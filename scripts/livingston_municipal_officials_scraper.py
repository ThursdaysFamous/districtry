#!/usr/bin/env python3
"""
Scrape Livingston County's clerk yearbook into the payload
build_municipal_officials_roster.py consumes.

SOURCE. The County Clerk's yearbook ("Livingston County 2025-2026 Yearbook",
updated 06-2026 — the 2026-07-31 validation-pass finding) carries a CITY AND
VILLAGE OFFICIALS section listing every one of the county's sixteen
municipalities with its FULL governing body — head of government, clerk,
treasurer, appointed staff, and every trustee / council member / ward
alderperson — plus the hall address, phone, e-mail and website. Fairbury
(4 wards) and Pontiac (5 wards) elect alderpersons by ward, two per ward.

FETCH POSTURE: open. Plain `requests` with a browser UA gets both the county
homepage and the PDF.

URL DISCOVERY, not a hardcoded path. The yearbook lives under a
per-update filename ("Yearbook updated 06-2026.pdf", previously
"Yearbook updated 04 -2026.pdf" — the county's own spacing varies), linked
from the county homepage; the constant below is only the fallback.

WHY A LINE PARSER. Each municipality is a contact header, then one officer
per dot-leader line ("Mayor ........ David Slagel"), then a board-list header
("Alderpersons" / "Board of Trustees" / "City Council Members") followed by
comma-separated names — and pypdf's extraction preserves that exactly. Blocks
span page breaks (Campus's trustees land after the printed page number), so
the parser works one flat line stream, skipping bare page-number lines.

APPOINTED STAFF. The yearbook prints Administrator / Manager / Superintendent
rows beside the elected officers without marking them; those offices are
statutorily appointed under the Illinois Municipal Code, never elected, so
they ship with appointed=True — the card must not imply an election that does
not exist. Clerk and Treasurer are NOT flagged: Illinois municipalities
genuinely differ on electing them, and the yearbook does not say.

TWO-NAME ROWS. "Ward 1 ..... Jon Kinate & Bruce Weber" (every ward seats two
alderpersons) and Chatsworth's two superintendents share one row; names are
split on the ampersand.

WHAT IS DELIBERATELY NOT COLLECTED: nothing per-person. The address, phone,
e-mail and website are the municipality's, and are carried at that level only.
The yearbook's township / fire / school sections are out of scope here.

Usage:
    python3 livingston_municipal_officials_scraper.py --out livingston_municipal_officials.json
    python3 livingston_municipal_officials_scraper.py --out out.json --pdf local.pdf
"""

import argparse
import datetime
import io
import json
import re
import sys
import urllib.parse

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_CHROME_WIN_126,
    require_robots_once,
)

try:
    import pypdf
except ImportError:  # pragma: no cover
    pypdf = None

REFERENCE_PAGE = "https://www.livingstoncountyil.gov/"
# Fallback only — the live URL is read off REFERENCE_PAGE (see module docstring).
YEARBOOK_URL = ("https://www.livingstoncountyil.gov/Documents/Government/"
                "Yearbook%20updated%2006-2026.pdf")
HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
}
REQUEST_TIMEOUT = 120

# The county's Revize CMS renders attributes as `href= "..."` (space after the
# equals) and declares a <base href>, so both are handled below.
YEARBOOK_LINK_RE = re.compile(r'href=\s*"([^"]*[Yy]earbook[^"]*\.pdf[^"]*)"')

# Both bounds anchored to a WHOLE LINE (the TOC repeats headings with dot
# leaders). The far bound is the fire-service section that follows the
# municipalities; ELECTION DATES is the fallback if MABAS is ever renamed.
START_RE = re.compile(r"^CITY AND VILLAGE OFFICIALS$", re.I)
END_RE = re.compile(r"^(MABAS DIVISION|ELECTION DATES)", re.I)

MUNI_RE = re.compile(r"^(CITY|VILLAGE|TOWN) OF ([A-Z][A-Z .'’-]+?)\s*$")
PHONE_RE = re.compile(r"Phone:\s*\(?(\d{3})\)?[-.\s]*(\d{3})[-.\s]*(\d{4})", re.I)
EMAIL_RE = re.compile(r"Email:\s*(\S+@\S+?)(?:\s*\||\s*$)", re.I)
WEBSITE_RE = re.compile(r"Website:\s*(\S+?)(?:\s*\||\s*$)", re.I)
CITY_ZIP_RE = re.compile(r"^(?:(.*),\s*)?([A-Za-z][A-Za-z .'-]*),\s*IL\s*(\d{5})(?:-\d{4})?\s*$")
PO_BOX_RE = re.compile(r",?\s*P\.?\s?O\.?\s?Box\s+\d+,?\s*$", re.I)

# "Mayor ........ David Slagel" — offices the yearbook prints as dot-leader rows.
OFFICE_RE = re.compile(r"^(Mayor|President|Clerk|Treasurer|Collector|Administrator|"
                       r"Manager|Superintendent|Supt\.?)\s*\.{3,}\s*(.+?)\s*$", re.I)
# "Ward 1 ....... Jon Kinate & Bruce Weber" under an Alderpersons header.
WARD_RE = re.compile(r"^Ward\s+(\d+)\s*\.{3,}\s*(.+?)\s*$", re.I)
# "Board of Trustees" / "Board of Trustees:" / "Alderpersons" / "City Council
# Members" — the header before a comma-separated name list.
BOARD_HEADER_RE = re.compile(r"^(Board of Trustees|Trustees|Alderpersons|Aldermen|"
                             r"City Council Members|Council Members)\s*:?\s*$", re.I)
PAGE_NO_RE = re.compile(r"^\d{1,3}\s*$")

# Statutorily appointed staff titles (see module docstring).
APPOINTED_TITLES = {"administrator", "manager", "superintendent", "supt", "supt."}
BOARD_TITLES = {"board of trustees": "Trustee", "trustees": "Trustee",
                "alderpersons": "Alderperson", "aldermen": "Alderman",
                "city council members": "Council Member",
                "council members": "Council Member"}
NON_PERSON_NAMES = {"vacant", "vacancy", "unassigned", "open", "tbd", "none", "n/a"}
HEAD_TITLES = {"mayor", "president"}

MIN_MUNICIPALITIES = 14
MIN_OFFICIALS = 110
MIN_HEADS = 14
MIN_WARD_SEATS = 14


def clean(value):
    value = re.sub(r"\s+", " ", (value or "")).strip().strip(",")
    return value or None


def discover_pdf_url(warnings):
    try:
        require_robots_once(REFERENCE_PAGE, HEADERS["User-Agent"], headers=HEADERS,
                            label="il-livingston-municipal-officials-scraper")
        resp = requests.get(REFERENCE_PAGE, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        warnings.append("could not read %s (%s) — falling back to the last known "
                        "yearbook URL" % (REFERENCE_PAGE, exc))
        return YEARBOOK_URL
    links = YEARBOOK_LINK_RE.findall(resp.text)
    if not links:
        warnings.append("no *Yearbook*.pdf link on %s — falling back to the last "
                        "known yearbook URL" % REFERENCE_PAGE)
        return YEARBOOK_URL
    base_match = re.search(r'<base\s+href=\s*"([^"]+)"', resp.text, re.I)
    base = base_match.group(1) if base_match else resp.url
    # The update stamp in the filename sorts by month within the edition year;
    # the highest path is the current one if several stay linked.
    return sorted(urllib.parse.urljoin(base, href.replace(" ", "%20"))
                  for href in links)[-1]


def fetch_pdf(url):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-livingston-municipal-officials-scraper")
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    if not resp.content.startswith(b"%PDF"):
        raise RuntimeError("yearbook URL did not return a PDF (got %d bytes of %s)"
                           % (len(resp.content), resp.headers.get("Content-Type")))
    return resp.content


def section_lines(pdf_bytes):
    if pypdf is None:
        raise RuntimeError("pypdf is required (pip install -c scripts/requirements.txt pypdf)")
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    lines = [l.rstrip() for l in text.split("\n")]
    start = next((i for i, l in enumerate(lines) if START_RE.match(l.strip())), None)
    if start is None:
        raise RuntimeError("could not find the 'CITY AND VILLAGE OFFICIALS' heading "
                           "— the yearbook's layout changed")
    end = next((i for i in range(start + 1, len(lines))
                if END_RE.match(lines[i].strip())), None)
    if end is None:
        raise RuntimeError("could not find the MABAS/ELECTION DATES heading that "
                           "bounds the municipal section")
    return lines[start + 1:end]


def parse_hall(lines):
    """-> (street, city, zip, phone, email, website) from a block's header."""
    street = city = zipcode = phone = email = website = None
    for raw in lines:
        text = clean(raw)
        if not text:
            continue
        m = PHONE_RE.search(text)
        if m and not phone and not re.search(r"Fax:\s*\(?%s" % m.group(1), text[:text.find(m.group(2))], re.I):
            phone = "%s-%s-%s" % m.groups()
        m = EMAIL_RE.search(text)
        if m and not email:
            email = m.group(1).lower().rstrip(".,")
        m = WEBSITE_RE.search(text)
        if m and not website:
            website = m.group(1).lower().rstrip("/.,")
        if re.match(r"^(Phone|Fax|Email|Website)\b", text, re.I):
            continue
        m = CITY_ZIP_RE.match(text)
        if m:
            city, zipcode = clean(m.group(2)), m.group(3)
            lead = clean(m.group(1))
            if lead and not street:
                street = lead
            continue
        if re.search(r"\d|P\.?\s?O\.?\s?Box", text, re.I) and not street:
            street = clean(text)
    # A physical street beats the mailing box; the box stays only when it is
    # all the municipality publishes (Reddick, Strawn).
    if street and not PO_BOX_RE.match(street):
        trimmed = PO_BOX_RE.sub("", street)
        if trimmed.strip():
            street = clean(trimmed)
    return street, city, zipcode, phone, email, website


def split_names(text):
    """A comma/ampersand-separated printed list -> individual names."""
    parts = []
    for chunk in re.split(r",| & | and ", text):
        name = clean(chunk.replace("&", " "))
        if name:
            parts.append(name)
    return parts


def parse(lines, warnings):
    blocks, current = [], None
    for line in lines:
        text = line.strip()
        if PAGE_NO_RE.match(text):
            continue
        match = MUNI_RE.match(text)
        if match:
            current = {"kind": match.group(1).capitalize(),
                       "name": clean(match.group(2)).title(), "lines": []}
            blocks.append(current)
        elif current is not None:
            current["lines"].append(line)
    if not blocks:
        raise RuntimeError("no 'CITY/VILLAGE/TOWN OF X' headers in the section")

    municipalities, officials = [], []
    for block in blocks:
        name = block["name"]
        jurisdiction = "%s of %s" % (block["kind"], name)
        municipalities.append(name)
        street, city, zipcode, phone, email, website = parse_hall(block["lines"][:6])

        shared = {
            "jurisdiction": jurisdiction,
            "office_address": street,
            "office_city": city,
            "office_state": "IL" if city else None,
            "office_zip": zipcode,
            "office_phone": phone,
            "office_email": email,
            "website": website,
        }

        rows = []
        board_office = None      # active "Board of Trustees"-style list context
        for raw in block["lines"]:
            text = clean(raw)
            if not text or re.match(r"^(Phone|Fax|Email|Website)\b", text, re.I):
                continue
            if CITY_ZIP_RE.match(text) and not OFFICE_RE.match(text):
                continue
            header = BOARD_HEADER_RE.match(text)
            if header:
                board_office = BOARD_TITLES[header.group(1).lower()]
                continue
            ward = WARD_RE.match(text)
            if ward:
                # Ward rows only appear under an Alderpersons header; each row
                # seats two.
                office = board_office or "Alderperson"
                for person in split_names(ward.group(2)):
                    rows.append({"office": office, "district": "Ward %s" % ward.group(1),
                                 "name": person})
                continue
            office_row = OFFICE_RE.match(text)
            if office_row:
                board_office = None
                title = office_row.group(1).rstrip(".").capitalize()
                for person in split_names(office_row.group(2)):
                    row = {"office": title, "district": None, "name": person}
                    if title.lower() in APPOINTED_TITLES:
                        row["appointed"] = True
                    rows.append(row)
                continue
            if board_office:
                # A comma-separated trustee list, possibly wrapping lines.
                for person in split_names(text):
                    rows.append({"office": board_office, "district": None,
                                 "name": person})
                continue
            if re.search(r"\.{3,}", text):
                warnings.append("unparsed officer row in %s: '%s'" % (jurisdiction, text))

        if not rows:
            warnings.append("no officers parsed for %s — check the yearbook layout" % name)
            continue

        head_names = {r["name"].lower() for r in rows
                      if (r["office"] or "").lower() in HEAD_TITLES and r.get("name")}
        for row in rows:
            person = row.get("name")
            if not person or person.lower() in NON_PERSON_NAMES:
                warnings.append("dropped a %s seat published as '%s' in %s"
                                % (row["office"], person or "(blank)", jurisdiction))
                continue
            office_low = (row["office"] or "").lower()
            if office_low not in HEAD_TITLES and person.lower() in head_names:
                warnings.append("dropped the %s row for %s in %s — the same person "
                                "is published as the head of government"
                                % (row["office"], person, jurisdiction))
                continue
            record = dict(shared, office=row["office"], district=row.get("district"),
                          name=person)
            if row.get("appointed"):
                record["appointed"] = True
            officials.append(record)
    return municipalities, officials


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--pdf", help="parse a local copy instead of fetching")
    args = parser.parse_args()

    warnings = []
    try:
        if args.pdf:
            source_url, pdf_bytes = YEARBOOK_URL, open(args.pdf, "rb").read()
        else:
            source_url = discover_pdf_url(warnings)
            pdf_bytes = fetch_pdf(source_url)
        municipalities, officials = parse(section_lines(pdf_bytes), warnings)
    except Exception as exc:  # noqa: BLE001
        print("FATAL: %s" % exc, file=sys.stderr)
        sys.exit(1)

    for warning in sorted(set(warnings)):
        print("  warning: %s" % warning, file=sys.stderr)

    heads = sum(1 for p in officials if (p["office"] or "").lower() in HEAD_TITLES)
    seats = sum(1 for p in officials if p.get("district"))
    problems = []
    if len(municipalities) < MIN_MUNICIPALITIES:
        problems.append("%d municipalities < floor %d" % (len(municipalities), MIN_MUNICIPALITIES))
    if len(officials) < MIN_OFFICIALS:
        problems.append("%d officials < floor %d" % (len(officials), MIN_OFFICIALS))
    if heads < MIN_HEADS:
        problems.append("%d heads of government < floor %d" % (heads, MIN_HEADS))
    # Fairbury's 8 + Pontiac's 10 ward-alderperson rows are the part of this
    # payload the municipal-ward layer joins to; a shape change that broke only
    # the "Ward N ....." rows would pass every count above.
    if seats < MIN_WARD_SEATS:
        problems.append("%d ward seats < floor %d" % (seats, MIN_WARD_SEATS))
    if problems:
        for problem in problems:
            print("  FAIL: %s" % problem, file=sys.stderr)
        print("FATAL: refusing to write a payload that lost coverage", file=sys.stderr)
        sys.exit(1)

    display_url = source_url.split("?")[0]
    scraped_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for record in officials:
        record["source_url"] = display_url
        record["scraped_at"] = scraped_at
    payload = {
        "county": "Livingston",
        "directory_url": display_url,
        "officials_page": REFERENCE_PAGE,
        "scraped_at": scraped_at,
        "municipalities": [{"name": n, "source_url": display_url,
                            "scraped_at": scraped_at} for n in municipalities],
        "officials": officials,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("scraped %d municipalities, %d officials (%d heads, %d ward seats) -> %s"
          % (len(municipalities), len(officials), heads, seats, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
