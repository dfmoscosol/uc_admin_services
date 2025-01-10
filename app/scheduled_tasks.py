from datetime import datetime, timedelta
from app import db

def enviar_recordatorios_eventos():
    from app.models import Evento, FechasEvento, Inscripcion
    from app.utils import send_email_async, get_reminder_email_content
    from datetime import datetime, timedelta

    # Calcular la fecha de recordatorio (hoy + 2 días)
    fecha_recordatorio = datetime.now() + timedelta(days=2)

    # Filtrar eventos cuya primera fecha coincide con la fecha de recordatorio
    eventos_a_recordar = []
    for evento in db.session.query(Evento).all():
        # Obtener la primera fecha del evento
        primera_fecha = min(evento.fechasevento, key=lambda x: x.fecha, default=None)
        
        # Si la primera fecha coincide con la fecha de recordatorio, agregar el evento a la lista
        if primera_fecha and primera_fecha.fecha == fecha_recordatorio.date():
            eventos_a_recordar.append((evento, primera_fecha))

    # Enviar recordatorio a los inscritos de cada evento
    for evento, primera_fecha in eventos_a_recordar:
        hora_inicio = None

        # Obtener la hora de inicio para la primera fecha específica
        if evento.charla and evento.charla.hora_inicio and primera_fecha.fecha == fecha_recordatorio.date():
            hora_inicio = evento.charla.hora_inicio
        elif evento.microtaller:
            for sesion in evento.microtaller.sesiones:
                if sesion.fecha_evento.fecha == primera_fecha.fecha:
                    hora_inicio = sesion.hora_inicio
                    break
        elif evento.talleres:
            for taller in evento.talleres:
                for sesion in taller.sesiones:
                    if sesion.fecha_evento.fecha == primera_fecha.fecha:
                        hora_inicio = sesion.hora_inicio
                        break
                if hora_inicio:
                    break

        # Listado de correos de inscritos aceptados
        inscritos = [
            inscripcion.docente.correo
            for inscripcion in evento.inscripciones
            if inscripcion.aceptada
        ]

        # Definir el contenido del correo, incluyendo la hora si está disponible
        fecha_hora_str = f"{fecha_recordatorio.strftime('%d-%m-%Y')} a las {hora_inicio.strftime('%H:%M')}" if hora_inicio else fecha_recordatorio.strftime('%d-%m-%Y')
        email_content = get_reminder_email_content(evento.nombre, evento.tipo, fecha_hora_str)

        # Enviar el correo a los inscritos
        if inscritos:
            send_email_async(inscritos, f"Recordatorio: {evento.nombre} en 2 días", email_content, "static/cabecera.png")


