# Service comparison implementation / Megvalósítási állapot

> **Pending update (November 18, 2026):** branch configuration now has sixteen permanent rules, thirty-five Service Comparison panels and one-minute backend probes (60s/15s/10s, three-minute freshness). The previously verified live deployment has fifteen rules; validation and rollout of this update are pending. [Validation and rollout](SECURITY_OVERVIEW_AND_FREQUENT_PROBES.md).

Updated / Frissítve: 2026-11-18.
Repository: Csabi179/ai-job-portal-monitoring.
Branch / Ág: feat/service-comparison.
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

The existing twelve outage/monitoring rules remain; service-comparison-security adds three, making fifteen permanent rules. TEST rules are temporary fixtures, not permanent provisioning source. Cleanup was confirmed by the operator; no separate post-cleanup API inventory was supplied.

A meglévő 12 kiesési/monitoring-szabály mellé három új került, összesen 15 állandó szabállyal. A TEST szabályok ideiglenesek; az eltávolítás visszaigazolt, külön API-leltár nem érkezett róla.

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
- The original promtool suite was not rerun here because required tools were unavailable. Local collector/helper tests and structure checks passed. / A régi promtool csomag itt nem futott újra; helyi collector/helper tesztek és szerkezeti ellenőrzések sikeresek.
- Existing draw.io/SVG remains the twelve-rule baseline; current addition is documented in text. / A régi ábra a 12 szabályos kiindulást mutatja, az új rész szövegesen dokumentált.
- Main merge, final pull request review and exact current live checkout HEAD are not established. / Main merge, végső PR-ellenőrzés és az éles checkout pontos HEAD-je nincs igazolva.

No secrets or raw application logs are recorded in these guides. / Titkos értékek és nyers alkalmazásnaplók nem kerültek a dokumentációba.

## Next requested revision / Következő kért módosítás

Implemented on the same branch: eight security panels, guarded 404 burst rule, one-minute backend cadence, shorter timeout and three-minute freshness across rules/dashboards. Full updated promtool suite and live Loki checks are the next operator step. No merge is planned now, as requested. / Ugyanazon az ágon elkészült a nyolc biztonsági panel, a 404-riasztás és a percenkénti backend-próba. Következő lépés a frissített tesztcsomag és lekérdezések Oracle-ellenőrzése. Összevonás most nincs tervben.

## Backend cadence rollout confirmed / Backend-gyakoriság igazolt

Operator supplied post-apply output: Grafana /api/health returned database=ok, version=13.2.1. Both blackbox_render_backend and blackbox_vercel_frontend targets report scrapeInterval=1m, scrapeTimeout=15s and health=up. Backend probe_success=1 at query timestamp 1795025266.993. This verifies active target configuration and a successful current HTTP probe; a long-term no-sleep guarantee is not claimed. New security panel rendering, four-rule group health and an actual 404 threshold trigger remain to be verified. No main merge was performed.

A frissítés utáni kimenet szerint a Grafana működik, a backend és a frontend targetje is 1m/15s beállítású és up állapotú. A backend probe_success=1. A percenkénti beállítás és a sikeres HTTP-próba igazolt; a hosszú távú elalvásmentesség nem garantált. Az új panelek megjelenése, a security csoport négy szabályának health értéke és a valódi 404-próba még ellenőrzendő. Main összevonás nem történt.
