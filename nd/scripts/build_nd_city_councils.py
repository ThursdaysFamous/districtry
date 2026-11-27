#!/usr/bin/env python3
"""
Build nd/data/app/nd-city-councils.json: the mayor and council or commission
of each of North Dakota's 7 cities of 25,000 people or more, written down from
each city's own pages and proved against them on every build.

    python3 nd/scripts/build_nd_city_councils.py            # read every page, prove every name, write
    python3 nd/scripts/build_nd_city_councils.py --check    # offline
    python3 nd/scripts/build_nd_city_councils.py --watch    # is every name still on its page?

The work is scripts/city_councils.py, which says what the proof is and what it
cannot prove. This file says which places, how many seats each has, which
pages were read once by hand, and why one city's wards are not drawn. The
seats are in nd/data/source/nd-city-council-seats.json, kept by hand.

WHICH PLACES. The 7 the done standard counts (docs/expected-governments.json,
Census 2020 population of 25,000 or more): Fargo, Bismarck, Grand Forks,
Minot, West Fargo, Williston and Dickinson, all read on 2026-11-27. North
Dakota's other cities name nobody, and gap nd-municipal-officeholders says so.

THREE PAGES WERE READ ONCE BY HAND in Adam's Chrome on 2026-11-27 (Adam,
2026-11-25), because the cities' sites refuse this project's reader: Grand
Forks's and Dickinson's answer it with HTTP 403, and Williston's robots.txt
disallows every page to every client. What was read is kept, dated, in
nd/data/source/councils/, and the build proves names against those excerpts
(`excerpts` below); they are not re-read automatically, and nd/WATCH.md
carries the re-read.

WILLISTON NAMES NOBODY. Its commission page says the commission is "five
Commissioners" and that "Commission photos will be updated at a later date",
and names none of them; the minutes of 10 November 2026 give surnames only.
A surname is not a name, so the five seats carry `unnamed`.

HOW EACH CITY ELECTS, read on 2026-11-27:
  * Five cities are governed by a board of city commissioners, and North
    Dakota law reads "The members of the board of city commissioners must be
    elected at large and not by wards" (NDCC 40-09-03, ndlegis.gov), the
    president (whom these cities call the mayor) on a line of his own. Fargo's
    and West Fargo's own pages say so in so many words ("The Mayor and four
    Commissioners are elected at large"; "four Commissioners and a Mayor are
    elected at large"). Fargo's voters rejected a council elected by ward at
    a special election on 6 October 2026 (the city's own special election
    page and the local press), so the commission stands.
  * Grand Forks: the council page, "elected by those within their ward",
    seven wards. Its mayor is elected citywide.
  * Minot: the council page quotes the city code: "The Mayor shall be elected
    at large", six aldermen, "One-half (1/2) of the elected aldermen shall be
    elected biennially". North Dakota law has a council city of Minot's size
    elect by wards (NDCC 40-08-04), and Minot is a home rule city that left
    wards in 2016. That the aldermen are elected citywide was measured from
    the 2026 election, not inferred: seven candidates filed "for Minot's three
    open council seats in the June 9 city election" (Minot Daily News, April
    2026), one contest for three seats, and the city's notice asks for
    petition signatures of "qualified voters within Minot city limits"
    (DocumentCenter/View/9942), with no ward named for any seat or candidate.

CONTACTS. Grand Forks's council page prints a number beside each member, and
Dickinson's prints one member's own number and the office's line
(701.456.7744) beside three others, which `officeLines` records so no seat
carries it. No other city prints a contact beside one member alone.

WARDS. Grand Forks elects by ward and its ward map is not drawn yet;
`undrawn` says so, and the City card says the ward map is not drawn. The
status page counts it as owed a ward map.

RE-READ. North Dakota's cities elect in June of even years and seat the
winners by July; nd/WATCH.md carries the re-read after each election.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import city_councils as cc  # noqa: E402

GRAND_FORKS = "3832060"

# Seats per place, the mayor included, as each place's own page gives them on
# 2026-11-27. A redistricting or a charter change moves these legitimately:
# read the place's page, then change the number deliberately.
SEATS = {
    "3825700": 5,      # Fargo: mayor and 4 commissioners
    "3807200": 5,      # Bismarck: mayor and 4 commissioners
    GRAND_FORKS: 8,    # Grand Forks: mayor and 7 ward members
    "3853380": 7,      # Minot: mayor and 6 aldermen
    "3884780": 5,      # West Fargo: mayor and 4 commissioners
    "3886220": 5,      # Williston: 5 commissioners, none named
    "3819620": 5,      # Dickinson: mayor and 4 commissioners
}

SPEC = cc.Spec(
    tag="nd",
    label="build_nd_city_councils",
    user_agent="districtry/1.0 (+https://districtry.com/nd/)",
    seats_file="nd-city-council-seats.json",
    out_file="nd-city-councils.json",
    seats=SEATS,
    # 8 members' numbers were written down on 2026-11-27 (7 in Grand Forks, 1
    # in Dickinson) and no member's e-mail address; the floor is about two
    # thirds.
    min_emails=0,
    min_phones=5,
    undrawn={GRAND_FORKS: "its wards are not drawn yet; the city publishes them as a map"},
    excerpts={
        "https://www.grandforksgov.com/government/city-leadership/city-council":
            "councils/grand-forks-2026-11-27.txt",
        "https://www.grandforksgov.com/government/city-leadership/mayor-bochenski":
            "councils/grand-forks-2026-11-27.txt",
        "https://www.cityofwilliston.com/government/city_commission/index.php":
            "councils/williston-2026-11-27.txt",
        "https://www.dickinsongov.com/city-commission":
            "councils/dickinson-2026-11-27.txt",
    },
)

if __name__ == "__main__":
    cc.main(SPEC, __doc__)
