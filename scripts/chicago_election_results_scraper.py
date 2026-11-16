#!/usr/bin/env python3
"""
Read every contest's precinct-by-precinct results for one Chicago election
from the Chicago Board of Election Commissioners, and write them as JSON for
build_chicago_election_results.py.

THE SOURCE. The Board's results page for an election
(https://chicagoelections.gov/elections/results/<id>; the 3 November 2026
general election is id 42, read 2026-11-05) is a Drupal form: a "Select
Contest" menu, ward and precinct menus, and a Submit button. Pressing Submit
posts the form to the same address with `?ajax_form=1` and the page draws the
answer, in a dialog, from the HTML that post returns: a citywide total table,
then one table per ward with a row per precinct. This script makes exactly that
post, once per contest, with ward and precinct left at ALL. The first menu
entry (value "") is "Registered Voters/Ballots/Turnout", which is read too.

Each contest's dialog also links "Download Data in Excel"
(`/elections/results/<id>/download?contest=N`), an old-format .xls. The HTML is
read instead because it carries the same numbers and needs nothing beyond the
standard library to read.

THE FETCH. chicagoelections.gov answers the `requests` stack 403 and the stdlib
stack 200 with this project's own token (CLAUDE.md, measured 2026-09-03 and
again for the polling-place scraper on 2026-10-23), so every request here goes
through urllib with UA_HEADERS_ROSTER_BOT. robots.txt is read first with that
client; its `*` group disallows /core/, /profiles/, /admin/, /search/ and a few
account paths, and nothing under /elections. Requests are paced one second
apart, so a full read of about 150 contests takes under four minutes.

WHAT THESE NUMBERS ARE. Unofficial until the Board proclaims the official
results. The Board's own vote-by-mail page says counts change as mail ballots
postmarked by Election Day arrive (for 2026, until 17 November) and are not
final until at least 14 days after the election. Nothing here says otherwise:
the builder stamps every file with the date it was read and `certified: false`.

THE ROWS ARE CHECKED, NOT TRUSTED: every precinct row must carry the same
number of cells as the header, each candidate cell must be followed by its
percentage cell, and the precinct rows of each ward must sum to that ward's
Total row. A contest that fails any check fails the run.

FINDING AN ELECTION'S PAGE BY ITS DATE (2026-11-15). The Board gives each
election's results page a number that says nothing about the election (2023's
city election is 241, its runoff 242, November 2026's general 42), and a new
election's number is not known until the Board lists it on
https://chicagoelections.gov/elections/results, where each entry reads
"<year> <name> - <m>/<d>/<yy or yyyy>". `--find-date` reads that list and
prints the number of the one entry with that date, so a job can start reading
an election the night its page first exists. It exits 3, saying so, when no
entry has the date yet, and fails when more than one does (a primary has a
page per party) unless `--find-name` leaves one. The date is the Board's own
typing: its list has carried a wrong one (the 2026 Libertarian primary under
3/19 for 3/17), and an election listed under a wrong date is one this cannot
find.

Usage:
    python3 scripts/chicago_election_results_scraper.py --election 42 -o /tmp/results_raw.json
    python3 scripts/chicago_election_results_scraper.py --find-date 2027-02-23
    python3 scripts/chicago_election_results_scraper.py --selftest
"""

import argparse
import datetime
import html
import http.cookiejar
import json
import re
import sys
import time
import urllib.parse
import urllib.request

from scraper_common import (UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, make_fail,
                            require_robots_once)

fail = make_fail("chicago-election-results-scraper")

BASE = "https://chicagoelections.gov/elections/results/"
LISTING = "https://chicagoelections.gov/elections/results"
PACE_SECONDS = 1.0
NOT_LISTED = 3      # --find-date's exit code when the list has no such date

LISTED_RE = re.compile(r'<a href="/elections/results/(\d+)"[^>]*>(.*?)</a>', re.S)
LISTED_DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})\s*$")

OPTION_RE = re.compile(r'<option value="(\d*)"[^>]*>(.*?)</option>', re.S)
CONTEST_SELECT_RE = re.compile(
    r'<select[^>]*name="contest"[^>]*>(.*?)</select>', re.S)
BUILD_ID_RE = re.compile(r'name="form_build_id" value="([^"]+)"')
TITLE_RE = re.compile(r"<title>(.*?)\|", re.S)
WARD_SPLIT_RE = re.compile(r"<h3>\s*Ward\s+(\d{1,2})\s*</h3>")
TABLE_RE = re.compile(r"<table[^>]*>(.*?)</table>", re.S)
ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL_RE = re.compile(r"<t([hd])[^>]*>(.*?)</t[hd]>", re.S)


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def number(text, where):
    t = text.replace(",", "").strip()
    if not re.fullmatch(r"\d+", t):
        fail("%s: expected a whole number, found %r" % (where, text))
    return int(t)


def rows_of(table_html):
    out = []
    for row in ROW_RE.findall(table_html):
        cells = [clean(c) for _, c in CELL_RE.findall(row)]
        if cells:
            out.append(cells)
    return out


def listed_elections(page):
    """[(results id, label, ISO date or None)] for every election the Board's
    results list links, in the list's order. A two-digit year is this
    century's: the list starts in the 2000s."""
    out = []
    for num, label in LISTED_RE.findall(page):
        label = clean(label)
        m = LISTED_DATE_RE.search(label)
        date = None
        if m:
            year = int(m.group(3))
            try:
                date = datetime.date(year if year > 99 else 2000 + year,
                                     int(m.group(1)), int(m.group(2))).isoformat()
            except ValueError:
                date = None
        out.append((int(num), label, date))
    return out


def find_election(page, date, name=None):
    """The entries of the Board's list dated `date` (ISO), narrowed to those
    whose label holds `name` when one is given."""
    hits = [e for e in listed_elections(page) if e[2] == date]
    if name:
        hits = [e for e in hits if name.lower() in e[1].lower()]
    return hits


def read_listing():
    require_robots_once(LISTING, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    req = urllib.request.Request(LISTING, headers=dict(UA_HEADERS_ROSTER_BOT))
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read().decode("utf-8", "replace")


def selftest():
    """The list's shapes, as read on 2026-11-15: a four-digit and a two-digit
    year, a label with no dash before its date, several pages on one date, and
    an entry with no date at all."""
    page = """
      <li><a href="/elections/results/76">2026 Primary - DEM - 3/17/2026                    </a></li>
      <li><a href="/elections/results/77">2026 Primary - REP - 3/17/2026 </a></li>
      <li><a href="/elections/results/42">2026 General Election - 11/3/2026 </a></li>
      <li><a href="/elections/results/242">2023 Municipal Runoffs - 4/4/23                   </a></li>
      <li><a href="/elections/results/241" class="x">2023 Municipal General - 2/28/23 </a></li>
      <li><a href="/elections/results/3">2017 Municipal General 2/28/17</a></li>
      <li><a href="/elections/results/9">Special Election</a></li>
      <li><a href="/elections/results/10">2011 Something - 2/30/11</a></li>
      <li><a href="/elections/results">All results</a></li>
      <li><a href="/elections/other/5">Not a results page - 2/28/23</a></li>
    """
    checks = [
        (len(listed_elections(page)) == 8, "eight results pages are listed"),
        (find_election(page, "2023-02-28") == [(241, "2023 Municipal General - 2/28/23", "2023-02-28")],
         "a two-digit year is read, and only a results page is taken"),
        (find_election(page, "2026-11-03")[0][0] == 42, "a four-digit year is read"),
        (find_election(page, "2017-02-28")[0][0] == 3, "a label with no dash before its date is read"),
        ([e[0] for e in find_election(page, "2026-03-17")] == [76, 77], "a primary's pages share a date"),
        ([e[0] for e in find_election(page, "2026-03-17", "rep")] == [77], "a name leaves one of them"),
        (find_election(page, "2027-02-23") == [], "an election not listed yet is not found"),
        (listed_elections(page)[6][2] is None, "an entry with no date has none"),
        (listed_elections(page)[7][2] is None, "a date that is no day has none"),
    ]
    bad = [why for ok, why in checks if not ok]
    for why in bad:
        print("chicago-election-results-scraper: selftest FAIL — " + why, file=sys.stderr)
    if bad:
        raise SystemExit(1)
    print("chicago-election-results-scraper: selftest OK — %d checks on the Board's list of "
          "results pages" % len(checks))


class Board(object):
    def __init__(self, election):
        self.url = BASE + str(int(election))
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        self.last = 0.0

    def _open(self, url, data=None):
        wait = PACE_SECONDS - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, data=data, headers=dict(UA_HEADERS_ROSTER_BOT))
        try:
            with self.opener.open(req, timeout=90) as resp:
                body = resp.read()
        finally:
            self.last = time.time()
        return body.decode("utf-8", "replace")

    def form(self):
        page = self._open(self.url)
        m = CONTEST_SELECT_RE.search(page)
        if not m:
            fail("no contest menu on %s" % self.url)
        contests = [(v, clean(label)) for v, label in OPTION_RE.findall(m.group(1))]
        build = BUILD_ID_RE.search(page)
        if not build:
            fail("no form_build_id on %s" % self.url)
        title = TITLE_RE.search(page)
        return page, contests, build.group(1), clean(title.group(1)) if title else None

    def contest_html(self, contest, build_id):
        fields = {
            "election_id": self.url.rsplit("/", 1)[1],
            "contest": contest, "ward": "", "precinct": "",
            "form_build_id": build_id, "form_id": "election_results_form",
            "homepage": "", "submit": "Submit",
            "_triggering_element_name": "submit",
            "_triggering_element_value": "Submit",
        }
        body = self._open(self.url + "?ajax_form=1&_wrapper_format=drupal_ajax",
                          urllib.parse.urlencode(fields).encode())
        # Without an XMLHttpRequest header Drupal wraps its answer in a
        # <textarea> (its iframe-upload mode); the JSON inside is the same.
        m = re.fullmatch(r"\s*<textarea>(.*)</textarea>\s*", body, re.S)
        if m:
            body = html.unescape(m.group(1))
        try:
            commands = json.loads(body)
        except ValueError:
            fail("contest %r: the Board answered something other than its form's JSON" % contest)
        for c in commands:
            if c.get("command") == "openDialog" and isinstance(c.get("data"), str):
                return c["data"]
        fail("contest %r: the Board's answer carried no results dialog" % contest)


def parse_contest(name, dialog):
    """-> {"columns": [...], "total": {...}, "precincts": {"W-P": {...}}}

    A candidate contest's tables read  Total Votes | A | % | B | % ...  (citywide)
    and  Precinct | Total Voters | A | % | B | % ... | (ward). The turnout entry
    reads  Registered Voters | Ballots Cast | Turnout  with a Precinct column in
    the ward tables. Columns are kept as the Board heads them, less the "%"
    columns, which are recomputed from the counts by whoever displays them.

    A ward table's "Total Voters" column is not the number of people who
    voted in the contest: it is the sum of the choices' votes (equal in every
    precinct of all 219 contests read on 2026-11-05, and 2,351 against 940
    ballots in one precinct of the vote-for-three Water Reclamation race). The
    card calls it votes, so that equality is checked on every row rather than
    assumed.
    """
    parts = WARD_SPLIT_RE.split(dialog)
    head_tables = TABLE_RE.findall(parts[0])
    if len(head_tables) != 1:
        fail("%s: expected one citywide table, found %d" % (name, len(head_tables)))
    city = rows_of(head_tables[0])
    if len(city) != 2:
        fail("%s: the citywide table has %d rows, expected a header and one total"
             % (name, len(city)))
    header, values = city
    keep = [i for i, h in enumerate(header) if h not in ("%", "Turnout")]
    columns = [header[i] for i in keep]
    total = [number(values[i], name + " citywide " + header[i]) for i in keep]

    precincts = {}
    wards = {}
    for i in range(1, len(parts), 2):
        ward = int(parts[i])
        tables = TABLE_RE.findall(parts[i + 1])
        if not tables:
            fail("%s ward %d: no table" % (name, ward))
        rows = rows_of(tables[0])
        wh = rows[0]
        if not wh or wh[0] != "Precinct":
            fail("%s ward %d: header does not start with Precinct: %r" % (name, ward, wh))
        if [h for h in wh[1:] if h not in ("%", "Turnout")][1:] != columns[1:]:
            fail("%s ward %d: ward columns %r differ from citywide %r" % (name, ward, wh, header))
        wkeep = [j for j, h in enumerate(wh) if j > 0 and h not in ("%", "Turnout")]
        sums = [0] * len(wkeep)
        ward_total = None
        for r in rows[1:]:
            if len(r) != len(wh):
                fail("%s ward %d: row %r has %d cells, header has %d" % (name, ward, r, len(r), len(wh)))
            vals = [number(r[j], "%s ward %d precinct %s" % (name, ward, r[0])) for j in wkeep]
            if columns[0] != "Registered Voters" and vals[0] != sum(vals[1:]):
                fail("%s ward %d row %s: first column %d is not the sum of the choices' votes %d"
                     % (name, ward, r[0], vals[0], sum(vals[1:])))
            if r[0] == "Total":
                ward_total = vals
                continue
            p = number(r[0], "%s ward %d precinct" % (name, ward))
            key = "%d-%d" % (ward, p)
            if key in precincts:
                fail("%s: precinct %s appears twice" % (name, key))
            precincts[key] = vals
            sums = [a + b for a, b in zip(sums, vals)]
        if ward_total is None:
            fail("%s ward %d: no Total row" % (name, ward))
        if ward_total != sums:
            fail("%s ward %d: precincts sum to %r, the ward's Total row says %r"
                 % (name, ward, sums, ward_total))
        wards[ward] = ward_total
    # Ward totals must sum to the citywide total for every candidate column.
    # The first column differs in meaning (citywide "Total Votes" vs ward
    # "Total Voters"), so only the candidate columns are held to the sum.
    if wards:
        city_sum = [sum(w[k] for w in wards.values()) for k in range(len(columns))]
        if city_sum[1:] != total[1:]:
            fail("%s: wards sum to %r, the citywide row says %r" % (name, city_sum, total))
    return {"columns": columns, "total": total, "precincts": precincts}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--election", type=int)
    ap.add_argument("-o", "--output")
    ap.add_argument("--only", help="comma-separated contest values, for testing")
    ap.add_argument("--find-date", metavar="YYYY-MM-DD",
                    help="print the results id the Board lists for this election date, "
                         "and read nothing else; exits %d when none is listed yet" % NOT_LISTED)
    ap.add_argument("--find-name", help="with --find-date: only an entry whose label holds this")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if args.find_date:
        try:
            datetime.date.fromisoformat(args.find_date)
        except ValueError:
            fail("--find-date %r is not a date" % args.find_date)
        hits = find_election(read_listing(), args.find_date, args.find_name)
        if not hits:
            print("chicago-election-results-scraper: the Board's list of results pages has "
                  "no election dated %s yet" % args.find_date, file=sys.stderr)
            raise SystemExit(NOT_LISTED)
        if len(hits) > 1:
            fail("the Board lists %d results pages dated %s (%s); name one with --find-name"
                 % (len(hits), args.find_date, "; ".join("%d %s" % (e[0], e[1]) for e in hits)))
        print("found %s as results page %d" % (hits[0][1], hits[0][0]), file=sys.stderr)
        print(hits[0][0])
        return
    if args.election is None or not args.output:
        ap.error("--election and --output are required to read an election's results")

    board = Board(args.election)
    require_robots_once(board.url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    _, contests, build_id, title = board.form()
    if args.only is not None:
        want = set(args.only.split(","))
        contests = [c for c in contests if c[0] in want]
    if len(contests) < 2:
        fail("the contest menu lists %d entries" % len(contests))

    out = []
    for value, label in contests:
        dialog = board.contest_html(value, build_id)
        parsed = parse_contest(label or "turnout", dialog)
        parsed.update({"contestId": value, "name": label})
        out.append(parsed)
        print("%-4s %-60s %4d precincts" % (value or "-", label[:60], len(parsed["precincts"])),
              file=sys.stderr)

    doc = {
        "source": board.url,
        "election": title,
        "electionId": args.election,
        "read": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "contests": out,
    }
    with open(args.output, "w") as fh:
        json.dump(doc, fh)
    print("wrote %d contests to %s" % (len(out), args.output), file=sys.stderr)


if __name__ == "__main__":
    main()
