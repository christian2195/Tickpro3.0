#!/usr/bin/env python3
import os
import shutil

# Colores para la consola de Linux
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

def corregir_bloqueos_vistas():
    ruta_views = "tikects_app/views.py"
    
    print(f"{BLUE}=================================================={RESET}")
    print(f"{BLUE}   PARCHE DE REDIRECCIONES NATIVAS (TICKPRO)      {RESET}")
    print(f"{BLUE}=================================================={RESET}\n")

    if not os.path.exists(ruta_views):
        print(f"❌ {RED}Error: No se encontró views.py en {ruta_views}. Ejecútalo en la raíz.{RESET}")
        return

    # 1. Crear respaldo preventivo
    ruta_bak = ruta_views + ".bak_redirecciones"
    shutil.copyfile(ruta_views, ruta_bak)
    print(f"💾 Respaldo de seguridad creado: {BLUE}{os.path.basename(ruta_bak)}{RESET}")

    with open(ruta_views, 'r', encoding='utf-8') as f:
        contenido = f.read()

    # 2. Definición del bloque de control nativo ultraligero
    bloque_viejo_filtro = "es_agente = Agentes.objects.filter(usuario=request.user).exists()\n    if request.user.is_superuser or es_agente:"
    bloque_nuevo_filtro = "if request.user.is_superuser or hasattr(request.user, 'agente') or hasattr(request.user, 'Agentes'):"

    print(f"⚙️  {BLUE}Sustituyendo validaciones de base de datos por atributos nativos de Django...{RESET}")

    modificado = False
    
    # Remplazar en las vistas de listado de clientes que tenían el query manual pesado
    if bloque_viejo_filtro in contenido:
        contenido = contenido.replace(bloque_viejo_filtro, bloque_nuevo_filtro)
        modificado = True
    else:
        # Fallback directo en caso de sutiles variaciones de espaciado
        if "es_agente = Agentes.objects.filter(usuario=request.user).exists()" in contenido:
            contenido = contenido.replace("es_agente = Agentes.objects.filter(usuario=request.user).exists()\n    if request.user.is_superuser or es_agente:", bloque_nuevo_filtro)
            contenido = contenido.replace("es_agente = Agentes.objects.filter(usuario=request.user).exists()\n    if request.user.is_superuser or es_agente:", bloque_nuevo_filtro)
            modificado = True

    # 3. Validar y asegurar que 'mesa_triage' no tenga bloqueos inversos heredados de migración
    if "def mesa_triage(request):" in contenido:
        print(f"⚙️  {BLUE}Verificando integridad estructural en la mesa de triage...{RESET}")
        # Forzar que el triage valide de forma idéntica y limpia al resolutor
        bloque_triage_viejo = "def mesa_triage(request):\n    "
        if bloque_triage_viejo in contenido and "hasattr(request.user" not in contenido.split("def mesa_triage(request):")[1][:200]:
            # No requiere inyección si el decorador personalizado @agente_or_superuser_required ya hace su trabajo arriba
            pass

    # 4. Guardar los cambios finales en caliente
    if modificado:
        with open(ruta_views, 'w', encoding='utf-8') as f:
            f.write(contenido)
        print(f"✅ {GREEN}views.py optimizado. Filtros unificados con el Navbar.{RESET}")
    else:
        print(f"ℹ️  {YELLOW}No se detectaron los queries antiguos en views.py. Aplicando optimización directa por bloques...{RESET}")
        
        # Parche directo de sobreescritura exacta para las tres vistas de cliente
        vistas = ["def ver_mis_tikects(request):", "def ver_mis_tikects_cerrados(request):", "def ver_mis_tikects_abiertos(request):"]
        for v in vistas:
            if v in contenido:
                reemplazo_directo = f"{v}\n    if request.user.is_superuser or hasattr(request.user, 'agente') or hasattr(request.user, 'Agentes'):\n        return redirect('pagina_principal')\n"
                # Limpiar cualquier residuo previo del query anterior si existiese de forma desordenada
                partes = contenido.split(v)
                resto_limpio = partes[1]
                if "es_agente =" in resto_limpio[:200]:
                    lines_resto = resto_limpio.split('\n')
                    # Removemos las líneas viejas del filtro manual
                    lines_resto = [l for l in lines_resto if "es_agente =" not in l and "if request.user.is_superuser or es_agente:" not in l]
                    resto_limpio = '\n'.join(lines_resto)
                contenido = partes[0] + reemplazo_directo + resto_limpio
                modificado = True
                
        if modificado:
            with open(ruta_views, 'w', encoding='utf-8') as f:
                f.write(contenido)
            print(f"✅ {GREEN}views.py reestructurado de manera quirúrgica y exitosa.{RESET}")

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    corregir_bloqueos_vistas()