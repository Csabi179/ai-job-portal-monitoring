"""Optional local fixtures for the manual alert-rule runbook.

No Docker/systemd commands, network requests, secret reads or Telegram sends.
serve listens on loopback. init/prepare/restore touch only the selected
Prometheus config and an explicitly supplied private backup directory.
"""
import argparse
import copy
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BACKEND = 'https://matchwise-backend-monitoring-test.onrender.com/api/health'
FRONTEND = 'https://www.matchwise.tech/'
SUPABASE = 'uvopvarvelpabhmrqaaw.supabase.co:443'
FIXTURE = '127.0.0.1:19199'
MODES = ['prometheus-scrape-fail', 'backend-http-fail', 'backend-http-ok',
         'backend-scrape-fail', 'backend-absent', 'frontend-http-fail',
         'frontend-http-ok', 'frontend-scrape-fail', 'frontend-absent',
         'supabase-metrics-fail', 'supabase-db-fail', 'supabase-ok']


class FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/http-fail', '/scrape-fail'):
            status, body, mime = 503, 'Intentional local alert test\n', 'text/plain'
        elif self.path == '/http-ok':
            status, body, mime = 200, 'Local alert test recovered\n', 'text/plain'
        elif self.path in ('/pg-down', '/pg-up'):
            value = 0 if self.path == '/pg-down' else 1
            labels = ('service_type="postgresql",'
                      'supabase_identifier="uvopvarvelpabhmrqaaw",'
                      'supabase_project_ref="uvopvarvelpabhmrqaaw"')
            body = '# TYPE pg_up gauge\n' + f'pg_up{{{labels}}} {value}\n'
            status, mime = 200, 'text/plain; version=0.0.4'
        else:
            status, body, mime = 404, 'Unknown fixture\n', 'text/plain'
        raw = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *_):
        pass


def make_config(original, mode):
    """Build exactly one test override, always starting from the backup."""
    result = copy.deepcopy(original)
    if mode.startswith('prometheus-'):
        job_name = 'prometheus'
    elif mode.startswith('backend-'):
        job_name = 'blackbox_render_backend'
    elif mode.startswith('frontend-'):
        job_name = 'blackbox_vercel_frontend'
    else:
        job_name = 'supabase'
    matches = [i for i, job in enumerate(result['scrape_configs']) if job['job_name'] == job_name]
    if len(matches) != 1:
        raise ValueError(f'Expected exactly one job: {job_name}')
    index = matches[0]
    if mode.endswith('-absent'):
        result['scrape_configs'].pop(index)
        return result
    labels = {}
    if job_name == 'prometheus':
        labels['instance'] = '127.0.0.1:9090'
    elif job_name == 'supabase':
        labels.update(instance=SUPABASE, project='uvopvarvelpabhmrqaaw', service='matchwise_database')
    else:
        backend = job_name == 'blackbox_render_backend'
        labels.update(instance=BACKEND if backend else FRONTEND,
                      service='matchwise_backend' if backend else 'matchwise_frontend')

    # New jobs intentionally omit Basic Auth, file_sd, HTTPS and secret paths.
    job = {'job_name': job_name, 'scrape_interval': '60s', 'scrape_timeout': '15s'}
    if '-http-' in mode:
        target = f'http://{FIXTURE}/http-' + ('fail' if mode.endswith('-fail') else 'ok')
        job.update(metrics_path='/probe',
                   params={'module': ['http_render_2xx' if job_name == 'blackbox_render_backend' else 'http_2xx']},
                   static_configs=[{'targets': [target], 'labels': labels}],
                   relabel_configs=[
                       {'source_labels': ['__address__'], 'target_label': '__param_target'},
                       {'target_label': '__address__', 'replacement': '127.0.0.1:9115'}])
    else:
        path = '/pg-down' if mode == 'supabase-db-fail' else '/pg-up' if mode == 'supabase-ok' else '/scrape-fail'
        job.update(metrics_path=path, static_configs=[{'targets': [FIXTURE], 'labels': labels}])
    result['scrape_configs'][index] = job
    return result


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write_config(path, raw):
    info = path.stat()
    fd, temporary = tempfile.mkstemp(prefix='.alert-rule-test-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, info.st_mode & 0o777)
        if hasattr(os, 'chown'):
            os.chown(temporary, info.st_uid, info.st_gid)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['serve', 'init', 'prepare', 'restore'])
    parser.add_argument('mode', nargs='?', choices=MODES)
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--state', type=Path)
    args = parser.parse_args()
    if args.action == 'serve':
        HTTPServer(('127.0.0.1', 19199), FixtureHandler).serve_forever()
        return
    if args.state is None:
        parser.error('--state is required')
    config = (args.repo / 'prometheus/prometheus.yml').resolve()
    state = args.state.resolve()
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    manifest_path = state / 'manifest.json'
    backup = state / 'prometheus.original.yml'
    if args.action == 'init':
        if manifest_path.exists() or backup.exists():
            parser.error('Backup already exists; use a new private state directory')
        raw = config.read_bytes()
        backup.write_bytes(raw)
        os.chmod(backup, 0o600)
        manifest = {'config': str(config), 'original_sha256': digest(raw), 'current_sha256': digest(raw)}
    else:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest['config'] != str(config) or digest(config.read_bytes()) != manifest['current_sha256']:
            parser.error('Config path/content changed outside this helper; inspect before restoring')
        raw = backup.read_bytes()
        if digest(raw) != manifest['original_sha256']:
            parser.error('Backup checksum mismatch')
        if args.action == 'prepare':
            if args.mode is None:
                parser.error('prepare requires a mode')
            import yaml
            raw = yaml.safe_dump(make_config(yaml.safe_load(raw), args.mode), sort_keys=False).encode('utf-8')
        write_config(config, raw)
        manifest['current_sha256'] = digest(raw)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    os.chmod(manifest_path, 0o600)
    print(f'{args.action}: config={config}; backup preserved at {backup}')
    print('No containers changed. Validate and recreate Prometheus using the runbook.')


if __name__ == '__main__':
    main()
