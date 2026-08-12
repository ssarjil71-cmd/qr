import sys
from config import Config
import MySQLdb

cfg = Config()
try:
    conn = MySQLdb.connect(host=cfg.MYSQL_HOST, user=cfg.MYSQL_USER, passwd=cfg.MYSQL_PASSWORD, db=cfg.MYSQL_DB)
    cur = conn.cursor()
    columns = [
        'emergency_primary_contact_name',
        'emergency_primary_contact_relation',
        'emergency_primary_contact_mobile',
        'emergency_primary_contact_whatsapp',
        'emergency_secondary_contact_name',
        'emergency_secondary_contact_relation',
        'emergency_secondary_contact_mobile',
        'emergency_doctor_name',
        'emergency_doctor_phone',
        'emergency_address',
        'emergency_note',
    ]
    for col in columns:
        print('checking', col)
        sys.stdout.flush()
        try:
            cur.execute("SHOW COLUMNS FROM users LIKE %s", (col,))
            row = cur.fetchone()
            if row:
                print('exists', col)
            else:
                sql = f"ALTER TABLE users ADD COLUMN {col} {'TEXT' if col.endswith('_address') or col == 'emergency_note' else 'VARCHAR(255)'}"
                if col.endswith('_relation'):
                    sql = f"ALTER TABLE users ADD COLUMN {col} VARCHAR(100)"
                elif col.endswith('_mobile') or col.endswith('_phone'):
                    sql = f"ALTER TABLE users ADD COLUMN {col} VARCHAR(50)"
                elif col.endswith('_whatsapp'):
                    sql = f"ALTER TABLE users ADD COLUMN {col} VARCHAR(10)"
                print('adding', col, sql)
                sys.stdout.flush()
                cur.execute(sql)
        except Exception as e:
            print('error', col, type(e).__name__, e)
            sys.stdout.flush()
            raise
    conn.commit()
    print('done')
except Exception as exc:
    print('exception', type(exc).__name__, exc)
    raise
finally:
    try:
        cur.close()
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass
