#!/usr/bin/env python3
"""
Stage 1 of the Carroll County Board roster pipeline: scrape the county's board
directory into raw JSON for build_carroll_county_board_roster.py.

PAGE SHAPE. A Revize "staff_directory" table with six columns — Address, First
Name, Last Name, Profession, Email, Phone — one row per member. The district and
any leadership role are both inside the PROFESSION cell, in one of these shapes:

    District I, Term Exp. 2028
    Chair / District II, Term Exp. 2028
    Vice-Chairman / District III, Term Exp. 2026

THE DISTRICT IS A ROMAN NUMERAL HERE and an Arabic one on the county's map. The
map is what the boundary file is keyed by, so the numeral is converted at this
stage rather than left for the card to reconcile — a card matching "District II"
against a boundary labelled "2" would silently find nothing.

The Address column is a city and ZIP only ("Lanark, IL 61046"), not a street, and
it is a RESIDENCE rather than an office — two members live in Lanark and sit for
different districts. It is deliberately not collected, matching McHenry,
Livingston, Sangamon, Winnebago, LaSalle and Madison.

Most members publish a personal gmail address rather than a county one, which is
what the county lists; those are their published contact and are carried as-is.

Usage:
    python3 carroll_county_board_scraper.py [output.json]
"""

import html
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_ROSTER_BOT,
    require_robots_once,
    output_path,
)

# The county rebuilt its site in 2026 and the old address
# (/county_board/board_members.php) now answers 404; measured 2026-10-10. The
# members moved to the county board's own page, as Revize staff-directory
# CARDS rather than the old six-column table, so parse() reads both shapes.
SOURCE_URL = "https://www.carrollcountyil.gov/government/county_board/index.php"
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
}
REQUEST_TIMEOUT = 60

ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
EMAIL_RE = re.compile(r"mailto:\s*([^\"?\s>]+)", re.I)
PHONE_RE = re.compile(r"\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}")
# "Dis...t" rather than "District": the county has typo'd one row as "Distirct I"
# (Susan Jacobs, District 1), and an exact-word regex silently dropped a sitting
# board member — the card would have shown two names for a three-member district
# and looked entirely normal. The builder's member floor is the second guard.
DISTRICT_RE = re.compile(r"\bDis\w{0,6}t\s+([IVX]+|\d+)\b", re.I)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7,
         "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12}
ROLE_RE = re.compile(r"\b(Vice[-\s]?Chair(?:man|person|woman)?|Chair(?:man|person|woman)?)\b", re.I)


def text_of(fragment):
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", fragment or ""))).strip()


def to_arabic(token):
    """Roman numeral -> the Arabic string the district map uses."""
    token = (token or "").strip().upper()
    if token.isdigit():
        return str(int(token))
    return str(ROMAN[token]) if token in ROMAN else None


CARD_SPLIT_RE = re.compile(r'<div class="rz-staff-directory-card\b', re.I)
CARD_FIELD_RE = {
    "position": re.compile(r'class="staff-position[^"]*"[^>]*>(.*?)</div>', re.S | re.I),
    "name": re.compile(r'class="staff-name[^"]*"[^>]*>(.*?)</div>', re.S | re.I),
    "bio": re.compile(r'class="staff-bio[^"]*"[^>]*>(.*?)</div>', re.S | re.I),
}
TEL_RE = re.compile(r'href="tel:([^"]+)"', re.I)


def card_rows(page):
    """The 2026 site's staff-directory cards, as the (name, profession, contact
    html) the table parser used to read: profession is the card's position line
    ("Chair / District II") joined to its bio ("Term Expires 2028"), which is
    the same text the old Profession cell carried in one string."""
    rows = []
    for chunk in CARD_SPLIT_RE.split(page)[1:]:
        fields = {}
        for key, rx in CARD_FIELD_RE.items():
            m = rx.search(chunk)
            fields[key] = text_of(m.group(1)) if m else ""
        if not fields["name"]:
            continue
        prof = ", ".join(v for v in (fields["position"], fields["bio"]) if v)
        rows.append((fields["name"], prof, chunk))
    return rows


def record_from(name, prof, contact_html):
    d = DISTRICT_RE.search(prof)
    if not d:
        return None
    district = to_arabic(d.group(1))
    if district is None or not name:
        return None
    rec = {"district": district, "name": name, "profession": prof}
    role = ROLE_RE.search(prof)
    if role:
        rec["role"] = ("Vice Chair" if role.group(1).lower().startswith("vice")
                       else "Board Chair")
    email = EMAIL_RE.search(contact_html)
    if email:
        rec["email"] = html.unescape(email.group(1)).strip()
    tel = TEL_RE.search(contact_html)
    phone = PHONE_RE.search(html.unescape(tel.group(1)) if tel else text_of(contact_html))
    if phone:
        rec["phone"] = re.sub(r"\s+", " ", phone.group(0)).strip()
    term = re.search(r"Term Exp(?:ires|\.)?\s*(\d{4})", prof, re.I)
    if term:
        rec["term_through"] = term.group(1)
    return rec


def parse(page):
    page = SCRIPT_RE.sub(" ", page)
    cards = [r for r in (record_from(*row) for row in card_rows(page)) if r]
    if cards:
        return cards
    records = []
    for row in ROW_RE.findall(page):
        cells = [text_of(c) for c in CELL_RE.findall(row)]
        raw_cells = CELL_RE.findall(row)
        if len(cells) < 4:
            continue
        prof = cells[3]
        d = DISTRICT_RE.search(prof)
        if not d:
            continue
        district = to_arabic(d.group(1))
        if district is None:
            continue
        name = " ".join(p for p in (cells[1], cells[2]) if p).strip()
        if not name:
            continue
        rec = {"district": district, "name": name, "profession": prof}
        role = ROLE_RE.search(prof)
        if role:
            rec["role"] = ("Vice Chair" if role.group(1).lower().startswith("vice")
                           else "Board Chair")
        blob = " ".join(raw_cells[4:])
        email = EMAIL_RE.search(blob)
        if email:
            rec["email"] = html.unescape(email.group(1)).strip()
        phone = PHONE_RE.search(text_of(blob))
        if phone:
            rec["phone"] = re.sub(r"\s+", " ", phone.group(0)).strip()
        term = re.search(r"Term Exp(?:ires|\.)?\s*(\d{4})", prof, re.I)
        if term:
            rec["term_through"] = term.group(1)
        records.append(rec)
    return records


def main():
    out_path = output_path("carroll_county_board_raw.json")
    require_robots_once(SOURCE_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-carroll-county-board-scraper")
    resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    records = parse(resp.text)
    if not records:
        print("carroll-scraper: FAIL — parsed 0 directory rows; the table markup "
              "changed", file=sys.stderr)
        sys.exit(1)
    payload = {"source_url": SOURCE_URL, "records": records}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    odd = [r for r in records if not re.search(r"\bDistrict\b", r.get("profession", ""))]
    for r in odd:
        print("carroll-scraper: note — District is misspelled for %s (%r); read via the "
              "tolerant pattern" % (r["name"], r.get("profession")), file=sys.stderr)
    print("carroll-scraper: wrote %s — %d members across %d districts, %d phones, "
          "%d e-mails, %d role(s)"
          % (out_path, len(records), len({r["district"] for r in records}),
             sum(1 for r in records if r.get("phone")),
             sum(1 for r in records if r.get("email")),
             sum(1 for r in records if r.get("role"))))


if __name__ == "__main__":
    main()
