#!/usr/bin/env python3
"""Read who won each Kentucky magisterial and commissioner district in the 2022 general election.

WHY. The Department for Local Government's county directory, which names every
fiscal court member (ky_county_officials_scraper.py), never says which district
a magistrate holds. The State Board of Elections does: its 2022 general
election "recap sheets" are each county's official precinct results, and every
fiscal court contest on them is headed with its district, for example
"MAGISTRATE 3rd Magisterial District" or "COUNTY COMMISSIONER, 1st District
Countywide". build_ky_county_officials.py joins a directory member to the
district whose 2022 winner carries the same name.

WHERE. https://elect.ky.gov/results/2020-2029/Pages/2022-General-Recap-Sheets.aspx
links one PDF per county. Measured 2026-10-11: the page links 119 of the 120
counties (Rockcastle is not linked), and Butler's link answers 404, so 118
sheets are read.

POLICY. elect.ky.gov's robots.txt (read 2026-10-11 with this scraper's client,
through scraper_common.require_robots_once) is one `User-agent: *` group
disallowing five SharePoint system folders (/_Layouts/, /SiteAssets/, /Lists/,
/_catalogs/, /WorkflowTasks/). /results/ matches none of them and the file
states no Crawl-delay. The scraper waits PAUSE seconds between requests.

TWO KINDS OF SHEET. 51 sheets carry a text layer and are read with pdftotext.
The other 67 are scans from a county office's copier, with no text at all, so
each page is rendered (pdftoppm, 200 dpi) and read with tesseract. A scanned
sheet's vote counts come back with stray characters ("23°", "2134%"), so the
counts here are good enough to find a contest's winner and are never shown to
a reader. The join in build_ky_county_officials.py is what protects against a
misread: a name only gains a district when it matches a directory member
exactly, so a misread name matches nobody rather than the wrong person.

THE SHEETS ARE PRECINCT RESULTS. Every contest is printed once per precinct,
so a candidate's votes are summed across every block of the same contest
before the winner is chosen. Two layouts occur:
  - "Choice / Party / Absentee / Early / Election Day / Total" with a count and
    a percentage in each column, ending in "Cast Votes:"; the TOTAL is the last
    count on the line.
  - "TOTAL / VOTE % / ..." with the party BEFORE the name, ending in "Write-In
    Totals" or "Total Votes Cast"; the TOTAL is the first count on the line.
A sheet is the second kind when it prints "Write-In Totals".

KENTUCKY ELECTS BOTH OFFICES IN SOME COUNTIES. In a commissioner county the
voters still elect magistrates (justices of the peace), who do not sit on the
fiscal court, so the builder reads only the contest that matches the county's
form. Both are kept here, as printed.

THE OUTPUT IS A 2022 SNAPSHOT. Terms that began in January 2023 end on the
first Monday of January 2027; the 2026 general election is 3 November 2026. Run
this again against the 2026 recap sheets once the State Board posts them
(ky/WATCH.md carries the row).

Output: ky/data/source/ky-fiscal-court-2022-results.json

    python3 ky/scripts/ky_fiscal_court_results_scraper.py            # live read (needs poppler-utils and tesseract-ocr)
    python3 ky/scripts/ky_fiscal_court_results_scraper.py --selftest # offline
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from datetime import date
from urllib.parse import unquote, urljoin

HERE = os.path.dirname(os.path.abspath(__file__))
TAG_ROOT = os.path.dirname(HERE)
OUT = os.path.join(TAG_ROOT, "data", "source", "ky-fiscal-court-2022-results.json")

PAGE = "https://elect.ky.gov/results/2020-2029/Pages/2022-General-Recap-Sheets.aspx"
ELECTION = "2022-11-08"
PAUSE = 0.5
# Measured 2026-10-11: 119 sheets linked, 118 served. Fewer is a broken read.
MIN_SHEETS = 115
# A text layer shorter than this is a scan (the scanned sheets extract to a
# few hundred bytes of form feeds; the shortest real text sheet is ~90 KB).
MIN_TEXT = 5000

HEADER = re.compile(r"^\s*['‘’\"]?(MAGISTRATE|COUNTY COMMISSIONER)\b[\s,\-]*(.*)$", re.I)
END = re.compile(r"^\s*(Cast Votes|Write-In Totals|Total Votes Cast|Undervotes|"
                 r"Under Votes|Overvotes|Over Votes)", re.I)
SKIP = re.compile(r"^\s*(Choice|Vote For|TOTAL\b|Not Assigned|Precinct|Run |Page\b|"
                  r"Voting\b|Day\b)", re.I)
PARTY = {"REP", "DEM", "IND", "LIB", "NP", "NON", "GRN", "CON", "SOC", "REF"}
# Words a scanned sheet's misread layout can put where a name goes.
NOT_A_NAME = re.compile(r"cast votes|constable|general election|magistrate|"
                        r"commissioner|write.?in|precinct", re.I)
# Words that are never part of a candidate's identity: suffixes, party codes,
# and "OEM", which is how text recognition reads a smudged party column.
NOISE = {"jr", "sr", "ii", "iii", "iv", "i", "rep", "dem", "oem", "ind", "lib"}
DIRECTIONS = ("Northeast", "Northwest", "Southeast", "Southwest", "North", "South",
              "East", "West", "Central", "Eastern", "Western")


def district_key(rest):
    """The district part of a contest heading -> "3", "A" or "Northwest"."""
    rest = re.sub(r",?\s*Vote For.*$", "", rest, flags=re.I).strip()
    m = re.match(r"(\d+)\s*(?:st|nd|rd|th)\b", rest, re.I)
    if m:
        return str(int(m.group(1)))
    m = re.search(r"District\s+(\d+)", rest, re.I)
    if m:
        return str(int(m.group(1)))
    m = re.match(r'["“]?([A-Z])["”]?\s+DISTRICT', rest)
    if m:
        return m.group(1)
    for d in DIRECTIONS:
        if re.match(d + r"\b", rest, re.I):
            return d
    return None


def candidate(line, total_first):
    """One result line -> (name, votes), or None when it is not a candidate."""
    toks = line.split()
    if toks and toks[0].upper() in PARTY:
        toks = toks[1:]
    name = []
    while toks and not re.search(r"\d", toks[0]) and toks[0].upper() not in PARTY:
        name.append(toks.pop(0))
    if toks and toks[0].upper() in PARTY:
        toks = toks[1:]
    name = " ".join(name).strip(" .,;:'‘’`|©°")
    if (not name or not re.search(r"[A-Za-z]{2}", name) or re.search(r"\(W", name)
            or NOT_A_NAME.search(name)):
        return None
    counts = []
    for t in toks:
        if "%" in t or re.match(r"^\D*\d+[.,]\d\d\D*$", t):
            continue
        digits = re.sub(r"[^\d]", "", t)
        if digits:
            counts.append(int(digits))
    if not counts:
        return None
    return name, counts[0] if total_first else counts[-1]


def identity(name):
    """(surname, first initial): one candidate however the scan spelled them.

    A scanned sheet reads the same candidate several ways on different pages
    ('Lonnie "Junior" MAIDEN', 'Lonnie “Junior’ MAIDEN'), and their votes must
    be summed as one; two candidates who share a surname but not an initial
    (Sara COMBS and Dennis COMBS, Powell County District 2) stay apart."""
    name = re.sub(r'["“”][^"“”]*["“”]', " ", name)
    toks = [t for t in re.sub(r"[^a-z]", " ", name.lower()).split()
            if t not in NOISE and len(t) > 1]
    return (toks[-1], toks[0][0]) if toks else None


def merge_spellings(votes):
    """{name: votes} -> the same with each candidate's spellings summed under
    the spelling that carried the most votes."""
    groups = defaultdict(list)
    for name, n in votes.items():
        groups[identity(name) or name].append((n, name))
    return {max(g)[1]: sum(n for n, _ in g) for g in groups.values()}


def parse_sheet(text):
    """Sheet text -> {"MAGISTRATE|3": {name: votes}} summed over precincts."""
    total_first = "write-in totals" in text.lower()
    out = defaultdict(lambda: defaultdict(int))
    cur = None
    for line in text.splitlines():
        h = HEADER.match(line)
        if h:
            d = district_key(h.group(2))
            cur = "%s|%s" % (h.group(1).upper(), d) if d else None
            continue
        if cur is None or not line.strip():
            continue
        if END.match(line):
            cur = None
            continue
        if SKIP.match(line):
            continue
        c = candidate(line, total_first)
        if c:
            out[cur][c[0]] += c[1]
    return {k: merge_spellings(v) for k, v in out.items() if v}


def sheet_text(pdf_path, workdir):
    """(text, method): pdftotext's layout text, or tesseract's for a scan."""
    text = subprocess.run(["pdftotext", "-layout", pdf_path, "-"], check=True,
                          capture_output=True, text=True, errors="replace").stdout
    if len(text) >= MIN_TEXT:
        return text, "text"
    pages = os.path.join(workdir, "p")
    subprocess.run(["pdftoppm", "-r", "200", "-gray", "-png", pdf_path, pages], check=True)
    parts = []
    env = dict(os.environ, OMP_THREAD_LIMIT="1")
    for img in sorted((f for f in os.listdir(workdir) if f.endswith(".png")),
                      key=lambda f: int(re.sub(r"\D", "", f))):
        parts.append(subprocess.run(["tesseract", os.path.join(workdir, img), "-",
                                     "--psm", "6", "-l", "eng"], check=True, env=env,
                                    capture_output=True, text=True, errors="replace").stdout)
        os.remove(os.path.join(workdir, img))
    return "\n".join(parts), "ocr"


def scrape():
    for tool in ("pdftotext", "pdftoppm", "tesseract"):
        if not shutil.which(tool):
            raise SystemExit("FAIL: %s is not installed (apt-get install poppler-utils "
                             "tesseract-ocr)" % tool)
    sys.path.insert(0, os.path.join(TAG_ROOT, "..", "scripts"))
    import requests
    import scraper_common as sc

    headers = dict(sc.UA_HEADERS_ROSTER_BOT)
    session = requests.Session()
    sc.require_robots_once(PAGE, sc.UA_ROSTER_BOT, headers=headers)
    r = session.get(PAGE, headers=headers, timeout=60)
    r.raise_for_status()
    links = sorted(set(urljoin(PAGE, html.unescape(h)) for h in
                       re.findall(r'href="([^"]+GeneralRecaps/[^"]+\.pdf)"', r.text, re.I)))
    counties, missing = {}, []
    for url in links:
        county = re.sub(r"\s+County$", "", unquote(url.rsplit("/", 1)[1])[:-4]).strip()
        time.sleep(PAUSE)
        rr = session.get(url, headers=headers, timeout=120)
        if rr.status_code != 200 or not rr.content.startswith(b"%PDF"):
            missing.append({"county": county, "url": url, "status": rr.status_code})
            continue
        with tempfile.TemporaryDirectory() as tmp:
            pdf = os.path.join(tmp, "sheet.pdf")
            with open(pdf, "wb") as fh:
                fh.write(rr.content)
            text, method = sheet_text(pdf, tmp)
        contests = parse_sheet(text)
        counties[county] = {"url": url, "method": method, "contests": {
            k: {"votes": v, "winner": max(v.items(), key=lambda x: x[1])[0]}
            for k, v in sorted(contests.items())}}
        print("  %s: %s, %d contests" % (county, method, len(contests)), file=sys.stderr)
    if len(counties) < MIN_SHEETS:
        raise SystemExit("FAIL: %d sheets read, floor %d" % (len(counties), MIN_SHEETS))
    return {"source": {"publisher": "Kentucky State Board of Elections", "url": PAGE,
                       "election": ELECTION, "read": date.today().isoformat(),
                       "notServed": missing},
            "counties": counties}


SELFTEST_A = """
MAGISTRATE 1st Magisterial District - (Vote for One)
Choice                                      Party       Absentee Voting        Early Voting   Election Day Voting                  Total
Tony DENTON                                 REP              2   100.00%       22   100.00%          147   100.00%          171   100.00%

                                         Cast Votes:         2   100.00%       22   100.00%          147   100.00%         171   100.00%

UNITED STATES SENATOR - (Vote for One)
Rand PAUL                                   REP              2   100.00%       22   100.00%          157   92.90%          181   93.78%

MAGISTRATE 1st Magisterial District - (Vote for One)
Choice Party Absentee Voting Early Voting Election Day Voting Total
Tony DENTON REP 23° 85.19% 62 78.48% 266 83.13% 351 82.39%
Joe SMITH. DEM 4 1481% 17° 21.52% 54 16,88% 75 17.61%
Cast Votes: 27 100.00% 79 = 100.00% 320 = 100.00% 426 100.00%.
"""

SELFTEST_B = """
  COUNTY COMMISSIONER, 1st District Countywide
  Vote For 1
                                           TOTAL    VOTE % Absentee    Early   Election
REP Beth SEWELL                            332     99.70%       0      47        285
Write-In Totals                              1      0.30%       0       0          1
  MAGISTRATE Northwest Magisterial District
REP Luie A. WHITAKER                       120
DEM Ann LEE                                 90
Write-In Totals                              0
"""


def selftest():
    a = parse_sheet(SELFTEST_A)
    assert a == {"MAGISTRATE|1": {"Tony DENTON": 522, "Joe SMITH": 75}}, a
    b = parse_sheet(SELFTEST_B)
    assert b == {"COUNTY COMMISSIONER|1": {"Beth SEWELL": 332},
                 "MAGISTRATE|Northwest": {"Luie A. WHITAKER": 120, "Ann LEE": 90}}, b
    assert merge_spellings({'Lonnie "Junior" MAIDEN': 543, "Lonnie “Junior’ MAIDEN": 208,
                            "Kevin BARNETT": 454}) == {'Lonnie "Junior" MAIDEN': 751,
                                                        "Kevin BARNETT": 454}
    assert len(merge_spellings({"Sara COMBS": 305, "Dennis COMBS": 222,
                                "DennisCOMBS =": 0, "Dennis COMBS |": 149})) >= 2
    assert district_key('"A" DISTRICT') == "A"
    assert district_key("District 1 District 1") == "1"
    assert district_key("2nd Magisterial District, Vote For 1") == "2"
    assert district_key("Southeast Magisterial District") == "Southeast"
    assert district_key("Countywide") is None
    print("ky_fiscal_court_results_scraper selftest: ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    doc = scrape()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    print("wrote %s: %d counties" % (args.out, len(doc["counties"])))


if __name__ == "__main__":
    main()
