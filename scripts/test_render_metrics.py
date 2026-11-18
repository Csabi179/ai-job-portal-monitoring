import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from urllib.error import HTTPError
from datetime import datetime, timezone

spec = importlib.util.spec_from_file_location('collector', Path(__file__).with_name('render-metrics-poll.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
NOW = 1795014900

def fixture():
    payloads = {}
    for key, unit in m.ENDPOINTS.items():
        payloads[key] = [{'unit': unit, 'labels': [{'field':'resource','value':'srv-test'}, {'field':'instance','value':'instance-1'}],
                         'values':[{'timestamp':datetime.fromtimestamp(NOW-60, timezone.utc).isoformat(),
                                    'value': {'cpu':0.0002448,'cpu-limit':0.15,'memory':95039490,'memory-limit':536870900}[key]}]}]
    return payloads

class Tests(unittest.TestCase):
    def test_http_error_diagnostics_hide_sensitive_details(self):
        for status in (400, 401, 403, 429, 500):
            with self.subTest(status=status):
                opener = Mock()
                opener.open.side_effect = HTTPError('https://example.test/secret', status, 'secret response', {}, None)
                with patch.object(m, 'build_opener', return_value=opener):
                    with self.assertRaises(m.MetricsHTTPError) as caught:
                        m.collect('secret-key', 'srv-test')
                self.assertEqual(m.failure_message(caught.exception), f'cpu: HTTP {status} (response body hidden)')
        self.assertEqual(m.failure_message(ValueError('secret')), 'ValueError')

    def test_ratios(self):
        out = m.calculate(fixture(), 'srv-test', NOW)
        self.assertAlmostEqual(out['matchwise_render_cpu_utilization_percent'], .1632)
        self.assertAlmostEqual(out['matchwise_render_memory_utilization_percent'], 17.7024843, places=5)

    def test_invalid_sources(self):
        for case in ('empty','multi','unit','resource','instance','zero','stale','nan','time'):
            with self.subTest(case=case):
                p=fixture()
                if case=='empty': p['cpu']=[]
                if case=='multi': p['cpu']*=2
                if case=='unit': p['cpu'][0]['unit']='bytes'
                if case=='resource': p['cpu'][0]['labels'][0]['value']='srv-other'
                if case=='instance': p['cpu'][0]['labels'][1]['value']='instance-2'
                if case=='zero': p['cpu-limit'][0]['values'][0]['value']=0
                if case=='nan': p['cpu'][0]['values'][0]['value']=float('nan')
                if case=='time': p['cpu'][0]['values'][0]['timestamp']='2020-01-01T00:00:00Z'
                with self.assertRaises(ValueError): m.calculate(p,'srv-test',NOW+600 if case=='stale' else NOW)

    def test_atomic_replacement(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            path=Path(directory)/'test.prom'
            m.publish(path,'old\n')
            m.publish(path,'new\n')
            self.assertEqual(path.read_text(),'new\n')
            self.assertEqual(list(Path(directory).iterdir()),[path])

if __name__=='__main__': unittest.main()

