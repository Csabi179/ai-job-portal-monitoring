import getpass
import json
import os
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "test-logs/render-backend.jsonl"

STATE_DIR = Path.home() / "monitoring-private-state"
STATE = STATE_DIR / "render-api-state.json"
DATABASE = STATE_DIR / "render-logs-seen.sqlite3"

OWNER = os.environ["RENDER_OWNER_ID"]
SERVICE = os.environ["RENDER_SERVICE_ID"]
PINO_SERVICE = os.environ.get("RENDER_PINO_SERVICE", "job-portal-backend")

ALLOWED = (
    "level", "event", "reqId", "method", "route",
    "statusCode", "responseTimeMs", "errorCode"
)


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def format_time(value):
    return value.isoformat().replace("+00:00", "Z")


def record_keys(record):
    keys = []

    timestamp = record.get("renderTimestamp")
    req_id = record.get("reqId")
    render_id = record.get("renderLogId")

    if isinstance(timestamp, str) and isinstance(req_id, str):
        legacy = json.dumps(
            [timestamp, req_id],
            separators=(",", ":")
        )
        keys.append("legacy:" + legacy)

    if isinstance(render_id, str) and render_id:
        keys.append("render:" + render_id)

    return keys


def prepare_database(db):
    # The database was created in the previous migration step.
    db.execute("""
        CREATE TABLE IF NOT EXISTS collector_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    row = db.execute(
        "SELECT value FROM collector_meta "
        "WHERE key = 'needs_reconcile'"
    ).fetchone()

    # Reconcile once after migration, or after an interrupted write.
    if row is None or row[0] == "1":
        indexed = 0

        if OUTPUT.exists():
            with OUTPUT.open(encoding="utf-8") as file:
                for line in file:
                    if not line.strip():
                        continue

                    record = json.loads(line)

                    for key in record_keys(record):
                        db.execute(
                            "INSERT OR IGNORE INTO processed_log_keys "
                            "(key) VALUES (?)",
                            (key,)
                        )
                        indexed += 1

        db.execute("""
            INSERT INTO collector_meta (key, value)
            VALUES ('needs_reconcile', '0')
            ON CONFLICT(key) DO UPDATE SET value = '0'
        """)
        db.commit()

        print("SQLite reconciliation completed.")
        print("Identity keys checked:", indexed)


def already_processed(db, keys):
    for key in keys:
        found = db.execute(
            "SELECT 1 FROM processed_log_keys "
            "WHERE key = ? LIMIT 1",
            (key,)
        ).fetchone()

        if found:
            return True

    return False


def main():
    key = os.environ.get("RENDER_API_KEY")
    if not key:
        key = getpass.getpass("Render API key: ")

    if not DATABASE.is_file():
        raise RuntimeError("SQLite database not found.")

    db = sqlite3.connect(DATABASE, timeout=30)
    db.execute("PRAGMA synchronous=FULL")

    try:
        prepare_database(db)

        now = datetime.now(timezone.utc)
        safe_end = now - timedelta(seconds=20)

        if STATE.exists():
            state = json.loads(STATE.read_text(encoding="utf-8"))
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
        current_keys = set()
        visited = set()
        page_count = 0

        while True:
            page_count += 1

            if page_count > 20:
                raise RuntimeError(
                    "Page limit reached. No logs written."
                )

            marker = (params["startTime"], params["endTime"])
            if marker in visited:
                raise RuntimeError("Repeated pagination cursor.")

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
                    or message.get("service") != PINO_SERVICE
                ):
                    continue

                timestamp = item.get("timestamp")
                req_id = message.get("reqId")
                render_id = item.get("id")

                if not isinstance(timestamp, str):
                    continue
                if not isinstance(req_id, str):
                    continue
                if not isinstance(render_id, str) or not render_id:
                    raise RuntimeError("Render log missing unique ID")

                safe = {
                    "service": PINO_SERVICE,
                    "renderServiceId": SERVICE,
                    "renderTimestamp": timestamp,
                    "renderLogId": render_id,
                }

                for field in ALLOWED:
                    value = message.get(field)
                    if type(value) in (str, int, float):
                        safe[field] = value

                keys = record_keys(safe)

                if any(k in current_keys for k in keys):
                    continue

                if already_processed(db, keys):
                    continue

                current_keys.update(keys)
                collected.append(safe)

            if not data.get("hasMore", False):
                break

            params["startTime"] = data["nextStartTime"]
            params["endTime"] = data["nextEndTime"]

        collected.sort(
            key=lambda record: record["renderTimestamp"]
        )

        if collected:
            # Mark an upcoming file write for crash recovery.
            db.execute("""
                INSERT INTO collector_meta (key, value)
                VALUES ('needs_reconcile', '1')
                ON CONFLICT(key) DO UPDATE SET value = '1'
            """)
            db.commit()

            # Write and flush logs before recording their IDs.
            with OUTPUT.open("a", encoding="utf-8") as file:
                for record in collected:
                    file.write(
                        json.dumps(record, ensure_ascii=False) + "\n"
                    )
                file.flush()
                os.fsync(file.fileno())

            keys_to_save = [
                (key,)
                for record in collected
                for key in record_keys(record)
            ]

            with db:
                db.executemany(
                    "INSERT OR IGNORE INTO processed_log_keys "
                    "(key) VALUES (?)",
                    keys_to_save
                )

                db.execute(
                    "UPDATE collector_meta SET value = '0' "
                    "WHERE key = 'needs_reconcile'"
                )

        # Advance the time cursor only after writing logs and IDs.
        temporary = STATE.with_suffix(".tmp")
        fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o600,
        )

        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(
                {"completedUntil": format_time(end)},
                file
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
            )
        )
        print("Collection completed through:", format_time(end))

    finally:
        db.close()


if __name__ == "__main__":
    main()
