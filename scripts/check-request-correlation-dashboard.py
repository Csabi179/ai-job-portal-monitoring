#!/usr/bin/env python3
"""Local model validation. Does not claim Grafana rendering or Loki delivery."""
import importlib.util
import argparse
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('builder', ROOT / 'scripts/build-request-correlation-dashboard.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--loki', help='Optional local Loki URL for read-only query syntax checks')
    args = parser.parse_args()
    models = []
    for lang in ('hu', 'en'):
        suffix = '' if lang == 'hu' else '-en'
        path = builder.DEST / f'matchwise-request-correlation{suffix}.json'
        model = json.loads(path.read_text(encoding='utf-8'))
        assert model == builder.build(lang), f'Rebuild {path}'
        assert len(model['uid']) <= 40
        panels = model['panels']
        for index, panel in enumerate(panels):
            a = panel['gridPos']
            assert 0 <= a['x'] and a['x'] + a['w'] <= 24
            for other in panels[index + 1:]:
                b = other['gridPos']
                assert not (a['x'] < b['x'] + b['w'] and b['x'] < a['x'] + a['w']
                            and a['y'] < b['y'] + b['h'] and b['y'] < a['y'] + a['h'])
        table = next(p for p in panels if p['type'] == 'table')
        transforms = table['transformations']
        assert any(t['id'] == 'joinByField' and t['options']['byField'] == 'request_id' for t in transforms)
        assert any(t['id'] == 'filterByValue' and t['options']['filters'][0]['fieldName'] == 'frontend_route'
                   for t in transforms), 'Backend-only probes must not enter the correlation table'
        for panel in panels:
            for target in panel['targets']:
                if target['datasource']['type'] == 'loki':
                    assert 'route!~"/(api/)?health/?"' in target['expr']
        queries = [t['expr'] for p in panels for t in p['targets']]
        models.append(queries)
        print(f'PASS: {lang}, {len(panels)} panels; layout and correlation guards')
    assert models[0] == models[1], 'HU/EN queries must match'
    if args.loki:
        if args.loki != 'http://127.0.0.1:3100':
            parser.error('Only the local Oracle Loki endpoint is supported')
        opener = build_opener(ProxyHandler({}))
        now = time.time_ns()
        for expression in models[0]:
            if not expression.startswith('{job='):
                continue
            expression = expression.replace('${request_id:regex}', '').replace('${slow_ms:raw}', '1000')
            params = {'query': expression, 'start': now - 300_000_000_000,
                      'end': now, 'limit': 1, 'direction': 'backward'}
            with opener.open(args.loki + '/loki/api/v1/query_range?' + urlencode(params), timeout=15) as response:
                assert json.load(response).get('status') == 'success'
        print('PASS: live Loki accepts all new log queries (empty results allowed).')
    print('Inspect Grafana rendering and real request delivery separately.')


if __name__ == '__main__':
    main()
