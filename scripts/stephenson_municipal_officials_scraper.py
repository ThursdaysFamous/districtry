#!/usr/bin/env python3
"""
Scrape Stephenson County's "City and Villages" directory into the payload
build_municipal_officials_roster.py consumes.

SOURCE. One county page, one table per municipality, each row three cells:
name | address | office. Most office cells carry an explicit "(Elected)" or
"(Appointed)" marker — 66 of 86 rows at the 2026-07 reading — which is a
stronger elected/appointed signal than any other county in this roster
publishes; Cook's DOEO API and the LaSalle directory both leave it to be
inferred from the office TITLE. It is used only where it is present: a bare
office ships with no appointed flag rather than being assumed elected. The
municipality's own name and phone are the <span class="subheader"> above each
table.

That gives full-governing-body depth — head of government, clerk, treasurer and
every trustee — so Stephenson joins as a full-governing-body county rather than
a mayor-level one.

COVERAGE IS 10 OF THE COUNTY'S 11 MUNICIPALITIES. The page is the county's
village directory and omits FREEPORT, the county seat and by far its largest
city. Freeport publishes its own governing body and is scraped separately by
freeport_council_scraper.py, which the builder applies as an --enrich payload.

FETCH POSTURE: open. Static, server-rendered Revize HTML; plain `requests` with
a browser UA succeeds and there is no challenge.

THE ADDRESSES ARE RESIDENCES AND ARE NOT COLLECTED. Every address cell is a
board member's home or PO box ("PO Box 541, Cedarville"), not a village hall —
different members of the same village carry different addresses, and one
Dakota row is a home in a neighbouring town. Shipping them would put private
home addresses on a public card, which is the same call LaSalle, Madison,
McHenry, Livingston, Sangamon and Winnebago all made. The municipality-level
phone from the subheader IS collected; it is the village's own number.

Usage:
    python3 stephenson_municipal_officials_scraper.py --out stephenson_municipal_officials.json
"""

import argparse
import datetime
import html
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_CHROME_WIN_126,
    require_robots_once,
)

DIRECTORY_URL = ("https://stephensoncountyil.gov/government/"
                 "boards_commissions_committees/city_and_villages.php")
HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
}
REQUEST_TIMEOUT = 90

SUBHEAD_RE = re.compile(r'<span class="subheader">(.*?)</span>', re.S | re.I)
ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
HEAD_LINE_RE = re.compile(r"^\s*([A-Z][A-Za-z .'-]+?)\s*[-–]\s*"
                          r"((?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4})\s*$")
# "(Elected)", "(Appointed)" and — on the one village-police row — "(Hired)".
# Written without a leading space because one row runs it together as
# "Trustee(Elected)".
STATUS_RE = re.compile(r"\((Elected|Appointed|Hired)\)", re.I)

HEAD_TITLES = {"mayor", "president", "village president", "city president"}

# ---------------------------------------------------------------------------
# OFFICES THE ELECTION AUTHORITY STATED AND THE DIRECTORY CONTRADICTS.
#
# The county's directory is the source of record for every row it fills in, and
# nothing here may touch a row it agrees with. This table exists for one narrow
# case: the county's page and the county's ELECTION AUTHORITY, in writing, say
# different things about the same seat. That is not a gap to infer across — it
# is two sourced claims, and the honest handling is to ship the stronger one and
# record the other, not to average them or to pick silently.
#
# SELF-RETIRING. An entry pins the office the county printed when it was
# written. If that cell changes at all — corrected, emptied, or the row removed
# — the entry stops matching and the run prints a RETIRE line, the same shape as
# the clerk roster's bounce guard. An entry can never outlive its conflict.
#
# IT IS EMPTY, AND THAT IS THE POINT. The one entry it ever held — Dakota's
# Jonathon Riley, whom this directory printed as a Trustee while Clerk & Recorder
# Jazmin Wingert said in writing he was president — lasted about eighteen hours.
# On 2026-08-06 STEPHENSON COUNTY UPDATED THE PAGE ITSELF: Riley now reads
# "President (Appointed)", the entry stopped matching, the run printed its RETIRE
# line, and the entry was deleted. The mechanism stays for the next conflict.
#
# The better record is what the update contained. The county did not just fix
# one title — it republished the whole Dakota table, and three trustees and the
# clerk this project had been shipping are no longer on it. ASKING FIXED THE
# SOURCE rather than producing a correction for this map to carry privately,
# which helps everyone who reads that directory. It also means the shipped
# roster was stale in a way no gate here could have detected: every name parsed,
# every count held, and the people had simply changed.
CLERK_STATED_OFFICES = {}

# Bodies this page lists alongside the village's own officers that are NOT the
# municipal government: Davis prints its zoning board of appeals, German Valley
# its hired police. They are appointed members of a separate body, and shipping
# them on a "who represents you" card would put people on it who hold no
# municipal office. Dropped, but counted in the run summary — never silently.
#
# The test is on the FULL office string, not a substring, precisely so that
# Davis's "Trustee/Zoning Chairperson" is kept: he is a sitting trustee who also
# chairs zoning, and split_office() below reduces him to "Trustee".
NON_GOVERNING_OFFICES = {"zoning board", "village police"}
# Placeholders the page uses for a seat nobody holds. A card must never print
# "Unassigned" as though it were a person's name.
NON_PERSON_NAMES = {"unassigned", "vacant", "vacancy", "open", "tbd", "none"}

MIN_MUNICIPALITIES = 8
MIN_OFFICIALS = 60
MIN_HEADS = 6


def text_of(fragment):
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", fragment or ""))).strip()


def clean(v):
    v = re.sub(r"\s+", " ", (v or "")).strip()
    return v or None


def split_office(office):
    """'Trustee/Zoning Chairperson' -> 'Trustee'.

    A combined title is reduced to the municipal seat it names, so the person
    is classified by the office he actually holds rather than by the committee
    he chairs. A slashed title with no recognisable seat is left whole and
    reaches the builder as-is, which warns rather than guesses.
    """
    parts = [p.strip() for p in (office or "").split("/") if p.strip()]
    for part in parts:
        if part.lower() in ("trustee", "president", "mayor", "clerk", "treasurer",
                            "alderman", "alderwoman", "alderperson"):
            return part
    return office


def normalise_office(raw):
    """'Village President (Elected)' -> ('Village President', False, True)."""
    status = STATUS_RE.search(raw or "")
    marker = status.group(1).lower() if status else None
    office = clean(STATUS_RE.sub("", raw or ""))
    return split_office(office), marker in ("appointed", "hired"), bool(status)


def parse(page, warnings, dropped):
    page = SCRIPT_RE.sub(" ", page)
    # Each municipality is a subheader followed by its own table; slicing between
    # consecutive subheaders keeps a village's rows with its own name even though
    # the markup nests them as siblings rather than as a container.
    heads = [(m.start(), m.end(), text_of(m.group(1))) for m in SUBHEAD_RE.finditer(page)]
    municipalities, officials, unmarked = [], [], []
    stated_used = set()
    for i, (s0, e0, label) in enumerate(heads):
        hm = HEAD_LINE_RE.match(label)
        if not hm:
            continue
        name, phone = clean(hm.group(1)), clean(hm.group(2))
        seg = page[e0: heads[i + 1][0] if i + 1 < len(heads) else len(page)]
        rows = []
        for row in ROW_RE.findall(seg):
            cells = [text_of(c) for c in CELL_RE.findall(row)]
            if len(cells) < 3:
                continue
            person, _residence, office_raw = cells[0], cells[1], cells[2]
            if not person:
                continue
            office, appointed, marked = normalise_office(office_raw)
            if not office:
                # A named person with a blank office cell, shipped NOWHERE: the
                # county published no title, and inferring one from the rows
                # around it is exactly the guess the honesty rules forbid.
                warnings.append("%s: '%s' is listed with no office — shipped "
                                "nowhere; the county published no title"
                                % (name, person))
                continue
            stated = CLERK_STATED_OFFICES.get((name, person))
            if stated and office == stated["county_prints"]:
                # The county's page and the county's election authority
                # disagree about this seat. The authority's written answer
                # ships; see CLERK_STATED_OFFICES for why, and for the guard
                # that retires this the moment the page changes.
                office, appointed, marked = stated["office"], False, False
                stated_used.add((name, person))
                warnings.append("%s: county page says '%s' for %s; shipped as "
                                "'%s' — %s"
                                % (name, stated["county_prints"], person,
                                   office, stated["why"]))
            if office.lower() in NON_GOVERNING_OFFICES:
                dropped.append("%s: %s (%s) — not a municipal office"
                               % (name, person, office))
                continue
            if person.strip().lower() in NON_PERSON_NAMES:
                dropped.append("%s: %s seat listed as '%s' — no officeholder"
                               % (name, office, person))
                continue
            rows.append((person, office, appointed, marked))
        if not rows:
            warnings.append("no officers parsed for %s — check the table markup" % name)
            continue
        municipalities.append(name)
        shared = {
            "jurisdiction": name,
            "office_address": None,   # residences only on this page — see header
            "office_city": None,
            "office_state": None,
            "office_zip": None,
            "office_phone": phone,
            "office_email": None,
            "website": None,
        }
        for person, office, appointed, marked in rows:
            rec = dict(shared, office=office, name=person, district=None)
            if appointed:
                rec["appointed"] = True
            if not marked:
                unmarked.append("%s: %s (%s)" % (name, person, office))
            officials.append(rec)
    # An entry that never applied is the loud case: the conflict it was
    # written for is over. Either the county corrected the office (good — the
    # county is the source of record and the entry should go) or the row moved
    # and the table now describes somebody the page no longer prints that way.
    for key in sorted(set(CLERK_STATED_OFFICES) - stated_used):
        warnings.append("RETIRE CLERK_STATED_OFFICES[%r] — it did not apply this "
                        "run, so the county no longer prints %r for that row; "
                        "the conflict is over, delete the entry"
                        % (key, CLERK_STATED_OFFICES[key]["county_prints"]))
    return municipalities, officials, unmarked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--html", help="parse a local copy instead of fetching")
    args = ap.parse_args()

    if args.html:
        page = open(args.html, encoding="utf-8", errors="replace").read()
    else:
        require_robots_once(DIRECTORY_URL, HEADERS["User-Agent"], headers=HEADERS,
                            label="il-stephenson-municipal-officials-scraper")
        resp = requests.get(DIRECTORY_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        page = resp.text

    warnings, dropped = [], []
    municipalities, officials, unmarked = parse(page, warnings, dropped)
    for w in sorted(set(warnings)):
        print("  warning: %s" % w, file=sys.stderr)
    for d in sorted(set(dropped)):
        print("  dropped: %s" % d, file=sys.stderr)
    # Counted rather than listed per row: a fifth of the page has always been
    # unmarked, so one line keeps a real change (the county dropping the marker
    # wholesale) visible without 20 lines of noise every week.
    if unmarked:
        print("  note: %d of %d rows carry no (Elected)/(Appointed) marker; "
              "shipped with no appointed flag rather than assumed elected"
              % (len(unmarked), len(officials)), file=sys.stderr)

    heads = sum(1 for p in officials if (p["office"] or "").lower() in HEAD_TITLES)
    problems = []
    if len(municipalities) < MIN_MUNICIPALITIES:
        problems.append("%d municipalities < floor %d" % (len(municipalities), MIN_MUNICIPALITIES))
    if len(officials) < MIN_OFFICIALS:
        problems.append("%d officials < floor %d" % (len(officials), MIN_OFFICIALS))
    if heads < MIN_HEADS:
        problems.append("%d heads of government < floor %d" % (heads, MIN_HEADS))
    if problems:
        for p in problems:
            print("  FAIL: %s" % p, file=sys.stderr)
        print("FATAL: refusing to write a payload that lost coverage", file=sys.stderr)
        sys.exit(1)

    scraped_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for p in officials:
        p["source_url"] = DIRECTORY_URL
        p["scraped_at"] = scraped_at
    payload = {
        "county": "Stephenson",
        "directory_url": DIRECTORY_URL,
        "officials_page": DIRECTORY_URL,
        "scraped_at": scraped_at,
        "municipalities": [{"name": n, "source_url": DIRECTORY_URL,
                            "scraped_at": scraped_at} for n in municipalities],
        "officials": officials,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("scraped %d municipalities, %d officials (%d heads, %d appointed) -> %s"
          % (len(municipalities), len(officials), heads,
             sum(1 for p in officials if p.get("appointed")), args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
