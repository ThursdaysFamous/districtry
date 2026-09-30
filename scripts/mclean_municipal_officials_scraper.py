#!/usr/bin/env python3
"""
Scrape McLean County's three ward-electing cities into the payload
build_municipal_officials_roster.py consumes.

SOURCES — three city rosters of record, one page each:

  * Bloomington — the city's own Board of Election Commissioners council
    page (Bloomington runs its own election commission, so the BEC, not the
    county clerk, is its officeholder authority). Mayor + nine ward
    alderpersons, each with TERM YEAR, direct phone and ward e-mail.
  * Le Roy — the city's council page: mayor + eight ward aldermen (two per
    ward), each with a city e-mail.
  * Lexington — the city's council + mayor pages (the city moved to
    lexingtonil.gov; the old lexingtonillinois.org 301s): mayor + six ward
    councilmen (two per ward), each with a city e-mail.

WHY CITY PAGES AND NOT THE COUNTY GIS. The clerk's MyElectedRepresentatives
City Council layer carries all 16 ward polygons with seat names, but its
Le Roy and Lexington rows were last edited 2022 and are STALE across the
April 2025 election — measured 2026-08-01: Le Roy wrong on 2 of 8 seats
(Welander -> Tucker, Morfey -> Dunafin), Lexington wrong on 2 of 6 (Little ->
Shubert, Stover -> Solberg). Bloomington's GIS rows are current (edited
2025-07) and were verified 9/9 against the BEC page, which also carries the
mayor and term years the GIS lacks — so the pages win on every axis.

WHY ONLY THREE MUNICIPALITIES. The county clerk's own Local Elected &
Appointed Officials database covers every municipality, but it is an
Airtable INTERFACE share (pag…) — fully JS-rendered, its data API needs
undocumented per-request parameters, and no fetch rung available to this
repo's CI renders it. These three cities are the county's ward-electing
municipalities — the rosters the municipal-ward layer joins against — and
each publishes its own machine-readable page. The county's remaining
municipalities stay on the guidebook's ledger against the Airtable route.

FETCH POSTURE: open. All three sites answer plain `requests` with a
browser UA.

Usage:
    python3 mclean_municipal_officials_scraper.py --out mclean_municipal_officials.json
"""

import argparse
import datetime
import html as html_mod
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery — do not fork)
    UA_CHROME_WIN_126,
    require_robots_allowed,
)

BLOOMINGTON_URL = "https://bloomingtonelectionsil.gov/information/bloomingtoncitycouncil/"
LEROY_URL = "https://www.leroy.org/government/city-hall/city-council"
LEXINGTON_COUNCIL_URL = "https://lexingtonil.gov/city-council"
LEXINGTON_MAYOR_URL = "https://lexingtonil.gov/mayor"
HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
}
REQUEST_TIMEOUT = 120

PHONE_RE = re.compile(r"\(?(\d{3})\)?[-.\s]*(\d{3})[-.\s]*(\d{4})")
EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
TERM_RE = re.compile(r"Term expires:\s*(\d{4})", re.I)
# A word may be a quoted nickname ('Mary "Mollie" Ward').
NAME_RE = re.compile(r"^[A-Z\"“][A-Za-z.'’\"“”()-]+(?:\s+[A-Z\"“][A-Za-z.'’\"“”()-]+){1,3}$")

MIN_WARD_SEATS = {"Bloomington": 8, "Le Roy": 7, "Lexington": 5}


# --- robots.txt, read once per host with the client this file crawls with ------
# CLAUDE.md's rule is that robots.txt is read before the first fetch of a host,
# and measured 2026-09-12 almost no scraper here enacted it. This file does now.
# Three municipalities on three hosts, one client, so the reading is per host and
# cached: measured 2026-09-30 through robots_policy's reader, all three serve a
# policy (781, 1,015 and 1,510 bytes) in which no rule matches the council pages
# below. Lexington's two pages share one host and therefore one reading, which is
# what keeps this at one extra request per site per run.
_ROBOTS_ASKED = set()


def require_robots(url):
    from urllib.parse import urlsplit

    host = urlsplit(url).hostname or ""
    if host in _ROBOTS_ASKED:
        return
    why = require_robots_allowed(url, HEADERS["User-Agent"], headers=HEADERS,
                                label="mclean-municipal-officials-scraper")
    print("robots.txt %s: %s" % (host, why), file=sys.stderr)
    _ROBOTS_ASKED.add(host)


def fetch_lines(url):
    require_robots(url)
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", resp.text,
                  flags=re.S | re.I)
    text = html_mod.unescape(re.sub(r"<[^>]+>", "\n", text))
    return [l.strip() for l in text.split("\n") if l.strip()]


def person(name, office, district=None, phone=None, email=None, term=None):
    rec = {"name": name, "office": office, "district": district}
    if phone:
        rec["person_phone"] = "%s-%s-%s" % PHONE_RE.search(phone).groups()
    if email:
        rec["person_email"] = email.lower()
    if term:
        rec["term_expires"] = term
    return rec


def parse_bloomington(lines, warnings):
    """BEC blocks: 'MAYOR' / 'WARD N ALDERPERSON (…)' then term, name, phone, email."""
    records = []
    office = None
    ward = None
    term = None
    pending = None
    reach = 0        # contact lines may sit at most this far below the name
    for line in lines:
        header = re.match(r"^(MAYOR|WARD\s+(\d+)\s+ALDERPERSON)", line)
        if header:
            if pending:
                records.append(pending)
            office = "Mayor" if header.group(1) == "MAYOR" else "Alderperson"
            ward = ("Ward %s" % header.group(2)) if header.group(2) else None
            term = None
            pending = None
            continue
        if office is None:
            continue
        tm = TERM_RE.match(line)
        if tm:
            term = tm.group(1)
            continue
        # Contact attaches only within a few lines of its name — the page
        # footer carries the BEC's own e-mail, which must never land on the
        # last alderperson whose block simply omits one.
        if pending and reach > 0:
            reach -= 1
            em = EMAIL_RE.search(line)
            if em:
                pending["person_email"] = em.group(1).lower()
                continue
            pm = PHONE_RE.fullmatch(line.strip())
            if pm:
                pending["person_phone"] = "%s-%s-%s" % pm.groups()
                continue
        if pending is None and NAME_RE.match(line) and not re.search(r"\d", line):
            pending = person(line, office, ward, term=term)
            reach = 3
    if pending:
        records.append(pending)
    heads = [r for r in records if r["office"] == "Mayor"]
    seats = [r for r in records if r.get("district")]
    if len(heads) != 1 or len(seats) < MIN_WARD_SEATS["Bloomington"]:
        raise RuntimeError("Bloomington BEC page parsed %d mayors / %d ward seats — "
                           "layout changed" % (len(heads), len(seats)))
    return records


def parse_leroy(lines, warnings):
    """'Council Members' anchor, then Mayor block and 'Ward N' groups of
    Name / 'Alderman' / e-mail pairs."""
    try:
        start = lines.index("Council Members")
    except ValueError:
        raise RuntimeError("Le Roy page lost its 'Council Members' anchor")
    records = []
    ward = None
    mode = None            # "mayor" after the Mayor caption
    pending = None
    for line in lines[start + 1:start + 80]:
        if re.match(r"^Council Meeting", line, re.I):
            break
        if line == "Mayor":
            mode = "mayor"
            continue
        wm = re.match(r"^Ward\s+(\d+)$", line)
        if wm:
            if pending:
                records.append(pending)
                pending = None
            ward = "Ward %s" % wm.group(1)
            mode = "board"
            continue
        if line == "Alderman":
            continue
        em = EMAIL_RE.search(line)
        if em and pending:
            pending["person_email"] = em.group(1).lower()
            records.append(pending)
            pending = None
            continue
        pm = PHONE_RE.fullmatch(line.strip())
        if pm and pending:
            pending["person_phone"] = "%s-%s-%s" % pm.groups()
            continue
        if NAME_RE.match(line) and not re.search(r"\d", line):
            if pending:
                records.append(pending)
            if mode == "mayor":
                pending = person(line, "Mayor")
                mode = "board"     # only one mayor
            elif ward:
                pending = person(line, "Alderman", ward)
    if pending:
        records.append(pending)
    heads = [r for r in records if r["office"] == "Mayor"]
    seats = [r for r in records if r.get("district")]
    if len(heads) != 1 or len(seats) < MIN_WARD_SEATS["Le Roy"]:
        raise RuntimeError("Le Roy page parsed %d mayors / %d ward seats — "
                           "layout changed" % (len(heads), len(seats)))
    return records


def parse_lexington(council_lines, mayor_lines, warnings):
    """'Councilmen for Ward N are:' then 'Name:' / e-mail pairs (e-mails can
    wrap mid-domain); the mayor is on his own page."""
    records = []
    ward = None
    pending = None
    email_frag = None
    seen = set()
    for line in council_lines:
        wm = re.search(r"Councilmen for Ward\s+(\d+)", line, re.I)
        if wm:
            ward = "Ward %s" % wm.group(1)
            continue
        if ward is None:
            continue
        if email_frag is not None:
            candidate = email_frag + line.strip()
            email_frag = None
            if EMAIL_RE.fullmatch(candidate):
                if pending:
                    pending["person_email"] = candidate.lower()
                    if pending["name"] not in seen:
                        seen.add(pending["name"])
                        records.append(pending)
                    pending = None
                continue
        nm = re.match(r"^([A-Z][A-Za-z.'’-]+(?:\s+[A-Z][A-Za-z.'’-]+){1,3}):\s*$", line)
        if nm:
            if pending and pending["name"] not in seen:
                seen.add(pending["name"])
                records.append(pending)
            pending = person(nm.group(1), "Councilman", ward)
            continue
        em = EMAIL_RE.search(line)
        if em and pending:
            pending["person_email"] = em.group(1).lower()
            if pending["name"] not in seen:
                seen.add(pending["name"])
                records.append(pending)
            pending = None
            continue
        if pending and re.match(r"^\S+@\S*$", line.strip()):
            email_frag = line.strip()
        # The bio blocks below repeat each name without a colon; `seen`
        # keeps them from doubling the roster.
    if pending and pending["name"] not in seen:
        records.append(pending)

    mayor = None
    for i, line in enumerate(mayor_lines):
        if line == "Mayor" and i + 1 < len(mayor_lines) and \
                NAME_RE.match(mayor_lines[i + 1]) and mayor is None:
            block = mayor_lines[i + 1:i + 6]
            phone = next((l for l in block if PHONE_RE.search(l)), None)
            email = next((EMAIL_RE.search(l).group(1) for l in block
                          if EMAIL_RE.search(l)), None)
            # The nav also renders "Mayor" above its "City Council" link; the
            # real block is the one that carries the office phone/e-mail.
            if phone or email:
                mayor = person(block[0], "Mayor", phone=phone, email=email)
    if mayor:
        records.insert(0, mayor)
    heads = [r for r in records if r["office"] == "Mayor"]
    seats = [r for r in records if r.get("district")]
    if len(heads) != 1 or len(seats) < MIN_WARD_SEATS["Lexington"]:
        raise RuntimeError("Lexington pages parsed %d mayors / %d ward seats — "
                           "layout changed" % (len(heads), len(seats)))
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    warnings = []
    cities = []
    try:
        cities.append(("Bloomington", BLOOMINGTON_URL, "https://www.bloomingtonil.gov",
                       parse_bloomington(fetch_lines(BLOOMINGTON_URL), warnings)))
        cities.append(("Le Roy", LEROY_URL, "https://www.leroy.org",
                       parse_leroy(fetch_lines(LEROY_URL), warnings)))
        cities.append(("Lexington", LEXINGTON_COUNCIL_URL, "https://lexingtonil.gov",
                       parse_lexington(fetch_lines(LEXINGTON_COUNCIL_URL),
                                       fetch_lines(LEXINGTON_MAYOR_URL), warnings)))
    except Exception as exc:  # noqa: BLE001
        print("FATAL: %s" % exc, file=sys.stderr)
        sys.exit(1)

    for warning in sorted(set(warnings)):
        print("  warning: %s" % warning, file=sys.stderr)

    scraped_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    officials = []
    municipalities = []
    for name, source_url, website, records in cities:
        municipalities.append({"name": name, "source_url": source_url,
                               "scraped_at": scraped_at})
        for rec in records:
            rec.update({"jurisdiction": name, "website": website,
                        "source_url": source_url, "scraped_at": scraped_at})
            officials.append(rec)

    heads = sum(1 for p in officials if p["office"] == "Mayor")
    seats = sum(1 for p in officials if p.get("district"))
    payload = {
        "county": "McLean",
        # Per-city sourceUrls ride the records; no single county directory.
        "directory_url": None,
        "officials_page": "https://www.mcleancountyil.gov/731/Elected-Appointed-Officials",
        "scraped_at": scraped_at,
        "municipalities": municipalities,
        "officials": officials,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("scraped %d municipalities, %d officials (%d heads, %d ward seats) -> %s"
          % (len(municipalities), len(officials), heads, seats, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
