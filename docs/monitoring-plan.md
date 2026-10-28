# Core Monitoring Plan

Status: Implementation in progress.

## Core components

- Grafana OSS
- Prometheus
- Node Exporter
- Blackbox Exporter
- Structured backend logging (planned)

## Monitoring scope

- Oracle CPU, RAM, storage and network usage
- Frontend HTTP availability
- Backend health endpoint availability
- HTTP response duration
- Monitoring service health
- Alerts and incident detection

## Data retention

Target Prometheus retention: 7 days, maximum 2 GB.
Retention settings must be verified in the running Prometheus process.

Project shutdown: no later than 2026-12-15.

## Exclusions

No Tempo, distributed tracing, dedicated analytics database
or custom event collection API in the core implementation.

## Oracle infrastructure alerting

The following Grafana-managed alert rules are provisioned
from grafana/provisioning/alerting/infrastructure-alerts.json.

| Rule | Condition | Pending period |
|---|---|---|
| Low Available Memory | Available RAM below 10% | 10 minutes |
| Low Disk Space | Root filesystem available space below 15% | 10 minutes |
| Exporter DOWN | Node Exporter or Blackbox Exporter unreachable | 3 minutes |

Evaluation interval: 60 seconds.

Alert notifications are routed through the provisioned
AI Job Telegram contact point.

When the Prometheus query returns no data, Grafana uses the
NoData state. Query execution errors use the Error state.

These alerts monitor the Oracle host and monitoring exporters,
not the CPU or RAM usage of Render or Vercel.

An outage of the entire Oracle monitoring server cannot be
reliably notified by Grafana running on that same server.
