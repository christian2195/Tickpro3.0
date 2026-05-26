#!/usr/bin/env python3
import os
import shutil

# Colores para la consola de Linux
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def crear_respaldo(ruta):
    """Genera un archivo de respaldo con sufijo .seguridad"""
    ruta_bak = ruta + ".seguridad"
    if os.path.exists(ruta):
        shutil.copyfile(ruta, ruta_bak)
        print(f"💾 Respaldo de seguridad creado: {BLUE}{os.path.basename(ruta_bak)}{RESET}")

def parchear_views():
    ruta_views = "tikects_app/views.py"
    if not os.path.exists(ruta_views):
        print("❌ Error: No se encuentra tikects_app/views.py")
        return False

    crear_respaldo(ruta_views)
    
    with open(ruta_views, 'r', encoding='utf-8') as f:
        lineas = f.readlines()

    modificado = False
    nueva_salida = []
    i = 0
    while i < len(lineas):
        linea = lineas[i]
        
        # Detectamos cuando se valida si es un cliente para redirigir
        if "hasattr(user, 'cliente')" in linea or "hasattr(request.user, 'cliente')" in linea:
            print(f"⚙️  {BLUE}Corrigiendo condicional de redirección del Login en views.py...{RESET}")
            # Reemplazamos la lógica vieja por la verificación estricta de privilegios de Agente/Admin
            linea = linea.replace("hasattr(user, 'cliente')", "not (user.is_superuser or hasattr(user, 'agentes'))")
            linea = linea.replace("hasattr(request.user, 'cliente')", "not (request.user.is_superuser or hasattr(request.user, 'agentes'))")
            modificado = True
        
        nueva_salida.append(linea)
        i += 1

    if modificado:
        with open(ruta_views, 'w', encoding='utf-8') as f:
            f.writelines(nueva_salida)
        print(f"✅ {GREEN}views.py blindado correctamente.{RESET}")
    else:
        print(f"ℹ️  {YELLOW}views.py ya cuenta con el filtro de redirección optimizado o requiere cambio manual.{RESET}")
    return modificado

def blindar_plantilla_html():
    ruta_html = "tikects_app/templates/pagina_principal.html"
    if not os.path.exists(ruta_html):
        print("❌ Error: No se encuentra tikects_app/templates/pagina_principal.html")
        return False

    crear_respaldo(ruta_html)

    with open(ruta_html, 'r', encoding='utf-8') as f:
        contenido = f.read()

    # Si ya tiene el candado puesto, no hacemos nada
    if "{% if user.is_superuser or user.agentes %}" in contenido:
        print(f"ℹ️  {YELLOW}La plantilla pagina_principal.html ya se encuentra blindada de forma nativa.{RESET}")
        return False

    # Buscamos el inicio del bloque de contenido para inyectar el candado de seguridad
    if "{% block content %}" in contenido:
        print(f"⚙️  {BLUE}Inyectando etiquetas de seguridad estructurales en la plantilla...{RESET}")
        
        # El candado se abre justo al iniciar el bloque de contenido
        reemplazo_inicio = "{% block content %}\n{% if user.is_superuser or user.agentes %}"
        contenido = contenido.replace("{% block content %}", reemplazo_inicio)
        
        # El candado se cierra justo antes de terminar el bloque de contenido con un redireccionador JS de respaldo
        bloque_seguridad_cierre = """
{% else %}
<div class="container-fluid px-4 mt-5">
    <div class="alert alert-danger text-center shadow-sm p-4">
        <h4 class="alert-heading fw-bold"><i class="fas fa-exclamation-triangle me-2"></i>Acceso Restringido</h4>
        <p class="mb-0">Tu cuenta no posee un perfil resolutor asignado. Redirigiéndote a tu portal de requerimientos...</p>
    </div>
</div>
<script type="text/javascript">
    setTimeout(function(){
        window.location.href = "{% url 'pagina_principal_clientes' %}";
    }, 1500);
</script>
{% endif %}
{% endblock %}"""
        
        contenido = contenido.replace("{% endblock %}", bloque_seguridad_cierre)
        
        with open(ruta_html, 'w', encoding='utf-8') as f:
            f.write(contenido)
        print(f"✅ {GREEN}pagina_principal.html blindada exitosamente.{RESET}")
        return True
    else:
        print("❌ No se encontró la etiqueta {% block content %} en la plantilla.")
        return False

if __name__ == '__main__':
    print(f"{BLUE}=================================================={RESET}")
    print(f"{BLUE}      PARCHE DE SEGURIDAD PARA CLIENTES (TICKPRO) {RESET}")
    print(f"{BLUE}=================================================={RESET}\\n")
    
    # Forzar la ejecución en el directorio actual
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    v_mod = parchear_views()
    h_mod = blindar_plantilla_html()
    
    if v_mod or h_mod:
        print(f"\\n{GREEN}¡Filtros aplicados con éxito! Procediendo a reiniciar servicios...{RESET}\\n")
    else:
        print(f"\\n{YELLOW}No se requirieron modificaciones estructurales.{RESET}\\n")