# D:\GitHub\RegiSync\app\__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate # Now installed!
from flask_jwt_extended import JWTManager # Now installed!
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
    # This handler writes logs to a file, rotating it when it reaches 10KB
    file_handler = RotatingFileHandler('logs/regisync.log', maxBytes=10240,
                                       backupCount=10)
    # Define the log message format
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    # Set the logging level for the file handler
    file_handler.setLevel(logging.INFO)
    # Add the file handler to the app's logger
    app.logger.addHandler(file_handler)
    # Set the overall logging level for the app
    app.logger.setLevel(logging.INFO)

    with app.app_context():
        # Import models here to ensure they are registered with SQLAlchemy
        # This is crucial for db.create_all() to find and create all your database tables.
        from . import models 
        
        # Import and initialize services after app context is pushed
        # This ensures services that rely on app.config or db are initialized correctly.
        from app.routes import init_services
        init_services(app) # Pass the Flask app instance directly

        # Register blueprints
        # Blueprints organize your routes and views into modular components.
        from . import routes
        app.register_blueprint(routes.bp) 

        # Create database tables if they don't already exist
        # This will create tables for all models defined in app/models.py.
        db.create_all()

        # You can add custom error handlers here if needed.
        # Example: from app.utils.error_handlers import register_error_handlers
        # register_error_handlers(app)

    return app