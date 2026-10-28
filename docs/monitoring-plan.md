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
