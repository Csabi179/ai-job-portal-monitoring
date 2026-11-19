# Dashboard visual audit — 2026-11-19

> **Current deployment — 2026-11-19:** The operator confirmed all supplied changes were already applied on Oracle. Monitoring was merged into `main` (`10f43d1`); no reinstallation is required because of that merge. [Current status](DEPLOYMENT_STATUS.md). Earlier rollout entries are historical; commands are retained for future updates or recovery.

The English Unified Monitoring and Service Comparison dashboards were inspected in an authenticated Chromium session at 1600×1050 with the Grafana navigation open. The inspection included overview/KPI sections, graphs, routes and endpoint table, database/Oracle details, security/collection health and frontend details. Candidate display changes were tested in the actual Grafana renderer by substituting read responses in an isolated browser. This preview does not save production dashboards; rollout uses the pinned Oracle installer.

Observed problems and corrections:

- Repeated service prefixes and long scope labels truncated many KPI titles. Service-section tiles now use concise titles; the comparison scorecard retains service names in the first column. Full original titles and measurement scope remain in descriptions.
- Availability history displayed threshold brackets (`< 1`, `1+`) rather than meaningful status names. It now uses its UP/DOWN value mappings. See [Grafana state-timeline legend configuration](https://grafana.com/docs/grafana/latest/visualizations/panels-visualizations/visualizations/state-timeline/).
- Bottom table legends hid the fourth service or HTTP status behind an internal scrollbar. Two-to-four-target graphs use wrapping list legends, retaining latest sample values.
- The frontend interpretation panel clipped its final paragraph. Its row now has more vertical space.
- The endpoint table's `P95 (ms)` heading conflicted with Grafana formatting values above one second as seconds. The heading is now `P95`; each value retains its displayed unit.
- A transient negative Supabase CPU percentage was observed. Its cause is not established by visual inspection. Percentage values outside 0–100 are marked `Invalid sample` / `Hibás minta`, not silently clamped to zero. This display guard does not repair the upstream metric or change any query.

Missing or idle traffic remains distinct from a measured zero; `n/a` remains for signals that are not collected. Metric expressions, datasource identities, query modes, variable defaults, dashboard UIDs and HU/EN visible names are unchanged. The installer accepts the previous service-grouped revision `8433198c9ce09e328fa51044e4bf186303e3eee7` without rerunning the earlier bilingual preparation.

Local checks: eight dashboard tests, twelve Grafana-storage regression tests, Bash syntax, and comparison of every panel's measurement configuration against the previous four models. No authentication material belongs in source files, documentation, screenshots, browser-state exports or the repository.
