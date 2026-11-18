# MatchWise monitoringterv

> **Új, még nem telepített frissítés (2026-11-18):** a fejlesztési ág 16 állandó szabályt, 35 Service Comparison panelt és percenkénti backendpróbát tartalmaz (60s/15s/10s, 3 perces frissesség). A korábban igazolt éles állapot 15 szabályos; az új frissítés éles ellenőrzése és telepítése még hátravan. [Ellenőrzés és alkalmazás](SECURITY_OVERVIEW_AND_FREQUENT_PROBES.md).

[English version](monitoring-plan.en.md) · [Dokumentációjegyzék](README.md)

## Cél és felelősség

A monitoring az Oracle host, a Render backend, a Vercel frontend, a Supabase és a naplógyűjtés állapotát követi. Az üzemeltető felel a Render-hostolásért, az Oracle monitoringért, a naplógyűjtésért, a dashboardokért, a riasztásokért és a dokumentációért. Az alkalmazás üzleti funkcióit és az adatbázis-migrációkat a csapat felelősei kezelik.

A dashboard teljesítményt és kapacitást is megjelenít. Aktív értesítés kieséshez, megfigyelési hibához és három új backend-erőforrás/biztonsági jelzéshez tartozik; a pontos feltételeket a [riasztási terv](alerting-plan.md) tartalmazza.

## Komponensek és elhelyezés

| Hely | Komponens | Feladat |
|---|---|---|
| Oracle Cloud | Ubuntu ARM64 VM, 2 OCPU / 12 GB RAM | Monitoringhost |
| Docker Compose | Prometheus 3.13.2; Grafana 13.2.1 | Metrikatárolás, dashboardok és Grafana Alerting |
| Docker Compose | Node Exporter 1.11.1; Blackbox Exporter 0.28.0 | Host- és textfile-metrikák, HTTP-próbák |
| Docker Compose | Loki 3.7.9; Alloy 1.21.2 | Naplótárolás és továbbítás |
| Docker Compose, public profil | Caddy 2.11.9 | Nyilvános HTTPS-elérés a helyi Grafanához |
| Oracle systemd | Külön Python napló- és metrikagyűjtő, valamint logrotate, service/timer párokkal | Render Logs API, Render Metrics API és JSONL-forgatás |
| Render | matchwise-backend-monitoring-test.onrender.com | A csapat backendje, a main ág automatikus telepítésével az üzemeltető beállítása szerint |
| Vercel | https://www.matchwise.tech/ | Frontend |
| Supabase | uvopvarvelpabhmrqaaw | PostgreSQL, Auth, PostgREST és Metrics API |
| Telegram | AI Job Telegram contact point | Angol Firing és Resolved üzenetek a csapat csoportjába |
| GitHub | Csabi179/ai-job-portal-monitoring | Konfigurációk és dokumentáció verziókezelése |

A Compose alapból hat szolgáltatást választ ki; az üzemelő HTTPS-eléréshez a public profil Caddy-szolgáltatása is szükséges. Render Service ID: `srv-dbh7b1nb9u1s73e6hpbg`. A pontos éles backendcommit külön ellenőrizendő; a forráskód állapota nem bizonyít telepítést.

Szerkeszthető architektúra: [draw.io és SVG](architecture/README.md).

## Adatforrások és adatfolyamok

1. Linux → Node Exporter → Prometheus → Grafana: CPU, memória, lemez, hálózat, terhelés és uptime.
2. Blackbox → Prometheus → Grafana: backend `/api/health`, frontend főoldal, Loki `/ready` és Alloy `/-/healthy`.
3. Supabase Metrics API → Prometheus → Grafana: scrape-állapot, `pg_up`, adatbázis-, host- és PostgREST-metrikák.
4. Pino stdout → Render Logs API → Python collector → deduplikált JSONL → Alloy → Loki → Grafana.
5. Sikeres collector-futás → heartbeat textfile → Node Exporter → Prometheus → Grafana Alerting.
6. Böngésző → HTTPS → Caddy → Grafana bejelentkezés és jogosultság-ellenőrzés.
7. Grafana Alerting → Telegram Bot API → a csapat Telegram-csoportja.
8. Render Metrics API → külön Python erőforrásgyűjtő → .prom fájl → Node Exporter → Prometheus → Grafana.

A collector csak a konfigurált service `http_request` eseményeit és az engedélyezett mezőket tartja meg: level, event, reqId, method, route, statusCode, responseTimeMs és errorCode, kiegészítve Render-azonosítókkal és időbélyeggel. Az Alloy az eredeti Render-eseményidőt használja. A route mező gyakran /api előtag nélküli sablon; kérésbody, CV-tartalom, jelszó és token nem része a gyűjtött mezőknek.

## Mérési ütem és időablakok

| Adat | Gyakoriság vagy ablak |
|---|---|
| Node Exporter, Blackbox saját metrikák, Prometheus önscrape | 60 s |
| Backend HTTP | 60 s; scrape timeout 15 s; prober timeout 10 s |
| Frontend HTTP | 60 s; scrape timeout 15 s; prober timeout 10 s |
| Supabase | 60 s; scrape timeout 30 s; file discovery 60 s |
| Loki és Alloy health-próbák | 60 s; scrape timeout 15 s |
| Naplócollector | OnBootSec=2min; OnUnitInactiveSec=1min; AccuracySec=10s |
| Render erőforrásgyűjtő | OnBootSec=2min; OnUnitInactiveSec=2min; AccuracySec=5s; futásonként 4 API-kérés |
| Grafana szabályértékelés | 1 perc |
| Backend HTTP-riasztások frissessége | 3 perc; pending 2 perc |
| Frontend HTTP-riasztások frissessége | 3 perc; pending 2 perc |
| Dashboard állapotkártyák | Backend 3 perc; frontend 5 perc a Unified, 3 perc a Service Comparison dashboardon |
| Gördülő Pino P50/P95 | 15 perc; végponttáblázat P95 a teljes kiválasztott időből |
| Unified dashboard frissítése; provisioning fájlfigyelés | 1 perc; 30 s |

A collector az előző futás befejezése után ütemeződik; sikertelen API-kérés után a timer újra próbálkozik, de a Python-programon belül nincs automatikus HTTP-retry. Sikeres, üres gyűjtés is frissítheti a heartbeatet; ez önmagában nem igazolja a Loki-kézbesítést.

## Dashboardok és riasztások

Fő dashboard: **MatchWise | Unified Monitoring**, UID `matchwise-unified-overview`, repositorybeli verzió 8. Két bevezető panel és kilenc csoport 82 panelje összesen **84 panelt** alkot. Adatforrás-UID: `prometheus`, `loki`.

A három részletes dashboard megmarad üzemeltetési használatra: Infrastructure Overview, Application Availability és Backend Logs. A hat auth-számláló login-, logout- és regisztrációs eredményeket mutat; nem aktív felhasználók vagy munkamenetek számát. A legutóbbi auth-teszt statikus szövegét eltávolítottuk a bevezető panelből; a teszteredmény a tesztnaplóban marad.

A korábbi **12 kiesési/monitoring-szabály** csoportjai: infrastructure-monitoring (3), monitoring-components (2), render-backend-monitoring (2), render-log-collector-monitoring (1), supabase-monitoring (2), vercel-frontend-monitoring (2). Ehhez a service-comparison-security csoport 3 szabálya csatlakozik: Render CPU >80% 5 percig, legalább 5 nem health 5xx/5 perc 2 perces kivárással, illetve legalább 10 POST login 401/5 perc 2 perces kivárással. A 404-bővítéssel a fejlesztési ágban **16 állandó szabály** szerepel; az új szabály még telepítésre vár. RAM/lemez, P95, általános 4xx és a csendes alkalmazás továbbra sem aktív riasztási ok.

Új dashboard: **MatchWise · Service Comparison**. A működés, frissességi feltételek és korlátok a [dashboardleírásban](SERVICE_COMPARISON_DASHBOARD.md), a gördülő ablak példája a [riasztásleírásban](SERVICE_COMPARISON_ALERTS.md) található.

A Telegram-üzenetek angol nyelvűek. A contact point UID-ja `ai_job_telegram`; a célcsoportot a privát Oracle `GRAFANA_TELEGRAM_CHAT_ID` választja ki. Group wait 30 s, group interval 5 perc, repeat interval 4 óra; a Resolved értesítés engedélyezett.

## Tárolás és hozzáférés

- Prometheus: a `prometheus/prometheus.yml` szerint 7 nap vagy 2 GB, a korábban elért korlát alapján.
- Loki: 168 óra, engedélyezett compactor retentionnel.
- JSONL: `~/ai-job-monitoring/test-logs/render-backend.jsonl`; óránkénti méretellenőrzés, 20 MB küszöb és legfeljebb hét tömörítetlen archívum.
- Named volume-ok: prometheus_data, grafana_data, loki_data, alloy_data, caddy_data és caddy_config.
- SQLite és kurzor: `~/monitoring-private-state/`; frissítéskor megőrzendők.
- Titkok: Gitből kizárt `.env` és `~/monitoring-private-secrets/`; a Supabase privát fájljai read-only Prometheus mounton érhetők el.
- Nyilvános cím: **https://grafana-r0cecq.duckdns.org/**, Caddyn át, TCP 80/443 használatával; a Grafana 3000-es és a belső monitoringportok loopbacken maradnak.
- A csapat közös Viewer-fiókja csak a Unified Monitoring dashboardhoz kap dashboardjogot, Grafana Admin nélkül; Oracle- vagy SSH-hozzáférést nem kap.
- Az ACL-ek és a felhasználók a Grafana adatbázisában tárolódnak, a dashboard-JSON nem állítja be őket automatikusan.
- A dashboardjogosultság nem adatforrás-szintű elkülönítés: a Viewer az elérhető adatforrásokon más lekérdezéseket is futtathat.
- Secure cookie mellett böngészős bejelentkezéshez a HTTPS-címet kell használni; az SSH shell és a helyi health-lekérdezés továbbra is elérhető.

Eljárás és visszaállítás: [HTTPS-hozzáférés](GRAFANA_HTTPS_ACCESS.md). A tartós tárolás nem helyettesíti a biztonsági mentést; a tényleges megőrzést és visszaállíthatóságot külön kell ellenőrizni.

## CV és AI megfigyelésének előkészítése

A november 15-én átadott main forrásmásolat CV-feltöltést és Cloudinary-tárolást tartalmazott. A külön `feat-ajsp-4-cv-profile` branch Cloudflare Workers AI `@cf/openai/gpt-oss-20b` használatával profilkészítést valósít meg.

Az üzemeltető a `CLOUDFLARE_ACCOUNT_ID` és `CLOUDFLARE_API_TOKEN` változókat Renderen előre beállította. Ez nem Oracle-monitoringkonfiguráció; a szükséges Supabase-migrációért az adatbázis felelőse felel. A merge és az éles telepítés állapotát a monitoringrepo nem igazolja.

Backendmódosítás nélkül a `/cv/upload` és `/cv/:id/profile` HTTP-kérésszáma, státuszkódja, teljes feldolgozási ideje és reqId-ja használható. Külön AI-időtartam, tokenhasználat és pontos szolgáltatói hibatípus nem áll rendelkezésre; a profilvégpont 503-as válasza nem bizonyít Cloudflare-kiesést. Külön AI-panel vagy AI-riasztás még nincs.

## Ellenőrzések és korlátok

A [tesztnapló](monitoring-tests.md) külön rögzíti a dátumhoz kötött méréseket és az üzemeltetői visszajelzéseket. Igazolt a 12 szabály betöltése, a collector és Node Exporter Firing/Resolved kézbesítése, az angol értesítés, a HTTPS-bejelentkezés, a Viewer-hozzáférés működésének visszajelzése és a Telegram-csoportos átállás. November 18-án a három új szabály szintetikus Firing/Resolved tesztje és a tesztszabályok eltávolítása igazolt; a valódi login-szabályt az üzemeltető 10 hibás bejelentkezéssel is kipróbálta. A másik tíz eredeti szabály egyenkénti élő tesztje, a 4 órás ismétlés és a teljes infrastruktúra-helyreállítás nincs igazolva.

A backend tervezett percenkénti mintavétele is kihagyhat egy percnél rövidebb kiesést; az HTTP 200 nem teljes üzleti vagy böngészős funkcióteszt. Render CPU/RAM már gyűjtött; Vercel host CPU/RAM, böngészős hibák, Web Vitals és tracing nincsenek gyűjtve. A 16 szabály sem ellenőrzi külön a nyilvános Caddy/DNS/TLS útvonal egészét.

A teljes Oracle VM vagy Grafana kiesésekor a helyi Grafana nem tud megbízhatóan értesíteni; független külső ellenőrzés későbbi fejlesztés. Collector-siker, Loki-health és tényleges naplókézbesítés külön állapot. A hiányzó adat nem automatikusan nulla hiba vagy UP.

## Üzemeltetés és változáskövetés

Konfigurációmódosítás → validálás → GitHub-commit → Oracle `git pull --ff-only` → az érintett szolgáltatás alkalmazása → működés ellenőrzése. Konfliktust nem oldunk meg `reset --hard` paranccsal; volume-ot, SQLite-ot vagy kurzort nem törlünk rutinszerűen.

Az egyedi fájl-bind mount módosítása konténer-újralétrehozást igényelhet. A dashboard-JSON-t a Grafana 30 másodpercenként figyeli; a környezeti változók módosításához Grafana-újralétrehozás kell. Az Oracle `.env` nem módosítja a Render Environment értékeit. Tervezett projektlezárás: legkésőbb 2026. december 15.

## November 18-i telepítési kiegészítés

A fejlesztés a feat/service-comparison ágon verziózott. Az Oracle-re ellenőrzött fájlmásolással került fel; main merge és az éles checkout átváltása nem igazolt. A telepített erőforrásgyűjtő külön példánya /usr/local/lib/matchwise/render-metrics-poll.py; későbbi frissítéskor ezt is telepíteni kell. Az új dashboard Viewer-hozzáférése külön ellenőrzendő. Részletek: [megvalósítási állapot](SERVICE_COMPARISON_PLAN.md).
