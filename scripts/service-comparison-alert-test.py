#!/usr/bin/env python3
"""Generate temporary Grafana alert fixtures. No network or service changes."""
import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time

IDS = {
    "matchwise_backend_cpu_high": "mw_test_cpu_flow",
    "matchwise_backend_5xx_burst": "mw_test_5xx_flow",
    "matchwise_backend_login_burst": "mw_test_login_flow",
}

def build(source, now):
    rules = [r for g in source["groups"] for r in g["rules"] if r["uid"] in IDS]
    if len(rules) != 3 or len({r["uid"] for r in rules}) != 3:
        raise ValueError("Expected the three distinct service comparison rules")
    start = int(now) + 120
    end = start + 720
    pulse = f"vector((time() >= bool {start}) * (time() < bool {end}))"
    result = []
    for original in rules:
        rule = copy.deepcopy(original)
        rule["uid"] = IDS[original["uid"]]
        rule["title"] = "TEST | " + original["title"]
        rule["annotations"] = {
            "summary": rule["title"],
            "description": "Controlled test with a synthetic value. No real backend failure or attack. Automatically clears after the test window.",
            "runbook_url": "https://github.com/Csabi179/ai-job-portal-monitoring/blob/feat/service-comparison/docs/SERVICE_COMPARISON_ALERT_TEST.md",
        }
        rule["labels"].update(category="security_test", test="true")
        rule["isPaused"] = False
        # Retain the real expression graph and pending duration.
        # Substitute only datasource inputs, including the monitoring gate.
        for query in rule["data"]:
            if query["datasourceUid"] == "__expr__":
                continue
            ref = query["refId"]
            if ref not in ("A", "D"):
                raise ValueError("Unexpected datasource input")
            query.clear()
            query.update(refId=ref, datasourceUid="prometheus",
                         relativeTimeRange={"from": 300, "to": 0},
                         model={"datasource": {"type": "prometheus", "uid": "prometheus"},
                                "editorMode": "code", "expr": pulse if ref == "A" else "vector(1)",
                                "instant": True, "range": False, "refId": ref,
                                "intervalMs": 1000, "maxDataPoints": 43200})
        result.append(rule)
    return {"apiVersion": 1, "groups": [{"orgId": 1, "name": "service-comparison-test",
             "folder": "AI Job Portal", "interval": "1m", "rules": result}]}, start, end

def cleanup():
    return {"apiVersion": 1, "deleteRules": [{"orgId": 1, "uid": uid} for uid in IDS.values()]}

def write_json(path, value):
    # Same-directory replace avoids publishing a partially written provisioning file.
    fd, temporary = tempfile.mkstemp(prefix=".alert-test-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["generate", "cleanup"])
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.source and args.source.resolve() == args.output.resolve():
        parser.error("Source and output must be different")
    if args.action == "generate":
        if not args.source:
            parser.error("generate requires --source")
        value, start, end = build(json.loads(args.source.read_text(encoding="utf-8")), time.time())
        write_json(args.output, value)
        for label, stamp in [("Test condition starts (UTC)", start), ("Automatically clears (UTC)", end)]:
            print(label + ": " + datetime.fromtimestamp(stamp, timezone.utc).isoformat())
    else:
        write_json(args.output, cleanup())
    print("Written:", args.output)
    print("No services changed. Install this file and reload/restart Grafana separately.")

if __name__ == "__main__":
    main()
