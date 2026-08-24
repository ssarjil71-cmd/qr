from functools import wraps

from flask import flash, redirect, request, session, url_for

from services.db import get_conn


class CardPermissionModel:
    USER_TYPE_OPTIONS = (
        ('student', 'Student', 'bi-mortarboard-fill'),
        ('employee', 'Employee', 'bi-briefcase-fill'),
        ('general_user', 'General User', 'bi-person-fill'),
        ('organization', 'Organization', 'bi-building-fill'),
    )

    DEFAULT_CARDS = (
        ('basic_information', 'Basic Information', 'Personal details, contact info, photo, and address.', 'bi-person-lines-fill', 1, 1),
        ('academic_information', 'Academic Information', 'College, branch, year, roll number, and student bio.', 'bi-mortarboard-fill', 2, 1),
        ('emergency_contact', 'Emergency Contact', 'Emergency contacts, doctor details, and safety notes.', 'bi-telephone-inbound-fill', 3, 1),
        ('medical_report', 'Medical Report', 'Health metrics, medical history, medicines, reports, and vaccinations.', 'bi-heart-pulse-fill', 4, 0),
        ('skills', 'Skills', 'Technical skills, soft skills, tools, and languages.', 'bi-stars', 5, 0),
        ('projects', 'Projects', 'Project portfolio, role, technologies, links, and descriptions.', 'bi-kanban-fill', 6, 0),
        ('certificates', 'Certificates', 'Credentials, certificates, issuers, and verification links.', 'bi-award-fill', 7, 0),
        ('upload_documents', 'Upload Documents', 'Student documents such as certificates, mark sheets, and PDFs.', 'bi-cloud-arrow-up-fill', 8, 0),
        ('resume', 'Resume', 'Resume summary, preferred role, profile links, and resume download.', 'bi-file-earmark-person-fill', 9, 1),
        ('social_links', 'Social Links', 'LinkedIn, GitHub, portfolio, and other public profile links.', 'bi-share-fill', 10, 0),
    )

    @staticmethod
    def _cursor():
        conn = get_conn()
        return conn, conn.cursor()

    @classmethod
    def ensure_tables(cls):
        conn, cur = cls._cursor()
        try:
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS card_features (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    card_key VARCHAR(100) NOT NULL UNIQUE,
                    card_name VARCHAR(255) NOT NULL,
                    description TEXT NULL,
                    icon VARCHAR(100) NULL,
                    display_order INT NOT NULL DEFAULT 0,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    is_default_enabled TINYINT(1) NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS user_card_permissions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    card_key VARCHAR(100) NOT NULL,
                    is_enabled TINYINT(1) NOT NULL DEFAULT 0,
                    is_required TINYINT(1) NOT NULL DEFAULT 0,
                    assigned_by INT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_user_card_permission (user_id, card_key),
                    KEY idx_user_card_permissions_user_id (user_id),
                    KEY idx_user_card_permissions_card_key (card_key),
                    CONSTRAINT fk_user_card_permissions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS user_type_card_permissions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_type VARCHAR(100) NOT NULL,
                    card_key VARCHAR(100) NOT NULL,
                    is_enabled TINYINT(1) NOT NULL DEFAULT 0,
                    is_required TINYINT(1) NOT NULL DEFAULT 0,
                    display_order INT NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_user_type_card_permission (user_type, card_key),
                    KEY idx_user_type_card_permissions_user_type (user_type),
                    KEY idx_user_type_card_permissions_card_key (card_key)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            try:
                cur.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS card_user_type VARCHAR(100) NULL')
            except Exception:
                pass
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS organization_card_permissions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    organization_id INT NOT NULL,
                    card_key VARCHAR(100) NOT NULL,
                    is_enabled TINYINT(1) NOT NULL DEFAULT 0,
                    is_required TINYINT(1) NOT NULL DEFAULT 0,
                    assigned_by INT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_org_card_permission (organization_id, card_key),
                    KEY idx_org_card_permissions_org_id (organization_id),
                    CONSTRAINT fk_org_card_permissions_org FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS card_assignment_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NULL,
                    organization_id INT NULL,
                    card_key VARCHAR(100) NOT NULL,
                    old_status VARCHAR(50) NULL,
                    new_status VARCHAR(50) NOT NULL,
                    changed_by INT NULL,
                    ip_address VARCHAR(100) NULL,
                    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    KEY idx_card_assignment_logs_user_id (user_id),
                    KEY idx_card_assignment_logs_org_id (organization_id),
                    KEY idx_card_assignment_logs_card_key (card_key)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            for key, name, description, icon, display_order, default_enabled in cls.DEFAULT_CARDS:
                cur.execute(
                    '''
                    INSERT INTO card_features (card_key, card_name, description, icon, display_order, is_active, is_default_enabled)
                    VALUES (%s, %s, %s, %s, %s, 1, %s)
                    ON DUPLICATE KEY UPDATE
                        card_name=VALUES(card_name),
                        description=VALUES(description),
                        icon=VALUES(icon),
                        display_order=VALUES(display_order)
                    ''',
                    (key, name, description, icon, display_order, default_enabled),
                )
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def normalize_card_user_type(cls, user_type):
        mapping = {
            'student': 'student',
            'employee': 'employee',
            'general_user': 'general_user',
            'organization': 'organization',
            'emergency': 'general_user',
            'citizen': 'general_user',
            'visitor': 'general_user',
        }
        return mapping.get((user_type or '').strip(), (user_type or 'general_user').strip())

    @classmethod
    def set_user_card_type(cls, user_id, card_user_type):
        cls.ensure_tables()
        conn, cur = cls._cursor()
        try:
            cur.execute('UPDATE users SET card_user_type=%s WHERE id=%s', (cls.normalize_card_user_type(card_user_type), user_id))
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def list_cards(cls):
        cls.ensure_tables()
        conn, cur = cls._cursor()
        try:
            cur.execute(
                '''
                SELECT card_key, card_name, description, icon, display_order, is_active, is_default_enabled
                FROM card_features
                WHERE is_active=1
                ORDER BY display_order ASC, card_name ASC
                '''
            )
            return [
                {
                    'key': row[0],
                    'name': row[1],
                    'description': row[2] or '',
                    'icon': row[3] or 'bi-grid',
                    'display_order': row[4],
                    'is_active': bool(row[5]),
                    'is_default_enabled': bool(row[6]),
                }
                for row in cur.fetchall()
            ]
        finally:
            cur.close()

    @classmethod
    def get_user_org_id(cls, user_id):
        conn, cur = cls._cursor()
        try:
            cur.execute('SELECT organization_id FROM organization_members WHERE user_id=%s AND is_active=1 ORDER BY id ASC LIMIT 1', (user_id,))
            row = cur.fetchone()
            return row[0] if row else None
        finally:
            cur.close()

    @classmethod
    def get_user_card_type(cls, user_id):
        cls.ensure_tables()
        conn, cur = cls._cursor()
        try:
            cur.execute('SELECT COALESCE(card_user_type, user_type) FROM users WHERE id=%s', (user_id,))
            row = cur.fetchone()
            return cls.normalize_card_user_type(row[0] if row else None)
        finally:
            cur.close()

    @classmethod
    def get_effective_permissions(cls, user_id):
        cards = cls.list_cards()
        org_id = cls.get_user_org_id(user_id)
        card_order = {card['key']: card['display_order'] for card in cards}
        defaults = {card['key']: {'is_enabled': card['is_default_enabled'], 'is_required': False, 'display_order': card['display_order'], 'source': 'System default'} for card in cards}
        conn, cur = cls._cursor()
        try:
            user_card_type = cls.get_user_card_type(user_id)
            cur.execute(
                'SELECT card_key, is_enabled, is_required, display_order FROM user_type_card_permissions WHERE user_type=%s',
                (user_card_type,),
            )
            for key, enabled, required, display_order in cur.fetchall():
                if key in defaults:
                    defaults[key] = {'is_enabled': bool(enabled), 'is_required': bool(required), 'display_order': display_order or card_order.get(key, 0), 'source': 'User type'}

            if org_id and not any(permission.get('source') == 'User type' for permission in defaults.values()):
                cur.execute('SELECT card_key, is_enabled, is_required FROM organization_card_permissions WHERE organization_id=%s', (org_id,))
                for key, enabled, required in cur.fetchall():
                    if key in defaults:
                        defaults[key] = {'is_enabled': bool(enabled), 'is_required': bool(required), 'display_order': card_order.get(key, 0), 'source': 'Organization'}
            cur.execute('SELECT COUNT(*) FROM user_card_permissions WHERE user_id=%s', (user_id,))
            has_user_override = (cur.fetchone()[0] or 0) > 0
            if not has_user_override:
                return defaults
            cur.execute('SELECT card_key, is_enabled, is_required FROM user_card_permissions WHERE user_id=%s', (user_id,))
            for key, enabled, required in cur.fetchall():
                if key in defaults:
                    defaults[key] = {'is_enabled': bool(enabled), 'is_required': bool(required), 'display_order': defaults[key].get('display_order', card_order.get(key, 0)), 'source': 'User override'}
            return defaults
        finally:
            cur.close()

    @classmethod
    def is_enabled(cls, user_id, card_key):
        return bool(cls.get_effective_permissions(user_id).get(card_key, {}).get('is_enabled'))

    @classmethod
    def assign_defaults_for_user(cls, user_id, assigned_by=None):
        cls.ensure_tables()
        return True

    @classmethod
    def list_user_type_summaries(cls):
        cls.ensure_tables()
        cards = cls.list_cards()
        total_cards = len(cards)
        conn, cur = cls._cursor()
        try:
            cur.execute(
                '''
                SELECT user_type, COUNT(CASE WHEN is_enabled=1 THEN 1 END)
                FROM user_type_card_permissions
                GROUP BY user_type
                '''
            )
            counts = {row[0]: row[1] or 0 for row in cur.fetchall()}
            return [
                {'key': key, 'label': label, 'icon': icon, 'assigned_count': counts.get(key, 0), 'total_cards': total_cards}
                for key, label, icon in cls.USER_TYPE_OPTIONS
            ]
        finally:
            cur.close()

    @classmethod
    def get_user_type_permissions(cls, user_type):
        normalized = cls.normalize_card_user_type(user_type)
        permissions = {card['key']: {'is_enabled': False, 'is_required': False, 'display_order': card['display_order']} for card in cls.list_cards()}
        conn, cur = cls._cursor()
        try:
            cur.execute(
                'SELECT card_key, is_enabled, is_required, display_order FROM user_type_card_permissions WHERE user_type=%s',
                (normalized,),
            )
            for key, enabled, required, display_order in cur.fetchall():
                permissions[key] = {'is_enabled': bool(enabled), 'is_required': bool(required), 'display_order': display_order}
            return permissions
        finally:
            cur.close()

    @classmethod
    def save_user_type_permissions(cls, user_type, form):
        normalized = cls.normalize_card_user_type(user_type)
        enabled_keys = set(form.getlist('enabled_cards'))
        required_keys = set(form.getlist('required_cards'))
        conn, cur = cls._cursor()
        try:
            for index, card in enumerate(cls.list_cards(), start=1):
                key = card['key']
                display_order = form.get(f'display_order_{key}', type=int) if hasattr(form, 'get') else None
                cur.execute(
                    '''
                    INSERT INTO user_type_card_permissions (user_type, card_key, is_enabled, is_required, display_order)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE is_enabled=VALUES(is_enabled), is_required=VALUES(is_required), display_order=VALUES(display_order)
                    ''',
                    (normalized, key, 1 if key in enabled_keys else 0, 1 if key in required_keys else 0, display_order or index),
                )
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def apply_user_type_to_existing_users(cls, user_type, mode='without_overrides', changed_by=None, ip_address=None):
        normalized = cls.normalize_card_user_type(user_type)
        permissions = cls.get_user_type_permissions(normalized)
        conn, cur = cls._cursor()
        try:
            cur.execute(
                '''
                SELECT id FROM users
                WHERE COALESCE(card_user_type, user_type)=%s
                   OR (%s='general_user' AND user_type IN ('emergency','citizen','visitor'))
                ''',
                (normalized, normalized),
            )
            user_ids = [row[0] for row in cur.fetchall()]
            updated = 0
            for user_id in user_ids:
                cur.execute('SELECT COUNT(*) FROM user_card_permissions WHERE user_id=%s', (user_id,))
                has_override = (cur.fetchone()[0] or 0) > 0
                if mode != 'force' and has_override:
                    continue
                for key, permission in permissions.items():
                    cur.execute(
                        '''
                        INSERT INTO user_card_permissions (user_id, card_key, is_enabled, is_required, assigned_by)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE is_enabled=VALUES(is_enabled), is_required=VALUES(is_required), assigned_by=VALUES(assigned_by)
                        ''',
                        (user_id, key, 1 if permission['is_enabled'] else 0, 1 if permission['is_required'] else 0, changed_by),
                    )
                updated += 1
            conn.commit()
            return updated
        finally:
            cur.close()

    @classmethod
    def save_user_permissions(cls, user_id, form, changed_by=None, ip_address=None):
        cls.ensure_tables()
        existing = cls.get_effective_permissions(user_id)
        cards = cls.list_cards()
        conn, cur = cls._cursor()
        try:
            for card in cards:
                key = card['key']
                enabled = key in form.getlist('enabled_cards')
                required = key in form.getlist('required_cards')
                old = existing.get(key, {})
                old_status = f"{'enabled' if old.get('is_enabled') else 'disabled'}:{'required' if old.get('is_required') else 'optional'}"
                new_status = f"{'enabled' if enabled else 'disabled'}:{'required' if required else 'optional'}"
                cur.execute(
                    '''
                    INSERT INTO user_card_permissions (user_id, card_key, is_enabled, is_required, assigned_by)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE is_enabled=VALUES(is_enabled), is_required=VALUES(is_required), assigned_by=VALUES(assigned_by)
                    ''',
                    (user_id, key, 1 if enabled else 0, 1 if required else 0, changed_by),
                )
                if old_status != new_status:
                    cur.execute(
                        '''
                        INSERT INTO card_assignment_logs (user_id, card_key, old_status, new_status, changed_by, ip_address)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ''',
                        (user_id, key, old_status, new_status, changed_by, ip_address),
                    )
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def save_org_permissions(cls, org_id, form, changed_by=None, ip_address=None, apply_existing=False):
        cls.ensure_tables()
        cards = cls.list_cards()
        conn, cur = cls._cursor()
        try:
            for card in cards:
                key = card['key']
                enabled = key in form.getlist('enabled_cards')
                required = key in form.getlist('required_cards')
                cur.execute(
                    '''
                    INSERT INTO organization_card_permissions (organization_id, card_key, is_enabled, is_required, assigned_by)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE is_enabled=VALUES(is_enabled), is_required=VALUES(is_required), assigned_by=VALUES(assigned_by)
                    ''',
                    (org_id, key, 1 if enabled else 0, 1 if required else 0, changed_by),
                )
                cur.execute(
                    '''
                    INSERT INTO card_assignment_logs (organization_id, card_key, old_status, new_status, changed_by, ip_address)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ''',
                    (org_id, key, None, 'enabled' if enabled else 'disabled', changed_by, ip_address),
                )
            if apply_existing:
                cur.execute('SELECT user_id FROM organization_members WHERE organization_id=%s AND is_active=1', (org_id,))
                user_ids = [row[0] for row in cur.fetchall()]
                conn.commit()
                for user_id in user_ids:
                    cls.save_user_permissions(user_id, form, changed_by, ip_address)
                return
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def set_system_defaults(cls, form):
        cls.ensure_tables()
        enabled_keys = set(form.getlist('default_enabled_cards'))
        conn, cur = cls._cursor()
        try:
            for card in cls.list_cards():
                cur.execute('UPDATE card_features SET is_default_enabled=%s WHERE card_key=%s', (1 if card['key'] in enabled_keys else 0, card['key']))
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def list_assignment_users(cls, filters):
        from models.student_profile import StudentProfileModel

        StudentProfileModel.ensure_tables()
        cls.ensure_tables()
        params = []
        where = " WHERE u.user_type IN ('student','employee','emergency','freelancer','visitor','citizen')"
        if filters.get('q'):
            like = f"%{filters['q']}%"
            where += ' AND (u.name LIKE %s OR u.email LIKE %s OR u.mobile LIKE %s)'
            params.extend([like, like, like])
        if filters.get('organization_id'):
            where += ' AND om.organization_id=%s'
            params.append(filters['organization_id'])
        if filters.get('branch_id'):
            where += ' AND sp.branch_id=%s'
            params.append(filters['branch_id'])
        if filters.get('department_id'):
            where += ' AND sp.department_id=%s'
            params.append(filters['department_id'])
        if filters.get('user_type'):
            where += ' AND u.user_type=%s'
            params.append(filters['user_type'])
        if filters.get('status') in ('active', 'inactive'):
            where += ' AND u.is_active=%s'
            params.append(1 if filters['status'] == 'active' else 0)
        conn, cur = cls._cursor()
        try:
            cur.execute(
                '''
                SELECT u.id, u.name, u.email, u.mobile, u.user_type, u.is_active, u.qr_token,
                       o.name, b.name, d.name,
                       COUNT(DISTINCT CASE WHEN ucp.is_enabled=1 THEN ucp.card_key END) AS assigned_count
                FROM users u
                LEFT JOIN organization_members om ON om.user_id = u.id AND om.is_active=1
                LEFT JOIN organizations o ON o.id = om.organization_id
                LEFT JOIN student_profiles sp ON sp.user_id = u.id
                LEFT JOIN org_branches b ON b.id = sp.branch_id
                LEFT JOIN org_departments d ON d.id = sp.department_id
                LEFT JOIN user_card_permissions ucp ON ucp.user_id = u.id
                ''' + where + '''
                GROUP BY u.id, u.name, u.email, u.mobile, u.user_type, u.is_active, u.qr_token, o.name, b.name, d.name
                ORDER BY u.created_at DESC
                LIMIT 200
                ''',
                params,
            )
            total_cards = len(cls.list_cards())
            return [
                {
                    'id': row[0], 'name': row[1], 'email': row[2], 'mobile': row[3], 'user_type': row[4],
                    'is_active': bool(row[5]), 'qr_status': 'Active' if row[6] else 'Pending',
                    'organization': row[7] or '-', 'branch': row[8] or '-', 'department': row[9] or '-',
                    'assigned_count': row[10] or 0, 'total_cards': total_cards,
                }
                for row in cur.fetchall()
            ]
        finally:
            cur.close()

    @classmethod
    def get_user_summary(cls, user_id):
        conn, cur = cls._cursor()
        try:
            cur.execute(
                '''
                SELECT u.id, u.name, u.email, u.mobile, u.user_type, u.photo, u.is_active, u.qr_token,
                       o.id, o.name, b.name, d.name
                FROM users u
                LEFT JOIN organization_members om ON om.user_id = u.id AND om.is_active=1
                LEFT JOIN organizations o ON o.id = om.organization_id
                LEFT JOIN student_profiles sp ON sp.user_id = u.id
                LEFT JOIN org_branches b ON b.id = sp.branch_id
                LEFT JOIN org_departments d ON d.id = sp.department_id
                WHERE u.id=%s
                LIMIT 1
                ''',
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                'id': row[0], 'name': row[1], 'email': row[2], 'mobile': row[3], 'user_type': row[4],
                'photo': row[5], 'is_active': bool(row[6]), 'qr_status': 'Active' if row[7] else 'Pending',
                'organization_id': row[8], 'organization': row[9] or '-', 'branch': row[10] or '-', 'department': row[11] or '-',
            }
        finally:
            cur.close()

    @classmethod
    def list_organizations(cls):
        conn, cur = cls._cursor()
        try:
            cur.execute('SELECT id, name FROM organizations ORDER BY name ASC')
            return [{'id': row[0], 'name': row[1]} for row in cur.fetchall()]
        finally:
            cur.close()

    @classmethod
    def get_org_permissions(cls, org_id):
        permissions = {card['key']: {'is_enabled': False, 'is_required': False} for card in cls.list_cards()}
        conn, cur = cls._cursor()
        try:
            cur.execute('SELECT card_key, is_enabled, is_required FROM organization_card_permissions WHERE organization_id=%s', (org_id,))
            for key, enabled, required in cur.fetchall():
                permissions[key] = {'is_enabled': bool(enabled), 'is_required': bool(required)}
            return permissions
        finally:
            cur.close()

    @classmethod
    def get_logs_for_user(cls, user_id, limit=25):
        cls.ensure_tables()
        conn, cur = cls._cursor()
        try:
            cur.execute(
                '''
                SELECT l.card_key, l.old_status, l.new_status, u.name, l.changed_at, l.ip_address
                FROM card_assignment_logs l
                LEFT JOIN users u ON u.id = l.changed_by
                WHERE l.user_id=%s
                ORDER BY l.changed_at DESC
                LIMIT %s
                ''',
                (user_id, limit),
            )
            return [{'card_key': r[0], 'old_status': r[1], 'new_status': r[2], 'changed_by': r[3] or 'Super Admin', 'changed_at': r[4], 'ip_address': r[5]} for r in cur.fetchall()]
        finally:
            cur.close()

    @classmethod
    def get_dashboard_stats(cls):
        cls.ensure_tables()
        conn, cur = cls._cursor()
        try:
            cur.execute('SELECT COUNT(*) FROM users WHERE is_active=1')
            active_users = cur.fetchone()[0]
            cur.execute('SELECT COUNT(*) FROM user_card_permissions WHERE is_enabled=1')
            cards_assigned = cur.fetchone()[0]
            cur.execute('SELECT COUNT(*) FROM user_card_permissions WHERE is_enabled=0')
            disabled_features = cur.fetchone()[0]
            cur.execute(
                '''
                SELECT cf.card_name, COUNT(ucp.user_id)
                FROM card_features cf
                LEFT JOIN user_card_permissions ucp ON ucp.card_key=cf.card_key AND ucp.is_enabled=1
                WHERE cf.is_active=1
                GROUP BY cf.card_key, cf.card_name, cf.display_order
                ORDER BY cf.display_order ASC
                '''
            )
            overview = [{'card_name': row[0], 'user_count': row[1]} for row in cur.fetchall()]
            return {'active_users': active_users, 'cards_assigned': cards_assigned, 'disabled_features': disabled_features, 'card_assignment_overview': overview}
        finally:
            cur.close()


def card_permission_required(card_key):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                flash('Login required', 'warning')
                return redirect(url_for('auth.login'))
            if not CardPermissionModel.is_enabled(user_id, card_key):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return {'success': False, 'message': 'Feature not available for this user'}, 403
                flash('Feature not available for this account', 'warning')
                return redirect(url_for('user.student_dashboard'))
            return func(*args, **kwargs)
        return wrapper
    return decorator
