#!/usr/bin/env python3
"""
Scrape Tazewell County's clerk yearbook into the payload
build_municipal_officials_roster.py consumes.

SOURCE. The County Clerk & Recorder publishes a "FULL YEARBOOK" PDF whose
"OFFICERS OF CITIES AND VILLAGES OF TAZEWELL COUNTY" section lists every
municipality with its FULL governing body — head of government, clerk,
treasurer, and every trustee or alderperson — plus the hall address, phone,
website and e-mail. That is DeKalb/Ogle/LaSalle depth, so Tazewell joins as a
full-governing-body county rather than a mayor-level one.

THE DOMAIN WAS THE WHOLE OBSTACLE, and it is worth writing down because it cost
a research pass. tazewell.com fails TLS at this project's egress gateway with a
VALID certificate — a direct socket handshake succeeds and the proxied one is
rejected — and www.tazewellcountyil.gov does not resolve at all. The county is
at tazewell-il.gov, which this repo already knew: data/app/il-county-clerks.json
carries jcackerman@tazewell-il.gov, built weekly from ISBE. **When a county
cannot be found, read the shipped clerk roster before guessing hostnames.**

WHY POSITIONAL PARSING, NOT LINE PARSING. On many pages the office titles and
the officers' names extract as SEPARATE BLOCKS. Marquette Heights, for one,
comes out as "Mayor / Clerk / Treasurer / Alderperson x6" and then eight names
in a run. A line-based read pairs the wrong people with the wrong offices —
quietly, and with output that looks entirely plausible. So the section is read
from word POSITIONS: pdfplumber, rows banded by y at ROW_BAND_PT, columns split
by x. Same recipe as LaSalle, for the same reason.

The columns are stable across the section (measured against the 2026-05
edition): the office title starts left of X_NAME, the officer's name occupies
X_NAME..X_CONTACT, and the hall address / phone / website / e-mail sit right of
X_CONTACT. A municipality's name is a row of CAPS in the office/name columns
that is FOLLOWED by an office row — the contact column is ignored, because most
headings share their row with the start of the hall address ("MARQUETTE HEIGHTS
Address: City Hall"). Requiring an empty contact column silently dropped that
municipality; requiring only CAPS captured the section title and a page header
as two more. The look-ahead is what separates a place from a heading.

TWO RULES THIS DOCUMENT TRIGGERS ON SIGHT, both already fleet convention:

  * "Vacant" is not a person. Minier publishes a vacant deputy clerk; the seat
    is counted and never named.
  * The yearbook prints 389 phone numbers WITHOUT an area code and states no
    default anywhere, so those ship as None rather than as a dead tel: link.
    Tazewell is entirely area code 309 — but the document does not say so, and
    the DMMC rule exists precisely because a completed guess is worse than an
    empty field. Ten-digit numbers, which the county's own offices use, are kept.

URL DISCOVERY, not a hardcoded path: the yearbook lives under a month-stamped
uploads path (…/wp-content/uploads/2026/05/…) that restamps each edition, so the
link is read off the clerk page and the constant below is only a fallback.

Usage:
    python3 tazewell_municipal_officials_scraper.py --out tazewell_municipal_officials.json
    python3 tazewell_municipal_officials_scraper.py --out out.json --pdf local.pdf
"""

import argparse
import collections
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
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

CLERK_PAGE = "https://tazewell-il.gov/countyclerkrecorder/"
# Fallback only — the live URL is read off CLERK_PAGE (see module docstring).
YEARBOOK_URL = "https://tazewell-il.gov/wp-content/uploads/2026/05/FULL-YEARBOOK-1.pdf"
HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
}
REQUEST_TIMEOUT = 180
YEARBOOK_LINK_RE = re.compile(r'href="([^"]*(?:YEARBOOK|Yearbook|yearbook)[^"]*\.pdf)"')

SECTION_START_RE = re.compile(r"OFFICERS OF CITIES AND VILLAGES", re.I)
# The section ends at whichever of these appears first. "Population-" and the
# college matter because both print CAPS headings that look exactly like a
# municipality name — and did get captured as two, which is how the count floor
# passed (17 >= 14) while the data was wrong in BOTH directions: two invented
# places masking one real one that had been dropped.
SECTION_END_RE = re.compile(
    r"(?i)^\s*(TOWNSHIP OFFICIALS|SCHOOL BOARD MEMBERS|POPULATION\s*[-–]|"
    r"ILLINOIS CENTRAL COLLEGE|PRECINCT COMMITTEE)")

# Column boundaries in PDF points, measured against the 2026-05 edition. The
# office title runs from the left margin to X_NAME, the officer's name from
# X_NAME to X_CONTACT, and the hall's address/phone/website/e-mail beyond it.
X_NAME = 120
X_CONTACT = 275
ROW_BAND_PT = 3.0

OFFICE_RE = re.compile(
    r"(?i)^(Mayor|President|Village President|City Clerk|Clerk|Deputy Clerk|Treasurer|"
    r"City Treasurer|Collector|Trustee|Commissioner|Alderman|Alderperson|Alderwoman|"
    r"Council ?Member|Councilman|Councilwoman|Supervisor|Attorney|Administrator|"
    r"Superintendent|Chief of Police|Engineer)\b")
HEAD_OFFICES = {"mayor", "president", "village president"}
# Offices that are hired rather than elected. Flagged, not dropped — the
# Stephenson convention: say what the source says, mark what the reader needs.
APPOINTED = {"attorney", "administrator", "superintendent", "chief of police",
             "engineer", "deputy clerk"}
NON_PERSON = {"vacant", "vacancy", "open", "none", "n/a", "tbd", "unassigned"}

PHONE_FULL_RE = re.compile(r"\(?(\d{3})\)?[\s.-]*(\d{3})[\s.-](\d{4})")
PHONE_BARE_RE = re.compile(r"^\d{3}-\d{4}$")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w{2,}")
URL_RE = re.compile(r"(?i)\b((?:https?://)?[\w-]+(?:\.[\w-]+)+(?:/[\w./-]*)?)")
ZIP_RE = re.compile(r"\b(\d{5})(?:-\d{4})?\b")

# Floors, not equalities — the fleet convention. Municipalities do not
# disappear, so that one is exact; officials and heads sit just below the
# measured 141/16 so an ordinary vacancy between scrapes does not block a
# refresh, while a layout collapse still does.
MIN_MUNICIPALITIES = 16
MIN_OFFICIALS = 130
MIN_HEADS = 15


def clean(value):
    value = re.sub(r"\s+", " ", (value or "")).strip().strip(",")
    return value or None


def norm_office(raw):
    office = re.sub(r"\s+", " ", (raw or "").strip()).rstrip(".:")
    return office.title() if office.islower() or office.isupper() else office


def discover_pdf_url(warnings):
    try:
        require_robots_once(CLERK_PAGE, HEADERS["User-Agent"], headers=HEADERS,
                            label="il-tazewell-municipal-officials-scraper")
        resp = requests.get(CLERK_PAGE, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        warnings.append("could not read %s (%s) — falling back to the last known "
                        "yearbook URL, whose uploads path is month-stamped and goes "
                        "stale when the clerk republishes" % (CLERK_PAGE, exc))
        return YEARBOOK_URL
    links = YEARBOOK_LINK_RE.findall(resp.text)
    if not links:
        warnings.append("no *yearbook*.pdf link on %s — falling back to the last "
                        "known yearbook URL" % CLERK_PAGE)
        return YEARBOOK_URL
    # Newest first: the uploads path is month-stamped, so the highest sorts to
    # the current edition even when older ones stay linked.
    return sorted(urllib.parse.urljoin(CLERK_PAGE, h) for h in links)[-1]


def fetch_pdf(url):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-tazewell-municipal-officials-scraper")
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    if not resp.content.startswith(b"%PDF"):
        raise RuntimeError("%s did not return a PDF (got %d bytes of %s)"
                           % (url, len(resp.content), resp.headers.get("Content-Type")))
    return resp.content


def section_rows(pdf_bytes):
    """Every row of the municipal section, as (office_text, name_text, contact_text)."""
    if pdfplumber is None:
        raise RuntimeError("pdfplumber is required "
                           "(pip install -c scripts/requirements.txt pdfplumber)")
    out = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        started = False
        for page in pdf.pages:
            text = page.extract_text() or ""
            if not started:
                if not SECTION_START_RE.search(text):
                    continue
                started = True
            elif any(SECTION_END_RE.match(l) for l in text.split("\n")):
                break
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            bands, last = [], None
            for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
                if last is not None and w["top"] - last <= ROW_BAND_PT:
                    bands[-1].append(w)
                else:
                    bands.append([w])
                last = w["top"]
            for band in bands:
                cols = {"office": [], "name": [], "contact": []}
                for w in sorted(band, key=lambda w: w["x0"]):
                    key = ("office" if w["x0"] < X_NAME else
                           "name" if w["x0"] < X_CONTACT else "contact")
                    cols[key].append(w["text"])
                out.append((" ".join(cols["office"]).strip(),
                            " ".join(cols["name"]).strip(),
                            " ".join(cols["contact"]).strip()))
    if not started:
        raise RuntimeError("could not find the 'OFFICERS OF CITIES AND VILLAGES' "
                           "heading — the yearbook's layout changed")
    return out


def is_municipality_heading(office, name, contact):
    """A place name is CAPS and sits in the left/name columns.

    The contact column is IGNORED, not required empty: most headings share their
    row with the start of the hall address ("MARQUETTE HEIGHTS  Address: City
    Hall"). Requiring an empty contact column silently dropped that municipality
    and every other one laid out the same way.
    """
    text = ("%s %s" % (office, name)).strip()
    if not text:
        return None
    if OFFICE_RE.match(text):
        return None
    if not re.fullmatch(r"[A-Z][A-Z .'&-]{2,40}", text):
        return None
    upper = text.upper()
    if upper in ("ADDRESS", "PHONE", "FAX", "EMAIL", "WEBSITE"):
        return None
    # The section's own title is CAPS in the same columns and IS followed by
    # offices, so neither the shape test nor the look-ahead rejects it.
    if SECTION_START_RE.search(upper) or "CITIES AND VILLAGES" in upper:
        return None
    return re.sub(r"\s+", " ", text.title()).replace(" Of ", " of ")


def _office_follows(rows, idx, window=6):
    for office_txt, name_txt, _ in rows[idx + 1: idx + 1 + window]:
        if OFFICE_RE.match(office_txt) and name_txt:
            return True
    return False


def parse(pdf_bytes, source_url, warnings):
    rows = section_rows(pdf_bytes)
    municipalities, officials = [], []
    current = None
    contact_lines = collections.defaultdict(list)

    for office_txt, name_txt, contact_txt in rows:
        heading = is_municipality_heading(office_txt, name_txt, contact_txt)
        # A heading is only believed if an OFFICE follows it within a few rows.
        # Section titles and table headers are CAPS too; officers are what makes
        # a municipality, so that is what the look-ahead requires.
        if heading and not _office_follows(rows, rows.index((office_txt, name_txt, contact_txt))):
            heading = None
        if heading:
            current = heading
            municipalities.append(current)
            continue
        if current is None:
            continue
        if contact_txt:
            contact_lines[current].append(contact_txt)
        office_m = OFFICE_RE.match(office_txt)
        if not office_m or not name_txt:
            continue
        office = norm_office(office_m.group(1))
        person = clean(name_txt)
        if not person:
            continue
        if person.lower() in NON_PERSON:
            # Counted by its absence, never named — the Livingston posture.
            warnings.append("%s: %s seat published as '%s' — not shipped as a person"
                            % (current, office, person))
            continue
        officials.append({
            "jurisdiction": current,
            "office": office,
            "district": None,
            "name": person,
            "appointed": office.lower() in APPOINTED,
        })

    # Contact is the MUNICIPALITY's, gathered per place rather than per person.
    by_place = {}
    for place, lines in contact_lines.items():
        blob = " ".join(lines)
        email = EMAIL_RE.search(blob)
        phone_full = PHONE_FULL_RE.search(blob)
        phone = None
        if phone_full:
            phone = "%s-%s-%s" % phone_full.groups()
        else:
            bare = [t for t in blob.split() if PHONE_BARE_RE.match(t)]
            if bare:
                # No area code and the document states no default: the DMMC rule.
                warnings.append("%s: phone %s printed with no area code — shipping "
                                "no phone rather than guessing one" % (place, bare[0]))
        site = None
        for cand in URL_RE.findall(blob):
            if "@" in cand or cand.lower().endswith((".il", ".rd", ".st")):
                continue
            if re.search(r"(?i)\.(com|org|net|gov|us)$|\.(com|org|net|gov|us)/", cand):
                site = cand if cand.startswith("http") else "https://" + cand
                break
        zipc = ZIP_RE.search(blob)
        by_place[place] = {
            "office_phone": phone,
            "office_email": clean(email.group(0)) if email else None,
            "website": site,
            "office_zip": zipc.group(1) if zipc else None,
        }

    for person in officials:
        person.update(by_place.get(person["jurisdiction"], {}))
        person["jurisdiction"] = person["jurisdiction"]
        person["source_url"] = source_url
    return municipalities, officials, warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--pdf", help="parse a local copy instead of fetching")
    args = ap.parse_args()

    warnings = []
    try:
        if args.pdf:
            pdf_bytes, source_url = open(args.pdf, "rb").read(), YEARBOOK_URL
        else:
            source_url = discover_pdf_url(warnings)
            pdf_bytes = fetch_pdf(source_url)
        municipalities, officials, warnings = parse(pdf_bytes, source_url, warnings)
    except Exception as exc:  # noqa: BLE001
        print("FATAL: %s" % exc, file=sys.stderr)
        sys.exit(1)

    for w in sorted(set(warnings)):
        print("  warning: %s" % w, file=sys.stderr)

    heads = sum(1 for o in officials if o["office"].lower() in HEAD_OFFICES)
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
    for o in officials:
        o["scraped_at"] = scraped_at
    payload = {
        "county": "Tazewell",
        "directory_url": source_url,
        "officials_page": CLERK_PAGE,
        "scraped_at": scraped_at,
        "municipalities": [{"name": n, "source_url": source_url,
                            "scraped_at": scraped_at} for n in municipalities],
        "officials": officials,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("scraped %d municipalities, %d officials (%d heads) -> %s"
          % (len(municipalities), len(officials), heads, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
