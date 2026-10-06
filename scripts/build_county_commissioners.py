#!/usr/bin/env python3
"""
Resolve scripts/il_county_commissioners_scraper.py's raw output into
data/app/il-county-commissioners.json — the at-large county boards the COUNTY
card renders.

Why this file exists separately from the county-board layer: a county that
elects its board at large has no district geometry, so there is nothing for a
`county-board` dispatch entry to join. Its members represent every resident of
the county, which is exactly what the county card already answers
(docs/EXPANSION_GUIDE.md §1.5). Adding one of these counties therefore adds no
layer, no toggle and no dispatch entry — only rows on a card that already
renders.

Keyed by county name normalized to uppercase letters only ("STCLAIR"), the
SAME key data/app/il-county-clerks.json uses, so index.html performs one
lookup shape for both rosters.

Usage:
    python3 build_county_commissioners.py <raw-scraper-output.json> [output_dir]
"""

import json
import os
import re
import sys
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)

# Every county here elects at large. The per-county seat count is the real
# guard — a board that suddenly parses one member short means the page changed
# shape, and that must not ship quietly. The range below is the backstop for a
# county added to the scraper before this table.
MIN_MEMBERS = 3
# Raised from 9 to 13 on 2026-08-21 for Saline, the largest at-large board in
# the file. This is only the backstop for a county added to the scraper before
# EXPECT_MEMBERS gets a row; the per-county count below is the real guard, and
# Saline has one. Widening this does NOT weaken any existing county.
MAX_MEMBERS = 13
EXPECT_MEMBERS = {
    "ALEXANDER": 3,                  # 2026-08-24; ALL THREE SEATS NAMED, closing the
                                     # shortfall this file carried since 2026-08-23.
                                     # Commission form proven from the county's own 7
                                     # May 2024 minutes (Chairman / Vice Chairman /
                                     # Commissioner in the letterhead) and countywide
                                     # election proven from its certified 2024 General
                                     # canvass, where "FOR COMMISSIONER" reports all
                                     # ELEVEN precincts — the same denominator the
                                     # presidential contest on that ballot reports. The
                                     # county's own team widget was proven stale on TWO
                                     # counts the same day (missing Essex entirely, and
                                     # Griggs/Smith's titles reversed), so the roster
                                     # moved to DOCUMENT_ROSTERS: an e-mail from the
                                     # Clerk & Recorder's office naming all three —
                                     # Chairman James (Jim) Smith, Vice Chairman Larry
                                     # (Steve) Essex, Member Joe E. Griggs.
    "MONROE": 3, "RANDOLPH": 3,      # commission form, 3 commissioners
    "PIKE": 9, "PUTNAM": 5, "BROWN": 7, "CALHOUN": 5,
    "SCHUYLER": 7,                   # pass-8; at-large proven from the canvass
    "GREENE": 7,                     # 2026-08-08; at-large proven from the county's
                                     # own OFFICIAL canvasses — "FOR COUNTY BOARD FOUR
                                     # YEAR TERM / 22 of 22 precincts / Vote for (4)".
                                     # The first County-card county that was ALREADY
                                     # served (7th-Circuit subcircuit) before its board
                                     # arrived, so it changes no ring and no anchor.
    "HAMILTON": 5,                   # pass-14; at-large stated by the Clerk, 2026-08-05
    "MOULTRIE": 9,                   # 2026-08-18; at-large proven from the Clerk's own
                                     # certified results — "COUNTY BOARD DISTRICT AT
                                     # LARGE MEMBER / 16 of 16 precincts / Vote For 5".
                                     # Found by the 34-county sweep of the
                                     # pollresults.net vendor, not by an e-mail: the
                                     # feed answers §2.5 step 2 without anyone replying.
                                     # Nine seats in staggered groups of five and four;
                                     # Sullivan moved from the OUTSIDE anchor list to
                                     # INSIDE in the same change.
    "MORGAN": 3,                     # 2026-08-08; commission form proven from the
                                     # county's OFFICIAL canvasses. Its roster comes from
                                     # morgancounty-il.COM — the .GOV is a content-free
                                     # React shell, and mistaking one for the other cost
                                     # this project a wrong gap record and nearly a wrong
                                     # e-mail to the Clerk.
    "EDWARDS": 3,                    # pass-14; commission form stated by the Clerk,
                                     # 2026-08-06. The first county whose roster is
                                     # not scraped from a page — Edwards has no website at
                                     # all, so its three come from a document the Clerk
                                     # sent (DOCUMENT_ROSTERS in the scraper), and the
                                     # scraper says so on every run.
    "SALINE": 13,                    # 2026-08-21; at-large proven from the county's own
                                     # certified 2026 primary canvass — "FOR MEMBERS OF THE
                                     # COUNTY BOARD / Precincts Counted 28 of 28 / (Vote for
                                     # not more than seven)" over all 15,441 registered
                                     # voters, with the Appellate Court contest on the same
                                     # page as the control. Corroborated by ISBE's structure
                                     # table (13, At-Large) — itself checked against four
                                     # counties this project can read — and by the county's
                                     # own unlabelled 13-member page. Seven of thirteen seats
                                     # each cycle is the stagger.
    "MASSAC": 3,                     # 2026-08-21; commission form proven from the county's
                                     # own published results — "FOR COUNTY COMMISSIONER /
                                     # Precincts Counted 17 of 17 / (Vote for one)" over
                                     # all 11,265 registered voters, with the countywide
                                     # Clerk contest on the same page as the control.
                                     # That report is marked Unofficial and is relied on
                                     # for the FORM only; the three names come from the
                                     # county's own commissioners page, never the returns.
                                     # A new ISLAND — all three Illinois neighbours
                                     # (Johnson, Pope, Pulaski) are unserved.
    "PULASKI": 3,                    # 2026-09-02; the roster half of a county already
                                     # served on precincts. At-large was settled on its
                                     # own record from the certified 2024 primary (one
                                     # countywide commissioner contest per party over
                                     # all eleven precincts); what was missing was who
                                     # holds the seats, because the gap record said the
                                     # county's website "cannot be reached from here".
                                     # IT CAN. The permutation this project uses to find
                                     # a county site derives it from the clerk's MAIL
                                     # domain, pulaskicountyil.gov, which serves no page;
                                     # the site is pulaskicountyil.net and its board page
                                     # names all three with a county e-mail each. The
                                     # page carried Last-Modified 2026-07-23 when read.
    "GALLATIN": 5,                   # 2026-08-21; at-large proven TWICE from the county's
                                     # own certified canvasses — "CO.BD.MEMBER CWD (VOTE
                                     # FOR) 3" in the 2026 primary and "COUNTY BOARD MEMBER
                                     # CWD (VOTE FOR) 2" in 2024, where CWD is the same
                                     # county-wide marker the Clerk, Treasurer and Sheriff
                                     # contests carry and district offices on the same
                                     # ballot do not. Five seats staggered three and two.
                                     # Reached only after the COLES PATTERN was found a
                                     # second time: gallatinco.illinois.gov omits its TLS
                                     # intermediate, so every automated client called the
                                     # county dark while the site answered 200 all along.
    "HARDIN": 3,                     # 2026-10-01; the THIRD no-website county
                                     # (DOCUMENT_ROSTERS). At-large was already proven
                                     # from certified returns before anyone replied —
                                     # its 2026 primary prints a committeeperson contest
                                     # per precinct per party and no district-suffixed
                                     # board contest anywhere — and Clerk Cowsert
                                     # confirmed both halves in writing: "Our county
                                     # board is elected countywide. And we do not have a
                                     # website in Hardin County." (2026-08-24). The three
                                     # names came by her reply of 2026-10-01. No e-mail
                                     # and no office ships: she assigns neither and the
                                     # county publishes no page to carry one.
    "WABASH": 3,                     # 2026-08-16; commission form stated in writing by
                                     # Clerk Will 2026-08-05, the three names sent by her
                                     # e-mail 2026-08-16. The SECOND no-website county
                                     # (DOCUMENT_ROSTERS): a mail domain with no web
                                     # server, measured 5 Aug and re-checked 9 Aug.
}
MIN_COUNTIES = 15
# How many counties may be CARRIED FORWARD from the shipped file in one run
# before the build refuses. Expressed as a fraction of the expected roster
# rather than a hand-set count, so it stays meaningful as counties are added.
#
# WHY CARRY FORWARD AT ALL. MIN_COUNTIES equals the number of counties this file
# actually ships, which means that before 2026-08-18 a SINGLE unreachable county
# failed the entire refresh and froze all twelve. That is not hypothetical: the
# 15 August run lost Greene to a 429, Pike and Brown to 403s, and Calhoun to a
# 200 that carried no members, and the whole job died — so eleven counties that
# answered perfectly well went unrefreshed for sixteen days because a handful of
# county websites do not like GitHub's runners. These are small county sites
# behind assorted edges; one of them having a bad afternoon is the normal case,
# not the alarming one.
#
# WHY A CEILING ON IT ANYWAY. Carrying forward is how the roster stays whole,
# but a run that carries most of the file is not a refresh at all — it is a
# systemic block wearing a green tick, and that is the state a human needs to
# see. Half is the line: below it, some sites were grumpy; at or above it,
# something changed about how this project reaches them.
MAX_CARRIED_FRACTION = 0.5
# Greene styles its chair "Chairwoman" and its deputy "Vice Chair". Both are
# the county's own words for real people and are kept verbatim rather than
# normalised to the -man forms, which would be a one-word misstatement.
# Moultrie writes "Chairperson" / "Vice Chairperson"; like Greene's
# "Chairwoman", those are the county's own words for real people and are kept
# verbatim rather than normalised, so the list widens instead.
# Massac (2026-08-21) writes "Secretary" for its third commissioner. It is a
# board OFFICE the county states, not a staff title: the page lists exactly
# three people under "Massac County Commissioners" and gives the third that
# word, so dropping it would print less than the county does. It is NOT a
# chair role — see CHAIR_ROLES below, which is deliberately not widened.
# Alexander (2026-08-24) writes plain "Member" for its third seat, in the
# Clerk's office's own e-mail alongside "Chairman" and "Vice Chairman" for the
# other two — the same "keep the county's own word" case as Greene's
# "Chairwoman" and Massac's "Secretary", not a staff title either.
ALLOWED_ROLES = ("Chairman", "Chairwoman", "Chairperson", "Vice Chairman",
                 "Vice-Chairman", "Vice Chair", "Vice Chairperson",
                 "Commissioner", "Board Member", "Member", "Secretary")
# Any of these means "this person chairs the board" for the one-chair guard.
# Matching the literal "Chairman" alone would have let Greene seat two chairs
# without a word, which is exactly the kind of silent hole widening
# ALLOWED_ROLES can open.
CHAIR_ROLES = ("Chairman", "Chairwoman", "Chairperson")
# Widening ALLOWED_ROLES without widening THIS is the hole the comment above
# warns about: Moultrie styles its chair "Chairperson", and had it landed only
# in ALLOWED_ROLES the one-chair guard would have stopped counting it.

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")


fail = make_fail("county-commissioners-roster")


def norm_key(name):
    return re.sub(r"[^A-Z]", "", re.sub(r"\s*COUNTY\s*$", "", (name or "").upper()))


def load_shipped(out_dir):
    """The roster as it currently ships, for counties this run could not read."""
    path = os.path.join(out_dir, "il-county-commissioners.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def main():
    if len(sys.argv) < 2:
        fail("usage: build_county_commissioners.py <raw-scraper-output.json> [output_dir]")
    with open(sys.argv[1], encoding="utf-8") as f:
        counties = json.load(f)["counties"]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_DIR

    # Counties the scraper could not read this run keep their last shipped entry
    # rather than vanishing or failing the job. The scraper has already said why
    # each one was skipped; this says, per county, that what ships is not fresh.
    shipped = load_shipped(out_dir)
    carried = sorted(set(shipped) - set(counties))
    for key in carried:
        counties[key] = shipped[key]
        print("county-commissioners-roster: NOT RE-READ — %s was not readable this "
              "run; carrying its %d shipped members forward unchanged."
              % (key, len(shipped[key].get("members") or [])), file=sys.stderr)
    if carried and len(carried) >= max(1, int(len(counties) * MAX_CARRIED_FRACTION)):
        fail("%d of %d counties were unreadable this run (%s) — that is not a few "
             "grumpy sites, it is a change in how this project reaches them. "
             "Refusing to ship a roster that is mostly last week's."
             % (len(carried), len(counties), ", ".join(carried)))

    roster = {}
    for key, block in counties.items():
        members = block.get("members") or []
        expect = EXPECT_MEMBERS.get(key)
        # THE EXACT COUNT WINS WHERE THERE IS ONE. MIN/MAX_MEMBERS is the
        # backstop for a county added to the scraper before it earns a row here,
        # and applying it on top of an exact count would be worse than useless:
        # Alexander publishes TWO members of a three-seat board, which its own
        # row states precisely and which the generic floor would reject.
        if expect is None:
            if not (MIN_MEMBERS <= len(members) <= MAX_MEMBERS):
                fail("%s parsed %d members, outside the %d-%d an at-large board "
                     "should have" % (key, len(members), MIN_MEMBERS, MAX_MEMBERS))
        elif len(members) != expect:
            fail("%s parsed %d members, the county publishes %d — the page's shape "
                 "changed, or the board did. Re-read it before shipping."
                 % (key, len(members), expect))
        # `seats` is the size of the BOARD, which is not always the length of the
        # list a county publishes. It is carried only where the two differ, and
        # it may never be smaller than the roster: a board with fewer seats than
        # members is a reading error, not a finding.
        seats = block.get("seats")
        if seats is not None:
            if not isinstance(seats, int) or seats < len(members):
                fail("%s declares %r seats against %d members — a board cannot "
                     "seat fewer people than it lists" % (key, seats, len(members)))
            if seats == len(members):
                fail("%s declares seats equal to its member count; drop the field "
                     "rather than shipping a shortfall of nothing" % key)
        names = [m.get("name") for m in members]
        if len(set(names)) != len(names):
            fail("%s has duplicate member names (%s)" % (key, ", ".join(sorted(names))))
        chairs = [m["name"] for m in members if m.get("role") in CHAIR_ROLES]
        if len(chairs) > 1:
            fail("%s marks %d chairmen (%s) — a board has one" % (key, len(chairs), ", ".join(chairs)))
        clean_members = []
        for m in members:
            if not m.get("name"):
                fail("%s has a member with no name" % key)
            role = m.get("role")
            if role and role not in ALLOWED_ROLES:
                fail("%s: unrecognized role %r for %s" % (key, role, m["name"]))
            entry = {"name": m["name"]}
            # `seat` and `districtSource` carry the RETURNS tier's provenance:
            # which lettered seat a commissioner holds, and which certified
            # election seated them. A roster read from canvasses cannot show a
            # mid-term appointment, so the row says what it is rather than
            # implying a currency it does not have (the Clark rule). `party` is
            # in the returns and is the county's own certification of it.
            for f_ in ("role", "seat", "party", "phone", "email", "since",
                       "districtSource"):
                if m.get(f_):
                    entry[f_] = m[f_]
            clean_members.append(entry)

        expected = norm_key(block.get("county"))
        if expected and expected != key:
            fail("%s is keyed inconsistently with its county name %r (expected key %s)"
                 % (key, block.get("county"), expected))

        out = {
            "county": block.get("county"),
            "structure": block.get("structure"),
            "members": clean_members,
        }
        if seats is not None:
            out["seats"] = seats
        # Provenance, and exactly one kind of it. Eight counties are scraped
        # from a page and carry sourceUrl; Edwards has no website at all and
        # carries the document its Clerk sent plus the date it was verified.
        # A county with neither would be a roster nobody can trace, so it fails
        # rather than shipping anonymous names.
        if block.get("sourceUrl"):
            out["sourceUrl"] = block["sourceUrl"]
        elif block.get("sourceDocument"):
            out["sourceDocument"] = block["sourceDocument"]
            if block.get("verified"):
                out["verified"] = block["verified"]
        else:
            fail("%s has neither a sourceUrl nor a sourceDocument — a shipped "
                 "roster must say where its names came from" % key)
        office = block.get("office") or {}
        office = {k: v for k, v in office.items() if v}
        if office:
            out["office"] = office
        roster[key] = out

    if len(roster) < MIN_COUNTIES:
        fail("only %d counties resolved (expected >= %d)" % (len(roster), MIN_COUNTIES))

    out_path = os.path.join(out_dir, "il-county-commissioners.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(roster, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    total = sum(len(v["members"]) for v in roster.values())
    contacts = sum(1 for v in roster.values() for m in v["members"] if m.get("email") or m.get("phone"))
    print("county-commissioners-roster: %d counties, %d members (%d with contact) -> %s"
          % (len(roster), total, contacts, out_path))


if __name__ == "__main__":
    main()
