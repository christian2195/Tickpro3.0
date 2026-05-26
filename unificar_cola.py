#!/usr/bin/env python3
import os
import shutil

# Colores para la consola de Linux
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def unificar_cola_tickets():
    ruta_views = "tikects_app/views.py"
    if not os.path.exists(ruta_views):
        print("❌ Error: No se encuentra tikects_app/views.py. Ejecuta el script en la raíz del proyecto.")
        return False

    # Crear respaldo preventivo
    ruta_bak = ruta_views + ".respaldo_cola"
    shutil.copyfile(ruta_views, ruta_bak)
    print(f"💾 Respaldo de seguridad creado: {BLUE}{os.path.basename(ruta_bak)}{RESET}")

    with open(ruta_views, 'r', encoding='utf-8') as f:
        contenido = f.read()

    # Buscamos la condición original que separaba al superusuario del agente
    bloque_viejo = "if user.is_superuser:\n            ultimos_tickets = Tickets.objects.all().order_by('-fecha_creacion')[:5]\n        elif agente:"
    
    # Variante de formato por si acaso hay espacios diferentes
    bloque_viejo_alt = "if user.is_superuser:\n            ultimos_tickets = Tickets.objects.all().order_by('-fecha_creacion')[:5]\n        elif agente:"

    print(f"⚙️  {BLUE}Modificando consultas en views.py para otorgar visibilidad global a los Agentes...{RESET}")

    if "if user.is_superuser:" in contenido and "elif agente:" in contenido:
        # Reemplazamos para que el 'if' una a superusuarios y agentes en la misma cola general
        contenido = contenido.replace("if user.is_superuser:", "if user.is_superuser or agente:")
        
        # Comentamos de forma segura el bloque 'elif agente' interno viejo para que no duplique lógica
        contenido = contenido.replace("elif agente:\n            try:\n                tickets_creados = Tickets.objects.filter(usuario=user)", 
                                      "elif False: # Bloque viejo deshabilitado por unificación\n            try:\n                tickets_creados = Tickets.objects.filter(usuario=user)")
        
        with open(ruta_views, 'w', encoding='utf-8') as f:
            f.write(contenido)
        print(f"✅ {GREEN}views.py actualizado. Ahora los agentes comparten la cola del Administrador.{RESET}")
        return True
    else:
        print(f"ℹ️  {YELLOW}No se encontraron los patrones exactos. Es posible que ya hayas unificado la cola manualmente.{RESET}")
        return False

if __name__ == '__main__':
    print(f"{BLUE}=================================================={RESET}")
    print(f"{BLUE}     UNIFICADOR DE COLA GLOBAL PARA AGENTES       {RESET}")
    print(f"{BLUE}=================================================={RESET}\n")
    
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    unificar_cola_tickets()