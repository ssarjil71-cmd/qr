import json
import sys
import os
import pymysql

# Ensure project root is on sys.path so we can import config.py
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

from config import Config

cfg = Config()
conn = None
try:
    conn = pymysql.connect(host=cfg.MYSQL_HOST, user=cfg.MYSQL_USER, password=cfg.MYSQL_PASSWORD, database=cfg.MYSQL_DB, cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()
    out = {}
    # tables existence
    def table_exists(name):
        cur.execute("SHOW TABLES LIKE %s", (name,))
        return cur.fetchone() is not None
    for t in ['states','districts','talukas','users','student_profiles']:
        out[t] = {'exists': table_exists(t)}
    # schemas and counts
    if out['states']['exists']:
        cur.execute('DESCRIBE states')
        out['states']['describe'] = cur.fetchall()
        cur.execute('SELECT COUNT(*) AS cnt FROM states')
        out['states']['count'] = cur.fetchone()['cnt']
        cur.execute('SELECT id, name FROM states ORDER BY name')
        out['states']['rows'] = cur.fetchall()
    if out['districts']['exists']:
        cur.execute('DESCRIBE districts')
        out['districts']['describe'] = cur.fetchall()
        cur.execute('SELECT COUNT(*) AS cnt FROM districts')
        out['districts']['count'] = cur.fetchone()['cnt']
        cur.execute("SELECT id, name, state_id FROM districts ORDER BY state_id, name")
        out['districts']['rows'] = cur.fetchall()
    if out['talukas']['exists']:
        cur.execute('DESCRIBE talukas')
        out['talukas']['describe'] = cur.fetchall()
        cur.execute('SELECT COUNT(*) AS cnt FROM talukas')
        out['talukas']['count'] = cur.fetchone()['cnt']
        cur.execute("SELECT id, name, district_id FROM talukas ORDER BY district_id, name LIMIT 200")
        out['talukas']['sample_rows'] = cur.fetchall()
    # find Maharashtra state id
    if out['states']['exists']:
        cur.execute("SELECT id FROM states WHERE name LIKE %s", ('%Maharashtra%',))
        out['maharashtra'] = cur.fetchall()
    # print json
    print(json.dumps(out, indent=2, ensure_ascii=False))
except Exception as e:
    print('ERROR', e, file=sys.stderr)
    sys.exit(2)
finally:
    if conn:
        conn.close()
