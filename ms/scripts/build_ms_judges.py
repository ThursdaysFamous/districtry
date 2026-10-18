#!/usr/bin/env python3
"""Build ms/data/app/ms-judge-roster.json: the judges of Mississippi's four
courts whose judges are elected from districts, keyed by the district each was
elected from, from the Mississippi Judiciary's own pages on courts.ms.gov.

    {"courts": {"supreme":  {"readFrom": ..., "districts": {"1": {"members": [...]}}},
                "appeals":  {...},
                "chancery": {"readFrom": ..., "listUpdated": "2025-08-01",
                             "structure": "until-2027", "districts": {...}},
                "circuit":  {...}}}

The four court maps the cards join this to are drawn by
ms/scripts/build_ms_court_districts.py; this file names the people.

WHERE EACH COURT'S JUDGES ARE PRINTED, measured 2026-10-15.
  - The Supreme Court's page of its justices (/appellatecourts/sc/scjustices.php)
    and the Court of Appeals' page of its judges (/appellatecourts/coa/coajudges.php)
    are HTML. Each judge is one table cell holding a link to a biography page,
    the judge's title and name in a <strong>, and the district and seat in an
    <em> ("District 2, Place 3"; the Court of Appeals says "Position"). Nine
    justices, three from each of three districts, and ten judges, two from each
    of five districts.
  - The chancery and circuit judges are two PDF lists, "Chancery Court Judges
    and Staff" (/trialcourts/chancerycourt/chanjud.pdf, "Updated August 1, 2025")
    and "Circuit Court Judges and Staff" (/trialcourts/circuitcourt/cirjud.pdf,
    "Updated February 4, 2026"), linked as "Judges & Staff" from each court's
    page. Each district opens with a heading ("3rd Chancery District") and the
    counties it covers, then lists every judge with the judge's own staff
    beneath. 52 chancellors and 59 circuit judges.

THE PDF LISTS ALSO PRINT THE JUDGES' STAFF, AND NOTHING OF THEIRS IS READ. Under
each judge the list names a court reporter, a court administrator, a staff
attorney or a law clerk, each with an address and a telephone, and some of those
addresses are street addresses in small towns. A staff member is not an
officeholder, and an address printed for one may be a home. So the parse reads
two lines per judge, the heading "Judge" and the name under it, and from the
judge's own row one cell, the telephone; the judges' own addresses are not
carried, and neither PDF is ever written into this repository (`--save` refuses
a folder inside it). A name must look like a name: a line with a digit, "P.O."
or an @ in it stops the build, because that is a layout change putting an
address where a name was.

A JUDGE'S OWN TELEPHONE IS CARRIED SINCE 2026-10-17, on Adam's ruling for every
state that a number an official government source prints beside an official is
published, whosever line it is; until that day no judge's number was read. Each
list is a table with an Address column, a town column, a Phone column and a Fax
column (one circuit district heads its last column E-mail instead), and a
judge's row is read BY POSITION, from the Phone column on the row that names
the judge (judge_phone_cells), because the list's text read as lines puts the
Fax column's number straight after the Phone column's, and on one row of the
chancery list of 1 August 2025 both on one line: a line-based read could not
tell a judge with no telephone and a fax from a judge with a telephone. The
column after Phone, fax or e-mail, is never read. A number the list prints for two or more judges is
the court office's line, as at Tupelo where three chancellors and their court
administrator share one, and it is carried on no judge, the rule this project
keeps for a number shared by officials; a number a judge shares only with the
judge's own staff is that judge's chambers line and is carried. Measured on
2026-10-17: 35 of the 52 chancellors and 55 of the 59 circuit judges the lists
print have a number of their own, and once CHANGES is applied 32 of 50 and 54
of 59 carry one (each court's phone_floor holds about two thirds of that). A
number ships exactly as printed, "(601)359-0000" with no space.

THE LISTS ARE OLDER THAN THE BENCH, SO FIVE CHANGES ARE APPLIED ON TOP, each from
the court's own news or the Governor's own announcement, in CHANGES below. The
chancery list was last updated fourteen months before this was written, and in
that time one chancellor retired and was replaced (3rd), another retired and was
replaced (10th), two died (5th and 9th), and a circuit judge (21st) joined the
Supreme Court and was replaced. EVERY ENTRY IS RE-TESTED AGAINST THE LIST ON
EVERY RUN, and FAILS once the list has caught up: when the list's own date
reaches the change, when the list no longer prints the person who left, or when
it already prints the person who arrived. A failing entry is a list that has
been updated, so a person re-reads it and deletes the entry; an entry is never
left to apply itself over a newer list. A judge the trial lists name who also
sits on an appellate court stops the build, which is how the circuit judge who
joined the Supreme Court would have been caught had her entry not been written.

WHICH MAP A LIST DESCRIBES IS READ FROM THE LIST. Two 2025 laws redraw the
chancery and circuit districts on 1 January 2027 (and the circuit districts again
on 1 January 2031), and each district's heading names its counties, so the
builder compares every heading's counties with the two shipped maps: a list
matching today's districts is `until-2027`, one matching the 2027 districts is
`from-2027`, and one matching neither stops the build. The app names chancellors
and circuit judges on a 2027 district only from a `from-2027` list, because a
judge elected from today's 3rd Chancery District is not thereby the judge of the
2027 one.

THE APPELLATE COUNTS ARE EXACT AND THE TRIAL COUNTS ARE FLOORS. The constitution
fixes nine justices and the Court of Appeals statute ten judges, each seat
printed once; how many chancellors and circuit judges a district elects is set
district by district in Title 9 and changes with each redistricting, so the trial
tiers carry floors about a tenth below the measured figures, and every district
the shipped map carries must name at least one judge.

ROBOTS AND PACING. courts.ms.gov publishes a robots.txt (871 bytes on 2026-10-15)
with no rule binding this client; it is read before the first fetch through
scraper_common.require_robots_once with the same client the fetches send. The
host dropped connections now and then on 2026-10-15, so requests are spaced three
seconds apart and retried. Its certificate chain is complete (no pin needed,
scripts/probe_incomplete_tls_chains.py, 2026-10-15). Four requests a run.

The file carries no date of reading, so an unchanged source rebuilds byte for
byte and the weekly job opens no pull request.

Usage:
    python3 ms/scripts/build_ms_judges.py                 # fetch and build
    python3 ms/scripts/build_ms_judges.py --save DIR      # also keep what was fetched
    python3 ms/scripts/build_ms_judges.py --offline DIR   # build from a --save folder
    python3 ms/scripts/build_ms_judges.py --check         # offline shape gate
    python3 ms/scripts/build_ms_judges.py --selftest      # offline, no files needed
"""

import argparse
import collections
import datetime
import html as html_module
import json
import os
import re
import sys
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
sys.path.insert(0, os.path.join(REPO, "scripts"))

USER_AGENT = "districtry/1.0 (+https://districtry.com/ms/)"
LABEL = "build-ms-judges"
BASE = "https://courts.ms.gov"
PACE_SECONDS = 3.0
ATTEMPTS = 4
RETRY_SECONDS = 6.0
FETCH_TIMEOUT = 90

OUT = os.path.join(INSTANCE, "data", "app", "ms-judge-roster.json")
APP = os.path.join(INSTANCE, "data", "app")

COURTS = {
    "supreme": {"url": BASE + "/appellatecourts/sc/scjustices.php",
                "file": "scjustices.php.htm",
                "districts": 3, "per": 3, "seat": "Place",
                "titles": ("Chief Justice", "Presiding Justice", "Associate Justice"),
                "chief": "Chief Justice"},
    "appeals": {"url": BASE + "/appellatecourts/coa/coajudges.php",
                "file": "coajudges.php.htm",
                "districts": 5, "per": 2, "seat": "Position",
                "titles": ("Chief Judge", "Presiding Judge", "Judge"),
                "chief": "Chief Judge"},
    "chancery": {"url": BASE + "/trialcourts/chancerycourt/chanjud.pdf",
                 "file": "chanjud.pdf", "word": "Chancery",
                 "maps": {"until-2027": "ms-chancery-court-districts.json",
                          "from-2027": "ms-chancery-court-districts-2027.json"},
                 # 52 on the list of 1 August 2025, 50 once two deaths are applied.
                 "floor": 46,
                 # Judges carrying a number of their own: 32 on 2026-10-17
                 # (see the module docstring), floored at about two thirds.
                 "phone_floor": 21},
    "circuit": {"url": BASE + "/trialcourts/circuitcourt/cirjud.pdf",
                "file": "cirjud.pdf", "word": "Circuit",
                "maps": {"until-2027": "ms-circuit-court-districts.json",
                         "from-2027": "ms-circuit-court-districts-2027.json"},
                # 59 on the list of 4 February 2026.
                "floor": 53,
                # 54 carrying a number of their own on 2026-10-17.
                "phone_floor": 36},
}
APPELLATE_MAPS = {"supreme": "ms-supreme-court-districts.json",
                  "appeals": "ms-court-of-appeals-districts.json"}

# The changes since the lists were printed, each from the court's own news or the
# Governor's own announcement, read 2026-10-15. `out` and `in` are names exactly
# as the list prints them (after tidy_name) and as the announcement names the new
# judge; `effective` is the day the change took effect. The Governor's newsroom
# had announced no appointment to either chancellor's seat left by a death when
# these were written, and ms/scripts/validate_sources.py reads both newsrooms
# monthly for headlines after that day.
CHANGES = (
    {"court": "chancery", "district": 3, "out": "Percy L. Lynchard Jr.",
     "in": "Sabrina D. Howell", "effective": "2026-07-01",
     "note": "Appointed by the Governor from 1 July 2026, after Chancellor Percy "
             "L. Lynchard Jr. retired.",
     "source": {"label": "Mississippi Judiciary news",
                "url": "https://courts.ms.gov/news/view_news_page.php?article=3145"}},
    {"court": "chancery", "district": 10, "out": "Chase Ford Morgan",
     "in": "Renee McBride Porter", "effective": "2026-08-17",
     "note": "Appointed by the Governor from 17 August 2026, after Chancellor "
             "Chase Ford Morgan retired.",
     "source": {"label": "Governor's announcement",
                "url": "https://governorreeves.ms.gov/governor-reeves-appoints-renee-"
                       "mcbride-porter-chancellor-for-the-10th-chancery-court-district/"}},
    {"court": "chancery", "district": 5, "out": "Dewayne Thomas", "in": None,
     "effective": "2026-09-16",
     "note": "Chancellor Dewayne Thomas died on 16 September 2026. The court "
             "expects the Governor to fill the seat by appointment until a special "
             "election, expected on 2 November 2027; the Governor's office had "
             "announced no appointment by 15 October 2026.",
     "source": {"label": "Mississippi Judiciary news",
                "url": "https://courts.ms.gov/news/view_news_page.php?article=3162"}},
    {"court": "chancery", "district": 9, "out": "Vicki R. Barnes", "in": None,
     "effective": "2026-09-27",
     "note": "Chancellor Vicki R. Barnes died on 27 September 2026. The Governor's "
             "office had announced no appointment to the seat by 15 October 2026.",
     "source": {"label": "Mississippi Judiciary news",
                "url": "https://courts.ms.gov/news/view_news_page.php?article=3166"}},
    {"court": "circuit", "district": 21, "out": "Celeste Embrey Wilson",
     "in": "Craig Treadway", "effective": "2026-09-01",
     "note": "Appointed by the Governor from 1 September 2026, after Judge "
             "Celeste Embrey Wilson joined the Mississippi Supreme Court.",
     "source": {"label": "Governor's announcement",
                "url": "https://governorreeves.ms.gov/governor-reeves-appoints-craig-"
                       "treadway-circuit-judge-for-the-21st-circuit-court-district-"
                       "and-reopens-qualifying/"}},
)

MONTHS = {m: i for i, m in enumerate(
    ("January February March April May June July August September October "
     "November December").split(), 1)}
UPDATED_RE = re.compile(r"Updated\s+([A-Z][a-z]+)\s+(\d{1,2}),\s+(\d{4})")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .,'\"()\-\u00c0-\u017f]*[A-Za-z.)\"\u00c0-\u017f]$")
NOT_A_NAME = re.compile(r"\d|P\.\s*O\.|@|\bBox\b|\bDrawer\b|\bSuite\b", re.I)
# A judge's Phone cell as the lists print it, "(662)432-2130"; a cell holding
# anything else (two numbers, an extension, a word) carries nothing.
PHONE_CELL_RE = re.compile(r"^\(\d{3}\) ?\d{3}-\d{4}$")


def fail(msg):
    print("%s: FAIL — %s" % (LABEL, msg), file=sys.stderr)
    raise SystemExit(1)


def clean(s):
    return " ".join(html_module.unescape(str(s)).replace("\xa0", " ").split())


def tidy_name(s):
    """The list's name with its suffix punctuation made uniform: "Michael P.
    Mills, Jr." and "Grady F. Tollison, III." become "Michael P. Mills Jr." and
    "Grady F. Tollison III", the form the chancery list already uses."""
    s = clean(s)
    s = re.sub(r",\s*(Jr|Sr)\.?$", r" \1.", s)
    s = re.sub(r",?\s+(II|III|IV)\.?$", r" \1", s)
    return s


def checked_name(name, where):
    if not NAME_RE.match(name) or NOT_A_NAME.search(name) or len(name) > 60:
        fail("%s: %r is not shaped like a person's name. The list's layout has "
             "probably moved and put another line (an address, a telephone) where "
             "a judge's name was; read the source before changing this builder, "
             "and never ship that line." % (where, name))
    if name.lower() == "vacant":
        fail("%s: the list prints a vacant seat. Decide how the card says so "
             "(a note on the district, from the list's own word) before shipping."
             % where)
    return name


def iso(month, day, year):
    if month not in MONTHS:
        fail("unreadable list date %r %r %r" % (month, day, year))
    return datetime.date(int(year), MONTHS[month], int(day)).isoformat()


# ---------------------------------------------------------------- fetching

def fetch_all(save_dir=None):
    import requests
    from scraper_common import require_robots_once

    out = {}
    for i, (court, spec) in enumerate(COURTS.items()):
        url = spec["url"]
        require_robots_once(url, USER_AGENT, headers={"User-Agent": USER_AGENT},
                            label=LABEL)
        if i:
            time.sleep(PACE_SECONDS)
        last = None
        for attempt in range(ATTEMPTS):
            try:
                resp = requests.get(url, headers={"User-Agent": USER_AGENT},
                                    timeout=FETCH_TIMEOUT)
                if resp.status_code >= 500:
                    last = "HTTP %d" % resp.status_code
                else:
                    resp.raise_for_status()
                    out[court] = resp.content
                    break
            except requests.ConnectionError as exc:
                last = str(exc)
            time.sleep(RETRY_SECONDS * (attempt + 1))
        else:
            fail("could not read %s after %d tries: %s" % (url, ATTEMPTS, last))
        if save_dir:
            with open(os.path.join(save_dir, spec["file"]), "wb") as fh:
                fh.write(out[court])
    return out


def read_saved(folder):
    out = {}
    for court, spec in COURTS.items():
        path = os.path.join(folder, spec["file"])
        if not os.path.exists(path):
            fail("%s is missing from %s" % (spec["file"], folder))
        with open(path, "rb") as fh:
            out[court] = fh.read()
    return out


def outside_repo(folder):
    real = os.path.realpath(folder)
    if real == REPO or real.startswith(REPO + os.sep):
        fail("refusing to save into %s: the judge lists print court staff's "
             "addresses and telephones, so they are never written into this "
             "repository. Save to a folder outside it." % folder)
    os.makedirs(real, exist_ok=True)
    return real


# ---------------------------------------------------------------- parsing

def parse_appellate(raw, court):
    """[{name, role, district, seat, profileUrl}] from one appellate page."""
    spec = COURTS[court]
    text = raw.decode("utf-8", errors="strict") if isinstance(raw, bytes) else raw
    text = re.sub(r"(?s)<!--.*?-->", "", text)
    rows = []
    for cell in re.findall(r"(?is)<td[^>]*>(.*?)</td>", text):
        if "bios/" not in cell:
            continue
        href = re.search(r'(?i)<a\s+href="([^"]+)"', cell)
        strong = re.search(r"(?is)<strong>(.*?)</strong>", cell)
        em = re.search(r"(?is)<em>(.*?)</em>", cell)
        if not (href and strong and em):
            fail("%s page: a judge's cell has lost its link, its <strong> name or "
                 "its <em> district" % court)
        title_name = clean(re.sub(r"<[^>]+>", " ", strong.group(1)))
        seat_text = clean(re.sub(r"<[^>]+>", " ", em.group(1)))
        role = next((t for t in spec["titles"] if title_name.startswith(t + " ")), None)
        if role is None:
            fail("%s page: %r starts with none of the titles %s"
                 % (court, title_name, ", ".join(spec["titles"])))
        name = checked_name(tidy_name(title_name[len(role):]), "%s page" % court)
        m = re.fullmatch(r"District (\d+), %s (\d+)" % spec["seat"], seat_text)
        if not m:
            fail("%s page: %s's seat reads %r, not 'District N, %s N'"
                 % (court, name, seat_text, spec["seat"]))
        profile = urllib.parse.urljoin(
            spec["url"], urllib.parse.quote(clean(href.group(1)), safe="/:%"))
        rows.append({"name": name, "role": role, "district": int(m.group(1)),
                     "seat": "%s %s" % (spec["seat"], m.group(2)),
                     "profileUrl": profile})
    return rows


def open_pdf(raw):
    # Only the weekly read of the two PDF lists needs pymupdf, and
    # update-ms-judges-roster.yml installs it; --selftest and --check, which
    # the smoke job runs, never reach this line, so the import is declared
    # optional rather than paid for by every pull request.
    try:
        import pymupdf
    except ImportError:
        raise RuntimeError("reading the judges' lists needs pymupdf: "
                           "pip install -c scripts/requirements.txt pymupdf")
    return pymupdf.open(stream=raw, filetype="pdf")


def pdf_lines(raw):
    lines = []
    for page in open_pdf(raw):
        lines.extend(page.get_text().split("\n"))
    return lines


def judge_phone_cells(raw, court):
    """{name: the Phone cell on that judge's row}, read by position.

    Each header row ("Address", a town column, "Phone" and the column after
    it, "Fax" on every district but one circuit district's "E-mail", read
    2026-10-17) gives the columns' left edges, and every header must give the
    same ones; a continuation page without a header takes them from the
    others. A judge's row is one whose first word is "Judge" alone in the
    left-hand column. The name is the words between that and the Address
    column, and the telephone the words in the Phone column, left of the
    column after it, which is never read. attach_phones() then requires the names to be
    exactly the ones the line read found, so the two reads cannot describe
    different tables."""
    pages = [page.get_text("words") for page in open_pdf(raw)]
    cols = set()
    for words in pages:
        for w in words:
            if w[4] != "Phone":
                continue
            row = sorted((v for v in words if abs(v[1] - w[1]) < 2), key=lambda v: v[0])
            addr = [v for v in row if v[4] == "Address"]
            after = [v for v in row if v[0] > w[2]]
            if addr and after:
                cols.add((round(addr[0][0]), round(w[0]), round(after[0][0])))
    if len(cols) != 1:
        fail("the %s list's Address, Phone and next columns start at %s, not at one "
             "place on every page: the layout changed" % (court, sorted(cols) or "no place"))
    addr_x, phone_x, fax_x = cols.pop()
    out = {}
    for words in pages:
        for w in words:
            if w[4] != "Judge":
                continue
            row = sorted((v for v in words if abs(v[1] - w[1]) < 2), key=lambda v: v[0])
            if tuple(row[0][:5]) != tuple(w[:5]) or len(row) < 2 or row[1][0] - w[2] < 10:
                continue
            name = tidy_name(" ".join(v[4] for v in row[1:] if v[2] <= addr_x - 2))
            if name in out:
                fail("the %s list prints two judges' rows named %s" % (court, name))
            out[name] = clean(" ".join(v[4] for v in row
                                       if phone_x - 3 <= v[0] < fax_x - 3))
    return out


def attach_phones(court, districts, cells):
    """The list's judges, each as {"name", "phone"} where the judge has a number
    of their own and as a bare name otherwise. Returns (judges whose Phone cell
    is not one telephone number, judges whose number the list prints for another
    judge too), both carried with no number; see the module docstring."""
    names = [n for v in districts.values() for n in v["judges"]]
    if sorted(names) != sorted(cells):
        fail("the %s list's lines and its table rows name different judges (%s): "
             "the layout changed" % (court, ", ".join(sorted(set(names) ^ set(cells))[:4])))
    shaped = {n: p for n, p in cells.items() if PHONE_CELL_RE.match(p)}
    odd = sorted(n for n, p in cells.items() if p and n not in shaped)
    count = collections.Counter(re.sub(r"\D", "", p) for p in shaped.values())
    shared = sorted(n for n, p in shaped.items() if count[re.sub(r"\D", "", p)] > 1)
    for v in districts.values():
        v["judges"] = [{"name": n, "phone": shaped[n]}
                       if n in shaped and n not in shared else n
                       for n in v["judges"]]
    return odd, shared


def split_counties(text):
    text = re.sub(r"(?i)\s*\bcount(?:y|ies)\b\.?\s*$", "", clean(text))
    parts = re.split(r"\s*,\s*(?:and\s+)?|\s+and\s+", text)
    return [p for p in (x.strip() for x in parts) if p]


def parse_trial_lines(lines, court):
    """(listUpdated, {district: {"counties": [...], "judges": [names]}})."""
    word = COURTS[court]["word"]
    head = re.compile(r"^(\d+)(?:st|nd|rd|th) %s District$" % word)
    stops = {"Address", "Name", "Judge"}
    updated = None
    for line in lines[:12]:
        m = UPDATED_RE.search(line)
        if m:
            updated = iso(*m.groups())
            break
    if updated is None:
        fail("the %s list prints no 'Updated <Month> <D>, <YYYY>' line at its top"
             % court)
    lines = [clean(l) for l in lines]
    districts, current, i = {}, None, 0
    while i < len(lines):
        line = lines[i]
        m = head.match(line)
        if m:
            current = int(m.group(1))
            if current in districts:
                fail("the %s list heads district %d twice" % (court, current))
            buf, j = [], i + 1
            while j < len(lines) and lines[j] not in stops and not head.match(lines[j]):
                buf.append(lines[j])
                j += 1
            districts[current] = {"counties": split_counties(" ".join(buf)),
                                  "judges": []}
            i = j
            continue
        if line == "Judge":
            if current is None:
                fail("the %s list prints a judge before its first district heading"
                     % court)
            name = next((l for l in lines[i + 1:i + 3] if l), "")
            districts[current]["judges"].append(
                checked_name(tidy_name(name), "%s list, district %d" % (court, current)))
        i += 1
    return updated, districts


def map_counties(path):
    """{unit: frozenset of lowercased county names} from a shipped court map."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    out = {}
    for f in data["features"]:
        p = f["properties"]
        out.setdefault(int(p["unit"]), set()).update(c.lower() for c in p["counties"])
    return {k: frozenset(v) for k, v in out.items()}


def appellate_units(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    units = set()
    for f in data["features"]:
        p = f["properties"]
        units.update(p["units"] if "units" in p else [p["unit"]])
    return units


def structure_of(court, districts, maps):
    """Which shipped map the list's own headings describe."""
    seen = {d: frozenset(c.lower() for c in v["counties"]) for d, v in districts.items()}
    hits = [name for name, units in maps.items() if units == seen]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        diffs = []
        for name, units in maps.items():
            bad = sorted(d for d in set(units) | set(seen) if units.get(d) != seen.get(d))
            diffs.append("%s differs in district(s) %s" % (name, ", ".join(map(str, bad))))
        fail("the %s list's district headings match neither shipped map (%s). The "
             "list describes districts this app does not draw; read it and the "
             "laws before shipping." % (court, "; ".join(diffs)))
    fail("the %s list's headings match both shipped maps, which cannot be told "
         "apart" % court)


# ---------------------------------------------------------------- assembly

def apply_changes(court, updated, districts, changes=CHANGES):
    """The list's judges with CHANGES applied; each entry re-tested against the
    list, and failing once the list has caught up."""
    notes = {}
    for ch in changes:
        if ch["court"] != court:
            continue
        where = "CHANGES entry %s district %d (%s)" % (court, ch["district"], ch["out"])
        if ch["district"] not in districts:
            fail("%s names a district the list does not carry" % where)
        judges = districts[ch["district"]]["judges"]
        if updated >= ch["effective"]:
            fail("%s: the list is dated %s, on or after the change (%s), so it should "
                 "already show it. Read the list and delete the entry."
                 % (where, updated, ch["effective"]))
        names = [j if isinstance(j, str) else j["name"] for j in judges]
        if ch["out"] not in names:
            fail("%s: the list no longer prints %s there, so it has been updated or "
                 "the district renumbered. Read it and delete or rewrite the entry."
                 % (where, ch["out"]))
        if ch["in"] and ch["in"] in names:
            fail("%s: the list already prints %s, so it has caught up. Read it and "
                 "delete the entry." % (where, ch["in"]))
        k = names.index(ch["out"])
        if ch["in"]:
            judges[k] = {"name": ch["in"], "note": ch["note"], "source": ch["source"]}
        else:
            del judges[k]
            notes.setdefault(ch["district"], []).append(
                {"text": ch["note"], "label": ch["source"]["label"],
                 "url": ch["source"]["url"]})
    return notes


def assemble(appellate, trial, maps, appellate_maps, changes=CHANGES):
    """The roster. `appellate` is {court: rows}, `trial` is {court: (updated,
    districts)}, `maps` is {court: {structure: {unit: counties}}}, and
    `appellate_maps` is {court: set of units}."""
    courts = {}
    for court in ("supreme", "appeals"):
        spec, rows = COURTS[court], appellate[court]
        want = spec["districts"] * spec["per"]
        if len(rows) != want:
            fail("the %s page names %d judges; the court has %d seats, so a "
                 "difference is a vacancy or a layout change and wants a person"
                 % (court, len(rows), want))
        units = set(range(1, spec["districts"] + 1))
        if units != appellate_maps[court]:
            fail("the %s map carries districts %s, not 1-%d"
                 % (court, sorted(appellate_maps[court]), spec["districts"]))
        seats = {}
        for r in rows:
            if r["district"] not in units:
                fail("the %s page puts %s in district %d, which the map does not "
                     "carry" % (court, r["name"], r["district"]))
            seats.setdefault(r["district"], []).append(r)
        for d in sorted(units):
            got = sorted(r["seat"] for r in seats.get(d, []))
            want_seats = ["%s %d" % (spec["seat"], n) for n in range(1, spec["per"] + 1)]
            if got != want_seats:
                fail("the %s page prints district %d's seats as %s, not %s"
                     % (court, d, got, want_seats))
        chiefs = [r["name"] for r in rows if r["role"] == spec["chief"]]
        if len(chiefs) != 1:
            fail("the %s page names %d %ss" % (court, len(chiefs), spec["chief"]))
        courts[court] = {"readFrom": spec["url"], "districts": {
            str(d): {"members": [
                {"name": r["name"], "role": r["role"], "seat": r["seat"],
                 "profileUrl": r["profileUrl"]}
                for r in sorted(seats[d], key=lambda r: r["seat"])]}
            for d in sorted(units)}}

    appellate_names = {r["name"] for court in ("supreme", "appeals")
                       for r in appellate[court]}
    for court in ("chancery", "circuit"):
        spec = COURTS[court]
        updated, districts = trial[court]
        districts = {d: {"counties": v["counties"], "judges": list(v["judges"])}
                     for d, v in districts.items()}
        structure = structure_of(court, districts, maps[court])
        notes = apply_changes(court, updated, districts, changes)
        seen = {}
        total = 0
        for d, v in sorted(districts.items()):
            if not v["judges"]:
                fail("the %s list names no judge for district %d" % (court, d))
            for j in v["judges"]:
                name = j if isinstance(j, str) else j["name"]
                if name in seen:
                    fail("the %s list names %s in district %d and district %d"
                         % (court, name, seen[name], d))
                seen[name] = d
                if name in appellate_names:
                    fail("the %s list names %s in district %d, who sits on an "
                         "appellate court: the list predates the move. Add a "
                         "CHANGES entry from the court's or the Governor's own "
                         "announcement." % (court, name, d))
                total += 1
        if total < spec["floor"]:
            fail("the %s list names %d judges, below the floor of %d — too few to "
                 "ship without a person looking" % (court, total, spec["floor"]))
        courts[court] = {
            "readFrom": spec["url"], "listUpdated": updated, "structure": structure,
            "districts": {str(d): dict(
                {"members": [{"name": j} if isinstance(j, str) else j
                             for j in v["judges"]]},
                **({"notes": notes[d]} if d in notes else {}))
                for d, v in sorted(districts.items())}}
    return {"courts": courts}


def load_maps():
    maps = {court: {s: map_counties(os.path.join(APP, f))
                    for s, f in COURTS[court]["maps"].items()}
            for court in ("chancery", "circuit")}
    appellate_maps = {court: appellate_units(os.path.join(APP, f))
                      for court, f in APPELLATE_MAPS.items()}
    return maps, appellate_maps


def render(payload):
    return json.dumps(payload, indent=1, ensure_ascii=False) + "\n"


def summary(payload):
    parts = []
    for court, v in payload["courts"].items():
        n = sum(len(d["members"]) for d in v["districts"].values())
        extra = ""
        if "listUpdated" in v:
            phones = sum(1 for d in v["districts"].values()
                         for m in d["members"] if m.get("phone"))
            extra = ", %d with a telephone, list of %s, %s" % (
                phones, v["listUpdated"], v["structure"])
        parts.append("%s %d districts/%d judges%s" % (court, len(v["districts"]), n, extra))
    return "; ".join(parts)


# ---------------------------------------------------------------- check

def check(payload, maps, appellate_maps, changes=CHANGES):
    """Problems with a shipped roster, offline. Empty when it is sound."""
    problems = []
    courts = payload.get("courts") or {}
    if set(courts) != set(COURTS):
        return ["courts are %s, not %s" % (sorted(courts), sorted(COURTS))]
    names = {}
    for court in ("supreme", "appeals"):
        spec, v = COURTS[court], courts[court]
        if v.get("readFrom") != spec["url"]:
            problems.append("%s readFrom is %r" % (court, v.get("readFrom")))
        if {int(d) for d in v["districts"]} != appellate_maps[court]:
            problems.append("%s districts %s do not match its map" % (court, sorted(v["districts"])))
        for d, rec in v["districts"].items():
            seats = sorted(m.get("seat", "") for m in rec["members"])
            if seats != ["%s %d" % (spec["seat"], n) for n in range(1, spec["per"] + 1)]:
                problems.append("%s district %s seats are %s" % (court, d, seats))
            for m in rec["members"]:
                names[m["name"]] = court
                if m.get("role") not in spec["titles"] or not m.get("profileUrl", "").startswith(BASE + "/"):
                    problems.append("%s district %s: %s carries role %r and profile %r"
                                    % (court, d, m["name"], m.get("role"), m.get("profileUrl")))
        chiefs = [m for rec in v["districts"].values() for m in rec["members"]
                  if m.get("role") == spec["chief"]]
        if len(chiefs) != 1:
            problems.append("%s has %d %ss" % (court, len(chiefs), spec["chief"]))
    phones = {"chancery": [], "circuit": []}
    for court in ("chancery", "circuit"):
        spec, v = COURTS[court], courts[court]
        if v.get("readFrom") != spec["url"]:
            problems.append("%s readFrom is %r" % (court, v.get("readFrom")))
        structure = v.get("structure")
        if structure not in spec["maps"]:
            problems.append("%s structure is %r" % (court, structure))
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v.get("listUpdated") or ""):
            problems.append("%s listUpdated is %r" % (court, v.get("listUpdated")))
            continue
        units = set(maps[court][structure])
        if {int(d) for d in v["districts"]} != units:
            problems.append("%s districts do not match the %s map" % (court, structure))
        total = 0
        for d, rec in v["districts"].items():
            if not rec.get("members"):
                problems.append("%s district %s names nobody" % (court, d))
            for m in rec.get("members", []):
                total += 1
                n = m.get("name", "")
                if not NAME_RE.match(n) or NOT_A_NAME.search(n):
                    problems.append("%s district %s: %r is not a name" % (court, d, n))
                if n in names:
                    problems.append("%s district %s: %s also sits on the %s court"
                                    % (court, d, n, names[n]))
                extra = set(m) - {"name", "note", "source", "phone"}
                if extra:
                    problems.append("%s district %s: %s carries %s" % (court, d, n, sorted(extra)))
                if "phone" in m:
                    # The value is never printed: the message names the seat.
                    if not PHONE_CELL_RE.match(str(m["phone"])):
                        problems.append("%s district %s: %s's telephone is not one "
                                        "telephone number" % (court, d, n))
                    phones[court].append(re.sub(r"\D", "", str(m["phone"])))
        if total < spec["floor"]:
            problems.append("%s names %d judges, below its floor of %d" % (court, total, spec["floor"]))
        shared = sorted(p for p, k in collections.Counter(phones[court]).items() if k > 1)
        if shared:
            problems.append("%s: %d telephone number(s) ride two or more judges, which "
                            "makes them the court office's line" % (court, len(shared)))
        if len(phones[court]) < spec["phone_floor"]:
            problems.append("%s: %d judges carry a telephone, below its floor of %d"
                            % (court, len(phones[court]), spec["phone_floor"]))
        # Every change is applied, and none has outlived its list.
        for ch in changes:
            if ch["court"] != court:
                continue
            rec = v["districts"].get(str(ch["district"]), {})
            got = [m.get("name") for m in rec.get("members", [])]
            if v["listUpdated"] >= ch["effective"]:
                problems.append("CHANGES %s %d: the list is dated %s, on or after the "
                                "change; retire the entry" % (court, ch["district"], v["listUpdated"]))
            if ch["out"] in got:
                problems.append("CHANGES %s %d: %s is still named" % (court, ch["district"], ch["out"]))
            if ch["in"]:
                if [m for m in rec.get("members", []) if m.get("name") == ch["in"]
                        and m.get("source") == ch["source"] and m.get("note") == ch["note"]] == []:
                    problems.append("CHANGES %s %d: %s is not named with the entry's note "
                                    "and source" % (court, ch["district"], ch["in"]))
            elif {"text": ch["note"], "label": ch["source"]["label"],
                  "url": ch["source"]["url"]} not in rec.get("notes", []):
                problems.append("CHANGES %s %d: the district carries no note for %s"
                                % (court, ch["district"], ch["out"]))
    return problems


# ---------------------------------------------------------------- selftest

def expect_fail(what, fn, *args):
    """Run fn(*args), which must stop the build; its FAIL line is swallowed so a
    passing selftest prints one line."""
    import contextlib
    import io

    with contextlib.redirect_stderr(io.StringIO()) as err:
        try:
            fn(*args)
        except SystemExit:
            return err.getvalue()
    raise AssertionError("%s must stop the build" % what)


def selftest():
    cell = ('<td><!-- <a href="bios/old.php"> --><a href="bios/judgeSt. Pe\'.php" '
            'aria-label="x"><img src="t.jpg"><br><span><strong>Judge Amy Lassitter '
            'St. P&eacute;</strong><br></span></a> <em>District 5, Position 2</em>'
            '<p>bio</p></td>')
    rows = parse_appellate(cell, "appeals")
    assert rows == [{"name": "Amy Lassitter St. P\u00e9", "role": "Judge", "district": 5,
                     "seat": "Position 2",
                     "profileUrl": BASE + "/appellatecourts/coa/bios/judgeSt.%20Pe%27.php"}], rows
    rows = parse_appellate('<td><a href="bios/j.php"><strong>Judge Anthony N. Lawrence, '
                           'III</strong></a><em>District 5, Position 1</em></td>', "appeals")
    assert rows[0]["name"] == "Anthony N. Lawrence III", rows

    # The staff lines are invented (a list's real staff are never written here,
    # not even as a fixture); the judges' names are as the list prints them.
    lines = ["Chancery Court Judges and Staff", "Updated August 1, 2025",
             "1st Chancery District", "Alcorn, Tishomingo,", "and Union counties",
             "Address", "Judge", "Jacqueline Mask", "P.O. Box 100", "Exampleton 00000",
             "Court Reporter", "Pat Example", "100 Example Circle",
             "Judge  ", "Michael P. Mills, Jr.", "Staff Attorney", "Sam Example",
             "2nd Chancery District", "Hinds County", "Address",
             "Judge", "Grady F. Tollison, III."]
    updated, d = parse_trial_lines(lines, "chancery")
    assert updated == "2025-08-01"
    assert d == {1: {"counties": ["Alcorn", "Tishomingo", "Union"],
                     "judges": ["Jacqueline Mask", "Michael P. Mills Jr."]},
                 2: {"counties": ["Hinds"], "judges": ["Grady F. Tollison III"]}}, d
    # A layout change that puts an address where a name was stops the build.
    for bad in ("P.O. Box 100", "100 Example Circle", "someone@example.com"):
        expect_fail("an address under 'Judge' (%r)" % bad,
                    parse_trial_lines, lines[:6] + ["Judge", bad], "chancery")

    today = {1: frozenset({"alcorn", "tishomingo", "union"}), 2: frozenset({"hinds"})}
    y2027 = {1: frozenset({"alcorn", "tishomingo"}), 2: frozenset({"hinds", "union"})}
    maps = {"until-2027": today, "from-2027": y2027}
    assert structure_of("chancery", d, maps) == "until-2027"
    moved = {1: {"counties": ["Alcorn", "Tishomingo"]}, 2: {"counties": ["Hinds", "Union"]}}
    assert structure_of("chancery", moved, maps) == "from-2027"
    expect_fail("a list matching neither map", structure_of, "chancery",
                {1: {"counties": ["Alcorn"]}, 2: {"counties": ["Hinds"]}}, maps)

    src = {"label": "x", "url": "https://example.test/a"}
    swap = {"court": "chancery", "district": 1, "out": "Jacqueline Mask",
            "in": "New Judge", "effective": "2026-07-01", "note": "n", "source": src}
    died = {"court": "chancery", "district": 1, "out": "Michael P. Mills Jr.",
            "in": None, "effective": "2026-09-16", "note": "died", "source": src}

    def run(changes, upd="2025-08-01", dists=None):
        dists = dists or {k: {"counties": list(v["counties"]), "judges": list(v["judges"])}
                          for k, v in d.items()}
        return apply_changes("chancery", upd, dists, changes), dists

    notes, got = run([swap, died])
    assert got[1]["judges"] == [{"name": "New Judge", "note": "n", "source": src}], got
    assert notes == {1: [{"text": "died", "label": "x", "url": src["url"]}]}, notes
    for label, changes, upd in (
            ("a list dated on or after the change", [swap], "2026-07-01"),
            ("a list that no longer prints the person who left",
             [dict(swap, out="Somebody Else")], "2025-08-01"),
            ("a list that already prints the person who arrived",
             [dict(swap, **{"in": "Michael P. Mills Jr."})], "2025-08-01")):
        expect_fail("a CHANGES entry over %s" % label, run, changes, upd)

    # The whole assembly: exact appellate seats, the overlap gate, and check().
    letters = "abcdefghijklmnopqrstuvwxyz"

    def bench(court, n_d, per):
        spec = COURTS[court]
        return [{"name": "Appellate %s Judge %s %s" % (court.title(), letters[dd], letters[s]),
                 "role": spec["chief"] if (dd, s) == (1, 1) else spec["titles"][-1],
                 "district": dd, "seat": "%s %d" % (spec["seat"], s),
                 "profileUrl": spec["url"].rsplit("/", 1)[0] + "/bios/x.php"}
                for dd in range(1, n_d + 1) for s in range(1, per + 1)]

    def benchful(prefix, base):
        return {k: {"counties": v["counties"],
                    "judges": list(base.get(k, [])) +
                    ["%s Judge %s %s%s" % (prefix, letters[k], c, e)
                     for c in letters for e in "ab"]}
                for k, v in d.items()}

    # Telephones. Every judge gets an invented number of their own, except two
    # who share one (the court office's line, carried on neither) and one whose
    # Phone cell holds two numbers (carried as nothing); the lists' real
    # numbers are never written here either.
    def phoned(court, dists):
        names = [n for v in dists.values() for n in v["judges"]]
        cells = {n: "(555)%03d-%04d" % (i // 10000, i % 10000) for i, n in enumerate(names)}
        cells[names[2]] = cells[names[1]]
        cells[names[3]] = "(555)000-0000 (555)000-0001"
        odd, shared = attach_phones(court, dists, cells)
        assert odd == [names[3]] and shared == sorted(names[1:3]), (odd, shared)
        flat = [j for v in dists.values() for j in v["judges"]]
        assert all(isinstance(j, str) for j in flat[1:4]), flat[:5]
        assert all(PHONE_CELL_RE.match(j["phone"]) for j in flat[:1] + flat[4:]), flat[4:6]
        return dists

    appellate = {"supreme": bench("supreme", 3, 3), "appeals": bench("appeals", 5, 2)}
    appellate_maps = {"supreme": {1, 2, 3}, "appeals": {1, 2, 3, 4, 5}}
    trial = {"chancery": ("2025-08-01", phoned("chancery", benchful(
                 "Chancery", {k: v["judges"] for k, v in d.items()}))),
             "circuit": ("2026-02-04", phoned("circuit", benchful("Circuit", {})))}
    expect_fail("a table naming a judge the lines do not", attach_phones, "circuit",
                benchful("Circuit", {}), {"Somebody Else": "(555)000-0000"})
    all_maps = {"chancery": maps, "circuit": maps}
    payload = assemble(appellate, trial, all_maps, appellate_maps, [swap, died])
    assert payload["courts"]["chancery"]["structure"] == "until-2027"
    assert payload["courts"]["chancery"]["districts"]["1"]["notes"][0]["text"] == "died"
    assert not check(payload, all_maps, appellate_maps, changes=[swap, died]), \
        check(payload, all_maps, appellate_maps, changes=[swap, died])
    # check() notices a hand edit that undoes a change.
    edited = json.loads(json.dumps(payload))
    edited["courts"]["chancery"]["districts"]["1"]["members"][0] = {"name": "Jacqueline Mask"}
    assert check(edited, all_maps, appellate_maps, changes=[swap, died])
    # ...one number on two judges, and a telephone that is an address, whose
    # value the message never prints.
    for bad in ("shared", "street"):
        edited = json.loads(json.dumps(payload))
        members = [m for m in edited["courts"]["circuit"]["districts"]["2"]["members"]
                   if m.get("phone")]
        members[0]["phone"] = members[1]["phone"] if bad == "shared" else "100 Example Street"
        found = check(edited, all_maps, appellate_maps, changes=[swap, died])
        assert found and not any("Example" in f for f in found), (bad, found)
    # A trial judge who also sits on an appellate court stops the build.
    moved = benchful("Circuit", {1: [appellate["supreme"][0]["name"]]})
    expect_fail("a trial judge who sits on an appellate court", assemble, appellate,
                dict(trial, circuit=("2026-02-04", moved)), all_maps, appellate_maps,
                [swap, died])
    short = dict(appellate, supreme=appellate["supreme"][:-1])
    expect_fail("an appellate page one seat short", assemble, short, trial, all_maps,
                appellate_maps, [swap, died])
    print("%s: selftest OK — appellate cells, the list's two lines per judge, an "
          "address refused as a name, map detection, every way a change goes stale, "
          "the overlap and seat gates, a judge's own telephone and the shared one "
          "carried on nobody, and check() catching a hand edit" % LABEL)


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="offline shape gate")
    ap.add_argument("--selftest", action="store_true", help="offline, needs no files")
    ap.add_argument("--save", metavar="DIR", help="keep what was fetched, outside the repo")
    ap.add_argument("--offline", metavar="DIR", help="build from a --save folder")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    maps, appellate_maps = load_maps()
    if args.check:
        if not os.path.exists(OUT):
            fail("%s is missing" % os.path.relpath(OUT, REPO))
        with open(OUT, encoding="utf-8") as fh:
            payload = json.load(fh)
        problems = check(payload, maps, appellate_maps)
        for p in problems:
            print("%s --check: FAIL — %s" % (LABEL, p), file=sys.stderr)
        if problems:
            raise SystemExit(1)
        today = datetime.date.today().isoformat()
        for court in ("chancery", "circuit"):
            if payload["courts"][court]["structure"] == "until-2027" and today >= "2027-01-01":
                print("%s --check: NOTE — the %s list still describes the districts "
                      "before 1 January 2027, so the app names no %s judge on the new "
                      "map; ms/WATCH.md says what to do" % (LABEL, court, court))
        print("%s --check: OK — %s" % (LABEL, summary(payload)))
        return
    if args.offline:
        raw = read_saved(args.offline)
    else:
        raw = fetch_all(outside_repo(args.save) if args.save else None)
    appellate = {c: parse_appellate(raw[c], c) for c in ("supreme", "appeals")}
    trial = {}
    for c in ("chancery", "circuit"):
        updated, districts = parse_trial_lines(pdf_lines(raw[c]), c)
        odd, shared = attach_phones(c, districts, judge_phone_cells(raw[c], c))
        # Names only, never a number: the run's log is public in Actions.
        if odd:
            print("%s: NOTE — the %s list's Phone cell for %s is not one telephone "
                  "number, so no number is carried" % (LABEL, c, "; ".join(odd)))
        if shared:
            print("%s: NOTE — the %s list prints the same number for %d judges (%s), "
                  "the court office's line, so it rides none of them"
                  % (LABEL, c, len(shared), "; ".join(shared)))
        trial[c] = (updated, districts)
    payload = assemble(appellate, trial, maps, appellate_maps)
    problems = check(payload, maps, appellate_maps)
    if problems:
        fail("the assembled roster fails its own check: " + "; ".join(problems))
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(render(payload))
    print("%s: wrote %s — %s" % (LABEL, os.path.relpath(OUT, REPO), summary(payload)))


if __name__ == "__main__":
    main()
