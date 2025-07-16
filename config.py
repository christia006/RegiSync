# D:\GitHub\RegiSync\config.py
import os

# Mengambil variabel lingkungan untuk keamanan
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'super-secret-jwt-key'

    # Konfigurasi database yang baru
    DB_CONFIG = {
        "dbname": "neurosordb",
        "user": "neurosord_user",
        "password": "Sayabag",
        "host": "localhost",
        "port": "5432"
    }

    # Menggunakan DB_CONFIG untuk membuat SQLALCHEMY_DATABASE_URI
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
        f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Konfigurasi untuk email (tetap sama)
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.googlemail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['your-email@example.com']

    # Konfigurasi untuk batasan token
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES = 30 # Contoh: 30 menit
    JWT_REFRESH_TOKEN_EXPIRES_DAYS = 7    # Contoh: 7 hari