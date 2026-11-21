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
        {'id': 'organize', 'options': {
            'excludeByName': {grouped_name('backend_route'): True, grouped_name('frontend_outcome'): True},
            'indexByName': {name: i for i, name in enumerate([
                grouped_name('frontend_started_ms'), grouped_name('frontend_route'),
                grouped_name('frontend_ms'), grouped_name('backend_ms'),
                grouped_name('frontend_status'), grouped_name('backend_status'), 'request_id'])},
            'renameByName': dict(zip([
                grouped_name('frontend_started_ms'), grouped_name('frontend_route'),
                grouped_name('frontend_ms'), grouped_name('backend_ms'),
                grouped_name('frontend_status'), grouped_name('backend_status'), 'request_id'],
                L(['Időpont', 'Útvonal', 'Frontend', 'Backend', 'FE státusz', 'BE státusz', 'Request ID'],
                  ['Time', 'Route', 'Frontend', 'Backend', 'FE status', 'BE status', 'Request ID']))) }},
    ])
    p['transformations'] = transforms
    p['options'] = {'showHeader': True, 'cellHeight': 'sm', 'footer': {'show': False}}
    p['fieldConfig']['overrides'] = [
        {'matcher': {'id': 'byName', 'options': grouped_name(name)}, 'properties': [
            {'id': 'unit', 'value': 'ms'},
            {'id': 'thresholds', 'value': {'mode': 'absolute', 'steps': [
                {'value': None, 'color': 'green'}, {'value': 1000, 'color': 'orange'},
                {'value': 5000, 'color': 'red'}]}},
            {'id': 'custom.width', 'value': 100},
            {'id': 'custom.cellOptions', 'value': {'type': 'auto'}},
            {'id': 'mappings', 'value': [{'type': 'special', 'options': {
                'match': 'null', 'result': {'text': '—', 'color': 'gray'}}}]}]}
        for name in ('frontend_ms', 'backend_ms')]
    p['fieldConfig']['overrides'].append({
        'matcher': {'id': 'byName', 'options': grouped_name('frontend_started_ms')},
        'properties': [{'id': 'unit', 'value': 'dateTimeAsIso'}, {'id': 'custom.width', 'value': 155}]})
    for name in ('frontend_status', 'backend_status'):
        p['fieldConfig']['overrides'].append({
            'matcher': {'id': 'byName', 'options': grouped_name(name)}, 'properties': [
                {'id': 'custom.width', 'value': 80},
                {'id': 'custom.cellOptions', 'value': {'type': 'color-background'}},
                {'id': 'color', 'value': {'mode': 'thresholds'}},
                {'id': 'thresholds', 'value': {'mode': 'absolute', 'steps': [{'value': None, 'color': 'gray'}]}},
                {'id': 'mappings', 'value': [
                    {'type': 'range', 'options': {'from': start, 'to': end, 'result': {'color': color}}}
                    for start, end, color in ((200, 399, 'green'), (400, 499, 'orange'), (500, 599, 'red'))
                ] + [{'type': 'special', 'options': {'match': 'null', 'result': {'text': '—', 'color': 'gray'}}}]}]})
    p['fieldConfig']['overrides'].extend([
        {'matcher': {'id': 'byName', 'options': grouped_name('frontend_route')},
         'properties': [{'id': 'custom.width', 'value': 160}]},
        {'matcher': {'id': 'byName', 'options': 'request_id'},
         'properties': [{'id': 'custom.width', 'value': 115}, {'id': 'custom.inspect', 'value': True}]},
    ])

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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--embed-only', type=Path, metavar='DASHBOARD_DIRECTORY',
                        help='Insert the request table and timing line chart into existing HU/EN Service Comparison JSON')
    mode.add_argument('--summary-only', type=Path, metavar='DASHBOARD_DIRECTORY',
                      help='Update only period-summary cards and event chart scales; preserve request table/chart')
    args = parser.parse_args()
    directory = args.embed_only or args.summary_only
    if directory:
        candidates = []
        for lang in ('hu', 'en'):
            suffix = '' if lang == 'hu' else '-en'
            path = directory / f'matchwise-service-comparison{suffix}.json'
            current = json.loads(path.read_text(encoding='utf-8'))
            expected_uid = 'matchwise-service-comparison' + suffix
            if current.get('uid') != expected_uid:
                raise ValueError(f'Unexpected dashboard UID: {path}')
            update = selected_period_summary if args.summary_only else embed_comparison_table
            candidates.append((path, update(current, lang)))
        # Validate both destinations before writing either file.
        for path, model in candidates:
            path.write_text(json.dumps(model, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
            print('Updated period summaries and event scales:' if args.summary_only else
                  'Updated request table and timing line chart:', path)
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
    model = embed_comparison_chart(model, table, lang)
    model = refine_comparison_scorecard(model, lang)
    model = selected_period_summary(model, lang)
    return model


def selected_period_summary(model, lang):
    """Period-wide counter rates and weighted error shares; never gate history on current health."""
    def L(hu, en):
        return hu if lang == 'hu' else en
    def walk(items):
        for item in items:
            yield item
            yield from walk(item.get('panels', []))
    panels = list(walk(model['panels']))
    start = next(i for i, p in enumerate(model['panels']) if p['type'] == 'row' and p['title'].startswith('01 ·'))
    end = next(i for i, p in enumerate(model['panels']) if p['type'] == 'row' and p['title'].startswith('02 ·'))
    cards = [p for p in model['panels'][start + 1:end] if p['type'] == 'stat']
    if len(cards) == 16:
        model['panels'][start]['title'] = L('01 · Ellenőrzések most · időszaki átlagok',
                                            '01 · Checks now · period averages')
        fe = 'job="frontend_traffic",mode="real"'
        db = 'job="supabase",instance="${supabase_instance}"'
        responses = f'sum(rate(frontend_api_http_responses_total{{{fe}}}[$__range]))'
        failures = f'sum(rate(frontend_api_http_responses_total{{{fe},status=~"4..|5.."}}[$__range]))'
        commits = f'sum(rate(pg_stat_database_xact_commit_total{{{db}}}[$__range]))'
        rollbacks = f'sum(rate(pg_stat_database_xact_rollback_total{{{db}}}[$__range]))'
        expressions = {
            2: f'sum(rate(frontend_api_requests_started_total{{{fe}}}[$__range])) * 60',
            3: f'100 * (({failures} or on() (0 * {responses})) / ({responses} > 0))',
            10: f'{commits} * 60',
            11: f'100 * {rollbacks} / (({commits} + {rollbacks}) > 0)',
        }
        for index in (2, 3, 6, 7, 10, 11):
            card = cards[index]
            for target in card['targets']:
                target['expr'] = expressions.get(index, target['expr'].replace('[5m]', '[$__range]'))
                target.update(instant=True, range=False)
            for key in ('timeFrom', 'timeShift'):
                card.pop(key, None)
            traffic = index % 4 == 2
            card['title'] = (L('Forgalom · időszaki átlag', 'Traffic · period avg') if traffic else
                             L('Rollback · időszaki arány', 'Rollback · period share') if index == 11 else
                             L('HTTP-hibák · időszaki arány', 'HTTP errors · period share'))
            card['description'] = L(
                'A kiválasztott teljes időablakra, annak végpontjában számítva. ',
                'Calculated over the entire selected time range at its end. ') + (
                L('Átlagos percenkénti forgalom; számláló-visszaállítások kezelve.',
                  'Average traffic per minute; counter resets are handled.') if traffic else
                L('Az időszak összes eseményével súlyozott hibaarány, nem a százalékok számtani átlaga.',
                  'Event-weighted share across the period, not an arithmetic mean of percentages.')) + L(
                ' Hiányos mintákból csak becslés készülhet; hiányzó adat nem nulla. Backend health checkek kizárva.',
                ' Incomplete samples can only yield an estimate; missing data is not zero. Backend health checks excluded.')
    for panel in panels:
        if panel['id'] in (29, 30, 31, 32) and panel['type'] == 'stat':
            for target in panel['targets']:
                expr = target['expr'].replace('[5m]', '[$__range]')
                # Idempotently convert period counts to average events/minute.
                if '$__range_s' not in expr:
                    expr = f'({expr}) * 60 / $__range_s'
                target['expr'] = expr
                target.update(instant=True, range=False, queryType='instant')
            for key in ('timeFrom', 'timeShift'):
                panel.pop(key, None)
            defaults = panel['fieldConfig']['defaults']
            defaults.update(unit='suffix:' + L('esemény/perc', 'events/min'), decimals=2)
            # Old count thresholds cannot be applied to a per-minute rate.
            defaults['color'] = {'mode': 'fixed', 'fixedColor': '#E69F00'}
            defaults['noValue'] = L('Nincs eseményminta', 'No event sample')
            panel['description'] = L(
                'A kiválasztott időablak eseményszáma / időtartama percben. Health checkek nélkül; hiányzó napló nem nulla.',
                'Selected-period event count / duration in minutes. Health checks excluded; absent logs are not zero.')
        if panel['id'] == 28 and panel['type'] == 'text':
            panel['options']['content'] = L(
                '**A kiválasztott teljes időablak átlaga, esemény/percben; health checkek nélkül.** '
                'A 401/403/404/429 vizsgálati jel, nem támadás bizonyítéka. Hiányzó napló nem nulla esemény. '
                'Nincs IP- vagy fiókazonosítás; a 429 önmagában nem bizonyít rate limitinget.',
                '**Average over the entire selected time range, in events/min; health checks excluded.** '
                'HTTP 401/403/404/429 are investigation signals, not proof of an attack. Missing logs do not mean zero events. '
                'No IP or account attribution is collected; a 429 does not prove rate limiting is implemented.')
        defaults = panel.get('fieldConfig', {}).get('defaults', {})
        unit = defaults.get('unit', '')
        if panel['type'] == 'timeseries' and (unit.startswith('suffix:') and any(
                word in unit for word in ('/min', '/perc')) or panel['id'] in (33, 34)):
            defaults['min'] = 0
            defaults.pop('max', None)
            custom = defaults.setdefault('custom', {})
            custom.update(axisSoftMin=0, axisSoftMax=1)
            if panel['id'] in (33, 34):
                defaults['unit'] = 'suffix:' + L('kérés/perc', 'requests/min')
    return model


def refine_comparison_scorecard(model, lang):
    """Disambiguate check status, probe duration and absent rate samples; no query changes."""
    def L(hu, en):
        return hu if lang == 'hu' else en
    start = next(i for i, p in enumerate(model['panels']) if p['type'] == 'row' and p['title'].startswith('01 ·'))
    end = next(i for i, p in enumerate(model['panels']) if p['type'] == 'row' and p['title'].startswith('02 ·'))
    cards = [p for p in model['panels'][start + 1:end] if p['type'] == 'stat']
    if len(cards) != 16:
        return model  # Preserve unfamiliar custom scorecards instead of relabelling the wrong cards.
    for index, card in enumerate(cards):
        service, column = divmod(index, 4)
        defaults = card['fieldConfig']['defaults']
        def absent(text):
            defaults['noValue'] = text
            defaults['mappings'] = [m for m in defaults.get('mappings', [])
                                    if not (m.get('type') == 'special' and m.get('options', {}).get('match') == 'null')]
            defaults['mappings'].append({'type': 'special', 'options': {
                'match': 'null', 'result': {'text': text, 'color': 'gray'}}})
        if column == 0:
            up, down = (L('HTTP ELÉRHETŐ', 'HTTP UP'), L('HTTP NEM ELÉRHETŐ', 'HTTP DOWN')) if service < 2 else (
                (L('DB ELÉRHETŐ', 'DB REACHABLE'), L('DB NEM ELÉRHETŐ', 'DB UNREACHABLE')) if service == 2 else
                (L('METRIKA ELÉRHETŐ', 'METRICS UP'), L('METRIKA NEM ELÉRHETŐ', 'METRICS DOWN')))
            defaults['mappings'] = [{'type': 'value', 'options': {
                '0': {'text': down, 'color': 'red'}, '1': {'text': up, 'color': 'green'}}}]
            absent(L('Nincs friss ellenőrzés', 'No fresh check'))
            note = L('Az állapot csak az ellenőrzött végpontra vonatkozik; üzleti kérés ettől még adhat hibát.',
                     'Status covers only the checked endpoint; business requests may still fail.')
        elif column == 1:
            card['title'] = L('HTTP-próba ideje', 'HTTP probe duration') if service < 2 else L('Scrape időtartama', 'Metrics scrape duration')
            absent(L('Nincs friss mérés', 'No fresh sample'))
            note = L('Nem a frontend felhasználói kéréseinek vagy a backend feldolgozásának válaszideje.',
                     'Not browser request latency or backend application processing time.')
        elif service == 3:
            continue  # Preserve explicitly uncollected Oracle application metrics.
        elif column == 2:
            card['title'] = L('Forgalom · 5p átlag', 'Traffic · 5m avg')
            absent(L('Nincs forgalmi minta', 'No traffic sample'))
            note = L('A hiányzó minta nem bizonyít nulla forgalmat.', 'An absent sample does not establish zero traffic.')
        else:
            card['title'] = (L('HTTP-hibák · 5p', 'HTTP errors · 5m') if service < 2 else
                             L('Rollback arány · 5p', 'Rollback share · 5m'))
            absent(L('Nincs arányminta', 'No rate sample'))
            note = L('Forgalom nélküli időszak vagy hiányzó telemetria esetén nem feltétlen számolható arány; ez nem 0%.',
                     'No traffic or missing telemetry can leave the rate undefined; that is not 0%.')
        if note not in card.get('description', ''):
            card['description'] = card.get('description', '') + '\n\n' + note
    return model


def embed_comparison_chart(model, table, lang):
    """Plot exact paired request durations over browser request start time."""
    chart = copy.deepcopy(table)
    chart.update(id=981, type='timeseries', title=(
        'Frontend és backend · válaszidő a kérések időpontjában' if lang == 'hu' else
        'Frontend and backend · response time by request time'))
    chart['description'] = (
        'X: a kérés böngészőben rögzített indítási időpontja. Y: válaszidő, közös időskálán. '
        'Kék frontend, narancssárga backend; azonos request ID alapján párosítva, a táblázat pontos értékeivel. '
        'Nincs átlagolás vagy 20-as korlát; legfeljebb 1000 naplósor oldalanként. '
        'Azonos időpontú kérések pontjai átfedhetnek. A vonal a megfigyelt kéréseket köti össze; hiányzó backendérték nem nulla.' if lang == 'hu' else
        'X: browser-recorded request start time. Y: response time on one shared duration scale. '
        'Blue frontend, orange backend, paired by request ID using the exact table values. '
        'No averaging or top-20 limit; at most 1000 log lines per side. '
        'Requests with identical timestamps may overlap. Lines connect observed requests; a missing backend value is not zero.')
    time_field = grouped_name('frontend_started_ms')
    duration_fields = [grouped_name(name) for name in ('frontend_ms', 'backend_ms')]
    transforms = copy.deepcopy(table['transformations'])
    transforms = [t for t in transforms if t['id'] not in ('organize', 'sortBy')]
    conversion = next(t for t in transforms if t['id'] == 'convertFieldType')
    next(c for c in conversion['options']['conversions'] if c['targetField'] == time_field)['destinationType'] = 'time'
    transforms.extend([
        {'id': 'filterFieldsByName', 'options': {'include': {'names': [time_field, *duration_fields]}}},
        {'id': 'sortBy', 'options': {'fields': {}, 'sort': [{'field': time_field, 'desc': False}]}},
        {'id': 'organize', 'options': {'excludeByName': {}, 'indexByName': {}, 'renameByName': {
            time_field: 'Time', duration_fields[0]: 'Frontend', duration_fields[1]: 'Backend'}}},
    ])
    chart['transformations'] = transforms
    chart['options'] = {'tooltip': {'mode': 'multi', 'sort': 'none'},
                        'legend': {'showLegend': True, 'displayMode': 'list', 'placement': 'bottom'}}
    chart['fieldConfig'] = {'defaults': {'unit': 'ms', 'min': 0, 'noValue': '—', 'custom': {
        'drawStyle': 'line', 'lineInterpolation': 'linear', 'lineWidth': 2, 'fillOpacity': 3,
        'showPoints': 'always', 'pointSize': 5, 'spanNulls': False, 'axisPlacement': 'auto',
        'axisColorMode': 'text', 'scaleDistribution': {'type': 'linear'},
        'stacking': {'mode': 'none', 'group': 'A'}, 'thresholdsStyle': {'mode': 'off'},
        'hideFrom': {'tooltip': False, 'viz': False, 'legend': False}}}, 'overrides': [
            {'matcher': {'id': 'byName', 'options': name}, 'properties': [
                {'id': 'color', 'value': {'mode': 'fixed', 'fixedColor': color}}]}
            for name, color in zip(duration_fields, ('#56B4E9', '#E69F00'))]}
    panels = model['panels']
    existing = next((i for i, p in enumerate(panels) if p['id'] == 981), None)
    if existing is not None:
        if panels[existing]['type'] not in ('barchart', 'timeseries') or 'matchwise_frontend_requests' not in json.dumps(panels[existing]):
            raise ValueError('Panel 981 is already used by an unrelated panel')
        chart['gridPos'] = copy.deepcopy(panels[existing]['gridPos'])
        old_bottom = chart['gridPos']['y'] + chart['gridPos']['h']
        delta = 8 - chart['gridPos']['h']
        chart['gridPos']['h'] = 8
        def resize_following(items):
            for panel in items:
                if panel['gridPos']['y'] >= old_bottom:
                    panel['gridPos']['y'] += delta
                resize_following(panel.get('panels', []))
        resize_following(panels)
        panels[existing] = chart
        return model
    index = next(i for i, p in enumerate(panels) if p['id'] == 980)
    start = panels[index]['gridPos']['y']
    def shift(items):
        for panel in items:
            if panel['gridPos']['y'] >= start:
                panel['gridPos']['y'] += 8
            shift(panel.get('panels', []))
    shift(panels)
    chart['gridPos'] = {'x': 0, 'y': start, 'w': 24, 'h': 8}
    panels.insert(index, chart)
    return model


if __name__ == '__main__':
    main()
