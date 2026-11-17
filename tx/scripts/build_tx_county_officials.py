#!/usr/bin/env python3
"""
Build tx/data/app/tx-county-officials.json: the county judge of every Texas
county, read from the Texas Office of Court Administration's judicial
directory, so the County card can name who presides over the commissioners
court of the county a reader clicked without reaching a third-party host at
click time.

WHO THIS NAMES, AND WHO IT DOES NOT. A Texas county is governed by a
commissioners court of five: the county judge, elected by the whole county,
who presides, and four commissioners, each elected from a commissioner
precinct (Texas Constitution, Article V, sections 15 and 18). This file names
the county judge. NO STATE OFFICE PUBLISHES A LIST OF THE COMMISSIONERS
(measured 2026-11-16: the judicial directory lists courts and their staff, and
the Secretary of State's results site answers this project's reader with a
managed challenge, which is an access control and is not worked around), so
the four commissioners are not in this file, and gap `tx-county-officials`
says so.

THE SOURCE, MEASURED 2026-11-16. The Office of Court Administration publishes
its judicial directory at www.txcourts.gov/judicial-data/judicial-directory/,
a page linking one file per listing. This script reads the one titled
"District, County and Justice Court Judges and Personnel by County", a PDF
(1,479,151 bytes and 168 pages that day) whose every page ends "Report Run
Date: 5/20/2026". The file's address carries a number the site assigns when a
file is uploaded, so THE FILE IS FOUND FROM THE PAGE, NOT TYPED: the script
reads the page and follows the one link whose file name is this listing's.

Each county's entry is the county's name on a line of its own, a "County
Seat:" line, then sections headed DISTRICT, COUNTY and JUSTICE(S) OF THE
PEACE. A section's rows are a label, a name, an address, a town, a ZIP code
and a telephone, joined by dot leaders. In the COUNTY section the row labelled
exactly "County Court" is the constitutional county court, and the name on it
is the county judge: 253 of the 254 counties carried one that day (Uvalde's
entry had no such row). The rows labelled "County Court at Law", "Probate
Court" and the like are statutory courts with judges of their own, and are not
read. Neither are the county clerk, the county attorney, the district courts
or the justices of the peace, all of which the same file names.

HOW THE FILE IS READ. The dot leaders are drawn over the same ground as the
text beside them, so a reader that sorts characters by position interleaves
the two ("C. .a .l h. o. on"). The file's own drawing order does not: each row
is drawn label, leader, name, leader, and so on, and the label and the name
are in the bold face while the leaders are not. So the script walks each
page's characters in the order the file draws them, starts a new row when the
baseline moves, and splits a row into runs by face. A "County Court" row must
be exactly two bold runs, the label and the name, or the build stops.

A NAME IS PRINTED AS THE DIRECTORY PRINTS IT, a nickname in brackets included
("James (Jim) Michael Johnson"), with runs of spaces closed up. A comma is
allowed only before a generational suffix ("Eddie Trevino, Jr."). A row whose
name is one of the fleet's vacancy words ships as `vacant: true` with no name.
A county whose entry has no "County Court" row ships as `notListed: true`:
the directory not naming a judge is not the county saying the seat is empty.
Every name is held to scripts/validate_officeholder_names.py's rule for what
is not a name. At most MAX_NOT_NAMED counties may be vacant or unlisted, so a
file that loses its county judges stops the build instead of emptying the
card.

WHAT SHIPS. For each of the 254 counties: the court's name and one seat, the
county judge, with the address of the file and the file's own report date.
The address, town and telephone the directory prints beside each judge are
not kept: this file is names only. NOTHING IN THE OUTPUT DEPENDS ON THE DAY
THE SCRIPT RUNS, so a weekly run that reads the same file writes the same
bytes and opens no pull request.

THE DIRECTORY IS A SNAPSHOT. A judge who took office after the report date is
not in it. Every county judge's term ends on 31 December 2026, and the judges
elected on 3 November 2026 take office on 1 January 2027, so the file read
today names the outgoing judge wherever the seat changed hands. The card
states the report date and says this. tx/WATCH.md carries the row.

ROBOTS, READ 2026-11-16 WITH THIS SCRIPT'S OWN CLIENT, on every run
(scripts/robots_policy.py): www.txcourts.gov serves a policy of 2,326 bytes
whose one binding group has no rule matching either address this script
reads. BOTH ADDRESSES ARE ON ONE HOST AND EACH IS ASKED ABOUT, because a
policy is a list of paths: the page and the file are different paths, and the
file's own path is not known until the page has been read. So a run is two
requests, paced a second apart, each after a read of robots.txt.

Usage:
    python3 tx/scripts/build_tx_county_officials.py [output_dir]
    python3 tx/scripts/build_tx_county_officials.py --save DIR [output_dir]
    python3 tx/scripts/build_tx_county_officials.py --offline DIR [output_dir]
    python3 tx/scripts/build_tx_county_officials.py --check

--check reads the SHIPPED file and nothing else, offline and with the standard
library alone: one record for each of the 254 counties under its own name,
one seat in each, the county judge, as a name, a vacancy or a judge the
directory did not list, and one file address and report date across the file.
It proves the file is what a build writes; it never proves the directory has
not moved since.

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
    UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, fetch as fetch_response, require_robots_allowed)
from validate_officeholder_names import (  # noqa: E402  (FLEET_SHARED)
    is_vacancy_marker, why_not_a_name)

PACE_SECONDS = 1.0

HOST = "https://www.txcourts.gov"
LANDING = HOST + "/judicial-data/judicial-directory/"
# The page links the listing at /media/<number>/<this name>; the number is the
# site's own and changes when the Office uploads a new file.
FILE_NAME = "district-county-and-justice-court-judges-and-personnel-by-county.pdf"
LINK_RE = re.compile(r'href="(/media/(\d+)/%s)"' % re.escape(FILE_NAME))
FILE_URL_RE = re.compile(r"^%s/media/\d+/%s$" % (re.escape(HOST), re.escape(FILE_NAME)))

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
OUT_NAME = "tx-county-officials.json"
COUNTIES_FILE = os.path.join(DEFAULT_OUT_DIR, "state-counties.json")

COUNTY_COUNT = 254
# Counties whose county judge the file may leave unnamed (a vacancy, or no
# "County Court" row) before the build stops. One on 2026-11-16, Uvalde.
MAX_NOT_NAMED = 5

SECTIONS = ("DISTRICT", "COUNTY", "JUSTICE(S) OF THE PEACE")
COUNTY_SECTION = "COUNTY"
JUDGE_ROW = "County Court"
JUDGE_SEAT = "County Judge"
PAGE_HEADING = "TRIAL COURTS BY COUNTY"
SEAT_OF_COUNTY = "County Seat:"
# The three lines every page ends with: two notes on the marks beside a
# local administrative judge's name, and the report's date and page number.
FOOTNOTE_STARTS = ("* Denotes", "^ Denotes")
RUN_DATE_RE = re.compile(r"^Report Run Date:\s*(\d{1,2})/(\d{1,2})/(\d{4})\b.*Page\s+\d+\s+of\s+\d+$")
# Four or more dots, each with optional space round it: a dot leader. A name's
# own full stop ("Carey G. McKinney") is one dot.
LEADER_RE = re.compile(r"(?:\s*\.\s*){4,}")
GENERATIONAL_RE = re.compile(r"^(?:Jr\.?|Sr\.?|II|III|IV|V)$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Two characters whose baselines differ by more than this are on two rows. A
# row's label and name sit 0.2 apart in the file and rows about 9.
ROW_GAP = 2.0

_LAST = [0.0]


def fetch(url):
    """One paced GET with this project's own client, after the host's
    robots.txt has been read with that same client and asked about THIS
    address's path (a refusal raises). Returns bytes."""
    why = require_robots_allowed(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT,
                                 label="tx-county-officials")
    print("robots.txt %s: %s" % (url.split("://", 1)[-1].split("/", 1)[0], why),
          file=sys.stderr)
    wait = PACE_SECONDS - (time.time() - _LAST[0])
    if wait > 0:
        time.sleep(wait)
    try:
        return fetch_response(url, UA_HEADERS_ROSTER_BOT, timeout=120, attempts=3).content
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
    """{BASENAME: (GEOID, NAME)} for the 254 counties the County layer draws."""
    with open(COUNTIES_FILE) as f:
        feats = json.load(f)["features"]
    out = {}
    for feat in feats:
        p = feat["properties"]
        out[str(p["BASENAME"])] = (str(p["GEOID"]), str(p["NAME"]))
    if len(out) != COUNTY_COUNT:
        raise RuntimeError("state-counties.json carries %d counties, not %d"
                           % (len(out), COUNTY_COUNT))
    return out


def listing_url(landing_html):
    """The address of the by-county listing the directory page links."""
    found = sorted(set(LINK_RE.findall(landing_html)), key=lambda m: int(m[1]))
    if len(found) != 1:
        raise RuntimeError("the judicial directory page links %d files named %s, not one"
                           % (len(found), FILE_NAME))
    return HOST + found[0][0]


def page_rows(page):
    """One page's rows, in the order the file draws them. A row is a list of
    (bold, text) runs: a new row starts when the baseline moves, a new run
    when the face changes between bold and not."""
    rows, row, top = [], [], None
    for ch in page.chars:
        if top is None or abs(ch["top"] - top) > ROW_GAP:
            if row:
                rows.append(row)
            row, top = [], ch["top"]
        bold = "Bold" in (ch.get("fontname") or "")
        if row and row[-1][0] == bold:
            row[-1][1].append(ch["text"])
        else:
            row.append([bold, [ch["text"]]])
    if row:
        rows.append(row)
    return [[(bold, "".join(text)) for bold, text in r] for r in rows]


def directory_rows(pdf_bytes):
    """Every page's rows in order, each as (page number, runs)."""
    import pdfplumber  # function-local: --check needs the standard library alone

    out = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            out.extend((number, runs) for runs in page_rows(page))
    return out


def clean_name(raw, where):
    """The judge's name from one "County Court" row, or None for a seat the
    directory itself calls vacant. Raises on any shape not measured."""
    name = " ".join(raw.split())
    if not name:
        raise RuntimeError("%s: the directory prints no name beside the court" % where)
    if is_vacancy_marker(name):
        return None
    if "," in name:
        head, _, tail = name.rpartition(",")
        head, tail = head.strip(), tail.strip()
        if not GENERATIONAL_RE.match(tail) or "," in head:
            raise RuntimeError("%s: the name carries a comma this script was not measured on" % where)
        name = "%s, %s" % (head, tail)
    problem = why_not_a_name(name)
    if problem:
        raise RuntimeError("%s: what the directory prints is not a name (%s)" % (where, problem))
    if ":" in name or len(name) > 60 or re.search(r"\d", name):
        raise RuntimeError("%s: what the directory prints is not one name" % where)
    return name


def parse(rows, by_name):
    """({GEOID: name, None for a vacancy, or False where the entry has no
    county court row}, report date as YYYY-MM-DD)."""
    judges, dates = {}, set()
    county = section = None
    for number, runs in rows:
        text = " ".join("".join(t for _bold, t in runs).split())
        if not text or text == PAGE_HEADING:
            continue
        if text.startswith(FOOTNOTE_STARTS):
            continue
        stamp = RUN_DATE_RE.match(text)
        if stamp:
            month, day, year = (int(g) for g in stamp.groups())
            dates.add("%04d-%02d-%02d" % (year, month, day))
            continue
        where = "page %d" % number
        if LEADER_RE.search(text):
            if county is None:
                raise RuntimeError("%s: a row stands before any county's name" % where)
            if section != COUNTY_SECTION:
                continue
            bold = [t.strip() for is_bold, t in runs if is_bold and t.strip()]
            if not bold or bold[0] != JUDGE_ROW:
                continue
            geoid, county_name = by_name[county]
            if len(bold) != 2:
                raise RuntimeError("%s: the \"%s\" row is %d bold runs, not a label and a name"
                                   % (county_name, JUDGE_ROW, len(bold)))
            if judges.get(geoid, False) is not False:
                raise RuntimeError("%s: two \"%s\" rows" % (county_name, JUDGE_ROW))
            judges[geoid] = clean_name(bold[1], "%s, %s" % (county_name, JUDGE_SEAT))
            continue
        if text in SECTIONS:
            if county is None:
                raise RuntimeError("%s: a section stands before any county's name" % where)
            section = text
            continue
        if text.startswith(SEAT_OF_COUNTY):
            continue
        if text in by_name:
            # a county's name. The file repeats it, and the section's heading
            # after it, where an entry runs on to the next page; a repeat
            # changes nothing here, so the section carries on either way
            if text != county:
                judges.setdefault(by_name[text][0], False)
                county, section = text, None
            continue
        raise RuntimeError("%s: a line that is no county, section, row or footer; this "
                           "script was not measured on it" % where)
    if len(dates) != 1:
        raise RuntimeError("the file's pages state %d report dates, not one" % len(dates))
    names = {geoid for geoid, _name in by_name.values()}
    if set(judges) != names:
        missing = sorted(n for n, (g, _c) in by_name.items() if g not in judges)
        raise RuntimeError("the file's county entries are not the %d counties (missing: %s)"
                           % (COUNTY_COUNT, ", ".join(missing) or "none"))
    return judges, dates.pop()


def build(files):
    by_name = counties()
    landing = files.get(LANDING).decode("utf-8", errors="replace")
    url = listing_url(landing)
    judges, file_date = parse(directory_rows(files.get(url)), by_name)
    out = {}
    for geoid, county_name in sorted(by_name.values()):
        seat = {"seat": JUDGE_SEAT, "countywide": True}
        judge = judges[geoid]
        if judge is False:
            seat["notListed"] = True
        elif judge is None:
            seat["vacant"] = True
        else:
            seat["name"] = judge
        out[geoid] = {
            "county": county_name,
            "body": "%s Commissioners Court" % county_name,
            "kind": "commissioners-court",
            "seats": [seat],
            "source": "the Texas Office of Court Administration's judicial directory",
            "sourceUrl": url,
            "fileDate": file_date,
        }
    problems = shape_problems(out, by_name)
    if problems:
        raise RuntimeError("; ".join(problems))
    return out, file_date


def shape_problems(data, by_name):
    """What is wrong with a roster in the shape this script writes; the build
    and --check both ask."""
    problems = []
    want = {geoid: name for geoid, name in by_name.values()}
    if set(data) != set(want):
        problems.append("%s does not hold exactly the %d counties" % (OUT_NAME, COUNTY_COUNT))
    urls, dates, not_named = set(), set(), 0
    for geoid, rec in sorted(data.items()):
        county = rec.get("county")
        if want.get(geoid) and county != want[geoid]:
            problems.append("%s is filed as %r, not %r" % (geoid, county, want[geoid]))
        seats = rec.get("seats") or []
        if [s.get("seat") for s in seats] != [JUDGE_SEAT]:
            problems.append("%s: the seats are not the county judge alone" % county)
        for s in seats:
            name = s.get("name")
            states = sum(1 for k in ("vacant", "notListed") if s.get(k) is True) + (1 if name else 0)
            if states != 1:
                problems.append("%s: the seat is not exactly one of a name, a vacancy "
                                "and a judge the directory did not list" % county)
            elif not name:
                not_named += 1
            elif why_not_a_name(name):
                problems.append("%s: not a name (%s)" % (county, why_not_a_name(name)))
            if s.get("countywide") is not True:
                problems.append("%s: the county judge is not marked as elected countywide" % county)
            extra = set(s) - {"seat", "countywide", "name", "vacant", "notListed"}
            if extra:
                problems.append("%s: a seat carries %s, which this file never ships"
                                % (county, ", ".join(sorted(extra))))
        if rec.get("body") != "%s Commissioners Court" % county:
            problems.append("%s: the court's name is not the county's" % county)
        if rec.get("kind") != "commissioners-court":
            problems.append("%s: the body is not a commissioners court" % county)
        urls.add(rec.get("sourceUrl"))
        dates.add(rec.get("fileDate"))
        if not rec.get("source"):
            problems.append("%s carries no source" % county)
    if not_named > MAX_NOT_NAMED:
        problems.append("%d counties name no county judge, more than the %d this file may"
                        % (not_named, MAX_NOT_NAMED))
    if len(urls) != 1 or not all(isinstance(u, str) and FILE_URL_RE.match(u) for u in urls):
        problems.append("the records do not share one directory file")
    if len(dates) != 1 or not all(isinstance(d, str) and ISO_DATE_RE.match(d) for d in dates):
        problems.append("the records do not share one report date")
    return problems


def counts(data):
    seats = [s for rec in data.values() for s in rec["seats"]]
    return (sum(1 for s in seats if s.get("name")),
            sum(1 for s in seats if s.get("vacant") is True),
            sum(1 for s in seats if s.get("notListed") is True))


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
    named, vacant, unlisted = counts(data)
    print("tx-county-officials: OK — %d counties, %d county judges named, %d vacant, %d not "
          "listed, the directory's file dated %s"
          % (len(data), named, vacant, unlisted, rec["fileDate"]))


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
    data, file_date = build(Files(offline=offline, save=save))
    path = os.path.join(out_dir, OUT_NAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    named, vacant, unlisted = counts(data)
    for geoid, rec in sorted(data.items()):
        if not rec["seats"][0].get("name"):
            print("NOT NAMED: %s (%s)" % (rec["county"], "vacant" if rec["seats"][0].get("vacant")
                                          else "no county court row in the file"), file=sys.stderr)
    print("Wrote %s (%d counties from the directory's file dated %s: %d county judges named, "
          "%d vacant, %d not listed)" % (path, len(data), file_date, named, vacant, unlisted))


if __name__ == "__main__":
    main(sys.argv[1:])
