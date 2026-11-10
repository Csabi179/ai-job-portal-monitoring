# Supabase metrics on the Oracle monitoring VM

On 2026-11-09 the operator verified direct HTTP 200 access, successful promtool validation, and automated Prometheus collection. The active target was uvopvarvelpabhmrqaaw.supabase.co:443 with health up and no last error at 21:26:43 UTC. The project replacement was intentional. The inventory contained 323 metric names, including Prometheus-generated scrape health series.

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

In Grafana Explore, select Prometheus and run `up{job="supabase"}`. The Unified Monitoring dashboard includes the Supabase section documented below.

## Rotation and troubleshooting

After changing the Supabase URL or secret in `.env`, rerun the preparation command. Then validate and recreate Prometheus as above. The helper updates private files inside the mounted directory.

For scrape failures, inspect `/api/v1/targets?state=active` and the Prometheus logs. A 401/403 indicates credentials or permissions need checking. A permission-denied error for the password file requires rerunning the helper with the current container UID. A missing target requires checking that the preparation step completed. Use `sudo docker compose config --quiet` for validation because full Compose output includes interpolated Grafana credentials.

Use both the active target status and up{job="supabase"} to verify collection. A previously selected project can appear briefly in instant query results because of stored samples and lookback. All Supabase panels explicitly filter by the Supabase target variable.

References

- [Supabase Metrics API setup](https://supabase.com/docs/guides/observability/metrics/vendor-agnostic)
- [Prometheus configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)


## Unified Monitoring panel selection

The dashboard keeps its existing UID, `matchwise-unified-overview`, and refreshes every minute. The Supabase section contains 18 visualizations selected from the operator's observed inventory. The `Supabase target` selector is populated from current `up{job="supabase"}` series and defaults to the newly verified target. Every Supabase expression includes both the job and selected instance.

| Panel | Operational purpose |
| --- | --- |
| Metrics endpoint | Check the authenticated Prometheus scrape. |
| PostgreSQL reachability | Check the database exporter's ability to connect, gated by scrape success. |
| Database connection slots used | Compare exported PostgreSQL connection totals with the exported limit. |
| Data filesystem used | Track allocated /data filesystem capacity. |
| CPU utilization | Detect database-host CPU pressure. |
| Memory utilization | Track memory usage using MemAvailable. |
| Open database connections | Track connection counts across database roles. |
| Database size | Track database-object storage, excluding template databases. |
| CPU and memory history | Correlate resource pressure over time. |
| Filesystem capacity | Compare root and data filesystem usage. |
| Connections by database role | Attribute connection usage to database roles and internal services. |
| Transaction throughput | Compare committed and rolled-back transaction rates. |
| PostgreSQL buffer cache hit ratio | Observe database buffer-cache behavior when blocks are accessed. |
| Query temporary-file writes | Detect query spills to temporary disk storage. |
| PostgREST connection-pool queue | Observe queued Data API work used by the application's supabase-js requests. |
| Deadlocks and Data API pool timeouts | Identify database contention and pool acquisition failures. |
| Disk read and write throughput | View per-device storage activity. |
| Average disk read and write time | View per-operation disk timing while I/O is occurring. |

Displayed warning/critical thresholds are 80/90 percent for CPU, memory and data filesystem usage, and 70/85 percent for database connection-slot usage. These are initial dashboard indicators and create no alert rules. Database size and filesystem capacity are distinct from a Supabase plan's billable storage allowance. PostgreSQL connection counts include internal services and have no direct equivalence to the number of signed-in users.

Rates use five-minute windows. Cache-hit ratio and disk latency leave zero-denominator cases empty. No missing Supabase metric is replaced with zero. Device I/O is shown per device rather than aggregated across potentially overlapping block-device layers.

Metric names were checked against the operator's inventory. Label conventions and calculation meanings were cross-checked with Supabase's example metric exposition and PostgreSQL's monitoring documentation. Live evaluation and visual acceptance of the new panels still require the Oracle Grafana environment.

Source references

- [Supabase metric exposition examples](https://github.com/supabase/supabase-grafana/blob/main/metrics.md)
- [Supabase dashboard reference](https://github.com/supabase/supabase-grafana/blob/main/dashboard.json)
- [PostgreSQL cumulative statistics](https://www.postgresql.org/docs/17/monitoring-stats.html)

## Outage alerting update — November 10, 2026

The repository adds separate Metrics API/telemetry and PostgreSQL reachability rules, pinned to `uvopvarvelpabhmrqaaw.supabase.co:443`. Successful scrape plus pg_up=0 means exporter-to-database connectivity failure; a failed API scrape alone does not establish database failure. Missing pg_up is a telemetry issue. Neither capacity nor latency creates an alert. See the [alerting plan](alerting-plan.en.md) for conditions, deployment and live tests still required. Change both alert selectors when intentionally changing project.
