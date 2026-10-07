#!/usr/bin/env python3
"""Scrape stage 1: the supervisors a county names on its OWN board page.

WHY A THIRD PUBLISHER, WHEN TWO ALREADY DISAGREE
------------------------------------------------
`build_ia_county_officers.py` ships a county's board only when two independent
statements agree: the ISAC directory's list of supervisors, and the seat count
this repo reads back from the state's shipped supervisor-district layer. Where
they disagree it WITHHOLDS the whole board with the reason printed, because
two publishers naming two different boards is not a thing to resolve by
preference. That is right, and it left EIGHT counties of 99 naming no
supervisor at all -- the whole of Iowa's remaining county tier under the fourth
test in `docs/DONE_STANDARD.md`.

What was never done is ask the county. Measured 2026-10-01, robots.txt read
first with the client that would crawl and every one permitting, SEVEN of the
eight publish their full board on their own website. A county is the publisher
OF ITS OWN BOARD, so where it names a legal board that agrees with the
districts this app draws, that is not a preference between two outside
directories -- it is the body itself.

WHAT THIS FILE READS, AND WHAT IT DELIBERATELY DOES NOT
-------------------------------------------------------
Five of the eight are here. The other three are measured and excluded, each for
its own reason, because an exclusion stated with its measurement is worth more
than a county quietly missing:

  WARREN needed nothing fetched. Its board was withheld because the shipped
  geometry's NUMDISTRICTS column says 3 while the SAME FILE draws five numbered
  district polygons. `build_ia_county_board_directory.py` now counts the
  polygons, the ISAC list of five agrees, and the gate passes on its own.

  WRIGHT is the county this route CANNOT close, and that is a finding rather
  than a gap. It names five supervisors on its own page, in districts 1 to 5,
  while the state's supervisor-district layer (vintage 2024-01-30) draws THREE
  districts for it. Shipping five names against a three-district map would have
  the card naming a supervisor for a district the map does not draw. The stale
  thing is the MAP, which is a different repair from a roster, so it is
  recorded as a gap instead.

  TAMA WAS THE SAME CASE UNTIL 2026-10-07, when the county's own five-district
  map replaced the state's three (build_county_supplied_supervisor_districts.py)
  and its page joined this file -- the fifth county here.

  POTTAWATTAMIE refuses this project at the page, with the districtry token and
  with a browser client alike, at `www.pottcounty-ia.gov` and at the apex, while
  publishing NO robots.txt at all to either (HTTP 404, which RFC 9309 files as
  allow). So it is a site-wide block rather than a policy, nothing here works
  around it, and its board stays withheld with the reason it already carries.

THREE PAGE SHAPES FOR FIVE COUNTIES, EACH DECLARED
---------------------------------------------------
  board_members   Adair, Lucas, Tama. A `Board Members` heading, then per supervisor
                  a NAME line followed by a role line -- Adair writes the role
                  INTO the name line (`Jerry Walker Chairperson - District 3SW
                  Supervisor`), Lucas puts a bare `Supervisor` on the line
                  after, and Tama the seat alone (`1st District`). Each member is followed by a `Representative
                  Appointments` block naming committees, which is where a
                  careless parse finds its next "member".

  district_line   Humboldt. `District N   <Name>`, then `Term:`, `Phone:` and
                  `Email:` lines, one member after another with no wrapper.

  staff_directory Floyd. The CivicPlus staff directory (`/m/directory/
                  department?did=`), which prints each person's INITIALS on
                  their own line above their name, then the title TWICE, then
                  `Email <Name>`, then the phone.

TWO TRAPS RECORDED WITH THEIR FIXTURES
---------------------------------------
ADAIR'S DISTRICTS ARE NOT NUMBERS. It writes `District 1NW`, `District 2NE`,
`District 3SW`, `District 4SE`, `District 5GF` -- a number and a compass
quadrant. A district pattern anchored on digits alone takes `1` and drops the
rest of the label, and one anchored on `\\d+$` matches nothing at all.

FLOYD PRINTS EVERY TITLE TWICE and its initials line is two capital letters
(`GC`, `FR`, `BC`) sitting exactly where a name is expected. A parser that
takes the line above the title gets `BC`, which passes a loose name test.

NO ADDRESS IS EVER CARRIED. These pages are courthouse addresses rather than
home ones, but the refusal is the fleet's and is not relaxed per page: a field
that reads as a street address is dropped, and the builder refuses again.

Stage 2 is `build_ia_county_officers.py`, which consults this cache ONLY for a
county whose two outside publishers disagree, and ships it only when the page's
board is a legal size AND equals the districts the app draws.
"""

import html as H
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "scripts"))

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
OUT = os.path.join(CACHE_DIR, "ia_county_board_pages.json")

UA = "districtry/1.0 (+https://districtry.com/ia/)"
HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}
TIMEOUT = 30

# geoid3 -> the county, its own board page, and the shape that page is in.
COUNTIES = [
    {"fips": "001", "name": "Adair", "shape": "board_members",
     "url": "https://www.adaircounty.iowa.gov/supervisors/"},
    {"fips": "067", "name": "Floyd", "shape": "staff_directory",
     # floydco.iowa.gov, NOT www.floydco.iowa.gov: the www name resets the
     # connection while the bare name answers 200, and the ISAC directory
     # publishes the www one. Measured 2026-10-01.
     "url": "https://floydco.iowa.gov/m/directory/department?did=21"},
    {"fips": "091", "name": "Humboldt", "shape": "district_line",
     "url": "https://www.humboldtcounty.iowa.gov/offices/administrative/"
            "board_of_supervisors/index.php"},
    {"fips": "117", "name": "Lucas", "shape": "board_members",
     "url": "https://lucascounty.iowa.gov/board_of_supervisors/"},
    # TAMA joined on 2026-10-07, when its five-district map did: the page has
    # named five supervisors in districts 1st to 5th all along, and was
    # excluded only because the shipped map drew three. robots.txt: HTTP 404
    # (allow all), read 2026-10-07 with this file's own client.
    #
    # NO TELEPHONE FROM THIS PAGE. The page prints one number per supervisor
    # and nothing says which are county lines; one is a 319 number for a
    # supervisor whose listed e-mail is a personal address. The Auditor was
    # asked on 2026-10-01 which numbers are county lines and has not said, so
    # the county's own board office number (on the County card) is what a
    # reader gets.
    {"fips": "171", "name": "Tama", "shape": "board_members", "phones": False,
     "url": "https://www.tamacounty.iowa.gov/supervisors/"},
]

TAGS = re.compile(r"(?s)<(script|style|noscript)\b.*?</\1>")
SUFFIX = r"(?:,\s*(?:Jr|Sr|II|III|IV)\.?)?"
NAME = re.compile(r"^[A-Z][\w.'’-]*(?:\s+[A-Z][\w.'’-]*){1,3}"
                  + SUFFIX + r"$", re.U)
# A district label is a NUMBER plus whatever the county attaches to it. Adair
# writes 1NW / 2NE / 3SW / 4SE / 5GF, so the trailing letters are part of the
# label and not noise to strip.
DISTRICT = re.compile(r"(?i)\bDistrict\s+(\d+[A-Z]{0,3})\b")
ORDINAL = re.compile(r"(?i)\b(\d+)(?:st|nd|rd|th)\s+District\b")
SEAT_LINE = re.compile(r"(?i)^\s*(?:\d+(?:st|nd|rd|th)\s+District|District\s+\d+[A-Z]{0,3})\b")
ROLE_WORD = re.compile(r"(?i)\b(supervisor|chair(?:man|person|woman)?|"
                       r"vice[-\s]?chair(?:man|person|woman)?|chairman\s+pro\s+tem)\b")
NOT_A_PERSON = re.compile(
    r"(?i)(\d{3}|^(board|representative|appointments?|county|contact|home|search"
    r"|email|phone|term|location|mailing|driving|office|department|related"
    r"|agendas?|minutes?|meetings?|skip|login|share|close|back|view|the)\b)")
# Two capitals on a line of their own is CivicPlus's avatar initials, not a
# person. `NAME` accepts it (two tokens, both capitalised), so it is refused
# explicitly rather than by tightening a pattern every other shape relies on.
INITIALS = re.compile(r"^[A-Z]{2,3}$")
ADDRESS = re.compile(
    r"(?i)(^\s*\d+[\w-]*\s+[\w.'-]+(\s+[\w.'-]+)*\s*,?\s*\b(st|street|ave|avenue"
    r"|rd|road|dr|drive|ln|lane|ct|court|pl|place|blvd|boulevard|way|ter|terrace"
    r"|cir|circle|pkwy|parkway|hwy|highway|suite|ste)\b"
    r"|\b[A-Z][a-z]+,\s*(IA|Iowa)\s*\d{5}\b"
    r"|\bP\.?\s*O\.?\s*Box\s*\d+)")
EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{4}")
TERM = re.compile(r"(?i)term(?:\s*expires?)?\s*:?\s*(.+)")


def text_lines(page):
    """The page as display lines, the way the other Iowa scrapers read one."""
    h = TAGS.sub(" ", page)
    h = re.sub(r"(?s)<!--.*?-->", " ", h)
    h = re.sub(r"(?i)<br\s*/?>", "\n", h)
    h = re.sub(r"(?i)</(p|div|li|tr|td|th|h[1-6]|a|span)\s*>", "\n", h)
    h = re.sub(r"(?s)<[^>]+>", " ", h)
    h = H.unescape(h)
    # A NO-BREAK SPACE IS NOT A SPACE TO `str.strip`. Humboldt separates
    # `District 1` from `Bruce Reimers` with U+00A0, so the name arrives with
    # a leading non-space the name pattern cannot start on, and the first live
    # run read ZERO supervisors on a page that names five. Every reader here
    # trims and splits on whitespace, so the character is normalised once,
    # for every shape, rather than guarded per parser.
    h = h.replace("\u00a0", " ").replace("\u2007", " ").replace("\u202f", " ")
    return [re.sub(r"\s+", " ", l).strip() for l in h.split("\n") if l.strip()]


def name_like(s):
    """Is this line a person's name and nothing else?"""
    if not s or len(s) > 60:
        return False
    if INITIALS.match(s) or NOT_A_PERSON.search(s) or ADDRESS.search(s):
        return False
    if ROLE_WORD.search(s) or EMAIL.search(s) or PHONE.search(s):
        return False
    return bool(NAME.match(s))


def seat_of(s):
    """The district label a county attaches to a seat, in its own words."""
    m = DISTRICT.search(s)
    if m:
        return m.group(1).upper()
    m = ORDINAL.search(s)
    if m:
        return m.group(1)
    return None


def split_role_name(line):
    """`Jerry Walker Chairperson - District 3SW Supervisor` -> both halves.

    A county that writes the role into the name line gives no separator worth
    relying on, so the split is at the first ROLE word, and the left half has
    to survive `name_like` on its own or the line is not this shape.
    """
    # The split is at the first ROLE word OR the first `District`, whichever
    # comes first: Adair writes `Matt Wedemeyer District 1NW Supervisor`, so
    # splitting on the role alone leaves `Matt Wedemeyer District 1NW` on the
    # left, and no name survives that.
    # Tama writes the seat as an ordinal (`Curt Hilmer 1st District`), so a
    # cut at `District` alone leaves `Curt Hilmer 1st` on the left; the
    # ordinal's own start is a cut point too.
    cuts = [m.start() for m in (ROLE_WORD.search(line),
                                re.search(r"(?i)\bDistrict\b", line),
                                ORDINAL.search(line)) if m]
    if not cuts or min(cuts) == 0:
        return None, None
    cut = min(cuts)
    left = line[:cut].strip(" -\u00b7\u2013,")
    right = line[cut:].strip()
    if not name_like(left):
        return None, None
    # AND THE RIGHT HALF MUST REALLY BE A ROLE. Splitting on `District`
    # alone also cuts a committee name inside the previous member's
    # appointments block: Adair's `Fifth Judicial District-Corrections`
    # gives a left half of `Fifth Judicial`, which is two capitalised words
    # and passes every name test there is. The first live run shipped it as
    # Adair's sixth supervisor on a five-seat board. A role word on the right
    # is what tells a seat from a committee.
    if not (ROLE_WORD.search(right) or SEAT_LINE.match(right)):
        return None, None
    return left, right


def _fields(window):
    """phone / email / term, from the lines that bound one member."""
    out = {}
    for l in window:
        if ADDRESS.search(l):
            continue
        if "email" not in out:
            m = EMAIL.search(l)
            if m:
                out["email"] = m.group(0).lower()
        if "phone" not in out:
            m = PHONE.search(l)
            if m and not EMAIL.search(l):
                out["phone"] = m.group(0).strip()
        if "term" not in out and re.match(r"(?i)\s*term\b", l):
            m = TERM.search(l)
            if m and m.group(1).strip():
                out["term"] = m.group(1).strip()
    return out


def parse_board_members(lines):
    """Adair, Lucas: a `Board Members` heading and a name per member."""
    try:
        start = next(i for i, l in enumerate(lines)
                     if re.fullmatch(r"(?i)\s*board members\s*", l))
    except StopIteration:
        return []
    hits = []
    for i in range(start + 1, len(lines)):
        l = lines[i]
        left, right = split_role_name(l)
        if left:
            hits.append((i, left, right))
            continue
        # A BARE NAME WHOSE NEXT LINE IS A ROLE AND NOTHING ELSE. Without
        # that last clause `Adair County Tourism` -- a committee inside the
        # previous member's appointments block -- forms a member, because the
        # line after it is the next supervisor's own name-and-role line and
        # that carries a role word. A committee name standing above a member
        # is how this shape invents people.
        if name_like(l):
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            # Tama's role line is the SEAT alone (`1st District`, `3rd
            # District - Vice Chair`), so a line that opens with a district
            # number counts as a role line too. It must OPEN with it: a
            # committee such as `6th Judicial District` puts a word between
            # the number and `District` and is refused by SEAT_LINE.
            if ((ROLE_WORD.search(nxt) or SEAT_LINE.match(nxt))
                    and not name_like(nxt) and not split_role_name(nxt)[0]):
                hits.append((i, l, nxt))
    return _from_hits(lines, hits)


def parse_district_line(lines):
    """Humboldt: `District N   <Name>` then Term / Phone / Email."""
    hits = []
    for i, l in enumerate(lines):
        m = DISTRICT.match(l.strip())
        if not m:
            continue
        rest = l[m.end():].strip(" ·-")
        if name_like(rest):
            hits.append((i, rest, l))
            continue
        # THE NAME CAN SIT ON THE NEXT LINE. Humboldt wraps each name in its
        # own element, so whether `District 1` and `Bruce Reimers` arrive as
        # one display line or two depends on which tags the reader breaks on
        # -- and this reader breaks on `span`, which the live page uses.
        # Reading the same line only answered ZERO supervisors on the first
        # live run, for a page that names five.
        if not rest:
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if name_like(nxt):
                hits.append((i + 1, nxt, l))
    return _from_hits(lines, hits)


def parse_staff_directory(lines):
    """Floyd: CivicPlus. Initials, name, title, title again, Email X, phone."""
    hits = []
    for i, l in enumerate(lines):
        if not name_like(l):
            continue
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if ROLE_WORD.search(nxt) and seat_of(nxt):
            hits.append((i, l, nxt))
    return _from_hits(lines, hits)


def _from_hits(lines, hits):
    """Bound each member by the next, and the last by the page's own gap.

    The last member is the one no next member bounds, which is where a footer
    donates a telephone number to whoever is last in the list. The window is
    the SMALLEST gap this page itself puts between two members, so a page that
    prints four lines per member never reaches ten lines past the last one.
    """
    if not hits:
        return []
    gaps = [hits[n + 1][0] - hits[n][0] for n in range(len(hits) - 1)]
    tail = min(gaps) if gaps else 6
    out = []
    for n, (i, name, role) in enumerate(hits):
        end = hits[n + 1][0] if n + 1 < len(hits) else min(i + tail, len(lines))
        rec = {"name": name}
        seat = seat_of(role) or seat_of(lines[i])
        if seat:
            rec["seat"] = seat
        rec.update(_fields(lines[i:end]))
        out.append(rec)
    return out


SHAPES = {"board_members": parse_board_members,
          "district_line": parse_district_line,
          "staff_directory": parse_staff_directory}


def dedupe(members):
    """One row per person, keeping the first and merging later fields in."""
    seen = {}
    order = []
    for m in members:
        key = re.sub(r"[^a-z]", "", m["name"].lower())
        if key in seen:
            for k, v in m.items():
                seen[key].setdefault(k, v)
            continue
        seen[key] = m
        order.append(key)
    return [seen[k] for k in order]


def refuse_addresses(members, county):
    """No field on a person's row may read as a street address."""
    for m in members:
        for k, v in list(m.items()):
            if isinstance(v, str) and ADDRESS.search(v):
                raise RuntimeError(
                    "%s: %r reads as a street address and this project ships "
                    "none -- the page's shape has changed" % (county, v))


def scrape(session, gate):
    out = {}
    for c in COUNTIES:
        allowed, why = gate.allows(c["url"])
        if not allowed:
            # WHICH no it is matters: a served file saying no is a policy, an
            # unreachable one is RFC 9309 abstention, and the two must not be
            # flattened into one word.
            stated = why.startswith("robots.txt served")
            out[c["fips"]] = {"county": c["name"], "url": c["url"],
                              "verdict": "robots-refused" if stated
                                         else "robots-unknown", "why": why}
            print("  %-13s %s" % (c["name"], out[c["fips"]]["verdict"]),
                  file=sys.stderr)
            continue
        r = session.get(c["url"], headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            out[c["fips"]] = {"county": c["name"], "url": c["url"],
                              "verdict": "http-%d" % r.status_code}
            print("  %-13s HTTP %d" % (c["name"], r.status_code),
                  file=sys.stderr)
            continue
        members = dedupe(SHAPES[c["shape"]](text_lines(r.text)))
        refuse_addresses(members, c["name"])
        if c.get("phones") is False:
            for m in members:
                m.pop("phone", None)
        out[c["fips"]] = {"county": c["name"], "url": c["url"],
                          "shape": c["shape"], "verdict": "ok",
                          "members": members}
        print("  %-13s %d supervisor(s): %s"
              % (c["name"], len(members),
                 ", ".join(m["name"] for m in members)), file=sys.stderr)
    return out


# --------------------------------------------------------------------------
# self-test: synthetic pages in each shape, no network.

ADAIR_PAGE = """
<div>Board Members</div>
<div>Matt Wedemeyer District 1NW Supervisor</div>
<div>Term Expires: 2028</div>
<div>Representative Appointments</div>
<div>Adair County Tourism</div>
<div>Jerry Walker Chairperson &middot; District 3SW Supervisor</div>
<div>Term Expires: 2028</div>
<div>Representative Appointments</div>
<div>Landfill Board, Alt</div>
"""

LUCAS_PAGE = """
<div>Board Members</div>
<div>Larry Davis</div><div>Supervisor</div>
<div>Representative Appointments</div>
<div>Larry Davis is appointed to the following committees/boards:</div>
<div>E911 Board</div>
<div>Cathy Reece</div><div>Supervisor</div>
<div>Representative Appointments</div>
<div>Area Agency on Aging board</div>
"""

HUMBOLDT_PAGE = """
<div>HUMBOLDT COUNTY BOARD OF SUPERVISORS</div>
<div>District 1&nbsp; &nbsp; Bruce Reimers</div>
<div>Term:       Jan 2023 to Dec 2026</div>
<div>Phone:      515 770-1067</div>
<div>Email:     breimers@humboldtcounty.iowa.gov</div>
<div>District 2      Dennis Thompson</div>
<div>Term:        Nov 2025 to Dec 2026</div>
<div>Phone:      515 332-0597</div>
<div>Email:     dthompson@humboldtcounty.iowa.gov</div>
<div>Humboldt County Courthouse</div>
<div>203 Main St Dakota City, IA 50529</div>
<div>Phone: 515 332-1571</div>
"""

FLOYD_PAGE = """
<div>Physical Address</div><div>101 S Main Street</div><div>Suite 304</div>
<div>Charles City, IA 50616</div><div>Phone Number</div><div>641-257-6129</div>
<div>GC</div><div>Gloria Carr</div>
<div>County Supervisor, District 1</div><div>County Supervisor, District 1</div>
<div>Email Gloria Carr</div><div>641-330-0989</div>
<div>FR</div><div>Frank   Rottinghaus</div>
<div>County Supervisor, District 2</div><div>County Supervisor, District 2</div>
<div>Email Frank Rottinghaus</div><div>641-426-0156</div>
<div>Back to Directory</div>
"""


HUMBOLDT_SPLIT_PAGE = """
<div><span>District 1</span><span>Bruce Reimers</span></div>
<div>Phone:      515 770-1067</div>
<div><span>District 2</span><span>Dennis Thompson</span></div>
<div>Phone:      515 332-0597</div>
"""

TAMA_PAGE = """
<div>Supervisors</div>
<div>Board Members</div>
<div>Curt Hilmer</div><div>1st District</div><div>319-939-3291</div>
<div>Term Expires: 2028</div>
<div>Representative Appointments</div>
<div>Curt Hilmer is also appointed to the following committees/boards:</div>
<div>Board of Health Services</div>
<div>6th Judicial District</div>
<div>Heather Knebel</div><div>3rd District - Vice Chair</div>
<div>641-481-2532</div><div>Term Expires: 2026</div>
<div>Representative Appointments</div>
<div>Mark Doland</div><div>4th District - Chair</div>
"""

# What the live page reads as: this reader breaks on <a> and <span> closes
# only, and the name and its seat share one element, so they arrive joined.
TAMA_JOINED_PAGE = """
<div>Board Members</div>
<div>Curt Hilmer 1st District</div><div>319-939-3291</div>
<div>Representative Appointments</div>
<div>6th Judicial District</div>
<div>David Turner 2nd District</div><div>641-481-2456</div>
<div>Representative Appointments</div>
<div>Region VI Planning Commission</div>
<div>Central Iowa Juvenile Detention</div>
<div>Heather Knebel 3rd District - Vice Chair</div>
"""

ADAIR_COMMITTEE_PAGE = """
<div>Board Members</div>
<div>Jodie Hoadley District 2NE Supervisor</div>
<div>Representative Appointments</div>
<div>Fifth Judicial District-Corrections</div>
<div>MATURA</div>
<div>Jerry Walker Chairperson &middot; District 3SW Supervisor</div>
"""

def _selftest():
    checks = failed = 0

    def ok(label, got, want):
        nonlocal checks, failed
        checks += 1
        good = got == want
        if not good:
            failed += 1
        print("  %s %-62s got %r" % ("ok  " if good else "FAIL", label, got))

    a = dedupe(parse_board_members(text_lines(ADAIR_PAGE)))
    ok("Adair: two supervisors", [m["name"] for m in a],
       ["Matt Wedemeyer", "Jerry Walker"])
    # THE TRAP: a compass quadrant is part of the label, not noise.
    ok("Adair: the district label keeps its quadrant",
       [m.get("seat") for m in a], ["1NW", "3SW"])
    ok("Adair: a committee name is not a supervisor",
       any(m["name"].startswith("Adair County") for m in a), False)
    ok("Adair: the term is carried", a[0].get("term"), "2028")

    l = dedupe(parse_board_members(text_lines(LUCAS_PAGE)))
    ok("Lucas: the role on the NEXT line still forms a member",
       [m["name"] for m in l], ["Larry Davis", "Cathy Reece"])
    ok("Lucas: an at-large board carries no seat label",
       [m.get("seat") for m in l], [None, None])
    ok("Lucas: the appointments sentence is not a second member",
       len(l), 2)

    h = dedupe(parse_district_line(text_lines(HUMBOLDT_PAGE)))
    ok("Humboldt: a district line names its member",
       [m["name"] for m in h], ["Bruce Reimers", "Dennis Thompson"])
    ok("Humboldt: seats", [m["seat"] for m in h], ["1", "2"])
    # The no-break space is in the first fixture row above on purpose: it is
    # what the live page uses and what read as zero supervisors.
    ok("Humboldt: e-mail", h[0].get("email"), "breimers@humboldtcounty.iowa.gov")
    # THE LAST MEMBER IS THE ONE NO NEXT MEMBER BOUNDS. The courthouse's own
    # number sits four lines past Thompson's row; the window is the page's own
    # member-to-member gap, so it never reaches it.
    ok("Humboldt: the courthouse number is not the last member's",
       h[-1].get("phone"), "515 332-0597")
    ok("Humboldt: no courthouse address is carried",
       any("Main St" in str(v) for m in h for v in m.values()), False)

    f = dedupe(parse_staff_directory(text_lines(FLOYD_PAGE)))
    # Floyd prints `Frank   Rottinghaus` with three spaces in its own markup.
    # The reader collapses runs of whitespace, so the name ships with one --
    # the only normalisation applied to a person's name anywhere here, and it
    # is of the separator rather than of the name.
    ok("Floyd: two supervisors", [m["name"] for m in f],
       ["Gloria Carr", "Frank Rottinghaus"])
    # THE TRAP: `GC` is two capitals on its own line, exactly where a name goes.
    ok("Floyd: the avatar initials are not a person",
       any(len(m["name"]) <= 3 for m in f), False)
    ok("Floyd: the title printed twice makes one member", len(f), 2)
    ok("Floyd: seats", [m["seat"] for m in f], ["1", "2"])
    ok("Floyd: the office suite is not carried",
       any("Suite" in str(v) for m in f for v in m.values()), False)

    # BOTH OF THESE FAILED ON THE FIRST LIVE RUN and no synthetic page above
    # reproduced either, which is why each has a fixture of its own.
    hs = dedupe(parse_district_line(text_lines(HUMBOLDT_SPLIT_PAGE)))
    ok("Humboldt: a name in its own element is still read",
       [m["name"] for m in hs], ["Bruce Reimers", "Dennis Thompson"])
    ok("Humboldt: and keeps its district", [m["seat"] for m in hs], ["1", "2"])
    ac = dedupe(parse_board_members(text_lines(ADAIR_COMMITTEE_PAGE)))
    ok("Adair: a committee with `District` in its name is not a supervisor",
       [m["name"] for m in ac], ["Jodie Hoadley", "Jerry Walker"])

    t = dedupe(parse_board_members(text_lines(TAMA_PAGE)))
    ok("Tama: a seat-only line after a name forms a member",
       [m["name"] for m in t], ["Curt Hilmer", "Heather Knebel", "Mark Doland"])
    ok("Tama: seats from the ordinal", [m.get("seat") for m in t], ["1", "3", "4"])
    ok("Tama: a committee naming a judicial district is not a member",
       any("Judicial" in m["name"] or m["name"] == "Board of Health Services"
           for m in t), False)
    tj = dedupe(parse_board_members(text_lines(TAMA_JOINED_PAGE)))
    ok("Tama: a name and its ordinal seat on one line",
       [(m["name"], m.get("seat")) for m in tj],
       [("Curt Hilmer", "1"), ("David Turner", "2"), ("Heather Knebel", "3")])
    ok("a seat line must open with its number",
       bool(SEAT_LINE.match("6th Judicial District")), False)

    ok("a street address is refused outright",
       _raises(refuse_addresses, [{"name": "A B", "seat": "101 S Main Street"}], "X"),
       True)
    ok("a bare role line is not a name", name_like("County Supervisor"), False)
    ok("a committee line is not a name", name_like("Landfill Board, Alt"), False)
    ok("a real name is", name_like("Bruce Reimers"), True)
    ok("a hyphenated name is", name_like("Jean-Paul O'Brien"), True)

    print("%d checks, %d failed" % (checks, failed))
    return 1 if failed else 0


def _raises(fn, *a):
    try:
        fn(*a)
    except RuntimeError:
        return True
    return False


def main():
    if "--selftest" in sys.argv[1:]:
        return _selftest()
    import requests
    from robots_gate import RobotsGate
    session = requests.Session()
    gate = RobotsGate(session, UA)
    out = scrape(session, gate)
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    named = sum(1 for v in out.values() if v.get("members"))
    print("wrote %d county/counties (%d with a board) -> %s"
          % (len(out), named, OUT), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
