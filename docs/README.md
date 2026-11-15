# MatchWise documentation / dokumentáció

Updated November 16, 2026. The guides describe current repository configuration and operator-confirmed deployment; dated test records preserve what was actually checked. Hungarian originals and English editions are listed below.

Frissítve: 2026. november 16. Az útmutatók a jelenlegi konfigurációt és az üzemeltető által visszaigazolt telepítést írják le; a dátumozott tesztnapló az elvégzett ellenőrzéseket őrzi.

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

The editable draw.io/SVG architecture uses Hungarian labels and is accompanied by an English guide. It includes Caddy HTTPS access, the Telegram team group, 12 alert rules and the identified AI provider as an unverified deployment path.

English Telegram delivery is evidenced by the Node Exporter test; the operator later confirmed the team-group destination. Rule UIDs, conditions and timing remain unchanged. See [TEST-11](monitoring-tests.md#test-11-node-exporter-delivery), [TEST-13](monitoring-tests.md#test-13-telegram-group-delivery), and the [alerting runbook](alerting-plan.en.md#deployment).

**Translation maintenance:** when changing a paired document, update both language editions, including commands, selectors, timing values and evidence status. Preserve stable rule UIDs and test references. Never infer new successful tests from a translation. Update this index when adding another Hungarian document and its English edition.
