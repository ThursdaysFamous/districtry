#!/usr/bin/env python3
"""
Stage 1 of the Douglas County Board roster pipeline: read the county's two
published surfaces into raw JSON for build_douglas_county_board.py.

DOUGLAS HAS NO BOARD MEMBERS PAGE. Its website carries no county-board section
at all — no member list, no district pages, nothing in the navigation. Both
halves of the roster therefore come from documents, and they are DIFFERENT
documents answering different halves:

  * THE COUNTY YEARBOOK (an annual PDF, currently Yearbook-2025.pdf) lists the
    seven members with a county e-mail address each. This is what the county
    maintains as PEOPLE.
  * THE CERTIFIED ELECTION SUMMARY REPORTS ("2022-General-Election-Results.pdf",
    "2024-General-Election-Results.pdf") print, for each numbered district, the
    winner of that district's contest. This is what fixes the DISTRICT NUMBER,
    in the county's own numbering — the same numbering its GIS district layer
    uses.

THE YEARBOOK'S NUMBERS ARE NOT DISTRICT NUMBERS, and that is this county's trap.
Its members are listed "1. Tom Hettinger", "2. Bibby Appleby", … which reads
exactly like a district column and is not one: the certified returns put
Hettinger in District 3 and Appleby in District 2, and taking the list positions
as districts would misplace SIX of the seven. The list order is nothing but list
order. The yearbook also prints a precinct list per member, and that cannot be
used to recover the district either — it contains at least one error, naming
"Camargo 1 & 2" for a member whose district is Camargo 2 and 3, with Camargo 1
appearing under a second member as well.

So the district comes from the returns, the person comes from the yearbook, and
they are joined on SURNAME. The builder fails when the two disagree about who is
on the board rather than choosing a winner.

BOTH DOCUMENTS ARE FOUND RATHER THAN HARDCODED. The site is a Next.js front end
over a WordPress backend (douglas.wp.webfoot.io), whose media API lists every
uploaded file, so this picks the newest yearbook and every general-election
summary report it can see. A new yearbook next year is picked up without an edit
here.

WHAT SHIPS: name, district and the county e-mail address. WHAT DOES NOT: the
HOME ADDRESS the yearbook prints for every member, which never ships; the term
line, which reads "November 2024" / "November 2026" with nothing saying whether
that is the election that seated the member or the year the term ends, and both
readings contradict the returns for at least one member; and no phone, because
the yearbook publishes none for board members.

Usage:
    python3 scripts/douglas_county_board_scraper.py [-o raw.json]
"""

import argparse
import io
import json
import re
import sys

import requests
from scraper_common import require_robots_once, make_fail, UA_ROSTER_BOT  # noqa: E402  (shared machinery — do not fork)

WP = "https://douglas.wp.webfoot.io/wp-json/wp/v2/media"
SITE = "https://douglascountyil.gov"
TIMEOUT = 90
HEADERS = {"User-Agent": UA_ROSTER_BOT,
           "Accept": "application/json"}

EXPECT_MEMBERS = 7
EXPECT_PRECINCTS = 17      # a district contest always reports fewer than this
YEARBOOK_RE = re.compile(r"/Yearbook[-_](\d{4})\.pdf$", re.I)
GENERAL_RE = re.compile(r"/(\d{4})-General-Election-Results[^/]*\.pdf$", re.I)

BOARD_ANCHOR = "COUNTY BOARD MEETINGS"
BOARD_END = "Sub-committees"
ENTRY_RE = re.compile(r"^\s*(\d+)\.\s+(.+?)\s*$")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
CONTEST_RE = re.compile(r"COUNTY BOARD (\d+)(?:ST|ND|RD|TH) DISTRICT MEMBER", re.I)
CAND_RE = re.compile(r"^(.*?)\s{1,}\((R|D|N|NON)\)\s*$")
INT_RE = re.compile(r"^[\d,]+$")
NO_CANDIDATE_RE = re.compile(r"^\s*no\s+candidate\s*$", re.I)


fail = make_fail("douglas-board-scraper")


def media(pattern):
    """[(date, url)] for every media item whose URL matches, newest first."""
    session = requests.Session()
    session.headers.update(HEADERS)
    require_robots_once(WP, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-douglas-county-board-scraper")
    probe = session.get(WP, params={"per_page": 1}, timeout=TIMEOUT)
    total = int(probe.headers.get("X-WP-Total") or 0)
    hits, page = [], 1
    while (page - 1) * 100 < total and page <= 40:
        resp = session.get(WP, params={"per_page": 100, "page": page,
                                       "orderby": "date", "order": "desc"},
                           timeout=TIMEOUT)
        items = resp.json()
        if not isinstance(items, list) or not items:
            break
        for item in items:
            url = item.get("source_url") or (item.get("guid") or {}).get("rendered") or ""
            if pattern.search(url):
                hits.append((item.get("date", "")[:10], url))
        page += 1
    return sorted(set(hits), reverse=True)


def pdf_text(url):
    import pymupdf
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-douglas-county-board-scraper")
    resp = requests.get(url, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=TIMEOUT)
    resp.raise_for_status()
    if not resp.content.startswith(b"%PDF"):
        fail("%s did not return a PDF" % url)
    with pymupdf.open(stream=io.BytesIO(resp.content), filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)


def parse_yearbook(text):
    """[{listPosition, name, email}] — the people, in the yearbook's own order."""
    start = text.find(BOARD_ANCHOR)
    if start < 0:
        fail("the yearbook no longer carries a %r section" % BOARD_ANCHOR)
    end = text.find(BOARD_END, start)
    block = text[start:end if end > start else start + 4000]
    lines = [l.strip() for l in block.split("\n")]
    members, current = [], None
    for line in lines:
        hit = ENTRY_RE.match(line)
        if hit and not INT_RE.match(hit.group(2)):
            current = {"listPosition": int(hit.group(1)),
                       "name": re.sub(r"\s+", " ", hit.group(2)).strip()}
            members.append(current)
            continue
        if current is None:
            continue
        mail = EMAIL_RE.search(line)
        if mail and "email" not in current:
            current["email"] = mail.group(0).strip()
    return members


def parse_returns(text, label):
    """{district: {name, votes}} — the winner of each district's contest.

    A CONTEST ENDS AT THE NEXT CONTEST OF ANY KIND, not at the next BOARD
    contest, and that distinction is the whole of this function's correctness.
    In the 2024 report the seventh district's contest is the last board race on
    the page and is followed by CIRCUIT COURT JUDGE — a countywide race whose
    winner polled 7,274 votes. Slicing to a fixed number of lines instead put
    that judge in District 7. Every contest in these reports is anchored the
    same way: a title line immediately followed by "Number of Precincts", so
    those anchors are what bound a segment.
    """
    lines = [l.strip() for l in text.split("\n")]
    anchors = [i for i in range(len(lines) - 1)
               if lines[i + 1] == "Number of Precincts" and lines[i]]
    marks = [(i, CONTEST_RE.search(lines[i]).group(1)) for i in anchors
             if CONTEST_RE.search(lines[i])]
    out = {}
    for start, dnum in marks:
        after = [a for a in anchors if a > start]
        end = after[0] if after else len(lines)
        seg = lines[start + 1:end]
        # A district contest never covers the whole county. If this one reports
        # every precinct, the segment is not what it claims to be.
        if len(seg) > 1 and seg[0] == "Number of Precincts" and INT_RE.match(seg[1]):
            if int(seg[1].replace(",", "")) >= EXPECT_PRECINCTS:
                fail("%s: the District %s contest reports %s precincts, which is "
                     "the whole county — this is not a single-district contest"
                     % (label, dnum, seg[1]))
        best = None
        for i, line in enumerate(seg):
            cand = CAND_RE.match(line)
            if not cand:
                continue
            name = cand.group(1).strip()
            if NO_CANDIDATE_RE.match(name):
                continue
            votes = 0
            if i + 1 < len(seg) and INT_RE.match(seg[i + 1]):
                votes = int(seg[i + 1].replace(",", ""))
            if best is None or votes > best["votes"]:
                best = {"name": re.sub(r"\s+", " ", name), "votes": votes}
        if best:
            out.setdefault(dnum, []).append(dict(best, election=label))
    return {d: sorted(v, key=lambda x: -x["votes"])[0] for d, v in out.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--output", help="write raw JSON here (default: stdout)")
    args = ap.parse_args()

    books = media(YEARBOOK_RE)
    if not books:
        fail("the county's media library lists no Yearbook PDF — the only source "
             "for this board's members and e-mail addresses")
    book_date, book_url = books[0]
    members = parse_yearbook(pdf_text(book_url))
    if len(members) != EXPECT_MEMBERS:
        fail("the %s yearbook yielded %d member(s), expected %d — its County Board "
             "section changed shape" % (book_date, len(members), EXPECT_MEMBERS))

    generals = media(GENERAL_RE)
    if not generals:
        fail("the county's media library lists no General Election Results PDF — "
             "nothing else fixes the district numbers")
    winners = {}
    read = []
    for _, url in sorted(generals, key=lambda x: x[1]):
        year = GENERAL_RE.search(url).group(1)
        label = "%s General" % year
        for dnum, win in parse_returns(pdf_text(url), label).items():
            # Newest election wins: these are walked oldest-first.
            winners[dnum] = win
        read.append(label)

    payload = {"yearbook": {"date": book_date, "url": book_url, "members": members},
               "returns": {"read": sorted(read), "winners": winners},
               "site": SITE}
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        print("douglas-board-scraper: %d member(s) from the %s yearbook; %d district "
              "winner(s) from %s -> %s"
              % (len(members), book_date, len(winners), ", ".join(sorted(read)),
                 args.output), file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
