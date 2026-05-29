from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from tikects_app.views import core, clientes, agentes, admin

try:
    from tikects_app import vistas_legado as v_viejas
except ImportError:
    v_viejas = None

# 🛡️ ESCUDO PROTECTOR ANTI-CAÍDAS
def mapear_vista(nombre_funcion):
    if v_viejas and hasattr(v_viejas, nombre_funcion):
        func = getattr(v_viejas, nombre_funcion)
        if callable(func) and not isinstance(func, type):
            return func
    return core.EnrutadorInicialView.as_view()

urlpatterns = [
    # 🔐 ENTORNO CORE / AUTENTICACIÓN
    path('', core.InicioSesionView.as_view(), name='inicio'),
    path('logout/', core.CerrarSesionView.as_view(), name='cerrar_sesion'),
    path('redireccionar/', core.EnrutadorInicialView.as_view(), name='enrutador_inicial'),

    # 👤 ENTORNO PORTAL DE CLIENTES
    path('portal/', include(([
        path('inicio/', clientes.DashboardClientesView.as_view(), name='dashboard'),
    ], 'clientes'))),

    # 🛠️ ENTORNO DE SOPORTE / RESOLUTORES (Namespaces)
    path('soporte/', include(([
        path('dashboard/', agentes.DashboardSoporteView.as_view(), name='dashboard'),
        path('triage/', mapear_vista('mesa_triage'), name='triage'),
    ], 'soporte'))),
    
    # Registro plano para que 'mesa_triage' sea encontrado globalmente
    path('mesa-triage/', mapear_vista('mesa_triage'), name='mesa_triage'),
    
    # 🔄 ALIAS DE COMPATIBILIDAD CON PLANTILLAS HTML
    path('soporte/main/', agentes.DashboardSoporteView.as_view(), name='pagina_principal'),
    path('portal/main/', clientes.DashboardClientesView.as_view(), name='pagina_principal_clientes'),

    # 📊 BOTONES OPERATIVOS
    path('configuracion/', admin.PanelConfiguracionView.as_view(), name='configuracion'),
    path('estadisticas/', mapear_vista('tikects_estadisticas'), name='estadisticas'),
    path('tikects/crear_tikects', mapear_vista('crear_tikects'), name='crear_tikects'),
    path('tikects/ver_todos/', mapear_vista('ver_tikects'), name='ver_tikects'),

    # ALIAS DE SERVICIOS Y COLAS
    path('configuracion/servicios/', mapear_vista('tikects_servicios'), name='tikects_servicios'),
    path('configuracion/servicios/crear/', mapear_vista('tikects_servicios_crear'), name='tikects_servicios_crear'),
    path('configuracion/servicios/editar/<int:servicio_id>/', mapear_vista('editar_servicios'), name='editar_servicio'),
    path('configuracion/servicios/eliminar/<int:servicio_id>/', mapear_vista('eliminar_servicio'), name='eliminar_servicio'),

    path('configuracion/colas/', mapear_vista('tikects_colas'), name='tikects_colas'),
    path('configuracion/colas/crear/', mapear_vista('tikects_colas_crear'), name='tikects_colas_crear'),
    path('configuracion/colas/editar/<int:cola_id>/', mapear_vista('editar_cola'), name='editar_cola'),
    path('configuracion/colas/eliminar/<int:cola_id>/', mapear_vista('eliminar_cola'), name='eliminar_cola'),

    path('configuracion/respuestas/', mapear_vista('tikects_respuestas_automaticas'), name='tikects_respuestas_automaticas'),
    path('configuracion/respuestas/crear/', mapear_vista('tikects_respuestas_automaticas_crear'), name='tikects_respuestas_automaticas_crear'),
    path('configuracion/respuestas/eliminar/<int:respuesta_id>/', mapear_vista('eliminar_respuesta_automatica'), name='eliminar_respuesta_automatica'),

    # MANTENIMIENTOS CRUD: CLIENTES, GRUPOS Y GERENCIAS
    path('configuracion/registrar/', mapear_vista('registrar_usuarios'), name='registrar_usuarios'),
    path('inicio/clientes/ver/', mapear_vista('clientes'), name='ver_cliente'),
    path('inicio/clientes/crear/', mapear_vista('crear_clientes'), name='crear_cliente'),
    path('usuarios/clientes_grupos/', mapear_vista('usuarios_clientes_grupos'), name='usuarios_clientes_grupos'),
    path('usuario/clientes_grupos/crear/', mapear_vista('usuarios_clientes_grupos_crear'), name='crear_grupo'),
    path('clientes/gerencias/', mapear_vista('ver_gerencias'), name='ver_gerencias'),
    path('clientes/gerencias/crear/', mapear_vista('crear_gerencia'), name='crear_gerencia'),
    path('admin-panel/clientes-base/', mapear_vista('clientes'), name='clientes'),

    # MANTENIMIENTOS CRUD: AGENTES Y GRUPOS
    path('usuarios/agentes', mapear_vista('usuarios_agentes'), name='usuarios_agentes'),
    path('usuarios/agentes/crear', mapear_vista('usuarios_agentes_crear'), name='usuarios_agentes_crear'),
    path('usuarios/grupos_agentes', mapear_vista('usuarios_grupos_agentes'), name='usuarios_grupos_agentes'),
    path('usuarios/grupos_agentes/crear', mapear_vista('usuarios_grupos_agentes_crear'), name='usuarios_grupos_agentes_crear'),
    path('usuarios/grupos_agentes/agentes', mapear_vista('usuarios_por_grupos_agentes'), name='usuarios_por_grupos_agentes'),
    path('usuarios/grupos_agentes/agregar', mapear_vista('usuarios_grupos_agentes_agregar'), name='usuarios_grupos_agentes_agregar'),
    path('grupos_agentes/eliminar/<int:grupo_id>/', mapear_vista('usuariops_grupo_agentes_eliminar'), name='eliminar_grupo_agentes'),
    path('grupos_agentes/eliminar_del_grupo/<int:grupo_agente_id>/', mapear_vista('eliminar_agente_de_grupo'), name='eliminar_agente_de_grupo'),

    path('ver-agentes-genericos/', mapear_vista('ver_agentes_genericos'), name='ver_agentes_genericos'),
    path('usuario/agente_generico/', mapear_vista('agente_generico'), name='agente_generico'),
    path('asignaciones/eliminar/<int:asignacion_id>/', mapear_vista('eliminar_asignacion'), name='eliminar_asignacion'),
    path('usuarios/permisos', mapear_vista('panel_permisos_roles'), name='panel_permisos_roles'),
    path('usuarios/permisos/actualizar/<int:usuario_id>/', mapear_vista('actualizar_rol_usuario'), name='actualizar_rol_usuario'),

    # IMPORTACIÓN Y EXPORTACIÓN MASIVA
    path('registrar-tickets/', mapear_vista('registrar_tickets_excel'), name='registrar_tickets'),
    path('exportar_tikects_excel/', mapear_vista('exportar_tikects_excel'), name='exportar_tikects_excel'),
    path('exportar_tikects_pdf/', mapear_vista('exportar_tikects_pdf'), name='exportar_tikects_pdf'),
    path('clientes/exportar-excel/', mapear_vista('exportar_usuarios_excel'), name='exportar_excel'),

    # 📑 ACCIONES DINÁMICAS Y FLUJOS CON IDs
    path('tikects/detalles/<int:tikect_id>/', mapear_vista('detalle_tikect'), name='detalle_tikect'),
    path('tikects/<int:tikect_id>/cerrar/', mapear_vista('cerrar_tikect'), name='cerrar_tikect'),
    path('procesar-triage/<int:ticket_id>/', mapear_vista('procesar_triage'), name='procesar_triage'),
    
    path('tikects/ver_todos/cerrados/', mapear_vista('ver_tikects_cerrados'), name='ver_tikects_cerrados'),
    path('tikects/ver_todos/abiertos/', mapear_vista('ver_tikects_abiertos'), name='ver_tikects_abiertos'),
    
    # 🔄 RUTAS DE BANDEJA DE AGENTES CORREGIDAS
    path('tikects/asignados_agentes/', mapear_vista('ver_tikects_asignados_agentes'), name='ver_tikects_asignados_agentes'),
    path('tikects/asignados_agentes/abiertos/', mapear_vista('ver_tikects_asignados_agentes_abiertos'), name='ver_tikects_asignados_agentes_abiertos'),
    path('tikects/asignados_agentes/cerrados/', mapear_vista('ver_tikects_asignados_agentes_cerrados'), name='ver_tikects_asignados_agentes_cerrados'),
    
    path('reasignar_tikect/<int:tikect_id>/', mapear_vista('reasignar_tikect'), name='reasignar_tikect'),
    path('clientes/editar/<int:cliente_id>/', mapear_vista('editar_cliente'), name='editar_cliente'),
    path('clientes/eliminar/<int:cliente_id>/', mapear_vista('eliminar_cliente'), name='eliminar_cliente'),
    path('gerencias/editar/<int:gerencia_id>/', mapear_vista('editar_gerencia'), name='editar_gerencia'),
    path('gerencias/eliminar/<int:gerencia_id>/', mapear_vista('eliminar_gerencia'), name='eliminar_gerencia'),
    path('agentes/editar/<int:agente_id>/', mapear_vista('editar_agente'), name='editar_agente'),
    path('agentes/eliminar/<int:agente_id>/', mapear_vista('eliminar_agente'), name='eliminar_agente'),

    path('tikects/cliente_ver_mis_tikects/', mapear_vista('ver_mis_tikects'), name='ver_mis_tikects'),
    path('tikects/mis_abiertos/', mapear_vista('ver_mis_tikects_abiertos'), name='ver_mis_tikects_abiertos'),
    path('tikects/mis_cerrados/', mapear_vista('ver_mis_tikects_cerrados'), name='ver_mis_tikects_cerrados'),
    path('tikects/crear_cliente_tikects/', mapear_vista('crear_tikects_clientes'), name='crear_tikects_clientes'),
    path('path/to/your/notification/api/', mapear_vista('check_notifications'), name='check_notifications'),

    # 🔑 RECUPERACIÓN DE CONTRASEÑA
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt'
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
]