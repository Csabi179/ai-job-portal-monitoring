#!/usr/bin/env bash
# Explicitly requested final review: deploy only reviewed monitoring dashboard files.
set -Eeuo pipefail
export LC_ALL=C.UTF-8
repo=/home/ubuntu/ai-job-monitoring
cd "$repo"
ref="${1:?Usage: bash install-dashboard-final-audit.sh COMMIT_SHA}"
[[ "$ref" =~ ^[0-9a-f]{40}$ ]] || { printf 'Expected pinned full commit SHA.\n' >&2; exit 2; }
baseline=f42a936b6c4446b8cbb14d60a98d0aef837cdb83
previous=829ccc54ffaadeb6c1191c11db4839342df17a01
folder=grafana/provisioning/dashboards/json
stage=$(mktemp -d /tmp/matchwise-final-audit.XXXXXX)
backup=
restore=0
prom_test=
finish() {
  result=$?
  trap - EXIT
  if [[ "$restore" == 1 ]]; then
    printf 'Restoring both dashboards from %s\n' "$backup" >&2
    cp -- "$backup/unified.before.json" "$folder/matchwise-unified-monitoring.json" || result=1
    cp -- "$backup/comparison.before.json" "$folder/matchwise-service-comparison.json" || result=1
  fi
  if [[ -n "$prom_test" ]]; then
    sudo -n docker exec --user 0 monitoring-prometheus rm -f -- "$prom_test" >/dev/null 2>&1 || true
  fi
  rm -rf -- "$stage"
  exit "$result"
}
trap finish EXIT
for script in check-dashboard-final-audit.py verify-provisioned-dashboards.py test_dashboard_final_audit.py; do
  git show "$ref:scripts/$script" > "$stage/$script"
done
git show "$ref:docs/dashboard-query-audit.json" > "$stage/dashboard-query-audit.json"
git show "$ref:scripts/dashboard-guard-tests.yml" > "$stage/dashboard-guard-tests.yml"
for name in unified comparison; do
  file=matchwise-service-comparison.json
  [[ "$name" != unified ]] || file=matchwise-unified-monitoring.json
  git show "$ref:$folder/$file" > "$stage/$file"
  git show "$baseline:$folder/$file" > "$stage/baseline-$name.json"
done
git show "$previous:$folder/matchwise-service-comparison.json" > "$stage/previous-comparison.json"
python3 "$stage/check-dashboard-final-audit.py" "$stage"
python3 "$stage/test_dashboard_final_audit.py" -v
prom_test="/tmp/matchwise-dashboard-guards.$$.yml"
sudo -n docker cp "$stage/dashboard-guard-tests.yml" "monitoring-prometheus:$prom_test"
sudo -n docker exec monitoring-prometheus promtool test rules "$prom_test"
python3 - "$repo/$folder" "$stage" <<'PY'
import json,sys
from pathlib import Path
live,stage=map(Path,sys.argv[1:])
for name,file in [('unified','matchwise-unified-monitoring.json'),('comparison','matchwise-service-comparison.json')]:
    current=json.loads((live/file).read_text(encoding='utf-8'))
    allowed=[json.loads((stage/('baseline-'+name+'.json')).read_text(encoding='utf-8')),json.loads((stage/file).read_text(encoding='utf-8'))]
    if name=='comparison': allowed.append(json.loads((stage/'previous-comparison.json').read_text(encoding='utf-8')))
    if current not in allowed:
        def walk(ps):
            for p in ps:
                yield p
                yield from walk(p.get('panels',[]))
        a={p['id']:p for p in walk(current.get('panels',[]))}
        b={p['id']:p for p in walk(allowed[0]['panels'])}
        print(name,'STOP: unknown live changes. Differing panel IDs:',sorted(k for k in set(a)|set(b) if a.get(k)!=b.get(k)))
        print('Differing root fields:',sorted(k for k in set(current)|set(allowed[0]) if current.get(k)!=allowed[0].get(k)))
        print('No files changed. Preserve and review the live model before installing.')
        raise SystemExit(1)
print('Both live dashboard files match reviewed versions.')
PY
curl --max-time 10 -fsS http://127.0.0.1:3000/api/health | python3 -c 'import json,sys; assert json.load(sys.stdin).get("database")=="ok"; print("Grafana database=ok")'
mkdir -p /home/ubuntu/monitoring-backups
backup=$(mktemp -d /home/ubuntu/monitoring-backups/dashboard-final-audit.XXXXXX)
cp -p -- "$folder/matchwise-unified-monitoring.json" "$backup/unified.before.json"
cp -p -- "$folder/matchwise-service-comparison.json" "$backup/comparison.before.json"
printf 'Backup: %s\n' "$backup"
# Finish the previously requested receiver upgrade only if it is still pending.
curl --max-time 10 -fsS http://127.0.0.1:9121/metrics > "$stage/receiver-metrics.txt"
if ! python3 - "$stage/receiver-metrics.txt" <<'PY'
import sys
from pathlib import Path
raise SystemExit(0 if 'frontend_telemetry_receiver_schema_version 2' in Path(sys.argv[1]).read_text() else 1)
PY
then
  printf 'Receiver v2 is not active; finishing the already-authorized frontend detail upgrade first.\n'
  git show "$baseline:scripts/install-frontend-details.sh" > "$stage/install-details.sh"
  bash -n "$stage/install-details.sh"
  restore=1
  bash "$stage/install-details.sh" "$baseline"
fi
printf 'Checking every target in both dashboards, including one-hour graph history...\n'
python3 "$stage/check-dashboard-final-audit.py" "$stage" --live --history | tee "$backup/datasource-audit.txt"
restore=1
cp -- "$stage/matchwise-unified-monitoring.json" "$folder/matchwise-unified-monitoring.json"
cp -- "$stage/matchwise-service-comparison.json" "$folder/matchwise-service-comparison.json"
cmp -- "$stage/matchwise-unified-monitoring.json" "$folder/matchwise-unified-monitoring.json"
cmp -- "$stage/matchwise-service-comparison.json" "$folder/matchwise-service-comparison.json"
verification=0
printf 'Waiting up to 75 seconds for Grafana to provision both reviewed dashboard models...\n'
sudo -n python3 "$stage/verify-provisioned-dashboards.py" "$stage" --wait 75 || verification=$?
if [[ "$verification" != 0 && "$verification" != 3 ]]; then exit "$verification"; fi
curl --max-time 10 -fsS http://127.0.0.1:3000/api/health | python3 -c 'import json,sys; assert json.load(sys.stdin).get("database")=="ok"; print("Grafana database=ok")'
restore=0
printf '\nPASS: both dashboard files installed; datasource audit passed. Backup: %s\n' "$backup"
if [[ "$verification" == 3 ]]; then printf 'Provisioning still needs browser confirmation; automatic stored-model check was unavailable.\n'; fi
printf 'Refresh both Grafana dashboards with Ctrl+F5. Comparison: removed Backend logs / Data sources rows; frontend details are now section 06.\n'
printf 'No restart was needed if receiver v2 was already installed. No business requests were generated.\n'
printf 'Rollback unified: cp -- %q %q\n' "$backup/unified.before.json" "$repo/$folder/matchwise-unified-monitoring.json"
printf 'Rollback comparison: cp -- %q %q\n' "$backup/comparison.before.json" "$repo/$folder/matchwise-service-comparison.json"
