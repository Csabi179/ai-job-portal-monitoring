#!/usr/bin/env python3
"""Browser v1/v2 telemetry -> Prometheus aggregates and bounded request JSONL."""
import collections
import json
import math
import os
import re
import threading
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PATH = '/matchwise-telemetry/v1'
LIMITS = [100, 250, 500, 1000, 2500, 5000, 10000, 30000, 60000]
ROUTES = {'auth', 'jobs', 'cv', 'profile', 'preferences', 'me', 'other'}
METHODS = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS', 'OTHER'}
OUTCOMES = {'http', 'network_error', 'aborted'}
MAX_RESULT_SERIES = 4096
DELIVERY_FIELDS = ('sent_batches', 'failed_attempts', 'dropped_batches', 'dropped_observations')
ORIGINS = frozenset(os.environ.get('FRONTEND_TRAFFIC_ORIGINS', 'https://www.matchwise.tech,https://matchwise.tech').split(','))
REQUEST_ROUTES = {'/auth/register', '/auth/login', '/auth/logout', '/me', '/account',
                  '/cv', '/cv/upload', '/profile', '/jobs', '/preferences', '/ai/usage',
                  '/cv/:id/download', '/cv/:id/profile', '/jobs/:id', 'unmatched'}
HEALTH_ROUTES = {'/health', '/api/health', '/health/', '/api/health/'}
REQUEST_ID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', re.I)


def validate_requests(batch):
    rows = batch['requests']
    if type(rows) is not list or len(rows) > 64:
        raise ValueError('requests')
    integer(batch['dropped_requests'])
    for row in rows:
        exact_keys(row, 'request_id started_at_ms finished_at_ms duration_ms route method status outcome')
        rid = row['request_id']
        if rid is not None and (type(rid) is not str or not REQUEST_ID.fullmatch(rid)):
            raise ValueError('request id')
        start = integer(row['started_at_ms'], 2**53 - 1)
        end = integer(row['finished_at_ms'], 2**53 - 1)
        duration = number(row['duration_ms'], 3_600_000)
        # Browser duration uses a monotonic clock; finished_at is rounded to ms.
        if end < start or abs(end - start - duration) > 1:
            raise ValueError('request timing')
        if row['route'] not in REQUEST_ROUTES | HEALTH_ROUTES or row['method'] not in METHODS:
            raise ValueError('request dimensions')
        if row['outcome'] not in OUTCOMES:
            raise ValueError('request outcome')
        status = row['status']
        if row['outcome'] == 'http':
            if status != 'other' and not (type(status) is int and 100 <= status <= 599):
                raise ValueError('request status')
        elif type(status) is not int or status != 0 or rid is not None:
            raise ValueError('request failure')


class RequestJournal:
    """Bounded JSONL for Alloy. Never use request IDs as stream/metric labels."""
    def __init__(self, path, max_bytes=20_000_000, backups=7):
        self.path = Path(path)
        self.max_bytes = max_bytes
        self.backups = backups

    def write(self, records):
        if not records:
            return
        data = ''.join(json.dumps(row, separators=(',', ':'), allow_nan=False) + '\n'
                       for row in records).encode('utf-8')
        if self.path.exists() and self.path.stat().st_size + len(data) > self.max_bytes:
            for index in range(self.backups, 0, -1):
                source = self.path if index == 1 else Path(str(self.path) + f'.{index - 1}')
                if source.exists():
                    os.replace(source, Path(str(self.path) + f'.{index}'))
        with self.path.open('ab', buffering=0) as output:
            offset = output.tell()
            try:
                remaining = memoryview(data)
                while remaining:
                    written = output.write(remaining)
                    if not written:
                        raise OSError('incomplete journal write')
                    remaining = remaining[written:]
                os.fsync(output.fileno())
            except OSError:
                # Avoid concatenating a partial JSON line with the next retry.
                os.ftruncate(output.fileno(), offset)
                raise


def integer(value, maximum=1_000_000_000):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError('integer')
    return value


def number(value, maximum):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= maximum:
        raise ValueError('number')
    return value


def exact_keys(value, keys):
    if type(value) is not dict or set(value) != set(keys.split()):
        raise ValueError('fields')


def validate(batch):
    if type(batch) is not dict:
        raise ValueError('batch')
    version = batch.get('schema_version')
    if type(version) is not int or version not in (1, 2):
        raise ValueError('version')
    fields = 'schema_version batch_id window_start_ms window_end_ms interval_ms timing mock_api mock_jobs inflight duration_limits_ms starts results delivery'
    exact_keys(batch, fields + (' requests dropped_requests' if version == 2 else ''))
    if version == 2:
        validate_requests(batch)
    if not isinstance(batch['batch_id'], str) or not re.fullmatch(r'[a-fA-F0-9-]{36}', batch['batch_id']):
        raise ValueError('id')
    start = integer(batch['window_start_ms'], 2**53 - 1)
    end = integer(batch['window_end_ms'], 2**53 - 1)
    if not 0 <= end - start <= 7 * 86400_000:
        raise ValueError('window')
    if type(batch['interval_ms']) is not int or batch['interval_ms'] != 60_000 or batch['timing'] != 'fetch_response_headers':
        raise ValueError('timing')
    if batch['duration_limits_ms'] != LIMITS:
        raise ValueError('bins')
    if type(batch['mock_api']) is not bool or type(batch['mock_jobs']) is not bool:
        raise ValueError('mock')
    integer(batch['inflight'])
    exact_keys(batch['delivery'], 'sent_batches failed_attempts dropped_batches dropped_observations')
    for value in batch['delivery'].values():
        integer(value)
    for name, maximum in [('starts', 56), ('results', 128)]:
        rows = batch[name]
        if type(rows) is not list or len(rows) > maximum:
            raise ValueError('rows')
        seen = set()
        for row in rows:
            exact_keys(row, 'route method count' if name == 'starts' else
                       'route method status outcome count duration_sum_ms duration_max_ms duration_bins')
            if row['route'] not in ROUTES or row['method'] not in METHODS:
                raise ValueError('dimensions')
            count = integer(row['count'])
            key = (row['route'], row['method'])
            if name == 'results':
                outcome, status = row['outcome'], row['status']
                if outcome not in OUTCOMES:
                    raise ValueError('outcome')
                if outcome == 'http':
                    if status != 'other' and not (type(status) is int and 100 <= status <= 599):
                        raise ValueError('status')
                elif type(status) is not int or status != 0:
                    raise ValueError('status')
                bins = row['duration_bins']
                if type(bins) is not list or len(bins) != len(LIMITS) + 1:
                    raise ValueError('bins')
                if sum(integer(value) for value in bins) != count:
                    raise ValueError('bin count')
                total = number(row['duration_sum_ms'], count * 3_600_000)
                peak = number(row['duration_max_ms'], 3_600_000)
                tolerance = 1e-6 * max(1, total)
                if peak > total + tolerance or (count == 0 and peak != 0) or total > count * peak + tolerance:
                    raise ValueError('duration')
                key += (outcome, str(status))
            if key in seen:
                raise ValueError('duplicate row')
            seen.add(key)
    return batch


class State:
    def __init__(self, journal=None):
        self.journal = journal
        self.lock = threading.Lock()
        self.metrics = collections.defaultdict(float)
        self.seen = collections.OrderedDict()
        self.requests = collections.deque()
        self.last_received = 0
        self.created = time.time()
        self.result_series = set()
        for name in ['frontend_telemetry_batches_total', 'frontend_telemetry_duplicate_batches_total',
                     'frontend_telemetry_rejected_total', 'frontend_telemetry_rate_limited_total']:
            self.add(name)

    def add(self, name, value=0, **labels):
        self.metrics[(name, tuple(sorted(labels.items())))] += value

    def set_value(self, name, value, **labels):
        self.metrics[(name, tuple(sorted(labels.items())))] = value

    def keep_max(self, name, value, **labels):
        key = (name, tuple(sorted(labels.items())))
        self.metrics[key] = max(self.metrics.get(key, 0), value)

    def allow(self):
        with self.lock:
            now = time.monotonic()
            while self.requests and self.requests[0] <= now - 60:
                self.requests.popleft()
            if len(self.requests) >= 600:
                self.add('frontend_telemetry_rate_limited_total', 1)
                return False
            self.requests.append(now)
            return True

    def reject(self):
        with self.lock:
            self.add('frontend_telemetry_rejected_total', 1)

    def ingest(self, batch):
        # Validate the whole object before changing counters.
        validate(batch)
        with self.lock:
            now = time.monotonic()
            while self.seen and next(iter(self.seen.values())) < now - 600:
                self.seen.popitem(last=False)
            batch_id = batch['batch_id']
            received = time.time()
            if batch_id in self.seen:
                self.last_received = received
                self.add('frontend_telemetry_duplicate_batches_total', 1)
                return
            mode = 'partial_mock' if batch['mock_api'] or batch['mock_jobs'] else 'real'
            records = []
            skipped = 0
            for index, row in enumerate(batch.get('requests', [])):
                if row['route'] in HEALTH_ROUTES:
                    skipped += 1
                    continue
                rid = row['request_id'].lower() if row['request_id'] else None
                records.append({**row, 'request_id': rid,
                                'event_id': f'{batch_id.lower()}:{index}',
                                'event': 'frontend_request', 'mode': mode,
                                'received_at_ms': round(received * 1000)})
            # Persist before acknowledging or counting the batch. Disk errors are retryable.
            if records:
                if self.journal is None:
                    raise OSError('request journal not configured')
                self.journal.write(records)
            self.last_received = received
            self.seen[batch_id] = now
            while len(self.seen) > 8192:
                self.seen.popitem(last=False)
            self.add('frontend_telemetry_batches_total', 1)
            if batch['schema_version'] == 2:
                self.add('frontend_telemetry_request_records_total', len(records), mode=mode)
                self.add('frontend_telemetry_request_records_without_id_total', sum(r['request_id'] is None for r in records), mode=mode)
                self.add('frontend_telemetry_reported_dropped_requests_total', batch['dropped_requests'], mode=mode)
                self.add('frontend_telemetry_excluded_health_records_total', skipped, mode=mode)
            self.add('frontend_telemetry_result_dimension_overflow_total', mode=mode)
            # Snapshots belong to the LAST reporting page, not all open browsers.
            # No stable client identifier is sent: cumulative delivery snapshots
            # cannot be summed or differenced safely across pages.
            self.set_value('frontend_telemetry_mode_last_received_timestamp_seconds', self.last_received, mode=mode)
            self.set_value('frontend_telemetry_reported_inflight', batch['inflight'], mode=mode)
            self.set_value('frontend_telemetry_reported_window_start_timestamp_seconds', batch['window_start_ms'] / 1000, mode=mode)
            self.set_value('frontend_telemetry_reported_window_end_timestamp_seconds', batch['window_end_ms'] / 1000, mode=mode)
            self.set_value('frontend_telemetry_reported_window_seconds', (batch['window_end_ms'] - batch['window_start_ms']) / 1000, mode=mode)
            # Signed, reception-time observation, including client clock skew.
            self.set_value('frontend_telemetry_reported_window_end_age_seconds', self.last_received - batch['window_end_ms'] / 1000, mode=mode)
            for field in DELIVERY_FIELDS:
                value = batch['delivery'][field]
                self.set_value('frontend_telemetry_reported_delivery', value, mode=mode, kind=field)
                self.keep_max('frontend_telemetry_reported_delivery_max', value, mode=mode, kind=field)
                if field != 'sent_batches':
                    self.add('frontend_telemetry_reports_with_delivery_issue_total', int(value > 0), mode=mode, kind=field)
            for row in batch['starts']:
                self.add('frontend_api_requests_started_total', row['count'], mode=mode,
                         route=row['route'], method=row['method'])
            for row in batch['results']:
                labels = dict(mode=mode, route=row['route'], outcome=row['outcome'])
                result_labels = dict(labels, method=row['method'], status=str(row['status']))
                series = tuple(sorted(result_labels.items()))
                if series not in self.result_series:
                    if len(self.result_series) < MAX_RESULT_SERIES:
                        self.result_series.add(series)
                    else:
                        # Keep overall outcomes/counts; fold only excess detailed dimensions.
                        result_labels.update(route='other', method='OTHER', status='other')
                        self.add('frontend_telemetry_result_dimension_overflow_total', row['count'], mode=mode)
                self.add('frontend_api_results_total', row['count'], **result_labels)
                if row['count']:
                    self.keep_max('frontend_api_fetch_headers_max_seconds', row['duration_max_ms'] / 1000, **labels)
                self.add('frontend_api_outcomes_total', row['count'], **labels)
                if row['outcome'] == 'http':
                    self.add('frontend_api_http_responses_total', row['count'], mode=mode, status=str(row['status']))
                name = 'frontend_api_fetch_headers_seconds'
                self.add(name + '_sum', row['duration_sum_ms'] / 1000, **labels)
                self.add(name + '_count', row['count'], **labels)
                cumulative = 0
                for bound, count in zip([*LIMITS, '+Inf'], row['duration_bins']):
                    cumulative += count
                    self.add(name + '_bucket', cumulative, le=str(bound / 1000) if bound != '+Inf' else '+Inf', **labels)

    def render(self):
        with self.lock:
            lines = ['# TYPE frontend_api_fetch_headers_seconds histogram',
                     'frontend_telemetry_receiver_schema_version 3',
                     '# TYPE frontend_api_results_total counter',
                     '# TYPE frontend_api_fetch_headers_max_seconds gauge',
                     '# TYPE frontend_telemetry_reported_delivery gauge',
                     '# TYPE frontend_telemetry_reported_delivery_max gauge',
                     '# TYPE frontend_telemetry_reports_with_delivery_issue_total counter',
                     '# TYPE frontend_telemetry_result_dimension_overflow_total counter']
            lines += ['frontend_telemetry_receiver_up 1',
                      f'frontend_telemetry_last_received_timestamp_seconds {self.last_received}',
                      f'frontend_telemetry_receiver_start_timestamp_seconds {self.created}']
            for (name, labels), value in sorted(self.metrics.items()):
                suffix = '{' + ','.join(f'{key}={json.dumps(val)}' for key, val in labels) + '}' if labels else ''
                lines.append(f'{name}{suffix} {value}')
            return ('\n'.join(lines) + '\n').encode('utf-8')


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, *_args):
        pass  # Never log client addresses, URLs, bodies or headers.

    def reply(self, status, body=b'', content_type='text/plain; charset=utf-8'):
        self.close_connection = True
        self.send_response(status)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Content-Type', content_type)
        self.send_header('Connection', 'close')
        self.send_header('Cache-Control', 'no-store')
        origin = self.headers.get('Origin')
        if origin in ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        if self.path == '/metrics':
            self.reply(200, self.server.state.render(), 'text/plain; version=0.0.4; charset=utf-8')
        elif self.path == '/health':
            self.reply(200, b'ok\n')
        else:
            self.reply(404)

    def do_OPTIONS(self):
        if self.path != PATH or self.headers.get('Origin') not in ORIGINS:
            self.reply(403)
        else:
            self.close_connection = True
            self.send_response(204)
            self.send_header('Access-Control-Allow-Origin', self.headers['Origin'])
            self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.send_header('Content-Length', '0')
            self.end_headers()

    def do_POST(self):
        if self.path != PATH:
            self.reply(404)
            return
        if self.headers.get('Origin') not in ORIGINS:
            self.server.state.reject()
            self.reply(403)
            return
        if not self.server.state.allow():
            self.reply(429)
            return
        try:
            if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length', [])) != 1:
                raise ValueError('framing')
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 60_000:
                self.server.state.reject()
                self.reply(413)
                return
            if self.headers.get_content_type() != 'text/plain':
                self.reply(415)
                return
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError('truncated')
            batch = json.loads(raw.decode('utf-8'))
            self.server.state.ingest(batch)
        except OSError:
            self.reply(503)
            return
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
            self.server.state.reject()
            self.reply(400)
            return
        self.reply(204)


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, journal=None):
        self.state = State(journal=journal)
        self.slots = threading.BoundedSemaphore(16)
        super().__init__(address, Handler)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()

    def handle_error(self, request, client_address):
        # Suppress BaseServer's traceback, which includes the client address.
        pass


if __name__ == '__main__':
    journal = RequestJournal(os.environ.get('FRONTEND_REQUEST_LOG',
                                           '/var/lib/matchwise-frontend-traffic/requests.jsonl'))
    Server(('127.0.0.1', 9121), journal=journal).serve_forever()
