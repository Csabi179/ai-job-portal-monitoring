# MatchWise dashboard languages

> **Current deployment — 2026-11-19:** The operator confirmed all supplied changes were already applied on Oracle. Monitoring was merged into `main` (`10f43d1`); no reinstallation is required because of that merge. [Current status](DEPLOYMENT_STATUS.md). Earlier rollout entries are historical; commands are retained for future updates or recovery.

> **Installed service-grouped layout:** the operator confirmed the four dashboards were applied. The [installer](SERVICE_DASHBOARDS_INSTALLATION.md) is retained for future changes or recovery, not as a post-merge task. The older layout/generation procedure below is rollout history; frontend details are section 08 in the new comparison layout.

> **Historical Grafana 13 incident:** an earlier retry restored its files after checking the obsolete legacy table. The [current-storage verifier fix](GRAFANA13_PROVISIONING_VERIFICATION.md) corrected that path; the operator subsequently applied the supplied updates. This is not an outstanding retry request.


The two Hungarian dashboards are retained. Separate English dashboards use the same measurements, defaults and layout. Only the Hungarian titles have a `HU` suffix; the English titles have no language suffix.

| Language | Dashboard title | UID |
| --- | --- | --- |
| Hungarian | MatchWise \| Unified Monitoring HU | matchwise-unified-overview |
| Hungarian | MatchWise · Szolgáltatások összehasonlítása HU | matchwise-service-comparison |
| English | MatchWise \| Unified Monitoring | matchwise-unified-overview-en |
| English | MatchWise · Service Comparison | matchwise-service-comparison-en |

The Hungarian dashboards keep the existing UIDs and provisioning filenames, so existing bookmarks continue to resolve. The English copies have separate internal UIDs/files; `-en` is not part of their visible titles. A language-switch dashboard link preserves the selected time range. English panel data links and inline dashboard links point to English dashboard UIDs, so opening logs from an English table does not switch back to Hungarian.

English localization covers panel and row titles, descriptions, Markdown, legends, null/status mappings, custom unit suffixes, axis labels, variable labels/choice text and table column/override names. Metric names, PromQL/LogQL expressions, request/status/route identifiers, datasource UIDs and raw variable values are preserved. The original Hungarian panel content is unchanged. No frontend deployment or new data collection is required.

The previously requested removal of the comparison dashboard's backend-log and generic data-source/methodology sections remains in both languages. Frontend details remain section **06**. The Unified dashboard's own diagnostic logs remain available.

## Generation and validation

> **Superseded for these two dashboards:** `scripts/build-service-dashboards.py` now emits both languages together (see [Service-grouped dashboards](SERVICE_DASHBOARDS_REDESIGN.md)); the translation-dictionary pipeline described next is retained only as history.

`scripts/build-bilingual-dashboards.py SOURCE_DIRECTORY OUTPUT_DIRECTORY` reads the two Hungarian provisioning files and generates four models plus `dashboard-language-manifest.json`. Hungarian titles receive the suffix once; generation is idempotent. The Hungarian files are the source of truth for measurements/layout. Update the explicit English title/description/label dictionaries when new UI fields are added, then regenerate the English models.

`scripts/check-bilingual-dashboards.py DIRECTORY` checks four distinct identities, exact visible English base names, HU suffixes, panel/grid/state equality, unchanged metric expressions/datasources/query modes, identical expanded default queries and filter values, unit dimensions, English UI coverage, table field names and language-specific data links. `--live` uses the existing read-only datasource auditor and deduplicates identical queries across language copies.

Four local tests passed: Hungarian panel preservation and idempotent generation; raw filter values that happen to match translated words; rejection of a changed English metric expression; read-only SQLite confirmation of four models and detection of a missing English model. Python and installer Bash syntax checks also passed. The English/Hungarian pairs contain 96 Unified and 73 Comparison JSON elements respectively, with unchanged refresh intervals and default time ranges.

## Installation on Oracle

Run the new pinned `scripts/install-bilingual-dashboards.sh FULL_COMMIT_SHA` helper from `/home/ubuntu/ai-job-monitoring`. This replaces the previously supplied manual command; do not run the old command first.

1. Stage and validate all four models; refuse unknown live file changes and symlinks. Existing unknown English files are not overwritten.
2. Back up all four file slots under `/home/ubuntu/monitoring-backups/dashboard-languages.*`, recording which English files did not previously exist.
3. If the prior final audit is still pending, invoke the final-audit installer from the same current pinned revision (the `75c65c454e89e6528bb93a46bdccaf3a597317b7` models remain comparison baselines). It finishes the authorized audit, including the 12 offline promtool scenarios and read-only checks of the 180 original targets; it upgrades the receiver only if the earlier v2 upgrade is still missing. A receiver upgrade restarts its memory counters. If already prepared, the bilingual helper audits the four models directly, reusing identical datasource queries.
4. First install the two HU names and confirm them in Grafana's local SQLite dashboard storage using read-only access. Only then create the two English files under the unmarked base names, avoiding a provisioning-order/title conflict. If this rename cannot be confirmed automatically, restore the files rather than guessing that the old base names are free.
5. Confirm all four stored models, and check Grafana database health. This is provisioning verification, not a screenshot/rendering test.
6. On failure, restore existing files and remove only newly created English files. A separately completed receiver preparation remains installed and has its own printed backup. No Git reset, main merge, Caddy/Prometheus configuration change or paid service is involved.

The source audit is reused after the first preparation because every translated expanded query is verified identical to its Hungarian counterpart. Four dashboard objects do not create new collectors or generate business requests; normal panel queries run when dashboards are viewed.

After success, refresh Grafana with Ctrl+F5. Check the four names in the dashboard list, then use the language link to switch. Authenticated browser rendering was subsequently audited, and the operator later confirmed all supplied updates were applied. This historical installation procedure is not a new post-merge requirement. Raw application logs and credentials are not printed by the checks.

Magyar üzemeltetési megjegyzés: a telepítés azóta megtörtént; a main merge miatt egyik telepítőparancsot sem kell újra futtatni. Az itt megőrzött eljárás későbbi frissítéshez vagy helyreállításhoz használható. Az angol dashboardnevek után nincs `EN` jelzés.
