#!/usr/bin/env python3
"""
Scrape the North Carolina General Assembly's own member lists for the office
block Open States does not carry.

WHY THIS EXISTS. Open States' current-people export is the fleet-standard
roster base for a state chamber, and for North Carolina it publishes name,
party, district and an e-mail for every one of the 170 seats — and **no
capitol address, no capitol phone, no district address and no district phone
for any of them** (0 of 170, measured 2026-09-29). The General Assembly's own
member lists carry exactly the other half: every listed member's Legislative
Building room and Capitol telephone, 54 of 54 Senate entries and 125 of 125
House entries. So people and e-mail come from Open States and the office and
phone come from here, joined by district.

TWO TRAPS IN THIS PAGE, BOTH MEASURED 2026-09-29.

First, THE OFFICE AND PHONE ARE PRINT-ONLY. They sit in `d-none
d-print-block` blocks — present in the served HTML, invisible in a browser —
so a parser written against what a browser shows returns nothing at all, and
a headless render would be worse than useless here. There is no JSON
endpoint and no JavaScript to execute: one request answers a whole chamber.

Second, THE PAGE KEEPS A DEPARTED MEMBER BESIDE THEIR SUCCESSOR. Each is
tagged in a parenthetical after the party — `(Resigned 5/1/26)`,
`(Appointed 5/21/26)`, `(Deceased 3/18/26)` — and nine districts carried two
people on the day this was written (Senate 1, 18, 23, 34 and House 40, 47,
60, 90, 119), which is why the Senate list holds 54 entries for 50 districts
and the House 125 for 120. **DOCUMENT ORDER IS ALPHABETICAL BY SURNAME, NOT
CHRONOLOGICAL**, so taking the last entry per district ships the RESIGNED
member for Senate 23 and 34 and House 90. The parenthetical is the
authority: a DEPARTED tag loses to any other entry for the same district.
It is not cosmetic — Senate 34's two entries give different rooms (300-B and
2106).

THE TWO CHAMBERS FORMAT A TELEPHONE DIFFERENTLY and neither is reformatted
here: the Senate prints "(919) 715-8293" and the House "919-733-5530". Each
is the publisher's own rendering of its own number, and normalising them
would be this project editing a contact detail to look tidier.

WHAT IT REFUSES TO RETURN. Only the room and the Capitol telephone, plus the
member's name for the builder's own cross-check. The page also prints a
legislative assistant's name, which is a staff member's identity and no part
of answering who represents you, so it is not read. No address is published
on these pages at all, so there is no home-address risk of the shape
Michigan's Senate scraper guards against.

ROBOTS. www.ncleg.gov's robots.txt disallows /WHPTest/ and /Ethics/ under a
single `*` group and states `Crawl-delay: 2`; /Members/ is allowed. The gate
is asked before the first fetch and the delay is honoured through HostPacer.
That file begins with a BYTE-ORDER MARK, the shape that made this project
misread ISBE's `Disallow: /` as a permission for a year — see robots_gate.py.

Usage:
    python3 nc/scripts/ncga_member_scraper.py            # JSON to stdout
    python3 nc/scripts/ncga_member_scraper.py out.json   # JSON to a file
"""

import html as html_module
import json
import re
import sys

from robots_gate import RobotsGate, HostPacer

USER_AGENT = "districtry/1.0 (+https://districtry.com/nc/)"

CHAMBER_URL = {
    "upper": "https://www.ncleg.gov/Members/MemberList/S",
    "lower": "https://www.ncleg.gov/Members/MemberList/H",
}

# One member's card. The list is a Bootstrap grid and this class run opens
# each member column; splitting on it is what keeps a member's room, phone and
# district together, which a flat regex over the page would not.
MEMBER_SPLIT = 'class="col-12 col-sm-6 col-lg-3 pr-0 member-col"'

BIOGRAPHY_RE = {
    "upper": re.compile(r'/Members/Biography/S/(\d+)">([^<]+)</a>'),
    "lower": re.compile(r'/Members/Biography/H/(\d+)">([^<]+)</a>'),
}
DISTRICT_RE = re.compile(r'/Redistricting/DistrictPlanMap/[^/"]+/(\d+)')
OFFICE_RE = re.compile(r"<strong>Office</strong>:(?:&nbsp;|\s)*([^<]+)")
PHONE_RE = re.compile(r"<strong>Phone</strong>:(?:&nbsp;|\s)*([^<]+)")
# The parenthetical after the party. DEPARTED loses to anything else for the
# same district; an APPOINTED tag is kept exactly as any untagged entry is.
DEPARTED_RE = re.compile(r"\((Resigned|Deceased|Withdrawn)[^)]*\)", re.I)


def fetch(chamber, session=None, gate=None, pacer=None):
    """The chamber's member-list HTML, after asking robots.txt."""
    import requests  # noqa: PLC0415 — network only; the parse is importable offline

    session = session or requests.Session()
    gate = gate or RobotsGate(session, USER_AGENT)
    pacer = pacer or HostPacer(gate)
    url = CHAMBER_URL[chamber]
    allowed, why = gate.allows(url)
    if not allowed:
        raise RuntimeError("robots.txt refuses %s (%s)" % (url, why))
    with pacer.hold(url):
        resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=90)
    resp.raise_for_status()
    return resp.text


def parse(html, chamber):
    """{district -> {name, office, phone}} for the member currently seated.

    A district carrying both a departed member and a successor resolves to the
    successor, whichever order the page printed them in.
    """
    bio_re = BIOGRAPHY_RE[chamber]
    out = {}
    for block in html.split(MEMBER_SPLIT)[1:]:
        district = DISTRICT_RE.search(block)
        member = bio_re.search(block)
        if not district or not member:
            continue
        key = district.group(1).lstrip("0") or district.group(1)
        text = re.sub(r"<[^>]+>", " ", block)
        entry = {
            # UNESCAPED. The page serves a name with a non-ASCII letter as a
            # numeric character reference — "Erin Par&#xE9;" for Paré,
            # measured 2026-09-29 — so a raw capture ships the entity text
            # into a name the builder then cross-checks and the card prints.
            "name": html_module.unescape(member.group(2)).strip(),
            "departed": bool(DEPARTED_RE.search(text)),
        }
        office = OFFICE_RE.search(block)
        if office:
            entry["office"] = html_module.unescape(office.group(1)).strip()
        phone = PHONE_RE.search(block)
        if phone:
            entry["phone"] = html_module.unescape(phone.group(1)).strip()
        prior = out.get(key)
        # The successor wins on the tag, never on document order.
        if prior is None or (prior.get("departed") and not entry["departed"]):
            out[key] = entry
    return {k: {kk: vv for kk, vv in v.items() if kk != "departed"}
            for k, v in sorted(out.items(), key=lambda kv: int(kv[0]))}


def parse_all(fetcher=fetch):
    return {chamber: parse(fetcher(chamber), chamber) for chamber in CHAMBER_URL}


def main():
    if len(sys.argv) > 2:
        print("usage: %s [out.json]" % sys.argv[0], file=sys.stderr)
        sys.exit(1)
    data = parse_all()
    for chamber, roster in data.items():
        print("%s: %d districts, %d with an office, %d with a phone"
              % (chamber, len(roster),
                 sum(1 for m in roster.values() if m.get("office")),
                 sum(1 for m in roster.values() if m.get("phone"))), file=sys.stderr)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if len(sys.argv) == 2:
        with open(sys.argv[1], "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
