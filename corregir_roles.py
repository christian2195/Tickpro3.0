#!/usr/bin/env python3
import os
import shutil

# Colores para la consola
GREEN = "\033[92m"
BLUE = "\033[94m"
RESET = "\033[0m"

def crear_respaldo(ruta):
    """Crea una copia de seguridad .bak si no existe una ya."""
    ruta_bak = ruta + ".bak"
    if os.path.exists(ruta) and not os.path.exists(ruta_bak):
        shutil.copyfile(ruta, ruta_bak)
        print(f"💾 Respaldo creado: {BLUE}{os.path.basename(ruta_bak)}{RESET}")

def corregir_views():
    ruta_views = "tikects_app/views.py"
    if not os.path.exists(ruta_views):
        return

    crear_respaldo(ruta_views)
    
    with open(ruta_views, 'r', encoding='utf-8') as f:
        contenido = f.read()

    # 1. Corregir el select_related en el query de usuarios
    viejos_cambios = [
        ("select_related('agente', 'cliente')", "select_related('agentes')"),
        ("filtro_rol == 'is_agente':\n            usuarios = usuarios.filter(agente__isnull=False)", 
         "filtro_rol == 'is_agente':\n            usuarios = usuarios.filter(agentes__isnull=False)"),
        ("hasattr(user_target, 'agente')", "hasattr(user_target, 'agentes')")
    ]

    modificado = False
    for viejo, nuevo in viejos_cambios:
        if viejo in contenido:
            contenido = contenido.replace(viejo, nuevo)
            modificado = True

    if modificado:
        with open(ruta_views, 'w', encoding='utf-8') as f:
            f.write(contenido)
        print(f"✅ {GREEN}views.py corregido exitosamente.{RESET}")
    else:
        print("ℹ views.py ya se encuentra actualizado.")

def corregir_html():
    ruta_html = "tikects_app/templates/admin_roles_permisos.html"
    if not os.path.exists(ruta_html):
        return

    crear_respaldo(ruta_html)

    with open(ruta_html, 'r', encoding='utf-8') as f:
        contenido = f.read()

    # 2. Corregir las instancias de u.agente por u.agentes en el HTML
    viejos_cambios_html = [
        ("{% elif u.agente %}", "{% elif u.agentes %}"),
        ("{% if u.agente and not u.is_superuser %}", "{% if u.agentes and not u.is_superuser %}"),
        ("{% if not u.agente and not u.is_superuser %}", "{% if not u.agentes and not u.is_superuser %}")
    ]

    modificado = False
    for viejo, nuevo in viejos_cambios_html:
        if viejo in contenido:
            contenido = contenido.replace(viejo, nuevo)
            modificado = True

    if modificado:
        with open(ruta_html, 'w', encoding='utf-8') as f:
            f.write(contenido)
        print(f"✅ {GREEN}admin_roles_permisos.html corregido exitosamente.{RESET}")
    else:
        print("ℹ admin_roles_permisos.html ya se encuentra actualizado.")

if __name__ == "__main__":
    print(f"{BLUE}=================================================={RESET}")
    print(f"{BLUE}      CORRECTOR AUTOMÁTICO DE RELACIONES           {RESET}")
    print(f"{BLUE}=================================================={RESET}\n")
    
    # Asegurar que se ejecuta en la raíz del proyecto
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    corregir_views()
    corregir_html()
    print(f"\n{GREEN}¡Proceso terminado! Sincronizando con producción...{RESET}\n")