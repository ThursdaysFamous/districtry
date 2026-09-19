#!/usr/bin/env python3
"""
Scrape Peoria County's Officials & Services Directory into the payload
build_municipal_officials_roster.py consumes.

SOURCE, AND THE GAP IT CLOSES. `peoria-municipal-officials` was recorded on
2026-08-02 as NO SOURCE AT ANY RUNG after a full probe: the county's election
authority is a commission that publishes candidates rather than seated
officers, the county phone directory is county staff, Tri-County RPC publishes
no member roster at all, and the county GIS's municipality layer is CORP_NAME
and nothing else. That was a correct finding about the places looked at and a
wrong conclusion about the county, and one e-mail settled it: the Clerk's
office answered on 2026-08-03 with "Our Service Directory contains the
information you have referenced".

It does, and it is the richest municipal source in the fleet. The 2026-2027
"Peoria County Officials & Services Directory" gives each of the county's
fifteen municipalities a block carrying the hall address, phone, fax, WEBSITE
and e-mail, then the head of government, clerk, treasurer, and every seat on
the governing body — with WARD numbers for Chillicothe and DISTRICT numbers
for the City of Peoria, whose council is five district seats plus five
at-large.

Peoria is also the largest county on the Municipality card outside the collar:
~180,000 people, and the City of Peoria alone is ~113,000.

FORMAT. Every field is a dot-leader row: "Mayor: ....... Rita Ali". The leader
collapses to nothing when the name is long enough to need the space
("District 3 Council Member: Timothy D. Riggenbach"), so the parse matches a
known LABEL and takes the rest of the line, rather than splitting on the dots.
One field prints with no colon at all ("Treasurer ....... Andrea Bredeman"),
which is why the colon is optional in every pattern.

DEPARTMENT HEADS ARE DELIBERATELY SKIPPED. The directory lists a Fire Chief and
a Police Chief for six municipalities. Neither is elected and neither belongs
on a card about who represents you — the same call Logan's yearbook got. The
appointed MANAGERS (city manager, village administrator) are kept, because they
run the municipality's business and the card flags them appointed, but a chief
of police is a department, not a government.

Usage:
    python3 peoria_municipal_officials_scraper.py --out peoria_municipal_officials.json
    python3 peoria_municipal_officials_scraper.py --out out.json --pdf local.pdf
"""

import argparse
import collections
import datetime
import io
import json
import re
import sys

import requests
from scraper_common import UA_CHROME_WIN_126  # noqa: E402  (shared machinery — do not fork)

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

SERVICE_DIRECTORY_PAGE = "https://www.peoriacounty.gov/250/Service-Directory"
COUNTY_SITE = "https://www.peoriacounty.gov"
DIRECTORY_FALLBACK = "https://www.peoriacounty.gov/DocumentCenter/View/295"
HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
}
REQUEST_TIMEOUT = 180

SECTION_RE = re.compile(r"(?m)^MUNICIPAL OFFICIALS")
# The section ends where the township one begins.
SECTION_END_RE = re.compile(r"(?m)^(TOWNSHIP|SCHOOL|FIRE PROTECTION|LIBRARY)\b")
SUBHEAD_RE = re.compile(r"(?i)^(CITIES|VILLAGES|TOWNS|MUNICIPAL OFFICIALS.*)$")
MEETING_RE = re.compile(r"(?i)^(regular|special)\b.*meeting")
DOTS_RE = re.compile(r"[.…]{2,}")
ADDRESS_RE = re.compile(r"^\d|\bP\.?O\.?\s*Box\b", re.I)
PHONE_RE = re.compile(r"\(?(\d{3})\)?[\s.\-]?(\d{3})[\s.\-]?(\d{4})")
ZIP_RE = re.compile(r"\b(6\d{4})\b")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PLACE_RE = re.compile(r"^[A-Z][A-Za-z'.\-]*(?:\s+[A-Z][A-Za-z'.\-]*){0,2}$")
NON_PERSON = ("vacant", "vacancy", "(vacancy)", "n/a", "tbd", "")

# Ordered: the first pattern that matches a line wins, so the more specific
# seat labels must precede the bare ones.
# THE OFFICE WORD MUST BE A COMPLETE TOKEN. Each pattern separates the label
# from the name with `\s*:?\s*` — an OPTIONAL colon and whitespace that may match
# ZERO characters — so the label matched as a PREFIX of a longer word. Measured
# across this 75-page directory (3,139 lines) that fired on exactly one line,
# "Clerk’s Email: ... clerk@bartonville.org", which shipped as a Village of
# Bartonville Clerk NAMED "’s Email: ... clerk@bartonville.org" from
# 2026-09-01 until 2026-09-19. The guard is a negative lookahead for a word
# character or an apostrophe; requiring a colon instead was measured and
# REJECTED, because 16 real rows use dot leaders and no colon
# ("Treasurer ....... Andrea Bredeman").
FIELD_PATTERNS = [
    (re.compile(r"(?i)^Alder(?:man|woman|person)\s*[-–]\s*Ward\s*(\d+)(?![\\w’'‘])\s*:?\s*(.*)$"),
     "board", "Alderperson", "Ward %s"),
    (re.compile(r"(?i)^District\s*(\d+)\s*Council\s*Member(?![\\w’'‘])\s*:?\s*(.*)$"),
     "board", "Council Member", "District %s"),
    (re.compile(r"(?i)^At[-\s]*Large\s*Council\s*Member(?![\\w’'‘])\s*:?\s*()(.*)$"),
     "board", "Council Member", "At-Large"),
    (re.compile(r"(?i)^Trustee(?![\\w’'‘])\s*:?\s*()(.*)$"), "board", "Trustee", None),
    (re.compile(r"(?i)^Mayor\s*/\s*President(?![\\w’'‘])\s*:?\s*()(.*)$"), "head", "Mayor", None),
    (re.compile(r"(?i)^Mayor(?![\\w’'‘])\s*:?\s*()(.*)$"), "head", "Mayor", None),
    (re.compile(r"(?i)^President(?![\\w’'‘])\s*:?\s*()(.*)$"), "head", "President", None),
    (re.compile(r"(?i)^Clerk\s*/\s*Treasurer(?![\\w’'‘])\s*:?\s*()(.*)$"), "officer", "Clerk/Treasurer", None),
    (re.compile(r"(?i)^Clerk(?![\\w’'‘])\s*:?\s*()(.*)$"), "officer", "Clerk", None),
    (re.compile(r"(?i)^Treasurer(?![\\w’'‘])\s*:?\s*()(.*)$"), "officer", "Treasurer", None),
    (re.compile(r"(?i)^Collector(?![\\w’'‘])\s*:?\s*()(.*)$"), "officer", "Collector", None),
    (re.compile(r"(?i)^City\s*Manager(?![\\w’'‘])\s*:?\s*()(.*)$"), "appointed", "City Manager", None),
    (re.compile(r"(?i)^City\s*Administrator(?![\\w’'‘])\s*:?\s*()(.*)$"), "appointed", "City Administrator", None),
    (re.compile(r"(?i)^Village\s*Administrator(?![\\w’'‘])\s*:?\s*()(.*)$"), "appointed", "Village Administrator", None),
    # Department heads: matched so they are consumed, then dropped by rule.
    (re.compile(r"(?i)^(?:Fire|Police)\s*Chief(?![\\w’'‘])\s*:?\s*()(.*)$"), "skip", None, None),
]
CONTACT_PATTERNS = [
    (re.compile(r"(?i)^Phone\s*:?\s*(.*)$"), "phone"),
    (re.compile(r"(?i)^Fax\s*:?\s*(.*)$"), "fax"),
    (re.compile(r"(?i)^Website\s*:?\s*(.*)$"), "website"),
    (re.compile(r"(?i)^E-?mail\s*:?\s*(.*)$"), "email"),
    (re.compile(r"(?i)^Mail(?:ing)?\s*Address\s*:?\s*(.*)$"), "mail"),
]

MIN_MUNICIPALITIES = 13
MIN_HEADS = 13
MIN_OFFICIALS = 110
# Chillicothe elects 8 by ward and the City of Peoria 5 by district; a parse
# that lost those labels would still produce a plausible at-large roster.
MIN_DISTRICT_SEATS = 11


def discover_pdf_url(session, warnings):
    try:
        resp = session.get(SERVICE_DIRECTORY_PAGE, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001 — discovery is best-effort
        warnings.append("could not read %s (%s) — using the recorded directory URL"
                        % (SERVICE_DIRECTORY_PAGE, type(exc).__name__))
        return DIRECTORY_FALLBACK
    match = re.search(r'href="(/DocumentCenter/View/\d+[^"]*)"[^>]*>\s*'
                      r'[^<]*at\s*Your\s*Service', resp.text, re.I)
    if not match:
        warnings.append("the Service Directory page no longer links an 'at Your "
                        "Service' document — using the recorded URL, which may be stale")
        return DIRECTORY_FALLBACK
    return COUNTY_SITE + match.group(1)


def fetch_pdf(session, url):
    resp = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    if not resp.content.startswith(b"%PDF"):
        raise RuntimeError("%s did not return a PDF (got %d bytes of %s)"
                           % (url, len(resp.content), resp.headers.get("Content-Type")))
    return resp.content


def section_lines(pdf_bytes):
    """Every line of the MUNICIPAL OFFICIALS section, in document order."""
    if pdfplumber is None:
        raise RuntimeError("pdfplumber is required "
                           "(pip install -c scripts/requirements.txt pdfplumber)")
    out, started = [], False
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if not started:
                if not SECTION_RE.search(text):
                    continue
                started = True
            elif not SECTION_RE.search(text):
                # The section runs over consecutive pages, each repeating the
                # header; the first page without it is past the end.
                break
            for line in text.splitlines():
                line = DOTS_RE.sub(" ", line)
                line = re.sub(r"\s+", " ", line).strip()
                if line:
                    out.append(line)
    if not started:
        raise RuntimeError("the directory has no MUNICIPAL OFFICIALS section — "
                           "its layout has changed")
    return out


def clean_value(text):
    return re.sub(r"\s+", " ", (text or "").replace("…", " ")).strip(" .:")


def parse(pdf_bytes, source_url, warnings):
    lines = section_lines(pdf_bytes)
    places, officials = [], []
    contact = {}
    current = None

    for line in lines:
        if SUBHEAD_RE.match(line) or MEETING_RE.match(line):
            continue

        matched = False
        for pattern, kind, office, district_fmt in FIELD_PATTERNS:
            match = pattern.match(line)
            if not match:
                continue
            matched = True
            if current is None:
                break
            value = clean_value(match.group(2))
            if kind == "skip":
                break
            if not value or value.lower() in NON_PERSON:
                if value.lower() in NON_PERSON and value:
                    warnings.append("%s: a %s seat is published as %r — counted, "
                                    "never named" % (current, office, value))
                break
            district = None
            if district_fmt:
                district = district_fmt % match.group(1) if "%s" in district_fmt else district_fmt
            officials.append({
                "jurisdiction": current,
                "office": office,
                "name": value,
                "district": district,
                "appointed": kind == "appointed",
            })
            break
        if matched:
            continue

        hit = False
        for pattern, key in CONTACT_PATTERNS:
            match = pattern.match(line)
            if not match:
                continue
            hit = True
            if current is not None:
                contact.setdefault(current, {})[key] = clean_value(match.group(1))
            break
        if hit:
            continue

        # An address line follows the place name; anything else that looks like
        # a bare title-case name IS the next place.
        if current and ADDRESS_RE.match(line) and "address" not in contact.get(current, {}):
            contact.setdefault(current, {})["address"] = line
            continue
        if PLACE_RE.match(line) and not ADDRESS_RE.match(line):
            current = line
            if current not in places:
                places.append(current)
            continue

    records = []
    for person in officials:
        info = contact.get(person["jurisdiction"], {})
        address = info.get("address") or ""
        # "908 N Second St., Chillicothe, 61523" -> street / city / zip
        zipcode = ZIP_RE.search(address)
        street = ZIP_RE.sub(" ", address)
        street = re.sub(r"(?i)[\s,]*%s[\s,]*$" % re.escape(person["jurisdiction"]),
                        "", street.strip())
        phone = PHONE_RE.search(info.get("phone") or "")
        website = info.get("website") or None
        if website and not re.match(r"(?i)^https?://", website):
            website = "https://" + website
        email = EMAIL_RE.search(info.get("email") or "")
        records.append({
            "jurisdiction": person["jurisdiction"],
            "office": person["office"],
            "name": person["name"],
            "district": person["district"],
            "appointed": person["appointed"],
            "office_address": re.sub(r"\s+", " ", street).strip(" ,.") or None,
            "office_city": person["jurisdiction"],
            "office_state": "IL",
            "office_zip": zipcode.group(1) if zipcode else None,
            "office_phone": "%s-%s-%s" % phone.groups() if phone else None,
            "office_email": email.group(0) if email else None,
            "website": website,
            "source_url": source_url,
        })
    return places, records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--pdf", help="parse a local copy instead of fetching")
    args = ap.parse_args()

    warnings = []
    session = requests.Session()
    try:
        if args.pdf:
            source_url, pdf_bytes = DIRECTORY_FALLBACK, open(args.pdf, "rb").read()
        else:
            source_url = discover_pdf_url(session, warnings)
            pdf_bytes = fetch_pdf(session, source_url)
        places, officials = parse(pdf_bytes, source_url, warnings)
    except Exception as exc:  # noqa: BLE001
        print("FATAL: %s" % exc, file=sys.stderr)
        sys.exit(1)

    for warning in sorted(set(warnings)):
        print("  warning: %s" % warning, file=sys.stderr)

    heads = sum(1 for o in officials if o["office"] in ("Mayor", "President"))
    seats = sum(1 for o in officials if o.get("district") and o["district"] != "At-Large")
    problems = []
    if len(places) < MIN_MUNICIPALITIES:
        problems.append("%d municipalities < floor %d" % (len(places), MIN_MUNICIPALITIES))
    if len(officials) < MIN_OFFICIALS:
        problems.append("%d officials < floor %d" % (len(officials), MIN_OFFICIALS))
    if heads < MIN_HEADS:
        problems.append("%d heads < floor %d" % (heads, MIN_HEADS))
    if seats < MIN_DISTRICT_SEATS:
        problems.append("%d ward/district seats < floor %d — the seat labels may "
                        "have stopped parsing" % (seats, MIN_DISTRICT_SEATS))
    if problems:
        for problem in problems:
            print("  FAIL: %s" % problem, file=sys.stderr)
        print("FATAL: refusing to write a payload that lost coverage", file=sys.stderr)
        sys.exit(1)

    payload = {
        "county": "Peoria",
        "directory_url": source_url,
        "officials_page": SERVICE_DIRECTORY_PAGE,
        "scraped_at": datetime.datetime.now(datetime.timezone.utc)
                              .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "municipalities": places,
        "officials": officials,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    per = collections.Counter(o["jurisdiction"] for o in officials)
    print("scraped %d municipalities, %d officials (%d heads, %d ward/district "
          "seats) — %s -> %s"
          % (len(places), len(officials), heads, seats,
             ", ".join("%s=%d" % (p, per[p]) for p in places), args.out),
          file=sys.stderr)


if __name__ == "__main__":
    main()
