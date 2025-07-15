import os
from dotenv import load_dotenv

load_dotenv() 

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key_if_not_set')

 
    DB_CONFIG = {
        "dbname": "neurosordb",
        "user": "neurosord_user",
        "password": "Sayabag",
        "host": "localhost",
        "port": "5432"
    }
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
        f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

  
    GOOGLE_CLIENT_SECRET_FILE = os.getenv('GOOGLE_CLIENT_SECRET_FILE')
    GOOGLE_SPREADSHEET_ID = os.getenv('GOOGLE_SPREADSHEET_ID')
  
    GOOGLE_SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/forms.responses.readonly'
    ]

    # Email Settings
    EMAIL_HOST = os.getenv('EMAIL_HOST')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')

    # Twilio SMS Settings
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')