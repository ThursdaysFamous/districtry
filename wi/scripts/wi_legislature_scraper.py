#!/usr/bin/env python3
"""
Scrape the Wisconsin Legislature's own per-chamber pages for the office
fields Open States cannot supply. Companion to build_wi_legislature_roster.py,
which merges this enrichment onto its Open States base.

WHY THIS EXISTS (measured 2026-08-25): the Open States wi.csv carries
capitol_address / capitol_voice filled for 0 of 132 Wisconsin members — the
upstream YAML has no offices block for them — while the Legislature's own
index pages (docs.legis.wisconsin.gov/2025/legislators/{assembly,senate})
carry every member in a district-id-keyed block with the Madison office room,
one or two telephones, fax and e-mail. Two fetches cover all 132.

THE URL IS SESSION-SCOPED AND THE UNVERSIONED PATH 404s: /2025/ is the
2025-26 biennium, and the path must be bumped each odd-year January
(WATCH.md row) or this scraper silently reads a frozen roster. The floors
below are the tripwire for a page reshape; the biennium bump is a calendar
fact no floor can catch.

TWO FIELDS ARE REFUSED BY CONSTRUCTION, not filtered afterwards: each block
carries the member's **Voting Address** — their HOME address — and their
staff's names and mailboxes. Neither is read; the parser walks only the
Madison Office / Telephone / Fax / Email spans, and the builder asserts on
the merged payload that no voting-address line survived (the fleet's
Boone/Mason rule: refuse residences structurally, then prove it).
"""

import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(SCRIPT_DIR, ".cache", "wi_legislature_offices.json")

BIENNIUM = "2025"  # bump each odd-year January — see WATCH.md
BASE = "https://docs.legis.wisconsin.gov/%s/legislators/" % BIENNIUM
CHAMBERS = {"senate": 31, "assembly": 94}  # min district blocks (floors match the builder's)

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
}


# ONE UNRETRIED TIMEOUT FREEZES THE ROSTER FOR A WEEK, measured 2026-09-24.
# Run 35762232826 (2026-09-22, scheduled) died after 61s on
# `urllib.error.URLError: <urlopen error timed out>` — one attempt, no retry —
# so steps 5-8 were skipped, no PR opened, and wi/data/app kept its 15
# September names until somebody noticed. Dispatched by hand two days later the
# same job finished in 23 SECONDS, which is what makes this transient rather
# than a refusal: docs.legis.wisconsin.gov is a host CLAUDE.md already records
# as intermittent from some vantages.
#
# THE POLICY IS scripts/scraper_common.fetch's, NOT A SECOND ANSWER TO ITS
# QUESTION: retry a timeout, a transport error, a 429 and a 5xx; never retry
# 401/403/404, because a moved or refused page is not fixed by waiting. It is
# reimplemented here rather than imported because wi/scripts has no path to
# that module (wi_wec_probe.py records the same) and this workflow installs no
# pip dependencies at all — that helper needs `requests`, and adding a
# dependency to make a retry available is a larger change than the retry.
ATTEMPTS = 4
TIMEOUT = 60


def fetch(url, attempts=ATTEMPTS, opener=None):
    """`opener` exists so selftest() can drive this with a stub transport.

    It is an argument rather than a monkeypatch because the alternative is a
    test that reaches into the module, replaces a name, and has to remember to
    put it back — and the one that forgets leaves every later call stubbed.
    """
    opener = opener or urllib.request.urlopen
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers=UA)
    last = None
    for attempt in range(attempts):
        try:
            with opener(req, timeout=TIMEOUT, context=ctx) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403, 404):
                raise
            last = "HTTP %d" % exc.code
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = "%s: %s" % (type(exc).__name__, exc)
        if attempt + 1 < attempts:
            # Linear, like the shared helper's: the failure this guards is a
            # host that hung for a full minute, and an exponential curve would
            # spend the job's time waiting rather than asking again.
            time.sleep(2.0 * (attempt + 1))
    raise SystemExit("failed to fetch %s after %d attempt(s): %s"
                     % (url, attempts, last))



def selftest():
    """Six cases for the retry, each asserting HOW MANY attempts it made.

    The ordering of the two except clauses is load-bearing and invisible:
    HTTPError SUBCLASSES URLError, so catching URLError first would retry a 404
    four times and turn a moved page into four minutes of waiting. Cases 4 and
    5 are what hold that ordering in place.
    """
    class Resp(object):
        def __init__(self, body): self.body = body.encode()
        def read(self): return self.body
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def stub(script, seen):
        def opener(req, timeout=None, context=None):
            outcome = script[min(seen[0], len(script) - 1)]
            seen[0] += 1
            if isinstance(outcome, Exception):
                raise outcome
            return Resp(outcome)
        return opener

    real_sleep, bad = time.sleep, []
    time.sleep = lambda _s: None                     # the cases are about counts
    try:
        def run(label, script, expect_ok, expect_calls):
            seen = [0]
            try:
                # BASE, never a fabricated host: probe_user_agents.py reads URL
                # literals out of this file and this one sends a browser string, so
                # an invented address here FAILS its check as an unmeasured host.
                # Nothing is fetched — the stub opener answers every call.
                got = fetch(BASE, opener=stub(script, seen))
                ok = expect_ok and got == "PAGE"
            except SystemExit:
                ok = not expect_ok
            except urllib.error.HTTPError:
                ok = not expect_ok
            if not ok or seen[0] != expect_calls:
                bad.append("%s: %d attempt(s), wanted %d" % (label, seen[0], expect_calls))

        timeout = urllib.error.URLError("<urlopen error timed out>")
        http = lambda code: urllib.error.HTTPError("u", code, "x", {}, None)
        # The real failure: run 35762232826 timed out once and the next
        # dispatch answered in 23 seconds.
        run("timeout then success", [timeout, "PAGE"], True, 2)
        run("three timeouts then success", [timeout, timeout, timeout, "PAGE"], True, 4)
        run("host never answers", [timeout], False, ATTEMPTS)
        run("404 raises immediately", [http(404)], False, 1)
        run("403 raises immediately", [http(403)], False, 1)
        run("503 is retried", [http(503), "PAGE"], True, 2)
    finally:
        time.sleep = real_sleep
    if bad:
        for line in bad:
            print("  FAIL %s" % line)
        raise SystemExit("selftest: %d retry case(s) wrong" % len(bad))
    print("selftest: 6 retry case(s), 0 failures")


def strip_tags(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def span_lines(block, cls):
    m = re.search(r"<span class='info %s'>.*?</span>\s*(.*?)</span>" % cls, block, re.S)
    if not m:
        return []
    return [strip_tags(x) for x in re.split(r"<br\s*/?>", m.group(1)) if strip_tags(x)]


def parse_chamber(html):
    out = {}
    blocks = re.split(r'id="district(\d+)"', html)
    for i in range(1, len(blocks) - 1, 2):
        district = str(int(blocks[i]))
        body = blocks[i + 1]
        entry = {}
        m = re.search(r'<strong><a href="(http[^"]+)">', body)
        if m:
            entry["url"] = m.group(1)
        office = span_lines(body, "office")
        if office:
            entry["capitolOffice"] = office
        phones = span_lines(body, "telephone")
        if phones:
            entry["phones"] = phones
        fax = span_lines(body, "fax")
        if fax:
            entry["fax"] = fax[0]
        m = re.search(r'<span class=\'info email\'>.*?mailto:([^"]+)"', body, re.S)
        if m:
            entry["email"] = m.group(1)
        out[district] = entry
    return out


def main():
    # On every run, not behind a flag nothing calls: it is milliseconds and
    # the weekly job is the witness that the retry still behaves.
    selftest()
    if "--selftest" in sys.argv[1:]:
        return
    argv = sys.argv[1:]
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT

    payload = {}
    for chamber, floor in CHAMBERS.items():
        parsed = parse_chamber(fetch(BASE + chamber))
        if len(parsed) < floor:
            raise SystemExit("%s page yielded %d district blocks (floor %d) — the page "
                             "reshaped, or the biennium constant needs its bump"
                             % (chamber, len(parsed), floor))
        with_email = sum(1 for e in parsed.values() if e.get("email"))
        if with_email < floor - 3:
            raise SystemExit("%s page yielded only %d e-mails over %d blocks — the "
                             "mailto pattern moved" % (chamber, with_email, len(parsed)))
        payload[chamber] = parsed

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("scraped offices: senate %d, assembly %d -> %s"
          % (len(payload["senate"]), len(payload["assembly"]), out_path))


if __name__ == "__main__":
    main()
