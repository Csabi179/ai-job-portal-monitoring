#!/usr/bin/env python3
"""Read-only preflight for new frontend comparison panels. No generated traffic."""
import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, build_opener


def walk_panels(panels):
    for panel in panels:
        yield panel
        yield from walk_panels(panel.get('panels', []))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dashboard', type=Path)
    parser.add_argument('--include-database', action='store_true', help='Also check panels 43–46 using the dashboard default Supabase instance')
    parser.add_argument('--overview', action='store_true', help='Check all visible overview metrics in the redesigned dashboard')
    parser.add_argument('--frontend-details', action='store_true', help='Check all 26 metrics in the expanded frontend detail section')
    args = parser.parse_args()
    dashboard = json.loads(args.dashboard.read_text(encoding='utf-8'))
    ids = {6, 7, 8, 38, 39, 40, 41, 42, 47, 50, 51, 52, 53, 54, 55} if args.overview else set(range(38, 47 if args.include_database else 43))
    if args.frontend_details:
        if args.overview or args.include_database:
            parser.error('--frontend-details is a separate mode')
        ids = set(range(62, 87))
    panels = [panel for panel in walk_panels(dashboard['panels']) if panel['id'] in ids]
    if {panel['id'] for panel in panels} != ids:
        raise SystemExit('Missing comparison panels; wrong dashboard version.')
    instance = next((item.get('current', {}).get('value') for item in dashboard.get('templating', {}).get('list', []) if item.get('name') == 'supabase_instance'), None)
    if (args.include_database or args.overview) and (not isinstance(instance, str) or not instance):
        raise SystemExit('Missing default Supabase instance.')
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
                with opener.open(base + '?' + urlencode({'query': target['expr'].replace('\"${supabase_instance}\"', json.dumps(instance)) if (args.include_database or args.overview) else target['expr']}), timeout=30) as response:
                    result = json.load(response)
                if result.get('status') != 'success':
                    raise ValueError('Query failed')
                if result.get('warnings'):
                    raise ValueError('Query returned warnings; inspect before rollout')
                rows = result['data']['result']
                print(name, 'OK', 'series=' + str(len(rows)))
                if not rows:
                    print('  No matching observations: may mean no matching events, missing/stale input, or a newly installed metric. Not proof of zero traffic.')
            except Exception as error:
                status = f' HTTP {error.code}' if isinstance(error, HTTPError) else ''
                print(name, 'FAILED', type(error).__name__ + status)
                failed = True
    expected_queries = 26 if args.frontend_details else (23 if args.overview else (15 if args.include_database else 9))
    if queries != expected_queries:
        raise SystemExit('Unexpected query count; expected ' + str(expected_queries))
    print('Preflight FAILED' if failed else 'Preflight PASS; empty series do not prove live frontend instrumentation.')
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
