#!/usr/bin/env python3
"""
Build the Nevada Senate and Assembly rosters (district -> current officeholder)
as same-origin app-data files, from the Nevada Legislature's OWN member pages
at www.leg.state.nv.us, so the nv-senate / nv-assembly cards join a small
roster instead of reaching a third-party host at click time.

index.html's nv-senate / nv-assembly layers fetch data/app/nv-senate-members.json
and nv-assembly-members.json lazily on first click and join them to the
pre-built legislative geometry by district number. This script writes the two
rosters shaped for the registerIlgaChamber factory ({district -> {name, party,
email, phone, capitolOffice, url}}, or a vacancy record). A weekly GitHub Action
(.github/workflows/update-nv-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a human look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-10. The Legislature prints one list per
chamber, /App/Legislator/A/Senate/Current and /App/Legislator/A/Assembly/Current,
as a table with two rows per member: the first gives the name surname-first
("Buck, Carrie Ann"), the party as a word and the district ("No. 5"), each
linking the member's own page (/App/Legislator/A/Senate/Current/5); the second
gives the member's Carson City room and telephone, a Las Vegas room, an e-mail
address and, for some, a work telephone and a fax number. That day the Senate
list held 21 members for 21 seats and the Assembly list 42 for 42. Above each
table the page prints where to send mail to legislators "at the capital during
session": c/o the chamber, 401 South Carson Street, Carson City, NV 89701-4747.

The list was read a week after the 3 November 2026 election. 20 of the 21
senators and 30 of the 42 Assembly members printed an e-mail address and a
Carson City room; the others, most of them newly seated, printed a Carson City
telephone and nothing else, and the floors below are set under that.

WHAT IS READ, AND WHAT IS NEVER READ. From the list: the party, the district,
the Carson City room and telephone, the e-mail address and the work telephone.
From each member's own page: the member's name in reading order, from the
page's title ("Senator Carrie Ann Buck"), because turning the list's
surname-first form round would mean guessing where a suffix or a two-word
surname goes; the page must also name the same district. From the list's head:
the chamber's mailing address. The Las Vegas room is never read, because the
page names no building for it; the fax number, the term and the counties a
district covers are never read either.

THE E-MAIL ADDRESS. The page hides each address from simple harvesters with
Cloudflare's e-mail protection (data-cfemail): the hex string's first byte is
a key, and XOR-ing every following byte with it gives the address, which is
what the visitor's browser does. It ships as the page writes it, because the
fleet's rule since 2026-10-17 (Adam: "E-mails too") is that an address a
government source prints in one official's own entry is that official's. An
address printed for two or more members is an office's and ships on no row.

THE WORK TELEPHONE ships as "work (775) 555-0100" on the member's row, because
the same rule covers a number printed in one official's own entry, with the
label the source gives it. A work number printed for two or more members, or
equal to a Carson City telephone, is an office's and ships on no member's row.

ROBOTS. www.leg.state.nv.us's robots.txt is read through
scripts/robots_policy.py with the User-Agent the fetches send, before the first
fetch, and a stated Crawl-delay is honoured by its HostPacer. Read 2026-11-10:
its `*` group disallows report, exhibit, fiscal-note, lobbyist and opinion
paths and nothing under /App/Legislator/, and states no Crawl-delay. The host
is paced at one request a second regardless.

Honesty: names are never guessed. A seat missing from a chamber's list gets a
vacancy record naming that list; a seat carried by two rows stops the build.

Usage:
    python3 nv/scripts/build_nv_legislature_roster.py [output_dir]
    python3 nv/scripts/build_nv_legislature_roster.py --save DIR [output_dir]
    python3 nv/scripts/build_nv_legislature_roster.py --offline DIR [output_dir]

--save writes every page fetched into DIR (senate-list.html, senate/<n>.html,
assembly-list.html and assembly/<n>.html), reading back any it already holds;
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

USER_AGENT = "districtry/1.0 (+https://districtry.com/nv/)"
# The host is paced at one second even where it states no delay.
MIN_PACE_SECONDS = 1.0
ATTEMPTS = 3
RETRY_SECONDS = 5.0

SITE = "https://www.leg.state.nv.us"

# Floors catch a truncated list or a layout change while tolerating real
# vacancies: 21 of 21 senators and 42 of 42 Assembly members were named on
# 2026-11-10.
CHAMBERS = {
    "S": {"out": "nv-senate-members.json", "label": "Senate", "seats": 21,
          "expected": 19, "rows": 18, "path": "Senate", "title": "Senator",
          "care_of": "c/o Nevada Senate",
          "body": "The Nevada Senate",
          # The share of named members carrying each field, floored below what
          # 2026-11-10 measured: every senator printed a party and a Carson
          # City telephone, and 20 of 21 an e-mail address. A field falling
          # under its floor is the Brown County shape: the row count holds and
          # the contact goes.
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.75}},
    "A": {"out": "nv-assembly-members.json", "label": "Assembly", "seats": 42,
          "expected": 38, "rows": 36, "path": "Assembly",
          "title": "Assemblymember", "care_of": "c/o Nevada Assembly",
          "body": "The Nevada Assembly",
          # 30 of 42 printed an e-mail address on 2026-11-10; most of the other
          # twelve were seated after the 3 November election and print only a
          # Carson City telephone so far.
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.5}},
}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\(\d{3}\) \d{3}-\d{4}$")
ROOM_RE = re.compile(r"^[A-Z]{0,3}\d{3,4}[A-Z]?$")

ROW_SPLIT = '<tr class="thisRow'
CELL_RE = re.compile(r'<td data-order="([^"]*)"')
FIELD_RE = re.compile(
    r'<span class="fieldName">([^<]*)</span>(?:&nbsp;|\s)*<span class="field">(.*?)</span>',
    re.S)
CFEMAIL_RE = re.compile(r'data-cfemail="([0-9a-fA-F]+)"')
DISTRICT_RE = re.compile(r"^No\. (\d+)$")
TITLE_RE = re.compile(r"<title>\s*([^<]*?)\s*</title>", re.S)
PAGE_DISTRICT_RE = re.compile(r'href="#districtTab"[^>]*>\s*District (\d+)\s*<')
# The chamber's mailing address at the capital, as the list prints it.
MAIL_RE = re.compile(
    r"To send mail to legislators at the capital during session, the address is:"
    r"\s*<br\s*/?>(.*?)</div>", re.S)
MAIL_CITY_RE = re.compile(r"^Carson City, NV 897\d\d(-\d{4})?$")

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
            # Every page read here declares UTF-8.
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


def cf_decode(hexstr):
    """Cloudflare's e-mail protection: the first byte is the key, and every
    following byte XOR the key is one character of the address."""
    key = int(hexstr[:2], 16)
    return "".join(chr(int(hexstr[i:i + 2], 16) ^ key)
                   for i in range(2, len(hexstr), 2))


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


def mailing_address(chamber, page):
    cfg = CHAMBERS[chamber]
    m = MAIL_RE.search(page)
    if not m:
        raise SystemExit("FAIL: the %s list no longer prints the capital mailing "
                         "address — its layout changed" % cfg["label"])
    lines = [clean(x) for x in re.split(r"<br\s*/?>", m.group(1))]
    lines = [x for x in lines if x]
    if (len(lines) != 3 or lines[0] != cfg["care_of"]
            or not MAIL_CITY_RE.match(lines[2])):
        raise SystemExit("FAIL: the %s list's capital mailing address reads %r, not "
                         "the chamber, a street and Carson City" % (cfg["label"], lines))
    return ", ".join(lines)


def parse_list(chamber, page):
    cfg = CHAMBERS[chamber]
    link_re = re.compile(r'href="(/App/Legislator/A/%s/Current/(\d+))"' % cfg["path"])
    rows, cur = [], None
    for chunk in page.split(ROW_SPLIT)[1:]:
        if chunk.startswith(" listRow"):
            cells = [html_module.unescape(c) for c in CELL_RE.findall(chunk)]
            link = link_re.search(chunk)
            if len(cells) < 3 or not link:
                raise SystemExit("FAIL: a %s member row lacks its name, party, district "
                                 "or page link — the list's layout changed" % cfg["label"])
            district = DISTRICT_RE.match(cells[2].strip())
            if not district:
                raise SystemExit("FAIL: a %s row prints its district as %r"
                                 % (cfg["label"], cells[2]))
            cur = {"listed": cells[0].strip(), "party": cells[1].strip() or None,
                   "district": int(district.group(1)), "path": link.group(1),
                   "fields": {}, "email": None}
            rows.append(cur)
        elif cur is not None and not cur["fields"] and cur["email"] is None:
            for key, value in FIELD_RE.findall(chunk):
                key = clean(key).rstrip(":").strip()
                cur["fields"].setdefault(key, clean(value))
            mail = CFEMAIL_RE.search(chunk)
            if mail:
                cur["email"] = cf_decode(mail.group(1))
    if len(rows) < cfg["rows"]:
        raise SystemExit("FAIL: the %s member list yielded %d rows — its layout changed"
                         % (cfg["label"], len(rows)))
    return rows


def plain_email(raw, where, notes):
    if not raw:
        return None
    raw = raw.strip()
    if EMAIL_RE.match(raw):
        return raw
    notes.append("%s: an e-mail entry that is not one plain address was not carried" % where)
    return None


def phone_or_none(raw, what, where, notes):
    if not raw:
        return None
    if PHONE_RE.match(raw):
        return raw
    notes.append("%s: the %s is not printed as one number, so it was not carried"
                 % (where, what))
    return None


def member_name(chamber, page, row, where):
    """The member's name in reading order, from the member page's title."""
    cfg = CHAMBERS[chamber]
    m = TITLE_RE.search(page)
    title = clean(m.group(1)) if m else ""
    prefix = cfg["title"] + " "
    if not title.startswith(prefix) or len(title) <= len(prefix):
        raise SystemExit("FAIL: %s's page is titled %r, not %r and a name"
                         % (where, title, prefix.strip()))
    name = title[len(prefix):].strip()
    # One title printed a doubled full stop after an initial ("Melissa R..
    # Hardy" on 2026-11-10); a run of full stops is a typing slip, never a name.
    name = re.sub(r"\.{2,}", ".", name)
    surname = row["listed"].split(",")[0].strip().lower()
    if surname and surname not in name.lower():
        raise SystemExit("FAIL: %s's page names %r, which does not carry the list's "
                         "surname %r" % (where, name, surname))
    d = PAGE_DISTRICT_RE.search(page)
    if not d or int(d.group(1)) != row["district"]:
        raise SystemExit("FAIL: %s's page names District %s"
                         % (where, d.group(1) if d else "none"))
    return name


def build_chamber(chamber, pages, previous, today):
    cfg = CHAMBERS[chamber]
    list_url = "%s/App/Legislator/A/%s/Current" % (SITE, cfg["path"])
    page = pages.get("%s-list.html" % cfg["path"].lower(), list_url)
    mail = mailing_address(chamber, page)
    rows = parse_list(chamber, page)
    seats, notes = {}, []
    for row in rows:
        district = row["district"]
        where = "%s %d" % (cfg["label"], district)
        if not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: %s is not one of the chamber's %d seats"
                             % (where, cfg["seats"]))
        if district in seats:
            raise SystemExit("FAIL: %s carries two member rows" % where)
        url = SITE + row["path"]
        member_page = pages.get("%s/%s.html" % (cfg["path"].lower(),
                                                row["path"].rsplit("/", 1)[1]), url)
        member = {"name": member_name(chamber, member_page, row, where)}
        if row["party"]:
            member["party"] = row["party"]
        else:
            notes.append("%s: no party printed" % where)
        email = plain_email(row["email"], where, notes)
        if email:
            member["email"] = email
        fields = row["fields"]
        capitol_phone = phone_or_none(fields.get("Carson City Phone"),
                                      "Carson City telephone", where, notes)
        work = phone_or_none(fields.get("Work Phone"), "work telephone", where, notes)
        if work and work != capitol_phone:
            member["phone"] = "work " + work
        office = []
        room = fields.get("Carson City Room")
        if room:
            if ROOM_RE.match(room):
                office.append("Room %s" % room)
            else:
                notes.append("%s: the Carson City room reads %r, which was not carried"
                             % (where, room))
        office.append("Mail during session: " + mail)
        if capitol_phone:
            office.append(capitol_phone)
        member["capitolOffice"] = office
        member["url"] = url
        seats[district] = member
    for district in range(1, cfg["seats"] + 1):
        if district not in seats:
            seats[district] = vacancy(
                "%s's member list names no one for this district." % cfg["body"],
                list_url, previous, district, today)
            notes.append("%s %d: no row, shipped as vacant" % (cfg["label"], district))
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
    for chamber in ("S", "A"):
        previous = previous_roster(out_dir, CHAMBERS[chamber])
        seats, notes = build_chamber(chamber, pages, previous, today)
        built[chamber] = (check(chamber, seats), notes)

    # An address or work number printed for two or more members, in either
    # chamber, is an office's and ships on no member's row.
    for field in ("email", "phone"):
        holders = {}
        for chamber, (roster, _) in built.items():
            for district, member in roster.items():
                if member.get(field):
                    holders.setdefault(member[field].lower(), []).append(
                        "%s %s" % (CHAMBERS[chamber]["label"], district))
        shared = {a for a, who in holders.items() if len(who) > 1}
        for who in sorted(" and ".join(w) for w in holders.values() if len(w) > 1):
            print("NOTE: one %s is printed for %s, so it is an office's and ships on "
                  "no member's row" % (field, who), file=sys.stderr)
        for roster, _ in built.values():
            for member in roster.values():
                if member.get(field, "").lower() in shared:
                    del member[field]
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
    # the Assembly cannot leave a fresh Senate file beside a stale Assembly one.
    os.makedirs(out_dir, exist_ok=True)
    for chamber, (roster, notes) in built.items():
        cfg = CHAMBERS[chamber]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        named = [m for m in roster.values() if m.get("name")]
        print("Wrote %s (%d of %d seats named, %d with an e-mail, %d with a Carson "
              "City room, %d with a work telephone)"
              % (out_path, len(named), cfg["seats"],
                 sum(1 for m in named if m.get("email")),
                 sum(1 for m in named
                     if any(x.startswith("Room ")
                            for x in m.get("capitolOffice", ()))),
                 sum(1 for m in named if m.get("phone"))),
              file=sys.stderr)
        for note in notes:
            print("  " + note, file=sys.stderr)
    if _PACER is not None:
        for line in _PACER.report():
            print(line, file=sys.stderr)


if __name__ == "__main__":
    main()
