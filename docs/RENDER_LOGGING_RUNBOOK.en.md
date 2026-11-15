# MatchWise – Render Backend Logging Runbook

[Magyar változat](RENDER_LOGGING_RUNBOOK.md) · [Documentation index](README.md)

Reviewed November 16, 2026. English notifications and team-group routing are deployed according to recorded operator evidence; historical tests are kept in the test log.

## Overview

The MatchWise backend produces structured Pino JSON logs.

Data path:

Render Backend → Render Logs API (HTTPS) → Oracle Cloud Python collector → JSONL log file → Grafana Alloy → Loki → Grafana Backend Logs dashboard.

Collector monitoring is separate:

Python collector → Node Exporter Textfile Collector → Prometheus → Grafana Alerting → Telegram.

## Infrastructure

- Oracle Cloud Ubuntu VM.
- Docker Compose: Grafana, Loki, Alloy, Prometheus and Node Exporter; Blackbox Exporter provides HTTP probes.
- Render Logs API.
- Python 3 and SQLite.
- systemd services and timers.

## Automatic log collection

| Item | Name or path |
|---|---|
| Service | `matchwise-render-logs.service` |
| Timer | `matchwise-render-logs.timer` |
| Program | `scripts/render-logs-poll.py` |
| Private deduplication database | `/home/ubuntu/monitoring-private-state/render-logs-seen.sqlite3` |
| Time cursor | `/home/ubuntu/monitoring-private-state/render-api-state.json` |
| Active log file | `test-logs/render-backend.jsonl` |

The collector runs approximately every minute and uses SQLite for deduplication. Private state files and real logs are not uploaded to GitHub.

## Log rotation

Service: `matchwise-render-logrotate.service`. Timer: `matchwise-render-logrotate.timer`.

Logrotate checks file size hourly. It uses a 20 MB threshold, keeps up to seven archives, shares a flock lock with the Python collector, and stores archives outside the Git repository at `/home/ubuntu/monitoring-private-archives/`.

## Grafana

Dashboard: **AI Job Portal / MatchWise | Backend Logs**. UID: `matchwise-backend-logs`. Loki job label: `matchwise_backend_render_api`.

The dashboard shows HTTP requests/errors, error rate, backend P50/P95 response times, routes and logs. `responseTimeMs` is application processing time, not the full network response time.

## Unified monitoring dashboard

Main overview: **AI Job Portal / MatchWise | Unified Monitoring**, UID `matchwise-unified-overview`.

Backend Logs remains available for detailed troubleshooting. The overview combines Oracle VM, Render/Vercel HTTP probes, Pino HTTP logs, collector status and Supabase monitoring. Render/Vercel host CPU/RAM and frontend browser errors are not collected.

## Checking collector health

```bash
sudo systemctl is-active matchwise-render-logs.timer
sudo systemctl show matchwise-render-logs.service -p Result -p ExecMainStatus
sudo journalctl -u matchwise-render-logs.service -n 30 --no-pager
```

Prometheus metric: `matchwise_render_collector_last_success_timestamp_seconds`.

English alert title: **MatchWise | Render log collector | Monitoring failure**; stable UID: `matchwise_render_collector_stale`.

The rule detects more than 300 seconds since the last successful request, followed by 2 minutes pending. Missing heartbeat/textfile status or a textfile processing error is also a condition, provided Node Exporter is available. Node Exporter absence has its own rule; the collector retains its last state. Absence of application traffic is not an alert condition.

Notification destination: **AI Job Telegram** contact point → the team Telegram group selected by the private `GRAFANA_TELEGRAM_CHAT_ID`.

Collector and Node Exporter Firing/Resolved delivery are evidenced, including English Node Exporter notifications. The operator confirmed the team-group switch. These do not verify all 12 rules individually. See [the alerting plan](alerting-plan.en.md), [TEST-11](monitoring-tests.md#test-11-node-exporter-delivery) and [TEST-13](monitoring-tests.md#test-13-telegram-group-delivery).

## Moving to another team Render service

On November 9, the existing Render service was switched to the team's repository main branch without changing URL or Service ID. Do not repeat that completed change. The following procedure applies to a future move to a different service. Do not reset state during routine updates.

Prerequisites:

- The team backend is running on Render.
- The Render API key can read the relevant service's logs.
- The backend emits structured Pino `http_request` logs containing reqId, route, statusCode and responseTimeMs.

1. Stop the automatic collection timer:

   ```bash
   sudo systemctl stop matchwise-render-logs.timer
   ```

2. Verify no collection is in progress:

   ```bash
   sudo systemctl is-active matchwise-render-logs.service
   ```

   Wait until the service is inactive before proceeding. Inactive is normal for a completed Type=oneshot service.

3. Back up the private configuration and current time cursor.

4. Edit the private configuration:

   ```bash
   nano /home/ubuntu/monitoring-private-secrets/render-logs.env
   ```

   Required settings:

   ```text
   RENDER_OWNER_ID=<team Workspace ID>
   RENDER_SERVICE_ID=<team Service ID>
   RENDER_PINO_SERVICE=job-portal-backend
   ```

   Keep the existing RENDER_API_KEY only if it is authorized for the new service.

5. Move the old time cursor into a private backup. The new service's initial query then uses the preceding 20-minute window. This is a deliberate service migration step, not routine cleanup. Preserve SQLite deduplication state.

6. Run the service once:

   ```bash
   sudo systemctl start matchwise-render-logs.service
   ```

7. After a successful run, restart the timer:

   ```bash
   sudo systemctl start matchwise-render-logs.timer
   ```

8. Update backend HTTP monitoring **separately**. Change the `blackbox_render_backend` target in `prometheus/prometheus.yml` to the actual health URL, retaining `service: matchwise_backend`. Validate and recreate Prometheus as documented in the alerting plan, preserving its data volume; verify the active target.

9. If the frontend also moves, update `blackbox_vercel_frontend` separately while keeping `service: matchwise_frontend`.

The Loki job label and dashboards can remain unchanged if the new backend uses compatible Pino fields. The initial query does not import the new service's entire log history. Old and new backend logs can overlap in a selected dashboard time range.

## Troubleshooting

| Symptom | Action |
|---|---|
| 401 Unauthorized | Check the Render API key and its access |
| 403 Forbidden | Check workspace and service permissions |
| 429 Too Many Requests | Check Render rate limiting, the next run and systemd journal |
| 500 / 503 | Possible temporary Render API issue; a failed run does not update the success timestamp |
| No new logs, collector succeeds | The application may be quiet, or compatible Pino logging may be missing; collector success does not prove application logging |
| No data in Grafana | Check Alloy, Loki, Grafana and the Loki job selector |
| SQLite error | Back up first; do not delete the database or cursor |

## Security

- Keep the Render API key outside the repository.
- Do not commit private keys or real logs.
- Grafana and internal monitoring APIs listen on loopback; authenticated team access reaches Grafana through Caddy HTTPS.
- Earlier public syslog ingress is not enabled.
- Collection uses HTTPS.
- The Python collector stores only allowlisted Pino fields.

## Legacy diagnostic helper — important

`scripts/render-logs-once.py` is an early **manual test helper** with a fixed test Service ID. It does **not** use the production collector's SQLite identity handling, time cursor or shared flock lock. Do not run it against the active `test-logs/render-backend.jsonl` alongside automatic collection: this can cause duplicate records and inconsistent state.

The production collector is exclusively `scripts/render-logs-poll.py`, started through `matchwise-render-logs.service`.

## Known limitations

- No automatic HTTP retry inside the collector.
- Pagination has an upper processing limit.
- Loki retention differs from JSONL archive retention.
- Collector health does not check Pino event contents or prove Loki delivery.
- Logrotate/Alloy cooperation has been tested, but there is no general guarantee of lossless delivery.

## GitHub

Repository: `Csabi179/ai-job-portal-monitoring`.

GitHub stores configurations, dashboards, alert rules and documentation. Real logs, SQLite databases and secret keys are not repository content.

## Render API read-timeout handling

The Python API request timeout is 30 seconds. A failed run does not refresh the success metric; the systemd timer tries again later. November 11 journal output showed repeated read timeouts followed by successful collection and heartbeat refresh ([TEST-15](monitoring-tests.md#test-15-collector-timeout-recovery)). A fast unauthenticated HTTP 401 proves API reachability, not authenticated log retrieval. Do not automatically increase the alert threshold or delete SQLite/cursor state.

## CV and AI logs

The existing collector retains only the configured service's `http_request` events and allowlisted fields. A new endpoint's HTTP events require no collector change if the deployed backend keeps the logging format. Separate AI events do not pass the current filter. Available data and limitations for the profile feature are in [the monitoring plan](monitoring-plan.en.md#cv-and-ai-monitoring-preparation).
