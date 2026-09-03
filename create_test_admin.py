import MySQLdb
from werkzeug.security import generate_password_hash
from config import Config

cfg = Config()
conn = MySQLdb.connect(
    host=cfg.MYSQL_HOST,
    user=cfg.MYSQL_USER,
    passwd=cfg.MYSQL_PASSWORD,
    database=cfg.MYSQL_DB
)
cur = conn.cursor()

# Check if admin already exists
cur.execute('SELECT id FROM users WHERE email=%s AND user_type=%s', ('admin@test.com', 'admin'))
existing = cur.fetchone()

if not existing:
    # Insert test admin with mobile number
    cur.execute('''
        INSERT INTO users (user_type, name, mobile, email, password_hash, is_active)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', ('admin', 'Test Admin', '+919999999999', 'admin@test.com', generate_password_hash('password123'), 1))
    conn.commit()
    print('✓ Test admin created: admin@test.com / password123')
    print('  Mobile: +919999999999')
else:
    print('✓ Test admin already exists')
    # Update mobile number if needed
    cur.execute('UPDATE users SET mobile=%s WHERE email=%s AND user_type=%s', 
                ('+919999999999', 'admin@test.com', 'admin'))
    conn.commit()
    print('  Mobile updated to: +919999999999')

cur.close()
conn.close()
