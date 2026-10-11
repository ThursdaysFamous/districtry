#!/usr/bin/env python3
"""South Carolina's county council members, from the State Election
Commission's certified results, every name dated to the election that seated
it — and each county's own council page read beside them.

WHAT THIS PUBLISHES AND WHAT IT DOES NOT. The State Election Commission runs
every county council election and publishes the results of each general
election through its results site (www.enr-scvotes.org), one summary file per
county. South Carolina elects county council members to staggered four-year
terms (two-year in Anderson and Edgefield), so the 2022 and 2024 generals,
with their recounts and runoffs, between them name a winner for every seat. A
winner is a fact with a date on it. It is NOT a statement of who holds the seat
today: a member who has resigned, died, or been replaced since still shows here
as the person who won. So every record names its election, and the card says
so in words — Minnesota's posture (mn/scripts/build_mn_commissioner_roster.py),
which Adam opened for certified returns on 2026-09-22.

THE SEATS ARE NOT ALL DISTRICTS, AND `COUNTYWIDE` AND `MULTI_MEMBER` SAY WHICH.
Measured on the 2022 and 2024 results (2026-10-11): six counties elect a council
chair by the whole county (Aiken, Clarendon, Horry, Kershaw, Saluda,
Spartanburg) and three a county supervisor (Berkeley, Union, Williamsburg);
Chester, Colleton and Jasper elect one member at large; Hampton elects all five
at large; Jasper's other four are elected by the whole county from four
townships; and three districts elect two members in alternate cycles
(Clarendon 2, Colleton 23 and 45). Every other seat is one member for one
district the state's council map draws.

HOW A SEAT IS FILLED. Within one election cycle, a recount or a runoff of a
contest REPLACES that contest (Hampton's 2022 at-large seats come from the
recount). Across cycles the newest contest for a seat comes first and older
ones fill whatever seats are left, so a two-member district takes one winner
from each cycle and Hampton takes two from 2024 and three from 2022. A contest
that would fill only part of what is left fails the build, because that is a
seat table that no longer describes the county. Within one cycle a full-term
contest comes before an unexpired-term one for the same seat, and an
unexpired-term contest that no longer fits is skipped, since the term it
filled ends when the full term begins.

FOUR WAYS A CONTEST IS NOT A WINNER. (1) Not yet canvassed: a contest counts
only once CANVASS_DAYS have passed since its election day. (2) A write-in wins:
the results name every write-in vote as "Write-In", so that seat names nobody
and the record says why. (3) A tie at the last winning place: nobody is named
for it. (4) A contest whose only choices are Yes and No is a referendum
(Clarendon's 2022 vote on its council's composition) and is not read.

NEW ELECTIONS ARE FOUND ON THE COMMISSION'S OWN RESULTS PAGE. `ELECTIONS` pins
the six this file was written against; every run also reads the Commission's
results page for general-election links from FIRST_CYCLE on and uses any new
one once it is canvassed, so the 3 November 2026 results enter the weekly
rebuild without an edit here. A general that is more than OVERDUE_DAYS past
with no link on that page fails the build rather than going on naming the
previous members as though nothing had happened.

ONE BLIND SPOT IS KNOWN AND STATED. A county special election held between
generals is run by the county, and the Commission's results page lists state
offices' specials only (its special-election results category, read
2026-10-11, names state House and Senate seats and none of a county's). Such a
seat shows its last general's winner. The county pages below are what catch it.

A SECOND PUBLISHER CHECKS THE FIRST. `COUNTY_PAGES` names each county's own
council page. Every run reads each page it can (robots.txt read at every
redirect hop), and checks that every winner's surname appears on it. Read here
on 2026-10-11, eleven seats are not the winner on the county's page (one of
them names the winner as a former member), and `COUNTY_SAYS` records each by
hand with what the county says and the date it was read; the record carries it
as `countySays` and the card prints both, each saying whose it is. The results
winner is not overwritten: the county page is the newer fact and the results
the certified one, and a reader should see that they disagree. A NEW
disagreement with no entry fails the build, and so does an entry that has
stopped describing the page (its name gone, or the winner's surname back), so
the table cannot rot in either direction. A winner elected within
WITNESS_GRACE_DAYS is not held to the page, because a new member takes office
in January and the county's page follows after.

THE RESULTS SITE CHALLENGES GITHUB'S RUNNERS, SO THE WEEKLY JOB OFTEN CANNOT
REBUILD AND MUST NOT GO QUIET ABOUT IT. Measured 2026-10-11: from this
project's build sandbox www.enr-scvotes.org answers robots.txt with 404 (allow
all) and every results file with 200, while from a GitHub runner its robots.txt
answers HTTP 202, an access control, on 2 of 2 runs, so the scheduled job may
not fetch a single result there. A refusal or a failed read on the results site
is therefore not a crash. The run keeps the shipped roster exactly as it is,
reads every county page against it (the witness below runs in full), and exits
EX_RESULTS_UNREADABLE (75), which the workflow reports on a tracking issue
rather than as a red run. What stops that becoming a job that never refreshes
anything is `owed()`: once a cycle's general is CANVASS_DAYS past and the
Commission's results page links an election of that cycle that `ELECTIONS`
does not pin, a run that cannot read it FAILS, naming the election, because
from then on the shipped names are owed a refresh nobody has done. Between
elections the certified results do not change, so not reading them costs
nothing. Whoever rebuilds after an election adds its ids to `ELECTIONS` in the
same change. How that rebuild is done while the runners are refused is a
question for the operator, recorded in sc/WATCH.md.

What the witness cannot see: it matches SURNAMES, so a page naming a different
person with the winner's surname reads as agreement; and a county whose page
cannot be read in a run is printed, not failed, so one unreachable page does
not stop 45 counties' refresh.

THE PAGES PRINT HOME ADDRESSES AND THIS NEVER READS THEM. Several county pages
(Union's, Clarendon's, Dillon's) print each member's home address beside the
name. The witness looks for surnames in the page's text and keeps nothing else.

Usage:
    python3 sc/scripts/build_sc_county_council_roster.py          # fetch and write
    python3 sc/scripts/build_sc_county_council_roster.py --check  # offline gate
"""

import argparse
import datetime
import gzip
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(os.path.dirname(INSTANCE), "scripts"))

from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

APP_DATA = os.path.join(INSTANCE, "data", "app")
DISTRICTS_FILE = os.path.join(APP_DATA, "sc-county-council-districts.json")
OUT_FILE = os.path.join(APP_DATA, "sc-county-council-members.json")

USER_AGENT = "districtry/1.0 (+https://districtry.com/sc/)"
RESULTS_HOST = "https://www.enr-scvotes.org"
RESULTS_PAGE = "https://scvotes.gov/elections-statistics/election-results/"
REQUEST_TIMEOUT = 60
PACE_SECONDS = 0.5
EX_RESULTS_UNREADABLE = 75

FIRST_CYCLE = 2022
CANVASS_DAYS = 21
OVERDUE_DAYS = 45
WITNESS_GRACE_DAYS = 100

# The elections this file was written against, as the Commission's results
# page links them (read 2026-10-11). `kind` orders contests within a cycle.
ELECTIONS = [
    {"id": "115412", "cycle": 2022, "kind": "general"},
    {"id": "116259", "cycle": 2022, "kind": "recount"},
    {"id": "116307", "cycle": 2022, "kind": "runoff"},
    {"id": "122436", "cycle": 2024, "kind": "general"},
    {"id": "122917", "cycle": 2024, "kind": "recount"},
    {"id": "122966", "cycle": 2024, "kind": "runoff"},
]
KIND_ORDER = {"general": 0, "recount": 1, "runoff": 2}

# Seats elected by the whole county: (kind, label, number of seats).
COUNTYWIDE = {
    "Aiken": [("chair", "", 1)],
    "Clarendon": [("chair", "", 1)],
    "Horry": [("chair", "", 1)],
    "Kershaw": [("chair", "", 1)],
    "Saluda": [("chair", "", 1)],
    "Spartanburg": [("chair", "", 1)],
    "Berkeley": [("supervisor", "", 1)],
    "Union": [("supervisor", "", 1)],
    "Williamsburg": [("supervisor", "", 1)],
    "Chester": [("at-large", "", 1)],
    "Colleton": [("at-large", "", 1)],
    "Hampton": [("at-large", "", 5)],
    "Jasper": [("at-large", "", 1), ("township", "Coosawhatchie", 1),
               ("township", "Hardeeville", 1), ("township", "Pocotaligo", 1),
               ("township", "Robertville", 1)],
}
# Districts that elect two members, one in each cycle.
MULTI_MEMBER = {("Clarendon", "2"): 2, ("Colleton", "23"): 2, ("Colleton", "45"): 2}
# Counties whose map features are not election districts (the district
# builder's FORMS): their seats are all in COUNTYWIDE.
NO_DISTRICT_SEATS = {"Hampton", "Jasper"}

EXPECT_SEATS = 334
# Seats the results name nobody for, with the reason. An entry that becomes
# named, or a new unnamed seat with no entry, fails the build.
KNOWN_UNNAMED = {}
MIN_NAMED = EXPECT_SEATS - len(KNOWN_UNNAMED)

PARTY_NAMES = {"REP": "Republican", "DEM": "Democratic", "LIB": "Libertarian",
               "CON": "Constitution", "GRN": "Green", "WFM": "Working Families",
               "ALN": "Alliance", "UNC": "United Citizens",
               "PET": "Petition candidate"}

# Each county's own council page. A list is read as one page (Union's
# supervisor has a page of his own). A (url, reason) pair is a page the card
# links and this builder does not read, and why — linking is not crawling.
# The state's council map carries a page link per county, and four of them
# had moved when read on 2026-10-11 (Richland, Lancaster, Jasper, Marlboro);
# Laurens's points at laurenscounty.us, a domain that now redirects to two
# unrelated businesses, where the county is at laurenscountysc.gov. Aiken's
# first link here answered a 404 page, and Spartanburg's and York's moved from
# .org and .com to .gov (all three read 2026-10-11). The first url in a list is
# the one the card links.
COUNTY_PAGES = {
    "Abbeville": ["https://abbevillecountysc.com/county-council/"],
    "Aiken": ["https://www.aikencountysc.gov/529/Council-Members"],
    "Allendale": ("https://www.allendalecounty.com/government/county_government/"
                  "city_council_members.php",
                  "the county's robots.txt disallows every path for every "
                  "client (read 2026-10-11)"),
    "Anderson": ["https://www.andersoncountysc.org/county-council/"],
    "Bamberg": ["https://www.bambergcounty.sc.gov/county-council-and-staff-directory"],
    "Barnwell": ["https://barnwellcountysc.us/173/Council"],
    "Beaufort": ["https://www.beaufortcountysc.gov/council/council-members/index.html"],
    "Berkeley": ("https://berkeleycountysc.gov/dept/council/elected-officials/",
                 "the county's site answers every request from this project "
                 "with a managed challenge (read 2026-10-11), which is an "
                 "access control and is not worked around"),
    "Calhoun": ["https://calhouncounty.sc.gov/officials"],
    "Charleston": ["https://www.charlestoncounty.org/departments/county-council/index.php"],
    "Cherokee": ["https://cherokeecountysc.gov/county-council-administration/"],
    "Chester": ["https://chestercountysc.gov/government/chester-county-council/county-council-members/"],
    "Chesterfield": ["https://www.chesterfieldcountysc.com/countycouncil"],
    "Clarendon": ["https://www.clarendoncountysc.gov/our-government/council/"],
    "Colleton": ["https://www.colletoncounty.org/county-council"],
    "Darlington": ["https://www.darcosc.com/government/county_council/index.php"],
    "Dillon": ["https://www.dilloncountysc.org/government/county_council/index.php"],
    "Dorchester": ["https://www.dorchestercountysc.gov/government/county-council/council-members"],
    "Edgefield": ["https://edgefieldcounty.sc.gov/county-council/"],
    "Fairfield": ["https://www.fairfieldsc.com/departments/county-council"],
    "Florence": ["https://florenceco.org/council"],
    "Georgetown": ["https://www.gtcounty.org/291/County-Council"],
    "Greenville": ["https://www.greenvillecounty.org/Council/ContactInfo.aspx"],
    "Greenwood": ["https://www.greenwoodcounty-sc.gov/county-council"],
    "Hampton": ["https://www.hamptoncountysc.org/2/County-Council"],
    "Horry": ["https://www.horrycountysc.gov/county-council/"],
    "Jasper": ["https://www.jaspercountysc.gov/government/council/"],
    "Kershaw": ["https://www.kershaw.sc.gov/our-county"],
    "Lancaster": ["https://www.lancastercountysc.gov/351/Lancaster-County-Council"],
    "Laurens": ["https://www.laurenscountysc.gov/departments/county_council/index.php"],
    "Lee": ["https://www.leecountysc.org/county_council/council_members.php"],
    "Lexington": ["https://lex-co.sc.gov/county-council/council-members"],
    "Marion": ["https://www.marionsc.org/government/county_council/index.php"],
    "Marlboro": ["https://marlborocounty.sc.gov/government_/council.php"],
    "McCormick": ["https://www.mccormickcountysc.org/government/county_council.php"],
    "Newberry": ["https://www.newberrycounty.net/county-council"],
    "Oconee": ["https://oconeesc.com/council-home/council-officials"],
    "Orangeburg": ["https://www.orangeburgcounty.org/288/County-Council"],
    "Pickens": ["https://www.co.pickens.sc.us/government/county_council/index.php"],
    "Richland": ["https://www.richlandcountysc.gov/Government/Elected-Offices/County-Council"],
    "Saluda": ["https://saludacounty.sc.gov/county-council"],
    # The council page names the chairman only; each district has a page.
    "Spartanburg": ["https://www.spartanburgcounty.gov/189/County-Council",
                    "https://www.spartanburgcounty.gov/194/Council-Chairman",
                    "https://www.spartanburgcounty.gov/196/District-1",
                    "https://www.spartanburgcounty.gov/197/District-2",
                    "https://www.spartanburgcounty.gov/198/District-3",
                    "https://www.spartanburgcounty.gov/199/District-4",
                    "https://www.spartanburgcounty.gov/200/District-5",
                    "https://www.spartanburgcounty.gov/201/District-6"],
    "Sumter": ["https://www.sumtercountysc.org/our_council/council_members/index.php"],
    "Union": ["https://gearupunionsc.com/officials/union-county-council/",
              "https://gearupunionsc.com/officials/union-county-supervisor/"],
    "Williamsburg": ["https://www.williamsburgcounty.sc.gov/184/County-Council"],
    "York": ["https://www.yorkcountysc.gov/375/County-Council"],
}

# Counties whose page no person has read, so a winner it does not name is
# PRINTED rather than failed: a first reading from the runner must not turn
# the job red on a disagreement nobody has looked at. Settle one and remove it;
# an entry for a county whose page names every winner fails.
#
# Charleston is the one left. Its site answers this project with its own block
# page from this sandbox and from GitHub's runner, for this project's client
# and for a browser's alike (read 2026-10-11), so the refusal is about the
# address and no client changes it.
#
# The other seven were read by a person on 2026-10-11. Aiken, Kershaw,
# Orangeburg and York name every winner; Chesterfield, Dorchester and
# Spartanburg differ on five seats, each now in COUNTY_SAYS below. Six of
# them refuse THIS PROJECT'S OWN CLIENT at the page itself, from the sandbox
# and from the runner alike: Aiken, Orangeburg,
# Spartanburg and York answer HTTP 403 with Cloudflare's "Attention Required!"
# block page, and Dorchester and Kershaw answer HTTP 403 with Akamai's "Access
# Denied". Each served its page to the standard library with
# scraper_common.UA_CHROME_WIN_126 and UA_HINTS_CHROME_126, robots.txt read
# with that same client first (no rule matches any path read), and that is how
# the person read them. This builder still sends its own token to all six, so
# the weekly job prints them unreadable and re-checks their COUNTY_SAYS
# entries only on a run where they answer it; switching those hosts to the
# browser client is a separate change, because it must first be measured from
# the runner and recorded in the fleet's user-agent measurements. Chesterfield
# was refused only by a rate limit here and is read by the runner.
UNREAD_BY_A_PERSON = {"Charleston"}

# Seats where the county's own page does not name the certified winner, each
# read by hand: the page names someone else ("name"), calls the seat vacant
# ("vacant"), lists the other members and not this one ("notListed"), or
# names the winner as a former member ("former"). Re-verified every run the
# page can be read: for the first three the winner's surname must still be
# absent and a name the county gives must still be present; for "former" the
# page's own words saying so (`phrase`) must still be on it, word for word,
# because a surname alone can be somebody else's (Spartanburg's council page
# names a clerk Walker). All
# eleven read 2026-10-11 from the page in COUNTY_PAGES. Two are explained by
# events the results this builder reads cannot show: Spartanburg District 3
# by a special election in November 2025 and District 5 by a resignation in
# August 2026, both as local news reported them. The other nine are not
# explained by anything this builder can see.
COUNTY_SAYS = {
    # "LaSean Tutt ... serving as the elected District 2 Councilwoman", term
    # expiring 2026; the 2022 general's District 2 winner is Christine W Long.
    "Abbeville|District 2": {"winner": "Christine W Long", "name": "LaSean Tutt",
                             "read": "2026-10-11"},
    # "County Council District 2 VACANT".
    "Cherokee|District 2": {"winner": "Bill Blanton", "vacant": True,
                            "read": "2026-10-11"},
    "Cherokee|District 7": {"winner": "Tracy A McDaniel", "name": "Peter M. Wilkins",
                            "read": "2026-10-11"},
    # "District 2 Roy Brunson ... Term Expires December 2026".
    "Chester|District 2": {"winner": "Mike Vaughn", "name": "Roy Brunson",
                           "read": "2026-10-11"},
    # The page links four members (Hollingsworth, Darrin Williams, Jinks,
    # Love) for a council of five, and not the 2022 at-large winner.
    "Hampton|at large": {"winner": "Camille Mixson Welch", "notListed": True,
                         "read": "2026-10-11"},
    # "Ceccarelli, Gene Council Member Coosawhatchie Township".
    "Jasper|Coosawhatchie township": {"winner": "Martin Sauls IV",
                                      "name": "Gene Ceccarelli", "read": "2026-10-11"},
    # "Dr. Lawrance Brand District 2 Term Expires: December 31, 2026".
    "Chesterfield|District 2": {"winner": "Gerald Miller", "name": "Lawrance Brand",
                                "read": "2026-10-11"},
    # "District 1: Peter Smith Jr." and "District 6: Frankie Staropoli", in the
    # page's own list and again in its contact table.
    "Dorchester|District 1": {"winner": "Harriet Holman", "name": "Peter Smith Jr.",
                              "read": "2026-10-11"},
    "Dorchester|District 6": {"winner": "Bill Hearn", "name": "Frankie Staropoli",
                              "read": "2026-10-11"},
    # The District 3 page names "Paul D. Abbott, Jr.", "Term Expires:
    # 01/01/2029", the term the 2024 winner was elected to. Local news reports
    # David Britt resigned in May 2025 and Abbott won a special election for
    # the rest of the term that November; this builder reads no special
    # elections, so the page is what records it.
    "Spartanburg|District 3": {"winner": "David Britt", "name": "Paul D. Abbott, Jr.",
                               "read": "2026-10-11"},
    # The District 5 page: "Bob Walker (Retired) Former Spartanburg County
    # Council Member". Local news reports he resigned in August 2026 and that
    # the governor left the seat to the 3 November election.
    "Spartanburg|District 5": {"winner": "Bob Walker", "former": True,
                               "phrase": "Bob Walker (Retired) Former",
                               "read": "2026-10-11"},
}


def fail(msg):
    raise SystemExit("build-sc-county-council-roster: FATAL: %s" % msg)


# ---------- the shipped map ----------
def counties_from_geometry():
    """county -> (fips, form, [district ids]) from the shipped council map, so
    the roster can never name a district the map does not draw."""
    with open(DISTRICTS_FILE, encoding="utf-8") as f:
        feats = json.load(f)["features"]
    out = {}
    for feat in feats:
        p = feat["properties"]
        fips, form, dists = out.setdefault(p["county"], (p["countyFips"], p["form"], []))
        dists.append(p["district"])
    if len(out) != 46:
        fail("the shipped council map holds %d counties, expected 46" % len(out))
    return out


def seat_groups(geo):
    """county -> {(kind, label): seats}, the whole seat table."""
    groups = {}
    for county, (_, form, dists) in geo.items():
        g = {}
        if county not in NO_DISTRICT_SEATS:
            if form != "district":
                fail("%s's map features are %r, and it has district seats" % (county, form))
            for d in dists:
                g[("district", d)] = MULTI_MEMBER.get((county, d), 1)
        elif form == "district":
            fail("%s is listed as having no district seats and its map draws districts" % county)
        for kind, label, n in COUNTYWIDE.get(county, []):
            g[(kind, label)] = n
        groups[county] = g
    for (county, d) in MULTI_MEMBER:
        if ("district", d) not in groups.get(county, {}):
            fail("MULTI_MEMBER names %s District %s, which the map does not draw" % (county, d))
    total = sum(sum(g.values()) for g in groups.values())
    if total != EXPECT_SEATS:
        fail("the seat table holds %d seats, expected %d" % (total, EXPECT_SEATS))
    return groups


# ---------- fetch ----------
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _get(url):
    """(status, final url, text) for one request with this project's own
    client, the standard library's. robots.txt is read before every hop of a
    redirect, so a redirect cannot carry a fetch to a host that refuses it.
    The standard library rather than `requests` because Chester County's
    server refuses `requests` and serves this client (measured 2026-10-11)."""
    for _ in range(6):
        require_robots_once(url, USER_AGENT, label="sc-council-roster")
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                   "Accept-Encoding": "gzip"})
        try:
            with _OPENER.open(req, timeout=REQUEST_TIMEOUT) as resp:
                status, body = resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308) and exc.headers.get("Location"):
                url = urllib.parse.urljoin(url, exc.headers["Location"])
                continue
            raise
        time.sleep(PACE_SECONDS)
        if body[:2] == b"\x1f\x8b":  # the results site sends gzip unasked
            body = gzip.decompress(body)
        return status, url, body.decode("utf-8", "replace")
    raise RuntimeError("more than six redirects from %s" % url)


def get_text(url):
    return _get(url)[2]


class ResultsUnreadable(Exception):
    """The results site refused this client or could not be read this run."""


def results_text(url):
    """get_text for the results site, where a robots refusal, a network
    failure or anything but a 200 is ResultsUnreadable rather than a crash: a
    challenge page read as JSON would otherwise surface as a parse error."""
    try:
        status, _, text = _get(url)
    except SystemExit as exc:  # require_robots_once refuses by raising it
        # It prints the refusal itself and raises with a bare exit status, so
        # str(exc) would be "1"; only a message raised with one is worth keeping.
        raise ResultsUnreadable(exc.code if isinstance(exc.code, str) else
                                "robots.txt refused this client (the reason is "
                                "printed above)")
    except (OSError, RuntimeError) as exc:
        raise ResultsUnreadable("%s: %s" % (type(exc).__name__, exc))
    if status != 200:
        raise ResultsUnreadable("%s answered HTTP %d" % (url, status))
    return text


def general_day(year):
    """The general election's date in an even year: the Tuesday after the
    first Monday in November."""
    nov1 = datetime.date(year, 11, 1)
    day = nov1 + datetime.timedelta(days=(1 - nov1.weekday()) % 7)
    if day == nov1:  # the Tuesday after the first MONDAY
        day += datetime.timedelta(days=7)
    return day


def owed(found, today):
    """Problems for each election the results page links that `ELECTIONS`
    does not pin, once its cycle's general is CANVASS_DAYS past. Asked only
    when the results site could not be read, because a run that reads it takes
    the new election itself."""
    pinned = {e["id"] for e in ELECTIONS}
    out = []
    for eid, meta in sorted(found.items()):
        age = (today - general_day(meta["cycle"])).days
        if eid not in pinned and age >= CANVASS_DAYS:
            out.append("the results page links the %d %s (election %s), %d days after "
                       "that general, and this run could not read the results site, "
                       "so the shipped names are owed a refresh — rebuild and add it to "
                       "ELECTIONS (sc/WATCH.md says how)"
                       % (meta["cycle"], meta["kind"], eid, age))
    return out


def discover(today):
    """General-election links on the Commission's results page from
    FIRST_CYCLE on, as {id: {cycle, kind}}; and fail on an overdue general."""
    page = get_text(RESULTS_PAGE)
    found = {}
    for m in re.finditer(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', page, re.S | re.I):
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", m.group(2)))).strip()
        t = re.match(r"^(20\d\d) (?:Statewide )?General Elections?"
                     r"(?:\s*-\s*|\s+)?(Recounts?|Runoffs?)?$", text, re.I)
        if not t or int(t.group(1)) < FIRST_CYCLE:
            continue
        href = urllib.parse.unquote(html.unescape(m.group(1)))
        idm = re.search(r"enr-scvotes\.org/SC/(\d+)/", href)
        if not idm:
            fail("the results page links %r to %r, which is not a results-site "
                 "election" % (text, href))
        kind = (t.group(2) or "").strip().lower().rstrip("s") or "general"
        found[idm.group(1)] = {"cycle": int(t.group(1)), "kind": kind}
    if not found:
        fail("the results page carries no general-election link at all — its "
             "layout changed, and this builder cannot see new elections")
    for year in range(2026, today.year + 1, 2):
        day = general_day(year)
        if (today - day).days > OVERDUE_DAYS and not any(
                e["cycle"] == year and e["kind"] == "general" for e in found.values()):
            fail("the %d general (%s) is %d days past and the results page links "
                 "no results for it" % (year, day, (today - day).days))
    return found


def fetch_election(eid):
    """(settings, {county: (summary rows, county results url)})."""
    ver = results_text("%s/SC/%s/current_ver.txt" % (RESULTS_HOST, eid)).strip()
    settings = json.loads(results_text(
        "%s/SC/%s/%s/json/en/electionsettings.json" % (RESULTS_HOST, eid, ver)))
    details = settings["settings"]["electiondetails"]
    out = {}
    for row in details.get("participatingcounties") or []:
        name, ceid, cver = row.split("|")[:3]
        url = "%s/SC/%s/%s/%s/json/en/summary.json" % (RESULTS_HOST, name, ceid, cver)
        out[name] = (json.loads(results_text(url)),
                     "%s/SC/%s/%s/" % (RESULTS_HOST, name, ceid))
    return details, out


# ---------- contests ----------
PREFIX = r"^(?:[A-Za-z'.]+ )?County "
DIST_RE = re.compile(PREFIX + r"Council\s+Dis\w*\s+(\d+)$", re.I)
TWP_RE = re.compile(PREFIX + r"Council\s+(.+?) Township$", re.I)
AL_RE = re.compile(PREFIX + r"Council\s+At[ -]Large$", re.I)
CHAIR_RE = re.compile(PREFIX + r"Council Chair(?:man)?$", re.I)
SUP_RE = re.compile(PREFIX + r"Supervisor$", re.I)
UNEXPIRED_RE = re.compile(r"\s*\(Unexpired Term\)$", re.I)
COUNCIL_WORDS = re.compile(r"county council|county supervisor", re.I)


def classify(name):
    """(kind, label, unexpired) for a council contest, or None. Measured on
    the 2022 and 2024 results: "County Council District 4" (and the misspelt
    "Disrict" and "Distric", once each), "Hampton County Council At Large",
    "County Council Coosawhatchie Township", "County Council Chair", "County
    Supervisor", each sometimes ending "(Unexpired Term)"."""
    unexpired = bool(UNEXPIRED_RE.search(name))
    core = UNEXPIRED_RE.sub("", name).strip()
    for rx, kind in ((DIST_RE, "district"), (TWP_RE, "township"),
                     (AL_RE, "at-large"), (CHAIR_RE, "chair"), (SUP_RE, "supervisor")):
        m = rx.match(core)
        if m:
            return kind, (m.group(1) if m.groups() else ""), unexpired
    return None


def contests(elections, groups, today):
    """Every council contest that counts, as dicts; and the held ones."""
    found, held = [], []
    day = {e["id"]: datetime.datetime.strptime(e["details"]["electiondate"], "%m/%d/%Y").date()
           for e in elections}
    general = {e["cycle"]: day[e["id"]] for e in elections if e["kind"] == "general"}
    for e in elections:
        # A recount counts the general's ballots again, so its winners were
        # elected on the general's day; a runoff is a vote of its own.
        date = general[e["cycle"]] if e["kind"] == "recount" else day[e["id"]]
        for county, (rows, url) in sorted(e["counties"].items()):
            county = "McCormick" if county.lower() == "mccormick" else county
            for row in rows:
                name = row["C"].strip()
                choices = [c.strip() for c in row["CH"]]
                if set(c.lower() for c in choices) <= {"yes", "no"}:
                    continue
                k = classify(name)
                if k is None:
                    if COUNCIL_WORDS.search(name) and not re.search(r"\b(city|town)\b", name, re.I):
                        fail("%s %s: a council contest this builder cannot place: %r"
                             % (e["id"], county, name))
                    continue
                kind, label, unexpired = k
                if county not in groups or (kind, label) not in groups[county]:
                    fail("%s %s: %r is a seat the seat table does not hold"
                         % (e["id"], county, name))
                c = {"election": e, "date": date, "county": county,
                     "group": (kind, label), "unexpired": unexpired, "contest": name,
                     "vf": int(row["VF"]), "url": url,
                     "candidates": list(zip(choices, row["P"], [int(v) for v in row["V"]]))}
                if (today - date).days < CANVASS_DAYS:
                    held.append((c, "not yet canvassed (%d days old)" % (today - date).days))
                    continue
                found.append(c)
    return found, held


def final_contests(all_contests):
    """A recount or runoff replaces the contest for the same seat in the same
    cycle. Matched by seat, not by contest name: Hampton's 2022 general names
    its contest "County Council At Large" and the recount of it "Hampton County
    Council At Large"."""
    best = {}
    for c in all_contests:
        e = c["election"]
        k = (c["county"], e["cycle"], c["group"], c["unexpired"])
        prev = best.get(k)
        if prev is not None and KIND_ORDER[e["kind"]] == KIND_ORDER[prev["election"]["kind"]]:
            fail("%s %d: two %s contests for the same seat (%r, %r)"
                 % (c["county"], e["cycle"], e["kind"], prev["contest"], c["contest"]))
        if prev is None or KIND_ORDER[e["kind"]] > KIND_ORDER[prev["election"]["kind"]]:
            if prev is not None and c["vf"] < prev["vf"]:
                fail("%s %s: the %s fills %d seats and replaces a contest that filled %d"
                     % (c["county"], c["contest"], e["kind"], c["vf"], prev["vf"]))
            best[k] = c
    return list(best.values())


def winners(c):
    """[(name or None, party, why)] for the contest's VF winning places."""
    ranked = sorted(c["candidates"], key=lambda x: -x[2])
    vf = c["vf"]
    first_loser = ranked[vf][2] if len(ranked) > vf else None
    out = []
    for name, party, votes in ranked[:vf]:
        if votes == first_loser:
            out.append((None, None, "the published result is a tie for this place"))
        elif name.lower() == "write-in":
            out.append((None, None, "the seat was won by write-in votes, which the "
                                    "results do not name"))
        else:
            if party and name.startswith(party + " "):
                name = name[len(party) + 1:].strip()
            out.append((name, PARTY_NAMES.get(party, party) if party else None, None))
    return out


def fill(groups, chosen):
    """county -> [seat records], filled newest contest first."""
    by_group = {}
    for c in chosen:
        by_group.setdefault((c["county"], c["group"]), []).append(c)
    roster = {}
    for county, g in groups.items():
        seats = []
        for group, n in sorted(g.items(), key=lambda kv: _group_order(kv[0])):
            cs = sorted(by_group.get((county, group), []),
                        key=lambda c: (-c["election"]["cycle"], c["unexpired"], c["contest"]))
            left, full_cycle = n, None
            for c in cs:
                w = winners(c)
                if left == 0:
                    break
                if len(w) > left:
                    if c["unexpired"] and full_cycle == c["election"]["cycle"]:
                        print("  skipped: %s %s %s — an unexpired term ending when the "
                              "full term elected beside it begins"
                              % (c["date"], county, c["contest"]))
                        continue
                    fail("%s %s: %s fills %d seats and only %d are left"
                         % (county, _label(group), c["contest"], len(w), left))
                if not c["unexpired"]:
                    full_cycle = c["election"]["cycle"]
                for name, party, why in w:
                    rec = {"seat": group[0], "election": c["date"].isoformat(),
                           "electionName": "%d general election%s" % (
                               c["election"]["cycle"],
                               {"general": "", "recount": ", after a recount",
                                "runoff": " runoff"}[c["election"]["kind"]]),
                           "sourceUrl": c["url"]}
                    if group[0] == "district":
                        rec["district"] = group[1]
                    if group[0] == "township":
                        rec["township"] = group[1]
                    if c["unexpired"]:
                        rec["unexpiredTerm"] = True
                    if name:
                        rec["name"] = name
                        if party:
                            rec["party"] = party
                    else:
                        rec["unnamed"] = why
                    seats.append(rec)
                left -= len(w)
            if left:
                label = "%s|%s" % (county, _label(group))
                why = KNOWN_UNNAMED.get(label)
                if why is None:
                    fail("%s %s: %d seat(s) no contest fills and no KNOWN_UNNAMED entry"
                         % (county, _label(group), left))
                for _ in range(left):
                    rec = {"seat": group[0], "unnamed": why}
                    if group[0] == "district":
                        rec["district"] = group[1]
                    if group[0] == "township":
                        rec["township"] = group[1]
                    seats.append(rec)
        roster[county] = seats
    return roster


def _group_order(group):
    kind, label = group
    rank = {"chair": 0, "supervisor": 0, "at-large": 1, "township": 2, "district": 3}[kind]
    return (rank, int(label) if label.isdigit() else 0, label)


def _label(group):
    kind, label = group
    if kind == "district":
        return "District %s" % label
    if kind == "township":
        return "%s township" % label
    return {"at-large": "at large", "chair": "chair", "supervisor": "supervisor"}[kind]


def seat_label(rec):
    return _label((rec["seat"], rec.get("district") or rec.get("township") or ""))


# ---------- the county pages ----------
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def _fold(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch)).lower()


def surname_parts(name):
    toks = [t for t in re.sub(r"[.,]", " ", name).split() if _fold(t) not in SUFFIXES]
    return [p for p in re.split(r"[-\s]", _fold(toks[-1])) if p] if toks else []


def page_tokens(text):
    """The page's visible text plus image alt and title text, as a list of
    folded words in page order. Nothing else is kept."""
    alts = " ".join(re.findall(r'\b(?:alt|title)="([^"]*)"', text, re.I))
    # Greenville writes each member's name into the page from an inline script
    # (`var contact = " Joey Russo"`, to hide the e-mail address from
    # harvesters), so the name is in the page as published but not in its text.
    alts += " " + " ".join(re.findall(r'\bvar\s+contact\s*=\s*"([^"]*)"', text))
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", text)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)) + " " + html.unescape(alts)
    return re.findall(r"[a-z]+", _fold(t).replace("'", "").replace("’", ""))


def page_words(text):
    return set(page_tokens(text))


def has_phrase(token_lists, phrase):
    """Whether the folded words of `phrase` appear consecutively on a page."""
    want = page_tokens(phrase)
    n = len(want)
    return bool(n) and any(toks[i:i + n] == want for toks in token_lists
                           for i in range(len(toks) - n + 1))


def witness(roster, today):
    """Hold every winner to the county's own page. Returns the problems."""
    problems, read, agree, unsettled = [], [], 0, set()
    for county in sorted(roster):
        entry = COUNTY_PAGES[county]
        if isinstance(entry, tuple):
            print("  county page %s: not read — %s" % (county, entry[1]))
            continue
        try:
            words, tokens = set(), []
            for url in entry:
                tokens.append(page_tokens(get_text(url)))
                words |= set(tokens[-1])
        except BaseException as exc:  # a robots refusal raises SystemExit
            if isinstance(exc, KeyboardInterrupt):
                raise
            print("  county page %s: unreadable this run (%s: %s)"
                  % (county, type(exc).__name__, str(exc)[:160]))
            continue
        named = [r for r in roster[county] if r.get("name")]
        if not any(p in words for r in named for p in surname_parts(r["name"])):
            # A block page, a page that moved, or one that lists nobody: none of
            # them is a statement about any member, so the county is not held.
            print("  county page %s: names none of the county's winners — read "
                  "as unreadable this run" % county)
            continue
        read.append(county)
        for rec in named:
            label = "%s|%s" % (county, seat_label(rec))
            present = any(p in words for p in surname_parts(rec["name"]))
            says = COUNTY_SAYS.get(label)
            if says and says.get("winner") == rec["name"]:
                if says.get("former"):
                    if not has_phrase(tokens, says["phrase"]):
                        problems.append("COUNTY_SAYS %s no longer describes the county's "
                                        "page (%r is gone from it) — re-read it"
                                        % (label, says["phrase"]))
                    continue
                theirs = (surname_parts(says["name"]) if says.get("name")
                          else ["vacant"] if says.get("vacant") else [])
                if present or (theirs and not any(p in words for p in theirs)):
                    problems.append("COUNTY_SAYS %s no longer describes the county's page "
                                    "(winner's surname %s%s) — re-read it"
                                    % (label, "back" if present else "absent",
                                       ", county's name gone" if theirs and not any(
                                           p in words for p in theirs) else ""))
                continue
            if present:
                agree += 1
                continue
            age = (today - datetime.date.fromisoformat(rec["election"])).days
            if age < WITNESS_GRACE_DAYS:
                print("  county page %s: %s %s not listed yet (elected %d days ago)"
                      % (county, seat_label(rec), rec["name"], age))
            elif county in UNREAD_BY_A_PERSON:
                unsettled.add(county)
                print("  county page %s: %s — the page does not name %s; this county's "
                      "page has not been read by a person, so settle it"
                      % (county, seat_label(rec), rec["name"]))
            else:
                problems.append("%s: the county's page does not name %s, the certified "
                                "winner (%s) — read the page and add a COUNTY_SAYS entry"
                                % (label, rec["name"], rec["election"]))
    for county in sorted(UNREAD_BY_A_PERSON & set(read)):
        if county not in unsettled:
            problems.append("UNREAD_BY_A_PERSON lists %s, and its page now names every "
                            "winner — remove the entry so a later difference fails" % county)
    print("county pages: %d read, %d winners named on them" % (len(read), agree))
    return problems


def attach_county_says(roster):
    for label, says in COUNTY_SAYS.items():
        county, seat = label.split("|")
        hits = [r for r in roster.get(county, []) if seat_label(r) == seat
                and r.get("name") == says.get("winner")]
        if len(hits) != 1:
            fail("COUNTY_SAYS %s names winner %r, and %d seats match"
                 % (label, says.get("winner"), len(hits)))
        out = {"read": says["read"]}
        for k in ("name", "vacant", "notListed", "former"):
            if says.get(k):
                out[k] = says[k]
        if len(out) != 2:
            fail("COUNTY_SAYS %s must say exactly one of name, vacant, notListed, "
                 "former" % label)
        if out.get("former") and not says.get("phrase"):
            fail("COUNTY_SAYS %s says former and quotes no phrase to re-check" % label)
        hits[0]["countySays"] = out


# ---------- output ----------
def build(geo, roster):
    out = {}
    for county, (fips, form, _) in sorted(geo.items(), key=lambda kv: kv[1][0]):
        entry = COUNTY_PAGES[county]
        rec = {"county": county, "form": form, "seats": roster[county],
               "countyPage": entry[0]}
        out[fips] = rec
    return out


def check(doc, geo, groups):
    problems = []
    if set(doc) != {fips for fips, _, _ in geo.values()}:
        problems.append("the roster's counties differ from the shipped map's")
    named = total = 0
    for fips, rec in doc.items():
        county = rec.get("county")
        g = groups.get(county)
        if g is None:
            problems.append("%s names county %r, which the map does not draw" % (fips, county))
            continue
        have = {}
        for s in rec.get("seats") or []:
            key = (s.get("seat"), s.get("district") or s.get("township") or "")
            have[key] = have.get(key, 0) + 1
            total += 1
            if s.get("name"):
                named += 1
                if not s.get("election") or not s.get("sourceUrl"):
                    problems.append("%s %s names somebody without the election that "
                                    "seated them" % (county, _label(key)))
            elif not s.get("unnamed"):
                problems.append("%s %s names nobody and says nothing about why"
                                % (county, _label(key)))
        if have != g:
            problems.append("%s's seats differ from the seat table: %s against %s"
                            % (county, sorted(have.items()), sorted(g.items())))
        if county not in NO_DISTRICT_SEATS and rec.get("form") != "district":
            problems.append("%s carries form %r" % (county, rec.get("form")))
    if total != EXPECT_SEATS:
        problems.append("%d seats, expected %d" % (total, EXPECT_SEATS))
    if named < MIN_NAMED:
        problems.append("%d seats named, floor %d" % (named, MIN_NAMED))
    for label, says in COUNTY_SAYS.items():
        county, seat = label.split("|")
        fips = geo.get(county, (None,))[0]
        if not any(seat_label(s) == seat and s.get("countySays")
                   for s in (doc.get(fips) or {}).get("seats", [])):
            problems.append("COUNTY_SAYS %s is not carried by the shipped roster" % label)
    for county in COUNTY_PAGES:
        if county not in groups:
            problems.append("COUNTY_PAGES names %r, which the map does not draw" % county)
    return problems, named, total


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped roster to the shipped council map")
    args = ap.parse_args()
    geo = counties_from_geometry()
    groups = seat_groups(geo)
    if args.check:
        with open(OUT_FILE, encoding="utf-8") as f:
            doc = json.load(f)
        problems, named, total = check(doc, geo, groups)
        if problems:
            for p in problems:
                print("build-sc-county-council-roster: FAIL: " + p)
            raise SystemExit(1)
        print("build-sc-county-council-roster --check: OK — %d of %d seats named in "
              "46 counties, each dated to the election that seated it" % (named, total))
        return
    today = datetime.date.today()
    found = discover(today)
    pinned = {e["id"]: e for e in ELECTIONS}
    for eid, meta in sorted(found.items()):
        if eid not in pinned:
            print("  new election on the results page: %s (%d %s)"
                  % (eid, meta["cycle"], meta["kind"]))
            pinned[eid] = {"id": eid, **meta}
        elif (pinned[eid]["cycle"], pinned[eid]["kind"]) != (meta["cycle"], meta["kind"]):
            fail("the results page calls election %s a %d %s, and ELECTIONS a %d %s"
                 % (eid, meta["cycle"], meta["kind"], pinned[eid]["cycle"],
                    pinned[eid]["kind"]))
    for eid in sorted(set(pinned) - set(found)):
        print("  note: election %s is no longer linked from the results page" % eid)
    elections = []
    try:
        for e in sorted(pinned.values(), key=lambda e: (e["cycle"], KIND_ORDER[e["kind"]])):
            details, counties = fetch_election(e["id"])
            elections.append({**e, "details": details, "counties": counties})
            print("  election %s (%d %s, %s): %d counties"
                  % (e["id"], e["cycle"], e["kind"], details["electiondate"], len(counties)))
    except ResultsUnreadable as exc:
        print("sc-council-roster: the results site could not be read this run — %s" % exc)
        print("  the shipped roster is kept as it is; reading the county pages against it")
        with open(OUT_FILE, encoding="utf-8") as f:
            doc = json.load(f)
        problems, named, total = check(doc, geo, groups)
        problems += witness({rec["county"]: rec["seats"] for rec in doc.values()}, today)
        problems += owed(found, today)
        if problems:
            for p in problems:
                print("build-sc-county-council-roster: FAIL: " + p)
            raise SystemExit(1)
        print("sc-council-roster: nothing written; %d of %d shipped seats named, and no "
              "new election is owed yet" % (named, total))
        raise SystemExit(EX_RESULTS_UNREADABLE)
    all_contests, held = contests(elections, groups, today)
    for c, why in held:
        print("  held: %s %s %s — %s" % (c["date"], c["county"], c["contest"], why))
    roster = fill(groups, final_contests(all_contests))
    attach_county_says(roster)
    problems = witness(roster, today)
    doc = build(geo, roster)
    p2, named, total = check(doc, geo, groups)
    problems += p2
    if problems:
        for p in problems:
            print("build-sc-county-council-roster: FAIL: " + p)
        raise SystemExit(1)
    by_year = {}
    for rec in doc.values():
        for s in rec["seats"]:
            if s.get("election"):
                by_year[s["electionName"]] = by_year.get(s["electionName"], 0) + 1
    print("seats by the election that names them: %s"
          % ", ".join("%s %d" % kv for kv in sorted(by_year.items())))
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    print("wrote %s: %d seats in %d counties, %d named"
          % (os.path.relpath(OUT_FILE, os.path.dirname(INSTANCE)), total, len(doc), named))


if __name__ == "__main__":
    main()
