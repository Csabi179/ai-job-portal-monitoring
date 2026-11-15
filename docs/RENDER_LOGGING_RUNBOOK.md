# MatchWise – Render Backend Logging Runbook

[English version](RENDER_LOGGING_RUNBOOK.en.md) · [Dokumentációjegyzék](README.md)

> Állapot: a collector és a Node Exporter Firing/Resolved kézbesítése igazolt, az üzenetek angolok és a csapat Telegram-csoportjába érkeznek. A többi tíz szabály egyenkénti élő tesztje nincs igazolva; részletek a [tesztnaplóban](monitoring-tests.md).

## Áttekintés

A MatchWise backend strukturált Pino JSON-naplókat készít.

Adatfolyam:

Render Backend
→ Render Logs API (HTTPS)
→ Oracle Cloud Python collector
→ JSONL naplófájl
→ Grafana Alloy
→ Loki
→ Grafana Backend Logs dashboard

A gyűjtő állapotát külön felügyelet figyeli:

Python collector
→ Node Exporter Textfile Collector
→ Prometheus
→ Grafana Alerting
→ Telegram

## Infrastruktúra

- Oracle Cloud Ubuntu VM
- Docker Compose
- Grafana, Loki, Alloy, Prometheus, Node Exporter
- Render Logs API
- Python 3 és SQLite
- systemd szolgáltatások és időzítők

## Automatikus naplógyűjtés

Szolgáltatás:
matchwise-render-logs.service

Időzítő:
matchwise-render-logs.timer

A gyűjtő körülbelül percenként fut.

Program:
scripts/render-logs-poll.py

A duplikációszűrés SQLite-alapú.

Privát adatbázis:
/home/ubuntu/monitoring-private-state/render-logs-seen.sqlite3

Időkurzor:
/home/ubuntu/monitoring-private-state/render-api-state.json

Aktív naplófájl:
test-logs/render-backend.jsonl

A privát állapotfájlok és naplók nem kerülnek GitHubra.

## Naplóforgatás

Szolgáltatás:
matchwise-render-logrotate.service

Időzítő:
matchwise-render-logrotate.timer

A logrotate óránként ellenőrzi a naplófájl méretét.

Beállítások:
- 20 MB-os forgatási küszöb
- legfeljebb 7 archivált fájl
- közös flock zárolás a Python collectorral
- az archívum a Git-repositoryn kívül található

Archívum:
/home/ubuntu/monitoring-private-archives/

## Grafana

Dashboard:
AI Job Portal / MatchWise | Backend Logs

Dashboard UID:
matchwise-backend-logs

Loki job címke:
matchwise_backend_render_api

A dashboard HTTP-kéréseket, HTTP-hibákat, hibaarányt,
P50/P95 backend válaszidőket, útvonalakat és naplókat mutat.

A responseTimeMs az alkalmazás feldolgozási ideje,
nem a teljes hálózati válaszidő.



## A központi monitoring dashboard

A fő áttekintő nézet: **AI Job Portal / MatchWise | Unified Monitoring**
(UID: `matchwise-unified-overview`).

A Backend Logs dashboard továbbra is elérhető a részletes hibakereséshez.
A fő nézet az Oracle VM, a Render HTTP-próbák, a Vercel HTTP-próbák,
a Pino HTTP-alkalmazásnaplók és a collector állapotának adatait egyesíti.
Render/Vercel host CPU/RAM és frontend böngészős hibák jelenleg nincsenek gyűjtve.

## Gyűjtő állapotának ellenőrzése

Timer:

    sudo systemctl is-active matchwise-render-logs.timer

Szolgáltatás:

    sudo systemctl show matchwise-render-logs.service -p Result -p ExecMainStatus

Legutóbbi futások:

    sudo journalctl -u matchwise-render-logs.service -n 30 --no-pager

Prometheus metrika:

    matchwise_render_collector_last_success_timestamp_seconds

Riasztás:
MatchWise | Render log collector | Monitoring failure

A riasztás feltétele:
az utolsó sikeres lekérdezés óta több mint 300 másodperc
telt el, további 2 perces pending idővel. A hiányzó heartbeat vagy textfile-hibajelző és a textfile-feldolgozás hibája is feltétel, működő Node Exporter mellett. Node Exporter-hiányra külön szabály figyel; a collector állapota ilyenkor KeepLast. Alkalmazásforgalom hiánya nem riasztás.

A 12 szabály betöltése és a collector Firing/Resolved tesztje igazolt. Az angol kézbesítést a Node Exporter tesztje is igazolja; a Telegram-csoportos átállást az üzemeltető visszaigazolta. Részletek: [riasztási terv](alerting-plan.md), [TEST-11](monitoring-tests.md#test-11-node-exporter-delivery) és [TEST-13](monitoring-tests.md#test-13-telegram-group-delivery).

Értesítési cél:
AI Job Telegram contact point → a csapat Telegram-csoportja, a privát GRAFANA_TELEGRAM_CHAT_ID szerint.

## Átállás a csapat Render backendjére – jövőbeli szolgáltatásváltás

2026. november 9-én a meglévő Render-szolgáltatás a csapat repositoryjának main ágára állt át, változatlan URL-lel és Service ID-val. Ezt nem kell megismételni. Az alábbi lépések másik szolgáltatásra költözésre vonatkoznak; az állapotot rutin frissítéskor ne nullázzuk.

Előfeltételek:

- A csapat backendje Renderen fut.
- A Render API-kulcs jogosult a csapat szolgáltatásának naplóit olvasni.
- A backend strukturált Pino http_request naplókat küld.
- A naplók tartalmazzák a reqId, route, statusCode
  és responseTimeMs mezőket.

1. Állítsuk le az automatikus naplógyűjtés timerét:

    sudo systemctl stop matchwise-render-logs.timer

2. Ellenőrizzük, hogy nincs folyamatban gyűjtés:

    sudo systemctl is-active matchwise-render-logs.service

A továbblépés előtt a szolgáltatásnak inactive állapotban
kell lennie. A Type=oneshot miatt ez normális.

3. Készítsünk biztonsági másolatot a privát konfigurációról
   és a jelenlegi időkurzorról.

4. Módosítsuk a privát konfigurációt:

    nano /home/ubuntu/monitoring-private-secrets/render-logs.env

A szükséges változók:

    RENDER_OWNER_ID=<csapat Workspace ID>
    RENDER_SERVICE_ID=<csapat Service ID>
    RENDER_PINO_SERVICE=job-portal-backend

A meglévő RENDER_API_KEY csak akkor tartható meg,
ha jogosult az új szolgáltatás naplóinak olvasására.

5. A régi időkurzort helyezzük biztonsági mentésbe.
   Ezután az új szolgáltatás első lekérdezése az
   előző 20 perces időablakkal indul.

6. Indítsuk el egyszer a szolgáltatást:

    sudo systemctl start matchwise-render-logs.service

7. Sikeres futás esetén kapcsoljuk vissza a timert:

    sudo systemctl start matchwise-render-logs.timer

8. A Render backend HTTP-elérhetőségének figyelését **külön át kell állítani**.
   A `prometheus/prometheus.yml` `blackbox_render_backend` target URL-jét
   módosítsuk a csapat valódi health endpointjára; tartsuk meg a
   `service: matchwise_backend` címkét. Prometheus konfigurációellenőrzés
   és újratöltés/újraindítás után ellenőrizzük a célpontot.

9. Ha a frontend is a csapat másik Vercel-címére kerül,
   a `blackbox_vercel_frontend` target URL-jét külön frissítsük,
   megtartva a `service: matchwise_frontend` címkét.

A Loki `job=matchwise_backend_render_api` címke és a Grafana-dashboard
ezek után változatlanul használható, **ha az új backend azonos Pino
`http_request` mezőket készít**.

Fontos: az első lekérdezés nem importálja automatikusan
az új szolgáltatás teljes korábbi naplóelőzményét.

A korábbi és új backend naplói időben átfedhetnek
a dashboardon, ha az időtartomány mindkettőt tartalmazza.

## Hibaelhárítás

401 Unauthorized:
Ellenőrizzük a Render API-kulcsot és hozzáférését.

403 Forbidden:
Ellenőrizzük a workspace és szolgáltatás jogosultságait.

429 Too Many Requests:
Render API sebességkorlátozás; a következő futást
és a systemd naplóit ellenőrizzük.

500 / 503:
Átmeneti Render API-hiba lehetséges.
A collector sikertelen futásakor az utolsó siker
időbélyege nem frissül.

Nincs új napló, de a collector sikeres:
Lehet, hogy nincs új alkalmazásforgalom,
vagy az új backend Pino-naplózása hiányzik.
A collector sikeressége önmagában nem bizonyítja,
hogy az alkalmazás megfelelően naplóz.

Grafana nem mutat adatokat:
Ellenőrizzük az Alloy, Loki és Grafana szolgáltatásokat,
valamint a Loki job címkét.

SQLite hiba:
Ne töröljük az adatbázist vagy az időkurzort.
Először készítsünk biztonsági másolatot.

## Biztonság

- A Render API-kulcs a Git-repositoryn kívül található.
- A privát kulcsokat és naplókat nem commitoljuk.
- A Grafana és monitoring API-k loopback címen érhetők el.
- A korábbi internetes syslog-fogadás nincs engedélyezve.
- A naplógyűjtés HTTPS-en keresztül történik.
- A Python collector csak engedélyezett Pino-mezőket tárol.

## Régi diagnosztikai segédszkript — fontos

A `scripts/render-logs-once.py` korai, **kézi tesztlekérő**, amelyben
rögzített test Service ID van. **Nem használja az éles gyűjtő SQLite
azonosítókezelését, időkurzorát és közös `flock` zárolását.** Ne futtassuk
az aktív `test-logs/render-backend.jsonl` fájlra az automatikus
collector mellett: duplikált naplókhoz és állapoteltéréshez vezethet.

Az éles gyűjtő kizárólag a `matchwise-render-logs.service` által
indított `scripts/render-logs-poll.py` program.

## Ismert korlátok

- A collector jelenleg nem végez automatikus HTTP-újrapróbálkozást.
- A feldolgozás oldalankénti felső korláttal rendelkezik.
- A Loki megőrzési szabálya különbözik a JSONL-archívumétól.
- A collector health riasztása nem ellenőrzi a Pino naplók tartalmát.
- A logrotate és Alloy együttműködése tesztelt,
  de teljes körű adatvesztésmentességi garancia nincs.

## GitHub

Repository:
Csabi179/ai-job-portal-monitoring

A GitHubban a konfigurációk, dashboardok,
riasztási szabályok és dokumentáció található.

A valódi naplók, SQLite-adatbázisok és
titkos kulcsok nem részei a repositorynak.

## Render API-időtúllépés kezelése

A Python API-kérés timeoutja 30 másodperc. Sikertelen futás nem frissíti a sikeres futás metrikáját; a systemd timer később újra próbálkozik. A november 11-i naplóban ismételt read timeout után sikeres gyűjtés és heartbeat-frissítés látható ([TEST-15](monitoring-tests.md#test-15-collector-timeout-recovery)). A gyors, token nélküli HTTP 401 csak az API elérését igazolja, a hitelesített naplólekérést nem. Ne növeld automatikusan a küszöböt, és ne töröld a SQLite/kurzor állapotot.

## CV és AI naplók

A meglévő collector kizárólag a konfigurált service `http_request` eseményeit és engedélyezett mezőit gyűjti. Az új végpont HTTP-naplója külön collectormódosítás nélkül használható, ha az éles backend ugyanazt a naplóformátumot adja. Külön AI-események nem jutnak át a jelenlegi szűrésen. A tervezett profilfunkció elérhető adatai és korlátai: [monitoringterv](monitoring-plan.md#cv-és-ai-megfigyelésének-előkészítése).
