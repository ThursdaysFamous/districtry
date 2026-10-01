#!/usr/bin/env python3
"""
Scrape De Witt County's board roster into raw board-roster records.

Stage 1 of the two-stage pipeline (scripts/build_dewitt_board_roster.py is
stage 2). The county publishes each of its twelve members as a block carrying,
in order: the member's name in caps, an optional role line (Chairman / Vice
Chairman), the LETTERED district (A-D), that district's precinct composition,
a term-length string, an optional phone, an e-mail, and a committee list.

The same page is the authority for the DISTRICT BOUNDARIES — its composition
lines are what scripts/build_dewitt_board_districts.py dissolves — so this
scraper also emits the composition it read, and the builder cross-checks it
against the composition compiled into that script. If the county rewrites its
districts, the mismatch surfaces in the weekly run instead of silently leaving
the shipped boundary a decade behind.

What is deliberately NOT read: the term-length string ("2 yr, 4 yr, 4 yr")
describes the staggered cycle of the district's three seats collectively, not
which one this member holds, so attaching it to a person would misstate it.
Committee lists are read — they are per-member and unambiguous.

FETCH POSTURE: open. Plain server-rendered HTML.

Usage:
    python3 dewitt_county_board_scraper.py [output.json]   # default: stdout
"""

import html as html_mod
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_ROSTER_BOT,
    require_robots_once,
)

SOURCE_URL = "https://www.dewittcountyil.gov/government/county_board.php"
UA = {"User-Agent": UA_ROSTER_BOT}

NAME_RE = re.compile(r"^[A-Z][A-Z.'\-]*(?:\s+[A-Z][A-Z.'\-]*){1,3}$")
DISTRICT_RE = re.compile(r"^District\s+([A-D])$", re.I)
ROLE_RE = re.compile(r"^(Chairman|Vice\s*Chairman)$", re.I)
PHONE_RE = re.compile(r"\(?(\d{3})\)?\D{0,2}(\d{3})\D?(\d{4})")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
TERM_RE = re.compile(r"^\d+\s*yr(\s*,\s*\d+\s*yr)*$", re.I)


def text_lines(page):
    body = re.sub(r"(?is)<(script|style|nav|footer|head)[^>]*>.*?</\1>", " ", page)
    text = html_mod.unescape(re.sub(r"(?s)<[^>]+>", "\n", body))
    return [l.strip() for l in text.splitlines() if l.strip()]


def tidy_name(caps):
    """The page prints names in caps; title-case them, but leave particles
    like McX alone by only lowering a run that is entirely uppercase."""
    parts = []
    for word in caps.split():
        parts.append(word.capitalize() if word.isupper() else word)
    return " ".join(parts)


def normalize_phone(raw):
    m = PHONE_RE.search(raw or "")
    return "-".join(m.groups()) if m else None


def main():
    require_robots_once(SOURCE_URL, UA["User-Agent"], headers=UA,
                        label="il-dewitt-county-board-scraper")
    resp = requests.get(SOURCE_URL, headers=UA, timeout=60)
    resp.raise_for_status()
    lines = text_lines(resp.text)

    records = []
    current = None
    for line in lines:
        if NAME_RE.match(line) and not DISTRICT_RE.match(line) and not ROLE_RE.match(line):
            # a new member block begins
            if current and current.get("district"):
                records.append(current)
            current = {"name": tidy_name(line), "role": None, "district": None,
                       "composition": [], "phone": None, "email": None, "committees": []}
            continue
        if current is None:
            continue
        m = ROLE_RE.match(line)
        if m:
            current["role"] = "Vice-Chairman" if line.lower().startswith("vice") else "Chairman"
            continue
        m = DISTRICT_RE.match(line)
        if m:
            current["district"] = m.group(1).upper()
            continue
        if TERM_RE.match(line):
            continue                      # staggered-cycle string, see header
        if EMAIL_RE.match(line):
            current["email"] = line.lower()
            continue
        if line.startswith("-"):
            current["committees"].append(line.lstrip("- ").strip())
            continue
        if current["district"] and not current["email"]:
            # composition lines follow the district and may wrap across lines
            if re.fullmatch(r"[A-Za-z0-9 ,&.]+", line) and not PHONE_RE.fullmatch(line):
                current["composition"].append(line)
                continue
        p = normalize_phone(line)
        if p and not current["phone"]:
            current["phone"] = p
    if current and current.get("district"):
        records.append(current)

    for rec in records:
        rec["composition"] = " ".join(rec["composition"]).strip() or None

    if not records:
        print("dewitt-board-scraper: FAIL — zero member blocks parsed (markup change?)",
              file=sys.stderr)
        sys.exit(1)

    out = json.dumps({"source": SOURCE_URL, "records": records}, indent=2, ensure_ascii=False)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(out)
        print("dewitt-board-scraper: %d records -> %s" % (len(records), sys.argv[1]))
    else:
        print(out)


if __name__ == "__main__":
    main()
