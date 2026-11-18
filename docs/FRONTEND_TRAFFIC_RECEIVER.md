# Frontendforgalom – fogadó és biztonságos bevezetés

Állapot: elkészült, helyben tesztelt fejlesztési kód; nincs Oracle-ra telepítve.
Nincs új dashboard vagy riasztás telepítve. Main összevonás nincs.

## Ellenőrzött környezet, 2026-11-18

A felhasználó kimenete alapján az Oracle checkout main ágon van, HEAD:
7ac0229c8384e55a23551b86f6d6db6002608b4b.
Helyi módosítások vannak többek között a Prometheus-, Blackbox-, dashboard-
és alertkonfigurációban, továbbá nem követett monitoringfájlok is léteznek.
A service-comparison-test.json létezése nem bizonyít aktív TEST-szabályt;
ebben a lépésben nem töröljük és nem aktiváljuk.
Ezért nincs git switch, pull, reset vagy a teljes konfiguráció felülírása.

A sudo-val kiolvasott Caddyfile a grafana-r0cecq.duckdns.org host minden
kérését a 127.0.0.1:3000 címre továbbítja. A docker socket a felhasználó
számára sudo nélkül nem hozzáférhető; a további dockerparancsok sudo-val futnak.
A Caddyfile gazdagépen lévő tényleges forrásútvonala még ellenőrzendő.

A frontendnél a felhasználó szerint automatikus deploy van.
A frontend GitHub-kapcsolat olvas, de az ág létrehozását 403
Resource not accessible by integration hibával elutasította.
A frontendváltozás ezért a patches/frontend-api-traffic.patch fájlban is
verziózott, alkalmazható formában szerepel. Nem állítjuk frontendcommitnak
vagy éles deploymentnek ezt a monitoringrepóban tárolt patch-et.

## Elkészült fájlok

- scripts/frontend-traffic-receiver.py: Python standard library, nincs pip-függőség.
- scripts/test_frontend_traffic_receiver.py és scripts/frontend-traffic-v1.json:
  a tényleges frontendmodulból generált minta, szerződés- és helyi HTTP-próbák.
- systemd/matchwise-frontend-traffic.service: külön, korlátozott systemd-szolgáltatás.
- prometheus/frontend-traffic-scrape.yml: beillesztendő scrape_configs-részlet.
- caddy/Caddyfile.frontend-traffic.example: az ellenőrzött élő alaphoz készített példa.
- patches/frontend-api-traffic.patch: frontendkód, dokumentáció, tesztek és CI-kiegészítés.

## Fogadó

Kizárólag 127.0.0.1:9121 címen figyel; a nyilvános Caddy csak a
/matchwise-telemetry/v1 útvonalat továbbíthatja ide.
A /metrics és /health csak helyi elérésre készült.

POST /matchwise-telemetry/v1: text/plain törzsbe írt JSON, schema_version=1.
Engedélyezett Origin: https://www.matchwise.tech. A szolgáltatás
FRONTEND_TRAFFIC_ORIGINS változója vesszővel elválasztott, pontos eredeteket
enged, wildcard nincs. Preview origin csak külön, ellenőrzött beállítás után használható.
A www nélküli domain nem engedélyezett automatikusan.

Siker és már átvett ismételt csomag: 204. Hibás adatok: 400;
tiltott origin: 403; túl nagy törzs: 413; hibás tartalomtípus: 415;
globális terhelési korlát: 429. A CORS nem hitelesítés.

Korlátok: 60 000 bájt, 16 párhuzamos kiszolgáló szál, 5 másodperces socket timeout,
600 elfogadási kísérlet percenként minden kliensre együtt, legfeljebb
8192 batchazonosító 10 perces ismétlésvédelemmel. A böngésző legfeljebb három,
percenkénti küldési kísérlete ehhez igazodik. Ez nem DDoS-védelem vagy hitelesítés.
Szigorú, verziózott mezők és engedélyezett dimenziók; minden sor ellenőrzése
megelőzi a számlálók módosítását. Ez új mezőknél összehangolt verziófrissítést igényel.

A batch_id csak az ismétlésvédelem memóriájában marad, nem metrikacímke.
Számlálók és deduplikáció memóriában vannak; szolgáltatás-újraindításkor nullázódnak.
Az újraindítás körüli ismétlés újra számlálódhat. Pontosan egyszeri, tartós
kézbesítést nem állítunk. A Prometheus a számláló-visszaállást rate/increase alatt kezeli.

A fogadó nem naplózza a kliensek IP-címét, a kérések tartalmát vagy fejléceit;
a standard HTTP-hibanapló címet kiíró ágát is elnémítja. A meglévő Caddy és
környező infrastruktúra naplózási viselkedését telepítéskor külön ellenőrizni kell.
Új Caddy access logot nem kapcsolunk be. Titkos kulcs nincs a frontendben.

## Metrikák és korlátok

- frontend_api_requests_started_total{mode,route,method}
- frontend_api_http_responses_total{mode,status}
- frontend_api_outcomes_total{mode,route,outcome}
- frontend_api_fetch_headers_seconds_bucket/sum/count{mode,route,outcome,...}
- frontend_telemetry_batches_total, frontend_telemetry_duplicate_batches_total
- frontend_telemetry_rejected_total, frontend_telemetry_rate_limited_total
- frontend_telemetry_last_received_timestamp_seconds
- frontend_telemetry_receiver_start_timestamp_seconds, frontend_telemetry_receiver_up

A hisztogram a frontend diszjunkt kosarait kumulatív kosarakká alakítja.
Nem készítjük el minden method/status/route kombináció teljes keresztszorzatát.
A mode értéke real vagy partial_mock (bármelyik mock kapcsoló aktív).
Utóbbi sem jelenti, hogy minden hívás mock; a tényleges HTTP-hívásokat tartalmazza.

A timing a fetch válaszfejlécig tartó ideje, hibáknál az elutasításig tartó idő.
Nem a teljes választest letöltési ideje. A hisztogramnál outcome=http szűréssel
elemezzük a HTTP-válaszok idejét a megszakításoktól és hálózati hibáktól külön.

Az inflight és a böngésző kumulatív delivery diagnosztikája ellenőrzött
csomagmező marad, nem adjuk össze őket lapok között hibás globális számlálóvá.
A fogadó saját küldés-/elfogadási állapotmetrikákat vezet.
Üres életjel esetén a hiányzó üzleti idősor nem automatikusan nulla.
Hiányzó telemetria nem bizonyít sem nulla forgalmat, sem fogadóhibát:
lehet, hogy nincs nyitott lap. A frissesség és a receiver up külön jel.

A számlálók beérkezéskor nőnek: hosszabb böngészős időablak vagy újraküldés
késleltetett forgalmat okozhat. Először 5 perces grafikonok és megfigyelés
készüljenek, szigorú forgalmi egyezést követelő riasztás nélkül.
Csak backend nem-health API-forgalommal hasonlítunk; a monitoringpróbákat
és ismert teszteket kizárjuk. Nem állítunk támadást egy arányszám alapján.

## Bevezetés sorrendje

1. Read-only ellenőrzés: sudo docker inspect monitoring-caddy --format '{{json .Mounts}}'
   és a Prometheus élő scrape_configs részének ellenőrzése titkok megosztása nélkül.
2. Git fetch után a fejlesztési ágból pontos fájlokat git show-val külön
   ideiglenes könyvtárba kinyerni, ott a Python-teszteket futtatni.
   A helyi checkouton ágváltás és pull nincs.
3. Meglévő telepített fájlok mentése után a scriptet a
   /usr/local/lib/matchwise/frontend-traffic-receiver.py helyre, a service-t az
   /etc/systemd/system/matchwise-frontend-traffic.service helyre telepíteni.
   systemctl daemon-reload; szolgáltatás indítása; helyi health/metrics ellenőrzés.
4. Az élő Caddyfile mentése után az új handle útvonalat beilleszteni,
   caddy validate után reload. A Grafana elérését és a CORS-választ újra ellenőrizni.
   A példafájl nem automatikus helyettesítője az élő konfigurációnak.
5. Az élő prometheus.yml mentése után a külön scrape-részletet beilleszteni
   a meglévő scrape_configs alá; promtool check config után reload/restart,
   frontend_traffic target up ellenőrzése. A teljes repóbeli fájlt nem másoljuk rá.
6. Az alapból kikapcsolt frontend patch-et külön fejlesztési ágon alkalmazni,
   tesztelni, commitolni. A fogadó igazolása után külön konfigurációmódosítással
   lehet engedélyezni a https://grafana-r0cecq.duckdns.org/matchwise-telemetry/v1 címet.
   Ez a tervezett cím, a nyilvános elérés még nincs tesztelve.
7. Valódi böngészőből legfeljebb néhány tesztkérés, egy perc várakozás,
   fogadó/Prometheus-adat és a rendes frontendműködés ellenőrzése.

Visszaállítás: frontend enabled=false és új deploy, Caddy/Prometheus mentések
validálás utáni visszaállítása, a fogadószolgáltatás leállítása. Üzleti API útvonala változatlan.

## Frontend patch alkalmazása

Kiindulási frontend main: 50d1058a035fe8cfb14ce291c923ab77c31f20cb.
A patch nem tartalmaz függőségtelepítést, titkot vagy bekapcsolt fogadócímet.
A frontend saját munkakönyvtárában először git status --short --branch;
helyi módosításokat nem írunk felül és nem dobunk el.
Ezután külön ágon git apply --check, majd git apply a patch teljes helyi útvonalával.
Eltérés/ütközés esetén megállni és ellenőrizni, erőltetett alkalmazás nélkül.
Utána node --test tests/apiTraffic.test.js, npm run lint, npm run build,
git diff ellenőrzés, git add a patch fájllistája szerint és git commit.
Git push automatikus deployt indíthat; a mérés a patch-ben kikapcsolt.
Main merge-t most nem végzünk.

## Helyi teszteredmény

10 frontendteszt sikeres. 6 Python-fogadóteszt sikeres, köztük helyi HTTP,
CORS, hibás csomagok, ismétlésvédelem, hisztogram és globális limit.
A HTTP-teszt a helyi sandbox socketkorlátja miatt engedélyezett,
sandboxon kívüli futtatásban sikerült; nem az Oracle-t érte el.
A környezetben npm nincs, ezért teljes Vite build és oxlint nem futott.
A patch a CI-ba beilleszti a frontendtesztet; CI-siker még nem igazolt.
Caddy-validálás, systemd-indítás, Oracle/Prometheus-integráció, frontenddeploy,
böngészős CORS és teljes lánc még nincs igazolva.
