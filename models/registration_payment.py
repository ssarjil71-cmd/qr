import json

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
