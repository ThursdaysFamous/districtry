#!/usr/bin/env python3
"""
Scrape the Whiteside County Yearbook into the payload
build_municipal_officials_roster.py consumes.

SOURCE. The County Clerk publishes a 68-page "Whiteside County Yearbook
2025 - 2026" through the county's CivicPlus DocumentCenter. Clerk Karen Stralow
named it on 2026-08-03, and her wording was exact: it "has SOME municipal
officials listed". Its index confirms the limit — "Mayors of Whiteside County"
on printed page 41 and "City Clerks" on 43, and nothing for trustees or
aldermen anywhere. So Whiteside joins at the MAYOR-AND-CLERK tier, like Kane,
McHenry, Kendall and Carroll, rather than as a full-governing-body county. The
edition covers 2025-2026, i.e. after the April 2025 consolidated election.

WHY LINE PARSING IS ENOUGH. Each entry is a municipality name on its own line
followed by one or two wrapped lines of "Name, address … Phone: nnn-nnn-nnnn".
Nothing pairs across columns and nothing wraps ambiguously, so word positions
would be ceremony. What the parse does need is the municipality list, which is
taken from the MAYORS section and then used to anchor the clerks section — the
same anchoring Henry needed, for the same reason: a name on its own line is
only recognisable as a place if you already know the places.

THE "(Office)" MARKER IS THE WHOLE ADDRESS RULE, and it is the county's own
distinction rather than an inference of mine. Eight of the eleven mayors' rows
end "Phone: … (Office)" and carry the city hall — Fulton's mayor and clerk both
sit at 415 11th Ave. The three that do not (Coleta, Deer Grove, Tampico's
mayor) carry something else: Coleta's mayor is at 110 Summit St and Coleta's
clerk at 211 S. Main, which are two different houses, not one village office.
So an address ships ONLY from a row the county marks "(Office)". Unmarked rows
ship the name and the phone — a published contact for the office — and no
address at all.

Usage:
    python3 whiteside_municipal_officials_scraper.py --out whiteside_municipal_officials.json
    python3 whiteside_municipal_officials_scraper.py --out out.json --pdf local.pdf
"""

import argparse
import datetime
import io
import json
import re
import sys

import requests
from scraper_common import require_robots_once, UA_ROSTER_BOT  # noqa: E402  (shared machinery — do not fork)

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

CLERK_PAGE = "https://www.whitesidecountyil.gov/235/County-Clerk"
YEARBOOK_FALLBACK = ("https://www.whitesidecountyil.gov/DocumentCenter/View/236/"
                     "County-Clerk-Year-Book-PDF")
COUNTY_SITE = "https://www.whitesidecountyil.gov/"
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
}
REQUEST_TIMEOUT = 120

MAYORS_TITLE_RE = re.compile(r"(?im)^\s*MAYORS\s+OF\s+WHITESIDE\s+COUNTY\s*$")
CLERKS_TITLE_RE = re.compile(r"(?im)^\s*CITY\s+CLERKS\s*$")
# A place heading: a short line of words, no digits, no comma, no "Phone:".
PLACE_RE = re.compile(r"^[A-Z][A-Za-z.'-]*(?:\s+[A-Z][A-Za-z.'-]*){0,2}$")
PHONE_RE = re.compile(r"(?i)Phone:\s*\(?(\d{3})\)?[\s.\-]?(\d{3})[\s.\-]?(\d{4})")
OFFICE_MARK_RE = re.compile(r"(?i)\(\s*Office\s*\)")
ZIP_RE = re.compile(r"\b(6\d{4})\b")
PAGE_NUM_RE = re.compile(r"^\d{1,3}$")
NON_PERSON = ("vacant", "vacancy", "(vacancy)", "n/a", "")

MIN_MUNICIPALITIES = 9
MIN_HEADS = 9
MIN_OFFICIALS = 18


def discover_pdf_url(session, warnings):
    """Read the yearbook link off the clerk page; fall back to the known id."""
    try:
        require_robots_once(CLERK_PAGE, HEADERS["User-Agent"], headers=HEADERS,
                            label="il-whiteside-municipal-officials-scraper")
        resp = session.get(CLERK_PAGE, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001 — discovery is best-effort
        warnings.append("could not read %s (%s) — using the recorded yearbook URL"
                        % (CLERK_PAGE, type(exc).__name__))
        return YEARBOOK_FALLBACK
    match = re.search(r'href="(/DocumentCenter/View/\d+/[^"]*(?:Year[-_ ]?Book|Yearbook)[^"]*)"',
                      resp.text, re.I)
    if not match:
        warnings.append("the clerk page no longer links a Year Book document — "
                        "using the recorded URL, which may be stale")
        return YEARBOOK_FALLBACK
    return COUNTY_SITE.rstrip("/") + match.group(1)


def fetch_pdf(session, url):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-whiteside-municipal-officials-scraper")
    resp = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    if not resp.content.startswith(b"%PDF"):
        raise RuntimeError("%s did not return a PDF (got %d bytes of %s)"
                           % (url, len(resp.content), resp.headers.get("Content-Type")))
    return resp.content


def section_lines(pdf_bytes, title_re, label):
    """The lines of the page whose text carries `title_re`, after the title."""
    if pdfplumber is None:
        raise RuntimeError("pdfplumber is required "
                           "(pip install -c scripts/requirements.txt pdfplumber)")
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if not title_re.search(text):
                continue
            lines = [re.sub(r"\s+", " ", l).strip() for l in text.splitlines()]
            lines = [l for l in lines if l and not PAGE_NUM_RE.match(l)]
            start = next(i for i, l in enumerate(lines) if title_re.match(l))
            return lines[start + 1:]
    raise RuntimeError("the yearbook has no '%s' section — its layout has changed"
                       % label)


def parse_section(lines, office, places, warnings):
    """-> ([place names in order], [records]). `places` anchors the clerks pass."""
    found, records = [], []
    current = None
    buffer = []

    def flush():
        if current is None or not buffer:
            return
        blob = " ".join(buffer)
        name = blob.split(",", 1)[0].strip()
        if not name or name.lower() in NON_PERSON:
            warnings.append("%s: %s row carries no name — counted, never named"
                            % (current, office))
            return
        phone = PHONE_RE.search(blob)
        is_office = bool(OFFICE_MARK_RE.search(blob))
        record = {
            "jurisdiction": current,
            "office": office,
            "name": name,
            "district": None,
            "appointed": False,
            "person_phone": None,
            "office_phone": "%s-%s-%s" % phone.groups() if (phone and is_office) else None,
        }
        if phone and not is_office:
            # Not marked "(Office)", so it is the officer's own line rather than
            # the hall's — published as the way to reach them, and kept as such.
            record["person_phone"] = "%s-%s-%s" % phone.groups()
        if is_office:
            # ONLY a row the county marks as an office contributes an address.
            street = blob.split(",", 1)[1] if "," in blob else ""
            street = PHONE_RE.sub(" ", street)
            street = OFFICE_MARK_RE.sub(" ", street)
            zipcode = ZIP_RE.search(street)
            street = ZIP_RE.sub(" ", street)
            # Trim the trailing town name the yearbook repeats before the ZIP.
            street = re.sub(r"(?i)[\s,]*%s[\s,]*$" % re.escape(current), "", street.strip())
            street = re.sub(r"\s+", " ", street).strip(" ,.")
            record["office_address"] = street or None
            record["office_zip"] = zipcode.group(1) if zipcode else None
        record["office_city"] = current
        record["office_state"] = "IL"
        records.append(record)

    for line in lines:
        candidate = line.strip()
        is_place = (PLACE_RE.match(candidate) and "Phone" not in candidate
                    and not ZIP_RE.search(candidate))
        if places is not None:
            is_place = is_place and candidate in places
        if is_place:
            flush()
            buffer = []
            current = candidate
            if current not in found:
                found.append(current)
            continue
        if current is None:
            continue
        buffer.append(candidate)
    flush()
    return found, records


def parse(pdf_bytes, source_url, warnings):
    mayor_lines = section_lines(pdf_bytes, MAYORS_TITLE_RE, "MAYORS OF WHITESIDE COUNTY")
    clerk_lines = section_lines(pdf_bytes, CLERKS_TITLE_RE, "CITY CLERKS")

    places, mayors = parse_section(mayor_lines, "Mayor", None, warnings)
    if not places:
        raise RuntimeError("no municipalities parsed from the mayors section — "
                           "the clerks section anchors on that list")
    _, clerks = parse_section(clerk_lines, "Clerk", set(places), warnings)

    officials = mayors + clerks
    # The hall ADDRESS is the municipality's, so a value found on either row
    # serves both.
    hall = {}
    for record in officials:
        slot = hall.setdefault(record["jurisdiction"], {})
        for key in ("office_address", "office_zip"):
            if record.get(key) and not slot.get(key):
                slot[key] = record[key]

    # The PHONE is not necessarily the municipality's, and assuming it was lost
    # real data. Four of the eight halls print a DIFFERENT office number for the
    # mayor than for the clerk — Rock Falls 815-622-1110 against 815-622-1100,
    # and likewise Fulton, Prophetstown and Sterling — so those are direct lines
    # at one hall, not one switchboard. Taking the first and applying it to both
    # silently replaced the clerk's number with the mayor's.
    #
    # So: a place whose office-marked rows AGREE has a hall phone and no
    # personal ones; a place whose rows DIFFER has no single hall number to
    # state, and each officer keeps their own.
    marked = {}
    for record in officials:
        if record.get("office_phone"):
            marked.setdefault(record["jurisdiction"], []).append(record["office_phone"])
    for record in officials:
        numbers = set(marked.get(record["jurisdiction"], []))
        own = record.pop("office_phone", None)
        if len(numbers) == 1:
            record["office_phone"] = next(iter(numbers))
        elif own:
            record["person_phone"] = own
            warnings.append("%s: the yearbook prints a different office line for "
                            "the %s than for the other officer — kept as a direct "
                            "number rather than collapsed into one hall phone"
                            % (record["jurisdiction"], record["office"].lower()))
    for record in officials:
        for key, value in hall.get(record["jurisdiction"], {}).items():
            record[key] = value
        # A "personal" number that is also the hall's is the hall's.
        if record.get("person_phone") and record["person_phone"] == record.get("office_phone"):
            record["person_phone"] = None
        record["source_url"] = source_url

    without_hall = [p for p in places if not hall.get(p, {}).get("office_address")]
    for place in without_hall:
        warnings.append("%s: neither its mayor nor its clerk row is marked "
                        "'(Office)', so no address ships — the yearbook prints "
                        "what appear to be residences for both" % place)
    return places, officials


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--pdf", help="parse a local copy instead of fetching")
    args = ap.parse_args()

    warnings = []
    session = requests.Session()
    try:
        if args.pdf:
            source_url, pdf_bytes = YEARBOOK_FALLBACK, open(args.pdf, "rb").read()
        else:
            source_url = discover_pdf_url(session, warnings)
            pdf_bytes = fetch_pdf(session, source_url)
        places, officials = parse(pdf_bytes, source_url, warnings)
    except Exception as exc:  # noqa: BLE001
        print("FATAL: %s" % exc, file=sys.stderr)
        sys.exit(1)

    for warning in sorted(set(warnings)):
        print("  warning: %s" % warning, file=sys.stderr)

    heads = sum(1 for o in officials if o["office"] == "Mayor")
    problems = []
    if len(places) < MIN_MUNICIPALITIES:
        problems.append("%d municipalities < floor %d" % (len(places), MIN_MUNICIPALITIES))
    if len(officials) < MIN_OFFICIALS:
        problems.append("%d officials < floor %d" % (len(officials), MIN_OFFICIALS))
    if heads < MIN_HEADS:
        problems.append("%d mayors < floor %d" % (heads, MIN_HEADS))
    if problems:
        for problem in problems:
            print("  FAIL: %s" % problem, file=sys.stderr)
        print("FATAL: refusing to write a payload that lost coverage", file=sys.stderr)
        sys.exit(1)

    payload = {
        "county": "Whiteside",
        "directory_url": source_url,
        "officials_page": CLERK_PAGE,
        "scraped_at": datetime.datetime.now(datetime.timezone.utc)
                              .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "municipalities": places,
        "officials": officials,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    with_addr = len({o["jurisdiction"] for o in officials if o.get("office_address")})
    print("scraped %d municipalities, %d officials (%d mayors, %d clerks), "
          "%d with an office address -> %s"
          % (len(places), len(officials), heads, len(officials) - heads,
             with_addr, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
