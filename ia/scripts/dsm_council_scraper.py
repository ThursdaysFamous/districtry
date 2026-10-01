#!/usr/bin/env python3
"""
Scrape stage 1: the City of Des Moines council roster, cached for
build_dsm_council.py (stage 2).

WHAT DES MOINES ELECTS
-----------------------
Iowa Code 372.4(1)(b): a city governed on 1 July 1975 by the mayor-council
form with "two council members elected at large and one council member from
each of four wards" may continue in that form. Des Moines does. So seven
people are elected citywide-or-by-ward, and only FOUR of them have a ward --
which is why this scrape exists at all. A ward layer alone answers for four of
the seven seats; the other three represent every ward and are invisible to any
boundary.

(372.4(2) also states plainly that "the mayor is not a member of the council",
which is why the mayor is carried in its own group here and badged Mayor
rather than folded into a council list.)

THE SECTION HEADING IS THE AUTHORITY, NOT THE CARD MARKUP
-----------------------------------------------------------
www.dsm.city is Revize, and every person on the council page -- elected or not
-- is rendered as the SAME `<div class="card shadow">` with the same
`<h3 class="card-title"><strong>NAME<br><span>SEAT</span></strong></h3>` and
the same `<dl><dt>Phone:</dt><dd>...` block. Four `<h2>` sections use it:

    Mayor                  1 card    ELECTED
    At-Large Council Members  2 cards ELECTED
    Ward Council Members   4 cards    ELECTED
    Appointed Staff        4 cards    NOT ELECTED -- City Manager, City
                                      Attorney, City Clerk, Library Director
    Department Directors   many       NOT ELECTED

A scraper that walks every `card-title` on this page ships the City Manager
and the Library Director as members of the city council. This one splits on
`<h2>` first and reads cards only inside the three elected sections, and
REFUSES if a name it recovered also appears under an unelected heading. That
is the Jackson County rule (the grouping heading is the authority) and the
Alexander County rule (a page's people-shaped markup outlives the people) in
one page.

TWO SMALLER TRAPS, BOTH MEASURED
---------------------------------
  * The seat label lives INSIDE the <strong>, after a <br/>, so the naive text
    of a card title is "Rob X. Barron Ward 1" -- one string, no separator. The
    <br/> is turned into a delimiter before any tag is stripped.
  * The Appointed Staff cards prove the same point in reverse: the City
    Attorney's name renders across two text nodes ("Jeffrey" / "D. Lester"),
    so whitespace is normalised rather than trusted. Nothing here reads those
    cards, but the same collapse would apply to an elected member if the city
    ever marks one up that way.

NO SWITCHBOARD HERE, AND THAT IS MEASURED RATHER THAN ASSUMED
---------------------------------------------------------------
The fleet's switchboard rule (docs/EXPANSION_GUIDE.md Part 5) hoists a number
shared by every member up to the body, because repeating it implies direct
lines that do not exist. Des Moines publishes SEVEN DISTINCT numbers, so the
test does not fire and each number stays on its own member -- which is the
rule working, not an exemption from it. build_dsm_council.py re-runs that test
every time rather than trusting this sentence.

Usage:
    python3 ia/scripts/dsm_council_scraper.py
"""

import html as html_mod
import json
import os
import re
import sys

import requests
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
OUT_PATH = os.path.join(CACHE_DIR, "dsm_council.json")

SOURCE_URL = "https://www.dsm.city/government/city_council/index.php"
HEADERS = {"User-Agent": "districtry/1.0 (+https://districtry.com/ia/)"}

# The three headings whose cards are ELECTED people, and the group each maps
# to. Matched on the heading's leading text: "Ward Council Members" carries a
# "Find Your Ward" button inside the same <h2>.
ELECTED_SECTIONS = [
    ("mayor", re.compile(r"^Mayor\b", re.I)),
    ("at-large", re.compile(r"^At-Large Council Members\b", re.I)),
    ("ward", re.compile(r"^Ward Council Members\b", re.I)),
]
# Headings that use identical card markup for people who are NOT elected. Any
# name recovered from these is a parse escape, and the build refuses.
UNELECTED_SECTIONS = re.compile(r"^(Appointed Staff|Department Directors)\b", re.I)

EXPECT = {"mayor": 1, "at-large": 2, "ward": 4}

CARD_RE = re.compile(r'<h3 class="card-title">(.*?)</h3>(.*?)(?=<h3 class="card-title">|\Z)',
                     re.S | re.I)
H2_RE = re.compile(r"<h2[^>]*>.*?</h2>", re.S | re.I)
DL_RE = re.compile(r"<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>", re.S | re.I)
WARD_RE = re.compile(r"^Ward\s+(\d+)$", re.I)


def fetch(url):
    require_robots_once(url, HEADERS["User-Agent"],
                        headers=HEADERS, label="ia-dsm-council-scraper")
    r = requests.get(url, headers=HEADERS, timeout=45)
    r.raise_for_status()
    return r.text


def text_of(fragment, br_as=" || "):
    """Strip tags to text, turning <br> into an explicit delimiter FIRST.

    Order matters: strip tags first and "Rob X. Barron<br/>Ward 1" collapses to
    one unsplittable string.
    """
    t = re.sub(r"<br\s*/?>", br_as, fragment, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html_mod.unescape(t)).strip()


def parse_card(title_html, body_html):
    parts = [p.strip() for p in text_of(title_html).split("||")]
    parts = [p for p in parts if p]
    if len(parts) < 2:
        return None
    name, seat = parts[0], parts[1]
    rec = {"name": name, "seat": seat}
    for dt, dd in DL_RE.findall(body_html):
        label = text_of(dt, br_as=" ").rstrip(":").strip().lower()
        value = text_of(dd, br_as=" ").strip()
        if not value:
            continue
        if label == "phone":
            rec["phone"] = value
        elif label == "email":
            rec["email"] = value
        elif label == "elected":
            rec["elected"] = value
        elif label.startswith("term expires"):
            rec["termExpires"] = value
    return rec


def parse(page):
    """Split on <h2> FIRST, then read cards inside each section."""
    main = re.search(r"<main\b.*?</main>", page, re.S | re.I)
    body = main.group(0) if main else page

    chunks = re.split(r"(<h2[^>]*>.*?</h2>)", body, flags=re.S | re.I)
    groups, unelected_names, heading = {}, [], None
    for chunk in chunks:
        if H2_RE.fullmatch(chunk or ""):
            heading = text_of(chunk, br_as=" ")
            continue
        if heading is None:
            continue
        cards = [parse_card(t, b) for t, b in CARD_RE.findall(chunk or "")]
        cards = [c for c in cards if c]
        if not cards:
            continue
        if UNELECTED_SECTIONS.match(heading):
            unelected_names.extend(c["name"] for c in cards)
            continue
        for key, pattern in ELECTED_SECTIONS:
            if pattern.match(heading):
                groups.setdefault(key, []).extend(cards)
                break
    return groups, unelected_names


def main():
    page = fetch(SOURCE_URL)
    groups, unelected = parse(page)

    for key, want in EXPECT.items():
        got = len(groups.get(key, []))
        if got != want:
            raise SystemExit(
                "the council page's %r section yielded %d people, expected %d. "
                "Iowa Code 372.4(1)(b) seats a mayor, two at-large members and "
                "four ward members in Des Moines; a different count is either a "
                "parse break or the city changing its form, and both need reading."
                % (key, got, want))

    # The wards must be exactly 1..4, read from the seat label rather than
    # from the order the page happens to list them in.
    wards = {}
    for rec in groups["ward"]:
        m = WARD_RE.match(rec["seat"])
        if not m:
            raise SystemExit("a Ward-section card is labelled %r, which names no ward"
                             % rec["seat"])
        wards[int(m.group(1))] = rec
    if sorted(wards) != [1, 2, 3, 4]:
        raise SystemExit("the ward cards name wards %s, expected [1, 2, 3, 4]"
                         % sorted(wards))

    elected_names = {r["name"] for recs in groups.values() for r in recs}
    leaked = elected_names & set(unelected)
    if leaked:
        raise SystemExit(
            "these names appear under BOTH an elected and an unelected heading: "
            "%s. The unelected sections (Appointed Staff, Department Directors) "
            "use identical card markup, so this means the section split broke."
            % sorted(leaked))
    if not unelected:
        raise SystemExit(
            "no cards were found under Appointed Staff / Department Directors. "
            "Those sections are the CONTROL for this scrape: they prove the page "
            "still renders unelected people in the same markup and that the "
            "heading split is what keeps them out. Their disappearance means the "
            "page was rebuilt and this parser needs re-reading.")

    payload = {
        "sourceUrl": SOURCE_URL,
        "mayor": groups["mayor"][0],
        "atLarge": groups["at-large"],
        "wards": {str(k): wards[k] for k in sorted(wards)},
        "unelectedSeen": len(unelected),
    }
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, indent=1, sort_keys=True)
        f.write("\n")

    print("dsm-council: mayor + %d at-large + %d wards (%d unelected cards correctly "
          "excluded)" % (len(groups["at-large"]), len(wards), len(unelected)),
          file=sys.stderr)
    for rec in [payload["mayor"]] + payload["atLarge"] + [wards[k] for k in sorted(wards)]:
        print("  %-22s %-22s %-16s %s" % (rec["name"], rec["seat"],
                                          rec.get("phone", "-"), rec.get("email", "-")),
              file=sys.stderr)
    print("wrote %s" % OUT_PATH, file=sys.stderr)


if __name__ == "__main__":
    main()
