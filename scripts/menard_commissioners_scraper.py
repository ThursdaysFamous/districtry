#!/usr/bin/env python3
"""
Stage 1 of the Menard County Board of Commissioners roster pipeline: scrape the
county's board page into raw JSON for build_menard_commissioners_roster.py.

PAGE SHAPE. One table, five columns, ONE row. The header names the districts and
the single body row holds the five commissioners, each in an <address> block:

    <thead><tr><th>District 1</th>…<th>District 5</th></tr></thead>
    <tbody><tr>
      <td><address><strong>Dalton Whitley</strong><br/>
          Elected 2024<br/>4 year term<br/>(217) 632-3469<br/>
          <a href="mailto:djwhitley@…">dwhitley@…</a></address></td>
      …

So district comes from the COLUMN POSITION, not from any text beside the name.
That is worth stating because it is the one thing a careless parse would get
wrong silently: shuffle the columns and every commissioner is still a valid
commissioner, just attached to the wrong district. The builder's floor is the
full board of five, and the header is read rather than assumed, so a table that
stops naming its districts fails instead of guessing at order.

THE E-MAIL LINK AND ITS LABEL DISAGREE, for District 1 only. The county's markup
is <a href="mailto:djwhitley@menardcountyil.gov">dwhitley@menardcountyil.gov</a>
— "dj" in the address it sends to, "d" in the text it shows. The other four match
the same first-initial-plus-surname pattern the visible text uses, so either
could be the typo and nothing here can resolve it.

WHAT SHIPS IS THE HREF, and the reasoning is not a coin toss: the href is what
the county's own page ACTUALLY SENDS MAIL TO when a resident clicks it, and this
card's Email link should land where the county's link lands. The label is a
label. Both values are carried in the raw output and the run prints a NOTE, so
the disagreement is visible rather than quietly resolved — the same handling as
Montgomery's cody.gudel@ (see montgomery_county_board_scraper.py), and the same
rule: publish what the source publishes, report the conflict, invent nothing.

NAMES ARE PRINTED NATURALLY HERE ("Dalton Whitley"), not surname-first, so no
inversion is needed. One carries a SUFFIX — "Ed Whitcomb, Jr. - Chair" — which
is precisely the case the shared uninvert_name() guard refuses to touch, and the
builder asserts it stayed untouched.

ROLES ride the name cell after a dash: "Troy Cummings - Vice-Chair".

Usage:
    python3 menard_commissioners_scraper.py [output.json]
"""

import html
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_ROSTER_BOT,
    require_robots_once,
    output_path,
)

SOURCE_URL = "https://www.menardcountyil.gov/elected-officials/board-commissioners/"
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
}
REQUEST_TIMEOUT = 60

SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
TABLE_RE = re.compile(r"<table[^>]*>(.*?)</table>", re.S | re.I)
HEAD_CELL_RE = re.compile(r"<th[^>]*>(.*?)</th>", re.S | re.I)
BODY_ROW_RE = re.compile(r"<tbody[^>]*>(.*?)</tbody>", re.S | re.I)
CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
NAME_RE = re.compile(r"<strong[^>]*>(.*?)</strong>", re.S | re.I)
MAILTO_RE = re.compile(r'href="mailto:\s*([^"?\s>]+)"[^>]*>(.*?)</a>', re.S | re.I)
PHONE_RE = re.compile(r"\(?(\d{3})\)?[\s.\-]*(\d{3})[\s.\-]*(\d{4})")
DISTRICT_RE = re.compile(r"District\s+(\d+)", re.I)
TERM_RE = re.compile(r"\b(Elected|Appointed)\b\s*([0-9/]{4,10})", re.I)
TAG_RE = re.compile(r"<[^>]+>")
# "Name - Role" / "Name — Role". Split on the LAST dash so a hyphenated surname
# survives; the county writes plain dashes around the role.
ROLE_SPLIT_RE = re.compile(r"\s+[-–—]\s+")


def text_of(fragment):
    return re.sub(r"\s+", " ",
                  html.unescape(TAG_RE.sub(" ", fragment or ""))).replace("\xa0", " ").strip()


def parse(page):
    page = SCRIPT_RE.sub(" ", page)
    for table in TABLE_RE.findall(page):
        heads = [text_of(h) for h in HEAD_CELL_RE.findall(table)]
        districts = [DISTRICT_RE.search(h) for h in heads]
        if not heads or not all(districts):
            continue
        body = BODY_ROW_RE.search(table)
        if not body:
            continue
        cells = CELL_RE.findall(body.group(1))
        if len(cells) != len(heads):
            continue
        records = []
        for head, cell in zip(districts, cells):
            name_m = NAME_RE.search(cell)
            if not name_m:
                continue
            raw = text_of(name_m.group(1))
            parts = ROLE_SPLIT_RE.split(raw, 1)
            rec = {"district": str(int(head.group(1))), "name": parts[0].strip()}
            if len(parts) > 1 and parts[1].strip():
                rec["role"] = parts[1].strip()
            body_text = text_of(cell)
            phone = PHONE_RE.search(body_text)
            if phone:
                rec["phone"] = "%s-%s-%s" % phone.groups()
            term = TERM_RE.search(body_text)
            if term:
                rec["seated"] = "%s %s" % (term.group(1).title(), term.group(2))
            mail = MAILTO_RE.search(cell)
            if mail:
                rec["email"] = html.unescape(mail.group(1)).strip()
                shown = text_of(mail.group(2))
                if shown and shown.lower() != rec["email"].lower():
                    rec["email_label"] = shown
            records.append(rec)
        if records:
            return records
    return []


def main():
    out_path = output_path("menard_commissioners_raw.json")
    require_robots_once(SOURCE_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-menard-commissioners-scraper")
    resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    records = parse(resp.text)
    if not records:
        print("menard-scraper: FAIL — parsed 0 commissioners. The page's one "
              "district-headed table changed shape; district comes from the "
              "COLUMN, so this refuses rather than guessing at order.",
              file=sys.stderr)
        sys.exit(1)

    for rec in records:
        if rec.get("email_label"):
            print("menard-scraper: NOTE — District %s (%s) links to %s but "
                  "displays %s. Shipping the LINK, because that is where the "
                  "county's own page sends mail; not corrected here."
                  % (rec["district"], rec["name"], rec["email"], rec["email_label"]),
                  file=sys.stderr)

    payload = {"source_url": SOURCE_URL, "records": records}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("menard-scraper: wrote %s — %d commissioners across %d districts, "
          "%d phones, %d e-mails, %d role(s)"
          % (out_path, len(records), len({r["district"] for r in records}),
             sum(1 for r in records if r.get("phone")),
             sum(1 for r in records if r.get("email")),
             sum(1 for r in records if r.get("role"))))


if __name__ == "__main__":
    main()
