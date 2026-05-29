#!/bin/bash

# Configuración
PROJECT_DIR="/var/www/html/Tickpro2.0"
VENV_DIR="$PROJECT_DIR/venv"

echo "🚀 Iniciando paso a producción en Tickpro 2.0..."

# 1. Moverse al directorio del proyecto
cd $PROJECT_DIR

# 2. Obtener los últimos cambios (si usas git)
# git pull origin main

# 3. Activar entorno virtual
source $VENV_DIR/bin/activate

# 4. Instalar dependencias
echo "📦 Instalando dependencias..."
pip install -r requirements.txt

# 5. Aplicar migraciones (Muy importante por el nuevo campo 'usuario')
echo "🗄️ Aplicando migraciones..."
python manage.py makemigrations
python manage.py migrate

# 6. Recopilar archivos estáticos
echo "🎨 Recopilando archivos estáticos..."
python manage.py collectstatic --noinput

# 7. Reiniciar Gunicorn
echo "🔄 Reiniciando Gunicorn..."
sudo systemctl restart gunicorn

# 8. Limpiar (Opcional)
# echo "🧹 Limpiando archivos temporales..."
# find . -name "*.pyc" -delete

echo "✅ Despliegue completado con éxito a las $(date)"