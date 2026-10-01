#!/usr/bin/env python3
"""
Scrape Washington County's board roster into raw board-roster records.

Stage 1 of the two-stage pipeline (scripts/build_washington_board_roster.py is
stage 2). The county publishes three district sections, each headed
"County Board District No. N" followed by a parenthetical naming the townships
it is composed of, then five members — name, phone(s), a "Send Message" mailto,
and a HOME ADDRESS.

THE HOME ADDRESS IS DELIBERATELY NOT READ. Every one of the fifteen members
has a street address printed under their name, and this scraper skips all of
them: a residence is not an office a resident can visit, and the fleet removed
Madison County's member residences for exactly this reason. Only the name,
phone and e-mail are taken.

The township composition IS read, because the shipped district boundary is
those townships dissolved (scripts/build_washington_board_districts.py). The
builder compares what this scraper saw against the table compiled into that
script and fails on any difference, so a redistricting turns the weekly job red
rather than leaving the derived lines a cycle out of date.

FETCH POSTURE: open. Plain server-rendered HTML.

Usage:
    python3 washington_county_board_scraper.py [output.json]   # default: stdout
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

SOURCE_URL = "https://washingtonco.illinois.gov/county-board/"
UA = {"User-Agent": UA_ROSTER_BOT}

HEADING_RE = re.compile(r"County Board District No\.\s*(\d+)", re.I)
COMPOSITION_RE = re.compile(r"^\(?\s*Composed of (.+?)\s*Townships?\.?\)?$", re.I)
NAME_RE = re.compile(r"^[A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*){1,3}$")
PHONE_RE = re.compile(r"\(?(\d{3})\)?\D{0,2}(\d{3})\D?(\d{4})")
# A residence line: a street address, or the "City, ST zip" that follows one.
ADDRESS_RE = re.compile(
    r"^\d+\s+\S|^[A-Za-z .'\-]+,\s*IL\.?\s*\d{5}|^\d+\s*[NSEW]\.?\s", re.I)
STOP_RE = re.compile(r"composed of \d+ elected|regular meetings|special meetings", re.I)


def text_lines(page):
    body = re.sub(r"(?is)<(script|style|nav|footer|head)[^>]*>.*?</\1>", " ", page)
    text = html_mod.unescape(re.sub(r"(?s)<[^>]+>", "\n", body))
    return [l.strip() for l in text.splitlines() if l.strip()]


def normalize_phone(raw):
    m = PHONE_RE.search(raw or "")
    return "-".join(m.groups()) if m else None


def main():
    require_robots_once(SOURCE_URL, UA["User-Agent"], headers=UA,
                        label="il-washington-county-board-scraper")
    resp = requests.get(SOURCE_URL, headers=UA, timeout=60)
    resp.raise_for_status()
    page = resp.text
    lines = text_lines(page)
    # mailto order follows the members' order on the page
    emails = [e.lower() for e in re.findall(
        r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", page)]

    records, compositions = [], {}
    district, current, email_i = None, None, 0
    for line in lines:
        if STOP_RE.search(line):
            break
        m = HEADING_RE.search(line)
        if m:
            if current:
                records.append(current)
                current = None
            district = m.group(1)
            continue
        if district is None:
            continue
        m = COMPOSITION_RE.match(line)
        if m:
            compositions[district] = m.group(1)
            continue
        if ADDRESS_RE.match(line):
            continue                       # residence — never collected
        if line.lower().startswith("send message"):
            if current and current.get("email") is None and email_i < len(emails):
                current["email"] = emails[email_i]
                email_i += 1
            continue
        p = normalize_phone(line)
        if p and current:
            if current["phone"] is None:
                current["phone"] = p
            continue
        if NAME_RE.match(line):
            if current:
                records.append(current)
            current = {"name": line, "district": district, "phone": None, "email": None}
    if current:
        records.append(current)

    for rec in records:
        rec["composition"] = compositions.get(rec["district"])

    if not records:
        print("washington-board-scraper: FAIL — zero member rows parsed (markup change?)",
              file=sys.stderr)
        sys.exit(1)
    missing = [d for d in sorted({r["district"] for r in records}) if d not in compositions]
    if missing:
        print("washington-board-scraper: WARN — no township composition found for "
              "district(s) %s" % ", ".join(missing), file=sys.stderr)

    out = json.dumps({"source": SOURCE_URL, "records": records}, indent=2, ensure_ascii=False)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(out)
        print("washington-board-scraper: %d records -> %s" % (len(records), sys.argv[1]))
    else:
        print(out)


if __name__ == "__main__":
    main()
