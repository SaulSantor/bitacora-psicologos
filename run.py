from app import create_app
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import logging
import app.send_notifications as send_notifications
import atexit
from app import create_app, db
from app.database import Usuario, Rol
from datetime import datetime
from werkzeug.security import generate_password_hash

app = create_app()

if __name__ == '__main__':
    # Determinar el puerto (útil para despliegue en plataformas como Heroku)
    port = int(os.environ.get('PORT', 5000))
    
    # Iniciar la aplicación
    app.run(host='localhost', port=port, debug=True)