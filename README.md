# AI Job Portal - Monitoring

DevOps monitoring system for the AI Job Portal university project.

## Scope

- Infrastructure monitoring
- Frontend and backend availability
- HTTP response times
- Backend logging
- Grafana dashboards
- Alerting
- Monitoring verification and documentation

## Technology stack

- Docker Engine and Docker Compose
- Prometheus
- Grafana OSS
- Node Exporter
- Blackbox Exporter

## Environment

Initial hosting: Oracle Cloud Ubuntu 24.04 ARM64.

Verified on 2026-10-28:
- Docker Engine 29.9.2
- Docker Compose 5.6.1
- Four monitoring containers running
- Grafana health endpoint responding
- Prometheus ready
- Node Exporter and Blackbox Exporter responding

## Installation

See docs/installation-guide.md.

## Configuration

1. Copy .env.example to .env.
2. Set GRAFANA_ADMIN_PASSWORD to a strong secret.
3. Validate the Docker Compose configuration.
4. Start the monitoring services.

Commands:

    sudo docker compose config --quiet
    sudo docker compose pull
    sudo docker compose up -d
    sudo docker compose ps

## Security

Do not commit .env, credentials, private keys or runtime data.

Monitoring interfaces are intended to be accessible through
an SSH tunnel, not directly from the public internet.

## Documentation

- docs/monitoring-plan.md
- docs/installation-guide.md
- docs/monitoring-tests.md

## Project lifetime

Target completion: as soon as practical.
Expected shutdown: no later than 2026-12-15.
