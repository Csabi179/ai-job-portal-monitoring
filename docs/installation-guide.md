# Monitoring Installation Guide

## Environment

The OS/engine versions below are recorded installation observations, not a new live version inventory. Current container image pins are in `compose.yaml`.

- Oracle Cloud ARM64 VM
- Ubuntu 24.04.5 LTS
- 2 ARM OCPU
- Approximately 11 GiB RAM
- Docker Engine 29.9.2
- Docker Compose 5.6.1

## Docker installation

Docker was installed using the official Docker Ubuntu APT repository.

Installation steps:

1. Install ca-certificates and curl.
2. Download the official Docker GPG key.
3. Configure the Docker APT repository for Ubuntu Noble ARM64.
4. Update APT package lists.
5. Install Docker Engine, CLI, containerd, Buildx and Compose plugin.

Package installation command:

    sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

Official instructions:
https://docs.docker.com/engine/install/ubuntu/

## Docker verification

    sudo docker --version
    sudo docker compose version
    sudo systemctl is-active docker
    sudo docker run --rm hello-world

The hello-world ARM64 test completed successfully.

## Monitoring deployment

The base stack contains **six** services: Prometheus, Grafana, Node Exporter, Blackbox Exporter, Loki and Alloy. The deployed HTTPS setup adds Caddy through the `public` profile. The original four-container test was an earlier milestone.

**Important:** a fresh clone is not a complete recovery. Populate `.env` from `.env.example` securely; provision private paths for `../monitoring-private-tls`, `../monitoring-exporter-metrics`, `~/monitoring-private-secrets/render-logs.env`, `~/monitoring-private-state` (cursor, SQLite and lock), and `~/monitoring-private-archives`. Preserve permissions and never commit credentials or runtime logs.

From the project root:

    sudo docker compose config --quiet
    sudo docker compose pull
    sudo docker compose up -d
    sudo docker compose ps

For the existing public deployment, manage/include Caddy with `sudo docker compose --profile public up -d` and `sudo docker compose --profile public ps`. On a fresh host, complete the [HTTPS procedure](GRAFANA_HTTPS_ACCESS.en.md) before starting the public profile.
## Service verification

    curl -fsS http://127.0.0.1:9090/-/ready
    curl -fsS http://127.0.0.1:3000/api/health
    curl -fsS http://127.0.0.1:9100/metrics
    curl -fsS http://127.0.0.1:9115/metrics
    curl -fsS http://127.0.0.1:3100/ready
    curl -fsS http://127.0.0.1:12345/-/healthy
    sudo systemctl is-active matchwise-render-logs.timer
    sudo systemctl is-active matchwise-render-logrotate.timer

Node Exporter collector health:

    sudo systemctl show matchwise-render-logs.service -p Result -p ExecMainStatus
    curl -fsS http://127.0.0.1:9100/metrics | grep -E '^(matchwise_render_collector_last_success_timestamp_seconds|node_textfile_scrape_error)'

## Maintenance

    sudo docker compose logs --tail=50
    sudo docker stats --no-stream

Named Docker volumes store Grafana, Prometheus, Loki and Alloy data/positions, plus Caddy certificate/runtime state.
Do not remove volumes during routine maintenance.

## Access

Team access uses **https://grafana-r0cecq.duckdns.org/** through Caddy on TCP 80/443. Grafana port 3000, Prometheus and exporter endpoints stay on loopback. Secure cookies require HTTPS for normal browser login. The team Viewer account can open Unified Monitoring; the other dashboards remain for operator use. Users and permissions are stored in Grafana's database and need restoration/configuration separately from the dashboard JSON. Viewer datasource-query access is not limited to visible panels. See [the HTTPS runbook](GRAFANA_HTTPS_ACCESS.en.md).

## Notes

Initial four-container validation was successful on 2026-10-28. By 2026-10-30 the six-service stack, four provisioned dashboards, nine Grafana alert rules, automatic Render API collection, and the Unified Monitoring dashboard were in use. The local test alert delivered Firing and Resolved Telegram messages; do not infer that all nine alert rules were independently fired.

---

## Backup and Recovery Strategy

### Configuration

The monitoring configuration is versioned in GitHub. Repository visibility is not a security boundary: secrets and runtime data stay outside Git.

The following items are version-controlled:
- Docker Compose configuration
- Prometheus configuration
- Exporter configuration
- Grafana dashboards
- Grafana alerting rules
- Installation and monitoring documentation

### Secrets

The .env file is excluded from Git.

Grafana administrator credentials and Telegram bot credentials
must be stored securely outside the Git repository.

### Grafana persistent data

Grafana uses the named Docker volume:

    ai-job-monitoring_grafana_data

A verified backup was created on 2026-10-28.

Backup directory:

    ~/monitoring-private-backups

The backup was created while Grafana was stopped.
Only the Grafana container was restarted afterward.

### Recovery verification

A backup archive was successfully extracted into a temporary
Docker volume.

The grafana.db database file was verified.

This is an extraction test, not a complete application
restore test.

### Prometheus data

Prometheus metrics are retained for up to 7 days or 2 GiB.

Prometheus metrics, Loki log data, Alloy read positions and the Render collector's private state are not included in the Grafana volume backup.

### Disaster recovery

1. Restore the monitoring repository from GitHub.
2. Restore the required environment variables securely.
3. Install Docker and Docker Compose.
4. Restore the Grafana volume if historical Grafana data is needed; recover Prometheus/Loki/Alloy volumes separately if their history is required.
5. Restore the collector private environment file, cursor, SQLite database, textfile metric directory and other private mounts; install systemd service/timer units from `systemd/`.
6. Start Docker Compose and the two Render-related systemd timers.
7. Verify Prometheus targets, the four Grafana dashboards, 12 alert rules and collector heartbeat; restore/check folder and dashboard permissions for the Viewer account.
8. Restore/check Caddy volumes and the public .env settings, then follow the HTTPS runbook for DNS/firewall/TLS verification.
9. Verify English Telegram test delivery to the team group using the private destination setting. No deliberate production outage is needed for a contact-point test.

Store an encrypted backup copy outside the Oracle VM
to protect against complete server loss.
