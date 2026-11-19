# Service comparison implementation / Megvalósítási állapot

> **Current deployment — 2026-11-19:** The operator confirmed all supplied changes were already applied on Oracle. Monitoring was merged into `main` (`10f43d1`); no reinstallation is required because of that merge. [Current status](DEPLOYMENT_STATUS.md). Earlier rollout entries are historical; commands are retained for future updates or recovery.

Updated / Frissítve: 2026-11-19.
Repository: Csabi179/ai-job-portal-monitoring.
Branch / Ág: main; feat/service-comparison merged / összevonva 2026-11-19.
Baseline / Kiindulási commit: c12e4041776545428717647ad3947efe22036e0e.

## Delivered / Elkészült

| Step / Lépés | State / Állapot | Evidence / Bizonyíték |
|---|---|---|
| Render API capability and units / API és mértékegységek | DONE | Four nonempty CPU/memory/limit responses / Négy nem üres válasz |
| Resource collector and atomic .prom / Erőforrásgyűjtő | DONE | Live success, Node Exporter read errors=0 / Éles siker, beolvasási hiba=0 |
| systemd scheduling and Prometheus ingestion / Időzítő és beérkezés | DONE | Active timer and collection_success=1 / Aktív időzítő és sikerjelző |
| Four-column Service Comparison dashboard / Négyoszlopos dashboard | DONE for operator / Üzemeltetőnél működik | Operator screenshots / Képek |
| Three permanent resource/security rules / Három állandó új szabály | DEPLOYED / TELEPÍTVE | Live queries, corrected provisioning, screenshots / Lekérdezések, javított betöltés, képek |
| Synthetic Firing/Resolved test / Szintetikus teszt | PASS | Telegram screenshots for all three / Mindhárom Telegram-üzenetpár |
| Temporary test cleanup / Teszteltávolítás | CONFIRMED / VISSZAIGAZOLT | Operator confirmation / Üzemeltetői visszajelzés |
| Real ten-failed-login test / Valódi 10 hibás login | CONFIRMED FIRING / VISSZAIGAZOLT FIRING | Operator report and production alert text / Visszajelzés és riasztásszöveg |
| HU/EN guides, timing example, indexes and test records / Dokumentáció | UPDATED / FRISSÍTVE | This documentation commit / Jelen dokumentációs commit |

## Where to read / Leírások

- [Render resource collector / Erőforrásgyűjtő](RENDER_METRICS_COLLECTOR.md)
- [Dashboard](SERVICE_COMPARISON_DASHBOARD.md)
- [Three rules and rolling-window example / Három szabály és időablakpélda](SERVICE_COMPARISON_ALERTS.md)
- [Synthetic test and explicit deletion / Szintetikus teszt és törlés](SERVICE_COMPARISON_ALERT_TEST.md)
- [Dated evidence TEST-17–21 / Dátumozott tesztnapló](monitoring-tests.md#test-17-render-resource-collection)

## Operational state / Üzemeltetési állapot

The existing twelve outage/monitoring rules remain; service-comparison-security contains four rules, making sixteen permanent rules. The 404 addition and one-minute backend cadence were applied before the merge. TEST rules are temporary fixtures, not permanent provisioning source. Cleanup was confirmed by the operator; no separate post-cleanup API inventory was supplied.

A meglévő 12 kiesési/monitoring-szabály mellé négy erőforrás/biztonsági szabály került, összesen 16 állandó szabállyal. A 404-bővítés és a percenkénti backendmérés alkalmazása a merge előtt megtörtént. A TEST szabályok ideiglenesek; az eltávolítás visszaigazolt, külön API-leltár nem érkezett róla.

Oracle rollout used reviewed git show/file-copy commands from this feature branch. The resource script is installed at /usr/local/lib/matchwise/render-metrics-poll.py; service/timer units are installed under /etc/systemd/system. Changing the repository copy alone does not update the installed script. Dashboard and alert JSON were copied into the live checkout. Inspect local changes/untracked files before later branch switching or pulling. Do not use reset --hard or discard live files to resolve collisions.

Az Oracle-telepítés ellenőrzött fájlmásolásokkal történt a fejlesztési ágról. A külön telepített Python-példányt és systemd-egységeket frissítéskor külön is alkalmazni kell. Későbbi ágváltás előtt ellenőrizd a helyi módosításokat és nem verziókövetett fájlokat; ütközést ne oldj meg adatvesztő visszaállítással.

## Fixes recorded / Rögzített javítások

1. Initial probe hid unit names; revised output confirmed cpu/bytes. / Az első próba elrejtette a mértékegységet, a javított igazolta.
2. Collector HTTP 400 with explicit time-window parameters; matching the successful default-window probe fixed it. Exact rejected parameter was not isolated. / A külön időablak elhagyásával megoldódott a 400-as hiba; konkrét hibás paraméter nem lett elkülönítve.
3. Grafana startup rejected __dashboardUid__ without __panelId__. Incomplete optional links removed; validator assertion added; recovery confirmed. / A hiányos dashboard/panel hivatkozás javítva, indulás visszaigazolt.

## Remaining checks and integration / Hátralévő ellenőrzések

- New-dashboard Viewer access is unverified. / Az új dashboard Viewer-hozzáférése nincs ellenőrizve.
- Real CPU/5xx threshold breaches and missing-data/error branches are unverified. Synthetic tests prove the notification path, not source threshold behavior. / A valódi CPU/5xx küszöbpróbák és adathiányos ágak nem teszteltek.
- Exact real-login pending/receipt times and its resolved message were not supplied. / A valódi login-próba pontos idői és resolved üzenete nem érkezett.
- The merge review passed 52 Python tests, 38 alert PromQL scenarios, dashboard guard scenarios, 106 dashboard PromQL expressions, Prometheus configuration syntax and shell syntax. / A merge előtti ellenőrzésen 52 Python-teszt, 38 riasztási PromQL-eset, dashboardvédelmi tesztek, 106 dashboardkifejezés, a Prometheus-konfiguráció és a shellszintaxis is sikeres volt.
- Existing draw.io/SVG remains the twelve-rule baseline; current addition is documented in text. / A régi ábra a 12 szabályos kiindulást mutatja, az új rész szövegesen dokumentált.
- Main integration completed on 2026-11-19 by fast-forward to 10f43d1 after validation. No PR was needed. Runtime deployment was confirmed by the operator; the current Oracle Git checkout HEAD was not re-inventoried. / A main összevonás 2026-11-19-én, ellenőrzések után fast-forwarddal megtörtént. Külön PR nem kellett; a telepítést az üzemeltető visszaigazolta. Az Oracle checkout aktuális HEAD-jéről nem készült új leltár.

No secrets or raw application logs are recorded in these guides. / Titkos értékek és nyers alkalmazásnaplók nem kerültek a dokumentációba.

## Completed revision / Elkészült bővítés

Implemented on the same branch: eight security panels, guarded 404 burst rule, one-minute backend cadence, shorter timeout and three-minute freshness across rules/dashboards. The later validation and operator rollout completed; the monitoring merge was explicitly authorized and completed on November 19. No replay is required because of that merge. / Ugyanazon az ágon elkészült a nyolc biztonsági panel, a 404-riasztás és a percenkénti backend-próba. A későbbi ellenőrzések és az üzemeltetői alkalmazás megtörténtek; a monitoring main összevonása külön engedéllyel november 19-én lezárult. Emiatt nincs újrafuttatási feladat.

## Historical backend cadence evidence — November 18 / Korábbi backend-gyakorisági bizonyíték

Operator supplied post-apply output: Grafana /api/health returned database=ok, version=13.2.1. Both blackbox_render_backend and blackbox_vercel_frontend targets report scrapeInterval=1m, scrapeTimeout=15s and health=up. Backend probe_success=1 at query timestamp 1795025266.993. This verifies active target configuration and a successful current HTTP probe; a long-term no-sleep guarantee is not claimed. New security panel rendering, four-rule group health and an actual 404 threshold trigger remain to be verified. No main merge was performed.

A frissítés utáni kimenet szerint a Grafana működik, a backend és a frontend targetje is 1m/15s beállítású és up állapotú. A backend probe_success=1. A percenkénti beállítás és a sikeres HTTP-próba igazolt; a hosszú távú elalvásmentesség nem garantált. Az új panelek megjelenése, a security csoport négy szabályának health értéke és a valódi 404-próba még ellenőrzendő. Main összevonás nem történt.
