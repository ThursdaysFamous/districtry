#!/usr/bin/env python3
"""
Resolve scripts/shelby_county_board_scraper.py's raw output into
data/app/shelby-county-board-members.json, keyed by board district number.

Shelby seats twenty-two members across eleven NUMBERED districts, two each,
and elects its Chair and Vice Chair from among them (both currently hold
District 3's seats; each carries a role alias e-mail beside the district
address). A vacant seat ships AS a vacancy — the county prints "Currently
Vacant" with the seat's e-mail, and so does the card; dropping it would
misstate the board's size, and inventing a name is against the house rules.

TWO CROSS-CHECKS run on every build:

  1. COMPOSITION (the DeWitt pattern) — the same page this roster comes from
     is the authority for the district BOUNDARIES:
     scripts/build_shelby_board_districts.py dissolves Census voting
     districts per the composition printed on it, including the one split
     precinct (Shelbyville 5, cut by Rt 16 and Lake Shelbyville). This
     builder re-parses the composition the scraper captured and compares it,
     precinct by precinct and split-piece by split-piece, to the one
     compiled into that script. A redistricting therefore fails the weekly
     roster job loudly instead of leaving the shipped boundary quietly a
     cycle out of date.
  2. CONTACTS — the county publishes the roster twice (coboard.aspx cards,
     contacts.aspx e-mail directory). Every directory row must match a card
     seat by e-mail and name, and both role aliases must land on the members
     the cards tag as Chair and Vice Chair. A half-updated site — one page
     edited, the other forgotten — fails here instead of shipping whichever
     page the scraper happened to read.

Home addresses are printed on every card and are NEVER shipped (the
Mason/Marshall precedent); stage 1 does not even capture them.

Usage:
    python3 build_shelby_board_roster.py <raw-scraper-output.json> [output_dir]
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_shelby_board_districts import (  # noqa: E402
    COMPOSITION, EXPECT_PRECINCTS,
)
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)

BOARD_URL = "https://www.shelbycounty-il.gov/coboard.aspx"
CONTACTS_URL = "https://www.shelbycounty-il.gov/contacts.aspx"

SEATS_PER_DISTRICT = 2
MIN_PHONES = 18   # 20 of the 22 seats carry one today; vacants carry none
MIN_EMAILS = 20   # every seat carries one today, vacant or not
ALLOWED_ROLES = ("Chair", "Vice Chair")
ALLOWED_PARTIES = ("Republican", "Democrat", "Democratic", "Independent")
# A bare year is a format the county actually publishes, not a parse
# accident: on 2026-08-19 a new appointee (Shawn Conlin) appeared as
# "Term 2026" — no start year, no "through" — alongside the usual
# "2022–2026" spans and one "through 2026". The card renders the value
# verbatim behind a "Term " prefix, so accepting it ships the county's
# own words; rejecting it froze the whole roster over one member's
# formatting and left his predecessor on the card.
TERM_RE = re.compile(r"^(\d{4}–\d{4}|\d{4}|through \d{4})$")
VACANT_NAMES = ("currently vacant",)
MAX_DIRECTORY_DRIFT = 2  # tolerated per-direction directory/card row drift mid-edit

# THE COUNTY CORRECTED AN E-MAIL TYPO ON ONE OF ITS TWO PAGES AND NOT THE OTHER,
# which broke the e-mail join below and refused the 2026-09-09 run. Measured that
# day, both pages fetched live:
#
#   coboard.aspx  (21,196 bytes)  distric1-2@shelbycounty-il.gov   x2, no 'h'
#   contacts.aspx (15,430 bytes)  district1-2@shelbycounty-il.gov  x1, corrected
#
# The two occurrences on coboard.aspx are one authored value the template repeats
# as href and link text, so this is a single typo rather than two.
#
# THIS IS NOT THIS PROJECT CORRECTING A CHARACTER IN SOMEBODY'S CONTACT DETAIL,
# and the difference from the DOUGLAS precedent is the whole reason it is allowed
# here. Douglas's yearbook printed District 1's address on `douglascountuil.gov`,
# a typo in the DOMAIN; nothing else published a corrected form, a DNS check
# proved that domain dead, and build_douglas_boundaries DROPPED the address
# rather than ship a bouncing one or edit a character. Three things differ here:
# the domain is identical and correct on both pages, a SECOND county surface
# publishes the corrected local part, and the pages' own convention corroborates
# it. CORRECTED 2026-09-09, having been overstated when first written: this
# said all TWENTY of the other seat addresses read `district<N>-<M>@`, and
# NINETEEN do. The twentieth is District 2's first seat, `district2@`, with no
# `-1` at all — published IDENTICALLY on both pages, so nothing disagrees, no
# join breaks and it is out of scope here. What holds either way is the part
# the argument rests on: every one of them spells `district` in full, and
# `distric1-2@` is the only address on either page that does not.
#
# WHICH SURFACE OWNS AN E-MAIL ADDRESS is what settles it, the Greene/Scott
# question asked of a contact detail instead of a place name. contacts.aspx IS
# the county's e-mail directory; coboard.aspx is the board page that also happens
# to print addresses. The directory wins, exactly as Merritt's spelling did.
#
# NEITHER SPELLING'S DELIVERABILITY IS TESTED and nothing here claims it. A
# domain's MX says nothing about a local part, and probing a mailbox is not
# something this project does to a county. What is claimed is only which form the
# county publishes where.
#
# NOT DATED, AND THAT IS A MEASUREMENT LIMIT RATHER THAN AN ABSENT FACT: when the
# county made the correction cannot be established from here, because this
# environment's egress proxy blocks web.archive.org outright
# (`x-block-reason: hostname_blocked`), which is not the Archive refusing.
#
# audit_email_corrections() FAILS when an entry stops being needed, so this
# cannot outlive the typo it exists for -- the ACCEPTED_DROPS discipline.
BOARD_EMAIL_CORRECTIONS = {
    "distric1-2@shelbycounty-il.gov": "district1-2@shelbycounty-il.gov",
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")


fail = make_fail("shelby-board-roster")


def norm(name):
    return " ".join(str(name or "").upper().split())


def norm_side(side):
    if side is None:
        return None
    return " ".join(re.sub(r"[–—]", "-", str(side)).split()).upper()


def parse_precincts(text):
    """A composition line as a set of (TOWNSHIP, number|None, side|None).

    "Moweaqua Precincts 1 and 2"    -> {(MOWEAQUA, 1, None), (MOWEAQUA, 2, None)}
    "Precincts of Penn, Flat Branch" -> {(PENN, None, None), (FLAT BRANCH, ...)}
    "part of Shelbyville Precinct 5 (S of Rt 16)" -> {(SHELBYVILLE, 5, "S OF RT 16")}

    A bare township means "all of that township's precincts", exactly as it
    does on De Witt's page — District 6's "Prairie" is the layer's PRAIRIE 1.
    """
    t = re.sub(r"[–—]", "-", text or "")
    sides = []

    def stash(m):
        sides.append(m.group(1).strip())
        return " @%d " % (len(sides) - 1)

    t = re.sub(r"\(([^)]*)\)", stash, t)
    t = re.sub(r"^\s*Precincts?\s+of\s+", "", t, flags=re.I)
    t = re.sub(r"\bpart\s+of\b", " ", t, flags=re.I)
    out, current = set(), None
    for chunk in re.split(r"\s*,\s*|\s+and\s+|\s*&\s*", t):
        chunk = chunk.strip()
        if not chunk:
            continue
        side = None
        m = re.search(r"@(\d+)", chunk)
        if m:
            side = norm_side(sides[int(m.group(1))])
            chunk = chunk[:m.start()].strip()
        m = re.match(r"^(.*?)\s+Precincts?\s+(\d+)$", chunk, re.I)
        if m:
            current = norm(m.group(1))
            out.add((current, int(m.group(2)), side))
            continue
        m = re.match(r"^(.*?)\s+Precincts?$", chunk, re.I)
        if m:
            current = norm(m.group(1))
            out.add((current, None, side))
            continue
        if re.fullmatch(r"\d+", chunk):
            if current is None:
                fail("composition %r opens with a bare precinct number" % text)
            out.add((current, int(chunk), side))
            continue
        current = norm(chunk)
        out.add((current, None, side))
    return out


def compiled_triples(district):
    """The boundary script's composition in the same triple shape."""
    out = set()
    for member in COMPOSITION[district]:
        name, side = member if isinstance(member, tuple) else (member, None)
        m = re.match(r"^(.*?)\s+(\d+)$", name)
        if m:
            out.add((norm(m.group(1)), int(m.group(2)), norm_side(side)))
        else:
            out.add((norm(name), None, norm_side(side)))
    return out


def compare_composition(published, shipped):
    """Human-readable difference, or None when they agree. A township the
    county writes BARE matches however the shipped side enumerates it."""
    pub_t = {t for t, _, _ in published}
    shp_t = {t for t, _, _ in shipped}
    if pub_t != shp_t:
        bits = []
        if pub_t - shp_t:
            bits.append("the county now includes %s" % ", ".join(sorted(pub_t - shp_t)))
        if shp_t - pub_t:
            bits.append("the county no longer includes %s" % ", ".join(sorted(shp_t - pub_t)))
        return "; ".join(bits)
    for township in sorted(pub_t):
        pub = {(n, s) for t, n, s in published if t == township}
        shp = {(n, s) for t, n, s in shipped if t == township}
        if pub == {(None, None)}:
            continue                     # written bare = all of it
        if pub != shp:
            return ("%s changed: the county now says %s, the shipped boundary "
                    "was built from %s" % (township, sorted(pub), sorted(shp)))
    return None


def apply_email_corrections(records):
    """Rewrite a stale board-page e-mail to the directory's spelling.

    Applied to the CARD records only, and PRINTED every run: this is a
    substitution in a real person's contact detail, so it is never silent.
    Returns the set of keys actually seen, for audit_email_corrections().
    """
    seen = set()
    for rec in records:
        for m in rec.get("members") or []:
            fixed = []
            for email in m.get("emails") or []:
                better = BOARD_EMAIL_CORRECTIONS.get(email)
                if better:
                    seen.add(email)
                    print("shelby-board-roster: coboard.aspx spells %s's address "
                          "%s; shipping %s, which contacts.aspx publishes and "
                          "which matches the county's own pattern on every "
                          "other seat" % (m.get("name") or "?", email, better))
                    fixed.append(better)
                else:
                    fixed.append(email)
            if fixed:
                m["emails"] = fixed
    return seen


def audit_email_corrections(seen):
    """FAIL on an entry that is no longer needed.

    The county fixing coboard.aspx is the good outcome, and it must not leave a
    substitution sitting in this file forever rewriting an address nobody
    publishes any more. Same shape as ACCEPTED_DROPS and EXPECTED_UNREACHABLE:
    an exception that cannot rot quietly.
    """
    orphans = sorted(set(BOARD_EMAIL_CORRECTIONS) - seen)
    if orphans:
        fail("BOARD_EMAIL_CORRECTIONS still maps %s, which coboard.aspx no "
             "longer carries — the county has fixed its own page, so remove "
             "the entry" % ", ".join(orphans))


def main():
    if len(sys.argv) < 2:
        fail("usage: build_shelby_board_roster.py <raw-scraper-output.json> [output_dir]")
    with open(sys.argv[1], encoding="utf-8") as f:
        raw = json.load(f)
    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_DIR
    records = raw.get("records") or []
    contacts = raw.get("contacts") or []
    updated = raw.get("updated")
    audit_email_corrections(apply_email_corrections(records))

    if sorted(r["district"] for r in records) != sorted(COMPOSITION, key=str):
        fail("parsed districts %s, expected exactly %s"
             % (sorted(r["district"] for r in records),
                sorted(COMPOSITION, key=str)))

    # --- the composition cross-check (see the module header)
    total_precincts = 0
    for rec in records:
        district = rec["district"]
        if not rec.get("composition"):
            fail("district %s published no precinct composition — the page's "
                 "shape changed, and the shipped boundary can no longer be "
                 "cross-checked" % district)
        published = parse_precincts(rec["composition"])
        diff = compare_composition(published, compiled_triples(district))
        if diff:
            fail("district %s composition CHANGED — %s. Re-read %s and rebuild "
                 "data/app/shelby-county-board-districts.json before shipping "
                 "this roster." % (district, diff, BOARD_URL))
        total_precincts += len(published)
    # The county names each whole precinct once and the split one three times
    # across the eleven cards; the parser collapsing a name would show here.
    if total_precincts != EXPECT_PRECINCTS + 2:
        fail("the eleven composition lines parse to %d precinct references, "
             "expected %d" % (total_precincts, EXPECT_PRECINCTS + 2))

    # --- resolve members
    roster = {}
    seat_by_email = {}
    for rec in records:
        district = rec["district"]
        members = []
        for m in rec.get("members") or []:
            if len(m.get("emails") or []) < 1:
                fail("district %s seat %r carries no e-mail" % (district, m.get("name")))
            if m.get("vacant"):
                member = {"name": m["name"], "vacant": True, "email": m["emails"][0]}
            else:
                if not m.get("name"):
                    fail("district %s has a nameless non-vacant seat" % district)
                if m.get("party") not in ALLOWED_PARTIES:
                    fail("%s carries unrecognized party %r" % (m["name"], m.get("party")))
                if not m.get("term") or not TERM_RE.match(m["term"]):
                    fail("%s carries unrecognized term %r" % (m["name"], m.get("term")))
                member = {"name": m["name"], "party": m["party"], "term": m["term"],
                          "email": m["emails"][0]}
                if m.get("phone"):
                    # A new appointee's card can carry "TBD" where the phone
                    # goes (Shawn Conlin, 2026-08-19). A placeholder is an
                    # honest "none yet", not a number — ship no phone rather
                    # than a card row reading TBD.
                    if len(re.sub(r"\D", "", m["phone"])) >= 7:
                        member["phone"] = m["phone"]
                    else:
                        print("shelby-board-roster: %s's phone reads %r — a "
                              "placeholder, not a number; not shipped"
                              % (m["name"], m["phone"]))
                if m.get("role"):
                    if m["role"] not in ALLOWED_ROLES:
                        fail("%s carries unrecognized role %r" % (m["name"], m["role"]))
                    member["role"] = m["role"]
                    if len(m["emails"]) > 1:
                        member["roleEmail"] = m["emails"][1]
            members.append(member)
            for email in m["emails"]:
                if email in seat_by_email:
                    fail("e-mail %s appears on two seats" % email)
                seat_by_email[email] = (district, m)
        if len(members) != SEATS_PER_DISTRICT:
            fail("district %s has %d seats, the county seats exactly %d per "
                 "district" % (district, len(members), SEATS_PER_DISTRICT))
        roster[district] = {"members": members, "sourceUrl": BOARD_URL,
                            "contactsUrl": CONTACTS_URL}
        if updated:
            roster[district]["updated"] = updated

    all_members = [m for e in roster.values() for m in e["members"]]
    for role in ALLOWED_ROLES:
        held = [m["name"] for m in all_members if m.get("role") == role]
        if len(held) != 1:
            fail("%d members marked %s (%s) — the board has one"
                 % (len(held), role, ", ".join(held) or "none"))
    phones = sum(1 for m in all_members if m.get("phone"))
    emails = sum(1 for m in all_members if m.get("email"))
    if phones < MIN_PHONES:
        fail("only %d phones resolved (expected >= %d)" % (phones, MIN_PHONES))
    if emails < MIN_EMAILS:
        fail("only %d e-mails resolved (expected >= %d)" % (emails, MIN_EMAILS))

    # --- the contacts cross-check (see the module header)
    role_rows = [c for c in contacts if not c["office"].startswith("District")]
    seat_rows = [c for c in contacts if c["office"].startswith("District")]
    # The two pages are hand-edited at different times, and a member swap
    # reaches the cards first: on 2026-08-19 Shawn Conlin was seated on the
    # cards while the directory still carried his predecessor, and the old
    # strict equality froze the whole roster on the stale name. The
    # transition has an exact shape — a directory row naming somebody the
    # cards no longer seat at all, or a card member the directory has not
    # caught up with — and ONLY that shape is tolerated, WARNed by name,
    # capped at MAX_DIRECTORY_DRIFT rows each way (a directory page that
    # collapses or a parser that loses the table blows past the cap and
    # still fails). A row whose e-mail does hit a card seat must agree with
    # it exactly, and a row whose NAME is a current member under an unknown
    # e-mail still fails: that is a live disagreement about a sitting
    # member, not a leftover.
    matched_emails = set()
    leftovers = 0
    for row in seat_rows:
        hit = seat_by_email.get(row["email"])
        if hit is None:
            if any(norm(row["name"]) == norm(m["name"]) for m in all_members):
                fail("contacts.aspx row %r carries an e-mail no card seat has" % row)
            leftovers += 1
            print("shelby-board-roster: WARN — contacts.aspx still lists %r "
                  "(%s) on %s, whom the cards no longer seat; skipped as a "
                  "departed member's leftover row"
                  % (row["name"], row["email"], row["office"]))
            continue
        matched_emails.add(row["email"])
        district, m = hit
        if row["office"] != "District %s" % district:
            fail("contacts.aspx puts %s in %r, the cards in District %s"
                 % (row["email"], row["office"], district))
        if norm(row["name"]) != norm(m["name"]):
            fail("contacts.aspx names %r on the seat the cards give %r (%s) — "
                 "the two pages disagree; the county is mid-edit"
                 % (row["name"], m["name"], row["email"]))
    behind = [m["name"] for m in all_members if m["email"] not in matched_emails]
    for name in behind:
        print("shelby-board-roster: WARN — %s has no contacts.aspx row yet"
              % name)
    if leftovers > MAX_DIRECTORY_DRIFT or len(behind) > MAX_DIRECTORY_DRIFT:
        fail("contacts.aspx and coboard.aspx disagree on %d leftover + %d "
             "missing rows — more than a member swap in flight (max %d each); "
             "one of the two pages changed shape"
             % (leftovers, len(behind), MAX_DIRECTORY_DRIFT))
    expect_role_offices = {"Board Chair": "Chair", "Board Vice Chair": "Vice Chair"}
    if sorted(c["office"] for c in role_rows) != sorted(expect_role_offices):
        fail("contacts.aspx role rows are %s, expected %s"
             % (sorted(c["office"] for c in role_rows), sorted(expect_role_offices)))
    for row in role_rows:
        want_role = expect_role_offices[row["office"]]
        holder = next(m for m in all_members if m.get("role") == want_role)
        if norm(row["name"]) != norm(holder["name"]):
            fail("contacts.aspx says %s is %r, the cards say %r"
                 % (row["office"], row["name"], holder["name"]))
        if holder.get("roleEmail") != row["email"]:
            fail("the %s alias is %r on contacts.aspx but %r on the cards"
                 % (row["office"], row["email"], holder.get("roleEmail")))

    out_path = os.path.join(out_dir, "shelby-county-board-members.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(roster, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    vacants = sum(1 for m in all_members if m.get("vacant"))
    print("shelby-board-roster: %d districts, %d seats (%d filled, %d vacant; "
          "%d phones, %d e-mails; Chair + Vice Chair verified against the "
          "e-mail directory); composition matches the shipped boundary in all "
          "11 districts -> %s"
          % (len(roster), len(all_members), len(all_members) - vacants, vacants,
             phones, emails, out_path))


if __name__ == "__main__":
    main()
