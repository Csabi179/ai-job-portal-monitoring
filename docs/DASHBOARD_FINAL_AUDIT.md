# Két dashboard végső felülvizsgálata · 2026-11-19

**Kész forrásváltozat:** Unified v10; Szolgáltatások összehasonlítása v8. Az Oracle-telepítés és az éles lekérdezésellenőrzés a pinned telepítővel történik. Az élő Grafana-URL-ek bejelentkezésre irányítanak, ezért nincs közvetlenül ellenőrzött böngészős képernyőkép. A helyi előnézetek csak elrendezési rajzok, kitalált mérési értékek nélkül.

## Szolgáltatások összehasonlítása

- A felhasználó kérésére törölve a korábbi **05 · Backend-naplók** és **07 · Adatforrások és mérési útmutató** sor, a bennük lévő panelek teljes tartalmával.
- A haladó, két tengelyes nézet most **05**, a frontend részletei **06**. A frontend szakasz 25 tartalmi panelje és 26 lekérdezése megmaradt.
- A fontos mérési korlátok a vonatkozó panelek leírásaiban, illetve a frontend saját rövid értelmező paneljén maradtak. Nincs külön általános adatforrás-szakasz.
- A két HTTP-elérhetőségi kártya csak sikeres aktuális exporter scrape mellett mutat legutóbbi, három percnél frissebb próbát. Exporterhiba nem minősül az alkalmazás bizonyított kiesésének: nincs adat jelenik meg, a tényleges sikertelen próba továbbra is piros.
- A rövid fejléc több helyet kapott, hogy ne kelljen feleslegesen görgetni a szövegét. Az eredeti forgalmi/latencia-, DB-, CPU- és memórianézetek megmaradtak.
- Összesen **73 JSON-elem**, **82 lekérdezési cél**, 1 perces frissítés és 1 órás alapablak.

## Unified Monitoring

- A fő nézet magyar feliratokat és az összehasonlítóval egyező szolgáltatásszíneket kapott. Felül elérhetőség és frissesség, utána Oracle-kapacitás és HTTP 5xx, forgalom/feldolgozási idő, közös HTTP-próba-összevetés, végül a DB fő kapacitásjelzői látszanak.
- A frontend és backend HTTP-próbák egy új, **közös másodperces skálájú** grafikonon is összevethetők. Az eredeti külön grafikonok megmaradtak a lenyitható részletekben.
- Az Oracle, adatbázis, HTTP-próbák, alkalmazásstátuszok/végpontok, hitelesítés és naplógyűjtés részletei alapból csukva vannak. A Unified meglévő naplódiagnosztikája megmaradt; a felhasználó által kért két törlés az összehasonlító dashboard megnevezett soraira vonatkozott.
- A fő nézet hosszú link/szűrőleírása a diagnosztikába került. Alkalmazás- és kölcsönös dashboardlinkek felül is elérhetők. A két dashboard UID-ja és a meglévő panelazonosítók megmaradtak; a meglévő naplóhivatkozások célpontjai is megvannak.
- A táblázat oszlopnevei magyarok; a rendezés, transzformációk, útvonalhivatkozások és mértékegységek ehhez igazodnak.
- A frontend/backend próbaablak egységesen 3 perc. Az alkalmazáspróba sikerének megjelenítéséhez sikeres exporter scrape is szükséges; az exporter saját állapota külön megmaradt.
- Oracle-erőforrás és Supabase-gépmetrika csak sikeres hozzá tartozó scrape mellett látszik. PostgreSQL-működéshez kötött DB-panelekhez pg_up=1 is szükséges; a host CPU/memória PostgreSQL-hiba mellett továbbra is megfigyelhető, ha a metrikagyűjtés működik.
- A numerikus HTTP-hibakódszűrés után a hibanapló külön kizárja a feldolgozási hibás sorokat.
- Az alapértelmezett időablak 1 óra, a frissítés 1 perc. A forgalmi szűrő alapértéke **Health nélkül**; a **Minden kérés** opció és a külön health-kérésszámláló megmaradt. A hitelesítési számlálók továbbra is függetlenek az alkalmazás-/naplószűrőktől.
- Összesen **96 JSON-elem**, **98 lekérdezési cél**. Minden eredeti Unified-panel megmaradt; két csoportosító sor és egy közös HTTP-próbagrafikon került hozzá.

## Ellenőrzés

`docs/dashboard-query-audit.json` az **51 szándékos kifejezésmódosítást** rögzíti az eredeti és új kifejezéssel, indoklással. Az összes többi megmaradt cél lekérdezése, adatforrása és instant/range módja változatlan. A szándékosan törölt összehasonlító panelek azonosítói külön listában vannak.

Helyben sikeres:

- Mindkét JSON-modell: egyedi azonosítók, egymást nem fedő elrendezés, megőrzött célok és adatforrások, hiányzó adatok közötti összekötés kikapcsolva, tábla/transzformáció-feliratok és a kért törlési kör ellenőrizve.
- **6 Python-teszt**: nem jóváhagyott modellváltozás megállítása; törlés korlátozása; változó- és regexkezelés; valódi range API-útvonalak kiválasztása és nyers naplók kiírásának elkerülése; nem véges metrikaeredmény felismerése; provisionált modell eltérésének felismerése. A hálózati válaszokat ezek a helyi tesztek helyettesítik, tehát nem bizonyítanak éles adatot.
- Python-szintaxis, telepítő Bash-szintaxisa és a fő nézetek helyi elrendezési előnézetei.

Az Oracle-telepítő végzi az éles ellenőrzést:

1. Ismert kiindulási modellekhez hasonlítja a két élő JSON-fájlt; ismeretlen módosításnál leáll. Kiinduló commit `f42a936b6c4446b8cbb14d60a98d0aef837cdb83`; az összehasonlítónál az előző v6 is elfogadott.
2. Lefuttatja a 6 Python-tesztet és **12 offline promtool-szituációt** a konténer meglévő promtool parancsával. Ezek nem telepítenek szabályokat és nem generálnak alkalmazásforgalmat. Esetek: exporterhiba és korábbi sikeres próba; valódi sikertelen próba; hiányzó/régi próba; sikertelen Supabase-scrape; PostgreSQL-hiba mellett elérhető host CPU; ismeretlen és mért nulla PostgREST-sor megkülönböztetése.
3. Mentést készít `/home/ubuntu/monitoring-backups/dashboard-final-audit.*` alá.
4. Ha a korábban kért frontend-fogadóbővítés még nincs telepítve, a korábbi pinned, tesztelt telepítővel pótolja. Ez csak ebben az esetben indítja újra a fogadót és kezdi újra a memóriában élő számlálóit. Ha a v2 fogadó már fut, ahhoz nem nyúl.
5. Végrehajtja **mind a 180 cél** olvasási ellenőrzését, az azonos kifejezések újrahasznosításával. Az idősoroknál az utolsó 1 órát, 60 másodperces lépéssel olvassa; a statoknál a jelenlegi pillanatot, a nyers naplóknál legfeljebb 5 sort az utolsó 5 percből. Naplótartalmat nem ír ki. A jelentés a mentés melletti `datasource-audit.txt` fájlba is bekerül.
6. Csak sikeres ellenőrzés után cseréli a két dashboardfájlt. Hiba esetén visszaállítja a két korábbi modellt.
7. Legfeljebb 75 másodpercig megpróbálja a helyi Grafana SQLite-tárolóból **csak olvasva** visszaellenőrizni a két UID paneljeit, címeit, elrendezését, sorállapotát és lekérdezéseit/adatforrásait. Nem olvas fiók- vagy hitelesítési táblákat, és nem módosít adatbázist. Más tároló esetén SKIP és kifejezett böngészős ellenőrzési kérés jelenik meg; nem állítja ellenőrzöttnek a betöltést. A tárolt modell egyezése sem képi renderelési bizonyíték.

Az üres eredmény önmagában nem hiba és nem bizonyít nulla forgalmat. A kiválasztott alapértékeket ellenőrizzük; az összes lehetséges szabad szöveges szűrőkombináció nem fut le. Nem változik riasztás, Caddy, Prometheus-konfiguráció, Vercel-beállítás vagy ingyenes csomag. Nincs monitoring main-merge vagy munkapéldány-reset.

Telepítés után Ctrl+F5 mindkét dashboardon. A bejelentkezett böngészőben ellenőrizendő még: kártyák olvashatósága saját képernyőméreten, jelmagyarázatok, tábla és napló-adathivatkozások tényleges működése. A helyi elrendezési előnézet nem helyettesíti ezt.

Grafana: [fájlalapú provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/) és [dashboardhivatkozások](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/manage-dashboard-links/).
