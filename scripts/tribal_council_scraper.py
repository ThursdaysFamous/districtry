#!/usr/bin/env python3
"""
Read who sits on each Wisconsin and Michigan nation's council, from the nation.

THE AUTHORITY IS EACH NATION'S OWN PUBLISHED COUNCIL. The Bureau of Indian
Affairs' directory carries one leader per government and never a council, so
there is no federal list to read instead. This module reads one page per
nation (two for the Ho-Chunk Nation and the Little Traverse Bay Bands, whose
executive and legislative branches publish separately), with a parser written
for that page, and writes data/tribal-councils.json. scripts/build_tribal_areas.py
--rosters stamps it onto each instance's tribal-areas.json, offline.

ONE SECOND SOURCE, AND ONLY WHERE THE NATION PUBLISHES NOTHING. The Wisconsin
Department of Administration publishes "Wisconsin Tribal Head Officials", a
one-page PDF naming every Wisconsin nation's council (updated 8 July 2026 when
this was written). It is a government publisher, but it is a state's list of
another government's officials, and on 2026-10-06 it was already behind four
nations' own pages (Oneida's vice-chair and two council seats, two of
Stockbridge-Munsee's, and a Forest County Potawatomi suffix). So it is used for
exactly the two Wisconsin nations that publish no council at all: Lac du
Flambeau, whose recorded council address now serves its employment page and
whose site names no council anywhere this project could find, and Sokaogon,
whose whole navigation names none. The card says the names are the state's and
gives the state's own date. Michigan has no current equivalent (the state's
own directory is dated January 2017), so Michigan's unreadable councils stay
unnamed.

WHAT A PARSER MAY NOT DO. A parser returns exactly the seats its page states,
and `SEATS` pins how many that is: a page that loses a member, gains a staff
row, or changes shape fails the run rather than shipping a short or padded
council. Nothing is corrected. Two cases are carried as published with a note
rather than repaired:
  * Bad River's page spells its treasurer "Michelle Conners" in its current
    council block and "Michelle Connors" in the contact table below it, and the
    state's list says Connors. The council block is what ships, with the other
    spelling stated on the row, because choosing between a nation's two
    spellings of its own officer is not this project's call.
  * Stockbridge-Munsee prints one member as "JOE Miller". Casing is the
    nation's and ships unchanged.
Contact details ship only where the page pairs them with the person on the
same row, never from a table elsewhere on the page with a different date
(Bad River's contact table is headed "2021", so its numbers are not taken).

DISTRICTS. Some councils are elected by district — Ho-Chunk's four, the Sault
Tribe's five units, Gun Lake's three, Fond du Lac's three. Those are the
nation's MEMBERSHIP districts, not shapes this app draws, so a district is
carried as a word on the member's row and never as geometry. Saginaw Chippewa's
list and its own biographies disagree about one member's district (the list
says "District 3", the biography "At-Large District 2"), so no Saginaw
district is carried at all.

PRESERVE, NEVER DELETE (Adam's ruling, 2026-09-19). A nation whose page cannot
be read this week keeps its last-read council with the date it was last read,
which the card prints. A refusal stops the fetch and never unpublishes. A
nation that has never been read and fails is a failed run.

Every page is fetched only after its robots.txt is read with the same client,
through scraper_common.require_robots_once.

Usage:
    python3 scripts/tribal_council_scraper.py                 # fetch and write
    python3 scripts/tribal_council_scraper.py --from-dir DIR  # parse saved pages
    python3 scripts/tribal_council_scraper.py --selftest      # offline
"""

import argparse
import datetime
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "data", "tribal-councils.json")

WI_DOA_LIST = "https://doa.wi.gov/DIR/Tribal-Leaders.pdf"

# AIANNH code -> the pages read and the parser. `seats` is the exact number of
# members the page states today; see the module docstring.
NATIONS = {
    "0140": {"nation": "Bad River", "pages": ["https://www.badriver-nsn.gov/government/"], "seats": 7},
    "0170": {"nation": "Bay Mills", "pages": ["https://www.baymills.org/executive-council"], "seats": 5},
    "1125": {"nation": "Fond du Lac", "pages": ["https://www.fdlband.org/government/tribal_council.php"], "seats": 5},
    "1135": {"nation": "Forest County Potawatomi", "pages": ["https://www.fcpotawatomi.com/government/executive-council/"], "seats": 6},
    "1370": {"nation": "Grand Traverse", "pages": ["https://www.gtbindians.org/council_members.asp"], "seats": 7},
    "1450": {"nation": "Ho-Chunk", "pages": [
        "https://ho-chunknation.com/government/executive-branch/office-of-the-president/",
        "https://ho-chunknation.com/government/legislative-branch/"], "seats": 13},
    "1550": {"nation": "Nottawaseppi Huron", "pages": ["https://nhbp-nsn.gov/tribal-council/"], "seats": 5},
    "1610": {"nation": "Saginaw Chippewa", "pages": ["https://www.sagchip.org/council/councilprofiles.aspx"], "seats": 12},
    "1815": {"nation": "Lac Courte Oreilles", "pages": ["https://lco-nsn.gov/tribal-governing-board/"], "seats": 7},
    "1825": {"nation": "Lac du Flambeau", "pages": [WI_DOA_LIST], "seats": 12, "stateList": True},
    "1830": {"nation": "Lac Vieux Desert", "pages": ["https://lvd-nsn.gov/Content/Tribal-Council.cfm"], "seats": 9, "br": " "},
    "1963": {"nation": "Little Traverse Bay", "pages": [
        "https://ltbbodawa-nsn.gov/government/executive/tribal-chairman-tribal-vice-chairperson/",
        "https://ltbbodawa-nsn.gov/tribal-council-and-legislative-office/"], "seats": 11},
    "2150": {"nation": "Gun Lake", "pages": ["https://gunlaketribe-nsn.gov/about/tribal-council/"], "seats": 7},
    "2175": {"nation": "Menominee", "pages": ["https://www.menominee-nsn.gov/GovernmentPages/Legislature"], "seats": 9},
    "2560": {"nation": "Oneida", "pages": ["https://oneida-nsn.gov/government/business-committee/members/"], "seats": 9},
    "2890": {"nation": "Pokagon", "pages": ["https://www.pokagonband-nsn.gov/government/tribal-council/"], "seats": 11},
    "3085": {"nation": "Red Cliff", "pages": ["https://www.redcliff-nsn.gov/government/tribal_government/index.php"], "seats": 9},
    "3305": {"nation": "St. Croix", "pages": ["https://stcroixojibwe-nsn.gov/tribal-council/"], "seats": 5},
    "3635": {"nation": "Sault Ste. Marie", "pages": ["https://www.saulttribe.com/government/board-of-directors/29-government/board-of-directors/109-board-members-and-reports"], "seats": 13},
    "3885": {"nation": "Sokaogon", "pages": [WI_DOA_LIST], "seats": 6, "stateList": True},
    "4015": {"nation": "Stockbridge-Munsee", "pages": ["https://mohican-nsn.gov/tribal-council/"], "seats": 7},
}

_BLOCK = (r"(?:p|div|h[1-6]|li|ul|ol|td|th|tr|table|section|article|header|footer|"
          r"nav|figcaption|figure|dt|dd|dl|main|aside|option|select|form|button|"
          r"label|title|hr)")


def lines_of(body, br=" \n"):
    """Page text, one line per block element; inline tags join. A <br> ends a
    line by default, because Red Cliff separates its whole council with them,
    and a page that breaks one NAME across a <br> inside a heading (Lac Vieux
    Desert) says so with `"br": " "` in NATIONS."""
    t = re.sub(r"(?is)<(script|style|noscript|template)\b.*?</\1>", " ", body)
    t = re.sub(r"(?is)<!--.*?-->", " ", t)
    t = re.sub(r"(?i)<br\b[^>]*>", br, t)
    t = re.sub(r"(?i)</?%s\b[^>]*>" % _BLOCK, "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t).replace("\xa0", " ").replace("‑", "-")
    out = []
    for raw in t.split("\n"):
        line = re.sub(r"\s+", " ", raw).strip()
        if line:
            out.append(line)
    return out


def _after(lines, marker, nth=0):
    """The lines after the nth line equal to `marker` (exact, case-sensitive)."""
    hits = [i for i, l in enumerate(lines) if l == marker]
    if len(hits) <= nth:
        raise ValueError("marker %r not on the page" % marker)
    return lines[hits[nth] + 1:]


def _m(name, role, **extra):
    out = {"name": name.strip(), "role": role.strip()}
    for k, v in extra.items():
        if v:
            out[k] = v.strip()
    return out


def _email(line):
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", line or "")
    return m.group(0) if m else None


def _phone(line):
    m = re.search(r"\(?\d{3}\)?[-. ]\d{3}-\d{4}", line or "")
    return m.group(0) if m else None


def _sentence_roles(text, roles):
    """'Role A Name, Role B Name, and Role C Name' -> [(role, name)], roles
    matched longest first so 'Vice President' is never read as 'President'."""
    pat = "|".join(re.escape(r) for r in sorted(roles, key=len, reverse=True))
    text = text.strip()
    # a closing full stop ends the sentence, except where it ends a suffix
    if text.endswith(".") and not re.search(r"\b(?:Jr|Sr)\.$", text):
        text = text[:-1]
    parts = re.split(r",\s*(?:and\s+)?|\s+and\s+", text)
    out = []
    for part in parts:
        m = re.match(r"(%s)\s+(.+)$" % pat, part.strip())
        if not m:
            raise ValueError("cannot read a role in %r" % part)
        out.append((m.group(1), m.group(2)))
    return out


# ---- one parser per nation --------------------------------------------------

def p_bad_river(pages):
    # "Tribal Council" is also a menu entry; the council block opens on its
    # first office heading
    i0 = pages[0].index("TRIBAL CHAIRMAN")
    ls = pages[0][i0:]
    out = []
    for i in range(0, 14, 2):
        role, name = ls[i].title(), ls[i + 1]
        out.append(_m(name, role))
    for m in out:
        if m["name"] == "Michelle Conners":
            m["note"] = "the same page also spells it Connors"
    return out


def p_bay_mills(pages):
    line = [l for l in pages[0] if l.startswith("Serving on the council currently are ")][0]
    text = line[len("Serving on the council currently are "):]
    out = []
    for role, name in _sentence_roles(text, ["Vice President", "President", "Secretary",
                                             "Council Person", "Treasurer"]):
        # the page runs "AndyLeBlanc" together; the space is the page's own
        # missing one, restored only between a lowercase and a capital
        name = re.sub(r"^Andy(?=LeBlanc$)", "Andy ", name)
        out.append(_m(name, role))
    return out


def p_fond_du_lac(pages):
    ls = [l for l in _after(pages[0], "Fond du Lac Tribal Council Members")
          if l != "Email Link" and not l.startswith("(click")]
    out = []
    for line in ls[:5]:
        name, rest = line.split(" - ", 1)
        role = rest.split(" - ")[0]
        district = None
        m = re.search(r"District (I{1,3})", role)
        if m:
            district = "District " + m.group(1)
        role = re.sub(r"\s*&\s*District I{1,3} Representative", "", role)
        role = "District Representative" if role.startswith("District") else role
        out.append(_m(name, role, district=district))
    return out


def p_forest_county(pages):
    line = [l for l in pages[0] if l.startswith("From Left to Right: ")][0]
    text = line[len("From Left to Right: "):]
    return [_m(n, r) for r, n in _sentence_roles(
        text, ["Vice Chairman", "Chairman", "Secretary", "Treasurer", "Council Member"])]


def _role_then_name(ls, roles, count):
    out, i = [], 0
    while len(out) < count:
        if ls[i] in roles:
            out.append(_m(ls[i + 1], ls[i]))
            i += 2
        else:
            i += 1
    return out


def p_grand_traverse(pages):
    # the heading appears in the breadcrumb and again over the list; the list
    # is under the last one
    ls = _after(pages[0], "Tribal Council Members",
                nth=pages[0].count("Tribal Council Members") - 1)
    return _role_then_name(ls, {"Chairwoman", "Chairman", "Vice Chairwoman",
                                "Vice Chairman", "Treasurer", "Secretary", "Councilor"}, 7)


def p_ho_chunk(pages):
    pres = [l for l in pages[0] if l.startswith("Ho-Chunk Nation President: ")][0]
    out = [_m(pres[len("Ho-Chunk Nation President: "):], "President")]
    ls = _after(pages[1], "Legislators")
    district, i = None, 0
    while i < len(ls) and len(out) < 13:
        m = re.match(r"District (\d) Legislators$", ls[i])
        if m:
            district = "District " + m.group(1)
            i += 1
            continue
        if ls[i] in ("Representative", "Vice President"):
            out.append(_m(ls[i + 1], ls[i], district=district, email=_email(ls[i + 2])))
            i += 3
            continue
        i += 1
    return out


def p_nhbp(pages):
    pre = "The current NHBP Tribal Council consists of "
    line = [l for l in pages[0] if l.startswith(pre)][0]
    return [_m(n, r) for r, n in _sentence_roles(
        line[len(pre):], ["Vice Chairperson", "Chairperson", "Secretary", "Treasurer",
                          "Sergeant-at-Arms"])]


def p_saginaw(pages):
    # the heading is in the menu too; the list is under the last one
    ls = _after(pages[0], "Meet The Council", nth=pages[0].count("Meet The Council") - 1)
    out = []
    i = 0
    while len(out) < 12:
        name, label = ls[i], ls[i + 1]
        assert ls[i + 2] == "Read Bio", ls[i:i + 3]
        role = label.split(" / ")[0]
        if role.startswith("District"):
            role = "Council Member"
        # the list prints the office "Chaplin"; the same page's biography of
        # that member calls it "Tribal Chaplain", which is the office's name
        if role == "Chaplin" and "Tribal Chaplain" in " ".join(ls):
            role = "Chaplain"
        out.append(_m(name, role))
        i += 3
    return out


def p_lco(pages):
    i = [k for k, l in enumerate(pages[0]) if re.match(r"Gary .Little Guy. Clause, Chair$", l)][0]
    out = []
    for line in pages[0][i:i + 7]:
        name, role = line.rsplit(", ", 1)
        out.append(_m(name, role))
    return out


def _state_list(pdf_bytes, heading, count):
    """One nation's block of the Wisconsin Department of Administration's list:
    officer lines read "Name, Role", then "Council Members:" and a comma-run of
    names that wraps across lines."""
    # Only the weekly read of the state's PDF needs pymupdf, and
    # update-tribal-councils.yml installs it; --selftest, which the smoke job
    # runs, never reaches this line, so the import is declared optional rather
    # than paid for by every pull request.
    try:
        import pymupdf
    except ImportError:
        raise RuntimeError("reading the state's list needs pymupdf: "
                           "pip install -c scripts/requirements.txt pymupdf")
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    text = "\n".join(p.get_text() for p in doc)
    m = re.search(r"Updated:\s*([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    if not m:
        raise ValueError("the state list prints no Updated date")
    updated = datetime.datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat()
    lines = [re.sub(r"\s+", " ", l).strip() for l in text.split("\n")]
    start = [k for k, l in enumerate(lines) if l.startswith(heading)][0]
    out, rest, members = [], [], False
    for line in lines[start + 1:]:
        if line.startswith("Location:"):
            break
        if line == "Council Members:":
            members = True
            continue
        if members:
            rest.append(line)
            continue
        m = re.match(r"(.+?), ((?:Tribal )?(?:Vice[- ])?(?:Chair|President)|Secretary|"
                     r"Treasurer|Council Member I+)$", line)
        if m:
            out.append(_m(m.group(1), m.group(2)))
    if rest:
        for name in re.split(r",\s*", " ".join(rest).strip(" ,")):
            out.append(_m(name, "Council Member"))
    if len(out) != count:
        raise ValueError("the state list gives %d for %r, expected %d: %r"
                         % (len(out), heading, count, out))
    return out, updated


def p_lvd(pages):
    ls = _after(pages[0], "2024 - 2026")
    out = [_m(ls[k], ls[k + 1]) for k in range(0, 8, 2)]
    rest = _after(pages[0], "TRIBAL COUNCIL MEMBERS")
    assert rest[0].startswith("2024"), rest[0]
    out += [_m(n, "Council Member") for n in rest[1:6]]
    return out


def p_ltbb(pages):
    out = []
    for role in ("Tribal Chairperson", "Vice Chairperson"):
        line = [l for l in pages[0] if l.startswith(role + ": ")][0]
        out.append(_m(line[len(role) + 2:], role))
    ls = _after(pages[1], "Term Expires")
    i = 0
    while len(out) < 11:
        label = ls[i]
        if label.startswith(("Legislative Leader", "Tribal Secretary", "Tribal Treasurer",
                             "Tribal Council")):
            role = label.split(":")[0]
            role = "Council Member" if role == "Tribal Council" else role
            # two office labels carry a link to the statute that defines the
            # office, which lands on a line of its own before the name
            if re.match(r"(?:WOS )?\d{4}-\d{3} ", ls[i + 1]):
                i += 1
            out.append(_m(ls[i + 1], role, phone=_phone(ls[i + 2]), email=_email(ls[i + 3]),
                          termEnds=ls[i + 4] if re.match(r"20\d\d$", ls[i + 4]) else None))
            i += 5
        else:
            i += 1
    return out


def p_gun_lake(pages):
    # each member's line is followed by the district they were elected from
    ls, out = pages[0], []
    for k, line in enumerate(ls):
        m = re.match(r"([A-Z][A-Za-z.' -]+), (Tribal Chairwoman|Tribal Chairman|Vice Chairman|"
                     r"Vice Chairwoman|Secretary|Treasurer|Councilor)$", line)
        if m:
            nxt = ls[k + 1] if k + 1 < len(ls) else ""
            district = nxt if re.match(r"(At-Large|Bradley|Salem) District$", nxt) else None
            if not district:
                raise ValueError("no district under %r" % line)
            out.append(_m(m.group(1), m.group(2).replace("Tribal ", ""), district=district))
    return out


def p_menominee(pages):
    line = [l for l in pages[0] if l.startswith("(left-right) ")][0]
    text = line[len("(left-right) "):]
    out = []
    for part in re.split(r",\s*(?:and\s+)?", text.rstrip(".")):
        m = re.match(r"(.+?)(?: \((.+)\))?$", part.strip())
        role = m.group(2) or "Legislator"
        out.append(_m(m.group(1), role))
    return out


def p_oneida(pages):
    ls = _after(pages[0], "Officers")
    roles = {"Chairperson", "Vice-Chairperson", "Tribal Secretary", "Treasurer", "Council Member"}
    out, i = [], 0
    while len(out) < 9:
        if ls[i] in roles:
            out.append(_m(ls[i + 1], ls[i], phone=_phone(ls[i + 2]), email=_email(ls[i + 3])))
            i += 4
        else:
            i += 1
    return out


def p_pokagon(pages):
    out = []
    for line in _after(pages[0], "Tribal Council Executive Committee Members"):
        if line == "Administrative Staff":
            break
        if line == "Tribal Council Members At Large":
            continue
        name, _, role = line.partition(", ")
        out.append(_m(name, role or "Member At Large"))
    return out


def p_red_cliff(pages):
    ls = pages[0]
    start = ls.index([l for l in ls if re.match(r"20\d\d-\d\d Tribal Council$", l)][0])
    out = []
    for line in ls[start + 1:start + 10]:
        name, role = line.split(" - ", 1)
        if role.startswith("At Large Member, serving the remainder"):
            role = "At Large Member"
        out.append(_m(name, role))
    # the e-mail below each name, where the page prints one
    for k, line in enumerate(ls):
        for m in out:
            if line == m["name"] and k + 3 < len(ls) and ls[k + 1].startswith("Term Expires"):
                e = _email(ls[k + 2])
                if e:
                    m["email"] = e
                m["termEnds"] = ls[k + 1][len("Term Expires "):]
    return out


def p_st_croix(pages):
    ls = _after(pages[0], "Tribal Council Members")
    out = []
    i = 0
    while len(out) < 5:
        if ls[i].endswith(", Tribal Council"):
            out.append(_m(ls[i - 1], ls[i][:-len(", Tribal Council")]))
        i += 1
    return out


def p_sault(pages):
    out = []
    ls = pages[0]
    for k, line in enumerate(ls):
        m = re.match(r"(.+?), (Chairman|Vice-Chairman|Secretary|Treasurer|Director)$", line)
        if not m:
            continue
        unit = ls[k + 1] if re.match(r"Unit [IV]+$", ls[k + 1]) else None
        contact = ls[k + 2] if unit else ls[k + 1]
        out.append(_m(m.group(1), m.group(2), district=unit, phone=_phone(contact)))
    return out


def p_stockbridge(pages):
    ls = _after(pages[0], "Current Tribal Council")
    return [_m(ls[k], ls[k + 1]) for k in range(0, 14, 2)]


PARSERS = {
    "0140": p_bad_river, "0170": p_bay_mills, "1125": p_fond_du_lac,
    "1135": p_forest_county, "1370": p_grand_traverse, "1450": p_ho_chunk,
    "1550": p_nhbp, "1610": p_saginaw, "1815": p_lco, "1830": p_lvd,
    "1963": p_ltbb, "2150": p_gun_lake, "2175": p_menominee, "2560": p_oneida,
    "2890": p_pokagon, "3085": p_red_cliff, "3305": p_st_croix, "3635": p_sault,
    "4015": p_stockbridge,
}
STATE_LIST_HEADINGS = {"1825": "Lac du Flambeau Band of Lake", "3885": "Sokaogon Chippewa Community"}

_ROLE_OK = re.compile(r"(chair|president|chief|secretary|treasurer|member|representative|"
                      r"director|legislator|councilor|council|sergeant|chaplain|leader)", re.I)
_ROLE_WORDS = re.compile(r"^(chair|vice|secretary|treasurer|council|member|president|"
                         r"representative|director|legislator|councilor)\b", re.I)


def validate(code, members):
    want = NATIONS[code]["seats"]
    if len(members) != want:
        raise ValueError("%s: read %d member(s), the page states %d"
                         % (NATIONS[code]["nation"], len(members), want))
    names = [m["name"] for m in members]
    if len(set(names)) != len(names):
        raise ValueError("%s: a name appears twice: %r" % (NATIONS[code]["nation"], names))
    for m in members:
        if (not m["name"] or _ROLE_WORDS.match(m["name"]) or len(m["name"]) > 60
                or re.search(r"[\d@&/]", m["name"]) or len(m["name"].split()) < 2):
            raise ValueError("%s: %r is not a name" % (NATIONS[code]["nation"], m["name"]))
        if not m["role"] or not _ROLE_OK.search(m["role"]):
            # a role this module does not recognise as an office is the
            # cheapest sign a parser has walked off its block into a menu
            raise ValueError("%s: %r is not an office (for %r)"
                             % (NATIONS[code]["nation"], m["role"], m["name"]))
    return members


def fetch_page(url):
    import scraper_common as S
    S.require_robots_once(url, S.UA_ROSTER_BOT, headers=S.UA_HEADERS_ROSTER_BOT,
                          label="tribal-councils")
    resp = S.fetch(url, S.UA_HEADERS_ROSTER_BOT, timeout=40, attempts=3)
    return resp.content


def run(from_dir=None, today=None):
    today = today or datetime.date.today().isoformat()
    prior = {}
    if os.path.exists(OUT):
        prior = json.load(open(OUT)).get("councils", {})
    cache = {}

    def get(url, key):
        if url not in cache:
            if from_dir:
                path = os.path.join(from_dir, key)
                cache[url] = open(path, "rb").read()
            else:
                cache[url] = fetch_page(url)
        return cache[url]

    councils, failed = {}, []
    for code in sorted(NATIONS):
        spec = NATIONS[code]
        try:
            if spec.get("stateList"):
                members, updated = _state_list(get(WI_DOA_LIST, "wi-doa.pdf"),
                                               STATE_LIST_HEADINGS[code], spec["seats"])
                rec = {"source": "state-list",
                       "publisher": "Wisconsin Department of Administration",
                       "page": WI_DOA_LIST, "listUpdated": updated}
            else:
                pages = [lines_of(get(u, "%s-%d.html" % (code, k)).decode("utf-8", "replace"),
                                  spec.get("br", "\n"))
                         for k, u in enumerate(spec["pages"])]
                members = PARSERS[code](pages)
                rec = {"source": "nation", "page": spec["pages"][-1],
                       "pages": spec["pages"]}
            rec["members"] = validate(code, members)
            rec["read"] = today
            councils[code] = rec
            print("tribal-councils: %s %-26s %2d member(s) from %s"
                  % (code, spec["nation"], len(members), rec["page"]))
        except Exception as exc:  # noqa: BLE001 — one nation never stops the rest
            if code in prior:
                councils[code] = dict(prior[code], carriedFrom=prior[code].get("read"))
                print("tribal-councils: %s %s NOT READ this run (%s); carrying the "
                      "council last read %s" % (code, spec["nation"], exc,
                                                prior[code].get("read")))
            else:
                failed.append("%s %s: %s" % (code, spec["nation"], exc))
    if failed:
        raise SystemExit("tribal-councils: never read and not readable now:\n  "
                         + "\n  ".join(failed))
    doc = {"note": "Who sits on each Wisconsin and Michigan nation's council, read "
                   "by scripts/tribal_council_scraper.py. Stamped onto the cards by "
                   "scripts/build_tribal_areas.py --rosters.",
           "councils": councils}
    with open(OUT, "w") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("tribal-councils: OK — %d council(s) written to %s" % (len(councils), OUT))
    return doc


def selftest():
    assert lines_of("<h3>Samuel<br>Klingman</h3><p>Vice Chairman</p>", " ") == ["Samuel Klingman", "Vice Chairman"]
    assert lines_of("Nicole Boyd - Chair<br>Misty Nordin - Vice Chair") == ["Nicole Boyd - Chair", "Misty Nordin - Vice Chair"]
    assert lines_of("<p>906‑632‑6453</p>") == ["906-632-6453"]
    assert _sentence_roles("Vice President Andy LeBlanc, President Whitney Gravelle, "
                           "and Treasurer Audrey Breakie.",
                           ["Vice President", "President", "Treasurer"]) == [
        ("Vice President", "Andy LeBlanc"), ("President", "Whitney Gravelle"),
        ("Treasurer", "Audrey Breakie")]
    try:
        _sentence_roles("Chef Somebody", ["President"])
    except ValueError:
        pass
    else:
        raise AssertionError("an unknown role must fail")
    assert _sentence_roles("Treasurer Joseph Daniels Sr., and Council Member Herb Daniels Jr.",
                           ["Treasurer", "Council Member"])[-1] == ("Council Member", "Herb Daniels Jr.")
    assert _phone("920-869-4420") == "920-869-4420" and _phone("none") is None
    assert _email("x thill7@oneidanation.org y") == "thill7@oneidanation.org"
    NATIONS["9999"] = {"nation": "Test", "seats": 2}
    try:
        for bad in ([_m("A B", "Chair")],
                    [_m("A B", "Chair"), _m("A B", "Secretary")],
                    [_m("A B", "Chair"), _m("Council Member", "Secretary")],
                    [_m("Veterans", "Tribal Council Meeting Login"), _m("C D", "Law Library")],
                    [_m("A B", "Chair"), _m("WOS 2012-017 Tribal Secretary", "Secretary")]):
            try:
                validate("9999", bad)
            except ValueError:
                continue
            raise AssertionError("validate passed %r" % bad)
        assert validate("9999", [_m("A B", "Chair"), _m("C D", "Secretary")])
    finally:
        del NATIONS["9999"]
    assert set(PARSERS) | set(STATE_LIST_HEADINGS) == set(NATIONS)
    print("tribal-council-scraper --selftest: OK — %d nation(s), %d parser(s), "
          "%d from the state list" % (len(NATIONS), len(PARSERS), len(STATE_LIST_HEADINGS)))
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--from-dir")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return 0 if selftest() else 1
    run(args.from_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
