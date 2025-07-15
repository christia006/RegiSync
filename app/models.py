from app.__init__ import db # Sesuaikan import
from datetime import datetime
import uuid

class Peserta(db.Model):
    __tablename__ = 'peserta'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nama = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    nomor_telepon = db.Column(db.String(20), nullable=True)
    status_pendaftaran = db.Column(db.String(50), default='pending') # registered, pending, rejected
    status_kehadiran = db.Column(db.Boolean, default=False)
    qr_code_data = db.Column(db.String(255), unique=True, nullable=True) # Data untuk QR code, bisa berupa ID peserta
    timestamp_registrasi = db.Column(db.DateTime, default=datetime.utcnow)
    timestamp_kehadiran = db.Column(db.DateTime, nullable=True)
    data_mentah_google_forms = db.Column(db.JSON, nullable=True)

    def __repr__(self):
        return f'<Peserta {self.nama} ({self.email})>'

class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False) # Store hashed password
    role = db.Column(db.String(50), default='admin') # admin, super_admin

    def __repr__(self):
        return f'<Admin {self.username}>'

class LogError(db.Model):
    __tablename__ = 'log_error'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    message = db.Column(db.Text, nullable=False)
    level = db.Column(db.String(20), default='ERROR') # INFO, WARNING, ERROR, CRITICAL
    traceback = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<LogError {self.timestamp} - {self.message[:50]}>'