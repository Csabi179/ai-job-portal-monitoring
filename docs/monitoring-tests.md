# Monitoring Verification

> **Current deployment — 2026-11-19:** The operator confirmed all supplied changes were already applied on Oracle. Monitoring was merged into `main` (`10f43d1`); no reinstallation is required because of that merge. [Current status](DEPLOYMENT_STATUS.md). Earlier rollout entries are historical; commands are retained for future updates or recovery.

## Current documented state — reviewed November 19, 2026

- Sixteen permanent rules: original twelve outage/monitoring rules plus four resource/security signals. Applied rollout is confirmed by the operator.
- Render resource API collection, .prom ingestion, systemd timer and Prometheus ingestion confirmed by operator output; Service Comparison dashboard confirmed by screenshots.
- All three new synthetic tests delivered firing and resolved to the team Telegram group. Operator confirmed cleanup and a real ten-failed-login trigger.
- Earlier collector and Node Exporter delivery evidence remains valid; the other ten original rules have not been individually verified live.
- Viewer access is confirmed only for Unified Monitoring, not the new comparison dashboard. Four-hour repetition, full-host failure protection and missing-data branches are not established.
- Monitoring main was fast-forwarded to 10f43d1 on November 19. The operator confirmed every supplied runtime change was already applied with the provided helpers. No additional deployment is required due to this merge; the current live Git checkout HEAD was not re-inventoried.
- Historical records retain their original scope/dates. CV/AI preparation is not proof of production deployment.

## TEST-24 — Deployment confirmation and monitoring main merge, 2026-11-19

**Result: operator-confirmed deployment; independently verified GitHub merge.** The operator clarified in chat that every supplied change was run immediately on Oracle. This includes the latest selected-period API count and removal of unavailable frontend host resource cards. No new deployment is required merely because the existing feature history was merged into main.

GitHub main was verified at 10f43d1c6b770a0ac5ca91a297d83d0b3dad3062 after a conflict-free fast-forward of 113 commits. Before merging, 52 Python tests, 38 alert PromQL scenarios, dashboard guard scenarios, 106 dashboard PromQL expressions, Prometheus configuration syntax and all shell syntax checks passed. This does not assert a new SSH audit, a new Oracle Git HEAD inventory or completion of every optional fault-injection test.

<a id="test-23-real-404-alert"></a>
## TEST-23 — Real HTTP 404 alert cycle, 2026-11-18

**Result: operator-confirmed successful procedure.** After running the bounded real-backend 404 test, the operator reported that everything completed successfully. The procedure expects twenty sequential HTTP 404 responses, the production HTTP 404 burst rule's firing notification and later recovery/resolved. This is an operator confirmation of the full procedure; raw response output, individual state/notification timestamps and new screenshots were not supplied. No exact latency is inferred.

The operator had also confirmed the new security panels appeared. The helper is versioned at scripts/test-backend-404-once.py and is intended for future controlled reruns. See the [repeatable test catalog](testing/README.md). This does not establish overload/DDoS resistance, 403/429 enforcement, a production CPU/5xx threshold breach or all missing-data/error branches. New repetitions need their own evidence.

<a id="test-22-security-update-preflight"></a>
## TEST-22 — Security overview and one-minute backend preparation, 2026-11-18

**Local checks only; live validation pending.** Branch configuration now adds a guarded 404 burst rule (sixteen permanent rules), eight security panels (35 comparison panels) and 60s/15s/10s backend cadence/timeouts with three-minute freshness. All alert UIDs, dashboard/panel annotation pairs, expression references/cycles, panel IDs and grid layout checked. Four query-checker tests passed for required telemetry, empty dashboard logs, safe HTTP diagnostics and bounded log query endpoints. Python syntax checked. The three existing synthetic-helper tests also passed with the expanded source rule set (seven Python tests total), and rollout command Bash syntax passed.

The original twelve-rule PromQL scenario suite was updated for backend recent/expired success and failure cases. It must be rerun with Oracle's deployed-version promtool; no successful rerun is claimed locally. New Loki queries, including offset baseline, require live read-only validation. No deployment success or actual 404 trigger has been supplied. [Staging and rollout](SECURITY_OVERVIEW_AND_FREQUENT_PROBES.md).

<a id="test-17-render-resource-collection"></a>
## TEST-17 — Render resource collection and scheduling, 2026-11-18

**Result: operator-supplied live output confirms the complete API-to-Prometheus path.** CPU, cpu-limit, memory and memory-limit each returned HTTP 200 with nonempty samples and units cpu/bytes. After a query-format fix, the Python collector exited 0 and emitted collection_success=1. File publication and Node Exporter reading were confirmed with CPU 0.14497778%, RAM 17.7024848991% and node_textfile_scrape_error=0. Operator output confirms an active two-minute timer and a Prometheus collection_success=1 vector with job=node_exporter.

Local collector tests: four methods including invalid inputs, safe HTTP diagnostics and atomic replacement passed. Initial explicit time-window requests returned HTTP 400; matching the earlier probe request fixed collection. Credentials were not changed or recorded. Exact rejected parameter not isolated. This verifies the supplied successful samples, not continuous availability or a fresh-data guarantee during a sleeping service.

<a id="test-18-service-comparison-dashboard"></a>
## TEST-18 — Service Comparison dashboard, 2026-11-18

**Result: operator screenshots confirm rendering and visible data.** Four columns show Render, Supabase, Vercel and Oracle. Resource graphs, status cards, sample ages, backend traffic/errors/response times, collector age and HTTP error logs are visible. Vercel CPU/RAM are explicitly Not collected. New Render history is short because collection just started. Local JSON/ID/grid/filter checks passed.

**Limits:** no Viewer-account test for this new dashboard was supplied. Different resource percentages do not establish an attack. The older architecture diagram has not been redrawn to include this feature.

<a id="test-19-alert-provisioning-recovery"></a>
## TEST-19 — Alert query preflight and Grafana startup recovery, 2026-11-18

**Result: all five datasource queries succeeded; startup incident identified and corrected.** Operator output: CPU A=0; 5xx A=0,D=1; login A=0,D=1. Grafana initially restarted because the new rule annotations set __dashboardUid__ without __panelId__. Logs explicitly identify that invalid pair. Removing the new file restored database=ok. The incomplete optional links were removed from all three rules and a validator assertion was added. Operator confirmed the corrected deployment worked; later screenshot shows all three production rules and database=ok.

**Limits:** JSON and datasource-query checks alone did not validate Grafana provisioning; this incident demonstrates that boundary. General missing-data/error branches and the full original promtool suite were not rerun in this environment.

<a id="test-20-synthetic-security-alert-cycle"></a>
## TEST-20 — Three synthetic alert cycles and cleanup, 2026-11-18

**Result: firing and resolved Telegram messages for all three TEST rules are visible in operator screenshots.** Temporary rules used separate test UIDs/category and timed Prometheus values. Real Grafana expression graphs and pending periods were preserved. The backend was not loaded and no application logs were fabricated. /api/health returned database=ok. Local helper tests covered source isolation, expression/pending preservation, deletion scope, invalid input and atomic output.

The operator subsequently confirmed cleanup succeeded and the system still worked. Removal is operator-confirmed; no independent post-cleanup inventory was supplied. Exact per-rule pending/receipt times were not measured. This confirms the synthetic notification/recovery path, not real CPU/5xx threshold breaches or telemetry failure behavior.

<a id="test-21-real-login-alert"></a>
## TEST-21 — Real rejected-login alert, 2026-11-18

**Result: operator-reported successful production-rule trigger.** The operator intentionally failed login ten times and supplied firing text for MatchWise | Render backend | Rejected login burst. This is distinct from the TEST fixture: it uses real backend HTTP logs and the permanent rule.

The rule counts POST /auth/login or /api/auth/login requests returning 401 across all users in the rolling last five minutes. It evaluates every minute and requires the count condition to remain true for two minutes. No new failed logins are required while the original ten remain in that window. See the [timing example](SERVICE_COMPARISON_ALERTS.md).

**Limits:** exact attempt/event/evaluation/receipt times, identities and a production-login resolved message were not supplied. Do not treat the illustrative 12:00 timeline as measured test evidence. Source CPU and 5xx threshold tests remain unverified.

<a id="test-14-https-viewer-access"></a>
## TEST-14 — Grafana HTTPS and Viewer access, 2026-11-11

**Result: deployment output plus operator confirmation.** Caddy configuration validation passed. Supplied OCI screenshots showed stateful TCP 80/443 ingress; iptables output showed their ACCEPT rules before REJECT. Caddy and Grafana started; logs reported successful certificate acquisition for grafana-r0cecq.duckdns.org. HTTPS Grafana health returned database=ok, version 13.2.1. The operator confirmed successful external browser login.

The operator removed the folder-wide Viewer grant and direct Viewer grants on the other three dashboards, retaining Viewer access on Unified Monitoring. The supplied account screenshot showed organization Viewer and Grafana Admin No; the operator confirmed the requested access test worked. This used a shared team account, not individual teammate accounts. Account credentials are deliberately omitted.

**Limits:** exact forbidden-URL responses and a dedicated Grafana Live test were not supplied. Firewall persistence across a reboot, per-datasource isolation and full disaster recovery were not verified. Users/ACLs are Grafana database state, not enforced by dashboard JSON.

<a id="test-15-collector-timeout-recovery"></a>
## TEST-15 — Render Logs API timeout and automatic recovery, 2026-11-11

**Result: successful recovery observed in supplied journal and metrics.** Repeated authenticated Logs API requests failed with read timeouts at the collector's 30-second request timeout. The timer remained active. Heartbeat age was 599.636 seconds while node_textfile_scrape_error=0.

An unauthenticated API reachability request returned HTTP 401 in 0.194216 seconds; this is reachability evidence, not an authenticated retrieval test. At 00:37:57 UTC the journal reported two pages fetched, 156 new Pino logs written, no new 4xx/5xx logs, collection through 00:37:34.735933Z, successful completion and success-metric update. A later Prometheus query showed heartbeat age 72.713 seconds.

**Limits:** the underlying cause of the upstream delay was not established. No new collector code/timeout/threshold change was made, and no later resolved Telegram message was supplied for this particular incident.

<a id="test-16-cv-ai-preparation"></a>
## TEST-16 — CV/AI source review and Render preparation, 2026-11-15

**Result: source inspection and operator-confirmed environment preparation only.** The supplied main archive contained authenticated CV upload, PDF/DOCX text extraction and Cloudinary file storage. The separate feat-ajsp-4-cv-profile archive contained profile extraction through Cloudflare Workers AI @cf/openai/gpt-oss-20b, using CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN with a 25-second AI-request timeout. It also contained the save_cv_profile SQL migration.

The operator reported adding both variables to Render. No values are recorded here. Existing collection allows only http_request events; endpoint counts/statuses, total request duration and reqId can be used if the deployed code emits the same format. Separate AI duration, token usage and detailed provider errors are unavailable. No AI panel or alert was added.

**Limits:** no live AI call or CV upload was executed during this review; merge, deployment, frontend integration and application of the Supabase migration are not established by this record. The later main/merge state was not independently established during the documentation review.

## Historical verification records


<a id="test-13-telegram-group-delivery"></a>
## TEST-13 — Telegram team-group destination, 2026-11-15

**Result: operator-reported successful switch to group delivery.** The operator created a Telegram group, added the existing bot and reported success after following the group chat-ID lookup, private environment update, Grafana recreation and contact-point test procedure. No direct Oracle or Telegram access was used by the assistant to verify these actions.

The destination is now the team group instead of the previous private conversation. The existing contact point `AI Job Telegram` (UID `ai_job_telegram`) reads `GRAFANA_TELEGRAM_CHAT_ID` and `GRAFANA_TELEGRAM_BOT_TOKEN` from the private Oracle environment. No bot token, actual chat ID or real `.env` is committed.

**Limits:** no timestamped API/test output or group-delivery screenshot was supplied. This records the operator's success confirmation, not a new induced firing/resolved test for any rule. Rule conditions, UIDs, resolved-message setting and notification grouping/timing are unchanged.

Repeatable procedure: [English](alerting-plan.en.md#telegram-group-as-the-notification-destination) · [Hungarian](alerting-plan.md#telegram-csoport-mint-értesítési-cél).


<a id="test-11-node-exporter-delivery"></a>
## TEST-11 — Node Exporter Firing/Resolved and English delivery, 2026-11-10

**PASS for the operator-provided Node Exporter failure/recovery sequence.** The operator supplied these query responses and Telegram messages after the earlier language update:

| Evidence | Observed value |
|---|---|
| `up{job="node_exporter",instance="127.0.0.1:9100"}` at query time 2026-11-10 21:09:04.266 UTC | 0 |
| Telegram firing | MatchWise / Oracle host metrics / Monitoring failure, English description and English runbook link |
| Same up selector at query time 2026-11-10 21:15:17.488 UTC | 1 |
| Telegram resolved | English recovery text: The alert condition has cleared. Verify evaluation health and fresh measurements. |

The timestamps above are the supplied Prometheus query evaluation times, not measured scrape/firing/receipt timestamps. The preceding procedure deliberately stopped and restarted Node Exporter; a full VM outage was not simulated. The operator also reported the English update succeeded. No direct assistant SSH access or exact new live Git HEAD was supplied.

Collector and Node Exporter Firing/Resolved have now been evidenced. The other ten rules have not been individually verified live. This does not prove grouped delivery, 4-hour repeat, missing-data branches or independent-host detection.

## TEST-12 — Manual command runbook and local fixture checks

**Local verification only; no new Oracle test executed.** The [English](alert-rule-tests.en.md) and [Hungarian](alert-rule-tests.md) runbooks document one procedure for every provisioned UID, expected inputs/notifications and restoration commands. Source: `41c3f8d`. The companion helper lives under docs/testing and never invokes Docker/systemd or sends Telegram messages itself.

Local checks passed for all 12 supported fixture modes using Prometheus 3.13.2 promtool syntax validation, one-job-only configuration changes, preserved original instance labels, absence of credentials in replacement jobs, exact-byte restoration and refusal to overwrite concurrent edits. Five local HTTP responses (200/503/pg_up 0/1) were exercised on an ephemeral loopback test port. These checks validate fixture construction, not full Blackbox/Grafana/systemd behavior on Oracle. Both language editions cover all 12 UIDs, and their 30 Bash blocks have identical executable commands. Bash -n syntax checking and relative documentation-link checks passed; Bash -n did not execute the documented commands.

The temporary fixture job replaces normal measurements during a manual test. Synthetic samples must be excluded from real availability interpretation. The backend's original 30-minute interval is restored from its private backup. Run one case at a time, record outcomes separately, and do not mark unexecuted procedures as passed.


[Documentation index](README.md)

<a id="test-10--oracle-rollout-and-collector-telegram-delivery-2026-11-10"></a>
## TEST-10 — Oracle rollout and collector Telegram delivery, 2026-11-10

**Result: PASS for the operator-evidenced deployment and this collector Firing/Resolved sequence. Not a complete 12-rule delivery test.** Evidence was supplied by the operator in chat; the assistant did not directly access Oracle.

- Oracle working tree advanced from `a39e5a5f86ca7de2c64d3afb57d4b3ebd1ddefe2` to `665d2d5272143402429e9cffd4cb975e460b1c8a`. Existing untracked dashboard-export/plugin-placeholder files were retained.
- Compose validation and the Oracle promtool configuration check succeeded. Prometheus was recreated with its persistent volume retained; readiness succeeded after an initial immediate-startup connection refusal.
- Direct Loki /ready and Alloy /-/healthy responses succeeded. The operator supplied `up=1` and `probe_success=1` for both new local probes.
- The selected Supabase instance returned `up=1` and `pg_up=1`.
- Grafana health reported database=ok and version 13.2.1. Logs included finished alert provisioning, rules=12, enabled rule evaluation and a running scheduler. The supplied rule-list screenshot showed all 12 expected provisioned rules with green status and no old capacity/local-test rule.
- A contact-point Test message was received in Telegram using the new template.
- The operator followed the controlled collector-timer interruption test and supplied the real `matchwise_render_collector_stale` firing message, then the resolved message after the instructed restoration. Both messages still used the Hungarian notification wording.

**Limits:** exact stop/start, pending, firing and resolved timestamps were not supplied; no measured detection-time SLA is claimed. The final timer activity/service-result command output was not pasted, so receipt of resolved alone is not a separate proof that the timer remains enabled. No other rule was individually fired. Grouping, 4h repeat, query Error and missing-data KeepLast transitions remain untested live. The successful collector test is not an end-to-end Loki delivery test or full-host outage test.

### English notification and documentation update

The later language-only repository update translates all 12 alert titles and summary/description annotations, the shared resolved message and Runbook label/link. UIDs, PromQL, condition chains, pending/evaluation intervals, No Data/Error handling, labels, Telegram destination and notification timing are preserved. Hungarian documents remain with separate English editions and a bilingual index.

Local checks **passed**: comparison against `665d2d5` confirmed unchanged rule logic, UIDs, timing and routing; all 19 JSON/YAML configurations parsed; the four English editions have reciprocal links and valid relative document links; all 12 descriptions are English and below the template's 200-character limit; the existing 37 promtool scenarios passed again. Prometheus syntax validation also passed. English Grafana provisioning and an English Telegram message test are **pending** until the operator supplies evidence. The previously received Hungarian collector messages do not establish delivery of the later English wording.


## TEST-09 — Outage-only alerting configuration, 2026-11-10

**Result: PASS for local static configuration and PromQL evaluation; Oracle rollout and live delivery NOT TESTED.**

Baseline inspected through the GitHub connector: main commit `374f74eab098deccfd408887bbef5db314c83223`. The Git CLI clone could not authenticate; repository files were fetched through the authorized connector. Local changes are in a source snapshot, not a complete local Git checkout. No Oracle SSH session or live Grafana API was used.

The nine baseline rules were reviewed individually. The local Grafana test, low-memory and low-disk rules are explicitly deleted through provisioning. Twelve outage/monitoring-failure rules replace the active set. Existing HTTP and collector UIDs are retained; the old exporter UID now specifically monitors Blackbox, with Node Exporter separate.

| Check | Result | Limit |
|---|---|---|
| Alert JSON/YAML parse, unique rule UIDs, evaluation intervals, threshold chain, KeepLast/Error settings | PASS | Local structure, not Grafana import |
| Explicit deletion of three old rules; no active overlap | PASS | Grafana database deletion awaits provisioning |
| Telegram variables and resolved flag preserved; grouping/template configuration parsed | PASS | Go template runtime and message delivery require live test |
| Prometheus 3.13.2 `promtool check config --syntax-only` | PASS | Private Supabase files and Oracle mounts not validated locally |
| Docker Compose `config --quiet` with explicit dummy Grafana environment values | PASS | No containers started; no secrets used |
| Actual provisioned PromQL, 37 synthetic scenarios with Prometheus 3.13.2 promtool | PASS | No Grafana pending/Error/KeepLast state machine or scheduler simulation |
| Oracle deployment, 12 live rule health states, actual Loki/Alloy endpoint responses | NOT TESTED | Operator steps in alerting-plan.md |
| Per-rule Telegram Firing/Resolved, grouping and 4h repeat | NOT TESTED | Test notification alone is insufficient |

The promtool Windows archive SHA-256 matched its official GitHub release asset digest: `ebd97831d80be097eed54af257816ca7fa93cc67682bdcf94d44057b17cde6ad`.

Reproduction: `python3 scripts/validate-alerting.py --promtool /path/to/promtool` with PyYAML installed. The test reads expressions from provisioning files. It exercises healthy/failing/missing scrapes; HTTP failure versus probe scrape failure; HTTP recovery; sparse backend data at 39 minutes and expiry beyond 40; Supabase API versus database failures; missing pg_up; fresh/frozen/missing collector heartbeat and textfile errors; quiet application; Node Exporter failure; Loki/Alloy health checks.

The simulator explicitly expects **no service-state result** when evidence is missing. Grafana KeepLast preservation must still be verified on the running version. The update adds documented local health endpoints but does not prove full log delivery, VM uptime or independent external outage detection.

Next live test records must include commit, time zone, UID, input, pending/firing/resolved times, Telegram receipt, restoration and final service state. See [the alerting plan](alerting-plan.md) for rollout, test matrix and rollback. Older entries below retain their historical scope.

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

At the time of this test, the dashboard auth metadata was manually set to `Verified by team` based on this operator-reported evidence; the later introductory latest-auth-test note has since been removed from the dashboard. This records the test outcome at the stated date. The two event correlations establish delivery for these requests. The full SQL comparison and 24-check database verification outputs were not provided, and continuous auth availability and browser frontend integration were not tested in this flow.

The earlier October test entries describe their original test environment. TEST-08 supplies the later team-backend auth and logging verification.

### TEST-22 Oracle preflight result — operator output

The staged copy at /tmp/matchwise-security-update.3fTDyq passed deployed-version promtool configuration syntax and all 38 scenarios for the twelve original rules. The validator also checked the sixteen-rule inventory. Live preflight returned CPU A=0, 5xx/login/404 A=0,D=1. Every Loki dashboard target, including the offset baseline and bounded logs, returned success with zero series at this check. Zero series is not a query error and does not independently prove complete ingestion; no matching non-health traffic was available in the queried windows. Rollout, cadence verification, Grafana evaluation and a real 404 trigger remain pending.

## Backend cadence rollout confirmed / Backend-gyakoriság igazolt

Operator supplied post-apply output: Grafana /api/health returned database=ok, version=13.2.1. Both blackbox_render_backend and blackbox_vercel_frontend targets report scrapeInterval=1m, scrapeTimeout=15s and health=up. Backend probe_success=1 at query timestamp 1795025266.993. This verifies active target configuration and a successful current HTTP probe; a long-term no-sleep guarantee is not claimed. New security panel rendering, four-rule group health and an actual 404 threshold trigger remain to be verified. No main merge was performed.

A frissítés utáni kimenet szerint a Grafana működik, a backend és a frontend targetje is 1m/15s beállítású és up állapotú. A backend probe_success=1. A percenkénti beállítás és a sikeres HTTP-próba igazolt; a hosszú távú elalvásmentesség nem garantált. Az új panelek megjelenése, a security csoport négy szabályának health értéke és a valódi 404-próba még ellenőrzendő. Main összevonás nem történt.
