import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlparse, parse_qs

spec = importlib.util.spec_from_file_location("checks", Path(__file__).with_name("check-service-comparison-queries.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Checks(unittest.TestCase):
    def run_main(self, values, dashboard=False):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            rules = Path(folder) / "rules.json"
            rules.write_text(json.dumps({"groups":[{"rules":[{"uid":"test", "data":[
                {"refId":"A","datasourceUid":"loki","model":{"expr":"vector(0)"}}]}]}]}))
            argv = ["check",str(rules)]
            if dashboard:
                dash=Path(folder)/"dashboard.json"
                dash.write_text(json.dumps({"panels":[{"title":"Logs","type":"logs",
                    "datasource":{"type":"loki"},"targets":[{"refId":"A","expr":"{}"}]}]}))
                argv += ["--dashboard", str(dash)]
            output=io.StringIO()
            with patch("sys.argv",argv), patch.object(m,"execute",side_effect=values), contextlib.redirect_stdout(output):
                code=m.main()
            return code,output.getvalue()

    def test_empty_alert_telemetry_is_failure(self):
        code,_=self.run_main([{"result":[]}])
        self.assertEqual(code,1)

    def test_empty_dashboard_logs_allowed_without_dumping_raw_logs(self):
        code,text=self.run_main([{"result":[{"value":[1,"0"]}]},{"result":[]}],True)
        self.assertEqual(code,0)
        self.assertIn("series=0",text)
        code,text=self.run_main([{"result":[{"value":[1,"0"]}]},
                                {"result":[{"values":[["1","PRIVATE LOG TEXT"]]}]}],True)
        self.assertEqual(code,0)
        self.assertNotIn("PRIVATE LOG TEXT",text)

    def test_http_diagnostics_do_not_expose_url_or_body(self):
        code,text=self.run_main([HTTPError("secret-url",400,"secret-body",{},None)])
        self.assertEqual(code,1)
        self.assertIn("HTTP 400",text)
        self.assertNotIn("secret",text)

    def test_log_queries_use_bounded_range_endpoint(self):
        class Response:
            def __enter__(self): return io.BytesIO(b'{"status":"success","data":{"result":[]}}')
            def __exit__(self,*args): pass
        with patch.object(m,"urlopen",return_value=Response()) as call:
            m.execute("loki","test expression",True)
        url=call.call_args.args[0]
        self.assertTrue(urlparse(url).path.endswith("/query_range"))
        params=parse_qs(urlparse(url).query)
        self.assertEqual(params["limit"],["5"])
        self.assertEqual(int(params["end"][0])-int(params["start"][0]),300_000_000_000)

if __name__=="__main__": unittest.main()
