from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from django.core.exceptions import PermissionDenied

class AgenteRequiredMixin:
    """Mixin de seguridad: Bloquea el acceso si el usuario no es resolutor."""
    def dispatch(self, request, *args, **kwargs):
        # 🔑 Candado unificado: Evalúa superusuario o relación inversa del modelo Agentes
        if not request.user.is_superuser and not hasattr(request.user, 'agente') and not hasattr(request.user, 'Agentes'):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

class InicioSesionView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('enrutador_inicial')  # ✨ Corregido
        return render(request, 'inicio_sesion_admin.html')

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('clave')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('enrutador_inicial')  # ✨ Corregido
        return render(request, 'inicio_sesion_admin.html', {'error': 'Usuario o contraseña incorrecta'})

class CerrarSesionView(LoginRequiredMixin, View):
    def get(self, request):
        logout(request)
        return redirect('/')

class EnrutadorInicialView(LoginRequiredMixin, View):
    """Distribuye el tráfico de login de manera limpia e inmune a bucles."""
    def get(self, request):
        # 🛡️ Aduana de tráfico: Si es soporte/admin va a su panel, si no, al portal de clientes
        if request.user.is_superuser or hasattr(request.user, 'agente') or hasattr(request.user, 'Agentes'):
            return redirect('soporte:dashboard')
        return redirect('clientes:dashboard')