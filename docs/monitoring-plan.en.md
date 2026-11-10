# MatchWise – monitoring plan and implementation status

[Magyar változat](monitoring-plan.md) · [Documentation index](README.md)

Documented on **November 10, 2026**. This is a retrospective description of an implemented system, not a plan written before development. The initial review used repository commit `374f74eab098deccfd408887bbef5db314c83223`. Configuration and previously recorded evidence were available; the assistant did not directly access the running Oracle VM during that review.

**Subsequent operator verification, November 10:** commit `665d2d5` was applied on Oracle. The operator supplied successful readiness and metric checks, Grafana provisioning logs for 12 rules, and a screenshot showing all 12 provisioned rules with green status. A Telegram contact-point test and the collector rule's Firing and Resolved notifications were received. This does not establish individual delivery for the other 11 rules. The later English notification update still requires deployment and a message test. See [TEST-10](monitoring-tests.md#test-10--oracle-rollout-and-collector-telegram-delivery-2026-11-10).

## Purpose and responsibilities

Monitor the services of the university MatchWise job portal, the Oracle host, and monitoring itself. The operator is responsible for Render hosting, Oracle monitoring, log collection, dashboards, alerts and documentation. The team develops the business backend and frontend.

The dashboard also displays performance and capacity. Active notifications cover only outages and monitoring failures; see the [alerting plan](alerting-plan.en.md).

## Components and deployment locations

| Location | Component | Role |
|---|---|---|
| Oracle Cloud | Ubuntu 24.04 ARM64 VM; previously documented as 2 OCPU / 12 GB RAM | Monitoring host |
| Oracle Docker Compose | Prometheus 3.13.2; Grafana 13.2.1 | Metric storage; dashboards and Grafana Alerting |
| Oracle Docker Compose | Node Exporter 1.11.1; Blackbox Exporter 0.28.0 | Host metrics/textfile; HTTP probes |
| Oracle Docker Compose | Loki 3.7.9; Alloy 1.21.2 | Log storage; file ingestion and forwarding |
| Oracle systemd | Python collector and logrotate, each with a service/timer pair | Render Logs API collection and JSONL rotation |
| Render Free | `matchwise-backend-monitoring-test.onrender.com` | Team backend on the existing Render service |
| Vercel | `https://www.matchwise.tech/` | Frontend |
| Supabase | `uvopvarvelpabhmrqaaw` | PostgreSQL, Auth, PostgREST, Metrics API |
| Telegram | AI Job Telegram | Firing and recovery notifications |
| GitHub | Csabi179/ai-job-portal-monitoring | Configuration and documentation history |

Render Service ID: `srv-dbh7b1nb9u1s73e6hpbg`. Its name is historical: November 9 evidence records the team's backend main branch running on that same service. The exact deployed backend commit was not supplied. The local backend source snapshot is dated November 9; this documentation task did not recheck the backend repository's current main branch.

Editable architecture diagram: [draw.io and SVG](architecture/README.en.md). The diagram's planned AI provider and full frontend–backend connection are not treated as implemented without new deployment evidence.

## Data sources and paths

1. Node Exporter → Prometheus → Grafana: CPU, memory, disk, network, load, uptime and textfile health.
2. Blackbox → Prometheus → Grafana: backend `/api/health`, frontend home page, and the new Loki `/ready` and Alloy `/-/healthy` checks.
3. Supabase Metrics API → Prometheus → Grafana: scrape health, `pg_up`, database/host metrics and PostgREST pool metrics.
4. Pino JSON stdout → Render Logs API → Python collector → deduplicated JSONL → Alloy → Loki → Grafana.
5. Successful systemd oneshot → heartbeat textfile → Node Exporter → Prometheus → Grafana Alerting → Telegram.

The collector filters by `event=http_request` and the configured `service`. Important fields include reqId, method, route, statusCode and responseTimeMs, plus Render timestamps and identifiers. Alloy uses the original Render event time. Auth routes often appear without the /api prefix. Passwords, tokens, Authorization headers, CV contents and request bodies must not enter the log stream.

## Frequencies and windows

| Data | Frequency / window |
|---|---|
| Node Exporter, Blackbox self-metrics, Prometheus self-scrape | 60 s |
| Backend HTTP | 30 minutes; scrape timeout 110 s; prober timeout 100 s |
| Frontend HTTP | 60 s; scrape timeout 15 s; prober timeout 10 s |
| Supabase | 60 s; scrape timeout 30 s; file discovery refresh 60 s |
| New Loki/Alloy HTTP health probes | 60 s; scrape timeout 15 s |
| Collector | OnBootSec=2min; OnUnitInactiveSec=1min; AccuracySec=10s |
| Grafana rule evaluation | 1 minute |
| Backend alert freshness | 40 minutes; pending 2 minutes |
| Frontend alert freshness | 3 minutes; pending 2 minutes |
| Dashboard status cards | Backend 40 minutes; frontend 5 minutes |
| Rolling Pino P50/P95 | 15 minutes; endpoint-table P95 uses the full selected period |
| Dashboard refresh | Unified dashboard 1 minute; provisioning file scan 30 s |

Collector scheduling is relative to the end of the previous run, not an exact wall-clock minute. A successful API request with no new events also refreshes its heartbeat. This does not prove delivery to Loki.

## Dashboards and interpretation

Main view: **MatchWise | Unified Monitoring**, UID `matchwise-unified-overview`, repository version 8. Datasource UIDs: `prometheus`, `loki`. It covers host, Supabase, backend, frontend, Pino, authentication, collector and diagnostics. The three detailed Infrastructure, Application Availability and Backend Logs dashboards remain available. Earlier panel counts are historical, not a verified inventory of the current dashboard.

CPU/RAM/disk, response times, P95 and 4xx remain diagnostic information. The six auth counters track successful/rejected/invalid login, login 5xx, logout and registration. They cannot determine the number of active users or sessions. Registration may also sign in the new account automatically.

The proportion of successful samples is not guaranteed continuous uptime. One stored sample can appear at multiple graph points. Pino time is not the full external HTTP duration. Health traffic can distort aggregate application error rates and percentiles. Zero errors and missing logs are different states. The frontend dashboard's 5-minute window and alert's 3-minute window intentionally differ: alerting detects missing measurements earlier.

## Storage, retention and access

- Prometheus: configured for 7 days or 2 GB, whichever limit is reached first.
- Loki: configured for 168 hours with compactor retention enabled; independent of JSONL rotation.
- JSONL: `~/ai-job-monitoring/test-logs/render-backend.jsonl`; hourly size check, 20 MB threshold, up to seven uncompressed archives.
- Persistent named volumes: prometheus_data, grafana_data, loki_data and alloy_data. Persistence alone is not a backup.
- SQLite and cursor: `~/monitoring-private-state/`; preserve them during routine updates.
- Secrets: Git-ignored `.env` and `~/monitoring-private-secrets/`; never print key values or include them in commits.
- Supabase password/target files: prepared by the helper and mounted read-only into Prometheus.
- Host networking with loopback management endpoints; Grafana access through SSH tunneling. Changing the VM .env does not change Render Environment values.

Retention settings are configuration targets. Actual disk use, retention execution and recoverability need separate verification.

## Evidence and status

Detailed records: [monitoring-tests.md](monitoring-tests.md).

| Area | Recorded evidence | Limit |
|---|---|---|
| Monitoring baseline | October 28 endpoint/container tests | Earlier four-service stage |
| Telegram baseline | October 28 local test Firing and Resolved | Not delivery testing for all new rules |
| Log path, deduplication, rotation | October 30 tests; 120 unique synthetic messages | Not a general no-data-loss guarantee |
| Auth and log correlation | November 9 register/login/me/account/logout, expected 401 and two reqIds in Loki | Not frontend integration or continuous business testing |
| Supabase | November 9 HTTP 200, UP target with no lastError; November 10 up=1 and pg_up=1 | A point-in-time scrape/exporter observation |
| Outage rules | November 10 local validation and 37 PromQL scenarios; operator-provided 12-rule deployment evidence | Not individual delivery testing for every rule |
| Collector delivery | November 10 controlled timer interruption, Telegram Firing and Resolved | Measured notification timestamps and final timer/service output were not supplied |

## Limitations and planned improvements

The local Grafana cannot reliably notify when its process or the entire Oracle VM fails. Independent monitoring on another infrastructure is required. This is **planned**, not deployed protection. Do not expose internal monitoring ports for this purpose. An external heartbeat service or VM could detect a missing outbound heartbeat and use a separate notification path.

Backend sampling every 30 minutes can miss short outages; probes are not increased to keep the service awake. A healthy endpoint is not a full business-function test. Frontend HTTP 200 does not establish browser behavior or backend integration. The earlier demo-login observation is date-specific and was not rechecked here. Render/Vercel host CPU/RAM, browser errors/Web Vitals and tracing are not collected.

Collector health, Loki health and actual log delivery are three distinct questions. A quiet application does not trigger a missing-log alert. Local health endpoints cannot detect every ingestion/forwarding problem. An independent synthetic log-path test could be a future improvement.

## Operations and change tracking

The repository is the configuration source of truth. Change → local validation → GitHub commit → VM `git pull --ff-only` → apply per container → verify live behavior and record evidence. Do not use `reset --hard` to bypass conflicts. Do not delete volumes or collector state during routine updates.

Single-file bind mounts can require recreation of Prometheus and, when its configuration changes, Alloy. The outage-rule deployment affected Prometheus and Grafana; the later English-only notification update requires Grafana provisioning only. Exact deployment/rollback: [alerting plan](alerting-plan.en.md#deployment). The previously documented project shutdown/completion target is no later than December 15, 2026.
