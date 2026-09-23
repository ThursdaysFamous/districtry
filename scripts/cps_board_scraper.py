#!/usr/bin/env python3
"""
The Chicago Board of Education's own members, from the Board's own site.

WHY THIS EXISTS. il/data/app/school-board-members.json was HAND-CURATED, and
the record said why: sources.html and metro-worksheet.json both stated that it
is hand-verified "because no machine-readable roster is published for this
board". Measured 2026-09-23 that is false, and had been for some time —
cpsboe.org publishes every seat as a semantic list (<ol class="bios">, one
<li> per member carrying .name, .title and .district spans plus a link to that
member's own bio page), and each bio page repeats the three and adds a cps.edu
address. A hand-curated file with nothing re-reading it drifts, and this one
had:

  * District 9a shipped the bare string VACANT. The Board's own index names
    its VICE PRESIDENT there, Dr. Angel L. Velez.
  * District 10b shipped Olga Bautista. The Board's news of 4 September 2026
    says she RESIGNED IN MARCH and that Connie L. Anderson was sworn in on
    27 August to succeed her.
  * District 4a shipped "Karen Zacor". The Board spells it Zaccor.

ABSENCE IS NOT VACANCY, and this source pair is the reason the rule is written
into the builder rather than assumed. On the same day, CPS's own page at
cps.edu/about/chicago-board-of-education/ listed twenty of the twenty-one
seats and simply had no row for District 10B — the seat Anderson holds. A list
that does not mention a district is a list that is behind, never a statement
that the seat is empty. So the builder FAILS on a district the Board's index
does not carry, and ships a vacancy only where the Board itself prints one.

THE PRESIDENT HOLDS NO DISTRICT AND THE SOURCE SAYS SO IN WORDS: his <li>
carries an EMPTY .district span rather than no span, which is the difference
between a seat drawn city-wide and a parse that lost a field. The builder
keeps him out of the district roster and on the board block.

FETCH POSTURE: open, and read by the rules. robots.txt is fetched first, as
the client that fetches — the districtry token, which www.cpsboe.org serves a
full page (200, 15.4 KB on 2026-09-23). Its robots.txt is 93 bytes, allows /,
states no Crawl-delay and carries no Content-Signal.

THE BIOS ARE PROSE AND ONLY THREE FIELDS ARE READ FROM THEM: the <h1> name,
the two <p> lines under it (role and district) and the mailto: in the contact
heading. Several bios say which neighbourhood a member lives in; nothing here
parses a member's home, in any form (the Madison/Peoria rule).

Stage 1 of the two-stage pattern; scripts/build_chicago_school_board_roster.py
is stage 2.

    python3 scripts/cps_board_scraper.py --out cps_board.json
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests                                                   # noqa: E402

from robots_policy import RobotsGate                              # noqa: E402
from scraper_common import make_fail                              # noqa: E402

BASE = "https://www.cpsboe.org"
INDEX_URL = BASE + "/about/bios"
USER_AGENT = "districtry/1.0 (+https://districtry.com/il/)"

# The Board seats 21: a president appointed city-wide plus twenty sub-district
# members. A floor rather than an equality, because the builder is where the
# exact shape is proved against the shipped geometry — a scraper that insisted
# on 21 would fail on the day a seat empties, which is a thing the Board is
# allowed to do and this pipeline has to carry.
MIN_ROWS = 18

LI_RE = re.compile(
    r'<li>\s*<a href="(?P<href>/about/bios/\d+)".*?'
    r'<span class="name">(?P<name>.*?)</span>.*?'
    r'<span class="title">(?P<title>.*?)</span>.*?'
    r'<span class="district">(?P<district>.*?)</span>',
    re.S)
BIO_HEADER_RE = re.compile(
    r'<div class="bio-name">\s*<h1>(?P<name>.*?)</h1>(?P<rest>.*?)</div>', re.S)
MAILTO_RE = re.compile(r'href="mailto:([^"?]+)"', re.I)
VCARD_RE = re.compile(r'<address class="vcard">(.*?)</address>', re.S)


fail = make_fail("cps-board-scraper")


def clean(text):
    """Tags out, entities in, whitespace collapsed. Returns "" for nothing."""
    import html as html_mod
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html_mod.unescape(text).replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


def span(markup, name):
    m = re.search(r'<span class="%s">(.*?)</span>' % name, markup, re.S)
    return clean(m.group(1)) if m else ""


def parse_index(html):
    """[{name, role, district, profile_url}] in the order the Board lists them.

    The district is the span's text exactly as published ("District 9A", or ""
    for the president), normalised no further here: the builder is what maps it
    onto the shipped geometry's own sub-district labels, and a scraper that
    normalised first would hide a source that changed its scheme.
    """
    block = re.search(r'<ol class="bios">(.*?)</ol>', html, re.S)
    if not block:
        fail("no <ol class=\"bios\"> on %s — the index's markup moved" % INDEX_URL)
    rows = []
    for m in LI_RE.finditer(block.group(1)):
        name = clean(m.group("name"))
        if not name:
            fail("a member <li> on %s carries no name" % INDEX_URL)
        rows.append({
            "name": name,
            "role": clean(m.group("title")),
            "district": clean(m.group("district")),
            "profile_url": BASE + m.group("href"),
        })
    return rows


def parse_bio(html, url):
    """{name, role, district, email} from one member's own page.

    The SECOND WITNESS, and the reason each bio is fetched at all: the index is
    one block of repeating markup, so a single pattern reading it wrongly reads
    all twenty-one wrongly and every count still passes. The bio page states
    the same three facts in a different element, so the builder can require
    that they agree.
    """
    header = BIO_HEADER_RE.search(html)
    if not header:
        fail("no <div class=\"bio-name\"> on %s — the bio markup moved" % url)
    lines = [clean(p) for p in re.findall(r"<p>(.*?)</p>", header.group("rest"), re.S)]
    lines = [l for l in lines if l]
    district = next((l for l in lines if re.match(r"(?i)^district\b", l)), "")
    role = next((l for l in lines if l != district), "")
    mail = MAILTO_RE.search(html)
    return {
        "name": clean(header.group("name")),
        "role": role,
        "district": district,
        "email": mail.group(1).strip().lower() if mail else None,
    }


def parse_office(html):
    """The Board's own office, from the hCard in the site footer.

    It is published as an <address class="vcard"> with .org, .street-address,
    .locality, .region, .postal-code and .tel, which is the Board saying where
    it sits rather than this project reading an address off a page and hoping.
    """
    card = VCARD_RE.search(html)
    if not card:
        return None
    markup = card.group(1)
    street = span(markup, "street-address").rstrip(",")
    locality = span(markup, "locality")
    region = span(markup, "region")
    postal = span(markup, "postal-code")
    tel = re.sub(r"\s*phone\s*$", "", span(markup, "tel"), flags=re.I)
    if not (street and locality):
        return None
    return {
        "org": span(markup, "org") or None,
        "address": ", ".join(p for p in [street, locality,
                                         " ".join(p for p in [region, postal] if p)]
                             if p),
        "phone": tel or None,
    }


def scrape(delay=0.5, timeout=60):
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT,
                            "Accept": "text/html,application/xhtml+xml"})
    gate = RobotsGate(session, USER_AGENT)
    ok, why = gate.allows(INDEX_URL)
    if not ok:
        fail("robots.txt refuses %s: %s" % (INDEX_URL, why))
    stated = gate.crawl_delay(INDEX_URL)
    if stated:
        print("cps-board-scraper: honouring Crawl-delay %.1fs" % stated, file=sys.stderr)
        delay = max(delay, stated)

    resp = session.get(INDEX_URL, timeout=timeout)
    resp.raise_for_status()
    index_html = resp.text
    rows = parse_index(index_html)
    if len(rows) < MIN_ROWS:
        fail("%s listed %d members, floor %d — the index's markup moved or the "
             "page is partial" % (INDEX_URL, len(rows), MIN_ROWS))

    for i, row in enumerate(rows, 1):
        time.sleep(delay)
        print("[%d/%d] %s" % (i, len(rows), row["profile_url"]), file=sys.stderr)
        ok, why = gate.allows(row["profile_url"])
        if not ok:
            fail("robots.txt refuses %s: %s" % (row["profile_url"], why))
        page = session.get(row["profile_url"], timeout=timeout)
        page.raise_for_status()
        row["bio"] = parse_bio(page.text, row["profile_url"])

    return {
        "source": INDEX_URL,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "office": parse_office(index_html),
        "records": rows,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--out", default="cps_board.json")
    ap.add_argument("--delay", type=float, default=0.5,
                    help="seconds between requests (raised to any stated Crawl-delay)")
    args = ap.parse_args()

    payload = scrape(delay=args.delay)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    seated = sum(1 for r in payload["records"] if r["district"])
    mails = sum(1 for r in payload["records"] if r["bio"].get("email"))
    print("cps-board-scraper: %d members -> %s (%d with a district, %d with an "
          "e-mail; office %s)"
          % (len(payload["records"]), args.out, seated, mails,
             "read" if payload["office"] else "NOT FOUND"), file=sys.stderr)


if __name__ == "__main__":
    main()
