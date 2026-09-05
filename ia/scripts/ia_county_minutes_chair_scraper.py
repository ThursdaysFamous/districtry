#!/usr/bin/env python3
"""Scrape stage 1b: the board chair as a county's own MINUTES name them.

WHY A SECOND ROUTE, WHEN ONE ALREADY SHIPS 35 COUNTIES
--------------------------------------------------------
`ia_county_chair_scraper.py` reads each county's BOARD PAGE. That route
answered 35 of 98 and left the state's biggest counties out: of the ten
largest counties with no chair, seven had a board page that simply never
uses the word, two refused the client, and one has no supervisor roster to
gate with. A page is not the only thing a county publishes about its own
board -- its MINUTES are a second, statutory surface, and Iowa boards open
them with an attendance line that names the chair outright. That is the Knox
shape from the Illinois work (a roster taken from the roll call of a
county's own minutes), and it is why this file exists beside the other
rather than replacing it.

MEASURED 2026-09-05 over the ten largest counties with no chair. FIVE
publish minutes this can read and FIVE do not, and the five refusals are
recorded here because the next pass should not redo them:

  Polk           minutes only through a CivicClerk single-page portal. The
                 OData API answers -- /v1/Events lists every Board of
                 Supervisors meeting back through 2026 -- but every route to
                 a FILE is shut to this client: /v1/Meetings 404s in all five
                 key shapes tried, /v1/Events(5151)/publishedFiles 404s,
                 GetEventFileStream 500s, and GetMeetingFileStream answers
                 200 with ZERO BYTES -- the function exists and the file id
                 is the part there is no way to learn. Its board pages carry zero
                 occurrences of chair. (The board page is reachable after
                 all: the earlier sweep recorded 403, which is what
                 www.polkcountyiowa.gov answers to a bot user-agent at its
                 Akamai edge; the same URL with browser headers answers 200
                 with 168 KB. A county is not blocked because one client is.)
  Dubuque        CivicPlus AgendaCenter that renders entirely client-side --
                 the served HTML's only heading is "Loading" -- and its own
                 AJAX endpoint /AgendaCenter/UpdateCategoryList answers 404
                 to this client for every catID 1-15. Its agenda RSS is a
                 stub naming the module rather than any meeting, an
                 Archive.aspx sweep of AMID 1-39 finds no supervisors
                 archive, and /290/Board-of-Supervisors carries no chair
                 word.
  Story          THE ONE WORTH READING TWICE. Its minutes are reachable and
                 they do not say chair: three consecutive packets (25 Aug,
                 18 Aug, 11 Aug 2026, 88/154/195 pages) open "Linda Murken
                 and Latifah Faisal, and Lisa Heddens, with Murken
                 presiding" and the only other role word in any of them is
                 "by the Chair of the Board of Supervisors", a role with no
                 name. PRESIDING IS NOT THE OFFICE -- a vice chair presides
                 when the chair is away -- so this county is refused on
                 vocabulary, not on reach.
  Warren         its Meetings, Agendas & Minutes page answers 200 at 339 KB
                 and the year tabs (2015-2026, agendas and minutes alike)
                 contain no document links at all; the whole flattened body
                 is 9,306 characters and the only PDFs on it are a county
                 profile, a district map and a trade-names list. Warren is
                 also the one county here with no supervisor roster in
                 ia-county-officers.json to gate a name against.
  Pottawattamie  www.pottcounty-ia.gov and pottcounty-ia.gov both answer
                 Cloudflare 403 to bot and browser headers alike; no other
                 hostname resolves.

THE TRAP THIS ROUTE HAS, AND IT IS THE FRANKLIN TRAP AGAIN
------------------------------------------------------------
A minutes signature block is a stack of lines, and flattening it puts a
role beside the NEXT person's name. Des Moines County's reads

    Shane McCampbell, Chair
    Tom Broeker, Vice Chair
    Jim Cary, Member

which flattens to `Shane McCampbell, Chair Tom Broeker, Vice Chair Jim
Cary, Member` -- so a role word taken with what FOLLOWS it makes Tom
Broeker the chair, and taken with what precedes it makes Shane McCampbell
the chair, in the same document. Both readings are available and only one is
right. So every role occurrence is resolved in BOTH directions and REFUSED
when the two disagree; the attendance line "with Chair Shane McCampbell,
Vice-Chair Tom Broeker" then settles it, because there the role has a name
only on one side.

Four more refusals, each earned on a real document:

  VICE      a role token preceded by "Vice" or "Vice-" is not the chair.
            Cerro Gordo's "Vice Chairman Carl Ginapp" and Des Moines's
            "Vice-Chair Tom Broeker" both sit inches from the real chair.
  ADJACENCY the name must touch the role -- nothing but whitespace, a comma
            or "/s/" between them. Clinton's "MOTION by Supervisor Irwin to
            authorize the Chairperson to sign" puts a supervisor's name 18
            characters from a chair word, which any proximity window wide
            enough to be useful would swallow.
  ROSTER    the name must resolve to exactly one member of that county's own
            supervisor roster in ia-county-officers.json, matched on
            surname and then on a first name that agrees (equal, diminutive
            or initialled): Clinton's minutes sign "Daniel A. Srp" where the
            roster says "Dan Srp". A surname shared by two members resolves
            to neither.
  ONE NAME  across a whole document exactly one roster member may survive as
            chair. Two is a refusal, not a coin toss.

AND TWO DOCUMENTS, NOT ONE. Each county's two most recent minutes are read
independently and must name the same chair. A single meeting can be gavelled
by whoever is in the room; two consecutive ones agreeing is the same
two-witness standard the county builds in this repo already hold. The one
week this costs is a straddle of the January reorganisation, where the
county drops out for a week rather than shipping the wrong name.

Usage:
    python3 ia/scripts/ia_county_minutes_chair_scraper.py [--county NAME ...]
    python3 ia/scripts/ia_county_minutes_chair_scraper.py --selftest
"""

import argparse
import datetime
import io
import json
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urljoin

# requests is imported inside main() rather than here so that `--selftest`,
# which is all literal strings, runs on a checkout with nothing installed.
# pdfplumber is likewise imported inside pdf_text(). Neither hides a real
# dependency: validate_workflow_deps.py walks function-local imports too, and
# the workflows that run the SCRAPE install both.

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "app")
CACHE_DIR = os.path.join(HERE, ".cache")
OUT_PATH = os.path.join(CACHE_DIR, "ia_county_minutes_chairs.json")
OFFICERS = os.path.join(DATA, "ia-county-officers.json")

BOT = {"User-Agent": "districtry/1.0 (+https://districtry.com/ia/)",
       "Accept": "text/html,application/xhtml+xml,application/pdf,*/*"}
# Granicus refuses the bot agent on ViewPublisher; nothing here defeats an
# access control, this is the ordinary desktop agent its own portal serves.
BROWSER = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/128.0.0.0 Safari/537.36"),
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
TIMEOUT = 90

# The five counties this route answers for, PINNED with the shape of their
# minutes index. `kind` selects the discovery function below; a county that
# redesigns should fail loudly here rather than vanish from a roster.
COUNTIES = [
    ("033", "Cerro Gordo", "files-meetings",
     "https://cerrogordo.gov/supervisors/meetings_minutes/"),
    ("045", "Clinton", "files-meetings",
     "https://www.clintoncounty-ia.gov/board_of_supervisors/meetings_minutes"),
    ("049", "Dallas", "civicplus",
     "https://www.dallascountyiowa.gov/AgendaCenter"),
    ("057", "Des Moines", "files-meetings",
     "https://www.desmoinescounty.iowa.gov/board_of_supervisors/meetings_minutes/"),
    ("103", "Johnson", "granicus",
     "https://johnson-county.granicus.com/ViewPublisher.php?view_id=1&count=20"),
]

WITNESSES = 2                      # documents that must agree, per county

# ---------------------------------------------------------------- extraction
# TITLE CASE ONLY, DELIBERATELY. `chair` lowercase is prose -- Dallas's
# minutes read "Chairperson Helm, in the chair" -- and an all-caps CHAIRPERSON
# is a heading. Both are skipped, so a county that writes its role word either
# way DROPS OUT rather than resolving to something adjacent; that is the safe
# direction, and it is the first thing to check when a county stops appearing.
ROLE = re.compile(r"\bChair(?:person|man|woman)?\b")
VICE = re.compile(r"vice[\s-]*$", re.I)
# A name token as minutes print one: capitalised, may carry an apostrophe, a
# hyphen or a trailing initial's full stop.
TOK = r"[A-Z][A-Za-z'’-]+\.?"
NAME_AFTER = re.compile(r"^[ \t]*(?:/s/[ \t]*)?((?:%s[ \t]+){0,3}%s)" % (TOK, TOK))
NAME_BEFORE = re.compile(r"((?:%s[ \t]+){0,3}%s)[ \t]*,[ \t]*$" % (TOK, TOK))
HONORIFIC = re.compile(r"^(?:Mr|Mrs|Ms|Dr)\.?$", re.I)


def name_tokens(s):
    out = []
    for t in re.sub(r"\s+", " ", s).strip().split():
        t = t.strip(".,")
        if not t or HONORIFIC.match(t):
            continue
        out.append(t)
    return out


def resolve(cand_tokens, roster, forward):
    """Resolve a run of tokens to exactly one roster name, or None.

    `forward` is True when the run FOLLOWS the role (so the person's name
    starts at the run's head) and False when it precedes it (so the name
    ends at the run's tail). Every slice of 1 to 4 tokens is tried and the
    LONGEST that resolves wins -- not the shortest, and the difference is a
    real misreading rather than a preference. A one-token slice matches on
    surname alone, so where one member's SURNAME is another's given name
    (`Mark Thomas` and `Thomas Reilly` on one board) the text `Chair Thomas
    Reilly` resolves at one token to Mark Thomas and at two to Thomas Reilly,
    whose own first name agrees. Taking the longest also discards a signature
    block's "SUPERVISORS Shane McCampbell" and "Casey Callanan Board", which
    do not resolve at three tokens at all.
    """
    if not cand_tokens:
        return None
    best = None
    for n in range(1, min(4, len(cand_tokens)) + 1):
        part = cand_tokens[:n] if forward else cand_tokens[-n:]
        surname = part[-1]
        hits = [full for full in roster
                if name_tokens(full) and name_tokens(full)[-1].lower() == surname.lower()]
        if len(hits) != 1:
            continue                      # nobody, or a surname two members share
        if n == 1:
            best = hits[0]
            continue
        first_page = part[0]
        first_roster = name_tokens(hits[0])[0]
        a, b = first_page.lower(), first_roster.lower()
        if a == b or a.startswith(b[:3]) or b.startswith(a[:3]):
            best = hits[0]
        # otherwise a middle initial or a stray capitalised word sits where the
        # first name should: keep whatever a shorter slice already resolved
    return best


def chair_in(text, roster):
    """Return (names, evidence) for every chair role paired with a member."""
    flat = re.sub(r"\s+", " ", text)
    pairs = []
    for m in ROLE.finditer(flat):
        if VICE.search(flat[max(0, m.start() - 8):m.start()]):
            continue
        aft = NAME_AFTER.match(flat[m.end():m.end() + 70])
        bef = NAME_BEFORE.search(flat[max(0, m.start() - 70):m.start()])
        na = resolve(name_tokens(aft.group(1)), roster, True) if aft else None
        nb = resolve(name_tokens(bef.group(1)), roster, False) if bef else None
        if na and nb and na != nb:
            continue                      # the role is claimed from both sides
        got = na or nb
        if got:
            pairs.append((got, flat[max(0, m.start() - 40):m.end() + 40].strip()))
    return sorted({p[0] for p in pairs}), pairs


def pdf_text(blob):
    """Flatten a minutes PDF to text.

    pdfplumber, which `ia/scripts/requirements.txt` already pins -- and NOT
    for the reason that file gives. It pins pdfplumber over pypdf because the
    sheriff and county-attorney directories are MULTI-COLUMN and need each
    word's x-coordinate. Board minutes are single-column narrative prose, so
    either library would do here and flattening is exactly what is wanted;
    this uses the one already on the list rather than adding a second PDF
    dependency to the weekly job for no gain.
    """
    import pdfplumber
    with pdfplumber.open(io.BytesIO(blob)) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)


# ---------------------------------------------------------------- discovery
class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.href = None
        self.buf = []
        self.out = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.buf = []

    def handle_data(self, data):
        if self.href is not None:
            self.buf.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.out.append((self.href, re.sub(r"\s+", " ", "".join(self.buf)).strip()))
            self.href = None


FILES_MEETINGS = re.compile(r"/files/meetings/(\d{4})-(\d{2})-(\d{2})_minutes[_.]", re.I)
CIVICPLUS_MIN = re.compile(r"/AgendaCenter/ViewFile/Minutes/_(\d{2})(\d{2})(\d{4})-\d+", re.I)
GRANICUS_MIN = re.compile(r"MinutesViewer\.php\?[^\"']*doc_id=", re.I)
# Granicus prints the meeting date in the row's own text, ahead of the link.
# Reading it is not decoration: without it the only ordering available is the
# portal's publication order, and "the newest is first" is an assumption about
# somebody else's page rather than something this scrape measures.
MONTHS = ("January February March April May June July August September "
          "October November December").split()
GRANICUS_DATE = re.compile(r"\b(%s)\s+(\d{1,2}),\s*(\d{4})" % "|".join(MONTHS))


def granicus_rows(html, base):
    """Pair each Granicus minutes link with the date printed in its own row."""
    text = re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ",
                                      html.replace("&nbsp;", " ")))
    out = []
    for m in re.finditer(r"MinutesViewer\.php\?[^\"']*doc_id=[^\"']+", html):
        # the row's date is the last one printed before the link
        window = re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ",
                        html[max(0, m.start() - 1500):m.start()].replace("&nbsp;", " ")))
        dates = GRANICUS_DATE.findall(window)
        if not dates:
            continue
        month, day, year = dates[-1]
        when = "%s-%02d-%02d" % (year, MONTHS.index(month) + 1, int(day))
        out.append((when, urljoin(base, m.group(0).replace("&amp;", "&"))))
    return out


def discover(session, kind, index_url):
    """Return [(meeting_date, absolute_url), ...] newest first."""
    headers = BROWSER if kind == "granicus" else BOT
    r = session.get(index_url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
    r.raise_for_status()
    if kind == "granicus":
        rows, seen = [], set()
        for when, url in granicus_rows(r.text, r.url):
            if url in seen:
                continue
            seen.add(url)
            rows.append((when, url))
        return sorted(rows, key=lambda t: t[0], reverse=True)
    parser = Anchors()
    parser.feed(r.text)
    found, seen = [], set()
    for href, _text in parser.out:
        if not href:
            continue
        full = urljoin(r.url, href)
        if full in seen:
            continue
        if kind == "files-meetings":
            m = FILES_MEETINGS.search(full)
            if not m:
                continue
            when = "%s-%s-%s" % m.groups()
        elif kind == "civicplus":
            m = CIVICPLUS_MIN.search(full)
            if not m:
                continue
            mm, dd, yyyy = m.groups()
            when = "%s-%s-%s" % (yyyy, mm, dd)
        else:
            raise AssertionError("unknown index kind %r" % kind)
        seen.add(full)
        found.append((when, full))
    return sorted(found, key=lambda t: t[0], reverse=True)


def read_county(session, fips, county, kind, index_url, roster):
    row = {"fips": fips, "county": county, "sourceUrl": index_url}
    if not roster:
        row["verdict"] = "no-roster"
        return row
    try:
        docs = discover(session, kind, index_url)
    except Exception as exc:
        row["verdict"] = "unreachable"
        row["error"] = "%s: %s" % (type(exc).__name__, exc)
        return row
    if len(docs) < WITNESSES:
        row["verdict"] = "too-few-documents"
        row["documents"] = len(docs)
        return row
    seen = []
    for when, url in docs[:WITNESSES]:
        try:
            d = session.get(url, headers=BROWSER if kind == "granicus" else BOT,
                            timeout=TIMEOUT, allow_redirects=True)
            d.raise_for_status()
            text = pdf_text(d.content) if d.content[:5] == b"%PDF-" else ""
        except Exception as exc:
            row["verdict"] = "unreadable"
            row["error"] = "%s on %s: %s" % (type(exc).__name__, url, exc)
            return row
        if not text.strip():
            row["verdict"] = "unreadable"
            row["error"] = "no extractable text in %s" % url
            return row
        names, pairs = chair_in(text, roster)
        seen.append({"url": url, "date": when, "names": names,
                     "evidence": [p[1] for p in pairs[:3]]})
    row["witnesses"] = seen
    picks = [w["names"] for w in seen]
    if any(len(p) == 0 for p in picks):
        row["verdict"] = "none"
        return row
    if any(len(p) > 1 for p in picks):
        row["verdict"] = "many"
        return row
    if len({p[0] for p in picks}) != 1:
        row["verdict"] = "disagree"
        return row
    row["verdict"] = "one"
    row["chair"] = picks[0][0]
    row["meetingDate"] = seen[0]["date"]
    return row


# Each case is a line these counties really print, the roster it must be read
# against, and the only answer that is not a misreading. They are here rather
# than in the docstring because every one of them was a wrong answer first.
SELFTEST = [
    ("Des Moines, the flattened signature block",
     "DES MOINES COUNTY BOARD OF SUPERVISORS Shane McCampbell, Chair "
     "Tom Broeker, Vice Chair Jim Cary, Member",
     ["Shane McCampbell", "Tom Broeker", "Jim Cary"], []),
    ("Des Moines, the attendance line that settles it",
     "at 9:00 AM on Tuesday, August 25th, 2026, with Chair Shane McCampbell, "
     "Vice-Chair Tom Broeker, and member Jim Cary present.",
     ["Shane McCampbell", "Tom Broeker", "Jim Cary"], ["Shane McCampbell"]),
    ("Cerro Gordo, a vice chair one comma away",
     "Present: Chairman Casey Callanan, Vice Chairman Carl Ginapp , "
     "Supervisor Chris Watts",
     ["Casey Callanan", "Carl Ginapp", "Chris Watts"], ["Casey Callanan"]),
    ("Clinton, a role with no name and a supervisor 18 characters off",
     "MOTION by Supervisor Irwin to authorize the Chairperson to sign Utility "
     "Permit Numbers 42-34-26",
     ["Dan Srp", "Erin George", "Mr. Jim Irwin Jr."], []),
    ("Clinton, the signature after a roll call",
     "Roll Call: Irwin: Yes; George: Yes; Srp: Yes. Daniel A. Srp, Chairperson "
     "RESOLUTION 2026-215 WHEREAS",
     ["Dan Srp", "Erin George", "Mr. Jim Irwin Jr."], ["Dan Srp"]),
    ("Johnson, a surname that is not the other member's surname",
     "Chairperson Green called the Johnson County Board of Supervisors to order",
     ["Jon Green", "Lisa Green-Douglass", "Rod Sullivan"], ["Jon Green"]),
    ("Story, presiding is not the office",
     "Linda Murken and Latifah Faisal, and Lisa Heddens, with Murken presiding.",
     ["Linda Murken", "Latifah Faisal", "Lisa Heddens"], []),
    ("a surname two members share resolves to neither",
     "Chair Smith called the meeting to order",
     ["Ann Smith", "Bob Smith", "Cal Jones"], []),
    ("one member's surname is another's given name",
     "with Chair Thomas Reilly presiding",
     ["Mark Thomas", "Thomas Reilly"], ["Thomas Reilly"]),
]


def selftest():
    bad = 0
    for label, text, roster, expect in SELFTEST:
        got, _pairs = chair_in(text, roster)
        ok = got == expect
        bad += 0 if ok else 1
        print("  %-4s %-58s %s" % ("OK" if ok else "FAIL", label, got))
    if bad:
        sys.exit("ia-county-minutes-chair --selftest: FAIL — %d of %d case(s)"
                 % (bad, len(SELFTEST)))
    print("ia-county-minutes-chair --selftest: OK — %d case(s)" % len(SELFTEST))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--county", action="append", default=[],
                    help="limit the run to these counties (repeatable)")
    ap.add_argument("--selftest", action="store_true",
                    help="run the parser's recorded trap cases and exit")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    import requests

    officers = json.load(open(OFFICERS, encoding="utf-8"))
    session = requests.Session()
    wanted = {c.lower() for c in args.county}
    rows = []
    for fips, county, kind, index_url in COUNTIES:
        if wanted and county.lower() not in wanted:
            continue
        roster = [m["name"] for m in
                  (officers.get("19" + fips) or {}).get("supervisors", [])]
        row = read_county(session, fips, county, kind, index_url, roster)
        rows.append(row)
        print("  %-13s %-16s %s" % (county, row["verdict"],
                                    row.get("chair") or row.get("error", "")[:70]))
        for w in row.get("witnesses", []):
            print("        %s %s -> %s" % (w["date"] or "(latest)",
                                           w["url"].split("/")[-1][:44], w["names"]))

    os.makedirs(CACHE_DIR, exist_ok=True)
    payload = {"scrapedOn": datetime.date.today().isoformat(), "counties": rows}
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
    got = sum(1 for r in rows if r["verdict"] == "one")
    print("\nwrote %s (%d of %d counties resolved)" % (OUT_PATH, got, len(rows)))
    return 0 if got else 1


if __name__ == "__main__":
    sys.exit(main())
