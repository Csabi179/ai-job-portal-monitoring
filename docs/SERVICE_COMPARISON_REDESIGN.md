# MatchWise összehasonlító dashboard · 6. verzió

Az alapnézet az állapotot, a forgalmat és a terhelést mutatja ebben a sorrendben. A fő nézetben nincs két külön függőleges tengely egy grafikonon. Kék: frontend; narancs: backend; zöld: adatbázis; lila: Oracle. Az elérhetőségi kártyák ettől függetlenül zöld/piros/szürke állapotszíneket használnak.

## Olvasási sorrend

1. Frontend és backend HTTP-próba; PostgreSQL-kapcsolat; Oracle telemetriafogadó scrape.
2. Böngészőcsomag és sikeres backend-naplógyűjtés kora; elfogadott összesítések a fogadó indulása óta. A csomagszám nem kérés- vagy felhasználószám.
3. Frontend API-indítások és HTTP-válaszok a backend naplózott API-kérései mellett; azonos kérés/perc egység, 5 perces átlag. A válaszvonal szaggatott.
4. Böngésző válaszfejlécekig mért átlag/P95 és backend-feldolgozási P95. Közös időegység, eltérő mérési szakaszok; a böngészős P95 becslés és szaggatott vonal.
5. Külön panelek: backend API/perc, lezárt DB-tranzakció/s, CPU%; alatta backend P95, PostgREST-várakozók, memória%. Közös időtengely, minden panelnek saját, feliratozott egysége van.
6. Lenyitható részletek: erőforrások és gyűjtés; HTTP-hibák/biztonsági jelzések; naplók; régi két tengelyes összevetések; adatforrások és útmutató.

Az alapértelmezett időablak 1 óra; a frissítés továbbra is 1 perc. Minden korábbi panel és lekérdezés megmaradt az eredeti azonosítójával. Az új összefoglaló panelek meglévő kifejezéseket használnak. A UID és a Supabase-változó változatlan. A fő nézet 16 tartalmi panelből áll; a részletek alapból csukva vannak.

## Értelmezési korlátok

- Hiányzó adat nem nulla; a nullák közötti rést nem kötjük össze. A mért nulla továbbra is megjelenhet.
- A fogadó elérhetősége nem bizonyít böngészőforgalmat. Az üres csomag életjel; bezárt böngésző mellett a csomag kora nőhet frontendkiesés nélkül.
- Az új számlálósor első mintájának eseményei még nem feltétlenül látszanak a rate-görbén. A későbbi csomagok önmagukban sem jelentenek új API-kéréseket.
- A frontend a mérőkódot futtató böngészőket, a backend a naplózott API-kéréseket látja. Nem várunk pontos számegyezést; a késleltetett beküldés időbeli eltolódást okozhat.
- A CPU/memória százalék saját szolgáltatáskapacitásra vonatkozik; a gépek és memóriafogalmak eltérnek. Render CPU: API-minta; Supabase/Oracle CPU: 5 perces átlag.
- A DB-tranzakciók belső és más kliensektől származó munkát is tartalmaznak. A PostgREST-sor nem általános DB-várakozásszámláló.
- Együttmozgás önmagában nem ok-okozati bizonyíték; a hibaszámok nem támadásbizonyítékok.

## Ellenőrzés és telepítés

`scripts/validate-dashboard-redesign.py CANDIDATE BASELINE` ellenőrzi a panelazonosítókat, a megőrzött kifejezéseket/adatforrásokat/lekérdezési módokat, az új panelek forrásait, a hiányzóadat-kezelést és az elrendezést. Nincs hálózati forgalma.

`scripts/check-frontend-comparison-queries.py DASHBOARD --overview` az alapnézet 23 metrikalekérdezését ellenőrzi helyben a Prometheus/Loki API-kon. A `--include-database` a korábbi 15 összevetési kifejezést ellenőrzi, már lenyitott sorokban is. Mindkettő csak olvas; az üres eredmény nem hiba, és nem bizonyít nulla forgalmat.

Az Oracle-on az `install-dashboard-redesign.sh COMMIT_SHA` a monitoring checkoutból futtatandó. A commit teljes SHA-val rögzített legyen. A segéd a `922aeaee8108db1f8ee91260971170eda5846f56` commit dashboardját tekinti ismert kiindulási állapotnak; ismeretlen élő eltérésnél leáll. Statikus és élő lekérdezési ellenőrzés után mentést készít a `/home/ubuntu/monitoring-backups/dashboard-redesign.*` könyvtárba, és kizárólag a provisionált összehasonlító JSON-t cseréli.

Nincs checkoutváltás, pull, reset, új riasztás vagy szolgáltatás-újraindítás. A monitoring fejlesztési ága nem kerül main-be. A Grafana meglévő fájlfigyelője beolvassa a változást; legfeljebb 60 másodperc után böngészőfrissítés és tényleges képi ellenőrzés szükséges. A segéd kiírja az egyfájlos visszaállítás parancsát.

Az elrendezési előnézet szándékosan nem tartalmaz kitalált mérési adatokat. A helyi elrendezésellenőrzés nem helyettesíti a telepítés utáni Grafana-képernyőkép ellenőrzését.

Grafana megjelenítési beállítások: [idősorok](https://grafana.com/docs/grafana/latest/visualizations/panels-visualizations/visualizations/time-series/) és [egyedi egységek](https://grafana.com/docs/grafana/latest/visualizations/panels-visualizations/configure-standard-options/).
