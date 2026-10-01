#!/usr/bin/env python3
"""
Scrape the Fulton County Board roster from the county's own Members page.

SOURCE. https://fultoncountyil.gov/county-board/members/ — a WordPress page that
publishes the board twice over, and both halves are needed:

  * a PHOTO GRID grouped under "District #1/2/3" headings, which is the only
    place the district is stated; and
  * a set of HIDDEN POPUP blocks (`mfp-hide elected_popup_otr`), one per member,
    which carry the e-mail address the grid omits.

Neither half is sufficient alone, so this joins them on the member's name.

THE CHAIRMAN SECTION IS A ROLE, NOT A SEAT. Above District #1 sits a fourth
section headed "Fulton County Board Chairman" containing one member — currently
John Spangler, who ALSO appears in his own District #2. Swept naively that is a
sixteenth board member and a district-2 count of six. It is read here as what it
is: the source of the `Chair` role, applied to the matching district row.
Barclay's "Vice-Chair" arrives differently again, glued onto the end of his name
inside the same heading ("James A Barclay (R) Vice-Chair"), so it is split off
rather than left to corrupt the name.

WHITESPACE MATTERS HERE. The page indents its markup, so `<div …><h3>` patterns
do not match the raw bytes; tags are closed up before parsing. Written down
because the first attempt silently produced zero members with no error — the
counts below are what caught it.

NAMES SHIP AS THE COUNTY PRINTS THEM, including "Karl WIlliams" with its
capital I. Correcting an officeholder's name is not ours to do, and the same
rule that ships Washington County's typo'd e-mail domain applies here.

Usage:
    python3 scripts/fulton_county_board_scraper.py --out fulton_board_raw.json
"""

import argparse
import collections
import datetime
import json
import re
import sys
from scraper_common import require_robots_once, UA_CIVIC_BOT  # noqa: E402  (shared machinery — do not fork)

try:
    import requests
except ImportError:  # pragma: no cover
    sys.exit("requests is required: pip install -c scripts/requirements.txt requests")

SOURCE_URL = "https://fultoncountyil.gov/county-board/members/"
COUNTY_PAGE = "https://fultoncountyil.gov/county-board/"
TIMEOUT = 45
USER_AGENT = UA_CIVIC_BOT

# 3 districts electing FIVE members each = 15. Floors sit three under the full
# board so a vacancy does not fail a weekly run, but a parse regression does.
EXPECTED_DISTRICTS = ("1", "2", "3")
SEATS_PER_DISTRICT = 5
MIN_MEMBERS = 12
MIN_EMAILS = 9

SECTION_RE = re.compile(
    r'(?is)<div class="member_loop_cat">(.*?)'
    r'(?=<div class="member_loop_cat">|<footer|\Z)')
TITLE_RE = re.compile(r"(?is)<h2>(.*?)</h2>")
CARD_RE = re.compile(
    r'(?is)<div class="elected_page_col_txt"><h3>(.*?)</h3><p>(.*?)</p>')
POPUP_RE = re.compile(
    r'(?is)<div class="mfp-hide elected_popup_otr".*?>(.*?)'
    r'(?=<div class="mfp-hide elected_popup_otr|\Z)')
POPUP_NAME_RE = re.compile(r"(?is)<h3>(.*?)</h3>")
MAILTO_RE = re.compile(r'(?is)href="mailto:\s*([^"]+)"')
DISTRICT_RE = re.compile(r"(?i)District\s*#?\s*(\d+)")
CHAIR_SECTION_RE = re.compile(r"(?i)chairman|chairperson|chair\b")
PARTY_RE = re.compile(r"\s*\(([DRI])\)\s*", re.I)
ROLE_RE = re.compile(r"(?i)\s*(Vice[-\s]*Chair(?:man|person)?|Chair(?:man|person)?)\s*$")
YEAR_RE = re.compile(r"(20\d\d)")


def text(fragment):
    out = re.sub(r"(?is)<[^>]+>", " ", fragment or "")
    for entity, char in (("&amp;", "&"), ("&nbsp;", " "), ("&#39;", "'"),
                         ("&#038;", "&"), ("&rsquo;", "’"), ("&quot;", '"')):
        out = out.replace(entity, char)
    return re.sub(r"\s+", " ", out).strip()


def split_name(raw):
    """'James A Barclay (R) Vice-Chair' -> ('James A Barclay', 'R', 'Vice-Chair')."""
    name = text(raw)
    role = None
    role_match = ROLE_RE.search(name)
    if role_match:
        role = role_match.group(1).strip()
        name = name[:role_match.start()].strip()
    party = None
    party_match = PARTY_RE.search(name)
    if party_match:
        party = party_match.group(1).upper()
        name = (name[:party_match.start()] + " " + name[party_match.end():]).strip()
    return re.sub(r"\s+", " ", name).strip(" ,"), party, role


def norm(name):
    return re.sub(r"[^a-z]", "", (name or "").lower())


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", default="fulton_board_raw.json")
    parser.add_argument("--html", help="parse a saved copy instead of fetching")
    args = parser.parse_args()

    if args.html:
        with open(args.html, encoding="utf-8") as handle:
            html = handle.read()
    else:
        require_robots_once(SOURCE_URL, USER_AGENT, headers={"User-Agent": USER_AGENT},
                            label="il-fulton-county-board-scraper")
        response = requests.get(SOURCE_URL, timeout=TIMEOUT,
                                headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        html = response.text
    html = re.sub(r">\s+<", "><", html)          # see the module docstring

    # e-mail by member, from the hidden popups
    emails = {}
    for block in POPUP_RE.findall(html):
        name_match = POPUP_NAME_RE.search(block)
        mail_match = MAILTO_RE.search(block)
        if not name_match or not mail_match:
            continue
        person, _, _ = split_name(name_match.group(1))
        emails.setdefault(norm(person), text(mail_match.group(1)).replace(" ", ""))

    members = []
    chair_names = []
    for section in SECTION_RE.findall(html):
        title_match = TITLE_RE.search(section)
        title = text(title_match.group(1)) if title_match else ""
        cards = CARD_RE.findall(section)
        district_match = DISTRICT_RE.search(title)

        if district_match is None:
            # the leadership feature — a ROLE, not a seat (see the docstring)
            if CHAIR_SECTION_RE.search(title):
                for raw_name, _ in cards:
                    person, _, _ = split_name(raw_name)
                    if person:
                        chair_names.append(person)
            continue

        district = district_match.group(1)
        for raw_name, raw_term in cards:
            person, party, role = split_name(raw_name)
            if not person:
                continue
            year = YEAR_RE.search(text(raw_term))
            members.append({
                "name": person,
                "district": district,
                "party": party,
                "role": role,
                "email": emails.get(norm(person)) or None,
                "term_expires": year.group(1) if year else None,
            })

    # apply the Chair role to the member's own district row
    for chair in chair_names:
        matched = [m for m in members if norm(m["name"]) == norm(chair)]
        if not matched:
            print("  FAIL: the Chairman section names %r, who appears in no "
                  "district — the page's two halves disagree" % chair,
                  file=sys.stderr)
            sys.exit(1)
        for m in matched:
            m["role"] = m["role"] or "Chair"

    per = collections.Counter(m["district"] for m in members)

    problems = []
    if len(members) < MIN_MEMBERS:
        problems.append("%d members < floor %d" % (len(members), MIN_MEMBERS))
    missing = [d for d in EXPECTED_DISTRICTS if d not in per]
    if missing:
        problems.append("no members for district(s) %s" % ", ".join(missing))
    for district, count in sorted(per.items()):
        if count > SEATS_PER_DISTRICT:
            problems.append("district %s has %d members but the board seats %d "
                            "per district — the Chairman feature was probably "
                            "swept in as a seat" % (district, count, SEATS_PER_DISTRICT))
    with_email = sum(1 for m in members if m["email"])
    if with_email < MIN_EMAILS:
        problems.append("%d e-mails < floor %d — the popup blocks that carry "
                        "them may have moved" % (with_email, MIN_EMAILS))
    seen = collections.Counter(norm(m["name"]) for m in members)
    dupes = [n for n, c in seen.items() if c > 1]
    if dupes:
        problems.append("%d member(s) appear twice — the Chairman section is a "
                        "role, not a seat" % len(dupes))

    if problems:
        for problem in problems:
            print("  FAIL: %s" % problem, file=sys.stderr)
        print("FATAL: refusing to write a payload that lost coverage", file=sys.stderr)
        sys.exit(1)

    payload = {
        "county": "Fulton",
        "source_url": SOURCE_URL,
        "county_page": COUNTY_PAGE,
        "scraped_at": datetime.datetime.now(datetime.timezone.utc)
                              .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "members": members,
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print("scraped %d members across %d districts (%s), %d with e-mail, %d with "
          "party, %d with a term year, roles: %s -> %s"
          % (len(members), len(per),
             ", ".join("D%s=%d" % (d, per[d]) for d in sorted(per)),
             with_email, sum(1 for m in members if m["party"]),
             sum(1 for m in members if m["term_expires"]),
             ", ".join(sorted({m["role"] for m in members if m["role"]})) or "none",
             args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
