import copy
import importlib.util
import json
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('receiver', HERE / 'frontend-traffic-receiver.py')
receiver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(receiver)


def fixture():
    return json.loads((HERE / 'frontend-traffic-v1.json').read_text(encoding='utf-8'))


class ReceiverTests(unittest.TestCase):
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
