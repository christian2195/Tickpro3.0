from tikects_app.decoradores import solo_clientes_permitido
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from tikects_app.models import Agentes, Cliente, Tickets_Servicios, Tickets_Colas, Gerencia
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Prefetch, Count, F, Avg
from django.db.models.functions import TruncMonth, TruncWeek
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import openpyxl
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from email.message import EmailMessage
import smtplib
import pandas as pd
from datetime import datetime
import os
import io
import itertools
import operator
import unicodedata
import ssl
# ============================================
# MODELOS
# ============================================
from .models import (
    Gerencia, Cliente, Tickets, 
    Agentes, Notificaciones, ReasignacionTikects, 
    Tickets_Servicios, Tickets_Colas, Tickets_Respuestas_Automaticas,
    Grupos_Agentes, Agentes_Por_Grupos, Grupos_Clientes, 
    AsignacionTikects, AgenteGenerico
)

# ============================================
# DECORADORES PERSONALIZADOS
# ============================================

def superuser_required(view_func):
    """Verifica que el usuario sea superusuario."""
    decorated_view_func = user_passes_test(
        lambda user: user.is_superuser,
        login_url='pagina_principal_clientes'
    )(view_func)
    return decorated_view_func

def agente_or_superuser_required(view_func):
    """Verifica que el usuario sea agente o superusuario."""
    decorated_view_func = user_passes_test(
        lambda user: user.is_superuser or hasattr(user, 'Agentes') or Agentes.objects.filter(usuario=user).exists(),
        login_url='inicio'
    )(view_func)
    return decorated_view_func

# ============================================
# FUNCIONES AUXILIARES
# ============================================

def _get_reasignaciones_dict():
    """Función auxiliar para obtener un diccionario de reasignaciones para todas las vistas."""
    reasignaciones_dict = {}
    try:
        for r in ReasignacionTikects.objects.select_related('agente_nuevo__usuario').all():
            if r.agente_nuevo and r.agente_nuevo.usuario:
                reasignaciones_dict[r.tikect.id] = r.agente_nuevo.usuario.username
    except Exception as e:
        print(f"Error obteniendo reasignaciones: {e}")
    return reasignaciones_dict

def _crear_ticket_base(request, titulo, descripcion, cola_id, servicio_id, usuario, gerencia_id=None):
    """Lógica común para crear un ticket."""
    cola = get_object_or_404(Tickets_Colas, id=cola_id)
    servicio = get_object_or_404(Tickets_Servicios, id=servicio_id)

    # 1. Buscamos el perfil del cliente a través del CORREO (ya que no existe campo 'usuario' en Cliente)
    cliente_vinculado = None
    if usuario.email:
        cliente_vinculado = Cliente.objects.filter(correo=usuario.email).first()

    correo_reserva = usuario.email or f"{usuario.username}@emvepro.gob.ve"

    # 2. PROCESAR LA GERENCIA DEL FORMULARIO
    if gerencia_id:
        gerencia_obj = Gerencia.objects.filter(id=gerencia_id).first()
        if gerencia_obj:
            if not cliente_vinculado:
                # CUIDADO AQUÍ: Quitamos 'usuario=usuario' porque ese campo no existe en tu BD
                cliente_vinculado = Cliente.objects.create(
                    nombre=usuario.get_full_name() or usuario.username,
                    correo=correo_reserva,
                    gerencia=gerencia_obj
                )
            else:
                # Si ya es cliente pero eligió otra gerencia, la actualizamos
                if cliente_vinculado.gerencia != gerencia_obj:
                    cliente_vinculado.gerencia = gerencia_obj
                    cliente_vinculado.save()

    # 3. Guardamos el ticket con su cliente vinculado
    nuevo_ticket = Tickets.objects.create(
        titulo=titulo,
        descripcion=descripcion,
        cola=cola,
        servicio=servicio,
        usuario=usuario,
        cliente=cliente_vinculado,
    )

    try:
        asignacion = AsignacionTikects.objects.get(servicio=servicio)
        if asignacion.agente_actual:
            Notificaciones.objects.create(
                tikect=nuevo_ticket,
                descripcion=f"Nuevo ticket '{titulo}'",
                usuario_creador=usuario,
                agente=asignacion.agente_actual
            )
    except AsignacionTikects.DoesNotExist:
        pass
    except Exception as e:
        print(f"Error creando notificación de asignación: {e}")

    return nuevo_ticket

@login_required
def crear_tikects_clientes(request):
    if request.method == 'GET':
        servicios = Tickets_Servicios.objects.all()
        colas = Tickets_Colas.objects.all()
        gerencias = Gerencia.objects.all()
        return render(request, 'tikects_crear.html', {
            'servicios': servicios,
            'colas': colas,
            'gerencias': gerencias,
        })
    elif request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        cola_id = request.POST.get('cola')
        servicio_id = request.POST.get('servicio')
        gerencia_id = request.POST.get('gerencia') # <--- CAPTURAMOS EL ID
        usuario = request.user

        if not all([titulo, descripcion, cola_id, servicio_id, gerencia_id]):
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect('crear_tikects_clientes')

        _crear_ticket_base(request, titulo, descripcion, cola_id, servicio_id, usuario, gerencia_id)
        
        messages.success(request, "Ticket creado exitosamente.")
        return redirect('ver_mis_tikects')
        
    return redirect('crear_tikects_clientes')

@login_required
def crear_tikects(request):
    # Verificamos si el usuario actual es un agente (o superusuario)
    es_agente_o_admin = request.user.is_superuser or Agentes.objects.filter(usuario=request.user).exists()

    if request.method == 'GET':
        servicios = Tickets_Servicios.objects.all()
        colas = Tickets_Colas.objects.all()
        gerencias = Gerencia.objects.all()
        
        # Obtenemos la lista de clientes para enviarla al template
        clientes = Cliente.objects.select_related('usuario').all()

        return render(request, 'tikects_crear.html', {
            'servicios': servicios,
            'colas': colas,
            'gerencias': gerencias,
            'clientes': clientes,
            'es_agente': es_agente_o_admin # Pasamos esta bandera al HTML
        })
        
    elif request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        cola_id = request.POST.get('cola')
        servicio_id = request.POST.get('servicio')
        gerencia_id = request.POST.get('gerencia') 
        
        # CAPTURAMOS EL CLIENTE AFECTADO (Si el agente lo seleccionó)
        cliente_id = request.POST.get('cliente_id')
        
        # Por defecto, el ticket le pertenece a quien tiene la sesión iniciada
        usuario = request.user 

        # Si se seleccionó a otro cliente, y quien crea el ticket tiene permisos (Agente/Admin)
        if cliente_id and es_agente_o_admin:
            try:
                usuario = User.objects.get(id=cliente_id)
            except User.DoesNotExist:
                messages.error(request, "El usuario seleccionado no existe.")
                return redirect('crear_tikects')

        if not all([titulo, descripcion, cola_id, servicio_id, gerencia_id]):
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect('crear_tikects')

        _crear_ticket_base(request, titulo, descripcion, cola_id, servicio_id, usuario, gerencia_id)
        
        messages.success(request, f"Ticket creado exitosamente para {usuario.first_name} {usuario.last_name}.")
        return redirect('ver_tikects')
        
    return redirect('crear_tikects')

# ============================================
# AUTENTICACIÓN
# ============================================

def inicio(request):
    if request.method == 'GET':
        return render(request, 'inicio_sesion_admin.html')
    else:
        username = request.POST.get('username')
        password = request.POST.get('clave')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            
            es_agente = Agentes.objects.filter(usuario=user).exists()
            
            if user.is_superuser or es_agente:
                return redirect('pagina_principal')
            else:
                return redirect('pagina_principal_clientes')
        else:
            return render(request, 'inicio_sesion_admin.html', {
                'error': 'Error usuario o contraseña incorrecta'
            })

@login_required
def cerrar_sesion(request):
    """Cierra la sesión activa de los usuarios y agentes."""
    logout(request)
    return redirect('/')

# ============================================
# PÁGINA PRINCIPAL
# ============================================

@login_required
def pagina_principal(request):
    user = request.user
    agente = None
    notificaciones = []
    text_tickets = []

    try:
        agente = Agentes.objects.filter(usuario=user).first()
    except Exception as e:
        print(f"Error al obtener instancia de Agente: {e}")

    if agente:
        try:
            notificaciones = Notificaciones.objects.filter(agente=agente, leida=False)[:5]
        except Exception as e:
            print(f"Error obteniendo notificaciones: {e}")

    try:
        if user.is_superuser or agente:
            ultimos_tickets = Tickets.objects.all().order_by('-fecha_creacion')[:5]
        else:
            tickets_cliente = Tickets.objects.filter(usuario=user).order_by('-fecha_creacion')[:5]
            if not tickets_cliente.exists():
                tickets_cliente = Tickets.objects.filter(cliente__usuario=user).order_by('-fecha_creacion')[:5]
            ultimos_tickets = tickets_cliente
    except Exception as e:
        print(f"Error al obtener tickets en panel principal: {e}")
        ultimos_tickets = []

    try:
        total_tickets = Tickets.objects.count()
        tickets_abiertos = Tickets.objects.exclude(estado='cerrado').count()
        tickets_cerrados = Tickets.objects.filter(estado__iexact='cerrado').count()
        total_agentes = Agentes.objects.count()
    except Exception as e:
        print(f"Error en estadísticas de página principal: {e}")
        total_tickets = tickets_abiertos = tickets_cerrados = total_agentes = 0

    now = datetime.now()

    return render(request, 'pagina_principal.html', {
        'notificaciones': notificaciones,
        'agente': agente,
        'ultimos_tickets': ultimos_tickets,
        'total_tickets': total_tickets,
        'tickets_abiertos': tickets_abiertos,
        'tickets_cerrados': tickets_cerrados,
        'total_agentes': total_agentes,
        'now': now
    })

@login_required
@solo_clientes_permitido
def pagina_clientes(request):
    """Página principal para clientes."""
    user = request.user
    
    # --- ESCUDO DE SEGURIDAD ---
    # Si el usuario es Agente, no tiene permiso para entrar al portal de clientes.
    # Lo redirigimos a la página principal de agentes o al dashboard técnico.
    if Agentes.objects.filter(usuario=user).exists():
        return redirect('pagina_principal') 
    # ---------------------------

    total_mis_tickets = 0
    mis_tickets_abiertos = 0
    mis_tickets_cerrados = 0
    ultimos_tickets = []

    try:
        # Optimizamos las consultas: obtenemos el queryset una sola vez
        mis_tickets = Tickets.objects.filter(usuario=user)
        
        total_mis_tickets = mis_tickets.count()
        mis_tickets_abiertos = mis_tickets.exclude(estado='cerrado').count()
        mis_tickets_cerrados = mis_tickets.filter(estado='cerrado').count()
        ultimos_tickets = mis_tickets.order_by('-fecha_creacion')[:5]
        
    except Exception as e:
        # En producción, podrías usar un logger en lugar de print
        print(f"Error en dashboard de clientes: {e}")

    return render(request, 'pagina_principal_clientes.html', {
        'total_mis_tickets': total_mis_tickets,
        'mis_tickets_abiertos': mis_tickets_abiertos,
        'mis_tickets_cerrados': mis_tickets_cerrados,
        'ultimos_tickets': ultimos_tickets,
        'now': datetime.now()
    })
# ============================================
# CONFIGURACIÓN
# ============================================

@superuser_required
@login_required
def configuracion(request):
    return render(request, 'configuracion.html')

# ============================================
# SERVICIOS, COLAS Y RESPUESTAS AUTOMÁTICAS
# ============================================

@superuser_required
@login_required
def tikects_servicios(request):
    servicios = Tickets_Servicios.objects.all()
    return render(request, 'tikects_servicios.html', {'servicios': servicios})

@superuser_required
@login_required
def tikects_colas(request):
    colas = Tickets_Colas.objects.all()
    return render(request, 'tikects_colas.html', {'colas': colas})

@login_required
def tikects_respuestas_automaticas(request):
    respuestas_automaticas = Tickets_Respuestas_Automaticas.objects.all()
    return render(request, 'tikects_respuestas_automaticas.html', {
        'respuestas_automaticas': respuestas_automaticas
    })

@superuser_required
@login_required
def tikects_servicios_crear(request):
    if request.method == 'POST':
        nombre = request.POST.get('servicio')
        descripcion = request.POST.get('servicio_descripcion')
        if nombre and descripcion:
            Tickets_Servicios.objects.create(nombre=nombre, descripcion=descripcion)
            return redirect('tikects_servicios')
    return render(request, 'tikects_servicios_crear.html')

@superuser_required
@login_required
def tikects_colas_crear(request):
    if request.method == 'POST':
        nombre = request.POST.get('colas')
        descripcion = request.POST.get('colas_descripcion')
        if nombre and descripcion:
            Tickets_Colas.objects.create(nombre=nombre, descripcion=descripcion)
            return redirect('tikects_colas')
    return render(request, 'tikects_colas_crear.html')

@superuser_required
@login_required
def tikects_respuestas_automaticas_crear(request):
    if request.method == 'POST':
        nombre = request.POST.get('respuesta')
        if nombre:
            Tickets_Respuestas_Automaticas.objects.create(nombre=nombre)
            return redirect('tikects_respuestas_automaticas')
    return render(request, 'tikects_respuestas_automaticas_crear.html')

@superuser_required
@login_required
def eliminar_servicio(request, servicio_id):
    servicio = get_object_or_404(Tickets_Servicios, id=servicio_id)
    if request.method == 'POST':
        servicio.delete()
    return redirect('tikects_servicios')

@superuser_required
@login_required
def eliminar_cola(request, cola_id):
    cola = get_object_or_404(Tickets_Colas, id=cola_id)
    if request.method == 'POST':
        cola.delete()
    return redirect('tikects_colas')

@superuser_required
@login_required
def eliminar_respuesta_automatica(request, respuesta_id):
    respuesta = get_object_or_404(Tickets_Respuestas_Automaticas, id=respuesta_id)
    if request.method == 'POST':
        respuesta.delete()
    return redirect('tikects_respuestas_automaticas')

@superuser_required
@login_required
def editar_servicios(request, servicio_id):
    servicio = get_object_or_404(Tickets_Servicios, id=servicio_id)
    if request.method == 'POST':
        servicio.nombre = request.POST.get('nombre')
        servicio.descripcion = request.POST.get('descripcion')
        servicio.save()
        return redirect('tikects_servicios')
    return render(request, 'tikects_servicios_editar.html', {'servicio': servicio})

@superuser_required
@login_required
def editar_cola(request, cola_id):
    cola = get_object_or_404(Tickets_Colas, id=cola_id)
    if request.method == 'POST':
        cola.nombre = request.POST.get('nombre')
        cola.descripcion = request.POST.get('descripcion')
        cola.save()
        return redirect('tikects_colas')
    return render(request, 'tikects_colas_editar.html', {'cola': cola})

# ============================================
# AGENTES Y GRUPOS
# ============================================

@superuser_required
@login_required
def usuarios_agentes(request):
    agentes = Agentes.objects.all()
    return render(request, 'usuarios_agentes.html', {'agentes': agentes})

@superuser_required
@login_required
def usuarios_agentes_crear(request):
    if request.method == 'GET':
        usuarios = User.objects.exclude(agentes__isnull=False).order_by('username')
        return render(request, 'usuarios_agentes_crear.html', {'usuarios_disponibles': usuarios})
    elif request.method == 'POST':
        usuario_id = request.POST.get('usuario_id')
        if usuario_id:
            user = get_object_or_404(User, id=usuario_id)
        else:
            nombre = request.POST.get('nombre')
            apellido = request.POST.get('apellido')
            username = request.POST.get('nombre_usuario')
            email = request.POST.get('email')
            password = request.POST.get('password')
            user = User.objects.create_user(username=username, email=email, password=password, first_name=nombre, last_name=apellido)
            user.is_staff = True
            user.save()
        agente, created = Agentes.objects.get_or_create(usuario=user, defaults={'nombre_usuario': user.username, 'correo': user.email})
        return redirect('usuarios_agentes')

@superuser_required
@login_required
def editar_agente(request, agente_id):
    agente = get_object_or_404(Agentes, id=agente_id)
    usuario = agente.usuario
    if request.method == 'POST':
        usuario.username = request.POST.get('nombre_usuario')
        usuario.first_name = request.POST.get('nombre')
        usuario.last_name = request.POST.get('apellido')
        usuario.email = request.POST.get('email')
        if request.POST.get('password'): usuario.set_password(request.POST.get('password'))
        usuario.save()
        agente.nombre_usuario = usuario.username
        agente.correo = usuario.email
        agente.save()
        return redirect('usuarios_agentes')
    return render(request, 'agentes_editar.html', {'agente': agente})

@superuser_required
@login_required
def eliminar_agente(request, agente_id):
    agent = get_object_or_404(Agentes, id=agente_id)
    if request.method == 'POST':
        agent.delete()
    return redirect('usuarios_agentes')

@login_required
def usuarios_grupos_agentes(request):
    return render(request, 'usuarios_grupos_agentes.html', {'grupos_agentes': Grupos_Agentes.objects.all()})

@login_required
def usuarios_grupos_agentes_crear(request):
    if request.method == 'POST':
        Grupos_Agentes.objects.create(nombre=request.POST.get('nombre_grupo'), descripcion=request.POST.get('descripcion_grupo'))
        return redirect('usuarios_grupos_agentes')
    return render(request, 'usuarios_grupos_agentes_crear.html')

@login_required
def usuariops_grupo_agentes_eliminar(request, grupo_id):
    if request.method == 'POST':
        get_object_or_404(Grupos_Agentes, id=grupo_id).delete()
    return redirect('usuarios_grupos_agentes')

@login_required
def usuarios_por_grupos_agentes(request):
    grupos = Grupos_Agentes.objects.prefetch_related(Prefetch('agentes_por_grupos_set', queryset=Agentes_Por_Grupos.objects.select_related('agente'))).all()
    return render(request, 'usuarios_por_grupos_agentes.html', {'grupos': grupos})

@login_required
def usuarios_grupos_agentes_agregar(request):
    if request.method == 'POST':
        agente_id = request.POST.get('agente')
        grupo_id = request.POST.get('grupo')
        if agente_id and grupo_id:
            Agentes_Por_Grupos.objects.get_or_create(agente_id=agente_id, grupo_id=grupo_id)
            return redirect('usuarios_por_grupos_agentes')
    return render(request, 'usuarios_grupos_agentes_agregar.html', {'agentes': Agentes.objects.all(), 'grupos': Grupos_Agentes.objects.all()})

@login_required
def eliminar_agente_de_grupo(request, grupo_agente_id):
    if request.method == 'POST':
        get_object_or_404(Agentes_Por_Grupos, id=grupo_agente_id).delete()
    return redirect('usuarios_por_grupos_agentes')

@login_required
def editar_grupo(request, grupo_id):
    grupo = get_object_or_404(Grupos_Agentes, id=grupo_id)
    if request.method == 'POST':
        grupo.nombre = request.POST.get('nombre')
        grupo.descripcion = request.POST.get('descripcion')
        grupo.save()
        Agentes_Por_Grupos.objects.filter(grupo=grupo).delete()
        for agente_id in request.POST.getlist('agentes'):
            Agentes_Por_Grupos.objects.create(grupo=grupo, agente_id=agente_id)
        return redirect('usuarios_grupos_agentes')
    return render(request, 'grupos_editar.html', {
        'grupo': grupo, 
        'todos_los_agentes': Agentes.objects.all(), 
        'agentes_del_grupo': Agentes_Por_Grupos.objects.filter(grupo=grupo).values_list('agente_id', flat=True)
    })

# ============================================
# CLIENTES Y GERENCIAS
# ============================================

@superuser_required
@login_required
def clientes(request):
    # 🔑 Le quitamos 'usuario' porque el modelo no tiene esa llave directa
    clientes_list = Cliente.objects.select_related('gerencia').all().order_by('nombre')
    paginator = Paginator(clientes_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'usuarios_clientes.html', {'page_obj': page_obj})

@superuser_required
@login_required
def crear_clientes(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip() or None
        telefono = request.POST.get('telefono', '').strip() or None
        password = request.POST.get('password', '').strip()
        gerencia_input = request.POST.get('gerencia', '').strip()

        if not all([nombre, apellido, username, password, gerencia_input]):
            messages.error(request, "Todos los campos marcados como obligatorios deben ser completados.")
            gerencias = Gerencia.objects.all()
            return render(request, 'usuarios_clientes_crear.html', {'gerencias': gerencias})

        if User.objects.filter(username=username).exists():
            messages.error(request, f"El nombre de usuario '{username}' ya se encuentra registrado.")
            gerencias = Gerencia.objects.all()
            return render(request, 'usuarios_clientes_crear.html', {'gerencias': gerencias})

        try:
            if gerencia_input.isdigit():
                gerencia_obj = get_object_or_404(Gerencia, id=int(gerencia_input))
            else:
                gerencia_obj, _ = Gerencia.objects.get_or_create(
                    nombre=gerencia_input,
                    defaults={'descripcion': f'Gerencia de {gerencia_input}'}
                )

            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=nombre,
                last_name=apellido,
                email=email if email else ''
            )
            
            Cliente.objects.create(
                nombre=f"{nombre} {apellido}",
                correo=email,
                telefono=telefono,
                gerencia=gerencia_obj,
                usuario=user
            )
            
            messages.success(request, f"Cliente '{nombre} {apellido}' registrado con éxito.")
            return redirect('clientes')
            
        except Exception as e:
            messages.error(request, f"Error de base de datos al registrar: {str(e)}")
            gerencias = Gerencia.objects.all()
            return render(request, 'usuarios_clientes_crear.html', {'gerencias': gerencias})
            
    gerencias = Gerencia.objects.all()
    return render(request, 'usuarios_clientes_crear.html', {'gerencias': gerencias})

@superuser_required
@login_required
def editar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente.objects.select_related('usuario'), id=cliente_id)
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        username = request.POST.get('nombre_usuario', '').strip()
        email = request.POST.get('email', '').strip() or None
        gerencia_id = request.POST.get('gerencia', '').strip()
        password = request.POST.get('password', '').strip()

        if not all([nombre, apellido, username, gerencia_id]):
            messages.error(request, "Nombre, apellido, nombre de usuario y gerencia son obligatorios.")
            gerencias = Gerencia.objects.all()
            return render(request, 'usuarios_editar_cliente.html', {
                'cliente': cliente,
                'gerencias': gerencias
            })

        try:
            user = cliente.usuario
            if user:
                user.username = username
                user.first_name = nombre
                user.last_name = apellido
                user.email = email if email else ''
                if password:
                    user.set_password(password)
                user.save()
            
            cliente.nombre = f"{nombre} {apellido}"
            cliente.correo = email
            cliente.gerencia_id = int(gerencia_id)
            cliente.save()
            
            messages.success(request, f"Cliente '{nombre} {apellido}' actualizado con éxito.")
            return redirect('clientes')
            
        except Exception as e:
            messages.error(request, f"Error al actualizar cliente: {str(e)}")
            
    gerencias = Gerencia.objects.all()
    return render(request, 'usuarios_editar_cliente.html', {
        'cliente': cliente,
        'gerencias': gerencias
    })

@superuser_required
@login_required
def eliminar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    if request.method == 'POST':
        try:
            nombre = cliente.nombre
            cliente.delete()
            messages.success(request, f"Cliente '{nombre}' eliminado exitosamente.")
        except Exception as e:
            messages.error(request, f"Error al eliminar cliente: {str(e)}")
    return redirect('clientes')

@superuser_required
@login_required
def usuarios_clientes_grupos(request):
    grupos_clientes = Grupos_Clientes.objects.all()
    return render(request, 'usuarios_clientes_grupos.html', {'grupos_clientes': grupos_clientes})

@superuser_required
@login_required
def usuarios_clientes_grupos_crear(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        if nombre and descripcion:
            Grupos_Clientes.objects.create(nombre=nombre, descripcion=descripcion)
            return redirect('usuarios_clientes_grupos')
    return render(request, 'usuarios_clientes_grupos_crear.html')

@login_required
@superuser_required
def ver_gerencias(request):
    # 'lista_gerencias' es la variable que enviaremos al HTML
    lista_gerencias = Gerencia.objects.all().order_by('nombre')
    return render(request, 'gerencias.html', {
        'gerencias': lista_gerencias
    })

@superuser_required
@login_required
def crear_gerencia(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        if nombre and descripcion:
            Gerencia.objects.create(nombre=nombre, descripcion=descripcion)
            messages.success(request, 'Gerencia creada con éxito.')
            return redirect('ver_gerencias')
        else:
            messages.error(request, 'Todos los campos son obligatorios.')
    return render(request, 'gerencias_crear.html')

@superuser_required
@login_required
def editar_gerencia(request, gerencia_id):
    gerencia = get_object_or_404(Gerencia, id=gerencia_id)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        if nombre and descripcion:
            gerencia.nombre = nombre
            gerencia.descripcion = descripcion
            gerencia.save()
            messages.success(request, 'Gerencia actualizada.')
            return redirect('ver_gerencias')
        else:
            messages.error(request, 'Todos los campos son obligatorios.')
    return render(request, 'editar_gerencia.html', {'gerencia': gerencia})

@superuser_required
@login_required
def eliminar_gerencia(request, gerencia_id):
    gerencia = get_object_or_404(Gerencia, id=gerencia_id)
    if request.method == 'POST':
        gerencia.delete()
        messages.success(request, 'Gerencia eliminada.')
    return redirect('ver_gerencias')

# ============================================
# TICKETS - VISTAS PRINCIPALES
# ============================================

@login_required
def ver_tikects(request):
    tikects = Tickets.objects.select_related('usuario', 'servicio', 'cola').all().order_by('-fecha_creacion')
    reasignaciones_dict = _get_reasignaciones_dict()
    paginator = Paginator(tikects, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'tikects_ver_todos.html', {
        'tikects': page_obj,
        'reasignaciones_dict': reasignaciones_dict
    })

@login_required
def ver_tikects_cerrados(request):
    tikects = Tickets.objects.filter(estado='cerrado').select_related('usuario', 'servicio', 'cola').order_by('-fecha_creacion')
    reasignaciones_dict = _get_reasignaciones_dict()
    paginator = Paginator(tikects, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'tikects_ver_todos.html', {
        'tikects': page_obj,
        'reasignaciones_dict': reasignaciones_dict
    })

@login_required
def ver_tikects_abiertos(request):
    tikects = Tickets.objects.exclude(estado='cerrado').select_related('usuario', 'servicio', 'cola').order_by('-fecha_creacion')
    reasignaciones_dict = _get_reasignaciones_dict()
    paginator = Paginator(tikects, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'tikects_ver_todos.html', {
        'tikects': page_obj,
        'reasignaciones_dict': reasignaciones_dict
    })

@login_required
def detalle_tikect(request, tikect_id):
    # Se añade 'cliente__gerencia' al select_related para traer la jerarquía completa
    # y evitar consultas adicionales al acceder a la gerencia en el template.
    tikect = get_object_or_404(
        Tickets.objects.select_related(
            'usuario', 
            'servicio', 
            'cola', 
            'cerrado_por_agente__usuario', 
            'cliente__gerencia'
        ), 
        id=tikect_id
    )
    
    # Marcamos notificaciones como leídas
    Notificaciones.objects.filter(tikect=tikect, agente__usuario=request.user).update(leida=True)

    # Lógica de cierre mediante POST
    if request.method == 'POST' and request.POST.get('accion') == 'cerrar':
        tikect.estado = 'cerrado'
        tikect.save()
        
        # Redirección según el rol del usuario
        if hasattr(request.user, 'agente'):
            return redirect('ver_tikects_asignados_agentes')
        else:
            return redirect('ver_tikects')

    # Lógica de verificación de reasignación
    reasignado = False
    if hasattr(request.user, 'agente'):
        reasignado = ReasignacionTikects.objects.filter(
            tikect=tikect,
            agente_nuevo=request.user.agente
        ).exists()

    return render(request, 'detalle_tikect.html', {
        'tikect': tikect,
        'reasignado': reasignado
    })

@agente_or_superuser_required  # <--- EL CANDADO REAL
def cerrar_tikect(request, tikect_id):
    # Optimizamos la carga para incluir el usuario relacionado
    tikect = get_object_or_404(Tickets.objects.select_related('usuario'), id=tikect_id)
    # ...
    if request.method == 'POST':
        descripcion_solucion = request.POST.get('descripcion_solucion', '').strip()
        
        # Actualizamos campos de cierre
        tikect.estado = 'cerrado'
        tikect.fecha_cierre = timezone.now()
        tikect.descripcion_solucion = descripcion_solucion
        
        # Intentamos obtener el agente de forma más segura
        # Primero buscamos en la relación directa, si no, buscamos en el modelo Agentes
        agente_actual = getattr(request.user, 'agente', None)
        if not agente_actual:
            agente_actual = Agentes.objects.filter(usuario=request.user).first()
            
        tikect.cerrado_por_agente = agente_actual
        tikect.save()
        
# Notificación por email
        if tikect.usuario and tikect.usuario.email:
            # EN LUGAR DE send_mail, LLAMAMOS A NUESTRA FUNCIÓN DE LA VISTA LEGADO
            try:
                enviar_correo_estado(tikect)
            except Exception as e:
                print(f"Error al enviar correo automático: {e}")

        messages.success(request, "Ticket cerrado exitosamente.")
        
        # Redirección basada en si el usuario es agente o no
        if agente_actual:
            return redirect('ver_tikects_asignados_agentes')
        return redirect('ver_tikects')
            
    return redirect('detalle_tikect', tikect_id=tikect.id)

@login_required
def reasignar_tikect(request, tikect_id):
    ticket = get_object_or_404(Tickets, id=tikect_id)
    
    try:
        agente_actual = Agentes.objects.get(usuario=request.user)
    except Agentes.DoesNotExist:
        messages.error(request, "No tienes permisos para reasignar tickets. No eres un agente.")
        return redirect('detalle_tikect', tikect_id=ticket.id)

    if ReasignacionTikects.objects.filter(tikect=ticket, agente_nuevo=agente_actual).exists():
        messages.error(request, "Este ticket ya ha sido reasignado a ti.")
        return redirect('detalle_tikect', tikect_id=ticket.id)

    grupo_agente_actual = Agentes_Por_Grupos.objects.filter(agente=agente_actual).first()
    if not grupo_agente_actual:
        messages.error(request, "No perteneces a ningún grupo resolutor.")
        return redirect('detalle_tikect', tikect_id=ticket.id)

    agentes_grupo = Agentes.objects.filter(
        agentes_por_grupos__grupo=grupo_agente_actual.grupo
    ).exclude(id=agente_actual.id).select_related('usuario')

    if request.method == 'POST':
        nuevo_agente_id = request.POST.get('nuevo_agente')
        if not nuevo_agente_id:
            messages.error(request, "Debe seleccionar un agente para reasignar.")
            return redirect('reasignar_tikect', tikect_id=ticket.id)
        
        try:
            nuevo_agente = Agentes.objects.get(id=nuevo_agente_id)
            
            # 1. Guardar la reasignación en la BD
            ReasignacionTikects.objects.create(
                tikect=ticket,
                agente_anterior=agente_actual,
                agente_nuevo=nuevo_agente
            )
            
            # 2. Generar la alerta interna (Campanita)
            Notificaciones.objects.create(
                tikect=ticket,
                agente=nuevo_agente,
                descripcion=f"Ticket reasignado desde {agente_actual.nombre_usuario}"
            )

            # 3. Disparar el correo electrónico al nuevo agente
            try:
                if nuevo_agente.usuario and nuevo_agente.usuario.email:
                    # Capturamos la prioridad de forma segura
                    prioridad_txt = ticket.prioridad.upper() if hasattr(ticket, 'prioridad') and ticket.prioridad else 'NO DEFINIDA'
                    
                    mensaje_reasignacion = (
                        f"Se te ha reasignado un nuevo ticket.<br><br>"
                        f"<b>Agente anterior:</b> {agente_actual.nombre_usuario}<br>"
                        f"<b>Prioridad:</b> {prioridad_txt}<br><br>"
                        f"Por favor, ingresa al portal de EMVEPRO para atender este requerimiento."
                    )
                    
                    enviar_correo_profesional(
                        ticket=ticket,
                        asunto=f"¡NUEVA REASIGNACIÓN! Ticket #{ticket.id} - {ticket.titulo}",
                        mensaje_cuerpo=mensaje_reasignacion,
                        destinatario_correo=nuevo_agente.usuario.email,
                        destinatario_nombre=nuevo_agente.nombre_usuario
                    )
            except Exception as email_error:
                print(f"Error al enviar correo de reasignación al agente {nuevo_agente.nombre_usuario}: {email_error}")
            
            # 4. Finalizar con éxito
            messages.success(request, f"Ticket reasignado exitosamente a {nuevo_agente.nombre_usuario}")
            return redirect('ver_tikects_asignados_agentes')
            
        except Exception as e:
            messages.error(request, f"Error al reasignar: {str(e)}")
            return redirect('reasignar_tikect', tikect_id=ticket.id)

    return render(request, 'reasignar_tikects.html', {
        'tikect': ticket,
        'agentes_grupo': agentes_grupo
    })
# ============================================
# TICKETS - VISTAS PARA CLIENTES (CORREGIDAS)
# ============================================

@login_required
@solo_clientes_permitido
def ver_mis_tikects(request):
    # 🚫 Restricción para resolutores
    if request.user.is_superuser or Agentes.objects.filter(usuario=request.user).exists():
        return redirect('pagina_principal')

    # Filtramos por el cliente relacionado al usuario
    tikects = Tickets.objects.filter(usuario=request.user).select_related('servicio', 'cola').order_by('-fecha_creacion')
    
    paginator = Paginator(tikects, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'tikects_vista_lista_cliente.html', {'page_obj': page_obj})

@login_required
@solo_clientes_permitido
def ver_mis_tikects_cerrados(request):
    if request.user.is_superuser or Agentes.objects.filter(usuario=request.user).exists():
        return redirect('pagina_principal')

    tikects = Tickets.objects.filter(usuario=request.user, estado__iexact='cerrado').select_related('servicio', 'cola').order_by('-fecha_creacion')
    paginator = Paginator(tikects, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'tikects_vista_lista_cliente.html', {'page_obj': page_obj})

@login_required
@solo_clientes_permitido
def ver_mis_tikects_abiertos(request):
    if request.user.is_superuser or Agentes.objects.filter(usuario=request.user).exists():
        return redirect('pagina_principal')

    tikects = Tickets.objects.filter(usuario=request.user).exclude(estado__iexact='cerrado').select_related('servicio', 'cola').order_by('-fecha_creacion')
    paginator = Paginator(tikects, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'tikects_vista_lista_cliente.html', {'page_obj': page_obj})

@login_required
@solo_clientes_permitido
def crear_tikects_clientes(request):
    if request.method == 'GET':
        servicios = Tickets_Servicios.objects.all()
        colas = Tickets_Colas.objects.all()
        gerencias = Gerencia.objects.all()
        return render(request, 'tikects_crear.html', {
            'servicios': servicios,
            'colas': colas,
            'gerencias': gerencias,
        })
    elif request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        cola_id = request.POST.get('cola')
        servicio_id = request.POST.get('servicio')
        usuario = request.user

        if not all([titulo, descripcion, cola_id, servicio_id]):
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect('crear_tikects_clientes')

        _crear_ticket_base(request, titulo, descripcion, cola_id, servicio_id, usuario)
        
        messages.success(request, "Ticket creado exitosamente.")
        return redirect('ver_mis_tikects')
        
    return redirect('crear_tikects_clientes')

@login_required
def crear_tikects(request):
    if request.method == 'GET':
        servicios = Tickets_Servicios.objects.all()
        colas = Tickets_Colas.objects.all()
        gerencias = Gerencia.objects.all()
        return render(request, 'tikects_crear.html', {
            'servicios': servicios,
            'colas': colas,
            'gerencias': gerencias
        })
    elif request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        cola_id = request.POST.get('cola')
        servicio_id = request.POST.get('servicio')
        usuario = request.user

        if not all([titulo, descripcion, cola_id, servicio_id]):
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect('crear_tikects')

        _crear_ticket_base(request, titulo, descripcion, cola_id, servicio_id, usuario)
        
        messages.success(request, "Ticket creado exitosamente.")
        return redirect('ver_tikects')
        
    return redirect('crear_tikects')

# ============================================
# TICKETS - VISTAS PARA AGENTES (UNIFICADAS)
# ============================================

@login_required
def ver_tikects_asignados_agentes(request):
    """Vista unificada que muestra todos los tickets asignados a un agente."""
    url_name = request.resolver_match.url_name
    
    try:
        agente_actual = Agentes.objects.get(usuario=request.user)
    except Agentes.DoesNotExist:
        messages.error(request, "No tienes un perfil de agente asociado.")
        return redirect('pagina_principal')

    # 1. Tickets creados por el agente (como usuario final)
    tickets_directos = Tickets.objects.filter(usuario=request.user)
    
    # 2. Tickets reasignados al agente
    tickets_reasignados = Tickets.objects.filter(reasignaciontikects__agente_nuevo=agente_actual)
    
    # 3. Tickets asignados directamente en el Triage
    tickets_triage = Tickets.objects.filter(agente_asignado=agente_actual)
    
    # 4. Tickets por Servicio (Extraemos los IDs para evitar el ValueError)
    # Accedemos al servicio a través del campo 'tikect' que sí existe en la tabla
    servicios_ids = list(AsignacionTikects.objects.filter(agente=agente_actual).values_list('tikect__servicio_id', flat=True))
    servicios_ids += list(AgenteGenerico.objects.filter(agente_actual=agente_actual).values_list('servicio_id', flat=True))
    tickets_servicios = Tickets.objects.filter(servicio_id__in=servicios_ids)
    
    # Unificamos todo de forma limpia
    tickets_combinados = Tickets.objects.filter(
        Q(id__in=tickets_directos) |
        Q(id__in=tickets_reasignados) |
        Q(id__in=tickets_triage) |
        Q(id__in=tickets_servicios)
    ).distinct().select_related('usuario', 'servicio', 'cola', 'cerrado_por_agente__usuario').order_by('-fecha_creacion')
    
    tikects_cerrados = tickets_combinados.filter(estado__iexact='cerrado').count()
    tikects_abiertos = tickets_combinados.exclude(estado__iexact='cerrado').count()
    
    if url_name == 'ver_tikects_asignados_agentes_cerrados':
        tickets_filtrados = tickets_combinados.filter(estado__iexact='cerrado')
    elif url_name == 'ver_tikects_asignados_agentes_abiertos':
        tickets_filtrados = tickets_combinados.exclude(estado__iexact='cerrado')
    else:
        tickets_filtrados = tickets_combinados
    
    paginator = Paginator(tickets_filtrados, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    reasignaciones_dict = _get_reasignaciones_dict()
    
    context = {
        'tikects': page_obj,
        'tikects_abiertos': tikects_abiertos,
        'tikects_cerrados': tikects_cerrados,
        'reasignaciones_dict': reasignaciones_dict,
    }
    return render(request, 'tikects_asignados_agentes.html', context)

@login_required
def ver_tikects_asignados_agentes_cerrados(request):
    return ver_tikects_asignados_agentes(request)

@login_required
def ver_tikects_asignados_agentes_abiertos(request):
    return ver_tikects_asignados_agentes(request)

# ============================================
# ESTADÍSTICAS Y EXPORTACIONES
# ============================================

@superuser_required
@login_required
def tikects_estadisticas(request):
    total_tikects = Tickets.objects.count()
    tikects_cerrados = Tickets.objects.filter(estado__iexact='cerrado').count()
    tikects_abiertos = total_tikects - tikects_cerrados

    porcentaje_abiertos = (tikects_abiertos / total_tikects * 100) if total_tikects > 0 else 0
    porcentaje_cerrados = (tikects_cerrados / total_tikects * 100) if total_tikects > 0 else 0

    servicios = Tickets.objects.values('servicio__nombre').annotate(count=Count('servicio')).order_by('-count')

    tikects_por_dia_cerrados = Tickets.objects.filter(estado='cerrado', fecha_cierre__isnull=False) \
        .values('fecha_cierre__date') \
        .annotate(count=Count('id')) \
        .order_by('fecha_cierre__date')
        
    tikects_por_mes_cerrados = Tickets.objects.filter(estado='cerrado', fecha_cierre__isnull=False) \
        .annotate(month=TruncMonth('fecha_cierre')) \
        .values('month') \
        .annotate(count=Count('id')) \
        .order_by('month')
        
    tikects_por_semana_cerrados = Tickets.objects.filter(estado='cerrado', fecha_cierre__isnull=False) \
        .annotate(week=TruncWeek('fecha_cierre')) \
        .values('week') \
        .annotate(count=Count('id')) \
        .order_by('week')

    tiempo_promedio = 0
    tickets_resueltos = Tickets.objects.filter(estado='cerrado', fecha_cierre__isnull=False)
    if tickets_resueltos.exists():
        promedio_td = tickets_resueltos.aggregate(avg_time=Avg(F('fecha_cierre') - F('fecha_creacion')))['avg_time']
        if promedio_td:
            tiempo_promedio = round(promedio_td.total_seconds() / 3600, 1)

    tickets_por_prioridad = list(Tickets.objects.values('prioridad').annotate(count=Count('id')))
    tickets_por_cola = list(Tickets.objects.values('cola__nombre').annotate(count=Count('id')).exclude(cola__isnull=True))

    tikects_por_agente = Tickets.objects.filter(estado='cerrado', cerrado_por_agente__isnull=False) \
        .values('cerrado_por_agente__usuario__username', 'cerrado_por_agente__usuario__first_name', 'cerrado_por_agente__usuario__last_name') \
        .annotate(count=Count('id')) \
        .order_by('-count')
        
    tikects_por_agente_list = []
    for item in tikects_por_agente:
        tikects_por_agente_list.append({
            'cerrado_por_agente__username': item['cerrado_por_agente__usuario__username'],
            'cerrado_por_agente__first_name': item['cerrado_por_agente__usuario__first_name'],
            'cerrado_por_agente__last_name': item['cerrado_por_agente__usuario__last_name'],
            'count': item['count']
        })

    context = {
        'total_tikects': total_tikects,
        'tikects_cerrados': tikects_cerrados,
        'tikects_abiertos': tikects_abiertos,
        'porcentaje_abiertos': porcentaje_abiertos,
        'porcentaje_cerrados': porcentaje_cerrados,
        'tiempo_promedio': tiempo_promedio,
        'tickets_por_prioridad': tickets_por_prioridad,
        'tickets_por_cola': tickets_por_cola,
        'servicios': list(servicios),
        'tikects_por_dia_cerrados': list(tikects_por_dia_cerrados),
        'tikects_por_mes_cerrados': list(tikects_por_mes_cerrados),
        'tikects_por_semana_cerrados': list(tikects_por_semana_cerrados),
        'tikects_por_agente': tikects_por_agente_list,
    }
    return render(request, 'estadisticas.html', context)

@superuser_required
@login_required
def exportar_tikects_excel(request):
    servicio_seleccionado = request.GET.get('servicio', 'Todo')
    if servicio_seleccionado == 'Todo':
        tikects = Tickets.objects.filter(estado='cerrado')
    else:
        tikects = Tickets.objects.filter(estado='cerrado', servicio__nombre=servicio_seleccionado)

    wb = openpyxl.Workbook()
    grid = wb.active
    grid.title = "Tickets Cerrados"

    headers = ['ID', 'Título', 'Descripción', 'Usuario', 'Servicio', 'Fecha Creación', 'Fecha Cierre', 'Solución', 'Agente que cerró', 'Gerencia']
    grid.append(headers)

    for t in tikects:
        grid.append([
            t.id,
            t.titulo,
            t.descripcion,
            t.usuario.username if t.usuario else '',
            t.servicio.nombre if t.servicio else '',
            t.fecha_creacion.strftime('%Y-%m-%d %H:%M') if t.fecha_creacion else '',
            t.fecha_cierre.strftime('%Y-%m-%d %H:%M') if t.fecha_cierre else '',
            t.descripcion_solucion or '',
            t.cerrado_por_agente.nombre_usuario if t.cerrado_por_agente else '',
            t.gerencia or ''
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=tickets_cerrados_{servicio_seleccionado}.xlsx'
    wb.save(response)
    return response

@superuser_required
@login_required
def exportar_tikects_pdf(request):
    servicio_seleccionado = request.GET.get('servicio', 'Todo')
    if servicio_seleccionado == 'Todo':
        tikects = Tickets.objects.filter(estado='cerrado')
    else:
        tikects = Tickets.objects.filter(estado='cerrado', servicio__nombre=servicio_seleccionado)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=tickets_cerrados_{servicio_seleccionado}.pdf'

    c = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    x, y = 50, height - 50
    line_height = 14

    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, f"Tickets Cerrados - {servicio_seleccionado}")
    y -= 30

    c.setFont("Helvetica-Bold", 10)
    headers = ['ID', 'Título', 'Usuario', 'Servicio', 'Fecha Cierre']
    col_widths = [40, 200, 100, 100, 80]
    x_pos = x
    for i, h in enumerate(headers):
        c.drawString(x_pos, y, h)
        x_pos += col_widths[i]
    y -= line_height

    c.setFont("Helvetica", 9)
    for t in tikects:
        x_pos = x
        c.drawString(x_pos, y, str(t.id))
        x_pos += col_widths[0]
        c.drawString(x_pos, y, t.titulo[:30] if t.titulo else '')
        x_pos += col_widths[1]
        c.drawString(x_pos, y, t.usuario.username[:15] if t.usuario else '')
        x_pos += col_widths[2]
        c.drawString(x_pos, y, t.servicio.nombre if t.servicio else '')
        x_pos += col_widths[3]
        c.drawString(x_pos, y, t.fecha_cierre.strftime('%Y-%m-%d') if t.fecha_cierre else '')
        y -= line_height
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 9)

    c.save()
    return response

# ============================================
# AGENTES GENÉRICOS
# ============================================

@superuser_required
@login_required
def agente_generico(request):
    if request.method == 'GET':
        servicios_asignados = AgenteGenerico.objects.values_list('servicio_id', flat=True)
        servicios = Tickets_Servicios.objects.exclude(id__in=servicios_asignados)
        agentes = Agentes.objects.all()
        return render(request, 'agente_generico.html', {'servicios': servicios, 'agentes': agentes})
    else:
        servicio_id = request.POST.get('servicio')
        agente_actual_id = request.POST.get('agente_actual')
        tiempo_reasignacion = request.POST.get('tiempo_reasignacion')
        agente_reasignacion_id = request.POST.get('agente_reasignacion')
        
        if not servicio_id or not agente_actual_id:
            messages.error(request, "Debe seleccionar un servicio y un agente actual.")
            return redirect('agente_generico')
        
        try:
            servicio = Tickets_Servicios.objects.get(id=servicio_id)
            agente_actual = Agentes.objects.get(id=agente_actual_id)
            agente_reasignacion = Agentes.objects.get(id=agente_reasignacion_id) if agente_reasignacion_id else None
            tiempo = int(tiempo_reasignacion) if tiempo_reasignacion else None
            
            AgenteGenerico.objects.create(
                servicio=servicio,
                agente_actual=agente_actual,
                tiempo_reasignacion=tiempo,
                agente_reasignacion=agente_reasignacion
            )
            messages.success(request, "Asignación de agente genérico completada.")
            return redirect('ver_agentes_genericos')
        except Exception as e:
            messages.error(request, f"Error: {e}")
            return redirect('agente_generico')

@superuser_required
@login_required
def ver_agentes_genericos(request):
    asignaciones = AgenteGenerico.objects.select_related('servicio', 'agente_actual', 'agente_reasignacion').all()
    return render(request, 'agentes_genericos_ver.html', {'asignaciones': asignaciones})

@superuser_required
@login_required
def eliminar_asignacion(request, asignacion_id):
    asignacion = get_object_or_404(AgenteGenerico, id=asignacion_id)
    if request.method == 'POST':
        asignacion.delete()
        messages.success(request, "Asignación personalizada removida.")
    return redirect('ver_agentes_genericos')

# ============================================
# PERMISOS & NOTIFICACIONES
# ============================================

@superuser_required
@login_required
def permisos(request):
    agentes = Agentes.objects.all()
    grupos = Grupos_Agentes.objects.all()
    return render(request, 'permisos.html', {'agentes': agentes, 'grupos': grupos})

def check_notifications(request):
    if request.user.is_authenticated:
        # Búsqueda segura para evitar el error RelatedObjectDoesNotExist
        agente = Agentes.objects.filter(usuario=request.user).first()
        
        if agente:
            nuevas = Notificaciones.objects.filter(agente=agente, leida=False)
            notificaciones = [
                {'tikect_id': n.tikect.id, 'descripcion': n.descripcion} 
                for n in nuevas
            ]
            return JsonResponse({
                'new_notifications': nuevas.exists(), 
                'notifications': notificaciones
            })
            
    return JsonResponse({'new_notifications': False, 'notifications': []})

# ============================================
# CARGA MASIVA DE USUARIOS Y TICKETS (EXCEL)
# ============================================

@superuser_required
@login_required
def registrar_usuarios(request):
    if request.method == 'POST':
        if 'archivo_excel' not in request.FILES:
            messages.error(request, "Por favor, selecciona un archivo Excel.")
            return redirect('registrar_usuarios')
            
        archivo = request.FILES['archivo_excel']
        try:
            df = pd.read_excel(archivo)
            df.columns = [str(col).strip() for col in df.columns]
            if 'Gerencia' in df.columns and 'Direccion' not in df.columns:
                df.rename(columns={'Gerencia': 'Direccion'}, inplace=True)
                
            required = ['Nombre', 'Apellido', 'usuario', 'Clave', 'Direccion']
            if not all(col in df.columns for col in required):
                messages.error(request, "Estructura incorrecta del Excel. Las columnas deben ser: Nombre, Apellido, usuario, Clave, Direccion")
                return redirect('registrar_usuarios')
            
            usuarios_creados = 0
            for _, row in df.iterrows():
                txt_nombre = str(row['Nombre']).strip()
                txt_apellido = str(row['Apellido']).strip()
                username_field = str(row['usuario']).strip()
                txt_clave = str(row['Clave']).strip()
                txt_direccion = str(row['Direccion']).strip()
                
                if not username_field or username_field.lower() == 'nan':
                    continue
                if not txt_clave or txt_clave.lower() == 'nan':
                    txt_clave = "Emvepro2026*"
                
                if not User.objects.filter(username=username_field).exists():
                    correo_automatico = generar_correo_institucional(txt_nombre, txt_apellido)
                    user = User.objects.create_user(
                        username=username_field, password=txt_clave, email=correo_automatico,
                        first_name=txt_nombre, last_name=txt_apellido
                    )
                    gerencia_obj, _ = Gerencia.objects.get_or_create(
                        nombre=txt_direccion, defaults={'descripcion': f'Gerencia de {txt_direccion}'}
                    )
                    
                    campos_reales = [f.name for f in Cliente._meta.get_fields()]
                    argumentos_validos = {
                        'nombre': f"{txt_nombre} {txt_apellido}",
                        'correo': correo_automatico,
                        'gerencia': gerencia_obj,
                        'usuario': user,
                        'telefono': 'N/A'
                    }
                    argumentos_validos = {k: v for k, v in argumentos_validos.items() if k in campos_reales}
                    Cliente.objects.create(**argumentos_validos)
                    usuarios_creados += 1
            
            messages.success(request, f"¡Carga masiva completada! Se registraron {usuarios_creados} usuarios.")
            return redirect('clientes')
        except Exception as e:
            messages.error(request, f"Error al procesar el archivo: {e}")
    return render(request, 'registrar_usuarios.html')

@superuser_required
@login_required
def exportar_usuarios_excel(request):
    clientes = Cliente.objects.all().order_by('nombre')
    datos = []
    for c in clientes:
        bits = c.nombre.split() if c.nombre else []
        primer_nombre = bits[0].upper() if len(bits) > 0 else "SIN NOMBRE"
        primer_apellido = bits[1].upper() if len(bits) > 1 else "---"
        correo_institucional = getattr(c, 'correo', 'N/A')
        datos.append({
            'Nombre': primer_nombre, 'Apellido': primer_apellido,
            'Nombre de Usuario': correo_institucional.split('@')[0] if correo_institucional != 'N/A' else 'N/A',
            'Correo Institucional': correo_institucional, 'Gerencia': c.gerencia.nombre if c.gerencia else 'Sin Asignar'
        })
    df = pd.DataFrame(datos)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Clientes EMVEPRO')
    output.seek(0)
    response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="clientes_emvepro_exportados.xlsx"'
    return response

@superuser_required
@login_required
def registrar_tickets_excel(request):
    if request.method == 'POST':
        if 'archivo_excel' not in request.FILES:
            messages.error(request, "Por favor, selecciona un archivo Excel.")
            return redirect('registrar_tickets_excel')
        archivo = request.FILES['archivo_excel']
        try:
            df = pd.read_excel(archivo)
            df.columns = [str(col).strip() for col in df.columns]
            tickets_importados = 0
            for _, row in df.iterrows():
                try:
                    correo_cliente = str(row['IDdelcliente']).strip()
                    cliente = Cliente.objects.filter(correo=correo_cliente).first()
                    cola_nombre = str(row['Cola']).strip()
                    servicio_nombre = str(row['Servicio']).strip()
                    
                    cola = Tickets_Colas.objects.filter(nombre__iexact=cola_nombre).first() or Tickets_Colas.objects.create(nombre=cola_nombre)
                    servicio = Tickets_Servicios.objects.filter(nombre__iexact=servicio_nombre).first() or Tickets_Servicios.objects.create(nombre=servicio_nombre)
                    
                    def limpiar_fecha(val):
                        if pd.isnull(val) or str(val).lower() == 'nan': return None
                        if isinstance(val, datetime): return timezone.make_aware(val) if timezone.is_naive(val) else val
                        try: return timezone.make_aware(datetime.strptime(str(val).split('(')[0].strip(), '%Y-%m-%d %H:%M:%S'))
                        except: return None

                    creado = limpiar_fecha(row.get('Creado')) or timezone.now()
                    cerrado_fecha = limpiar_fecha(row.get('Fechadecierre'))
                    estado_bool = str(row.get('Estado', '')).lower().strip() == 'cerrado'
                    usuario_asignado = cliente.usuario if (cliente and hasattr(cliente, 'usuario')) else request.user

                    argumentos_ticket = {
                        'titulo': str(row['Título']).strip(),
                        'descripcion': str(row.get('Descripción', 'Importación masiva')).strip(),
                        'fecha_creacion': creado,
                        'estado': 'cerrado' if estado_bool else 'nuevo',
                        'fecha_cierre': cerrado_fecha if estado_bool else None,
                        'cola': cola,
                        'servicio': servicio,
                        'usuario': usuario_asignado
                    }
                    
                    if 'descripcion_solucion' in [f.name for f in Tickets._meta.get_fields()]:
                        argumentos_ticket['descripcion_solucion'] = str(row.get('Solución', 'Resuelto en migración')).strip()
                        
                    Tickets.objects.create(**argumentos_ticket)
                    tickets_importados += 1
                except Exception as e:
                    print(f"Error importando ticket: {e}")
                    continue
            messages.success(request, f"Se importaron {tickets_importados} tickets de forma exitosa.")
            return redirect('ver_tikects')
        except Exception as e:
            messages.error(request, f"Error crítico: {e}")
    return render(request, 'registrar_tickets_excel.html')

# ============================================
# TRIAGE
# ============================================

@agente_or_superuser_required
def mesa_triage(request):
    tickets_nuevos = Tickets.objects.filter(Q(estado_triage='nuevo') | Q(estado_triage='triaje')).order_by('-fecha_creacion')
    stats = {
        'total_pendientes': Tickets.objects.filter(estado_triage__in=['nuevo', 'triaje']).count(),
        'por_prioridad': {
            'critica': Tickets.objects.filter(prioridad='critica', estado_triage='nuevo').count(),
            'urgente': Tickets.objects.filter(prioridad='urgente', estado_triage='nuevo').count(),
            'alta': Tickets.objects.filter(prioridad='alta', estado_triage='nuevo').count(),
        },
        'por_tipo': list(Tickets.objects.values('tipo').filter(estado_triage='nuevo').annotate(total=Count('id'))),
    }

    prioridad = request.GET.get('prioridad', '')
    tipo = request.GET.get('tipo', '')
    busqueda = request.GET.get('busqueda', '')

    if prioridad: tickets_nuevos = tickets_nuevos.filter(prioridad=prioridad)
    if tipo: tickets_nuevos = tickets_nuevos.filter(tipo=tipo)
    if busqueda:
        tickets_nuevos = tickets_nuevos.filter(Q(titulo__icontains=busqueda) | Q(descripcion__icontains=busqueda))

    paginator = Paginator(tickets_nuevos, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'mesa_triage.html', {
        'tickets': page_obj, 'stats': stats, 'prioridad_actual': prioridad, 'tipo_actual': tipo, 'busqueda': busqueda,
        'prioridades': [('baja', 'Baja'), ('media', 'Media'), ('alta', 'Alta'), ('urgente', 'Urgente'), ('critica', 'Crítica')],
        'tipos': [('bug', 'Bug/Error'), ('feature', 'Nueva Funcionalidad'), ('support', 'Soporte'), ('consulta', 'Consulta')]
    })

@agente_or_superuser_required
def procesar_triage(request, ticket_id):
    ticket = get_object_or_404(Tickets, id=ticket_id)
    
    if request.method == 'POST':
        ticket.tipo = request.POST.get('tipo')
        ticket.prioridad = request.POST.get('prioridad')
        ticket.estado_triage = request.POST.get('estado_triage', 'asignado')
        ticket.fecha_triage = datetime.now()
        
        if hasattr(request.user, 'agente'):
            ticket.agente_triage = request.user.agente

        agente_id = request.POST.get('agente_asignado')
        if agente_id:
            agente = Agentes.objects.get(id=agente_id)
            ticket.agente = agente  
        else:
            ticket.agente = None

        tiempo_estimado = request.POST.get('tiempo_estimado')
        ticket.tiempo_resolucion_estimado = int(tiempo_estimado) if tiempo_estimado else None
        ticket.tags = request.POST.get('tags', '')
        ticket.notas_triage = request.POST.get('notas_triage', '')

        ticket.save()
        messages.success(request, "Ticket procesado en triage exitosamente.")
        return redirect('mesa_triage')

    return render(request, 'procesar_triage.html', {
        'ticket': ticket, 
        'agentes': Agentes.objects.all(), 
        'colas': Tickets_Colas.objects.all(), 
        'servicios': Tickets_Servicios.objects.all(),
        'prioridades': [('baja', 'Baja'), ('media', 'Media'), ('alta', 'Alta'), ('urgente', 'Urgente'), ('critica', 'Crítica')],
        'estados_triage': [('nuevo', 'Nuevo'), ('triaje', 'En Triaje'), ('asignado', 'Asignado')]
    })

# ============================================
# GESTIÓN AVANZADA DE ROLES Y PERMISOS
# ============================================

@superuser_required
@login_required
def panel_permisos_roles(request):
    """Muestra el listado de usuarios del sistema con sus roles y estados."""
    busqueda = request.GET.get('buscar_usuario', '')
    filtro_rol = request.GET.get('filtro_rol', '')

  # 🔑 Se retira 'cliente' del select_related para evitar el choque de relaciones inversas
    usuarios = User.objects.select_related('agentes').all().order_by('-date_joined')

    if busqueda:
        usuarios = usuarios.filter(
            Q(username__icontains=busqueda) | 
            Q(first_name__icontains=busqueda) | 
            Q(last_name__icontains=busqueda)
        )
        
    if filtro_rol:
        if filtro_rol == 'is_superuser':
            usuarios = usuarios.filter(is_superuser=True)
        elif filtro_rol == 'is_agente':
            usuarios = usuarios.filter(agentes__isnull=False)
        elif filtro_rol == 'is_cliente':
            usuarios = usuarios.filter(cliente__isnull=False)

    paginator = Paginator(usuarios, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_roles_permisos.html', {
        'usuarios': page_obj,
        'buscar_usuario': busqueda,
        'filtro_rol': filtro_rol
    })

@superuser_required
@login_required
def actualizar_rol_usuario(request, usuario_id):
    """Procesa el cambio de rol y actualiza los accesos y banderas en la BD."""
    if request.method == 'POST':
        user_target = get_object_or_404(User, id=usuario_id)
        nuevo_rol = request.POST.get('nuevo_rol')
        estado_activo = request.POST.get('is_active') == 'on'

        user_target.is_active = estado_activo

        if nuevo_rol == 'superuser':
            user_target.is_superuser = True
            user_target.is_staff = True
        elif nuevo_rol == 'agente':
            user_target.is_superuser = False
            user_target.is_staff = True
            if not hasattr(user_target, 'agentes'):
                Agentes.objects.get_or_create(
                    usuario=user_target,
                    defaults={
                        'nombre_usuario': user_target.username,
                        'correo': user_target.email or f"{user_target.username}@emvepro.gob.ve"
                    }
                )
        elif nuevo_rol == 'cliente':
            user_target.is_superuser = False
            user_target.is_staff = False

        user_target.save()
        messages.success(request, f"Permisos de '{user_target.username}' actualizados correctamente.")
        
    return redirect('panel_permisos_roles')

# ============================================
# DISPARADOR DE CORREOS (GLOBAL)
# ============================================
def get_ssl_context():
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context

# 🛠️ MEJORA: Ahora acepta nombre y correo opcionales para notificar a agentes
def enviar_correo_profesional(ticket, asunto, mensaje_cuerpo, plantilla='email_ticket.html', destinatario_correo=None, destinatario_nombre=None):
    
    # 1. Definir a quién va el correo (Si no se especifica, va al dueño del ticket)
    correo_final = destinatario_correo or (ticket.usuario.email if ticket.usuario else None)
    nombre_final = destinatario_nombre or (ticket.usuario.first_name if ticket.usuario else "Usuario")

    if not correo_final:
        return

    # 2. Renderizamos tu plantilla HTML de EMVEPRO
    context_html = {
        'saludo': f"Hola {nombre_final},",
        'mensaje_cuerpo': mensaje_cuerpo,
        'ticket': ticket
    }
    
    html_content = render_to_string('emails/' + plantilla, context_html)

    # 3. Construcción del Mensaje
    msg = EmailMessage()
    msg['Subject'] = asunto
    msg['From'] = settings.EMAIL_HOST_USER
    msg['To'] = correo_final
    msg.add_alternative(html_content, subtype="html")

    # 4. Envío Seguro
    try:
        with smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT, context=get_ssl_context()) as server:
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"Error SMTP: {e}")

# --- CORREO AUTOMÁTICO AL CERRAR ---
def enviar_correo_estado(ticket):
    # ✅ CORRECCIÓN: Extraemos la solución real del ticket o ponemos un texto por defecto
    solucion = ticket.descripcion_solucion if hasattr(ticket, 'descripcion_solucion') and ticket.descripcion_solucion else 'No especificada'
    
    enviar_correo_profesional(
        ticket=ticket, 
        asunto=f"Ticket Cerrado: #{ticket.id} - {ticket.titulo}",
        mensaje_cuerpo=f"Tu requerimiento ha sido marcado como CERRADO.<br><br><b>Solución aplicada:</b><br>{solucion}"
    )

# --- CORREO MANUAL DESDE EL DETALLE ---
@agente_or_superuser_required
def enviar_respuesta_correo(request, tikect_id):
    ticket = get_object_or_404(Tickets, id=tikect_id)
    if request.method == 'POST':
        mensaje = request.POST.get('mensaje', '').strip()
        if mensaje:
            enviar_correo_profesional(
                ticket=ticket, 
                asunto=f"Respuesta de Soporte EMVEPRO - Ticket #{ticket.id}", 
                mensaje_cuerpo=mensaje
            )
            messages.success(request, "Respuesta enviada correctamente con formato profesional.")
    return redirect('detalle_tikect', tikect_id=ticket.id)