#!/usr/bin/env bash
# Single entry point: finish the pending audit, retain HU models, add English copies.
set -Eeuo pipefail
export LC_ALL=C.UTF-8
repo=/home/ubuntu/ai-job-monitoring
cd "$repo"
ref="${1:?Usage: bash install-bilingual-dashboards.sh COMMIT_SHA}"
[[ "$ref" =~ ^[0-9a-f]{40}$ ]] || { printf 'Expected full pinned commit SHA.\n' >&2; exit 2; }
preparation=75c65c454e89e6528bb93a46bdccaf3a597317b7
legacy=f42a936b6c4446b8cbb14d60a98d0aef837cdb83
previous=829ccc54ffaadeb6c1191c11db4839342df17a01
folder=grafana/provisioning/dashboards/json
files=(matchwise-unified-monitoring.json matchwise-unified-monitoring-en.json matchwise-service-comparison.json matchwise-service-comparison-en.json)
stage=$(mktemp -d /tmp/matchwise-dashboard-languages.XXXXXX)
backup=
restore=0
finish() {
  result=$?
  trap - EXIT
  if [[ "$restore" == 1 ]]; then
    printf 'Restoring all four dashboard file slots from %s\n' "$backup" >&2
    for file in "${files[@]}"; do
      if [[ -f "$backup/$file.present" ]]; then
        cp -- "$backup/$file" "$folder/$file" || result=1
      else
        rm -f -- "$folder/$file" || result=1
      fi
    done
    printf 'Any separately completed receiver preparation remains installed; its own backup was printed.\n' >&2
  fi
  rm -rf -- "$stage"
  exit "$result"
}
trap finish EXIT
for file in "${files[@]}"; do
  [[ ! -L "$folder/$file" ]] || { printf 'STOP: unexpected symlink: %s\n' "$file" >&2; exit 1; }
  git show "$ref:$folder/$file" > "$stage/$file"
done
for script in check-bilingual-dashboards.py check-dashboard-final-audit.py verify-provisioned-dashboards.py build-bilingual-dashboards.py test_bilingual_dashboards.py; do
  git show "$ref:scripts/$script" > "$stage/$script"
done
git show "$ref:docs/dashboard-language-manifest.json" > "$stage/dashboard-language-manifest.json"
for kind in unified comparison; do
  file=matchwise-service-comparison.json
  [[ "$kind" != unified ]] || file=matchwise-unified-monitoring.json
  git show "$preparation:$folder/$file" > "$stage/preparation-$kind.json"
  git show "$legacy:$folder/$file" > "$stage/legacy-$kind.json"
done
git show "$previous:$folder/matchwise-service-comparison.json" > "$stage/previous-comparison.json"
python3 "$stage/check-bilingual-dashboards.py" "$stage"
python3 "$stage/test_bilingual_dashboards.py" -v
python3 - "$folder" "$stage" <<'PY'
import json,sys
from pathlib import Path
live,stage=map(Path,sys.argv[1:])
manifest=json.loads((stage/'dashboard-language-manifest.json').read_text(encoding='utf-8'))['dashboards']
prepared=[]
for item in manifest:
    file=item['file']; path=live/file
    candidate=json.loads((stage/file).read_text(encoding='utf-8'))
    if not path.exists():
        if item['language']=='en': continue
        raise SystemExit('STOP: missing existing Hungarian dashboard file: '+file)
    current=json.loads(path.read_text(encoding='utf-8'))
    allowed=[candidate]
    if item['language']=='hu':
        allowed += [json.loads((stage/(prefix+'-'+item['kind']+'.json')).read_text(encoding='utf-8')) for prefix in ('preparation','legacy')]
        if item['kind']=='comparison': allowed.append(json.loads((stage/'previous-comparison.json').read_text(encoding='utf-8')))
        prepared.append(current==candidate)
    if current not in allowed:
        raise SystemExit('STOP: unknown live changes in '+file+'; preserve and review before installing.')
if any(prepared) and not all(prepared):
    raise SystemExit('STOP: only one HU model matches the candidate; review the partial state.')
(stage/'preparation-needed').write_text('0' if all(prepared) else '1')
print('Live files match reviewed versions; unknown English files will not be overwritten.')
PY
mkdir -p /home/ubuntu/monitoring-backups
backup=$(mktemp -d /home/ubuntu/monitoring-backups/dashboard-languages.XXXXXX)
for file in "${files[@]}"; do
  if [[ -f "$folder/$file" ]]; then
    cp -p -- "$folder/$file" "$backup/$file"
    touch "$backup/$file.present"
  fi
done
printf 'Backup: %s\n' "$backup"
restore=1
if [[ "$(cat "$stage/preparation-needed")" == 1 ]]; then
  printf 'Completing the previously requested final audit using its pinned installer...\n'
  git show "$preparation:scripts/install-dashboard-final-audit.sh" > "$stage/prepare.sh"
  bash -n "$stage/prepare.sh"
  bash "$stage/prepare.sh" "$preparation" | tee "$backup/preparation-audit.txt"
  printf 'HU/English expanded queries are identical; reusing the successful source datasource audit.\n'
else
  python3 "$stage/check-bilingual-dashboards.py" "$stage" --live | tee "$backup/datasource-audit.txt"
fi
printf 'Phase 1: apply and confirm HU names before reusing the base names for English.\n'
for file in matchwise-unified-monitoring.json matchwise-service-comparison.json; do
  cp -- "$stage/$file" "$folder/$file"
  cmp -- "$stage/$file" "$folder/$file"
done
rename_verification=0
sudo -n python3 "$stage/verify-provisioned-dashboards.py" "$stage" --wait 75 || rename_verification=$?
if [[ "$rename_verification" != 0 ]]; then
  printf 'Cannot confirm the HU rename before creating English dashboards with the original names; restoring files.\n' >&2
  exit 1
fi
printf 'Phase 2: add the two English dashboards with unmarked base names.\n'
for file in matchwise-unified-monitoring-en.json matchwise-service-comparison-en.json; do
  cp -- "$stage/$file" "$folder/$file"
  cmp -- "$stage/$file" "$folder/$file"
done
verification=0
printf 'Waiting up to 75 seconds for all four Grafana models...\n'
sudo -n python3 "$stage/verify-provisioned-dashboards.py" "$stage" --files "${files[@]}" --wait 75 || verification=$?
if [[ "$verification" != 0 && "$verification" != 3 ]]; then exit "$verification"; fi
curl --max-time 10 -fsS http://127.0.0.1:3000/api/health | python3 -c 'import json,sys; assert json.load(sys.stdin).get("database")=="ok"; print("Grafana database=ok")'
restore=0
printf '\nPASS: two HU dashboards retained; two English dashboards added. Backup: %s\n' "$backup"
if [[ "$verification" == 3 ]]; then printf 'Browser provisioning verification is still required; stored-model check was unavailable.\n'; fi
python3 - "$stage/dashboard-language-manifest.json" <<'PY'
import json,sys
from pathlib import Path
for item in json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))['dashboards']:
    print(item['title']+' -> https://grafana-r0cecq.duckdns.org/d/'+item['uid'])
PY
printf 'Refresh Grafana with Ctrl+F5. Use the dashboard language link to switch. No monitoring main merge.\n'
