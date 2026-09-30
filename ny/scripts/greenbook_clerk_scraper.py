#!/usr/bin/env python3
"""
Scrape the five NYC County Clerks from the City of New York's own staff
directory — the Green Book, Socrata dataset `mdcw-n682` on
data.cityofnewyork.us. Stage 1 of the pipeline; build_borough_officials.py
resolves this into data/app/borough-officials.json.

WHY THIS SOURCE AND NOT THE COURTS'. NYC County Clerks are APPOINTED by the
Appellate Division, so there is no certified election return to fall back on.
The only source that has ever named them for this project is nycourts.gov,
which publishes the incumbent in two boroughs of five and has been behind a
Cloudflare managed challenge since 2026-09-26 (`cf-mitigated: challenge`, a
"Just a moment..." body). A challenge is an access control and is never solved
or worked around, so that route is shut and the other three boroughs named
nobody. The Green Book is the city's own directory, publishes one principal per
county for all five, and is served to this client with its path allowed.

WHAT IT IS ALLOWED TO DO, AND WHAT IT IS NOT. This scraper only ever reports
what the directory says. The decision about what to DO with a name is the
builder's, and it is narrow by Adam's ruling of 2026-09-29: fill an ABSENCE,
never overwrite a name already on a card. The Bronx is the case that rule
exists for — the two publishers disagree there (the card says Hon. Ischia
Bravo, the Green Book says Luis Diaz) and nothing this project can read settles
which is current, so nothing touches it.

THE DISCRIMINATOR IS `office_title` AND THERE IS NO `title` FIELD. A first
query against a `title` field matched ZERO of 26 rows and returned HTTP 200 —
a confident "no clerk rows here" assembled out of a wrong question, the shape
CLAUDE.md already records for an API error read as an empty answer. The
principal is the row whose office_title names the County Clerk and carries none
of the deputy/counsel/administrative words; measured 2026-09-29 that is exactly
one row per county, and this file REFUSES rather than guessing if it ever
stops being exactly one.

THE TITLES ARE NOT UNIFORM and that is why the rule is subtractive rather than
an equality test. Measured 2026-09-29 the five principals read: "County Clerk"
(Bronx, New York), "County Clerk and Clerk of the Supreme Court and
Commissioner of Jurors, County of Kings.", "Queens County Clerk, Clerk of the
Supreme Court, Commissioner of Jurors" and "County Clerk, Clerk of the Supreme
Court, Commissioner of Jurors and Register" (Richmond).

VACANCIES ARE PUBLISHED EXPLICITLY — three New York County rows read "Vacant
Vacant" — which is evidence the directory is maintained rather than a stale
copy left up, and is why a name of "Vacant" is read as an absence and never as
a person.

Usage:
    python3 ny/scripts/greenbook_clerk_scraper.py [--out PATH]
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

DATASET = "mdcw-n682"
BASE = "https://data.cityofnewyork.us/resource/%s.json" % DATASET
LANDING = "https://data.cityofnewyork.us/d/%s" % DATASET
UA = "districtry-nyc/1.0 (+https://districtry.com/ny/)"
DEFAULT_OUT = os.path.join(os.path.dirname(__file__), ".cache", "greenbook_clerks.json")

# The directory names counties; the app keys boroughs. One is not the other's
# spelling — "Richmond County" is Staten Island — so the join is stated here
# rather than derived from a string.
COUNTY_TO_BOROUGH = {
    "New York County": "Manhattan",
    "Bronx County": "Bronx",
    "Kings County": "Brooklyn",
    "Queens County": "Queens",
    "Richmond County": "Staten Island",
}

# Words that mark a row as somebody OTHER than the principal. Every one was
# seen in the 26 rows measured 2026-09-29; "Chief" is here because every
# "Chief Deputy County Clerk" also carries Deputy, and it costs nothing.
SUBORDINATE_WORDS = (
    "deputy", "counsel", "administrator", "comptroller", "assistant",
    "chief", "director", "secretary",
)

# ---------------------------------------------------------------- robots.txt
# THE FLEET'S ONE READER, scripts/robots_policy.py. APPENDED to sys.path rather
# than inserted, so ny/scripts/ keeps priority for its own siblings.
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "scripts"))
import robots_policy as rp                                        # noqa: E402


def fetch_rows(timeout=60):
    """One paced, permitted GET of every County Clerk row.

    MEASURED 2026-09-29 as the client above sends: data.cityofnewyork.us serves
    1,752 bytes, one binding `*` group, no rule matching /resource/, and a
    `Crawl-delay: 1` which HostPacer honours. A refusal raises rather than
    returning empty, because a refusal a caller can carry on past is one a
    caller will — and here an empty answer would read as "the directory names
    no clerks", which is the exact wrong reading this file exists to avoid.
    """
    gate = rp.RobotsGate(None, UA)
    pacer = rp.HostPacer(gate)
    url = BASE + "?" + urllib.parse.urlencode({
        "$where": "division_name like 'County Clerk - %'",
        "$limit": "500",
    })
    ok, why = gate.allows(url)
    if not ok:
        raise SystemExit(
            "greenbook_clerk_scraper: FAIL — %s refuses this client: %s. "
            "Nothing is fetched, and borough-officials.json keeps its "
            "last-good records (CLAUDE.md, Adam's ruling of 2026-09-19)."
            % (url, why))
    with pacer.hold(url):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        body = urllib.request.urlopen(req, timeout=timeout).read()
    rows = json.loads(body.decode("utf-8", "replace"))
    if not isinstance(rows, list):
        raise SystemExit("greenbook_clerk_scraper: FAIL — the endpoint answered "
                         "%s rather than a list of rows." % type(rows).__name__)
    return rows


def full_name(row):
    """The person's name, or None where the directory publishes a vacancy."""
    first = (row.get("first_name") or "").strip()
    last = (row.get("last_name") or "").strip()
    middle = (row.get("middle_initial") or "").strip()
    if not first and not last:
        return None
    if first.lower() == "vacant" or last.lower() == "vacant":
        return None
    parts = [p for p in (first, middle, last) if p]
    return " ".join(parts)


def is_principal(office_title):
    title = (office_title or "").lower()
    if "county clerk" not in title:
        return False
    return not any(word in title for word in SUBORDINATE_WORDS)


def resolve(rows):
    """One principal per county, or a refusal naming what it saw.

    THE GATE IS "EXACTLY ONE", IN BOTH DIRECTIONS. Zero means the title
    vocabulary moved and the subtractive rule stopped matching; more than one
    means it stopped discriminating, and picking either would be a guess about
    which of two people holds an office. Both are the directory changing shape
    under a rule measured against it once, which is precisely when a roster
    builder should stop rather than ship.
    """
    by_county = {}
    for row in rows:
        division = (row.get("division_name") or "").strip()
        if not division.startswith("County Clerk - "):
            continue
        county = division[len("County Clerk - "):].strip()
        if county not in COUNTY_TO_BOROUGH:
            continue
        if not is_principal(row.get("office_title")):
            continue
        by_county.setdefault(county, []).append(row)

    clerks = {}
    problems = []
    for county, borough in sorted(COUNTY_TO_BOROUGH.items()):
        found = by_county.get(county, [])
        if len(found) != 1:
            problems.append("%s: %d principal rows (%s)" % (
                county, len(found),
                "; ".join(r.get("office_title") or "?" for r in found) or "none"))
            continue
        row = found[0]
        name = full_name(row)
        if not name:
            problems.append("%s: the principal row publishes a vacancy" % county)
            continue
        clerks[borough] = {
            "name": name,
            "county": county,
            "office_title": (row.get("office_title") or "").strip(),
        }
    return clerks, problems


def main():
    argv = sys.argv[1:]
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT

    rows = fetch_rows()
    clerks, problems = resolve(rows)
    for line in problems:
        print("greenbook_clerk_scraper: NOT RESOLVED — %s" % line, file=sys.stderr)
    if len(clerks) < 5:
        raise SystemExit(
            "greenbook_clerk_scraper: FAIL — resolved %d of 5 County Clerks from "
            "%d rows. The directory's own shape has moved, so nothing is written "
            "and the last-good roster stands; re-read the rows before changing "
            "the rule." % (len(clerks), len(rows)))

    scraped_at = os.environ.get("SCRAPED_AT") or time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payload = {
        "source": "NYC Green Book (city staff directory), Socrata %s" % DATASET,
        "source_url": LANDING,
        "scraped_at": scraped_at,
        "rows_read": len(rows),
        "clerks": clerks,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("wrote %s: %d of 5 County Clerks from %d rows"
          % (out_path, len(clerks), len(rows)), file=sys.stderr)


if __name__ == "__main__":
    main()
