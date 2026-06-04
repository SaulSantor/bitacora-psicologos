import logging
from app.database import db, Notificacion, Cita, Psicologo, Paciente
from flask_mail import Message
from app import mail
from datetime import datetime
import configparser

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("notification_sender.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Cargar configuración
config = configparser.ConfigParser()
config.read('config.ini')

def enviar_email(destinatario, asunto, cuerpo):
    """Función para enviar un correo electrónico usando Flask-Mail"""
    msg = Message(
        asunto,
        recipients=[destinatario],
        body=cuerpo
    )
    try:
        mail.send(msg)
        return True
    except Exception as e:
        logger.error(f"Error al enviar el correo: {str(e)}")
        return False

def enviar_sms(destinatario, mensaje):
    """Función de ejemplo para enviar un SMS. (Debes configurar un proveedor de SMS)"""
    try:
        # Ejemplo de integración con API de SMS
        print(f"Enviando SMS a {destinatario}: {mensaje}")
        return True  # Suponemos que el SMS fue enviado con éxito
    except Exception as e:
        logger.error(f"Error al enviar el SMS: {str(e)}")
        return False

def process_notifications():
    """Procesa todas las notificaciones pendientes"""
    try:
        # Consultar notificaciones pendientes de la base de datos usando SQLAlchemy
        notificaciones = db.session.query(Notificacion).filter(
            Notificacion.enviada == False,
            Notificacion.tiempo_envio <= datetime.now()
        ).all()

        for notif in notificaciones:
            print(f"Notificación enviada: {notif.id}")

            # Obtener detalles de la cita asociada
            cita = Cita.query.get(notif.cita_id)
            if cita:
                psicologo = Psicologo.query.get(cita.psicologo_id)
                paciente = Paciente.query.get(cita.paciente_id)

                # Generar el cuerpo del correo o SMS
                if notif.tipo == 'email':
                    cuerpo = f"Hola {paciente.nombre},\n\nTienes una cita con {psicologo.nombre} el {cita.fecha}."
                    enviado = enviar_email(notif.destinatario, 'Recordatorio de cita', cuerpo)
                elif notif.tipo == 'sms':
                    mensaje = f"Recordatorio: Tienes una cita con {psicologo.nombre} el {cita.fecha}."
                    enviado = enviar_sms(notif.destinatario, mensaje)

                # Si la notificación se envió con éxito, actualizar la base de datos
                if enviado:
                    notif.enviada = True
                    notif.fecha_envio = datetime.now()  # Establecer la fecha y hora de envío
                    db.session.commit()
                    print(f"Notificación {notif.id} enviada con éxito.")
                else:
                    print(f"Error al enviar la notificación {notif.id}")
        
        db.session.commit()

    except Exception as e:
        logger.error(f"Error procesando notificaciones: {str(e)}")
        if 'db' in locals():
            db.session.rollback()
