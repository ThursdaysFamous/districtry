#!/usr/bin/env python3
"""
Illinois Supreme and Appellate Court justices, from the courts' own site
=======================================================================
Reads illinoiscourts.gov and produces one record per JUDICIAL DISTRICT (1-5)
carrying the Supreme Court justice or justices elected from it, the Appellate
Court branch that sits in it (courthouse, clerk, telephone), and that branch's
sitting justices. scripts/build_il_court_justices.py resolves the raw output
into il/data/app/il-court-justices.json, which the `il-supreme-court` card
joins to the PA 102-0011 district geometry the app already ships.

WHY THIS EXISTS, AND WHAT IT CORRECTS. il/index.html has said since the layer
shipped that "no live-verifiable roster source exists for either body in this
build environment, so -- per the playbook's 'never guess' rule -- both cards
link to the official body instead of naming names." That was true of the
SHAPEFILE, whose attribute table carries no officeholder column, and it was
never true of the court: illinoiscourts.gov publishes all seven justices with
the district each was elected from, and publishes every appellate justice with
their district in a searchable directory. Measured 2026-09-15, the districtry
token gets both at HTTP 200 (www.illinoiscourts.gov is `token-ok` in
user-agent-measurements.json, and this scraper sends the token; no browser
string is needed or sent).

ONE SET OF DISTRICTS SERVES BOTH COURTS, which is why one file answers for
both. Illinois Constitution art. VI, sec. 2: "The State is divided into five
Judicial Districts for the selection of Supreme and Appellate Court Judges."
705 ILCS 25/1(a) adds that "A branch of the appellate court is established in
each of the 5 judicial districts as such districts are determined by law" --
the Appellate Court Act defines no districts of its own -- and 705 ILCS 23
(the Judicial Districts Act of 2021, P.A. 102-11) is where they are
determined, county by county. The builder holds the court's own county lists
to that statute.

THREE SURFACES, READ SEPARATELY:

  1. /courts/supreme-court/meet-the-justices/ -- seven accordion blocks, each
     a heading with the justice's name and a subheading reading "Supreme Court
     Justice, <Nth> District". SIX OF THE SEVEN CARRY THAT COMMA AND ONE DOES
     NOT: Lisa Holder White's block reads "Supreme Court Justice Fourth
     District". A comma-requiring pattern drops exactly her, and she is the
     Fourth District's only justice -- 41 counties would name nobody, with the
     other six looking perfectly correct. The comma is optional here for that
     reason, and the builder's per-district count is what would catch the next
     variant of it.

  2. /courts/circuit-court/chief-judges-and-administrative-staff/?t=appellate
     -- the Judicial Directory, filtered to the appellate court. It is an
     ASP.NET WebForms page: the filters are <select>s that POST back and "View
     More Results" bumps a hidden page size, so the full roster needs a form
     POST carrying __VIEWSTATE, not a query string. Thirty rows arrive on the
     GET and the rest on one postback.

  3. /courts/appellate-court/districts-<ordinal>-district/ -- the branch's
     seat city, courthouse address, telephone, clerk, and the circuits (with
     their counties) it hears appeals from. That county list is the third
     witness to the composition, independent of both the statute and the
     shipped geometry.

WHAT IS NOT CLAIMED. The directory lists every justice currently serving in a
district, which is more than the seats 705 ILCS 25/1(b)-(c) elects (18 in the
First District, 6 in each of the others), because sec. 1(d) lets the Supreme
Court assign additional judges "as the business of the appellate court
requires". The record therefore says how many justices the district's page
lists and never that this is the elected complement; no row here distinguishes
an elected justice from an assigned one, because the directory does not.

Usage:
    python3 il_court_justices_scraper.py --out /tmp/il_court_justices_raw.json
"""

import argparse
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robots_policy import RobotsGate  # noqa: E402
from scraper_common import UA_ROSTER_BOT  # noqa: E402  (shared machinery -- do not fork)

BASE = "https://www.illinoiscourts.gov"
SUPREME_URL = BASE + "/courts/supreme-court/meet-the-justices/"
DIRECTORY_URL = BASE + "/courts/circuit-court/chief-judges-and-administrative-staff/?t=appellate"
DISTRICT_URLS = {
    1: BASE + "/courts/appellate-court/districts-first-district/",
    2: BASE + "/courts/appellate-court/districts-second-district/",
    3: BASE + "/courts/appellate-court/districts-third-district/",
    4: BASE + "/courts/appellate-court/districts-fourth-district/",
    5: BASE + "/courts/appellate-court/districts-fifth-district/",
}
ORDINALS = {"First": 1, "Second": 2, "Third": 3, "Fourth": 4, "Fifth": 5}
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
    "Accept-Language": "en-US,en;q=0.9",
}


def clean(text):
    """Entity-decode, drop the zero-width marks the CMS sprays through
    addresses, and collapse whitespace."""
    text = html.unescape(text or "")
    text = text.replace("​", "").replace("﻿", "").replace("\xa0", " ")
    return " ".join(text.split())


def strip_tags(fragment):
    fragment = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", fragment, flags=re.S | re.I)
    return clean(re.sub(r"<[^>]+>", " ", fragment))


def hidden_fields(body):
    """Every <input type=hidden> on the page, by name -- the WebForms state a
    postback has to carry back."""
    fields = {}
    for tag in re.findall(r'<input[^>]*type="hidden"[^>]*>', body, flags=re.I):
        name = re.search(r'name="([^"]+)"', tag)
        value = re.search(r'value="([^"]*)"', tag)
        if name:
            fields[name.group(1)] = html.unescape(value.group(1)) if value else ""
    return fields


# ---------------------------------------------------------------- supreme court

# The comma after "Justice" is OPTIONAL on purpose; see the module docstring.
SUPREME_TITLE = re.compile(
    r"<h3[^>]*>\s*Supreme Court Justice,?\s*(First|Second|Third|Fourth|Fifth)\s+District",
    re.I,
)
ACCORDION = re.compile(
    r'<div class="accordion cloneable">(.*?)</div>\s*</div>', re.S | re.I
)


def scrape_supreme(session, gate, verbose=True):
    body = fetch(session, gate, SUPREME_URL)
    justices = []
    for block in ACCORDION.finditer(body):
        chunk = block.group(1)
        title = SUPREME_TITLE.search(chunk)
        if not title:
            continue
        district = ORDINALS[title.group(1).title()]
        # The accordion's own summary heading is the authority for the name:
        # it is the one place the page writes it once, where the body repeats
        # it and then goes on to prose that also contains other people's names.
        heading = re.search(
            r'<h2 class="accordion-title[^"]*"[^>]*>(.*?)</h2>', chunk, re.S | re.I
        )
        if not heading:
            continue
        label = strip_tags(heading.group(1))
        role = "Justice"
        # "P. Scott Neville, Jr., Chief Justice" -- the role is a trailing
        # clause on the summary, and only the Chief Justice has one.
        chief = re.search(r",\s*Chief Justice\s*$", label, re.I)
        if chief:
            role = "Chief Justice"
            label = label[: chief.start()].strip()
        justices.append({
            "name": label,
            "role": role,
            "district": district,
            "source_url": SUPREME_URL,
        })
    if verbose:
        print("  supreme court: %d justices" % len(justices))
        for j in justices:
            print("     D%d  %-28s %s" % (j["district"], j["name"], j["role"]))
    return justices


# ------------------------------------------------------------ appellate roster

def parse_directory_rows(body):
    """One record per repeater row. The directory numbers its labels
    (lblLastName_0, lblFirstName_0, ...), so the row index is the join key."""
    rows = []
    for match in re.finditer(r'lblLastName_(\d+)"[^>]*>([^<]*)', body):
        index = match.group(1)

        def label(key):
            found = re.search(r'lbl%s_%s"[^>]*>([^<]*)' % (key, index), body)
            return clean(found.group(1)) if found else ""

        profile = re.search(
            r'hlDetailName_%s"\s+href="([^"]+)"' % index, body
        )
        rows.append({
            "last": clean(match.group(2)),
            "first": label("FirstName"),
            "middle": label("MiddleName"),
            "title": label("Title"),
            "district": label("District"),
            # each row links the justice's own page on the same site
            "profile_url": html.unescape(profile.group(1)) if profile else None,
        })
    return rows


def scrape_appellate(session, gate, verbose=True):
    body = fetch(session, gate, DIRECTORY_URL)
    rows = parse_directory_rows(body)
    # "View More Results" is a postback that raises the page size; loop until
    # the control is gone rather than guessing how many pages there are.
    for _ in range(10):
        if "View More Results" not in body:
            break
        form = hidden_fields(body)
        form["ctl00$ctl04$ddlFilterCourtType"] = "Appellate Court"
        form["__EVENTTARGET"] = "ctl00$ctl04$btnLoadMoreResults"
        form["__EVENTARGUMENT"] = ""
        time.sleep(1.0)
        response = session.post(
            DIRECTORY_URL, data=form,
            headers=dict(HEADERS, Referer=DIRECTORY_URL), timeout=60,
        )
        response.raise_for_status()
        body = response.text
        rows = parse_directory_rows(body)
    justices = []
    for row in rows:
        if "appellate court justice" not in row["title"].lower():
            continue
        if not row["district"].isdigit():
            continue
        name = " ".join(p for p in (row["first"], row["middle"], row["last"]) if p)
        justices.append({
            "name": name,
            # THE DIRECTORY PUBLISHES THE SURNAME AS ITS OWN FIELD, suffix
            # included ("Martin Jr.", "Ocasio III", "Van Tine", "Vancil Jr."),
            # so it is carried rather than re-derived: splitting the joined
            # name on its last token sorts four of the 57 under "Jr.", "III"
            # or "Tine". The publisher already answers this; do not re-answer it.
            "last": row["last"],
            "district": int(row["district"]),
            "profile_url": row.get("profile_url"),
            "source_url": DIRECTORY_URL,
        })
    if verbose:
        counts = {}
        for j in justices:
            counts[j["district"]] = counts.get(j["district"], 0) + 1
        print("  appellate directory: %d justices  %s"
              % (len(justices), " ".join("D%d=%d" % (d, counts[d]) for d in sorted(counts))))
    return justices


# ---------------------------------------------------------- appellate branches

# "The Second District Appellate Court is located in Elgin and hears cases
# appealed from trial courts in 5 counties."
SEAT = re.compile(
    r"The (First|Second|Third|Fourth|Fifth) District Appellate Court is located in "
    r"(.+?) and hears cases appealed from trial courts in (\d+ counties|[A-Z][\w ]+County)",
    re.I,
)
# "Circuits: 16th (Kane), 19th (Lake), 22nd (McHenry), 23rd (DeKalb & Kendall)"
CIRCUIT = re.compile(r"(\d+)(?:st|nd|rd|th)\s*\(([^)]*)\)")
PHONE = re.compile(r"\((\d{3})\)\s*(\d{3})-(\d{4})")
CLERK = re.compile(r"([A-Z][\w.'\-]+(?:\s+[A-Z][\w.'\-]+){1,3}),\s*Clerk\b")
POPULATION = re.compile(r"District Population:\s*([\d,]+)")


def to_lines(fragment):
    """The CMS writes an office block as <br>-separated lines inside <p>s, so
    the line breaks ARE the address's structure. Flattening the whole block to
    one string throws that away and yields "Michael A. Bilandic Building 160
    North LaSalle St. Chicago, IL 60601" where the page shows three lines."""
    fragment = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", fragment, flags=re.S | re.I)
    fragment = re.sub(r"<\s*br\s*/?>|</\s*(p|h\d|div|li)\s*>", "\n", fragment, flags=re.I)
    lines = [clean(re.sub(r"<[^>]+>", " ", line)) for line in fragment.split("\n")]
    return [line for line in lines if line]


def scrape_branch(session, gate, district, verbose=True):
    url = DISTRICT_URLS[district]
    body = fetch(session, gate, url)
    text = strip_tags(body)
    seat = SEAT.search(text)
    record = {
        "district": district,
        "source_url": url,
        "seat": clean(seat.group(2)) if seat else None,
        "scope": clean(seat.group(3)) if seat else None,
        "counties": [],
        "circuits": [],
    }
    # The office block is anchored on its own <h3> ("Fifth District - Mt.
    # Vernon") and runs to the district population line. Anchoring on the seat
    # SENTENCE instead reads the First District's following sentence ("The
    # First District is divided into six divisions.") as an address line, and
    # taking the seat city as one word puts "Vernon" at the head of the Fifth
    # District's address.
    heading = re.search(
        r"<h3[^>]*>\s*(?:First|Second|Third|Fourth|Fifth) District\s*[-\u2013]",
        body, flags=re.I,
    )
    if heading:
        stop = body.find("District Population", heading.end())
        block = body[heading.end():stop if stop > 0 else heading.end() + 2000]
        lines = to_lines(block)
        address, seen_phone = [], False
        for line in lines:
            if PHONE.search(line):
                phone = PHONE.search(line)
                record["phone"] = "(%s) %s-%s" % phone.groups()
                seen_phone = True
                continue
            clerk = CLERK.search(line)
            if clerk:
                record["clerk"] = clean(clerk.group(1))
                continue
            if seen_phone or "Research Director" in line:
                continue
            # The heading's own trailing city, and the court's aside on the
            # Bilandic Building's former name, are not address lines.
            if line.startswith(record["seat"] or "\0") and len(line) <= len((record["seat"] or "")) + 2:
                continue
            if line.startswith("(") or line.startswith("Formerly"):
                continue
            address.append(line)
        record["address_lines"] = address
    population = POPULATION.search(text)
    if population:
        record["population"] = int(population.group(1).replace(",", ""))
    for match in CIRCUIT.finditer(text):
        circuit, counties = match.groups()
        names = [clean(c) for c in re.split(r"&|,", counties) if clean(c)]
        record["circuits"].append({"circuit": int(circuit), "counties": names})
        record["counties"].extend(names)
    if district == 1 and not record["counties"]:
        # The First District's page names no circuit list: it is one county,
        # and says so in the seat sentence ("trial courts in Cook County").
        if record["scope"] and "cook" in record["scope"].lower():
            record["counties"] = ["Cook"]
            record["circuits"].append({"circuit": None, "counties": ["Cook"]})
    if verbose:
        print("  D%d %-12s %-52s %-15s %2d counties"
              % (district, record["seat"] or "?",
                 " / ".join(record.get("address_lines") or ["?"])[:52],
                 record.get("phone") or "?", len(record["counties"])))
    return record


# ------------------------------------------------------------------- machinery

def fetch(session, gate, url):
    allowed, why = gate.allows(url)
    if not allowed:
        raise SystemExit("robots.txt declines %s: %s" % (url, why))
    delay = gate.crawl_delay(url)
    if delay:
        time.sleep(delay)
    response = session.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    return response.text


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", required=True, help="raw JSON output path")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    verbose = not args.quiet

    session = requests.Session()
    gate = RobotsGate(session, UA_ROSTER_BOT)

    payload = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "supreme": scrape_supreme(session, gate, verbose),
        "appellate": scrape_appellate(session, gate, verbose),
        "branches": [scrape_branch(session, gate, d, verbose) for d in sorted(DISTRICT_URLS)],
    }
    with open(args.out, "w") as handle:
        json.dump(payload, handle, indent=1)
    if verbose:
        print("wrote %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
