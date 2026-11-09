# Monitoring Verification

## Baseline - 2026-10-28

- Docker hello-world ARM64: PASS
- Four monitoring containers started: PASS
- Prometheus ready endpoint: PASS
- Grafana health endpoint: PASS
- Node Exporter metrics endpoint: PASS
- Blackbox Exporter metrics endpoint: PASS
- Grafana web login: PASS

## Verification overview updated 2026-10-30

The October 28 baseline describes the **earlier four-service stage**. The current deployment uses six monitoring containers.

| Area | Recorded evidence | Status |
| --- | --- | --- |
| Prometheus, Node Exporter, Blackbox | Metrics and HTTP probe outputs | Verified |
| Infrastructure, Availability, Backend Logs dashboards | Real data displayed in Grafana | Verified |
| Unified Monitoring dashboard (English) | User visually accepted Oracle, Render, Vercel, backend and collector sections | Verified visually |
| Alert Firing, Telegram Firing and Resolved | TEST-01: controlled local test endpoint | Verified **for the local test** |
| Grafana backup and extraction | TEST-02; not a full restored Grafana server | Extraction verified |
| Render API log pull → JSONL → Alloy → Loki | Pino HTTP requests and 404 in Grafana | Verified |
| SQLite deduplication | Integrity check and duplicate-ID counts | Verified in project tests |
| File rotation with Alloy ingestion | Synthetic 120-message run: 120 present, 0 missing, 0 duplicate | Verified for synthetic case |
| Collector health metric/alert | Node Exporter scrape error 0; Prometheus timestamp; new Grafana rule Normal | Verified Normal, not independently fired |
| Render Log Streams external TLS push | Endpoint rejected connection; experimental ingress removed | **Not deployed** |
| Individual firing of all nine alerts | Only local test firing/resolved confirmed | **Not fully tested** |
| End-to-end disaster restoration | Only Grafana backup extraction tested | **Not tested** |

Historical test steps below are retained as evidence and must not be read as the current configuration.

---

## TEST-01 - HTTP failure detection and Telegram recovery alert

**Date:** 2026-10-28
**Status:** PASS
**Environment:** Oracle Cloud Ubuntu 24.04 ARM64
**Components:** Blackbox Exporter, Prometheus, Grafana, Telegram

### Objective

Verify automatic HTTP failure detection, alert firing,
Telegram notification, and recovery detection.

### Test procedure

1. Verified that the monitoring test endpoint returned HTTP 200.
2. Created a backup of blackbox/blackbox.yml.
3. Temporarily changed the expected HTTP status from 200 to 418.
4. Restarted Blackbox Exporter to apply the test configuration.
5. Observed automatic alert evaluation and the Firing state.
6. Received the automatic Firing notification in Telegram.
7. Restored the original Blackbox Exporter configuration.
8. Restarted Blackbox Exporter.
9. Verified HTTP 200 and probe_success = 1.
10. Received the automatic Resolved notification in Telegram.
11. Verified that the Git working tree was clean.

### Observed results

| Check | Result |
|---|---|
| HTTP endpoint response after recovery | 200 |
| Blackbox probe_success after recovery | 1 |
| Grafana Firing notification | PASS |
| Telegram Firing delivery | PASS |
| Grafana Resolved notification | PASS |
| Telegram Resolved delivery | PASS |
| Alert expression after recovery | A=0, B=0, C=0 |
| Original configuration restored | PASS |
| Git working tree clean | PASS |

### Conclusion

PASS - The complete alerting and recovery notification
workflow was successfully verified.

This was a controlled monitoring failure simulation.
The actual Grafana service was not stopped.

### Evidence

Telegram Firing and Resolved messages were observed.
Screenshots can be stored separately for the university demo.

---

## TEST-02 - Grafana Backup and Restore Extraction

**Date:** 2026-10-28
**Status:** PASS
**Environment:** Oracle Cloud Ubuntu 24.04 ARM64

### Objective

Verify that Grafana persistent data can be backed up
and extracted into a separate Docker volume.

### Test procedure

1. Created a private backup directory.
2. Stopped the Grafana container.
3. Created a compressed archive of the Grafana Docker volume.
4. Restarted Grafana.
5. Verified the Grafana health endpoint.
6. Verified that the archive contains grafana.db.
7. Created a separate temporary Docker volume.
8. Extracted the backup into the temporary volume.
9. Verified that grafana.db exists and is not empty.
10. Removed the temporary test volume.

### Observed results

| Check | Result |
|---|---|
| Backup command exit code | 0 |
| Backup archive size | 159 MB |
| Archive contains grafana.db | PASS |
| Grafana restarted successfully | PASS |
| Grafana database health | OK |
| Restore extraction | PASS |
| Temporary test volume removed | PASS |
| Other monitoring containers remained running | PASS |

### Limitations

This test verified backup creation and successful extraction
into an isolated Docker volume.

A complete Grafana application restore on a separate server
was not performed.

The local backup alone does not protect against the loss
of the entire Oracle VM.

### Conclusion

PASS - Grafana backup and restore extraction verified.

---

## TEST-03 - Local RFC5424 Syslog to Loki

**Date:** 2026-10-30
**Status:** PASS

### Objective

Verify the local RFC5424 syslog ingestion pipeline:

Syslog TCP -> Grafana Alloy -> Grafana Loki -> Grafana Explore

### Test

A synthetic RFC5424 message containing JSON application
logging fields was sent to the local Alloy TCP listener
at 127.0.0.1:1514.

### Verification

Grafana Explore, Loki data source:

    {job="render_syslog_test"} |= "render_syslog_pipeline_test"

The expected log entry was found and displayed.

### Limitations

This verifies the local syslog ingestion pipeline only.

The external Render Log Streams TLS connection has not
yet been configured or tested.

No public syslog listener was enabled during this test.

---

## TEST-TLS-01 - Local TLS Syslog Ingestion

Date: 2026-10-30
Status: PASS

### Objective

Verify encrypted RFC5424 syslog ingestion using:

TLS client -> Grafana Alloy -> Grafana Loki -> Grafana Explore

### Configuration

- TLS endpoint: 127.0.0.1:6514
- Certificate: Let's Encrypt
- Domain: matchwise-logs-r0cecq.duckdns.org
- TLS version tested: TLS 1.3
- Loki job label: render_tls_test

### Verification

A synthetic RFC5424 syslog message was transmitted over TLS.

The Alloy loki_source_syslog_entries_total counter
increased from 0 to 1 while the connection remained open.

Grafana Explore successfully displayed the test entry.

### Limitations

The test used a local TLS connection.

Render Log Streams connectivity was attempted but not established. Experimental inbound Oracle rules were subsequently removed. **Current ingestion uses Render Logs API over HTTPS**, not external syslog push.

The local test listener remains bound to 127.0.0.1.

Private keys and certificate files are stored outside
the Git repository.


---

## TEST-04 — Render Logs API and SQLite collector

**Date:** 2026-10-30 · **Result:** PASS for the independently hosted backend.

Pino JSON HTTP requests were returned by Render Logs API, appended to the local allowlisted JSONL stream, forwarded by Alloy into Loki and displayed in Grafana. An intentionally generated HTTP 404 appeared as `statusCode=404` and `route=unmatched`. The SQLite integrity check passed, and duplicate identity counts were zero in the recorded checks. The team-hosted backend has **not** been verified to use the same logging middleware.

## TEST-05 — Synthetic log rotation under write load

**Date:** 2026-10-30 · **Result:** PASS for controlled synthetic test.

A 120-message synthetic file rotation produced **120 unique messages in Loki, 0 missing and 0 duplicate**. This did not force-rotate the real Render backend JSONL and does not establish an absolute zero-data-loss guarantee.

## TEST-06 — Render collector health and alert

**Date:** 2026-10-30 · **Result:** PASS for telemetry and rule provisioning.

Node Exporter exposed `matchwise_render_collector_last_success_timestamp_seconds` with `node_textfile_scrape_error=0`. Prometheus returned the metric. Grafana displayed **MatchWise - Render Log Collector Stale** as **Provisioned / Normal**. Its individual Telegram Firing/Resolved delivery was **not** tested.

## TEST-07 — Unified Monitoring dashboard

**Date:** 2026-10-30 · **Result:** PASS for visual user acceptance.

The unified English dashboard displayed Oracle CPU/RAM/disk and host history, Render and Vercel HTTP probes, backend Pino logs and collector monitoring; seven collapsible sections were present. The user confirmed the final translated and query-corrected dashboard worked as intended.

Refer to `docs/MONITORING_GUIDE.md` for the deployed architecture and the exact backend migration procedure.

## TEST-08 — Team backend, new Supabase project and auth log delivery

**Date:** 2026-11-09 · **Result:** PASS for the exercised live flow and two request-ID log correlations.

The existing Render service `matchwise-backend-monitoring-test` was connected to `emmanuelkyeremeh/job-portal-backend` on `main`. The same Render URL and Service ID were retained. The operator configured a newly created Supabase project through Render environment variables. The exact deployed backend commit was not supplied in the shared evidence.

The operator ran the following requests from the Oracle VM against the deployed backend and shared the results.

| Request | Expected and observed HTTP status | Request ID |
| --- | --- | --- |
| Register a new test account | 201, token and user returned | `5c0bd609-5350-492a-aea5-900737b2eab3` |
| Log in with the test account | 200 | `14738520-0087-492b-a4a8-adfc50d1471a` |
| Fetch /api/me using the issued token | 200 | `72eb5bda-c7ec-4e52-b3b5-c553d90190c2` |
| Fetch /api/account using the issued token | 200 | `073565b5-9d78-4ab3-bf51-c206aafa7e28` |
| Log out the current session | 204 | `98cdab42-4793-434e-ac45-1fc8b9a3fe77` |
| Reuse the logged-out token for /api/me | 401 | `ebd54217-a7d2-419f-8dcf-4dc858bc3e27` |

The live flow exercised Supabase Auth, application user-row reads and the protected-route session check. The post-logout 401 was the expected rejection.

The operator located these matching Pino events in Grafana, confirming delivery through Render Logs API, the Oracle collector, Alloy and Loki.

| UTC event time | Logged method and route | HTTP status | responseTimeMs | Request ID |
| --- | --- | --- | --- | --- |
| 2026-11-09T16:22:55.843582935Z | POST /auth/login | 200 | 815 | `14738520-0087-492b-a4a8-adfc50d1471a` |
| 2026-11-09T16:22:57.78386259Z | GET /me | 401 | 94 | `ebd54217-a7d2-419f-8dcf-4dc858bc3e27` |

The 401 event appeared in both the general HTTP log panel and the filtered HTTP error panel with the same Render log ID. These are two views of one event.

The dashboard auth metadata is manually set to `Verified by team` based on this operator-reported evidence. This records the test outcome at the stated date. The two event correlations establish delivery for these requests. The full SQL comparison and 24-check database verification outputs were not provided, and continuous auth availability and browser frontend integration were not tested in this flow.

The earlier October test entries describe their original test environment. TEST-08 supplies the later team-backend auth and logging verification.
