#!/usr/bin/env python3
"""
Stage 1 of the Warren County Board roster pipeline: scrape the county's own
board page into raw JSON for build_warren_county_board.py, and RE-READ the
district composition from the county's precinct map in the same run.

TWO SOURCES, TWO JOBS. The PEOPLE come from warrencountyil.gov, which publishes
each member as a nested list — name, then "County Board Member District N", the
committees they serve on, the year their term expires, and an e-mail. The
COMPOSITION comes from the legend of the county's own precinct map
(build_warren_boundaries.py), and this module re-reads that legend weekly, which
is the §3.5.1 step-6 tripwire in its strongest available form: the same document
the boundary was built from, re-parsed.

THE E-MAILS ARE CLOUDFLARE-OBFUSCATED — every one of them, with no plain
mailto: anywhere on the page. That is the exact markup that silently emptied
Brown County's seven addresses on 2026-08-08 while every count guard passed, so
this decodes data-cfemail and treats markup-present-but-nothing-decoded as a
hard failure rather than as members with no e-mail.

THE DISTRICT COMES FROM THE MEMBER'S OWN ROW, never from position on the page.
Each member's sub-list contains the literal string "County Board Member District
N", so a member is only ever attributed to the district their own entry names —
the reading that Cumberland's board table and Franklin's grid both punished.

Usage:
    python3 scripts/warren_county_board_scraper.py [-o raw.json]
"""

import argparse
import html
import json
import re
import sys

import requests
from scraper_common import require_robots_once, make_fail, UA_ROSTER_BOT  # noqa: E402  (shared machinery — do not fork)

BOARD_URL = "https://warrencountyil.gov/government/county-board/"
MAP_URL = "https://warrencountyil.gov/wp-content/uploads/2025/07/Precinct-Map.pdf"
TIMEOUT = 60
HEADERS = {"User-Agent": UA_ROSTER_BOT}

EXPECTED_DISTRICTS = ("1", "2", "3", "4")
EXPECTED_MEMBERS = 15
MIN_EMAILS = 12
MIN_TERMS = 12

# The page writes members TWO ways and only one is the obvious shape:
#     <li>Name<ul> …details… </ul></li>                       (thirteen of them)
#     <li>Name</li><li style="…"><ul> …details… </ul></li>     (two of them)
# Matching only the first drops two of the fifteen — and one of the two is the
# CHAIRMAN OF THE BOARD, so the naive parse loses a member and the chair while
# every district still looks populated. Both shapes are matched explicitly
# rather than by searching backwards for a name, which is how an earlier attempt
# at this started reading members' HOME ADDRESSES as their names.
NOT_A_NAME_RE = re.compile(r"(?i)^(county board member|serves on|term expires|chairman|vice|\\d)")
MEMBER_RE = re.compile(
    r"<li[^>]*>(?P<name>[^<>]{3,60}?)<ul>(?P<detail>.*?)</ul>\s*</li>", re.S)
SPLIT_MEMBER_RE = re.compile(
    r"<li[^>]*>(?P<name>[^<>]{3,60}?)</li>\s*<li[^>]*>\s*<ul>(?P<detail>.*?)</ul>\s*</li>",
    re.S)
DISTRICT_RE = re.compile(r"County\s+Board\s+Member\s+District\s+(\d+)", re.I)
TERM_RE = re.compile(r"Term\s+expires\s+(\d{4})", re.I)
COMMITTEE_RE = re.compile(r"Serves\s+on\s+the\s+(.+?)\s*$", re.I)
CFEMAIL_RE = re.compile(r'data-cfemail="([0-9a-f]+)"')
STREET_RE = re.compile(
    r"\d+\s+\S+\s*(st|street|ave|avenue|rd|road|dr|drive|ln|lane|ct|court|"
    r"blvd|hwy|way|circle|cir|place|pl|trail)\b", re.I)


fail = make_fail("warren-board-scraper")


def get(url, binary=False):
    try:
        require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                            label="il-warren-county-board-scraper")
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001 — any failure is a refusal to write
        fail("could not read %s (%s: %s)" % (url, type(exc).__name__, exc))
    return resp.content if binary else resp.text


def cf_decode(blob):
    """Cloudflare e-mail obfuscation: hex, XOR-keyed by its own first byte."""
    try:
        key = int(blob[:2], 16)
        return "".join(chr(int(blob[i:i + 2], 16) ^ key)
                       for i in range(2, len(blob), 2))
    except (ValueError, IndexError):
        return ""


def clean(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def scrape_members(page):
    """-> {district: [member]}.

    THE DETAIL LIST ENDS WITH A HOME ADDRESS on every member, so the address
    line is identified and DISCARDED rather than filtered afterwards — the
    Madison/Peoria rule. The count of dropped lines is returned so a run can say
    it saw them and refused them, instead of being silent about it.
    """
    obfuscated = len(CFEMAIL_RE.findall(page))
    roster, decoded, addresses = {}, 0, 0
    seen = set()
    for pattern in (MEMBER_RE, SPLIT_MEMBER_RE):
        for match in pattern.finditer(page):
            name = clean(match.group("name"))
            detail = match.group("detail")
            dmatch = DISTRICT_RE.search(clean(detail))
            if not name or not dmatch:
                continue
            if NOT_A_NAME_RE.match(name) or STREET_RE.search(name):
                continue
            key = (name, dmatch.group(1))
            if key in seen:
                continue
            seen.add(key)
            member = {"name": name, "district": dmatch.group(1)}
            committees = []
            for item in re.findall(r"<li[^>]*>(.*?)</li>", detail, re.S):
                text = clean(item)
                if not text or DISTRICT_RE.match(text):
                    continue
                if STREET_RE.search(text):
                    addresses += 1          # a residence: seen, counted, dropped
                    continue
                cmatch = COMMITTEE_RE.match(text)
                if cmatch:
                    committees.append(cmatch.group(1).strip())
                    continue
                if re.match(r"(?i)^chairman\s+of\s+the\s+board$", text):
                    member["role"] = text    # an OFFICE, not a committee seat
                    continue
                if re.match(r"(?i)^(chairman|vice[- ]chair)", text):
                    committees.append(text)
                    continue
                term = TERM_RE.match(text)
                if term:
                    member["termExpires"] = term.group(1)
                    continue
                phone = re.match(r"^(\d{3}-\d{3}-\d{4})$", text)
                if phone:
                    member["phone"] = phone.group(1)
            if committees:
                member["committees"] = committees
            blob = CFEMAIL_RE.search(detail)
            if blob:
                address = cf_decode(blob.group(1))
                if address and "@" in address:
                    member["email"] = address
                    decoded += 1
            roster.setdefault(member["district"], []).append(member)
    if obfuscated and not decoded:
        fail("the page carries %d Cloudflare-obfuscated address(es) and none "
             "decoded — this is the Brown County failure, where every count "
             "guard passed while the contact column emptied" % obfuscated)
    if not addresses:
        fail("no residence lines were seen on the board page — this county "
             "publishes one per member, so their disappearance means the layout "
             "changed and this parse should be re-read before it is trusted")
    return roster, addresses


def read_map_legend():
    """Re-read the district->precinct table from the county's own precinct map.

    This is the same document build_warren_boundaries.py took the composition
    from, so a change here is a change to the shipped boundary's only source.
    """
    import io
    try:
        import pdfplumber
    except ImportError:
        fail("pdfplumber is required to re-read the county's precinct-map legend")
    from collections import defaultdict
    data = get(MAP_URL, binary=True)
    if not data.startswith(b"%PDF"):
        fail("the precinct map at %s did not return a PDF (%d bytes) — a 200 of "
             "plausible size is not a document" % (MAP_URL, len(data)))
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        page = pdf.pages[0]
        words = [w for w in page.extract_words() if w["top"] > 1040]
    columns = {}
    for word in words:
        if not re.match(r"(?i)^district$", word["text"]):
            continue
        nxt = [w for w in words
               if abs(w["top"] - word["top"]) < 8 and 0 < w["x0"] - word["x1"] < 30]
        if nxt:
            columns[float(word["x0"])] = nxt[0]["text"]
    if sorted(columns.values()) != sorted(EXPECTED_DISTRICTS):
        fail("the precinct map's legend now heads columns %s, expected %s — the "
             "county reapportioned, or the map was replaced"
             % (sorted(columns.values()), list(EXPECTED_DISTRICTS)))
    xs = sorted(columns)
    rows = defaultdict(list)
    for word in words:
        if re.match(r"(?i)^district$", word["text"]):
            continue
        if word["text"] in columns.values() and word["top"] < 1072:
            continue
        rows[(round(word["top"] / 6),
              min(xs, key=lambda c: abs(c - word["x0"])))].append(word)
    comp = defaultdict(list)
    for (_row, col), group in sorted(rows.items()):
        text = " ".join(g["text"] for g in sorted(group, key=lambda g: g["x0"])).strip()
        if text:
            comp[columns[col]].append(text)
    return {d: sorted(v) for d, v in comp.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("-o", "--out", default="warren_county_board_raw.json")
    args = parser.parse_args()

    roster, addresses = scrape_members(get(BOARD_URL))
    districts = sorted(roster, key=int)
    total = sum(len(v) for v in roster.values())
    if tuple(districts) != EXPECTED_DISTRICTS:
        fail("the board page names districts %s, expected %s"
             % (districts, list(EXPECTED_DISTRICTS)))
    if total != EXPECTED_MEMBERS:
        fail("%d members parsed, expected %d" % (total, EXPECTED_MEMBERS))
    emails = sum(1 for ms in roster.values() for m in ms if m.get("email"))
    terms = sum(1 for ms in roster.values() for m in ms if m.get("termExpires"))
    if emails < MIN_EMAILS:
        fail("%d members carry an e-mail, floor is %d" % (emails, MIN_EMAILS))
    if terms < MIN_TERMS:
        fail("%d members carry a term year, floor is %d" % (terms, MIN_TERMS))
    for members in roster.values():
        for member in members:
            for key, value in member.items():
                if STREET_RE.search(str(value)):
                    fail("a street address reached %s's %s (%r)"
                         % (member["name"], key, value))

    composition = read_map_legend()

    payload = {
        "boardUrl": BOARD_URL,
        "mapUrl": MAP_URL,
        "districts": {d: roster[d] for d in districts},
        "composition": composition,
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    phones = sum(1 for ms in roster.values() for m in ms if m.get("phone"))
    print("warren-board-scraper: %d members across %d districts (%d e-mails, "
          "%d phones, %d term years; %d residence lines seen and dropped) -> %s"
          % (total, len(districts), emails, phones, terms, addresses, args.out),
          file=sys.stderr)
    print("  legend re-read: %s"
          % {d: len(v) for d, v in sorted(composition.items())}, file=sys.stderr)


if __name__ == "__main__":
    main()
