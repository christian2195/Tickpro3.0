from django.shortcuts import redirect
from functools import wraps
from tikects_app.models import Agentes

def solo_clientes_permitido(view_func):
    """
    Decorador para bloquear el acceso a agentes en vistas de clientes.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Si el usuario actual tiene un registro en Agentes, lo expulsamos al soporte
        if Agentes.objects.filter(usuario=request.user).exists():
            return redirect('pagina_principal')
        return view_func(request, *args, **kwargs)
    return _wrapped_view