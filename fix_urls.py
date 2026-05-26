# fix_urls.py
import os

path_urls = '/var/www/html/Tickpro2.0/tikects_app/urls.py'

with open(path_urls, 'r') as f:
    content = f.read()

# Reemplazamos la ruta problemática por una configuración clara
new_content = content.replace(
    "path('triage/', mapear_vista('mesa_triage'), name='mesa_triage'),", 
    "path('triage/', mapear_vista('mesa_triage'), name='triage'),"
)

with open(path_urls, 'w') as f:
    f.write(new_content)

print("urls.py actualizado exitosamente.")