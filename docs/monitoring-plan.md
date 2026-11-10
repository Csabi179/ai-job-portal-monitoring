# MatchWise – monitoringterv és megvalósítási állapot

[English version](monitoring-plan.en.md) · [Dokumentációjegyzék](README.md)

> Kiegészítés, 2026. november 10.: az alábbi magyar szöveg az eredeti dokumentálási állapotot is megőrzi. Azóta az üzemeltető alkalmazta a 12 szabályos konfigurációt, és megérkezett a collector Telegram Firing és Resolved üzenete. A többi szabály egyenkénti kézbesítési tesztje nem történt meg. A későbbi angol üzenetszöveg-frissítés még külön alkalmazandó. Részletek: [TEST-10](monitoring-tests.md#test-10--oracle-rollout-and-collector-telegram-delivery-2026-11-10).

Dokumentálás: **2026. november 10.** Ez a már megvalósított rendszer visszamenőleges leírása, nem a fejlesztés előtt készült terv. Kiindulási repository: `374f74eab098deccfd408887bbef5db314c83223`. A konfiguráció és a korábban rögzített bizonyítékok ellenőrizhetők; az Oracle VM jelenlegi futó állapotát ezen a napon nem értük el.

## Cél és felelősség

Az egyetemi MatchWise állásportál szolgáltatásainak, az Oracle hostnak és a megfigyelés működésének követése. Az üzemeltető feladata a Render-hostolás, az Oracle monitoring, a naplógyűjtés, dashboardok, riasztások és dokumentáció. Az üzleti backendfunkciókat és a frontendet a csapat fejleszti.

A dashboardon teljesítmény és kapacitás is látható. Az aktív értesítések kizárólag kiesést vagy a megfigyelés hibáját jelzik; részletek a [riasztási tervben](alerting-plan.md).

## Komponensek és helyük

| Hely | Komponens | Szerep |
|---|---|---|
| Oracle Cloud | Ubuntu 24.04 ARM64 VM; korábban dokumentált 2 OCPU / 12 GB RAM | Monitoringhost |
| Oracle Docker Compose | Prometheus 3.13.2; Grafana 13.2.1 | Metrikák tárolása; dashboard és Grafana Alerting |
| Oracle Docker Compose | Node Exporter 1.11.1; Blackbox Exporter 0.28.0 | Hostmetrikák/textfile; HTTP-próbák |
| Oracle Docker Compose | Loki 3.7.9; Alloy 1.21.2 | Naplótárolás; fájlbeolvasás és továbbítás |
| Oracle systemd | Python collector és logrotate, saját service/timer párokkal | Render Logs API gyűjtés és JSONL-forgatás |
| Render Free | `matchwise-backend-monitoring-test.onrender.com` | A csapat backendje ugyanazon korábbi szolgáltatáson |
| Vercel | `https://www.matchwise.tech/` | Frontend |
| Supabase | `uvopvarvelpabhmrqaaw` | PostgreSQL, Auth, PostgREST, Metrics API |
| Telegram | AI Job Telegram | Riasztási és helyreállási értesítés |
| GitHub | Csabi179/ai-job-portal-monitoring | Konfiguráció és dokumentáció változáskövetése |

Render Service ID: `srv-dbh7b1nb9u1s73e6hpbg`. A szolgáltatás neve történeti; a november 9-i bizonyíték szerint a csapat backendjének main ágát futtatja. A pontos akkor telepített backendcommit nem ismert. A helyi backendforrásmásolat november 9-i; e dokumentálási feladat nem ellenőrizte újra a backendmain tartalmát.

Az architektúra szerkeszthető ábrája: [draw.io és SVG](architecture/README.md). Az AI-szolgáltató és a teljes frontend–backend kapcsolat ábrabeli tervezett jelölését új telepítési bizonyíték nélkül nem tekintjük megvalósultnak.

## Adatforrások és adatút

1. Node Exporter → Prometheus → Grafana: CPU, memória, lemez, hálózat, terhelés, uptime, textfile állapot.
2. Blackbox → Prometheus → Grafana: backend `/api/health`, frontend főoldal; az új konfigurációban Loki `/ready` és Alloy `/-/healthy`.
3. Supabase Metrics API → Prometheus → Grafana: scrape állapot, `pg_up`, adatbázis- és hostmetrikák, PostgREST pool.
4. Pino JSON stdout → Render Logs API → Python collector → deduplikált JSONL → Alloy → Loki → Grafana.
5. Sikeres systemd oneshot → heartbeat textfile → Node Exporter → Prometheus → Grafana Alerting → Telegram.

A collector `event=http_request` és a konfigurált `service` alapján szűr. Fontos mezők: reqId, method, route, statusCode, responseTimeMs; hozzáadott Render-időbélyeg és azonosítók. Alloy az eredeti Render-időt használja. Az auth útvonalak gyakran /api előtag nélkül szerepelnek a naplóban. Jelszó, token, Authorization fejléc, CV és kérésbody nem kerülhet a naplóba.

## Gyakoriság és időablakok

| Adat | Gyakoriság / ablak |
|---|---|
| Node Exporter, Blackbox saját metrikák, Prometheus önscrape | 60 s |
| Backend HTTP | 30 perc; scrape timeout 110 s; prober timeout 100 s |
| Frontend HTTP | 60 s; scrape timeout 15 s; prober timeout 10 s |
| Supabase | 60 s; scrape timeout 30 s; file discovery frissítés 60 s |
| Új Loki/Alloy HTTP health-próbák | 60 s; scrape timeout 15 s |
| Collector | OnBootSec=2min; OnUnitInactiveSec=1min; AccuracySec=10s |
| Grafana szabályértékelés | 1 perc |
| Új backendriasztás frissessége | 40 perc; pending 2 perc |
| Új frontendriasztás frissessége | 3 perc; pending 2 perc |
| Dashboard állapotkártyák | Backend 40 perc; frontend 5 perc |
| Pino gördülő P50/P95 | 15 perc; végponttáblázat P95 a teljes kiválasztott időből |
| Dashboardadatok frissítése | Unified dashboard 1 perc; provisioning fájlfigyelés 30 s |

A collector gyakorisága futásvéghez kötött, nem pontos faliórai perc. Sikeres üres API-lekérés is frissíti a heartbeatet. Ez nem bizonyít Loki-kézbesítést.

## Dashboardok és értelmezés

Fő nézet: **MatchWise | Unified Monitoring**, UID `matchwise-unified-overview`, repositorybeli verzió 8. Adatforrás-UID: `prometheus`, `loki`. Host-, Supabase-, backend-, frontend-, Pino-, auth-, collector- és diagnosztikai nézetek. Megmarad a három részletes Infrastructure, Application Availability és Backend Logs dashboard. A korábbi panelszámok történetiek, nem a jelenlegi nézet ellenőrzött leltárai.

A CPU/RAM/lemez, a válaszidők, P95 és 4xx továbbra is diagnosztikai adatok. A hat auth-számláló sikeres/elutasított/hibás login, login 5xx, logout és regisztráció eseményét követi; aktív felhasználó vagy munkamenet nem számolható belőlük. A regisztráció automatikusan be is léptethet.

A minták sikeraránya nem garantált folyamatos uptime. Egy tárolt minta több grafikonpontban is megjelenhet. A Pino-idő nem teljes külső HTTP-idő. A health-forgalom torzíthatja az alkalmazásfunkciók összesített hibaarányát és percentiliseit. Nulla hiba és hiányzó napló eltérő állapot. A dashboard frontendkártyájának 5 perces és a riasztás 3 perces frissessége tudatos eltérés: a riasztás hamarabb jelzi a mérés hiányát.

## Tárolás, megőrzés, hozzáférés

- Prometheus: konfigurált 7 nap vagy 2 GB, a korábban elért korlát szerint.
- Loki: konfigurált 168 óra, compactor retention bekapcsolva; nem azonos a JSONL-forgatással.
- JSONL: `~/ai-job-monitoring/test-logs/render-backend.jsonl`; óránkénti méretellenőrzés, 20 MB küszöb, legfeljebb hét tömörítetlen archívum.
- Tartós named volume: prometheus_data, grafana_data, loki_data, alloy_data. A tartós tárolás nem önmagában biztonsági mentés.
- SQLite és kurzor: `~/monitoring-private-state/`; rutinszerű frissítéskor megőrzendő.
- Titkok: gitből kizárt `.env`, `~/monitoring-private-secrets/`; kulcsértékek nem kerülhetnek parancskimenetbe vagy commitba.
- Supabase privát password/target fájl: a helper által előállítva, read-only Prometheus mount.
- Host network, loopback management végpontok; Grafana SSH-alagúton. A VM .env módosítása nem módosítja a Render Environment értékeit.

A megőrzési értékek konfigurációs célok; a tényleges lemezhasználatot, megőrzési ciklust és visszaállíthatóságot külön kell mérni.

## Bizonyítékok és állapot

Részletes dátumok: [monitoring-tests.md](monitoring-tests.md).

| Terület | Rögzített bizonyíték | Korlát |
|---|---|---|
| Alap monitoring | Október 28-i endpoint- és konténertesztek | Korábbi négyszolgáltatásos állapot |
| Telegram | Október 28-i helyi tesztszabály Firing és Resolved | Nem az összes új szabály kézbesítési tesztje |
| Naplóút, deduplikáció, rotáció | Október 30-i tesztek; 120 egyedi szintetikus üzenet | Nem általános adatvesztésmentesség |
| Auth és naplókorreláció | November 9-i regisztráció/login/me/account/logout és várt 401; két reqId Lokiban | Nem frontendintegráció és nem folyamatos üzleti teszt |
| Supabase | November 9-i HTTP 200, UP célpont, lastError nélkül | Nem november 10-i élő állapot |
| Új kiesésriasztások | November 10-i helyi konfiguráció- és PromQL-tesztek | VM-provisioning és élő Telegram még tesztelendő |

## Korlátok és tervezett fejlesztések

A teljes Oracle VM vagy Grafana kiesésekor a helyi Grafana nem képes megbízható értesítésre. Független, másik infrastruktúrán futó ellenőrzés szükséges; ez jelenleg **tervezett**, nem telepített védelem. Ne nyissuk meg emiatt a belső monitoringportokat. Egy külső VM/heartbeat szolgáltatás elmaradó, kifelé küldött heartbeatet és külön értesítési utat használhat.

A backend 30 perces mintavétele kihagyhat rövid kiesést; nem tartjuk ébren sűrűbb lekéréssel. A health sikere nem teljes üzleti funkcióteszt. A frontend HTTP 200 nem bizonyít böngészős működést vagy API-kapcsolatot. A korábbi demo-login megfigyelés dátumhoz kötött, most nem ellenőriztük újra. Render/Vercel host CPU/RAM, browser hibák/Web Vitals és tracing nincsenek gyűjtve.

A collector elérhetősége, a Loki health és a valódi naplókézbesítés három külön kérdés. Egy csendes alkalmazásra nem indítunk naplóhiány-riasztást. A helyi health-próbák sem detektálnak minden beolvasási/továbbítási hibát. Független szintetikus naplóút-teszt későbbi fejlesztés lehet.

## Üzemeltetés és változáskövetés

Repository a konfiguráció elsődleges forrása. Módosítás → helyi validálás → GitHub-commit → VM `git pull --ff-only` → konténerenkénti alkalmazás → élő ellenőrzés és bizonyíték rögzítése. Konfliktus esetén nincs `reset --hard`; volume vagy collectorállapot nem törölhető rutinszerűen.

Az egyedi fájl-bind mount miatt Prometheus és szükség esetén Alloy konfigurációjához konténer-újralétrehozás kellhet. A mostani változás Prometheust és Grafanát érinti. Pontos alkalmazás és rollback: [riasztási terv](alerting-plan.md#alkalmazas). Projektlezárási cél a korábbi dokumentáció szerint legkésőbb 2026. december 15.
