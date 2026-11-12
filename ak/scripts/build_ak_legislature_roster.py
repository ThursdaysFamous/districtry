#!/usr/bin/env python3
"""
Build the Alaska Senate and House of Representatives rosters (district ->
current officeholder) as same-origin app-data files, from the Alaska State
Legislature's own member pages at akleg.gov, so the ak-senate / ak-house cards
join a small roster instead of reaching another host at click time.

Alaska elects 20 senators from districts lettered A to T and 40
representatives from districts numbered 1 to 40; each Senate district is two
House districts. index.html's ak-senate / ak-house layers fetch
data/app/ak-senate-members.json and ak-house-members.json lazily on first
click and join them to the pre-built geometry: the Senate by district letter,
the House by number. This script writes the two rosters shaped for the
registerIlgaChamber factory ({district -> {name, party, email, phone, url}},
or a record naming nobody). A weekly GitHub Action
(.github/workflows/update-ak-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-12.

The Senate's and House's pages (akleg.gov/senate.php and akleg.gov/house.php)
list every sitting member of the 34th Legislature with a link to the member's
page, the member's party and district, a Capitol telephone, a toll-free
number and an e-mail link. That day they listed all 20 senators and all 40
representatives. The page hides each e-mail address behind Cloudflare's
e-mail protection link (/cdn-cgi/l/email-protection#...), which the page's
own script turns back into the address for every visitor; this script does
the same decoding, which reads the page as published, and carries an address
only at akleg.gov.

WHAT IS READ. The name, the member page link, and the Party, District, Phone
and Toll-Free lines of each member's entry, and the e-mail link. The Capitol
number ships unlabelled and the toll-free number labelled "toll-free", under
the fleet's rule of 2026-10-17; a number or address printed for two or more
members is an office's and is not carried. WHAT IS NEVER READ: each entry's
City line, which names the member's home town, the photograph, and the
leadership list at the top of each page, which repeats members with titles.

WHEN THE NEW LEGISLATURE SITS. The members elected on 3 November 2026 take
their seats when the 35th Legislature convenes in January 2027, when the
Legislature's pages list them and the weekly refresh opens a pull request.

ROBOTS. akleg.gov/robots.txt is read through scripts/robots_policy.py with
the User-Agent the fetches send, before the two requests this script makes.

Honesty: names are never guessed. A seat the page carries nobody for gets a
record naming nobody, dated; a seat listed twice stops the build.

Usage:
    python3 ak/scripts/build_ak_legislature_roster.py [output_dir]
    python3 ak/scripts/build_ak_legislature_roster.py --save DIR [output_dir]
    python3 ak/scripts/build_ak_legislature_roster.py --offline DIR [output_dir]
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


USER_AGENT = "districtry/1.0 (+https://districtry.com/ak/)"
PAGES = {"S": "https://akleg.gov/senate.php", "H": "https://akleg.gov/house.php"}

SENATE_DISTRICTS = {chr(c): 1 for c in range(ord("A"), ord("T") + 1)}

# 20 of 20 senators and 40 of 40 representatives were listed on 2026-11-12.
CHAMBERS = {
    "S": {"out": "ak-senate-members.json", "label": "Senate", "districts": SENATE_DISTRICTS,
          "expected": 18, "fields": {"party": 0.9, "email": 0.9, "phone": 0.8, "url": 0.9}},
    "H": {"out": "ak-house-members.json", "label": "House", "seats": 40,
          "expected": 36, "fields": {"party": 0.9, "email": 0.9, "phone": 0.8, "url": 0.9}},
}
PARTIES = {"Republican": "Republican", "Democrat": "Democratic",
           "Democratic": "Democratic", "Independent": "Independent",
           "Nonpartisan": "Nonpartisan", "Undeclared": "Undeclared",
           "Libertarian": "Libertarian", "Not Affiliated": "Not Affiliated"}
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@akleg\.gov$", re.I)
ENTRY_RE = re.compile(
    r'<li>\s*<a href="(http://www\.akleg\.gov/basis/Member/Detail/\d+\?code=\w+)">\s*'
    r'<img[^>]*>\s*<(?:strong|span) class="name"[^>]*>([^<]*)</(?:strong|span)></a>\s*'
    r'<dl>(.*?)</dl>', re.S)
PAIR_RE = re.compile(r'<dt>([^<]*)</dt>\s*<dd>([^<]*)</dd>')
PROTECTED_RE = re.compile(r'href="/cdn-cgi/l/email-protection#([0-9a-f]+)"')


def sources(raw):
    return [("senate.html", PAGES["S"], {}), ("house.html", PAGES["H"], {})]


def decode_email(hexed):
    """Cloudflare's e-mail protection: the first byte is a key XORed with
    every byte after it, the decoding the page's own script performs."""
    key = int(hexed[:2], 16)
    return "".join(chr(int(hexed[i:i + 2], 16) ^ key) for i in range(2, len(hexed), 2))


def parse(raw, notes):
    entries = []
    for chamber, name_file in (("S", "senate.html"), ("H", "house.html")):
        label = CHAMBERS[chamber]["label"]
        page = raw[name_file].decode("utf-8", "replace")
        found = ENTRY_RE.findall(page)
        if not found:
            raise SystemExit("FAIL: the %s page carries no member entry in the form this "
                             "build reads; read it and update ENTRY_RE" % label)
        for url, printed, block in found:
            lines = {}
            for key, value in PAIR_RE.findall(block):
                key = clean(key).rstrip(":").strip().lower().replace(" ", "-")
                if key == "city":
                    continue  # the member's home town: never read
                lines[key] = clean(value)
            district = lines.get("district", "").upper().lstrip("0")
            if chamber == "S" and district not in SENATE_DISTRICTS:
                raise SystemExit("FAIL: a Senate entry names district %r" % district)
            if chamber == "H" and not district.isdigit():
                raise SystemExit("FAIL: a House entry names district %r" % district)
            where = "%s %s" % (label, district)
            name = clean(printed)
            if not name or re.search(r"\d", name):
                raise SystemExit("FAIL: %s's entry names %r" % (where, name))
            member = {"name": name}
            party = lines.get("party", "")
            if party in PARTIES:
                member["party"] = PARTIES[party]
            elif party:
                raise SystemExit("FAIL: %s's party %r is one this builder has no name for"
                                 % (where, party))
            protected = PROTECTED_RE.search(block)
            email = decode_email(protected.group(1)) if protected else ""
            if EMAIL_RE.match(email):
                member["email"] = email
            elif email:
                notes.append("%s: an e-mail address off akleg.gov was not carried" % where)
            add_phones(member, labelled_phones(
                [(lines.get("phone", ""), ""), (lines.get("toll-free", ""), "toll-free")],
                where, notes))
            member["url"] = url
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
