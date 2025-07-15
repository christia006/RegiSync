-- database/init_db.sql

CREATE TABLE IF NOT EXISTS peserta (
    id VARCHAR(36) PRIMARY KEY,
    nama VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    nomor_telepon VARCHAR(20),
    status_pendaftaran VARCHAR(50) DEFAULT 'pending',
    status_kehadiran BOOLEAN DEFAULT FALSE,
    qr_code_data VARCHAR(255) UNIQUE,
    timestamp_registrasi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp_kehadiran TIMESTAMP,
    data_mentah_google_forms JSONB
);

CREATE TABLE IF NOT EXISTS admin (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'admin'
);

CREATE TABLE IF NOT EXISTS log_error (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message TEXT NOT NULL,
    level VARCHAR(20) DEFAULT 'ERROR',
    traceback TEXT
);

-- Contoh admin user (Anda akan membuatnya melalui API /admin/register setelah aplikasi berjalan)
-- INSERT INTO admin (username, password_hash, role) VALUES ('admin', 'hashed_password_here', 'super_admin') ON CONFLICT (username) DO NOTHING;