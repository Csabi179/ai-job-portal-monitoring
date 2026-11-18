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
3. IN PROGRESS: live API collection, .prom publication and Node Exporter ingestion verified. Service and two-minute timer implemented; installation and Prometheus verification pending.
4. TODO: Service Comparison dashboard with aligned time axes, same units for comparable data, explicit freshness and backend logs. Vercel CPU/memory shown as not collected.
5. TODO: backend CPU, backend 5xx and failed-login rules. Thresholds are initial examples, not measured service objectives. Exclude health traffic; require valid telemetry; document recovery and notification routing.
6. TODO: bilingual install/rollback instructions; update documentation index, monitoring and alerting plans; verify Viewer access to the new dashboard.
7. TODO: live Oracle rollout and controlled alert checks; record evidence separately from local tests. Review pull request before main integration.

## Current operator step / Jelenlegi felhasználói lépés

Follow [RENDER_METRICS_COLLECTOR.md](RENDER_METRICS_COLLECTOR.md) for the read-only collector test. Automatic collection is not installed yet.

A gyűjtő egyszeri próbájához kövesd a fenti leírást. Automatikus gyűjtés még nincs telepítve.

## Evidence / Ellenőrzés

2026-11-18 operator output: all four endpoints HTTP 200, one series and 61 samples each. Source timestamp 2026-11-18T15:12:00Z. CPU 0.0002448 / limit 0.15, both unit cpu. Memory 95039490 / limit 536870900, both bytes. Derived usage: CPU 0.1632% of limit, memory 17.7025% of limit.

Local tests: three test methods passed, including nine invalid-input subcases and atomic file replacement. These are synthetic tests; actual resource/instance label matching and source freshness still need the Oracle dry run. No new dashboard or alert is deployed.

Mind a négy végpont használható mintát és mértékegységet adott. A helyi tesztek sikeresek, de az éles gyűjtőpróba még hátravan. Új dashboard és riasztás még nincs telepítve.
