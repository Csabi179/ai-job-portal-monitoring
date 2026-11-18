# Manual tests for all 12 Grafana alert rules

> **Pending update (November 18, 2026):** branch configuration now has sixteen permanent rules, thirty-five Service Comparison panels and one-minute backend probes (60s/15s/10s, three-minute freshness). The previously verified live deployment has fifteen rules; validation and rollout of this update are pending. [Validation and rollout](SECURITY_OVERVIEW_AND_FREQUENT_PROBES.md).

**Scope:** this runbook covers the original twelve rules. The current set has fifteen permanent rules; the three additions have a separate [test runbook](SERVICE_COMPARISON_ALERT_TEST.md) and [test record](monitoring-tests.md#test-20-synthetic-security-alert-cycle).

**Current applicability:** the conditions below still match the original 12 provisioned rules; HTTP targets and pending times are unchanged. Normal Grafana access uses HTTPS and Telegram delivery targets the team group. Collector and Node Exporter live tests are evidenced; procedures for the other ten rules do not mean those tests were executed. See [current state and evidence](monitoring-tests.md).


[Magyar változat](alert-rule-tests.md) · [Documentation index](README.md)

Local fixture helper: [docs/testing/alert-rule-test-helper.py](testing/alert-rule-test-helper.py).

This runbook targets configuration `41c3f8d`. **Creating this document did not run new live tests.** Previously verified: collector Firing/Resolved and Node Exporter `up=0` → Firing → `up=1` → Resolved. Other procedures below are planned; local validation is not an Oracle or Telegram delivery test. Evidence: [test log](monitoring-tests.md).

Run commands in **Bash on the Oracle Ubuntu VM**. Test one rule at a time and restore service/configuration after each test. Do not restart Grafana during a test because pending timing may reset.

## What each test exercises

| # | Rule UID | Fault input | Pending |
|---|---|---|---|
| 1 | matchwise_node_exporter_unavailable | Stop Node Exporter | 3m |
| 2 | ai_job_exporter_down | Stop Blackbox Exporter | 3m |
| 3 | matchwise_prometheus_scrape_unavailable | Redirect only self-scraping to local HTTP 503 | 3m |
| 4 | matchwise_backend_down | Blackbox probes local HTTP 503 using original series labels | 2m |
| 5 | matchwise_backend_probe_missing | Redirect backend scrape to HTTP 503: up=0 | 2m |
| 6 | matchwise_frontend_down | Blackbox probes local HTTP 503 | 2m |
| 7 | matchwise_frontend_probe_missing | Redirect frontend scrape to HTTP 503: up=0 | 2m |
| 8 | matchwise_supabase_metrics_unavailable | Metrics scrape receives local HTTP 503 | 3m |
| 9 | matchwise_supabase_database_down | Local metric source: up=1, pg_up=0 | 2m |
| 10 | matchwise_render_collector_stale | Stop collector timer | 2m after heartbeat age exceeds 300s |
| 11 | matchwise_loki_health_unavailable | Stop Loki | 3m |
| 12 | matchwise_alloy_health_unavailable | Stop Alloy | 3m |

Tests 1/2/10/11/12 pause real monitoring components. Tests 3–9 exercise unchanged live rules with controlled local inputs, not real remote application/database shutdown. Test samples enter normal Prometheus series: record the test period and exclude its synthetic samples from real application-availability interpretation. The helper does not change alert rules, tokens, SQLite or Docker volumes.

## 0. Shared preparation

Pull the commit containing this runbook first. Inspect git status: known untracked exports may remain, but reconcile local configuration changes first.

```bash
cd ~/ai-job-monitoring
git status --short
git pull --ff-only
git diff --exit-code -- prometheus/prometheus.yml
sudo docker compose config --quiet
sudo docker compose ps
sudo systemctl is-active matchwise-render-logs.timer
```

All services should be running, the collector timer active, and all 12 rules Normal after fresh evaluation. Initial KeepLast/Normal alone is not UP evidence.

Only tests 3–9 require the fixture server. Check PyYAML; if missing, install the Ubuntu package:

```bash
python3 -c 'import yaml; print(yaml.__version__)'
# Only if the import above reports a missing module:
# sudo apt-get update
# sudo apt-get install -y python3-yaml
```

Create a unique private configuration backup and start the loopback fixture. Do not expose port 19199 publicly.

```bash
mkdir -p "$HOME/monitoring-private-state"
ALERT_TEST_STATE=$(mktemp -d "$HOME/monitoring-private-state/alert-rules.XXXXXX")
printf 'Private test backup: %s\n' "$ALERT_TEST_STATE"
sudo python3 docs/testing/alert-rule-test-helper.py init --state "$ALERT_TEST_STATE"

sudo systemd-run --unit=matchwise-alert-fixture --collect \
  --property=User=ubuntu --property=Group=ubuntu --property=RuntimeMaxSec=2h \
  /usr/bin/python3 "$PWD/docs/testing/alert-rule-test-helper.py" serve

curl -fsS http://127.0.0.1:19199/http-ok
curl -sS -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:19199/http-fail
```

Expect `Local alert test recovered` and `HTTP 503`. If the unit name/port is already in use, inspect the previous test rather than overwriting another process. The 2h limit controls fixture-server lifetime; it **does not automatically restore configuration**.

Define the following helpers in the same SSH shell. Each mode starts from the original backup. The helper refuses to overwrite configuration changed outside its own workflow.

```bash
pq() {
  curl -fsSG http://127.0.0.1:9090/api/v1/query \
    --data-urlencode "query=$1" | python3 -m json.tool
}

apply_test_config() {
  sudo docker compose run --rm --no-deps --entrypoint promtool prometheus \
    check config /etc/prometheus/prometheus.yml &&
  sudo docker compose up -d --no-deps --force-recreate prometheus
}

inject() {
  sudo python3 docs/testing/alert-rule-test-helper.py prepare "$1" \
    --state "$ALERT_TEST_STATE" && apply_test_config
}

restore_prom() {
  sudo python3 docs/testing/alert-rule-test-helper.py restore \
    --state "$ALERT_TEST_STATE" && apply_test_config
}
```

Fixture scrapes run every **60s**, matching the pending live backend/frontend cadence while preserving original instance/service labels. Backend HTTP fixture tests send requests only to the local fixture, not to Render. Preserving the original instance label avoids leaving a separately labelled failed sample in the rule's three-minute window. Supabase fixtures omit all Basic Auth, secret and file_sd settings; no key is sent to the fixture server.

New samples usually appear after 60–90s, followed by pending and evaluation. Allow 30s additional group wait for a new group or up to 5m for changes to an existing group. Add grouping delay to the approximate 2–5m timings below. For every test inspect Grafana Pending/Firing/Normal and the matching Telegram firing/resolved event. You do not need to wait the 4-hour repeat interval.

## 1. Oracle host metrics — matchwise_node_exporter_unavailable

```bash
sudo docker compose stop node-exporter
# After 60–90s:
pq 'up{job="node_exporter"}'
```

**Expected:** up=0; after 3m pending, `MatchWise | Oracle host metrics | Monitoring failure` fires, usually after 3–5m plus grouping. The collector rule can retain its prior state with KeepLast while collection itself continues.

```bash
sudo docker compose start node-exporter
# After 60–90s:
pq 'up{job="node_exporter"}'
```

**Recovery:** up=1, Normal and resolved. The operator has already verified this complete cycle.

## 2. Blackbox Exporter — ai_job_exporter_down

```bash
sudo docker compose stop blackbox-exporter
# After 60–90s:
pq 'up{job="blackbox_exporter"}'
```

**Expected:** up=0; after 3m pending, `MatchWise | Blackbox Exporter | Monitoring failure` fires. Other HTTP/health monitoring alerts may also fire because this is a shared dependency; rules do not automatically inhibit them. The infrequent backend scrape may not run during a short test.

```bash
sudo docker compose start blackbox-exporter
# After 60–90s:
pq 'up{job="blackbox_exporter"}'
pq 'probe_success{job="blackbox_monitoring_components"}'
```

**Recovery:** Blackbox up=1, both Loki/Alloy probes at 1 and Blackbox resolved. Check all other alerts caused by this test; backend recovery can wait up to 30m for its natural probe.

## 3. Prometheus self-check — matchwise_prometheus_scrape_unavailable

```bash
inject prometheus-scrape-fail
# After 60–90s:
curl -fsS http://127.0.0.1:9090/-/ready
pq 'up{job="prometheus"}'
```

**Expected:** the query API remains available while self-scrape up=0; after 3m pending, `MatchWise | Prometheus self-check | Monitoring failure` fires. Stopping all of Prometheus would instead test DatasourceError, not this rule.

```bash
restore_prom
# After 60–90s:
pq 'up{job="prometheus"}'
```

**Recovery:** up=1, Normal and resolved.

## 4. Render backend HTTP — matchwise_backend_down

```bash
inject backend-http-fail
# After 60–90s:
pq 'last_over_time(up{job="blackbox_render_backend",service="matchwise_backend"}[3m])'
pq 'last_over_time(probe_success{job="blackbox_render_backend",service="matchwise_backend"}[3m])'
```

**Expected:** up=1, probe_success=0; after 2m pending, `MatchWise | Render backend | HTTP outage` fires. This state should not trigger the backend monitoring-failure rule. The real Render backend is not stopped.

```bash
inject backend-http-ok
# After 60–90s:
pq 'last_over_time(probe_success{job="blackbox_render_backend",service="matchwise_backend"}[3m])'
# Wait for Normal/resolved, then:
restore_prom
```

**Recovery:** the same series changes to probe_success=1 on a local successful response and resolves. Then restore the original 30m Render probe. The remaining synthetic success does not establish real Render availability; verify the next original scheduled scrape separately.

## 5. Render backend monitoring — matchwise_backend_probe_missing

```bash
inject backend-scrape-fail
# After 60–90s:
pq 'last_over_time(up{job="blackbox_render_backend",service="matchwise_backend"}[3m])'
```

**Expected:** up=0; after 2m pending, `MatchWise | Render backend | Monitoring failure` fires. This is a scrape failure, not a proven HTTP outage; the HTTP rule uses KeepLast.

```bash
inject backend-http-ok
# Wait for up=1, probe_success=1 and resolved, then:
restore_prom
```

**Optional missing-data branch:** run `inject backend-absent`, then `pq 'absent_over_time(up{job="blackbox_render_backend",service="matchwise_backend"}[3m])'`. Initially the result is empty because an old sample remains. Once the last sample is older than 3m, the result is 1 and the rule fires after another 2m pending: roughly 5–7m plus grouping. Do not shorten the rule's 3m window. Recover with `inject backend-http-ok`, wait for resolved, then `restore_prom`.

## 6. Vercel frontend HTTP — matchwise_frontend_down

```bash
inject frontend-http-fail
# After 60–90s:
pq 'last_over_time(up{job="blackbox_vercel_frontend",service="matchwise_frontend"}[3m])'
pq 'last_over_time(probe_success{job="blackbox_vercel_frontend",service="matchwise_frontend"}[3m])'
```

**Expected:** up=1, probe_success=0; after 2m pending, `MatchWise | Vercel frontend | HTTP outage` fires.

```bash
inject frontend-http-ok
# Wait for probe_success=1 and resolved, then:
restore_prom
```

**Recovery:** Normal/resolved, then the restored real frontend target should also succeed on its next 60s scrape.

## 7. Vercel frontend monitoring — matchwise_frontend_probe_missing

```bash
inject frontend-scrape-fail
# After 60–90s:
pq 'last_over_time(up{job="blackbox_vercel_frontend",service="matchwise_frontend"}[3m])'
```

**Expected:** up=0; after 2m pending, `MatchWise | Vercel frontend | Monitoring failure` fires. The HTTP rule has no proven new HTTP failure.

```bash
inject frontend-http-ok
# Wait for up=1, probe_success=1 and resolved, then:
restore_prom
```

**Optional missing-data branch:** `inject frontend-absent`, then `pq 'absent_over_time(up{job="blackbox_vercel_frontend",service="matchwise_frontend"}[3m])'`. After 3m without samples the result is 1; after another 2m pending expect firing, roughly 5–7m plus grouping. Recover with `inject frontend-http-ok`, wait for resolved, then `restore_prom`.

## 8. Supabase metrics — matchwise_supabase_metrics_unavailable

```bash
inject supabase-metrics-fail
# After 60–90s:
pq 'up{job="supabase",instance="uvopvarvelpabhmrqaaw.supabase.co:443"}'
```

**Expected:** up=0; after 3m pending, `MatchWise | Supabase | Monitoring failure` fires. The PostgreSQL rule keeps its previous state; this does not establish a real database outage.

```bash
inject supabase-ok
# After 60–90s:
pq 'pg_up{job="supabase",instance="uvopvarvelpabhmrqaaw.supabase.co:443"}'
# Wait for up=1, pg_up=1 and resolved, then:
restore_prom
```

**Recovery:** first the local fixture, then the real Supabase source after restoration must return up=1 and pg_up=1. Do not change or print credentials.

## 9. Supabase PostgreSQL — matchwise_supabase_database_down

```bash
inject supabase-db-fail
# After 60–90s:
pq 'up{job="supabase",instance="uvopvarvelpabhmrqaaw.supabase.co:443"}'
pq 'pg_up{job="supabase",instance="uvopvarvelpabhmrqaaw.supabase.co:443"}'
```

**Expected:** up=1, pg_up=0; after 2m pending, `MatchWise | Supabase PostgreSQL | Connectivity failure` fires. This state should not trigger the Metrics API monitoring rule. The synthetic pg_up input neither stops nor tests the real PostgreSQL database, Auth or PostgREST.

```bash
inject supabase-ok
# Wait for up=1, pg_up=1 and resolved, then:
restore_prom
```

**Recovery:** Normal/resolved; after restoration verify both real Supabase metrics too.

## 10. Render log collector — matchwise_render_collector_stale

```bash
sudo systemctl stop matchwise-render-logs.timer
sudo systemctl is-active matchwise-render-logs.timer
sudo systemctl is-active matchwise-render-logs.service
pq 'max(time() - matchwise_render_collector_last_success_timestamp_seconds{job="node_exporter"})'
```

**Expected:** timer inactive. If a oneshot is still running, wait for completion; do not kill it during a write. Heartbeat age exceeds 300s while Node Exporter remains up=1, then after 2m pending `MatchWise | Render log collector | Monitoring failure` fires. Allow about 7–10m plus grouping since last successful run. The nonzero exit status from is-active for an inactive unit is expected.

```bash
sudo systemctl start matchwise-render-logs.service
sudo systemctl start matchwise-render-logs.timer
sudo systemctl show matchwise-render-logs.service -p Result -p ExecMainStatus
sudo systemctl is-active matchwise-render-logs.timer
# After 60–90s:
pq 'max(time() - matchwise_render_collector_last_success_timestamp_seconds{job="node_exporter"})'
pq 'node_textfile_scrape_error{job="node_exporter"}'
```

**Recovery:** Result=success, ExecMainStatus=0, timer active, fresh heartbeat, textfile error=0, Normal/resolved. Firing/Resolved has already been verified. Do not delete heartbeat, SQLite or cursor files. This alone is not a Loki-delivery test.

## 11. Loki health — matchwise_loki_health_unavailable

```bash
sudo docker compose stop loki
# After 60–90s:
pq 'up{job="blackbox_monitoring_components",service="loki"}'
pq 'probe_success{job="blackbox_monitoring_components",service="loki"}'
```

**Expected:** up=1, probe_success=0; after 3m pending, `MatchWise | Loki | Health check failure` fires. Loki writes/queries pause and Alloy may report forwarding errors/retries; this test does not guarantee lossless log delivery.

```bash
sudo docker compose start loki
curl -fsS http://127.0.0.1:3100/ready
# Retry curl later if startup returns 503 or connection refused.
# After 60–90s:
pq 'probe_success{job="blackbox_monitoring_components",service="loki"}'
```

**Recovery:** ready, probe_success=1, Normal/resolved. Check Alloy and actual log delivery separately; a health response alone is not delivery evidence.

## 12. Alloy health — matchwise_alloy_health_unavailable

```bash
sudo docker compose stop alloy
# After 60–90s:
pq 'up{job="blackbox_monitoring_components",service="alloy"}'
pq 'probe_success{job="blackbox_monitoring_components",service="alloy"}'
```

**Expected:** up=1, probe_success=0; after 3m pending, `MatchWise | Alloy | Health check failure` fires. The collector may continue writing JSONL while forwarding into Loki is paused.

```bash
sudo docker compose start alloy
curl -fsS http://127.0.0.1:12345/-/healthy
# Retry curl later if the service is still starting.
# After 60–90s:
pq 'probe_success{job="blackbox_monitoring_components",service="alloy"}'
```

**Recovery:** healthy, probe_success=1, Normal/resolved. The Alloy volume/read positions remain; verify real log delivery separately.

## Completion and recovery from an interrupted test

If injection or validation fails, do not continue to another test. Run `restore_prom` in the same shell and inspect the result. In a new SSH session, set ALERT_TEST_STATE to the exact previously printed private directory and redefine the helpers, or use the direct commands:

```bash
# Replace the placeholder with your previously printed private directory:
# ALERT_TEST_STATE="$HOME/monitoring-private-state/alert-rules.XXXXXX"
sudo python3 docs/testing/alert-rule-test-helper.py restore --state "$ALERT_TEST_STATE"
sudo docker compose run --rm --no-deps --entrypoint promtool prometheus \
  check config /etc/prometheus/prometheus.yml
# Only after successful validation:
sudo docker compose up -d --no-deps --force-recreate prometheus
```

If the helper refuses restoration because another process changed configuration, compare the private backup and current file before proceeding. Do not use reset --hard.

After all tests you actually performed:

```bash
restore_prom
sudo docker compose start node-exporter blackbox-exporter loki alloy
sudo systemctl start matchwise-render-logs.timer
sudo systemctl is-active matchwise-render-logs.timer
sudo systemctl stop matchwise-alert-fixture.service
git diff --exit-code -- prometheus/prometheus.yml
sudo docker compose ps
pq 'up{job="node_exporter"}'
pq 'up{job="blackbox_exporter"}'
pq 'up{job="prometheus"}'
pq 'probe_success{job="blackbox_monitoring_components"}'
pq 'up{job="supabase",instance="uvopvarvelpabhmrqaaw.supabase.co:443"}'
pq 'pg_up{job="supabase",instance="uvopvarvelpabhmrqaaw.supabase.co:443"}'
```

If you did not start the fixture, a missing fixture systemd unit is not a new application fault. Preserve the private backup until verification is complete. Empty/0 results are not success; the restored backend can take up to 30m to run its natural probe. Close all Grafana/Telegram events associated with each test.

Record date/time zone, commit, UID, real versus synthetic input, query results, Firing/Resolved delivery and restored state in the [test log](monitoring-tests.md). One successful test does not prove all 12. Complete VM/Grafana failure requires independent external monitoring; these rules do not replace it.
