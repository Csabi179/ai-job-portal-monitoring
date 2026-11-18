# Service comparison implementation / Megvalósítási terv

Started / Kezdés: 2026-11-18.
Baseline: c12e4041776545428717647ad3947efe22036e0e.
Branch: feat/service-comparison.

## Scope / Cél

Simple side-by-side backend, Supabase, frontend and Oracle panels. Reuse existing Prometheus, Loki, Node Exporter and Grafana. Add Render CPU/memory collection only after API access and response semantics are verified. Missing metrics must not appear as zero. All labels and dashboards are English; operational instructions are provided in Hungarian and English.

Egyszerű összehasonlító dashboard a meglévő rendszerre építve. A Render CPU/memória gyűjtése API-ellenőrzés után készül el. A hiányzó mérés nem nulla. A szolgáltatások eltérő erőforráshasználata önmagában nem támadás.

## Steps / Lépések

1. DONE: baseline and branch created; implementation plan versioned.
2. DONE: operator confirmed four nonempty API responses and units (cpu / bytes) on November 18.
3. DONE: collector, textfile ingestion, systemd timer and Prometheus ingestion verified by operator.
4. IN PROGRESS: operator screenshots confirm dashboard rendering and visible data; Viewer access check pending.
5. IN PROGRESS: three guarded rules implemented (CPU >80% for 5m, >=5 5xx/5m for 2m, >=10 login401/5m for 2m). Structure checked; live queries, provisioning and notification tests pending.
6. TODO: bilingual install/rollback instructions; update documentation index, monitoring and alerting plans; verify Viewer access to the new dashboard.
7. TODO: live Oracle rollout and controlled alert checks; record evidence separately from local tests. Review pull request before main integration.

## Current operator step / Jelenlegi felhasználói lépés

Run the read-only preflight in [SERVICE_COMPARISON_ALERTS.md](SERVICE_COMPARISON_ALERTS.md). Rules are versioned but not installed on Oracle. / Futtasd a csak olvasó lekérdezéspróbát; a szabályok még nincsenek telepítve az Oracle gépen.

## Evidence / Ellenőrzés

2026-11-18: operator confirmed Render API access/units, successful collector calculation, atomic .prom publication, Node Exporter ingestion, active timer and Prometheus collection_success=1. Screenshots confirm the comparison dashboard renders with resource data, status panels, log context and explicit Vercel resource gaps. Viewer access remains unverified.

Collector: four local test methods passed. Dashboard structure checks passed. Three new alert rule structures and references checked; actual PromQL/LogQL, Grafana expressions and delivery still require live verification. Existing promtool suite not rerun here (tools unavailable).

A gyűjtés és a dashboard éles működése a felhasználó kimenetével és képeivel igazolt. Viewer hozzáférés és az új riasztások éles működése még nincs ellenőrizve. A fő ág változatlan; a munka a fejlesztési ágon található.
