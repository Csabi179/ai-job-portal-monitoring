#!/usr/bin/env python3
"""Read-only diagnosis of missing backend comparison curves; no raw logs printed."""
import json
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, build_opener

STREAM = '{job="matchwise_backend_render_api"}'
PARSED = STREAM + ' | json event="event", route="route", statusCode="statusCode", duration_ms="responseTimeMs" | event="http_request" | __error__=""'
BUSINESS = PARSED + ' | route!~"(/api/health|/health)"'

def count(expr):
    return 'sum(count_over_time(' + expr + ' [15m]))'

QUERIES = [
    ('collector_success_age_seconds', 'prometheus', 'time() - max(matchwise_render_collector_last_success_timestamp_seconds)'),
    ('frontend_starts_since_receiver_restart', 'prometheus', 'sum(frontend_api_requests_started_total{job="frontend_traffic",mode="real"})'),
    ('frontend_http_responses_since_receiver_restart', 'prometheus', 'sum(frontend_api_http_responses_total{job="frontend_traffic",mode="real"})'),
    ('backend_all_log_entries_15m', 'loki', count(STREAM)),
    ('backend_parsed_http_events_15m', 'loki', count(PARSED)),
    ('backend_non_health_events_15m', 'loki', count(BUSINESS)),
    ('backend_api_prefix_events_15m', 'loki', count(BUSINESS + ' | route=~"/api(/.*)?"')),
    ('backend_relative_api_groups_15m', 'loki', count(BUSINESS + ' | route=~"/(auth|cv|jobs|profile|preferences|me)(/.*)?"')),
    ('backend_missing_or_empty_route_15m', 'loki', count(PARSED + ' | route=""')),
    ('backend_mean_logged_duration_ms_15m', 'loki', 'avg(avg_over_time(' + BUSINESS + ' | unwrap duration_ms | __error__="" [15m]))'),
]

def main():
    opener = build_opener(ProxyHandler({}))
    failed = False
    for name, source, query in QUERIES:
        base = 'http://127.0.0.1:9090/api/v1/query' if source == 'prometheus' else 'http://127.0.0.1:3100/loki/api/v1/query'
        try:
            with opener.open(base + '?' + urlencode({'query': query}), timeout=30) as response:
                result = json.load(response)
            if result.get('status') != 'success':
                raise ValueError('Query failed')
            rows = result['data']['result']
            values = [row['value'][1] for row in rows if 'value' in row]
            print(name, 'OK', 'series=' + str(len(rows)), 'values=' + json.dumps(values))
            if result.get('warnings'):
                print('  Query warnings present; not a clean result.')
                failed = True
        except Exception as error:
            status = ' HTTP ' + str(error.code) if isinstance(error, HTTPError) else ''
            print(name, 'FAILED', type(error).__name__ + status)
            failed = True
    print('Empty series are missing observations, not proof of zero traffic.')
    return int(failed)

if __name__ == '__main__':
    raise SystemExit(main())
