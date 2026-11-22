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
             ('frontend_method', 'method', False),
             ('frontend_route', 'route', False), ('frontend_status', 'status', False),
             ('frontend_outcome', 'outcome', False), ('frontend_started_ms', 'started_at_ms', True)]
BE_FIELDS = [('request_id', 'reqId', False), ('backend_ms', 'responseTimeMs', True),
             ('backend_route', 'route', False), ('backend_status', 'statusCode', False),
             ('backend_error_code', 'errorCode', False)]


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
    p['description'] += L(
        ' A párosítás kizárólag közös kérésazonosítóval történik, nem időpont vagy útvonal alapján. '
        'A metódus a frontend kérésből, a hibakód az azonos ID-jú backend http_request rekordból származik. '
        'Hiányzó hibakód: —; külön hibanaplóból nem következtetünk rá. Későn érkező párhoz frissíts vagy tágítsd az időablakot.',
        ' Matching uses only the shared request ID, never timestamp or route proximity. '
        'Method comes from the frontend request; error code comes from its matched backend http_request record. '
        'Missing error code: —; it is not inferred from separate error logs. Refresh or widen the range for late matches.')
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
                grouped_name('frontend_started_ms'), grouped_name('frontend_method'), grouped_name('frontend_route'),
                grouped_name('frontend_ms'), grouped_name('backend_ms'),
                grouped_name('frontend_status'), grouped_name('backend_status'), grouped_name('backend_error_code'), 'request_id'])},
            'renameByName': dict(zip([
                grouped_name('frontend_started_ms'), grouped_name('frontend_method'), grouped_name('frontend_route'),
                grouped_name('frontend_ms'), grouped_name('backend_ms'),
                grouped_name('frontend_status'), grouped_name('backend_status'), grouped_name('backend_error_code'), 'request_id'],
                L(['Időpont', 'Metódus', 'Útvonal', 'Frontend', 'Backend', 'FE státusz', 'BE státusz', 'Backend hibakód', 'Request ID'],
                  ['Time', 'Method', 'Route', 'Frontend', 'Backend', 'FE status', 'BE status', 'Backend error code', 'Request ID']))) }},
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
        {'matcher': {'id': 'byName', 'options': grouped_name('frontend_method')},
         'properties': [{'id': 'custom.width', 'value': 80}]},
        {'matcher': {'id': 'byName', 'options': grouped_name('backend_error_code')},
         'properties': [{'id': 'custom.width', 'value': 290}, {'id': 'custom.inspect', 'value': True},
                        {'id': 'mappings', 'value': [
                            {'type': 'regex', 'options': {'pattern': '^$', 'result': {'text': '—'}}},
                            {'type': 'special', 'options': {'match': 'null', 'result': {'text': '—'}}}]}]},
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
    mode.add_argument('--request-table-only', type=Path, metavar='DASHBOARD_DIRECTORY',
                      help='Update only the request tables in both HU/EN dashboard pairs; preserve all graphs')
    mode.add_argument('--embed-only', type=Path, metavar='DASHBOARD_DIRECTORY',
                        help='Insert the request table and timing line chart into existing HU/EN Service Comparison JSON')
    mode.add_argument('--summary-only', type=Path, metavar='DASHBOARD_DIRECTORY',
                      help='Update only period-summary cards and event chart scales; preserve request table/chart')
    mode.add_argument('--http-signals-only', type=Path, metavar='DASHBOARD_DIRECTORY',
                      help='Refine only HTTP access/error signals; keep both graphs in this section')
    mode.add_argument('--error-legends-only', type=Path, metavar='DASHBOARD_DIRECTORY',
                      help='Show Last* and Max together on the English Errors section charts only')
    mode.add_argument('--timing-trend-only', type=Path, metavar='DASHBOARD_DIRECTORY',
                      help='Update the Average/P95 timing trend and sample-count panel in both languages')
    args = parser.parse_args()
    if args.request_table_only:
        candidates = []
        for lang, suffix in [('hu', ''), ('en', '-en')]:
            for kind in ('service-comparison', 'request-correlation'):
                path = args.request_table_only / f'matchwise-{kind}{suffix}.json'
                model = json.loads(path.read_text(encoding='utf-8'))
                if model.get('uid') != f'matchwise-{kind}{suffix}':
                    raise ValueError(f'Unexpected dashboard UID: {path}')
                candidates.append((path, update_request_table(model, lang, 980 if kind == 'service-comparison' else 2)))
        for path, model in candidates:
            path.write_text(json.dumps(model, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
            print('Updated request table only:', path)
        return
    directory = (args.embed_only or args.summary_only or args.http_signals_only or
                 args.error_legends_only or args.timing_trend_only)
    if directory:
        candidates = []
        for lang in ('hu', 'en'):
            if args.error_legends_only and lang != 'en':
                continue
            suffix = '' if lang == 'hu' else '-en'
            path = directory / f'matchwise-service-comparison{suffix}.json'
            current = json.loads(path.read_text(encoding='utf-8'))
            expected_uid = 'matchwise-service-comparison' + suffix
            if current.get('uid') != expected_uid:
                raise ValueError(f'Unexpected dashboard UID: {path}')
            update = (update_timing_trend if args.timing_trend_only else
                      error_legend_summaries if args.error_legends_only else
                      readable_http_signals if args.http_signals_only else
                      selected_period_summary if args.summary_only else embed_comparison_table)
            candidates.append((path, update(current, lang)))
        # Validate both destinations before writing either file.
        for path, model in candidates:
            path.write_text(json.dumps(model, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
            print('Updated Average/P95 timing trend:' if args.timing_trend_only else
                  'Updated English error chart legends:' if args.error_legends_only else
                  'Updated HTTP access/error signals:' if args.http_signals_only else
                  'Updated period summaries and event scales:' if args.summary_only else
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
    return error_legend_summaries(readable_http_signals(model, lang), lang)


def error_legend_summaries(model, lang):
    """Keep Last* semantics and add Max; change only the four English error legends."""
    if lang != 'en':
        return model
    def walk(items):
        for panel in items:
            yield panel
            yield from walk(panel.get('panels', []))
    charts = [p for p in walk(model['panels']) if p['id'] in (374, 375, 376, 377)]
    if not charts:
        return model  # A custom dashboard may omit the Errors section entirely.
    if len(charts) != 4 or any(p['type'] != 'timeseries' for p in charts):
        raise ValueError('Expected the four existing Errors time-series panels (374–377)')
    for panel in charts:
        panel['options']['legend']['calcs'] = ['lastNotNull', 'max']
    return model


def readable_http_signals(model, lang):
    """Show exact counts prominently, with a small separate average below each card."""
    def L(hu, en):
        return hu if lang == 'hu' else en
    def walk(items):
        for item in items:
            yield item
            yield from walk(item.get('panels', []))
    panels = list(walk(model['panels']))
    by_id = {p['id']: p for p in panels}
    for panel in panels:
        if panel['type'] == 'row' and panel['title'].startswith('05 ·'):
            panel['title'] = L('05 · Backend · HTTP-hozzáférési és hibajelek',
                               '05 · Backend · HTTP access and error signals')
    header = by_id.get(28)
    if header and header['type'] == 'text':
        header['title'] = L('HTTP-hozzáférési és hibajelek', 'HTTP access and error signals')
        header['options']['content'] = L(
            'Összes esemény a kiválasztott időszakban; alatta az átlag percenként. Health checkek nélkül; a hiányzó adat nem nulla.',
            'Total events in the selected period; the average per minute is shown below. Health checks excluded; missing data is not zero.')
        header['description'] = L(
            'A 401/403/404/429 vizsgálati jel, nem támadás bizonyítéka. Nem gyűjtünk IP- vagy fiókazonosítást. '
            'A 429 önmagában nem bizonyít rate limitinget. Nullát csak meglévő alapforgalom mellett jelzünk; hiányzó napló nem nulla.',
            'HTTP 401/403/404/429 are investigation signals, not proof of an attack. No IP or account attribution is collected. '
            'A 429 does not prove rate limiting is implemented. Zero is shown only when base traffic exists; absent logs are not zero.')
        bottom = header['gridPos']['y'] + header['gridPos']['h']
        delta = 3 - header['gridPos']['h']
        header['gridPos']['h'] = 3
        for panel in panels:
            if panel is not header and panel['gridPos']['y'] >= bottom:
                panel['gridPos']['y'] += delta
    for offset, key in enumerate((29, 30, 31, 32)):
        card = by_id.get(key)
        if not card or card['type'] != 'stat':
            continue
        count = card['targets'][0]['expr'].replace('[5m]', '[$__range]')
        suffix = ' * 60 / $__range_s'
        if count.endswith(suffix):
            count = count[:-len(suffix)][1:-1]  # Remove the prior average wrapper only.
        card['targets'][0]['expr'] = count
        defaults = card['fieldConfig']['defaults']
        defaults.update(unit='suffix:' + L('esemény', 'events'), decimals=0,
                        color={'mode': 'thresholds'}, thresholds={'mode': 'absolute', 'steps': [
                            {'value': None, 'color': 'gray'}, {'value': 1, 'color': 'orange'}]})
        defaults['mappings'] = [{'type': 'special', 'options': {'match': 'null', 'result': {
            'text': L('Nincs eseményminta', 'No event sample'), 'color': 'gray'}}}]
        card['description'] = L('Összes naplózott esemény a kiválasztott időablakban, health checkek nélkül.',
                                'Total logged events in the selected time range, health checks excluded.')
        card['options']['textSize'] = {'value': 32}
        sub_id = 982 + offset
        existing = by_id.get(sub_id)
        if existing and not (existing.get('type') == 'stat' and '$__range_s' in json.dumps(existing.get('targets', []))
                             and existing.get('title') == ''):
            raise ValueError(f'Panel {sub_id} is already used by an unrelated panel')
        if not existing:
            card['gridPos']['h'] = max(2, card['gridPos']['h'] - 1)
        average = copy.deepcopy(card)
        average.update(id=sub_id, title='', transparent=True, description=L(
            'Az eseményszám osztva a kiválasztott időablak hosszával percben.',
            'Event count divided by the selected time range duration in minutes.'))
        average['gridPos'] = dict(card['gridPos'], y=card['gridPos']['y'] + card['gridPos']['h'], h=1)
        average['targets'][0]['expr'] = f'({count}) * 60 / $__range_s'
        average['fieldConfig']['defaults'].update(
            unit='suffix:' + L('esemény/perc · átlag', 'events/min · avg'), decimals=4,
            color={'mode': 'fixed', 'fixedColor': 'gray'})
        average['options']['textSize'] = {'value': 16}
        if existing:
            existing.clear()
            existing.update(average)
        else:
            # Keep count panels first so the four-column layout remains easy to inspect.
            model['panels'].insert(next(i for i, p in enumerate(model['panels']) if p['id'] == 33), average)
    for key in (33, 34):
        panel = by_id.get(key)
        if not panel:
            continue
        panel['options']['legend'].update(calcs=[], displayMode='list')
        labels = (['401', '403', '404', '429'] if key == 33 else
                  L(['Aktuális · 5p', 'Korábbi · 30p (−5p)'], ['Current · 5m', 'Previous · 30m (−5m)']))
        for target, label in zip(panel['targets'], labels):
            target['legendFormat'] = label
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


def ensure_timing_variable(model):
    variables = model.setdefault('templating', {}).setdefault('list', [])
    existing = next((v for v in variables if v['name'] == 'timing_stat'), None)
    if existing:
        if existing.get('type') != 'custom' or existing.get('query') != 'Average : 0,P95 : 1':
            raise ValueError('Variable timing_stat is already used by an unrelated setting')
        return
    variables.append({'name': 'timing_stat', 'label': 'Response time', 'type': 'custom',
                      'query': 'Average : 0,P95 : 1', 'current': {'text': 'Average', 'value': '0'},
                      'options': [{'text': 'Average', 'value': '0', 'selected': True},
                                  {'text': 'P95', 'value': '1', 'selected': False}],
                      'multi': False, 'includeAll': False, 'allowCustomValue': False, 'hide': 0})


def timing_sample_pipelines():
    frontend = (FE + f' | request_id=~"{UUID}" | request_id=~".*${{request_id:regex}}.*"'
                + ' | duration_ms >= 0 | __error__=""')
    # Keep the API route scope used by the other comparison panels. Exclude explicit
    # UptimeRobot markers as well as health paths; no backend/frontend join is implied.
    backend = ('{job="matchwise_backend_render_api"} !~ "(?i)uptimerobot" | json'
               ' | event="http_request"' + f' | route!~"{HEALTH}"'
               + ' | route=~"(/api(/.*)?|/(auth|cv|jobs|profile|preferences|me)(/.*)?)"'
               + f' | reqId=~"{UUID}" | reqId=~".*${{request_id:regex}}.*"'
               + ' | responseTimeMs >= 0 | __error__=""')
    return [('A', frontend, 'duration_ms', 'Frontend'), ('B', backend, 'responseTimeMs', 'Backend')]


def timing_trend_panel(lang):
    def metric(ref, pipeline, legend):
        window = pipeline + ' [$__interval]'
        # Group within the range aggregation: an average of stream averages or
        # percentile of stream percentiles would weight the observations incorrectly.
        mean = f'avg_over_time({window}) by ()'
        p95 = f'quantile_over_time(0.95, {window}) by ()'
        expr = (f'(({mean} and on() (vector(${{timing_stat:raw}}) == 0)) or '
                f'({p95} and on() (vector(${{timing_stat:raw}}) == 1)))'
                ' or (vector(0) / vector(0))')
        # Explicit NaN at empty evaluation steps preserves a gap, never a fake zero.
        return {'refId': ref, 'expr': expr, 'datasource': LOKI, 'queryType': 'range',
                'instant': False, 'range': True, 'editorMode': 'code', 'legendFormat': legend}
    return {'id': 981, 'type': 'timeseries', 'datasource': LOKI,
            'title': ('Frontend és backend · válaszidőtrend · ${timing_stat:text}' if lang == 'hu' else
                      'Frontend and backend · response time trend · ${timing_stat:text}'),
            'description': (
                'Average / P95: az összes naplózott minta időablakonkénti átlaga / 95. percentilise. '
                'Legalább 5 perces időablakok. A nagy pontok mért időszaki értékek; a szaggatott vonal '
                'csak összeköti őket, a kérésmentes szakaszokon is. Köztes válaszidőt nem mértünk. '
                'Mean / Max: a megjelenített időszaki értékek átlaga / maximuma, nem az egyedi kéréseké. '
                'X: Loki naplóidő, nem a böngésző indítási ideje; a két gyűjtés késése eltérhet. '
                'Frontend: valódi, ID-val rendelkező böngészős kérések. Backend: külön API-naplóminta; '
                'health útvonalak és kifejezett UptimeRobot-jelölések nélkül. '
                'A görbék nem ID-párosítottak; pontos párosítás a lenti táblázatban. '
                'A táblázat 1000 soros korlátja nem vonatkozik erre az összesítésre.' if lang == 'hu' else
                'Average / P95: mean / 95th percentile of all logged samples per interval. '
                'Intervals of at least 5 minutes. Large points are observed interval values; dashed lines '
                'only connect them, including across periods without requests. No latency was measured between points. '
                'Mean / Max summarize displayed interval values, not individual requests. '
                'X: Loki log time, not browser start time; collection delays may differ. '
                'Frontend: real browser requests with IDs. Backend: a separate API log population, '
                'excluding health paths and explicit UptimeRobot markers. '
                'The curves are not ID-paired; the table below provides exact matches. '
                'The table\'s 1000-line limit does not apply to these metric aggregations.'),
            'targets': [metric(ref, pipeline + f' | unwrap {field} | __error__=""', legend)
                        for ref, pipeline, field, legend in timing_sample_pipelines()],
            'transformations': [], 'interval': '5m', 'maxDataPoints': 600,
            'options': {'tooltip': {'mode': 'multi', 'sort': 'none'},
                        'legend': {'showLegend': True, 'displayMode': 'list', 'placement': 'bottom',
                                   'calcs': ['mean', 'max']}},
            'fieldConfig': {'defaults': {'unit': 'ms', 'min': 0, 'noValue': '—', 'custom': {
                'drawStyle': 'line', 'lineInterpolation': 'linear', 'lineWidth': 1, 'fillOpacity': 0,
                'lineStyle': {'fill': 'dash', 'dash': [5, 5]},
                'showPoints': 'always', 'pointSize': 7, 'spanNulls': True, 'axisPlacement': 'auto', 'axisWidth': 72,
                'axisColorMode': 'text', 'scaleDistribution': {'type': 'linear'},
                'stacking': {'mode': 'none', 'group': 'A'}, 'thresholdsStyle': {'mode': 'off'}}},
                'overrides': [{'matcher': {'id': 'byName', 'options': name}, 'properties': [
                    {'id': 'color', 'value': {'mode': 'fixed', 'fixedColor': color}}]}
                    for name, color in [('Frontend', '#56B4E9'), ('Backend', '#E69F00')]]}}


def timing_count_panel(lang):
    chart = timing_trend_panel(lang)
    chart.update(id=986, title=('Frontend és backend · az összesítés mintaszáma' if lang == 'hu' else
                                'Frontend and backend · requests per interval'), description=(
        'A fenti válaszidő-összesítéshez használt naplózott kérések száma, azonos időablakokkal és szűrőkkel. '
        'Legalább 5 perces felbontás; hosszabb időtartományban automatikusan nagyobb. '
        'Nincs oszlop: nincs naplózott minta; ez önmagában nem bizonyít nulla tényleges forgalmat.' if lang == 'hu' else
        'Number of logged requests used by the response-time summary above, with identical intervals and filters. '
        'At least 5-minute resolution, automatically coarser for longer time ranges. '
        'No bar means no logged sample; it does not establish zero actual traffic.'))
    chart['targets'] = [{'refId': ref, 'expr': f'sum(count_over_time({pipeline} [$__interval])) or (vector(0) / vector(0))',
                         'datasource': LOKI, 'queryType': 'range', 'instant': False, 'range': True,
                         'editorMode': 'code', 'legendFormat': legend}
                        for ref, pipeline, _, legend in timing_sample_pipelines()]
    chart['options']['legend']['calcs'] = []
    defaults = chart['fieldConfig']['defaults']
    defaults.update(unit='short', decimals=0)
    custom = defaults['custom']
    custom.update(drawStyle='bars', lineWidth=0, fillOpacity=80, showPoints='never', spanNulls=False,
                  lineStyle={'fill': 'solid'}, barWidthFactor=0.4, axisSoftMax=1)
    for override, alignment in zip(chart['fieldConfig']['overrides'], (-1, 1)):
        override['properties'].append({'id': 'custom.barAlignment', 'value': alignment})
    return chart


def update_timing_trend(model, lang):
    def walk(items):
        for panel in items:
            yield panel
            yield from walk(panel.get('panels', []))
    current = next((p for p in walk(model['panels']) if p['id'] == 981), None)
    if not current or current['type'] != 'timeseries' or 'matchwise_frontend_requests' not in json.dumps(current):
        raise ValueError('Expected the existing request timing chart (981)')
    count = next((p for p in walk(model['panels']) if p['id'] == 986), None)
    if count and (count['type'] != 'timeseries' or 'matchwise_frontend_requests' not in json.dumps(count)
                  or 'count_over_time' not in json.dumps(count)):
        raise ValueError('Panel 986 is already used by an unrelated panel')
    chart = timing_trend_panel(lang)
    chart['gridPos'] = copy.deepcopy(current['gridPos'])
    ensure_timing_variable(model)
    current.clear()
    current.update(chart)
    counts = timing_count_panel(lang)
    counts['gridPos'] = dict(current['gridPos'], y=current['gridPos']['y'] + current['gridPos']['h'], h=5)
    if count:
        counts['gridPos'] = copy.deepcopy(count['gridPos'])
        count.clear()
        count.update(counts)
    else:
        bottom = counts['gridPos']['y']
        for panel in walk(model['panels']):
            if panel is not current and panel['gridPos']['y'] >= bottom:
                panel['gridPos']['y'] += 5
        def insert(items):
            for i, panel in enumerate(items):
                if panel is current:
                    items.insert(i + 1, counts)
                    return True
                if insert(panel.get('panels', [])):
                    return True
            return False
        insert(model['panels'])
    return model


def update_request_table(model, lang, panel_id=980):
    """Replace table data/presentation, retaining layout and every unrelated panel."""
    result = copy.deepcopy(model)
    table = next(p for p in build(lang)['panels'] if p['type'] == 'table')
    if panel_id == 980:
        table['description'] += ('\n\nFrontend: fetch indításától a válaszfejlécekig; backend: szerveroldali feldolgozás. '
                                'Health/próbakérések kizárva. Legfeljebb 1000 naplósor oldalanként; szűkítsd az időablakot vagy adj meg request ID-t.'
                                if lang == 'hu' else
                                '\n\nFrontend: fetch until response headers; backend: server processing. '
                                'Health/backend-only probes excluded. At most 1000 log lines per side; narrow the range or filter by request ID.')
    def replace(panels):
        found = 0
        for index, panel in enumerate(panels):
            if panel.get('id') == panel_id:
                if panel.get('type') != 'table' or not any(
                        'matchwise_frontend_requests' in t.get('expr', '') for t in panel.get('targets', [])):
                    raise ValueError(f'Panel {panel_id} is not a request correlation table')
                updated = copy.deepcopy(table)
                updated.update(id=panel_id, gridPos=copy.deepcopy(panel['gridPos']))
                panels[index] = updated
                found += 1
            else:
                found += replace(panel.get('panels', []))
        return found
    if replace(result['panels']) != 1:
        raise ValueError(f'Expected exactly one request table {panel_id}')
    return result


def embed_comparison_chart(model, table, lang):
    """Build an uncapped Loki metric trend; the request table remains the paired detail view."""
    chart = timing_trend_panel(lang)
    ensure_timing_variable(model)
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
        return update_timing_trend(model, lang)
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
    return update_timing_trend(model, lang)


if __name__ == '__main__':
    main()
