# Frontend részletmérés · dashboard v8 / fogadómetrikák v2

> **Aktuális telepítési állapot — 2026-11-19:** Az üzemeltető minden átadott módosítást már alkalmazott az Oracle-on. A monitoringág bekerült a `main` ágba (`10f43d1`); emiatt nincs újratelepítési feladat. [Aktuális állapot](DEPLOYMENT_STATUS.md). A korábbi bevezetési bejegyzések történeti állapotok; a parancsok későbbi frissítéshez vagy helyreállításhoz maradnak meg.

Az éles frontend meglévő, 60 másodpercenként küldött v1 csomagjait használjuk. Nincs frontendkód-, Vercel- vagy környezetiváltozó-módosítás. A monitoring fejlesztése azóta bekerült a `main` ágba; az üzemeltető a telepítést már elvégezte.

## Megjelenítés

A fő nézet megmaradt; a felhasználó kérésére a backend-naplók és az általános adatforrás/mérési útmutató külön sorai kikerültek. Új, alapból csukott `06 · Frontend részletek · útvonalak, hibák és adatküldés` szakasz került alulra: 25 tartalmi panel, 26 Prometheus-lekérdezés. A frissítés 1 perc; a sebességek 5 perces átlagok. A részletes útvonalpanelek egységes útvonalcsoport-színeket használnak.

| Küldött adat | Felhasználás |
| --- | --- |
| starts: route, method, count | Útvonal- és metódusbontású API-indítás/perc; indítások a fogadó indulása óta |
| results: route, method, outcome, status, count | HTTP-státuszok; HTTP-hibaarány; útvonalankénti 4xx/5xx; hálózati hibák és megszakítások; metódus/kimenetel bontás; megfigyelt eredményösszeg |
| duration_sum_ms, count | Átlag a válaszfejlécekig, útvonalanként is |
| duration_bins, duration_limits_ms | Hisztogram és becsült P95, útvonalanként is |
| duration_max_ms | Pontos megfigyelt legnagyobb fejlécekig mért idő, útvonalanként, a fogadó indulása óta |
| inflight | Az utoljára jelentő lap csomagkészítéskori folyamatban lévő kérései |
| delivery.sent_batches | Utoljára jelentett sikeres küldésszámláló |
| delivery.failed_attempts / dropped_batches / dropped_observations | Utoljára jelentett érték; legnagyobb megfigyelt lapérték; problémát jelentő csomagok üteme |
| window_start_ms / window_end_ms | Ablakhossz és a fogadáskor megfigyelt, óraeltérést is tartalmazó ablakvég-kor; nyers időpontok helyi metrikákban is elérhetők |
| batch_id | Duplikált küldések kiszűrése a meglévő, korlátos 10 perces deduplikációs tárolóval; nincs UUID-metrikacímke |
| schema_version / interval_ms / timing | Csomagszerződés ellenőrzése: továbbra is v1, 60000 ms, fetch_response_headers |
| mock_api / mock_jobs | Valódi és részben szimulált adat elkülönítése; a részletpanelek csak real módot mutatnak |

A fogadó saját duplikált/elutasított/korlátozott csomagszámlálói is külön grafikonra kerültek. Ezek nem kizárólag éles böngészőforgalmat tartalmaznak; diagnosztikai kézi küldés is növelheti őket.

## Pontos jelentés és korlátok

A böngésző nem küld tartós kliens- vagy lapazonosítót. Az egymás utáni csomagok különböző lapoktól érkezhetnek. Emiatt **a delivery halmozott értékeit tilos összeadni vagy egymásból kivonni globális hibaszámként**. A csomag készítéskor rögzített érték a mostani csomag küldési sikerét még nem tartalmazza. Újraküldéskor ugyanaz a pillanatkép érkezik újra.

- `reported_delivery`: az utolsó egyedi csomagban jelentett, adott lap indulása óta halmozott érték; fel- és lefelé is változhat lapváltáskor.
- `reported_delivery_max`: a fogadó indulása óta látott legnagyobb laponkénti érték. Nem globális összeg.
- `reports_with_delivery_issue_total`: pozitív diagnosztikai hibaszámlálót jelentő, elfogadott egyedi csomagok száma. Egy régi hiba sok új csomagban is jelezhető; ez nem új hibák darabszáma. Duplikált csomag nem növeli.
- `reported_inflight`: az utolsó jelentő lap pillanatképe, nem az összes böngésző egyidejű terhelése.
- `reported_window_end_age_seconds`: Oracle-fogadási idő mínusz kliens által közölt ablakvég. Nem tiszta hálózati késleltetés: háttérlap, újraküldés és óraeltérés is befolyásolja. Negatív értéket is megőrzünk.
- Maximumok és számlálók a fogadó indulásától élnek, nem tartósak. Új metrikákból nincs visszamenőleges történet. A Prometheus korábbi idősorai megmaradnak.
- Friss pillanatképek és sebességek csak 3 percnél frissebb **real** csomag és elérhető scrape esetén jelennek meg. A real frissességét nem tudja frissíteni egy mock csomag. Indulás óta mért maximumok/összegek csak elérhető scrape mellett jelennek meg.
- A HTTP-hibaarány nevezője a pozitív mért HTTP-válaszforgalom; hálózati hibák és megszakítások nem részei. Hiányzó hibaszámlálót csak pozitív HTTP-nevező mellett értelmezünk 0 hibának. Válaszforgalom nélkül nem mutatunk kitalált 0%-ot.
- Új számlálósor első mintájának eseményei még nem feltétlenül látszanak rate-ként. Az indulás óta mért útvonalösszegek ezt kis forgalomnál is láthatóvá teszik.

## Új metrikák

Minden kliensadat `mode=real|partial_mock` szerint különül el. Az új címkék fix listákból származnak; nincs teljes URL, IP, token, önéletrajzadat, fiók- vagy kliensazonosító.

| Metrika | Jelentés / címkék |
| --- | --- |
| frontend_telemetry_receiver_schema_version | 2 = bővített fogadó; nem a frontend csomagverziója |
| frontend_api_results_total | Eredmények: mode, route, method, outcome, status |
| frontend_api_fetch_headers_max_seconds | Legnagyobb jelentett idő indulás óta: mode, route, outcome |
| frontend_telemetry_mode_last_received_timestamp_seconds | Utolsó elfogadott egyedi csomag ideje, mode szerint |
| frontend_telemetry_reported_inflight | Utolsó csomag inflight értéke |
| frontend_telemetry_reported_window_start_timestamp_seconds | Utolsó csomag ablakkezdete |
| frontend_telemetry_reported_window_end_timestamp_seconds | Utolsó csomag ablakvége |
| frontend_telemetry_reported_window_seconds | Utolsó csomag ablakhossza |
| frontend_telemetry_reported_window_end_age_seconds | Utolsó csomag fogadáskor megfigyelt, előjeles ablakvég-kora |
| frontend_telemetry_reported_delivery | Utolsó lapjelentés halmozott diagnosztikai számlálói; kind szerint |
| frontend_telemetry_reported_delivery_max | Látott legnagyobb lapértékek; kind szerint |
| frontend_telemetry_reports_with_delivery_issue_total | Hibát jelző egyedi csomagok száma; kind szerint |
| frontend_telemetry_result_dimension_overflow_total | A részletes dimenziókorlát miatt összevont megfigyelések száma |

A részletes route/method/outcome/status kombinációk száma legfeljebb 4096, ezen felül legfeljebb 6 mode/outcome tartalék sor. A korlát felett a részletcímkék `route=other, method=OTHER, status=other` értékre váltanak. Az eredményösszegek megmaradnak, a részletes dimenziók részben elvesznek és ezt külön számláló jelzi. A régi pontos összesített HTTP-státusz-, útvonal/kimenetel- és hisztogrammetrikák változatlanok.

## Későbbi frissítés vagy helyreállítás az Oracle-on

A két dashboardhoz a `scripts/install-dashboard-final-audit.sh FULL_COMMIT_SHA` pinned telepítője használható. [Teljes végső audit és telepítés](DASHBOARD_FINAL_AUDIT.md).

Ez a korábban kért v2 fogadófrissítést csak akkor pótolja a régi, rögzített telepítővel, ha még nincs fenn. Ekkor a fogadó egyszer újraindul és memóriában élő számlálói újrakezdődnek. Ha a v2 már fut, nincs fogadó-újraindítás. Frontenddeploy vagy Vercel-változtatás nem szükséges.

A telepítő mentést készít és olvasási lekérdezésekkel ellenőriz. Nem generál éles üzleti forgalmat. Az új metrikákhoz az első valódi böngészőcsomag szükséges; a Prometheus korábbi idősorai megmaradnak. Nyisd meg az éles oldalt, végezz szokásos műveleteket és tartsd aktívan 2–3 percig, majd a Grafanában nyisd le a **06 · Frontend részletek** sort. Az üres életjel nem API-kérés, a hiányzó adat nem nulla forgalom.
