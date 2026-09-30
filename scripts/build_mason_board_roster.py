#!/usr/bin/env python3
"""
Write data/app/mason-county-board-members.json from the County Clerk's own
published spreadsheet, cross-checked against the hand transcription it replaced.

WHY THERE WAS NO SCRAPER UNTIL 2026-08-04. Mason publishes its board roster as one PDF, and that
PDF is a SCAN — a single 1690x2216 greyscale JPEG. It does carry a text layer,
which is the trap: the layer is written in a non-embedded Helvetica whose
encoding does not survive extraction, so pdfplumber and pdftotext both return
line noise ("xRF# ISgH tlgP  E:AS eh9A") rather than failing. A scraper reading
that would not error — it would produce confident garbage and ship it under a
real officeholder's name. So the roster is transcribed by hand from the scan
(2026-08-02), which is the fleet's existing posture for sources automation
cannot read (Kendall, McHenry, the early-voting sites).

WHAT CHANGED. On 2026-08-04 the Clerk's elections office shared the county's
own "Mason County Directory" as a Google Sheet — owned by countyclerk@
masoncountyil.gov, readable by anyone with the link, and exportable as CSV. The
scan is no longer the only machine-reachable copy of the roster, so this build
now READS that sheet. The hand transcription below is kept, and it is not
decoration: the sheet is parsed on every run and compared against it, so the
first time the county changes a member the difference is printed rather than
applied silently. It confirmed the transcription exactly on the day it arrived
— all eight members, every name, party, phone, e-mail, term year and both
officer roles.

WHAT STILL WATCHES THE SCAN. scripts/mason_roster_watch.py runs weekly and checks
two things it CAN check without reading the scan: that the county-board page
still links this exact PDF (a superseded roster almost always lands at a new
WordPress upload path, leaving the old URL serving the old file forever), and
that the PDF's bytes still hash to the fingerprint recorded here. Either
change opens a tracking issue asking for a fresh human read. It never edits
this file — a scan cannot be re-read automatically, so a change is a request
for a person, not a diff.

NO RESIDENCE DATA AT ALL, INCLUDING THE TOWN. The county prints every member's
home address, and one member's row reads "SECURED ADDRESS" — she is in an
address-confidentiality program. The fleet never collects home addresses (the
Madison precedent), and here that is extended one column further: the HOME TOWN
is dropped for every member too. Shipping town-for-seven-and-blank-for-one
would make the protected member the one row that stands out, which is the exact
outcome the protection exists to prevent — and the card already carries name,
district, party, role, phone, e-mail and term year without it.

Usage:
    python3 scripts/build_mason_board_roster.py
    python3 scripts/build_mason_board_roster.py --check
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_mason_board_districts import SEATS_PER_DISTRICT  # noqa: E402
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    make_fail,
    require_robots_once,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "mason-county-board-members.json")

SOURCE_URL = "https://masoncountyil.gov/county-board/"
ROSTER_PDF = "https://masoncountyil.gov/wp-content/uploads/2026/05/Board-Members-.pdf"
TRANSCRIBED = "2026-08-02"

PARTY = {"D": "Democratic", "R": "Republican"}

# Transcribed verbatim from the scan, left to right, in the order the table
# prints them. Address and City columns are deliberately absent (see header).
#
# The Position column carries two free-text notes the county wrote about
# mid-term changes — Bender was appointed 05/12/2026, Sarnes's seat went vacant
# 11/03/2025 — and both say the member "will run for full term in 2026". Those
# are the county's words about how a member reached the seat, not an office, so
# they ride `seatNote` and are rendered as a note rather than as a badge.
MEMBERS = [
    # District 1
    {"name": "Kimi S. Bender", "district": "1", "party": "D",
     "phone": "309-259-0402", "email": "bender70boss@yahoo.com", "termExpires": 2026,
     "seatNote": "Appointed 05/12/2026 — will run for full term in 12/2026"},
    {"name": "Scott Garlisch", "district": "1", "party": "R",
     "phone": "217-414-8470", "email": "garlischfarms@gmail.com", "termExpires": 2028},
    {"name": "Dorothy J. Kreiling", "district": "1", "party": "R", "role": "Vice-Chairman",
     "phone": "309-597-2124", "email": "djhouse@casscomm.com", "termExpires": 2026},
    {"name": "Ronald Knollenberg", "district": "1", "party": "R",
     "phone": "217-482-5351", "email": "rknoll4020@gmail.com", "termExpires": 2028},
    # District 2
    {"name": "Kenneth Walker", "district": "2", "party": "D", "role": "Chairman",
     "phone": "309-360-1723", "email": "kr44walker@gmail.com", "termExpires": 2026},
    {"name": "Brenda Davenport-Fornoff", "district": "2", "party": "R",
     "phone": "309-357-0999", "email": "davenportfornoff@casscomm.com", "termExpires": 2028},
    {"name": "Adam Sarnes", "district": "2", "party": "D",
     "phone": "309-338-8319", "email": "adamsarnes11@gmail.com", "termExpires": 2026,
     "seatNote": "Seat vacant 11/03/2025 — will run for full term in 2026"},
    {"name": "Andrea Holtmeyer Thomson", "district": "2", "party": "D",
     "phone": "309-202-8796", "email": "athomson.mcboard@gmail.com", "termExpires": 2028},
]

SHEET_ID = "1pffRO68CZLhQkVmFKlmDy_J1YyaDlYDkS2TATLpeNkQ"
SHEET_TAB = "County Board Members"
SHEET_URL = ("https://docs.google.com/spreadsheets/d/%s/gviz/tq"
             "?tqx=out:csv&sheet=%s" % (SHEET_ID, SHEET_TAB.replace(" ", "%20")))
SHEET_NOTE = ("Mason County Clerk & Recorder, \"Mason County Directory\" "
              "(County Board Members tab), shared 2026-08-04")
ROLE_WORDS = ("Chairman", "Vice-Chairman")


def normalize_note(text):
    """The county's own seat note, punctuated so a card cannot misread it.

    Two transforms, both documented because neither may change a fact:

    1. The sheet writes the separator as a bare hyphen, sometimes with no
       spaces ("Vacant 11/03/2025-Will run for full term in 2026"). It becomes
       a spaced em dash so the note reads as one sentence.
    2. A note that OPENS with "Vacant" is prefixed "Seat ". On the card the note
       sits directly under a named member, and "Vacant 11/03/2025" under
       "Adam Sarnes" reads as though the person is vacant. He is not — he holds
       the seat that fell vacant on that date, which is what the county means
       and what its own Position column is describing.

    Nothing else is touched: no word is dropped, added or reordered.
    """
    note = re.sub(r"\s*-\s*", " — ", (text or "").strip())
    note = re.sub(r"\s+", " ", note)
    if note.lower().startswith("vacant"):
        note = "Seat " + note[0].lower() + note[1:]
    return re.sub(r"— Will run", "— will run", note)

EXPECT_DISTRICTS = ("1", "2")
PHONE_RE = re.compile(r"^\d{3}-\d{3}-\d{4}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
ADDRESS_RE = re.compile(r"\b\d+\s+(N|S|E|W|CR|County Road)\b", re.I)


fail = make_fail("mason-board-roster")


def fetch_sheet_members():
    """The Clerk's published tab, parsed into the same shape as MEMBERS.

    A gviz request for an unknown tab silently returns the FIRST sheet rather
    than erroring, so the parse asserts it found the board header before
    trusting anything it read."""
    import csv as _csv
    import io as _io
    import requests
    from build_metro_outline import HEADERS, REQUEST_TIMEOUT
    require_robots_once(SHEET_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-mason-board-roster")
    resp = requests.get(SHEET_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    rows = [[c.strip() for c in r] for r in _csv.reader(_io.StringIO(resp.text))]
    if not any("MEMBERS OF THE MASON COUNTY BOARD" in " ".join(r) for r in rows[:5]):
        fail("the %r tab did not come back — gviz returns the first sheet for an "
             "unknown tab name, and this is not the board tab" % SHEET_TAB)
    out = []
    for row in rows:
        if len(row) < 8:
            continue
        name, _addr, email, _city, phone, district, party, term = row[:8]
        position = row[8] if len(row) > 8 else ""
        if district not in EXPECT_DISTRICTS or not EMAIL_RE.match(email or ""):
            continue
        member = {"name": name, "district": district, "party": party,
                  "phone": (phone or "").replace("/", "-"), "email": email,
                  "termExpires": int(term)}
        role = next((w for w in ROLE_WORDS if position.strip() == w), None)
        if role:
            member["role"] = role
        elif position.strip():
            member["seatNote"] = normalize_note(position)
        out.append(member)
    return out


def compare_to_transcription(scraped):
    """Print any drift between the Clerk's sheet and the recorded transcription.

    NOT a failure: a difference is how turnover looks, and the sheet is the
    source. It is printed so the first divergence is seen by a person rather
    than shipped silently."""
    def key(m):
        return (m["name"], m["district"], m["party"], m["phone"], m["email"],
                str(m["termExpires"]), m.get("role") or "")
    a = {key(m) for m in scraped}
    b = {key(m) for m in MEMBERS}
    if a == b:
        return "sheet matches the %s transcription exactly (8/8)" % TRANSCRIBED
    added = sorted(x[0] for x in a - b)
    gone = sorted(x[0] for x in b - a)
    return ("SHEET DIFFERS from the %s transcription — now on the sheet: %s; no "
            "longer: %s. The sheet is the source; review before merging."
            % (TRANSCRIBED, ", ".join(added) or "(none)", ", ".join(gone) or "(none)"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify the shipped file, write nothing")
    ap.add_argument("--offline", action="store_true",
                    help="build from the recorded transcription without fetching the sheet")
    args = ap.parse_args()

    if args.offline:
        source, drift = MEMBERS, "offline — built from the recorded transcription"
    else:
        source = fetch_sheet_members()
        if len(source) != len(MEMBERS):
            fail("the Clerk's sheet parsed %d members, the county seats %d — refusing "
                 "to ship a partial board" % (len(source), len(MEMBERS)))
        drift = compare_to_transcription(source)

    roster = {}
    for m in source:
        d = m["district"]
        if d not in EXPECT_DISTRICTS:
            fail("member %s sits in district %r, which the county does not have" % (m["name"], d))
        if not PHONE_RE.match(m.get("phone") or ""):
            fail("%s has no well-formed phone (%r)" % (m["name"], m.get("phone")))
        if not EMAIL_RE.match(m.get("email") or ""):
            fail("%s has no well-formed e-mail (%r)" % (m["name"], m.get("email")))
        # Belt and braces on the header's promise: no residence data, in any
        # field, ever reaches the shipped file.
        for key, value in m.items():
            if isinstance(value, str) and ADDRESS_RE.search(value):
                fail("%s's %s looks like a street address (%r) — Mason ships no "
                     "residence data at all" % (m["name"], key, value))
        member = {"name": m["name"], "party": PARTY[m["party"]], "termExpires": m["termExpires"],
                  "phone": m["phone"], "email": m["email"]}
        if m.get("role"):
            member["role"] = m["role"]
        if m.get("seatNote"):
            member["seatNote"] = m["seatNote"]
        roster.setdefault(d, {"members": [], "sourceUrl": SOURCE_URL,
                              "rosterPdf": ROSTER_PDF, "transcribed": TRANSCRIBED})
        roster[d]["members"].append(member)

    if sorted(roster) != sorted(EXPECT_DISTRICTS):
        fail("transcribed districts %s, expected exactly %s"
             % (sorted(roster), list(EXPECT_DISTRICTS)))
    for d, entry in roster.items():
        if len(entry["members"]) != SEATS_PER_DISTRICT:
            fail("district %s has %d members, the county seats exactly %d per district "
                 "(the same seat count the derived boundary's population check assumes)"
                 % (d, len(entry["members"]), SEATS_PER_DISTRICT))
        entry["members"].sort(key=lambda m: m["name"].split()[-1])

    roles = sorted(m["role"] for e in roster.values() for m in e["members"] if m.get("role"))
    if roles != ["Chairman", "Vice-Chairman"]:
        fail("the table marks %s — expected exactly one Chairman and one Vice-Chairman"
             % (roles or "no officers"))

    body = json.dumps(roster, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if args.check:
        if not os.path.exists(OUT_PATH):
            fail("%s does not exist" % OUT_PATH)
        with open(OUT_PATH, encoding="utf-8") as f:
            if f.read() != body:
                fail("%s differs from the transcribed table in this file" % OUT_PATH)
        print("mason-board-roster: %s" % drift)
        print("mason-board-roster: OK — %s matches the table transcribed %s"
              % (OUT_PATH, TRANSCRIBED))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(body)
    print("mason-board-roster: wrote %s — %d districts, %d members "
          "(8 phones, 8 e-mails, party on every row), transcribed %s"
          % (OUT_PATH, len(roster), len(MEMBERS), TRANSCRIBED))


if __name__ == "__main__":
    main()
