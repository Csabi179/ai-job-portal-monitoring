# Az éles frontendmérés bekapcsolása

Állapot (2026-11-19): a frontend main összevonása külön felhasználói engedélyt kapott; a végrehajtás és production build még nincs igazolva. A monitoringág továbbra is külön marad.
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
