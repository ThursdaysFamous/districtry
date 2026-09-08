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
section publishes the unit's office address, telephone, fax and e-mail
together with named role-holders. The Comptroller is the COLLECTOR; the unit
is the author, which is what makes this the district's own statement rather
than a third party's assertion about it.

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
import html
import json
import re
import sys
import time

import requests
from scraper_common import UA_ROSTER_COMPACT  # noqa: E402  (shared machinery — do not fork)

WAREHOUSE = ("https://illinoiscomptroller.gov/constituent-services/"
             "local-government/local-government-warehouse/")
SEARCH_FORM = WAREHOUSE + "searchform/?SearchType=AFRSearch"
RESULTS = WAREHOUSE + "processsearchresults/"

PEORIA_GIS = "https://services.arcgis.com/iPiPjILCMYxPZWTc/arcgis/rest/services/"
LAYERS = [("fire", "Fire_Protection_Districts", ("Fire Protection District",)),
          ("park", "Park_Districts", ("Park District",)),
          ("library", "Library_Districts",
           ("Public Library District", "Library District"))]

HEADERS = {"User-Agent": UA_ROSTER_COMPACT}
TIMEOUT = 45
PACE = 1.0                       # a state government site, one request a second

# An ELECTED board office. A district's trustees elect these from among
# themselves, so a person filed under one of them holds a board seat.
BOARD_TITLES = {"president", "vice president", "vice-president", "secretary",
                "treasurer", "trustee", "chairman", "chair", "chairperson",
                "commissioner", "board president", "board chairman"}
# An APPOINTED post. Shipped, and never as a board seat.
HEAD_TITLES = {"fire chief", "chief", "director", "executive director",
               "administrator", "village administrator", "city administrator",
               "librarian", "head librarian", "superintendent", "manager"}

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

SLOTS = 4                        # A Contact Person, B CEO, C CFO, D Purchasing Agent
# Only B and C are read: the form captions them "Your name will be listed with
# this responsibility on our website", which is the unit publishing an officer.
PUBLISHED_SLOTS = (1, 2)
CONTACT_SLOT = 0                 # the unit's own office address and telephone

RESULT_RE = re.compile(
    r'href="[^"]*[Cc]ode=([0-9/]+)"[^>]*>\s*([^<]{3,140}?)\s*</a>', re.S)


def fail(msg):
    sys.exit("peoria-district-officials: FATAL — " + msg)


def text_of(markup):
    body = re.sub(r"<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ",
                  markup, flags=re.S)
    lines = html.unescape(re.sub(r"<[^>]+>", "\n", body)).split("\n")
    return [l.strip() for l in lines if l.strip()]


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


def enumerate_county(session, county):
    """[(code, label)] for every unit the Warehouse files under this county.

    ONE search on the county name returns the whole county -- 96 typed units
    for Peoria -- because the search matches the county as well as the unit
    name. Looking units up one at a time would be 25 requests for the same
    answer.
    """
    r = session.post(RESULTS, timeout=TIMEOUT,
                     data={"displayMode": "GetLandingPage",
                           "SearchType": "AFRSearch", "GovUnit": county})
    r.raise_for_status()
    hits = [(c, html.unescape(re.sub(r"\s+", " ", t)).strip())
            for c, t in RESULT_RE.findall(r.text)]
    return [(c, t) for c, t in hits if ("in %s County" % county) in t]


def latest_fiscal_year(session, code):
    """The fiscal year this unit last filed for, off its landing page.

    THE YEAR IS ASKED FOR, NEVER ASSUMED. An empty CFY returns a page with no
    contact block at all -- which the first draft of this file sent, so every
    unit parsed as unfiled and the whole run failed -- and a hardcoded year
    would silently skip a unit that is one year behind. Hanna City Park
    District's latest is FY2024 where the other seven sampled are FY2025.
    """
    r = session.get(WAREHOUSE + "landingpage",
                    params={"code": code, "searchtype": "AFRSearch"},
                    timeout=TIMEOUT)
    r.raise_for_status()
    lines = text_of(r.text)
    for i, line in enumerate(lines):
        if line == "For Fiscal Year" and i + 1 < len(lines):
            year = lines[i + 1].strip()
            return year if re.fullmatch(r"20\d\d", year) else None
    return None


def contact_rows(markup):
    """The contact table's rows as lists of cell text, or []."""
    for table in re.findall(r"<table[^>]*>.*?</table>", markup, re.S):
        if "Chief Executive Officer" not in table:
            continue
        rows = []
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S):
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)
            rows.append([re.sub(r"\s+", " ",
                                html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                         for c in cells])
        return rows
    return []


def contact_block(session, code, unit_label, warnings):
    """The unit's office and its two published officers, or None.

    PARSED FROM THE TABLE, NEVER FROM FLATTENED TEXT. The first draft read the
    page as a list of lines and sliced it four at a time, which mispaired every
    unit: THE NAME ROW CARRIES EIGHT CELLS (a forename and a surname for each
    of the four slots) WHERE EVERY OTHER ROW CARRIES FOUR, so a positional read
    took `Ann | Joyce | Ann | Joyce` as four forenames and `Jim | Winters | Jim
    | Withers` as their surnames and shipped a trustee called "Ann Jim". It
    published 24 board officers, none of them trustworthy. The rows are keyed
    by their own shape and their own labels here, and a table that does not
    match is SKIPPED with a warning rather than guessed at.
    """
    year = latest_fiscal_year(session, code)
    if not year:
        warnings.append("%s: no fiscal year on its landing page — it files no "
                        "contact block this run" % unit_label)
        return None
    time.sleep(PACE)
    r = session.post(RESULTS, timeout=TIMEOUT,
                     data={"DisplayMode": "GetAFR", "Code": code,
                           "CFY": year, "AFRDesiredData": "Contact Information"})
    r.raise_for_status()
    rows = contact_rows(r.text)
    names = next((x for x in rows if len(x) == 2 * SLOTS
                  and any(c for c in x)), None)
    if names is None:
        warnings.append("%s: no %d-cell name row in the contact table — the "
                        "form's layout changed" % (unit_label, 2 * SLOTS))
        return None
    after = rows[rows.index(names) + 1:]
    quad = [x for x in after if len(x) == SLOTS]
    if len(quad) < 6:
        warnings.append("%s: contact table has %d four-cell row(s), expected at "
                        "least 6" % (unit_label, len(quad)))
        return None
    titles = quad[0]
    # The three rows between the titles and the labelled ones, in the form's
    # own order. Labelled rows identify themselves and are found by label.
    unlabelled = [x for x in quad[1:] if not any(
        c.startswith(("Phone:", "Fax:", "E-mail:")) for c in x)]
    street = unlabelled[0][0] if unlabelled else ""
    city = unlabelled[1][0] if len(unlabelled) > 1 else ""
    region = unlabelled[2][0] if len(unlabelled) > 2 else ""

    def labelled(prefix, slot):
        for x in quad:
            if x[slot].startswith(prefix):
                return x[slot][len(prefix):].split("Ext")[0].strip()
        return ""

    officers = []
    for slot in PUBLISHED_SLOTS:
        name = " ".join(x for x in (names[2 * slot], names[2 * slot + 1]) if x).strip()
        title = (titles[slot] or "").strip()
        if not name or not title:
            continue
        key = title.lower().rstrip(".").strip()
        # West Peoria FPD files Mark Stecher, President, as BOTH its CEO and
        # its CFO — one person holding two responsibilities, not two trustees.
        # Deduped on the pair as filed, never by matching names loosely: the
        # same unit can file one person under two spellings and this must not
        # be the code that decides two spellings are one person.
        if any(q["name"] == name and q["role"] == title for _b, q in officers):
            continue
        if key in BOARD_TITLES:
            officers.append(("board", {"name": name, "role": title}))
        else:
            if key not in HEAD_TITLES:
                warnings.append("%s: filed title %r for %s is neither a board "
                                "office nor a recognised appointed post — "
                                "shipped as appointed, never as a board seat"
                                % (unit_label, title, name))
            officers.append(("heads", {"name": name, "role": title}))
    return {"filedFor": year,
            "street": street,
            "city": " ".join(x for x in (city, region) if x).strip(),
            "phone": labelled("Phone:", CONTACT_SLOT),
            "email": labelled("E-mail:", CONTACT_SLOT),
            "officers": officers}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--county", default="Peoria")
    args = ap.parse_args()

    warnings, unmatched = [], []
    s = requests.Session(); s.headers.update(HEADERS)
    s.get(SEARCH_FORM, timeout=TIMEOUT)        # ColdFusion session cookie

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
