# MatchWise Monitoring — Architecture and Operations Guide

[Documentation index](README.md) · [English monitoring plan](monitoring-plan.en.md) · [English alerting plan](alerting-plan.en.md)

> November 10 follow-up: the operator supplied successful 12-rule rollout evidence and collector Telegram Firing/Resolved messages. See [TEST-10](monitoring-tests.md#test-10--oracle-rollout-and-collector-telegram-delivery-2026-11-10). Other per-rule tests remain pending. The later English notification update requires deployment.


> **Status:** Retrospective documentation updated November 10, 2026. Repository changes are distinct from live Oracle rollout.  
> **Main dashboard:** **MatchWise | Unified Monitoring** (Grafana UID: **matchwise-unified-overview**).  
> **Scope:** Oracle Cloud monitoring VM, independently deployed Render backend, Vercel frontend, Supabase, and backend HTTP logs.

## 1. System architecture

The monitoring stack runs on an Oracle Cloud Always Free Ubuntu 24.04 ARM64 VM (2 OCPU / 12 GB RAM). Docker Compose manages six containers:

| Component | Version in Compose | Role | Listener |
| --- | --- | --- | --- |
| Grafana | 13.2.1 | Dashboards and Telegram alerting | 127.0.0.1:3000 |
| Prometheus | 3.13.2 | Time-series storage and scrape scheduling | 127.0.0.1:9090 |
| Node Exporter | 1.11.1 | Oracle host metrics and collector health textfile | 127.0.0.1:9100 |
| Blackbox Exporter | 0.28.0 | HTTP probing of local, Render, and Vercel URLs | 127.0.0.1:9115 |
| Loki | 3.7.9 | Structured application log storage and LogQL | 127.0.0.1:3100 |
| Grafana Alloy | 1.21.2 | Read local JSONL/syslog and forward logs to Loki | 127.0.0.1:12345 (management) |

Monitoring dashboards use three data paths:

1. **Oracle:** Node Exporter → Prometheus → Grafana.
2. **Availability:** Blackbox Exporter → Prometheus → Grafana (Render backend and Vercel frontend).
3. **Application logs:** Render backend Pino JSON → Render Logs API over HTTPS → systemd Python collector → JSONL → Alloy → Loki → Grafana.

A fourth path watches the log collection process:

**systemd successful collector run → Node Exporter textfile → Prometheus → Grafana alerting → Telegram.**

The monitoring services are local-only. Access Grafana through an SSH tunnel, rather than opening port 3000 on the internet. For an SSH host you are authorized to access, forward local port 3000 to remote 127.0.0.1:3000.

## 2. Data sources, collection rates and limits

| Data | Metric or Loki selector | Collection cadence | Notes |
| --- | --- | --- | --- |
| Oracle CPU, RAM, disk, I/O, network, load, uptime | Node Exporter metrics (job=node_exporter) | Prometheus every 60 seconds | VM-level, not Render/Vercel host resources |
| Monitoring service health | Prometheus up and local Blackbox probe | Every 60 seconds | Shows exporter/probe health |
| Render backend availability | blackbox_render_backend / matchwise_backend | Every 30 minutes | The Render Free service may sleep; cold starts can dominate probe duration |
| Vercel frontend availability | blackbox_vercel_frontend / matchwise_frontend | Every 60 seconds | Verifies the deployed HTTP endpoint, not browser execution or JavaScript errors |
| HTTP request logs | Loki: job=matchwise_backend_render_api | Collector approximately every minute | Only approved Pino http_request fields; not an application metrics endpoint |
| Supabase PostgreSQL/Metrics API | up and pg_up plus database/host metrics | Every 60 seconds | Current project uvopvarvelpabhmrqaaw; see SUPABASE_METRICS.md |
| Collector heartbeat | matchwise_render_collector_last_success_timestamp_seconds | Updated on successful systemd oneshot runs | Measured by Node Exporter and scraped by Prometheus |

Prometheus configuration: **prometheus/prometheus.yml**; HTTP probe modules: **blackbox/blackbox.yml**. The Prometheus TSDB retention configuration is **7 days or 2 GB**. Loki retention is configured separately in **loki/loki-config.yaml**; it is not the same as JSONL log rotation.

**Important interpretation:** A Blackbox probe measures an end-to-end HTTP request including Render cold-start delay. The Pino responseTimeMs field measures server-side request processing and does **not** include the entire client-to-server round trip. A successful Render HTTP probe is the **latest sampled probe**, not a guarantee of continuous availability between 30-minute checks.

**Unavailable telemetry:** Render/Vercel platform CPU/RAM and frontend browser errors, Web Vitals, and frontend application logs are **not currently collected**. Do not read these as zero; they are outside monitoring coverage.

## 3. Dashboard inventory

Grafana dashboard provisioning is configured in **grafana/provisioning/dashboards/infrastructure.yml**:

- Provider: **ai-job-monitoring**
- Folder: **AI Job Portal**
- Watched directory: **grafana/provisioning/dashboards/json**
- Refresh: **every 30 seconds**
- UI edits to provisioned dashboards: **disabled** (allowUiUpdates=false)

| Dashboard | UID | Purpose |
| --- | --- | --- |
| **MatchWise | Unified Monitoring** | matchwise-unified-overview | Main operations landing page, including Supabase and auth counters |
| **AI Job Portal - Infrastructure Overview** | ai-job-infrastructure | Detailed Oracle host history |
| **AI Job Portal - Application Availability** | ai-job-availability | Detailed HTTP probe history |
| **MatchWise | Backend Logs** | matchwise-backend-logs | Deep dive into HTTP logs, status codes, P50/P95 and request IDs |

The unified dashboard covers system health, Oracle, Supabase, Render, Vercel, application/auth logs, collector status and diagnostics. Expand Diagnostics to inspect detailed HTTP logs and errors. Older seven-section/panel-count descriptions are historical.

Dashboard source-of-truth:

    grafana/provisioning/dashboards/json/matchwise-unified-monitoring.json

For changes, edit and version the JSON in Git, update the Oracle working tree, and let Grafana rescan the file. Do **not** maintain a second UI-edited copy with the same UID. The existing detailed dashboards remain for troubleshooting.

## 4. Alerting

The repository now contains **12 outage/monitoring-failure rules**. High RAM/disk usage and the old local Grafana test rule are explicitly deleted from the provisioned state. Performance and 4xx remain dashboard diagnostics.

The authoritative [alerting plan](alerting-plan.en.md) documents exact conditions, pending times, No Data/Error handling, Telegram grouping, deployment, rollback and unexecuted live tests. HTTP/database/collector rules keep their last state when evidence disappears. Separate monitoring rules report telemetry failures. The backend retains 30-minute probing and uses a 40-minute freshness window; one failed completed probe with 2-minute pending now suffices, replacing the earlier two-failure requirement.

The existing **AI Job Telegram** contact point and resolved messages are retained. A previous local test delivered Firing/Resolved; this does not verify each new rule. Full Oracle/Grafana failure cannot be reported reliably by the same host.

## 5. Collector, state, and log rotation

The Render API collector is **scripts/render-logs-poll.py**. Systemd runs it with a shared flock lock:

- **matchwise-render-logs.service** (oneshot)
- **matchwise-render-logs.timer** (approximately every minute)
- **matchwise-render-logrotate.service** (uses the same file lock)
- **matchwise-render-logrotate.timer** (hourly)

The collector keeps a private time cursor at **~/monitoring-private-state/render-api-state.json** and SQLite deduplication state at **~/monitoring-private-state/render-logs-seen.sqlite3**. JSONL output is **test-logs/render-backend.jsonl**, read by Alloy via the existing Docker bind mount. A successful collector run updates the textfile metric at **~/monitoring-exporter-metrics/matchwise_render_collector.prom**.

Log rotation uses **logrotate/matchwise-render-backend.conf**, with a **20 MB** threshold, up to **7 archives**, and an archive directory outside the repository: **~/monitoring-private-archives/**. The configured hourly schedule checks for rotation; it does not force a rotation every hour. Loki has its own independent retention.

Test evidence from October 30, 2026: a synthetic 120-message rotation test yielded **120 unique messages, 0 missing, 0 duplicates** in Loki. This is useful validation, not a blanket zero-data-loss guarantee.

## 6. Common operational checks

Run these on the Oracle VM from the monitoring repository:

    cd ~/ai-job-monitoring
    sudo docker compose config --quiet
    sudo docker compose ps
    sudo systemctl list-timers --all | grep matchwise-render
    sudo systemctl show matchwise-render-logs.service -p Result -p ExecMainStatus
    sudo journalctl -u matchwise-render-logs.service -n 30 --no-pager

Check local health and telemetry without printing secrets:

    curl -fsS http://127.0.0.1:3000/api/health
    curl -fsS http://127.0.0.1:12345/-/ready
    curl -fsS http://127.0.0.1:9100/metrics | grep -E '^(matchwise_render_collector_last_success_timestamp_seconds|node_textfile_scrape_error)'
    curl -fsSG http://127.0.0.1:9090/api/v1/query --data-urlencode 'query=max(time() - matchwise_render_collector_last_success_timestamp_seconds)'

Troubleshooting:

| Symptom | Check |
| --- | --- |
| Collector 401/403 | Render API token permissions, workspace/service membership; never paste tokens into logs or chat |
| Collector 429/5xx | Render rate limiting or API availability; inspect the last systemd result and journal |
| Collector success but no new Pino logs | No application traffic, wrong Render service, or missing structured logging |
| Collector alert fired | Check successful-run age, systemd timer/service, API credentials and Node Exporter metric |
| Grafana panel is No data | PromQL/LogQL selector, target reachability, elapsed time window, and correct datasource |
| Render shows long response time | Compare Blackbox duration (cold start + network) with Pino responseTimeMs (server-side) |
| Frontend shows HTTP 200 but app fails in browser | HTTP probing does not detect React/JavaScript runtime failures |
| Duplicate or missing logs | Inspect SQLite and JSONL state; preserve backups before attempting repairs |

Do not delete SQLite, cursor, logs, or Grafana volumes merely to clear a dashboard problem.

## 7. Current backend and future service migration

On November 9, the same Render service was switched to the team backend main branch while retaining URL and Service ID. See TEST-08. The following procedure applies to a future move to a different service, not a required repeat of that completed change.

**Both** the logging collector **and** HTTP availability target need updating for a different service. Changing the Render Service ID alone does **not** change the Blackbox Exporter target.

Prerequisites:

1. The team backend is deployed, its Render **Service ID**, **Workspace/Owner ID**, health endpoint URL and API access are known.
2. The running team backend emits compatible Pino JSON **http_request** entries (service identifier, reqId, route, statusCode, responseTimeMs).
3. The Render API key grants authorized log access to the team's deployment. The logging branch may still require review/merge/deployment.

Safe migration sequence on Oracle:

1. Stop **matchwise-render-logs.timer**, confirm the oneshot service is not still running, and keep the shared file lock in place.
2. Back up the private environment configuration and **render-api-state.json** to a restricted folder **outside Git**. Never show the Render API key in terminal output.
3. Edit **~/monitoring-private-secrets/render-logs.env**: set **RENDER_OWNER_ID**, **RENDER_SERVICE_ID**, and (if different) **RENDER_PINO_SERVICE**. Keep/replace **RENDER_API_KEY** only as permitted.
4. Archive and remove the **active cursor** only after taking a backup. Without the cursor, the collector starts from a limited recent window (currently 20 minutes); it does **not** backfill the full Render history.
5. Run **sudo systemctl start matchwise-render-logs.service**, inspect its exit status and journal, then restart **matchwise-render-logs.timer** only after success.
6. In **prometheus/prometheus.yml**, replace the **blackbox_render_backend** target URL with the team's actual **/api/health** URL, keeping the **service=matchwise_backend** label. Validate config, then force-recreate Prometheus to refresh single-file bind mounts and confirm the new target. Preserve its data volume.
7. The Loki **job=matchwise_backend_render_api** selector, collector alert, and unified dashboard remain stable. Both old and new service logs may appear together when a time range spans the transition. The new JSONL records include **renderServiceId**.

If the team also deploys a different Vercel frontend URL, update **blackbox_vercel_frontend** in **prometheus/prometheus.yml** separately, preserving **service=matchwise_frontend**. A browser-frontend deployment alone does not supply server CPU/RAM or JavaScript telemetry.

See **docs/RENDER_LOGGING_RUNBOOK.en.md** for the detailed English logging runbook (Hungarian original preserved).

## 8. Security, Git and handover

- Keep **.env**, Render API keys, Telegram bot token/chat ID, TLS keys, real JSONL logs, archives, SQLite and cursor files outside Git.
- Grafana/Prometheus/Loki/Alloy management listeners are bound to loopback on Oracle. Use SSH tunneling for operator access.
- Earlier experimental public syslog ingress was closed; the supported Render logging integration now pulls from Render Logs API via HTTPS.
- Render collector logs intentionally include a restricted Pino field allowlist; no bearer tokens, request bodies or raw URLs should be recorded.
- No infrastructure change should stop the independently running Ollama process.
- Keep existing three specialist dashboards as fallbacks while adopting Unified Monitoring for daily use.

To sync changes committed directly to GitHub on Oracle:

    cd ~/ai-job-monitoring
    git status --short
    git pull --ff-only
    sudo docker compose config --quiet

**Do not run git reset --hard** on the Oracle working tree. If Git reports local conflicts or untracked-file collisions, review them first.

## 9. Project verification and known limitations

Verified in the project: Oracle and HTTP availability measurements, Pino structured logs, Render Logs API collection, SQLite duplicate suppression, local file ingestion by Alloy, Grafana dashboard visualizations, Telegram test notification, and a healthy collector alert provisioned in Grafana.

Limitations: coarse 30-minute Render HTTP probing; Render Free sleeping; frontend HTTP-only probing; lack of Render/Vercel CPU/RAM and browser performance telemetry; collector API pagination cap; no automatic retry inside the Python collector; log rotation is not a proof of perfect delivery; Grafana/Prometheus outages reduce monitoring visibility.

For installation, test history and background planning, see **docs/installation-guide.md**, **docs/monitoring-tests.md**, and **docs/monitoring-plan.md**.
