#!/usr/bin/env python3
"""
Build the Texas Senate and House of Representatives rosters (district ->
current officeholder) as same-origin app-data files, from each chamber's OWN
site (senate.texas.gov and house.texas.gov), so the tx-senate / tx-house cards
join a small roster instead of reaching a third-party host at click time.

index.html's tx-senate / tx-house layers fetch data/app/tx-senate-members.json
and tx-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party,
capitolOffice, url}}, or a vacancy record). A weekly GitHub Action
(.github/workflows/update-tx-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a human look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-11.

The Senate's member list, senate.texas.gov/members.php, prints one entry per
district linking member.php?d=<district>, with the senator's name, and marks a
vacant seat with an asterisk whose title says "indicates a currently vacant
seat" (District 22 that day, listed as "Constituent Services"). Each
senator's own page names the senator in its title ("Senator Bryan Hughes:
District 1"), prints the party ("Party: Republican"), and prints a "Capitol
Address" cell (the chamber's mailing box at Capitol Station in Austin and the
office telephone) beside one or more "District Address" cells. 30 of the 31
seats were named that day.

The House's member list, house.texas.gov/members, carries every seat as JSON in
the page itself: the member's name as "Last, First", the district, a link to
the member's own page (house.texas.gov/members/<code>) and an "active" flag.
That day 148 seats were active and two were not (Districts 1 and 93, listed by
the district's name alone), which this builder reads as vacant. Each member's
own page names the member in its title ("Rep. Wharton, Trey") and prints a
"Capitol Address" block (the office room in the Capitol or its extension, the
chamber's mailing box, the Austin ZIP code and the office telephone) followed
by a "District Address" block. The House site prints no party and no e-mail
address for any member, and neither does Texas Legislature Online
(capitol.texas.gov), so the House roster carries neither. The Senate links a
contact form for each senator instead of an address, so the Senate roster
carries no e-mail address either.

WHAT IS READ, AND WHAT IS NEVER READ. From each member: the name, the
district, the party (Senate only), the Capitol address and its telephone as
printed, and the member's own page. District addresses, home towns, biographies
and staff are never read, and no district office ships, because the builder
has no way to tell one apart from a member's home. Every Capitol address must
end in an Austin ZIP code (787xx) or the build refuses it.

ROBOTS. Both hosts' robots.txt are read through scripts/robots_policy.py with
the User-Agent the fetches send, before the first fetch, and a stated
Crawl-delay is honoured by its HostPacer. Read 2026-11-11: house.texas.gov's
`*` group allows every path and carries Cloudflare's Content-Signal
(search=yes, ai-train=no, use=reference), which the fleet's reading covers
(naming an officeholder with a link back to the page that names them is the
reference use); its other groups name AI vendors' crawlers and do not bind
this client. senate.texas.gov's `*` group disallows only /_assets, /bin, /kids,
/hola, /tsn and /memberForm.php, none of them read here. The Senate is paced
at one request a second and the House at one every three seconds regardless.

Honesty: names are never guessed. A seat the chamber marks vacant, or that is
missing from its list, gets a vacancy record naming that list; a seat carried
twice stops the build.

Usage:
    python3 tx/scripts/build_tx_legislature_roster.py [output_dir]
    python3 tx/scripts/build_tx_legislature_roster.py --save DIR [output_dir]
    python3 tx/scripts/build_tx_legislature_roster.py --offline DIR [output_dir]

--save writes every page fetched into DIR (senate-list.html, senate/<d>.html,
house-list.html and house/<code>.html), reading back any it already holds;
--offline reads them back instead of fetching, for building and testing
without the network.
"""

import datetime
import html as html_module
import json
import os
import re
import sys
import time
import urllib.parse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from robots_policy import HostPacer, RobotsGate  # noqa: E402  (FLEET_SHARED)

USER_AGENT = "districtry/1.0 (+https://districtry.com/tx/)"
# Each host is paced at one second at least, even where it states no delay,
# and the House at three (below).
MIN_PACE_SECONDS = 1.0
# house.texas.gov answers slower and slower at one request a second: measured
# 2026-11-11, two runs each stalled on a member page after about sixty, for
# minutes at a time, while the same page answered in under a second to a fresh
# request. So the House is asked once every three seconds, and a timed-out
# connection is dropped rather than reused.
HOST_PACE_SECONDS = {"house.texas.gov": 3.0}
# A member page answers in under a second; on 2026-11-11 one House page stalled
# for three 120-second reads in a row and answered in 0.6 s a minute later, so
# a read gives up sooner and a retry waits longer.
ATTEMPTS = 4
RETRY_SECONDS = 20.0

SENATE_SITE = "https://senate.texas.gov"
HOUSE_SITE = "https://house.texas.gov"
LISTS = {"S": SENATE_SITE + "/members.php", "H": HOUSE_SITE + "/members"}

# Floors catch a truncated list or a layout change while tolerating real
# vacancies: 30 of 31 senators and 148 of 150 representatives were named on
# 2026-11-11.
CHAMBERS = {
    "S": {"out": "tx-senate-members.json", "label": "Senate", "seats": 31,
          "expected": 27, "path": "senate",
          "of": "the Texas Senate",
          # The share of named members carrying each field, floored below what
          # 2026-11-11 measured: every named senator printed a party and a
          # Capitol address. A field falling under its floor is the Brown
          # County shape: the row count holds and the contact goes.
          "fields": {"party": 0.9, "capitolOffice": 0.9}},
    "H": {"out": "tx-house-members.json", "label": "House of Representatives",
          "seats": 150, "expected": 135, "path": "house",
          "of": "the Texas House of Representatives",
          # The House prints no party and no e-mail address for anyone.
          "fields": {"capitolOffice": 0.9}},
}

PARTIES = ("Republican", "Democrat", "Democratic", "Independent", "Libertarian")

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

# A telephone line as the two sites print one: "(512) 463-0101" mostly, but
# some House pages print "512-463-0490" and one senator's office its toll-free
# line, "1 (800) 959-8633 (TOLL-FREE)" (measured 2026-11-11). Each is one number.
PHONE_RE = re.compile(r"^(?:1 )?(?:\(\d{3}\) |\d{3}-)\d{3}-\d{4}(?: \(TOLL-FREE\))?$")
CAPITOL_ZIP_RE = re.compile(r"\bAustin,? (TX|Texas) 787\d\d(-\d{4})?$")

# The Senate list: one entry per district.
SENATE_ENTRY_RE = re.compile(
    r'<div class="mempicdiv">.*?<br><a href="member\.php\?d=(\d+)">(.*?)</a>'
    r'<br><span class="shrinkb">District (\d+)</span></div>', re.S)
SENATE_VACANT_MARK = "indicates a currently vacant seat"
SENATE_TITLE_RE = re.compile(r"<title>\s*Senator (.*?): District (\d+) \|", re.S)
SENATE_PARTY_RE = re.compile(r'<p class="meminfo"><span>Party:</span>([^<]*)</p>')
# The cell headed "Capitol Address" (id d<NN>CAP), and nothing beside it.
SENATE_CAPITOL_RE = re.compile(r'<td headers="d(\d+)CAP">(.*?)</td>', re.S)

# The House list: the member JSON in the page's <get-members> element.
HOUSE_MEMBERS_RE = re.compile(r'<get-members\b[^>]*?:members="([^"]*)"', re.S)
HOUSE_LINK_RE = re.compile(r"^https://(www\.)?house\.texas\.gov/members/(\d+)$")
HOUSE_TITLE_RE = re.compile(
    r"<title>\s*Official Home Page of the Texas House of Representatives Website for "
    r"Rep\. (.*?)\.?\s*</title>", re.S)
# The paragraph under "Capitol Address:", and nothing after it.
HOUSE_CAPITOL_RE = re.compile(r">Capitol Address:</h2>\s*<p>(.*?)</p>", re.S)

_SESSION = None


def session():
    global _SESSION
    if _SESSION is None:
        import requests

        _SESSION = requests.Session()
        _SESSION.headers["User-Agent"] = USER_AGENT
    return _SESSION


_GATE = None
_PACER = None
_LAST = {}


def gate():
    global _GATE, _PACER
    if _GATE is None:
        _GATE = RobotsGate(session(), USER_AGENT)
        _PACER = HostPacer(_GATE)
    return _GATE


def fetch(url):
    import requests

    ok, why = gate().allows(url)
    host = urllib.parse.urlsplit(url).netloc
    if host not in _LAST:
        print("robots.txt %s: %s" % (host, why), file=sys.stderr)
        _LAST[host] = 0.0
    if not ok:
        raise SystemExit("FAIL: robots.txt refuses %s (%s)" % (url, why))
    last = None
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_SECONDS * attempt)
        wait = HOST_PACE_SECONDS.get(host, MIN_PACE_SECONDS) - (time.time() - _LAST[host])
        if wait > 0:
            time.sleep(wait)
        try:
            with _PACER.hold(url):
                resp = session().get(url, timeout=45)
            _LAST[host] = time.time()
            resp.raise_for_status()
            # Both sites declare UTF-8.
            resp.encoding = "utf-8"
            return resp.text
        except requests.RequestException as exc:  # reset, timeout, 5xx
            _LAST[host] = time.time()
            if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
                session().close()  # a fresh connection on the next attempt
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (url, ATTEMPTS, last))


class Pages:
    """Fetch, save or replay the pages one run reads."""

    def __init__(self, offline=None, save=None):
        self.offline, self.save = offline, save

    def get(self, name, url):
        source = self.offline or (self.save if self.save and
                                  os.path.exists(os.path.join(self.save, name)) else None)
        if source:
            # --offline, or a page an interrupted --save run already wrote.
            with open(os.path.join(source, name), encoding="utf-8") as fh:
                return fh.read()
        body = fetch(url)
        if self.save:
            path = os.path.join(self.save, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(body)
        return body


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html_module.unescape(text)).strip()


def previous_roster(out_dir, cfg):
    try:
        with open(os.path.join(out_dir, cfg["out"]), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def vacancy(why, source, previous, district, today):
    prev = previous.get(str(district)) or {}
    return {
        "vacant": True,
        "vacantWhy": why,
        "sourceUrl": source,
        # The day the chamber was first read saying so, kept across runs.
        "asOf": (prev.get("asOf") if prev.get("vacant") else None) or today,
    }


def office_lines(block):
    """The lines of a printed address block, split on its line breaks."""
    parts = re.split(r"<br\s*/?>", block)
    return [clean(p) for p in parts if clean(p)]


def capitol_office(lines, where, notes):
    """The Capitol address as printed: its address lines, which end at the line
    carrying the Austin ZIP code, then the office telephone. A Senate cell
    names the senator ("The Honorable ..."), and that line is dropped;
    a "(TEL)" label is dropped from the telephone. Lines after the address
    that are not a telephone (office hours, "Meetings by Appointment Only")
    are not carried, and a fax line is never read."""
    lines = [re.sub(r"\s*\(TEL\)$", "", text) for text in lines
             if "FAX" not in text.upper() and not text.startswith("The Honorable")]
    # Four senators print a "Physical Address" block (the Capitol room) above a
    # "Mailing Address:" block (measured 2026-11-11). The physical block is
    # carried, without its label, because it names the room as the House
    # cards do; the phone is read from anywhere in the cell.
    labels = [i for i, text in enumerate(lines)
              if re.match(r"^(Physical|Mailing) Address:?$", text, re.I)]
    if labels:
        phones_anywhere = [text for text in lines if PHONE_RE.match(text)]
        first = lines[labels[0] + 1:labels[1]] if len(labels) > 1 else lines[labels[0] + 1:]
        lines = [text for text in first if not PHONE_RE.match(text)] + phones_anywhere
    ends = [i for i, text in enumerate(lines) if CAPITOL_ZIP_RE.search(text)]
    if not ends:
        notes.append("%s: the Capitol address reads %r, which carries no Austin ZIP "
                     "code, so it was not carried" % (where, lines))
        return []
    office = [text for text in lines[:ends[-1] + 1] if not PHONE_RE.match(text)]
    phones = [text for text in lines if PHONE_RE.match(text)]
    other = [text for text in lines[ends[-1] + 1:] if not PHONE_RE.match(text)]
    if other:
        notes.append("%s: %d line(s) after the Capitol address that are not a "
                     "telephone were not carried" % (where, len(other)))
    if len(phones) > 1:
        notes.append("%s: a second Capitol telephone was not carried" % where)
    if phones:
        office.append(phones[0])
    return office


def reading_order(last_first):
    """'Wharton, Trey' -> 'Trey Wharton'. A name printed without one comma
    ships as printed, and is reported."""
    parts = [p.strip() for p in last_first.split(",")]
    if len(parts) != 2 or not all(parts):
        return None
    return "%s %s" % (parts[1], parts[0])


def build_senate(pages, previous, today):
    cfg = CHAMBERS["S"]
    list_url = LISTS["S"]
    page = pages.get("senate-list.html", list_url)
    entries = SENATE_ENTRY_RE.findall(page)
    if len(entries) < cfg["seats"] - 2:
        raise SystemExit("FAIL: the Senate member list yielded %d entries — its layout "
                         "changed" % len(entries))
    seats, notes = {}, []
    for link_d, label, shown_d in entries:
        district = int(shown_d)
        where = "Senate %d" % district
        if int(link_d) != district:
            raise SystemExit("FAIL: %s links member.php?d=%s" % (where, link_d))
        if not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: %s is not one of the chamber's %d seats"
                             % (where, cfg["seats"]))
        if district in seats:
            raise SystemExit("FAIL: %s is listed twice" % where)
        if SENATE_VACANT_MARK in label:
            seats[district] = vacancy(
                "The member list of %s marks this seat as currently vacant." % cfg["of"],
                list_url, previous, district, today)
            notes.append("%s: marked vacant on the list" % where)
            continue
        url = "%s/member.php?d=%d" % (SENATE_SITE, district)
        member_page = pages.get("senate/%d.html" % district, url)
        title = SENATE_TITLE_RE.search(member_page)
        if not title or int(title.group(2)) != district:
            raise SystemExit("FAIL: %s's page does not name its senator in its title"
                             % where)
        name = clean(title.group(1))
        if name.split()[-1].lower() not in clean(label).lower():
            raise SystemExit("FAIL: %s's page names %r, which the list does not"
                             % (where, name))
        member = {"name": name}
        party = SENATE_PARTY_RE.search(member_page)
        party = clean(party.group(1)) if party else None
        if party in PARTIES:
            member["party"] = "Democratic" if party == "Democrat" else party
        elif party:
            notes.append("%s: party printed as %r ships as printed" % (where, party))
            member["party"] = party
        else:
            notes.append("%s: no party printed" % where)
        cell = [c for c in SENATE_CAPITOL_RE.findall(member_page)
                if int(c[0]) == district]
        if cell:
            office = capitol_office(office_lines(cell[0][1]), where, notes)
            if office:
                member["capitolOffice"] = office
        else:
            notes.append("%s: the senator's page prints no Capitol address" % where)
        member["url"] = url
        seats[district] = member
    for district in range(1, cfg["seats"] + 1):
        if district not in seats:
            seats[district] = vacancy(
                "The member list of %s names no one for this district." % cfg["of"],
                list_url, previous, district, today)
            notes.append("Senate %d: not listed, shipped as vacant" % district)
    return seats, notes


def build_house(pages, previous, today):
    cfg = CHAMBERS["H"]
    list_url = LISTS["H"]
    page = pages.get("house-list.html", list_url)
    m = HOUSE_MEMBERS_RE.search(page)
    if not m:
        raise SystemExit("FAIL: the House member list carries no member data — its "
                         "layout changed")
    rows = json.loads(html_module.unescape(m.group(1)))
    if len(rows) < cfg["seats"] - 5:
        raise SystemExit("FAIL: the House member list yielded %d rows — its layout "
                         "changed" % len(rows))
    seats, notes = {}, []
    for row in rows:
        district = int(row["id"])
        where = "House %d" % district
        if not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: %s is not one of the chamber's %d seats"
                             % (where, cfg["seats"]))
        if district in seats:
            raise SystemExit("FAIL: %s is listed twice" % where)
        if not row.get("active"):
            seats[district] = vacancy(
                "The member list of %s names no one for this district." % cfg["of"],
                list_url, previous, district, today)
            notes.append("%s: listed as inactive, shipped as vacant" % where)
            continue
        link = HOUSE_LINK_RE.match(str(row.get("link", "")))
        if not link or link.group(2) != str(row.get("member_bill_code")):
            raise SystemExit("FAIL: %s links %r, not a member page" % (where, row.get("link")))
        url = "%s/members/%s" % (HOUSE_SITE, link.group(2))
        name = reading_order(clean(row.get("member_name", "")))
        if not name:
            raise SystemExit("FAIL: %s's name %r is not printed as 'Last, First'"
                             % (where, row.get("member_name")))
        member_page = pages.get("house/%s.html" % link.group(2), url)
        title = HOUSE_TITLE_RE.search(member_page)
        if not title or reading_order(clean(title.group(1))) != name:
            raise SystemExit("FAIL: %s's page does not name %s in its title" % (where, name))
        member = {"name": name}
        block = HOUSE_CAPITOL_RE.search(member_page)
        if block:
            office = capitol_office(office_lines(block.group(1)), where, notes)
            if office:
                member["capitolOffice"] = office
        else:
            notes.append("%s: the member's page prints no Capitol address" % where)
        member["url"] = url
        seats[district] = member
    for district in range(1, cfg["seats"] + 1):
        if district not in seats:
            seats[district] = vacancy(
                "The member list of %s names no one for this district." % cfg["of"],
                list_url, previous, district, today)
            notes.append("House %d: not listed, shipped as vacant" % district)
    return seats, notes


def check(chamber, seats):
    cfg = CHAMBERS[chamber]
    roster = {str(d): seats[d] for d in range(1, cfg["seats"] + 1)}
    named = [m for m in roster.values() if m.get("name")]
    if len(named) < cfg["expected"]:
        raise SystemExit("FAIL: resolved %d named %s districts (expected >= %d) — "
                         "refusing to overwrite the roster with an incomplete chamber"
                         % (len(named), cfg["label"], cfg["expected"]))
    for field, share in sorted(cfg["fields"].items()):
        have = sum(1 for m in named if m.get(field))
        if have < share * len(named):
            raise SystemExit("FAIL: only %d of %d %s members carry %s, under the floor "
                             "of %d%% — a field the members carried stopped arriving"
                             % (have, len(named), cfg["label"], field, round(share * 100)))
    return roster


def build(pages, out_dir, today):
    built = {}
    for chamber, builder in (("S", build_senate), ("H", build_house)):
        previous = previous_roster(out_dir, CHAMBERS[chamber])
        seats, notes = builder(pages, previous, today)
        built[chamber] = (check(chamber, seats), notes)
    return built


def main():
    args = sys.argv[1:]
    offline = save = None
    while args and args[0] in ("--offline", "--save"):
        if len(args) < 2:
            print(__doc__.split("Usage:")[1].split("--save writes")[0], file=sys.stderr)
            sys.exit(1)
        if args[0] == "--offline":
            offline = args[1]
        else:
            save = args[1]
        args = args[2:]
    if len(args) > 1 or (offline and save):
        print("usage: %s [--offline DIR | --save DIR] [output_dir]" % sys.argv[0],
              file=sys.stderr)
        sys.exit(1)
    out_dir = args[0] if args else DEFAULT_OUT_DIR
    today = datetime.date.today().isoformat()

    built = build(Pages(offline, save), out_dir, today)

    # Write only once BOTH chambers have passed every guard, so a failure in
    # the House cannot leave a fresh Senate file beside a stale House one.
    os.makedirs(out_dir, exist_ok=True)
    for chamber, (roster, notes) in built.items():
        cfg = CHAMBERS[chamber]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        named = [m for m in roster.values() if m.get("name")]
        print("Wrote %s (%d of %d seats named, %d with a party, %d with a Capitol "
              "address, %d with its telephone)"
              % (out_path, len(named), cfg["seats"],
                 sum(1 for m in named if m.get("party")),
                 sum(1 for m in named if m.get("capitolOffice")),
                 sum(1 for m in named
                     if any(PHONE_RE.match(x) for x in m.get("capitolOffice", ())))),
              file=sys.stderr)
        for note in notes:
            print("  " + note, file=sys.stderr)
    if _PACER is not None:
        for line in _PACER.report():
            print(line, file=sys.stderr)


if __name__ == "__main__":
    main()
