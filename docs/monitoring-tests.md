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
