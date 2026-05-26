from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, View
from django.contrib import messages
from tikects_app.models import Tickets, Tickets_Servicios, Tickets_Colas
from datetime import datetime

class DashboardClientesView(LoginRequiredMixin, ListView):
    model = Tickets
    template_name = 'pagina_principal_clientes.html'
    context_object_name = 'ultimos_tickets'

    def get_queryset(self):
        return Tickets.objects.filter(usuario=self.request.user).order_by('-fecha_creacion')[:5]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['total_mis_tickets'] = Tickets.objects.filter(usuario=user).count()
        context['mis_tickets_abiertos'] = Tickets.objects.filter(usuario=user).exclude(estado='cerrado').count()
        context['mis_tickets_cerrados'] = Tickets.objects.filter(usuario=user, estado='cerrado').count()
        context['now'] = datetime.now()
        return context
