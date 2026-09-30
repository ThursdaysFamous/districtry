#!/usr/bin/env python3
"""
Scrape Cass County's board roster into raw board-roster records.

Stage 1 of the two-stage pipeline (scripts/build_cass_board_roster.py is stage
2). The county lists its board under four "District No. N" headings, each
member as a name line followed by a phone and (usually) an e-mail. The
Chairman is named once above the districts and also holds a district seat, so
his role is attached to that seat rather than becoming a separate entry.

TWO SOURCE QUIRKS THIS HANDLES, both from the page's hand-entered markup:

  * PHONE NUMBERS WRAP MID-STRING. One member's number renders as "2" then
    "17-323-4586" on separate lines, another as "309-825" / "-6420". Digits are
    therefore gathered across the lines that follow a name until ten of them
    exist, rather than matched line-by-line — a line-anchored regex silently
    drops those two members' phones.
  * ONE MEMBER PUBLISHES NO E-MAIL. That is the county's own omission and ships
    as a phone-only row; nothing is invented to fill it.

The DISTRICT SIZES are emitted as well, and they matter more than they look:
Cass seats eleven members as 3/3/3/2, and that split is the input the shipped
boundary's population test depends on (scripts/build_cass_board_districts.py).
Because Cass publishes its district COMPOSITION only in a linked PDF, the
weekly composition check De Witt and Washington get is impossible here — the
seat-count check in stage 2 is the available tripwire.

FETCH POSTURE: open. Plain server-rendered HTML.

Usage:
    python3 cass_county_board_scraper.py [output.json]   # default: stdout
"""

import html as html_mod
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_CHROME_X11_128,
    require_robots_once,
)

SOURCE_URL = "https://co.cass.il.us/elected-officials/cass-county-board"
UA = {"User-Agent": UA_CHROME_X11_128}

HEADING_RE = re.compile(r"District\s+No\.\s*(\d+)", re.I)
CHAIR_RE = re.compile(r"Chairman of the Cass County Board:\s*(.+)$", re.I)
NAME_RE = re.compile(r"^[A-Z][A-Za-z.'\-]+(?:\s+\([A-Za-z]+\))?(?:\s+[A-Z][A-Za-z.'\-]*){1,3}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
STOP_RE = re.compile(r"helpful links|meeting agendas|county audits", re.I)


def text_lines(page):
    body = re.sub(r"(?is)<(script|style|nav|footer|head)[^>]*>.*?</\1>", " ", page)
    text = html_mod.unescape(re.sub(r"(?s)<[^>]+>", "\n", body))
    return [l.strip() for l in text.splitlines() if l.strip()]


def name_keys(name):
    """Every (given, surname) pair a name could be written as.

    The chairman is announced as "Bill Merriman" while his member row reads
    "William (Bill) Merriman" — the PARENTHETICAL IS THE NAME HE IS ANNOUNCED
    UNDER, so stripping it (the obvious move) is exactly what breaks the match.
    Both forms are emitted and the caller matches on any overlap.
    """
    raw = name or ""
    nicknames = re.findall(r"\(([^)]*)\)", raw)
    bare = re.sub(r"\([^)]*\)", " ", raw)
    parts = [p for p in re.split(r"[^A-Za-z]+", bare.lower()) if len(p) > 1]
    if len(parts) < 2:
        return set()
    surname = parts[-1]
    givens = {parts[0]}
    for nick in nicknames:
        for token in re.split(r"[^A-Za-z]+", nick.lower()):
            if len(token) > 1:
                givens.add(token)
    return {(g, surname) for g in givens}


def main():
    require_robots_once(SOURCE_URL, UA["User-Agent"], headers=UA,
                        label="il-cass-county-board-scraper")
    resp = requests.get(SOURCE_URL, headers=UA, timeout=60)
    resp.raise_for_status()
    lines = text_lines(resp.text)

    chair_keys = set()
    for line in lines:
        m = CHAIR_RE.search(line)
        if m:
            chair_keys = name_keys(m.group(1))
            break

    records = []
    district, current, digits = None, None, ""

    def close():
        nonlocal current, digits
        if current:
            d = re.sub(r"\D", "", digits)
            if len(d) >= 10:
                d = d[-10:]
                current["phone"] = "%s-%s-%s" % (d[:3], d[3:6], d[6:])
            records.append(current)
        current, digits = None, ""

    for line in lines:
        if STOP_RE.search(line):
            continue
        m = HEADING_RE.search(line)
        if m:
            close()
            district = m.group(1)
            continue
        if district is None:
            continue
        if EMAIL_RE.match(line):
            if current:
                current["email"] = line.lower()
            continue
        if NAME_RE.match(line) and not re.search(r"\d", line):
            close()
            current = {"name": line, "district": district, "phone": None, "email": None}
            continue
        if current and re.search(r"\d", line):
            # phone digits, possibly split across lines by the page's markup
            digits += line
    close()

    for rec in records:
        rec["role"] = ("Chairman" if (chair_keys and name_keys(rec["name"]) & chair_keys)
                       else None)

    if not records:
        print("cass-board-scraper: FAIL — zero member rows parsed (markup change?)",
              file=sys.stderr)
        sys.exit(1)
    if chair_keys and not any(r["role"] for r in records):
        print("cass-board-scraper: WARN — the page names a Chairman who matches no "
              "district member row; no role will be tagged", file=sys.stderr)

    out = json.dumps({"source": SOURCE_URL, "records": records}, indent=2, ensure_ascii=False)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(out)
        print("cass-board-scraper: %d records -> %s" % (len(records), sys.argv[1]))
    else:
        print(out)


if __name__ == "__main__":
    main()
