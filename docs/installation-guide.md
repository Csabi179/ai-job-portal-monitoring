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
