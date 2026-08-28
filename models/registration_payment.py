import json
from datetime import datetime
from io import StringIO
import csv

from services.db import get_conn


class RegistrationPaymentModel:
    USER_TYPES = ('student', 'employee', 'general_user', 'organization')
    LABELS = {
        'student': 'Student',
        'employee': 'Employee',
        'general_user': 'General User',
        'organization': 'Organization',
    }
    DEFAULT_PRICES = {
        'student': 99,
        'employee': 149,
        'general_user': 79,
        'organization': 499,
    }

    class PaymentStatus:
        SUCCESS = "success"
        PAID = "paid"
        PENDING = "pending"
        FAILED = "failed"
        CANCELLED = "cancelled"

    class RegistrationStatus:
        COMPLETED = "completed"
        INCOMPLETE = "incomplete"
        PAYMENT_PENDING = "payment_pending"
        NOT_STARTED = "not_started"

    @classmethod
    def registration_status_sql(cls):
        return """CASE
            WHEN rp.user_id IS NOT NULL THEN 'completed'
            WHEN rp.payment_status = 'paid' AND rp.razorpay_payment_id IS NOT NULL THEN 'incomplete'
            WHEN rp.payment_status = 'pending' THEN 'payment_pending'
            ELSE 'not_started'
        END"""

    @staticmethod
    def verified_payment_sql():
        return "(payment_status = 'paid' AND razorpay_payment_id IS NOT NULL AND razorpay_signature IS NOT NULL)"

    @staticmethod
    def normalize_user_type(user_type):
        if user_type == 'general':
            return 'general_user'
        if user_type in RegistrationPaymentModel.USER_TYPES:
            return user_type
        return None

    @classmethod
    def ensure_tables(cls):
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS registration_pricing (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_type VARCHAR(50) NOT NULL UNIQUE,
                    amount_rupees DECIMAL(10,2) NOT NULL DEFAULT 0,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    updated_by INT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS registration_payments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_token VARCHAR(128) NOT NULL UNIQUE,
                    user_id INT NULL,
                    user_type VARCHAR(50) NOT NULL,
                    mobile VARCHAR(50) NOT NULL,
                    amount_rupees DECIMAL(10,2) NOT NULL,
                    amount_paise INT NOT NULL,
                    otp_status VARCHAR(30) NOT NULL DEFAULT 'pending',
                    surepass_client_id VARCHAR(255) NULL,
                    razorpay_order_id VARCHAR(255) NULL,
                    razorpay_payment_id VARCHAR(255) NULL,
                    razorpay_signature VARCHAR(255) NULL,
                    payment_status VARCHAR(30) NOT NULL DEFAULT 'pending',
                    status VARCHAR(30) NOT NULL DEFAULT 'otp_pending',
                    metadata TEXT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    KEY idx_registration_payments_mobile (mobile),
                    KEY idx_registration_payments_order (razorpay_order_id),
                    KEY idx_registration_payments_user_id (user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            for user_type, amount in cls.DEFAULT_PRICES.items():
                cur.execute(
                    '''
                    INSERT INTO registration_pricing (user_type, amount_rupees, is_active)
                    VALUES (%s, %s, 1)
                    ON DUPLICATE KEY UPDATE user_type=VALUES(user_type)
                    ''',
                    (user_type, amount),
                )
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def list_pricing(cls):
        cls.ensure_tables()
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute('SELECT user_type, amount_rupees, is_active, updated_at FROM registration_pricing ORDER BY FIELD(user_type, "student", "employee", "general_user", "organization")')
            rows = cur.fetchall()
            pricing = {row[0]: {'amount': row[1], 'is_active': row[2], 'updated_at': row[3]} for row in rows}
            return [
                {
                    'user_type': user_type,
                    'label': cls.LABELS[user_type],
                    'amount': pricing.get(user_type, {}).get('amount', cls.DEFAULT_PRICES[user_type]),
                    'is_active': pricing.get(user_type, {}).get('is_active', 1),
                    'updated_at': pricing.get(user_type, {}).get('updated_at'),
                }
                for user_type in cls.USER_TYPES
            ]
        finally:
            cur.close()

    @classmethod
    def get_price(cls, user_type):
        cls.ensure_tables()
        user_type = cls.normalize_user_type(user_type)
        if not user_type:
            return None
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute('SELECT amount_rupees FROM registration_pricing WHERE user_type=%s AND is_active=1', (user_type,))
            row = cur.fetchone()
            return float(row[0]) if row else None
        finally:
            cur.close()

    @classmethod
    def update_prices(cls, form, updated_by=None):
        cls.ensure_tables()
        conn = get_conn()
        cur = conn.cursor()
        try:
            for user_type in cls.USER_TYPES:
                amount = float(form.get(f'amount_{user_type}') or 0)
                cur.execute(
                    '''
                    INSERT INTO registration_pricing (user_type, amount_rupees, is_active, updated_by)
                    VALUES (%s, %s, 1, %s)
                    ON DUPLICATE KEY UPDATE amount_rupees=VALUES(amount_rupees), is_active=1, updated_by=VALUES(updated_by)
                    ''',
                    (user_type, amount, updated_by),
                )
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def create_attempt(cls, session_token, user_type, mobile, amount_rupees):
        cls.ensure_tables()
        amount_paise = int(round(float(amount_rupees) * 100))
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                '''
                INSERT INTO registration_payments (session_token, user_type, mobile, amount_rupees, amount_paise, status)
                VALUES (%s, %s, %s, %s, %s, 'otp_pending')
                ON DUPLICATE KEY UPDATE user_type=VALUES(user_type), mobile=VALUES(mobile), amount_rupees=VALUES(amount_rupees), amount_paise=VALUES(amount_paise)
                ''',
                (session_token, user_type, mobile, amount_rupees, amount_paise),
            )
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def get_attempt(cls, session_token):
        cls.ensure_tables()
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                '''
                SELECT id, session_token, user_id, user_type, mobile, amount_rupees, amount_paise,
                       otp_status, surepass_client_id, razorpay_order_id, razorpay_payment_id,
                       razorpay_signature, payment_status, status, metadata
                FROM registration_payments
                WHERE session_token=%s
                LIMIT 1
                ''',
                (session_token,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                'id': row[0],
                'session_token': row[1],
                'user_id': row[2],
                'user_type': row[3],
                'mobile': row[4],
                'amount_rupees': float(row[5]),
                'amount_paise': int(row[6]),
                'otp_status': row[7],
                'surepass_client_id': row[8],
                'razorpay_order_id': row[9],
                'razorpay_payment_id': row[10],
                'razorpay_signature': row[11],
                'payment_status': row[12],
                'status': row[13],
                'metadata': json.loads(row[14]) if row[14] else {},
            }
        finally:
            cur.close()

    @staticmethod
    def update_attempt(session_token, **fields):
        if not fields:
            return
        allowed = {
            'user_id', 'otp_status', 'surepass_client_id', 'razorpay_order_id',
            'razorpay_payment_id', 'razorpay_signature', 'payment_status',
            'status', 'metadata',
        }
        updates = []
        params = []
        for key, value in fields.items():
            if key not in allowed:
                continue
            updates.append(f'{key}=%s')
            params.append(json.dumps(value) if key == 'metadata' else value)
        if not updates:
            return
        params.append(session_token)
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute(f'UPDATE registration_payments SET {", ".join(updates)} WHERE session_token=%s', params)
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def get_all_user_types(cls):
        return list(cls.USER_TYPES)

    @classmethod
    def get_transactions_summary(cls):
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT
                    COUNT(id) AS total_transactions,
                    SUM(CASE WHEN {verified_payment} THEN 1 ELSE 0 END) AS successful_payments,
                    SUM(CASE WHEN payment_status = 'pending' THEN 1 ELSE 0 END) AS pending_payments,
                    SUM(CASE WHEN payment_status = 'failed' THEN 1 ELSE 0 END) AS failed_payments,
                    SUM(CASE WHEN {verified_payment} THEN amount_rupees ELSE 0 END) AS total_revenue,
                    SUM(CASE WHEN user_id IS NOT NULL THEN 1 ELSE 0 END) AS completed_registrations,
                    SUM(CASE WHEN user_id IS NULL AND payment_status = 'paid' AND razorpay_payment_id IS NOT NULL THEN 1 ELSE 0 END) AS incomplete_registrations
                FROM registration_payments
            """.format(verified_payment=cls.verified_payment_sql()), ())
            summary = cur.fetchone()
            return {
                'total_transactions': summary[0] or 0,
                'successful_payments': summary[1] or 0,
                'pending_payments': summary[2] or 0,
                'failed_payments': summary[3] or 0,
                'total_revenue': float(summary[4] or 0),
                'completed_registrations': summary[5] or 0,
                'incomplete_registrations': summary[6] or 0,
            }
        finally:
            cur.close()

    @classmethod
    def list_transactions_paginated(cls, page, per_page, filters, sort_by, sort_order):
        conn = get_conn()
        cur = conn.cursor()
        try:
            offset = (page - 1) * per_page
            
            where_clauses = []
            params = []
            registration_status_sql = cls.registration_status_sql()

            # Search
            search_query = filters.get('search_query')
            if search_query:
                where_clauses.append(
                    "(rp.id LIKE %s OR rp.razorpay_payment_id LIKE %s OR "
                    "rp.razorpay_order_id LIKE %s OR rp.mobile LIKE %s OR u.name LIKE %s)"
                )
                params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])
            
            # Payment Status Filter
            payment_status = filters.get('payment_status')
            if payment_status and payment_status != 'All':
                where_clauses.append("rp.payment_status = %s")
                params.append(payment_status.lower())

            # Registration Status Filter
            registration_status = filters.get('registration_status')
            if registration_status and registration_status != 'All':
                if registration_status == cls.RegistrationStatus.INCOMPLETE:
                    where_clauses.append(f"{registration_status_sql} = %s")
                    params.append(cls.RegistrationStatus.INCOMPLETE)
                else:
                    where_clauses.append(f"{registration_status_sql} = %s")
                    params.append(registration_status.lower())

            # User Type Filter
            user_type = filters.get('user_type')
            if user_type and user_type != 'All':
                where_clauses.append("rp.user_type = %s")
                params.append(user_type.lower())

            # Date Range Filter
            date_range = filters.get('date_range')
            if date_range == 'Today':
                where_clauses.append("DATE(rp.created_at) = CURDATE()")
            elif date_range == 'Last 7 Days':
                where_clauses.append("rp.created_at >= CURDATE() - INTERVAL 7 DAY")
            elif date_range == 'Last 30 Days':
                where_clauses.append("rp.created_at >= CURDATE() - INTERVAL 30 DAY")
            # Custom Range can be added here if needed in the future

            where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            # Sorting
            order_sql = ""
            if sort_by == 'latest_payment':
                order_sql = "ORDER BY rp.created_at DESC"
            elif sort_by == 'oldest_payment':
                order_sql = "ORDER BY rp.created_at ASC"
            elif sort_by == 'highest_amount':
                order_sql = "ORDER BY rp.amount_rupees DESC"
            elif sort_by == 'lowest_amount':
                order_sql = "ORDER BY rp.amount_rupees ASC"
            elif sort_by == 'registration_status':
                order_sql = f"ORDER BY {registration_status_sql} {'ASC' if sort_order == 'asc' else 'DESC'}"

            # Total count query
            cur.execute(f"""
                SELECT COUNT(rp.id)
                FROM registration_payments rp
                LEFT JOIN users u ON rp.user_id = u.id
                {where_sql}
            """, params)
            total_items = cur.fetchone()[0]

            # Main data query
            cur.execute(f"""
                SELECT
                    rp.id, rp.razorpay_payment_id, rp.razorpay_order_id, rp.user_id,
                    rp.user_type, rp.mobile, rp.amount_rupees, rp.payment_status, {registration_status_sql},
                    rp.created_at, rp.updated_at, u.name AS user_name, u.email AS user_email
                FROM registration_payments rp
                LEFT JOIN users u ON rp.user_id = u.id
                {where_sql}
                {order_sql}
                LIMIT %s OFFSET %s
            """, params + [per_page, offset])
            rows = cur.fetchall()

            transactions = []
            for row in rows:
                # Determine registration completed date safely
                registration_completed_date = None
                transactions.append({
                    'id': row[0],
                    'razorpay_payment_id': row[1],
                    'razorpay_order_id': row[2],
                    'user_id': row[3],
                    'user_type': row[4],
                    'mobile': row[5],
                    'amount_rupees': float(row[6]),
                    'payment_status': row[7],
                    'registration_status': row[8],
                    'payment_date': None,
                    'registration_completed_date': registration_completed_date,
                    'user_name': row[11] if row[11] else 'N/A',
                    'user_email': row[12] if row[12] else 'N/A',
                    'currency': 'INR', # Assuming INR for now
                })

            total_pages = (total_items + per_page - 1) // per_page

            return {
                'items': transactions,
                'total_items': total_items,
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1,
                'next_num': page + 1 if page < total_pages else None,
                'prev_num': page - 1 if page > 1 else None,
            }
        finally:
            cur.close()

    @classmethod
    def get_transaction_details(cls, transaction_id):
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute(""" 
                SELECT
                    rp.id, rp.user_id, rp.user_type, rp.mobile, rp.amount_rupees,
                    rp.amount_paise, rp.otp_status, rp.razorpay_order_id,
                    rp.razorpay_payment_id, rp.payment_status, {registration_status_sql},
                    rp.created_at, rp.updated_at, u.name AS user_name, u.email AS user_email
                FROM registration_payments rp
                LEFT JOIN users u ON rp.user_id = u.id
                WHERE rp.id = %s
            """.format(registration_status_sql=cls.registration_status_sql()), (transaction_id,))
            row = cur.fetchone()
            if not row:
                return None
            
            registration_completed_date = None
            return {
                'id': row[0],
                'user_id': row[1],
                'user_type': row[2],
                'mobile': row[3],
                'amount_rupees': float(row[4]),
                'amount_paise': int(row[5]),
                'otp_status': row[6],
                'razorpay_order_id': row[7],
                'razorpay_payment_id': row[8],
                'payment_status': row[9],
                'registration_status': row[10],
                'created_at': row[11],
                'updated_at': row[12],
                'user_name': row[13] if row[13] else 'N/A',
                'user_email': row[14] if row[14] else 'N/A',
                'currency': 'INR',
                'registration_completed_date': registration_completed_date,
            }
        finally:
            cur.close()

    @classmethod
    def export_transactions_to_csv(cls, filters, sort_by, sort_order):
        conn = get_conn()
        cur = conn.cursor()
        try:
            where_clauses = []
            params = []
            registration_status_sql = cls.registration_status_sql()

            # Search
            search_query = filters.get('search_query')
            if search_query:
                where_clauses.append(
                    "(rp.id LIKE %s OR rp.razorpay_payment_id LIKE %s OR "
                    "rp.razorpay_order_id LIKE %s OR rp.mobile LIKE %s OR u.name LIKE %s)"
                )
                params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])
            
            # Payment Status Filter
            payment_status = filters.get('payment_status')
            if payment_status and payment_status != 'All':
                where_clauses.append("rp.payment_status = %s")
                params.append(payment_status.lower())

            # Registration Status Filter
            registration_status = filters.get('registration_status')
            if registration_status and registration_status != 'All':
                if registration_status == cls.RegistrationStatus.INCOMPLETE:
                    where_clauses.append(f"{registration_status_sql} = %s")
                    params.append(cls.RegistrationStatus.INCOMPLETE)
                else:
                    where_clauses.append(f"{registration_status_sql} = %s")
                    params.append(registration_status.lower())

            # User Type Filter
            user_type = filters.get('user_type')
            if user_type and user_type != 'All':
                where_clauses.append("rp.user_type = %s")
                params.append(user_type.lower())

            # Date Range Filter
            date_range = filters.get('date_range')
            if date_range == 'Today':
                where_clauses.append("DATE(rp.created_at) = CURDATE()")
            elif date_range == 'Last 7 Days':
                where_clauses.append("rp.created_at >= CURDATE() - INTERVAL 7 DAY")
            elif date_range == 'Last 30 Days':
                where_clauses.append("rp.created_at >= CURDATE() - INTERVAL 30 DAY")

            where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            # Sorting
            order_sql = ""
            if sort_by == 'latest_payment':
                order_sql = "ORDER BY rp.created_at DESC"
            elif sort_by == 'oldest_payment':
                order_sql = "ORDER BY rp.created_at ASC"
            elif sort_by == 'highest_amount':
                order_sql = "ORDER BY rp.amount_rupees DESC"
            elif sort_by == 'lowest_amount':
                order_sql = "ORDER BY rp.amount_rupees ASC"
            elif sort_by == 'registration_status':
                order_sql = f"ORDER BY {registration_status_sql} {'ASC' if sort_order == 'asc' else 'DESC'}"

            cur.execute(f"""
                SELECT
                    rp.id, rp.razorpay_payment_id, rp.razorpay_order_id, u.name, rp.mobile,
                    rp.user_type, rp.amount_rupees, rp.payment_status, {registration_status_sql},
                    rp.created_at, rp.updated_at
                FROM registration_payments rp
                LEFT JOIN users u ON rp.user_id = u.id
                {where_sql}
                {order_sql}
            """, params)
            rows = cur.fetchall()

            output = StringIO()
            writer = csv.writer(output)

            # Headers
            writer.writerow([
                'Transaction ID', 'Razorpay Payment ID', 'Razorpay Order ID', 'User Name', 
                'Mobile Number', 'User Type', 'Amount', 'Currency', 'Payment Status', 
                'Registration Status', 'Payment Date', 'Registration Completion Date'
            ])

            for row in rows:
                registration_completed_date = None
                writer.writerow([
                    row[0], row[1], row[2], row[3] if row[3] else 'N/A', row[4], 
                    row[5], float(row[6]), 'INR', row[7], 
                    row[8], row[9].strftime('%Y-%m-%d %H:%M:%S'), ''
                ])
            
            return output
        finally:
            cur.close()

    @classmethod
    def get_recent_transactions(cls, limit=5):
        conn = get_conn()
        cur = conn.cursor()
        try:
            registration_status_sql = cls.registration_status_sql()
            cur.execute("""
                SELECT
                    rp.id, rp.razorpay_payment_id, rp.user_id,
                    rp.user_type, rp.mobile, rp.amount_rupees, rp.payment_status, {registration_status_sql},
                    rp.created_at, rp.updated_at, u.name AS user_name
                FROM registration_payments rp
                LEFT JOIN users u ON rp.user_id = u.id
                ORDER BY rp.created_at DESC
                LIMIT %s
                """.format(registration_status_sql=registration_status_sql), (limit,))
            rows = cur.fetchall()

            transactions = []
            for row in rows:
                registration_completed_date = None
                transactions.append({
                    'id': row[0],
                    'razorpay_payment_id': row[1],
                    'user_id': row[2],
                    'user_type': row[3],
                    'mobile': row[4],
                    'amount_rupees': float(row[5]),
                    'payment_status': row[6],
                    'registration_status': row[7],
                    'payment_date': None,
                    'registration_completed_date': registration_completed_date,
                    'user_name': row[10] if row[10] else 'N/A',
                    'currency': 'INR',
                })
            return transactions
        finally:
            cur.close()
