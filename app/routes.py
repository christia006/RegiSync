from flask import Blueprint, request, jsonify, current_app, send_file, url_for
from app.__init__ import db
from app.models import Peserta, Admin, LogError
from app.services.google_forms_service import GoogleFormsService
from app.services.email_sms_service import EmailSMSService
from app.services.qr_code_service import QRCodeService
from app.services.auth_service import AuthService
from app.utils.helpers import log_error, handle_errors, generate_confirmation_message
from datetime import datetime
from sqlalchemy import or_
import base64
import io
import logging
import traceback

logger = logging.getLogger(__name__)

# Buat Blueprint
bp = Blueprint('api', __name__)

# Inisialisasi services sebagai variabel global (akan di-set oleh init_services)
google_forms_service = None
email_sms_service = None
qr_code_service = QRCodeService()
auth_service = AuthService()

def init_services(app):
    """
    Inisialisasi services yang membutuhkan app context atau konfigurasi.
    Dipanggil dari app/__init__.py
    """
    global google_forms_service, email_sms_service
    # Pastikan services hanya diinisialisasi sekali
    if google_forms_service is None:
        google_forms_service = GoogleFormsService(
            app.config['GOOGLE_CLIENT_SECRET_FILE'],
            app.config['GOOGLE_SPREADSHEET_ID'],
            app.config['GOOGLE_SCOPES']
        )
        logger.info("GoogleFormsService initialized.")
    
    if email_sms_service is None:
        email_sms_service = EmailSMSService(app.config)
        logger.info("EmailSMSService initialized.")


# Dekorator untuk otentikasi admin (Basic Auth sederhana)
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Basic '):
            log_error("Unauthorized access attempt: Missing or invalid Authorization header.", level="WARNING")
            return jsonify({"message": "Authorization required"}), 401
        
        encoded_creds = auth_header.split(' ')[1]
        try:
            decoded_creds = base64.b64decode(encoded_creds).decode('utf-8')
            username, password = decoded_creds.split(':', 1)
        except Exception as e:
            log_error(f"Invalid Authorization header format: {e}", level="WARNING")
            return jsonify({"message": "Invalid authorization header format"}), 401

        admin = auth_service.authenticate_admin(username, password)
        if not admin:
            log_error(f"Unauthorized access attempt: Invalid credentials for user '{username}'.", level="WARNING")
            return jsonify({"message": "Invalid credentials"}), 401
        
        request.admin = admin # Menyimpan objek admin di request context
        return f(*args, **kwargs)
    return decorated_function


# Route untuk admin login
@bp.route('/admin/login', methods=['POST'])
@handle_errors
def admin_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400

    admin = auth_service.authenticate_admin(username, password)
    if admin:
        return jsonify({"message": "Login successful", "username": admin.username, "role": admin.role}), 200
    return jsonify({"message": "Invalid username or password"}), 401

# Route untuk membuat admin baru (gunakan ini untuk setup awal)
@bp.route('/admin/register', methods=['POST'])
@handle_errors
def admin_register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'admin')

    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400

    admin = auth_service.create_admin(username, password, role)
    if admin:
        return jsonify({"message": "Admin user created successfully"}), 201
    return jsonify({"message": "Admin user already exists"}), 409

# Sync data dari Google Forms
@bp.route('/sync-google-forms', methods=['POST'])
@admin_required
@handle_errors
def sync_google_forms():
    if not google_forms_service:
        log_error("Google Forms Service not initialized.", level="CRITICAL")
        return jsonify({"message": "Server error: Google Forms Service not ready."}), 500

    sheet_data = google_forms_service.get_form_responses()
    if not sheet_data or len(sheet_data) < 2: # Minimal 1 header + 1 baris data
        log_error("No new data or insufficient data found in Google Sheet.", level="INFO")
        return jsonify({"message": "No new data to sync or sheet is empty."}), 200

    # Asumsi baris pertama adalah header
    headers = [h.strip() for h in sheet_data[0]] # Hapus spasi di header
    data_rows = sheet_data[1:]

    synced_count = 0
    updated_count = 0
    error_count = 0
    
    for row_index, row in enumerate(data_rows):
        # Mulai transaksi per baris agar bisa rollback per baris
        # Note: Flask-SQLAlchemy handles transactions automatically per request by default.
        # For granular control or partial commits, explicit transaction management is needed.
        # Here, we will just try to process each and log failures.
        try:
            # Pastikan row memiliki cukup kolom. Sesuaikan indeks ini dengan Google Form Anda.
            # Contoh: Timestamp (0), Nama (1), Email (2), Nomor Telepon (3)
            if len(row) < 3: 
                log_error(f"Row {row_index+2} has insufficient columns: {row}. Skipping.", level="WARNING")
                error_count += 1
                continue

            timestamp_str = row[0]
            nama = row[1]
            email = row[2]
            nomor_telepon = row[3] if len(row) > 3 else None

            # Konversi timestamp
            try:
                # Coba beberapa format, sesuaikan dengan output Google Forms Anda
                # Contoh format: '7/15/2025 15:30:00', 'YYYY-MM-DD HH:MM:SS'
                timestamp_registrasi = datetime.strptime(timestamp_str, '%m/%d/%Y %H:%M:%S')
            except ValueError:
                try:
                    timestamp_registrasi = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    log_error(f"Invalid timestamp format for row {row_index+2}: '{timestamp_str}'. Skipping.", level="WARNING")
                    error_count += 1
                    continue

            # Cek apakah peserta sudah ada berdasarkan email
            existing_peserta = Peserta.query.filter_by(email=email).first()

            row_dict = dict(zip(headers, row)) # Simpan data mentah sebagai JSON

            if existing_peserta:
                # Update data jika ada perubahan signifikan
                if (existing_peserta.nama != nama or
                    existing_peserta.nomor_telepon != nomor_telepon or
                    existing_peserta.data_mentah_google_forms != row_dict):
                    
                    existing_peserta.nama = nama
                    existing_peserta.nomor_telepon = nomor_telepon
                    existing_peserta.data_mentah_google_forms = row_dict
                    db.session.add(existing_peserta)
                    db.session.commit() # Commit setiap update/insert
                    updated_count += 1
                    logger.info(f"Peserta '{email}' updated.")
                else:
                    logger.info(f"Peserta '{email}' already exists and no significant changes found.")
                    synced_count += 1 # Hitung sebagai synced meski tidak diupdate
            else:
                new_peserta = Peserta(
                    nama=nama,
                    email=email,
                    nomor_telepon=nomor_telepon,
                    status_pendaftaran='registered', # Otomatis registered setelah sync
                    data_mentah_google_forms=row_dict
                )
                db.session.add(new_peserta)
                db.session.flush() # Dapatkan ID sebelum commit untuk QR Code

                # Generate QR Code dan simpan data QR ke database
                qr_data = str(new_peserta.id) # Gunakan ID peserta sebagai data QR
                qr_code_bytes = qr_code_service.generate_qr_code(qr_data)
                new_peserta.qr_code_data = qr_data
                db.session.add(new_peserta) # Add kembali jika ada perubahan pada new_peserta
                db.session.commit() # Commit setiap update/insert

                # Kirim konfirmasi email/SMS
                if email_sms_service:
                    qr_code_url = url_for('api.get_peserta_qr_code', peserta_id=new_peserta.id, _external=True)
                    email_body = generate_confirmation_message(new_peserta, qr_code_url)
                    email_sms_service.send_email(new_peserta.email, "Konfirmasi Pendaftaran RegiSync", email_body)
                    if new_peserta.nomor_telepon:
                        sms_message = f"Halo {new_peserta.nama}, pendaftaran Anda di RegiSync telah dikonfirmasi! QR Code Anda: {qr_code_url}"
                        email_sms_service.send_sms(new_peserta.nomor_telepon, sms_message)
                
                synced_count += 1
                logger.info(f"New Peserta '{email}' added and confirmed.")

        except Exception as e:
            # Rollback transaksi database jika ada kesalahan
            db.session.rollback() 
            log_error(f"Failed to process row {row_index+2} from Google Sheet: {row}. Error: {str(e)}", level="ERROR", tb=traceback.format_exc())
            error_count += 1
            # Lanjutkan ke baris berikutnya, jangan berhenti total jika hanya satu baris yang error
            continue # Lanjut ke baris berikutnya jika ada kesalahan di satu baris

    return jsonify({"message": "Data sync completed.", "new_registrations": synced_count, "updated_registrations": updated_count, "errors": error_count}), 200


# Otentikasi Peserta (cek status pendaftaran & kehadiran)
@bp.route('/peserta/authenticate', methods=['POST'])
@handle_errors
def authenticate_peserta():
    data = request.get_json()
    email = data.get('email')
    qr_data = data.get('qr_data') # Bisa juga pakai QR data yang discan

    peserta = None
    if email:
        peserta = Peserta.query.filter_by(email=email).first()
    elif qr_data:
        peserta = Peserta.query.filter_by(qr_code_data=qr_data).first()
    
    if peserta:
        return jsonify({
            "message": "Authentication successful",
            "id": peserta.id,
            "nama": peserta.nama,
            "email": peserta.email,
            "status_pendaftaran": peserta.status_pendaftaran,
            "status_kehadiran": peserta.status_kehadiran,
            "timestamp_kehadiran": peserta.timestamp_kehadiran.isoformat() if peserta.timestamp_kehadiran else None
        }), 200
    return jsonify({"message": "Peserta not found or invalid credentials"}), 404

# Absensi Peserta via QR Code
@bp.route('/peserta/check-in', methods=['POST'])
@admin_required # Hanya admin yang bisa melakukan check-in
@handle_errors
def check_in_peserta():
    data = request.get_json()
    qr_data = data.get('qr_data') # Data yang discan dari QR code

    if not qr_data:
        return jsonify({"message": "QR data is required"}), 400

    peserta = Peserta.query.filter_by(qr_code_data=qr_data).first()

    if peserta:
        if peserta.status_pendaftaran == 'registered':
            if not peserta.status_kehadiran:
                peserta.status_kehadiran = True
                peserta.timestamp_kehadiran = datetime.utcnow()
                db.session.commit()
                logger.info(f"Peserta '{peserta.email}' checked in.")
                return jsonify({
                    "message": "Check-in successful",
                    "id": peserta.id,
                    "nama": peserta.nama,
                    "status_kehadiran": peserta.status_kehadiran,
                    "timestamp_kehadiran": peserta.timestamp_kehadiran.isoformat()
                }), 200
            else:
                return jsonify({"message": "Peserta already checked in", "id": peserta.id}), 409
        else:
            return jsonify({"message": "Peserta is not registered. Status: " + peserta.status_pendaftaran}), 403
    return jsonify({"message": "Peserta not found or invalid QR data"}), 404

# Dashboard Admin: Get All Peserta
@bp.route('/admin/peserta', methods=['GET'])
@admin_required
@handle_errors
def get_all_peserta():
    search_query = request.args.get('search', '').strip()
    status_pendaftaran = request.args.get('status_pendaftaran', '').strip().lower()
    status_kehadiran = request.args.get('status_kehadiran', '').strip().lower()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    query = Peserta.query

    if search_query:
        query = query.filter(or_(
            Peserta.nama.ilike(f'%{search_query}%'),
            Peserta.email.ilike(f'%{search_query}%'),
            Peserta.nomor_telepon.ilike(f'%{search_query}%')
        ))
    if status_pendaftaran:
        query = query.filter_by(status_pendaftaran=status_pendaftaran)
    if status_kehadiran:
        query = query.filter_by(status_kehadiran=(status_kehadiran == 'true'))

    paginated_pesertas = query.paginate(page=page, per_page=per_page, error_out=False)
    
    result = []
    for p in paginated_pesertas.items:
        result.append({
            "id": p.id,
            "nama": p.nama,
            "email": p.email,
            "nomor_telepon": p.nomor_telepon,
            "status_pendaftaran": p.status_pendaftaran,
            "status_kehadiran": p.status_kehadiran,
            "timestamp_registrasi": p.timestamp_registrasi.isoformat(),
            "timestamp_kehadiran": p.timestamp_kehadiran.isoformat() if p.timestamp_kehadiran else None,
            "qr_code_data": p.qr_code_data
        })
    
    return jsonify({
        "data": result,
        "total": paginated_pesertas.total,
        "page": paginated_pesertas.page,
        "per_page": paginated_pesertas.per_page,
        "pages": paginated_pesertas.pages
    }), 200

# Dashboard Admin: Get Peserta by ID
@bp.route('/admin/peserta/<peserta_id>', methods=['GET'])
@admin_required
@handle_errors
def get_peserta_by_id(peserta_id):
    peserta = Peserta.query.get(peserta_id)
    if peserta:
        return jsonify({
            "id": peserta.id,
            "nama": peserta.nama,
            "email": peserta.email,
            "nomor_telepon": peserta.nomor_telepon,
            "status_pendaftaran": peserta.status_pendaftaran,
            "status_kehadiran": peserta.status_kehadiran,
            "timestamp_registrasi": peserta.timestamp_registrasi.isoformat(),
            "timestamp_kehadiran": peserta.timestamp_kehadiran.isoformat() if peserta.timestamp_kehadiran else None,
            "qr_code_data": peserta.qr_code_data,
            "data_mentah_google_forms": peserta.data_mentah_google_forms
        }), 200
    return jsonify({"message": "Peserta not found"}), 404

# Dashboard Admin: Edit Peserta Data
@bp.route('/admin/peserta/<peserta_id>', methods=['PUT'])
@admin_required
@handle_errors
def edit_peserta_data(peserta_id):
    peserta = Peserta.query.get(peserta_id)
    if not peserta:
        return jsonify({"message": "Peserta not found"}), 404
    
    data = request.get_json()
    peserta.nama = data.get('nama', peserta.nama)
    peserta.email = data.get('email', peserta.email) # Hati-hati mengubah email jika itu unique key
    peserta.nomor_telepon = data.get('nomor_telepon', peserta.nomor_telepon)
    peserta.status_pendaftaran = data.get('status_pendaftaran', peserta.status_pendaftaran)
    peserta.status_kehadiran = data.get('status_kehadiran', peserta.status_kehadiran)

    try:
        db.session.commit()
        logger.info(f"Peserta '{peserta_id}' data updated by admin.")
        return jsonify({"message": "Peserta data updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        log_error(f"Failed to update peserta '{peserta_id}': {e}", tb=traceback.format_exc())
        return jsonify({"message": "Failed to update peserta data", "error": str(e)}), 500

# Dashboard Admin: Approval Peserta (mengubah status_pendaftaran)
@bp.route('/admin/peserta/<peserta_id>/approve', methods=['POST'])
@admin_required
@handle_errors
def approve_peserta(peserta_id):
    peserta = Peserta.query.get(peserta_id)
    if not peserta:
        return jsonify({"message": "Peserta not found"}), 404
    
    if peserta.status_pendaftaran != 'registered':
        peserta.status_pendaftaran = 'registered'
        # Regenerate QR code jika status berubah dan belum ada
        if not peserta.qr_code_data:
            qr_data = str(peserta.id)
            qr_code_bytes = qr_code_service.generate_qr_code(qr_data)
            peserta.qr_code_data = qr_data
            logger.info(f"QR code generated for approved peserta '{peserta.id}'.")
            
        try:
            db.session.commit()
            logger.info(f"Peserta '{peserta_id}' approved by admin.")

            # Kirim konfirmasi email/SMS setelah approval
            if email_sms_service:
                qr_code_url = url_for('api.get_peserta_qr_code', peserta_id=peserta.id, _external=True)
                email_body = generate_confirmation_message(peserta, qr_code_url)
                email_sms_service.send_email(peserta.email, "Pendaftaran RegiSync Anda Dikonfirmasi!", email_body)
                if peserta.nomor_telepon:
                    sms_message = f"Halo {peserta.nama}, pendaftaran Anda di RegiSync telah dikonfirmasi! QR Code Anda: {qr_code_url}"
                    email_sms_service.send_sms(peserta.nomor_telepon, sms_message)
            
            return jsonify({"message": "Peserta approved successfully", "status_pendaftaran": peserta.status_pendaftaran}), 200
        except Exception as e:
            db.session.rollback()
            log_error(f"Failed to approve peserta '{peserta_id}': {e}", tb=traceback.format_exc())
            return jsonify({"message": "Failed to approve peserta", "error": str(e)}), 500
    return jsonify({"message": "Peserta already registered"}), 409

# Dashboard Admin: Delete Peserta
@bp.route('/admin/peserta/<peserta_id>', methods=['DELETE'])
@admin_required
@handle_errors
def delete_peserta(peserta_id):
    peserta = Peserta.query.get(peserta_id)
    if not peserta:
        return jsonify({"message": "Peserta not found"}), 404
    
    try:
        db.session.delete(peserta)
        db.session.commit()
        logger.info(f"Peserta '{peserta_id}' deleted by admin.")
        return jsonify({"message": "Peserta deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        log_error(f"Failed to delete peserta '{peserta_id}': {e}", tb=traceback.format_exc())
        return jsonify({"message": "Failed to delete peserta", "error": str(e)}), 500

# Export Data CSV
@bp.route('/admin/export-data', methods=['GET'])
@admin_required
@handle_errors
def export_data():
    search_query = request.args.get('search', '').strip()
    status_pendaftaran = request.args.get('status_pendaftaran', '').strip().lower()
    status_kehadiran = request.args.get('status_kehadiran', '').strip().lower()

    query = Peserta.query

    if search_query:
        query = query.filter(or_(
            Peserta.nama.ilike(f'%{search_query}%'),
            Peserta.email.ilike(f'%{search_query}%'),
            Peserta.nomor_telepon.ilike(f'%{search_query}%')
        ))
    if status_pendaftaran:
        query = query.filter_by(status_pendaftaran=status_pendaftaran)
    if status_kehadiran:
        query = query.filter_by(status_kehadiran=(status_kehadiran == 'true'))

    pesertas = query.all()

    # Buat CSV string
    csv_lines = [
        "ID,Nama,Email,Nomor Telepon,Status Pendaftaran,Status Kehadiran,Timestamp Registrasi,Timestamp Kehadiran,QR Code Data"
    ]
    for p in pesertas:
        csv_lines.append(
            f'"{p.id}","{p.nama}","{p.email}","{p.nomor_telepon or ""}","{p.status_pendaftaran}",'
            f'"{p.status_kehadiran}","{p.timestamp_registrasi.isoformat()}",'
            f'"{p.timestamp_kehadiran.isoformat() if p.timestamp_kehadiran else ""}","{p.qr_code_data or ""}"'
        )
    csv_data = "\n".join(csv_lines)

    logger.info("Exporting participant data to CSV.")
    # Kirim sebagai file CSV
    response = current_app.response_class(
        csv_data,
        mimetype='text/csv',
        headers={"Content-disposition": "attachment; filename=regisync_data.csv"}
    )
    return response

# Log Error Dashboard
@bp.route('/admin/error-logs', methods=['GET'])
@admin_required
@handle_errors
def get_error_logs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    logs_paginated = LogError.query.order_by(LogError.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    result = []
    for log in logs_paginated.items:
        result.append({
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "message": log.message,
            "level": log.level,
            "traceback": log.traceback
        })
    return jsonify({
        "data": result,
        "total": logs_paginated.total,
        "page": logs_paginated.page,
        "per_page": logs_paginated.per_page,
        "pages": logs_paginated.pages
    }), 200

# Endpoint untuk mendapatkan QR code sebagai gambar
@bp.route('/peserta/<peserta_id>/qr', methods=['GET'])
@handle_errors
def get_peserta_qr_code(peserta_id):
    peserta = Peserta.query.get(peserta_id)
    if not peserta or not peserta.qr_code_data:
        logger.warning(f"QR code not found for participant ID: {peserta_id}")
        return jsonify({"message": "QR code not found for this participant"}), 404
    
    qr_code_bytes = qr_code_service.generate_qr_code(peserta.qr_code_data)
    
    if qr_code_bytes is None:
        return jsonify({"message": "Failed to generate QR code image"}), 500

    logger.info(f"Serving QR code for participant ID: {peserta_id}")
    return send_file(
        io.BytesIO(qr_code_bytes),
        mimetype='image/png',
        as_attachment=False,
        download_name=f"qr_code_{peserta_id}.png"
    )