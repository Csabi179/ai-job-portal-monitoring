import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
OUT=HERE/'output'
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
builder=module('builder','build-bilingual-dashboards.py')
checker=module('checker','check-bilingual-dashboards.py')
provision=module('provision','verify-provisioned-dashboards.py')
def read(root,file): return json.loads((root/file).read_text(encoding='utf-8'))
def source(kind):
    for file in ('source-'+kind+'.json','preparation-'+kind+'.json'):
        if (HERE/file).exists(): return read(HERE,file)
    filename='matchwise-unified-monitoring.json' if kind=='unified' else 'matchwise-service-comparison.json'
    return read(OUT,filename)

class BilingualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global OUT
        cls.temp=None
        if (HERE/'dashboard-language-manifest.json').exists(): OUT=HERE
        elif not OUT.exists():
            cls.temp=tempfile.TemporaryDirectory();OUT=Path(cls.temp.name)
            repo=HERE.parent
            manifest=read(repo/'docs','dashboard-language-manifest.json')
            (OUT/'dashboard-language-manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
            for item in manifest['dashboards']:
                (OUT/item['file']).write_bytes((repo/'grafana/provisioning/dashboards/json'/item['file']).read_bytes())
            (OUT/'check-dashboard-final-audit.py').write_bytes((HERE/'check-dashboard-final-audit.py').read_bytes())

    @classmethod
    def tearDownClass(cls):
        if cls.temp is not None: cls.temp.cleanup()

    def test_hu_panels_preserved_and_names_do_not_accumulate_suffixes(self):
        for kind in ('unified','comparison'):
            original=source(kind)
            hu,en=builder.build(original,kind)
            self.assertEqual(hu['panels'],original['panels'])
            again,english=builder.build(hu,kind)
            self.assertEqual(again,hu)
            self.assertEqual(english,en)
            self.assertEqual(en['uid'],original['uid']+'-en')
            self.assertFalse(en['title'].endswith(' EN'))

    def test_filter_values_that_match_translated_words_remain_literal(self):
        original=source('unified')
        variable=next(v for v in original['templating']['list'] if v['name']=='route_filter')
        variable['current']={'value':'Mind','text':'Mind'};variable['query']='Mind'
        hu,en=builder.build(original,'unified')
        other=next(v for v in en['templating']['list'] if v['name']=='route_filter')
        self.assertEqual(variable['current'],other['current'])
        self.assertEqual(other['query'],'Mind')
        self.assertEqual(other['label'],'Route contains')

    def test_parity_validator_rejects_changed_english_measurement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for file in OUT.glob('*.json'):
                (root/file.name).write_bytes(file.read_bytes())
            (root/'check-dashboard-final-audit.py').write_bytes((OUT/'check-dashboard-final-audit.py').read_bytes())
            with contextlib.redirect_stdout(io.StringIO()): checker.validate(root)
            d=read(root,'matchwise-service-comparison-en.json')
            d['panels'][1]['targets'][0]['expr']='vector(1)'
            (root/'matchwise-service-comparison-en.json').write_text(json.dumps(d),encoding='utf-8')
            with self.assertRaises(AssertionError),contextlib.redirect_stdout(io.StringIO()): checker.validate(root)

    def test_all_four_models_are_verified_from_sqlite_without_changing_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'grafana.db'
            files=[x['file'] for x in read(OUT,'dashboard-language-manifest.json')['dashboards']]
            with contextlib.closing(sqlite3.connect(db)) as c, c:
                c.execute('CREATE TABLE dashboard (uid TEXT PRIMARY KEY, data TEXT)')
                for file in files:
                    d=read(OUT,file);c.execute('INSERT INTO dashboard VALUES (?,?)',(d['uid'],json.dumps(d)))
            args=['verify',str(OUT),'--wait','0','--files',*files]
            with patch.object(provision,'locate_database',return_value=db),patch.object(sys,'argv',args),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(provision.main(),0)
            with contextlib.closing(sqlite3.connect(db)) as c, c:
                self.assertEqual(c.execute('SELECT count(*) FROM dashboard').fetchone()[0],4)
                c.execute('DELETE FROM dashboard WHERE uid=?',('matchwise-service-comparison-en',))
            with patch.object(provision,'locate_database',return_value=db),patch.object(sys,'argv',args),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(provision.main(),1)

if __name__=='__main__': unittest.main()
