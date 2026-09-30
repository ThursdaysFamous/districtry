#!/usr/bin/env python3
"""
Stage 1 of the Clark County Board roster pipeline: read the county's own
CERTIFIED ELECTION CANVASSES into raw JSON for build_clark_county_board.py.

WHY THE CANVASSES AND NOT A BOARD PAGE. Clark's county site publishes exactly
one board document — "2022 - 2024 County Board List", linked from
clarkcountyil.org/board — and it is a SCANNED IMAGE with no text layer, so no
scraper can ever read it. County Clerk & Recorder Laura H. Lee's reply of
2026-08-18 ("The County Board is elected by districts. I do not have maps
available.") settled the board's form and closed the map route in the same
sentence. What the county DOES publish machine-readably is its election
returns: il-clark.accessliberty.com carries one text-layer canvass PDF per
election back to 2006, and il-clark.pollresults.net serves the live feed. So
the roster here is not "who a page says sits on the board" but "who the county
certified as elected, per district, in the most recent election that seated
that seat" — which is a stronger claim, and one that renews itself every
November without anybody maintaining a page.

THE PDF ANATOMY, measured on the 2022 and 2024 files. Each canvass is a
"Statement of Votes Cast" whose pages carry ONE OR TWO contests side by side.
A contest begins with the words "COUNTY BOARD <n>(ST|ND|RD|TH) DISTRICT
MEMBER" and owns the column that starts at that header's x-position and runs
to the next contest header (or the page edge). Under it sit the candidate
headers ("REX E. GOBLE (REP)"), then one row per precinct — every precinct in
the COUNTY appears on every row, with a bare "-" in the columns of contests
that precinct is not in. So a precinct belongs to a contest exactly when the
cells inside that contest's x-range on that precinct's row contain a NUMBER.
That is the whole parse, and it is why this reads geometry-free: the county
never publishes a district's precinct list in prose, but its canvass tables
are that list.

WHAT COUNTS AS A SEATING ELECTION. November general elections only, and their
files are titled "<year> nov <day> il clark.pdf" on the Clerk's past-elections
page. Primaries (March) and consolidated elections (April) never seat a county
board member here, and reading a primary winner as a member is exactly the
error this project refuses to make. Districts are walked newest-first: the
first general canvass that carries a district is the one that seated its
current member, which handles Clark's staggered terms (districts 3, 4 and 7
were last elected in 2024; 1, 2, 5 and 6 in 2022 and are on the 2026 ballot)
without anything here knowing the schedule.

WHAT THIS DOES NOT PROVIDE: phone numbers and e-mail addresses. Those exist
only in the scanned board list, so they ride build_clark_county_board.py's
DOCUMENT_CONTACT with the document named and dated on every render — the
Edwards/Wabash shape. Home addresses appear in that scan and NEVER ship
(the Madison/Peoria rule).

Usage:
    python3 scripts/clark_county_board_scraper.py [-o raw.json]
"""

import os
import argparse
import io
import json
import re
import sys

import requests
from scraper_common import make_fail, UA_ROSTER_BOT  # noqa: E402  (shared machinery — do not fork)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_common import require_robots_once  # noqa: E402  (shared machinery)

PAST_ELECTIONS_URL = "https://il-clark.accessliberty.com/pastelections.aspx"
BOARD_URL = "https://www.clarkcountyil.org/board"
TIMEOUT = 60
HEADERS = {"User-Agent": UA_ROSTER_BOT}

# The Clerk's past-elections page names each file; a seating election is a
# November general. Odd years never carry one (consolidated elections are in
# April), so the year parity is part of the match rather than a separate check.
GENERAL_RE = re.compile(r"^(\d{4}) nov \d{1,2} il clark\.pdf$", re.I)
CONTEST_RE = re.compile(r"^(\d)(ST|ND|RD|TH)$", re.I)
# Every Clark county-board contest header reads "(Vote for one)"; a district
# that ever elects two would need the builder's seat handling revisited.
PARTY_RE = re.compile(r"\((REP|DEM|IND|GRN|LIB)\)")

MIN_DISTRICTS = 7


fail = make_fail("clark-board-scraper")


def get(url, **kw):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-clark-county-board-scraper")
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, **kw)
    resp.raise_for_status()
    return resp


def list_general_canvasses():
    """[(year, title, url)] for every November general canvass, newest first."""
    html = get(PAST_ELECTIONS_URL).text
    seen = {}
    for m in re.finditer(r"href='([^']*SharedFiles/Download\.aspx[^']*)'\s+title='([^']+)'",
                         html):
        url, title = m.group(1).replace("&amp;", "&"), m.group(2).strip()
        hit = GENERAL_RE.match(title)
        if not hit:
            continue
        year = int(hit.group(1))
        if year % 2:
            continue
        seen[year] = (year, title, url)
    if not seen:
        fail("no November general canvass found on %s — the page's file list "
             "changed shape" % PAST_ELECTIONS_URL)
    return [seen[y] for y in sorted(seen, reverse=True)]


def _vkey(name):
    """Collapse spacing and punctuation so a canvass's "PARIS  1" matches a
    feed's "PARIS 1" without either spelling being rewritten."""
    return re.sub(r"[^A-Z0-9]", "", (name or "").upper())


def parse_canvass(pdf_bytes, known_precincts=None):
    """{district: {"precincts": [...], "candidates": [{name, party, votes}]}}

    The page anatomy this relies on, measured on the 2022 and 2024 files:
    a contest header block reads "COUNTY BOARD <n>TH DISTRICT MEMBER" and owns
    the x-range from its own left edge to the next header's; each candidate is
    ONE text block inside that range reading "<NAME>  (<PARTY>)"; the words
    "Jurisdiction Wide" divide the headers from the precinct rows; precinct
    labels sit in the far-left column below that divider; and the final "Total"
    row carries every candidate's countywide vote total in cell order.

    PRECINCT NAMES ARE MATCHED AGAINST A KNOWN VOCABULARY when one is supplied,
    and that is not a nicety. Reading a label as "one capitalised word plus an
    optional digit" works for Clark, whose 23 precincts all have that shape, and
    silently mangles counties that do not: measured on Edgar's 2022 canvass, it
    split BROUILLETTS CREEK into two precincts, turned YOUNG AMERICA 1 into
    "YOUNG" plus "AMERICA 1", and collapsed PARIS 10, 11, 12, 14 and 15 into one
    bare "PARIS" because the digit pattern matched a single character. Pass the
    county's own precinct list — the Clerk's results feed publishes it — and each
    row is matched LONGEST-NAME-FIRST against that list instead, so a multi-word
    or multi-digit name cannot be shortened into a different precinct. Without a
    vocabulary the old heuristic still applies, and the builder's composition
    check is what stops a bad parse from shipping.
    """
    import pymupdf  # heavy; function-local so the builder can import constants

    doc = pymupdf.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
    vocab = sorted(((_vkey(x), len(x.split())) for x in (known_precincts or ())),
                   key=lambda t: -t[1])
    out = {}
    for page in doc:
        words = page.get_text("words")   # (x0, y0, x1, y1, word, block, line, n)
        cols = []
        for i, w in enumerate(words):
            if (w[4] == "COUNTY" and i + 4 < len(words) and words[i + 1][4] == "BOARD"
                    and CONTEST_RE.match(words[i + 2][4] or "")
                    and words[i + 3][4] == "DISTRICT" and words[i + 4][4] == "MEMBER"):
                cols.append([w[0] - 4.0, words[i + 2][4][0], None, w[3]])
        if not cols:
            continue
        cols.sort()
        for idx, col in enumerate(cols):
            col[2] = cols[idx + 1][0] if idx + 1 < len(cols) else 1e9
        jw = [w for w in words if w[4] == "Jurisdiction"]
        if not jw:
            continue
        jw_y = min(w[1] for w in jw)
        label_x = min(c[0] for c in cols)

        # candidate cells, as whole text blocks (one block per cell)
        cells = []
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            bx0, by0, bx1, by1 = block["bbox"]
            if by1 <= 100 or by0 >= jw_y + 3:
                continue
            text = re.sub(r"\s+", " ",
                          " ".join(sp["text"] for ln in block["lines"]
                                   for sp in ln["spans"])).strip()
            cells.append((bx0, bx1, text))

        for x0, dnum, x1, head_y1 in cols:
            rec = out.setdefault(dnum, {"precincts": [], "candidates": []})
            for bx0, bx1, text in sorted(c for c in cells if x0 <= c[0] < x1):
                pm = PARTY_RE.search(text)
                if not pm:
                    continue
                name = text[:pm.start()].strip(" .,")
                if not name or name.lower() == "no candidate":
                    continue
                if not any(c["name"] == name for c in rec["candidates"]):
                    rec["candidates"].append({"name": name, "party": pm.group(1),
                                              "cellX": bx0, "votes": None})

            # precinct rows, and the countywide Total row that closes them
            total_row = None
            for i, w in enumerate(words):
                if w[0] >= label_x or w[1] <= jw_y:
                    continue
                if w[4] == "Total":
                    y = (w[1] + w[3]) / 2.0
                    total_row = [t for t in words
                                 if abs((t[1] + t[3]) / 2.0 - y) < 3.5 and t[0] >= w[2]]
                    continue
                if not re.fullmatch(r"[A-Z][A-Z]+", w[4] or ""):
                    continue
                label, end_w = w[4], w
                if vocab:
                    for cand, ntok in vocab:      # longest first: PARIS 10 beats PARIS
                        toks = [words[i + k][4] for k in range(ntok)
                                if i + k < len(words)]
                        if len(toks) == ntok and _vkey(" ".join(toks)) == cand:
                            label, end_w = " ".join(toks), words[i + ntok - 1]
                            break
                    else:
                        continue
                else:
                    nxt = words[i + 1] if i + 1 < len(words) else None
                    if nxt and re.fullmatch(r"\d+", nxt[4] or "") and nxt[0] - w[2] < 12:
                        label, end_w = "%s %s" % (w[4], nxt[4]), nxt
                y = (w[1] + w[3]) / 2.0
                row = [t for t in words if abs((t[1] + t[3]) / 2.0 - y) < 3.5
                       and t[0] >= end_w[2]]
                if any(re.fullmatch(r"\d+", t[4] or "") for t in row
                       if x0 <= t[0] < x1):
                    if label not in rec["precincts"]:
                        rec["precincts"].append(label)

            # A contested race is decided by votes, never by cell order, so the
            # totals are read rather than assumed. Unopposed races (every Clark
            # county-board contest so far) need no arithmetic.
            named = [c for c in rec["candidates"] if c.get("votes") is None]
            if total_row and named:
                nums = [t for t in sorted(total_row, key=lambda t: t[0])
                        if x0 <= t[0] < x1 and re.fullmatch(r"[\d,]+", t[4] or "")]
                for cand in named:
                    after = [t for t in nums if t[0] >= cand["cellX"] - 6]
                    if after:
                        cand["votes"] = int(after[0][4].replace(",", ""))
    for rec in out.values():
        rec["precincts"].sort()
        for cand in rec["candidates"]:
            cand.pop("cellX", None)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--output", help="write raw JSON here (default: stdout)")
    args = ap.parse_args()

    generals = list_general_canvasses()
    records = {}
    consulted = []
    for year, title, url in generals:
        if len(records) >= MIN_DISTRICTS:
            break
        body = get(url).content
        if not body.startswith(b"%PDF"):
            fail("%s did not answer with a PDF — the download handler changed" % title)
        parsed = parse_canvass(body)
        if not parsed:
            continue
        consulted.append({"year": year, "title": title, "url": url,
                          "districts": sorted(parsed, key=int)})
        for dnum, rec in sorted(parsed.items(), key=lambda kv: int(kv[0])):
            if dnum in records:
                continue          # an older canvass never overrides a newer one
            named = [c for c in rec["candidates"] if c["name"]]
            if not named:
                continue
            records[dnum] = {
                "district": dnum,
                "precincts": rec["precincts"],
                "candidates": named,
                "electedYear": year,
                "electionTitle": title,
                "sourceUrl": url,
            }

    payload = {
        "source": PAST_ELECTIONS_URL,
        "boardUrl": BOARD_URL,
        "canvassesConsulted": consulted,
        "records": [records[d] for d in sorted(records, key=int)],
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        print("clark-board-scraper: %d district(s) from %d canvass(es) -> %s"
              % (len(records), len(consulted), args.output), file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
