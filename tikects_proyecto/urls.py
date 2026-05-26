from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls), # Panel nativo de Django
    path('', include('tikects_app.urls')), # 🔑 Enlazamos el enrutador modular directo a la raíz web
]