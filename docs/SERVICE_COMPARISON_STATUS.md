# Forgalmi összehasonlítás – aktuális állapot

Frissítve: 2026-11-19. Az első közös grafikonos változat tesztje és az ideiglenes teszt lezárása sikeres.

## Mi működik tartósan az Oracle-on?

- Python fogadó: 127.0.0.1:9121, külön systemd-szolgáltatás.
- HTTPS-fogadás a meglévő Caddy /matchwise-telemetry/v1 útvonalán.
- Prometheus frontend_traffic scrape: 60s/10s.
- 45 paneles Service Comparison dashboard, változatlan UID-val: matchwise-service-comparison.
- Közös frontend–backend forgalmi és latenciagrafikonok, valamint backend–Supabase aktivitási kontextus.
- A backend relatív és /api előtagos API-útvonalait is kezeli az összehasonlító szűrés; health kérések kizárva.
- A backend és Supabase korábbi adatgyűjtése megmaradt. Új riasztást nem adtunk hozzá.

## Mit igazolt a teszt?

Az Oracle-on futó frontend saját SSH-alagúton nyílt meg a felhasználó böngészőjében.
A külön tesztkonfiguráció Renderre továbbította az API-hívásokat.
A mérőkód 60 000 ms-os periódussal indult; ismételt 204-es fogadás látszott.
Egy pontosan 60 másodperces csomagban valódi auth POST és cv GET HTTP 200
események, számlálók és fejlécig mért időadatok jelentek meg.
A frontend adatainak böngésző -> Oracle -> Prometheus -> Grafana útja igazolt.
A backend API-ráta és P95, a Supabase committed transactions/s, a Render CPU
és a PostgREST pool waiting grafikonjai képpel igazoltak.

Ellenőrzések: 10 frontendteszt, 6 fogadóteszt, 3 konfigurációmegőrzési teszt,
lint és production build sikeres; 15 dashboard-lekérdezés Oracle-preflightja sikeres.
A frontend utolsó pusholt commitja e48661ef58be096bf1ff970368432ebd16e5e9ca,
[CI](https://github.com/ernoking/job-portal-frontend/actions/runs/44413623454) sikeres.
A Vercel branch-deploy státusza sikeres, de a védett preview-hoz a felhasználónak nincs hozzáférése.

## A teszt lezárása igazolt

A felhasználó visszaadta a cleanup kimenetét:
- receiver /health: ok;
- www.matchwise.tech Origin OPTIONS: 204;
- localhost:5173 Origin OPTIONS: 403;
- az Oracle 5173-as portjának ss-listája üres (csak fejléc).

Az ideiglenes localhost-engedély visszavonva, a Vite-porton nincs szerver.
A receiver restart nullázza a memóriabeli számlálókat és deduplikációt;
a korábbi Prometheus-minták megmaradnak.
A frontendgörbékben a teszt után elmaradó friss adat elvárt: a tesztfrontend leállt.
A fogadó szolgáltatás és a monitoring ettől tovább működik.

## Éles működés és még nem igazolt részek

**A www.matchwise.tech éles oldalon az automatikus küldés és a tényleges API-kérések összesített mérése igazolt.**
A forrásbeli trafficConfig.js alapértéke enabled=false és üres endpoint;
a teszt a Vite-folyamat környezeti változóival működött, amelyeket nem írtunk .env fájlba.
A projekt kezelője a felhasználó visszajelzése alapján beállította a Production-változókat és deployolt;
a main merge utáni éles oldalon a küldés már látszik. A csomagok üzleti API-tartalmát
és az éles forgalom Grafana-megjelenését még ellenőrizni kell. A frontend main merge 2026-11-19-én külön engedélyt kapott és megtörtént; a monitoringág külön maradt.

Nincs automatikus összetett eltérésriasztás, DDoS-/terheléses igazolás vagy általános
rendellenesség-felismerési bizonyíték. Az új panelek Viewer-hozzáférése nincs külön igazolva.
A PostgREST queue mintavételezett kapcsolatkészlet-várakozás, nem teljes adatbázis-/lock-várakozás.
A DB-tranzakciók belső szolgáltatásokat és más klienseket is tartalmaznak.
A külön tengelyeken lévő görbék egyezése vagy eltérése önmagában nem ok-okozati bizonyíték.
A böngészős idők válaszfejlécig mérnek; P95 kosarakból becsült.
Hiányzó frontendadat nem nulla forgalom; a gyűjtési késés és az eltérő lefedettség számít.

## Verziózás és üzemeltetési korlát

- Monitoring: Csabi179/ai-job-portal-monitoring, feat/service-comparison.
- Frontend: ernoking/job-portal-frontend, feat/frontend-api-traffic.
- Kód és dokumentáció mindkét fejlesztési ágban verziózott.
- Oracle monitoring checkout: a felhasználó utolsó igazolása szerint main,
  7ac0229c8384e55a23551b86f6d6db6002608b4b, helyi módosításokkal.
  A telepítés fájlonkénti másolással történt: nincs pull/ágváltás.
  Későbbi frissítés előtt git status; helyi fájlokat nem dobunk el.
- A külön telepített Python-scriptek és systemd-fájlok nem frissülnek automatikusan Git-frissítéstől.

Részletes bizonyítékok és eljárások:
[frontend/fogadó](FRONTEND_TRAFFIC_RECEIVER.md),
[dashboard](SERVICE_COMPARISON_DASHBOARD.md),
[SSH-teszt](FRONTEND_SSH_TEST.md),
[Supabase](SUPABASE_METRICS.md).

## Éles forrás előkészítése – 2026-11-19

A felhasználó most külön engedélyezte a frontend feat/frontend-api-traffic -> main
összevonást. A monitoring feat/service-comparison ág továbbra sem vonható össze.
A kapcsolt GitHub-eszköz PR-létrehozására 403 érkezett, ezért az Oracle GitHub CLI-hez
készült rögzített SHA-kat, readiness-t és CI-t ellenőrző merge-segéd.
A script helyi Bash-szintaxisellenőrzése sikeres; a tényleges Oracle-futás,
PR-létrehozás és merge még nincs igazolva. Részletek:
[Production activation](FRONTEND_PRODUCTION_ACTIVATION.md).
A két Production-változó mellett új Production build szükséges;
a változók mentése önmagában nem írja át a már kiadott frontend JavaScriptjét.

## Frontend merge és az utána indult CI/deploy sikeres – 2026-11-19

A felhasználó REST merge-kimenete merged=true, SHA:
86fc6ff74ce1819e77749be899de598bf54b6577.
A kapcsolt GitHub-eszköz ezt [PR #11](https://github.com/ernoking/job-portal-frontend/pull/11)
merged állapotával és a main aktuális HEAD-jével külön igazolta.
A tesztelt e48661e forrás a merge elődje; e48661e -> 86fc6ff összehasonlításban
0 változott fájl szerepel. A frontendkód tartalma megegyezik a teszteltével.
[Main CI 44423094254](https://github.com/ernoking/job-portal-frontend/actions/runs/44423094254): completed/success.
Az új merge-commit Vercel státusza success, Deployment has completed.
[Deployment státusz céloldala](https://vercel.com/ai-job-portal1/matchwise/6Q6jnND9uuawRBNkGnedCZujnu89).

A két környezeti változó beállítását és a deployt a felhasználó korábban jelezte.
A Vercel-projekt konkrét beállításait közvetlenül nem olvastuk ki.
Következő ellenőrzés: az éles https://www.matchwise.tech oldalt újratöltve,
valódi automatikus /matchwise-telemetry/v1 POST 204, nem üres normál API-adatok,
majd Prometheus/Grafana frissülés. Ez még nincs visszaigazolva.
A merge és a Vercel success önmagában nem éles böngészős adatküldési bizonyíték.
A monitoring feat/service-comparison ága továbbra sem lett main-be olvasztva.

## Éles oldalon ismétlődő 204-es küldés igazolva – 2026-11-19

A felhasználó az éles www.matchwise.tech oldal újratöltése és Network-vizsgálata
után képet adott vissza. Öt POST látszik a grafana-r0cecq.duckdns.org v1
fogadóútvonalára, mind 204. Az initiator a buildelt index JavaScript fetch-hívása.
A képen az első csomag átvitele 1,84 kB, a későbbieké 1,26 kB.
A nagyobb méretből önmagában nem következtetünk nem üres API-adatokra.

Ez az éles oldalon ismétlődő automatikus fogadást igazolja a felhasználó
aktuális böngészőjében. Nem bizonyít minden látogatóra teljes lefedettséget,
pontos időközöket vagy a csomagtörzsben szereplő mock kapcsolók értékét.
Következő, még nem igazolt lépés: az első nagyobb csomag starts/results
és mock_api/mock_jobs értékeinek ellenőrzése, majd Grafana frissesség és görbék.
Nincs szükség localhost/Vite újraindításra; a localhost Origin továbbra is tiltott.

## Éles, nem üres API-csomag igazolva – 2026-11-19

A felhasználó az éles oldal első, f8c446b4-a9d6-40a4-a5e7-36d0f431f97b csomagját
adta vissza. Időablak 1795045538927–1795045598927 ms: pontosan 60 000 ms.
interval_ms=60000; mock_api=false; mock_jobs=false; inflight=0.
Starts és results egyaránt 4 esemény, 3 dimenziósor:
- me / GET: 1 HTTP 200, fejlécig mért idő 1015 ms;
- cv / GET: 2 HTTP 200, időösszeg 1077 ms, maximum 583 ms (átlag 538,5 ms);
- auth / POST: 1 HTTP 200, fejlécig mért idő 562 ms.
A Network-kép szerint a csomag POST-ja 204 volt.
Delivery failed_attempts/dropped_batches/dropped_observations mind 0.
A sent_batches=0 az első csomag küldés előtti pillanatképe: a kód sikeres
204 után növeli ezt, ezért nem sikertelen vagy hiányzó küldést jelent.

Ez az éles buildben a tényleges API-indítások és HTTP-válaszok mérését,
a csoportosítást és fejlécig tartó időadatok gyűjtését igazolja a megfigyelt
böngészőben. Nem állítunk minden kliensre garantált, veszteségmentes lefedettséget.
Következő utolsó próba: egyszeri normál éles oldalfrissítés, két perc gyűjtési idő,
majd a Grafana frontend/backend paneljei és a fogadás frissességének ellenőrzése.
A kezdeti counter-idősorok és az 5 perces ráták miatt további normál kérések/minták
szükségesek lehetnek a forgalmi görbékhez. Ez az ellenőrzés még nincs visszaigazolva.
Nincs localhost-engedély vagy SSH/Vite teszt újraindítva.
