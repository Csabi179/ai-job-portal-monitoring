# Render resource collector / Render erőforrásgyűjtő

## Magyar

A Python program négy Render Metrics API-végpontot olvas: cpu, cpu-limit, memory és memory-limit. A CPU- és memóriahasználatot a saját kapacitáskorlátjuk százalékában is megadja. A kérések a Render API-nak mennek, nem a backend health végpontjára.

Alapértelmezésben csak kiírja a Prometheus-formátumú eredményt. Nem módosít szolgáltatást vagy mérési fájlt. A --write kapcsolóval atomikusan cseréli a ~/monitoring-exporter-metrics/matchwise_render_resources.prom fájlt; a szülőkönyvtárnak léteznie kell. Ezt később a Node Exporter olvassa.

Egy szolgáltatáspéldányt támogat. Mind a négy mérés azonos szolgáltatáshoz, példányhoz és időponthoz kell tartozzon. Legfeljebb ötperces forrásadatot fogad el. Üres, több idősoros, elavult vagy hibás válasznál collection_success=0 jelenik meg, a használati értékek kimaradnak. Az alvó szolgáltatás hiányzó mérése nem jelent 0% használatot. Telepítés közben több példány adatai átmenetileg elutasíthatók.

A későbbi paneleknek és riasztásoknak a collection_success mellett a last_attempt és a source_timestamp frissességét is ellenőrizniük kell. Ha a program nem indul el vagy nem tud írni, a régi fájl megmaradhat.

### Egyszeri próba Oracle gépen

A meglévő Render-naplógyűjtő környezeti fájlját használjuk. API-kulcsot nem kell a parancsba írni. A parancs egy egyszeri folyamatot indít, nem telepít időzítőt. Siker esetén collection_success=1, CPU- és memóriaértékek láthatók. Csak a kimenetet küldd vissza, a környezeti fájlt ne.

## English

The Python script reads four Render Metrics API endpoints: cpu, cpu-limit, memory and memory-limit. It also shows CPU and memory use as a percentage of their own limits. Requests go to the Render API, not to the backend health endpoint.

By default, it only prints metrics. It does not change a service or a metrics file. With --write, it replaces ~/monitoring-exporter-metrics/matchwise_render_resources.prom atomically. The parent directory must exist. Node Exporter can read this file later.

This first version supports one instance. All four readings must have the same resource, instance and sample time. Data older than five minutes is rejected. Empty, multiple-series, old or invalid data produces collection_success=0 without usage values. Missing data from a sleeping service is not 0% usage. Multiple instances during deployment can cause a temporary collection failure.

Future panels and alerts must check collection_success and the age of last_attempt and source_timestamp. If the script cannot start or write, the old file may remain.

### One-time Oracle test

Use the existing Render log collector environment file. Do not put the API key in the command. This starts one process and does not install a timer. A successful run prints collection_success=1 plus CPU and memory values. Share the output only, not the environment file.

```bash
cd ~/ai-job-monitoring
git fetch origin feat/service-comparison
git show FETCH_HEAD:scripts/render-metrics-poll.py > /tmp/matchwise-render-metrics-poll.py
sudo systemd-run --unit=matchwise-render-metrics-check --wait --pipe --collect --property=User=ubuntu --property=EnvironmentFile=/home/ubuntu/monitoring-private-secrets/render-logs.env /usr/bin/python3 /tmp/matchwise-render-metrics-poll.py
```

## Local verification / Helyi ellenőrzés

From scripts: python3 -m unittest -v test_render_metrics.py

Three test methods passed: percentage calculation, nine invalid-input cases, and atomic file replacement. No live API access was used in these tests. Automatic collection, dashboard integration and alerts follow after the Oracle test.

Három tesztmetódus sikeres: százalékszámítás, kilenc hibás bemenet és atomikus fájlcsere. Ezek nem éles API-tesztek. Az Oracle-próba után következik az időzítő, a dashboard és a riasztások.

## Oracle dry-run status / Oracle-próba állapota

2026-11-18: the first collector dry run failed with HTTPError. The status code was not recorded, so the cause is not yet known. The earlier interactive probe succeeded; the collector uses the existing environment file and adds time-window parameters. Either difference needs investigation. Do not change credentials based on this result alone.

The collector now reports only the endpoint name and HTTP status code. Response bodies, headers and credentials remain hidden. Four local tests pass, including safe diagnostics for HTTP 400, 401, 403, 429 and 500. Repeat the one-time command above to obtain the status. Automatic rollout remains pending.

Az első Oracle-próba HTTP-hibával végződött, de a státuszkód még nem ismert. A korábbi sikeres próba kézzel bekért kulcsot használt, a gyűjtő pedig a meglévő környezeti fájlból olvas, és időablakot is megad. A hiba oka még nincs igazolva. A javított üzenet megmutatja a végpontot és a HTTP-kódot, titkos adatot nem ír ki. A négy helyi teszt sikeres. Következő lépés a fenti egyszeri próba megismétlése; az automatikus telepítés még vár.

## HTTP 400 follow-up / Javítás

The second Oracle run returned cpu: HTTP 400. Removed explicit startTime/endTime parameters to match the successful probe. The collector now uses the API default time window and still rejects samples older than five minutes. Four local tests passed. Live confirmation is pending; the exact rejected parameter is not yet proven.

A második próba cpu: HTTP 400 hibát adott. A kérésből eltávolítottuk a külön megadott időablakot, így a korábban sikeres próba kérését használjuk. Az ötperces frissességellenőrzés megmarad. Négy helyi teszt sikeres; az éles megerősítés még hátravan. A konkrét elutasított paraméter még nem bizonyított.

## Successful Oracle dry run / Sikeres Oracle-próba

2026-11-18: operator confirmed exit status 0 and collection_success=1 after removing explicit time-window parameters. CPU 0.14924444%, memory 17.7024848991%. Source timestamp 1795015320, collection timestamp 1795015346.67 (about 27 seconds old). Existing environment credentials worked. This validates API collection and calculation, not yet textfile ingestion or scheduled collection.

A gyűjtő éles próbája sikeres. A meglévő kulcs működik; a friss adat feldolgozása igazolt. A következő lépés az egyszeri .prom fájlírás és a Node Exporter ellenőrzése. Az automatikus futtatás még nincs telepítve.

Run the same transient systemd command with --write --output /home/ubuntu/monitoring-exporter-metrics/matchwise_render_resources.prom appended after the Python script. Then inspect http://127.0.0.1:9100/metrics for matchwise_render_ metrics and node_textfile_scrape_error. This writes a real metrics file but does not schedule collection. A one-time file becomes stale; it must not be treated as current indefinitely.

## Scheduled collection / Rendszeres gyűjtés

Operator verified successful file publication and Node Exporter ingestion on 2026-11-18: collection_success=1, CPU 0.14497778%, RAM 17.7024848991%, node_textfile_scrape_error=0. Prometheus ingestion remains to be checked.

The new timer runs two minutes after the previous run finishes. It makes four Render API requests per run. It does not call the backend application endpoint. Source samples must still be at most five minutes old. The root-owned installed script under /usr/local/lib/matchwise allows this feature to be tested without switching the live repository checkout. Update that installed copy when updating the collector. The service uses the existing environment file. No Docker restart is required. Timer/service validation on Oracle is still pending.

Az időzítő az előző futás befejezése után két perccel indít új gyűjtést, futásonként négy API-kéréssel. A telepített program külön könyvtárba kerül, így nem kell átváltani az éles repó ágát. Későbbi programfrissítésnél ezt a példányt is frissíteni kell. A Node Exporter beolvasása igazolt; a Prometheus és az időzítő ellenőrzése még hátravan.

Run each command in order; stop if one fails. / A parancsokat sorrendben futtasd; hiba esetén állj meg.

```bash
cd ~/ai-job-monitoring
git fetch origin feat/service-comparison
git show FETCH_HEAD:scripts/render-metrics-poll.py > /tmp/matchwise-render-metrics-poll.py
git show FETCH_HEAD:systemd/matchwise-render-metrics.service > /tmp/matchwise-render-metrics.service
git show FETCH_HEAD:systemd/matchwise-render-metrics.timer > /tmp/matchwise-render-metrics.timer

sudo install -d -m 755 /usr/local/lib/matchwise
sudo install -m 644 /tmp/matchwise-render-metrics-poll.py /usr/local/lib/matchwise/render-metrics-poll.py
sudo install -m 644 /tmp/matchwise-render-metrics.service /etc/systemd/system/matchwise-render-metrics.service
sudo install -m 644 /tmp/matchwise-render-metrics.timer /etc/systemd/system/matchwise-render-metrics.timer
sudo systemd-analyze verify /etc/systemd/system/matchwise-render-metrics.service /etc/systemd/system/matchwise-render-metrics.timer
sudo systemctl daemon-reload
sudo systemctl start matchwise-render-metrics.service
sudo systemctl enable --now matchwise-render-metrics.timer
systemctl list-timers matchwise-render-metrics.timer --no-pager
curl -fsSG http://127.0.0.1:9090/api/v1/query --data-urlencode 'query=matchwise_render_metrics_collection_success'
```

Wait for the next Prometheus scrape (about one minute) if the query result is initially empty. Expect value 1 and a scheduled next timer run. Do not share environment file contents.

Ha a Prometheus eredménye kezdetben üres, körülbelül egy perc múlva ismételd a lekérdezést. A várt érték 1, az időzítőnél pedig látszódjon a következő futás.

Rollback / Visszaállítás:

```bash
sudo systemctl disable --now matchwise-render-metrics.timer
sudo systemctl stop matchwise-render-metrics.service
sudo rm -f /home/ubuntu/monitoring-exporter-metrics/matchwise_render_resources.prom
```

This removes only the new resource metrics file. Existing log collector metrics remain. Failure diagnosis: sudo journalctl -u matchwise-render-metrics.service -n 30 --no-pager.
