from app import create_app
from services.db import get_conn

app = create_app()
with app.app_context():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, qr_path, name FROM users WHERE qr_path IS NOT NULL LIMIT 5')
    rows = cur.fetchall()
    if not rows:
        print("No QR paths found")
    for row in rows:
        print(f"User {row[0]}: {row[2]}")
        print(f"  Path: {repr(row[1])}")
    cur.close()
    conn.close()
