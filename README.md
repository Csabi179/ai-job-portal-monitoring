# MatchWise — AI Job Portal Monitoring

DevOps monitoring for the university AI-assisted job portal project.

## Main dashboard

**MatchWise | Unified Monitoring** (Grafana UID: `matchwise-unified-overview`) is the default operations view. It combines:

- Oracle Cloud VM: CPU, RAM, filesystem, disk I/O, network traffic, uptime and system load.
- Render backend: HTTP status, latest probe, response time and availability history.
- Vercel frontend: HTTP status, availability and response time (no host CPU/RAM metrics).
- Backend application: Pino HTTP requests, 4xx/5xx errors, error rate, P50/P95, routes and searchable logs.
- Supabase database: scrape/reachability health, CPU/RAM, storage, connection capacity, transactions, cache, PostgREST pool pressure and disk I/O. See [Supabase metrics setup](docs/SUPABASE_METRICS.md).
- Render log collector: latest successful collection and Node Exporter textfile scrape health.
- Expandable diagnostics for detailed HTTP logs.

Dashboard JSON: `grafana/provisioning/dashboards/json/matchwise-unified-monitoring.json`.

The original dedicated Infrastructure, Application Availability and Backend Logs dashboards are retained.

## Stack and ingestion

- **Docker Compose:** Grafana, Prometheus, Node Exporter, Blackbox Exporter, Loki and Grafana Alloy.
- **Render logs:** Pino JSON → Render Logs API → Python systemd collector → deduplicated JSONL → Alloy → Loki.
- **Metrics:** Node Exporter and Blackbox Exporter → Prometheus → Grafana.
- **Alerting:** 12 outage/monitoring-failure rules in the repository; existing Telegram routing and resolved notifications retained. Oracle rollout and per-rule delivery tests are pending; see the [alerting plan](docs/alerting-plan.md).
- **Retention:** Prometheus 7 days or 2 GB; logrotate rotates the local JSONL at 20 MB with seven archives. Loki retention is separate.

Oracle VM: Ubuntu 24.04 on ARM64 (Always Free). All monitoring web services are bound to loopback and are intended to be reached through an SSH tunnel.

## Installation and operations

Start here: **[Monitoring architecture and operations guide](docs/MONITORING_GUIDE.md)**.

Additional documentation:

- [Editable stack and data-flow diagram (draw.io + SVG)](docs/architecture/README.md)

- [Render backend logging and migration runbook](docs/RENDER_LOGGING_RUNBOOK.md)
- [Installation guide](docs/installation-guide.md)
- [Monitoring tests](docs/monitoring-tests.md)
- [Monitoring plan](docs/monitoring-plan.md)
- [Outage-only alerting plan, deployment and tests](docs/alerting-plan.md)

Basic operations on Oracle:

```bash
cd ~/ai-job-monitoring
sudo docker compose config --quiet
sudo docker compose ps
sudo systemctl list-timers --all | grep matchwise-render
```

To get new GitHub commits on the VM:

```bash
cd ~/ai-job-monitoring
git status --short
git pull --ff-only
```

If `git pull --ff-only` reports a conflict or untracked-file collision, **stop and inspect the local files**. Do not use `git reset --hard`.

## Backend migration

On November 9, the existing Render service was switched to the team's backend repository main branch. Its URL and Service ID were retained. Direct auth and log-delivery checks are recorded in the test log. Future service changes require updating the collector and HTTP target separately; see the operations guide. HTTP 200 on the frontend does not establish frontend–backend integration.

## Security and limits

Never commit `.env`, Render API keys, Telegram tokens, TLS private keys, SQLite state, real backend logs or archives. No Render/Vercel host CPU/RAM telemetry or frontend browser-performance data is currently collected. Render availability is sampled every 30 minutes, so the latest UP result is not a continuous-uptime guarantee.

Project target completion/shutdown: no later than **December 15, 2026**.
