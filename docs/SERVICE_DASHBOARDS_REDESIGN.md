# Service-grouped dashboards / Szolgáltatás szerinti dashboardok

> **Current deployment — 2026-11-19:** The operator confirmed all supplied changes were already applied on Oracle. Monitoring was merged into `main` (`10f43d1`); no reinstallation is required because of that merge. [Current status](DEPLOYMENT_STATUS.md). Earlier rollout entries are historical; commands are retained for future updates or recovery.

Applies to **MatchWise | Unified Monitoring** and **MatchWise · Service Comparison** (HU and EN copies; UIDs, filenames and the language links are unchanged).

> **Current update:** [selected-period frontend counts and removed host placeholders](FRONTEND_SELECTED_RANGE_COUNT.md). The original six-card design described below is superseded for frontend health (four cards) and the comparison scorecard (four common columns; collected CPU/memory cards in Load).

## English

### Unified Monitoring — one section per service

Rows follow the data flow: `00 Overview` → `01 Frontend (Vercel)` → `02 Backend (Render)` → `03 Database (Supabase)` → `04 Oracle VM` → `05 Log pipeline` → `06 Diagnostics`.

Every service section opens with the same two KPI strips (six tiles of equal size):

| Strip | Tiles |
| --- | --- |
| Health | Status · Check success rate (selected period) · Check duration · Data freshness · CPU (%) · Memory (%) |
| Load and errors | Traffic/min · 4xx/min · 5xx/min · Error rate (%) · Latency P95 · service-specific tile |

Frontend CPU/memory tiles show `n/a · not collected` (Vercel host metrics are not collected). The Oracle VM is the monitoring host, so its second strip shows host values (uptime, load, filesystem, free memory/disk, textfile collector). Detail rows (`01a`, `02a`–`02c`, `03a`, `04a`) are collapsed so their queries run only when opened. The previous panels (routes, endpoint table, authentication, PostgreSQL/PostgREST details, disk/network, log filters) are kept with their original IDs, so existing data links (`viewPanel=47`) still work.

### Service Comparison — the same panel for every service

Fixed colours: blue frontend · orange backend · green database · purple Oracle. Sections: `01 Scorecard` (4 services × 6 identical tiles: status, check duration, traffic/min, error rate, CPU, memory) → `02 Availability and freshness` (state timeline, success rate, freshness) → `03 Load` (traffic, CPU, memory, check duration, application latency P95, saturation bar gauge) → `04 Errors` (error rate, 5xx/min, 4xx/min, database error signals) → `05 Backend security signals` → `06 Telemetry and collection health` → collapsed `07 Advanced two-axis` and `08 Frontend details`.

Comparability rules:

- **Check duration** is an HTTP probe for frontend/backend and a Prometheus scrape for database/Oracle: the same idea (the monitor asking a healthy answer from the service), not application response time.
- **Error rate**: frontend/backend are 4xx+5xx shares of HTTP responses (API routes, health checks excluded); the database shows the rolled-back transaction share, which is not an HTTP error.
- **Traffic**: database traffic is committed transactions/min (internal services included), not backend requests.
- Where a service does not collect a signal the tile says `n/a`, never zero.

### Regenerating

`scripts/build-service-dashboards.py OUTPUT_DIR` writes all four files. Reviewed panels and expressions are copied from baseline revision `900002e` (`--baseline-ref`, or `--baseline-dir`); only layout, titles and the new comparison/strip queries are generated. It replaces `build-bilingual-dashboards.py` for these two dashboards (HU and EN are now emitted together, so no translation dictionary keyed by panel ID is needed). Because Grafana provisions these files with `allowUiUpdates: false`, edit the generator and regenerate rather than editing the JSON.

Validate with `scripts/check-service-dashboards.py DIR [--promtool PATH] [--loki URL]` (layout, unique IDs, HU/EN parity, identical service strips, variable and link references; optional promtool parse of every PromQL expression and execution of every LogQL expression against a throw-away Loki). `scripts/test_bilingual_dashboards.py` runs the offline tests.

The supplied package reports promtool parsing and synthetic Loki checks. Integration independently verifies generation, structure, language parity and Grafana-storage handling locally. Actual promtool parsing and live Prometheus/Loki query checks are mandatory installer steps on Oracle. A subsequent [authenticated visual audit](DASHBOARD_VISUAL_AUDIT.md) corrected presentation issues and previewed the candidate in the real Grafana renderer. Use the [single-command installation procedure](SERVICE_DASHBOARDS_INSTALLATION.md), which includes backups and rollback.

## Magyar

### Unified Monitoring — szolgáltatásonként egy szekció

A sorok az adatfolyamot követik: `00 Áttekintés` → `01 Frontend (Vercel)` → `02 Backend (Render)` → `03 Adatbázis (Supabase)` → `04 Oracle VM` → `05 Naplógyűjtés` → `06 Diagnosztika`.

Minden szolgáltatás ugyanazzal a két, hat egyforma csempéből álló KPI-sávval indul:

| Sáv | Csempék |
| --- | --- |
| Egészség | Állapot · Ellenőrzések sikeressége (kiválasztott időszak) · Ellenőrzés időtartama · Adatfrissesség · CPU (%) · Memória (%) |
| Terhelés és hibák | Forgalom/perc · 4xx/perc · 5xx/perc · Hibaarány (%) · Késleltetés P95 · szolgáltatásspecifikus csempe |

A frontend CPU/memória csempéi `n/a · nem gyűjtött` értéket mutatnak (a Vercel host-metrikái nincsenek gyűjtve). Az Oracle VM a monitoring gazdagép, ezért a második sávja host-értékeket mutat. A részletes sorok (`01a`, `02a`–`02c`, `03a`, `04a`) összecsukottak, így a lekérdezéseik csak kinyitáskor futnak. A korábbi panelek (útvonalak, végpont-táblázat, hitelesítés, PostgreSQL/PostgREST-részletek, lemez/hálózat, naplószűrők) az eredeti azonosítójukkal megmaradtak, a meglévő adatlinkek (`viewPanel=47`) működnek.

### Service Comparison — ugyanaz a panel minden szolgáltatásra

Fix színek: kék frontend · narancs backend · zöld adatbázis · lila Oracle. Szekciók: `01 Összegzőkártya` (4 szolgáltatás × 6 azonos csempe) → `02 Elérhetőség és adatfrissesség` → `03 Terhelés` → `04 Hibák` → `05 Backend biztonsági jelek` → `06 Telemetria és gyűjtés egészsége` → összecsukva `07 Haladó, két tengely` és `08 Frontend-részletek`.

Összehasonlíthatósági szabályok:

- Az **ellenőrzés időtartama** frontenden/backenden HTTP-próba, adatbázison/Oracle-ön Prometheus-scrape: nem alkalmazásszintű válaszidő.
- A **hibaarány** frontenden/backenden a 4xx+5xx arány (API-útvonalak, health nélkül); az adatbázisnál a visszagörgetett tranzakciók aránya, ami nem HTTP-hiba.
- Az adatbázis **forgalma** lezárt tranzakció/perc (belső szolgáltatásokkal együtt), nem backendkérés.
- Ahol egy szolgáltatás nem gyűjt adatot, ott `n/a` áll, soha nem nulla.

### Újragenerálás és ellenőrzés

`scripts/build-service-dashboards.py KIMENETI_MAPPA` mind a négy fájlt előállítja; a korábban átvizsgált panelek és kifejezések a `900002e` alapverzióból másolódnak. A JSON-t nem kézzel, hanem a generátor módosításával és újragenerálással érdemes változtatni (`allowUiUpdates: false`). Ellenőrzés: `scripts/check-service-dashboards.py MAPPA [--promtool ÚTVONAL] [--loki URL]`. A kapott csomag promtool- és szintetikus Loki-tesztekről számol be. Az integráció során a helyi generálási, szerkezeti, nyelvi és Grafana-tárolási teszteket ellenőriztük; az éles lekérdezés és a promtool-ellenőrzés az Oracle-telepítő kötelező lépése. A későbbi [böngészős audit](DASHBOARD_VISUAL_AUDIT.md) feltárta a megjelenítési hibákat, és ellenőrizte a javított előnézetet. [Telepítés egy parancsblokkal, mentéssel és visszaállítással](SERVICE_DASHBOARDS_INSTALLATION.md).
