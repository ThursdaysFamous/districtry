#!/usr/bin/env python3
"""
Read the Chicago Board of Election Commissioners' list of the candidates who
filed for the next Chicago municipal election, and write it as JSON for
build_chicago_candidates.py.

WHY. Adam asked on 2026-11-10 for a "who's running in my ward" page for
Chicago's February 23, 2027 election, and chose to start it from the filed
list, marked objections pending, rather than wait for the certified ballot
("now"): a page about an election has to exist and be indexed before the
searches for it peak.

THE SOURCE. The Board's Candidates page
(https://chicagoelections.gov/getting-ballot/candidates) links each election's
"Candidate List" as one PDF on its blob store, named for the day it was printed
(".../prod/2026-11/Candidate List_20261109-1.pdf", read 2026-11-10: 18 pages,
"Candidate Filings in Ballot Order, February 23, 2027", "Status as of
11/9/2026 4:01:16 PM"). The page links the list for more than one election at
a time (on 2026-11-10 also the November 3, 2026 general election's), and a
revision gets a new file name, so every linked list is read on every run and
the one kept is the newest election whose list has alderperson races. A list
with none is a different election (a primary or a general), which these pages
are not about.

THE LIST PRINTS EACH CANDIDATE'S HOME ADDRESS, AND NOTHING HERE KEEPS IT. A
candidate's row carries the name on the left and the Board's status in a
column at the right ("Candidate", "Challenged"); the address is the next line
down, in the name column, with nothing in the status column. A row is taken
only where the status column has text, and only its name-column words are
read, so the address line is never read into anything this writes. No address
is printed in a log or an error message either: a line this cannot place is
reported by its page and position.

WHAT IS EMITTED: the election date from the list's title, the "Status as of"
time, both URLs, and per office, in the list's order, its name, its "Vote for"
line and each candidate's name and status exactly as printed (whitespace
collapsed), with a ballot number where the list prints one. The ballot's
write-in line ("Write-in", status "N/A") and a "No Candidate" line (where fewer
people filed than a race has seats) are not candidates and are skipped.
The "Referenda and Local Options" section at the end is not read.

THE FETCH. chicagoelections.gov answers the `requests` stack 403 and the stdlib
stack 200 with this project's own token (user-agent-measurements.json), so the
page is read with fetch_stdlib and UA_HEADERS_ROSTER_BOT, after its robots.txt
(read with that same client; it permits /getting-ballot). The PDF's host has no
robots.txt (404, allow all) and serves `requests` normally, as
chicago_polling_places_scraper.py already measured.

Usage:
    python3 scripts/chicago_candidates_scraper.py -o /tmp/chicago_candidates_raw.json
"""

import argparse
import datetime
import io
import json
import re
import sys
import urllib.parse

from scraper_common import (UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, fetch_stdlib,
                            make_fail, require_robots_once)

fail = make_fail("chicago-candidates-scraper")

PAGE_URL = "https://chicagoelections.gov/getting-ballot/candidates"
BLOB_PREFIX = "https://cboeprod.blob.core.usgovcloudapi.net/"
LIST_NAME_RE = re.compile(r"Candidate(?:%20| )List_\d{8}", re.I)

TITLE_RE = re.compile(r"Candidate Filings in Ballot Order,\s*([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})")
AS_OF_RE = re.compile(r"Status as of\s*(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})\s*([AP]M)")
MONTHS = {m: i for i, m in enumerate(
    "January February March April May June July August September October "
    "November December".split(), 1)}

# Column geometry, in PDF points, measured on the 2026-11-09 list: an office
# heading starts at x 66 in 13pt type; "Vote for ..." at x 78; a candidate's
# name at x 113 and the status column at x 486-513; the address line at x 113
# with nothing to its right. The bounds are loose on purpose (a revision that
# shifts a column by a few points still reads), and BALLOT_X_MAX leaves room
# for the ballot numbers the "Ballot No." column will carry once the Board
# assigns them.
HEADING_MIN_SIZE = 12.0
HEADING_X_MAX = 100.0
NAME_X = (100.0, 140.0)
STATUS_X_MIN = 400.0
BALLOT_X_MAX = 100.0
LINE_TOLERANCE = 3.0

# Each page's footer runs across both columns ("Monday, November 9, 2026" at
# the left, "Page 1 of 18" in the status column), so it is named rather than
# left for the name test to catch.
PAGE_FOOTER_RE = re.compile(r"^Page \d+ of \d+$")
# Rows the list prints with status "N/A" that are lines of the ballot rather
# than people: the write-in line, and "No Candidate" where fewer people filed
# than a race has seats (the 5th police district on 2026-11-09). Any other N/A
# row is kept, and the builder refuses a status it has no words for.
PLACEHOLDERS = {"write-in", "no candidate"}


def discover_lists(page_html):
    links = re.findall(r'href="([^"]+\.pdf)"', page_html, re.I)
    hits = []
    for raw in links:
        raw = raw.replace("&amp;", "&")
        if raw.startswith(BLOB_PREFIX) and LIST_NAME_RE.search(raw):
            # The page links the name with literal spaces; quote the path only.
            parts = urllib.parse.urlsplit(raw)
            path = urllib.parse.quote(urllib.parse.unquote(parts.path))
            url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, "", ""))
            if url not in hits:
                hits.append(url)
    if not hits:
        fail("no 'Candidate List_<date>' PDF linked on %s" % PAGE_URL)
    return hits


def lines_of(page):
    words = sorted(page.extract_words(extra_attrs=["size"]),
                   key=lambda w: (w["top"], w["x0"]))
    out = []
    for w in words:
        if out and abs(w["top"] - out[-1][0]["top"]) <= LINE_TOLERANCE:
            out[-1].append(w)
        else:
            out.append([w])
    return [sorted(line, key=lambda w: w["x0"]) for line in out]


def text(words):
    return " ".join(" ".join(w["text"] for w in words).split())


def parse(pdf_bytes, url):
    import pdfplumber  # function-local: only this step needs it

    election_date = as_of = None
    contests = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        done = False
        for pno, page in enumerate(pdf.pages, 1):
            if done:
                break
            for line in lines_of(page):
                whole = text(line)
                if election_date is None:
                    m = TITLE_RE.search(whole)
                    if m and m.group(1) in MONTHS:
                        election_date = "%s-%02d-%02d" % (
                            m.group(3), MONTHS[m.group(1)], int(m.group(2)))
                        continue
                if as_of is None:
                    m = AS_OF_RE.search(whole)
                    if m:
                        hour = int(m.group(4)) % 12 + (12 if m.group(7) == "PM" else 0)
                        as_of = "%s-%02d-%02dT%02d:%s:%s" % (
                            m.group(3), int(m.group(1)), int(m.group(2)), hour,
                            m.group(5), m.group(6))
                        continue
                big = line[0]["size"] >= HEADING_MIN_SIZE
                if big and whole.startswith("Referenda"):
                    done = True
                    break
                if big and line[0]["x0"] < HEADING_X_MAX:
                    # A race running onto the next page may repeat its heading
                    # there; it is still one race.
                    if not contests or contests[-1]["office"] != whole:
                        contests.append({"office": whole, "voteFor": None, "candidates": []})
                    continue
                if not contests or big:
                    continue
                if whole.startswith("Vote for"):
                    contests[-1]["voteFor"] = whole
                    continue
                status = [w for w in line if w["x0"] >= STATUS_X_MIN]
                names = [w for w in line if NAME_X[0] <= w["x0"] < STATUS_X_MIN]
                ballot = [w for w in line if w["x0"] < BALLOT_X_MAX]
                if not status:
                    continue          # an address line, or the page's furniture
                if PAGE_FOOTER_RE.match(text(status)):
                    continue          # "Monday, November 9, 2026 ... Page 1 of 18"
                if not names or names[0]["x0"] >= NAME_X[1]:
                    fail("%s page %d: a status at y %.0f with no name beside it"
                         % (url, pno, line[0]["top"]))
                name = text(names)
                if text(status) == "N/A" and name.lower() in PLACEHOLDERS:
                    continue          # a line of the ballot, not a person
                row = {"name": name, "status": text(status)}
                if ballot:
                    row["ballotNumber"] = text(ballot)
                contests[-1]["candidates"].append(row)
    return election_date, as_of, contests


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()

    require_robots_once(PAGE_URL, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    page = fetch_stdlib(PAGE_URL, headers=UA_HEADERS_ROSTER_BOT)

    import requests  # function-local, mirroring scraper_common.fetch
    best = None
    for url in discover_lists(page):
        require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
        r = requests.get(url, headers=UA_HEADERS_ROSTER_BOT, timeout=120)
        if r.status_code != 200 or not r.content.startswith(b"%PDF"):
            fail("PDF fetch %s: HTTP %s, %d bytes, starts %r"
                 % (url, r.status_code, len(r.content), r.content[:8]))
        election_date, as_of, contests = parse(r.content, url)
        wards = sum(1 for c in contests if c["office"].startswith("Alderperson"))
        print("%s: election %s, status as of %s, %d offices, %d alderperson races"
              % (url, election_date, as_of, len(contests), wards))
        if not wards:
            continue          # another election's list (a primary or a general)
        if not (election_date and as_of):
            fail("%s: title or 'Status as of' line not read (election=%r as_of=%r)"
                 % (url, election_date, as_of))
        if best is None or election_date > best["electionDate"]:
            best = {"electionDate": election_date, "listAsOf": as_of,
                    "sourcePage": PAGE_URL, "sourceUrl": url, "contests": contests}
    if best is None:
        fail("no candidate list linked on %s has alderperson races" % PAGE_URL)

    best["read"] = datetime.date.today().isoformat()
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(best, indent=2, ensure_ascii=False) + "\n")
    n = sum(len(c["candidates"]) for c in best["contests"])
    print("kept %s: %d offices, %d candidates, election %s"
          % (best["sourceUrl"], len(best["contests"]), n, best["electionDate"]))


if __name__ == "__main__":
    sys.exit(main())
