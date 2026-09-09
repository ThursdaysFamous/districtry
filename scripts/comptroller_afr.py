#!/usr/bin/env python3
"""Read an Illinois unit of local government's own Annual Financial Report.

WHY THIS IS SHARED. Every Illinois unit of local government files an AFR with
the Comptroller under the Fiscal Responsibility Report Card Act, and the
report's Contact Information section publishes the unit's office address,
telephone, fax and e-mail together with named role-holders and THE TITLE THE
UNIT ITSELF FILED. The Comptroller is the COLLECTOR; the unit is the author,
which is what makes a row here the district's own statement about itself
rather than a third party's assertion about it.

That is a route to any county's special districts, not one county's trick.
Peoria was first (peoria_district_officials_scraper.py) and Logan second
(logan_district_officials_scraper.py); the two differ only in where the list
of districts to join TO comes from -- Peoria reads its county's own ArcGIS
layers, Logan the shipped boundary file a regional planning commission drew.
Everything else was identical, so it lives here once. scraper_common carries
the same instruction and it holds here: SHARED MACHINERY -- DO NOT FORK.

ONLY TWO OF THE FOUR ROLE SLOTS ARE READ, and the form itself says why. Slots
B and C are captioned "Your name will be listed with this responsibility on
our website" -- they are the officers the unit is publishing. Slot A (Contact
Person) and slot D (Purchasing Agent) are administrative contacts for the
filing, and reading them buys nothing and costs accuracy: Dunlap Fire
Protection District files the same person as "Jim Winters" in slot C and
"Jim Withers" in slot D, so a parser reading all four ships one trustee twice
under two spellings. NAMES ARE NEVER CORRECTED HERE and never joined on; the
unit CODE is the key.

THE FILED TITLE DECIDES WHICH LIST A PERSON JOINS, and this is the whole
reason the source is usable. docs/EXPANSION_GUIDE.md §3.4 records that the
Comptroller's "CEO" is often the appointed manager, and that holds -- Lisle-
Woodridge FPD in DuPage files its FIRE CHIEF in slot B. But the title the unit
filed sits beside the name, so an elected officer and an appointed one are
told apart per row instead of the whole source being trusted or discarded:
Dunlap FPD files Ann Joyce, PRESIDENT, and Dunlap Public Library District
files James Emanuels, PRESIDENT and Ron Holohan, TREASURER. Following
boone_district_officials, an appointed officer is not withheld -- it ships
under `heads` labelled with its own filed title, where a trustee ships under
`board`. A title this file does not recognise ships under `heads` with a
warning naming it, never silently dropped and never guessed into a board seat.

EVERY RECORD NAMES ITS FISCAL YEAR. An AFR is a snapshot filed for one year,
and the Comptroller's own page says "The contact person listed on the AFRs is
for the current Fiscal Year. Previous fiscal years may have a different
contact person." So `filedFor` rides every district and a card can say what
was filed and when rather than claiming a currency the filing cannot support.
"""

import html
import re
import time

import requests  # noqa: F401  (callers pass a session; imported for the dep pin)
from scraper_common import UA_ROSTER_COMPACT  # noqa: E402  (shared — do not fork)

WAREHOUSE = ("https://illinoiscomptroller.gov/constituent-services/"
             "local-government/local-government-warehouse/")
SEARCH_FORM = WAREHOUSE + "searchform/?SearchType=AFRSearch"
RESULTS = WAREHOUSE + "processsearchresults/"

HEADERS = {"User-Agent": UA_ROSTER_COMPACT}
TIMEOUT = 45
PACE = 1.0                       # a state government site, one request a second

# An ELECTED board office. A district's trustees elect these from among
# themselves, so a person filed under one of them holds a board seat.
BOARD_TITLES = {"president", "vice president", "vice-president", "secretary",
                "treasurer", "trustee", "chairman", "chair", "chairperson",
                "commissioner", "board president", "board chairman"}
# An APPOINTED post. Shipped, and never as a board seat.
HEAD_TITLES = {"fire chief", "chief", "director", "executive director",
               "administrator", "village administrator", "city administrator",
               "librarian", "head librarian", "superintendent", "manager"}

# A filed SPELLING of a title already in BOARD_TITLES, mapped to the title it
# abbreviates. This is a vocabulary table and never a judgement about a person:
# each entry expands an abbreviation of an office the table above already
# treats as elected, so nothing here can promote a title that is not already a
# board office. THE FILED TITLE STILL SHIPS VERBATIM -- only the bucket
# decision reads the expansion, so a card shows "V-President" as filed.
#
# WHY IT EXISTS. Logan's seven park districts file three titles that fall
# outside both vocabularies -- Atlanta Memorial's "V-President", Chestnut-
# Beason's "Sec./Treas." and San Jose's "Acting President" -- and without this
# table three elected trustees ship under Administration, which tells a reader
# they are appointed staff. None of the three spellings appears in any of
# Peoria's 18 filing districts, so adding them changed no shipped record.
#
# "Treas./Admin." IS DELIBERATELY ABSENT, and it is the reason this is a table
# rather than a normalizer that strips punctuation and expands abbreviations.
# Three Peoria districts file it, and unlike the three above it names TWO
# posts -- Treasurer, which is a board office, and Administrator, which is not
# -- so nothing here can say which one the filer meant. It stays where the
# conservative rule puts it, under `heads`, with its warning.
TITLE_ALIASES = {
    "v-president": "vice president",
    "v. president": "vice president",
    "vp": "vice president",
    "sec./treas.": "secretary",
    "sec/treas": "secretary",
    "acting president": "president",
}

SLOTS = 4                        # A Contact Person, B CEO, C CFO, D Purchasing Agent
# B and C are the unit's PUBLISHED officers: the form captions them "Your name
# will be listed with this responsibility on our website".
PUBLISHED_SLOTS = (1, 2)
# A and D are the filing's administrative contacts, and are read ONLY for a
# BOARD-TITLED person the unit has not already named in B or C. Measured across
# all 25 shipped districts on 2026-09-09, that admits exactly three trustees who
# were previously invisible -- Brimfield Public Library's George Stenger
# (Secretary, slot D), Timber-Hollis FPD's Shelly Bergland (V-President, slot A)
# and San Jose Park District's Alex Hamilton (Trustee, slot D) -- and admits
# nobody else.
#
# WHY BOARD-TITLED ONLY, AND WHY THAT ONE TEST IS THE WHOLE GUARD. Slots A and D
# are exactly where this source's duplicate traps live: of 27 repeated names
# across the 25 districts, EVERY ONE is non-board-titled, so the title test
# excludes all of them without a single name comparison. The three shapes,
# measured rather than assumed:
#   * the same name in two slots (23 cases -- West Peoria files Mark Stecher in
#     all four), already caught by the pair dedupe below;
#   * CASE-ONLY, which the pair dedupe did NOT catch until this change: Hanna
#     City Park District files "Trace Evans" in B and "trace evans" in D, both
#     C.E.O.;
#   * THE SAME PERSON UNDER DIFFERENT TITLES: Chillicothe Park files Kevin Yates
#     as Director in A and Purchasing Agent in D.
# Dunlap FPD's "Jim Winters"/"Jim Withers" pair is a fourth shape and needs no
# name matching either: both are filed Treas./Admin., which is not a board title.
#
# AN ADDRESS TEST WAS PROPOSED AND MEASURED WRONG, which is why it is not here.
# San Jose's Hamilton does file a different street from B and C -- but Brimfield's
# Stenger and Timber-Hollis's Bergland file the SAME street as theirs, so keying
# on a differing address would ship one real trustee and drop the other two.
#
# THE SLOT IS AN ADMINISTRATIVE ROLE AND THE TITLE IS AN OFFICE, and reading the
# title is the point. A unit filing "our Purchasing Agent is Alex Hamilton,
# Trustee" is stating that Hamilton is a trustee; the caption that governs B and
# C is about what the Comptroller publishes on its own site, not about who holds
# office. NON-board titles in A and D are still not read: they are appointed
# staff filed as filing contacts, they carry every duplicate shape above, and
# they buy nothing a card should assert.
BOARD_ONLY_SLOTS = (0, 3)
CONTACT_SLOT = 0                 # the unit's own office address and telephone

RESULT_RE = re.compile(
    r'href="[^"]*[Cc]ode=([0-9/]+)"[^>]*>\s*([^<]{3,140}?)\s*</a>', re.S)


def new_session():
    """A session holding the ColdFusion cookie the results endpoint needs."""
    s = requests.Session()
    s.headers.update(HEADERS)
    s.get(SEARCH_FORM, timeout=TIMEOUT)
    return s


def text_of(markup):
    body = re.sub(r"<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ",
                  markup, flags=re.S)
    lines = html.unescape(re.sub(r"<[^>]+>", "\n", body)).split("\n")
    return [l.strip() for l in lines if l.strip()]


def search_units(session, term):
    """[(code, label)] for every unit the Warehouse's search returns for a term.

    THE SEARCH IS A SUBSTRING MATCH AND THE CALLER MUST NOT TREAT IT AS A
    LOOKUP: searching "Armington" also returns seven FARMINGTON units. Callers
    filter it -- enumerate_county() by the county the label names, and a
    cross-county filer by its own unit code.
    """
    r = session.post(RESULTS, timeout=TIMEOUT,
                     data={"displayMode": "GetLandingPage",
                           "SearchType": "AFRSearch", "GovUnit": term})
    r.raise_for_status()
    return [(c, html.unescape(re.sub(r"\s+", " ", t)).strip())
            for c, t in RESULT_RE.findall(r.text)]


def enumerate_county(session, county):
    """[(code, label)] for every unit the Warehouse files under this county.

    ONE search on the county name returns the whole county -- 96 typed units
    for Peoria, 82 for Logan -- because the search matches the county as well
    as the unit name. Looking units up one at a time would be 25 requests for
    the same answer.

    A CROSS-COUNTY DISTRICT IS NOT HERE, because it files once, under its home
    county: Logan's Armington Community Park District files in Tazewell and its
    San Jose Park District in Mason, and neither appears in a Logan search. A
    caller that needs them names them by unit code -- see logan_district_
    officials_scraper.EXTERNAL_FILERS.
    """
    return [(c, t) for c, t in search_units(session, county)
            if ("in %s County" % county) in t]


def latest_fiscal_year(session, code):
    """The fiscal year this unit last filed for, off its landing page.

    THE YEAR IS ASKED FOR, NEVER ASSUMED. An empty CFY returns a page with no
    contact block at all -- which the first draft of the Peoria scraper sent,
    so every unit parsed as unfiled and the whole run failed -- and a hardcoded
    year would silently skip a unit that is one year behind. Hanna City Park
    District's latest is FY2024 where every other Peoria and Logan unit
    measured is FY2025.
    """
    r = session.get(WAREHOUSE + "landingpage",
                    params={"code": code, "searchtype": "AFRSearch"},
                    timeout=TIMEOUT)
    r.raise_for_status()
    lines = text_of(r.text)
    for i, line in enumerate(lines):
        if line == "For Fiscal Year" and i + 1 < len(lines):
            year = lines[i + 1].strip()
            return year if re.fullmatch(r"20\d\d", year) else None
    return None


def contact_rows(markup):
    """The contact table's rows as lists of cell text, or []."""
    for table in re.findall(r"<table[^>]*>.*?</table>", markup, re.S):
        if "Chief Executive Officer" not in table:
            continue
        rows = []
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S):
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)
            rows.append([re.sub(r"\s+", " ",
                                html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                         for c in cells])
        return rows
    return []


def contact_block(session, code, unit_label, warnings):
    """The unit's office and its two published officers, or None.

    PARSED FROM THE TABLE, NEVER FROM FLATTENED TEXT. The first draft read the
    page as a list of lines and sliced it four at a time, which mispaired every
    unit: THE NAME ROW CARRIES EIGHT CELLS (a forename and a surname for each
    of the four slots) WHERE EVERY OTHER ROW CARRIES FOUR, so a positional read
    took `Ann | Joyce | Ann | Joyce` as four forenames and `Jim | Winters | Jim
    | Withers` as their surnames and shipped a trustee called "Ann Jim". It
    published 24 board officers, none of them trustworthy. The rows are keyed
    by their own shape and their own labels here, and a table that does not
    match is SKIPPED with a warning rather than guessed at.
    """
    year = latest_fiscal_year(session, code)
    if not year:
        warnings.append("%s: no fiscal year on its landing page — it files no "
                        "contact block this run" % unit_label)
        return None
    time.sleep(PACE)
    r = session.post(RESULTS, timeout=TIMEOUT,
                     data={"DisplayMode": "GetAFR", "Code": code,
                           "CFY": year, "AFRDesiredData": "Contact Information"})
    r.raise_for_status()
    rows = contact_rows(r.text)
    names = next((x for x in rows if len(x) == 2 * SLOTS
                  and any(c for c in x)), None)
    if names is None:
        warnings.append("%s: no %d-cell name row in the contact table — the "
                        "form's layout changed" % (unit_label, 2 * SLOTS))
        return None
    after = rows[rows.index(names) + 1:]
    quad = [x for x in after if len(x) == SLOTS]
    if len(quad) < 6:
        warnings.append("%s: contact table has %d four-cell row(s), expected at "
                        "least 6" % (unit_label, len(quad)))
        return None
    titles = quad[0]
    # The three rows between the titles and the labelled ones, in the form's
    # own order. Labelled rows identify themselves and are found by label.
    unlabelled = [x for x in quad[1:] if not any(
        c.startswith(("Phone:", "Fax:", "E-mail:")) for c in x)]
    street = unlabelled[0][0] if unlabelled else ""
    city = unlabelled[1][0] if len(unlabelled) > 1 else ""
    region = unlabelled[2][0] if len(unlabelled) > 2 else ""

    def labelled(prefix, slot):
        for x in quad:
            if x[slot].startswith(prefix):
                return x[slot][len(prefix):].split("Ext")[0].strip()
        return ""

    def slot_person(slot):
        name = " ".join(x for x in (names[2 * slot], names[2 * slot + 1]) if x).strip()
        title = (titles[slot] or "").strip()
        if not name or not title:
            return None, None, None
        key = title.lower().strip()
        # An abbreviation of a board office is classified as that office and
        # still SHIPS as filed. Unknown spellings fall through unchanged and
        # are warned about below.
        key = TITLE_ALIASES.get(key, TITLE_ALIASES.get(key.rstrip("."), key))
        return name, title, key.rstrip(".").strip()

    officers = []

    def already_named(name):
        """Has this unit already named this person, ignoring case?

        CASE-FOLDED AND NOTHING CLEVERER. Hanna City Park District files "Trace
        Evans" in slot B and "trace evans" in slot D, which an exact match reads
        as two people. This is NOT a judgement that two similar names are one
        person -- Dunlap FPD's "Jim Winters" and "Jim Withers" stay two records
        here, and are kept out of the board list by their title instead.
        """
        return any(q["name"].casefold() == name.casefold() for _b, q in officers)

    for slot in PUBLISHED_SLOTS:
        name, title, key = slot_person(slot)
        if not name:
            continue
        # West Peoria FPD files Mark Stecher, President, as BOTH its CEO and
        # its CFO — one person holding two responsibilities, not two trustees.
        # Deduped on the pair as filed, never by matching names loosely: the
        # same unit can file one person under two spellings and this must not
        # be the code that decides two spellings are one person.
        if any(q["name"] == name and q["role"] == title for _b, q in officers):
            continue
        if key in BOARD_TITLES:
            officers.append(("board", {"name": name, "role": title}))
        else:
            if key not in HEAD_TITLES:
                warnings.append("%s: filed title %r for %s is neither a board "
                                "office nor a recognised appointed post — "
                                "shipped as appointed, never as a board seat"
                                % (unit_label, title, name))
            officers.append(("heads", {"name": name, "role": title}))

    # The second pass, over the filing's administrative slots. A board-titled
    # person the unit has not already named is a trustee it would otherwise have
    # left invisible; everything else in these slots is skipped. See
    # BOARD_ONLY_SLOTS for what this admits and what it deliberately does not.
    for slot in BOARD_ONLY_SLOTS:
        name, title, key = slot_person(slot)
        if not name or key not in BOARD_TITLES or already_named(name):
            continue
        officers.append(("board", {"name": name, "role": title}))

    return {"filedFor": year,
            "street": street,
            "city": " ".join(x for x in (city, region) if x).strip(),
            "phone": labelled("Phone:", CONTACT_SLOT),
            "email": labelled("E-mail:", CONTACT_SLOT),
            "officers": officers}
