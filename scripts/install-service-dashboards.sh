#!/usr/bin/env bash
# Integrate the supplied service-grouped dashboards; change only their four model files.
set -Eeuo pipefail
export LC_ALL=C.UTF-8
repo=/home/ubuntu/ai-job-monitoring
cd "$repo"
ref="${1:?Usage: bash install-service-dashboards.sh FULL_COMMIT_SHA}"
[[ "$ref" =~ ^[0-9a-f]{40}$ ]] || { printf 'Expected full pinned commit SHA.\n' >&2; exit 2; }
baseline=900002e74e6889515b44bf4ac2d4a6ecd110e0b4
service_previous=5ca71a7a0c3d46209e87bdb3e18d467b6904125e
service_original=8433198c9ce09e328fa51044e4bf186303e3eee7
known_refs=("$baseline" "$service_previous" "$service_original" 9437a1d7a2d8f01f9633bfbf7c2689a94aab3d34 75c65c454e89e6528bb93a46bdccaf3a597317b7 f42a936b6c4446b8cbb14d60a98d0aef837cdb83 829ccc54ffaadeb6c1191c11db4839342df17a01)
folder=grafana/provisioning/dashboards/json
files=(matchwise-unified-monitoring.json matchwise-unified-monitoring-en.json matchwise-service-comparison.json matchwise-service-comparison-en.json)
stage=$(mktemp -d /tmp/matchwise-service-dashboards.XXXXXX)
backup=
restore=0
prom_test=
finish() {
  result=$?
  trap - EXIT
  if [[ "$restore" == 1 ]]; then
    printf 'Install failed; restoring the previous four dashboard models from %s\n' "$backup" >&2
    if ! bash "$backup/rollback.sh" "$backup"; then
      printf 'Automatic rollback could not be confirmed. Preserve this backup: %s\n' "$backup" >&2
    fi
    result=1
  fi
  if [[ -n "$prom_test" ]]; then
    sudo -n docker exec --user 0 monitoring-prometheus rm -f -- "$prom_test" >/dev/null 2>&1 || true
  fi
  rm -rf -- "$stage"
  exit "$result"
}
trap finish EXIT
mkdir -p "$stage/scripts" "$stage/$folder" "$stage/baseline" "$stage/docs" "$stage/known"
for script in build-service-dashboards.py check-service-dashboards.py test_bilingual_dashboards.py verify-provisioned-dashboards.py check-dashboard-final-audit.py rollback-service-dashboards.sh; do
  git show "$ref:scripts/$script" > "$stage/scripts/$script"
done
for file in "${files[@]}"; do
  git show "$ref:$folder/$file" > "$stage/$folder/$file"
  git show "$baseline:$folder/$file" > "$stage/baseline/$file"
done
git show "$ref:docs/dashboard-language-manifest.json" > "$stage/docs/dashboard-language-manifest.json"
for known_ref in "${known_refs[@]}"; do
  mkdir -p "$stage/known/$known_ref"
  for file in "${files[@]}"; do
    if git cat-file -e "$known_ref:$folder/$file" 2>/dev/null; then
      git show "$known_ref:$folder/$file" > "$stage/known/$known_ref/$file"
    fi
  done
done
python3 "$stage/scripts/check-service-dashboards.py" "$stage/$folder" --export-promql-rules "$stage/parse-only.yml"
MATCHWISE_DASHBOARD_BASELINE_DIR="$stage/baseline" python3 "$stage/scripts/test_bilingual_dashboards.py" -v
prom_test="/tmp/matchwise-service-query-parse.$$.yml"
sudo -n docker cp "$stage/parse-only.yml" "monitoring-prometheus:$prom_test"
sudo -n docker exec monitoring-prometheus promtool check rules "$prom_test"
python3 - "$folder" "$stage" "$service_previous" "$service_original" <<'PY'
import json,sys
from pathlib import Path
live,stage=map(Path,sys.argv[1:3]);previous,original=sys.argv[3:5]
files=['matchwise-unified-monitoring.json','matchwise-unified-monitoring-en.json','matchwise-service-comparison.json','matchwise-service-comparison-en.json']
candidate=baseline=ready=0
for name in files:
    path=live/name
    if path.is_symlink(): raise SystemExit('STOP: unexpected live symlink: '+name)
    if not path.exists():
        if name.endswith('-en.json'): continue
        raise SystemExit('STOP: missing existing HU file: '+name)
    current=json.loads(path.read_text(encoding='utf-8'))
    new=json.loads((stage/'grafana/provisioning/dashboards/json'/name).read_text(encoding='utf-8'))
    old=json.loads((stage/'baseline'/name).read_text(encoding='utf-8'))
    allowed=[new]+[json.loads(p.read_text(encoding='utf-8')) for p in (stage/'known').glob('*/'+name)]
    if current not in allowed: raise SystemExit('STOP: unknown live changes in '+name+'; no trial files installed.')
    previous_model=json.loads((stage/'known'/previous/name).read_text(encoding='utf-8'))
    original_model=json.loads((stage/'known'/original/name).read_text(encoding='utf-8'))
    candidate+=int(current==new);baseline+=int(current==old)
    ready+=int(current in (old,new,previous_model,original_model))
if candidate and candidate!=4: raise SystemExit('STOP: partial service-dashboard install; restore the printed backup before retrying.')
(stage/'prepare-needed').write_text('0' if ready==4 else '1')
print('Live dashboard files match reviewed versions.')
PY
if [[ "$(cat "$stage/prepare-needed")" == 1 ]]; then
  printf 'Finishing the earlier HU/English setup first, using its Grafana-13-aware pinned installer...\n'
  git show "$baseline:scripts/install-bilingual-dashboards.sh" > "$stage/prepare.sh"
  bash -n "$stage/prepare.sh"
  bash "$stage/prepare.sh" "$baseline"
fi
curl --max-time 10 -fsS http://127.0.0.1:9121/metrics > "$stage/receiver-metrics.txt"
python3 - "$stage/receiver-metrics.txt" <<'PY'
import sys
from pathlib import Path
if 'frontend_telemetry_receiver_schema_version 2' not in Path(sys.argv[1]).read_text():
    raise SystemExit('STOP: extended receiver v2 must be active before installing these dashboards.')
PY
curl --max-time 10 -fsS http://127.0.0.1:3000/api/health | python3 -c 'import json,sys; assert json.load(sys.stdin).get("database")=="ok"'
printf 'Read-only live audit of all candidate queries and one-hour history...\n'
python3 "$stage/scripts/check-service-dashboards.py" "$stage/$folder" --live | tee "$stage/datasource-audit.txt"
mkdir -p /home/ubuntu/monitoring-backups
backup=$(mktemp -d /home/ubuntu/monitoring-backups/service-dashboards.XXXXXX)
mkdir -p "$backup/candidate"
for file in "${files[@]}"; do
  cp -p -- "$folder/$file" "$backup/$file"
  cp -- "$stage/$folder/$file" "$backup/candidate/$file"
done
cp -- "$stage/scripts/rollback-service-dashboards.sh" "$backup/rollback.sh"
cp -- "$stage/scripts/verify-provisioned-dashboards.py" "$backup/verify-provisioned-dashboards.py"
cp -- "$stage/datasource-audit.txt" "$backup/datasource-audit.txt"
python3 - "$backup" "$ref" "$baseline" <<'PY'
import json,sys
from pathlib import Path
backup=Path(sys.argv[1])
files=['matchwise-unified-monitoring.json','matchwise-unified-monitoring-en.json','matchwise-service-comparison.json','matchwise-service-comparison-en.json']
(backup/'metadata.json').write_text(json.dumps({'commit':sys.argv[2],'baseline':sys.argv[3],'files':files},indent=2)+'\n',encoding='utf-8')
PY
printf 'Backup: %s\n' "$backup"
restore=1
for file in "${files[@]}"; do
  cp -- "$stage/$folder/$file" "$folder/.install-$file.tmp"
  mv -f -- "$folder/.install-$file.tmp" "$folder/$file"
  cmp -- "$stage/$folder/$file" "$folder/$file"
done
printf 'Waiting up to 90 seconds for Grafana to load all four trial models...\n'
sudo -n python3 "$stage/scripts/verify-provisioned-dashboards.py" "$stage/$folder" --files "${files[@]}" --wait 90
curl --max-time 10 -fsS http://127.0.0.1:3000/api/health | python3 -c 'import json,sys; assert json.load(sys.stdin).get("database")=="ok"; print("Grafana database=ok")'
restore=0
printf '\nPASS: service-grouped HU/English dashboards installed and stored models verified.\n'
printf 'Refresh Grafana with Ctrl+F5. Authenticated browser rendering still needs visual confirmation.\n'
printf 'One-command rollback: bash %q %q\n' "$backup/rollback.sh" "$backup"
printf 'No collector/configuration changes were made for the new design. No business traffic was generated.\n'
