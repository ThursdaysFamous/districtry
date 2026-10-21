#!/usr/bin/env python3
"""Build two rosters from the Louisiana Secretary of State's list of elected
officials: la/data/app/la-municipal-officials.json, the mayor, the council or
board of aldermen and the chief of police or marshal of every city, town and
village the list names, keyed by the Census Bureau's place GEOID; and
la/data/app/la-school-board-members.json, the members of every school board,
keyed by the Census Bureau's school district GEOID.

THE SOURCE is the one build_la_parish_officials.py reads: the voter portal's
list of offices (https://voterportal.sos.la.gov/ElectedOfficials/Office/Index)
and its CSV export of each. Five offices are read here, by the index's own
names:
  300_0 "Mayor";
  310_0 "Alderman / City Council Member";
  308_0 "Alderman / City Council at Large";
  305_0 "Chief of Police / Marshal";
  255_0 "School Board Member".
Measured 2026-10-20: 299, 1,249, 62, 192 and 639 rows. The index's "Other
Municipal Office" (320_0) is not read. The three parish offices are read too,
for the contact rules below, so a run reads all eight exports: a weekly run
takes the ones the parish builder fetched and kept (--exports).

WHAT IS READ, AND WHAT IS NEVER READ, follows the parish builder, through its
own functions (person_record, office_contacts, contact_book): from each row the
title, the seat, the name, the party, the telephone and the date the term ends,
and never the race or gender the rows also print. A telephone printed for one
official alone ships on that official's row. An address ships only as an
office that at least three of one government's officials print and no
official outside it prints, and a telephone shared that way is the office's.
A town's officials, for this, are its mayor, its council and its chief of
police or marshal; a school board's are its members. On 2026-10-20 the rule
kept no office address for the City of Gonzales or Ascension Parish, because
the five members of Gonzales's council and ten of Ascension Parish's council
members print the same post office box.

A MUNICIPALITY is the list's "City of", "Town of" or "Village of" name, after
the seat where a council member's row names one ("District 2, Town of
Vidalia"). It is joined to the Census Bureau's incorporated place (TIGERweb's
Places_CouSub_ConCity_SubMCD layer 4, which the map draws) by its name,
letters only, and every municipality the list names must match exactly one
place. The two do not always agree about the style: on 2026-10-20 the list
called eight places a town or a village where the Census calls them something
else (Chatham, Clarks, Clayton, Eros, Kaplan, Newellton, St. Joseph and
Waterproof), and its rows call Ridgecrest a town on the mayor's row, as the
Census does, and a village on its aldermen's. The record keeps the list's name, the mayor's
row's where the rows differ, and the card says what the list calls the place
where the Census calls it something else. Three of the Census's 305 places
have no record: New Orleans, whose mayor and council the list names as Orleans
Parish's government; Baton Rouge, whose government is East Baton Rouge
Parish's Metropolitan Council and Mayor-President; and Houma, which has no
government of its own (the Census's FUNCSTAT N).

THE MAYOR. One row per municipality, except that the list printed Sicily
Island's mayor twice on 2026-10-20, once with a term that ended in 2022. A
person listed twice under one office is one record, with the later term,
where the two rows also agree on the telephone or the address (dedupe); two
different people as one town's mayor stop the build. Four municipalities had
no mayor's row that day: Lafayette, whose Mayor-President the list names as
Lafayette Parish's executive, and Clarence, Cullen and Shongaloo, for which
the card says the list names no mayor.

THE COUNCIL. The members' titles say what the body's members are called, and
the record's "kind" carries it: aldermen ("Alderman", "Aldermen"), council
members (every spelling the list uses is in MEMBER_KINDS), selectmen (Homer and
Plaquemine) or
trustees (Jackson's "Member, Board of Trustees"). A municipality whose rows
use two of those stops the build. The seat is the part of the description
before the municipality's name ("District 2", "Ward 1, Division A"; St.
Francisville's "Election Sect. 2" is written "Election Section 2"), except
Mandeville's, whose seats are in the titles ("Council Member I" to "III") and
ship as titled. A member of the at-large office, or one titled at large in
the other (Krotz Springs's five), is "At large", with the description's seat
after it where it gives one ("At large, Division A"). 770 of that office's
1,249 rows name no seat, in 202 municipalities whose rows name none; those
members ship with no seat, and the card does not call them elected at large,
which the list does not say. Vidalia's District 2 and District 3 and
DeQuincy's District 1 were each printed twice that day and are one record
each. Estherwood's two aldermen named Stephen Smith print different addresses
and only one prints a telephone, so they ship as the list prints them, twice.

THE POLICE. The Chief of Police / Marshal office named a chief of police in
185 municipalities and a marshal in five on 2026-10-20, and Bogalusa's one row
in it is its City Prosecutor; each ships under the title the list prints, and
two different people under one title in one town stop the build. Vidalia's
chief was printed twice and is one record.

A SCHOOL BOARD is one of the Census Bureau's 69 school districts (TIGERweb's
School layer 0, which the map draws). A row's description is its seat, with
the city school system after it where the row is one's ("District 1, City of
Monroe", "Dist. 3, Central Comm."); CITY_SYSTEMS names the five, and any other
"City of" suffix stops the build. Every other row belongs to the parish school
system of the row's parish, "<Parish> School District". The build refuses
unless every one of the 69 districts has a board and every row a district.
"Dist." is written "District", and a seat of "At large" or "at Large" is an
at-large seat (Iberville's and West Baton Rouge's). 610 of the 639 members'
terms end on December 31, 2026, and la/WATCH.md says when to read them again.

THE PARTY, THE SKIPPED SEATS AND THE DATE follow the parish builder: the party
as a word ("Other" and any value not in its PARTY_NAMES ship as printed); a
numbered or lettered run of seats that skips one names the skipped seat under
"unlisted"; and each file carries the day the list was read, kept while that
file's records are unchanged. A build from kept exports (--exports, --offline)
takes that day from the record the parish builder's --save keeps beside them,
never from the clock.

ROBOTS. tigerweb.geo.census.gov's policy is read before the first fetch from
it through scraper_common.require_robots_once, with the User-Agent the fetches
send; voterportal.sos.la.gov's is read the same way by the parish builder's
fetch, whichever builder fetches the exports.

Usage:
    python3 la/scripts/build_la_local_officials.py                # fetch everything and write
    python3 la/scripts/build_la_local_officials.py --exports DIR  # the list's exports from DIR
    python3 la/scripts/build_la_local_officials.py --save DIR     # also keep what was fetched
    python3 la/scripts/build_la_local_officials.py --offline DIR  # rebuild from DIR alone
    python3 la/scripts/build_la_local_officials.py --check        # offline: the shipped files
"""

import datetime
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
sys.path.insert(0, HERE)
import build_la_parish_officials as parish  # noqa: E402  (same instance tree)
assert os.path.dirname(os.path.abspath(parish.__file__)) == HERE, parish.__file__
sys.path.append(os.path.join(REPO, "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

USER_AGENT = parish.USER_AGENT
LABEL = "la-build-la-local-officials"
TIGERWEB = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
PLACES_URL = TIGERWEB + "Places_CouSub_ConCity_SubMCD/MapServer/4"
SCHOOLS_URL = TIGERWEB + "School/MapServer/0"
STATE = "22"
CENSUS_FILE = "census-attributes.json"
SOURCE = parish.SOURCE
INDEX_URL = parish.INDEX_URL

MUNI_OUT = os.path.join(INSTANCE, "data", "app", "la-municipal-officials.json")
SCHOOL_OUT = os.path.join(INSTANCE, "data", "app", "la-school-board-members.json")

# Floors catch a truncated export while tolerating a vacancy or two. On
# 2026-10-20: 305 Census places; 302 municipalities, 298 mayors, 1,308 council
# members and aldermen, 191 chiefs, marshals and prosecutors; 69 school boards
# with 639 members.
MIN_PLACES = 300
MIN_MUNICIPALITIES = 290
MIN_MAYORS = 285
MIN_COUNCIL = 1200
MIN_OFFICERS = 175
EXPECTED_SCHOOL_DISTRICTS = 69
MIN_SCHOOL_MEMBERS = 600
MIN_SCHOOL_BOARD = 5     # East Carroll's and the City of Baker's boards have five
# Shares of the people named carrying their own telephone and a party, set
# below the day's measurement so a column going missing fails while a few
# officials starting to print their town hall's number do not. On 2026-10-20:
# 83.9% of town officials and 87.8% of school board members carried their own
# telephone (most of the rest print their town hall's or school board's), and
# 97.3% and 97.8% a party.
MIN_PHONE_SHARE = 0.75
MIN_PARTY_SHARE = 0.9

MUNI_RE = re.compile(r"^(?:(?P<seat>.*?),\s*)?(?P<kind>City|Town|Village) of (?P<name>.+)$")
CENSUS_STYLES = {"25": "City", "43": "Town", "47": "Village"}   # the place's LSADC
MEMBER_KINDS = {
    "Alderman": "aldermen", "Aldermen": "aldermen", "Alderman at Large": "aldermen",
    "Council Member": "council", "Council Member(s)": "council",
    "Councilman": "council", "Councilmember": "council", "City Council Member": "council",
    "Council Member at Large": "council", "Council Member(s) at Large": "council",
    "Councilman at Large": "council", "Councilmen at Large": "council",
    "Selectman": "selectmen",
    "Member, Board of Trustees": "trustees",
}
# Mandeville's three district seats are named in the title, not the description.
SEAT_TITLE_RE = re.compile(r"^Council Member (I|II|III|IV|V|VI)$")
KINDS = {"aldermen", "council", "selectmen", "trustees"}
OFFICER_TITLES = {"Chief of Police", "Marshal", "City Prosecutor"}
# The Central and Zachary boards' rows abbreviate the title.
SCHOOL_TITLES = {"Member of School Board", "Mbr. of School Bd."}
# The five city school systems, as the list's descriptions end, and the
# Census's name for each district.
CITY_SYSTEMS = {
    "Central Comm.": "Central Community School District",
    "Zachary Comm.": "Zachary Community School District",
    "City of Baker": "City of Baker School District",
    "City of Bogalusa": "City of Bogalusa School District",
    "City of Monroe": "City of Monroe School District",
}


# ---------------------------------------------------------------- the Census

def census_get(url, fields):
    params = {"where": "STATE='%s'" % STATE, "outFields": fields,
              "returnGeometry": "false", "f": "json"}
    q = url + "/query?" + urllib.parse.urlencode(params)
    require_robots_once(q, USER_AGENT, headers={"User-Agent": USER_AGENT}, label=LABEL)
    for attempt in range(4):
        try:
            req = urllib.request.Request(q, headers={"User-Agent": USER_AGENT,
                                                     "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, dict) and "error" in data:
                # An ArcGIS error is an object, not an empty answer.
                raise RuntimeError("TIGERweb answered an error: %r" % (data["error"],))
            break
        except Exception as err:  # noqa: BLE001 — retried, then raised
            if attempt == 3:
                raise
            print("local-officials: retrying after %s" % err, file=sys.stderr)
            time.sleep(2 ** (attempt + 1))
    if data.get("exceededTransferLimit"):
        raise SystemExit("FAIL: TIGERweb cut %s's answer short; it needs paging" % url)
    return [f["attributes"] for f in data.get("features") or []]


def read_census(offline=None, save=None):
    if offline:
        path = os.path.join(offline, CENSUS_FILE)
        if not os.path.exists(path):
            raise SystemExit("FAIL: %s has no %s; --save writes it" % (offline, CENSUS_FILE))
        with open(path) as fh:
            data = json.load(fh)
    else:
        data = {"places": census_get(PLACES_URL, "GEOID,NAME,BASENAME,LSADC,FUNCSTAT"),
                "schools": census_get(SCHOOLS_URL, "GEOID,NAME")}
        if save:
            os.makedirs(save, exist_ok=True)
            with open(os.path.join(save, CENSUS_FILE), "w") as fh:
                json.dump(data, fh, indent=1, sort_keys=True)
    if len(data.get("places") or []) < MIN_PLACES:
        raise SystemExit("FAIL: the Census answered %d places for Louisiana, under %d"
                         % (len(data.get("places") or []), MIN_PLACES))
    if len(data.get("schools") or []) != EXPECTED_SCHOOL_DISTRICTS:
        raise SystemExit("FAIL: the Census answered %d school districts for Louisiana, "
                         "expected %d" % (len(data.get("schools") or []),
                                          EXPECTED_SCHOOL_DISTRICTS))
    return data


# ---------------------------------------------------------------- helpers

def term_of(row):
    m = parish.DATE_RE.match(row["ExpDate"] or "")
    return (m.group(3), m.group(1), m.group(2)) if m else ("",)


def dedupe(entries, where, notes):
    """(seat, row) pairs with each person listed twice in one seat kept once,
    with the later term: twice means the same name and the same telephone or
    address, since two rows naming the same name with neither in common may be
    two people."""
    kept = []
    for seat, row in entries:
        twin = None
        for i, (s, r) in enumerate(kept):
            if s == seat and parish.person_key(r) == parish.person_key(row) and (
                    (r["Phone"] and r["Phone"] == row["Phone"]) or
                    (r["Address"] and parish.norm_address(r["Address"]) ==
                     parish.norm_address(row["Address"]))):
                twin = i
                break
        if twin is None:
            kept.append((seat, row))
            continue
        notes.append("%s: the list prints %s%s twice; one record is kept"
                     % (where, parish.person_name(row), " (%s)" % seat if seat else ""))
        if term_of(row) > term_of(kept[twin][1]):
            kept[twin] = (seat, row)
    return kept


def tidy_seat(seat):
    seat = parish.tidy(seat)
    seat = re.sub(r"^Dist\.\s*", "District ", seat)
    return re.sub(r"\bSect\.\s*", "Section ", seat)


def at_large_seat(part):
    if not part or re.fullmatch(r"at large", part, re.I):
        return "At large"
    return "At large, " + tidy_seat(part)


def member_kind(title, where):
    if title in MEMBER_KINDS:
        return MEMBER_KINDS[title]
    if SEAT_TITLE_RE.match(title):
        return "council"
    raise SystemExit("FAIL: %s carries a member titled %r — a new title needs a reading "
                     "in MEMBER_KINDS" % (where, title))


def keep_read(result, previous, today):
    """Unchanged records keep the day they were first read in this form."""
    read = today
    if previous and all(isinstance(v, dict) for v in previous.values()):
        stripped = {k: {f: x for f, x in v.items() if f != "read"} for k, v in previous.items()}
        if stripped == result:
            read = next(iter(previous.values())).get("read") or today
    for rec in result.values():
        rec["read"] = read
    return result


# ---------------------------------------------------------------- towns

def build_municipal(texts, census, book, previous, today):
    notes = []
    places = {}
    for p in census["places"]:
        key = parish.fold(p["BASENAME"])
        if key in places:
            raise SystemExit("FAIL: two Census places fold to %r" % key)
        places[key] = p

    towns = defaultdict(lambda: {"names": Counter(), "mayor_name": None, "mayor": [],
                                 "members": [], "officers": []})
    for office in ("300_0", "310_0", "308_0", "305_0"):
        for row in parish.rows_of(texts[office], office):
            m = MUNI_RE.match(row["OfficeTitleDescription"])
            if not m:
                raise SystemExit("FAIL: office %s carries a row whose description %r names "
                                 "no city, town or village" % (office, row["OfficeTitleDescription"]))
            t = towns[parish.fold(m.group("name"))]
            listed = "%s of %s" % (m.group("kind"), parish.tidy(m.group("name")))
            t["names"][listed] += 1
            title = row["OfficeTitle"]
            if office == "300_0":
                if title != "Mayor" or m.group("seat"):
                    raise SystemExit("FAIL: %s's mayor's row is titled %r for %r"
                                     % (listed, title, row["OfficeTitleDescription"]))
                t["mayor"].append((None, row))
                t["mayor_name"] = listed
            elif office == "305_0":
                if title not in OFFICER_TITLES or m.group("seat"):
                    raise SystemExit("FAIL: %s's row in the police office is titled %r — a "
                                     "new title needs a reading in OFFICER_TITLES" % (listed, title))
                t["officers"].append((title, row))
            else:
                t["members"].append((office, row, m.group("seat")))

    result = {}
    for key, t in sorted(towns.items()):
        name = t["mayor_name"] or t["names"].most_common(1)[0][0]
        if len(t["names"]) > 1:
            notes.append("%s: the list's rows write its name %s; the record keeps %r"
                         % (name, " and ".join(sorted(t["names"])), name))
        place = places.get(key)
        if not place:
            raise SystemExit("FAIL: the list names %s, which matches no Census place" % name)
        style = CENSUS_STYLES.get(str(place.get("LSADC")))
        if style and not name.startswith(style + " of "):
            notes.append("%s: the Census calls it %s" % (name, place["NAME"]))

        mayors = dedupe(t["mayor"], name + " mayor", notes)
        if len(mayors) > 1:
            raise SystemExit("FAIL: the list names %d mayors for %s" % (len(mayors), name))

        kinds, seats, at_large, plain = set(), [], [], []
        for office, row, part in t["members"]:
            title = row["OfficeTitle"]
            kinds.add(member_kind(title, name))
            if office == "308_0" or re.search(r"\bat large\b", title, re.I):
                at_large.append((at_large_seat(part), row))
            elif SEAT_TITLE_RE.match(title):
                if part:
                    raise SystemExit("FAIL: %s's %r row also names the seat %r"
                                     % (name, title, part))
                seats.append((title, row))
            elif part:
                seats.append((tidy_seat(part), row))
            else:
                plain.append((None, row))
        if len(kinds) > 1:
            raise SystemExit("FAIL: %s's members carry titles of %d kinds: %s"
                             % (name, len(kinds), sorted(kinds)))
        if seats and plain:
            notes.append("%s: the list gives a seat for %d members and none for %d"
                         % (name, len(seats), len(plain)))
        seats = dedupe(seats, name, notes)
        at_large = dedupe(at_large, name, notes)
        plain = dedupe(plain, name, notes)

        by_title = defaultdict(list)
        for title, row in t["officers"]:
            by_title[title].append((None, row))
        officers = []
        for title in sorted(by_title):
            kept = dedupe(by_title[title], "%s %s" % (name, title), notes)
            if len(kept) > 1:
                raise SystemExit("FAIL: the list names %d people as %s's %s"
                                 % (len(kept), name, title))
            officers.append((title, kept[0][1]))

        rec = {"municipality": name}
        if kinds:
            rec["kind"] = kinds.pop()
        if mayors:
            rec["mayor"] = parish.person_record(mayors[0][1], None, name + " mayor", book, notes)
        if seats:
            rec["seats"] = [parish.person_record(r, s, "%s %s" % (name, s), book, notes)
                            for s, r in seats]
        if at_large:
            rec["atLarge"] = [parish.person_record(r, s, "%s %s" % (name, s), book, notes)
                              for s, r in at_large]
        if plain:
            rec["members"] = [parish.person_record(r, None, name + " member", book, notes)
                              for _, r in plain]
        skipped = parish.unlisted_seats([s for s, _ in seats])
        if skipped:
            rec["unlisted"] = skipped
            notes.append("%s: the list names no one for %s" % (name, ", ".join(skipped)))
        if officers:
            rec["officers"] = []
            for title, row in officers:
                person = parish.person_record(row, None, "%s %s" % (name, title), book, notes)
                person["title"] = title
                rec["officers"].append(person)
        rows = ([r for _, r in mayors] + [r for _, r in seats + at_large + plain] +
                [r for _, r in officers])
        address, phone = parish.office_contacts(rows, book, name, notes)
        if address:
            rec["officeAddress"] = address
        if phone:
            rec["officePhone"] = phone
        rec.update({"source": SOURCE, "sourceUrl": INDEX_URL})
        result[str(place["GEOID"])] = rec

    named = {str(places[k]["GEOID"]) for k in towns}
    for p in sorted(census["places"], key=lambda p: p["NAME"]):
        if str(p["GEOID"]) not in named:
            notes.append("the list names no officials for %s (the Census's FUNCSTAT %s)"
                         % (p["NAME"], p.get("FUNCSTAT")))
    return keep_read(result, previous, today), notes


# ---------------------------------------------------------------- school boards

def build_schools(texts, census, book, previous, today):
    notes = []
    parishes = parish.load_parishes()
    districts = {}
    for d in census["schools"]:
        key = parish.fold(d["NAME"])
        if key in districts:
            raise SystemExit("FAIL: two Census school districts fold to %r" % key)
        districts[key] = d
    boards = defaultdict(list)
    for row in parish.rows_of(texts["255_0"], "255_0"):
        if row["OfficeTitle"] not in SCHOOL_TITLES:
            raise SystemExit("FAIL: a school board member's row is titled %r (%s)"
                             % (row["OfficeTitle"], row["Parish"]))
        desc = row["OfficeTitleDescription"]
        head, comma, tail = desc.rpartition(",")
        tail = tail.strip()
        if comma and tail in CITY_SYSTEMS:
            district, seat = CITY_SYSTEMS[tail], head
        elif comma and tail.startswith("City of"):
            raise SystemExit("FAIL: a school board row names a city system %r that "
                             "CITY_SYSTEMS does not" % tail)
        else:
            home = parishes.get(parish.fold(row["Parish"]))
            if not home:
                raise SystemExit("FAIL: a school board row names a parish %r that matches "
                                 "no Census parish" % row["Parish"])
            district, seat = home[1] + " School District", desc
        found = districts.get(parish.fold(district))
        if not found:
            raise SystemExit("FAIL: the list's %r matches no Census school district" % district)
        boards[str(found["GEOID"])].append((tidy_seat(seat), row))
    missing = {str(d["GEOID"]) for d in census["schools"]} - set(boards)
    if missing:
        raise SystemExit("FAIL: the list names no school board for %s"
                         % sorted(d["NAME"] for d in census["schools"]
                                  if str(d["GEOID"]) in missing))

    by_geoid = {str(d["GEOID"]): d for d in census["schools"]}
    result = {}
    for geoid in sorted(boards):
        name = by_geoid[geoid]["NAME"]
        entries = dedupe(boards[geoid], name, notes)
        seats, at_large = [], []
        for seat, row in entries:
            if not seat:
                raise SystemExit("FAIL: a member of %s's board names no seat" % name)
            if re.fullmatch(r"at large", seat, re.I):
                at_large.append(("At large", row))
            else:
                seats.append((seat, row))
        rec = {"district": name,
               "seats": [parish.person_record(r, s, "%s %s" % (name, s), book, notes)
                         for s, r in seats]}
        if at_large:
            rec["atLarge"] = [parish.person_record(r, s, "%s %s" % (name, s), book, notes)
                              for s, r in at_large]
        skipped = parish.unlisted_seats([s for s, _ in seats])
        if skipped:
            rec["unlisted"] = skipped
            notes.append("%s: the list names no one for %s" % (name, ", ".join(skipped)))
        address, phone = parish.office_contacts([r for _, r in entries], book, name, notes)
        if address:
            rec["officeAddress"] = address
        if phone:
            rec["officePhone"] = phone
        rec.update({"source": SOURCE, "sourceUrl": INDEX_URL})
        result[geoid] = rec
    return keep_read(result, previous, today), notes


# ---------------------------------------------------------------- gates

MUNI_FIELDS = {"municipality", "kind", "mayor", "seats", "atLarge", "members", "unlisted",
               "officers", "officeAddress", "officePhone", "source", "sourceUrl", "read"}
SCHOOL_FIELDS = {"district", "seats", "atLarge", "unlisted", "officeAddress",
                 "officePhone", "source", "sourceUrl", "read"}
PERSON = {"seat", "name", "party", "phone", "termEnds"}
ISO = re.compile(r"\d{4}-\d{2}-\d{2}")


def check_person(p, where, problems, seat, title=False):
    allowed = (PERSON | {"title"} if title else PERSON) - (set() if seat else {"seat"})
    if set(p) - allowed:
        problems.append("%s: a person carries %s" % (where, sorted(set(p) - allowed)))
    if not parish.readable_name(p.get("name")):
        problems.append("%s: a person with no readable name" % where)
    if seat and not p.get("seat"):
        problems.append("%s: a member with no seat" % where)
    if title and p.get("title") not in OFFICER_TITLES:
        problems.append("%s: an officer titled %r" % (where, p.get("title")))
    if p.get("phone") and (not parish.PHONE_RE.match(p["phone"]) or
                           parish.placeholder_phone(p["phone"])):
        problems.append("%s: telephone %r" % (where, p["phone"]))
    if p.get("termEnds") and not ISO.fullmatch(p["termEnds"]):
        problems.append("%s: term %r" % (where, p["termEnds"]))


def check_office(rec, people, where, problems):
    if rec.get("officePhone") and (not parish.PHONE_RE.match(rec["officePhone"]) or
                                   parish.placeholder_phone(rec["officePhone"])):
        problems.append("%s: office telephone %r" % (where, rec["officePhone"]))
    if rec.get("officePhone") and rec["officePhone"] in {p.get("phone") for p in people}:
        problems.append("%s: the office's telephone also rides an official's row" % where)
    if parish.shared_own_phones(people):
        problems.append("%s: one telephone rides two officials' rows" % where)
    if not ISO.fullmatch(str(rec.get("read") or "")):
        problems.append("%s: read %r" % (where, rec.get("read")))


def shares(people):
    n = len(people)
    return (sum(1 for p in people if p.get("phone")) / n if n else 0,
            sum(1 for p in people if p.get("party")) / n if n else 0)


def check_municipal(data):
    problems = []
    counts = Counter()
    everyone = []
    for geoid, rec in sorted(data.items()):
        where = "%s %s" % (geoid, rec.get("municipality"))
        if not re.fullmatch(r"22\d{5}", geoid):
            problems.append("%s: not a Louisiana place GEOID" % where)
        if set(rec) - MUNI_FIELDS:
            problems.append("%s carries %s" % (where, sorted(set(rec) - MUNI_FIELDS)))
        if not MUNI_RE.fullmatch(str(rec.get("municipality") or "")) or \
                MUNI_RE.match(rec["municipality"]).group("seat"):
            problems.append("%s: municipality %r" % (where, rec.get("municipality")))
        members = list(rec.get("seats") or []) + list(rec.get("atLarge") or []) + \
            list(rec.get("members") or [])
        if members and rec.get("kind") not in KINDS:
            problems.append("%s: kind %r" % (where, rec.get("kind")))
        for p in rec.get("seats") or []:
            check_person(p, where, problems, seat=True)
        for p in rec.get("atLarge") or []:
            check_person(p, where, problems, seat=True)
            if not str(p.get("seat") or "").startswith("At large"):
                problems.append("%s: an at-large seat %r" % (where, p.get("seat")))
        for p in rec.get("members") or []:
            check_person(p, where, problems, seat=False)
        people = list(members)
        if rec.get("mayor"):
            check_person(rec["mayor"], where + " mayor", problems, seat=False)
            people.append(rec["mayor"])
            counts["mayors"] += 1
        for p in rec.get("officers") or []:
            check_person(p, where, problems, seat=False, title=True)
            people.append(p)
            counts["officers"] += 1
        if not people:
            problems.append("%s names nobody" % where)
        check_office(rec, people, where, problems)
        counts["council"] += len(members)
        everyone.extend(people)
    if len(data) < MIN_MUNICIPALITIES:
        problems.append("%d municipalities, floor %d" % (len(data), MIN_MUNICIPALITIES))
    for what, floor in (("mayors", MIN_MAYORS), ("council", MIN_COUNCIL),
                        ("officers", MIN_OFFICERS)):
        if counts[what] < floor:
            problems.append("%d %s, floor %d" % (counts[what], what, floor))
    phone, party = shares(everyone)
    if phone < MIN_PHONE_SHARE:
        problems.append("%.1f%% of town officials carry a telephone, under %.0f%%"
                        % (100 * phone, 100 * MIN_PHONE_SHARE))
    if party < MIN_PARTY_SHARE:
        problems.append("%.1f%% of town officials carry a party, under %.0f%%"
                        % (100 * party, 100 * MIN_PARTY_SHARE))
    return problems, counts, phone


def check_schools(data):
    problems = []
    everyone = []
    if len(data) != EXPECTED_SCHOOL_DISTRICTS:
        problems.append("%d school boards, expected %d" % (len(data), EXPECTED_SCHOOL_DISTRICTS))
    for geoid, rec in sorted(data.items()):
        where = "%s %s" % (geoid, rec.get("district"))
        if not re.fullmatch(r"22\d{5}", geoid):
            problems.append("%s: not a Louisiana school district GEOID" % where)
        if set(rec) - SCHOOL_FIELDS:
            problems.append("%s carries %s" % (where, sorted(set(rec) - SCHOOL_FIELDS)))
        if not str(rec.get("district") or "").endswith("School District"):
            problems.append("%s: district %r" % (where, rec.get("district")))
        people = list(rec.get("seats") or []) + list(rec.get("atLarge") or [])
        for p in people:
            check_person(p, where, problems, seat=True)
        if len(people) < MIN_SCHOOL_BOARD:
            problems.append("%s: %d members, fewer than %d" % (where, len(people), MIN_SCHOOL_BOARD))
        check_office(rec, people, where, problems)
        everyone.extend(people)
    if len(everyone) < MIN_SCHOOL_MEMBERS:
        problems.append("%d school board members, floor %d" % (len(everyone), MIN_SCHOOL_MEMBERS))
    phone, party = shares(everyone)
    if phone < MIN_PHONE_SHARE:
        problems.append("%.1f%% of school board members carry a telephone, under %.0f%%"
                        % (100 * phone, 100 * MIN_PHONE_SHARE))
    if party < MIN_PARTY_SHARE:
        problems.append("%.1f%% of school board members carry a party, under %.0f%%"
                        % (100 * party, 100 * MIN_PARTY_SHARE))
    return problems, len(everyone), phone


# ---------------------------------------------------------------- main

def load(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def summary(munis, schools):
    mp, mc, mphone = check_municipal(munis)
    sp, members, sphone = check_schools(schools)
    return mp + sp, ("%d municipalities (%d mayors, %d council members and aldermen, %d "
                     "chiefs, marshals and prosecutors; %.0f%% of their officials with "
                     "their own telephone) and %d school boards (%d members, %.0f%% with "
                     "their own telephone)"
                     % (len(munis), mc["mayors"], mc["council"], mc["officers"],
                        100 * mphone, len(schools), members, 100 * sphone))


def main(argv):
    args = list(argv)

    def value(flag):
        return args[args.index(flag) + 1] if flag in args else None

    if "--check" in args:
        problems, text = summary(load(MUNI_OUT), load(SCHOOL_OUT))
        if problems:
            for p in problems:
                print("FAIL: " + p)
            return 1
        print("OK: %s and %s — %s" % (os.path.relpath(MUNI_OUT, REPO),
                                     os.path.relpath(SCHOOL_OUT, REPO), text))
        return 0
    offline, exports, save = value("--offline"), value("--exports"), value("--save")
    texts = parish.read_exports(offline=offline or exports,
                                save=None if (offline or exports) else save)
    census = read_census(offline=offline, save=save)
    book = parish.contact_book(texts)
    # The day the list was read: kept exports carry it (the parish builder's
    # --save writes it), so a rebuild from them never stamps a later day.
    kept = offline or exports
    today = parish.read_date(kept) if kept else datetime.date.today().isoformat()
    munis, mnotes = build_municipal(texts, census, book, load(MUNI_OUT), today)
    schools, snotes = build_schools(texts, census, book, load(SCHOOL_OUT), today)
    problems, text = summary(munis, schools)
    if problems:
        for p in problems:
            print("FAIL: " + p)
        return 1
    for path, data in ((MUNI_OUT, munis), (SCHOOL_OUT, schools)):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1, ensure_ascii=False, sort_keys=True)
            fh.write("\n")
    print("Wrote %s and %s: %s" % (os.path.relpath(MUNI_OUT, REPO),
                                  os.path.relpath(SCHOOL_OUT, REPO), text))
    for n in mnotes + snotes:
        print("  " + n)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
