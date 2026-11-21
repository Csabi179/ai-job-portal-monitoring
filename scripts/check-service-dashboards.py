#!/usr/bin/env python3
"""Offline validation of the four service-grouped MatchWise dashboards.

Structure checks always run. Optional query checks:
  --promtool PATH   parse every Prometheus expression with promtool (no server needed)
  --loki URL        run every Loki expression against a Loki instance (e.g. a throw-away one
                    loaded with synthetic http_request lines) and report syntax/runtime errors
Nothing is written to Grafana, Prometheus or Loki.
"""
import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

FILES = ['matchwise-unified-monitoring.json', 'matchwise-unified-monitoring-en.json',
         'matchwise-service-comparison.json', 'matchwise-service-comparison-en.json']
SUBST = [('${excluded_route:raw}', '(/api/health|/health)'), ('${route_filter:regex}', ''),
         ('${status_filter:raw}', '.*'), ('${request_id:regex}', ''),
         ('${supabase_instance}', 'example.supabase.co:443'), ('$__range_s', '900'), ('$__range', '15m'),
         ('$__rate_interval', '5m'), ('$__interval', '1m')]
SERVICES_UNIFIED = ('Frontend', 'Backend', 'Oracle')
STRIP = 6


def walk(panels):
    for p in panels:
        yield p
        yield from walk(p.get('panels', []))


def substitute(expr):
    for a, b in SUBST:
        expr = expr.replace(a, b)
    return expr


def balanced(expr):
    stack, quote, escaped = [], None, False
    pairs = {')': '(', ']': '[', '}': '{'}
    for ch in expr:
        if quote:
            if escaped:
                escaped=False
                continue
            if ch=='\\' and quote!='`':
                escaped=True
                continue
            if ch == quote:
                quote = None
            continue
        if ch in '"`':
            quote = ch
        elif ch in '([{':
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack and quote is None


def overlap(a, b):
    return not (a['x'] + a['w'] <= b['x'] or b['x'] + b['w'] <= a['x'] or a['y'] + a['h'] <= b['y'] or b['y'] + b['h'] <= a['y'])


def check_layout(model, errors, name):
    seen, ids = [], set()
    for p in walk(model['panels']):
        if p['id'] in ids:
            errors.append(f'{name}: duplicate panel id {p["id"]}')
        ids.add(p['id'])
    def groups(panels):
        flat = [p for p in panels]
        for i, p in enumerate(flat):
            g = p['gridPos']
            if g['x'] < 0 or g['y'] < 0 or g['w'] <= 0 or g['h'] <= 0 or g['x'] + g['w'] > 24:
                errors.append(f'{name}: panel {p["id"]} outside grid {g}')
            for q in flat[i + 1:]:
                if overlap(g, q['gridPos']):
                    errors.append(f'{name}: panels {p["id"]} and {q["id"]} overlap')
    groups(model['panels'])
    for p in model['panels']:
        if p['type'] == 'row':
            if p['collapsed'] and not p['panels']:
                errors.append(f'{name}: collapsed row {p["id"]} is empty')
            if not p['collapsed'] and p['panels']:
                errors.append(f'{name}: expanded row {p["id"]} holds panels')
            if p['collapsed']:
                groups(p['panels'])
                if any(q['gridPos']['y'] <= p['gridPos']['y'] for q in p['panels']):
                    errors.append(f'{name}: nested panel above its row {p["id"]}')


def check_semantics(model, uids, errors, name):
    variables = {v['name'] for v in model.get('templating', {}).get('list', [])}
    panel_ids = {p['id'] for p in walk(model['panels'])}
    for p in walk(model['panels']):
        if p['type'] == 'timeseries':
            if p['fieldConfig']['defaults']['custom'].get('spanNulls') is not False:
                errors.append(f'{name}: {p["id"]} spanNulls must be false (missing data is not zero)')
        for t in p.get('targets', []):
            expr = t.get('expr', '')
            if not expr.strip():
                errors.append(f'{name}: {p["id"]}/{t["refId"]} empty expression')
            if not balanced(expr):
                errors.append(f'{name}: {p["id"]}/{t["refId"]} unbalanced brackets/quotes')
            for var in re.findall(r'\$\{(\w+)', expr):
                if var not in variables:
                    errors.append(f'{name}: {p["id"]} uses undefined variable {var}')
            if t['datasource']['uid'] not in ('prometheus', 'loki'):
                errors.append(f'{name}: {p["id"]} unknown datasource {t["datasource"]}')
        text = json.dumps(p.get('fieldConfig', {}), ensure_ascii=False)
        for url in re.findall(r'"url": "([^"]+)"', text):
            m = re.match(r'/d/([^/]+)/', url)
            if m and m.group(1) not in uids:
                errors.append(f'{name}: panel {p["id"]} links to unknown dashboard {m.group(1)}')
            if m and m.group(1) == model['uid']:
                vp = re.search(r'viewPanel=(\d+)', url)
                if vp and int(vp.group(1)) not in panel_ids:
                    errors.append(f'{name}: panel {p["id"]} links to missing panel {vp.group(1)}')
    for link in model.get('links', []):
        m = re.match(r'/d/([^/]+)/', link.get('url', ''))
        if m and m.group(1) not in uids:
            errors.append(f'{name}: dashboard link to unknown uid {m.group(1)}')


def check_consistency(models, errors):
    """Every service must open with the same strips (unified) / the same scorecard (comparison)."""
    for lang in ('hu', 'en'):
        uni = models['matchwise-unified-monitoring' + ('' if lang == 'hu' else '-en') + '.json']
        top = uni['panels']
        sections = {}
        current = None
        for p in top:
            if p['type'] == 'row':
                current = None if p['collapsed'] else p['title']
                if current:
                    sections[current] = []
            elif current:
                sections[current].append(p)
        wanted = {}
        for title, panels in sections.items():
            for svc in SERVICES_UNIFIED + ('Adatbázis', 'Database'):
                if title.split('·')[1].strip().startswith(svc) if '·' in title else False:
                    wanted[svc] = panels
        for svc, panels in wanted.items():
            count=4 if svc=='Frontend' else STRIP
            first = sorted(panels, key=lambda p: (p['gridPos']['y'], p['gridPos']['x']))[:count]
            ys = {p['gridPos']['y'] for p in first}
            if len(first) != count or len(ys) != 1 or any(p['gridPos']['w'] != 24//count for p in first):
                errors.append(f'unified {lang}: {svc} does not open with a {count}-tile strip')
            kinds = [p['title'].split('·', 1)[-1].strip() for p in first]
            ref = [k.replace('(%)', '').strip() for k in kinds]
            if svc in ('Frontend', 'Backend', 'Oracle', 'Adatbázis', 'Database'):
                if len(set(p['type'] for p in first)) != 1:
                    errors.append(f'unified {lang}: {svc} strip mixes panel types')
        titles = [[p['title'].split('·', 1)[-1].strip() for p in sorted(panels, key=lambda p: (p['gridPos']['y'], p['gridPos']['x']))[:STRIP]] for svc,panels in wanted.items() if svc!='Frontend']
        if 'Frontend' in wanted:
            fe_titles=[p['title'] for p in sorted(wanted['Frontend'],key=lambda p:(p['gridPos']['y'],p['gridPos']['x']))[:4]]
            if titles and fe_titles!=titles[0][:4]: errors.append(f'unified {lang}: frontend common health tiles differ')
        expected_services={'Frontend','Backend','Oracle','Adatbázis' if lang=='hu' else 'Database'}
        if set(wanted)!=expected_services:
            errors.append(f'unified {lang}: missing or unexpected service sections: {sorted(set(wanted)^expected_services)}')
        if titles and any(t != titles[0] for t in titles[1:]):
            errors.append(f'unified {lang}: service strips differ: {titles}')
        cmp_ = models['matchwise-service-comparison' + ('' if lang == 'hu' else '-en') + '.json']
        score = [p for p in cmp_['panels'] if p['type'] == 'stat'][:16]
        rows = {}
        for p in score:
            rows.setdefault(p['gridPos']['y'], []).append(p)
        shape = [tuple(q['title'] for q in sorted(r, key=lambda p: p['gridPos']['x'])) for r in rows.values()]
        services=['Frontend','Backend','Adatbázis' if lang=='hu' else 'Database','Oracle']
        if [s[0] for s in shape] != services:
            errors.append(f'comparison {lang}: missing scorecard service labels')
        shape=[s[1:] for s in shape]
        if len(rows) != 4 or any(len(s) != 3 for s in shape) or any(p['gridPos']['w']!=6 for p in score):
            errors.append(f'comparison {lang}: scorecard is not 4 identical rows of 4: {shape}')
        else:
            durations = [s[0] for s in shape]
            expected = (['HTTP-próba ideje'] * 2 + ['Scrape időtartama'] * 2 if lang == 'hu' else
                        ['HTTP probe duration'] * 2 + ['Metrics scrape duration'] * 2)
            if durations != expected:
                errors.append(f'comparison {lang}: probe and scrape duration labels are ambiguous: {durations}')


def check_parity(models, errors):
    for base in ('matchwise-unified-monitoring', 'matchwise-service-comparison'):
        hu, en = models[base + '.json'], models[base + '-en.json']
        h = {p['id']: p for p in walk(hu['panels'])}
        e = {p['id']: p for p in walk(en['panels'])}
        if set(h) != set(e):
            errors.append(f'{base}: HU/EN panel id sets differ')
            continue
        if hu.get('time')!=en.get('time') or hu.get('refresh')!=en.get('refresh'):
            errors.append(f'{base}: HU/EN time defaults differ')
        hv={v['name']:v for v in hu.get('templating',{}).get('list',[])}
        ev={v['name']:v for v in en.get('templating',{}).get('list',[])}
        if set(hv)!=set(ev): errors.append(f'{base}: variable names differ')
        for var in set(hv)&set(ev):
            a,b=hv[var],ev[var]
            for key in ('type','datasource','regex'):
                if a.get(key)!=b.get(key): errors.append(f'{base}: variable {var} {key} differs')
            if a.get('current',{}).get('value')!=b.get('current',{}).get('value'):
                errors.append(f'{base}: variable {var} values differ')
            if [(o['value'],o.get('selected')) for o in a.get('options',[])]!=[(o['value'],o.get('selected')) for o in b.get('options',[])]:
                errors.append(f'{base}: variable {var} option values differ')
        for pid, p in h.items():
            q = e[pid]
            for key in ('type', 'gridPos', 'collapsed'):
                if p.get(key) != q.get(key):
                    errors.append(f'{base}: panel {pid} {key} differs between HU and EN')
            pt, qt = p.get('targets', []), q.get('targets', [])
            if len(pt) != len(qt):
                errors.append(f'{base}: panel {pid} target count differs')
                continue
            for a, b in zip(pt, qt):
                for key in ('refId', 'expr', 'datasource', 'instant', 'range', 'queryType'):
                    if a.get(key) != b.get(key):
                        errors.append(f'{base}: panel {pid}/{a["refId"]} {key} differs between HU and EN')


def collect_queries(model):
    out = []
    for p in walk(model['panels']):
        for t in p.get('targets', []):
            out.append((p['id'], p['title'], p['type'], t))
    return out


def run_promtool(path, models, errors):
    rules, seen = [], {}
    for name, model in models.items():
        if name.endswith('-en.json'):
            continue
        for pid, title, kind, t in collect_queries(model):
            if t['datasource']['uid'] == 'prometheus':
                expr = substitute(t['expr'])
                if expr not in seen:
                    seen[expr] = f'q{len(seen)}'
                    rules.append((seen[expr], expr, f'{name}:{pid}'))
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / 'rules.yml'
        body = ['groups:', '- name: dashboards', '  rules:']
        for rid, expr, _ in rules:
            body += [f'  - record: dashboard:{rid}', '    expr: ' + json.dumps(expr)]
        f.write_text('\n'.join(body) + '\n', encoding='utf-8')
        res = subprocess.run([path, 'check', 'rules', str(f)], capture_output=True, text=True)
        print(res.stdout.strip() or res.stderr.strip())
        if res.returncode:
            errors.append('promtool rejected one or more expressions')
            for rid, expr, src in rules:
                one = Path(tmp) / f'{rid}.yml'
                one.write_text(f'groups:\n- name: g\n  rules:\n  - record: x:y\n    expr: {json.dumps(expr)}\n', encoding='utf-8')
                r = subprocess.run([path, 'check', 'rules', str(one)], capture_output=True, text=True)
                if r.returncode:
                    errors.append(f'  PromQL FAILED {src}: {(r.stdout + r.stderr).strip()[-300:]}')
    print(f'promtool checked {len(rules)} distinct Prometheus expressions')


def run_loki(url, models, errors):
    now = time.time_ns()
    seen, empty = set(), []
    for name, model in models.items():
        if name.endswith('-en.json'):
            continue
        for pid, title, kind, t in collect_queries(model):
            if t['datasource']['uid'] != 'loki':
                continue
            expr = substitute(t['expr'])
            mode = 'logs' if kind == 'logs' else ('instant' if t.get('instant') else 'range')
            key = (expr, mode)
            if key in seen:
                continue
            seen.add(key)
            if mode == 'instant':
                path, params = '/loki/api/v1/query', {'query': expr, 'time': now}
            else:
                params = {'query': expr, 'start': now - 900 * 10**9, 'end': now, 'step': 60, 'limit': 5}
                path = '/loki/api/v1/query_range'
            try:
                with urllib.request.urlopen(url + path + '?' + urllib.parse.urlencode(params), timeout=60) as r:
                    data = json.load(r)['data']['result']
                if not data:
                    empty.append(f'{name}:{pid} {title}')
            except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ValueError,KeyError) as e:
                status=f' HTTP {e.code}' if isinstance(e,urllib.error.HTTPError) else ''
                errors.append(f'  LogQL FAILED {name}:{pid}: {type(e).__name__}{status}')
    print(f'loki ran {len(seen)} distinct expressions; {len(empty)} returned no series (may be legitimate for synthetic data)')
    for e in empty:
        print('   empty:', e)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('directory', type=Path)
    ap.add_argument('--promtool')
    ap.add_argument('--loki')
    ap.add_argument('--export-promql-rules',type=Path,help='Write parse-only rules for container promtool; never installed as recording rules')
    ap.add_argument('--live',action='store_true',help='Read every dashboard query from local Prometheus/Loki using the safe shared auditor')
    args = ap.parse_args()
    models = {f: json.loads((args.directory / f).read_text(encoding='utf-8')) for f in FILES}
    uids = {m['uid'] for m in models.values()}
    errors = []
    if len(uids) != 4:
        errors.append('dashboard UIDs are not unique')
    for name, model in models.items():
        if len(model['uid']) > 40:
            errors.append(f'{name}: uid too long')
        check_layout(model, errors, name)
        check_semantics(model, uids, errors, name)
    check_parity(models, errors)
    check_consistency(models, errors)
    expected_titles={'matchwise-unified-monitoring.json':'MatchWise | Unified Monitoring HU','matchwise-unified-monitoring-en.json':'MatchWise | Unified Monitoring','matchwise-service-comparison.json':'MatchWise · Szolgáltatások összehasonlítása HU','matchwise-service-comparison-en.json':'MatchWise · Service Comparison'}
    for name,model in models.items():
        if model['title']!=expected_titles[name]: errors.append(name+': unexpected visible title')
        expected_uid=('matchwise-unified-overview' if 'unified' in name else 'matchwise-service-comparison')+('-en' if name.endswith('-en.json') else '')
        if model['uid']!=expected_uid: errors.append(name+': existing dashboard UID changed')
        if name.endswith('-en.json'):
            def strings(value):
                if isinstance(value,str): yield value
                elif isinstance(value,list):
                    for x in value: yield from strings(x)
                elif isinstance(value,dict):
                    for k,x in value.items():
                        if k!='expr': yield from strings(x)
            if any(re.search('[áéíóöőúüűÁÉÍÓÖŐÚÜŰ]',s) for s in strings(model)):
                errors.append(name+': untranslated Hungarian UI text')
    if args.export_promql_rules:
        expressions=sorted({substitute(t['expr']) for name,model in models.items() if not name.endswith('-en.json') for _,_,_,t in collect_queries(model) if t['datasource']['uid']=='prometheus'})
        rules={'groups':[{'name':'matchwise-dashboard-parse-only','rules':[{'record':f'matchwise_dashboard_parse:query_{i}','expr':expr} for i,expr in enumerate(expressions)]}]}
        args.export_promql_rules.write_text(json.dumps(rules,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
        print(f'Exported {len(expressions)} distinct PromQL expressions for parse-only validation.')
    if args.promtool:
        run_promtool(args.promtool, models, errors)
    if args.loki:
        run_loki(args.loki, models, errors)
    for n, m in models.items():
        print(f'{n}: {len(list(walk(m["panels"])))} panels')
    if errors:
        print('\nFAILED:')
        for e in errors:
            print(' -', e)
        sys.exit(1)
    print('OK')
    if args.live:
        path=Path(__file__).resolve().with_name('check-dashboard-final-audit.py')
        spec=importlib.util.spec_from_file_location('safe_dashboard_audit',path)
        audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
        raise SystemExit(int(audit.query_all(models,True)))


if __name__ == '__main__':
    main()
