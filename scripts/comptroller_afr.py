#!/usr/bin/env python3
"""Read an Illinois unit of local government's own Annual Financial Report.

WHY THIS IS SHARED. Every Illinois unit of local government files an AFR with
the Comptroller under the Fiscal Responsibility Report Card Act, and the
report's Contact Information section names up to four role-holders with THE
TITLE THE UNIT ITSELF FILED, and beside each one the address, telephone, fax
and e-mail THAT PERSON gave. The Comptroller is the COLLECTOR; the unit is the
author, which is what makes a row here the district's own statement about
itself rather than a third party's assertion about it.

WHAT IT DOES NOT CARRY IS A UNIT ADDRESS, and this file said otherwise until
2026-09-10 and shipped 24 people's private details as public bodies' contacts
because of it. See CONTACT WITNESSES below for the measurement and for the
witnesses a contact value now has to pass.

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

# A LOCALITY THE UNIT ITSELF MISFILED, corrected by unit CODE and never by name.
#
# The "record the disagreement and correct neither direction" rule that governs
# unit NAMES (il_special_district_officials_scraper.py) does not reach this, and
# the difference is the whole justification: that rule is for two publishers
# spelling one place differently, where correcting either would be picking a
# winner. Here there is one publisher and nothing disagrees with the filing
# except the filing.
#
# Norridge Park District's 2026 report gives its locality as "Norrideg". Its own
# unit name in the same table is NORRIDGE PARK DISTRICT, its 2025 report filed
# "Norridge", and 60706 is the Norridge/Harwood Heights ZIP -- Norwood Park FPD
# files "Harwood Heights IL 60706" in this very table. There is no Norrideg,
# Illinois. Shipping it would print a wrong address on a real park district's
# card, having previously printed the right one.
#
# NOT A GENERAL NAME-MATCHER, and that was measured before this was written. Of
# the 486 units carrying an office, 74 file a locality sharing no word with
# their own name, and essentially all of them are correct: a fire protection
# district is routinely housed in a neighbouring village (Norwood Park FPD in
# Harwood Heights, Central Stickney FPD in Chicago, Roberts Park FPD in
# Justice). "The city does not match the name" is not evidence of anything, so
# each entry here is one unit, stated, with its own reason.
#
# EACH ENTRY NAMES THE FILED VALUE IT REPLACES, so it cannot outlive the defect:
# when the unit files the corrected spelling the entry stops matching and the
# run prints a STALE line telling the next reader to delete it. That is a
# warning rather than a failure on purpose -- a district fixing its own typo is
# a good event, and failing the weekly refresh over it would block every other
# unit's update to punish the source for improving.
LOCALITY_CORRECTIONS = {
    # unit code:  (locality as filed, locality to ship)
    "016/490/12": ("Norrideg", "Norridge"),      # Norridge Park District, 2026 filing
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

# CONTACT WITNESSES
#
# THE FORM HAS NO UNIT-ADDRESS FIELD, and reading one out of it was a bug. Each
# of the four slots carries the address, telephone and e-mail of THE PERSON in
# that slot, and until 2026-09-10 this file returned slot A's as "the district's
# office". Measured across all 50 filings the fleet reads, that shipped one
# person's private details as a public body's contact in 24 of them: Atlanta
# Memorial Park District's card carried a rural grid address, a mobile number
# and a hotmail account, all its President's, while the only other filer gave a
# different rural address; Elmwood FPD's carried its President's employer's
# e-mail while its Treasurer filed his own at faa.gov; and West Peoria FPD's
# carried its President's address at another company while slot D of the SAME
# filing carried his address on the district's own domain.
#
# So a value ships only where the filing itself shows it is not one person's.
# Two witnesses exist and each is computed from the filing, never judged:
#
#   * A STREET OR TELEPHONE TWO DIFFERENTLY-SURNAMED FILERS GAVE. Two unrelated
#     officers do not share a home or a mobile, so a value both filed is the
#     unit's. Slots are scanned in the form's own order and the first witnessed
#     value is taken; measured, that admits 27 of 50 addresses and 21 of 50
#     telephones, and every admitted address is a station, a library, a park
#     office or a PO box.
#   * AN E-MAIL THAT NAMES THE UNIT AND WHAT KIND OF BODY IT IS, in its domain
#     or its local part -- `hudsonfire.org`, `chestnutbeasonpark@gmail.com`. A
#     mailbox saying whose and what it is cannot be one person's private
#     account; `pigjock76@hotmail.com` says neither. That admits 20 of 50,
#     and it is the test that reaches a value in a slot the old code never
#     looked at: West Peoria FPD's address on its own domain sits in slot D.
#
# THE TWO-FILER TEST IS NOT USED FOR E-MAIL, because it is wrong in both
# directions there: it withholds `director@dunlaplibrary.org` (filed once) and
# admits `april.wagner3953@hotmail.com` (a filer copied one personal account
# into two people's slots). Withholding a real contact is a cost; publishing a
# private one is a rule this project does not break.
#
# ITS KNOWN HOLE IS STATED RATHER THAN PATCHED. Two witnesses means two distinct
# SURNAMES, so a unit filing one person under two spellings of a surname would
# satisfy it -- Eureka Library District files Cindy O'Neill and Cindy O'Neil, and
# Dunlap FPD Jim Winters and Jim Withers. Measured across the 50 filings, no
# address or telephone is admitted on such a pair alone; both those units carry
# two further, plainly distinct witnesses. Nothing here decides that two similar
# names are one person.

# A token of the unit's own name has to be long enough not to match by accident
# and specific enough to mean the unit: "El Paso" contributes `paso`, and a type
# word contributes nothing, because every fire district's domain may carry
# `fire` without being that district's.
UNIT_TOKEN_MIN = 4
UNIT_TOKEN_STOP = {"district", "districts", "park", "parks", "fire", "library",
                   "libraries", "public", "protection", "township", "community",
                   "county", "illinois", "memorial", "rural"}

# A word naming WHAT KIND OF BODY the mailbox belongs to. An e-mail has to carry
# one of these as well as a word of the unit's own name, and El Paso is why: its
# fire district files a contact at `elpasoil.org`, which is the CITY OF EL PASO's
# own website ("El Paso, IL - Official Website"), so the town's name alone does
# not distinguish the district from the municipality it is named after. A
# mailbox that says which kind of body it serves does -- `hudsonfire.org`,
# `metamoraparks.org`, `elpasodistrictlibrary.org`, `chestnutbeasonpark@`.
#
# THE LIST IS THE KINDS THIS ROUTE SERVES, which the builders state as
# EXPECT_KINDS: fire, park and library. A run that starts carrying another kind
# of unit needs a word here, and the builders' EXPECT_KINDS check is what
# surfaces that rather than an e-mail quietly going missing.
UNIT_KIND_WORDS = {"fire", "fd", "fpd", "park", "parks", "library", "libraries",
                   "lib", "district", "districts"}

RESULT_RE = re.compile(
    r'href="[^"]*[Cc]ode=([0-9/]+)"[^>]*>\s*([^<]{3,140}?)\s*</a>', re.S)


def _flat(value):
    """A value reduced to its comparable core: lowercase alphanumerics."""
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _surname(name):
    """The last word of a filed name, for counting distinct filers.

    Nothing here matches names loosely -- see the hole stated above.
    """
    parts = _flat(name).split()
    return parts[-1] if parts else ""


def unit_tokens(unit_label):
    """The unit's own name words, for testing whether a domain is the unit's.

    Callers hand this file a label in one of two shapes -- the Warehouse's own
    "Benson - a Fire Protection District in Woodford County" and Logan's
    "Atlanta Memorial (Logan County)" -- so both the type clause and a trailing
    parenthesis are cut before tokenising.
    """
    name = unit_label.split(" - ")[0]
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name)
    return {t for t in re.split(r"[^a-z0-9]+", name.lower())
            if len(t) >= UNIT_TOKEN_MIN and t not in UNIT_TOKEN_STOP}


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

    def labelled(prefix, slot):
        for x in quad:
            if x[slot].startswith(prefix):
                return x[slot][len(prefix):].split("Ext")[0].strip()
        return ""

    def cell(rows, index, slot):
        return rows[index][slot].strip() if len(rows) > index else ""

    # EVERY SLOT IS READ, because each carries its own filer's details and the
    # one the unit can be shown to own is not always slot A.
    filers = [{"name": " ".join(x for x in (names[2 * i], names[2 * i + 1]) if x).strip(),
               "street": cell(unlabelled, 0, i),
               "city": cell(unlabelled, 1, i),
               "region": cell(unlabelled, 2, i),
               "phone": labelled("Phone:", i),
               "email": labelled("E-mail:", i)}
              for i in range(SLOTS)]

    def witnessed(field):
        """The first slot whose `field` two differently-surnamed filers gave.

        WHAT THIS COSTS, MEASURED ON A UNIT THAT PAID IT. Reddick Fire
        (053/085/06) shipped 210 E MAIN ST, REDDICK and (815) 365-4911 from its
        FY2025 filing and ships no office at all from FY2026 — and the filing
        did NOT get sparser. Read on 2026-09-21, both years through this same
        parser: FY2026 carries the street in all four slots and the telephone in
        all four. What changed is WHO SIGNED. FY2025's slot B was ROBERT LOWERY
        against SUE BERGAN in A, C and D, so a second surname witnessed the
        address; in FY2026 SUE BERGAN fills all four, every value has exactly
        one witness, and nothing ships.

        THAT IS THE RULE WORKING, NOT A LOSS TO FIX. These slots routinely carry
        the filer's OWN office rather than the unit's — Reddick's filed e-mail
        is an outside accountant's (billrodosky.com), which is why no e-mail
        ships either. One person in every slot is exactly the case where an
        address cannot be told apart from that person's own, so it is withheld.
        The FY2026 filing also disagrees with itself on the ZIP (60921 in two
        slots, 60961 in the other two; Reddick is 60961), which is a second
        reason not to ship it unwitnessed.

        So a reader losing that address is a second filer stopping signing the
        form, never anything changing about the fire district. Do not relax this
        to a one-witness rule to win the address back.

        THERE IS A SECOND LOSS SHAPE AND IT IS REDDICK'S MIRROR IMAGE. Metamora
        Public Library District (102/010/10) dropped its telephone from
        woodford-district-officials.json in #1076. Read on 2026-09-22, both
        years through this same parser: the FILER SLOTS ARE IDENTICAL in both,
        Smith / Smith / Weddle / Smith, and what moved is the VALUE. FY2025
        carried (309) 367-4591 in all four, so Smith and Weddle witnessed it.
        FY2026 carries (309) 921-5074 Ext: 101 in A, B and D -- every one of
        them Smith -- against (309) 645-0963 in C, Weddle's, beside his gmail
        address. Each distinct number now has exactly one surname.

        So the two shapes are exact opposites and a reader of a phone loss must
        tell them apart: Reddick kept ONE VALUE and lost a signer, Metamora kept
        BOTH SIGNERS and filed new values. Do not read every loss here as
        who-signed drift.

        WHY CARRYING THE OLD VALUE FORWARD IS WORSE HERE, not merely disallowed.
        The unit's own current filing has REPLACED that number, so preserving it
        would publish a telephone the publisher has superseded -- a wrong answer
        rather than a missing one. Adam's 2026-09-19 ruling that a refusal never
        unpublishes does not reach this case either: the host served fine and
        the publisher gave new information rather than declining to be read.
        Weddle's own number moving to what sits beside his personal gmail is a
        further reason to withhold it.

        THE EXTENSION IS STRIPPED BEFORE WITNESSING (labelled() splits at
        "Ext"), which was measured rather than assumed on 2026-09-22 and the
        current behaviour is right. Stripping can only ever CREATE a match --
        two raw values differing solely by extension become equal -- and never
        break one, since equal raws stay equal. The match it can create is two
        differently-surnamed filers giving the SAME base number at DIFFERENT
        extensions, which is stronger evidence of an institution's switchboard
        than an identical full number is, and a switchboard is exactly what the
        two-witness rule exists to establish. Measured on a 40-unit sample of
        the 509 in afr-special-districts.json, each asked for its OWN latest
        fiscal year: 37 read, 0 filing an extension anywhere, 0 where stripping
        creates a witness the raw values deny. That is a sample and not the
        whole corpus, so it bounds the case rather than closing it -- but
        nothing here licenses relaxing the two-surname rule, which an extension
        does not bear on: one surname is one surname.

        A TRAP THAT COST THIS MEASUREMENT ITS FIRST RUN: most units' latest
        filing is not the current year. Asking all 60 of a first sample for
        FY2026 returned an empty contact block for 46 of them, which reads
        exactly like "this unit files nothing" and is really "not that year" --
        28 of the 37 later read were on FY2025 and only 8 on FY2026. Ask
        latest_fiscal_year() per unit; never hardcode the year.
        """
        for filer in filers:
            value = _flat(filer[field])
            if not value:
                continue
            who = {_surname(other["name"]) for other in filers
                   if _flat(other[field]) == value}
            who.discard("")
            if len(who) >= 2:
                return filer
        return None

    def unit_email():
        """The first e-mail the unit's own name appears in, domain first.

        TWO PASSES, AND THE SECOND IS WHY THE FIRST IS NOT ENOUGH. A domain
        named for the unit is the unit's infrastructure and settles the question
        by itself. But a district with no domain of its own often keeps a role
        mailbox at a provider anyone can use, and three of Logan's seven park
        districts do, two of them naming themselves outright --
        `chestnutbeasonpark@gmail.com` and `sanjoseilparkdistrict@gmail.com` --
        so a domain-only test drops a body's own published address. The local part
        is read only where it carries a word of the unit's name AND not a word
        of the filer's own name, which is what keeps `pigjock76@hotmail.com`
        out and would keep out a hypothetical `carlock@gmail.com` filed by
        somebody surnamed Carlock.

        Mt. Pulaski's `mpparkdist@` stays withheld either way: it abbreviates
        the unit to initials, and this file matches the unit's words, never
        guesses at its initials.
        """
        tokens = unit_tokens(unit_label)
        if not tokens:
            return ""

        def names_the_unit(part):
            """Does this piece of an address name this unit AND its kind?"""
            found = [t for t in tokens if t in part]
            if not found:
                return False
            # A kind word that sits INSIDE the matched name is the name talking,
            # not the mailbox: a district called Liberty would otherwise satisfy
            # `lib` out of its own name.
            return any(kind in part and not any(kind in t for t in found)
                       for kind in UNIT_KIND_WORDS)

        addressed = [f for f in filers if "@" in f["email"]]
        for filer in addressed:
            domain = re.sub(r"[^a-z0-9]", "", filer["email"].rsplit("@", 1)[1].lower())
            if names_the_unit(domain):
                return filer["email"]
        for filer in addressed:
            local = re.sub(r"[^a-z0-9]", "",
                           filer["email"].rsplit("@", 1)[0].lower())
            own = [w for w in _flat(filer["name"]).split() if len(w) >= 3]
            if names_the_unit(local) and not any(w in local for w in own):
                return filer["email"]
        return ""

    address = witnessed("street")
    telephone = witnessed("phone")

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

    def locality():
        """The filed locality and its state/ZIP, with a misfiling corrected.

        The locality and the state/ZIP come from THE SAME SLOT as the street:
        pairing a witnessed street with another filer's town would compose an
        address no filer gave.
        """
        if not address:
            return ""
        filed = (address["city"] or "").strip()
        entry = LOCALITY_CORRECTIONS.get(code)
        if entry and filed == entry[0]:
            warnings.append("%s: locality corrected, filed %r -> shipped %r "
                            "(LOCALITY_CORRECTIONS)" % (code, entry[0], entry[1]))
            filed = entry[1]
        elif entry:
            warnings.append("%s: STALE LOCALITY_CORRECTIONS entry — it expects "
                            "the unit to file %r and the unit now files %r. "
                            "Delete the entry." % (code, entry[0], filed))
        return " ".join(x for x in (filed, address["region"]) if x).strip()

    return {"filedFor": year,
            "street": address["street"] if address else "",
            "city": locality(),
            "phone": telephone["phone"] if telephone else "",
            "email": unit_email(),
            "officers": officers}


def _selftest():
    """Drive contact_block through the real parser, three ways.

    LOCALITY_CORRECTIONS is the one place this module overrides what a unit
    filed, so its three branches are exercised rather than reasoned about: the
    defect is corrected, a unit that fixes its own filing is passed through and
    its entry reported stale, and a unit with no entry is left alone however
    odd its locality looks. Run it after touching that table:

        python3 scripts/comptroller_afr.py --selftest
    """
    global PACE, latest_fiscal_year
    PACE = 0
    latest_fiscal_year = lambda session, code: 2026

    def markup(city):
        def tr(cells):
            return "<tr>" + "".join("<td>%s</td>" % c for c in cells) + "</tr>"
        return "<table>" + "".join([
            tr(["Contact Person", "Chief Executive Officer",
                "Chief Financial Officer", "Purchasing Agent"]),
            tr(["Ann", "Joyce", "Nate", "Brown", "Pat", "Reed", "Dee", "Fox"]),
            tr(["Contact Person", "President", "Treasurer", "Purchasing Agent"]),
            tr(["4631 N Overhill"] * SLOTS),
            tr([city] * SLOTS),
            tr(["IL 60706"] * SLOTS),
            tr(["Phone: (708) 457-1244"] * SLOTS),
            tr(["E-mail: x@example.org"] * SLOTS),
        ]) + "</table>"

    class _Session(object):
        def __init__(self, city):
            self.city = city

        def post(self, *a, **k):
            body = markup(self.city)

            class _R(object):
                text = body

                def raise_for_status(self):
                    pass
            return _R()

    def run(code, city):
        warnings = []
        block = contact_block(_Session(city), code, "SELFTEST UNIT", warnings)
        return (block or {}).get("city"), warnings

    failed = []

    def check(label, got, want):
        if got != want:
            failed.append("%s / got %r / want %r" % (label, got, want))
        print(("  ok   " if got == want else "  FAIL ") + label)

    city, warned = run("016/490/12", "Norrideg")
    check("corrects the misfiled locality", city, "Norridge IL 60706")
    check("prints what it corrected",
          any("locality corrected" in w for w in warned), True)

    city, warned = run("016/490/12", "Norridge")
    check("passes a corrected filing through", city, "Norridge IL 60706")
    check("reports the entry stale", any("STALE" in w for w in warned), True)
    check("does not also claim a correction",
          any("locality corrected" in w for w in warned), False)

    city, warned = run("016/999/99", "Harwood Heights")
    check("leaves an unlisted unit alone", city, "Harwood Heights IL 60706")
    check("says nothing about it", [w for w in warned if "LOCALITY" in w], [])

    if failed:
        print("")
        print("%d CHECK(S) FAILED" % len(failed))
        for f in failed:
            print("  " + f)
        return 1
    print("")
    print("OK - LOCALITY_CORRECTIONS behaves in all three directions")
    return 0


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit("usage: comptroller_afr.py --selftest   (this module is a library)")
