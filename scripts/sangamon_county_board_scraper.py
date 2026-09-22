#!/usr/bin/env python3
"""
Stage 1 of the Sangamon County Board roster pipeline: walk the county's 29
per-district member pages into raw JSON for
build_sangamon_county_board_roster.py.

WHY 29 PAGE FETCHES AND NOT ONE: the county's board GIS
(CountyBoardDistricts2020_WithURLs) carries no member name — what it carries is
a `DistrictMemberURL` per district, pointing at exactly these pages. So the join
key is published and exact; the names simply live one hop away. This walks the
same URLs the GIS names, in district order, rather than guessing a URL pattern.

NEITHER THE TAGS NOR THE LABELS ARE RELIABLE, and both cost a rewrite to
discover. The member block is an <h3> on most pages, a plain <p> on district 21,
and a <p><span style="font-size:130%"> on district 12 — so keying on <h3> silently
lost two members. On district 4 the <h3> also wraps the address, so keying on the
element's whole text produced the name "Lanae Clarke (R) 1523 Horse Creek Trl
Pawnee, IL 62558". Labels vary the same way: some pages write "Email:" and "C:",
others print a bare address and phone, and one has no e-mail at all.

What IS stable across all 29 is the ORDER: a "Term:" paragraph, then a block
whose FIRST LINE is "Name (Party)" and whose remaining lines are the address and
contact. So the parse anchors on Term, takes the first line after it as the name,
and matches contact fields by SHAPE (an e-mail is an e-mail, a phone is a phone)
rather than by position or label. A missing field is left null instead of being
filled from whatever line happened to sit there.

The street addresses are RESIDENCES and are deliberately not collected, the same
call the McHenry and Livingston rosters made. The published phone is collected:
the county prints it as the way to reach that member.

WHY A THIRTIETH FETCH — THE INDEX PAGE: on 2026-08-18 district 2's page came back
with its name, address, phone and e-mail all deleted and only "(R)" and the term
left behind, and the weekly refresh dropped the district silently. It was RIGHT
to drop the name (the seat is empty) and wrong to drop the district: an absent
key renders a card headed "District 2" with nothing under it, which reads as a
broken layer rather than an empty seat. The trouble is that on the per-district
page alone, "the county emptied this seat" and "our parse broke" are the SAME
BYTES. The members index is what tells them apart — it prints "District 2 -
vacant" in the county's own word — so it is fetched once per run for exactly
that. A vacancy is recorded only when BOTH sources agree (the index says vacant
AND the district page yields no name); a disagreement leaves the district out
the old way rather than inventing an empty seat. The party marker stranded on
the emptied page belongs to the FORMER holder and is not carried: the seat has
no party, the person who left it did.

AND THE COUNTY WRITES A VACANCY TWO WAYS. District 2 above is the blank kind —
the name deleted, the party marker left behind. District 16 emptied between the
2026-09-01 refresh, which still named a member, and the 2026-09-22 one, and its
page reads "vacant (R)": the county's own word printed where the name was. That
line carries a party marker, so the name branch took it and returned the literal
string "vacant", which is truthy, so the seat shipped as a MEMBER of that name —
a schema.org Person called vacant, affiliated Republican, on the county's own
page (#1093, held before it merged). Both shapes now land on the same path, and
both are pinned in PARSE_SELFTEST below rather than left to a live run: the
blank shape had been exercised weekly since 2026-08-18 and said nothing about
this one, because a live run only ever tests the shapes the county is publishing
that week.

Usage:
    python3 sangamon_county_board_scraper.py [output.json]
"""

import html
import json
import re
import sys
import time

import requests
from scraper_common import UA_CHROME_X11_120  # noqa: E402  (shared machinery — do not fork)

BASE = "https://sangamonil.gov/departments/a-c/county-board/districts/members/district-%d"
SOURCE_URL = "https://sangamonil.gov/departments/a-c/county-board/districts"
MEMBERS_URL = SOURCE_URL + "/members"
DISTRICTS = range(1, 30)  # 29 single-member districts

HEADERS = {
    "User-Agent": UA_CHROME_X11_120,
}
REQUEST_TIMEOUT = 45
PAUSE_SECONDS = 0.6  # 29 sequential fetches; be a polite guest on a county server

SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
# Line-level structure matters here, so block-enders become newlines before tags
# are stripped — that is what keeps "Name (Party)" separate from the address that
# shares its element on district 4.
BREAK_RE = re.compile(r"<br[^>]*>|</p>|</h[1-6]>|</div>|</li>", re.I)
TERM_RE = re.compile(r"Term:\s*([0-9]{4}\s*-\s*[0-9]{4})")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\b(\d{3})[.\-\s]?(\d{3})[.\-\s]?(\d{4})\b")
PARTY_RE = re.compile(r"\(([RDI])\)\s*$")
# Curly quotes and the nickname convention ("Harry “Tom” Fraase, Jr.") are kept
# as published — a name is rendered as its owner's government publishes it.
QUOTES = {"“": '"', "”": '"', "‘": "'", "’": "'"}
# The index prints one row per district as `<a href=".../district-N">District
# N</a> - Name`, so the row is anchored on the same member URL the GIS publishes
# — the join key stays the county's on both sides here too.
INDEX_ROW_RE = re.compile(
    r'href="[^"]*/members/district-(\d+)"[^>]*>\s*District\s*\d+\s*</a>\s*[-\u2010-\u2015]\s*([^<]*)',
    re.I)
VACANT_RE = re.compile(r"^vacan\w*$", re.I)


def text_of(fragment):
    s = html.unescape(TAG_RE.sub(" ", fragment))
    for bad, good in QUOTES.items():
        s = s.replace(bad, good)
    return re.sub(r"\s+", " ", s).strip()


def lines_after_term(body):
    """Content lines following the 'Term:' paragraph, in document order."""
    marker = body.find("Term:")
    if marker < 0:
        return []
    tail = BREAK_RE.sub("\n", body[marker:])
    out = []
    for raw in TAG_RE.sub(" ", tail).split("\n"):
        line = text_of(raw)
        if line and not line.startswith("Term:"):
            out.append(line)
    return out


def vacancies_from_index(page):
    """Districts the county's own members index prints as vacant.

    Returns a set of district strings, or None when the index cannot be read at
    all — the caller treats None as "no corroboration" and falls back to the old
    silent skip rather than guessing.
    """
    rows = INDEX_ROW_RE.findall(SCRIPT_RE.sub("", page))
    if not rows:
        return None
    return set(d for d, name in rows if VACANT_RE.match(text_of(name)))


def parse(page, district):
    body = SCRIPT_RE.sub("", page)
    rec = {"district": str(district)}

    for line in lines_after_term(body):
        party = PARTY_RE.search(line)
        if not party:
            # The name line is the one carrying the party marker. Nothing else on
            # these pages does, so this never has to guess which line is a name.
            continue
        rec["party"] = party.group(1)
        name = PARTY_RE.sub("", line).strip(" ,")
        if VACANT_RE.match(name):
            # THE COUNTY WRITES A VACANCY TWO WAYS ON THE SAME KIND OF PAGE, and
            # only one of them used to survive. District 2 prints a bare "(R)",
            # so this loop finds a party and an EMPTY name and main() asks the
            # index. District 16 prints "vacant (R)" -- a party marker on the
            # line, so the name branch takes it and returns the literal string
            # "vacant", which main() reads as a member because it is truthy.
            # That shipped a schema.org Person named "vacant" on the county page
            # (#1093, held). A word the county uses to say NOBODY HOLDS THIS SEAT
            # is not a name, so it is dropped here and the district takes
            # District 2's path. The party is left set exactly as District 2
            # leaves it: main() discards it when it builds the vacancy record,
            # because the marker is the DEPARTED member's rather than the seat's.
            break
        rec["name"] = name
        break

    flat = text_of(BREAK_RE.sub(" ", body))
    term = TERM_RE.search(flat)
    if term:
        rec["term"] = re.sub(r"\s*-\s*", "-", term.group(1))
    email = EMAIL_RE.search(flat)
    if email:
        rec["email"] = email.group(0)
    phone = PHONE_RE.search(flat)
    if phone:
        rec["phone"] = "-".join(phone.groups())
    rec["url"] = BASE % district
    return rec


# The shapes this parse must keep getting right, checked on every run before a
# single page is fetched. Each is a MINIMISED copy of what sangamonil.gov
# actually served on 2026-09-22, cut to the Term paragraph and the member block
# that follows it — with every street replaced, because those are residences and
# the rule against writing one into this repo does not stop at a test fixture.
#
# The two vacancy rows are the pair the county publishes AT THE SAME TIME, and
# they are why this table exists: for three weeks only one of them was tested,
# by a live run, and the other shipped the word "vacant" as a person's name.
RESIDENCE = "[residence omitted]"

PARSE_SELFTEST = (
    # District 2: the seat emptied, leaving the departed member's party marker
    # on an otherwise blank heading.
    ("<p>Term: 2022&nbsp;- 2026</p>\n<h3>&nbsp;(R)</h3>\n<p><br />\n&nbsp;</p>", None),
    # District 16: the same emptying written the other way, with the county's
    # own word for it left on the line (#1093).
    ("<p>Term: 2024-2028</p>\n<h3>vacant (R)</h3>\n<p></p>", None),
    # Case and inflection are the county's to choose, not ours to depend on.
    ("<p>Term: 2024-2028</p>\n<h3>Vacant (D)</h3>", None),
    ("<p>Term: 2024-2028</p>\n<h3>VACANCY (R)</h3>", None),
    # District 4: the address shares the heading with the name, so the line
    # split is the only thing keeping the residence out of the name.
    ("<p>Term: 2022-2026 (appointed 7/14/26)</p>\n<h3>Lanae Clarke (R)<br />\n"
     + RESIDENCE + "<br />\nPawnee, IL 62558</h3>\n<p>217-898-2244</p>",
     "Lanae Clarke"),
    # District 21: a plain <p> rather than a heading.
    ("<p>Term: 2025-2026*appointed 2/11/25</p>\n<p>Reggie Guyton (D)<br />\n"
     + RESIDENCE + "<br />\nSpringfield, IL 62703</p>", "Reggie Guyton"),
    # District 12: the member block wrapped in a styled <span>.
    ('<p>Term: 2024-2026 (appointed 6/9/26)</p>\n<p><span style="font-size:130%;">'
     "Sheila Feipel (D)<br />\n" + RESIDENCE + "<br />\nSpringfield, IL 62704"
     "</span></p>", "Sheila Feipel"),
    # A surname is two tokens and the vacancy word is one, so a name that merely
    # STARTS like it is still a name. Without this the guard would be free to
    # widen into a prefix test and take a real person off the board.
    ("<p>Term: 2022-2026</p>\n<h3>Vance Parker (R)</h3>", "Vance Parker"),
)


def _run_parse_selftest():
    for fragment, expected in PARSE_SELFTEST:
        got = parse(fragment, 0).get("name")
        if (got or None) != expected:
            sys.exit("sangamon-scraper: SELFTEST FAIL — %r parsed name %r, expected %r"
                     % (fragment, got, expected))


def main():
    _run_parse_selftest()
    out_path = sys.argv[1] if len(sys.argv) > 1 else "sangamon_county_board_raw.json"
    session = requests.Session()

    # One extra fetch, read only to tell an empty seat from a broken parse.
    vacant = None
    try:
        resp = session.get(MEMBERS_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        vacant = vacancies_from_index(resp.text)
    except requests.RequestException as exc:
        print("sangamon-scraper: members index failed (%s) — vacancies will not be "
              "distinguishable from parse failures this run" % exc, file=sys.stderr)
    if vacant is None:
        print("sangamon-scraper: members index gave no district rows — falling back "
              "to skipping unparsed districts", file=sys.stderr)
    else:
        print("sangamon-scraper: index lists %d vacant district(s): %s"
              % (len(vacant), ", ".join(sorted(vacant, key=int)) or "none"),
              file=sys.stderr)

    records = []
    for district in DISTRICTS:
        url = BASE % district
        try:
            resp = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print("sangamon-scraper: district %d failed (%s) — skipped" % (district, exc),
                  file=sys.stderr)
            time.sleep(PAUSE_SECONDS)
            continue
        rec = parse(resp.text, district)
        if rec.get("name"):
            records.append(rec)
        elif vacant and str(district) in vacant:
            # Both sources agree the seat is empty. Carry the district with no
            # person and no party — the marker left on the emptied page is the
            # departed member's, not the seat's.
            records.append({"district": str(district), "vacant": True,
                            "url": BASE % district})
            print("sangamon-scraper: district %d is vacant per the county's index"
                  % district, file=sys.stderr)
        else:
            print("sangamon-scraper: district %d had no member heading" % district,
                  file=sys.stderr)
        time.sleep(PAUSE_SECONDS)

    named = [r for r in records if r.get("name")]
    if not named:
        print("sangamon-scraper: FAIL — parsed 0 members; the page shape changed",
              file=sys.stderr)
        sys.exit(1)
    payload = {"source_url": SOURCE_URL, "records": records}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("sangamon-scraper: wrote %s — %d/%d districts (%d named, %d vacant), "
          "%d e-mails, %d phones, %d parties"
          % (out_path, len(records), len(list(DISTRICTS)),
             len(named), sum(1 for r in records if r.get("vacant")),
             sum(1 for r in records if r.get("email")),
             sum(1 for r in records if r.get("phone")),
             sum(1 for r in records if r.get("party"))))


if __name__ == "__main__":
    main()
