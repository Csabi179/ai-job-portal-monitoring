# MatchWise monitoring plan

> **Pending update (November 18, 2026):** branch configuration now has sixteen permanent rules, thirty-five Service Comparison panels and one-minute backend probes (60s/15s/10s, three-minute freshness). The previously verified live deployment has fifteen rules; validation and rollout of this update are pending. [Validation and rollout](SECURITY_OVERVIEW_AND_FREQUENT_PROBES.md).

[Magyar változat](monitoring-plan.md) · [Documentation index](README.md)

## Purpose and responsibilities

Monitoring follows the Oracle host, Render backend, Vercel frontend, Supabase and log collection. The operator manages Render hosting, Oracle monitoring, log collection, dashboards, alerting and documentation. The team's application and database owners manage business features and database migrations.

Dashboards also show performance and capacity. Active notifications cover outages, monitoring failures and three new backend resource/security signals; exact conditions are in the [alerting plan](alerting-plan.en.md).

## Components and deployment locations

| Location | Component | Purpose |
|---|---|---|
| Oracle Cloud | Ubuntu ARM64 VM, 2 OCPU / 12 GB RAM | Monitoring host |
| Docker Compose | Prometheus 3.13.2; Grafana 13.2.1 | Metrics, dashboards and Grafana Alerting |
| Docker Compose | Node Exporter 1.11.1; Blackbox Exporter 0.28.0 | Host/textfile metrics and HTTP probes |
| Docker Compose | Loki 3.7.9; Alloy 1.21.2 | Log storage and forwarding |
| Docker Compose, public profile | Caddy 2.11.9 | Public HTTPS access to local Grafana |
| Oracle systemd | Separate Python log/resource collectors and logrotate, with service/timer pairs | Render Logs API, Render Metrics API and JSONL rotation |
| Render | matchwise-backend-monitoring-test.onrender.com | Team backend; main auto-deployment configured by the operator |
| Vercel | https://www.matchwise.tech/ | Frontend |
| Supabase | uvopvarvelpabhmrqaaw | PostgreSQL, Auth, PostgREST and Metrics API |
| Telegram | AI Job Telegram contact point | English Firing and Resolved messages to the team group |
| GitHub | Csabi179/ai-job-portal-monitoring | Configuration and documentation history |

Compose selects six services by default; the deployed HTTPS path also requires Caddy from the public profile. Render Service ID: `srv-dbh7b1nb9u1s73e6hpbg`. Verify the exact deployed backend commit separately; source availability does not prove deployment.

Editable architecture: [draw.io and SVG](architecture/README.en.md).

## Data sources and flows

1. Linux → Node Exporter → Prometheus → Grafana: CPU, memory, disk, network, load and uptime.
2. Blackbox → Prometheus → Grafana: backend `/api/health`, frontend home page, Loki `/ready` and Alloy `/-/healthy`.
3. Supabase Metrics API → Prometheus → Grafana: scrape health, `pg_up`, database, host and PostgREST metrics.
4. Pino stdout → Render Logs API → Python collector → deduplicated JSONL → Alloy → Loki → Grafana.
5. Successful collector run → heartbeat textfile → Node Exporter → Prometheus → Grafana Alerting.
6. Browser → HTTPS → Caddy → Grafana authentication and permissions.
7. Grafana Alerting → Telegram Bot API → the team's Telegram group.
8. Render Metrics API → separate Python resource collector → .prom file → Node Exporter → Prometheus → Grafana.

The collector retains only the configured service's `http_request` events and allowlisted fields: level, event, reqId, method, route, statusCode, responseTimeMs and errorCode, with Render identifiers and timestamps. Alloy uses the original Render event time. Routes are often templates without /api; bodies, CV contents, passwords and tokens are not collected fields.

## Collection cadence and windows

| Data | Frequency or window |
|---|---|
| Node Exporter, Blackbox self-metrics, Prometheus self-scrape | 60 s |
| Backend HTTP | 60 s; scrape timeout 15 s; prober timeout 10 s |
| Frontend HTTP | 60 s; scrape timeout 15 s; prober timeout 10 s |
| Supabase | 60 s; scrape timeout 30 s; file discovery 60 s |
| Loki and Alloy health probes | 60 s; scrape timeout 15 s |
| Log collector | OnBootSec=2min; OnUnitInactiveSec=1min; AccuracySec=10s |
| Render resource collector | OnBootSec=2min; OnUnitInactiveSec=2min; AccuracySec=5s; four API requests per run |
| Grafana rule evaluation | 1 minute |
| Backend HTTP alert freshness | 3 minutes; pending 2 minutes |
| Frontend HTTP alert freshness | 3 minutes; pending 2 minutes |
| Dashboard status cards | Backend 3 minutes; frontend 5 minutes in Unified, 3 minutes in Service Comparison |
| Rolling Pino P50/P95 | 15 minutes; endpoint-table P95 uses the full selected period |
| Unified dashboard refresh; provisioning file scan | 1 minute; 30 s |

The collector is scheduled relative to the previous run's completion. The timer tries again after a failed API request, but the Python program has no internal automatic HTTP retry. Successful empty collection can refresh the heartbeat; this alone does not prove Loki delivery.

## Dashboards and alerting

Main dashboard: **MatchWise | Unified Monitoring**, UID `matchwise-unified-overview`, repository version 8. Two introductory panels and 82 panels in nine groups make **84 panels**. Datasource UIDs: `prometheus`, `loki`.

Three specialist dashboards remain for operator use: Infrastructure Overview, Application Availability and Backend Logs. The six authentication counters show login, logout and registration outcomes, not active-user/session counts. The static latest-auth-test note was removed from the introductory panel; its evidence remains in the test log.

The original **12 outage/monitoring rules** are grouped into infrastructure-monitoring (3), monitoring-components (2), render-backend-monitoring (2), render-log-collector-monitoring (1), supabase-monitoring (2) and vercel-frontend-monitoring (2). The service-comparison-security group adds three rules: Render CPU >80% for 5 minutes, at least five non-health 5xx/5 minutes with a 2-minute pending period, and at least ten POST login 401/5 minutes with a 2-minute pending period. The 404 addition brings branch configuration to **16 permanent rules**; rollout of the new rule is pending. RAM/disk, P95, general 4xx and a quiet application are still not active alert conditions.

New dashboard: **MatchWise · Service Comparison**. See the [dashboard guide](SERVICE_COMPARISON_DASHBOARD.md) for freshness and comparison limits, and the [alert guide](SERVICE_COMPARISON_ALERTS.md) for the rolling-window example.

Telegram messages are English. Contact point UID: `ai_job_telegram`; the private Oracle `GRAFANA_TELEGRAM_CHAT_ID` selects the team group. Group wait 30 s, group interval 5 minutes, repeat interval 4 hours; resolved messages are enabled.

## Storage and access

- Prometheus: 7 days or 2 GB, whichever limit is reached first, configured in `prometheus/prometheus.yml`.
- Loki: 168 hours with compactor retention enabled.
- JSONL: `~/ai-job-monitoring/test-logs/render-backend.jsonl`; hourly size checks, 20 MB threshold and up to seven uncompressed archives.
- Named volumes: prometheus_data, grafana_data, loki_data, alloy_data, caddy_data and caddy_config.
- SQLite and cursor: `~/monitoring-private-state/`; preserve during updates.
- Secrets: Git-ignored `.env` and `~/monitoring-private-secrets/`; Supabase private files use a read-only Prometheus mount.
- Public URL: **https://grafana-r0cecq.duckdns.org/** through Caddy on TCP 80/443; Grafana port 3000 and internal monitoring endpoints remain on loopback.
- The team's shared Viewer account has dashboard access only to Unified Monitoring and no Grafana Admin rights; it receives no Oracle or SSH access.
- Users and ACLs are stored in Grafana's database; dashboard JSON does not automatically configure them.
- Dashboard permissions do not isolate datasource data: a Viewer can issue other queries to accessible datasources.
- Secure cookies require the HTTPS URL for browser login; SSH shell and local health queries remain available.

Procedure and rollback: [HTTPS access](GRAFANA_HTTPS_ACCESS.en.md). Persistent storage is not a backup; actual retention and recoverability require separate verification.

## CV and AI monitoring preparation

The main source archive supplied on November 15 contained CV upload and Cloudinary storage. A separate `feat-ajsp-4-cv-profile` branch implements profile generation using Cloudflare Workers AI `@cf/openai/gpt-oss-20b`.

The operator preconfigured `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` on Render. These are not Oracle monitoring settings; the database owner handles the required Supabase migration. This monitoring repository does not establish the merge or production deployment state.

Without backend changes, `/cv/upload` and `/cv/:id/profile` HTTP counts, status codes, total processing duration and reqId can be used. Separate AI duration, token usage and precise provider-error classification are unavailable; profile HTTP 503 does not establish a Cloudflare outage. No dedicated AI panel or AI alert is deployed.

## Verification and limitations

The [test log](monitoring-tests.md) separates dated measurements from operator confirmations. Recorded evidence covers 12-rule provisioning, collector and Node Exporter Firing/Resolved delivery, English notifications, HTTPS login, operator-confirmed Viewer access and the Telegram group switch. On November 18, all three new synthetic Firing/Resolved tests and cleanup were confirmed; the operator also tested the real login rule with ten failed logins. Individual live tests for the other ten original rules, 4-hour repetition and full infrastructure restoration are not established.

The pending one-minute backend sampling can still miss sub-minute outages; HTTP 200 is not a full business/browser test. Render CPU/RAM is now collected; Vercel host CPU/RAM, browser errors, Web Vitals and tracing are not collected. The 16 rules do not separately cover the complete public Caddy/DNS/TLS path.

The local Grafana cannot reliably notify during complete Oracle VM or Grafana failure; independent external checking is a future improvement. Collector success, Loki health and real log delivery are separate states. Missing data does not automatically mean zero errors or UP.

## Operations and change tracking

Configuration change → validation → GitHub commit → Oracle `git pull --ff-only` → apply the affected service → verify behavior. Do not bypass conflicts with `reset --hard`; do not delete volumes, SQLite or cursor state during routine maintenance.

Single-file bind-mount changes can require container recreation. Grafana scans dashboard JSON every 30 seconds; changed environment values require Grafana recreation. Oracle `.env` changes do not alter Render Environment settings. Planned project completion/shutdown: no later than December 15, 2026.

## November 18 deployment note

Work is versioned on feat/service-comparison. Oracle was updated using reviewed file copies; no main merge or live checkout switch is established. The installed resource collector is a separate copy at /usr/local/lib/matchwise/render-metrics-poll.py and must also be updated during future deployments. Viewer access to the new dashboard needs a separate check. See [implementation status](SERVICE_COMPARISON_PLAN.md).
