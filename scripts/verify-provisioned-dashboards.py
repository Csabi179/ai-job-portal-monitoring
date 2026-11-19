#!/usr/bin/env python3
"""Read only the two provisioned dashboard models from the local Grafana SQLite DB."""
import argparse
import json
from pathlib import Path
import sqlite3
import subprocess
import time

def walk(ps):
    for p in ps:
        yield p
        yield from walk(p.get('panels',[]))

def matches(actual,expected):
    if actual.get('title')!=expected['title']: return False
    a={p['id']:p for p in walk(actual.get('panels',[]))}
    e={p['id']:p for p in walk(expected['panels'])}
    if set(a)!=set(e): return False
    for pid,p in e.items():
        for key in ('type','title','gridPos'):
            if a[pid].get(key)!=p.get(key): return False
        if p['type']=='row' and a[pid].get('collapsed',False)!=p.get('collapsed',False): return False
        targets={t['refId']:t for t in a[pid].get('targets',[])}
        for t in p.get('targets',[]):
            if t['refId'] not in targets: return False
            if targets[t['refId']].get('expr')!=t.get('expr'): return False
            if targets[t['refId']].get('datasource',a[pid].get('datasource'))!=t.get('datasource',p.get('datasource')): return False
        if len(targets)!=len(p.get('targets',[])): return False
    return True

def locate_database():
    # Mount metadata only: never inspect/print Grafana credentials or user tables.
    ids=subprocess.check_output(['docker','ps','--filter','label=com.docker.compose.service=grafana','--format','{{.ID}}'],text=True).split()
    if len(ids)!=1: return None
    raw=subprocess.check_output(['docker','inspect',ids[0],'--format','{{json .Mounts}}'],text=True)
    mounts=json.loads(raw)
    sources=[Path(m['Source']) for m in mounts if m.get('Destination')=='/var/lib/grafana']
    if len(sources)!=1: return None
    db=sources[0]/'grafana.db'
    return db if db.is_file() else None

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--wait',type=int,default=75)
    args=parser.parse_args()
    expected=[json.loads((args.directory/f).read_text(encoding='utf-8')) for f in ['matchwise-unified-monitoring.json','matchwise-service-comparison.json']]
    try:
        db=locate_database()
    except (OSError,subprocess.SubprocessError,ValueError):
        db=None
    if db is None:
        print('SKIP: local Grafana SQLite dashboard storage unavailable; browser provisioning verification still required.')
        return 3
    deadline=time.monotonic()+max(0,args.wait)
    while True:
        try:
            connection=sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True,timeout=5)
            try:
                connection.execute('PRAGMA query_only=ON')
                rows=connection.execute('SELECT uid, data FROM dashboard WHERE uid IN (?,?)',tuple(d['uid'] for d in expected)).fetchall()
            finally:
                connection.close()
            actual={uid:json.loads(data) for uid,data in rows}
            if all(d['uid'] in actual and matches(actual[d['uid']],d) for d in expected):
                print('PASS: Grafana stored both expected dashboard models, including panel layout, titles, collapsed rows and queries.')
                print('This verifies provisioning, not browser rendering or positive business traffic.')
                return 0
        except sqlite3.OperationalError:
            print('SKIP: legacy dashboard table unreadable; browser provisioning verification still required.')
            return 3
        if time.monotonic()>=deadline:
            print('FAILED: Grafana did not load the expected dashboard models within the provisioning window.')
            return 1
        time.sleep(2)

if __name__=='__main__': raise SystemExit(main())
