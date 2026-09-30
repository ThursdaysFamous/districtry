#!/usr/bin/env python3
"""
Scrape stage 1: the City of Cedar Rapids council roster, cached for
build_cedar_rapids_council.py (stage 2).

WHAT CEDAR RAPIDS ELECTS
-------------------------
A mayor, three at-large council members, and one council member from each of
five districts -- nine seats. The city calls them DISTRICTS, not wards; Des
Moines and Waterloo say ward. Both words are kept as the city that uses them
uses them, and only the map toggle is generic.

A district layer alone answers five of the nine seats. The three at-large
members represent every district and are invisible to any boundary, so they
ship on every district's card.

ONE PAGE PER SEAT, WHICH IS THE OPPOSITE OF WATERLOO'S PROBLEM
----------------------------------------------------------------
Waterloo's roster is one hand-pasted WYSIWYG block with no element containing
one member and only one member, so its parser works on text lines and invents
a record separator. Cedar Rapids publishes SEVEN pages -- mayor, at-large, and
district_1..5 -- and every member is a properly structured pair:

    <h2 class="subheader"><span class="header">Councilmember NAME</span></h2>
    <p>District N Representative<br />Term of Office: YYYY&ndash;YYYY<br />
       <a href="tel:...">PHONE</a><br /><a href="mailto:...">EMAIL</a></p>

So this parser is STRUCTURAL: a member is an <h2> heading plus the <p> that
immediately follows it, and contact is read from inside that <p> and nowhere
else. There is no window, no distance guess, and no next-member boundary to
get wrong.

THE MAYOR'S PAGE USES A DIFFERENT HEADING CLASS, AND THAT IS WHY BOTH MATCH
----------------------------------------------------------------------------
Councilmembers sit in `<h2 class="subheader">` wrapping `<span class="header">`.
The mayor sits in a bare `<h2 class="header">` with no span. A parser keyed on
the councilmember shape alone returns EIGHT of nine and looks complete -- the
mayor's page silently yields zero blocks.

Both shapes are matched here, and the mayor IS scraped, even though
build_cedar_rapids_council.py then drops him under the fleet's at-large rule
(a citywide officer belongs on the unit's identity card, not a district card).
Scraping him is what makes that exclusion a decision this file can prove rather
than a gap it cannot see: SEATS below demands nine, so the day the mayor's page
reshapes, this scraper fails instead of quietly shipping eight.

THE SWITCHBOARD IS NEUTRALISED BY STRUCTURE, NOT BY A FILTER
--------------------------------------------------------------
319-286-5763 (the City Clerk's office) appears in the page furniture of ALL
SEVEN pages. A parser that took "the first 319 number on the page", or read a
window around the name, would ship it as somebody's direct line -- and it would
do so for every member, which is exactly the shared-number failure the fleet's
switchboard rule exists to catch AFTER the fact.

Scoping to the member's own <p> means that number is never a candidate. It is
still asserted, as a control: SWITCHBOARD must appear on every page (proving
the furniture is still there) and must never appear inside a member block. If
the first ever stops being true the page was rebuilt; if the second starts
being true the scoping broke.

FOUR MORE TRAPS, ALL MEASURED 2026-09-04
------------------------------------------
  * DISTRICT 4'S NAME CARRIES POST-NOMINALS: the heading reads "Councilmember
    Scott Olson, AIA (Emeritus), RCFM, RSIOR". The credentials are cut at the
    first comma. What is NOT done is any surname-based keying, because...
  * ...THERE ARE TWO OLSONS: Tyler Olson at-large and Scott Olson in District
    4. Surname is not a key on this council, and a roster joined on one would
    silently merge two people.
  * DISTRICT 4'S CONTACT IS NOT ON A CITY DOMAIN: the city publishes
    scott@scotteolson.com (his own firm) and a phone labelled "(cell)". Both
    ship as the city publishes them -- the address test is the county officers'
    one, which asks whether the officeholder's own name vouches for the local
    part, not what the domain is. Consulting the domain errs in both
    directions, which the five-city Tier A build measured on six of thirty
    addresses.
  * THE TERM USES AN EN DASH: "Term of Office: 2026&ndash;2029" unescapes to
    U+2013, not a hyphen. Matched as either.

THE DISTRICT NUMBER IS CROSS-CHECKED AGAINST ITS OWN PAGE
-----------------------------------------------------------
Each district page states its own number in the member's <p> ("District 3
Representative"). That is asserted to equal the number in the page's URL. It is
the cheap version of the check RUSD's board scraper needs: a CMS whose
fragments can reorder will happily serve district 3's block under district
4's URL, and nothing else here would notice.

Usage:
    python3 ia/scripts/cedar_rapids_council_scraper.py
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
OUT_PATH = os.path.join(CACHE_DIR, "cedar_rapids_council.json")

BASE = ("https://www.cedar-rapids.org/local_government/city_council/"
        "mayor_and_city_council")
# The page a reader should land on, and what the card links.
SOURCE_URL = BASE + "/index.php"
HEADERS = {"User-Agent": "districtry/1.0 (+https://districtry.com/ia/)"}

# slug -> (kind, expected member count). Nine seats across seven pages.
SEATS = [
    ("mayor", "mayor", 1),
    ("at-large", "at-large", 3),
    ("district_1", "district", 1),
    ("district_2", "district", 1),
    ("district_3", "district", 1),
    ("district_4", "district", 1),
    ("district_5", "district", 1),
]
EXPECT_DISTRICTS = [1, 2, 3, 4, 5]
EXPECT_AT_LARGE = 3
EXPECT_TOTAL = 9

# The City Clerk's office number, in the furniture of every page. Never a
# member's. See the docstring.
SWITCHBOARD = "319-286-5763"

# A member is a heading plus the <p> that immediately follows it. Two heading
# shapes: councilmembers wrap a span, the mayor does not.
BLOCK_RE = re.compile(
    r"<h2[^>]*class=\"(?:sub)?header\"[^>]*>([\s\S]*?)</h2>\s*(<p>[\s\S]*?</p>)",
    re.I)

ROLE_RE = re.compile(r"^District\s+(?P<num>\d+)\s+Representative", re.I)
AT_LARGE_RE = re.compile(r"^At-Large\s+Representative", re.I)
# en dash or hyphen; the end year is the one that matters
TERM_RE = re.compile(r"Term of Office:\s*(?P<start>\d{4})\s*[–-]\s*(?P<end>\d{4})", re.I)
PHONE_RE = re.compile(r"\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w{2,}")
NAME_PREFIX_RE = re.compile(r"^(?:Councilmember|Council Member|Mayor)\s+", re.I)


def fetch(url):
    require_robots_once(url, HEADERS["User-Agent"],
                        headers=HEADERS, label="ia-cedar-rapids-council-scraper")
    r = requests.get(url, headers=HEADERS, timeout=45)
    r.raise_for_status()
    return r.text


def block_lines(fragment):
    """The member <p> to text lines.

    <br /> IS THE ONLY SEPARATOR inside the block, so it must become a newline
    BEFORE tags are stripped -- otherwise role, term, phone and e-mail collapse
    into one unsplittable string. Same ordering rule as the Waterloo and Des
    Moines scrapers.
    """
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", fragment)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|div|li)>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html_mod.unescape(t)
    out = []
    for line in t.split("\n"):
        line = re.sub(r"[ \t\xa0]+", " ", line).strip()
        if line:
            out.append(line)
    return out


def clean_name(raw):
    """'Councilmember Scott Olson, AIA (Emeritus), RCFM, RSIOR' -> 'Scott Olson'.

    The prefix goes, then everything from the first comma -- which on this page
    is always post-nominal credentials. A name is never truncated to a single
    token, so a legitimate suffix-free name is untouched.
    """
    name = html_mod.unescape(re.sub(r"<[^>]+>", " ", raw))
    name = re.sub(r"[ \t\xa0]+", " ", name).strip()
    name = NAME_PREFIX_RE.sub("", name).strip()
    name = name.split(",")[0].strip()
    return name


def parse_page(slug, kind, expect_n, text):
    if SWITCHBOARD not in text:
        raise RuntimeError(
            "%s: the City Clerk's number %s is no longer in this page's furniture. "
            "It is the control that proves member contact is being read from "
            "inside each member's own block; its disappearance means the page was "
            "rebuilt and this parser needs re-reading." % (slug, SWITCHBOARD))

    found = []
    for m in BLOCK_RE.finditer(text):
        name = clean_name(m.group(1))
        if not name:
            continue
        lines = block_lines(m.group(2))
        blob = " ".join(lines)
        if SWITCHBOARD in blob:
            raise RuntimeError(
                "%s: %s appears INSIDE %s's block. That number is the City "
                "Clerk's office and is shared by all nine seats; shipping it as a "
                "member's direct line is the shared-number failure the fleet's "
                "switchboard rule exists to prevent. The block scoping has broken."
                % (slug, SWITCHBOARD, name))

        rec = {"name": name, "kind": kind, "page": slug}

        role = None
        for line in lines:
            mm = ROLE_RE.match(line)
            if mm:
                role = int(mm.group("num"))
                break
            if AT_LARGE_RE.match(line):
                role = "at-large"
                break
        if kind == "district":
            want = int(slug.rsplit("_", 1)[1])
            if role != want:
                raise RuntimeError(
                    "%s: the block for %s states %r where the page's own URL says "
                    "district %d. A CMS that reorders fragments will serve one "
                    "district's member under another's address, and this is the "
                    "only thing that notices." % (slug, name, role, want))
            rec["district"] = want
        elif kind == "at-large":
            if role != "at-large":
                raise RuntimeError(
                    "%s: %s is not marked an At-Large Representative (read %r)."
                    % (slug, name, role))
            rec["seat"] = "At-Large"

        mt = TERM_RE.search(blob)
        if mt:
            rec["termStart"] = mt.group("start")
            rec["termExpires"] = mt.group("end")

        mp = PHONE_RE.search(blob)
        if mp:
            rec["phone"] = mp.group(0).strip()
            # THE CITY'S "(cell)" LABEL ON DISTRICT 4'S NUMBER IS NOT CARRIED,
            # and that is a decision rather than an oversight. This scraper once
            # recorded it as `phoneNote`, which NOTHING consumed: the card's
            # person row takes {name, badge, note, phone, email}, its `note` is
            # already the term-expiry line, and `cardContactLine` has no slot
            # for a phone label -- all of it inside the shared ENGINE fence
            # `card-helpers`, so shipping the label would mean an engine change
            # ported to all six instances for one member of one city.
            # A field no consumer reads is a claim that rots, so it is gone.
            # The number itself ships exactly as the city publishes it.
        me = EMAIL_RE.search(blob)
        if me:
            rec["email"] = me.group(0).strip()

        found.append(rec)

    if len(found) != expect_n:
        raise RuntimeError(
            "%s: parsed %d member block(s), expected %d. The mayor's page uses "
            "<h2 class=\"header\"> and councilmembers use <h2 class=\"subheader\"> "
            "wrapping a span; a change to either shape shows up here first."
            % (slug, len(found), expect_n))
    return found


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    records = []
    for slug, kind, expect_n in SEATS:
        url = "%s/%s.php" % (BASE, slug)
        try:
            text = fetch(url)
        except Exception as exc:
            raise RuntimeError("%s: fetch failed — %s" % (url, exc))
        got = parse_page(slug, kind, expect_n, text)
        for rec in got:
            rec["sourceUrl"] = url
            seat = (rec.get("seat") or ("District %s" % rec["district"])
                    if kind != "mayor" else "Mayor")
            print("  %-10s %-22s %-12s %-16s %s"
                  % (slug, rec["name"], seat, rec.get("phone", "-"),
                     rec.get("email", "-")), file=sys.stderr)
        records.extend(got)

    names = [r["name"] for r in records]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        raise RuntimeError(
            "the same name appears on more than one seat: %s. Cedar Rapids seats "
            "two Olsons (Tyler at-large, Scott in District 4), so a repeated FULL "
            "name is a parse fault rather than a coincidence." % dupes)

    districts = sorted(r["district"] for r in records if r["kind"] == "district")
    at_large = [r for r in records if r["kind"] == "at-large"]
    mayors = [r for r in records if r["kind"] == "mayor"]
    if districts != EXPECT_DISTRICTS:
        raise RuntimeError("districts %s, expected %s" % (districts, EXPECT_DISTRICTS))
    if len(at_large) != EXPECT_AT_LARGE:
        raise RuntimeError("%d at-large members, expected %d"
                           % (len(at_large), EXPECT_AT_LARGE))
    if len(mayors) != 1:
        raise RuntimeError("%d mayors, expected 1" % len(mayors))
    if len(records) != EXPECT_TOTAL:
        raise RuntimeError("%d seats, expected %d" % (len(records), EXPECT_TOTAL))

    payload = {"sourceUrl": SOURCE_URL, "members": records}
    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("wrote %s — %d seats (%d districts, %d at-large, 1 mayor)"
          % (OUT_PATH, len(records), len(districts), len(at_large)), file=sys.stderr)


if __name__ == "__main__":
    main()
