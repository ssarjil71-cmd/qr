import sys, os, json, pymysql, requests
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
from config import Config

cfg = Config()
DB_CFG = dict(host=cfg.MYSQL_HOST, user=cfg.MYSQL_USER, password=cfg.MYSQL_PASSWORD, database=cfg.MYSQL_DB, cursorclass=pymysql.cursors.DictCursor, autocommit=False)

URL = 'https://raw.githubusercontent.com/datameet/maps/master/website/docs/data/geojson/dists11.geojson'

def norm(s):
    return (s or '').strip()

def main():
    print('Downloading', URL)
    r = requests.get(URL, timeout=30)
    r.raise_for_status()
    data = r.json()
    # properties likely have 'ST_NM' or 'state' and 'DISTRICT'
    items = []
    for f in data.get('features', []):
        props = f.get('properties', {})
        # try multiple property names
        state = props.get('ST_NM') or props.get('STATE') or props.get('state') or props.get('st_nm')
        dist = props.get('DISTRICT') or props.get('DIST_NAME') or props.get('dist') or props.get('DIST') or props.get('DISTRICT_')
        if state and dist:
            items.append((state.strip(), dist.strip()))
    print('Parsed', len(items), 'district entries')
    # load db states
    conn = pymysql.connect(**DB_CFG)
    try:
        cur = conn.cursor()
        cur.execute('SELECT id, name FROM states')
        states = cur.fetchall()
        state_by_norm = {norm(s['name']).lower(): s['id'] for s in states}
        # load existing districts
        cur.execute('SELECT id, name, state_id FROM districts')
        districts = cur.fetchall()
        district_keys = {(d['state_id'], norm(d['name']).lower()): d['id'] for d in districts}
        to_insert = set()
        for state, dist in items:
            s_norm = state.lower()
            sid = state_by_norm.get(s_norm)
            if not sid:
                # try startswith match
                for k,v in state_by_norm.items():
                    if k.startswith(s_norm) or s_norm.startswith(k):
                        sid = v
                        break
            if not sid:
                print('Unknown state:', state)
                continue
            key = (sid, dist.lower())
            if key not in district_keys:
                to_insert.add((sid, dist))
        print('New districts to insert:', len(to_insert))
        inserted = 0
        for sid, dist in sorted(to_insert):
            cur.execute('SELECT id FROM districts WHERE state_id=%s AND name=%s', (sid, dist))
            if cur.fetchone():
                continue
            cur.execute('INSERT INTO districts (state_id, name) VALUES (%s, %s)', (sid, dist))
            inserted += 1
            if inserted % 100 == 0:
                conn.commit()
        conn.commit()
        print('Inserted districts:', inserted)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
