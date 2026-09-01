import math

from werkzeug.security import generate_password_hash, check_password_hash
from services.db import get_conn
from models.card_permission import CardPermissionModel

class UserModel:
    MANAGED_USER_TYPES = ('student', 'employee', 'emergency', 'freelancer', 'visitor', 'citizen')

    @staticmethod
    def _get_conn_and_cursor():
        conn = get_conn()
        cur = conn.cursor()
        return conn, cur

    @staticmethod
    def create(user):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute(
            """
            INSERT INTO users (user_type, name, mobile, email, password_hash, photo, education, skills, resume, certificates, company_name, designation, experience, emergency_contact, blood_group, medical_notes, address, vehicle_number, qr_token, qr_path)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                user.get('user_type'), user.get('name'), user.get('mobile'), user.get('email'),
                generate_password_hash(user.get('password')), user.get('photo'), user.get('education'),
                user.get('skills'), user.get('resume'), user.get('certificates'), user.get('company_name'),
                user.get('designation'), user.get('experience'), user.get('emergency_contact'), user.get('blood_group'),
                user.get('medical_notes'), user.get('address'), user.get('vehicle_number'), user.get('qr_token'), user.get('qr_path')
            )
        )
        db_conn.commit()
        uid = cur.lastrowid
        cur.close()
        return uid

    @staticmethod
    def find_by_email(email):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute('SELECT id, email, password_hash, is_active, user_type, name FROM users WHERE email=%s', (email,))
        row = cur.fetchone()
        cur.close()
        return row

    @staticmethod
    def find_by_mobile(mobile):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute('SELECT id, email, password_hash, is_active, user_type, name, mobile FROM users WHERE mobile=%s', (mobile,))
        row = cur.fetchone()
        cur.close()
        return row

    @staticmethod
    def find_accounts_by_mobile(mobile):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute(
            'SELECT id, name, email, user_type, is_active, mobile FROM users WHERE mobile=%s ORDER BY id ASC',
            (mobile,),
        )
        rows = cur.fetchall()
        cur.close()
        return rows

    @staticmethod
    def update_password(mobile, new_password):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute(
            'UPDATE users SET password_hash=%s WHERE mobile=%s',
            (generate_password_hash(new_password), mobile),
        )
        db_conn.commit()
        cur.close()

    @staticmethod
    def update_password_by_id(user_id, new_password):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute(
            'UPDATE users SET password_hash=%s WHERE id=%s',
            (generate_password_hash(new_password), user_id),
        )
        db_conn.commit()
        cur.close()

    @staticmethod
    def find_by_id(uid):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute('SELECT * FROM users WHERE id=%s', (uid,))
        row = cur.fetchone()
        cur.close()
        return row

    @staticmethod
    def find_by_qr_token(token):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute('SELECT * FROM users WHERE qr_token=%s', (token,))
        row = cur.fetchone()
        cur.close()
        return row

    @staticmethod
    def update_qr(uid, token, path):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute('UPDATE users SET qr_token=%s, qr_path=%s WHERE id=%s', (token, path, uid))
        db_conn.commit()
        cur.close()

    @staticmethod
    def check_password(stored_hash, password):
        return check_password_hash(stored_hash, password)

    @staticmethod
    def list_users(search=None):
        db_conn, cur = UserModel._get_conn_and_cursor()
        base_query = '''
            SELECT
                u.id,
                u.name,
                u.email,
                u.user_type,
                u.is_active,
                u.created_at,
                COALESCE(sl.scan_count, 0) * 1024 AS data_usage,
                u.subscription_start_date,
                u.subscription_expiry_date,
                DATEDIFF(u.subscription_expiry_date, CURRENT_DATE) AS remaining_days,
                COALESCE(u.subscription_status, 'Suspended') AS subscription_status
            FROM users u
            LEFT JOIN (
                SELECT user_id, COUNT(*) AS scan_count
                FROM scan_logs
                GROUP BY user_id
            ) sl ON sl.user_id = u.id
        '''
        if search:
            q = f"%{search}%"
            cur.execute(base_query + ' WHERE u.name LIKE %s OR u.email LIKE %s', (q, q))
        else:
            cur.execute(base_query)
        rows = cur.fetchall()
        cur.close()
        return rows

    @staticmethod
    def find_org_admin_by_email(email):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute(
            '''
            SELECT
                u.id,
                u.email,
                u.password_hash,
                u.is_active,
                u.user_type,
                u.name,
                om.organization_id,
                o.name
            FROM users u
            INNER JOIN organization_members om ON om.user_id = u.id
            INNER JOIN organizations o ON o.id = om.organization_id
            WHERE u.email=%s AND u.user_type='admin' AND om.is_active=1
            ORDER BY om.id ASC
            LIMIT 1
            ''',
            (email,),
        )
        row = cur.fetchone()
        cur.close()
        return row

    @staticmethod
    def organization_has_primary_admin(org_id):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute(
            '''
            SELECT COUNT(*)
            FROM organization_members om
            INNER JOIN users u ON u.id = om.user_id
            WHERE om.organization_id=%s AND om.is_active=1 AND u.user_type='admin'
            ''',
            (org_id,),
        )
        count = cur.fetchone()[0]
        cur.close()
        return count > 0

    @staticmethod
    def get_primary_admin(org_id):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute(
            '''
            SELECT u.id, u.name, u.email, u.mobile, u.is_active, u.created_at
            FROM organization_members om
            INNER JOIN users u ON u.id = om.user_id
            WHERE om.organization_id=%s AND om.is_active=1 AND u.user_type='admin'
            ORDER BY om.id ASC
            LIMIT 1
            ''',
            (org_id,),
        )
        row = cur.fetchone()
        cur.close()
        return row

    @staticmethod
    def create_organization_admin(org_id, user):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute(
            """
            INSERT INTO users (user_type, name, mobile, email, password_hash, photo, education, skills, resume, certificates, company_name, designation, experience, emergency_contact, blood_group, medical_notes, address, vehicle_number, qr_token, qr_path)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                'admin',
                user.get('name'),
                user.get('mobile'),
                user.get('email'),
                generate_password_hash(user.get('password')),
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                user.get('address'),
                None,
                None,
                None,
            )
        )
        user_id = cur.lastrowid
        cur.execute(
            'INSERT INTO organization_members (organization_id, user_id, is_active) VALUES (%s, %s, 1)',
            (org_id, user_id),
        )
        db_conn.commit()
        cur.close()
        return user_id

    @staticmethod
    def get_org_context(org_id):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute('SELECT id, name FROM organizations WHERE id=%s', (org_id,))
        row = cur.fetchone()
        cur.close()
        return row

    @staticmethod
    def get_org_branches(org_id):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute(
            'SELECT id, name, code FROM org_branches WHERE organization_id=%s AND is_active=1 ORDER BY name ASC',
            (org_id,),
        )
        rows = cur.fetchall()
        cur.close()
        return rows

    @staticmethod
    def get_org_departments(org_id):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute(
            '''
            SELECT d.id, d.name, d.code, b.name
            FROM org_departments d
            INNER JOIN org_branches b ON b.id = d.branch_id
            WHERE b.organization_id=%s AND d.is_active=1
            ORDER BY b.name ASC, d.name ASC
            ''',
            (org_id,),
        )
        rows = cur.fetchall()
        cur.close()
        return rows

    @staticmethod
    def get_org_dashboard_stats(org_id):
        db_conn, cur = UserModel._get_conn_and_cursor()
        stats = {
            'total_students': 0,
            'total_employees': 0,
            'total_emergency_profiles': 0,
            'total_qr_cards': 0,
            'total_scans': 0,
        }
        cur.execute(
            '''
            SELECT u.user_type, COUNT(*)
            FROM users u
            INNER JOIN organization_members om ON om.user_id = u.id
            WHERE om.organization_id=%s AND om.is_active=1 AND u.user_type IN ('student','employee','emergency')
            GROUP BY u.user_type
            ''',
            (org_id,),
        )
        for user_type, total in cur.fetchall():
            if user_type == 'student':
                stats['total_students'] = total
            elif user_type == 'employee':
                stats['total_employees'] = total
            elif user_type == 'emergency':
                stats['total_emergency_profiles'] = total

        cur.execute(
            '''
            SELECT COUNT(*)
            FROM users u
            INNER JOIN organization_members om ON om.user_id = u.id
            WHERE om.organization_id=%s AND om.is_active=1 AND u.qr_token IS NOT NULL AND u.qr_token <> ''
            ''',
            (org_id,),
        )
        stats['total_qr_cards'] = cur.fetchone()[0]

        cur.execute(
            '''
            SELECT COUNT(*)
            FROM scan_logs sl
            INNER JOIN organization_members om ON om.user_id = sl.user_id
            WHERE om.organization_id=%s AND om.is_active=1
            ''',
            (org_id,),
        )
        stats['total_scans'] = cur.fetchone()[0]
        cur.close()
        return stats

    @staticmethod
    def get_recent_org_registrations(org_id, limit=10):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute(
            '''
            SELECT u.id, u.name, u.email, u.user_type, u.created_at
            FROM users u
            INNER JOIN organization_members om ON om.user_id = u.id
            WHERE om.organization_id=%s AND om.is_active=1 AND u.user_type IN ('student','employee','emergency','freelancer','visitor','citizen')
            ORDER BY u.created_at DESC
            LIMIT %s
            ''',
            (org_id, limit),
        )
        rows = cur.fetchall()
        cur.close()
        return rows

    @staticmethod
    def get_org_scan_statistics(org_id):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute(
            '''
            SELECT DATE_FORMAT(sl.scanned_at, '%%Y-%%m') AS month_label, COUNT(*)
            FROM scan_logs sl
            INNER JOIN organization_members om ON om.user_id = sl.user_id
            WHERE om.organization_id=%s AND om.is_active=1
              AND sl.scanned_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 5 MONTH)
            GROUP BY DATE_FORMAT(sl.scanned_at, '%%Y-%%m')
            ORDER BY month_label ASC
            ''',
            (org_id,),
        )
        rows = cur.fetchall()
        cur.close()
        labels = [row[0] for row in rows]
        values = [row[1] for row in rows]
        return {'labels': labels, 'values': values, 'total': sum(values)}

    @staticmethod
    def list_org_users(org_id, user_type=None, search=None):
        db_conn, cur = UserModel._get_conn_and_cursor()
        params = [org_id]
        where = " WHERE om.organization_id=%s AND om.is_active=1 AND u.user_type IN ('student','employee','emergency','freelancer','visitor','citizen')"
        if user_type:
            where += ' AND u.user_type=%s'
            params.append(user_type)
        if search:
            where += ' AND (u.name LIKE %s OR u.email LIKE %s OR u.mobile LIKE %s)'
            like = f'%{search}%'
            params.extend([like, like, like])
        cur.execute(
            '''
            SELECT
                u.id,
                u.name,
                u.email,
                u.mobile,
                u.user_type,
                u.company_name,
                u.designation,
                u.qr_token,
                u.is_active,
                u.created_at
            FROM users u
            INNER JOIN organization_members om ON om.user_id = u.id
            ''' + where + '''
            ORDER BY u.created_at DESC
            ''',
            params,
        )
        rows = cur.fetchall()
        cur.close()
        return rows

    @staticmethod
    def list_org_users_paginated(org_id, user_type=None, search=None, status=None, qr_status=None, page=1, per_page=10):
        db_conn, cur = UserModel._get_conn_and_cursor()
        params = [org_id]
        where = " WHERE om.organization_id=%s AND om.is_active=1 AND u.user_type IN ('student','employee','emergency','freelancer','visitor','citizen')"
        if user_type:
            where += ' AND u.user_type=%s'
            params.append(user_type)
        if search:
            like = f'%{search}%'
            where += ' AND (u.name LIKE %s OR u.email LIKE %s OR u.mobile LIKE %s OR u.company_name LIKE %s OR u.designation LIKE %s)'
            params.extend([like, like, like, like, like])
        if status in ('active', 'inactive'):
            where += ' AND u.is_active=%s'
            params.append(1 if status == 'active' else 0)
        if qr_status == 'generated':
            where += " AND u.qr_token IS NOT NULL AND u.qr_token <> ''"
        elif qr_status == 'pending':
            where += " AND (u.qr_token IS NULL OR u.qr_token = '')"

        cur.execute(
            'SELECT COUNT(*) FROM users u INNER JOIN organization_members om ON om.user_id=u.id ' + where,
            params,
        )
        total = cur.fetchone()[0]
        offset = max(page - 1, 0) * per_page
        cur.execute(
            '''
            SELECT
                u.id,
                u.name,
                u.email,
                u.mobile,
                u.user_type,
                u.company_name,
                u.designation,
                u.qr_token,
                u.is_active,
                u.created_at,
                u.photo
            FROM users u
            INNER JOIN organization_members om ON om.user_id = u.id
            ''' + where + '''
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
            ''',
            params + [per_page, offset],
        )
        rows = cur.fetchall()
        cur.close()
        total_pages = max(math.ceil(total / per_page), 1)
        return {'items': rows, 'total': total, 'page': page, 'per_page': per_page, 'total_pages': total_pages}

    @staticmethod
    def get_org_user(org_id, uid):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute(
            '''
            SELECT u.*
            FROM users u
            INNER JOIN organization_members om ON om.user_id = u.id
            WHERE om.organization_id=%s AND om.is_active=1 AND u.id=%s
              AND u.user_type IN ('student','employee','emergency','freelancer','visitor','citizen')
            LIMIT 1
            ''',
            (org_id, uid),
        )
        row = cur.fetchone()
        cur.close()
        return row

    @staticmethod
    def create_org_user(org_id, user):
        user_id = UserModel.create(user)
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute(
            'INSERT INTO organization_members (organization_id, user_id, is_active) VALUES (%s, %s, 1)',
            (org_id, user_id),
        )
        db_conn.commit()
        cur.close()
        CardPermissionModel.set_user_card_type(user_id, user.get('card_user_type') or user.get('user_type'))
        CardPermissionModel.assign_defaults_for_user(user_id)
        return user_id

    @staticmethod
    def update_org_user(org_id, uid, user):
        existing = UserModel.get_org_user(org_id, uid)
        if not existing:
            return False
        db_conn, cur = UserModel._get_conn_and_cursor()
        params = [
            user.get('name'),
            user.get('mobile'),
            user.get('email'),
            user.get('photo'),
            user.get('education'),
            user.get('company_name'),
            user.get('designation'),
            user.get('experience'),
            user.get('emergency_contact'),
            user.get('blood_group'),
            user.get('medical_notes'),
            user.get('address'),
            user.get('vehicle_number'),
            uid,
        ]
        query = '''
            UPDATE users
            SET name=%s,
                mobile=%s,
                email=%s,
                photo=%s,
                education=%s,
                company_name=%s,
                designation=%s,
                experience=%s,
                emergency_contact=%s,
                blood_group=%s,
                medical_notes=%s,
                address=%s,
                vehicle_number=%s
        '''
        password = user.get('password')
        if password:
            query += ', password_hash=%s'
            params.insert(-1, generate_password_hash(password))
        query += ' WHERE id=%s'
        cur.execute(query, params)
        db_conn.commit()
        cur.close()
        return True

    @staticmethod
    def delete_org_user(org_id, uid):
        row = UserModel.get_org_user(org_id, uid)
        if not row:
            return False
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute('DELETE FROM organization_members WHERE organization_id=%s AND user_id=%s', (org_id, uid))
        cur.execute("DELETE FROM users WHERE id=%s AND user_type IN ('student','employee','emergency','freelancer','visitor','citizen')", (uid,))
        db_conn.commit()
        cur.close()
        return True

    @staticmethod
    def delete_user(uid):
        db_conn, cur = UserModel._get_conn_and_cursor()
        # remove any organization membership links first
        cur.execute('DELETE FROM organization_members WHERE user_id=%s', (uid,))
        # remove the user record
        cur.execute('DELETE FROM users WHERE id=%s', (uid,))
        db_conn.commit()
        cur.close()
        return True

    @staticmethod
    def list_org_qr_cards(org_id):
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute(
            '''
            SELECT u.id, u.name, u.email, u.user_type, u.qr_token, u.qr_path, u.created_at
            FROM users u
            INNER JOIN organization_members om ON om.user_id = u.id
            WHERE om.organization_id=%s AND om.is_active=1
              AND u.user_type IN ('student','employee','emergency','freelancer','visitor','citizen')
            ORDER BY u.created_at DESC
            ''',
            (org_id,),
        )
        rows = cur.fetchall()
        cur.close()
        return rows

    @staticmethod
    def set_active_status(org_id, uid, is_active):
        row = UserModel.get_org_user(org_id, uid)
        if not row:
            return False
        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute('UPDATE users SET is_active=%s WHERE id=%s', (1 if is_active else 0, uid))
        db_conn.commit()
        cur.close()
        return True

    @staticmethod
    def user_display_code(uid):
        return f"LSQ-{uid:06d}"
