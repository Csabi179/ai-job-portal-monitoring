#!/usr/bin/env bash
# Explicitly authorized on 2026-11-19: FRONTEND main only. No monitoring merge.
set -Eeuo pipefail

if [[ "${1:-}" != "--merge" || "$#" != 1 ]]; then
  printf 'Usage: bash %s --merge\n' "$0" >&2
  exit 2
fi

repo=ernoking/job-portal-frontend
head_branch=feat/frontend-api-traffic
expected_head=e48661ef58be096bf1ff970368432ebd16e5e9ca
expected_base=475cc291ae2187048ab588a51c1b4cc69b732e36

fail() { printf '%s\n' "$*" >&2; exit 1; }
command -v gh >/dev/null
command -v python3 >/dev/null
command -v curl >/dev/null

# Verify the already-installed Oracle receiver and Prometheus before release preparation.
curl --noproxy '*' --max-time 5 -fsS http://127.0.0.1:9121/health
python3 - <<'PY'
import json
from urllib.parse import urlencode
from urllib.request import ProxyHandler, build_opener
opener = build_opener(ProxyHandler({}))
for query in ('up{job="frontend_traffic"}', 'frontend_telemetry_receiver_up{job="frontend_traffic"}'):
    url = 'http://127.0.0.1:9090/api/v1/query?' + urlencode({'query': query})
    with opener.open(url, timeout=10) as response:
        data = json.load(response)
    rows = data.get('data', {}).get('result', [])
    if data.get('status') != 'success' or len(rows) != 1 or float(rows[0]['value'][1]) != 1:
        raise SystemExit('Receiver/Prometheus readiness check failed: ' + query)
print('Oracle receiver and Prometheus: READY')
PY

cors="$(curl --noproxy '*' --resolve grafana-r0cecq.duckdns.org:443:127.0.0.1 \
  --max-time 10 -sS -X OPTIONS -H 'Origin: https://www.matchwise.tech' \
  -o /dev/null -w '%{http_code}' \
  https://grafana-r0cecq.duckdns.org/matchwise-telemetry/v1)"
[[ "$cors" == 204 ]] || fail "Production-origin CORS returned $cors; expected 204."
printf 'Production-origin HTTPS/CORS: READY\n'

actual_head="$(gh api "repos/$repo/branches/$head_branch" --jq '.commit.sha')"
[[ "$actual_head" == "$expected_head" ]] || fail 'Frontend head changed; review the new commit before merging.'
actual_base="$(gh api "repos/$repo/branches/main" --jq '.commit.sha')"
if [[ "$actual_base" != "$expected_base" ]]; then
  comparison="$(gh api "repos/$repo/compare/$expected_head...main" --jq '.status')"
  if [[ "$comparison" == ahead || "$comparison" == identical ]]; then
    printf 'The tested frontend code is already contained in main: %s\n' "$actual_base"
    exit 0
  fi
  fail 'Frontend main changed; repeat the comparison/review before merging.'
fi

work="$(mktemp -d /tmp/matchwise-production-pr.XXXXXX)"
cat > "$work/pr-body.md" <<'PRBODY'
Adds browser-side API traffic aggregates for comparing frontend activity with Render backend logs and Supabase workload. The shared request helper records starts, HTTP responses, network failures and response-header timing, then sends bounded batches every 60 seconds to the Oracle receiver. Reporting remains disabled by default and requires explicit build configuration.

No raw URLs, request/response bodies, credentials or user identifiers are included. The Oracle receiver and 45-panel comparison dashboard are deployed and were verified using the SSH/Vite test configuration.

Validation:
- 10 telemetry tests passed.
- Lint and production build passed on Oracle and GitHub CI.
- Repeated HTTP 204 ingestion and real auth/CV API observations verified.
- Frontend/backend and database context charts rendered successfully.
- Temporary localhost test access removed after testing.

Production activation:
1. Ensure the production deployment uses this source.
2. Set Production-only `VITE_FRONTEND_TELEMETRY_ENABLED=true`.
3. Set `VITE_FRONTEND_TELEMETRY_URL=https://grafana-r0cecq.duckdns.org/matchwise-telemetry/v1`.
4. Build/deploy with the Production values, then verify real browser POSTs and Grafana freshness.

The production environment settings and deployment remain operator actions. This PR does not merge the monitoring repository branch or enable paid Vercel observability features.

[Production activation guide](https://github.com/Csabi179/ai-job-portal-monitoring/blob/feat/service-comparison/docs/FRONTEND_PRODUCTION_ACTIVATION.md)
PRBODY

pr="$(gh pr list --repo "$repo" --base main --head "$head_branch" --state open \
  --json number --jq '.[0].number // empty')"
if [[ -z "$pr" ]]; then
  gh pr create --repo "$repo" --base main --head "$head_branch" \
    --title 'feat: add opt-in browser API traffic monitoring' --body-file "$work/pr-body.md"
  pr="$(gh pr list --repo "$repo" --base main --head "$head_branch" --state open \
    --json number --jq '.[0].number // empty')"
fi
[[ "$pr" =~ ^[0-9]+$ ]] || fail 'Could not identify the frontend PR.'

pr_head="$(gh pr view "$pr" --repo "$repo" --json headRefOid --jq '.headRefOid')"
pr_base="$(gh pr view "$pr" --repo "$repo" --json baseRefName --jq '.baseRefName')"
draft="$(gh pr view "$pr" --repo "$repo" --json isDraft --jq '.isDraft')"
[[ "$pr_head" == "$expected_head" && "$pr_base" == main && "$draft" == false ]] \
  || fail 'PR head/base/draft state differs from the reviewed release.'
printf 'Frontend PR: https://github.com/%s/pull/%s\n' "$repo" "$pr"

# Allow newly-created PR checks to register, then wait for all reported checks.
registered=false
for attempt in 1 2 3 4 5 6; do
  count="$(gh pr checks "$pr" --repo "$repo" --json name --jq 'length')" || true
  if [[ "$count" =~ ^[0-9]+$ && "$count" -gt 0 ]]; then registered=true; break; fi
  sleep 5
done
[[ "$registered" == true ]] || fail 'No PR checks registered; do not merge without validation.'
gh pr checks "$pr" --repo "$repo" --watch --fail-fast
ci_success="$(gh api "repos/$repo/commits/$expected_head/check-runs" --jq '[.check_runs[] | select(.name == "check" and .conclusion == "success")] | length')"
[[ "$ci_success" =~ ^[0-9]+$ && "$ci_success" -gt 0 ]] || fail 'The frontend CI check has no successful result for the tested head.'

actual_base="$(gh api "repos/$repo/branches/main" --jq '.commit.sha')"
[[ "$actual_base" == "$expected_base" ]] || fail 'Main moved during CI; repeat review before merging.'

# Normal PR merge only: no --admin, --auto, force push or branch deletion.
gh pr merge "$pr" --repo "$repo" --merge --match-head-commit "$expected_head"
gh pr view "$pr" --repo "$repo" --json state,mergedAt,mergeCommit,url

main_sha="$(gh api "repos/$repo/branches/main" --jq '.commit.sha')"
comparison="$(gh api "repos/$repo/compare/$expected_head...$main_sha" --jq '.status')"
[[ "$comparison" == ahead || "$comparison" == identical ]] || fail 'Merge ancestry verification failed.'
printf 'Frontend main contains the tested source: %s\n' "$main_sha"
printf 'Monitoring branch was not merged. Production variables and a new Production build are still required.\n'
