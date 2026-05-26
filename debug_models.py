import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tu_proyecto.settings') # Cambia esto por tu settings
django.setup()

from django.contrib.auth.models import User
from tikects_app.models import Agentes, Cliente

u = User.objects.first()
print(f"¿Usuario tiene agente?: {hasattr(u, 'agentes')}")
print(f"¿Usuario tiene cliente?: {hasattr(u, 'cliente')}")