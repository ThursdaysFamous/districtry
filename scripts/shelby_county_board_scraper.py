#!/usr/bin/env python3
"""
Scrape Shelby County's board roster into raw board-roster records.

Stage 1 of the two-stage pipeline (scripts/build_shelby_board_roster.py is
stage 2). The county publishes its County Board twice, and this scraper reads
BOTH so the builder can hold them against each other:

  * coboard.aspx — eleven district cards (semantic markup: div.board-card >
    h2 / p.board-precincts / div.board-member), each carrying the district's
    PRECINCT COMPOSITION and two members: name, an optional
    "(Board Chair)" / "(Board Vice Chair)" tag, party, term, phone, and one
    or two e-mails (the chair and vice chair each carry a role alias beside
    their district address). A vacant seat prints "Currently Vacant" with the
    district's e-mail and nothing else — that is shipped as a vacancy, never
    dropped, per the Bureau lesson.
  * contacts.aspx — the county's e-mail directory, a 24-row table (22 seats
    plus the two role aliases) of Office | Name | E-mail.

The composition lines are the same text scripts/build_shelby_board_districts.py
compiles its boundary from, so the builder cross-checks them weekly — a
redistricting turns the roster job red instead of leaving the shipped lines
a cycle out of date (the DeWitt pattern).

What is deliberately NOT read: each member's HOME ADDRESS, printed in an
<address> block on every card. This project never ships officials' home
addresses (the Mason/Marshall precedent), so the scraper does not even
capture them into its raw output — nothing downstream can leak what stage 1
never wrote.

FETCH POSTURE: open. Plain server-rendered ASP.NET HTML, no challenge.

Usage:
    python3 shelby_county_board_scraper.py [output.json]   # default: stdout
"""

import html as html_mod
import json
import re
import sys

import requests
from scraper_common import require_robots_once, UA_CHROME_X11_128, fetch as fetch_with_retry  # noqa: E402  (shared machinery — do not fork)

BOARD_URL = "https://www.shelbycounty-il.gov/coboard.aspx"
CONTACTS_URL = "https://www.shelbycounty-il.gov/contacts.aspx"
UA = {"User-Agent": UA_CHROME_X11_128}

# Cards are delimited by their OPENING tags, not by matching close tags: a
# non-greedy close-tag match swallowed the second member's </div> and every
# district parsed one member instead of two. Each split element runs to the
# next card's opening (the last runs into the page footer, which the anchored
# field regexes ignore).
CARD_OPEN_RE = re.compile(r'<div class="board-card">')
H2_RE = re.compile(r"<h2>(.*?)</h2>", re.S)
PRECINCTS_RE = re.compile(r'<p class="board-precincts">(.*?)</p>', re.S)
MEMBER_RE = re.compile(r'<div class="board-member">(.*?)</div>', re.S)
H3_RE = re.compile(r"<h3>(.*?)</h3>", re.S)
ROLE_RE = re.compile(r"\(Board\s+(Chair|Vice\s+Chair)\)", re.I)
TERM_P_RE = re.compile(r'<p class="board-term">(.*?)</p>', re.S)
TEL_RE = re.compile(r'href="tel:[^"]*"[^>]*>([^<]+)<')
MAILTO_RE = re.compile(r'href="mailto:([^"?]+)"')
UPDATED_RE = re.compile(r"Updated\s+([A-Z][a-z]+ \d{1,2}, \d{4})")
DISTRICT_RE = re.compile(r"^District\s+(\d+)$")
CONTACT_ROW_RE = re.compile(
    r"<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>",
    re.S)


def clean(fragment):
    """Tag-free, entity-decoded, whitespace-collapsed text."""
    text = html_mod.unescape(re.sub(r"(?s)<[^>]+>", " ", fragment or ""))
    return " ".join(text.split())


def fetch(url):
    # scraper_common.fetch retries 429/5xx (numeric Retry-After honoured,
    # capped) and refuses to retry 401/403/404 — the Henry rule. Parsing and
    # every page check stay in this file.
    require_robots_once(url, UA["User-Agent"], headers=UA,
                        label="il-shelby-county-board-scraper")
    return fetch_with_retry(url, UA, timeout=60).text


def parse_board(page):
    records, updated = [], None
    m = UPDATED_RE.search(clean(page))
    if m:
        updated = m.group(1)
    for card in CARD_OPEN_RE.split(page)[1:]:
        h2 = H2_RE.search(card)
        title = clean(h2.group(1)) if h2 else ""
        dm = DISTRICT_RE.match(title)
        if not dm:
            continue                # the Board Administrative Assistant card
        district = dm.group(1)
        pre = PRECINCTS_RE.search(card)
        composition = clean(pre.group(1)) if pre else None
        members = []
        for block in MEMBER_RE.findall(card):
            h3 = H3_RE.search(block)
            if not h3:
                continue
            role_m = ROLE_RE.search(h3.group(1))
            role = None
            if role_m:
                role = "Vice Chair" if role_m.group(1).lower().startswith("vice") else "Chair"
            name = clean(ROLE_RE.sub("", h3.group(1)))
            term_m = TERM_P_RE.search(block)
            party = term = None
            if term_m:
                bits = [b.strip() for b in clean(term_m.group(1)).split("·")]
                if bits:
                    party = bits[0] or None
                if len(bits) > 1:
                    term = re.sub(r"^Term\s+", "", bits[1]) or None
            tel = TEL_RE.search(block)
            emails = [e.strip().lower() for e in MAILTO_RE.findall(block)]
            members.append({
                "name": name,
                "vacant": name.lower() == "currently vacant",
                "role": role,
                "party": party,
                "term": term,
                "phone": clean(tel.group(1)) if tel else None,
                "emails": emails,
                # NO address field, by design — see the module header.
            })
        records.append({"district": district, "composition": composition,
                        "members": members})
    return records, updated


def parse_contacts(page):
    """The County Board Members table only — the page also lists department
    heads, whose rows have two columns and are skipped by the three-column
    match; the board section is additionally cut at its closing table."""
    start = page.find("County Board Members")
    if start < 0:
        return []
    end = page.find("</table>", start)
    section = page[start:end if end > 0 else len(page)]
    rows = []
    for office, name, email in CONTACT_ROW_RE.findall(section):
        office, name, email = clean(office), clean(name), clean(email).lower()
        if not office or office.lower() == "office" or "@" not in email:
            continue
        rows.append({"office": office, "name": name, "email": email})
    return rows


def main():
    board_records, updated = parse_board(fetch(BOARD_URL))
    contacts = parse_contacts(fetch(CONTACTS_URL))

    if not board_records:
        print("shelby-board-scraper: FAIL — zero district cards parsed "
              "(markup change?)", file=sys.stderr)
        sys.exit(1)
    if not contacts:
        print("shelby-board-scraper: FAIL — the contacts.aspx board table "
              "parsed to zero rows (markup change?)", file=sys.stderr)
        sys.exit(1)

    out = json.dumps({
        "source": BOARD_URL,
        "contactsSource": CONTACTS_URL,
        "updated": updated,
        "records": board_records,
        "contacts": contacts,
    }, indent=2, ensure_ascii=False)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(out)
        print("shelby-board-scraper: %d district cards + %d contact rows -> %s"
              % (len(board_records), len(contacts), sys.argv[1]))
    else:
        print(out)


if __name__ == "__main__":
    main()
