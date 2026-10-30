import getpass
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "test-logs/render-backend.jsonl"

STATE_DIR = Path.home() / "monitoring-private-state"
STATE_DIR.mkdir(mode=0o700, exist_ok=True)
STATE = STATE_DIR / "render-api-state.json"

OWNER = "tea-dbh72puc6qcc73fqjgvg"
SERVICE = "srv-dbh7b1nb9u1s73e6hpbg"

def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def format_time(value):
    return value.isoformat().replace("+00:00", "Z")

def identity(record):
    return (
        record.get("renderTimestamp"),
        record.get("reqId"),
    )

def main():
    key = os.environ.get("RENDER_API_KEY")
    if not key:
        key = getpass.getpass("Render API key: ")

    seen = set()
    if OUTPUT.exists():
        with OUTPUT.open(encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    seen.add(identity(json.loads(line)))

    now = datetime.now(timezone.utc)
    safe_end = now - timedelta(seconds=20)

    if STATE.exists():
        state = json.loads(STATE.read_text())
        cursor = parse_time(state["completedUntil"])
        start = cursor - timedelta(minutes=3)
        end = min(safe_end, cursor + timedelta(minutes=15))
    else:
        start = now - timedelta(minutes=20)
        end = safe_end

    if start >= end:
        print("No new interval to collect.")
        return

    params = {
        "ownerId": OWNER,
        "resource": SERVICE,
        "type": "app",
        "startTime": format_time(start),
        "endTime": format_time(end),
        "direction": "forward",
        "limit": 100,
    }

    collected = []
    page_count = 0
    visited = set()

    while True:
        page_count += 1
        if page_count > 20:
            raise RuntimeError(
                "Page limit reached. No changes saved."
            )

        cursor_key = (
            params["startTime"],
            params["endTime"],
        )

        if cursor_key in visited:
            raise RuntimeError("Repeated pagination cursor.")

        visited.add(cursor_key)

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

        with urllib.request.urlopen(
            request, timeout=30
        ) as response:
            data = json.load(response)

        for item in data.get("logs", []):
            try:
                message = json.loads(item["message"])
            except (KeyError, ValueError, TypeError):
                continue

            if not isinstance(message, dict):
                continue

            if (
                message.get("event") != "http_request"
                or message.get("service") != "job-portal-backend"
            ):
                continue

            timestamp = item.get("timestamp")
            req_id = message.get("reqId")

            if not isinstance(timestamp, str):
                continue
            if not isinstance(req_id, str):
                continue

            safe = {
                "service": "job-portal-backend",
                "renderTimestamp": timestamp,
            }

            allowed = (
                "level", "event", "reqId", "method",
                "route", "statusCode", "responseTimeMs",
                "errorCode",
            )

            for field in allowed:
                value = message.get(field)
                if type(value) in (str, int, float):
                    safe[field] = value

            record_id = identity(safe)

            if record_id not in seen:
                seen.add(record_id)
                collected.append(safe)

        if not data.get("hasMore", False):
            break

        params["startTime"] = data["nextStartTime"]
        params["endTime"] = data["nextEndTime"]

    collected.sort(
        key=lambda record: record["renderTimestamp"]
    )

    with OUTPUT.open("a", encoding="utf-8") as file:
        for record in collected:
            file.write(
                json.dumps(record, ensure_ascii=False) + "\n"
            )

        file.flush()
        os.fsync(file.fileno())

    temporary = STATE.with_suffix(".tmp")
    fd = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )

    with os.fdopen(fd, "w", encoding="utf-8") as file:
        json.dump(
            {"completedUntil": format_time(end)},
            file,
        )
        file.flush()
        os.fsync(file.fileno())

    os.replace(temporary, STATE)

    print("API pages fetched:", page_count)
    print("New Pino logs written:", len(collected))
    print(
        "New 4xx/5xx logs:",
        sum(
            1 for record in collected
            if isinstance(record.get("statusCode"), int)
            and record["statusCode"] >= 400
        ),
    )
    print("Collection completed through:", format_time(end))

if __name__ == "__main__":
    main()
