import json

from services.db import get_conn


class OrganizationModel:
    TYPE_OPTIONS = [
        ('college', 'College'),
        ('company', 'Company'),
        ('venue', 'Venue'),
        ('hospital', 'Hospital'),
        ('school', 'School'),
        ('training_institute', 'Training Institute'),
    ]
    DB_TYPE_MAP = {
        'college': 'college',
        'company': 'company',
        'venue': 'venue',
        'hospital': 'company',
        'school': 'college',
        'training_institute': 'college',
    }
    TYPE_LABELS = dict(TYPE_OPTIONS)

    @staticmethod
    def _cursor():
        conn = get_conn()
        return conn, conn.cursor()

    @staticmethod
    def _safe_text(value):
        return (value or '').strip()

    @classmethod
    def _table_exists(cls, table_name):
        conn, cur = cls._cursor()
        try:
            cur.execute('SHOW TABLES LIKE %s', (table_name,))
            return cur.fetchone() is not None
        finally:
            cur.close()

    @classmethod
    def _safe_count(cls, table_name, where_clause='', params=None):
        if not cls._table_exists(table_name):
            return 0
        conn, cur = cls._cursor()
        try:
            query = f'SELECT COUNT(*) FROM {table_name}'
            if where_clause:
                query += f' WHERE {where_clause}'
            cur.execute(query, params or [])
            row = cur.fetchone()
            return row[0] if row else 0
        except Exception:
            return 0
        finally:
            cur.close()

    @classmethod
    def _safe_fetchall(cls, query, params=None):
        conn, cur = cls._cursor()
        try:
            cur.execute(query, params or [])
            return cur.fetchall()
        except Exception:
            return []
        finally:
            cur.close()

    @classmethod
    def _safe_fetchone(cls, query, params=None):
        conn, cur = cls._cursor()
        try:
            cur.execute(query, params or [])
            return cur.fetchone()
        except Exception:
            return None
        finally:
            cur.close()

    @classmethod
    def _build_metadata(cls, form_data, legacy_address=''):
        address = cls._safe_text(form_data.get('address')) or cls._safe_text(legacy_address)
        org_type = cls._safe_text(form_data.get('organization_type') or form_data.get('type')) or 'company'
        metadata = {
            'address': address,
            'organization_type': org_type,
            'contact_person': cls._safe_text(form_data.get('contact_person')),
            'mobile': cls._safe_text(form_data.get('mobile')),
            'email': cls._safe_text(form_data.get('email')),
            'status': cls._safe_text(form_data.get('status')) or 'active',
        }
        return json.dumps(metadata, ensure_ascii=True)

    @staticmethod
    def _parse_address_blob(raw_value):
        if not raw_value:
            return {'address': '', 'organization_type': '', 'contact_person': '', 'mobile': '', 'email': '', 'status': 'active'}
        if isinstance(raw_value, bytes):
            raw_value = raw_value.decode('utf-8', errors='ignore')
        text = raw_value.strip()
        if not text:
            return {'address': '', 'organization_type': '', 'contact_person': '', 'mobile': '', 'email': '', 'status': 'active'}
        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                payload.setdefault('address', '')
                payload.setdefault('organization_type', '')
                payload.setdefault('contact_person', '')
                payload.setdefault('mobile', '')
                payload.setdefault('email', '')
                payload.setdefault('status', 'active')
                return payload
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
        return {'address': text, 'organization_type': '', 'contact_person': '', 'mobile': '', 'email': '', 'status': 'active'}

    @classmethod
    def _row_to_dict(cls, row):
        metadata = cls._parse_address_blob(row[4])
        org_type = metadata.get('organization_type') or row[3] or ''
        status = metadata.get('status') or 'active'
        return {
            'id': row[0],
            'uuid': row[1],
            'name': row[2],
            'db_type': row[3],
            'organization_type': org_type,
            'organization_type_label': cls.TYPE_LABELS.get(org_type, org_type.replace('_', ' ').title()),
            'address': metadata.get('address', ''),
            'city': row[5] or '',
            'state': row[6] or '',
            'contact_person': metadata.get('contact_person', ''),
            'mobile': metadata.get('mobile', ''),
            'email': metadata.get('email', ''),
            'status': status,
            'is_active': 1 if status == 'active' else 0,
            'created_at': row[7],
        }

    @classmethod
    def get_dashboard_stats(cls):
        monthly_revenue = 0
        active_subscriptions = 0

        if cls._table_exists('payment_transactions'):
            row = cls._safe_fetchone(
                '''
                SELECT COALESCE(SUM(amount), 0)
                FROM payment_transactions
                WHERE status IN ('paid', 'success', 'completed')
                  AND YEAR(created_at) = YEAR(CURRENT_DATE())
                  AND MONTH(created_at) = MONTH(CURRENT_DATE())
                '''
            )
            monthly_revenue = float(row[0]) if row and row[0] is not None else 0
        elif cls._table_exists('payments'):
            row = cls._safe_fetchone(
                '''
                SELECT COALESCE(SUM(amount), 0)
                FROM payments
                WHERE status IN ('paid', 'success', 'completed')
                  AND YEAR(created_at) = YEAR(CURRENT_DATE())
                  AND MONTH(created_at) = MONTH(CURRENT_DATE())
                '''
            )
            monthly_revenue = float(row[0]) if row and row[0] is not None else 0

        if cls._table_exists('organization_subscriptions'):
            active_subscriptions += cls._safe_count('organization_subscriptions', "status='active'")
        if cls._table_exists('user_subscriptions'):
            active_subscriptions += cls._safe_count('user_subscriptions', "status='active'")
        if active_subscriptions == 0 and cls._table_exists('subscriptions'):
            active_subscriptions = cls._safe_count('subscriptions', "status='active'")

        return {
            'total_orgs': cls._safe_count('organizations'),
            'total_branches': cls._safe_count('org_branches'),
            'total_departments': cls._safe_count('org_departments'),
            'total_users': cls._safe_count('users'),
            'total_qr': cls._safe_count('qr_tokens'),
            'total_scans': cls._safe_count('scan_logs'),
            'total_active_subscriptions': active_subscriptions,
            'monthly_revenue': monthly_revenue,
        }

    @classmethod
    def get_recent_activity(cls, limit=10):
        activities = []

        if cls._table_exists('scan_logs'):
            scan_rows = cls._safe_fetchall(
                '''
                SELECT sl.id, u.name, sl.scanned_at, sl.ip_address
                FROM scan_logs sl
                LEFT JOIN users u ON u.id = sl.user_id
                ORDER BY sl.scanned_at DESC
                LIMIT %s
                ''',
                (limit,),
            )
            for row in scan_rows:
                activities.append({
                    'type': 'QR Scan',
                    'subject': row[1] or 'Unknown User',
                    'description': f"QR scanned from {row[3] or 'unknown IP'}",
                    'created_at': row[2],
                })

        if cls._table_exists('organizations'):
            org_rows = cls._safe_fetchall(
                '''
                SELECT id, name, city, created_at
                FROM organizations
                ORDER BY created_at DESC
                LIMIT %s
                ''',
                (limit,),
            )
            for row in org_rows:
                activities.append({
                    'type': 'Organization',
                    'subject': row[1],
                    'description': f"Organization added in {row[2] or 'N/A'}",
                    'created_at': row[3],
                })

        if cls._table_exists('users'):
            user_rows = cls._safe_fetchall(
                '''
                SELECT id, name, user_type, created_at
                FROM users
                ORDER BY created_at DESC
                LIMIT %s
                ''',
                (limit,),
            )
            for row in user_rows:
                activities.append({
                    'type': 'User',
                    'subject': row[1],
                    'description': f"New {row[2]} registered",
                    'created_at': row[3],
                })

        activities.sort(key=lambda item: item['created_at'] or '', reverse=True)
        return activities[:limit]

    @classmethod
    def get_latest_users(cls, limit=8):
        if not cls._table_exists('users'):
            return []
        rows = cls._safe_fetchall(
            '''
            SELECT id, name, email, user_type, is_active, created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT %s
            ''',
            (limit,),
        )
        return [
            {
                'id': row[0],
                'name': row[1],
                'email': row[2] or '-',
                'user_type': row[3],
                'is_active': row[4],
                'created_at': row[5],
            }
            for row in rows
        ]

    @classmethod
    def get_latest_organizations(cls, limit=8):
        if not cls._table_exists('organizations'):
            return []
        rows = cls._safe_fetchall(
            '''
            SELECT id, uuid, name, type, address_line1, city, state, created_at
            FROM organizations
            ORDER BY created_at DESC
            LIMIT %s
            ''',
            (limit,),
        )
        return [cls._row_to_dict(row) for row in rows]

    @classmethod
    def get_qr_scan_statistics(cls):
        if not cls._table_exists('scan_logs'):
            return {'labels': [], 'values': [], 'total': 0}
        rows = cls._safe_fetchall(
            '''
            SELECT DATE_FORMAT(scanned_at, '%%Y-%%m') AS month_label, COUNT(*)
            FROM scan_logs
            WHERE scanned_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 5 MONTH)
            GROUP BY DATE_FORMAT(scanned_at, '%%Y-%%m')
            ORDER BY month_label ASC
            '''
        )
        labels = [row[0] for row in rows]
        values = [row[1] for row in rows]
        return {'labels': labels, 'values': values, 'total': sum(values)}

    @classmethod
    def list_paginated(cls, search=None, page=1, per_page=10):
        conn, cur = cls._cursor()
        try:
            where = ''
            params = []
            if search:
                like = f"%{search.strip()}%"
                where = ' WHERE name LIKE %s OR city LIKE %s OR state LIKE %s OR address_line1 LIKE %s'
                params = [like, like, like, like]

            cur.execute(f'SELECT COUNT(*) FROM organizations{where}', params)
            total = cur.fetchone()[0]

            offset = max(page - 1, 0) * per_page
            query = (
                'SELECT id, uuid, name, type, address_line1, city, state, created_at '
                f'FROM organizations{where} ORDER BY id DESC LIMIT %s OFFSET %s'
            )
            cur.execute(query, params + [per_page, offset])
            rows = cur.fetchall()
            items = [cls._row_to_dict(row) for row in rows]
            total_pages = max((total + per_page - 1) // per_page, 1)
            return {'items': items, 'total': total, 'page': page, 'per_page': per_page, 'total_pages': total_pages}
        finally:
            cur.close()

    @classmethod
    def get_by_id(cls, org_id):
        conn, cur = cls._cursor()
        try:
            cur.execute(
                'SELECT id, uuid, name, type, address_line1, city, state, created_at FROM organizations WHERE id=%s',
                (org_id,),
            )
            row = cur.fetchone()
            return cls._row_to_dict(row) if row else None
        finally:
            cur.close()

    @classmethod
    def create(cls, form_data):
        conn, cur = cls._cursor()
        try:
            name = cls._safe_text(form_data.get('name'))
            org_type = cls._safe_text(form_data.get('organization_type')) or 'company'
            db_type = cls.DB_TYPE_MAP.get(org_type, 'company')
            city = cls._safe_text(form_data.get('city'))
            state = cls._safe_text(form_data.get('state'))
            address_blob = cls._build_metadata(form_data)
            cur.execute(
                'INSERT INTO organizations (uuid, name, type, address_line1, city, state) VALUES (UUID(), %s, %s, %s, %s, %s)',
                (name, db_type, address_blob, city, state),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            cur.close()

    @classmethod
    def update(cls, org_id, form_data):
        existing = cls.get_by_id(org_id)
        if not existing:
            return False
        conn, cur = cls._cursor()
        try:
            name = cls._safe_text(form_data.get('name'))
            org_type = cls._safe_text(form_data.get('organization_type')) or existing['organization_type'] or 'company'
            db_type = cls.DB_TYPE_MAP.get(org_type, existing['db_type'] or 'company')
            city = cls._safe_text(form_data.get('city'))
            state = cls._safe_text(form_data.get('state'))
            address_blob = cls._build_metadata(form_data, legacy_address=existing.get('address', ''))
            cur.execute(
                'UPDATE organizations SET name=%s, type=%s, address_line1=%s, city=%s, state=%s WHERE id=%s',
                (name, db_type, address_blob, city, state, org_id),
            )
            conn.commit()
            return True
        finally:
            cur.close()

    @classmethod
    def toggle_status(cls, org_id):
        org = cls.get_by_id(org_id)
        if not org:
            return None
        new_status = 'inactive' if org['status'] == 'active' else 'active'
        payload = {
            'address': org.get('address', ''),
            'organization_type': org.get('organization_type', org.get('db_type', 'company')),
            'contact_person': org.get('contact_person', ''),
            'mobile': org.get('mobile', ''),
            'email': org.get('email', ''),
            'status': new_status,
        }
        conn, cur = cls._cursor()
        try:
            cur.execute('UPDATE organizations SET address_line1=%s WHERE id=%s', (json.dumps(payload, ensure_ascii=True), org_id))
            cur.execute(
                'UPDATE organization_members SET is_active=%s WHERE organization_id=%s',
                (1 if new_status == 'active' else 0, org_id),
            )
            conn.commit()
            return new_status
        finally:
            cur.close()

    @classmethod
    def delete(cls, org_id):
        conn, cur = cls._cursor()
        try:
            cur.execute(
                '''
                DELETE d FROM org_divisions d
                INNER JOIN org_departments dep ON dep.id = d.department_id
                INNER JOIN org_branches b ON b.id = dep.branch_id
                WHERE b.organization_id = %s
                ''',
                (org_id,),
            )
            cur.execute(
                '''
                DELETE dep FROM org_departments dep
                INNER JOIN org_branches b ON b.id = dep.branch_id
                WHERE b.organization_id = %s
                ''',
                (org_id,),
            )
            cur.execute('DELETE FROM org_branches WHERE organization_id=%s', (org_id,))
            cur.execute('DELETE FROM organization_members WHERE organization_id=%s', (org_id,))
            cur.execute('DELETE FROM organizations WHERE id=%s', (org_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close()

    @classmethod
    def get_branch_summary(cls, org_id):
        conn, cur = cls._cursor()
        try:
            cur.execute(
                '''
                SELECT
                    b.id,
                    b.uuid,
                    b.name,
                    b.code,
                    b.city,
                    b.is_active,
                    COUNT(DISTINCT dep.id) AS department_count,
                    COUNT(DISTINCT divs.id) AS division_count
                FROM org_branches b
                LEFT JOIN org_departments dep ON dep.branch_id = b.id
                LEFT JOIN org_divisions divs ON divs.department_id = dep.id
                WHERE b.organization_id=%s
                GROUP BY b.id, b.uuid, b.name, b.code, b.city, b.is_active
                ORDER BY b.id DESC
                ''',
                (org_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    'id': row[0],
                    'uuid': row[1],
                    'name': row[2],
                    'code': row[3] or '',
                    'city': row[4] or '',
                    'is_active': row[5],
                    'department_count': row[6],
                    'division_count': row[7],
                }
                for row in rows
            ]
        finally:
            cur.close()
