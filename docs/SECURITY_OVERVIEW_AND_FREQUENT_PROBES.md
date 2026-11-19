# Security overview and frequent probes / Biztonsági panelek és percenkénti próbák

> **Current deployment — 2026-11-19:** The operator confirmed all supplied changes were already applied on Oracle. Monitoring was merged into `main` (`10f43d1`); no reinstallation is required because of that merge. [Current status](DEPLOYMENT_STATUS.md). Earlier rollout entries are historical; commands are retained for future updates or recovery.

Updated / Frissítve: 2026-11-19. Branch: main; the feature merge completed / az összevonás megtörtént. The applied update needs no post-merge reinstallation / a már alkalmazott frissítést nem kell a merge után újratelepíteni.

## Magyar

A frissítés telepítve: az Oracle-kimenet a percenkénti backend/frontendscrape-et és a sikeres backendpróbát igazolja, az üzemeltető a paneleket és a valódi 404-próbát is visszaigazolta. Az alábbi telepítési parancsok későbbi újrafuttatáshoz maradnak meg. A korábbi 15 szabályos állapothoz képest 1 új riasztás és 8 új panel készült; összesen 16 állandó szabály és 35 panel a Service Comparison dashboardon. A korábbi éles teszteredmények nem igazolják ennek a frissítésnek az éles működését.

### Új panelek

- HTTP 401, 403, 404 és 429 darabszám az előző öt percben, egymás mellett.
- Az előbbi négy válasz percenkénti üteme közös grafikonon, ötperces számítással.
- Forgalomváltozás: aktuális ötperces requests/min átlag és az azt megelőző 30 perc átlaga; az összehasonlító ablak öt perccel eltolva nem tartalmazza az aktuális öt percet.
- Szűrt 401/403/404/429 naplók.

Minden új forgalmi lekérdezés kizárja a /api/health és /health route-ot. A 401 itt minden nem health 401, nem csak login. Az értékek minden felhasználót együtt számolnak; IP/fiók szerinti bontás nincs. Ismeretlen route-ok unmatched név alatt összevonódhatnak.

A nulla pótlása csak akkor történik meg a panelekben, ha az adott ablakban volt naplózott nem health forgalom. Ha ilyen forgalom sincs, adathiány látszódhat; ez nem bizonyít kiesést. A naplócollector egészségét külön is ellenőrizd. A 429-panel csak naplózott 429 válaszokat számol; nem hoz létre és nem bizonyít kéréskorlátozást. A forgalomösszehasonlítás vizuális jelzés, automatikus forgalomkiugrás-riasztás nincs bekapcsolva.

### Új riasztás

UID: matchwise_backend_404_burst.
Név: MatchWise | Render backend | HTTP 404 burst.
Feltétel: legalább 20 naplózott, nem health 404 az előző 5 percben, 2 perces pendinggel. Értékelés percenként. Kezdeti küszöb, valós forgalomhoz igazítandó. Rövid sorozat régi eseményei is fenntarthatják a feltételt; nem kell közben újabb kérés. Ugyanazt a Prometheus monitoringkaput és KeepLast kezelést használja, mint a már telepített 5xx/login szabály. Telegram: meglévő security csoport. A sok 404 lehet keresgélés vagy hibás kliens/link; nem bizonyított támadás.

403-hoz, 429-hez és forgalomkiugráshoz egyelőre panel készült. Az új riasztás a korábban javasolt 404-es szabály.

### Backend ugyanúgy percenként

- Backend és frontend: scrape_interval=60s, scrape_timeout=15s.
- Blackbox backend és frontend HTTP-timeout: 10s. A backend modul neve http_render_2xx marad, timeoutja rövidül.
- Backend riasztások frissességi ablaka 40 percről 3 percre változik; a kétperces pending megmarad.
- Service Comparison, Unified és Application Availability backendkártyái 3 perces ablakot használnak; a félórás feliratok frissítve.
- A gyakoribb egészségkérés általában elkerüli a forgalomhiány miatti elalvást, amíg a monitoring és a szolgáltatás elérhető. Nem helyettesíti a szolgáltatói rendelkezésre állási garanciát. Kezdeti hidegindítás meghaladhatja a 10 másodpercet, ezért átmeneti sikertelen próba lehetséges.
- A Render ingyenes kerete a hivatalos leírás szerint workspace-enként havi 750 óra; az állandóan ébren tartott szolgáltatás ezt folyamatosan fogyasztja. Más szolgáltatásokkal megosztott keret és korlátelérés továbbra is okozhat leállást. Ez a változás nem vált fizetős csomagra.

## English

The update is deployed: Oracle output confirms one-minute backend/frontend scrapes and a successful backend probe, and the operator confirmed the panels and real 404 procedure. Installation commands below remain for future use. It adds eight panels and one 404 alert to the earlier fifteen-rule deployment: sixteen permanent rules and thirty-five Service Comparison panels. Earlier live test evidence does not validate this update.

New panels show five-minute 401/403/404/429 counts, their rates, security logs and a traffic comparison. Traffic compares the current five-minute requests/min average with the preceding thirty-minute average, offset by five minutes. All new traffic queries exclude /api/health and /health. Counts combine all users. Unknown routes may appear as unmatched. No IP/account attribution is available.

Panel zero fallback requires non-health HTTP traffic in that window. No traffic/logs can leave a gap; check collector health. 429 counts do not implement or prove rate limiting. Traffic comparison is visual; no traffic-spike alert is enabled.

New rule matchwise_backend_404_burst alerts on at least twenty non-health 404 responses in five minutes, sustained for two minutes. Evaluation is every minute. Earlier events can sustain the count without new attempts. It reuses the existing log monitoring gate, KeepLast handling and security Telegram routing. Many 404 responses can mean scanning or broken links; they do not prove an attack. No new 403/429/traffic-spike rule is enabled.

Backend and frontend now use 60-second scraping, 15-second scrape timeout and 10-second HTTP probe timeout. Backend freshness changes from forty to three minutes in alerts and three dashboards. The two-minute pending period stays. Frequent inbound probes should avoid idle spin-down while monitoring/service remain available. Initial cold starts can exceed ten seconds. Render free hours are consumed while awake; provider limits/outages can still stop service. No paid plan is selected.

## Stage and validate first / Először előkészítés és ellenőrzés

These commands create a separate temporary checkout snapshot. They do not modify live files or restart services. The Prometheus container supplies the matching native promtool. Python validation requires PyYAML on Oracle; if import fails, stop and report it. Run commands in order and stop on any failure.

Ezek külön ideiglenes könyvtárba készítik elő a verziózott fájlokat. Éles fájlt nem módosítanak és szolgáltatást nem indítanak újra. A Python-validátorhoz PyYAML szükséges. Hiba esetén állj meg.

```bash
cd ~/ai-job-monitoring
git fetch origin feat/service-comparison
MW_SECURITY_STAGE=$(mktemp -d /tmp/matchwise-security-update.XXXXXX)
git archive FETCH_HEAD | tar -x -C "$MW_SECURITY_STAGE"
git rev-parse FETCH_HEAD > "$MW_SECURITY_STAGE/DEPLOY_COMMIT"
printf '%s\n' "$MW_SECURITY_STAGE"

sudo docker cp monitoring-prometheus:/bin/promtool "$MW_SECURITY_STAGE/promtool"
"$MW_SECURITY_STAGE/promtool" check config --syntax-only "$MW_SECURITY_STAGE/prometheus/prometheus.yml"
python3 "$MW_SECURITY_STAGE/scripts/validate-alerting.py" --promtool "$MW_SECURITY_STAGE/promtool"
python3 "$MW_SECURITY_STAGE/scripts/check-service-comparison-queries.py" "$MW_SECURITY_STAGE/grafana/provisioning/alerting/service-comparison-alerts.json" --dashboard "$MW_SECURITY_STAGE/grafana/provisioning/dashboards/json/matchwise-service-comparison.json"
```

The PromQL suite tests the original twelve rules with the new backend timing, including valid recent samples and expired success/failure. It structurally checks sixteen permanent rules and annotation pairs. The live preflight checks all current CPU/log rule datasource queries plus every Loki dashboard target, including bounded log queries. It prints counts/values, not raw log messages. Empty dashboard traffic is allowed; missing rule telemetry and syntax/HTTP errors fail. No backend traffic is generated by these checks. New backend freshness becomes testable against regular live samples only after cadence deployment.

A PromQL-teszt az új backend-időzítéssel ellenőrzi az eredeti 12 szabályt; a 16 állandó szabály szerkezete is ellenőrzött. A csak olvasó próba az összes új Loki-panelt is lekérdezi. Üres forgalmi panel önmagában nem hiba. A percenkénti backend frissessége telepítés után ellenőrizhető élesben.

## Apply after successful checks / Alkalmazás sikeres ellenőrzés után

Keep the same shell and MW_SECURITY_STAGE value. Record the printed stage path if reconnecting. Review git status before copying. The seven files below are existing files that will be backed up; no secrets, volumes or collector state are changed. Backup directory is private. Stop if any command fails.

Azonos shellben folytasd, megőrzött MW_SECURITY_STAGE értékkel. A hét meglévő éles fájlról mentés készül. Hiba esetén állj meg.

```bash
cd ~/ai-job-monitoring
git status --short
MW_SECURITY_BACKUP=$(mktemp -d /home/ubuntu/monitoring-private-state/security-update.XXXXXX)
(
set -eu
for file in prometheus/prometheus.yml blackbox/blackbox.yml grafana/provisioning/alerting/render-backend-alerts.json grafana/provisioning/alerting/service-comparison-alerts.json grafana/provisioning/dashboards/json/matchwise-service-comparison.json grafana/provisioning/dashboards/json/matchwise-unified-monitoring.json grafana/provisioning/dashboards/json/application-availability.json; do
  mkdir -p "$MW_SECURITY_BACKUP/$(dirname "$file")"
  cp -p "$file" "$MW_SECURITY_BACKUP/$file"
done
)
printf '%s\n' "$MW_SECURITY_BACKUP"
```

Check that all seven backups exist before proceeding. / Mind a hét mentés meglétét ellenőrizd folytatás előtt.

```bash
(
set -eu
for file in prometheus/prometheus.yml blackbox/blackbox.yml grafana/provisioning/alerting/render-backend-alerts.json grafana/provisioning/alerting/service-comparison-alerts.json grafana/provisioning/dashboards/json/matchwise-service-comparison.json grafana/provisioning/dashboards/json/matchwise-unified-monitoring.json grafana/provisioning/dashboards/json/application-availability.json; do
  test -f "$MW_SECURITY_BACKUP/$file"
  test -f "$MW_SECURITY_STAGE/$file"
done
for file in prometheus/prometheus.yml blackbox/blackbox.yml grafana/provisioning/alerting/render-backend-alerts.json grafana/provisioning/alerting/service-comparison-alerts.json grafana/provisioning/dashboards/json/matchwise-service-comparison.json grafana/provisioning/dashboards/json/matchwise-unified-monitoring.json grafana/provisioning/dashboards/json/application-availability.json; do
  install -m 644 "$MW_SECURITY_STAGE/$file" "$file"
done
sudo docker compose config --quiet
sudo docker compose up -d --no-deps --force-recreate blackbox-exporter prometheus
)
```

Single-file bind mounts are recreated so exporters/Prometheus read the new files. After about 60–90 seconds check:

Az egyedi fájlmountok miatt az érintett konténerek újralétrejönnek. Körülbelül 60–90 másodperc után:

```bash
curl -fsS http://127.0.0.1:9090/-/ready
curl -fsSG http://127.0.0.1:9090/api/v1/query --data-urlencode 'query=up{job="blackbox_render_backend"}'
curl -fsSG http://127.0.0.1:9090/api/v1/query --data-urlencode 'query=probe_success{job="blackbox_render_backend"}'
```

Proceed after successful probes, then load the new alert file:

Sikeres próba után töltsd be az új riasztásfájlt:

```bash
sudo docker restart monitoring-grafana
```

Check database=ok via /api/health; Service Comparison shows the new panels; service-comparison-security contains four rules and the total permanent count is sixteen. Check every rule's health, not just state. Query timestamp(probe_success{job="blackbox_render_backend"}) twice more than a minute apart; timestamps should advance. Use Prometheus target configuration to confirm scrapeInterval=1m and scrapeTimeout=15s. A dashboard screenshot alone does not prove cadence.

Ellenőrizd a health választ, a paneleket, a security csoport négy szabályát és a 16 állandó szabályt. A probe_success timestampje több mint egy perc különbséggel kérdezve lépjen előre. A Prometheus target beállítása legyen 1m/15s. Képernyőkép önmagában nem igazolja a gyakoriságot.

### Rollback / Visszaállítás

Restore the same seven files from the private backup and recreate Blackbox/Prometheus, then restart Grafana. Also provision deleteRules for only matchwise_backend_404_burst before restarting Grafana; restoring a source file alone does not delete the stored new rule. Do not delete existing rules, storage or collector state. Original pre-update backend cadence is 30m/110s/100s with a 40-minute freshness window.

Ugyanazt a hét fájlt állítsd vissza a privát mentésből, majd Blackbox/Prometheus újralétrehozás és Grafana-újraindítás kell. Az új matchwise_backend_404_burst UID-t külön deleteRules bejegyzéssel töröld; a régi fájl visszamásolása önmagában nem törli. A korábbi backend-beállítás 30m/110s/100s és 40 perces frissesség.

## Verification status / Ellenőrzési állapot

Local checks passed: sixteen-rule UID/annotation/reference/cycle checks, 35-panel unique-ID/grid checks, Python syntax, seven Python tests (four query-checker tests plus three fixture-isolation/cleanup tests) and Bash syntax validation of rollout commands. The updated full promtool suite and live Loki offset queries still require the staged Oracle run. No successful live deployment or 404 trigger is claimed yet.

Helyi szerkezeti, Python-szintaxis- és hét Python-teszt és a telepítési parancsok Bash-szintaxisellenőrzése sikeres. A teljes frissített promtool-csomag és az új Loki-lekérdezések éles ellenőrzése még hátravan. Telepítési sikert és valódi 404-riasztást még nem állítunk.

Sources: [Render free instances](https://render.com/docs/free), [Loki metric queries and offset](https://grafana.com/docs/loki/latest/query/metric_queries/).

## Oracle preflight confirmed / Oracle-ellenőrzés igazolt

Operator output from the staged snapshot /tmp/matchwise-security-update.3fTDyq confirms valid Prometheus configuration, PASS for twelve rules and 38 PromQL scenarios, successful source queries for all four security rules, and successful (empty) results for all Loki dashboard queries. This is a successful read-only preflight, not proof of deployment. Next: back up and apply the seven files, recreate Blackbox/Prometheus and load Grafana rules.

A felhasználó kimenete igazolta az érvényes konfigurációt és mind a 38 tesztesetet. A négy security-szabály lekérdezése sikeres; a Loki-panelek üres, de hibamentes választ adtak. Az éles telepítés és a percenkénti mintavétel ellenőrzése még hátravan.

## Backend cadence rollout confirmed / Backend-gyakoriság igazolt

Operator supplied post-apply output: Grafana /api/health returned database=ok, version=13.2.1. Both blackbox_render_backend and blackbox_vercel_frontend targets report scrapeInterval=1m, scrapeTimeout=15s and health=up. Backend probe_success=1 at query timestamp 1795025266.993. This verifies active target configuration and a successful current HTTP probe; a long-term no-sleep guarantee is not claimed. New security panel rendering, four-rule group health and an actual 404 threshold trigger remain to be verified. No main merge was performed.

A frissítés utáni kimenet szerint a Grafana működik, a backend és a frontend targetje is 1m/15s beállítású és up állapotú. A backend probe_success=1. A percenkénti beállítás és a sikeres HTTP-próba igazolt; a hosszú távú elalvásmentesség nem garantált. Az új panelek megjelenése, a security csoport négy szabályának health értéke és a valódi 404-próba még ellenőrzendő. Main összevonás nem történt.

## Panel confirmation and real 404 test / Panelek és valódi 404-próba

Operator confirmed all requested panels appeared after rollout. Individual four-rule Health values were not separately supplied. Next controlled test uses scripts/test-backend-404-once.py: at most twenty sequential GET requests to a unique, intentionally nonexistent path on the fixed MatchWise backend. It follows no redirects, uses no credentials, stops on unexpected status/network failure, limits request duration and never retries. These are real logs and may trigger the permanent security rule. Do not repeatedly rerun the script if an alert is delayed; first inspect log collection and rule health.

Az üzemeltető visszaigazolta a panelek megjelenését. A következő próba legfeljebb húsz egymás utáni GET-kérést küld egy nem létező tesztútvonalra. Nem használ hitelesítést, nem követ átirányítást, váratlan válasznál leáll, nem próbálkozik újra. Ez valódi naplókon át a valódi 404-riasztást teszteli. Késő értesítés miatt ne futtasd ismételten; előbb a collectort és a szabály health értékét ellenőrizd.

```bash
cd ~/ai-job-monitoring
git fetch origin feat/service-comparison
git show FETCH_HEAD:scripts/test-backend-404-once.py > /tmp/matchwise-test-backend-404-once.py
python3 /tmp/matchwise-test-backend-404-once.py
```

Expect twenty HTTP 404 results, then allow collection/evaluation/pending/grouping. A brief event burst can sustain the rolling count for two minutes without new requests. After those events leave the five-minute window, a successful evaluation clears the condition and Telegram may send resolved after grouping. Original event time is used, so unusually late ingestion can shorten the remaining alert window. Record firing and resolved separately; no live success is claimed for this test yet.

Húsz 404 választ várunk. Utána a begyűjtés, értékelés, kétperces pending és Telegram-csoportosítás idejét is hagyd lefutni. Újabb kérés nélkül is fennmaradhat a feltétel. Az események ötperces ablakból kikerülése után sikeres értékelés feloldja a feltételt. A firing és resolved külön rögzítendő; ennek a próbának a sikere még nincs igazolva.

## Real 404 result and reuse / Valódi 404-eredmény és újrafuttatás

Operator confirmed the whole 404 procedure completed successfully. This records operator-confirmed firing/recovery behavior without exact timestamps or raw output. The script and related programs are retained in Git; [repeatable test catalog](testing/README.md) is the entry point for future runs. Every new run needs its own evidence. A bounded functional check is not a DDoS test and proves no DDoS resistance.

Az üzemeltető visszaigazolta a teljes 404-próba sikerét. A program és a kapcsolódó tesztek Gitben megmaradnak; későbbi futtatáshoz az [újrafuttatható tesztek jegyzékét](testing/README.md) használd. Pontos időadat és nyers kimenet nem érkezett. A kis mennyiségű funkcionális próba nem DDoS-teszt, és nem bizonyít DDoS-állóságot.
