#!/usr/bin/env python3
"""Read-only validation of both timing trend modes against local Loki."""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import time
from urllib.parse import urlencode, urlparse
from urllib.error import HTTPError
from urllib.request import build_opener, ProxyHandler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--loki', default='http://127.0.0.1:3100')
    args = parser.parse_args()
    endpoint = urlparse(args.loki)
    if endpoint.scheme != 'http' or endpoint.hostname not in ('localhost', '127.0.0.1', '::1'):
        parser.error('Only local HTTP Loki endpoints are accepted')
    spec = importlib.util.spec_from_file_location('audit', Path(__file__).with_name('check-dashboard-final-audit.py'))
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    model = json.loads((args.directory / 'matchwise-service-comparison-en.json').read_text(encoding='utf-8'))
    def walk(items):
        for p in items:
            yield p
            yield from walk(p.get('panels', []))
    chart = next(p for p in walk(model['panels']) if p['id'] == 981)
    variable = next(v for v in model['templating']['list'] if v['name'] == 'timing_stat')
    opener = build_opener(ProxyHandler({}))
    now = time.time()
    for name, value in [('Average', '0'), ('P95', '1')]:
        variable['current']['value'] = value
        for interval in (60, 300):
            for target in chart['targets']:
                expr = audit.expand(target['expr'], model, 3600).replace('[1m]', f'[{interval}s]')
                params = {'query': expr, 'start': int((now - 3600) * 1e9),
                          'end': int(now * 1e9), 'step': interval}
                try:
                    with opener.open(args.loki.rstrip('/') + '/loki/api/v1/query_range?' + urlencode(params), timeout=60) as response:
                        payload = json.load(response)
                except HTTPError as exc:
                    detail = exc.read(1200).decode('utf-8', errors='replace')
                    raise RuntimeError(f'Loki rejected {name}/{interval}s/{target["legendFormat"]}: {detail}') from exc
                if payload.get('status') != 'success' or payload.get('data', {}).get('resultType') != 'matrix':
                    raise RuntimeError(f'{name}/{target["refId"]}: unexpected Loki result')
                series = payload['data']['result']
                if len(series) > 1:
                    raise RuntimeError('Expected one aggregated series, not per-request series')
                values = [float(v) for s in series for _, v in s['values']]
                if any(v < 0 for v in values if math.isfinite(v)):
                    raise RuntimeError('Negative latency returned')
                finite = sum(math.isfinite(v) for v in values)
                print(f'PASS: {name}, {interval}s, {target["legendFormat"]}: {finite} observed points, '
                      f'{len(values) - finite} empty steps')
    print('PASS: both modes and resolutions accepted by Loki. Inspect Grafana rendering separately.')


if __name__ == '__main__':
    main()
