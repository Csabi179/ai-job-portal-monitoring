#!/usr/bin/env bash
# Run on the Oracle host as ubuntu. Does not switch branches or touch Prometheus.
set -Eeuo pipefail

repo=/home/ubuntu/ai-job-monitoring
source_ref=1060584f6f0e6e40769e3db4ed06f6d0ace3baaf
host=grafana-r0cecq.duckdns.org
cd "$repo"

fail() { printf '%s\n' "$*" >&2; exit 1; }
command -v python3 >/dev/null
command -v curl >/dev/null
# Check authorization per command without prompting; no blanket sudo -v.
sudo -n systemctl is-active --quiet matchwise-frontend-traffic.service
curl --noproxy '*' --max-time 5 -fsS http://127.0.0.1:9121/health

mount_path="$(sudo -n docker inspect monitoring-caddy --format '{{range .Mounts}}{{if eq .Destination "/etc/caddy"}}{{.Source}}{{end}}{{end}}')"
[[ "$mount_path" == "$repo/caddy" ]] || fail "Unexpected Caddy mount: $mount_path"
network="$(sudo -n docker inspect monitoring-caddy --format '{{.HostConfig.NetworkMode}}')"
[[ "$network" == host ]] || fail "Caddy must use host networking for this rollout."

mkdir -p /home/ubuntu/monitoring-backups
work="$(mktemp -d /home/ubuntu/monitoring-backups/frontend-traffic-caddy.XXXXXX)"
modified=false
successful=false
rollback() {
    status=$?
    trap - EXIT
    if [[ "$modified" == true && "$successful" != true ]]; then
        printf 'Restoring previous Caddyfile from %s\n' "$work/Caddyfile.before" >&2
        if sudo -n cp -- "$work/Caddyfile.before" caddy/Caddyfile; then
            sudo -n docker exec monitoring-caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile || true
        fi
        [[ "$status" -ne 0 ]] || status=1
    fi
    exit "$status"
}
trap rollback EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

git show "$source_ref:caddy/Caddyfile" > "$work/Caddyfile.expected"
git show "$source_ref:caddy/Caddyfile.frontend-traffic.example" > "$work/Caddyfile.candidate"
sudo -n cp -a -- caddy/Caddyfile "$work/Caddyfile.before"

# Preserve unknown edits. An already-enabled configuration is also safe to rerun.
if sudo -n cmp -s caddy/Caddyfile "$work/Caddyfile.candidate"; then
    printf 'Caddyfile already contains the intended route; validating again.\n'
else
    sudo -n cmp -s caddy/Caddyfile "$work/Caddyfile.expected" || fail \
        "Live Caddyfile differs from the reviewed baseline. Stopped; inspect $work."
fi

candidate="/tmp/matchwise-frontend-traffic-$(basename "$work").Caddyfile"
sudo -n docker cp "$work/Caddyfile.candidate" "monitoring-caddy:$candidate"
sudo -n docker exec monitoring-caddy caddy validate --config "$candidate" --adapter caddyfile

# Recheck after validation, before updating the mounted file.
sudo -n cmp -s caddy/Caddyfile "$work/Caddyfile.before" || fail 'Caddyfile changed during validation; stopped.'
modified=true
sudo -n cp -- "$work/Caddyfile.candidate" caddy/Caddyfile
sudo -n docker exec monitoring-caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile

# Test HTTPS locally with the real hostname and certificate, without DNS/hairpin dependencies.
base="https://$host"
https=(curl --noproxy '*' --resolve "$host:443:127.0.0.1" --max-time 10 -sS)
code="$("${https[@]}" -D "$work/preflight.headers" -o /dev/null -w '%{http_code}' \
    -X OPTIONS -H 'Origin: https://www.matchwise.tech' \
    -H 'Access-Control-Request-Method: POST' "$base/matchwise-telemetry/v1")"
[[ "$code" == 204 ]] || fail "Allowed-origin preflight returned $code; expected 204."
python3 - "$work/preflight.headers" <<'PY'
from email.parser import Parser
from pathlib import Path
import sys
raw = Path(sys.argv[1]).read_text()
headers = Parser().parsestr(raw.split('\n', 1)[1])
if headers.get('Access-Control-Allow-Origin') != 'https://www.matchwise.tech':
    raise SystemExit('Missing or incorrect CORS origin header')
PY

code="$("${https[@]}" -o /dev/null -w '%{http_code}' -X OPTIONS \
    -H 'Origin: https://not-allowed.example' "$base/matchwise-telemetry/v1")"
[[ "$code" == 403 ]] || fail "Disallowed-origin preflight returned $code; expected 403."

# Invalid JSON shape must reach the receiver, never count as business API traffic.
code="$("${https[@]}" -o /dev/null -w '%{http_code}' \
    -H 'Origin: https://www.matchwise.tech' -H 'Content-Type: text/plain' \
    --data-binary '{}' "$base/matchwise-telemetry/v1")"
[[ "$code" == 400 ]] || fail "Invalid-payload POST returned $code; expected 400."

"${https[@]}" -f "$base/api/health" > "$work/grafana-health.json"
python3 - "$work/grafana-health.json" <<'PY'
import json
from pathlib import Path
import sys
health = json.loads(Path(sys.argv[1]).read_text())
if health.get('database') != 'ok':
    raise SystemExit('Grafana health is not database=ok')
print('Grafana health: database=ok')
PY

successful=true
printf '\nPASS: HTTPS route; CORS 204/403; invalid POST 400; Grafana healthy.\n'
printf 'Backup and verification files: %s\n' "$work"
printf 'The invalid POST increases rejected_total by one; no business requests were added.\n'
printf 'Prometheus and frontend activation are still pending.\n'

