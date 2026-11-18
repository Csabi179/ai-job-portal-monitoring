# Teljes frontendteszt SSH-alagúton

Állapot: a Vite-indítás, az SSH-alagúton történő oldalbetöltés és az ismétlődő automatikus telemetriaküldés felhasználói kimenettel/képpel igazolt.
A tényleges API-forgalom mérése és a frontend Grafana-görbék megjelenése igazolt.
A backend összehasonlító görbéi még nem látszanak; ennek oka diagnosztika alatt.
A felhasználó megerősítette, hogy SSH-val csatlakozik az Oracle-ra.
Nincs main merge és nincs új nyilvános fejlesztői port.

## Cél és adatút

Az Oracle /home/ubuntu/job-portal-frontend, feat/frontend-api-traffic munkapéldányát teszteljük.
A Vercel preview nem elérhető a felhasználónak. Ez a teszt saját, engedélyezett
forrásból fut, nem változtatja meg a Vercel-hozzáférést vagy annak védelmét.

Böngésző http://localhost:5173 -> saját SSH-alagút -> Oracle 127.0.0.1:5173
-> Vite /api proxy -> Render -> Supabase.
Telemetria: böngésző -> nyilvános Oracle HTTPS-fogadó -> Prometheus -> Grafana.

A Vercel routingot és az éles frontendtelepítést ez a teszt nem igazolja.
A mode=real valódi HTTP-hívásokat jelent, nem feltétlenül éles felhasználói eredetet.
A kontrollált teszt idejét dokumentálni kell, nem természetes éles forgalomként értelmezni.

## Verziózott fájlok

- frontend-test/vite.monitoring-test.config.mjs: a frontend gyökerébe másolandó külön config.
- systemd/matchwise-frontend-traffic-local-test.conf: ideiglenes drop-in.
  Telepítési hely: /etc/systemd/system/matchwise-frontend-traffic.service.d/50-local-browser-test.conf.

A Vite-konfiguráció megtartja az alap React plugint, de a /api proxyt a Renderre állítja.
A szokásos vite.config.js az Oracle-on a Grafana 3000-es portjára vinne API-hívásokat.
A tesztconfig csak 127.0.0.1:5173 címen figyel, strictPort-tal;
allowedHosts: localhost és 127.0.0.1. Nem lesz allowedHosts=true vagy 0.0.0.0.
A Node-szintaxisellenőrzés helyben sikeres. A felhasználó Vite v8.3.4 ready üzenetet és 127.0.0.1:5173 helyi címet adott vissza.

## Indítás Oracle-on

A monitoring fejlesztési ágból a két fájlt git show-val, rögzített commitból nyerjük ki.
Meglévő, eltérő tesztconfig/drop-in esetén megállunk, nem írjuk felül.
A drop-in megtartja a www.matchwise.tech eredetet és hozzáadja kizárólag
a http://localhost:5173 eredetet. Nem engedélyez wildcardot vagy más localhost portot.
A fogadó újraindítása nullázza annak memóriabeli számlálóit és deduplikációját;
a korábbi Prometheus-minták megmaradnak. A helyi Origin OPTIONS válaszát ellenőrizni kell.

A frontend könyvtárában a külön configgal, csak az adott folyamatra:

```bash
env VITE_FRONTEND_TELEMETRY_ENABLED=true \
  VITE_FRONTEND_TELEMETRY_URL=https://grafana-r0cecq.duckdns.org/matchwise-telemetry/v1 \
  VITE_USE_MOCK_API=false VITE_USE_MOCK_JOBS=false \
  npm run dev -- --config vite.monitoring-test.config.mjs
```

A frontend forrásbeli trafficConfig.js enabled=false értéke nem változik.
A már elkészült telemetry kód a Vite-változókat a fájlkonfiguráció előtt használja.
Nem írunk .env fájlt és nem teszünk titkot a konfigurációba.

## Saját gép: SSH-alagút és böngésző

A saját szokásos OpenSSH-parancsban, a meglévő kulcs/host beállítások megtartásával:
-N -o ExitOnForwardFailure=yes -L 127.0.0.1:5173:127.0.0.1:5173.
Az opciókat a távoli cél elé kell tenni. A helyi és távoli végpont is loopback.
PuTTY esetén helyi tunnel: source 5173, destination 127.0.0.1:5173.
Nem továbbítunk SSH-agentet.

A saját böngészőben pontosan http://localhost:5173 legyen; a 127.0.0.1 URL
más Origin, a fogadó tesztengedélye nem tartalmazza automatikusan.
Az első automatikus csomag egy perc után várható; lap maradjon előtérben.
A Network nézetben a matchwise-telemetry/v1 POST válasza 204 legyen.
Néhány normál, olvasó API-művelettel és pár perc megfigyeléssel tesztelünk,
nem terheléses vagy hibásbejelentkezés-sorozattal.

Külön ellenőrzendő: valódi API-válaszok (szükség esetén backend CORS),
60 másodperces automatikus küldés, számlálók növekedése, majd Grafana.
Az elsőként létrejött counter-idősor és az 5 perces rate miatt a görbékhez
további minták és újabb normál kérések is szükségesek lehetnek.
A puszta Vite-indítás nem indít böngészős telemetriát.

## Leállítás

A Vite terminálban Ctrl+C, az SSH-alagút termináljában Ctrl+C.
A külön teszt-drop-in eltávolítása után daemon-reload és fogadó restart
visszaállítja az eredeti www-only Origin beállítást, ha más drop-in nem módosítja.
Csak a fenti pontos drop-in fájlt távolítjuk el, nem a teljes könyvtárat.
Ez is nullázza a memóriabeli számlálókat; a teszt időablakát fel kell jegyezni.
A frontend új tesztconfigja később külön commitban kerülhet a frontend ágra;
addig is a monitoringrepóban verziózott. Éles frontendaktiválás külön lépés.

Források: [Vite server options](https://vite.dev/config/server-options),
[OpenSSH -L](https://man.openbsd.org/ssh#L).

## Ismétlődő automatikus küldés igazolva – 2026-11-18

A felhasználó megerősítette, hogy az alkalmazás a saját böngészőjében,
SSH-alagúton betöltődött. A Network-kép négy POST kérést mutat a
fogadó grafana-r0cecq.duckdns.org /matchwise-telemetry/v1 végpontjához,
mind a négy 204 állapottal; initiator: apiTraffic.js (fetch).
Ez az automatikus, ismétlődő küldést és a fogadást igazolja.
A pontos kérések közötti 60 másodperces távolságot a képből külön nem mérjük ki;
a periódus a kódban 60 000 ms és egységteszttel ellenőrzött.
A kép a csomagtörzseket nem mutatja, ezért ebből nem állítunk valódi
üzleti API-eseményeket, sikeres álláslistát vagy új Prometheus-forgalmi mintákat.
Következő próba: normál álláslista-/részletmegnyitás, következő csomag starts/results
listáinak ellenőrzése, majd Prometheus/Grafana. Nem küldünk szándékos hibasorozatot.
Az SSH-s teszt nem éles Vercel frontendtelepítés. Main összevonás nincs.

## Valódi API-események a csomagban igazolva – 2026-11-18

A felhasználó a 11226837-b2fa-446c-aef2-69e0368bff30 csomag összesített tartalmát
adta vissza. Időablak: 1795039361018–1795039421018 ms, pontosan 60 000 ms;
interval_ms=60000, mock_api=false, mock_jobs=false, inflight=0.
Starts és results egyaránt három eseményt tartalmaz, két dimenziósorban:
- auth / POST: 1 HTTP 200; fejlécig mért idő 759 ms.
- cv / GET: 2 HTTP 200; időösszeg 1489 ms, maximum 964 ms (átlag 744,5 ms).
A diszjunkt időtartamkosár mindhárom megfigyelést az 500–1000 ms tartományba sorolja.
Delivery: sent_batches=10, failed_attempts=0, dropped_batches=0, dropped_observations=0.
Ezek a böngésző adott lapjának korábbi küldési diagnosztikái, nem globális számlálók.
A csomag átvétele a korábbi Network-képen 204 volt.

Ez tényleges API-indítások, HTTP-válaszok, csoportosítás és időmérés működését
igazolja az SSH/Vite tesztúton. Nem teljes választestidő és nem éles Vercel-forgalom.
A három esemény Prometheus-számlálóinak és a Grafana görbéinek ellenőrzése még hátravan.
Az elsőként megjelenő counter-idősor első értékéből a rate nem tud előző
növekményt számolni; a görbékhez következő normál kérések és további scrape-minták kellenek.
Egy normál oldalfrissítéssel, majd két perc megfigyeléssel folytatjuk,
nem mesterséges hibasorozattal vagy terheléses próbával.

## Frontend forgalmi és latenciagörbék megjelentek – 2026-11-18

A felhasználó Grafana-képe a Last 15 minutes időablakban igazolja:
fogadó scrape UP, utolsó csomag kora 1,56 perc, elfogadott csomagok száma 27.
Látszik a frontend API starts/min és HTTP responses/min idősora, valamint
a böngészős fejlécig mért átlag és kosarakból becsült P95.
A kép végén hozzávetőleg 1 indítás/perc, 1,5 válasz/perc,
550 ms átlag és 950 ms becsült P95 látszik. Ezek vizuális közelítések,
nem nyers lekérdezési vagy benchmarkeredmények.
A rate értékek beérkezési ütemet és külön indítás-/befejezésszámlálókat
követnek; a köztük lévő eltérés önmagában nem bizonyít hibát.

Igazolt a tényleges frontend API-adatok útja az SSH/Vite tesztböngészőtől
a fogadón és Prometheuson át a Grafana frontendgörbéiig.
A backend görbék és azok legendái nem látszanak a képen.
Ezért a frontend-backend összefüggések teljes összehasonlítását még nem
tekintjük késznek. Nem következtetünk a hiányzó görbéből nulla backendforgalomra.

A scripts/diagnose-backend-comparison.py kizárólag olvasó Prometheus/Loki
lekérdezéseket futtat: collector-frissesség, frontend kumulatív számlálók,
15 perces backend nyers naplódarabszám, értelmezhető HTTP-események,
non-health események, /api prefixszűrés, relatív API-csoportok,
hiányzó route és naplózott időadatok. Csak összesített számokat ír ki,
nyers naplót, útvonalakat, felhasználói adatokat vagy titkokat nem.
A segéd Python-szintaxisellenőrzése sikeres; az Oracle-kimenet még hátravan.
A /api szűrőt csak e bizonyíték alapján változtatjuk, nem vakon tágítjuk.
Éles Vercel-mérés és main merge továbbra sincs.

## Backend–Supabase közös grafikonok megjelenése igazolva – 2026-11-18

A felhasználó képe igazolja a három új grafikon megjelenését:
backend API requests/min és Supabase committed transactions/s;
Render CPU % és Supabase committed transactions/s;
backend processing P95 és PostgREST waiting requests.
A jobb oldali tengelyek külön mértékegységet mutatnak. A sárga DB-tranzakciógörbe
nem CPU-százalék: a zöld Render CPU-görbe ezen a mintán alacsony.
A PostgREST várakozási sor mintái a képen 0-t mutatnak; ebből nem következik,
hogy rövid tüskék, PostgreSQL lock-várakozás vagy más szűk keresztmetszet sosem volt.
A DB-aktivitás belső szolgáltatásokból és más kliensekből is eredhet;
a görbék együttmozgása önmagában nem ok-okozati vagy rendellenességi bizonyíték.

Az első, közös grafikonokra épülő forgalmi megfigyelési változat működik:
a 45 paneles dashboardban a frontend–backend és backend–Supabase kontextus
az Oracle SSH/Vite frontendteszttel ellenőrizve. Automatikus összetett
riasztás, terheléses/DDOS-próba és éles Vercel frontendmérés nincs bevezetve.
A meglévő éles main ágat nem vontuk össze.

A külön Vite-tesztconfig eddig a monitoringrepóban verziózott és a frontend
Oracle-munkapéldányában tesztelt fájl. A frontend-test/SSH_MONITORING_TEST.md
rövid, a frontendrepóba átemelhető útmutatót ad. Következő lépés e két fájl
commitolása/pusholása a frontend feat/frontend-api-traffic ágára, majd a
Vite/SSH-alagút leállítása és az ideiglenes localhost CORS drop-in eltávolítása.
Ezek még nincsenek visszaigazolva. A fogadó újraindításakor a memóriabeli
számlálók nullázódnak, a korábbi Prometheus-adatok megmaradnak.
