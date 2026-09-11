#!/usr/bin/env python3
"""Office address and telephone for the statewide library layer's cards, from L2.

il/index.html draws 550 library cards across 72 counties. 339 of them name a
board from the library's own Annual Financial Report
(il_library_district_officials_scraper.py). The other 211 name nobody and
nothing, because only a district-governed library files an AFR: a municipal
library is covered by its city's or village's report, and a township library
files as or within a township, whose board is not the library's board. That is
the statewide-library-officials gap, narrowed on 2026-09-11 and still open on the
people half.

This half answers the location and contact rows, for those 211 and for the 339
whose filings leave one out. The three Illinois library systems — Chicago Public
Library, RAILS and Illinois Heartland — run a shared public directory known as
L2, and every public library in the state has a row in it.

It does not answer the officers and does not try to. Each row links a staff list
at /directory-staff/<id>, which returns HTTP 403 with "Sign in for Full Access to
Events, Libraries, and People". That is an access control and is not worked
around.

WHICH PATH, AND WHY IT IS WORTH STATING. The rows come from the rendered page at
/directory?type=124&page=N, one HTML table per page, 41 pages of 20. A Drupal
directory of this shape often serves the same rows from a REST endpoint, and
librarylearning.org/robots.txt closes that one: the `User-agent: *` group carries
`Disallow: /restapi/*`. Nothing here fetches it. That same group allows
/directory, names no vendor crawler, and disallows only brandwatch.net wholesale,
so this scraper's `districtry/1.0` token follows `*` and is free to read the
directory.

THE JOIN IS ON THE FULL NAME, NOT A NORMALISED ONE, and that is what makes it
safe. 346 of the layer's 373 card names appear in L2 spelled identically, so no
inference is involved. Four more match only after
il_library_district_officials_scraper.normalise, and all four are printed on every
run because they are the only places a judgment is made: Coulterville Public
Library against Coulterville District Library, Elizabeth Township Library against
Elizabeth Township Public Library, North Pike Library District against North Pike
District Library, and Potomac Public Library against Potomac Public Library
District. A normalised match ships only where the key names exactly one card and
exactly one directory row; anything else is reported and dropped.

THERE IS NO PLACE GATE HERE, AND THE FIRST DRAFT HAD ONE. It required the city L2
prints to sit inside one of the counties the card appears in, and it produced
FALSE REJECTIONS, because a library legitimately sits outside the counties its
card covers: the layer clips each service area to the county, so River Valley
District Library draws a Henry County card from its building in Port Byron, Rock
Island County. The AFR route already measured how normal that is — 180 of its 339
stamped cards carry a library filing in another county. Exact-name matching
removes the need: it resolved by itself both collisions the gate was written for,
Lincoln Public Library District in Logan against Springfield's Lincoln Library,
and the two Odells in Livingston and Whiteside.

THE CHECK IS THE OTHER PUBLISHER. 184 of the 197 AFR libraries are also in L2.
Where both carry a street address 112 of 118 agree; where both carry a telephone
130 of 137 agree. The filing's value ships in either case, because it is the
unit's own return, and every difference prints so a later pass can settle it.
What L2 adds is what the filings leave out: 66 of the 184 carry no street address
and L2 has one for all of them, and 47 carry no telephone.

THE ADDRESS CELL HAS NO DELIMITER and the census place list splits it. L2 prints
"205 East Olive Street Bloomington , IL 61701" as one cell, so the city is found
as the longest known place name ending immediately before " , IL"; all 641
administrative-entity rows end in that shape. TIGERweb's Incorporated Places and
Census Designated Places layers give all 1,294 Illinois places and 167 CDPs in two
requests, need no API key, and need no geometry, because each row carries its
interior point as attributes. THE LIST MUST BE THE WHOLE STATE: the first draft
used only places inside the 72 counties and failed to split 58 rows, Peoria and
Cahokia among them, and mis-split Port Byron as Byron. api.census.gov is not a
route — it answers "Missing Key" to an unauthenticated request.

FIVE LIBRARIES ARE ADDRESSED AT ANOTHER LIBRARY'S BUILDING and the host's name
ships rather than being stripped, because a reader looking for the building needs
it: Dixmoor at William Leonard Public Library District, Golden Prairie at
Bloomington Public Library, Hooppole at Annawan Alba Township Library,
Milan-Blackhawk at Rock Island Public Library, and Rock River at Silvis Public
Library. One more, Flanagan, leads with a post-office box before its street. Both
shapes are published as they stand.

E-MAIL IS NOT SHIPPED FROM THIS SOURCE. 633 of the 641 rows carry one, and they
are a mix of institutional mailboxes (acorn@acornlibrary.org) and named
individuals' work addresses (medjo@addisonlibrary.org). The AFR route ships an
e-mail only where the filing witnesses it as the unit's; a directory row cannot
make that distinction, so this one carries the address and telephone and leaves
the mailbox alone.
"""

import argparse
import collections
import datetime
import html
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from il_library_district_officials_scraper import (  # noqa: E402
    normalise, shipped_cards, statewide_library_counties)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA = os.path.join(REPO_ROOT, "il", "data", "app")

SOURCE = ("Illinois library systems' shared directory (L2) — Chicago Public "
          "Library, RAILS and Illinois Heartland")
DIRECTORY = "https://librarylearning.org/directory"
LISTING = DIRECTORY + "?type=124&page=%d"
UA = "districtry/1.0 (+https://districtry.com/il/)"
PACE = 1.0                       # one request a second, as with every state site
MAX_PAGES = 60                   # 41 today; a guard, not an expectation

TIGERWEB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
            "Places_CouSub_ConCity_SubMCD/MapServer/%d/query")
PLACE_LAYERS = ((4, "incorporated places"), (5, "census designated places"))
MIN_PLACES = 1200                # 1,461 measured; a short list mis-splits addresses

AFR_FILE = os.path.join(APP_DATA, "il-library-district-officials.json")
PRIMARY = "(Primary Building)"
CITY_TAIL = re.compile(r"\s*,\s*IL\s+\d{5}(?:-\d{4})?\s*$")
PHONE = re.compile(r"(\d{3})-(\d{3})-(\d{4})")
MAX_CITY_WORDS = 4               # "East Saint Louis", "Village of Lakewood"


def fail(msg):
    sys.exit("il-library-contacts: FAIL — " + msg)


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(text).replace(PRIMARY, "")
                  .replace("\xa0", " ")).strip()


def place_key(name):
    """A place name reduced for lookup only.

    L2 and the census disagree on spacing and on Saint: the directory writes
    DuQuoin, DeLand, La Salle, East Saint Louis where TIGERweb has Du Quoin, De
    Land, LaSalle, East St. Louis. Folding both to the same key matches them
    without inventing anything.
    """
    text = re.sub(r"[^A-Za-z0-9 ]+", "", html.unescape(name)).upper()
    text = re.sub(r"\bSAINT\b", "ST", text)
    return re.sub(r"\s+", "", text)


def session():
    import requests
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    return s


def place_names(sess):
    """-> {PLACE NAME} for every incorporated place and CDP in Illinois."""
    names, total = set(), 0
    for layer, kind in PLACE_LAYERS:
        time.sleep(PACE)
        r = sess.get(TIGERWEB % layer, timeout=90, params={
            "where": "STATE='17'", "outFields": "BASENAME",
            "returnGeometry": "false", "f": "json"})
        r.raise_for_status()
        body = r.json()
        if body.get("exceededTransferLimit"):
            fail("TIGERweb paged the %s layer — the list is incomplete" % kind)
        for feature in body.get("features") or []:
            names.add(place_key(feature["attributes"]["BASENAME"]))
            total += 1
    if total < MIN_PLACES:
        fail("TIGERweb returned only %d Illinois places — the query changed shape"
             % total)
    print("indexed %d Illinois places and CDPs, %d distinct names"
          % (total, len(names)), file=sys.stderr)
    return names


def cells(row_html):
    return [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", cell)).strip()
            for cell in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)]


def listing(sess):
    """-> [(name, contact cell, address cell)] for every (Primary Building) row."""
    rows, page = [], 0
    while page < MAX_PAGES:
        time.sleep(PACE)
        r = sess.get(LISTING % page, timeout=60)
        if r.status_code != 200:
            fail("%s answered %s" % (LISTING % page, r.status_code))
        got = 0
        for block in re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, re.S):
            cell = cells(block)
            if len(cell) >= 3 and cell[0]:
                got += 1
                if PRIMARY in cell[0]:
                    rows.append((clean(cell[0]), cell[1], cell[2]))
        if not got:
            break
        page += 1
    if page >= MAX_PAGES:
        fail("the listing did not end within %d pages" % MAX_PAGES)
    if not rows:
        fail("no %s row on any page — the table changed shape" % PRIMARY)
    print("read %d page(s), %d administrative-entity row(s)" % (page, len(rows)),
          file=sys.stderr)
    return rows


STREET_TYPE = re.compile(
    r"\b(?:STREET|ST|AVENUE|AVE|ROAD|RD|DRIVE|DR|LANE|LN|BOULEVARD|BLVD|PLACE|"
    r"PL|COURT|CT|HIGHWAY|HWY|CIRCLE|CIR|TERRACE|TER|TRAIL|PARKWAY|PKWY|WAY|"
    r"SQUARE|SQ|PIKE|BOX)\b", re.I)


def split_address(cell, names):
    """-> (street, city, from_census) or (None, None, False).

    Longest census match wins, which is what tells Port Byron from Byron. Where
    no census name matches, the city is the run of words after the last
    street-type word — Cahokia village was absorbed into Cahokia Heights in 2021
    and North Utica renamed, so the directory names places the current census
    fabric does not, and dropping those addresses would cost a real library its
    location. Every city derived that way prints on the run.
    """
    cell = re.sub(r"\s+", " ", clean(cell))
    tail = CITY_TAIL.search(cell)
    if not tail:
        return None, None, False
    head = cell[: tail.start()].strip()
    words = head.split()
    for take in range(min(MAX_CITY_WORDS, len(words)), 0, -1):
        candidate = " ".join(words[-take:])
        if place_key(candidate) in names:
            return (" ".join(words[:-take]).strip(" ,") or None), candidate, True
    last = None
    for i, word in enumerate(words):
        if STREET_TYPE.fullmatch(word.strip(".,")) or word.strip(".,").isdigit():
            last = i
    if last is None or last + 1 >= len(words):
        return None, None, False
    city = " ".join(words[last + 1:])
    if len(city.split()) > MAX_CITY_WORDS or STREET_TYPE.search(city):
        return None, None, False
    return (" ".join(words[: last + 1]).strip(" ,") or None), city, False


ABBREV = (("STREET", "ST"), ("AVENUE", "AVE"), ("ROAD", "RD"), ("DRIVE", "DR"),
          ("NORTH", "N"), ("SOUTH", "S"), ("EAST", "E"), ("WEST", "W"),
          ("BOULEVARD", "BLVD"), ("PLACE", "PL"), ("COURT", "CT"),
          ("HIGHWAY", "HWY"), ("SUITE", "STE"), ("FIRST", "1"), ("SECOND", "2"),
          ("THIRD", "3"), ("FOURTH", "4"), ("FIFTH", "5"), ("SIXTH", "6"),
          ("SEVENTH", "7"), ("EIGHTH", "8"), ("NINTH", "9"), ("TENTH", "10"))


def has_street(value):
    """Does this address name a place, or only a post-office box?

    "Office" names a place on the card. 15 of the 138 addresses the filings carry
    are a box and no street, so the directory's street is not a competing answer
    there — it is the only one.
    """
    return bool(street_key(value))


def street_key(value):
    """A street reduced for comparison only. Never shipped."""
    text = (value or "").upper()
    text = re.sub(r"\bP\.?\s?O\.?\s?BOX\b\s*\d*|\bPOST OFFICE BOX\b\s*\d*", " ", text)
    # The apostrophe goes rather than becoming a space: the filings write
    # OBANNON where the directory writes O'Bannon.
    text = text.replace("'", "").replace("\u2019", "")
    text = re.sub(r"[.,#/;]", " ", text)
    for long, short in ABBREV:
        text = re.sub(r"\b%s\b" % long, short, text)
    return " ".join(text.split())


DIRECTIONAL = {"N", "S", "E", "W", "NE", "NW", "SE", "SW"}
ORDINAL = re.compile(r"^(\d+)(?:ST|ND|RD|TH)$")
WORD_NUMBER = {"FIRST": "1", "SECOND": "2", "THIRD": "3", "FOURTH": "4",
               "FIFTH": "5", "SIXTH": "6", "SEVENTH": "7", "EIGHTH": "8",
               "NINTH": "9", "TENTH": "10", "ELEVENTH": "11", "TWELFTH": "12"}


def address_pair(value):
    """-> (house number, street name) or None, for comparison only.

    THE TWO PUBLISHERS WRITE THE SAME ADDRESS MANY WAYS. The filings abbreviate
    and drop words the directory spells out: "220 SOUTH 5TH STREET" against "220
    South Fifth Street", "109 OBANNON ST" against "109 South O'Bannon Street",
    "100 Library Ln" against "100 Library Lane", "1205 State St Litchfield, IL
    62056" against "1205 South State Street". Comparing the full strings called
    60 of those a disagreement and buried the twelve that are real, so the test
    is the house number and the first distinctive street word — which is what
    tells 308 North Wilmor from 380 North Wilmor, and 500 Wabash from 250 North
    1st.
    """
    words = street_key(value).split()
    for i, word in enumerate(words):
        if word.isdigit():
            for rest in words[i + 1:]:
                rest = WORD_NUMBER.get(rest, rest)
                ordinal = ORDINAL.match(rest)
                if ordinal:
                    rest = ordinal.group(1)
                if rest in DIRECTIONAL or STREET_TYPE.fullmatch(rest):
                    continue
                return word, rest
            return word, ""
    return None


def agrees(field, filed, listed):
    """Do the two publishers say the same thing?"""
    if field == "phone":
        return re.sub(r"\D", "", filed) == re.sub(r"\D", "", listed)
    a, b = address_pair(filed), address_pair(listed)
    return bool(a) and a == b


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    slugs = statewide_library_counties()
    kinds, _ = shipped_cards(slugs)
    sess = session()
    names = place_names(sess)
    rows = listing(sess)

    with open(AFR_FILE, encoding="utf-8") as fh:
        afr = json.load(fh)["libraries"]

    # THE NAME CELL IS THE AGENCY FOLLOWED BY THE BUILDING'S OWN NAME on the
    # rows that have one — "Rockford Public Library Main Library",
    # "Cairo Public Library A.B. Safford Memorial Library",
    # "Arthur Public Library District John E. Timm Memorial Building". RAILS's own
    # listing calls these the parent agencies. Matching the whole cell found 346
    # cards and missed 23 real libraries for that reason alone, so a card also
    # matches a row whose name begins with the card's name and a space — the
    # agency portion, still exact — and only where exactly one unclaimed row does.
    by_exact = collections.defaultdict(list)
    by_norm = collections.defaultdict(list)
    for row in rows:
        by_exact[row[0].lower()].append(row)
        by_norm[normalise(row[0])].append(row)
    cards_by_norm = collections.defaultdict(list)
    for card in kinds:
        cards_by_norm[normalise(card)].append(card)

    chosen, claimed, ambiguous, unmatched = {}, set(), [], []
    prefixed, loose = [], []
    for card in sorted(kinds):                      # exact first, so it wins
        found = by_exact.get(card.lower()) or []
        if len(found) > 1:
            ambiguous.append((card, [r[0] for r in found]))
        elif found:
            chosen[card] = found[0]
            claimed.add(id(found[0]))
    for card in sorted(kinds):                      # then the agency prefix
        if card in chosen or any(c == card for c, _ in ambiguous):
            continue
        head = card.lower() + " "
        found = [r for r in rows
                 if r[0].lower().startswith(head) and id(r) not in claimed]
        if len(found) == 1:
            chosen[card] = found[0]
            claimed.add(id(found[0]))
            prefixed.append((card, found[0][0]))
        elif found:
            ambiguous.append((card, [r[0] for r in found]))
    for card in sorted(kinds):                      # then a unique normalisation
        if card in chosen or any(c == card for c, _ in ambiguous):
            continue
        key = normalise(card)
        near = [r for r in by_norm.get(key, []) if id(r) not in claimed]
        if len(near) == 1 and len(cards_by_norm[key]) == 1:
            chosen[card] = near[0]
            claimed.add(id(near[0]))
            loose.append((card, near[0][0]))
        elif near:
            ambiguous.append((card, [r[0] for r in near]))
        else:
            unmatched.append(card)

    contacts, differences, unsplit, derived = {}, [], [], []
    for card, row in sorted(chosen.items()):
        name, contact_cell, address_cell = row
        street, city, from_census = split_address(address_cell, names)
        if not city:
            unsplit.append((name, address_cell))
            continue
        if not from_census:
            derived.append((name, city, address_cell))
        entry = {"city": city}
        if street:
            entry["address"] = street
        phone = PHONE.search(contact_cell)
        if phone:
            entry["phone"] = "(%s) %s-%s" % phone.groups()
        filed = dict((afr.get(card) or {}).get("office") or {})
        if filed.get("address") and not has_street(filed["address"]):
            filed.pop("address")        # a box, so the directory's street ships
        for field in ("address", "phone"):
            if filed.get(field) and entry.get(field):
                if agrees(field, filed[field], entry[field]):
                    entry.pop(field)
                else:
                    differences.append((card, field, filed[field],
                                        entry.pop(field)))
        if not entry.get("address"):
            entry.pop("city", None)     # a city means nothing without a street
        if entry.get("address") or entry.get("phone"):
            contacts[card] = entry

    payload = {
        "source": SOURCE,
        "sourceUrl": DIRECTORY,
        "generated": datetime.datetime.now(datetime.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "libraries": contacts,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")

    for card, row in sorted(prefixed):
        print("  AGENCY PREFIX: the card %r takes the row %r" % (card, row),
              file=sys.stderr)
    for card, row in sorted(loose):
        print("  NORMALISED: the card %r takes the row %r" % (card, row),
              file=sys.stderr)
    for name, city, cell in sorted(derived):
        print("  CITY NOT IN THE CENSUS PLACE LIST: %s reads %r from %r"
              % (name, city, cell), file=sys.stderr)
    for card, found in sorted(ambiguous):
        print("  AMBIGUOUS: %s — %d directory rows could be it (%s); nothing "
              "ships rather than picking one"
              % (card, len(found), "; ".join(found)), file=sys.stderr)
    for name, cell in sorted(unsplit):
        print("  UNSPLIT: %s — no city found before the ZIP in %r"
              % (name, cell), file=sys.stderr)
    for card, field, filed, listed in sorted(differences):
        print("  DIFFERS: %s %s — filing %r, directory %r (the filing ships)"
              % (card, field, filed, listed), file=sys.stderr)
    if unmatched:
        print("  UNMATCHED: %d card name(s) have no directory row: %s"
              % (len(unmatched), ", ".join(sorted(unmatched))), file=sys.stderr)
    addr = sum(1 for v in contacts.values() if v.get("address"))
    ph = sum(1 for v in contacts.values() if v.get("phone"))
    print("matched %d of %d card name(s) — %d on the full name, %d on the agency "
          "prefix, %d on a normalisation. %d ship something the filings do not "
          "already give: %d an address, %d a telephone -> %s"
          % (len(chosen), len(kinds), len(chosen) - len(prefixed) - len(loose),
             len(prefixed), len(loose), len(contacts), addr, ph, args.out),
          file=sys.stderr)


if __name__ == "__main__":
    main()
