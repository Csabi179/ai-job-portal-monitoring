#!/usr/bin/env python3
"""Oracle table-only update, with live Loki preflight and automatic file rollback."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time
from urllib.parse import urlencode
from urllib.request import ProxyHandler, build_opener

FILES = [f'matchwise-{kind}{suffix}.json' for suffix in ('', '-en')
         for kind in ('service-comparison', 'request-correlation')]


def walk(panels):
    for panel in panels:
        yield panel
        yield from walk(panel.get('panels', []))


def validate_scope(before, after, name):
    panel_id = 980 if 'service-comparison' in name else 2
    old = json.loads(before)
    new = json.loads(after)
    if old.get('uid') != name[:-5] or new.get('uid') != old['uid']:
        raise ValueError(f'Unexpected UID in {name}')
    old_table = [p for p in walk(old['panels']) if p['id'] == panel_id]
    new_table = [p for p in walk(new['panels']) if p['id'] == panel_id]
    if len(old_table) != 1 or len(new_table) != 1 or new_table[0]['type'] != 'table':
        raise ValueError(f'Unexpected request table in {name}')
    if old_table[0]['gridPos'] != new_table[0]['gridPos']:
        raise ValueError(f'Table moved in {name}')
    new_table[0].clear()
    new_table[0].update(old_table[0])
    if new != old:
        raise ValueError(f'Changes outside request table in {name}')


def validate_loki(expressions):
    opener = build_opener(ProxyHandler({}))
    end = time.time_ns()
    for expression in sorted(expressions):
        expression = expression.replace('${request_id:regex}', '')
        params = {'query': expression, 'start': end - 3600_000_000_000,
                  'end': end, 'limit': 1, 'direction': 'backward'}
        url = 'http://127.0.0.1:3100/loki/api/v1/query_range?' + urlencode(params)
        with opener.open(url, timeout=15) as response:
            result = json.load(response)
        if result.get('status') != 'success':
            raise ValueError('Loki rejected a request-table query')
    print('PASS: Loki accepts the request-table queries (empty results allowed).')


def replace_file(path, content):
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        shutil.copymode(path, tmp)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ref')
    args = parser.parse_args()
    repo = Path.cwd()
    ref = subprocess.check_output(['git', 'rev-parse', '--verify', args.ref + '^{commit}'], text=True).strip()
    directory = repo / 'grafana/provisioning/dashboards/json'
    before = {name: (directory / name).read_bytes() for name in FILES}
    with tempfile.TemporaryDirectory(prefix='matchwise-request-table-') as temp:
        staging = Path(temp)
        builder = staging / 'builder.py'
        builder.write_bytes(subprocess.check_output(['git', 'show', ref + ':scripts/build-request-correlation-dashboard.py']))
        for name, content in before.items():
            (staging / name).write_bytes(content)
        subprocess.run(['python3', str(builder), '--request-table-only', str(staging)], check=True)
        after = {name: (staging / name).read_bytes() for name in FILES}
    expressions = set()
    for name in FILES:
        validate_scope(before[name], after[name], name)
        panel_id = 980 if 'service-comparison' in name else 2
        table = next(p for p in walk(json.loads(after[name])['panels']) if p['id'] == panel_id)
        expressions.update(t['expr'] for t in table['targets'])
    validate_loki(expressions)
    root = Path.home() / 'monitoring-backups'
    root.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix='request-table-details.', dir=root))
    for name, content in before.items():
        (backup / name).write_bytes(content)
    (backup / 'source-commit.txt').write_text(ref + '\n', encoding='ascii')
    print('Backup:', backup, flush=True)
    # Avoid overwriting a file changed by another operator during preflight.
    if any((directory / name).read_bytes() != content for name, content in before.items()):
        raise RuntimeError('Dashboards changed during preflight; no files installed. Repeat after reviewing.')
    written = []
    try:
        for name in FILES:
            if before[name] != after[name]:
                written.append(name)
                replace_file(directory / name, after[name])
        for name in FILES:
            if (directory / name).read_bytes() != after[name]:
                raise RuntimeError(f'Post-write verification failed: {name}')
    except BaseException:
        for name in reversed(written):
            replace_file(directory / name, before[name])
        raise
    print('PASS: only the four HU/EN request tables updated; graphs and runtime services unchanged.')
    print('Allow up to 60 seconds for Grafana provisioning, then refresh.')
    print('Missing backend error code is displayed as —, never inferred from HTTP status.')
    for name in FILES:
        print('Rollback:', 'cp --', shlex.quote(str(backup / name)), shlex.quote(str(directory / name)))


if __name__ == '__main__':
    main()
