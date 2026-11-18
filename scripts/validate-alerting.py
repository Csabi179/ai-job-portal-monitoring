"""Validate provisioning and exercise its actual PromQL with promtool.

Requires PyYAML and promtool on PATH, or --promtool /path/to/promtool.
Does not contact Oracle, Render, Supabase, Grafana or Telegram.
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--promtool', default='promtool')
    args = parser.parse_args()
    rules = {}
    deleted = set()
    for path in sorted((ROOT / 'grafana/provisioning/alerting').iterdir()):
        doc = yaml.safe_load(path.read_text(encoding='utf-8'))
        assert doc['apiVersion'] == 1, path
        # A locally deployed demo is separate from the 15 permanent rules.
        if path.name == 'service-comparison-test.json':
            allowed = {'mw_test_cpu_flow', 'mw_test_5xx_flow', 'mw_test_login_flow'}
            for item in doc.get('deleteRules', []):
                assert item['uid'] in allowed, item
            for group in doc.get('groups', []):
                assert group['name'] == 'service-comparison-test', group['name']
                for rule in group['rules']:
                    assert rule['uid'] in allowed, rule['uid']
                    assert rule['labels']['test'] == 'true', rule['uid']
                    annotations = rule.get('annotations', {})
                    assert bool(annotations.get('__dashboardUid__')) == bool(annotations.get('__panelId__')), rule['uid']
            print('Checked temporary demo IDs; excluded demo from permanent-rule scenarios.')
            continue
        deleted.update(r['uid'] for r in doc.get('deleteRules', []))
        for group in doc.get('groups', []):
            assert group['interval'] == '1m', path
            for rule in group['rules']:
                uid = rule['uid']
                annotations = rule.get('annotations', {})
                assert bool(annotations.get('__dashboardUid__')) == bool(annotations.get('__panelId__')), (uid, 'incomplete dashboard/panel link')
                assert uid not in rules, uid
                assert not rule['isPaused'], uid
                assert rule['execErrState'] == ('KeepLast' if rule['noDataState'] == 'KeepLast' else 'Error'), uid
                assert rule['noDataState'] in ('Alerting', 'KeepLast'), uid
                assert rule['condition'] == 'C', uid
                assert rule['labels']['category'] in ('monitoring', 'availability', 'security'), uid
                assert rule['data'][-1]['model']['conditions'][0]['evaluator'] == {'params': [0.5], 'type': 'gt'}, uid
                rules[uid] = rule
    assert len(rules) == 15, len(rules)
    security_uids = {'matchwise_backend_cpu_high', 'matchwise_backend_5xx_burst', 'matchwise_backend_login_burst'}
    assert security_uids <= rules.keys()
    for uid in security_uids:
        assert rules[uid]['labels']['category'] == 'security'
        assert rules[uid]['noDataState'] == 'KeepLast'
    # The original promtool suite covers the 12 infrastructure/availability rules.
    # New cross-datasource rules require check-service-comparison-queries.py and Grafana evaluation.
    rules = {uid: rule for uid, rule in rules.items() if uid not in security_uids}
    assert deleted == {'ai_job_test_endpoint_down', 'ai_job_low_memory', 'ai_job_low_disk'}
    assert not deleted.intersection(rules)
    policy = yaml.safe_load((ROOT / 'grafana/provisioning/alerting/telegram.yml').read_text(encoding='utf-8'))
    receiver = policy['contactPoints'][0]['receivers'][0]
    assert receiver['disableResolveMessage'] is False
    assert receiver['settings']['bottoken'] == '$GRAFANA_TELEGRAM_BOT_TOKEN'
    assert receiver['settings']['chatid'] == '$GRAFANA_TELEGRAM_CHAT_ID'
    assert receiver['settings']['parse_mode'] == 'None'
    prom = yaml.safe_load((ROOT / 'prometheus/prometheus.yml').read_text(encoding='utf-8'))
    jobs = {job['job_name']: job for job in prom['scrape_configs']}
    assert jobs['blackbox_render_backend']['scrape_interval'] == '30m'
    assert jobs['blackbox_render_backend']['scrape_timeout'] == '110s'
    assert jobs['supabase']['basic_auth']['password_file'] == '/etc/prometheus/secrets/supabase-api-key'
    assert len(jobs['blackbox_monitoring_components']['static_configs']) == 2

    tests = []

    def case(name, inputs, expectations, when='1m'):
        tests.append({'name': name, 'interval': '1m',
                      'input_series': [{'series': s, 'values': v} for s, v in inputs.items()],
                      'promql_expr_test': [
                          {'expr': rules[uid]['data'][0]['model']['expr'], 'eval_time': when,
                           'exp_samples': [] if value is None else [{'labels': '{}', 'value': value}]}
                          for uid, value in expectations.items()]})

    # An entirely empty database must expose every monitoring gap, never UP.
    case('all telemetry absent', {}, {uid: None if r['noDataState'] == 'KeepLast' else 1 for uid, r in rules.items()})
    for job, uid in [('node_exporter', 'matchwise_node_exporter_unavailable'),
                     ('blackbox_exporter', 'ai_job_exporter_down'),
                     ('prometheus', 'matchwise_prometheus_scrape_unavailable')]:
        case(job + ' scrape success', {f'up{{job="{job}"}}': '1 1'}, {uid: 0})
        case(job + ' scrape failure', {f'up{{job="{job}"}}': '1 0'}, {uid: 1})
    for prefix, job, service in [('backend', 'blackbox_render_backend', 'matchwise_backend'),
                                 ('frontend', 'blackbox_vercel_frontend', 'matchwise_frontend')]:
        suffix = f'{{job="{job}",service="{service}"}}'
        u, p = 'up' + suffix, 'probe_success' + suffix
        down, missing = f'matchwise_{prefix}_down', f'matchwise_{prefix}_probe_missing'
        case(prefix + ' HTTP success', {u: '1 1', p: '1 1'}, {down: 0, missing: 0})
        case(prefix + ' latest HTTP failure', {u: '1 1', p: '1 0'}, {down: 1, missing: 0})
        case(prefix + ' HTTP recovery', {u: '1 1', p: '0 1'}, {down: 0, missing: 0})
        case(prefix + ' scrape failure is not HTTP failure', {u: '1 0', p: '0 stale'}, {down: None, missing: 1})
        case(prefix + ' scrape succeeds without probe metric', {u: '1 1'}, {down: None, missing: 1})
        if prefix == 'backend':
            case('backend old success expires', {u: '1', p: '1'}, {down: None, missing: 1}, '41m')
            case('backend old failure expires without recovery', {u: '1', p: '0'}, {down: None, missing: 1}, '41m')
            case('backend retains sparse sample at 39 minutes', {u: '1', p: '0'}, {down: 1, missing: 0}, '39m')
            case('backend second scrape fails', {u: '1 ' + '_ ' * 29 + '0', p: '1 ' + '_ ' * 29 + 'stale'}, {down: None, missing: 1}, '31m')
        else:
            case('frontend expired sample', {u: '1', p: '0'}, {down: None, missing: 1}, '4m')

    sb = '{job="supabase",instance="uvopvarvelpabhmrqaaw.supabase.co:443"}'
    sm, sd = 'matchwise_supabase_metrics_unavailable', 'matchwise_supabase_database_down'
    case('Supabase healthy', {'up' + sb: '1 1', 'pg_up' + sb: '1 1'}, {sm: 0, sd: 0})
    case('database inaccessible with healthy Metrics API', {'up' + sb: '1 1', 'pg_up' + sb: '1 0'}, {sm: 0, sd: 1})
    case('Metrics API failure is not database failure', {'up' + sb: '1 0', 'pg_up' + sb: '1 stale'}, {sm: 1, sd: None})
    case('database status missing', {'up' + sb: '1+0x5'}, {sm: 1, sd: None}, '5m')
    n = 'up{job="node_exporter"}'
    heartbeat = 'matchwise_render_collector_last_success_timestamp_seconds{job="node_exporter"}'
    err = 'node_textfile_scrape_error{job="node_exporter"}'
    collector = 'matchwise_render_collector_stale'
    case('quiet application with fresh collector', {n: '1+0x10', heartbeat: '0+60x10', err: '0+0x10'}, {collector: 0}, '10m')
    case('collector frozen timestamp', {n: '1+0x10', heartbeat: '0+0x10', err: '0+0x10'}, {collector: 1}, '10m')
    case('collector heartbeat file missing', {n: '1 1', err: '0 0'}, {collector: 1})
    case('textfile processing failure', {n: '1 1', heartbeat: '0 60', err: '1 1'}, {collector: 1})
    case('Node Exporter unavailable', {n: '0 0'}, {collector: None, 'matchwise_node_exporter_unavailable': 1})
    for service in ('loki', 'alloy'):
        labels = f'{{job="blackbox_monitoring_components",service="{service}"}}'
        uid = f'matchwise_{service}_health_unavailable'
        case(service + ' health success', {'up' + labels: '1 1', 'probe_success' + labels: '1 1'}, {uid: 0})
        case(service + ' health failure', {'up' + labels: '1 1', 'probe_success' + labels: '1 0'}, {uid: 1})
        case(service + ' probe scrape failure', {'up' + labels: '1 0'}, {uid: 1})

    with tempfile.TemporaryDirectory(prefix='matchwise-alert-tests-') as folder:
        path = Path(folder) / 'expressions.yml'
        path.write_text(yaml.safe_dump({'rule_files': [], 'evaluation_interval': '1m', 'tests': tests}), encoding='utf-8')
        subprocess.run([args.promtool, 'test', 'rules', str(path)], check=True)
    print(f'PASS: {len(rules)} rules, {len(tests)} PromQL scenarios; live delivery not tested.')


if __name__ == '__main__':
    main()
