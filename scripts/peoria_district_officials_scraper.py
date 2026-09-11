#!/usr/bin/env python3
"""Peoria County's fire, park and library district officers, from AFR filings.

WHY THIS EXISTS. il/index.html dispatches Peoria in the fire, park and library
layers off the county's own ArcGIS layers, which carry a district NAME and a
WEBSITE and nothing else -- no officer, no address, no telephone. That is the
`peoria-fire-park-library-contact` gap, and its record said until 2026-09-08
that "nobody publishes a list of the trustees who run these districts".

SOMEBODY DOES: THE DISTRICTS THEMSELVES. Every Illinois unit of local
government files an Annual Financial Report with the Comptroller under the
Fiscal Responsibility Report Card Act, and the AFR's Contact Information
section names up to four role-holders and, beside each, the address, telephone
and e-mail THAT PERSON filed. The Comptroller is the COLLECTOR; the unit is
the author, which is what makes this the district's own statement rather than
a third party's assertion about it.

THE FORM CARRIES NO UNIT ADDRESS, and this docstring claimed one until
2026-09-10. Three Peoria districts were shipping a trustee's own address and
telephone as the district's office as a result; comptroller_afr.py's CONTACT
WITNESSES section carries the measurement and the two tests a contact value
now has to pass.

ONLY TWO OF THE FOUR ROLE SLOTS ARE READ, and the form itself says why. Slots
B and C are captioned "Your name will be listed with this responsibility on
our website" -- they are the officers the unit is publishing. Slot A (Contact
Person) and slot D (Purchasing Agent) are administrative contacts for the
filing, and reading them buys nothing and costs accuracy: Dunlap Fire
Protection District files the same person as "Jim Winters" in slot C and
"Jim Withers" in slot D, so a parser reading all four ships one trustee twice
under two spellings. NAMES ARE NEVER CORRECTED HERE and never joined on; the
unit CODE is the key.

THE FILED TITLE DECIDES WHICH LIST A PERSON JOINS, and this is the whole
reason the source is usable. docs/EXPANSION_GUIDE.md §3.4 records that the
Comptroller's "CEO" is often the appointed manager, and that holds here --
Lisle-Woodridge FPD in DuPage files its FIRE CHIEF in slot B. But the title
the unit filed sits beside the name, so an elected officer and an appointed
one are told apart per row instead of the whole source being trusted or
discarded: Dunlap FPD files Ann Joyce, PRESIDENT, and Dunlap Public Library
District files James Emanuels, PRESIDENT and Ron Holohan, TREASURER.
Following boone_district_officials, an appointed officer is not withheld --
it ships under `heads` labelled with its own filed title, where a trustee
ships under `board`. A title this file does not recognise ships under `heads`
with a warning naming it, never silently dropped and never guessed into a
board seat.

EVERY RECORD NAMES ITS FISCAL YEAR. An AFR is a snapshot filed for one year,
and the Comptroller's own page says "The contact person listed on the AFRs is
for the current Fiscal Year. Previous fiscal years may have a different
contact person." So `filedFor` rides every district and the card can say what
was filed and when rather than claiming a currency the filing cannot support.
Measured 2026-09-08 across eight Peoria units: six FY2025, Hanna City Park
District FY2024, and Tuscarora FPD carrying no fiscal year and no officer at
all while NOT appearing on the Comptroller's delinquency list -- unexplained
rather than delinquent, and shipped as absent.

THE JOIN IS TO THE COUNTY'S OWN LAYER NAMES, because that is what the card
holds at render time. Three mismatches are expected and none is reconciled
away: the county's Library_Districts layer carries PEORIA LIBRARY and
PEO HTS PUBLIC LIBR, which are MUNICIPAL libraries filing inside their city
and village rather than as districts; FARMINGTON COMM FPD and WILLIAMSFIELD
FPD file under their home counties, because a cross-county district files
once; and the Comptroller lists a Tuscarora fire district that the county's
layer carries only inside an overlap row.
"""

import argparse
import datetime
import json
import re
import sys
import time

import requests
from comptroller_afr import (  # noqa: E402  (shared machinery — do not fork)
    PACE, SEARCH_FORM, TIMEOUT, WAREHOUSE, contact_block, enumerate_county,
    new_session)


PEORIA_GIS = "https://services.arcgis.com/iPiPjILCMYxPZWTc/arcgis/rest/services/"
LAYERS = [("fire", "Fire_Protection_Districts", ("Fire Protection District",)),
          ("park", "Park_Districts", ("Park District",)),
          ("library", "Library_Districts",
           ("Public Library District", "Library District"))]


# The county's own abbreviations, expanded so a unit name can be matched. The
# SEARCH matches a unit's NAME FIELD ONLY -- "Dunlap Fire Protection District"
# is filed as the unit "Dunlap" and its type is metadata the result line
# appends -- so type words are stripped from the query and applied afterwards.
EXPAND = [(r"\bFPD\b", "Fire Protection District"), (r"\bPKD\b", "Park District"),
          (r"\bLBRY DIST\b", "Library District"), (r"\bPUB LIBR\b", "Public Library"),
          (r"\bPUBLIC LIBR\b", "Public Library"), (r"\bPUB LIBRARY\b", "Public Library"),
          (r"\bCOMM\b", "Community"), (r"\bTWP\b", "Township"),
          (r"\bPRINCEVLLE\b", "Princeville"), (r"\bDRIVEWY\b", "Driveway"),
          (r"\bWMSFIELD\b", "Williamsfield"), (r"\bBRIMFLD\b", "Brimfield"),
          (r"\bPEO HTS\b", "Peoria Heights"), (r"\bLBRY\b", "Library"),
          # A BODY's name may be expanded to join; a PERSON's never is. The
          # county abbreviates the Lillie M. Evans Library District to its
          # initials and the Warehouse files it in full.
          (r"\bL M EVANS\b", "Lillie M. Evans")]
TYPE_WORDS = re.compile(
    r"\b(Fire Protection District|Public Library District|Library District|"
    r"Park District|Public Library|Fire District|District|Library|Township)\b", re.I)



def fail(msg):
    sys.exit("peoria-district-officials: FATAL — " + msg)



def gis_districts(session):
    """{kind: [county District_Name, …]} from the same layers the app loads."""
    out = {}
    for kind, service, _types in LAYERS:
        r = session.get(PEORIA_GIS + service + "/FeatureServer/0/query",
                        params={"where": "1=1", "outFields": "District_Name,WebSite",
                                "returnGeometry": "false", "f": "json"},
                        timeout=TIMEOUT)
        r.raise_for_status()
        payload = r.json()
        if "error" in payload:
            fail("Peoria's %s layer returned an error: %s" % (kind, payload["error"]))
        names = []
        for feat in payload.get("features", []):
            name = (feat.get("attributes", {}).get("District_Name") or "").strip()
            # "A & B" rows are the county's overlap annotation, not a district.
            if name and "&" not in name:
                names.append(name)
        if not names:
            fail("Peoria's %s layer returned no districts" % kind)
        out[kind] = sorted(set(names))
    return out


def query_for(gis_name):
    n = re.sub(r"\s*\(Dist # \d+\).*$", "", gis_name).strip()
    for pat, rep in EXPAND:
        n = re.sub(pat, rep, n)
    return " ".join(TYPE_WORDS.sub(" ", n).split()).title()




def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--county", default="Peoria")
    args = ap.parse_args()

    warnings, unmatched = [], []
    s = new_session()                          # holds the ColdFusion cookie

    layers = gis_districts(s)
    units = enumerate_county(s, args.county)
    if not units:
        fail("the Warehouse returned no %s County units — the search changed"
             % args.county)

    districts = {}
    for kind, _service, types in LAYERS:
        for gis_name in layers[kind]:
            want = query_for(gis_name).lower()
            typed = [(c, t) for c, t in units
                     if any((" - a %s in " % ty).lower() in t.lower() for ty in types)]
            hit = [(c, t) for c, t in typed
                   if t.split(" - ")[0].strip().lower() == want]
            if not hit:
                # A SECOND, BOUNDED ATTEMPT, and only within the right type and
                # county. The county's layer and the Warehouse do not always
                # write a name the same way: "RICHWOODS FPD" files as "Richwoods
                # Twp", and the county's "CHILLICOTHE PARK" is the Warehouse's
                # "Chillicothe" park district. A prefix match settles both, and
                # is accepted ONLY when it is unique — two candidates is an
                # ambiguity to report, never one to pick from.
                hit = [(c, t) for c, t in typed
                       if t.split(" - ")[0].strip().lower().startswith(want)
                       or want.startswith(t.split(" - ")[0].strip().lower())]
            if len(hit) != 1:
                unmatched.append("%s (%s) — %d Warehouse unit(s) named %r"
                                 % (gis_name, kind, len(hit), want))
                continue
            code, label = hit[0]
            time.sleep(PACE)
            block = contact_block(s, code, label, warnings)
            if not block:
                unmatched.append("%s (%s) — unit %s files no contact block"
                                 % (gis_name, kind, code))
                continue
            entry = {"kind": kind, "comptrollerCode": code,
                     "filedFor": block["filedFor"], "office": {}}
            for field, value in (("address", block["street"]), ("city", block["city"]),
                                 ("phone", block["phone"]), ("email", block["email"])):
                if value:
                    entry["office"][field] = value
            for bucket, person in block["officers"]:
                entry.setdefault(bucket, []).append(person)
            districts[gis_name] = entry

    if not districts:
        # PRINT BEFORE FAILING. The first draft called fail() here, which exits
        # before the warning and not-matched lists below — losing every line
        # explaining the failure at exactly the moment it mattered.
        for w in warnings:
            print("  WARN: %s" % w, file=sys.stderr)
        for u in unmatched:
            print("  NOT MATCHED: %s" % u, file=sys.stderr)
        fail("no district joined to a Warehouse unit — the join or the search broke")

    payload = {
        "source": "Illinois Comptroller, Annual Financial Report — Contact Information",
        "sourceUrl": WAREHOUSE,
        "officialsPage": SEARCH_FORM,
        "generated": datetime.datetime.now(datetime.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "districts": districts,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")

    for w in warnings:
        print("  WARN: %s" % w, file=sys.stderr)
    for u in unmatched:
        print("  NOT MATCHED: %s" % u, file=sys.stderr)
    board = sum(len(d.get("board") or []) for d in districts.values())
    heads = sum(len(d.get("heads") or []) for d in districts.values())
    print("scraped %d of %d Peoria district(s): %d board officer(s), %d appointed "
          "-> %s" % (len(districts), sum(len(v) for v in layers.values()),
                     board, heads, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
