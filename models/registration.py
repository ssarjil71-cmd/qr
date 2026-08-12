import json

from services.db import get_conn


class RegistrationModel:
    PROFILE_OPTIONS = (
        'student',
        'employee',
        'intern',
        'freelancer',
        'business_owner',
        'emergency',
        'visitor',
        'citizen',
    )
    PROFILE_LABELS = {
        'student': 'Student',
        'employee': 'Employee',
        'intern': 'Intern',
        'freelancer': 'Freelancer',
        'business_owner': 'Business Owner',
        'emergency': 'Emergency',
        'visitor': 'Visitor',
        'citizen': 'Citizen',
    }

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
                CREATE TABLE IF NOT EXISTS user_profile_selections (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    profile_type VARCHAR(50) NOT NULL,
                    profile_data LONGTEXT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_user_profile_selection (user_id, profile_type),
                    CONSTRAINT fk_user_profile_selections_user
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                '''
            )
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def get_selected_profiles(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                'SELECT profile_type FROM user_profile_selections WHERE user_id=%s ORDER BY id ASC',
                (user_id,),
            )
            return [row[0] for row in cur.fetchall()]
        finally:
            cur.close()

    @classmethod
    def save_selected_profiles(cls, user_id, profiles):
        cls.ensure_tables()
        filtered = [profile for profile in profiles if profile in cls.PROFILE_OPTIONS]
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                'SELECT profile_type, profile_data FROM user_profile_selections WHERE user_id=%s',
                (user_id,),
            )
            existing = {row[0]: row[1] for row in cur.fetchall()}

            for profile in filtered:
                if profile not in existing:
                    cur.execute(
                        'INSERT INTO user_profile_selections (user_id, profile_type, profile_data) VALUES (%s, %s, %s)',
                        (user_id, profile, json.dumps({}, ensure_ascii=True)),
                    )

            for profile in existing:
                if profile not in filtered:
                    cur.execute(
                        'DELETE FROM user_profile_selections WHERE user_id=%s AND profile_type=%s',
                        (user_id, profile),
                    )
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def get_profile_data_map(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                'SELECT profile_type, profile_data FROM user_profile_selections WHERE user_id=%s ORDER BY id ASC',
                (user_id,),
            )
            result = {}
            for profile_type, profile_data in cur.fetchall():
                try:
                    result[profile_type] = json.loads(profile_data) if profile_data else {}
                except (TypeError, ValueError, json.JSONDecodeError):
                    result[profile_type] = {}
            return result
        finally:
            cur.close()

    @classmethod
    def save_profile_details(cls, user_id, details_by_profile):
        cls.ensure_tables()
        conn, cur = cls._get_conn_and_cursor()
        try:
            for profile_type, payload in details_by_profile.items():
                if profile_type not in cls.PROFILE_OPTIONS:
                    continue
                cur.execute(
                    '''
                    UPDATE user_profile_selections
                    SET profile_data=%s
                    WHERE user_id=%s AND profile_type=%s
                    ''',
                    (json.dumps(payload, ensure_ascii=True), user_id, profile_type),
                )
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def sync_user_summary_fields(cls, user_id, details_by_profile):
        conn, cur = cls._get_conn_and_cursor()
        try:
            profile_priority = ['student', 'employee', 'intern', 'freelancer', 'business_owner', 'emergency', 'visitor', 'citizen']
            primary_type = 'citizen'
            for profile_type in profile_priority:
                if profile_type in details_by_profile:
                    if profile_type in ('student', 'employee', 'freelancer', 'emergency', 'visitor', 'citizen'):
                        primary_type = profile_type
                    elif profile_type == 'intern':
                        primary_type = 'employee'
                    elif profile_type == 'business_owner':
                        primary_type = 'freelancer'
                    break

            employee = details_by_profile.get('employee', {})
            student = details_by_profile.get('student', {})
            emergency = details_by_profile.get('emergency', {})
            freelancer = details_by_profile.get('freelancer', {})
            intern = details_by_profile.get('intern', {})
            business_owner = details_by_profile.get('business_owner', {})
            citizen = details_by_profile.get('citizen', {})

            education = student.get('college', '') if student else citizen.get('city', '')
            company_name = (
                employee.get('company')
                or intern.get('company')
                or business_owner.get('business_name')
                or ''
            )
            designation = (
                employee.get('designation')
                or freelancer.get('profession')
                or intern.get('department')
                or business_owner.get('business_type')
                or ''
            )
            experience = employee.get('experience') or intern.get('duration') or ''
            medical_notes = emergency.get('medical_notes') or ''
            blood_group = emergency.get('blood_group') or ''
            emergency_contact = emergency.get('emergency_contact') or ''

            cur.execute(
                '''
                UPDATE users
                SET user_type=%s,
                    education=%s,
                    company_name=%s,
                    designation=%s,
                    experience=%s,
                    blood_group=%s,
                    emergency_contact=%s,
                    medical_notes=%s
                WHERE id=%s
                ''',
                (
                    primary_type,
                    education,
                    company_name,
                    designation,
                    experience,
                    blood_group,
                    emergency_contact,
                    medical_notes,
                    user_id,
                ),
            )
            conn.commit()
        finally:
            cur.close()
