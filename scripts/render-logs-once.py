import getpass
import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

OWNER = "tea-dbh72puc6qcc73fqjgvg"
SERVICE = "srv-dbh7b1nb9u1s73e6hpbg"
OUTPUT = Path("test-logs/render-backend.jsonl")

key = getpass.getpass("Render API key: ")

now = datetime.now(timezone.utc)
start = now - timedelta(minutes=10)

def iso(value):
    return value.isoformat().replace("+00:00", "Z")

params = {
    "ownerId": OWNER,
    "resource": SERVICE,
    "type": "app",
    "startTime": iso(start),
    "endTime": iso(now),
    "direction": "backward",
    "limit": 100,
}

records = {}
pages = 0
visited = set()

while True:
    pages += 1

    if pages > 12:
        raise SystemExit(
            "Pagination exceeds test limit. No file written."
        )

    marker = (params["startTime"], params["endTime"])
    if marker in visited:
        raise SystemExit("Repeated pagination cursor.")
    visited.add(marker)

    url = (
        "https://api.render.com/v1/logs?"
        + urllib.parse.urlencode(params)
    )

    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)

    for item in data.get("logs", []):
        try:
            message = json.loads(item["message"])
        except (ValueError, TypeError, KeyError):
            continue

        if not isinstance(message, dict):
            continue

        if (
            message.get("event") != "http_request"
            or message.get("service") != "job-portal-backend"
        ):
            continue

        log_id = item.get("id")
        if not isinstance(log_id, str):
            continue

        # Allowlist: never store the raw Render log message.
        allowed = (
            "level", "event", "reqId", "method", "route",
            "statusCode", "responseTimeMs", "errorCode"
        )

        safe = {
            "service": "job-portal-backend",
            "renderTimestamp": item.get("timestamp"),
        }

        for field in allowed:
            value = message.get(field)
            if type(value) in (str, int, float):
                safe[field] = value

        records[log_id] = safe

    if not data.get("hasMore", False):
        break

    params["startTime"] = data["nextStartTime"]
    params["endTime"] = data["nextEndTime"]

with OUTPUT.open("a", encoding="utf-8") as file:
    for record in sorted(
        records.values(),
        key=lambda item: item.get("renderTimestamp") or ""
    ):
        file.write(json.dumps(record, ensure_ascii=False) + "\n")

print("API pages fetched:", pages)
print("Pino logs written:", len(records))
print("Output:", OUTPUT)
