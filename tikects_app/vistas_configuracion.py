from django.shortcuts import render, redirect
from .models import Tickets_Respuestas_Automaticas
from django.contrib import messages

def lista_respuestas(request):
    respuestas = Tickets_Respuestas_Automaticas.objects.all()
    return render(request, 'tickets_repuesta_automaticas.html', {'respuestas': respuestas})

def crear_respuesta(request):
    if request.method == 'POST':
        Tickets_Respuestas_Automaticas.objects.create(
            nombre=request.POST.get('nombre'),
            asunto=request.POST.get('asunto'),
            cuerpo=request.POST.get('cuerpo')
        )
        messages.success(request, "Respuesta automática creada exitosamente.")
        # Corregido: Nombre que definimos en urls.py
        return redirect('tickets_repuesta_automaticas_lista')
    
    # Corregido: Nombre del archivo que creamos en templates
    return render(request, 'tickets_respuesta_automaticas_crear.html')

def eliminar_respuesta_automatica(request, respuesta_id):
    respuesta = get_object_or_404(Tickets_Respuestas_Automaticas, id=respuesta_id)
    respuesta.delete()
    messages.success(request, "Respuesta eliminada correctamente.")
    return redirect('tickets_repuesta_automaticas_lista')

def enviar_respuesta_automatica(ticket, respuesta_automatica):
    # Contexto para tu plantilla
    context = {
        'saludo': f"Hola {ticket.cliente.nombre},",
        'mensaje_cuerpo': respuesta_automatica.cuerpo,
        'ticket': ticket
    }
    
    # Renderizar el HTML
    html_message = render_to_string('emails/email_ticket.html', context)
    
    # Enviar el correo
    send_mail(
        subject=respuesta_automatica.asunto,
        message=respuesta_automatica.cuerpo, # Versión texto plano
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[ticket.cliente.correo],
        html_message=html_message,
        fail_silently=False,
    )