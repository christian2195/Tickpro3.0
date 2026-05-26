#!/usr/bin/env python3
import os
import shutil

# Colores para la terminal de Linux
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def crear_estructura_modular():
    print(f"{BLUE}=================================================={RESET}")
    print(f"{BLUE}   REESTRUCTURACIÓN DE ARQUITECTURA TICKPRO 2.0   {RESET}")
    print(f"{BLUE}=================================================={RESET}\n")

    base_dir = "tikects_app"
    views_dir = os.path.join(base_dir, "views")

    if not os.path.exists(base_dir):
        print(f"❌ Ejecuta el script en el directorio raíz: /var/www/html/Tickpro2.0/")
        return

    # 1. Crear el paquete views/
    os.makedirs(views_dir, exist_ok=True)
    print(f"📁 Creando directorio modular de vistas en: {YELLOW}{views_dir}{RESET}")

    # 2. Crear archivo __init__.py para el paquete
    with open(os.path.join(views_dir, "__init__.py"), "w", encoding="utf-8") as f:
        f.write("# Paquete de vistas modulares para Tickpro 2.0\n")

    # 3. MÓDULO CORE: Autenticación, Login, Logout y Mixins de Seguridad
    core_content = """from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from django.core.exceptions import PermissionDenied

class AgenteRequiredMixin:
    \"\"\"Mixin de seguridad: Bloquea el acceso si el usuario no es resolutor.\"\"\"
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser and not hasattr(request.user, 'agente') and not hasattr(request.user, 'Agentes'):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

class InicioSesionView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('core:enrutador_inicial')
        return render(request, 'inicio_sesion_admin.html')

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('clave')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('core:enrutador_inicial')
        return render(request, 'inicio_sesion_admin.html', {'error': 'Usuario o contraseña incorrecta'})

class CerrarSesionView(LoginRequiredMixin, View):
    def get(self, request):
        logout(request)
        return redirect('/')

class EnrutadorInicialView(LoginRequiredMixin, View):
    \"\"\"Distribuye el tráfico de login de manera limpia e inmune a bucles.\"\"\"
    def get(self, request):
        if request.user.is_superuser or hasattr(request.user, 'agente') or hasattr(request.user, 'Agentes'):
            return redirect('soporte:dashboard')
        return redirect('clientes:dashboard')
"""
    with open(os.path.join(views_dir, "core.py"), "w", encoding="utf-8") as f:
        f.write(core_content)
    print(f"📄 Módulo {GREEN}core.py{RESET} generado con éxito.")

    # 4. MÓDULO CLIENTES: Operaciones exclusivas del solicitante
    clientes_content = """from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, View
from django.contrib import messages
from tikects_app.models import Tickets, Tickets_Servicios, Tickets_Colas
from datetime import datetime

class DashboardClientesView(LoginRequiredMixin, ListView):
    model = Tickets
    template_name = 'pagina_principal_clientes.html'
    context_object_name = 'ultimos_tickets'

    def get_queryset(self):
        return Tickets.objects.filter(usuario=self.request.user).order_by('-fecha_creacion')[:5]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['total_mis_tickets'] = Tickets.objects.filter(usuario=user).count()
        context['mis_tickets_abiertos'] = Tickets.objects.filter(usuario=user).exclude(estado='cerrado').count()
        context['mis_tickets_cerrados'] = Tickets.objects.filter(usuario=user, estado='cerrado').count()
        context['now'] = datetime.now()
        return context
"""
    with open(os.path.join(views_dir, "clientes.py"), "w", encoding="utf-8") as f:
        f.write(clientes_content)
    print(f"📄 Módulo {GREEN}clientes.py{RESET} generado con éxito.")

    # 5. MÓDULO AGENTES: Cola unificada de resolutores y mesa de Triage
    agentes_content = """from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, View
from django.db.models import Q, Count
from tikects_app.models import Tickets, Agentes, Notificaciones
from .core import AgenteRequiredMixin
from datetime import datetime

class DashboardSoporteView(LoginRequiredMixin, AgenteRequiredMixin, ListView):
    model = Tickets
    template_name = 'pagina_principal.html'
    context_object_name = 'ultimos_tickets'

    def get_queryset(self):
        return Tickets.objects.all().order_by('-fecha_creacion')[:5]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['agente'] = Agentes.objects.filter(usuario=self.request.user).first()
        context['total_tickets'] = Tickets.objects.count()
        context['tickets_abiertos'] = Tickets.objects.exclude(estado='cerrado').count()
        context['tickets_cerrados'] = Tickets.objects.filter(estado__iexact='cerrado').count()
        context['total_agentes'] = Agentes.objects.count()
        context['now'] = datetime.now()
        return context

class MesaTriageView(LoginRequiredMixin, AgenteRequiredMixin, ListView):
    model = Tickets
    template_name = 'mesa_triage.html'
    context_object_name = 'tickets'
    paginate_by = 20

    def get_queryset(self):
        queryset = Tickets.objects.filter(Q(estado_triage='nuevo') | Q(estado_triage='triaje')).order_by('-fecha_creacion')
        prioridad = self.request.GET.get('prioridad', '')
        tipo = self.request.GET.get('tipo', '')
        if prioridad: queryset = queryset.filter(prioridad=prioridad)
        if tipo: queryset = queryset.filter(tipo=tipo)
        return queryset
"""
    with open(os.path.join(views_dir, "agentes.py"), "w", encoding="utf-8") as f:
        f.write(agentes_content)
    print(f"📄 Módulo {GREEN}agentes.py{RESET} generado con éxito.")

    # 6. MÓDULO ADMIN: Estadísticas avanzadas e infraestructura
    admin_content = """from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib.auth.decorators import user_passes_test
from .core import AgenteRequiredMixin

class PanelConfiguracionView(LoginRequiredMixin, AgenteRequiredMixin, TemplateView):
    template_name = 'configuracion.html'
"""
    with open(os.path.join(views_dir, "admin.py"), "w", encoding="utf-8") as f:
        f.write(admin_content)
    print(f"📄 Módulo {GREEN}admin.py{RESET} generado con éxito.")

    # 7. ENRUTADOR DE URLS MODULAR (urls_modular.py)
    urls_content = """from django.urls import path, include
from tikects_app.views import core, clientes, agentes, admin

urlpatterns = [
    # Espacio Base / Core de la Aplicación
    path('', core.InicioSesionView.as_view(), name='inicio'),
    path('logout/', core.CerrarSesionView.as_view(), name='cerrar_sesion'),
    path('redireccionar/', core.EnrutadorInicialView.as_view(), name='enrutador_inicial'),

    # Espacio reservado para los Clientes
    path('portal/', include(([
        path('inicio/', clientes.DashboardClientesView.as_view(), name='dashboard'),
    ], 'clientes'))),

    # Espacio reservado para los Resolutores (Soporte Técnico)
    path('soporte/', include(([
        path('dashboard/', agentes.DashboardSoporteView.as_view(), name='dashboard'),
        path('triage/', agentes.MesaTriageView.as_view(), name='triage'),
    ], 'soporte'))),
]
"""
    with open(os.path.join(base_dir, "urls_modular.py"), "w", encoding="utf-8") as f:
        f.write(urls_content)
    print(f"\n🗺️  {BLUE}Mapa de enrutamiento guardado en: tikects_app/urls_modular.py{RESET}")
    print(f"\n✅ {GREEN}¡Reestructuración completada de forma limpia y exitosa!{RESET}")

if __name__ == '__main__':
    crear_estructura_modular()