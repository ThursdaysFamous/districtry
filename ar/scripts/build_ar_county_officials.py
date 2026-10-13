#!/usr/bin/env python3
"""
Build the county officials Arkansas's cards name — every county judge and every
justice of the peace — into ar/data/app/ar-county-officials.json.

EVERY ARKANSAS COUNTY ELECTS A COUNTY JUDGE AND A QUORUM COURT. The county
judge is the county's executive and presides over the quorum court; the quorum
court is the county's legislative body, 9 to 15 justices of the peace, one from
each district (Arkansas Code 14-14-402). The districts are
`build_ar_quorum_court_districts.py`'s; this file is the people.

TWO PUBLISHERS, AND WHAT EACH IS TRUSTED FOR:

  The county judges come from the Arkansas Judiciary's own directory
  (arcourts.gov/directories/county-judge-clerk), one table of every county's
  judge and clerk with the office address and telephone. Read 2026-10-13: 75
  judges, one per county. The build refuses unless every one of the 75 counties
  has exactly one.

  The justices of the peace come from the Association of Arkansas Counties
  (arcounties.org/counties/<county>/), whose page for each county names its
  justices in one comma-separated line. NO GOVERNMENT PUBLISHES THEIR NAMES
  STATEWIDE: five state routes were read during planning (2026-10-09) and
  none lists them. The association's line does not say which justice sits for
  which district, and its order is not claimed to be district order, so this
  file carries the list as the association prints it and claims no district —
  the rule Adam set on 2026-10-13 ("District, else list"): a justice is named
  by district only where the county's own site numbers them (`NUMBERED`
  below), and elsewhere the association's names go on the County card,
  credited and dated, without a district — and the district card takes the
  2024 election results described next.

  THE ASSOCIATION ALSO PUBLISHES WHO WON EACH DISTRICT, and on Adam's second
  ruling of 2026-10-13 ("Use 2024 list") that names a district's justice
  everywhere else. Its "2024 General Election Results — Justices of the Peace"
  (updated 17 December 2024) gives the winner of every one of the 775 districts
  by county and number. It is a dated record of an election, not a list of who
  sits now, so a winner is named for a district ONLY while the association's
  current page for the county still lists that person (`match_results`), and
  that comparison is re-run on every weekly build. A winner who has left is
  not named, and neither is the justice who replaced them, because the results
  cannot say which district a replacement holds. The county's own numbered
  list, where there is one, wins over the results. Measured 2026-10-13 on the
  20 counties that number their own: the results named 203 of their
  districts this way and 202 agreed with the county. The other was Carroll
  District 1, where the county's own page says the 2024 winner was later
  appointed to District 2 — a move the results cannot show, and the reason the
  county's own list wins wherever it exists. The results are read into
  ar/data/source/ once (`--read-results`) rather than weekly, because the
  document is a dated record that does not change; its SHA-256 is kept with it
  so a re-read can tell whether the association has revised it.

  The association's page also names each county judge, which is the witness
  for the judiciary's directory: a county where the two name different people
  FAILS the build unless a person has read a third source and recorded which
  one is right in `JUDGE_DISAGREES`. And it prints the judge's office address,
  so the address ships only where both publishers give the same street number
  and city — the fleet's two-source rule for an office address.

  THE JUDICIARY'S DIRECTORY IS THE ONE THAT GOES STALE, measured 2026-10-13:
  the two disagreed in Boone, Cleveland, Desha, Jefferson and Sevier, and in
  all five the directory was the one out of date. Boone County's own page
  names Mitchell Archer, the association's judge, where the directory still
  names Robert Hathaway; in Cleveland the directory names Jimmy D. Cummings,
  who died in August 2025, where the quorum court appointed Don Triplett in
  February 2026; local newspapers name the association's judge in Desha
  (Wayne Smith) and Jefferson (Ivan Whitfield); and Sevier County's own page
  names Sandra Dunn. So a government directory is not the authority by being
  a government's: each disagreement is settled by reading a third source,
  and the entry FAILS the day it stops describing the two publishers (the
  directory corrected, or the association naming someone else), so it cannot
  outlive what it records.

THE COUNTS ARE HELD TO THE MAP. Each county's justice line must carry exactly
as many names as the state's map draws districts for that county (a "Vacant"
entry counts as a seat), because a list one short reads as a full court to a
reader. A county that differs FAILS until a person reads it and records it in
`COUNT_DIFFERS`.

ALL 775 SEATS ARE ON THE 3 NOVEMBER 2026 BALLOT, AND THE NEW TERMS START ON
1 JANUARY 2027. Adam chose (2026-10-13) to name the justices now and re-check
every county in January; the weekly refresh re-reads the association, and the
January re-read is a row in ar/WATCH.md.

PACING. arcounties.org asks for 20 seconds between requests in its robots.txt
(read 2026-10-13 with this client); this builder reads that value from the
file rather than hard-coding it, and pauses that long between pages, so a full
read is 76 requests and about 25 minutes. arcourts.gov's robots.txt (Drupal's
default) permits the directory and states no delay; it is one request.

The builder never reads a justice's or judge's home address or telephone: the
association prints the judge's OFFICE line only, and the justices' line is
names alone.

Usage:
    python3 ar/scripts/build_ar_county_officials.py                  # fetch, build, write
    python3 ar/scripts/build_ar_county_officials.py --cache DIR      # keep/reuse raw pages
    python3 ar/scripts/build_ar_county_officials.py --check          # offline gate
    python3 ar/scripts/build_ar_county_officials.py --read-results   # re-read the results PDF
    python3 ar/scripts/build_ar_county_officials.py --read-results --results-pdf FILE
"""

import argparse
import datetime
import hashlib
import html
import io
import json
import os
import re
import sys
import time
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(os.path.dirname(INSTANCE), "scripts"))

from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

APP_DATA = os.path.join(INSTANCE, "data", "app")
OUT_FILE = os.path.join(APP_DATA, "ar-county-officials.json")
DISTRICTS_FILE = os.path.join(APP_DATA, "ar-quorum-court-districts.json")
COUNTIES_FILE = os.path.join(APP_DATA, "state-counties.json")

USER_AGENT = "districtry/1.0 (+https://districtry.com/ar/)"
JUDGES_URL = "https://arcourts.gov/directories/county-judge-clerk"
AAC_BASE = "https://arcounties.org"
AAC_INDEX = AAC_BASE + "/counties/"
AAC_ROBOTS = AAC_BASE + "/robots.txt"
DEFAULT_DELAY = 20.0  # what arcounties.org stated on 2026-10-13, if the read fails to say
RESULTS_URL = AAC_BASE + "/site/assets/files/6331/2024_general_election_winners.pdf"
RESULTS_FILE = os.path.join(INSTANCE, "data", "source", "aac-2024-jp-results.json")
RESULTS_TITLE = "2024 General Election Results, Justices of the Peace"

# Counties whose own website numbers its justices by district, read by a
# person and recorded here: fips -> {"url": the county's page, "asOf": date,
# "districts": {"1": "Name", ...}, and optionally "differs": {association's
# surname: county's surname} with "why"}. A county here must name the
# association's people, compared by surname (first names are spelled
# differently as a matter of course), in some order, or the build FAILS — two
# publishers disagreeing about who sits on a court is a thing a person reads,
# not one the build picks a side on. Where a person has read a surname that the
# two spell differently and settled it, `differs` maps the association's
# spelling to the county's; an entry there FAILS once the association stops
# printing that spelling, so it cannot outlive the difference it records.
#
# Surveyed 2026-10-13, every county, robots.txt read first: 37 counties number
# their justices on their own site, and these 20 are the ones whose list is
# complete, headed with the current term (or not dated), and names the
# association's people. The other 17, and why each is held back, are in
# ar/WATCH.md; 29 counties could not be read at all (no site, a block, or a
# robots.txt that refuses or cannot be read) and 9 publish no list by district.
NUMBERED = {
    "05005": {  # Baxter
        "url": "https://www.baxtercountyar.gov/justices.php",
        "asOf": "2026-10-13",
        "districts": {
            "1": "Dennis Frank",
            "2": "Mike McDonald",
            "3": "Rick Steiner",
            "4": "William Dirk Waldrop",
            "5": "Maryanne Edge",
            "6": "Lisa House",
            "7": "Bob Nault",
            "8": "Eddie Griffin",
            "9": "Cameron Davis",
            "10": "Shannon Walker",
            "11": "Eric Payne",
        },
    },
    "05015": {  # Carroll
        "url": "http://carrollcounty.us/QuorumCourt/Justices",
        "asOf": "2026-10-13",
        "districts": {
            "1": "Gary Capcik",
            "2": "Jack Deaton",
            "3": "Harrie Farrow",
            "4": "Hunter Rivett",
            "5": "Matt Phillips",
            "6": "Craig Hicks",
            "7": "Kellie Matt",
            "8": "Bobby James",
            "9": "Aaron Hall",
            "10": "Jerry King",
            "11": "Caroline Rogers",
        },
    },
    "05019": {  # Clark
        "url": "https://clarkcountyar.gov/quorum-court/",
        "asOf": "2026-10-13",
        "districts": {
            "1": "Zach Bledsoe",
            "2": "Michael Ankton",
            "3": "Vanilla Hannah",
            "4": "Llewellyn Terry Sr.",
            "5": "Jimmy King",
            "6": "Stuart Thomas",
            "7": "Jenna Scott",
            "8": "Garry \"BJ\" Johns",
            "9": "Andrea Angle",
            "10": "Wayne Baumgardner",
            "11": "Tracy Drake",
        },
    },
    "05029": {  # Conway
        "url": "https://conwaycountyar.com/home/quorum-court/",
        "asOf": "2026-10-13",
        "districts": {
            "1": "Philip Hoyt",
            "2": "Patrick Hartman",
            "3": "Steven Davenport",
            "4": "Thomas Flowers",
            "5": "Keith Long",
            "6": "Brigham Jones, Jr",
            "7": "Johnathan Trafford",
            "8": "Michael Hammons",
            "9": "John Trafford",
            "10": "Leslie Griffiths",
            "11": "Jimmy Miller",
        },
    },
    "05033": {  # Crawford
        "url": "https://crawfordcountyar.gov/officials/justices.cshtml",
        "asOf": "2026-10-13",
        "districts": {
            "1": "Robert Kevin Arnold",
            "2": "Lonnie Myers",
            "3": "Morgan R. Morgan",
            "4": "Lloyd Cole",
            "5": "Brad Martin",
            "6": "Mark Shaffer",
            "7": "Kyle Stinchcomb",
            "8": "Tia Woodruff",
            "9": "Jason Cox",
            "10": "Jayson Peppas",
            "11": "Kevin Bell",
            "12": "Donna Staton",
            "13": "Steve Johnson",
        },
    },
    "05049": {  # Fulton
        "url": "https://www.fultoncountyar.gov/quorum-court",
        "asOf": "2026-10-13",
        "districts": {
            "1": "Cris Newberry",
            "2": "Dennis Kinder",
            "3": "Albert Roork",
            "4": "Gary Phillips",
            "5": "Scott Watkins",
            "6": "Marjorie A. Rogers",
            "7": "Gary Tanner",
            "8": "Jimmy Marler",
            "9": "Hank Burke",
        },
    },
    "05051": {  # Garland
        "url": "https://www.garlandcounty.org/280/Justices-of-the-Peace",
        "asOf": "2026-10-13",
        "districts": {
            "1": "Micah Braughton",
            "2": "Thomas Anderson",
            "3": "Susan Garner Jones",
            "4": "Jimmy Young",
            "5": "Ralf Bailes",
            "6": "Ben Hooten",
            "7": "Dayton Myers",
            "8": "Alan Floyd",
            "9": "Dr. Brian Peters",
            "10": "Debbie McGrew",
            "11": "Ronald (Nub) Hunter",
            "12": "Jeremy Brown",
            "13": "Ralph Edds",
        },
    },
    "05057": {  # Hempstead
        "url": "https://hempsteadcountyar.com/justice-of-the-peace/",
        "asOf": "2026-10-13",
        # District 1 is printed vacant, and the association lists one vacancy.
        "districts": {
            "1": "Vacant",
            "2": "Krystal Goshen",
            "3": "Doris Brown",
            "4": "Ed Darling",
            "5": "Victor Ford",
            "6": "Joe Mac Raschke",
            "7": "Steve Atchley",
            "8": "David Clayton",
            "9": "Jessie Henry",
            "10": "Jay Lathrop",
            "11": "Keith Steed",
        },
    },
    "05065": {  # Izard
        "url": "https://www.izardcountyar.org/plugins/show_image.php?id=726",
        "asOf": "2026-10-13",
        # The county's quorum court page links a document titled "Quorum Court
        # Members 2026" listing DISTRICT 1 to 9.
        "districts": {
            "1": "Mark Simino",
            "2": "Kelly Hatman",
            "3": "Randy “Hank” Sherrell",
            "4": "Frances Syce",
            "5": "John David Miller",
            "6": "Justin Thornton",
            "7": "Quillen Edwards",
            "8": "Doug Harber",
            "9": "Richard “Rich” Emmens",
        },
    },
    "05071": {  # Johnson
        "url": "https://johnsoncounty.arkansas.gov/quorum-court/",
        "asOf": "2026-10-13",
        # The association has no website for the county; the county's own site was
        # found by its address. The page's "Pete Petersen" for District 10 is the
        # association's Robert Petersen, the District 10 winner on its December
        # 2024 results list.
        "districts": {
            "1": "Lewis “Ray” Hobbs",
            "2": "Paula Ober",
            "3": "Van Hill",
            "4": "Bethany Bean",
            "5": "Mike Estes",
            "6": "John Payne",
            "7": "Kris Muldoon",
            "8": "Katie Howard",
            "9": "Larry Jones",
            "10": "Pete Petersen",
            "11": "Bryan Cooper",
        },
    },
    "05081": {  # Little River
        "url": "https://lrcounty.org/departments/quorum-court/",
        "asOf": "2026-10-13",
        "districts": {
            "1": "Andrea Billingsley",
            "2": "Lisa Hearn",
            "3": "Keith Pullen",
            "4": "Mark Ardwin",
            "5": "Tyler Davis",
            "6": "John Bowman",
            "7": "Charles Henderson",
            "8": "Suzanne Ward",
            "9": "Larry Phillips",
        },
    },
    "05083": {  # Logan
        "url": "https://logancountyark.org/quorum-court",
        "asOf": "2026-10-13",
        "districts": {
            "1": "Charles Sparks",
            "2": "Gary Rhinehart",
            "3": "Mike Schluterman",
            "4": "Joyce Koch",
            "5": "Bill Wright",
            "6": "Jeffrey O'Neal",
            "7": "Bobby Cobb",
            "8": "Dalton Haller",
            "9": "Sam Tabler",
            "10": "Chistopher Loftin",
            "11": "Brenda Brewer",
        },
    },
    "05087": {  # Madison
        "url": "https://madisoncountyar.gov/quorum_court.php",
        "asOf": "2026-10-13",
        # The page's JP contact list, which the page loads from its own feed (a
        # POST to process.php, job LoadJPs) a moment after it opens.
        "districts": {
            "1": "Bob Rawson",
            "2": "Cord Riley",
            "3": "Jason Yates",
            "4": "Sam Roddy",
            "5": "Wendy Pettz",
            "6": "Shannon Fancher",
            "7": "Joe Wilson",
            "8": "Jeff Marley",
            "9": "Michael Keck",
        },
    },
    "05089": {  # Marion
        "url": "https://marioncounty.arkansas.gov/Marion-County-Quorum-Court",
        "asOf": "2026-10-13",
        "districts": {
            "1": "Chuck Van Velkinburgh",
            "2": "Sandra Lee",
            "3": "Travis Hopson",
            "4": "Kolton Jensen",
            "5": "John Reed",
            "6": "Leslie Kerwood",
            "7": "Wesley Shipman",
            "8": "Tommy Dorsey",
            "9": "Tommy Dean Johnson",
        },
    },
    "05119": {  # Pulaski
        "url": "https://www.pulaskicounty.net/quorum-court",
        "asOf": "2026-10-13",
        "differs": {"Elliot": "Elliott"},
        "why": "The Pulaski County Election Commission's elected officials list (votepulaskiar.gov, May 2025) prints \"Paul Elliott\" for District 14, as the county does; the association prints \"Paul Elliot\". District 13's Douglas House was appointed on 3 September 2026, per the county's own news.",
        "districts": {
            "1": "Rebekah L. Davis",
            "2": "Natalie Capps",
            "3": "Kathy Lewison",
            "4": "Julie Blackwood",
            "5": "Steven Person",
            "6": "Donna Massey",
            "7": "Dianne Curry",
            "8": "Curtis Keith",
            "9": "Tina Ward",
            "10": "Patricia Young-Baker",
            "11": "Aaron Robinson",
            "12": "Luke McCoy",
            "13": "Douglas House",
            "14": "Paul Elliott",
            "15": "Staci Medlock",
        },
    },
    "05123": {  # St. Francis
        "url": "https://stfranciscountyar.gov/departments/quorum-court/",
        "asOf": "2026-10-13",
        # District 10 is printed vacant, and the association lists one vacancy.
        "districts": {
            "1": "Charles Jones",
            "2": "Jimmy Long",
            "3": "Kevin Vandiver",
            "4": "David Coleman",
            "5": "Ernestine Weaver",
            "6": "Regan Hill",
            "7": "Nathaniel Murray",
            "8": "Christopher (Chris) Ray",
            "9": "Maceo Hawkins",
            "10": "VACANT",
            "11": "Jamie Busby",
        },
    },
    "05125": {  # Saline
        "url": "https://salinecounty.org/government/quorum_court/justices_of_the_peace.php",
        "asOf": "2026-10-13",
        "districts": {
            "1": "Pat Bisbee",
            "2": "Wilson Hatcher",
            "3": "Carlton Billingsley",
            "4": "Keith Kellum",
            "5": "Mike Davidson",
            "6": "Rick Bellinger",
            "7": "Josh Curtis",
            "8": "Ed Albares",
            "9": "CJ Engel",
            "10": "Jim Whitley",
            "11": "Clint Chism",
            "12": "Stephanie Johnson",
            "13": "Karen Crowson",
        },
    },
    "05131": {  # Sebastian
        "url": "https://sebastiancountyar.gov/Departments/County-Judge/Quorum-Court/Current-Members",
        "asOf": "2026-10-13",
        "districts": {
            "1": "Johnny Hobbs",
            "2": "Jackie Davis",
            "3": "Shawn Looper",
            "4": "James Butler",
            "5": "Brandon Morrison",
            "6": "Danny W. Aldridge",
            "7": "Kenneth Williamson",
            "8": "Valeria J. Robinson",
            "9": "Rhonda Royal",
            "10": "Dickie Lee Robertson",
            "11": "Gerry Ward",
            "12": "Tommy Camp",
            "13": "Lorrie Glidewell Runion",
        },
    },
    "05135": {  # Sharp
        "url": "https://sharpcountyar.com/officials",
        "asOf": "2026-10-13",
        # The officials page, which fills itself in from its own public feed a
        # moment after it opens.
        "districts": {
            "1": "Kevin Dienst",
            "2": "Briana DiIorio",
            "3": "Joey Barnes",
            "4": "Roy \"Chuck\" Murphy",
            "5": "Tommy Estes",
            "6": "Jackie Pickett",
            "7": "Buell Wilkes",
            "8": "Jeral Hastings",
            "9": "Zack Baxter",
        },
    },
    "05137": {  # Stone
        "url": "https://www.stonecountyar.gov/justices-of-the-peace",
        "asOf": "2026-10-13",
        "districts": {
            "1": "Jim Bullard",
            "2": "Travis Trammell",
            "3": "Billy Wayne Mitchell",
            "4": "Jason Kocher",
            "5": "Ronald Clark",
            "6": "Mark Davis",
            "7": "Michael W. Vickers",
            "8": "Neal Harness",
            "9": "Eddie Cowell",
        },
    },
}

# fips -> why a person accepted that the association's line carries a different
# number of names than the map draws districts. Empty: on 2026-10-13 every
# county matched.
COUNT_DIFFERS = {}

# fips -> a county where the judiciary's directory and the association name
# different county judges, settled by a person reading a third source.
#   directory  the name the judiciary's directory prints, which the entry
#              overrides; the build FAILS once the directory prints anything
#              else, because then the disagreement this entry settles is gone
#   name       the judge, spelled as the deciding source spells it; its surname
#              must still be the association's every week
#   source / sourceUrl / asOf   what the card credits for the name. Where the
#              deciding source is the association's own page the card dates it
#              by the weekly read, and otherwise by `asOf`, the day a person
#              read it — never a date for a read nobody made
#   why        the reading, with its date
JUDGE_DISAGREES = {
    "05009": {  # Boone
        "directory": "Robert Hathaway",
        "name": "Mitchell Archer",
        "source": "Boone County's own page for its county judge",
        "sourceUrl": "https://www.boonecountyar.com/county-judge",
        "asOf": "2026-10-13",
        "why": "Read 2026-10-13: the county's own county-judge page names "
               "\"Mitchell Archer, County Judge\" at 100 North Main, Ste 300, "
               "Harrison, with the office telephone the directory prints, and "
               "a separate county judge elect, so the directory's Robert "
               "Hathaway is an earlier judge. The association prints the "
               "first name \"MItchell\", so the name is spelled as the "
               "county spells it.",
    },
    "05025": {  # Cleveland
        "directory": "Jimmy D. Cummings",
        "name": "Don Triplett",
        "source": "the Association of Arkansas Counties' page for Cleveland County",
        "sourceUrl": "https://arcounties.org/counties/cleveland/",
        "asOf": "2026-10-13",
        "why": "Read 2026-10-13: the Cleveland County Herald reported on "
               "2 February 2026 that Jimmy Cummings died in August 2025 and "
               "that his appointed successor had also died, and then that the "
               "quorum court appointed Don Triplett to serve through "
               "31 December 2026 (\"Triplett Appointed As New County Judge\"). "
               "The county has no website of its own that answers, so the "
               "association's page, which names Triplett and is read every "
               "week, is the credited source.",
    },
    "05041": {  # Desha
        "directory": "Richard Tindall",
        "name": "Wayne Smith",
        "source": "the Association of Arkansas Counties' page for Desha County",
        "sourceUrl": "https://arcounties.org/counties/desha/",
        "asOf": "2026-10-13",
        "why": "Read 2026-10-13: the Dumas Clarion's photo caption from May 2026 "
               "names \"Desha County Judge Wayne Smith\" administering the oath "
               "to the sheriff the quorum court appointed on 19 May 2026, and "
               "the paper's 2025 items name him swearing in deputies. Read "
               "through a search of the paper's site, because the page that "
               "carried the caption rotates and no longer shows it. When "
               "Richard Tindall left office is NOT established. Desha County "
               "has no website the association links, so its page, which is "
               "read every week, is the credited source.",
    },
    "05069": {  # Jefferson
        "directory": "Gerald L. Robinson",
        "name": "Ivan Whitfield",
        "source": "the Association of Arkansas Counties' page for Jefferson County",
        "sourceUrl": "https://arcounties.org/counties/jefferson/",
        "asOf": "2026-10-13",
        "why": "Read 2026-10-13: the Pine Bluff Commercial reported on "
               "1 July 2026 (\"Whitfield sworn in as Jefferson County judge\") "
               "that the quorum court chose Ivan Whitfield on 12 June to serve "
               "out Gerald Robinson's term after Robinson retired on 30 June. "
               "The county's own site answers its robots.txt with HTTP 403 and "
               "was not read. The association's page, which names Whitfield "
               "and is read every week, is the credited source.",
    },
    "05133": {  # Sevier
        "directory": "Dick Tallman",
        "name": "Sandra Dunn",
        "source": "the Association of Arkansas Counties' page for Sevier County",
        "sourceUrl": "https://arcounties.org/counties/sevier/",
        "asOf": "2026-10-13",
        "why": "Read 2026-10-13: Sevier County's own county-judge page "
               "(seviercountyar.org/government/departments/county-judge, no "
               "robots.txt, HTTP 404) names \"Sevier County Judge - Sandra "
               "Dunn\" with the office telephone and street the association "
               "prints, and its home page lists her among the county's "
               "officials. When Dick Tallman left office is NOT established. "
               "The association's page, which agrees with the county's and is "
               "read every week, is the credited source.",
    },
}


def fail(msg):
    raise SystemExit("build-ar-county-officials: FATAL: %s" % msg)


def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def surname(name):
    parts = [p for p in fold(name).split() if p not in ("jr", "sr", "ii", "iii", "iv")]
    return parts[-1] if parts else ""


def tidy(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


# ---------- fetch ----------
class Fetcher:
    def __init__(self, cache):
        import requests  # noqa: PLC0415
        self.session = requests.Session()
        self.cache = cache
        self.last = {}
        self.delay = {}

    def _cache_path(self, url):
        if not self.cache:
            return None
        return os.path.join(self.cache, re.sub(r"[^A-Za-z0-9]+", "_", url) + ".html")

    def get(self, url, delay=0.0):
        cp = self._cache_path(url)
        if cp and os.path.exists(cp):
            with open(cp, encoding="utf-8") as f:
                return f.read()
        require_robots_once(url, USER_AGENT, label="ar-county-officials")
        host = re.sub(r"^https?://([^/]+).*$", r"\1", url)
        wait = self.last.get(host, 0) + delay - time.time()
        if wait > 0:
            time.sleep(wait)
        resp = self.session.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
        self.last[host] = time.time()
        resp.raise_for_status()
        text = resp.text
        if cp:
            os.makedirs(self.cache, exist_ok=True)
            with open(cp, "w", encoding="utf-8") as f:
                f.write(text)
        return text

    def get_bytes(self, url, delay=0.0):
        require_robots_once(url, USER_AGENT, label="ar-county-officials")
        host = re.sub(r"^https?://([^/]+).*$", r"\1", url)
        wait = self.last.get(host, 0) + delay - time.time()
        if wait > 0:
            time.sleep(wait)
        resp = self.session.get(url, headers={"User-Agent": USER_AGENT}, timeout=120)
        self.last[host] = time.time()
        resp.raise_for_status()
        return resp.content


def aac_delay():
    from robots_policy import fetch_verdict  # noqa: PLC0415
    v = fetch_verdict(AAC_ROBOTS, USER_AGENT)
    d = v.policy.crawl_delay(USER_AGENT) if v.policy is not None else None
    return float(d) if d else DEFAULT_DELAY


# ---------- parse ----------
def parse_judges(page):
    out = {}
    for row in re.findall(r"<tr>(.*?)</tr>", page, re.S):
        cells = {k: tidy(v) for k, v in re.findall(
            r'class="views-field views-field-([a-z-]+)">(.*?)</td>', row, re.S)}
        if cells.get("field-position-county-staff") != "Judge":
            continue
        county = cells.get("field-county", "")
        if county in out:
            fail("the judiciary's directory names two judges for %s" % county)
        out[county] = {
            "name": cells.get("title", ""),
            "street": cells.get("field-n", ""),
            "city": cells.get("field-city", ""),
            "zip": cells.get("field-zip-code", ""),
            "phone": cells.get("field-phone-number", ""),
        }
    return out


def parse_index(page):
    return [(AAC_BASE + h, n.strip()) for h, n in
            re.findall(r"href='(/counties/[a-z-]+/)'>([^<]+)<", page)]


def parse_aac(page):
    """The judge's name and office line, the justices, and the county's own
    website, from one county page."""
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
    # Inline formatting is not a line break: Pike's page underlines one comma
    # in its justice line (`Mohlenhoff<u>,</u> John J. Plyler`), and reading
    # every tag as a break cut the list at that comma, two names short.
    body = re.sub(r"</?(?:u|em|i|b|span|font)(?:\s[^>]*)?>", "", body, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", "\n", body))
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]
    out = {"judge": None, "judge_address": None, "justices": None, "website": None}
    for i, ln in enumerate(lines):
        if ln == "County Judge" and out["judge"] is None and i + 1 < len(lines):
            out["judge"] = lines[i + 1]
            for nxt in lines[i + 2:i + 12]:
                if nxt.startswith("Address:"):
                    out["judge_address"] = nxt[len("Address:"):].strip()
                    break
        if ln == "Justices of the Peace" and i + 1 < len(lines):
            out["justices"] = split_names(lines[i + 1])
    # The county's own site is the one link whose visible text is itself an
    # address ("www.baxtercounty.org", "https://bentoncountyar.gov",
    # "jacksoncountyar.com"); the page's other links carry words or images.
    for href, label in re.findall(r'<a[^>]+href="(https?://[^"]+)"[^>]*>\s*([^<\s]+)\s*<', page):
        if re.match(r"^(https?://)?(www\.)?[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}/?$", label, re.I):
            out["website"] = href
            break
    return out


def website_names_county(url, county):
    """True when a website's host carries the county's name. Measured
    2026-10-13, the association's Hempstead page links garlandcounty.org, a
    different county's site, so a link is shipped only where its host names
    the county it is offered for ("countyofcolumbia.org", "hotspringcounty.org",
    "crawford-county.org")."""
    host = re.sub(r"^https?://([^/:]+).*$", r"\1", url or "").lower()
    key = re.sub(r"[^a-z]", "", fold(county).replace("saint", "st"))
    return bool(key) and key in re.sub(r"[^a-z]", "", host)


SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}


def split_names(line):
    """The association's one line of justices, as a list of names. Measured
    2026-10-13 on its 75 pages, the line is comma-separated with three habits a
    plain split gets wrong: the last two names joined by "and" ("Lloyd Brosius
    and Curtis Ahrens."), a full stop after the last name, and a suffix set off
    by its own comma ("John D. Trafford, Jr."), which would otherwise read as a
    person called "Jr."."""
    parts = [p.strip() for p in line.strip().rstrip(".").split(",")]
    names = []
    for part in parts:
        if not part:
            continue
        if fold(part) in SUFFIXES and names:
            names[-1] = names[-1] + ", " + part
            continue
        names.extend(n.strip() for n in re.split(r"\s+and\s+|\s*&\s*", part) if n.strip())
    return names


def same_office(court, aac_address):
    """True when the two publishers give the judge's office the same street
    number and city."""
    if not aac_address or not court.get("street"):
        return False
    num_c = re.match(r"\s*#?(\d+)", court["street"])
    num_a = re.match(r"\s*#?(\d+)", aac_address)
    if not num_c or not num_a or num_c.group(1) != num_a.group(1):
        return False
    return fold(court.get("city")) in fold(aac_address)


def is_vacant(name):
    return fold(name) in ("vacant", "vacancy", "open", "open seat")


# ---------- the association's 2024 election results ----------
def parse_results_pdf(body):
    """{county name as printed: {district: printed line}} and the "Updated"
    date, from the association's results PDF. The document is set in three
    columns (measured 2026-10-13: 19 US-letter pages, columns starting near
    x 36, 230 and 430 pt), each a run of a county heading in capitals, then
    "District N" lines each followed by the winner, "Name* (R)", the
    asterisk marking an incumbent. Words are read with their positions,
    grouped into lines per column and read column by column, because a
    flattened page reads across all three columns at once. A name that wraps
    onto a second line is joined back to its district."""
    # Optional on purpose: only --read-results parses the PDF, and the weekly
    # refresh, which never does, installs no PDF library.
    try:
        import pdfplumber  # noqa: PLC0415
    except ImportError:
        fail("--read-results needs pdfplumber (pip install -c scripts/requirements.txt pdfplumber)")
    lines = []
    updated = None
    with pdfplumber.open(io.BytesIO(body)) as pdf:
        for pi, page in enumerate(pdf.pages):
            if pi == 0:
                # The cover page: centred title lines straddle the column
                # split, so it is read as plain text, for its date alone. Its
                # title is set twice over itself for weight, which reads as
                # "UUppddaatteedd" until the duplicate characters are dropped.
                m = re.search(r"Updated\s+([A-Z][a-z]+)\.?\s+(\d{1,2}),\s+(\d{4})",
                              page.dedupe_chars().extract_text() or "")
                if m:
                    updated = datetime.datetime.strptime(
                        "%s %s %s" % (m.group(1)[:3], m.group(2), m.group(3)),
                        "%b %d %Y").date().isoformat()
                continue
            groups = {}
            for w in page.extract_words():
                col = 0 if w["x0"] < 200 else (1 if w["x0"] < 400 else 2)
                groups.setdefault((col, round(w["top"])), []).append(w)
            merged = []
            for key in sorted(groups):
                if merged and merged[-1][0][0] == key[0] and abs(merged[-1][0][1] - key[1]) <= 2:
                    merged[-1][1].extend(groups[key])
                else:
                    merged.append([key, list(groups[key])])
            for (col, top), words in merged:
                words.sort(key=lambda w: w["x0"])
                text = " ".join(w["text"] for w in words).strip()
                if text:
                    lines.append((pi, col, top, text))
    lines.sort(key=lambda ln: (ln[0], ln[1], ln[2]))
    out = {}
    county = dist = None
    stray = []
    for _pi, _col, _top, t in lines:
        if t in ("2025 JUSTICES OF THE PEACE", "*Denotes Incumbent"):
            continue
        m = re.match(r"^District (\d+)$", t)
        if m:
            dist = m.group(1)
            continue
        if re.match(r"^[A-Z][A-Z .']+$", t):
            county = t
            out[county] = {}
            dist = None
            continue
        if county and dist:
            out[county][dist] = (out[county][dist] + " " + t) if dist in out[county] else t
            continue
        stray.append(t)
    if stray:
        fail("the results PDF has lines outside any county and district: %r" % stray[:5])
    if not updated:
        fail("the results PDF's first page carries no \"Updated\" date")
    return out, updated


def results_record(printed):
    """{"name", "party", "incumbent"} from one printed winner line, or
    {"vacant": true} where the results print "Vacant" — five districts,
    measured 2026-10-13 (Franklin 4, Howard 7, Union 6, Van Buren 1 and
    White 13), where nobody won in 2024."""
    if is_vacant(printed):
        return {"vacant": True}
    m = re.match(r"^(.*?)\s*\(([A-Z]{1,3})\)\s*$", printed)
    name, party = (m.group(1), m.group(2)) if m else (printed, None)
    incumbent = "*" in name
    return {"name": re.sub(r"\s+", " ", name.replace("*", "")).strip(),
            "party": party, "incumbent": incumbent}


def read_results(body, today):
    """The snapshot ar/data/source/ keeps: every county's winners keyed by its
    Census FIPS and district, refused unless every county and every district
    the state's map draws is there exactly once."""
    printed, updated = parse_results_pdf(body)
    counties = census_counties()
    seats = seats_from_map()
    by_fold = {fold(n): f for n, f in counties.items()}
    out = {}
    for name, dd in printed.items():
        fips = by_fold.get(fold(name))
        if not fips:
            fail("the results name a county the Census does not: %r" % name)
        if fips in out:
            fail("the results print %r twice" % name)
        if sorted(int(d) for d in dd) != list(range(1, seats[fips] + 1)):
            fail("%s: the results give districts %s and the map draws 1..%d"
                 % (name, sorted(int(d) for d in dd), seats[fips]))
        recs = {d: results_record(t) for d, t in dd.items()}
        for d, r in recs.items():
            if not r.get("vacant") and not r["name"]:
                fail("%s District %s: the results print no winner (%r)" % (name, d, dd[d]))
        out[fips] = recs
    if set(out) != set(seats):
        fail("the results cover %d counties, the map %d" % (len(out), len(seats)))
    return {
        "$comment": "The Association of Arkansas Counties' 2024 general election "
                    "results for justices of the peace, read by "
                    "ar/scripts/build_ar_county_officials.py --read-results. A dated "
                    "record of who won each district, kept here because it does not "
                    "change; the weekly build names a winner only while the "
                    "association's current list for the county still carries them.",
        "title": RESULTS_TITLE,
        "publisher": "Association of Arkansas Counties",
        "url": RESULTS_URL,
        "updated": updated,
        "read": today,
        "sha256": hashlib.sha256(body).hexdigest(),
        "counties": {f: out[f] for f in sorted(out)},
    }


def load_results():
    if not os.path.exists(RESULTS_FILE):
        fail("%s is missing — run with --read-results" % os.path.relpath(RESULTS_FILE))
    with open(RESULTS_FILE, encoding="utf-8") as f:
        return json.load(f)


def given_names(name):
    """Every word of a name but its surname and any suffix, folded — the first
    name, middle names or initials, and a nickname printed in quotes or
    brackets ('James G. (Jim) Anders', 'Roy “Chuck” Murphy')."""
    parts = [p for p in fold(name).split() if p not in SUFFIXES]
    return parts[:-1]


def same_given_name(a, b):
    """True when two names that share a surname plausibly name one person.
    The two documents spell first names differently as a matter of course —
    measured 2026-10-13, 33 of the 728 surname matches differ in the first
    name, nearly all a nickname, an initial or a misspelling ('Michael' and
    'Mike', 'C.J.' and 'CJ', 'Keith' and 'Kieth', 'Laurie \"Harrie\"' and
    'Harrie') — so a name matches when a word of more than one letter is
    shared, when one word begins another ('Brad', 'Bradley'), or when the
    first names share an initial. Three did not, and are left unnamed rather
    than guessed: 'Jonathon Davis' and 'Allen Davis' in Greene, 'Patrick
    Robinson IV' and 'Alfred Robinson IV' in Phillips, and 'Danny Loggins' and
    'Jerry Loggins' in Searcy."""
    ga, gb = given_names(a), given_names(b)
    if not ga or not gb:
        return False
    long_a = {w for w in ga if len(w) > 1}
    long_b = {w for w in gb if len(w) > 1}
    if long_a & long_b:
        return True
    for x in long_a:
        for y in long_b:
            if min(len(x), len(y)) >= 3 and (x.startswith(y) or y.startswith(x)):
                return True
    return ga[0][0] == gb[0][0]


def match_results(winners, names):
    """Which of a county's 2024 winners are still on the association's current
    list. Returns ({district: winner's name}, [districts whose winner is not on
    the list], [districts where the list cannot say], [districts the results
    print as vacant]). A winner is matched by
    surname; where the county has two justices of one surname (Ashley's two
    Pippens, Conway's two Traffords) the whole name decides, then the first
    name, and anything still ambiguous is left unnamed. No current justice is
    matched to two districts."""
    current = [n for n in names if not is_vacant(n)]
    picked = {}
    gone, unclear, empty = [], [], []
    for d in sorted(winners, key=int):
        if winners[d].get("vacant"):
            empty.append(d)
            continue
        w = winners[d]["name"]
        cands = [n for n in current if surname(n) == surname(w)]
        if not cands:
            gone.append(d)
            continue
        exact = [n for n in cands if fold(n) == fold(w)]
        pick = exact if len(exact) == 1 else [n for n in cands if same_given_name(w, n)]
        if len(pick) == 1:
            picked[d] = pick[0]
        else:
            unclear.append(d)
    used = {}
    for d, n in picked.items():
        used.setdefault(n, []).append(d)
    for n, ds in used.items():
        if len(ds) > 1:
            unclear.extend(ds)
            for d in ds:
                del picked[d]
    named = {d: winners[d]["name"] for d in sorted(picked, key=int)}
    return named, gone, sorted(unclear, key=int), empty


# ---------- build ----------
def seats_from_map():
    with open(DISTRICTS_FILE, encoding="utf-8") as f:
        feats = json.load(f)["features"]
    out = {}
    for ft in feats:
        p = ft["properties"]
        out[p["countyFips"]] = out.get(p["countyFips"], 0) + 1
    return out


def census_counties():
    with open(COUNTIES_FILE, encoding="utf-8") as f:
        feats = json.load(f)["features"]
    return {ft["properties"]["BASENAME"]: ft["properties"]["GEOID"] for ft in feats}


def build(fetcher, today):
    counties = census_counties()
    seats = seats_from_map()
    if len(counties) != 75 or set(seats) != set(counties.values()):
        fail("the county fabric (%d) and the district map (%d counties) disagree"
             % (len(counties), len(seats)))

    judges = parse_judges(fetcher.get(JUDGES_URL))
    if set(judges) != set(counties):
        fail("the judiciary's directory names judges for %d counties; missing %s, "
             "unknown %s" % (len(judges), sorted(set(counties) - set(judges)),
                             sorted(set(judges) - set(counties))))

    results = load_results()
    delay = aac_delay()
    index = parse_index(fetcher.get(AAC_INDEX))
    by_name = {n: u for u, n in index}
    if set(by_name) != set(counties):
        fail("the association's index lists %d counties; missing %s, unknown %s"
             % (len(by_name), sorted(set(counties) - set(by_name)),
                sorted(set(by_name) - set(counties))))

    out = {}
    problems = []
    addresses = 0
    dropped_sites = []
    for name in sorted(counties):
        fips = counties[name]
        url = by_name[name]
        aac = parse_aac(fetcher.get(url, delay=delay))
        court = judges[name]
        if not aac["justices"]:
            problems.append("%s: the association's page carries no justices line" % name)
            continue
        names = aac["justices"]
        if len(names) != seats[fips] and fips not in COUNT_DIFFERS:
            problems.append("%s: the association names %d justices and the map draws "
                            "%d districts" % (name, len(names), seats[fips]))
        judge = {"name": court["name"], "phone": court["phone"],
                 "source": "the Arkansas Judiciary's directory of county judges and clerks",
                 "sourceUrl": JUDGES_URL, "asOf": today, "weekly": True}
        settled = JUDGE_DISAGREES.get(fips)
        if not aac["judge"]:
            problems.append("%s: the association's page names no county judge" % name)
        elif surname(aac["judge"]) == surname(court["name"]):
            if settled:
                problems.append("%s: JUDGE_DISAGREES settles a disagreement that is gone — "
                                "both publishers now name %r; retire the entry"
                                % (name, court["name"]))
        elif not settled:
            problems.append("%s: the judiciary names %r as county judge and the "
                            "association names %r" % (name, court["name"], aac["judge"]))
        elif fold(settled["directory"]) != fold(court["name"]):
            problems.append("%s: the judiciary's directory now names %r, not the %r "
                            "JUDGE_DISAGREES records; re-read and update the entry"
                            % (name, court["name"], settled["directory"]))
        elif surname(settled["name"]) != surname(aac["judge"]):
            problems.append("%s: the association now names %r, not the %r JUDGE_DISAGREES "
                            "records; re-read and update the entry"
                            % (name, aac["judge"], settled["name"]))
        else:
            weekly = settled["sourceUrl"] == url
            judge = {"name": settled["name"], "phone": court["phone"],
                     "source": settled["source"], "sourceUrl": settled["sourceUrl"],
                     "asOf": today if weekly else settled["asOf"], "weekly": weekly,
                     "note": "The Arkansas Judiciary's directory names an earlier judge."}
        if same_office(court, aac["judge_address"]):
            judge["office"] = "%s, %s, AR %s" % (court["street"], court["city"], court["zip"])
            addresses += 1
        if aac["website"] and not website_names_county(aac["website"], name):
            dropped_sites.append("%s (%s)" % (name, aac["website"]))
            aac["website"] = None
        entry = {
            "county": name + " County",
            "judge": judge,
            "quorumCourt": {
                "seats": seats[fips],
                # A vacant seat carries no `name`: the word "Vacant" in a name
                # field is a marker standing where a person should be, which
                # validate_officeholder_names.py refuses fleet-wide.
                "justices": [{"vacant": True} if is_vacant(n) else {"name": n}
                             for n in names],
                "sourceUrl": url,
                "publisher": "Association of Arkansas Counties",
                "asOf": today,
            },
        }
        if aac["website"]:
            entry["website"] = aac["website"]
        num = NUMBERED.get(fips)
        if num:
            # Held by SURNAME, because the two spell first names differently
            # as a matter of course ("Bob Nault" on Baxter's page, "Robert
            # Nault" on the association's), and the district card prints the
            # county's spelling since the county is the source it credits.
            differs = {fold(k): fold(v) for k, v in (num.get("differs") or {}).items()}
            raw = [surname(n) for n in names if not is_vacant(n)]
            for gone in sorted(set(differs) - set(raw)):
                problems.append("%s: NUMBERED records the association spelling %r, "
                                "which it no longer prints; re-read and retire it"
                                % (name, gone))
            listed = sorted(differs.get(n, n) for n in raw)
            theirs = sorted(surname(n) for n in num["districts"].values() if not is_vacant(n))
            if listed != theirs:
                problems.append("%s: the county's own page and the association name "
                                "different justices: only the association %s, only the "
                                "county %s" % (name, sorted(set(listed) - set(theirs)),
                                               sorted(set(theirs) - set(listed))))
            entry["quorumCourt"]["districts"] = num["districts"]
            entry["quorumCourt"]["districtSourceUrl"] = num["url"]
            entry["quorumCourt"]["districtAsOf"] = num["asOf"]
        entry["quorumCourt"]["results"] = results_block(results, fips, names, today)
        out[fips] = entry
    if problems:
        for p in problems:
            print("build-ar-county-officials: FAIL: " + p)
        raise SystemExit(1)
    for d in dropped_sites:
        print("build-ar-county-officials: note: website not shipped, its host does not "
              "name the county: " + d)
    return out, addresses


def results_block(results, fips, names, today):
    """What the district card needs from the 2024 results for one county:
    the winners still on the association's current list, by district, and
    which districts the results cannot name and why. `asOf` is the day the
    comparison was made, which is the day the current list was read."""
    named, gone, unclear, empty = match_results(results["counties"][fips], names)
    return {
        "districts": named,
        "notOnList": gone,
        "unclear": unclear,
        "noWinner": empty,
        "sourceUrl": results["url"],
        "publisher": results["publisher"],
        "title": results["title"],
        "updated": results["updated"],
        "asOf": today,
    }


def check_shipped(doc):
    problems = []
    seats = seats_from_map()
    if set(doc) != set(seats):
        problems.append("the file covers %d counties, the map %d" % (len(doc), len(seats)))
    for fips, e in doc.items():
        qc = e.get("quorumCourt") or {}
        if qc.get("seats") != seats.get(fips):
            problems.append("%s: %r seats against the map's %r" % (fips, qc.get("seats"),
                                                                 seats.get(fips)))
        if len(qc.get("justices") or []) != qc.get("seats") and fips not in COUNT_DIFFERS:
            problems.append("%s: %d justices for %r seats" % (
                fips, len(qc.get("justices") or []), qc.get("seats")))
        if not (e.get("judge") or {}).get("name"):
            problems.append("%s: no county judge" % fips)
        d = qc.get("districts")
        if d is not None and sorted(int(k) for k in d) != list(range(1, qc["seats"] + 1)):
            problems.append("%s: its numbered districts are not 1..%d" % (fips, qc["seats"]))
    if set(NUMBERED) - set(doc):
        problems.append("NUMBERED names counties the file does not carry")
    for fips, settled in JUDGE_DISAGREES.items():
        shipped = (doc.get(fips) or {}).get("judge") or {}
        if shipped.get("name") != settled["name"]:
            problems.append("%s is in JUDGE_DISAGREES as %r and ships %r — rebuild"
                            % (fips, settled["name"], shipped.get("name")))
    for fips, e in doc.items():
        site = e.get("website")
        if site and not website_names_county(site, e.get("county", "").replace(" County", "")):
            problems.append("%s: ships a website whose host does not name the county" % fips)
    for fips in NUMBERED:
        if fips in doc and "districts" not in doc[fips]["quorumCourt"]:
            problems.append("%s is in NUMBERED and ships no districts — rebuild" % fips)
    # The results block is re-derived from the snapshot and the shipped list,
    # so a hand edit, a stale snapshot or a change to the matching rule that
    # was not rebuilt all fail here, offline.
    results = load_results()
    if set(results["counties"]) != set(seats):
        problems.append("the 2024 results snapshot covers %d counties, the map %d"
                        % (len(results["counties"]), len(seats)))
    for fips, recs in results["counties"].items():
        if sorted(int(d) for d in recs) != list(range(1, seats.get(fips, 0) + 1)):
            problems.append("%s: the 2024 results snapshot does not number 1..%r"
                            % (fips, seats.get(fips)))
    for fips, e in doc.items():
        qc = e.get("quorumCourt") or {}
        shipped = qc.get("results")
        if fips not in results["counties"]:
            continue
        names = ["Vacant" if j.get("vacant") else j.get("name", "")
                 for j in qc.get("justices") or []]
        want = results_block(results, fips, names, (shipped or {}).get("asOf"))
        if shipped != want:
            problems.append("%s: the shipped 2024-results block is not what the snapshot "
                            "and the shipped list give — rebuild" % fips)
    return problems


def named_counts(doc):
    """(districts the district card names, from the county's own list, from
    the 2024 results) — the county's own list wins where it exists."""
    own = res = 0
    for e in doc.values():
        qc = e["quorumCourt"]
        for d in range(1, qc["seats"] + 1):
            d = str(d)
            if qc.get("districts") and d in qc["districts"]:
                own += not is_vacant(qc["districts"][d])
            elif d in ((qc.get("results") or {}).get("districts") or {}):
                res += 1
    return own + res, own, res


def summary(doc):
    n = sum(len(e["quorumCourt"]["justices"]) for e in doc.values())
    vac = sum(1 for e in doc.values() for j in e["quorumCourt"]["justices"] if j.get("vacant"))
    total, own, res = named_counts(doc)
    gone = sum(len(e["quorumCourt"]["results"]["notOnList"]) for e in doc.values())
    unclear = sum(len(e["quorumCourt"]["results"]["unclear"]) for e in doc.values())
    return ("%d county judges, %d justice seats (%d vacant); the district card names "
            "%d of %d districts — %d from the county's own list in %d counties, %d from "
            "the 2024 results; across all 75 counties %d 2024 winners are no longer on "
            "the current list and %d cannot be told apart from it"
            % (len(doc), n, vac, total, sum(e["quorumCourt"]["seats"] for e in doc.values()),
               own, sum(1 for e in doc.values() if "districts" in e["quorumCourt"]), res,
               gone, unclear))


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--check", action="store_true", help="offline: hold the shipped file "
                    "to the district map, its own registry and the 2024 results snapshot")
    ap.add_argument("--cache", help="directory to keep raw pages in, and to reuse them from")
    ap.add_argument("--read-results", action="store_true", help="read the association's "
                    "2024 results PDF into ar/data/source/ (needs pdfplumber)")
    ap.add_argument("--results-pdf", help="with --read-results: a saved copy of the PDF")
    args = ap.parse_args()

    if args.read_results:
        today = datetime.date.today().isoformat()
        if args.results_pdf:
            with open(args.results_pdf, "rb") as f:
                body = f.read()
        else:
            body = Fetcher(None).get_bytes(RESULTS_URL)
        snap = read_results(body, today)
        if os.path.exists(RESULTS_FILE):
            with open(RESULTS_FILE, encoding="utf-8") as f:
                old = json.load(f)
            if old.get("sha256") != snap["sha256"]:
                print("build-ar-county-officials: the results PDF differs from the copy "
                      "last read (%s); review the diff before committing"
                      % old.get("read"))
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(snap, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print("wrote %s: %d counties, %d districts, updated %s"
              % (os.path.relpath(RESULTS_FILE), len(snap["counties"]),
                 sum(len(v) for v in snap["counties"].values()), snap["updated"]))
        return

    if args.check:
        with open(OUT_FILE, encoding="utf-8") as f:
            doc = json.load(f)
        problems = check_shipped(doc)
        if problems:
            for p in problems:
                print("build-ar-county-officials: FAIL: " + p)
            raise SystemExit(1)
        print("build-ar-county-officials --check: OK — " + summary(doc))
        return

    today = datetime.date.today().isoformat()
    doc, addresses = build(Fetcher(args.cache), today)
    problems = check_shipped(doc)
    if problems:
        for p in problems:
            print("build-ar-county-officials: FAIL: " + p)
        raise SystemExit(1)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    print("wrote ar/data/app/%s: %d judges with an office both publishers agree on; %s"
          % (os.path.basename(OUT_FILE), addresses, summary(doc)))


if __name__ == "__main__":
    main()
