#!/usr/bin/env python3
"""Validate both dashboard models; optionally read all their datasource queries."""
import argparse
import json
import math
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, build_opener

REMOVED={2,3,4,5,12,16,22,27,36,37,58,60}
def walk(panels):
    for panel in panels:
        yield panel
        yield from walk(panel.get('panels',[]))

def validate_layout(panels):
    for i,p in enumerate(panels):
        a=p['gridPos']
        assert a['x']>=0 and a['y']>=0 and a['w']>0 and a['h']>0 and a['x']+a['w']<=24
        for q in panels[i+1:]:
            b=q['gridPos']
            assert not (a['x']<b['x']+b['w'] and b['x']<a['x']+a['w'] and a['y']<b['y']+b['h'] and b['y']<a['y']+a['h']), (p['id'],q['id'],'overlap')
        validate_layout(p.get('panels',[]))

def validate(name,d,baseline,manifest):
    panels=list(walk(d['panels'])); by={p['id']:p for p in panels}
    original={p['id']:p for p in walk(baseline['panels'])}
    assert len(by)==len(panels),'Duplicate IDs'
    assert d['uid']==baseline['uid']
    assert d['refresh']==baseline['refresh']=='1m'
    removed=set(original)-set(by)
    assert removed==(REMOVED if name=='comparison' else set()), (name,removed)
    assert set(by)-set(original)==({94,95,96} if name=='unified' else set())
    edits={(x['id'],x['refId']):x for x in manifest['changes'] if x['dashboard']==name}
    observed=set()
    for pid,old in original.items():
        if pid in removed: continue
        p=by[pid];assert p['type']==old['type']
        assert len(p.get('targets',[]))==len(old.get('targets',[]))
        for oldt in old.get('targets',[]):
            t=next(t for t in p['targets'] if t['refId']==oldt['refId'])
            key=(pid,t['refId'])
            if key in edits:
                assert oldt['expr']==edits[key]['before'] and t['expr']==edits[key]['after']
                observed.add(key)
            else: assert oldt['expr']==t['expr'],(name,pid,'Unexpected query change')
            for attr in ('datasource','instant','range','queryType','format'):
                assert oldt.get(attr)==t.get(attr),(name,pid,attr)
    assert observed==set(edits)
    for p in panels:
        if p['type']=='row': assert not p['panels'] or p['collapsed']
        if p['type']=='timeseries': assert p['fieldConfig']['defaults']['custom']['spanNulls'] is False
    validate_layout(d['panels'])
    assert {v['name'] for v in d['templating']['list']}=={v['name'] for v in baseline['templating']['list']}
    if name=='comparison':
        assert by[61]['collapsed'] and by[61]['title'].startswith('06 ·')
        assert len(by[61]['panels'])==25
    else:
        assert by[66]['options']['sortBy'][0]['displayName']=='Kérések'
        transforms=by[66]['transformations']
        assert transforms[-1]['options']['renameByName']=={'method':'Metódus','route':'Útvonal'}
        assert transforms[0]['options']['renameByName']['Value #A']=='Kérések'
        assert transforms[4]['options']['renameByName']['Value #E']=='Időminták'
        assert by[43]['options']['xField']=='route'
        assert by[49]['collapsed'] and {p['id'] for p in by[49]['panels']}=={50,47,48}
        assert by[96]['fieldConfig']['defaults']['unit']=='s'
        assert by[96]['targets'][0]['expr']==by[26]['targets'][0]['expr']
        assert by[96]['targets'][1]['expr']==by[32]['targets'][0]['expr']
        for pid in (5,29,30,52,56,58):
            assert '[5m' not in by[pid]['targets'][0]['expr']
    print(f'{name}: static PASS; {len(panels)} nodes; {sum(len(p.get("targets",[])) for p in panels)} targets')

def expand(expr,d,seconds=3600):
    variables={v['name']:v.get('current',{}).get('value','') for v in d.get('templating',{}).get('list',[])}
    def replace(match):
        name,fmt=match.group(1),match.group(2)
        if name not in variables: raise ValueError('Unknown dashboard variable')
        value=variables[name]
        if not isinstance(value,str): raise ValueError('Expected single string variable')
        if fmt=='regex': value=re.escape(value)
        elif fmt not in (None,'raw'): raise ValueError('Unsupported variable formatter')
        return json.dumps(value,ensure_ascii=False)[1:-1]
    expr=re.sub(r'\$\{([A-Za-z_][A-Za-z0-9_]*)(?::([a-z]+))?\}',replace,expr)
    for key,value in [('$__range_s',str(seconds)),('$__interval_ms','60000'),('$__rate_interval','5m'),('$__interval','1m'),('$__range',str(seconds)+'s')]:
        expr=expr.replace(key,value)
    if re.search(r'\$[A-Za-z_{]',expr): raise ValueError('Unexpanded variable')
    return expr

def query_all(dashboards,history):
    opener=build_opener(ProxyHandler({}));seen={};failed=0;empty=0;total=0
    now=time.time();start=now-3600
    for name,d in dashboards.items():
        for p in walk(d['panels']):
            for t in p.get('targets',[]):
                total+=1
                label=f'{name} {p["id"]} {t["refId"]}'
                try:
                    uid=t.get('datasource',p.get('datasource',{})).get('uid')
                    if uid not in ('prometheus','loki'): raise ValueError('Unsupported datasource')
                    expr=expand(t['expr'],d)
                    is_log=p['type']=='logs'
                    ranged=is_log or (history and t.get('range',False))
                    key=(uid,expr,ranged,is_log)
                    if key in seen:
                        count=seen[key];print(label,'OK reused',f'series={count}');continue
                    base='http://127.0.0.1:9090/api/v1/' if uid=='prometheus' else 'http://127.0.0.1:3100/loki/api/v1/'
                    params={'query':expr}
                    if ranged:
                        params.update(start=str(int((now-300 if is_log else start)*1e9)) if uid=='loki' else str(start),end=str(int(now*1e9)) if uid=='loki' else str(now))
                        params.update({'limit':5,'direction':'backward'} if is_log else {'step':'60'})
                    else: params['time']=str(now)
                    with opener.open(base+('query_range' if ranged else 'query')+'?'+urlencode(params),timeout=30) as response:
                        result=json.load(response)
                    if result.get('status')!='success' or result.get('warnings'): raise ValueError('Datasource error or warnings')
                    rows=result['data']['result'];count=len(rows)
                    if not is_log:
                        for row in rows:
                            values=row.get('values',[]) or ([row['value']] if 'value' in row else [])
                            if any(not math.isfinite(float(value[1])) for value in values):
                                raise ValueError('Non-finite metric result')
                    seen[key]=count
                    if not count: empty+=1
                    print(label,uid,'range' if ranged else 'instant','OK',f'series={count}')
                except Exception as error:
                    status=f' HTTP {error.code}' if isinstance(error,HTTPError) else ''
                    print(label,'FAILED',type(error).__name__+status);failed+=1
    print(f'Datasource audit: targets={total}; unique_successful={len(seen)}; empty={empty}; failed={failed}')
    print('Empty results are missing matching observations, not proof of zero traffic. No raw logs were printed.')
    return bool(failed)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--history',action='store_true')
    args=parser.parse_args();root=args.directory
    manifest=json.loads((root/'dashboard-query-audit.json').read_text(encoding='utf-8'))
    dashboards={}
    for name in ('unified','comparison'):
        filename='matchwise-unified-monitoring.json' if name=='unified' else 'matchwise-service-comparison.json'
        d=json.loads((root/filename).read_text(encoding='utf-8'))
        baseline=json.loads((root/('baseline-'+name+'.json')).read_text(encoding='utf-8'))
        validate(name,d,baseline,manifest);dashboards[name]=d
    return int(query_all(dashboards,args.history)) if args.live else 0

if __name__=='__main__': raise SystemExit(main())
