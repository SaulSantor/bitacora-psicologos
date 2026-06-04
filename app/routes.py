import secrets
import string
import traceback
from flask import Blueprint, Request, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from app.database import Nota, NotificacionSistema, db, Psicologo, Paciente, Cita, Configuracion, Rol, Notificacion, Usuario, get_db_connection, Contacto, TipoCita, psicologo_tipo_cita
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_
import os
import json
from datetime import datetime, timedelta
from flask_wtf.csrf import generate_csrf
from sqlalchemy.orm import joinedload
from datetime import date
import pyodbc
from datetime import timedelta
from flask import request, jsonify
from flask_login import login_required, current_user
from app import db
import logging
from app.utils import enviar_email_credenciales, enviar_notificacion_contacto, enviar_respuesta_contacto
from flask import send_file
from flask_mail import Message
from app import mail  # Asegúrate de que tienes Flask-Mail configurado
from sqlalchemy import insert, delete
from app.database import psicologo_tipo_cita  # Asegúrate de importar la tabla de asociación


# Crear Blueprint
main = Blueprint('main', __name__)
logger = logging.getLogger(__name__)



def get_date_range(periodo):
    today = datetime.now()
    
    if periodo == 'semana':
        # Esta semana (lunes a domingo)
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        return start_of_week.replace(hour=0, minute=0, second=0), end_of_week.replace(hour=23, minute=59, second=59)
    
    elif periodo == 'mes':
        # Este mes
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0)
        # Último día del mes actual
        next_month = today.replace(day=28) + timedelta(days=4)
        last_day = (next_month - timedelta(days=next_month.day)).day
        end_of_month = today.replace(day=last_day, hour=23, minute=59, second=59)
        return start_of_month, end_of_month
    
    elif periodo == 'trimestre':
        # Este trimestre
        current_quarter = (today.month - 1) // 3 + 1
        start_month = (current_quarter - 1) * 3 + 1
        end_month = current_quarter * 3
        
        start_of_quarter = today.replace(month=start_month, day=1, hour=0, minute=0, second=0)
        
        # Último día del trimestre
        if end_month == 12:
            end_of_quarter = today.replace(month=end_month, day=31, hour=23, minute=59, second=59)
        else:
            end_of_quarter = today.replace(month=end_month + 1, day=1, hour=0, minute=0, second=0) - timedelta(seconds=1)
        
        return start_of_quarter, end_of_quarter
    
    elif periodo == 'año':
        # Este año
        start_of_year = today.replace(month=1, day=1, hour=0, minute=0, second=0)
        end_of_year = today.replace(month=12, day=31, hour=23, minute=59, second=59)
        return start_of_year, end_of_year
    
    else:  # 'todo' o cualquier otro valor
        # Sin límite de tiempo (solo aplica a los usuarios activos)
        return None, None


# Suponiendo que estás utilizando pyodbc o similar para conectar con SQL Server

from flask import session, url_for, redirect, request, jsonify
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os
import pickle

SCOPES = ['https://www.googleapis.com/auth/calendar']



@main.route('/api/google-auth', methods=['GET'])
@login_required
def google_auth():
    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=SCOPES,
        redirect_uri=url_for('main.google_auth_callback', _external=True)
    )
    redirect_uri = url_for('main.google_auth_callback', _external=True)
    current_app.logger.info(f"Redirect URI enviada: {redirect_uri}")
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    session['redirect_after_auth'] = request.referrer or url_for('main.nueva_cita')
    return redirect(authorization_url)


@main.route('/api/google-auth-callback', methods=['GET'])
@login_required
def google_auth_callback():
    state = session.get('state')
    if not state or state != request.args.get('state'):
        flash('Estado inválido', 'danger')
        return redirect(url_for('main.nueva_cita'))

    try:
        flow = Flow.from_client_secrets_file(
            'client_secret.json',
            scopes=SCOPES,
            redirect_uri=url_for('main.google_auth_callback', _external=True)
        )
        flow.fetch_token(authorization_response=request.url)
        creds = flow.credentials

        token_path = f'token_{current_user.id}.pickle'
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

        redirect_url = session.get('redirect_after_auth', url_for('main.nueva_cita'))
        flash('Autenticación con Google completada', 'success')
        return redirect(redirect_url)
    except Exception as e:
        current_app.logger.error(f"Error en autenticación: {str(e)}")
        flash(f'Error en autenticación', 'danger')
        return redirect(url_for('main.nueva_cita'))


@main.route('/api/sync-google-calendar', methods=['POST'])
@login_required
def sync_google_calendar():
    try:
        data = request.json
        cita_id = data.get('cita_id')
        fecha = data.get('fecha')
        notifications = data.get('notifications', {})
        summary = data.get('summary', 'Cita')
        description = data.get('description', '')
        duration = data.get('duration', 60)

        if not cita_id or not fecha:
            return jsonify({
                'success': False,
                'message': 'Datos incompletos para sincronización'
            }), 400

        try:
            fecha_cita = datetime.fromisoformat(fecha.replace('Z', '+00:00'))
            fecha_fin = fecha_cita + timedelta(minutes=duration)
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Formato de fecha inválido'
            }), 400

        token_path = f'token_{current_user.id}.pickle'
        creds = None
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            return jsonify({
                'success': False,
                'message': 'Autenticación requerida',
                'redirect': url_for('main.google_auth')
            }), 401

        service = build('calendar', 'v3', credentials=creds)

        # Verificar solapamiento en Google Calendar
        events_result = service.events().list(
            calendarId='primary',
            timeMin=fecha_cita.isoformat(),
            timeMax=fecha_fin.isoformat(),
            singleEvents=True
        ).execute()
        events = events_result.get('items', [])

        if events:
            return jsonify({
                'success': False,
                'message': 'El horario seleccionado está ocupado en Google Calendar'
            }), 409

        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': fecha_cita.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': fecha_fin.isoformat(),
                'timeZone': 'UTC',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': notifications.get('email', 30)},
                    {'method': 'popup', 'minutes': notifications.get('popup', 10)}
                ]
            }
        }

        calendar_id = 'primary'
        event = service.events().insert(calendarId=calendar_id, body=event).execute()

        # Opcional: Guardar event_id en la base de datos
        cita = Cita.query.get(cita_id)
        cita.google_event_id = event.get('id')
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Cita sincronizada correctamente',
            'event_id': event.get('id')
        })

    except Exception as e:
        current_app.logger.error(f"Error en sincronización: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error interno al sincronizar: {str(e)}'
        }), 500



# Ruta principal
@main.route('/')
def index():
    return render_template('index.html')

@main.route('/paciente_dashboard')
def paciente_dashboard():
    return render_template('paciente_dashboard.html')

# Ruta de login
@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.tipo_usuario == 'psicologo':
            return redirect(url_for('main.psicologo'))
        elif current_user.tipo_usuario == 'paciente':
            return redirect(url_for('main.CITASPACIENTE'))
        elif current_user.tipo_usuario == 'admin':
            return redirect(url_for('main.verificar_psicologos'))  # Redireccionar administradores a la página de verificación
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if not usuario:
            flash('Email no encontrado.', 'danger')
            return redirect(url_for('main.login'))
            
        if usuario.esta_bloqueado():
            flash('Su cuenta está temporalmente bloqueada. Intente más tarde.', 'danger')
            return redirect(url_for('main.login'))
            
        if not usuario.check_password(password):
            usuario.registrar_login_fallido()
            db.session.commit()
            flash('Contraseña incorrecta.', 'danger')
            return redirect(url_for('main.login'))
        
        # Verificar estado de cuenta para psicólogos
        if usuario.tipo_usuario == 'psicologo' and not usuario.activo:
            # Verificar el estado del psicólogo
            psicologo = Psicologo.query.filter_by(usuario_id=usuario.id).first()
            
            if psicologo and psicologo.estado_verificacion == 'pendiente':
                flash('Tu cuenta está pendiente de verificación. Te notificaremos cuando sea aprobada.', 'info')
                return redirect(url_for('main.login'))
            elif psicologo and psicologo.estado_verificacion == 'rechazado':
                flash('Tu solicitud de psicólogo ha sido rechazada. Para más información, revisa tu email.', 'danger')
                return redirect(url_for('main.login'))
            elif psicologo and psicologo.estado_verificacion == 'info_adicional':
                flash('Se requiere información adicional para verificar tu cuenta. Por favor revisa tu email.', 'warning')
                return redirect(url_for('main.login'))
            else:
                flash('Tu cuenta no está activa. Contacta al administrador para más información.', 'danger')
                return redirect(url_for('main.login'))
        
        # Verificar 2FA si está habilitado
        if usuario.auth_dos_factores:
            # Guardar en sesión para verificación de 2FA
            session['usuario_2fa_id'] = usuario.id
            return redirect(url_for('main.verificar_2fa'))
        
        # Login exitoso
        login_user(usuario, remember=remember)
        usuario.registrar_login_exitoso()
        db.session.commit()
        
        # Configurar tiempo de sesión
        if usuario.cierre_sesion_auto:
            session.permanent = True
            current_app.permanent_session_lifetime = timedelta(minutes=usuario.tiempo_inactividad or 15)
        
        # Verificar notificaciones no leídas
        try:
            # Contar notificaciones no leídas para mostrar en la bandeja de entrada
            notificaciones_count = NotificacionSistema.query.filter_by(usuario_id=usuario.id, leida=False).count()
            if notificaciones_count > 0:
                flash(f'Tienes {notificaciones_count} notificaciones sin leer.', 'info')
        except Exception as e:
            print(f"Error al verificar notificaciones.")
        
        # Redireccionar según el tipo de usuario
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
            
        if usuario.tipo_usuario == 'psicologo':
            return redirect(url_for('main.psicologo'))
        elif usuario.tipo_usuario == 'paciente':
            return redirect(url_for('main.paciente_dashboard'))
        elif usuario.tipo_usuario == 'admin':
            return redirect(url_for('main.verificar_psicologos'))
        
        return redirect(url_for('main.index'))
        
    return render_template('login.html')



# Ruta para verificar 2FA
@main.route('/verificar-2fa', methods=['GET', 'POST'])
def verificar_2fa():
    if 'usuario_2fa_id' not in session:
        return redirect(url_for('main.login'))
        
    usuario_id = session.get('usuario_2fa_id')
    usuario = Usuario.query.get(usuario_id)
    
    if not usuario:
        return redirect(url_for('main.login'))
        
    if request.method == 'POST':
        token = request.form.get('token')
        
        if usuario.verificar_2fa(token):
            # 2FA exitoso
            login_user(usuario)
            usuario.registrar_login_exitoso()
            db.session.commit()
            session.pop('usuario_2fa_id', None)
            
            if usuario.tipo_usuario == 'psicologo':
                return redirect(url_for('main.psicologo'))
            elif usuario.tipo_usuario == 'paciente':
                return redirect(url_for('main.paciente_dashboard'))
                
            return redirect(url_for('main.index'))
        else:
            flash('Código incorrecto. Intente nuevamente.', 'danger')
    
    return render_template('verificar_2fa.html')




# Ruta para configurar 2FA
@main.route('/configurar-2fa', methods=['GET', 'POST'])
@login_required
def configurar_2fa():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'enable':
            # Generar secreto si no existe
            if not current_user.secreto_2fa:
                current_user.generar_secreto_2fa()
                
            # Verificar token ingresado
            token = request.form.get('token')
            if current_user.verificar_2fa(token):
                current_user.auth_dos_factores = True
                db.session.commit()
                flash('Autenticación de dos factores activada correctamente.', 'success')
            else:
                flash('Código incorrecto. Intente nuevamente.', 'danger')
                
        elif action == 'disable':
            current_user.auth_dos_factores = False
            db.session.commit()
            flash('Autenticación de dos factores desactivada.', 'info')
            
    # Generar URL para código QR si 2FA está deshabilitado
    qr_url = None
    if not current_user.auth_dos_factores:
        qr_url = current_user.get_qr_code_url()
        
    return render_template('configurar_2fa.html', qr_url=qr_url)







# Agregar estas funciones a tu archivo routes.py

# Función auxiliar para validar archivos
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Función para enviar email de confirmación de registro pendiente
def enviar_email_verificacion_pendiente(email, nombre):
    try:
        msg = Message(
            'Solicitud de verificación recibida',
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[email]
        )
        msg.body = f"""
        Hola {nombre},
        
        Hemos recibido tu solicitud de registro como psicólogo en nuestra plataforma.
        
        Nuestro equipo revisará tu documentación y verificará tus credenciales profesionales.
        Este proceso puede tomar entre 1-3 días hábiles.
        
        Te notificaremos por email cuando tu cuenta sea aprobada.
        
        Si tienes alguna pregunta, no dudes en contactarnos.
        
        Saludos,
        El equipo de la Plataforma
        """
        mail.send(msg)
    except Exception as e:
        print(f"Error al enviar email: {str(e)}")

# Función para enviar email de aprobación
def enviar_email_verificacion_aprobada(email, nombre):
    try:
        msg = Message(
            '¡Tu cuenta ha sido verificada!',
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[email]
        )
        msg.body = f"""
        Hola {nombre},
        
        ¡Buenas noticias! Tu cuenta de psicólogo ha sido verificada y aprobada.
        
        Ya puedes acceder a la plataforma con todas las funcionalidades disponibles.
        
        Gracias por unirte a nuestra comunidad.
        
        Saludos,
        El equipo de la Plataforma
        """
        mail.send(msg)
    except Exception as e:
        print(f"Error al enviar email: {str(e)}")

# Función para enviar email de rechazo
def enviar_email_verificacion_rechazada(email, nombre, motivo):
    try:
        msg = Message(
            'Resultado de verificación de cuenta',
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[email]
        )
        msg.body = f"""
        Hola {nombre},
        
        Hemos revisado tu solicitud para registrarte como psicólogo en nuestra plataforma.
        
        Lamentablemente, no podemos aprobar tu cuenta en este momento debido a:
        
        {motivo}
        
        Si consideras que esto es un error o deseas proporcionar información adicional, 
        por favor responde a este correo.
        
        Saludos,
        El equipo de la Plataforma
        """
        mail.send(msg)
    except Exception as e:
        print(f"Error al enviar email: {str(e)}")

# Función para enviar email solicitando más información
def enviar_email_verificacion_info_adicional(email, nombre, info_requerida):
    try:
        msg = Message(
            'Información adicional requerida para verificación',
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[email]
        )
        msg.body = f"""
        Hola {nombre},
        
        Estamos revisando tu solicitud para registrarte como psicólogo en nuestra plataforma.
        
        Necesitamos información adicional para continuar con el proceso de verificación:
        
        {info_requerida}
        
        Por favor, inicia sesión en tu cuenta y actualiza la información en tu perfil,
        o responde a este correo con los detalles solicitados.
        
        Saludos,
        El equipo de la Plataforma
        """
        mail.send(msg)
    except Exception as e:
        print(f"Error al enviar email: {str(e)}")

# Decorador para verificar que el usuario es administrador
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.tipo_usuario != 'admin':
            flash('No tienes permisos para acceder a esta página.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function






@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        password = request.form.get('password')
        tipo_usuario = request.form.get('tipo_usuario', 'psicologo')
        
        # Validar si el email ya está registrado
        usuario_existente = Usuario.query.filter_by(email=email).first()
        
        if usuario_existente:
            # Si el usuario existente es un admin, no permitir registro como psicólogo
            if usuario_existente.tipo_usuario == 'admin' and tipo_usuario == 'psicologo':
                flash('Este email de administrador no puede registrarse como psicólogo.', 'danger')
                return redirect(url_for('main.register'))
            
            flash('El email ya está registrado.', 'danger')
            return redirect(url_for('main.register'))
        
        # El resto del código permanece igual
        try:    
            # Obtener rol correspondiente
            rol = Rol.query.filter_by(nombre=tipo_usuario).first()
            if not rol:
                rol = Rol(nombre=tipo_usuario)
                db.session.add(rol)
                db.session.flush()
                print(f"Rol creado con ID: {rol.id}")
            
            # Determinar el estado inicial del usuario según su tipo
            activo = True if tipo_usuario == 'paciente' else False
            
            # Crear usuario
            nuevo_usuario = Usuario(
                email=email,
                password=password,
                fecha_registro=datetime.utcnow(),
                activo=activo,  # Solo los pacientes son activados automáticamente
                tipo_usuario=tipo_usuario,
                rol_id=rol.id,
                cierre_sesion_auto=True,
                tiempo_inactividad=15
            )
            
            db.session.add(nuevo_usuario)
            db.session.flush()
            print(f"Usuario creado con ID: {nuevo_usuario.id}")
            
            # Crear registro específico según tipo
            if tipo_usuario == 'psicologo': 
                # Obtener la especialidad y el título del formulario
                especialidad = request.form.get('especialidad', 'psicologia-clinica')
                otra_especialidad = request.form.get('otra_especialidad') if especialidad == 'otro' else None
                titulo = request.form.get('titulo_profesional', 'dr')
                
                # Obtener campos adicionales para verificación
                numero_licencia = request.form.get('numero_licencia')
                institucion = request.form.get('institucion')
                
                # Permitir subida de documentos para verificación
                archivo_titulo = request.files.get('archivo_titulo')
                archivo_licencia = request.files.get('archivo_licencia')
                
                # Guardar los archivos si fueron proporcionados
                ruta_titulo = None
                ruta_licencia = None
                
                if archivo_titulo and allowed_file(archivo_titulo.filename):
                    filename = secure_filename(f"{nuevo_usuario.id}_titulo.{archivo_titulo.filename.rsplit('.', 1)[1].lower()}")
                    ruta_titulo = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    archivo_titulo.save(ruta_titulo)
                
                if archivo_licencia and allowed_file(archivo_licencia.filename):
                    filename = secure_filename(f"{nuevo_usuario.id}_licencia.{archivo_licencia.filename.rsplit('.', 1)[1].lower()}")
                    ruta_licencia = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    archivo_licencia.save(ruta_licencia)
                
                nuevo_psicologo = Psicologo(
                    usuario_id=nuevo_usuario.id,
                    nombre=nombre,
                    apellido=apellido,
                    especialidad=especialidad if especialidad != 'otro' else otra_especialidad,
                    otra_especialidad=otra_especialidad,
                    titulo=titulo,
                    numero_licencia=numero_licencia,
                    institucion=institucion,
                    ruta_archivo_titulo=ruta_titulo,
                    ruta_archivo_licencia=ruta_licencia,
                    estado_verificacion='pendiente'  # Estado inicial de verificación
                )
                db.session.add(nuevo_psicologo)
                db.session.flush()
                
                # NUEVO: Método para asignar tipos de cita
                asignar_tipos_cita_a_psicologo(nuevo_psicologo)
                
                # Verificación adicional
                print(f"Psicólogo creado con ID: {nuevo_psicologo.id} y estado 'pendiente'")
                if not nuevo_psicologo.id:
                    raise Exception('No se pudo generar un ID para el psicólogo')
                
                # Recuperar de nuevo el psicólogo para confirmar
                psicologo_verificado = Psicologo.query.get(nuevo_psicologo.id)
                if not psicologo_verificado:
                    raise Exception(f'No se pudo recuperar el psicólogo con ID {nuevo_psicologo.id} después de crearlo')
                
                # Crear configuración básica
                configuracion = Configuracion(
                    psicologo_id=nuevo_psicologo.id,
                    notificaciones_email=True,
                    tiempo_anticipacion=60,
                    frecuencia_recordatorios=2,
                    alertas_cambios_citas=True,
                    alertas_pacientes_nuevos=True,
                    notificaciones_actualizacion=True,
                    sonidos_notificacion=False,
                    retencion_datos=5
                )
                db.session.add(configuracion)
                
                # Enviar notificación a administradores
                admins = Usuario.query.filter_by(tipo_usuario='admin').all()
                for admin in admins:
                    # Crear notificación para el administrador
                    NotificacionSistema.crear_notificacion_verificacion(
                        db.session, 
                        usuario_id=admin.id,
                        tipo='verificacion_psicologo',
                        referencia_id=nuevo_psicologo.id,
                        titulo='Nuevo psicólogo pendiente de verificación',
                        mensaje=f'Psicólogo {nombre} {apellido} ha solicitado verificación'
                    )
                
            elif tipo_usuario == 'paciente':
                # Código para pacientes (sin cambios)
                psicologo_id = request.form.get('psicologo_id')
                if not psicologo_id:
                    raise Exception('No se proporcionó un ID de psicólogo')
                
                psicologo = Psicologo.query.get(psicologo_id)
                if not psicologo:
                    raise Exception(f'El psicólogo con ID {psicologo_id} no existe en el sistema')
                
                nuevo_paciente = Paciente(
                    usuario_id=nuevo_usuario.id,
                    nombre=nombre,
                    apellido=apellido,
                    psicologo_id=psicologo_id
                )
                db.session.add(nuevo_paciente)
            
            # Commit final después de verificar todas las entidades
            db.session.commit()
            
            if tipo_usuario == 'psicologo':
                flash('¡Registro enviado! Tu cuenta está pendiente de verificación por nuestro equipo. Te notificaremos por email cuando sea aprobada.', 'info')
                # Enviar email de confirmación
                try:
                    enviar_email_verificacion_pendiente(email, nombre)
                except Exception as e:
                    print(f"Error al enviar email de verificación: {str(e)}")
            else:
                flash('¡Registro exitoso! Ya puedes iniciar sesión.', 'success')
            
            return redirect(url_for('main.login'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error en el registro: {str(e)}")  # Log detallado para depuración
            flash(f'Error al registrar el usuario', 'danger')
            psicologos = Psicologo.query.all()
            return render_template('register.html', psicologos=psicologos)
        
    # GET request
    psicologos = Psicologo.query.all()
    return render_template('register.html', psicologos=psicologos)

# Función separada para asignar tipos de cita
def asignar_tipos_cita_a_psicologo(psicologo):
    """
    Asigna tipos de cita activos a un psicólogo
    """
    from sqlalchemy import insert, delete

    # Inicializar tipos de cita si no existen
    if TipoCita.query.count() == 0:
        TipoCita.seed_default_types(db.session)

    # Obtener tipos de cita activos
    tipos_activos = TipoCita.query.filter_by(activo=True).all()
    print(f"Tipos activos: {tipos_activos}, tipo: {type(tipos_activos)}")  # Depuración
    # Limpiar asociaciones existentes
    db.session.execute(
        delete(psicologo_tipo_cita).where(
            psicologo_tipo_cita.c.psicologo_id == psicologo.id
        )
    )
    
    # Insertar nuevas asociaciones
    for tipo in tipos_activos:
        db.session.execute(
            insert(psicologo_tipo_cita).values(
                psicologo_id=psicologo.id, 
                tipo_cita_id=tipo.id
            )
        )





# Ruta de logout
@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))




@main.route("/terminos-condiciones")
def terminos_condiciones():
    return render_template("terminos_condiciones.html")

@main.route("/politica-privacidad")
def politica_privacidad():
    return render_template("politica_privacidad.html")





# Agregar estas rutas a tu archivo routes.py

# Ruta para la página del admin para ver psicólogos pendientes
@main.route('/admin/verificar-psicologos', methods=['GET'])
@login_required
@admin_required
def verificar_psicologos():
    psicologos_pendientes = db.session.query(Psicologo).join(Usuario, Psicologo.usuario_id == Usuario.id).filter(
        Psicologo.estado_verificacion == 'pendiente'
    ).all()
    fecha_limite = datetime.utcnow() - timedelta(days=7)
    psicologos_verificados = db.session.query(Psicologo).join(Usuario, Psicologo.usuario_id == Usuario.id).filter(
        Psicologo.estado_verificacion == 'verificado',
        Psicologo.fecha_verificacion >= fecha_limite
    ).all()
    return render_template(
        'admin/verificar_psicologos.html', 
        psicologos=psicologos_pendientes,
        psicologos_verificados=psicologos_verificados
    )



# Ruta para verificar un psicólogo específico
@main.route('/admin/verificar-psicologo/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def verificar_psicologo(id):
    psicologo = Psicologo.query.get_or_404(id)
    
    # Obtener el usuario manualmente hasta que se corrija la relación
    usuario = Usuario.query.get_or_404(psicologo.usuario_id)
    if not usuario:
        flash(f"El psicólogo con ID {id} no tiene un usuario válido asociado.", 'danger')
        return redirect(url_for('main.verificar_psicologos'))
    
    if request.method == 'POST':
        decision = request.form.get('decision')
        comentarios = request.form.get('comentarios', '')
        
        if decision == 'aprobar':
            psicologo.estado_verificacion = 'verificado'
            psicologo.fecha_verificacion = datetime.utcnow()
            psicologo.verificado_por = current_user.id
            psicologo.comentarios_verificacion = comentarios
            usuario.activo = True
            
            NotificacionSistema.crear_notificacion_verificacion(
                db.session,
                usuario_id=usuario.id,
                tipo='verificacion_aprobada',
                referencia_id=psicologo.id,
                mensaje=f'Tu cuenta de psicólogo ha sido verificada y activada. {comentarios if comentarios else ""}'
            )
            enviar_email_verificacion_aprobada(usuario.email, psicologo.nombre)
            db.session.commit()
            flash('Psicólogo verificado y cuenta activada con éxito.', 'success')
            
        elif decision == 'rechazar':
            psicologo.estado_verificacion = 'rechazado'
            psicologo.fecha_verificacion = datetime.utcnow()
            psicologo.verificado_por = current_user.id
            psicologo.comentarios_verificacion = comentarios
            
            NotificacionSistema.crear_notificacion_verificacion(
                db.session,
                usuario_id=usuario.id,
                tipo='verificacion_rechazada',
                referencia_id=psicologo.id,
                mensaje=f'Tu solicitud de verificación como psicólogo ha sido rechazada. Motivo: {comentarios}'
            )
            enviar_email_verificacion_rechazada(usuario.email, psicologo.nombre, comentarios)
            db.session.commit()
            flash('Solicitud de psicólogo rechazada.', 'info')
            
        elif decision == 'solicitar_mas_info':
            psicologo.estado_verificacion = 'info_adicional'
            psicologo.comentarios_verificacion = comentarios
            
            NotificacionSistema.crear_notificacion_verificacion(
                db.session,
                usuario_id=usuario.id,
                tipo='verificacion_info_adicional',
                referencia_id=psicologo.id,
                mensaje=f'Se requiere información adicional para verificar tu cuenta: {comentarios}'
            )
            enviar_email_verificacion_info_adicional(usuario.email, psicologo.nombre, comentarios)
            db.session.commit()
            flash('Se ha solicitado información adicional al psicólogo.', 'info')
        
        notificaciones = NotificacionSistema.query.filter_by(
            referencia_id=psicologo.id, 
            tipo='verificacion_psicologo',
            usuario_id=current_user.id
        ).all()
        for notif in notificaciones:
            notif.leida = True
        db.session.commit()
        
        return redirect(url_for('main.verificar_psicologos'))
        
    return render_template(
        'admin/detalle_verificacion.html',
        psicologo=psicologo,
        usuario=usuario
    )





# API para obtener detalles de verificación de un psicólogo
@main.route('/api/admin/psicologo/<int:id>/verificacion')
@login_required
@admin_required
def api_detalles_verificacion(id):
    try:
        psicologo = Psicologo.query.get_or_404(id)
        
        # Obtener el usuario manualmente
        usuario = Usuario.query.get(psicologo.usuario_id)
        if not usuario:
            return jsonify({
                'success': False,
                'message': f"El psicólogo con ID {id} no tiene un usuario válido asociado"
            }), 400
        
        return jsonify({
            'success': True,
            'psicologo': {
                'id': psicologo.id,
                'nombre_completo': f"{psicologo.nombre} {psicologo.apellido}",
                'email': usuario.email,
                'especialidad': psicologo.especialidad,
                'titulo': psicologo.titulo,
                'numero_licencia': psicologo.numero_licencia,
                'institucion': psicologo.institucion,
                'estado_verificacion': psicologo.estado_verificacion,
                'fecha_verificacion': psicologo.fecha_verificacion.isoformat() if psicologo.fecha_verificacion else None,
                'comentarios_verificacion': psicologo.comentarios_verificacion,
                'tiene_archivo_titulo': bool(psicologo.ruta_archivo_titulo),
                'tiene_archivo_licencia': bool(psicologo.ruta_archivo_licencia),
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500





# Ruta para descargar documentos de verificación
@main.route('/admin/psicologo/<int:id>/documento/<tipo>')
@login_required
@admin_required
def descargar_documento(id, tipo):
    psicologo = Psicologo.query.get_or_404(id)
    
    if tipo == 'titulo':
        if not psicologo.ruta_archivo_titulo:
            flash('Este psicólogo no ha subido su título.', 'warning')
            return redirect(url_for('main.verificar_psicologo', id=id))
        return send_file(psicologo.ruta_archivo_titulo, as_attachment=True)
    
    elif tipo == 'licencia':
        if not psicologo.ruta_archivo_licencia:
            flash('Este psicólogo no ha subido su licencia.', 'warning')
            return redirect(url_for('main.verificar_psicologo', id=id))
        return send_file(psicologo.ruta_archivo_licencia, as_attachment=True)
    
    flash('Tipo de documento no válido.', 'danger')
    return redirect(url_for('main.verificar_psicologo', id=id))





# Ruta para ver notificaciones
@main.route('/notificaciones')
@login_required
def notificaciones():
    # Obtener notificaciones para el usuario actual
    notificaciones = NotificacionSistema.query.filter_by(
        usuario_id=current_user.id
    ).order_by(
        NotificacionSistema.leida,  # No leídas primero
        NotificacionSistema.fecha.desc()  # Más recientes primero
    ).all()
    
    # Agrupar notificaciones por tipo
    notificaciones_agrupadas = {
        'verificacion': [],
        'sistema': [],
        'otras': []
    }
    
    for notif in notificaciones:
        if 'verificacion' in notif.tipo:
            notificaciones_agrupadas['verificacion'].append(notif)
        elif 'sistema' in notif.tipo:
            notificaciones_agrupadas['sistema'].append(notif)
        else:
            notificaciones_agrupadas['otras'].append(notif)
    
    return render_template(
        'notificaciones.html',
        notificaciones=notificaciones,
        notificaciones_agrupadas=notificaciones_agrupadas
    )

# Ruta para marcar notificación como leída
@main.route('/notificacion/<int:id>/leer', methods=['POST'])
@login_required
def marcar_notificacion_leida(id):
    notificacion = NotificacionSistema.query.get_or_404(id)
    
    # Verificar que la notificación pertenece al usuario actual
    if notificacion.usuario_id != current_user.id:
        return jsonify(success=False, message="No tienes permiso para modificar esta notificación"), 403
    
    # Marcar como leída
    notificacion.leida = True
    db.session.commit()
    
    return jsonify(success=True)

# Ruta para marcar todas las notificaciones como leídas
@main.route('/notificaciones/leer-todas', methods=['POST'])
@login_required
def marcar_todas_notificaciones_leidas():
    # Obtener todas las notificaciones no leídas del usuario
    notificaciones = NotificacionSistema.query.filter_by(
        usuario_id=current_user.id,
        leida=False
    ).all()
    
    # Marcar todas como leídas
    for notif in notificaciones:
        notif.leida = True
    
    db.session.commit()
    
    return jsonify(success=True)



def get_notificaciones_no_leidas(usuario_id):
    """Función de ayuda para obtener notificaciones no leídas"""
    if not usuario_id:
        return []
    
    try:
        return NotificacionSistema.query.filter_by(
            usuario_id=usuario_id,
            leida=False
        ).order_by(NotificacionSistema.fecha.desc()).all()
    except Exception as e:
        print(f"Error al obtener notificaciones: {str(e)}")
        return []






# Ruta dashboard del psicólogo
@main.route('/psicologo')
@login_required
def psicologo():

    # Verificar que el usuario sea psicólogo
    if current_user.tipo_usuario != 'psicologo':
        flash('Acceso denegado. No tienes permisos de psicólogo.', 'danger')
        return redirect(url_for('main.index'))

    # Obtener estadísticas básicas
    total_pacientes = Paciente.query.filter_by(psicologo_id=current_user.id).count()
    
    # Obtener citas para hoy
    hoy = datetime.now().date()
    now = datetime.now()  # Para comparar con fecha y hora
    
    citas_hoy = Cita.query.filter_by(psicologo_id=current_user.id).filter(
        db.func.cast(Cita.fecha, db.Date) == hoy
    ).order_by(Cita.fecha).all()
    
    # Obtener todos los pacientes para la pestaña de pacientes
    pacientes = Paciente.query.filter_by(psicologo_id=current_user.id).all()
    
    # Obtener todas las citas para cálculos eficientes
    todas_citas = Cita.query.filter_by(psicologo_id=current_user.id).all()
    
    # Agrupar citas por paciente_id para cálculos más eficientes
    citas_por_paciente = {}
    for cita in todas_citas:
        if cita.paciente_id not in citas_por_paciente:
            citas_por_paciente[cita.paciente_id] = []
        citas_por_paciente[cita.paciente_id].append(cita)
    
    # Calcular última cita y próxima cita para cada paciente
    for paciente in pacientes:
        citas_paciente = citas_por_paciente.get(paciente.id, [])
        
        # Encontrar última cita (más reciente en el pasado)
        ultima_cita = None
        for cita in citas_paciente:
            if cita.fecha < now and (ultima_cita is None or cita.fecha > ultima_cita.fecha):
                ultima_cita = cita
        
        # Encontrar próxima cita (más cercana en el futuro)
        proxima_cita = None
        for cita in citas_paciente:
            if cita.fecha >= now and (proxima_cita is None or cita.fecha < proxima_cita.fecha):
                proxima_cita = cita
        
        # Asignar las citas al paciente
        paciente.ultima_cita = ultima_cita.fecha if ultima_cita else None
        paciente.proxima_cita = proxima_cita.fecha if proxima_cita else None
    
    return render_template('psicologo.html', 
                          total_pacientes=total_pacientes,
                          citas_hoy=citas_hoy,
                          pacientes=pacientes)


# Rutas de pacientes
@main.route('/pacientes')
@login_required
def pacientes():
    # Verificar que el usuario sea psicólogo
    if current_user.tipo_usuario != 'psicologo':
        flash('Acceso denegado. No tienes permisos del psicologo.', 'danger')
        return redirect(url_for('main.index'))

    today = datetime.now()  # Fecha actual completa con hora
    today_date = today.date()  # Solo la fecha para comparaciones
    start_of_month = today_date.replace(day=1)  # Primer día del mes actual como date
    
    # Obtener el psicólogo asociado al usuario actual
    psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()

    if not psicologo:
        flash('Error: No se encontró tu perfil de psicólogo.', 'danger')
        return redirect(url_for('main.index'))

    # Ahora filtramos los pacientes usando el id del psicólogo
    pacientes = Paciente.query.filter_by(psicologo_id=psicologo.id).order_by(Paciente.apellido).all()
    

    # Obtener las citas para todos los pacientes de una sola vez (más eficiente)
    paciente_ids = [p.id for p in pacientes]
    todas_citas = Cita.query.filter(
        Cita.paciente_id.in_(paciente_ids),
        Cita.psicologo_id == current_user.id
    ).all()

    # Organizar citas por paciente_id
    citas_por_paciente = {}
    for cita in todas_citas:
        if cita.paciente_id not in citas_por_paciente:
            citas_por_paciente[cita.paciente_id] = []
        citas_por_paciente[cita.paciente_id].append(cita)

    # Calcular estadísticas
    pacientes_nuevos_mes = 0
    pacientes_activos = 0
    
    # Para cada paciente, encontrar última y próxima cita e información de usuario
    for paciente in pacientes:
        # Obtener email desde el modelo Usuario
        paciente.email = paciente.usuario.email if hasattr(paciente, 'usuario') and paciente.usuario else ""
        
        # Verificar si está activo y gestionar fecha de registro
        if hasattr(paciente, 'usuario') and paciente.usuario:
            paciente.activo = paciente.usuario.activo
            if paciente.activo:
                pacientes_activos += 1
            
            if paciente.usuario.fecha_registro:
                fecha_registro_date = paciente.usuario.fecha_registro.date()
                paciente.fecha_registro = fecha_registro_date
                
                # Contar pacientes nuevos este mes
                if fecha_registro_date >= start_of_month:
                    pacientes_nuevos_mes += 1
        else:
            paciente.activo = False
            paciente.fecha_registro = None
        
        # Procesar citas
        citas_paciente = citas_por_paciente.get(paciente.id, [])
        
        # Encontrar última cita (más reciente en el pasado)
        ultima_cita = None
        for cita in citas_paciente:
            if cita.fecha < today and (ultima_cita is None or cita.fecha > ultima_cita.fecha):
                ultima_cita = cita
        
        # Encontrar próxima cita (más cercana en el futuro)
        proxima_cita = None
        for cita in citas_paciente:
            if cita.fecha >= today and (proxima_cita is None or cita.fecha < proxima_cita.fecha):
                proxima_cita = cita
        
        # Asignar las citas al paciente (mantener fecha y hora completas)
        paciente.ultima_cita = ultima_cita.fecha if ultima_cita else None
        paciente.proxima_cita = proxima_cita.fecha if proxima_cita else None

    # Contar pacientes con status urgente
    pacientes_urgentes = sum(1 for p in pacientes if getattr(p, 'status', None) == 'urgencia')
    

    if pacientes:
        primer_paciente = pacientes[0]
        print(f"Paciente: {primer_paciente.nombre} {primer_paciente.apellido}, Status: {primer_paciente.status}, Diagnóstico: {primer_paciente.diagnostico}")

    # Pasar todas las variables necesarias a la plantilla
    return render_template(
        'pacientes.html', 
        pacientes=pacientes,
        today=today_date, 
        pacientes_urgentes=pacientes_urgentes,
        pacientes_activos=pacientes_activos,
        pacientes_nuevos_mes=pacientes_nuevos_mes,
        start_of_month=start_of_month
    )


# Ruta para nuevos pacientes
@main.route('/nuevo-paciente', methods=['GET', 'POST'])
@login_required
def nuevo_paciente():
    if request.method == 'POST':
        # Obtener datos del formulario
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        fecha_nacimiento = request.form.get('fecha_nacimiento')
        genero = request.form.get('genero')
        direccion = request.form.get('direccion')
        ocupacion = request.form.get('ocupacion')
        estado_civil = request.form.get('estado_civil')
        status = request.form.get('status')
        diagnostico = request.form.get('diagnostico')
        notas = request.form.get('notas')
        
        # Verificar si ya existe un usuario con ese email
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            flash('Ya existe un usuario con ese correo electrónico.', 'danger')
            return redirect(url_for('main.nuevo_paciente'))
        
        # Verificar que el psicólogo existe
        psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
        if not psicologo:
            flash('Error: No se puede asignar el paciente porque tu perfil de psicólogo no está configurado correctamente.', 'danger')
            return redirect(url_for('main.psicologo'))
        
        # Obtener rol de paciente
        rol_paciente = Rol.query.filter_by(nombre='paciente').first()
        if not rol_paciente:
            rol_paciente = Rol(nombre='paciente')
            db.session.add(rol_paciente)
            db.session.flush()

        # Validar la fecha de nacimiento si existe
        if fecha_nacimiento:
            try:
                fecha_nac = datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date()
                if fecha_nac > date.today():
                    flash('Error: La fecha de nacimiento no puede estar en el futuro.', 'danger')
                    return redirect(url_for('main.nuevo_paciente'))
            except ValueError:
                flash('Error: Formato de fecha inválido.', 'danger')
                return redirect(url_for('main.nuevo_paciente'))
        
        # Generar contraseña aleatoria para el usuario
        caracteres = string.ascii_letters + string.digits
        password_temp = ''.join(secrets.choice(caracteres) for i in range(10))
        
        try:
            # Crear usuario para el paciente
            nuevo_usuario = Usuario(
                email=email,
                password=password_temp,
                fecha_registro=datetime.utcnow(),
                activo=True,
                tipo_usuario='paciente',
                rol_id=rol_paciente.id
            )
            db.session.add(nuevo_usuario)
            db.session.flush()
            
            # Crear nuevo paciente
            nuevo_paciente = Paciente(
                usuario_id=nuevo_usuario.id,
                nombre=nombre,
                apellido=apellido,
                telefono=telefono,
                fecha_nacimiento=fecha_nac if fecha_nacimiento else None,
                genero=genero,
                direccion=direccion,
                ocupacion=ocupacion,
                estado_civil=estado_civil,
                status=status,
                diagnostico=diagnostico,
                psicologo_id=psicologo.id,
                creado_en=datetime.utcnow()
            )
            db.session.add(nuevo_paciente)
            db.session.flush()

            print(f"Notas: {notas}, tipo: {type(notas)}")  # Depuración
            # Crear nota si se proporcionó
            if notas and notas.strip():
                nueva_nota = Nota(
                    contenido=notas.strip(),
                    paciente_id=nuevo_paciente.id,
                    psicologo_id=psicologo.id,
                    creado_en=datetime.utcnow(),
                    actualizado_en=datetime.utcnow()
                )
                db.session.add(nueva_nota)
            print("Commit exitoso")  # Depuración
            db.session.commit()
            
            # Enviar email con credenciales
            try:
                email_enviado = enviar_email_credenciales(email, password_temp, nombre)
                if not email_enviado:
                    flash('No se pudo enviar el email de credenciales. Por favor, contacta al administrador.', 'warning')
            except Exception as e:
                print(f"Error al enviar email: {str(e)}")
                flash('Hubo un problema al enviar el email de credenciales.', 'warning')
            
            flash(f'Paciente agregado exitosamente. Contraseña temporal: {password_temp}', 'success')
            return redirect(url_for('main.pacientes'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear paciente.', 'danger')
            return redirect(url_for('main.nuevo_paciente'))
    
    today = date.today().strftime('%Y-%m-%d')
    return render_template('nuevo_paciente.html', today=today)





@main.route('/paciente/<int:paciente_id>')
@login_required
def detalles_pacientes(paciente_id):
    psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
    if not psicologo:
        flash('No se encontró tu perfil.', 'danger')
        return redirect(url_for('main.index'))
    
    paciente = Paciente.query.filter_by(id=paciente_id, psicologo_id=psicologo.id).first()
    if not paciente:
        flash('Paciente no encontrado', 'danger')
        return redirect(url_for('main.pacientes'))
    
    return render_template('detalles_paciente.html', paciente=paciente)





# Ruta para obtener el paciente
from sqlalchemy.orm import joinedload

# Ruta para obtener el paciente
@main.route('/api/paciente/<int:paciente_id>')
@login_required
def detalles_paciente(paciente_id):
    try:
        print(f"DEBUG: Buscando paciente con ID: {paciente_id}")
        print(f"DEBUG: Usuario actual ID: {current_user.id}, Es psicólogo: {current_user.es_psicologo()}")
        
        paciente_existe = Paciente.query.filter_by(id=paciente_id).first()
        if not paciente_existe:
            print(f"DEBUG: El paciente con ID {paciente_id} no existe en la base de datos")
            return jsonify(success=False, message="Paciente no encontrado en la base de datos"), 404
        
        psicologo_actual = Psicologo.query.filter_by(usuario_id=current_user.id).first()
        if not psicologo_actual:
            print("DEBUG: Usuario es psicólogo pero no se encontró registro en la tabla psicologos")
            return jsonify(success=False, message="Psicólogo no encontrado"), 404
        
        paciente = Paciente.query.filter_by(id=paciente_id, psicologo_id=psicologo_actual.id).first()
        if not paciente:
            print(f"DEBUG: El paciente existe pero no pertenece al psicólogo actual ({psicologo_actual.id})")
            return jsonify(success=False, message="Paciente no encontrado para este psicólogo"), 404
        
        citas = Cita.query.filter_by(paciente_id=paciente_id).all()
        notas_paciente = Nota.query.filter_by(paciente_id=paciente_id, psicologo_id=psicologo_actual.id).order_by(Nota.creado_en.desc()).all()
        
        citas_data = []
        for cita in citas:
            notas_cita = Nota.query.filter_by(cita_id=cita.id, psicologo_id=psicologo_actual.id).order_by(Nota.creado_en.desc()).all()
            citas_data.append({
                'id': cita.id,
                'fecha': cita.fecha.isoformat() if cita.fecha else None,
                'duracion': cita.obtener_duracion(),
                'tipo': cita.tipo_cita.nombre if cita.tipo_cita else None,
                'status': cita.status if hasattr(cita, 'status') else None,
                'notas': [nota.to_dict() for nota in notas_cita]
            })

        email = paciente.usuario.email if hasattr(paciente, 'usuario') and paciente.usuario else ""

        return jsonify(
            success=True,
            paciente={
                'id': paciente.id,
                'nombre': paciente.nombre if hasattr(paciente, 'nombre') else "",
                'apellido': paciente.apellido if hasattr(paciente, 'apellido') else "",
                'email': email,
                'telefono': paciente.telefono if hasattr(paciente, 'telefono') else "",
                'diagnostico': paciente.diagnostico if hasattr(paciente, 'diagnostico') else "",
                'fecha_nacimiento': paciente.fecha_nacimiento.strftime('%Y-%m-%d') if hasattr(paciente, 'fecha_nacimiento') and paciente.fecha_nacimiento else None,
                'genero': paciente.genero if hasattr(paciente, 'genero') else "",
                'direccion': paciente.direccion if hasattr(paciente, 'direccion') else "",
                'ocupacion': paciente.ocupacion if hasattr(paciente, 'ocupacion') else "",
                'citas': citas_data,
                'notas': [nota.to_dict() for nota in notas_paciente]
            }
        )
    except Exception as e:
        import traceback
        print(f"ERROR: Error al obtener paciente {paciente_id}: {str(e)}")
        print(traceback.format_exc())
        return jsonify(success=False, message=f"Error interno del servidor: {str(e)}"), 500



    
# Rutas API para pacientes
@main.route('/api/pacientes', methods=['GET'])
@login_required
def api_pacientes():
    try:
        # Debugging: Print user information
        print(f"API Request - User ID: {current_user.id}, Username: {current_user.username if hasattr(current_user, 'username') else 'unknown'}")
        
        # Verificar que los modelos necesarios estén disponibles
        print("Verificando modelos disponibles...")
        
        # Obtener el psicólogo asociado al usuario actual
        print(f"Buscando psicólogo para usuario_id: {current_user.id}")
        psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
        
        if not psicologo:
            print(f"Error: No se encontró perfil de psicólogo para el usuario {current_user.id}")
            return jsonify([])  # Retornar lista vacía si no hay psicólogo
        
        print(f"Psicólogo encontrado - ID: {psicologo.id}")
        
        # Verificar total de pacientes para este psicólogo antes de aplicar filtros
        print(f"Buscando pacientes para psicologo_id: {psicologo.id}")
        try:
            total_pacientes = Paciente.query.filter_by(psicologo_id=psicologo.id).count()
            print(f"Total de pacientes para psicólogo {psicologo.id}: {total_pacientes}")
        except Exception as e:
            print(f"Error al contar pacientes: {str(e)}")
            return jsonify({"error": "Error al contar pacientes", "details": str(e)}), 500
        
        # Obtener los filtros del query string
        status_filter = request.args.get('status')
        diagnosis_filter = request.args.get('diagnosis')
        last_visit_filter = request.args.get('last_visit')
        search_term = request.args.get('search')
        
        # Imprimir filtros aplicados para debug
        print(f"Filtros: status={status_filter}, diagnosis={diagnosis_filter}, last_visit={last_visit_filter}, search={search_term}")
        
        # Usar el ID del psicólogo, no el ID del usuario
        try:
            query = Paciente.query.filter_by(psicologo_id=psicologo.id)
            
            # Aplicar filtros
            if status_filter:
                query = query.filter_by(status=status_filter)

            if diagnosis_filter:
                query = query.filter_by(diagnostico=diagnosis_filter)
            
            if last_visit_filter:
                # NOTA: Este filtro puede causar problemas porque 'ultima_cita' no es una columna en la BD
                # sino un atributo calculado. Comentar temporalmente para diagnóstico.
                print("Advertencia: El filtro de última visita puede no funcionar si 'ultima_cita' no es una columna real")
                """
                today = datetime.now()
                if last_visit_filter == 'week':
                    last_week = today - timedelta(days=7)
                    query = query.filter(Paciente.ultima_cita >= last_week)
                elif last_visit_filter == 'month':
                    last_month = today - timedelta(days=30)
                    query = query.filter(Paciente.ultima_cita >= last_month)
                elif last_visit_filter == 'quarter':
                    last_quarter = today - timedelta(days=90)
                    query = query.filter(Paciente.ultima_cita >= last_quarter)
                elif last_visit_filter == 'year':
                    last_year = today - timedelta(days=365)
                    query = query.filter(Paciente.ultima_cita >= last_year)
                """
            
            if search_term:
                search_term = f"%{search_term}%"
                query = query.filter(
                    or_(
                        Paciente.nombre.ilike(search_term),
                        Paciente.apellido.ilike(search_term),
                        # Ya no podemos filtrar directamente por email
                        Paciente.diagnostico.ilike(search_term)
                    )
                )

            pacientes = query.all()
            print(f"Pacientes después de aplicar filtros: {len(pacientes)}")
        except Exception as e:
            print(f"Error al ejecutar consulta de pacientes: {str(e)}")
            return jsonify({"error": "Error al ejecutar consulta de pacientes", "details": str(e)}), 500
        
        # Para cada paciente, calcular última y próxima cita
        today = datetime.now()
        resultado_pacientes = []
        
        for paciente in pacientes:
            try:
                # Verificar atributos del paciente
                print(f"Procesando paciente ID: {paciente.id}, Nombre: {paciente.nombre} {paciente.apellido}")
                
                # Buscar la última cita (más reciente en el pasado)
                ultima_cita = Cita.query.filter_by(
                    paciente_id=paciente.id,
                    psicologo_id=psicologo.id  # Usar psicologo.id, no current_user.id
                ).filter(
                    Cita.fecha < today
                ).order_by(
                    Cita.fecha.desc()
                ).first()
                
                # Buscar la próxima cita (más cercana en el futuro)
                proxima_cita = Cita.query.filter_by(
                    paciente_id=paciente.id,
                    psicologo_id=psicologo.id  # Usar psicologo.id, no current_user.id
                ).filter(
                    Cita.fecha >= today
                ).order_by(
                    Cita.fecha.asc()
                ).first()
                
                # Crear objeto de paciente para respuesta JSON
                paciente_dict = {
                    'id': paciente.id,
                    'nombre': paciente.nombre,
                    'apellido': paciente.apellido,
                    'telefono': paciente.telefono or "",
                    'diagnostico': paciente.diagnostico or "",
                    'status': paciente.status or "vigente",  # Valor por defecto
                    'ultima_cita': ultima_cita.fecha.isoformat() if ultima_cita else None,
                    'proxima_cita': proxima_cita.fecha.isoformat() if proxima_cita else None
                }
                
                # Obtener email con manejo de errores
                try:
                    paciente_dict['email'] = paciente.usuario.email if hasattr(paciente, 'usuario') and paciente.usuario else ""
                except Exception as e:
                    print(f"Error al obtener email para paciente {paciente.id}: {str(e)}")
                    paciente_dict['email'] = ""
                
                resultado_pacientes.append(paciente_dict)
            except Exception as e:
                print(f"Error al procesar paciente {paciente.id}: {str(e)}")
                # Continuar con el siguiente paciente
        
        print(f"Enviando {len(resultado_pacientes)} pacientes en respuesta")
        return jsonify(resultado_pacientes)
    
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error en api_pacientes: {str(e)}")
        print(f"Traceback: {error_traceback}")
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500
    


# Ruta para editar paciente (API)
@main.route('/api/paciente/<int:paciente_id>/editar', methods=['POST'])
@login_required
def editar_paciente_api(paciente_id):
    psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
    if not psicologo:
        return jsonify(success=False, message="Psicólogo no encontrado"), 404

    paciente = Paciente.query.filter_by(id=paciente_id, psicologo_id=psicologo.id).first_or_404()
    data = request.get_json()

    if not data:
        return jsonify(success=False, message="No se enviaron datos"), 400
    
    print("Datos recibidos en la API:", data)

    try:
        # Actualizar campos del paciente
        paciente.nombre = data.get('nombre', paciente.nombre)
        paciente.apellido = data.get('apellido', paciente.apellido)
        paciente.status = data.get('status', paciente.status)
        paciente.diagnostico = data.get('diagnostico', paciente.diagnostico)
        paciente.telefono = data.get('telefono', paciente.telefono)

        # Actualizar email en Usuario
        if hasattr(paciente, 'usuario') and paciente.usuario:
            paciente.usuario.email = data.get('email', paciente.usuario.email)

        # Manejar notas (crear una nueva si se proporciona)
        notas = data.get('notas')
        if notas and notas.strip():
            nueva_nota = Nota(
                contenido=notas.strip(),
                paciente_id=paciente.id,
                psicologo_id=psicologo.id,
                creado_en=datetime.utcnow(),
                actualizado_en=datetime.utcnow()
            )
            db.session.add(nueva_nota)

        # Limpiar campos
        paciente.nombre = paciente.nombre.strip() if paciente.nombre else None
        paciente.apellido = paciente.apellido.strip() if paciente.apellido else None
        paciente.status = paciente.status.strip() if paciente.status else None
        paciente.diagnostico = paciente.diagnostico.strip() if paciente.diagnostico else None
        paciente.telefono = paciente.telefono.strip() if paciente.telefono else None
        if hasattr(paciente, 'usuario') and paciente.usuario:
            paciente.usuario.email = paciente.usuario.email.strip() if paciente.usuario.email else None

        db.session.commit()
        return jsonify(success=True, message="Paciente actualizado correctamente.")
    
    except Exception as e:
        db.session.rollback()
        print(f"Error al actualizar paciente: {str(e)}")
        return jsonify(success=False, message=f"Error al actualizar paciente: {str(e)}"), 400




import logging
import traceback  # Added import
from flask import jsonify, request
from flask_login import login_required, current_user
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')

@main.route('/api/paciente/<int:paciente_id>/notas', methods=['GET', 'POST'])
@login_required
def paciente_notas(paciente_id):
    logging.debug(f"Request to /api/paciente/{paciente_id}/notas, method={request.method}, user_id={current_user.id}")
    try:
        # Verify the current user is a psychologist
        psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
        if not psicologo:
            logging.error("Psicólogo no encontrado para usuario_id=%s", current_user.id)
            return jsonify(success=False, message="Psicólogo no encontrado"), 404

        logging.debug("Psicólogo encontrado: id=%s", psicologo.id)

        # Verify the patient exists and belongs to the psychologist
        paciente = Paciente.query.filter_by(id=paciente_id, psicologo_id=psicologo.id).first()
        if not paciente:
            logging.error("Paciente no encontrado: paciente_id=%s, psicologo_id=%s", paciente_id, psicologo.id)
            return jsonify(success=False, message="Paciente no encontrado para este psicólogo"), 404

        logging.debug("Paciente encontrado: id=%s, nombre=%s %s", paciente.id, paciente.nombre, paciente.apellido)

        if request.method == 'GET':
            notas = Nota.query.filter_by(paciente_id=paciente_id, psicologo_id=psicologo.id).order_by(Nota.creado_en.desc()).all()
            logging.debug("Notas recuperadas: %s", len(notas))
            return jsonify({
                'success': True,
                'patient_name': f"{paciente.nombre} {paciente.apellido}",
                'notas': [nota.to_dict() for nota in notas]
            })

        elif request.method == 'POST':
            data = request.get_json()
            logging.debug("Datos recibidos: %s", data)
            if not data or 'contenido' not in data:
                logging.error("Falta contenido en la solicitud")
                return jsonify(success=False, message="No se proporcionó contenido para la nota"), 400
            
            contenido = data['contenido'].strip()
            if not contenido:
                logging.error("Contenido vacío después de strip")
                return jsonify(success=False, message="La nota no puede estar vacía"), 400

            logging.debug("Creando nueva nota para paciente_id=%s, psicologo_id=%s", paciente_id, psicologo.id)
            nueva_nota = Nota(
                contenido=contenido,
                paciente_id=paciente_id,
                psicologo_id=psicologo.id,
                creado_en=datetime.utcnow(),
                actualizado_en=datetime.utcnow(),
                cita_id=None
            )
            db.session.add(nueva_nota)
            logging.debug("Nota agregada a la sesión, intentando commit")
            db.session.commit()
            logging.info("Nota creada exitosamente: id=%s", nueva_nota.id)

            return jsonify({
                'success': True,
                'message': "Nota agregada correctamente",
                'nota': nueva_nota.to_dict()
            })

    except Exception as e:
        logging.error("Error en paciente_notas: %s", str(e))
        logging.error("Traceback: %s", traceback.format_exc())
        db.session.rollback()
        return jsonify(success=False, message=f"Error interno del servidor: {str(e)}"), 500






@main.route('/api/paciente/<int:paciente_id>/eliminar', methods=['POST'])
@login_required
def eliminar_paciente(paciente_id):
    try:
        # Buscar el psicólogo actual
        psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
        
        if not psicologo:
            return jsonify(success=False, message="Psicólogo no encontrado"), 404
        
        # Buscar el paciente específicamente para este psicólogo
        paciente = Paciente.query.filter_by(id=paciente_id, psicologo_id=psicologo.id).first()
        
        if not paciente:
            return jsonify(success=False, message="Paciente no encontrado"), 404

        # Eliminar notificaciones asociadas a citas del paciente (por si quedaron notificaciones huérfanas)
        db.session.execute(
            db.text("DELETE FROM notificaciones WHERE cita_id IN (SELECT id FROM citas WHERE paciente_id = :paciente_id)"),
            {"paciente_id": paciente_id}
        )
        
        # Eliminar notas asociadas a citas del paciente (por consistencia)
        db.session.execute(
            db.text("DELETE FROM notas WHERE cita_id IN (SELECT id FROM citas WHERE paciente_id = :paciente_id)"),
            {"paciente_id": paciente_id}
        )
        
        # Eliminar todas las citas asociadas al paciente
        Cita.query.filter_by(paciente_id=paciente_id).delete()
        
        # Eliminar las notas asociadas al paciente
        Nota.query.filter_by(paciente_id=paciente_id).delete()
        
        # Guardar referencia al usuario asociado
        usuario_id = paciente.usuario_id
        
        # Eliminar notificaciones relacionadas con el paciente
        NotificacionSistema.query.filter_by(referencia_id=paciente_id).delete()
        
        # Eliminar el paciente
        db.session.delete(paciente)
        
        # Eliminar el usuario correspondiente
        if usuario_id:
            usuario = Usuario.query.get(usuario_id)
            if usuario:
                # Eliminar notificaciones del usuario
                NotificacionSistema.query.filter_by(usuario_id=usuario_id).delete()
                db.session.delete(usuario)
        
        db.session.commit()
        return jsonify(success=True, message="Paciente eliminado correctamente")
    
    except Exception as e:
        # En caso de error, hacer rollback
        db.session.rollback()
        
        # Registrar el error
        print(f"Error al eliminar paciente: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Devolver mensaje de error
        return jsonify(success=False, message=f"Error al eliminar el paciente: {str(e)}"), 500





@main.route('/nueva-cita', methods=['GET', 'POST'])
@login_required
def nueva_cita():
    psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
    
    if not psicologo:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'No se encontró tu perfil de psicólogo.'}), 404
        flash('No se encontró tu perfil de psicólogo.', 'danger')
        return redirect(url_for('main.index'))
    
    pacientes = Paciente.query.join(Usuario, Paciente.usuario_id == Usuario.id) \
        .filter(Paciente.psicologo_id == psicologo.id, Usuario.activo == True) \
        .order_by(Paciente.apellido, Paciente.nombre) \
        .all()
    
    tipos_cita = []
    if current_user.es_psicologo():
        if not psicologo.tipos_cita_disponibles:
            tipos_activos = TipoCita.query.filter_by(activo=True).all()
            psicologo.tipos_cita_disponibles = tipos_activos
            try:
                db.session.add(psicologo)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error al asignar tipos de cita: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': f"Error al asignar tipos de cita: {str(e)}"}), 500
                flash(f"Error al asignar tipos de cita.", 'danger')
        
        tipos_cita = psicologo.tipos_cita_disponibles
    
    if not tipos_cita:
        tipos_cita = TipoCita.query.filter_by(activo=True).all()
    
    horas_ocupadas = Cita.query.filter_by(psicologo_id=psicologo.id, status='Programada').all()
    horas_ocupadas = [cita.fecha.strftime('%Y-%m-%d %H:%M') for cita in horas_ocupadas]

    if request.method == 'POST':
        paciente_id = request.form.get('paciente_id')
        fecha = request.form.get('fecha')
        hora = request.form.get('hora')
        tipo_cita_id = request.form.get('tipo_cita_id')
        motivo = request.form.get('motivo')
        notas = request.form.get('notas')  # Obtener notas del formulario
        sync_google = request.form.get('sync_google') == 'on'

        current_app.logger.info(f"Form data: paciente_id={paciente_id}, fecha={fecha}, hora={hora}, tipo_cita_id={tipo_cita_id}, motivo={motivo}, notas={notas}, sync_google={sync_google}")

        if not all([paciente_id, fecha, hora, tipo_cita_id]):
            current_app.logger.error("Missing required fields")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Todos los campos obligatorios deben estar completos.'}), 400
            flash('Todos los campos obligatorios deben estar completos.', 'danger')
            return redirect(url_for('main.nueva_cita'))

        try:
            # Validar formato de fecha y hora
            fecha_hora = datetime.strptime(f"{fecha} {hora}", '%Y-%m-%d %H:%M')
            ahora = datetime.now()
            if fecha_hora < ahora:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'No puedes programar una cita en una fecha pasada.'}), 400
                flash('No puedes programar una cita en una fecha pasada.', 'danger')
                return redirect(url_for('main.nueva_cita'))

            # Crear cita temporal para obtener duración
            temp_cita = Cita(
                fecha=fecha_hora,
                tipo_cita_id=int(tipo_cita_id) if tipo_cita_id else None,
                motivo=motivo,
                psicologo_id=psicologo.id,
                paciente_id=int(paciente_id),
                status='Programada'
            )
            duracion = temp_cita.obtener_duracion()
            fecha_fin = fecha_hora + timedelta(minutes=duracion)

            # Verificar solapamiento en la base de datos
            citas_existentes = Cita.query.filter_by(psicologo_id=psicologo.id, status='Programada') \
                .filter(func.cast(Cita.fecha, db.Date) == fecha_hora.date()) \
                .all()

            for cita in citas_existentes:
                cita_fin = cita.fecha + timedelta(minutes=cita.obtener_duracion())
                if not (fecha_fin <= cita.fecha or fecha_hora >= cita_fin):
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'message': f'Hora ocupada: {cita.fecha.strftime("%H:%M")} ya está reservada.'}), 400
                    flash(f'Hora ocupada: {cita.fecha.strftime("%H:%M")} ya está reservada.', 'danger')
                    return redirect(url_for('main.nueva_cita'))

            # Crear la cita (sin pasar notas)
            nueva_cita = Cita(
                fecha=fecha_hora,
                tipo_cita_id=int(tipo_cita_id) if tipo_cita_id else None,
                motivo=motivo,
                psicologo_id=psicologo.id,
                paciente_id=int(paciente_id),
                status='Programada'
            )

            db.session.add(nueva_cita)
            db.session.flush()  # Obtener el ID de la cita antes de crear la nota

            # Crear una nota si el campo notas no está vacío
            if notas and notas.strip():
                nueva_nota = Nota(
                    contenido=notas.strip(),
                    cita_id=nueva_cita.id,
                    psicologo_id=psicologo.id,
                    paciente_id=int(paciente_id)
                )
                db.session.add(nueva_nota)

            db.session.commit()
            current_app.logger.info(f"Cita creada: id={nueva_cita.id}, fecha={nueva_cita.fecha}, psicologo_id={nueva_cita.psicologo_id}, status={nueva_cita.status}")

            # Programar notificaciones
            Notificacion.programar_recordatorios_cita(db.session, nueva_cita)
            
            tipo_cita = TipoCita.query.get(tipo_cita_id)
            paciente = Paciente.query.get(paciente_id)
            
            NotificacionSistema.crear_notificacion_verificacion(
                db.session,
                usuario_id=current_user.id,
                tipo='nueva_cita',
                referencia_id=nueva_cita.id,
                titulo='Nueva cita programada',
                mensaje=f'Has programado una cita de {tipo_cita.nombre if tipo_cita else "consulta"} con {paciente.nombre} {paciente.apellido} para el {fecha_hora.strftime("%d/%m/%Y a las %H:%M")}'
            )
            
            if paciente.usuario_id:
                NotificacionSistema.crear_notificacion_verificacion(
                    db.session,
                    usuario_id=paciente.usuario_id,
                    tipo='nueva_cita',
                    referencia_id=nueva_cita.id,
                    titulo='Nueva cita programada',
                    mensaje=f'Tu psicólogo ha programado una cita de {tipo_cita.nombre if tipo_cita else "consulta"} para el {fecha_hora.strftime("%d/%m/%Y a las %H:%M")}'
                )
            
            db.session.commit()
            current_app.logger.info(f"Notificaciones creadas para cita id={nueva_cita.id}")

            # Sincronizar con Google Calendar si está marcado
            if sync_google:
                try:
                    token_path = f'token_{current_user.id}.pickle'
                    creds = None
                    if os.path.exists(token_path):
                        with open(token_path, 'rb') as token:
                            creds = pickle.load(token)

                    if not creds or not creds.valid:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return jsonify({
                                'success': True,
                                'message': 'Cita guardada. Autenticación con Google requerida.',
                                'redirect': url_for('main.google_auth', _external=True)
                            })
                        flash('Cita guardada. Por favor, autentícate con Google para sincronizar.', 'info')
                        return redirect(url_for('main.google_auth'))

                    service = build('calendar', 'v3', credentials=creds)

                    # Verificar solapamiento en Google Calendar
                    events_result = service.events().list(
                        calendarId='primary',
                        timeMin=fecha_hora.isoformat(),
                        timeMax=fecha_fin.isoformat(),
                        singleEvents=True
                    ).execute()
                    events = events_result.get('items', [])

                    if events:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return jsonify({
                                'success': False,
                                'message': 'El horario seleccionado está ocupado en Google Calendar'
                            }), 409
                        flash('El horario seleccionado está ocupado en Google Calendar', 'danger')
                        return redirect(url_for('main.nueva_cita'))

                    # Crear evento en Google Calendar
                    event = {
                        'summary': tipo_cita.nombre if tipo_cita else 'Cita',
                        'description': notas or motivo or '',  # Usar notas aquí para el evento
                        'start': {
                            'dateTime': fecha_hora.isoformat(),
                            'timeZone': 'UTC',
                        },
                        'end': {
                            'dateTime': fecha_fin.isoformat(),
                            'timeZone': 'UTC',
                        },
                        'reminders': {
                            'useDefault': False,
                            'overrides': [
                                {'method': 'email', 'minutes': 30},
                                {'method': 'popup', 'minutes': 10}
                            ]
                        }
                    }

                    calendar_id = 'primary'
                    event = service.events().insert(calendarId=calendar_id, body=event).execute()

                    # Guardar event_id en la cita
                    nueva_cita.google_event_id = event.get('id')
                    db.session.commit()

                    mensaje_exito = 'Cita programada y sincronizada con Google Calendar exitosamente.'
                except Exception as e:
                    current_app.logger.error(f"Error al sincronizar con Google: {str(e)}")
                    mensaje_exito = 'Cita programada, pero no se pudo sincronizar con Google Calendar.'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({
                            'success': True,
                            'message': mensaje_exito,
                            'redirect': url_for('main.historial')
                        })
                    flash(mensaje_exito, 'warning')
                    return redirect(url_for('main.historial'))
            else:
                mensaje_exito = 'Cita programada exitosamente.'

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'message': mensaje_exito,
                    'redirect': url_for('main.historial')
                })
            flash(mensaje_exito, 'success')
            return redirect(url_for('main.historial'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al crear cita: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': str(e)}), 400
            flash(f'Error al crear la cita.', 'danger')
            import traceback
            traceback.print_exc()
            return redirect(url_for('main.nueva_cita'))

    return render_template('pagina_nueva_cita.html', 
                          pacientes=pacientes, 
                          tipos_cita=tipos_cita, 
                          horas_ocupadas=horas_ocupadas)




@main.route('/asignar-tipos-cita', methods=['GET'])
@login_required
def asignar_tipos_cita():
    if not current_user.es_psicologo():
        flash('Acceso denegado. No tienes permisos de psicólogo.', 'danger')
        return redirect(url_for('main.index'))
    
    psicologo = Psicologo.query.get(current_user.id)
    
    # Si el psicólogo no tiene tipos de cita asignados, asignar todos los activos
    if not psicologo.tipos_cita_disponibles:
        tipos_activos = TipoCita.query.filter_by(activo=True).all()
        psicologo.tipos_cita_disponibles = tipos_activos
        db.session.commit()
        flash('Se han asignado los tipos de cita disponibles a tu perfil.', 'success')
    
    return redirect(url_for('main.psicologo'))



@main.route('/admin/inicializar-tipos-cita')
@login_required
def inicializar_tipos_cita():
    # Verificar si hay registros
    total_antes = TipoCita.query.count()
    
    # Eliminar todos los registros existentes (opcional)
    TipoCita.query.delete()
    
    # Solo poblar si no hay registros o si se fuerza
    if total_antes == 0 or request.args.get('force') == '1':
        TipoCita.seed_default_types(db.session)
        
    # Verificar después
    total_despues = TipoCita.query.count()
    
    # Obtener todos los tipos
    tipos = TipoCita.query.all()
    
    return jsonify({
        'success': True,
        'mensaje': f'Tipos de cita inicializados. Antes: {total_antes}, Después: {total_despues}',
        'tipos': [{'id': t.id, 'nombre': t.nombre, 'color': t.color} for t in tipos]
    })



@main.route('/admin/asignar-tipos-cita-todos')
@login_required
def asignar_tipos_cita_todos():
    tipos_activos = TipoCita.query.filter_by(activo=True).all()
    if not tipos_activos:
        return jsonify({
            'success': False,
            'mensaje': 'No hay tipos de cita activos para asignar.'
        })
    
    psicologos = Psicologo.query.all()
    contador = 0
    
    for psicologo in psicologos:
        if not psicologo.tipos_cita_disponibles:
            psicologo.tipos_cita_disponibles = tipos_activos
            contador += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'mensaje': f'Se asignaron tipos de cita a {contador} psicólogos.'
    })



@main.route('/debug/tipos-cita')
@login_required
def debug_tipos_cita():
    # Obtener el psicólogo actual
    psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
    
    if not psicologo:
        return jsonify({
            'error': 'No se encontró el psicólogo',
            'success': False
        })
    
    # Obtener todos los tipos de cita activos
    tipos_activos = TipoCita.query.filter_by(activo=True).all()
    
    return jsonify({
        'success': True,
        'psicologo': {
            'id': psicologo.id,
            'nombre': psicologo.nombre,
            'tipos_cita_asignados': len(psicologo.tipos_cita_disponibles),
            'tipos_cita': [{
                'id': tipo.id,
                'nombre': tipo.nombre,
                'activo': tipo.activo
            } for tipo in psicologo.tipos_cita_disponibles]
        },
        'tipos_activos_totales': len(tipos_activos)
    })


from sqlalchemy import func  # Import func for SQL Server compatibility

# api horas ocupadas
@main.route('/api/horas_ocupadas', methods=['GET'])
@login_required
def horas_ocupadas():
    try:
        psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
        if not psicologo:
            return jsonify({'success': False, 'message': 'No se encontró tu perfil de psicólogo.'}), 404

        fecha = request.args.get('fecha')
        horas_ocupadas = []

        if fecha:
            try:
                fecha_dt = datetime.strptime(fecha, '%Y-%m-%d').date()
                citas = Cita.query.filter_by(psicologo_id=psicologo.id, status='Programada') \
                    .filter(func.cast(Cita.fecha, db.Date) == fecha_dt) \
                    .all()
                horas_ocupadas = [cita.fecha.strftime('%H:%M') for cita in citas]
            except ValueError:
                return jsonify({'success': False, 'message': 'Formato de fecha inválido'}), 400
        else:
            citas = Cita.query.filter_by(psicologo_id=psicologo.id, status='Programada').all()
            horas_ocupadas = [cita.fecha.strftime('%H:%M') for cita in citas]

        return jsonify({'success': True, 'horas_ocupadas': horas_ocupadas})
    except Exception as e:
        current_app.logger.error(f"Error en /api/horas_ocupadas: {str(e)}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500


@main.route('/historial')
@login_required
def historial():
    # Buscar el psicólogo asociado al usuario actual
    psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
    
    if not psicologo:
        flash('No se encontró tu perfil de psicólogo.', 'danger')
        return redirect(url_for('main.index'))

    # Get current date and time for comparison
    today = datetime.now()
    
    # Get all appointments for this psychologist
    all_citas = Cita.query.filter_by(psicologo_id=psicologo.id)\
        .join(Paciente, Cita.paciente_id == Paciente.id)\
        .join(TipoCita, Cita.tipo_cita_id == TipoCita.id, isouter=True)\
        .order_by(Cita.fecha.desc())\
        .all()
    
    # Estadísticas para el resumen
    total_citas = len(all_citas)

    citas_completadas = Cita.query.filter_by(psicologo_id=psicologo.id, status='Completada').count()
    pacientes_atendidos = db.session.query(Cita.paciente_id).filter_by(psicologo_id=psicologo.id).distinct().count()
    
    # Calculate attendance rate the same way as in statistics page
    # Only consider past appointments with status 'Completada' or 'Cancelada'
    past_citas = [c for c in all_citas if c.fecha < today]
    total_pasadas = sum(1 for c in past_citas if c.status in ['Completada', 'Cancelada'])
    asistidas = sum(1 for c in past_citas if c.status == 'Completada')
    tasa_asistencia = round((asistidas / total_pasadas * 100) if total_pasadas > 0 else 0, 2)
    
    # Obtener pacientes del psicólogo
    pacientes = {p.id: p for p in Paciente.query.filter_by(psicologo_id=psicologo.id).all()}
    
    return render_template('historial.html', 
                          citas=all_citas, 
                          pacientes=pacientes,
                          total_citas=total_citas,
                          citas_completadas=citas_completadas,
                          pacientes_atendidos=pacientes_atendidos,
                          tasa_asistencia=tasa_asistencia)


# API para obtener los tipos de cita disponibles
@main.route('/api/tipos-cita')
@login_required
def api_tipos_cita():
    try:
        # Si el usuario es psicólogo, obtener sus tipos de cita disponibles
        if current_user.es_psicologo():
            psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
            if psicologo:
                # Verificar y asignar tipos de cita si están vacíos
                if not psicologo.tipos_cita_disponibles:
                    tipos_activos = TipoCita.query.filter_by(activo=True).all()
                    psicologo.tipos_cita_disponibles = tipos_activos
                    try:
                        db.session.add(psicologo)
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                
                tipos_cita = psicologo.tipos_cita_disponibles
            else:
                tipos_cita = TipoCita.query.filter_by(activo=True).all()
        else:
            tipos_cita = TipoCita.query.filter_by(activo=True).all()
        
        # Convertir a formato JSON
        result = [{
            'id': tipo.id,
            'nombre': tipo.nombre,
            'duracion': tipo.duracion_predeterminada,
            'color': tipo.color
        } for tipo in tipos_cita]
        
        return jsonify(result)
    
    except Exception as e:
        current_app.logger.error(f"Error en api_tipos_cita: {str(e)}")
        return jsonify([])





# Rutas API para citas
@main.route('/api/citas')
@login_required
def api_citas():
    try:
        psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
        if not psicologo:
            return jsonify([])
        
        citas = Cita.query.filter_by(psicologo_id=psicologo.id)\
            .join(Paciente, Cita.paciente_id == Paciente.id)\
            .join(TipoCita, Cita.tipo_cita_id == TipoCita.id, isouter=True)\
            .order_by(Cita.fecha.desc())\
            .all()
        
        citas_json = []
        for cita in citas:
            paciente = Paciente.query.get(cita.paciente_id)
            notas_texto = cita.notas if cita.notas else ''
            
            cita_dict = {
                'id': cita.id,
                'paciente_id': cita.paciente_id,
                'paciente_nombre': f"{paciente.nombre} {paciente.apellido}" if paciente else "Sin asignar",
                'fecha': cita.fecha.isoformat(),
                'duracion': cita.obtener_duracion(),
                'tipo': cita.tipo_cita.nombre if cita.tipo_cita else "No especificado",
                'tipo_cita_id': cita.tipo_cita_id,
                'status': cita.status,
                'notas': notas_texto
            }
            citas_json.append(cita_dict)
        
        return jsonify(citas_json)
    
    except Exception as e:
        current_app.logger.error(f"Error en api_citas: {str(e)}")
        return jsonify([]), 500




@main.route('/api/cita/<int:cita_id>')
@login_required
def obtener_cita(cita_id):
    try:
        current_app.logger.info(f"Procesando solicitud para cita ID {cita_id}")
        psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
        if not psicologo:
            current_app.logger.warning(f"No se encontró psicólogo para usuario ID {current_user.id}")
            return jsonify({'success': False, 'message': 'Psicólogo no encontrado'}), 404
        
        cita = Cita.query.filter_by(id=cita_id, psicologo_id=psicologo.id).first()
        if not cita:
            current_app.logger.warning(f"No se encontró cita con ID {cita_id} para psicólogo ID {psicologo.id}")
            return jsonify({'success': False, 'message': 'Cita no encontrada'}), 404
        
        paciente = Paciente.query.get(cita.paciente_id)
        paciente_nombre = f"{paciente.nombre} {paciente.apellido}" if paciente else "Paciente no especificado"
        notas_texto = cita.notas if cita.notas else ''
        tipo_cita_nombre = cita.tipo_cita.nombre if cita.tipo_cita else "No especificado"
        
        # Validar fecha
        fecha_str = cita.fecha.isoformat() if isinstance(cita.fecha, datetime) else 'No especificada'
        
        response_data = {
            'success': True,
            'cita': {
                'id': cita.id,
                'paciente': paciente_nombre,
                'paciente_id': cita.paciente_id,
                'fecha': fecha_str,
                'duracion': cita.obtener_duracion(),
                'tipo': tipo_cita_nombre,
                'tipo_cita_id': cita.tipo_cita_id,
                'status': cita.status,
                'notas': notas_texto
            }
        }
        
        current_app.logger.info(f"Detalles de cita ID {cita_id} recuperados exitosamente")
        return jsonify(response_data)
    
    except Exception as e:
        current_app.logger.error(f"Error inesperado al obtener cita ID {cita_id}: {str(e)}")
        return jsonify({'success': False, 'message': f'Error interno del servidor: {str(e)}'}), 500
    





@main.route('/api/cita/<int:cita_id>/status', methods=['POST'])
@login_required
def actualizar_status_cita(cita_id):
    cita = Cita.query.filter_by(id=cita_id, psicologo_id=current_user.id).first_or_404()
    data = request.get_json()
    
    if 'status' in data:
        cita.status = data['status']
        db.session.commit()
        return jsonify(success=True, message=f"Cita actualizada a '{data['status']}'")
    
    return jsonify(success=False, message="No se proporcionó el status"), 400





# Ruta para editar citas
# Ruta para editar citas - CORREGIDA
@main.route('/cita/<int:cita_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_cita(cita_id):
    psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
    if not psicologo:
        flash('No se encontró tu perfil de psicólogo.', 'danger')
        return redirect(url_for('main.index'))
    
    cita = Cita.query.filter_by(id=cita_id, psicologo_id=psicologo.id).first_or_404()
    pacientes = Paciente.query.join(Usuario, Paciente.usuario_id == Usuario.id)\
                      .filter(Paciente.psicologo_id == psicologo.id, Usuario.activo == True)\
                      .all()
    tipos_cita = psicologo.get_tipos_cita()
    es_cita_pasada = cita.fecha < datetime.now()
    
    # CORREGIDO: Usar 'notas' en lugar de 'nota'
    nota_texto = cita.notas if cita.notas else ''
    
    if request.method == 'POST':
        try:
            fecha = request.form.get('fecha')
            hora = request.form.get('hora')
            nueva_fecha = datetime.strptime(f"{fecha} {hora}", '%Y-%m-%d %H:%M')
            
            if not es_cita_pasada and nueva_fecha < datetime.now():
                flash('No se puede programar una cita en el pasado.', 'danger')
                return render_template('editar_cita.html', cita=cita, pacientes=pacientes, tipos_cita=tipos_cita, error_fecha=True, nota=nota_texto)
            
            cita.fecha = nueva_fecha
            cita.tipo_cita_id = request.form.get('tipo_cita_id')
            cita.duracion = cita.obtener_duracion()
            cita.status = request.form.get('status')
            
            # CORREGIDO: Lógica simplificada para manejar notas
            nota_texto = request.form.get('nota', '').strip()
            
            # Opción 1: Si tu modelo Cita tiene un campo 'notas' (texto simple)
            cita.notas = nota_texto if nota_texto else None
            
            # Opción 2: Si tienes una tabla separada de Notas (descomenta si es el caso)
            """
            # Buscar si ya existe una nota para esta cita
            nota_existente = Nota.query.filter_by(cita_id=cita.id).first()
            
            if nota_texto:
                if nota_existente:
                    # Actualizar nota existente
                    nota_existente.contenido = nota_texto
                    nota_existente.actualizado_en = datetime.utcnow()
                else:
                    # Crear nueva nota
                    nueva_nota = Nota(
                        contenido=nota_texto,
                        cita_id=cita.id,
                        psicologo_id=psicologo.id,
                        paciente_id=cita.paciente_id
                    )
                    db.session.add(nueva_nota)
            elif nota_existente:
                # Eliminar nota si se borró el contenido
                db.session.delete(nota_existente)
            """
            
            db.session.commit()
            flash('Cita actualizada exitosamente', 'success')
            return redirect(url_for('main.historial'))
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al editar cita {cita_id}: {str(e)}")
            flash(f'Error al actualizar la cita.', 'danger')
            return render_template('editar_cita.html', cita=cita, pacientes=pacientes, tipos_cita=tipos_cita, nota=nota_texto)
    
    return render_template('editar_cita.html', 
                          cita=cita, 
                          pacientes=pacientes, 
                          tipos_cita=tipos_cita, 
                          es_cita_pasada=es_cita_pasada,
                          nota=nota_texto)





@main.route('/api/cita/<int:cita_id>/notas', methods=['GET', 'POST'])
@login_required
def cita_notas(cita_id):
    try:
        psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
        if not psicologo:
            current_app.logger.error(f"Psicólogo no encontrado para usuario {current_user.id}")
            return jsonify({'success': False, 'message': 'Psicólogo no encontrado'}), 404
        
        cita = Cita.query.filter_by(id=cita_id, psicologo_id=psicologo.id).first()
        if not cita:
            current_app.logger.error(f"Cita {cita_id} no encontrada para psicólogo {psicologo.id}")
            return jsonify({'success': False, 'message': 'Cita no encontrada'}), 404
        
        if request.method == 'POST':
            data = request.get_json()
            current_app.logger.info(f"Datos recibidos para POST notas en cita {cita_id}: {data}")
            contenido = data.get('contenido', '').strip()
            
            # ACTUALIZADO: Usar el campo 'notas' del modelo Cita como en editar_cita
            if contenido:
                cita.notas = contenido
                current_app.logger.info(f"Nota actualizada directamente en cita {cita_id}")
            else:
                cita.notas = None
                current_app.logger.info(f"Nota eliminada de cita {cita_id}")
            
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Nota guardada correctamente',
                'nota': {'contenido': cita.notas} if cita.notas else None
            })
        
        # GET: Obtener la nota de la cita desde el campo 'notas'
        paciente = Paciente.query.get(cita.paciente_id)
        current_app.logger.info(f"Nota obtenida para cita {cita_id}: {'Sí' if cita.notas else 'Ninguna'}")
        
        return jsonify({
            'success': True,
            'patient_name': f"{paciente.nombre} {paciente.apellido}",
            'cita_id': cita_id,
            'notas': [{'contenido': cita.notas}] if cita.notas else []
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al gestionar notas de cita {cita_id}: {str(e)}")
        return jsonify({'success': False, 'message': f'Error interno del servidor: {str(e)}'}), 500




@main.route('/api/cita/<int:cita_id>/eliminar', methods=['POST'])
@login_required
def eliminar_cita(cita_id):
    try:
        # Buscar el psicólogo actual
        psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
        
        if not psicologo:
            return jsonify(success=False, message="Psicólogo no encontrado"), 404
        
        # Buscar la cita específicamente para este psicólogo
        cita = Cita.query.filter_by(id=cita_id, psicologo_id=psicologo.id).first()
        
        if not cita:
            return jsonify(success=False, message="Cita no encontrada"), 404
        
        # Eliminar notificaciones relacionadas
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notificaciones WHERE cita_id = ?", (cita_id,))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as db_error:
            print(f"Error al eliminar notificaciones: {str(db_error)}")
        
        # Eliminar la cita
        db.session.delete(cita)
        db.session.commit()
        
        return jsonify(success=True, message="Cita eliminada correctamente")
    
    except Exception as e:
        # En caso de error, hacer rollback
        db.session.rollback()
        
        # Registrar el error
        print(f"Error al eliminar cita: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Devolver mensaje de error
        return jsonify(success=False, message=f"Error al eliminar la cita: {str(e)}"), 500



# Ruta de configuración
@main.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    # Verificar que el usuario actual no sea un admin
    if current_user.tipo_usuario == 'admin':
        flash('Solo los psicologos pueden acceder a su configuracion.', 'danger')
        return redirect(url_for('main.verificar_psicologos'))
    
    # Primero obtenemos el objeto Psicologo asociado al usuario actual
    psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
    
    # Si no existe el perfil, creamos uno nuevo y vacío
    if not psicologo:
        psicologo = Psicologo(
            usuario_id=current_user.id,
            titulo='dr',  # Valor predeterminado
            especialidad='psicologia-clinica',  # Valor predeterminado
            nombre='Nuevo',
            apellido='Usuario'
        )
        db.session.add(psicologo)
        db.session.commit()
    
    # Ahora buscamos la configuración usando el ID del psicólogo
    configuracion = Configuracion.query.filter_by(psicologo_id=psicologo.id).first()
    
    # Si no existe configuración para este psicólogo, crear una por defecto
    if not configuracion:
        configuracion = Configuracion(
            psicologo_id=psicologo.id,
            notificaciones_email=True,
            tiempo_anticipacion=60,
            frecuencia_recordatorios=2,
            alertas_cambios_citas=True,
            alertas_pacientes_nuevos=True,
            notificaciones_actualizacion=True,
            sonidos_notificacion=False,
            retencion_datos=5
        )
        db.session.add(configuracion)
        db.session.commit()
    
    # Pasamos tanto el objeto psicologo como configuracion a la plantilla
    return render_template('config.html', psicologo=psicologo, configuracion=configuracion)



@main.route('/api/obtener-config', methods=['GET'])
@login_required
def obtener_config():
    # Verificar que el usuario actual no sea un admin
    if current_user.tipo_usuario == 'admin':
        return jsonify(success=False, message="Acceso denegado")
    
    # Primero obtenemos el objeto Psicologo asociado al usuario actual
    psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
    
    if not psicologo:
        return jsonify(success=False, message="No se encontró el perfil de psicólogo")
    
    # Ahora buscamos la configuración usando el ID del psicólogo
    configuracion = Configuracion.query.filter_by(psicologo_id=psicologo.id).first()
    
    if not configuracion:
        return jsonify(success=False, message="No existe configuración para este usuario")
    
    # Ya no necesitamos devolver estos datos porque las pestañas fueron eliminadas
    return jsonify(
        success=True
    )




# Ruta para obtener los datos del perfil del psicólogo
@main.route('/api/obtener-perfil-psicologo', methods=['GET'])
@login_required
def obtener_perfil_psicologo():
    # Verificar que el usuario actual no sea un admin
    if current_user.tipo_usuario == 'admin':
        return jsonify(success=False, message="Acceso denegado")
    
    # Obtenemos el objeto Psicologo asociado al usuario actual
    psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
    
    # Si no existe el perfil, creamos uno nuevo y vacío
    if not psicologo:
        psicologo = Psicologo(
            usuario_id=current_user.id,
            titulo='',
            especialidad='',
            nombre='',
            apellido='',
            numero_licencia='',
            telefono='',
            direccion_consulta=''
        )
        db.session.add(psicologo)
        db.session.commit()
        
        return jsonify(
            success=True,
            titulo='',
            especialidad='',
            nombre_completo='',
            numero_licencia='',
            email=current_user.email,  # Obtenemos el email del usuario actual
            telefono='',
            direccion='',
            message='Se ha creado un nuevo perfil. Por favor, completa tu información.'
        )
    
    # Si existe el perfil, devolvemos sus datos incluyendo el email del usuario
    return jsonify(
        success=True,
        titulo=getattr(psicologo, 'titulo', '') or '',
        especialidad=getattr(psicologo, 'especialidad', '') or '',
        nombre_completo=psicologo.nombre_completo,
        numero_licencia=getattr(psicologo, 'numero_licencia', '') or '',
        email=psicologo.usuario.email if psicologo.usuario else '',  # Obtener email del usuario asociado
        telefono=getattr(psicologo, 'telefono', '') or '',
        direccion=getattr(psicologo, 'direccion_consulta', '') or ''  # Cambiado a direccion_consulta
    )





@main.route('/api/guardar-config', methods=['POST'])
@login_required
def guardar_config():
    try:
        # Verificar que los datos enviados sean JSON
        if not request.is_json:
            return jsonify(success=False, message="Se esperaba contenido JSON"), 400
            
        # Obtenemos el objeto Psicologo asociado al usuario actual
        psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
        
        if not psicologo:
            return jsonify(success=False, message="No se encontró el perfil de psicólogo")
        
        data = request.get_json()
        print(f"Datos recibidos: {data}")  # Log para depuración
        
        if 'tab' in data:
            tab = data['tab']
            
            # Si es la pestaña 'profile', actualizamos los datos del psicólogo
            if tab == 'profile':
                # Actualizamos los campos del psicólogo con los datos recibidos
                if 'title' in data:
                    psicologo.titulo = data['title']
                if 'specialty' in data:
                    psicologo.especialidad = data['specialty']
                if 'fullname' in data:
                    psicologo.set_nombre_completo(data['fullname'])
                if 'license' in data:
                    psicologo.numero_licencia = data['license']
                if 'email' in data:
                    # Actualizamos el email en el usuario relacionado
                    if psicologo.usuario:
                        psicologo.usuario.email = data['email']
                if 'phone' in data:
                    psicologo.telefono = data['phone']
                if 'address' in data:
                    # Corregido para usar el nombre correcto del campo según tu modelo
                    psicologo.direccion_consulta = data['address']
                
                # Guardar los cambios en la base de datos
                db.session.commit()
                
                return jsonify(success=True, message="Perfil actualizado correctamente")
            
            # Dentro de la función guardar_config, justo después del bloque 'profile'
            elif tab == 'security':
                # Obtener el usuario asociado al psicólogo
                usuario = psicologo.usuario
                
                # Obtener la configuración
                configuracion = Configuracion.query.filter_by(psicologo_id=psicologo.id).first()
    
                if not configuracion:
                    configuracion = Configuracion(psicologo_id=psicologo.id)
                    db.session.add(configuracion)
    
                # Actualizar campos de seguridad en Usuario
                if 'auth_dos_factores' in data:
                    usuario.auth_dos_factores = data['auth_dos_factores']
                if 'cierre_sesion_auto' in data:
                    usuario.cierre_sesion_auto = data['cierre_sesion_auto']
                if 'tiempo_inactividad' in data:
                    usuario.tiempo_inactividad = data['tiempo_inactividad']
                
                # Actualizar retención de datos en Configuracion
                if 'retencion_datos' in data:
                    configuracion.retencion_datos = data['retencion_datos']
    
                db.session.commit()
                return jsonify(success=True, message="Configuración de seguridad guardada correctamente")
                
            # Añadir soporte para la pestaña de notificaciones
            elif tab == 'notifications':
                configuracion = Configuracion.query.filter_by(psicologo_id=psicologo.id).first()
                
                if not configuracion:
                    configuracion = Configuracion(psicologo_id=psicologo.id)
                    db.session.add(configuracion)
                
                # Guardar configuración de notificaciones
                if 'notificaciones_email' in data:
                    configuracion.notificaciones_email = data['notificaciones_email']
                if 'tiempo_anticipacion' in data:
                    configuracion.tiempo_anticipacion = data['tiempo_anticipacion']
                if 'frecuencia_recordatorios' in data:
                    configuracion.frecuencia_recordatorios = data['frecuencia_recordatorios']
                if 'alertas_cambios_citas' in data:
                    configuracion.alertas_cambios_citas = data['alertas_cambios_citas']
                if 'alertas_pacientes_nuevos' in data:
                    configuracion.alertas_pacientes_nuevos = data['alertas_pacientes_nuevos']
                if 'notificaciones_actualizacion' in data:
                    configuracion.notificaciones_actualizacion = data['notificaciones_actualizacion']
                if 'sonidos_notificacion' in data:
                    configuracion.sonidos_notificacion = data['sonidos_notificacion']
                
                db.session.commit()
                return jsonify(success=True, message="Configuración de notificaciones guardada correctamente")
        
        return jsonify(success=False, message="No se especificó pestaña de configuración")
    
    except Exception as e:
        # Registrar el error para depuración
        print(f"Error en guardar_config: {str(e)}")
        # Hacer rollback de la sesión
        db.session.rollback()
        # Devolver respuesta de error
        return jsonify(success=False, message=f"Error del servidor: {str(e)}"), 500
    





@main.route('/api/cambiar-contrasena', methods=['POST'])
@login_required
def cambiar_contrasena():
    try:
        # Verificar que los datos sean JSON
        if not request.is_json:
            return jsonify(success=False, message="Se esperaba contenido JSON"), 400
            
        data = request.get_json()
        
        # Verificar que se enviaron los campos necesarios
        if not data or 'current_password' not in data or 'new_password' not in data:
            return jsonify(success=False, message="Faltan campos requeridos"), 400
        
        # Verificar la contraseña actual
        if not current_user.check_password(data['current_password']):
            return jsonify(success=False, message="La contraseña actual es incorrecta"), 401
        
        # Validar la nueva contraseña
        new_password = data['new_password']
        if len(new_password) < 8:
            return jsonify(success=False, message="La contraseña debe tener al menos 8 caracteres"), 400
        
        # Verificar requisitos adicionales de seguridad
        if not any(c.isupper() for c in new_password):
            return jsonify(success=False, message="La contraseña debe contener al menos una letra mayúscula"), 400
            
        if not any(c.isdigit() for c in new_password):
            return jsonify(success=False, message="La contraseña debe contener al menos un número"), 400
            
        if not any(c in "!@#$%^&*(),.?\":{}|<>" for c in new_password):
            return jsonify(success=False, message="La contraseña debe contener al menos un carácter especial"), 400
        
        # Actualizar la contraseña
        current_user.set_password(new_password)
        db.session.commit()
        
        return jsonify(success=True, message="Contraseña actualizada correctamente")
        
    except Exception as e:
        # Log del error para depuración
        print(f"Error en cambiar_contrasena: {str(e)}")
        db.session.rollback()
        return jsonify(success=False, message=f"Error al cambiar la contraseña: {str(e)}"), 500





@main.route('/api/obtener-security-config', methods=['GET'])
@login_required
def obtener_security_config():
    # Primero obtenemos el objeto Psicologo asociado al usuario actual
    psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
    
    if not psicologo:
        return jsonify(success=False, message="No se encontró el perfil de psicólogo")
    
    # Ahora buscamos la configuración usando el ID del psicólogo
    configuracion = Configuracion.query.filter_by(psicologo_id=psicologo.id).first()
    
    if not configuracion:
        return jsonify(success=False, message="No existe configuración para este usuario")
    
    # Obtener datos de seguridad desde el usuario
    usuario = psicologo.usuario
    
    return jsonify(
        success=True,
        auth_dos_factores=usuario.auth_dos_factores,
        cierre_sesion_auto=usuario.cierre_sesion_auto,
        tiempo_inactividad=usuario.tiempo_inactividad,
        retencion_datos=configuracion.retencion_datos
    )




# Ruta para eliminar cuenta
@main.route('/api/eliminar-cuenta', methods=['POST'])
@login_required
def eliminar_cuenta():
    # Verificar que el usuario es un psicólogo
    if not current_user.es_psicologo():
        return jsonify(success=False, message="Solo los psicólogos pueden eliminar su cuenta"), 403
    
    # Obtener datos del formulario
    data = request.get_json()
    if not data or 'password' not in data:
        return jsonify(success=False, message="Contraseña no proporcionada"), 400
    
    # Verificar la contraseña
    if not current_user.check_password(data['password']):
        return jsonify(success=False, message="Contraseña incorrecta"), 401
    
    # Obtener el objeto Psicologo asociado a este usuario
    psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
    if not psicologo:
        return jsonify(success=False, message="No se encontró el perfil de psicólogo"), 404
    
    try:
        # Verificar si hay pacientes asociados
        pacientes_count = Paciente.query.filter_by(psicologo_id=psicologo.id).count()
        if pacientes_count > 0:
            return jsonify(
                success=False, 
                message=f"No se puede eliminar la cuenta porque tienes {pacientes_count} pacientes asociados. Transfiere o elimina tus pacientes primero."
            ), 400
        
        # Verificar si hay citas pendientes
        citas_futuras = Cita.query.filter(
            Cita.psicologo_id == psicologo.id,
            Cita.fecha > datetime.now(),
            Cita.status.in_(['Programada', 'Confirmada'])
        ).count()
        
        if citas_futuras > 0:
            return jsonify(
                success=False, 
                message=f"No se puede eliminar la cuenta porque tienes {citas_futuras} citas pendientes. Cancela tus citas primero."
            ), 400
        
        # Obtener IDs para referencias
        usuario_id = current_user.id
        psicologo_id = psicologo.id
        
        # Eliminar notificaciones asociadas a las citas del psicólogo
        # Primero obtener IDs de citas
        citas_ids = [cita.id for cita in Cita.query.filter_by(psicologo_id=psicologo_id).all()]
        
        # Eliminar notificaciones relacionadas con estas citas
        if citas_ids:
            Notificacion.query.filter(Notificacion.cita_id.in_(citas_ids)).delete(synchronize_session=False)
        
        # Eliminar configuración
        Configuracion.query.filter_by(psicologo_id=psicologo_id).delete()
        
        # Eliminar relaciones con tipos de cita
        db.session.execute(db.delete(psicologo_tipo_cita).where(
            psicologo_tipo_cita.c.psicologo_id == psicologo_id
        ))
        
        # Eliminar citas históricas
        Cita.query.filter_by(psicologo_id=psicologo_id).delete()
        
        # Eliminar el psicólogo
        db.session.delete(psicologo)
        
        # Eliminar el usuario asociado
        usuario = Usuario.query.get(usuario_id)
        db.session.delete(usuario)
        
        # Confirmar los cambios
        db.session.commit()
        
        # Cerrar la sesión del usuario
        logout_user()
        
        return jsonify(success=True, message="Tu cuenta ha sido eliminada correctamente")
        
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message=f"Error al eliminar la cuenta: {str(e)}"), 500
        



# Ruta de estadísticas
@main.route('/estadisticas')
@login_required
def estadisticas():
    
    return render_template('estadisticas.html')



@main.route('/api/estadisticas', methods=['GET'])
@login_required
def api_estadisticas():
    periodo = request.args.get('periodo', 'semana')
    
    # Get the psychologist ID
    psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
    if not psicologo:
        return jsonify({"error": "No se encontró perfil de psicólogo"}), 404
    
    # Calculate time ranges based on periodo
    today = datetime.now()
    if periodo == 'semana':
        start_date = today - timedelta(days=today.weekday())
    elif periodo == 'mes':
        start_date = today.replace(day=1)
    elif periodo == 'trimestre':
        start_date = today - timedelta(days=90)
    elif periodo == 'año':
        start_date = today.replace(month=1, day=1)
    else:  # 'todo'
        start_date = datetime(2000, 1, 1)  # Set to a very old date
    
    # Get patients and appointments data
    pacientes = Paciente.query.filter_by(psicologo_id=psicologo.id).all()
    citas = Cita.query.filter(
        Cita.psicologo_id == psicologo.id,
        Cita.fecha >= start_date
    ).all()
    
    # Count patients by gender
    genero_count = {
        'masculino': sum(1 for p in pacientes if p.genero == 'Masculino'),
        'femenino': sum(1 for p in pacientes if p.genero == 'Femenino'),
        'otro': sum(1 for p in pacientes if p.genero and p.genero not in ['Masculino', 'Femenino'])
    }
    
    # Count patients by age range
    edad_ranges = {
        '0-12': 0, '13-17': 0, '18-25': 0, '26-35': 0,
        '36-45': 0, '46-60': 0, '60+': 0
    }
    
    for p in pacientes:
        if hasattr(p, 'edad') and p.edad:
            if p.edad <= 12:
                edad_ranges['0-12'] += 1
            elif p.edad <= 17:
                edad_ranges['13-17'] += 1
            elif p.edad <= 25:
                edad_ranges['18-25'] += 1
            elif p.edad <= 35:
                edad_ranges['26-35'] += 1
            elif p.edad <= 45:
                edad_ranges['36-45'] += 1
            elif p.edad <= 60:
                edad_ranges['46-60'] += 1
            else:
                edad_ranges['60+'] += 1
    
    # Count appointments by status
    status_count = {
        'programadas': sum(1 for c in citas if c.status == 'Programada'),
        'completadas': sum(1 for c in citas if c.status == 'Completada'),
        'reprogramadas': sum(1 for c in citas if c.status == 'Reprogramada'),
        'canceladas': sum(1 for c in citas if c.status == 'Cancelada')
    }
    
    # Count appointments by month
    month_names = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    citas_por_mes = {}
    
    for i in range(6):  # Last 6 months
        month_date = today.replace(day=1) - timedelta(days=30*i)
        month_name = month_names[month_date.month-1]
        citas_por_mes[month_name] = sum(1 for c in citas if c.fecha.month == month_date.month and c.fecha.year == month_date.year)
    
    # Calculate attendance rate
    total_pasadas = sum(1 for c in citas if c.fecha < today and c.status in ['Completada', 'Cancelada'])
    asistidas = sum(1 for c in citas if c.fecha < today and c.status == 'Completada')
    tasa_asistencia = round((asistidas / total_pasadas) * 100) if total_pasadas > 0 else 0
    
    # Get latest appointments for the table (limit to 10)
    ultimas_citas = []
    for cita in sorted(citas, key=lambda x: x.fecha, reverse=True)[:10]:
        paciente = Paciente.query.get(cita.paciente_id)
        ultimas_citas.append({
            'id': cita.id,
            'paciente': f"{paciente.nombre} {paciente.apellido}",
            'fecha': cita.fecha.isoformat(),
            'tipo': cita.tipo_cita.nombre if cita.tipo_cita else "No especificado",
            'duracion': cita.obtener_duracion(),
            'status': cita.status
        })
    
    # Prepare the response data
    response_data = {
        'pacientes': {
            'total': len(pacientes),
            'porGenero': genero_count,
            'porEdad': edad_ranges
        },
        'citas': {
            'completadas': status_count['completadas'],
            'pendientes': status_count['programadas'],
            'reprogramadas': status_count['reprogramadas'],
            'canceladas': status_count['canceladas'],
            'asistencia': tasa_asistencia,
            'porStatus': status_count,
            'porMes': citas_por_mes,
            'ultimas': ultimas_citas
        }
    }
    
    return jsonify(response_data)




@main.route('/api/estadisticas/exportar', methods=['POST'])
@login_required
def exportar_estadisticas():
    periodo = request.args.get('periodo', 'semana')
    
    # Here you would generate a PDF with statistics
    # For now, just return a simple text file as placeholder
    from io import BytesIO
    
    buffer = BytesIO()
    buffer.write(f"Estadísticas del período: {periodo}\n".encode('utf-8'))
    buffer.write(f"Generado en: {datetime.now()}\n".encode('utf-8'))
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"estadisticas_{periodo}_{datetime.now().strftime('%Y-%m-%d')}.pdf",
        mimetype='application/pdf'
    )





from flask import jsonify, current_app, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta

@main.route('/api/proximas-citas')
@login_required
def proximas_citas():
    """
    Retorna las citas próximas para notificaciones en tiempo real.
    Busca citas que comienzan en los próximos minutos (configurable).
    """
    try:
        # Obtener la configuración del psicólogo actual
        psicologo = current_user.psicologo
        if not psicologo:
            return jsonify({"success": False, "message": "Usuario no es un psicólogo"}), 403
        
        # Obtener la configuración de notificaciones
        config = psicologo.configuracion
        tiempo_anticipacion = config.tiempo_anticipacion if config else 60  # Por defecto 60 minutos
        
        # Calcular el rango de tiempo para buscar citas
        ahora = datetime.now()
        limite_inferior = ahora
        limite_superior = ahora + timedelta(minutes=tiempo_anticipacion)
        
        # Buscar citas en el rango y que no hayan enviado recordatorio
        citas_proximas = Cita.query.filter(
            Cita.psicologo_id == psicologo.id,
            Cita.fecha.between(limite_inferior, limite_superior),
            Cita.status == 'Programada',
            Cita.recordatorio_enviado == False
        ).all()
        
        # Preparar la respuesta
        citas = []
        for cita in citas_proximas:
            paciente = Paciente.query.get(cita.paciente_id)
            tipo_cita = TipoCita.query.get(cita.tipo_cita_id) if cita.tipo_cita_id else None
            
            # Calcular tiempo hasta la cita
            tiempo_restante = cita.fecha - ahora
            minutos_restantes = int(tiempo_restante.total_seconds() / 60)
            
            citas.append({
                'id': cita.id,
                'paciente': f"{paciente.nombre} {paciente.apellido}",
                'fecha': cita.fecha.isoformat(),
                'hora': cita.fecha.strftime('%H:%M'),
                'duracion': cita.obtener_duracion(),
                'tipo': tipo_cita.nombre if tipo_cita else "No especificado",
                'minutos_restantes': minutos_restantes
            })
            
            # Marcar la cita como que ya se envió recordatorio
            cita.recordatorio_enviado = True
            
            # Programar las notificaciones para la cita si está configurado en la configuración del psicólogo
            Notificacion.programar_recordatorios_cita(db.session, cita, config)

        # Guardar cambios en la base de datos
        db.session.commit()
        
        return jsonify({
            "success": True,
            "citas": citas,
            "config": {
                "tiempo_anticipacion": tiempo_anticipacion,
                "sonidos_notificacion": config.sonidos_notificacion if config else False
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al obtener citas próximas: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
    






from flask import Blueprint, jsonify
from app import create_app
from app.database import db, Notificacion


@main.route('/api/enviar-notificaciones', methods=['GET'])
@login_required
def enviar_notificaciones():
    try:
        # Obtener las citas próximas y programar notificaciones
        citas_proximas = Cita.query.filter(Cita.status == 'Programada').all()
        
        print(f"Se encontraron {len(citas_proximas)} citas programadas.")  # Ver cuántas citas se encuentran

        for cita in citas_proximas:
            # Obtener la configuración del psicólogo de la cita
            config = Configuracion.query.filter_by(psicologo_id=cita.psicologo_id).first()

            if not config:
                print(f"No se encontró configuración para la cita con id {cita.id}")
                continue  # Si no hay configuración, pasar a la siguiente cita

            # Llamar a la función para programar las notificaciones
            Notificacion.programar_recordatorios_cita(db.session, cita, config)
        
        # Verificar que las notificaciones se han creado
        notificaciones = Notificacion.query.all()
        print(f"Notificaciones en la base de datos: {len(notificaciones)}")  # Mostrar la cantidad de notificaciones

        return jsonify({
            "message": "Notificaciones enviadas correctamente."
        })
    except Exception as e:
        current_app.logger.error(f"Error al enviar notificaciones: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500









@main.route('/api/marcar-notificada/<int:cita_id>', methods=['POST'])
@login_required
def marcar_notificada(cita_id):
    """Marca una cita como notificada manualmente"""
    try:
        cita = Cita.query.get_or_404(cita_id)
        
        # Verificar que la cita pertenezca al psicólogo actual
        if cita.psicologo_id != current_user.psicologo.id:
            return jsonify({"success": False, "message": "No tienes permiso para esta cita"}), 403
        
        cita.recordatorio_enviado = True
        db.session.commit()
        
        return jsonify({"success": True, "message": "Cita marcada como notificada"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


    


@main.route('/api/programar-notificaciones', methods=['POST'])
@login_required
def programar_notificaciones():
    try:
        # Aquí deberías implementar la lógica para programar las notificaciones.
        # Esto podría incluir guardar un evento en la base de datos, programar un job, etc.
        
        return jsonify({'success': True, 'message': 'Notificaciones programadas correctamente'})
    
    except Exception as e:
        print(f"Error al programar notificaciones: {e}")
        return jsonify({'success': False, 'message': 'Error al programar las notificaciones'}), 500

    



@main.route('/api/notificaciones/pendientes')
@login_required
def obtener_notificaciones_pendientes():
    """Obtiene las notificaciones pendientes para el usuario actual"""
    try:
        # Verificar si es psicólogo
        psicologo = current_user.psicologo
        if not psicologo:
            return jsonify({"success": False, "message": "Usuario no es un psicólogo"}), 403
        
        # Obtener notificaciones no leídas para este psicólogo
        # (Solo notificaciones tipo 'app' o 'browser')
        notificaciones = Notificacion.query.join(
            Cita, Notificacion.cita_id == Cita.id
        ).filter(
            Cita.psicologo_id == psicologo.id,
            Notificacion.enviada == False,
            Notificacion.destinatario == 'psicologo',
            Notificacion.tipo.in_(['app', 'browser'])
        ).order_by(
            Notificacion.tiempo_envio.desc()
        ).limit(10).all()
        
        # Formatear resultado
        resultado = []
        for notif in notificaciones:
            resultado.append({
                'id': notif.id,
                'cita_id': notif.cita_id,
                'contenido': notif.contenido,
                'fecha': notif.tiempo_envio.isoformat(),
                'prioridad': notif.prioridad
            })
            
            # Marcar como enviada
            notif.enviada = True
            notif.fecha_envio = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "notificaciones": resultado
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al obtener notificaciones: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
        

# Actualizar esta ruta para manejar específicamente la configuración de notificaciones
@main.route('/api/obtener-notification-config')
@login_required
def obtener_notification_config():
    """Obtiene la configuración de notificaciones del psicólogo actual"""
    try:
        # Obtener el psicólogo actual
        psicologo = current_user.psicologo
        if not psicologo:
            current_app.logger.warning(f"Usuario {current_user.id} no es un psicólogo")
            return jsonify({"success": False, "message": "Usuario no es un psicólogo"}), 403
        
        current_app.logger.info(f"Obteniendo configuración para psicólogo {psicologo.id}")
        
        # Obtener o crear configuración
        config = psicologo.configuracion
        if not config:
            current_app.logger.info(f"Psicólogo {psicologo.id} no tiene configuración, usando valores predeterminados")
            # Si no hay configuración, usar valores predeterminados
            return jsonify({
                "success": True,
                "notificaciones_email": True,
                "tiempo_anticipacion": 60,
                "frecuencia_recordatorios": 2,
                "alertas_cambios_citas": True,
                "alertas_pacientes_nuevos": True,
                "notificaciones_actualizacion": True,
                "sonidos_notificacion": False
            })
        
        # Devolver configuración existente
        current_app.logger.info(f"Configuración encontrada: {config.id}")
        return jsonify({
            "success": True,
            "notificaciones_email": config.notificaciones_email,
            "tiempo_anticipacion": config.tiempo_anticipacion,
            "frecuencia_recordatorios": config.frecuencia_recordatorios,
            "alertas_cambios_citas": config.alertas_cambios_citas,
            "alertas_pacientes_nuevos": config.alertas_pacientes_nuevos,
            "notificaciones_actualizacion": config.notificaciones_actualizacion,
            "sonidos_notificacion": config.sonidos_notificacion
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener configuración de notificaciones: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500





# Ruta de contacto
@main.route('/contacto', methods=['GET', 'POST'])
def contacto():
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            nombre = request.form.get('nombre')
            email = request.form.get('email')
            telefono = request.form.get('telefono', '')
            asunto = request.form.get('asunto')
            mensaje = request.form.get('mensaje')
            
            # Validar datos
            if not nombre or not email or not asunto or not mensaje:
                flash('Por favor complete todos los campos obligatorios', 'danger')
                return redirect(url_for('main.contacto'))
            
            # Obtener dirección IP para prevención de spam
            ip_remitente = request.remote_addr
            
            # Obtener el ID del psicólogo actual si el usuario está autenticado y es psicólogo
            psicologo_id = None
            if current_user.is_authenticated and current_user.es_psicologo():
                # Buscar el objeto Psicologo asociado con este usuario
                psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
                if psicologo:
                    psicologo_id = psicologo.id
            
            # Crear nuevo mensaje de contacto
            nuevo_contacto = Contacto(
                nombre=nombre,
                email=email,
                telefono=telefono,
                asunto=asunto,
                mensaje=mensaje,
                ip_remitente=ip_remitente,
                psicologo_id=psicologo_id
            )
            
            db.session.add(nuevo_contacto)
            db.session.commit()
            
            # Enviar notificación por email al administrador
            try:
                enviar_notificacion_contacto(nuevo_contacto)
            except Exception as e:
                # Solo loggear el error pero no afectar la experiencia del usuario
                print(f"Error al enviar notificación: {str(e)}")
            
            flash('¡Gracias por contactarnos! Te responderemos a la brevedad.', 'success')
            return redirect(url_for('main.contacto'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error en formulario de contacto: {str(e)}")
            flash('Error al enviar el mensaje. Por favor intente nuevamente.', 'danger')
            return redirect(url_for('main.contacto'))
    
    # Para solicitudes GET
    # Si el usuario está autenticado, prellenar los campos con sus datos
    datos_iniciales = {}
    if current_user.is_authenticated:
        datos_iniciales['nombre'] = getattr(current_user, 'nombre', '')
        datos_iniciales['email'] = current_user.email
        
        # Si es psicólogo o paciente, obtener teléfono
        if current_user.es_psicologo():
            psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
            if psicologo:
                datos_iniciales['nombre'] = f"{psicologo.nombre} {psicologo.apellido}"
                datos_iniciales['telefono'] = psicologo.telefono or ''
        elif current_user.es_paciente():
            paciente = Paciente.query.filter_by(usuario_id=current_user.id).first()
            if paciente:
                datos_iniciales['nombre'] = f"{paciente.nombre} {paciente.apellido}"
                datos_iniciales['telefono'] = paciente.telefono or ''
    
    return render_template('contacto.html', datos=datos_iniciales)




@main.route('/admin/contactos')
@login_required
def admin_contactos():
    """
    Vista para administrar los mensajes de contacto (solo disponible para administradores o psicólogos)
    """
    # Verificar permisos (solo administradores o psicólogos pueden ver esta página)
    if not current_user.es_psicologo() and not (hasattr(current_user, 'rol') and current_user.rol and current_user.rol.nombre == 'admin'):
        flash('Acceso denegado. No tienes permisos para ver esta página.', 'danger')
        return redirect(url_for('main.index'))
    
    # Si es psicólogo, solo ver mensajes relacionados con él
    if current_user.es_psicologo():
        psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
        if psicologo:
            # Mensajes asignados directamente a este psicólogo o sin asignar
            mensajes = Contacto.query.filter(
                (Contacto.psicologo_id == psicologo.id) | 
                (Contacto.psicologo_id == None)
            ).order_by(Contacto.fecha_envio.desc()).all()
        else:
            mensajes = []
    else:
        # Si es admin, ver todos los mensajes
        mensajes = Contacto.query.order_by(Contacto.fecha_envio.desc()).all()
    
    # Estadísticas
    total_mensajes = len(mensajes)
    mensajes_no_leidos = sum(1 for m in mensajes if not m.leido)
    mensajes_respondidos = sum(1 for m in mensajes if m.respondido)
    
    return render_template(
        'admin/contactos.html',  # Esta plantilla deberá ser creada
        mensajes=mensajes,
        total_mensajes=total_mensajes,
        mensajes_no_leidos=mensajes_no_leidos,
        mensajes_respondidos=mensajes_respondidos
    )


@main.route('/admin/contacto/<int:contacto_id>', methods=['GET', 'POST'])
@login_required
def ver_contacto(contacto_id):
    """
    Vista para ver y responder a un mensaje específico
    """
    # Verificar permisos
    if not current_user.es_psicologo() and not (hasattr(current_user, 'rol') and current_user.rol and current_user.rol.nombre == 'admin'):
        flash('Acceso denegado. No tienes permisos para ver esta página.', 'danger')
        return redirect(url_for('main.index'))
    
    # Obtener el mensaje
    contacto = Contacto.query.get_or_404(contacto_id)
    
    # Si es psicólogo, verificar que el mensaje le pertenezca o no esté asignado
    if current_user.es_psicologo():
        psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
        if psicologo and contacto.psicologo_id and contacto.psicologo_id != psicologo.id:
            flash('No tienes permisos para ver este mensaje.', 'danger')
            return redirect(url_for('main.admin_contactos'))
    
    # Marcar como leído si no lo estaba
    if not contacto.leido:
        contacto.leido = True
        db.session.commit()
    
    # Procesar respuesta
    if request.method == 'POST':
        respuesta = request.form.get('respuesta')
        
        if respuesta:
            # Aquí podrías implementar el envío de la respuesta por email
            # enviar_respuesta_contacto(contacto, respuesta)
            
            # Marcar como respondido
            contacto.respondido = True
            db.session.commit()
            
            flash('Respuesta enviada correctamente.', 'success')
            return redirect(url_for('main.admin_contactos'))
        else:
            flash('Por favor, escribe una respuesta.', 'warning')
    
    return render_template(
        'admin/ver_contacto.html',  # Esta plantilla deberá ser creada
        contacto=contacto
    )


@main.route('/admin/contacto/<int:contacto_id>/asignar', methods=['POST'])
@login_required
def asignar_contacto(contacto_id):
    """
    Ruta para asignar un mensaje a un psicólogo específico
    """
    # Verificar permisos (solo admin)
    if not (hasattr(current_user, 'rol') and current_user.rol and current_user.rol.nombre == 'admin'):
        return jsonify(success=False, message='Permiso denegado'), 403
    
    # Obtener mensaje y datos
    contacto = Contacto.query.get_or_404(contacto_id)
    data = request.get_json()
    psicologo_id = data.get('psicologo_id')
    
    # Validar psicólogo
    if psicologo_id:
        psicologo = Psicologo.query.get(psicologo_id)
        if not psicologo:
            return jsonify(success=False, message='Psicólogo no encontrado'), 404
    
    # Actualizar asignación
    contacto.psicologo_id = psicologo_id
    db.session.commit()
    
    return jsonify(success=True, message='Mensaje asignado correctamente')


@main.route('/admin/contacto/<int:contacto_id>/eliminar', methods=['POST'])
@login_required
def eliminar_contacto(contacto_id):
    """
    Ruta para eliminar un mensaje de contacto
    """
    # Verificar permisos
    if not current_user.es_psicologo() and not (hasattr(current_user, 'rol') and current_user.rol and current_user.rol.nombre == 'admin'):
        return jsonify(success=False, message='Permiso denegado'), 403
    
    # Obtener el mensaje
    contacto = Contacto.query.get_or_404(contacto_id)
    
    # Si es psicólogo, verificar que el mensaje le pertenezca o no esté asignado
    if current_user.es_psicologo():
        psicologo = Psicologo.query.filter_by(usuario_id=current_user.id).first()
        if psicologo and contacto.psicologo_id and contacto.psicologo_id != psicologo.id:
            return jsonify(success=False, message='No tienes permisos para eliminar este mensaje'), 403
    
    # Eliminar el mensaje
    db.session.delete(contacto)
    db.session.commit()
    
    return jsonify(success=True, message='Mensaje eliminado correctamente')