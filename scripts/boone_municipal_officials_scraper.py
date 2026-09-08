#!/usr/bin/env python3
"""
Scrape Boone County's clerk Year Book into the payload
build_municipal_officials_roster.py consumes.

SOURCE. The County Clerk & Recorder publishes an annual "Boone County,
Illinois Year Book" — a 70-page booklet whose "COUNTY OF BOONE –
CITY/VILLAGE OFFICIALS" section carries every one of the county's five
incorporated places with its FULL governing body: head of government, clerk,
treasurer, and every trustee or ward alderperson, plus the hall address,
phone and website, and the year each elected seat's term expires. That is
Cook/Will/DeKalb depth from one county document, so Boone joins as a
full-governing-body county rather than a mayor-level one. Belvidere is the
county's one ward-electing city — ten alderpersons, two per ward across five
wards, terms staggered so each ward has one seat up every two years.

WHY THIS SOURCE AND NOT THE COUNTY'S WEB PAGES. Boone publishes its county
board on a CMS page (scripts/boone_county_board_scraper.py reads it) but
publishes nothing municipal on the web at all: the five villages' and city's
officers exist in county-published form only inside this booklet. Belvidere's
ten alderpersons are the one exception — the county GIS serves them on the
Belvidere_Wards layer the app already reads — and that overlap is used below
as a CROSS-CHECK rather than as a second source.

FETCH POSTURE: open. Plain `requests` with a browser UA gets the index page
and the PDF. The PDF link 302s to the county's Revize CDN; redirects are
followed and the bytes are checked for a %PDF header before parsing.

EDITION DISCOVERY IS BY LINK TEXT, NOT BY FILENAME, and this is the one place
this county will punish a copied scraper. The index page lists every edition
back to 2019, and THE FILENAMES LIE: the 2024 edition is served as
"BCC-2022 Yearbook-2024 Final 08272024.pdf" and the 2023 edition as
"BCC-2022 Yearbook-Oct19_2023.pdf" — both still carrying the 2022 file stem.
Worse, the newest file is "BCC 2026 Yearbook Final 7.7.26.pdf" with a SPACE
where every older one has a hyphen, so a lexical sort of filenames (the
Grundy/Logan trick) puts "BCC-2025 …" last and silently pins the scraper to
last year's book. The anchor TEXT is the county's own edition label ("2026
Yearbook", "2025 Yearbook", …), so the highest year in the link text wins.
INDEX_PAGE below is the current index in spite of its `2019_` slug — the CMS
never renamed the page — and YEARBOOK_URL is the pinned FALLBACK, used only
when the index page cannot be read or carries no dated link.

WHY A WORD-POSITION READ (pdfplumber, not pypdf). Belvidere's ALDERPERSONS
block prints the ward label in its own text column, and each label shares its
BASELINE with the FIRST of that ward's two members — nothing but that shared y
ties a ward to a person. Measured on both the 2025 and 2026 editions, a
flattened extraction happens to emit each label just ahead of its member, so a
line parser would appear to work; this parser does not rely on that, because
"appears to work" is how a ward gets silently attached to the wrong
alderperson the first time a label drifts a fraction of a point off its row.
Rows are rebuilt from word coordinates, the ward label is lifted off the front
of its row, and the assignment is then CROSS-CHECKED against the county's own
Belvidere_Wards service (below).

WHAT THE COORDINATES ARE AND ARE NOT USED FOR, because the obvious first draft
of this was wrong. ABSOLUTE x THRESHOLDS ARE EDITION-SPECIFIC IN THIS BOOKLET:
the 2025 edition's page is 252 x 457 pt with the ward labels at x≈27.0 and the
member rows at x≈58.0, and the 2026 edition is the same page rescaled to
297 x 684 with those columns at x≈49.4 and x≈80.4. A threshold measured on
2026 puts BOTH of 2025's columns on the same side of the line and glues
"First:" onto a person's name — which is a real regression this scraper was
caught committing against last year's book before the rule changed. The gap
between label and member is no better a key: it is a tab stop, so it ranges
from 5.1 to 14.1 pt with the length of the label. What is stable across both
editions, to within a twentieth of a point, is that all ten member rows start
at the SAME x while every ward label starts left of it. So the label is found
by CONTENT and the column is proven by ANCHOR AGREEMENT — a member landing off
that anchor, or a label overlapping it, is a warning naming both coordinates.

EVERY OTHER DECISION IS BY CONTENT, NOT BY GEOMETRY, and deliberately so:
the booklet's own indentation is not reliable (Caledonia's sixth trustee,
Rhonda Moore, starts at the caption column x≈49.4 while the other five sit at
x≈61.7, and her dot leaders are a mix of '.' and U+2026). So a row is
classified by what it contains — leaders plus a term year make a member row,
leaders plus a title make an appointed-staff row, everything else is contact
— and the x coordinates are used for the one thing content cannot settle.

*** HOME ADDRESSES ARE PRINTED THROUGHOUT AND NEVER SHIP. ***
The booklet prints a RESIDENCE under almost every official — 54 of this
section's lines open with a street number, and 40 of those are somebody's
home (the other 14 are the six municipalities' own hall addresses, seven page
numbers and one bare hall phone) — exactly as Madison's and Peoria's sources
do, and exactly as this project has always refused to publish. The refusal is
STRUCTURAL, not a blocklist: the only street address a record can ever carry
is `office_address`, and the only lines that can set it are the hall-header
lines between a municipality's own "X CITY/VILLAGE OFFICERS" banner and its
first office caption (Belvidere City Hall at 401 Whitney Blvd., Capron at 250
W. Main Street, Poplar Grove at 200 N. Hill St., Timberlane at 2940 Charleston
Ct.; Caledonia's block prints no address at all and therefore ships none).
From every OTHER line the parser takes nothing but a regex-matched phone
number and a regex-matched e-mail address — the line itself is discarded
unread. Three assertions then prove the property on the built payload rather
than trusting the parser: no `name` or `office` may contain a digit, an '@' or
a street-suffix token; no street-shaped text may appear anywhere in the
payload once the hall addresses are blanked out; and the residence detector
must have SEEN at least MIN_RESIDENCE_LINES residences, because a guard that
finds nothing to guard against proves nothing. Any of the three failing is
fatal — this refuses to write rather than ship one home address.

PER-PERSON PHONES AND E-MAILS DO SHIP, and the distinction is not arbitrary.
The phone printed beside an officer's residence is the contact number the
county publishes FOR THAT OFFICE — for Belvidere's ten alderpersons the same
numbers are already on this app's ward card, served from the county's own
Belvidere_Wards GIS layer — and the e-mails are official
(@belvidereil.gov, @villageofpoplargrove.com, …). Both are lifted by regex
from lines whose remaining text is thrown away. A "direct" number that merely
repeats the hall's main line is dropped, per the fleet rule.

THE WARD CROSS-CHECK (on by default, `--no-cross-check` to skip, fail-open).
The county GIS serves ward_num / ald_1 / ald_2 / phone_1 / phone_2 for all
five Belvidere wards. After parsing, each shipped alderperson is looked up
there by name: a ward disagreement or a name the service does not know is a
loud WARN (the yearbook stays the roster of record — this never rewrites a
ward), and a PHONE disagreement drops the phone. If the service is
unreachable the run says so and ships the yearbook unchanged; a verification
that can take the whole scrape down with it is worse than no verification.

ONE PHONE IS OMITTED TODAY, and it is omitted rather than picked. The
yearbook gives Ward 3's Sandra Gramkowski 815-289-0493; the county's own ward
service gives 815-298-0493. One of the two transposed a digit, and NOTHING IN
EITHER SOURCE SETTLES WHICH: both exchanges are real in Belvidere and both
appear elsewhere in these same two files (289 on Jerry Hoiness, 298 on Mike
McGee). A wrong direct number sends a resident to a stranger's phone, which is
worse than a card with no number on it — and her official e-mail still ships,
so the card is not left contactless. The cross-check above finds this
disagreement itself, so nothing about it is hand-recorded and it retires
itself the day either publisher fixes the digit.

DELIBERATELY NOT COLLECTED — CHERRY VALLEY AND LOVES PARK. The booklet prints
both between Capron and Poplar Grove, and it is entitled to: both municipal
boundaries cross the county line (Census 2020 lists both under Boone as well
as Winnebago), so the Boone Clerk is an election authority for part of each.
They are still not taken, because the app resolves a municipality to ONE
county source and Winnebago is already that source for both, more deeply:
Winnebago publishes all TEN of Loves Park's ward alderpersons where this
booklet prints only its mayor, clerk and treasurer, and it publishes the same
Cherry Valley president and six trustees this booklet does. Shipping Boone's
copies would add nothing, would put two municipalities into a cross-county
contest settled by list position rather than by evidence, and would print a
"listed by both" NOTE on every build. If Boone's listing ever goes deeper than
Winnebago's, the answer is a COUNTY_PRECEDENCE decision made on the record,
not a quiet second source. A municipality header that is in neither list is a
loud WARN and is not shipped — a newly incorporated place gets a human, never
a silent drop.

ALSO NOT COLLECTED — BELVIDERE'S DEPARTMENT HEADS. The city's page prints
eleven appointed officers (City Attorney, Budget & Finance Officer, Police and
Fire Chiefs, Director of Public Works, Community Development Planner,
Administrative Assistant, Director of Buildings, Plumbing and Electrical
Inspectors, the Fire & Police Commission), and Poplar Grove prints two. The
card is the governing body, not the org chart — the Logan rule. Poplar
Grove's Village DEPUTY CLERK and the appointed Treasurers do ship, with
appointed=True, because those are municipal officers the builder already
classifies; a staff title outside the recognised department vocabulary is a
WARN rather than a silent skip, so the day Boone prints an Administrator this
run says so.

ROWS THE PARSER DROPS, all counted and printed, never silent:
  * Capron's Village Treasurer, published as "Vacant" — a vacancy is not an
    officeholder.
  * Capron's first Trustee row, a bare "Vacant" with no year.
  * A name that appears both as head of government and on the board (none in
    this edition; kept as a guard, the DeKalb rule).

ONE NAME SHIPS THAT IS PROBABLY NOT A PERSON: Poplar Grove's Village
Treasurer is published as "Sikich" — the accounting firm the village
contracts the office to. It ships as published, with appointed=True and a
WARN, because the village's treasurer of record genuinely is that firm and
inventing a human's name would be the actual dishonesty. Any single-token
name warns for the same reason.

WHAT WOULD BREAK THIS: the Clerk renaming the section banner or the
"FIRE PROTECTION DISTRICT" heading that bounds it; a municipality banner in
a form other than "<NAME> CITY|VILLAGE OFFICERS"; the ward column merging into
the member column (the anchor check warns, the cross-check fires, and
MIN_WARDS fails before anything is written); the index page dropping its dated
link text (the pinned fallback then serves, one edition behind, with a WARN).
Re-verify against the PREVIOUS edition after any change to the row assembly —
`--pdf <last year's book> --no-cross-check` must still produce the same five
municipalities and ten warded seats, and it is the check that caught the
absolute-x mistake above.

Usage:
    python3 boone_municipal_officials_scraper.py --out boone_municipal_officials.json
    python3 boone_municipal_officials_scraper.py --out out.json --pdf local.pdf
    python3 boone_municipal_officials_scraper.py --out out.json --no-cross-check
"""

import argparse
import datetime
import html as html_mod
import io
import json
import re
import sys
import urllib.parse

import requests
from arcgis_error import raise_for_arcgis_error
from scraper_common import UA_CHROME_WIN_126  # noqa: E402  (shared machinery — do not fork)

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

INDEX_PAGE = ("https://www.boonecountyil.gov/government/departments/"
              "clerk___recorder/2019_boone_county_illinois_year_book.php")
# Fallback ONLY — the live edition is discovered from INDEX_PAGE's link text
# (see the module docstring; the filenames are not a reliable edition key).
YEARBOOK_URL = ("https://www.boonecountyil.gov/Departments/Clerk-Recorder/"
                "BCC%202026%20Yearbook%20Final%207.7.26.pdf")
# The county's own ward layer, the same URL index.html reads as
# BELVIDERE_WARD_SERVICE. Used to cross-check the ward column, never as a
# source of record.
BELVIDERE_WARD_SERVICE = ("https://maps.boonecountyil.org/arcgis/rest/services/"
                          "Clerk_and_Recorder/Belvidere_Wards/MapServer/0")

HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
}
REQUEST_TIMEOUT = 120

# <a href= "Departments/…/BCC 2026 Yearbook Final 7.7.26.pdf?t=…">2026 Yearbook</a>
# The CMS writes `href= "…"` with a space after the equals, and the hrefs are
# resolved against the page's own <base href>.
YEARBOOK_LINK_RE = re.compile(
    r'<a\s+href=\s*"([^"]*\.pdf[^"]*)"[^>]*>\s*((?:19|20)\d{2})\s+Year\s*book\s*</a>',
    re.I)
BASE_HREF_RE = re.compile(r'<base\s+href=\s*"([^"]+)"', re.I)

# ---------------------------------------------------------------------------
# Section bounds and municipality banners.
SECTION_START_RE = re.compile(r"^COUNTY OF BOONE\s*[–—-]\s*CITY/VILLAGE OFFICIALS$", re.I)
SECTION_END_RE = re.compile(r"^FIRE PROTECTION DISTRICT$", re.I)
MUNI_BANNER_RE = re.compile(r"^([A-Z][A-Z .'&-]+?)\s+(CITY|VILLAGE)\s+OFFICERS$")
# "City of Belvidere cont." / "Caledonia Village cont." — a page continuation,
# not a caption. The municipality context persists across pages regardless.
MUNI_CONT_RE = re.compile(
    r"^(?:(?:City|Village|Town)\s+of\s+.+|.+\s+(?:City|Village|Town))\s+cont\.?$", re.I)
PAGE_NUMBER_RE = re.compile(r"^\d{1,3}$")

# The five incorporated places of Boone County (Census 2020), keyed by the
# banner's own name folded to lowercase.
BOONE_MUNICIPALITIES = {
    "belvidere": "City",
    "caledonia": "Village",
    "capron": "Village",
    "poplar grove": "Village",
    "timberlane": "Village",
}
# Printed in this section, deliberately not taken — see the module docstring.
OUT_OF_SCOPE = {
    "cherry valley": "already published in full by Winnebago County, whose "
                     "directory is this app's source for it",
    "loves park": "already published in full by Winnebago County, which names "
                  "all ten ward alderpersons this booklet omits",
}

# ---------------------------------------------------------------------------
# Row shapes. Leaders are a run of periods, of U+2026 ellipses, or of both —
# Caledonia's sixth trustee row mixes them.
LEADER_RE = re.compile(r"[.…]{3,}")
YEAR_RE = re.compile(r"^((?:19|20)\d{2})[.,*]?$")
APPOINTED_RE = re.compile(r"^appointed[.,*]?$", re.I)
PHONE_RE = re.compile(r"\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})")
EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
NON_PERSON_NAMES = {"vacant", "vacancy", "unassigned", "open", "tbd", "none",
                    "n/a", "na", "-"}

# A contact line that is a RESIDENCE: it opens with a house number or a post
# box. Used to COUNT what is being refused, never to decide what is kept —
# what is kept is only ever a regex-matched phone or e-mail.
RESIDENCE_OPENER_RE = re.compile(r"^\s*(?:\d|P\.?\s?O\.?\s+Box\b)", re.I)
# Street shape, for the post-build assertion. Deliberately broad: a number
# followed by words ending in a street-suffix token.
STREET_SHAPE_RE = re.compile(
    r"\b\d+\s*(?:½\s*)?(?:[A-Za-z][A-Za-z.'-]*\s+){0,4}"
    r"(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Ln|Lane|Ct|Court|Blvd|Boulevard|"
    r"Pkwy|Parkway|Trl|Trail|Ter|Terrace|Cir|Circle|Pl|Place|Way|Hwy|Highway|"
    r"Ridge|Crossing|Box)\b\.?", re.I)
STREET_SUFFIX_WORDS = re.compile(
    r"\b(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Ln|Lane|Ct|Court|Blvd|"
    r"Boulevard|Pkwy|Parkway|Trl|Trail|Ter|Terrace|Cir|Circle|Hwy|Highway)\b\.?",
    re.I)

# ---------------------------------------------------------------------------
# Hall-header lines: the ONLY lines that may set a street address.
#   "250 W. Main Street • Capron, Illinois 61012"
#   "2940 Charleston Ct. • P.O. Box 56 Caledonia, Illinois 61011"
HALL_FULL_RE = re.compile(
    r"^(?P<street>\d[^•]*?)\s*[•·]\s*(?P<rest>.+?),\s*(?:Illinois|IL)\.?\s*"
    r"(?P<zip>\d{5})(?:-\d{4})?\s*$", re.I)
#   "401 Whitney Blvd."  — street alone, no city or zip printed
HALL_STREET_RE = re.compile(r"^\d+\s+[A-Za-z0-9 .'’-]+$")
HALL_PHONE_RE = re.compile(r"^(?:Phone\s*)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", re.I)
HALL_WEBSITE_RE = re.compile(r"^(?:https?://)?(www\.[A-Za-z0-9.-]+\.[A-Za-z]{2,})/?$", re.I)
HALL_EMAIL_RE = re.compile(r"^E-?mail:\s*(\S+@\S+)$", re.I)
PO_BOX_RE = re.compile(r"^P\.?\s?O\.?\s+Box\s+\d+\s*,?\s*", re.I)

# ---------------------------------------------------------------------------
# Office captions. Everything shipped comes from this allowlist; a caption
# outside it ships verbatim WITH a warning (the builder's stance: a new office
# type gets a human, never a silent drop), unless it is a recognised
# department-head title, which is skipped.
KEEP_TITLES = {
    "mayor": ("Mayor", False),
    "president": ("President", False),
    "village president": ("President", False),
    "city president": ("President", False),
    # Belvidere elects ONE officer to both offices and prints it "City Clerk &
    # Collector". Emitted in the fleet's existing combined-office wording
    # ("clerk/collector", which De Witt's Waynesville already ships and the
    # builder already classifies) rather than dropping half the office.
    "city clerk & collector": ("Clerk/Collector", False),
    "village clerk & collector": ("Clerk/Collector", False),
    "city clerk": ("Clerk", False),
    "village clerk": ("Clerk", False),
    "clerk": ("Clerk", False),
    "city deputy clerk": ("Deputy Clerk", True),
    "village deputy clerk": ("Deputy Clerk", True),
    "deputy clerk": ("Deputy Clerk", True),
    "city treasurer": ("Treasurer", False),
    "village treasurer": ("Treasurer", False),
    "treasurer": ("Treasurer", False),
    "city collector": ("Collector", False),
    "village collector": ("Collector", False),
    "trustee": ("Trustee", False),
    "trustees": ("Trustee", False),
    "alderman": ("Alderperson", False),
    "aldermen": ("Alderperson", False),
    "alderperson": ("Alderperson", False),
    "alderpersons": ("Alderperson", False),
}
# Captions whose members carry a ward from the label column beside them.
WARD_CAPTIONS = {"alderman", "aldermen", "alderperson", "alderpersons"}
# Column captions that name no office.
IGNORE_CAPTIONS = {"ward", "wards", "name", "office"}
# Appointed department heads, recognised so they can be skipped quietly. A
# leader row whose title is NOT here warns instead.
STAFF_TITLE_RE = re.compile(
    r"^(City Attorney|Village Attorney|Attorney|Budget|Police|Chief|Fire|"
    r"Deputy Chief|Director|Community|Planner|Administrative|Plumbing|"
    r"Electrical|Building|Buildings|Inspector|Public Works|Street|Water|"
    r"Waste|Zoning|Engineer|Marshal|Interim|Custodian|Secretary|Commission)\b",
    re.I)

HEAD_TITLES = {"mayor", "president"}

# Ward labels sit in their own column; each shares a baseline with the FIRST
# of its two members.
WARD_LABEL_RE = re.compile(
    r"^(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)\s*:?$",
    re.I)
WARD_ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
                 "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10}
# THE COLUMN IS PROVEN BY ANCHOR AGREEMENT, NOT BY A PIXEL THRESHOLD, and that
# is a correction of the obvious first draft. Absolute coordinates ARE
# edition-specific here: the 2025 edition's page is 252 x 457 pt with the ward
# labels at x≈27.0 and the member rows at x≈58.0, while the 2026 edition is the
# same page scaled to 297 x 684 with those columns at x≈49.4 and x≈80.4. A
# threshold measured on 2026 puts both of 2025's columns on the same side and
# glues "First:" onto a person's name. The gap between label and member is no
# better — it is a tab stop, so it ranges from 5.1 to 14.1 pt with the label's
# length. What IS stable across both editions, to within a twentieth of a
# point, is that every one of the ten member rows starts at the SAME x while
# every ward label starts left of it. That is what a column is, and it is what
# this checks.
WARD_COLUMN_TOLERANCE = 2.0     # measured spread of the member anchor: 0.07 pt
# Words within this many points of a row's top edge belong to that row. The
# booklet's line pitch is ~9.5 pt and its superscripted ordinals ("9th") sit a
# fraction high, so a fixed bucket splits them off their own line.
ROW_TOLERANCE = 3.0

# 2026-08 live: 5 municipalities / 47 officials / 5 heads / 10 ward seats
# across 5 wards / 40 residences refused. The 2025 edition parses to the same
# five counts, which is the regression test for any change to row assembly.
# Deliberate under-tolerances —
# ordinary turnover and a vacancy pass, a section that stopped parsing does
# not. MIN_MUNICIPALITIES sits at the true value because Boone HAS five
# incorporated places: this source cannot lose one and still be right.
MIN_MUNICIPALITIES = 5
MIN_OFFICIALS = 40
MIN_HEADS = 4
MIN_WARD_SEATS = 8
MIN_WARDS = 5
# The home-address guard must have something to guard against. A run that
# refuses zero residences has stopped reading the contact lines, which is
# exactly the state in which the guard would pass while being blind.
MIN_RESIDENCE_LINES = 30


def clean(value):
    return re.sub(r"\s+", " ", (value or "")).strip() or None


def recase(text):
    """'POPLAR GROVE' -> 'Poplar Grove'; a mixed-case string is left alone."""
    if not text or not text.isupper():
        return text
    out = []
    for token in text.split(" "):
        bare = token.rstrip(".,")
        if bare.startswith("MC") and len(bare) > 2:
            out.append("Mc" + bare[2:].capitalize() + token[len(bare):])
        else:
            out.append(token[:1] + token[1:].lower())
    return " ".join(out)


def format_phone(match):
    return "%s-%s-%s" % match.groups()[-3:]


# ---------------------------------------------------------------------------
# Fetching

def discover_yearbook_url(warnings):
    """-> the URL of the newest edition the index page LABELS, else the pin."""
    try:
        resp = requests.get(INDEX_PAGE, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        warnings.append("could not read the yearbook index page (%s) — falling "
                        "back to the pinned edition %s" % (exc, YEARBOOK_URL))
        return YEARBOOK_URL
    links = YEARBOOK_LINK_RE.findall(resp.text)
    if not links:
        warnings.append("no dated 'NNNN Yearbook' link on %s — the index page's "
                        "markup changed; falling back to the pinned edition"
                        % INDEX_PAGE)
        return YEARBOOK_URL
    base_match = BASE_HREF_RE.search(resp.text)
    base = base_match.group(1) if base_match else resp.url
    href, year = max(links, key=lambda pair: int(pair[1]))
    url = urllib.parse.urljoin(base, html_mod.unescape(href).replace(" ", "%20"))
    return url


def fetch_pdf(url):
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT,
                        allow_redirects=True)
    resp.raise_for_status()
    if not resp.content.startswith(b"%PDF"):
        raise RuntimeError("yearbook URL did not return a PDF (got %d bytes of %s)"
                           % (len(resp.content), resp.headers.get("Content-Type")))
    return resp.content


# ---------------------------------------------------------------------------
# Layout-aware row assembly

class Row(object):
    """One printed line, rebuilt from word coordinates."""

    def __init__(self, words):
        self.words = sorted(words, key=lambda w: w["x0"])
        self.text = clean(" ".join(w["text"] for w in self.words)) or ""
        self.x0 = self.words[0]["x0"] if self.words else 0.0

    def split_ward_column(self):
        """-> (label, member_row, label_x1) when a ward label opens this row.

        The label is identified by CONTENT (an ordinal in the ward vocabulary);
        whether it is really a separate column is decided by the caller, which
        compares the member's x against the anchor every other member row in
        the block shares. Splitting on a fixed x would be wrong — see
        WARD_COLUMN_TOLERANCE.
        """
        if len(self.words) < 2:
            return None, self, None
        first = self.words[0]
        if not WARD_LABEL_RE.match(first["text"]):
            return None, self, None
        return first["text"], Row(self.words[1:]), first["x1"]


def document_rows(pdf_bytes):
    """-> [Row] for the whole document, in reading order."""
    if pdfplumber is None:
        raise RuntimeError("pdfplumber is required "
                           "(pip install -c scripts/requirements.txt pdfplumber)")
    rows = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            words = sorted(page.extract_words(), key=lambda w: (w["top"], w["x0"]))
            bucket, anchor = [], None
            for word in words:
                if anchor is None or word["top"] - anchor <= ROW_TOLERANCE:
                    if anchor is None:
                        anchor = word["top"]
                    bucket.append(word)
                else:
                    rows.append(Row(bucket))
                    bucket, anchor = [word], word["top"]
            if bucket:
                rows.append(Row(bucket))
    if not rows:
        raise RuntimeError("no text extracted from the yearbook — is it a scan?")
    return rows


def section_rows(rows):
    start = next((i for i, r in enumerate(rows) if SECTION_START_RE.match(r.text)), None)
    if start is None:
        raise RuntimeError("could not find the 'COUNTY OF BOONE – CITY/VILLAGE "
                           "OFFICIALS' banner — the yearbook's layout changed")
    end = next((i for i in range(start + 1, len(rows))
                if SECTION_END_RE.match(rows[i].text)), None)
    if end is None:
        raise RuntimeError("could not find the 'FIRE PROTECTION DISTRICT' heading "
                           "that bounds the municipal section")
    return rows[start + 1:end]


# ---------------------------------------------------------------------------
# Parsing

class Municipality(object):
    def __init__(self, name, kind):
        self.name = name
        self.kind = kind
        self.jurisdiction = "%s of %s" % (kind, name)
        self.street = None
        self.city = None
        self.zipcode = None
        self.phone = None
        self.email = None
        self.website = None
        self.records = []


class Member(object):
    def __init__(self, office, appointed, district):
        self.office = office
        self.appointed = appointed
        self.district = district
        self.name = None
        self.term = None
        self.phone = None
        self.email = None


def looks_like_title(text):
    """A short, digit-free, comma-free caption — an office, not a person's row.

    Used only to tell an appointed-staff leader row ("Police Chief …… Shane
    Woody") from a residence line ("610 W. 9th Street …… 815-218-4335"): a
    title carries no digits and no '@', a residence always opens with a house
    number.
    """
    if not text or "@" in text or re.search(r"\d", text) or "," in text:
        return False
    words = text.split()
    return 1 <= len(words) <= 5


def strip_term_caption(text):
    """'Village President Term Expires' -> 'Village President'."""
    return clean(re.sub(r"\s*Terms?\s+Expires\b.*$", "", text, flags=re.I)) or ""


def feed_contact(member, text, residences):
    """Take ONLY a phone and an e-mail from a line; discard the line itself.

    This is the whole home-address defence: the text of a residence line never
    reaches a record, because nothing here reads it as text.
    """
    if RESIDENCE_OPENER_RE.match(text):
        residences.append(text)
    email = EMAIL_RE.search(text)
    if email and member is not None and not member.email:
        member.email = email.group(1).lower()
    phone = PHONE_RE.search(text)
    if phone and member is not None and not member.phone:
        member.phone = format_phone(phone)


def parse_hall_line(muni, text, residences):
    """Set a hall field from a header line, or discard the line. -> bool taken."""
    full = HALL_FULL_RE.match(text)
    if full:
        muni.street = clean(full.group("street"))
        # "P.O. Box 56 Caledonia" — the hall is a place a resident can drive
        # to, so the box is dropped rather than concatenated (the Grundy rule).
        muni.city = clean(PO_BOX_RE.sub("", full.group("rest")))
        muni.zipcode = full.group("zip")
        return True
    website = HALL_WEBSITE_RE.match(text)
    if website:
        muni.website = website.group(1).lower().rstrip("/")
        return True
    email = HALL_EMAIL_RE.match(text)
    if email:
        muni.email = email.group(1).lower()
        return True
    if HALL_PHONE_RE.match(text):
        # "Phone 815-765-3201 • Fax 815-765-3571" — the first number only.
        found = PHONE_RE.search(text.split("•")[0])
        if found and not muni.phone:
            muni.phone = format_phone(found)
        return True
    if HALL_STREET_RE.match(text) and STREET_SUFFIX_WORDS.search(text):
        if not muni.street:
            muni.street = clean(text)
        return True
    if RESIDENCE_OPENER_RE.match(text):
        residences.append(text)
    return False


def parse(rows, warnings, drops, residences):
    """-> ([Municipality], skipped_names)."""
    municipalities = []
    muni = None
    skipping = None          # a banner we recognised and deliberately do not take
    hall_mode = False
    office = None            # (label, appointed) currently in effect
    ward_mode = False
    ward = None
    ward_anchor = None       # x of the member column beside the ward labels
    member = None
    pending_year = None      # a member row whose term year wrapped to its own line
    skipped = []

    def close_member():
        """End the current member's contact block, and account for a lost year.

        A member whose row ended in leaders and never met its wrapped term year
        still ships — the person is the point — but it says so, because a
        silently termless seat is the first symptom of the row assembly
        drifting.
        """
        nonlocal member, pending_year
        if pending_year is not None and pending_year.term is None:
            warnings.append("%s: '%s' is printed with leaders and no term year — "
                            "shipped without one"
                            % (muni.jurisdiction if muni else "?", pending_year.name))
        member = None
        pending_year = None

    for row in rows:
        text = row.text
        if not text or PAGE_NUMBER_RE.match(text):
            continue

        banner = MUNI_BANNER_RE.match(text)
        if banner:
            close_member()
            name = recase(clean(banner.group(1)))
            kind = banner.group(2).capitalize()
            key = (name or "").lower()
            if key in OUT_OF_SCOPE:
                skipping = name
                muni = None
                skipped.append(name)
                continue
            if key not in BOONE_MUNICIPALITIES:
                skipping = name
                muni = None
                warnings.append("unknown municipality banner '%s %s OFFICERS' — "
                                "NOT shipped; if Boone has a new incorporated "
                                "place, add it to BOONE_MUNICIPALITIES"
                                % (banner.group(1), banner.group(2)))
                continue
            skipping = None
            muni = Municipality(name, BOONE_MUNICIPALITIES[key])
            municipalities.append(muni)
            hall_mode = True
            office = None
            ward_mode = False
            ward = None
            ward_anchor = None
            continue

        if skipping is not None:
            continue
        if muni is None:
            continue
        if MUNI_CONT_RE.match(text):
            continue

        # --- ward column ------------------------------------------------
        row_ward = None
        off_column = False
        if ward_mode:
            label, member_row, label_x1 = row.split_ward_column()
            if label:
                if ward_anchor is None:
                    ward_anchor = member_row.x0
                if abs(member_row.x0 - ward_anchor) > WARD_COLUMN_TOLERANCE:
                    warnings.append("%s: the member beside ward label '%s' starts "
                                    "at x=%.1f but this block's member column is "
                                    "at x=%.1f — the ward columns moved; the ward "
                                    "on this row may be wrong"
                                    % (muni.jurisdiction, label, member_row.x0,
                                       ward_anchor))
                if label_x1 is not None and label_x1 > member_row.x0 + 0.5:
                    warnings.append("%s: ward label '%s' overlaps the member "
                                    "column — the two are no longer separate "
                                    "columns" % (muni.jurisdiction, label))
                row_ward = WARD_ORDINALS[label.rstrip(":").lower()]
                row = member_row
                text = row.text
            elif (ward_anchor is not None
                  and row.x0 < ward_anchor - WARD_COLUMN_TOLERANCE):
                # Only meaningful if this turns out to BE a member row; the
                # department-head rows that follow the block sit in the caption
                # column and are not the ward column's business.
                off_column = True

        leaders = LEADER_RE.search(text)
        left = clean(text[:leaders.start()]) if leaders else None
        tail = clean(text[leaders.end():]) if leaders else None

        # --- a seat with no holder --------------------------------------
        if leaders and ((left or "").lower() in NON_PERSON_NAMES
                        or (tail or "").lower() in NON_PERSON_NAMES):
            close_member()
            named = left if (left or "").lower() not in NON_PERSON_NAMES else None
            drops.append("%s: %s seat published as a vacancy — dropped, a vacancy "
                         "is not an officeholder"
                         % (muni.jurisdiction,
                            named or (office[0] if office else "a")))
            continue

        # --- a member row -----------------------------------------------
        if leaders and tail and (YEAR_RE.match(tail) or APPOINTED_RE.match(tail)):
            if office is None:
                warnings.append("%s: '%s' carries a term but no office caption is "
                                "in effect — not shipped" % (muni.jurisdiction, left))
                close_member()
                continue
            label, appointed = office
            member = Member(label, appointed, None)
            if ward_mode:
                if row_ward is not None:
                    ward = row_ward
                elif off_column:
                    warnings.append("%s: the member row '%s' starts left of this "
                                    "block's member column at x=%.1f — a ward "
                                    "label may have been read as part of the name"
                                    % (muni.jurisdiction, left, ward_anchor))
                member.district = "Ward %d" % ward if ward else None
            member.name = left
            if APPOINTED_RE.match(tail):
                member.appointed = True
            else:
                member.term = YEAR_RE.match(tail).group(1)
            muni.records.append(member)
            pending_year = None
            continue

        # --- a member row whose year wrapped onto its own line -----------
        # The booklet does this ("Mike Fidder ……" then "2029" alone on the next
        # line, in the township section that precedes this one), so the shape is
        # real. It is also the one shape that could ship an OFFICE as a person:
        # "Village Treasurer ……" with nothing after it names nobody. So a left
        # side that is itself a known caption is refused here rather than
        # rescued — the row is a title with no holder, not a person with no year.
        if leaders and not tail and looks_like_title(left) and office is not None:
            key = (left or "").lower().rstrip(":.")
            if key in KEEP_TITLES or key in IGNORE_CAPTIONS or STAFF_TITLE_RE.match(left):
                warnings.append("%s: the '%s' row names nobody — skipped"
                                % (muni.jurisdiction, left))
                close_member()
                continue
            label, appointed = office
            member = Member(label, appointed, None)
            if ward_mode:
                if row_ward is not None:
                    ward = row_ward
                member.district = "Ward %d" % ward if ward else None
            member.name = left
            muni.records.append(member)
            pending_year = member
            continue
        if pending_year is not None and YEAR_RE.match(text):
            pending_year.term = YEAR_RE.match(text).group(1)
            pending_year = None
            continue

        # --- an appointed department head printed inline -----------------
        if leaders and looks_like_title(left):
            close_member()
            if not STAFF_TITLE_RE.match(left):
                warnings.append("%s: '%s' is printed as an appointed officer with "
                                "no term year and is not a recognised department "
                                "title — NOT shipped; wire it into KEEP_TITLES if "
                                "it is a municipal officer"
                                % (muni.jurisdiction, left))
            continue

        # --- a hall-header line ------------------------------------------
        # Tried BEFORE the caption branch: a bare website line ("www.
        # villageofcaledonia.com") is short, digit-free and comma-free, so the
        # caption test would otherwise claim it as an office.
        if hall_mode and parse_hall_line(muni, text, residences):
            continue

        # --- an office caption -------------------------------------------
        if not leaders:
            caption = strip_term_caption(text)
            if not caption:
                hall_mode = False
                close_member()
                continue
            key = caption.lower().rstrip(":").rstrip(".")
            key = re.sub(r"\s+cont\.?$", "", key)
            if looks_like_title(caption):
                hall_mode = False
                close_member()
                if key in IGNORE_CAPTIONS:
                    continue
                if key in KEEP_TITLES:
                    office = KEEP_TITLES[key]
                    ward_mode = key in WARD_CAPTIONS
                    if not ward_mode:
                        ward = None
                        ward_anchor = None
                    continue
                if STAFF_TITLE_RE.match(caption):
                    office = None
                    ward_mode = False
                    continue
                office = (caption, False)
                ward_mode = False
                warnings.append("%s: unrecognised office caption '%s' — its "
                                "members ship under that wording; add it to "
                                "KEEP_TITLES to normalise it"
                                % (muni.jurisdiction, caption))
                continue

        # --- everything else is contact, and only a phone/e-mail is taken --
        feed_contact(member, text, residences)

    close_member()
    if not municipalities:
        raise RuntimeError("no municipality banners inside the section — the "
                           "yearbook's layout changed")
    return municipalities, skipped


# ---------------------------------------------------------------------------
# Cross-check against the county's own Belvidere ward service

def name_key(value):
    return re.sub(r"[^a-z]", "", (value or "").lower())


def cross_check_wards(municipalities, warnings):
    """Compare Belvidere's parsed wards with the county GIS. Fail-open.

    The yearbook stays the roster of record: a ward or name disagreement is
    reported and nothing is rewritten. A PHONE disagreement drops the phone —
    see the module docstring for why omitting beats picking.
    """
    belvidere = next((m for m in municipalities if m.name.lower() == "belvidere"), None)
    if belvidere is None:
        return "skipped: Belvidere not parsed"
    seats = [r for r in belvidere.records if r.district]
    if not seats:
        return "skipped: no ward seats parsed"
    try:
        resp = requests.get(BELVIDERE_WARD_SERVICE + "/query", headers=HEADERS,
                            timeout=REQUEST_TIMEOUT,
                            params={"where": "1=1", "outFields": "*",
                                    "returnGeometry": "false", "f": "json"})
        resp.raise_for_status()
        # An ArcGIS error arrives as HTTP 200 with an `error` member, so without
        # this the warning below would say the service "answered with no
        # features" — blaming the county's data for what is often our own
        # request rate. Raising here puts the service's own words in the note.
        features = raise_for_arcgis_error(
            resp.json(), "Boone's county ward service").get("features") or []
        if not features:
            raise RuntimeError("the ward service answered with no features")
    except Exception as exc:  # noqa: BLE001
        warnings.append("could not cross-check Belvidere's wards against the "
                        "county ward service (%s) — the yearbook's ward column "
                        "ships unverified" % exc)
        return "unavailable"

    gis = {}
    for feature in features:
        attrs = feature.get("attributes") or {}
        num = attrs.get("ward_num")
        for name_field, phone_field in (("ald_1", "phone_1"), ("ald_2", "phone_2")):
            person = clean(attrs.get(name_field))
            if person:
                gis[name_key(person)] = (num, clean(attrs.get(phone_field)), person)

    agreed = 0
    for seat in seats:
        key = name_key(seat.name)
        parsed_ward = int(re.sub(r"\D", "", seat.district or "0") or 0)
        if key not in gis:
            warnings.append("Belvidere: the yearbook seats %s in %s, and the "
                            "county ward service does not name that person — one "
                            "of the two is out of date"
                            % (seat.name, seat.district))
            continue
        gis_ward, gis_phone, gis_name = gis.pop(key)
        if gis_ward != parsed_ward:
            warnings.append("Belvidere: WARD DISAGREEMENT for %s — the yearbook "
                            "says Ward %d, the county ward service says Ward %s; "
                            "shipped as the yearbook prints it"
                            % (seat.name, parsed_ward, gis_ward))
            continue
        agreed += 1
        if seat.phone and gis_phone and seat.phone != gis_phone:
            warnings.append("Belvidere: %s's phone is %s in the yearbook and %s "
                            "in the county ward service — a transposed digit in "
                            "one of the two, and nothing in either settles which, "
                            "so NO phone ships for this seat (the e-mail does)"
                            % (seat.name, seat.phone, gis_phone))
            seat.phone = None
    for num, phone, person in gis.values():
        warnings.append("Belvidere: the county ward service names %s in Ward %s "
                        "and the yearbook's ward column does not — one of the two "
                        "is out of date" % (person, num))
    return "%d of %d ward seats agree name-for-name with the county ward service" \
        % (agreed, len(seats))


# ---------------------------------------------------------------------------
# Payload

def build_payload(municipalities, warnings, drops, source_url, scraped_at):
    officials = []
    for muni in municipalities:
        shared = {
            "jurisdiction": muni.jurisdiction,
            "office_address": muni.street,
            "office_city": muni.city,
            "office_state": "IL" if muni.city else None,
            "office_zip": muni.zipcode,
            "office_phone": muni.phone,
            "office_email": muni.email,
            "website": muni.website,
        }
        head_names = {name_key(r.name) for r in muni.records
                      if r.name and (r.office or "").lower() in HEAD_TITLES}
        for rec in muni.records:
            if not rec.name:
                warnings.append("%s: a %s row carries no readable name — skipped"
                                % (muni.jurisdiction, rec.office))
                continue
            if rec.name.lower() in NON_PERSON_NAMES:
                drops.append("%s: %s seat published as '%s' — dropped"
                             % (muni.jurisdiction, rec.office, rec.name))
                continue
            if ((rec.office or "").lower() not in HEAD_TITLES
                    and name_key(rec.name) in head_names):
                drops.append("%s: dropped the %s row for %s — the same person is "
                             "published as the head of government"
                             % (muni.jurisdiction, rec.office, rec.name))
                continue
            if len(rec.name.split()) == 1:
                warnings.append("%s: %s is published as '%s', a single token — it "
                                "may be an organisation rather than a person; "
                                "shipped exactly as published"
                                % (muni.jurisdiction, rec.office, rec.name))
            record = dict(shared, office=rec.office, district=rec.district,
                          name=rec.name)
            if rec.appointed:
                record["appointed"] = True
            if rec.term:
                record["term_expires"] = rec.term
            # A "direct" number that is only the hall's main line is not a
            # direct line; same for a shared inbox.
            if rec.phone and rec.phone != muni.phone:
                record["person_phone"] = rec.phone
            if rec.email and rec.email != (muni.email or ""):
                record["person_email"] = rec.email
            record["source_url"] = source_url
            record["scraped_at"] = scraped_at
            officials.append(record)

    return {
        "county": "Boone",
        "directory_url": source_url,
        "officials_page": INDEX_PAGE,
        "scraped_at": scraped_at,
        "municipalities": [{"name": m.name, "source_url": source_url,
                            "scraped_at": scraped_at} for m in municipalities],
        "officials": officials,
    }


def assert_no_home_addresses(payload, residences):
    """Prove on the BUILT payload that no residence got in. Fatal on failure.

    Three independent checks, because the parser being right is a claim and
    this is the evidence: (1) nothing that can name a person carries a digit,
    an '@' or a street word; (2) once the hall addresses are blanked, no
    street-shaped text survives anywhere in the payload; (3) the residence
    detector actually saw residences, so check (2) is not passing blind.
    """
    problems = []

    for record in payload["officials"]:
        for field in ("name", "office", "district"):
            value = record.get(field)
            if not value:
                continue
            if re.search(r"@", value) or STREET_SUFFIX_WORDS.search(value):
                problems.append("%s carries '%s' in its %s field"
                                % (record.get("jurisdiction"), value, field))
            if field != "district" and re.search(r"\d", value):
                problems.append("%s carries a digit in its %s field ('%s')"
                                % (record.get("jurisdiction"), field, value))
            # A colon in a name is the ward-column failure wearing a disguise:
            # "First: Clayton Stevens" is what a mis-split row produces, and it
            # reads on a card as a person's name.
            if field == "name" and ":" in value:
                problems.append("%s carries a colon in a person's name ('%s') — "
                                "a ward label was probably read as part of it"
                                % (record.get("jurisdiction"), value))

    blob = json.dumps(payload, ensure_ascii=False)
    halls = {r.get("office_address") for r in payload["officials"] if r.get("office_address")}
    for hall in halls:
        blob = blob.replace(hall, "<hall>")
    leaked = STREET_SHAPE_RE.search(blob)
    if leaked:
        problems.append("street-shaped text '%s' survives in the payload with "
                        "the hall addresses blanked out" % leaked.group(0))

    if len(residences) < MIN_RESIDENCE_LINES:
        problems.append("the residence detector saw only %d street-address lines "
                        "(floor %d) — it has stopped seeing the lines it exists "
                        "to refuse, so the checks above prove nothing"
                        % (len(residences), MIN_RESIDENCE_LINES))

    if problems:
        for problem in problems:
            print("  HOME-ADDRESS GUARD: %s" % problem, file=sys.stderr)
        print("FATAL: refusing to write a payload that may carry a home address",
              file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--pdf", help="parse a local copy instead of fetching")
    parser.add_argument("--no-cross-check", action="store_true",
                        help="skip the Belvidere ward cross-check against the "
                             "county GIS (offline runs)")
    args = parser.parse_args()

    warnings, drops, residences = [], [], []
    try:
        if args.pdf:
            source_url, pdf_bytes = YEARBOOK_URL, open(args.pdf, "rb").read()
        else:
            source_url = discover_yearbook_url(warnings)
            pdf_bytes = fetch_pdf(source_url)
        municipalities, skipped = parse(section_rows(document_rows(pdf_bytes)),
                                        warnings, drops, residences)
    except Exception as exc:  # noqa: BLE001
        print("FATAL: %s" % exc, file=sys.stderr)
        sys.exit(1)

    cross_check = "skipped (--no-cross-check)"
    if not args.no_cross_check:
        cross_check = cross_check_wards(municipalities, warnings)

    scraped_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    display_url = source_url.split("?")[0]
    payload = build_payload(municipalities, warnings, drops, display_url, scraped_at)

    for name in skipped:
        print("  out of scope: %s — %s" % (name, OUT_OF_SCOPE[name.lower()]),
              file=sys.stderr)
    for drop in sorted(set(drops)):
        print("  dropped: %s" % drop, file=sys.stderr)
    for warning in sorted(set(warnings)):
        print("  warning: %s" % warning, file=sys.stderr)

    assert_no_home_addresses(payload, residences)

    officials = payload["officials"]
    heads = sum(1 for p in officials if (p["office"] or "").lower() in HEAD_TITLES)
    seats = [p for p in officials if p.get("district")]
    wards = {p["district"] for p in seats}
    problems = []
    if len(municipalities) < MIN_MUNICIPALITIES:
        problems.append("%d municipalities < floor %d"
                        % (len(municipalities), MIN_MUNICIPALITIES))
    if len(officials) < MIN_OFFICIALS:
        problems.append("%d officials < floor %d" % (len(officials), MIN_OFFICIALS))
    if heads < MIN_HEADS:
        problems.append("%d heads of government < floor %d" % (heads, MIN_HEADS))
    # Belvidere's ten alderpersons are the part of this payload the
    # municipal-ward layer joins to; a break confined to the ward column would
    # pass every count above.
    if len(seats) < MIN_WARD_SEATS:
        problems.append("%d ward seats < floor %d" % (len(seats), MIN_WARD_SEATS))
    if len(wards) < MIN_WARDS:
        problems.append("%d distinct wards < floor %d (Belvidere has five, each "
                        "with one of its two seats up every two years, so a ward "
                        "cannot go unrepresented)" % (len(wards), MIN_WARDS))
    if problems:
        for problem in problems:
            print("  FAIL: %s" % problem, file=sys.stderr)
        print("FATAL: refusing to write a payload that lost coverage", file=sys.stderr)
        sys.exit(1)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print("scraped %d municipalities, %d officials (%d heads, %d ward seats "
          "across %d wards) from %s -> %s"
          % (len(municipalities), len(officials), heads, len(seats), len(wards),
             display_url, args.out), file=sys.stderr)
    print("home addresses refused: %d residence lines read for a phone/e-mail "
          "and otherwise discarded; 0 in the payload"
          % len(residences), file=sys.stderr)
    print("Belvidere ward cross-check: %s" % cross_check, file=sys.stderr)


if __name__ == "__main__":
    main()
