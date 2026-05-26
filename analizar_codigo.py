#!/usr/bin/env python3
import os
import re

# Colores para la consola
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def analizar_archivo_py(ruta_archivo):
    """Busca errores de lógica comunes en archivos Python (views.py, etc.)"""
    errores_encontrados = []
    
    with open(ruta_archivo, 'r', encoding='utf-8', errors='ignore') as f:
        lineas = f.readlines()
        
    for num_linea, linea in enumerate(lineas, 1):
        # 1. Detectar si se está pisando el usuario creador del ticket en el POST
        if re.search(r'\.usuario\s*=\s*\w+\.usuario', linea):
            errores_encontrados.append(
                f"Línea {num_linea}: {YELLOW}Alerta de Suplantación{RESET} -> Posible sobreescritura de ticket.usuario con el usuario del agente."
            )
            
        # 2. Detectar asignación directa de request.user a campos de perfil Agente
        if re.search(r'por_agente\s*=\s*request\.user', linea) or re.search(r'\.agente\s*=\s*request\.user', linea):
            if "request.user.agente" not in linea:
                errores_encontrados.append(
                    f"Línea {num_linea}: {RED}ValueError Potencial{RESET} -> Intentando asignar 'request.user' (User) a un campo que espera una instancia de 'Agentes'."
                )
                
    return errores_encontrados

def analizar_archivo_html(ruta_archivo):
    """Busca errores de sintaxis y estructura en plantillas de Django (.html)"""
    errores_encontrados = []
    
    with open(ruta_archivo, 'r', encoding='utf-8', errors='ignore') as f:
        contenido = f.read()
        lineas = contenido.splitlines()

    # 3. Validar el orden de {% extends %}
    # Si existe extends pero no está en las primeras líneas significativas
    if "{% extends" in contenido:
        for num_linea, linea in enumerate(lineas, 1):
            linea_limpia = linea.strip()
            if linea_limpia and "{% extends" not in linea_limpia and "{% load" not in linea_limpia:
                # Encontró código antes del extends
                if any("{% extends" in l for l in lineas[num_linea:]):
                    errores_encontrados.append(
                        f"Estructura: {RED}TemplateSyntaxError{RESET} -> Hay código o estilos antes de la etiqueta '{{% extends %}}'."
                    )
                    break

    # 4. Detectar etiquetas de Django mal cerradas (como endspan)
    for num_linea, linea in enumerate(lineas, 1):
        if "endspan" in linea.lower():
            errores_encontrados.append(
                f"Línea {num_linea}: {RED}Sintaxis Rota{RESET} -> Se encontró 'endspan' suelto. Debería ser la etiqueta HTML '</span>'."
            )
            
    return errores_encontrados

def escanear_proyecto(directorio_base):
    print(f"{BLUE}=================================================={RESET}")
    print(f"{BLUE}   ANALIZADOR DE CÓDIGO PERSONALIZADO - TICKPRO    {RESET}")
    print(f"{BLUE}=================================================={RESET}\n")
    
    total_errores = 0
    
    # Carpetas a ignorar para no perder tiempo (como el entorno virtual o git)
    carpetas_ignoradas = ['venv', '.git', '__pycache__', 'static', 'media']

    for raiz, directorios, archivos in os.walk(directorio_base):
        # Filtrar carpetas ignoradas en el camino
        directorios[:] = [d for d in directorios if d not in carpetas_ignoradas]
        
        for archivo in archivos:
            ruta_completa = os.path.join(raiz, archivo)
            errores = []
            
            if archivo.endswith('.py'):
                errores = analizar_archivo_py(ruta_completa)
            elif archivo.endswith('.html'):
                errores = analizar_archivo_html(ruta_completa)
                
            if errores:
                ruta_relativa = os.path.relpath(ruta_completa, directorio_base)
                print(f"📁 Archivo: {BLUE}{ruta_relativa}{RESET}")
                for err in errores:
                    print(f"  ❌ {err}")
                print("-" * 50)
                total_errores += len(errores)
                
    if total_errores == 0:
        print(f"{GREEN}✓ ¡Código limpio! No se encontraron patrones de error conocidos.{RESET}\n")
    else:
        print(f"{YELLOW}⚠ Análisis concluido. Se encontraron {total_errores} problemas potenciales.{RESET}\n")

if __name__ == "__main__":
    # Ejecutar en el directorio actual
    ruta_proyecto = os.path.dirname(os.path.abspath(__file__))
    escanear_proyecto(ruta_proyecto)
