#!/usr/bin/env python3
"""Rebuild the two MatchWise dashboards around one consistent per-service structure.

Unified Monitoring   -> one section per service (Frontend, Backend, Database, Oracle,
                        log pipeline), every service opens with the same KPI strips.
Service Comparison   -> the same panel shows every service side by side, with fixed
                        service colours (blue frontend, orange backend, green database,
                        purple Oracle) and the same units.

Reviewed queries are NOT retyped: panels and expressions that already existed are copied
from a baseline revision (default: git commit 900002e) and only re-arranged. Newly added
queries are composed from the same metrics and gating patterns.

Usage:
    scripts/build-service-dashboards.py OUTPUT_DIRECTORY [--baseline-ref REF | --baseline-dir DIR]
"""
import argparse
import copy
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
JSON_DIR = 'grafana/provisioning/dashboards/json'
FILES = {
    ('unified', 'hu'): 'matchwise-unified-monitoring.json',
    ('unified', 'en'): 'matchwise-unified-monitoring-en.json',
    ('comparison', 'hu'): 'matchwise-service-comparison.json',
    ('comparison', 'en'): 'matchwise-service-comparison-en.json',
}

LANG = 'en'


def L(hu, en):
    return hu if LANG == 'hu' else en


# ---------------------------------------------------------------- constants
PROM = {'type': 'prometheus', 'uid': 'prometheus'}
LOKI = {'type': 'loki', 'uid': 'loki'}
COLOR = {'fe': '#56B4E9', 'be': '#E69F00', 'db': '#009E73', 'or': '#B28CD9', 'log': '#8DA0CB', 'mix': '#9198A5'}
PLUGIN = '13.2.1'

FEP = 'job="blackbox_vercel_frontend",service="matchwise_frontend"'
BEP = 'job="blackbox_render_backend",service="matchwise_backend"'
DBS = 'job="supabase",instance="${supabase_instance}"'
ORS = 'job="node_exporter"'

FEG = ' and on() ((min(up{job="frontend_traffic"}) == 1) and on() (time() - max(frontend_telemetry_last_received_timestamp_seconds{job="frontend_traffic"}) < 180))'
LOKI_BASE = ('{job="matchwise_backend_render_api"} | json event="event", route="route", method="method", '
             'statusCode="statusCode", duration_ms="responseTimeMs" | event="http_request" | __error__=""')
API_ROUTES = '(/api(/.*)?|/(auth|cv|jobs|profile|preferences|me)(/.*)?)'
HEALTH = '(/api/health|/health)'


def dbg(expr):
    return f'({expr}) and on() ((min(up{{{DBS}}}) == 1) and on() (min(pg_up{{{DBS}}}) == 1))'


def org(expr):
    return f'({expr}) and on() (min(up{{{ORS}}}) == 1)'


def be_sel(x, y, extra=''):
    return f'{LOKI_BASE} | route!~"{x}" | route=~"{y}"{extra}'


def be_rate(x, y, status=''):
    """Requests per minute, zero-filled when the log stream has traffic but no match."""
    base = be_sel(x, y)
    if not status:
        return f'sum(rate({base} [5m])) * 60'
    return (f'(sum(rate({be_sel(x, y, status)} | __error__="" [5m])) or '
            f'(sum(rate({base} [5m])) * 0)) * 60')


def be_error_pct(x, y):
    base = be_sel(x, y)
    err = be_sel(x, y, ' | statusCode >= 400')
    return (f'100 * ((sum(rate({err} | __error__="" [5m])) or (sum(rate({base} [5m])) * 0)) '
            f'/ (sum(rate({base} [5m])) > 0))')


def be_p95(x, y, window='5m'):
    return f'quantile_over_time(0.95, {be_sel(x, y)} | unwrap duration_ms | __error__="" [{window}]) by (job)'


def fe_status_rate(status_regex):
    sel = 'job="frontend_traffic",mode="real"'
    return (f'((sum(rate(frontend_api_http_responses_total{{{sel},status=~"{status_regex}"}}[5m])) or on() '
            f'(0 * sum(rate(frontend_api_http_responses_total{{{sel}}}[5m])))) * 60){FEG}')


def db_error_share():
    c = f'sum(rate(pg_stat_database_xact_commit_total{{{DBS}}}[5m]))'
    r = f'sum(rate(pg_stat_database_xact_rollback_total{{{DBS}}}[5m]))'
    return dbg(f'100 * {r} / (({c} + {r}) > 0)')


# ------------------------------------------------------------ baseline access
class Baseline:
    def __init__(self, ref=None, directory=None):
        self.models = {}
        for key, name in FILES.items():
            if directory:
                raw = (Path(directory) / name).read_text(encoding='utf-8')
            else:
                raw = subprocess.check_output(['git', 'show', f'{ref}:{JSON_DIR}/{name}'], cwd=REPO).decode('utf-8')
            self.models[key] = json.loads(raw)
        self.panels = {}
        for key, model in self.models.items():
            self.panels[key] = {}
            self._flatten(model['panels'], self.panels[key])

    def _flatten(self, panels, out):
        for p in panels:
            out[p['id']] = p
            self._flatten(p.get('panels', []), out)

    def leg(self, kind, pid, w=None, h=None, title=None):
        panel = copy.deepcopy(self.panels[(kind, LANG)][pid])
        panel['_w'] = w or panel['gridPos']['w']
        panel['_h'] = h or panel['gridPos']['h']
        panel['_x'] = panel['gridPos']['x']
        panel['_y'] = panel['gridPos']['y']
        panel.pop('gridPos', None)
        if title:
            panel['title'] = title
        return panel

    def expr(self, kind, pid, index=0):
        return self.panels[(kind, 'en')][pid]['targets'][index]['expr']


# ----------------------------------------------------------------- builders
class Ids:
    def __init__(self, start):
        self.n = start

    def next(self):
        self.n += 1
        return self.n


IDS = Ids(300)


def tgt(ref, expr, kind='p', legend=None, instant=False):
    t = {'refId': ref, 'expr': expr, 'datasource': copy.deepcopy(PROM if kind == 'p' else LOKI)}
    if kind == 'l':
        t['editorMode'] = 'code'
        t['queryType'] = 'instant' if instant else 'range'
    if legend is not None:
        t['legendFormat'] = legend
    t['instant'] = instant
    t['range'] = not instant
    return t


def steps(spec):
    return [{'value': v, 'color': c} for v, c in spec]


def no_data():
    return L('Nincs adat', 'No data')


def null_map(text=None):
    return {'type': 'special', 'options': {'match': 'null', 'result': {'text': text or no_data(), 'color': 'gray'}}}


def status_map():
    return [{'type': 'value', 'options': {'0': {'text': L('NEM ELÉRHETŐ', 'DOWN'), 'color': 'red'},
                                          '1': {'text': L('ELÉRHETŐ', 'UP'), 'color': 'green'}}}, null_map()]


def ds_of(targets):
    kinds = {t['datasource']['type'] for t in targets}
    if len(kinds) > 1:
        return {'type': 'datasource', 'uid': '-- Mixed --'}
    return copy.deepcopy(targets[0]['datasource'])


PCT = [(None, 'green'), (75, 'orange'), (90, 'red')]
ERR = [(None, 'green'), (1, 'orange'), (5, 'red')]
DUR = [(None, 'green'), (2, 'orange'), (10, 'red')]
AGE = [(None, 'green'), (180, 'orange'), (300, 'red')]
OKPCT = [(None, 'red'), (95, 'orange'), (99, 'green')]
UPDOWN = [(None, 'red'), (1, 'green')]


def stat(title, desc, targets, unit='short', th=None, w=4, h=4, mappings=None, decimals=None,
         fixed=None, vmin=None, vmax=None, nv=None):
    nv = nv or no_data()
    d = {'unit': unit, 'noValue': nv, 'mappings': mappings if mappings is not None else [null_map(nv)]}
    if fixed:
        d['color'] = {'mode': 'fixed', 'fixedColor': fixed}
        d['thresholds'] = {'mode': 'absolute', 'steps': steps([(None, fixed)])}
    else:
        d['thresholds'] = {'mode': 'absolute', 'steps': steps(th or [(None, 'blue')])}
    if decimals is not None:
        d['decimals'] = decimals
    if vmin is not None:
        d['min'] = vmin
    if vmax is not None:
        d['max'] = vmax
    return {
        'id': IDS.next(), 'type': 'stat', 'title': title, 'description': desc,
        'datasource': ds_of(targets), 'targets': targets,
        'fieldConfig': {'defaults': d, 'overrides': []},
        'options': {'reduceOptions': {'values': False, 'calcs': ['lastNotNull'], 'fields': ''},
                    'orientation': 'auto', 'textMode': 'value', 'colorMode': 'value',
                    'graphMode': 'none', 'justifyMode': 'auto'},
        'pluginVersion': PLUGIN, '_w': w, '_h': h,
    }


def na_stat(title, desc, w=4, h=4):
    """Same tile as the services that do have the signal, so the grid stays aligned."""
    return stat(title, desc, [tgt('A', 'vector(1) == 0')], th=[(None, 'gray')], mappings=[],
                nv=L('n/a · nem gyűjtött', 'n/a · not collected'), w=w, h=h)


def ts(title, desc, targets, unit='short', w=12, h=8, colors=None, color=None, vmin=0, vmax=None,
       points='never', fill=3, decimals=None, th=None):
    custom = {'drawStyle': 'line', 'lineInterpolation': 'linear', 'lineWidth': 2, 'fillOpacity': fill,
              'showPoints': points, 'pointSize': 5, 'spanNulls': False, 'axisPlacement': 'auto',
              'axisColorMode': 'text', 'scaleDistribution': {'type': 'linear'},
              'stacking': {'mode': 'none', 'group': 'A'}, 'thresholdsStyle': {'mode': 'off'}}
    d = {'unit': unit, 'custom': custom, 'noValue': no_data()}
    if vmin is not None:
        d['min'] = vmin
    if vmax is not None:
        d['max'] = vmax
    if decimals is not None:
        d['decimals'] = decimals
    if color:
        d['color'] = {'mode': 'fixed', 'fixedColor': color}
    elif not colors:
        d['color'] = {'mode': 'palette-classic'}
    overrides = []
    for name, hexcolor in (colors or {}).items():
        overrides.append({'matcher': {'id': 'byName', 'options': name},
                          'properties': [{'id': 'color', 'value': {'mode': 'fixed', 'fixedColor': hexcolor}}]})
    return {
        'id': IDS.next(), 'type': 'timeseries', 'title': title, 'description': desc,
        'datasource': ds_of(targets), 'targets': targets,
        'fieldConfig': {'defaults': d, 'overrides': overrides},
        'options': {'legend': {'displayMode': 'table', 'placement': 'bottom', 'showLegend': True,
                               'calcs': ['lastNotNull']},
                    'tooltip': {'mode': 'multi', 'sort': 'desc'}},
        'pluginVersion': PLUGIN, '_w': w, '_h': h,
    }


def timeline(title, desc, targets, colors, w=24, h=7):
    return {
        'id': IDS.next(), 'type': 'state-timeline', 'title': title, 'description': desc,
        'datasource': ds_of(targets), 'targets': targets,
        'fieldConfig': {'defaults': {'unit': 'short', 'noValue': no_data(), 'mappings': status_map(),
                                     'color': {'mode': 'thresholds'},
                                     'thresholds': {'mode': 'absolute', 'steps': steps(UPDOWN)},
                                     'custom': {'lineWidth': 0, 'fillOpacity': 80,
                                                'hideFrom': {'legend': False, 'tooltip': False, 'viz': False}}},
                        'overrides': []},
        'options': {'mergeValues': True, 'showValue': 'never', 'alignValue': 'center', 'rowHeight': 0.8,
                    'legend': {'showLegend': True, 'displayMode': 'list', 'placement': 'bottom'},
                    'tooltip': {'mode': 'single', 'sort': 'none'}},
        'pluginVersion': PLUGIN, '_w': w, '_h': h,
    }


def bars(title, desc, targets, w=12, h=10):
    return {
        'id': IDS.next(), 'type': 'bargauge', 'title': title, 'description': desc,
        'datasource': ds_of(targets), 'targets': targets,
        'fieldConfig': {'defaults': {'unit': 'percent', 'min': 0, 'max': 100, 'noValue': no_data(),
                                     'decimals': 1, 'mappings': [null_map()],
                                     'color': {'mode': 'thresholds'},
                                     'thresholds': {'mode': 'absolute', 'steps': steps(PCT)}},
                        'overrides': []},
        'options': {'orientation': 'horizontal', 'displayMode': 'gradient', 'showUnfilled': True,
                    'valueMode': 'color', 'namePlacement': 'left', 'sizing': 'auto', 'minVizHeight': 16,
                    'reduceOptions': {'values': False, 'calcs': ['lastNotNull'], 'fields': ''}},
        'pluginVersion': PLUGIN, '_w': w, '_h': h,
    }


def text(title, content, desc='', w=24, h=3):
    return {'id': IDS.next(), 'type': 'text', 'title': title, 'description': desc,
            'options': {'mode': 'markdown', 'content': content}, '_w': w, '_h': h}


# ------------------------------------------------------------------- layout
class Board:
    def __init__(self):
        self.head = []   # list of (height, [panels]) outside rows
        self.rows = []
        self.row_id = 900

    def line(self, panels, h=None):
        target = self.rows[-1]['lines'] if self.rows else self.head
        height = h or max(p['_h'] for p in panels)
        target.append((height, panels))

    def row(self, title, collapsed=False):
        self.row_id += 1
        self.rows.append({'id': self.row_id, 'title': title, 'collapsed': collapsed, 'lines': []})

    def nested_legacy(self, panels):
        """Place copied panels by their original grid order, one line per original y."""
        groups = {}
        for p in panels:
            groups.setdefault(p['_y'], []).append(p)
        for y in sorted(groups):
            self.line(sorted(groups[y], key=lambda p: p['_x']))

    def build(self):
        out = []
        y = 0

        def place(lines, y0):
            placed = []
            y1 = y0
            for height, panels in lines:
                x = 0
                for p in panels:
                    q = copy.deepcopy(p)
                    q['gridPos'] = {'x': x, 'y': y1, 'w': q.pop('_w'), 'h': height}
                    for k in ('_h', '_x', '_y'):
                        q.pop(k, None)
                    x += q['gridPos']['w']
                    placed.append(q)
                y1 += height
            return placed, y1

        placed, y = place(self.head, y)
        out += placed
        for row in self.rows:
            r = {'id': row['id'], 'type': 'row', 'title': row['title'], 'collapsed': row['collapsed'],
                 'panels': [], 'gridPos': {'x': 0, 'y': y, 'w': 24, 'h': 1}}
            inner, y_end = place(row['lines'], y + 1)
            if row['collapsed']:
                r['panels'] = inner
                out.append(r)
                y += 1
            else:
                out.append(r)
                out += inner
                y = y_end
        return out


# -------------------------------------------------------- shared KPI strips
def S(name):
    return {'fe': 'Frontend', 'be': 'Backend', 'db': L('Adatbázis', 'Database'), 'or': 'Oracle'}[name]


class Q:
    """Expression library. Expressions that already existed come from the baseline."""

    def __init__(self, base):
        b = base
        self.avail = {
            'fe': f'(last_over_time(probe_success{{{FEP}}}[3m])) and on(job,instance) (up{{{FEP}}} == 1)',
            'be': f'(last_over_time(probe_success{{{BEP}}}[3m])) and on(job,instance) (up{{{BEP}}} == 1)',
            'db': f'min(pg_up{{{DBS}}}) and on() (min(up{{{DBS}}}) == 1)',
            'or': f'up{{{ORS}}}'}
        self.okrate = {
            'fe': f'100 * avg_over_time(probe_success{{{FEP}}}[$__range])',
            'be': f'100 * avg_over_time(probe_success{{{BEP}}}[$__range])',
            'db': f'100 * avg_over_time(pg_up{{{DBS}}}[$__range])',
            'or': f'100 * avg_over_time(up{{{ORS}}}[$__range])'}
        self.dur_now = {
            'fe': f'(last_over_time(probe_duration_seconds{{{FEP}}}[3m])) and on(job,instance) (up{{{FEP}}} == 1)',
            'be': f'(last_over_time(probe_duration_seconds{{{BEP}}}[3m])) and on(job,instance) (up{{{BEP}}} == 1)',
            'db': f'last_over_time(scrape_duration_seconds{{{DBS}}}[3m])',
            'or': f'last_over_time(scrape_duration_seconds{{{ORS}}}[3m])'}
        self.dur_ts = {
            'fe': f'probe_duration_seconds{{{FEP}}}', 'be': f'probe_duration_seconds{{{BEP}}}',
            'db': f'scrape_duration_seconds{{{DBS}}}', 'or': f'scrape_duration_seconds{{{ORS}}}'}
        self.age = {
            'fe': f'time() - max_over_time(timestamp(probe_success{{{FEP}}})[3m:30s])',
            'be': f'time() - max_over_time(timestamp(probe_success{{{BEP}}})[3m:30s])',
            'db': f'time() - max_over_time(timestamp(up{{{DBS}}})[3m:30s])',
            'or': f'time() - max_over_time(timestamp(up{{{ORS}}})[3m:30s])'}
        # reviewed expressions copied verbatim
        self.cpu = {'be': b.expr('comparison', 10), 'db': b.expr('comparison', 11), 'or': b.expr('comparison', 13)}
        self.mem = {'be': b.expr('comparison', 14), 'db': b.expr('comparison', 15), 'or': b.expr('comparison', 17)}
        self.fe_starts = b.expr('comparison', 41, 0)
        # Historical count ends at the selected dashboard end time. No current freshness gate.
        self.fe_calls_range = 'sum(increase(frontend_api_requests_started_total{job="frontend_traffic",mode="real"}[$__range]))'
        self.fe_mean = b.expr('comparison', 42, 0)
        self.fe_p95 = b.expr('comparison', 42, 1)
        self.fe_err_pct = b.expr('comparison', 67)
        self.fe_batch_age = b.expr('comparison', 39)
        self.db_tx_s = b.expr('unified', 86, 0)
        self.db_rb_s = b.expr('unified', 86, 1)
        self.db_conn_pct = b.expr('unified', 77)
        self.db_fs_pct = b.expr('unified', 78)
        self.db_wait = b.expr('unified', 89)
        self.or_fs_pct = b.expr('unified', 9)
        self.collector_age = b.expr('unified', 67)
        self.last_event = b.expr('unified', 64)
        self.db_tx_min = dbg(f'sum(rate(pg_stat_database_xact_commit_total{{{DBS}}}[5m])) * 60')
        self.db_rb_min = dbg(f'sum(rate(pg_stat_database_xact_rollback_total{{{DBS}}}[5m])) * 60')
        self.db_dl_min = dbg(f'sum(rate(pg_stat_database_deadlocks_total{{{DBS}}}[5m])) * 60')
        self.db_pt_min = dbg(f'sum(rate(pgrst_db_pool_timeouts_total{{{DBS}}}[5m])) * 60')
        self.db_share = db_error_share()


NA_DESC = {
    ('fe', 'cpu'): ('A Vercel host CPU-ja nincs gyűjtve.', 'Vercel host CPU is not collected.'),
    ('fe', 'mem'): ('A Vercel host memóriája nincs gyűjtve.', 'Vercel host memory is not collected.'),
}


def health_strip(q, svc, with_status=True):
    """Identical first strip for every service: status, success rate, check duration, freshness, CPU, memory."""
    name = S(svc)
    dur_desc = {
        'fe': L('Az Oracle gépről indított HTTP-próba utolsó időtartama (DNS, kapcsolat, hálózat). Nem böngészős válaszidő.',
                'Latest HTTP probe duration from the Oracle machine (DNS, connection, network). Not a browser response time.'),
        'be': L('Az Oracle gépről indított HTTP-próba utolsó időtartama (DNS, kapcsolat, hálózat). Nem alkalmazásszintű feldolgozási idő.',
                'Latest HTTP probe duration from the Oracle machine (DNS, connection, network). Not application processing time.'),
        'db': L('A Prometheus-scrape utolsó időtartama a Supabase metrikavégpontról. Nem SQL-lekérdezési idő.',
                'Latest Prometheus scrape duration for the Supabase metrics endpoint. Not SQL query time.'),
        'or': L('A Prometheus-scrape utolsó időtartama a Node Exporterről. Nem alkalmazásválaszidő.',
                'Latest Prometheus scrape duration of Node Exporter. Not an application response time.'),
    }[svc]
    avail_desc = {
        'fe': L('Az utolsó HTTP-próba 3 percen belül, csak működő exporter mellett. Nem folyamatos SLA.',
                'Latest HTTP probe within three minutes while the exporter works. Not a continuous availability SLA.'),
        'be': L('Az utolsó HTTP-próba 3 percen belül, csak működő exporter mellett. Nem folyamatos SLA.',
                'Latest HTTP probe within three minutes while the exporter works. Not a continuous availability SLA.'),
        'db': L('PostgreSQL elérhetőség (pg_up), csak sikeres Supabase-scrape mellett.',
                'PostgreSQL reachability (pg_up), shown only while the Supabase scrape succeeds.'),
        'or': L('A Node Exporter scrape sikeressége az Oracle gépen.',
                'Node Exporter scrape success on the Oracle machine.'),
    }[svc]
    out = []
    if with_status:
        out.append(stat(f'{name} · ' + L('Állapot', 'Status'), avail_desc, [tgt('A', q.avail[svc], instant=True)],
                        th=UPDOWN, mappings=status_map()))
    out.append(stat(f'{name} · ' + L('Sikeresség', 'Check success rate'),
                    L('A sikeres ellenőrzések aránya a kiválasztott időszakban (HTTP-próba vagy scrape). Nem szerződéses SLA.',
                      'Share of successful checks (HTTP probe or scrape) in the selected period. Not a contractual SLA.'),
                    [tgt('A', q.okrate[svc], instant=True)], unit='percent', th=OKPCT, decimals=2, vmin=0, vmax=100))
    out.append(stat(f'{name} · ' + L('Ellenőrzési idő', 'Check duration'), dur_desc,
                    [tgt('A', q.dur_now[svc], instant=True)], unit='s', th=DUR, decimals=2))
    out.append(stat(f'{name} · ' + L('Adatfrissesség', 'Data freshness'),
                    L('A legutóbbi tényleges minta kora (1 perces mintavétel). Hiányzó minta: nincs adat, nem nulla.',
                      'Age of the latest actual sample (one-minute sampling). A missing sample is no data, not zero.'),
                    [tgt('A', q.age[svc], instant=True)], unit='s', th=AGE, decimals=0))
    for key, label, expr_map, unit_desc in (
            ('cpu', 'CPU (%)', q.cpu, L('CPU-kihasználtság', 'CPU utilisation')),
            ('mem', L('Memória (%)', 'Memory (%)'), q.mem, L('Memóriakihasználtság', 'Memory utilisation'))):
        if svc == 'fe':
            hu, en = NA_DESC[(svc, key)]
            out.append(na_stat(f'{name} · {label}', L(hu, en)))
        else:
            extra = ''
            if svc == 'be':
                extra = L(' (Render Metrics API, külön gyűjtő).', ' (Render Metrics API, separate collector).')
            out.append(stat(f'{name} · {label}', f'{unit_desc}{extra}', [tgt('A', expr_map[svc], instant=True)],
                            unit='percent', th=PCT, vmin=0, vmax=100, decimals=1))
    return out


def traffic_strip(q, svc, filters=None):
    name = S(svc)
    if svc == 'fe':
        starts = (q.fe_calls_range, L(
            'API-hívások becsült száma a kiválasztott időablakban, Prometheus-számlálónövekményből. '
            'Egész számra kerekített megjelenítés. A csomagbeérkezés és a percenkénti mintavétel ideje számít; '
            'a frissen megjelenő sorozat első értéke nem feltétlenül számolható. A hiányzó adat nem nulla.',
            'Estimated API calls in the selected time range, from Prometheus counter increases. '
            'Displayed rounded to a whole number. Batch arrival and one-minute sampling determine timing; '
            'the first value of a new series may not be counted. Missing data is not zero.'))
        p = [
            stat(f'{name} · ' + L('API-hívások', 'API calls'), starts[1], [tgt('A', starts[0], instant=True)],
                 unit='suffix:' + L('hívás', 'calls'), fixed=COLOR['fe'], decimals=0),
            stat(f'{name} · 4xx / ' + L('perc', 'min'), L('Böngészőben látott 4xx HTTP-válaszok percenként.', '4xx HTTP responses seen in the browser per minute.'),
                 [tgt('A', fe_status_rate('4..'), instant=True)], unit='suffix:' + L('hiba/perc', 'errors/min'),
                 th=[(None, 'green'), (0.1, 'orange')], decimals=1),
            stat(f'{name} · 5xx / ' + L('perc', 'min'), L('Böngészőben látott 5xx HTTP-válaszok percenként.', '5xx HTTP responses seen in the browser per minute.'),
                 [tgt('A', fe_status_rate('5..'), instant=True)], unit='suffix:' + L('hiba/perc', 'errors/min'),
                 th=[(None, 'green'), (0.1, 'red')], decimals=1),
            stat(f'{name} · ' + L('Hibaarány (%)', 'Error rate (%)'),
                 L('4xx+5xx a böngészőben látott HTTP-válaszok között, 5 perces ablak.', '4xx+5xx share of browser-observed HTTP responses, 5-minute window.'),
                 [tgt('A', q.fe_err_pct, instant=True)], unit='percent', th=ERR, decimals=2, vmin=0),
            stat(f'{name} · ' + L('Késleltetés P95', 'Latency P95'),
                 L('Becsült P95 a válaszfejlécekig (böngészős telemetria hisztogramból).', 'Estimated P95 time to response headers (from browser telemetry histogram).'),
                 [tgt('A', q.fe_p95, instant=True)], unit='ms', th=[(None, 'green'), (1000, 'orange'), (3000, 'red')], decimals=0),
            stat(f'{name} · ' + L('Telemetria kora', 'Telemetry age'),
                 L('Az utolsó böngészős telemetriacsomag kora.', 'Age of the latest browser telemetry batch.'),
                 [tgt('A', q.fe_batch_age, instant=True)], unit='s', th=AGE, decimals=0),
        ]
        return p
    if svc == 'be':
        x, y = filters
        scope = L(' A Traffic és Route contains szűrők érvényesek.', ' Traffic and Route contains filters apply.') if '${' in x else ''
        return [
            stat(f'{name} · ' + L('Kérés / perc', 'Requests / min'), L('Naplózott HTTP-kérések percenként, 5 perces ablak.', 'Logged HTTP requests per minute, 5-minute window.') + scope,
                 [tgt('A', be_rate(x, y), 'l', instant=True)], unit='suffix:' + L('kérés/perc', 'requests/min'), fixed=COLOR['be'], decimals=1),
            stat(f'{name} · 4xx / ' + L('perc', 'min'), L('4xx válaszok percenként.', '4xx responses per minute.') + scope,
                 [tgt('A', be_rate(x, y, ' | statusCode >= 400 | statusCode < 500'), 'l', instant=True)],
                 unit='suffix:' + L('hiba/perc', 'errors/min'), th=[(None, 'green'), (0.1, 'orange')], decimals=1),
            stat(f'{name} · 5xx / ' + L('perc', 'min'), L('5xx válaszok percenként.', '5xx responses per minute.') + scope,
                 [tgt('A', be_rate(x, y, ' | statusCode >= 500'), 'l', instant=True)],
                 unit='suffix:' + L('hiba/perc', 'errors/min'), th=[(None, 'green'), (0.1, 'red')], decimals=1),
            stat(f'{name} · ' + L('Hibaarány (%)', 'Error rate (%)'), L('4xx+5xx a naplózott kérések között, 5 perces ablak.', '4xx+5xx share of logged requests, 5-minute window.') + scope,
                 [tgt('A', be_error_pct(x, y), 'l', instant=True)], unit='percent', th=ERR, decimals=2, vmin=0),
            stat(f'{name} · ' + L('Késleltetés P95', 'Latency P95'), L('Feldolgozási idő P95 a naplókból, 5 perces ablak.', 'Processing time P95 from logs, 5-minute window.') + scope,
                 [tgt('A', be_p95(x, y), 'l', instant=True)], unit='ms', th=[(None, 'green'), (1000, 'orange'), (3000, 'red')], decimals=0),
            stat(f'{name} · ' + L('Utolsó HTTP-esemény', 'Latest HTTP event'),
                 L('Az utolsó Lokiban látható HTTP-esemény ideje (utolsó óra). Forgalom nélkül nem frissül.',
                   'Time of the latest HTTP event visible in Loki (last hour). It does not advance without traffic.'),
                 [tgt('A', q.last_event, 'l', instant=True)], unit='dateTimeFromNow', th=[(None, 'blue')], decimals=1),
        ]
    if svc == 'db':
        return [
            stat(f'{name} · ' + L('Tranzakció / perc', 'Transactions / min'), L('Lezárt PostgreSQL-tranzakciók percenként; belső szolgáltatásokat is tartalmaz. Nem HTTP-kérésszám.', 'Committed PostgreSQL transactions per minute; includes internal services. Not an HTTP request count.'),
                 [tgt('A', q.db_tx_min, instant=True)], unit='suffix:' + L('tranzakció/perc', 'transactions/min'), fixed=COLOR['db'], decimals=1),
            stat(f'{name} · ' + L('Visszagörgetés / perc', 'Rollbacks / min'), L('Visszagörgetett tranzakciók percenként.', 'Rolled-back transactions per minute.'),
                 [tgt('A', q.db_rb_min, instant=True)], unit='suffix:' + L('db/perc', 'events/min'), th=[(None, 'green'), (1, 'orange')], decimals=1),
            stat(f'{name} · Deadlock / ' + L('perc', 'min'), L('PostgreSQL deadlockok percenként.', 'PostgreSQL deadlocks per minute.'),
                 [tgt('A', q.db_dl_min, instant=True)], unit='suffix:' + L('db/perc', 'events/min'), th=[(None, 'green'), (0.01, 'red')], decimals=2),
            stat(f'{name} · ' + L('Hibaarány (%)', 'Error rate (%)'), L('Visszagörgetett tranzakciók aránya. Nem HTTP-hibaarány; a visszagörgetés önmagában nem feltétlenül hiba.', 'Rolled-back share of transactions. Not an HTTP error rate; a rollback alone is not necessarily a fault.'),
                 [tgt('A', q.db_share, instant=True)], unit='percent', th=ERR, decimals=2, vmin=0),
            stat(f'{name} · ' + L('Kapcsolatok (%)', 'Connection slots (%)'), L('Használt kapcsolati helyek a maximumhoz képest.', 'Connection slots used versus the maximum.'),
                 [tgt('A', q.db_conn_pct, instant=True)], unit='percent', th=PCT, decimals=1, vmin=0, vmax=100),
            stat(f'{name} · ' + L('PostgREST várakozók', 'PostgREST waiting'), L('A PostgREST kapcsolatkészletre várakozó kérések. Nem minden PostgreSQL-várakozás.', 'Requests waiting for a PostgREST pool connection. Not all PostgreSQL waiting.'),
                 [tgt('A', q.db_wait, instant=True)], unit='suffix:' + L('kérés', 'requests'), th=[(None, 'green'), (1, 'orange'), (5, 'red')], decimals=0),
        ]
    raise ValueError(svc)


# ------------------------------------------------------------- shared series
Y4, Y5 = '#F0E442', '#F2495C'   # 4xx / 5xx colours used everywhere


def svc_names():
    return {k: S(k) for k in ('fe', 'be', 'db', 'or')}


def tile(q, svc, w):
    p = health_strip(q, svc)[0]
    p['_w'] = w
    return p


def probe_ts(q, svc, w=12):
    name = S(svc)
    label = f'{name} · ' + (L('HTTP-próba', 'HTTP probe') if svc in ('fe', 'be') else 'scrape')
    return ts(f'{name} · ' + L('Ellenőrzés időtartama', 'Check duration'),
              L('Az ellenőrzés időtartama (HTTP-próba vagy scrape). Az 1 perces mintavétel miatt a pontok önálló mérések.',
                'Duration of the check (HTTP probe or scrape). With one-minute sampling every point is an independent measurement.'),
              [tgt('A', q.dur_ts[svc], legend=label)], unit='s', w=w, color=COLOR[svc], points='always', decimals=2)


def cpu_mem_ts(q, svc, w=12):
    name = S(svc)
    cpu_l, mem_l = 'CPU', L('Memória', 'Memory')
    mem_color = {'be': '#D55E00', 'db': '#56B4E9', 'or': '#CC79A7'}[svc]
    return ts(f'{name} · ' + L('CPU és memória (%)', 'CPU and memory (%)'),
              L('Saját kapacitáshoz viszonyított kihasználtság.', 'Utilisation relative to the service\'s own capacity.'),
              [tgt('A', q.cpu[svc], legend=cpu_l), tgt('B', q.mem[svc], legend=mem_l)], unit='percent',
              colors={cpu_l: COLOR[svc], mem_l: mem_color}, vmax=100, w=w)


def fe_traffic_ts(q, w=12):
    a, c4, c5 = L('API-hívás / perc', 'API calls / min'), '4xx / ' + L('perc', 'min'), '5xx / ' + L('perc', 'min')
    return ts('Frontend · ' + L('Böngészős API-forgalom és hibák', 'Browser API traffic and errors'),
              L('A böngészőből látott API-hívások és HTTP-hibák percenként. A 0 és a hiányzó telemetria különbözik.',
                'API calls and HTTP errors seen from the browser per minute. Zero and missing telemetry differ.'),
              [tgt('A', q.fe_starts, legend=a), tgt('B', fe_status_rate('4..'), legend=c4), tgt('C', fe_status_rate('5..'), legend=c5)],
              unit='suffix:' + L('db/perc', 'events/min'), colors={a: COLOR['fe'], c4: Y4, c5: Y5}, w=w)


# ------------------------------------------------------------------ unified
def build_unified(base):
    q = Q(base)
    b = Board()
    X, Y = '${excluded_route:raw}', '.*${route_filter:regex}.*'

    b.line([text(L('MatchWise · Üzemeltetési áttekintés', 'MatchWise · Operations overview'),
                 L('**Szolgáltatásonként csoportosítva.** Állapot, sikeresség, mérési idő és adatfrissesség, majd '
                   '*forgalom · hibák · késleltetés*. CPU és memória ott szerepel, ahol ezek gyűjtöttek. '
                   'Színek: kék frontend · narancs backend · zöld adatbázis · lila Oracle.\n\n'
                   'Hiányzó adat ≠ nulla. A szolgáltatások egymás melletti összevetése: **Szolgáltatások összehasonlítása** dashboard (felső link).\n\n'
                   '**Frontend host:** a statikus Vercel-frontend host CPU-/memóriaadatai ehhez a monitoringhoz nem érhetők el; a böngészős telemetria nem méri őket. '
                   '**API-hívások:** a kiválasztott időablak becsült összes hívása, nem percenkénti átlag.',
                   '**Grouped by service.** Status, check success, check duration and freshness, followed by '
                   '*traffic · errors · latency*. CPU and memory appear where collected. '
                   'Colours: blue frontend · orange backend · green database · purple Oracle.\n\n'
                   'Missing data ≠ zero. For side-by-side comparison open the **Service Comparison** dashboard (link above).\n\n'
                   '**Frontend host:** host CPU/memory metrics for this static Vercel frontend are unavailable to this monitoring system; browser telemetry does not measure them. '
                   '**API calls:** estimated total calls in the selected time range, not a per-minute rate.'),
                 L('Az összes jelenleg gyűjtött adat áttekintése.', 'High-level view of all currently collected monitoring data.'), h=7)])

    # 00 overview
    b.row(L('00 · Áttekintés · állapot', '00 · Overview · status'))
    b.line([tile(q, s, 6) for s in ('fe', 'be', 'db', 'or')])
    ov = []
    ov.append(base.leg('unified', 10, w=6, h=4))
    be_pct = stat('Backend · ' + L('Hibaarány (%)', 'Error rate (%)'),
                  L('4xx+5xx a naplózott kérések között, 5 perces ablak. A Traffic és Route contains szűrők érvényesek.',
                    '4xx+5xx share of logged requests, 5-minute window. Traffic and Route contains filters apply.'),
                  [tgt('A', be_error_pct(X, Y), 'l', instant=True)], unit='percent', th=ERR, decimals=2, vmin=0, w=6)
    fe_pct = stat('Frontend · ' + L('Hibaarány (%)', 'Error rate (%)'),
                  L('4xx+5xx a böngészőben látott HTTP-válaszok között, 5 perces ablak.',
                    '4xx+5xx share of browser-observed HTTP responses, 5-minute window.'),
                  [tgt('A', q.fe_err_pct, instant=True)], unit='percent', th=ERR, decimals=2, vmin=0, w=6)
    lg = stat(L('Naplógyűjtő · utolsó sikeres futás kora', 'Log collector · age since successful run'),
              L('Az utolsó sikeres naplógyűjtő-futás kora. Nem az utolsó üzleti kérés kora.',
                'Seconds since the last successful log collector run. Not the age of the last business request.'),
              [tgt('A', q.collector_age, instant=True)], unit='s', th=AGE, decimals=0, w=6)
    b.line([be_pct, fe_pct, lg, ov[0]])

    # 01 frontend
    b.row('01 · Frontend · Vercel')
    frontend_health=health_strip(q, 'fe')[:4]
    for panel in frontend_health: panel['_w']=6
    b.line(frontend_health)
    b.line(traffic_strip(q, 'fe'))
    b.line([probe_ts(q, 'fe'), fe_traffic_ts(q)])
    b.row(L('01a · Frontend · HTTP-próba részletei', '01a · Frontend · HTTP probe details'), True)
    b.line([base.leg('unified', 29, 6, 4), base.leg('unified', 58, 6, 4), base.leg('unified', 54, 6, 4), base.leg('unified', 56, 6, 4)])
    b.line([base.leg('unified', 32, 12, 8), base.leg('unified', 33, 12, 8)])

    # 02 backend
    b.row('02 · Backend · Render')
    b.line(health_strip(q, 'be'))
    b.line(traffic_strip(q, 'be', (X, Y)))
    b.line([base.leg('unified', 39, 12, 8), base.leg('unified', 40, 12, 8)])
    b.line([base.leg('unified', 41, 12, 8), base.leg('unified', 42, 12, 8)])
    b.line([cpu_mem_ts(q, 'be'), probe_ts(q, 'be')])
    b.row(L('02a · Backend · Útvonalak és végpontok', '02a · Backend · Routes and endpoints'), True)
    b.line([base.leg('unified', i, 6, 4) for i in (35, 36, 37, 38)])
    b.line([base.leg('unified', i, 6, 4) for i in (60, 61, 62, 59)])
    b.line([base.leg('unified', 43, 24, 8)])
    b.line([base.leg('unified', 66, 24, 10)])
    b.row(L('02b · Backend · Hitelesítés · kiválasztott időszak', '02b · Backend · Authentication · selected period'), True)
    b.line([base.leg('unified', i, 4, 4) for i in (69, 70, 71, 72, 73, 74)])
    b.row(L('02c · Backend · HTTP-próba részletei', '02c · Backend · HTTP probe details'), True)
    b.line([base.leg('unified', i, 6, 4) for i in (23, 57, 53, 55)])
    b.line([base.leg('unified', 27, 24, 7)])

    # 03 database
    b.row(L('03 · Adatbázis · Supabase', '03 · Database · Supabase'))
    b.line(health_strip(q, 'db'))
    b.line(traffic_strip(q, 'db'))
    b.line([base.leg('unified', 86, 12, 8), base.leg('unified', 85, 12, 8)])
    b.line([base.leg('unified', 83, 12, 8), base.leg('unified', 84, 12, 8)])
    b.row(L('03a · Adatbázis · Kapacitás és részletek', '03a · Database · Capacity and details'), True)
    b.line([base.leg('unified', i, 6, 4) for i in (78, 81, 82, 75)])
    b.line([base.leg('unified', 87, 12, 8), base.leg('unified', 88, 12, 8)])
    b.line([base.leg('unified', 89, 12, 8), base.leg('unified', 90, 12, 8)])
    b.line([base.leg('unified', 91, 12, 8), base.leg('unified', 92, 12, 8)])

    # 04 Oracle
    b.row('04 · Oracle · ' + L('monitoring VM', 'monitoring VM'))
    b.line(health_strip(q, 'or'))
    errs = stat('Oracle · ' + L('Textfile-gyűjtő hiba', 'Textfile collector error'),
                L('Node Exporter textfile-scrape hibajelző: 0 = rendben, 1 = hiba.', 'Node Exporter textfile scrape error flag: 0 = OK, 1 = error.'),
                [tgt('A', org('node_textfile_scrape_error{job="node_exporter"}'), instant=True)],
                th=[(None, 'green'), (1, 'red')],
                mappings=[{'type': 'value', 'options': {'0': {'text': L('RENDBEN', 'OK'), 'color': 'green'},
                                                       '1': {'text': L('HIBA', 'ERROR'), 'color': 'red'}}}, null_map()])
    strip2 = [base.leg('unified', 12, 4, 4), base.leg('unified', 15, 4, 4), base.leg('unified', 9, 4, 4),
              base.leg('unified', 13, 4, 4), base.leg('unified', 14, 4, 4), errs]
    b.line(strip2)
    b.line([cpu_mem_ts(q, 'or'), base.leg('unified', 18, 12, 8)])
    b.row(L('04a · Oracle · Lemez, hálózat, terhelés', '04a · Oracle · Disk, network, load'), True)
    b.line([base.leg('unified', 19, 12, 8), base.leg('unified', 20, 12, 8)])
    b.line([base.leg('unified', 21, 24, 8)])

    # 05 log pipeline
    b.row(L('05 · Naplógyűjtés · frissesség és hibák', '05 · Log pipeline · freshness and errors'))
    b.line([base.leg('unified', 67, 8, 4), base.leg('unified', 63, 8, 4), base.leg('unified', 64, 8, 4)])
    b.line([base.leg('unified', 65, 24, 4)])
    b.line([base.leg('unified', 45, 12, 8), base.leg('unified', 46, 12, 8)])

    # 06 diagnostics
    b.row(L('06 · Diagnosztika · szűrt backendnaplók', '06 · Diagnostics · filtered backend logs'), True)
    b.line([base.leg('unified', 50, 24, 4)])
    b.line([base.leg('unified', 47, 24, 10)])
    b.line([base.leg('unified', 48, 24, 10)])

    m = copy.deepcopy(base.models[('unified', LANG)])
    m['panels'] = b.build()
    m['version'] = m.get('version', 1) + 1
    m['description'] = L(
        'Egységes üzemeltetési nézet szolgáltatásonként csoportosítva: Frontend (Vercel), Backend (Render), Adatbázis (Supabase), '
        'Oracle VM és naplógyűjtés. Egységes egészség- és forgalmi nézetek; CPU és memória csak gyűjtött adatforrással. '
        'A frontend API-hívásszáma a kiválasztott időablak becsült összesítése. A frontend host CPU/RAM-kártyái hiányzó adatforrás miatt nem szerepelnek.',
        'Unified operations view grouped by service: Frontend (Vercel), Backend (Render), Database (Supabase), Oracle VM and log collection. '
        'Consistent health and traffic views; CPU and memory only where collected. Frontend API calls show an estimated selected-period total. '
        'Frontend host CPU/RAM cards are omitted because this monitoring system has no data source for them.')
    return m


# --------------------------------------------------------------- comparison
def score_row(q, svc):
    name = S(svc)
    cells = [tile(q, svc, 4)]
    cells[0]['_h'] = 3
    cells.append(stat(f'{name} · ' + L('Ellenőrzés időtartama', 'Check duration'),
                      L('HTTP-próba (frontend, backend) vagy Prometheus-scrape (adatbázis, Oracle) utolsó időtartama.',
                        'Latest HTTP probe (frontend, backend) or Prometheus scrape (database, Oracle) duration.'),
                      [tgt('A', q.dur_now[svc], instant=True)], unit='s', th=DUR, decimals=2, h=3))
    traffic = {
        'fe': (q.fe_starts, 'p', L('Böngészős API-hívások percenként.', 'Browser API calls per minute.'), 'suffix:' + L('hívás/perc', 'calls/min')),
        'be': (be_rate(HEALTH, API_ROUTES), 'l', L('Naplózott API-kérések percenként (health nélkül).', 'Logged API requests per minute (health checks excluded).'), 'suffix:' + L('kérés/perc', 'requests/min')),
        'db': (q.db_tx_min, 'p', L('Lezárt PostgreSQL-tranzakciók percenként. Nem HTTP-kérés.', 'Committed PostgreSQL transactions per minute. Not HTTP requests.'), 'suffix:' + L('tranzakció/perc', 'transactions/min')),
    }
    errors = {
        'fe': (q.fe_err_pct, 'p', L('4xx+5xx a böngészőben látott HTTP-válaszok között.', '4xx+5xx share of browser-observed HTTP responses.')),
        'be': (be_error_pct(HEALTH, API_ROUTES), 'l', L('4xx+5xx a naplózott API-kérések között.', '4xx+5xx share of logged API requests.')),
        'db': (q.db_share, 'p', L('Visszagörgetett tranzakciók aránya. Nem HTTP-hibaarány.', 'Rolled-back share of transactions. Not an HTTP error rate.')),
    }
    if svc in traffic:
        e, k, d, u = traffic[svc]
        cells.append(stat(f'{name} · ' + L('Forgalom / perc', 'Traffic / min'), d, [tgt('A', e, k, instant=True)], unit=u,
                          fixed=COLOR[svc], decimals=1, h=3))
        e, k, d = errors[svc]
        cells.append(stat(f'{name} · ' + L('Hibaarány (%)', 'Error rate (%)'), d, [tgt('A', e, k, instant=True)],
                          unit='percent', th=ERR, decimals=2, vmin=0, h=3))
    else:
        cells.append(na_stat(f'{name} · ' + L('Forgalom / perc', 'Traffic / min'),
                             L('Az Oracle VM a monitoring gazdagép; alkalmazásforgalmat nem szolgál ki.', 'The Oracle VM is the monitoring host; it serves no application traffic.'), h=3))
        cells.append(na_stat(f'{name} · ' + L('Hibaarány (%)', 'Error rate (%)'),
                             L('Nincs alkalmazásszintű hibaarány az Oracle VM-en.', 'There is no application-level error rate on the Oracle VM.'), h=3))
    strip = health_strip(q, svc, with_status=False)
    cpu, mem = strip[-2], strip[-1]
    cpu['_h'] = mem['_h'] = 3
    cells += [cpu, mem]
    return cells


def build_comparison(base):
    q = Q(base)
    b = Board()
    names = svc_names()
    fe_n, be_n, db_n, or_n = (names[k] for k in ('fe', 'be', 'db', 'or'))
    colors4 = {fe_n: COLOR['fe'], be_n: COLOR['be'], db_n: COLOR['db'], or_n: COLOR['or']}

    b.line([text(L('MatchWise · Szolgáltatások összehasonlítása', 'MatchWise · Service Comparison'),
                 L('**Ugyanaz a panel minden szolgáltatásra.** Fix színek: kék frontend · narancs backend · zöld adatbázis · lila Oracle. '
                   'Az egy panelen lévő sorozatok azonos mértékegységűek; ahol a szolgáltatás nem gyűjt adatot, *n/a* jelenik meg, nem nulla.\n\n'
                   'Sorrend: **Összegzőkártya → Elérhetőség → Terhelés → Hibák → Biztonsági jelek**. Az adatbázis hibaaránya a visszagörgetett tranzakciók aránya, '
                   'a forgalma tranzakció/perc: nem HTTP-kérés. A részletes böngészős nézet a lap alján.',
                   '**The same panel for every service.** Fixed colours: blue frontend · orange backend · green database · purple Oracle. '
                   'Series on one panel share a unit; where a service collects no data the tile shows *n/a*, not zero.\n\n'
                   'Order: **Scorecard → Availability → Load → Errors → Security signals**. Database error rate is the rolled-back transaction share and its '
                   'traffic is transactions/min: not HTTP requests. The detailed browser view is at the bottom.')+'\n\n'+
                 L('**Frontend host:** a statikus Vercel-frontend host CPU-/memóriaadatai ehhez a monitoringhoz nem érhetők el; a böngészős telemetria nem méri őket. '
                   'Erőforrás-kártyák csak a backendhez, az adatbázishoz és az Oracle VM-hez szerepelnek.',
                   '**Frontend host:** host CPU/memory metrics for this static Vercel frontend are unavailable to this monitoring system; browser telemetry does not measure them. '
                   'Resource cards are shown for the backend, database and Oracle VM only.'),
                 L('Szolgáltatások egymás melletti összehasonlítása azonos felépítéssel.', 'Side-by-side service comparison with an identical structure.'), h=7)])

    b.row(L('01 · Összegzőkártya · most', '01 · Scorecard · now'))
    resource_cards=[]
    for svc in ('fe', 'be', 'db', 'or'):
        cells=score_row(q, svc)
        for panel in cells[:4]: panel['_w']=6
        b.line(cells[:4])
        if svc!='fe':
            for panel in cells[4:]: panel['_w']=8
            resource_cards.append(cells[4:])

    b.row(L('02 · Elérhetőség és adatfrissesség', '02 · Availability and freshness'))
    b.line([timeline(L('Elérhetőség · minden szolgáltatás', 'Availability · all services'),
                     L('Frontend és backend: HTTP-próba; adatbázis: pg_up; Oracle: Node Exporter scrape. Zöld = ELÉRHETŐ, piros = NEM ELÉRHETŐ, szürke = nincs adat. Nem folyamatos SLA.',
                       'Frontend and backend: HTTP probe; database: pg_up; Oracle: Node Exporter scrape. Green = UP, red = DOWN, grey = no data. Not a continuous SLA.'),
                     [tgt(r, q.avail[k], legend=names[k]) for r, k in zip('ABCD', ('fe', 'be', 'db', 'or'))], None, h=6)])
    b.line([stat(f'{names[k]} · ' + L('Ellenőrzések sikeressége', 'Check success rate'),
                 L('Sikeres ellenőrzések aránya a kiválasztott időszakban. Nem szerződéses SLA.', 'Share of successful checks in the selected period. Not a contractual SLA.'),
                 [tgt('A', q.okrate[k], instant=True)], unit='percent', th=OKPCT, decimals=2, vmin=0, vmax=100, w=6) for k in ('fe', 'be', 'db', 'or')])
    b.line([stat(f'{names[k]} · ' + L('Adatfrissesség', 'Data freshness'),
                 L('A legutóbbi tényleges minta kora (1 perces mintavétel).', 'Age of the latest actual sample (one-minute sampling).'),
                 [tgt('A', q.age[k], instant=True)], unit='s', th=AGE, decimals=0, w=6) for k in ('fe', 'be', 'db', 'or')])

    b.row(L('03 · Terhelés', '03 · Load'))
    b.line([cells[0] for cells in resource_cards])
    b.line([cells[1] for cells in resource_cards])
    lt_fe = f'{fe_n} · ' + L('böngészős API-hívás/perc', 'browser API calls/min')
    lt_be = f'{be_n} · ' + L('naplózott API-kérés/perc', 'logged API requests/min')
    b.line([
        ts(L('Forgalom · Frontend és Backend', 'Traffic · Frontend and backend'),
           L('API-forgalom percenként: a frontend a böngészőből indított hívásokat, a backend a naplózott kéréseket (health nélkül) számolja.',
             'API traffic per minute: the frontend counts browser-initiated calls, the backend logged requests (health checks excluded).'),
           [tgt('A', q.fe_starts, legend=lt_fe), tgt('B', be_rate(HEALTH, API_ROUTES), 'l', legend=lt_be)],
           unit='suffix:' + L('kérés/perc', 'requests/min'), colors={lt_fe: COLOR['fe'], lt_be: COLOR['be']}),
        ts(L('Forgalom · Adatbázis', 'Traffic · Database'),
           L('Lezárt PostgreSQL-tranzakciók percenként. Belső szolgáltatásokat is tartalmaz; nem a backend kéréseinek száma.',
             'Committed PostgreSQL transactions per minute. Includes internal services; not the backend request count.'),
           [tgt('A', q.db_tx_min, legend=f'{db_n} · ' + L('tranzakció/perc', 'transactions/min'))],
           unit='suffix:' + L('tranzakció/perc', 'transactions/min'), color=COLOR['db'])])
    b.line([
        ts('CPU (%)', L('Saját kapacitáshoz viszonyított CPU-kihasználtság. A Vercel host CPU-ja nincs gyűjtve, ezért a frontend nem szerepel.',
                        'CPU utilisation relative to each service\'s own capacity. Vercel host CPU is not collected, so the frontend is absent.'),
           [tgt('A', q.cpu['be'], legend=be_n), tgt('B', q.cpu['db'], legend=db_n), tgt('C', q.cpu['or'], legend=or_n)],
           unit='percent', colors={be_n: COLOR['be'], db_n: COLOR['db'], or_n: COLOR['or']}, vmax=100),
        ts(L('Memória (%)', 'Memory (%)'), L('Saját kapacitáshoz viszonyított memóriakihasználtság. A Vercel host memóriája nincs gyűjtve.',
                                          'Memory utilisation relative to each service\'s own capacity. Vercel host memory is not collected.'),
           [tgt('A', q.mem['be'], legend=be_n), tgt('B', q.mem['db'], legend=db_n), tgt('C', q.mem['or'], legend=or_n)],
           unit='percent', colors={be_n: COLOR['be'], db_n: COLOR['db'], or_n: COLOR['or']}, vmax=100)])
    b.line([
        ts(L('Ellenőrzés időtartama · minden szolgáltatás', 'Check duration · all services'),
           L('Frontend és backend: HTTP-próba időtartama (DNS, kapcsolat, hálózat); adatbázis és Oracle: Prometheus-scrape időtartama. Nem alkalmazásszintű válaszidő.',
             'Frontend and backend: HTTP probe duration (DNS, connection, network); database and Oracle: Prometheus scrape duration. Not application-level response time.'),
           [tgt(r, q.dur_ts[k], legend=names[k]) for r, k in zip('ABCD', ('fe', 'be', 'db', 'or'))],
           unit='s', colors=colors4, points='always', decimals=2),
        ts(L('Alkalmazási késleltetés P95 · Frontend és Backend', 'Application latency P95 · Frontend and backend'),
           L('Frontend: becsült P95 a válaszfejlécekig a böngészőből; backend: feldolgozási idő P95 a naplókból (health nélkül, API-útvonalak). Különböző mérési pont, ezért a két görbe nem azonos.',
             'Frontend: estimated P95 time to response headers from the browser; backend: processing-time P95 from logs (health excluded, API routes). Different measurement points, so the two curves are not identical.'),
           [tgt('A', q.fe_p95, legend=f'{fe_n} · P95'), tgt('B', be_p95(HEALTH, API_ROUTES), 'l', legend=f'{be_n} · P95')],
           unit='ms', colors={f'{fe_n} · P95': COLOR['fe'], f'{be_n} · P95': COLOR['be']})])
    cap_names = [
        (f'{be_n} · CPU', q.cpu['be']), (f'{db_n} · CPU', q.cpu['db']), (f'{or_n} · CPU', q.cpu['or']),
        (f'{be_n} · ' + L('memória', 'memory'), q.mem['be']), (f'{db_n} · ' + L('memória', 'memory'), q.mem['db']),
        (f'{or_n} · ' + L('memória', 'memory'), q.mem['or']),
        (f'{db_n} · ' + L('kapcsolati helyek', 'connection slots'), q.db_conn_pct),
        (f'{db_n} · ' + L('adatfájlrendszer', 'data filesystem'), q.db_fs_pct),
        (f'{or_n} · ' + L('gyökérfájlrendszer', 'root filesystem'), q.or_fs_pct)]
    b.line([bars(L('Telítettség · a saját határ százalékában', 'Saturation · percent of own limit'),
                 L('Egy nézetben minden mért kapacitásérték. Zöld < 75%, narancs 75–90%, piros ≥ 90%. A frontend nem szerepel (host-metrika nincs).',
                   'Every measured capacity value in one view. Green < 75%, orange 75–90%, red ≥ 90%. Frontend is absent (no host metrics).'),
                 [tgt(chr(65 + i), e, legend=n, instant=True) for i, (n, e) in enumerate(cap_names)], w=24, h=9)])

    b.row(L('04 · Hibák', '04 · Errors'))
    be_pct_l, fe_pct_l, db_pct_l = f'{be_n} · ' + L('HTTP-hibaarány', 'HTTP error rate'), f'{fe_n} · ' + L('HTTP-hibaarány', 'HTTP error rate'), f'{db_n} · ' + L('visszagörgetési arány', 'rollback share')
    b.line([
        ts(L('Hibaarány (%) · minden szolgáltatás', 'Error rate (%) · all services'),
           L('Frontend és backend: 4xx+5xx az HTTP-válaszok között. Adatbázis: visszagörgetett tranzakciók aránya (nem HTTP-hiba). Forgalom nélkül nincs adat.',
             'Frontend and backend: 4xx+5xx share of HTTP responses. Database: rolled-back transaction share (not an HTTP error). No data without traffic.'),
           [tgt('A', q.fe_err_pct, legend=fe_pct_l), tgt('B', be_error_pct(HEALTH, API_ROUTES), 'l', legend=be_pct_l), tgt('C', q.db_share, legend=db_pct_l)],
           unit='percent', colors={fe_pct_l: COLOR['fe'], be_pct_l: COLOR['be'], db_pct_l: COLOR['db']}),
        ts(L('5xx / perc · Frontend és Backend', '5xx / min · Frontend and backend'),
           L('Szerveroldali hibák percenként: a böngészőben látott 5xx válaszok és a backendnaplók 5xx kérései.',
             'Server-side errors per minute: 5xx responses seen in the browser and 5xx requests in backend logs.'),
           [tgt('A', fe_status_rate('5..'), legend=f'{fe_n} · 5xx'), tgt('B', be_rate(HEALTH, API_ROUTES, ' | statusCode >= 500'), 'l', legend=f'{be_n} · 5xx')],
           unit='suffix:' + L('hiba/perc', 'errors/min'), colors={f'{fe_n} · 5xx': COLOR['fe'], f'{be_n} · 5xx': COLOR['be']})])
    db_rb, db_dl, db_pt = L('Visszagörgetés / perc', 'Rollbacks / min'), L('Deadlock / perc', 'Deadlocks / min'), L('PostgREST pool-időtúllépés / perc', 'PostgREST pool timeouts / min')
    b.line([
        ts(L('4xx / perc · Frontend és Backend', '4xx / min · Frontend and backend'),
           L('Kliensoldali hibák percenként: 401/403/404/429 is ide tartozik. A részletes bontás a biztonsági jelek alatt.',
             'Client-side errors per minute, including 401/403/404/429. See the security signals below for the breakdown.'),
           [tgt('A', fe_status_rate('4..'), legend=f'{fe_n} · 4xx'), tgt('B', be_rate(HEALTH, API_ROUTES, ' | statusCode >= 400 | statusCode < 500'), 'l', legend=f'{be_n} · 4xx')],
           unit='suffix:' + L('hiba/perc', 'errors/min'), colors={f'{fe_n} · 4xx': COLOR['fe'], f'{be_n} · 4xx': COLOR['be']}),
        ts(L('Adatbázis · hibajelek / perc', 'Database · error signals / min'),
           L('Visszagörgetések, deadlockok és PostgREST pool-időtúllépések percenként. A visszagörgetés önmagában nem bizonyít hibát.',
             'Rollbacks, deadlocks and PostgREST pool timeouts per minute. A rollback alone does not prove a fault.'),
           [tgt('A', q.db_rb_min, legend=db_rb), tgt('B', q.db_dl_min, legend=db_dl), tgt('C', q.db_pt_min, legend=db_pt)],
           unit='suffix:' + L('db/perc', 'events/min'), colors={db_rb: Y4, db_dl: Y5, db_pt: COLOR['be']})])

    b.row(L('05 · Backend · biztonsági jelek', '05 · Backend · security signals'))
    b.line([base.leg('comparison', 28, 24, 4)])
    b.line([base.leg('comparison', i, 6, 4) for i in (29, 30, 31, 32)])
    b.line([base.leg('comparison', 33, 12, 8), base.leg('comparison', 34, 12, 8)])

    b.row(L('06 · Telemetria és gyűjtés egészsége', '06 · Telemetry and collection health'))
    b.line([base.leg('comparison', i, 8, 4) for i in (38, 39, 40)])
    b.line([base.leg('comparison', i, 8, 4) for i in (47, 18)] + [base.leg('comparison', 19, 8, 4)])

    b.row(L('07 · Haladó · két külön tengely', '07 · Advanced · two separate axes'), True)
    b.line([base.leg('comparison', 43, 24, 4)])
    for i in (44, 45, 46):
        b.line([base.leg('comparison', i, 24, 8)])

    b.row(L('08 · Frontend · útvonalak, hibák és kézbesítés', '08 · Frontend · routes, errors and delivery'), True)
    details = [base.leg('comparison', i) for i in range(62, 87)]
    details[0]['_h'] = 10  # The full explanation must fit with the navigation open.
    b.nested_legacy(details)

    m = copy.deepcopy(base.models[('comparison', LANG)])
    m['panels'] = b.build()
    m['version'] = m.get('version', 1) + 1
    m['description'] = L(
        'Szolgáltatások egymás melletti összehasonlítása azonos felépítéssel: összegzőkártya, elérhetőség, terhelés, hibák, '
        'biztonsági jelek. Fix szolgáltatásszínek, azonos mértékegységek, n/a ahol nincs gyűjtött adat.',
        'Side-by-side service comparison with an identical structure: scorecard, availability, load, errors, security signals. '
        'Fixed service colours, shared units, n/a where no data is collected.')
    return m


def polish_display(model, kind):
    """Presentation-only fixes confirmed against the actual Grafana renderer."""
    prefixes = ('Frontend · ', 'Backend · ', 'Database · ', 'Adatbázis · ', 'Oracle · ')
    short = {
        'Check success rate': 'Success (%)', 'Check duration': 'Check time',
        'Data freshness': 'Sample age', 'Connection slots (%)': 'Connections',
        'PostgREST waiting': 'Pool waiting', 'Latest HTTP event': 'Last request',
        'API calls / min': 'API calls', 'Transactions / min': 'Transactions',
        'Requests / min': 'Requests', 'Telemetry age': 'Batch age',
        'Root filesystem (%)': 'Root disk (%)', 'Available disk space': 'Free disk',
        'Rollbacks / min':'Rollbacks','Deadlock / min':'Deadlocks','Collector error':'Textfile error',
        'Ellenőrzési idő':'Mérési idő','API-hívás / perc':'API-hívások',
        'Tranzakció / perc':'Tranzakciók','Rollback / perc':'Rollback',
        'Deadlock / perc':'Deadlock','Késleltetés P95':'P95 idő','Telemetria kora':'Csomag kora',
        'Utolsó HTTP-hívás':'Utolsó hívás','Kapcsolatok (%)':'Kapcsolatok',
        'Rendszerterhelés · 1 perc':'Terhelés · 1p','Gyökérlemez (%)':'Gyökérlemez',
        'Elérhető memória':'Szabad RAM','Szabad lemezterület':'Szabad lemez',
        'Textfile collector error': 'Textfile error', 'System load · 1 minute': 'Load · 1 min',
        'Available memory': 'Free memory', 'Available disk': 'Free disk',
        'Visszagörgetés / perc': 'Rollback', 'PostgREST várakozók': 'Pool-sor',
        'Utolsó HTTP-esemény': 'Utolsó hívás', 'Textfile-gyűjtő hiba': 'Gyűjtőhiba',
        'Adatfrissesség':'Minta kora','Hibaarány (%)':'Hibaarány',
        'Log collector · age since successful run': 'Log collector · Sample age',
        'Backend logs · Age since successful collection': 'Backend logs · Sample age',
        'Log collector · Age since successful run': 'Log collector · Sample age',
        'Backend · HTTP 5xx · Selected period': 'Backend · 5xx in period',
        'Backend · HTTP 5xx · Kiválasztott időszak': 'Backend · 5xx (időszak)',
        'Log collector · HTTP events · Selected period': 'Log collector · HTTP events',
        'Loki · Latest HTTP event · Last hour': 'Loki · Last HTTP event',
        'Naplógyűjtő · utolsó sikeres futás kora': 'Naplógyűjtő · minta kora',
        'Backendnaplók · sikeres gyűjtés kora': 'Backendnaplók · minta kora',
        'Naplógyűjtő · HTTP-események · Kiválasztott időszak':'Naplógyűjtő · HTTP-események',
        'Loki · Legutóbbi HTTP-esemény · Utolsó óra':'Loki · Utolsó HTTP-esemény',
    }
    def strip_prefix(title):
        return next((title[len(p):] for p in prefixes if title.startswith(p)), title)
    def visit(panels, in_service=False):
        for panel in panels:
            if panel['type'] == 'row':
                in_service = kind == 'unified' and panel['title'][:2] in ('01','02','03','04')
                visit(panel.get('panels', []), in_service)
                continue
            old = panel['title']
            if panel['type'] == 'stat':
                title = strip_prefix(old) if in_service else old
                title = short.get(title, title)
                title = title.replace(' · Check success rate',' · Check success').replace(' · Data freshness',' · Sample age')
                title = title.replace(' · Ellenőrzések sikeressége',' · Sikeresség')
                title = title.replace('403 · Hozzáférés megtagadva','403 · Tiltott')
                if in_service:
                    title=title.replace(' · Selected period','').replace(' · Kiválasztott időszak','')
                    if panel['id'] in range(69,75):
                        labels=L(['Belépés · 200','Belépés · 401','Belépés · 400','Belépés · 5xx','Kilépés · 204','Regisztráció'],
                                 ['Login · 200','Login · 401','Login · 400','Login · 5xx','Logout · 204','Signup · 201'])
                        title=labels[panel['id']-69]
                if kind=='comparison' and panel['id'] in range(71,79):
                    title=L(['Folyamatban','Csomagkésés','Összesítési ablak','Fogadó sémaverzió','Sikeres küldések','Sikertelen küldések','Elveszett csomagok','Elveszett minták'],
                            ['Requests in flight','Batch delay','Batch window','Receiver schema','Successful deliveries','Failed attempts','Dropped batches','Dropped observations'])[panel['id']-71]
                if ' · 5 minutes' in title: title = title.replace(' · 5 minutes', '')
                if ' · 5 perc' in title: title = title.replace(' · 5 perc', '')
                panel['title'] = title
                if title != old:
                    panel['description'] = old+'\n\n'+panel.get('description','')
            if panel['type'] == 'state-timeline':
                # Threshold colouring produces '< 1 / 1+' instead of mapped UP/DOWN.
                panel['fieldConfig']['defaults']['color'] = {'mode':'fixed','fixedColor':'green'}
            if panel['type'] == 'timeseries' and 2 <= len(panel.get('targets',[])) <= 4:
                legend=panel.setdefault('options',{}).setdefault('legend',{})
                legend.update(displayMode='list',placement='bottom',showLegend=True)
            defaults=panel.get('fieldConfig',{}).get('defaults',{})
            if defaults.get('unit')=='percent':
                invalid={'text':L('Hibás minta','Invalid sample'),'color':'gray'}
                defaults.setdefault('mappings',[]).extend([
                    {'type':'range','options':{'from':-1e30,'to':-0.000001,'result':invalid}},
                    {'type':'range','options':{'from':100.000001,'to':1e30,'result':invalid}},
                ])
                panel['description']=panel.get('description','')+'\n\n'+L(
                    'A 0–100% tartományon kívüli érték hibás minta; nem helyettesítjük nullával.',
                    'A value outside 0–100% is an invalid sample; it is not replaced with zero.')
    visit(model['panels'])
    if kind == 'comparison':
        cards=[p for p in model['panels'] if p['type']=='stat'][:16]
        labels=[None,L('Mérési idő','Check time'),L('Forgalom','Traffic / min'),
                L('Hibaarány','Errors (%)'),'CPU (%)',L('Memória (%)','Memory (%)')]
        for i,panel in enumerate(cards):
            old=panel['title']
            panel['title']=S(('fe','be','db','or')[i//4]) if i%4==0 else labels[i%4]
            panel['description']=old+'\n\n'+panel.get('description','')
    # Grafana automatically scales milliseconds to seconds. Keep the column label unit-neutral.
    def relabel(value):
        if isinstance(value,str): return value.replace('P95 (ms)','P95')
        if isinstance(value,list): return [relabel(x) for x in value]
        if isinstance(value,dict): return {relabel(k):v if k=='expr' else relabel(v) for k,v in value.items()}
        return value
    return relabel(model)


# ---------------------------------------------------------------------- main
def main():
    global LANG
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('output', type=Path)
    ap.add_argument('--baseline-ref', default='900002e74e6889515b44bf4ac2d4a6ecd110e0b4', help='git revision holding the reviewed dashboards')
    ap.add_argument('--baseline-dir', type=Path, help='directory with the four baseline JSON files (overrides --baseline-ref)')
    args = ap.parse_args()
    base = Baseline(ref=args.baseline_ref, directory=args.baseline_dir)
    args.output.mkdir(parents=True, exist_ok=True)
    for lang in ('hu', 'en'):
        LANG = lang
        IDS.n = 300
        for kind, builder in (('unified', build_unified), ('comparison', build_comparison)):
            IDS.n = 300
            model = polish_display(builder(base), kind)
            path = args.output / FILES[(kind, lang)]
            path.write_text(json.dumps(model, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
            print('wrote', path, len(list(walk(model['panels']))), 'panels')


def walk(panels):
    for p in panels:
        yield p
        yield from walk(p.get('panels', []))


if __name__ == '__main__':
    main()
