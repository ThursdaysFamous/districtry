"""
Offline proof of scraper_common.fetch()'s retry semantics.

The fleet's scrapers can only be proven against their real sites by their
weekly runs, so the shared fetch's CONTRACT is proven here instead, against a
localhost stub that scripts each failure shape the henry rules exist for:

  1. 429 with numeric Retry-After -> retried after that many seconds, then OK
  2. 5xx -> retried on the 2*(attempt+1) backoff, then OK
  3. 429 with a hostile Retry-After (9999) -> delay capped at retry_after_cap
  4. 403 -> raises immediately, exactly one request made
  5. 404 -> raises immediately, exactly one request made
  6. permanent 500 -> RuntimeError after exactly `attempts` requests

Run it directly (needs `requests`, talks only to 127.0.0.1):

    python3 scripts/selftest_scraper_common.py

It is not wired into CI — the module's consumers exercise fetch() weekly, and
this exists so a change to scraper_common.py can be proven without touching a
county's site. Re-run it whenever fetch() changes.

NOT GATED ON robots.txt: IT TALKS ONLY TO ITS OWN SERVER. The one host this
reaches is 127.0.0.1, an HTTP server this file starts a few lines earlier to
serve its own fixtures, so a robots read would be this file asking itself for
permission. A loopback address is never somebody's site -- the same reason
probe_user_agents.py skips it -- and the whole point of the fixture is to prove
fetch() without touching a county's server.

THE TEST IS WHOSE SITE, never which client. If this ever fetched a real host,
it would be gated in full.
"""
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scraper_common  # noqa: E402

SCRIPTS = {
    "/retry-after": [(429, {"Retry-After": "1"}), (200, {})],
    "/backoff-5xx": [(500, {}), (503, {}), (200, {})],
    "/hostile-cap": [(429, {"Retry-After": "9999"}), (200, {})],
    "/forbidden": [(403, {})],
    "/missing": [(404, {})],
    "/always-500": [(500, {})] * 99,
}
HITS = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        n = HITS.get(self.path, 0)
        HITS[self.path] = n + 1
        script = SCRIPTS[self.path]
        status, headers = script[min(n, len(script) - 1)]
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


def expect(cond, label):
    if not cond:
        print("selftest-scraper-common: FAIL — %s" % label, file=sys.stderr)
        sys.exit(1)
    print("  ok: %s" % label)


def main():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % server.server_port
    ua = {"User-Agent": scraper_common.UA_ROSTER_COMPACT}

    t0 = time.monotonic()
    resp = scraper_common.fetch(base + "/retry-after", ua)
    expect(resp.status_code == 200 and HITS["/retry-after"] == 2,
           "429 + Retry-After: 1 retried once then succeeded")
    expect(time.monotonic() - t0 >= 1.0, "numeric Retry-After was honoured (>=1s)")

    resp = scraper_common.fetch(base + "/backoff-5xx", ua)
    expect(resp.status_code == 200 and HITS["/backoff-5xx"] == 3,
           "500 then 503 retried on backoff then succeeded")

    t0 = time.monotonic()
    resp = scraper_common.fetch(base + "/hostile-cap", ua, retry_after_cap=2.0)
    expect(resp.status_code == 200 and time.monotonic() - t0 < 5.0,
           "hostile Retry-After: 9999 capped at retry_after_cap")

    import requests
    for path, code in (("/forbidden", 403), ("/missing", 404)):
        try:
            scraper_common.fetch(base + path, ua)
        except requests.RequestException as exc:
            expect(exc.response.status_code == code and HITS[path] == 1,
                   "%d raised immediately after exactly one request" % code)
        else:
            expect(False, "%d did not raise" % code)

    try:
        scraper_common.fetch(base + "/always-500", ua, attempts=3)
    except RuntimeError as exc:
        expect("after 3 attempts" in str(exc) and HITS["/always-500"] == 3,
               "permanent 500 exhausted exactly `attempts` requests")
    else:
        expect(False, "permanent 500 did not raise RuntimeError")

    fail = scraper_common.make_fail("selftest-label")
    try:
        fail("boom")
    except SystemExit as exc:
        expect(exc.code == 1, "make_fail exits 1 (label output checked by eye above)")

    server.shutdown()
    print("selftest-scraper-common: OK — all fetch() semantics hold")


if __name__ == "__main__":
    main()
