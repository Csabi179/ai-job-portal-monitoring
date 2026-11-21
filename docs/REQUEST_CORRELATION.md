# Frontend/backend request correlation

Updated November 21, 2026. **Oracle deployment and the English Grafana request table are operator-verified.**
The Hungarian dashboard has identical queries and transforms and passed local
checks; its live rendering has not been separately evidenced.

## Contract verified against the merged frontend

Source: [ernoking/job-portal-frontend at 339074e](https://github.com/ernoking/job-portal-frontend/blob/339074ea339f92b7138efc4a07afef4617fde613/src/monitoring/apiTraffic.js).
The actual capture mode sends `schema_version: 2`, all original aggregate fields,
and **both** `requests` and `dropped_requests`. A request has exactly:

```json
{
  "request_id": "14738520-0087-492b-a4a8-adfc50d1471a",
  "started_at_ms": 1795000000000,
  "finished_at_ms": 1795000001250,
  "duration_ms": 1250,
  "route": "/cv/:id/profile",
  "method": "POST",
  "status": 200,
  "outcome": "http"
}
```

The receiver preserves v1. V2 allows at most 64 request details per batch, UUID
or null IDs, known route templates, HTTP 100–599/`other`, and status 0 for
`network_error`/`aborted`. Durations are finite, 0–3,600,000 ms; timestamps
are safe integers with at most 1 ms rounding difference from duration.
Non-HTTP failures have null IDs, as emitted by the frontend. Unknown fields,
raw resource paths, queries and credentials are rejected before changing counts.
The full HTTP payload limit remains 60,000 bytes. The receiver implementation
metric is 3; that is distinct from accepted payload versions 1 and 2.

Frontend flags (Vite build-time settings): `VITE_FRONTEND_TELEMETRY_ENABLED=true`,
`VITE_FRONTEND_TELEMETRY_REQUESTS_ENABLED=true`, and the existing telemetry URL.
The operator reports these were configured and the frontend redeployed. This
change does not independently establish what production Vercel is serving.

## Data path and comparison

Browser -> existing public receiver -> `/var/lib/matchwise-frontend-traffic/requests.jsonl`
-> Alloy -> Loki stream `job="matchwise_frontend_requests"` -> Grafana.
The JSONL journal is 20 MB per file with seven archives. It is outside Git,
owned through the receiver's systemd StateDirectory, with a read-only Alloy bind.
The Docker daemon resolves the DynamicUser state directory symlink as root;
verify actual readability on Oracle. No request IDs become ingestion labels.

The frontend journal may not exist until the first v2 request batch arrives.
Use `local.file_match.frontend_requests` with a ten-second discovery interval,
feeding `loki.source.file.frontend_requests`, so startup without the file does
not permanently skip collection. The operator observed this failure with the
initial static target: ten valid ID-bearing records were readable inside Alloy
but its startup log reported `failed to create source, skipping` because the
file had not existed yet. The operator then validated/applied dynamic discovery
and confirmed healthy Alloy plus continued real ID correlation. Reproducing a
missing-file startup followed by delayed file creation has not been tested live.

After the operator restarted Alloy with the file present, the read-only verifier
matched a real `/auth/logout` request: frontend 485 ms, backend 390 ms, both
HTTP 204. This confirms one real request correlation in Loki. It does not yet
verify the Grafana table rendering, other error cases or missing-file recovery.

The operator subsequently validated/applied dynamic discovery on Oracle and the
same ID match remained successful. Frontend slow-request logs were visible in
Grafana, but the table was empty with aggregate-suffixed column names. The table
fix preserves Grafana's actual `field (lastNotNull)` identities through join,
filter, conversion and sorting; presentation renames run last. The local checker
now validates these field references. The operator's subsequent English dashboard
screenshot shows populated, correctly named frontend/backend columns, matching
routes and statuses, duration colouring and a separate slow-request log list.
It includes `/cv/:id/profile` HTTP 503 on both sides, with displayed timings of
approximately 1.68 s frontend / 1.57 s backend, and successful login/logout rows.
The ID-less and dropped-detail diagnostics show zero in this observation; this
does not prove behavior under induced network failures or dropped batches.

The receiver fsyncs the journal before acknowledging 204. A disk error returns
503 for the existing browser retry policy. Journal writes do not add request
counts to the original aggregate metrics: aggregates remain authoritative for
overall counts and histograms. `dropped_requests` contributes to a separate
diagnostic counter, not an application error count.

Grafana dashboards:

- Hungarian: `/d/matchwise-request-correlation`
- English: `/d/matchwise-request-correlation-en`

The request table extracts frontend and backend fields, collapses repeated
records by request ID, joins frontend `request_id` with backend `reqId`, and
keeps rows that have frontend details. Missing backend duration stays null.
HTTP responses without IDs, network errors and aborts are listed separately;
null IDs are never used as a join key. Slow/failed records include a selectable
duration threshold, HTTP 4xx/5xx, network failures and aborts.

Frontend time measures fetch until response headers, excluding body download
and JSON parsing. Backend time measures server processing. Their difference is
not a pure network measurement. This is request correlation, not distributed
tracing of internal backend/database spans.

Frontend already excludes health routes. The receiver additionally drops
explicit health detail rows; every new Loki query excludes health routes.
Backend-only traffic cannot enter the correlation table, so UptimeRobot checks
without a browser report do not appear even if their target changes. These
filters apply to the new request view; existing availability panels still show
their own probes. No User-Agent or IP collection is introduced.

## Deployment

Use the actual reviewed branch/commit; do not run an old installer against the
new receiver (legacy scripts expect receiver implementation version 2).
Preserve local Caddy/Prometheus changes and private files; never reset Git.

```bash
cd ~/ai-job-monitoring
git status --short
# After the reviewed branch is available, fetch/check out or merge it per team workflow.
# Confirm its exact commit before continuing:
git rev-parse HEAD
bash scripts/install-request-correlation.sh
```

The installer rejects tracked local modifications and an existing requests.conf
drop-in. It backs up the installed receiver, preserves existing service origin
settings and local-test overrides, installs the small state-directory drop-in,
restarts the receiver and validates/recreates Alloy. Its new directory must
exist before Compose can create Alloy. Provisioned dashboards reload within
30 seconds; Grafana/Prometheus are not restarted.

If installation fails, the trap attempts receiver/drop-in rollback and prints
the backup path. It cannot guarantee Alloy recovery or restore Git configuration;
inspect those explicitly. The installer prints receiver rollback commands.
For full rollback, restore this change's `alloy/config.alloy`, `compose.yaml`
and dashboard/link changes from the prior reviewed commit, validate and recreate
Alloy. Remove the two new dashboards through Grafana administration if necessary:
the provisioning provider has `disableDeletion: true`. Keep private journals.

## Live verification and acceptance

1. `curl -fsS http://127.0.0.1:9121/metrics` must show receiver implementation 3.
2. Open the real frontend and make a normal API request. Wait for its 60-second
   report, Prometheus scrape and Render log collection. Do not send test traffic
   containing real CVs/tokens in diagnostic payloads.
3. Run the read-only verifier:

   ```bash
   python3 scripts/verify-request-correlation.py
   # Or select one UUID copied from a real request:
   python3 scripts/verify-request-correlation.py --request-id UUID
   ```

4. Open the new Grafana dashboard. Confirm the same ID, frontend/backend times,
   route and statuses. A successful Loki match does not verify the table's
   transformations or rendering; inspect the table itself.
5. Exercise a known-safe HTTP error, aborted request and slow request. Check
   the error/slow list, and retain ID-less failures without inventing a backend
   match. Confirm `/health` and `/api/health` never appear in the new view while
   existing availability probes keep working.
6. Confirm request details are readable inside Alloy and present in Loki:

   ```bash
   sudo docker compose logs --tail 60 alloy
   sudo systemctl status matchwise-frontend-traffic.service --no-pager
   ```

Record commit, UTC test time, sample UUID, both durations/statuses, Grafana
evidence and UptimeRobot exclusion in `monitoring-tests.md` only after running.

## Limits

- Browser data can be blocked, dropped or fabricated; it is not an audit log.
- Reporting is bounded to 64 details per batch. Details are not all traffic.
- IDs require the backend header to survive the Vercel proxy. For direct
  cross-origin API calls, backend CORS must expose `X-Request-Id`.
- Frontend Loki times use ingestion time; original browser timestamps remain
  fields. Backend uses Render event time. Collection delay/window boundaries
  can temporarily hide a match; widen the range and refresh.
- Each table query reads at most 1000 lines. A missing match is not proof of a
  missing backend request. Narrow the range or filter by UUID.
- Batch deduplication remains in-memory, bounded to 10 minutes/8192 IDs.
  A restart/retry or process crash can duplicate detail lines. Grafana collapses
  ID-bearing duplicates; ID-less logs can repeat. This is not exactly-once delivery.
- File rotation and fsync reduce risk, but do not guarantee zero loss during
  a prolonged Alloy/Loki outage. Archives are deliberately not re-read by Alloy.
  Size caps are not age-based retention; delete retained data at project shutdown.
- The new receiver restart resets its aggregate counters, as previous updates do.

## Local checks

### Service Comparison placement and request timing lines

The visual review follow-up improves the request table and Service Comparison
scorecard without changing datasource queries. HTTP status cells retain their
actual codes and use green for 2xx/3xx, orange for 4xx, red for 5xx and gray for
missing values. Duration cells use ordinary text so a fast HTTP 503 is not
presented as a green success. Time/route/durations/statuses precede a narrow,
inspectable Request ID column; redundant backend route and HTTP outcome columns
are hidden, not removed from the underlying data. Human-readable HU/EN headers
replace raw field names.

Scorecard labels distinguish HTTP checks, PostgreSQL reachability and Oracle
metrics availability. Duration cards distinguish HTTP probe duration from
metrics scrape duration. Missing traffic/rate samples are labeled conservatively,
without inferring zero traffic, 0% errors or an outage; Oracle's explicitly
uncollected application metrics remain unchanged. Five-minute windows are visible
in rate-card titles. Live rendering of this visual follow-up remains pending.

The request table is embedded below the section 01 scorecard and before section
02 Availability and freshness in both Service Comparison language editions.
An operator screenshot confirms the table's English placement and populated rows.
The user approved an inline preview of a two-line time chart immediately above
that table: browser-recorded request start time on X and response duration on Y,
with blue frontend and orange backend lines on the same zero-based duration scale.
It uses the exact same joined records and Request ID filter, without averaging,
stacking or a top-twenty limit. Missing backend durations remain missing. Requests
with identical start timestamps retain their values and can overlap visually;
the table remains available to inspect individual requests. The chart connects
observed requests and does not imply continuous latency sampling between them.
Updating an existing bar panel replaces it and reclaims the extra layout space,
preserving the request table and all subsequent panels. The operator's subsequent
English screenshot confirms live rendering: browser request times on X, response
duration on Y, blue Frontend and orange Backend lines, both series in the tooltip
(one shown pair is 411 ms / 292 ms), and the request table directly below.
Some older frontend records have no backend match within the selected query
window; their backend cells remain empty. The screenshot does not establish the
cause of each missing match. Long segments connect sparse request observations.
Separate live Hungarian rendering remains unverified.

`build-request-correlation-dashboard.py --embed-only DIRECTORY` preserves existing
Service Comparison panels/settings, inserts or replaces the table/chart idempotently and
shifts subsequent grid positions. It validates both language destination UIDs
before writing. No receiver, Alloy, Prometheus or Grafana restart is required.

```bash
python3 -m unittest discover -s scripts -p 'test_frontend*.py'
python3 scripts/build-request-correlation-dashboard.py
python3 scripts/check-request-correlation-dashboard.py
bash -n scripts/install-request-correlation.sh
```

Local tests cover mixed v1/v2 traffic, no aggregate double counting, missing IDs,
health exclusion, invalid records, retry after disk failure, bounded rotation,
HTTP acknowledgement and existing receiver behavior. Model checks cover HU/EN
query parity, table join/filter guards and layout. Live Loki, Alloy/systemd and
Grafana rendering checks require the Oracle environment.

Implementation references: [Grafana transformations](https://grafana.com/docs/grafana/latest/visualizations/panels-visualizations/query-transform-data/transform-data/),
[Loki query pipelines](https://grafana.com/docs/loki/latest/query/log_queries/).

### Selected-period averages and event chart scale

Service Comparison traffic scorecards now evaluate `rate(counter[$__range]) * 60`
at the selected end time. HTTP error and rollback percentages are event-weighted
shares over that same window, not averages of rolling percentages. Historical
summaries do not depend on current health or telemetry freshness gates; the
separate current-health cards retain those checks. Incomplete counter coverage
can still produce an extrapolated estimate; missing samples remain missing.
Counter resets are handled by applying rate before aggregation.

The four security cards show selected-period log counts divided by
`$__range_s / 60`, in events/minute (two decimals), preserving their health
exclusion and zero fallback only where the base log stream exists. Their text
describes the new units. Time-series event/traffic charts have a zero minimum
and a soft maximum of one event/minute, with no hard upper cap; peaks can extend
the axis. Percentage and request-latency chart scales are unchanged. Both
languages and the in-place updater use these settings. Live query execution
and Grafana rendering must be checked after deployment.

References: [Grafana time-range variables](https://grafana.com/docs/grafana/latest/visualizations/dashboards/variables/built-in-variables/),
[Prometheus rate](https://prometheus.io/docs/prometheus/latest/querying/functions/#rate),
[Grafana soft axis limits](https://grafana.com/docs/grafana/latest/visualizations/panels-visualizations/visualizations/time-series/).

### HTTP access and error signals presentation

The HTTP-signal section now promotes exact selected-period event counts to the
four main cards. A smaller stat directly below each count retains the average
in events/minute, using the same count divided by the selected duration. Zero
counts are gray; positive counts are orange; absent samples remain gray and
unavailable. No new zero-filling is introduced. Both existing time-series graphs
stay together in the section, with unchanged expressions and shorter legends
without last-non-null statistics. The header is reduced from four grid units to
three, with two brief sentences and detailed caveats in its information tooltip.
The section is labelled HTTP access and error signals, rather than security.

`--http-signals-only DIRECTORY` updates just this section in both languages,
preserving scorecard queries and the request timing table/chart. Four reserved
panels (982–985) hold the small average values; the original count-card area is
split into a count and an average without increasing its total height. Updates
are idempotent, and unrelated uses of the reserved IDs are rejected. Live visual
verification remains necessary after deployment.
