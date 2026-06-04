from flask import Flask, render_template
from flask_mail import Mail
from app.config import Config
from app.database import db, login_manager, migrate, TipoCita
from app.database import Notificacion, NotificacionSistema  # Asegúrate de importar NotificacionSistema
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import inspect

# Inicializar Mail
mail = Mail()

# Función para obtener notificaciones no leídas
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

def create_app(config_class=Config):
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config_class)
    
    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    login_manager.init_app(app)
    
    # Configurar login
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Por favor inicie sesión para acceder a esta página'
    login_manager.login_message_category = 'warning'
    
    
    # Registrar context processor para funciones de utilidad
    @app.context_processor
    def utility_functions():  # noqa: F811
        """Esta función es utilizada por Flask para proveer funciones a las plantillas."""
        return dict(get_notificaciones_no_leidas=get_notificaciones_no_leidas)
        
    # Verificar si las tablas existen antes de consultar
    with app.app_context():
        try:
            # Verificar la existencia de tablas, y inicializar tipos de citas si es necesario
            inspector = inspect(db.engine)
            if 'tipos_cita' in inspector.get_table_names():
                if TipoCita.query.count() == 0:
                    TipoCita.seed_default_types(db.session)
                    print("Tipos de cita inicializados correctamente.")
            else:
                print("La tabla 'tipos_cita' no existe todavía.")
        except Exception as e:
            print(f"Error al verificar tipos de cita: {e}")
            # Continuar con la inicialización aún si hay error


    # Registrar rutas
    from app.routes import main as main_routes
    app.register_blueprint(main_routes)

    # Registrar blueprint de API de estadísticas
    from app.stats_api import stats_api
    app.register_blueprint(stats_api, url_prefix='/api')

    # Configurar manejador de errores
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('index.html'), 404
    
    return app