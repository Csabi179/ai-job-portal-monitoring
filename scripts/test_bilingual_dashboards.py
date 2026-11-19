"""Tests for the service-grouped dashboards (generator, validator, provisioning verifier).

The previous HU->EN translation pipeline (build-bilingual-dashboards.py) is superseded for the
Unified and Comparison dashboards by build-service-dashboards.py, which emits both languages.
"""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
JSON_DIR = REPO / 'grafana/provisioning/dashboards/json'


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


checker = module('checker', 'check-service-dashboards.py')
provision = module('provision', 'verify-provisioned-dashboards.py')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def run_checker(directory):
    with contextlib.redirect_stdout(io.StringIO()):
        sys_argv = ['check-service-dashboards.py', str(directory)]
        with patch.object(sys, 'argv', sys_argv):
            try:
                checker.main()
            except SystemExit as exc:
                return exc.code or 0
    return 0


class ServiceDashboardTests(unittest.TestCase):
    def copy_models(self, tmp):
        for name in checker.FILES:
            (Path(tmp) / name).write_bytes((JSON_DIR / name).read_bytes())
        return Path(tmp)

    def test_committed_dashboards_pass_structure_parity_and_consistency(self):
        self.assertEqual(run_checker(JSON_DIR), 0)

    def test_validator_rejects_changed_english_measurement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.copy_models(tmp)
            path = root / 'matchwise-service-comparison-en.json'
            d = read(path)
            target = next(t for p in d['panels'] for t in p.get('targets', []))
            target['expr'] = 'vector(1)'
            path.write_text(json.dumps(d), encoding='utf-8')
            self.assertEqual(run_checker(root), 1)

    def test_validator_rejects_service_strip_that_differs_from_the_others(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.copy_models(tmp)
            for name in ('matchwise-unified-monitoring.json', 'matchwise-unified-monitoring-en.json'):
                d = read(root / name)
                oracle=False
                for p in d['panels']:
                    if p['type']=='row': oracle=p['title'].startswith('04 · Oracle')
                    if oracle and p['type']=='stat' and p['title']=='CPU (%)':
                        p['title']='Different CPU load'
                (root / name).write_text(json.dumps(d), encoding='utf-8')
            self.assertEqual(run_checker(root), 1)

    def test_validator_rejects_different_english_filter_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.copy_models(tmp)
            path=root/'matchwise-unified-monitoring-en.json';d=read(path)
            d['templating']['list'][0]['current']['value']='different.example:443'
            path.write_text(json.dumps(d),encoding='utf-8')
            self.assertEqual(run_checker(root),1)

    def test_validator_rejects_missing_service_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.copy_models(tmp)
            for name in ('matchwise-unified-monitoring.json','matchwise-unified-monitoring-en.json'):
                d=read(root/name)
                for p in d['panels']:
                    if p['type']=='row' and p['title'].startswith('01 · Frontend'):
                        p['title']='01 · Missing service'
                (root/name).write_text(json.dumps(d),encoding='utf-8')
            self.assertEqual(run_checker(root),1)

    def test_generator_is_deterministic_from_the_baseline_revision(self):
        baseline_dir=os.environ.get('MATCHWISE_DASHBOARD_BASELINE_DIR')
        if not baseline_dir:
            probe = subprocess.run(['git', 'cat-file', '-e', '900002e74e6889515b44bf4ac2d4a6ecd110e0b4'], cwd=REPO, capture_output=True)
            if probe.returncode:
                self.skipTest('provide MATCHWISE_DASHBOARD_BASELINE_DIR or fetch the pinned baseline commit')
        with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
            for out in (one, two):
                extra=['--baseline-dir',str(Path(baseline_dir).resolve())] if baseline_dir else []
                subprocess.run([sys.executable, str(HERE / 'build-service-dashboards.py'), out,*extra],
                               check=True, capture_output=True)
            for name in checker.FILES:
                self.assertEqual((Path(one) / name).read_bytes(), (Path(two) / name).read_bytes())
                self.assertEqual((Path(one) / name).read_bytes(), (JSON_DIR / name).read_bytes())

    def test_all_four_models_are_verified_from_sqlite_without_changing_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / 'grafana.db'
            files = [x['file'] for x in read(REPO / 'docs/dashboard-language-manifest.json')['dashboards']]
            with contextlib.closing(sqlite3.connect(db)) as c, c:
                c.execute('CREATE TABLE dashboard (uid TEXT PRIMARY KEY, data TEXT)')
                for file in files:
                    d = read(JSON_DIR / file)
                    c.execute('INSERT INTO dashboard VALUES (?,?)', (d['uid'], json.dumps(d)))
            args = ['verify', str(JSON_DIR), '--wait', '0', '--files', *files]
            with patch.object(provision, 'locate_database', return_value=db), patch.object(sys, 'argv', args), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(provision.main(), 0)
            with contextlib.closing(sqlite3.connect(db)) as c, c:
                self.assertEqual(c.execute('SELECT count(*) FROM dashboard').fetchone()[0], 4)
                c.execute('DELETE FROM dashboard WHERE uid=?', ('matchwise-service-comparison-en',))
            with patch.object(provision, 'locate_database', return_value=db), patch.object(sys, 'argv', args), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(provision.main(), 1)

    def test_all_four_candidate_models_use_current_grafana13_resource_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'grafana.db'
            files=checker.FILES
            with contextlib.closing(sqlite3.connect(db)) as c,c:
                c.execute('CREATE TABLE dashboard (uid TEXT PRIMARY KEY,data TEXT)')
                c.execute('CREATE TABLE resource ("group" TEXT,resource TEXT,namespace TEXT,name TEXT,value TEXT,action INTEGER)')
                for file in files:
                    d=read(JSON_DIR/file)
                    c.execute('INSERT INTO dashboard VALUES (?,?)',(d['uid'],json.dumps(d)))
                    wrapped={'apiVersion':'dashboard.grafana.app/v0alpha1','kind':'Dashboard','metadata':{'name':d['uid'],'namespace':'default'},'spec':d}
                    c.execute('INSERT INTO resource VALUES (?,?,?,?,?,?)',('dashboard.grafana.app','dashboards','default',d['uid'],json.dumps(wrapped),2))
            args=['verify',str(JSON_DIR),'--wait','0','--files',*files]
            with patch.object(provision,'locate_database',return_value=db),patch.object(sys,'argv',args),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(provision.main(),0)
            with contextlib.closing(sqlite3.connect(db)) as c,c:
                c.execute('DELETE FROM resource WHERE name=?',('matchwise-service-comparison-en',))
            with patch.object(provision,'locate_database',return_value=db),patch.object(sys,'argv',args),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(provision.main(),1)


if __name__ == '__main__':
    unittest.main()
