"""Contract and rollout checks for the additional, request-ID-paired timing plot."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


builder = module('paired_builder', 'build-request-correlation-dashboard.py')
installer = module('paired_installer', 'install-request-table-details.py')


class PairedRequestChartTests(unittest.TestCase):
    def model(self, suffix='-en'):
        return json.loads((builder.DEST / f'matchwise-service-comparison{suffix}.json').read_text(encoding='utf-8'))

    def test_same_queries_id_join_and_browser_start_for_both_timings(self):
        for lang, suffix in [('hu', ''), ('en', '-en')]:
            model = builder.update_paired_chart(self.model(suffix), lang)
            table = next(p for p in model['panels'] if p['id'] == 980)
            chart = next(p for p in model['panels'] if p['id'] == 987)
            self.assertEqual(chart['targets'], table['targets'])
            self.assertTrue(all(t['maxLines'] == 1000 for t in chart['targets']))
            self.assertTrue(all('avg_over_time' not in t['expr'] and 'unwrap' not in t['expr'] for t in chart['targets']))
            # The entire table extraction/deduplication/join prefix is retained,
            # including the frontend-only guard. Arrival order/time/route cannot join rows.
            prefix = [t for t in table['transformations'] if t['id'] not in ('organize', 'sortBy')]
            self.assertEqual(chart['transformations'][:len(prefix)], prefix)
            joins = [t['options'] for t in chart['transformations'] if t['id'] == 'joinByField']
            self.assertEqual(joins, [{'byField': 'request_id', 'mode': 'outerTabular'}])
            extra = chart['transformations'][len(prefix):]
            self.assertEqual(extra[0]['options']['match'], 'all')
            self.assertEqual({f['fieldName'] for f in extra[0]['options']['filters']}, {
                'frontend_started_ms (lastNotNull)', 'frontend_ms (lastNotNull)', 'backend_ms (lastNotNull)'})
            self.assertEqual(extra[1]['options']['conversions'], [{
                'targetField': 'frontend_started_ms (lastNotNull)', 'destinationType': 'time'}])
            self.assertEqual(extra[-1]['options']['renameByName'], {
                'frontend_started_ms (lastNotNull)': 'Time', 'frontend_ms (lastNotNull)': 'Frontend',
                'backend_ms (lastNotNull)': 'Backend', 'request_id': 'Request ID'})
            self.assertFalse(chart['fieldConfig']['defaults']['custom']['spanNulls'])
            self.assertEqual(chart['fieldConfig']['defaults']['unit'], 'ms')

    def test_click_links_keep_row_id_and_context_without_changing_numeric_series(self):
        for lang, suffix in [('hu', ''), ('en', '-en')]:
            model = self.model(suffix)
            # Existing filter values must not override the clicked row's ID.
            variable = next(v for v in model['templating']['list'] if v['name'] == 'request_id')
            variable['current'] = {'text': 'old-filter', 'value': 'old-filter'}
            chart = next(p for p in builder.update_paired_chart(model, lang)['panels'] if p['id'] == 987)
            kept = next(t for t in chart['transformations'] if t['id'] == 'filterFieldsByName')['options']['include']['names']
            self.assertEqual(kept, ['frontend_started_ms (lastNotNull)', 'frontend_ms (lastNotNull)',
                                    'backend_ms (lastNotNull)', 'request_id'])
            self.assertEqual(len(chart['fieldConfig']['overrides']), 2)
            for override in chart['fieldConfig']['overrides']:
                links = next(p['value'] for p in override['properties'] if p['id'] == 'links')
                self.assertEqual(len(links), 1)
                link = links[0]
                self.assertFalse(link['oneClick'])  # First click must show ID, not navigate immediately.
                self.assertFalse(link['targetBlank'])
                self.assertIn('${__data.fields["Request ID"]}', link['title'])
                self.assertTrue(link['url'].startswith('/d/' + model['uid'] + '?from=${__from}&to=${__to}'))
                self.assertEqual(link['url'].count('var-request_id='), 1)
                self.assertNotIn('${request_id', link['url'])
                for variable in model['templating']['list']:
                    if variable['name'] != 'request_id':
                        self.assertIn('${' + variable['name'] + ':queryparam}', link['url'])
                # Different requests with identical timestamps still resolve from
                # their own row ID; no time-based lookup or first-match ID is used.
                for request_id in ('11111111-1111-4111-8111-111111111111', '22222222-2222-4222-8222-222222222222'):
                    resolved = link['url'].replace('${__data.fields["Request ID"]}', request_id)
                    self.assertTrue(resolved.endswith('&var-request_id=' + request_id))

    def test_only_new_panel_and_necessary_layout_shift_then_idempotent(self):
        current = self.model()
        original = copy.deepcopy(current)
        original['panels'] = [p for p in original['panels'] if p['id'] != 987]
        start = next(p for p in current['panels'] if p['id'] == 987)['gridPos']['y']
        for panel in installer.walk(original['panels']):
            if panel['gridPos']['y'] >= start:
                panel['gridPos']['y'] -= 8
        installed = builder.update_paired_chart(original, 'en')
        self.assertEqual(installed, current)
        installer.validate_scope(json.dumps(original), json.dumps(installed),
                                 'matchwise-service-comparison-en.json', paired_chart=True)
        self.assertEqual(builder.update_paired_chart(installed, 'en'), installed)
        installer.validate_scope(json.dumps(installed), json.dumps(installed),
                                 'matchwise-service-comparison-en.json', paired_chart=True)
        self.assertEqual(len(original['panels']) + 1, len(installed['panels']))

    def test_installer_rejects_changed_existing_graph_or_table(self):
        old = self.model()
        for panel_id in (980, 981, 986):
            changed = copy.deepcopy(old)
            next(p for p in changed['panels'] if p['id'] == panel_id)['title'] = 'Unexpected change'
            with self.subTest(panel=panel_id), self.assertRaises(ValueError):
                installer.validate_scope(json.dumps(old), json.dumps(changed),
                                         'matchwise-service-comparison-en.json', paired_chart=True)

    def test_refuses_unrelated_reserved_panel_or_wrong_join(self):
        for change in ('panel', 'join'):
            model = self.model()
            if change == 'panel':
                next(p for p in model['panels'] if p['id'] == 987)['type'] = 'stat'
            else:
                table = next(p for p in model['panels'] if p['id'] == 980)
                next(t for t in table['transformations'] if t['id'] == 'joinByField')['options']['byField'] = 'Time'
            with self.subTest(change=change), self.assertRaises(ValueError):
                builder.update_paired_chart(model, 'en')


if __name__ == '__main__':
    unittest.main()
