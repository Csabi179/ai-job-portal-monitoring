#!/usr/bin/env python3
"""Read-only datasource preflight. No rules installed and no application traffic generated."""
import argparse
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

def execute(source, expr, logs=False):
    if source == "prometheus":
        base = "http://127.0.0.1:9090/api/v1/query"
    else:
        base = "http://127.0.0.1:3100/loki/api/v1/" + ("query_range" if logs else "query")
    params = {"query": expr}
    if logs:
        now = time.time_ns()
        params.update(start=now - 300_000_000_000, end=now, limit=5)
    with urlopen(base + "?" + urlencode(params), timeout=30) as response:
        result = json.load(response)
    if result.get("status") != "success":
        raise ValueError("Query did not succeed")
    return result["data"]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rules", type=Path)
    parser.add_argument("--dashboard", type=Path)
    args = parser.parse_args()
    tasks = []
    for group in json.loads(args.rules.read_text(encoding="utf-8"))["groups"]:
        for rule in group["rules"]:
            for query in rule["data"]:
                if query["datasourceUid"] in ("prometheus", "loki"):
                    tasks.append((rule["uid"] + " " + query["refId"], query["datasourceUid"],
                                  query["model"]["expr"], False, True))
    if args.dashboard:
        dashboard = json.loads(args.dashboard.read_text(encoding="utf-8"))
        for panel in dashboard["panels"]:
            if panel.get("datasource", {}).get("type") != "loki":
                continue
            for query in panel.get("targets", []):
                tasks.append((panel["title"] + " " + query["refId"], "loki",
                              query["expr"], panel["type"] == "logs", False))
    failed = False
    for name, source, expr, logs, required in tasks:
        try:
            data = execute(source, expr, logs)
            values = data["result"]
            # Do not print raw application log contents or URLs from error bodies.
            sample_values = [item["value"][1] for item in values if "value" in item]
            print(name, "OK", "series=" + str(len(values)), "values=" + json.dumps(sample_values[:8]))
            if not values:
                print("  No matching traffic/logs or unavailable telemetry.")
                if required:
                    failed = True
        except Exception as error:
            status = " HTTP " + str(error.code) if isinstance(error, HTTPError) else ""
            print(name, "FAILED", type(error).__name__ + status)
            failed = True
    return int(failed)

if __name__ == "__main__":
    raise SystemExit(main())
