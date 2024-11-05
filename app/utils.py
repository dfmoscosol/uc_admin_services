import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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

def send_email(subject, recipient, body):
    sender = current_app.config['MAIL_USERNAME']
    password = current_app.config['MAIL_PASSWORD']

    # Configuración del mensaje
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = subject

    # Cuerpo del correo
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Conexión al servidor SMTP de Gmail
        server = smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT'])
        server.ehlo()  # Identificación con el servidor
        server.starttls()  # Iniciar conexión TLS
        server.ehlo()  # Identificación nuevamente después de iniciar TLS
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()

        return 'Correo enviado con éxito'
    except Exception as e:
        return f'Error al enviar el correo: {e}'
