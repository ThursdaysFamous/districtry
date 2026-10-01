#!/usr/bin/env python3
"""
Scrape stage 1: the City of Waterloo council roster, cached for
build_waterloo_council.py (stage 2).

WHAT WATERLOO ELECTS
---------------------
A mayor, two at-large council members, and one council member from each of
five wards. Structurally the same as Des Moines (Iowa Code 372.4(1)(b)) with
five wards instead of four -- so, exactly as there, a ward layer alone answers
five of the seven council seats and the other two represent every ward and are
invisible to any boundary. Both at-large members therefore ship on every ward's
card.

THE MAYOR IS NOT SCRAPED HERE. Waterloo publishes him on a different page
(/government/mayor/index.php), and he is elected by the whole city, so by the
fleet's at-large rule he belongs on the unit's identity card rather than on a
district card. Des Moines carries its mayor in this file for historical
reasons; Waterloo's absence is a decision, not an oversight.

THIS PAGE IS NOTHING LIKE DES MOINES'S, AND THE DIFFERENCE IS THE WHOLE PARSER
------------------------------------------------------------------------------
Both cities run Revize, which is why it is worth saying plainly that the
markup does NOT transfer. www.dsm.city renders every person as a structured
`<div class="card shadow">` with an `<h3 class="card-title">` and a
`<dl><dt>Phone:</dt>` block, so its scraper splits on `<h2>` and reads cards.

Waterloo's council page has NO cards, NO <dl>, and ONE <h3> on the entire
page. The roster is hand-pasted WYSIWYG HTML carrying Word's inline styles:
the first member happens to sit inside an `<h2>`, and the other six are loose
`<span>` runs in `<p>` blocks separated by bare `<br />`, interleaved with
`<img>` headshots. There is no element that contains one member and only one
member, so there is nothing to iterate over.

So this parser works on TEXT LINES, and the record separator is the identity
line itself:

    NAME, (Ward N|At-Large) Through MM/DD/YYYY

Phone and e-mail are read from the lines that follow, up to the next identity
line.

THE "Through <date>" IS NOT DECORATION -- IT IS THE DISCRIMINATOR
------------------------------------------------------------------
Every member is ALSO named a second time, in the anchor text of a link to
their biography page:

    Steve Simons, At Large. Click on their name to be redirected to their
    bio link page.

Those lines have the same `NAME, SEAT` shape and NO "Through <date>", which is
the only thing separating them from the real ones. It matters because TWO OF
THE SIX disagree with the authoritative line (measured 2026-09-04):

    bio link "Steve Simons"                 heading "Steve Simon"
    bio link "Hector Salamanca-Arroyo"      heading "Hector A. Salamanca-Arroyo"

A parser keyed on the bio-link anchors -- the obvious thing to key on, since
they are the only <a> elements naming members -- ships a councilman whose name
is misspelt on the city's own page. Belinda Creighton-Smith has no bio link at
all, so such a parser would also ship six of seven and look complete.

Those lines are consequently kept as the CONTROL, the way dsm_council_scraper
keeps the Appointed Staff cards: they prove the page still renders the
duplicate form and that the "Through" test is what excludes it. Their
disappearance means the page was rebuilt and this parser needs re-reading.

TWO SMALLER TRAPS, BOTH MEASURED
---------------------------------
  * "Through" is capitalised for six members and lowercase for Dave Morrow
    ("Ward 2 through 12/31/2027"). Matched case-insensitively.
  * Phone formatting is not consistent -- "(319) 324-0593" for most, but
    "(319)-988-1960" and "(515)-447-1186" with a hyphen after the area code.
    Both ship verbatim; normalising a published number invents one.

NO SWITCHBOARD HERE, AND THAT IS MEASURED RATHER THAN ASSUMED
---------------------------------------------------------------
The fleet's switchboard rule (docs/EXPANSION_GUIDE.md Part 5) hoists a number
shared by every member up to the body, because repeating it implies direct
lines that do not exist. Waterloo publishes SEVEN DISTINCT numbers, so the
test does not fire and each number stays on its own member. build_waterloo_
council.py re-runs that test every time rather than trusting this sentence.

Usage:
    python3 ia/scripts/waterloo_council_scraper.py
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
OUT_PATH = os.path.join(CACHE_DIR, "waterloo_council.json")

SOURCE_URL = "https://www.cityofwaterlooiowa.com/government/city_council/index.php"
HEADERS = {"User-Agent": "districtry/1.0 (+https://districtry.com/ia/)"}

EXPECT_WARDS = [1, 2, 3, 4, 5]
EXPECT_AT_LARGE = 2

# The authoritative identity line. The "Through <date>" is REQUIRED -- it is
# what separates a member's own line from the bio-link anchor that repeats
# their name (and, for two of them, misspells it).
IDENT_RE = re.compile(
    r"^(?P<name>[A-Z][A-Za-z.'\-]*(?:\s+[A-Za-z.'\-]+)*),\s*"
    r"(?P<seat>Ward\s*(?P<ward>\d+)|At-Large)\s+"
    r"[Tt]hrough\s+(?P<term>\d{1,2}/\d{1,2}/\d{4})\s*$")

# The same NAME, SEAT shape WITHOUT the term -- the bio-link anchors. Trailing
# prose is allowed because the page runs "Click on their name..." onto the
# same line.
BIOLINK_RE = re.compile(
    r"^(?P<name>[A-Z][A-Za-z.'\-]*(?:\s+[A-Za-z.'\-]+)*),\s*"
    r"(?:Ward\s*\d+|At[- ]Large)\b")

PHONE_RE = re.compile(r"^Phone:?\s*(?P<v>.+?)\s*$", re.I)
EMAIL_LINE_RE = re.compile(r"^E-?mail:?\s*(?P<v>.*)$", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w{2,}")


def fetch(url):
    require_robots_once(url, HEADERS["User-Agent"],
                        headers=HEADERS, label="ia-waterloo-council-scraper")
    r = requests.get(url, headers=HEADERS, timeout=45)
    r.raise_for_status()
    return r.text


def text_lines(fragment):
    """Tags to text, but <br> and block ends become LINE BREAKS first.

    Order matters, exactly as in dsm_council_scraper.text_of: strip tags first
    and a member's name, phone and e-mail collapse into one unsplittable
    string, because <br /> is the only separator this page has.
    """
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", fragment)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|h[1-6]|div|li|tr|td)>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html_mod.unescape(t).replace("\xa0", " ")
    return [re.sub(r"\s+", " ", line).strip() for line in t.split("\n")]


def parse(page):
    lines = [ln for ln in text_lines(page) if ln]

    members, control = [], []
    for i, line in enumerate(lines):
        m = IDENT_RE.match(line)
        if m:
            members.append((i, m))
            continue
        b = BIOLINK_RE.match(line)
        if b:
            control.append(b.group("name"))

    records = []
    for n, (i, m) in enumerate(members):
        # scan to the next identity line; the last member is bounded so a
        # footer full of addresses cannot donate a phone number to him
        stop = members[n + 1][0] if n + 1 < len(members) else min(len(lines), i + 10)
        rec = {"name": m.group("name"), "termExpires": m.group("term")}
        ward = m.group("ward")
        rec["seat"] = ("Ward %d" % int(ward)) if ward else "At-Large"
        if ward:
            rec["ward"] = int(ward)
        for line in lines[i + 1:stop]:
            if "phone" not in rec:
                pm = PHONE_RE.match(line)
                if pm and pm.group("v"):
                    rec["phone"] = pm.group("v")
                    continue
            if "email" not in rec:
                em = EMAIL_LINE_RE.match(line)
                if em:
                    found = EMAIL_RE.search(em.group("v"))
                    if found:
                        rec["email"] = found.group(0)
        records.append(rec)
    return records, control


def main():
    page = fetch(SOURCE_URL)
    records, control = parse(page)

    at_large = [r for r in records if "ward" not in r]
    wards = {}
    for rec in records:
        if "ward" in rec:
            if rec["ward"] in wards:
                raise SystemExit(
                    "ward %d is claimed by both %r and %r. The page lists each "
                    "member once; two identity lines for one ward means the "
                    "'Through <date>' test stopped separating a member's own "
                    "line from their bio link."
                    % (rec["ward"], wards[rec["ward"]]["name"], rec["name"]))
            wards[rec["ward"]] = rec

    if sorted(wards) != EXPECT_WARDS:
        raise SystemExit(
            "the council page names wards %s, expected %s. Waterloo elects one "
            "member from each of five wards; a different set is either a parse "
            "break or the city changing its form, and both need reading."
            % (sorted(wards), EXPECT_WARDS))
    if len(at_large) != EXPECT_AT_LARGE:
        raise SystemExit(
            "the council page names %d at-large member(s), expected %d"
            % (len(at_large), EXPECT_AT_LARGE))

    names = [r["name"] for r in records]
    if len(set(names)) != len(names):
        raise SystemExit("a name is claimed by two seats: %s" % sorted(names))

    if not control:
        raise SystemExit(
            "no bio-link lines were found. Those lines are the CONTROL for this "
            "scrape: they repeat each member's name WITHOUT a term date, two of "
            "them differ from the authoritative spelling, and their presence is "
            "what proves the 'Through <date>' test is still doing the "
            "separating. Their disappearance means the page was rebuilt and "
            "this parser needs re-reading.")

    # Report, rather than silently drop, a bio link that disagrees with the
    # member's own line -- this is the misspelling the control exists for.
    disagree = sorted(set(control) - set(names))

    missing_phone = [r["name"] for r in records if not r.get("phone")]
    missing_email = [r["name"] for r in records if not r.get("email")]

    payload = {
        "sourceUrl": SOURCE_URL,
        "atLarge": at_large,
        "wards": {str(k): wards[k] for k in sorted(wards)},
        "controlSeen": len(control),
        "biolinkDisagreements": disagree,
    }
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, indent=1, sort_keys=True)
        f.write("\n")

    print("waterloo-council: %d at-large + %d wards (%d bio-link control lines)"
          % (len(at_large), len(wards), len(control)), file=sys.stderr)
    for rec in at_large + [wards[k] for k in sorted(wards)]:
        print("  %-30s %-10s %-16s %s" % (rec["name"], rec["seat"],
                                          rec.get("phone", "-"),
                                          rec.get("email", "-")), file=sys.stderr)
    if disagree:
        print("  bio-link anchors NOT matching any member (excluded, by design): %s"
              % ", ".join(repr(d) for d in disagree), file=sys.stderr)
    if missing_phone:
        print("  no phone: %s" % ", ".join(missing_phone), file=sys.stderr)
    if missing_email:
        print("  no e-mail: %s" % ", ".join(missing_email), file=sys.stderr)
    print("wrote %s" % OUT_PATH, file=sys.stderr)


if __name__ == "__main__":
    main()
