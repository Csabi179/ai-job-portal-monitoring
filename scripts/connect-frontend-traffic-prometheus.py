#!/usr/bin/env python3
"""Add one scrape job while preserving the modified live config. No dependencies."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
import unittest
from urllib.parse import urlencode
from urllib.request import ProxyHandler, build_opener
import uuid

REPO = Path('/home/ubuntu/ai-job-monitoring')
LIVE = REPO / 'prometheus/prometheus.yml'


def candidate_config(original):
    text = original.decode('utf-8')
    matches = list(re.finditer(r'(?m)^scrape_configs:[ \t]*(?:#[^\r\n]*)?\r?\n', text))
    if len(matches) != 1:
        raise ValueError('Expected one block-style scrape_configs list; stopped without changes.')
    start = matches[0].end()
    rest = text[start:]
    next_section = re.search(r'(?m)^[a-zA-Z_][a-zA-Z_0-9]*:', rest)
    block = rest[:next_section.start()] if next_section else rest
    if re.search(r'''(?m)^ +-[ \t]+job_name:[ \t]*['"]?frontend_traffic['"]?[ \t]*(?:#.*)?$''', block):
        raise ValueError('frontend_traffic job already exists; inspect the active target instead of adding it again.')
    first_job = re.search(r'(?m)^( +)-[ \t]+job_name[ \t]*:', block)
    if not first_job:
        raise ValueError('Unsupported scrape_configs layout; stopped without changes.')
    indent = first_job.group(1)
    addition = (
        f'{indent}- job_name: frontend_traffic\n'
        f'{indent}  scrape_interval: 60s\n'
        f'{indent}  scrape_timeout: 10s\n'
        f'{indent}  static_configs:\n'
        f"{indent}    - targets: ['127.0.0.1:9121']\n\n"
    )
    # Every original byte is retained before/after this insertion.
    return (text[:start] + addition + text[start:]).encode('utf-8')


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def read_live():
    return run('sudo', '-n', 'cat', str(LIVE), stdout=subprocess.PIPE).stdout


def write_live(data):
    # Keep the existing inode: Docker bind-mounts this single file.
    run('sudo', '-n', 'tee', str(LIVE), input=data, stdout=subprocess.DEVNULL)


def reload_prometheus():
    run('sudo', '-n', 'docker', 'kill', '--signal=HUP', 'monitoring-prometheus', stdout=subprocess.DEVNULL)


def apply():
    opener = build_opener(ProxyHandler({}))
    def api(path):
        with opener.open('http://127.0.0.1:9090' + path, timeout=5) as response:
            result = json.load(response)
        if result.get('status') != 'success':
            raise ValueError('Prometheus API did not return success.')
        return result['data']

    mounted = run('sudo', '-n', 'docker', 'inspect', 'monitoring-prometheus', '--format',
                  '{{range .Mounts}}{{if eq .Destination "/etc/prometheus/prometheus.yml"}}{{.Source}}{{end}}{{end}}',
                  stdout=subprocess.PIPE, text=True).stdout.strip()
    if mounted != str(LIVE):
        raise ValueError('Unexpected Prometheus config mount; stopped.')
    network = run('sudo', '-n', 'docker', 'inspect', 'monitoring-prometheus', '--format',
                  '{{.HostConfig.NetworkMode}}', stdout=subprocess.PIPE, text=True).stdout.strip()
    if network != 'host':
        raise ValueError('Expected host networking; stopped.')
    with opener.open('http://127.0.0.1:9121/health', timeout=5) as response:
        if response.status != 200:
            raise ValueError('Receiver health check failed.')
    before_jobs = {row['labels'].get('job') for row in api('/api/v1/targets?state=active')['activeTargets']}
    original = read_live()
    candidate = candidate_config(original)
    backup_root = Path('/home/ubuntu/monitoring-backups')
    backup_root.mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='frontend-traffic-prometheus.', dir=backup_root))
    backup = work / 'prometheus.yml.before'
    backup.write_bytes(original)
    backup.chmod(0o600)
    staged = work / 'prometheus.yml.candidate'
    staged.write_bytes(candidate)
    staged.chmod(0o600)
    print(f'Backup: {backup}', flush=True)

    container_file = '/etc/prometheus/frontend-traffic-' + uuid.uuid4().hex + '.yml'
    run('sudo', '-n', 'docker', 'cp', str(staged), 'monitoring-prometheus:' + container_file)
    run('sudo', '-n', 'docker', 'exec', '--user', '0', 'monitoring-prometheus', 'chmod', '644', container_file)
    run('sudo', '-n', 'docker', 'exec', 'monitoring-prometheus', 'promtool', 'check', 'config', container_file)
    if read_live() != original:
        raise ValueError('Live config changed during validation; stopped without changes.')
    modified = False
    try:
        modified = True
        write_live(candidate)
        run('sudo', '-n', 'docker', 'exec', 'monitoring-prometheus', 'promtool', 'check', 'config',
            '/etc/prometheus/prometheus.yml')
        reload_prometheus()
        print('Waiting up to 90 seconds for the first successful 60-second scrape...', flush=True)
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            try:
                targets = api('/api/v1/targets?state=active')['activeTargets']
                jobs = {row['labels'].get('job') for row in targets}
                rows = [row for row in targets if row['labels'].get('job') == 'frontend_traffic']
                query = urlencode({'query': 'frontend_telemetry_receiver_up{job="frontend_traffic"}'})
                data = api('/api/v1/query?' + query)
                samples = data.get('result', [])
                if (before_jobs <= jobs and len(rows) == 1 and rows[0].get('health') == 'up'
                    and rows[0].get('scrapeUrl') == 'http://127.0.0.1:9121/metrics'
                    and len(samples) == 1 and float(samples[0]['value'][1]) == 1):
                    print('PASS: frontend_traffic target up; receiver_up=1 in Prometheus; previous jobs retained.')
                    print('Frontend activation and real browser traffic remain pending.')
                    return
            except Exception:
                pass
            time.sleep(2)
        raise ValueError('Prometheus did not confirm receiver ingestion within 90 seconds.')
    except BaseException:
        if modified:
            print('Restoring the backed-up Prometheus config.', flush=True)
            try:
                write_live(original)
                reload_prometheus()
            except Exception:
                print(f'Automatic restore failed; restore manually from {backup}', flush=True)
        raise
    finally:
        # Remove the temporary config copy inside the container; retain the host backup.
        subprocess.run(['sudo', '-n', 'docker', 'exec', '--user', '0', 'monitoring-prometheus',
                        'rm', '-f', container_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class CandidateTests(unittest.TestCase):
    def test_preserves_live_customizations(self):
        original = b'global:\n  scrape_interval: 60s\nscrape_configs:\n  # live comment\n  - job_name: custom\n    static_configs:\n      - targets: ["127.0.0.1:9999"]\nremote_write: []\n'
        candidate = candidate_config(original)
        prefix, suffix = original.split(b'scrape_configs:\n', 1)
        self.assertTrue(candidate.startswith(prefix + b'scrape_configs:\n'))
        self.assertTrue(candidate.endswith(suffix))
        self.assertIn(b'scrape_interval: 60s', candidate)
        self.assertIn(b"targets: ['127.0.0.1:9121']", candidate)

    def test_existing_and_unsupported_layout_stop(self):
        for original in [b'scrape_configs: []\n', b'global: {}\n',
                         b'scrape_configs:\n  - job_name: "frontend_traffic"\n',
                         b'scrape_configs:\n\nscrape_configs:\n']:
            with self.assertRaises(ValueError):
                candidate_config(original)

    def test_alternative_indent(self):
        value = candidate_config(b'scrape_configs:\n    - job_name: existing\n')
        self.assertIn(b'\n    - job_name: frontend_traffic\n', value)
        self.assertTrue(value.endswith(b'    - job_name: existing\n'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--self-test', action='store_true')
    group.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        unittest.main(argv=['connect-frontend-traffic-prometheus'], verbosity=2)
    else:
        try:
            apply()
        except Exception as error:
            raise SystemExit(f'ERROR: {error}')
