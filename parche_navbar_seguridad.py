#!/usr/bin/env python3
import os
import shutil

# Colores para la consola de Linux
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

def aplicar_parche_limpieza_visual():
    ruta_views = "tikects_app/views.py"
    ruta_base = "tikects_app/templates/base.html"
    
    print(f"{BLUE}=================================================={RESET}")
    print(f"{BLUE}   PARCHE DE SEGURIDAD: CONTROL DE ACCESO NAVBAR  {RESET}")
    print(f"{BLUE}=================================================={RESET}\n")

    # --- 1. PARCHEAR VIEWS.PY (BLINDAJE DE URLS DE CLIENTES) ---
    if os.path.exists(ruta_views):
        ruta_bak_v = "%s.bak_navbar" % ruta_views
        shutil.copyfile(ruta_views, ruta_bak_v)
        print(f"💾 Respaldo de seguridad creado: {BLUE}{os.path.basename(ruta_bak_v)}{RESET}")
        
        with open(ruta_views, 'r', encoding='utf-8') as f:
            contenido_v = f.read()
        
        # Bloque de restricción que inyectaremos en las vistas de cliente
        bloque_restriccion = """    # 🚫 Restricción para resolutores: No se les permite ver este historial
    es_agente = Agentes.objects.filter(usuario=request.user).exists()
    if request.user.is_superuser or es_agente:
        return redirect('pagina_principal')\n\n"""

        # Inyección quirúrgica en las cabeceras de las vistas correspondientes
        vistas_a_parchear = [
            "def ver_mis_tikects(request):",
            "def ver_mis_tikects_cerrados(request):",
            "def ver_mis_tikects_abiertos(request):"
        ]
        
        modificado_v = False
        for vista in vistas_a_parchear:
            # Validamos que la vista exista y no esté parchada ya
            if vista in contenido_v and ("es_agente = Agentes.objects.filter" not in contenido_v.split(vista)[1][:500]):
                reemplazo = "%s\n%s" % (vista, bloque_restriccion)
                contenido_v = contenido_v.replace(vista, reemplazo)
                print(f"⚙️  {BLUE}Candado de seguridad inyectado en vista: {vista}{RESET}")
                modificado_v = True
                
        if modificado_v:
            with open(ruta_views, 'w', encoding='utf-8') as f:
                f.write(contenido_v)
            print(f"✅ {GREEN}views.py blindado exitosamente.{RESET}")
        else:
            print(f"ℹ️  {YELLOW}Las vistas de views.py ya se encuentran protegidas o no se encontraron.{RESET}")
    else:
        print(f"❌ {RED}Error: No se encontró views.py en {ruta_views}{RESET}")

    print("")

    # --- 2. PARCHEAR BASE.HTML (FILTRADO DEL NAVBAR) ---
    if os.path.exists(ruta_base):
        ruta_bak_b = "%s.bak_navbar" % ruta_base
        shutil.copyfile(ruta_base, ruta_bak_b)
        print(f"💾 Respaldo de seguridad creado: {BLUE}{os.path.basename(ruta_bak_b)}{RESET}")
        
        with open(ruta_base, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        contenido_b = "".join(lines)
        if "{% if not user.is_superuser and not agente %}" in contenido_b:
            print(f"ℹ️  {YELLOW}El Navbar en base.html ya cuenta con las restricciones de exclusividad.{RESET}")
            return

        nueva_salida = []
        i = 0
        modificado_b = False
        while i < len(lines):
            linea = lines[i]
            
            # Detectamos la etiqueta que renderiza el enlace al panel de "Mis Tickets"
            if "ver_mis_tikects" in linea:
                # Buscamos el inicio del contenedor de la lista (<li>) que suele estar 1 o 2 líneas arriba
                back = 1
                while back <= 3 and i - back >= 0:
                    if "<li" in nueva_salida[-(back)]:
                        # Inyectamos el tag condicional de Django antes del <li> correspondiente
                        posicion_insercion = len(nueva_salida) - back
                        nueva_salida.insert(posicion_insercion, "                {% if not user.is_superuser and not agente %}\n")
                        print(f"⚙️  {BLUE}Ocultando enlace 'Mis Tickets' en el Navbar de agentes/admins...{RESET}")
                        modificado_b = True
                        break
                    back += 1
                
                # Agregamos la línea actual que tiene la URL
                nueva_salida.append(linea)
                
                # Buscamos el cierre del contenedor (</li>) en las siguientes líneas para cerrar el {% endif %}
                i += 1
                while i < len(lines) and "</li>" not in lines[i]:
                    nueva_salida.append(lines[i])
                    i += 1
                if i < len(lines):
                    nueva_salida.append(lines[i]) # Agrega el </li>
                    nueva_salida.append("                {% endif %}\n") # Cierra el candado
                i += 1
                continue
                
            nueva_salida.append(linea)
            i += 1

        if modificado_b:
            with open(ruta_base, 'w', encoding='utf-8') as f:
                f.writelines(nueva_salida)
            print(f"✅ {GREEN}base.html actualizado. Enlaces restringidos de forma dinámica.{RESET}")
    else:
        print(f"❌ {RED}Error: No se encontró base.html en {ruta_base}{RESET}")

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    aplicar_parche_limpieza_visual()