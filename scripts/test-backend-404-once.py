#!/usr/bin/env python3
"""Send at most twenty sequential GET requests to the MatchWise backend.
Expected response is 404. No credentials, retries, redirects or data writes.
This creates real HTTP logs and can trigger the real HTTP 404 burst alert.
"""
import time
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener
import uuid

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def main():
    target = "https://matchwise-backend-monitoring-test.onrender.com/.well-known/matchwise-monitoring-404-test-" + uuid.uuid4().hex
    opener = build_opener(NoRedirect())
    start = time.monotonic()
    print("Target:", target, flush=True)
    for number in range(1, 21):
        remaining = 90 - (time.monotonic() - start)
        if remaining <= 0:
            print("Stopped: test took too long. Do not automatically repeat.")
            return 1
        request = Request(target, headers={"User-Agent": "MatchWise-Monitoring-404-Test/1"})
        try:
            with opener.open(request, timeout=min(10, remaining)) as response:
                status = response.status
        except HTTPError as error:
            status = error.code
            error.close()
        except Exception as error:
            print("Stopped:", type(error).__name__, "(details hidden)")
            return 1
        print(f"{number}/20 HTTP {status}", flush=True)
        if status != 404:
            print("Stopped: expected 404. Do not automatically repeat.")
            return 1
        time.sleep(0.25)
    print("Twenty HTTP 404 responses confirmed. No more requests will be sent.")
    print("Observe the production rule and Telegram. Do not repeat before recovery.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
