# Az éles frontendmérés bekapcsolása

Állapot: végrehajtható átadási leírás; élesítés nem történt.
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

Nem futtatunk automatikus main merge-t vagy production promote parancsot.
A felhasználónak nincs Vercel-hozzáférése, ezért ez a lépés projektkezelői
közreműködést igényel. A monitoringrepó fejlesztési ágát ehhez nem kell mainbe olvasztani.

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
