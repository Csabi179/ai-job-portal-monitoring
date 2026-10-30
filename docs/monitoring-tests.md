# Monitoring Verification

## Baseline - 2026-10-28

- Docker hello-world ARM64: PASS
- Four monitoring containers started: PASS
- Prometheus ready endpoint: PASS
- Grafana health endpoint: PASS
- Node Exporter metrics endpoint: PASS
- Blackbox Exporter metrics endpoint: PASS
- Grafana web login: PASS

## Pending tests

- Prometheus target status
- Infrastructure dashboard
- Application availability dashboard
- Alert notification
- Simulated service outage
- Recovery notification
- Backend structured logging
- Monitoring configuration backup and restoration

Actual test results and screenshots will be added during implementation.

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

External Render Log Streams connectivity has not yet
been configured or verified.

The syslog endpoint remains bound to localhost.

Private keys and certificate files are stored outside
the Git repository.
