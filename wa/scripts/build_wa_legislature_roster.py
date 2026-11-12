#!/usr/bin/env python3
"""
Build the Washington Senate and House rosters (district -> current
officeholders) as same-origin app-data files, from the Legislature's OWN
pages at leg.wa.gov, so the wa-senate / wa-house cards join a small roster
instead of reaching a third-party host at click time.

index.html's wa-senate / wa-house layers fetch data/app/wa-senate-members.json
and wa-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory: the Senate as {district -> {name,
party, capitolOffice, url}}, one senator per district, and the House as
{district -> {"seats": 2, "members": [two such rows]}}, because each of
Washington's 49 legislative districts elects one senator and TWO
representatives, to Position 1 and Position 2. A weekly GitHub Action
(.github/workflows/update-wa-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a human look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-11. The Legislature's member list,
https://leg.wa.gov/legislators/, prints one card per sitting member of both
chambers, each carrying the member's name ("Abbarno, Peter"), chamber, district
and party as attributes, and a link to the member's own page under
/legislators/member/. That day it listed 49 senators, one for each district,
and 97 representatives: two for every district but the 16th, which it gave one.
Each member's page prints the name with its title ("Representative Adam
Bernbaum"), the chamber, the party, the district and, for a representative,
the position ("District 24 - Position 1"), then the Olympia office as address
lines and its telephone.

WHAT IS READ, AND WHAT IS NEVER READ. From the list: each card's chamber,
district, party and member-page link. From each member's page: the name, the
district and position (checked against the list), and the Olympia office's
lines and telephone. The pages link each member's caucus website and an e-mail
form on app.leg.wa.gov, and print no e-mail address, so none is shipped; the
form's host refuses every client in its robots.txt and is never read. A
member's district office, which some pages print, is never read. The member
photographs are never fetched.

ROBOTS AND PACING. leg.wa.gov serves no robots.txt (HTTP 404 on 2026-11-11,
which RFC 9309 reads as allow-all), read through scripts/robots_policy.py with
the User-Agent the fetches send before the first fetch. The host is paced at
one request a second, so a run reads its 147 pages in about two and a half
minutes.

Honesty: names are never guessed. A House district the list gives fewer than
two members ships those it gives, dated; a Senate district with no card ships
as vacant, naming the list; a district carrying more members than it elects,
or two representatives holding one position, stops the build.

Usage:
    python3 wa/scripts/build_wa_legislature_roster.py [output_dir]
    python3 wa/scripts/build_wa_legislature_roster.py --save DIR [output_dir]
    python3 wa/scripts/build_wa_legislature_roster.py --offline DIR [output_dir]

--save writes every page fetched into DIR (legislators.html and one file per
member page under members/), reading back any it already holds; --offline
reads them back instead of fetching, for building and testing without the
network.
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

USER_AGENT = "districtry/1.0 (+https://districtry.com/wa/)"
MIN_PACE_SECONDS = 1.0
ATTEMPTS = 3
RETRY_SECONDS = 5.0

SITE = "https://leg.wa.gov"
LIST_URL = SITE + "/legislators/"

# Floors catch a truncated list or a layout change while tolerating real
# vacancies: 49 of 49 senators and 97 of 98 representatives were named on
# 2026-11-11.
CHAMBERS = {
    "S": {"out": "wa-senate-members.json", "label": "Senate", "seats": 49,
          "per_district": 1, "expected": 45, "list_chamber": "Senate",
          "page_chamber": "Senate", "title": "Senator",
          "chamber": "Washington State Senate", "name": "The Washington Legislature",
          # The share of named members carrying each field, floored below what
          # 2026-11-11 measured: every senator's page printed a party and an
          # Olympia office. A field falling under its floor is the Brown County
          # shape: the row count holds and the contact goes.
          "fields": {"party": 0.9, "capitolOffice": 0.9}},
    "H": {"out": "wa-house-members.json", "label": "House", "seats": 49,
          "per_district": 2, "expected": 90, "list_chamber": "House of Representatives",
          "page_chamber": "House of Representatives", "title": "Representative",
          "chamber": "Washington House of Representatives",
          "name": "The Washington Legislature",
          "fields": {"party": 0.9, "capitolOffice": 0.9}},
}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

CARD_RE = re.compile(
    r'<li role="listitem" data-id="(\d+)" data-name="([^"]*)" data-chamber="([^"]*)" '
    r'data-district="(\d+)" data-party="([^"]*)"[^>]*>(.*?)</li>', re.S)
# A slug carries the member's name as the Legislature spells it, apostrophe and all
# (T'wina Nobles is "t&#x27;wina-nobles", read 2026-11-11), so it is read whole and
# unescaped rather than held to letters and hyphens.
MEMBER_LINK_RE = re.compile(
    r'<a href="(/legislators/member/(?:[^"/?#&]|&#x?[0-9a-fA-F]+;|&[a-z]+;)+)" class="title">')
H1_RE = re.compile(r"<h1>([^<]+)</h1>")
INFO_RE = re.compile(r'<div><div><span>(Chamber|Party|District)</span></div>\s*<div><span>(.*?)</span></div></div>',
                     re.S)
DISTRICT_RE = re.compile(r"^District (\d+)(?: - Position ([12]))?$")
CONTACT_RE = re.compile(r'<ul role="list" class="contact-list">(.*?)</ul>', re.S)
BLOCK_RE = re.compile(r'<p class="text-lg">([^<]+)</p>\s*<p class="text-md contact-block-indent">(.*?)</p>', re.S)
PHONE_RE = re.compile(r"^\(\d{3}\) \d{3}-\d{4}$")
OLYMPIA_RE = re.compile(r"^Olympia, WA 985\d\d(?:-\d{4})?$")

_SESSION = None
_GATE = None
_PACER = None
_LAST = {}


def session():
    global _SESSION
    if _SESSION is None:
        import requests

        _SESSION = requests.Session()
        _SESSION.headers["User-Agent"] = USER_AGENT
    return _SESSION


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
            # The pages declare UTF-8.
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


def list_cards(page):
    """Every member card on the list, as (chamber, district, party, path)."""
    cards = []
    for _id, _name, chamber, district, party, body in CARD_RE.findall(page):
        link = MEMBER_LINK_RE.search(body)
        if not link:
            raise SystemExit("FAIL: a member card for district %s lacks its member-page "
                             "link — the list's layout changed" % district)
        cards.append((html_module.unescape(chamber), int(district),
                      html_module.unescape(party).strip(),
                      html_module.unescape(link.group(1))))
    if len(cards) < 130:
        raise SystemExit("FAIL: the member list yielded %d cards — its layout changed"
                         % len(cards))
    return cards


def read_member(page, cfg, district, path, notes):
    """The member's own page: name, position and Olympia office."""
    where = "%s %d" % (cfg["label"], district)
    h1 = H1_RE.search(page)
    title = cfg["title"] + " "
    if not h1 or not clean(h1.group(1)).startswith(title):
        raise SystemExit("FAIL: %s's page (%s) does not open with a %s's name — its "
                         "layout changed" % (where, path, cfg["title"]))
    name = clean(h1.group(1))[len(title):].strip()
    info = {k: clean(v) for k, v in INFO_RE.findall(page)}
    if info.get("Chamber") != cfg["page_chamber"]:
        raise SystemExit("FAIL: %s's page names the chamber %r" % (where, info.get("Chamber")))
    m = DISTRICT_RE.match(info.get("District", ""))
    if not m or int(m.group(1)) != district:
        raise SystemExit("FAIL: %s's page names %r, not district %d — the list and the "
                         "page disagree" % (where, info.get("District"), district))
    position = m.group(2)
    if cfg["per_district"] > 1 and not position:
        raise SystemExit("FAIL: %s: %s's page prints no position" % (where, name))
    member = {"name": name}
    if info.get("Party"):
        member["party"] = info["Party"]
    office = None
    contact = CONTACT_RE.search(page)
    blocks = BLOCK_RE.findall(contact.group(1)) if contact else []
    lines, phone = [], None
    for i, (label, body) in enumerate(blocks):
        label = clean(label)
        if label == "Olympia Office":
            lines = [clean(x) for x in re.split(r"<br\s*/?>", body) if clean(x)]
            # The telephone is the block straight after the office.
            if i + 1 < len(blocks) and clean(blocks[i + 1][0]) == "Phone":
                phone = clean(blocks[i + 1][1])
    if lines and OLYMPIA_RE.match(lines[-1]):
        office = [cfg["chamber"]] + lines
        if phone and PHONE_RE.match(phone):
            office.append(phone)
        elif phone:
            notes.append("%s: %s's Olympia telephone is not printed as one number, so it "
                         "was not carried" % (where, name))
    elif lines:
        notes.append("%s: %s's Olympia office does not end in an Olympia address line, so "
                     "it was not carried" % (where, name))
    else:
        notes.append("%s: %s's page prints no Olympia office" % (where, name))
    if office:
        member["capitolOffice"] = office
    member["url"] = SITE + path
    return member, position


def build_chamber(chamber, cards, pages, previous, today):
    cfg = CHAMBERS[chamber]
    by_district, notes = {}, []
    for card_chamber, district, party, path in cards:
        if card_chamber != cfg["list_chamber"]:
            continue
        where = "%s %d" % (cfg["label"], district)
        if not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: %s is not one of the chamber's %d districts"
                             % (where, cfg["seats"]))
        slug = re.sub(r"[^a-z0-9-]", "_", path.rstrip("/").rsplit("/", 1)[-1].lower())
        page = pages.get("members/%s.html" % slug, SITE + path)
        member, position = read_member(page, cfg, district, path, notes)
        if party and member.get("party") and party != member["party"]:
            raise SystemExit("FAIL: %s: the list says %s's party is %r and the page %r"
                             % (where, member["name"], party, member["party"]))
        by_district.setdefault(district, []).append((position, member))
    seats = {}
    for district in range(1, cfg["seats"] + 1):
        where = "%s %d" % (cfg["label"], district)
        listed = by_district.get(district, [])
        if len(listed) > cfg["per_district"]:
            raise SystemExit("FAIL: %s carries %d current members for %d seats"
                             % (where, len(listed), cfg["per_district"]))
        if cfg["per_district"] == 1:
            if listed:
                seats[district] = listed[0][1]
            else:
                prev = previous.get(str(district)) or {}
                seats[district] = {
                    "vacant": True,
                    "vacantWhy": "%s's member list names no senator for this district."
                                 % cfg["name"],
                    "sourceUrl": LIST_URL,
                    # The day the list was first read saying so, kept across runs.
                    "asOf": (prev.get("asOf") if prev.get("vacant") else None) or today,
                }
                notes.append("%s: no member card, shipped as vacant" % where)
            continue
        positions = [p for p, _ in listed]
        if len(set(positions)) != len(positions):
            raise SystemExit("FAIL: %s lists two representatives in Position %s"
                             % (where, positions[0]))
        members = [m for _, m in sorted(listed, key=lambda pm: pm[0])]
        record = {"seats": cfg["per_district"], "members": members}
        if len(members) < cfg["per_district"]:
            prev = previous.get(str(district)) or {}
            prev_short = len(prev.get("members") or []) < cfg["per_district"] and prev.get("asOf")
            record["asOf"] = prev.get("asOf") if prev_short else today
            record["sourceUrl"] = LIST_URL
            missing = sorted({"1", "2"} - set(positions))
            notes.append("%s: %d of %d members listed (no Position %s)"
                         % (where, len(members), cfg["per_district"], ", ".join(missing)))
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
    cards = list_cards(pages.get("legislators.html", LIST_URL))
    built = {}
    for chamber in ("S", "H"):
        previous = previous_roster(out_dir, CHAMBERS[chamber])
        seats, notes = build_chamber(chamber, cards, pages, previous, today)
        built[chamber] = (check(chamber, seats), notes)
    known = {CHAMBERS[c]["list_chamber"] for c in CHAMBERS}
    stray = sorted({c for c, _, _, _ in cards} - known)
    if stray:
        raise SystemExit("FAIL: the member list names a chamber this builder does not "
                         "know: %s" % ", ".join(stray))
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
        print("Wrote %s (%d of %d seats named, %d with an Olympia office)"
              % (out_path, len(named), cfg["seats"] * cfg["per_district"],
                 sum(1 for m in named if m.get("capitolOffice"))),
              file=sys.stderr)
        for note in notes:
            print("  " + note, file=sys.stderr)
    if _PACER is not None:
        for line in _PACER.report():
            print(line, file=sys.stderr)


if __name__ == "__main__":
    main()
