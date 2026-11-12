#!/usr/bin/env python3
"""
Build the Florida Senate and House of Representatives rosters (district ->
current officeholder) as same-origin app-data files, from each chamber's OWN
site (flsenate.gov and flhouse.gov), so the fl-senate / fl-house cards join a
small roster instead of reaching a third-party host at click time.

index.html's fl-senate / fl-house layers fetch data/app/fl-senate-members.json
and fl-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party, email,
capitolOffice, url}}, or a vacancy record). A weekly GitHub Action
(.github/workflows/update-fl-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a human look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-11.

Both chambers' lists already showed the 2026-2028 term that day, the members
elected on 3 November 2026.

The Senate's member list, flsenate.gov/Senators/, is one table with a row per
district: the senator's name as "Last, First" linking the senator's page for
the term (/Senators/2026-2028/S<district>, which redirects to
/Senators/S<district>), the district, the party ("Republican", "Democrat" or
"No Party Affiliation") and the counties. A vacant seat's row names "Vacant"
and no party (District 39 that day). Each senator's own page names the senator
("Senator Ben Albritton"), prints "Party: <party>", prints the senator's own
e-mail address (a mailto link at flsenate.gov, inside the page's noscript
block; 31 of the 39 did that day, and the other eight offer only an e-mail
form) and a "Tallahassee Office" block: the Capitol room, the street, the
Tallahassee ZIP code, the office telephone and an internal "Senate VOIP"
extension, which is not carried. 39 of the 40 seats were named that day.

The House's member list, flhouse.gov/Sections/Representatives/
representatives.aspx, carries one entry per member: the name as "Last, First",
the party and "District: <n>", and a link to the member's page for the term
(details.aspx?MemberId=<id>&LegislativeTermId=92). All 120 seats were named
that day. Each member's contact page (contactmember.aspx?MemberId=<id>)
prints a "Capitol Office" block (the street, the Tallahassee ZIP code and the
office telephone) followed by one or more "District Office" blocks. The House
links an e-mail form for each member rather than printing an address, so the
House roster carries no e-mail address.

WHAT IS READ, AND WHAT IS NEVER READ. From each member: the name, the
district, the party, the senator's own e-mail address, the Capitol address and
its telephone as printed, and the member's own page. District offices, home
towns, biographies and staff are never read, and no district office ships,
because the builder has no way to tell one apart from a member's home. Every
Capitol address must end in a Tallahassee ZIP code (32399, the Capitol's own)
or the build refuses it.

ROBOTS. Both hosts' robots.txt are read through scripts/robots_policy.py with
the User-Agent the fetches send, before the first fetch, and a stated
Crawl-delay is honoured by its HostPacer. Read 2026-11-11: flsenate.gov's
file begins with a byte-order mark, which the shared reader strips, and its
`*` group disallows admin, API, e-mail-form and tracker-account paths, none of
them read here; flhouse.gov's `*` group disallows its login, bill-search,
salary and contract search forms and a few internal paths, none of them read
here. Neither states a Crawl-delay. The Senate is paced at one request a
second and the House at one every two seconds regardless.

Honesty: names are never guessed. A seat the chamber lists as vacant, or that
is missing from its list, gets a vacancy record naming that list; a seat
carried twice stops the build.

Usage:
    python3 fl/scripts/build_fl_legislature_roster.py [output_dir]
    python3 fl/scripts/build_fl_legislature_roster.py --save DIR [output_dir]
    python3 fl/scripts/build_fl_legislature_roster.py --offline DIR [output_dir]

--save writes every page fetched into DIR (senate-list.html, senate/<d>.html,
house-list.html and house/<id>.html), reading back any it already holds;
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

USER_AGENT = "districtry/1.0 (+https://districtry.com/fl/)"
MIN_PACE_SECONDS = 1.0
HOST_PACE_SECONDS = {"www.flhouse.gov": 2.0}
ATTEMPTS = 4
RETRY_SECONDS = 20.0

SENATE_SITE = "https://www.flsenate.gov"
HOUSE_SITE = "https://www.flhouse.gov"
LISTS = {"S": SENATE_SITE + "/Senators/",
         "H": HOUSE_SITE + "/Sections/Representatives/representatives.aspx"}

# Floors catch a truncated list or a layout change while tolerating real
# vacancies: 39 of 40 senators and 120 of 120 representatives were named on
# 2026-11-11.
CHAMBERS = {
    "S": {"out": "fl-senate-members.json", "label": "Senate", "seats": 40,
          "expected": 35, "of": "the Florida Senate",
          # The share of named members carrying each field, floored below what
          # 2026-11-11 measured: every named senator printed a party and a
          # Tallahassee office (one, District 10, an address with no ZIP code,
          # which is not carried). A field falling under its floor is the
          # Brown County shape: the row count holds and the contact goes.
          # 31 of the 39 named senators print their own e-mail address; the
          # other eight offer only the Senate's "Email the Senator" form, and
          # the one address on their pages is the site's webmaster, which is
          # nobody's (measured 2026-11-11). So the e-mail floor is 0.7.
          "fields": {"party": 0.9, "email": 0.7, "capitolOffice": 0.9}},
    "H": {"out": "fl-house-members.json", "label": "House of Representatives",
          "seats": 120, "expected": 108, "of": "the Florida House of Representatives",
          # The House prints no e-mail address for anyone. 43 of the 120
          # members' contact pages print no Capitol office, only an e-mail
          # form: the 40 members new to the House and three returning after a
          # break, all elected on 3 November 2026, whose offices are not
          # posted yet (measured 2026-11-11). So the office floor is 0.6 until
          # they are, which fl/WATCH.md records to raise back.
          "fields": {"party": 0.9, "capitolOffice": 0.6}},
}

PARTIES = ("Republican", "Democrat", "Democratic", "No Party Affiliation",
           "Independent", "Libertarian")

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

PHONE_RE = re.compile(r"^\(\d{3}\) \d{3}-\d{4}$")
CAPITOL_ZIP_RE = re.compile(r"\bTallahassee,? FL 32399(-\d{4})?$")
SENATE_EMAIL_RE = re.compile(r'href="mailto:([a-z0-9.\-]+@flsenate\.gov)"', re.I)

# The Senate list: one table row per district.
SENATE_ROW_RE = re.compile(r'<tr class="All[^"]*">(.*?)</tr>', re.S)
SENATE_LINK_RE = re.compile(r'<a class="senatorLink" href="/Senators/[0-9-]+/S(\d+)">'
                            r'(?:<img[^>]*>)?(.*?)</a>', re.S)
SENATE_CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
SENATE_NAME_RE = re.compile(r'<h2 class="senatorName">\s*Senator (.*?)\s*</h2>', re.S)
SENATE_PARTY_RE = re.compile(r'<p class="[^"]*">\s*Party: ([^<]*)</p>')
# The block headed "Tallahassee Office", and nothing after it.
SENATE_CAPITOL_RE = re.compile(r"<h4>Tallahassee Office</h4>\s*<div class=\"left\">(.*?)</div>",
                               re.S)

# The House list: one box per member.
HOUSE_BOX_RE = re.compile(
    r'<div class="team-box">\s*<a href="/Sections/Representatives/details\.aspx\?'
    r'MemberId=(\d+)&(?:amp;)?LegislativeTermId=(\d+)"[^>]*>.*?<h5>(.*?)</h5>\s*'
    r'<p>(.*?)</p>', re.S)
HOUSE_PARTY_DISTRICT_RE = re.compile(r"^(.*?)\s*—\s*District:\s*(\d+)$")
HOUSE_CONTACT_NAME_RE = re.compile(
    r'<h1 class="ribbon" id="contact-info-header">Contact Information for(.*?)</h1>', re.S)
# The <address> under "Capitol Office", and nothing after it.
HOUSE_CAPITOL_RE = re.compile(r'<h2 id="capitol-office">Capitol Office</h2>.*?'
                              r"<address>(.*?)</address>", re.S)
HOUSE_INFO_RE = re.compile(r'<span class="info[^"]*">(.*?)</span>', re.S)

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
    carrying the Tallahassee ZIP code, then the office telephone. The Senate's
    internal "Senate VOIP" extension and any fax line are never carried."""
    lines = [text for text in lines
             if "FAX" not in text.upper() and not text.upper().startswith("SENATE VOIP")]
    ends = [i for i, text in enumerate(lines) if CAPITOL_ZIP_RE.search(text)]
    if not ends:
        notes.append("%s: the Capitol address reads %r, which carries no Tallahassee "
                     "ZIP code, so it was not carried" % (where, lines))
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


SUFFIXES = {"Jr.", "Jr", "Sr.", "Sr", "II", "III", "IV"}


def reading_order(last_first):
    """'Abbott, Shane G.' -> 'Shane G. Abbott', and a suffix printed after a
    second comma goes last: 'Massullo, Ralph E., Jr.' -> 'Ralph E. Massullo
    Jr.' (the Senate list prints it that way, measured 2026-11-11). Any other
    shape is refused by the caller."""
    parts = [p.strip() for p in last_first.split(",")]
    if not all(parts):
        return None
    if len(parts) == 2:
        return "%s %s" % (parts[1], parts[0])
    if len(parts) == 3 and parts[2] in SUFFIXES:
        return "%s %s %s" % (parts[1], parts[0], parts[2])
    return None


def party_of(printed, where, notes):
    if printed in PARTIES:
        return "Democratic" if printed == "Democrat" else printed
    if printed:
        notes.append("%s: party printed as %r ships as printed" % (where, printed))
        return printed
    notes.append("%s: no party printed" % where)
    return None


def build_senate(pages, previous, today):
    cfg = CHAMBERS["S"]
    list_url = LISTS["S"]
    page = pages.get("senate-list.html", list_url)
    rows = SENATE_ROW_RE.findall(page)
    if len(rows) < cfg["seats"] - 2:
        raise SystemExit("FAIL: the Senate member list yielded %d rows — its layout "
                         "changed" % len(rows))
    seats, notes = {}, []
    for row in rows:
        link = SENATE_LINK_RE.search(row)
        cells = [clean(c) for c in SENATE_CELL_RE.findall(row)]
        if not link or len(cells) < 2:
            raise SystemExit("FAIL: a Senate list row carries no senator link and "
                             "district — its layout changed")
        district = int(cells[0])
        where = "Senate %d" % district
        if int(link.group(1)) != district:
            raise SystemExit("FAIL: %s links S%s" % (where, link.group(1)))
        if not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: %s is not one of the chamber's %d seats"
                             % (where, cfg["seats"]))
        if district in seats:
            raise SystemExit("FAIL: %s is listed twice" % where)
        label = clean(link.group(2))
        if label.lower() == "vacant":
            seats[district] = vacancy(
                "The member list of %s lists this seat as vacant." % cfg["of"],
                list_url, previous, district, today)
            notes.append("%s: listed as vacant" % where)
            continue
        listed = reading_order(label)
        if not listed:
            raise SystemExit("FAIL: %s's name %r is not printed as 'Last, First'"
                             % (where, label))
        url = "%s/Senators/S%d" % (SENATE_SITE, district)
        member_page = pages.get("senate/%d.html" % district, url)
        named = SENATE_NAME_RE.search(member_page)
        if not named:
            raise SystemExit("FAIL: %s's page does not name its senator" % where)
        name = clean(named.group(1))
        surname = label.split(",")[0].strip().lower()
        if surname not in name.lower():
            raise SystemExit("FAIL: %s's page names %r, which the list (%r) does not"
                             % (where, name, label))
        member = {"name": name}
        party = SENATE_PARTY_RE.search(member_page)
        party = party_of(clean(party.group(1)) if party else (cells[1] if len(cells) > 1 else ""),
                         where, notes)
        if party:
            member["party"] = party
        if len(cells) > 1 and cells[1] and party and \
                party_of(cells[1], where, []) != party:
            raise SystemExit("FAIL: %s's page prints party %r and the list %r"
                             % (where, party, cells[1]))
        emails = sorted(set(e.lower() for e in SENATE_EMAIL_RE.findall(member_page)))
        if len(emails) == 1:
            member["email"] = emails[0]
        elif emails:
            notes.append("%s: %d e-mail addresses printed, none carried"
                         % (where, len(emails)))
        else:
            notes.append("%s: no e-mail address printed" % where)
        block = SENATE_CAPITOL_RE.search(member_page)
        if block:
            office = capitol_office(office_lines(block.group(1)), where, notes)
            if office:
                member["capitolOffice"] = office
        else:
            notes.append("%s: the senator's page prints no Tallahassee office" % where)
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
    boxes = HOUSE_BOX_RE.findall(page)
    if len(boxes) < cfg["seats"] - 5:
        raise SystemExit("FAIL: the House member list yielded %d entries — its layout "
                         "changed" % len(boxes))
    terms = set(term for _, term, _, _ in boxes)
    if len(terms) != 1:
        raise SystemExit("FAIL: the House member list links %d terms (%s), not one"
                         % (len(terms), ", ".join(sorted(terms))))
    seats, notes = {}, []
    for member_id, term, label, info in boxes:
        m = HOUSE_PARTY_DISTRICT_RE.match(clean(info))
        if not m:
            raise SystemExit("FAIL: House member %s's entry reads %r, not "
                             "'<party> — District: <n>'" % (member_id, clean(info)))
        district = int(m.group(2))
        where = "House %d" % district
        if not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: %s is not one of the chamber's %d seats"
                             % (where, cfg["seats"]))
        if district in seats:
            raise SystemExit("FAIL: %s is listed twice" % where)
        label = clean(label)
        if label.lower() == "vacant":
            seats[district] = vacancy(
                "The member list of %s lists this seat as vacant." % cfg["of"],
                list_url, previous, district, today)
            notes.append("%s: listed as vacant" % where)
            continue
        name = reading_order(label)
        if not name:
            raise SystemExit("FAIL: %s's name %r is not printed as 'Last, First'"
                             % (where, label))
        member = {"name": name}
        party = party_of(m.group(1), where, notes)
        if party:
            member["party"] = party
        contact_url = "%s/Sections/Representatives/contactmember.aspx?MemberId=%s" % (
            HOUSE_SITE, member_id)
        contact = pages.get("house/%s.html" % member_id, contact_url)
        heading = HOUSE_CONTACT_NAME_RE.search(contact)
        # The list may print a suffix inside the surname ("Bush III, Dr.
        # James") where the contact page prints it after a comma ("Dr. James
        # Bush , III"), so the suffix is left out of the comparison.
        surname = " ".join(w for w in label.split(",")[0].split()
                           if w.rstrip(".") not in {x.rstrip(".") for x in SUFFIXES}).lower()
        if not heading or surname not in clean(heading.group(1)).lower():
            raise SystemExit("FAIL: %s's contact page does not name %s" % (where, name))
        block = HOUSE_CAPITOL_RE.search(contact)
        if block:
            lines = []
            for span in HOUSE_INFO_RE.findall(block.group(1)):
                if "<a " in span:
                    continue  # the map link under the address
                lines.extend(office_lines(span))
            office = capitol_office(lines, where, notes)
            if office:
                member["capitolOffice"] = office
        else:
            notes.append("%s: the member's contact page prints no Capitol office" % where)
        member["url"] = ("%s/Sections/Representatives/details.aspx?MemberId=%s"
                         "&LegislativeTermId=%s" % (HOUSE_SITE, member_id, term))
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
        print("Wrote %s (%d of %d seats named, %d with a party, %d with an e-mail "
              "address, %d with a Capitol address, %d with its telephone)"
              % (out_path, len(named), cfg["seats"],
                 sum(1 for m in named if m.get("party")),
                 sum(1 for m in named if m.get("email")),
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
