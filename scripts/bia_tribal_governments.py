#!/usr/bin/env python3
"""Read the Bureau of Indian Affairs' list of tribal governments.

The Census draws the land and never says whose government holds it. The Bureau
publishes the governments and never draws the land. Joining the two is this
project's own work (`data/tribal-government-join.json`), and this module supplies
the half of the join that has to come from a publisher: the current list of
government names, so that a join entry cannot name a government nobody
recognises.

WHAT THIS WRITES, AND WHAT IT DELIBERATELY LEAVES OUT
----------------------------------------------------
The Bureau's directory is a LEADERS directory: one person per government, with a
job title, a postal address, a telephone number and an e-mail address. This
module keeps the GOVERNMENTS and drops the people. Nothing in the fleet reads a
tribal leader's contact details yet -- the card work in step 5 reads each
nation's own published council list, which is the authority for who sits on it --
so committing 587 officials' direct lines and home-region e-mail addresses would
be publishing personal contact data no reader is served and no gate checks. When
a card needs a name it will read this directory again for that name.

ONE LEADER IS NOT A COUNCIL, WHICH IS WHY THIS IS A GATE AND NOT A ROSTER
------------------------------------------------------------------------
The directory carries exactly one person per government and no council members
at all, and the Bureau's mapping organisation publishes no council or district
layer for any nation (37 public datasets, measured 2026-09-29: child-welfare
regions, this directory, agency offices, grasslands, bison). That is correct
rather than a gap -- a nation's internal elections are its own government's
business -- so there is no federal shortcut to a council, and the only federal
thing worth holding a join table to is whether the government exists.

THE COUNT DOES NOT REPRODUCE AN EARLIER READING, AND THAT IS RECORDED
--------------------------------------------------------------------
A read on 2026-09-29 returned 602 rows with capitalised field names (OBJECTID,
LARtype, ancsaregion). The Bureau's own server publishes ONE leaders directory
today -- `Hosted/Tribal_Leaders_Directory_new`, measured 2026-09-30 by sweeping
all 23 of its service folders -- and it answers 587 rows with lower-case field
names and two fields the earlier read did not have (`tribe`, `organization`).
Which endpoint served the 602 was not established; it is not on this host. So
587 is what the Bureau's server answers, the 602 is not reproduced, and this
module reports the count every run rather than asserting either figure.

Usage:
    python3 scripts/bia_tribal_governments.py            # fetch and write
    python3 scripts/bia_tribal_governments.py --check    # offline drift gate
"""

import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO_ROOT, "data", "bia-tribal-governments.json")

SERVICE = (
    "https://biamaps.geoplatform.gov/server/rest/services/Hosted/"
    "Tribal_Leaders_Directory_new/FeatureServer/0"
)
HOST_ROOT = "https://biamaps.geoplatform.gov/"
USER_AGENT = "districtry/1.0 (+https://districtry.com/)"

# The government-identifying columns. Everything else the directory carries is
# about a PERSON and is not written -- see the docstring.
#
# `website` and `city` JOINED THE LIST ON 2026-10-01, for Illinois's tribal card,
# and they are government columns rather than the personal ones above them: a
# nation's own site is how a reader reaches the government that answers for the
# land they clicked, and the city is where that government's office is. The
# directory's `physicaladdress`, `phone`, `fax` and `email` stay out, for the
# reason the docstring gives -- a street address and a direct line belong to the
# one person per row, and no reader here is served by them.
#
# WHY THEY COME FROM HERE RATHER THAN FROM THE CARD'S OWN BUILDER. The seat and
# the site are what a card says ABOUT A GOVERNMENT, and `scripts/tribal_areas.py`
# already records why eight instances read one publisher through one module. A
# builder that fetched these two columns itself would be a second reader of this
# directory, which is where this fleet's recurring defect starts.
KEEP = ("tribefullname", "tribealternatename", "tribalcomponent", "biaregion",
        "state", "website", "city")

# A floor, not an assertion. 587 was measured 2026-09-30; a directory that has
# lost a third of its rows is a failed read rather than a change in federal
# recognition, and that is what this catches.
MIN_ROWS = 400


def _robots_allows():
    """Read the host's rules with the same client that will read the data."""
    sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
    import requests
    from robots_policy import RobotsGate

    session = requests.Session()
    gate = RobotsGate(session, USER_AGENT)
    allowed, why = gate.allows(SERVICE)
    return allowed, why, gate.crawl_delay(HOST_ROOT)


def fetch():
    """Every row of the directory, keeping only the government columns."""
    import urllib.parse
    import subprocess

    allowed, why, delay = _robots_allows()
    print("robots (%s): %s — %s" % (USER_AGENT, "allowed" if allowed else "REFUSED", why))
    if not allowed:
        raise SystemExit("robots.txt refuses this client; not fetching")
    if delay:
        print("host states a crawl delay of %ss; this reader makes one request" % delay)

    rows = []
    offset = 0
    page = 1000
    while True:
        url = (
            SERVICE + "/query?where=1%3D1&outFields=" + urllib.parse.quote(",".join(KEEP)) +
            "&returnGeometry=false&resultOffset=%d&resultRecordCount=%d&f=json" % (offset, page)
        )
        out = subprocess.run(
            ["curl", "-sS", "--fail", "--max-time", "120", "-A", USER_AGENT, url],
            check=True, capture_output=True,
        ).stdout
        got = json.loads(out)
        if "error" in got:
            raise RuntimeError("directory returned an error envelope: %r" % got["error"])
        batch = got.get("features")
        if batch is None:
            raise RuntimeError("directory answered with no features key: %r" % list(got))
        rows.extend(f.get("attributes") or {} for f in batch)
        if not got.get("exceededTransferLimit") and len(batch) < page:
            break
        if not batch:
            break
        offset += len(batch)
    return rows


def shape(rows):
    """One record per government, sorted, with the people dropped."""
    seen = {}
    for row in rows:
        name = (row.get("tribefullname") or "").strip()
        if not name:
            continue
        rec = {
            "name": name,
            "alternate": (row.get("tribealternatename") or "").strip() or None,
            "component": (row.get("tribalcomponent") or "").strip() or None,
            "biaRegion": (row.get("biaregion") or "").strip() or None,
            "state": (row.get("state") or "").strip() or None,
            # The office city, which for a government is where it sits. Paired
            # with `state` it is the seat a card names.
            "city": (row.get("city") or "").strip() or None,
            # The government's own site, exactly as the Bureau publishes it --
            # http and all. It is LINKED and not fetched, and a scheme this
            # project would prefer is not this project's to rewrite.
            "website": (row.get("website") or "").strip() or None,
        }
        # A government listed twice keeps its first row; the directory is one row
        # per government, so a duplicate is worth printing rather than merging.
        if name in seen and seen[name] != rec:
            print("NOTE %r appears more than once with different details" % name)
            continue
        seen[name] = rec
    return [seen[k] for k in sorted(seen)]


def write(records, rows_read):
    if len(records) < MIN_ROWS:
        raise SystemExit(
            "refusing to write: %d governments resolved from %d rows, floor is %d"
            % (len(records), rows_read, MIN_ROWS)
        )
    payload = {
        "source": SERVICE,
        "note": (
            "Government names, seats and own websites. The directory's leader, "
            "street address, telephone, fax and e-mail columns are deliberately "
            "not carried; see "
            "scripts/bia_tribal_governments.py."
        ),
        "governments": records,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("wrote %s: %d governments from %d directory rows" % (
        os.path.relpath(OUT, REPO_ROOT), len(records), rows_read))
    return 0


def load():
    """The committed list, for the join gate. Offline."""
    with open(OUT, encoding="utf-8") as fh:
        return json.load(fh)


def check():
    """Offline: the committed file is shaped as this module writes it."""
    if not os.path.exists(OUT):
        raise SystemExit("%s is missing" % os.path.relpath(OUT, REPO_ROOT))
    got = load()
    if got.get("source") != SERVICE:
        raise SystemExit(
            "%s names a different source than this module reads:\n  file: %r\n  module: %r"
            % (os.path.relpath(OUT, REPO_ROOT), got.get("source"), SERVICE)
        )
    govs = got.get("governments") or []
    if len(govs) < MIN_ROWS:
        raise SystemExit("%s carries %d governments, floor is %d" % (OUT, len(govs), MIN_ROWS))
    names = [g.get("name") for g in govs]
    if names != sorted(n for n in names if n):
        raise SystemExit("governments are not sorted by name, or one has no name")
    if len(set(names)) != len(names):
        raise SystemExit("a government name appears twice")
    personal = ("firstname", "middlename", "lastname", "salutation", "suffix",
                "aka", "jobtitle", "email", "phone", "fax", "physicaladdress",
                "mailingaddress", "dateelected", "nextelection")
    leaked = sorted({k for g in govs for k in g if k in personal})
    if leaked:
        raise SystemExit(
            "this file carries columns about a person, which it must not: %s" % ", ".join(leaked)
        )
    # THE KEY SET IS ASSERTED, not only the absence of the personal columns.
    # Checking for a leak catches a column added under the directory's own name
    # and says nothing about a field this module stopped writing -- so a reader
    # of `city` or `website` would go quiet rather than fail the day one of them
    # left `shape()`. The expected set is derived from that function's own
    # output so the two cannot drift apart.
    expected = set(shape([{k: "x" for k in KEEP}])[0])
    for g in govs:
        if set(g) != expected:
            raise SystemExit(
                "a government carries keys %s where this module writes %s — "
                "refetch the file rather than editing it"
                % (sorted(set(g)), sorted(expected))
            )
    print("OK %s: %d governments, no personal columns" % (os.path.relpath(OUT, REPO_ROOT), len(govs)))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="offline drift gate")
    args = ap.parse_args()
    if args.check:
        return check()
    rows = fetch()
    return write(shape(rows), len(rows))


if __name__ == "__main__":
    sys.exit(main())
