"""New browser v2 contract, journal, HTTP acknowledgement and Grafana integration."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen, build_opener, ProxyHandler

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('receiver', HERE / 'frontend-traffic-receiver.py')
receiver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(receiver)
RID = '14738520-0087-492b-a4a8-adfc50d1471a'


def fixture():
    batch = json.loads((HERE / 'frontend-traffic-v1.json').read_text(encoding='utf-8'))
    batch.update(schema_version=2, dropped_requests=0, requests=[{
        'request_id': RID, 'started_at_ms': 1795000000000,
        'finished_at_ms': 1795000001250, 'duration_ms': 1250,
        'route': '/cv/:id/profile', 'method': 'POST', 'status': 200, 'outcome': 'http',
    }])
    return batch


class RequestTests(unittest.TestCase):
    def test_v1_v2_coexist_without_double_counting(self):
        journal = Mock()
        state = receiver.State(journal)
        batch = fixture()
        state.ingest(batch)
        state.ingest(batch)
        journal.write.assert_called_once()
        self.assertEqual(journal.write.call_args.args[0][0]['request_id'], RID)
        metrics = state.render().decode()
        self.assertIn('frontend_api_outcomes_total{mode="real",outcome="http",route="jobs"} 1.0', metrics)
        self.assertIn('frontend_telemetry_request_records_total{mode="real"} 1.0', metrics)
        self.assertNotIn(RID, metrics)
        self.assertNotIn('/cv/:id/profile', metrics)
        old = json.loads((HERE / 'frontend-traffic-v1.json').read_text())
        old['batch_id'] = '22345678-1234-1234-1234-123456789abc'
        state.ingest(old)
        journal.write.assert_called_once()

    def test_null_ids_errors_abort_mock_and_health(self):
        journal = Mock()
        batch = fixture()
        good = batch['requests'][0]
        batch['requests'] = [dict(good, request_id=None, status=0, outcome=outcome)
                             for outcome in ('network_error', 'aborted')]
        batch['requests'] += [dict(good, request_id=None), dict(good, route='/api/health')]
        batch.update(mock_jobs=True, dropped_requests=4)
        state = receiver.State(journal)
        state.ingest(batch)
        rows = journal.write.call_args.args[0]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row['request_id'] is None for row in rows))
        self.assertTrue(all(row['mode'] == 'partial_mock' for row in rows))
        self.assertEqual(len({row['event_id'] for row in rows}), 3)
        metrics = state.render().decode()
        self.assertIn('frontend_telemetry_reported_dropped_requests_total{mode="partial_mock"} 4.0', metrics)
        self.assertIn('frontend_telemetry_excluded_health_records_total{mode="partial_mock"} 1.0', metrics)

    def test_invalid_record_cannot_partially_update_aggregates_or_journal(self):
        mutations = [
            lambda b: b.update(requests=b['requests'] * 65),
            lambda b: b.update(dropped_requests=-1),
            lambda b: b.pop('dropped_requests'),
            lambda b: b['requests'][0].update(request_id='backend-request-id'),
            lambda b: b['requests'][0].update(route='/cv/private-user/profile'),
            lambda b: b['requests'][0].update(route='/jobs?token=secret'),
            lambda b: b['requests'][0].update(duration_ms=float('nan')),
            lambda b: b['requests'][0].update(duration_ms=-1),
            lambda b: b['requests'][0].update(finished_at_ms=0),
            lambda b: b['requests'][0].update(status=True),
            lambda b: b['requests'][0].update(outcome='network_error', status=0),
            lambda b: b['requests'][0].update(extra='secret'),
            lambda b: b['requests'].append(dict(b['requests'][0], duration_ms=-1)),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                journal = Mock()
                state = receiver.State(journal)
                before = state.render()
                batch = fixture()
                mutate(batch)
                with self.assertRaises((ValueError, TypeError, KeyError)):
                    state.ingest(batch)
                self.assertEqual(state.render(), before)
                journal.write.assert_not_called()

    def test_disk_failure_is_retryable_without_counting_batch(self):
        journal = Mock()
        journal.write.side_effect = OSError('disk full')
        state = receiver.State(journal)
        before = state.render()
        with self.assertRaises(OSError):
            state.ingest(fixture())
        self.assertEqual(state.render(), before)
        self.assertFalse(state.seen)
        journal.write.side_effect = None
        state.ingest(fixture())
        self.assertEqual(len(state.seen), 1)

    def test_rounding_uppercase_ids_and_strict_schema(self):
        batch = fixture()
        batch['requests'][0].update(duration_ms=1249.65, request_id=RID.upper())
        journal = Mock()
        receiver.State(journal).ingest(batch)
        self.assertEqual(journal.write.call_args.args[0][0]['request_id'], RID)
        batch['requests'][0]['duration_ms'] = 1248
        with self.assertRaises(ValueError):
            receiver.validate(batch)

    def test_journal_rotation_and_safe_jsonl(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'requests.jsonl'
            journal = receiver.RequestJournal(path, max_bytes=1, backups=2)
            for index in range(4):
                journal.write([{'event_id': str(index)}])
            self.assertEqual(json.loads(path.read_text())['event_id'], '3')
            self.assertEqual(json.loads(Path(str(path) + '.2').read_text())['event_id'], '1')
            self.assertEqual(len(list(Path(folder).iterdir())), 3)

    def test_http_v2_and_disk_failure_status(self):
        journal = Mock()
        server = receiver.Server(('127.0.0.1', 0), journal)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        opener = build_opener(ProxyHandler({}))
        def post(batch):
            req = Request(f'http://127.0.0.1:{server.server_port}' + receiver.PATH,
                          json.dumps(batch).encode(),
                          {'Origin': 'https://www.matchwise.tech', 'Content-Type': 'text/plain'})
            try:
                return opener.open(req, timeout=5)
            except HTTPError as error:
                return error
        try:
            batch = fixture()
            journal.write.side_effect = OSError('disk full')
            with post(batch) as response:
                self.assertEqual(response.status, 503)
            journal.write.side_effect = None
            with post(batch) as response:
                self.assertEqual(response.status, 204)
            with post(batch) as response:
                self.assertEqual(response.status, 204)
            self.assertEqual(journal.write.call_count, 2)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
