#!/usr/bin/env python3
"""
Build the Arkansas Senate and Arkansas House rosters (district -> current
officeholder) as same-origin app-data files, from the Arkansas State
Legislature's OWN member pages, so the ar-senate / ar-house cards join a small
roster instead of reaching a third-party host at click time.

index.html's ar-senate / ar-house layers fetch data/app/ar-senate-members.json
and ar-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script reads the legislature's
one member list on www.arkleg.state.ar.us and each member's own page, and writes
the two rosters, shaped for the registerIlgaChamber factory
({district -> {name, party, email, url}}, or a vacancy record). A weekly GitHub
Action (.github/workflows/update-ar-legislature-roster.yml) reruns this and
opens a PR when a roster changes, so officeholder data gets a human look before
it ships.

WHY THE LEGISLATURE AND NOT OPEN STATES. The fleet's rule for people is to take
them from whatever the government keeps up to date as people. The Bureau of
Legislative Research publishes every member of the 95th General Assembly at
/Legislators/List, one page for both chambers, and a page per member.

WHAT THE PAGES CARRY, MEASURED 2026-10-13. The list holds 138 rows for 135
seats: 102 representatives and 36 senators, each with a title ("Representative",
"Senator"), the member's page, the name, the chamber and the district, and 131
of the 138 with an e-mail address. A member who has left keeps their row. Their own page
prints the reason in bold under the name — "Deceased" or "Resigned" — and the
list itself says nothing. That is how three districts carry two rows (House 44,
where Stan Berry is marked deceased and Bill Teeter holds the seat; House 70,
Carlton Wing resigned and Alex B. Holladay holds it; Senate 26, Gary Stubblefield
deceased and Brad Simon holds it) and three carry one row whose member has gone
(Senate 1, Ben Gilmore resigned; Senate 18, Jonathan Dismang resigned; House 8,
Austin McCollum resigned). So every member page is read: the list cannot tell
a sitting member from a former one.

THE PARTY IS ON THE MEMBER PAGE, not the list: the page's heading reads
"Senator Brad Simon (R)". Measured 2026-10-13: House 82 R / 20 D, Senate 30 R /
6 D across all 138 rows, former members included.

THE MEMBER PAGE ALSO PRINTS A MAILING ADDRESS AND A TELEPHONE. THE TELEPHONE
IS READ AND THE ADDRESS IS NOT. On a senator's page the bold line under the
name is that address — a post office box for most, a street address for some
("3 Great Oak Court, North Little Rock"), which may be a home — and a legislator's
home is no part of answering who represents you, so it is never read. The
"Phone:" row is unlabelled as to whose line it is, and for many members it is
plainly the member's own; it was not read either until Adam ruled on
2026-10-17, for the whole fleet, that "if the official government source uses
personal phone numbers, we publish those." The legislature's page is that
source, so the number ships on the member's row exactly as the page prints it.
A number two or more members share is not any one member's line and ships on
none of their rows, a link that dials a different number from the one it shows
ships neither, and a value that is not a telephone number stops the build.
Measured 2026-10-17: 101 of the 138 pages print a Phone row, and 97 of the 132
sitting members ship a number. A bold line that is
neither a known status word nor an address (it carries no digit) stops the
build rather than being guessed at.

THE E-MAIL IS THE LIST'S, which the legislature prints as each member's contact
on every row. Most are on the chambers' own domains; a few are personal
addresses the member gave the legislature, and those ship as published.

ROBOTS. www.arkleg.state.ar.us's robots.txt (97 bytes with a byte-order mark,
read 2026-10-13) is `User-agent: *` / `Allow: /` plus two groups refusing
ChatGPT's crawlers, which do not name this client. No Crawl-delay is stated.
It is read before the first fetch through scraper_common.require_robots_once,
with the same User-Agent the fetches send, and the member pages are paced at
two seconds anyway. The host reset the connection on about one request in five
on 2026-10-13, so each fetch is retried.

Honesty: names are never guessed. A district whose only member has left gets a
vacancy record naming the page that says so; it never inherits the departed
member's name.

Usage:
    python3 ar/scripts/build_ar_legislature_roster.py [output_dir]
    python3 ar/scripts/build_ar_legislature_roster.py --offline DIR [output_dir]

--offline reads saved pages from DIR (list.html, and detail/<member>.html for
each member, named by the page's own member= value) instead of fetching, for
building and testing without the network.
"""

import datetime
import html as html_module
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

USER_AGENT = "districtry/1.0 (+https://districtry.com/ar/)"
BASE = "https://www.arkleg.state.ar.us"
LIST_URL = BASE + "/Legislators/List"
PACE_SECONDS = 2.0
ATTEMPTS = 3
RETRY_SECONDS = 5.0

# Floors catch a truncated page or a layout change while tolerating real
# vacancies: 34 of 35 senators and 99 of 100 representatives were named on
# 2026-10-13 once the departed members were set aside.
CHAMBERS = {
    "Senate": {"out": "ar-senate-members.json", "label": "Senate",
               "title": "Senator", "expected": 30, "seats": 35},
    "House": {"out": "ar-house-members.json", "label": "House",
              "title": "Representative", "expected": 90, "seats": 100},
}
# Every row carried an e-mail on 2026-10-13. A field every row carries going
# missing is the Brown County shape: the row count holds and the contact goes.
MIN_EMAIL_SHARE = 0.9
# A floor on the members' Phone rows: 29 of 33 senators and 68 of 99
# representatives shipped one on 2026-10-17. A parse that stops finding them
# has broken; a chamber does not lose half its numbers in a year.
MIN_PHONE_SHARE = 0.5

# The member page's own words for a member who has left. Anything else in that
# bold line without a digit stops the build.
STATUS_WORDS = {"Deceased": "deceased", "Resigned": "resigned"}

# The heading prints the party as one letter. Anything else ships as printed,
# and the run says so, rather than being guessed at.
PARTY_NAMES = {"R": "Republican", "D": "Democratic"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

ROW_SPLIT = re.compile(r'<div class="row tableRow(?:Alt)?"[^>]*role="row"')
ROW_LINK_RE = re.compile(
    r'(Representative|Senator)\s*<a href="(/Legislators/Detail\?member=[^"]+)">([^<]+)</a>')
ROW_EMAIL_RE = re.compile(r'href="mailto:([^"]+)"')
ROW_CHAMBER_RE = re.compile(r'Chamber:</span>\s*(House|Senate)\s*<')
ROW_DISTRICT_RE = re.compile(r'District:</span>\s*(\d+)\s*<')

PAGE_HEADING_RE = re.compile(
    r'<h1>\s*(Senator|Representative)\s+(.+?)\s*\(([^)]*)\)\s*</h1>')
PAGE_BOLD_RE = re.compile(r'</h1>\s*<p>\s*<b>([^<]*)</b>\s*</p>')
PAGE_DISTRICT_RE = re.compile(r'<b>District:</b>\s*(\d+)')
# The "Phone:" row. The page prints each row twice, once for a phone-sized
# screen with the number after the label, as a tel: link, and once for a wide
# one with the label alone in its own cell; the first copy that carries text is
# read. Only the link's own text is read, so nothing beside the number can ride
# along, and the link's dialled digits must be the same number.
PAGE_PHONE_RE = re.compile(r'<b>Phone:</b>\s*(?:<a\b([^>]*)>)?([^<]*)')
TEL_HREF_RE = re.compile(r'href="tel:([^"]*)"')
# Ten digits in the shapes the pages use, "(870) 818-7067" and "501-804-7844",
# with an optional extension. Anything else in that row stops the build.
PHONE_SHAPE_RE = re.compile(
    r'^\(?\d{3}\)?[\s.-]*\d{3}[\s.-]\d{4}(?:\s*(?:x|ext\.?)\s*\d{1,6})?$', re.I)


def fetch(url):
    last = None
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_SECONDS * attempt)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (OSError, urllib.error.URLError) as exc:  # reset, timeout
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (url, ATTEMPTS, last))


def clean(text):
    return re.sub(r"\s+", " ", html_module.unescape(text or "")).strip()


def member_key(href):
    """The page's own member= value ("F.+Allen"), which names the saved file."""
    query = urllib.parse.urlsplit(html_module.unescape(href)).query
    for part in query.split("&"):
        if part.startswith("member="):
            return part[len("member="):]
    raise SystemExit("FAIL: a list link carries no member= value: %r" % href)


def parse_list(page):
    """[(chamber, district, href, name, email)] from the member list."""
    rows = []
    for block in ROW_SPLIT.split(page)[1:]:
        link = ROW_LINK_RE.search(block)
        chamber = ROW_CHAMBER_RE.search(block)
        district = ROW_DISTRICT_RE.search(block)
        if not link or not chamber or not district:
            raise SystemExit("FAIL: a list row carries no member link, chamber or "
                             "district — the page layout changed")
        title = CHAMBERS[chamber.group(1)]["title"]
        if link.group(1) != title:
            raise SystemExit("FAIL: %s is listed in the %s as a %s"
                             % (clean(link.group(3)), chamber.group(1), link.group(1)))
        email = ROW_EMAIL_RE.search(block)
        rows.append((chamber.group(1), district.group(1),
                     html_module.unescape(link.group(2)), clean(link.group(3)),
                     clean(email.group(1)) if email else None))
    return rows


def parse_member_page(page, who):
    """(title, name, party_letter, status_or_None, district, phone_or_None)
    from a member page.

    Reads the heading, the bold line under it, the District row and the Phone
    row only; see the module docstring."""
    heading = PAGE_HEADING_RE.search(page)
    district = PAGE_DISTRICT_RE.search(page)
    if not heading or not district:
        raise SystemExit("FAIL: %s's member page carries no heading or no District "
                         "row — the page layout changed" % who)
    status = None
    bold = PAGE_BOLD_RE.search(page)
    if bold:
        text = clean(bold.group(1))
        if text in STATUS_WORDS:
            status = STATUS_WORDS[text]
        elif text and not re.search(r"\d", text):
            raise SystemExit("FAIL: %s's member page prints %r under the name, which "
                             "is neither a known status nor an address — add it to "
                             "STATUS_WORDS once its meaning is read" % (who, text))
    phone = None
    for attrs, text in PAGE_PHONE_RE.findall(page):
        text = clean(text)
        if not text:
            continue
        if not PHONE_SHAPE_RE.match(text):
            raise SystemExit("FAIL: %s's member page prints %r in its Phone row, "
                             "which is not a telephone number" % (who, text))
        href = TEL_HREF_RE.search(attrs or "")
        if href and (re.sub(r"\D", "", href.group(1)).lstrip("1")
                     != re.sub(r"\D", "", text).lstrip("1")):
            # A link that dials a different number from the one it shows is
            # not carried at all: neither number can be said to be the one the
            # page publishes.
            print("NOTE: %s's Phone row shows %r and dials %r, so neither ships"
                  % (who, text, href.group(1)), file=sys.stderr)
        else:
            phone = text
        break
    return (heading.group(1), clean(heading.group(2)), clean(heading.group(3)),
            status, district.group(1), phone)


def surname(name):
    parts = [p for p in re.split(r"[\s,]+", name) if p]
    while parts and parts[-1].rstrip(".").lower() in ("jr", "sr", "ii", "iii", "iv"):
        parts.pop()
    return parts[-1].lower() if parts else ""


def read_previous(out_dir, cfg):
    path = os.path.join(out_dir, cfg["out"])
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def build(offline, out_dir, today):
    page = (open(os.path.join(offline, "list.html"), encoding="utf-8").read()
            if offline else fetch(LIST_URL))
    rows = parse_list(page)
    seats = {chamber: {} for chamber in CHAMBERS}
    odd_parties = []
    for chamber, district, href, name, email in rows:
        cfg = CHAMBERS[chamber]
        if not 1 <= int(district) <= cfg["seats"]:
            raise SystemExit("FAIL: %s district %s is not one of the chamber's %d"
                             % (cfg["label"], district, cfg["seats"]))
        key = member_key(href)
        url = BASE + href
        if offline:
            mpage = open(os.path.join(offline, "detail", key + ".html"),
                         encoding="utf-8").read()
        else:
            time.sleep(PACE_SECONDS)
            mpage = fetch(url)
        title, page_name, party, status, page_district, phone = parse_member_page(
            mpage, name)
        # The member's own page must agree with the list about who this is and
        # which seat they hold, or the two pages describe different people and
        # nothing from either ships.
        if title != cfg["title"] or str(int(page_district)) != str(int(district)):
            raise SystemExit("FAIL: the list puts %s in %s District %s and their own "
                             "page says %s, District %s"
                             % (name, cfg["label"], district, title, page_district))
        if surname(page_name) != surname(name):
            raise SystemExit("FAIL: %s District %s: the list names %r and the member "
                             "page %r" % (cfg["label"], district, name, page_name))
        seats[chamber].setdefault(str(int(district)), []).append(
            {"name": name, "party": party, "email": email, "url": url,
             "status": status, "phone": phone})
        if party and party not in PARTY_NAMES:
            odd_parties.append("%s %s (%s)" % (cfg["label"], district, party))

    # A NUMBER TWO SITTING MEMBERS SHARE IS NOT EITHER MEMBER'S LINE. Counted
    # across both chambers, on every digit including an extension, so two
    # extensions of one office stay two numbers while one number printed for
    # two or more members ships on none of their rows, rather than reading as
    # each one's own. On 2026-10-17 one was: 501-682-6107, a state government
    # exchange, printed for four members.
    def digits(phone):
        return re.sub(r"\D", "", phone)
    holders = {}
    for listed_by_district in seats.values():
        for listed in listed_by_district.values():
            for m in listed:
                if m["phone"] and not m["status"]:
                    holders.setdefault(digits(m["phone"]), []).append(m["name"])
    shared = {d: names for d, names in holders.items() if len(names) > 1}
    for d, names in sorted(shared.items()):
        print("NOTE: one telephone number is printed for %s, so it ships on "
              "none of their rows" % ", ".join(names), file=sys.stderr)

    built = {}
    for chamber, cfg in CHAMBERS.items():
        previous = read_previous(out_dir, cfg)
        roster, notes = {}, []
        for d in range(1, cfg["seats"] + 1):
            key = str(d)
            listed = seats[chamber].get(key, [])
            sitting = [m for m in listed if not m["status"]]
            if len(sitting) > 1:
                raise SystemExit("FAIL: %s District %s has two sitting members on the "
                                 "legislature's own pages (%s)"
                                 % (cfg["label"], key,
                                    ", ".join(m["name"] for m in sitting)))
            if sitting:
                m = sitting[0]
                member = {"name": m["name"]}
                if m["party"]:
                    member["party"] = PARTY_NAMES.get(m["party"], m["party"])
                if m["email"]:
                    member["email"] = m["email"]
                if m["phone"] and digits(m["phone"]) not in shared:
                    member["phone"] = m["phone"]
                member["url"] = m["url"]
                roster[key] = member
                for gone in listed:
                    if gone["status"]:
                        notes.append("%s %s: %s is marked %s and %s holds the seat"
                                     % (cfg["label"], key, gone["name"],
                                        gone["status"], m["name"]))
                continue
            if listed:
                # Every member the list gives this district has left. The
                # legislature does not use the word "vacant", so the record says
                # what its page does say, and dates it. The date carries forward
                # while the seat stays empty, so a weekly run that changes
                # nothing writes nothing.
                gone = listed[-1]
                prev = previous.get(key) or {}
                as_of = prev.get("asOf") if prev.get("vacant") else None
                roster[key] = {
                    "vacant": True,
                    "vacantWhy": ("The Arkansas State Legislature's page for "
                                  "this district's last member marks them as %s, "
                                  "and its member list names nobody after them."
                                  % gone["status"]),
                    "sourceUrl": gone["url"],
                    "asOf": as_of or today,
                }
                notes.append("%s %s: vacant (%s %s)" % (cfg["label"], key,
                                                        gone["name"], gone["status"]))
                continue
            prev = previous.get(key) or {}
            roster[key] = {"asOf": (prev.get("asOf") if not prev.get("name")
                                    and not prev.get("vacant") else None) or today}
            notes.append("%s %s: the list names nobody" % (cfg["label"], key))

        named = [m for m in roster.values() if m.get("name")]
        if len(named) < cfg["expected"]:
            raise SystemExit("FAIL: resolved %d named %s districts (expected >= %d) — "
                             "refusing to overwrite the roster with an incomplete "
                             "chamber" % (len(named), cfg["label"], cfg["expected"]))
        emails = sum(1 for m in named if m.get("email"))
        if emails < MIN_EMAIL_SHARE * len(named):
            raise SystemExit("FAIL: only %d of %d %s members carry an e-mail — the list "
                             "stopped publishing a field it has carried on every row"
                             % (emails, len(named), cfg["label"]))
        phones = sum(1 for m in named if m.get("phone"))
        if phones < MIN_PHONE_SHARE * len(named):
            raise SystemExit("FAIL: only %d of %d %s members carry a telephone — the "
                             "member pages' Phone row stopped parsing"
                             % (phones, len(named), cfg["label"]))
        built[chamber] = (roster, len(named), emails, phones, notes)
    if odd_parties:
        print("NOTE: party shipped as printed, not in PARTY_NAMES: %s"
              % "; ".join(odd_parties), file=sys.stderr)
    return built


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
    today = datetime.date.today().isoformat()

    if not offline:
        require_robots_once(LIST_URL, USER_AGENT, label="ar-build-ar-legislature-roster")
    built = build(offline, out_dir, today)

    # Write only once BOTH chambers have passed every guard, so a failure in
    # the House cannot leave a fresh Senate file beside a stale House one.
    os.makedirs(out_dir, exist_ok=True)
    for chamber, (roster, named, emails, phones, notes) in built.items():
        cfg = CHAMBERS[chamber]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("Wrote %s (%d of %d seats named, %d with an e-mail, %d with a "
              "telephone)" % (out_path, named, cfg["seats"], emails, phones),
              file=sys.stderr)
        for note in notes:
            print("  " + note, file=sys.stderr)


if __name__ == "__main__":
    main()
