import copy
import importlib.util
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('receiver', HERE / 'frontend-traffic-receiver.py')
receiver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(receiver)


def fixture():
    return json.loads((HERE / 'frontend-traffic-v1.json').read_text(encoding='utf-8'))


class ReceiverTests(unittest.TestCase):
    def test_diagnostic_snapshots_are_not_added_and_duplicates_do_not_replace_them(self):
        state = receiver.State()
        first = fixture()
        first['inflight'] = 3
        first['delivery'].update(sent_batches=10, failed_attempts=4, dropped_batches=2, dropped_observations=5)
        state.ingest(first)
        second = copy.deepcopy(first)
        second['batch_id'] = '22345678-1234-1234-1234-123456789abc'
        second['inflight'] = 1
        second['delivery'].update(sent_batches=2, failed_attempts=1, dropped_batches=0, dropped_observations=0)
        state.ingest(second)
        state.ingest(first)  # Retry of older packet cannot overwrite the newer snapshot.
        metrics = state.render().decode()
        self.assertIn('frontend_telemetry_reported_inflight{mode="real"} 1', metrics)
        self.assertIn('frontend_telemetry_reported_delivery{kind="failed_attempts",mode="real"} 1', metrics)
        self.assertIn('frontend_telemetry_reported_delivery_max{kind="failed_attempts",mode="real"} 4', metrics)
        self.assertIn('frontend_telemetry_reports_with_delivery_issue_total{kind="failed_attempts",mode="real"} 2.0', metrics)
        self.assertIn('frontend_telemetry_reports_with_delivery_issue_total{kind="dropped_batches",mode="real"} 1.0', metrics)
        self.assertIn('frontend_telemetry_batches_total 2.0', metrics)

    def test_windows_preserve_signed_clock_skew_and_mode_isolation(self):
        state = receiver.State()
        batch = fixture()
        batch.update(window_start_ms=1_000_000, window_end_ms=1_060_000)
        with patch.object(receiver.time, 'time', return_value=1058):
            state.ingest(batch)
        mock = copy.deepcopy(batch)
        mock.update(batch_id='22345678-1234-1234-1234-123456789abc', mock_jobs=True, inflight=7)
        state.ingest(mock)
        metrics = state.render().decode()
        self.assertIn('frontend_telemetry_reported_window_seconds{mode="real"} 60.0', metrics)
        self.assertIn('frontend_telemetry_reported_window_end_age_seconds{mode="real"} -2.0', metrics)
        self.assertIn('frontend_telemetry_mode_last_received_timestamp_seconds{mode="real"} 1058', metrics)
        self.assertIn('frontend_telemetry_reported_inflight{mode="partial_mock"} 7', metrics)
        self.assertIn('frontend_telemetry_reported_inflight{mode="real"} 0', metrics)

    def test_detailed_results_and_peaks_preserve_failures_and_no_double_count(self):
        state = receiver.State()
        batch = fixture()
        state.ingest(batch)
        second = copy.deepcopy(batch)
        second['batch_id'] = '22345678-1234-1234-1234-123456789abc'
        second['results'][0].update(method='POST', status=503)
        state.ingest(second)
        state.ingest(second)
        metrics = state.render().decode()
        self.assertIn('frontend_api_results_total{method="POST",mode="real",outcome="http",route="jobs",status="503"} 1.0', metrics)
        self.assertIn('frontend_api_fetch_headers_max_seconds{mode="real",outcome="http",route="jobs"} 0.35', metrics)
        self.assertIn('frontend_api_outcomes_total{mode="real",outcome="http",route="jobs"} 2.0', metrics)

    def test_detail_cardinality_overflow_folds_counts_without_losing_legacy_totals(self):
        state = receiver.State()
        with patch.object(receiver, 'MAX_RESULT_SERIES', 1):
            for i in range(4):
                batch = fixture()
                batch['batch_id'] = f'{i:08d}-1234-1234-1234-123456789abc'
                batch['results'][0]['status'] = 200 + i
                state.ingest(batch)
        self.assertEqual(len(state.result_series), 1)
        metrics = state.render().decode()
        self.assertIn('frontend_telemetry_result_dimension_overflow_total{mode="real"} 3.0', metrics)
        self.assertIn('frontend_api_results_total{method="OTHER",mode="real",outcome="http",route="other",status="other"} 3.0', metrics)
        self.assertIn('frontend_api_outcomes_total{mode="real",outcome="http",route="jobs"} 4.0', metrics)

    def test_browser_contract_and_histogram_conversion(self):
        state = receiver.State()
        state.ingest(fixture())
        metrics = state.render().decode()
        self.assertIn('frontend_api_requests_started_total{method="GET",mode="real",route="jobs"} 1.0', metrics)
        self.assertIn('frontend_api_http_responses_total{mode="real",status="200"} 1.0', metrics)
        self.assertIn('le="0.25",mode="real",outcome="http",route="jobs"} 0.0', metrics)
        self.assertIn('le="0.5",mode="real",outcome="http",route="jobs"} 1.0', metrics)
        self.assertIn('le="+Inf",mode="real",outcome="http",route="jobs"} 1.0', metrics)
        self.assertIn('_sum{mode="real",outcome="http",route="jobs"} 0.35', metrics)
        self.assertNotIn('private-id', metrics)
        self.assertNotIn(fixture()['batch_id'], metrics)

    def test_duplicates_do_not_double_count(self):
        state = receiver.State()
        state.ingest(fixture()); state.ingest(fixture())
        metrics = state.render().decode()
        self.assertIn('frontend_telemetry_batches_total 1.0', metrics)
        self.assertIn('frontend_telemetry_duplicate_batches_total 1.0', metrics)

    def test_invalid_data_is_atomic(self):
        mutations = [
            lambda x: x.update(schema_version=2),
            lambda x: x.update(extra='forbidden'),
            lambda x: x.update(interval_ms=30_000),
            lambda x: x.update(mock_api='false'),
            lambda x: x.update(starts=x['starts'] * 57),
            lambda x: x['results'][0].update(count=-1),
            lambda x: x['results'][0].update(status=True),
            lambda x: x['results'][0].update(route='arbitrary-client-path'),
            lambda x: x['results'][0].update(duration_sum_ms=float('nan')),
            lambda x: x['results'][0].update(duration_bins=[0] * 10),
            lambda x: x['results'].append(copy.deepcopy(x['results'][0])),
            lambda x: x['results'][0].update(duration_max_ms=500),
        ]
        for mutate in mutations:
            state = receiver.State(); before = state.render()
            batch = fixture(); mutate(batch)
            with self.assertRaises((ValueError, TypeError)):
                state.ingest(batch)
            self.assertEqual(state.render(), before)

    def test_mock_mode_and_network_errors(self):
        batch = fixture(); batch['mock_api'] = True
        batch['results'][0].update(status=0, outcome='network_error')
        state = receiver.State(); state.ingest(batch)
        metrics = state.render().decode()
        self.assertIn('mode="partial_mock"', metrics)
        self.assertIn('outcome="network_error"', metrics)
        self.assertNotIn('frontend_api_http_responses_total', metrics)

    def test_global_rate_limit(self):
        state = receiver.State()
        for _ in range(600): self.assertTrue(state.allow())
        self.assertFalse(state.allow())

    def test_http_ingest_cors_and_metrics(self):
        server = receiver.Server(('127.0.0.1', 0))
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        def post(body, origin='https://www.matchwise.tech', content_type='text/plain'):
            req = Request(base + receiver.PATH, data=body, headers={'Origin': origin, 'Content-Type': content_type})
            try:
                return urlopen(req, timeout=5)
            except HTTPError as error:
                return error
        try:
            raw = json.dumps(fixture()).encode()
            with post(raw) as response:
                self.assertEqual(response.status, 204)
                self.assertEqual(response.headers['Access-Control-Allow-Origin'], 'https://www.matchwise.tech')
            with post(raw) as response: self.assertEqual(response.status, 204)
            with post(raw, origin='https://evil.example') as response: self.assertEqual(response.status, 403)
            with post(b'invalid json') as response: self.assertEqual(response.status, 400)
            with post(b'x' * 60_001) as response: self.assertEqual(response.status, 413)
            with post(raw, content_type='application/json') as response: self.assertEqual(response.status, 415)
            with urlopen(base + '/metrics') as response:
                self.assertIn('frontend_telemetry_duplicate_batches_total 1.0', response.read().decode())
            with urlopen(base + '/health') as response: self.assertEqual(response.status, 200)
        finally:
            server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__':
    unittest.main()
