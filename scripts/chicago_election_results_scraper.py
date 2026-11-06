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

Usage:
    python3 scripts/chicago_election_results_scraper.py --election 42 -o /tmp/results_raw.json
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
PACE_SECONDS = 1.0

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
    ap.add_argument("--election", type=int, required=True)
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--only", help="comma-separated contest values, for testing")
    args = ap.parse_args()

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
