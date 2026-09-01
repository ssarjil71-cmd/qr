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
  nationality VARCHAR(100),
  card_user_type VARCHAR(100)
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

CREATE TABLE IF NOT EXISTS student_medical_reports (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  blood_group VARCHAR(20),
  height DECIMAL(6,2),
  weight DECIMAL(6,2),
  bmi DECIMAL(6,2),
  blood_pressure VARCHAR(50),
  pulse_rate VARCHAR(50),
  spo2 VARCHAR(50),
  body_temperature VARCHAR(50),
  last_health_checkup_date DATE,
  has_allergies VARCHAR(10),
  drug_allergies TEXT,
  food_allergies TEXT,
  other_allergies TEXT,
  allergy_details TEXT,
  diabetes VARCHAR(10),
  hypertension VARCHAR(10),
  heart_disease VARCHAR(10),
  asthma VARCHAR(10),
  epilepsy VARCHAR(10),
  kidney_disease VARCHAR(10),
  other_medical_condition TEXT,
  previous_surgery VARCHAR(10),
  surgery_details TEXT,
  currently_taking_medicines VARCHAR(10),
  vaccination_status VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_student_medical_reports_user_id (user_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_medicines (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  medicine_name VARCHAR(255) NOT NULL,
  dosage VARCHAR(100),
  frequency VARCHAR(100),
  purpose TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_student_medicines_user_id (user_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_vaccinations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  vaccine_name VARCHAR(255) NOT NULL,
  dose VARCHAR(100),
  vaccination_date DATE,
  next_due_date DATE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_student_vaccinations_user_id (user_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_medical_documents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  document_name VARCHAR(255) NOT NULL,
  document_type VARCHAR(100) NOT NULL,
  document_date DATE,
  description TEXT,
  file_path VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_student_medical_documents_user_id (user_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_technical_skills (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  skill_name VARCHAR(255) NOT NULL,
  skill_category VARCHAR(100) NOT NULL,
  proficiency_level VARCHAR(50) NOT NULL,
  years_experience DECIMAL(5,2),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_student_technical_skill (user_id, skill_name, skill_category),
  KEY idx_student_technical_skills_user_id (user_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_soft_skills (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  skill_name VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_student_soft_skill (user_id, skill_name),
  KEY idx_student_soft_skills_user_id (user_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_skill_tools (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  tool_name VARCHAR(255) NOT NULL,
  proficiency_level VARCHAR(50),
  years_experience DECIMAL(5,2),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_student_skill_tool (user_id, tool_name),
  KEY idx_student_skill_tools_user_id (user_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_languages (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  language_name VARCHAR(255) NOT NULL,
  reading_level VARCHAR(50),
  writing_level VARCHAR(50),
  speaking_level VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_student_language (user_id, language_name),
  KEY idx_student_languages_user_id (user_id),
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
ALTER TABLE users ADD COLUMN IF NOT EXISTS card_user_type VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_start_date DATE NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_expiry_date DATE NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(30) NOT NULL DEFAULT 'Suspended';

CREATE TABLE IF NOT EXISTS subscription_expiry_audit (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  previous_expiry_date DATE NULL,
  new_expiry_date DATE NULL,
  change_reason VARCHAR(100) NOT NULL DEFAULT 'manual_adjustment',
  changed_by INT NULL,
  changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_subscription_expiry_audit_user_id (user_id),
  KEY idx_subscription_expiry_audit_changed_at (changed_at),
  CONSTRAINT fk_subscription_expiry_audit_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS subscription_reminder_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  reminder_date DATE NOT NULL,
  reminder_type VARCHAR(50) NOT NULL DEFAULT 'expiry_warning',
  notification_channel VARCHAR(50) NOT NULL DEFAULT 'internal',
  notification_status VARCHAR(30) NOT NULL DEFAULT 'queued',
  message TEXT NULL,
  sent_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_subscription_reminder_daily (user_id, reminder_date, reminder_type),
  KEY idx_subscription_reminder_logs_user_id (user_id),
  KEY idx_subscription_reminder_logs_reminder_date (reminder_date),
  CONSTRAINT fk_subscription_reminder_logs_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_users_subscription_start_date ON users (subscription_start_date);
CREATE INDEX idx_users_subscription_expiry_date ON users (subscription_expiry_date, subscription_status);

CREATE TABLE IF NOT EXISTS organizations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  uuid VARCHAR(36) UNIQUE,
  name VARCHAR(255) NOT NULL,
  type VARCHAR(50),
  address_line1 TEXT,
  city VARCHAR(100),
  state VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS organization_members (
  id INT AUTO_INCREMENT PRIMARY KEY,
  organization_id INT NOT NULL,
  user_id INT NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_organization_member (organization_id, user_id),
  KEY idx_organization_members_user_id (user_id),
  FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS org_branches (
  id INT AUTO_INCREMENT PRIMARY KEY,
  organization_id INT NOT NULL,
  uuid VARCHAR(36) UNIQUE,
  name VARCHAR(255) NOT NULL,
  code VARCHAR(100),
  address_line1 TEXT,
  city VARCHAR(100),
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  KEY idx_org_branches_organization_id (organization_id),
  FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS org_departments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  branch_id INT NOT NULL,
  uuid VARCHAR(36) UNIQUE,
  name VARCHAR(255) NOT NULL,
  code VARCHAR(100),
  manager_user_id INT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  KEY idx_org_departments_branch_id (branch_id),
  FOREIGN KEY (branch_id) REFERENCES org_branches(id) ON DELETE CASCADE,
  FOREIGN KEY (manager_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS card_features (
  id INT AUTO_INCREMENT PRIMARY KEY,
  card_key VARCHAR(100) NOT NULL UNIQUE,
  card_name VARCHAR(255) NOT NULL,
  description TEXT,
  icon VARCHAR(100),
  display_order INT NOT NULL DEFAULT 0,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  is_default_enabled TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_card_permissions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  card_key VARCHAR(100) NOT NULL,
  is_enabled TINYINT(1) NOT NULL DEFAULT 0,
  is_required TINYINT(1) NOT NULL DEFAULT 0,
  assigned_by INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_user_card_permission (user_id, card_key),
  KEY idx_user_card_permissions_user_id (user_id),
  KEY idx_user_card_permissions_card_key (card_key),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (assigned_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS user_type_card_permissions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_type VARCHAR(100) NOT NULL,
  card_key VARCHAR(100) NOT NULL,
  is_enabled TINYINT(1) NOT NULL DEFAULT 0,
  is_required TINYINT(1) NOT NULL DEFAULT 0,
  display_order INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_user_type_card_permission (user_type, card_key),
  KEY idx_user_type_card_permissions_user_type (user_type),
  KEY idx_user_type_card_permissions_card_key (card_key)
);

CREATE TABLE IF NOT EXISTS organization_card_permissions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  organization_id INT NOT NULL,
  card_key VARCHAR(100) NOT NULL,
  is_enabled TINYINT(1) NOT NULL DEFAULT 0,
  is_required TINYINT(1) NOT NULL DEFAULT 0,
  assigned_by INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_org_card_permission (organization_id, card_key),
  KEY idx_org_card_permissions_org_id (organization_id),
  FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
  FOREIGN KEY (assigned_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS card_assignment_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NULL,
  organization_id INT NULL,
  card_key VARCHAR(100) NOT NULL,
  old_status VARCHAR(50),
  new_status VARCHAR(50) NOT NULL,
  changed_by INT NULL,
  ip_address VARCHAR(100),
  changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  KEY idx_card_assignment_logs_user_id (user_id),
  KEY idx_card_assignment_logs_org_id (organization_id),
  KEY idx_card_assignment_logs_card_key (card_key),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL,
  FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE SET NULL
);

INSERT INTO card_features (card_key, card_name, description, icon, display_order, is_active, is_default_enabled) VALUES
('basic_information', 'Basic Information', 'Personal details, contact info, photo, and address.', 'bi-person-lines-fill', 1, 1, 1),
('academic_information', 'Academic Information', 'College, branch, year, roll number, and student bio.', 'bi-mortarboard-fill', 2, 1, 1),
('emergency_contact', 'Emergency Contact', 'Emergency contacts, doctor details, and safety notes.', 'bi-telephone-inbound-fill', 3, 1, 1),
('medical_report', 'Medical Report', 'Health metrics, medical history, medicines, reports, and vaccinations.', 'bi-heart-pulse-fill', 4, 1, 0),
('skills', 'Skills', 'Technical skills, soft skills, tools, and languages.', 'bi-stars', 5, 1, 0),
('projects', 'Projects', 'Project portfolio, role, technologies, links, and descriptions.', 'bi-kanban-fill', 6, 1, 0),
('certificates', 'Certificates', 'Credentials, certificates, issuers, and verification links.', 'bi-award-fill', 7, 1, 0),
('upload_documents', 'Upload Documents', 'Student documents such as certificates, mark sheets, and PDFs.', 'bi-cloud-arrow-up-fill', 8, 1, 0),
('resume', 'Resume', 'Resume summary, preferred role, profile links, and resume download.', 'bi-file-earmark-person-fill', 9, 1, 1),
('social_links', 'Social Links', 'LinkedIn, GitHub, portfolio, and other public profile links.', 'bi-share-fill', 10, 1, 0)
ON DUPLICATE KEY UPDATE
  card_name=VALUES(card_name),
  description=VALUES(description),
  icon=VALUES(icon),
  display_order=VALUES(display_order);
