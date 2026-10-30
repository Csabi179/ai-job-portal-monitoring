# MatchWise – Render Backend Logging Runbook

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
MatchWise - Render Log Collector Stale

A riasztás feltétele:
az utolsó sikeres lekérdezés óta több mint 300 másodperc
telt el, további 2 perces pending idővel.

Értesítési cél:
AI Job Telegram

## Átállás a csapat Render backendjére

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

A Loki job címke és a Grafana dashboard nem változik.

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
