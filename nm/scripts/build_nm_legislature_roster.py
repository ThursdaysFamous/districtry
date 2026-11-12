#!/usr/bin/env python3
"""
Build the New Mexico Senate and House of Representatives rosters (district ->
current officeholder) as same-origin app-data files, from the New Mexico
Legislature's own member pages at nmlegis.gov, so the nm-senate / nm-house
cards join a small roster instead of reaching another host at click time.

index.html's nm-senate / nm-house layers fetch data/app/nm-senate-members.json
and nm-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party, email,
phone, url}}, or a record naming nobody). A weekly GitHub Action
(.github/workflows/update-nm-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-12.

The Legislature's list pages (nmlegis.gov/Members/Legislator_List?T=S for the
Senate and ?T=R for the House) print each sitting member's name, party letter
and district, and link the member's page (Legislator?SponCode=...). That day
they listed all 42 senators and 68 of the 70 representatives; House Districts
37 and 64, which the list did not carry, get a record naming nobody. Each
member's page prints the member's e-mail address (at nmlegis.gov for 101 of
the 110 that day; the other nine members give the Legislature an address of
their own, which the page prints in the same place) and, for some members, one
or two telephone numbers (27 members that day), "Phone" and "Alt Phone". This
script reads the list pages and then every member's page, one a second.

WHAT IS READ ON A MEMBER'S PAGE: the heading (to check the page is the
member's), the district link (to check it is the district the list gives), the
e-mail link and the two telephone fields. An address or number the page prints
beside the member ships on that member under the fleet's rule of 2026-10-17
(a government source printing an official's own contact beside that
official), the number with the label the page gives it; an address or number
printed for two or more members is not carried on any of them. WHAT IS NEVER READ: the address field (a district
office for some members, a home or business address for others), the
occupation, the photograph, and the legislative assistant's name, e-mail and
telephone, which belong to a staff member.

ROBOTS. www.nmlegis.gov/robots.txt (138 bytes) was read on 2026-11-12: its
group for every client disallows only /*.axd. It is read through
scripts/robots_policy.py with the User-Agent the fetches send.

Honesty: names are never guessed. A seat the list carries nobody for gets a
record naming nobody, dated; a member page naming another district stops the
build.

Usage:
    python3 nm/scripts/build_nm_legislature_roster.py [output_dir]
    python3 nm/scripts/build_nm_legislature_roster.py --save DIR [output_dir]
    python3 nm/scripts/build_nm_legislature_roster.py --offline DIR [output_dir]
"""

import datetime
import html
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

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
ATTEMPTS = 4
RETRY_SECONDS = 20.0


USER_AGENT = "districtry/1.0 (+https://districtry.com/nm/)"
HOST = "https://www.nmlegis.gov/Members/"
LISTS = {"S": HOST + "Legislator_List?T=S", "H": HOST + "Legislator_List?T=R"}
PAGE = HOST + "Legislator?SponCode=%s"
PAUSE = 1.0  # seconds between member pages; robots.txt states no delay for us

# 42 of 42 senators and 68 of 70 representatives were listed on 2026-11-12.
CHAMBERS = {
    "S": {"out": "nm-senate-members.json", "label": "Senate", "seats": 42,
          "expected": 38, "fields": {"party": 0.9, "email": 0.9, "url": 0.9}},
    "H": {"out": "nm-house-members.json", "label": "House", "seats": 70,
          "expected": 63, "fields": {"party": 0.9, "email": 0.9, "url": 0.9}},
}
PARTIES = {"D": "Democratic", "R": "Republican", "I": "Independent",
           "L": "Libertarian", "DTS": "Decline to State"}
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
CARD_RE = re.compile(
    r'href="Legislator\?SponCode=(\w+)".*?lblName_\d+"[^>]*>([^<]*)</span>'
    r'.*?lblDistrict_\d+">\s*District:\s*(\d+)\s*</span>', re.S)
NAME_RE = re.compile(r"^(.+?)\s*-\s*\((\w+)\)$")
FIELD = r'<[^>]*id="MainContent_formView%s_%s"[^>]*>(.*?)</'


def cards(raw, chamber):
    """[(sponsor code, name, party letter, district)] from a chamber's list."""
    page = raw["list-%s.html" % chamber].decode("utf-8", "replace")
    rows = []
    for code, printed, district in CARD_RE.findall(page):
        m = NAME_RE.match(clean(printed))
        if not m:
            raise SystemExit("FAIL: the %s list prints %r where a name and party "
                             "letter belong" % (CHAMBERS[chamber]["label"], clean(printed)))
        rows.append((code, m.group(1), m.group(2), str(int(district))))
    if not rows:
        raise SystemExit("FAIL: the %s list carries no member in the form this build "
                         "reads; read it and update CARD_RE" % CHAMBERS[chamber]["label"])
    return rows


def sources(raw):
    for chamber in ("S", "H"):
        yield "list-%s.html" % chamber, LISTS[chamber], {}
    for chamber in ("S", "H"):
        for code, _name, _party, _district in cards(raw, chamber):
            yield "member-%s.html" % code, PAGE % code, {}


def field(page, view, key):
    m = re.search(FIELD % (view, key), page, re.S)
    return m


def phone_label(page, key):
    """The words printed just before a telephone field's colon ("Phone:" reads
    as no label, "Capitol Phone:" as "capitol"). Only words of letters count,
    so the e-mail address or number printed before the label is never taken
    for it."""
    m = re.search(r'id="MainContent_formViewLegislator_%s"' % key, page)
    if not m:
        return ""
    before = clean(page[max(0, m.start() - 400):m.start()] + ">").rstrip(" <")
    if not before.endswith(":"):
        return ""
    words = []
    for word in reversed(before[:-1].split()):
        if not word.isalpha() or len(words) == 3:
            break
        words.insert(0, word)
    return " ".join(w for w in words if w.lower() != "phone").lower()


def parse(raw, notes):
    entries = []
    for chamber in ("S", "H"):
        label = CHAMBERS[chamber]["label"]
        for code, name, letter, district in cards(raw, chamber):
            where = "%s %s" % (label, district)
            if letter not in PARTIES:
                raise SystemExit("FAIL: %s's party letter %r is one this builder has "
                                 "no name for" % (where, letter))
            member = {"name": name, "party": PARTIES[letter]}
            page = raw["member-%s.html" % code].decode("utf-8", "replace")
            heading = field(page, "LegislatorName", "lblLegislatorName")
            surname = name.split()[-1]
            if not heading or surname.lower() not in clean(heading.group(1)).lower():
                raise SystemExit("FAIL: %s's page (%s) does not name %s" % (where, code, name))
            linked = field(page, "Legislator", "linkDistrict")
            if not linked or clean(linked.group(1)) != district:
                raise SystemExit("FAIL: %s's page (%s) names district %r"
                                 % (where, code, clean(linked.group(1)) if linked else None))
            mail = field(page, "Legislator", "linkEmail")
            email = clean(mail.group(1)) if mail else ""
            if EMAIL_RE.match(email):
                member["email"] = email
            elif email:
                notes.append("%s: the e-mail field holds something that is not an address"
                             % where)
            pairs = []
            for key in ("lblPhone1", "lblPhone2"):
                value = field(page, "Legislator", key)
                if value and clean(value.group(1)):
                    pairs.append((clean(value.group(1)), phone_label(page, key)))
            add_phones(member, labelled_phones(pairs, where, notes))
            member["url"] = PAGE % code
            entries.append((chamber, district, member))
    shared(entries, notes)
    return entries


def shared(entries, notes):
    """Drop an address or number printed for two or more members: it is an
    office's, not a member's."""
    seen = {}
    for _chamber, _district, member in entries:
        for value in [member.get("email", "").lower(), member.get("phone")] + \
                [p for p in member.get("phonesExtra", [])]:
            if value:
                digits = re.sub(r"\D", "", value) if "@" not in value else value
                seen[digits] = seen.get(digits, 0) + 1
    for chamber, district, member in entries:
        where = "%s %s" % (CHAMBERS[chamber]["label"], district)
        if member.get("email") and seen[member["email"].lower()] > 1:
            del member["email"]
            notes.append("%s: an e-mail address printed for two or more members was "
                         "not carried" % where)
        numbers = [member.get("phone")] + list(member.get("phonesExtra", []))
        kept = [n for n in numbers if n and seen[re.sub(r"\D", "", n)] == 1]
        if len(kept) != len([n for n in numbers if n]):
            notes.append("%s: a telephone printed for two or more members was not carried"
                         % where)
            member.pop("phone", None)
            member.pop("phonesExtra", None)
            add_phones(member, kept)


def clean(text):
    """One line of text as a reader sees it: entities decoded, tags and runs
    of whitespace collapsed."""
    text = re.sub(r"<[^>]+>", " ", str(text or ""))
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def normal_phone(text):
    """A ten-digit number as NNN-NNN-NNNN, whatever punctuation it was printed
    with, or None when the text is not one telephone number."""
    if re.search(r"[A-Za-z]", text or ""):
        return None
    digits = re.sub(r"\D", "", text or "")
    if len(digits) == 11 and digits[0] == "1":
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])


def labelled_phones(pairs, where, notes):
    """[(printed number, label or "")] -> the member's telephones, one entry
    per number, carrying every label it was printed under."""
    labels, order = {}, []
    for printed, label in pairs:
        printed = clean(printed)
        if not printed:
            continue
        number = normal_phone(printed)
        if not number:
            notes.append("%s: a telephone printed as %r is not one number, not carried"
                         % (where, printed))
            continue
        if number not in labels:
            labels[number] = []
            order.append(number)
        if label and label not in labels[number]:
            labels[number].append(label)

    def joined(words):
        return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]
    return [("%s %s" % (joined(labels[n]), n)) if labels[n] else n for n in order]


def add_phones(member, numbers):
    if numbers:
        member["phone"] = numbers[0]
        if numbers[1:]:
            member["phonesExtra"] = numbers[1:]


_SESSION = None
_GATE = None
_PACER = None
_ASKED = set()
_LAST = {}


def session():
    global _SESSION, _GATE, _PACER
    if _SESSION is None:
        import requests

        _SESSION = requests.Session()
        _SESSION.headers["User-Agent"] = USER_AGENT
        _GATE = RobotsGate(_SESSION, USER_AGENT)
        _PACER = HostPacer(_GATE)
    return _SESSION


def fetch(url, data=None, headers=None):
    """One request, after robots.txt is read with the client that sends it;
    a stated Crawl-delay is honoured by the shared HostPacer."""
    import requests

    session()
    host = urllib.parse.urlsplit(url).netloc
    ok, why = _GATE.allows(url)
    if host not in _ASKED:
        _ASKED.add(host)
        print("robots.txt %s: %s" % (host, why), file=sys.stderr)
    if not ok:
        raise SystemExit("FAIL: robots.txt refuses %s (%s)" % (url, why))
    # A builder that fetches many pages from one host sets PAUSE (seconds),
    # on top of any Crawl-delay the host states.
    wait = globals().get("PAUSE", 0.0) - (time.time() - _LAST.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    last = None
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_SECONDS * attempt)
        try:
            _LAST[host] = time.time()
            with _PACER.hold(url):
                if data is None:
                    resp = _SESSION.get(url, headers=headers, timeout=60)
                else:
                    resp = _SESSION.post(url, data=data, headers=headers, timeout=60)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as exc:
            if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
                _SESSION.close()
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (url, ATTEMPTS, last))


def load(offline, save):
    """Every source, by the name it is saved under. sources() is handed the
    sources read so far, so a later address can depend on an earlier answer."""
    raw = {}
    for name, url, opts in sources(raw):
        if offline:
            with open(os.path.join(offline, name), "rb") as fh:
                raw[name] = fh.read()
            continue
        raw[name] = fetch(url, **opts)
        if save:
            os.makedirs(save, exist_ok=True)
            with open(os.path.join(save, name), "wb") as fh:
                fh.write(raw[name])
    return raw


def district_keys(cfg):
    if "districts" in cfg:
        return list(cfg["districts"])
    return [str(d) for d in range(1, cfg["seats"] + 1)]


def seats_in(cfg, key):
    if "districts" in cfg:
        return cfg["districts"][key]
    return cfg.get("per_district", 1)


def multi(cfg):
    return "districts" in cfg or cfg.get("per_district", 1) > 1


def previous_roster(out_dir, cfg):
    try:
        with open(os.path.join(out_dir, cfg["out"]), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def build(entries, previous, today):
    """Seat every listed member, and give every seat nobody is listed for a
    dated record naming nobody. The date is carried forward from the last
    roster while the same seat stays short, so a weekly rerun changes nothing
    until the source does."""
    listed = {c: {} for c in CHAMBERS}
    notes = {c: [] for c in CHAMBERS}
    for chamber, key, member in entries:
        cfg = CHAMBERS[chamber]
        where = "%s %s" % (cfg["label"], key)
        if key not in district_keys(cfg):
            raise SystemExit("FAIL: %s is not one of the chamber's districts" % where)
        members = listed[chamber].setdefault(key, [])
        if len(members) >= seats_in(cfg, key):
            raise SystemExit("FAIL: %s lists more members than the %d seat(s) it elects"
                             % (where, seats_in(cfg, key)))
        if any(m["name"] == member["name"] for m in members):
            raise SystemExit("FAIL: %s lists %s twice" % (where, member["name"]))
        members.append(member)
    out = {}
    for chamber, cfg in CHAMBERS.items():
        roster = {}
        for key in district_keys(cfg):
            members = listed[chamber].get(key, [])
            seats = seats_in(cfg, key)
            prev = previous[chamber].get(key) or {}
            if multi(cfg):
                rec = {"seats": seats, "members": members}
                if len(members) < seats:
                    same = ([m.get("name") for m in prev.get("members") or []]
                            == [m.get("name") for m in members])
                    rec["asOf"] = (prev.get("asOf") if same else None) or today
                    notes[chamber].append("%s %s: %d of %d members listed"
                                          % (cfg["label"], key, len(members), seats))
            elif members:
                rec = members[0]
            else:
                rec = {"asOf": (prev.get("asOf") if not prev.get("name") else None) or today}
                notes[chamber].append("%s %s: no member listed" % (cfg["label"], key))
            roster[key] = rec
        out[chamber] = check(chamber, roster)
    return out, notes


def named_members(cfg, roster):
    if multi(cfg):
        return [m for rec in roster.values() for m in rec.get("members") or []]
    return [m for m in roster.values() if m.get("name")]


def check(chamber, roster):
    cfg = CHAMBERS[chamber]
    named = named_members(cfg, roster)
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
    parse_notes = []
    entries = parse(load(offline, save), parse_notes)
    previous = {c: previous_roster(out_dir, cfg) for c, cfg in CHAMBERS.items()}
    built, notes = build(entries, previous, today)
    os.makedirs(out_dir, exist_ok=True)
    for chamber, cfg in CHAMBERS.items():
        roster = built[chamber]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        named = named_members(cfg, roster)
        total = sum(seats_in(cfg, k) for k in district_keys(cfg))
        print("Wrote %s (%d of %d seats named, %d with a party, %d with an e-mail "
              "address, %d with a telephone)"
              % (out_path, len(named), total,
                 sum(1 for m in named if m.get("party")),
                 sum(1 for m in named if m.get("email")),
                 sum(1 for m in named if m.get("phone"))), file=sys.stderr)
        for note in notes[chamber]:
            print("  " + note, file=sys.stderr)
    for note in parse_notes:
        print("  " + note, file=sys.stderr)


if __name__ == "__main__":
    main()
