#!/usr/bin/env python3
import os
import re

# Colores para una lectura limpia en la terminal
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

def buscar_en_archivo(ruta, patrones):
    """Busca patrones sospechosos y devuelve las líneas exactas con su contexto"""
    if not os.path.exists(ruta):
        return []
    
    hallazgos = []
    with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
        lineas = f.readlines()
        
    for i, linea in enumerate(lineas, 1):
        for nombre_patron, regex in patrones.items():
            if re.search(regex, linea):
                hallazgos.append({
                    'linea_num': i,
                    'codigo': linea.strip(),
                    'tipo': nombre_patron
                })
    return hallazgos

def auditar_aplicacion():
    print(f"{BLUE}=================================================={RESET}")
    print(f"{BLUE}   AUDITOR DE FLUJO Y SEGURIDAD CRÍTICA (2026)    {RESET}")
    print(f"{BLUE}=================================================={RESET}\n")

    # Definimos los sospechosos habituales que causan los bucles de redirección
    patrones_views = {
        "Atributo Agente en Minúsculas (hasattr)": r"hasattr\(.*,\s*['\"]agentes?['\"]\)",
        "Atributo Agente en Minúsculas (directo)": r"\.agentes?(?![A-Za-z_])",
        "Redirección Forzada a Clientes": r"redirect\(['\"]pagina_principal_clientes['\"]\)",
        "Decorador de Triage/Agente": r"@agente_or_superuser_required"
    }
    
    patrones_html = {
        "Atributo de Plantilla en Minúsculas": r"user\.agents?",
        "Validación de navbar errática": r"user\.agente\.id"
    }

    # 1. Auditoría del Backend
    ruta_views = "tikects_app/views.py"
    print(f"🔍 Evaluando backend clínico en: {YELLOW}{ruta_views}{RESET}...")
    hallazgos_views = buscar_en_archivo(ruta_views, patrones_views)
    
    if hallazgos_views:
        print(f"⚠️  Se detectaron {RED}{len(hallazgos_views)}{RESET} posibles focos de conflicto en el backend:")
        for h in hallazgos_views:
            print(f"   [{RED}Línea {h['linea_num']}{RESET}] ({YELLOW}{h['tipo']}{RESET}): {BLUE}{h['codigo']}{RESET}")
    else:
        print(f"✅ Backend libre de inconsistencias obvias de nombres.")

    print("-" * 50)

    # 2. Auditoría del Frontend (Plantillas estructurales)
    templates = [
        "tikects_app/templates/base.html",
        "tikects_app/templates/pagina_principal.html",
        "tikects_app/templates/mesa_triage.html"
    ]
    
    total_html_issues = 0
    for t in templates:
        if os.path.exists(t):
            print(f"🔍 Evaluando arquitectura de plantilla: {YELLOW}{t}{RESET}...")
            hallazgos_html = buscar_en_archivo(t, patrones_html)
            if hallazgos_html:
                total_html_issues += len(hallazgos_html)
                for h in hallazgos_html:
                    print(f"   [{RED}Línea {h['linea_num']}{RESET}] ({YELLOW}{h['tipo']}{RESET}): {BLUE}{h['codigo']}{RESET}")
            else:
                print(f"   ✅ Estructura limpia.")
                
    print("\n" + "=" * 50)
    print(f"{GREEN}   CONCLUSIÓN DEL DIAGNÓSTICO{RESET}")
    print("=" * 50)
    if len(hallazgos_views) == 0 and total_html_issues == 0:
        print(f" {GREEN}Felicidades. Las rutas analizadas no presentan colisiones sintácticas evidentes.{RESET}")
    else:
        print(f" 🛠️  Analiza las líneas impresas arriba. El cortocircuito ocurre en una de esas condiciones.")
    print("=" * 50)

if __name__ == '__main__':
    # Asegurar ejecución en el directorio raíz del proyecto
    if os.path.exists("tikects_app"):
        auditar_aplicacion()
    else:
        print(f"❌ {RED}Por favor, coloca y ejecuta este script en /var/www/html/Tickpro2.0/{RESET}")