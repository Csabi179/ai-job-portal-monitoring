# MatchWise – riasztási terv és Oracle-frissítési eljárás

[English version](alerting-plan.en.md) · [Dokumentációjegyzék](README.md)

**Jelenlegi dokumentált állapot (2026. november 18.):** 15 állandó szabály: 12 kiesési/megfigyelési és 3 backend-erőforrás/biztonsági jelzés. Render CPU/RAM-gyűjtés és Service Comparison dashboard telepítve. A három új szabály szintetikus Firing/Resolved Telegram-köre képekkel igazolt; a tesztszabályok eltávolítását és a valódi, 10 hibás loginos próbát az üzemeltető visszaigazolta. Az eredeti collector/Node Exporter kézbesítési bizonyíték megmarad; a többi tíz eredeti szabály teljes éles tesztje nincs igazolva. [Tesztnapló](monitoring-tests.md).

Konkrét tesztparancsok az eredeti 12 szabályhoz: [magyar](alert-rule-tests.md) · [English](alert-rule-tests.en.md).

## Cél és döntések

Kiesési és megfigyelési riasztások mellett három új backendjelzés aktív. Magas Render CPU, sok 5xx és sok elutasított POST login értesítést adhat. Egyetlen hibás jelszó, RAM/lemezfoglaltság, sikeres lassú HTTP, P95, általános 4xx és forgalomhiány nem aktív riasztási ok.

### A korábbi kilenc szabály felülvizsgálata

| Kiindulási szabály / UID | Döntés | Indok |
|---|---|---|
| Monitoring Test Endpoint DOWN / ai_job_test_endpoint_down | Törlés a provisionált állapotból | Helyi tesztszabály; Grafana teljes kiesését saját maga nem tudja jelezni |
| Oracle – Low Available Memory / ai_job_low_memory | Törlés | Kapacitás, nem kiesés |
| Oracle – Low Disk Space / ai_job_low_disk | Törlés | Kapacitás, nem kiesés |
| Oracle – Exporter DOWN / ai_job_exporter_down | Módosítás | A meglévő UID most a Blackbox Exportert figyeli; Node Exporter és Prometheus külön, hiányzó sorral együtt |
| MatchWise Backend DOWN / matchwise_backend_down | Módosítás | A legutóbbi friss próba hibája; nincs hiányzó-adatból képzett nulla |
| Backend Monitoring Data Missing / matchwise_backend_probe_missing | Módosítás | 40 perces frissesség és a legutóbbi scrape hibája |
| MatchWise Frontend DOWN / matchwise_frontend_down | Módosítás | Friss HTTP-hiba, scrape-hibától megkülönböztetve |
| Frontend Monitoring Data Missing / matchwise_frontend_probe_missing | Módosítás | 3 perces frissesség és scrape-hiba |
| Render Log Collector Stale / matchwise_render_collector_stale | Módosítás | Heartbeat és textfile-feldolgozás; Node Exporter elérhetőségével feltételesen |

A kiindulási backend- és frontendszabály két legutóbbi sikertelen próbát követelt; a backend akár további fél órát várt. Az új szabály egyetlen, a teljes 100 másodperces prober timeout után is sikertelen backendpróbát jelez, 2 perces pendinggel. A 30 perces próbaintervallum változatlan. A 22 másodperces, HTTP 200-zal sikeres hidegindítás nem riasztási ok.

A kivett három UID explicit `deleteRules` bejegyzésben szerepel: önmagában a fájl eltávolítása nem törölné a Grafanában tárolt szabályt. A korábbi kiesési/monitoring-készlet **12 szabály**, az új hárommal együtt **15 állandó szabály**; minden csoport értékelése **1 perc**.

## November 18-i három új szabály

| UID | Feltétel | Pending |
|---|---|---|
| matchwise_backend_cpu_high | Render CPU >80%, friss és érvényes erőforrásméréssel | 5m |
| matchwise_backend_5xx_burst | Legalább 5 nem health HTTP 5xx a gördülő előző 5 percben | 2m |
| matchwise_backend_login_burst | Legalább 10 POST login 401 a gördülő előző 5 percben, minden felhasználó együtt | 2m |

A kétperces pending nem követel új hibákat: a már megtörtént események addig számítanak, amíg az ötperces ablakban maradnak. A perc az értékelés gyakorisága. [Részletes idővonal, frissességi kapuk és KeepLast](SERVICE_COMPARISON_ALERTS.md). Az új naplóalapú szabályok Loki A-lekérdezést és Prometheus D-kaput, majd B/E/F/C Grafana-kifejezéseket használnak; nem az alábbi 12 régi szabály egyszerű PromQL-láncát.

[Teszt és eltávolítás](SERVICE_COMPARISON_ALERT_TEST.md). A további eredeti telepítési és visszaállítási példák a korábbi kiesési csomagra vonatkoznak; az aktuális állandó darabszám 15.

## Az eredeti 12 szabály pontos feltételei és késései

A szabályok `A` PromQL-kifejezése, `B=last(A)` redukciója és `C: B > 0.5` küszöbe a [provisioning könyvtárban](../grafana/provisioning/alerting/) található. Az alábbi definíciók ezekhez tartoznak; nincs rejtett dashboardváltozó.

| Szabály UID | Kiesés vagy mérési hiba definíciója | Pending | Jellemző észlelés, értesítési várakozás előtt |
|---|---|---|---|
| matchwise_node_exporter_unavailable | `1 - (min(up{job="node_exporter"}) or vector(0)) > 0.5` | 3m | Sikertelen scrape után kb. 3–5m; eltávolított sor esetén lookback/staleness is számít |
| ai_job_exporter_down | Ugyanez `job="blackbox_exporter"` mellett | 3m | Kb. 3–5m scrape-hibánál |
| matchwise_prometheus_scrape_unavailable | Ugyanez `job="prometheus"` mellett | 3m | Önscrape-hiba; a Prometheus teljes elérhetetlenségét DatasourceError jelzi |
| matchwise_backend_down | `max(1-last_over_time(probe_success[40m]))`, csak ha a megfelelő legutóbbi `up[40m]=1` | 2m | Kb. 2–35m a kiesés kezdetétől, a következő próbától és timeouttól függően |
| matchwise_backend_probe_missing | `1-(min(last_over_time(up[40m])) or vector(0))*(max(present_over_time(probe_success[40m])) or vector(0))` | 2m | Sikertelen scrape után kb. 2–4m; teljes mintahiány kb. 42–44m az utolsó mintától |
| matchwise_frontend_down | Backendhez hasonló, `[3m]` ablakkal és frontend job/service címkével | 2m | Kb. 2–4m, plusz a HTTP-próba ideje |
| matchwise_frontend_probe_missing | Backendhez hasonló, `[3m]` ablakkal | 2m | Scrape-hiba kb. 2–4m; adatelmaradás kb. 5–7m az utolsó mintától |
| matchwise_supabase_metrics_unavailable | `up` hiányzik/0, vagy 3m-en belül nincs `pg_up` | 3m | API-hiba kb. 3–5m; pg_up hiánynál kb. 6–8m |
| matchwise_supabase_database_down | `max(1-last_over_time(pg_up[3m]))`, csak `min(up)=1` mellett | 2m | Kb. 2–4m, plusz scrape-idő |
| matchwise_render_collector_stale | Heartbeat kora >300s, hiányzó heartbeat/textfile hibajelző, vagy `node_textfile_scrape_error=1`; csak `up{job="node_exporter"}=1` mellett | 2m | Elakadás kb. 7–10m az utolsó sikertől; textfile-hiba kb. 2–4m |
| matchwise_loki_health_unavailable | A loki service `blackbox_monitoring_components` próbájának `probe_success` vagy `up` értéke 0/hiányzik | 3m | Kb. 3–5m; teljes sor eltűnése lookback miatt késhet |
| matchwise_alloy_health_unavailable | Ugyanez alloy service mellett | 3m | Kb. 3–5m; teljes sor eltűnése lookback miatt késhet |

A backend selector `job="blackbox_render_backend",service="matchwise_backend"`; frontend: `job="blackbox_vercel_frontend",service="matchwise_frontend"`. A Supabase selector rögzítetten az aktuális `uvopvarvelpabhmrqaaw.supabase.co:443` instance, nem a korábbi projekt. Projektváltáskor ezt a két szabályt is módosítani kell, különben a régi projekt mérési hiánya jogosan riaszt.

A késések becslések, nem SLA-k: scrape-fázis, prober futási idő, staleness és Grafana-ütemezés befolyásolja őket. A kezdő értesítéshez további legfeljebb körülbelül 30s csoportvárakozás, már létező csoport új eseményéhez akár 5m járulhat. A Prometheus alapértelmezett instant lookbackje 5m; ezért teljes sor eltűnése nem mindig azonos a következő sikertelen scrape időpontjával.

### Fontos állapotkülönbségek

`up=1, probe_success=0`: a Blackbox scrape működik, de a HTTP-próba sikertelen. `up=0`: a scrape nem működik; ebből nem tudjuk, hogy a célalkalmazás él-e. A backend 40 perces range ablaka szükséges, mert a 30 perces scrape gyakran kívül esik az instant lookbacken. Nem számolunk új próbának grafikonon megismételt értéket.

`up{job="supabase"}=0`: Metrics API/hitelesítési/hálózati hiba lehetséges. `pg_up=0` sikeres scrape mellett: az exporter nem tud PostgreSQL-hez kapcsolódni. Ez exporteri elérési hiba, nem független adatbázis-bizonyíték. A `pg_up` a meglévő dashboardban és a dokumentált metrikakészletben szerepel.

Loki `http://127.0.0.1:3100/ready`; Alloy `http://127.0.0.1:12345/-/healthy`: dokumentált, 200-as választ váró endpointok. Az új próbák konfigurálva vannak; ezen a napon az Oracle-n futó példányokon nem ellenőriztük őket. Az Alloy `/-/ready` csak indulási készséget mutat; ezért az összes komponens egészségét jelző `/-/healthy` a próba célja. A health nem teljes beolvasási/tárolási/kézbesítési teszt.

A Node Exporter kiesése a hostmegfigyelés kiesése; teljes VM-kiesést ebből nem állítunk. A collector elakadása megfigyelési szolgáltatáshiba, mert a Render-naplók begyűjtése leállhat. Sem a legújabb Loki-alkalmazásnapló kora, sem forgalomszám nem riasztási feltétel.

## No Data és lekérdezési hiba

- Backend/frontend HTTP, PostgreSQL és collector: `noDataState=KeepLast`, `execErrState=KeepLast`. A bizonyíték hiánya vagy lekérdezési hiba nem oldhat fel egy folyamatban lévő kiesést. A kapcsolódó monitoring-szabály jelzi a mérés hibáját.
- A többi nyolc monitoring-szabály: `noDataState=Alerting`, `execErrState=Error`. Sikeresen lefutó üres selector esetén explicit hibajelzés képződik. A fallback kizárólag a várt monitoringbemenet hiányát kódolja hibává; nem állítja a szolgáltatást UP állapotúra.
- Az eredeti 12 szabály szolgáltatásszabályai nem használnak `or vector(0)` egészségesnek minősítő pótlást. Aggregálással stabil, egyetlen címkekészletet adnak, csökkentve a MissingSeries miatti téves feloldást.
- A KeepLast kezdeti Normal állapota nem friss UP-bizonyíték. Mindig a hozzá tartozó monitoringriasztással és a minta korával együtt értelmezendő.
- A DatasourceError eseményeket közös adatforrás szerinti értesítési csoport fogja össze. A Grafana pontos Error/Pending állapotmenetét a futó 13.2.1 példányon tesztelni kell. A normál küszöbtesztek nem helyettesítik ezt.
- Egy kizárólag a KeepLast szabály saját kifejezését érintő futásidejű hiba rejtve maradhat, ha a kapcsolódó monitoringkifejezés működik. Ezt a helyi promtool tesztek, a telepítéskori szabály-Health ellenőrzés és a rendszeres operátori ellenőrzés mérsékli.

## Telegram, csoportosítás és helyreállás

Megmaradó contact point: **AI Job Telegram**, UID `ai_job_telegram`. Token/chat ID környezeti változóban. A 2026-11-15-i üzemeltetői visszajelzés szerint a cél a csapat Telegram-csoportja a korábbi privát beszélgetés helyett. `disableResolveMessage=false`. A sablon felsorolja az eseményenkénti firing/resolved állapotot, a szabály összefoglalóját és rövid, legfeljebb 200 karakteres hibaleírását; közös teendőhivatkozással. Plain text (`parse_mode: None`) csökkenti a Telegram formázásból eredő kézbesítési hibáit. A 4096 karakteres Telegram-korlát miatt a nagy csoportok üzenete rövidülhet.

Normál csoportkulcs: `grafana_folder, category`; külön availability, monitoring és security csoport; a kontrollált teszt security_test kategóriát használ. DatasourceError: `alertname, datasource_uid`. Group wait 30s, group interval 5m, repeat 4h. A 4h ismétlés a tartósan fennálló, változatlan csoportra vonatkozik; csoportváltozás előbb is küldhet üzenetet.

Nincs automatikus függőségi elnyomás. Egy Blackbox-hibához több monitoringriasztás tartozhat; ezek egy csoportosított üzenetben jelennek meg. Egy már aktív HTTP-kiesés mérési hiba alatt is megmaradhat: ez tudatosan nem hamis helyreállás. A közös hibát először a Blackbox/Prometheus irányából kell vizsgálni.

HTTP-helyreállást új sikeres próba vált ki. Backend esetén ez akár a következő 30 perces próbáig késhet, utána értékelés és értesítési csoportvárakozás következik. A monitoringriasztás feloldása a mérés működésének helyreállása, nem automatikusan az alkalmazásé. Üzenetben mindkét állapot olvasható. Nincs külön keep-firing idő.


### Telegram-csoport mint értesítési cél

A bot változatlan; a célcsoportot a privát Oracle `.env` fájl `GRAFANA_TELEGRAM_CHAT_ID` értéke választja ki. A `GRAFANA_TELEGRAM_BOT_TOKEN` marad a meglévő bot tokenje. A valódi értékeket és a `.env` fájlt nem verziózzuk. A provisioning már ezeket a változókat használja, ezért a címzéshez nem kell szabályt vagy YAML-fájlt átírni.

1. Add hozzá a botot a célcsoporthoz, és engedélyezd számára az üzenetküldést.
2. Küldd el a csoportban a `/start@<bot_felhasznaloneve>` parancsot a valódi botnévvel. Válasz nem szükséges: a Grafana értesítési botnak nincs parancsokra válaszoló programja.
3. A Telegram Bot API `getUpdates` válaszában keresd a célcsoport `chat.id` mezőjét, a `chat.title` és `chat.type` alapján ellenőrizve a csoportot. A bot tokenjét ne tedd megosztott URL-be vagy kimenetbe.
4. A `~/ai-job-monitoring/.env` fájlban csak a `GRAFANA_TELEGRAM_CHAT_ID` értékét cseréld a csoport azonosítójára; a negatív előjelet is őrizd meg.
5. Alkalmazd a módosítást:

```bash
cd ~/ai-job-monitoring
sudo docker compose config --quiet
sudo docker compose up -d --no-deps --force-recreate grafana
curl -fsS http://127.0.0.1:3000/api/health
```

A Grafana röviden újraindul; a többi szolgáltatást nem kell újraindítani. Azonnali health-hiba esetén az indulás után ismételd meg az ellenőrzést. Teljes `docker compose config` kimenetet ne ossz meg, mert titkokat tartalmazhat.

Grafanában adminnal: **Alerting → Contact points → AI Job Telegram → Test → Send test notification**. Ellenőrizd, hogy a teszt a célcsoportba érkezik. Ez a csatornát ellenőrzi, nem mind a 12 szabály firing/resolved működését. Az átállítás a privát cél helyett a csoportot használja; nem hoz létre második privát kézbesítést. A visszaállításhoz a korábbi, privát helyen megőrzött chat ID-t állítsd vissza és ismételd meg az alkalmazást és a tesztet.

A sikeres átállítás üzemeltetői visszajelzését a [TEST-13](monitoring-tests.md#test-13-telegram-group-delivery) rögzíti. API-leírás: [Telegram getUpdates](https://core.telegram.org/bots/api#getupdates).

## Hibakeresés

<a id="http"></a>
### HTTP

Backend: következő időzített próba, Prometheus targets lastError, `up` és `probe_success` utolsó mintája; Render deploy/logok; DNS/TLS és HTTP státusz. Kézi health-GET csak célzott hibakeresésként: felébresztheti a Render Free szolgáltatást. Frontend: HTTP státusz, Vercel deploy, DNS/TLS; szükség esetén külön böngészős funkcióteszt.

<a id="monitoring"></a>
### Monitoring

`sudo docker compose ps`; Prometheus `/-/ready`; targets és scrape hibák; Node/Blackbox metrics endpoint; containerlogok. Node Exporter hiánynál a host állapotát külön Oracle/SSH csatornán ellenőrizzük. A Prometheus önscrape sikere nem véd a teljes VM kiesésétől.

<a id="supabase"></a>
### Supabase

Metrics API scrape és pg_up külön; 401/403-nál privát secret/jogosultság, file_sd célpont és password-file olvashatóság. Ne írasd ki a jelszófájlt. A régi projektet ne állítsd vissza automatikusan. Pg_up=0-nál Supabase állapot/DB elérhetőség; az alkalmazásfunkciókat külön vizsgáld.

<a id="collector"></a>
### Collector

Timer aktív-e, oneshot Result/ExecMainStatus, journal; heartbeat kor; `node_textfile_scrape_error`; Render API 401/403/429/5xx, flock vagy timeout. Sikeres collector mellett a csendes alkalmazás normális lehet. SQLite/kurzor megőrzendő.

<a id="logs"></a>
### Loki és Alloy

Közvetlen health-GET, Blackbox Exporter állapot; konténerlogok; Alloy komponensek és loki.write hibák; JSONL mount és fájlolvasási jog; Loki query. Külön reqId-korreláció igazolja a valódi kézbesítést. Új alkalmazásnapló hiánya önmagában nem pipeline-hiba.

<a id="alkalmazas"></a>
## Alkalmazás az Oracle VM-en

A következő parancsokat az üzemeltető futtatja. A jelenlegi munka nem futtatta őket az Oracle gépen. A `.env`, collectorállapot és named volume-ok megmaradnak.

### 1. Munkafa és visszaállítási pont

```bash
cd ~/ai-job-monitoring
git status --short
# Csak tiszta / előzetesen áttekintett munkafával folytasd.
PREVIOUS_MONITORING_COMMIT=$(git rev-parse HEAD)
printf '%s\n' "$PREVIOUS_MONITORING_COMMIT"
git pull --ff-only
git log -1 --oneline
sudo docker compose config --quiet
```

Jegyezd fel a régi és új commitot privát üzemeltetési naplóban. Konfliktusnál ne írj felül helyi módosításokat. Teljes `docker compose config` kimenetet ne ossz meg, mert titkokat interpolál.

### 2. Új konfiguráció validálása és endpointok

```bash
sudo docker compose run --rm --no-deps --entrypoint promtool prometheus \
  check config /etc/prometheus/prometheus.yml

curl -fsS http://127.0.0.1:3100/ready
curl -fsS http://127.0.0.1:12345/-/healthy
curl -fsS http://127.0.0.1:3000/api/health
```

Ha a privát Supabase-mount hibás, kövesd a [Supabase-eljárást](SUPABASE_METRICS.md), a tényleges Prometheus UID-val. Rutin riasztásfrissítéshez a secret-generátort nem kell újrafuttatni.

### 3. Prometheus alkalmazása, Grafana előtt

```bash
sudo docker compose up -d --no-deps --force-recreate prometheus
sudo docker compose ps prometheus
curl -fsS http://127.0.0.1:9090/-/ready
```

Az első scrape után, legalább 60–90 másodperc elteltével:

```bash
curl -fsSG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="blackbox_monitoring_components"}' | python3 -m json.tool
curl -fsSG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=probe_success{job="blackbox_monitoring_components"}' | python3 -m json.tool
curl -fsSG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="supabase",instance="uvopvarvelpabhmrqaaw.supabase.co:443"}' | python3 -m json.tool
curl -fsSG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=pg_up{job="supabase",instance="uvopvarvelpabhmrqaaw.supabase.co:443"}' | python3 -m json.tool
```

Mindkét loki/alloy sor és mindkét Supabase lekérdezés várt értéke 1. Üres eredmény nem siker. Hiba esetén először javítsd a mérést; az új próbák indulási hiányát ne tekintsd igazolt szolgáltatáskiesésnek.

### 4. Grafana provisioning

```bash
sudo docker compose up -d --no-deps --force-recreate grafana
sudo docker compose ps
curl -fsS http://127.0.0.1:3000/api/health
sudo docker compose logs --since=10m grafana
```

A restart a Grafana értékelési állapotát/pending idejét befolyásolhatja. A volume megmarad. A HTTPS-címen megnyitott Grafana Alert rules nézetben ellenőrizd:

- 12 aktív, provisionált szabály; a három törölt UID nincs jelen.
- A fennmaradó szabályok UID-ja az elvárt; nincs régi vagy kézzel létrehozott párhuzamos szabály.
- Query Health rendben; No Data/Error nem elfedett; a backendnél van 40 percen belüli mérés.
- Contact point és policy címzése megmaradt; resolve üzenet engedélyezett; sablon előnézet működik.

A provisionált fájlok nem kezelik automatikusan az ismeretlen kézi szabályokat. Ha ilyet találsz, dokumentáld és külön kezeld.

### 5. Teszt és bizonyíték

Az alábbi táblázat az elvégzett és a még tervezett teszteket külön jelöli; új tesztet külön tesztkörnyezetben vagy egyeztetett rövid karbantartási ablakban. A health/szolgáltatás szándékos leállítása ne érintse véletlenül az alkalmazás adatait.

| Forgatókönyv | Várt eredmény | Állapot |
|---|---|---|
| Contact point teszt és sablon firing/resolved előnézet | Telegram üzenet; csak csatornateszt | Angol kézbesítés TEST-11; csoportos átállás TEST-13; külön resolved-előnézet nem igazolt |
| Frontend/backend sikeres, akár 22s HTTP 200 | Nincs kiesésriasztás | PromQL szinten siker tesztelt; élő új szabály még nem |
| HTTP failure, up=1 | Csak HTTP-kiesés pending → firing | Helyi PromQL tesztelt; élő teszt tervezett |
| up=0 vagy probe_success eltűnik | Monitoringhiba; szolgáltatásállapot nem oldódik fel bizonyíték nélkül | Helyi PromQL tesztelt; KeepLast élő teszt tervezett |
| Backend utolsó minta 39m, majd >40m | 39m-nél még értékelhető; utána mérési hiba | Helyi PromQL tesztelt |
| Supabase API-hiba / pg_up=0 / hiányzó pg_up | Külön monitoringhiba és DB-elérési hiba | Helyi PromQL tesztelt; ne állíts le DB-t rutintesztként |
| Collector timer megállítása, folyó oneshot megvárása | Heartbeat elavul; firing, majd új siker után resolved | Firing/Resolved igazolt: TEST-10; pontos időmérés nélkül |
| Nincs alkalmazásforgalom, collector továbbra is sikeres | Nincs collector-riasztás | Helyi PromQL tesztelt |
| Loki/Alloy ellenőrzött health-hiba, majd helyreállás | Firing és resolved, mérési hibától megkülönböztetve | Élő teszt tervezett |
| Prometheus elérhetetlen, Grafana működik | Csoportos DatasourceError; nincs hamis szolgáltatás-helyreállás | Élő teszt tervezett |
| Backend/collector már firing, majd mérés eltűnik | KeepLast, nincs hiányból keletkező resolved | Élő Grafana-állapotmenet tervezett |
| Több kapcsolódó hiba, változatlan 4h hiba | Csoportosítás, ismétlés, resolved üzenetek | Tervezett |
| Teljes Oracle VM-kiesés | Helyi Grafanától nem várható üzenet | Külső ellenőrzés nincs telepítve |

A collector tesztnél visszaállítás:
```bash
sudo systemctl start matchwise-render-logs.service
sudo systemctl start matchwise-render-logs.timer
sudo systemctl show matchwise-render-logs.service -p Result -p ExecMainStatus
```

Ne töröld a SQLite-ot, kurzort vagy heartbeatet a teszt kedvéért. Ne használd a régi render-logs-once.py szkriptet az aktív JSONL-re.

Minden teszthez rögzítsd: dátum/időzóna, commit, szabály UID, bemenet/hiba módja, query érték, pending/firing ideje, Telegram firing ideje, helyreállítás ideje, resolved ideje, képernyőkép vagy privát bizonyíték helye és végső állapot. Titkok nélkül. Eredményeket a [meglévő tesztnaplóba](monitoring-tests.md) írd.

### Visszaállítás

Tiszta munkafánál a korábban feljegyzett commit provisioning- és Prometheus-fájljait állítsd vissza, majd validálj és hozd újra létre a két konténert:

```bash
git restore --source="$PREVIOUS_MONITORING_COMMIT" -- prometheus/prometheus.yml grafana/provisioning/alerting
sudo docker compose config --quiet
sudo docker compose run --rm --no-deps --entrypoint promtool prometheus \
  check config /etc/prometheus/prometheus.yml
sudo docker compose up -d --no-deps --force-recreate prometheus grafana
```

Fontos: a régi fájlok visszaállítása újra létrehozza a régi szabályokat, de az új hat UID-t nem törli automatikusan. A fenti konténer-újralétrehozás **előtt** hozz létre átmeneti törlési provisioning fájlt:

```bash
python3 - <<'PY'
import json
from pathlib import Path
uids = ['matchwise_node_exporter_unavailable', 'matchwise_prometheus_scrape_unavailable',
        'matchwise_supabase_metrics_unavailable', 'matchwise_supabase_database_down',
        'matchwise_loki_health_unavailable', 'matchwise_alloy_health_unavailable']
Path('grafana/provisioning/alerting/rollback-new-rules.json').write_text(
    json.dumps({'apiVersion': 1, 'deleteRules': [{'orgId': 1, 'uid': u} for u in uids]}),
    encoding='utf-8')
PY
```

Ezután validálj és hozd újra létre a konténereket a fenti parancsokkal. Ellenőrizd a teljes aktívszabály-leltárt. A törlőfájlt sikeres rollback után helyezd a Git-munkafán kívüli privát állapotkönyvtárba, hogy egy későbbi előrelépés ne törölje az új szabályokat. A rollback helyi fájleltéréseit is rendezd a következő frissítés előtt. A volume-ok és collectorállapot visszaállítása nem része ennek a konfigurációs rollbacknek.

## Teljes monitoringhost-kiesés

A helyi Grafana nem értesít megbízhatóan saját folyamata vagy a teljes Oracle VM leállásakor. A helyi Node Exporter, Prometheus és Blackbox egymást ellenőrző szabályai ezt nem oldják meg.

**Tervezett külön fejlesztés:** az Oracle gépről kifelé küldött heartbeatet más szolgáltatón futó rendszer ellenőrizze, önálló értesítési útvonallal. A heartbeat lefedettségét (csak VM vagy Grafana-értékelés is) előre meg kell határozni. A teljes VM és Grafana leállításával kontrollált teszt szükséges. Ez most nincs megvalósítva; monitoringport megnyitása nem szükséges.

## Források és helyi ellenőrzés

- [Grafana fájlalapú provisioning](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/)
- [Grafana No Data/Error](https://grafana.com/docs/grafana/latest/alerting/fundamentals/alert-rule-evaluation/nodata-and-error-states/)
- [Prometheus range függvények](https://prometheus.io/docs/prometheus/latest/querying/functions/)
- [Alloy HTTP health](https://grafana.com/docs/alloy/latest/reference/http/)
- [Loki HTTP API](https://grafana.com/docs/loki/latest/reference/loki-http-api/)
- [Supabase metrikaexpozíció](https://github.com/supabase/supabase-grafana/blob/main/metrics.md)
- [Telegram Grafana-integráció](https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/integrations/configure-telegram/)

A helyi ellenőrzés PyYAML-t és a használt verziójú promtoolt igényli:
```bash
python3 scripts/validate-alerting.py --promtool /path/to/promtool
promtool check config --syntax-only prometheus/prometheus.yml
```

A --syntax-only nem ellenőrzi a privát jelszófájlt és file_sd tartalmat; ezért az Oracle-n teljes promtool check is kell. A tesztszkript közvetlenül a provisionált A-kifejezéseket használja, és sem külső szolgáltatást, sem Telegramot nem hív.
