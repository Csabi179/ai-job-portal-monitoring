# Installing the supplied service-grouped dashboards

This trial updates both MatchWise dashboards in Hungarian and English. Existing UIDs, bookmarks, names and language links remain unchanged. Hungarian names end in `HU`; English names have no suffix. The monitoring branch remains `feat/service-comparison`.

## Oracle installation

Use the full integration commit SHA supplied with the release instructions:

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
2. Checks all four models and runs eight offline tests, including deterministic generation and Grafana 13 authoritative-storage verification. Parses 105 distinct PromQL expressions using the existing Prometheus container's `promtool`; the temporary rule file is never installed.
3. If the previous bilingual installation is still pending, completes it using revision `900002e74e6889515b44bf4ac2d4a6ecd110e0b4`. That installer may finish the previously requested receiver-v2 preparation. This baseline step has its own backup and remains completed if the subsequent design trial stops.
4. Checks receiver v2 and Grafana health. Executes all 508 candidate target entries, reusing duplicate queries, against local Prometheus/Loki. Graphs use one hour of history; raw-log checks request at most five rows and never print their contents. Empty results mean missing matching observations, not proof of zero traffic. Intentional `n/a` queries are empty.
5. Backs up the four previous models and installs only the four dashboard JSON files. Waits up to 90 seconds for Grafana provisioning and verifies the models through read-only access to Grafana 13's authoritative dashboard storage. No restart is required.

On a trial installation failure it attempts to restore and verify the previous four models automatically. On success it prints a **one-command rollback** with the exact backup path. Keep that path. Rollback stops if unrelated dashboard edits were made after installation, instead of overwriting them.

After `PASS`, refresh Grafana with **Ctrl+F5** and check both languages. Model/layout validation cannot establish actual browser rendering. No authenticated visual rendering or live Oracle query audit was available on the development machine; server checks run when this installer is executed.

## Package and integration checks

The supplied patch applies cleanly to revision `900002e`; its eleven output files match the ZIP after normalizing line endings. Input SHA-256:

- Patch: `2f218a065f152e4ac95801e6ac34a7b0934bfdc26e2046b8f2e35b66fbe9dd02`
- ZIP: `5ff8ffbbebac8189335aec5567078923977ad4004c0a7b2323d9b566ecb0679c`

Integration corrects swapped Hungarian/English Vercel CPU/memory explanations, guards the backend error-share denominator against zero traffic, shortens two Hungarian KPI titles and makes generated JSON line endings deterministic. Structural checks additionally cover all four service sections, language/filter parity and exact existing names/UIDs. Eight dashboard tests and twelve existing Grafana-storage regression tests pass locally. Both shell helpers pass `bash -n`.

The layout follows [the supplied service-grouped design](SERVICE_DASHBOARDS_REDESIGN.md). Frontend details now appear in section **08** of the comparison dashboard; earlier section-06 instructions refer to the previous layout. The comparison's removed generic backend-log and measurement-guide sections are not reintroduced. Unified Monitoring retains its own diagnostic detail rows.

## Magyar röviden

A fenti egyetlen parancsblokk telepíti a négy új nézetet. A korábbi kétnyelvű telepítőt külön nem kell futtatni. Ismeretlen helyi dashboard-módosításnál megáll; telepítés előtt mentést készít, hiba esetén megpróbál visszaállni. A sikeres futás végén kiírja az egysoros visszaállítási parancsot. A magyar nevek végén megmarad a `HU`, az angol neveken nincs jelzés. Sikeres ellenőrzés után frissítsd a Grafanát **Ctrl+F5**-tel; a tényleges böngészős megjelenést ezután lehet véglegesen megítélni.
