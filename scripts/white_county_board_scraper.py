#!/usr/bin/env python3
"""
Stage 1 of the White County Board pipeline: scrape the county's board page AND
its Elections page into raw JSON for build_white_county_board.py.

TWO PAGES, ONE SITE (whitecounty-il.gov, a Duda/irp-hosted site that serves
static HTML — no challenge, no JS rendering needed):

  * /county-board — "WHITE COUNTY BOARD MEMBERS", five lines of the shape
    "CASSIE (HUGHES) PIGG (R) (CHAIR)". The trailing parentheticals are read
    as party — (R)/(D) — and role — (CHAIR)/(VICE); any OTHER parenthetical is
    part of the name as the county prints it ("(HUGHES)" is one). The page
    names NO districts; the district join lives in the builder, proven from
    the county's own certified canvasses. The page also publishes the board's
    single mailing address and its single e-mail (the Clerk's), which ship at
    BOARD level — one address printed for five members is the board's, not
    five members' (the Calhoun switchboard rule).
  * the Elections page — "POLLING PLACES IN WHITE COUNTY", eleven bullet
    lines covering all 18 precincts (grouped: "Carmi #12, 13, 14, 16, 18, 19
    & 20" is one line, one building). Each line ships verbatim after its
    precinct spec — place and address are one string, because splitting
    "Fire House 912 Loy St." into place/address would be a guess.
    THE SAME PAGE LINKS THE ADOPTED MAP this county's boundaries were built
    from, so the scrape also records whether that exact link is still there —
    the weekly drift check build_white_county_board.py enforces (the Mason
    watcher rule: a WordPress-style CDN replacement lands at a NEW path while
    the old URL keeps serving the old file forever).

Usage:
    python3 white_county_board_scraper.py [output.json]
"""

import html
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_CHROME_WIN_126,
    require_robots_once,
)

BOARD_URL = "https://www.whitecounty-il.gov/county-board"
ELECTIONS_URL = "https://www.whitecounty-il.gov/elections925f89e8"
# The adopted map's link, exactly as the Elections page carries it (URL-encoded).
MAP_HREF_RE = re.compile(
    r"href=\"([^\"]*White%20County%2C%20IL%20voting%20districts"
    r"%20%26%20precincts%20map\.pdf)\"", re.I)

HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
}
REQUEST_TIMEOUT = 60

SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
PARTY_RE = re.compile(r"\(\s*([RD])\s*\)", re.I)
ROLE_RE = re.compile(r"\(\s*(CHAIR|VICE)\s*\)", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# A member line: mostly-uppercase words, at least two of them, with a party.
POLL_HEAD_RE = re.compile(r"POLLING PLACES IN WHITE COUNTY", re.I)


def page_lines(page):
    page = SCRIPT_RE.sub(" ", page)
    text = html.unescape(TAG_RE.sub("\n", page)).replace("\xa0", " ")
    return [re.sub(r"\s+", " ", line).strip()
            for line in text.splitlines() if line.strip()]


def parse_board(page):
    lines = page_lines(page)
    try:
        start = next(i for i, l in enumerate(lines)
                     if "WHITE COUNTY BOARD MEMBERS" in l.upper())
    except StopIteration:
        return [], None, None
    members, board_email, board_address = [], None, None
    i = start + 1
    while i < len(lines) and len(members) < 12:
        line = lines[i]
        i += 1
        if "MAILINGS FOR" in line.upper():
            break
        party = PARTY_RE.search(line)
        if not party:
            # a role printed alone on the next line ("(CHAIR)") belongs to the
            # previous member
            role = ROLE_RE.search(line)
            if role and members and "role" not in members[-1]:
                members[-1]["role"] = role.group(1).upper()
            continue
        rec = {"party": party.group(1).upper()}
        role = ROLE_RE.search(line)
        if role:
            rec["role"] = role.group(1).upper()
        name = ROLE_RE.sub("", PARTY_RE.sub("", line))
        name = re.sub(r"\s+", " ", name).strip(" -–")
        if not name:
            continue
        rec["name"] = name
        members.append(rec)
    # the board's own mailing address + e-mail, printed after the roster
    tail = " ".join(lines[i - 1:i + 6])
    addr = re.search(r"White County Board,\s*PO Box[^,]*,\s*[^,]+,\s*IL\s*\d{5}",
                     tail, re.I)
    if addr:
        board_address = re.sub(r"\s+", " ", addr.group(0)).strip()
    email = EMAIL_RE.search(tail)
    if email:
        board_email = email.group(0)
    return members, board_email, board_address


def parse_polling(page):
    lines = page_lines(page)
    try:
        start = next(i for i, l in enumerate(lines) if POLL_HEAD_RE.search(l))
    except StopIteration:
        return []
    entries = []
    for line in lines[start + 1:start + 40]:
        if line.upper().startswith("SHARE BY"):
            break
        cleaned = line.lstrip("•").strip()
        # "<Township words> #<numbers...> <location...>" — the number run is
        # greedy across ", " and "&" so "Carmi #12, 13, 14, 16, 18, 19 & 20"
        # yields seven numbers, not one.
        m = re.match(r"([A-Za-z .]+?)\s*#\s*(\d+(?:\s*[,&]\s*\d+)*)\s*[-–]?\s*(\S.*)$",
                     cleaned)
        if not m:
            continue
        township = re.sub(r"\s+", " ", m.group(1)).strip()
        numbers = [int(n) for n in re.findall(r"\d+", m.group(2))]
        location = m.group(3).strip(" -–").strip()
        if not township or not numbers or not location:
            continue
        entries.append({"township": township, "numbers": numbers,
                        "location": location})
    return entries


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "white_county_board_raw.json"
    require_robots_once(BOARD_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-white-county-board-scraper")
    board_resp = requests.get(BOARD_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    board_resp.raise_for_status()
    members, board_email, board_address = parse_board(board_resp.text)
    if not members:
        print("white-scraper: FAIL — parsed 0 member lines from %s; the page "
              "reshaped" % BOARD_URL, file=sys.stderr)
        sys.exit(1)

    require_robots_once(ELECTIONS_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-white-county-board-scraper")
    elections_resp = requests.get(ELECTIONS_URL, headers=HEADERS,
                                  timeout=REQUEST_TIMEOUT)
    elections_resp.raise_for_status()
    polling = parse_polling(elections_resp.text)
    if not polling:
        print("white-scraper: FAIL — parsed 0 polling lines from %s; the page "
              "reshaped" % ELECTIONS_URL, file=sys.stderr)
        sys.exit(1)
    map_link = MAP_HREF_RE.search(elections_resp.text)

    payload = {
        "board_url": BOARD_URL,
        "elections_url": ELECTIONS_URL,
        "members": members,
        "board_email": board_email,
        "board_address": board_address,
        "polling": polling,
        "map_link": map_link.group(1) if map_link else None,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("white-scraper: wrote %s — %d members (%d with a role), board e-mail "
          "%s, %d polling lines covering %d precinct numbers, map link %s"
          % (out_path, len(members),
             sum(1 for m in members if m.get("role")),
             "found" if board_email else "MISSING",
             len(polling), sum(len(e["numbers"]) for e in polling),
             "still on the page" if map_link else "MISSING"))


if __name__ == "__main__":
    main()
