#!/usr/bin/env python3
"""
Build the Arizona Senate and House rosters (district -> current officeholders)
as same-origin app-data files, from the Arizona Legislature's OWN member
rosters at www.azleg.gov, so the az-senate / az-house cards join a small
roster instead of reaching a third-party host at click time.

index.html's az-senate / az-house layers fetch data/app/az-senate-members.json
and az-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory: the Senate as {district -> {name,
party, email, capitolOffice, url}}, one senator per district, and the House as
{district -> {"seats": 2, "members": [two such rows]}}, because each of
Arizona's 30 legislative districts elects one senator and TWO representatives
(Ariz. Const. art. IV, pt. 2, sec. 1). A weekly GitHub Action
(.github/workflows/update-az-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a human look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-10. The Legislature prints one table
per chamber, /memberroster/?body=S and /memberroster/?body=H (tables
"SenateRoster" and "HouseRoster"), one row per member: the name in reading
order, linking the member's own page; the district; the party as a letter with
the word in its title ("Democratic"); the e-mail address's local part, under a
column headed "Email @azleg.gov" whose title says the suffix is the same for
every member; the Capitol room; and the Capitol telephone. A member who has
left keeps a row marked class="inactive", with the reason in red in place of
the e-mail ("Resigned on 3/2 to run for Congress"), and those rows are not
read. That day the Senate table held 30 current senators for 30 districts and
one inactive row, and the House table 60 current representatives, two for each
district, and two inactive rows. The tables list the 57th Legislature, whose
members serve until the 58th is sworn in in January 2027.

WHAT IS READ, AND WHAT IS NEVER READ. From each row: the name, the district,
the party's word, the e-mail address, the room and the telephone. A leadership
title printed after the name (" -- Majority Whip") is not part of the name and
is not read. The member photographs, the district map links and the member
pages are never fetched. The roster prints no building or street address, so
the Capitol office ships as the chamber, the room and the telephone, and no
address is supplied from anywhere else.

THE E-MAIL ADDRESS is the column's local part followed by the suffix its
heading names, lower-cased, because the site prints the local part in
capitals ("Email: AABEYTIA") and an address is not case-sensitive in practice.
The fleet's rule since 2026-10-17 (Adam: "E-mails too") is that an address a
government source prints in one official's own entry is that official's. An
address printed for two or more members is an office's and ships on no row.

ROBOTS AND PACING. www.azleg.gov's robots.txt is read through
scripts/robots_policy.py with the User-Agent the fetches send, before the first
fetch. Read 2026-11-10: its `*` group disallows /search/, /xml/, the calendar
and document-formatting paths and nothing under /memberroster/, and it states
a Crawl-delay of 120 seconds, which HostPacer honours, so a run takes about
four minutes for its two pages. apps.azleg.gov, whose robots.txt says
`Disallow: /` to every client, is never read.

Honesty: names are never guessed. A district the table gives fewer members
than it elects ships those it gives, dated; a Senate district with no row ships
as vacant, naming the table; a district carrying more members than it elects
stops the build.

Usage:
    python3 az/scripts/build_az_legislature_roster.py [output_dir]
    python3 az/scripts/build_az_legislature_roster.py --save DIR [output_dir]
    python3 az/scripts/build_az_legislature_roster.py --offline DIR [output_dir]

--save writes every page fetched into DIR (senate.html, house.html), reading
back any it already holds; --offline reads them back instead of fetching, for
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

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from robots_policy import HostPacer, RobotsGate  # noqa: E402  (FLEET_SHARED)

USER_AGENT = "districtry/1.0 (+https://districtry.com/az/)"
# The host is paced at one second even where it states no delay; it states 120.
MIN_PACE_SECONDS = 1.0
ATTEMPTS = 3
RETRY_SECONDS = 5.0

SITE = "https://www.azleg.gov"

# Floors catch a truncated table or a layout change while tolerating real
# vacancies: 30 of 30 senators and 60 of 60 representatives were named on
# 2026-11-10.
CHAMBERS = {
    "S": {"out": "az-senate-members.json", "label": "Senate", "seats": 30,
          "per_district": 1, "expected": 27, "rows": 27, "body": "S",
          "table": "SenateRoster", "chamber": "Arizona State Senate",
          "name": "The Arizona Senate",
          # The share of named members carrying each field, floored below what
          # 2026-11-10 measured: every current senator printed a party, an
          # e-mail address, a room and a telephone. A field falling under its
          # floor is the Brown County shape: the row count holds and the
          # contact goes.
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.9}},
    "H": {"out": "az-house-members.json", "label": "House", "seats": 30,
          "per_district": 2, "expected": 54, "rows": 54, "body": "H",
          "table": "HouseRoster", "chamber": "Arizona House of Representatives",
          "name": "The Arizona House",
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.9}},
}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

LOCAL_RE = re.compile(r"^[A-Za-z0-9._%+-]+$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\(\d{3}\) \d{3}-\d{4}$")
ROOM_RE = re.compile(r"^Room \d{1,4}[A-Z]?$")
ROW_RE = re.compile(r'<tr class="([^"]*)">(.*?)</tr>', re.S)
CELL_RE = re.compile(r"<td>(.*?)</td>", re.S)
MEMBER_LINK_RE = re.compile(
    r'<a href="(https://www\.azleg\.gov/(?:Senate/Senate|House/House)-member/\?[^"]*legislator=\d+)"')
TOOLTIP_RE = re.compile(r"<span>.*?</span>", re.S)
PARTY_RE = re.compile(r'<span title="([A-Za-z ]+)">([A-Z])</span>')
EMAIL_CELL_RE = re.compile(r">Email: ([^<]+)</a>")
# The column heading that states the suffix every address shares.
SUFFIX_RE = re.compile(r'<th title="Same suffix for all members">Email (@[a-z0-9.-]+)</th>')
TITLE_SUFFIX_RE = re.compile(r"\s+--\s+.*$")

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
        wait = MIN_PACE_SECONDS - (time.time() - _LAST[host])
        if wait > 0:
            time.sleep(wait)
        try:
            with _PACER.hold(url):
                resp = session().get(url, timeout=120)
            _LAST[host] = time.time()
            resp.raise_for_status()
            # The roster pages declare UTF-8.
            resp.encoding = "utf-8"
            return resp.text
        except requests.RequestException as exc:  # reset, timeout, 5xx
            _LAST[host] = time.time()
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


def roster_table(chamber, page):
    cfg = CHAMBERS[chamber]
    start = page.find('<table id="%s"' % cfg["table"])
    if start < 0:
        raise SystemExit("FAIL: the %s roster page no longer holds the %s table — "
                         "its layout changed" % (cfg["label"], cfg["table"]))
    end = page.find("</table>", start)
    return page[start:end]


def parse_rows(chamber, table):
    """Every CURRENT member row of a chamber's table, as plain fields."""
    cfg = CHAMBERS[chamber]
    suffix = SUFFIX_RE.search(table)
    if not suffix or suffix.group(1) != "@azleg.gov":
        raise SystemExit("FAIL: the %s table's e-mail column no longer says every "
                         "address ends @azleg.gov — its layout changed" % cfg["label"])
    rows, inactive = [], 0
    for cls, body in ROW_RE.findall(table):
        if cls == "inactive":
            inactive += 1
            continue
        if cls not in ("", "odd"):
            raise SystemExit("FAIL: a %s row is marked %r, which this builder does not "
                             "know how to read" % (cfg["label"], cls))
        cells = CELL_RE.findall(body)
        if len(cells) != 6:
            raise SystemExit("FAIL: a %s row carries %d cells, not 6 — the table's "
                             "layout changed" % (cfg["label"], len(cells)))
        link = MEMBER_LINK_RE.search(cells[0])
        name = TITLE_SUFFIX_RE.sub("", clean(TOOLTIP_RE.sub("", cells[0])))
        district = clean(TOOLTIP_RE.sub("", cells[1]))
        party = PARTY_RE.search(cells[2])
        email = EMAIL_CELL_RE.search(cells[3])
        if not link or not name or not district.isdigit():
            raise SystemExit("FAIL: a %s row lacks its name, member page or district "
                             "— the table's layout changed" % cfg["label"])
        rows.append({
            "name": name,
            "district": int(district),
            "party": party.group(1).strip() if party else None,
            "local": email.group(1).strip() if email else None,
            "room": clean(cells[4]),
            "phone": clean(cells[5]),
            "url": html_module.unescape(link.group(1)),
        })
    if len(rows) < cfg["rows"]:
        raise SystemExit("FAIL: the %s table yielded %d current members — its layout "
                         "changed" % (cfg["label"], len(rows)))
    return rows, inactive


def member_row(chamber, row, where, notes):
    cfg = CHAMBERS[chamber]
    member = {"name": row["name"]}
    if row["party"]:
        member["party"] = row["party"]
    else:
        notes.append("%s: no party printed for %s" % (where, row["name"]))
    local = row["local"]
    if local and LOCAL_RE.match(local) and EMAIL_RE.match(local.lower() + "@azleg.gov"):
        member["email"] = local.lower() + "@azleg.gov"
    elif local:
        notes.append("%s: %s's e-mail entry %r is not an address, so it was not carried"
                     % (where, row["name"], local))
    office = [cfg["chamber"]]
    if ROOM_RE.match(row["room"]):
        office.append(row["room"])
    elif row["room"]:
        notes.append("%s: %s's room reads %r, which was not carried"
                     % (where, row["name"], row["room"]))
    if PHONE_RE.match(row["phone"]):
        office.append(row["phone"])
    elif row["phone"]:
        notes.append("%s: %s's telephone is not printed as one number, so it was not "
                     "carried" % (where, row["name"]))
    if len(office) > 1:
        member["capitolOffice"] = office
    member["url"] = row["url"]
    return member


def build_chamber(chamber, pages, previous, today):
    cfg = CHAMBERS[chamber]
    list_url = "%s/memberroster/?body=%s" % (SITE, cfg["body"])
    table = roster_table(chamber, pages.get("%s.html" % cfg["label"].lower(), list_url))
    rows, inactive = parse_rows(chamber, table)
    by_district, notes = {}, []
    if inactive:
        notes.append("%d row(s) marked inactive (a member who left) were not read"
                     % inactive)
    for row in rows:
        district = row["district"]
        where = "%s %d" % (cfg["label"], district)
        if not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: %s is not one of the chamber's %d districts"
                             % (where, cfg["seats"]))
        by_district.setdefault(district, []).append(member_row(chamber, row, where, notes))
    seats = {}
    for district in range(1, cfg["seats"] + 1):
        where = "%s %d" % (cfg["label"], district)
        members = by_district.get(district, [])
        if len(members) > cfg["per_district"]:
            raise SystemExit("FAIL: %s carries %d current members for %d seats"
                             % (where, len(members), cfg["per_district"]))
        if cfg["per_district"] == 1:
            if members:
                seats[district] = members[0]
            else:
                prev = previous.get(str(district)) or {}
                seats[district] = {
                    "vacant": True,
                    "vacantWhy": "%s's roster lists no current member for this district."
                                 % cfg["name"],
                    "sourceUrl": list_url,
                    # The day the chamber was first read saying so, kept across runs.
                    "asOf": (prev.get("asOf") if prev.get("vacant") else None) or today,
                }
                notes.append("%s: no current member row, shipped as vacant" % where)
            continue
        record = {"seats": cfg["per_district"], "members": members}
        if len(members) < cfg["per_district"]:
            prev = previous.get(str(district)) or {}
            prev_short = len(prev.get("members") or []) < cfg["per_district"] and prev.get("asOf")
            record["asOf"] = prev.get("asOf") if prev_short else today
            record["sourceUrl"] = list_url
            notes.append("%s: %d of %d members listed" % (where, len(members),
                                                          cfg["per_district"]))
        seats[district] = record
    return seats, notes


def named_members(chamber, roster):
    out = []
    for rec in roster.values():
        if CHAMBERS[chamber]["per_district"] > 1:
            out.extend(m for m in rec.get("members") or [] if m.get("name"))
        elif rec.get("name"):
            out.append(rec)
    return out


def check(chamber, seats):
    cfg = CHAMBERS[chamber]
    roster = {str(d): seats[d] for d in range(1, cfg["seats"] + 1)}
    named = named_members(chamber, roster)
    if len(named) < cfg["expected"]:
        raise SystemExit("FAIL: resolved %d named %s members (expected >= %d) — "
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
    for chamber in ("S", "H"):
        previous = previous_roster(out_dir, CHAMBERS[chamber])
        seats, notes = build_chamber(chamber, pages, previous, today)
        built[chamber] = (check(chamber, seats), notes)

    # An address printed for two or more members, in either chamber, is an
    # office's and ships on no member's row.
    holders = {}
    for chamber, (roster, _) in built.items():
        for member in named_members(chamber, roster):
            if member.get("email"):
                holders.setdefault(member["email"], []).append(
                    "%s %s" % (CHAMBERS[chamber]["label"], member["name"]))
    shared = {a for a, who in holders.items() if len(who) > 1}
    for who in sorted(" and ".join(w) for w in holders.values() if len(w) > 1):
        print("NOTE: one e-mail address is printed for %s, so it is an office's and "
              "ships on no member's row" % who, file=sys.stderr)
    for chamber, (roster, _) in built.items():
        for member in named_members(chamber, roster):
            if member.get("email") in shared:
                del member["email"]
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
    if len(args) > 1 or (offline and save) or (args and args[0].startswith("-")):
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
        named = named_members(chamber, roster)
        print("Wrote %s (%d of %d seats named, %d with an e-mail, %d with a room)"
              % (out_path, len(named), cfg["seats"] * cfg["per_district"],
                 sum(1 for m in named if m.get("email")),
                 sum(1 for m in named
                     if any(x.startswith("Room ") for x in m.get("capitolOffice", ())))),
              file=sys.stderr)
        for note in notes:
            print("  " + note, file=sys.stderr)
    if _PACER is not None:
        for line in _PACER.report():
            print(line, file=sys.stderr)


if __name__ == "__main__":
    main()
