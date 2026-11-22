#!/usr/bin/env bash
# Update only request tables from a pinned commit; retain live dashboard customizations.
set -Eeuo pipefail
cd /home/ubuntu/ai-job-monitoring
ref=${1:?Usage: bash install-request-table-details.sh COMMIT}
ref=$(git rev-parse --verify "$ref^{commit}")
helper=$(mktemp /tmp/matchwise-request-table.XXXXXX.py)
trap 'rm -f -- "$helper"' EXIT
git show "$ref:scripts/install-request-table-details.py" > "$helper"
python3 "$helper" "$ref"
