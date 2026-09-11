#!/usr/bin/env python3
"""Officers for the statewide library layer's district-governed cards, from AFRs.

il/index.html draws 550 library cards across 72 counties through
`statewideLibraryEntry`, off a statewide broadband-office boundary layer that
carries a library's name, how it is governed, and no contact of any kind. Every
one of those cards named the library and nothing else — no trustee, no address,
no telephone. That is the `statewide-library-officials` gap. Nothing was
blocking it; no record said it was missing until 2026-09-10.

The libraries publish it themselves. Every Illinois unit of local government
files an Annual Financial Report with the Comptroller, whose Contact
Information section names role-holders with the title the unit filed.
comptroller_afr.py carries that route and its rules, including which contact
values a filing witnesses as the unit's rather than one filer's. This file
carries only what is specific to the library layer.

Only the district class is in scope, and the other two are excluded by reason
rather than left unmatched. Of the 550 cards, 371 are district-governed (365
`District` + 6 `District (contracting)`) and file their own AFR. 140 are
municipal (114 City, 24 Village, 1 Village (contracting), 1 Town): a municipal
library is covered by its city's or village's report and has no unit to look up,
the shape Minonk City Library takes in Woodford and Sun River Terrace in
Kankakee. 39 are township: those file as or within a township, and a township
library's board is not the township's board, so reading a township's filing here
would name the wrong body.

The join is statewide by name and cannot be per-county. The boundary layer clips
each library's service area to the county, so a district spanning counties draws
a card in every county it touches while filing once, under its home county.
Matching each card against its own county's units resolves only 124 of 371
(measured 2026-09-10). Indexed statewide instead, the 371 cards carry 216
distinct names against 378 unit labels, and one filing stamps every county's card
for the same library. That is why this is one scraper rather than 72 county
tables. 180 of the 339 stamped cards carry a library filing in another county,
and sixteen of those filing counties are not among the 72 the layer draws,
including seven the app does not serve at all (Bureau, Christian, Fayette, Ford,
Henderson, Lawrence, Piatt). So the index is all 102 counties and not the 72.

The match is three mechanical steps and nothing else, because the two publishers
abbreviate differently and neither is wrong. Measured 2026-09-11, and the run
prints this split every time rather than leaving it to this file:

  1. Exact on the Warehouse's own label. None. The index is keyed on the label
     the Warehouse prints before " - a ", which carries no governance words, so
     "Alpha Park" never equals the card's "Alpha Park Public Library District".
     An earlier version of this docstring claimed 171 here; it was never
     measured. The step is kept because it is the strictest test available and
     costs one dict lookup, and because the boundary layer's names come from a
     third party that could start publishing bare labels.
  2. Mechanical normalisation: case, `&` and `/` to "and", punctuation dropped,
     `Mt.`/`St.`/`Co.` expanded, trailing governance words stripped iteratively
     (the first draft stripped once, which is why "Illinois Prairie District
     Public Library" missed "Illinois Prairie"), and a space-blind retry so
     "LaHarpe" reaches "La Harpe". 192 names, no ambiguity.
  3. A single trailing qualifier — Area, Community, Regional, Township(s) —
     dropped from the card's name only, and only when the result is unique
     statewide and the unit's county is one the card appears in. 7 more names,
     each printed with the unit it reached.

Nothing semantic is allowed. Step 3's county gate refused two matches that read
as obviously right: Centralia Regional against Marion's "Centralia" unit, and
Milan-Blackhawk Area against Rock Island's "Milan-Blackhawk". Those units' home
counties draw no statewide card, so nothing here witnesses that the two names are
one body, and both stay in the residue. Refusing two probably-correct matches is
the right failure direction for officeholder data: "Gilman-Danforth" is not
"Gilman Area" and "Central" is not "Centralia", and no fuzzy matcher can be
trusted to know the difference.

The residue is three different things. Of the 216 names, 199 resolve to a unit
and 197 of those file a readable contact block; the other 17 do not resolve. So
19 names go unshipped: 15 whose name matches no unit anywhere in Illinois, 2 the
county gate refused, and 2 that resolve to a unit whose landing page carries no
fiscal year and therefore has no report to read — Auburn (083/040/10) and Carrier
Mills-Stonefort (082/005/10), which ship the run a filing appears, as Mazon Fire
does in Grundy. All three classes print every run with the counties their cards
appear in, so a later change can settle each against the library's own
publication rather than against a string distance.

The county list is the one hand-kept thing here and it was wrong on the first
run. COUNTIES held 101 of Illinois's 102, missing St. Clair, the county with more
library cards than any other in the layer, and the run reported 17 of its 19 as
libraries filed under no name anywhere in Illinois. That is a false statement
about seventeen real library boards, produced by a typed list rather than by
anything the source did. The unit floor did not catch it (371 still cleared 300)
and the per-county retry covers a refusal rather than an omission. unit_index now
compares the list's length to 102.

One label is ambiguous statewide: "Washington" is a Public Library District in
Tazewell County and another in Washington County. The same county gate settles
it, which is why that gate applies to disambiguation as well as to step 3. An
ambiguous name is not an absent one — where two units share a name and neither
sits in a county the card appears in, the residue says so and names both. The
fall-through message this replaced would have reported a filed library as filed
nowhere in Illinois.
"""

import argparse
import collections
import datetime
import difflib
import json
import os
import re
import sys
import time

from comptroller_afr import (  # noqa: E402  (shared machinery — do not fork)
    PACE, SEARCH_FORM, WAREHOUSE, contact_block, enumerate_county, new_session)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA = os.path.join(REPO_ROOT, "il", "data", "app")
APP_HTML = os.path.join(REPO_ROOT, "il", "index.html")

# Every Illinois county, because a library serving one of the 72 may file in a
# county that has no statewide card of its own — Fossil Ridge files in Will,
# Cordova in Rock Island. Indexing fewer would lose exactly those.
COUNTIES = (
    "Adams", "Alexander", "Bond", "Boone", "Brown", "Bureau", "Calhoun", "Carroll", "Cass",
    "Champaign", "Christian", "Clark", "Clay", "Clinton", "Coles", "Cook", "Crawford",
    "Cumberland", "Dekalb", "Dewitt", "Douglas", "Dupage", "Edgar", "Edwards", "Effingham",
    "Fayette", "Ford", "Franklin", "Fulton", "Gallatin", "Greene", "Grundy", "Hamilton",
    "Hancock", "Hardin", "Henderson", "Henry", "Iroquois", "Jackson", "Jasper", "Jefferson",
    "Jersey", "Jo Daviess", "Johnson", "Kane", "Kankakee", "Kendall", "Knox", "Lake",
    "Lasalle", "Lawrence", "Lee", "Livingston", "Logan", "Macon", "Macoupin", "Madison",
    "Marion", "Marshall", "Mason", "Massac", "Mcdonough", "Mchenry", "Mclean", "Menard",
    "Mercer", "Monroe", "Montgomery", "Morgan", "Moultrie", "Ogle", "Peoria", "Perry",
    "Piatt", "Pike", "Pope", "Pulaski", "Putnam", "Randolph", "Richland", "Rock Island",
    "St. Clair", "Saline", "Sangamon", "Schuyler", "Scott", "Shelby", "Stark", "Stephenson",
    "Tazewell",
    "Union", "Vermilion", "Wabash", "Warren", "Washington", "Wayne", "White", "Whiteside",
    "Will", "Williamson", "Winnebago", "Woodford",
)

UNIT_TYPE = " - a Public Library District in "

# Trailing governance words, stripped iteratively from both sides of the match.
# A BARE TRAILING "public" IS HERE BECAUSE THE WAREHOUSE'S LABELS CARRY ONE.
# Its label is the unit's name with the governance words already removed, so
# "Macomb Public Library District" files as "Macomb Public" — the card strips
# the whole phrase and reaches "macomb" while the unit stopped at
# "macomb public", and the two never met. That put a real library board in the
# residue as "filed nowhere in Illinois" (measured 2026-09-11; the other
# fourteen names in that class genuinely file nothing, by two searches each).
# Stripping one more word makes a key shorter and so likelier to collide, which
# is why the run's own ambiguity report is the check: no two of the 373 card
# names collide on it, and a unit collision is reported rather than matched.
TAIL = ("public library district", "library district", "district library",
        "public library", "district", "library", "public")
# Abbreviations the Warehouse uses and the boundary layer spells out.
ABBREV = ((r"\bmt\b", "mount"), (r"\bst\b", "saint"), (r"\bco\b", "county"),
          (r"\bpub\b", "public"), (r"\bdist\b", "district"), (r"\bmem\b", "memorial"))
# Step 3 only. Dropped from the CARD's name, one word, gated twice — see the
# module docstring for why this list is short and why it is not extended.
QUALIFIERS = ("area", "community", "regional", "townships", "township")

# The county slug the app keys a card by -> the Warehouse's spelling. Only the
# slugs whose punctuation differs need a row; the comparison is punctuation- and
# space-blind, so this exists to make the two vocabularies explicit rather than
# to do work the normaliser already does.
SLUG_COUNTY = {"jo-daviess": "Jo Daviess", "st-clair": "St. Clair",
               "rock-island": "Rock Island"}

# A governance type this scraper answers for. Anything else is excluded with a
# reason rather than reported as a failure to match.
IN_SCOPE = ("District",)          # matches "District" and "District (contracting)"
OUT_OF_SCOPE = {
    "City": "a municipal library, which files inside its city's own report",
    "Village": "a municipal library, which files inside its village's own report",
    "Village (contracting)": "a municipal library, which files inside its village's own report",
    "Town": "a municipal library, which files inside its town's own report",
    "Township": "a township library, which files as or within a township — and a "
                "township library's board is not the township's board",
}

# How many times a county's index request is retried before the run is
# abandoned. See unit_index for why abandoning is the only other option.
INDEX_RETRIES = 3

SINGULAR_OFFICES = {"president", "acting president", "vice president",
                    "treasurer", "secretary", "sec./treas.", "chairman",
                    "chief", "director", "acting director"}


def fail(msg):
    sys.exit("il-library-district-officials: FATAL — " + msg)


def surname(name):
    parts = [p for p in (name or "").replace(",", " ").split() if p]
    return parts[-1].lower() if parts else ""


def drop_refiled_duplicates(name, officers, notes):
    """Drop a singular office filed twice under one near-identical name.

    The rule Grundy's Prairie Creek Library earned and Kankakee's Otto Fire
    confirmed the next day. Every drop is printed, so a board never quietly
    loses a row.
    """
    kept, seen = [], {}
    for bucket, person in officers:
        role = (person.get("role") or "").strip().lower()
        if role in SINGULAR_OFFICES and role in seen:
            first = seen[role]
            close = difflib.SequenceMatcher(
                None, surname(first["name"]), surname(person["name"])).ratio()
            if close >= 0.8:
                notes.append("%s files %s twice — kept %r, dropped %r (one "
                             "person, two spellings)"
                             % (name, person.get("role"), first["name"],
                                person["name"]))
                continue
        if role in SINGULAR_OFFICES:
            seen.setdefault(role, person)
        kept.append((bucket, person))
    return kept


def normalise(name):
    """Mechanical only: case, separators, punctuation, abbreviations, tail."""
    text = name.lower().replace("&", " and ").replace("/", " and ")
    text = " ".join(re.sub(r"[^a-z0-9 ]+", " ", text).split())
    for pattern, replacement in ABBREV:
        text = re.sub(pattern, replacement, text)
    text = " ".join(text.split())
    changed = True
    while changed:
        changed = False
        for suffix in TAIL:
            if text.endswith(" " + suffix):
                text = text[: -len(suffix) - 1].strip()
                changed = True
                break
    return text


def same_county(unit_county, card_slugs):
    """Is this unit filed in a county one of its cards appears in?"""
    flat = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    want = flat(unit_county)
    return any(flat(SLUG_COUNTY.get(slug, slug)) == want for slug in card_slugs)


def statewide_library_counties():
    """The county slugs il/index.html dispatches through statewideLibraryEntry."""
    with open(APP_HTML, encoding="utf-8") as fh:
        html = fh.read()
    keys = sorted(set(re.findall(
        r'statewideLibraryEntry\(\{\s*key:\s*"([a-z\-]+)"', html)))
    if len(keys) < 50:
        fail("found only %d statewideLibraryEntry keys in il/index.html — the "
             "dispatch table changed shape" % len(keys))
    return keys


def shipped_cards(slugs):
    """-> ({library name: governance type}, {library name: [county slug]})."""
    kinds, where = {}, collections.defaultdict(list)
    for slug in slugs:
        path = os.path.join(APP_DATA, "%s-library-districts.json" % slug)
        if not os.path.exists(path):
            fail("%s is dispatched but %s is missing" % (slug, path))
        with open(path, encoding="utf-8") as fh:
            geojson = json.load(fh)
        for feature in geojson.get("features") or []:
            props = feature.get("properties") or {}
            name = props.get("library")
            if not name:
                fail("a feature in %s carries no `library` name — the boundary "
                     "file changed shape" % path)
            kinds[name] = props.get("type")
            where[name].append(slug)
    return kinds, where


def unit_index(session):
    """-> {normalised label: [(code, text, county)]} for every library district."""
    # Illinois has 102 counties and the first version of this tuple held 101. It
    # was missing St. Clair, the county with the most library cards in the layer,
    # and the run reported 17 of its 19 as libraries filed under no name anywhere
    # in Illinois. The per-county retry below covers a refusal, not an omission,
    # and the unit floor did not catch it because 371 units still cleared 300.
    if len(COUNTIES) != 102:
        fail("COUNTIES lists %d of Illinois's 102 counties — a county missing "
             "from the index unresolves every library filed there, which reads "
             "on the card exactly like a library that files nothing"
             % len(COUNTIES))
    exact, normed = {}, collections.defaultdict(list)
    total = 0
    for county in COUNTIES:
        # ONE HUNDRED AND TWO SEQUENTIAL REQUESTS WILL MEET A BLIP, and a
        # partial index is the one failure this scraper must never ship: a
        # county dropped from it silently unresolves every library filed there,
        # which reads on the card exactly like a library that files nothing. So
        # each county is retried before the run is abandoned, and the run IS
        # abandoned rather than completed short. The first live run died on
        # Hamilton with a proxy reset at county 33 of 102.
        units, last = None, None
        for attempt in range(INDEX_RETRIES + 1):
            time.sleep(PACE * (attempt + 1))
            try:
                units = enumerate_county(session, county)
                break
            except Exception as exc:  # noqa: BLE001
                last = exc
        if units is None:
            fail("the Warehouse refused %s County after %d attempt(s) (%s) — a "
                 "partial index would silently drop every library filed there"
                 % (county, INDEX_RETRIES + 1, last))
        for code, text in units:
            if UNIT_TYPE not in text:
                continue
            label = text.split(" - a ")[0].strip()
            exact.setdefault(label.lower(), []).append((code, text, county))
            key = normalise(label)
            normed[key].append((code, text, county))
            normed[key.replace(" ", "")].append((code, text, county))
            total += 1
    if total < 300:
        fail("indexed only %d Public Library District units statewide — the "
             "search changed shape" % total)
    return exact, normed, total


def resolve(name, card_slugs, exact, normed):
    """-> ((code, text, county), how) or (None, why not). Three steps, no more."""
    def unique(units):
        codes = {u[0] for u in units or ()}
        if len(codes) == 1:
            return units[0]
        if len(codes) > 1:
            # One label, two units statewide. The card's own counties settle it.
            here = [u for u in units if same_county(u[2], card_slugs)]
            if len({u[0] for u in here}) == 1:
                return here[0]
        return None

    hit = unique(exact.get(name.lower()))
    if hit:
        return hit, "exact"
    key = normalise(name)
    hit = unique(normed.get(key)) or unique(normed.get(key.replace(" ", "")))
    if hit:
        return hit, "normalised"
    for qualifier in QUALIFIERS:
        if not key.endswith(" " + qualifier):
            continue
        base = key[: -len(qualifier) - 1].strip()
        hit = unique(normed.get(base)) or unique(normed.get(base.replace(" ", "")))
        if hit and same_county(hit[2], card_slugs):
            return hit, "qualifier:" + qualifier
        if hit:
            return None, ("dropping %r reaches %s, whose county is not one this "
                          "card appears in" % (qualifier, hit[1]))
        break
    # `unique` returns nothing both when the name is missing and when two units
    # share it and none sits in a county this card appears in. Reporting the
    # second as the first would state something false, so they are told apart
    # here rather than in the message.
    shared = (exact.get(name.lower()) or normed.get(key)
              or normed.get(key.replace(" ", "")) or [])
    if shared:
        return None, ("%d units share that name statewide and none is in a "
                      "county this card appears in: %s"
                      % (len({u[0] for u in shared}),
                         "; ".join(sorted({u[1] for u in shared}))))
    return None, "no unit of this name is filed anywhere in Illinois"


def match_breakdown(resolved):
    """How each name was matched, printed every run.

    The docstring above used to claim a split between the three steps and
    nothing measured it: its first version said 171 exact, where the run reports
    none at all. The index is keyed on the Warehouse's own label, which carries
    no governance suffix, so `Alpha Park` never equals `Alpha Park Public Library
    District` and almost every name arrives through step 2. The counts move as
    either publisher re-words a name, and step 3 is the one that drops a word
    from the card's name, so a shift toward it belongs on the run rather than in
    a re-read of this file.
    """
    counts = collections.Counter(how for _, how in resolved.values())
    return ", ".join("%s %d" % (how, n) for how, n in sorted(counts.items()))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--index-only", action="store_true",
                    help="resolve names and report, without reading any filing")
    args = ap.parse_args()

    slugs = statewide_library_counties()
    kinds, where = shipped_cards(slugs)
    districts = sorted(n for n, t in kinds.items()
                       if str(t or "").startswith(IN_SCOPE))
    if not districts:
        fail("no District-governed library appears in any shipped file")

    session = new_session()
    exact, normed, unit_total = unit_index(session)
    print("indexed %d Public Library District units across %d counties"
          % (unit_total, len(COUNTIES)), file=sys.stderr)

    resolved, unresolved = {}, []
    for name in districts:
        hit, how = resolve(name, where[name], exact, normed)
        if hit:
            resolved[name] = (hit, how)
        else:
            unresolved.append((name, how, sorted(where[name])))

    if args.index_only:
        for name, (hit, how) in sorted(resolved.items()):
            print("  %-12s %-46s -> %s" % (how, name, hit[1]), file=sys.stderr)
        for name, why, counties in unresolved:
            print("  UNRESOLVED   %-46s %s (cards in %s)"
                  % (name, why, ", ".join(counties)), file=sys.stderr)
        print("matched by: %s" % match_breakdown(resolved), file=sys.stderr)
        print("resolved %d of %d District-governed names"
              % (len(resolved), len(districts)), file=sys.stderr)
        return

    warnings, notes, libraries, blocks = [], [], {}, {}
    for name in sorted(resolved):
        (code, text, county), how = resolved[name]
        if code not in blocks:
            time.sleep(PACE)
            blocks[code] = contact_block(session, code, text, warnings)
        block = blocks[code]
        if not block:
            unresolved.append((name, "unit %s files no contact block" % code,
                               sorted(where[name])))
            continue
        entry = {"comptrollerCode": code, "filedFor": block["filedFor"],
                 "filesIn": county, "office": {}}
        for field, value in (("address", block["street"]), ("city", block["city"]),
                             ("phone", block["phone"]), ("email", block["email"])):
            if value:
                entry["office"][field] = value
        for bucket, person in drop_refiled_duplicates(name, block["officers"], notes):
            entry.setdefault(bucket, []).append(person)
        libraries[name] = entry

    if not libraries:
        fail("no library files a contact block — the search or the form broke")

    out_of_scope = collections.Counter()
    for name, kind in kinds.items():
        if not str(kind or "").startswith(IN_SCOPE):
            out_of_scope[kind] += len(where[name])

    payload = {
        "source": "Illinois Comptroller, Annual Financial Report — Contact Information",
        "sourceUrl": WAREHOUSE,
        "officialsPage": SEARCH_FORM,
        "generated": datetime.datetime.now(datetime.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "libraries": libraries,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")

    for warning in warnings:
        print("  WARN: %s" % warning, file=sys.stderr)
    for note in notes:
        print("  DUPLICATE: %s" % note, file=sys.stderr)
    for name, why, counties in sorted(unresolved):
        print("  UNRESOLVED: %s — %s (cards in %s)"
              % (name, why, ", ".join(counties)), file=sys.stderr)
    for kind, cards in sorted(out_of_scope.items()):
        print("  OUT OF SCOPE: %d card(s) governed %r — %s"
              % (cards, kind, OUT_OF_SCOPE.get(kind, "not a library district")),
              file=sys.stderr)
    board = sum(len(v.get("board") or []) for v in libraries.values())
    heads = sum(len(v.get("heads") or []) for v in libraries.values())
    stamped = sum(len(where[n]) for n in libraries)
    print("matched by: %s" % match_breakdown(resolved), file=sys.stderr)
    print("scraped %d of %d District-governed librar(ies), stamping %d card(s): "
          "%d board officer(s), %d appointed -> %s"
          % (len(libraries), len(districts), stamped, board, heads, args.out),
          file=sys.stderr)


if __name__ == "__main__":
    main()
