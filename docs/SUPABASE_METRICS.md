# Supabase metrics on the Oracle monitoring VM

The operator verified HTTP 200 and Prometheus-format metrics from the hosted project on 2026-11-09. Automated Prometheus collection still requires the deployment and checks below.

## Configuration

The existing repository-local `.env` is the source for `SUPABASE_URL` and `SUPABASE_SECRET_KEY`. It is ignored by Git and should have mode 600. The helper reads these two variables as literal single-line values, optionally quoted, without executing the file or expanding shell variables. Other environment settings are ignored by the helper. Render environment variables are maintained separately.

`scripts/prepare-supabase-metrics.py` creates two private files under `../monitoring-private-secrets/prometheus/`. One holds the API key, the other supplies the scrape target derived from the URL. Files are atomically replaced with mode 400 and owned by the running Prometheus UID. The directory has mode 500 and the same owner. The Compose bind mount is read-only and requires this directory to exist.

The `supabase` job uses HTTPS, Basic Auth with the documented username `username`, and a password-file reference. It scrapes every 60 seconds with a 30-second timeout. The project target is loaded through file-based service discovery. The secret value stays outside the repository.

## First deployment

Run on Oracle from the monitoring repository. The current Prometheus container must be running so its actual UID can be determined.

```bash
cd ~/ai-job-monitoring
git status --short
git pull --ff-only

PROMETHEUS_READER_UID=$(sudo docker exec monitoring-prometheus id -u)
sudo python3 scripts/prepare-supabase-metrics.py \
  --reader-uid "$PROMETHEUS_READER_UID"

sudo docker compose config --quiet
sudo docker compose run --rm --no-deps --entrypoint promtool prometheus \
  check config /etc/prometheus/prometheus.yml
```

Proceed only if preparation and validation succeeded. The one-off promtool container checks the new host configuration and private directory through the same mounts as Prometheus.

```bash
sudo docker compose up -d --no-deps --force-recreate prometheus
sudo docker compose ps prometheus
```

Recreation causes a brief Prometheus interruption. The named Prometheus data volume is reused. Wait at least 60 seconds, then query:

```bash
curl -fsS -G http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="supabase"}' | python3 -m json.tool
```

Expect `service="matchwise_database"` and a sample value of `"1"`. To inspect the collected metric inventory:

```bash
curl -fsS -G http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=count by (__name__) ({job="supabase"})' \
  | python3 -m json.tool
```

In Grafana Explore, select Prometheus and run `up{job="supabase"}`. Supabase resource panels can be built after confirming which metrics this project actually exposes.

## Rotation and troubleshooting

After changing the Supabase URL or secret in `.env`, rerun the preparation command. Then validate and recreate Prometheus as above. The helper updates private files inside the mounted directory.

For scrape failures, inspect `/api/v1/targets?state=active` and the Prometheus logs. A 401/403 indicates credentials or permissions need checking. A permission-denied error for the password file requires rerunning the helper with the current container UID. A missing target requires checking that the preparation step completed. Use `sudo docker compose config --quiet` for validation because full Compose output includes interpolated Grafana credentials.

The successful curl probe alone does not establish ongoing Prometheus collection. Record the first successful automated scrape separately.

References

- [Supabase Metrics API setup](https://supabase.com/docs/guides/observability/metrics/vendor-agnostic)
- [Prometheus configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)
