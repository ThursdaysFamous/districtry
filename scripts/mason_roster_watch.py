#!/usr/bin/env python3
"""
Watch Mason County's board roster PDF for change, so a hand-transcribed roster
does not quietly go stale.

WHY A WATCHER AND NOT A SCRAPER. Mason's roster is a SCAN with a broken text
layer — extraction returns line noise, not text, so a scraper would ship
confident garbage under real officeholders' names (the reasoning is in
scripts/build_mason_board_roster.py). The roster is therefore transcribed by
hand. What can still be automated is noticing that the source moved, which is
the failure this county is actually exposed to: a transcription is only as
current as the document it was read from, and nothing else in the pipeline
would ever say otherwise.

TWO CHECKS, IN THIS ORDER — the first is the one that matters:

  1. THE PAGE STILL LINKS THIS PDF. Mason publishes through WordPress, so a new
     roster lands at a new upload path (/2026/05/... -> /2027/xx/...) and the
     OLD url keeps serving the OLD file with a 200 forever. Hashing alone would
     never see that; this is the same supersession failure validate_sources.py
     exists for.
  2. THE BYTES STILL MATCH. Catches a same-path replacement.

DELIBERATELY NOISY. A re-export of the identical scan changes the bytes and
trips check 2 with no real change behind it. That direction is the right one to
err in: a false alarm costs one person one minute, a missed roster change ships
a wrong officeholder until someone happens to notice.

It never edits anything. A scan cannot be re-read automatically, so a change is
a request for a human, not a diff.

Usage:
    python3 scripts/mason_roster_watch.py            # exit 0 unchanged, 2 changed
    python3 scripts/mason_roster_watch.py --record   # print the current fingerprint
"""

import argparse
import hashlib
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_CHROME_X11_128,
    require_robots_once,
)

BOARD_PAGE = "https://masoncountyil.gov/county-board/"
ROSTER_PDF = ("https://masoncountyil.gov/wp-content/uploads/2026/05/"
              "Board-Members-.pdf")
# sha256 of the PDF as read 2026-08-02, the transcription in
# scripts/build_mason_board_roster.py.
KNOWN_SHA256 = "a1d1e96af9d4f3e8548be133639be370f1fa2e385c9edd3da24797c99632c551"
UA = {"User-Agent": UA_CHROME_X11_128}
TIMEOUT = 90

# What the county-board page calls the link, used only to report a rename.
LINK_TEXT = "County Board Members"


def get(url):
    require_robots_once(url, UA["User-Agent"], headers=UA,
                        label="il-mason-roster-watch")
    resp = requests.get(url, headers=UA, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true",
                    help="print the live fingerprint instead of comparing")
    args = ap.parse_args()

    pdf = get(ROSTER_PDF)
    if not pdf.content.startswith(b"%PDF"):
        print("mason-roster-watch: FAIL — %s no longer returns a PDF (%d bytes of %s)"
              % (ROSTER_PDF, len(pdf.content), pdf.headers.get("content-type")),
              file=sys.stderr)
        sys.exit(1)
    digest = hashlib.sha256(pdf.content).hexdigest()

    if args.record:
        print(digest)
        return

    page = get(BOARD_PAGE).text
    linked = sorted(set(re.findall(r'href="([^"]*\.pdf)"', page, re.I)))
    still_linked = ROSTER_PDF in linked

    problems = []
    if not still_linked:
        others = [u for u in linked if "board" in u.lower() or "member" in u.lower()]
        problems.append(
            "the county board page NO LONGER LINKS the transcribed PDF. It links "
            "%s. A superseded roster lands at a new upload path while the old URL "
            "keeps serving the old file, so this is the change that matters: "
            "re-read the new document and update "
            "scripts/build_mason_board_roster.py."
            % (", ".join(others or linked) or "no PDF at all"))
    if digest != KNOWN_SHA256:
        problems.append(
            "the PDF's bytes CHANGED (sha256 %s, recorded %s). This can be a "
            "harmless re-export of the same scan — compare the document against "
            "the table in scripts/build_mason_board_roster.py, then update "
            "KNOWN_SHA256 here either way." % (digest[:16], KNOWN_SHA256[:16]))

    if problems:
        for p in problems:
            print("mason-roster-watch: CHANGED — %s" % p)
        sys.exit(2)

    print("mason-roster-watch: OK — %s still links the transcribed PDF (%r) and its "
          "bytes are unchanged (sha256 %s)" % (BOARD_PAGE, LINK_TEXT, digest[:16]))


if __name__ == "__main__":
    main()
