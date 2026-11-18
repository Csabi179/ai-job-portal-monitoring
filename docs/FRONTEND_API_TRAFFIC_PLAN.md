# Frontend API-forgalom mérése – megvalósítási terv

Dátum: 2026-11-18.
Állapot: TERV; nincs implementálva, telepítve vagy élesben tesztelve.
Monitoringág: feat/service-comparison. Main összevonás nincs.

## Ellenőrzött kiindulás

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
- Böngészőben mért idő összege és elemszáma; kezdetben átlag,
  percentilisek és hisztogram nélkül.
- Fogadott jelentések száma, utolsó sikeres fogadás ideje,
  a fogadó működését jelző saját állapot.

A mérés pontos időhatárát implementálás előtt rögzíteni kell:
a fetch válaszfejlécig tartó ideje és a törzs beolvasásáig tartó idő
különböző fogalmak. A fetch-hiba nem bizonyít backendhibát;
hálózati hiba vagy megszakítás is lehet.

Felhasználói követelmény: az összesítések időzített küldése 60 másodpercenként
(1 perc) történjen, böngészőlaponként. Nincs külön háttérbe kerüléskor
indított küldés. A böngésző háttérben késleltetheti az időzítőt;
ez nem garantált, pontos falióra szerinti percenkénti kézbesítés.
A küldés nem blokkolhatja az üzleti kéréseket.
Nincs korlátlan sor vagy korlátlan újrapróbálkozás.
Ha van újraküldés, batchazonosítóval és korlátozott idejű
duplikációszűréssel kell elkerülni a dupla számlálást.

Első körben nincs útvonal-, felhasználó- vagy sessioncímke,
nincs query string, token, kérés-/választörzs vagy IP-cím naplózása.
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
