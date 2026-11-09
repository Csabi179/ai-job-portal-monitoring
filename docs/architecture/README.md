# MatchWise stack és adatáramlás

Az ábra a projekt dokumentált, 2026. november 10-i felépítését mutatja. A szolgáltatókon és a VM-en belüli dobozok a tényleges futtatási helyet jelölik; a szaggatott lila elemek tervezett integrációk.

![MatchWise teljes stack](matchwise-stack.svg)

- [Szerkeszthető draw.io / diagrams.net fájl](matchwise-stack.drawio)
- [Nagyítható SVG](matchwise-stack.svg)

## Szerkesztés

A diagrams.net oldalon válaszd a **File → Open From → Device** lehetőséget, és nyisd meg a `matchwise-stack.drawio` fájlt. A dobozok, a csoportok, a nyilak és a feliratok külön szerkeszthetők. A Docker-csoport az Oracle VM csoportjában található. A kép egyoldalas.

A Python-standardkönyvtárral működő `build_stack_diagram.py` közös geometriai leírásból előállítja a draw.io-fájlt és az SVG-t. A generált fájlok kézi szerkesztéseit a generátor újrafuttatása felülírja.

## Kapcsolatok és jelölések

| Jelölés | Jelentés |
|---|---|
| Kék | Alkalmazásoldali HTTPS / API-kapcsolat |
| Zöldeskék | Metrikák és automatikus HTTP-próbák |
| Aranybarna | Alkalmazásnaplók, JSONL és Loki |
| Piros | Grafana-riasztási értesítések |
| Szürke | Üzemeltetői hozzáférés és verziókövetési / telepítési kapcsolat |
| Szaggatott lila | Tervezett kapcsolat vagy szolgáltatás |
| Kéthegyű nyíl | Feliratozott kérés/válasz vagy lekérdezés/eredmény kapcsolat |

Az adatirányú nyíl nem mindig a hálózati kapcsolat kezdeményezőjét jelöli. A Prometheus lekéri az exporter- és Supabase-metrikákat; a Python collector lekéri a Render Logs API eseményeit. A Grafana lekérdezi a Prometheust és a Lokit. A feliratok ezeket a pull-kapcsolatokat külön megnevezik.

## Hol mi fut?

- **Vercel:** a React frontend, jelenlegi címe `https://www.matchwise.tech/`.
- **Render:** a csapat `job-portal-backend` repositoryjából telepített Node.js / Express backend, Pino HTTP-naplózással. A Render a stdout alkalmazásnaplókat a saját Logs API-ján keresztül teszi hozzáférhetővé.
- **Supabase:** kezelt PostgreSQL, Supabase Auth, PostgREST Data API és a projekt Metrics API-végpontja. Ezek szolgáltatási funkciók; az ábra nem állít külön saját konténert mindegyikhez.
- **Oracle VM / Docker Compose:** Prometheus, Grafana a beépített Grafana Alertinggal, Node Exporter, Blackbox Exporter, Loki, Grafana Alloy. A VM host hálózati módját használják, a monitoring webes végpontjai loopbackre kötöttek.
- **Oracle VM / systemd:** a Python Render-naplógyűjtő. A timer egy futás befejezése után körülbelül egy perccel indít új futást (`OnUnitInactiveSec=1min`, `AccuracySec=10s`).
- **Oracle VM / fájlok:** a collector deduplikált JSONL-kimenete, privát SQLite-állapota és időkurzora; a textfile metrikák és privát konfiguráció. A titkok nem kerülnek Gitbe.
- **Docker volume-ok:** a Prometheus, a Grafana, a Loki és az Alloy tartós adatai.
- **Telegram:** a konfigurált Grafana contact point Bot API-n keresztüli értesítési célja.
- **GitHub:** a backend forrása a Render számára, illetve a monitoring konfigurációinak és dokumentációjának verziókezelése. A VM frissítése a dokumentált `git pull` folyamattal történik. Az ábra nem állít automatikus VM-telepítést vagy ellenőrzött Render auto-deploy beállítást.

## Működő adatút és tervezett részek

1. A backend Supabase Authot és a Data API-t használja. A regisztráció, login, fiókelérés, logout és kijelentkezés utáni elutasítás közvetlen backendtesztje 2026. november 9-én sikeres volt.
2. A közzétett frontend 2026. november 9-i kódellenőrzésekor a login és a regisztráció még szimulált volt. A frontend → backend alkalmazáskapcsolat ezért tervezettként szerepel; ez egy dátumhoz kötött megfigyelés, nem élő integrációs teszt.
3. Az AI-szolgáltató és az asszisztens integrációjának részletei még nincsenek kijelölve. A backend → AI kapcsolat javasolt jövőbeli adatút; jelenleg nem igazolt működő szolgáltatás.
4. A Telegram-riasztási útvonal és kilenc szabály konfigurált. Az ábra önmagában nem bizonyít minden szabályhoz külön ellenőrzött éles kézbesítést.

## A fő adatfolyamok

- **Erőforrásmetrikák:** Linux → Node Exporter → Prometheus → Grafana.
- **Külső HTTP-próbák:** Blackbox Exporter → backend `/api/health` 30 percenként; Blackbox Exporter → frontend 60 másodpercenként. A Prometheus a próbametrikákat gyűjti.
- **Supabase-metrikák:** Metrics API → Prometheus, 60 másodpercenként, privát hitelesítéssel.
- **Backendnaplók:** Pino → Render Logs API → Python collector → JSONL → Alloy → Loki → Grafana. Az Alloy megőrzi az eredeti Render-esemény időbélyegét.
- **Collector heartbeat:** collector → `.prom` → Node Exporter textfile collector → Prometheus → Grafana.
- **Riasztás:** Grafana Alerting → Telegram Bot API → konfigurált chat.
- **Üzemeltetői felület:** böngésző → SSH-alagút → Grafana.

A ritka backend-HTTP-próbák nem jelentenek folyamatos elérhetőségi garanciát. A collector sikeres API-gyűjtése és a naplók Lokiba jutása külön állapot, ezért mindkettőhöz szerepel jelzés a dashboardon.

## Források és ellenőrzés

A repository `a39e5a5f86ca7de2c64d3afb57d4b3ebd1ddefe2` állapotából olvasott README, Alloy-konfiguráció és collector / timer, a helyi Compose- és Prometheus-konfiguráció, a backend 2026.11.09-i forrásmásolata és a felhasználó által bemutatott működő dashboard alapján készült. A megadott dátum dokumentációs pillanatfelvétel, nem teljes infrastruktúra-audit.

A generátor ellenőrzi az XML-ek feldolgozhatóságát, az egyedi azonosítókat, a csoportokon belüli elhelyezést és a merőleges nyílszakaszokat. Az SVG-ből készített PNG-előnézetet vizuálisan is ellenőriztük. A draw.io-fájlt natív diagrams.net szerkesztőben nem ellenőriztük.
