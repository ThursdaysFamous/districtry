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
witnesses a contact value now has to pass. Each officer it ships carries the
telephone that officer's own slot gives, since Adam's ruling of 2026-10-17
("if the official government source uses personal phone numbers, we publish
those"), and the e-mail address it gives, since he chose "E-mails too" the
same day; the end of CONTACT WITNESSES says which numbers and addresses still
ride nobody.

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

import hashlib
import html
import json
import os
import re
import time

import requests  # noqa: F401  (callers pass a session; imported for the dep pin)
from scraper_common import require_robots_once, UA_ROSTER_COMPACT  # noqa: E402  (shared — do not fork)
from undeliverable import withhold  # noqa: E402  (the fleet's one list of dead addresses)

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
# into two people's slots). Withholding a real contact is a cost; shipping one
# person's mailbox as the district's is a false statement about whose it is.
# That reasoning is about the DISTRICT's contact and still governs it. An
# officer's own address is a different question, answered under OFFICER E-MAIL
# below.
#
# ITS KNOWN HOLE IS STATED RATHER THAN PATCHED. Two witnesses means two distinct
# SURNAMES, so a unit filing one person under two spellings of a surname would
# satisfy it -- Eureka Library District files Cindy O'Neill and Cindy O'Neil, and
# Dunlap FPD Jim Winters and Jim Withers. Measured across the 50 filings, no
# address or telephone is admitted on such a pair alone; both those units carry
# two further, plainly distinct witnesses. Nothing here decides that two similar
# names are one person.
#
# AN OFFICER'S OWN TELEPHONE RIDES THAT OFFICER, SINCE 2026-10-17. Each slot
# prints a telephone beside the person it names. Until that day this file
# shipped one only where two differently-surnamed filers gave it, as the
# district's, and withheld the rest because a slot's number may be the
# officer's own home or mobile line. Adam ruled that day, for the whole fleet:
# "if the official government source uses personal phone numbers, we publish
# those." An AFR is filed with a state agency and published by it, so the
# number a slot prints now ships on the officer that slot names, as `phone`,
# whosever line it is, and a different number the same person filed in another
# slot goes in `phonesExtra`, in slot order (officer_phones in contact_block).
# Three things do not change:
#
#   * A NUMBER SOMEBODY ELSE ALSO FILED RIDES NO PERSON. Where a different
#     person -- told apart by full name, not only by surname -- gave the same
#     number (its extension set aside, as the witness test sets it aside), the
#     number is the office's. Two differently-surnamed filers make it the
#     district's telephone exactly as before; two people sharing a surname make
#     it a number printed for two officials, which the fleet's rule also gives
#     to the office. Dunlap FPD files one telephone beside Ann Joyce, Jim
#     Winters and Jim Withers, so it ships as the district's and on none of
#     the three.
#   * ONLY AN OFFICER THIS FILE ALREADY EMITS CARRIES ONE. A slot naming a
#     preparer, an accountant or an employer contact who is not shipped as an
#     officer ships nothing, as before. A slot naming somebody who IS shipped
#     from another slot (Atlanta Memorial files its President in A, B and D)
#     gives its number to the same person.
#   * NO ADDRESS AND NO FAX. An officer's e-mail address follows rules of its
#     own, under OFFICER E-MAIL below.
#
# THE EXTENSION SHIPS WITH AN OFFICER'S NUMBER, because it is part of what the
# filer wrote beside that person: Illinois Prairie District Public Library
# (102/010/10) files its Director's telephone with "Ext: 101" in each of the
# three slots that name the Director (read 2026-10-17). The district's own
# number still ships without an extension, as labelled() has always read it,
# so the witness rule is untouched.
#
# A VALUE THAT IS NOT A TELEPHONE NUMBER SHIPS ON NOBODY. The Phone cell is free
# text, so an officer's number must have the shape of one (OFFICER_PHONE_SHAPE):
# at most one label word the filer typed ("cell", "home", "work" and the like,
# kept as typed), an optional area code, seven digits, an optional extension
# and nothing else -- no street word, no ZIP code, no "@", no second number. A
# value that fails is dropped with a warning naming the unit and the slot and
# never the value, and the builders refuse a payload carrying one
# (suspect_phones_in), so a parse that starts reading the wrong cell stops the
# write rather than publishing it. A number filed with no area code ships as
# filed: none is ever supplied here, because a mobile can be issued anywhere and
# a wrong guess reaches a stranger.
OFFICER_PHONE_SHAPE = re.compile(
    r"^(?:(?:cell|home|work|business|office|mobile|personal|residence)"
    r"\s*:?\s*)?"                                # one label word, as typed
    r"(?:\+?1[\s.-]?)?"                          # a country code, rarely filed
    r"(?:\(\d{3}\)\s*|\d{3}[\s.-]?)?"            # an area code, which may be left off
    r"\d{3}[\s.-]?\d{4}"                         # the number itself
    r"(?:\s*(?:ext\.?|x)\s*:?\s*\d{1,6})?$",     # and an extension
    re.I)
# A number with no area code: seven digits and an optional extension. Counted
# by count_officer_phones so a builder can report one rather than ship it
# unremarked.
NO_AREA_CODE = re.compile(r"^(?:[a-z]+\s*:?\s*)?\d{3}[\s.-]?\d{4}"
                          r"(?:\s*(?:ext\.?|x)\s*:?\s*\d{1,6})?$", re.I)
# The form's extension caption with nothing after it, which a filer who leaves
# the extension box empty can leave behind.
EMPTY_EXTENSION = re.compile(r"\s*Ext\s*:?\s*$", re.I)
# A warning names a slot by its letter, never by the value it carried.
SLOT_LETTERS = "ABCD"

# OFFICER E-MAIL
#
# AN OFFICER'S OWN E-MAIL ADDRESS RIDES THAT OFFICER, SINCE 2026-10-17. Until
# that day no officer's address shipped, because the address a slot prints is
# often the officer's own mailbox at a provider or at an employer. Adam chose
# "E-mails too" that day, extending his telephone ruling to e-mail: an address
# a government publisher prints beside a named official ships on that
# official, whosever mailbox it is. So the address a slot prints beside an
# officer this file emits ships on that officer as `email`, as filed and in
# the case it was filed in (officer_email in contact_block).
#
# THE RULING REMOVED THE OBJECTION THAT AN ADDRESS MIGHT BE PERSONAL. IT DID NOT
# REMOVE THE QUESTION OF WHOSE ADDRESS IT IS, AND THIS FORM ANSWERS THAT WRONGLY
# OFTEN ENOUGH TO MEASURE. A slot is meant to carry its own person's details,
# but whoever types the report fills the slots with what is to hand, and that is
# often the office of whoever prepares the filing. Read on 2026-10-17: Reddick
# Community FPD (053/085/06) names Sue Bergan in all four slots and gives two
# different mailboxes at an outside accountant's domain beside that name,
# neither carrying it; four fire districts on the Grundy County map give one
# accounting firm's `admin@` mailbox beside four different treasurers; Spring
# Bay FPD (102/080/06) gives an address at a bank, named for somebody who is not
# on the filing, beside its Accountant; and Mt. Pulaski Park District
# (054/030/12) gives an address made of its bookkeeper's initial and the first
# letters of the bookkeeper's surname beside its President. So every test here
# is about whose the address is, and none about what kind of mailbox it is:
#
#   * AN ADDRESS IS READ ONLY FROM A SLOT THAT NAMES THE OFFICER. The address
#     in the next slot belongs to the person that slot names -- a preparer, an
#     accountant, another officer -- and never to this one.
#   * AN ADDRESS PRINTED BESIDE TWO DIFFERENT PEOPLE RIDES NEITHER. A filer who
#     copies one account into several people's slots -- april.wagner3953@,
#     above, sits in two -- has not said whose it is. Names are told apart in
#     full, as for a telephone, case and punctuation aside. The builders apply
#     the same test across a roster's filings (drop_mail_given_for_two), which
#     is what catches the accounting firm's mailbox given beside four
#     treasurers in four reports, and across the seven rosters these filings
#     feed (AFR_ROSTERS), which is what catches one personal mailbox given
#     beside a library's President in one county and a fire district's
#     Treasurer in another.
#   * AN ADDRESS NAMED FOR ANOTHER FILER IS NOT THIS OFFICER'S. Where the part
#     before the @ carries a piece of another filer's name (person_tokens: a
#     name word of three letters or more, or an initial with the first three
#     letters of a surname) and no piece that is this officer's alone, the
#     address was filed in the wrong slot: it rides nobody, with a warning
#     naming the unit and the slot.
#   * AN ADDRESS NAMED FOR THE UNIT IS THE UNIT'S. Where the part before the @
#     carries a word of the unit's own name (unit_tokens) and no piece of the
#     officer's name, it is a mailbox the district keeps -- a library's
#     `catlin13@` beside its President -- and a mailbox the district keeps is
#     the office's, so it rides nobody.
#   * THE DISTRICT'S OWN ADDRESS STAYS THE DISTRICT'S. The address unit_email
#     picks ships in the office row, as it always has, and on no person. Where
#     an officer's own address on the unit's domain or a government domain IS
#     that address, the officer carries no second one beside it: the fleet's
#     rule is one address per person, the official one kept.
#   * AN ACCOUNTANT'S OR A BANK'S ADDRESS IS THE FIRM'S. An address with a
#     word naming an accountant or a bank in it (firm_address) rides an officer
#     only where it also carries a piece of that officer's name.
#   * ONE PERSON GIVEN TWO ADDRESSES GETS ONE THAT NAMES THEM, OR NONE. Where
#     the filing gives one officer more than one address, it has not said which
#     is theirs: an address on the unit's own domain or on a government domain
#     is kept, the fleet's rule, and otherwise only one carrying a piece of the
#     officer's own name can ship, the first in slot order. Reddick's two
#     mailboxes ship on nobody this way. Two addresses for one person one
#     character apart ship as neither, warned by slot, because the filing
#     disagrees with itself and one is a typing error.
#   * ONE ADDRESS, SHAPED AS ONE, AND DELIVERABLE. OFFICER_EMAIL_SHAPE admits
#     one address and no space; a cell that fails ships on nobody, warned by
#     unit and slot and never by value, and the builders refuse a payload
#     carrying one (suspect_emails_in). An address undeliverable.py lists stays
#     withheld, as everywhere else. A typing error is never corrected.
#
# WHAT THESE TESTS CANNOT SEE IS STATED RATHER THAN GUESSED AT. An address
# naming nobody -- a handle at a mail provider, which is the commonest shape a
# personal mailbox takes -- ships on the officer whose slot gives it, because
# the form says it is theirs and nothing in the filing says otherwise; a
# preparer's or a relative's handle given in one officer's slot alone looks
# exactly like it, and no test here tells them apart.
#
# WHAT THE TESTS COST IS STATED TOO. Each test that withholds can withhold an
# address that is the officer's own: a treasurer who keeps the district's books
# at their own firm and files that firm's mailbox, a trustee given a mailbox the
# library keeps for their seat (`trustee4@` at a mail provider), and an officer
# given two mailboxes neither of which carries their name. Withholding one costs
# a reader an e-mail link; shipping the wrong one sends a reader's message to
# somebody the filing never said holds the office.
OFFICER_EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
# A government's own domain, which the one-address rule keeps over another.
GOVERNMENT_DOMAIN = re.compile(r"\.(?:gov|mil|us)$", re.I)
# A word naming the kind of firm that prepares a report rather than holds an
# office: an accountant or a bank. `cpa` counts only at the END of one of the
# address's words, alone or before an `s` or digits (`mackcpas`, `redbirdcpa1992`),
# because it also sits inside words that name nothing of the kind -- `sycparks`
# is Sycamore Park District's own domain. See firm_address.
FIRM_WORDS = ("accounting", "bank")
FIRM_CPA = re.compile(r"cpas?\d*$")

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


# A COMMA THE FILER TYPED WHERE A MIDDLE INITIAL'S PERIOD BELONGS, and the
# only character substitution this module makes to a filed name.
#
# MEASURED ON THE FILING THAT FORCED IT (2026-09-27, Walnut Public Library
# District, 006/030/10). Its FY2026 contact table prints the Director's forename
# cell three times and does not agree with itself: `Jaclyn G,` in slots A and C
# and `Jaclyn G.` in slot D. FY2025 printed a THIRD spelling, `Jaclyn G` with no
# punctuation at all, in that same slot D. So the comma is the Comptroller's
# document and not this parser -- both years were read through this same code --
# and one person has been filed three ways across two filings.
#
# WHY NOT VOTE ACROSS THE SLOTS, which is the obvious alternative and is wrong
# here: the corrupted spelling holds TWO of the three populated slots and a
# majority would ship it. Nor is "take the slot that looks right" available --
# slot D is in BOARD_ONLY_SLOTS for the measured duplicate-trap reasons above, so
# a head filed there is deliberately never read, and reopening that to win a
# character back would readmit 27 measured duplicates.
#
# THE RULE IS THEREFORE NARROW AND DECLARED. A comma is rewritten ONLY where it
# sits immediately after a single capital letter that itself sits between a
# given name and a surname. It does not touch a suffix comma, which is the only
# legitimate comma this source files: measured across the 1,622 names in the
# eight AFR-derived rosters on 2026-09-27, exactly two carry a comma at all --
# `Juan Martinez, Jr.` and `John Shea, Jr.` -- and neither matches this pattern.
# It does not touch a surname-first value either (`Auter, Tara`), which is a
# different defect with its own remedy in the Vermilion scraper.
#
# IT IS NEVER SILENT. Every rewrite appends a warning naming both spellings, and
# the weekly run prints its warnings, which is the condition Adam's rule sets for
# correcting a published name at all.
MIDDLE_INITIAL_COMMA = re.compile(r"^(?P<given>.+?)\s+(?P<initial>[A-Z]),\s+(?P<rest>\S.*)$")

# A comma this module will not rewrite and will not ship: anything after it that
# is not one of the suffixes the source genuinely files. `suspect_name` is the
# builders' backstop, not a fixer -- it names the value and lets the caller
# refuse, the way the count guards refuse rather than write.
NAME_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v", "phd", "md", "esq", "cpa"}


# A NAME FILED IN CAPITALS IS SHIPPED IN ORDINARY CASE (Adam, 2026-10-13: "fix
# the formatting of the all caps submissions"). Some filers type the whole form
# in capitals ("MARLIN DONLEY", Kempton Fire Protection District FY2026), and a
# card that prints one district's board in capitals beside another's in mixed
# case reads as two different sources. Only a name with NO lower-case letter is
# touched, so a filer's own mixed-case spelling (McCleary, DeMoss) is never
# second-guessed. Each word is capitalised; "Mc" is the one internal capital
# supplied, as `platinum_canvass.name_case` does, and a letter after an
# apostrophe or hyphen starts a new word (O'Brien, Smith-Jones). A filed
# generational suffix stays in capitals (II, III, IV) and Jr./Sr. take the
# usual case. Prefixes this cannot decide (De-, Van-, La-) are left as plain
# capitalised words rather than guessed.
CAPS_SUFFIXES = {"II", "III", "IV", "V"}


def _case_word(word):
    if word.rstrip(".,") in CAPS_SUFFIXES:
        return word
    out = []
    for i, piece in enumerate(re.split(r"([-'’])", word)):
        if piece in ("-", "'", "’") or not piece:
            out.append(piece)
        elif len(piece) > 3 and piece.upper().startswith("MC"):
            out.append("Mc" + piece[2:].capitalize())
        else:
            out.append(piece.capitalize())
    return "".join(out)


def case_capitals(name):
    """`name` in ordinary case when it was filed with no lower-case letter."""
    if not name or not any(ch.isalpha() for ch in name) \
            or any(ch.islower() for ch in name):
        return name
    return " ".join(_case_word(w) for w in name.split())


def normalise_filed_name(name, unit_label, warnings):
    """A filed name in ordinary case, with a middle initial's comma restored
    to a period.

    Returns the name unchanged when neither applies. Appends a warning naming
    both spellings when either does, so no correction is silent.
    """
    cased = case_capitals(name)
    if cased != name:
        said = ("%s: filed name %r is in capitals; shipped as %r"
                % (unit_label, name, cased))
        if said not in warnings:
            warnings.append(said)
        name = cased
    m = MIDDLE_INITIAL_COMMA.match(name or "")
    if not m:
        return name
    fixed = "%s %s. %s" % (m.group("given"), m.group("initial"), m.group("rest"))
    # ONE LINE PER CORRECTION, NOT ONE PER READ. Every slot's name is built
    # twice -- once for the witness table and once for slot_person -- and a unit
    # can file the same person in three slots, so an unguarded append printed one
    # correction up to six times and read as six separate defects.
    said = ("%s: filed name %r carries a comma after the middle initial; "
            "shipped as %r" % (unit_label, name, fixed))
    if said not in warnings:
        warnings.append(said)
    return fixed


def suspect_name(name):
    """Why a name must not ship, or None.

    The one shape checked is a comma whose right-hand side is not a filed
    suffix, because `normalise_filed_name` has already restored the middle
    initial's period and any comma left over is unexplained.
    """
    if "," not in (name or ""):
        return None
    tail = name.split(",", 1)[1].strip().rstrip(".").lower()
    if tail.split(" ")[0] in NAME_SUFFIXES:
        return None
    return ("a comma that is not a filed suffix, so the surname or the middle "
            "initial is not as the filer typed it")


def suspect_names_in(payload):
    """[(where, name, why)] for every name in a payload that must not ship.

    A WALKER RATHER THAN A LOOP PER BUILDER. The eight rosters this parser feeds
    nest their officers three different ways -- the library file keys them by
    library, five county files by district, and the special-district file by
    county then layer then name -- so a per-builder loop would be eight copies of
    one question, which is where this fleet's recurring defect starts. This walks
    whatever shape it is given and names the path it found the value at.

    `where` is the dotted path to the officer's own record, so a refusal names
    the district and the group rather than only the person.
    """
    found = []

    def walk(node, path):
        if isinstance(node, dict):
            name = node.get("name")
            if isinstance(name, str) and name.strip():
                why = suspect_name(name)
                if why:
                    found.append((path or "payload", name, why))
            for key, value in node.items():
                if key != "name":
                    walk(value, "%s.%s" % (path, key) if path else str(key))
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, "%s[%d]" % (path, i))

    walk(payload, "")
    return found


def one_digit_apart(a, b):
    """Are two digit strings one typing error apart?

    The same length, and either one digit different or two neighbouring
    digits swapped. Equal strings are not: those are one number.
    """
    if len(a) != len(b) or a == b:
        return False
    differ = [i for i in range(len(a)) if a[i] != b[i]]
    if len(differ) == 1:
        return True
    return (len(differ) == 2 and differ[1] == differ[0] + 1
            and a[differ[0]] == b[differ[1]] and a[differ[1]] == b[differ[0]])


def one_typo_apart(a, b):
    """Are two strings one typing error apart?

    One character different, added or dropped, or two neighbouring characters
    swapped. Equal strings are not: those are one value.
    """
    if a == b:
        return False
    if len(a) == len(b):
        return one_digit_apart(a, b)
    short, long_ = sorted((a, b), key=len)
    if len(long_) - len(short) != 1:
        return False
    return any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))


OFFICER_LISTS = ("board", "heads")


def _officer_records(payload):
    """(path, record) for every officer record in a payload, whatever its nesting.

    An officer record is an item of a `board` or `heads` list, which is where
    contact_block's two lists land in all eight rosters this parser feeds; the
    district's own `office` is not an officer and is not visited.
    """
    found = []

    def walk(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                here = "%s.%s" % (path, key) if path else str(key)
                if key in OFFICER_LISTS and isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            found.append(("%s[%d]" % (here, i), item))
                else:
                    walk(value, here)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, "%s[%d]" % (path, i))

    walk(payload, "")
    return found


def suspect_phones_in(payload):
    """[(where, why)] for every officer telephone in a payload that must not ship.

    The builders' backstop for officer_phones, refusing a write the way
    suspect_names_in does. Each `phone` and each `phonesExtra` entry must match
    OFFICER_PHONE_SHAPE, and `phonesExtra` must be a list of strings. `where`
    names the district and the officer's place in its list; the value itself is
    never named, so a refusal cannot print a number or an address into a log.
    """
    found = []
    for where, record in _officer_records(payload):
        values = []
        if "phone" in record:
            values.append(("phone", record["phone"]))
        if "phonesExtra" in record:
            extra = record["phonesExtra"]
            if not isinstance(extra, list) or not extra:
                found.append((where, "phonesExtra is not a non-empty list"))
                extra = []
            values.extend(("phonesExtra[%d]" % i, v) for i, v in enumerate(extra))
        for field, value in values:
            if not isinstance(value, str) or not OFFICER_PHONE_SHAPE.match(value):
                found.append((where, "%s is not shaped like one telephone number"
                              % field))
    return found


def count_officer_phones(payload):
    """Officer records in a payload, and how many carry a telephone.

    Returns {"officers", "withPhone", "withSecond", "noAreaCode"}: every record
    in a board or heads list, those carrying `phone`, those also carrying
    `phonesExtra`, and the numbers (first or further) filed without an area
    code. A district filed under two counties is counted once per copy, as the
    file holds it.
    """
    out = {"officers": 0, "withPhone": 0, "withSecond": 0, "noAreaCode": 0}
    for _where, record in _officer_records(payload):
        out["officers"] += 1
        if record.get("phone"):
            out["withPhone"] += 1
        if record.get("phonesExtra"):
            out["withSecond"] += 1
        for value in [record.get("phone")] + list(record.get("phonesExtra") or []):
            if isinstance(value, str) and NO_AREA_CODE.match(value):
                out["noAreaCode"] += 1
    return out


def suspect_emails_in(payload):
    """[(where, why)] for every officer e-mail in a payload that must not ship.

    The builders' backstop for officer_email, as suspect_phones_in is for
    officer_phones: each officer's `email` must be one string shaped like one
    address (OFFICER_EMAIL_SHAPE). `where` names the district and the
    officer's place in its list, and the value is never named.
    """
    found = []
    for where, record in _officer_records(payload):
        if "email" not in record:
            continue
        value = record["email"]
        if not isinstance(value, str) or not OFFICER_EMAIL_SHAPE.match(value):
            found.append((where, "email is not shaped like one address"))
    return found


def count_officer_emails(payload):
    """Officer records in a payload, and how many carry an e-mail address.

    Returns {"officers", "withEmail"}, counted as count_officer_phones counts:
    a district filed under two counties is counted once per copy.
    """
    out = {"officers": 0, "withEmail": 0}
    for _where, record in _officer_records(payload):
        out["officers"] += 1
        if record.get("email"):
            out["withEmail"] += 1
    return out


def person_tokens(name):
    """The pieces of a filed name an e-mail address can carry.

    Each name word of three letters or more, the first initial with the first
    three letters of the surname, and the first three letters of the given name
    with the surname's initial: Kathy Letterle gives `kathy`, `letterle`,
    `klet` and `katl`. Apostrophes and periods are dropped first (O'Brien is
    `obrien`), and a suffix the source files (NAME_SUFFIXES) is not taken for
    a surname.
    """
    words = re.sub(r"[^a-z]+", " ",
                   re.sub(r"['\u2019.]", "", (name or "").lower())).split()
    while len(words) > 1 and words[-1] in NAME_SUFFIXES:
        words.pop()
    out = {w for w in words if len(w) >= 3}
    if len(words) >= 2:
        given, surname = words[0], words[-1]
        if len(surname) >= 3:
            out.add(given[0] + surname[:3])
        if len(given) >= 3:
            out.add(given[:3] + surname[0])
    return out


def local_letters(value):
    """The letters of the part of an address before the @, lowercased."""
    return re.sub(r"[^a-z]", "", (value or "").rsplit("@", 1)[0].lower())


def firm_address(value):
    """Does an address carry a word naming an accountant or a bank?

    Its words are what lies between the characters that are not a letter or a
    digit, on both sides of the @: `office@doecpas.com` gives `office`,
    `doecpas` and `com`, and `doecpas` ends in `cpas`.
    """
    words = re.split(r"[^a-z0-9]+", (value or "").lower())
    return any(any(firm in word for firm in FIRM_WORDS) or FIRM_CPA.search(word)
               for word in words if word)


# THE SEVEN ROSTERS BUILT FROM THESE FILINGS. An address one of them gives
# beside one person and another gives beside a different person is nobody's in
# either (drop_mail_given_for_two), so each builder reads the other six as
# shipped (mail_elsewhere).
AFR_ROSTERS = ("il-library-district-officials.json",
               "il-special-district-officials.json",
               "logan-district-officials.json", "peoria-district-officials.json",
               "woodford-district-officials.json", "grundy-district-officials.json",
               "kankakee-district-officials.json")
# WHERE A ROSTER RECORDS WHAT IT TOOK OFF, so the others can still see it once
# it is gone. Without it the rosters disagree by build order: the first to see
# a conflict takes the address off its own officer, and the other, built later,
# finds it nowhere and keeps it on its own. Each entry is a digest of the
# address (mail_digest) and digests of the names the roster's own filings gave
# it beside; nothing is written out, and nothing reads the entry but the
# builders.
MAIL_GIVEN_FOR_TWO = "mailGivenForTwo"


def mail_digest(text):
    """The first 16 hex digits of the SHA-256 of `text`, so two rosters can
    compare an address, or a name as _flat reduces it, without writing it out."""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def mail_elsewhere(app_dir, own):
    """{address digest: {name digests}} from every AFR roster but `own`, as
    shipped in `app_dir`: each address an officer there carries, beside that
    officer's name, and each address that roster took off as given for two
    (MAIL_GIVEN_FOR_TWO), beside the names its own filings gave it. A roster not
    yet shipped contributes nothing."""
    seen = {}
    for fname in AFR_ROSTERS:
        path = os.path.join(app_dir, fname)
        if fname == own or not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
        for _where, record in _officer_records(payload):
            value = record.get("email")
            flat = _flat(record.get("name"))
            if isinstance(value, str) and value and flat:
                seen.setdefault(mail_digest(value.casefold()), set()).add(
                    mail_digest(flat))
        for key, names in (payload.get(MAIL_GIVEN_FOR_TWO) or {}).items():
            seen.setdefault(key, set()).update(names)
    return seen


def drop_mail_given_for_two(payload, elsewhere=None, withheld=None):
    """Take every officer address that rides two differently-named officers off
    all of them, across a whole roster and, given `elsewhere`, across the other
    AFR rosters too. Returns the number of records changed.

    contact_block already keeps an address printed beside two people in ONE
    report off both; this is the same rule across reports, because one
    accounting firm's mailbox typed beside a different treasurer in each of
    four districts' filings is no treasurer's. Names are compared as
    already_named compares them, case and punctuation aside, so one person
    filed by two districts, or the same district copied into two counties,
    keeps an address the same name gives both times. `elsewhere` is
    mail_elsewhere's answer for the other rosters; `withheld`, a dict, receives
    an entry for every address taken off, which the builder writes under
    MAIL_GIVEN_FOR_TWO.
    """
    records = _officer_records(payload)
    names = {}
    for _where, record in records:
        value = record.get("email")
        if isinstance(value, str) and value:
            mine = names.setdefault(value.casefold(), set())
            flat = _flat(record.get("name"))
            if flat:
                mine.add(mail_digest(flat))
    shared = set()
    for key, mine in names.items():
        digest = mail_digest(key)
        if len(mine | (elsewhere or {}).get(digest, set())) > 1:
            shared.add(key)
            if withheld is not None:
                withheld[digest] = sorted(mine)
    dropped = 0
    for _where, record in records:
        value = record.get("email")
        if isinstance(value, str) and value.casefold() in shared:
            record.pop("email")
            dropped += 1
    return dropped


def line_digits(value):
    """A telephone's digits with any extension and a leading 1 removed.

    What two printings of one line have in common: "(309) 555-0114 Ext: 101"
    and "309.555.0114" both give "3095550114". A number filed without an area
    code gives seven digits.
    """
    head = re.split(r"(?i)\s*(?:ext\.?|x)\s*:?\s*\d", value or "", maxsplit=1)[0]
    digits = re.sub(r"\D", "", head)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def same_line(a, b):
    """Are two digit strings from line_digits the same line?

    Equal, or one has no area code and its seven digits end the other.
    """
    if not a or not b:
        return False
    if a == b:
        return True
    short, long_ = sorted((a, b), key=len)
    return len(short) == 7 and len(long_) == 10 and long_.endswith(short)


def drop_lines_from_officers(entry, lines):
    """Take a body's own telephone lines off its officers. Returns the count.

    An officer's number that is the same line as one the body publishes as its
    own -- the office telephone a second publisher prints for it, such as the
    library systems' directory -- belongs to the office and not the person
    (the rule set with Adam's ruling of 2026-10-17), so it rides nobody, as no
    officer's number did before that ruling. officer_phones() already keeps
    the filing's own district number off every officer; this is for a line
    the filing does not show to be the body's and another publisher does.
    """
    lines = [line_digits(v) for v in lines if v]
    lines = [d for d in lines if d]
    dropped = 0
    for bucket in OFFICER_LISTS:
        for person in entry.get(bucket) or []:
            if not isinstance(person, dict):
                continue
            numbers = [n for n in [person.get("phone")]
                       + list(person.get("phonesExtra") or []) if n]
            kept = [n for n in numbers
                    if not any(same_line(line_digits(n), d) for d in lines)]
            if len(kept) == len(numbers):
                continue
            dropped += len(numbers) - len(kept)
            person.pop("phone", None)
            person.pop("phonesExtra", None)
            if kept:
                person["phone"] = kept[0]
            if len(kept) > 1:
                person["phonesExtra"] = kept[1:]
    return dropped


def drop_mail_from_officers(entry, addresses):
    """Take a body's own e-mail addresses off its officers. Returns the count.

    The e-mail counterpart of drop_lines_from_officers: an officer's address
    that is one a second publisher prints as the body's own office address
    -- Lake County's GIS carries one on each fire and park district, and the
    card prints it in the district's own contact row -- belongs to the office
    and rides nobody. Compared without regard to case.
    """
    wanted = {a.strip().casefold() for a in addresses if a and a.strip()}
    dropped = 0
    for bucket in OFFICER_LISTS:
        for person in entry.get(bucket) or []:
            if isinstance(person, dict) and person.get("email") \
                    and person["email"].casefold() in wanted:
                person.pop("email")
                dropped += 1
    return dropped


# The two shipped files a library card reads its office telephone from.
LIBRARY_DIRECTORY = "il-library-contacts.json"
LIBRARY_FILINGS = "il-library-district-officials.json"


def library_directory_lines(app_dir):
    """Each library's telephone in the library systems' shared directory.

    Returns ({library name: telephone}, {comptroller code: telephone}). The app
    prints the directory's telephone as the library's own office line, on the
    statewide library card (withLibraryOfficials) and on a county library card
    whose filing gives no district telephone (withCountyLibraryPhone), so an
    officer's number that is the same line belongs to the library and rides
    nobody (drop_lines_from_officers). Names join the statewide file; a county
    file's library joins by comptroller code through LIBRARY_FILINGS, the join
    withCountyLibraryPhone makes. A missing or unreadable file raises: a
    builder that cannot see the library's line cannot tell an officer's number
    apart from it.
    """
    with open(os.path.join(app_dir, LIBRARY_DIRECTORY), encoding="utf-8") as fh:
        directory = json.load(fh).get("libraries") or {}
    with open(os.path.join(app_dir, LIBRARY_FILINGS), encoding="utf-8") as fh:
        filings = json.load(fh).get("libraries") or {}
    if not directory or not filings:
        raise ValueError("%s or %s holds no libraries"
                         % (LIBRARY_DIRECTORY, LIBRARY_FILINGS))
    by_name = {name: rec["phone"] for name, rec in directory.items()
               if isinstance(rec, dict) and rec.get("phone")}
    by_code = {}
    for name, rec in filings.items():
        code = (rec or {}).get("comptrollerCode")
        if code and name in by_name:
            by_code[code] = by_name[name]
    return by_name, by_code


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
    require_robots_once(SEARCH_FORM, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-comptroller-afr")
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
    require_robots_once(WAREHOUSE + "landingpage", HEADERS["User-Agent"], headers=HEADERS,
                        label="il-comptroller-afr")
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

    def filed_phone(slot):
        """Slot `slot`'s telephone as filed, extension and all.

        The officer's number, and only the officer's: the witness test and the
        district's number go on reading labelled(), which drops the extension,
        so nothing about the district rule moves. An empty extension caption
        is cut and runs of spaces closed up; nothing else is touched.
        """
        for x in quad:
            if x[slot].startswith("Phone:"):
                value = " ".join(x[slot][len("Phone:"):].split())
                return EMPTY_EXTENSION.sub("", value).strip()
        return ""

    def cell(rows, index, slot):
        return rows[index][slot].strip() if len(rows) > index else ""

    # EVERY SLOT IS READ, because each carries its own filer's details and the
    # one the unit can be shown to own is not always slot A.
    def filed_name(i):
        """Slot i's name as filed, with a middle initial's comma restored.

        BOTH READERS OF THE NAME GO THROUGH HERE -- the witness table below and
        slot_person() -- because a name corrected in one and not the other would
        make `already_named` and the witnessing disagree about one person.
        """
        joined = " ".join(x for x in (names[2 * i], names[2 * i + 1]) if x).strip()
        return normalise_filed_name(joined, unit_label, warnings)

    def filed_email(slot):
        """Slot `slot`'s e-mail cell as filed, runs of spaces closed up.

        labelled() cuts a value at "Ext", which is right for a telephone and
        wrong for an address that happens to carry those three letters, so an
        address is read whole here, for the district and the officer alike.
        """
        for x in quad:
            if x[slot].startswith("E-mail:"):
                return " ".join(x[slot][len("E-mail:"):].split())
        return ""

    filers = [{"name": filed_name(i),
               "street": cell(unlabelled, 0, i),
               "city": cell(unlabelled, 1, i),
               "region": cell(unlabelled, 2, i),
               "phone": labelled("Phone:", i),
               "email": filed_email(i)}
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

        THERE IS A SECOND LOSS SHAPE AND IT IS REDDICK'S MIRROR IMAGE. The library
        district filing as 102/010/10 dropped its telephone from
        woodford-district-officials.json in #1076. IT HAS TWO NAMES IN THIS
        REPO AND BOTH ARE CORRECT: Woodford County's own parcel fabric calls it
        `IL Prairie Library District` (code LYIL), which is what the boundary
        file and that county roster use, while the library's own state
        directory and its AFR filing call it `Illinois Prairie District Public
        Library`. Two publishers naming one body, not a defect -- so neither
        file is renamed to match the other. An earlier draft of this paragraph
        called it "Metamora Public Library District" -- a name NEITHER PUBLISHER
        USES, supplied from the town in the filing's address by a reader who had
        the code, the office and the head in front of them but not the key.
        Cite a unit by its comptroller code, which is the one identifier both
        publishers share. Read on 2026-09-22, both
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
        Weddle's own number moving to what sits beside his personal gmail was a
        further reason to withhold it AS THE DISTRICT'S, and still is. Since
        Adam's ruling of 2026-10-17 it ships on Weddle's own record instead,
        as the number the filing prints beside him (officer_phones), and the
        Director's number with its extension ships on the Director's.

        THE EXTENSION IS STRIPPED BEFORE WITNESSING (labelled() splits at
        "Ext"), which was measured rather than assumed on 2026-09-22 and the
        current behaviour is right. Stripping can only ever CREATE a match --
        two raw values differing solely by extension become equal -- and never
        break one, since equal raws stay equal. The match it can create is two
        differently-surnamed filers giving the SAME base number at DIFFERENT
        extensions, which is stronger evidence of an institution's switchboard
        than an identical full number is, and a switchboard is exactly what the
        two-witness rule exists to establish.

        MEASURED TWICE, BECAUSE THE FIRST SAMPLE WAS DRAWN FROM THE WRONG
        INVENTORY. afr-special-districts.json holds FIRE (323) and PARK (186)
        districts and NO libraries at all, so a 40-unit sample of it read 37
        and found 0 extensions -- a clean zero for something that does not
        occur in that population, measured while the documented case is a
        LIBRARY district outside it. Sampling the 198 library districts that
        carry a comptroller code instead: 40 sampled, all 40 read, 2 filing an
        extension -- Illinois Prairie District Public Library, which IS
        102/010/10 above, and Kewanee Public Library District at
        (309) 853-3333 Ext: 1136. Across both populations, 77 units read and 0
        where stripping creates a witness the raw values deny. These are
        samples rather than the whole corpus, so they bound the case rather
        than closing it -- but nothing here licenses relaxing the two-surname
        rule, which an extension does not bear on: one surname is one surname.

        A SAMPLE INHERITS ITS INVENTORY'S SCOPE, which is the transferable
        part: a zero measured over a population the phenomenon cannot appear in
        reads exactly like a zero measured over one where it could. Check that
        the inventory you sample contains the case you are reasoning about.

        A TRAP THAT COST THIS MEASUREMENT ITS FIRST RUN: most units' latest
        filing is not the current year. Asking all 60 of a first sample for
        FY2026 returned an empty contact block for 46 of them, which reads
        exactly like "this unit files nothing" and is really "not that year" --
        28 of the 37 later read were on FY2025 and only 8 on FY2026. Ask
        latest_fiscal_year() per unit; never hardcode the year.

        ONE FILING REACHES SEVERAL COUNTY ROSTERS, ON SEVERAL WEEKS' RUNS, and
        that is a rule about REVIEW rather than about this function. A
        cross-county district files once under its home county and is stamped
        onto every county whose polygons draw it, each by that county's own
        weekly job: Reddick Community FPD (053/085/06) is in both
        grundy-district-officials.json and kankakee-district-officials.json,
        and Fossil Ridge Public Library District likewise. #1023 took Grundy's
        copy to the FY2026 filing on 2026-09-19 and #1053 took Kankakee's four
        days later, so a reading merged with a caveat on one PR was already
        shipped on a second before the caveat was answered (it was answered on
        2026-09-21 by the Reddick paragraph above, and it held). SO A PR
        TOUCHING ONE COUNTY'S COPY UNDERSTATES ITS REACH: read the unit, not
        the county, and expect the same diff in a sibling county's PR next
        week.

        check_roster_retention.py cannot see this and is not at fault for it.
        One district losing an office is one record of twenty, which is under
        MIN_ABSOLUTE_DROP and under RECORD_COLLAPSE_RATIO by design -- that
        gate's own docstring says a member leaving moves these by ones and
        twos. The guard here is the two-witness rule plus a reader who knows
        the unit spans counties; there is no threshold that catches it without
        firing on every ordinary turnover.
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

    tokens = unit_tokens(unit_label)

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
        if not tokens:
            return ""
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
    district_email = unit_email()

    def officer_phones(name):
        """Every telephone the filing prints beside `name` alone, in slot order.

        A slot is this officer's when its filed name is the same once case and
        punctuation are set aside -- the comparison already_named() makes, so
        "Trace Evans" in B and "trace evans" in D are one person here as there.
        A number another name also filed (its extension set aside, as the
        witness test sets it aside) is the office's and is skipped: that covers
        the district's own telephone, which two different surnames gave by
        definition, and a number two people of one surname share. A value
        that is not shaped like a telephone number is skipped with a warning
        naming the unit and the slot, never the value.

        TWO NUMBERS FOR ONE PERSON THAT DIFFER BY A SINGLE DIGIT, or by two
        neighbouring digits swapped, ship as neither. That is the filing
        disagreeing with itself about one number, and one of the two is a
        typing error that would ring a stranger. Which one cannot be told from
        the filing, and counting slots is no answer -- Benson Fire (102/010/06)
        files its Treas./Admin.'s telephone one way in slots C and D and with
        its fourth digit different in slot A, and a copied slot carries a typo
        as easily as the right number, which is why filed names are never
        voted on either (MIDDLE_INITIAL_COMMA). The warning names the unit and
        the slots, never the values.
        """
        me = _flat(name)
        out, seen = [], set()
        for slot, filer in enumerate(filers):
            if _flat(filer["name"]) != me:
                continue
            base = _flat(filer["phone"])
            if not base or base in seen:
                continue
            others = {_flat(other["name"]) for other in filers
                      if _flat(other["phone"]) == base}
            others.discard(me)
            others.discard("")
            if others:
                continue
            value = filed_phone(slot)
            if not OFFICER_PHONE_SHAPE.match(value):
                said = ("%s: slot %s files a telephone that is not shaped like "
                        "a telephone number; it ships on nobody"
                        % (unit_label, SLOT_LETTERS[slot]))
                if said not in warnings:
                    warnings.append(said)
                continue
            seen.add(base)
            out.append((slot, value, re.sub(r"\D", "", base)))
        clash = {i for i, a in enumerate(out) for j, b in enumerate(out)
                 if i != j and one_digit_apart(a[2], b[2])}
        if clash:
            said = ("%s: slots %s file telephones for one person that differ by "
                    "one digit; neither ships"
                    % (unit_label, ", ".join(SLOT_LETTERS[out[i][0]]
                                             for i in sorted(clash))))
            if said not in warnings:
                warnings.append(said)
        return [value for i, (_slot, value, _d) in enumerate(out) if i not in clash]

    def names_another_filer(value, name):
        """Is `value` named for another filer of this report rather than `name`?

        True where the part before the @ carries a piece of another filer's
        name (person_tokens) that `name` does not share, and no piece that is
        `name`'s alone. Two filers sharing a surname share its pieces, so they
        decide nothing between them and a given name has to.
        """
        local = local_letters(value)
        me = _flat(name)
        mine = person_tokens(name)
        theirs = set()
        for other in filers:
            flat = _flat(other["name"])
            if flat and flat != me:
                theirs |= person_tokens(other["name"])
        return (any(t in local for t in theirs - mine)
                and not any(t in local for t in mine - theirs))

    def official(value):
        """Is `value` on the unit's own domain or on a government domain?"""
        domain = re.sub(r"[^a-z0-9]", "", value.rsplit("@", 1)[1].lower())
        return bool(names_the_unit(domain) or GOVERNMENT_DOMAIN.search(value))

    def officer_email(name):
        """The one e-mail address the filing gives `name` alone, or "".

        See OFFICER E-MAIL for each test and why it is there. A slot is this
        officer's when its filed name is the same once case and punctuation
        are set aside, as for a telephone; addresses are compared without
        regard to case, and the one that ships is the case it was filed in.
        """
        me = _flat(name)
        mine = person_tokens(name)

        def names_officer(value):
            return any(t in local_letters(value) for t in mine)

        def names_unit_only(value):
            local = local_letters(value)
            return any(t in local for t in tokens) and not names_officer(value)

        found, seen = [], set()
        for slot, filer in enumerate(filers):
            if _flat(filer["name"]) != me:
                continue
            value = filer["email"]
            key = value.casefold()
            if not value or key in seen:
                continue
            seen.add(key)
            others = {_flat(other["name"]) for other in filers
                      if other["email"].casefold() == key}
            others.discard(me)
            others.discard("")
            if others:
                continue
            if not OFFICER_EMAIL_SHAPE.match(value):
                said = ("%s: slot %s files an e-mail that is not shaped like "
                        "one address; it ships on nobody"
                        % (unit_label, SLOT_LETTERS[slot]))
                if said not in warnings:
                    warnings.append(said)
                continue
            if names_another_filer(value, name):
                said = ("%s: slot %s files an e-mail named for another filer "
                        "of the same report; it ships on nobody"
                        % (unit_label, SLOT_LETTERS[slot]))
                if said not in warnings:
                    warnings.append(said)
                continue
            found.append((slot, value))
        district = district_email.casefold()
        if any(value.casefold() == district and official(value)
               for _slot, value in found):
            return ""
        several = len(found) > 1
        found = [(slot, value) for slot, value in found
                 if value.casefold() != district and not names_unit_only(value)]
        clash = {i for i, a in enumerate(found) for j, b in enumerate(found)
                 if i != j and one_typo_apart(a[1].casefold(), b[1].casefold())}
        if clash:
            said = ("%s: slots %s file e-mail addresses for one person that "
                    "differ by one character; neither ships"
                    % (unit_label, ", ".join(SLOT_LETTERS[found[i][0]]
                                             for i in sorted(clash))))
            if said not in warnings:
                warnings.append(said)
        kept = [value for i, (_slot, value) in enumerate(found) if i not in clash]
        kept = [value for value in kept if withhold(value, unit_label)[0]]
        chosen = [value for value in kept if official(value)]
        if not chosen:
            chosen = [value for value in kept if names_officer(value)
                      or not (several or firm_address(value))]
        return chosen[0] if chosen else ""

    def officer(name, title):
        """An officer's record: the name and filed title, and the officer's
        own telephone and e-mail address where the filing gives them (see
        officer_phones and officer_email)."""
        record = {"name": name, "role": title}
        numbers = officer_phones(name)
        if numbers:
            record["phone"] = numbers[0]
        if len(numbers) > 1:
            record["phonesExtra"] = numbers[1:]
        email = officer_email(name)
        if email:
            record["email"] = email
        return record

    def slot_person(slot):
        name = filed_name(slot)
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
            officers.append(("board", officer(name, title)))
        else:
            if key not in HEAD_TITLES:
                warnings.append("%s: filed title %r for %s is neither a board "
                                "office nor a recognised appointed post — "
                                "shipped as appointed, never as a board seat"
                                % (unit_label, title, name))
            officers.append(("heads", officer(name, title)))

    # The second pass, over the filing's administrative slots. A board-titled
    # person the unit has not already named is a trustee it would otherwise have
    # left invisible; everything else in these slots is skipped. See
    # BOARD_ONLY_SLOTS for what this admits and what it deliberately does not.
    for slot in BOARD_ONLY_SLOTS:
        name, title, key = slot_person(slot)
        if not name or key not in BOARD_TITLES or already_named(name):
            continue
        officers.append(("board", officer(name, title)))

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
            "email": district_email,
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

    def markup(city, name_row=None, phones=None, emails=None):
        def tr(cells):
            return "<tr>" + "".join("<td>%s</td>" % c for c in cells) + "</tr>"
        return "<table>" + "".join([
            tr(["Contact Person", "Chief Executive Officer",
                "Chief Financial Officer", "Purchasing Agent"]),
            tr(name_row or
               ["Ann", "Joyce", "Nate", "Brown", "Pat", "Reed", "Dee", "Fox"]),
            tr(["Contact Person", "President", "Treasurer", "Purchasing Agent"]),
            tr(["4631 N Overhill"] * SLOTS),
            tr([city] * SLOTS),
            tr(["IL 60706"] * SLOTS),
            tr(["Phone: " + p for p in (phones or ["(708) 457-1244"] * SLOTS)]),
            tr(["Fax: (708) 457-9999"] * SLOTS),
            tr(["E-mail: " + e for e in (emails or ["x@example.org"] * SLOTS)]),
        ]) + "</table>"

    class _Session(object):
        def __init__(self, city, name_row=None, phones=None, emails=None):
            self.city = city
            self.name_row = name_row
            self.phones = phones
            self.emails = emails

        def post(self, *a, **k):
            body = markup(self.city, self.name_row, self.phones, self.emails)

            class _R(object):
                text = body

                def raise_for_status(self):
                    pass
            return _R()

    def run(code, city, name_row=None):
        warnings = []
        block = contact_block(_Session(city, name_row), code, "SELFTEST UNIT",
                              warnings)
        return (block or {}).get("city"), warnings

    def officers(name_row):
        """(the officers shipped, the warnings) for one name row.

        Drives the REAL contact_block rather than calling the normaliser, so a
        name corrected in one of its two readers and not the other fails here.
        """
        warnings = []
        block = contact_block(_Session("Norridge", name_row), "016/999/99",
                              "SELFTEST UNIT", warnings)
        return [o[1]["name"] for o in (block or {}).get("officers") or []], warnings

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

    # THE MIDDLE-INITIAL COMMA, in all four directions. The real filing that
    # forced it (Walnut Public Library District FY2026) puts the comma in the
    # CFO slot, which is a published slot, so that is the slot driven here.
    got, warned = officers(["Jaclyn G,", "Trujillo", "Brenda", "Helms",
                            "Jaclyn G,", "Trujillo", "Dee", "Fox"])
    check("ships the middle initial's comma as a period",
          [n for n in got if "Trujillo" in n], ["Jaclyn G. Trujillo"])
    check("never ships the comma spelling",
          any("Jaclyn G," in n for n in got), False)
    check("prints the correction it made",
          len([w for w in warned if "comma after the middle initial" in w]), 1)

    # SLOT C, a PUBLISHED slot whose fixture title is Treasurer. A first draft
    # put this in slot A and the check failed for the right reason: A is in
    # BOARD_ONLY_SLOTS, so a name filed there ships only under a board title.
    got, _ = officers(["Ann", "Joyce", "Brenda", "Helms",
                       "Juan", "Martinez, Jr.", "Dee", "Fox"])
    check("leaves a filed suffix comma alone",
          [n for n in got if "Martinez" in n], ["Juan Martinez, Jr."])
    check("and does not call a filed suffix suspect",
          suspect_name("Juan Martinez, Jr."), None)

    # CAPITALS, cased and printed; a filer's own mixed case left alone.
    got, warned = officers(["MARLIN", "DONLEY", "Brenda", "Helms",
                            "ROGER", "GUALANDI", "Dee", "Fox"])
    # Slot C is a published slot (slot A ships only under a board title).
    check("ships a name filed in capitals in ordinary case",
          [n for n in got if "GUALANDI" in n.upper()], ["Roger Gualandi"])
    check("never ships the capitals spelling",
          any(n in ("MARLIN DONLEY", "ROGER GUALANDI") for n in got), False)
    check("prints the casing it applied",
          any("is in capitals" in w for w in warned), True)
    for raw, want in (("SCOTT MCDONALD", "Scott McDonald"),
                      ("MARY O'BRIEN-SMITH", "Mary O'Brien-Smith"),
                      ("JOHN SHEA, JR.", "John Shea, Jr."),
                      ("JAMES DOE III", "James Doe III"),
                      ("Ann DeMoss", "Ann DeMoss"),
                      ("Ric Warhol", "Ric Warhol")):
        check("cases %r as %r" % (raw, want), case_capitals(raw), want)

    check("calls an unexplained comma suspect",
          suspect_name("Jaclyn G, Trujillo") is not None, True)
    check("calls a surname-first value suspect",
          suspect_name("Auter, Tara") is not None, True)

    # AN OFFICER'S OWN TELEPHONE (Adam's ruling of 2026-10-17). Driven through
    # the real contact_block, with the fixture's fax row present in every case
    # so a fax riding anybody would show here.
    def people(name_row, phones, emails=None):
        """(officers by name, the district's telephone, the warnings)."""
        warnings = []
        block = contact_block(_Session("Norridge", name_row, phones, emails),
                              "016/999/99", "SELFTEST UNIT", warnings) or {}
        shipped = {}
        for _bucket, record in block.get("officers") or []:
            shipped.setdefault(record["name"], []).append(
                {k: v for k, v in record.items() if k not in ("name", "role")})
        return shipped, block.get("phone"), warnings

    # Illinois Prairie's FY2026 shape, with made-up numbers in the 555-01xx
    # range: one person in A, B and D with an extension, a second person
    # alone in C with a different number.
    got, district, warned = people(
        ["Ann", "Joyce", "Ann", "Joyce", "Cal", "Moss", "Ann", "Joyce"],
        ["(309) 555-0114 Ext: 101", "(309) 555-0114 Ext: 101",
         "(309) 555-0115", "(309) 555-0114 Ext: 101"])
    check("an officer's own number rides that officer, extension and all",
          got.get("Ann Joyce"), [{"phone": "(309) 555-0114 Ext: 101"}])
    check("a second officer's own number rides that officer",
          got.get("Cal Moss"), [{"phone": "(309) 555-0115"}])
    check("and neither is the district's", district, "")
    check("no fax rides anybody",
          any("9999" in str(r) for rs in got.values() for r in rs), False)

    # The default fixture: one number filed by four different surnames.
    got, district, _ = people(None, None)
    check("a number several people filed is the district's", district,
          "(708) 457-1244")
    check("and rides none of them",
          [r for rs in got.values() for r in rs if r], [])

    # Two people of one surname sharing a number: not the district's (one
    # surname witnesses nothing) and not either person's (two officials).
    got, district, _ = people(
        ["Ann", "Smith", "Ann", "Smith", "Bob", "Smith", "Dee", "Fox"],
        ["(309) 555-0101", "(309) 555-0101", "(309) 555-0101", ""])
    check("a number two officials of one surname share rides neither",
          [r for rs in got.values() for r in rs if r], [])
    check("and is not the district's either", district, "")

    # One person in both published slots with two different numbers.
    got, _, _ = people(
        ["Pat", "Reed", "Ann", "Joyce", "Ann", "Joyce", "Dee", "Fox"],
        ["(309) 555-0109", "(309) 555-0121", "(309) 555-0187", ""])
    check("a second number goes in phonesExtra, in slot order",
          got.get("Ann Joyce", [None])[0],
          {"phone": "(309) 555-0121", "phonesExtra": ["(309) 555-0187"]})
    check("a filer this file does not emit carries nothing",
          "Pat Reed" in got, False)

    # The same person filed in two cases is one person here, as already_named
    # treats them; a number only that person gave in slot D is theirs too.
    got, _, _ = people(
        ["Pat", "Reed", "Trace", "Evans", "Bo", "Lund", "trace", "evans"],
        ["", "(309) 555-0121", "(309) 555-0102", "(309) 555-0187 Ext:"])
    check("case-only respellings are one person and an empty Ext is cut",
          got.get("Trace Evans", [None])[0],
          {"phone": "(309) 555-0121", "phonesExtra": ["(309) 555-0187"]})

    # Not a telephone number: dropped, warned about by slot, never printed.
    got, _, warned = people(
        ["Pat", "Reed", "Ann", "Joyce", "Bo", "Lund", "Dee", "Fox"],
        ["", "call the station", "(309) 555-0102 / (309) 555-0103", ""])
    check("a value that is not a number ships on nobody",
          [r for rs in got.values() for r in rs if r], [])
    check("the warning names the slots",
          sorted(w.split(": slot ")[1][0] for w in warned if ": slot " in w),
          ["B", "C"])
    check("and never the value",
          any("station" in w or "555" in w for w in warned), False)

    # One person, two numbers one typing error apart: neither ships.
    for second, label in (("(309) 555-0124", "one digit"),
                          ("(309) 555-0132", "two neighbouring digits swapped")):
        got, _, warned = people(
            ["Pat", "Reed", "Ann", "Joyce", "Bo", "Lund", "Ann", "Joyce"],
            ["", "(309) 555-0123", "(309) 555-0102", second])
        check("numbers %s apart for one person: neither ships" % label,
              got.get("Ann Joyce"), [{}])
        check("and the warning names slots B and D, never a value",
              [w.split(": slots ")[1].split(" file")[0] for w in warned
               if ": slots " in w], ["B, D"])
    got, _, _ = people(
        ["Pat", "Reed", "Ann", "Joyce", "Bo", "Lund", "Ann", "Joyce"],
        ["", "(309) 555-0123", "(309) 555-0102", "(815) 555-0199"])
    check("two clearly different numbers for one person both ship",
          got.get("Ann Joyce"),
          [{"phone": "(309) 555-0123", "phonesExtra": ["(815) 555-0199"]}])
    check("one_digit_apart: equal strings are one number, not a typo",
          one_digit_apart("3095550123", "3095550123"), False)

    # A number filed without an area code ships exactly as filed.
    got, _, _ = people(
        ["Pat", "Reed", "Ann", "Joyce", "Bo", "Lund", "Dee", "Fox"],
        ["", "555-0114", "", ""])
    check("a number with no area code ships as filed",
          got.get("Ann Joyce"), [{"phone": "555-0114"}])

    for value, want in (("(309) 555-0114 Ext: 101", True),
                        ("309-555-0114", True), ("cell 309.555.0114", True),
                        ("555-0114", True), ("(309) 555-0114 x12", True),
                        ("309-555-0114, 309-555-0115", False),
                        ("12 Main St", False), ("a@b.org", False),
                        ("(309) 555-0114 IL 60706", False)):
        check("shape of %r" % value, bool(OFFICER_PHONE_SHAPE.match(value)), want)

    payload = {"districts": {"X": {
        "office": {"phone": "(309) 555-0114"},
        "board": [{"name": "A", "role": "President", "phone": "555-0114"},
                  {"name": "B", "role": "Trustee", "phone": "12 Main St"}],
        "heads": [{"name": "C", "role": "Director", "phone": "(309) 555-0101",
                   "phonesExtra": ["a@b.org"]}]}}}
    found = suspect_phones_in(payload)
    check("suspect_phones_in finds each bad value",
          [w for w, _why in found],
          ["districts.X.board[1]", "districts.X.heads[0]"])
    check("and never names the value",
          any("Main" in why or "@" in why for _w, why in found), False)
    check("count_officer_phones counts records, numbers and missing area codes",
          count_officer_phones(payload),
          {"officers": 3, "withPhone": 3, "withSecond": 1, "noAreaCode": 1})

    check("line_digits drops an extension and a leading 1",
          [line_digits(v) for v in ("(309) 555-0114 Ext: 101",
                                    "1-309-555-0114", "555-0114 x2", "")],
          ["3095550114", "3095550114", "5550114", ""])
    check("same_line: a number with no area code matches the line it ends",
          (same_line("5550114", "3095550114"), same_line("5550114", "3095550115"),
           same_line("3095550114", "8155550114")), (True, False, False))
    entry = {"office": {"phone": "(309) 555-0150"},
             "board": [{"name": "A", "phone": "(309) 555-0114 Ext: 101",
                        "phonesExtra": ["(309) 555-0116"]},
                       {"name": "B", "phone": "555-0114"},
                       {"name": "C", "phone": "(309) 555-0117"}],
             "heads": [{"name": "D"}]}
    dropped = drop_lines_from_officers(entry, ["309.555.0114", ""])
    check("drop_lines_from_officers takes the body's line off every officer",
          (dropped, entry["board"]),
          (2, [{"name": "A", "phone": "(309) 555-0116"}, {"name": "B"},
               {"name": "C", "phone": "(309) 555-0117"}]))
    check("and leaves the office and an officer with no number alone",
          (entry["office"], entry["heads"]),
          ({"phone": "(309) 555-0150"}, [{"name": "D"}]))
    entry = {"office": {"email": "Office@Example.org"},
             "board": [{"name": "A", "email": "office@example.org"},
                       {"name": "B", "email": "b@example.org"}],
             "heads": [{"name": "C"}]}
    check("drop_mail_from_officers takes the body's address off, any case",
          (drop_mail_from_officers(entry, ["OFFICE@example.org", " "]),
           entry["board"], entry["office"]),
          (1, [{"name": "A"}, {"name": "B", "email": "b@example.org"}],
           {"email": "Office@Example.org"}))

    # AN OFFICER'S OWN E-MAIL ADDRESS (Adam's choice of 2026-10-17, "E-mails
    # too"). Driven through the real contact_block. Every address here is on a
    # made-up or reserved domain; slot B is the President and slot C the
    # Treasurer, both shipped, while A and D ship only a board title.
    def mails(emails, name_row=None):
        """({officer name: e-mail}, the district's e-mail, the warnings)."""
        warnings = []
        block = contact_block(
            _Session("Norridge",
                     name_row or ["Pat", "Reed", "Ann", "Joyce",
                                  "Cal", "Moss", "Dee", "Fox"],
                     ["", "", "", ""], emails),
            "016/999/99", "SELFTEST UNIT", warnings) or {}
        shipped = {}
        for _bucket, record in block.get("officers") or []:
            shipped[record["name"]] = record.get("email")
        return shipped, block.get("email"), warnings

    got, district, _ = mails(["", "ann.joyce@example.com", "cmoss@example.net", ""])
    check("an officer's own address rides that officer",
          got, {"Ann Joyce": "ann.joyce@example.com", "Cal Moss": "cmoss@example.net"})
    check("and is not the district's", district, "")

    got, _, _ = mails(["", "Shared@Example.com", "shared@example.com", ""])
    check("an address printed beside two people, in any case, rides neither",
          got, {"Ann Joyce": None, "Cal Moss": None})

    got, _, _ = mails(["pat.reed@example.com", "", "", "dee@example.com"])
    check("an address in another person's slot is not an officer's",
          got, {"Ann Joyce": None, "Cal Moss": None})

    got, _, warned = mails(["", "cal.moss@example.com", "", ""])
    check("an address named for another filer rides nobody",
          got, {"Ann Joyce": None, "Cal Moss": None})
    check("and the warning names the slot, never the value",
          [w for w in warned if "named for another filer" in w],
          ["SELFTEST UNIT: slot B files an e-mail named for another filer of "
           "the same report; it ships on nobody"])
    got, _, _ = mails(["", "bob.smith@example.com", "asmith@example.com", ""],
                      ["Pat", "Reed", "Ann", "Smith", "Bob", "Smith", "Dee", "Fox"])
    check("a shared surname decides nothing; a given name does",
          got.get("Ann Smith"), None)
    got, _, _ = mails(["", "asmith@example.com", "bob.smith@example.com", ""],
                      ["Pat", "Reed", "Ann", "Smith", "Bob", "Smith", "Dee", "Fox"])
    check("and each Smith keeps an address that names nobody else",
          got, {"Ann Smith": "asmith@example.com", "Bob Smith": "bob.smith@example.com"})

    got, district, _ = mails(["", "info@selftestfire.org", "cmoss@example.net", ""])
    check("the district's own address stays the district's",
          (district, got.get("Ann Joyce"), got.get("Cal Moss")),
          ("info@selftestfire.org", None, "cmoss@example.net"))

    both = ["Pat", "Reed", "Ann", "Joyce", "Cal", "Moss", "Ann", "Joyce"]
    got, _, _ = mails(["", "annj@example.com", "", "ajoyce@selftest.il.us"], both)
    check("one address per person, a government domain kept over another",
          got.get("Ann Joyce"), "ajoyce@selftest.il.us")
    got, district, _ = mails(["", "annj@example.com", "", "ann@selftestfire.org"],
                             both)
    check("and where the one kept is the district's, the officer carries none",
          (district, got.get("Ann Joyce")), ("ann@selftestfire.org", None))
    got, _, _ = mails(["", "annj@example.com", "", "ann.j@example.net"], both)
    check("two addresses that both carry the officer's name: the first in slot order",
          got.get("Ann Joyce"), "annj@example.com")
    got, _, _ = mails(["", "bill@example.com", "", "kim@example.com"], both)
    check("two addresses neither carrying the officer's name: neither ships",
          got.get("Ann Joyce"), None)
    got, _, _ = mails(["", "kim@example.com", "", "ann.joyce@example.net"], both)
    check("two addresses, one carrying the officer's name: that one ships",
          got.get("Ann Joyce"), "ann.joyce@example.net")
    got, district, _ = mails(["", "selftestfire@example.com", "", "ann.joyce@example.com"],
                             both)
    check("a district mailbox at a provider stays the district's, "
          "and the officer's own address ships",
          (district, got.get("Ann Joyce")),
          ("selftestfire@example.com", "ann.joyce@example.com"))
    got, district, _ = mails(["", "selftestfire@example.com", "", "kim@example.com"],
                             both)
    check("beside a district mailbox, an address not carrying the name ships on nobody",
          (district, got.get("Ann Joyce")), ("selftestfire@example.com", None))
    got, _, _ = mails(["", "selftest13@example.com", "", ""])
    check("an address named for the unit and not the officer is the unit's",
          got.get("Ann Joyce"), None)
    got, _, _ = mails(["", "admin@mackcpas.example", "office@ruralbank.example", ""])
    check("an accountant's or a bank's address not carrying the name ships on nobody",
          got, {"Ann Joyce": None, "Cal Moss": None})
    got, _, _ = mails(["", "ann.joyce@joycecpa.example", "cmoss@example.net", ""])
    check("and one carrying the officer's name ships",
          got, {"Ann Joyce": "ann.joyce@joycecpa.example", "Cal Moss": "cmoss@example.net"})
    check("firm_address reads the address's words, not a bare substring",
          [firm_address(v) for v in ("staff@sycparks.example", "cpamb@example.net",
                                     "jo.cpa@example.net", "redbird1992cpa@example.com",
                                     "kim@tricountycpas.example", "x@farmerbank.example",
                                     "x@ruralaccountinginc.example")],
          [False, False, True, True, True, True, True])
    got, _, warned = mails(["", "klet62@example.com", "", ""],
                           ["Kathy", "Letterle", "Ann", "Joyce", "Cal", "Moss",
                            "Dee", "Fox"])
    check("an address made of another filer's initial and surname rides nobody",
          got.get("Ann Joyce"), None)
    check("and is warned about by slot",
          [w for w in warned if "named for another filer" in w],
          ["SELFTEST UNIT: slot B files an e-mail named for another filer of "
           "the same report; it ships on nobody"])
    check("person_tokens: words, initial with surname, given name with initial",
          sorted(person_tokens("Kathy Letterle")),
          ["kathy", "katl", "klet", "letterle"])
    check("person_tokens: an apostrophe dropped and a suffix not a surname",
          sorted(person_tokens("Charles O'Brien III")),
          ["chao", "charles", "cobr", "obrien"])

    got, _, warned = mails(["", "ann.joyce@example.com", "", "ann.joyce@exmple.com"],
                           both)
    check("two addresses one character apart for one person: neither ships",
          got.get("Ann Joyce"), None)
    check("and the warning names slots B and D, never a value",
          [w.split(": slots ")[1].split(" file")[0] for w in warned
           if ": slots " in w], ["B, D"])

    got, _, warned = mails(["", "ann@example.com / ann2@example.com",
                            "not an address", ""])
    check("a cell not shaped like one address ships on nobody",
          got, {"Ann Joyce": None, "Cal Moss": None})
    check("the warning names the slots",
          sorted(w.split(": slot ")[1][0] for w in warned if "not shaped" in w),
          ["B", "C"])
    check("and never the value", any("example" in w for w in warned), False)

    got, _, _ = mails(["", "Ann.Joyce@Example.com", "MaxExton@example.com", ""])
    check("an address ships in its filed case and is never cut at 'Ext'",
          got, {"Ann Joyce": "Ann.Joyce@Example.com", "Cal Moss": "MaxExton@example.com"})

    import contextlib
    import io
    with contextlib.redirect_stderr(io.StringIO()):
        got, _, _ = mails(["", "eeeten@gmail.org", "", ""])
    check("an address undeliverable.py lists stays withheld",
          got.get("Ann Joyce"), None)

    check("one_typo_apart: a dropped, a changed and a swapped character",
          [one_typo_apart(a, b) for a, b in (("abcd", "abd"), ("abcd", "abxd"),
                                             ("abcd", "abdc"), ("abcd", "abcd"),
                                             ("abcd", "ab"))],
          [True, True, True, False, False])

    payload = {"districts": {"X": {
        "office": {"email": "office@example.org"},
        "board": [{"name": "A", "role": "President", "email": "a@example.org"},
                  {"name": "B", "role": "Trustee", "email": "b c@example.org"}],
        "heads": [{"name": "C", "role": "Director",
                   "email": "c@example.org, d@example.org"},
                  {"name": "D", "role": "Manager"}]}}}
    found = suspect_emails_in(payload)
    check("suspect_emails_in finds each bad value",
          [w for w, _why in found],
          ["districts.X.board[1]", "districts.X.heads[0]"])
    check("and never names the value",
          any("@" in why for _w, why in found), False)
    check("count_officer_emails counts records and addresses",
          count_officer_emails(payload), {"officers": 4, "withEmail": 3})

    payload = {"districts": {
        "X": {"board": [{"name": "Ann Joyce", "email": "admin@firm.example"},
                        {"name": "Cal Moss", "email": "cmoss@example.net"}]},
        "Y": {"board": [{"name": "Dee Fox", "email": "ADMIN@firm.example"},
                        {"name": "CAL MOSS", "email": "cmoss@example.net"}]}}}
    check("drop_mail_given_for_two: one address beside two people, across filings",
          (drop_mail_given_for_two(payload),
           [p.get("email") for d in ("X", "Y")
            for p in payload["districts"][d]["board"]]),
          (2, [None, "cmoss@example.net", None, "cmoss@example.net"]))

    # ACROSS ROSTERS, built in either order and then again, as the weekly jobs
    # build them: an address one roster gives Lee Park and another gives Mo
    # Reyes ends on neither, and one both give Sal Ortiz stays on him in both.
    import tempfile
    library, special = AFR_ROSTERS[0], AFR_ROSTERS[1]

    def roster(person):
        return {"libraries": {"L": {"board": [
            {"name": person, "email": "pat.home@example.net"},
            {"name": "Sal Ortiz", "email": "sal@example.net"}]}}}

    def build(app_dir, own, payload):
        withheld = {}
        drop_mail_given_for_two(payload, mail_elsewhere(app_dir, own), withheld)
        if withheld:
            payload[MAIL_GIVEN_FOR_TWO] = withheld
        with open(os.path.join(app_dir, own), "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        return [p.get("email") for p in payload["libraries"]["L"]["board"]]

    for order in ((library, special), (special, library)):
        with tempfile.TemporaryDirectory() as app_dir:
            who = {library: "Lee Park", special: "Mo Reyes"}
            got = {}
            for _round in range(2):
                for own in order:
                    got[own] = build(app_dir, own, roster(who[own]))
            check("drop_mail_given_for_two: one address beside two people in two "
                  "rosters, %s built first" % order[0].split("-")[1],
                  (got[library], got[special]),
                  ([None, "sal@example.net"], [None, "sal@example.net"]))
            with open(os.path.join(app_dir, special), encoding="utf-8") as fh:
                written = json.dumps(json.load(fh))
            check("and the roster records it as digests, never the address or name",
                  ("pat.home" in written.split(MAIL_GIVEN_FOR_TWO)[1],
                   "Mo Reyes" in written.split(MAIL_GIVEN_FOR_TWO)[1]),
                  (False, False))
    with tempfile.TemporaryDirectory() as app_dir:
        for _round in range(2):
            for own in (library, special):
                kept = build(app_dir, own, roster("Pat Home"))
        check("one person given one address in two rosters keeps it in both",
              kept, ["pat.home@example.net", "sal@example.net"])

    if failed:
        print("")
        print("%d CHECK(S) FAILED" % len(failed))
        for f in failed:
            print("  " + f)
        return 1
    print("")
    print("OK - LOCALITY_CORRECTIONS behaves in all three directions, the "
          "middle-initial comma is corrected, printed, and never guessed, and "
          "an officer's own telephone and e-mail address ride that officer and "
          "nobody else")
    return 0


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit("usage: comptroller_afr.py --selftest   (this module is a library)")
