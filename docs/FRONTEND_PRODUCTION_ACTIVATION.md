# Az éles frontendmérés bekapcsolása

Állapot (2026-11-19): a frontend main merge, CI/deploy, az éles automatikus 204-es küldés, a tényleges API-csomag és a Grafana fogadási adatai igazoltak. Az aktuális éles ablakban a frontendráta nulla, pozitív frontend-latenciagörbe nem látszik; részletek az aktuális állapotban. A monitoringág külön marad.
A fogadó, HTTPS, Prometheus és a 45 paneles dashboard működik az Oracle-on.
Az SSH/Vite teszt lezárva; a localhost CORS-engedély visszavonva.

## Szükséges forrás

Frontend: ernoking/job-portal-frontend, feat/frontend-api-traffic.
Utolsó tesztelt/pusholt commit: e48661ef58be096bf1ff970368432ebd16e5e9ca.
A GitHub CI sikeres. A mérőkód ebben a forrásban van, a normál
trafficConfig.js alapértéke enabled=false és üres endpoint.
A browserTraffic.js a VITE_FRONTEND_TELEMETRY_* buildváltozókat előnyben részesíti.

Az éles kiadásnak ezt a mérőkódot tartalmazó forrást kell használnia.
Egy régi, mérőkód nélküli production build újratelepítése csak változókkal nem elég.
A projekt kezelője ellenőrizze az aktuális éles forrással szembeni diffet,
hogy közben készült módosítás ne maradjon ki a kiadásból.

## Javasolt bekapcsolás: csak Production környezeti változók

A Vercel-projekt kezelője a projekt Environment Variables felületén,
kizárólag Production környezetre állítsa be:

| Név | Érték |
| --- | --- |
| VITE_FRONTEND_TELEMETRY_ENABLED | true |
| VITE_FRONTEND_TELEMETRY_URL | https://grafana-r0cecq.duckdns.org/matchwise-telemetry/v1 |

Ezek nyilvános frontendkonfigurációk, nem titkos kulcsok.
A fejlesztési és preview környezetet nem szükséges bekapcsolni.
Az éles VITE_USE_MOCK_API és VITE_USE_MOCK_JOBS értékét is ellenőrizni kell:
a mock, hálózat nélküli műveletekből nem lesz valódi API-forgalmi mérés.

## Új Production build és deploy

A változók csak új build/deploy esetén épülnek a frontendbe.
A Vercel kezeli a preview-ból productionbe emelést is: az illetékes kezelő
a megfelelő commithoz tartozó deploymentből készíthet Production kiadást,
amely production változókkal újraépül. Ez önmagában nem Git main merge.
A konkrét deploymentet, a projektet és a www.matchwise.tech production domaint
a kezelőnek azonosítania kell; a production branch jelenlegi beállítása nincs nálunk igazolva.

A felhasználó 2026-11-19-én kifejezetten engedélyezte kizárólag a frontend
feat/frontend-api-traffic ág main-be összevonását. A monitoringág nem vonható össze.
A frontend PR/merge az Oracle-on működő GitHub CLI-vel készíthető elő;
a kapcsolt GitHub-eszköz PR-létrehozása 403 Resource not accessible by integration hibát adott.
A Vercel Production-változókat továbbra is a projekt kezelője állítja be.

## Ellenőrzés és visszaállítás

Új build Ready állapota után a www.matchwise.tech oldalon:
- normál API-művelet, legalább egy perc várakozás;
- Network: a /matchwise-telemetry/v1 POST válasza 204;
- a csomagban a konfigurált periódus 60 000 ms és szükség esetén nem üres starts/results;
- Prometheus/Grafana: frissülő csomagkor és csomagszámláló, később forgalmi görbék;
- szokásos bejelentkezés és alkalmazásműködés ellenőrzése.

A www Origin már engedélyezett az Oracle-on; localhostot ehhez nem nyitunk vissza.
Az összesítést a látogatók böngészője küldi, nem kell Vite-szervert vagy SSH-alagutat indítani.
A hiányzó frontendadat továbbra sem nulla forgalom, az inaktív oldalak nem küldenek életjelet.

Kikapcsolás: Production VITE_FRONTEND_TELEMETRY_ENABLED=false, majd új production build/deploy.
A változó átírása önmagában a már letöltött JavaScriptet nem módosítja.
Problémás kiadásnál a projekt kezelője a korábbi működő deploymentet is visszaállíthatja.
A dashboard és a backend/Supabase megfigyelés ettől megmaradhat.

Források:
[Vercel environment variables](https://vercel.com/docs/environment-variables/managing-environment-variables),
[Preview -> Production](https://vercel.com/docs/deployments/promote-preview-to-production).

## Minden egyéb előkészítése az env-beállítás előtt – 2026-11-19

Ellenőrzött frontend main: 50d1058a035fe8cfb14ce291c923ab77c31f20cb.
Ellenőrzött feature HEAD: e48661ef58be096bf1ff970368432ebd16e5e9ca.
A feature 2 committal előrébb van, 0 committal lemaradva; 12 érintett fájl,
kizárólag mérőkód, tesztek, CI-kiegészítés, tesztkonfiguráció és dokumentáció.
Az összehasonlításkor nem volt nyitott PR. A feature CI már sikeres volt.

A scripts/merge-tested-frontend.sh --merge az Oracle-on futtatandó, nem helyben:
1. receiver health, Prometheus up/receiver_up és production-Origin HTTPS/CORS ellenőrzése;
2. a konkrét head/base SHA ellenőrzése;
3. PR létrehozása vagy a már létező megfelelő PR használata, pontos leírással;
4. a PR checkek kivárása;
5. normál merge, --match-head-commit védelemmel;
6. a main tartalmazza-e a tesztelt forrást: ancestry ellenőrzés.

Nincs admin/force/auto-merge vagy ágak törlése. Nem váltja át a helyi monitoring
checkoutot, és nem merge-eli a monitoringágat. A script Bash-szintaxisa ellenőrzött;
tényleges PR/merge végrehajtás még nincs igazolva. A default frontendkapcsoló
marad false, a Production-változók felülírják új buildkor.

A forrás main-re kerülése automatikus Vercel-deployt indíthat. A merge/deploy után
külön ellenőrizzük, hogy a Production környezetben a megfelelő forrás fut-e;
a projekt production branch beállítása még nincs közvetlenül igazolva.
Amikor a kezelő beállította a két Production-változót, új Production build kell.
Ezt a Vercel Redeploy-val vagy a megerősített production Git-ág új commitjával
lehet indítani. Az env mentésétől a korábbi statikus JS nem frissül magától.
Ha a kezelő csak a változókat állítja be, a buildindítás a következő közös lépés;
Nem állítjuk, hogy változómentés önmagában azonnal aktiválja a mérést.

## Új main commit ellenőrizve, env/deploy felhasználó által visszajelezve – 2026-11-19

A felhasználó jelzi, hogy a két változó beállítása és deploy megtörtént.
Az Oracle-segéd receiver/Prometheus és production-Origin HTTPS/CORS readiness
ellenőrzése sikeres volt, majd a megváltozott main miatt megállt; PR/merge nem történt.

A kapcsolt GitHub-eszközzel ellenőrzött frontend main most
475cc291ae2187048ab588a51c1b4cc69b732e36; feature változatlanul
e48661ef58be096bf1ff970368432ebd16e5e9ca. Nyitott PR nincs.
A régi 50d1058a -> 475cc291 összehasonlítás 1 új commitot és 0 változott fájlt
mutat; a forrásfa SHA-ja mindkettőn b9653bbfbb35cba13c3a98b7a773f58f01fbd340.
A feature a main-hez képest 2 committal előrébb és 1-gyel lemaradva van;
a mérőkód fájljai még nem szerepelnek main-ben.
Az új main forrástartalma felülvizsgálva, ezért a segéd expected_base értéke
475cc291-re frissítve. A head/base és CI védelem megmaradt; monitoring merge nincs.

Nem állítjuk, hogy a Vercelben ténylegesen melyik forrás/környezet épült:
nincs közvetlen Vercel-hozzáférés. A konfiguráció/deploy felhasználói visszajelzés,
az éles böngészős telemetria még ellenőrizendő.
Az új merge után a CI/deployment és a www.matchwise.tech automatikus
204-es POST-jai, a csomagok tartalma és a Grafana frissessége lesz az ellenőrzés.

## PR #11 elkészült, régi gh checks kompatibilitás javítva – 2026-11-19

A felhasználó a felülvizsgált main-alappal futtatta a segédet. A readiness sikeres,
[PR #11](https://github.com/ernoking/job-portal-frontend/pull/11) létrejött.
A gh pr checks --json kapcsolót az Oracle CLI-verziója nem támogatja;
a segéd megállt a merge előtt. A többször kiírt hiba nem több merge-kísérlet:
a check-regisztrációs várakozó ciklus futott. A 11 helyi nem commitolt módosítás
figyelmeztetése a monitoring checkoutból ered, nem lett eldobva vagy stage-elve.

A kapcsolt GitHub-eszközzel ellenőrizve: PR open, merged=false, mergeable=true,
mergeable_state=clean, head=e48661ef58be096bf1ff970368432ebd16e5e9ca,
base=475cc291ae2187048ab588a51c1b4cc69b732e36.
Az új pull_request CI run 44422242453 és a korábbi push CI sikeres;
a check-runs listában a check és a Vercel Preview Comments success.
A kapcsolt eszköz közvetlen merge-hívását is 403-mal utasította el a GitHub;
ezért a végrehajtás továbbra is az Oracle felhasználói gh-fiókjával történik.

A segéd most check-runs REST API-val számolja az ellenőrzéseket,
a rendelkezésre álló gh pr checks --watch --fail-fast paranccsal vár,
és REST PUT /pulls/11/merge sha feltétellel védi a headet.
A régi gh pr checks --json és az esetleg verziófüggő --match-head-commit
használata megszűnt. A normál GitHub merge-védelem megmarad, nincs admin/force.
A PR-műveletek ideiglenes könyvtárból futnak, nem a módosított monitoring checkoutból.
A javított Bash-szintaxis ellenőrzése sikeres; tényleges merge még nincs visszaigazolva.

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

## Éles Grafana ellenőrzés képpel visszaigazolva – 2026-11-19

A felhasználó képei: receiver UP, 9 elfogadott csomag, utolsó fogadás kora 1,11 perc.
A frontend indítás-/HTTP-válasz rátaidősorok nullán látszanak; pozitív éles
frontendráta vagy frontend-latenciagörbe ezen az utolsó képen nem látható.
A backend API-ráta és P95, a Supabase commit-sebesség, a Render CPU és
PostgREST waiting grafikonjai megjelennek. Az utóbbi mintavételezett értékei 0.

A friss életjel nem jelent új API-műveletet. Az első counter-minta kezdőérték;
a rate és a pozitív elemszámra kapuzott latency újabb megfigyelések nélkül
maradhat nulla/üres. Ez összhangban van a képpel, nem bizonyított rendellenesség.
Az éles, valódi API-csomag korábban 4 HTTP 200 eseményt és 60s időablakot
igazolt; a fogadási adatok és a frontend idősorok együtt az éles adatút működését
alátámasztják. Nem állítunk az utolsó képen nem látható pozitív frontendlatenciát.
További mesterséges teszt vagy módosítás nem szükséges; normál használati adatot gyűjtünk.
Aktuális összefoglaló: [SERVICE_COMPARISON_STATUS.md](SERVICE_COMPARISON_STATUS.md).
