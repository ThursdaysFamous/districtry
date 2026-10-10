#!/usr/bin/env python3
"""
Build data/app/carroll-precinct-polling.json from the Carroll County Clerk's
published polling-place notice.

WHY THIS FILE EXISTS. Carroll's precinct GEOMETRY is served live from
TIGERweb's Census 2020 voting-district layer — the county did not re-precinct
after 2020, so the 22 VTDs ARE the current fabric (the 2026-07-31 validation
pass's 22/22 name match) — but its polling assignment is published only as a
one-page PDF notice from the clerk. This builder downloads the notice,
expands its GROUPED rows ("SAVANNA 1,2,3,4,5 &6" is six precincts sharing one
fire station) against the county's own 22 precinct names, and writes the
small same-origin file the precinct card joins on TIGER's BASENAME.

DETERMINISTIC, NEVER A GUESS: each notice line must begin with one of the 22
known precinct base names (in the notice's own spelling — it writes
"FAIRHAVEN" and "MT.CARROLL" where TIGER writes "FAIR HAVEN" / "MT CARROLL",
an enumerated alias, not a fuzzy match), and the expansion must cover exactly
the 22 known precincts or the build refuses.

POLLING ASSIGNMENTS ARE PER-ELECTION. Re-run when the clerk republishes the
notice; the shipped file carries the fetch date and the card links the
clerk's page as the authority.

Usage:
    python3 build_carroll_precinct_polling.py            # fetch + write
    python3 build_carroll_precinct_polling.py --check    # fetch + compare
"""

import datetime
import io
import json
import os
import re
import sys

import requests
from scraper_common import require_robots_once, make_fail, UA_ROSTER_BOT  # noqa: E402  (shared machinery — do not fork)

try:
    import pypdf
except ImportError:  # pragma: no cover
    pypdf = None

NOTICE_URL = ("https://cms9files.revize.com/carrollil/"
              "NOTICE%20OF%20POLLING%20PLACES%20FOR%20THE.pdf")
# The Clerk's election page on the 2026 site; the old Clerk front page
# (/county_departments/clerk___recorder/index.php) answers 404, measured
# 2026-10-10.
CLERK_PAGE = ("https://www.carrollcountyil.gov/departments/"
              "clerk_recorder/election_information/index.php")
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
}
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "carroll-precinct-polling.json")

# TIGER 2020 BASENAMEs for Carroll's 22 VTDs — the precinct card's join keys,
# verified live against TIGERweb 2026-08-01. Keyed here as (notice spelling ->
# TIGER base, numbered): the notice compresses whitespace and periods.
BASES = [
    ("CHERRY GROVE/SHANNON", "CHERRY GROVE/SHANNON", True),
    ("ELKHORN GROVE", "ELKHORN GROVE", False),
    ("FAIRHAVEN", "FAIR HAVEN", False),
    ("FREEDOM", "FREEDOM", False),
    ("MT.CARROLL", "MT CARROLL", True),
    ("MT. CARROLL", "MT CARROLL", True),
    ("ROCK CREEK/LIMA", "ROCK CREEK/LIMA", True),
    ("SALEM", "SALEM", False),
    ("SAVANNA", "SAVANNA", True),
    ("WASHINGTON", "WASHINGTON", False),
    ("WOODLAND", "WOODLAND", False),
    ("WYSOX", "WYSOX", True),
    ("YORK", "YORK", False),
]
EXPECTED = {
    "CHERRY GROVE/SHANNON 1", "CHERRY GROVE/SHANNON 2", "ELKHORN GROVE",
    "FAIR HAVEN", "FREEDOM", "MT CARROLL 1", "MT CARROLL 2", "MT CARROLL 3",
    "ROCK CREEK/LIMA 1", "ROCK CREEK/LIMA 2", "SALEM", "SAVANNA 1", "SAVANNA 2",
    "SAVANNA 3", "SAVANNA 4", "SAVANNA 5", "SAVANNA 6", "WASHINGTON",
    "WOODLAND", "WYSOX 1", "WYSOX 2", "YORK",
}


fail = make_fail("carroll-precinct-polling")


def clean(value):
    return re.sub(r"\s+", " ", (value or "")).strip().strip(",").strip()


def parse_notice(pdf_bytes):
    if pypdf is None:
        fail("pypdf is required (pip install -c scripts/requirements.txt pypdf)")
    text = " ".join((p.extract_text() or "")
                    for p in pypdf.PdfReader(io.BytesIO(pdf_bytes)).pages)
    text = re.sub(r"\s+", " ", text)
    assignments = {}
    for notice_base, tiger_base, numbered in BASES:
        # Anchor on the notice's own spelling; the numbered groups read
        # "1,2 & 3" / "1 &2" / "1,2,3,4,5 &6" — commas and ampersands only.
        pattern = re.escape(notice_base)
        if numbered:
            pattern += r"\s*((?:\d+\s*[,&]?\s*)+)"
        match = re.search(pattern + r"\s+(.+?)(?=(?:" +
                          "|".join(re.escape(b) for b, _t, _n in BASES) +
                          r")\b|\*PLEASE|THE POLLS|$)", text)
        if not match:
            continue
        if numbered:
            nums = re.findall(r"\d+", match.group(1))
            location = clean(match.group(2))
            names = ["%s %s" % (tiger_base, n) for n in nums]
        else:
            location = clean(match.group(1))
            names = [tiger_base]
        parts = location.split(",", 1)
        entry = {"place": clean(parts[0])}
        if len(parts) > 1 and clean(parts[1]):
            entry["address"] = clean(parts[1])
        for name in names:
            # "MT. CARROLL" and "MT.CARROLL" both anchor the same rows; the
            # first spelling that matched wins and a re-match is identical.
            assignments.setdefault(name, entry)
    return assignments


def main():
    check = "--check" in sys.argv
    require_robots_once(NOTICE_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-carroll-precinct-polling")
    resp = requests.get(NOTICE_URL, headers=HEADERS, timeout=120)
    resp.raise_for_status()
    if not resp.content.startswith(b"%PDF"):
        fail("the notice URL did not return a PDF")
    assignments = parse_notice(resp.content)

    got = set(assignments)
    if got != EXPECTED:
        missing = sorted(EXPECTED - got)
        extra = sorted(got - EXPECTED)
        fail("expansion does not cover the county's 22 precincts exactly — "
             "missing %s, unexpected %s (the notice's wording changed; update "
             "BASES)" % (missing, extra))

    payload = {
        "source": NOTICE_URL,
        "sourcePage": CLERK_PAGE,
        "fetched": datetime.date.today().isoformat(),
        "precincts": dict(sorted(assignments.items())),
    }
    body = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"

    if check:
        if not os.path.exists(OUT_PATH):
            fail("--check: %s does not exist" % os.path.relpath(OUT_PATH, REPO_ROOT))
        shipped = json.load(open(OUT_PATH, encoding="utf-8"))
        if shipped.get("precincts") != payload["precincts"]:
            fail("--check: the clerk's notice no longer matches the shipped file — "
                 "re-run this builder and review the diff")
        print("carroll-precinct-polling: OK — shipped file matches the notice "
              "(22 precincts)")
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(body)
    print("carroll-precinct-polling: wrote %s — %d precincts"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), len(assignments)))


if __name__ == "__main__":
    main()
