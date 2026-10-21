#!/usr/bin/env python3
"""Build la/data/app/la-parish-officials.json: the elected governing body of
every Louisiana parish, seat by seat, and the parish president or mayor where
the parish elects one, from the Secretary of State's list of elected officials.

WHAT A LOUISIANA PARISH ELECTS. Every one of the 64 parishes is governed by a
body whose members are elected from districts. In 38 parishes it is a police
jury, whose members are police jurors; Caddo's is the Parish Commission; and
the other 25 are parish councils, under home-rule charters, three of which
are also a city's government: the New Orleans City Council for Orleans
Parish, the Metropolitan Council for East Baton Rouge Parish and the City of
Baton Rouge, and Terrebonne's. Seven councils also elect some members at
large (Jefferson, Orleans, St. Bernard, St. Charles, St. John the Baptist, St.
Mary and West Feliciana; St. Mary three, West Feliciana one and the rest two).
Every council parish elects an executive too: twenty-two a parish president,
Lafayette and East Baton Rouge a mayor-president, and Orleans the Mayor of New
Orleans. A police jury elects
its own president from among its members, which the Secretary of State's list
does not record, so no police jury's president is named.

THE SOURCE. The Secretary of State's voter portal lists every elected
official by office at https://voterportal.sos.la.gov/ElectedOfficials/Office/Index
and offers each office's list as a CSV export. Three are read:
  245_0 "Police Juror": every parish governing body's district members, and
        St. Mary's and West Feliciana's at-large members (the office group
        holds councils and the commission as well as police juries; its
        OfficeTitle column says which: "Police Juror", "Parish Commission
        Member", or one of six ways of writing a council member);
  244_0 "Councilman at Large": the at-large members of the other five
        councils that elect them;
  243_0 "Parish President": the parish presidents, both mayor-presidents
        and the Mayor of New Orleans.
Measured 2026-10-20: 563 rows, 10 and 25, covering all 64 parishes. The
list's five other offices that a city, town, village or school board elects
are read too (LOCAL_OFFICES), and so are its three judicial offices whose
judges are elected by district (JUDGE_OFFICES: the Supreme Court, the courts
of appeal and the district courts), only to learn who prints each telephone
and address; build_la_local_officials.py and build_la_judges.py build their
own rosters from the same exports.

WHAT IS READ, AND WHAT IS NEVER READ. From each row: the office title and its
description (the seat), the name, the telephone, the party and the date the
term ends. Each row also prints a mailing address and the official's race and
gender. The race and gender are never read. An address is never carried for
any one official, because some are homes (St. Mary's members print their own
street addresses); the only address that ships is a body's office, kept where
at least three of the parish government's officials (its members and its
executive) print the same one (SHARED_BY), because three people do not share a
home. On 2026-10-20 that held for 16 parishes, and for one of them the address
is wrong: Tensas Parish's seven police jurors all print "701 Murray Street" in
St. Joseph, the street address Rapides Parish's police jurors print in
Alexandria. So an address any official outside the body also prints is
carried for neither body, and the run says so. "Outside the body" is measured
across all eleven offices read (contact_book): a post office box by
the box and its town, since two towns' post offices number their boxes alike,
and a street address by its street line alone, which is what catches Tensas's.
On 2026-10-20 that rule also left out Ascension Parish's office (P.O. Box 1659,
Gonzales), which ten of its eleven council members print and so do all five
members of the City of Gonzales's council, so 13 parishes carry an office
address.

A TELEPHONE printed for one official alone ships on that official's row, under
Adam's fleet ruling of 2026-10-17 ("if the official government source uses
personal phone numbers, we publish those"). One printed for two or more
officials is an office's and ships on no row: where at least three of one
body's officials print it and nobody outside the body does, it is the body's
office telephone (St. Landry's thirteen council members all print the parish
government's number, measured 2026-10-20), and otherwise it is carried
nowhere, since it cannot be told whose it is (two St. Tammany council members,
that day). An official is told apart from another by the name the list prints,
letters only, so one person listed twice is one official and a number they
print on both rows is still theirs alone. A number whose area code or exchange
is 555 is a placeholder rather than anyone's telephone, and is carried
nowhere: one Ascension police juror's row printed one on 2026-10-20, as did
three rows in the list's municipal offices.

THE SEAT is the row's description with its spacing tidied ("District  1" is
"District 1"): districts are numbered or lettered, Concordia's carry a place
("District 1, Place A"), Assumption's are wards, and East Baton Rouge's are
"Metro District" 1 to 12. Cameron's police jury elects two members from
District 4, and both are listed under it. An at-large member's seat is "At
large", with the description after it where the list gives one ("At large,
Division A"), except that St. Mary's three and West Feliciana's one are
printed with the description of a district (St. Mary's "District 9" to
"District 11", West Feliciana's "District E") and titled at large; the title
is believed, because a member elected parish-wide has no district a reader
could live in. Where a parish's districts are numbered 1 to N, or lettered,
and the list skips one, the record names the skipped seat under "unlisted":
on 2026-10-20 Avoyelles's list ran 1-3 and 5-9 and LaSalle's 1-4 and 6-10, and
the card says the list names no one for District 4 and District 5 rather than
calling the seats vacant, which the list does not say.

THE PARTY is printed as a word; "Democrat" is written "Democratic" and "No
Party" "No party", and a value not in PARTY_NAMES ships as printed. Five rows
printed none that day, and a row that prints no telephone or term carries none.

THE BODY'S NAME is built from the office title: "Police Juror" rows are the
<Parish> Police Jury, "Parish Commission Member" the <Parish> Commission, and
every council title the <Parish> Council, except Orleans's New Orleans City
Council and East Baton Rouge's Metropolitan Council (BODY_OVERRIDES). A
parish whose rows use two kinds of title stops the build.

THE PARISH is the list's name in capitals ("DESOTO", "ST. JOHN THE BAPTIST")
matched to the Census Bureau's parish ("De Soto", "St. John the Baptist") with
every character but the letters removed, and every one of the 64 must match
exactly one row group.

ROBOTS. voterportal.sos.la.gov answers /robots.txt with a policy whose one
group, User-agent *, disallows six paths (election results data, candidate
inquiry, sample ballots and parish print pages) and nothing under
/ElectedOfficials/ (read 2026-10-20). Its policy is read before the first
fetch through scraper_common.require_robots_once, with the same User-Agent the
fetches send. www.sos.la.gov and electionstatistics.sos.la.gov disallow every
path to every client, and neither is read. The host serves its whole
certificate chain.

THE DATE. The list is the Secretary of State's live record rather than a dated
edition, so the file carries the day it was read. A weekly run whose records
are unchanged keeps the previous day, so the file changes only when a record
does. --save writes that day beside the exports (READ_FILE), and a build from
kept exports takes it from there, never from the clock: until 2026-10-21 a
rebuild from exports kept overnight stamped every record with the day of the
rebuild, a day nobody read the list.

Usage:
    python3 la/scripts/build_la_parish_officials.py              # fetch and write
    python3 la/scripts/build_la_parish_officials.py --save DIR    # also keep the exports
    python3 la/scripts/build_la_parish_officials.py --offline DIR # rebuild from kept exports
    python3 la/scripts/build_la_parish_officials.py --check       # offline: the shipped file
"""

import csv
import datetime
import io
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
sys.path.insert(0, os.path.join(REPO, "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)
from validate_officeholder_names import why_not_a_name  # noqa: E402  (FLEET_SHARED: one reader of a name)

USER_AGENT = "districtry/1.0 (+https://districtry.com/la/)"
INDEX_URL = "https://voterportal.sos.la.gov/ElectedOfficials/Office/Index"
EXPORT_URL = "https://voterportal.sos.la.gov/ElectedOfficials/Office/Export?officeId=%s"
OFFICES = ("245_0", "244_0", "243_0")
# Mayor; Alderman / City Council Member; Alderman / City Council at Large;
# Chief of Police / Marshal; School Board Member (the index's own names).
LOCAL_OFFICES = ("300_0", "310_0", "308_0", "305_0", "255_0")
# Justice of the Supreme Court; Judge of a Court of Appeal; District Judge
# (the index's own names), which build_la_judges.py names.
JUDGE_OFFICES = ("150_1", "155_1", "210_1")
ALL_OFFICES = OFFICES + LOCAL_OFFICES + JUDGE_OFFICES
SOURCE = "the Louisiana Secretary of State's list of elected officials"

OUT = os.path.join(INSTANCE, "data", "app", "la-parish-officials.json")
COUNTIES = os.path.join(INSTANCE, "data", "app", "state-counties.json")

EXPECTED_PARISHES = 64
# Floors catch a truncated export while tolerating a vacancy or two: 573
# members and 25 executives on 2026-10-20.
MIN_MEMBERS = 550
MIN_EXECUTIVES = 22
MIN_BODY = 5          # the smallest bodies (East Carroll, Madison...) have five
SHARED_BY = 3
# A field nearly every row carries going missing is the Brown County shape: the
# row count holds and the contact goes. 569 of 573 printed a telephone and 568
# a party that day.
MIN_PHONE_SHARE = 0.9
MIN_PARTY_SHARE = 0.9
PACE_SECONDS = 2.0
ATTEMPTS = 3
RETRY_SECONDS = 5.0

COLUMNS = ["OfficeTitle", "OfficeTitleDescription", "FirstName", "LastName", "Suffix",
           "Address", "City", "State", "Zip", "Phone", "Party", "Race", "Gender",
           "ExpDate", "Parish"]
# What kind of body each member's office title makes. The card words its
# members from the kind ("police juror", "council member"), so no title ships.
MEMBER_TITLES = {
    "Police Juror": "police-jury",
    "Parish Commission Member": "commission",
    "Council Member": "council",
    "Councilman": "council",
    "Councilmember": "council",
    "Parish Council Member": "council",
    "Member of Parish Council": "council",
}
AT_LARGE_TITLES = {"Council Member at Large", "Councilman at Large",
                   "Councilmember at Large"}
EXECUTIVE_TITLES = {"Parish President", "Mayor-President", "Mayor"}
BODY_SUFFIX = {"police-jury": "Police Jury", "commission": "Commission",
               "council": "Council"}
# The two bodies that are not called "<Parish> Council" (docstring).
BODY_OVERRIDES = {"Orleans Parish": "New Orleans City Council",
                  "East Baton Rouge Parish": "Metropolitan Council"}
PARTY_NAMES = {"Republican": "Republican", "Democrat": "Democratic",
               "Democratic": "Democratic", "Independent": "Independent",
               "Libertarian": "Libertarian", "No Party": "No party"}

PHONE_RE = re.compile(r"^\((\d{3})\) (\d{3})-(\d{4})$")
DATE_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
DATE_ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
SEAT_RE = re.compile(r"^(District|Ward|Metro District) ([0-9]+|[A-Z])$")

_LAST = [0.0]


def fetch(url):
    import requests

    require_robots_once(url, USER_AGENT, label="la-build-la-parish-officials")
    wait = PACE_SECONDS - (time.time() - _LAST[0])
    if wait > 0:
        time.sleep(wait)
    last = None
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_SECONDS * attempt)
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
            _LAST[0] = time.time()
            resp.raise_for_status()
            return resp.content.decode("utf-8-sig")
        except requests.RequestException as exc:  # reset, timeout, 5xx
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (url, ATTEMPTS, last))


READ_FILE = "read.txt"


def read_date(directory):
    """The day the exports kept in `directory` were read, as --save wrote it."""
    path = os.path.join(directory, READ_FILE)
    try:
        with open(path) as fh:
            day = fh.read().strip()
    except OSError:
        raise SystemExit("FAIL: %s has no %s, so the day its exports were read is not "
                         "known; --save writes it" % (directory, READ_FILE))
    if not DATE_ISO_RE.fullmatch(day):
        raise SystemExit("FAIL: %s says %r, not a date" % (path, day))
    return day


def read_exports(offline=None, save=None):
    """Every office's CSV, from the portal or from a directory --save wrote."""
    texts = {}
    for office in ALL_OFFICES:
        name = "office_%s.csv" % office
        if offline:
            path = os.path.join(offline, name)
            if not os.path.exists(path):
                raise SystemExit("FAIL: %s has no %s; a build from kept exports needs "
                                 "all %d offices (--save keeps them)"
                                 % (offline, name, len(ALL_OFFICES)))
            with open(path, encoding="utf-8-sig") as fh:
                texts[office] = fh.read()
            continue
        texts[office] = fetch(EXPORT_URL % office)
        if save:
            os.makedirs(save, exist_ok=True)
            with open(os.path.join(save, name), "w", encoding="utf-8") as fh:
                fh.write(texts[office])
    if save and not offline:
        with open(os.path.join(save, READ_FILE), "w") as fh:
            fh.write(datetime.date.today().isoformat() + "\n")
    return texts


def tidy(value):
    return re.sub(r"\s+", " ", value or "").strip()


def rows_of(text, office):
    reader = csv.DictReader(io.StringIO(text))
    # The export's last header is "Parish " with a trailing space.
    header = [tidy(h) for h in (reader.fieldnames or [])]
    if header != COLUMNS:
        raise SystemExit("FAIL: office %s's export has columns %r, expected %r — the "
                         "export changed" % (office, header, COLUMNS))
    rows = []
    for raw in reader:
        rows.append({tidy(k): tidy(v) for k, v in raw.items()})
    if not rows:
        raise SystemExit("FAIL: office %s's export is empty" % office)
    return rows


def fold(name):
    """'ST. JOHN THE BAPTIST' and 'St. John the Baptist' alike: letters only."""
    return re.sub(r"[^A-Z]", "", (name or "").upper())


def load_parishes():
    with open(COUNTIES) as fh:
        feats = json.load(fh)["features"]
    out = {}
    for feat in feats:
        p = feat["properties"]
        key = fold(p["BASENAME"])
        if key in out:
            raise SystemExit("FAIL: two parishes fold to %r" % key)
        out[key] = (str(p["GEOID"]), p["NAME"])
    if len(out) != EXPECTED_PARISHES:
        raise SystemExit("state-counties.json carries %d parishes, expected %d"
                         % (len(out), EXPECTED_PARISHES))
    return out


DIGIT_NICKNAME_RE = re.compile(r"(['\"])[^'\"]*\d[^'\"]*\1")


def person_name(row):
    """First name, last name and suffix as the list prints them, less a quoted
    nickname with a digit in it: the fleet's name gate reads a digit in a name
    as a row number welded on, and the name without the nickname is still the
    official's name. One row in the eight exports read on 2026-10-20 carried
    one; every other nickname ships as printed."""
    first = DIGIT_NICKNAME_RE.sub(" ", row["FirstName"])
    return tidy(" ".join(x for x in (first, row["LastName"], row["Suffix"]) if x))


def nickname_dropped(row):
    return bool(DIGIT_NICKNAME_RE.search(row["FirstName"]))


def iso_date(raw, where):
    if not raw:
        return None
    m = DATE_RE.match(raw)
    if not m:
        raise SystemExit("FAIL: %s's term ends %r, not a date" % (where, raw))
    month, day, year = m.groups()
    return "%s-%s-%s" % (year, month, day)


def placeholder_phone(raw):
    """A number whose area code or exchange is 555 is nobody's telephone."""
    m = PHONE_RE.match(raw or "")
    return bool(m) and "555" in (m.group(1), m.group(2))


def phone_digits(raw):
    """The digits of a printed telephone that is one real number, else ''."""
    if not raw or not PHONE_RE.match(raw) or placeholder_phone(raw):
        return ""
    return re.sub(r"\D", "", raw)


def phone_of(raw, where, notes):
    if not raw:
        return None
    if placeholder_phone(raw):
        notes.append("%s: the telephone printed is a placeholder (a 555 area code "
                     "or exchange), so none is carried" % where)
        return None
    if PHONE_RE.match(raw):
        return raw
    notes.append("%s: the telephone is not printed as one number, so it is not "
                 "carried" % where)
    return None


def norm_address(street):
    a = street.upper()
    a = re.sub(r"\bPOST OFFICE BOX\b|\bP\.?\s*O\.?\s*BOX\b", "PO BOX", a)
    a = re.sub(r"\bP\.?\s*O\.?\s*DRAWER\b", "PO DRAWER", a)
    a = re.sub(r"[.,#]", " ", a)
    return re.sub(r"\s+", " ", a).strip()


def readable_name(name):
    """A name the fleet's name gate (scripts/validate_officeholder_names.py)
    accepts. This read its own test until 2026-10-21, which let a digit inside
    a quoted nickname through, and the gate refused the file."""
    return why_not_a_name(name) is None


def person_key(row):
    """One official across every row the list prints for them."""
    return fold(person_name(row))


def is_box(street):
    return street.startswith("PO BOX ") or street.startswith("PO DRAWER ")


def contact_book(texts):
    """Who prints each telephone and each address, across all of the list's
    offices that the builders read: a number by its digits; a post office box
    by the box and its town (two post offices number their boxes alike); and a
    street address by the box-or-street key and also by its street line alone,
    which is what shows a body printing another body's street (Tensas's)."""
    phones, places, streets = defaultdict(set), defaultdict(set), defaultdict(set)
    for office in ALL_OFFICES:
        for row in rows_of(texts[office], office):
            who = person_key(row)
            digits = phone_digits(row["Phone"])
            if digits:
                phones[digits].add(who)
            if row["Address"]:
                street = norm_address(row["Address"])
                places[(street, row["City"].upper())].add(who)
                if not is_box(street):
                    streets[street].add(who)
    return {"phones": phones, "places": places, "streets": streets}


def own_phone(row, book):
    """True where the row's telephone is printed for this official alone."""
    digits = phone_digits(row["Phone"])
    return bool(digits) and book["phones"][digits] == {person_key(row)}


def office_contacts(rows, book, where, notes):
    """The address and the telephone a body's own officials print as its
    office: at least SHARED_BY of them print it and no official outside the
    body does. Returns (address, telephone), either of them None."""
    people = {person_key(r) for r in rows}
    address = phone = None
    groups = defaultdict(list)
    for r in rows:
        if r["Address"] and r["City"]:
            groups[(norm_address(r["Address"]), r["City"].upper(), r["Zip"][:5])].append(r)
    shared = sorted((key for key, rs in groups.items()
                     if len({person_key(r) for r in rs}) >= SHARED_BY),
                    key=lambda k: -len({person_key(r) for r in groups[k]}))
    if len(shared) > 1 and (len({person_key(r) for r in groups[shared[0]]}) ==
                            len({person_key(r) for r in groups[shared[1]]})):
        notes.append("%s: its officials share two addresses equally often, so neither "
                     "is carried" % where)
    elif shared:
        street, city, _zip = shared[0]
        printers = set(book["places"][(street, city)])
        if not is_box(street):
            printers |= book["streets"][street]
        if printers <= people:
            sample = Counter((r["Address"], r["City"], r["Zip"])
                             for r in groups[shared[0]]).most_common(1)[0][0]
            address = "%s, %s, LA %s" % sample
        else:
            notes.append("%s: the address its officials share is printed by %d "
                         "official(s) outside it too, so it is not carried"
                         % (where, len(printers - people)))
    numbers = []
    for digits in sorted({phone_digits(r["Phone"]) for r in rows} - {""}):
        if len({person_key(r) for r in rows if phone_digits(r["Phone"]) == digits}) < SHARED_BY:
            continue
        if book["phones"][digits] <= people:
            numbers.append(digits)
        else:
            notes.append("%s: a telephone its officials share is printed by %d "
                         "official(s) outside it too, so it is not carried"
                         % (where, len(book["phones"][digits] - people)))
    if len(numbers) == 1:
        d = numbers[0]
        phone = "(%s) %s-%s" % (d[:3], d[3:6], d[6:])
    elif numbers:
        notes.append("%s: its officials share %d telephones, so none is carried as the "
                     "office's" % (where, len(numbers)))
    return address, phone


def person_record(row, seat, where, book, notes):
    """One official as the roster carries them: the seat (None for none), the
    name, the party, the telephone printed for them alone, the term's end."""
    name = person_name(row)
    why = why_not_a_name(name)
    if why:
        raise SystemExit("FAIL: %s carries no readable name (%s)" % (where, why))
    if nickname_dropped(row):
        notes.append("%s: the list prints a nickname with a digit in it, which is "
                     "left off the name" % where)
    rec = {"seat": seat, "name": name} if seat else {"name": name}
    party = row["Party"]
    if party:
        rec["party"] = PARTY_NAMES.get(party, party)
        if party not in PARTY_NAMES:
            notes.append("%s: party %r ships as printed" % (where, party))
    phone = phone_of(row["Phone"], where, notes)
    if phone and own_phone(row, book):
        rec["phone"] = phone
    ends = iso_date(row["ExpDate"], where)
    if ends:
        rec["termEnds"] = ends
    return rec


def unlisted_seats(seats):
    """Seats a numbered or lettered run skips: ['District 4'] for 1-3, 5-9."""
    words, marks = set(), []
    for s in seats:
        m = SEAT_RE.match(s)
        if not m:
            return []
        words.add(m.group(1))
        marks.append(m.group(2))
    if len(words) != 1 or not marks:
        return []
    word = words.pop()
    if all(x.isdigit() for x in marks):
        nums = sorted(set(int(x) for x in marks))
        return ["%s %d" % (word, n) for n in range(1, nums[-1] + 1) if n not in nums]
    if all(x.isalpha() for x in marks):
        last = max(marks)
        return ["%s %s" % (word, chr(c)) for c in range(ord("A"), ord(last) + 1)
                if chr(c) not in marks]
    return []


def build(texts, previous, today):
    parishes = load_parishes()
    notes = []
    groups = defaultdict(lambda: {"members": [], "at_large": [], "executive": []})
    for office in OFFICES:
        for row in rows_of(texts[office], office):
            key = fold(row["Parish"])
            if key not in parishes:
                raise SystemExit("FAIL: office %s lists a parish %r that matches no "
                                 "Census parish" % (office, row["Parish"]))
            title = row["OfficeTitle"]
            if office == "243_0":
                if title not in EXECUTIVE_TITLES:
                    raise SystemExit("FAIL: %s's executive is titled %r" % (row["Parish"], title))
                groups[key]["executive"].append(row)
            elif title in AT_LARGE_TITLES:
                groups[key]["at_large"].append(row)
            elif office == "245_0" and title in MEMBER_TITLES:
                groups[key]["members"].append(row)
            else:
                raise SystemExit("FAIL: office %s carries a row titled %r (%s) — a "
                                 "new title needs a reading in MEMBER_TITLES"
                                 % (office, title, row["Parish"]))
    if set(groups) != set(parishes):
        raise SystemExit("FAIL: the lists cover %d parishes; missing %s"
                         % (len(groups), sorted(set(parishes) - set(groups))))

    # Who prints each telephone and address, across every office read: a value
    # an official outside the parish's government prints is not its own.
    book = contact_book(texts)

    result = {}
    for key, (geoid, parish_name) in sorted(parishes.items(), key=lambda kv: kv[1][0]):
        g = groups[key]
        kinds = {MEMBER_TITLES[r["OfficeTitle"]] for r in g["members"]}
        if g["at_large"]:
            kinds.add("council")
        if len(kinds) != 1:
            raise SystemExit("FAIL: %s's rows name %d kinds of body: %s"
                             % (parish_name, len(kinds), sorted(kinds)))
        kind = kinds.pop()
        base = parish_name[:-len(" Parish")] if parish_name.endswith(" Parish") else parish_name
        body = BODY_OVERRIDES.get(parish_name) or "%s Parish %s" % (base, BODY_SUFFIX[kind])
        people = g["members"] + g["at_large"] + g["executive"]
        if len(g["members"]) + len(g["at_large"]) < MIN_BODY:
            raise SystemExit("FAIL: %s lists %d members, fewer than %d"
                             % (parish_name, len(g["members"]) + len(g["at_large"]), MIN_BODY))
        if len(g["executive"]) > 1:
            raise SystemExit("FAIL: %s lists %d executives" % (parish_name, len(g["executive"])))

        def record(row, seat):
            return person_record(row, seat, "%s %s" % (parish_name, seat), book, notes)

        seats = []
        for row in g["members"]:
            seat = row["OfficeTitleDescription"]
            if not seat:
                raise SystemExit("FAIL: a %s member's row names no seat" % parish_name)
            seats.append(record(row, seat))
        at_large = []
        for row in g["at_large"]:
            desc = row["OfficeTitleDescription"]
            # 244_0 describes its seats as divisions; 245_0's at-large rows
            # carry a district's description, which the title overrides.
            seat = ("At large, " + desc) if desc and not re.match(r"^District\b", desc) \
                else "At large"
            at_large.append(record(row, seat))

        rec = {"parish": parish_name, "body": body, "kind": kind, "seats": seats}
        if at_large:
            rec["atLarge"] = at_large
        skipped = unlisted_seats([s["seat"] for s in seats])
        if skipped:
            rec["unlisted"] = skipped
            notes.append("%s: the list names no one for %s" % (parish_name, ", ".join(skipped)))
        if g["executive"]:
            row = g["executive"][0]
            exe = record(row, row["OfficeTitle"])
            exe["title"] = exe.pop("seat")
            rec["executive"] = exe

        # The body's office: an address or telephone at least SHARED_BY of the
        # parish government's officials print, and no official outside it.
        address, phone = office_contacts(people, book, parish_name, notes)
        if address:
            rec["boardAddress"] = address
        if phone:
            rec["boardPhone"] = phone
        rec.update({"source": SOURCE, "sourceUrl": INDEX_URL})
        result[geoid] = rec

    # Unchanged records keep the day they were first read in this form.
    read = today
    if previous and all(isinstance(v, dict) for v in previous.values()):
        stripped = {k: {f: x for f, x in v.items() if f != "read"} for k, v in previous.items()}
        if stripped == result:
            read = next(iter(previous.values())).get("read") or today
    for rec in result.values():
        rec["read"] = read
    return result, notes


# ---------------------------------------------------------------- gates

ALLOWED = {"parish", "body", "kind", "seats", "atLarge", "unlisted",
           "executive", "boardAddress", "boardPhone", "source", "sourceUrl", "read"}
PERSON = {"seat", "name", "party", "phone", "termEnds"}


def shared_own_phones(people):
    """Telephones carried on the rows of two differently named officials,
    which an official's own number never is."""
    names = defaultdict(set)
    for p in people:
        if p.get("phone"):
            names[p["phone"]].add(fold(p.get("name")))
    return sorted(ph for ph, who in names.items() if len(who) > 1)


def check_shape(data):
    problems = []
    parishes = load_parishes()
    geoids = {g for g, _ in parishes.values()}
    if set(data) != geoids:
        problems.append("parish keys differ from state-counties.json: missing %s, extra %s"
                        % (sorted(geoids - set(data)), sorted(set(data) - geoids)))
    members = executives = phones = parties = 0
    for geoid, rec in sorted(data.items()):
        extra = set(rec) - ALLOWED
        if extra:
            problems.append("%s carries unexpected fields %s" % (geoid, sorted(extra)))
        if rec.get("kind") not in BODY_SUFFIX:
            problems.append("%s: kind %r" % (geoid, rec.get("kind")))
        people = list(rec.get("seats") or []) + list(rec.get("atLarge") or [])
        if len(people) < MIN_BODY:
            problems.append("%s: %d members" % (geoid, len(people)))
        for p in people + ([rec["executive"]] if rec.get("executive") else []):
            keys = set(p) - {"title"} if p is rec.get("executive") else set(p)
            allowed = (PERSON - {"seat"}) if p is rec.get("executive") else PERSON
            if keys - allowed:
                problems.append("%s: a person carries %s" % (geoid, sorted(keys - allowed)))
            if not p.get("name"):
                problems.append("%s: a person with no name" % geoid)
            if p.get("phone") and not PHONE_RE.match(p["phone"]):
                problems.append("%s: telephone %r" % (geoid, p["phone"]))
            if p.get("phone") and placeholder_phone(p["phone"]):
                problems.append("%s: a person carries a placeholder telephone" % geoid)
            if p.get("termEnds") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", p["termEnds"]):
                problems.append("%s: term %r" % (geoid, p["termEnds"]))
        for p in people:
            members += 1
            phones += bool(p.get("phone"))
            parties += bool(p.get("party"))
            if not p.get("seat"):
                problems.append("%s: a member with no seat" % geoid)
        if rec.get("executive"):
            executives += 1
            if rec["executive"].get("title") not in EXECUTIVE_TITLES:
                problems.append("%s: executive title %r" % (geoid, rec["executive"].get("title")))
        if rec.get("boardPhone") and (not PHONE_RE.match(rec["boardPhone"]) or
                                      placeholder_phone(rec["boardPhone"])):
            problems.append("%s: board telephone %r" % (geoid, rec["boardPhone"]))
        own = [p.get("phone") for p in people if p.get("phone")]
        if rec.get("boardPhone") in own:
            problems.append("%s: the board's telephone also rides a member's row" % geoid)
        if shared_own_phones(people):
            problems.append("%s: one telephone rides two members' rows" % geoid)
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(rec.get("read") or "")):
            problems.append("%s: read %r" % (geoid, rec.get("read")))
    if members < MIN_MEMBERS:
        problems.append("%d members, floor %d" % (members, MIN_MEMBERS))
    if executives < MIN_EXECUTIVES:
        problems.append("%d executives, floor %d" % (executives, MIN_EXECUTIVES))
    if members and phones / members < MIN_PHONE_SHARE:
        problems.append("%d of %d members carry a telephone, under %.0f%%"
                        % (phones, members, 100 * MIN_PHONE_SHARE))
    if members and parties / members < MIN_PARTY_SHARE:
        problems.append("%d of %d members carry a party, under %.0f%%"
                        % (parties, members, 100 * MIN_PARTY_SHARE))
    return problems, members, executives, phones


def main(argv):
    args = list(argv)
    if "--check" in args:
        with open(OUT) as fh:
            data = json.load(fh)
        problems, members, executives, phones = check_shape(data)
        if problems:
            for p in problems:
                print("FAIL: " + p)
            return 1
        print("OK: %s — %d parishes, %d members (%d with their own telephone), %d "
              "parish presidents and mayors" % (os.path.relpath(OUT, REPO), len(data),
                                               members, phones, executives))
        return 0
    offline = save = None
    if "--offline" in args:
        offline = args[args.index("--offline") + 1]
    if "--save" in args:
        save = args[args.index("--save") + 1]
    try:
        with open(OUT) as fh:
            previous = json.load(fh)
    except (OSError, ValueError):
        previous = {}
    texts = read_exports(offline=offline, save=save)
    today = read_date(offline) if offline else datetime.date.today().isoformat()
    data, notes = build(texts, previous, today)
    problems, members, executives, phones = check_shape(data)
    if problems:
        for p in problems:
            print("FAIL: " + p)
        return 1
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    addresses = sum(1 for r in data.values() if r.get("boardAddress"))
    board_phones = sum(1 for r in data.values() if r.get("boardPhone"))
    print("Wrote %s: %d parishes, %d members (%d with their own telephone), %d parish "
          "presidents and mayors, %d bodies with an office address and %d with an "
          "office telephone" % (os.path.relpath(OUT, REPO), len(data), members, phones,
                                executives, addresses, board_phones))
    for n in notes:
        print("  " + n)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
