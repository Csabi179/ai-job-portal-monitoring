#!/usr/bin/env python3
"""Read-only preflight for new frontend comparison panels. No generated traffic."""
import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, build_opener


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dashboard', type=Path)
    args = parser.parse_args()
    dashboard = json.loads(args.dashboard.read_text(encoding='utf-8'))
    panels = [panel for panel in dashboard['panels'] if panel['id'] in range(37, 43)]
    if {panel['id'] for panel in panels} != set(range(37, 43)):
        raise SystemExit('Expected six frontend comparison panels; wrong dashboard version.')
    opener = build_opener(ProxyHandler({}))
    failed = False
    queries = 0
    for panel in panels:
        for target in panel.get('targets', []):
            uid = target.get('datasource', panel.get('datasource', {})).get('uid')
            if uid not in ('prometheus', 'loki'):
                raise SystemExit('Unsupported datasource in frontend comparison panel.')
            base = 'http://127.0.0.1:9090/api/v1/query' if uid == 'prometheus' else 'http://127.0.0.1:3100/loki/api/v1/query'
            name = f"{panel['id']} {target['refId']} {uid}"
            queries += 1
            try:
                with opener.open(base + '?' + urlencode({'query': target['expr']}), timeout=30) as response:
                    result = json.load(response)
                if result.get('status') != 'success':
                    raise ValueError('Query failed')
                if result.get('warnings'):
                    raise ValueError('Query returned warnings; inspect before rollout')
                rows = result['data']['result']
                print(name, 'OK', 'series=' + str(len(rows)))
                if not rows:
                    print('  No matching observations: expected while automatic telemetry is inactive or stale.')
            except Exception as error:
                status = f' HTTP {error.code}' if isinstance(error, HTTPError) else ''
                print(name, 'FAILED', type(error).__name__ + status)
                failed = True
    if queries != 9:
        raise SystemExit('Unexpected query count; expected nine.')
    print('Preflight FAILED' if failed else 'Preflight PASS; empty series do not prove live frontend instrumentation.')
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
