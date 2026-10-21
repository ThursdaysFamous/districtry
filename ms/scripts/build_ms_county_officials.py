#!/usr/bin/env python3
"""Build ms/data/app/ms-county-officials.json: the five supervisors and the
five election commissioners of every Mississippi county, by district, from the
Secretary of State's County Offices and Directory.

WHAT A MISSISSIPPI COUNTY ELECTS. Every one of the 82 counties is governed by
a board of five supervisors, each elected from a district; five counties
(Carroll, George, Jasper, Jones and Scott) print the district as a "Beat".
The County card names all five, and the label each county itself uses. Each
county also elects five election commissioners, numbered District 1 to 5 like
its supervisors. The directory's own description of the office (printed page
43 of the 2026 edition) requires each to be "A qualified elector of the
supervisor district in which election is sought" and gives their duties as
"conducting general and special elections, certifying election results, and
purging voter rolls". The County card names them too.

THE SOURCE. The Secretary of State publishes a County Offices and Directory
once a year as a PDF, linked from
https://www.sos.ms.gov/publications-external-affairs/publications/state-county-directory
as "County Offices and Directory_<year>.pdf". The builder reads that page,
takes the newest edition it links, and fails if it links none. The 2026
edition (92 pages, its own creation date 6 May 2026, SHA-256
22360b0f846d8cd93922a72fa900617ecab6d19180ff5027f082047af653e674, read
2026-10-15) names every county officer, including all 410 supervisors.

HOW THE PDF IS READ, measured on the 2026 edition:
  - A county begins on a page carrying its "Named for" line, and the 82 such
    pages run in alphabetical order. The county's own name is set as artwork
    on 80 of the 82 pages and is absent from the text, so the k-th such page
    is taken to be the k-th county alphabetically and held to that three ways:
    there must be exactly 82; where the text does print "<NAME> COUNTY"
    (Adams and Humphreys in 2026) it must agree; and the "Named for" line,
    which names the person or river the county is named for, must name the
    county on at least MIN_NAMED_FOR pages (68 of 82 in 2026) — a shift of
    one page would match almost none.
  - Harrison runs onto a second page headed "(CONTINUED)", and its
    supervisors are on that page, so a continuation page belongs to the
    county before it.
  - Each supervisor is one line, "District 1....Name....Address....Telephone"
    with runs of dots between the fields, followed by a fax line "(f) ...".
    Two lines join the name and the address with one or two dots instead of a
    run (Claiborne District 4, Simpson District 5), and the split falls before
    the address there. Copiah prints the board's number and then each
    supervisor's own cell number marked "(c)": the first is read for the
    board test below, and the second is the supervisor's own number.
  - A run of dots swallows the period of "Jr." and "Sr.", which is put back.
  - Every county must have exactly one supervisors block of five lines,
    districts 1 to 5, each with a name or the word "Vacant". The 2026 edition
    prints one vacant seat, Sunflower District 3, and the file carries it as
    {"district": "3", "vacant": true} rather than as a person called Vacant;
    more than MAX_VACANT is read as a broken parse.
  - Every county also has exactly one "Election Commissioners" heading, alone
    on its line in 66 counties and followed by a run of dots and a telephone
    in 16, and under it exactly five lines, "District 1" to "District 5" —
    "District" even in the five counties that call their supervisor
    districts beats — each running on from the name to an address and, on
    some, a telephone. One line (Wilkinson District 4) sets part of its run
    of dots as ellipsis characters, so a commissioner's line is cut at either.
    All 410 commissioners are named in 2026; a seat printed "Vacant" would be
    carried the way a supervisor's is.

WHAT IS CARRIED, AND WHAT NEVER IS. The directory prints an address and a
telephone beside every supervisor. In most counties all five print the same
one, which is the courthouse, the board's office or its post-office box; in
others each prints a different street address, which may be a home. So the
board's address is carried only where at least three of the five print the
same one, because five people do not share a home, and an address printed for
one supervisor alone is never carried. The board's telephone is found by the
same test. A supervisor's OWN number is carried on the supervisor: the number
the directory prints for that supervisor where it is not the board's, and
Copiah's "(c)" cell numbers, written "cell 601-953-9901" so the card says what
the directory says about them. Some of those are office extensions and some may
be a supervisor's own cell or home line; the directory does not say which, and
it prints them beside the name. Until 2026-10-17 no supervisor's own number
was carried, on the reasoning that it might be personal; that day Adam ruled
for the whole fleet, "if the official government source uses personal phone
numbers, we publish those." The ruling covers telephone numbers, so the
addresses are still left out. On 2026-10-15 the board test gave a board
address in 76 counties and a board telephone in 68, and on 2026-10-17 81
named supervisors had a number of their own.

For the election commissioners THE NAME AND THE COMMISSIONER'S OWN TELEPHONE
ARE KEPT, AND NEVER THE ADDRESS. Each commissioner's line runs on from the
name to the commissioner's own address, which may be a home, and on 45 lines
in nine counties of the 2026 edition to a telephone after it. The name is
everything before the line's first run of dots; the telephone is the line's
last field, kept only when that field is a telephone and nothing else; the
address between them is never kept, written or printed, not even in an error
message, so an error names only the county and the district. A name that
carries a digit, an @ or a post-office box is a line cut in the wrong place,
and the build stops rather than carry it. The telephone was left out as well
until Adam's ruling of 2026-10-17 above. The telephone 16 counties print after
the heading is still not carried: it is printed beside no one, and nothing on
the page says whose line it is.

NOTHING IN THE FILE CHANGES UNLESS THE PDF DOES. Each county carries the
edition, the PDF's own creation date and the page the county is on, and no
date of reading, so the weekly job opens a pull request only when the
Secretary of State publishes something different.

robots.txt: www.sos.ms.gov serves a Drupal default (2,027 bytes, read
2026-10-15) whose one `User-agent: *` group disallows Drupal's own paths
(/core/, /profiles/, /admin/, /user/ and the like) and nothing this builder
reads, and states no Crawl-delay. It is read through
scraper_common.require_robots_once before the first fetch, with the same
client the fetches send.

Usage:
    python3 ms/scripts/build_ms_county_officials.py            # fetch + write
    python3 ms/scripts/build_ms_county_officials.py --pdf FILE # read a saved copy
    python3 ms/scripts/build_ms_county_officials.py --check    # offline shape gate
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter
from urllib.parse import quote, urljoin

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
sys.path.insert(0, os.path.join(REPO, "scripts"))

from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

USER_AGENT = "districtry/1.0 (+https://districtry.com/ms/)"
INDEX_URL = ("https://www.sos.ms.gov/publications-external-affairs/"
             "publications/state-county-directory")
# The link text varies; the file name does not, so the edition is read from it.
PDF_LINK_RE = re.compile(
    r'href="([^"]*County(?:%20| )Offices(?:%20| )and(?:%20| )Directory_(\d{4})\.pdf)"',
    re.I)
SOURCE_TITLE = "County Offices and Directory"

OUT = os.path.join(INSTANCE, "data", "app", "ms-county-officials.json")
COUNTIES = os.path.join(INSTANCE, "data", "app", "state-counties.json")

EXPECTED_COUNTIES = 82
SEATS = 5
# How many "Named for" lines must name their county; 68 of 82 did in 2026.
# The other fourteen are named for a word or a place spelled differently
# ("Indian word meaning ...", "Granada, Spain").
MIN_NAMED_FOR = 62
# A board address or telephone needs this many of the five supervisors.
SHARED_BY = 3
# Floors on the board fields, measured 2026-10-15 at 76 and 68; a parse that
# stops finding them is a broken parse, not a directory that changed overnight.
MIN_BOARD_ADDRESS = 70
MIN_BOARD_PHONE = 58
# Seats the directory prints as "Vacant": one in the 2026 edition (Sunflower
# District 3). Many more than that is a parse reading the wrong column.
MAX_VACANT = 8
# Election commissioners named: all 410 in the 2026 edition, measured
# 2026-10-16. A parse that names far fewer has lost a county's block.
MIN_COMMISSIONERS = 400
# Floors on the people's own numbers, measured 2026-10-17 on the 2026 edition:
# 81 named supervisors carry a number that is not the board's (76, plus
# Copiah's five cell numbers), and 45 election commissioners print one. A parse that stops
# finding them has broken; a directory does not lose a third of them in a year.
MIN_SUPERVISOR_PHONES = 60
MIN_COMMISSIONER_PHONES = 30

FETCH_TIMEOUT = 120

LEADER = re.compile(r"\s*\.{2,}\s*")
# A commissioner's line is cut at a run of dots or of ellipsis characters.
COMMISSIONER_LEADER = re.compile(r"\s*(?:\.{2,}|\u2026+)\s*")
# What is left of a run of dots in a name that was cut in the wrong place.
LEADER_REMNANT_RE = re.compile(r"\.{2,}|\u2026")
ENTRY_RE = re.compile(r"^(District|Beat)\s*(\d+)\s*\.{2,}\s*(.*)$")
# A name run straight into its address by one or two dots (no leader run).
GLUED_RE = re.compile(r"^(.*?[A-Za-z])\.{1,2}((?:P\.\s?O\.|\d).*)$")
PHONE_RE = re.compile(r"^(\d{3})[-. ](\d{3})-(\d{4})")
# A supervisor's own cell number after the board's, as Copiah prints it:
# "601-894-1858/(c) 601-953-9901" (and once "(c) 601 953-9903").
CELL_RE = re.compile(r"\(c\)\s*(\d{3})[-. ]?(\d{3})-(\d{4})", re.I)
# A field that is a telephone and nothing else: the last field of an election
# commissioner's line, where the directory prints one after the address.
PHONE_ONLY_RE = re.compile(r"^(\d{3})[-. ](\d{3})-(\d{4})$")
# How every telephone in the file is written.
PHONE_SHAPE_RE = re.compile(r"^\d{3}-\d{3}-\d{4}$")
# A supervisor's own number, which may carry the directory's "(c)" as "cell ".
OWN_PHONE_SHAPE_RE = re.compile(r"^(?:cell )?\d{3}-\d{3}-\d{4}$")
# A line inside a supervisors block that belongs to the entry above it: a fax
# line, a stray period, or another number ("County Barn 662-...").
CONT_RE = re.compile(r"^(?:\(f\)|\.$|.*\b\d{3}-\d{4}\b)")
SUFFIX_RE = re.compile(r",\s*(Jr|Sr)$")
# A role printed after a commissioner's name: "Danny Glaskox, Chairman" in
# Jackson County's District 1, the one such line in the 2026 edition. The
# file carries names only, so the role is cut off rather than kept.
CHAIR_SUFFIX_RE = re.compile(r",\s*(?:Chairman|Chairwoman|Chairperson|Chair)\.?$", re.I)
# A role word at the end of a kept name, which the check refuses: the parse
# cut the name in the wrong place or a new edition prints a new role.
ROLE_WORD_RE = re.compile(r"\b(?:Chairman|Chairwoman|Chairperson|Chair|President|"
                          r"Secretary|Treasurer|Clerk)\.?$", re.I)
# The directory's word for a seat nobody holds.
VACANT_RE = re.compile(r"^vacant$", re.I)
# The commissioners' heading: alone, or followed by a run of dots and the
# telephone 16 counties print there, which is never read.
COMMISSIONERS_HEAD_RE = re.compile(r"^Election Commissioners(?:\s*\.{2,}.*)?$")
# What a name never carries and an address always does: a digit (a street
# number, a box number, a ZIP code), an @, or a post-office box.
NOT_A_NAME_RE = re.compile(r"\d|@|\bP\.\s?O\.", re.I)


def clean(s):
    return " ".join(str(s).replace(" ", " ").split())


def norm_address(a):
    return " ".join(a.lower().replace(",", " ").replace(".", " ").split())


# ---------------------------------------------------------------- fetching

def fetch(url, binary=False):
    import requests

    resp = requests.get(url, headers={"User-Agent": USER_AGENT},
                        timeout=FETCH_TIMEOUT)
    resp.raise_for_status()
    return resp.content if binary else resp.text


def newest_edition(index_html):
    found = {}
    for href, year in PDF_LINK_RE.findall(index_html):
        found[int(year)] = urljoin(INDEX_URL, href.replace(" ", "%20"))
    if not found:
        raise SystemExit(
            "build_ms_county_officials: the Secretary of State's directory page "
            "links no 'County Offices and Directory_<year>.pdf' — the page or "
            "the file name changed. Read %s before changing this builder."
            % INDEX_URL)
    year = max(found)
    return year, found[year]


# ---------------------------------------------------------------- parsing

def pdf_date(meta):
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})", (meta or {}).get("creationDate") or "")
    return "%s-%s-%s" % m.groups() if m else None


def county_pages(doc):
    """[(start page index, [page indexes])] for every county, in PDF order."""
    starts = []
    for i in range(doc.page_count):
        lines = doc[i].get_text().split("\n")
        if any(l.strip().startswith("Named for") for l in lines[:14]):
            starts.append((i, [i]))
        elif starts and any("(CONTINUED)" in l.upper() for l in lines[:6]):
            starts[-1][1].append(i)
    return starts


def named_for_text(lines):
    for k, l in enumerate(lines[:14]):
        if l.strip().startswith("Named for"):
            return clean(l + " " + (lines[k + 1] if k + 1 < len(lines) else ""))
    return ""


def printed_page(lines):
    for l in lines[:3]:
        if re.fullmatch(r"\d{1,3}", l.strip()):
            return int(l.strip())
    return None


def parse_entry(label, number, rest, where):
    parts = [p for p in LEADER.split(rest) if p.strip()]
    if len(parts) == 2:
        glued = GLUED_RE.match(parts[0])
        if glued:
            parts = [glued.group(1), glued.group(2), parts[1]]
    if len(parts) != 3:
        # The fields are not printed: a supervisor's own address and telephone
        # may be a home's, and a CI log is not where they belong.
        raise SystemExit("%s %s %s: expected a name, an address and a telephone "
                         "separated by runs of dots, and the line splits into %d "
                         "fields instead" % (where, label, number, len(parts)))
    name, address, phone = (clean(p) for p in parts)
    name = SUFFIX_RE.sub(lambda m: ", %s." % m.group(1), name)
    phone_m = PHONE_RE.match(phone.strip(" ."))
    cell_m = CELL_RE.search(phone)
    return {
        "district": str(int(number)),
        "name": name,
        "vacant": bool(VACANT_RE.match(name)),
        # Read for the shared-office test only; never written per supervisor.
        "_address": address.strip(" ."),
        # The board test reads this, and own_phone() keeps it on the
        # supervisor when it is not the board's.
        "_phone": "%s-%s-%s" % phone_m.groups() if phone_m else None,
        # Kept with the directory's own word for it, as "cell 601-953-9901".
        "_cell": "cell %s-%s-%s" % cell_m.groups() if cell_m else None,
    }


def own_phone(entry, board_phone):
    """The number the directory prints for this supervisor alone, or None.

    A cell number marked "(c)" is the supervisor's own wherever it appears.
    Otherwise the supervisor's number is their own only when it is not the
    board's, which the County card already shows in the board's office block,
    so one number is never printed six times."""
    if entry["_cell"]:
        return entry["_cell"]
    if entry["_phone"] and entry["_phone"] != board_phone:
        return entry["_phone"]
    return None


def supervisor_record(entry, board_phone):
    if entry["vacant"]:
        return {"district": entry["district"], "vacant": True}
    record = {"district": entry["district"], "name": entry["name"]}
    phone = own_phone(entry, board_phone)
    if phone:
        record["phone"] = phone
    return record


def supervisors_block(lines, where):
    """The one block of supervisor lines on a county's pages."""
    heads = [k for k, l in enumerate(lines) if l.strip() == "Supervisors"]
    if len(heads) != 1:
        raise SystemExit("%s: %d 'Supervisors' headings, expected exactly one"
                         % (where, len(heads)))
    entries = []
    labels = set()
    for raw in lines[heads[0] + 1:]:
        s = raw.strip()
        if not s:
            continue
        m = ENTRY_RE.match(s)
        if m:
            labels.add(m.group(1))
            entries.append(parse_entry(m.group(1), m.group(2), m.group(3), where))
            continue
        if entries and CONT_RE.match(s):
            continue
        break
    if len(labels) != 1:
        raise SystemExit("%s: supervisor lines labelled %s" % (where, sorted(labels)))
    districts = [e["district"] for e in entries]
    if districts != [str(n) for n in range(1, SEATS + 1)]:
        raise SystemExit("%s: supervisor districts read %s, expected 1 to %d"
                         % (where, districts, SEATS))
    for e in entries:
        if not e["vacant"] and not re.search(r"[A-Za-z]{2}", e["name"]):
            raise SystemExit("%s: supervisor district %s has no name"
                             % (where, e["district"]))
    return labels.pop(), entries


def commissioner_name(rest, where, number):
    """The name at the start of an election commissioner's line, and nothing
    else from it: the rest of the line is the commissioner's own address."""
    first = next((p for p in COMMISSIONER_LEADER.split(rest) if p.strip()), "")
    glued = GLUED_RE.match(first)
    if glued:
        first = glued.group(1)
    name = CHAIR_SUFFIX_RE.sub("", clean(first).strip(" ."))
    name = SUFFIX_RE.sub(lambda m: ", %s." % m.group(1), name)
    if NOT_A_NAME_RE.search(name) or LEADER_REMNANT_RE.search(name):
        raise SystemExit("%s: the election commissioner line for district %s does "
                         "not cut where a name ends: what would be kept carries a "
                         "digit, an @, a post-office box or a run of dots. Nothing "
                         "from the line is printed, because it carries an address."
                         % (where, number))
    if not VACANT_RE.match(name) and not re.search(r"[A-Za-z]{2}", name):
        raise SystemExit("%s: election commissioner district %s has no name"
                         % (where, number))
    return name


def commissioner_phone(rest):
    """The telephone at the end of an election commissioner's line, or None.

    Only a last field that is a telephone and nothing else is read. The
    commissioner's address sits between the name and the telephone, so it is
    never kept, and a line whose last field is the address carries no
    telephone."""
    parts = [p for p in COMMISSIONER_LEADER.split(rest) if p.strip()]
    if len(parts) < 2:
        return None
    m = PHONE_ONLY_RE.match(clean(parts[-1]).strip(" ."))
    return "%s-%s-%s" % m.groups() if m else None


def commissioners_block(lines, where):
    """The county's five election commissioners: district, name and, where the
    directory prints one after the address, the commissioner's telephone."""
    heads = [k for k, l in enumerate(lines) if COMMISSIONERS_HEAD_RE.match(l.strip())]
    if len(heads) != 1:
        raise SystemExit("%s: %d 'Election Commissioners' headings, expected exactly one"
                         % (where, len(heads)))
    entries = []
    labels = set()
    for raw in lines[heads[0] + 1:]:
        s = raw.strip()
        if not s:
            continue
        m = ENTRY_RE.match(s)
        if not m:
            break
        labels.add(m.group(1))
        name = commissioner_name(m.group(3), where, m.group(2))
        district = str(int(m.group(2)))
        if VACANT_RE.match(name):
            entries.append({"district": district, "vacant": True})
            continue
        entry = {"district": district, "name": name}
        phone = commissioner_phone(m.group(3))
        if phone:
            entry["phone"] = phone
        entries.append(entry)
    if len(labels) != 1:
        raise SystemExit("%s: election commissioner lines labelled %s"
                         % (where, sorted(labels)))
    districts = [e["district"] for e in entries]
    if districts != [str(n) for n in range(1, SEATS + 1)]:
        raise SystemExit("%s: election commissioner districts read %s, expected 1 to %d"
                         % (where, districts, SEATS))
    return labels.pop(), entries


def shared(values):
    """The value at least SHARED_BY entries print, or None."""
    counts = Counter(v for v in values if v)
    if not counts:
        return None
    value, n = counts.most_common(1)[0]
    return value if n >= SHARED_BY else None


def board_office(entries):
    by_norm = {}
    for e in entries:
        by_norm.setdefault(norm_address(e["_address"]), []).append(e["_address"])
    key = shared(norm_address(e["_address"]) for e in entries)
    address = Counter(by_norm[key]).most_common(1)[0][0] if key else None
    phone = shared(e["_phone"] for e in entries)
    return address, phone


def load_counties():
    with open(COUNTIES) as f:
        feats = json.load(f)["features"]
    out = []
    for feat in feats:
        p = feat["properties"]
        out.append((str(p["GEOID"]), p["NAME"], p["BASENAME"]))
    if len(out) != EXPECTED_COUNTIES:
        raise SystemExit("state-counties.json carries %d counties, expected %d"
                         % (len(out), EXPECTED_COUNTIES))
    return sorted(out, key=lambda c: c[2].lower())


def parse(pdf_bytes, pdf_url, edition):
    # Only the weekly read of the directory needs pymupdf, and
    # update-ms-county-officials.yml installs it; --check, which the smoke job
    # runs, never reaches this line, so the import is declared optional rather
    # than paid for by every pull request.
    try:
        import pymupdf
    except ImportError:
        raise RuntimeError("reading the directory needs pymupdf: "
                           "pip install -c scripts/requirements.txt pymupdf")

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    published = pdf_date(doc.metadata)
    counties = load_counties()
    groups = county_pages(doc)
    if len(groups) != EXPECTED_COUNTIES:
        raise SystemExit("found %d county start pages, expected %d"
                         % (len(groups), EXPECTED_COUNTIES))

    named_hits = []
    result = {}
    for (geoid, name, base), (start, pages) in zip(counties, groups):
        where = "%s (PDF page %d)" % (name, start + 1)
        lines = []
        for p in pages:
            lines += doc[p].get_text().split("\n")
        first = doc[start].get_text().split("\n")
        printed = [l.strip() for l in first[:8]
                   if re.fullmatch(r"[A-Z][A-Z .']+ COUNTY", l.strip())]
        if printed and printed[0] != name.upper():
            raise SystemExit("%s: the page prints %r — the pages are out of step "
                             "with the alphabetical county list" % (where, printed[0]))
        if re.search(r"\b%s\b" % re.escape(base.lower()), named_for_text(first).lower()):
            named_hits.append(name)
        label, entries = supervisors_block(lines, where)
        address, phone = board_office(entries)
        commissioner_label, commissioners = commissioners_block(lines, where)
        record = {
            "county": name,
            "label": label,
            "supervisors": [supervisor_record(e, phone) for e in entries],
            "commissionerLabel": commissioner_label,
            "electionCommissioners": commissioners,
        }
        if address:
            record["boardAddress"] = address
        if phone:
            record["boardPhone"] = phone
        record.update({
            "source": "the Mississippi Secretary of State's %s, %d edition"
                      % (SOURCE_TITLE, edition),
            "published": published,
            "sourceUrl": pdf_url,
            "sourcePage": start + 1,
        })
        page_no = printed_page(first)
        if page_no is not None:
            record["printedPage"] = page_no
        result[geoid] = record

    if len(named_hits) < MIN_NAMED_FOR:
        raise SystemExit(
            "only %d of %d 'Named for' lines name their county (floor %d) — the "
            "county pages are probably out of step with the alphabetical list"
            % (len(named_hits), EXPECTED_COUNTIES, MIN_NAMED_FOR))
    return result, published, len(named_hits)


# ---------------------------------------------------------------- gates

def check_shape(data):
    """Hold a built or shipped file to the shape the County card reads."""
    problems = []
    geoids = {c[0] for c in load_counties()}
    if set(data) != geoids:
        problems.append("county keys differ from state-counties.json: missing %s, extra %s"
                        % (sorted(geoids - set(data)), sorted(set(data) - geoids)))
    allowed = {"county", "label", "supervisors", "boardAddress", "boardPhone",
               "commissionerLabel", "electionCommissioners",
               "source", "published", "sourceUrl", "sourcePage", "printedPage"}
    addresses = phones = vacant = commissioners = commissioners_vacant = 0
    own_phones = commissioner_phones = 0
    for geoid, rec in sorted(data.items()):
        extra = set(rec) - allowed
        if extra:
            problems.append("%s carries unexpected fields %s" % (geoid, sorted(extra)))
        if rec.get("label") not in ("District", "Beat"):
            problems.append("%s: label %r" % (geoid, rec.get("label")))
        sups = rec.get("supervisors") or []
        if [s.get("district") for s in sups] != [str(n) for n in range(1, SEATS + 1)]:
            problems.append("%s: districts %s" % (geoid, [s.get("district") for s in sups]))
        for s in sups:
            if set(s) == {"district", "vacant"} and s.get("vacant") is True:
                vacant += 1
                continue
            # Field NAMES only: a record carrying more than a name and a
            # telephone may be carrying an address, which does not belong in a
            # log either.
            if set(s) - {"phone"} != {"district", "name"} or not s.get("name") \
                    or VACANT_RE.match(str(s.get("name"))):
                problems.append("%s supervisor district %s carries fields %s"
                                % (geoid, s.get("district"), sorted(s)))
            elif "phone" in s and not OWN_PHONE_SHAPE_RE.match(str(s["phone"])):
                problems.append("%s supervisor district %s: the telephone is not "
                                "written NNN-NNN-NNNN or cell NNN-NNN-NNNN (not printed)"
                                % (geoid, s.get("district")))
            elif "phone" in s and re.sub(r"\D", "", str(s["phone"])) == \
                    re.sub(r"\D", "", str(rec.get("boardPhone") or "")):
                problems.append("%s supervisor district %s carries the board's own "
                                "telephone, which the board's office block shows"
                                % (geoid, s.get("district")))
            elif LEADER_REMNANT_RE.search(str(s["name"])):
                problems.append("%s supervisor district %s: the name carries a run "
                                "of dots, so its line was cut in the wrong place "
                                "(not printed)" % (geoid, s.get("district")))
            elif ROLE_WORD_RE.search(str(s["name"])):
                problems.append("%s supervisor district %s: the name ends in a role "
                                "word (not printed)" % (geoid, s.get("district")))
            else:
                own_phones += "phone" in s
        if rec.get("commissionerLabel") not in ("District", "Beat"):
            problems.append("%s: election commissioner label %r"
                            % (geoid, rec.get("commissionerLabel")))
        coms = rec.get("electionCommissioners") or []
        if [c.get("district") for c in coms] != [str(n) for n in range(1, SEATS + 1)]:
            problems.append("%s: election commissioner districts %s"
                            % (geoid, [c.get("district") for c in coms]))
        for c in coms:
            if set(c) == {"district", "vacant"} and c.get("vacant") is True:
                commissioners_vacant += 1
                continue
            if set(c) - {"phone"} != {"district", "name"} or not c.get("name") \
                    or VACANT_RE.match(str(c.get("name"))):
                problems.append("%s election commissioner district %s carries "
                                "fields %s" % (geoid, c.get("district"), sorted(c)))
                continue
            if "phone" in c and not PHONE_SHAPE_RE.match(str(c["phone"])):
                problems.append("%s election commissioner district %s: the "
                                "telephone is not written NNN-NNN-NNNN (not printed)"
                                % (geoid, c.get("district")))
                continue
            if NOT_A_NAME_RE.search(str(c["name"])) or LEADER_REMNANT_RE.search(str(c["name"])):
                problems.append("%s election commissioner district %s: the name "
                                "carries a digit, an @, a post-office box or a run "
                                "of dots, so it may carry an address (not printed)"
                                % (geoid, c.get("district")))
                continue
            if ROLE_WORD_RE.search(str(c["name"])):
                problems.append("%s election commissioner district %s: the name "
                                "ends in a role word (not printed)"
                                % (geoid, c.get("district")))
                continue
            commissioners += 1
            commissioner_phones += "phone" in c
        if rec.get("boardPhone") and not re.fullmatch(r"\d{3}-\d{3}-\d{4}", rec["boardPhone"]):
            problems.append("%s: board telephone %r" % (geoid, rec["boardPhone"]))
        if not str(rec.get("sourceUrl", "")).startswith("https://www.sos.ms.gov/"):
            problems.append("%s: sourceUrl %r" % (geoid, rec.get("sourceUrl")))
        addresses += bool(rec.get("boardAddress"))
        phones += bool(rec.get("boardPhone"))
    if addresses < MIN_BOARD_ADDRESS:
        problems.append("only %d counties carry a board address (floor %d)"
                        % (addresses, MIN_BOARD_ADDRESS))
    if phones < MIN_BOARD_PHONE:
        problems.append("only %d counties carry a board telephone (floor %d)"
                        % (phones, MIN_BOARD_PHONE))
    if vacant > MAX_VACANT:
        problems.append("%d seats read as vacant (at most %d) — the parse is "
                        "probably reading the wrong column" % (vacant, MAX_VACANT))
    if commissioners < MIN_COMMISSIONERS:
        problems.append("only %d election commissioners named (floor %d)"
                        % (commissioners, MIN_COMMISSIONERS))
    if commissioners_vacant > MAX_VACANT:
        problems.append("%d election commissioner seats read as vacant (at most %d)"
                        % (commissioners_vacant, MAX_VACANT))
    if own_phones < MIN_SUPERVISOR_PHONES:
        problems.append("only %d supervisors carry a telephone of their own (floor %d)"
                        % (own_phones, MIN_SUPERVISOR_PHONES))
    if commissioner_phones < MIN_COMMISSIONER_PHONES:
        problems.append("only %d election commissioners carry a telephone (floor %d)"
                        % (commissioner_phones, MIN_COMMISSIONER_PHONES))
    return (problems, addresses, phones, vacant, commissioners, commissioners_vacant,
            own_phones, commissioner_phones)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pdf", help="read this saved copy of the directory instead of fetching")
    ap.add_argument("--edition", type=int, help="the edition year of --pdf (default: from its name)")
    ap.add_argument("--check", action="store_true",
                    help="hold the shipped file to its shape, offline, and write nothing")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    if args.check:
        with open(OUT) as f:
            data = json.load(f)
        (problems, addresses, phones, vacant, coms, coms_vacant, own_phones,
         com_phones) = check_shape(data)
        if problems:
            for p in problems:
                print("build_ms_county_officials --check: FAIL — " + p, file=sys.stderr)
            return 1
        print("build_ms_county_officials --check: OK — %d counties, %d supervisor "
              "seats (%d named, %d vacant, %d with a telephone of their own), a "
              "board address in %d and a board telephone in %d; %d election "
              "commissioners named (%d with a telephone) and %d vacant, no "
              "address but the board's"
              % (len(data), SEATS * len(data), SEATS * len(data) - vacant, vacant,
                 own_phones, addresses, phones, coms, com_phones, coms_vacant))
        return 0

    if args.pdf:
        with open(args.pdf, "rb") as f:
            pdf_bytes = f.read()
        m = re.search(r"(\d{4})", os.path.basename(args.pdf))
        edition = args.edition or (int(m.group(1)) if m else None)
        if not edition:
            raise SystemExit("--pdf needs --edition when the file name carries no year")
        # The address the Secretary of State publishes each edition under.
        pdf_url = ("https://www.sos.ms.gov/sites/default/files/publications/"
                   + quote("%s_%d.pdf" % (SOURCE_TITLE, edition)))
    else:
        require_robots_once(INDEX_URL, USER_AGENT, label="ms-build-ms-county-officials")
        edition, pdf_url = newest_edition(fetch(INDEX_URL))
        require_robots_once(pdf_url, USER_AGENT, label="ms-build-ms-county-officials")
        pdf_bytes = fetch(pdf_url, binary=True)

    sha = hashlib.sha256(pdf_bytes).hexdigest()
    data, published, named = parse(pdf_bytes, pdf_url, edition)
    (problems, addresses, phones, vacant, coms, coms_vacant, own_phones,
     com_phones) = check_shape(data)
    if problems:
        for p in problems:
            print("build_ms_county_officials: FAIL — " + p, file=sys.stderr)
        return 1

    payload = json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=out_dir, suffix=".json")
    with os.fdopen(fd, "w") as f:
        f.write(payload)
    os.chmod(tmp, 0o644)  # mkstemp makes it private; the app serves it
    os.replace(tmp, args.out)
    labels = Counter(r["label"] for r in data.values())
    vacancies = ["%s %s %s" % (r["county"], r["label"], s["district"])
                 for r in data.values() for s in r["supervisors"] if s.get("vacant")]
    print("build_ms_county_officials: %d counties, %d supervisor seats (%s) from "
          "the %d edition published %s, %s, SHA-256 %s; %d named and %d vacant "
          "(%s), %d with a telephone of their own; a board address in %d "
          "counties and a board telephone in %d; %d election commissioners "
          "named (%d with a telephone) and %d vacant; %d of %d 'Named for' "
          "lines name their county"
          % (len(data), SEATS * len(data),
             ", ".join("%d %s" % (n, l) for l, n in sorted(labels.items())),
             edition, published, pdf_url, sha, SEATS * len(data) - vacant, vacant,
             ", ".join(sorted(vacancies)) or "none", own_phones, addresses, phones,
             coms, com_phones, coms_vacant, named, EXPECTED_COUNTIES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
