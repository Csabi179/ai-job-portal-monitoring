# Frontend API count and resource visibility

> **Aktuális telepítési állapot — 2026-11-19:** Az üzemeltető minden átadott módosítást már alkalmazott az Oracle-on. A monitoringág bekerült a `main` ágba (`10f43d1`); emiatt nincs újratelepítési feladat. [Aktuális állapot](DEPLOYMENT_STATUS.md). A korábbi bevezetési bejegyzések történeti állapotok; a parancsok későbbi frissítéshez vagy helyreállításhoz maradnak meg.

The Unified Monitoring `API calls` / `API-hívások` card now shows the estimated number of real browser API starts in the selected dashboard time range. It is an instant query at the selected range end:

```promql
sum(increase(frontend_api_requests_started_total{job="frontend_traffic",mode="real"}[$__range]))
```

The value uses `calls` / `hívás`, rounded to a whole number, rather than `calls/min`. A past window remains queryable even when the receiver or reporting browser is currently inactive; no current `up` or last-packet freshness condition hides historical counts. Missing observations remain `No data`, not an invented zero. Existing traffic graphs and the comparison scorecard retain explicitly labelled per-minute rates.

This is a sampled estimate, not an exact event ledger. [Prometheus increase](https://prometheus.io/docs/prometheus/latest/querying/functions/#increase) accounts for counter resets and extrapolates to window boundaries. Minute-batched browser data is assigned to receipt/scrape time, and a new series may begin above zero before its first stored sample. The first such observations cannot be reconstructed retrospectively. Short windows, partial minutes and missing scrapes can therefore affect the estimated total. No collector or frontend code is changed by this dashboard update.

Both dashboard introductions explain that host CPU and memory data for the deployed static Vercel frontend are unavailable to this monitoring system. Browser telemetry cannot measure Vercel host resources. Vercel documents [CPU/memory observability for Functions](https://vercel.com/docs/observability/insights), a different runtime from the static frontend used here. This change does not claim that Vercel has no compute metrics for any deployment.

Frontend CPU/memory placeholder cards are removed in HU and EN. In Unified Monitoring the remaining four frontend health cards fill the row. In Service Comparison all four services retain the same four common scorecard columns; collected backend/database/Oracle CPU and memory cards move together into the Load section. Their measurements and panel IDs are retained. The existing Oracle application-traffic `n/a` cards are unrelated and remain in place.

The guarded installer accepts both the original service-grouped release (`8433198c9ce09e328fa51044e4bf186303e3eee7`) and the visual-audit release (`5ca71a7a0c3d46209e87bdb3e18d467b6904125e`), as well as the earlier bilingual baseline. It backs up the four current models and prints rollback instructions.

## Magyar

A Unified `API-hívások` kártyája a kiválasztott időablak becsült összes hívását mutatja. A történeti összesítést nem rejti el az, ha a böngésző vagy a fogadó jelenleg inaktív. A percenkénti csomagküldés és mintavétel miatt a szám becslés; a korábbi, még nem tárolt első számlálóértékek utólag nem pótolhatók. Hiányzó mintánál nem jelenítünk meg hamis nullát.

A frontend host CPU-/memóriakártyáit mindkét dashboard mindkét nyelvi változatából eltávolítottuk. A hiányzó host-adatforrást a fejléc magyarázza. A backend, az adatbázis és az Oracle tényleges erőforrásadatai megmaradnak; az összehasonlító nézetben a Terhelés szekcióba kerülnek.
