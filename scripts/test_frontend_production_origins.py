"""Production redirect/origin regression checks; no live writes or service changes."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('origin_fix', HERE / 'enable-frontend-production-origins.py')
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


class ProductionOriginTests(unittest.TestCase):
    def test_preserves_explicit_origins_without_reading_other_environment_values(self):
        env = (b'OTHER_VARIABLE=not-an-origin\0FRONTEND_TRAFFIC_ORIGINS='
               b'https://www.matchwise.tech,http://localhost:5173,https://preview.example\0')
        self.assertEqual(helper.allowed_origins(env), [
            'https://www.matchwise.tech', 'http://localhost:5173', 'https://preview.example', 'https://matchwise.tech'])
        repeated = b'FRONTEND_TRAFFIC_ORIGINS=https://matchwise.tech,https://www.matchwise.tech\0'
        self.assertEqual(helper.allowed_origins(repeated), list(reversed(helper.PRODUCTION)))

    def test_rejects_missing_or_unsafe_settings(self):
        for value in (b'OTHER=example\0', b'FRONTEND_TRAFFIC_ORIGINS=*\0',
                      b'FRONTEND_TRAFFIC_ORIGINS=https://example%host\0',
                      b'FRONTEND_TRAFFIC_ORIGINS=https://example\nRestart=no\0'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                helper.allowed_origins(value)

    def test_cors_checks_both_production_origins_and_refuses_wildcard(self):
        for wrong in (False, True):
            opener = MagicMock()
            seen = []
            def open_request(request, timeout):
                seen.append((request.method, request.headers['Origin']))
                allowed = request.headers['Origin'] in helper.PRODUCTION
                response = MagicMock()
                response.status = 204 if allowed else 403
                response.headers = {'Access-Control-Allow-Origin': '*' if wrong else request.headers['Origin']} if allowed else {}
                response.__enter__.return_value = response
                return response
            opener.open.side_effect = open_request
            with patch.object(helper, 'build_opener', return_value=opener):
                if wrong:
                    with self.assertRaises(RuntimeError):
                        helper.check_cors('http://127.0.0.1:9121')
                else:
                    helper.check_cors('http://127.0.0.1:9121')
                    self.assertEqual(seen, [('OPTIONS', origin) for origin in helper.PRODUCTION] +
                                     [('OPTIONS', 'https://unrelated.invalid')])

    def test_service_and_receiver_defaults_allow_both_production_hosts(self):
        root = HERE.parent
        service = (root / 'systemd/matchwise-frontend-traffic.service').read_text(encoding='utf-8')
        self.assertIn('Environment=FRONTEND_TRAFFIC_ORIGINS=' + ','.join(helper.PRODUCTION), service)
        source = (HERE / 'frontend-traffic-receiver.py').read_text(encoding='utf-8')
        self.assertIn("'" + ','.join(helper.PRODUCTION) + "'", source)


if __name__ == '__main__':
    unittest.main()
