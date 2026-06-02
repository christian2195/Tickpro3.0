from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib.auth.decorators import user_passes_test
from .core import AgenteRequiredMixin

class PanelConfiguracionView(LoginRequiredMixin, AgenteRequiredMixin, TemplateView):
    template_name = 'configuracion.html'
