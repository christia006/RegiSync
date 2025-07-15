from werkzeug.security import generate_password_hash, check_password_hash
from app.models import Admin, db
import logging

logger = logging.getLogger(__name__)

class AuthService:
    def hash_password(self, password):
        return generate_password_hash(password)

    def check_password(self, hashed_password, password):
        return check_password_hash(hashed_password, password)

    def authenticate_admin(self, username, password):
        admin = Admin.query.filter_by(username=username).first()
        if admin and self.check_password(admin.password_hash, password):
            logger.info(f"Admin '{username}' authenticated successfully.")
            return admin
        logger.warning(f"Failed authentication attempt for admin '{username}'.")
        return None

    def create_admin(self, username, password, role='admin'):
        existing_admin = Admin.query.filter_by(username=username).first()
        if existing_admin:
            logger.warning(f"Attempt to create existing admin user: {username}")
            return None # User already exists
        
        hashed_password = self.hash_password(password)
        new_admin = Admin(username=username, password_hash=hashed_password, role=role)
        db.session.add(new_admin)
        db.session.commit()
        logger.info(f"Admin user '{username}' created successfully with role '{role}'.")
        return new_admin

    def get_admin_by_id(self, admin_id):
        return Admin.query.get(admin_id)