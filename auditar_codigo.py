#!/usr/bin/env python3
import os
import re

# Colores para la consola
VERDE = "\033[92m"
AMARILLO = "\033[93m"
ROJO = "\033[91m"
RESET = "\033[0m"
AZUL = "\033[94m"

def analizar_archivo_views(ruta_archivo):
    """Busca asignaciones sospechosas de request.user a campos de agentes."""
    errores = []
    # Patrón para detectar ticket.campo_agente = request.user
    patron_user_erroneo = re.compile(r'(ticket|tikect)\.\w*(agente|asignado|resolutor)\w*\s*=\s*request\.user\b')
    
    with open(ruta_archivo, 'r', encoding='utf-8', errors='ignore') as f:
        for num_linea, linea in enumerate(f, 1):
            if patron_user_erroneo.search(linea) and not linea.strip().startswith('#'):
                errores.append((num_linea, linea.strip(), "Asignación directa de 'request.user' (instancia User) a un campo de tipo 'Agentes'. Causará ValueError en producción."))
    return errores

def analizar_archivo_template(ruta_archivo):
    """Busca etiquetas rotas de cierre tipo 'endspan', 'enddiv' o texto fuera de bloques."""
    errores = []
    # Patrones para detectar errores comunes de tipeo en el cierre de etiquetas
    patrones_rotos = [
        (re.compile(r'\bendspan\b', re.IGNORECASE), "Se encontró 'endspan' suelto. Debería ser '</span>' o '{% endif %}'."),
        (re.compile(r'\benddiv\b', re.IGNORECASE), "Se encontró 'enddiv' suelto. Debería ser '</div>'."),
        (re.compile(r'\bendp\b', re.IGNORECASE), "Se encontró 'endp' suelto. Debería ser '</p>'."),
        (re.compile(r'\{%\s*extends\s*.*?%\}(?!=\A)', re.IGNORECASE), "La etiqueta '{% extends %}' no está en la primera línea del archivo.")
    ]
    
    with open(ruta_archivo, 'r', encoding='utf-8', errors='ignore') as f:
        contenido = f.read()
        lines = contenido.splitlines()
        
        # Analizar línea por línea para patrones rotos
        for num_linea, linea in enumerate(lines, 1):
            for patron, mensaje in patrones_rotos:
                if patron.search(linea) and not ("
