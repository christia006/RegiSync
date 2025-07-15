from app.models import LogError, db
from functools import wraps
import traceback
from datetime import datetime
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)

def log_error(message, level='ERROR', tb=None):
    try:
        error_entry = LogError(message=message, level=level, traceback=tb)
        db.session.add(error_entry)
        db.session.commit()
        logger.log(getattr(logging, level.upper()), message, exc_info=(tb is not None))
    except Exception as e:
        logger.error(f"Failed to log error to database: {e}", exc_info=True)
        # Fallback to console logging if DB logging fails
        logging.error(f"Fallback: {message}", exc_info=True)


def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            tb_str = traceback.format_exc()
            log_error(f"Error in API endpoint {request.path}: {str(e)}", level="ERROR", tb=tb_str)
            # Rollback any pending transaction in case of an error
            if db.session.is_active:
                db.session.rollback()
            return jsonify({"message": "An internal server error occurred.", "error": str(e), "traceback": tb_str if current_app.debug else None}), 500
    return decorated_function

def generate_confirmation_message(peserta, qr_code_url=None):
    message = f"""
    <html>
    <body>
        <p>Halo <strong>{peserta.nama}</strong>,</p>
        <p>Terima kasih telah mendaftar di acara kami!</p>
        <p><strong>Detail Pendaftaran Anda:</strong></p>
        <ul>
            <li>Nama: {peserta.nama}</li>
            <li>Email: {peserta.email}</li>
            <li>Status Pendaftaran: <strong>{peserta.status_pendaftaran.capitalize()}</strong></li>
        </ul>
    """
    if peserta.status_pendaftaran == 'registered' and qr_code_url:
        message += f"""
        <p>Untuk absensi di lokasi, silakan gunakan QR Code berikut:</p>
        <p><img src="{qr_code_url}" alt="QR Code Absensi" width="200"></p>
        <p>Atau akses langsung di: <a href="{qr_code_url}">{qr_code_url}</a></p>
        <p>Kami tunggu kehadiran Anda!</p>
        """
    elif peserta.status_pendaftaran == 'pending':
        message += """
        <p>Pendaftaran Anda sedang kami tinjau. Kami akan mengirimkan konfirmasi lebih lanjut setelah disetujui.</p>
        """
    message += """
        <p>Salam Hormat,<br>Tim RegiSync</p>
    </body>
    </html>
    """
    return message