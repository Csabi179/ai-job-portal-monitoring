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
