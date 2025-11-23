import os

class Config:
    # cheia pentru semnarea cookie-urilor si CSRF
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'eLKJqj2llXC1hSt09s22v5-p2Ih8LXU7VMOCtdLHSpE'

    # calea catre baza de date SQLite
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL') or 
        'sqlite:///' + os.path.join(BASE_DIR, 'budget.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # configurare flask-login
    LOGIN_VIEW = 'main.login'
    LOGIN_MESSAGE = 'Autentificare necesara pentru acces'
    
    # Configurare AWS
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    S3_BUCKET = os.environ.get('S3_BUCKET')
    
    # Configurare pentru logare
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    
    # Configurare pentru deployment
    ENVIRONMENT = os.environ.get('FLASK_ENV') or 'development'
    DEBUG = ENVIRONMENT == 'development'
    
    # Configurare pentru exporturi
    EXPORT_FOLDER = os.path.join(BASE_DIR, 'exports')
    if not os.path.exists(EXPORT_FOLDER):
        os.makedirs(EXPORT_FOLDER)

    # Adăugare limită pentru dimensiunea fișierelor încărcate (ex: 16MB)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # Configurații Flask-Limiter (opțional, dar bun pentru producție)
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'memory://' # Folosește Redis dacă e disponibil
    RATELIMIT_STRATEGY = 'fixed-window' # sau 'moving-window'
    RATELIMIT_DEFAULT = '200 per day;50 per hour'