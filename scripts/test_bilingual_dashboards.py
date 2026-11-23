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
    def test_timing_trend_updater_preserves_table_and_all_other_panels(self):
        import copy
        requests = module('timing_trend', 'build-request-correlation-dashboard.py')
        audit = module('timing_expansion', 'check-dashboard-final-audit.py')
        for lang, suffix in [('hu', ''), ('en', '-en')]:
            name = f'matchwise-service-comparison{suffix}.json'
            old = json.loads(subprocess.check_output(
                ['git', 'show', f'fc94f130d7aa50418dfd954205b7ea811c4464d1:grafana/provisioning/dashboards/json/{name}'],
                cwd=REPO).decode('utf-8'))
            new = requests.update_timing_trend(copy.deepcopy(old), lang)
            self.assertEqual(new, requests.update_timing_trend(copy.deepcopy(new), lang))
            before = {p['id']: p for p in checker.walk(old['panels'])}
            after = {p['id']: p for p in checker.walk(new['panels'])}
            self.assertEqual(set(before) | {986}, set(after))
            bottom = before[981]['gridPos']['y'] + before[981]['gridPos']['h']
            for key in before:
                if key != 981:
                    expected = copy.deepcopy(before[key])
                    def shift(items):
                        for panel in items:
                            if panel['gridPos']['y'] >= bottom:
                                panel['gridPos']['y'] += 5
                            shift(panel.get('panels', []))
                    shift([expected])
                    self.assertEqual(after[key], expected)
            chart = after[981]
            self.assertEqual(chart['gridPos'], before[981]['gridPos'])
            self.assertEqual(chart['transformations'], [])
            self.assertTrue(chart['fieldConfig']['defaults']['custom']['spanNulls'])
            self.assertEqual(chart['fieldConfig']['defaults']['custom']['lineStyle']['fill'], 'dash')
            self.assertEqual(chart['interval'], '5m')
            counts = after[986]
            self.assertEqual(counts['gridPos']['y'], chart['gridPos']['y'] + chart['gridPos']['h'])
            self.assertEqual(counts['interval'], chart['interval'])
            self.assertEqual(counts['maxDataPoints'], chart['maxDataPoints'])
            for latency, count in zip(chart['targets'], counts['targets']):
                self.assertIn('count_over_time', count['expr'])
                self.assertNotIn('unwrap', count['expr'])
                pipeline = count['expr'].split('count_over_time(', 1)[1].split(' [$__interval]', 1)[0]
                self.assertIn(pipeline, latency['expr'])
            variable = next(v for v in new['templating']['list'] if v['name'] == 'timing_stat')
            self.assertEqual(variable['current']['value'], '0')
            for mode in ('0', '1'):
                variable['current']['value'] = mode
                for target in chart['targets']:
                    expr = audit.expand(target['expr'], new)
                    self.assertTrue(checker.balanced(expr))
                    self.assertNotIn('$', expr)
                    self.assertIn('by ()', expr)
                    self.assertIn('vector(0) / vector(0)', expr)  # Empty steps are NaN, not zero.
                    self.assertNotIn('maxLines', target)
                    self.assertIn('route!~', expr)
                    self.assertIn('unwrap', expr)
            self.assertIn('uptimerobot', chart['targets'][1]['expr'])
            self.assertIn('mode="real"', chart['targets'][0]['expr'])
            # Keep an existing P95 selection during subsequent idempotent updates.
            again = requests.update_timing_trend(copy.deepcopy(new), lang)
            self.assertEqual(again, new)

    def test_http_signal_counts_secondary_averages_and_graphs_stay_together(self):
        import copy
        requests = module('http_signals', 'build-request-correlation-dashboard.py')
        for lang, suffix in [('hu', ''), ('en', '-en')]:
            name = f'matchwise-service-comparison{suffix}.json'
            old = json.loads(subprocess.check_output(
                ['git', 'show', f'c9b21046093d85e16f039b2be91d5ff2f5d4a01f:grafana/provisioning/dashboards/json/{name}'],
                cwd=REPO).decode('utf-8'))
            new = requests.readable_http_signals(copy.deepcopy(old), lang)
            self.assertEqual(new, requests.readable_http_signals(copy.deepcopy(new), lang))
            before = {p['id']: p for p in checker.walk(old['panels'])}
            after = {p['id']: p for p in checker.walk(new['panels'])}
            for key in (29, 30, 31, 32):
                count, average = after[key], after[982 + key - 29]
                d = count['fieldConfig']['defaults']
                self.assertEqual(d['thresholds']['steps'], [
                    {'value': None, 'color': 'gray'}, {'value': 1, 'color': 'orange'}])
                self.assertEqual(d['mappings'][0]['options']['result']['color'], 'gray')
                self.assertNotIn('$__range_s', count['targets'][0]['expr'])
                self.assertIn('$__range_s', average['targets'][0]['expr'])
                self.assertLess(average['options']['textSize']['value'], count['options']['textSize']['value'])
                self.assertEqual(average['gridPos']['y'], count['gridPos']['y'] + count['gridPos']['h'])
                self.assertEqual(average['gridPos']['x'], count['gridPos']['x'])
                self.assertEqual(count['gridPos']['h'] + average['gridPos']['h'], before[key]['gridPos']['h'])
            self.assertLess(after[28]['gridPos']['h'], before[28]['gridPos']['h'])
            self.assertLess(len(after[28]['options']['content']), len(before[28]['options']['content']))
            self.assertIn('429', after[28]['description'])
            for key in (33, 34):
                self.assertEqual(after[key]['options']['legend']['calcs'], [])
                self.assertEqual([t['expr'] for t in after[key]['targets']],
                                 [t['expr'] for t in before[key]['targets']])
                for axis in ('x', 'w', 'h'):
                    self.assertEqual(after[key]['gridPos'][axis], before[key]['gridPos'][axis])
            self.assertEqual(after[33]['gridPos']['y'], after[34]['gridPos']['y'])
            self.assertEqual(after[980], before[980])
            self.assertEqual(after[981], before[981])

    def test_period_summaries_upgrade_old_models_without_changing_other_queries(self):
        import copy
        requests = module('period_summaries', 'build-request-correlation-dashboard.py')
        for lang, suffix in [('hu', ''), ('en', '-en')]:
            name = f'matchwise-service-comparison{suffix}.json'
            old = json.loads(subprocess.check_output(
                ['git', 'show', f'212c4902a4bc1e5b20b5edb8428d9951319d57db:grafana/provisioning/dashboards/json/{name}'],
                cwd=REPO).decode('utf-8'))
            old['live_setting'] = 'keep'
            result = requests.selected_period_summary(copy.deepcopy(old), lang)
            self.assertEqual(result, requests.selected_period_summary(copy.deepcopy(result), lang))
            self.assertEqual(result['live_setting'], 'keep')
            before = {p['id']: p for p in checker.walk(old['panels'])}
            after = {p['id']: p for p in checker.walk(result['panels'])}
            changed_queries = {29, 30, 31, 32, 309, 310, 323, 324, 337, 338}
            for key, panel in after.items():
                if key not in changed_queries and key in before:
                    self.assertEqual([t.get('expr') for t in panel.get('targets', [])],
                                     [t.get('expr') for t in before[key].get('targets', [])])
            for key in changed_queries:
                for target in after[key]['targets']:
                    expr = target['expr']
                    self.assertIn('[$__range]', expr)
                    self.assertNotIn('[5m]', expr)
                    self.assertNotIn('time()', expr)
                    self.assertNotIn('min(up', expr)  # Current health must not hide history.
                    self.assertTrue(target['instant'])
                    self.assertFalse(target['range'])
                    expanded = checker.substitute(expr)
                    self.assertNotIn('$__', expanded)
                    self.assertNotIn('15m_s', expanded)
                    if key in (29, 30, 31, 32):
                        self.assertNotIn('$__range_s', expr)  # Main value is the exact count.
                        self.assertIn('route!~', expr)
                        self.assertEqual(after[key]['fieldConfig']['defaults']['decimals'], 0)
                        average = after[982 + key - 29]
                        self.assertEqual(average['targets'][0]['expr'], f'({expr}) * 60 / $__range_s')
                    if key in (323, 324):
                        self.assertIn('route!~', expr)
                        self.assertIn('route=~', expr)
            for key in (310, 324, 338):
                self.assertIn('> 0', after[key]['targets'][0]['expr'])
                self.assertNotIn('avg_over_time', after[key]['targets'][0]['expr'])
            for key in (33, 34, 377):
                defaults = after[key]['fieldConfig']['defaults']
                self.assertEqual(defaults['min'], 0)
                self.assertNotIn('max', defaults)  # Peaks above one must remain visible.
                self.assertEqual(defaults['custom']['axisSoftMax'], 1)
            self.assertEqual(after[981], before[981])  # Request timing graph is not an event counter.

    def test_visual_refinements_preserve_queries_and_distinguish_failures_from_speed(self):
        requests = module('visual_refinements', 'build-request-correlation-dashboard.py')
        for lang, suffix in [('hu', ''), ('en', '-en')]:
            current = read(JSON_DIR / f'matchwise-service-comparison{suffix}.json')
            result = requests.embed_comparison_table(current, lang)
            before = [p.get('targets', []) for p in checker.walk(current['panels'])]
            after = [p.get('targets', []) for p in checker.walk(result['panels'])]
            self.assertEqual(before, after)
            self.assertEqual(result, current)
            table = next(p for p in result['panels'] if p['id'] == 980)
            organize = table['transformations'][-1]['options']
            self.assertEqual(organize['indexByName']['frontend_started_ms (lastNotNull)'], 0)
            self.assertEqual(organize['indexByName']['request_id'], 8)
            self.assertTrue(organize['excludeByName']['backend_route (lastNotNull)'])
            overrides = {o['matcher']['options']: {p['id']: p['value'] for p in o['properties']}
                         for o in table['fieldConfig']['overrides']}
            for side in ('frontend', 'backend'):
                duration = overrides[side + '_ms (lastNotNull)']
                self.assertEqual(duration['custom.cellOptions']['type'], 'auto')
                status = overrides[side + '_status (lastNotNull)']
                red = [m for m in status['mappings'] if m['type'] == 'range'
                       and m['options']['from'] == 500][0]
                self.assertEqual(red['options']['result']['color'], 'red')
                self.assertEqual(red['options']['to'], 599)
                self.assertNotIn('text', red['options']['result'])  # Keep the actual HTTP code.
            cards = [p for p in result['panels'] if p['type'] == 'stat'][:16]
            mapping = cards[0]['fieldConfig']['defaults']['mappings'][0]['options']['1']['text']
            self.assertIn('HTTP', mapping)
            self.assertNotEqual(cards[1]['title'], cards[9]['title'])  # Probe vs metrics scrape.
            for index in (3, 7, 11):
                d = cards[index]['fieldConfig']['defaults']
                nulls = [m for m in d['mappings'] if m['type'] == 'special' and m['options']['match'] == 'null']
                self.assertEqual(nulls[0]['options']['result']['color'], 'gray')
                self.assertNotEqual(nulls[0]['options']['result']['text'], '0%')

    def test_request_table_insertion_preserves_live_panels_and_is_idempotent(self):
        requests = module('request_table', 'build-request-correlation-dashboard.py')
        original = {
            'uid': 'matchwise-service-comparison-en', 'custom_live_setting': 'keep',
            'templating': {'list': [{'name': 'existing_filter', 'type': 'textbox'}]},
            'panels': [
                {'id': 901, 'type': 'row', 'title': '01 · Scorecard · now',
                 'gridPos': {'x': 0, 'y': 0, 'w': 24, 'h': 1}},
                {'id': 321, 'type': 'stat', 'title': 'Live custom card', 'custom': 'keep',
                 'gridPos': {'x': 0, 'y': 1, 'w': 24, 'h': 3}},
                {'id': 902, 'type': 'row', 'title': '02 · Availability and freshness',
                 'gridPos': {'x': 0, 'y': 4, 'w': 24, 'h': 1}},
                {'id': 903, 'type': 'row', 'title': 'Details', 'collapsed': True,
                 'gridPos': {'x': 0, 'y': 5, 'w': 24, 'h': 1},
                 'panels': [{'id': 30, 'type': 'text', 'title': 'Existing detail',
                             'gridPos': {'x': 0, 'y': 6, 'w': 24, 'h': 3}}]},
            ],
        }
        result = requests.embed_comparison_table(original, 'en')
        self.assertEqual([p['id'] for p in result['panels']], [901, 321, 981, 986, 987, 980, 902, 903])
        chart, counts, paired, table = result['panels'][2:6]
        self.assertEqual(chart['type'], 'timeseries')
        self.assertEqual(table['type'], 'table')
        self.assertEqual(chart['gridPos'], {'x': 0, 'y': 4, 'w': 24, 'h': 8})
        self.assertEqual(counts['gridPos'], {'x': 0, 'y': 12, 'w': 24, 'h': 5})
        self.assertEqual(paired['gridPos'], {'x': 0, 'y': 17, 'w': 24, 'h': 8})
        self.assertEqual(table['gridPos'], {'x': 0, 'y': 25, 'w': 24, 'h': 12})
        self.assertEqual(result['panels'][6]['gridPos']['y'], 37)
        self.assertEqual(result['panels'][7]['panels'][0]['gridPos']['y'], 39)
        self.assertNotEqual(chart['targets'], table['targets'])
        self.assertEqual(chart['transformations'], [])
        self.assertEqual(chart['interval'], '5m')
        self.assertEqual(chart['maxDataPoints'], 600)
        for target in chart['targets']:
            self.assertIn('avg_over_time(', target['expr'])
            self.assertIn('quantile_over_time(0.95,', target['expr'])
            self.assertIn('[$__interval]', target['expr'])
            self.assertNotIn('maxLines', target)
        self.assertTrue(chart['fieldConfig']['defaults']['custom']['spanNulls'])
        self.assertEqual(chart['fieldConfig']['defaults']['min'], 0)
        self.assertEqual(result['panels'][1], original['panels'][1])
        self.assertEqual(result['custom_live_setting'], 'keep')
        self.assertEqual([v['name'] for v in result['templating']['list']], ['existing_filter', 'request_id', 'timing_stat'])
        self.assertEqual(requests.embed_comparison_table(result, 'en'), result)
        self.assertEqual(len(original['panels']), 4)

    def test_replacing_old_bars_reclaims_space_and_keeps_request_table(self):
        requests = module('request_chart_replacement', 'build-request-correlation-dashboard.py')
        current = read(JSON_DIR / 'matchwise-service-comparison-en.json')
        old = json.loads(json.dumps(current))
        graph = next(p for p in old['panels'] if p['id'] == 981)
        old_bottom = graph['gridPos']['y'] + graph['gridPos']['h']
        graph['type'] = 'barchart'
        graph['gridPos']['h'] = 14
        def shift(items):
            for p in items:
                if p['gridPos']['y'] >= old_bottom:
                    p['gridPos']['y'] += 6
                shift(p.get('panels', []))
        shift(old['panels'])
        self.assertEqual(requests.embed_comparison_table(old, 'en'), current)

    def copy_models(self, tmp):
        for name in checker.FILES:
            (Path(tmp) / name).write_bytes((JSON_DIR / name).read_bytes())
        return Path(tmp)

    def test_committed_dashboards_pass_structure_parity_and_consistency(self):
        self.assertEqual(run_checker(JSON_DIR), 0)

    def test_api_count_uses_selected_period_and_survives_current_receiver_staleness(self):
        audit=module('range_audit','check-dashboard-final-audit.py')
        for suffix in ('','-en'):
            d=read(JSON_DIR/('matchwise-unified-monitoring'+suffix+'.json'))
            card=next(p for p in d['panels'] if p['id']==335)
            target=card['targets'][0];expr=target['expr']
            self.assertIn('sum(increase(frontend_api_requests_started_total',expr)
            self.assertIn('[$__range]',expr)
            self.assertNotIn('rate(',expr)
            self.assertNotIn('up{',expr)
            self.assertNotIn('last_received',expr)
            self.assertTrue(target['instant']);self.assertFalse(target['range'])
            self.assertNotIn('/min',card['fieldConfig']['defaults']['unit'])
            for seconds in (900,7200):
                self.assertIn('['+str(seconds)+'s]',audit.expand(expr,d,seconds))

    def test_frontend_host_placeholders_are_removed_with_visible_explanation(self):
        for name in checker.FILES:
            d=read(JSON_DIR/name)
            ids={p['id'] for p in checker.walk(d['panels'])}
            removed={333,334} if 'unified' in name else {314,315}
            self.assertFalse(ids&removed)
            heading=d['panels'][0]['options']['content']
            self.assertIn('Frontend host',heading)
            self.assertIn('CPU',heading)
            self.assertIn('Vercel',heading)

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
