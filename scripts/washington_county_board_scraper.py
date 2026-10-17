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
phones and e-mail are taken.

EVERY NUMBER A MEMBER'S ROW PRINTS IS READ. Until 2026-10-17 only the first
was kept, so the member who prints a second number ("... OR (Cell) ...") lost
it and the "(Cell)" label never reached a reader. Since Adam's ruling that day
("if the official government source uses personal phone numbers, we publish
those") the first number goes in `phone` and any others in `phonesExtra`, in
the page's order, each led by the word in the parenthesis before it ("cell
618-..."). A number printed anywhere else on the page as well is an office line
and is not added to a member as their own; a number marked as a fax never
ships. Measured 2026-10-17: all fifteen members print a number, four of those
numbers are labelled "(Cell)", and one member prints two.

The township composition IS read, because the shipped district boundary is
those townships dissolved (scripts/build_washington_board_districts.py). The
builder compares what this scraper saw against the table compiled into that
script and fails on any difference, so a redistricting turns the weekly job red
rather than leaving the derived lines a cycle out of date.

FETCH POSTURE: open. Plain server-rendered HTML.

Usage:
    python3 washington_county_board_scraper.py [output.json]   # default: stdout
"""

import collections
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
# The label the page prints in parentheses before a number, "(Cell)", and the
# word it ships as (the fleet's convention: scraper_common.PERSON_PHONE_LABELS).
# A label outside this table ships no word.
LABEL_RE = re.compile(r"\(\s*([A-Za-z]+)\s*\)\s*$")
PHONE_LABELS = {"cell": "cell", "c": "cell", "home": "home", "h": "home",
                "work": "work", "w": "work", "business": "business",
                "b": "business", "office": "office", "o": "office",
                "mobile": "mobile"}
FAX_RE = re.compile(r"\bfax\b", re.I)
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


def line_phones(line):
    """Every number on a line, in order, as "618-555-0100" or, where the page
    prints a label in parentheses before it, "cell 618-555-0100". A number the
    text before it marks as a fax is left out."""
    out, last = [], 0
    for m in PHONE_RE.finditer(line or ""):
        before, last = line[last:m.start()], m.end()
        if FAX_RE.search(before):
            continue
        label = LABEL_RE.search(before)
        word = PHONE_LABELS.get(label.group(1).lower()) if label else None
        number = "-".join(m.groups())
        out.append("%s %s" % (word, number) if word else number)
    return out


def digits(number):
    return re.sub(r"\D", "", number)[-10:]


def page_numbers(page):
    """How many times each number is printed anywhere on the page, header and
    footer included, so a county or office line is recognised wherever it sits."""
    body = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
    text = html_mod.unescape(re.sub(r"(?s)<[^>]+>", " ", body))
    return collections.Counter(digits("".join(m.groups())) for m in PHONE_RE.finditer(text))


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
            current["phones"].extend(line_phones(line))
            continue
        if NAME_RE.match(line):
            if current:
                records.append(current)
            current = {"name": line, "district": district, "phones": [], "email": None}
    if current:
        records.append(current)

    # The first number stays where it always went; a further number printed
    # more than once on the page belongs to an office and is not added.
    printed = page_numbers(page)
    for rec in records:
        numbers = rec.pop("phones")
        extras = [n for n in numbers[1:] if printed[digits(n)] < 2]
        rec["phone"] = numbers[0] if numbers else None
        rec["phonesExtra"] = extras

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
