from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, View
from django.db.models import Q, Count
from tikects_app.models import Tickets, Agentes, Notificaciones
from .core import AgenteRequiredMixin
from datetime import datetime
from django.contrib.auth.mixins import UserPassesTestMixin
from tikects_app.models import Agentes

class AgenteRequiredMixin(UserPassesTestMixin):
    """
    Mixin que permite el acceso SOLO a Superusuarios o a usuarios 
    que tengan un perfil registrado en la tabla Agentes.
    """
    def test_func(self):
        # Si es superusuario, pasa directo
        if self.request.user.is_superuser:
            return True
            
        # Si no es superusuario, verificamos si existe en la tabla Agentes
        es_agente = Agentes.objects.filter(usuario=self.request.user).exists()
        return es_agente
    
class DashboardSoporteView(LoginRequiredMixin, AgenteRequiredMixin, ListView):
    model = Tickets
    template_name = 'pagina_principal.html'
    context_object_name = 'ultimos_tickets'

    def get_queryset(self):
        return Tickets.objects.all().order_by('-fecha_creacion')[:5]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['agente'] = Agentes.objects.filter(usuario=self.request.user).first()
        context['total_tickets'] = Tickets.objects.count()
        context['tickets_abiertos'] = Tickets.objects.exclude(estado='cerrado').count()
        context['tickets_cerrados'] = Tickets.objects.filter(estado__iexact='cerrado').count()
        context['total_agentes'] = Agentes.objects.count()
        context['now'] = datetime.now()
        return context

class MesaTriageView(LoginRequiredMixin, AgenteRequiredMixin, ListView):
    model = Tickets
    template_name = 'mesa_triage.html'
    context_object_name = 'tickets'
    paginate_by = 20

    def get_queryset(self):
        queryset = Tickets.objects.filter(Q(estado_triage='nuevo') | Q(estado_triage='triaje')).order_by('-fecha_creacion')
        prioridad = self.request.GET.get('prioridad', '')
        tipo = self.request.GET.get('tipo', '')
        if prioridad: queryset = queryset.filter(prioridad=prioridad)
        if tipo: queryset = queryset.filter(tipo=tipo)
        return queryset
