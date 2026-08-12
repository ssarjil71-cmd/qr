from services.db import get_conn
import os
import qrcode
from flask import current_app


class QrCardModel:
    @staticmethod
    def create_for_user(user_id, payload_url_template):
        conn = get_conn()
        cur = conn.cursor()
        # generate a random token
        import secrets
        token = secrets.token_urlsafe(24)

        # insert placeholder row to get id
        cur.execute('INSERT INTO qr_cards (user_id, token, is_active) VALUES (%s,%s,1)', (user_id, token))
        conn.commit()
        qr_row_id = cur.lastrowid

        qr_id = f'LSQ{qr_row_id:06d}'
        # prepare file paths
        qr_folder = os.path.join(current_app.config.get('QR_FOLDER'))
        os.makedirs(qr_folder, exist_ok=True)
        filename = f'qr_{qr_id}.png'
        path = os.path.join(qr_folder, filename)

        # generate QR image
        payload = payload_url_template.replace('__TOKEN__', token)
        img = qrcode.make(payload)
        img.save(path)

        rel_path = os.path.relpath(path, start=current_app.root_path)

        # update the row with qr_id and path
        cur.execute('UPDATE qr_cards SET qr_id=%s, path=%s WHERE id=%s', (qr_id, rel_path, qr_row_id))
        conn.commit()
        cur.close()

        return {
            'id': qr_row_id,
            'qr_id': qr_id,
            'token': token,
            'path': rel_path,
            'is_active': 1,
        }

    @staticmethod
    def find_by_token(token):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT id, qr_id, user_id, token, path, is_active, scan_count, last_scanned_at, created_at FROM qr_cards WHERE token=%s', (token,))
        row = cur.fetchone()
        cur.close()
        return row

    @staticmethod
    def get_latest_for_user(user_id):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT id, qr_id, user_id, token, path, is_active, scan_count, last_scanned_at, created_at FROM qr_cards WHERE user_id=%s ORDER BY created_at DESC LIMIT 1', (user_id,))
        row = cur.fetchone()
        cur.close()
        return row

    @staticmethod
    def increment_scan(qr_id, ip, user_agent, device_info=None):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('UPDATE qr_cards SET scan_count = scan_count + 1, last_scanned_at = NOW() WHERE id=%s', (qr_id,))
        conn.commit()
        cur.close()

    @staticmethod
    def stats_for_user(user_id):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM qr_cards WHERE user_id=%s', (user_id,))
        total_cards = cur.fetchone()[0]
        cur.execute('SELECT SUM(scan_count) FROM qr_cards WHERE user_id=%s', (user_id,))
        total_scans = cur.fetchone()[0] or 0
        cur.close()
        return {'total_cards': total_cards, 'total_scans': total_scans}
