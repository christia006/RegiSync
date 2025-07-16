from werkzeug.security import generate_password_hash, check_password_hash
import logging
import traceback
from app.utils.helpers import log_error 
from flask import current_app # <<< TAMBAHKAN INI UNTUK MENGAKSES KONTEKS APLIKASI

logger = logging.getLogger(__name__)

class AuthService:
    # --- PERBAIKAN DI SINI ---
    def __init__(self): # <<< HAPUS db_instance DARI KONSTRUKTOR
        pass # Tidak ada inisialisasi spesifik di sini

    @property # <<< Ini adalah properti yang akan mengembalikan instance db yang terikat konteks
    def db(self):
        # Mengakses instance SQLAlchemy melalui ekstensi current_app
        # Ini memastikan kita selalu menggunakan instance db yang terikat dengan konteks aplikasi Flask yang aktif
        return current_app.extensions['sqlalchemy']
    # --- AKHIR PERBAIKAN ---

    def hash_password(self, password):
        return generate_password_hash(password)

    def check_password(self, hashed_password, password):
        return check_password_hash(hashed_password, password)

    def authenticate_admin(self, username, password):
        from app.models import Admin # <<< Tetap impor model di dalam method
        
        # Gunakan self.db.session untuk query
        admin = self.db.session.query(Admin).filter_by(username=username).first()
        if admin and self.check_password(admin.password_hash, password):
            logger.info(f"Admin '{username}' authenticated successfully.")
            return admin
        logger.warning(f"Failed authentication attempt for admin '{username}'.")
        return None

    def create_admin(self, username, password, role='admin'):
        from app.models import Admin # <<< Tetap impor model di dalam method
        
        try:
            # Gunakan self.db untuk query dan session
            existing_admin = self.db.session.query(Admin).filter_by(username=username).first()
            if existing_admin:
                logger.warning(f"Attempt to create existing admin user: {username}")
                return None 
            
            hashed_password = self.hash_password(password)
            new_admin = Admin(username=username, password_hash=hashed_password, role=role)
            self.db.session.add(new_admin) # <<< Gunakan self.db.session
            self.db.session.commit()      # <<< Gunakan self.db.session
            logger.info(f"Admin user '{username}' created successfully with role '{role}'.")
            return new_admin
        except Exception as e:
            self.db.session.rollback() # <<< Gunakan self.db.session
            log_error(f"Error creating admin: {e}", tb=traceback.format_exc())
            return None

    def get_admin_by_id(self, admin_id):
        from app.models import Admin # <<< Tetap impor model di dalam method
        # Gunakan self.db.session untuk query
        return self.db.session.query(Admin).get(admin_id)