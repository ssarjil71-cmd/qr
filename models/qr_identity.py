import os

from flask import current_app

from services.db import get_conn
from services.qrcode_service import generate_qr_for_user, render_qr_to_path


class QRIdentityModel:
    PROFILE = 'profile'
    EMERGENCY = 'emergency'

    @staticmethod
    def _ensure_table():
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                '''
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
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )
            cur.execute('SHOW COLUMNS FROM qr_cards')
            existing = {row[0] for row in cur.fetchall()}
            if 'qr_type' not in existing:
                cur.execute("ALTER TABLE qr_cards ADD COLUMN qr_type VARCHAR(32) NOT NULL DEFAULT 'profile' AFTER user_id")
            conn.commit()
        finally:
            cur.close()

    @classmethod
    def find_by_user_and_type(cls, user_id, qr_type):
        cls._ensure_table()
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                '''
                SELECT id, user_id, qr_type, token, path, is_active, scan_count, last_scanned_at, created_at
                FROM qr_cards
                WHERE user_id=%s AND qr_type=%s AND is_active=1
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                ''',
                (user_id, qr_type),
            )
            return cur.fetchone()
        finally:
            cur.close()

    @classmethod
    def find_by_token_and_type(cls, token, qr_type):
        cls._ensure_table()
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                '''
                SELECT id, user_id, qr_type, token, path, is_active, scan_count, last_scanned_at, created_at
                FROM qr_cards
                WHERE token=%s AND qr_type=%s AND is_active=1
                LIMIT 1
                ''',
                (token, qr_type),
            )
            return cur.fetchone()
        finally:
            cur.close()

    @classmethod
    def ensure_for_user(cls, user_id, qr_type, url_template):
        card = cls.find_by_user_and_type(user_id, qr_type)
        if card and card[3] and card[4]:
            payload_url = url_template.replace('__TOKEN__', card[3])
            render_qr_to_path(payload_url, cls.file_path(card[4]), qr_type)
            return {'token': card[3], 'path': card[4]}

        token, path = generate_qr_for_user(user_id, url_template, prefix=f'{qr_type}_qr', qr_type=qr_type)
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                '''
                INSERT INTO qr_cards (user_id, qr_type, token, path, is_active)
                VALUES (%s, %s, %s, %s, 1)
                ''',
                (user_id, qr_type, token, path),
            )
            conn.commit()
        finally:
            cur.close()
        return {'token': token, 'path': path}

    @classmethod
    def increment_scan(cls, token, qr_type):
        cls._ensure_table()
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                '''
                UPDATE qr_cards
                SET scan_count=COALESCE(scan_count, 0)+1, last_scanned_at=CURRENT_TIMESTAMP
                WHERE token=%s AND qr_type=%s
                ''',
                (token, qr_type),
            )
            conn.commit()
        finally:
            cur.close()

    @staticmethod
    def file_path(relative_path):
        if not relative_path:
            return None
        return os.path.join(current_app.root_path, 'static', relative_path)
