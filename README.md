# MatchWise — AI Job Portal Monitoring

## Frontend/backend request correlation — update prepared November 21, 2026

The receiver now accepts the merged frontend's **schema v2** (`requests` plus
`dropped_requests`) alongside legacy schema v1 aggregates. Its implementation
version metric is **3**. Request IDs stay in bounded JSONL/Loki records, never
Prometheus or Loki stream labels. Existing aggregate counts are not incremented
again from request details.

New HU/English **Request Correlation** dashboards compare frontend `request_id`
with backend `reqId`, show both durations and statuses, and retain slow/failed
and ID-less browser requests. The correlation table keeps browser-reported rows
only; both sides exclude `/health` and `/api/health` (including trailing slashes).
Health/UptimeRobot traffic is not application request traffic.

**Operator-verified on Oracle on November 21:** receiver v3, healthy Alloy with
dynamic file discovery, a real frontend/backend ID match in Loki, and a populated
English Grafana table including HTTP 503 responses. See the
[request correlation deployment and verification guide](docs/REQUEST_CORRELATION.md).
The commands below describe a clean-checkout installation. The operator's
existing Oracle checkout contains older local configuration changes, so this
rollout used pinned release directories and targeted file updates instead of a
blanket pull or the clean-checkout installer. Preserve that distinction for
future updates. For a clean checkout:

```bash
cd ~/ai-job-monitoring
bash scripts/install-request-correlation.sh
python3 scripts/verify-request-correlation.py
```

The verifier requires a real browser request, its 60-second telemetry report and
the corresponding backend log to have arrived. Installation alone is not proof
of end-to-end delivery. No frontend/backend deployment or firewall change is
performed by the installer.

> **Current deployment — 2026-11-19:** The operator confirmed all supplied changes were already applied on Oracle. Monitoring was merged into `main` (`10f43d1`); no reinstallation is required because of that merge. [Current status](docs/DEPLOYMENT_STATUS.md). Earlier rollout entries are historical; commands are retained for future updates or recovery.

DevOps monitoring for the university AI-assisted job portal project.

## Main dashboard

The operator-confirmed service-grouped redesign is installed in both languages. For future updates or recovery, use the [pinned Oracle installer with backup and rollback](docs/SERVICE_DASHBOARDS_INSTALLATION.md). Hungarian dashboard names retain the `HU` suffix; English copies have no suffix. Existing dashboard UIDs and bookmarks are preserved.

**MatchWise | Unified Monitoring** (Grafana UID: `matchwise-unified-overview`) is the default operations view. It combines:

- Oracle Cloud VM: CPU, RAM, filesystem, disk I/O, network traffic, uptime and system load.
- Render backend: HTTP status, latest probe, response time and availability history.
- Vercel frontend: HTTP status, availability and response time (no host CPU/RAM metrics).
- Backend application: Pino HTTP requests, 4xx/5xx errors, error rate, P50/P95, routes and searchable logs.
- Supabase database: scrape/reachability health, CPU/RAM, storage, connection capacity, transactions, cache, PostgREST pool pressure and disk I/O. See [Supabase metrics setup](docs/SUPABASE_METRICS.md).
- Render log collector: latest successful collection and Node Exporter textfile scrape health.
- Expandable diagnostics for detailed HTTP logs.

Dashboard JSON: `grafana/provisioning/dashboards/json/matchwise-unified-monitoring.json`. Since the service-grouped redesign the dashboard has one section per service (Frontend, Backend, Database, Oracle, log pipeline), each opening with the same KPI strips; see [Service-grouped dashboards](docs/SERVICE_DASHBOARDS_REDESIGN.md).

The original dedicated Infrastructure, Application Availability and Backend Logs dashboards are retained.

## Service comparison and security signals

**MatchWise · Service Comparison** (UID `matchwise-service-comparison`) places Render, Supabase, Vercel and Oracle side by side with identical panels, fixed service colours and shared units (scorecard, availability, load, errors, security signals). Render CPU/RAM are collected through its Metrics API by a separate Python/systemd collector; Vercel host CPU/RAM are not collected.

The first three added rules cover high Render CPU (>80% for 5 minutes), at least five non-health 5xx responses in five minutes (2-minute pending), and at least ten rejected POST logins in five minutes (2-minute pending). The login counter covers all users together. Existing events can keep the rolling-window condition true without further failed attempts.

- [Resource collector and installation (HU/EN)](docs/RENDER_METRICS_COLLECTOR.md)
- [Comparison dashboard (HU/EN)](docs/SERVICE_COMPARISON_DASHBOARD.md)
- [Alert behavior and timing examples (HU/EN)](docs/SERVICE_COMPARISON_ALERTS.md)
- [Controlled test and cleanup (HU/EN)](docs/SERVICE_COMPARISON_ALERT_TEST.md)
- [Implementation and deployment status (HU/EN)](docs/SERVICE_COMPARISON_PLAN.md)

November 18 evidence: resource ingestion/timer and dashboard confirmed; all three synthetic tests delivered firing/resolved to Telegram; test cleanup confirmed by the operator. The operator also reported a successful real ten-failed-login test and supplied the production alert text. Viewer access to this new dashboard remains unverified. The changes were applied on Oracle with the supplied helpers and are now merged into `main`. The operator confirmed all supplied updates were run as they were delivered; this merge requires no additional deployment.

## Stack and ingestion

- **Docker Compose:** six base services (Grafana, Prometheus, Node Exporter, Blackbox Exporter, Loki and Alloy), plus deployed Caddy in the opt-in `public` profile.
- **Render logs:** Pino JSON → Render Logs API → Python systemd collector → deduplicated JSONL → Alloy → Loki.
- **Metrics:** Node Exporter and Blackbox Exporter → Prometheus → Grafana.
- **Alerting:** 16 permanent English rules in the merged configuration: 12 outage/monitoring-failure rules plus four backend resource/security signals, with Firing/Resolved notifications sent to the team's Telegram group. Collector and Node Exporter delivery were verified; the other ten rules have not been individually fired live. See the [alerting plan](docs/alerting-plan.en.md).
- **Retention:** Prometheus 7 days or 2 GB; logrotate rotates the local JSONL at 20 MB with seven archives. Loki retention is separate.

Oracle VM: Ubuntu 24.04 on ARM64 (Always Free). Internal monitoring web services bind to loopback. Team access uses Caddy HTTPS at https://grafana-r0cecq.duckdns.org/ with Grafana authentication; no Oracle or SSH access is granted to teammates.

## Installation and operations

Start here: **[Monitoring architecture and operations guide](docs/MONITORING_GUIDE.md)**.

Additional documentation:

- [Documentation index / Dokumentációjegyzék (English and Hungarian)](docs/README.md)

- [Editable stack and data-flow diagram (draw.io + SVG)](docs/architecture/README.en.md)

- [Render backend logging and migration runbook](docs/RENDER_LOGGING_RUNBOOK.en.md)
- [Installation guide](docs/installation-guide.md)
- [Monitoring tests](docs/monitoring-tests.md)
- [Monitoring plan](docs/monitoring-plan.en.md)
- [Alerting plan, deployment and tests](docs/alerting-plan.en.md)

Basic operations on Oracle:

```bash
cd ~/ai-job-monitoring
sudo docker compose config --quiet
sudo docker compose ps
sudo systemctl list-timers --all | grep matchwise-render
```

For future repository maintenance only (not required after the completed merge):

```bash
cd ~/ai-job-monitoring
git status --short --branch
```

The existing Oracle checkout has locally applied files. Do not run a pull/reset merely to match GitHub after this merge. For a future runtime change, review local modifications and use the guarded update procedure; stop on unknown changes. Never discard working files or persistent state.

## Backend migration

On November 9, the existing Render service was switched to the team's backend repository main branch. Its URL and Service ID were retained. Direct auth and log-delivery checks are recorded in the test log. Future service changes require updating the collector and HTTP target separately; see the operations guide. HTTP 200 on the frontend does not establish frontend–backend integration.

## Security and limits

Never commit `.env`, Render API keys, Telegram tokens, TLS private keys, SQLite state, real backend logs or archives. Render CPU/RAM telemetry is collected through its Metrics API. Vercel host CPU/RAM and frontend browser-performance data are not collected. The applied configuration samples Render availability every minute, so the latest UP result is not a continuous-uptime guarantee.

Project target completion/shutdown: no later than **December 15, 2026**.

## HTTPS team access

Caddy is deployed from the **public** Compose profile. The operator supplied successful certificate/health output and confirmed external browser login. The shared Viewer account has dashboard access only to **MatchWise | Unified Monitoring**, with no Grafana Admin rights. The other three dashboards remain for operator use. See [TEST-14](docs/monitoring-tests.md#test-14-https-viewer-access).

Users and folder/dashboard permissions live in the Grafana database and must be restored or configured separately from dashboard JSON. Viewer datasource-query access is broader than dashboard visibility; this is not datasource-level isolation.

Use the [English HTTPS runbook](docs/GRAFANA_HTTPS_ACCESS.en.md) or [Hungarian edition](docs/GRAFANA_HTTPS_ACCESS.md) for repeatable setup and rollback. The private Oracle .env holds public URL/secure-cookie and Telegram group settings; real values are not committed. Use `sudo docker compose --profile public ps` to include Caddy in status checks.

## CV and AI preparation

The operator reviewed November 15 main/feature-branch source archives and preconfigured the two Cloudflare variables on Render. The feature uses Cloudinary CV storage and Cloudflare Workers AI for profile extraction. This is preparation, not evidence that the feature is merged or deployed. Existing HTTP logs can show endpoint counts, statuses and total processing duration; separate AI latency, token usage and provider-specific errors are unavailable. No dedicated AI panels or rules have been added. See the [monitoring plan](docs/monitoring-plan.en.md#cv-and-ai-monitoring-preparation).

Security additions and the new cadence are described in [Security overview and frequent probes](docs/SECURITY_OVERVIEW_AND_FREQUENT_PROBES.md). The existing three synthetic tests remain a dated fifteen-rule deployment test; the new 404 rule and cadence still need rollout verification.

## Reusable test programs

[Repeatable test catalog (HU/EN)](docs/testing/README.md) lists the versioned real 404 check, synthetic alert lifecycle test, query preflight and local validation tools. The operator confirmed the real 404 test completed successfully. These are functional monitoring checks, not proof of DDoS resistance. Future runs should record their own source commit and results; temporary /tmp files need not survive.
