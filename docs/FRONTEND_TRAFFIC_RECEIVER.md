# Frontendforgalom – fogadó és biztonságos bevezetés

Állapot: a fogadó Oracle-ra telepítve, a felhasználó kimenetével igazolva.
A Caddy HTTPS-útvonalának helyi ellenőrzése és a fogadó Prometheus-bekötése sikeres.
A frontendkód az Oracle fejlesztési ágán alkalmazva, tesztelve és GitHubra pusholva.
A GitHub CI és a Vercel deploy státusza sikeres. Az aktiválás és a valódi
böngészős mérés még hátravan.
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
A felhasználó docker inspect kimenete igazolta a Caddy bind mountját:
/home/ubuntu/ai-job-monitoring/caddy -> /etc/caddy.
A Prometheus konfigurációja:
/home/ubuntu/ai-job-monitoring/prometheus/prometheus.yml -> /etc/prometheus/prometheus.yml.
A fogadó telepítése előtt a 9121-es port szabad volt.

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
A systemd-indítás és az Oracle helyi health/metrics elérése a felhasználó
kimenetével igazolt. A Caddy-validálás/reload, Prometheus-integráció,
frontenddeploy, böngészős CORS és teljes lánc még nincs igazolva.

## Oracle fogadótelepítés igazolva – 2026-11-18

A felhasználó a 1060584f6f0e6e40769e3db4ed06f6d0ace3baaf commitból
kivett fájlokkal telepített, ágváltás/pull nélkül. A 6 Python-teszt az
Oracle-on is sikeres (0,541 s). A systemd-szolgáltatás enabled és active (running),
ExecStart: /usr/bin/python3 /usr/local/lib/matchwise/frontend-traffic-receiver.py.
Indulás: 2026-11-18 21:40:12 Europe/Budapest (20:40:12 UTC).
A helyi /health válasza ok; a /metrics receiver_up=1 értéket és nulla
csomagszámlálókat mutat. Ez még nem frontendforgalom- vagy HTTPS-igazolás.

## Következő lépés: csak a Caddy útvonal

A scripts/enable-frontend-traffic-caddy.sh a rögzített 1060584 commitból
használja az ellenőrzött alapot és az új Caddyfile-példát.
A tényleges mountot és a host hálózati módot ellenőrzi. Eltérő alapnál megáll;
az alapváltozat és a már bekötött célváltozat is elfogadott.
Mentés: /home/ubuntu/monitoring-backups/frontend-traffic-caddy.XXXXXX.
Validálás után caddy reload, majd helyi HTTPS a valódi domainnel és certtel:
engedélyezett Origin OPTIONS=204 és megfelelő CORS fejléc,
tiltott Origin OPTIONS=403, hibás csomag POST=400, Grafana database=ok.
A hibás POST egy elutasított csomagot ad hozzá; üzleti forgalmat nem generál.
Sikertelen ellenőrzésnél a script megpróbálja visszamásolni és újratölteni
a mentett konfigurációt; a mentés helyét kiírja. A visszaállítás sikerét
valódi hibaszituációban még nem teszteltük.
Nem módosítja a Prometheust, a frontendkonfigurációt vagy a Git checkout ágát.

A segéd Bash-szintaxisellenőrzése sikeres. Az ellenőrzés a Windows Bash
sandboxkorlátozása miatt engedélyezett, sandboxon kívüli futtatásban történt;
a telepítőscriptet helyben nem hajtottuk végre, Oracle-futás még hátravan.

A validálás/reload a [Caddy CLI](https://caddyserver.com/docs/command-line),
a külön útvonal és a Grafana fallback a
[handle](https://caddyserver.com/docs/caddyfile/directives/handle) dokumentációját követi.

## Caddy rollout elakadás: sudo-ellenőrzés – 2026-11-18

A felhasználó kimenete alapján a Git fetch sikeres: a fejlesztési ág
09c8d705 commitig letöltve. Az SSH-kulcs passphrase kérése és a sudo
ubuntu-jelszókérése két külön hitelesítés. A segéd a korai sudo -v
ellenőrzésnél állt meg, három hibás próbálkozással; ebben a futásban nem
jutott el Caddyfile-módosításig vagy reloadig. A korábban telepített fogadó
állapotát ez a sikertelen futás nem módosította.

A sudo -v szabályfüggően akkor is kérhet jelszót, ha egyes konkrét parancsok
NOPASSWD joggal rendelkeznek (verifypw). Ez lehetséges magyarázat, az Oracle
konkrét sudo-szabályai még nincsenek igazolva.
A segédből eltávolítottuk a sudo -v lépést, és minden tényleges sudo-hívás
sudo -n formában fut: jelszókérés helyett jogosultsághiánynál megáll.
Ez nem ad új jogosultságot és nem módosít sudoers-beállítást.
A javított Bash-szintaxis ellenőrzése sikeres, Oracle-újrafuttatás még nem történt.
Következő csak olvasó diagnosztika: sudo -n -l, majd
sudo -n systemctl is-active matchwise-frontend-traffic.service.
Hiba esetén is a teljes kimenetet kell értékelni; jelszót nem kérünk be.

Forrás: [sudoers – verifypw](https://github.com/sudo-project/sudo/blob/main/docs/sudoers.man.in).

## Caddy HTTPS-próba sikeres, CR-sorhiba javítva – 2026-11-18

A felhasználó visszaadta a javított sudo -n segéd kimenetét:
Valid configuration, Grafana database=ok, PASS a 204/403 CORS- és 400 POST-próbákkal.
Mentés: /home/ubuntu/monitoring-backups/frontend-traffic-caddy.drfoPx.
A próbák helyi HTTPS-en, --resolve használatával futottak: ez nem teljes,
külső böngészős elérésigazolás és nem igazolt frontenddeploy.

A PASS után a 107. sorban egy külön CR karakter command not found hibát okozott.
A Git-fájl lekérése igazolta az egyetlen fölösleges CR karaktert a végén.
Ezt eltávolítottuk. A successful=true beállítás már a hibás sor előtt megtörtént,
így a script visszaállítást nem indított; a sikeres Caddy-bekötést nem kell
emiatt újrafuttatni. A Caddy behúzásra vonatkozó figyelmeztetése nem validálási hiba.

## Következő lépés: Prometheus

A scripts/connect-frontend-traffic-prometheus.py --self-test három helyi
tesztje sikeres: eredeti kommentek/beállítások megőrzése, eltérő behúzás,
már létező feladat vagy nem támogatott elrendezés biztonságos elutasítása.
A script Oracle-futtatása és a Prometheusba történő adatbeérkezés még hátravan.

A --apply ellenőrzi a bind mountot, a host hálózatot és a fogadó állapotát.
A meglévő élő prometheus.yml tartalmába egy új frontend_traffic feladatot szúr,
60s/10s időzítéssel, 127.0.0.1:9121 címmel. Az eredeti tartalmat nem cseréli le
a repóban lévő teljes konfigurációra. Nem használ új Python-függőséget.
A támogatott block-style scrape_configs elrendezéstől eltérő esetben megáll.
A már létező frontend_traffic feladatnál nem illeszt be duplikátumot.

Mentés és jelölt konfiguráció a /home/ubuntu/monitoring-backups alá kerül,
privát könyvtárba és 0600 jogosultságú fájlokba; a konfigurációt nem írja ki.
A konténerben, az eredeti konfiguráció könyvtárában promtool check config fut,
így a titkos fájlokra és relatív hivatkozásokra is ellenőriz.
A gazdagépfájl inódját megtartja a Docker egyfájlos bind mountja miatt.
Újratöltés SIGHUP-pal történik, nem szükséges a web lifecycle endpoint megnyitása.
Forrás: [Prometheus újratöltés](https://prometheus.io/docs/prometheus/latest/configuration/configuration/).

A script legfeljebb 90 másodpercig vár az első scrape-re. Sikerhez kell:
az előző feladatok jelenléte, a frontend_traffic target up állapota,
a megfelelő scrape URL és a frontend_telemetry_receiver_up=1 lekérdezhető minta.
Hiba esetén megpróbálja visszaírni és újratölteni a mentett konfigurációt;
a tényleges visszaállítást hibaszituációban még nem teszteltük.
Caddy-, frontend- és riasztásmódosítás ebben a lépésben nincs.

## Prometheus-integráció Oracle-on igazolva – 2026-11-18

A felhasználó a 326ca439b26c38f6f4f625014a39b72402f96f80 verzió
Prometheus-segédjének kimenetét adta vissza. A 3 konfigurációmegőrzési teszt
az Oracle-on is sikeres (0,002 s). A jelölt és az élő konfiguráció
promtool check config ellenőrzése sikeres.
Mentés: /home/ubuntu/monitoring-backups/frontend-traffic-prometheus.uevpd6hx/prometheus.yml.before.
A segéd PASS eredménye igazolja: frontend_traffic target up,
frontend_telemetry_receiver_up=1 lekérdezhető a Prometheusból,
a korábbi feladatok nevei az aktív targetek között megmaradtak.
Ez a korábbi feladatok teljes mérési egészségét külön nem igazolja.

Igazolt láncszakasz: Oracle-fogadó -> Prometheus.
A frontendmérés továbbra is alapból kikapcsolt; valódi böngészős
adatküldés, külső CORS, frontenddeploy és összehasonlító Grafana-panelek
még nincsenek igazolva. Main összevonás nem történt.
Következő lépés: a frontend munkapéldány azonosítása, a kikapcsolt patch
fejlesztési ágon alkalmazása, frontendtesztek/lint/build, majd az
engedélyezés és a deploy célágának tisztázása után korlátozott böngészős próba.

## Frontend munkapéldány elkészült – 2026-11-18

A felhasználó az Oracle-on klónozta a nyilvános ernoking/job-portal-frontend repót
/home/ubuntu/job-portal-frontend alá, és létrehozta a feat/frontend-api-traffic ágat.
A korábbi patch alkalmazása sikeres volt, de két új üres zárósor miatt a
git diff --check hibával megállt: src/api/http.js és src/main.jsx.
A blokk ezért a Node/npm verziók kiírásáig nem jutott el.
Ez formázási hiba; a frontend build és működés ettől még nem igazolt.

A patch-ben a két fájl végét egyetlen LF-re normalizáltuk.
A javított patch git apply --check --whitespace=error próbája sikeres.
A már módosított Oracle munkapéldányra nem alkalmazzuk újra a teljes patch-et;
ott csak a két fájl felesleges üres zárósorait távolítjuk el, majd
újra git diff --check és Node/npm verzióellenőrzés következik.
Frontendcommit, push, deploy és adatküldés továbbra sincs igazolva.

## Frontendvalidálás Oracle-on sikeres – 2026-11-18

A felhasználó kimenete alapján a /home/ubuntu/job-portal-frontend
feat/frontend-api-traffic munkapéldányában a formázási javítás után
sikeres a git diff --check. Node.js v24.22.2 és npm 11.19.1 elérhető.
Az npm ci 28 csomagot telepített, az audit a futtatáskor 0 sérülékenységet jelzett.
Az npm run test:telemetry mind a 10 tesztje sikeres.
Az npm run lint 0 figyelmeztetéssel és 0 hibával zárt (70 fájl, 104 szabály).
Az npm run build Vite 8.3.4-gyel sikeres (123 transzformált modul).
A blokk utolsó git diff --check lépése nem jelzett hibát.
Ez a forrás buildelhetőségét és a tesztelt viselkedéseket igazolja;
nem frontenddeploy- vagy böngészős adatküldés-igazolás.
A mérés konfigurációja továbbra is kikapcsolt. Frontendcommit és push még nincs visszaigazolva.
Következő lépés: a pontos fájlok commitolása az új fejlesztési ágon,
majd normál, force nélküli push. HTTPS-hitelesítésnél interaktív jelszókérést
nem indítunk; hiányzó hitelesítés esetén a hibát külön kezeljük.
Main összevonás és telemetria-aktiválás ebben a lépésben nincs.

## Frontendcommit elkészült, HTTPS-push hitelesítés hiányzik – 2026-11-18

A felhasználó kimenete igazolja az Oracle-on létrejött d180f6f helyi commitot,
feat/frontend-api-traffic ágon, 10 fájllal (545 beszúrás, 2 törlés).
A push sikertelen: could not read Username for https://github.com:
terminal prompts disabled. Ez nem GitHubon igazolt ág vagy deploy.
A helyi commitot megőrizzük, nem készítjük újra és nem reseteljük.

Következő lépésként GitHub CLI webes/device hitelesítést javaslunk a
felhasználó saját fiókjával, HTTPS-protokollal. A workflow scope szükséges
az érintett .github/workflows/ci.yml fájl pushához OAuth-token használatakor.
A hitelesítő segédet a frontendrepó helyi konfigurációjához állítjuk be.
Nincs token beillesztése parancssorba, távoli URL-be vagy chatbe.
A monitoring SSH-aliasát és kulcsát nem módosítjuk.
A gh telepítése/bejelentkezés és az új push még nem igazolt.

Források: [gh auth login](https://cli.github.com/manual/gh_auth_login),
[GitHub CLI mint Git hitelesítő segéd](https://cli.github.com/manual/gh_auth_setup-git).

## Frontend push, CI és deploy státusz igazolva – 2026-11-18

A felhasználó push-kimenete igazolja a feat/frontend-api-traffic ág létrejöttét
és az origin követését. A kapcsolt GitHub-eszközzel ellenőrzött HEAD:
d180f6f06bc5ded13bf55a5f6f6f7baf6d6334ea.
GitHub Actions CI run 44400084367: completed/success, check: completed/success.
[CI](https://github.com/ernoking/job-portal-frontend/actions/runs/44400084367).
A Vercel commit status success, leírása: Deployment has completed.
[Deploy státusz céloldala](https://vercel.com/ai-job-portal1/matchwise/977ZAK7axrdQqNXwT9uSwb9Ko5wx).
A Vercel Preview Comments check is success; ez visszajelzés-kezelési check,
nem külön bizonyíték az alkalmazás funkcionális működésére.

A Vercel check által megadott preview-eredet:
https://matchwise-git-feat-frontend-api-traffic-ai-job-portal1.vercel.app.
A webes eszköz ezt nem tudta megnyitni; ebből nem következtetünk a
Vercel-védelem állapotára vagy a felhasználó böngészős elérésére.
A felhasználói megnyitás és az esetleges Vercel-hitelesítés még ellenőrzendő.

A frontend forráskonfigurációja továbbra is enabled=false és üres endpoint.
A fogadó jelenleg csak https://www.matchwise.tech Origin-t engedélyez.
Preview-ból történő aktiválás előtt a pontos preview Origin-t külön,
verziózott konfigurációval engedélyezni kell, wildcard nélkül.
A preview próbaforgalma nem tekinthető a www.matchwise.tech éles felhasználói
forgalmának. Main merge, éles telemetria és új összehasonlító panelek még nincsenek igazolva.

## Preview-hozzáférés hiányzik; külön böngészős fogadópróba – 2026-11-18

A felhasználó megnyitotta a preview-címet: Vercel-bejelentkezést kér,
és ehhez nincs hozzáférése. A preview teszthez jelenleg nem használható.
Nem módosítjuk a Vercel védelmét, és main merge-t sem végzünk.
A teljes frontendváltozat böngészős ellenőrzéséhez a projekt kezelőjétől
preview-hozzáférés vagy más jóváhagyott teszttelepítés szükséges.
A projekt kezelőjének üzenetet nem küldtünk.

A fogadó külső böngészős HTTPS/CORS-útvonala ettől függetlenül ellenőrizhető:
a https://www.matchwise.tech oldalon megnyitott fejlesztői konzolban
az alábbi üres csomagot küldjük. Ez nem a módosított request() automatikus
mérésének, nem a percenkénti működésnek és nem az éles build mock
kapcsolóinak igazolása. Nem küld üzleti kéréseket vagy személyes adatot.
Csak a fogadó csomagszámlálóját és a fogadás frissességét változtatja;
a frontendforgalmi számlálókhoz nem ad kitalált kéréseket.
A próba még nincs visszaigazolva.

```javascript
(async () => {
  if (location.origin !== "https://www.matchwise.tech") {
    throw new Error("A tesztet a https://www.matchwise.tech oldalon futtasd.");
  }
  const now = Date.now();
  const response = await fetch(
    "https://grafana-r0cecq.duckdns.org/matchwise-telemetry/v1",
    {
      method: "POST",
      headers: { "Content-Type": "text/plain;charset=UTF-8" },
      credentials: "omit",
      referrerPolicy: "no-referrer",
      body: JSON.stringify({
        schema_version: 1, batch_id: crypto.randomUUID(),
        window_start_ms: now, window_end_ms: now, interval_ms: 60000,
        timing: "fetch_response_headers", mock_api: false, mock_jobs: false,
        inflight: 0,
        duration_limits_ms: [100, 250, 500, 1000, 2500, 5000, 10000, 30000, 60000],
        starts: [], results: [],
        delivery: { sent_batches: 0, failed_attempts: 0,
          dropped_batches: 0, dropped_observations: 0 }
      })
    }
  );
  console.log("Fogadó válasza:", response.status);
})().catch(error => console.error("Teszt sikertelen:", error.message));
```

Elvárt válasz: Fogadó válasza: 204. Ez böngésző -> Oracle átvételt igazol;
a Prometheusban való megjelenést utána külön ellenőrizzük.

## Külső böngészős üres csomag átvétele igazolva – 2026-11-18

A felhasználó a www.matchwise.tech oldalon futtatott, fent dokumentált
konzolpróbára Fogadó válasza: 204 eredményt adott vissza.
Ez igazolja a böngésző -> nyilvános Oracle HTTPS -> fogadó útvonalat,
a www Origin-hoz tartozó CORS-válasz olvashatóságát és az üres,
verziózott csomag sikeres fogadását.
A próba üres starts/results listákat tartalmazott; üzleti API-forgalmat
nem szimulált. A csomagszámláló és az utolsó fogadás időpontjának
Prometheusbeli ellenőrzése a következő lépés, még nincs visszaigazolva.

A frontend automatikus mérőkódja továbbra is kikapcsolt.
A védett preview-hoz nincs felhasználói hozzáférés; a 60 másodperces automatikus
böngészős küldés, üzleti API-kérések mérése és a teljes frontendintegráció
ettől a konzolpróbától nem vált igazolttá. Main összevonás nincs.

## Böngészős próba Prometheusban igazolva; dashboard előkészítve – 2026-11-18

A felhasználó Prometheus-kimenete success állapotú, job=frontend_traffic,
instance=127.0.0.1:9121 idősorokat mutat:
frontend_telemetry_batches_total=1;
frontend_telemetry_last_received_timestamp_seconds=1795037032.555537.
A lekérdezés ideje 1795037230 körül volt. Ez az üres konzolpróba
böngésző -> Oracle -> Prometheus adatútját igazolja, nem automatikus,
percenkénti forgalommérést és nem valódi üzleti kérések mérését.

A meglévő Service Comparison dashboardhoz hat új panelt készítettünk elő,
41 összes panellel. A korábbi 35 panel változatlan. A forgalom és latencia
közös Prometheus/Loki grafikonon látható majd, adatfrissességi kapuval és
kitalált nullaértékek nélkül. A panelek és a 9 lekérdezést ellenőrző,
csak olvasó segéd Gitben verziózott; a JSON/Python szerkezeti ellenőrzés sikeres.
Az Oracle-lekérdezéspróba és a paneltelepítés még hátravan.
Részletek: [dashboard](SERVICE_COMPARISON_DASHBOARD.md#frontendforgalmi-bővítés--2026-11-18).
A védett preview hiánya továbbra is fennáll; a frontendmérés kikapcsolt,
main merge nincs. A további automatikus frontendteszthez a Vercel-projekt
kezelőjének preview-hozzáférést vagy más engedélyezett telepítést kell biztosítania.

## Új dashboard-lekérdezések Oracle-próbája sikeres – 2026-11-18

A felhasználó a cef1f2d83d166339f2963c69e475f20b6168bdfd verzió
csak olvasó ellenőrzésének kimenetét adta vissza. Mind a kilenc
Prometheus/Loki lekérdezés success eredményű, a segéd Preflight PASS.
A 38/39/40 stat panelek lekérdezése egy-egy idősorral tért vissza.
A 41/42 forgalmi/latenciapanelek hat lekérdezése üres.
Ez nem lekérdezési hiba. A frontendmérés kikapcsolt; a backend üres
API-naplóeredménye önmagában nem igazol nulla forgalmat vagy hibátlan collectort.
A lekérdezéspróba nem Grafana-megjelenítési vagy frontend-aktiválási bizonyíték.

A repóban a dashboard provider updateIntervalSeconds értéke 30,
az allowUiUpdates false; a betöltési út /etc/grafana/provisioning/dashboards/json.
Következő lépés: Grafana bind mount ellenőrzése, az élő dashboard teljes mentése,
a meglévő panelek és metadata összehasonlítása a megőrzött alappal,
majd csak a Service Comparison JSON fájl telepítése. Eltérés esetén megállunk.
Nincs Grafana-újraindítás vagy main merge; a vizuális ellenőrzés még hátravan.
