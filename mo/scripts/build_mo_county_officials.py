#!/usr/bin/env python3
"""
Build mo/data/app/mo-county-officials.json: every Missouri county's governing
body and its other elected officers, read from the Missouri Secretary of
State's Missouri Roster, so the county card can name who governs the county a
reader clicked without reaching a third-party host at click time.

THE SOURCE, MEASURED 2026-10-21. The Secretary of State prints a Missouri
Roster every two years and links it from www.sos.mo.gov/pubs ("2025-2026
Missouri Roster" that day, a 256-page PDF). Its section "Missouri County
Officials" lists, county by county, every county official the county clerks
furnished: the office, the person's name, party, office address, telephones
and e-mail address. All 114 counties and the City of St. Louis are in it. The
script follows whichever edition the publications page links, so the
2027-2028 edition is read the week it appears.

WHAT EACH COUNTY'S GOVERNING BODY IS. 110 counties are governed by a county
commission of a presiding commissioner, elected countywide, and two district
commissioners (RSMo 49.010-49.020); Clay County's commission has seven seats
and Cass County calls its district seats associate commissioners. Four
counties have charters: St. Louis, St. Charles and Jefferson counties each
elect a county executive and a seven-member council by district, and Jackson
County a county executive and a nine-member legislature, six seats by district
and three by groups of districts. The City of St. Louis is a county of its own,
governed by its mayor and Board of Aldermen; the roster names the mayor and the
Board's president and not the fourteen ward aldermen, so the file says so
rather than inventing the rest. The script checks every county against that
shape and stops on any difference.

ONE NAME THE ROSTER PRINTS IS NOT SHIPPED. Jackson County's voters recalled
County Executive Frank White Jr. on 30 September 2025, after this edition was
printed, so STALE carries the office with the date and the election board's
results page, and the card says the office is not named rather than naming
him. An entry there must still match the roster word for word, so it stops
the build once a new edition no longer prints the name.

THREE CHARTER COUNTIES' OWN PAGES NAME THEIR MEMBERS, AND WIN. The roster was
printed in June 2025, so it can be a member behind. Read on 2026-10-26, the
pages of Jefferson County (www.jeffcomo.gov/399/County-Council), St. Charles
County (www.sccmo.org/1352/Council-Members) and Jackson County
(www.jacksongov.org/Government/County-Legislature) list every seat of their
council or legislature, and Jefferson's and Jackson's differ from the roster:
Jefferson's 5th District is Tim Bennett Jr. where the roster prints Scott Seek,
and Jackson's 3rd District at Large is Megan L. Smith where it prints Megan L.
Marshall. So COUNTY_PAGES reads each page every run, and its names ship. A
member whose surname matches the roster's within one letter (Lori Arons, whom
the roster prints Lori Aronns) is the same person and keeps the telephone,
e-mail address and party the roster prints beside them; anyone else ships with
only what the county's page prints beside them (St. Charles prints each
member's e-mail address). A page that stops listing every seat stops the
build. St. Louis County's own page answers this script with a managed
challenge (HTTP 403, "Just a moment...", 2026-10-26), which is an access
control, so its council is named from the roster alone.

HOW THE PDF IS READ. pdftotext (poppler-utils) writes every word with its page,
text flow and position (-tsv). Each page prints two columns, and on pages where
two counties start side by side poppler's own reading order takes both
headings first and then both bodies, so the script orders each page's flows
itself: left column top to bottom, then the right. The running head and page
number are dropped and must be the only text above the columns. The default
text mode was tried first and is not used: it joins a word broken at a line's
end and drops the hyphen, which turned "665-" "3350" into "6653350" and
shannon-county.com into shannoncounty.com; the word list keeps every hyphen as
printed. Discretionary hyphens (U+00AD) are invisible marks and are removed.

WHAT SHIPS, AND WHAT NEVER DOES. For each official: the office as printed, the
name, the party, whether the roster marks them appointed, the first telephone
printed in their own entry and the first e-mail address. A telephone or
address printed beside two or more officials of one county belongs to an
office, not a person (the fleet's rule since 2026-10-17): printed beside two or
more members of the governing body, it ships as the body's own; otherwise it
ships nowhere. An address is printed as the body's office only when two or
more members print it word for word; no official's own address ships, because
for some offices (a coroner, a surveyor) the address printed is not a public
building. Fax numbers never ship. Appointed staff (health directors, road
supervisors, emergency managers and the like) are not carried; the elected
offices in OFFICER_TITLES are, along with anyone the roster marks appointed to
one of them.

Honesty: names are never guessed and nothing is carried over from an earlier
run. A county whose entries do not match the expected shape stops the build.

ROBOTS. www.sos.mo.gov's robots.txt (199 bytes, read 2026-10-21 through
scripts/robots_policy.py with this script's own User-Agent) disallows nothing
this script reads and states no delay; every fetch is still paced at one
second. Read 2026-10-26 the same way: www.jeffcomo.gov (2,643 bytes) and
www.sccmo.org (2,901 bytes) disallow neither page and state Crawl-delay 10,
which the HostPacer honours; www.jacksongov.org (14,608 bytes) disallows
neither and states no delay.

Usage:
    python3 mo/scripts/build_mo_county_officials.py [output_dir]
    python3 mo/scripts/build_mo_county_officials.py --save DIR [output_dir]
    python3 mo/scripts/build_mo_county_officials.py --offline DIR [output_dir]
    python3 mo/scripts/build_mo_county_officials.py --check

--check reads the SHIPPED file and nothing else, offline: one record for each
of the 115 GEOIDs in state-counties.json under its own name, every county's
body in the shape the build requires (the charter counties, the city and the
commission counties, seat counts included), the STALE office still not named,
every seat and office either named or marked vacant, no fax number, and the
same floors the build applies. It proves the file is what a build writes; it
never proves the roster has not moved since.

--save writes the publications page, the roster PDF and the three county pages
into DIR (sos-pubs.html, mo-roster.pdf and COUNTY_PAGES' files), reading back any it already holds; --offline reads them back
instead of fetching, for building and testing without the network.
"""

import collections
import datetime
import html as html_module
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.parse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from robots_policy import HostPacer, RobotsGate  # noqa: E402  (FLEET_SHARED)

USER_AGENT = "districtry/1.0 (+https://districtry.com/mo/)"
MIN_PACE_SECONDS = 1.0
ATTEMPTS = 3
RETRY_SECONDS = 5.0

SOS_PUBS = "https://www.sos.mo.gov/pubs"
# ".../MORoster/2025-2026_MO_Roster.pdf">2025-2026 Missouri Roster<
MO_ROSTER_LINK_RE = re.compile(
    r'href="([^"]*MORoster[^"]*\.pdf)"[^>]*>\s*(\d{4})\s*[-–]\s*(\d{4})\s+Missouri Roster\s*<',
    re.I)

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
OUT_NAME = "mo-county-officials.json"
COUNTIES_FILE = os.path.join(DEFAULT_OUT_DIR, "state-counties.json")

SECTION_START = "Missouri County Officials"
SECTION_END = "Classification of Municipalities"
# The band above the columns where each page prints its running head and page
# number (36 points from the top on every page measured); columns start at 61.
HEAD_BAND = 50.0
RUNNING_HEADS = ("Missouri Roster", "County Officials")

# The charter counties and the city, by county GEOID.
CHARTER = {
    "29189": {"kind": "council", "body": "St. Louis County Council", "seats": 7},
    "29183": {"kind": "council", "body": "St. Charles County Council", "seats": 7},
    "29099": {"kind": "council", "body": "Jefferson County Council", "seats": 7},
    "29095": {"kind": "legislature", "body": "Jackson County Legislature", "seats": 9},
}
ST_LOUIS_CITY = "29510"
# Commission counties whose commission is not a presiding commissioner and two
# district commissioners, measured in the 2025-2026 edition.
COMMISSION_SEATS = {"29047": 7}

# A name the roster prints that is known to be out of date, by GEOID and the
# office's key. "printed" must match the roster exactly, so the entry stops the
# build when an edition no longer prints it and has to be re-read.
STALE = {
    ("29095", "executive"): {
        "printed": "Frank White Jr.",
        "why": ("Jackson County voters recalled Frank White Jr., whom the Secretary "
                "of State's roster names, on 30 September 2025, after the roster was "
                "printed. This map does not name the county executive yet."),
        "sourceUrl": "https://jcebmo.org/september-30-2025-special-recall-election/",
        "checked": "2026-10-21",
    },
}

# The charter counties whose own pages list every seat of their council or
# legislature, read every run (see the module docstring), and the seat labels
# each page's words map to.
COUNTY_PAGES = {
    "29099": {"url": "https://www.jeffcomo.gov/399/County-Council",
              "file": "jefferson-council.html", "parse": "jefferson",
              "source": "Jefferson County's own website (jeffcomo.gov)"},
    "29183": {"url": "https://www.sccmo.org/1352/Council-Members",
              "file": "stcharles-council.html", "parse": "stcharles",
              "source": "St. Charles County's own website (sccmo.org)"},
    "29095": {"url": "https://www.jacksongov.org/Government/County-Legislature",
              "file": "jackson-legislature.html", "parse": "jackson",
              "source": "Jackson County's own website (jacksongov.org)"},
}
ORDINAL_SEATS = {"1": "First", "2": "Second", "3": "Third", "4": "Fourth",
                 "5": "Fifth", "6": "Sixth", "7": "Seventh"}
ORDINAL_WORDS = {"1st": "1", "2nd": "2", "3rd": "3", "4th": "4", "5th": "5",
                 "6th": "6", "7th": "7"}

# The elected county offices carried on the card, by the title the roster
# prints (asterisks removed) -> the label the card shows. Anything else the
# roster lists is appointed staff and is not carried.
OFFICER_TITLES = {
    "Assessor": "Assessor",
    "Auditor": "Auditor",
    "County Auditor": "Auditor",
    "Clerk County Commission": "County Clerk",
    "County Clerk": "County Clerk",
    "County Clerk/Election Authority": "County Clerk",
    "Clerk Circuit Court": "Circuit Clerk",
    "Clerk Circuit Court Interim": "Circuit Clerk (interim)",
    "Circuit Clerk": "Circuit Clerk",
    "Circuit Court Clerk": "Circuit Clerk",
    "Clerk of Circuit Court": "Circuit Clerk",
    # Worth County's circuit clerk is printed under "Circuit Court" alone (a
    # courts.mo.gov address, sorted where "Clerk Circuit Court" sorts).
    "Circuit Court": "Circuit Clerk",
    "Clerk Circuit Court and ex officio Recorder of Deeds": "Circuit Clerk and Recorder of Deeds",
    "Circuit Court Clerk and ex officio Recorder of Deeds": "Circuit Clerk and Recorder of Deeds",
    "Collector of Revenue": "Collector of Revenue",
    "Collector/Treasurer": "Collector and Treasurer",
    "Collector-Treasurer": "Collector and Treasurer",
    "Treasurer/Collector": "Collector and Treasurer",
    "Treasurer and ex officio Collector of Revenue": "Treasurer and Collector of Revenue",
    "Treasurer": "Treasurer",
    "Coroner": "Coroner",
    "Prosecuting Attorney": "Prosecuting Attorney",
    "Circuit Attorney": "Circuit Attorney",
    "Public Administrator": "Public Administrator",
    "Recorder of Deeds": "Recorder of Deeds",
    "Recorder of Deeds and Vital Records Registrar": "Recorder of Deeds",
    "Sheriff": "Sheriff",
    "County Surveyor": "Surveyor",
    "Surveyor": "Surveyor",
    "County Surveyor and Engineer": "Surveyor",
    "Comptroller": "Comptroller",
    "License Collector": "License Collector",
}
# The order offices are listed on the card.
OFFICER_ORDER = ["County Clerk", "Assessor", "Auditor", "Collector of Revenue",
                 "Collector and Treasurer", "Treasurer and Collector of Revenue",
                 "Treasurer", "Comptroller", "License Collector", "Recorder of Deeds",
                 "Circuit Clerk and Recorder of Deeds", "Circuit Clerk",
                 "Circuit Clerk (interim)", "Prosecuting Attorney", "Circuit Attorney",
                 "Sheriff", "Coroner", "Public Administrator", "Surveyor"]
# A word in a title that marks the governing body or its executive. A title
# carrying one that the parser does not place stops the build.
BODY_WORDS = re.compile(r"\b(Commissioner|Council|Legislature|Aldermen|Executive|Mayor)\b")
# Offices whose titles carry those words and are not the governing body.
NOT_BODY = {"Clerk County Commission", "Clerk County Legislature",
            "County Clerk and Administrative Director to the Council",
            "Northern Road Commissioner", "Southern Road Commissioner"}

# Floors: the share of counties naming each of these officers on 2026-10-21
# was 105-113 of 115. A layout change that loses one shows here first.
OFFICER_FLOORS = {"Sheriff": 105, "Prosecuting Attorney": 100, "Assessor": 100,
                  "County Clerk": 95, "Coroner": 90, "Public Administrator": 95}

PARTY_NAMES = {"R": "Republican", "D": "Democratic", "I": "Independent",
               "L": "Libertarian", "G": "Green", "C": "Constitution"}
NAME_SUFFIXES = {"Jr.", "Sr.", "II", "III", "IV"}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\(\d{3}\)\s*\d{3}-\d{4}(?:,?\s*[Ee]xt\.?\s*\d+)?")
PARTY_RE = re.compile(r"^\(([A-Z])\)$")

# A line that ends an entry: an e-mail address or web address, a telephone, an
# extension, a vacancy, a ZIP code after a town's name.
ENTRY_END = re.compile(
    r"(@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|\d{3}-\d{4}|\d{3}-[A-Z]{4}|[Ee]xt\.?\s*\d+|\(Vacancy\)"
    r"|option \d+|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:org|gov|com|net|us|edu|info)"
    r"|(?<=[A-Za-z.]) \d{5})$")
# An office title: words up to the first comma, then that comma.
TITLE_RE = re.compile(r"^[A-Z][A-Za-z0-9/&’'. -]*?\*{0,2},(\s|$)")
# The first entry of a county (offices are listed alphabetically, so it is one
# of these), which also ends the county's description above it.
FIRST_TITLE_RE = re.compile(
    r"^(Assessor|Auditor|Board|Chief|Circuit|City|Clerk|Collector|Comptroller|Commissioner"
    r"|Coroner|Council|County|Director|Emergency|Highway|License|Mayor|Medical|Presiding"
    r"|Prosecuting|Public|Recorder|Sheriff|Surveyor|Treasurer)\b")
COMPLETE_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")

_SESSION = None
_GATE = None
_PACER = None
_LAST = {}


def session():
    global _SESSION
    if _SESSION is None:
        import requests

        _SESSION = requests.Session()
        _SESSION.headers["User-Agent"] = USER_AGENT
    return _SESSION


def gate():
    global _GATE, _PACER
    if _GATE is None:
        _GATE = RobotsGate(session(), USER_AGENT)
        _PACER = HostPacer(_GATE)
    return _GATE


def fetch(url, binary=False):
    import requests

    ok, why = gate().allows(url)
    host = urllib.parse.urlsplit(url).netloc
    if host not in _LAST:
        print("robots.txt %s: %s" % (host, why), file=sys.stderr)
        _LAST[host] = 0.0
    if not ok:
        raise SystemExit("FAIL: robots.txt refuses %s (%s)" % (url, why))
    last = None
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_SECONDS * attempt)
        wait = MIN_PACE_SECONDS - (time.time() - _LAST[host])
        if wait > 0:
            time.sleep(wait)
        try:
            with _PACER.hold(url):
                resp = session().get(url, timeout=300)
            _LAST[host] = time.time()
            resp.raise_for_status()
            if binary:
                return resp.content
            resp.encoding = resp.encoding if resp.encoding and "utf" in resp.encoding.lower() \
                else "utf-8"
            return resp.text
        except requests.RequestException as exc:  # reset, timeout, 5xx
            _LAST[host] = time.time()
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (url, ATTEMPTS, last))


class Pages:
    """Fetch, save or replay the files one run reads."""

    def __init__(self, offline=None, save=None):
        self.offline, self.save = offline, save

    def get(self, name, url, binary=False):
        source = self.offline or (self.save if self.save and
                                  os.path.exists(os.path.join(self.save, name)) else None)
        if source:
            with open(os.path.join(source, name), "rb" if binary else "r",
                      **({} if binary else {"encoding": "utf-8"})) as fh:
                return fh.read()
        body = fetch(url, binary)
        if self.save:
            path = os.path.join(self.save, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb" if binary else "w",
                      **({} if binary else {"encoding": "utf-8"})) as fh:
                fh.write(body)
        return body


def reads_as_name(text):
    """Letters (accented too), spaces and . ' ’ ( ) -, at least two words."""
    return (len(text.split()) >= 2 and text[0].isupper() and text[-1] not in " -"
            and all(c.isalpha() or c in " .'\u2019()-" for c in text))


def letters(text):
    """Lower-case letters only, accents dropped: O’Laughlin -> olaughlin."""
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text if c.isalpha() and not unicodedata.combining(c)).lower()


# --- the PDF ----------------------------------------------------------------

def roster_url(pubs):
    """(pdf url, 'YYYY-YYYY') of the newest Missouri Roster the page links."""
    found = []
    for href, first, second in MO_ROSTER_LINK_RE.findall(pubs):
        found.append((int(first), int(second), urllib.parse.urljoin(SOS_PUBS, html_module.unescape(href))))
    if not found:
        raise SystemExit("FAIL: www.sos.mo.gov/pubs links no 'YYYY-YYYY Missouri Roster' "
                         "PDF — the page changed")
    first, second, url = max(found)
    return url, "%d–%d" % (first, second)


def pdf_words(pdf_bytes):
    """pdftotext -tsv over the whole PDF."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "roster.pdf")
        with open(path, "wb") as fh:
            fh.write(pdf_bytes)
        try:
            out = subprocess.run(["pdftotext", "-tsv", "-enc", "UTF-8", path, "-"],
                                 check=True, capture_output=True, timeout=600)
        except FileNotFoundError:
            raise SystemExit("FAIL: pdftotext is not installed (apt-get install "
                             "poppler-utils)")
    return out.stdout.decode("utf-8", "replace")


def reading_order(tsv):
    """[(page, head, lines)] with each page's columns read left then right.

    Each text block poppler finds is placed in the left or right column by
    its centre and read top to bottom; a block wider than a column (a
    section's heading or opening paragraph) goes before the columns it sits
    above. Blocks in the band above the columns are the page's head.
    """
    pages = collections.OrderedDict()
    widths = {}
    for row in tsv.split("\n")[1:]:
        f = row.split("\t")
        if len(f) < 12:
            continue
        # pdftotext -tsv: level, page, flow, block, line, word, left, top,
        # width, height, conf, text. A level-3 row ("###FLOW###") is one
        # block of a flow and carries that block's box.
        level, page, block = f[0], int(f[1]), (int(f[2]), int(f[3]))
        if level == "1":
            widths[page] = float(f[8])
            pages[page] = collections.OrderedDict()
        elif level == "3":
            pages[page][block] = {"left": float(f[6]), "top": float(f[7]),
                                  "width": float(f[8]), "lines": [], "key": None}
        elif level == "5":
            fl = pages[page][block]
            if f[4] != fl["key"]:
                fl["lines"].append([])
                fl["key"] = f[4]
            fl["lines"][-1].append(f[11])
    out = []
    for page, flows in pages.items():
        width = widths[page]
        head, body = [], []
        for fl in flows.values():
            text = [" ".join(words) for words in fl["lines"]]
            if fl["top"] < HEAD_BAND:
                head.extend(text)
            else:
                body.append((fl, text))
        columns = [fl for fl, _ in body if fl["width"] <= width * 0.55]
        top = min((fl["top"] for fl in columns), default=float("inf"))

        def rank(item):
            fl = item[0]
            if fl["width"] > width * 0.55:
                return (-1 if fl["top"] < top else 2, fl["top"])
            return (0 if fl["left"] + fl["width"] / 2 < width / 2 else 1, fl["top"])

        lines = []
        for _, text in sorted(body, key=rank):
            lines.extend(text)
        out.append((page, head, lines))
    return out


def county_section(pages):
    """The section's lines, its page heads checked and dropped."""
    lines, inside, done = [], False, False
    for page, head, body in pages:
        if not inside and SECTION_START in body:
            start = body.index(SECTION_START)
            if not any("following list of officials" in line for line in body[start:start + 3]):
                continue
            inside = True
            body = body[start + 1:]
        if not inside:
            continue
        ends = [i for i, line in enumerate(body) if line.startswith(SECTION_END)]
        if ends:
            lines.extend(body[:ends[0]])
            done = True
            break
        if any(item.startswith(SECTION_END) for item in head):
            done = True
            break
        for item in head:
            if not (item in RUNNING_HEADS or re.fullmatch(r"\d{1,3}", item)):
                raise SystemExit("FAIL: roster page %d prints %r above its columns, where "
                                 "only a running head and page number were — the page "
                                 "layout changed" % (page, item))
        lines.extend(body)
    if not done:
        raise SystemExit("FAIL: the roster has no %r section ending at %r"
                         % (SECTION_START, SECTION_END))
    return [line.strip() for line in lines
            if line.strip() and line.strip() != "*Appointed"
            and not re.fullmatch(r"_+", line.strip())]


def join(a, b):
    """Line b appended to text a, the way the roster's line break meant it."""
    if a.endswith("­"):
        return a[:-1] + b
    last = a.rsplit(" ", 1)[-1]
    first = b.split(" ", 1)[0]
    if a.endswith("-"):
        # A hyphen ends a line only where the roster printed one (a telephone,
        # an e-mail address), except in a word broken across the line.
        if "@" in last or "@" in first or re.search(r"\d-$", last):
            return a + b
        if re.search(r"[A-Za-z]{2}-$", last) and re.match(r"[a-z]", first):
            return a[:-1] + b
        return a + b
    # An e-mail address broken after its @ or one of its dots, or at its domain.
    if ("@" in last and not COMPLETE_EMAIL_RE.fullmatch(last.rstrip(";,"))
            and re.match(r"^[A-Za-z0-9][A-Za-z0-9.-]*[;,]?$", first)):
        return a + b
    if "@" in first and re.fullmatch(r"[A-Za-z0-9._%+-]*[._-]", last):
        return a + b
    return a + " " + b


def starts_entry(body, j):
    """Does body[j] open an entry ("Office, ...")? The office may wrap onto
    the following lines before its comma."""
    if not re.match(r"[A-Z]", body[j]):
        return False
    text = body[j]
    for k in range(1, 7):
        plain = text.replace("­", "")
        if "," in plain:
            head = plain.split(",", 1)[0]
            return (bool(TITLE_RE.match(head + ", ")) and len(head) <= 90
                    and not re.search(r"[;@()]", head))
        if j + k >= len(body):
            return False
        text = join(text, body[j + k])
    return False


def split_counties(lines, counties):
    """{GEOID: [entry text]} in roster order, checking every county appears."""
    by_name = {c["name"].lower(): c for c in counties}
    heads = [(i, by_name[line.lower()]) for i, line in enumerate(lines)
             if line.lower() in by_name]
    seen = collections.Counter(c["geoid"] for _, c in heads)
    missing = sorted(c["name"] for c in counties if c["geoid"] not in seen)
    twice = sorted(c["name"] for c in counties if seen[c["geoid"]] > 1)
    if missing or twice:
        raise SystemExit("FAIL: county headings missing %s, printed twice %s" % (missing, twice))
    # The roster lists the counties alphabetically, "St." and "Ste." read as
    # Saint and Sainte, and the City of St. Louis after them. A heading out of
    # that order means a page's columns were read in the wrong order.
    order = [c["name"] for _, c in heads]
    spelled = lambda n: n.lower().replace("ste. ", "sainte ").replace("st. ", "saint ")
    expect = sorted((n for n in order if n != "St. Louis city"), key=spelled) + ["St. Louis city"]
    if order != expect:
        raise SystemExit("FAIL: the county headings are not in the roster's alphabetical "
                         "order after reading each page's columns: %s"
                         % [n for n, m in zip(order, expect) if n != m][:5])
    out = collections.OrderedDict()
    for k, (i, county) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        body = lines[i + 1:end]
        entries = []
        for j, line in enumerate(body):
            if not entries:
                if starts_entry(body, j) and FIRST_TITLE_RE.match(line):
                    entries.append(line)
                # else: the county's description (seat, population, history)
                continue
            if ENTRY_END.search(entries[-1].replace("­", "")) and starts_entry(body, j):
                entries.append(line)
            else:
                entries[-1] = join(entries[-1], line)
        out[county["geoid"]] = [re.sub(r"\s+", " ", e.replace("­", "")).strip()
                                for e in entries]
    return out


# --- one entry --------------------------------------------------------------

def fields_of(text):
    return [f.strip() for f in text.split(",")]


def parse_entry(text, where):
    """{title, appointed, seat?, name|vacant, party?, contact} from one entry."""
    m = re.match(r"^(?P<title>[^,]+?)\s*(?P<star>\*{0,2}),\s*(?P<rest>.*)$", text)
    if not m:
        raise SystemExit("FAIL: %s: an entry with no office before its first comma: %r"
                         % (where, text[:120]))
    title, rest = m.group("title").strip(), m.group("rest")
    entry = {"title": title, "appointed": bool(m.group("star")), "raw": text}
    parts = fields_of(rest)
    if title in ("Commissioner", "Associate Commissioner", "Council Member",
                 "County Legislature", "Board of Aldermen"):
        seat = parts.pop(0)
        if seat.endswith("*"):
            entry["appointed"] = True
            seat = seat.rstrip("*").strip()
        entry["seat"] = seat
    while parts and re.fullmatch(r"\d+(?:st|nd|rd|th) (?:Judicial )?Circuit", parts[0]):
        parts.pop(0)  # Greene's circuit clerk prints the circuit: "31st Circuit"
    if parts and re.fullmatch(r"Division [IVX\d]+", parts[0]):
        entry["division"] = parts.pop(0)  # Marion has two circuit clerks
    if not parts:
        raise SystemExit("FAIL: %s: %r names nobody" % (where, text[:120]))
    name = parts.pop(0)
    if name.endswith("*"):
        entry["appointed"] = True
        name = name.rstrip("*").strip()
    if name == "(Vacancy)":
        entry["vacant"] = True
        entry["contact"] = ", ".join(parts)
        return entry
    inline = re.match(r"^(.*\S)\s+\(([A-Z])\)$", name)
    if inline:
        name, entry["party"] = inline.group(1), inline.group(2)
    while parts and "party" not in entry:
        nxt = parts[0]
        party = PARTY_RE.match(nxt)
        if party:
            entry["party"] = party.group(1)
            parts.pop(0)
        elif nxt in NAME_SUFFIXES:
            name = name + " " + parts.pop(0)
        elif re.fullmatch(r"[A-Z]{2,5}|[A-Z][A-Za-z]?\.(?:[A-Z][a-z]?\.)+", nxt):
            parts.pop(0)  # a credential after the name (NCG, CPA, Ph.D.)
        else:
            break
    entry["name"] = name
    entry["contact"] = ", ".join(parts)
    return entry


def contacts(contact):
    """(address, [phone], [email]) from the text after the party.

    Segments are separated by semicolons. The address is every segment before
    the first telephone or e-mail address; telephones are taken only from
    segments before the first fax number, and never from a fax segment.
    """
    segs = [s.strip() for s in contact.split(";") if s.strip()]
    address, phones, emails = [], [], []
    fax = False
    for seg in segs:
        has_phone = bool(PHONE_RE.search(seg))
        found = EMAIL_RE.findall(seg)
        if seg.upper().startswith("FAX"):
            fax = True
            emails.extend(found)
            continue
        if not phones and not emails and not has_phone and not found:
            address.append(seg)
            continue
        if has_phone and not fax:
            label = None
            lead = seg[:PHONE_RE.search(seg).start()].strip().lower().rstrip(":-").strip()
            if lead in ("cell", "home", "office", "mobile"):
                label = lead
            phones.append((PHONE_RE.search(seg).group(0), label))
        emails.extend(found)
    return ", ".join(address), phones, emails


def phone_text(raw):
    """'(660) 665-4423' / '(660) 542-0615, ext. 2' in one spelling."""
    m = re.match(r"\((\d{3})\)\s*(\d{3}-\d{4})(?:,?\s*[Ee]xt\.?\s*(\d+))?$", raw)
    text = "(%s) %s" % (m.group(1), m.group(2))
    if m.group(3):
        text += ", ext. %s" % m.group(3)
    return text


def phone_key(raw):
    return re.sub(r"\D", "", raw)


# --- one county -------------------------------------------------------------

def build_county(geoid, county, entries, edition, src, today, notes):
    where = county["name"]
    parsed = [parse_entry(e, where) for e in entries]
    # Who prints each telephone and address: distinct people, by name.
    phone_people = collections.defaultdict(set)
    email_people = collections.defaultdict(set)
    for p in parsed:
        if p.get("vacant"):
            continue
        _, phones, emails = contacts(p["contact"])
        for raw, _ in phones:
            phone_people[phone_key(raw)].add(letters(p["name"]))
        for e in emails:
            email_people[e.lower()].add(letters(p["name"]))

    def person(p, extra):
        row = dict(extra)
        if p.get("vacant"):
            row["vacant"] = True
            return row
        row["name"] = p["name"]
        if p.get("party"):
            if p["party"] not in PARTY_NAMES:
                raise SystemExit("FAIL: %s: party %r for %s is not one the script knows"
                                 % (where, p["party"], p["name"]))
            row["party"] = PARTY_NAMES[p["party"]]
        if p["appointed"]:
            row["appointed"] = True
        _, phones, emails = contacts(p["contact"])
        for raw, label in phones:
            if len(phone_people[phone_key(raw)]) == 1:
                row["phone"] = phone_text(raw)
                if label:
                    row["phoneLabel"] = label
                break
        for e in emails:
            if len(email_people[e.lower()]) == 1:
                row["email"] = e
                break
        if not reads_as_name(row["name"]):
            raise SystemExit("FAIL: %s: %r does not read as a person's name (entry %r)"
                             % (where, row["name"], p["raw"][:120]))
        return row

    record = collections.OrderedDict()
    record["county"] = county["name"]
    seats, members, officers, executive = [], [], [], None
    presiding = [p for p in parsed if p["title"] == "Presiding Commissioner"]
    for p in parsed:
        title = p["title"]
        if title in OFFICER_TITLES:
            label = OFFICER_TITLES[title]
            if p.get("division"):
                label += ", " + p["division"]
            if any(o["office"] == label for o, _ in officers):
                raise SystemExit("FAIL: %s prints the office %r twice" % (where, label))
            officers.append((person(p, {"office": label}), p))
            continue
        if title == "Presiding Commissioner":
            seats.insert(0, (person(p, {"seat": "Presiding Commissioner", "countywide": True}), p))
            continue
        if title == "Commissioner" and p["seat"] == "Presiding":
            # Clay prints its presiding commissioner twice, Pettis only this way.
            if presiding:
                if letters(presiding[0].get("name")) != letters(p.get("name")):
                    raise SystemExit("FAIL: %s names two presiding commissioners" % where)
                continue
            seats.insert(0, (person(p, {"seat": "Presiding Commissioner", "countywide": True}), p))
            continue
        if title in ("Commissioner", "Associate Commissioner", "Council Member",
                     "County Legislature"):
            seats.append((person(p, {"seat": p["seat"]}), p))
            continue
        if title == "Board of Aldermen":
            if p["seat"] != "President":
                raise SystemExit("FAIL: %s: Board of Aldermen entry for %r" % (where, p["seat"]))
            seats.append((person(p, {"seat": "President", "countywide": True}), p))
            continue
        if title in ("County Executive", "Mayor"):
            if executive:
                raise SystemExit("FAIL: %s prints two executives" % where)
            executive = (person(p, {"title": title}), p)
            continue
        if BODY_WORDS.search(title) and title not in NOT_BODY:
            raise SystemExit("FAIL: %s: %r looks like a governing-body office the script "
                             "does not place (entry %r)" % (where, title, p["raw"][:120]))
    # The body's shape.
    if geoid in CHARTER:
        shape = CHARTER[geoid]
        record["body"], record["kind"] = shape["body"], shape["kind"]
        if len(seats) != shape["seats"] or any(s.get("countywide") for s, _ in seats):
            raise SystemExit("FAIL: %s: %d seats where its charter has %d"
                             % (where, len(seats), shape["seats"]))
        if not executive or executive[0]["title"] != "County Executive":
            raise SystemExit("FAIL: %s: no county executive" % where)
    elif geoid == ST_LOUIS_CITY:
        record["body"], record["kind"] = "Board of Aldermen", "city"
        if len(seats) != 1 or not executive or executive[0]["title"] != "Mayor":
            raise SystemExit("FAIL: St. Louis city: expected the mayor and the Board's "
                             "president, found %d seats" % len(seats))
        record["bodyNote"] = ("The Secretary of State's roster names the Board's president "
                              "and not its fourteen ward aldermen.")
    else:
        record["body"], record["kind"] = county["name"] + " Commission", "commission"
        want = COMMISSION_SEATS.get(geoid, 3)
        if executive:
            raise SystemExit("FAIL: %s: a commission county with an executive" % where)
        if len(seats) != want or not seats[0][0].get("countywide") \
                or sum(1 for s, _ in seats if s.get("countywide")) != 1:
            raise SystemExit("FAIL: %s: %d commission seats (%s) where %d were expected"
                             % (where, len(seats), [s.get("seat") for s, _ in seats], want))
    if any(s.get("seat") is None for s, _ in seats):
        raise SystemExit("FAIL: %s: a seat with no label" % where)
    labels = [s["seat"] for s, _ in seats]
    if len(set(labels)) != len(labels):
        raise SystemExit("FAIL: %s prints a seat twice: %s" % (where, labels))
    # The body's own office: what two or more members print word for word.
    body_people = [p for _, p in seats if not p.get("vacant")]
    if executive:
        body_people.append(executive[1])
    addr = collections.Counter()
    phone = collections.Counter()
    mail = collections.Counter()
    phone_raw = {}
    for p in body_people:
        a, phones, emails = contacts(p["contact"])
        if a:
            addr[a] += 1
        for raw, _ in phones[:1]:
            phone[phone_key(raw)] += 1
            phone_raw[phone_key(raw)] = raw
        for e in set(x.lower() for x in emails):
            mail[e] += 1
    for counter, key in ((addr, "boardAddress"), (phone, "boardPhone"), (mail, "boardEmail")):
        if counter:
            value, n = counter.most_common(1)[0]
            if n >= 2:
                record[key] = phone_text(phone_raw[value]) if key == "boardPhone" else value
    record["seats"] = [s for s, _ in seats]
    if executive:
        row = executive[0]
        stale = STALE.get((geoid, "executive"))
        if stale:
            if row.get("name") != stale["printed"]:
                raise SystemExit("FAIL: %s: STALE expects the roster to print %r for the "
                                 "executive and it prints %r — re-read the entry"
                                 % (where, stale["printed"], row.get("name")))
            row = {"title": row["title"], "notNamed": stale["why"],
                   "sourceUrl": stale["sourceUrl"]}
            notes.append("%s: executive not shipped (STALE, checked %s)" % (where, stale["checked"]))
        record["executive"] = row
    officers.sort(key=lambda item: (OFFICER_ORDER.index(item[0]["office"].split(", ")[0]),
                                    item[0]["office"]))
    record["officers"] = [o for o, _ in officers]
    record["source"] = "the Missouri Secretary of State's %s Missouri Roster" % edition
    record["sourceUrl"] = src
    record["read"] = today
    return record


def page_text(raw):
    text = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", raw, flags=re.S | re.I)
    text = html_module.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip()


NAME_WORDS = r"[A-Z][A-Za-z.'’-]*(?: [A-Z][A-Za-z.'’-]*){1,3}?"


def parse_county_page(kind, raw):
    """{seat label: {"name", "email"?}} from one county's own page."""
    text = page_text(raw)
    seats = {}
    if kind == "jefferson":
        # "District 5 - Tim Bennett Jr. Tim Bennett Jr. Contact & Biography"
        for m in re.finditer(r"District ([1-7]) - (?:Mrs\.|Mr\.|Ms\.|Dr\.)? ?(" + NAME_WORDS
                             + r") (?:Mrs\.|Mr\.|Ms\.|Dr\.)? ?\2 Contact", text):
            seats.setdefault(ORDINAL_SEATS[m.group(1)] + " District", {"name": m.group(2)})
    elif kind == "stcharles":
        # "Council District 1 Matt Swanson - Council Vice Chair Email Matt Swanson Blog"
        blocks = re.split(r"Council District (?=[1-7]\b)", raw)
        for block in blocks[1:]:
            m = re.match(r"([1-7]) (" + NAME_WORDS + r")(?: - Council(?: Vice)? Chair)? Email ",
                         page_text(block))
            if not m:
                continue
            row = {"name": m.group(2)}
            mail = re.findall(r'href="mailto:([^"?]+)"', block)
            if len(set(mail)) == 1:
                row["email"] = mail[0]
            seats.setdefault(ORDINAL_SEATS[m.group(1)] + " District", row)
    elif kind == "jackson":
        # "Jalen Anderson - 1st District At-Large ... Manuel Abarca IV - 1st District"
        for m in re.finditer(r"(" + NAME_WORDS + r") - ([1-7](?:st|nd|rd|th)) District"
                             r"( At-Large)?", text):
            label = ORDINAL_SEATS[ORDINAL_WORDS[m.group(2)]] + " District" + \
                (" at Large" if m.group(3) else "")
            seats.setdefault(label, {"name": m.group(1)})
    return seats


def surname_key(name):
    words = [w for w in re.split(r"\s+", str(name or "").strip()) if w not in NAME_SUFFIXES]
    return letters(words[-1]) if words else ""


def near(a, b):
    """True when a and b differ by at most one letter added, dropped or changed."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    short, long_ = sorted((a, b), key=len)
    return any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))


def apply_county_page(geoid, record, pages, today, notes):
    spec = COUNTY_PAGES[geoid]
    found = parse_county_page(spec["parse"], pages.get(spec["file"], spec["url"]))
    labels = [s["seat"] for s in record["seats"]]
    if sorted(found) != sorted(labels):
        raise SystemExit("FAIL: %s's own page lists seats %s where the roster prints %s"
                         % (record["county"], sorted(found), sorted(labels)))
    seats = []
    for row in record["seats"]:
        page = found[row["seat"]]
        if not reads_as_name(page["name"]):
            raise SystemExit("FAIL: %s's own page: %r does not read as a name"
                             % (record["county"], page["name"]))
        same = (not row.get("vacant") and letters(row.get("name", ""))[:1] ==
                letters(page["name"])[:1] and near(surname_key(row.get("name")),
                                                   surname_key(page["name"])))
        if same:
            new = dict(row, name=page["name"])
        else:
            new = {"seat": row["seat"], "name": page["name"]}
            notes.append("%s %s: the county's page names %s where the roster prints %s"
                         % (record["county"], row["seat"], page["name"],
                            "a vacancy" if row.get("vacant") else row.get("name")))
        if page.get("email") and not new.get("email"):
            new["email"] = page["email"]
        seats.append(new)
    record["seats"] = seats
    record["seatsSource"] = spec["source"]
    record["seatsSourceUrl"] = spec["url"]
    record["seatsRead"] = today


def build(pages, today):
    with open(COUNTIES_FILE, encoding="utf-8") as fh:
        counties = [{"geoid": f["properties"]["GEOID"], "name": f["properties"]["NAME"]}
                    for f in json.load(fh)["features"]]
    if len(counties) != 115:
        raise SystemExit("FAIL: %s holds %d counties, not Missouri's 115" % (COUNTIES_FILE, len(counties)))
    pubs = pages.get("sos-pubs.html", SOS_PUBS)
    url, edition = roster_url(pubs)
    pdf = pages.get("mo-roster.pdf", url, binary=True)
    lines = county_section(reading_order(pdf_words(pdf)))
    by_county = split_counties(lines, counties)
    notes = []
    names = {c["geoid"]: c for c in counties}
    out = collections.OrderedDict()
    for geoid in sorted(by_county):
        out[geoid] = build_county(geoid, names[geoid], by_county[geoid], edition, url,
                                  today, notes)
        if geoid in COUNTY_PAGES:
            apply_county_page(geoid, out[geoid], pages, today, notes)
    check(out)
    return out, notes, url, edition


def check(out):
    counts = collections.Counter()
    for rec in out.values():
        for o in rec["officers"]:
            if o.get("name"):
                counts[o["office"]] += 1
    short = {k: (counts[k], v) for k, v in OFFICER_FLOORS.items() if counts[k] < v}
    if short:
        raise SystemExit("FAIL: officers named in fewer counties than the floor "
                         "(named, floor): %s" % short)
    named = sum(1 for rec in out.values() for s in rec["seats"] if s.get("name"))
    if named < 330:
        raise SystemExit("FAIL: only %d governing-body seats named" % named)


def check_shipped(path):
    """--check: the shipped file's shape, offline (see the module docstring)."""
    with open(path, encoding="utf-8") as fh:
        out = json.load(fh)
    with open(COUNTIES_FILE, encoding="utf-8") as fh:
        names = {f["properties"]["GEOID"]: f["properties"]["NAME"]
                 for f in json.load(fh)["features"]}
    problems = []
    if set(out) != set(names):
        problems.append("the file's GEOIDs differ from state-counties.json: missing %s, extra %s"
                        % (sorted(set(names) - set(out)), sorted(set(out) - set(names))))
    for geoid, rec in sorted(out.items()):
        where = rec.get("county") or geoid
        if rec.get("county") != names.get(geoid):
            problems.append("%s: county %r where state-counties.json names %r"
                            % (geoid, rec.get("county"), names.get(geoid)))
        seats = rec.get("seats") or []
        executive = rec.get("executive")
        if geoid in CHARTER:
            shape = CHARTER[geoid]
            want = (shape["kind"], shape["body"], shape["seats"])
            if not executive or executive.get("title") != "County Executive":
                problems.append("%s: no county executive" % where)
        elif geoid == ST_LOUIS_CITY:
            want = ("city", "Board of Aldermen", 1)
            if not executive or executive.get("title") != "Mayor":
                problems.append("%s: no mayor" % where)
            if not rec.get("bodyNote"):
                problems.append("%s: the note on the unnamed ward aldermen is missing" % where)
        else:
            want = ("commission", "%s Commission" % names.get(geoid), COMMISSION_SEATS.get(geoid, 3))
            if executive:
                problems.append("%s: a commission county with an executive" % where)
            if not seats or not seats[0].get("countywide") or \
                    sum(1 for s in seats if s.get("countywide")) != 1:
                problems.append("%s: the presiding commissioner is not the one countywide "
                                "seat, first" % where)
        got = (rec.get("kind"), rec.get("body"), len(seats))
        if got != want:
            problems.append("%s: body %r where %r was expected" % (where, got, want))
        labels = [s.get("seat") for s in seats]
        if None in labels or len(set(labels)) != len(labels):
            problems.append("%s: seat labels %r" % (where, labels))
        for row in seats + (rec.get("officers") or []):
            if not row.get("vacant") and not (row.get("name") and reads_as_name(row["name"])):
                problems.append("%s: %r is neither named nor vacant"
                                % (where, row.get("seat") or row.get("office")))
        for o in rec.get("officers") or []:
            if o.get("office", "").split(", ")[0] not in OFFICER_ORDER:
                problems.append("%s: office %r is not one the build carries" % (where, o.get("office")))
        stale = STALE.get((geoid, "executive"))
        if stale:
            if not executive or executive.get("name") or not executive.get("notNamed"):
                problems.append("%s: STALE says the executive is not named, and the file "
                                "names one or says nothing" % where)
        elif executive and not executive.get("name"):
            problems.append("%s: an executive with no name and no STALE entry" % where)
        if not str(rec.get("sourceUrl", "")).startswith("https://www.sos.mo.gov/") or \
                not re.match(r"^\d{4}-\d{2}-\d{2}$", str(rec.get("read", ""))):
            problems.append("%s: source %r read %r" % (where, rec.get("sourceUrl"), rec.get("read")))
        if geoid in COUNTY_PAGES:
            spec = COUNTY_PAGES[geoid]
            if rec.get("seatsSourceUrl") != spec["url"] or rec.get("seatsSource") != spec["source"] \
                    or not re.match(r"^\d{4}-\d{2}-\d{2}$", str(rec.get("seatsRead", ""))):
                problems.append("%s: its members are not marked as read from its own page"
                                % where)
        elif rec.get("seatsSourceUrl") or rec.get("seatsSource"):
            problems.append("%s: names a page for its members that COUNTY_PAGES does not"
                            % where)
        if re.search(r"\bfax\b", json.dumps(rec), re.I):
            problems.append("%s: carries the word fax" % where)
    if problems:
        for line in problems:
            print("FAIL: " + line, file=sys.stderr)
        sys.exit(1)
    check(out)
    print("mo county officials: OK — %d records match state-counties.json and the shape the "
          "build writes" % len(out))


def main():
    args = sys.argv[1:]
    if args == ["--check"]:
        check_shipped(os.path.join(DEFAULT_OUT_DIR, OUT_NAME))
        return
    offline = save = None
    while args and args[0] in ("--offline", "--save"):
        if len(args) < 2:
            print(__doc__.split("Usage:")[1].split("--save writes")[0], file=sys.stderr)
            sys.exit(1)
        if args[0] == "--offline":
            offline = args[1]
        else:
            save = args[1]
        args = args[2:]
    if len(args) > 1 or (offline and save):
        print("usage: %s [--offline DIR | --save DIR] [output_dir]" % sys.argv[0],
              file=sys.stderr)
        sys.exit(1)
    out_dir = args[0] if args else DEFAULT_OUT_DIR
    today = datetime.date.today().isoformat()
    out, notes, url, edition = build(Pages(offline, save), today)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, OUT_NAME)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    seats = [s for rec in out.values() for s in rec["seats"]]
    officers = [o for rec in out.values() for o in rec["officers"]]
    print("Wrote %s from the %s Missouri Roster (%s): %d counties, %d of %d body seats "
          "named, %d officers named, %d with a telephone, %d with an e-mail address"
          % (path, edition, url, len(out), sum(1 for s in seats if s.get("name")), len(seats),
             sum(1 for o in officers if o.get("name")),
             sum(1 for x in seats + officers if x.get("phone")),
             sum(1 for x in seats + officers if x.get("email"))), file=sys.stderr)
    for note in notes:
        print("  " + note, file=sys.stderr)
    if _PACER is not None:
        for line in _PACER.report():
            print(line, file=sys.stderr)


if __name__ == "__main__":
    main()
