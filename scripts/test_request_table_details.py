"""Guard the table-only rollout and its request-ID/error-code provenance."""
import copy
import contextlib
import importlib.util
import json
import io
import itertools
from pathlib import Path
import unittest
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('request_tables', ROOT / 'scripts/build-request-correlation-dashboard.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
INSTALL_SPEC = importlib.util.spec_from_file_location('table_installer', ROOT / 'scripts/install-request-table-details.py')
installer = importlib.util.module_from_spec(INSTALL_SPEC)
INSTALL_SPEC.loader.exec_module(installer)


class RequestTableDetailsTests(unittest.TestCase):
    def test_only_table_changes_in_all_four_dashboards(self):
        for lang, suffix in [('hu', ''), ('en', '-en')]:
            for kind, panel_id in [('service-comparison', 980), ('request-correlation', 2)]:
                with self.subTest(lang=lang, kind=kind):
                    path = builder.DEST / f'matchwise-{kind}{suffix}.json'
                    original = json.loads(path.read_text(encoding='utf-8'))
                    old = copy.deepcopy(original)
                    old_table = next(p for p in old['panels'] if p['id'] == panel_id)
                    old_table['targets'] = [{'expr': 'legacy matchwise_frontend_requests'}]
                    changed = builder.update_request_table(old, lang, panel_id)
                    expected = copy.deepcopy(old)
                    index = next(i for i, p in enumerate(expected['panels']) if p['id'] == panel_id)
                    expected['panels'][index] = changed['panels'][index]
                    self.assertEqual(changed, expected)  # Graphs, variables, links and layout stay identical.
                    self.assertEqual(changed['panels'][index]['gridPos'], old_table['gridPos'])
                    self.assertEqual(builder.update_request_table(changed, lang, panel_id), changed)
                    self.assertEqual(old_table['targets'][0]['expr'], 'legacy matchwise_frontend_requests')

    def test_method_and_error_are_from_the_correct_side_of_the_id_join(self):
        table = next(p for p in builder.build('en')['panels'] if p['type'] == 'table')
        front, back = (t['expr'] for t in table['targets'])
        self.assertIn('"frontend_method":{{ printf "%q" .method }}', front)
        self.assertNotIn('errorCode', front)
        self.assertIn('event="http_request"', back)
        self.assertIn('"request_id":{{ printf "%q" .reqId }}', back)
        self.assertIn('"backend_error_code":{{ printf "%q" .errorCode }}', back)
        transforms = table['transformations']
        joins = [t['options'] for t in transforms if t['id'] == 'joinByField']
        self.assertEqual(joins, [{'byField': 'request_id', 'mode': 'outerTabular'}])
        # Different arrival times and equal routes must not become matching keys.
        for t in transforms:
            if t['id'] == 'groupBy':
                keys = [k for k, v in t['options']['fields'].items() if v['operation'] == 'groupby']
                self.assertEqual(keys, ['request_id'])
        self.assertIn('request_id=~"' + builder.UUID + '"', front)
        self.assertIn('reqId=~"' + builder.UUID + '"', back)
        self.assertEqual(transforms[-1]['options']['renameByName']['frontend_method (lastNotNull)'], 'Method')
        self.assertEqual(transforms[-1]['options']['renameByName']['backend_error_code (lastNotNull)'], 'Backend error code')

    def test_missing_codes_are_not_reported_as_success_or_fabricated(self):
        table = next(p for p in builder.build('en')['panels'] if p['type'] == 'table')
        overrides = {o['matcher']['options']: o['properties'] for o in table['fieldConfig']['overrides']}
        props = {p['id']: p['value'] for p in overrides['backend_error_code (lastNotNull)']}
        mappings = props['mappings']
        self.assertEqual(mappings[0]['options']['pattern'], '^$')
        self.assertEqual(mappings[0]['options']['result']['text'], '—')
        self.assertEqual(mappings[1]['options']['match'], 'null')
        self.assertEqual(mappings[1]['options']['result']['text'], '—')
        self.assertNotIn('color', props)

    def test_updater_refuses_unrelated_or_missing_table(self):
        for panels in ([], [{'id': 980, 'type': 'table', 'targets': [{'expr': 'unrelated'}]}]):
            with self.assertRaises(ValueError):
                builder.update_request_table({'panels': panels}, 'en')

    def test_installer_rejects_graph_variable_or_uid_changes(self):
        name = 'matchwise-service-comparison-en.json'
        original = json.loads((builder.DEST / name).read_text(encoding='utf-8'))
        for change in ('graph', 'variable', 'uid'):
            changed = copy.deepcopy(original)
            if change == 'graph':
                next(p for p in changed['panels'] if p['id'] == 981)['title'] = 'changed'
            elif change == 'variable':
                changed['templating']['list'][0]['label'] = 'changed'
            else:
                changed['uid'] = 'wrong-dashboard'
            with self.subTest(change=change), self.assertRaises(ValueError):
                installer.validate_scope(json.dumps(original), json.dumps(changed), name)

    def test_installer_preflight_and_partial_write_failure_preserve_live_files(self):
        source = (ROOT / 'scripts/build-request-correlation-dashboard.py').read_bytes()
        real_run = subprocess.run
        real_replace = installer.replace_file
        for failure, paired in itertools.product(('none', 'loki', 'second-write'), (False, True)):
            with self.subTest(failure=failure, paired=paired), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                directory = root / 'grafana/provisioning/dashboards/json'
                directory.mkdir(parents=True)
                originals = {}
                for name in installer.FILES:
                    model = json.loads((builder.DEST / name).read_text(encoding='utf-8'))
                    panel_id = 980 if 'service-comparison' in name else 2
                    next(p for p in model['panels'] if p['id'] == panel_id)['title'] = 'Before update'
                    originals[name] = json.dumps(model).encode()
                    (directory / name).write_bytes(originals[name])
                writes = []
                def replace(path, content):
                    writes.append(path.name)
                    if failure == 'second-write' and len(writes) == 2:
                        raise OSError('simulated disk failure')
                    real_replace(path, content)
                def run(command, **kwargs):
                    return real_run([sys.executable, *command[1:]], **kwargs)
                with contextlib.ExitStack() as stack:
                    stack.enter_context(patch.object(Path, 'cwd', return_value=root))
                    stack.enter_context(patch.object(Path, 'home', return_value=root))
                    stack.enter_context(patch.object(sys, 'argv', ['installer', 'reviewed-ref'] + (['--paired-chart'] if paired else [])))
                    stack.enter_context(patch.object(installer.subprocess, 'check_output', side_effect=['a' * 40, source]))
                    stack.enter_context(patch.object(installer.subprocess, 'run', side_effect=run))
                    loki = stack.enter_context(patch.object(installer, 'validate_loki', side_effect=OSError('Loki offline') if failure == 'loki' else None))
                    stack.enter_context(patch.object(installer, 'replace_file', side_effect=replace))
                    stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                    if failure == 'none':
                        installer.main()
                    else:
                        with self.assertRaises(OSError):
                            installer.main()
                    loki.assert_called_once()
                for name in installer.FILES:
                    actual = (directory / name).read_bytes()
                    if failure == 'none' and (not paired or 'service-comparison' in name):
                        installer.validate_scope(originals[name], actual, name, paired_chart=paired)
                        self.assertNotEqual(originals[name], actual)
                    else:
                        self.assertEqual(actual, originals[name])
                if failure == 'loki':
                    self.assertEqual(writes, [])


if __name__ == '__main__':
    unittest.main()
