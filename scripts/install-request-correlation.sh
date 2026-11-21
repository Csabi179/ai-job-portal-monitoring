#!/usr/bin/env bash
# Run after pulling the reviewed commit. Never resets Git or opens firewall ports.
set -Eeuo pipefail
cd /home/ubuntu/ai-job-monitoring
service=matchwise-frontend-traffic.service
receiver=/usr/local/lib/matchwise/frontend-traffic-receiver.py
dropin=/etc/systemd/system/$service.d/requests.conf
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || {
  printf 'STOP: review tracked local changes before installation.\n' >&2; exit 1;
}
sudo -n systemctl is-active --quiet "$service"
sudo -n test -f "$receiver"
sudo -n test ! -f "$dropin" || {
  printf 'STOP: requests.conf already exists; inspect the previous installation.\n' >&2; exit 1;
}
cmd=$(sudo -n systemctl show "$service" -p ExecStart --value)
[[ "$cmd" == *"$receiver"* ]] || { printf 'Unexpected receiver executable.\n' >&2; exit 1; }
FRONTEND_TRAFFIC_ORIGINS=https://www.matchwise.tech python3 -m unittest discover -s scripts -p 'test_frontend*.py'
python3 scripts/check-request-correlation-dashboard.py
sudo -n docker compose config --quiet

# DynamicUser state is created by systemd when the upgraded service starts.
mkdir -p /home/ubuntu/monitoring-backups
backup=$(mktemp -d /home/ubuntu/monitoring-backups/request-correlation.XXXXXX)
sudo -n cp -p "$receiver" "$backup/receiver.before.py"
printf '%s\n' "$(git rev-parse HEAD)" > "$backup/source-commit.txt"
printf 'Backup: %s\n' "$backup"
printf 'Rollback receiver (does not remove retained request logs):\n'
printf 'sudo install -m 0644 %q %q\n' "$backup/receiver.before.py" "$receiver"
printf 'sudo rm -- %q\n' "$dropin"
printf 'sudo systemctl daemon-reload && sudo systemctl restart %q\n' "$service"

rollback=1
finish() {
  result=$?
  trap - EXIT
  if [[ "$result" != 0 && "$rollback" == 1 ]]; then
    printf 'Installation failed; restoring receiver. Backup: %s\n' "$backup" >&2
    sudo -n install -m 0644 "$backup/receiver.before.py" "$receiver" || true
    sudo -n rm -f -- "$dropin" || true
    sudo -n systemctl daemon-reload || true
    sudo -n systemctl restart "$service" || true
    printf 'Inspect Alloy state and retained Git configuration before retrying.\n' >&2
  fi
  exit "$result"
}
trap finish EXIT

sudo -n install -m 0644 scripts/frontend-traffic-receiver.py "$receiver"
sudo -n install -d -m 0755 "/etc/systemd/system/$service.d"
sudo -n install -m 0644 systemd/matchwise-frontend-requests.conf "$dropin"
sudo -n systemctl daemon-reload
sudo -n systemctl restart "$service"
for attempt in {1..15}; do
  if curl --max-time 3 -fsS http://127.0.0.1:9121/metrics > "$backup/receiver-metrics.txt" &&
     grep -q '^frontend_telemetry_receiver_schema_version 3$' "$backup/receiver-metrics.txt"; then
    break
  fi
  sleep 1
done
grep -q '^frontend_telemetry_receiver_schema_version 3$' "$backup/receiver-metrics.txt"
sudo -n test -d /var/lib/matchwise-frontend-traffic
sudo -n docker compose run --rm --no-deps --entrypoint alloy alloy \
  validate /etc/alloy/config.alloy
sudo -n docker compose up -d --no-deps --force-recreate alloy
curl --retry 10 --retry-connrefused --retry-delay 1 --max-time 5 -fsS http://127.0.0.1:12345/-/healthy
python3 scripts/check-request-correlation-dashboard.py --loki http://127.0.0.1:3100
rollback=0
printf '\nReceiver v3 and Alloy updated. Grafana file provisioning reloads within 30 seconds.\n'
printf 'Open the real frontend, make an API request, wait for the 60-second report and backend collection.\n'
printf 'Verify frontend/backend request IDs and durations in /d/matchwise-request-correlation-en.\n'
printf 'Installation is NOT an end-to-end delivery test. Keep this backup: %s\n' "$backup"
