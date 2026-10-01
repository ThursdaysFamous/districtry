#!/usr/bin/env python3
"""
Scrape the Cass County Directory into the payload
build_municipal_officials_roster.py consumes.

SOURCE. The County Clerk publishes a 43-page "Cass County Directory", linked
from the front page of co.cass.il.us. Clerk Shelly Wessel pointed at it on
2026-08-03 when asked whether the county published a municipal list; nothing
about its link text says "officials", which is why a search had not found it.
The edition read here is stamped May 2026 and its terms run to April 2027 and
2029, so it postdates the April 2025 consolidated election — the test every
municipal source has to pass before it can be shipped.

DEPTH. Two facing sections carry the whole of local government: an officers
table (head of government, clerk, treasurer, with the municipal hall address in
each section heading) and a "CITY & VILLAGE BOARDS / ALDERMEN/TRUSTEES" table
(every trustee and alderperson, with WARD numbers for Beardstown and Virginia).
That is full-governing-body depth for all five of the county's municipalities.

WHY POSITIONAL PARSING. The office titles WRAP: "President of / Village Board"
and "Village Treasurer / (Appointed)" each occupy two printed lines, and a
member's name sits on the first of them while their phone sits on the second.
Read as lines, the second line of one record pairs with the first line of the
next. The words carry x/y, so the columns are recoverable exactly as printed —
the LaSalle recipe, for the same reason LaSalle needed it.

THE ADDRESS COLUMN IS DROPPED WHOLESALE, and that is the point of splitting by
x rather than by text. Both tables print each officer's HOME address in a column
of its own (President Privia at 204 S State, Trustee Bateman at 305 E Main).
Discarding a column is a stronger guarantee than filtering strings afterwards:
nothing from that x-range is read, so no residence can reach the payload by
being formatted unexpectedly. The MUNICIPAL address still ships — it is printed
in the section heading ("VILLAGE OF ARENZVILLE – 201 E. MAIN…"), which is the
village office, not a house.

Usage:
    python3 cass_municipal_officials_scraper.py --out cass_municipal_officials.json
    python3 cass_municipal_officials_scraper.py --out out.json --pdf local.pdf
"""

import argparse
import collections
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

COUNTY_SITE = "https://co.cass.il.us/"
# Fallback only: the link is a per-upload UUID and restamps with each edition,
# so discovery from the front page is the real path.
DIRECTORY_FALLBACK = ("https://co.cass.il.us/download_file/view/"
                      "6b66614e-1d1e-4422-a9b6-6f528b7fa689/1")
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
}
REQUEST_TIMEOUT = 120

# Column boundaries in PDF points, measured against the May 2026 edition.
# OFFICERS page: office title 90-195, name/phone 195-300, HOME ADDRESS 300-445
# (never read), term 445+.
OFF_X_TITLE = (60, 195)
OFF_X_NAME = (195, 300)
OFF_X_TERM = (445, 620)
# BOARDS page: name (+ ward/term note) 80-196, phone 196-268, HOME ADDRESS
# 268-480 (never read), term 480+.
BRD_X_NAME = (60, 196)
BRD_X_PHONE = (196, 268)
BRD_X_TERM = (480, 620)
ROW_BAND_PT = 4.0

HEAD_SECTION_RE = re.compile(r"(?i)^(VILLAGE|CITY|TOWN)\s+OF\s+([A-Z][A-Z .'-]*?)\s*$")
# The same heading as it appears on the page: name, en/em dash, hall address.
HALL_HEAD_RE = re.compile(r"(?im)^(?:VILLAGE|CITY|TOWN)\s+OF\s+[A-Z][A-Z .'-]*\s*[\u2013\u2014]\s*\S")
BOARDS_TITLE_RE = re.compile(r"(?i)CITY\s*&\s*VILLAGE\s+BOARDS")
PLACE_HEAD_RE = re.compile(r"^([A-Z][A-Z .'-]{2,})$")
PHONE_RE = re.compile(r"\(?(\d{3})\)?[\s.\-]?(\d{3})[\s.\-]?(\d{4})")
TERM_RE = re.compile(r"(?i)\b(20\d{2})\b")
WARD_RE = re.compile(r"\(W-?\s?(\d+)\)")
TERM_NOTE_RE = re.compile(r"\(\s*\d+\s*yr\s*\)|\(UEX\)|\(Appointed\)", re.I)
NON_PERSON = ("vacant", "vacancy", "(vacancy)", "n/a", "")

# Office titles the officers table prints, normalised to the builder's words.
TITLE_MAP = {
    "president of village board": "President",
    "president of the village board": "President",
    "mayor": "Mayor",
    "village clerk": "Clerk",
    "city clerk": "Clerk",
    "village treasurer": "Treasurer",
    "city treasurer": "Treasurer",
}
APPOINTED_MARK = "(appointed)"

# Cass has exactly five incorporated places and the directory covers all five,
# so the municipality bound is an equality in spirit; it is written as a floor
# only so a genuine disincorporation does not need a code change to ship.
MIN_MUNICIPALITIES = 5
MIN_HEADS = 5
MIN_OFFICIALS = 40
# Beardstown elects 8 by ward and Virginia 6; a parse that lost the "(W1)"
# markers would still produce a plausible at-large roster, so they are floored.
MIN_WARD_SEATS = 12


def discover_pdf_url(session, warnings):
    try:
        require_robots_once(COUNTY_SITE, HEADERS["User-Agent"], headers=HEADERS,
                            label="il-cass-municipal-officials-scraper")
        resp = session.get(COUNTY_SITE, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001 — discovery is best-effort
        warnings.append("could not read %s (%s) — using the recorded directory URL"
                        % (COUNTY_SITE, type(exc).__name__))
        return DIRECTORY_FALLBACK
    for href, text in re.findall(r'(?is)<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', resp.text):
        label = re.sub(r"(?s)<[^>]+>", " ", text)
        if re.search(r"(?i)\bdirectory\b", label):
            if href.startswith("/"):
                href = COUNTY_SITE.rstrip("/") + href
            return href
    warnings.append("the county front page no longer links anything named "
                    "'Directory' — using the recorded URL, which may be stale")
    return DIRECTORY_FALLBACK


def fetch_pdf(session, url):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-cass-municipal-officials-scraper")
    resp = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    if not resp.content.startswith(b"%PDF"):
        raise RuntimeError("%s did not return a PDF (got %d bytes of %s)"
                           % (url, len(resp.content), resp.headers.get("Content-Type")))
    return resp.content


def banded(words):
    """Words clustered into printed rows by proximity in y."""
    bands = []
    for word in sorted(words, key=lambda w: w["top"]):
        if bands and word["top"] - bands[-1][0] <= ROW_BAND_PT:
            bands[-1][1].append(word)
        else:
            bands.append((word["top"], [word]))
    return [sorted(ws, key=lambda w: w["x0"]) for _top, ws in bands]


def cell(row, span):
    return " ".join(w["text"] for w in row if span[0] <= w["x0"] < span[1]).strip()


def page_rows(page):
    return banded(page.extract_words(use_text_flow=False, keep_blank_chars=False))


def parse_officers(pages, warnings):
    """The officers table: head of government, clerk, treasurer, per municipality."""
    officials, halls = [], {}
    current = None
    pending = None  # a record whose title/phone continues on the next band

    def flush():
        if pending and pending.get("name"):
            officials.append(pending)

    for page in pages:
        for row in page_rows(page):
            line = " ".join(w["text"] for w in row).strip()
            title = cell(row, OFF_X_TITLE)
            name = cell(row, OFF_X_NAME)
            term = cell(row, OFF_X_TERM)

            head = HEAD_SECTION_RE.match(re.split(r"[\u2013\u2014]", line)[0].strip())
            if head and re.search(r"[\u2013\u2014]", line):
                flush()
                pending = None
                place = "%s of %s" % (head.group(1).title(), head.group(2).title())
                current = place
                # Everything after the dash is the MUNICIPAL office address —
                # the one address in this document that is not a residence.
                hall = re.split(r"[–—]", line, 1)[1].strip() if re.search(r"[–—]", line) else ""
                hall = re.sub(r"(?i)\s*Term\s+Expires\s*$", "", hall).strip()
                halls[place] = hall or None
                continue
            if current is None:
                continue

            # A band that carries a NAME starts a record; a band that carries
            # only a title fragment or a phone continues the previous one.
            if name and not PHONE_RE.match(name):
                flush()
                pending = {"jurisdiction": current, "title_parts": [title] if title else [],
                           "name": name, "term": term, "phone": None,
                           "appointed": False}
            elif pending is not None:
                if title:
                    pending["title_parts"].append(title)
                phone = PHONE_RE.search(name)
                if phone:
                    pending["phone"] = "%s-%s-%s" % phone.groups()
                if not pending.get("term") and term:
                    pending["term"] = term
        flush()
        pending = None

    records = []
    for rec in officials:
        raw_title = " ".join(rec["title_parts"]).strip()
        appointed = APPOINTED_MARK in raw_title.lower()
        key = re.sub(r"\s+", " ", TERM_NOTE_RE.sub(" ", raw_title)).strip().lower()
        office = TITLE_MAP.get(key)
        if office is None:
            warnings.append("%s: unrecognised office title %r — shipped as printed"
                            % (rec["jurisdiction"], raw_title))
            office = raw_title or "Officer"
        person = re.sub(r"\s+", " ", TERM_NOTE_RE.sub(" ", rec["name"])).strip()
        if not person or person.lower() in NON_PERSON:
            warnings.append("%s: a %s seat is published with no name — counted, "
                            "never named" % (rec["jurisdiction"], office))
            continue
        year = TERM_RE.search(rec.get("term") or "")
        records.append({
            "jurisdiction": rec["jurisdiction"],
            "office": office,
            "name": person,
            "district": None,
            "appointed": appointed,
            "term_expires": year.group(1) if year else None,
            "person_phone": rec.get("phone"),
        })
    return records, halls


def parse_boards(pages, place_lookup, warnings):
    """The ALDERMEN/TRUSTEES table: every seat, with ward where the county gives one."""
    records = []
    current = None
    for page in pages:
        for row in page_rows(page):
            name_cell = cell(row, BRD_X_NAME)
            phone_cell = cell(row, BRD_X_PHONE)
            term_cell = cell(row, BRD_X_TERM)
            if not name_cell:
                continue
            bare = re.sub(r"(?i)\s*Term\s+Expires\s*$", "", name_cell).strip()
            if PLACE_HEAD_RE.match(bare) and not phone_cell:
                resolved = place_lookup.get(bare.upper())
                if resolved is None:
                    warnings.append("the boards table names %r, which the officers "
                                    "table does not — skipped rather than guessed"
                                    % bare)
                    current = None
                else:
                    current = resolved
                continue
            if current is None:
                continue
            ward = WARD_RE.search(name_cell)
            person = WARD_RE.sub(" ", name_cell)
            person = re.sub(r"\s+", " ", TERM_NOTE_RE.sub(" ", person)).strip(" ,.")
            if not person or person.lower() in NON_PERSON:
                warnings.append("%s: a board seat is published as %r — counted, "
                                "never named" % (current, name_cell))
                continue
            phone = PHONE_RE.search(phone_cell)
            year = TERM_RE.search(term_cell)
            records.append({
                "jurisdiction": current,
                "office": "Alderperson" if current.lower().startswith("city") else "Trustee",
                "name": person,
                "district": ("Ward %s" % ward.group(1)) if ward else None,
                "appointed": False,
                "term_expires": year.group(1) if year else None,
                "person_phone": "%s-%s-%s" % phone.groups() if phone else None,
            })
    return records


def recase(text):
    """Title-case the directory's ALL-CAPS addresses, keeping ordinals lowercase.

    str.title() alone turns "105 W. 3RD ST." into "105 W. 3Rd St." — the ordinal
    suffix reads as a typo on a card.
    """
    out = (text or "").strip().title()
    return re.sub(r"\b(\d+)(St|Nd|Rd|Th)\b", lambda m: m.group(1) + m.group(2).lower(), out)


def split_hall(hall):
    """'201 E. MAIN, ARENZVILLE, IL 62611' -> (street, city, state, zip)."""
    if not hall:
        return None, None, None, None
    match = re.match(r"^(.*?),\s*([A-Za-z .'-]+),\s*(IL)\s*(\d{5})?\s*$", hall.strip())
    if not match:
        return recase(hall) or None, None, None, None
    street, city, state, zipcode = match.groups()
    return recase(street), recase(city), state, zipcode


def parse(pdf_bytes, source_url, warnings):
    if pdfplumber is None:
        raise RuntimeError("pdfplumber is required "
                           "(pip install -c scripts/requirements.txt pdfplumber)")
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        texts = [(p, p.extract_text() or "") for p in pdf.pages]
        # A municipality heading is "VILLAGE OF X – <hall address>". Requiring
        # the DASH AND ADDRESS, and at least two of them on a page, is what
        # separates the officers table from the rest of the directory: several
        # later pages name a municipality in passing (the Economic Development
        # Commission roster names four), and matching those attributed a
        # drainage-district board to the City of Virginia.
        officer_pages = [p for p, t in texts if len(HALL_HEAD_RE.findall(t)) >= 2]
        # "Term Expires" is what tells the real boards table from the table of
        # CONTENTS, which also contains the words "City & Village Boards".
        board_pages = [p for p, t in texts
                       if BOARDS_TITLE_RE.search(t) and re.search(r"(?i)Term\s+Expires", t)]
        if not officer_pages:
            raise RuntimeError("no municipal officers table found — the directory's "
                               "layout has changed")
        if not board_pages:
            raise RuntimeError("no 'CITY & VILLAGE BOARDS' table found — the "
                               "directory's layout has changed")
        officers, halls = parse_officers(officer_pages, warnings)
        lookup = {}
        for place in halls:
            lookup[place.split(" of ", 1)[1].upper()] = place
        boards = parse_boards(board_pages, lookup, warnings)

    officials = officers + boards
    contact = {}
    for place, hall in halls.items():
        street, city, state, zipcode = split_hall(hall)
        contact[place] = {"office_address": street, "office_city": city,
                          "office_state": state or "IL", "office_zip": zipcode}
    for person in officials:
        person.update(contact.get(person["jurisdiction"], {}))
        person["source_url"] = source_url
    return sorted(halls), officials


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
    ward_seats = sum(1 for o in officials if o.get("district"))
    problems = []
    if len(places) < MIN_MUNICIPALITIES:
        problems.append("%d municipalities < floor %d" % (len(places), MIN_MUNICIPALITIES))
    if len(officials) < MIN_OFFICIALS:
        problems.append("%d officials < floor %d" % (len(officials), MIN_OFFICIALS))
    if heads < MIN_HEADS:
        problems.append("%d heads < floor %d" % (heads, MIN_HEADS))
    if ward_seats < MIN_WARD_SEATS:
        problems.append("%d ward seats < floor %d — the (Wn) markers may have "
                        "stopped parsing" % (ward_seats, MIN_WARD_SEATS))
    if problems:
        for problem in problems:
            print("  FAIL: %s" % problem, file=sys.stderr)
        print("FATAL: refusing to write a payload that lost coverage", file=sys.stderr)
        sys.exit(1)

    payload = {
        "county": "Cass",
        "directory_url": source_url,
        "officials_page": COUNTY_SITE,
        "scraped_at": datetime.datetime.now(datetime.timezone.utc)
                              .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "municipalities": places,
        "officials": officials,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    per = collections.Counter(o["jurisdiction"] for o in officials)
    print("scraped %d municipalities, %d officials (%d heads, %d ward seats) — %s -> %s"
          % (len(places), len(officials), heads, ward_seats,
             ", ".join("%s=%d" % (p.split(" of ", 1)[-1], per[p]) for p in places),
             args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
