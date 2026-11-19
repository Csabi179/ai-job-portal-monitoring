import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
def module(name,filename):
    spec=importlib.util.spec_from_file_location(name,HERE/filename)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result
audit=module('audit','check-dashboard-final-audit.py')
provision=module('provision','verify-provisioned-dashboards.py')
def read(filename): return json.loads((HERE/filename).read_text(encoding='utf-8'))

class AuditTests(unittest.TestCase):
    def test_reviewed_models_pass_and_unreviewed_query_change_stops(self):
        manifest=read('dashboard-query-audit.json')
        d=read('matchwise-service-comparison.json');old=read('baseline-comparison.json')
        with contextlib.redirect_stdout(io.StringIO()): audit.validate('comparison',d,old,manifest)
        d['panels'][1]['targets'][0]['expr']='vector(1)'
        with self.assertRaises(AssertionError): audit.validate('comparison',d,old,manifest)

    def test_requested_removal_is_limited_to_the_named_sections(self):
        d=read('matchwise-service-comparison.json');old=read('baseline-comparison.json')
        d['panels']=[p for p in d['panels'] if p['id']!=59]
        with self.assertRaises(AssertionError): audit.validate('comparison',d,old,read('dashboard-query-audit.json'))

    def test_real_variable_interpolation_preserves_regex_and_json_escaping(self):
        d=read('matchwise-unified-monitoring.json')
        expr='route!~"${excluded_route:raw}" | route=~".*${route_filter:regex}.*" [$__range]'
        expanded=audit.expand(expr,d)
        self.assertIn('route!~"(/api/health|/health)"',expanded)
        self.assertIn('[3600s]',expanded)
        for v in d['templating']['list']:
            if v['name']=='route_filter': v['current']['value']='a.b"c'
        self.assertIn('a\\\\.b\\"c',audit.expand(expr,d))
        with self.assertRaises(ValueError): audit.expand('${unknown}',d)

    def test_live_check_uses_range_endpoints_and_never_prints_raw_logs(self):
        dashboards={'unified':read('matchwise-unified-monitoring.json'),'comparison':read('matchwise-service-comparison.json')}
        urls=[]
        class Response:
            def __init__(self,url): self.url=url
            def __enter__(self):
                is_log='limit=5' in self.url
                return io.StringIO(json.dumps({'status':'success','data':{'result':[{'stream':{},'values':[['123','PRIVATE-LOG-BODY']]}] if is_log else []}}))
            def __exit__(self,*args): pass
        class Opener:
            def open(self,url,timeout):
                urls.append(url);return Response(url)
        output=io.StringIO()
        with patch.object(audit,'build_opener',return_value=Opener()),contextlib.redirect_stdout(output):
            self.assertFalse(audit.query_all(dashboards,True))
        self.assertNotIn('PRIVATE-LOG-BODY',output.getvalue())
        self.assertTrue(any('/query_range?' in url and 'step=60' in url for url in urls))
        self.assertTrue(any('limit=5' in url for url in urls))
        self.assertTrue(all('%24%7B' not in url and '%24__' not in url for url in urls))

    def test_nonfinite_metric_is_reported_as_a_failure(self):
        d={'panels':[{'id':1,'type':'stat','datasource':{'uid':'prometheus'},'targets':[{'refId':'A','expr':'vector(0)'}]}]}
        class Response:
            def __enter__(self): return io.StringIO('{"status":"success","data":{"result":[{"value":[1,"NaN"]}]}}')
            def __exit__(self,*args): pass
        class Opener:
            def open(self,*args,**kwargs): return Response()
        with patch.object(audit,'build_opener',return_value=Opener()),contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(audit.query_all({'test':d},False))

    def test_provisioned_match_requires_expected_queries_layout_and_rows(self):
        d=read('matchwise-service-comparison.json')
        actual=copy.deepcopy(d);actual['id']=99;actual['version']=999
        self.assertTrue(provision.matches(actual,d))
        actual['panels'][1]['targets'][0]['expr']='vector(1)'
        self.assertFalse(provision.matches(actual,d))
        actual=copy.deepcopy(d);actual['panels'][-1]['collapsed']=False
        self.assertFalse(provision.matches(actual,d))
        actual=copy.deepcopy(d);actual['panels'][1]['gridPos']['x']=1
        self.assertFalse(provision.matches(actual,d))

if __name__=='__main__': unittest.main()
