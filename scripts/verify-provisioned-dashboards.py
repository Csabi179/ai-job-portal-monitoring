#!/usr/bin/env python3
"""Read only the requested provisioned dashboard models from the local Grafana SQLite DB."""
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

def differences(actual,expected):
    issues=[]
    if actual is None: return ['dashboard missing from authoritative storage']
    if actual.get('title')!=expected['title']: issues.append('root.title differs')
    a={p['id']:p for p in walk(actual.get('panels',[]))}
    e={p['id']:p for p in walk(expected['panels'])}
    if set(a)!=set(e):
        issues.append('panel IDs differ: missing='+str(sorted(set(e)-set(a)))+' extra='+str(sorted(set(a)-set(e))))
    for pid,p in e.items():
        if pid not in a: continue
        for key in ('type','title','gridPos'):
            if a[pid].get(key)!=p.get(key): issues.append(f'panel {pid}: {key} differs')
        if p['type']=='row' and a[pid].get('collapsed',False)!=p.get('collapsed',False): issues.append(f'panel {pid}: collapsed state differs')
        targets={t['refId']:t for t in a[pid].get('targets',[])}
        for t in p.get('targets',[]):
            if t['refId'] not in targets:
                issues.append(f'panel {pid}: target {t["refId"]} missing');continue
            if targets[t['refId']].get('expr')!=t.get('expr'): issues.append(f'panel {pid}/{t["refId"]}: expression differs')
            if targets[t['refId']].get('datasource',a[pid].get('datasource'))!=t.get('datasource',p.get('datasource')): issues.append(f'panel {pid}/{t["refId"]}: datasource differs')
        if len(targets)!=len(p.get('targets',[])): issues.append(f'panel {pid}: target count differs')
    return issues

def matches(actual,expected):
    return not differences(actual,expected)

class UnsupportedStorage(ValueError):
    pass

def unwrap_resource(raw,name,namespace):
    obj=json.loads(raw)
    if not isinstance(obj,dict): raise UnsupportedStorage('resource JSON is not an object')
    meta=obj.get('metadata',{})
    if obj.get('kind')!='Dashboard' or not obj.get('apiVersion','').startswith('dashboard.grafana.app/'):
        raise UnsupportedStorage('unexpected resource kind/API group')
    if meta.get('name')!=name or meta.get('namespace',namespace)!=namespace:
        raise UnsupportedStorage('resource identity differs from its storage key')
    if meta.get('deletionTimestamp'): return None
    spec=obj.get('spec')
    if not isinstance(spec,dict) or not isinstance(spec.get('panels'),list):
        raise UnsupportedStorage('dashboard resource is not a supported Classic/V1 spec; cannot verify without conversion')
    return spec

def read_models(connection,uids):
    tables={r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    placeholders=','.join('?' for _ in uids)
    if 'resource' in tables:
        columns={r[1] for r in connection.execute('PRAGMA table_info("resource")')}
        if not {'group','resource','namespace','name','value','action'}.issubset(columns):
            raise UnsupportedStorage('unified resource table has an unsupported schema')
        # Grafana v13 reads this table. Never accept a stale legacy dashboard row instead.
        rows=connection.execute('SELECT "namespace","name","value" FROM "resource" '
            'WHERE "group"=? AND "resource"=? AND "namespace" IN (?,?) '
            'AND "action" IN (1,2) AND "name" IN ('+placeholders+')',
            ('dashboard.grafana.app','dashboards','default','org-1',*uids)).fetchall()
        actual={}
        for namespace,name,raw in rows:
            if name in actual: raise UnsupportedStorage('ambiguous org-1 namespace aliases for a dashboard UID')
            model=unwrap_resource(raw,name,namespace)
            if model is not None: actual[name]=model
        return 'unified.resource (org 1)',actual
    if 'unifiedstorage_migration_log' in tables:
        raise UnsupportedStorage('unified storage migration marker exists but current resource storage is unavailable; refusing legacy rows')
    if 'dashboard' not in tables: raise UnsupportedStorage('no supported dashboard storage table')
    rows=connection.execute('SELECT uid,data FROM dashboard WHERE uid IN ('+placeholders+')',tuple(uids)).fetchall()
    return 'legacy.dashboard (no unified storage tables)',{uid:json.loads(data) for uid,data in rows}

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
    parser.add_argument('--files',nargs='+',default=['matchwise-unified-monitoring.json','matchwise-service-comparison.json'])
    args=parser.parse_args()
    expected=[json.loads((args.directory/f).read_text(encoding='utf-8')) for f in args.files]
    try:
        db=locate_database()
    except (OSError,subprocess.SubprocessError,ValueError):
        db=None
    if db is None:
        print('SKIP: local Grafana SQLite dashboard storage unavailable; browser provisioning verification still required.')
        return 3
    deadline=time.monotonic()+max(0,args.wait)
    printed_source=None
    while True:
        try:
            connection=sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True,timeout=5)
            try:
                connection.execute('PRAGMA query_only=ON')
                source,actual=read_models(connection,[d['uid'] for d in expected])
            finally:
                connection.close()
            if source!=printed_source:
                print('Authoritative dashboard verification source:',source)
                printed_source=source
            if all(d['uid'] in actual and matches(actual[d['uid']],d) for d in expected):
                print(f'PASS: Grafana stored all {len(expected)} expected dashboard models, including panel layout, titles, collapsed rows and queries.')
                print('This verifies provisioning, not browser rendering or positive business traffic.')
                return 0
        except (sqlite3.OperationalError,UnsupportedStorage,json.JSONDecodeError) as error:
            print('SKIP: current storage cannot be verified:',str(error) if isinstance(error,UnsupportedStorage) else type(error).__name__)
            print('No fallback to stale legacy dashboard rows. Browser/API verification is required.')
            return 3
        if time.monotonic()>=deadline:
            print('FAILED: Grafana did not load the expected dashboard models within the provisioning window.')
            for d in expected:
                issues=differences(actual.get(d['uid']),d)
                if issues:
                    print(d['uid']+': '+'; '.join(issues[:12]))
                    if len(issues)>12: print(f'  {len(issues)-12} further model differences omitted.')
            return 1
        time.sleep(2)

if __name__=='__main__': raise SystemExit(main())
