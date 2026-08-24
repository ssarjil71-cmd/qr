import sys
import os
import csv
import io
import json
import time
import pymysql
import requests

# ensure project root on path
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
from config import Config

cfg = Config()
DB_CFG = dict(host=cfg.MYSQL_HOST, user=cfg.MYSQL_USER, password=cfg.MYSQL_PASSWORD, database=cfg.MYSQL_DB, cursorclass=pymysql.cursors.DictCursor, autocommit=False)

# Candidate CSV sources (community/government). The script will try each until one succeeds.
CANDIDATE_URLS = [
    # Datameet project (common community dataset)
    'https://raw.githubusercontent.com/datameet/india/master/talukas.csv',
    'https://raw.githubusercontent.com/datameet/maps/master/2011StateDistTalukaCSV/taluka_2011.csv',
    'https://raw.githubusercontent.com/datameet/india/master/districts.csv',
    # Alternate community sources
    'https://raw.githubusercontent.com/iamvivekkaushik/india-districts/master/data/talukas.csv',
    # Government open data portal exports (may change)
    'https://data.gov.in/sites/default/files/State_District_Taluka.csv'
]

MAH_DISTRICT_RENAMES = {
    'Ahmednagar': 'Ahilyanagar',
    'Aurangabad': 'Chhatrapati Sambhajinagar',
    'Osmanabad': 'Dharashiv'
}

# Normalization helpers
import unicodedata

def norm(s):
    if s is None:
        return ''
    s = s.strip()
    s = unicodedata.normalize('NFKD', s)
    s = s.replace('\u200b','')
    return ' '.join(s.split())


def try_download(url):
    print('Trying', url)
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        content = r.content.decode('utf-8', errors='replace')
        # save last successful download for inspection
        try:
            outp = os.path.join(os.path.dirname(__file__), 'downloaded_source.csv')
            with open(outp, 'w', encoding='utf-8') as f:
                f.write(content)
            print('Saved downloaded source to', outp)
            # print sample lines
            for i, line in enumerate(content.splitlines()[:10]):
                print(i+1, line[:300])
        except Exception as e:
            print('Failed to save sample download:', e)
        return content
    except Exception as e:
        print('Failed', url, '->', e)
        return None


def parse_csv_text(text):
    # Try to sniff delimiter
    sample = text[:8192]
    sniffer = csv.Sniffer()
    dialect = None
    try:
        dialect = sniffer.sniff(sample)
    except Exception:
        dialect = csv.excel
    f = io.StringIO(text)
    reader = csv.DictReader(f, dialect=dialect)
    rows = [dict((k.strip(), v.strip()) for k, v in row.items()) for row in reader if any((v and v.strip()) for v in row.values())]
    return rows


def find_column_candidates(cols):
    l = [c.lower() for c in cols]
    candidates = {
        'state': None,
        'district': None,
        'taluka': None
    }
    for c in cols:
        lc = c.lower()
        if any(k in lc for k in ['state','st_name','state_name']):
            candidates['state'] = c
        if any(k in lc for k in ['district','dist','dt_name']):
            candidates['district'] = c
        if any(k in lc for k in ['taluka','tehsil','subdistrict','taluk','tehsilname','sub-district','sub_district']):
            candidates['taluka'] = c
    return candidates


def load_remote_dataset():
    for url in CANDIDATE_URLS:
        text = try_download(url)
        if not text:
            continue
        try:
            rows = parse_csv_text(text)
            if not rows:
                continue
            cols = list(rows[0].keys())
            cand = find_column_candidates(cols)
            if not cand['state'] or not cand['district']:
                # might be a districts-only file with columns state,district
                if len(cols) >= 2:
                    cand['state'] = cand['state'] or cols[0]
                    cand['district'] = cand['district'] or cols[1]
            print('Using URL', url)
            return rows, cand, url
        except Exception as e:
            print('Parse error for', url, e)
    return None, None, None


def main():
    rows, cand, used_url = load_remote_dataset()
    if rows is None:
        print('No usable remote dataset found. Aborting.')
        return 2
    print('Loaded', len(rows), 'rows from', used_url)

    conn = pymysql.connect(**DB_CFG)
    try:
        cur = conn.cursor()
        # load states
        cur.execute('SELECT id, name FROM states')
        states = cur.fetchall()
        state_by_norm = {norm(s['name']).lower(): s['id'] for s in states}
        print('DB states:', len(states))

        # load existing districts
        cur.execute('SELECT id, name, state_id FROM districts')
        districts = cur.fetchall()
        districts_by_state = {}
        for d in districts:
            key = (d['state_id'], norm(d['name']).lower())
            districts_by_state[key] = d['id']
        print('DB districts:', len(districts))

        # prepare inserts
        district_inserts = []
        taluka_inserts = []

        for r in rows:
            state_name = norm(r.get(cand['state']) or r.get(list(r.keys())[0]))
            district_name = norm(r.get(cand['district']) or r.get(list(r.keys())[1]))
            taluka_name = norm(r.get(cand['taluka']) or '')
            if not state_name or not district_name:
                continue
            s_norm = state_name.lower()
            state_id = state_by_norm.get(s_norm)
            if not state_id:
                # try fuzzy match by prefix
                for k,v in state_by_norm.items():
                    if k.startswith(s_norm) or s_norm.startswith(k):
                        state_id = v
                        break
            if not state_id:
                print('Unknown state in dataset:', state_name)
                continue
            # district rename mapping for Maharashtra (state_id 14)
            if state_id == 14 and district_name in MAH_DISTRICT_RENAMES:
                district_name_db = MAH_DISTRICT_RENAMES[district_name]
            else:
                district_name_db = district_name
            dist_key = (state_id, district_name_db.lower())
            if dist_key not in districts_by_state:
                district_inserts.append((state_id, district_name_db))
                # mark with a temporary placeholder id (will refresh after insert)
                districts_by_state[dist_key] = None
            if taluka_name:
                taluka_inserts.append((state_id, district_name_db, taluka_name))

        print('New districts to insert:', len(district_inserts))
        print('Taluka rows identified:', len(taluka_inserts))

        # Insert districts (batch)
        inserted_districts = 0
        if district_inserts:
            for state_id, district_name in district_inserts:
                # avoid duplicates (re-check)
                cur.execute('SELECT id FROM districts WHERE state_id=%s AND name=%s', (state_id, district_name))
                row = cur.fetchone()
                if row:
                    districts_by_state[(state_id, district_name.lower())] = row['id']
                    continue
                cur.execute('INSERT INTO districts (state_id, name) VALUES (%s, %s)', (state_id, district_name))
                inserted_districts += 1
            conn.commit()
            print('Inserted', inserted_districts, 'districts')

        # reload districts map for IDs
        cur.execute('SELECT id, name, state_id FROM districts')
        districts = cur.fetchall()
        districts_by_state = {(d['state_id'], norm(d['name']).lower()): d['id'] for d in districts}

        # Insert talukas
        inserted_talukas = 0
        skipped = 0
        for state_id, district_name, taluka_name in taluka_inserts:
            key = (state_id, district_name.lower())
            district_id = districts_by_state.get(key)
            if not district_id:
                # sometimes district name in dataset differs slightly; try to find by lower startswith
                found = None
                for (sid, dname), did in districts_by_state.items():
                    if sid == state_id and (dname == district_name.lower() or dname.startswith(district_name.lower()) or district_name.lower().startswith(dname)):
                        found = did
                        break
                if found:
                    district_id = found
                else:
                    print('Could not resolve district for taluka', taluka_name, '->', district_name, 'in state_id', state_id)
                    skipped += 1
                    continue
            # avoid duplicates
            cur.execute('SELECT id FROM talukas WHERE district_id=%s AND name=%s', (district_id, taluka_name))
            if cur.fetchone():
                continue
            cur.execute('INSERT INTO talukas (district_id, name) VALUES (%s, %s)', (district_id, taluka_name))
            inserted_talukas += 1
            # commit periodically
            if inserted_talukas % 200 == 0:
                conn.commit()
        conn.commit()
        print('Inserted talukas:', inserted_talukas, 'Skipped:', skipped)

        # Verification queries
        cur.execute('SELECT COUNT(*) AS cnt FROM states')
        states_cnt = cur.fetchone()['cnt']
        cur.execute('SELECT COUNT(*) AS cnt FROM districts')
        districts_cnt = cur.fetchone()['cnt']
        cur.execute('SELECT COUNT(*) AS cnt FROM talukas')
        talukas_cnt = cur.fetchone()['cnt']

        print('\nVerification:')
        print('States:', states_cnt)
        print('Districts:', districts_cnt)
        print('Talukas:', talukas_cnt)

        # states with zero districts
        cur.execute('SELECT s.id, s.name FROM states s LEFT JOIN districts d ON s.id=d.state_id WHERE d.id IS NULL')
        no_district_states = cur.fetchall()
        print('\nStates with zero districts:', len(no_district_states))
        for s in no_district_states:
            print(' -', s['name'])

        # districts with zero talukas
        cur.execute('SELECT d.id, d.name, s.name AS state FROM districts d LEFT JOIN talukas t ON d.id=t.district_id JOIN states s ON d.state_id=s.id WHERE t.id IS NULL')
        no_talukas = cur.fetchall()
        print('\nDistricts with zero talukas:', len(no_talukas))
        for d in no_talukas[:50]:
            print(' -', d['state'], '/', d['name'])

        # duplicate districts within a state
        cur.execute('SELECT state_id, name, COUNT(*) c FROM districts GROUP BY state_id, name HAVING c>1')
        dup_districts = cur.fetchall()
        print('\nDuplicate districts (state,district):', len(dup_districts))

        # duplicate talukas within a district
        cur.execute('SELECT district_id, name, COUNT(*) c FROM talukas GROUP BY district_id, name HAVING c>1')
        dup_talukas = cur.fetchall()
        print('Duplicate talukas (district,taluka):', len(dup_talukas))

        # invalid state->district relationships (not likely since districts have state_id FK)
        # invalid district->taluka relationships
        cur.execute('SELECT t.id, t.name FROM talukas t LEFT JOIN districts d ON t.district_id=d.id WHERE d.id IS NULL')
        invalid_talukas = cur.fetchall()
        print('Talukas with invalid district FK:', len(invalid_talukas))

    finally:
        conn.close()

if __name__ == '__main__':
    sys.exit(main())
