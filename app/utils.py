import smtplib
import threading
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from flask import current_app

modalidades = {
    1: "Presencial",
    2: "Virtual",
    3: "Híbrida"
}

competencias = {
    1: "Tecnológica",
    2: "Pedagógica",
    3: "Comunicativa",
    4: "De Gestión",
    5: "Investigativa"
}

momentos = {
    1: "Explorador",
    2: "Integrador",
    3: "Innovador"
}


def send_custom_email(recipients, subject, html_content, cabecera_path, mail_username, mail_password, mail_server, mail_port, max_retries=3, retry_delay=5):
    sender = mail_username
    password = mail_password
    
    # Si recipients es una cadena (un solo destinatario), conviértelo en una lista
    if isinstance(recipients, str):
        recipients = [recipients]

    # Configuración del mensaje
    msg = MIMEMultipart("related")
    msg['From'] = sender
    msg['To'] = ", ".join(recipients)  # Mostrar todos los destinatarios en el encabezado
    msg['Subject'] = subject

    # Cuerpo del correo en HTML
    msg_alternative = MIMEMultipart("alternative")
    msg.attach(msg_alternative)
    msg_alternative.attach(MIMEText(html_content, 'html'))

    # Adjuntar la imagen de la cabecera
    with open(cabecera_path, 'rb') as img:
        mime_image = MIMEImage(img.read())
        mime_image.add_header('Content-ID', '<cabecera>')
        msg.attach(mime_image)

    # Intentos de envío
    attempts = 0
    while attempts < max_retries:
        try:
            print("Iniciando conexión con el servidor SMTP...", flush=True)
            server = smtplib.SMTP(mail_server, mail_port)
            print("Conexión inicial al servidor SMTP establecida.", flush=True)
            server.set_debuglevel(1)
            server.ehlo()
            print("EHLO enviado con éxito.", flush=True)
            server.starttls()
            print("STARTTLS inicializado correctamente.", flush=True)
            server.ehlo()
            print("EHLO después de STARTTLS enviado con éxito.", flush=True)
            server.login(sender, password)
            print("Inicio de sesión SMTP exitoso.", flush=True)

            server.sendmail(sender, recipients, msg.as_string())  # Envía a todos los destinatarios
            server.quit()

            print(f'Correo enviado con éxito a {", ".join(recipients)}', flush=True)
            return 'Correo enviado con éxito'

        except Exception as e:
            attempts += 1
            print(f'Error al enviar el correo a {", ".join(recipients)}, intento {attempts} de {max_retries}: {e}', flush=True)
            
            if attempts < max_retries:
                time.sleep(retry_delay)  # Esperar antes de reintentar
            else:
                print(f'Error definitivo al enviar el correo a {", ".join(recipients)} después de {max_retries} intentos', flush=True)
                return f'Error al enviar el correo: {e}'

# Función para enviar correo de manera asíncrona
def send_email_async(recipient, subject, html_content, cabecera_path):
    # Extraer la configuración de correo de current_app
    mail_username = current_app.config['MAIL_USERNAME']
    mail_password = current_app.config['MAIL_PASSWORD']
    mail_server = current_app.config['MAIL_SERVER']
    mail_port = current_app.config['MAIL_PORT']

    # Crear y ejecutar un hilo para el envío del correo
    thread = threading.Thread(target=send_custom_email, args=(recipient, subject, html_content, cabecera_path, mail_username, mail_password, mail_server, mail_port))
    thread.start()
    
def get_acceptance_email_content(docente_nombre, evento_nombre, evento_tipo, taller_nombre=None):
    # Definir el mensaje personalizado según el tipo de evento
    if evento_tipo == 1 and taller_nombre:
        mensaje_evento = f"Nos complace confirmar que ha sido aceptada su inscripción en las <strong>{evento_nombre}</strong> para el taller <strong>{taller_nombre}</strong>"
    elif evento_tipo == 2:
        mensaje_evento = f"Nos complace confirmar que ha sido aceptada su inscripción en la charla <strong>{evento_nombre}</strong>"
    elif evento_tipo == 3:
        mensaje_evento = f"Nos complace confirmar que ha sido aceptada su inscripción en el microtaller <strong>{evento_nombre}</strong>"
    elif evento_tipo == 4:
        mensaje_evento = f"Nos complace confirmar que ha sido aceptada su inscripción en el programa de acompañamiento áulico para el periodo <strong>{evento_nombre}</strong>"

    return f"""
    <html>
    <body style="font-family: Arial, Helvetica, sans-serif; color: #333; margin: 0; padding: 0; line-height: 1.6;">
        <!-- Contenedor principal centrado con ancho máximo -->
        
        <div style="max-width: 600px; margin: 0 auto; text-align: justify; padding: 20px; box-shadow: 0px 0px 10px rgba(0,0,0,0.1);">
            <!-- Imagen de la cabecera usando CID y forzando ancho completo -->
            <div style="text-align: center;">
                <img src="cid:cabecera" alt="Cabecera" style="width: 100%; height: auto;">
            </div>
            <!-- Línea horizontal de separación -->
            <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
            
            <!-- Contenido del mensaje -->
            <p style="margin-top: 20px;">Estimado/a</p>
            <p><strong>{docente_nombre}</strong></p>
            <p>Su despacho</p>
            <p>
                Reciba un cordial saludo de la <strong>Dirección de Innovación Educativa</strong>. {mensaje_evento}.
                Agradecemos su interés en participar y confiamos en que esta capacitación será una oportunidad para fortalecer sus habilidades y conocimientos.
            </p>
            <p>Sin otro particular, le extendemos nuestros mejores deseos.</p>
            
            <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
            <div style="text-align: center; margin-top: 20px;">
                <p>Atentamente,</p>
                <p><strong>Dirección de Innovación Educativa</strong></p>
            </div>
            <!-- Línea horizontal antes del pie de página -->
            <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
            
            <!-- Pie de página con información adicional -->
            <div style="text-align: center; font-size: 0.9em; color: #555;">
                <p>Teléfono: 4051000 ext 1271-1272 | <a href="mailto:capacitaciones.die@ucuenca.edu.ec">capacitaciones.die@ucuenca.edu.ec</a></p>
                <p style="font-size: 0.8em; color: #888; margin-top: 10px;"><em>* El contenido de este correo es responsabilidad de quien suscribe.<br><strong>Por favor no conteste este correo.</strong></em></p>
            </div>
        </div>
        <!-- Barra de pie de página -->
        <div style="background-color: #0e1b46; padding: 10px 0; text-align: center; color: #ffffff;">
            
        </div>
    </body>
    </html>
    """

def get_inscription_email_content(docente_nombre, evento_nombre, evento_tipo, taller_nombre=None):
    # Definir el mensaje personalizado según el tipo de evento
    if evento_tipo == 1 and taller_nombre:
        mensaje_evento = f"Nos complace informar que ha sido inscrito en las <strong>{evento_nombre}</strong> para el taller <strong>{taller_nombre}</strong>"
    elif evento_tipo == 2:
        mensaje_evento = f"Nos complace informar que ha sido inscrito en la charla <strong>{evento_nombre}</strong>"
    elif evento_tipo == 3:
        mensaje_evento = f"Nos complace informar que ha sido inscrito en el microtaller <strong>{evento_nombre}</strong>"
    elif evento_tipo == 4:
        mensaje_evento = f"Nos complace informar que ha sido inscrito en el programa de acompañamiento áulico para el periodo <strong>{evento_nombre}</strong>"

    return f"""
    <html>
    <body style="font-family: Arial, Helvetica, sans-serif; color: #333; margin: 0; padding: 0; line-height: 1.6;">
        <!-- Contenedor principal centrado con ancho máximo -->
        
        <div style="max-width: 600px; margin: 0 auto; text-align: justify; padding: 20px; box-shadow: 0px 0px 10px rgba(0,0,0,0.1);">
            <!-- Imagen de la cabecera usando CID y forzando ancho completo -->
            <div style="text-align: center;">
                <img src="cid:cabecera" alt="Cabecera" style="width: 100%; height: auto;">
            </div>
            <!-- Línea horizontal de separación -->
            <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
            
            <!-- Contenido del mensaje -->
            <p style="margin-top: 20px;">Estimado/a</p>
            <p><strong>{docente_nombre}</strong></p>
            <p>Su despacho</p>
            <p>
                Reciba un cordial saludo de la <strong>Dirección de Innovación Educativa</strong>. {mensaje_evento}.
                Agradecemos su interés en participar y confiamos en que esta capacitación será una oportunidad para fortalecer sus habilidades y conocimientos.
            </p>
            <p>Sin otro particular, le extendemos nuestros mejores deseos.</p>
            
            <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
            <div style="text-align: center; margin-top: 20px;">
                <p>Atentamente,</p>
                <p><strong>Dirección de Innovación Educativa</strong></p>
            </div>
            <!-- Línea horizontal antes del pie de página -->
            <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
            
            <!-- Pie de página con información adicional -->
            <div style="text-align: center; font-size: 0.9em; color: #555;">
                <p>Teléfono: 4051000 ext 1271-1272 | <a href="mailto:capacitaciones.die@ucuenca.edu.ec">capacitaciones.die@ucuenca.edu.ec</a></p>
                <p style="font-size: 0.8em; color: #888; margin-top: 10px;"><em>* El contenido de este correo es responsabilidad de quien suscribe.<br><strong>Por favor no conteste este correo.</strong></em></p>
            </div>
        </div>
        <!-- Barra de pie de página -->
        <div style="background-color: #0e1b46; padding: 10px 0; text-align: center; color: #ffffff;">
            
        </div>
    </body>
    </html>
    """

def get_denial_email_content(docente_nombre, evento_nombre, evento_tipo, taller_nombre=None):
    # Definir el mensaje personalizado según el tipo de evento
    if evento_tipo == 1 and taller_nombre:
        mensaje_evento = f"su inscripción en las <strong>{evento_nombre}</strong> para el taller <strong>{taller_nombre}</strong> ha sido anulada."
    elif evento_tipo == 2:
        mensaje_evento = f"su inscripción en la charla <strong>{evento_nombre}</strong> ha sido anulada."
    elif evento_tipo == 3:
        mensaje_evento = f"su inscripción en el microtaller <strong>{evento_nombre}</strong> ha sido anulada."
    elif evento_tipo == 4:
        mensaje_evento = f"su inscripción en el programa de acompañamiento áulico para el periodo <strong>{evento_nombre}</strong> ha sido anulada."

    return f"""
    <html>
        <body style="font-family: Arial, Helvetica, sans-serif; color: #333; margin: 0; padding: 0; line-height: 1.6;">
            <!-- Contenedor principal centrado con ancho máximo -->
            
            <div style="max-width: 600px; margin: 0 auto; text-align: justify; padding: 20px; box-shadow: 0px 0px 10px rgba(0,0,0,0.1);">
                <!-- Imagen de la cabecera usando CID y forzando ancho completo -->
                <div style="text-align: center;">
                    <img src="cid:cabecera" alt="Cabecera" style="width: 100%; height: auto;">
                </div>
                <!-- Línea horizontal de separación -->
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                
                <!-- Contenido del mensaje -->
                <p style="margin-top: 20px;">Estimado/a</p>
                <p><strong>{docente_nombre}</strong></p>
                <p>Su despacho</p>
                <p>
                    Reciba un cordial saludo de la <strong>Dirección de Innovación Educativa</strong>. En respuesta a su solicitud, le informamos que {mensaje_evento} 
                    Esperamos que pueda participar en futuros espacios de formación.
                </p>
                <p>Sin otro particular, le extendemos nuestros mejores deseos.</p>
                
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                <div style="text-align: center; margin-top: 20px;">
                    <p>Atentamente,</p>
                    <p><strong>Dirección de Innovación Educativa</strong></p>
                </div>
                <!-- Línea horizontal antes del pie de página -->
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                
                <!-- Pie de página con información adicional -->
                <div style="text-align: center; font-size: 0.9em; color: #555;">
                    <p>Teléfono: 4051000 ext 1271-1272 | <a href="mailto:capacitaciones.die@ucuenca.edu.ec">capacitaciones.die@ucuenca.edu.ec</a></p>
                    <p style="font-size: 0.8em; color: #888; margin-top: 10px;"><em>* El contenido de este correo es responsabilidad de quien suscribe.<br><strong>Por favor no conteste este correo.</strong></em></p>
                </div>
            </div>
            <!-- Barra de pie de página -->
            <div style="background-color: #0e1b46; padding: 10px 0; text-align: center; color: #ffffff;">
                
            </div>
        </body>
    </html>
    """

def get_updated_email_content(evento):
    # Definir el mensaje personalizado según el tipo de evento   
    sesiones_info = ""
    if evento["tipo"] in [1, 3]:
        for sesion in evento["sesiones"]:
            if sesion["modalidad"] == "Presencial":
                ubicacion_info = f"<strong>Ubicación:</strong> {sesion['ubicacion']}<br>"
            else:
                ubicacion_info = f"<strong>Enlace:</strong> <a href='{sesion['ubicacion']}' target='_blank'>Ingrese aquí</a><br>"
            sesiones_info += f"""
                <strong>Sesión {sesion["fecha"]}:</strong>
                <ul>
                    <strong>Hora de inicio:</strong> {sesion["hora_inicio"]}<br>
                    <strong>Duración:</strong> {sesion["duracion"]} horas<br>
                    <strong>Modalidad:</strong> {sesion["modalidad"]}<br>
                    {ubicacion_info}
                </ul>
            """
            
    if evento["tipo"]== 1:
        mensaje_evento = f"las <strong>{evento['nombre']}</strong> para el taller <strong>{evento['taller']}</strong>: <br><br>{sesiones_info}"
    elif evento["tipo"] == 2:
        if evento["modalidad"] == "Presencial":
                ubicacion_info = f"<strong>Ubicación:</strong> {evento['ubicacion']}<br>"
        else:
            ubicacion_info = f"<strong>Enlace:</strong> <a href='{evento['ubicacion']}' target='_blank'>Ingrese aquí</a><br>"
        mensaje_evento = f"""la charla <strong>{evento['nombre']}</strong>: <br><br>
                                <ul>
                                    <strong>Hora de inicio:</strong> {evento['hora_inicio']}<br>
                                    <strong>Duración:</strong> {evento['duracion']} horas<br>
                                    <strong>Modalidad:</strong> {evento['modalidad']}<br>
                                    {ubicacion_info}
                                </ul>
                                """
    elif evento["tipo"] == 3:
        mensaje_evento = f"el microtaller <strong>{evento['nombre']}</strong>: <br><br>{sesiones_info}"
    
    return f"""
    <html>
        <body style="font-family: Arial, Helvetica, sans-serif; color: #333; margin: 0; padding: 0; line-height: 1.6;">
            <!-- Contenedor principal centrado con ancho máximo -->
            
            <div style="max-width: 600px; margin: 0 auto; text-align: justify; padding: 20px; box-shadow: 0px 0px 10px rgba(0,0,0,0.1);">
                <!-- Imagen de la cabecera usando CID y forzando ancho completo -->
                <div style="text-align: center;">
                    <img src="cid:cabecera" alt="Cabecera" style="width: 100%; height: auto;">
                </div>
                <!-- Línea horizontal de separación -->
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                
                <!-- Contenido del mensaje -->
                <p style="margin-top: 20px;">Estimado/a</p>
                <p>Docente</p>
                <p>Su despacho</p>
                <p>
                    Reciba un cordial saludo de la <strong>Dirección de Innovación Educativa</strong>. Indicamos que se realizaron cambios en {mensaje_evento}.
                </p>
                <p>Agradecemos su interés en participar y confiamos en que esta capacitación será una oportunidad para fortalecer sus habilidades y conocimientos.
                Sin otro particular, le extendemos nuestros mejores deseos.
                </p>
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                <div style="text-align: center; margin-top: 20px;">
                    <p>Atentamente,</p>
                    <p><strong>Dirección de Innovación Educativa</strong></p>
                </div>
                <!-- Línea horizontal antes del pie de página -->
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                
                <!-- Pie de página con información adicional -->
                <div style="text-align: center; font-size: 0.9em; color: #555;">
                    <p>Teléfono: 4051000 ext 1271-1272 | <a href="mailto:capacitaciones.die@ucuenca.edu.ec">capacitaciones.die@ucuenca.edu.ec</a></p>
                    <p style="font-size: 0.8em; color: #888; margin-top: 10px;"><em>* El contenido de este correo es responsabilidad de quien suscribe.<br><strong>Por favor no conteste este correo.</strong></em></p>
                </div>
            </div>
            <!-- Barra de pie de página -->
            <div style="background-color: #0e1b46; padding: 10px 0; text-align: center; color: #ffffff;">
                
            </div>
        </body>
    </html>
    """
    
def get_reproved_email_content(docente_nombre, evento_nombre, evento_tipo, asistio, aprobo, taller_nombre=None):
    # Definir el mensaje personalizado según el tipo de evento
    if evento_tipo == 1 and taller_nombre:
        mensaje_evento = f"el taller <strong>{taller_nombre}</strong> correspondiente a las <strong>{evento_nombre}</strong>."
    elif evento_tipo == 2:
        mensaje_evento = f"la charla <strong>{evento_nombre}</strong>"
    elif evento_tipo == 3:
        mensaje_evento = f"el microtaller <strong>{evento_nombre}</strong>"
        
    if not asistio:
        mensaje_motivo = "incumplimiento en asistencia"
    elif asistio and not aprobo:
        mensaje_motivo = "que no alcanzó la nota mínima requerida"

    return f"""
    <html>
        <body style="font-family: Arial, Helvetica, sans-serif; color: #333; margin: 0; padding: 0; line-height: 1.6;">
            <!-- Contenedor principal centrado con ancho máximo -->
            
            <div style="max-width: 600px; margin: 0 auto; text-align: justify; padding: 20px; box-shadow: 0px 0px 10px rgba(0,0,0,0.1);">
                <!-- Imagen de la cabecera usando CID y forzando ancho completo -->
                <div style="text-align: center;">
                    <img src="cid:cabecera" alt="Cabecera" style="width: 100%; height: auto;">
                </div>
                <!-- Línea horizontal de separación -->
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                
                <!-- Contenido del mensaje -->
                <p style="margin-top: 20px;">Estimado/a</p>
                <p><strong>{docente_nombre}</strong></p>
                <p>Su despacho</p>
                
            
                <p>De mi consideración:</p>
                
                <p>
                    Por medio de la presente, le informamos que {mensaje_evento} no ha sido completado de manera satisfactoria debido a {mensaje_motivo}.
                </p>
                
                Sin otro particular, le extendemos nuestros mejores deseos.
                </p>
                
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                <div style="text-align: center; margin-top: 20px;">
                    <p>Atentamente,</p>
                    <p><strong>Dirección de Innovación Educativa</strong></p>
                </div>
                <!-- Línea horizontal antes del pie de página -->
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                
                <!-- Pie de página con información adicional -->
                <div style="text-align: center; font-size: 0.9em; color: #555;">
                    <p>Teléfono: 4051000 ext 1271-1272 | <a href="mailto:capacitaciones.die@ucuenca.edu.ec">capacitaciones.die@ucuenca.edu.ec</a></p>
                    <p style="font-size: 0.8em; color: #888; margin-top: 10px;"><em>* El contenido de este correo es responsabilidad de quien suscribe.<br><strong>Por favor no conteste este correo.</strong></em></p>
                </div>
            </div>
            <!-- Barra de pie de página -->
            <div style="background-color: #0e1b46; padding: 10px 0; text-align: center; color: #ffffff;">
                
            </div>
        </body>
    </html>
    """
    
def get_approved_email_content(docente_nombre, evento_nombre, evento_tipo, taller_nombre=None):
    # Definir el mensaje personalizado según el tipo de evento
    if evento_tipo == 1 and taller_nombre:
        mensaje_evento = f"el taller <strong>{taller_nombre}</strong> correspondiente a las <strong>{evento_nombre}</strong>."
    elif evento_tipo == 2:
        mensaje_evento = f"la charla <strong>{evento_nombre}</strong>"
    elif evento_tipo == 3:
        mensaje_evento = f"el microtaller <strong>{evento_nombre}</strong>"

    return f"""
    <html>
        <body style="font-family: Arial, Helvetica, sans-serif; color: #333; margin: 0; padding: 0; line-height: 1.6;">
            <!-- Contenedor principal centrado con ancho máximo -->
            
            <div style="max-width: 600px; margin: 0 auto; text-align: justify; padding: 20px; box-shadow: 0px 0px 10px rgba(0,0,0,0.1);">
                <!-- Imagen de la cabecera usando CID y forzando ancho completo -->
                <div style="text-align: center;">
                    <img src="cid:cabecera" alt="Cabecera" style="width: 100%; height: auto;">
                </div>
                <!-- Línea horizontal de separación -->
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                
                <!-- Contenido del mensaje -->
                <p style="margin-top: 20px;">Estimado/a</p>
                <p><strong>{docente_nombre}</strong></p>
                <p>Su despacho</p>
                
            
                <p>De mi consideración:</p>
                
                <p>
                    Nos complace informarle que ha completado {mensaje_evento} de manera satisfactoria. Puede descargar su informe de horas totales acumuladas durante los diversos eventos <a href='pentagono.ucuenca.edu.ec/eventos' target='_blank'>aquí</a>.
                </p>
                
                Sin otro particular, le extendemos nuestros mejores deseos.
                </p>
                
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                <div style="text-align: center; margin-top: 20px;">
                    <p>Atentamente,</p>
                    <p><strong>Dirección de Innovación Educativa</strong></p>
                </div>
                <!-- Línea horizontal antes del pie de página -->
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                
                <!-- Pie de página con información adicional -->
                <div style="text-align: center; font-size: 0.9em; color: #555;">
                    <p>Teléfono: 4051000 ext 1271-1272 | <a href="mailto:capacitaciones.die@ucuenca.edu.ec">capacitaciones.die@ucuenca.edu.ec</a></p>
                    <p style="font-size: 0.8em; color: #888; margin-top: 10px;"><em>* El contenido de este correo es responsabilidad de quien suscribe.<br><strong>Por favor no conteste este correo.</strong></em></p>
                </div>
            </div>
            <!-- Barra de pie de página -->
            <div style="background-color: #0e1b46; padding: 10px 0; text-align: center; color: #ffffff;">
                
            </div>
        </body>
    </html>
    """
    
def get_observation_email_content(docente_nombre, evento_nombre):

    return f"""
    <html>
        <body style="font-family: Arial, Helvetica, sans-serif; color: #333; margin: 0; padding: 0; line-height: 1.6;">
            <!-- Contenedor principal centrado con ancho máximo -->
            
            <div style="max-width: 600px; margin: 0 auto; text-align: justify; padding: 20px; box-shadow: 0px 0px 10px rgba(0,0,0,0.1);">
                <!-- Imagen de la cabecera usando CID y forzando ancho completo -->
                <div style="text-align: center;">
                    <img src="cid:cabecera" alt="Cabecera" style="width: 100%; height: auto;">
                </div>
                <!-- Línea horizontal de separación -->
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                
                <!-- Contenido del mensaje -->
                <p style="margin-top: 20px;">Estimado/a</p>
                <p><strong>{docente_nombre}</strong></p>
                <p>Su despacho</p>
                
            
                <p>De mi consideración:</p>
                
                <p>
                    Reciba un cordial saludo de la Dirección de Innovación Educativa. Nos complace informar que usted ha finalizado el proceso de Acompañamiento Áulico {evento_nombre} con éxito. Puede acceder al informe final <a href='pentagono.ucuenca.edu.ec/eventos' target='_blank'>aquí</a>. Agradecemos su interés en participar y confiamos en que este acompañamiento ha sido una valiosa oportunidad para fortalecer sus habilidades y conocimientos.
                </p>
                
                Sin otro particular, le extendemos nuestros mejores deseos.
                </p>
                
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                <div style="text-align: center; margin-top: 20px;">
                    <p>Atentamente,</p>
                    <p><strong>Dirección de Innovación Educativa</strong></p>
                </div>
                <!-- Línea horizontal antes del pie de página -->
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                
                <!-- Pie de página con información adicional -->
                <div style="text-align: center; font-size: 0.9em; color: #555;">
                    <p>Teléfono: 4051000 ext 1271-1272 | <a href="mailto:capacitaciones.die@ucuenca.edu.ec">capacitaciones.die@ucuenca.edu.ec</a></p>
                    <p style="font-size: 0.8em; color: #888; margin-top: 10px;"><em>* El contenido de este correo es responsabilidad de quien suscribe.<br><strong>Por favor no conteste este correo.</strong></em></p>
                </div>
            </div>
            <!-- Barra de pie de página -->
            <div style="background-color: #0e1b46; padding: 10px 0; text-align: center; color: #ffffff;">
                
            </div>
        </body>
    </html>
    """
    
def get_accepted_certificate_email_content(docente_nombre, certificado, horas_acreditadas, horas_disponibles):

    return f"""
    <html>
        <body style="font-family: Arial, Helvetica, sans-serif; color: #333; margin: 0; padding: 0; line-height: 1.6;">
            <!-- Contenedor principal centrado con ancho máximo -->
            
            <div style="max-width: 600px; margin: 0 auto; text-align: justify; padding: 20px; box-shadow: 0px 0px 10px rgba(0,0,0,0.1);">
                <!-- Imagen de la cabecera usando CID y forzando ancho completo -->
                <div style="text-align: center;">
                    <img src="cid:cabecera" alt="Cabecera" style="width: 100%; height: auto;">
                </div>
                <!-- Línea horizontal de separación -->
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                
                <!-- Contenido del mensaje -->
                <p style="margin-top: 20px;">Estimado/a</p>
                <p><strong>{docente_nombre}</strong></p>
                <p>Su despacho</p>
                
            
                <p>De mi consideración:</p>
                
                <p>
                    Reciba un cordial saludo de la <strong>Dirección de Innovación Educativa</strong>. Nos complace confirmar que su certificado <strong>"{certificado}"</strong> ha sido aprobado en el programa de Formación Docentes D360. Se le han acreditado {horas_acreditadas} horas, teniendo un total de {horas_disponibles} horas disponibles para certificaciones externas.
                </p>
                
                Sin otro particular, le extendemos nuestros mejores deseos.
                </p>
                
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                <div style="text-align: center; margin-top: 20px;">
                    <p>Atentamente,</p>
                    <p><strong>Dirección de Innovación Educativa</strong></p>
                </div>
                <!-- Línea horizontal antes del pie de página -->
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                
                <!-- Pie de página con información adicional -->
                <div style="text-align: center; font-size: 0.9em; color: #555;">
                    <p>Teléfono: 4051000 ext 1271-1272 | <a href="mailto:capacitaciones.die@ucuenca.edu.ec">capacitaciones.die@ucuenca.edu.ec</a></p>
                    <p style="font-size: 0.8em; color: #888; margin-top: 10px;"><em>* El contenido de este correo es responsabilidad de quien suscribe.<br><strong>Por favor no conteste este correo.</strong></em></p>
                </div>
            </div>
            <!-- Barra de pie de página -->
            <div style="background-color: #0e1b46; padding: 10px 0; text-align: center; color: #ffffff;">
                
            </div>
        </body>
    </html>
    """
    
def get_denied_certificate_email_content(docente_nombre, certificado):

    return f"""
    <html>
        <body style="font-family: Arial, Helvetica, sans-serif; color: #333; margin: 0; padding: 0; line-height: 1.6;">
            <!-- Contenedor principal centrado con ancho máximo -->
            
            <div style="max-width: 600px; margin: 0 auto; text-align: justify; padding: 20px; box-shadow: 0px 0px 10px rgba(0,0,0,0.1);">
                <!-- Imagen de la cabecera usando CID y forzando ancho completo -->
                <div style="text-align: center;">
                    <img src="cid:cabecera" alt="Cabecera" style="width: 100%; height: auto;">
                </div>
                <!-- Línea horizontal de separación -->
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                
                <!-- Contenido del mensaje -->
                <p style="margin-top: 20px;">Estimado/a</p>
                <p><strong>{docente_nombre}</strong></p>
                <p>Su despacho</p>
                
            
                <p>De mi consideración:</p>
                
                <p>
                    Reciba un cordial saludo de la <strong>Dirección de Innovación Educativa</strong>. Le informamos que, tras revisar su solicitud, la acreditación del certificado por su capacitación externa <strong>"{certificado}"</strong> ha sido rechazada, ya que no se alinea con los lineamientos internos de nuestra Dirección.
                </p>
                
                Sin otro particular, le extendemos nuestros mejores deseos.
                </p>
                
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                <div style="text-align: center; margin-top: 20px;">
                    <p>Atentamente,</p>
                    <p><strong>Dirección de Innovación Educativa</strong></p>
                </div>
                <!-- Línea horizontal antes del pie de página -->
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                
                <!-- Pie de página con información adicional -->
                <div style="text-align: center; font-size: 0.9em; color: #555;">
                    <p>Teléfono: 4051000 ext 1271-1272 | <a href="mailto:capacitaciones.die@ucuenca.edu.ec">capacitaciones.die@ucuenca.edu.ec</a></p>
                    <p style="font-size: 0.8em; color: #888; margin-top: 10px;"><em>* El contenido de este correo es responsabilidad de quien suscribe.<br><strong>Por favor no conteste este correo.</strong></em></p>
                </div>
            </div>
            <!-- Barra de pie de página -->
            <div style="background-color: #0e1b46; padding: 10px 0; text-align: center; color: #ffffff;">
                
            </div>
        </body>
    </html>
    """
    
def get_unasistance_alert_email_content(docente_nombre,docente_correo, eventos):

    eventos_html = f"<p>Se ha inscrito sin asistir a los siguientes {len(eventos)} eventos:</p>"
    eventos_html += "<ul>"  # Iniciar lista desordenada
    for evento in eventos:
        eventos_html += f"<li>{evento}</li>"  # Agregar cada evento como elemento de lista
    eventos_html += "</ul>"
    
    return f"""
    <html>
        <body style="font-family: Arial, Helvetica, sans-serif; color: #333; margin: 0; padding: 0; line-height: 1.6;">
            <!-- Contenedor principal centrado con ancho máximo -->
            
            <div style="max-width: 600px; margin: 0 auto; text-align: justify; padding: 20px; box-shadow: 0px 0px 10px rgba(0,0,0,0.1);">
                <!-- Imagen de la cabecera usando CID y forzando ancho completo -->
                <div style="text-align: center;">
                    <img src="cid:cabecera" alt="Cabecera" style="width: 100%; height: auto;">
                </div>
                <!-- Línea horizontal de separación -->
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                
                <!-- Contenido del mensaje -->
                <p>El/La docente <strong>{docente_nombre}</strong> con correo eléctrónico: <strong>{docente_correo}</strong></p>
                                
                {eventos_html}
                
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                <div style="text-align: center; margin-top: 20px;">
                    <p>Atentamente,</p>
                    <p><strong>Dirección de Innovación Educativa</strong></p>
                </div>
                <!-- Línea horizontal antes del pie de página -->
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                
                <!-- Pie de página con información adicional -->
                <div style="text-align: center; font-size: 0.9em; color: #555;">
                    <p>Teléfono: 4051000 ext 1271-1272 | <a href="mailto:capacitaciones.die@ucuenca.edu.ec">capacitaciones.die@ucuenca.edu.ec</a></p>
                    <p style="font-size: 0.8em; color: #888; margin-top: 10px;"><em>* El contenido de este correo es responsabilidad de quien suscribe.<br><strong>Por favor no conteste este correo.</strong></em></p>
                </div>
            </div>
            <!-- Barra de pie de página -->
            <div style="background-color: #0e1b46; padding: 10px 0; text-align: center; color: #ffffff;">
                
            </div>
        </body>
    </html>
    """
    
def get_finish_alert_email_content(docente_nombre, docente_correo, facultades):
       
    return f"""
    <html>
        <body style="font-family: Arial, Helvetica, sans-serif; color: #333; margin: 0; padding: 0; line-height: 1.6;">
            <!-- Contenedor principal centrado con ancho máximo -->
            
            <div style="max-width: 600px; margin: 0 auto; text-align: justify; padding: 20px; box-shadow: 0px 0px 10px rgba(0,0,0,0.1);">
                <!-- Imagen de la cabecera usando CID y forzando ancho completo -->
                <div style="text-align: center;">
                    <img src="cid:cabecera" alt="Cabecera" style="width: 100%; height: auto;">
                </div>
                <!-- Línea horizontal de separación -->
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                
                <!-- Contenido del mensaje -->
                <p>El/La siguiente docente ha cumplido con las 140 horas del programa de formación docente D360:</p>
                <ul>
                    <li><strong>Nombre: </strong>{docente_nombre}</li>
                    <li><strong>Correo: </strong>{docente_correo}</li>
                    <li><strong>Facultad/es: </strong>{facultades}</li>
                </ul>              
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                <div style="text-align: center; margin-top: 20px;">
                    <p>Atentamente,</p>
                    <p><strong>Dirección de Innovación Educativa</strong></p>
                </div>
                <!-- Línea horizontal antes del pie de página -->
                <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
                
                <!-- Pie de página con información adicional -->
                <div style="text-align: center; font-size: 0.9em; color: #555;">
                    <p>Teléfono: 4051000 ext 1271-1272 | <a href="mailto:capacitaciones.die@ucuenca.edu.ec">capacitaciones.die@ucuenca.edu.ec</a></p>
                    <p style="font-size: 0.8em; color: #888; margin-top: 10px;"><em>* El contenido de este correo es responsabilidad de quien suscribe.<br><strong>Por favor no conteste este correo.</strong></em></p>
                </div>
            </div>
            <!-- Barra de pie de página -->
            <div style="background-color: #0e1b46; padding: 10px 0; text-align: center; color: #ffffff;">
                
            </div>
        </body>
    </html>
    """
    
def get_reminder_email_content(evento_nombre, evento_tipo, fecha):
    # Definir el mensaje personalizado según el tipo de evento
    if evento_tipo == 1:
        mensaje_evento = f"Le recordamos que las <strong>{evento_nombre}</strong> se desarrollarán a partir del día "
    elif evento_tipo == 2:
        mensaje_evento = f"Le recordamos que la charla <strong>{evento_nombre}</strong> se desarrollará el día "
    elif evento_tipo == 3:
        mensaje_evento = f"Le recordamos que el microtaller <strong>{evento_nombre}</strong> se desarrollará el día "
    
    return f"""
    <html>
    <body style="font-family: Arial, Helvetica, sans-serif; color: #333; margin: 0; padding: 0; line-height: 1.6;">
        <!-- Contenedor principal centrado con ancho máximo -->
        
        <div style="max-width: 600px; margin: 0 auto; text-align: justify; padding: 20px; box-shadow: 0px 0px 10px rgba(0,0,0,0.1);">
            <!-- Imagen de la cabecera usando CID y forzando ancho completo -->
            <div style="text-align: center;">
                <img src="cid:cabecera" alt="Cabecera" style="width: 100%; height: auto;">
            </div>
            <!-- Línea horizontal de separación -->
            <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
            
            <!-- Contenido del mensaje -->
            <p style="margin-top: 20px;">Estimado/a</p>
            <p>Docente</p>
            <p>Su despacho</p>
            <p>
                Reciba un cordial saludo de la <strong>Dirección de Innovación Educativa</strong>. {mensaje_evento}{fecha}.
                Esperamos contar con su participación en esta valiosa oportunidad para fortalecer sus habilidades y conocimientos.
            </p>
            <p>Sin otro particular, le extendemos nuestros mejores deseos.</p>
            
            <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
            <div style="text-align: center; margin-top: 20px;">
                <p>Atentamente,</p>
                <p><strong>Dirección de Innovación Educativa</strong></p>
            </div>
            <!-- Línea horizontal antes del pie de página -->
            <hr style="border: none; border-top: 1px solid #002856; margin: 20px 0;">
            
            <!-- Pie de página con información adicional -->
            <div style="text-align: center; font-size: 0.9em; color: #555;">
                <p>Teléfono: 4051000 ext 1271-1272 | <a href="mailto:capacitaciones.die@ucuenca.edu.ec">capacitaciones.die@ucuenca.edu.ec</a></p>
                <p style="font-size: 0.8em; color: #888; margin-top: 10px;"><em>* El contenido de este correo es responsabilidad de quien suscribe.<br><strong>Por favor no conteste este correo.</strong></em></p>
            </div>
        </div>
        <!-- Barra de pie de página -->
        <div style="background-color: #0e1b46; padding: 10px 0; text-align: center; color: #ffffff;">
            
        </div>
    </body>
    </html>
    """