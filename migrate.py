import os
import sys
from config import Config
import MySQLdb

def run():
    cfg = Config()
    conn = MySQLdb.connect(host=cfg.MYSQL_HOST, user=cfg.MYSQL_USER, passwd=cfg.MYSQL_PASSWORD)
    cur = conn.cursor()
    sql = open(os.path.join(os.path.dirname(__file__), 'database', 'schema.sql')).read()
    for stmt in sql.split(';'):
        s = stmt.strip()
        if s:
            cur.execute(s)
    conn.commit()
    cur.close()
    print('Migrations applied')

if __name__ == '__main__':
    run()
