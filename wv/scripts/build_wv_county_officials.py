#!/usr/bin/env python3
"""
Build wv/data/app/wv-county-officials.json: every West Virginia county's
county commission and its other elected officers, read from the West Virginia
Secretary of State's directory of county officials, so the County card can name
who governs the county a reader clicked without reaching a third-party host at
click time.

THE SOURCE, MEASURED 2026-10-29. The Secretary of State publishes a directory
of elected county officials by year at apps.sos.wv.gov/elections/Officials/.
Its index that day offered the years 2022 to 2025, and the 2025 directory
listed all 55 counties. Each county's page lists every official by name and
title, and each name links to a page of its own giving the official's
telephone, fax, e-mail address and mailing address. The 2025 directory held,
for every county: the county commissioners (three in 53 counties and five in
Berkeley and Jefferson), five members of the board of education, and one each
of county clerk, circuit clerk, sheriff, prosecuting attorney and surveyor,
with an assessor in 54 (Cabell's page lists none). The script reads the newest
year whose directory lists all 55 counties, so a 2027 directory is followed
once it is complete, and the card says which year it read.

WHAT EACH COUNTY'S GOVERNING BODY IS. Every county is governed by a county
commission (W. Va. Const. art. IX, sec. 9), three commissioners in most
counties and five in Berkeley and Jefferson, each elected by the whole county
to a six-year term, staggered so that one seat (or two) is on the ballot every
two years. No two commissioners may live in the same magisterial district
(art. IX, sec. 10), which is why the Magisterial District layer exists.

THE BOARD OF EDUCATION IS NOT READ FROM THIS DIRECTORY, and that is the year's
doing, not the directory's: the boards are elected in May of even years and
take office on 1 July, so the 2025 directory names members whose seats were on
the ballot in May 2026 and may since have changed hands. They are recorded as
gap wv-school-board-members until a list that postdates 1 July 2026 is read.

WHAT SHIPS, AND WHAT NEVER DOES. For each official: the title as the directory
prints it, the name, and the telephone and e-mail address printed on that
official's own page. A telephone or address printed for two or more officials
of one county belongs to an office, not a person (the fleet's rule since
2026-10-17): printed for two or more commissioners, it ships as the
commission's own; otherwise it ships nowhere. A mailing address ships only as
the commission's office, where at least two commissioners print the same one,
because a rural official's mailing address can be a home. Fax numbers never
ship.

A VACANCY IS NOT A NAME. Where the directory prints "Vacant" in the name
column (measured 2026-10-29: the county surveyor in 28 counties, and nothing
else), the row ships as `vacant: true` with no name, telephone or e-mail
address. The page that row links to is still read, for one purpose: a number
or address it prints that is also printed for a person is an office's, so it
ships on nobody's row.

Honesty: names are never guessed and nothing is carried over from an earlier
run. A county whose page does not have the expected shape stops the build.

ROBOTS. apps.sos.wv.gov's robots.txt (330 bytes, read 2026-10-29 with this
script's own User-Agent) disallows nothing this script reads and states no
delay; every fetch is still paced at one second. A run is about 560 requests,
some ten minutes.

Usage:
    python3 wv/scripts/build_wv_county_officials.py [output_dir]
    python3 wv/scripts/build_wv_county_officials.py --save DIR [output_dir]
    python3 wv/scripts/build_wv_county_officials.py --offline DIR [output_dir]
    python3 wv/scripts/build_wv_county_officials.py --check

--check reads the SHIPPED file and nothing else, offline: one record for each
of the 55 GEOIDs in state-counties.json under its own name, every county's
commission in the shape the build requires, no fax number and the same floors
the build applies. It proves the file is what a build writes; it never proves
the directory has not moved since.

--save writes every page fetched into DIR, reading back any it already holds;
--offline reads them back instead of fetching.
"""

import collections
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
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)
from undeliverable import withhold  # noqa: E402  (FLEET_SHARED)

USER_AGENT = "districtry/1.0 (+https://districtry.com/wv/)"
HEADERS = {"User-Agent": USER_AGENT}
PACE_SECONDS = 1.0
ATTEMPTS = 3
RETRY_SECONDS = 5.0

HOST = "https://apps.sos.wv.gov"
INDEX = HOST + "/elections/Officials/"

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
OUT_NAME = "wv-county-officials.json"
COUNTIES_FILE = os.path.join(DEFAULT_OUT_DIR, "state-counties.json")

COMMISSIONER = "County Commissioner"
SCHOOL_BOARD = "Board of Education"
# Five-member commissions, by GEOID; every other county has three.
COMMISSION_SEATS = {"54003": 5, "54037": 5}
# The directory's titles for the other elected county offices, and the words
# the card prints for each, in the order it prints them.
OFFICER_TITLES = collections.OrderedDict([
    ("County Clerk", "County Clerk"),
    ("Circuit Clerk", "Circuit Clerk"),
    ("County Assessor", "Assessor"),
    ("County Sheriff", "Sheriff"),
    ("County Prosecuting Attorney", "Prosecuting Attorney"),
    ("County Surveyor", "Surveyor"),
])
# Counties carrying each office, as floors: every county carried every office
# on 2026-10-29 except Cabell's assessor.
OFFICER_FLOOR = 50
KNOWN_TITLES = set(OFFICER_TITLES) | {COMMISSIONER, SCHOOL_BOARD}

ROW_RE = re.compile(
    r'<a href="(/elections/Officials/Home/Details/[0-9a-f-]+)">\s*(.*?)\s*</a>\s*</td>\s*'
    r'<td>\s*<a href="[^"]*Office=[^"]*">\s*(.*?)\s*</a>', re.S)
DL_RE = re.compile(r"<dt>\s*(.*?)\s*</dt>\s*<dd>\s*(.*?)\s*</dd>", re.S)
PHONE_RE = re.compile(r"^\(?\d{3}\)?[-. ]?\d{3}-\d{4}(?:\s*(?:x|ext\.?)\s*\d+)?$", re.I)
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
# The directory fills an office nobody holds with the word "Vacant" where the
# name goes (the 2025 directory: the surveyor in 28 counties).
VACANT_RE = re.compile(r"^\s*vacant\.?\s*$", re.I)

_LAST = [0.0]


def fetch(url):
    require_robots_once(url, USER_AGENT, headers=HEADERS, label="wv-county-officials")
    last = None
    for attempt in range(ATTEMPTS):
        wait = PACE_SECONDS - (time.time() - _LAST[0])
        if wait > 0:
            time.sleep(wait)
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            _LAST[0] = time.time()
            return body
        except Exception as exc:  # noqa: BLE001
            _LAST[0] = time.time()
            last = exc
            time.sleep(RETRY_SECONDS * (attempt + 1))
    raise RuntimeError("could not read %s: %s" % (url, last))


class Pages(object):
    """Fetch, or read back, each page by a file name derived from its URL."""

    def __init__(self, offline=None, save=None):
        self.offline = offline
        self.save = save

    @staticmethod
    def name(url):
        return re.sub(r"[^A-Za-z0-9._-]+", "_", url.split("://", 1)[-1]) + ".html"

    def get(self, url):
        name = self.name(url)
        for d in (self.offline, self.save):
            if d and os.path.exists(os.path.join(d, name)):
                with open(os.path.join(d, name), encoding="utf-8") as f:
                    return f.read()
        if self.offline:
            raise RuntimeError("%s is not saved in %s" % (url, self.offline))
        body = fetch(url)
        if self.save:
            os.makedirs(self.save, exist_ok=True)
            with open(os.path.join(self.save, name), "w", encoding="utf-8") as f:
                f.write(body)
        return body


def text(fragment):
    s = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(html_module.unescape(s).split())


def county_geoids():
    with open(COUNTIES_FILE) as f:
        feats = json.load(f)["features"]
    out = {}
    for feat in feats:
        p = feat["properties"]
        out[str(p["BASENAME"]).lower()] = (str(p["GEOID"]), str(p["NAME"]))
    if len(out) != 55:
        raise RuntimeError("state-counties.json carries %d counties, not 55" % len(out))
    return out


def county_url(year, county):
    return INDEX + "?" + urllib.parse.urlencode({"Year": str(year), "County": county})


def pick_year(pages):
    """The newest year whose directory lists all 55 counties, and its counties."""
    idx = pages.get(INDEX)
    years = sorted({int(y) for y in re.findall(r"\?Year=(\d{4})", idx)}, reverse=True)
    if not years:
        raise RuntimeError("the directory's index offers no year")
    for year in years:
        page = pages.get(INDEX + "?Year=%d" % year)
        counties = sorted({html_module.unescape(c) for c in re.findall(
            r"\?Year=%d&amp;County=([^\"&]+)\"" % year, page)})
        if len(counties) == 55:
            return year, counties
        print("the %d directory lists %d counties, not 55; reading an earlier year"
              % (year, len(counties)), file=sys.stderr)
    raise RuntimeError("no year's directory lists all 55 counties")


def details(pages, href):
    page = pages.get(HOST + href)
    fields = {}
    for dt, dd in DL_RE.findall(page):
        key = text(dt)
        if key:
            fields[key] = text(dd)
    return fields


def build(pages):
    geoids = county_geoids()
    year, counties = pick_year(pages)
    read = datetime.date.today().isoformat()
    out = {}
    officer_counts = collections.Counter()
    for county in counties:
        key = county.lower()
        if key not in geoids:
            raise RuntimeError("the directory names a county %r that state-counties.json does not" % county)
        geoid, county_name = geoids[key]
        url = county_url(year, county)
        page = pages.get(url)
        rows = [(href, text(name), text(title)) for href, name, title in ROW_RE.findall(page)]
        if not rows:
            raise RuntimeError("%s: the directory page lists nobody" % county_name)
        for _, name, title in rows:
            if title not in KNOWN_TITLES:
                raise RuntimeError("%s: %s's title %r is not one this script knows"
                                   % (county_name, name, title))
        commissioners = [(h, n) for h, n, t in rows if t == COMMISSIONER]
        want = COMMISSION_SEATS.get(geoid, 3)
        if len(commissioners) != want:
            raise RuntimeError("%s lists %d county commissioners, not %d"
                               % (county_name, len(commissioners), want))
        officers = []
        for title, label in OFFICER_TITLES.items():
            held = [(h, n) for h, n, t in rows if t == title]
            if len(held) > 1:
                raise RuntimeError("%s lists %d %ss" % (county_name, len(held), title))
            if held:
                officers.append((label, held[0]))
                officer_counts[label] += 1
        people = []
        # A row the directory fills with "Vacant" is a vacancy, not a person:
        # it ships as `vacant: true` with no name and no contact. Its own page
        # is still read, because a number or address printed there and for a
        # person is an office's, never that person's own.
        for href, name in commissioners:
            people.append({"role": "seat", "name": name, "d": details(pages, href),
                           "vacant": bool(VACANT_RE.match(name))})
        for label, (href, name) in officers:
            people.append({"role": "officer", "office": label, "name": name,
                           "d": details(pages, href), "vacant": bool(VACANT_RE.match(name))})
        # who prints each telephone, e-mail address and mailing address
        phones = collections.defaultdict(list)
        emails = collections.defaultdict(list)
        addresses = collections.defaultdict(list)
        for i, p in enumerate(people):
            d = p["d"]
            phone = d.get("Telephone", "")
            if phone and PHONE_RE.match(phone):
                phones[re.sub(r"\D", "", phone)].append(i)
                p["phone"] = phone
            email = d.get("Email", "")
            # an address on a domain that does not exist cannot receive
            # mail, so it is withheld rather than corrected (undeliverable.py)
            if email and EMAIL_RE.match(email):
                email, _why = withhold(email, "%s, %s" % (county_name, p["name"]))
            if email and EMAIL_RE.match(email):
                emails[email.lower()].append(i)
                p["email"] = email
            street, city, zipc = d.get("Address", ""), d.get("City", ""), d.get("ZIP Code", "")
            if street and city:
                addr = "%s, %s, WV%s" % (street, city, (" " + zipc) if zipc else "")
                addresses[addr].append(i)
        seat_idx = {i for i, p in enumerate(people) if p["role"] == "seat" and not p["vacant"]}
        record = {"county": county_name, "body": county_name + " Commission",
                  "kind": "commission"}
        for table, field, board in ((phones, "phone", "boardPhone"), (emails, "email", "boardEmail")):
            for value, who in table.items():
                if len(who) < 2:
                    continue
                shown = people[who[0]][field]
                for i in who:
                    people[i].pop(field, None)
                if len(seat_idx.intersection(who)) >= 2 and board not in record:
                    record[board] = shown
        for addr, who in sorted(addresses.items(), key=lambda kv: -len(kv[1])):
            if len(seat_idx.intersection(who)) >= 2:
                record["boardAddress"] = addr
                break
        seats = []
        officers_out = []
        for p in people:
            row = {"vacant": True} if p["vacant"] else {"name": p["name"]}
            if p.get("phone") and not p["vacant"]:
                row["phone"] = p["phone"]
            if p.get("email") and not p["vacant"]:
                row["email"] = p["email"]
            if p["role"] == "seat":
                row = dict([("seat", "Commissioner"), ("countywide", True)] + list(row.items()))
                seats.append(row)
            else:
                row = dict([("office", p["office"])] + list(row.items()))
                officers_out.append(row)
        record["seats"] = seats
        record["officers"] = officers_out
        record["year"] = year
        record["source"] = "the West Virginia Secretary of State's %d directory of county officials" % year
        record["sourceUrl"] = url
        record["read"] = read
        out[geoid] = record
    if len(out) != 55:
        raise RuntimeError("%d counties read, not 55" % len(out))
    for label in OFFICER_TITLES.values():
        if officer_counts[label] < OFFICER_FLOOR:
            raise RuntimeError("only %d counties list a %s, below the floor of %d"
                               % (officer_counts[label], label, OFFICER_FLOOR))
    return out, year


def check():
    path = os.path.join(DEFAULT_OUT_DIR, OUT_NAME)
    with open(path) as f:
        data = json.load(f)
    geoids = county_geoids()
    problems = []
    want = {g: n for g, n in geoids.values()}
    if set(data) != set(want):
        problems.append("%s does not hold exactly the 55 counties' GEOIDs" % OUT_NAME)
    counts = collections.Counter()
    for geoid, rec in data.items():
        if want.get(geoid) and rec.get("county") != want[geoid]:
            problems.append("%s is filed as %r, not %r" % (geoid, rec.get("county"), want[geoid]))
        seats = rec.get("seats") or []
        if len(seats) != COMMISSION_SEATS.get(geoid, 3):
            problems.append("%s has %d commissioners" % (rec.get("county"), len(seats)))
        for s in seats + (rec.get("officers") or []):
            if not s.get("name") and s.get("vacant") is not True:
                problems.append("%s: a row names nobody and is not marked vacant" % rec.get("county"))
            if s.get("name") and VACANT_RE.match(s["name"]):
                problems.append("%s: %r stands where a name goes" % (rec.get("county"), s["name"]))
            if s.get("vacant") and (s.get("name") or s.get("phone") or s.get("email")):
                problems.append("%s: a vacancy carries a name or a contact" % rec.get("county"))
            if "fax" in json.dumps(s).lower():
                problems.append("%s: a row carries a fax number" % rec.get("county"))
        for o in rec.get("officers") or []:
            counts[o.get("office")] += 1
        for k in ("source", "sourceUrl", "read"):
            if not rec.get(k):
                problems.append("%s carries no %s" % (rec.get("county"), k))
    for label in OFFICER_TITLES.values():
        if counts[label] < OFFICER_FLOOR:
            problems.append("only %d counties carry a %s" % (counts[label], label))
    for p in problems:
        print("FAIL: %s" % p, file=sys.stderr)
    if problems:
        sys.exit(1)
    print("wv-county-officials: OK — 55 counties, %d commissioners, %d other officers"
          % (sum(len(r["seats"]) for r in data.values()),
             sum(len(r["officers"]) for r in data.values())))


def main(argv):
    args = list(argv)
    if "--check" in args:
        check()
        return
    save = offline = None
    if "--save" in args:
        i = args.index("--save")
        save = args[i + 1]
        del args[i:i + 2]
    if "--offline" in args:
        i = args.index("--offline")
        offline = args[i + 1]
        del args[i:i + 2]
    out_dir = args[0] if args else DEFAULT_OUT_DIR
    data, year = build(Pages(offline=offline, save=save))
    path = os.path.join(out_dir, OUT_NAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("Wrote %s (55 counties from the %d directory: %d commissioners, %d other officers)"
          % (path, year, sum(len(r["seats"]) for r in data.values()),
             sum(len(r["officers"]) for r in data.values())))


if __name__ == "__main__":
    main(sys.argv[1:])
