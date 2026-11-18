#!/usr/bin/env python3
"""Read-only checks of new alert queries on the Oracle VM. No alerts installed."""
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
import sys

doc = json.loads(Path(sys.argv[1]).read_text())
failed = False
for group in doc['groups']:
    for rule in group['rules']:
        for query in rule['data']:
            source = query['datasourceUid']
            if source not in ('prometheus', 'loki'):
                continue
            base = 'http://127.0.0.1:9090/api/v1/query' if source == 'prometheus' else 'http://127.0.0.1:3100/loki/api/v1/query'
            try:
                with urlopen(base + '?' + urlencode({'query': query['model']['expr']}), timeout=30) as response:
                    result = json.load(response)
                if result.get('status') != 'success':
                    raise ValueError('Query did not succeed')
                values = result['data']['result']
                print(rule['uid'], query['refId'], 'OK', json.dumps(values))
                if not values:
                    print('No valid telemetry: fix this before installing the rules.')
                    failed = True
            except Exception as error:
                print(rule['uid'], query['refId'], 'FAILED', type(error).__name__)
                failed = True
raise SystemExit(1 if failed else 0)
