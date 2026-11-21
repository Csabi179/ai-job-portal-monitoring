#!/usr/bin/env python3
"""Read-only local Loki check: compare a recent browser record with its backend ID."""
import argparse
import json
import re
import time
from urllib.parse import urlencode
from urllib.request import build_opener, ProxyHandler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request-id', help='Optional backend UUID from a real browser request')
    args = parser.parse_args()
    uuid = r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}'
    if args.request_id and not re.fullmatch(uuid, args.request_id, re.I):
        parser.error('request ID must be a UUID')
    opener = build_opener(ProxyHandler({}))
    end = time.time_ns()
    def query(expr):
        url = 'http://127.0.0.1:3100/loki/api/v1/query_range?' + urlencode({
            'query': expr, 'start': end - 3600_000_000_000, 'end': end,
            'limit': 1000, 'direction': 'backward'})
        with opener.open(url, timeout=15) as response:
            data = json.load(response)
        if data.get('status') != 'success':
            raise SystemExit('Loki query failed')
        rows = [(int(ts), json.loads(line)) for stream in data['data']['result']
                for ts, line in stream['values']]
        return [row for _, row in sorted(rows, key=lambda value: value[0], reverse=True)]
    selected = args.request_id.lower() if args.request_id else ''
    fe = query('{job="matchwise_frontend_requests"} | json | event="frontend_request"'
               ' | mode="real" | route!~"/(api/)?health/?" | request_id!="" | __error__=""'
               + (f' | request_id="{selected}"' if selected else ''))
    fe = [row for row in fe if isinstance(row.get('request_id'), str)
          and re.fullmatch(uuid, row['request_id'])]
    if not fe:
        raise SystemExit('No recent real frontend record with an ID. Check frontend flags, receiver and Alloy.')
    ids = {row['request_id'] for row in fe[:100]}
    expression = '|'.join(sorted(ids))
    be = query('{job="matchwise_backend_render_api"} | json | event="http_request"'
               ' | route!~"/(api/)?health/?" | __error__=""' + f' | reqId=~"{expression}"')
    by_id = {row.get('reqId'): row for row in be}
    for front in fe:
        back = by_id.get(front['request_id'])
        if back is not None:
            print(json.dumps({'request_id': front['request_id'], 'frontend_ms': front['duration_ms'],
                              'backend_ms': back.get('responseTimeMs'), 'frontend_status': front['status'],
                              'backend_status': back.get('statusCode'), 'route': front['route']}))
            print('PASS: one real ID matched in Loki. Inspect the Grafana table separately.')
            return
    raise SystemExit('Frontend details exist but no backend match yet; inspect collector delay and the shared ID.')


if __name__ == '__main__':
    main()
