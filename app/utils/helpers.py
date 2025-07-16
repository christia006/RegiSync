# D:\GitHub\RegiSync\app\utils\helpers.py

from functools import wraps
import traceback
from datetime import datetime
from flask import request, jsonify, current_app 
import logging

# --- PERBAIKAN DI SINI ---
# Import model LogError di sini agar bisa diakses oleh fungsi log_error
from app.models import LogError
# --- AKHIR PERBAIKAN ---

logger = logging.getLogger(__name__)

def log_error(message, level='ERROR', tb=None):
    # Defer import of db to avoid RuntimeError when module is loaded
    # Kita tetap impor db di sini karena log_error bisa dipanggil di luar konteks request Flask
    from app.__init__ import db 
    try:
        error_entry = LogError(message=message, level=level, traceback=tb)
        db.session.add(error_entry)
        db.session.commit()
        # Menggunakan logger bawaan Flask untuk konsistensi
        current_app.logger.log(getattr(logging, level.upper()), message, exc_info=(tb is not None))
    except Exception as e:
        # Fallback logging to file if database logging fails
        logger.error(f"Failed to log error to database: {e}", exc_info=True)
        # Rollback here too, just in case the error was during the commit for LogError itself
        if 'db' in locals() and db.session.is_active: # Check if db is defined and session is active
            db.session.rollback()
        
        # Tambahkan fallback yang lebih jelas ke konsol
        print(f"\n--- CRITICAL FALLBACK LOGGING ERROR ---")
        print(f"Original message: {message}")
        print(f"Level: {level}")
        print(f"Error logging to DB: {e}")
        if tb:
            print("Original Traceback:\n", tb)
        print(f"--- END CRITICAL FALLBACK LOGGING ERROR ---\n")


def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Defer import of db to avoid RuntimeError when module is loaded
        from app.__init__ import db 
        try:
            return f(*args, **kwargs)
        except Exception as e:
            tb_str = traceback.format_exc()
            log_error(f"Error in API endpoint {request.path}: {str(e)}", level="ERROR", tb=tb_str)
            
            # Rollback any pending transaction in case of an error
            if db.session.is_active:
                db.session.rollback()
            
            response_data = {
                "message": "An internal server error occurred.", 
                "error": str(e)
            }
            if current_app.debug: # Only show traceback in debug mode
                response_data["traceback"] = tb_str
            
            return jsonify(response_data), 500
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