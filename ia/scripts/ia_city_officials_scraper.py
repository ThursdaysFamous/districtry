#!/usr/bin/env python3
"""
Scrape stage 1: the elected officials of the Iowa cities whose own pages a
machine can read, cached for build_ia_city_officials.py (stage 2).

THIS IS A SHORT LIST ON PURPOSE, AND THE MEASUREMENT BEHIND IT IS THE POINT.
On 2026-09-04 all 532 Iowa cities that publish a website were swept for a
council roster. SIXTEEN yielded one; five of those cleared every check. That
is 1.7% of Iowa's 939 cities, and 407 of those cities publish no website at
all, which is the ceiling before any markup question is asked. The full
measurement lives in the `ia-municipal-officeholders` gap record's blocker.

So this file is NOT the beginning of a statewide roster and must never be
described as one. It is five cities that happen to publish readably, added
because a reader in one of them is better served than by a card that names
nobody -- and the gap stays open for the other 932 (939 less these five, Des Moines
and Waterloo, whose ward cards name theirs).

EVERY CITY HERE IS AT-LARGE, WHICH IS WHY NO LAYER SHIPS WITH THEM.
All five elect a mayor plus five council members, none of them by ward
(measured: not one carries a ward or district in its published role). The
fleet's at-large rule -- "a body elected by the whole unit adds zero
point-discrimination; it rides the unit's identity card, never a polygon
layer" -- puts them on the City card. Des Moines and Waterloo are the two
Iowa cities that DO elect by ward, and they are the `city-ward` layer.

TWO CONVENTIONS, AND THE PLATFORM DOES NOT PREDICT WHICH
----------------------------------------------------------
Four of the five write `Name, Role`; Tiffin writes `Role: Name`. That split
is not a property of the content system: Des Moines, Waterloo and Norwalk all
run the SAME system and need three different parsers. So each city carries its
convention explicitly in CITIES below rather than having it guessed, and a
city whose page changes convention fails its count gate rather than silently
returning nothing.

WHAT EACH CITY'S GATE IS
-------------------------
`seats` is what the city itself publishes, counted at first build, and the
scrape refuses on any other number. It is a measurement of the page, not a
target: Iowa Code 372.4 seats a mayor and five council members in the
mayor-council cities here, and all five pages agree, but the gate is the page.

A NAME MUST NOT APPEAR TWICE. That is the Waterloo lesson, earned on a city
NOT in this list: its page repeats every member in a bio-link anchor, two of
those anchors disagree with the member's own line, and one is a misspelling
unique enough to survive a dedupe. A plausible seat count does NOT catch it --
Waterloo parses to eight council members, which is an entirely ordinary
council. The duplicate check is what catches it, so it runs here on every city.

ROBOTS IS CONSULTED BEFORE EVERY FETCH, AND ONE OF THE FIVE SAYS NO.
Added 2026-09-05 after review. `cityofpalo.com/robots.txt` names Googlebot,
bingbot, ia_archiver, archive.org_bot, W3C-checklink and CCBot, allows each of
them everything but /admin/ and /manager/ -- and ends `User-agent: * /
Disallow: /`. It reads as permissive for four hundred bytes and refuses in the
last two lines, which is exactly why this is now a machine check and not a
human reading a file. Palo is therefore SKIPPED: its page is not requested at
all, its six officials leave the card, and the entry stays in CITIES so the
check runs weekly and the city re-enters by itself if its file changes. The
other four allow (moraviaiowa.com serves a permissive file; Norwalk, Riverside
and Tiffin serve none, which RFC 9309 makes allow-all). See
`ia/scripts/robots_gate.py`.

Usage:
    python3 ia/scripts/ia_city_officials_scraper.py
"""

import html as html_mod
import json
import os
import re
import sys

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)          # robots_gate is a sibling, not a package
from robots_gate import RobotsGate  # noqa: E402

CACHE_DIR = os.path.join(HERE, ".cache")
OUT_PATH = os.path.join(CACHE_DIR, "ia_city_officials.json")
HEADERS = {"User-Agent": "districtry/1.0 (+https://districtry.com/ia/)",
           "Accept": "text/html,application/xhtml+xml"}

# geoid -> the city's own council page, its naming convention, and the number
# of seats ITS OWN PAGE publishes. Keyed by 7-digit TIGER place GEOID, the key
# the City card already reads.
CITIES = [
    {"geoid": "1953985", "name": "Moravia", "convention": "fwd", "seats": 6,
     "url": "https://moraviaiowa.com/city-services/council-mayor/"},
    {"geoid": "1957675", "name": "Norwalk", "convention": "fwd", "seats": 6,
     "url": "https://www.norwalk.iowa.gov/government/mayor___city_council.php"},
    {"geoid": "1961230", "name": "Palo", "convention": "fwd", "seats": 6,
     "url": "https://cityofpalo.com/council"},
    {"geoid": "1967440", "name": "Riverside", "convention": "fwd", "seats": 6,
     "url": "https://riversideiowa.gov/government/mayor_and_council/"},
    {"geoid": "1978060", "name": "Tiffin", "convention": "rev", "seats": 6,
     "url": "https://www.tiffin-iowa.org/city_government/city_council.php"},
]

ROLE = (r"(?:Mayor\s*Pro[-\s]?Tem(?:pore)?|Mayor|Council\s*(?:Member|man|woman|person)"
        r"(?:\s*At[-\s]?Large)?|At[-\s]?Large\s*Council\s*\w*)")
NAME = r"[A-Z][A-Za-z.'\-]*(?:\s+[A-Za-z.'\-]+){0,3}"
FWD = re.compile(r"^(?P<name>%s)\s*[,–-]\s*(?P<role>%s)\b" % (NAME, ROLE), re.I)
REV = re.compile(r"^(?P<role>%s)\s*[:\-–]\s*(?P<name>%s)\s*$" % (ROLE, NAME), re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.\w{2,}")
PHONE = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
MAYOR_ONLY = re.compile(r"(?i)^mayor$")


def text_lines(page):
    """Tags to text, with <br>, <hr> and block ends becoming LINE BREAKS first.

    Order matters, as it does in every scraper in this instance: strip tags
    first and a member's name, phone and e-mail collapse into one unsplittable
    string on the pages that separate them with <br> alone.

    A mailto anchor is rewritten to `text address` BEFORE tags are stripped.
    Wrapping the address in angle brackets instead -- the obvious thing -- makes
    the tag stripper eat it as though it were a tag, which silently returned
    zero e-mails for a whole city while the names parsed perfectly.
    """
    t = re.sub(r"(?is)<(script|style|nav|footer)[^>]*>.*?</\1>", " ", page)
    t = re.sub(r'<a[^>]*href="mailto:([^"?]+)[^"]*"[^>]*>(.*?)</a>', r" \2 \1 ", t,
               flags=re.I | re.S)
    t = re.sub(r"<br\s*/?>|<hr\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|h[1-6]|div|li|td|tr|strong|span|b|em|a|dt|dd)>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html_mod.unescape(t).replace("\xa0", " ")
    return [re.sub(r"\s+", " ", line).strip() for line in t.split("\n") if line.strip()]


def field_reach(lines, hits, pattern):
    """How many lines past its own name line THIS PAGE puts this field.

    Measured only on the members the NEXT member bounds, so the page states the
    distance rather than the reader guessing one. Returns 0 where the page
    publishes the field for nobody, which reads only a member's own name line --
    the one line that is unambiguously theirs.
    """
    offsets = []
    for n in range(len(hits) - 1):
        start, stop = hits[n][0], hits[n + 1][0]
        for k in range(start, stop):
            if pattern.search(lines[k]):
                offsets.append(k - start)
                break
    return max(offsets) if offsets else 0


def parse(page, convention):
    lines = text_lines(page)
    rx = FWD if convention == "fwd" else REV
    hits = [(i, m) for i, line in enumerate(lines) for m in [rx.match(line)] if m]
    # Every member's scan is bounded by the NEXT member, so nothing below the
    # roster can donate a contact detail to somebody. THE LAST MEMBER HAS NO
    # NEXT ONE, and the fixed twelve-line window that used to stand in for one
    # is what shipped Riverside's city-hall number as council member Lois
    # Schneider's phone. Her row publishes no phone at all: measured 2026-09-18
    # her name is line 57 of riversideiowa.gov's 70, the page's `<div
    # id="footer">` opens at 62, and `(319) 648-3501` sits at 65 -- eight lines
    # below her, inside a twelve-line window and outside any bound this page
    # states. text_lines() strips the <footer> ELEMENT and not a div named for
    # one, so nothing else caught it either.
    #
    # So the last member is bounded by the distance THIS PAGE puts between a
    # name line and that field, PER FIELD, because the two differ -- measured
    # 2026-09-18, phone then e-mail: Moravia 1 and 2, Norwalk 3 and 1,
    # Riverside 1 and 2, Tiffin 3 and 5. One window for both fields would have
    # been wrong about one of them on three of the four pages.
    #
    # The bound is deliberately only applied where the page gives no next
    # member, which is where the defect is. It can drop a real value if a page
    # ever sets its LAST member's contact further out than any other member's,
    # and that is the safe direction: an omission trips MIN_PHONES in the
    # builder and is visible, where an invented number is not.
    reach = {"email": field_reach(lines, hits, EMAIL),
             "phone": field_reach(lines, hits, PHONE)}
    out = []
    for n, (i, m) in enumerate(hits):
        rec = {"name": m.group("name").strip(), "role": m.group("role").strip()}
        for field, pattern in (("email", EMAIL), ("phone", PHONE)):
            stop = (hits[n + 1][0] if n + 1 < len(hits)
                    else min(len(lines), i + reach[field] + 1))
            found = pattern.search(" ".join(lines[i:stop]))
            if found:
                rec[field] = found.group(0)
        out.append(rec)
    return out


# ---------------------------------------------------------------- self-test
# Fixtures are built from string parts rather than written as whole URLs: this
# file's URL literals are the inventory `scripts/probe_user_agents.py` probes,
# and an invented host in a test fixture reads there as a host nobody measured.
_FOOTER = ('<div id="footer"><b>City of Example</b><br>1 Main St.<br>'
           'Example, Iowa 50000<br>(319) 555-9999</div>')


def _member(name, role, *rows):
    return "<p>" + name + ", " + role + "<br>" + "<br>".join(rows) + "</p>"


def _page(*members):
    return "<div>" + "".join(members) + "</div>" + _FOOTER


def _selftest():
    """Offline checks on the bound parse() puts on the LAST member.

    Every case is about that member, because they are the one no next member
    bounds and the one the old fixed twelve-line window got wrong. Each case
    that expects NO phone also asserts the old window WOULD have taken the
    footer's -- a fixture that does not reproduce the defect proves nothing.
    """
    failures, ran = [], []

    def check(cond, msg):
        ran.append(msg)
        print(("  ok   " if cond else "  FAIL ") + msg)
        if not cond:
            failures.append(msg)

    def old_window_phone(page, convention):
        """What the retired `i + 12` bound would have given the last member."""
        lines = text_lines(page)
        rx = FWD if convention == "fwd" else REV
        hits = [i for i, ln in enumerate(lines) for m in [rx.match(ln)] if m]
        i = hits[-1]
        found = PHONE.search(" ".join(lines[i:min(len(lines), i + 12)]))
        return found.group(0) if found else None

    # 1. THE RIVERSIDE SHAPE. Only the mayor publishes a phone; the last member
    #    publishes an e-mail and no phone, and a footer below carries the city
    #    hall number. Measured on riversideiowa.gov 2026-09-18: phone reach 1,
    #    e-mail reach 2.
    riverside = _page(
        _member("Pat Doe", "Mayor", "(319) 555-0101", "mayor@example.gov"),
        _member("Ann Roe", "Council Person", "aroe@example.gov"),
        _member("Bo Fay", "Council Person", "bfay@example.gov"),
        _member("Cal Ives", "Council Person", "cives@example.gov"),
        _member("Dee Jann", "Council Person", "djann@example.gov"),
        _member("Lee Poe", "Council Person", "lpoe@example.gov"))
    recs = parse(riverside, "fwd")
    check(len(recs) == 6, "riverside shape: 6 members parsed (got %d)" % len(recs))
    check(recs[-1]["name"] == "Lee Poe", "riverside shape: last member is Lee Poe")
    check("phone" not in recs[-1],
          "riverside shape: last member takes NO phone from the footer (got %r)"
          % recs[-1].get("phone"))
    check(recs[-1].get("email") == "lpoe@example.gov",
          "riverside shape: last member keeps their own e-mail")
    check(recs[0].get("phone") == "(319) 555-0101",
          "riverside shape: the one published phone still reaches the mayor")
    check(old_window_phone(riverside, "fwd") == "(319) 555-9999",
          "riverside shape: the retired 12-line window DID take the footer number")

    # 2. TWO FIELDS AT DIFFERENT OFFSETS -- the Tiffin shape, where the e-mail
    #    sits further from the name than the phone. One window for both fields
    #    is wrong about one of them.
    tiffin = _page(*[
        _member(n, "Council Member", "First Elected: 2020",
                "Phone: 515-555-01%02d" % k, "Email: c%d@example.gov" % k)
        for k, n in enumerate(["Pat Doe", "Ann Roe", "Bo Fay", "Cal Ives",
                               "Dee Jann", "Lee Poe"])])
    recs = parse(tiffin, "fwd")
    check(recs[-1].get("phone") == "515-555-0105",
          "split offsets: last member keeps their OWN phone (got %r)"
          % recs[-1].get("phone"))
    check(recs[-1].get("email") == "c5@example.gov",
          "split offsets: last member keeps their own e-mail, further out than the phone")

    # 3. A PAGE THAT PUBLISHES NO PHONE FOR ANYONE gives the last member none,
    #    though a footer below carries one. Reach falls back to the member's own
    #    name line, which is the only line unambiguously theirs.
    nophones = _page(*[
        _member(n, "Council Person", "%s@example.gov" % n.split()[0].lower())
        for n in ["Pat Doe", "Ann Roe", "Bo Fay", "Cal Ives", "Dee Jann", "Lee Poe"]])
    recs = parse(nophones, "fwd")
    check(all("phone" not in r for r in recs),
          "no phones published: nobody gets one, last member included")
    check(recs[-1].get("email") == "lee@example.gov",
          "no phones published: the last member's e-mail still reaches them")
    check(old_window_phone(nophones, "fwd") == "(319) 555-9999",
          "no phones published: the retired window DID take the footer number")

    # 4. THE BOUND MUST NOT DROP A REAL VALUE. Where every member including the
    #    last publishes a phone at the page's own offset, every one survives --
    #    the Moravia and Norwalk shape, and the arm that fails if the bound is
    #    made tighter than the page.
    moravia = _page(*[
        _member(n, "Councilman", "641-555-01%02d" % k, "m%d@example.gov" % k)
        for k, n in enumerate(["Pat Doe", "Ann Roe", "Bo Fay", "Cal Ives",
                               "Dee Jann", "Lee Poe"])])
    recs = parse(moravia, "fwd")
    check(sum(1 for r in recs if r.get("phone")) == 6,
          "every member publishes one: all 6 phones survive (got %d)"
          % sum(1 for r in recs if r.get("phone")))
    check(recs[-1].get("phone") == "641-555-0105",
          "every member publishes one: the last is their own, not the footer's")

    # 5. ONE MEMBER ALONE states no spacing at all, so nothing past their own
    #    name line is read.
    single = _page(_member("Pat Doe", "Mayor", "(319) 555-0101", "mayor@example.gov"))
    recs = parse(single, "fwd")
    check(len(recs) == 1 and "phone" not in recs[0],
          "single member: no spacing stated, so nothing below the name line is read")

    print("%d checks, %d failed" % (len(ran), len(failures)))
    return 1 if failures else 0


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    session = requests.Session()
    gate = RobotsGate(session, HEADERS["User-Agent"])
    payload, refused = {}, []
    for city in CITIES:
        allowed, why = gate.allows(city["url"])
        if not allowed:
            # The city's own robots.txt refuses this agent, so its page is
            # never requested. The entry STAYS in CITIES: the check runs every
            # week, so a city that changes its file re-enters by itself.
            refused.append((city["name"], why))
            print("  %-11s SKIPPED — robots.txt refuses districtry (%s)"
                  % (city["name"], why), file=sys.stderr)
            continue
        r = session.get(city["url"], headers=HEADERS, timeout=45)
        r.raise_for_status()
        recs = parse(r.text, city["convention"])

        if len(recs) != city["seats"]:
            raise SystemExit(
                "%s: parsed %d officials, its page publishes %d. That is either the "
                "page changing shape or the city changing its council, and both need "
                "reading before anything ships." % (city["name"], len(recs), city["seats"]))

        names = [x["name"] for x in recs]
        dupes = sorted({n for n in names if names.count(n) > 1})
        if dupes:
            raise SystemExit(
                "%s: these names appear more than once: %s. A repeated name means the "
                "page now names each member twice -- and the second naming is not always "
                "spelled the same, which is how a misspelt councilman would ship. Read "
                "the page." % (city["name"], ", ".join(dupes)))

        mayors = [x for x in recs if MAYOR_ONLY.match(x["role"])]
        if len(mayors) != 1:
            raise SystemExit(
                "%s: found %d plain 'Mayor' records, expected exactly one (a Mayor Pro "
                "Tem is a council member and is not one)." % (city["name"], len(mayors)))

        missing = [x["name"] for x in recs if not x.get("email")]
        if missing:
            raise SystemExit(
                "%s: no e-mail for %s. Every one of this city's published officials "
                "carried one at first build, so a shortfall is the page changing rather "
                "than a person declining to publish." % (city["name"], ", ".join(missing)))

        payload[city["geoid"]] = {"city": city["name"], "sourceUrl": city["url"],
                                  "members": recs}
        print("  %-11s %d officials, %d e-mails, %d phones"
              % (city["name"], len(recs), sum(1 for x in recs if x.get("email")),
                 sum(1 for x in recs if x.get("phone"))), file=sys.stderr)

    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, indent=1, sort_keys=True)
        f.write("\n")
    print("ia-city-officials: %d cities cached to %s (%d refused by robots.txt)"
          % (len(payload), OUT_PATH, len(refused)), file=sys.stderr)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    main()
