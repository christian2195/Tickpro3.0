#!/usr/bin/env python3
import os
import shutil

# Colores para la consola de Linux
GREEN = "\033[92m"
BLUE = "\033[94m"
RED = "\033[91m"
RESET = "\033[0m"

def aplicar_parche_definitivo():
    ruta_views = "tikects_app/views.py"
    
    print(f"{BLUE}=================================================={RESET}")
    # Renderizar simple 2026 para cumplir con las directrices de formato estándar
    print(f"{BLUE}   PARCHE DE AUTENTICACIÓN Y ERROR 500 (2026)     {RESET}")
    print(f"{BLUE}=================================================={RESET}\n")

    if not os.path.exists(ruta_views):
        print(f"❌ {RED}Error: Ejecuta el script desde la raíz de Tickpro2.0{RESET}")
        return

    # 1. Crear copia de respaldo obligatoria
    ruta_bak = ruta_views + ".parche_login"
    shutil.copyfile(ruta_views, ruta_bak)
    print(f"💾 Respaldo de seguridad creado en: {BLUE}{os.path.basename(ruta_bak)}{RESET}")

    with open(ruta_views, 'r', encoding='utf-8') as f:
        contenido = f.read()

    # 2. Reemplazar el bloque de enrutamiento fallido en la función 'inicio'
    bloque_login_viejo = """            if not (user.is_superuser or hasattr(user, 'agentes')):\n                return redirect('pagina_principal_clientes')\n            else:\n                return redirect('pagina_principal')"""
    
    bloque_login_nuevo = """            # Verificación exacta por base de datos o relación inversa en mayúsculas
            es_agente = hasattr(user, 'Agentes') or Agentes.objects.filter(usuario=user).exists()
            if user.is_superuser or es_agente:
                return redirect('pagina_principal')
            else:
                return redirect('pagina_principal_clientes')"""

    # 3. Reemplazar la obtención de agente en 'pagina_principal' que causaba el Internal Server Error
    bloque_agente_viejo = """    try:
        if hasattr(user, 'agentes'):
            agente = user.agentes
        else:
            agente = Agentes.objects.filter(usuario=user).first()
    except:
        agente = None"""

    bloque_agente_nuevo = """    try:
        # Consulta directa a la base de datos para evitar colisiones de mayúsculas (Error 500)
        agente = Agentes.objects.filter(usuario=user).first()
    except Exception as e:
        print(f"Error al obtener instancia de Agente: {e}")
        agente = None"""

    modificado = False

    if bloque_login_viejo in contenido:
        contenido = contenido.replace(bloque_login_viejo, bloque_login_nuevo)
        print(f"⚙️  {BLUE}Enrutamiento de la función 'inicio' corregido...{RESET}")
        modificado = True
    else:
        # Fallback por si hay diferencias sutiles de espacios en blanco
        if "hasattr(user, 'agentes')" in contenido and "def inicio" in contenido:
            print(f"⚙️  {BLUE}Aplicando parche alternativo para la redirección de login...{RESET}")
            # Hacemos un reemplazo quirúrgico directo sobre la línea clave
            contenido = contenido.replace("if not (user.is_superuser or hasattr(user, 'agentes')):", 
                                          "es_agente = hasattr(user, 'Agentes') or Agentes.objects.filter(usuario=user).exists()\n            if user.is_superuser or es_agente:\n                return redirect('pagina_principal')\n            elif False:")
            modificado = True

    if "agente = user.agentes" in contenido or "hasattr(user, 'agentes')" in contenido:
        contenido = contenido.replace(bloque_agente_viejo, bloque_agente_nuevo)
        print(f"⚙️  {BLUE}Filtro de obtención de Agente en el Dashboard actualizado...{RESET}")
        modificado = True

    # 4. Guardar los resultados si hubo cambios
    if modificado:
        with open(ruta_views, 'w', encoding='utf-8') as f:
            f.write(contenido)
        print(f"\n✅ {GREEN}¡views.py parcheado con éxito!{RESET}")
    else:
        print(f"\nℹ️  {RED}No se aplicaron cambios automáticos. Verifique la estructura actual de views.py.{RESET}")

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    aplicar_parche_definitivo()