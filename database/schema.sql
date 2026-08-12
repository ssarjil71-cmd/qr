-- Database: qr_card
CREATE DATABASE IF NOT EXISTS qr_card CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE qr_card;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_type ENUM('student','employee','emergency','admin') NOT NULL DEFAULT 'student',
  name VARCHAR(255) NOT NULL,
  mobile VARCHAR(50),
  email VARCHAR(255),
  password_hash VARCHAR(255) NOT NULL,
  photo VARCHAR(255),
  education TEXT,
  skills TEXT,
  resume VARCHAR(255),
  certificates TEXT,
  company_name VARCHAR(255),
  designation VARCHAR(255),
  experience VARCHAR(255),
  emergency_contact VARCHAR(255),
  blood_group VARCHAR(20),
  medical_notes TEXT,
  address TEXT,
  vehicle_number VARCHAR(100),
  qr_token VARCHAR(255) UNIQUE,
  qr_path VARCHAR(255),
  is_active TINYINT DEFAULT 1,
  reset_token VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  emergency_primary_contact_name VARCHAR(255),
  emergency_primary_contact_relation VARCHAR(100),
  emergency_primary_contact_mobile VARCHAR(50),
  emergency_primary_contact_whatsapp VARCHAR(10),
  emergency_secondary_contact_name VARCHAR(255),
  emergency_secondary_contact_relation VARCHAR(100),
  emergency_secondary_contact_mobile VARCHAR(50),
  emergency_doctor_name VARCHAR(255),
  emergency_doctor_phone VARCHAR(50),
  emergency_address TEXT,
  emergency_note TEXT,
  dob DATE,
  gender VARCHAR(50),
  city VARCHAR(100),
  state VARCHAR(100),
  pin_code VARCHAR(20),
  nationality VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS scan_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ip_address VARCHAR(100),
  user_agent VARCHAR(500),
  device_info VARCHAR(255),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS qr_cards (
  id INT AUTO_INCREMENT PRIMARY KEY,
  qr_id VARCHAR(32) UNIQUE,
  user_id INT NOT NULL,
  token VARCHAR(255) UNIQUE,
  path VARCHAR(255),
  is_active TINYINT DEFAULT 1,
  scan_count INT DEFAULT 0,
  last_scanned_at TIMESTAMP NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS emergency_primary_contact_name VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS emergency_primary_contact_relation VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS emergency_primary_contact_mobile VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS emergency_primary_contact_whatsapp VARCHAR(10);
ALTER TABLE users ADD COLUMN IF NOT EXISTS emergency_secondary_contact_name VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS emergency_secondary_contact_relation VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS emergency_secondary_contact_mobile VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS emergency_doctor_name VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS emergency_doctor_phone VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS emergency_address TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS emergency_note TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS dob DATE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS gender VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS city VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS state VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS pin_code VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS nationality VARCHAR(100);
