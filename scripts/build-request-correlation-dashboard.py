#!/usr/bin/env python3
"""Build a separate HU/EN request correlation view; preserve existing dashboards."""
import json
import copy
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'grafana/provisioning/dashboards/json'
LOKI = {'type': 'loki', 'uid': 'loki'}
PROM = {'type': 'prometheus', 'uid': 'prometheus'}
HEALTH = '/(api/)?health/?'
UUID = '[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}'
FE = ('{job="matchwise_frontend_requests"} | json | event="frontend_request"'
      f' | mode="real" | route!~"{HEALTH}" | __error__=""')
BE = ('{job="matchwise_backend_render_api"} | json | event="http_request"'
      f' | route!~"{HEALTH}" | __error__=""')


def project(fields):
    parts = []
    for name, source, numeric in fields:
        template = '{{.' + source + '}}' if numeric else '{{ printf "%q" .' + source + ' }}'
        parts.append(json.dumps(name) + ':' + template)
    return ' | line_format `' + '{' + ','.join(parts) + '}' + '`'


FE_FIELDS = [('request_id', 'request_id', False), ('frontend_ms', 'duration_ms', True),
             ('frontend_route', 'route', False), ('frontend_status', 'status', False),
             ('frontend_outcome', 'outcome', False), ('frontend_started_ms', 'started_at_ms', True)]
BE_FIELDS = [('request_id', 'reqId', False), ('backend_ms', 'responseTimeMs', True),
             ('backend_route', 'route', False), ('backend_status', 'statusCode', False)]


def grouped_name(name):
    # Grafana groupBy changes the raw field identity. Display-name renames do
    # not survive every downstream join, so use the real names until the end.
    return name if name == 'request_id' else name + ' (lastNotNull)'


FRONT = (FE + f' | request_id=~"{UUID}" | request_id=~".*${{request_id:regex}}.*"'
         + project(FE_FIELDS))
BACK = (BE + f' | reqId=~"{UUID}" | reqId=~".*${{request_id:regex}}.*"'
        + ' | responseTimeMs >= 0 | __error__=""' + project(BE_FIELDS))


def target(ref, expr, ds=LOKI):
    return {'refId': ref, 'expr': expr, 'datasource': ds, 'queryType': 'range',
            'editorMode': 'code', 'maxLines': 1000}


def build(lang):
    def L(hu, en):
        return hu if lang == 'hu' else en
    panels = []
    def panel(kind, title, x, y, w, h, targets=None, description=''):
        p = {'id': len(panels) + 1, 'type': kind, 'title': title,
             'gridPos': {'x': x, 'y': y, 'w': w, 'h': h}, 'description': description,
             'fieldConfig': {'defaults': {'noValue': '—'}, 'overrides': []},
             'options': {}, 'targets': targets or []}
        if targets:
            p['datasource'] = targets[0]['datasource']
        panels.append(p)
        return p

    p = panel('text', L('Frontend és backend kérések', 'Frontend and backend requests'), 0, 0, 24, 5)
    p['options'] = {'mode': 'markdown', 'content': L(
        '**Párosítás: frontend `request_id` = backend `reqId`.** A felső táblázat közös ID alapján mutatja a két időt. '
        'A frontend a fetch indításától a válaszfejlécekig mér; a backend a szerveroldali feldolgozást. '
        'A különbség nem tisztán hálózati idő. Hiányzó pár ≠ nulla idő. Az ID nélküli hibák lent külön láthatók. '
        'UptimeRobot/health kérések kizárva; csak frontend által jelentett kérések jelennek meg a táblázatban. '
        'Csak valódi mód; a böngészőadat nem hitelesített. Legfeljebb 1000 naplósor/oldal/lekérdezés: szűkítsd az időablakot vagy adj meg ID-t. '
        'A két gyűjtési idő eltér: késő backendpárhoz frissíts vagy tágítsd az időablakot.',
        '**Match: frontend `request_id` = backend `reqId`.** The top table compares timings by the shared ID. '
        'Frontend measures fetch until response headers; backend measures server processing. '
        'Their difference is not pure network time. A missing match is not zero latency. ID-less failures appear separately below. '
        'UptimeRobot/health checks are excluded; the table only retains requests reported by the frontend. '
        'Real mode only; browser reports are untrusted. Maximum 1000 log lines per side/query: narrow the time range or enter an ID. '
        'Collection times differ: refresh or widen the time range for delayed backend matches.')}

    p = panel('table', L('Kérésenkénti idő és státusz', 'Timing and status per request'), 0, 5, 24, 12,
              [target('A', FRONT), target('B', BACK)],
              L('Külső összekapcsolás ID alapján. Üres frontend/backend cella: a kiválasztott ablakban nincs pár. '
                'Az ID nélküli rekordokat nem kapcsoljuk össze egymással.',
                'Outer join by ID. Empty frontend/backend cells mean no match in the selected window. '
                'Records without IDs are never joined to each other.'))
    transforms = []
    for ref, fields in [('A', FE_FIELDS), ('B', BE_FIELDS)]:
        filt = {'id': 'byRefId', 'options': ref}
        transforms.extend([
            {'id': 'extractFields', 'filter': filt,
             'options': {'source': 'Line', 'format': 'json', 'replace': True, 'keepTime': False}},
            {'id': 'groupBy', 'filter': filt, 'options': {'fields': {
                name: {'operation': 'groupby', 'aggregations': []} if name == 'request_id' else
                      {'operation': 'aggregate', 'aggregations': ['lastNotNull']}
                for name, _, _ in fields}}},
        ])
    transforms.extend([
        {'id': 'joinByField', 'options': {'byField': 'request_id', 'mode': 'outerTabular'}},
        {'id': 'filterByValue', 'options': {'type': 'include', 'match': 'all', 'filters': [
            {'fieldName': grouped_name('frontend_route'), 'config': {'id': 'isNotNull', 'options': {}}}]}},
        {'id': 'convertFieldType', 'options': {'conversions': [
            {'targetField': grouped_name(f), 'destinationType': 'number'}
            for f in ('frontend_ms', 'backend_ms', 'frontend_started_ms')]}},
        {'id': 'sortBy', 'options': {'fields': {}, 'sort': [{'field': grouped_name('frontend_ms'), 'desc': True}]}},
        # Presentation renames are applied after joins, filters and sorting.
        {'id': 'organize', 'options': {'excludeByName': {}, 'indexByName': {},
         'renameByName': {grouped_name(name): name for name, _, _ in FE_FIELDS + BE_FIELDS
                          if name != 'request_id'}}},
    ])
    p['transformations'] = transforms
    p['options'] = {'showHeader': True, 'cellHeight': 'sm', 'footer': {'show': False}}
    p['fieldConfig']['overrides'] = [
        {'matcher': {'id': 'byName', 'options': grouped_name(name)}, 'properties': [
            {'id': 'unit', 'value': 'ms'},
            {'id': 'thresholds', 'value': {'mode': 'absolute', 'steps': [
                {'value': None, 'color': 'green'}, {'value': 1000, 'color': 'orange'},
                {'value': 5000, 'color': 'red'}]}},
            {'id': 'custom.cellOptions', 'value': {'type': 'color-background'}}]}
        for name in ('frontend_ms', 'backend_ms')]
    p['fieldConfig']['overrides'].append({
        'matcher': {'id': 'byName', 'options': grouped_name('frontend_started_ms')},
        'properties': [{'id': 'unit', 'value': 'dateTimeAsIso'}]})

    p = panel('logs', L('Lassú vagy hibás frontendkérések', 'Slow or failed frontend requests'), 0, 17, 24, 9,
              [target('A', FE + ' | duration_ms >= ${slow_ms:raw} or status=~"[45][0-9][0-9]" or outcome!="http"'
                      ' | __error__="" | request_id=~".*${request_id:regex}.*"')],
              L('Lassúsági küszöb ms-ban; 4xx/5xx, hálózati hiba és megszakítás. ID nélkül is megmaradnak.',
                'Slow threshold in ms; 4xx/5xx, network errors and aborts. Retains records without IDs.'))
    p['options'] = {'showTime': True, 'sortOrder': 'Descending', 'wrapLogMessage': True,
                    'enableLogDetails': True, 'showLabels': False}
    p = panel('logs', L('ID nélküli frontendkérések', 'Frontend requests without a backend ID'), 0, 26, 24, 8,
              [target('A', FE + ' | request_id=""')],
              L('Nem csak hálózati hibák: a proxy/fejléc hiánya esetén sikeres HTTP-válasz is lehet.',
                'Includes HTTP responses without an exposed/preserved ID, not only network failures.'))
    p['options'] = {'showTime': True, 'sortOrder': 'Descending', 'wrapLogMessage': True,
                    'enableLogDetails': True, 'showLabels': False}
    for index, (metric, title) in enumerate([
        ('frontend_telemetry_request_records_total', L('Fogadott részletes rekordok', 'Received request details')),
        ('frontend_telemetry_request_records_without_id_total', L('ID nélkül fogadott rekordok', 'Received details without ID')),
        ('frontend_telemetry_reported_dropped_requests_total', L('Frontend által eldobott rekordok', 'Details dropped by frontend')),
    ]):
        p = panel('stat', title, index * 8, 34, 8, 4,
                  [target('A', f'sum(increase({metric}{{job="frontend_traffic",mode="real"}}[$__range]))', PROM)])
        p['options'] = {'reduceOptions': {'calcs': ['lastNotNull'], 'values': False}, 'colorMode': 'value'}
        p['description'] = L('Becsült számlálónövekedés a kiválasztott időszakban; nem a párosított kérések száma.',
                             'Estimated counter increase over the selected range; not a count of matched requests.')
    suffix = '' if lang == 'hu' else '-en'
    return {'uid': 'matchwise-request-correlation' + suffix,
            'title': 'MatchWise · ' + L('Kérések összekapcsolása HU', 'Request Correlation'),
            'schemaVersion': 39, 'version': 1, 'timezone': 'browser', 'editable': False,
            'tags': ['matchwise', 'request-correlation', lang], 'refresh': '1m',
            'time': {'from': 'now-30m', 'to': 'now'}, 'panels': panels,
            'templating': {'list': [
                {'name': 'request_id', 'label': L('Request ID · üres = mind', 'Request ID · empty = all'),
                 'type': 'textbox', 'query': '', 'current': {'text': '', 'value': ''}, 'options': []},
                {'name': 'slow_ms', 'label': L('Lassúság (ms)', 'Slow threshold (ms)'), 'type': 'custom',
                 'query': '500,1000,2500,5000,10000', 'current': {'text': '1000', 'value': '1000'},
                 'options': [{'text': str(v), 'value': str(v), 'selected': v == 1000}
                             for v in (500, 1000, 2500, 5000, 10000)], 'multi': False}],},
            'links': [{'title': L('Szolgáltatások összehasonlítása', 'Service Comparison'), 'type': 'link',
                       'url': '/d/matchwise-service-comparison' + suffix, 'keepTime': True},
                      {'title': L('English', 'Magyar'), 'type': 'link',
                       'url': '/d/matchwise-request-correlation' + ('-en' if lang == 'hu' else ''),
                       'keepTime': True}]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--embed-only', type=Path, metavar='DASHBOARD_DIRECTORY',
                        help='Insert only the request table into existing HU/EN Service Comparison JSON')
    args = parser.parse_args()
    if args.embed_only:
        candidates = []
        for lang in ('hu', 'en'):
            suffix = '' if lang == 'hu' else '-en'
            path = args.embed_only / f'matchwise-service-comparison{suffix}.json'
            current = json.loads(path.read_text(encoding='utf-8'))
            expected_uid = 'matchwise-service-comparison' + suffix
            if current.get('uid') != expected_uid:
                raise ValueError(f'Unexpected dashboard UID: {path}')
            candidates.append((path, embed_comparison_table(current, lang)))
        # Validate both destinations before writing either file.
        for path, model in candidates:
            path.write_text(json.dumps(model, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
            print('Inserted request table:', path)
        return
    for lang in ('hu', 'en'):
        suffix = '' if lang == 'hu' else '-en'
        path = DEST / f'matchwise-request-correlation{suffix}.json'
        path.write_text(json.dumps(build(lang), ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        for kind in ('unified-monitoring', 'service-comparison'):
            existing = DEST / f'matchwise-{kind}{suffix}.json'
            model = json.loads(existing.read_text(encoding='utf-8'))
            if kind == 'service-comparison':
                model = embed_comparison_table(model, lang)
            url = '/d/matchwise-request-correlation' + suffix
            links = model.setdefault('links', [])
            if not any(link.get('url') == url for link in links):
                links.append({'type': 'link', 'title': 'Kérések összekapcsolása' if lang == 'hu' else 'Request Correlation',
                              'url': url, 'keepTime': True})
                existing.write_text(json.dumps(model, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
            else:
                # Keep generated files byte-identical on Windows and Linux.
                existing.write_text(json.dumps(model, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def embed_comparison_table(model, lang):
    """Add only the proven table, preserving existing panels, filters and identities."""
    model = copy.deepcopy(model)
    table = copy.deepcopy(next(p for p in build(lang)['panels'] if p['type'] == 'table'))
    table['id'] = 980
    table['description'] += ('\n\nFrontend: fetch indításától a válaszfejlécekig; backend: szerveroldali feldolgozás. '
                            'Health/próbakérések kizárva. Legfeljebb 1000 naplósor oldalanként; szűkítsd az időablakot vagy adj meg request ID-t.'
                            if lang == 'hu' else
                            '\n\nFrontend: fetch until response headers; backend: server processing. '
                            'Health/backend-only probes excluded. At most 1000 log lines per side; narrow the range or filter by request ID.')
    panels = model['panels']
    existing = next((i for i, p in enumerate(panels) if p['id'] == 980), None)
    if existing is not None:
        if panels[existing]['type'] != 'table' or 'frontend_ms' not in json.dumps(panels[existing]):
            raise ValueError('Panel 980 is already used by an unrelated panel')
        table['gridPos'] = copy.deepcopy(panels[existing]['gridPos'])
        panels[existing] = table
    else:
        index = next(i for i, p in enumerate(panels)
                     if p['type'] == 'row' and p['title'].startswith('02 ·'))
        if not any(p['type'] == 'row' and p['title'].startswith('01 ·') for p in panels[:index]):
            raise ValueError('Scorecard row must precede availability')
        start = panels[index]['gridPos']['y']
        height = 12
        def shift(items):
            for panel in items:
                if panel['gridPos']['y'] >= start:
                    panel['gridPos']['y'] += height
                shift(panel.get('panels', []))
        shift(panels)
        table['gridPos'] = {'x': 0, 'y': start, 'w': 24, 'h': height}
        panels.insert(index, table)
    variables = model.setdefault('templating', {}).setdefault('list', [])
    if not any(v['name'] == 'request_id' for v in variables):
        variables.append(copy.deepcopy(next(v for v in build(lang)['templating']['list'] if v['name'] == 'request_id')))
    return model


if __name__ == '__main__':
    main()
