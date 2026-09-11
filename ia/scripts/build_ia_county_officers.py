#!/usr/bin/env python3
"""
Build data/app/ia-county-officers.json -- the rest of each Iowa county's
ELECTED slate, keyed by 5-digit FIPS GEOID and read by ia/index.html's County
card alongside data/app/ia-county-auditors.json.

Iowa elects six county offices (Iowa Code ch. 331): auditor, treasurer,
recorder, sheriff, county attorney, and the board of supervisors. The AUDITOR
already ships in its own file with its own weekly workflow, because Iowa Code
47.2 makes that office the county's commissioner of elections and it has a
source nothing else shares. THIS file carries the other five.

WHERE EACH OFFICE COMES FROM, AND WHY IT IS NOT ONE SOURCE
------------------------------------------------------------
ISAC's member portal (ia_county_officers_scraper.py) publishes every office in
one table per county, regenerated daily -- but it publishes NO E-MAIL for
anybody, gives supervisors no district, and is measurably wrong about some
supervisor counts. Three offices have a dedicated statewide directory that is
better on every axis (ia_county_officer_sources_scraper.py), so:

    treasurer        ISAC only              -- no statewide directory EXISTS.
    recorder         Iowa Land Records      + ISAC phone if the card lacks one
    sheriff          ISSDA directory (PDF)  + ISAC phone if the card lacks one
    county attorney  ICAA roster (PDF)      + ISAC phone if the card lacks one
    supervisors      ISAC only              -- gated hard, see below.

THE TREASURER HAS NO SECOND WITNESS AND THAT IS RECORDED, NOT PAPERED OVER.
iowatreasurers.org is a payment portal (vehicle registration, property tax); it
names nobody. Every other office here is corroborated by two independent
publishers, and the treasurer is corroborated by one. The row still ships --
ISAC is a real source, published by the counties' own association -- but the
asymmetry is stated here rather than left for a reader to infer.

SUPERVISORS ARE GATED ON IOWA CODE 331.201 AND ON GEOMETRY THIS REPO ALREADY SHIPS
-----------------------------------------------------------------------------------
Section 331.201: a board of supervisors "shall consist of three members unless
the membership is increased to five". A county whose ISAC table lists any other
number is not a county with an unusual board -- it is a stale or partial table,
and shipping it would put a made-up board size in front of a reader. So a
county's supervisors ship only when BOTH hold:

  1. the ISAC row count is exactly 3 or 5, and
  2. it equals the seat count in data/app/ia-county-board-directory.json,
     which was derived from the Legislature's own supervisor-district geometry
     in phase 2 -- a completely independent publisher.

Seven counties fail one or both (measured 2026-08-28): Adair returns 4 rows,
Floyd 2, Henry 4, Humboldt 6, Tama 4 -- all impossible; Warren and Wright
return a legal 5 against the geometry's 3. Those counties ship every other
office and carry `supervisorsWithheld` naming the reason, so the card can say
what it does not know instead of showing a board that is the wrong size. The
same reader still gets the board through the county-supervisor layer, which is
built from the geometry rather than from this table.

NO ADDRESS FROM ANY OF THESE SOURCES IS SHIPPED. The ISAC table and both PDFs
print an address block per officer, and the ICAA's are a mix of courthouse and
PRIVATE LAW OFFICE addresses. The scrapers read those lines only to pull a
phone number and an e-mail out of them; this builder never receives the line
and could not ship one. The County card's office block continues to come from
the auditors' association, which publishes courthouse addresses only.

Usage:
    python3 ia/scripts/ia_county_officers_scraper.py          # ISAC portal
    python3 ia/scripts/ia_county_officer_sources_scraper.py   # the three directories
    python3 ia/scripts/build_ia_county_officers.py
    python3 ia/scripts/build_ia_county_officers.py --check
"""

import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ia/
# The withhold list is FLEET-WIDE and lives at the repo root: one measurement
# behind one list beats three drifting copies.
sys.path.insert(0, os.path.join(os.path.dirname(REPO_ROOT), "scripts"))
import undeliverable  # noqa: E402
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")

COUNTIES = os.path.join(APP_DATA_DIR, "state-counties.json")
BOARD_DIRECTORY = os.path.join(APP_DATA_DIR, "ia-county-board-directory.json")
ISAC_CACHE = os.path.join(CACHE_DIR, "ia_county_officers.json")
SOURCES_CACHE = os.path.join(CACHE_DIR, "ia_county_officer_sources.json")
EMAILS_CACHE = os.path.join(CACHE_DIR, "ia_county_officer_emails.json")
OUT = os.path.join(APP_DATA_DIR, "ia-county-officers.json")

EXPECT_COUNTIES = 99
LEGAL_BOARD_SIZES = (3, 5)          # Iowa Code 331.201

# The ISAC portal publishes party as a letter; ia-county-auditors.json (from a
# different publisher) spells it out, and the two ship side by side on one
# card, so the letters are expanded here rather than in the app. "NP" is Iowa's
# own NO PARTY registration -- a real answer, not a missing one, and distinct
# from the empty cell that means the portal simply printed nothing. An
# unrecognised code FAILS rather than riding onto a card as a bare letter.
# "Democratic", not "Democrat": ia-county-auditors.json already ships the
# adjective form from a different publisher, and both rosters render on ONE
# card -- an auditor labelled "Democratic" beside a treasurer labelled
# "Democrat" reads as two different facts about the same party.
PARTY = {"R": "Republican", "D": "Democratic", "I": "Independent",
         "L": "Libertarian", "NP": "No party", "": None}

# Offices whose source publishes names in ALL CAPS. Only the ICAA roster does;
# Iowa Land Records and the ISSDA directory both publish mixed case, and
# running this over a correctly-cased name risks changing a spelling its own
# publisher chose. So it is keyed by office, not applied by detection.
ALL_CAPS_SOURCES = ("countyAttorney",)
_ROMAN = {"II", "III", "IV", "V"}

# Offices carried here, and the ISAC "Office" string each is published under.
OFFICES = [
    ("treasurer", "Treasurer"),
    ("recorder", "Recorder"),
    ("sheriff", "Sheriff"),
    ("countyAttorney", "County Attorney"),
]
SUPERVISOR_OFFICE = "Supervisor"
# Offices with a dedicated statewide directory (the enrichment cache's keys).
ENRICHED = ("recorder", "sheriff", "countyAttorney")

# Floors, not targets. Measured 2026-08-28: treasurer 99, recorder 99,
# sheriff 99, county attorney 99, supervisor boards 92 of 99.
MIN_PER_OFFICE = {"treasurer": 95, "recorder": 95, "sheriff": 95, "countyAttorney": 95}
MIN_BOARDS = 88
# MIN_EMAILS measured 2026-08-29: 97 recorder + 97 attorney + 87 sheriff + 65
# treasurer = 346, and the floor sits above 346 minus the treasurer block.
#
# WHAT IT CATCHES CHANGED when the carry-forward went in on 2026-09-11, and
# saying so matters more than the number. It used to mean "the treasurer
# source going dark fails here rather than shipping silently". It no longer
# means that: if iowatreasurers.org and the county sites all went dark
# tomorrow, every address already in the shipped file would still be carried
# forward under its unchanged officeholder and this floor would not fire --
# which is correct, because those addresses would still be right. What it
# catches now is the ACCUMULATOR breaking: a prior that fails to load, a
# large number of offices changing hands at once, or the merge dropping
# addresses it should have kept. That is the failure this floor actually
# caught on 2026-09-04 and 2026-09-11, and it caught it twice.
MIN_EMAILS = 320
MIN_PHONES = 380
# A divergence is one office in one county where ISAC and the office's own
# directory name different people. 6 measured; the ceiling catches a source
# that has been re-pointed at a different vintage rather than a few counties
# turning over between two publishers' refresh cycles.
MAX_DIVERGENCES = 12

# WHERE THE TWO PUBLISHERS DISAGREE ABOUT WHO HOLDS AN OFFICE, AND A THIRD
# WITNESS SETTLED IT. Keyed (county, office) -> (winner, the page that decided).
# NEITHER PUBLISHER WINS CATEGORICALLY, which is the whole reason this is a
# table of measurements rather than a preference:
#
#   ISAC ships APPOINTED deputies in an elected officer's row -- Crawford, Page
#   and Sioux all name their chief deputy as sheriff, and Page names an
#   assistant as county attorney. Those four are detected automatically
#   (named_in) because the directory's own entry names the same person as a
#   deputy, so they need no pin.
#   THE DIRECTORIES GO STALE -- both are dated documents (ISSDA April 2025,
#   ICAA May 2026). Sac County's own site names Kathryn "Katie" Stange as
#   sheriff; the ISSDA PDF still carries her predecessor Ken McClure.
#
# Everything else diverging is WITHHELD: two publishers naming two different
# people, with nothing to break the tie, is exactly the case where this project
# says so instead of choosing.
DIVERGENCE_RESOLVED = {
    ("Sac", "sheriff"): ("isac", "https://www.saccountyiowa.gov/sheriff"),
}


def expand_party(code, county, office):
    key = (code or "").strip().upper()
    if key not in PARTY:
        raise RuntimeError("%s %s: unrecognised party code %r -- add it to PARTY "
                           "deliberately rather than shipping a bare letter"
                           % (county, office, code))
    return PARTY[key]


def title_name(raw):
    """Restore an ALL-CAPS name to display case without flattening it.

    The naive form is wrong for the names this document actually contains:
    "McGOWAN" becomes "Mcgowan", "O\u2019TOOLE" becomes "O\u2019toole", the
    initial in "TY A. STEWART" becomes "a.", and "JR." becomes "Jr." only by
    luck. Mc/Mac, a leading letter-apostrophe, single-letter initials, roman
    numerals and hyphenated surnames are each handled explicitly.
    """
    def cap(word):
        if not word:
            return word
        bare = word.strip(".,")
        if bare.upper() in _ROMAN:
            return bare.upper() + word[len(bare):]
        if len(bare) == 1:
            return word.upper()                       # an initial: "A."
        out = word[0].upper() + word[1:].lower()
        m = re.match(r"^(Mc|Mac)(.+)$", out)
        if m and len(m.group(2)) > 1:
            out = m.group(1) + m.group(2)[0].upper() + m.group(2)[1:]
        m = re.match(r"^([A-Za-z][\u2019'])(.+)$", out)
        if m:
            out = m.group(1) + m.group(2)[0].upper() + m.group(2)[1:]
        return out

    words = []
    for word in (raw or "").split():
        words.append("".join(cap(part) if part != "-" else "-"
                             for part in re.split(r"(-)", word)))
    return " ".join(words)


def load(path, what):
    try:
        with open(path) as f:
            return json.load(f)
    except OSError as e:
        raise RuntimeError("no %s at %s (%s) -- run the scrapers first"
                           % (what, path, e))


# Honorifics and post-nominals the two sources disagree about publishing.
_TITLES = {"mr", "mrs", "ms", "miss", "dr", "hon", "sheriff", "the"}
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "jd", "esq", "phd"}


def name_tokens(name):
    """Lower-case name words, with titles, post-nominals and any parenthetical
    designation removed, and hyphens treated as spaces."""
    s = re.sub(r"\([^)]*\)", " ", (name or ""))          # "(J-CINA)", "(MC)"
    s = s.replace("\u2019", "'").replace("-", " ")
    s = re.sub(r"[^A-Za-z' ]+", " ", s).lower()
    toks = [t.strip("'") for t in s.split() if t.strip("'")]
    # Single letters are middle initials ("SHAWN M. HARDEN") and the debris of
    # post-nominals the character filter splits ("J.D." -> "j" "d"). Neither is
    # evidence about which person this is.
    return [t for t in toks
            if len(t) > 1 and t not in _TITLES and t not in _SUFFIXES]


def surname(name):
    toks = name_tokens(name)
    return toks[-1] if toks else ""


def _edit_distance(a, b, cap=2):
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def same_person(a, b):
    """Do two directories name the SAME person, spelled differently?

    Measured differences that are NOT disagreements about who holds the office:
    honorifics ("Mr. Shawn Harden, J.D." / "SHAWN M. HARDEN"), a dropped middle
    initial, a hyphen ("Cosgrove-Whitmer" / "COSGROVE WHITMER"), spacing inside
    a surname ("VanDerMaaten" / "VAN DER MAATEN"), a suffix ("MARCUS GROSS,
    JR."), a typographic apostrophe ("O'Toole" / "O’TOOLE"), an ICAA
    designation ("JARED HARMON (J-CINA)"), and a single-character misspelling
    ("Rasmussen" / "Rassmussen"). Anything beyond that is treated as a real
    disagreement and the office is withheld -- never resolved by preference.
    """
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return False
    ca, cb = "".join(ta), "".join(tb)
    if ca == cb or _edit_distance(ca, cb) <= 1:
        return True          # spacing, apostrophes, one-character misspellings
    sa, sb = set(ta), set(tb)
    if sa <= sb or sb <= sa:
        return True          # a dropped middle name
    # Nicknames. The two directories publish "Jeff"/"Jeffrey", "Sam"/"Samantha",
    # "Tammy"/"Tamara", "Cathy"/"Catherine", "Matt"/"Matthew", "Dave"/"David" --
    # none of which is a prefix rule away from the other, and all of which share
    # a surname and a first initial. In EVERY divergence that turned out to be
    # two different people, the SURNAMES differ outright, so the surname is what
    # this test leans on. The known limit: two people who share a surname and a
    # first initial, in the same office of the same county, would read as one.
    return (_edit_distance(ta[-1], tb[-1]) <= 1 and ta[0][:1] == tb[0][:1])


def named_in(name, blob, officer_name):
    """Is this person named anywhere in a directory entry's own text?

    Used ONLY to detect the ISAC portal publishing an APPOINTED deputy or
    assistant in an elected officer's row. A one-character tolerance is
    deliberate: Crawford's chief deputy is "Rasmussen" to ISAC and
    "Rassmussen" to ISSDA, and an exact test misses exactly that case.
    """
    target = surname(name)
    if len(target) < 4 or not blob:
        return False
    # The officer's OWN name is in their own entry, so it must come out first --
    # otherwise every nickname difference reads as a mislabelled deputy.
    own = set(name_tokens(officer_name))
    return any(_edit_distance(target, w) <= 1
               for w in name_tokens(blob) if len(w) >= 4 and w not in own)


def email_witnesses(name, email):
    """Does this address's local part carry THIS person's name?

    Re-checked against the name the build actually ships, not the one the
    scrape matched. A divergence resolution can change which of two publishers'
    names wins after the address was gathered, and an address witnessed against
    the loser belongs to somebody this card is not naming.
    """
    local = re.sub(r"[^a-z]", "", email.split("@")[0].lower())
    toks = [t.lower() for t in re.findall(r"[A-Za-z]{3,}", name or "")]
    if any(t in local for t in toks):
        return True
    parts = [t.lower() for t in re.findall(r"[A-Za-z]{2,}", name or "")]
    if len(parts) >= 2:
        for sur in parts[1:]:
            if local.startswith(parts[0][0] + sur):
                return True
    return False


def clean_phone(raw):
    """Keep a phone only if it really is one; never ship a fragment."""
    if not raw:
        return None
    m = re.search(r"\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{4}", raw)
    return re.sub(r"\s+", " ", m.group(0)).strip() if m else None


def main():
    check_only = "--check" in sys.argv[1:]

    counties = load(COUNTIES, "state-counties.json")
    geoid_by_name = {f["properties"]["BASENAME"]: f["properties"]["GEOID"]
                     for f in counties["features"]}
    if len(geoid_by_name) != EXPECT_COUNTIES:
        raise RuntimeError("state-counties.json carries %d counties, expected %d"
                           % (len(geoid_by_name), EXPECT_COUNTIES))

    isac = load(ISAC_CACHE, "ISAC officer cache")
    sources = load(SOURCES_CACHE, "per-office directory cache")
    # Optional: the e-mail cache is a later addition and a build without it is
    # the build as it was before, not a broken one.
    try:
        officer_emails = load(EMAILS_CACHE, "officer e-mail cache")
    except RuntimeError:
        officer_emails = {}
        print("  no officer e-mail cache -- treasurer/sheriff addresses will be "
              "absent (run ia_county_officer_email_scraper.py)", file=sys.stderr)
    # ---- THE SHIPPED FILE IS AN INPUT AS WELL AS THE OUTPUT, and it has to be.
    # The e-mail scraper is INCREMENTAL against this very file: it skips any
    # county that already carries an address, so its cache holds only the
    # addresses found THIS run. Measured 2026-09-11 on the failing CI run --
    # it probed 35 treasurer counties (99 records minus the 64 already
    # carrying one) and 11 sheriff (98 minus 87), and accepted 3 and 0. The
    # builder used to rebuild from the caches alone, so the 61 treasurer
    # addresses that exist only here were dropped every week: 97 recorder +
    # 97 attorney + 83 sheriff + 3 treasurer = 280 against a floor of 320,
    # which is exactly what CI reported on 2026-09-04 and 2026-09-11. The
    # treasurer has NO statewide directory at all, so for that office this
    # file is the only accumulator there is.
    #
    # A missing prior is not an error: a first build, or a checkout without
    # the data file, simply carries nothing forward.
    try:
        prior = load(OUT, "previously shipped roster")
    except RuntimeError:
        prior = {}
        print("  no previously shipped roster -- nothing to carry forward",
              file=sys.stderr)
    board_dir = load(BOARD_DIRECTORY, "county board directory")
    # ia-county-board-directory.json is keyed by 3-digit county FIPS.
    seats_by_geoid = {"19" + k.zfill(3): v.get("seats")
                      for k, v in board_dir.items()}

    unmatched = sorted(set(isac) - set(geoid_by_name))
    if unmatched:
        raise RuntimeError("ISAC cache names %d county/counties not in "
                           "state-counties.json: %s" % (len(unmatched), unmatched))
    if len(isac) != EXPECT_COUNTIES:
        raise RuntimeError("ISAC cache carries %d counties, expected %d"
                           % (len(isac), EXPECT_COUNTIES))

    directory = {}
    filled = {k: 0 for k, _ in OFFICES}
    boards = withheld = divergences = mislabels = resolved = switchboards = 0
    scraped_emails = unwitnessed = carried_emails = dropped_emails = 0
    pins_used = set()
    withheld_detail = []

    for county, geoid in sorted(geoid_by_name.items()):
        rows = isac.get(county, {}).get("rows", [])
        entry = {"county": county}

        for key, office_label in OFFICES:
            best = None
            enrich = sources.get(key, {}).get(county) if key in ENRICHED else None
            isac_rows = [r for r in rows if r["office"] == office_label]
            isac_row = isac_rows[0] if len(isac_rows) == 1 else None

            if enrich and enrich.get("name"):
                agree = not isac_row or same_person(isac_row["name"], enrich["name"])
                mislabel = (not agree and isac_row
                            and named_in(isac_row["name"],
                                         enrich.get("blockText", "")
                                         + " " + enrich.get("assistantText", ""),
                                         enrich["name"]))
                if agree or mislabel:
                    best = {"name": enrich["name"]}
                    if key in ALL_CAPS_SOURCES:
                        best["name"] = title_name(best["name"])
                    if enrich.get("phone"):
                        best["phone"] = enrich["phone"]
                    if enrich.get("email"):
                        best["email"] = enrich["email"]
                    if mislabel:
                        mislabels += 1
                        print("  %-13s %-15s ISAC names %r, who the %s directory "
                              "lists as an APPOINTED deputy/assistant -- the "
                              "directory's elected officer ships"
                              % (county, key, isac_row["name"], key), file=sys.stderr)
                elif (county, key) in DIVERGENCE_RESOLVED:
                    winner, witness = DIVERGENCE_RESOLVED[(county, key)]
                    pins_used.add((county, key))
                    resolved += 1
                    print("  %-13s %-15s ISAC %r vs directory %r -- %s wins per %s"
                          % (county, key, isac_row["name"], enrich["name"],
                             winner, witness), file=sys.stderr)
                    if winner == "isac":
                        # The directory's e-mail belongs to the person it names,
                        # who is not the person taking the office -- so the name
                        # comes over WITHOUT it, never paired with a stranger's.
                        best = {"name": isac_row["name"]}
                    else:
                        best = {"name": title_name(enrich["name"])
                                if key in ALL_CAPS_SOURCES else enrich["name"]}
                        if enrich.get("phone"):
                            best["phone"] = enrich["phone"]
                        if enrich.get("email"):
                            best["email"] = enrich["email"]
                else:
                    # Two publishers, two different people, no third witness.
                    # Ship neither: a card that says the sources disagree is
                    # honest; a card that picks one is a guess.
                    entry[key + "Withheld"] = (
                        "the county directory names %s and the %s's own statewide "
                        "directory names %s" % (isac_row["name"], office_label.lower(),
                                                enrich["name"]))
                    divergences += 1
                    print("  WITHHELD  %-13s %-15s ISAC %r vs directory %r"
                          % (county, key, isac_row["name"], enrich["name"]),
                          file=sys.stderr)
                    continue
            elif isac_row and isac_row["name"]:
                best = {"name": isac_row["name"]}

            if best is None:
                continue
            if "phone" not in best and isac_row:
                ph = clean_phone(isac_row.get("phone"))
                if ph:
                    best["phone"] = ph
            if isac_row and isac_row.get("party"):
                party = expand_party(isac_row["party"], county, key)
                if party:
                    best["party"] = party

            # ---- an address the county itself publishes, for the two offices
            # no statewide directory carries one for. TWO WAYS IN AND NO THIRD:
            # an OFFICE mailbox is the office's whoever holds it, and a personal
            # one must carry the name THIS BUILD SHIPS.
            if "email" not in best:
                hit = (officer_emails.get(key) or {}).get(county) or {}
                addr, why = hit.get("email"), hit.get("why")
                if addr and why == "office":
                    best["email"] = addr
                    scraped_emails += 1
                elif addr and email_witnesses(best["name"], addr):
                    best["email"] = addr
                    scraped_emails += 1
                elif addr:
                    unwitnessed += 1
                    print("  %-13s %-15s %s was witnessed against a name this "
                          "build does not ship (%r) -- dropped"
                          % (county, key, addr, best["name"]), file=sys.stderr)

            # ---- and an address this file already carries, WHEN THE SAME
            # PERSON STILL HOLDS THE OFFICE. That condition is the whole of the
            # safety here, and it covers both kinds of address the probe above
            # accepts: a personal one is still that person's, and an office
            # mailbox is still the office's. When the officeholder changes the
            # address is dropped rather than re-pointed at a stranger -- and
            # dropping it is also what makes the next run re-probe that county,
            # since the scraper's skip list is this file.
            #
            # WHAT THIS DOES NOT DO is re-verify an address while its holder
            # stays put. The name is re-read from ISAC every week; the address
            # is not. A domain that dies is still caught, by scripts/
            # undeliverable.py, which globs every instance's data/app -- but a
            # mailbox that stops working inside a live domain would not be.
            # Rotating re-verification is the fix for that and is deliberately
            # not built here.
            if "email" not in best:
                was = (prior.get(geoid) or {}).get(key) or {}
                if was.get("email") and was.get("name"):
                    if same_person(was["name"], best["name"]):
                        best["email"] = was["email"]
                        carried_emails += 1
                    else:
                        dropped_emails += 1
                        print("  %-13s %-15s %s dropped -- this file had it under "
                              "%r and the office is now %r"
                              % (county, key, was["email"], was["name"],
                                 best["name"]), file=sys.stderr)
            entry[key] = best
            filled[key] += 1

        # ---- supervisors: two independent gates, both must pass
        sups = [r for r in rows if r["office"] == SUPERVISOR_OFFICE]
        seats = seats_by_geoid.get(geoid)
        reason = None
        if len(sups) not in LEGAL_BOARD_SIZES:
            reason = ("the county directory lists %d, and Iowa Code 331.201 allows "
                      "only 3 or 5" % len(sups))
        elif seats is not None and len(sups) != seats:
            reason = ("the county directory lists %d, and the supervisor-district "
                      "geometry seats %d" % (len(sups), seats))
        if reason:
            entry["supervisorsWithheld"] = reason
            withheld += 1
            withheld_detail.append("%s (%s)" % (county, reason))
        else:
            members = []
            for r in sups:
                m = {"name": r["name"]}
                ph = clean_phone(r.get("phone"))
                if ph:
                    m["phone"] = ph
                if r.get("party"):
                    party = expand_party(r["party"], county, "supervisor")
                    if party:
                        m["party"] = party
                members.append(m)
            members.sort(key=lambda m: surname(m["name"]))
            # AN IDENTICAL PHONE ON EVERY MEMBER ROW IS A SWITCHBOARD, NOT
            # CONTACT (docs/EXPANSION_GUIDE.md Part 5). Repeating one number
            # under five names implies five direct lines that do not exist.
            # The guide states the test mechanically -- collect the distinct
            # numbers, and if exactly one covers the whole board, it belongs to
            # the board -- so it is applied that way here rather than by a
            # per-county pin. Measured 2026-08-28: every one of the 92 boards
            # ISAC publishes is a single switchboard, but a county that ever
            # publishes real per-member lines keeps them on the members.
            phones = {m["phone"] for m in members if m.get("phone")}
            if len(phones) == 1 and len(members) > 1:
                entry["boardPhone"] = phones.pop()
                switchboards += 1
                for m in members:
                    m.pop("phone", None)
            entry["supervisors"] = members
            if seats is not None:
                entry["supervisorSeats"] = seats
            plan = (board_dir.get(geoid[2:].lstrip("0").zfill(3), {}) or {}).get("plan")
            if plan:
                entry["supervisorPlan"] = plan
            boards += 1

        directory[geoid] = entry

    # ---------------------------------------------------------------- gates
    for key, floor in MIN_PER_OFFICE.items():
        if filled[key] < floor:
            raise RuntimeError("only %d counties carry a %s (floor %d) -- a source "
                               "reshaped" % (filled[key], key, floor))
    if boards < MIN_BOARDS:
        raise RuntimeError("only %d counties ship a board of supervisors (floor %d) "
                           "-- the ISAC table or the seat geometry moved"
                           % (boards, MIN_BOARDS))
    if divergences > MAX_DIVERGENCES:
        raise RuntimeError("%d offices withheld for an unresolved ISAC-vs-directory "
                           "divergence (ceiling %d) -- that is a source pointing at "
                           "a different vintage, not counties turning over"
                           % (divergences, MAX_DIVERGENCES))

    # A pin must not calcify: once the two publishers agree again it is dead
    # weight asserting a disagreement that no longer exists.
    stale_pins = sorted(set(DIVERGENCE_RESOLVED) - pins_used)
    if stale_pins:
        raise RuntimeError(
            "DIVERGENCE_RESOLVED pins %s, but those sources no longer disagree -- "
            "drop the pin" % (stale_pins,))

    emails = sum(1 for v in directory.values() for k, _ in OFFICES
                 if isinstance(v.get(k), dict) and v[k].get("email"))
    phones = sum(1 for v in directory.values() for k, _ in OFFICES
                 if isinstance(v.get(k), dict) and v[k].get("phone"))
    phones += sum(1 for v in directory.values() for m in v.get("supervisors", [])
                  if m.get("phone"))
    if emails < MIN_EMAILS:
        raise RuntimeError("only %d officer e-mails (floor %d) -- an enrichment "
                           "source stopped publishing them" % (emails, MIN_EMAILS))
    if phones < MIN_PHONES:
        raise RuntimeError("only %d officer phone numbers (floor %d)"
                           % (phones, MIN_PHONES))

    # Structural refusal: no address field can exist on any record, whatever a
    # source starts publishing. The scrapers never emit one; this proves it.
    for geoid, v in directory.items():
        for key, _ in OFFICES:
            rec = v.get(key)
            if isinstance(rec, dict) and set(rec) - {"name", "phone", "email", "party"}:
                raise RuntimeError("%s %s carries unexpected field(s) %s -- only "
                                   "name/phone/email/party may ship"
                                   % (geoid, key, sorted(set(rec) - {"name", "phone", "email", "party"})))
        for m in v.get("supervisors", []):
            if set(m) - {"name", "phone", "party"}:
                raise RuntimeError("%s supervisor carries unexpected field(s) %s"
                                   % (geoid, sorted(set(m) - {"name", "phone", "party"})))

    print("  switchboard phones hoisted off member rows: %d board(s)" % switchboards,
          file=sys.stderr)
    print("  e-mails added from the counties' own sites / the treasurers' state "
          "site: %d (+%d dropped as witnessed against a name not shipped)"
          % (scraped_emails, unwitnessed), file=sys.stderr)
    print("  e-mails carried forward from the shipped file, same officeholder: "
          "%d (+%d dropped, the office changed hands)"
          % (carried_emails, dropped_emails), file=sys.stderr)
    print("ia-county-officers: %d counties | %s | boards %d, withheld %d | "
          "%d e-mails, %d phones | %d office(s) withheld for divergence, "
          "%d ISAC mislabel(s) corrected, %d pinned divergence(s)"
          % (len(directory), ", ".join("%s %d" % (k, filled[k]) for k, _ in OFFICES),
             boards, withheld, emails, phones, divergences, mislabels, resolved),
          file=sys.stderr)
    for line in withheld_detail:
        print("  supervisors withheld: %s" % line, file=sys.stderr)

    # An address on a domain that cannot receive mail is a contact a reader
    # gets no bounce from; the withhold list drops it and keeps the name,
    # office, party and phone beside it. Every drop and every stale entry
    # prints.
    for geoid, rec in directory.items():
        if not isinstance(rec, dict):
            continue
        for office, value in rec.items():
            if isinstance(value, dict) and value.get("email"):
                kept, _why = undeliverable.withhold(
                    value["email"], "%s %s" % (rec.get("county") or geoid, office))
                if kept is None:
                    del value["email"]

    payload = json.dumps(directory, indent=1, sort_keys=True) + "\n"
    if check_only:
        try:
            with open(OUT) as f:
                shipped = f.read()
        except OSError as e:
            raise RuntimeError("data/app/ia-county-officers.json is missing (%s) -- "
                               "run this script without --check" % e)
        if shipped != payload:
            raise RuntimeError("data/app/ia-county-officers.json has drifted from "
                               "the caches. Re-run: python3 "
                               "ia/scripts/build_ia_county_officers.py")
        print("check: shipped roster matches the caches", file=sys.stderr)
        return

    with open(OUT, "w") as f:
        f.write(payload)
    print("wrote data/app/ia-county-officers.json", file=sys.stderr)


if __name__ == "__main__":
    main()
