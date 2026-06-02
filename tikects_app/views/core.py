from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import View

class AgenteRequiredMixin(UserPassesTestMixin):
    """Mixin de seguridad: Bloquea el acceso si el usuario no es resolutor."""
    def test_func(self):
        # 1. Si es superusuario, lo dejamos pasar siempre.
        if self.request.user.is_superuser:
            return True
            
        # 2. Si es agente normal, verificamos en la base de datos (Método infalible).
        from tikects_app.models import Agentes
        return Agentes.objects.filter(usuario=self.request.user).exists()

class InicioSesionView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('enrutador_inicial')
        return render(request, 'inicio_sesion_admin.html')

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('clave')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('enrutador_inicial')
        return render(request, 'inicio_sesion_admin.html', {'error': 'Usuario o contraseña incorrecta'})

class CerrarSesionView(LoginRequiredMixin, View):
    def get(self, request):
        logout(request)
        return redirect('/')

class EnrutadorInicialView(LoginRequiredMixin, View):
    """Distribuye el tráfico de login de manera limpia e inmune a bucles."""
    def get(self, request):
        # 🛡️ Aduana de tráfico: Importamos Agentes aquí adentro para evitar error 500 por importación circular
        from tikects_app.models import Agentes
        
        # Si es superusuario o está registrado en la tabla Agentes, va a Soporte
        if request.user.is_superuser or Agentes.objects.filter(usuario=request.user).exists():
            return redirect('soporte:dashboard')
            
        # Si no, es un cliente y va a su propio portal
        return redirect('clientes:dashboard')