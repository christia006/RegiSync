# D:\GitHub\RegiSync\app\__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate 
from flask_jwt_extended import JWTManager 
from config import Config
import logging
from logging.handlers import RotatingFileHandler
import os

db = SQLAlchemy() 
migrate = Migrate() 
jwt = JWTManager() 

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app) 
    migrate.init_app(app, db) 
    jwt.init_app(app) 

    # Configure logging for the application
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/regisync.log', maxBytes=10240,
                                       backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)

    with app.app_context():
        from . import models # Pastikan model diimpor di sini agar Alembic menemukannya
        
        from app.routes import init_services
        init_services(app) 
        
        from . import routes
        app.register_blueprint(routes.bp) 

        # --- PERBAIKAN DI SINI ---
        # HAPUS BARIS INI: db.create_all()
        # db.create_all() # <<< HAPUS BARIS INI!
        # --- AKHIR PERBAIKAN ---

        # from app.utils.error_handlers import register_error_handlers
        # register_error_handlers(app)

    return app