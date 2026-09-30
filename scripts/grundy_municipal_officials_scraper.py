#!/usr/bin/env python3
"""
Scrape Grundy County's clerk directory booklet into the payload
build_municipal_officials_roster.py consumes.

SOURCE. The County Clerk's "Grundy County Directory" booklet ("Updated July
2026" on the cover — the 2026-07-31 validation-pass finding) carries a
MUNICIPAL OFFICIALS section listing every one of the county's seventeen
municipalities with its FULL governing body — head of government, clerk,
treasurer, and every commissioner / trustee / ward alderman — plus the hall
address, phone and website, and the year each elected seat's TERM ENDS. That
is Cook/Will/DeKalb depth from one county document, so Grundy joins as a
full-governing-body county rather than a mayor-level one. Morris is the
county's one ward-electing city (eight aldermen across four wards).

FETCH POSTURE: open. Plain `requests` with a browser UA gets both the landing
page and the PDF.

URL DISCOVERY, not a hardcoded path. The booklet lives under a per-edition
filename ("BOOKLET GRUNDY COUNTY DIRECTORY 2026.pdf") and the county DELETES
the prior edition when it republishes — the 2025 file 404s today — so the link
is read off the clerk's Directory of Officials page and the constant below is
only the fallback.

WHY A LINE PARSER. Each municipality is a contact header, a "TERM ENDS"
column caption, then one officer per line, and pypdf's extraction preserves
that exactly — the DeKalb/Ogle shape, not LaSalle's interleaved columns.

THE BOOKLET PRINTS EVERYTHING IN CAPS. Person names and hall addresses are
recased before they ship ("TODD LYONS" -> "Todd Lyons") because every other
county source in the roster is mixed-case and the card renders these strings
verbatim. The recaser is deliberately conservative: Mc-surnames, apostrophes,
hyphens, quoted nicknames and Jr./Sr./II suffixes are handled; two-letter
vowelless tokens ("CJ", "CT") are left as the initials they are.

ROWS THE PARSER DROPS, all logged rather than silent:

  * A seat printed as "VACANT" is not a person (six seats this edition).
  * An office row with an appointed marker and no name at all ("TREASURER
    (APPOINTED)*", Kinsman and Verona) names nobody to ship.
  * A name that appears BOTH as head of government and on the board is kept
    only as the head (the DeKalb rule; none this edition, kept as a guard).

An "(APPT. M/YYYY)" marker on a board seat (Diamond's Dave Warner) ships that
member with appointed=True — the county says the seat was filled by
appointment, and the card must not imply an election that did not happen.

WHAT IS DELIBERATELY NOT COLLECTED: nothing per-person. The address, phone,
e-mail and website are the municipality's, and are carried at that level only
— this document publishes no direct line for any individual officer. The
booklet's township / fire / library / park / school sections are out of scope
here (fire districts are a recorded gap with their own ledger entry).

Usage:
    python3 grundy_municipal_officials_scraper.py --out grundy_municipal_officials.json
    python3 grundy_municipal_officials_scraper.py --out out.json --pdf local.pdf
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

REFERENCE_PAGE = "https://www.grundycountyil.gov/communities/directory_of_officials.php"
# Fallback only — the live URL is read off REFERENCE_PAGE (see module docstring).
BOOKLET_URL = ("https://www.grundycountyil.gov/Documents/Communities/"
               "Directory%20of%20Officials/BOOKLET%20GRUNDY%20COUNTY%20DIRECTORY%202026.pdf")
HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
}
REQUEST_TIMEOUT = 120

# The org chart shares the same folder, so the pattern requires DIRECTORY in
# the filename; the ?t= cache-buster the CMS appends is kept (it still serves
# the PDF) but stripped for display. The CMS renders attributes as
# `href= "..."` — with a space after the equals — so the pattern allows it.
BOOKLET_LINK_RE = re.compile(
    r'href=\s*"([^"]*Directory of Officials[^"]*DIRECTORY[^"]*\.pdf[^"]*)"', re.I)

# Both bounds anchored to a WHOLE LINE: the table of contents carries each
# heading too, trailed by dot leaders and page numbers, and a substring match
# would bound the section to the TOC's few characters.
START_RE = re.compile(r"^MUNICIPAL OFFICIALS$", re.I)
END_RE = re.compile(r"^FIRE DISTRICT OFFICIALS$", re.I)

MUNI_RE = re.compile(r"^(CITY|VILLAGE|TOWN) OF ([A-Z][A-Z .'’-]+?)\s*$")
PHONE_RE = re.compile(r"^\(?(\d{3})\)?[-.\s]*(\d{3})[-.\s]*(\d{4})\s*$")
WEBSITE_RE = re.compile(r"^WEBSITE:\s*(\S+)\s*$", re.I)
EMAIL_RE = re.compile(r"^EMAIL:\s*(\S+@\S+)\s*$", re.I)
CITY_ZIP_RE = re.compile(r"^([A-Z][A-Z .'-]*?),\s*IL\.?\s*(\d{5})(?:-\d{4})?\s*$", re.I)
PO_BOX_RE = re.compile(r",?\s*P\.?\s?O\.?\s?BOX\s+\d+,?\s*$", re.I)

# "MAYOR TODD LYONS 2027" / "CLERK (APPOINTED) ADAM BEATY" /
# "ALDERMAN – WARD 1 JAKE DUVICK 2027" / "COMMISSIONERS ELIZABETH DIXON 2027".
# The rest-of-line group is optional: Mazon prints "TRUSTEES DALTON MISENER"
# with the year alone on the next line.
OFFICE_RE = re.compile(
    r"^(MAYOR|PRESIDENT|CLERK|TREASURER|COMMISSIONERS?|TRUSTEES?|ALDERMEN|ALDERMAN)\b"
    r"\s*(\(APPOINTED\))?\s*\*?"
    r"(?:\s*[–—-]\s*WARD\s+(\d+))?"
    r"\s*(.*)$", re.I)
# Continuation under a plural office: "HERB WYETH 2029", "VACANT 2027",
# "DIANE E. YATUNI 2027", "KELLY LEGNER 2027*" — or a bare name whose year
# follows on the next line.
NAME_YEAR_RE = re.compile(r"^(.*?)\s*(\d{4})(\*?)\s*$")
# The same "(APPT. M/YYYY)" marker, GLUED TO THE NAME instead of standing on
# its own line: "JIM RODGERS (APPT. 5/2025)", "WAYNETTE MCTAGUE(8/2026)"
# (Carbon Hill, 2026-08 edition). Left alone it becomes part of the person's
# name, and the card prints "Jim Rodgers (Appt. 5/2025)" as though that were
# what he is called.
#
# THE DISCRIMINATOR MATTERS MORE THAN THE STRIP. Seventeen municipalities in
# this roster carry a parenthetical inside a name, and all but these are
# NICKNAMES — "Michele (Missy) Crawford", "Edward (Jake) Kindred",
# "Alexis (Allie) Dawson". Those are part of the person's name and must
# survive untouched. So this only matches a trailing parenthetical that is an
# APPOINTMENT MARKER or a bare DATE, never a word.
NAME_ANNOTATION_RE = re.compile(
    r"\s*\(\s*(?:APPT\.?|APPOINTED)?\s*(\d{1,2}/\d{4}|\d{4})?\s*\)\s*$", re.I)


def split_name_annotation(text, jurisdiction, warnings):
    """('JIM RODGERS (APPT. 5/2025)') -> ('JIM RODGERS', True).

    Returns the name with a trailing appointment/date marker removed and
    whether that marker said the seat was filled by appointment. A BARE date
    with no APPT wording is stripped too — it is plainly not part of a name —
    but it does NOT set appointed, because nobody said it did, and it is
    warned about so a dropped fact is never silent.
    """
    m = NAME_ANNOTATION_RE.search(text or "")
    if not m or not m.group(0).strip():
        return text, False
    inner = m.group(0)
    if not re.search(r"APPT|APPOINTED|\d", inner, re.I):
        return text, False           # "(Missy)" and friends: a nickname, keep it
    stripped = text[:m.start()].strip()
    if not stripped:
        return text, False           # the annotation IS the whole cell; leave it
    if re.search(r"APPT|APPOINTED", inner, re.I):
        return stripped, True
    warnings.append("%s: dropped %s from the name '%s' — it is a date, not a "
                    "name, and carries no appointment wording to act on"
                    % (jurisdiction, inner.strip(), text))
    return stripped, False
# Diamond's vacancy fill: a name line, then "(APPT. 5/2025) 2027".
APPT_YEAR_RE = re.compile(r"^\(APPT[^)]*\)\s*(\d{4})\*?\s*$", re.I)
YEAR_ONLY_RE = re.compile(r"^(\d{4})\*?\s*$")
APPOINTED_ONLY_RE = re.compile(r"^\(APPOINTED\)\s*$", re.I)

NON_PERSON_NAMES = {"vacant", "vacancy", "unassigned", "open", "tbd", "none", "n/a"}
HEAD_TITLES = {"mayor", "president"}
PLURAL_OFFICES = {"commissioners": "Commissioner", "commissioner": "Commissioner",
                  "trustees": "Trustee", "trustee": "Trustee",
                  "aldermen": "Alderman", "alderman": "Alderman"}

MIN_MUNICIPALITIES = 15
MIN_OFFICIALS = 110
MIN_HEADS = 15
MIN_WARD_SEATS = 6

# Recasing the booklet's ALL-CAPS strings. Tokens that are initials stay as
# printed; everything else gets one capital. Suffix and particle handling is
# enumerated, not guessed.
SUFFIX_KEEP_UPPER = {"II", "III", "IV"}
SUFFIX_TITLE = {"JR": "Jr", "SR": "Sr"}
KEEP_UPPER = {"IL", "PO", "P.O.", "US"}


def _recase_core(word):
    """One alphabetic run -> cased form. 'MCMILLIN' -> 'McMillin'."""
    if not word:
        return word
    # Dotted initials stay exactly as printed: "E.", "P.O.", "J.D.".
    if re.fullmatch(r"(?:[A-Z]\.)+[A-Z]?\.?", word):
        return word
    bare = word.rstrip(".")
    if bare in SUFFIX_KEEP_UPPER:
        return word
    if bare in SUFFIX_TITLE:
        return SUFFIX_TITLE[bare] + word[len(bare):]
    # Two-letter vowelless tokens are initials ("CJ", "CT"), not words.
    if len(bare) <= 2 and not re.search(r"[AEIOUY]", bare):
        return word
    if bare.startswith("MC") and len(bare) > 2:
        return "Mc" + bare[2:].capitalize() + word[len(bare):]
    return word[:1] + word[1:].lower()


def recase(text):
    """'JAMES E. "MOOSE" MIKEL' -> 'James E. "Moose" Mikel'; caps-safe.

    Applied only to strings the booklet prints in caps; a string that already
    carries lowercase is passed through untouched.
    """
    if not text or not text.isupper():
        return text
    out = []
    for token in text.split(" "):
        # Case each alphabetic run in place, leaving digits, quotes, parens,
        # hyphens and apostrophes exactly where the source put them.
        out.append(re.sub(r"[A-Z]+(?:\.[A-Z]+)*\.?",
                          lambda m: _recase_core(m.group(0)), token))
    return " ".join(out)


# Street-suffix tokens that the initials rule above would otherwise keep
# upper ("ST.", "RD.") or that need their own casing. Applied only to
# addresses — "CT" in a PERSON name is someone's initials, not a court.
STREET_SUFFIXES = {"ST": "St", "RD": "Rd", "DR": "Dr", "LN": "Ln", "CT": "Ct",
                   "PL": "Pl", "SQ": "Sq", "TER": "Ter", "CIR": "Cir",
                   "AVE": "Ave", "BLVD": "Blvd", "HWY": "Hwy", "PKWY": "Pkwy"}


def recase_address(text):
    """recase() plus street-suffix casing: '141 W. MAIN ST.' -> '141 W. Main St.'."""
    if not text or not text.isupper():
        return text
    out = []
    for token in recase(text).split(" "):
        bare = token.rstrip(".,")
        if bare.upper() in STREET_SUFFIXES and bare.upper() == bare:
            token = STREET_SUFFIXES[bare.upper()] + token[len(bare):]
        out.append(token)
    return " ".join(out)


def clean(value):
    value = re.sub(r"\s+", " ", (value or "")).strip().strip(",")
    return value or None


def discover_pdf_url(warnings):
    try:
        require_robots_once(REFERENCE_PAGE, HEADERS["User-Agent"], headers=HEADERS,
                            label="il-grundy-municipal-officials-scraper")
        resp = requests.get(REFERENCE_PAGE, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        warnings.append("could not read %s (%s) — falling back to the last known "
                        "booklet URL" % (REFERENCE_PAGE, exc))
        return BOOKLET_URL
    links = BOOKLET_LINK_RE.findall(resp.text)
    if not links:
        warnings.append("no directory-booklet link on %s — falling back to the "
                        "last known booklet URL" % REFERENCE_PAGE)
        return BOOKLET_URL
    # The CMS page declares <base href="https://www.grundycountyil.gov/"> and
    # writes site-root-relative hrefs ("Documents/…"), so links resolve against
    # the base, not the page path — and requests may land on the CMS origin
    # after redirects, so neither resp.url nor REFERENCE_PAGE is safe alone.
    base_match = re.search(r'<base\s+href=\s*"([^"]+)"', resp.text, re.I)
    base = base_match.group(1) if base_match else resp.url
    # Per-edition filenames sort by year, so the highest is the current one
    # even if the county ever leaves an older edition linked.
    return sorted(urllib.parse.urljoin(base, href.replace(" ", "%20"))
                  for href in links)[-1]


def fetch_pdf(url):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-grundy-municipal-officials-scraper")
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    if not resp.content.startswith(b"%PDF"):
        raise RuntimeError("booklet URL did not return a PDF (got %d bytes of %s)"
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
        raise RuntimeError("could not find the 'MUNICIPAL OFFICIALS' heading — "
                           "the booklet's layout changed")
    end = next((i for i in range(start + 1, len(lines))
                if END_RE.match(lines[i].strip())), None)
    if end is None:
        raise RuntimeError("could not find the 'FIRE DISTRICT OFFICIALS' heading "
                           "that bounds the municipal section")
    return lines[start + 1:end]


def parse_hall(lines):
    """-> (street, city, zip, phone, email, website) from a block's header."""
    street = city = zipcode = phone = email = website = None
    for raw in lines:
        text = clean(raw)
        if not text or re.match(r"^\d+\s*\|\s*Page", text, re.I):
            continue
        if re.match(r"^FAX\b", text, re.I) or re.match(r"^TERM ENDS", text, re.I):
            continue
        m = WEBSITE_RE.match(text)
        if m:
            website = m.group(1).rstrip("/").lower()
            continue
        m = EMAIL_RE.match(text)
        if m:
            email = m.group(1).lower()
            continue
        m = PHONE_RE.match(text)
        if m and not phone:
            phone = "%s-%s-%s" % m.groups()
            continue
        m = CITY_ZIP_RE.match(text)
        if m:
            city, zipcode = clean(m.group(1)), m.group(2)
            continue
        if re.search(r"\d|P\.?\s?O\.?\s?BOX", text, re.I) and not street:
            street = text
    # The hall is a physical place; where the booklet gives both a street and
    # a mailing box, the box is dropped rather than concatenated onto the
    # address a visitor would drive to. Where the box is all there is, it stays.
    if street and not PO_BOX_RE.match(street):
        trimmed = PO_BOX_RE.sub("", street)
        if trimmed.strip():
            street = clean(trimmed)
    return street, city, zipcode, phone, email, website


def parse(lines, warnings):
    blocks, current = [], None
    for line in lines:
        match = MUNI_RE.match(line.strip())
        if match:
            current = {"kind": match.group(1).capitalize(),
                       "name": recase(clean(match.group(2))), "lines": []}
            blocks.append(current)
        elif current is not None:
            current["lines"].append(line)
    if not blocks:
        raise RuntimeError("no 'CITY/VILLAGE OF X' headers in the section")

    municipalities, officials = [], []
    for block in blocks:
        name = block["name"]
        jurisdiction = "%s of %s" % (block["kind"], name)
        municipalities.append(name)

        # Everything before the first office row is the hall header.
        head_lines = []
        for raw in block["lines"]:
            if OFFICE_RE.match(raw.strip()) and not CITY_ZIP_RE.match(raw.strip()):
                break
            head_lines.append(raw)
        street, city, zipcode, phone, email, website = parse_hall(head_lines)

        shared = {
            "jurisdiction": jurisdiction,
            "office_address": recase_address(street) if street else None,
            "office_city": recase_address(city) if city else None,
            "office_state": "IL" if city else None,
            "office_zip": zipcode,
            "office_phone": phone,
            "office_email": email,
            "website": website,
        }

        # Row scan. `pending` is a record still waiting for its TERM ENDS year
        # on a following line; `plural` is the office continuation context.
        rows = []
        pending = None
        plural_office = None
        plural_ward = None

        def flush_pending():
            nonlocal pending
            if pending is not None:
                rows.append(pending)
                pending = None

        for raw in block["lines"][len(head_lines):]:
            text = clean(raw)
            if not text or re.match(r"^\d+\s*\|\s*Page", text, re.I):
                continue
            if re.match(r"^TERM ENDS$", text, re.I):
                continue
            if APPOINTED_ONLY_RE.match(text):
                target = pending or (rows[-1] if rows else None)
                if target is not None:
                    target["appointed"] = True
                flush_pending()
                continue
            m = APPT_YEAR_RE.match(text)
            if m and pending is not None:
                pending["year"] = m.group(1)
                pending["appointed"] = True
                flush_pending()
                continue
            m = YEAR_ONLY_RE.match(text)
            if m and pending is not None:
                pending["year"] = m.group(1)
                flush_pending()
                continue
            m = OFFICE_RE.match(text)
            if m:
                flush_pending()
                office_raw = m.group(1).lower()
                appointed = bool(m.group(2))
                ward = m.group(3)
                rest = clean(m.group(4))
                if office_raw in PLURAL_OFFICES:
                    plural_office = PLURAL_OFFICES[office_raw]
                    plural_ward = ("Ward %s" % ward) if ward else None
                    office = plural_office
                    district = plural_ward
                else:
                    plural_office = None
                    plural_ward = None
                    office = office_raw.capitalize()
                    district = None
                if not rest:
                    if plural_office is None:
                        # "TREASURER (APPOINTED)*" with no name at all
                        # (Kinsman, Verona): nobody to ship.
                        warnings.append("%s: %s row names nobody — skipped"
                                        % (jurisdiction, office))
                    continue
                nm = NAME_YEAR_RE.match(rest)
                person, year, starred = ((nm.group(1), nm.group(2), nm.group(3))
                                         if nm else (rest, None, ""))
                person, glued_appt = split_name_annotation(person, jurisdiction, warnings)
                pending = {"office": office, "district": district,
                           "name": clean(person), "year": year,
                           "appointed": appointed or glued_appt,
                           "starred": bool(starred)}
                if year is not None:
                    flush_pending()
                continue
            # Continuation line under a plural office (or a stray name line).
            if plural_office is None:
                warnings.append("unparsed line in %s: '%s'" % (jurisdiction, text))
                continue
            nm = NAME_YEAR_RE.match(text)
            person, year, starred = ((nm.group(1), nm.group(2), nm.group(3))
                                     if nm else (text, None, ""))
            person, glued_appt = split_name_annotation(person, jurisdiction, warnings)
            pending = {"office": plural_office, "district": plural_ward,
                       "name": clean(person), "year": year,
                       "appointed": glued_appt, "starred": bool(starred)}
            if year is not None:
                flush_pending()
        flush_pending()

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
            if row.get("starred"):
                warnings.append("%s: %s's term year carries the booklet's asterisk "
                                "footnote — shipped without it" % (jurisdiction, person))
            record = dict(shared, office=row["office"], district=row["district"],
                          name=recase(person))
            if row.get("appointed"):
                record["appointed"] = True
            if row.get("year") and not row.get("appointed"):
                record["term_expires"] = row["year"]
            elif row.get("year"):
                # Appointed to a seat with a printed TERM ENDS (Diamond's
                # vacancy fill): the year is still when the seat is up.
                record["term_expires"] = row["year"]
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
            source_url, pdf_bytes = BOOKLET_URL, open(args.pdf, "rb").read()
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
    # Morris's eight ward-aldermen rows are the part of this payload the
    # municipal-ward layer joins to; a shape change that broke only the
    # "ALDERMAN – WARD N" rows would pass every count above.
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
        "county": "Grundy",
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
