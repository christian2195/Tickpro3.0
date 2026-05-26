#!/usr/bin/env python3
import os
import shutil

# Colores para la consola de Linux
GREEN = "\033[92m"
BLUE = "\033[94m"
RED = "\033[91m"
RESET = "\033[0m"

def reparar_plantilla():
    ruta_html = "tikects_app/templates/pagina_principal.html"
    ruta_backup = ruta_html + ".seguridad"
    
    print(f"{BLUE}=================================================={RESET}")
    print(f"{BLUE}   REPARADOR EXACTO DE SINTAXIS: TICKPRO 2.0      {RESET}")
    print(f"{BLUE}=================================================={RESET}\n")

    # 1. Recuperar el archivo limpio de respaldo si existe
    if os.path.exists(ruta_backup):
        shutil.copyfile(ruta_backup, ruta_html)
        print(f"🔄 {GREEN}Restaurado el archivo original limpio desde el respaldo.{RESET}")
    else:
        if not os.path.exists(ruta_html):
            print(f"❌ {RED}Error: No se encontró {ruta_html}{RESET}")
            return
        # Si no existía respaldo, lo creamos justo antes del proceso
        shutil.copyfile(ruta_html, ruta_backup)

    with open(ruta_html, 'r', encoding='utf-8') as f:
        contenido = f.read()

    # Validar que contenga los tags mínimos estructurales
    if "{% block content %}" not in contenido or "{% endblock %}" not in contenido:
        print(f"❌ {RED}Error: Estructura base HTML inválida para el parseo.{RESET}")
        return

    # 2. Reconstrucción quirúrgica de bloques balanceados
    partes = contenido.split("{% block content %}")
    cabecera = partes[0] + "{% block content %}\n{% if user.is_superuser or user.agents %}"
    
    resto = partes[1].rsplit("{% endblock %}", 1)
    cuerpo_interno = resto[0]
    
    # Generamos la sección alternativa que bloqueará a usuarios clientes
    pie_archivo = "{% else %}\n"
    pie_archivo += "<div class=\"container-fluid px-4 mt-5\">\n"
    pie_archivo += "    <div class=\"alert alert-danger text-center shadow-sm p-4\">\n"
    pie_archivo += "        <h4 class=\"alert-heading fw-bold\"><i class=\"fas fa-exclamation-triangle me-2\"></i>Acceso Restringido</h4>\n"
    pie_archivo += "        <p class=\"mb-0\">Tu cuenta no posee un perfil resolutor asignado. Redirigiéndote a tu portal de requerimientos...</p>\n"
    pie_archivo += "    </div>\n"
    pie_archivo += "</div>\n"
    pie_archivo += "<script type=\"text/javascript\">\n"
    pie_archivo += "    setTimeout(function(){\n"
    pie_archivo += "        window.location.href = \"{% url 'pagina_principal_clientes' %}\";\n"
    pie_archivo += "    }, 1200);\n"
    pie_archivo += "</script>\n"
    pie_archivo += "{% endif %}\n"
    pie_archivo += "{% endblock %}" + resto[1]

    # Guardar la combinación perfecta final
    with open(ruta_html, 'w', encoding='utf-8') as f:
        f.write(cabecera + cuerpo_interno + pie_archivo)

    print(f"✅ {GREEN}Plantilla pagina_principal.html blindada de forma exacta sin errores de sintaxis.{RESET}")

if __name__ == '__main__':
    reparar_plantilla()