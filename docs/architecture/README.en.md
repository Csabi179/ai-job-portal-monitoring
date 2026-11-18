# MatchWise stack and data flow

**Diagram version:** the draw.io/SVG below shows the earlier twelve-rule baseline. November 18 added a separate Render Metrics API → Python → .prom → Node Exporter flow, a comparison dashboard and three rules; the current permanent count is fifteen. The diagram was not redrawn in this documentation update. See [current implementation status](../SERVICE_COMPARISON_PLAN.md).

[Magyar változat](README.md) · [Documentation index](../README.md)

The editable diagram describes the current monitoring configuration and operator-confirmed deployment. AI integration and frontend-to-backend browser behavior are labelled separately where deployment or end-to-end verification is not established.

![MatchWise stack and data flow, Hungarian labels](matchwise-stack.svg)

- [Editable draw.io file](matchwise-stack.drawio)
- [Zoomable SVG](matchwise-stack.svg)

## Components and deployment locations

- **Vercel:** React frontend at https://www.matchwise.tech/.
- **Render:** team Node.js/Express backend and Pino stdout logs exposed through Render Logs API. Main auto-deployment was reported by the operator; a precise deployed commit requires separate checking.
- **Supabase:** managed PostgreSQL, Auth, PostgREST and Metrics API.
- **Cloudinary:** CV file storage in the November 15 backend source archives; account configuration is separate from Oracle monitoring.
- **Cloudflare Workers AI:** gpt-oss-20b profile extraction in the supplied feature branch; variables preconfigured on Render, merge/deployment not verified.
- **Oracle Docker Compose:** six base monitoring services (Prometheus, Grafana, Node Exporter, Blackbox Exporter, Loki, Alloy), plus Caddy in the public profile.
- **Oracle systemd/files:** collector and rotation timers; deduplicated JSONL, private SQLite/cursor, heartbeat textfile and secrets outside Git.
- **Persistent volumes:** Prometheus, Grafana, Loki, Alloy and Caddy certificate/runtime state.
- **Telegram:** English notifications to the team group, selected through private environment settings.
- **GitHub:** source/version history; monitoring changes reach Oracle through git pull and service-specific application.

## Main flows

1. Linux → Node Exporter → Prometheus → Grafana.
2. Blackbox probes backend /api/health every 30 minutes, frontend and local Loki/Alloy health every 60 seconds; Prometheus stores results.
3. Supabase Metrics API → Prometheus every 60 seconds.
4. Pino → Render Logs API → Python collector → JSONL → Alloy → Loki → Grafana.
5. Collector success → heartbeat textfile → Node Exporter → Prometheus → Grafana Alerting.
6. Grafana Alerting → Telegram Bot API → team group; 12 rules, collector and Node Exporter individually evidenced.
7. Team browser → HTTPS Caddy → local Grafana login and Viewer permissions; no SSH access is granted.
8. Feature-branch CV flow: backend → Cloudinary download → text extraction → Cloudflare AI → Supabase profile save; production state remains unverified.

## Access and interpretation

Only Caddy TCP 80/443 is published for web access. Grafana 3000 and monitoring management endpoints remain on loopback. Caddy's admin API is 127.0.0.1:2019. Users and ACLs live in the Grafana database, not dashboard JSON. Viewer dashboard visibility is not datasource-level isolation.

Blue denotes application APIs, teal metrics, gold logs, red notifications, grey access/versioning, and dashed purple an unverified/future integration. Arrows represent labelled data or request/response flow; Prometheus and the collector initiate pulls. The diagram no longer describes nine active rules or SSH-only Grafana access. The frontend integration label is a verification boundary, not a claim that current authentication is simulated.

A successful health check is not a full business test. Collector success, Loki health and actual event delivery differ. The current 15 rules do not independently cover the entire public Caddy/DNS/TLS path or complete VM failure. See the [monitoring plan](../monitoring-plan.en.md) and [test log](../monitoring-tests.md).

## Editing and validation

Open matchwise-stack.drawio in diagrams.net using File → Open From → Device. The Python-standard-library generator build_stack_diagram.py produces both editable XML and SVG; rerunning it overwrites manual generated-file edits.

The November 16 refresh retains the original layout and updates rule count, Caddy/team access, Telegram destination and the identified feature-branch dependencies. Generator checks cover XML parsing, unique IDs, containment and orthogonal paths. These checks are separate from native diagrams.net editing and live deployment verification.

The regenerated SVG was rendered to PNG and visually inspected during this refresh. Native diagrams.net editing and a new live infrastructure audit were not performed.
