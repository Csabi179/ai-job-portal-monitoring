# Forgalmi összehasonlítás – aktuális állapot

Frissítve: 2026-11-19. Az első közös grafikonos változat tesztje és az ideiglenes teszt lezárása sikeres.

## Mi működik tartósan az Oracle-on?

- Python fogadó: 127.0.0.1:9121, külön systemd-szolgáltatás.
- HTTPS-fogadás a meglévő Caddy /matchwise-telemetry/v1 útvonalán.
- Prometheus frontend_traffic scrape: 60s/10s.
- 45 paneles Service Comparison dashboard, változatlan UID-val: matchwise-service-comparison.
- Közös frontend–backend forgalmi és latenciagrafikonok, valamint backend–Supabase aktivitási kontextus.
- A backend relatív és /api előtagos API-útvonalait is kezeli az összehasonlító szűrés; health kérések kizárva.
- A backend és Supabase korábbi adatgyűjtése megmaradt. Új riasztást nem adtunk hozzá.

## Mit igazolt a teszt?

Az Oracle-on futó frontend saját SSH-alagúton nyílt meg a felhasználó böngészőjében.
A külön tesztkonfiguráció Renderre továbbította az API-hívásokat.
A mérőkód 60 000 ms-os periódussal indult; ismételt 204-es fogadás látszott.
Egy pontosan 60 másodperces csomagban valódi auth POST és cv GET HTTP 200
események, számlálók és fejlécig mért időadatok jelentek meg.
A frontend adatainak böngésző -> Oracle -> Prometheus -> Grafana útja igazolt.
A backend API-ráta és P95, a Supabase committed transactions/s, a Render CPU
és a PostgREST pool waiting grafikonjai képpel igazoltak.

Ellenőrzések: 10 frontendteszt, 6 fogadóteszt, 3 konfigurációmegőrzési teszt,
lint és production build sikeres; 15 dashboard-lekérdezés Oracle-preflightja sikeres.
A frontend utolsó pusholt commitja e48661ef58be096bf1ff970368432ebd16e5e9ca,
[CI](https://github.com/ernoking/job-portal-frontend/actions/runs/44413623454) sikeres.
A Vercel branch-deploy státusza sikeres, de a védett preview-hoz a felhasználónak nincs hozzáférése.

## A teszt lezárása igazolt

A felhasználó visszaadta a cleanup kimenetét:
- receiver /health: ok;
- www.matchwise.tech Origin OPTIONS: 204;
- localhost:5173 Origin OPTIONS: 403;
- az Oracle 5173-as portjának ss-listája üres (csak fejléc).

Az ideiglenes localhost-engedély visszavonva, a Vite-porton nincs szerver.
A receiver restart nullázza a memóriabeli számlálókat és deduplikációt;
a korábbi Prometheus-minták megmaradnak.
A frontendgörbékben a teszt után elmaradó friss adat elvárt: a tesztfrontend leállt.
A fogadó szolgáltatás és a monitoring ettől tovább működik.

## Mi nincs még élesítve vagy igazolva?

**A www.matchwise.tech éles frontendjén az automatikus mérés nincs bekapcsolva.**
A forrásbeli trafficConfig.js enabled=false és üres endpoint értékű;
a teszt a Vite-folyamat környezeti változóival működött, amelyeket nem írtunk .env fájlba.
Az éles aktiváláshoz külön engedélyezett frontendkonfiguráció és éles deploy szükséges,
a projekt kezelőjével egyeztetve. Main merge egyik repóban sem történt.

Nincs automatikus összetett eltérésriasztás, DDoS-/terheléses igazolás vagy általános
rendellenesség-felismerési bizonyíték. Az új panelek Viewer-hozzáférése nincs külön igazolva.
A PostgREST queue mintavételezett kapcsolatkészlet-várakozás, nem teljes adatbázis-/lock-várakozás.
A DB-tranzakciók belső szolgáltatásokat és más klienseket is tartalmaznak.
A külön tengelyeken lévő görbék egyezése vagy eltérése önmagában nem ok-okozati bizonyíték.
A böngészős idők válaszfejlécig mérnek; P95 kosarakból becsült.
Hiányzó frontendadat nem nulla forgalom; a gyűjtési késés és az eltérő lefedettség számít.

## Verziózás és üzemeltetési korlát

- Monitoring: Csabi179/ai-job-portal-monitoring, feat/service-comparison.
- Frontend: ernoking/job-portal-frontend, feat/frontend-api-traffic.
- Kód és dokumentáció mindkét fejlesztési ágban verziózott.
- Oracle monitoring checkout: a felhasználó utolsó igazolása szerint main,
  7ac0229c8384e55a23551b86f6d6db6002608b4b, helyi módosításokkal.
  A telepítés fájlonkénti másolással történt: nincs pull/ágváltás.
  Későbbi frissítés előtt git status; helyi fájlokat nem dobunk el.
- A külön telepített Python-scriptek és systemd-fájlok nem frissülnek automatikusan Git-frissítéstől.

Részletes bizonyítékok és eljárások:
[frontend/fogadó](FRONTEND_TRAFFIC_RECEIVER.md),
[dashboard](SERVICE_COMPARISON_DASHBOARD.md),
[SSH-teszt](FRONTEND_SSH_TEST.md),
[Supabase](SUPABASE_METRICS.md).

## Éles forrás előkészítése – 2026-11-19

A felhasználó most külön engedélyezte a frontend feat/frontend-api-traffic -> main
összevonást. A monitoring feat/service-comparison ág továbbra sem vonható össze.
A kapcsolt GitHub-eszköz PR-létrehozására 403 érkezett, ezért az Oracle GitHub CLI-hez
készült rögzített SHA-kat, readiness-t és CI-t ellenőrző merge-segéd.
A script helyi Bash-szintaxisellenőrzése sikeres; a tényleges Oracle-futás,
PR-létrehozás és merge még nincs igazolva. Részletek:
[Production activation](FRONTEND_PRODUCTION_ACTIVATION.md).
A két Production-változó mellett új Production build szükséges;
a változók mentése önmagában nem írja át a már kiadott frontend JavaScriptjét.
