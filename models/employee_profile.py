from models.student_profile import (
    CertificateModel,
    DocumentModel,
    ProjectModel,
    ResumeProfileModel,
    SocialLinkModel,
    StudentProfileModel,
)


class EmployeeProfileModel(StudentProfileModel):
    SECTION_KEYS = (
        'basic_information',
        'company_information',
        'work_experience',
        'skills',
        'projects',
        'certificates',
        'resume',
        'social_links',
    )

    @classmethod
    def ensure_tables(cls):
        super().ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS employee_profiles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    organization_id INT NULL,
                    branch_id INT NULL,
                    department_id INT NULL,
                    company_name VARCHAR(255) NULL,
                    employee_code VARCHAR(100) NULL,
                    designation VARCHAR(255) NULL,
                    employment_type VARCHAR(100) NULL,
                    office_location VARCHAR(255) NULL,
                    joining_date DATE NULL,
                    professional_summary TEXT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_employee_profiles_user_id (user_id),
                    KEY idx_employee_profiles_organization_id (organization_id),
                    KEY idx_employee_profiles_branch_id (branch_id),
                    KEY idx_employee_profiles_department_id (department_id),
                    CONSTRAINT fk_employee_profiles_user
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    CONSTRAINT fk_employee_profiles_organization
                        FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL,
                    CONSTRAINT fk_employee_profiles_branch
                        FOREIGN KEY (branch_id) REFERENCES org_branches(id) ON DELETE SET NULL,
                    CONSTRAINT fk_employee_profiles_department
                        FOREIGN KEY (department_id) REFERENCES org_departments(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS experiences (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    organization_id INT NULL,
                    company_name VARCHAR(255) NOT NULL,
                    job_title VARCHAR(255) NOT NULL,
                    employment_type VARCHAR(100) NULL,
                    start_date DATE NULL,
                    end_date DATE NULL,
                    is_current TINYINT(1) NOT NULL DEFAULT 0,
                    location VARCHAR(255) NULL,
                    description TEXT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    KEY idx_experiences_user_id (user_id),
                    KEY idx_experiences_organization_id (organization_id),
                    CONSTRAINT fk_experiences_user
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    CONSTRAINT fk_experiences_organization
                        FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def has_employee_profile(cls, user_id):
        if not user_id:
            return False
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                'SELECT COUNT(*) FROM user_profile_selections WHERE user_id=%s AND profile_type=%s',
                (user_id, 'employee'),
            )
            if cur.fetchone()[0] > 0:
                return True
        except Exception:
            pass
        finally:
            cur.close()
        user = cls._get_user(user_id)
        return bool(user and user['user_type'] == 'employee')

    @classmethod
    def _get_employee_profile(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                SELECT id, user_id, organization_id, branch_id, department_id, company_name,
                       employee_code, designation, employment_type, office_location, joining_date,
                       professional_summary, created_at, updated_at
                FROM employee_profiles
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
                'company_name': row[5],
                'employee_code': row[6],
                'designation': row[7],
                'employment_type': row[8],
                'office_location': row[9],
                'joining_date': row[10].isoformat() if row[10] else '',
                'professional_summary': row[11],
                'created_at': row[12],
                'updated_at': row[13],
            }
        finally:
            cur.close()

    @classmethod
    def _list_experiences(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                SELECT id, company_name, job_title, employment_type, start_date, end_date,
                       is_current, location, description, created_at, updated_at
                FROM experiences
                WHERE user_id=%s
                ORDER BY is_current DESC, start_date DESC, created_at DESC, id DESC
                ''',
                (user_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    'id': row[0],
                    'company_name': row[1],
                    'job_title': row[2],
                    'employment_type': row[3],
                    'start_date': row[4].isoformat() if row[4] else '',
                    'end_date': row[5].isoformat() if row[5] else '',
                    'is_current': bool(row[6]),
                    'location': row[7],
                    'description': row[8],
                    'created_at': row[9],
                    'updated_at': row[10],
                }
                for row in rows
            ]
        finally:
            cur.close()

    @classmethod
    def _sync_legacy_company_fields(cls, user_id):
        profile = cls._get_employee_profile(user_id)
        latest_experience = cls._list_experiences(user_id)
        experience_summary = None
        if latest_experience:
            current = latest_experience[0]
            experience_summary = current['job_title']
            if current['company_name']:
                experience_summary = f"{current['job_title']} at {current['company_name']}"
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                UPDATE users
                SET company_name=%s, designation=%s, experience=%s
                WHERE id=%s
                ''',
                (
                    profile.get('company_name') if profile else None,
                    profile.get('designation') if profile else None,
                    experience_summary,
                    user_id,
                ),
            )
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def _build_sections(cls, user, employee_profile, experiences, projects, certificates, resume_profile, social_links):
        basic_completion = cls._completion([user['name'], user['mobile'], user['email'], user['address'], user['photo']])
        company_completion = cls._completion(
            [
                employee_profile['company_name'] if employee_profile else '',
                employee_profile['employee_code'] if employee_profile else '',
                employee_profile['designation'] if employee_profile else '',
                employee_profile['employment_type'] if employee_profile else '',
                employee_profile['office_location'] if employee_profile else '',
                employee_profile['joining_date'] if employee_profile else '',
            ]
        )
        experience_completion = 0
        if experiences:
            experience_completion = round(
                sum(
                    cls._completion(
                        [
                            experience['company_name'],
                            experience['job_title'],
                            experience['employment_type'],
                            experience['start_date'],
                            experience['location'],
                            experience['description'],
                        ]
                    )
                    for experience in experiences
                ) / len(experiences)
            )
        skills_completion = cls._completion([user['skills']])
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
        return [
            {'key': 'basic_information', 'title': 'Basic Information', 'completion': basic_completion},
            {'key': 'company_information', 'title': 'Company Information', 'completion': company_completion},
            {'key': 'work_experience', 'title': 'Work Experience', 'completion': experience_completion},
            {'key': 'skills', 'title': 'Skills', 'completion': skills_completion},
            {'key': 'projects', 'title': 'Projects', 'completion': project_completion},
            {'key': 'certificates', 'title': 'Certificates', 'completion': certificate_completion},
            {'key': 'resume', 'title': 'Resume', 'completion': resume_completion},
            {'key': 'social_links', 'title': 'Social Links', 'completion': social_completion},
        ]

    @classmethod
    def get_employee_dashboard_data(cls, user_id):
        cls.ensure_tables()
        user = cls._get_user(user_id)
        if not user:
            return None
        employee_profile = cls._get_employee_profile(user_id)
        experiences = cls._list_experiences(user_id)
        projects = cls._list_projects(user_id)
        certificates = cls._list_certificates(user_id)
        resume_profile = cls._get_resume_profile(user_id)
        social_links = cls._list_social_links(user_id)
        sections = cls._build_sections(
            user=user,
            employee_profile=employee_profile,
            experiences=experiences,
            projects=projects,
            certificates=certificates,
            resume_profile=resume_profile,
            social_links=social_links,
        )
        visible_section_keys = cls.get_visible_section_keys(user_id, 'employee')
        for section in sections:
            section['public_visible'] = section['key'] in visible_section_keys
        overall_completion = round(sum(section['completion'] for section in sections) / len(sections)) if sections else 0
        return {
            'user': user,
            'employee_profile': employee_profile or {},
            'experiences': experiences,
            'projects': projects,
            'certificates': certificates,
            'resume_profile': resume_profile or {},
            'social_links': social_links,
            'sections': sections,
            'visible_section_keys': visible_section_keys,
            'overall_completion': overall_completion,
        }

    @classmethod
    def update_company_information(cls, user_id, payload):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            organization_id = cls._get_user_organization_id(user_id)
            cur.execute('SELECT id FROM employee_profiles WHERE user_id=%s', (user_id,))
            row = cur.fetchone()
            values = (
                organization_id,
                payload.get('company_name'),
                payload.get('employee_code'),
                payload.get('designation'),
                payload.get('employment_type'),
                payload.get('office_location'),
                payload.get('joining_date') or None,
                payload.get('professional_summary'),
            )
            if row:
                cur.execute(
                    '''
                    UPDATE employee_profiles
                    SET organization_id=%s,
                        company_name=%s,
                        employee_code=%s,
                        designation=%s,
                        employment_type=%s,
                        office_location=%s,
                        joining_date=%s,
                        professional_summary=%s
                    WHERE user_id=%s
                    ''',
                    values + (user_id,),
                )
            else:
                cur.execute(
                    '''
                    INSERT INTO employee_profiles (
                        user_id, organization_id, company_name, employee_code, designation,
                        employment_type, office_location, joining_date, professional_summary
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''',
                    (user_id,) + values,
                )
            conn.commit()
            cls._sync_legacy_company_fields(user_id)
            return True
        finally:
            cur.close()

    @classmethod
    def clear_company_information(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute('DELETE FROM employee_profiles WHERE user_id=%s', (user_id,))
            conn.commit()
        finally:
            cur.close()
        cls._sync_legacy_company_fields(user_id)


class ExperienceModel(EmployeeProfileModel):
    @classmethod
    def create(cls, user_id, payload):
        cls.ensure_tables()
        organization_id = cls._get_user_organization_id(user_id)
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                INSERT INTO experiences (
                    user_id, organization_id, company_name, job_title, employment_type,
                    start_date, end_date, is_current, location, description
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''',
                (
                    user_id,
                    organization_id,
                    payload.get('company_name'),
                    payload.get('job_title'),
                    payload.get('employment_type'),
                    payload.get('start_date') or None,
                    payload.get('end_date') or None,
                    1 if payload.get('is_current') else 0,
                    payload.get('location'),
                    payload.get('description'),
                ),
            )
            conn.commit()
            cls._sync_legacy_company_fields(user_id)
            return cur.lastrowid
        finally:
            cur.close()

    @classmethod
    def update(cls, user_id, experience_id, payload):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute('SELECT id FROM experiences WHERE id=%s AND user_id=%s', (experience_id, user_id))
            if not cur.fetchone():
                return False
            cur.execute(
                '''
                UPDATE experiences
                SET company_name=%s,
                    job_title=%s,
                    employment_type=%s,
                    start_date=%s,
                    end_date=%s,
                    is_current=%s,
                    location=%s,
                    description=%s
                WHERE id=%s AND user_id=%s
                ''',
                (
                    payload.get('company_name'),
                    payload.get('job_title'),
                    payload.get('employment_type'),
                    payload.get('start_date') or None,
                    payload.get('end_date') or None,
                    1 if payload.get('is_current') else 0,
                    payload.get('location'),
                    payload.get('description'),
                    experience_id,
                    user_id,
                ),
            )
            conn.commit()
            cls._sync_legacy_company_fields(user_id)
            return True
        finally:
            cur.close()

    @classmethod
    def delete(cls, user_id, experience_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute('DELETE FROM experiences WHERE id=%s AND user_id=%s', (experience_id, user_id))
            conn.commit()
            deleted = cur.rowcount > 0
        finally:
            cur.close()
        cls._sync_legacy_company_fields(user_id)
        return deleted
