import os
import re

# Configuración de archivos a modificar
archivos_a_modificar = ['tikects_app/vistas_legado.py', 'tikects_app/views/clientes.py']
decorador_import = "from tikects_app.decoradores import solo_clientes_permitido"

def procesar_archivo(ruta):
    if not os.path.exists(ruta):
        print(f"Archivo no encontrado: {ruta}")
        return

    with open(ruta, 'r') as f:
        contenido = f.read()

    # 1. Agregar el import si no existe
    if decorador_import not in contenido:
        contenido = decorador_import + "\n" + contenido

    # 2. Decorar funciones (para vistas_legado.py)
    # Busca @login_required y añade @solo_clientes_permitido debajo
    contenido = re.sub(r'(@login_required\n)def', r'\1@solo_clientes_permitido\ndef', contenido)

    # 3. Decorar Clases (para vistas basadas en clases)
    # Busca la clase y añade el method_decorator
    contenido = re.sub(
        r'class (\w+View)\(View\):', 
        r'@method_decorator(solo_clientes_permitido, name="dispatch")\nclass \1(View):', 
        contenido
    )

    with open(ruta, 'w') as f:
        f.write(contenido)
    print(f"✅ Archivo procesado: {ruta}")

for archivo in archivos_a_modificar:
    procesar_archivo(archivo)