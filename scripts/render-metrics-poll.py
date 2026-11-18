#!/usr/bin/env python3
"""Render metrics -> Node Exporter textfile. Standard library only.

Requires RENDER_API_KEY and RENDER_SERVICE_ID. Default mode prints metrics only.
--write atomically publishes a .prom file. Never prints API response bodies.
"""
import argparse
from datetime import datetime, timezone, timedelta
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPRedirectHandler

ENDPOINTS = {"cpu": "cpu", "cpu-limit": "cpu", "memory": "bytes", "memory-limit": "bytes"}

class MetricsHTTPError(Exception):
    """Only trusted endpoint names and numeric status codes may be displayed."""
    def __init__(self, endpoint, status):
        self.endpoint = endpoint
        self.status = int(status)
        super().__init__(f"{endpoint}: HTTP {self.status} (response body hidden)")

def failure_message(exc):
    return str(exc) if isinstance(exc, MetricsHTTPError) else type(exc).__name__

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def samples(payload, unit, service, now):
    # Initial deployment deliberately supports one active instance only.
    # Reject multi-series results rather than accidentally double-count a deployment.
    if not isinstance(payload, list) or len(payload) != 1:
        raise ValueError("Expected exactly one metric series")
    series = payload[0]
    if series.get("unit") != unit:
        raise ValueError("Unexpected unit")
    labels = {item["field"]: item["value"] for item in series.get("labels", [])}
    if labels.get("resource", labels.get("service")) != service:
        raise ValueError("Resource mismatch")
    result = {}
    for item in series.get("values", []):
        stamp = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("Timestamp has no timezone")
        epoch = stamp.timestamp()
        raw = item["value"]
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError("Non-numeric metric")
        if not math.isfinite(raw) or raw < 0:
            raise ValueError("Invalid metric")
        if epoch > now + 30:
            raise ValueError("Future metric")
        if epoch in result:
            raise ValueError("Duplicate timestamp")
        result[epoch] = float(raw)
    return labels.get("instance"), result

def calculate(payloads, service, now):
    parsed = {name: samples(payloads[name], unit, service, now) for name, unit in ENDPOINTS.items()}
    instances = {item[0] for item in parsed.values()}
    if None in instances or len(instances) != 1:
        raise ValueError("Instance mismatch or missing instance")
    common = set.intersection(*(set(item[1]) for item in parsed.values()))
    if not common:
        raise ValueError("No common timestamp")
    stamp = max(common)
    if now - stamp > 300:
        raise ValueError("Source metrics are stale")
    values = {name: item[1][stamp] for name, item in parsed.items()}
    if values["cpu-limit"] <= 0 or values["memory-limit"] <= 0:
        raise ValueError("Invalid capacity limit")
    return {
        "matchwise_render_cpu_used": values["cpu"],
        "matchwise_render_cpu_limit": values["cpu-limit"],
        "matchwise_render_cpu_utilization_percent": 100 * values["cpu"] / values["cpu-limit"],
        "matchwise_render_memory_used_bytes": values["memory"],
        "matchwise_render_memory_limit_bytes": values["memory-limit"],
        "matchwise_render_memory_utilization_percent": 100 * values["memory"] / values["memory-limit"],
        "matchwise_render_metrics_source_timestamp_seconds": stamp,
    }

def render(metrics, service):
    lines = []
    for name, value in sorted(metrics.items()):
        lines.extend([f"# TYPE {name} gauge", f'{name}{{service="matchwise_backend",resource="{service}"}} {value:.12g}'])
    return "\n".join(lines) + "\n"

def publish(path, content):
    # Parent must be deliberately created by the operator.
    fd, tmp = tempfile.mkstemp(prefix=".render-metrics-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def collect(key, service):
    now = datetime.now(timezone.utc)
    query = urlencode({"resource": service, "resolutionSeconds": 60,
                       "startTime": (now - timedelta(minutes=10)).isoformat(), "endTime": now.isoformat()})
    opener = build_opener(NoRedirect())
    payloads = {}
    for name in ENDPOINTS:
        request = Request("https://api.render.com/v1/metrics/" + name + "?" + query,
                          headers={"Authorization": "Bearer " + key, "Accept": "application/json"})
        try:
            with opener.open(request, timeout=20) as response:
                body = response.read(2000001)
                if len(body) > 2000000:
                    raise ValueError("Oversized response")
                payloads[name] = json.loads(body)
        except HTTPError as exc:
            raise MetricsHTTPError(name, exc.code) from None
    return calculate(payloads, service, time.time())

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=Path.home() / "monitoring-exporter-metrics/matchwise_render_resources.prom")
    args = parser.parse_args()
    service = os.environ.get("RENDER_SERVICE_ID", "")
    key = os.environ.get("RENDER_API_KEY", "")
    if not re.fullmatch(r"srv-[A-Za-z0-9-]+", service) or not key:
        parser.error("Valid RENDER_SERVICE_ID and RENDER_API_KEY are required")
    if args.write and args.output.suffix != ".prom":
        parser.error("Output must have .prom extension")
    try:
        metrics = collect(key, service)
        metrics["matchwise_render_metrics_collection_success"] = 1
        metrics["matchwise_render_metrics_last_success_timestamp_seconds"] = time.time()
        exit_code = 0
    except Exception as exc:
        # Replace old resource data with explicit failure; do not present old usage as fresh.
        metrics = {"matchwise_render_metrics_collection_success": 0}
        print("Collection failed: " + failure_message(exc), file=__import__("sys").stderr)
        exit_code = 1
    metrics["matchwise_render_metrics_last_attempt_timestamp_seconds"] = time.time()
    output = render(metrics, service)
    if args.write:
        publish(args.output, output)
    else:
        print(output, end="")
    return exit_code

if __name__ == "__main__":
    raise SystemExit(main())

