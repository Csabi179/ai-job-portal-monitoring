#!/usr/bin/env bash
# Add a Grafana panel only: no new service, no restart, no reset/pull of the live checkout.
set -Eeuo pipefail
cd /home/ubuntu/ai-job-monitoring
ref=${1:?Usage: bash install-paired-request-chart.sh COMMIT}
ref=$(git rev-parse --verify "$ref^{commit}")
helper=$(mktemp /tmp/matchwise-paired-chart.XXXXXX.py)
trap 'rm -f -- "$helper"' EXIT
git show "$ref:scripts/install-request-table-details.py" > "$helper"
python3 "$helper" "$ref" --paired-chart
