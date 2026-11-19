# Installing the supplied service-grouped dashboards

> **Current deployment — 2026-11-19:** The operator confirmed all supplied changes were already applied on Oracle. Monitoring was merged into `main` (`10f43d1`); no reinstallation is required because of that merge. [Current status](DEPLOYMENT_STATUS.md). Earlier rollout entries are historical; commands are retained for future updates or recovery.

The supplied installer updated both MatchWise dashboards in Hungarian and English; the operator confirmed every supplied change was applied on Oracle. Existing UIDs, bookmarks, names and language links remain unchanged. Hungarian names end in `HU`; English names have no suffix. The implementation is now merged into `main` through commit `10f43d1c6b770a0ac5ca91a297d83d0b3dad3062`. The merge does not require reinstallation.

## Future installation or recovery only

The existing installation is complete according to the operator. Do not run the following block just because the branch was merged. It is retained for a fresh host, a deliberately chosen future update or recovery; use the full reviewed runtime commit SHA for that operation:

```bash
(
set -euo pipefail
cd /home/ubuntu/ai-job-monitoring
git fetch origin feat/service-comparison
traffic_ref=FULL_INTEGRATION_COMMIT_SHA
traffic_helper="$(mktemp /tmp/matchwise-service-dashboards.XXXXXX)"
git show "$traffic_ref:scripts/install-service-dashboards.sh" > "$traffic_helper"
bash -n "$traffic_helper"
bash "$traffic_helper" "$traffic_ref"
)
```

The installer:

1. Stages the pinned models and helpers without switching branches or updating the working tree from Git. Unknown dashboard edits cause a stop.
2. Checks all four models and runs ten offline tests, including deterministic generation, selected-period API counts and Grafana 13 authoritative-storage verification. Parses 106 distinct PromQL expressions using the existing Prometheus container's `promtool`; the temporary rule file is never installed.
3. If the previous bilingual installation is still pending, completes it using revision `900002e74e6889515b44bf4ac2d4a6ecd110e0b4`. That installer may finish the previously requested receiver-v2 preparation. This baseline step has its own backup and remains completed if the subsequent design trial stops.
4. Checks receiver v2 and Grafana health. Executes all 500 candidate target entries, reusing duplicate queries, against local Prometheus/Loki. Graphs use one hour of history; raw-log checks request at most five rows and never print their contents. Empty results mean missing matching observations, not proof of zero traffic. Intentional `n/a` queries are empty.
5. Backs up the four previous models and installs only the four dashboard JSON files. Waits up to 90 seconds for Grafana provisioning and verifies the models through read-only access to Grafana 13's authoritative dashboard storage. No restart is required.

On a trial installation failure it attempts to restore and verify the previous four models automatically. On success it prints a **one-command rollback** with the exact backup path. Keep that path. Rollback stops if unrelated dashboard edits were made after installation, instead of overwriting them.

After `PASS`, refresh Grafana with **Ctrl+F5** and check both languages. An authenticated browser audit subsequently identified and corrected presentation problems; see [visual audit](DASHBOARD_VISUAL_AUDIT.md). Candidate models were previewed with read-response substitution in an isolated browser, without writing server models. The installer still runs its full server-side query/provisioning checks on Oracle.

## Package and integration checks

The supplied patch applies cleanly to revision `900002e`; its eleven output files match the ZIP after normalizing line endings. Input SHA-256:

- Patch: `2f218a065f152e4ac95801e6ac34a7b0934bfdc26e2046b8f2e35b66fbe9dd02`
- ZIP: `5ff8ffbbebac8189335aec5567078923977ad4004c0a7b2323d9b566ecb0679c`

Integration guards the backend error-share denominator against zero traffic, corrects clipped titles and makes generated JSON line endings deterministic. Frontend host CPU/memory placeholders have since been removed, with a visible explanation at the top of both dashboards. The Unified API-calls card now counts the selected period; see [semantics and limits](FRONTEND_SELECTED_RANGE_COUNT.md). Structural checks cover all service sections, language/filter parity and exact existing names/UIDs. Ten dashboard tests and twelve existing Grafana-storage regression tests pass locally. Both shell helpers pass `bash -n`.

The layout follows [the supplied service-grouped design](SERVICE_DASHBOARDS_REDESIGN.md). Frontend details now appear in section **08** of the comparison dashboard; earlier section-06 instructions refer to the previous layout. The comparison's removed generic backend-log and measurement-guide sections are not reintroduced. Unified Monitoring retains its own diagnostic detail rows.

## Magyar röviden

Az üzemeltető a négy nézet frissítéseit már alkalmazta; a main merge miatt sem ezt, sem a korábbi telepítőt nem kell ismét futtatni. A fenti parancsblokk új gép, későbbi frissítés vagy helyreállítás esetére marad meg. A korábbi kétnyelvű telepítőt külön nem kell futtatni. Ismeretlen helyi dashboard-módosításnál megáll; telepítés előtt mentést készít, hiba esetén megpróbál visszaállni. A sikeres futás végén kiírja az egysoros visszaállítási parancsot. A magyar nevek végén megmarad a `HU`, az angol neveken nincs jelzés. Sikeres ellenőrzés után frissítsd a Grafanát **Ctrl+F5**-tel; a tényleges böngészős megjelenést ezután lehet véglegesen megítélni.
