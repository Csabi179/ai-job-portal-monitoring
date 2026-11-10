# MatchWise documentation / dokumentáció

Updated November 10, 2026. Hungarian originals are preserved; their full English editions are listed below. Existing English guides are shared rather than duplicated. Both editions retain historical evidence and distinguish later operator verification from tests still pending.

Frissítve: 2026. november 10. A magyar eredetik megmaradtak, külön angol változattal. A már angol dokumentumokat nem duplikáljuk. A történeti megállapításokat a későbbi ellenőrzésektől külön kezeljük.

| Document / dokumentum | English | Magyar |
|---|---|---|
| Grafana HTTPS team access / Grafana HTTPS csapathozzáférés | [English](GRAFANA_HTTPS_ACCESS.en.md) | [Magyar](GRAFANA_HTTPS_ACCESS.md) |
| Monitoring plan / Monitoringterv | [English](monitoring-plan.en.md) | [Magyar](monitoring-plan.md) |
| Commands to test all 12 rules / Mind a 12 szabály tesztparancsai | [English](alert-rule-tests.en.md) | [Magyar](alert-rule-tests.md) |
| Alerting plan and Oracle rollout / Riasztási terv és Oracle-frissítés | [English](alerting-plan.en.md) | [Magyar](alerting-plan.md) |
| Render logging runbook / Render-naplózási leírás | [English](RENDER_LOGGING_RUNBOOK.en.md) | [Magyar](RENDER_LOGGING_RUNBOOK.md) |
| Architecture and data flow / Architektúra és adatáramlás | [English](architecture/README.en.md) | [Magyar](architecture/README.md) |
| Architecture and operations guide | [Existing English guide](MONITORING_GUIDE.md) | — |
| Installation and recovery guide | [Existing English guide](installation-guide.md) | — |
| Supabase metrics | [Existing English guide](SUPABASE_METRICS.md) | — |
| Verification and test evidence | [Shared English test log](monitoring-tests.md) | — |

The architecture guide's draw.io/SVG assets retain their original Hungarian labels as a dated diagram snapshot. The English architecture document explains every component, connection and notation. The original diagram's nine-rule label is historical; the current active set has 12 rules.

Telegram notifications, alert titles and descriptions are English after deploying the language update. Rule UIDs, queries, thresholds, pending times and routing are unchanged. The English [alerting runbook](alerting-plan.en.md#deployment) includes the Grafana-only update steps.

**Translation maintenance:** when changing a paired document, update both language editions, including commands, selectors, timing values and evidence status. Preserve stable rule UIDs and test references. Never infer new successful tests from a translation. Update this index when adding another Hungarian document and its English edition.
