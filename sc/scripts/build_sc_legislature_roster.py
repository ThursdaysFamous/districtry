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
({district -> {name, party, url, capitolOffice, phone?, phonesExtra?}}). A
weekly GitHub Action
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

THE MEMBER PAGE ALSO PRINTS A HOME ADDRESS AND, UNDER IT, A HOME AND A
BUSINESS TELEPHONE. THE TELEPHONES ARE READ AND THE ADDRESS NEVER IS. Until
2026-10-17 neither was read, on the reasoning that a home telephone is
personal; that day Adam ruled for the whole fleet, "if the official government
source uses personal phone numbers, we publish those", and the General
Assembly prints these on each member's own page. The ruling covers telephone
numbers, so the home address is still never parsed, written or printed. Each
block is read by its own heading: the Columbia business phone stays in the
Capitol office block as before, and a member whose Columbia block carries no
business phone gets none there rather than whatever number comes next on the
page. In the Home Address block only the rows labelled "... Phone" are read,
each carried with the page's own label ("home (843) 665-7321", "business (864)
638-4237") so a reader can tell the two apart; the first is the member's
`phone` and any second is in `phonesExtra`. Measured on 2026-10-17 across all
170 pages: 164 print a Home Address block, 93 of those print a telephone
under it, 61 labelled "Home Phone" and 61 "Business Phone", and no other
label. Three numbers are not carried on a member's row: one equal to the
member's own Columbia business phone, which the Capitol office already shows
(two members); a second copy of a number the block prints twice, once as home
and once as business (two members, carried once with the first label); and a
number the pages print for two or more members, because a number two
legislators share is an office's and not either member's own (two numbers that
day, each printed for one senator and one representative from the same
county, which is what a county legislative delegation office looks like).

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
# A floor on the members' own numbers from the Home Address block, across both
# chambers: 91 of 170 carried one on 2026-10-17. A parse that stops finding
# them has broken; members do not take a third of them down in a year.
MIN_OWN_PHONES = 60

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
# The member page's "Home Address" block, read for its telephone rows only
# (see the module docstring): a row is a bold label and the text after it.
HOME_BLOCK_RE = re.compile(
    r'<h2[^>]*>\s*Home Address\s*</h2>(.*?)</div>', re.S | re.I)
BLOCK_ROW_RE = re.compile(r'<span[^>]*>\s*([^<]*?)\s*</span>\s*([^<]*)', re.I)
PHONE_LABEL_RE = re.compile(r'^(.*?)\s*Phone$', re.I)
PHONE_SHAPE_RE = re.compile(
    r'^\(?\d{3}\)?[\s.-]*\d{3}[\s.-]\d{4}(?:\s*(?:x|ext\.?)\s*\d{1,6})?$', re.I)
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


def digits(number):
    return re.sub(r"\D", "", number)


def home_phones(page, where):
    """[(label, number)] from the Home Address block's telephone rows.

    The block's address paragraph is never read; see the module docstring.
    A row labelled anything but "... Phone" is not read and the run says so,
    so a new field is seen rather than carried."""
    block = HOME_BLOCK_RE.search(page)
    if not block:
        return []
    phones = []
    for label, value in BLOCK_ROW_RE.findall(block.group(1)):
        label, value = clean(label), clean(value)
        m = PHONE_LABEL_RE.match(label)
        if not m:
            print("NOTE: %s: a Home Address row labelled %r was not read"
                  % (where, label), file=sys.stderr)
            continue
        if not PHONE_SHAPE_RE.match(value):
            raise SystemExit("FAIL: %s: the Home Address row %r holds %r, which is "
                             "not a telephone number" % (where, label, value))
        phones.append((m.group(1).strip().lower(), value))
    return phones


def parse_member_page(page, where):
    """(district, title_line, columbia_lines, business_phone, home_phones) from
    a member page.

    Reads the Columbia Address block, and the Home Address block's telephone
    rows only; see the module docstring."""
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
    return (d.group(1) if d else None, clean(t.group(1)) if t else None, lines, phone,
            home_phones(page, where))


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
        page_district, page_title, lines, phone, home = parse_member_page(
            mpage, "%s District %s" % (cfg["label"], district))
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
        # The member's own numbers, settled in main() once both chambers are
        # read, because a number shared across the two is an office's.
        own, seen = [], {digits(phone)} if phone else set()
        for label, number in home:
            if digits(number) in seen:
                continue
            seen.add(digits(number))
            own.append((label, number))
        member["_home"] = own
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

    # A number printed for two or more members, in either chamber, is an
    # office's, and ships on no member's row.
    holders = {}
    for chamber, (roster, _, _) in built.items():
        for district, member in roster.items():
            for _, number in member["_home"]:
                holders.setdefault(digits(number), []).append(
                    "%s %s" % (CHAMBERS[chamber]["label"], district))
    shared = {d: who for d, who in holders.items() if len(who) > 1}
    for d, who in sorted(shared.items()):
        print("NOTE: a Home Address number is printed for %s, so it is an office's "
              "and ships on neither member's row" % " and ".join(who), file=sys.stderr)
    own_phones = 0
    for chamber, (roster, _, _) in built.items():
        for member in roster.values():
            numbers = ["%s %s" % (label, number) if label else number
                       for label, number in member.pop("_home")
                       if digits(number) not in shared]
            if numbers:
                member["phone"] = numbers[0]
                own_phones += 1
            if len(numbers) > 1:
                member["phonesExtra"] = numbers[1:]
    if own_phones < MIN_OWN_PHONES:
        print("FAIL: only %d members carry a number from their Home Address block "
              "(expected >= %d) — the page layout changed" % (own_phones, MIN_OWN_PHONES),
              file=sys.stderr)
        sys.exit(1)

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
        print("Wrote %s (%d of %d districts, %d with an office, %d with a telephone, "
              "%d with a number of their own; no member listed for: %s)"
              % (out_path, len(roster), cfg["seats"], offices, phones,
                 sum(1 for m in roster.values() if m.get("phone")),
                 ", ".join(missing) or "none"),
              file=sys.stderr)


if __name__ == "__main__":
    main()
