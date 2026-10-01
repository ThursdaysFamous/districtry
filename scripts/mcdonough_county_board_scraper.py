#!/usr/bin/env python3
"""
Scrape the McDonough County Board's member table into the intermediate JSON
build_mcdonough_board_roster.py consumes.

SOURCE. http://mcg.mcdonough.il.us/members.html — the county's own board page.
Note the scheme: this site is served over HTTP ONLY and has no HTTPS listener,
which is why it is spelled out rather than upgraded. It is also a subdomain
(`mcg.`), and that combination is why a nine-hostname sweep on 2026-08-02
concluded the county had no public website at all. Its clerk supplied the
address on request the next day.

WHAT THE PAGE CARRIES, per member: name, party, the year the seat is next up,
a HOME address, a phone and an e-mail — laid out as a four-cell table row under
a district heading that also prints that district's precinct composition. The
composition is read by build_mcdonough_board_districts.py; this scraper reads
the people.

HOME ADDRESSES ARE NOT COLLECTED. Twenty-one of the twenty-one rows print one,
and the third cell mixes it with the phone ("11 Indian Trail / Macomb, IL 61455
/ (309)837-4999"). Only the phone is taken, by matching a phone shape against
each line; every other line of that cell is discarded unread. This is the same
rule Logan, Mason and Brown are held to, and it is a rule about people rather
than about parsing — the county may publish where its members live, but a map
that puts a pin on it is a different thing from a directory that lists it.

The e-mail addresses ARE collected. Most are personal domains (gmail, comcast,
hotmail) rather than county ones, but they are what the county publishes as the
way to reach each member about county business, and a card that omitted them
would leave a resident with no route to their own representative.

CHAIR AND VICE-CHAIR are named above the table ("County Board Chair - Eric
Blakeley"), not on the member rows, so they are read from there and matched
back onto the member of that name. A tag that matches nobody is a warning, not
a silent drop — the Woodford/Boone posture: a role is rendered only where the
county says who holds it.

Usage:
    python3 mcdonough_county_board_scraper.py --out mcdonough_board_raw.json
    python3 mcdonough_county_board_scraper.py --out out.json --html local.html
"""

import argparse
import collections
import datetime
import json
import re
import sys

import requests
from scraper_common import require_robots_once, UA_ROSTER_BOT, fetch as fetch_with_retry  # noqa: E402  (shared machinery — do not fork)

SOURCE_URL = "http://mcg.mcdonough.il.us/members.html"
COUNTY_PAGE = "http://mcg.mcdonough.il.us/"
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
}
REQUEST_TIMEOUT = 120

WORD_DISTRICT = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
                 "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"}
DISTRICT_RE = re.compile(r"(?i)\bDistrict\s+([A-Za-z]+|\d+)\b")
PHONE_RE = re.compile(r"\(?(\d{3})\)?[\s.\-]?(\d{3})[\s.\-]?(\d{4})")
PARTY_RE = re.compile(r"^\(([A-Za-z])\)$")
YEAR_RE = re.compile(r"^(20\d{2})$")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Matched against a TAG-STRIPPED copy of the page, not the markup: the county
# writes "<strong>County Board Chair</strong> - Eric Blakeley", so the label and
# the name are separated by a closing tag and no markup-aware pattern spanning
# them stays readable. The name is bounded as a run of capitalised words rather
# than "up to the next tag", because after stripping there are no tags left.
# The officer LABEL only. What follows it is not captured by this pattern at
# all — the text is SPLIT on it, so each officer's name runs to the next label
# or to the end, and is then resolved by longest-prefix against the member list.
#
# That indirection is the third attempt and the first correct one. Flattened,
# the page reads "… Chair - Eric Blakeley County Board Vice-Chair - Mike Cox
# Precinct Map": a name is followed by whatever the county put next, which is
# first another label and then a link caption. Blacklisting the trailing words
# fixed one case and missed the other, twice; capturing greedily instead ate
# the Vice-Chair LABEL into the Chair's name, so the second officer vanished
# silently. Splitting cannot do either, because a label is a boundary rather
# than something to match through.
CHAIR_LABEL_RE = re.compile(r"(?i)County Board\s+(Vice[-\s]*Chair|Chair)\s*[-–]\s*")
NON_PERSON = ("vacant", "vacancy", "(vacancy)", "n/a", "")

MIN_MEMBERS = 21
MIN_DISTRICTS = 3


def fetch(url):
    # scraper_common.fetch retries 429/5xx (numeric Retry-After honoured,
    # capped) and refuses to retry 401/403/404 — the Henry rule. Parsing and
    # every page check stay in this file.
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-mcdonough-county-board-scraper")
    return fetch_with_retry(url, HEADERS, timeout=REQUEST_TIMEOUT).text


def cell_lines(html_fragment):
    """A table cell's visible lines, <br>-separated, tags stripped."""
    text = re.sub(r"(?i)<br\s*/?>", "\n", html_fragment)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = (text.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&#39;", "'").replace("&quot;", '"'))
    return [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()
            if line.strip()]


def parse(html, warnings):
    role_candidates = []
    flat = re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", html))
    parts = CHAIR_LABEL_RE.split(flat)
    # split() with one capturing group yields [before, label, text, label, text…]
    for i in range(1, len(parts) - 1, 2):
        label = re.sub(r"(?i)vice[-\s]*chair", "Vice-Chair", parts[i].strip())
        label = "Chair" if label.lower() == "chair" else label
        role_candidates.append((parts[i + 1].strip(), label))

    members = []
    district = None
    # Rows are split on EITHER a <tr> or a </tr>, not matched as <tr>…</tr>
    # pairs, because this page's markup is not well formed: District Three's
    # second member (Vicky Kipling) is written with no opening <tr> at all —
    # her cells sit between the previous row's </tr> and the next <tr>. A
    # paired match skips that row silently, which is exactly what the 21-member
    # floor caught. Splitting on both delimiters puts every run of cells in its
    # own chunk whether or not the county closed the tag.
    for row in re.split(r"(?i)<tr\b[^>]*>|</tr\s*>", html):
        # `[^>]*>` and not `(.*?)`: the opening tag's own attributes are not
        # cell content, and capturing them put `width="24%">` on the front of
        # every member's name — the tag stripper cannot remove text that sits
        # outside a tag.
        cells = re.findall(r"(?is)<t[dh]\b[^>]*>(.*?)</t[dh]>", row)
        if not cells:
            continue
        # A district heading is a single full-width cell naming the district.
        if len(cells) == 1:
            heading = " ".join(cell_lines(cells[0]))
            match = DISTRICT_RE.search(heading)
            if match:
                token = match.group(1).lower()
                district = WORD_DISTRICT.get(token, token if token.isdigit() else None)
                if district is None:
                    warnings.append("could not read a district number from %r" % heading)
            continue
        if district is None or len(cells) < 4:
            continue

        name_lines = cell_lines(cells[0])
        if not name_lines:
            continue
        name = name_lines[0]
        if name.lower() in NON_PERSON:
            warnings.append("district %s publishes a seat as %r — counted, never "
                            "named" % (district, name))
            continue
        party = None
        for line in name_lines[1:]:
            party_match = PARTY_RE.match(line)
            if party_match:
                party = party_match.group(1).upper()
        term = None
        for line in cell_lines(cells[1]):
            if YEAR_RE.match(line):
                term = int(line)
        # Cell 3 is the member's HOME address plus a phone. Only the phone is
        # read; every other line is discarded without being stored anywhere.
        phone = None
        for line in cell_lines(cells[2]):
            phone_match = PHONE_RE.search(line)
            if phone_match and not re.search(r"[A-Za-z]{3}", line):
                phone = "%s-%s-%s" % phone_match.groups()
        email_match = EMAIL_RE.search(re.sub(r"(?s)<[^>]+>", " ", cells[3]))
        email = email_match.group(0).lower() if email_match else None

        members.append({
            "district": district,
            "name": name,
            "party": party,
            "term_expires": term,
            "phone": phone,
            "email": email,
            "role": None,
        })

    # Resolve each role tag to the LONGEST member name the captured text starts
    # with. A tag that resolves to nobody is reported and dropped rather than
    # guessed at — the Woodford/Boone posture: a role is rendered only where the
    # county says who holds it.
    by_name = {m["name"]: m for m in members}
    for candidate, label in role_candidates:
        match = None
        for name in sorted(by_name, key=len, reverse=True):
            if candidate == name or candidate.startswith(name + " "):
                match = name
                break
        if match is None:
            warnings.append("the page names %r as %s but no member row carries "
                            "that name — role not applied" % (candidate, label))
            continue
        if by_name[match]["role"] and by_name[match]["role"] != label:
            warnings.append("%s is tagged both %s and %s — keeping the first"
                            % (match, by_name[match]["role"], label))
            continue
        by_name[match]["role"] = label
    return members


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--html", help="parse a local copy instead of fetching")
    args = parser.parse_args()

    warnings = []
    try:
        html = open(args.html, encoding="utf-8", errors="replace").read() \
            if args.html else fetch(SOURCE_URL)
        members = parse(html, warnings)
    except Exception as exc:  # noqa: BLE001
        print("FATAL: %s" % exc, file=sys.stderr)
        sys.exit(1)

    for warning in sorted(set(warnings)):
        print("  warning: %s" % warning, file=sys.stderr)

    per = collections.Counter(m["district"] for m in members)
    problems = []
    if len(members) < MIN_MEMBERS:
        problems.append("%d members < floor %d" % (len(members), MIN_MEMBERS))
    if len(per) < MIN_DISTRICTS:
        problems.append("%d districts < floor %d" % (len(per), MIN_DISTRICTS))
    # A row whose e-mail landed outside its cell would show up as a member with
    # none, which is the failure this four-cell layout invites.
    without_email = [m["name"] for m in members if not m["email"]]
    if len(without_email) > 2:
        problems.append("%d members carry no e-mail (%s) — the cell order "
                        "probably moved" % (len(without_email),
                                            ", ".join(without_email[:4])))
    if problems:
        for problem in problems:
            print("  FAIL: %s" % problem, file=sys.stderr)
        print("FATAL: refusing to write a payload that lost coverage", file=sys.stderr)
        sys.exit(1)

    scraped_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "county": "McDonough",
        "source_url": SOURCE_URL,
        "county_page": COUNTY_PAGE,
        "scraped_at": scraped_at,
        "members": members,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    tagged = sum(1 for m in members if m["role"])
    print("scraped %d members across %d districts (%s), %d with phone, %d with "
          "e-mail, %d role-tagged -> %s"
          % (len(members), len(per),
             ", ".join("D%s=%d" % (d, per[d]) for d in sorted(per, key=int)),
             sum(1 for m in members if m["phone"]),
             sum(1 for m in members if m["email"]), tagged, args.out),
          file=sys.stderr)


if __name__ == "__main__":
    main()
