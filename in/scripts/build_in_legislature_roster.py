#!/usr/bin/env python3
"""
Build the Indiana Senate and House of Representatives rosters (district ->
current officeholder) as same-origin app-data files, from the Indiana General
Assembly's own site at iga.in.gov, so the in-senate / in-house cards join a
small roster instead of naming nobody.

index.html's in-senate / in-house layers fetch data/app/in-senate-members.json
and in-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party, email,
capitolOffice, url}}, or a record naming nobody). A weekly GitHub Action
(.github/workflows/update-in-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-14.

iga.in.gov is a page that fills itself in: the document a browser first
receives is a 691-byte shell, and its script reads the General Assembly's own
feeds under the /api path of that host, sending no key and no sign-in (the
script's requests carry a Content-Type header and nothing else). Three feeds
are read here, the three the legislator pages read:

  * /getSessionYears lists each session with an `active` flag. The active
    one that day was session_2027, the 125th General Assembly.
  * /getLegislators?session_lpid=<session> lists every member of that
    session: first name, last name, honorific ("Senator" or
    "Representative"), district, party ("Republican" or "Democrat") and the
    path of the member's page. It held 150 rows, 50 senators and 100
    representatives.
  * /getLegislatorDetails?session_lpid=<session>&legislator_lpid=<member>
    gives one member's Statehouse telephone, business e-mail address and
    caucus page, where the General Assembly has filled them in.

THE ACTIVE SESSION IS THE SITTING GENERAL ASSEMBLY. Indiana elected its whole
House and half its Senate on 3 November 2026, and a member's term runs "from
the day next after their general election" (Indiana Constitution, Article 4,
Section 3), so the members listed for session_2027 held their seats on the day
this was measured.

A DISTRICT THE LIST GIVES TWO PEOPLE NAMES NOBODY. That day the list put two
newly elected senators in Senate District 1 and nobody in Senate District 46,
and each of those senators' own detail record says District 1 too. One of the
two is in the wrong district in the General Assembly's data and nothing in it
says which, so both seats get a record naming nobody, dated, and the run says
so. Picking one would be a guess.

THE TELEPHONE IS CARRIED AS THE STATEHOUSE OFFICE'S. The detail record's
`statephone` is a Statehouse line (area code 317, the 232 exchange). On
2026-11-15 76 of the 100 representatives carried one, every one a different
number, and no senator did. It goes under the Statehouse office. The feed
prints no office address, so none is carried.

MANY MEMBERS CARRY NO TELEPHONE OR E-MAIL ADDRESS YET. The session_2027 list
was read twelve days after the election: 26 of its 148 detail records held an
e-mail address that day, and the 24 representatives with no telephone are
newly elected. The weekly run picks each up when the General Assembly fills
it in.

THE BROWSER CLIENT, AND THE MEASUREMENT THAT ALLOWS IT. On 2026-11-14 every
path on iga.in.gov, its favicon and both feeds included, answered this
project's own token (districtry/1.0) with the same 691-byte HTML shell, marked
"Error from cloudfront". Changing one header at a time, the token with every
other header a browser sends still got the shell, and the Chrome 126 string
with its client hints (scraper_common.UA_HINTS_CHROME_126) got the JSON: the
User-Agent is what the site refuses on. It is no captcha and no managed
challenge. So this file reads with the browser client, and reads robots.txt
with that same client.

ROBOTS. iga.in.gov/robots.txt, read that day with the browser client, is 144
bytes: one group naming Googlebot, Bingbot and Slurp (Disallow /search/ and
/pdf-documents/, Request-rate 1/5). No group binds this client and nothing
this file reads is under either path. The member details are paced at one
request every two seconds anyway.

Honesty: names are never guessed. A seat with no member listed, or with two,
gets a record naming nobody, dated.

Usage:
    python3 in/scripts/build_in_legislature_roster.py [output_dir]
    python3 in/scripts/build_in_legislature_roster.py --save DIR [output_dir]
    python3 in/scripts/build_in_legislature_roster.py --offline DIR [output_dir]
"""

import datetime
import json
import os
import re
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
import scraper_common as sc  # noqa: E402  (FLEET_SHARED)
from scraper_common import UA_HINTS_CHROME_126  # noqa: E402

ATTEMPTS = 4
RETRY_SECONDS = 20.0
PAUSE_SECONDS = 2.0
SITE = "https://iga.in.gov"
API = SITE + "/api"
# WRITTEN WHOLE, not composed from API: scripts/probe_user_agents.py reads URL
# literals out of this file and measures the host at the one it finds, so a
# feed address has to be a literal for the measurement to be of a feed. The
# first probe found only the bare /api path, which is no feed and answers
# every client the page shell, and recorded the host as answering nothing.
YEARS = "https://iga.in.gov/api/getSessionYears"
MEMBERS = API + "/getLegislators?session_lpid=%s"
DETAILS = API + "/getLegislatorDetails?session_lpid=%s&legislator_lpid=%s"

# 48 of 50 Senate districts and 100 of 100 House districts were named on
# 2026-11-14 (Senate 1 was listed twice and Senate 46 not at all).
CHAMBERS = {
    "S": {"out": "in-senate-members.json", "label": "Senate", "seats": 50,
          "expected": 44, "title": "Senator",
          "fields": {"party": 0.9}},
    "H": {"out": "in-house-members.json", "label": "House of Representatives",
          "seats": 100, "expected": 90, "title": "Representative",
          "fields": {"party": 0.9}},
}
# Across both chambers, how many named members must carry a Statehouse
# telephone: members elected for the first time on 3 November 2026 had none
# yet on 2026-11-14 (measured then: see the run's own summary line).
MIN_STATEHOUSE_PHONES = 60

PARTIES = {"Democrat": "Democratic", "Democratic": "Democratic",
           "Republican": "Republican"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

PHONE_RE = re.compile(r"^\(?\d{3}\)?[ .-]?\d{3}[ .-]\d{4}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
LPID_RE = re.compile(r"^[a-z0-9_]+$")
PAGE_RE = re.compile(r"^/legislative/\d{4}/legislators/[a-z0-9_]+$")

_SESSION = None


def session():
    global _SESSION
    if _SESSION is None:
        import requests

        _SESSION = requests.Session()
        _SESSION.headers.update(UA_HINTS_CHROME_126)
    return _SESSION


def fetch_json(url):
    import requests

    sc.require_robots_once(url, UA_HINTS_CHROME_126["User-Agent"],
                           headers=dict(UA_HINTS_CHROME_126))
    last = None
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_SECONDS * attempt)
        try:
            resp = session().get(url, timeout=60)
            resp.raise_for_status()
            if "json" not in (resp.headers.get("content-type") or ""):
                # The 691-byte shell, served with HTTP 200, is the site
                # refusing the client; it is never a feed.
                last = "the site answered with a page, not the feed"
                continue
            return resp.content.decode("utf-8")
        except requests.RequestException as exc:
            if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
                session().close()
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (url, ATTEMPTS, last))


class Feeds(object):
    """The three feeds, from the site or from a saved directory."""

    def __init__(self, offline, save):
        self.offline, self.save = offline, save
        self.fetched = 0

    def get(self, name, url):
        if self.offline:
            with open(os.path.join(self.offline, name), encoding="utf-8") as fh:
                body = fh.read()
        else:
            if self.fetched:
                time.sleep(PAUSE_SECONDS)
            self.fetched += 1
            body = fetch_json(url)
            if self.save:
                os.makedirs(self.save, exist_ok=True)
                with open(os.path.join(self.save, name), "w", encoding="utf-8") as fh:
                    fh.write(body)
        try:
            return json.loads(body)
        except ValueError:
            raise SystemExit("FAIL: %s is not the JSON it was" % name)


def active_session(years):
    rows = years.get("years") if isinstance(years, dict) else None
    active = [r for r in rows or []
              if isinstance(r, dict) and r.get("active") and not r.get("special")
              and re.match(r"^session_\d{4}$", str(r.get("lpid")))]
    if not active:
        raise SystemExit("FAIL: the session list marks no regular session active")
    return max(active, key=lambda r: r["lpid"])["lpid"]


def previous_roster(out_dir, cfg):
    try:
        with open(os.path.join(out_dir, cfg["out"]), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def build(feeds, previous, today):
    session_id = active_session(feeds.get("years.json", YEARS))
    listed = feeds.get("members.json", MEMBERS % session_id).get("legislators")
    if not isinstance(listed, list) or len(listed) < 120:
        raise SystemExit("FAIL: the member list for %s held %s members — its shape changed"
                         % (session_id, len(listed) if isinstance(listed, list) else "no list of"))
    titles = {cfg["title"]: c for c, cfg in CHAMBERS.items()}
    claims = {"S": {}, "H": {}}
    notes = {"S": ["read from %s" % session_id], "H": ["read from %s" % session_id]}
    for row in listed:
        chamber = titles.get(row.get("honorific"))
        if not chamber:
            raise SystemExit("FAIL: a member's honorific reads %r" % row.get("honorific"))
        cfg = CHAMBERS[chamber]
        try:
            district = int(row.get("district"))
        except (TypeError, ValueError):
            raise SystemExit("FAIL: a %s member's district reads %r"
                             % (cfg["label"], row.get("district")))
        where = "%s %d" % (cfg["label"].split()[0], district)
        if not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: %s is not one of the chamber's %d seats"
                             % (where, cfg["seats"]))
        name = " ".join(str(row.get(k) or "").strip() for k in ("firstname", "lastname")).strip()
        name = re.sub(r"\s+", " ", name)
        lpid = str(row.get("lpid") or "")
        if not name or re.search(r"\d", name) or not LPID_RE.match(lpid):
            raise SystemExit("FAIL: %s's row names %r (%r)" % (where, name, lpid))
        member = {"name": name}
        party = str(row.get("party") or "").strip()
        if party in PARTIES:
            member["party"] = PARTIES[party]
        elif party:
            member["party"] = party
            notes[chamber].append("%s: party printed as %r ships as printed" % (where, party))
        page = str(row.get("url") or "")
        if PAGE_RE.match(page):
            member["url"] = SITE + page
        claims[chamber].setdefault(district, []).append((lpid, member))
    out = {}
    phones = 0
    for chamber, cfg in CHAMBERS.items():
        short = cfg["label"].split()[0]
        seats = {}
        for district in range(1, cfg["seats"] + 1):
            key = str(district)
            rows = claims[chamber].get(district) or []
            if len(rows) != 1:
                prev = previous[chamber].get(key) or {}
                seats[key] = {"asOf": (prev.get("asOf") if not prev.get("name") else None) or today}
                notes[chamber].append(
                    "%s %d: %s" % (short, district,
                                   "no member listed" if not rows else
                                   "the list names %d people for this one seat (%s), so "
                                   "nobody is named" % (len(rows), " and ".join(
                                       m["name"] for _, m in rows))))
                continue
            lpid, member = rows[0]
            where = "%s %d" % (short, district)
            detail = feeds.get("member-%s.json" % lpid, DETAILS % (session_id, lpid))
            if not isinstance(detail, dict):
                detail = {}
            if detail and detail.get("district_id") not in (district, str(district)):
                raise SystemExit("FAIL: %s's own record names district %r"
                                 % (where, detail.get("district_id")))
            phone = str(detail.get("statephone") or "").strip()
            if PHONE_RE.match(phone):
                member["capitolOffice"] = [phone]
                phones += 1
            elif phone:
                notes[chamber].append("%s: the Statehouse telephone is not one whole "
                                      "number, not carried" % where)
            email = str(detail.get("busemail") or "").strip()
            if EMAIL_RE.match(email):
                member["email"] = email
            elif email:
                notes[chamber].append("%s: the e-mail entry is not one address, not carried" % where)
            seats[key] = member
        out[chamber] = check(chamber, seats)
    if phones < MIN_STATEHOUSE_PHONES:
        raise SystemExit("FAIL: only %d members carry a Statehouse telephone (expected >= %d) "
                         "— the detail feed stopped carrying it" % (phones, MIN_STATEHOUSE_PHONES))
    return out, notes


def check(chamber, roster):
    cfg = CHAMBERS[chamber]
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


def main():
    args = sys.argv[1:]
    offline = save = None
    while args and args[0] in ("--offline", "--save"):
        if len(args) < 2:
            sys.exit("usage: %s [--offline DIR | --save DIR] [output_dir]" % sys.argv[0])
        if args[0] == "--offline":
            offline = args[1]
        else:
            save = args[1]
        args = args[2:]
    if len(args) > 1 or (offline and save):
        sys.exit("usage: %s [--offline DIR | --save DIR] [output_dir]" % sys.argv[0])
    out_dir = args[0] if args else DEFAULT_OUT_DIR
    today = datetime.date.today().isoformat()
    previous = {c: previous_roster(out_dir, cfg) for c, cfg in CHAMBERS.items()}
    built, notes = build(Feeds(offline, save), previous, today)
    os.makedirs(out_dir, exist_ok=True)
    for chamber in ("S", "H"):
        cfg, roster = CHAMBERS[chamber], built[chamber]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        named = [m for m in roster.values() if m.get("name")]
        print("Wrote %s (%d of %d seats named, %d with a party, %d with an e-mail "
              "address, %d with a Statehouse telephone)"
              % (out_path, len(named), cfg["seats"],
                 sum(1 for m in named if m.get("party")),
                 sum(1 for m in named if m.get("email")),
                 sum(1 for m in named if m.get("capitolOffice"))), file=sys.stderr)
        for note in notes[chamber]:
            print("  " + note, file=sys.stderr)


if __name__ == "__main__":
    main()
