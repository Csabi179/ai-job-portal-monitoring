# Forgalmi összehasonlítás – aktuális állapot

> **Aktuális telepítési állapot — 2026-11-19:** Az üzemeltető minden átadott módosítást már alkalmazott az Oracle-on. A monitoringág bekerült a `main` ágba (`10f43d1`); emiatt nincs újratelepítési feladat. [Aktuális állapot](DEPLOYMENT_STATUS.md). A korábbi bevezetési bejegyzések történeti állapotok; a parancsok későbbi frissítéshez vagy helyreállításhoz maradnak meg.

Frissítve: 2026-11-19. **Az éles frontend → Oracle → Prometheus → Grafana adatút működése igazolt.**

## Elkészült és működik

- Éles www.matchwise.tech frontend: automatikus, 60 000 ms-ra konfigurált összesítés.
- Külön Python fogadó: 127.0.0.1:9121, systemd alatt.
- HTTPS-fogadás a meglévő Caddy /matchwise-telemetry/v1 útvonalán.
- Prometheus frontend_traffic gyűjtés: 60s/10s.
- 45 paneles Service Comparison dashboard, UID: matchwise-service-comparison.
- Közös frontend–backend forgalmi és latenciakontextus.
- Backend API-ráta, Render CPU, Supabase commit-sebesség és PostgREST-sor közös grafikonjai.
- Backend relatív és /api előtagos API-útvonalak kezelése, health kizárással.
- A meglévő backend/Supabase gyűjtés és riasztások megmaradtak; új összetett riasztás nincs.

## Élesítési és mérési bizonyíték

A frontend PR #11 külön felhasználói engedéllyel main-be került.
Merge: 86fc6ff74ce1819e77749be899de598bf54b6577.
A [main CI](https://github.com/ernoking/job-portal-frontend/actions/runs/44423094254)
és a Vercel commitstatus sikeres. A forrás tartalma megegyezik a tesztelt e48661e változattal.

A felhasználó jelezte a Production-változók beállítását és deployt.
Az éles oldal böngészőjében ismételt, buildelt JavaScriptből indított POST-ok,
mind 204 válasszal. Egy pontosan 60 másodperces csomagban:
- me GET: 1 HTTP 200, fejlécig mért idő 1015 ms;
- cv GET: 2 HTTP 200, időösszeg 1077 ms, maximum 583 ms;
- auth POST: 1 HTTP 200, fejlécig mért idő 562 ms.
Starts és results: összesen 4 esemény; mock_api=false, mock_jobs=false.
Nincs jelzett sikertelen kísérlet vagy eldobott csomag/megfigyelés.
A sent_batches=0 az első csomag küldés előtti pillanatképe, nem hibajelzés.

Az éles ellenőrzés utáni Grafana-kép: receiver UP, 9 elfogadott csomag,
utolsó csomag kora 1,11 perc. A frontend rátaidősorok jelen vannak,
az adott időablakban nullán. Pozitív éles frontendráta és frontend-latenciagörbe
ezen az utolsó képen nem látható. A backend- és DB-görbék láthatók;
a PostgREST queue mintái nullák, a Render CPU alacsony.

Az első pozitív counter-minta az idősor kiindulóértéke, abból a rate még nem
tud megelőző növekményt számolni. További, API-esemény nélküli életjelek
friss fogadást és nulla rátát eredményezhetnek; a frontend latency-panel
pozitív HTTP-megfigyelési rátát igényel. A kép ezzel összhangban van,
de ebből nem állítunk minden kliensre garantált, veszteségmentes lefedettséget.
Az SSH-teszt alatt pozitív frontend forgalmi/latenciagörbék külön is igazoltak.

## Tesztek

10 frontendteszt, 6 fogadóteszt, 3 konfigurációmegőrzési teszt;
Oracle/GitHub lint és production build sikeres.
15 dashboard-lekérdezés Oracle-preflightja sikeres.
A kézi üres fogadópróba után az SSH/Vite teszt valódi API-eseményeket és
pozitív frontend/backend grafikonokat igazolt; az éles mérés külön ellenőrizve.

## Ideiglenes teszt lezárva

Health ok; www Origin OPTIONS 204; localhost:5173 Origin OPTIONS 403.
Az Oracle 5173-as portján nincs listener. A Vite és a localhost-engedély nem szükséges
az éles működéshez. A receiver restart nullázza a memóriabeli számlálókat
és deduplikációt, a korábbi Prometheus-minták megmaradnak.

## Értelmezési korlátok

A frontend nem Vercel access log: csak a mérőkódon átmenő böngészős API-hívások látszanak.
A háttérbe tett vagy bezárt lap, blokkolás és hálózati hiba adatvesztést/késést okozhat.
Hiányzó adat nem nulla forgalom. A beérkezés és az API-esemény időpontja eltérhet.
A böngészős idő válaszfejlécig tart; a P95 kosarakból becsült.
A PostgREST-sor nem a teljes adatbázis vagy PostgreSQL lock-várakozás.
A DB-tranzakciók belső szolgáltatásokat és más klienseket is tartalmaznak.
Külön tengelyeken lévő görbék egyezése/eltérése nem ok-okozati bizonyíték.
Nincs új automatikus rendellenesség-riasztás vagy DDoS-/terheléses igazolás.
Az új dashboard Viewer-hozzáférése nincs külön igazolva.

## Verziózás és üzemeltetés

- Frontend: ernoking/job-portal-frontend; a tesztelt fejlesztési ág main-be összevonva, PR #11.
- Monitoring: Csabi179/ai-job-portal-monitoring; a feat/service-comparison ág 2026-11-19-én bekerült a main ágba, a 10f43d1c6b770a0ac5ca91a297d83d0b3dad3062 commitig.
- Kód és dokumentáció Gitben verziózott.
- Az Oracle checkout korábbi Git-leltára szerint main,
  7ac0229c8384e55a23551b86f6d6db6002608b4b, helyi módosításokkal.
  A telepített fájlok az átadott segédekkel frissültek; a checkout régi HEAD-je nem a futó konfiguráció verziójának bizonyítéka. Az üzemeltető minden változás azonnali alkalmazását visszaigazolta; a merge miatt nincs újratelepítési feladat.
  Későbbi frissítés előtt git status; helyi fájlokat nem dobunk el.
- A külön telepített Python és systemd példányokat a Git-frissítés önmagában nem frissíti.

Nincs további kötelező tesztparancs. Normál használat mellett gyűlhet az éles minta;
új közös riasztási küszöbök előtt ennek lefedettségét és szokásos viselkedését kell értékelni.

Részletek: [élesítés](FRONTEND_PRODUCTION_ACTIVATION.md),
[fogadó és bizonyítékok](FRONTEND_TRAFFIC_RECEIVER.md),
[dashboard](SERVICE_COMPARISON_DASHBOARD.md), [SSH-teszt](FRONTEND_SSH_TEST.md).
