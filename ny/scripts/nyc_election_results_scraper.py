#!/usr/bin/env python3
"""
Read New York City's election district results for one election from the
Board of Elections in the City of New York, and write them as JSON for
build_nyc_election_results.py.

THE SOURCE. The Board publishes its election night results at
https://enr.boenyc.gov/ as plain HTML pages. The home page (index.html) lists
every contest. A contest held citywide or in one district links straight to
its page, CD<id>ADI0.html; an office elected from several districts (Congress,
State Senate, Assembly, the courts) links to an index, OF<id>AD0PY<n>.html,
that lists one CD page per district. Every contest has a page by Assembly
District, CD<id>AD0.html, linking one page per Assembly District,
CD<id>AD<ad>0.html, and that page has one row per Election District: the ED
number, the share of scanners reported, and each ballot line's votes.

enr.boenyc.gov answers /robots.txt by redirecting to its home page, an HTML
page and not a policy, which RFC 9309 reads as no policy (allow all); it is read
first with the client below, through the fleet's one reader. Measured
2026-11-06: the host serves this project's own token a full page.

BALLOT LINES. New York lets a candidate run on several parties' lines, and the
pages give each line its own column, so the same name appears more than once.
The scraper keeps every column as published (name, line and votes); the
builder adds a candidate's lines together, because a reader's question is who
got the most votes, not which party's line they were cast on.

THE PAGES ARE CHECKED, NOT TRUSTED: every contest page must name its office, an
Assembly District page must carry the header row of names, the row of ballot
lines and at least one ED row, every ED row must carry one whole number per
column, the
election districts must add to the page's Total row, and the run fails if fewer than MIN_CONTESTS contests or MIN_ROWS
election district rows are read.

WHAT THESE NUMBERS ARE. The Board's unofficial election night results. Ballots
the Board counts after election night are not in them, and the Board certifies
its results about early December. The home page's "Page Creation" time (its
contest pages also carry an "Information As Of" time, which the home page does
not) is recorded so the daily job can tell when the Board has published again.

Usage:
    python3 ny/scripts/nyc_election_results_scraper.py --date 2026-11-03 -o /tmp/nyc_results_raw.json
    python3 ny/scripts/nyc_election_results_scraper.py ... --cache-dir /tmp/nyc_pages
    python3 ny/scripts/nyc_election_results_scraper.py --as-of-only   # print the home page's time and exit
"""

import argparse
import datetime
import html
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
FLEET_SCRIPTS = os.path.join(os.path.dirname(INSTANCE), "scripts")
sys.path.insert(0, FLEET_SCRIPTS)

from scraper_common import make_fail, require_robots_once  # noqa: E402

fail = make_fail("nyc-election-results-scraper")

HOST = "https://enr.boenyc.gov"
USER_AGENT = "districtry/1.0 (+https://districtry.com/ny/)"
REQUEST_TIMEOUT = 60
PAUSE = 0.25
MIN_CONTESTS = 60
MIN_ROWS = 20000
MONTHS = {m: i for i, m in enumerate(
    ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST",
     "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"], 1)}

_last = [0.0]


def get(name, cache_dir=None):
    if cache_dir:
        path = os.path.join(cache_dir, name)
        if os.path.exists(path):
            return open(path, encoding="utf-8").read()
    wait = PAUSE - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    url = "%s/%s" % (HOST, name)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                final = resp.geturl()
                body = resp.read().decode("latin-1")
            break
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                fail("%s: %s" % (url, e))
            time.sleep(2 * (attempt + 1))
    _last[0] = time.time()
    if final.rstrip("/") != url.rstrip("/"):
        fail("%s redirected to %s, so the page does not exist" % (url, final))
    if cache_dir:
        with open(os.path.join(cache_dir, name), "w", encoding="utf-8") as fh:
            fh.write(body)
    return body


def text(fragment):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").split())


def cells(row):
    return [text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]


def as_of(home):
    m = re.search(r"Information As Of:\s*([0-9-]+ [0-9:]+)", home)
    if m:
        return m.group(1)
    m = re.search(r"Page Creation:\s*([0-9/]+ [0-9:]+ [AP]M)", home)
    return m.group(1) if m else None


def election_date(home):
    m = re.search(r"(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)"
                  r"\s+(\d{1,2}),\s+(\d{4})", home)
    if not m:
        fail("the home page names no election date")
    return "%s-%02d-%02d" % (m.group(3), MONTHS[m.group(1)], int(m.group(2)))


def contests_from_home(home, cache_dir):
    """[(cd id, office name, starred)]: every contest the home page lists."""
    found = []
    for row in re.findall(r"<tr.*?</tr>", home, re.S):
        links = re.findall(r'href="([^"]+)"', row)
        if len(links) != 2:
            continue
        label = text(row)
        m = re.match(r"\d+ (.+?) Summary AD Details", label)
        if not m:
            continue
        office = m.group(1)
        detail = links[1]
        cd = re.fullmatch(r"CD(\d+)ADI0\.html", detail)
        if cd:
            found.append((cd.group(1), office, "*" in label))
            continue
        if not re.fullmatch(r"OF\d+AD0PY\d+\.html", detail):
            fail("contest %r links %r, which is neither a contest nor an office index" % (office, detail))
        index = get(detail, cache_dir)
        n = 0
        for r in re.findall(r"<tr.*?</tr>", index, re.S):
            m2 = re.search(r'href="CD(\d+)ADI0\.html"', r)
            if not m2:
                continue
            name = re.sub(r"^\d+ ", "", text(r)).rstrip(" *").strip()
            found.append((m2.group(1), name, "*" in text(r)))
            n += 1
        if not n:
            fail("the office index %s lists no contests" % detail)
    return found


def whole(s, where):
    s = s.replace(",", "")
    if not re.fullmatch(r"\d+", s):
        fail("%s: %r is not a whole number" % (where, s))
    return int(s)


def parse_ad_page(page, where):
    """The ballot lines (name, party) and the ED rows [(ed, [votes...])]."""
    m = re.search(r'<table class="underline">(.*?)</table>', page, re.S)
    if not m:
        fail("%s has no results table" % where)
    rows = re.findall(r"<tr>(.*?)</tr>", m.group(1), re.S)
    if len(rows) < 3:
        fail("%s: the results table has %d rows" % (where, len(rows)))
    head = cells(rows[0])
    parties = cells(rows[1])
    # The first two columns are the ED label and the share reported; after them
    # every other column is a spacer.
    names = [c for i, c in enumerate(head[2:]) if i % 2 == 1]
    lines = [c for i, c in enumerate(parties[2:]) if i % 2 == 1]
    while names and not names[-1]:
        names.pop()
    lines = lines[:len(names)]
    if not names or any(not n for n in names):
        fail("%s: a column names nobody: %r" % (where, head))
    lines = [re.sub(r"^\((.*)\)$", r"\1", ln) for ln in lines]
    eds = []
    total = None
    for r in rows[2:]:
        c = cells(r)
        if not c or not c[0]:
            continue
        if c[0] == "Total":
            vals = [v for i, v in enumerate(c[2:]) if i % 2 == 1][:len(names)]
            # A Total of "-" is how a page whose districts counted no votes says so.
            total = [None if v == "-" else whole(v, "%s total" % where) for v in vals]
            continue
        mm = re.fullmatch(r"ED\s+(\d+)", c[0])
        if not mm:
            fail("%s: a row headed %r is not an election district" % (where, c[0]))
        vals = [v for i, v in enumerate(c[2:]) if i % 2 == 1][:len(names)]
        if len(vals) != len(names):
            fail("%s ED %s has %d counts for %d columns" % (where, mm.group(1), len(vals), len(names)))
        eds.append((int(mm.group(1)), [whole(v, "%s ED %s" % (where, mm.group(1))) for v in vals]))
    if not eds:
        fail("%s has no election district rows" % where)
    if total is not None:
        summed = [sum(v[i] for _ed, v in eds) for i in range(len(names))]
        if [None if t is None and n == 0 else n for n, t in zip(summed, total)] != total:
            fail("%s: its election districts add to %r and its Total row says %r" % (where, summed, total))
    return list(zip(names, lines)), eds


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--date", help="the election's date, YYYY-MM-DD")
    ap.add_argument("--cache-dir", help="keep each page here and read it from here on a later run")
    ap.add_argument("--as-of-only", action="store_true", help="print the home page's results time and exit")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()

    require_robots_once(HOST + "/", USER_AGENT)
    if args.cache_dir:
        os.makedirs(args.cache_dir, exist_ok=True)
    home = get("index.html", None if args.as_of_only else args.cache_dir)
    stamp = as_of(home)
    if args.as_of_only:
        print(stamp or "")
        return
    if not args.date or not args.output:
        fail("--date and -o are required")
    if election_date(home) != args.date:
        fail("the Board's results are for %s, expected %s" % (election_date(home), args.date))

    contests = contests_from_home(home, args.cache_dir)
    if len(contests) < MIN_CONTESTS:
        fail("%d contests, expected at least %d" % (len(contests), MIN_CONTESTS))
    out = []
    nrows = 0
    for cd, office, starred in contests:
        index = get("CD%sAD0.html" % cd, args.cache_dir)
        ads = sorted({int(a) for a in re.findall(r'href="CD%sAD(\d+)0\.html"' % cd, index)})
        if not ads:
            fail("%s (CD%s) lists no Assembly Districts" % (office, cd))
        title = re.search(r'<th[^>]*font-size: medium[^>]*>([^<]*\*?\*?)</th>',
                          index.split("UNOFFICIAL ELECTION NIGHT RESULTS", 1)[-1])
        columns = None
        rows = []
        for ad in ads:
            where = "%s, AD %d" % (office, ad)
            lines, eds = parse_ad_page(get("CD%sAD%d0.html" % (cd, ad), args.cache_dir), where)
            if columns is None:
                columns = lines
            elif lines != columns:
                fail("%s: the ballot lines differ between Assembly Districts (%r, %r)" % (where, columns, lines))
            for ed, vals in eds:
                rows.append([ad, ed, vals])
        nrows += len(rows)
        out.append({"id": cd, "office": office, "title": text(title.group(1)) if title else office,
                    "partOutside": starred, "lines": [list(x) for x in columns], "rows": rows})
        print("  %s: %d ADs, %d EDs" % (office, len(ads), len(rows)), file=sys.stderr)
    if nrows < MIN_ROWS:
        fail("%d election district rows, expected at least %d" % (nrows, MIN_ROWS))
    raw = {
        "source": HOST + "/",
        "read": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
                        .isoformat().replace("+00:00", "Z"),
        "asOf": stamp,
        "contests": out,
    }
    with open(args.output, "w") as fh:
        json.dump(raw, fh, separators=(",", ":"), ensure_ascii=False)
    print("read %d contests and %d election district rows from %s (as of %s)"
          % (len(out), nrows, HOST, stamp), file=sys.stderr)


if __name__ == "__main__":
    main()
