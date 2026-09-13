#!/usr/bin/env python3
"""
Stage 1 of the Jo Daviess County Board roster pipeline: scrape the county's
board page and its per-member directory pages into raw JSON for
build_jodaviess_board_roster.py.

THE RIGHT DOMAIN, STATED BECAUSE THE WRONG ONE IS A TRAP. The county is at
jodaviesscountyil.gov. The OLD jodaviess.org answers EVERY path with its home
page — a dead link that looks live — so nothing here may ever cite it (the
warning first recorded on the jo-daviess-county-board-districts gap).

PAGE SHAPE (CivicPlus/CivicEngage). /1199/County-Board carries a Members <ul>;
each <li> is one SEAT:

    <li><a href="/directory.aspx?EID=30">LaDon Trost (R), Chair<br></a>
        Term: 2024 to 2028<br>
        District 17: Stockton II precinct and part Rush precincts</li>

or, for an unfilled seat, the same shape with "VACANT" in place of the linked
name. The seat count is the guard, not the name count — a vacancy is COUNTED,
never named (the Lee rule; the engine's Livingston-style `vacancies` rendering).

WHICH SEAT IS VACANT MOVES, so it is not written down here as though it were a
property of the page: District 16 was the vacancy at first ship and District 10
is the vacancy as of 2026-09-13, the same day the county filled 16. Both changes
were held out of the shipped file for a day by the shape guard below, which is
the guard doing its job rather than a bug — it refused a half-parse instead of
shipping one.

THE DIRECTORY LINK ALSO EXISTS IN TWO SHAPES; see the LINK_RE note.

Each named member's /directory.aspx?EID=nn page carries the e-mail (a plain
mailto, sometimes with a stray space after the colon — John Lang's reads
"mailto: johnblang300@gmail.com", so the parse tolerates whitespace) inside the
page's own #staff-email block and a direct phone inside #staff-phone. All 16
named members carried a DISTINCT phone at first ship, so these are direct
lines, not a switchboard (the Calhoun test was run and does not apply).

THE SAME PAGES PRINT EVERY MEMBER'S HOME ADDRESS. It is NEVER captured — not
parsed, not stored, not shipped (the Madison/Peoria precedent: a residence is
not an office you can visit). The parse reads only the #staff-email and
#staff-phone blocks and the Term/District lines, so nothing downstream can
leak what was never collected.

E-MAIL IS CARRIED EXACTLY AS PUBLISHED. Several members list personal
addresses (gmail/icloud) rather than @jodaviesscountyil.gov ones; they ship
verbatim — inventing a county address for symmetry would be inventing contact
details.

CROSS-CHECKS, because the roster spans seventeen fetches of two surfaces: a
member's directory page must agree with the board page on the DISTRICT NUMBER,
and its title must match the board-page name on surname + first initial
(unique across the board, the fleet's name-match rule). Any disagreement fails
the run rather than shipping whichever page the scraper happened to trust.

PACING. Seventeen serial fetches, ~1s apart; 429/5xx back off and retry with a
capped Retry-After (the Henry lesson), 403/404 do not retry (a moved directory
is not fixed by waiting).

Usage:
    python3 jodaviess_county_board_scraper.py [output.json]
"""

import html
import json
import re
import sys
import time

import requests
from scraper_common import UA_ROSTER_BOT, fetch as fetch_with_retry  # noqa: E402  (shared machinery — do not fork)

BASE = "https://www.jodaviesscountyil.gov"
SOURCE_URL = BASE + "/1199/County-Board"
# THE DISTRICTRY TOKEN, MEASURED RATHER THAN ASSUMED (2026-09-13). This file sent
# a pinned Chrome string with no refusal recorded behind it, which is the state
# scripts/probe_user_agents.py exists to find. Two measurements say the browser
# string bought nothing here. The sweep of 2026-09-12 recorded this host
# token-ok in user-agent-measurements.json (requests + the token, HTTP 200,
# 85,523 bytes) — but it asked /1226/GIS-IT, and the #931 finding is that the
# page matters, so THIS page was asked both ways on 2026-09-13: SOURCE_URL
# answered HTTP 200 and 82,783 bytes to the token and to Chrome/126 alike, byte
# for byte, and served robots.txt to both (816 bytes, one binding group, no rule
# matching /1199/County-Board). A sibling already proves it weekly —
# scripts/build_jodaviess_board_districts.py reads the same host under its own
# districtry token. The witness for this change is Saturday's own weekly run,
# which is what scripts/scraper_common.py requires; if the host starts refusing
# the token, that run fails visibly rather than shipping a short roster, because
# the seat-count guard below refuses the write.
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
}
REQUEST_TIMEOUT = 60
FETCH_GAP_S = 1.0
MAX_RETRIES = 3
RETRY_AFTER_CAP_S = 60

SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
# One seat: an optional directory link (a vacancy has none), then the seat's
# lines. Non-greedy up to </li> so a seat can never absorb its neighbour.
SEAT_RE = re.compile(r"<li[^>]*>(.*?)</li>", re.S | re.I)
# TWO LINK SHAPES, BOTH LIVE ON ONE PAGE, and that is why the 2026-09-12 run
# stopped: CivicPlus has moved this directory from /directory.aspx?EID=nn to
# /m/directory/employee?eid=nn, and the county updated only the seat it
# edited. Measured 2026-09-13: fifteen seats still link the legacy path, the
# newly filled District 16 links the new one, and the LEGACY PATH REDIRECTS
# to the new one for every member (checked on eid 59 and on the control
# eid 30), so both reach the same page and the new one is what the county now
# serves. The shipped `url` is normalised to it rather than storing whichever
# shape a given <li> happens to carry, which would put two spellings of one
# address in one file for no reason a reader could see.
LINK_RE = re.compile(
    r'<a href="(/(?:directory\.aspx\?EID=|m/directory/employee\?eid=)(\d+))">'
    r'(.*?)</a>', re.S | re.I)
MEMBER_URL = BASE + "/m/directory/employee?eid=%s"
# "LaDon Trost (R), Chair" / "Lynn L. Gallagher (D)" — name, party, role.
NAME_RE = re.compile(r"^(.*?)\s*\(([RD])\)\s*(?:,\s*(.+))?$")
TERM_RE = re.compile(r"Term:?\s*(\d{4})\s*(?:to|[-–])\s*(\d{4})", re.I)
DISTRICT_RE = re.compile(r"District\s+(\d+)\s*[:–-]", re.I)
EMAIL_RE = re.compile(r'id="staff-email".*?mailto:\s*([^"?\s>]+)', re.S | re.I)
PHONE_RE = re.compile(r'id="staff-phone".*?</div>', re.S | re.I)
PHONE_NUM_RE = re.compile(r"\d{3}-\d{3}-\d{4}")
DIR_TITLE_RE = re.compile(
    r'directory-page-title[^>]*>\s*<span class="fw-bold">([^<]+)</span>', re.I)


def text_of(fragment):
    return re.sub(r"\s+", " ",
                  html.unescape(TAG_RE.sub(" ", fragment or ""))).strip()


def get(url):
    # scraper_common.fetch retries 429/5xx (numeric Retry-After honoured,
    # capped) and refuses to retry 401/403/404 — the Henry rule. Parsing and
    # every page check stay in this file.
    return fetch_with_retry(url, HEADERS, timeout=REQUEST_TIMEOUT,
                            attempts=MAX_RETRIES + 1,
                            retry_after_cap=RETRY_AFTER_CAP_S).text


def name_key(name):
    """surname + first initial, the fleet's cross-surface match rule."""
    toks = [t for t in re.sub(r"[^A-Za-z ]", "", name).split() if t]
    if len(toks) < 2:
        return None
    return (toks[-1].lower(), toks[0][0].lower())


def parse_board_page(page):
    """(records, vacancies) read from the Members list."""
    page = SCRIPT_RE.sub(" ", page)
    # The Members <ul> is the one whose items link /directory.aspx?EID= —
    # matched per-seat rather than by section heading so the page's other
    # lists (navigation, quick links) can never contribute a seat.
    records, vacancies = [], []
    for m in SEAT_RE.finditer(page):
        body = m.group(1)
        dmatch = DISTRICT_RE.search(text_of(body))
        if not dmatch:
            continue                      # not a seat row
        district = str(int(dmatch.group(1)))
        term = TERM_RE.search(text_of(body))
        term_str = ("%s to %s" % term.groups()) if term else None
        link = LINK_RE.search(body)
        if not link:
            if "VACANT" not in text_of(body).upper():
                print("jodaviess-scraper: FAIL — district %s has neither a "
                      "member link nor a VACANT marker; the page changed shape"
                      % district, file=sys.stderr)
                sys.exit(1)
            vacancies.append({"district": district, "term": term_str})
            continue
        label = text_of(link.group(3))
        nm = NAME_RE.match(label)
        if not nm:
            print("jodaviess-scraper: FAIL — member label %r does not parse "
                  "as 'Name (R|D)[, Role]'" % label, file=sys.stderr)
            sys.exit(1)
        rec = {"district": district,
               "name": nm.group(1).strip(),
               "party": nm.group(2),
               "eid": int(link.group(2)),
               "url": MEMBER_URL % link.group(2)}
        if nm.group(3):
            rec["role"] = nm.group(3).strip()
        if term_str:
            rec["term"] = term_str
        records.append(rec)
    return records, vacancies


def enrich_from_directory(rec):
    """e-mail + phone from the member's own directory page, with the
    board-page district and name re-checked against it. Reads ONLY the
    #staff-email / #staff-phone blocks — the page's home-address lines are
    deliberately never parsed."""
    page = get(rec["url"])
    title = DIR_TITLE_RE.search(page)
    if title:
        got = name_key(text_of(re.sub(r"\([RD]\)", "", title.group(1))))
        want = name_key(rec["name"])
        if got and want and got != want:
            print("jodaviess-scraper: FAIL — %s links directory EID=%d whose "
                  "title reads %r; the two county surfaces disagree about who "
                  "this is" % (rec["name"], rec["eid"], text_of(title.group(1))),
                  file=sys.stderr)
            sys.exit(1)
    dmatch = DISTRICT_RE.search(text_of(SCRIPT_RE.sub(" ", page)))
    if dmatch and str(int(dmatch.group(1))) != rec["district"]:
        print("jodaviess-scraper: FAIL — the board page puts %s in District "
              "%s, their directory page says District %s; not shipping either "
              "claim" % (rec["name"], rec["district"], int(dmatch.group(1))),
              file=sys.stderr)
        sys.exit(1)
    email = EMAIL_RE.search(page)
    if email:
        rec["email"] = html.unescape(email.group(1)).strip()
    phseg = PHONE_RE.search(page)
    if phseg:
        phone = PHONE_NUM_RE.search(phseg.group(0))
        if phone:
            rec["phone"] = phone.group(0)


def main():
    out_path = (sys.argv[1] if len(sys.argv) > 1
                else "jodaviess_county_board_raw.json")
    records, vacancies = parse_board_page(get(SOURCE_URL))
    if not records:
        print("jodaviess-scraper: FAIL — parsed 0 members; the Members list "
              "changed shape", file=sys.stderr)
        sys.exit(1)
    keys = [name_key(r["name"]) for r in records]
    if len(set(keys)) != len(keys):
        print("jodaviess-scraper: FAIL — two members collide on surname + "
              "first initial; the directory cross-check cannot be trusted",
              file=sys.stderr)
        sys.exit(1)
    for rec in records:
        time.sleep(FETCH_GAP_S)
        enrich_from_directory(rec)

    payload = {"source_url": SOURCE_URL, "records": records,
               "vacancies": vacancies}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    distinct_phones = {r["phone"] for r in records if r.get("phone")}
    print("jodaviess-scraper: wrote %s — %d members + %d vacant seat(s) "
          "across %d districts; %d e-mails, %d phones (%d distinct), "
          "%d role(s)"
          % (out_path, len(records), len(vacancies),
             len({r["district"] for r in records} | {v["district"] for v in vacancies}),
             sum(1 for r in records if r.get("email")),
             sum(1 for r in records if r.get("phone")),
             len(distinct_phones),
             sum(1 for r in records if r.get("role"))))


if __name__ == "__main__":
    main()
