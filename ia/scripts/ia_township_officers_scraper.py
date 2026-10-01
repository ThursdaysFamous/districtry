#!/usr/bin/env python3
"""
Scrape the TOWNSHIP-OFFICIALS pages Iowa counties publish for the townships in
them -- the clerk and trustees of each civil township, by name.

THE ROUTE, AND THE SENTENCE IT CORRECTS
-----------------------------------------
The County Subdivision card has said since this layer shipped that a township
is "an active local government (elected trustees, clerk and assessor under Iowa
Code ch. 359)" and that "no statewide roster of township officers was found in
the research pass." The first half is right and the second half was answered
the wrong way round: there is no STATEWIDE roster and there never was, and
twelve counties publish their own, which is how Iowa's city officials already
arrive (ia_county_city_officials_scraper.py, 2026-09-05).

Measured 2026-10-01: the same twelve counties that publish a city-officials
page publish a township one beside it, at `/about/elected_officials/township/`
on the same CMS, and all twelve answer HTTP 200 to this instance's own token.
Together they name 617 officials across 186 townships -- a clerk and three
trustees each, bar the townships where the county names fewer.

TWELVE COUNTIES OF 99, AND THE CARD SAYS SO. Iowa has about 1,600 civil
townships and this reaches 186 of them, so the gap record stays open and the
card names the county that published whatever it shows. The fleet's precedent
for shipping a sub-county tier this thin is Illinois's township layer, which
names Cook's 29 boards of about 1,400 townships and is the whole of what that
state answers at this level.

TWO MARKUP SHAPES, AND HALF THE COUNTIES ARE IN EACH
------------------------------------------------------
This is the trap `ia_county_city_officials_scraper.py` already records for the
city pages, in a second costume. SIX counties wrap an official's name in
`<div class="offContact4x offContactName"><b>Name</b><br>Role</div>` -- Boone,
Crawford, Iowa, Marion, Sac and Shelby -- and the other SIX put the same
`<b>Name</b><br>Role` straight inside `<div class="offInfo">` with no inner
wrapper at all: Adams, Cerro Gordo, Jackson, Keokuk, Muscatine and Winnebago.
A parser written against either wrapper returns SIX COUNTIES AND ZERO
OFFICIALS for the other six, which is exactly what the first draft of this
file did -- a clean, confident, half-empty answer. So the row pattern names
neither wrapper: inside each `offRow` it takes the first `<b>` as the name and
the text after the following `<br>` as the role, which both shapes satisfy.

NO HOME ADDRESSES, EVER -- AND THESE PAGES ARE FULL OF THEM
-------------------------------------------------------------
A township officer is not reached at a courthouse. Every one of these pages
publishes the officer's own street address, because that is where they live:
"823 F Ave., Ogden, IA 50212". The city scraper's rule applies unchanged and
matters more here, so this file reads NAME, ROLE, TERM END, TERM LENGTH and
PHONE and never an address line -- not even to discard it later, because a
value that is parsed is a value that can leak into an output.

The PHONE is read, on the same reasoning the city builder already records for
Moravia's councilman: the number a government publishes beside an officeholder
is how that government says to reach them, whosever handset it is.

CERRO GORDO SAYS SOMETHING THE OTHER ELEVEN DO NOT, AND IT IS NOT A NAME
--------------------------------------------------------------------------
Its headings read "Bath Appointed", "Clear Lake Elected", "Grant Elected" --
the county stating, per township, whether its officers were elected or
appointed by the board of supervisors. Under Iowa Code 359.17 a township whose
electors fail to fill a vacancy has it filled by appointment, so this is a real
distinction and the county is the only publisher of it. Read as part of the
NAME it matches no township in the census fabric and all sixteen would be
dropped; so the suffix is split off, kept as `selection`, and the join uses
what is left. Nothing is inferred for the other eleven counties: a township
whose county does not say carries no `selection` field at all.

Usage:
    python3 ia/scripts/ia_township_officers_scraper.py
    python3 ia/scripts/ia_township_officers_scraper.py --selftest
"""

import json
import os
import re
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)          # robots_gate is a sibling, not a package
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from robots_gate import RobotsGate  # noqa: E402
from validate_officeholder_names import is_vacancy_marker  # noqa: E402  (one reader for the word)

CACHE_DIR = os.path.join(HERE, ".cache")
OUT_PATH = os.path.join(CACHE_DIR, "ia_township_officers.json")
HEADERS = {"User-Agent": "districtry/1.0 (+https://districtry.com/ia/)",
           "Accept": "text/html,application/xhtml+xml"}
TIMEOUT = 45

# PINNED, not discovered, for the reason the city scraper gives: a county that
# redesigns its site should fail loudly here rather than vanish from a roster
# nobody is watching. The list is the same twelve as the city sweep, which is a
# fact about that CMS rather than a coincidence -- both pages are generated
# from one officials table. A thirteenth county is an entry, not a code change.
#
# EVERY ONE WAS READ WITH THIS FILE'S OWN TOKEN on 2026-10-01, robots.txt first
# through the shared reader: twelve of twelve answered 200, none refused, and no
# host states a Crawl-delay that binds this client. The sleep below is courtesy,
# not compliance.
COUNTIES = [
    ("19003", "Adams", "https://adamscounty.iowa.gov/about/elected_officials/township/"),
    ("19015", "Boone", "https://boonecounty.iowa.gov/about/elected_officials/township/"),
    ("19033", "Cerro Gordo", "https://cerrogordo.gov/about/elected_officials/township/"),
    ("19047", "Crawford", "https://www.crawfordcounty.iowa.gov/about/elected_officials/township/"),
    ("19095", "Iowa", "https://iowacounty.iowa.gov/about/elected_officials/township/"),
    ("19097", "Jackson", "https://jacksoncounty.iowa.gov/about/elected_officials/township/"),
    ("19107", "Keokuk", "https://keokukcounty.iowa.gov/about/elected_officials/township/"),
    ("19125", "Marion", "https://www.marioncountyiowa.gov/about/elected_officials/township/"),
    ("19139", "Muscatine", "https://muscatinecountyiowa.gov/about/elected_officials/township/"),
    ("19161", "Sac", "https://www.saccountyiowa.gov/about/elected_officials/township/"),
    ("19165", "Shelby", "https://shelbycounty.iowa.gov/about/elected_officials/township/"),
    ("19189", "Winnebago", "https://winnebagocountyiowa.gov/about/elected_officials/township/"),
]

# One township's block. `data-filter-name` is the CMS's own slug for the
# township the block belongs to, so the block boundary is the county's rather
# than a guess, and the <h2> inside it is the township's printed name.
BLOCK = re.compile(r'<div class="filterDiv[^"]*"[^>]*data-filter-name="([^"]+)"[^>]*>'
                   r'(.*?)(?=<div class="filterDiv|\Z)', re.S)
H2 = re.compile(r"<h2>\s*(.*?)\s*</h2>", re.S)
# Wrapper-agnostic, which is the whole point -- see the two-shapes note above.
ROW = re.compile(r"<b>\s*(?P<name>[^<]{2,60}?)\s*</b>\s*(?:<[^>]+>\s*)*?<br\s*/?>"
                 r"\s*(?P<role>[A-Za-z][A-Za-z .'-]{2,40}?)\s*(?=<|$)", re.S)
PHONE = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
TERM_ENDS = re.compile(r"Term Ends:\s*(\d{4})")
TERM_LENGTH = re.compile(r"Term Length:\s*(\d+)\s*Years?", re.I)
# The only two offices Iowa Code ch. 359 makes these pages' subject. An
# assessor or a fire chief appearing here is a page change to read, not a row
# to ship under a vocabulary this file never measured.
ROLES = ("Clerk", "Trustee")
# Cerro Gordo alone, and only as a trailing word -- see the note above. It is
# anchored to the end so a township genuinely named for one of these words
# could never have it stripped.
SELECTION = re.compile(r"\s+(Appointed|Elected)$")


def clean(fragment):
    """Markup to one line of text, entities resolved."""
    text = re.sub(r"<[^>]+>", " ", fragment)
    for entity, char in (("&amp;", "&"), ("&#39;", "'"), ("&rsquo;", "'"),
                         ("&nbsp;", " "), ("&quot;", '"')):
        text = text.replace(entity, char)
    return re.sub(r"\s+", " ", text).strip()


def parse(page):
    """{township name: {selection?, officials: [...]}} for one county's page.

    Each official is read inside their own `offRow`, so a phone or a term can
    never cross from one person to the next -- the bounding problem the city
    scraper solved with a measured per-field reach does not arise here, because
    this CMS gives every official their own element.
    """
    out = {}
    for match in BLOCK.finditer(page):
        body = match.group(2)
        heading = H2.search(body)
        if not heading:
            continue
        name = clean(heading.group(1))
        selection = None
        suffix = SELECTION.search(name)
        if suffix:
            selection = suffix.group(1)
            name = name[:suffix.start()].strip()
        officials = []
        for chunk in re.split(r'<div class="offRow">', body)[1:]:
            row = ROW.search(chunk)
            if not row:
                continue
            person, role = clean(row.group("name")), clean(row.group("role"))
            if not person or role not in ROLES:
                continue
            text = clean(chunk)
            # A COUNTY'S WORD FOR AN EMPTY SEAT IS A FACT ABOUT THE SEAT AND
            # NEVER A PERSON. Jackson County prints "Vacant" in the name cell
            # of one Iowa township trustee row, and carrying that string
            # through would ship a township officer called Vacant -- which is
            # exactly what this repo already published twice in Illinois
            # before `validate_officeholder_names.py` started refusing the
            # word. The seat is recorded structurally instead: the role is
            # kept, because the county is naming a seat that exists, and the
            # name is dropped rather than replaced. The word list has ONE
            # reader (scripts/validate_officeholder_names.py) so this scraper
            # and that gate cannot come to disagree about which words mean an
            # empty seat.
            if is_vacancy_marker(person):
                rec = {"role": role, "vacant": True}
            else:
                rec = {"name": person, "role": role}
            phone = PHONE.search(text)
            if phone:
                rec["phone"] = phone.group(0)
            ends = TERM_ENDS.search(text)
            if ends:
                rec["termEnds"] = ends.group(1)
            length = TERM_LENGTH.search(text)
            if length:
                rec["termLength"] = length.group(1)
            officials.append(rec)
        if not officials:
            continue
        rec = {"officials": officials}
        if selection:
            rec["selection"] = selection
        out[name] = rec
    return out


# ---------------------------------------------------------------- self-test
def _row(name, role, *extra, **kw):
    """One official in whichever of the two markup shapes is asked for."""
    inner = "<b>%s</b>        <br>\n    %s    " % (name, role)
    if kw.get("shape") == "wrapped":
        inner = ('<div class="offContact4x offContactName">\n    %s</div>'
                 % inner)
    else:
        inner = '<div class="offInfo">\n    %s</div>' % inner
    return ('<div class="offRow">%s%s<div class="offTerm">Term Ends: 2026'
            '<div class="termLengthDescription">Term Length: 4 Years</div>'
            '</div></div>' % (inner, "".join(extra)))


def _township(slug, heading, *rows):
    return ('<div class="filterDiv %s" data-filter-item data-filter-name="%s">'
            '<h2>%s</h2><div class="officialInfo">%s</div></div>'
            % (slug, slug, heading, "".join(rows)))


def _selftest():
    """Offline checks on the two things that have gone wrong on these pages.

    Both arms of the markup case are asserted, because a fixture carrying only
    the shape the parser was written against is what let the first draft report
    six counties and zero officials for the other six.
    """
    failures, ran = [], []

    def check(cond, msg):
        ran.append(msg)
        print(("  ok   " if cond else "  FAIL ") + msg)
        if not cond:
            failures.append(msg)

    # 1. THE WRAPPED SHAPE -- Boone, Crawford, Iowa, Marion, Sac, Shelby.
    wrapped = _township("amaqua", "Amaqua",
                        _row("Craig Heineman", "Clerk",
                             '<div class="offContact4x">823 F Ave.<br>Ogden, IA 50212</div>',
                             '<div class="offContact4x">(515) 275-2303</div>',
                             shape="wrapped"),
                        _row("John Hunter", "Trustee", shape="wrapped"))
    got = parse(wrapped)
    check(list(got) == ["Amaqua"], "wrapped shape: one township named Amaqua (got %s)"
          % list(got))
    check([o["name"] for o in got.get("Amaqua", {}).get("officials", [])]
          == ["Craig Heineman", "John Hunter"],
          "wrapped shape: both officials, in page order")
    check(got["Amaqua"]["officials"][0].get("phone") == "(515) 275-2303",
          "wrapped shape: the published phone reaches the clerk")

    # 2. THE BARE SHAPE -- Adams, Cerro Gordo, Jackson, Keokuk, Muscatine,
    #    Winnebago. Identical expectations, no wrapper.
    bare = _township("bellevue", "Bellevue",
                     _row("Troy Patzner", "Clerk"),
                     _row("Bill Bevan", "Trustee"))
    got = parse(bare)
    check([o["name"] for o in got.get("Bellevue", {}).get("officials", [])]
          == ["Troy Patzner", "Bill Bevan"],
          "bare shape: both officials parse with no inner wrapper")

    # 3. NO ADDRESS LINE IS EVER CARRIED. The wrapped fixture publishes a street
    #    address beside the clerk; no field of the parsed record may contain it.
    got = parse(wrapped)
    blob = json.dumps(got)
    check("823 F Ave" not in blob and "Ogden" not in blob,
          "no home address appears in any parsed field")

    # 3b. A COUNTY'S OWN WORD FOR AN EMPTY SEAT becomes a fact about the seat
    #     rather than a person. Jackson County prints "Vacant" in the name
    #     cell of one Iowa township trustee row, and carrying it through would
    #     ship a township officer of that name -- which this fleet published
    #     twice in Illinois before a gate started refusing the word. The ROLE
    #     survives, because the county is naming a seat that exists, so a
    #     four-seat township still reads as four seats.
    got = parse(_township("iowa", "Iowa",
                          _row("Melanie Macy", "Clerk"),
                          _row("Vacant", "Trustee"),
                          _row("Dean Papke", "Trustee")))
    rows = got.get("Iowa", {}).get("officials", [])
    check(len(rows) == 3, "vacant seat: the empty seat is still a row (got %d)"
          % len(rows))
    check(rows[1].get("vacant") is True and "name" not in rows[1],
          "vacant seat: recorded structurally, with no name (got %r)" % (rows[1],))
    check(rows[1].get("role") == "Trustee",
          "vacant seat: the role survives, so the seat is still counted")
    check("Vacant" not in json.dumps(
              [r for r in rows if "name" in r]),
          "vacant seat: the word reaches no name field")

    # 4. CERRO GORDO'S SUFFIX is split off the name and kept as a fact.
    got = parse(_township("bath", "Bath Appointed", _row("Pat Doe", "Trustee")))
    check(list(got) == ["Bath"], "selection suffix: the township is Bath (got %s)"
          % list(got))
    check(got["Bath"].get("selection") == "Appointed",
          "selection suffix: kept as a field rather than discarded")
    got = parse(_township("union", "Union", _row("Pat Doe", "Trustee")))
    check("selection" not in got["Union"],
          "selection suffix: a county that does not say carries no field")
    # The one way stripping could do harm: a township whose own name ends in
    # one of those words. Anchored to the end of the heading AND requiring the
    # space, "Elected Township" is untouched.
    got = parse(_township("elected_grove", "Elected Grove", _row("Pat Doe", "Trustee")))
    check(list(got) == ["Elected Grove"],
          "selection suffix: only a TRAILING word is split, never a leading one")

    # 5. AN UNMEASURED OFFICE IS NOT SHIPPED under a vocabulary nothing read.
    got = parse(_township("vernon", "Vernon",
                          _row("Pat Doe", "Assessor"),
                          _row("Ann Roe", "Trustee")))
    check([o["role"] for o in got["Vernon"]["officials"]] == ["Trustee"],
          "unknown office: an Assessor row is dropped rather than shipped")

    # 6. A TOWNSHIP WITH NO OFFICIALS is absent rather than present and empty,
    #    so the builder's floors see a township leave.
    got = parse(_township("empty", "Empty"))
    check(got == {}, "a township the county names with no officials is not emitted")

    print("%d checks, %d failed" % (len(ran), len(failures)))
    return 1 if failures else 0


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    session = requests.Session()
    gate = RobotsGate(session, HEADERS["User-Agent"])
    out, failed = {}, []
    for fips, county, url in COUNTIES:
        allowed, why = gate.allows(url)
        if not allowed:
            # NOT FETCHED, and the verdict is the gate's rather than a guess --
            # `unreachable` means no answer arrived and `refused` means one did
            # and said no. The entry STAYS in COUNTIES so a county whose file
            # changes re-enters by itself on the next weekly run.
            failed.append((county, "not fetched — %s" % why))
            print("  %-14s NOT FETCHED — %s" % (county, why), file=sys.stderr)
            continue
        try:
            response = session.get(url, headers=HEADERS, timeout=TIMEOUT)
            response.raise_for_status()
            townships = parse(response.text)
        except Exception as exc:
            failed.append((county, "%s: %s" % (type(exc).__name__, exc)))
            print("  %-14s FAILED %s" % (county, exc), file=sys.stderr)
            continue
        if not townships:
            # A county that parses to zero is the two-shapes defect, or a
            # redesign. Either way it is a page to read, never a county to drop
            # quietly: the builder's floors turn this into a refusal to write.
            failed.append((county, "page parsed to zero townships"))
            print("  %-14s parsed to ZERO townships" % county, file=sys.stderr)
            continue
        people = sum(len(t["officials"]) for t in townships.values())
        out[fips] = {"county": county, "sourceUrl": url, "townships": townships}
        print("  %-14s townships=%-3d officials=%-4d phones=%-4d" % (
            county, len(townships), people,
            sum(1 for t in townships.values() for o in t["officials"]
                if o.get("phone"))))
        time.sleep(0.5)
    if failed:
        print("\n%d county page(s) did not yield:" % len(failed), file=sys.stderr)
        for county, why in failed:
            print("  %-14s %s" % (county, why), file=sys.stderr)
    with open(OUT_PATH, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("\nwrote %s (%d counties, %d townships, %d officials)" % (
        OUT_PATH, len(out), sum(len(c["townships"]) for c in out.values()),
        sum(len(t["officials"]) for c in out.values()
            for t in c["townships"].values())))


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    main()
