from django.urls import path, include
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
