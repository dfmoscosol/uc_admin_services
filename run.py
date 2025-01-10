from app import app, db
from app.scheduled_tasks import enviar_recordatorios_eventos
from flask_apscheduler import APScheduler

def enviar_recordatorios_con_contexto():
    with app.app_context():
        enviar_recordatorios_eventos()

# Configura APScheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# Programa la tarea para que se ejecute todos los días a las 9:59 AM
scheduler.add_job(
    id='enviar_recordatorios_eventos',  # ID único para la tarea
    func=enviar_recordatorios_con_contexto,  # Llama a la función de contenedor con el contexto
    trigger='cron',
    hour=8,
    minute=0,
)

if __name__ == "__main__":
    app.run()


