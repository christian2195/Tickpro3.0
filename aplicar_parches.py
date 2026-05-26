import os

# Rutas de tus archivos
base_path = '/var/www/html/Tickpro2.0/tikects_app/templates/base.html'
admin_path = '/var/www/html/Tickpro2.0/tikects_app/templates/admin_roles_permisos.html'

def parchar_base():
    with open(base_path, 'r') as f:
        content = f.read()
    
    # Reemplazo seguro para el menú de Triage
    target = '<a class="nav-link" href="{% url \'soporte:triage\' %}">'
    replacement = '<a class="nav-link" href="/soporte/triage/">'
    
    if target in content:
        new_content = content.replace(target, replacement)
        with open(base_path, 'w') as f:
            f.write(new_content)
        print("✅ base.html parcheado correctamente.")
    else:
        print("⚠️ No se encontró el bloque en base.html, verifícalo manualmente.")

def parchar_admin():
    with open(admin_path, 'r') as f:
        content = f.read()
    
    # Reemplazo para la validación de Agente
    target = "{% elif u.agentes %}"
    replacement = "{% elif u.agente_set.exists %}"
    
    if target in content:
        new_content = content.replace(target, replacement)
        with open(admin_path, 'w') as f:
            f.write(new_content)
        print("✅ admin_roles_permisos.html parcheado correctamente.")
    else:
        print("⚠️ No se encontró el bloque en admin_roles_permisos.html.")

if __name__ == "__main__":
    parchar_base()
    parchar_admin()