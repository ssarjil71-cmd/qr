from services.db import get_conn


class StudentProfileModel:
    SECTION_KEYS = (
        'basic_information',
        'academic_information',
        'skills',
        'projects',
        'certificates',
        'upload_documents',
        'resume',
        'emergency_contact',
        'medical_report',
        'social_links',
    )

    @staticmethod
    def _get_conn_and_cursor():
        conn = get_conn()
        cur = conn.cursor()
        return conn, cur

    @classmethod
    def ensure_tables(cls):
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS student_profiles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    organization_id INT NULL,
                    branch_id INT NULL,
                    department_id INT NULL,
                    college VARCHAR(255) NULL,
                    academic_branch VARCHAR(255) NULL,
                    academic_year VARCHAR(50) NULL,
                    roll_number VARCHAR(100) NULL,
                    bio TEXT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_student_profiles_user_id (user_id),
                    KEY idx_student_profiles_organization_id (organization_id),
                    KEY idx_student_profiles_branch_id (branch_id),
                    KEY idx_student_profiles_department_id (department_id),
                    CONSTRAINT fk_student_profiles_user
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    CONSTRAINT fk_student_profiles_organization
                        FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL,
                    CONSTRAINT fk_student_profiles_branch
                        FOREIGN KEY (branch_id) REFERENCES org_branches(id) ON DELETE SET NULL,
                    CONSTRAINT fk_student_profiles_department
                        FOREIGN KEY (department_id) REFERENCES org_departments(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS documents (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    document_type VARCHAR(100) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    file_path VARCHAR(255) NULL,
                    external_url VARCHAR(255) NULL,
                    notes TEXT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    KEY idx_documents_user_id (user_id),
                    KEY idx_documents_type (document_type),
                    CONSTRAINT fk_documents_user
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS projects (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    organization_id INT NULL,
                    title VARCHAR(255) NOT NULL,
                    role_name VARCHAR(255) NULL,
                    technologies TEXT NULL,
                    project_url VARCHAR(255) NULL,
                    start_date DATE NULL,
                    end_date DATE NULL,
                    description TEXT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    KEY idx_projects_user_id (user_id),
                    KEY idx_projects_organization_id (organization_id),
                    CONSTRAINT fk_projects_user
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    CONSTRAINT fk_projects_organization
                        FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS certificates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    document_id INT NULL,
                    title VARCHAR(255) NOT NULL,
                    issuer VARCHAR(255) NULL,
                    issue_date DATE NULL,
                    expiry_date DATE NULL,
                    credential_id VARCHAR(255) NULL,
                    credential_url VARCHAR(255) NULL,
                    description TEXT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    KEY idx_certificates_user_id (user_id),
                    KEY idx_certificates_document_id (document_id),
                    CONSTRAINT fk_certificates_user
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    CONSTRAINT fk_certificates_document
                        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS resume_profiles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    resume_document_id INT NULL,
                    headline VARCHAR(255) NULL,
                    summary TEXT NULL,
                    current_city VARCHAR(100) NULL,
                    preferred_role VARCHAR(255) NULL,
                    linkedin_url VARCHAR(255) NULL,
                    github_url VARCHAR(255) NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_resume_profiles_user_id (user_id),
                    KEY idx_resume_profiles_document_id (resume_document_id),
                    CONSTRAINT fk_resume_profiles_user
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    CONSTRAINT fk_resume_profiles_document
                        FOREIGN KEY (resume_document_id) REFERENCES documents(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS user_social_links (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    platform VARCHAR(100) NOT NULL,
                    username VARCHAR(255) NULL,
                    profile_url VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    KEY idx_user_social_links_user_id (user_id),
                    CONSTRAINT fk_user_social_links_user
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS student_medical_reports (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    blood_group VARCHAR(20) NULL,
                    height DECIMAL(6,2) NULL,
                    weight DECIMAL(6,2) NULL,
                    bmi DECIMAL(6,2) NULL,
                    blood_pressure VARCHAR(50) NULL,
                    pulse_rate VARCHAR(50) NULL,
                    spo2 VARCHAR(50) NULL,
                    body_temperature VARCHAR(50) NULL,
                    last_health_checkup_date DATE NULL,
                    has_allergies VARCHAR(10) NULL,
                    drug_allergies TEXT NULL,
                    food_allergies TEXT NULL,
                    other_allergies TEXT NULL,
                    allergy_details TEXT NULL,
                    diabetes VARCHAR(10) NULL,
                    hypertension VARCHAR(10) NULL,
                    heart_disease VARCHAR(10) NULL,
                    asthma VARCHAR(10) NULL,
                    epilepsy VARCHAR(10) NULL,
                    kidney_disease VARCHAR(10) NULL,
                    other_medical_condition TEXT NULL,
                    previous_surgery VARCHAR(10) NULL,
                    surgery_details TEXT NULL,
                    currently_taking_medicines VARCHAR(10) NULL,
                    vaccination_status VARCHAR(100) NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_student_medical_reports_user_id (user_id),
                    CONSTRAINT fk_student_medical_reports_user
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS student_medicines (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    medicine_name VARCHAR(255) NOT NULL,
                    dosage VARCHAR(100) NULL,
                    frequency VARCHAR(100) NULL,
                    purpose TEXT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    KEY idx_student_medicines_user_id (user_id),
                    CONSTRAINT fk_student_medicines_user
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS student_vaccinations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    vaccine_name VARCHAR(255) NOT NULL,
                    dose VARCHAR(100) NULL,
                    vaccination_date DATE NULL,
                    next_due_date DATE NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    KEY idx_student_vaccinations_user_id (user_id),
                    CONSTRAINT fk_student_vaccinations_user
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS student_medical_documents (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    document_name VARCHAR(255) NOT NULL,
                    document_type VARCHAR(100) NOT NULL,
                    document_date DATE NULL,
                    description TEXT NULL,
                    file_path VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    KEY idx_student_medical_documents_user_id (user_id),
                    CONSTRAINT fk_student_medical_documents_user
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS student_technical_skills (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    skill_name VARCHAR(255) NOT NULL,
                    skill_category VARCHAR(100) NOT NULL,
                    proficiency_level VARCHAR(50) NOT NULL,
                    years_experience DECIMAL(5,2) NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_student_technical_skill (user_id, skill_name, skill_category),
                    KEY idx_student_technical_skills_user_id (user_id),
                    CONSTRAINT fk_student_technical_skills_user
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS student_soft_skills (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    skill_name VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_student_soft_skill (user_id, skill_name),
                    KEY idx_student_soft_skills_user_id (user_id),
                    CONSTRAINT fk_student_soft_skills_user
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS student_skill_tools (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    tool_name VARCHAR(255) NOT NULL,
                    proficiency_level VARCHAR(50) NULL,
                    years_experience DECIMAL(5,2) NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_student_skill_tool (user_id, tool_name),
                    KEY idx_student_skill_tools_user_id (user_id),
                    CONSTRAINT fk_student_skill_tools_user
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS student_languages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    language_name VARCHAR(255) NOT NULL,
                    reading_level VARCHAR(50) NULL,
                    writing_level VARCHAR(50) NULL,
                    speaking_level VARCHAR(50) NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_student_language (user_id, language_name),
                    KEY idx_student_languages_user_id (user_id),
                    CONSTRAINT fk_student_languages_user
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS profile_section_visibility (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    profile_type VARCHAR(50) NOT NULL,
                    section_key VARCHAR(100) NOT NULL,
                    is_visible TINYINT(1) NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_profile_section_visibility (user_id, profile_type, section_key),
                    KEY idx_profile_section_visibility_user_id (user_id),
                    CONSTRAINT fk_profile_section_visibility_user
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            conn.commit()
        finally:
            cur.close()

    @staticmethod
    def _clean_photo(value):
        if not value or str(value).startswith('scrypt:'):
            return None
        cleaned = str(value)
        if cleaned.startswith('static/uploads/'):
            cleaned = cleaned.replace('static/uploads/', '', 1)
        return cleaned

    @staticmethod
    def _row_to_user_dict(row):
        return {
            'id': row[0],
            'user_type': row[1],
            'name': row[2],
            'mobile': row[3],
            'email': row[4],
            'photo': StudentProfileModel._clean_photo(row[6]),
            'education': row[7],
            'skills': row[8],
            'resume': row[9],
            'certificates': row[10],
            'company_name': row[11],
            'designation': row[12],
            'experience': row[13],
            'emergency_contact': row[14],
            'blood_group': row[15],
            'medical_notes': row[16],
            'address': row[17],
            'vehicle_number': row[18],
            'qr_token': row[19],
            'qr_path': row[20],
            'is_active': row[21],
            'reset_token': row[22],
            'created_at': row[23],
            'emergency_primary_contact_name': row[24] if len(row) > 24 else None,
            'emergency_primary_contact_relation': row[25] if len(row) > 25 else None,
            'emergency_primary_contact_mobile': row[26] if len(row) > 26 else None,
            'emergency_primary_contact_whatsapp': row[27] if len(row) > 27 else None,
            'emergency_secondary_contact_name': row[28] if len(row) > 28 else None,
            'emergency_secondary_contact_relation': row[29] if len(row) > 29 else None,
            'emergency_secondary_contact_mobile': row[30] if len(row) > 30 else None,
            'emergency_doctor_name': row[31] if len(row) > 31 else None,
            'emergency_doctor_phone': row[32] if len(row) > 32 else None,
            'emergency_address': row[33] if len(row) > 33 else None,
            'emergency_note': row[34] if len(row) > 34 else None,
            'dob': row[35] if len(row) > 35 else None,
            'gender': row[36] if len(row) > 36 else None,
            'city': row[37] if len(row) > 37 else None,
            'state': row[38] if len(row) > 38 else None,
            'pin_code': row[39] if len(row) > 39 else None,
            'nationality': row[40] if len(row) > 40 else None,
        }

    @classmethod
    def _ensure_user_columns(cls):
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute('SHOW COLUMNS FROM users')
            existing_columns = {row[0] for row in cur.fetchall()}
            required_columns = {
                'dob': 'DATE',
                'gender': 'VARCHAR(50)',
                'city': 'VARCHAR(100)',
                'state': 'VARCHAR(100)',
                'pin_code': 'VARCHAR(20)',
                'nationality': 'VARCHAR(100)',
            }
            for column_name, column_type in required_columns.items():
                if column_name not in existing_columns:
                    cur.execute(f'ALTER TABLE users ADD COLUMN {column_name} {column_type}')
            # Add district_id and taluka_id to store selected IDs (nullable)
            if 'district_id' not in existing_columns:
                cur.execute('ALTER TABLE users ADD COLUMN district_id INT NULL')
            if 'taluka_id' not in existing_columns:
                cur.execute('ALTER TABLE users ADD COLUMN taluka_id INT NULL')
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def _get_user(cls, user_id):
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute('SELECT * FROM users WHERE id=%s', (user_id,))
            row = cur.fetchone()
            return cls._row_to_user_dict(row) if row else None
        finally:
            cur.close()

    @classmethod
    def _get_user_organization_id(cls, user_id):
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                SELECT organization_id
                FROM organization_members
                WHERE user_id=%s AND is_active=1
                ORDER BY id ASC
                LIMIT 1
                ''',
                (user_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None
        finally:
            cur.close()

    @classmethod
    def _completion(cls, values):
        if not values:
            return 0
        filled = 0
        for value in values:
            if isinstance(value, str):
                if value.strip():
                    filled += 1
            elif value is not None and value != '':
                filled += 1
        return round((filled / len(values)) * 100)

    @classmethod
    def has_student_profile(cls, user_id):
        if not user_id:
            return False
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                'SELECT COUNT(*) FROM user_profile_selections WHERE user_id=%s AND profile_type=%s',
                (user_id, 'student'),
            )
            if cur.fetchone()[0] > 0:
                return True
        except Exception:
            pass
        finally:
            cur.close()

        user = cls._get_user(user_id)
        return bool(user and user['user_type'] == 'student')

    @classmethod
    def _get_student_profile(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                SELECT id, user_id, organization_id, branch_id, department_id, college,
                       academic_branch, academic_year, roll_number, bio, created_at, updated_at
                FROM student_profiles
                WHERE user_id=%s
                LIMIT 1
                ''',
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                'id': row[0],
                'user_id': row[1],
                'organization_id': row[2],
                'branch_id': row[3],
                'department_id': row[4],
                'college': row[5],
                'branch': row[6],
                'year': row[7],
                'roll_number': row[8],
                'bio': row[9],
                'created_at': row[10],
                'updated_at': row[11],
            }
        finally:
            cur.close()

    @classmethod
    def _list_projects(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                SELECT id, title, role_name, technologies, project_url, start_date, end_date, description,
                       created_at, updated_at
                FROM projects
                WHERE user_id=%s
                ORDER BY created_at DESC, id DESC
                ''',
                (user_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    'id': row[0],
                    'title': row[1],
                    'role_name': row[2],
                    'technologies': row[3],
                    'project_url': row[4],
                    'start_date': row[5].isoformat() if row[5] else '',
                    'end_date': row[6].isoformat() if row[6] else '',
                    'description': row[7],
                    'created_at': row[8],
                    'updated_at': row[9],
                }
                for row in rows
            ]
        finally:
            cur.close()

    @classmethod
    def _list_social_links(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                SELECT id, platform, username, profile_url, created_at, updated_at
                FROM user_social_links
                WHERE user_id=%s
                ORDER BY created_at DESC, id DESC
                ''',
                (user_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    'id': row[0],
                    'platform': row[1],
                    'username': row[2],
                    'profile_url': row[3],
                    'created_at': row[4],
                    'updated_at': row[5],
                }
                for row in rows
            ]
        finally:
            cur.close()

    @classmethod
    def _list_certificates(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                SELECT c.id, c.document_id, c.title, c.issuer, c.issue_date, c.expiry_date,
                       c.credential_id, c.credential_url, c.description,
                       d.external_url, d.file_path, c.created_at, c.updated_at
                FROM certificates c
                LEFT JOIN documents d ON d.id = c.document_id
                WHERE c.user_id=%s
                ORDER BY c.created_at DESC, c.id DESC
                ''',
                (user_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    'id': row[0],
                    'document_id': row[1],
                    'title': row[2],
                    'issuer': row[3],
                    'issue_date': row[4].isoformat() if row[4] else '',
                    'expiry_date': row[5].isoformat() if row[5] else '',
                    'credential_id': row[6],
                    'credential_url': row[7],
                    'description': row[8],
                    'document_url': row[9] or '',
                    'document_path': row[10] or '',
                    'created_at': row[11],
                    'updated_at': row[12],
                }
                for row in rows
            ]
        finally:
            cur.close()

    @classmethod
    def _get_resume_profile(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                SELECT r.id, r.user_id, r.resume_document_id, r.headline, r.summary, r.current_city,
                       r.preferred_role, r.linkedin_url, r.github_url, d.external_url, d.file_path,
                       r.created_at, r.updated_at
                FROM resume_profiles r
                LEFT JOIN documents d ON d.id = r.resume_document_id
                WHERE r.user_id=%s
                LIMIT 1
                ''',
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                'id': row[0],
                'user_id': row[1],
                'resume_document_id': row[2],
                'headline': row[3],
                'summary': row[4],
                'current_city': row[5],
                'preferred_role': row[6],
                'linkedin_url': row[7],
                'github_url': row[8],
                'document_url': row[9] or '',
                'document_path': row[10] or '',
                'created_at': row[11],
                'updated_at': row[12],
            }
        finally:
            cur.close()

    @classmethod
    @classmethod
    def _list_uploaded_documents(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                SELECT id, document_type, title, file_path, external_url, notes, created_at, updated_at
                FROM documents
                WHERE user_id=%s AND document_type IN ('caste_certificate', 'domicile', 'nationality', 'mark_sheet')
                ORDER BY created_at DESC, id DESC
                ''',
                (user_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    'id': row[0],
                    'document_type': row[1],
                    'title': row[2],
                    'file_path': row[3] or '',
                    'external_url': row[4] or '',
                    'notes': row[5] or '',
                    'created_at': row[6],
                    'updated_at': row[7],
                }
                for row in rows
            ]
        finally:
            cur.close()

    @classmethod
    def _get_medical_report(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                SELECT id, user_id, blood_group, height, weight, bmi, blood_pressure, pulse_rate,
                       spo2, body_temperature, last_health_checkup_date, has_allergies,
                       drug_allergies, food_allergies, other_allergies, allergy_details,
                       diabetes, hypertension, heart_disease, asthma, epilepsy, kidney_disease,
                       other_medical_condition, previous_surgery, surgery_details,
                       currently_taking_medicines, vaccination_status, created_at, updated_at
                FROM student_medical_reports
                WHERE user_id=%s
                LIMIT 1
                ''',
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return {}
            keys = (
                'id', 'user_id', 'blood_group', 'height', 'weight', 'bmi', 'blood_pressure', 'pulse_rate',
                'spo2', 'body_temperature', 'last_health_checkup_date', 'has_allergies',
                'drug_allergies', 'food_allergies', 'other_allergies', 'allergy_details',
                'diabetes', 'hypertension', 'heart_disease', 'asthma', 'epilepsy', 'kidney_disease',
                'other_medical_condition', 'previous_surgery', 'surgery_details',
                'currently_taking_medicines', 'vaccination_status', 'created_at', 'updated_at',
            )
            report = dict(zip(keys, row))
            for date_key in ('last_health_checkup_date',):
                report[date_key] = report[date_key].isoformat() if report[date_key] else ''
            for decimal_key in ('height', 'weight', 'bmi'):
                report[decimal_key] = str(report[decimal_key]) if report[decimal_key] is not None else ''
            return report
        finally:
            cur.close()

    @classmethod
    def _list_medicines(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                SELECT id, medicine_name, dosage, frequency, purpose
                FROM student_medicines
                WHERE user_id=%s
                ORDER BY id ASC
                ''',
                (user_id,),
            )
            return [
                {'id': row[0], 'medicine_name': row[1], 'dosage': row[2], 'frequency': row[3], 'purpose': row[4]}
                for row in cur.fetchall()
            ]
        finally:
            cur.close()

    @classmethod
    def _list_vaccinations(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                SELECT id, vaccine_name, dose, vaccination_date, next_due_date
                FROM student_vaccinations
                WHERE user_id=%s
                ORDER BY id ASC
                ''',
                (user_id,),
            )
            return [
                {
                    'id': row[0],
                    'vaccine_name': row[1],
                    'dose': row[2],
                    'vaccination_date': row[3].isoformat() if row[3] else '',
                    'next_due_date': row[4].isoformat() if row[4] else '',
                }
                for row in cur.fetchall()
            ]
        finally:
            cur.close()

    @classmethod
    def _list_medical_documents(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                SELECT id, document_name, document_type, document_date, description, file_path
                FROM student_medical_documents
                WHERE user_id=%s
                ORDER BY created_at DESC, id DESC
                ''',
                (user_id,),
            )
            return [
                {
                    'id': row[0],
                    'document_name': row[1],
                    'document_type': row[2],
                    'document_date': row[3].isoformat() if row[3] else '',
                    'description': row[4],
                    'file_path': row[5],
                }
                for row in cur.fetchall()
            ]
        finally:
            cur.close()

    @classmethod
    def _list_technical_skills(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                SELECT id, skill_name, skill_category, proficiency_level, years_experience
                FROM student_technical_skills
                WHERE user_id=%s
                ORDER BY skill_name ASC
                ''',
                (user_id,),
            )
            return [
                {
                    'id': row[0],
                    'skill_name': row[1],
                    'skill_category': row[2],
                    'proficiency_level': row[3],
                    'years_experience': str(row[4]) if row[4] is not None else '',
                }
                for row in cur.fetchall()
            ]
        finally:
            cur.close()

    @classmethod
    def _list_soft_skills(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                'SELECT id, skill_name FROM student_soft_skills WHERE user_id=%s ORDER BY skill_name ASC',
                (user_id,),
            )
            return [{'id': row[0], 'skill_name': row[1]} for row in cur.fetchall()]
        finally:
            cur.close()

    @classmethod
    def _list_skill_tools(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                SELECT id, tool_name, proficiency_level, years_experience
                FROM student_skill_tools
                WHERE user_id=%s
                ORDER BY tool_name ASC
                ''',
                (user_id,),
            )
            return [
                {
                    'id': row[0],
                    'tool_name': row[1],
                    'proficiency_level': row[2],
                    'years_experience': str(row[3]) if row[3] is not None else '',
                }
                for row in cur.fetchall()
            ]
        finally:
            cur.close()

    @classmethod
    def _list_languages(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                SELECT id, language_name, reading_level, writing_level, speaking_level
                FROM student_languages
                WHERE user_id=%s
                ORDER BY language_name ASC
                ''',
                (user_id,),
            )
            return [
                {
                    'id': row[0],
                    'language_name': row[1],
                    'reading_level': row[2],
                    'writing_level': row[3],
                    'speaking_level': row[4],
                }
                for row in cur.fetchall()
            ]
        finally:
            cur.close()

    @classmethod
    def _build_sections(cls, user, student_profile, projects, certificates, uploaded_documents, resume_profile, social_links, medical_report=None, medicines=None, vaccinations=None, medical_documents=None, technical_skills=None, soft_skills=None, skill_tools=None, languages=None):
        basic_completion = cls._completion(
            [
                user['name'],
                user['mobile'],
                user['email'],
                user['dob'],
                user['gender'],
                user['blood_group'],
                user['address'],
                user['city'],
                user['state'],
                user['pin_code'],
                user['nationality'],
                user['photo'],
            ]
        )
        academic_completion = cls._completion(
            [
                student_profile['college'] if student_profile else '',
                student_profile['branch'] if student_profile else '',
                student_profile['year'] if student_profile else '',
                student_profile['roll_number'] if student_profile else '',
            ]
        )
        technical_skills = technical_skills or []
        soft_skills = soft_skills or []
        skill_tools = skill_tools or []
        languages = languages or []
        skills_completion = 0
        if technical_skills:
            skills_completion += 40
        if soft_skills:
            skills_completion += 20
        if skill_tools:
            skills_completion += 15
        if languages:
            skills_completion += 25
        project_completion = 0
        if projects:
            project_completion = round(
                sum(
                    cls._completion(
                        [
                            project['title'],
                            project['role_name'],
                            project['technologies'],
                            project['project_url'],
                            project['description'],
                        ]
                    )
                    for project in projects
                ) / len(projects)
            )
        certificate_completion = 0
        if certificates:
            certificate_completion = round(
                sum(
                    cls._completion(
                        [
                            certificate['title'],
                            certificate['issuer'],
                            certificate['issue_date'],
                            certificate['credential_id'],
                            certificate['credential_url'] or certificate['document_url'],
                        ]
                    )
                    for certificate in certificates
                ) / len(certificates)
            )
        documents_completion = 100 if uploaded_documents else 0
        resume_completion = cls._completion(
            [
                resume_profile['headline'] if resume_profile else '',
                resume_profile['summary'] if resume_profile else '',
                resume_profile['current_city'] if resume_profile else '',
                resume_profile['preferred_role'] if resume_profile else '',
                resume_profile['linkedin_url'] if resume_profile else '',
                resume_profile['document_url'] if resume_profile else '',
            ]
        )
        social_completion = 0
        if social_links:
            social_completion = round(
                sum(
                    cls._completion([link['platform'], link['username'], link['profile_url']])
                    for link in social_links
                ) / len(social_links)
            )
        emergency_completion = cls._completion([user['emergency_contact']])
        medical_report = medical_report or {}
        medicines = medicines or []
        vaccinations = vaccinations or []
        medical_documents = medical_documents or []
        medical_completion = cls._completion(
            [
                medical_report.get('blood_group') or user.get('blood_group'),
                medical_report.get('height'),
                medical_report.get('weight'),
                medical_report.get('bmi'),
                medical_report.get('blood_pressure'),
                medical_report.get('pulse_rate'),
                medical_report.get('spo2'),
                medical_report.get('body_temperature'),
                medical_report.get('last_health_checkup_date'),
                medical_report.get('has_allergies'),
                medical_report.get('diabetes'),
                medical_report.get('hypertension'),
                medical_report.get('heart_disease'),
                medical_report.get('asthma'),
                medical_report.get('epilepsy'),
                medical_report.get('kidney_disease'),
                medical_report.get('previous_surgery'),
                medical_report.get('currently_taking_medicines'),
                1 if medicines else '',
                medical_report.get('vaccination_status'),
                1 if vaccinations else '',
                1 if medical_documents else '',
            ]
        )

        return [
            {'key': 'basic_information', 'title': 'Basic Information', 'completion': basic_completion},
            {'key': 'academic_information', 'title': 'Academic Information', 'completion': academic_completion},
            {'key': 'emergency_contact', 'title': 'Emergency Contact', 'completion': emergency_completion},
            {'key': 'medical_report', 'title': 'Medical Report', 'completion': medical_completion},
            {'key': 'skills', 'title': 'Skills', 'completion': skills_completion},
            {'key': 'projects', 'title': 'Projects', 'completion': project_completion},
            {'key': 'certificates', 'title': 'Certificates', 'completion': certificate_completion},
            {'key': 'upload_documents', 'title': 'Upload Documents', 'completion': documents_completion},
            {'key': 'resume', 'title': 'Resume', 'completion': resume_completion},
            {'key': 'social_links', 'title': 'Social Links', 'completion': social_completion},
        ]

    @classmethod
    def get_visible_section_keys(cls, user_id, profile_type='student'):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                SELECT section_key
                FROM profile_section_visibility
                WHERE user_id=%s AND profile_type=%s AND is_visible=1
                ''',
                (user_id, profile_type),
            )
            return {row[0] for row in cur.fetchall()}
        finally:
            cur.close()

    @classmethod
    def set_section_visibility(cls, user_id, section_key, is_visible, profile_type='student'):
        if section_key not in cls.SECTION_KEYS:
            return False
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                INSERT INTO profile_section_visibility (user_id, profile_type, section_key, is_visible)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE is_visible=VALUES(is_visible)
                ''',
                (user_id, profile_type, section_key, 1 if is_visible else 0),
            )
            conn.commit()
            return True
        finally:
            cur.close()

    @classmethod
    def get_student_dashboard_data(cls, user_id):
        cls.ensure_tables()
        user = cls._get_user(user_id)
        if not user:
            return None

        student_profile = cls._get_student_profile(user_id)
        projects = cls._list_projects(user_id)
        certificates = cls._list_certificates(user_id)
        uploaded_documents = cls._list_uploaded_documents(user_id)
        resume_profile = cls._get_resume_profile(user_id)
        social_links = cls._list_social_links(user_id)
        medical_report = cls._get_medical_report(user_id)
        medicines = cls._list_medicines(user_id)
        vaccinations = cls._list_vaccinations(user_id)
        medical_documents = cls._list_medical_documents(user_id)
        technical_skills = cls._list_technical_skills(user_id)
        soft_skills = cls._list_soft_skills(user_id)
        skill_tools = cls._list_skill_tools(user_id)
        languages = cls._list_languages(user_id)
        sections = cls._build_sections(
            user=user,
            student_profile=student_profile,
            projects=projects,
            certificates=certificates,
            uploaded_documents=uploaded_documents,
            resume_profile=resume_profile,
            social_links=social_links,
            medical_report=medical_report,
            medicines=medicines,
            vaccinations=vaccinations,
            medical_documents=medical_documents,
            technical_skills=technical_skills,
            soft_skills=soft_skills,
            skill_tools=skill_tools,
            languages=languages,
        )
        visible_section_keys = cls.get_visible_section_keys(user_id, 'student')
        for section in sections:
            section['public_visible'] = section['key'] in visible_section_keys
        overall_completion = round(sum(section['completion'] for section in sections) / len(sections)) if sections else 0
        return {
            'user': user,
            'student_profile': student_profile or {},
            'projects': projects,
            'certificates': certificates,
            'uploaded_documents': uploaded_documents,
            'resume_profile': resume_profile or {},
            'social_links': social_links,
            'medical_report': medical_report,
            'medicines': medicines,
            'vaccinations': vaccinations,
            'medical_documents': medical_documents,
            'technical_skills': technical_skills,
            'soft_skills': soft_skills,
            'skill_tools': skill_tools,
            'languages': languages,
            'sections': sections,
            'visible_section_keys': visible_section_keys,
            'overall_completion': overall_completion,
        }

    @classmethod
    def update_basic_information(cls, user_id, payload):
        cls._ensure_user_columns()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                UPDATE users
                SET name=%s,
                    mobile=%s,
                    email=%s,
                    dob=%s,
                    gender=%s,
                    blood_group=%s,
                    address=%s,
                    city=%s,
                    state=%s,
                    pin_code=%s,
                    district_id=%s,
                    taluka_id=%s,
                    nationality=%s,
                    photo=%s
                WHERE id=%s
                ''',
                (
                    payload.get('name'),
                    payload.get('mobile'),
                    payload.get('email'),
                    payload.get('dob'),
                    payload.get('gender'),
                    payload.get('blood_group'),
                    payload.get('address'),
                    payload.get('city'),
                    payload.get('state'),
                    payload.get('pin_code'),
                    payload.get('district_id'),
                    payload.get('taluka_id'),
                    payload.get('nationality'),
                    payload.get('photo'),
                    user_id,
                ),
            )
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def update_academic_information(cls, user_id, payload):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            organization_id = cls._get_user_organization_id(user_id)
            cur.execute('SELECT id FROM student_profiles WHERE user_id=%s', (user_id,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    '''
                    UPDATE student_profiles
                    SET organization_id=%s,
                        college=%s,
                        academic_branch=%s,
                        academic_year=%s,
                        roll_number=%s,
                        bio=%s
                    WHERE user_id=%s
                    ''',
                    (
                        organization_id,
                        payload.get('college'),
                        payload.get('branch'),
                        payload.get('year'),
                        payload.get('roll_number'),
                        payload.get('bio'),
                        user_id,
                    ),
                )
            else:
                cur.execute(
                    '''
                    INSERT INTO student_profiles (
                        user_id, organization_id, college, academic_branch, academic_year, roll_number, bio
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''',
                    (
                        user_id,
                        organization_id,
                        payload.get('college'),
                        payload.get('branch'),
                        payload.get('year'),
                        payload.get('roll_number'),
                        payload.get('bio'),
                    ),
                )
            cur.execute('UPDATE users SET education=%s WHERE id=%s', (payload.get('college'), user_id))
            conn.commit()
            return True, ''
        finally:
            cur.close()

    @classmethod
    def clear_academic_information(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute('DELETE FROM student_profiles WHERE user_id=%s', (user_id,))
            cur.execute('UPDATE users SET education=NULL WHERE id=%s', (user_id,))
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def update_emergency_contact(cls, user_id, payload):
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                UPDATE users
                SET emergency_contact=%s,
                    emergency_primary_contact_name=%s,
                    emergency_primary_contact_relation=%s,
                    emergency_primary_contact_mobile=%s,
                    emergency_primary_contact_whatsapp=%s,
                    emergency_secondary_contact_name=%s,
                    emergency_secondary_contact_relation=%s,
                    emergency_secondary_contact_mobile=%s,
                    emergency_doctor_name=%s,
                    emergency_doctor_phone=%s,
                    emergency_address=%s,
                    emergency_note=%s
                WHERE id=%s
                ''',
                (
                    payload.get('emergency_primary_contact_mobile'),
                    payload.get('emergency_primary_contact_name'),
                    payload.get('emergency_primary_contact_relation'),
                    payload.get('emergency_primary_contact_mobile'),
                    payload.get('emergency_primary_contact_whatsapp'),
                    payload.get('emergency_secondary_contact_name'),
                    payload.get('emergency_secondary_contact_relation'),
                    payload.get('emergency_secondary_contact_mobile'),
                    payload.get('emergency_doctor_name'),
                    payload.get('emergency_doctor_phone'),
                    payload.get('emergency_address'),
                    payload.get('emergency_note'),
                    user_id,
                ),
            )
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def update_medical_report(cls, user_id, payload):
        cls.ensure_tables()
        height = payload.get('height') or None
        weight = payload.get('weight') or None
        bmi = None
        try:
            height_m = float(height) / 100 if height else 0
            weight_kg = float(weight) if weight else 0
            if height_m > 0 and weight_kg > 0:
                bmi = round(weight_kg / (height_m * height_m), 2)
        except (TypeError, ValueError):
            bmi = None

        has_allergies = payload.get('has_allergies')
        previous_surgery = payload.get('previous_surgery')
        currently_taking_medicines = payload.get('currently_taking_medicines')
        allergy_values = {
            'drug_allergies': payload.get('drug_allergies') if has_allergies == 'yes' else None,
            'food_allergies': payload.get('food_allergies') if has_allergies == 'yes' else None,
            'other_allergies': payload.get('other_allergies') if has_allergies == 'yes' else None,
            'allergy_details': payload.get('allergy_details') if has_allergies == 'yes' else None,
        }
        surgery_details = payload.get('surgery_details') if previous_surgery == 'yes' else None
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                INSERT INTO student_medical_reports (
                    user_id, blood_group, height, weight, bmi, blood_pressure, pulse_rate, spo2,
                    body_temperature, last_health_checkup_date, has_allergies, drug_allergies,
                    food_allergies, other_allergies, allergy_details, diabetes, hypertension,
                    heart_disease, asthma, epilepsy, kidney_disease, other_medical_condition,
                    previous_surgery, surgery_details, currently_taking_medicines, vaccination_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    blood_group=VALUES(blood_group), height=VALUES(height), weight=VALUES(weight), bmi=VALUES(bmi),
                    blood_pressure=VALUES(blood_pressure), pulse_rate=VALUES(pulse_rate), spo2=VALUES(spo2),
                    body_temperature=VALUES(body_temperature), last_health_checkup_date=VALUES(last_health_checkup_date),
                    has_allergies=VALUES(has_allergies), drug_allergies=VALUES(drug_allergies),
                    food_allergies=VALUES(food_allergies), other_allergies=VALUES(other_allergies),
                    allergy_details=VALUES(allergy_details), diabetes=VALUES(diabetes),
                    hypertension=VALUES(hypertension), heart_disease=VALUES(heart_disease), asthma=VALUES(asthma),
                    epilepsy=VALUES(epilepsy), kidney_disease=VALUES(kidney_disease),
                    other_medical_condition=VALUES(other_medical_condition),
                    previous_surgery=VALUES(previous_surgery), surgery_details=VALUES(surgery_details),
                    currently_taking_medicines=VALUES(currently_taking_medicines),
                    vaccination_status=VALUES(vaccination_status)
                ''',
                (
                    user_id, payload.get('blood_group'), height, weight, bmi, payload.get('blood_pressure'),
                    payload.get('pulse_rate'), payload.get('spo2'), payload.get('body_temperature'),
                    payload.get('last_health_checkup_date') or None, has_allergies,
                    allergy_values['drug_allergies'], allergy_values['food_allergies'],
                    allergy_values['other_allergies'], allergy_values['allergy_details'],
                    payload.get('diabetes'), payload.get('hypertension'), payload.get('heart_disease'),
                    payload.get('asthma'), payload.get('epilepsy'), payload.get('kidney_disease'),
                    payload.get('other_medical_condition'), previous_surgery, surgery_details,
                    currently_taking_medicines, payload.get('vaccination_status'),
                ),
            )
            cur.execute('UPDATE users SET blood_group=%s WHERE id=%s', (payload.get('blood_group'), user_id))
            cur.execute('DELETE FROM student_medicines WHERE user_id=%s', (user_id,))
            if currently_taking_medicines == 'yes':
                for medicine in payload.get('medicines') or []:
                    if medicine.get('medicine_name'):
                        cur.execute(
                            '''
                            INSERT INTO student_medicines (user_id, medicine_name, dosage, frequency, purpose)
                            VALUES (%s, %s, %s, %s, %s)
                            ''',
                            (user_id, medicine.get('medicine_name'), medicine.get('dosage'), medicine.get('frequency'), medicine.get('purpose')),
                        )
            cur.execute('DELETE FROM student_vaccinations WHERE user_id=%s', (user_id,))
            for vaccination in payload.get('vaccinations') or []:
                if vaccination.get('vaccine_name'):
                    cur.execute(
                        '''
                        INSERT INTO student_vaccinations (user_id, vaccine_name, dose, vaccination_date, next_due_date)
                        VALUES (%s, %s, %s, %s, %s)
                        ''',
                        (
                            user_id, vaccination.get('vaccine_name'), vaccination.get('dose'),
                            vaccination.get('vaccination_date') or None, vaccination.get('next_due_date') or None,
                        ),
                    )
            for document in payload.get('documents') or []:
                if document.get('document_name') and document.get('document_type') and document.get('file_path'):
                    cur.execute(
                        '''
                        INSERT INTO student_medical_documents (
                            user_id, document_name, document_type, document_date, description, file_path
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        ''',
                        (
                            user_id, document.get('document_name'), document.get('document_type'),
                            document.get('document_date') or None, document.get('description'), document.get('file_path'),
                        ),
                    )
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def delete_medical_document(cls, user_id, document_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute('DELETE FROM student_medical_documents WHERE id=%s AND user_id=%s', (document_id, user_id))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close()

    @classmethod
    def update_skills(cls, user_id, payload):
        cls.ensure_tables()
        technical_skills = payload.get('technical_skills') or []
        soft_skills = payload.get('soft_skills') or []
        skill_tools = payload.get('skill_tools') or []
        languages = payload.get('languages') or []
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute('DELETE FROM student_technical_skills WHERE user_id=%s', (user_id,))
            cur.execute('DELETE FROM student_soft_skills WHERE user_id=%s', (user_id,))
            cur.execute('DELETE FROM student_skill_tools WHERE user_id=%s', (user_id,))
            cur.execute('DELETE FROM student_languages WHERE user_id=%s', (user_id,))
            for skill in technical_skills:
                cur.execute(
                    '''
                    INSERT INTO student_technical_skills (
                        user_id, skill_name, skill_category, proficiency_level, years_experience
                    ) VALUES (%s, %s, %s, %s, %s)
                    ''',
                    (
                        user_id,
                        skill.get('skill_name'),
                        skill.get('skill_category'),
                        skill.get('proficiency_level'),
                        skill.get('years_experience') or None,
                    ),
                )
            for skill in soft_skills:
                cur.execute(
                    'INSERT INTO student_soft_skills (user_id, skill_name) VALUES (%s, %s)',
                    (user_id, skill.get('skill_name')),
                )
            for tool in skill_tools:
                cur.execute(
                    '''
                    INSERT INTO student_skill_tools (user_id, tool_name, proficiency_level, years_experience)
                    VALUES (%s, %s, %s, %s)
                    ''',
                    (user_id, tool.get('tool_name'), tool.get('proficiency_level'), tool.get('years_experience') or None),
                )
            for language in languages:
                cur.execute(
                    '''
                    INSERT INTO student_languages (
                        user_id, language_name, reading_level, writing_level, speaking_level
                    ) VALUES (%s, %s, %s, %s, %s)
                    ''',
                    (
                        user_id,
                        language.get('language_name'),
                        language.get('reading_level'),
                        language.get('writing_level'),
                        language.get('speaking_level'),
                    ),
                )
            summary_parts = []
            if technical_skills:
                summary_parts.append('Technical Skills: ' + ', '.join(skill['skill_name'] for skill in technical_skills))
            if soft_skills:
                summary_parts.append('Soft Skills: ' + ', '.join(skill['skill_name'] for skill in soft_skills))
            if skill_tools:
                summary_parts.append('Tools: ' + ', '.join(tool['tool_name'] for tool in skill_tools))
            if languages:
                summary_parts.append('Languages: ' + ', '.join(language['language_name'] for language in languages))
            cur.execute('UPDATE users SET skills=%s WHERE id=%s', (' | '.join(summary_parts) or None, user_id))
            conn.commit()
            return True, ''
        except Exception as exc:
            conn.rollback()
            return False, str(exc)
        finally:
            cur.close()

    @classmethod
    def clear_skills(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute('DELETE FROM student_technical_skills WHERE user_id=%s', (user_id,))
            cur.execute('DELETE FROM student_soft_skills WHERE user_id=%s', (user_id,))
            cur.execute('DELETE FROM student_skill_tools WHERE user_id=%s', (user_id,))
            cur.execute('DELETE FROM student_languages WHERE user_id=%s', (user_id,))
            cur.execute('UPDATE users SET skills=NULL WHERE id=%s', (user_id,))
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def _sync_legacy_certificates(cls, user_id):
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute('SELECT title FROM certificates WHERE user_id=%s ORDER BY created_at DESC, id DESC', (user_id,))
            titles = [row[0] for row in cur.fetchall() if row[0]]
            cur.execute('UPDATE users SET certificates=%s WHERE id=%s', (', '.join(titles) or None, user_id))
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def _sync_legacy_resume(cls, user_id):
        resume_profile = ResumeProfileModel.get_by_user(user_id)
        legacy_value = None
        if resume_profile:
            legacy_value = resume_profile.get('document_url') or resume_profile.get('document_path') or resume_profile.get('headline')
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute('UPDATE users SET resume=%s WHERE id=%s', (legacy_value, user_id))
            conn.commit()
        finally:
            cur.close()


class ProjectModel:
    @staticmethod
    def create(user_id, payload):
        StudentProfileModel.ensure_tables()
        organization_id = StudentProfileModel._get_user_organization_id(user_id)
        conn, cur = StudentProfileModel._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                INSERT INTO projects (
                    user_id, organization_id, title, role_name, technologies, project_url,
                    start_date, end_date, description
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''',
                (
                    user_id,
                    organization_id,
                    payload.get('title'),
                    payload.get('role_name'),
                    payload.get('technologies'),
                    payload.get('project_url'),
                    payload.get('start_date') or None,
                    payload.get('end_date') or None,
                    payload.get('description'),
                ),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            cur.close()

    @staticmethod
    def update(user_id, project_id, payload):
        StudentProfileModel.ensure_tables()
        conn, cur = StudentProfileModel._get_conn_and_cursor()
        try:
            cur.execute('SELECT id FROM projects WHERE id=%s AND user_id=%s', (project_id, user_id))
            if not cur.fetchone():
                return False
            cur.execute(
                '''
                UPDATE projects
                SET title=%s,
                    role_name=%s,
                    technologies=%s,
                    project_url=%s,
                    start_date=%s,
                    end_date=%s,
                    description=%s
                WHERE id=%s AND user_id=%s
                ''',
                (
                    payload.get('title'),
                    payload.get('role_name'),
                    payload.get('technologies'),
                    payload.get('project_url'),
                    payload.get('start_date') or None,
                    payload.get('end_date') or None,
                    payload.get('description'),
                    project_id,
                    user_id,
                ),
            )
            conn.commit()
            return True
        finally:
            cur.close()

    @staticmethod
    def delete(user_id, project_id):
        StudentProfileModel.ensure_tables()
        conn, cur = StudentProfileModel._get_conn_and_cursor()
        try:
            cur.execute('DELETE FROM projects WHERE id=%s AND user_id=%s', (project_id, user_id))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close()


class DocumentModel:
    @staticmethod
    def upsert(user_id, document_type, title, external_url=None, file_path=None, notes=None, document_id=None):
        StudentProfileModel.ensure_tables()
        conn, cur = StudentProfileModel._get_conn_and_cursor()
        try:
            if document_id:
                cur.execute('SELECT id FROM documents WHERE id=%s AND user_id=%s', (document_id, user_id))
                if cur.fetchone():
                    cur.execute(
                        '''
                        UPDATE documents
                        SET document_type=%s, title=%s, external_url=%s, file_path=%s, notes=%s
                        WHERE id=%s AND user_id=%s
                        ''',
                        (document_type, title, external_url, file_path, notes, document_id, user_id),
                    )
                    conn.commit()
                    return document_id
            cur.execute(
                '''
                INSERT INTO documents (user_id, document_type, title, external_url, file_path, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                ''',
                (user_id, document_type, title, external_url, file_path, notes),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            cur.close()

    @staticmethod
    def delete(user_id, document_id):
        StudentProfileModel.ensure_tables()
        conn, cur = StudentProfileModel._get_conn_and_cursor()
        try:
            cur.execute('DELETE FROM documents WHERE id=%s AND user_id=%s', (document_id, user_id))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close()


class CertificateModel:
    @staticmethod
    def create(user_id, payload):
        StudentProfileModel.ensure_tables()
        document_id = None
        document_url = (payload.get('document_url') or '').strip()
        if document_url:
            document_id = DocumentModel.upsert(
                user_id=user_id,
                document_type='certificate',
                title=payload.get('title'),
                external_url=document_url,
                notes=payload.get('description'),
            )
        conn, cur = StudentProfileModel._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                INSERT INTO certificates (
                    user_id, document_id, title, issuer, issue_date, expiry_date,
                    credential_id, credential_url, description
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''',
                (
                    user_id,
                    document_id,
                    payload.get('title'),
                    payload.get('issuer'),
                    payload.get('issue_date') or None,
                    payload.get('expiry_date') or None,
                    payload.get('credential_id'),
                    payload.get('credential_url'),
                    payload.get('description'),
                ),
            )
            conn.commit()
            StudentProfileModel._sync_legacy_certificates(user_id)
            return cur.lastrowid
        finally:
            cur.close()

    @staticmethod
    def update(user_id, certificate_id, payload):
        StudentProfileModel.ensure_tables()
        conn, cur = StudentProfileModel._get_conn_and_cursor()
        try:
            cur.execute(
                'SELECT document_id FROM certificates WHERE id=%s AND user_id=%s',
                (certificate_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                return False
            document_id = row[0]
            document_url = (payload.get('document_url') or '').strip()
            if document_url:
                document_id = DocumentModel.upsert(
                    user_id=user_id,
                    document_type='certificate',
                    title=payload.get('title'),
                    external_url=document_url,
                    notes=payload.get('description'),
                    document_id=document_id,
                )
            elif document_id:
                DocumentModel.delete(user_id, document_id)
                document_id = None
            cur.execute(
                '''
                UPDATE certificates
                SET document_id=%s,
                    title=%s,
                    issuer=%s,
                    issue_date=%s,
                    expiry_date=%s,
                    credential_id=%s,
                    credential_url=%s,
                    description=%s
                WHERE id=%s AND user_id=%s
                ''',
                (
                    document_id,
                    payload.get('title'),
                    payload.get('issuer'),
                    payload.get('issue_date') or None,
                    payload.get('expiry_date') or None,
                    payload.get('credential_id'),
                    payload.get('credential_url'),
                    payload.get('description'),
                    certificate_id,
                    user_id,
                ),
            )
            conn.commit()
            StudentProfileModel._sync_legacy_certificates(user_id)
            return True
        finally:
            cur.close()

    @staticmethod
    def delete(user_id, certificate_id):
        StudentProfileModel.ensure_tables()
        conn, cur = StudentProfileModel._get_conn_and_cursor()
        try:
            cur.execute('SELECT document_id FROM certificates WHERE id=%s AND user_id=%s', (certificate_id, user_id))
            row = cur.fetchone()
            if not row:
                return False
            document_id = row[0]
            cur.execute('DELETE FROM certificates WHERE id=%s AND user_id=%s', (certificate_id, user_id))
            if document_id:
                cur.execute('DELETE FROM documents WHERE id=%s AND user_id=%s', (document_id, user_id))
            conn.commit()
            StudentProfileModel._sync_legacy_certificates(user_id)
            return True
        finally:
            cur.close()


class ResumeProfileModel:
    @staticmethod
    def get_by_user(user_id):
        return StudentProfileModel._get_resume_profile(user_id)

    @staticmethod
    def save(user_id, payload):
        StudentProfileModel.ensure_tables()
        existing = StudentProfileModel._get_resume_profile(user_id)
        document_id = existing['resume_document_id'] if existing else None
        document_url = (payload.get('document_url') or '').strip()
        headline = payload.get('headline') or 'Resume'
        if document_url:
            document_id = DocumentModel.upsert(
                user_id=user_id,
                document_type='resume',
                title=headline,
                external_url=document_url,
                notes=payload.get('summary'),
                document_id=document_id,
            )
        elif document_id:
            DocumentModel.delete(user_id, document_id)
            document_id = None

        conn, cur = StudentProfileModel._get_conn_and_cursor()
        try:
            if existing:
                cur.execute(
                    '''
                    UPDATE resume_profiles
                    SET resume_document_id=%s,
                        headline=%s,
                        summary=%s,
                        current_city=%s,
                        preferred_role=%s,
                        linkedin_url=%s,
                        github_url=%s
                    WHERE user_id=%s
                    ''',
                    (
                        document_id,
                        payload.get('headline'),
                        payload.get('summary'),
                        payload.get('current_city'),
                        payload.get('preferred_role'),
                        payload.get('linkedin_url'),
                        payload.get('github_url'),
                        user_id,
                    ),
                )
            else:
                cur.execute(
                    '''
                    INSERT INTO resume_profiles (
                        user_id, resume_document_id, headline, summary, current_city,
                        preferred_role, linkedin_url, github_url
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''',
                    (
                        user_id,
                        document_id,
                        payload.get('headline'),
                        payload.get('summary'),
                        payload.get('current_city'),
                        payload.get('preferred_role'),
                        payload.get('linkedin_url'),
                        payload.get('github_url'),
                    ),
                )
            conn.commit()
            StudentProfileModel._sync_legacy_resume(user_id)
            return True
        finally:
            cur.close()

    @staticmethod
    def delete(user_id):
        StudentProfileModel.ensure_tables()
        existing = StudentProfileModel._get_resume_profile(user_id)
        conn, cur = StudentProfileModel._get_conn_and_cursor()
        try:
            cur.execute('DELETE FROM resume_profiles WHERE user_id=%s', (user_id,))
            if existing and existing.get('resume_document_id'):
                cur.execute('DELETE FROM documents WHERE id=%s AND user_id=%s', (existing['resume_document_id'], user_id))
            conn.commit()
            StudentProfileModel._sync_legacy_resume(user_id)
            return True
        finally:
            cur.close()


class SocialLinkModel:
    @staticmethod
    def create(user_id, payload):
        StudentProfileModel.ensure_tables()
        conn, cur = StudentProfileModel._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                INSERT INTO user_social_links (user_id, platform, username, profile_url)
                VALUES (%s, %s, %s, %s)
                ''',
                (user_id, payload.get('platform'), payload.get('username'), payload.get('profile_url')),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            cur.close()




    @staticmethod
    def update(user_id, social_link_id, payload):
        StudentProfileModel.ensure_tables()
        conn, cur = StudentProfileModel._get_conn_and_cursor()
        try:
            cur.execute('SELECT id FROM user_social_links WHERE id=%s AND user_id=%s', (social_link_id, user_id))
            if not cur.fetchone():
                return False
            cur.execute(
                '''
                UPDATE user_social_links
                SET platform=%s, username=%s, profile_url=%s
                WHERE id=%s AND user_id=%s
                ''',
                (
                    payload.get('platform'),
                    payload.get('username'),
                    payload.get('profile_url'),
                    social_link_id,
                    user_id,
                ),
            )
            conn.commit()
            return True
        finally:
            cur.close()

    @staticmethod
    def delete(user_id, social_link_id):
        StudentProfileModel.ensure_tables()
        conn, cur = StudentProfileModel._get_conn_and_cursor()
        try:
            cur.execute('DELETE FROM user_social_links WHERE id=%s AND user_id=%s', (social_link_id, user_id))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close()
            


    
