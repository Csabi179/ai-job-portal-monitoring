#!/usr/bin/env bash
# Run from the monitoring checkout. Only the provisioned comparison JSON is changed.
set -Eeuo pipefail
export LC_ALL=C.UTF-8
repo=/home/ubuntu/ai-job-monitoring
cd "$repo"
ref="${1:?Usage: bash install-dashboard-redesign.sh COMMIT_SHA}"
[[ "$ref" =~ ^[0-9a-f]{40}$ ]] || { printf 'Expected pinned commit SHA.\n' >&2; exit 2; }
baseline_ref=922aeaee8108db1f8ee91260971170eda5846f56
dashboard=grafana/provisioning/dashboards/json/matchwise-service-comparison.json
stage=$(mktemp -d /tmp/matchwise-dashboard-redesign.XXXXXX)
trap 'rm -rf -- "$stage"' EXIT
git show "$ref:$dashboard" > "$stage/candidate.json"
git show "$baseline_ref:$dashboard" > "$stage/baseline.json"
git show "$ref:scripts/validate-dashboard-redesign.py" > "$stage/validate.py"
git show "$ref:scripts/check-frontend-comparison-queries.py" > "$stage/check.py"
python3 "$stage/validate.py" "$stage/candidate.json" "$stage/baseline.json"
python3 - "$dashboard" "$stage/baseline.json" "$stage/candidate.json" <<'PY'
import json, sys
from pathlib import Path
live, baseline, candidate = (json.loads(Path(p).read_text(encoding='utf-8')) for p in sys.argv[1:])
if live not in (baseline, candidate):
    raise SystemExit('STOP: live dashboard differs from the known baseline; preserve and review local changes.')
print('Live comparison dashboard matches a reviewed version.')
PY
python3 "$stage/check.py" "$stage/candidate.json" --overview
python3 "$stage/check.py" "$stage/candidate.json" --include-database
curl --max-time 10 -fsS http://127.0.0.1:3000/api/health | python3 -c 'import json,sys; h=json.load(sys.stdin); assert h.get("database")=="ok"; print("Grafana database=ok")'
mkdir -p /home/ubuntu/monitoring-backups
backup=$(mktemp -d /home/ubuntu/monitoring-backups/dashboard-redesign.XXXXXX)
cp -p -- "$dashboard" "$backup/dashboard.before.json"
cp -- "$stage/candidate.json" "$backup/dashboard.after.json"
cp -- "$stage/candidate.json" "$dashboard"
cmp -- "$stage/candidate.json" "$dashboard"
printf '\nInstalled comparison dashboard only. Backup: %s\n' "$backup"
printf 'Allow up to 60 seconds for provisioning, then refresh Grafana. No container restart required.\n'
printf 'Rollback: cp -- %q %q\n' "$backup/dashboard.before.json" "$repo/$dashboard"
