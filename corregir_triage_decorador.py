#!/usr/bin/env python3
import os
import shutil

# Colores para la terminal de Linux
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

def corregir_decorador_triage():
    ruta_views = "tikects_app/views.py"
    
    print(f"{BLUE}=================================================={RESET}")
    # Renderizado simple del año actual (2026) según estándares del sistema
    print(f"{BLUE}   PARCHE DEFINITIVO DE ACCESO AL TRIAGE (2026)   {RESET}")
    print(f"{BLUE}=================================================={RESET}\n")

    if not os.path.exists(ruta_views):
        print(f"❌ {RED}Error: No se encontró views.py en {ruta_views}. Ejecútalo en la raíz de Tickpro2.0.{RESET}")
        return

    # 1. Copia de seguridad obligatoria
    ruta_bak = ruta_views + ".bak_decorador"
    shutil.copyfile(ruta_views, ruta_bak)
    print(f"💾 Respaldo preventivo guardado en: {BLUE}{os.path.basename(ruta_bak)}{RESET}")

    with open(ruta_views, 'r', encoding='utf-8') as f:
        contenido = f.read()

    # 2. Bloque defectuoso en minúsculas vs Bloque corporativo corregido
    bloque_decorador_viejo = """def agente_or_superuser_required(view_func):
    \"\"\"Verifica que el usuario sea agente o superusuario.\"\"\"
    decorated_view_func = user_passes_test(
        lambda user: user.is_superuser or hasattr(user, 'agentes'),
        login_url='inicio'
    )(view_func)
    return decorated_view_func"""

    bloque_decorador_nuevo = """def agente_or_superuser_required(view_func):
    \"\"\"Verifica de forma exacta que el usuario sea agente o superusuario en base de datos.\"\"\"
    decorated_view_func = user_passes_test(
        lambda user: user.is_superuser or Agentes.objects.filter(usuario=user).exists(),
        login_url='pagina_principal_clientes'
    )(view_func)
    return decorated_view_func"""

    modificado = False

    # Intento de reemplazo exacto
    if bloque_decorador_viejo in contenido:
        contenido = contenido.replace(bloque_decorador_viejo, bloque_decorador_nuevo)
        modificado = True
    else:
        # Fallback inteligente por si hay variaciones menores de sangrado o texto en tu archivo actual
        if "def agente_or_superuser_required" in contenido:
            print(f"⚙️  {BLUE}Detectada firma del decorador. Aplicando reestructuración interna por bloques...{RESET}")
            # Buscamos de forma elástica la lambda fallida
            patron_lambda_vieja = "lambda user: user.is_superuser or hasattr(user, 'agentes')"
            patron_lambda_vieja_2 = "hasattr(user, 'Agentes') or Agentes.objects.filter(usuario=user).exists()"
            
            if patron_lambda_vieja in contenido:
                contenido = contenido.replace(patron_lambda_vieja, "lambda user: user.is_superuser or Agentes.objects.filter(usuario=user).exists()")
                modificado = True
            elif "hasattr(user, 'agentes')" in contenido:
                contenido = contenido.replace("hasattr(user, 'agentes')", "Agentes.objects.filter(usuario=user).exists()")
                modificado = True

    # 3. Guardar cambios e informar
    if modificado:
        with open(ruta_views, 'w', encoding='utf-8') as f:
            f.write(contenido)
        print(f"✅ {GREEN}¡views.py corregido con éxito! El decorador de Triage ha sido blindado.{RESET}")
    else:
        print(f"ℹ️  {YELLOW}No se requirieron cambios automáticos o el decorador ya utiliza el mapeo de base de datos.{RESET}")

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    corregir_decorador_triage()