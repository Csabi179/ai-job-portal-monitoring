# Service Comparison dashboard / Összehasonlító dashboard

> **Állapot / State (2026-11-18):** a 41 paneles frontend–backend változat Oracle-on és képpel igazolt. A fejlesztési ág most 45 panelt készít elő; a négy új backend–Supabase panel lekérdezéspróbája és telepítése még hátravan. A 16 állandó riasztáson nem változtatunk; main merge nincs.

## Magyar

Név: MatchWise · Service Comparison. Mappa: AI Job Portal. URL: /d/matchwise-service-comparison.
A négy oszlop: Render backend, Supabase adatbázis, Vercel frontend, Oracle monitoring VM.

Az egymás melletti CPU- és memóriapanelek 0–100%-os skálát használnak. Minden százalék az adott szolgáltatás saját kapacitásához viszonyul; a gépek eltérő méretűek. Oracle/Supabase CPU: ötperces átlag, Render CPU: API-minta. Az időbeli változásokat érdemes összevetni. A backend magasabb terhelése önmagában nem bizonyít támadást.

A Render használati panel csak sikeres gyűjtés, négy percnél frissebb gyűjtési kísérlet, öt percnél frissebb forrásminta, elérhető Node Exporter és hibamentes textfile-beolvasás mellett mutat értéket. Hiányzó adatnál rés marad. Frontend CPU/RAM: Not collected. Az elérhetőségi sor eltérő ellenőrzéseket jelöl: backend/frontend HTTP-próba, Supabase adatbázis-kapcsolat, Oracle metrikalekérés.

A backend forgalma, hibái, válaszideje és hibanaplói a közös időablakban láthatók, health kérések nélkül. A többi szolgáltatás naplóit jelenleg nem gyűjtjük. Üres backend naplópanel lehet forgalomhiány vagy hiányzó napló; ellenőrizd a collector korát. A frissítésben backend HTTP-próba: percenként, legfeljebb 3 perces eredménnyel. Frontend: legfeljebb 3 perces eredmény.

Éles bizonyíték: a felhasználó kimenete alapján a Render időzítő aktív és a Prometheus collection_success=1 értéket tárol (2026-11-18). A dashboard helyi szerkezetellenőrzése sikeres; a felhasználó képei az éles megjelenést és a látható panelek adatait is igazolják. Riasztásokat ez a dashboard nem telepít.

## English

Name: MatchWise · Service Comparison. Folder: AI Job Portal. URL: /d/matchwise-service-comparison.
Four columns show Render backend, Supabase database, Vercel frontend and Oracle monitoring VM.

CPU and memory panels use the same 0–100% scale. Each percentage uses the service's own capacity. Machines have different sizes. Oracle/Supabase CPU uses a five-minute average; Render CPU uses API samples. Compare changes over time. Higher backend usage alone does not prove an attack.

Render usage is shown only when collection succeeds, the attempt is under four minutes old, the source is under five minutes old, Node Exporter is available and textfile reading has no errors. Missing data leaves a gap. Frontend CPU/RAM says Not collected. The status row uses different checks: HTTP probes for backend/frontend, database connectivity for Supabase, metrics collection for Oracle.

Backend traffic, errors, response times and error logs use the same time range and exclude health requests. Logs from other services are not collected here. An empty backend log panel can mean no traffic or missing logs; check collector age. In the pending update, backend probes run every minute and results are used for up to three minutes. Frontend results are used for up to three minutes.

Live evidence: operator output confirms the Render timer is active and Prometheus stores collection_success=1 on 2026-11-18. Dashboard structure checks passed: JSON parsing, unique panel IDs, no grid overlaps and resolved filters. Operator screenshots confirm live display and visible panel data. This dashboard does not install alerts.

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

## Evidence update / Ellenőrzési kiegészítés — 2026-11-18

Operator screenshots confirm the four-column layout, Render/Supabase/Oracle resources, Vercel Not collected cards, statuses, ages and backend log context. No independent Viewer-account check was supplied for this new dashboard. Existing Viewer access to Unified Monitoring does not automatically grant access here.

A négyoszlopos elrendezés és a látható adatok a felhasználó képeivel igazoltak. Az új dashboard Viewer-fiókos ellenőrzése nem történt meg; a Unified Monitoring meglévő jogosultsága ezt nem adja meg automatikusan.

## Security panels / Biztonsági panelek

The pending revision adds eight panels, bringing this dashboard to 35 panels: 401/403/404/429 count cards, rates, traffic comparison and security logs. [Interpretation and rollout](SECURITY_OVERVIEW_AND_FREQUENT_PROBES.md). / A frissítés nyolc új panellel összesen 35 panelt tartalmaz; az éles megjelenés ellenőrzése még hátravan.

## Frontendforgalmi bővítés – 2026-11-18

A fejlesztési ág 41 panelt tartalmaz; a korábbi 35 panel változatlan.
A hat új panel (37–42) Oracle-ra telepítve; felhasználói kimenettel és képpel igazolva:

| ID | Tartalom |
| --- | --- |
| 37 | Lefedettség, hiányzó adatok és a kézi teszt értelmezése |
| 38 | A fogadó Prometheus-scrape állapota; nem böngészős küldési állapot |
| 39 | Utolsó elfogadott csomag kora, beleértve az üres kézi próbát |
| 40 | Deduplikált csomagok száma a fogadó indulása óta; nem API-kérésszám |
| 41 | Frontend API-indítások és HTTP-válaszok, backend naplózott /api kérések: közös 5 perces, kérés/perc grafikon |
| 42 | Böngészős fetch-fejléc átlag és becsült P95, backend feldolgozási P95: közös 5 perces kontextus |

A forgalmi/latenciapanelek vegyes Prometheus/Loki adatforrást használnak.
A frontend mode=real adatait mutatják, csak sikeres scrape és 3 percen belüli
elfogadott csomag mellett. Nincs hiányzó adatot nullával helyettesítő fallback,
nincs hiányokon át összekötött vonal. Az üres kézi teszt önmagában nem hoz
létre üzleti forgalmi idősorokat; ezek most várhatóan üresek.
A frontend latencia kizárólag outcome=http adatot használ, pozitív megfigyelési
ráta mellett. A frontend P95 kosarakból becsült érték.

A backend összehasonlító görbék a /api és /api/... útvonalakat, valamint a
naplóban relatív auth/cv/jobs/profile/preferences/me API-csoportokat számolják,
/api/health és /health nélkül. Ez szűkebb lefedettség, mint a dashboard
korábbi, minden nem-health útvonalat számláló backendpaneljei.
A nem mért direkt fetch-ek, közvetlen backendhívások, megszakítások, cache,
mock mód, gyűjtési késés és újraküldés miatt nincs elvárt pontos egyezés.
A backend és a frontend ideje eltérő időhatárt mér, nem vonhatók ki
pontos hálózati késésként. Nincs új riasztás.

Ellenőrzés: JSON érvényes; 41 egyedi panelazonosító; 6 új panel és 9 lekérdezés;
a korábbi 35 panel JSON-tartalma változatlan; az új panelek nem fedik át a régieket.
A kilenc lekérdezés Oracle-próbája és az új rész Grafana-megjelenése sikeres, felhasználói kimenettel és képpel igazolva.
A scripts/check-frontend-comparison-queries.py dashboard.json parancs a
9 új lekérdezést olvasással ellenőrzi. Az üres eredmény nem hiba és nem aktív
frontendmérés igazolása; lekérdezési hiba vagy warning esetén nem PASS.
A Supabase meglévő CPU/RAM paneljei megmaradtak; külön adatbázis-aktivitás/
várakozás összehasonlítása ebben a bővítésben még nincs megvalósítva.

## Paneltelepítés visszaigazolva – 2026-11-18

A felhasználó képe szerint a fogadó UP, a csomagszám 1, az egyszeri
üres próba kora 15,9 perc. A két forgalmi/latencia grafikon No matching telemetry.
Mentés: /home/ubuntu/monitoring-backups/frontend-dashboard.UnZHUI.
A Grafana health database=ok, version=13.2.1. Az automatikus frontendmérés
még nincs aktiválva; valódi forgalmi görbéket, eltérések felismerését és
Viewer-hozzáférést ez a kép nem igazol. Main összevonás nincs.

## Backend útvonalszűrés diagnózisa és javítása – 2026-11-18

A felhasználó Oracle-diagnosztikája success eredményű:
collector siker kora ~70,2 s; frontend indítások/válaszok kumulatív száma 9/9;
15 percben 229 backend napló és 229 értelmezhető HTTP-esemény,
6 non-health esemény, 0 hiányzó route. A /api előtagszűrés üres,
a relatív auth/cv/jobs/profile/preferences/me szűrés 6 eseményt ad.
Naplózott időadat is elérhető. Ez igazolja, hogy az új panelek kötelező /api
előtagja zárta ki a meglévő nem-health API-forgalmat. Az Express/logger
pontos belső előtagkezelését ezzel külön nem vizsgáltuk.

A 41 C és 42 C backendlekérdezéseinek szűrőjét javítottuk:
route=~"(/api(/.*)?|/(auth|cv|jobs|profile|preferences|me)(/.*)?)".
A health kizárás megmaradt. Ismeretlen relatív root útvonalakat nem veszünk fel
vakon; ezek később külön lefedettségi vizsgálatot igényelhetnek.
A két összehasonlító panelen kívül minden panel változatlan, összesen 41 panel.
A JSON-ellenőrzés és az előtagos/relatív, illetve kizárandó útvonalak helyi
regexpróbái sikeresek. Az új LogQL élő preflightja és a javított dashboard
Oracle-telepítése még hátravan. A rögzített javítási commit:
594564ac5d7297f5814ac68daeb84f17a379682f.

A 9/9 frontendérték a fogadó indulása óta kumulatív, a 6 backendérték 15 perces
ablakot fed. Ezeket nem hasonlítjuk közvetlenül és nem jelöljük eltérésnek.
A grafikonok azonos 5 perces ablakot használnak, de a mintavétel, kézbesítés,
eltérő lefedettség és kezdeti counter-idősorok miatt akkor sincs kötelező egyezés.
A javítás után friss normál kérés és a collector átfutása mellett ellenőrzünk.
Main merge és új riasztás nincs.

## Frontend–backend közös görbék igazolva – 2026-11-18

A felhasználó új képe már a Backend logged API requests/min és Backend processing
P95 görbéit is mutatja a frontend görbék mellett. Fogadó UP, 36 elfogadott csomag,
utolsó csomag kora 1,50 perc. Ez a relatív útvonalszűrés javításának megjelenési
bizonyítéka az SSH/Vite tesztben. Nem éles Vercel-aktiválás és nem terheléses teszt.

## Backend–Supabase bővítés előkészítve: 45 panel

A korábbi 41 panel változatlan; négy új panel, még nincs telepítve:
- 43: lefedettségi és mértékegység-magyarázat.
- 44: backend API requests/min (bal tengely) és Supabase committed transactions/s (jobb).
- 45: Render CPU % (bal) és Supabase committed transactions/s (jobb).
- 46: backend feldolgozási P95 ms (bal) és PostgREST pool waiting requests (jobb).

A Supabase-lekérdezéseket a már meglévő Unified Monitoring dashboardból vesszük:
pg_stat_database_xact_commit_total és pgrst_db_pool_waiting.
Minden DB-sor a kiválasztott supabase_instance értékre szűr, és sikeres
up/pg_up mellett látszik. Hiányzó adatoknál nem készítünk nullaértéket.
A tranzakciószám projekt-/adatbázisszintű aktivitás, belső szolgáltatásokat
és más klienseket is tartalmazhat; nem backend-kérésszámláló.
A várakozási sor kizárólag PostgREST kapcsolatkészlet, nem PostgreSQL lock-wait
és nem a teljes adatbázis várakozási sora. A 60 másodperces scrape rövid tüskéket kihagyhat.

A közös időtengely trendek megfigyelésére szolgál. Két külön tengely miatt
a görbék metszése vagy azonos magassága nem számszerű egyezés és nem ok-okozati bizonyíték.
Az 5 perces tranzakció- és backend-ráták mellett a CPU Render API-minta,
a queue pedig scrape-pillanatkép. Nem adunk automatikus rendellenesség-riasztást.

Ellenőrzés: érvényes JSON, 45 egyedi panel, 15 lekérdezés a 37–46 panelcsoportban,
a korábbi 41 panel változatlan. Python-szintaxisellenőrzés sikeres.
Oracle-preflight: check-frontend-comparison-queries.py dashboard.json --include-database.
Ez a dashboard alapértelmezett Supabase-instance változóját helyettesíti a tesztben.
Az új DB-metrikák aktuális adata, az élő lekérdezések és a Grafana-megjelenés még ellenőrizendő.
