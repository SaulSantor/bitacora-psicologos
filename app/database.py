from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, time, timedelta
import json
from flask_login import LoginManager
from enum import Enum
from sqlalchemy import Enum as SQLAlchemyEnum
import pyodbc
import configparser
from sqlalchemy.dialects.mssql import NVARCHAR, BIT, SMALLINT, TIME
from flask_migrate import Migrate
import secrets
import pyotp
from functools import wraps
from werkzeug.utils import secure_filename
import os
from sqlalchemy import event
from sqlalchemy.orm import Session


# Inicializar SQLAlchemy
db = SQLAlchemy()

# Inicializar LoginManager
login_manager = LoginManager()

migrate = Migrate()

# Iniciar sesion
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


def get_db_connection():
    # Intentar leer la configuración del archivo config.ini
    try:
        config = configparser.ConfigParser()
        config.read('config.ini')
        conn_str = config.get('Database', 'CONNECTION_STRING')
        return pyodbc.connect(conn_str)
    except:
        # Si no se puede leer del archivo, usar valores por defecto o de entorno
        conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=LAPTOP-O1FGL8OS;DATABASE=Integrador;UID=sa;PWD=12345678"
        return pyodbc.connect(conn_str)
    

def validar_psicologo(psicologo_id):
    """
    Verifica si un psicólogo existe y tiene un usuario válido.
    
    Args:
        psicologo_id: El ID del psicólogo a validar
        
    Returns:
        tuple: (existe, mensaje), donde existe es un booleano y mensaje es una cadena
    """
    if not psicologo_id:
        return False, "No se ha proporcionado un ID de psicólogo"
    
    psicologo = Psicologo.query.get(psicologo_id)
    if not psicologo:
        return False, f"No existe ningún psicólogo con ID {psicologo_id}"
    
    if not psicologo.usuario:
        return False, f"El psicólogo con ID {psicologo_id} no tiene un usuario válido asociado"
        
    return True, "El psicólogo existe y tiene un usuario válido"




def crear_psicologo_seguro(datos_form):
    try:
        rol_psicologo = Rol.query.filter_by(nombre='psicologo').first()
        if not rol_psicologo:
            rol_psicologo = Rol(nombre='psicologo')
            db.session.add(rol_psicologo)
            db.session.flush()
        
        nuevo_usuario = Usuario(
            email=datos_form.get('email'),
            password=generate_password_hash(datos_form.get('password')),
            fecha_registro=datetime.utcnow(),
            activo=False,
            tipo_usuario='psicologo',
            rol_id=rol_psicologo.id
        )
        db.session.add(nuevo_usuario)
        db.session.flush()
        
        nuevo_psicologo = Psicologo(
            usuario_id=nuevo_usuario.id,
            nombre=datos_form.get('nombre'),
            apellido=datos_form.get('apellido'),
            titulo=datos_form.get('titulo'),
            especialidad=datos_form.get('especialidad'),
            numero_licencia=datos_form.get('numero_licencia'),
            telefono=datos_form.get('telefono'),
            institucion=datos_form.get('institucion'),
            estado_verificacion='pendiente'
        )
        db.session.add(nuevo_psicologo)
        db.session.commit()
        
        return True, nuevo_psicologo
    except Exception as e:
        db.session.rollback()
        return False, f"Error al crear psicólogo: {str(e)}"




def crear_paciente_seguro(datos_form, psicologo_id=None):
    # Si no se proporciona psicologo_id, intentar obtenerlo del formulario
    if not psicologo_id:
        psicologo_id = datos_form.get('psicologo_id')
    
    # Validar psicólogo
    psicologo_existe, mensaje = validar_psicologo(psicologo_id)
    if not psicologo_existe:
        return False, mensaje
    
    try:
        # Obtener rol de paciente
        rol_paciente = Rol.query.filter_by(nombre='paciente').first()
        if not rol_paciente:
            rol_paciente = Rol(nombre='paciente')
            db.session.add(rol_paciente)
            db.session.flush()
        
        # Generar contraseña si no se proporciona
        password = datos_form.get('password')
        if not password:
            import secrets
            import string
            caracteres = string.ascii_letters + string.digits
            password = ''.join(secrets.choice(caracteres) for i in range(10))
        
        # Crear usuario
        nuevo_usuario = Usuario(
            email=datos_form.get('email'),
            password=password,
            fecha_registro=datetime.utcnow(),
            activo=True,
            tipo_usuario='paciente',
            rol_id=rol_paciente.id
        )
        db.session.add(nuevo_usuario)
        db.session.flush()
        
        # Crear paciente
        nuevo_paciente = Paciente(
            usuario_id=nuevo_usuario.id,
            nombre=datos_form.get('nombre'),
            apellido=datos_form.get('apellido'),
            telefono=datos_form.get('telefono'),
            fecha_nacimiento=datetime.strptime(datos_form.get('fecha_nacimiento'), '%Y-%m-%d').date() if datos_form.get('fecha_nacimiento') else None,
            genero=datos_form.get('genero'),
            direccion=datos_form.get('direccion'),
            ocupacion=datos_form.get('ocupacion'),
            estado_civil=datos_form.get('estado_civil'),
            status=datos_form.get('status', 'Vigente'),
            diagnostico=datos_form.get('diagnostico'),
            notas=datos_form.get('notas', ''),
            psicologo_id=psicologo_id
        )
        db.session.add(nuevo_paciente)
        db.session.commit()
        
        return True, (nuevo_paciente, password)
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error al crear paciente: {str(e)}"


class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_login = db.Column(db.DateTime, nullable=True)
    activo = db.Column(db.Boolean, default=True)
    
    # Campos de seguridad
    auth_dos_factores = db.Column(db.Boolean, default=False)
    secreto_2fa = db.Column(db.String(32), nullable=True)
    cierre_sesion_auto = db.Column(db.Boolean, default=True)
    tiempo_inactividad = db.Column(db.Integer, default=15)
    intentos_fallidos = db.Column(db.Integer, default=0)
    bloqueado_hasta = db.Column(db.DateTime, nullable=True)
    
    # Relación con roles
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)
    rol = db.relationship('Rol', foreign_keys=[rol_id])
    
    # Discriminador para saber qué tipo de usuario es
    tipo_usuario = db.Column(db.String(20), nullable=False)
    
    # Relaciones one-to-one con psicólogo o paciente
    psicologo = db.relationship('Psicologo', 
                               foreign_keys='Psicologo.usuario_id', 
                               backref='usuario_base',  # Cambiado de 'usuario_base' a 'usuario'
                               uselist=False, 
                               cascade="all, delete-orphan")
    paciente = db.relationship('Paciente', backref='usuario_base', uselist=False, cascade="all, delete-orphan")
    
    @property
    def nombre(self):
        """Devuelve el nombre del usuario según su tipo"""
        if self.es_psicologo() and hasattr(self, 'psicologo') and self.psicologo:
            return self.psicologo.nombre
        elif self.es_paciente() and hasattr(self, 'paciente') and self.paciente:
            return self.paciente.nombre
        # Si no tiene nombre, devuelve la primera parte del email o un valor por defecto
        return self.email.split('@')[0] if self.email else "Usuario"

    @property
    def apellido(self):
        """Devuelve el apellido del usuario según su tipo"""
        if self.es_psicologo() and hasattr(self, 'psicologo') and self.psicologo:
            return self.psicologo.apellido
        elif self.es_paciente() and hasattr(self, 'paciente') and self.paciente:
            return self.paciente.apellido
        return ""

    @property
    def nombre_completo(self):
        """Devuelve el nombre completo del usuario según su tipo"""
        if self.es_psicologo() and hasattr(self, 'psicologo') and self.psicologo:
            return f"{self.psicologo.nombre} {self.psicologo.apellido}"
        elif self.es_paciente() and hasattr(self, 'paciente') and self.paciente:
            return f"{self.paciente.nombre} {self.paciente.apellido}"
        # Si no tiene nombre, devuelve el email o un valor por defecto
        return self.email if self.email else "Usuario sin nombre"

    @property
    def foto_perfil(self):
        """Devuelve la foto de perfil si existe"""
        if self.es_psicologo() and hasattr(self, 'psicologo') and self.psicologo:
            return self.psicologo.foto_perfil
        # Podrías añadir manejo para foto de pacientes si lo implementas en el futuro
        return None

    @property
    def password(self):
        raise AttributeError('password: no readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generar_secreto_2fa(self):
        """Genera un nuevo secreto para 2FA"""
        self.secreto_2fa = pyotp.random_base32()
        return self.secreto_2fa
        
    def verificar_2fa(self, token):
        """Verifica un token 2FA"""
        if not self.secreto_2fa:
            return False
        totp = pyotp.TOTP(self.secreto_2fa)
        return totp.verify(token)
    
    def get_qr_code_url(self, app_name="PsychCalendar"):
        """Genera URL para código QR de 2FA"""
        if not self.secreto_2fa:
            self.generar_secreto_2fa()
        totp = pyotp.TOTP(self.secreto_2fa)
        return totp.provisioning_uri(name=self.email, issuer_name=app_name)
    
    def registrar_login_exitoso(self):
        """Actualiza campos tras un login exitoso"""
        self.ultimo_login = datetime.utcnow()
        self.intentos_fallidos = 0
        self.bloqueado_hasta = None
        
    def registrar_login_fallido(self):
        """Actualiza campos tras un login fallido"""
        self.intentos_fallidos += 1
        # Bloquear cuenta temporalmente después de 5 intentos fallidos
        if self.intentos_fallidos >= 5:
            self.bloqueado_hasta = datetime.utcnow() + timedelta(minutes=15)
    
    def esta_bloqueado(self):
        """Verifica si la cuenta está bloqueada"""
        if self.bloqueado_hasta and self.bloqueado_hasta > datetime.utcnow():
            return True
        return False
    
    
    def es_psicologo(self):
        """Verifica si el usuario es psicólogo"""
        return self.tipo_usuario == 'psicologo'
    
    def es_paciente(self):
        """Verifica si el usuario es paciente"""
        return self.tipo_usuario == 'paciente'
    
    def set_password(self, password):
        """Establece un nuevo hash de contraseña para el usuario"""
        self.password_hash = generate_password_hash(password)


class Rol(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(20), nullable=False)
    
    # Relación inversa
    psicologos = db.relationship('Psicologo', backref='rol', lazy=True)
    
    def __repr__(self):
        return f'<Rol {self.nombre}>'


class Psicologo(db.Model, UserMixin):
    __tablename__ = 'psicologos'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    usuario = db.relationship('Usuario', foreign_keys=[usuario_id])
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    titulo = db.Column(db.String(10), nullable=True)
    especialidad = db.Column(db.String(255), nullable=True)
    otra_especialidad = db.Column(db.String(100), nullable=True)
    numero_licencia = db.Column(db.String(20), nullable=True)
    telefono = db.Column(db.String(20), nullable=True)
    direccion_consulta = db.Column(db.String(255), nullable=True)
    foto_perfil = db.Column(db.String(255), default='default.jpg', nullable=True)
    estado_verificacion = db.Column(db.String(20), default='pendiente')
    institucion = db.Column(db.String(100), nullable=True)
    fecha_verificacion = db.Column(db.DateTime, nullable=True)
    verificado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    comentarios_verificacion = db.Column(db.Text, nullable=True)
    ruta_archivo_titulo = db.Column(db.String(255), nullable=True)
    ruta_archivo_licencia = db.Column(db.String(255), nullable=True)
    
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)
    verificador = db.relationship('Usuario', 
                                 foreign_keys='Psicologo.verificado_por',
                                 backref='psicologos_verificados')
    tipos_cita_disponibles = db.relationship('TipoCita', 
                                            secondary='psicologo_tipo_cita', 
                                            lazy='subquery', 
                                            backref=db.backref('psicologos', lazy=True))
    pacientes = db.relationship('Paciente', backref='psicologo', lazy=True, cascade="all, delete-orphan")
    configuracion = db.relationship('Configuracion', backref='psicologo', uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Psicologo {self.nombre} {self.apellido}>'
    
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
    
    def set_nombre_completo(self, nombre_completo):
        partes = nombre_completo.strip().split(' ', 1)
        self.nombre = partes[0]
        self.apellido = partes[1] if len(partes) > 1 else ''
    
    def obtener_datos_perfil(self):
        return {
            'titulo': self.titulo or 'dra',
            'especialidad': self.especialidad or 'psicologia-clinica',
            'nombre_completo': self.nombre_completo(),
            'numero_licencia': self.numero_licencia or '',
            'email': self.usuario.email if self.usuario else '',
            'telefono': self.telefono or '',
            'direccion_consulta': self.direccion_consulta or ''
        }
    
    def actualizar_desde_formulario(self, form_data):
        self.titulo = form_data.get('title', self.titulo)
        self.especialidad = form_data.get('specialty', self.especialidad)
        self.set_nombre_completo(form_data.get('fullname', self.nombre_completo()))
        self.numero_licencia = form_data.get('license', self.numero_licencia)
        if self.usuario:
            self.usuario.email = form_data.get('email', self.usuario.email)
        self.telefono = form_data.get('phone', self.telefono)
        self.direccion_consulta = form_data.get('address', self.direccion_consulta)

    def get_tipos_cita(self):
        return self.tipos_cita_disponibles if self.tipos_cita_disponibles else TipoCita.query.filter_by(activo=True).all()
    
    def asignar_tipos_cita(self):
        if TipoCita.query.count() == 0:
            TipoCita.seed_default_types(db.session)
        tipos_activos = TipoCita.query.filter_by(activo=True).all()
        db.session.execute(
            psicologo_tipo_cita.delete().where(
                psicologo_tipo_cita.c.psicologo_id == self.id
            )
        )
        for tipo in tipos_activos:
            db.session.execute(
                psicologo_tipo_cita.insert().values(
                    psicologo_id=self.id, 
                    tipo_cita_id=tipo.id
                )
            )
        db.session.commit()




class Paciente(db.Model):
    __tablename__ = 'pacientes'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    usuario = db.relationship('Usuario', foreign_keys=[usuario_id])
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20), nullable=True)
    fecha_nacimiento = db.Column(db.Date, nullable=True)
    genero = db.Column(db.String(10), nullable=True)
    direccion = db.Column(db.Text, nullable=True)
    ocupacion = db.Column(db.String(100), nullable=True)
    estado_civil = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(50), nullable=True)
    diagnostico = db.Column(db.String(255), nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)
    psicologo_id = db.Column(db.Integer, db.ForeignKey('psicologos.id'), nullable=False)
    
    @property
    def edad(self):
        if self.fecha_nacimiento:
            today = date.today()
            return today.year - self.fecha_nacimiento.year - ((today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day))
        return None

    def __repr__(self):
        return f'<Paciente {self.nombre} {self.apellido}>'

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'apellido': self.apellido,
            'email': self.usuario.email if self.usuario else None,
            'telefono': self.telefono,
            'fecha_nacimiento': self.fecha_nacimiento.isoformat() if self.fecha_nacimiento else None,
            'genero': self.genero,
            'direccion': self.direccion,
            'ocupacion': self.ocupacion,
            'estado_civil': self.estado_civil,
            'status': self.status,
            'diagnostico': self.diagnostico,
            'activo': self.usuario.activo if self.usuario else None,
            'fecha_registro': self.usuario.fecha_registro.isoformat() if self.usuario and self.usuario.fecha_registro else None,
            'ultima_cita': self.ultima_cita.isoformat() if hasattr(self, 'ultima_cita') and self.ultima_cita else None,
            'proxima_cita': self.proxima_cita.isoformat() if hasattr(self, 'proxima_cita') and self.proxima_cita else None
        }





class Cita(db.Model):
    __tablename__ = 'citas'
    
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, nullable=False)
    tipo_cita_id = db.Column(db.Integer, db.ForeignKey('tipos_cita.id'), nullable=True)
    motivo = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Programada', nullable=True)
    asistio = db.Column(db.Boolean, default=None, nullable=True)
    recordatorio_enviado = db.Column(db.Boolean, default=False, nullable=False)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)
    google_event_id = db.Column(db.String(255), nullable=True)
    google_calendar_id = db.Column(db.String(255), nullable=True)
    notas = db.Column(db.Text, nullable=True)  # New column for cita notes
    psicologo_id = db.Column(db.Integer, db.ForeignKey('psicologos.id'), nullable=False)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)

    paciente = db.relationship('Paciente', backref='citas')
    psicologo = db.relationship('Psicologo', backref='citas')
    tipo_cita = db.relationship('TipoCita', backref='citas')

    def __repr__(self):
        return f'<Cita {self.id} - {self.fecha}>'

    def obtener_duracion(self):
        if self.tipo_cita:
            return self.tipo_cita.duracion_predeterminada
        duraciones_por_motivo = {
            'seguimiento': 30,
            'primera consulta': 90,
            'evaluación psicológica': 120,
            'intervención en crisis': 60,
            'terapia de pareja': 90,
            'terapia familiar': 90,
            'teleconsulta': 50,
            'sesión de cierre': 60,
        }
        motivo_normalizado = self.motivo.lower() if self.motivo else ""
        for key, duracion in duraciones_por_motivo.items():
            if key in motivo_normalizado:
                return duracion
        return 60

    def to_dict(self):
        from datetime import timedelta
        paciente = Paciente.query.get(self.paciente_id)
        tipo_cita_nombre = self.tipo_cita.nombre if self.tipo_cita else "No especificado"
        duracion = self.obtener_duracion()
        return {
            'id': self.id,
            'title': f"{paciente.nombre} {paciente.apellido}",
            'start': self.fecha.isoformat(),
            'end': (self.fecha + timedelta(minutes=duracion)).isoformat(),
            'paciente_id': self.paciente_id,
            'tipo_cita_id': self.tipo_cita_id,
            'tipo': tipo_cita_nombre,
            'duracion': duracion,
            'status': self.status,
            'className': f"cita-{self.status.lower()}",
            'color': self.tipo_cita.color if self.tipo_cita else "#4e73df"
        }
    


    


class Nota(db.Model):
    __tablename__ = 'notas'
    id = db.Column(db.Integer, primary_key=True)
    contenido = db.Column(db.Text)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    cita_id = db.Column(db.Integer, db.ForeignKey('citas.id'), nullable=True)  # Removed unique=True
    psicologo_id = db.Column(db.Integer, db.ForeignKey('psicologos.id'), nullable=False)
    
    paciente = db.relationship('Paciente', backref=db.backref('notas', lazy='dynamic'))
    psicologo = db.relationship('Psicologo', backref=db.backref('notas', lazy=True))
    cita = db.relationship('Cita', backref=db.backref('related_notas', lazy='dynamic'))  # Changed to support multiple notes

    def to_dict(self):
        return {
            'id': self.id,
            'contenido': self.contenido,
            'creado_en': self.creado_en.isoformat(),
            'actualizado_en': self.actualizado_en.isoformat(),
            'paciente_id': self.paciente_id,
            'cita_id': self.cita_id,
            'psicologo_id': self.psicologo_id
        }



class TipoCita(db.Model):
    __tablename__ = 'tipos_cita'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.Text, nullable=True)
    duracion_predeterminada = db.Column(db.Integer, default=60)  # Duración en minutos
    color = db.Column(db.String(20), default='#4e73df')  # Color para mostrar en el calendario
    activo = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<TipoCita {self.nombre}>'
    
    @classmethod
    def seed_default_types(cls, db_session):
        """Poblar la tabla con tipos de cita predeterminados"""
        default_types = [
            {'nombre': 'Consulta general', 'descripcion': 'Sesión terapéutica regular de seguimiento', 'duracion_predeterminada': 60, 'color': '#4e73df'},
            {'nombre': 'Primera consulta', 'descripcion': 'Evaluación inicial para pacientes nuevos', 'duracion_predeterminada': 90, 'color': '#1cc88a'},
            {'nombre': 'Evaluación psicológica', 'descripcion': 'Aplicación de tests o pruebas específicas', 'duracion_predeterminada': 120, 'color': '#f6c23e'},
            {'nombre': 'Intervención en crisis', 'descripcion': 'Atención urgente para situaciones críticas', 'duracion_predeterminada': 60, 'color': '#e74a3b'},
            {'nombre': 'Terapia de pareja', 'descripcion': 'Sesión de terapia con dos personas', 'duracion_predeterminada': 90, 'color': '#36b9cc'},
            {'nombre': 'Terapia familiar', 'descripcion': 'Sesión con todos los miembros de la familia', 'duracion_predeterminada': 90, 'color': '#6610f2'},
            {'nombre': 'Seguimiento', 'descripcion': 'Breve revisión de progreso', 'duracion_predeterminada': 30, 'color': '#fd7e14'},
            {'nombre': 'Teleconsulta', 'descripcion': 'Sesión por videollamada', 'duracion_predeterminada': 50, 'color': '#20c9a6'},
            {'nombre': 'Sesión de cierre', 'descripcion': 'Finalización del proceso terapéutico', 'duracion_predeterminada': 60, 'color': '#858796'},
        ]
        
        for type_data in default_types:
            tipo_cita = cls(**type_data)
            db_session.add(tipo_cita)
        
        db_session.commit()





# Tabla de relación para los tipos de citas que ofrece cada psicólogo
psicologo_tipo_cita = db.Table('psicologo_tipo_cita',
    db.Column('psicologo_id', db.Integer, db.ForeignKey('psicologos.id'), primary_key=True),
    db.Column('tipo_cita_id', db.Integer, db.ForeignKey('tipos_cita.id'), primary_key=True)
)





class Configuracion(db.Model):
    __tablename__ = 'configuraciones'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Configuración de notificaciones
    notificaciones_email = db.Column(db.Boolean, default=True)
    tiempo_anticipacion = db.Column(db.Integer, default=60)  # minutos
    frecuencia_recordatorios = db.Column(db.Integer, default=2)  # cantidad
    alertas_cambios_citas = db.Column(db.Boolean, default=True)
    alertas_pacientes_nuevos = db.Column(db.Boolean, default=True)
    notificaciones_actualizacion = db.Column(db.Boolean, default=True)
    sonidos_notificacion = db.Column(db.Boolean, default=False)
    
    # Configuración de seguridad
    retencion_datos = db.Column(db.Integer, default=5)  # años
    
    # Nuevo campo que indica si los recordatorios automáticos están habilitados
    recordatorios_automaticos = db.Column(db.Boolean, default=True)
    
    # Relación con el psicólogo
    psicologo_id = db.Column(db.Integer, db.ForeignKey('psicologos.id'), nullable=False)
    
    def get_tipos_cita(self):
        """Obtiene los tipos de cita disponibles para este psicólogo"""
        return self.psicologo.get_tipos_cita() if self.psicologo else TipoCita.query.filter_by(activo=True).all()
    
    def get_section_data(self, section):
        if section == 'notifications':
            return {
                'notificaciones_email': self.notificaciones_email,
                'tiempo_anticipacion': self.tiempo_anticipacion,
                'frecuencia_recordatorios': self.frecuencia_recordatorios,
                'alertas_cambios_citas': self.alertas_cambios_citas,
                'alertas_pacientes_nuevos': self.alertas_pacientes_nuevos,
                'notificaciones_actualizacion': self.notificaciones_actualizacion,
                'sonidos_notificacion': self.sonidos_notificacion,
                'recordatorios_automaticos': self.recordatorios_automaticos  # Agregar aquí
            }
        elif section == 'security':
            # Extraemos la información de seguridad del usuario asociado al psicólogo
            user_security = {}
            if self.psicologo and self.psicologo.usuario:
                user = self.psicologo.usuario
                user_security = {
                    'auth_dos_factores': user.auth_dos_factores,
                    'cierre_sesion_auto': user.cierre_sesion_auto,
                    'tiempo_inactividad': user.tiempo_inactividad
                }
            
            return {
                **user_security,
                'retencion_datos': self.retencion_datos
            }
        return {}
    
    def update_from_form(self, section, form_data):
        """Actualiza los datos del modelo desde un formulario según la sección"""
        if section == 'notifications':
            self.notificaciones_email = form_data.get('notificaciones_email', False) == 'true'
            self.tiempo_anticipacion = int(form_data.get('tiempo_anticipacion', self.tiempo_anticipacion))
            self.frecuencia_recordatorios = int(form_data.get('frecuencia_recordatorios', self.frecuencia_recordatorios))
            self.alertas_cambios_citas = form_data.get('alertas_cambios_citas', False) == 'true'
            self.alertas_pacientes_nuevos = form_data.get('alertas_pacientes_nuevos', False) == 'true'
            self.notificaciones_actualizacion = form_data.get('notificaciones_actualizacion', False) == 'true'
            self.sonidos_notificacion = form_data.get('sonidos_notificacion', False) == 'true'
            # Aquí debes actualizar el valor de recordatorios_automaticos
            self.recordatorios_automaticos = form_data.get('recordatorios_automaticos', False) == 'true'
        
        elif section == 'security':
            # Actualizar la información de seguridad en el usuario asociado
            if self.psicologo and self.psicologo.usuario:
                user = self.psicologo.usuario
                if 'auth_dos_factores' in form_data:
                    user.auth_dos_factores = form_data.get('auth_dos_factores', False) == 'true'
                if 'cierre_sesion_auto' in form_data:
                    user.cierre_sesion_auto = form_data.get('cierre_sesion_auto', False) == 'true'
                if 'tiempo_inactividad' in form_data:
                    user.tiempo_inactividad = int(form_data.get('tiempo_inactividad', user.tiempo_inactividad))
            
            # Actualizar la retención de datos en la configuración
            if 'retencion_datos' in form_data:
                self.retencion_datos = int(form_data.get('retencion_datos', self.retencion_datos))
    
    def __repr__(self):
        return f'<Configuracion Psicologo {self.psicologo_id}>'




class NotificacionSistema(db.Model):
    __tablename__ = 'notificaciones_sistema'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    titulo = db.Column(db.String(100), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # 'verificacion_psicologo', 'verificacion_aprobada', etc.
    referencia_id = db.Column(db.Integer, nullable=True)  # ID opcional para referencias (ej: ID del psicólogo)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    leida = db.Column(db.Boolean, default=False)
    
    # Relación con el usuario
    usuario = db.relationship('Usuario', backref=db.backref('notificaciones_sistema', lazy=True))
    
    def __repr__(self):
        return f'<NotificacionSistema {self.id} para usuario {self.usuario_id}>'
        
    @classmethod
    def crear_notificacion_verificacion(cls, db_session, usuario_id, tipo, referencia_id=None, titulo=None, mensaje=None):
        """
        Crea una notificación de sistema relacionada con verificación de psicólogos
        
        Args:
            db_session: Sesión de base de datos
            usuario_id: ID del usuario destinatario
            tipo: Tipo de notificación ('verificacion_psicologo', 'verificacion_aprobada', etc.)
            referencia_id: ID opcional de referencia (ej: ID del psicólogo)
            titulo: Título personalizado (opcional)
            mensaje: Mensaje personalizado (opcional)
        """
        # Títulos y mensajes predeterminados según el tipo
        titulos_default = {
            'verificacion_psicologo': 'Nuevo psicólogo pendiente de verificación',
            'verificacion_aprobada': '¡Tu cuenta ha sido verificada!',
            'verificacion_rechazada': 'Resultado de verificación',
            'verificacion_info_adicional': 'Se requiere información adicional'
        }
        
        mensajes_default = {
            'verificacion_psicologo': f'Un psicólogo ha solicitado verificación (ID: {referencia_id})',
            'verificacion_aprobada': 'Tu cuenta de psicólogo ha sido verificada y activada. Ya puedes comenzar a usar la plataforma.',
            'verificacion_rechazada': 'Tu solicitud de verificación como psicólogo ha sido rechazada.',
            'verificacion_info_adicional': 'Se requiere información adicional para verificar tu cuenta.'
        }
        
        # Usar valores predeterminados si no se proporcionan personalizados
        titulo_final = titulo or titulos_default.get(tipo, 'Notificación del sistema')
        mensaje_final = mensaje or mensajes_default.get(tipo, 'Notificación del sistema')
        
        # Crear la notificación
        notificacion = cls(
            usuario_id=usuario_id,
            titulo=titulo_final,
            mensaje=mensaje_final,
            tipo=tipo,
            referencia_id=referencia_id,
            fecha=datetime.utcnow(),
            leida=False
        )
        
        db_session.add(notificacion)
        
        # No hacer commit aquí para permitir transacciones más grandes
        
        return notificacion
        
    @classmethod
    def obtener_no_leidas(cls, usuario_id, tipo=None):
        """
        Obtiene las notificaciones no leídas para un usuario
        
        Args:
            usuario_id: ID del usuario
            tipo: Tipo de notificación para filtrar (opcional)
            
        Returns:
            Lista de notificaciones no leídas
        """
        query = cls.query.filter_by(usuario_id=usuario_id, leida=False)
        
        if tipo:
            query = query.filter_by(tipo=tipo)
            
        return query.order_by(cls.fecha.desc()).all()





class Notificacion(db.Model):
    __tablename__ = 'notificaciones'
    
    id = db.Column(db.Integer, primary_key=True)
    cita_id = db.Column(db.Integer, db.ForeignKey('citas.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    tiempo_envio = db.Column(db.DateTime, nullable=False)
    enviada = db.Column(db.Boolean, default=False)
    fecha_envio = db.Column(db.DateTime, nullable=True)
    destinatario = db.Column(db.String(20), nullable=False)
    contenido = db.Column(db.Text, nullable=True)
    prioridad = db.Column(db.String(10), default='normal')
    
    cita = db.relationship('Cita', backref=db.backref('notificaciones', lazy=True))
    
    def __repr__(self):
        return f'<Notificacion {self.id} para cita {self.cita_id}>'
    
    @classmethod
    def programar_recordatorios_cita(cls, db_session, cita, config=None):
        if not config:
            config = cita.psicologo.configuracion
        
        if not config or not config.recordatorios_automaticos:
            print("Recordatorios automáticos deshabilitados o sin configuración.")
            return
        
        db_session.query(cls).filter(cls.cita_id == cita.id).delete()
        
        tiempo_anticipacion = config.tiempo_anticipacion
        frecuencia = config.frecuencia_recordatorios
        
        tiempos_envio = []
        tiempos_envio.append(cita.fecha - timedelta(minutes=tiempo_anticipacion))
        if frecuencia > 1:
            tiempos_envio.append(cita.fecha.replace(hour=20, minute=0) - timedelta(days=1))
        if frecuencia > 2:
            tiempos_envio.append(cita.fecha - timedelta(minutes=15))
        
        for tiempo in tiempos_envio:
            print(f"Tiempo de envío calculado: {tiempo}, Tiempo actual: {datetime.now()}")
            if tiempo > datetime.now():
                if config.notificaciones_email:
                    print(f"Creando notificación para cita {cita.id} a {tiempo}")
                    notificacion = cls(
                        cita_id=cita.id,
                        tipo='email',
                        tiempo_envio=tiempo,
                        destinatario='paciente',
                        contenido=f"Recordatorio de su cita programada para {cita.fecha.strftime('%d/%m/%Y %H:%M')}"
                    )
                    db_session.add(notificacion)
        
        try:
            db_session.commit()
            print("Commit exitoso.")
        except Exception as e:
            db_session.rollback()
            print(f"Error al hacer commit: {str(e)}")

    @classmethod
    def notificar_cambio_cita(cls, db_session, cita, accion="modificada"):
        config = cita.psicologo.configuracion
        
        if not config or not config.alertas_cambios_citas:
            return
        
        notificacion_psicologo = cls(
            cita_id=cita.id,
            tipo='app',
            tiempo_envio=datetime.now(),
            destinatario='psicologo',
            contenido=f"La cita con {cita.paciente.nombre} {cita.paciente.apellido} ha sido {accion}.",
            prioridad='alta' if accion == "cancelada" else "normal"
        )
        db_session.add(notificacion_psicologo)
        
        if config.notificaciones_email and cita.paciente.usuario and cita.paciente.usuario.email:
            notificacion_paciente = cls(
                cita_id=cita.id,
                tipo='email',
                tiempo_envio=datetime.now(),
                destinatario='paciente',
                contenido=f"Su cita del {cita.fecha.strftime('%d/%m/%Y %H:%M')} ha sido {accion}."
            )
            db_session.add(notificacion_paciente)
        
        try:
            db_session.commit()
            print("Notificación de cambio de cita enviada exitosamente.")
        except Exception as e:
            db_session.rollback()
            print(f"Error al enviar notificación de cambio de cita: {str(e)}")
    
    @classmethod
    def obtener_pendientes(cls, db_session):
        ahora = datetime.now()
        return db_session.query(
            cls, 
            Cita, 
            Psicologo,
            Paciente
        ).join(
            Cita, cls.cita_id == Cita.id
        ).join(
            Psicologo, Cita.psicologo_id == Psicologo.id
        ).join(
            Paciente, Cita.paciente_id == Paciente.id
        ).filter(
            cls.enviada == False,
            cls.tiempo_envio <= ahora
        ).all()
    
    def marcar_como_enviada(self, db_session):
        self.enviada = True
        self.fecha_envio = datetime.now()
        db_session.commit()






class Contacto(db.Model):
    __tablename__ = 'contactos'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    telefono = db.Column(db.String(20), nullable=True)
    asunto = db.Column(db.String(100), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    fecha_envio = db.Column(db.DateTime, default=datetime.utcnow)
    leido = db.Column(db.Boolean, default=False)
    respondido = db.Column(db.Boolean, default=False)
    ip_remitente = db.Column(db.String(50), nullable=True)
    
    # Si quieres relacionarlo con un psicólogo (opcional)
    psicologo_id = db.Column(db.Integer, db.ForeignKey('psicologos.id'), nullable=True)
    psicologo = db.relationship('Psicologo', backref=db.backref('mensajes_contacto', lazy=True))
    
    def __repr__(self):
        return f'<Contacto {self.id} - {self.asunto}>'
    
    def to_dict(self):
        """Convierte el contacto a un diccionario para las respuestas JSON"""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'email': self.email,
            'telefono': self.telefono,
            'asunto': self.asunto,
            'mensaje': self.mensaje,
            'fecha_envio': self.fecha_envio.isoformat() if self.fecha_envio else None,
            'leido': self.leido,
            'respondido': self.respondido,
            'psicologo_id': self.psicologo_id
        }