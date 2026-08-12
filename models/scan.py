from services.db import get_conn

class ScanModel:
    @staticmethod
    def log_scan(user_id, ip, user_agent, device_info=None):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('INSERT INTO scan_logs (user_id, ip_address, user_agent, device_info) VALUES (%s,%s,%s,%s)', (user_id, ip, user_agent, device_info))
        conn.commit()
        cur.close()

    @staticmethod
    def list_for_user(user_id):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT id, scanned_at, ip_address, user_agent, device_info FROM scan_logs WHERE user_id=%s ORDER BY scanned_at DESC', (user_id,))
        rows = cur.fetchall()
        cur.close()
        return rows
