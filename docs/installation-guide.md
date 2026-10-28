# Monitoring Installation Guide

## Environment

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

From the project root:

    sudo docker compose config --quiet
    sudo docker compose pull
    sudo docker compose up -d
    sudo docker compose ps

## Service verification

    curl -fsS http://127.0.0.1:9090/-/ready
    curl -fsS http://127.0.0.1:3000/api/health
    curl -fsS http://127.0.0.1:9100/metrics
    curl -fsS http://127.0.0.1:9115/metrics

## Maintenance

    sudo docker compose logs --tail=50
    sudo docker stats --no-stream

Persistent Docker volumes store Grafana and Prometheus data.
Do not remove volumes during routine maintenance.

## Access

Grafana is accessed over an SSH tunnel.
Public Grafana, Prometheus and exporter ports are not required.

## Notes

Initial validation was successful on 2026-10-28.
Dashboard provisioning and alerting verification are pending.

---

## Backup and Recovery Strategy

### Configuration

The monitoring configuration is stored in a private GitHub
repository.

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

Prometheus historical metrics are not included in the
Grafana backup.

### Disaster recovery

1. Restore the monitoring repository from GitHub.
2. Restore the required environment variables securely.
3. Install Docker and Docker Compose.
4. Restore the Grafana volume if historical Grafana data is needed.
5. Start the monitoring stack.
6. Verify Prometheus targets, Grafana dashboards and alert rules.
7. Test the Telegram notification channel.

Store an encrypted backup copy outside the Oracle VM
to protect against complete server loss.
