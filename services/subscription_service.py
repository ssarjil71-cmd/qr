from __future__ import annotations

import calendar
import logging
from datetime import date, datetime, timedelta

import MySQLdb.cursors
from flask import has_app_context

from services.db import get_conn

logger = logging.getLogger(__name__)

try:
    from services.registration_gateways import MSG91Gateway
except Exception:  # pragma: no cover - optional integration
    MSG91Gateway = None


def calculate_subscription_expiry(start_date):
    return SubscriptionService.calculate_subscription_expiry(start_date)


def get_subscription_status(reference_date, expiry_date):
    return SubscriptionService.get_subscription_status(reference_date, expiry_date)


class SubscriptionService:
    Status = {
        'ACTIVE': 'Active',
        'EXPIRING_SOON': 'Expiring Soon',
        'EXPIRED': 'Expired',
        'SUSPENDED': 'Suspended',
    }

    @staticmethod
    def _get_conn_and_cursor():
        conn = get_conn()
        cur = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
        return conn, cur

    @classmethod
    def ensure_schema(cls):
        if not has_app_context():
            raise RuntimeError('SubscriptionService.ensure_schema() must be called inside a Flask application context.')

        conn, cur = cls._get_conn_and_cursor()
        try:
            for column_name, column_sql in {
                'subscription_start_date': 'DATE NULL',
                'subscription_expiry_date': 'DATE NULL',
                'subscription_status': 'VARCHAR(30) NOT NULL DEFAULT "Suspended"',
            }.items():
                cur.execute(f"SHOW COLUMNS FROM users LIKE '{column_name}'")
                if cur.fetchone() is None:
                    cur.execute(f'ALTER TABLE users ADD COLUMN {column_name} {column_sql}')

            cur.execute(
                '''
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
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute(
                '''
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
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            for index_name, index_sql in {
                'idx_users_subscription_start_date': 'CREATE INDEX idx_users_subscription_start_date ON users (subscription_start_date)',
                'idx_users_subscription_expiry_date': 'CREATE INDEX idx_users_subscription_expiry_date ON users (subscription_expiry_date, subscription_status)',
            }.items():
                cur.execute('SHOW INDEX FROM users WHERE Key_name=%s', (index_name,))
                if cur.fetchone() is None:
                    cur.execute(index_sql)
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception('Subscription schema initialization failed')
            raise
        finally:
            cur.close()

    @staticmethod
    def today_date(as_of=None):
        if as_of is None:
            return date.today()
        if isinstance(as_of, datetime):
            return as_of.date()
        return as_of

    @staticmethod
    def calculate_subscription_expiry(start_date):
        if not start_date:
            return None
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        return SubscriptionService.add_calendar_years(start_date, 1)

    @staticmethod
    def add_calendar_years(base_date, years):
        if base_date is None:
            return None
        if isinstance(base_date, datetime):
            base_date = base_date.date()
        year = base_date.year + years
        month = base_date.month
        day = base_date.day
        last_day = calendar.monthrange(year, month)[1]
        safe_day = min(day, last_day)
        return date(year, month, safe_day)

    @staticmethod
    def add_calendar_months(base_date, months):
        if base_date is None:
            return None
        if isinstance(base_date, datetime):
            base_date = base_date.date()
        total_months = base_date.month - 1 + months
        year = base_date.year + (total_months // 12)
        month = (total_months % 12) + 1
        last_day = calendar.monthrange(year, month)[1]
        safe_day = min(base_date.day, last_day)
        return date(year, month, safe_day)

    @staticmethod
    def get_valid_quick_action_base(start_date, expiry_date):
        if expiry_date:
            return expiry_date if isinstance(expiry_date, date) else datetime.strptime(str(expiry_date), '%Y-%m-%d').date()
        if start_date:
            start = start_date if isinstance(start_date, date) else datetime.strptime(str(start_date), '%Y-%m-%d').date()
            return SubscriptionService.calculate_subscription_expiry(start)
        return None

    @staticmethod
    def get_subscription_status(reference_date, expiry_date):
        today = SubscriptionService.today_date(reference_date)
        if not expiry_date:
            return SubscriptionService.Status['SUSPENDED']
        expiry = expiry_date if isinstance(expiry_date, date) else datetime.strptime(str(expiry_date), '%Y-%m-%d').date()
        if today > expiry:
            return SubscriptionService.Status['EXPIRED']
        if expiry - today <= timedelta(days=2):
            return SubscriptionService.Status['EXPIRING_SOON']
        return SubscriptionService.Status['ACTIVE']

    @staticmethod
    def get_remaining_days(reference_date, expiry_date):
        today = SubscriptionService.today_date(reference_date)
        if not expiry_date:
            return 0
        expiry = expiry_date if isinstance(expiry_date, date) else datetime.strptime(str(expiry_date), '%Y-%m-%d').date()
        return max((expiry - today).days, 0)

    @classmethod
    def sync_user_subscription_status(cls, user_id):
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute('SELECT subscription_start_date, subscription_expiry_date FROM users WHERE id=%s', (user_id,))
            row = cur.fetchone()
            if not row:
                return None
            start_date, expiry_date = row['subscription_start_date'], row['subscription_expiry_date']
            status = cls.get_subscription_status(date.today(), expiry_date)
            cur.execute('UPDATE users SET subscription_status=%s WHERE id=%s', (status, user_id))
            conn.commit()
            return {'user_id': user_id, 'subscription_start_date': start_date, 'subscription_expiry_date': expiry_date, 'subscription_status': status}
        finally:
            cur.close()

    @classmethod
    def apply_subscription_for_registration(cls, user_id, start_date=None, changed_by=None):
        start = cls.today_date(start_date) if start_date else date.today()
        expiry = cls.calculate_subscription_expiry(start)
        status = cls.get_subscription_status(date.today(), expiry)
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                'UPDATE users SET subscription_start_date=%s, subscription_expiry_date=%s, subscription_status=%s WHERE id=%s',
                (start, expiry, status, user_id),
            )
            conn.commit()
            return {'user_id': user_id, 'subscription_start_date': start, 'subscription_expiry_date': expiry, 'subscription_status': status}
        finally:
            cur.close()

    @classmethod
    def set_manual_expiry_date(cls, user_id, new_expiry_date, changed_by=None, reason='manual_adjustment'):
        if not new_expiry_date:
            raise ValueError('Expiry date is required')
        if isinstance(new_expiry_date, str):
            new_expiry_date = datetime.strptime(new_expiry_date, '%Y-%m-%d').date()
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute('SELECT subscription_start_date, subscription_expiry_date FROM users WHERE id=%s', (user_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError('User not found')
            previous_expiry = row['subscription_expiry_date']
            start_date = row['subscription_start_date'] or date.today()
            status = cls.get_subscription_status(date.today(), new_expiry_date)
            cur.execute(
                'UPDATE users SET subscription_start_date=%s, subscription_expiry_date=%s, subscription_status=%s WHERE id=%s',
                (start_date, new_expiry_date, status, user_id),
            )
            cur.execute(
                '''
                INSERT INTO subscription_expiry_audit (user_id, previous_expiry_date, new_expiry_date, change_reason, changed_by)
                VALUES (%s, %s, %s, %s, %s)
                ''',
                (user_id, previous_expiry, new_expiry_date, reason, changed_by),
            )
            conn.commit()
            return {'user_id': user_id, 'subscription_start_date': start_date, 'subscription_expiry_date': new_expiry_date, 'subscription_status': status}
        finally:
            cur.close()

    @classmethod
    def get_user_subscription_summary(cls, user_id, as_of=None):
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                SELECT id, subscription_start_date, subscription_expiry_date, subscription_status
                FROM users WHERE id=%s
                ''',
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            today = cls.today_date(as_of)
            start_date = row['subscription_start_date']
            expiry_date = row['subscription_expiry_date']
            status = row['subscription_status'] or cls.get_subscription_status(today, expiry_date)
            if expiry_date:
                status = cls.get_subscription_status(today, expiry_date)
            return {
                'user_id': row['id'],
                'subscription_start_date': start_date,
                'subscription_expiry_date': expiry_date,
                'subscription_status': status,
                'remaining_days': cls.get_remaining_days(today, expiry_date),
                'is_active': status == cls.Status['ACTIVE'],
                'is_expiring_soon': status == cls.Status['EXPIRING_SOON'],
                'is_expired': status == cls.Status['EXPIRED'],
            }
        finally:
            cur.close()

    @staticmethod
    def get_reminder_dates_for_window(reference_date, expiry_date):
        today = SubscriptionService.today_date(reference_date)
        if not expiry_date:
            return []
        expiry = expiry_date if isinstance(expiry_date, date) else datetime.strptime(str(expiry_date), '%Y-%m-%d').date()
        if expiry < today:
            return []
        start = expiry - timedelta(days=2)
        if start < today:
            start = today
        days = []
        cursor = start
        while cursor <= expiry:
            days.append(cursor)
            cursor += timedelta(days=1)
        return days

    @classmethod
    def _find_users_for_daily_reminders(cls, reminder_date):
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                '''
                SELECT id, email, mobile, subscription_expiry_date, subscription_status
                FROM users
                WHERE subscription_expiry_date IS NOT NULL
                  AND subscription_expiry_date >= %s
                  AND subscription_expiry_date <= %s
                ORDER BY subscription_expiry_date ASC, id ASC
                ''',
                (reminder_date, reminder_date + timedelta(days=2)),
            )
            return cur.fetchall()
        finally:
            cur.close()

    @classmethod
    def has_reminder_been_sent(cls, user_id, reminder_date, reminder_type='expiry_warning'):
        conn, cur = cls._get_conn_and_cursor()
        try:
            cur.execute(
                'SELECT id FROM subscription_reminder_logs WHERE user_id=%s AND reminder_date=%s AND reminder_type=%s LIMIT 1',
                (user_id, reminder_date, reminder_type),
            )
            return cur.fetchone() is not None
        finally:
            cur.close()

    @staticmethod
    def _build_reminder_message(user, expiry_date, reminder_date):
        days_left = (expiry_date - reminder_date).days
        if days_left == 2:
            return f"Your QR-NexID subscription expires in 2 days on {expiry_date.strftime('%d %b %Y')}."
        if days_left == 1:
            return f"Your QR-NexID subscription expires tomorrow on {expiry_date.strftime('%d %b %Y')}."
        if days_left == 0:
            return f"Your QR-NexID subscription expires today ({expiry_date.strftime('%d %b %Y')})."
        return f"Your QR-NexID subscription will expire on {expiry_date.strftime('%d %b %Y')}."

    @classmethod
    def send_daily_reminders(cls, reminder_date=None):
        reminder_date = cls.today_date(reminder_date)
        conn, cur = cls._get_conn_and_cursor()
        try:
            users = cls._find_users_for_daily_reminders(reminder_date)
            for user in users:
                if cls.has_reminder_been_sent(user['id'], reminder_date):
                    continue
                expiry_date = user['subscription_expiry_date']
                if not expiry_date:
                    continue
                reminder_days = (expiry_date - reminder_date).days
                if reminder_days < 0 or reminder_days > 2:
                    continue
                message = cls._build_reminder_message(user, expiry_date, reminder_date)
                notification_status = 'logged'
                notification_channel = 'internal'
                if MSG91Gateway is not None:
                    try:
                        MSG91Gateway.send_sms(user.get('mobile'), message)
                        notification_status = 'sent'
                        notification_channel = 'sms'
                    except Exception as exc:
                        notification_status = 'failed'
                        logger.warning('Subscription reminder failed for user %s: %s', user['id'], exc)
                cur.execute(
                    '''
                    INSERT INTO subscription_reminder_logs (user_id, reminder_date, reminder_type, notification_channel, notification_status, message, sent_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    ''',
                    (user['id'], reminder_date, 'expiry_warning', notification_channel, notification_status, message),
                )
                conn.commit()
        finally:
            cur.close()

    @staticmethod
    def start_background_jobs(app):
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
        except Exception:
            return None

        scheduler = getattr(app, 'subscription_scheduler', None)
        if scheduler is not None:
            if not scheduler.running:
                scheduler.start()
            return scheduler

        def run_subscription_reminders():
            with app.app_context():
                SubscriptionService.send_daily_reminders(date.today())

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            run_subscription_reminders,
            'interval',
            days=1,
            id='qrnexid-subscription-reminders',
            replace_existing=True,
        )
        scheduler.start()
        app.subscription_scheduler = scheduler
        return scheduler
