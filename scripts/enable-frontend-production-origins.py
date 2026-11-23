#!/usr/bin/env python3
"""Add both production browser origins, preserving the running receiver's allowlist."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

SERVICE = 'matchwise-frontend-traffic.service'
PRODUCTION = ('https://www.matchwise.tech', 'https://matchwise.tech')
KEY = 'FRONTEND_TRAFFIC_ORIGINS'
DROPIN = Path('/etc/systemd/system') / (SERVICE + '.d') / 'zz-production-origins.conf'
PATH = '/matchwise-telemetry/v1'


def allowed_origins(environment):
    values = [v.split(b'=', 1)[1].decode('utf-8') for v in environment.split(b'\0') if v.startswith(KEY.encode() + b'=')]
    if len(values) != 1:
        raise ValueError('Expected one explicit running receiver origin setting')
    origins = list(dict.fromkeys(values[0].split(',')))
    # Systemd specifiers/quotes/newlines must not be introduced through config.
    if any(not value or any(c in value for c in ('%', '"', '\\', '\n', '\r', '*')) for value in origins):
        raise ValueError('Unexpected origin format; inspect existing configuration manually')
    return list(dict.fromkeys(origins + list(PRODUCTION)))


def systemctl(*args):
    return subprocess.check_output(['systemctl', *args], text=True).strip()


def check_cors(base):
    opener = build_opener(ProxyHandler({}))
    for origin, status in [*( (origin, 204) for origin in PRODUCTION), ('https://unrelated.invalid', 403)]:
        request = Request(base + PATH, method='OPTIONS', headers={
            'Origin': origin, 'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type'})
        try:
            response = opener.open(request, timeout=15)
        except HTTPError as error:
            response = error
        with response:
            actual = response.status
            allowed = response.headers.get('Access-Control-Allow-Origin')
        if actual != status or (status == 204 and allowed != origin) or (status == 403 and allowed is not None):
            raise RuntimeError(f'CORS check failed for {origin}: HTTP {actual}')


def restart_and_wait():
    systemctl('daemon-reload')
    systemctl('restart', SERVICE)
    opener = build_opener(ProxyHandler({}))
    for attempt in range(20):
        try:
            with opener.open('http://127.0.0.1:9121/health', timeout=2) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.25)
    raise RuntimeError('Receiver health check failed')


def main():
    if os.geteuid() != 0:
        raise SystemExit('Run this helper with sudo.')
    if systemctl('is-active', SERVICE) != 'active':
        raise RuntimeError('Receiver is not active; inspect it before changing origins')
    pid = int(systemctl('show', SERVICE, '--property=MainPID', '--value'))
    if pid <= 0:
        raise RuntimeError('Receiver has no running process')
    origins = allowed_origins((Path('/proc') / str(pid) / 'environ').read_bytes())
    content = '[Service]\nEnvironment=' + json.dumps(KEY + '=' + ','.join(origins)) + '\n'
    previous = DROPIN.read_bytes() if DROPIN.exists() else None
    previous_mode = DROPIN.stat().st_mode & 0o777 if previous is not None else 0o644
    backup_root = Path('/home/ubuntu/monitoring-backups')
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix='frontend-origins.', dir=backup_root))
    if previous is not None:
        shutil.copy2(DROPIN, backup / 'dropin.before.conf')
    else:
        (backup / 'dropin.was-absent').touch()
    print('Backup:', backup, flush=True)
    DROPIN.parent.mkdir(parents=True, exist_ok=True)
    try:
        DROPIN.write_text(content, encoding='utf-8')
        DROPIN.chmod(0o644)
        restart_and_wait()
        check_cors('http://127.0.0.1:9121')
        check_cors('https://grafana-r0cecq.duckdns.org')
    except BaseException:
        if previous is None:
            DROPIN.unlink(missing_ok=True)
        else:
            DROPIN.write_bytes(previous)
            DROPIN.chmod(previous_mode)
        restart_and_wait()
        raise
    print('PASS: www and apex production origins accepted locally and over HTTPS; unrelated origin rejected.')
    print('Receiver only restarted; no telemetry POST or business request was fabricated.')
    print('Open the real frontend, make a normal API request and keep the tab open for 60-120 seconds.')


if __name__ == '__main__':
    main()
