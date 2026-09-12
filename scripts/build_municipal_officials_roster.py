#!/usr/bin/env python3
"""
Resolve the per-county municipal-officials scraper outputs into one record per
municipality and write the JSON app-data file the Municipality card reads:
data/app/municipal-officials.json.

Keys are the 7-digit CENSUS PLACE GEOID ("17" + PLACEFP, e.g. 1701010 for
Alsip) because that is exactly the `GEOID` the app's TIGERweb places layer
already carries on every municipality feature — so the card's join needs no
name normalization at query time, and the 47 metro municipalities that span
county lines resolve to ONE entry instead of one per county
(docs/EXPANSION_GUIDE.md §3.4).

The name -> GEOID mapping comes from the Census 2020 place-by-county reference
file committed at data/source/st17_il_place_by_county2020.txt. Lookup prefers
a place in the source's own county and falls back to a statewide unique match,
which is what resolves municipalities the county clerk claims but Census lists
only under a neighbour (Oak Brook is a Cook Clerk jurisdiction but is listed
under DuPage). Only two Illinois incorporated-place names collide statewide
(Wilmington, Windsor) and neither is in the metro; an ambiguous or unmatched
name is a hard failure, never a guess.

Contact data in these sources is MUNICIPALITY-level, not per-person — in the
Cook DOEO API every official of a municipality carries the same village-hall
phone/email/address and the per-person columns are empty for all 1,134
records. It is therefore emitted once under `office`, never on a person, so
the card cannot imply a direct line to a trustee that does not exist.

Usage:
    python3 build_municipal_officials_roster.py cook_municipal_officials.json [more...] [--out-dir DIR]

Each positional argument is one county scraper's output. Counties may be
built incrementally: this rewrites the whole file from the inputs given, so
pass every county's output that should ship.
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import undeliverable  # noqa: E402  (the fleet's withhold list)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")
PLACES_FILE = os.path.join(REPO_ROOT, "il", "data", "source", "st17_il_place_by_county2020.txt")

# Census county FIPS for every sourced county, for county-preferred lookup.
COUNTY_FIPS = {
    "Cook": "031",
    "Boone": "007",
    "LaSalle": "099",
    "DuPage": "043",
    "Kane": "089",
    "Kendall": "093",
    "Lake": "097",
    "McHenry": "111",
    "Winnebago": "201",
    "Will": "197",
    "Ogle": "141",
    "Stephenson": "177",
    "Carroll": "015",
    "DeKalb": "037",
    # The pass-6 tranche (2026-08-01): eight counties whose sources the
    # validation pass verified publishable, shipped together.
    "Grundy": "063",
    "Livingston": "105",
    "Logan": "107",
    "McLean": "113",
    "Sangamon": "167",
    "Madison": "119",
    "St. Clair": "163",
    "Rock Island": "161",
    # Pass-9 (2026-08-03): three counties unlocked by ASKING their clerks, each
    # pointing at a document no search had surfaced.
    "Henry": "073",
    "Cass": "017",
    "Whiteside": "195",
    "Peoria": "143",
    # Two counties whose clerks sent a DOCUMENT rather than a link, on the same
    # day: Marshall's 5-page elected-officers table and Washington's 40-page
    # Blue Book. Neither is published on the county's website, so both are
    # archived under data/source/raw/ and parsed from there — refreshing them
    # means asking again rather than re-fetching a URL.
    "Marshall": "123",
    "Washington": "189",
    # Mason's directory is neither a website nor an archived document: it is a
    # Google Sheet the County Clerk publishes, readable by anyone with the link
    # and exportable as CSV. That is what made a scraper possible where the
    # county's board roster still needs a hand transcription from a scan.
    "Mason": "125",
    # De Witt (the Census's spacing) is the third archived-document county:
    # its Clerk's "Village/City Officials" Word document, sent by e-mail on
    # 2026-08-17 and committed under data/source/raw/.
    "De Witt": "039",
    # Macoupin's directory is a page that arrives EMPTY and fills itself from a
    # REST service beside the CMS. The service's address was recorded from a
    # browser capture on 2026-08-20 — the one step the sandbox could not take —
    # and needs no browser now that it is known.
    "Macoupin": "117",
    # Kankakee is the first RUNG-3 county: no county source names a municipal
    # officer at all, so its heads come from the regional council — the KATS
    # MPO's Policy Committee minutes. It ships FIVE of its 21 municipalities
    # by construction, because only the five MPO members sit on that
    # committee. See kankakee_municipal_officials_scraper.py.
    "Kankakee": "091",
}

# Office classification. HEAD is the single head of government; BOARD is the
# governing body's seats; OFFICERS are the other municipality-wide elected
# officers. An office name not listed here still ships (under officers) and
# prints a warning — new office types get a human's attention, never a silent
# drop.
# "acting president" is a sitting trustee wearing the gavel (Spaulding,
# Williamsville, Worden print the office exactly that way); the same person's
# trustee row legitimately coexists with it, so the scrapers' head-duplicate
# rules already exempt it.
HEAD_OFFICES = {"mayor", "president", "village president", "acting president"}
BOARD_OFFICES = {"trustee", "alderperson", "alderman", "alderwoman",
                 "council member", "commissioner", "councilman", "councilwoman",
                 "councilperson"}
OFFICER_OFFICES = {"clerk", "treasurer", "village clerk", "city clerk",
                   # The Town of Cicero elects a municipal Assessor (and a
                   # Collector, already below) — the coterminous-town officer
                   # set. Same class as comptroller: a finance officer of the
                   # corporate authorities, not a board seat.
                   "assessor",
                   "taxpayer advocate", "collector", "supervisor",
                   # Ashley (Washington County) elects one; a municipal finance
                   # officer like the treasurer beside it, not hired staff
                   "comptroller",
                   # Oak Grove (Rock Island) elects one officer to both
                   "clerk/treasurer",
                   # Waynesville (De Witt) fills both with one officer too
                   "clerk/collector",
                   # appointed staff LaSalle prints beside the elected officers;
                   # the record carries appointed=True so a card never implies
                   # these were elected
                   "deputy clerk", "administrator", "village administrator",
                   "city administrator", "city manager", "village manager",
                   "manager", "superintendent", "superintendent of public works"}

# Per-county floors: deliberate under-tolerances against the verified 2026-07
# live values (Cook 129 municipalities incl. the TWNSP-filed Town of Cicero
# / ~1,097 governing records / 130 heads incl. Chicago;
# Will 34 / 303 / 34). A real coverage loss fails the build and leaves the last
# good file in place; ordinary turnover does not.
COUNTY_FLOORS = {
    "Cook": {"municipalities": 120, "members": 900, "heads": 120},
    # Boone, a full-governing-body source from the Clerk's own yearbook
    # (2026 edition live: 5 municipalities / 47 officials / 5 heads). The
    # county has exactly five incorporated places and the book carries every
    # one in full, so the municipality floor is an equality in all but name;
    # heads sits one under because Capron publishes a vacancy from time to
    # time and one empty chair must not freeze the county.
    "Boone": {"municipalities": 5, "members": 40, "heads": 4},
    "Will": {"municipalities": 30, "members": 260, "heads": 30},
    # LaSalle, the third full-governing-body source and the first county outside
    # the metro (2026-07 live: 26 municipalities / 206 officials / 26 heads).
    "LaSalle": {"municipalities": 22, "members": 170, "heads": 22},
    # Winnebago, the fourth full-governing-body source (2026-07 live: 11
    # municipalities / 84 officials / 9 heads). HEADS IS BELOW MUNICIPALITIES ON
    # PURPOSE: WinGIS publishes no mayor/president layer for Loves Park or
    # Machesney Park, only their council seats, so a floor of 11 heads would fail
    # on correct data. See winnebago_municipal_officials_scraper.py.
    "Winnebago": {"municipalities": 10, "members": 75, "heads": 8},
    # The five mayor-level counties (2026-07 live values in parentheses). Their
    # sources publish no trustees, so `members` counts the head plus the elected
    # clerk/treasurer rows only — a floor equal to the head count would pass on
    # a run that silently lost every officer.
    "DuPage": {"municipalities": 32, "members": 32, "heads": 32},        # 36 / 36 / 36
    "Kane": {"municipalities": 26, "members": 50, "heads": 26},          # 29 / 58 / 29
    "McHenry": {"municipalities": 26, "members": 48, "heads": 24},       # 30 / 55 / 30
    "Kendall": {"municipalities": 12, "members": 28, "heads": 12},       # 14 / 34 / 14
    # Lake publishes NO officeholder names (rule-4 honesty floor), so its
    # member/head floors are 0 BY DESIGN — the municipality count is the real
    # guard. See lake_municipal_officials_scraper.py.
    "Lake": {"municipalities": 48, "members": 0, "heads": 0},            # 55 / 0 / 0
    # Kankakee reads an ATTENDANCE roll, so its floors are one under the
    # measured five rather than equal to it: a town whose head misses every
    # meeting for a year leaves the source without anything being wrong, and
    # freezing the county over that would be a worse answer than four names.
    # `members` equals `heads` because the Policy Committee seats one chief
    # elected officer per municipality and never a trustee or a clerk.
    "Kankakee": {"municipalities": 4, "members": 4, "heads": 4},          # 5 / 5 / 5
    # The northern frontier (2026-07 live values in parentheses). Ogle and
    # Stephenson are full-governing-body sources; Carroll is mayor-level, so its
    # `members` counts the head plus the clerk only.
    "Ogle": {"municipalities": 11, "members": 90, "heads": 11},          # 13 / 110 / 13
    # DeKalb, the sixth full-governing-body source, and the only one whose
    # document gives every seat's NEXT ELECTION date (2026-07 live: 14 / 118 /
    # 14). Two rows the scraper drops by rule are already excluded from that
    # count — a seat published as "Vacant" and a trustee row duplicating the
    # village president.
    "DeKalb": {"municipalities": 12, "members": 100, "heads": 12},       # 14 / 118 / 14
    # HEADS SITS BELOW MUNICIPALITIES for Stephenson because the county's page
    # still shows Dakota no president: it prints Jonathon Riley as a Trustee,
    # which the Clerk contradicted in writing on 2026-08-05, so the scraper
    # ships him as Village President from CLERK_STATED_OFFICES and the live head
    # count is 10, not 9. The floor stays at 7 rather than tracking that up —
    # it guards against a source collapsing, and pinning it to a count that
    # depends on one hand-kept correction would make the guard brittle. Freeport
    # is not counted here at all: the county page omits it and the city's own
    # payload supplies it through --enrich.
    "Stephenson": {"municipalities": 9, "members": 70, "heads": 7},      # 10 / 82 / 10
    # Carroll's whole county is seven municipalities, so the floors sit only
    # one or two under the full set. Thomson's president is vacant, which is why
    # heads is two under the municipality count rather than one.
    "Carroll": {"municipalities": 6, "members": 11, "heads": 5},         # 7 / 13 / 6
    # The pass-6 tranche (2026-08-01 live values in parentheses), all
    # full-governing-body sources — each scraper carries its own tighter
    # per-source floors, so these are the coarse back-stops.
    "Grundy": {"municipalities": 15, "members": 110, "heads": 15},       # 17 / 133 / 17
    "Livingston": {"municipalities": 14, "members": 120, "heads": 14},   # 16 / 153 / 16
    "Logan": {"municipalities": 10, "members": 75, "heads": 10},         # 11 / 92 / 11
    # McLean covers ONLY its three ward-electing cities (the county-wide
    # source is a JS-locked Airtable interface — see the scraper), so its
    # floors describe three municipalities, not a county sweep.
    "McLean": {"municipalities": 3, "members": 22, "heads": 3},          # 3 / 26 / 3
    "Sangamon": {"municipalities": 22, "members": 170, "heads": 20},     # 26 / 208 / 26
    "Madison": {"municipalities": 24, "members": 190, "heads": 24},      # 28 / 241 / 28
    "St. Clair": {"municipalities": 22, "members": 190, "heads": 22},    # 26 / 247 / 26
    "Rock Island": {"municipalities": 13, "members": 100, "heads": 13},  # 15 / 122 / 15
    # Henry (2026-08-03 live: 15 / 120 / 15). The handbook covers all fifteen of
    # the county's incorporated places, so these sit two under the full set —
    # this source cannot lose three municipalities and still be right. One of
    # those fifteen (Coal Valley) is also published by Rock Island, so the
    # county's contribution after dedupe is fourteen.
    "Henry": {"municipalities": 13, "members": 100, "heads": 13},        # 15 / 120 / 15
    # Cass (2026-08-03 live: 5 / 47 / 5). The county has exactly five
    # incorporated places and its directory carries all five in full, so these
    # sit as close to the true values as a floor sensibly can.
    "Cass": {"municipalities": 5, "members": 40, "heads": 5},            # 5 / 47 / 5
    # Whiteside (2026-08-03 live: 11 / 22 / 11) is a MAYOR-AND-CLERK source —
    # its yearbook publishes no trustees — so `members` counts the head plus the
    # clerk only, and a floor equal to the head count would pass on a run that
    # silently lost every clerk.
    "Whiteside": {"municipalities": 9, "members": 18, "heads": 9},       # 11 / 22 / 11
    # Peoria (2026-08-03 live: 15 / 140 / 15) — the largest county on this card
    # outside the collar, and the richest source in the fleet: hall address,
    # phone, e-mail AND website per municipality, plus every seat with its ward
    # or district. All fifteen of the county's incorporated places are covered.
    "Peoria": {"municipalities": 13, "members": 110, "heads": 13},       # 15 / 140 / 15
    # Mason (2026-08-04 live: 9 / 82 / 9). All nine incorporated places, each
    # with its whole body — president or mayor, clerk, treasurer and every
    # trustee or alderman — and Havana's eight aldermen carry their ward.
    "Mason": {"municipalities": 8, "members": 70, "heads": 8},           # 9 / 82 / 9
    # De Witt (2026-08-17 live: 7 / 52 / 7). The Clerk's archived document
    # covers all seven of the county's incorporated places in full — two
    # commission-form cities (mayor + commissioners) and five villages — so the
    # municipality and head floors sit at the true value: this source cannot
    # lose a municipality and still be right.
    "De Witt": {"municipalities": 7, "members": 44, "heads": 7},         # 7 / 52 / 7
    # Macoupin (2026-08-20 live: 27 / 232 / 26). All twenty-seven of the
    # county's incorporated places with their whole bodies, and all 28 wards of
    # its eight ward cities carry their number. `heads` is one under the
    # municipality count because Hettick's presidency is published vacant.
    "Macoupin": {"municipalities": 24, "members": 190, "heads": 22},     # 27 / 232 / 26
}
# Merged floor across all counties supplied. Cook + Will resolve to 156 unique
# municipalities (6 of Will's 34 are shared with Cook); the pre-tranche
# counties resolve to ~270, and the pass-6 tranche (Grundy, Livingston, Logan,
# McLean's three ward cities, Sangamon, Madison, St. Clair, Rock Island) adds
# ~140 more after cross-county dedupe.
MIN_TOTAL_MUNICIPALITIES = 380

# Placeholders county documents print where a seat has no holder. They are not
# names and never reach a card — see the drop in the person loop below.
VACANT_NAMES = {"vacant", "vacancy", "unassigned", "open", "tbd", "none",
                "n/a", "na", "-"}

# ---------------------------------------------------------------------------
# "Surname, Given" rows inside a directory that otherwise prints "Given Surname".
#
# WHY THIS IS NORMALISATION AND NOT INFERENCE, which is the only reason it is
# allowed here at all: a comma in a roster name field is the universal index
# convention for surname-first, and re-ordering around it invents nothing — the
# same characters the source published, in the order the same source uses for
# every other row. That is the argument the guidebook already makes for printing
# "Village President" where a source writes "president". Producing a name the
# source did not publish would be a different act, and this refuses it.
#
# FOUND 2026-08-06 in the shipped roster, not in a scraper: three rows across TWO
# counties were being rendered backwards on live cards — Stephenson's Dakota gained
# "Holste, McKenzie" when the county republished that village's table, and LaSalle's
# Village of Dana has shipped "Centeno, Joseph L." and "Centeno, Rebecca" all along.
# Two sources means this belongs where every roster funnels through, next to the
# vacancy guard, rather than in one county's parser.
#
# THE GUARD IS THE WHOLE DESIGN. 24 of the 27 comma-carrying names in the roster
# are suffixes — "Roy Williams, Jr.", "John W. Hamm, III" — and inverting one of
# those would produce "Jr. Roy Williams", a worse defect than the one being fixed.
# So an inversion applies only when every one of these holds: exactly one comma
# (so "Williams, Jr., Roy" is left alone and stays visible), both sides non-empty,
# the trailing side is not a known suffix, and both sides look like name text.
# Anything else ships exactly as published.
NAME_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v", "vi",
                 "md", "phd", "dds", "esq", "cpa", "ret"}
# Letters, spaces, initials, hyphens and apostrophes (straight or curly). A digit
# or a stray office word means this is not a name printed backwards.
NAME_TEXT_RE = re.compile("^[A-Za-z][A-Za-z .'’‘-]*$")
ONE_COMMA_RE = re.compile(r"^([^,]+),([^,]+)$")


def uninvert_name(name):
    """"Holste, McKenzie" -> "McKenzie Holste"; "Roy Williams, Jr." -> None.

    None means "leave it exactly as the source printed it" — both for a name
    that carries no comma and for one this refuses to touch.
    """
    m = ONE_COMMA_RE.match(str(name or "").strip())
    if not m:
        return None
    surname, given = m.group(1).strip(), m.group(2).strip()
    if not surname or not given:
        return None
    if given.replace(".", "").strip().lower() in NAME_SUFFIXES:
        return None
    if not NAME_TEXT_RE.match(surname) or not NAME_TEXT_RE.match(given):
        return None
    return "%s %s" % (given, surname)

# ---------------------------------------------------------------------------
# Preserving a blocked source's last-good entries.
#
# Several sources refuse GitHub's runner IPs outright — McHenry and Kendall
# block every rung including the Archive's crawler, and DuPage/Joliet 403 the
# datacenter ranges while answering a developer machine. Gating the build on
# all ten therefore froze the whole roster indefinitely: one permanently
# blocked county withheld every OTHER county's turnover too, which is the
# opposite of the isolation the workflow set out to provide.
#
# So a missing source no longer withdraws its data — it carries forward what is
# already shipped, and the run says exactly which sources were served that way.
# A preserved county's entries are re-inserted through the same cross-county
# precedence as a fresh build; a preserved city payload is re-applied through
# merge_contact, so it can still only FILL fields the county left empty and can
# never resurrect a seat-holder the county has since replaced.
#
# Cook and Will are not preservable: they are the only two full-governing-body
# sources, so building without either would silently ship a roster of mayors
# where councils used to be. If one of them is down, the run must fail.
REQUIRED_COUNTIES = ("Cook", "Will")
PRESERVABLE = {
    # LaSalle is a full-governing-body source like Cook and Will, but unlike them
    # it is NOT in REQUIRED_COUNTIES: Cook and Will are required because losing
    # either would silently replace councils that are already shipped with
    # mayors. LaSalle carries its own 26 municipalities and nothing else depends
    # on it, so a fetch failure should carry its last-good entries forward, not
    # fail every other county's turnover.
    "boone": {"kind": "county", "county": "Boone"},
    "lasalle": {"kind": "county", "county": "LaSalle"},
    "winnebago": {"kind": "county", "county": "Winnebago"},
    "dupage": {"kind": "county", "county": "DuPage"},
    "kane": {"kind": "county", "county": "Kane"},
    "mchenry": {"kind": "county", "county": "McHenry"},
    "kendall": {"kind": "county", "county": "Kendall"},
    "lake": {"kind": "county", "county": "Lake"},
    "ogle": {"kind": "county", "county": "Ogle"},
    "stephenson": {"kind": "county", "county": "Stephenson"},
    "carroll": {"kind": "county", "county": "Carroll"},
    "dekalb": {"kind": "county", "county": "DeKalb"},
    "grundy": {"kind": "county", "county": "Grundy"},
    "livingston": {"kind": "county", "county": "Livingston"},
    "logan": {"kind": "county", "county": "Logan"},
    "mclean": {"kind": "county", "county": "McLean"},
    "sangamon": {"kind": "county", "county": "Sangamon"},
    "madison": {"kind": "county", "county": "Madison"},
    "st-clair": {"kind": "county", "county": "St. Clair"},
    "rock-island": {"kind": "county", "county": "Rock Island"},
    "tazewell": {"kind": "county", "county": "Tazewell"},
    "henry": {"kind": "county", "county": "Henry"},
    "cass": {"kind": "county", "county": "Cass"},
    "whiteside": {"kind": "county", "county": "Whiteside"},
    "peoria": {"kind": "county", "county": "Peoria"},
    "mason": {"kind": "county", "county": "Mason"},
    # All three are archived DOCUMENTS rather than fetched pages, so their
    # "scrape" cannot fail on a network blip — but they are preservable anyway,
    # so that a parser regression carries last-good entries forward instead of
    # dropping a county's whole governing body. De Witt's is the Clerk's
    # "Village/City Officials" Word document, sent by e-mail on 2026-08-17.
    "marshall": {"kind": "county", "county": "Marshall"},
    "washington": {"kind": "county", "county": "Washington"},
    "dewitt": {"kind": "county", "county": "De Witt"},
    "macoupin": {"kind": "county", "county": "Macoupin"},
    # Kankakee's source is a third party's minute book, not the county's own
    # site, so a KATS outage must carry its five heads forward rather than
    # blank them.
    "kankakee": {"kind": "county", "county": "Kankakee"},
    # City payloads name the municipalities they cover, because the payload
    # that would have named them is precisely what is missing. Each list is
    # guarded by its scraper's own floor, so a drift here fails there first.
    "freeport": {"kind": "enrich", "places": ["City of Freeport"]},
    # Galesburg, added 2026-08-22 with Knox County's ward layer. Knox has NO
    # county municipal source at all — its Clerk's site is dead and the
    # county's own answers 403 — so the city's page is not an enrichment of a
    # county directory here, it is the only directory there is.
    "galesburg": {"kind": "enrich", "places": ["City of Galesburg"]},
    "will-cities": {"kind": "enrich",
                    "places": ["City of Crest Hill", "City of Lockport",
                               "City of Wilmington"]},
    "skokie": {"kind": "enrich", "places": ["Village of Skokie"]},
    "joliet": {"kind": "enrich", "places": ["City of Joliet"]},
    # Plano, added 2026-09-11 for the plano-ward-officials gap. Kendall's
    # yearbook stops at the mayor and clerk for every municipality, so this is
    # the only source that names Plano's council at all — and its four wards
    # are already drawn, which is what made a card that named nobody visible.
    "plano": {"kind": "enrich", "places": ["City of Plano"]},
}

# Tie-break for a municipality claimed by two counties, applied only AFTER
# depth (see pick_entry). Both directories describe the same government, so
# this is a freshness call, not a correctness one: Cook's is a live API
# reflecting each election as it is certified, Will's is an annually
# republished directory.
# DeKalb sits ahead of LaSalle for the one municipality both name: Somonauk.
# Depth cannot separate them — each publishes the village's full board, and
# each names the same five sitting trustees — so this is the tie-break doing its
# job. DeKalb wins it because the village hall is in DeKalb County (LaSalle
# lists Somonauk because the village extends across the line) and because
# DeKalb's book additionally dates every seat's next election.
# Grundy sits ahead of Livingston for the one municipality both publish in
# full: Dwight. The two 2026 editions disagree on one trustee seat (Grundy:
# Randy Irvin; Livingston: Debra Karch) and Grundy's booklet is a month
# fresher (July vs June 2026) and dates every seat's term — the freshness
# call, made explicit. LaSalle already precedes both, which settles Streator
# (hall in LaSalle) the same way.
# Rock Island sits ahead of Henry for the one municipality both publish in full:
# Coal Valley. Both name its whole board and the two agree, so this is a
# provenance call rather than a freshness one — and Henry's own handbook makes
# it, printing Coal Valley's clerk as "(R.I. Co.)". The village hall is in Rock
# Island County; Henry lists the village because it extends across the line.
# De Witt's position is untested by construction: all seven of its
# municipalities' halls are in De Witt County, Census lists each under FIPS 039
# alone, and no other shipped source (McLean's three ward cities included)
# claims any of them — verified at its 2026-08-17 build, which printed no
# both-counties NOTE for it.
# Macoupin sits BEHIND Sangamon, and one municipality is what that decides:
# Virden, whose city hall stands in Macoupin but whose plat crosses into
# Sangamon, so both clerks publish it. This is the rare tie where the hall-county
# rule that settled Coal Valley and Somonauk points the OTHER way from the
# reader's interest, and it is not a correctness call at all — the two
# directories name the same mayor, the same eight aldermen and the same hall,
# and disagree about nothing. What separates them is what each carries beside
# the names: Sangamon publishes a direct e-mail AND phone for all nine
# officeholders, eighteen fields Macoupin's directory does not have, while
# Macoupin adds two rows Sangamon omits (the city clerk and treasurer). Keeping
# Sangamon trades two rows for eighteen contacts, which is the better card for
# somebody trying to reach their alderman. Macoupin's other twenty-six
# municipalities are its alone.
COUNTY_PRECEDENCE = ["Cook", "Will", "DeKalb", "LaSalle", "Winnebago", "Ogle",
                     "Boone",
                     "Stephenson", "Grundy", "Livingston", "Logan", "McLean",
                     "Sangamon", "Madison", "St. Clair", "Rock Island", "Henry",
                     "Cass", "Peoria", "Tazewell", "DuPage", "Kane", "Kendall", "McHenry",
                     "Carroll", "Whiteside", "Marshall", "Washington", "De Witt",
                     "Macoupin",
                     # Kankakee names five heads and no board, from a regional
                     # council rather than the county, so any county that
                     # publishes a governing body outranks it; only Lake, which
                     # publishes no names at all, ranks below.
                     "Kankakee",
                     "Lake"]

# ONE municipality at a time, where evidence settles a cross-county tie that
# the general rules above get wrong. Keyed by Census GEOID -> (county, reason).
# The reason is not a comment: the build refuses to run without one, because
# overriding the ordering for a single place is precisely the edit that should
# never be possible to make quietly.
#
# This is deliberately NOT a reordering of COUNTY_PRECEDENCE. The ordering is a
# statement about two counties in general; an override is a statement about one
# town, and the evidence here is about one town.
PLACE_SOURCE_OVERRIDE = {
    # Wenona straddles the Marshall/LaSalle line and both clerks publish it in
    # full, so depth cannot separate them and LaSalle wins on ordering. The two
    # lists disagree about the council: LaSalle names eight alderpersons and no
    # treasurer, Marshall names six trustees plus a treasurer, dates every seat
    # 2027 or 2029, and carries three direct phone numbers where LaSalle repeats
    # the city-hall line on every row.
    #
    # What settles it is provenance, not our reading of which looks fresher.
    # Marshall County Clerk Jill Kenyon, asked directly on 2026-08-03: "I just
    # go by what the City has furnished to me." That is a chain — City of Wenona
    # to its county clerk to here — and LaSalle's directory states no origin at
    # all. Marshall's document is also not careless about the distinction it is
    # being trusted on: it labels the board of its three OTHER cities
    # "Alderperson" and only Wenona's "Trustee", so that word is the city's, not
    # a habit of the table.
    #
    # Three people LaSalle names (Julia Kitchens, Randy Lohr, William Simmons)
    # are therefore no longer shown, and Matt Zulz and Treasurer Jaclyn DeRubeis
    # now are. The disagreement itself stays on the record as the gap
    # wenona-two-clerks-disagree rather than being retired, because only one of
    # the two clerks has explained where her list comes from.
    "1779813": ("Marshall",
                "Marshall's clerk states her list is furnished by the City "
                "itself (e-mail, 2026-08-03); LaSalle's directory names no "
                "source. See wenona-two-clerks-disagree."),
}


def _fold(text):
    """Shared tail of both normalizers: expand "Mt.", then letters only.

    Carroll's clerk writes its county seat "Mt. Carroll"; Census writes
    "Mount Carroll". Expanded rather than aliased because it is an abbreviation
    of one word, not a different name, and every Illinois place spelled "Mt." on
    some source is "Mount" in the Census file.
    """
    text = re.sub(r"^Mt\.?(?=\s|$)", "Mount", (text or "").strip(), flags=re.I)
    return re.sub(r"[^A-Z]", "", text.upper())


def norm_census_place(name):
    """Normalize a name from the Census reference file, which SUFFIXES the form.

    "Calumet City city" -> CALUMETCITY, "Rock City village" -> ROCKCITY.
    """
    return _fold(re.sub(r"\s+(village|city|town|CDP)$", "", (name or "").strip(),
                        flags=re.I))


def norm_place(name):
    """Normalize a name from a county/city SOURCE, which PREFIXES the form.

    The two sides label the government form on opposite ends — the clerk writes
    "City of Calumet City", Census writes "Calumet City city" — so each side
    gets its own strip. Doing both here is what this function used to do, and it
    was wrong in both directions: it reduced the clerk's "City of Calumet City"
    to "Calumet", and for a source that publishes BARE names (Stephenson's
    county page, Winnebago's GIS layers) it ate the second word of "Rock City"
    and left "Rock", which matches no Census place at all.
    """
    text = (name or "").strip()
    # "United City of Yorkville" is Yorkville's legal name and the form its
    # county clerk prints; Census lists it as "Yorkville city". The optional
    # qualifier keeps that join working without a per-place alias.
    return _fold(re.sub(r"^(?:united\s+)?(village|city|town)\s+of\s+", "", text,
                        flags=re.I))


def load_places(path):
    """-> ({county_fips: {norm: geoid}}, {norm: set(geoid)}, {geoid: legal name}).

    The third map is the Census's own "<Name> <village|city|town>" wording,
    re-ordered into the "Village of <Name>" form the app's card labels read.
    """
    if not os.path.exists(path):
        print("FATAL: Census place reference missing at %s" % path, file=sys.stderr)
        sys.exit(1)
    by_county = defaultdict(dict)
    statewide = defaultdict(set)
    legal = {}
    with open(path, encoding="utf-8-sig") as f:
        rows = [line.rstrip("\n").split("|") for line in f if line.strip()]
    header = rows[0]
    for row in rows[1:]:
        if len(row) != len(header):
            continue
        rec = dict(zip(header, row))
        if rec.get("TYPE") != "INCORPORATED PLACE":
            continue
        key = norm_census_place(rec["PLACENAME"])
        geoid = "17" + rec["PLACEFP"]
        by_county[rec["COUNTYFP"]][key] = geoid
        statewide[key].add(geoid)
        form = re.search(r"\s+(village|city|town)$", rec["PLACENAME"], flags=re.I)
        if form:
            legal[geoid] = "%s of %s" % (form.group(1).capitalize(),
                                         rec["PLACENAME"][:form.start()].strip())
    if not statewide:
        print("FATAL: no incorporated places parsed from %s" % path, file=sys.stderr)
        sys.exit(1)
    return by_county, statewide, legal


# Places incorporated AFTER the committed Census 2020 reference file. Cahokia
# Heights formed in May 2021 from Cahokia, Alorton and Centreville; the 2020
# file still lists its three predecessors and not it, while the app's
# TIGERweb municipality layer serves the new city under this GEOID (verified
# live 2026-08-01). Keyed by norm_place() form.
POST_2020_GEOIDS = {
    "CAHOKIAHEIGHTS": "1710373",
}


def resolve_geoid(name, county, by_county, statewide):
    key = norm_place(name)
    if not key:
        return None, "unparseable name"
    if key in POST_2020_GEOIDS:
        return POST_2020_GEOIDS[key], None
    fips = COUNTY_FIPS.get(county)
    if fips and key in by_county.get(fips, {}):
        return by_county[fips][key], None
    matches = statewide.get(key) or set()
    if len(matches) == 1:
        return next(iter(matches)), None
    if not matches:
        return None, "no Census place matches"
    return None, "ambiguous statewide (%s)" % ", ".join(sorted(matches))


def classify(office):
    o = (office or "").strip().lower()
    if o in HEAD_OFFICES:
        return "head"
    if o in BOARD_OFFICES:
        return "board"
    if o in OFFICER_OFFICES:
        return "officer"
    return None


def election_year(value):
    """A four-digit year from either shape the sources use.

    Cook publishes ISO datetimes ("2029-04-01T00:00:00-05:00"), Will and
    Kendall bare years ("2027"). Anything else is None rather than a guess.
    """
    match = re.match(r"^(\d{4})(?:-\d{2}-\d{2})?", str(value or "").strip())
    return match.group(1) if match else None


def district_sort_key(member):
    """Ward 1 < Ward 2 < Ward 10; unnumbered seats sort last, then by name."""
    district = member.get("district") or ""
    nums = re.findall(r"\d+", district)
    return (0, int(nums[0])) if nums else (1, 0), member.get("name") or ""


def office_block(records):
    """One municipality-level office block from the shared contact fields."""
    rec = records[0]
    street = rec.get("office_address")
    city = rec.get("office_city")
    state = rec.get("office_state")
    zipcode = rec.get("office_zip")
    locality = " ".join(p for p in (city, state) if p)
    if locality and zipcode:
        locality = "%s %s" % (locality, zipcode)
    address = ", ".join(p for p in (street, locality) if p) or None
    block = {}
    if address:
        block["address"] = address
    phone = format_phone(rec.get("office_phone"))
    if phone:
        block["phone"] = phone
    if rec.get("office_email"):
        block["email"] = rec["office_email"]
    return block


def format_phone(phone):
    """10 digits -> 708-385-6902, the shape the card's phone helper renders.

    cardPhoneLink() prints the stored string verbatim (only swapping hyphens
    for non-breaking ones), so an unformatted run of digits would ship as
    '7083856902'. Anything that isn't a plain US number is left untouched
    rather than reshaped into a guess.
    """
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return phone
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])


def normalize_website(url):
    if not url:
        return None
    url = url.strip()
    if not url:
        return None
    if not re.match(r"^https?://", url, flags=re.I):
        url = "https://" + url
    return url


def build_county(payload, by_county, statewide, legal, warnings, apply_floors=True):
    county = payload.get("county") or "?"
    grouped = defaultdict(list)
    for rec in payload.get("officials") or []:
        if rec.get("jurisdiction"):
            grouped[rec["jurisdiction"]].append(rec)

    entries = {}
    for jurisdiction, records in grouped.items():
        geoid, problem = resolve_geoid(jurisdiction, county, by_county, statewide)
        if geoid is None:
            print("FATAL: cannot resolve '%s' (%s County) to a Census place GEOID — %s"
                  % (jurisdiction, county, problem), file=sys.stderr)
            sys.exit(1)

        head = None
        board = []
        officers = []
        for rec in records:
            name = rec.get("name")
            if not name:
                continue
            # A SEAT NOBODY HOLDS IS NOT A PERSON. Several county documents
            # print "Vacant" in the name column, and a card that renders it
            # verbatim tells a resident their trustee is a man called Vacant.
            # Individual scrapers already drop these (Grundy, Stephenson); the
            # guard lives HERE as well because it is true of every source, and
            # four had slipped through — Braceville's and Peotone's commissioner
            # and treasurer rows (Will), Monroe Center's and Mt. Morris's
            # treasurers (Ogle). Counted, never silent: an empty seat is real
            # information about the municipality, it is just not a name.
            if name.strip().lower() in VACANT_NAMES:
                warnings.append("%s: %s seat published as '%s' — dropped, a "
                                "vacancy is not an officeholder"
                                % (jurisdiction, rec.get("office") or "?", name.strip()))
                continue
            # A NAME PRINTED BACKWARDS IS STILL THE SAME NAME. See the
            # uninvert_name contract above for why this is re-ordering rather
            # than inference, and for the suffix guard that makes it safe.
            # Counted, never silent, in both directions: an applied inversion
            # says so, and a comma-form name this refuses to touch — one that
            # is neither a suffix nor invertible — says that too, because such
            # a row is exactly where the next defect of this kind will surface.
            flipped = uninvert_name(name)
            if flipped:
                warnings.append("%s: '%s' published surname-first — shipped as "
                                "'%s'" % (jurisdiction, name.strip(), flipped))
                name = flipped
            elif ("," in name
                  and name.rsplit(",", 1)[-1].replace(".", "").strip().lower()
                      not in NAME_SUFFIXES):
                warnings.append("%s: '%s' carries a comma that is neither a "
                                "suffix nor a surname-first name — shipped "
                                "verbatim" % (jurisdiction, name.strip()))
            kind = classify(rec.get("office"))
            person = {"name": name, "role": rec.get("office")}
            if rec.get("district"):
                person["district"] = rec["district"]
            if rec.get("appointed"):
                person["appointed"] = True
            # Per-PERSON contact, carried only where the source publishes it per
            # member (McHenry prints a direct line or office e-mail for a few
            # officials). The municipality-level hall contact below is never
            # copied onto a person — that would imply a direct line that the
            # source does not publish.
            if rec.get("person_phone"):
                person["phone"] = format_phone(rec["person_phone"])
            if rec.get("person_email"):
                person["email"] = rec["person_email"]
            # When this seat is next on the ballot, where the source publishes
            # it (Cook: 100% of records). Terms are STAGGERED — 103 of Cook's
            # 104 village boards mix two cycles — so this belongs on the person,
            # not the card. Stored as the year; the card hides a year already
            # past rather than calling it "next".
            # Term information, labelled as its own source labels it rather
            # than normalised into one field: Cook publishes the NEXT election
            # date, Will the year a term EXPIRES, Kendall the date an officer
            # was last ELECTED. Collapsing three different facts into one label
            # would state something none of them says.
            next_election = election_year(rec.get("next_election"))
            if next_election:
                person["nextElection"] = next_election
            term_expires = election_year(rec.get("term_expires"))
            if term_expires:
                person["termExpires"] = term_expires
            # Cook publishes BOTH a last-elected and a next-election date; the
            # next election is the more useful of the two and the card shows it,
            # so the last-elected date is kept only where it is the only term
            # fact a source gives (Kendall). Storing both would put ~1,000
            # fields in the file that nothing reads.
            last_elected = election_year(rec.get("last_elected"))
            if last_elected and not next_election:
                person["lastElected"] = last_elected
            if kind == "head":
                if head is not None:
                    print("FATAL: %s resolved two heads of government (%s, %s)"
                          % (jurisdiction, head["name"], name), file=sys.stderr)
                    sys.exit(1)
                head = person
            elif kind == "board":
                board.append(person)
            else:
                if kind is None:
                    warnings.append("unclassified office '%s' in %s — shipped under officers"
                                    % (rec.get("office"), jurisdiction))
                officers.append(person)

        board.sort(key=district_sort_key)
        officers.sort(key=lambda m: (m.get("role") or "", m.get("name") or ""))

        # The card's hall and body labels read the legal form off this name
        # ("Village of Alsip" -> "Village Hall"), so a source that publishes
        # BARE names — Stephenson's county page, Winnebago's GIS layers — would
        # otherwise land on the generic "Municipal Hall". The form comes from
        # the Census reference file's own designation ("Rock City village"),
        # not from an inference about the place. A source that already states
        # the form keeps its own wording: "United City of Yorkville" is the
        # city's legal name and the Census's plain "City of Yorkville" would be
        # a downgrade, not a fix.
        entry = {"name": legal.get(geoid, jurisdiction)
                 if not re.match(r"^(?:united\s+)?(village|city|town)\s+of\s+",
                                 jurisdiction, flags=re.I) else jurisdiction,
                 "county": county}
        # Chicago's 50 ward seats are published under a different jurisdiction
        # type and answered by the `ward` layer, so this card points there
        # instead of implying the city has no council.
        if any(rec.get("ward_seats_elsewhere") for rec in records):
            entry["councilOnWardLayer"] = True
        if head:
            entry["head"] = head
        if board:
            entry["board"] = board
        if officers:
            entry["officers"] = officers
        office = office_block(records)
        if office:
            entry["office"] = office
        website = normalize_website(records[0].get("website"))
        if website:
            entry["url"] = website
        entry["sourceUrl"] = payload.get("directory_url") or records[0].get("source_url")
        entries[geoid] = entry

    floors = COUNTY_FLOORS.get(county) if apply_floors else None
    if floors:
        n_munis = len(entries)
        n_members = sum(len(e.get("board") or []) + len(e.get("officers") or [])
                        + (1 if e.get("head") else 0) for e in entries.values())
        n_heads = sum(1 for e in entries.values() if e.get("head"))
        for label, actual, floor in (("municipalities", n_munis, floors["municipalities"]),
                                     ("members", n_members, floors["members"]),
                                     ("heads of government", n_heads, floors["heads"])):
            if actual < floor:
                print("FATAL: %s County resolved %d %s, floor is %d — refusing to write"
                      % (county, actual, label, floor), file=sys.stderr)
                sys.exit(1)
    return entries


def name_tokens(name):
    """Comparable name parts: lowercase alpha words, nicknames included."""
    return [t for t in re.split(r"[^A-Za-z]+", str(name or "").lower()) if t]


def same_person(a, b):
    """Match a city site's name against the clerk's, allowing nicknames.

    Surnames must agree and at least one given/nick name must overlap, so
    "Nathaniel "Nate" Albert" meets "Nate Albert" and "Angelo Sante Deserio"
    meets "Angelo Deserio", while two different Smiths never merge.
    """
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb or ta[-1] != tb[-1]:
        return False
    given_a, given_b = ta[:-1], tb[:-1]
    if not given_a or not given_b:
        return False
    for x in given_a:
        for y in given_b:
            # Equal, or a truncation of the other ("Chris"/"Christine",
            # "Tom"/"Thomas"). Nicknames the clerk prints in quotes already
            # appear as their own token, so "Nate" meets
            # "Nathaniel \u201cNate\u201d Albert" by equality. Nicknames that
            # are NOT truncations ("Joe"/"Joseph" — Joseph is "jos…") fall to
            # the surname tier in merge_contact rather than a nickname table,
            # which would be guesswork dressed as data.
            if x == y:
                return True
            if len(x) >= 3 and len(y) >= 3 and (x.startswith(y) or y.startswith(x)):
                return True
    return False


def people_of(entry):
    return ([entry["head"]] if entry.get("head") else []) + \
        (entry.get("board") or []) + (entry.get("officers") or [])


def merge_contact(existing, addition, warnings):
    """Fill per-person fields the county left empty, from a municipality's own site.

    The county clerk's directory stays the roster of record: this never adds a
    seat-holder, renames one, or changes a role, and never overwrites a value
    the county already published — an unmatched name is reported instead,
    because a mismatch means one of the two sources is out of date and that is
    a human's call.

    Contact is the usual payload. DISTRICT is the exception that earns its
    keep: Skokie's four district trustees and two at-large trustees are all
    published municipality-wide by the Clerk, with no district on any of them,
    while Cook GIS carries the four district polygons — so the seats existed on
    the map with nobody attached. The village publishes the assignment itself,
    which is the authority on its own districting.

    A WHOLE BOARD IS THE SECOND EXCEPTION, and it is narrower than it sounds.
    "The clerk is the roster of record" is a rule about DISAGREEMENT: where two
    sources name a council, a name in one and not the other means one of them is
    stale, and that is a human's call. Where the county published no council at
    all there is nothing to disagree with, so a city's own board is adopted
    whole rather than reported eight times as not-added. Plano is the case that
    found this: Kendall's yearbook stops at the mayor and clerk for every
    municipality, its four wards are drawn, and the card named nobody in them.

    The HEAD and the OFFICERS are never adopted this way, only the board. Plano
    is also why: the same city page that names the council says its mayor was
    "Elected in 2021" while the county clerk has him last elected 2025, so the
    page is maintained and still carries a stale adjacent field. The county's
    head stays the county's.

    Measured 2026-09-11 before this was written: all seven municipalities the
    other five city payloads cover already carry a board, so this branch is
    inert for every one of them. 143 of the roster's 629 municipalities carry
    none, which is the size of the opening it makes for a future city payload.
    """
    hall = existing.get("office") or {}
    addition_board = addition.get("board") or []
    if addition_board and not existing.get("board"):
        existing["board"] = [dict(m) for m in addition_board]
        warnings.append("%s: the county directory publishes no council, so all "
                        "%d seat(s) come from the municipality's own site"
                        % (existing.get("name"), len(addition_board)))
    for person in people_of(addition):
        matches = [c for c in people_of(existing)
                   if same_person(c.get("name"), person.get("name"))]
        if not matches:
            # Second tier: an unambiguous surname inside one small council is a
            # safe join even when given names differ by nickname. Logged so the
            # looser rule is always visible in the build output.
            surname = (name_tokens(person.get("name")) or [None])[-1]
            by_surname = [c for c in people_of(existing)
                          if (name_tokens(c.get("name")) or [None])[-1] == surname]
            if surname and len(by_surname) == 1:
                matches = by_surname
                warnings.append("%s: matched '%s' to '%s' on surname alone"
                                % (existing.get("name"), person.get("name"),
                                   by_surname[0].get("name")))
        if len(matches) > 1:
            # Two seat-holders could be this person: attributing a phone to the
            # wrong one is worse than shipping none.
            warnings.append("%s: '%s' matches %d people in the county directory — "
                            "ambiguous, contact not applied"
                            % (existing.get("name"), person.get("name"), len(matches)))
            continue
        match = matches[0] if matches else None
        if match is None:
            warnings.append("%s: '%s' is on the city site but not in the county "
                            "directory — not added (clerk is the roster of record)"
                            % (existing.get("name"), person.get("name")))
            continue
        # A district the county never published (Skokie). Filled, never
        # overwritten, and logged so the looser field is visible in the build.
        if person.get("district") and not match.get("district"):
            match["district"] = person["district"]
            warnings.append("%s: district '%s' for %s came from the municipality's "
                            "own site (the county published none)"
                            % (existing.get("name"), person["district"],
                               match.get("name")))
        phone = person.get("phone")
        # A "direct" number that is just the main line is not a direct line.
        if phone and phone != hall.get("phone") and not match.get("phone"):
            match["phone"] = phone
        email = person.get("email")
        if email and email != hall.get("email") and not match.get("email"):
            match["email"] = email


def entry_depth(entry):
    """How much of the governing body a source actually names.

    2 = full body (a head plus the board), 1 = head only, 0 = contact only.
    This is what decides a cross-county municipality, NOT which county the
    place is mostly in: a village that straddles Cook and Will should show the
    board wherever one is published.
    """
    if entry.get("board"):
        return 2
    if entry.get("head"):
        return 1
    return 0


def describe_depth(entry):
    return {2: "full governing body", 1: "head of government only",
            0: "contact only"}[entry_depth(entry)]


def pick_entry(a, b, geoid=None):
    """-> (kept, dropped) for one municipality claimed by two counties."""
    override = PLACE_SOURCE_OVERRIDE.get(geoid)
    if override:
        county, reason = override
        if not reason or not reason.strip():
            print("FATAL: PLACE_SOURCE_OVERRIDE[%r] carries no reason" % geoid,
                  file=sys.stderr)
            sys.exit(1)
        # Only act when the named county is actually one of the two in hand.
        # If it is not, the override has gone stale — the county stopped
        # publishing this place, or its name changed — and silently falling
        # back to the ordering would undo a decision made on evidence.
        if a["county"] == county:
            return a, b
        if b["county"] == county:
            return b, a
        print("FATAL: PLACE_SOURCE_OVERRIDE[%r] names %s County, but this place "
              "is claimed by %s and %s — the override is stale"
              % (geoid, county, a["county"], b["county"]), file=sys.stderr)
        sys.exit(1)
    if entry_depth(a) != entry_depth(b):
        return (a, b) if entry_depth(a) > entry_depth(b) else (b, a)
    rank = {c: i for i, c in enumerate(COUNTY_PRECEDENCE)}
    fallback = len(COUNTY_PRECEDENCE)
    if rank.get(a["county"], fallback) <= rank.get(b["county"], fallback):
        return a, b
    return b, a


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("inputs", nargs="+", help="per-county scraper output JSON files")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--places", default=PLACES_FILE)
    parser.add_argument("--enrich", nargs="*", default=[],
                        help="city-site payloads: add per-seat contact to the "
                             "county roster, and supply municipalities the county "
                             "source omits entirely")
    parser.add_argument("--preserve", metavar="ROSTER_JSON",
                        help="the currently shipped roster, read to carry "
                             "forward the sources named by --preserved")
    parser.add_argument("--preserved", nargs="*", default=[], metavar="SOURCE",
                        help="sources whose scrape failed this run (%s); their "
                             "shipped entries are carried forward instead of "
                             "being dropped" % ", ".join(sorted(PRESERVABLE)))
    args = parser.parse_args()

    unknown = [s for s in args.preserved if s not in PRESERVABLE]
    if unknown:
        print("FATAL: --preserved names unknown source(s) %s; known: %s"
              % (", ".join(unknown), ", ".join(sorted(PRESERVABLE))), file=sys.stderr)
        sys.exit(1)
    if args.preserved and not args.preserve:
        print("FATAL: --preserved needs --preserve <shipped roster> to read from",
              file=sys.stderr)
        sys.exit(1)

    shipped = {}
    if args.preserve:
        with open(args.preserve) as f:
            shipped = json.load(f)

    by_county, statewide, legal = load_places(args.places)

    roster = {}
    warnings = []
    supplied_counties = set()

    def absorb(geoid, entry):
        """Merge one entry into the roster under cross-county precedence."""
        if geoid not in roster:
            roster[geoid] = entry
            return
        keep, drop = pick_entry(roster[geoid], entry, geoid)
        override = PLACE_SOURCE_OVERRIDE.get(geoid)
        print("NOTE: %s (%s) is listed by both %s and %s County — keeping the "
              "%s entry (%s)%s" % (geoid, keep["name"], roster[geoid]["county"],
                                   entry["county"], keep["county"],
                                   describe_depth(keep),
                                   " [OVERRIDE: %s]" % override[1] if override else ""),
              file=sys.stderr)
        if drop.get("board") and not keep.get("board") and not override:
            print("FATAL: dropped entry for %s had a board and the kept one "
                  "does not — precedence is wrong" % geoid, file=sys.stderr)
            sys.exit(1)
        roster[geoid] = keep

    for path in args.inputs:
        with open(path) as f:
            payload = json.load(f)
        supplied_counties.add(payload.get("county"))
        entries = build_county(payload, by_county, statewide, legal, warnings)
        for geoid, entry in entries.items():
            absorb(geoid, entry)

    # A full-body county is never preserved (see PRESERVABLE) — losing one would
    # turn councils into mayors across a third of the metro without any single
    # count floor noticing, since the municipalities all remain.
    for county in REQUIRED_COUNTIES:
        if county not in supplied_counties:
            print("FATAL: %s County is required and was not supplied — it is one "
                  "of the two full-governing-body sources, so building without it "
                  "would ship heads of government where councils belong"
                  % county, file=sys.stderr)
            sys.exit(1)

    # Carry forward a blocked county BEFORE the city payloads run, so the
    # enrichment step still refines it exactly as it would a fresh scrape.
    preserved_counts = {}
    for source in args.preserved:
        spec = PRESERVABLE[source]
        if spec["kind"] != "county":
            continue
        if spec["county"] in supplied_counties:
            print("FATAL: --preserved names %s but its county (%s) WAS supplied — "
                  "refusing to overwrite a fresh scrape with shipped data"
                  % (source, spec["county"]), file=sys.stderr)
            sys.exit(1)
        kept = 0
        for geoid, entry in shipped.items():
            if entry.get("county") != spec["county"]:
                continue
            absorb(geoid, json.loads(json.dumps(entry)))
            kept += 1
        if not kept:
            print("FATAL: --preserved %s carried forward 0 entries — the shipped "
                  "roster has none tagged %s, so this would silently drop the "
                  "county" % (source, spec["county"]), file=sys.stderr)
            sys.exit(1)
        preserved_counts[source] = kept

    # City-site payloads run last: they refine what the counties established.
    for path in args.enrich:
        with open(path) as f:
            payload = json.load(f)
        entries = build_county(payload, by_county, statewide, legal, warnings,
                               apply_floors=False)
        for geoid, entry in entries.items():
            if geoid not in roster:
                print("NOTE: %s (%s) is absent from its county's directory — "
                      "supplied by the city's own site" % (geoid, entry["name"]),
                      file=sys.stderr)
                roster[geoid] = entry
            else:
                merge_contact(roster[geoid], entry, warnings)

    # A blocked city payload is re-applied from what is shipped, through the
    # SAME merge_contact the live payload would have used. That matters: the
    # county's fresh entry stays the roster of record, so a seat-holder the
    # county has since replaced is not resurrected — only fields the county
    # left empty are filled, and an unmatched name is reported as a warning.
    for source in args.preserved:
        spec = PRESERVABLE[source]
        if spec["kind"] != "enrich":
            continue
        wanted = {norm_place(p) for p in spec["places"]}
        found = set()
        for geoid, entry in shipped.items():
            key = norm_place(entry.get("name"))
            if key not in wanted:
                continue
            found.add(key)
            if geoid not in roster:
                # The county source omits this municipality entirely and the
                # city payload was the only thing supplying it.
                print("NOTE: %s (%s) is absent from its county's directory and "
                      "its city payload is blocked — carried forward as shipped"
                      % (geoid, entry.get("name")), file=sys.stderr)
                roster[geoid] = json.loads(json.dumps(entry))
                continue
            merge_contact(roster[geoid], json.loads(json.dumps(entry)), warnings)
        missing = wanted - found
        if missing:
            print("FATAL: --preserved %s expected %d municipalities in the "
                  "shipped roster and %d are absent — the place list in "
                  "PRESERVABLE has drifted from what the scraper covers"
                  % (source, len(wanted), len(missing)), file=sys.stderr)
            sys.exit(1)
        preserved_counts[source] = len(found)

    # The Skokie class: a municipality whose seats the ward layer maps, but
    # whose roster carries no districted seat, renders a district polygon with
    # nobody attached. Warn rather than fail — a municipality may legitimately
    # have ward geometry drawn before it takes effect — but never let it pass
    # unseen again.
    coverage_path = os.path.join(args.out_dir, "municipal-ward-coverage.json")
    if os.path.exists(coverage_path):
        with open(coverage_path) as f:
            covered = json.load(f)
        for feature in (covered.get("features") or []):
            geoid = str((feature.get("properties") or {}).get("geoid") or "")
            entry = roster.get(geoid)
            if not entry or not entry.get("board"):
                continue
            if not any(m.get("district") and
                       not re.match(r"^at[\s-]*large$", str(m["district"]), re.I)
                       for m in entry["board"]):
                warnings.append("%s has ward geometry but no districted seat in the "
                                "roster — its ward card will name nobody"
                                % entry.get("name"))

    if len(roster) < MIN_TOTAL_MUNICIPALITIES:
        print("FATAL: resolved %d municipalities, floor is %d — refusing to write"
              % (len(roster), MIN_TOTAL_MUNICIPALITIES), file=sys.stderr)
        sys.exit(1)

    for warning in warnings:
        print("WARNING: %s" % warning, file=sys.stderr)

    # THE WITHHOLD SWEEP RUNS ONCE, OVER THE ASSEMBLED ROSTER. An address
    # reaches this file by three different routes — a village hall's `office`
    # block, an `officers` row and a `board` row — and all three carry an
    # `email` key, so a walk of the finished structure covers every shape and
    # cannot be out of step with a fourth route added later. Nine of these
    # municipalities publish an address on a domain that does not resolve at
    # all; each is dropped with its reason printed, and the name, office, phone
    # and page URL beside it are untouched.
    def _drop_undeliverable(node, where):
        if isinstance(node, dict):
            for key, value in list(node.items()):
                if key == "email" and isinstance(value, str):
                    kept, _why = undeliverable.withhold(value, where)
                    if kept is None:
                        del node[key]
                else:
                    _drop_undeliverable(value, where)
        elif isinstance(node, list):
            for item in node:
                _drop_undeliverable(item, where)

    for geoid, entry in roster.items():
        _drop_undeliverable(entry, "%s %s" % (geoid, entry.get("name") or ""))

    out_path = os.path.join(args.out_dir, "municipal-officials.json")
    with open(out_path, "w") as f:
        json.dump(roster, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")

    n_board = sum(len(e.get("board") or []) for e in roster.values())
    n_seats = sum(1 for e in roster.values() for m in (e.get("board") or []) if m.get("district"))
    print("wrote %s: %d municipalities, %d board members (%d ward/district seats)"
          % (out_path, len(roster), n_board, n_seats), file=sys.stderr)
    if preserved_counts:
        # Printed so the run log and the PR body both name every source that did
        # NOT refresh — a preserved county is data that is shipped but no longer
        # verified this week, and that has to stay visible.
        print("PRESERVED (blocked this run, carried forward from the shipped "
              "roster): %s" % ", ".join("%s %d" % (s, n) for s, n
                                        in sorted(preserved_counts.items())),
              file=sys.stderr)


if __name__ == "__main__":
    main()
