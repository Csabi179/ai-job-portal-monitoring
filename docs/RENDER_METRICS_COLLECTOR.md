# Render resource collector / Render erőforrásgyűjtő

**Current status / Jelenlegi állapot — 2026-11-18:** deployed and operator-verified from API to Prometheus / az API-tól a Prometheusig telepítve és az üzemeltető kimenetével igazolva. Separate from the log collector / a naplócollectortól külön program.

## Magyar

A Python program négy Render Metrics API-végpontot olvas: cpu, cpu-limit, memory és memory-limit. A CPU- és memóriahasználatot a saját kapacitáskorlátjuk százalékában is megadja. A kérések a Render API-nak mennek, nem a backend health végpontjára.

Alapértelmezésben csak kiírja a Prometheus-formátumú eredményt. Nem módosít szolgáltatást vagy mérési fájlt. A --write kapcsolóval atomikusan cseréli a ~/monitoring-exporter-metrics/matchwise_render_resources.prom fájlt; a szülőkönyvtárnak léteznie kell. Ezt a Node Exporter olvassa.

Egy szolgáltatáspéldányt támogat. Mind a négy mérés azonos szolgáltatáshoz, példányhoz és időponthoz kell tartozzon. Legfeljebb ötperces forrásadatot fogad el. Üres, több idősoros, elavult vagy hibás válasznál collection_success=0 jelenik meg, a használati értékek kimaradnak. Az alvó szolgáltatás hiányzó mérése nem jelent 0% használatot. Telepítés közben több példány adatai átmenetileg elutasíthatók.

A paneleknek és riasztásoknak a collection_success mellett a last_attempt és a source_timestamp frissességét is ellenőrizniük kell. Ha a program nem indul el vagy nem tud írni, a régi fájl megmaradhat.

### Egyszeri próba Oracle gépen

A meglévő Render-naplógyűjtő környezeti fájlját használjuk. API-kulcsot nem kell a parancsba írni. A parancs egy egyszeri folyamatot indít, nem telepít időzítőt. Siker esetén collection_success=1, CPU- és memóriaértékek láthatók. Csak a kimenetet küldd vissza, a környezeti fájlt ne.

## English

The Python script reads four Render Metrics API endpoints: cpu, cpu-limit, memory and memory-limit. It also shows CPU and memory use as a percentage of their own limits. Requests go to the Render API, not to the backend health endpoint.

By default, it only prints metrics. It does not change a service or a metrics file. With --write, it replaces ~/monitoring-exporter-metrics/matchwise_render_resources.prom atomically. The parent directory must exist. Node Exporter reads this file.

This first version supports one instance. All four readings must have the same resource, instance and sample time. Data older than five minutes is rejected. Empty, multiple-series, old or invalid data produces collection_success=0 without usage values. Missing data from a sleeping service is not 0% usage. Multiple instances during deployment can cause a temporary collection failure.

Panels and alerts must check collection_success and the age of last_attempt and source_timestamp. If the script cannot start or write, the old file may remain.

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

Four test methods passed: percentage calculation, nine invalid-input cases, atomic file replacement, and safe HTTP-error diagnostics. No live API access was used in these tests. Automatic collection, dashboard integration and alerts were subsequently deployed and checked as recorded below.

Négy tesztmetódus sikeres: százalékszámítás, kilenc hibás bemenet, atomikus fájlcsere és biztonságos HTTP-hibajelzés. Ezek nem éles API-tesztek. Az időzítő, dashboard és riasztások telepítése azóta megtörtént.


## Scheduled collection / Rendszeres gyűjtés

Operator verified successful file publication and Node Exporter ingestion on 2026-11-18: collection_success=1, CPU 0.14497778%, RAM 17.7024848991%, node_textfile_scrape_error=0. Prometheus ingestion and active timer were then confirmed by operator output.

The new timer runs two minutes after the previous run finishes. It makes four Render API requests per run. It does not call the backend application endpoint. Source samples must still be at most five minutes old. The root-owned installed script under /usr/local/lib/matchwise allows this feature to be tested without switching the live repository checkout. Update that installed copy when updating the collector. The service uses the existing environment file. No Docker restart is required. Timer/service operation on Oracle was confirmed by operator output.

Az időzítő az előző futás befejezése után két perccel indít új gyűjtést, futásonként négy API-kéréssel. A telepített program külön könyvtárba kerül, így nem kell átváltani az éles repó ágát. Későbbi programfrissítésnél ezt a példányt is frissíteni kell. A Node Exporter beolvasása igazolt; a Prometheusba beérkezést és az aktív időzítőt az üzemeltető kimenete igazolja.

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

## Verified behavior and earlier fixes / Igazolt működés és korábbi javítások

- Four Render API endpoints returned nonempty samples: CPU/cpu-limit unit cpu, memory/memory-limit unit bytes. Requests use resource and resolutionSeconds=60 with the API default window. Source timestamps are checked separately.
- The first collector request with explicit startTime/endTime returned HTTP 400. Removing those parameters to match the successful probe fixed collection. The exact rejected parameter was not isolated. Existing environment credentials worked.
- A later live sample showed CPU 0.14497778%, RAM 17.7024848991%, collection_success=1 and node_textfile_scrape_error=0.
- The systemd timer and Prometheus collection_success=1 were confirmed. Dashboard screenshots show the collected resources. Values above are dated samples, not current usage guarantees.
- Failure diagnostics print a trusted endpoint name and numeric HTTP status; secrets and raw response bodies remain hidden.

Mind a négy API-végpont adatai és mértékegységei igazoltak. A külön időablakot tartalmazó kérés 400-as hibát adott; az időablak-paraméterek elhagyása után a meglévő kulccsal működött. A fájlírás, Node Exporter, időzítő és Prometheus beérkezés külön is igazolt. A fenti számok a teszt idején mért minták, nem állandó terhelési értékek.

The service executes /usr/local/lib/matchwise/render-metrics-poll.py. Updating the GitHub script or live checkout alone does not update that installed copy. Follow the installation commands to publish the new version. No branch merge or exact current live checkout HEAD is asserted by these checks.

A szolgáltatás a /usr/local/lib/matchwise/render-metrics-poll.py példányt futtatja. A GitHubon lévő fájl frissítése önmagában ezt nem frissíti; telepítéskor a külön példányt is cserélni kell. A tesztek nem igazolják az éles checkout pontos HEAD-jét vagy a main merge-et.
