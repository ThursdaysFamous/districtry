#!/usr/bin/env python3
"""
Scrape Ogle County's clerk yearbook into the payload
build_municipal_officials_roster.py consumes.

SOURCE. The clerk's annual yearbook carries an "OGLE COUNTY CITIES & VILLAGES"
section listing every municipality's FULL governing body — head of government,
clerk, treasurer and every trustee / alderperson / council member, with ward
numbers where a city elects by ward — plus the hall address, phone and website.
That is Cook/Will/LaSalle depth from one county document, so Ogle joins as a
full-governing-body county rather than a mayor-level one.

FETCH POSTURE: open. The PDF is served to an ordinary browser UA with no
challenge; plain `requests` succeeds.

WHY A LINE PARSER AND NOT LaSalle's GEOMETRIC ONE. LaSalle's directory is a
six-column table whose columns interleave, so it had to be read from word
positions. This document is single-column narrative text, one officer per line
in "<office> <name>" form, and pypdf's line extraction preserves that exactly.
Reaching for the geometric parser here would be more machinery for no gain.

WHAT IS DELIBERATELY NOT COLLECTED:
  * The office ADDRESS is the village hall and is collected. There are no
    per-person addresses in this section at all, so the residence problem that
    shaped the LaSalle/Madison/Stephenson decisions does not arise.
  * Appointed staff (City Manager, Deputy Clerk, Superintendent) are carried
    with appointed=True so a card can never imply they were elected, matching
    the LaSalle payload.

WHERE THE SECTION ENDS, and why that took two goes. Parsing starts at the
CITIES & VILLAGES heading — the TOWNSHIP officials before it are a different
body, not municipal officers. It used to END at "OGLE COUNTY POLLING PLACES",
which is one heading too late: "GENERAL INFORMATION" sits between them, and its
levy-deadline block is INDENTED, so the last municipality's still-open
"Trustees" group swallowed it. Stillman Valley shipped ten trustees who are
phrases — "Other Special Districts", "Library Districts Townships",
"www.census.gov". The bound is now the next ALL-CAPS heading of any kind, which
is measured, not assumed: across the whole 2025-2027 book only four lines match
that shape after the start, the first is GENERAL INFORMATION, and no line inside
any municipality block matches it at all.

Usage:
    python3 ogle_municipal_officials_scraper.py --out ogle_municipal_officials.json
    python3 ogle_municipal_officials_scraper.py --out out.json --pdf local.pdf
"""

import argparse
import datetime
import io
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_ROSTER_BOT,
    require_robots_once,
)

try:
    import pypdf
except ImportError:  # pragma: no cover
    pypdf = None

YEARBOOK_URL = ("https://www.oglecountyil.gov/document_center/County%20Clerk/"
                "Yearbook/2025-%202027%20Yearbook.pdf")
CLERK_PAGE = "https://www.oglecountyil.gov/departments/county_clerk/index.php"
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
}
REQUEST_TIMEOUT = 120

START_RE = re.compile(r"OGLE COUNTY CITIES\s*&\s*VILLAGES", re.I)
# The section ends at the book's next ALL-CAPS heading — see the module
# docstring for why a named sentinel was the wrong bound. Anchored to a whole
# line so a capitalised fragment inside an address can never end the section.
SECTION_HEADING_RE = re.compile(r"^[A-Z][A-Z0-9 &.'’/-]{5,}$")
MUNI_RE = re.compile(r"^(City|Village|Town) of ([A-Z][A-Za-z .'/-]+?)\s*$")
# Adeline writes "Phone: President - 815-535-3572  Clerk - 815-440-2736", so the
# gap between the word and the first digits is wider than a tight bound allows.
# The FIRST number on a Phone line is the one taken.
PHONE_RE = re.compile(r"Phone[^0-9\n]{0,40}?((?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4})", re.I)
WEBSITE_RE = re.compile(r"Website:\s*(\S+)", re.I)
EMAIL_RE = re.compile(r"Email[^A-Za-z0-9]{0,6}\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", re.I)
# "Rochelle, IL 61068-0601" — the +4 is optional but Rochelle publishes one, and
# without it that city's whole locality dropped out.
ZIP_RE = re.compile(r"^(.*),\s*IL\s*(\d{5})(?:-\d{4})?\s*$", re.I)
ADDR_LABEL_RE = re.compile(r"^(Physical|Mailing)\s+Address:\s*", re.I)
# "8763 N. Main St - Village Hall" — a descriptor, not part of the address; the
# card already labels the block "Village Hall".
HALL_SUFFIX_RE = re.compile(r"\s+-\s+(?:Village|City|Town)\s+Hall\s*$", re.I)

# "<office> <name>" lines. Ward-bearing seats are matched first so "Alderman
# Ward 2 Doug Wilken" does not fall through to the bare-office pattern with
# "Ward 2 Doug Wilken" as the name.
WARD_SEAT_RE = re.compile(r"^(Alderman|Alderperson|Alderwoman|Councilman|Councilwoman|Council Member)\s+"
                          r"Ward\s+(\d+)\s+(.+?)\s*$", re.I)
OFFICE_RE = re.compile(r"^(Mayor|President|Pres\.?|Clerk|Deputy Clerk|Treasurer|Collector|"
                       r"City Manager|Village Administrator|City Administrator|Administrator|"
                       r"Superintendent(?: of Public Works)?)\s+(.+?)\s*$", re.I)
# A bare group heading whose members follow one per indented line. "Councilmen"
# is Rochelle's word for its six at-large council seats, and its absence here
# was why the county's largest city shipped with a mayor, a clerk, a treasurer
# and no council at all.
GROUP_RE = re.compile(r"^(Trustees|Council Members|Councilmen|Councilwomen|"
                      r"Commissioners|Aldermen)\s*$", re.I)

APPOINTED = {"deputy clerk", "city manager", "village administrator",
             "city administrator", "administrator", "superintendent",
             "superintendent of public works"}
HEAD_TITLES = {"mayor", "president"}

MIN_MUNICIPALITIES = 11
MIN_OFFICIALS = 90
MIN_HEADS = 11


def norm_office(raw):
    o = re.sub(r"\s+", " ", (raw or "").strip()).rstrip(".")
    low = o.lower()
    if low in ("pres", "president"):
        return "President"
    return o.title() if low.islower() or o.isupper() else o


def clean(v):
    v = re.sub(r"\s+", " ", (v or "")).strip(" . ")
    return v or None


def fetch_pdf(url):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-ogle-municipal-officials-scraper")
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    if not resp.content.startswith(b"%PDF"):
        raise RuntimeError("yearbook URL did not return a PDF (got %d bytes of %s)"
                           % (len(resp.content), resp.headers.get("Content-Type")))
    return resp.content


# The headings this section has actually ended at. The bound is structural (the
# next ALL-CAPS heading) so a NEW heading still terminates correctly — but a
# stray capitalised line INSIDE the section would also terminate it, and losing
# the last one or two municipalities could slip under the count floors. So an
# unfamiliar terminator is reported: the run still writes, and the weekly PR
# carries the warning for a human.
KNOWN_END_HEADINGS = {"GENERAL INFORMATION", "OGLE COUNTY POLLING PLACES"}


def section_lines(pdf_bytes, warnings=None):
    if pypdf is None:
        raise RuntimeError("pypdf is required (pip install -c scripts/requirements.txt pypdf)")
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    start = START_RE.search(text)
    if not start:
        raise RuntimeError("could not find the CITIES & VILLAGES heading — the "
                           "yearbook's layout changed")
    lines = [l.rstrip() for l in text[start.end():].split("\n")]
    for i, line in enumerate(lines):
        heading = line.strip()
        if SECTION_HEADING_RE.match(heading):
            print("  section ends at %r (line %d)" % (heading, i), file=sys.stderr)
            if warnings is not None and re.sub(r"\s+", " ", heading) not in KNOWN_END_HEADINGS:
                warnings.append("section ended at an unfamiliar heading %r — check "
                                "that no municipality was cut off" % heading)
            return lines[:i]
    # Every edition so far ends the section with a heading. If one stops doing
    # so, the run should say why the shape changed rather than parse the rest of
    # the book as though it were still municipal officers.
    raise RuntimeError("no ALL-CAPS heading follows the CITIES & VILLAGES "
                       "section — the yearbook's layout changed")


def parse(lines, warnings):
    blocks, current = [], None
    for line in lines:
        m = MUNI_RE.match(line.strip())
        if m:
            current = {"kind": m.group(1), "name": clean(m.group(2)), "lines": []}
            blocks.append(current)
        elif current is not None:
            current["lines"].append(line)
    if not blocks:
        raise RuntimeError("no 'City/Village of X' headers in the section")

    municipalities, officials = [], []
    for b in blocks:
        name = b["name"]
        municipalities.append(name)
        body = "\n".join(b["lines"])
        phone = PHONE_RE.search(body)
        site = WEBSITE_RE.search(body)
        email = EMAIL_RE.search(body)
        # The header region is everything BEFORE the first officer line. Bounding
        # it matters: Adeline's hall block is all label lines ("Physical
        # Address:", "Phone: President - ...") that a skip-list filters out, and
        # an unbounded scan then took "Pres. Mike Dickinson" as the street.
        head_lines = []
        for l in b["lines"]:
            t = l.strip()
            if WARD_SEAT_RE.match(t) or OFFICE_RE.match(t) or GROUP_RE.match(t):
                break
            head_lines.append(l)

        # Twelve of the thirteen blocks give ONE address across several lines —
        # street, an optional P.O. Box, then "City, IL ZIP" — so street and
        # locality must be combined across lines. Adeline is the exception: it
        # labels a PHYSICAL and a MAILING address that are different places
        # (8763 vs 9069 N. Main St, and the mailing city is Leaf River, not
        # Adeline). Grouping by label keeps those two apart; blending them
        # produced a street and a city that never appeared together on any
        # document the county published.
        groups, current = {}, "physical"
        for l in head_lines:
            t = l.strip()
            label = ADDR_LABEL_RE.match(t)
            if label:
                current = label.group(1).lower()
                t = ADDR_LABEL_RE.sub("", t)
            if t:
                groups.setdefault(current, []).append(t)

        street = city = zipcode = None
        # The hall is where the office IS, so the physical address wins; the
        # mailing address is used only when it is the only one given. A physical
        # address with no city keeps its city empty rather than borrowing the
        # mailing address's — that is the blend this exists to prevent.
        for key in ("physical", "mailing"):
            lines_for = groups.get(key)
            if not lines_for:
                continue
            for t in lines_for:
                z = ZIP_RE.match(t)
                if z:
                    zipcode = z.group(2)
                    bits = [p.strip() for p in z.group(1).strip().rstrip(",").split(",") if p.strip()]
                    city = bits[-1] if bits else None
                    break
            for t in lines_for:
                if ZIP_RE.match(t):
                    continue
                if t.lower().startswith(("phone", "fax", "email", "meeting", "website")):
                    continue
                # a street line carries a number or a PO box; a stray label does not
                if not re.search(r"\d|P\.?\s?O\.?\s?Box", t, re.I):
                    continue
                street = HALL_SUFFIX_RE.sub("", t.split("  -")[0].strip()).rstrip(",")
                break
            if street or city:
                break

        shared = {
            "jurisdiction": "%s of %s" % (b["kind"], name),
            "office_address": street,
            "office_city": city,
            "office_state": "IL" if city else None,
            "office_zip": zipcode,
            "office_phone": clean(phone.group(1)) if phone else None,
            "office_email": clean(email.group(1)) if email else None,
            "website": clean(site.group(1)) if site else None,
        }

        group = None
        found = 0
        for raw in b["lines"]:
            line = raw.strip()
            if not line or ZIP_RE.match(line):
                continue
            if line.lower().startswith(("phone", "fax", "email", "meeting", "website",
                                        "physical address", "mailing address")):
                continue
            g = GROUP_RE.match(line)
            if g:
                lab = g.group(1).lower()
                group = ("Trustee" if lab == "trustees" else
                         "Alderperson" if lab == "aldermen" else
                         "Commissioner" if lab == "commissioners" else "Council Member")
                continue
            w = WARD_SEAT_RE.match(line)
            if w:
                officials.append(dict(shared, office=norm_office(w.group(1)),
                                      district="Ward %s" % w.group(2),
                                      name=clean(w.group(3))))
                found += 1
                group = None
                continue
            o = OFFICE_RE.match(line)
            if o:
                office = norm_office(o.group(1))
                officials.append(dict(shared, office=office, district=None,
                                      name=clean(o.group(2)),
                                      appointed=office.lower() in APPOINTED))
                found += 1
                group = None
                continue
            if group and raw.startswith((" ", "\t")):
                officials.append(dict(shared, office=group, district=None,
                                      name=clean(line)))
                found += 1
        if not found:
            warnings.append("no officers parsed for %s — check the yearbook layout" % name)
    return municipalities, officials


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--pdf", help="parse a local copy instead of fetching")
    args = ap.parse_args()

    pdf_bytes = open(args.pdf, "rb").read() if args.pdf else fetch_pdf(YEARBOOK_URL)
    warnings = []
    try:
        municipalities, officials = parse(section_lines(pdf_bytes, warnings), warnings)
    except Exception as e:  # noqa: BLE001
        print("FATAL: %s" % e, file=sys.stderr)
        sys.exit(1)
    for w in sorted(set(warnings)):
        print("  warning: %s" % w, file=sys.stderr)

    heads = sum(1 for p in officials if (p["office"] or "").lower() in HEAD_TITLES)
    seats = sum(1 for p in officials if p.get("district"))
    problems = []
    if len(municipalities) < MIN_MUNICIPALITIES:
        problems.append("%d municipalities < floor %d" % (len(municipalities), MIN_MUNICIPALITIES))
    if len(officials) < MIN_OFFICIALS:
        problems.append("%d officials < floor %d" % (len(officials), MIN_OFFICIALS))
    if heads < MIN_HEADS:
        problems.append("%d heads of government < floor %d" % (heads, MIN_HEADS))
    if problems:
        for p in problems:
            print("  FAIL: %s" % p, file=sys.stderr)
        print("FATAL: refusing to write a payload that lost coverage", file=sys.stderr)
        sys.exit(1)

    scraped_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for p in officials:
        p["source_url"] = YEARBOOK_URL
        p["scraped_at"] = scraped_at
    payload = {
        "county": "Ogle",
        "directory_url": YEARBOOK_URL,
        "officials_page": CLERK_PAGE,
        "scraped_at": scraped_at,
        "municipalities": [{"name": n, "source_url": YEARBOOK_URL,
                            "scraped_at": scraped_at} for n in municipalities],
        "officials": officials,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("scraped %d municipalities, %d officials (%d heads, %d ward seats) -> %s"
          % (len(municipalities), len(officials), heads, seats, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
