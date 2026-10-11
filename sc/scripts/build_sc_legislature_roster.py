#!/usr/bin/env python3
"""
Build the South Carolina Senate and South Carolina House rosters (district ->
current officeholder) as same-origin app-data files, from the General
Assembly's OWN member pages, so the sc-senate / sc-house cards join a small
roster instead of reaching a third-party host at click time.

index.html's sc-senate / sc-house layers fetch data/app/sc-senate-members.json
and sc-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script reads the two chamber
lists on www.scstatehouse.gov and each member's own page, and writes the two
rosters, shaped for the registerIlgaChamber factory
({district -> {name, party, url, capitolOffice}}). A weekly GitHub Action
(.github/workflows/update-sc-legislature-roster.yml) reruns this and opens a PR
when a roster changes, so officeholder data gets a human look before it ships.

WHY THE LEGISLATURE AND NOT OPEN STATES. Oklahoma's and North Carolina's
arrivals took names from the Open States export; this one takes them from the
government that keeps them, which is the fleet's rule for people ("from
whatever the government keeps up to date as people"). The state's own map
service also carries legislators' names, and the planning pass on 2026-10-09
found 3 of 170 of those out of date against the legislature's own list, so the
map is used for nothing but lines.

WHAT THE PAGES CARRY, MEASURED 2026-10-10. One list per chamber
(member.php?chamber=S, ?chamber=H): 46 senators and 124 representatives, one
entry per district with no gaps and no duplicates, each with the district
number, the member's own page, the name with a title prefix ("Senator",
"Representative"), the party as one letter in parentheses (Senate 34 R / 12 D,
House 89 R / 35 D) and the State House office on one line. The list carries an
empty phone element for every member; the TELEPHONE is on each member's own
page, under "Columbia Address" as "Business Phone", so this script reads all
170 member pages too.

THE MEMBER PAGE ALSO PRINTS A HOME ADDRESS AND A HOME TELEPHONE, AND THIS
SCRIPT NEVER READS THEM. The parse is confined to the block headed "Columbia
Address", which ends where the next block starts; a member whose Columbia block
carries no business phone gets no phone rather than whatever number comes
next on the page. A legislator's home is no part of answering who represents
you, and a parser that took "the first phone on the page" would publish one.

NO E-MAIL. The General Assembly publishes no e-mail address for any member,
only a message form on the member's page ("Send message to ..."), so the card
links the member's page and carries no e-mail.

ROBOTS. www.scstatehouse.gov's robots.txt (176 bytes, read 2026-10-10)
disallows /images/, /jpeg/, /gif/, /dashboard/ and /sys/ under its `*` group,
names two other crawlers it shuts out entirely, and states no Crawl-delay.
/member.php is allowed. It is read before the first fetch through
scraper_common.require_robots_once, with the same User-Agent the fetches send,
and the member pages are paced at one request a second anyway.

Honesty: names are never guessed. A district the list does not fill simply
doesn't appear in its roster, and the card falls back to "district number +
chamber directory" — the factory's empty-member path.

Usage:
    python3 sc/scripts/build_sc_legislature_roster.py [output_dir]
    python3 sc/scripts/build_sc_legislature_roster.py --offline DIR [output_dir]

--offline reads saved pages from DIR (S.html, H.html and m<code>.html for each
member) instead of fetching, for building and testing without the network.
"""

import html as html_module
import json
import os
import re
import sys
import time
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

USER_AGENT = "districtry/1.0 (+https://districtry.com/sc/)"
BASE = "https://www.scstatehouse.gov"
LIST_URL = BASE + "/member.php?chamber=%s"
MEMBER_URL = BASE + "/member.php?code=%s"
PACE_SECONDS = 1.0

# Floors catch a truncated page or a layout change while tolerating real
# vacancies: both chambers listed every seat on 2026-10-10.
CHAMBERS = {
    "S": {"out": "sc-senate-members.json", "label": "Senate", "title": "Senator",
          "expected": 42, "seats": 46},
    "H": {"out": "sc-house-members.json", "label": "House", "title": "Representative",
          "expected": 114, "seats": 124},
}
# Floors on the two contact fields, measured at 46 of 46 and 124 of 124 for
# the office and the telephone alike. A field every row carries going missing
# is the Brown County shape: the row count holds and the contact goes.
MIN_OFFICE_SHARE = 0.9
MIN_PHONE_SHARE = 0.9

# The list prints the party as one letter. Anything else ships as the
# publisher printed it, and the run says so, rather than being guessed at.
PARTY_NAMES = {"R": "Republican", "D": "Democratic"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

# One member's entry on a chamber list. Splitting on the outline div keeps a
# member's district, name, party and office together, which a flat regex over
# the page would not.
ENTRY_SPLIT = '<div class="memberOutline">'
DISTRICT_RE = re.compile(
    r'<div class="district"><h1><a href="/member\.php\?code=(\d+)">District (\d+)</a>')
NAME_RE = re.compile(
    r'class="membername" href="/member\.php\?code=(\d+)">([^<]+)</a>\s*\(([^)]*)\)')
OFFICE_RE = re.compile(r'<div id="address">([^<]*)</div>')

# The member page's "Columbia Address" block, up to the block that follows it
# (the Home Address block is the next sibling on every page read 2026-10-10).
COLUMBIA_BLOCK_RE = re.compile(
    r'<h2[^>]*>\s*Columbia Address\s*</h2>(.*?)</div>', re.S | re.I)
BLOCK_ADDRESS_RE = re.compile(r'<p[^>]*>(.*?)</p>', re.S)
BUSINESS_PHONE_RE = re.compile(
    r'<span[^>]*>\s*Business Phone\s*</span>\s*([^<]+)', re.I)
PAGE_DISTRICT_RE = re.compile(r'>District (\d+) -')
PAGE_TITLE_RE = re.compile(r'<h2 class="barheader">(?:&nbsp;|\s)*([^<]+)</h2>')


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def clean(text):
    return re.sub(r"\s+", " ", html_module.unescape(text or "")).strip()


def strip_title(name, title):
    name = clean(name)
    if name.startswith(title + " "):
        name = name[len(title) + 1:]
    return name


def parse_list(page, chamber):
    """[(district, code, name, party_letter, office_line)] from a chamber list."""
    cfg = CHAMBERS[chamber]
    rows = []
    for block in page.split(ENTRY_SPLIT)[1:]:
        d = DISTRICT_RE.search(block)
        n = NAME_RE.search(block)
        if not d or not n:
            raise SystemExit("FAIL: a %s list entry carries no district or no name — the "
                             "page layout changed" % cfg["label"])
        if d.group(1) != n.group(1):
            raise SystemExit("FAIL: %s District %s links one member page and names "
                             "another" % (cfg["label"], d.group(2)))
        o = OFFICE_RE.search(block)
        rows.append((d.group(2), d.group(1), strip_title(n.group(2), cfg["title"]),
                     clean(n.group(3)), clean(o.group(1)) if o else ""))
    return rows


def parse_member_page(page):
    """(district, title_line, columbia_lines, business_phone) from a member page.

    Reads ONLY the Columbia Address block; see the module docstring."""
    d = PAGE_DISTRICT_RE.search(page)
    t = PAGE_TITLE_RE.search(page)
    block = COLUMBIA_BLOCK_RE.search(page)
    lines, phone = [], None
    if block:
        body = block.group(1)
        paras = BLOCK_ADDRESS_RE.findall(body)
        if paras:
            lines = [clean(x) for x in re.split(r"<br\s*/?>", paras[0]) if clean(x)]
        p = BUSINESS_PHONE_RE.search(body)
        if p and clean(p.group(1)):
            phone = clean(p.group(1))
    return (d.group(1) if d else None, clean(t.group(1)) if t else None, lines, phone)


def surname(name):
    parts = [p for p in re.split(r"[\s,]+", name) if p]
    while parts and parts[-1].rstrip(".").lower() in ("jr", "sr", "ii", "iii", "iv"):
        parts.pop()
    return parts[-1].lower() if parts else ""


def build_chamber(chamber, offline):
    cfg = CHAMBERS[chamber]
    page = (open(os.path.join(offline, chamber + ".html"), encoding="utf-8").read()
            if offline else fetch(LIST_URL % chamber))
    rows = parse_list(page, chamber)
    roster, odd_parties = {}, []
    for district, code, name, party, office in rows:
        if not district.isdigit() or not 1 <= int(district) <= cfg["seats"]:
            raise SystemExit("FAIL: %s district %r is not one of the state's %d"
                             % (cfg["label"], district, cfg["seats"]))
        if district in roster:
            raise SystemExit("FAIL: %s district %s carries two members (%r and %r)"
                             % (cfg["label"], district, roster[district]["name"], name))
        if offline:
            mpath = os.path.join(offline, "m%s.html" % code)
            mpage = open(mpath, encoding="utf-8").read() if os.path.exists(mpath) else ""
        else:
            time.sleep(PACE_SECONDS)
            mpage = fetch(MEMBER_URL % code)
        page_district, page_title, lines, phone = parse_member_page(mpage)
        if mpage:
            # The member's own page must agree with the list about who this is
            # and which seat they hold, or the two pages describe different
            # people and nothing from either ships.
            if page_district != district:
                raise SystemExit("FAIL: %s list puts %s in District %s and their own page "
                                 "says %r" % (cfg["label"], name, district, page_district))
            if not page_title or surname(strip_title(page_title, cfg["title"])) != surname(name):
                raise SystemExit("FAIL: %s District %s: the list names %r and the member "
                                 "page %r" % (cfg["label"], district, name, page_title))
        member = {"name": name}
        if party in PARTY_NAMES:
            member["party"] = PARTY_NAMES[party]
        elif party:
            member["party"] = party
            odd_parties.append("%s %s (%s)" % (cfg["label"], district, party))
        member["url"] = MEMBER_URL % code
        office_lines = lines or ([office] if office else [])
        if office_lines or phone:
            member["capitolOffice"] = office_lines + (["Phone: " + phone] if phone else [])
        roster[district] = member
    if odd_parties:
        print("NOTE: party shipped as printed, not in PARTY_NAMES: %s"
              % "; ".join(odd_parties), file=sys.stderr)
    return {d: roster[d] for d in sorted(roster, key=int)}


def main():
    args = sys.argv[1:]
    offline = None
    if args and args[0] == "--offline":
        if len(args) < 2:
            print("usage: %s --offline DIR [output_dir]" % sys.argv[0], file=sys.stderr)
            sys.exit(1)
        offline = args[1]
        args = args[2:]
    if len(args) > 1:
        print("usage: %s [--offline DIR] [output_dir]" % sys.argv[0], file=sys.stderr)
        sys.exit(1)
    out_dir = args[0] if args else DEFAULT_OUT_DIR

    if not offline:
        require_robots_once(LIST_URL % "S", USER_AGENT,
                            label="sc-build-sc-legislature-roster")
    built = {}
    for chamber, cfg in CHAMBERS.items():
        roster = build_chamber(chamber, offline)
        if len(roster) < cfg["expected"]:
            print("FAIL: resolved %d %s districts (expected >= %d) — refusing to "
                  "overwrite the roster with an incomplete chamber"
                  % (len(roster), cfg["label"], cfg["expected"]), file=sys.stderr)
            sys.exit(1)
        offices = sum(1 for m in roster.values()
                      if any(not l.startswith("Phone: ") for l in m.get("capitolOffice", [])))
        phones = sum(1 for m in roster.values()
                     if any(l.startswith("Phone: ") for l in m.get("capitolOffice", [])))
        for what, n, share in (("a State House office", offices, MIN_OFFICE_SHARE),
                               ("a business telephone", phones, MIN_PHONE_SHARE)):
            if n < share * len(roster):
                print("FAIL: only %d of %d %s seats carry %s — the page stopped "
                      "publishing a field it has carried on every member"
                      % (n, len(roster), cfg["label"], what), file=sys.stderr)
                sys.exit(1)
        built[chamber] = (roster, offices, phones)

    # Write only once BOTH chambers have passed every guard, so a failure in
    # the House cannot leave a fresh Senate file beside a stale House one.
    os.makedirs(out_dir, exist_ok=True)
    for chamber, (roster, offices, phones) in built.items():
        cfg = CHAMBERS[chamber]
        missing = [str(d) for d in range(1, cfg["seats"] + 1) if str(d) not in roster]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("Wrote %s (%d of %d districts, %d with an office, %d with a telephone; "
              "no member listed for: %s)" % (out_path, len(roster), cfg["seats"], offices,
                                             phones, ", ".join(missing) or "none"),
              file=sys.stderr)


if __name__ == "__main__":
    main()
