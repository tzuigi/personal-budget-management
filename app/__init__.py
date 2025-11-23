from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import logging
from logging.handlers import RotatingFileHandler

from config import Config

# instante globale ale extensiilor
# vor fi initializate in create_app

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
login_manager.login_message = 'Vă rugăm să vă autentificați pentru a accesa această pagină.'
login_manager.login_message_category = 'warning'

# Limiter pentru protecție împotriva atacurilor de tip brute-force
limiter = Limiter(key_func=get_remote_address)

from .models import User

@login_manager.user_loader
def load_user(user_id):
    # primeste id-ul (string) din sesiune si returneaza obiectul User
    return User.query.get(int(user_id))



def create_app(config_class=Config):
    """
    Functie care creeaza si configureaza aplicatia Flask.
    Initializeaza extensiile si inregistreaza rutele.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)    # initializare extensii cu aplicatia
    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    
    # Configurare logging
    if not app.debug and not app.testing:
        # Asigurare existență director logs
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # Configurare handler fișier de log
        file_handler = RotatingFileHandler('logs/budget_app.log', 
                                          maxBytes=10240, 
                                          backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Aplicația buget personal a pornit')
    
    # inregistrare blueprint pentru rute
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # Inregistrare custom error handlers
    from flask import render_template

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        # Este o practică bună să facem rollback la sesiune în caz de eroare 500
        # pentru a curăța orice tranzacții eșuate.
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app