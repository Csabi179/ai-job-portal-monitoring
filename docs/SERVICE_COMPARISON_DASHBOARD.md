# Service Comparison dashboard / Összehasonlító dashboard

## Magyar

Név: MatchWise · Service Comparison. Mappa: AI Job Portal. URL: /d/matchwise-service-comparison.
A négy oszlop: Render backend, Supabase adatbázis, Vercel frontend, Oracle monitoring VM.

Az egymás melletti CPU- és memóriapanelek 0–100%-os skálát használnak. Minden százalék az adott szolgáltatás saját kapacitásához viszonyul; a gépek eltérő méretűek. Oracle/Supabase CPU: ötperces átlag, Render CPU: API-minta. Az időbeli változásokat érdemes összevetni. A backend magasabb terhelése önmagában nem bizonyít támadást.

A Render használati panel csak sikeres gyűjtés, négy percnél frissebb gyűjtési kísérlet, öt percnél frissebb forrásminta, elérhető Node Exporter és hibamentes textfile-beolvasás mellett mutat értéket. Hiányzó adatnál rés marad. Frontend CPU/RAM: Not collected. Az elérhetőségi sor eltérő ellenőrzéseket jelöl: backend/frontend HTTP-próba, Supabase adatbázis-kapcsolat, Oracle metrikalekérés.

A backend forgalma, hibái, válaszideje és hibanaplói a közös időablakban láthatók, health kérések nélkül. A többi szolgáltatás naplóit jelenleg nem gyűjtjük. Üres backend naplópanel lehet forgalomhiány vagy hiányzó napló; ellenőrizd a collector korát. Backend HTTP-próba: 30 percenként, legfeljebb 40 perces eredménnyel. Frontend: legfeljebb 3 perces eredmény.

Éles bizonyíték: a felhasználó kimenete alapján a Render időzítő aktív és a Prometheus collection_success=1 értéket tárol (2026-11-18). A dashboard helyi szerkezetellenőrzése sikeres; éles megjelenés és lekérdezések ellenőrzése még hátravan. Riasztásokat ez a dashboard nem telepít.

## English

Name: MatchWise · Service Comparison. Folder: AI Job Portal. URL: /d/matchwise-service-comparison.
Four columns show Render backend, Supabase database, Vercel frontend and Oracle monitoring VM.

CPU and memory panels use the same 0–100% scale. Each percentage uses the service's own capacity. Machines have different sizes. Oracle/Supabase CPU uses a five-minute average; Render CPU uses API samples. Compare changes over time. Higher backend usage alone does not prove an attack.

Render usage is shown only when collection succeeds, the attempt is under four minutes old, the source is under five minutes old, Node Exporter is available and textfile reading has no errors. Missing data leaves a gap. Frontend CPU/RAM says Not collected. The status row uses different checks: HTTP probes for backend/frontend, database connectivity for Supabase, metrics collection for Oracle.

Backend traffic, errors, response times and error logs use the same time range and exclude health requests. Logs from other services are not collected here. An empty backend log panel can mean no traffic or missing logs; check collector age. Backend probes run every 30 minutes and results are used for up to 40 minutes. Frontend results are used for up to three minutes.

Live evidence: operator output confirms the Render timer is active and Prometheus stores collection_success=1 on 2026-11-18. Dashboard structure checks passed: JSON parsing, unique panel IDs, no grid overlaps and resolved filters. Live display and query validation are pending. This dashboard does not install alerts.

## Installation / Telepítés

The existing Grafana provider reads the JSON directory every 30 seconds. No restart is needed. Run from the live repository without changing its branch. This creates one untracked dashboard file; when switching to the feature branch later, move this exact file outside the checkout first if Git reports it would be overwritten.

A Grafana 30 másodpercenként beolvassa a könyvtárat. Az alábbi telepítés egy új, helyben még nem verziókövetett fájlt hoz létre; későbbi ágváltásnál, ha a Git ütközést jelez, előbb helyezd a fájlt a repón kívülre.

```bash
cd ~/ai-job-monitoring
git fetch origin feat/service-comparison
git show FETCH_HEAD:grafana/provisioning/dashboards/json/matchwise-service-comparison.json > /tmp/matchwise-service-comparison.json
python3 -m json.tool /tmp/matchwise-service-comparison.json > /dev/null
install -m 644 /tmp/matchwise-service-comparison.json grafana/provisioning/dashboards/json/matchwise-service-comparison.json
```

Open the dashboard after about 30 seconds. Verify Render CPU/RAM, Supabase/Oracle resource graphs, frontend Not collected messages, status panels and backend log queries. Check that a Viewer account can open it. Historical Render data exists only since the collector was started.

Körülbelül 30 másodperc után nyisd meg. Ellenőrizd a Render CPU/RAM adatokat, a Supabase/Oracle grafikonokat, a Frontend Not collected jelölést és a naplólekérdezéseket. Viewer jogosultságú fiókkal is ellenőrizd a hozzáférést. Render előzményadat csak a gyűjtés indulásától van.

If any panel shows a query error, share the panel title and error text. Alert rules are the next stage after this check.

Ha egy panel lekérdezési hibát jelez, a panel címét és a hiba szövegét küldd vissza. Ezután következnek a riasztási szabályok.
