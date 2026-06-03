from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.contrib.auth.decorators import login_required, permission_required
from tikects_app.models import Agentes, Tickets_Respuestas_Automaticas
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

# Ajustamos los imports según el nombre correcto de tu modelo
from tikects_app.models import Tickets_Respuestas_Automaticas, Agentes, Agentes_Por_Grupos

def lista_respuestas(request):
    respuestas = Tickets_Respuestas_Automaticas.objects.all()
    return render(request, 'tickets_repuesta_automaticas.html', {'respuestas': respuestas})

def crear_respuesta(request):
    if request.method == 'POST':
        Tickets_Respuestas_Automaticas.objects.create(
            nombre=request.POST.get('nombre'),
            asunto=request.POST.get('asunto'),
            cuerpo=request.POST.get('cuerpo')
        )
        messages.success(request, "Respuesta automática creada exitosamente.")
        return redirect('tickets_repuesta_automaticas_lista')
    
    return render(request, 'tickets_respuesta_automaticas_crear.html')

def eliminar_respuesta_automatica(request, respuesta_id):
    respuesta = get_object_or_404(Tickets_Respuestas_Automaticas, id=respuesta_id)
    respuesta.delete()
    messages.success(request, "Respuesta eliminada correctamente.")
    return redirect('tickets_repuesta_automaticas_lista')

def enviar_respuesta_automatica(ticket, respuesta_automatica):
    context = {
        'saludo': f"Hola {ticket.cliente.nombre},",
        'mensaje_cuerpo': respuesta_automatica.cuerpo,
        'ticket': ticket
    }
    
    html_message = render_to_string('emails/email_ticket.html', context)
    
    send_mail(
        subject=respuesta_automatica.asunto,
        message=respuesta_automatica.cuerpo,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[ticket.cliente.correo],
        html_message=html_message,
        fail_silently=False,
    )

def gestionar_permisos(request):
    # Traemos los agentes con su usuario relacionado
    agentes = Agentes.objects.select_related('usuario').all()
    # Traemos los grupos
    grupos = Group.objects.prefetch_related('user_set').all()
    
    context = {
        'agentes': agentes,
        'grupos': grupos,
    }
    return render(request, 'gestion_permisos.html', context)

def editar_agente(request, agente_id):
    agente = get_object_or_404(Agentes, id=agente_id)
    
    if request.method == 'POST':
        # 1. Obtener los datos del formulario
        rol = request.POST.get('rol_sistema')
        is_active = request.POST.get('is_active') == 'on'  # Checkbox devuelve 'on' si está marcado
        
        # 2. Asignar los permisos según la selección
        if rol == 'superusuario':
            agente.usuario.is_superuser = True
            agente.usuario.is_staff = True
        elif rol == 'staff':
            agente.usuario.is_superuser = False
            agente.usuario.is_staff = True
        else: # rol == 'agente'
            agente.usuario.is_superuser = False
            agente.usuario.is_staff = False
            
        # 3. Asignar el estado de la cuenta (Activo/Inactivo)
        agente.usuario.is_active = is_active
        
        # 4. Guardar los cambios en el modelo User de Django
        agente.usuario.save()
        
        # 5. Enviar mensaje de éxito y redireccionar
        messages.success(request, f"Los permisos de {agente.usuario.username} fueron actualizados correctamente.")
        return redirect('panel_permisos_roles')
        
    return render(request, 'editar_agente.html', {'agente': agente})