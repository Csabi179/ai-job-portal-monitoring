# MatchWise — Monitoring Scope and Implementation Status

**Status (2026-10-30): Core monitoring implemented.** This document reflects the current configuration rather than an early roadmap.

## Deployed stack

Six Docker Compose services run on the Oracle Cloud ARM64 Ubuntu 24.04 host:

- **Grafana 13.2.1** — dashboards and Grafana-managed Telegram alerting
- **Prometheus 3.13.2** — Oracle metrics and HTTP probe results
- **Node Exporter 1.11.1** — VM metrics and collector-success textfile
- **Blackbox Exporter 0.28.0** — Render backend, Vercel frontend and local Grafana HTTP probes
- **Loki 3.7.9** — backend HTTP log storage and queries
- **Grafana Alloy 1.21.2** — JSONL ingestion and local-only syslog test listeners

The actual production-like log pipeline is **Pino JSON → Render Logs API (HTTPS) → systemd Python collector → JSONL → Alloy → Loki → Grafana**. The earlier experiment with Render Log Streams/TLS syslog was not adopted for external ingestion.

## Monitoring scope

| System | Data collected | Cadence |
| --- | --- | --- |
| Oracle VM | CPU, memory, filesystem, disk I/O, network, load, uptime | 60-second Prometheus scrape |
| Render backend | Sampled HTTP availability/status and total HTTP probe duration | Every 30 minutes |
| Vercel frontend | Sampled HTTP availability/status and probe duration | Every 60 seconds |
| Backend app | Pino `http_request` logs, 4xx/5xx, routes and responseTimeMs | Render Logs API poll about every minute |
| Collector | Last successful collection timestamp, textfile scrape errors | Updated after successful oneshot run, scraped every 60 seconds |

Render/Vercel host CPU/RAM, frontend browser errors/Web Vitals and distributed tracing are **not collected**. The Render Free instance can sleep between probes; an UP indicator only describes the latest observation.

## Retention and rotation

- **Prometheus:** configured for **7 days or 2 GB**, whichever limit is hit first (`prometheus/prometheus.yml`).
- **Loki:** configured with a **168-hour retention period** and compactor retention enabled (`loki/loki-config.yaml`).
- **Local backend JSONL:** rotate at **20 MB** during hourly checks; retain **seven uncompressed archives** in a private directory outside Git (`logrotate/matchwise-render-backend.conf`).

## Dashboards

Grafana file provisioning in `grafana/provisioning/dashboards/infrastructure.yml` refreshes every 30 seconds, with UI edits disabled:

- **MatchWise | Unified Monitoring** — main dashboard, 7 sections and 42 text/visualization panels.
- **AI Job Portal - Infrastructure Overview** — detailed VM panels.
- **AI Job Portal - Application Availability** — detailed endpoint availability.
- **MatchWise | Backend Logs** — detailed Pino logs and HTTP metrics.

## Alerting

**Nine** Grafana-managed provisioned rules, evaluated every minute:

| Scope | Rules |
| --- | --- |
| Local monitoring test | 1: local test endpoint DOWN |
| Oracle VM/exporters | 3: low available memory (<10%, pending 10m); low free root disk (<15%, pending 10m); exporter DOWN (pending 3m) |
| Render backend | 2: repeated HTTP probe failures; missing probe data |
| Vercel frontend | 2: repeated HTTP probe failures; missing probe data |
| Render logs collector | 1: last success older than 300 seconds, pending 2m |

Alert routing: `grafana/provisioning/alerting/telegram.yml` → **AI Job Telegram**. The local test rule's Firing and Resolved messages were observed; **not all nine rules have been individually fired**.

Grafana runs on the same VM it monitors, so it cannot reliably notify on complete Oracle VM failure.

## Current deployment targets and transition

The committed `prometheus/prometheus.yml` still probes the **independently deployed test Render backend and Vercel frontend**, not the team's final hosting.

The Render API collector uses `RENDER_OWNER_ID`, `RENDER_SERVICE_ID`, `RENDER_PINO_SERVICE` and `RENDER_API_KEY` from its private systemd environment file. Switching to the team's backend also requires changing the **Blackbox Render HTTP target URL**; optionally change the Vercel URL. Preserve the existing service/job labels so dashboards and alerts continue working.

Detailed operational instructions: [MONITORING_GUIDE.md](MONITORING_GUIDE.md), [RENDER_LOGGING_RUNBOOK.md](RENDER_LOGGING_RUNBOOK.md).

University project shutdown target: **no later than December 15, 2026**.

This document records repository configuration and verification evidence through October 30; it does not claim direct access to the Oracle VM's current running processes.
