# Grafana HTTPS access for the team

[Magyar változat](GRAFANA_HTTPS_ACCESS.md) · [Documentation index](README.md)

Reviewed **November 16, 2026**. Public URL: **https://grafana-r0cecq.duckdns.org/**. The operator supplied successful Caddy certificate acquisition and Grafana HTTPS health output, confirmed external browser login, then confirmed Viewer access after restricting dashboard permissions. See [TEST-14](monitoring-tests.md#test-14-https-viewer-access).

The current team access uses a shared Viewer account, not individual teammate accounts. It grants dashboard access only to Unified Monitoring, with no Grafana Admin, Oracle account, SSH key or shell access. The procedure below documents setup/recovery; it is not a pending rollout or an instruction to repeat completed firewall changes.

## Architecture

Browser → HTTPS TCP 443 → Caddy → HTTP 127.0.0.1:3000 → Grafana.

The official ARM64-capable `caddy:2.11.9-alpine` image is an opt-in Compose **public** profile. The default six monitoring services remain active without Caddy. Persistent caddy_data/caddy_config volumes preserve certificate/runtime state. Caddy's admin API binds only to 127.0.0.1:2019. There are no proxy routes for Prometheus, Loki or exporters. Grafana endpoints still enforce Grafana authentication and permissions.

Pulling this commit does not open firewall ports, start Caddy or modify private .env values. Without the three new environment settings, Grafana retains its previous local HTTP defaults.

## 1 Prechecks and update

On the Oracle VM:

```bash
cd ~/ai-job-monitoring
git status --short
# Continue only with a reviewed working tree; preserve known untracked exports.
PREVIOUS_HTTPS_COMMIT=$(git rev-parse HEAD)
git pull --ff-only
sudo docker compose config --quiet

getent ahostsv4 grafana-r0cecq.duckdns.org
sudo ss -ltnp '( sport = :80 or sport = :443 )'
sudo iptables -L INPUT -n -v --line-numbers
sudo systemctl is-active netfilter-persistent
sudo systemctl list-timers --all | grep -Ei 'certbot|acme|caddy' || true
```

The name must resolve to the actual Oracle public IP. If an IPv6 AAAA record exists, separately verify that it points to a reachable correct destination. Preserve the existing matchwise-logs-r0cecq.duckdns.org record and TLS files. If an older certbot/ACME timer requires standalone port 80, coordinate renewal with Caddy; do not blindly disable it.

## 2 Validate Caddy and configure private Grafana settings

```bash
sudo docker compose --profile public pull caddy
sudo docker compose --profile public run --rm --no-deps --entrypoint caddy caddy \
  validate --config /etc/caddy/Caddyfile --adapter caddyfile

mkdir -p "$HOME/monitoring-private-backups"
GRAFANA_ENV_BACKUP="$HOME/monitoring-private-backups/grafana-env-before-https-$(date -u +%Y%m%dT%H%M%SZ)"
(umask 077; cp .env "$GRAFANA_ENV_BACKUP")
printf 'Private env backup: %s\n' "$GRAFANA_ENV_BACKUP"
nano .env
```

Set these three values once in .env while preserving all other settings:

```dotenv
GRAFANA_PUBLIC_DOMAIN=grafana-r0cecq.duckdns.org
GRAFANA_PUBLIC_URL=https://grafana-r0cecq.duckdns.org/
GRAFANA_COOKIE_SECURE=true
```

Do not paste the entire .env into chat or Git. Administrator password and Telegram credentials stay unchanged. Future normal Grafana recreations read the same public URL and secure-cookie setting from this file.

```bash
chmod 600 .env
sudo docker compose --profile public config --quiet
```

Secure cookies mean normal browser login should use the HTTPS URL; a plain HTTP localhost SSH tunnel cannot carry the login cookie correctly. The SSH shell and local health requests remain available.

## 3 Oracle Cloud ingress

In an NSG attached to the correct VM VNIC, or the subnet's applicable Security List, add two **stateful ingress** rules:

| Source | Protocol | Source port | Destination port | Description |
|---|---|---|---|---|
| 0.0.0.0/0 | TCP | All | 80 | Caddy HTTP redirect and certificate validation |
| 0.0.0.0/0 | TCP | All | 443 | Grafana HTTPS through Caddy |

Add rules to the applicable network control; do not automatically duplicate them into every NSG and Security List. Preserve SSH and other necessary rules. Do not expose 3000, 9090, 9100, 9115, 3100, 12345 or 2019. UDP 443 is not required for this basic HTTP/1.1 and HTTP/2 access.

## 4 Ubuntu INPUT rules

These commands match the operator's observed INPUT ordering: rules 1–4 remain, and new ACCEPT rules are inserted at position 5 before REJECT. If ordering has changed, inspect it first rather than reusing the numeric position blindly.

```bash
GRAFANA_FIREWALL_BACKUP="$HOME/monitoring-private-backups/firewall-before-grafana-$(date -u +%Y%m%dT%H%M%SZ).v4"
(umask 077; sudo iptables-save > "$GRAFANA_FIREWALL_BACKUP")
printf 'Firewall backup: %s\n' "$GRAFANA_FIREWALL_BACKUP"

sudo iptables -C INPUT -p tcp --dport 80 -m conntrack --ctstate NEW -j ACCEPT ||
  sudo iptables -I INPUT 5 -p tcp --dport 80 -m conntrack --ctstate NEW -j ACCEPT

sudo iptables -C INPUT -p tcp --dport 443 -m conntrack --ctstate NEW -j ACCEPT ||
  sudo iptables -I INPUT 5 -p tcp --dport 443 -m conntrack --ctstate NEW -j ACCEPT

sudo iptables -L INPUT -n -v --line-numbers
sudo netfilter-persistent save
```

The SSH ACCEPT on port 22 remains. Do not flush chains, change policies or replace the entire ruleset. Host-network Caddy traffic passes through INPUT; there is no Docker port publishing here.

## 5 Start the two affected services

```bash
sudo docker compose --profile public up -d --no-deps --force-recreate grafana caddy
sudo docker compose --profile public ps grafana caddy
sudo docker compose --profile public logs --since=10m --tail=150 caddy grafana
```

Grafana briefly restarts. Other monitoring containers and the collector are not restarted by this command. Anonymous access and self-registration remain disabled. Caddy begins certificate acquisition, which requires correct DNS, host firewall and OCI rules. Do not delete its certificate volume during routine maintenance.

## 6 Verify and configure team accounts

```bash
curl -fsS http://127.0.0.1:3000/api/health
curl -I http://grafana-r0cecq.duckdns.org/
curl -fsS https://grafana-r0cecq.duckdns.org/api/health
curl -I https://grafana-r0cecq.duckdns.org/login
sudo ss -ltnp '( sport = :80 or sport = :443 or sport = :3000 or sport = :2019 )'
```

Expect successful local/HTTPS Grafana health, HTTP redirection to HTTPS, login HTTP 200, and loopback-only listeners for 3000/2019. Also open the URL from outside the Oracle VM: a request to the VM's own public address is not sufficient proof of external access. Do not use curl -k as final TLS validation.

For future per-person access, create individual password-based Viewer accounts. Configure the selected folder/dashboard permissions and inherited Viewer grants separately: HTTPS alone does not limit users to one dashboard. Basic Viewer datasource-query rights do not enforce per-panel data isolation either. Do not share the administrator account or an SSH key. Log in as a Viewer to verify intended dashboard visibility, inability to edit, and Grafana Live behavior.

### Current folder and dashboard permissions

- In **AI Job Portal → Manage permissions**, remove the folder-wide **Viewer → View** grant; keep Admin and the intended Editor grant.
- On **MatchWise | Unified Monitoring → Settings → Permissions**, retain its direct **Viewer → View** grant.
- Remove direct Viewer grants from **Application Availability**, **Infrastructure Overview** and **Backend Logs**. A higher inherited permission cannot be denied on a child dashboard.
- The current team account has organization role **Viewer**, with **Grafana Admin: No**. Individual accounts can be introduced later.
- Permission changes are separate from saving dashboard content. The top dashboard Save can be blocked by file provisioning; reload the permissions page to verify the ACL change persisted instead of exporting or duplicating the dashboard.
- Users and ACLs persist in **grafana_data**, not in the provisioned dashboard JSON. Recheck/restore them after a fresh deployment or database restore.
- Test from a separate Viewer session: Unified Monitoring loads, the other dashboards are denied even by direct URL, and editing is unavailable. Dashboard visibility does not restrict Viewer queries to the displayed panels' datasource data.

## Troubleshooting and rollback

- HTTPS timeout: DNS, OCI ingress, INPUT rule order and Caddy state.
- Certificate errors: A/AAAA destination, port 80/443 reachability, Caddy logs and possible previous ACME rate limits; avoid repeated restarts.
- HTTP 502: Grafana's 127.0.0.1:3000 endpoint and container health.
- Wrong redirects/login: the three .env values, final HTTPS URL and browser cookies; the domain must match the Caddyfile.
- The existing 12 rules observe local components and external applications; they do not separately prove the complete public Caddy/DNS/certificate path.

For rollback, stop Caddy and reset the three public .env settings:

```bash
sudo docker compose --profile public stop caddy
nano .env
```

```dotenv
GRAFANA_PUBLIC_DOMAIN=localhost
GRAFANA_PUBLIC_URL=http://localhost:3000/
GRAFANA_COOKIE_SECURE=false
```

```bash
sudo docker compose config --quiet
sudo docker compose up -d --no-deps --force-recreate grafana
curl -fsS http://127.0.0.1:3000/api/health
```

Remove only the following exact firewall rules added by this rollout, and only if they did not exist previously:

```bash
sudo iptables -D INPUT -p tcp --dport 80 -m conntrack --ctstate NEW -j ACCEPT
sudo iptables -D INPUT -p tcp --dport 443 -m conntrack --ctstate NEW -j ACCEPT
sudo netfilter-persistent save
```

Withdraw only the two newly added OCI ingress rules as well. Do not blindly restore a full old iptables dump while Docker is running. Preserve Caddy/Grafana volumes and collector state. Review any private env backup before restoring it so later credential changes are not lost.

## Verification status and references

Local checks validated the six-service default, public profile and Caddyfile. Operator output additionally confirmed DNS, OCI TCP 80/443 rules, host ACCEPT rules before REJECT, Caddy/Grafana startup, successful certificate acquisition and HTTPS health. The operator confirmed external browser login and Viewer operation. Firewall persistence after reboot, Grafana Live-specific behavior and a complete recovery were not separately evidenced. See TEST-14.

- [Caddy HTTPS](https://caddyserver.com/docs/automatic-https)
- [Caddy reverse proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)
- [Grafana reverse proxy](https://grafana.com/tutorials/run-grafana-behind-a-proxy/)
- [Oracle security rules](https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/securityrules.htm)
