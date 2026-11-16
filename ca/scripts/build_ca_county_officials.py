#!/usr/bin/env python3
"""
Build ca/data/app/ca-county-officials.json: the board of supervisors of every
California county outside San Francisco, read from the California Secretary of
State's California Roster, so the County card can name who governs the county
a reader clicked without reaching a third-party host at click time.

THE SOURCE, MEASURED 2026-11-16. The Secretary of State publishes the
California Roster, the state's directory of public officials (Government Code
sections 12240 to 12242), at www.sos.ca.gov/administration/california-roster.
That page links each edition's sections as PDF files, one of them the "County
Officials Directory", at admin.cdn.sos.ca.gov/ca-roster/<year>/counties.pdf.
The 2026 file that day was 574,091 bytes and 30 pages, its own modification
date 29 June 2026. It opens with the sentence "The information herein is
provided to the Secretary of State's Office by each local jurisdiction", so
each county's entry is that county's own filing.

Each page is two columns. Each county's entry starts with a line that is the
county's name alone, followed by a line starting "Address:", and carries one
"Board of Supervisors" heading followed by one "District N: <name>" line per
supervisor: five in 57 counties and eleven in San Francisco, 296 in all that
day. The other officials the entry lists (assessor, sheriff, district attorney
and the appointed department heads beside them) are not read here.

THE EDITION IS FOUND, NOT TYPED. The script reads the landing page and takes
the newest year for which it links a counties.pdf, so the 2027 Roster is
followed the week the Secretary of State links it. The page also links older
editions (2022 that day), which is why the newest is chosen rather than the
first.

SAN FRANCISCO IS PARSED AND NOT SHIPPED. San Francisco is a city and county in
one, and its Board of Supervisors is named on the Supervisor District card from
the city's own data, refreshed weekly (sf-supervisor-members.json). Shipping a
second, older reading of the same eleven names would give one question two
answers, so this file holds the other 57 counties. The Roster's San Francisco
entry is still parsed, as a check on the parser (it must find districts 1 to
11), and the run prints a DRIFT line for any district where the Roster and the
city's own data name different people. That line is information for a person;
it changes nothing.

WHAT SHIPS. For each county: the board's name and one seat per supervisorial
district with the supervisor's name, the Roster's edition year, the address of
the file and the file's own date. NOTHING IN THE OUTPUT DEPENDS ON THE DAY THE
SCRIPT RUNS, so a weekly run that reads the same file writes the same bytes and
opens no pull request. The date a reader is shown is the file's own, which is
the day the Secretary of State last changed it.

A NAME IS PRINTED AS THE ROSTER PRINTS IT, WITH FOUR MEASURED EXCEPTIONS, each
of which stops the build when it meets a shape it was not measured on:

  * Three counties file their names in capitals (Del Norte, Fresno and
    Monterey, 15 names). A name wholly in capitals is rewritten with an initial
    capital on each word, and only when every word is plain letters; a word
    starting MC or MAC, or one carrying an apostrophe or a hyphen, has no one
    right capitalisation, so the build stops and a person adds the name to
    CAPS_NAMES.
  * Plumas files "Mimi Hall - Chair". The post after the dash is dropped: a
    board chooses its chair each year, the other 56 counties file none, and
    this file is names only.
  * Siskiyou files each supervisor's town after a comma ("Jess Harris,
    Montague"). The town is dropped for that county alone (TOWN_AFTER_NAME).
  * A comma is otherwise allowed only before a generational suffix
    ("Lloyd Pareira, Jr."). Any other comma stops the build.

An empty seat is a vacancy only when the Roster says so: a line whose name is
one of the fleet's vacancy words ships as `vacant: true` with no name. A line
with nothing after the colon stops the build, because the Roster printing no
name is not the county saying the seat is empty. Every name is also held to
scripts/validate_officeholder_names.py's rule for what is not a name.

THE ROSTER IS A YEARLY SNAPSHOT. A supervisor who took office after the file's
date is not in it. Supervisors elected in 2026 take office around the start of
2027, on a date that varies with a county's charter, and the 2026 file will
name their predecessors until the Secretary of State publishes the next
edition. The card states the file's date and says this. ca/WATCH.md carries
the row.

ROBOTS, READ 2026-11-16 WITH THIS SCRIPT'S OWN CLIENT. www.sos.ca.gov answers
its robots.txt with an empty file, which disallows nothing. admin.cdn.sos.ca.gov
answers its robots.txt with HTTP 403, which RFC 9309 section 2.3.1.3 files with
"no policy published" (scripts/robots_policy.py), and serves the file itself
normally. A run is two requests, paced a second apart.

Usage:
    python3 ca/scripts/build_ca_county_officials.py [output_dir]
    python3 ca/scripts/build_ca_county_officials.py --save DIR [output_dir]
    python3 ca/scripts/build_ca_county_officials.py --offline DIR [output_dir]
    python3 ca/scripts/build_ca_county_officials.py --check

--check reads the SHIPPED file and nothing else, offline and with the standard
library alone: one record for each of the 57 counties under its own name and
none for San Francisco, five seats numbered 1 to 5 in each, every seat a name
or a vacancy, and one edition, file address and file date across the file. It
proves the file is what a build writes; it never proves the Roster has not
moved since.

--save writes both fetched files into DIR, reading back any it already holds;
--offline reads them back instead of fetching.
"""

import io
import json
import os
import re
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts"))
from scraper_common import (  # noqa: E402  (FLEET_SHARED)
    UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, fetch as fetch_response, require_robots_once)
from validate_officeholder_names import (  # noqa: E402  (FLEET_SHARED)
    is_vacancy_marker, why_not_a_name)

PACE_SECONDS = 1.0

LANDING = "https://www.sos.ca.gov/administration/california-roster"
# The landing page links each edition's county file at this address; the year
# is the edition.
FILE_RE = re.compile(r'href="(https://admin\.cdn\.sos\.ca\.gov/ca-roster/(\d{4})/counties\.pdf)"')

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
OUT_NAME = "ca-county-officials.json"
COUNTIES_FILE = os.path.join(DEFAULT_OUT_DIR, "state-counties.json")
SF_ROSTER_FILE = os.path.join(DEFAULT_OUT_DIR, "sf-supervisor-members.json")

SF_GEOID = "06075"
# Supervisors per county. State law sets five (Government Code section 25000);
# San Francisco's charter sets eleven. A county that changes its number (Los
# Angeles voted in 2024 to grow to nine by 2032) stops the build until this
# table says so.
BOARD_SEATS = {SF_GEOID: 11}
DEFAULT_SEATS = 5

BOARD_HEADING = "Board of Supervisors"
SEAT_RE = re.compile(r"^District\s+(\d+):\s*(.*)$")
# A post filed after the name ("Mimi Hall - Chair"). Dropped; see the docstring.
POST_AFTER_NAME_RE = re.compile(
    r"\s+[-\u2013\u2014]\s+(?:Vice[- ])?Chair(?:man|woman|person)?$", re.I)
GENERATIONAL_RE = re.compile(r"^(?:Jr\.?|Sr\.?|II|III|IV|V)$")
# Counties that file each supervisor's town after a comma, by GEOID. Measured
# 2026-11-16: Siskiyou alone.
TOWN_AFTER_NAME = {"06093"}
TOWN_RE = re.compile(r"^[A-Za-z][A-Za-z. ]*$")
# A name filed wholly in capitals that the rule below will not rewrite, with
# the capitalisation a person read from the county's own site. Empty on
# 2026-11-16: all 15 such names were plain words.
CAPS_NAMES = {}
CAPS_WORD_RE = re.compile(r"^(?:[A-Z]{2,}|[A-Z]\.)$")
FILE_DATE_RE = re.compile(r"^D:(\d{4})(\d{2})(\d{2})")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_LAST = [0.0]


def fetch(url):
    """One paced GET with this project's own client, after the host's
    robots.txt has been read with that same client. Returns bytes."""
    require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT,
                        label="ca-county-officials")
    wait = PACE_SECONDS - (time.time() - _LAST[0])
    if wait > 0:
        time.sleep(wait)
    try:
        return fetch_response(url, UA_HEADERS_ROSTER_BOT, timeout=90, attempts=3).content
    finally:
        _LAST[0] = time.time()


class Files(object):
    """Fetch, or read back, each file by a name derived from its URL."""

    def __init__(self, offline=None, save=None):
        self.offline = offline
        self.save = save

    @staticmethod
    def name(url):
        return re.sub(r"[^A-Za-z0-9._-]+", "_", url.split("://", 1)[-1])

    def get(self, url):
        name = self.name(url)
        for d in (self.offline, self.save):
            if d and os.path.exists(os.path.join(d, name)):
                with open(os.path.join(d, name), "rb") as f:
                    return f.read()
        if self.offline:
            raise RuntimeError("%s is not saved in %s" % (url, self.offline))
        body = fetch(url)
        if self.save:
            os.makedirs(self.save, exist_ok=True)
            with open(os.path.join(self.save, name), "wb") as f:
                f.write(body)
        return body


def counties():
    """{BASENAME: (GEOID, NAME)} for the 58 counties the County layer draws."""
    with open(COUNTIES_FILE) as f:
        feats = json.load(f)["features"]
    out = {}
    for feat in feats:
        p = feat["properties"]
        out[str(p["BASENAME"])] = (str(p["GEOID"]), str(p["NAME"]))
    if len(out) != 58:
        raise RuntimeError("state-counties.json carries %d counties, not 58" % len(out))
    return out


def newest_edition(landing_html):
    """(year, url) of the newest county file the landing page links."""
    found = {int(year): url for url, year in FILE_RE.findall(landing_html)}
    if not found:
        raise RuntimeError("the California Roster page links no county officials file")
    year = max(found)
    return year, found[year]


def roster_lines(pdf_bytes):
    """(lines, file_date): each page's left column then its right, top to
    bottom, and the file's own modification date as YYYY-MM-DD."""
    import pdfplumber  # function-local: --check needs the standard library alone

    lines = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        meta = pdf.metadata or {}
        for page in pdf.pages:
            width, height = page.width, page.height
            for x0, x1 in ((0, width / 2.0), (width / 2.0, width)):
                text = page.crop((x0, 0, x1, height)).extract_text(
                    x_tolerance=1.5, y_tolerance=3) or ""
                lines.extend(line.strip() for line in text.split("\n"))
    stamp = FILE_DATE_RE.match(str(meta.get("ModDate") or meta.get("CreationDate") or ""))
    if not stamp:
        raise RuntimeError("the county officials file states no date of its own")
    return lines, "%s-%s-%s" % stamp.groups()


def from_capitals(name, where):
    """A name filed wholly in capitals, with an initial capital on each word."""
    if name in CAPS_NAMES:
        return CAPS_NAMES[name]
    words = name.split(" ")
    for word in words:
        if not CAPS_WORD_RE.match(word) or re.match(r"^MA?C[A-Z]", word):
            raise RuntimeError(
                "%s: a name is filed in capitals and one of its words has no single "
                "right capitalisation; read the county's own site and add the name "
                "to CAPS_NAMES" % where)
    return " ".join(w if w.endswith(".") else w[0] + w[1:].lower() for w in words)


def clean_name(raw, geoid, where):
    """The supervisor's name from one "District N:" line, or None for a seat
    the Roster itself calls vacant. Raises on any shape not measured."""
    name = " ".join(raw.split())
    if not name:
        raise RuntimeError("%s: the Roster prints no name, and does not call the seat vacant" % where)
    if is_vacancy_marker(name):
        return None
    name = POST_AFTER_NAME_RE.sub("", name)
    if "," in name:
        head, _, tail = name.rpartition(",")
        head, tail = head.strip(), tail.strip()
        if GENERATIONAL_RE.match(tail):
            name = "%s, %s" % (head, tail)
        elif geoid in TOWN_AFTER_NAME and TOWN_RE.match(tail) and "," not in head:
            name = head
        else:
            raise RuntimeError("%s: the name carries a comma this script was not measured on" % where)
    if name.upper() == name and re.search(r"[A-Z]{2}", name):
        name = from_capitals(name, where)
    problem = why_not_a_name(name)
    if problem:
        raise RuntimeError("%s: what the Roster prints is not a name (%s)" % (where, problem))
    if ":" in name or len(name) > 60:
        raise RuntimeError("%s: what the Roster prints is not one name" % where)
    return name


def parse(lines, by_name):
    """{GEOID: [(district, name or None), ...]} for all 58 counties."""
    heads = [i for i, line in enumerate(lines[:-1])
             if line in by_name and lines[i + 1].startswith("Address:")]
    seen = [lines[i] for i in heads]
    if sorted(seen) != sorted(by_name):
        missing = sorted(set(by_name) - set(seen))
        twice = sorted({n for n in seen if seen.count(n) > 1})
        raise RuntimeError("the file's county entries are not the 58 counties once each "
                           "(missing: %s; twice: %s)" % (missing or "none", twice or "none"))
    out = {}
    for k, start in enumerate(heads):
        end = heads[k + 1] if k + 1 < len(heads) else len(lines)
        block = lines[start:end]
        geoid, county_name = by_name[block[0]]
        at = [n for n, line in enumerate(block) if line == BOARD_HEADING]
        if len(at) != 1:
            raise RuntimeError("%s: %d \"%s\" headings, not one" % (county_name, len(at), BOARD_HEADING))
        seats = []
        n = at[0] + 1
        while n < len(block):
            m = SEAT_RE.match(block[n])
            if not m:
                break
            district = int(m.group(1))
            where = "%s, District %d" % (county_name, district)
            seats.append((district, clean_name(m.group(2), geoid, where)))
            n += 1
        # the list ends at the next office's own "Label: value" line; anything
        # else there is a name that wrapped onto a second line
        if n < len(block) and ":" not in block[n]:
            raise RuntimeError("%s: the supervisors' list is followed by a line that is not "
                               "another office" % county_name)
        if any(SEAT_RE.match(line) for line in block[n:]):
            raise RuntimeError("%s: a \"District N:\" line stands outside the supervisors' list"
                               % county_name)
        want = BOARD_SEATS.get(geoid, DEFAULT_SEATS)
        if [d for d, _ in seats] != list(range(1, want + 1)):
            raise RuntimeError("%s: the supervisors' list is districts %s, not 1 to %d"
                               % (county_name, [d for d, _ in seats], want))
        out[geoid] = seats
    return out


def report_sf_drift(sf_seats):
    """Print a line for each district where the Roster and the city's own data
    name different people. Information for a person; changes nothing."""
    try:
        with open(SF_ROSTER_FILE) as f:
            city = json.load(f)
    except (OSError, ValueError):
        return
    for district, name in sf_seats:
        own = (city.get(str(district)) or {}).get("name")
        if own and name and own != name:
            print("DRIFT (not shipped): San Francisco District %d is %r in the Roster and %r "
                  "in the city's own data" % (district, name, own), file=sys.stderr)


def build(files):
    by_name = counties()
    landing = files.get(LANDING).decode("utf-8", errors="replace")
    edition, url = newest_edition(landing)
    lines, file_date = roster_lines(files.get(url))
    boards = parse(lines, by_name)
    report_sf_drift(boards[SF_GEOID])
    names = {geoid: name for geoid, name in by_name.values()}
    out = {}
    for geoid in sorted(boards):
        if geoid == SF_GEOID:
            continue
        seats = []
        for district, name in boards[geoid]:
            seat = {"seat": "District %d" % district, "district": district}
            if name is None:
                seat["vacant"] = True
            else:
                seat["name"] = name
            seats.append(seat)
        out[geoid] = {
            "county": names[geoid],
            "body": "%s Board of Supervisors" % names[geoid],
            "kind": "supervisors",
            "seats": seats,
            "edition": edition,
            "source": "the California Secretary of State's %d California Roster" % edition,
            "sourceUrl": url,
            "fileDate": file_date,
        }
    problems = shape_problems(out, by_name)
    if problems:
        raise RuntimeError("; ".join(problems))
    return out, edition, file_date


def shape_problems(data, by_name):
    """What is wrong with a roster in the shape this script writes; the build
    and --check both ask."""
    problems = []
    want = {geoid: name for geoid, name in by_name.values() if geoid != SF_GEOID}
    if set(data) != set(want):
        problems.append("%s does not hold exactly the 57 counties outside San Francisco" % OUT_NAME)
    editions, urls, dates = set(), set(), set()
    for geoid, rec in sorted(data.items()):
        county = rec.get("county")
        if want.get(geoid) and county != want[geoid]:
            problems.append("%s is filed as %r, not %r" % (geoid, county, want[geoid]))
        seats = rec.get("seats") or []
        size = BOARD_SEATS.get(geoid, DEFAULT_SEATS)
        if [s.get("district") for s in seats] != list(range(1, size + 1)):
            problems.append("%s: the seats are not districts 1 to %d" % (county, size))
        for s in seats:
            name = s.get("name")
            if s.get("vacant") is True:
                if name:
                    problems.append("%s: a vacancy carries a name" % county)
            elif not name:
                problems.append("%s: a seat names nobody and is not marked vacant" % county)
            elif why_not_a_name(name):
                problems.append("%s, %s: not a name (%s)" % (county, s.get("seat"), why_not_a_name(name)))
            if s.get("seat") != "District %s" % s.get("district"):
                problems.append("%s: a seat's label and district disagree" % county)
            extra = set(s) - {"seat", "district", "name", "vacant"}
            if extra:
                problems.append("%s: a seat carries %s, which this file never ships"
                                % (county, ", ".join(sorted(extra))))
        if rec.get("body") != "%s Board of Supervisors" % county:
            problems.append("%s: the board's name is not the county's" % county)
        editions.add(rec.get("edition"))
        urls.add(rec.get("sourceUrl"))
        dates.add(rec.get("fileDate"))
        if not rec.get("source"):
            problems.append("%s carries no source" % county)
    if len(editions) != 1 or not all(isinstance(e, int) for e in editions):
        problems.append("the records do not share one edition year")
    if len(urls) != 1 or not all(isinstance(u, str) and FILE_RE.match('href="%s"' % u) for u in urls):
        problems.append("the records do not share one county officials file")
    if len(dates) != 1 or not all(isinstance(d, str) and ISO_DATE_RE.match(d) for d in dates):
        problems.append("the records do not share one file date")
    return problems


def counts(data):
    seats = [s for rec in data.values() for s in rec["seats"]]
    return len(seats), sum(1 for s in seats if s.get("vacant") is True)


def check():
    path = os.path.join(DEFAULT_OUT_DIR, OUT_NAME)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    problems = shape_problems(data, counties())
    for p in problems:
        print("FAIL: %s" % p, file=sys.stderr)
    if problems:
        sys.exit(1)
    rec = next(iter(data.values()))
    total, vacant = counts(data)
    print("ca-county-officials: OK — 57 counties, %d seats (%d named, %d vacant), the %d "
          "Roster's file dated %s" % (total, total - vacant, vacant, rec["edition"], rec["fileDate"]))


def main(argv):
    args = list(argv)
    if "--check" in args:
        check()
        return
    save = offline = None
    if "--save" in args:
        i = args.index("--save")
        save = args[i + 1]
        del args[i:i + 2]
    if "--offline" in args:
        i = args.index("--offline")
        offline = args[i + 1]
        del args[i:i + 2]
    out_dir = args[0] if args else DEFAULT_OUT_DIR
    data, edition, file_date = build(Files(offline=offline, save=save))
    path = os.path.join(out_dir, OUT_NAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    total, vacant = counts(data)
    print("Wrote %s (57 counties from the %d Roster's file dated %s: %d supervisors named, "
          "%d seats vacant)" % (path, edition, file_date, total - vacant, vacant))


if __name__ == "__main__":
    main(sys.argv[1:])
