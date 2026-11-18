#!/usr/bin/env python3
"""Read-only Render metrics probe. No files changed; no credentials printed.
HU: Csak olvasasi ellenorzes. A kulcs rejtve kerul beolvasasra.
Run: python3 probe-render-metrics.py
"""
import getpass
import json
import re
import warnings
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def summary(value, depth=0):
    if depth > 6:
        return "<depth limit>"
    if isinstance(value, dict):
        return {str(k): summary(v, depth + 1) for k, v in list(value.items())[:16]}
    if isinstance(value, list):
        return {"count": len(value), "last_item": summary(value[-1], depth + 1) if value else None}
    if isinstance(value, str):
        # Keep dates and numeric strings only. Identifiers and other text are hidden.
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}T[0-9:.+Z-]+", value):
            return value
        if re.fullmatch(r"-?\d+(\.\d+)?([eE][+-]?\d+)?", value):
            return value
        return "<text hidden>"
    return value

def main():
    service = input("Render service ID (srv-...): ").strip()
    if not re.fullmatch(r"srv-[a-zA-Z0-9-]+", service):
        raise SystemExit("Invalid service ID.")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        key = getpass.getpass("Render API key (hidden, not saved): ").strip()
    if not key:
        raise SystemExit("API key required.")
    opener = build_opener(NoRedirect())
    query = urlencode({"resource": service, "resolutionSeconds": 60})
    for endpoint in ("cpu", "memory", "cpu-limit", "memory-limit"):
        url = "https://api.render.com/v1/metrics/" + endpoint + "?" + query
        request = Request(url, headers={"Authorization": "Bearer " + key, "Accept": "application/json"})
        try:
            with opener.open(request, timeout=30) as response:
                payload = response.read(2000001)
                if len(payload) > 2000000:
                    print(endpoint + ": response too large")
                    continue
                data = json.loads(payload)
                print(endpoint + ": HTTP " + str(response.status))
                print(json.dumps(summary(data), indent=2))
        except HTTPError as exc:
            print(endpoint + ": HTTP " + str(exc.code) + " (response body hidden)")
        except Exception as exc:
            print(endpoint + ": " + type(exc).__name__ + " (details hidden)")
    print("Finished. HTTP 200 with an empty list is not proof of usable metrics.")

if __name__ == "__main__":
    main()
