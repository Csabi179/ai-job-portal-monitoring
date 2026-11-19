# Grafana 13 provisioning verification fix

> **Current deployment — 2026-11-19:** The operator confirmed all supplied changes were already applied on Oracle. Monitoring was merged into `main` (`10f43d1`); no reinstallation is required because of that merge. [Current status](DEPLOYMENT_STATUS.md). Earlier rollout entries are historical; commands are retained for future updates or recovery.

The reported installation completed all datasource checks: **180 targets, 143 successful unique queries, 48 empty results, zero query failures**. The four bilingual and six audit tests passed, and promtool reported success. It stopped while confirming provisioning, then restored the original dashboard file slots. The four new language models were therefore not confirmed installed.

## Cause and correction

The verifier read the legacy `dashboard` SQL table. Grafana 13 migrates dashboards into unified storage and the legacy table can remain stale. The old timeout did not reliably establish whether the active dashboard had been loaded.

The corrected verifier prefers the current `resource` table. It selects only the requested dashboard names in `dashboard.grafana.app/dashboards`, restricted to organization 1's `default`/`org-1` namespace forms and non-deleted resource actions. It reads the Dashboard resource's Classic/V1 `spec` and performs the existing strict title, panel, layout, row-state, expression and datasource checks. Deleted resources, identity mismatches, ambiguous namespace aliases and unsupported shapes cannot produce success. V2 element/layout models are explicitly unsupported rather than silently accepted as Classic models.

If unified storage exists, fresh legacy rows cannot mask a missing or incorrect current model. Legacy reads remain available only when neither unified resources nor a unified migration marker are present. SQL access remains read-only, with query-only mode and parameterized names; no migrations, resource writes, user-table access or credential changes occur.

The second bug was in the caller: the bilingual installer always invoked the previous pinned preparation installer, which reintroduced the old verifier. It now invokes the final-audit installer and verifier from the **same current pinned revision**. The previous reviewed model commits remain baselines only. The final-audit guard also recognizes the reviewed pre-language model files.

Missing storage confirmation is no longer accepted as a completed installation. Both installers require a successful verification and otherwise restore their dashboard files. On timeout, the verifier now prints the selected storage source and bounded field/panel differences without dumping queries or application logs.

## Historical validation and retry procedure

Local checks passed: 12 new storage/caller regression tests, the existing four bilingual tests and six final-audit tests, plus both installer Bash syntax checks. Regression cases include stale legacy versus current unified data, refusing legacy false positives, namespace/resource scoping, wrapped Classic specs, deleted resources, unsupported V2 schemas, migration markers, safe diagnostics and the current-revision preparation call.

No dashboard JSON, title, language assignment, metric query or receiver behavior changed in this fix. The original HU UIDs and the unmarked English base names remain as requested.

At that stage the prescribed recovery was to retry the newly pinned `scripts/install-bilingual-dashboards.sh`; do not rerun revision `9437a1d7a2d8f01f9633bfbf7c2689a94aab3d34`, whose preparation still used the old verifier. The operator has since confirmed the supplied updates were applied. The retry instructions are retained as incident history and recovery guidance, not as a pending task after this merge. Local regression tests alone do not prove an installed/rendered dashboard.

Primary sources: [Grafana 13 upgrade guide](https://grafana.com/docs/grafana/latest/upgrade-guide/upgrade-v13/upgrade-v13.0/), [Grafana 13.2.1 resource table read](https://github.com/grafana/grafana/blob/v13.2.1/pkg/storage/unified/sql/data/resource_read.sql), and [Classic dashboard provisioning wrapper](https://github.com/grafana/grafana/blob/v13.2.1/pkg/services/dashboards/service/dashboard_service.go).
