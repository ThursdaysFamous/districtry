#!/usr/bin/env python3
"""Kentucky's school board divisions: Jefferson County's from KRS 160.211, Rowan County's from election results.

Writes ky/data/app/ky-school-board-divisions.json, the school-board-district
layer, and ky/data/source/ky-school-board-divisions.source.json, the record
that --check holds it to.

Kentucky elects each county board of education from five divisions made of
whole voting precincts, and each independent district's board at large (KRS
160.210). No office publishes the divisions for the whole state, so this
builder draws two counties' divisions, by two different methods, records why
it draws no others, and names no board member (gap ky-school-board-members:
no list of members by division has been found). Every number below was
measured on 2026-10-17 unless it says otherwise.

JEFFERSON COUNTY, FROM THE STATUTE
----------------------------------
2026 Ky. Acts ch. 154 cut the Jefferson County board from seven members to
five and wrote the five divisions into KRS 160.211 as lists of precinct codes,
"based upon the precinct identification codes and precinct boundaries
maintained by the Jefferson County Clerk's Office as of March 19, 2026", made
of the "territory in Jefferson County that is part of the Jefferson County
School District". The five divisions are first elected at the November 3, 2026
general election (act section 17; FIRST_ELECTION).

* The codified section, kept as data/source/statutes/krs160.211.txt, lists 643
  codes: 135, 144, 127, 127 and 110 to Divisions One to Five
  (EXPECT_DIVISION_SIZES). Section 9 of the act as published (ACT, read on
  every build) lists the same codes in the same order, and the build stops if
  the two differ.
* The State Board of Elections' precinct map (PRECINCTS, edited 2026-10-15)
  holds 646 Jefferson precincts: all 643 listed codes, and F154, F155 and F183,
  which no list names (EXPECT_UNLISTED; the build stops if that set changes).
* Each division is the union of its listed precincts, cut to the Census
  Bureau's boundary of the Jefferson County School District (TIGERweb unified
  district 2102990). The cut takes 0.0294 km2 from Division 1, 0.1391 from
  Division 3 and 0.0127 from Division 5, and nothing from 2 or 4. Of that,
  0.1116 km2 is ground the Census map puts in the Anchorage Independent School
  District (2100090), in six listed precincts: F145 7.44 ha, F164 1.72, F167
  1.22, F171 0.67, F158 0.07 and F153 0.04.
* THE CUT FOLLOWS THE STATUTE'S WORDS, AND OTHER EVIDENCE DISAGREES WITH THE
  CENSUS LINE THERE. Both published maps of the divisions keep all 0.1116 km2
  inside a division, the same area the cut removes, and in the 2022 general
  election the Jefferson County board race was on 949 of F145's 949 ballots,
  288 of F153's 288, 696 of F158's 697, 718 of F164's 718 and 657 of F171's
  657; F167's 1,020 ballots carried no Jefferson County board race, and its
  Anchorage board race records no votes. So no ballot cast in those six
  precincts carried Anchorage's board race. Two readings fit that, and which
  is right is not established here: the Census line and the county's line
  differ there, or the cut ground has no voters. The card says the lines are
  approximate and sends a reader to the county board of elections for a
  definitive answer.
* F154, F155 and F183 each lie across the line between the two school
  districts. KRS 160.211(2) has the county board of elections add the part of
  such a precinct inside the Jefferson County School District to a contiguous
  division. No such assignment was found published, so each is shipped WHOLE,
  as a feature of kind "unplaced", in no division: what is not known is which
  division the county part joined, and the Census line is a poor guide to
  where that part is. It puts all but 0.0005 km2 of F154's 2.0411 km2 in
  Anchorage's district, leaving the county part as ten slivers, the widest
  1.36 m across, yet 72 of F154's 521 ballots in 2022 carried a Jefferson
  County board race (449 carried Anchorage's). F155 is 3.3058 km2, 3.2623 of
  it in Anchorage's district by the Census map, with 597 ballots in 2022, 27
  of them county and 570 Anchorage; F183 is 2.7785 km2, 2.3713 of it
  Anchorage's, with 370 ballots, 197 county and 173 Anchorage. Neither
  published map of the divisions puts any of the three in a division (at most
  0.1 m2 each).
* Three Louisville layers are read as CHECKS on the statute parse and the
  join, never as sources. LOJIC's precinct layer (LOJIC_PRECINCTS, 646
  records) gives each of the 643 listed precincts the statute's division in
  its SCHOOLDIST column, and gives the three unlisted precincts "3A", which is
  not one of its five divisions. LOJIC's map of the divisions (LOJIC_BOARD,
  six records: the five divisions and "ANS", the Anchorage district) and the
  school district's own (JCPS_MAP, edited 2026-04-27) each score 0.9995, 1.0,
  0.99896, 1.0 and 0.99951 for Divisions 1 to 5 as intersection over union
  with the statute's divisions as whole listed precincts (floor
  WITNESS_IOU_FLOOR, 0.998), and 0.99949, 1.0, 0.99869, 1.0 and 0.9995 with
  the divisions as cut.

THE COUNTIES DRAWN FROM ELECTION RESULTS
----------------------------------------
Every other county board's divisions can be known here only from which
precincts' ballots carried which division's race. Nine counties were proposed
from a survey of the State Board's recap sheets on 2026-10-16 (CANDIDATES),
and every build tests each one against its sheets for the 2022 and 2024
general elections (GENERALS). A county is drawn only if:

* every precinct code on each sheet is a code on today's precinct map, and
  every code on the map heads a page of each sheet;
* every board race on a precinct's page is a numbered Educational District,
  vote for one, with cast votes, undervotes and overvotes adding up to the
  precinct's ballots, so the precinct voted whole in that division;
* every precinct is placed, never in two divisions, and the divisions placed
  are 1 to 5;
* today's precincts carry the 2020 Census voting districts' codes, and no
  ground lies in different divisions in the two once the difference is eroded
  by ERODE_M (30 m), because nothing dates a precinct change against the
  elections read.

Rowan alone passes (EXPECT_RESULTS_DRAWN; the build stops if the set
changes): 18 precincts, Divisions 1 and 5 placed by the 2022 general and 2, 3
and 4 by the 2024 general; 164.6, 197.0, 252.0, 113.7 and 14.0 km2, cut to the
Census boundary of the Rowan County School District (2105100). Not drawn:

  Grayson     codes on the 2022 sheet that today's map does not carry (C101, D103)
  Harrison    the same (D103)
  Henderson   the same (A102, A114, A116, B102, B104, B105)
  Jessamine   the 2022 sheet's precinct headings are not read: a scan, or a
              layout this reader does not know
  Monroe      ground in different divisions now and in 2020, after erosion:
              1,567.06 ha in Division 4 and 1,540.52 in Division 5
  Muhlenberg  the same: 70.55 ha in Divisions 1 and 5
  Nicholas    the same in every division, up to 2,226.33 ha in Division 2
  Webster     the same: up to 5,266.05 ha in Division 5

DRAWING AND THE GATES
---------------------
Every feature is simplified in ONE mapshaper run (MAPSHAPER, Douglas-Peucker,
keep-shapes, interval 8 m, the precinct file's own), so a line two features
share is one arc. Before simplifying, rings enclosing less than SLIVER_M2
(1 m2) are dropped: two holes of 0.0139 m2 together in Division 4, where two
precincts' lines do not quite meet. Measured on this build:

* fidelity: the true line strays at most 8.03 m from the drawn one
  (FIDELITY_CEILING_M, 10 m);
* validate: 3,000 of 3,000 points over the two counties' envelopes get the
  same answer from the drawn file as from the exact composition, and none
  falls in two features;
* overlaps: mapshaper could not repair 7 intersections, so drawn features
  overlap by 0.008 m2 (Division 3 and F154) and 8.042 m2 (Division 3 and
  F155), under OVERLAP_CEILING_M2 (25 m2 per pair);
* agreement with the shipped precinct file: of 400 points inside each feature,
  the share whose precinct in ky-precincts.json is one the feature is made of
  is at least 0.9975 (Division 4), against AGREE_FLOOR 0.99;
* each board's own page (BOARD_PAGES) answers HTTP 200 before the card links it.

Every host's robots.txt is read with this builder's client before the first
request to it and at every redirect hop, and a refusal stops the build; the
verdicts are kept in the record.

USAGE
-----
  python3 ky/scripts/build_ky_school_board_divisions.py              # build (network, shapely, pyproj, pdftotext, npx)
  python3 ky/scripts/build_ky_school_board_divisions.py --cache DIR  # build, keeping fetched layers and sheets in DIR
  python3 ky/scripts/build_ky_school_board_divisions.py --check      # offline
  python3 ky/scripts/build_ky_school_board_divisions.py --selftest   # offline

--check needs no network: it holds the shipped file to the hash in the
record, the kept statute to the codes the build read, every feature's
properties to the record, the shipped precinct file to the precincts each
feature is made of (so a ky-precincts.json rebuild that changes a code in a
drawn county fails here), and the card to the claims in CARD_CLAIMS. It is
not yet run in CI.
"""

import argparse
import collections
import datetime
import hashlib
import html
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile
import time
import types
from urllib.parse import unquote, urljoin, urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
sys.path.insert(0, os.path.join(REPO, "scripts"))

import statewide_precincts as sp  # noqa: E402  (point lookup and the card check)
from robots_policy import RobotsGate  # noqa: E402  (stdlib-only at import)

USER_AGENT = "districtry/1.0 (+https://districtry.com/ky/)"
PACE = 0.5  # seconds between two requests to one host, unless robots.txt asks for more

APP = os.path.join(INSTANCE, "data", "app")
OUT_NAME = "ky-school-board-divisions.json"
OUT_FILE = os.path.join(APP, OUT_NAME)
PRECINCT_FILE = os.path.join(APP, "ky-precincts.json")
RECORD = os.path.join(INSTANCE, "data", "source", "ky-school-board-divisions.source.json")
STATUTE = os.path.join(INSTANCE, "data", "source", "statutes", "krs160.211.txt")

# ---------- sources ----------
PRECINCTS = ("https://services3.arcgis.com/ghsX9CKghMvyYjBU/arcgis/rest/services/"
             "Ky_SBE_VTD_Boundaries_WM/FeatureServer/0")
TIGER_SCHOOL = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/School/MapServer"
TIGER_VTD_2020 = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                  "tigerWMS_Census2020/MapServer/58")
LOJIC = "https://gis.lojic.org/maps/rest/services/LojicSolutions/OpenDataPolitical/MapServer"
LOJIC_BOARD = LOJIC + "/2"       # "Jefferson County KY School Board Districts"
LOJIC_PRECINCTS = LOJIC + "/6"   # "Jefferson County KY Voting Precincts", with SCHOOLDIST
JCPS_MAP = ("https://services5.arcgis.com/aPhGC3Kc78PZRGIh/arcgis/rest/services/"
            "BoardDistricts_PostSB4NoAnchorage/FeatureServer/0")
JCPS_MAP_PAGE = "https://experience.arcgis.com/experience/08ff50c42ad04f00922dc7e3bbbadcfb"
ACT = "https://apps.legislature.ky.gov/law/acts/26RS/documents/0154.pdf"
GENERALS = {
    "2022-11-08": "https://elect.ky.gov/results/2020-2029/Pages/2022-General-Recap-Sheets.aspx",
    "2024-11-05": "https://elect.ky.gov/results/2020-2029/Pages/2024General-Recap-Sheets.aspx",
}

# ---------- Jefferson: the statute ----------
JEFFERSON = "21111"
JEFFERSON_DISTRICT = "2102990"   # TIGER unified: Jefferson County School District
ANCHORAGE_DISTRICT = "2100090"   # TIGER elementary: Anchorage Independent School District
EXPECT_DIVISION_SIZES = {"1": 135, "2": 144, "3": 127, "4": 127, "5": 110}
# Current precincts the statute does not list. A change here is a
# re-precincting or an amendment: read both before changing it.
EXPECT_UNLISTED = ("F154", "F155", "F183")
FIRST_ELECTION = "2026-11-03"    # the five divisions' first election (act section 17)
WITNESS_IOU_FLOOR = 0.998

# ---------- the counties drawn from election results ----------
# Proposed for this tier from a survey of the recap sheets on 2026-10-16, and
# tested here on every build. The fips are the counties' own.
CANDIDATES = {
    "Grayson": "21085", "Harrison": "21097", "Henderson": "21101", "Jessamine": "21113",
    "Monroe": "21171", "Muhlenberg": "21177", "Nicholas": "21181", "Rowan": "21205",
    "Webster": "21233",
}
# The candidates that pass every test, measured 2026-10-17. The build fails
# when the measured set differs, so a change is read by a person first.
EXPECT_RESULTS_DRAWN = ("Rowan",)
ERODE_M = 30.0   # a change to a division smaller than this on every side is a drafting difference

# Each drawn board's own page, fetched at every build (HTTP 200 and the words
# "Board of Education") before the card links it.
BOARD_PAGES = {
    "21111": "https://www.jefferson.kyschools.us/page/board-of-education",
    "21205": "https://www.rowan.kyschools.us/page/board-of-education",
}

# ---------- drawing ----------
MAPSHAPER = "mapshaper@0.6.102"
INTERVAL = "8"            # metres; the precinct file's own interval
PRECISION = "0.000001"
FIDELITY_CEILING_M = 10.0
VALIDATE_SAMPLES = 1500   # per drawn county, over its envelope
AGREE_POINTS = 400        # per shipped feature, for the precinct agreement gate
AGREE_FLOOR = 0.99        # lowest measured 0.9975 on 2026-10-17; see agree_with_precincts()
OVERLAP_CEILING_M2 = 25.0 # per pair of drawn features; see overlaps()
CARD_CLAIMS = ("KRS 160.211", "November 3, 2026")

NUM = {"One": "1", "Two": "2", "Three": "3", "Four": "4", "Five": "5"}


def fail(msg):
    raise SystemExit("build-ky-school-board-divisions: FATAL: %s" % msg)


# ---------- reading the statute ----------
STATUTE_HEAD = re.compile(r"\(([a-e])\)\s+Division (One|Two|Three|Four|Five) shall consist "
                          r"of the following territory:")
STATUTE_END = re.compile(r"^\s*\(2\)\s+If any precinct", re.M)
# Page furniture in the session-law PDF, which falls between codes
ACT_NOISE = (re.compile(r"^\s*CHAPTER 154\s*\d*\s*$"),
             re.compile(r"^\s*Legislative Research Commission PDF Version\s*$"),
             re.compile(r"^\s*\d*\s*ACTS OF THE GENERAL ASSEMBLY\s*\d*\s*$"))
CODE = re.compile(r"\b([A-Z]\d{3})\b")


def parse_divisions(text):
    """{division: [codes in printed order]} from KRS 160.211 as codified, or
    from section 9 of 2026 Ky. Acts ch. 154 as enacted. Anything between two
    division headings other than codes (and the act's page furniture) stops
    the build, so a sentence inside a list cannot be skipped silently."""
    at = text.find("SECTION 9.")
    if at < 0:
        at = text.find("160.211")
    if at < 0:
        fail("the text is neither KRS 160.211 nor the act's section 9")
    text = text[at:]
    heads = list(STATUTE_HEAD.finditer(text))
    if [NUM[h.group(2)] for h in heads] != ["1", "2", "3", "4", "5"]:
        fail("expected Division One to Five in order, read %r" % [h.group(2) for h in heads])
    end = STATUTE_END.search(text, heads[-1].end())
    if not end:
        fail("subsection (2) does not follow Division Five")
    out = {}
    for i, h in enumerate(heads):
        stop = heads[i + 1].start() if i + 1 < len(heads) else end.start()
        body = "\n".join(line for line in text[h.end():stop].split("\n")
                         if not any(n.match(line) for n in ACT_NOISE))
        rest = CODE.sub("", body).strip()
        if rest:
            fail("Division %s's list carries words as well as codes: %r" % (h.group(2), rest[:200]))
        out[NUM[h.group(2)]] = CODE.findall(body)
    every = [c for codes in out.values() for c in codes]
    if len(every) != len(set(every)):
        twice = sorted(c for c, n in collections.Counter(every).items() if n > 1)
        fail("the statute lists %s more than once" % twice)
    return out


# ---------- reading the recap sheets ----------
# The State Board's county recap sheets, read as pdftotext lays them out.
# Most counties' sheets ("Precinct Results Report") put each precinct's code
# at the start of a line with its ballots cast at the end of that line.
SHEET_PRECINCT = re.compile(r"^\s{0,3}([A-Z]\d{3})[A-Z]?(?:\s|$)")
SHEET_BALLOTS = re.compile(r"([\d,]+)\s+ballots cast\s*$")
SHEET_BOARD = re.compile(r"BOARD\s+of\s+EDUCATION\s*(.*?)\s*-\s*\(Vote\s+for\s+(\w+)\)", re.I)
SHEET_DIVISION = re.compile(r"^(\d)(?:st|nd|rd|th)\s+Educational\s+District$", re.I)


def _counts(line):
    return [int(t.replace(",", "")) for t in line.split() if re.fullmatch(r"\d[\d,]*", t)]


def parse_sheet(text):
    """(seen, ballots, races, other) from one county's recap sheet.

    seen: every precinct code heading a page; ballots: {code: ballots cast};
    races: {code: [(division, contest, cast, under, over, vote_for)]} for each
    board race on that precinct's pages; other: board-of-education contests
    whose name is not a numbered Educational District, which the caller
    refuses rather than reads."""
    seen, ballots, races, other = set(), {}, collections.defaultdict(list), []
    cur, race = None, None
    for line in text.split("\n"):
        m = SHEET_PRECINCT.match(line)
        if m:
            cur, race = m.group(1), None
            seen.add(cur)
            b = SHEET_BALLOTS.search(line)
            if b:
                n = int(b.group(1).replace(",", ""))
                if ballots.setdefault(cur, n) != n:
                    other.append("%s heads pages with two ballot counts" % cur)
            continue
        b = SHEET_BOARD.search(line)
        if b:
            name = re.sub(r"\s+", " ", b.group(1)).strip()
            d = SHEET_DIVISION.match(name)
            if not d or cur is None:
                other.append(name)
                race = None
                continue
            contest = re.sub(r"\s+", " ", line.split(" - (")[0]).strip()
            race = {"division": d.group(1), "contest": contest, "vote_for": b.group(2).lower()}
            continue
        if race is not None:
            s = line.strip()
            if s.startswith("Cast Votes:"):
                race["cast"] = (_counts(s) or [None])[-1]
            elif s.startswith("Undervotes:"):
                race["under"] = (_counts(s) or [None])[-1]
            elif s.startswith("Overvotes:"):
                race["over"] = (_counts(s) or [None])[-1]
                races[cur].append(race)
                race = None
    return seen, ballots, dict(races), other


# Jefferson's sheets are Electionware's "Precinct Summary Results Report": a
# precinct code alone on a line, then two-space-indented contest headings
# with "Vote For N" and a "Contest Totals" row counting ballots times N.
JEFF_PRECINCT = re.compile(r"^\s{0,3}([A-Z]\d{3})\s*$")
JEFF_HEAD = re.compile(r"^  ([A-Z][^ ].*?)\s*$")
JEFF_NOT_HEAD = ("Vote For", "Contest Totals", "Write-In", "Not Assigned", "Total Votes")


def parse_jefferson(text, codes):
    """{code: {"ballots": n, "races": [(contest, vote_for, contest_totals)]}}
    for the school board races on the named precincts' pages."""
    out = {c: {"ballots": None, "races": []} for c in codes}
    cur, contest, vote_for = None, None, None
    for line in text.split("\n"):
        m = JEFF_PRECINCT.match(line)
        if m:
            cur = m.group(1)
            continue
        if cur not in out:
            continue
        if line.startswith("Ballots Cast - Total"):
            n = _counts(line)[0]
            if out[cur]["ballots"] not in (None, n):
                fail("precinct %s reads two ballot totals" % cur)
            out[cur]["ballots"] = n
            continue
        h = JEFF_HEAD.match(line)
        if h and not h.group(1).startswith(JEFF_NOT_HEAD):
            contest, vote_for = h.group(1), None
            continue
        s = line.strip()
        if s.startswith("Vote For"):
            vote_for = _counts(s)[-1]
        elif s.startswith("Contest Totals") and contest and "SCHOOL BOARD" in contest:
            race = (contest, vote_for, _counts(s)[0])
            if race not in out[cur]["races"]:
                out[cur]["races"].append(race)
    return out


def jefferson_split(parsed):
    """For each unlisted precinct: ballots cast, the ballots that carried the
    Jefferson County board race and those that carried Anchorage's. The two
    must add up to the ballots cast, or the reading is wrong."""
    out = {}
    for code, rec in sorted(parsed.items()):
        county = [r for r in rec["races"] if "ANCHORAGE" not in r[0]]
        anchorage = [r for r in rec["races"] if "ANCHORAGE" in r[0]]
        if rec["ballots"] is None or len(county) != 1 or len(anchorage) != 1:
            fail("precinct %s on the 2022 Jefferson sheet: ballots %r, races %r"
                 % (code, rec["ballots"], rec["races"]))
        (cname, cvf, ctot), (aname, avf, atot) = county[0], anchorage[0]
        if cvf != 1 or not avf or atot % avf:
            fail("precinct %s: unexpected vote-for counts %r" % (code, rec["races"]))
        if ctot + atot // avf != rec["ballots"]:
            fail("precinct %s: %d + %d/%d ballots do not make the %d cast"
                 % (code, ctot, atot, avf, rec["ballots"]))
        out[code] = {"ballots": rec["ballots"], "countyBoard": ctot, "anchorage": atot // avf,
                     "countyContest": cname, "anchorageContest": aname}
    return out


# ---------- fetching ----------
class Http(object):
    """One client: robots.txt read with it before the first request to every
    host and at every redirect hop, and requests to one host paced."""

    def __init__(self, cache):
        import requests  # noqa: PLC0415  (fleet scraper dependency)
        self.requests = requests
        self.session = requests.Session()
        self.headers = {"User-Agent": USER_AGENT}
        self.gate = RobotsGate(self.session, USER_AGENT, headers=self.headers)
        self.cache = cache
        self.verdicts = {}
        self.last = {}

    def allow(self, url):
        ok, why = self.gate.allows(url)
        host = urlsplit(url).hostname
        if host not in self.verdicts:
            delay = float(self.gate.crawl_delay(url) or 0.0)
            self.verdicts[host] = {"verdict": why, "crawlDelay": delay}
            print("robots.txt %s: %s — %s" % (host, "allowed" if ok else "REFUSED", why),
                  file=sys.stderr)
        if not ok:
            fail("robots.txt on %s refuses this client for %s (%s); not fetching" % (host, url, why))

    def get(self, url, params=None):
        cur, first = url, True
        for _ in range(6):
            self.allow(cur)
            host = urlsplit(cur).hostname
            wait = max(PACE, self.verdicts[host]["crawlDelay"])
            since = time.time() - self.last.get(host, 0.0)
            if since < wait:
                time.sleep(wait - since)
            last = None
            for attempt in range(4):
                try:
                    r = self.session.get(cur, params=params if first else None,
                                         headers=self.headers, timeout=300, allow_redirects=False)
                    break
                except self.requests.RequestException as exc:
                    last = exc
                    time.sleep(5.0 * (attempt + 1))
            else:
                fail("%s did not answer after four tries: %s" % (cur, last))
            self.last[host] = time.time()
            if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
                cur, first = urljoin(cur, r.headers["Location"]), False
                continue
            if r.status_code != 200:
                fail("%s answered HTTP %d" % (cur, r.status_code))
            return r
        fail("more than five redirects from %s" % url)

    def json(self, url, params):
        doc = self.get(url, params).json()
        if isinstance(doc, dict) and doc.get("error"):
            fail("%s answered an error envelope: %r" % (url, doc["error"]))
        return doc

    def cached(self, name, fn):
        path = os.path.join(self.cache, name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        data = fn()
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        return data

    def pdf_text(self, url, name):
        """pdftotext's layout text of a PDF, cached."""
        def read():
            r = self.get(url)
            if not r.content.startswith(b"%PDF"):
                fail("%s is not a PDF" % url)
            with tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "f.pdf")
                with open(path, "wb") as fh:
                    fh.write(r.content)
                text = subprocess.run(["pdftotext", "-layout", path, "-"], check=True,
                                      capture_output=True, text=True, errors="replace").stdout
            return {"url": url, "bytes": len(r.content),
                    "lastModified": r.headers.get("Last-Modified"), "text": text}
        return self.cached(name, read)

    def arcgis(self, layer, where, out_fields):
        """Every record of an ArcGIS layer as Esri JSON, fetched in runs of
        consecutive object ids so no record is read twice or skipped."""
        meta = self.json(layer, {"f": "json"})
        oid = meta.get("objectIdField") or next(
            (f["name"] for f in meta.get("fields") or [] if f.get("type") == "esriFieldTypeOID"), None)
        if not oid:
            fail("%s names no object id field" % layer)
        page = min(500, int(meta.get("maxRecordCount") or 500))
        ids = self.json(layer + "/query", {"where": where, "returnIdsOnly": "true",
                                           "f": "json"}).get("objectIds") or []
        ids.sort()
        feats = []
        for i in range(0, len(ids), page):
            run = ids[i:i + page]
            doc = self.json(layer + "/query", {
                "where": "(%s) AND %s >= %d AND %s <= %d" % (where, oid, run[0], oid, run[-1]),
                "outFields": out_fields, "returnGeometry": "true", "outSR": "4326",
                "orderByFields": oid, "f": "json"})
            got = doc.get("features")
            if got is None or len(got) != len(run):
                fail("%s: asked for %d records by object id and got %r" % (
                    layer, len(run), None if got is None else len(got)))
            feats.extend(got)
        edited = (meta.get("editingInfo") or {}).get("lastEditDate")
        return {"features": feats, "edited": (
            datetime.datetime.fromtimestamp(edited / 1000.0, datetime.timezone.utc)
            .strftime("%Y-%m-%d") if edited else None), "name": meta.get("name")}

    def recap_links(self, page):
        """{county: sheet url} from one election's recap page."""
        text = self.get(page).text
        out = {}
        for href in re.findall(r'href="([^"]+GeneralRecaps/[^"]+\.pdf)"', text, re.I):
            url = urljoin(page, html.unescape(href))
            county = re.sub(r"\s+County$", "", unquote(url.rsplit("/", 1)[1])[:-4]).strip()
            out[county] = url
        if len(out) < 100:
            fail("%s links %d county sheets, expected about 120" % (page, len(out)))
        return out


# ---------- geometry ----------
_FWD = _INV = None


def _transformers():
    global _FWD, _INV
    if _FWD is None:
        import pyproj  # noqa: PLC0415
        _FWD = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True).transform
        _INV = pyproj.Transformer.from_crs("EPSG:5070", "EPSG:4326", always_xy=True).transform
    return _FWD, _INV


def metres(g):
    """g in an equal-area projection (Albers, EPSG:5070), for areas and erosion."""
    from shapely.ops import transform  # noqa: PLC0415
    return transform(_transformers()[0], g)


def km2(g):
    return metres(g).area / 1e6


def polygonal(g):
    from shapely.geometry import MultiPolygon, Polygon  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415
    if g is None or g.is_empty:
        return Polygon()
    if isinstance(g, (Polygon, MultiPolygon)):
        return g
    parts = [p for p in getattr(g, "geoms", []) if isinstance(p, (Polygon, MultiPolygon))]
    return unary_union(parts) if parts else Polygon()


def esri_shape(geometry):
    """An Esri polygon read by the even-odd rule the app's pointInGeometry
    uses: a point is inside when an odd number of rings enclose it. Each ring
    is a polygon and the rings are combined by symmetric difference, so a
    hole is a hole whatever its winding."""
    from shapely import make_valid  # noqa: PLC0415
    from shapely.geometry import Polygon  # noqa: PLC0415
    g = None
    for ring in (geometry or {}).get("rings") or []:
        if len(ring) < 4:
            continue
        p = Polygon([(x, y) for x, y in (pt[:2] for pt in ring)])
        if not p.is_valid:
            p = make_valid(p)
        p = polygonal(p)
        g = p if g is None else polygonal(g.symmetric_difference(p))
    if g is None or g.is_empty:
        fail("a record carries no polygon")
    return g


def parts_of(g):
    return [p for p in getattr(g, "geoms", [g]) if not p.is_empty]


SLIVER_M2 = 1.0   # a ring enclosing less ground than this is a gap between two
                  # precincts' lines in the State Board's file, not a place


def clean(g):
    """g without the holes and parts that enclose less than SLIVER_M2, and
    what was dropped (count, m2). The union of whole precincts leaves such
    rings where two neighbours' lines do not quite meet; no reader can be
    inside one, and the simplifier would drop them anyway."""
    from shapely.geometry import MultiPolygon, Polygon  # noqa: PLC0415
    keep, dropped, area = [], 0, 0.0
    for p in parts_of(g):
        a = metres(p).area
        if a < SLIVER_M2:
            dropped, area = dropped + 1, area + a
            continue
        holes = []
        for h in p.interiors:
            ha = metres(Polygon(h)).area
            if ha < SLIVER_M2:
                dropped, area = dropped + 1, area + ha
            else:
                holes.append(h)
        keep.append(Polygon(p.exterior, holes))
    if not keep:
        return Polygon(), dropped, area
    return (keep[0] if len(keep) == 1 else MultiPolygon(keep)), dropped, area


# ---------- the tests a county drawn from election results must pass ----------
def results_county(name, fips, codes, sheets, vtd):
    """Apply every test to one candidate county. Returns a dict with
    "drawn" (bool), "why" (the first failure, in words), "placement"
    {code: (division, election, contest)} and the measurements read."""
    rep = {"county": name, "fips": fips, "precincts": len(codes), "drawn": False}
    placement, divisions = {}, collections.defaultdict(list)
    shapes, codes = codes, set(codes)
    for day, sheet in sorted(sheets.items()):
        if sheet is None:
            rep["why"] = "no %s recap sheet is linked for the county" % day
            return rep
        if day[:4] not in sheet["dates"]:
            rep["why"] = "the %s sheet does not carry that election's date" % day
            return rep
        seen, ballots, races, other = parse_sheet(sheet["text"])
        if not seen:
            rep["why"] = ("the %s sheet's precinct headings are not read: a scan, or a layout "
                          "this reader does not know" % day)
            return rep
        if other:
            rep["why"] = "the %s sheet carries a board race this reader cannot place: %r" % (
                day, sorted(set(other))[:3])
            return rep
        gone = sorted(seen - codes)
        if gone:
            rep["why"] = ("precinct codes on the %s sheet are not in today's map (%s): the "
                          "precincts changed after that election" % (day, ", ".join(gone[:6])))
            return rep
        absent = sorted(codes - seen)
        if absent:
            rep["why"] = ("today's precincts %s are not on the %s sheet: the precincts changed "
                          "after that election" % (", ".join(absent[:6]), day))
            return rep
        for code, lst in races.items():
            for r in lst:
                total = (r.get("cast") or 0) + (r.get("under") or 0) + (r.get("over") or 0)
                if r["vote_for"] != "one":
                    rep["why"] = "%s's %s board race is not vote-for-one" % (code, day)
                    return rep
                if total != ballots.get(code):
                    rep["why"] = ("in %s the %s board race was on %d of the precinct's %r "
                                  "ballots, so the precinct may be split" % (
                                      code, day, total, ballots.get(code)))
                    return rep
                if code in placement and placement[code][0] != r["division"]:
                    rep["why"] = "precinct %s voted in divisions %s and %s" % (
                        code, placement[code][0], r["division"])
                    return rep
                placement[code] = (r["division"], day, r["contest"])
        rep["sheet" + day[:4]] = sheet["url"]
    unplaced = sorted(codes - set(placement))
    if unplaced:
        rep["why"] = "no board race placed precincts %s in the 2022 or 2024 general" % (
            ", ".join(unplaced[:6]))
        return rep
    for code, (d, _, _) in placement.items():
        divisions[d].append(code)
    if sorted(divisions) != ["1", "2", "3", "4", "5"]:
        rep["why"] = "the results place precincts in divisions %s, not 1 to 5" % sorted(divisions)
        return rep
    # unchanged since the 2020 Census: the same codes, and no ground across a
    # division line other than slivers narrower than ERODE_M on every side
    from shapely.ops import unary_union  # noqa: PLC0415
    if set(vtd) != codes:
        rep["why"] = ("the county's precincts are not the 2020 Census's (only now: %s; only in "
                      "2020: %s), and nothing dates that change against the elections read"
                      % (", ".join(sorted(codes - set(vtd))[:4]) or "none",
                         ", ".join(sorted(set(vtd) - codes)[:4]) or "none"))
        return rep
    moved = {}
    for d, cs in sorted(divisions.items()):
        now = metres(unary_union([shapes[c] for c in cs]))
        then = metres(unary_union([vtd[c] for c in cs]))
        core = now.symmetric_difference(then).buffer(-ERODE_M)
        moved[d] = round(core.area / 1e4, 2)
    rep["movedSince2020Ha"] = moved
    if any(v > 0 for v in moved.values()):
        rep["why"] = ("ground has moved across a division line since the 2020 Census "
                      "(hectares after a %d m erosion, by division: %s), and nothing dates "
                      "that change against the elections read" % (ERODE_M, moved))
        return rep
    rep["drawn"] = True
    rep["why"] = "every test passed"
    rep["placement"] = {c: {"division": d, "election": day, "contest": contest}
                        for c, (d, day, contest) in sorted(placement.items())}
    return rep


# ---------- the build ----------
def fetch_tiger_district(http, geoid, layer):
    doc = http.json("%s/%d/query" % (TIGER_SCHOOL, layer), {
        "where": "GEOID='%s'" % geoid, "outFields": "GEOID,NAME",
        "returnGeometry": "true", "outSR": "4326", "f": "json"})
    feats = doc.get("features") or []
    if len(feats) != 1:
        fail("TIGERweb School layer %d holds %d records for GEOID %s" % (layer, len(feats), geoid))
    return feats[0]["attributes"]["NAME"], esri_shape(feats[0]["geometry"])


def tiger_district_named(http, name):
    doc = http.json("%s/0/query" % TIGER_SCHOOL, {
        "where": "STATE='21' AND NAME='%s'" % name.replace("'", "''"), "outFields": "GEOID,NAME",
        "returnGeometry": "false", "f": "json"})
    feats = doc.get("features") or []
    if len(feats) != 1:
        fail("TIGERweb holds %d unified districts named %r" % (len(feats), name))
    return feats[0]["attributes"]["GEOID"]


def iou(a, b):
    a, b = metres(a), metres(b)
    u = a.union(b).area
    return a.intersection(b).area / u if u else 1.0


def witnesses(http, statute, fabric_j, jdistrict, anchorage):
    """The two Jefferson maps drawn by other offices, read as checks on the
    statute parse and the join, never as sources. Each is scored against the
    divisions as whole listed precincts (the floor applies there: that is the
    statute read directly) and as cut at the Census line, and the ground each
    keeps inside a division that the Census puts in Anchorage's district is
    recorded, because that is where the two readings part."""
    from shapely.ops import unary_union  # noqa: PLC0415
    code_div = {c: d for d, cs in statute.items() for c in cs}
    out = {}
    pct = http.arcgis(LOJIC_PRECINCTS, "1=1", "PRECINCT,SCHOOLDIST")
    tags = {}
    for f in pct["features"]:
        a = f["attributes"]
        tags[(a.get("PRECINCT") or "").strip()] = (a.get("SCHOOLDIST") or "").strip()
    wrong = sorted(c for c, d in code_div.items() if tags.get(c) != d)
    if wrong:
        fail("LOJIC's precinct layer disagrees with the statute for %s" % wrong[:10])
    out["lojicPrecincts"] = {"url": LOJIC_PRECINCTS, "records": len(tags), "edited": pct["edited"],
                             "agree": len(code_div),
                             "unlisted": {c: tags.get(c) for c in EXPECT_UNLISTED}}
    whole = {d: unary_union([fabric_j[c] for c in cs]) for d, cs in statute.items()}
    for label, url, field in (("lojicBoard", LOJIC_BOARD, "SCHOOLDIST"),
                              ("jcpsMap", JCPS_MAP, "district")):
        doc = http.arcgis(url, "1=1", field)
        theirs = collections.defaultdict(list)
        for f in doc["features"]:
            theirs[str(f["attributes"].get(field)).strip()].append(esri_shape(f["geometry"]))
        scores, scores_cut = {}, {}
        for d in sorted(statute):
            key = d if d in theirs else str(int(d))
            if key not in theirs:
                fail("%s has no division %s" % (url, d))
            scores[d] = round(iou(whole[d], unary_union(theirs[key])), 5)
            scores_cut[d] = round(iou(whole[d].intersection(jdistrict), unary_union(theirs[key])), 5)
        if min(scores.values()) < WITNESS_IOU_FLOOR:
            fail("%s matches the statute's divisions at IoU %r, under %.3f"
                 % (url, scores, WITNESS_IOU_FLOOR))
        # the three unlisted precincts lie in none of the witness's five divisions
        five = unary_union([unary_union(theirs[k]) for k in theirs if k in ("1", "2", "3", "4", "5")])
        inside = {c: round(metres(fabric_j[c].intersection(five)).area, 1) for c in EXPECT_UNLISTED}
        if any(v > 1000 for v in inside.values()):
            fail("%s puts unlisted precincts inside a division: %r m2" % (url, inside))
        out[label] = {"url": url, "edited": doc["edited"], "iou": scores, "iouCut": scores_cut,
                      "keptInCensusAnchorageKm2": round(km2(five.intersection(anchorage)), 4),
                      "unlistedInsideM2": inside, "areas": sorted(theirs)}
    return out


def build(cache):
    from shapely.geometry import mapping  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415
    http = Http(cache)
    stale = check_card()
    if stale:
        fail("; ".join(stale) + " — change the card before building")

    # 1. the statute, codified and as enacted
    with open(STATUTE, encoding="utf-8") as fh:
        statute = parse_divisions(fh.read())
    sizes = {d: len(cs) for d, cs in statute.items()}
    if sizes != EXPECT_DIVISION_SIZES:
        fail("the statute reads %r, expected %r" % (sizes, EXPECT_DIVISION_SIZES))
    act = http.pdf_text(ACT, "act-0154.json")
    if parse_divisions(act["text"]) != statute:
        fail("section 9 of 2026 Ky. Acts ch. 154 and the codified KRS 160.211 list different codes")
    print("statute: %d codes (%s), identical in the act as enacted"
          % (sum(sizes.values()), "/".join(str(sizes[d]) for d in sorted(sizes))))

    # 2. the precincts, at full precision
    counties = [JEFFERSON] + sorted(CANDIDATES.values())
    sbe = http.cached("sbe-precincts.json", lambda: http.arcgis(
        PRECINCTS, "StCoFIPS_str IN (%s)" % ",".join("'%s'" % c for c in counties),
        "StCoFIPS_str,CountyName,PrecinctCode,PrecinctName,PrecinctID"))
    fabric = collections.defaultdict(dict)
    names = {}
    for f in sbe["features"]:
        a = f["attributes"]
        fips, code = a["StCoFIPS_str"].strip(), a["PrecinctCode"].strip()
        if code in fabric[fips]:
            fail("precinct %s appears twice in county %s" % (code, fips))
        fabric[fips][code] = esri_shape(f["geometry"])
        names[(fips, code)] = (a.get("PrecinctName") or "").strip()
    fj = fabric[JEFFERSON]
    listed = {c for cs in statute.values() for c in cs}
    missing = sorted(listed - set(fj))
    if missing:
        fail("the statute lists codes today's precinct map does not carry: %s" % missing)
    unlisted = tuple(sorted(set(fj) - listed))
    if unlisted != EXPECT_UNLISTED:
        fail("today's map carries %s that the statute does not list, expected %s — read the "
             "layer and the statute before changing EXPECT_UNLISTED" % (unlisted, EXPECT_UNLISTED))
    print("precincts: Jefferson %d (%d listed, unlisted %s); layer edited %s"
          % (len(fj), len(listed), ", ".join(unlisted), sbe["edited"]))

    # 3. the school districts
    jname, jdistrict = fetch_tiger_district(http, JEFFERSON_DISTRICT, 0)
    aname, anchorage = fetch_tiger_district(http, ANCHORAGE_DISTRICT, 2)
    wit = witnesses(http, statute, fj, jdistrict, anchorage)
    print("witnesses: LOJIC precinct tags agree %d/%d; IoU LOJIC %s, JCPS %s"
          % (wit["lojicPrecincts"]["agree"], len(listed), wit["lojicBoard"]["iou"],
             wit["jcpsMap"]["iou"]))

    # 4. the unlisted precincts' ballots in the 2022 general
    links = {day: http.recap_links(page) for day, page in GENERALS.items()}
    jsheet = http.pdf_text(links["2022-11-08"]["Jefferson"], "g2022-Jefferson.json")
    split = jefferson_split(parse_jefferson(jsheet["text"], EXPECT_UNLISTED))
    for c, s in sorted(split.items()):
        print("  %s: %d ballots in 2022, %d carried the county board race, %d Anchorage's"
              % (c, s["ballots"], s["countyBoard"], s["anchorage"]))

    # 5. the counties drawn from election results
    vtd_doc = http.cached("vtd2020.json", lambda: http.arcgis(
        TIGER_VTD_2020, "STATE='21' AND COUNTY IN (%s)" % ",".join(
            "'%s'" % f[2:] for f in sorted(CANDIDATES.values())), "GEOID,VTD,COUNTY"))
    vtd = collections.defaultdict(dict)
    for f in vtd_doc["features"]:
        a = f["attributes"]
        vtd["21" + a["COUNTY"]][a["VTD"][-4:]] = esri_shape(f["geometry"])
    verdicts = {}
    for name, fips in sorted(CANDIDATES.items()):
        sheets = {}
        for day in GENERALS:
            url = links[day].get(name) or links[day].get(name + " County")
            if not url:
                sheets[day] = None
                continue
            doc = http.pdf_text(url, "g%s-%s.json" % (day[:4], name))
            m, d, y = int(day[5:7]), int(day[8:10]), day[:4]
            dates = y if ("%d/%d/%s" % (m, d, y)) in doc["text"] or ("%02d/%02d/%s" % (m, d, y)) in doc["text"] else ""
            sheets[day] = {"url": url, "text": doc["text"], "dates": dates}
        verdicts[name] = results_county(name, fips, fabric[fips], sheets, vtd[fips])
        print("  %-10s %s — %s" % (name, "DRAWN" if verdicts[name]["drawn"] else "not drawn",
                                   verdicts[name]["why"]))
    drawn = tuple(sorted(n for n, v in verdicts.items() if v["drawn"]))
    if drawn != EXPECT_RESULTS_DRAWN:
        fail("the counties passing every test are %s, expected %s — read why before changing "
             "EXPECT_RESULTS_DRAWN" % (drawn, EXPECT_RESULTS_DRAWN))

    # 6. the board pages the card links
    boards = {}
    for fips, url in sorted(BOARD_PAGES.items()):
        r = http.get(url)
        if "board of education" not in r.text.lower():
            fail("%s does not say Board of Education" % url)
        boards[fips] = url

    # 7. compose
    features, report = [], {"Jefferson": {}, "results": {}}
    jcut = {}
    for d in sorted(statute):
        whole = unary_union([fj[c] for c in statute[d]])
        cut = polygonal(whole.intersection(jdistrict))
        jcut[d] = cut
        report["Jefferson"][d] = {"precincts": len(statute[d]), "km2": round(km2(cut), 3),
                                  "cutAwayKm2": round(km2(whole) - km2(cut), 4),
                                  "parts": len(parts_of(cut))}
        features.append(feature(cut, {
            "key": "%s-%s" % (JEFFERSON, d), "county": "Jefferson", "countyFips": JEFFERSON,
            "board": "Jefferson County Board of Education", "web": boards[JEFFERSON],
            "kind": "division", "division": d, "drawnFrom": "statute", "law": "KRS 160.211",
            "firstElection": FIRST_ELECTION, "precincts": len(statute[d])}))
    # The listed precincts the Census line cuts. The cut takes this ground out
    # of their divisions; both published maps keep it in. Their 2022 ballots
    # are recorded beside it, as the one record of which side their voters
    # were on (the codes may have moved since 2022, which a missing page shows).
    into_anchorage = {}
    for c in sorted(listed):
        a = km2(fj[c].intersection(anchorage))
        if a > 1e-4:
            into_anchorage[c] = {"ha": round(a * 100, 2)}
    cut_pages = parse_jefferson(jsheet["text"], tuple(into_anchorage))
    for c, rec in cut_pages.items():
        into_anchorage[c]["ballots2022"] = rec["ballots"]
        into_anchorage[c]["boardRaces2022"] = [list(r) for r in rec["races"]]
        print("  listed %s: %.2f ha cut at the Census line; 2022: %r ballots, %r"
              % (c, into_anchorage[c]["ha"], rec["ballots"], rec["races"]))
    report["listedIntoAnchorage"] = into_anchorage
    for c in EXPECT_UNLISTED:
        # Shipped whole. KRS 160.211(2) leaves the part of such a precinct in
        # the county district to the county board of elections, and the
        # Census line cannot say where that part is: it puts all but 0.0005
        # km2 of F154 in Anchorage's district, while 72 of F154's 521 ballots
        # in 2022 carried a Jefferson County board race. Cut at that line, the
        # county part would be ten slivers, the widest 1.36 m across. So the card
        # describes the whole precinct, both sides, and places none of it.
        g = fj[c]
        s = split[c]
        report.setdefault("unlisted", {})[c] = {
            "name": names[(JEFFERSON, c)], "km2": round(km2(g), 4),
            "km2InTigerJefferson": round(km2(g.intersection(jdistrict)), 4),
            "km2InTigerAnchorage": round(km2(g.intersection(anchorage)), 4), "ballots2022": s}
        features.append(feature(g, {
            "key": "%s-%s" % (JEFFERSON, c), "county": "Jefferson", "countyFips": JEFFERSON,
            "board": "Jefferson County Board of Education", "web": boards[JEFFERSON],
            "kind": "unplaced", "precinct": c, "km2": round(km2(g), 2),
            "anchorageKm2": round(km2(g.intersection(anchorage)), 2),
            "law": "KRS 160.211", "ballots2022": s["ballots"],
            "countyBoard2022": s["countyBoard"], "anchorage2022": s["anchorage"]}))
    for name in drawn:
        v = verdicts[name]
        fips = v["fips"]
        district_name = "%s County School District" % name
        geoid = tiger_district_named(http, district_name)
        _, district = fetch_tiger_district(http, geoid, 0)
        spill = km2(unary_union(list(fabric[fips].values())).difference(district))
        v["district"] = {"geoid": geoid, "name": district_name,
                         "precinctGroundOutsideKm2": round(spill, 4)}
        by_div = collections.defaultdict(list)
        for c, p in v["placement"].items():
            by_div[p["division"]].append(c)
        for d in sorted(by_div):
            cs = sorted(by_div[d])
            elections = {v["placement"][c]["election"] for c in cs}
            contests = {v["placement"][c]["contest"] for c in cs}
            if len(elections) != 1 or len(contests) != 1:
                fail("%s division %s was read from %r / %r" % (name, d, elections, contests))
            cut = polygonal(unary_union([fabric[fips][c] for c in cs]).intersection(district))
            report["results"].setdefault(name, {})[d] = {
                "precincts": cs, "km2": round(km2(cut), 3), "parts": len(parts_of(cut))}
            features.append(feature(cut, {
                "key": "%s-%s" % (fips, d), "county": name, "countyFips": fips,
                "board": "%s County Board of Education" % name, "web": boards[fips],
                "kind": "division", "division": d, "drawnFrom": "results",
                "election": elections.pop(), "contest": contests.pop(), "precincts": len(cs)}))
    src = {"type": "FeatureCollection", "features": features}
    print("composed %d features" % len(features))
    with open(os.path.join(cache, "composed.geojson"), "w", encoding="utf-8") as fh:
        json.dump(src, fh)  # the exact composition, kept beside the cache for reading

    # 8. simplify once, so a line two features share is one arc
    with tempfile.TemporaryDirectory() as tmp:
        a, b = os.path.join(tmp, "src.geojson"), os.path.join(tmp, "out.geojson")
        with open(a, "w", encoding="utf-8") as fh:
            json.dump(src, fh)
        subprocess.run(["npx", "-y", MAPSHAPER, a, "-simplify", "dp", "keep-shapes",
                        "interval=" + INTERVAL, "-o", "precision=" + PRECISION,
                        "format=geojson", b], check=True, cwd=INSTANCE)
        with open(b, encoding="utf-8") as fh:
            simp = json.load(fh)
    drawn_geo = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": f["properties"], "geometry": f["geometry"]}
        for f in simp["features"]]}
    if len(drawn_geo["features"]) != len(features):
        fail("%d features after simplifying, %d before" % (len(drawn_geo["features"]), len(features)))

    # 9. gates
    worst, over = fidelity(src["features"], drawn_geo["features"])
    print("fidelity: worst %.1f m (ceiling %.0f m)" % (worst, FIDELITY_CEILING_M))
    if over:
        fail("features stray past %.0f m: %s" % (FIDELITY_CEILING_M, over))
    ok, vmsg = validate(src["features"], drawn_geo["features"])
    print("validate: " + vmsg)
    if not ok:
        fail(vmsg)
    lap = overlaps(drawn_geo["features"])
    print("overlaps after simplifying: %s" % (", ".join("%s %.3f m2" % kv for kv in sorted(lap.items()))
                                             or "none"))
    big = {k: v for k, v in lap.items() if v > OVERLAP_CEILING_M2}
    if big:
        fail("drawn features overlap by more than %.0f m2: %r" % (OVERLAP_CEILING_M2, big))
    record = {
        "built": datetime.date.today().isoformat(),
        "sources": {
            "statute": os.path.relpath(STATUTE, REPO), "act": ACT,
            "actLastModified": act.get("lastModified"),
            "precincts": PRECINCTS, "precinctsEdited": sbe["edited"],
            "tigerSchool": TIGER_SCHOOL, "tigerVtd2020": TIGER_VTD_2020,
            "generals": GENERALS, "jefferson2022Sheet": jsheet["url"],
            "jcpsMapPage": JCPS_MAP_PAGE,
        },
        "robots": http.verdicts,
        "statute": {d: statute[d] for d in sorted(statute)},
        "unlisted": list(EXPECT_UNLISTED),
        "witnesses": wit,
        "jefferson": report,
        "candidates": verdicts,
        "boardPages": boards,
        "ringsUnder1m2Dropped": CLEANED,
        "fidelityWorstM": round(worst, 2),
        "validate": vmsg,
        "overlapsM2": lap,
    }
    raw = json.dumps(drawn_geo, separators=(",", ":"), ensure_ascii=False) + "\n"
    problems = check_shipped(json.loads(raw), record)
    agree, lines = agree_with_precincts(json.loads(raw), record)
    problems += agree
    for line in lines:
        print(line)
    if problems:
        fail("; ".join(problems[:10]))
    with open(OUT_FILE, "w", encoding="utf-8") as fh:
        fh.write(raw)
    record["agreement"] = lines
    record["shipped_sha256"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    os.makedirs(os.path.dirname(RECORD), exist_ok=True)
    with open(RECORD, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    print("wrote %s: %d features, %d bytes"
          % (os.path.relpath(OUT_FILE, REPO), len(drawn_geo["features"]), len(raw)))


CLEANED = {}


def feature(geom, props):
    from shapely.geometry import mapping  # noqa: PLC0415
    geom, dropped, area = clean(geom)
    if dropped:
        CLEANED[props["key"]] = {"rings": dropped, "m2": round(area, 4)}
    if geom.is_empty:
        fail("%s has no ground left" % props["key"])
    return {"type": "Feature", "properties": props, "geometry": json.loads(json.dumps(mapping(geom)))}


# ---------- gates on the drawn file ----------
def _rings(geom):
    c = geom.get("coordinates") or []
    if geom.get("type") == "Polygon":
        return c
    if geom.get("type") == "MultiPolygon":
        return [ring for poly in c for ring in poly]
    return []


def _seg_to_m(p, a, b):
    mx = 111320.0 * math.cos(math.radians(p[1]))
    px, py, ax, ay, bx, by = p[0] * mx, p[1] * 111320.0, a[0] * mx, a[1] * 111320.0, b[0] * mx, b[1] * 111320.0
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def fidelity(src_features, drawn_features, cell=0.01):
    """The worst distance from a source vertex to its own feature as drawn:
    how far the true line strays from the line a reader sees."""
    drawn = {f["properties"]["key"]: f for f in drawn_features}
    worst, over = 0.0, []
    for f in src_features:
        d = drawn.get(f["properties"]["key"])
        if d is None:
            over.append(f["properties"]["key"] + " (lost)")
            continue
        idx = {}
        for ring in _rings(d["geometry"]):
            for i in range(len(ring) - 1):
                a, b = ring[i], ring[i + 1]
                for gx in range(int(math.floor(min(a[0], b[0]) / cell)), int(math.floor(max(a[0], b[0]) / cell)) + 1):
                    for gy in range(int(math.floor(min(a[1], b[1]) / cell)), int(math.floor(max(a[1], b[1]) / cell)) + 1):
                        idx.setdefault((gx, gy), []).append((a, b))
        w = 0.0
        every = [s for segs in idx.values() for s in segs]
        for ring in _rings(f["geometry"]):
            for v in ring[:-1]:
                gx, gy = int(math.floor(v[0] / cell)), int(math.floor(v[1] / cell))
                cand = [s for dx in (-1, 0, 1) for dy in (-1, 0, 1) for s in idx.get((gx + dx, gy + dy), ())]
                # nothing drawn within a cell: measure against every segment,
                # so a vertex far from every drawn line counts rather than vanishing
                w = max(w, min(_seg_to_m(v, a, b) for a, b in (cand or every)))
        worst = max(worst, w)
        if w > FIDELITY_CEILING_M:
            over.append("%s %.1f m" % (f["properties"]["key"], w))
    return worst, over


def _model(features):
    return [(f["properties"]["key"], f["geometry"], sp.bbox(f["geometry"])) for f in features]


def _hits(model, pt):
    return [k for k, g, bb in model
            if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3] and sp.point_in_geometry(pt, g)]


def validate(src_features, drawn_features, seed=2026):
    """Points over each county's envelope get the same answer from the drawn
    file as from the exact one at >= 99.5%, and no point is in two features."""
    src, new = _model(src_features), _model(drawn_features)
    rng = random.Random(seed)
    agree = total = overlaps = 0
    for fips in sorted({f["properties"]["countyFips"] for f in drawn_features}):
        bbs = [sp.bbox(f["geometry"]) for f in drawn_features if f["properties"]["countyFips"] == fips]
        bb = [min(b[0] for b in bbs), min(b[1] for b in bbs), max(b[2] for b in bbs), max(b[3] for b in bbs)]
        for _ in range(VALIDATE_SAMPLES):
            pt = (rng.uniform(bb[0], bb[2]), rng.uniform(bb[1], bb[3]))
            s, o = _hits(new, pt), _hits(src, pt)
            overlaps += len(s) > 1
            agree += (s[0] if len(s) == 1 else len(s)) == (o[0] if len(o) == 1 else len(o))
            total += 1
    pct = 100.0 * agree / total
    if overlaps:
        return False, "%d of %d points fell in two features" % (overlaps, total)
    if pct < 99.5:
        return False, "agreement only %.2f%% (need 99.5%%)" % pct
    return True, ("%d/%d (%.2f%%) agreement over the drawn counties' envelopes; no sampled "
                  "point in two features" % (agree, total, pct))


def overlaps(drawn_features):
    """Every pair of drawn features that overlap, in square metres. The
    source pieces do not overlap; where a line cut at the Census boundary runs
    a few metres from a precinct line, the two are separate arcs and can cross
    once each is simplified. A pair over OVERLAP_CEILING_M2 fails the build."""
    from shapely import make_valid  # noqa: PLC0415
    from shapely.geometry import shape  # noqa: PLC0415
    gs = [(f["properties"]["key"], make_valid(shape(f["geometry"]))) for f in drawn_features]
    out = {}
    for i, (ka, a) in enumerate(gs):
        for kb, b in gs[i + 1:]:
            if a.intersects(b):
                g = polygonal(a.intersection(b))
                if not g.is_empty:
                    out["%s/%s" % (ka, kb)] = round(metres(g).area, 3)
    return out


def check_shipped(geo, record):
    """What the file must say, held to the record and to itself, offline."""
    problems = []
    feats = geo.get("features") or []
    keys = [f["properties"].get("key") for f in feats]
    if len(set(keys)) != len(keys):
        problems.append("a key appears twice")
    per = collections.defaultdict(lambda: collections.defaultdict(list))
    for f in feats:
        p = f["properties"]
        per[p.get("countyFips")][p.get("kind")].append(p)
        for field in ("key", "county", "countyFips", "board", "web", "kind"):
            if not p.get(field):
                problems.append("%s has no %s" % (p.get("key"), field))
        if p.get("web") != (record.get("boardPages") or {}).get(p.get("countyFips")):
            problems.append("%s links %r, not the board page the build checked" % (p.get("key"), p.get("web")))
        if p.get("kind") == "division":
            if p.get("drawnFrom") == "statute":
                if p.get("law") != "KRS 160.211" or p.get("firstElection") != FIRST_ELECTION:
                    problems.append("%s does not name the statute and first election" % p.get("key"))
                if p.get("precincts") != len(record["statute"].get(p.get("division")) or []):
                    problems.append("%s counts %r precincts" % (p.get("key"), p.get("precincts")))
            elif p.get("drawnFrom") == "results":
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.get("election") or "") or not p.get("contest"):
                    problems.append("%s carries no election date or contest" % p.get("key"))
            else:
                problems.append("%s is drawn from %r" % (p.get("key"), p.get("drawnFrom")))
        elif p.get("kind") == "unplaced":
            for field in ("precinct", "km2", "anchorageKm2",
                          "ballots2022", "countyBoard2022", "anchorage2022"):
                if p.get(field) in (None, ""):
                    problems.append("%s has no %s" % (p.get("key"), field))
            if (p.get("countyBoard2022") or 0) + (p.get("anchorage2022") or 0) != p.get("ballots2022"):
                problems.append("%s's 2022 ballots do not add up" % p.get("key"))
        else:
            problems.append("%s is of kind %r" % (p.get("key"), p.get("kind")))
    jd = sorted(p["division"] for p in per[JEFFERSON]["division"])
    if jd != ["1", "2", "3", "4", "5"]:
        problems.append("Jefferson's divisions are %s" % jd)
    ju = tuple(sorted(p["precinct"] for p in per[JEFFERSON]["unplaced"]))
    if ju != tuple(record.get("unlisted") or ()):
        problems.append("Jefferson's unplaced precincts are %s, the record's %s" % (ju, record.get("unlisted")))
    drawn = {v["fips"]: n for n, v in (record.get("candidates") or {}).items() if v.get("drawn")}
    for fips in sorted(set(per) - {JEFFERSON}):
        if fips not in drawn:
            problems.append("county %s is drawn and the record does not say it passed" % fips)
            continue
        ds = sorted(p["division"] for p in per[fips]["division"])
        if ds != ["1", "2", "3", "4", "5"] or per[fips]["unplaced"]:
            problems.append("%s carries divisions %s" % (drawn[fips], ds))
        placement = record["candidates"][drawn[fips]]["placement"]
        for p in per[fips]["division"]:
            mine = sorted(c for c, x in placement.items() if x["division"] == p["division"])
            if p.get("precincts") != len(mine):
                problems.append("%s counts %r precincts, the record %d" % (p["key"], p.get("precincts"), len(mine)))
            if {placement[c]["election"] for c in mine} != {p.get("election")}:
                problems.append("%s names election %r" % (p["key"], p.get("election")))
    for fips in drawn:
        if fips not in per:
            problems.append("%s passed every test and is not drawn" % drawn[fips])
    return problems


def agree_with_precincts(geo, record, seed=2027):
    """Points inside each shipped feature, looked up in the SHIPPED precinct
    file: the precinct there must be one the feature is made of (by the
    statute's list, or the record's placement, or the unplaced precinct
    itself). The two files are simplified separately, so they can part within
    a few metres of a line; AGREE_FLOOR is set from the first measured build.
    A change to the precinct file that moves a code fails here."""
    with open(PRECINCT_FILE, encoding="utf-8") as fh:
        pf = json.load(fh)["features"]
    index = sp.Index(pf)
    code_of = {f["properties"]["key"]: f["properties"]["code"] for f in pf}
    statute_div = {c: d for d, cs in record["statute"].items() for c in cs}
    placements = {v["fips"]: v["placement"] for v in (record.get("candidates") or {}).values() if v.get("drawn")}
    rng = random.Random(seed)
    problems, worst, lines = [], [], []
    for f in geo["features"]:
        p = f["properties"]
        g, bb = f["geometry"], sp.bbox(f["geometry"])
        same = other = none = n = tries = 0
        while n < AGREE_POINTS and tries < AGREE_POINTS * 200:
            tries += 1
            pt = (rng.uniform(bb[0], bb[2]), rng.uniform(bb[1], bb[3]))
            if not sp.point_in_geometry(pt, g):
                continue
            n += 1
            hits = [(code_of[k], cf) for k, cf in index.at(pt)]
            if len(hits) != 1:
                none += 1
                continue
            code, cf = hits[0]
            if cf != p["countyFips"]:
                other += 1
            elif p["kind"] == "unplaced":
                same += code == p["precinct"]
                other += code != p["precinct"]
            elif p["drawnFrom"] == "statute":
                same += statute_div.get(code) == p["division"]
                other += statute_div.get(code) != p["division"]
            else:
                want = (placements.get(cf) or {}).get(code, {}).get("division")
                same += want == p["division"]
                other += want != p["division"]
        share = same / float(n) if n else 0.0
        worst.append((share, p["key"], same, other, none, n))
        if not n or share < AGREE_FLOOR:
            problems.append("%s: %d of %d points inside it are in one of its own precincts in "
                            "ky-precincts.json (%d in another, %d in none; floor %.3f)"
                            % (p["key"], same, n, other, none, AGREE_FLOOR))
    worst.sort()
    w = worst[0]
    lines.append("precinct agreement: %d features, %d points each; lowest %.4f (%s: %d own, "
                 "%d other, %d none of %d)" % (len(worst), AGREE_POINTS, w[0], w[1], w[2], w[3], w[4], w[5]))
    # every precinct of each drawn county is still in the precinct file, and no new one
    fabric = collections.defaultdict(set)
    for f in pf:
        fabric[f["properties"]["countyFips"]].add(f["properties"]["code"])
    want_j = set(statute_div) | set(record.get("unlisted") or ())
    if fabric[JEFFERSON] != want_j:
        problems.append("ky-precincts.json's Jefferson codes have changed (new: %s; gone: %s) — "
                        "re-read KRS 160.211 and rebuild" % (
                            sorted(fabric[JEFFERSON] - want_j)[:6], sorted(want_j - fabric[JEFFERSON])[:6]))
    for fips, placement in placements.items():
        if fabric[fips] != set(placement):
            problems.append("ky-precincts.json's codes for county %s are no longer the ones the "
                            "election results placed — rebuild" % fips)
    return problems, lines


def check_card():
    spec = types.SimpleNamespace(tag="ky", instance=INSTANCE, out_file=OUT_NAME,
                                 interval=INTERVAL, card_claims=CARD_CLAIMS)
    return sp.check_card(spec, "school board division card")


def check():
    with open(OUT_FILE, encoding="utf-8") as fh:
        raw = fh.read()
    with open(RECORD, encoding="utf-8") as fh:
        record = json.load(fh)
    geo = json.loads(raw)
    problems = []
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != record.get("shipped_sha256"):
        problems.append("the shipped file does not hash to what the builder recorded; rebuild it "
                        "rather than editing it by hand")
    with open(STATUTE, encoding="utf-8") as fh:
        statute = parse_divisions(fh.read())
    if statute != record.get("statute"):
        problems.append("KRS 160.211 as kept in the repository no longer reads as the build read it")
    problems += check_shipped(geo, record)
    agree, lines = agree_with_precincts(geo, record)
    problems += agree
    problems += check_card()
    for line in lines:
        print(line)
    if problems:
        for p in problems:
            print("build-ky-school-board-divisions: FAIL: " + p)
        raise SystemExit(1)
    by = collections.Counter(f["properties"]["county"] for f in geo["features"]
                             if f["properties"]["kind"] == "division")
    print("build-ky-school-board-divisions --check: OK: %s; %d Jefferson precincts not placed; "
          "matches the record of %s" % (
              ", ".join("%s %d divisions" % kv for kv in sorted(by.items())),
              sum(1 for f in geo["features"] if f["properties"]["kind"] == "unplaced"), record["built"]))


# ---------- self-test ----------
SELFTEST_STATUTE = """160.211 Divisions for the Jefferson County Board of Education.
(1) The divisions ...:
      (a) Division One shall consist of the following territory:
      A101       A102
      (b) Division Two shall consist of the following territory:
      B101
      (c) Division Three shall consist of the following territory:
      C101
      (d) Division Four shall consist of the following territory:
      D101
                                   Legislative Research Commission PDF Version
      (e) Division Five shall consist of the following territory:
      E101
(2)   If any precinct or part of a precinct ...
"""
SELFTEST_SHEET = """
A101                                              248 ballots cast

MEMBER BOARD of EDUCATION 5th Educational District - (Vote for One)
Choice                Party   Absentee Voting    Early Voting   Election Day Voting   Total
Scott DAVISON                    20   100.00%       26   100.00%      111   100.00%    157   100.00%

                    Cast Votes:  20   100.00%       26   100.00%      111   100.00%    157   100.00%

                    Undervotes:  11                 20                 59                90
                     Overvotes:   0                  0                  1                 1
A102                                              10 ballots cast
MAYOR City of Morehead - (Vote for One)
"""
SELFTEST_JEFFERSON = """
F154
Ballots Cast - Total                       521        435       40           4          42          0
  SCHOOL BOARD - DISTRICT 3 District 3
  Vote For 1
  Contest Totals                            72         62       3         0         7          0
  ANCHORAGE SCHOOL BOARD District 3A
  Vote For 3
  Contest Totals                          1,347     1,119      111       12       105          0
"""


def selftest():
    d = parse_divisions(SELFTEST_STATUTE)
    assert d == {"1": ["A101", "A102"], "2": ["B101"], "3": ["C101"], "4": ["D101"], "5": ["E101"]}, d
    try:
        parse_divisions(SELFTEST_STATUTE.replace("B101", "B101 and"))
        raise AssertionError("a word inside a list was read")
    except SystemExit:
        pass
    seen, ballots, races, other = parse_sheet(SELFTEST_SHEET)
    assert seen == {"A101", "A102"} and ballots == {"A101": 248, "A102": 10}, (seen, ballots)
    r = races["A101"][0]
    assert (r["division"], r["cast"], r["under"], r["over"], r["vote_for"]) == ("5", 157, 90, 1, "one"), r
    assert r["contest"] == "MEMBER BOARD of EDUCATION 5th Educational District", r
    assert not other
    s = jefferson_split(parse_jefferson(SELFTEST_JEFFERSON, ("F154",)))
    assert s["F154"]["countyBoard"] == 72 and s["F154"]["anchorage"] == 449, s
    # even-odd: a ring inside a ring is a hole whichever way it winds
    hole = {"rings": [[[0, 0], [0, 4], [4, 4], [4, 0], [0, 0]], [[1, 1], [1, 2], [2, 2], [2, 1], [1, 1]]]}
    g = esri_shape(hole)
    assert abs(g.area - 15.0) < 1e-9, g.area
    hole["rings"][1].reverse()
    assert abs(esri_shape(hole).area - 15.0) < 1e-9
    # the results tests, on a two-precinct county that cannot pass (one division only)
    from shapely.geometry import box  # noqa: PLC0415
    codes = {"A101": box(0, 0, 0.01, 0.01), "A102": box(0.01, 0, 0.02, 0.01)}
    def sheets(text):
        return {"2022-11-08": {"url": "u", "text": text, "dates": "2022"},
                "2024-11-05": {"url": "u", "text": text, "dates": "2024"}}
    rep = results_county("T", "21000", codes, sheets(SELFTEST_SHEET), codes)
    assert not rep["drawn"] and "A102" in rep["why"], rep
    # a race on fewer ballots than the precinct cast: the precinct may be split
    rep = results_county("T", "21000", codes, sheets(SELFTEST_SHEET.replace("248 ballots", "250 ballots")), codes)
    assert not rep["drawn"] and "may be split" in rep["why"], rep
    # a code on the sheet that today's map does not carry
    rep = results_county("T", "21000", {"A101": codes["A101"]}, sheets(SELFTEST_SHEET), codes)
    assert not rep["drawn"] and "not in today's map" in rep["why"], rep
    print("build-ky-school-board-divisions --selftest: OK")


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    ap.add_argument("--check", action="store_true", help="offline: hold the shipped file to its record")
    ap.add_argument("--selftest", action="store_true", help="offline: the parsers and the tests")
    ap.add_argument("--cache", help="keep fetched layers and sheets here (default: a temporary directory)")
    args = ap.parse_args()
    if args.selftest:
        selftest()
    elif args.check:
        check()
    elif args.cache:
        os.makedirs(args.cache, exist_ok=True)
        build(args.cache)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            build(tmp)


if __name__ == "__main__":
    main()
