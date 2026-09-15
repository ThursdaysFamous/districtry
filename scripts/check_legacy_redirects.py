#!/usr/bin/env python3
"""Monthly check that the old domain still carries traffic to the new one.

WHY THIS EXISTS. On 2026-09-15, three weeks after the rename, chidistricts.com
still earned 91% of the site's clicks and 79% of its impressions. Every one of
those arrives through a 301 that this project does not serve and cannot see:
the forwarding is configured at the registrar, and the domain is a renewal
somebody has to remember. The SEO audit's phase 0 says "keep chidistricts.com
registered and forwarding for at least a year", and until this script that
sentence was a note in a document — the exact shape of claim this repo has been
bitten by everywhere else, a commitment nothing measures.

If the domain lapses or the forwarding is reconfigured, nothing in the repo
changes, no gate goes red, and the site quietly loses most of its search
traffic. This is the only check that would notice.

WHAT IT CHECKS, and why each is what it is:

  * Every legacy URL Google had indexed WITH IMPRESSIONS still resolves to its
    districtry page with a 200. The list is the redirect map in
    docs/search-baseline/2026-08-24-chidistricts-gsc.md, which is the only
    durable record of what the old property ranked for — a GSC property cannot
    be renamed and its history cannot be moved.
  * The registration expiry, from Verisign's RDAP service, which publishes it
    as JSON. Under a year out is a WARN: the audit asked for at least a year,
    and a renewal is a person's job rather than a script's.

ROBOTS IS ASKED BEFORE EVERY HOST, through scripts/robots_policy.py, which is
the fleet's one reader. Both hosts allow, and both answer in a way worth
recording rather than assuming: chidistricts.com has no robots.txt of its own,
because the path-preserving forwarding sends /robots.txt to
districtry.com/il/robots.txt, which does not exist — a 404, which RFC 9309
files as allow. rdap.verisign.com answers 400, the same allow class, and is an
API serving its data to everyone. A refusal here is reported as a WARN rather
than a FAIL: it means the chain was not checked, not that it is broken.

It never edits anything. Exit codes follow validate_sources.py: 0 for ok or
warn, 1 for a broken chain, with --report and --status-file for the monthly
workflow to fold into its single tracking issue.
"""

import argparse
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robots_policy import RobotsGate            # noqa: E402

# The redirect map, from docs/search-baseline/2026-08-24-chidistricts-gsc.md:
# every old URL Google had indexed with impressions before the move, and where
# it must land now. MEASURED 2026-09-15 — all seven resolve.
#
# One differs from that document and the measurement is what ships: the doc maps
# chidistricts.com/county-board.html to the ROOT /county-board.html stub, and
# the registrar actually forwards it straight to /il/county-board.html, which is
# the real page rather than a meta-refresh shell. Better than documented.
LEGACY = [
    ("https://chidistricts.com/", "https://districtry.com/il/"),
    ("https://chidistricts.com/school-board.html",
     "https://districtry.com/il/school-board.html"),
    ("https://chidistricts.com/police-district.html",
     "https://districtry.com/il/police-district.html"),
    ("https://chidistricts.com/sources.html",
     "https://districtry.com/il/sources.html"),
    ("https://chidistricts.com/county-board.html",
     "https://districtry.com/il/county-board.html"),
    ("https://nyc.chidistricts.com/", "https://districtry.com/ny/"),
    ("https://sf.chidistricts.com/", "https://districtry.com/ca/"),
]

# Registrable domain behind all three hosts above.
DOMAIN = "chidistricts.com"
RDAP = "https://rdap.verisign.com/com/v1/domain/%s"
# The audit asked for "at least a year". Warn inside that.
EXPIRY_WARN_DAYS = 365

# Pages that are 301 TARGETS of URLs still earning impressions on the old
# domain. The audit holds large rewrites on these until the new URLs earn
# impressions of their own: rewriting a page while Google is still deciding
# whether its redirect source and it are the same thing throws away the signal
# the move is meant to transfer. Printed every run so the hold is visible while
# it lasts rather than remembered.
HOLD_REWRITES = [
    ("https://districtry.com/il/", "chidistricts.com/ — 50 clicks, 1,245 impressions pre-move"),
    ("https://districtry.com/il/school-board.html", "chidistricts.com/school-board.html — 65 impressions"),
    ("https://districtry.com/il/police-district.html", "chidistricts.com/police-district.html — 37 impressions"),
]

UA = "districtry-migration-check/1.0 (+https://districtry.com/)"
TIMEOUT = 30


def fetch(url):
    """Follow redirects; return (final_url, status) or (None, reason)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.geturl(), r.status
    except urllib.error.HTTPError as e:
        return e.geturl(), e.code
    except Exception as e:                                  # noqa: BLE001
        return None, type(e).__name__


def expiry_days():
    """Days until DOMAIN expires, or None with a reason."""
    req = urllib.request.Request(RDAP % DOMAIN.upper(),
                                 headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = json.load(r)
    except Exception as e:                                  # noqa: BLE001
        return None, type(e).__name__
    for event in body.get("events", []):
        if event.get("eventAction") == "expiration":
            when = datetime.datetime.fromisoformat(
                event["eventDate"].replace("Z", "+00:00"))
            left = (when - datetime.datetime.now(datetime.timezone.utc)).days
            return left, when.date().isoformat()
    return None, "no expiration event in the RDAP record"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", help="write a markdown report here")
    ap.add_argument("--status-file", help="write ok|warn|fail here")
    ap.add_argument("--offline", action="store_true",
                    help="list the surface and check nothing")
    args = ap.parse_args()

    gate = RobotsGate(None, UA)
    lines, worst = [], "ok"

    def note(level, text):
        nonlocal worst
        order = {"ok": 0, "warn": 1, "fail": 2}
        if order[level] > order[worst]:
            worst = level
        lines.append((level, text))
        print("%-5s %s" % (level.upper(), text))

    if args.offline:
        print("offline — %d legacy URL(s), domain %s, %d page(s) held from "
              "rewrite" % (len(LEGACY), DOMAIN, len(HOLD_REWRITES)))
        for old, new in LEGACY:
            print("  %s -> %s" % (old, new))
        return 0

    for old, expected in LEGACY:
        allowed, why = gate.allows(old)
        if not allowed:
            note("warn", "%s not checked — robots.txt refuses this client (%s)"
                 % (old, why))
            continue
        final, status = fetch(old)
        if final is None:
            note("fail", "%s did not resolve (%s). The old domain carries most "
                         "of the site's search traffic." % (old, status))
        elif status != 200:
            note("fail", "%s ended at HTTP %s (%s)" % (old, status, final))
        elif final.rstrip("/") != expected.rstrip("/"):
            note("fail", "%s now lands on %s, expected %s"
                 % (old, final, expected))
        else:
            note("ok", "%s -> %s" % (old, final))

    rdap_url = RDAP % DOMAIN.upper()
    allowed, why = gate.allows(rdap_url)
    if not allowed:
        note("warn", "registration expiry not checked — RDAP robots.txt "
                     "refuses this client (%s)" % why)
        left, detail = None, "not checked"
    else:
        left, detail = expiry_days()
    if left is None and detail != "not checked":
        note("warn", "could not read %s's expiry from RDAP (%s)"
             % (DOMAIN, detail))
    elif left is None:
        pass
    elif left < EXPIRY_WARN_DAYS:
        note("warn", "%s expires %s, in %d days. The audit asks for at least a "
                     "year; renew it." % (DOMAIN, detail, left))
    else:
        note("ok", "%s registered until %s, %d days out" % (DOMAIN, detail, left))

    print()
    print("Held from rewrite while their redirect sources still earn impressions:")
    for url, why in HOLD_REWRITES:
        print("  %s  (%s)" % (url, why))

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write("## Legacy domain redirects\n\n")
            f.write("`scripts/check_legacy_redirects.py` — the old domain still "
                    "carries most of the site's search traffic, and its "
                    "forwarding and renewal are configured outside this "
                    "repository.\n\n")
            for level, text in lines:
                mark = {"ok": "OK", "warn": "WARN", "fail": "**FAIL**"}[level]
                f.write("- %s — %s\n" % (mark, text))
            f.write("\n**Held from rewrite** while their redirect sources still "
                    "earn impressions (SEO audit, phase 0):\n\n")
            for url, why in HOLD_REWRITES:
                f.write("- `%s` — %s\n" % (url, why))
            f.write("\n")
    if args.status_file:
        with open(args.status_file, "w", encoding="utf-8") as f:
            f.write(worst)

    print("\ncheck-legacy-redirects: %s — %d legacy URL(s) checked"
          % (worst.upper(), len(LEGACY)))
    return 1 if worst == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
