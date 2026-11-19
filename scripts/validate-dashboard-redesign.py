#!/usr/bin/env python3
"""Validate layout and preservation of the previously reviewed queries (no network)."""
import argparse
import json
from pathlib import Path


def walk(panels):
    for panel in panels:
        yield panel
        yield from walk(panel.get('panels', []))


def validate(candidate, baseline):
    panels = list(walk(candidate['panels']))
    by_id = {p['id']: p for p in panels}
    assert len(by_id) == len(panels), 'Duplicate panel IDs'
    assert candidate['uid'] == baseline['uid'] == 'matchwise-service-comparison'
    assert candidate['templating'] == baseline['templating'], 'Datasource variable changed'
    assert candidate['refresh'] == baseline['refresh']
    for old in walk(baseline['panels']):
        new = by_id[old['id']]
        assert new['type'] == old['type'], f"Panel type changed: {old['id']}"
        # Legend text may change; every existing expression, datasource and query mode stays.
        for item in old.get('targets', []):
            target = next(t for t in new['targets'] if t['refId'] == item['refId'])
            for key in ('expr', 'datasource', 'instant', 'range', 'queryType'):
                assert target.get(key) == item.get(key), (old['id'], key)
    # New overview views reuse exact reviewed expressions and datasource selections.
    sources = {47: [(26, 0)], 50: [(41, 2)], 51: [(44, 1)], 52: [(46, 1)],
               53: [(10, 0), (11, 0), (13, 0)], 54: [(14, 0), (15, 0), (17, 0)], 55: [(42, 2)]}
    for panel_id, pairs in sources.items():
        targets = by_id[panel_id]['targets']
        assert len(targets) == len(pairs)
        for target, (source_id, index) in zip(targets, pairs):
            source = by_id[source_id]['targets'][index]
            assert target['expr'] == source['expr']
            assert target.get('datasource', by_id[panel_id].get('datasource')) == source.get('datasource', by_id[source_id].get('datasource'))
    for panel in panels:
        if panel['type'] == 'timeseries':
            assert panel['fieldConfig']['defaults']['custom']['spanNulls'] is False
        if panel['type'] == 'row':
            assert not panel['panels'] or panel['collapsed']
        if panel['id'] in (53, 54):
            assert panel['fieldConfig']['defaults']['max'] == 100
    def layout(items):
        for index, p in enumerate(items):
            a = p['gridPos']
            assert a['x'] >= 0 and a['y'] >= 0 and a['w'] > 0 and a['h'] > 0 and a['x'] + a['w'] <= 24
            for q in items[index + 1:]:
                b = q['gridPos']
                overlap = a['x'] < b['x'] + b['w'] and b['x'] < a['x'] + a['w'] and a['y'] < b['y'] + b['h'] and b['y'] < a['y'] + a['h']
                assert not overlap, f"Panels overlap: {p['id']}, {q['id']}"
            layout(p.get('panels', []))
    layout(candidate['panels'])
    for p in candidate['panels']:
        if p['type'] == 'timeseries':
            assert not any(prop['id'] == 'custom.axisPlacement' and prop['value'] == 'right'
                           for override in p['fieldConfig'].get('overrides', []) for prop in override['properties'])
    print(f"PASS: {len(panels)} nodes; original queries preserved; overview single axes; layout valid.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('baseline', type=Path)
    args = parser.parse_args()
    validate(json.loads(args.candidate.read_text(encoding='utf-8-sig')),
             json.loads(args.baseline.read_text(encoding='utf-8-sig')))


if __name__ == '__main__':
    main()
