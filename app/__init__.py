from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from app.utils.error_handlers import register_error_handlers # Import error handler

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        # Import models here to ensure they are registered with SQLAlchemy
        from . import models
        
        # Import and initialize services after app context is pushed
        from app.routes import init_services
        init_services(app)

        # Register blueprints or routes
        from . import routes
        app.register_blueprint(routes.bp) # Menggunakan Blueprint

        # Create database tables if they don't exist
        db.create_all()

        # Register custom error handlers
        register_error_handlers(app)

    return app