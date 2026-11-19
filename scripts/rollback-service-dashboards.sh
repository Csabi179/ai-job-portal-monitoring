#!/usr/bin/env bash
set -Eeuo pipefail
backup="${1:?Usage: bash rollback-service-dashboards.sh BACKUP_DIRECTORY}"
repo=/home/ubuntu/ai-job-monitoring
folder="$repo/grafana/provisioning/dashboards/json"
python3 - "$backup" "$folder" <<'PY'
import json,sys
from pathlib import Path
backup,live=map(lambda p:Path(p).resolve(),sys.argv[1:])
if not backup.is_relative_to(Path('/home/ubuntu/monitoring-backups').resolve()) or not backup.name.startswith('service-dashboards.'):
    raise SystemExit('STOP: expected a service-dashboards backup directory.')
meta=json.loads((backup/'metadata.json').read_text(encoding='utf-8'))
for name in meta['files']:
    if name not in ('matchwise-unified-monitoring.json','matchwise-unified-monitoring-en.json','matchwise-service-comparison.json','matchwise-service-comparison-en.json'):
        raise SystemExit('STOP: unexpected backup filename.')
    old=json.loads((backup/name).read_text(encoding='utf-8'))
    new=json.loads((backup/'candidate'/name).read_text(encoding='utf-8'))
    if old['uid']!=new['uid']: raise SystemExit('STOP: backup dashboard identity differs.')
    if (live/name).is_symlink(): raise SystemExit('STOP: unexpected live symlink.')
    if (live/name).exists():
        current=json.loads((live/name).read_text(encoding='utf-8'))
        if current not in (old,new): raise SystemExit('STOP: unrelated live changes in '+name+'; preserve and review them.')
print('Rollback identities and live file versions verified.')
PY
files=(matchwise-unified-monitoring.json matchwise-unified-monitoring-en.json matchwise-service-comparison.json matchwise-service-comparison-en.json)
for file in "${files[@]}"; do
  cp -- "$backup/$file" "$folder/.restore-$file.tmp"
  mv -f -- "$folder/.restore-$file.tmp" "$folder/$file"
done
sudo -n python3 "$backup/verify-provisioned-dashboards.py" "$backup" --files "${files[@]}" --wait 90
printf 'PASS: previous four dashboard models restored and verified in Grafana.\n'
