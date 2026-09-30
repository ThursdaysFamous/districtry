#!/usr/bin/env python3
"""
Scrape the Stark County Board roster from the county's Elected Officials page.

The page is a category-grouped staff directory, and the county board occupies
the first two categories on it. Each person is one `amsd-item` block:

    <h3 class="amsd-title-text-link category">District 1</h3>
    ...
    <a class="amsd-title-text-link name">Kari Bush</a>
    <p class="amsd-meta-text">Board Chair</p>
    <a href="mailto: boarddist1-4@starkco.illinois.gov">...</a>
    <p class="amsd-description-text grid">Term ending November 2028</p>

so the parse is genuinely structural rather than a guess at layout, which is a
pleasant change from most counties this size.

TWO THINGS THIS SCRAPER IS CAREFUL ABOUT
----------------------------------------
1. IT ONLY READS THE TWO DISTRICT CATEGORIES. The same page also lists the
   Circuit Clerk, County Clerk and Recorder, Sheriff, State's Attorney and
   Treasurer under their own category headings. Those are county officers, not
   board members, and a scraper that swept every `amsd-item` on the page would
   silently file five of them as board members. We walk category by category and
   take only the ones matching DISTRICT_HEADING_RE.

2. `mailto:` ON THIS SITE CARRIES A LEADING SPACE — `href="mailto: boarddist1-4@…"`.
   Unstripped, every e-mail ships with a space in it and every mail link on the
   card is broken. It is the kind of thing that works in a browser and fails in
   data.

The per-seat addresses are worth noting: Stark gives each of its eight seats a
positional mailbox (`boarddist1-1` … `boarddist2-4`) rather than a personal one,
so these survive turnover and are the right thing to publish.

Usage:
    python3 scripts/stark_county_board_scraper.py --out stark_board_raw.json
"""

import argparse
import datetime
import json
import re
import sys
from scraper_common import require_robots_once, UA_CIVIC_BOT  # noqa: E402  (shared machinery — do not fork)

try:
    import requests
except ImportError:  # pragma: no cover
    sys.exit("requests is required: pip install -c scripts/requirements.txt requests")

SOURCE_URL = "https://starkco.illinois.gov/government/elected-officials-and-staff"
COUNTY_PAGE = "https://starkco.illinois.gov/"
TIMEOUT = 45
USER_AGENT = UA_CIVIC_BOT

# Eight seats, four per district. Floors sit two under the full board so a
# genuine vacancy does not fail the run, but a parse regression does.
MIN_MEMBERS = 6
EXPECTED_DISTRICTS = ("1", "2")
SEATS_PER_DISTRICT = 4

CATEGORY_RE = re.compile(
    r'(?is)<h3[^>]*class="[^"]*\bcategory\b[^"]*"[^>]*>(.*?)</h3>')
DISTRICT_HEADING_RE = re.compile(r"(?i)^\s*District\s+(\d+)\s*$")
ITEM_RE = re.compile(r'(?is)<div[^>]*class="[^"]*\bamsd-item\b[^"]*"[^>]*>(.*?)'
                     r'(?=<div[^>]*class="[^"]*\bamsd-item\b|\Z)')
NAME_RE = re.compile(r'(?is)<a[^>]*class="[^"]*\bname\b[^"]*"[^>]*>(.*?)</a>')
ROLE_RE = re.compile(r'(?is)<p[^>]*class="amsd-meta-text"[^>]*>(.*?)</p>')
# NOTE the `\s*` after mailto: — this site emits `mailto: someone@example.gov`
MAILTO_RE = re.compile(r'(?is)href="mailto:\s*([^"]+)"')
TERM_RE = re.compile(r'(?is)<p[^>]*class="[^"]*\bamsd-description-text\b[^"]*"'
                     r'[^>]*>(.*?)</p>')
TERM_TEXT_RE = re.compile(r"(?i)Term\s+end(?:ing|s)?\s+(.+)$")
PHONE_RE = re.compile(r"(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})")


def text(fragment):
    """Tags out, entities in, whitespace collapsed."""
    if not fragment:
        return ""
    out = re.sub(r"(?is)<[^>]+>", " ", fragment)
    for entity, char in (("&amp;", "&"), ("&nbsp;", " "), ("&#39;", "'"),
                         ("&rsquo;", "’"), ("&quot;", '"'), ("&lt;", "<"),
                         ("&gt;", ">")):
        out = out.replace(entity, char)
    return re.sub(r"\s+", " ", out).strip()


def district_sections(html):
    """Slice the page into (district, html) for the District N categories only.

    Everything after the last district heading up to the NEXT category heading
    belongs to that district; the county-officer categories that follow are
    dropped here rather than filtered later, so they can never reach a member row.
    """
    marks = [(m.start(), m.end(), text(m.group(1)))
             for m in CATEGORY_RE.finditer(html)]
    sections = []
    for index, (start, end, heading) in enumerate(marks):
        match = DISTRICT_HEADING_RE.match(heading)
        if not match:
            continue
        stop = marks[index + 1][0] if index + 1 < len(marks) else len(html)
        sections.append((match.group(1), html[end:stop]))
    return sections


def parse_member(district, block):
    name = text(NAME_RE.search(block).group(1)) if NAME_RE.search(block) else ""
    if not name:
        return None

    role = ""
    role_match = ROLE_RE.search(block)
    if role_match:
        candidate = text(role_match.group(1))
        # the meta paragraph is also where a phone would sit if one existed
        if candidate and not PHONE_RE.fullmatch(candidate):
            role = candidate

    email = ""
    mail_match = MAILTO_RE.search(block)
    if mail_match:
        email = text(mail_match.group(1)).replace(" ", "")

    term = ""
    term_match = TERM_RE.search(block)
    if term_match:
        term_text = text(term_match.group(1))
        inner = TERM_TEXT_RE.search(term_text)
        term = inner.group(1).strip() if inner else term_text

    phone = ""
    phone_match = PHONE_RE.search(text(block))
    if phone_match:
        phone = phone_match.group(1).strip()

    return {"name": name, "district": district, "role": role, "email": email,
            "phone": phone, "term_expires": term}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="stark_board_raw.json")
    parser.add_argument("--html", help="parse a saved copy instead of fetching")
    args = parser.parse_args()

    if args.html:
        with open(args.html, encoding="utf-8") as handle:
            html = handle.read()
    else:
        require_robots_once(SOURCE_URL, USER_AGENT, headers={"User-Agent": USER_AGENT},
                            label="il-stark-county-board-scraper")
        response = requests.get(SOURCE_URL, timeout=TIMEOUT,
                                headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        html = response.text

    members = []
    per_district = {}
    for district, section in district_sections(html):
        for block in ITEM_RE.findall(section):
            member = parse_member(district, block)
            if member:
                members.append(member)
                per_district[district] = per_district.get(district, 0) + 1

    problems = []
    if len(members) < MIN_MEMBERS:
        problems.append("%d members < floor %d" % (len(members), MIN_MEMBERS))
    missing = [d for d in EXPECTED_DISTRICTS if d not in per_district]
    if missing:
        problems.append("no members found for district(s) %s" % ", ".join(missing))
    for district, count in sorted(per_district.items()):
        if count > SEATS_PER_DISTRICT:
            problems.append("district %s has %d members but the board seats %d "
                            "per district — a non-board category was probably "
                            "swept in" % (district, count, SEATS_PER_DISTRICT))
    # Every seat on this board has a positional mailbox. A member without one
    # means the mailto parse moved, which is exactly what the leading space in
    # `mailto: ` invites.
    without_email = [m["name"] for m in members if not m["email"]]
    if without_email:
        problems.append("%d member(s) carry no e-mail (%s) — every Stark seat "
                        "has a positional mailbox, so this is a parse failure"
                        % (len(without_email), ", ".join(without_email)))

    if problems:
        for problem in problems:
            print("  FAIL: %s" % problem, file=sys.stderr)
        print("FATAL: refusing to write a payload that lost coverage",
              file=sys.stderr)
        sys.exit(1)

    payload = {
        "county": "Stark",
        "source_url": SOURCE_URL,
        "county_page": COUNTY_PAGE,
        "scraped_at": datetime.datetime.now(datetime.timezone.utc)
                              .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "members": members,
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print("scraped %d members across %d districts (%s), %d with e-mail, "
          "%d with a term end, %d role-tagged -> %s"
          % (len(members), len(per_district),
             ", ".join("D%s=%d" % (d, per_district[d])
                       for d in sorted(per_district, key=int)),
             sum(1 for m in members if m["email"]),
             sum(1 for m in members if m["term_expires"]),
             sum(1 for m in members if m["role"]), args.out),
          file=sys.stderr)


if __name__ == "__main__":
    main()
