#!/usr/bin/env python3
"""
Build data/app/hamilton-precinct-polling.json from the Hamilton County Clerk's
published polling-place notice.

WHY THIS FILE EXISTS. Hamilton's precinct GEOMETRY is served live from the
county's own vendor-hosted org (Voter_Precincts_Hamilton), but that layer
carries exactly one attribute — the precinct name — and the county publishes
no polling layer. The pairing lived only in correspondence with Clerk Bowman
(13 locations confirmed, the McLeansboro gym confirmed, the FY 2017 map
confirmed current) until the county's post-migration website published the
statutory election notice itself: "Polling Places and Addresses — 03-17-2026
General Primary Election", a one-page PDF listing all SIXTEEN precincts with
their polling place and street address. That notice is the election
authority's own per-election word — it settles the Dahlgren #1/#2 pairing the
2026-08-05 georeferencing pass measured as unguessable (both markers ~0.3 mi
coarse in the same polygon), and it re-confirms all four McLeansboro precincts
at the Old Highschool Gym.

DETERMINISTIC, NEVER A GUESS: every notice row must begin with one of the 16
known precinct labels (in the notice's own spelling — it writes "Dahlgren #1"
where the GIS writes "DAHLGREN 1", a fixed transform, not a fuzzy match), the
address split is place-text / first-digit-run street / ", IL zip" city, and
the parse must cover exactly the 16 known precincts or the build refuses. The
13-distinct-locations count the Clerk confirmed in writing is asserted too.

POLLING ASSIGNMENTS ARE PER-ELECTION. Re-run when the clerk republishes the
notice (the shipped file names the election it was published for, and the
card labels the row with it); the clerk's page stays the linked authority.

Usage:
    python3 build_hamilton_precinct_polling.py            # fetch + write
    python3 build_hamilton_precinct_polling.py --check    # fetch + compare
"""

import datetime
import io
import json
import os
import re
import sys

import requests
from scraper_common import require_robots_once, make_fail, UA_CHROME_WIN_126  # noqa: E402  (shared machinery — do not fork)

try:
    import pypdf
except ImportError:  # pragma: no cover
    pypdf = None

NOTICE_URL = ("https://cms.hamiltoncountyil.gov/app/uploads/2026/02/"
              "03-17-2026-GPE-Polling-Places-Addresses.pdf")
NOTICE_PAGE = ("https://www.hamiltoncountyil.gov/election-notices/"
               "polling-places-and-addresses-03-17-2026-general-primary-election/")
ELECTION = "March 17, 2026 General Primary"
HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
}
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "hamilton-precinct-polling.json")

# The 16 notice labels, longest-first so "South Crouch" never matches as
# "Crouch". The GIS join key is the label uppercased with "#" dropped —
# exactly how Voter_Precincts_Hamilton spells its Precinct_Name (the layer's
# one attribute; its "MCLEANSBORO 4 " trailing space is the loader's problem).
NOTICE_LABELS = sorted([
    "Beaver Creek", "Crook", "Crouch", "Dahlgren #1", "Dahlgren #2",
    "Flannigan", "Knights Prairie", "Mayberry", "McLeansboro #1",
    "McLeansboro #2", "McLeansboro #3", "McLeansboro #4", "South Crouch",
    "South Flannigan", "South Twigg", "Twigg",
], key=len, reverse=True)
EXPECTED = {re.sub(r"\s+", " ", label.replace("#", "")).upper()
            for label in NOTICE_LABELS}
EXPECTED_LOCATIONS = 13  # 12 rural + the shared McLeansboro gym, per the Clerk


fail = make_fail("hamilton-precinct-polling")


def clean(value):
    return re.sub(r"\s+", " ", (value or "")).strip()


def parse_notice(pdf_bytes):
    if pypdf is None:
        fail("pypdf is required (pip install -c scripts/requirements.txt pypdf)")
    text = " ".join((p.extract_text() or "")
                    for p in pypdf.PdfReader(io.BytesIO(pdf_bytes)).pages)
    text = re.sub(r"\s+", " ", text)
    # The polling table sits between its heading and the contact footer.
    start = text.find("Precinct Polling Locations")
    end = text.find("For further information")
    if start < 0 or end < 0 or end <= start:
        fail("the notice's polling-table section was not found — the notice's "
             "layout changed; re-read it before trusting any parse")
    section = text[start:end]
    # Every row ends with an Illinois ZIP; that terminator is the row split.
    rows = re.findall(r"(.+?IL\s+\d{5})", section)
    assignments = {}
    for row in rows:
        row = clean(row)
        label = next((l for l in NOTICE_LABELS
                      if row.startswith(l) or row.upper().startswith(l.upper())),
                     None)
        if label is None:
            # The heading sentence rides ahead of the first ZIP-terminated row.
            m = re.search(r"(?:^|\s)(" + "|".join(
                re.escape(l) for l in NOTICE_LABELS) + r")\s", row)
            if not m:
                continue
            row = row[m.start(1):]
            label = m.group(1)
        rest = clean(row[len(label):])
        # place = text before the first street-number token; the street runs
        # greedily to the city, which every row prints as a SINGLE word before
        # ", IL <zip>" (Springerton / McLeansboro / Dahlgren / Broughton /
        # Thompsonville) — a multi-word city fails the parse loudly rather
        # than splitting wrong.
        m = re.match(r"(.*?)\s(\d+\s.*)\s([A-Za-z]+,\s*IL\s+\d{5})$", rest)
        if not m:
            fail("row for %r did not split into place / street / city: %r"
                 % (label, rest))
        key = re.sub(r"\s+", " ", label.replace("#", "")).upper()
        assignments[key] = {
            "place": clean(m.group(1)),
            "address": clean(m.group(2)) + ", " + clean(m.group(3)),
        }
    return assignments


def main():
    check = "--check" in sys.argv
    require_robots_once(NOTICE_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-hamilton-precinct-polling")
    resp = requests.get(NOTICE_URL, headers=HEADERS, timeout=120)
    resp.raise_for_status()
    if not resp.content.startswith(b"%PDF"):
        fail("the notice URL did not return a PDF")
    assignments = parse_notice(resp.content)

    got = set(assignments)
    if got != EXPECTED:
        fail("parse does not cover the county's 16 precincts exactly — "
             "missing %s, unexpected %s (the notice's wording changed; update "
             "NOTICE_LABELS)" % (sorted(EXPECTED - got), sorted(got - EXPECTED)))
    locations = {(v["place"], v["address"]) for v in assignments.values()}
    if len(locations) != EXPECTED_LOCATIONS:
        fail("expected %d distinct polling locations (the Clerk's confirmed "
             "count), parsed %d" % (EXPECTED_LOCATIONS, len(locations)))
    gym = {k for k, v in assignments.items() if "GYM" in v["place"].upper()}
    if gym != {"MCLEANSBORO 1", "MCLEANSBORO 2", "MCLEANSBORO 3", "MCLEANSBORO 4"}:
        fail("the shared-gym rows are not exactly McLeansboro 1-4: %s"
             % sorted(gym))

    payload = {
        "source": NOTICE_URL,
        "sourcePage": NOTICE_PAGE,
        "election": ELECTION,
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
        print("hamilton-precinct-polling: OK — shipped file matches the notice "
              "(16 precincts, %d locations)" % EXPECTED_LOCATIONS)
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(body)
    print("hamilton-precinct-polling: wrote %s — %d precincts, %d locations"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), len(assignments),
             len(locations)))


if __name__ == "__main__":
    main()
