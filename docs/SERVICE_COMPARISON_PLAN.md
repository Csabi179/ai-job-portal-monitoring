# Service comparison implementation / Megvalósítási terv

Started / Kezdés: 2026-11-18.
Baseline: c12e4041776545428717647ad3947efe22036e0e.
Branch: feat/service-comparison.

## Scope / Cél

Simple side-by-side backend, Supabase, frontend and Oracle panels. Reuse existing Prometheus, Loki, Node Exporter and Grafana. Add Render CPU/memory collection only after API access and response semantics are verified. Missing metrics must not appear as zero. All labels and dashboards are English; operational instructions are provided in Hungarian and English.

Egyszerű összehasonlító dashboard a meglévő rendszerre építve. A Render CPU/memória gyűjtése API-ellenőrzés után készül el. A hiányzó mérés nem nulla. A szolgáltatások eltérő erőforráshasználata önmagában nem támadás.

## Steps / Lépések

1. DONE: baseline and branch created; implementation plan versioned.
2. IN PROGRESS: read-only Render metrics API probe. CPU, memory and capacity limits; verify account access and actual payload. Operator verified HTTP 200 and nonempty samples for all four endpoints on November 18. Unit verification pending.
3. TODO: Python metrics collector, atomic textfile output, source timestamp and collection health, systemd timer; tests for errors/stale data.
4. TODO: Service Comparison dashboard with aligned time axes, same units for comparable data, explicit freshness and backend logs. Vercel CPU/memory shown as not collected.
5. TODO: backend CPU, backend 5xx and failed-login rules. Thresholds are initial examples, not measured service objectives. Exclude health traffic; require valid telemetry; document recovery and notification routing.
6. TODO: bilingual install/rollback instructions; update documentation index, monitoring and alerting plans; verify Viewer access to the new dashboard.
7. TODO: live Oracle rollout and controlled alert checks; record evidence separately from local tests. Review pull request before main integration.

## Current operator step / Jelenlegi felhasználói lépés

Run the read-only API probe described in scripts/probe-render-metrics.py on Oracle. It asks for the service ID and a hidden API key, makes GET requests only, and prints schema information plus numeric samples. It does not save credentials or alter services. Share only its summary output.

Futtasd a scripts/probe-render-metrics.py ellenőrzőt az Oracle gépen. A szolgáltatásazonosítót és az API-kulcsot helyben kéri be; a kulcs beírása rejtett. Csak olvasási kéréseket küld, szolgáltatást nem módosít. Csak az összefoglaló kimenetet küldd vissza.

## Evidence / Ellenőrzés

Official API references checked: https://api-docs.render.com/reference/get-cpu and https://api-docs.render.com/reference/get-memory. Operator output confirms access and the list/labels/unit/values response structure. Units remain unverified because the initial probe hid unit strings. No CPU percentage formula or live alert is deployed in this phase.

Az API-leírás ellenőrzött; a saját fiók hozzáférése és a válasz szerkezete a felhasználó kimenetével igazolt. A mértékegységek ellenőrzéséhez a javított program egyszeri újrafuttatása szükséges. Ebben a fázisban nem telepítünk új riasztást.

## API probe evidence 2026-11-18 / API-ellenőrzés

Operator supplied four HTTP 200 responses, each containing one series and 61 samples. Latest reported sample time: 2026-11-18T15:08:00Z. Raw values: CPU 0.00028793333; CPU limit 0.15; memory 95039490; memory limit 536870900. These are raw API numbers, not yet validated units or derived percentages. No credentials recorded. The revised probe preserves unit names and label field names while hiding identifier values. Local unit-visibility and redaction checks passed; revised live output pending.

Mind a négy API-lekérés sikeres: egy-egy idősor, 61 mintával. A számok nyers API-értékek, a mértékegységet még ellenőrizzük. A javított program helyi ellenőrzése sikeres. Következő lépés: egyszeri újrafuttatás, utána a metrikagyűjtő megírása.
