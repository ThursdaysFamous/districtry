#!/usr/bin/env python3
"""
Kane County Municipal Officials Scraper (County Clerk Government Guide)
======================================================================
Extracts every Kane County municipality's head of government and municipal
clerk — plus village/city hall address, phone, e-mail, and official website —
from the Kane County Clerk's annually issued Government Guide.

Why this source: the Clerk's Government Guide
(clerk.kanecountyil.gov/elections -> "Government Guide") is the county's own
published record of who holds each local office, and its "Cities and Village
Officials" section covers every Kane municipality in one document. Kane's
county GIS carries municipal boundaries but no officials data, and no council
of governments publishes a competing roster, so this is rung 2 of the source
ladder (docs/EXPANSION_GUIDE.md §3.4).

DEPTH: head of government + municipal clerk only. The guide does NOT print
trustees or aldermen, so this county ships a `head` with no `board` — an
honest mayor-level entry, never a fabricated or partial council. The
Municipality card links the village's own site for the full board.

The PDF is a text PDF with a stable two-column visual layout, so it is parsed
in pypdf's layout mode: each entry is anchored by its "<Name> ... www.site"
header line, and the fields below it are matched positionally. A
line-flattened extraction glues the right-hand column onto the left and is
NOT usable here (docs/EXPANSION_GUIDE.md §3.4, PDF-parse lessons).

Scope note: the same guide prints Township, Park/Library District, and School
District sections. Only the municipal section is parsed here — the township
roster exists since 2026-08-19 (township-officials.json; Cook ships, Kane is
a recorded candidate via this same guide) — and the section stays bounded
explicitly so the township scrape, when Kane joins it, is additive.

Usage:
    python3 kane_municipal_officials_scraper.py --out kane_municipal_officials.json

Notes on data honesty (per project conventions):
- Fields that can't be parsed are stored as null, never guessed.
- Every record includes `source_url` and `scraped_at` for traceability.
- Contact fields are MUNICIPALITY-level (one village hall per entry, shared by
  its officers), so they are emitted under the municipality and never as a
  person's own contact — the guide prints no per-person phone or e-mail.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone

import requests
from scraper_common import require_robots_once, UA_CHROME_WIN_124  # noqa: E402  (shared machinery — do not fork)

GUIDE_URL = "https://clerk.kanecountyil.gov/Elections/Documents/GovernmentGuide.pdf"
ELECTIONS_URL = "https://clerk.kanecountyil.gov/elections"

HEADERS = {
    "User-Agent": UA_CHROME_WIN_124,
}
REQUEST_TIMEOUT = 120

# Section bounds inside the guide. Matched as plain substrings on a whitespace
# collapsed line, longest-first, because layout mode pads headings with runs of
# spaces and a \b-anchored pattern fails silently against them.
SECTION_START = "Cities and Village Officials"
SECTION_END = "Township Officials"

# Cities elect a Mayor, villages a President; the guide groups them under these
# headings and prints the matching office label on each entry.
GROUP_HEADINGS = {"CITIES": "city", "VILLAGES": "village"}

# An entry header: the municipality name at the left margin, its website at the
# right. Two-plus spaces is the column gutter.
ENTRY_RE = re.compile(
    r"^\s{0,40}(?P<name>[A-Z][A-Za-z.'’\- ]+?)\s{2,}(?P<web>www\.\S+)\s*$"
)
# "44 E. Downer Pl., Aurora, 60505 .......... 630/256-4636"
ADDRESS_RE = re.compile(
    r"^\s*(?P<pre>.+?)\s+(?P<zip>\d{5})\s*\.{2,}\s*(?P<phone>\d{3}[/-]\d{3}-\d{4})",
    re.M,
)
EMAIL_RE = re.compile(r"E-?[Mm]ail:\s*(?P<email>[^\s]+@[^\s]+)")
HEAD_RE = re.compile(r"\b(?P<office>Mayor|President):\s*(?P<name>.+?)(?:\s{2,}|$)", re.M)
CLERK_RE = re.compile(r"\bClerk:\s*(?P<name>.+?)(?:\s{2,}|$)", re.M)

# Deliberate under-tolerance against the verified 2026-07 live value (29
# municipalities: 5 cities + 24 villages). Census lists 30 incorporated places
# touching Kane; the guide prints the ones the county administers, so the floor
# sits below both.
MIN_MUNICIPALITIES = 26
MIN_HEADS = 26


def fetch_pdf(url):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-kane-municipal-officials-scraper")
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    body = resp.content
    if not body.startswith(b"%PDF"):
        print("FATAL: %s did not return a PDF (got %d bytes of %s) — source moved "
              "or challenged" % (url, len(body), resp.headers.get("Content-Type")),
              file=sys.stderr)
        sys.exit(1)
    return body


def guide_text(body):
    """Layout-mode text of the whole guide, page-joined."""
    import io

    import pypdf

    reader = pypdf.PdfReader(io.BytesIO(body))
    return "\n".join(
        (page.extract_text(extraction_mode="layout") or "") for page in reader.pages
    )


def municipal_section(text):
    start = text.find(SECTION_START)
    if start < 0:
        print("FATAL: '%s' heading not found — the guide's structure changed"
              % SECTION_START, file=sys.stderr)
        sys.exit(1)
    end = text.find(SECTION_END, start)
    if end < 0:
        print("FATAL: '%s' heading not found after the municipal section — cannot "
              "bound the parse" % SECTION_END, file=sys.stderr)
        sys.exit(1)
    return text[start:end]


def clean(value):
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def split_address(pre, zipcode, name):
    """-> (street, city). Peel the municipality name off the tail as the city.

    Most entries read "<street>, <City>, <zip>", but some omit the comma before
    the city ("234 S. State St., (P.O. Box 457) Hampshire, 60140"), so a plain
    rsplit on the last comma mis-parses them. The municipality's own name is
    the reliable anchor; anything else falls back to the last comma, and an
    undelimitable address returns the whole string as the street rather than a
    guessed split.
    """
    pre = (pre or "").strip().rstrip(",").strip()
    if not pre:
        return None, None
    if name and pre.lower().endswith(name.lower()):
        street = pre[: -len(name)].strip().rstrip(",").strip()
        return (street or None), name
    if "," in pre:
        street, city = pre.rsplit(",", 1)
        return (street.strip() or None), (city.strip() or None)
    return pre, None


def parse_entries(section):
    """-> [{name, kind, website, body}] in document order."""
    entries = []
    current = None
    kind = None
    for line in section.splitlines():
        stripped = line.strip()
        if stripped in GROUP_HEADINGS:
            kind = GROUP_HEADINGS[stripped]
            continue
        match = ENTRY_RE.match(line)
        if match:
            current = {
                "name": clean(match.group("name")),
                "kind": kind,
                "website": clean(match.group("web")),
                "lines": [],
            }
            entries.append(current)
            continue
        if current is not None and stripped:
            current["lines"].append(line)
    return entries


def records_for(entry, scraped_at):
    """-> list of official records for one municipality (head, then clerk)."""
    body = "\n".join(entry["lines"])
    name = entry["name"]

    address = ADDRESS_RE.search(body)
    street, city = (None, None)
    zipcode = phone = None
    if address:
        street, city = split_address(address.group("pre"), address.group("zip"), name)
        zipcode = address.group("zip")
        # The guide writes phones as 630/256-4636; the builder reformats to the
        # card's 630-256-4636 shape.
        phone = address.group("phone")
    email = EMAIL_RE.search(body)
    head = HEAD_RE.search(body)
    clerk = CLERK_RE.search(body)

    # The guide groups entries under CITIES / VILLAGES; carrying that form into
    # the jurisdiction name matches the Cook source's "Village of Alsip" shape,
    # which is what the card reads to title the hall row. The builder strips the
    # prefix again before joining on GEOID.
    prefix = {"city": "City of ", "village": "Village of "}.get(entry["kind"], "")
    shared = {
        "jurisdiction": prefix + name if prefix else name,
        "district": None,
        "office_address": street,
        "office_city": city,
        "office_state": "IL" if city else None,
        "office_zip": zipcode,
        "office_phone": phone,
        "office_email": clean(email.group("email")) if email else None,
        "website": entry["website"],
        "source_url": GUIDE_URL,
        "scraped_at": scraped_at,
    }

    out = []
    if head:
        out.append(dict(shared, office=clean(head.group("office")),
                        name=clean(head.group("name"))))
    if clerk:
        out.append(dict(shared, office="Clerk", name=clean(clerk.group("name"))))
    if not out:
        # Never drop a municipality silently: an entry whose officers did not
        # parse is reported so a human sees it, and contributes no invented row.
        print("WARNING: no officers parsed for %s — check the guide's layout" % name,
              file=sys.stderr)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", default="kane_municipal_officials.json")
    parser.add_argument("--pdf", help="parse a local PDF instead of fetching (testing)")
    args = parser.parse_args()

    scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if args.pdf:
        with open(args.pdf, "rb") as f:
            body = f.read()
    else:
        body = fetch_pdf(GUIDE_URL)

    section = municipal_section(guide_text(body))
    entries = parse_entries(section)

    records = []
    for entry in entries:
        records.extend(records_for(entry, scraped_at))

    municipalities = sorted({r["jurisdiction"] for r in records})
    heads = [r for r in records if r["office"] in ("Mayor", "President")]
    if len(municipalities) < MIN_MUNICIPALITIES:
        print("FATAL: parsed %d municipalities (expected >= %d) — the guide's layout "
              "changed or the fetch was partial" % (len(municipalities), MIN_MUNICIPALITIES),
              file=sys.stderr)
        sys.exit(1)
    if len(heads) < MIN_HEADS:
        print("FATAL: parsed %d heads of government (expected >= %d)"
              % (len(heads), MIN_HEADS), file=sys.stderr)
        sys.exit(1)

    payload = {
        "county": "Kane",
        "directory_url": ELECTIONS_URL,
        "scraped_at": scraped_at,
        "officials": records,
    }
    with open(args.out, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print("scraped %d municipalities, %d officials (%d heads of government) -> %s"
          % (len(municipalities), len(records), len(heads), args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
