#!/usr/bin/env bash
# Upgrade receiver and one provisioned dashboard; preserve service/Caddy/Prometheus settings.
set -Eeuo pipefail
export LC_ALL=C.UTF-8
repo=/home/ubuntu/ai-job-monitoring
cd "$repo"
ref="${1:?Usage: bash install-frontend-details.sh COMMIT_SHA}"
[[ "$ref" =~ ^[0-9a-f]{40}$ ]] || { printf 'Expected full commit SHA.\n' >&2; exit 2; }
baseline_ref=829ccc54ffaadeb6c1191c11db4839342df17a01
dashboard=grafana/provisioning/dashboards/json/matchwise-service-comparison.json
installed_receiver=/usr/local/lib/matchwise/frontend-traffic-receiver.py
service=matchwise-frontend-traffic.service
stage=$(mktemp -d /tmp/matchwise-frontend-details.XXXXXX)
backup=
rollback_needed=0
finish() {
  result=$?
  trap - EXIT
  if [[ "$rollback_needed" == 1 ]]; then
    printf '\nUpgrade failed; restoring receiver and dashboard from %s\n' "$backup" >&2
    sudo -n install -o root -g root -m 0644 "$backup/receiver.before.py" "$installed_receiver" || result=1
    cp -- "$backup/dashboard.before.json" "$dashboard" || result=1
    sudo -n systemctl restart "$service" || result=1
  fi
  rm -rf -- "$stage"
  exit "$result"
}
trap finish EXIT
for name in frontend-traffic-receiver.py test_frontend_traffic_receiver.py frontend-traffic-v1.json check-frontend-comparison-queries.py validate-dashboard-redesign.py; do
  git show "$ref:scripts/$name" > "$stage/$name"
done
git show "$ref:$dashboard" > "$stage/candidate.json"
git show "$baseline_ref:$dashboard" > "$stage/baseline.json"
git show "$baseline_ref:scripts/frontend-traffic-receiver.py" > "$stage/receiver.baseline.py"
python3 "$stage/validate-dashboard-redesign.py" "$stage/candidate.json" "$stage/baseline.json"
python3 - "$dashboard" "$stage/baseline.json" "$stage/candidate.json" "$installed_receiver" "$stage/receiver.baseline.py" "$stage/frontend-traffic-receiver.py" <<'PY'
import json, sys
from pathlib import Path
live, baseline, candidate = (json.loads(Path(p).read_text(encoding='utf-8')) for p in sys.argv[1:4])
if live not in (baseline, candidate):
    raise SystemExit('STOP: unknown live dashboard changes; preserve and review them.')
receiver, old, new = (Path(p).read_text(encoding='utf-8') for p in sys.argv[4:7])
if receiver not in (old, new):
    raise SystemExit('STOP: unknown live receiver changes; preserve and review them.')
print('Live files match reviewed versions.')
PY
FRONTEND_TRAFFIC_ORIGINS=https://www.matchwise.tech python3 "$stage/test_frontend_traffic_receiver.py" -v
sudo -n systemctl is-active --quiet "$service"
command_line=$(sudo -n systemctl show "$service" -p ExecStart --value)
[[ "$command_line" == *"$installed_receiver"* ]] || { printf 'Unexpected service executable; stop.\n' >&2; exit 1; }
python3 "$stage/check-frontend-comparison-queries.py" "$stage/candidate.json" --overview
python3 "$stage/check-frontend-comparison-queries.py" "$stage/candidate.json" --frontend-details
curl --max-time 10 -fsS http://127.0.0.1:3000/api/health | python3 -c 'import json,sys; assert json.load(sys.stdin).get("database")=="ok"'
mkdir -p /home/ubuntu/monitoring-backups
backup=$(mktemp -d /home/ubuntu/monitoring-backups/frontend-details.XXXXXX)
cp -p -- "$installed_receiver" "$backup/receiver.before.py"
cp -p -- "$dashboard" "$backup/dashboard.before.json"
printf 'Backup: %s\n' "$backup"
rollback_needed=1
sudo -n install -o root -g root -m 0644 "$stage/frontend-traffic-receiver.py" "$installed_receiver"
sudo -n systemctl restart "$service"
for attempt in {1..10}; do
  if curl --max-time 3 -fsS http://127.0.0.1:9121/metrics > "$stage/metrics.txt"; then
    if python3 - "$stage/metrics.txt" <<'PY'
import sys
from pathlib import Path
assert 'frontend_telemetry_receiver_schema_version 2' in Path(sys.argv[1]).read_text()
PY
    then break; fi
  fi
  sleep 1
done
python3 - "$stage/metrics.txt" <<'PY'
import sys
from pathlib import Path
assert 'frontend_telemetry_receiver_schema_version 2' in Path(sys.argv[1]).read_text()
PY
printf 'Waiting up to 90 seconds for Prometheus to scrape receiver version 2...\n'
python3 - <<'PY'
import json, time
from urllib.parse import urlencode
from urllib.request import ProxyHandler, build_opener
opener = build_opener(ProxyHandler({}))
deadline = time.monotonic() + 90
expr = '(min(frontend_telemetry_receiver_schema_version{job="frontend_traffic"}) == 2) and on() (min(up{job="frontend_traffic"}) == 1)'
while time.monotonic() < deadline:
    try:
        with opener.open('http://127.0.0.1:9090/api/v1/query?' + urlencode({'query':expr}), timeout=5) as r:
            data=json.load(r)
        if data.get('status')=='success' and data['data']['result']:
            print('PASS: Prometheus sees receiver version 2.'); break
    except (OSError, ValueError):
        pass
    time.sleep(2)
else:
    raise SystemExit('Version 2 scrape not confirmed; rollback.')
PY
python3 "$stage/check-frontend-comparison-queries.py" "$stage/candidate.json" --frontend-details
cp -- "$stage/candidate.json" "$dashboard"
cmp -- "$stage/candidate.json" "$dashboard"
curl --max-time 10 -fsS http://127.0.0.1:3000/api/health | python3 -c 'import json,sys; assert json.load(sys.stdin).get("database")=="ok"; print("Grafana database=ok")'
rollback_needed=0
printf '\nPASS: receiver v2 and frontend detail dashboard installed. Backup: %s\n' "$backup"
printf 'Receiver counters restarted. No business traffic was generated by installation.\n'
printf 'Open the production frontend; keep it active for 2-3 minutes. Refresh Grafana after 60 seconds and expand section 08.\n'
printf 'New snapshot metrics appear after the next real packet; old detail history cannot be reconstructed.\n'
printf 'Rollback receiver: sudo install -o root -g root -m 0644 %q %q && sudo systemctl restart %q\n' "$backup/receiver.before.py" "$installed_receiver" "$service"
printf 'Rollback dashboard: cp -- %q %q\n' "$backup/dashboard.before.json" "$repo/$dashboard"
