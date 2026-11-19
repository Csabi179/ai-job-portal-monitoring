# Frontend API-forgalom mérése – megvalósítási terv

> **Aktuális telepítési állapot — 2026-11-19:** Az üzemeltető minden átadott módosítást már alkalmazott az Oracle-on. A monitoringág bekerült a `main` ágba (`10f43d1`); emiatt nincs újratelepítési feladat. [Aktuális állapot](DEPLOYMENT_STATUS.md). A korábbi bevezetési bejegyzések történeti állapotok; a parancsok későbbi frissítéshez vagy helyreállításhoz maradnak meg.

Dátum: 2026-11-18.
Aktuális állapot: az éles frontendmérés és az Oracle-adatút működik, az üzemeltető minden átadott frissítést alkalmazott. Az alábbi terv a november 18-i megvalósítási előzményt őrzi. [Megvalósítás, fájlok és bevezetés](FRONTEND_TRAFFIC_RECEIVER.md).
Monitoringág: main; a feat/service-comparison összevonása 2026-11-19-én megtörtént. Az alábbi lépések történeti tervek, nem új merge utáni teendők.

## Történeti terv — 2026-11-18

### Ellenőrzött kiindulás

A felhasználó szerint minden szolgáltatás ingyenes csomagban van, nincs közvetlen Vercel-hozzáférése, a frontend forrását módosíthatja. A felhasználó megerősítette, hogy a frontendnél automatikus deploy működik. A deployt indító ágak és a fejlesztési ág preview telepítése még nincs igazolva.

A kapcsolt GitHub-eszközzel ellenőrzött forrás:
- ernoking/job-portal-frontend, main, src/api/http.js:
  blob 396ce2cf5c932f28a4df072c11a873a052fdd605.
  Közös request() segéd; apiFetch ugyanennek az aliasa.
- vercel.json: blob c8ac6e44aacc0d37d4686d4e780ab0054d72d32c.
  /api/:path* -> https://matchwise-backend-monitoring-test.onrender.com/api/:path*.
- A monitoringág ellenőrzött kiinduló HEAD-je:
  c2c66effecd7679b7d5265ddd4803c1975b51664.
- A repó Caddy-konfigurációja a grafana-r0cecq.duckdns.org hoston
  a helyi Grafanához továbbít. Ez nem bizonyítja az Oracle élő konfigurációját.

A frontend main forrása nem bizonyítja az éles deployment tartalmát.

## Javasolt egyszerű adatút

Böngésző request() -> memóriában összesített számlálók
-> időszakos HTTPS POST az Oracle fogadójának
-> helyi Prometheus-metrikák -> Grafana.

Az üzleti API-kérések útvonala marad Vercel -> Render -> Supabase.
A telemetria külön, közvetlen Oracle-hívás legyen, a request() segéd megkerülésével.
A fogadó ne a Renderen fusson: így a Render kiesése önmagában nem
akadályozza a frontendjelentés fogadását.

Új fizetős szolgáltatás nem szükséges a tervhez; az Oracle meglévő
erőforrásainak elegendőségét a telepítés során kell ellenőrizni.

## Első változat javasolt adatai

- Elindított API-kérések száma.
- HTTP-válaszok száma státuszkód szerint.
- Válasz nélkül végződő fetch-hibák külön számlálója.
- Böngészőben mért idő összege, maximuma, elemszáma és fix időtartamkosarak;
  a későbbi lassulás- és percentiliselemzéshez előkészítve.
- Fogadott jelentések száma, utolsó sikeres fogadás ideje,
  a fogadó működését jelző saját állapot.

Rögzített időhatár: a fetch indításától a válaszfejlécekig tartó idő,
hibánál a fetch elutasításáig. A választest teljes beolvasását és
a JSON feldolgozását nem méri. A fetch-hiba nem bizonyít backendhibát;
hálózati hiba vagy megszakítás is lehet.

Felhasználói követelmény: az összesítések időzített küldése 60 másodpercenként
(1 perc) történjen, böngészőlaponként. Nincs külön háttérbe kerüléskor
indított küldés. A böngésző háttérben késleltetheti az időzítőt;
ez nem garantált, pontos falióra szerinti percenkénti kézbesítés.
A küldés nem blokkolhatja az üzleti kéréseket.
Nincs korlátlan sor vagy korlátlan újrapróbálkozás.
Ha van újraküldés, batchazonosítóval és korlátozott idejű
duplikációszűréssel kell elkerülni a dupla számlálást.

Rögzített, engedélyezett API-csoportok vannak; nyers útvonal,
felhasználó- és sessionazonosító, query string, token,
kérés-/választörzs és IP-cím nem kerül a jelentésbe.
A proxy és fogadó alkalmazás saját naplóbeállításait is ellenőrizni kell.

## Korlátok és védelem

Ez böngészőoldali API-mérés, nem Vercel access log.
Csak a módosított segéden átmenő valódi HTTP-kéréseket látja.
Mock mód, más fetch-hívások, közvetlen backendhívások és a mérőkódot
nem futtató kliensek nem fedhetők le automatikusan.

Lapbezárás, offline állapot vagy blokkolás miatt jelentés elveszhet.
Hiányzó telemetria nem tekinthető nulla forgalomnak. Az utolsó
fogadás ideje nem bizonyítja minden böngésző jelentésének teljességét.
A frontendadat kliens által módosítható; nem biztonsági bizonyíték.

A nyilvános fogadóhoz méret-, séma-, számérték- és terhelési korlát kell.
CORS csak a szükséges frontend eredeteket engedje; nem hitelesítés.
Frontendbe titkos kulcsot nem teszünk.
A Prometheus/Loki belső végpontjait nem nyitjuk meg a böngészőknek.

## Összehasonlítás

Kezdetben közös 5 perces grafikonok, összetett riasztás nélkül:
frontend indítások/válaszok, backend nem-health API-forgalom,
Render CPU, elérhető Supabase aktivitás/várakozás.

A telemetriát, health próbákat és ismert szintetikus kéréseket
az összehasonlítható üzleti forgalomból ki kell zárni.
Eltérést okozhat eltérő lefedettség, cache, megszakítás, közvetlen hívás,
eltérő időablak vagy gyűjtési késés. Az eltérés önmagában nem támadás.

## Következő lépések

1. Automatikus frontenddeploy visszaigazolva; ellenőrizni, mely ágak
   indítanak éles vagy preview telepítést. Main összevonást nem végzünk.
2. Oracle-on csak olvasással ellenőrizni az aktuális Git-állapotot,
   élő Caddy-konfigurációt és elérési korlátozásokat.
3. Ezek alapján megírni a kis fogadót és frontendkiegészítést,
   külön fejlesztési ágakon, dokumentációval.
4. Ellenőrizni: 2xx/4xx/5xx, fetch-hiba, 204, kijelentkeztetés,
   fogadókiesés alatti zavartalan üzleti API, duplikált/hibás csomagok.
5. Korlátozott próba és Grafana-adatellenőrzés; csak ezután éles bekötés.
   Main összevonás külön felhasználói kérésig nincs.

Oracle ágváltás/pull előtt helyi módosításokat és nem követett fájlokat
ellenőrizni kell; az élő checkout fejlesztési ágra váltása nem igazolt.

## Fejlesztési implementáció és Oracle-állapot – 2026-11-18

A frontend kódja 60 másodperces időzítéssel, verziózott csomaggal,
fix útvonalcsoportokkal és időtartamkosarakkal elkészült. Alapból kikapcsolt.
A frontend GitHub-kapcsolata az ág létrehozását 403-mal elutasította;
a teljes módosítás ezért a patches/frontend-api-traffic.patch fájlban verziózott.
Nincs frontend-ág vagy igazolt deploy ettől a változtatástól.
10 frontendteszt és 6 fogadóteszt sikeres; git apply --check sikeres.
Teljes frontend build/lint nem futott: npm nincs a helyi környezetben.

Az Oracle checkout a felhasználó szerint main, HEAD
7ac0229c8384e55a23551b86f6d6db6002608b4b, helyi módosításokkal és nem követett fájlokkal.
A sudo-val kiolvasott élő Caddyfile a repóban lévő alappal egyezik.
Továbbra sincs ágváltás, pull vagy teljes konfigurációfelülírás.
A szolgáltatás telepítése, Caddy/Prometheus-bekötés, dashboard és a
valódi böngészős teljes adatút ellenőrzése hátravan.
