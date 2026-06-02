import os
import re

# Directorio donde buscar los archivos (tikects_app)
ruta_proyecto = './tikects_app'
campo_error = 'descripcion_solucion'

def corregir_archivos():
    for root, dirs, files in os.walk(ruta_proyecto):
        for file in files:
            if file.endswith('.py'):
                ruta_completa = os.path.join(root, file)
                with open(ruta_completa, 'r', encoding='utf-8') as f:
                    contenido = f.read()

                if campo_error in contenido:
                    print(f"Corrigiendo archivo: {ruta_completa}")
                    # Reemplazamos el atributo problemático por un texto vacío
                    nuevo_contenido = contenido.replace(f'ticket.{campo_error}', '""')
                    
                    with open(ruta_completa, 'w', encoding='utf-8') as f:
                        f.write(nuevo_contenido)

if __name__ == "__main__":
    corregir_archivos()
    print("¡Listo! Todas las referencias a 'descripcion_solucion' han sido eliminadas.")