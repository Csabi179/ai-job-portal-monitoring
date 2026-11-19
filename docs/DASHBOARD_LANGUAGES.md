# MatchWise dashboard languages

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

`scripts/build-bilingual-dashboards.py SOURCE_DIRECTORY OUTPUT_DIRECTORY` reads the two Hungarian provisioning files and generates four models plus `dashboard-language-manifest.json`. Hungarian titles receive the suffix once; generation is idempotent. The Hungarian files are the source of truth for measurements/layout. Update the explicit English title/description/label dictionaries when new UI fields are added, then regenerate the English models.

`scripts/check-bilingual-dashboards.py DIRECTORY` checks four distinct identities, exact visible English base names, HU suffixes, panel/grid/state equality, unchanged metric expressions/datasources/query modes, identical expanded default queries and filter values, unit dimensions, English UI coverage, table field names and language-specific data links. `--live` uses the existing read-only datasource auditor and deduplicates identical queries across language copies.

Four local tests passed: Hungarian panel preservation and idempotent generation; raw filter values that happen to match translated words; rejection of a changed English metric expression; read-only SQLite confirmation of four models and detection of a missing English model. Python and installer Bash syntax checks also passed. The English/Hungarian pairs contain 96 Unified and 73 Comparison JSON elements respectively, with unchanged refresh intervals and default time ranges.

## Installation on Oracle

Run the new pinned `scripts/install-bilingual-dashboards.sh FULL_COMMIT_SHA` helper from `/home/ubuntu/ai-job-monitoring`. This replaces the previously supplied manual command; do not run the old command first.

1. Stage and validate all four models; refuse unknown live file changes and symlinks. Existing unknown English files are not overwritten.
2. Back up all four file slots under `/home/ubuntu/monitoring-backups/dashboard-languages.*`, recording which English files did not previously exist.
3. If the prior final audit is still pending, invoke its pinned `75c65c454e89e6528bb93a46bdccaf3a597317b7` installer. It finishes the authorized audit, including the 12 offline promtool scenarios and read-only checks of the 180 original targets; it upgrades the receiver only if the earlier v2 upgrade is still missing. A receiver upgrade restarts its memory counters. If already prepared, the bilingual helper audits the four models directly, reusing identical datasource queries.
4. First install the two HU names and confirm them in Grafana's local SQLite dashboard storage using read-only access. Only then create the two English files under the unmarked base names, avoiding a provisioning-order/title conflict. If this rename cannot be confirmed automatically, restore the files rather than guessing that the old base names are free.
5. Confirm all four stored models, and check Grafana database health. This is provisioning verification, not a screenshot/rendering test.
6. On failure, restore existing files and remove only newly created English files. A separately completed receiver preparation remains installed and has its own printed backup. No Git reset, main merge, Caddy/Prometheus configuration change or paid service is involved.

The source audit is reused after the first preparation because every translated expanded query is verified identical to its Hungarian counterpart. Four dashboard objects do not create new collectors or generate business requests; normal panel queries run when dashboards are viewed.

After success, refresh Grafana with Ctrl+F5. Check the four names in the dashboard list, then use the language link to switch. Actual authenticated browser rendering still needs confirmation; the session has no Grafana login access. Raw application logs and credentials are not printed by the checks.

Magyar üzemeltetési megjegyzés: az előző telepítőparancsot nem kell külön futtatni. Az új telepítő az elmaradt előkészítést is elvégzi, majd a két HU és két angol dashboardot telepíti. Az angolok neve után nincs `EN` jelzés.
