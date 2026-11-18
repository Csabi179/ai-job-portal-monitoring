# MatchWise – alerting plan and Oracle deployment procedure

[Magyar változat](alerting-plan.md) · [Documentation index](README.md)

**Current documented state (November 18, 2026):** 15 permanent rules: 12 outage/monitoring rules plus three backend resource/security signals. Render CPU/RAM collection and the Service Comparison dashboard are deployed. Screenshots prove synthetic Firing/Resolved Telegram delivery for all three new rules; the operator confirmed cleanup and a real ten-failed-login test. Earlier collector/Node Exporter delivery evidence remains; the other ten original rules have not been fully tested live. See [test records](monitoring-tests.md).

Exact commands for the original 12 rules: [English](alert-rule-tests.en.md) · [Hungarian](alert-rule-tests.md).

## Purpose and decisions

Outage and monitoring alerts are joined by three backend signals. High Render CPU, many 5xx responses and many rejected POST logins can send notifications. One wrong password, RAM/disk usage, a slow but successful HTTP response, P95, general 4xx and absence of traffic are not active alert conditions.

### Review of the previous nine rules

| Original rule / UID | Decision | Reason |
|---|---|---|
| Monitoring Test Endpoint DOWN / ai_job_test_endpoint_down | Delete from provisioned state | Local test; Grafana cannot report its own complete outage |
| Oracle – Low Available Memory / ai_job_low_memory | Delete | Capacity, not an outage |
| Oracle – Low Disk Space / ai_job_low_disk | Delete | Capacity, not an outage |
| Oracle – Exporter DOWN / ai_job_exporter_down | Modify | Existing UID now monitors Blackbox; Node Exporter and Prometheus have separate missing-series-aware rules |
| MatchWise Backend DOWN / matchwise_backend_down | Modify | Latest fresh probe failure; missing data is not replaced by a healthy zero |
| Backend Monitoring Data Missing / matchwise_backend_probe_missing | Modify | 40-minute freshness and latest scrape failure |
| MatchWise Frontend DOWN / matchwise_frontend_down | Modify | Fresh HTTP failure, distinct from scrape failure |
| Frontend Monitoring Data Missing / matchwise_frontend_probe_missing | Modify | 3-minute freshness and scrape failure |
| Render Log Collector Stale / matchwise_render_collector_stale | Modify | Heartbeat/textfile processing, conditional on Node Exporter availability |

The original backend/frontend rules required the latest two probes to fail; this could add another 30 minutes for the backend. The replacement reports one unsuccessful completed backend probe, allowing its full 100-second prober timeout and then 2 minutes pending. Probes still run every 30 minutes. A 22-second cold start that ends in HTTP 200 is not an alert condition.

The three removed UIDs appear explicitly under `deleteRules`: deleting a provisioning file alone would not delete the stored rule. The earlier outage/monitoring set contains **12 rules**; with the three additions there are **15 permanent rules**, evaluated **every minute**.

## Three new rules added November 18

| UID | Condition | Pending |
|---|---|---|
| matchwise_backend_cpu_high | Render CPU >80% with fresh valid resource data | 5m |
| matchwise_backend_5xx_burst | At least five non-health HTTP 5xx responses in the rolling last five minutes | 2m |
| matchwise_backend_login_burst | At least ten POST login 401 responses in the rolling last five minutes, all users combined | 2m |

The two-minute pending period does not require new failures: earlier events still count while they remain in the five-minute window. One minute is the evaluation frequency. See [timing examples, telemetry gates and KeepLast](SERVICE_COMPARISON_ALERTS.md). New log rules combine a Loki A query, a Prometheus D gate and Grafana B/E/F/C expressions; they differ from the simpler PromQL chain of the original twelve rules below.

[Test and cleanup](SERVICE_COMPARISON_ALERT_TEST.md). Later original deployment and rollback examples concern the earlier outage bundle; the current permanent count is fifteen.

## Exact conditions and delays of the original twelve rules

The actual `A` PromQL expressions, `B=last(A)` reductions and `C: B > 0.5` thresholds are in the [provisioning directory](../grafana/provisioning/alerting/). The definitions below describe those files; there are no hidden dashboard variables. The English update changes titles, summaries, descriptions and runbook links only, not rule logic or UIDs.

| Rule UID | Outage or monitoring-failure definition | Pending | Approximate detection before notification grouping |
|---|---|---|---|
| matchwise_node_exporter_unavailable | `1 - (min(up{job="node_exporter"}) or vector(0)) > 0.5` | 3m | About 3–5m after scrape failure; removed series also depend on lookback/staleness |
| ai_job_exporter_down | Same for `job="blackbox_exporter"` | 3m | About 3–5m for scrape failure |
| matchwise_prometheus_scrape_unavailable | Same for `job="prometheus"` | 3m | Self-scrape failure; complete Prometheus unavailability is reported through DatasourceError |
| matchwise_backend_down | `max(1-last_over_time(probe_success[40m]))`, only when the corresponding latest `up[40m]=1` | 2m | About 2–35m from outage onset, depending on the next probe and timeout |
| matchwise_backend_probe_missing | `1-(min(last_over_time(up[40m])) or vector(0))*(max(present_over_time(probe_success[40m])) or vector(0))` | 2m | About 2–4m after scrape failure; complete sample absence about 42–44m after the last sample |
| matchwise_frontend_down | Same pattern as backend, with a `[3m]` window and frontend job/service | 2m | About 2–4m plus HTTP probe duration |
| matchwise_frontend_probe_missing | Same monitoring pattern, with `[3m]` | 2m | Scrape failure about 2–4m; missing data about 5–7m after the last sample |
| matchwise_supabase_metrics_unavailable | `up` absent/0, or no `pg_up` within 3m | 3m | API failure about 3–5m; missing pg_up about 6–8m |
| matchwise_supabase_database_down | `max(1-last_over_time(pg_up[3m]))`, only when `min(up)=1` | 2m | About 2–4m plus scrape duration |
| matchwise_render_collector_stale | Heartbeat older than 300s, missing heartbeat/textfile error indicator, or `node_textfile_scrape_error=1`; only with `up{job="node_exporter"}=1` | 2m | Stalled collection about 7–10m since last success; textfile error about 2–4m |
| matchwise_loki_health_unavailable | `probe_success` or `up` for service loki in `blackbox_monitoring_components` is 0/absent | 3m | About 3–5m; entire series disappearance may wait for lookback |
| matchwise_alloy_health_unavailable | Same for service alloy | 3m | About 3–5m; entire series disappearance may wait for lookback |

Backend selector: `job="blackbox_render_backend",service="matchwise_backend"`. Frontend: `job="blackbox_vercel_frontend",service="matchwise_frontend"`. Supabase is pinned to the current instance `uvopvarvelpabhmrqaaw.supabase.co:443`, not the previous project. An intentional project change must also update both alert selectors, otherwise missing measurements for the old project will correctly alert.

These are estimates, not SLAs. Scrape phase, prober runtime, staleness and Grafana scheduling affect them. Initial notification adds approximately up to 30 seconds of group wait; a new event in an existing group can wait up to 5 minutes. Prometheus's default instant lookback is 5 minutes, so series disappearance and the next failed scrape are not equivalent timings.

### Important distinctions

`up=1, probe_success=0`: the Blackbox scrape works but the HTTP probe failed. `up=0`: scraping failed; target application availability is unknown. The backend needs a 40-minute range because a 30-minute scrape often falls outside instant lookback. Repeated graph values are not additional probes.

`up{job="supabase"}=0`: a Metrics API, authentication or network problem is possible. `pg_up=0` with successful scraping means the exporter cannot connect to PostgreSQL. This is exporter-to-database connectivity evidence, not an independent database test. The existing dashboard and documented metric inventory include pg_up.

Loki `http://127.0.0.1:3100/ready` and Alloy `http://127.0.0.1:12345/-/healthy` are documented endpoints expected to return 200. They were initially configuration-only checks; the later operator-provided November 10 output confirmed both direct endpoint responses and both probe metrics at 1. Alloy `/-/ready` indicates startup readiness; `/-/healthy` covers component health and is the selected probe. Health is not a full ingestion/storage/delivery test.

Node Exporter failure means host monitoring has failed; it does not establish complete VM failure. A stalled collector is a monitoring-service failure because Render log collection may stop. Neither the age of the latest Loki application event nor request volume is an alert condition.

## No Data and query errors

- Backend/frontend HTTP, PostgreSQL and collector: `noDataState=KeepLast`, `execErrState=KeepLast`. Missing evidence or a query error must not clear an active outage. Related monitoring rules report telemetry failure.
- The other eight monitoring rules: `noDataState=Alerting`, `execErrState=Error`. Successfully evaluated empty selectors produce explicit failure. Fallbacks encode missing expected monitoring input as a fault; they do not declare the application UP.
- Service rules in the original twelve-rule set do not use a healthy `or vector(0)` fallback. Aggregation produces one stable label set to reduce false MissingSeries resolution.
- Initial Normal state under KeepLast is not fresh UP evidence. Interpret it alongside the related monitoring rule and sample age.
- DatasourceError events are grouped by datasource. The exact Error/Pending transitions still need testing on the running Grafana 13.2.1 instance. Normal threshold tests do not replace this.
- A runtime error affecting only a KeepLast rule's own expression can remain hidden if the related monitoring expression works. Local promtool tests, deployment-time rule Health checks and regular operator review mitigate this limitation.

## Telegram, grouping and recovery

Contact point remains **AI Job Telegram**, UID `ai_job_telegram`. Bot token/chat ID remain environment variables. On November 15, 2026, the operator reported switching the destination from a private conversation to the team's Telegram group. `disableResolveMessage=false`.

The notification language is English, including the 12 rule titles, summary/description annotations and recovery text. The template lists each event's firing/resolved state, summary and at most 200 description characters, followed by a shared English runbook link. The current descriptions are complete sentences shorter than 200 characters. Plain text (`parse_mode: None`) reduces formatting-related Telegram failures. Large groups may still be truncated by Telegram's 4096-character limit.

Normal grouping: `grafana_folder, category`, keeping availability, monitoring and security groups separate. Controlled tests use security_test. DatasourceError grouping: `alertname, datasource_uid`. Group wait 30s; group interval 5m; repeat 4h. The 4-hour repeat applies to an unchanged persistent group; group changes can notify sooner.

There is no automatic dependency inhibition. One Blackbox failure can trigger several monitoring rules, grouped into one notification. An already-active HTTP outage can remain active during a telemetry failure to avoid false recovery. Investigate shared Blackbox/Prometheus causes first.

A new successful HTTP probe clears the HTTP condition. Backend recovery can wait for the next 30-minute probe, followed by evaluation and notification grouping. A monitoring alert's resolution means measurement has recovered, not necessarily the application. Each event has its own state in the notification. There is no additional keep-firing period.


### Telegram group as the notification destination

The bot stays the same; `GRAFANA_TELEGRAM_CHAT_ID` in the private Oracle `.env` selects the destination group. Keep `GRAFANA_TELEGRAM_BOT_TOKEN` set to the existing bot token. Neither real value nor the `.env` file is versioned. Provisioning already reads these variables, so changing the destination requires no rule or YAML changes.

1. Add the bot to the destination group and allow it to send messages.
2. Send `/start@<bot_username>` in the group using the actual bot username. No reply is required: the Grafana notification bot has no command-response program.
3. Find the group's `chat.id` in the Telegram Bot API `getUpdates` response, checking `chat.title` and `chat.type` to identify the intended group. Do not expose the bot token in shared URLs or output.
4. In `~/ai-job-monitoring/.env`, replace only `GRAFANA_TELEGRAM_CHAT_ID` with the group ID, preserving its negative sign.
5. Apply the change:

```bash
cd ~/ai-job-monitoring
sudo docker compose config --quiet
sudo docker compose up -d --no-deps --force-recreate grafana
curl -fsS http://127.0.0.1:3000/api/health
```

Grafana restarts briefly; no other service restart is required. If the immediate health check fails, retry after startup. Do not share full `docker compose config` output because it can contain secrets.

As a Grafana administrator, select **Alerting → Contact points → AI Job Telegram → Test → Send test notification** and verify receipt in the destination group. This checks channel delivery, not all 12 rules' firing/resolved behavior. The group replaces the private destination; it does not add a second private delivery. To roll back, restore the previous privately retained chat ID, then repeat application and testing.

[TEST-13](monitoring-tests.md#test-13-telegram-group-delivery) records the operator-reported successful switch. API reference: [Telegram getUpdates](https://core.telegram.org/bots/api#getupdates).

## Troubleshooting

<a id="http"></a>
### HTTP

Backend: next scheduled probe, Prometheus target lastError, latest up/probe_success samples, Render deployments/logs, DNS/TLS and HTTP status. Use a manual health GET only for targeted troubleshooting because it can wake Render Free. Frontend: HTTP status, Vercel deployment and DNS/TLS; use a separate browser function test where needed.

<a id="monitoring"></a>
### Monitoring

Check `sudo docker compose ps`, Prometheus `/-/ready`, targets/scrape errors, Node/Blackbox metrics endpoints and container logs. If Node Exporter is missing, inspect host health through Oracle/SSH separately. Successful Prometheus self-scraping does not protect against full VM failure.

<a id="supabase"></a>
### Supabase

Separate Metrics API scrape health from pg_up. For 401/403, inspect private credentials/permissions, file_sd target and password-file readability. Do not print the password file. Do not automatically restore the old project. For pg_up=0, investigate Supabase/database availability; check business functions separately.

<a id="collector"></a>
### Collector

Check timer activity, oneshot Result/ExecMainStatus, journal, heartbeat age, node_textfile_scrape_error, Render API 401/403/429/5xx, flock and timeout. A quiet application can be normal while collection succeeds. Preserve SQLite and cursor state.

<a id="logs"></a>
### Loki and Alloy

Check direct health GETs and Blackbox availability, container logs, Alloy components/loki.write errors, JSONL mount/file permissions and Loki queries. Separate reqId correlation establishes actual delivery. Absence of new application logs alone is not a pipeline failure.

<a id="deployment"></a>
## Deployment on the Oracle VM

The operator runs these commands. Earlier deployment was verified through user-supplied output, not direct assistant SSH access. Preserve .env, collector state and named volumes.

### Applying a future notification-text update

The English wording is already deployed and evidenced in TEST-11. The commands below are reusable for a later text/provisioning update; no repeat deployment is needed merely to translate the existing messages.

The outage rules and new Prometheus probes were already applied at `665d2d5`. For the later language-only update, inspect the working tree, pull and validate, then recreate **Grafana only**:

```bash
cd ~/ai-job-monitoring
git status --short
# Proceed only after reviewing any local changes or untracked-file collisions.
git pull --ff-only
sudo docker compose config --quiet
sudo docker compose up -d --no-deps --force-recreate grafana
```

After startup, check `/api/health`, the 12 rules and their Health, and use the AI Job Telegram contact-point Test. Expect an English title, English recovery text when previewed, and a Runbook link to this English document. Contact-point Test proves the channel/template, not every rule. No Prometheus restart or collector-state reset is required for this language change. Renamed alert titles may be visible in history/notification identity even though UIDs and conditions are unchanged.

### Full outage-rule rollout: 1. Working tree and rollback point

The remaining steps document the original complete rollout and can be reused when applicable. They do not need to be repeated for the English-only change.

```bash
cd ~/ai-job-monitoring
git status --short
# Continue only with a clean or reviewed working tree.
PREVIOUS_MONITORING_COMMIT=$(git rev-parse HEAD)
printf '%s\n' "$PREVIOUS_MONITORING_COMMIT"
git pull --ff-only
git log -1 --oneline
sudo docker compose config --quiet
```

Record old/new commits in the private operations log. Do not overwrite local changes on conflict. Do not share full docker compose config output because it interpolates secrets.

### 2. Validate configuration and endpoints

```bash
sudo docker compose run --rm --no-deps --entrypoint promtool prometheus \
  check config /etc/prometheus/prometheus.yml

curl -fsS http://127.0.0.1:3100/ready
curl -fsS http://127.0.0.1:12345/-/healthy
curl -fsS http://127.0.0.1:3000/api/health
```

If the private Supabase mount is wrong, follow [the Supabase procedure](SUPABASE_METRICS.md) using the actual Prometheus UID. Do not rerun secret preparation merely for routine alert changes.

### 3. Apply Prometheus before Grafana

```bash
sudo docker compose up -d --no-deps --force-recreate prometheus
sudo docker compose ps prometheus
curl -fsS http://127.0.0.1:9090/-/ready
```

Readiness can fail briefly immediately after startup; retry after initialization. After the first scrape, allowing at least 60–90 seconds:

```bash
curl -fsSG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="blackbox_monitoring_components"}' | python3 -m json.tool
curl -fsSG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=probe_success{job="blackbox_monitoring_components"}' | python3 -m json.tool
curl -fsSG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="supabase",instance="uvopvarvelpabhmrqaaw.supabase.co:443"}' | python3 -m json.tool
curl -fsSG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=pg_up{job="supabase",instance="uvopvarvelpabhmrqaaw.supabase.co:443"}' | python3 -m json.tool
```

Expect both loki/alloy series and both Supabase query values to be 1. Empty output is not success. Fix measurement failures before treating new-probe startup gaps as proven service outages.

### 4. Provision Grafana

```bash
sudo docker compose up -d --no-deps --force-recreate grafana
sudo docker compose ps
curl -fsS http://127.0.0.1:3000/api/health
sudo docker compose logs --since=10m grafana
```

Restarting can affect evaluation state/pending timing. Persistent volumes remain. Using the HTTPS Grafana URL, check Alert rules:

- 12 active provisioned rules; the three deleted UIDs are absent.
- Expected UIDs; no old or manually created duplicate rules.
- Query Health is good; No Data/Error is not hidden; backend data is less than 40 minutes old.
- Contact-point/policy destination is preserved; resolved messages are enabled; template preview works.

Provisioning files do not automatically manage unknown manual rules. Record and handle any such rules separately.

### 5. Tests and evidence

Use a test environment or an agreed short maintenance window for deliberate failures. Do not accidentally affect application data.

| Scenario | Expected result | Status |
|---|---|---|
| Contact-point test and template preview | Telegram message; channel test only | English delivery evidenced in TEST-11; operator-confirmed team-group switch in TEST-13 |
| Successful frontend/backend HTTP, even 22s | No outage alert | Success condition tested in local PromQL; no separate live induced-latency test |
| HTTP failure with up=1 | HTTP outage pending → firing | Local PromQL tested; live test pending |
| up=0 or missing probe_success | Monitoring failure; no evidence-free service recovery | Local PromQL tested; live KeepLast test pending |
| Backend sample at 39m, then older than 40m | Valid at 39m, then monitoring failure | Local PromQL tested |
| Supabase API error / pg_up=0 / missing pg_up | Distinct monitoring and DB connectivity failures | Local PromQL tested; do not stop the database for a routine test |
| Stop collector timer, allow current oneshot to finish | Stale heartbeat → firing; new success → resolved | Operator supplied both Telegram notifications November 10; exact elapsed times not measured |
| No application traffic, successful collection | No collector alert | Local PromQL tested |
| Loki/Alloy health failure and recovery | Firing/resolved; distinguish measurement failure | Healthy endpoints/probes verified; induced failure test pending |
| Prometheus unavailable while Grafana runs | Grouped DatasourceError; no false service recovery | Live test pending |
| Service already firing, then data disappears | KeepLast; no missing-data resolved event | Live Grafana state-transition test pending |
| Multiple dependent faults and unchanged 4h fault | Grouping, repetition and resolved behavior | Pending |
| Complete Oracle VM failure | Do not expect local Grafana delivery | Independent external monitoring is not deployed |

Restore collector operation after a controlled timer test:

```bash
sudo systemctl start matchwise-render-logs.service
sudo systemctl start matchwise-render-logs.timer
sudo systemctl show matchwise-render-logs.service -p Result -p ExecMainStatus
sudo systemctl is-active matchwise-render-logs.timer
```

Do not delete SQLite, cursor or heartbeat to induce a test. Do not run render-logs-once.py against the active JSONL file.

For each test record date/time zone, commit, rule UID, injected input/fault, query value, pending/firing time, Telegram firing receipt, restoration time, resolved receipt, private screenshot/evidence location and final state. Exclude secrets. Use the [existing test log](monitoring-tests.md).

### Rollback of the full outage-rule rollout

This procedure concerns rollback to the original nine-rule configuration. For an English-only rollback, restore the previous alerting files and recreate Grafana; no rule UIDs were added by the language update.

With a clean/reviewed working tree, restore the previous Prometheus/provisioning files:

```bash
git restore --source="$PREVIOUS_MONITORING_COMMIT" -- prometheus/prometheus.yml grafana/provisioning/alerting
```

Restoring files recreates the old rules but does not automatically remove the six new UIDs. **Before restarting Grafana**, create temporary deletion provisioning:

```bash
python3 - <<'PY'
import json
from pathlib import Path
uids = ['matchwise_node_exporter_unavailable', 'matchwise_prometheus_scrape_unavailable',
        'matchwise_supabase_metrics_unavailable', 'matchwise_supabase_database_down',
        'matchwise_loki_health_unavailable', 'matchwise_alloy_health_unavailable']
Path('grafana/provisioning/alerting/rollback-new-rules.json').write_text(
    json.dumps({'apiVersion': 1, 'deleteRules': [{'orgId': 1, 'uid': u} for u in uids]}),
    encoding='utf-8')
PY
```

Then validate and recreate:

```bash
sudo docker compose config --quiet
sudo docker compose run --rm --no-deps --entrypoint promtool prometheus \
  check config /etc/prometheus/prometheus.yml
sudo docker compose up -d --no-deps --force-recreate prometheus grafana
```

Verify the full active-rule inventory. After successful rollback, move the deletion file into the private state directory outside Git so it cannot delete new rules during a later rollout. Reconcile rollback working-tree differences before the next update. This configuration rollback does not restore volumes or collector state.

## Complete monitoring-host failure

Local Grafana cannot reliably notify when its own process or the entire Oracle VM stops. Local Node Exporter/Prometheus/Blackbox cross-checks do not solve this.

**Separate planned improvement:** send an outbound Oracle heartbeat to a service running with another provider and use an independent notification path. Define whether the heartbeat covers only the VM or also Grafana evaluation. Controlled full-VM and Grafana shutdown tests are needed. This protection is not implemented; exposing monitoring ports is not required.

## References and local validation

- [Grafana file provisioning](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/)
- [Grafana No Data/Error](https://grafana.com/docs/grafana/latest/alerting/fundamentals/alert-rule-evaluation/nodata-and-error-states/)
- [Prometheus range functions](https://prometheus.io/docs/prometheus/latest/querying/functions/)
- [Alloy HTTP health](https://grafana.com/docs/alloy/latest/reference/http/)
- [Loki HTTP API](https://grafana.com/docs/loki/latest/reference/loki-http-api/)
- [Supabase metric exposition](https://github.com/supabase/supabase-grafana/blob/main/metrics.md)
- [Grafana Telegram integration](https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/integrations/configure-telegram/)

Local validation requires PyYAML and the deployed-version promtool:

```bash
python3 scripts/validate-alerting.py --promtool /path/to/promtool
promtool check config --syntax-only prometheus/prometheus.yml
```

Syntax-only checking does not validate private password files or file_sd contents; use a full check on Oracle. The test script reads the actual provisioned A expressions and contacts neither external services nor Telegram.
