#!/usr/bin/env python3
"""
Read the Chicago Board of Election Commissioners' list of every precinct's
Election Day polling place, and write it as JSON for
build_chicago_polling_places.py.

THE SOURCE. The Board's "Election Day Voting" page
(https://chicagoelections.gov/voting/election-day-voting) links "a full list of
all Chicago precinct polling places" as one PDF on its blob store, e.g.
".../prod/2026-10/All polling place list 10.19.26.pdf" (read 2026-10-23: 50
pages, a Crystal Reports "Polling Place Ward List" with ward, precinct, tier,
address and building name for all 1,291 precincts). Every revision gets a new
file name carrying its date, so the link is DISCOVERED from the page on every
run rather than pinned, and the newest list is whatever the page links today.
The PDF's footer says "This list is subject to change", which is why the
refresh runs daily until Election Day.

THE FETCH. chicagoelections.gov answers the `requests` stack 403 and the
stdlib stack 200 with this project's own token (measured 2026-10-23 on the
Election Day page; the same split CLAUDE.md records for the early-voting page
on 2026-09-03), so the page is read with fetch_stdlib and UA_HEADERS_ROSTER_BOT.
robots.txt is read first with that same client and permits /voting. The PDF's
host (cboeprod.blob.core.usgovcloudapi.net) has no robots.txt (404, allow all)
and serves `requests` normally.

WHAT IS EMITTED: per precinct, ward, precinct, address and building name,
exactly as printed (whitespace collapsed); the election and its date from the
report header; the report's own date; both URLs. The "Tier" column (High,
Medium, "Low or No") is NOT emitted: the report does not say what it measures,
and a column nobody can explain is not shipped.

Usage:
    python3 scripts/chicago_polling_places_scraper.py -o /tmp/chicago_polling_raw.json
"""

import argparse
import json
import re
import sys
import urllib.parse

from scraper_common import (UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, fetch_stdlib,
                            make_fail, require_robots_once)

fail = make_fail("chicago-polling-scraper")

PAGE_URL = "https://chicagoelections.gov/voting/election-day-voting"
BLOB_PREFIX = "https://cboeprod.blob.core.usgovcloudapi.net/"

# A precinct row: the precinct number, the tier word(s), then the address and
# the building name separated by a run of spaces (layout extraction keeps the
# report's columns apart). The tier is glued to the house number ("High2723").
ROW_RE = re.compile(
    r"^\s*(\d{1,3})\s+(?:High|Medium|Low or No|Low|None)?\s*"
    r"(\d+[A-Z0-9\-/]*\s+\S.*?)\s{3,}(\S.*?)\s*$")
WARD_RE = re.compile(r"^\s*WARD\s+(\d{1,2})\s*$")
REPORT_DATE_RE = re.compile(r"Date:\s*(\d{1,2})/(\d{1,2})/(\d{4})")
MONTHS = {m: i for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
ELECTION_RE = re.compile(r"^\s*([A-Z][A-Z ]+ELECTION)\b")
ELECTION_DATE_RE = re.compile(r"^\s*([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d{4})\b")


def discover_pdf(page_html):
    links = re.findall(r'href="([^"]+\.pdf)"', page_html, re.I)
    hits = [l for l in links
            if l.startswith(BLOB_PREFIX) and re.search(r"polling place list", l, re.I)]
    if len(set(hits)) != 1:
        fail("expected exactly one 'polling place list' PDF on %s, found %r"
             % (PAGE_URL, sorted(set(hits))))
    raw = hits[0]
    # The page links the name with literal spaces; quote the path only.
    parts = urllib.parse.urlsplit(raw)
    path = urllib.parse.quote(urllib.parse.unquote(parts.path))
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def parse(pdf_bytes):
    import io
    import pypdf  # function-local: only this step needs it

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    rows, ward = [], None
    election = election_date = report_date = None
    for page in reader.pages:
        for line in page.extract_text(extraction_mode="layout").splitlines():
            if election is None:
                m = ELECTION_RE.match(line)
                if m:
                    election = " ".join(m.group(1).split()).title()
            if election_date is None:
                m = ELECTION_DATE_RE.match(line)
                if m and m.group(1) in MONTHS:
                    election_date = "%s-%02d-%02d" % (
                        m.group(3), MONTHS[m.group(1)], int(m.group(2)))
            if report_date is None:
                m = REPORT_DATE_RE.search(line)
                if m:
                    report_date = "%s-%02d-%02d" % (
                        m.group(3), int(m.group(1)), int(m.group(2)))
            m = WARD_RE.match(line)
            if m:
                ward = int(m.group(1))
                continue
            m = ROW_RE.match(line)
            if m:
                if ward is None:
                    fail("precinct row before any WARD heading: %r" % line.strip())
                rows.append({
                    "ward": ward,
                    "precinct": int(m.group(1)),
                    "address": " ".join(m.group(2).split()),
                    "place": " ".join(m.group(3).split()),
                })
            elif re.match(r"^\s*\d{1,3}\s+\S", line):
                # A numbered line the row pattern did not take is a precinct
                # this run would silently drop.
                fail("unparsed precinct line: %r" % " ".join(line.split()))
    if not (election and election_date and report_date):
        fail("report header not read: election=%r date=%r report=%r"
             % (election, election_date, report_date))
    return rows, election, election_date, report_date


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()

    require_robots_once(PAGE_URL, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    page = fetch_stdlib(PAGE_URL, headers=UA_HEADERS_ROSTER_BOT)
    pdf_url = discover_pdf(page)

    import requests  # function-local, mirroring scraper_common.fetch
    require_robots_once(pdf_url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    r = requests.get(pdf_url, headers=UA_HEADERS_ROSTER_BOT, timeout=120)
    if r.status_code != 200 or not r.content.startswith(b"%PDF"):
        fail("PDF fetch: HTTP %s, %d bytes, starts %r"
             % (r.status_code, len(r.content), r.content[:8]))

    rows, election, election_date, report_date = parse(r.content)
    payload = {
        "election": election,
        "electionDate": election_date,
        "listDate": report_date,
        "sourcePage": PAGE_URL,
        "sourceUrl": pdf_url,
        "rows": rows,
    }
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    print("read %d precinct rows in %d wards from %s (%s, list dated %s)"
          % (len(rows), len({x["ward"] for x in rows}), pdf_url, election, report_date))


if __name__ == "__main__":
    sys.exit(main())
