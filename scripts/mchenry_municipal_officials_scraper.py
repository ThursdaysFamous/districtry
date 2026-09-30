#!/usr/bin/env python3
"""
McHenry County Municipal Officials Scraper (County Clerk yearbook)
==================================================================
Extracts every McHenry County municipality's head of government and elected
municipal officers — plus hall address, phone, e-mail, and official website —
from the County Clerk's annual County Yearbook, "Cities & Villages" page.

Why this source: McHenry's county GIS carries municipal boundaries with no
officials data, and no council of governments publishes a member roster, so
the Clerk's yearbook is the county's own record and rung 2 of the source
ladder (docs/EXPANSION_GUIDE.md §3.4).

DEPTH: head of government + elected clerk/treasurer. The yearbook prints no
trustees or aldermen, so this county ships a `head` with no `board` — an
honest mayor-level entry. The Municipality card links the village's own site
for the full board.

Appointed staff are EXCLUDED, not misfiled: the yearbook lists village
administrators, city managers, directors of administration, and deputy clerks
alongside the elected officers, but the card's officers section is titled
"Other Elected Officials", so shipping an appointee there would mislabel them.
Only the offices in HEAD_OFFICES / ELECTED_OFFICER_OFFICES ship.

FETCH POSTURE (measured 2026-07-28 — Playwright is the day-one rung)
--------------------------------------------------------------------
mchenrycountyil.gov sits behind an Akamai edge that fingerprints the HTTP
CLIENT, not just its headers. Measured against this page with a byte-identical
full browser header set (Accept, Accept-Language, Accept-Encoding incl. br,
sec-ch-ua / Sec-Fetch-* client hints, Upgrade-Insecure-Requests):

    curl      -> 200
    requests  -> 403

So the header set is necessary but not sufficient: python-requests' TLS/HTTP
fingerprint is refused whatever it sends. The requests rung is kept as a cheap
first try that fails fast (the edge may relax, and a WARN-free run is worth the
one request), but **Playwright is the rung that carries this county in CI**,
which is why the workflow installs Chromium for it.

The Internet Archive is the third rung and is genuinely available again for
this path — snapshots exist from 2025-03-06 onward, contrary to the older
"blocks even the Archive's crawler" note, which was recorded for the
county-board path and still stands there.

Sandbox note: Chromium cannot reach the network through the agent proxy in
Claude Code web sessions, so the Playwright rung is unverifiable there; use
`--html <file>` to exercise the parser against a locally fetched copy.

Usage:
    python3 mchenry_municipal_officials_scraper.py --out mchenry_municipal_officials.json
    python3 mchenry_municipal_officials_scraper.py --engine wayback   # forced rung

Notes on data honesty (per project conventions):
- Fields that can't be parsed are stored as null, never guessed.
- Every record includes `source_url` and `scraped_at` for traceability.
- Hall contact is MUNICIPALITY-level. Where the yearbook additionally prints a
  PER-PERSON phone or e-mail (a handful of officials do), it is carried on that
  person and never spread to the others.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone

import requests
from scraper_common import (  # noqa: E402  (shared machinery — do not fork)
    UA_CHROME_WIN_124,
    require_robots_allowed,
    robots_deferred,
)

PAGE_URL = "https://www.mchenrycountyil.gov/county-government/county-yearbook/cities-villages"
WAYBACK_API = "https://archive.org/wayback/available?url=%s"

# The complete fingerprint — see FETCH POSTURE above. Dropping any of these
# headers brings back the Akamai "Access Denied" interstitial.
HEADERS = {
    "User-Agent": UA_CHROME_WIN_124,
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Connection": "keep-alive",
}
REQUEST_TIMEOUT = 90
# A snapshot older than this is refused rather than served as current — the
# same guard the county-board scrapers use.
WAYBACK_MAX_AGE_DAYS = 45

BLOCK_MARKERS = ("Access Denied", "You don't have permission to access",
                 "errors.edgesuite.net", "Request unsuccessful")

# Elected offices only. Villages elect a President, cities a Mayor; clerk and
# treasurer are elected municipal offices in Illinois villages and cities
# (65 ILCS 5/3.1-25-5 et seq.) and the app already ships them as "Other Elected
# Officials" for Cook and Will.
HEAD_OFFICES = {"president", "village president", "mayor"}
ELECTED_OFFICER_OFFICES = {"clerk", "village clerk", "city clerk", "treasurer",
                           "village treasurer", "city treasurer"}

MIN_MUNICIPALITIES = 26
MIN_HEADS = 24

PHONE_RE = re.compile(r"\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}")
EMAIL_RE = re.compile(r"[\w.\-+]+@[\w.\-]+\.\w+")
LABELLED_WORK_PHONE_RE = re.compile(r"\bW:\s*(\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4})")


def looks_blocked(html):
    return any(marker in html for marker in BLOCK_MARKERS)


def fetch_requests(url):
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    if looks_blocked(resp.text):
        raise RuntimeError("edge returned a block interstitial")
    return resp.text


def fetch_playwright(url):
    """Escalation rung: a real browser, no evasion beyond being a real browser."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(user_agent=HEADERS["User-Agent"])
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
            html = page.content()
        finally:
            browser.close()
    if looks_blocked(html):
        raise RuntimeError("edge returned a block interstitial to the browser rung")
    return html


def fetch_wayback(url):
    """Last rung: the Internet Archive's most recent snapshot, age-guarded."""
    from datetime import datetime as dt

    resp = requests.get(WAYBACK_API % url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    snapshot = ((resp.json() or {}).get("archived_snapshots") or {}).get("closest")
    if not snapshot or not snapshot.get("available"):
        raise RuntimeError("no Archive snapshot available")
    stamp = snapshot.get("timestamp") or ""
    taken = dt.strptime(stamp, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - taken).days
    if age_days > WAYBACK_MAX_AGE_DAYS:
        raise RuntimeError("newest snapshot is %d days old (max %d) — refusing to serve "
                           "stale data as current" % (age_days, WAYBACK_MAX_AGE_DAYS))
    require_robots(snapshot["url"])
    page = requests.get(snapshot["url"], headers=HEADERS, timeout=REQUEST_TIMEOUT)
    page.raise_for_status()
    return page.text


# --- robots.txt, read once per host with the client this file crawls with ------
# CLAUDE.md's rule is that robots.txt is read before the first fetch of a host,
# and measured 2026-09-12 almost no scraper here enacted it. This file does now.
# Every rung below sends HEADERS' User-Agent, so one reading answers for all of
# them and there is no client to escalate to. Cached per host so a run that
# fetches several pages from one site asks once, which is also what keeps the
# extra request count at one per host per run.
#
# Measured 2026-09-30, four reads per client: www.mchenrycountyil.gov serves a
# 6,641-byte policy to this client, whose HEADERS carry the Sec-CH-UA hints its
# edge wants; a client without them is refused its own robots.txt with 403 four
# times of four, which under RFC 9309 2.3.1.3 permits anyway. No rule in its one
# binding group matches the pages read here, and it states no Crawl-delay and no
# Content-Signal. THAT POLICY IS THE CMS VENDOR'S DEFAULT, byte-identical by md5
# to the one www.kendallcountyil.gov and www.joliet.gov serve.
_ROBOTS_ASKED = {}


def require_robots(url):
    from urllib.parse import urlsplit

    host = urlsplit(url).hostname or ""
    if host in _ROBOTS_ASKED:
        return
    deferred = robots_deferred(url)
    if deferred:
        # A recorded gap, never a permission: scraper_common carries the
        # measurement and the reason, and printing it puts the deferral in the
        # log of every run rather than leaving it silent.
        print("robots.txt NOT read for %s — %s" % (host, deferred), file=sys.stderr)
        _ROBOTS_ASKED[host] = None
        return
    why = require_robots_allowed(url, HEADERS["User-Agent"], headers=HEADERS,
                                 label='mchenry-municipal-officials-scraper')
    print("robots.txt %s: %s" % (host, why), file=sys.stderr)
    _ROBOTS_ASKED[host] = why


def fetch(url, engine):
    rungs = {"requests": [fetch_requests], "playwright": [fetch_playwright],
             "wayback": [fetch_wayback]}.get(
                 engine, [fetch_requests, fetch_playwright, fetch_wayback])
    require_robots(url)
    last = None
    for rung in rungs:
        try:
            return rung(url)
        except Exception as exc:  # noqa: BLE001 - every rung failure escalates
            last = exc
            print("%s rung failed (%s)" % (rung.__name__, exc), file=sys.stderr)
    print("FATAL: every fetch rung failed for %s — last error: %s" % (url, last),
          file=sys.stderr)
    sys.exit(1)


def clean(value):
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def row_cells(row):
    return [clean(cell.get_text(" ", strip=True)) or "" for cell in row.find_all("td")]


def parse_address(text):
    """"2200 Harnish Dr., Algonquin, IL 60102" -> (street, city, state, zip)."""
    match = re.match(r"^(?P<street>.+),\s*(?P<city>[^,]+),\s*(?P<state>[A-Z]{2})\s*"
                     r"(?P<zip>\d{5})$", text or "")
    if not match:
        return (clean(text), None, None, None)
    return (clean(match.group("street")), clean(match.group("city")),
            match.group("state"), match.group("zip"))


def person_contact(cells):
    """Per-person phone/e-mail from the row's trailing cell, when present."""
    extra = " ".join(cells[2:]).strip()
    if not extra:
        return (None, None)
    email = EMAIL_RE.search(extra)
    phone = None
    labelled = LABELLED_WORK_PHONE_RE.search(extra)
    found = PHONE_RE.findall(extra)
    if labelled:
        # "W: 815-385-6023 C: 815-482-8605" — the work line is the office
        # contact; the cell number is not published as a public office line.
        phone = labelled.group(1)
    elif len(found) == 1:
        phone = found[0]
    return (clean(phone), clean(email.group(0) if email else None))


def normalize_phone(value):
    text = clean(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return text
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])


def parse(html, scraped_at):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    records = []
    skipped_appointed = 0
    current = None

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row_cells(row)
            if not any(cells):
                continue
            first = cells[0]

            # A single all-caps cell starts a municipality ("VILLAGE OF CARY").
            if len(cells) == 1 or all(not c for c in cells[1:]):
                if re.match(r"^(?:THE\s+)?(?:UNITED\s+)?(?:VILLAGE|CITY|TOWN)\s+OF\s+\S",
                            first, flags=re.I):
                    current = {
                        "jurisdiction": first.title().replace(" Of ", " of "),
                        "address": None, "city": None, "state": None, "zip": None,
                        "phone": None, "email": None, "website": None,
                    }
                    continue
                if current and current["address"] is None and re.search(r"\d{5}$", first):
                    street, city, state, zipcode = parse_address(first)
                    current.update(address=street, city=city, state=state, zip=zipcode)
                    continue

            if current is None:
                continue

            joined = " ".join(c for c in cells if c)
            if joined.startswith("Phone:") or joined.startswith("Fax:") \
                    or joined.startswith("Email:"):
                phone = re.search(r"Phone:\s*(" + PHONE_RE.pattern + ")", joined)
                if phone and not current["phone"]:
                    current["phone"] = normalize_phone(phone.group(1))
                email = re.search(r"Email:\s*(" + EMAIL_RE.pattern + ")", joined)
                if email and not current["email"]:
                    current["email"] = clean(email.group(1))
                continue
            if joined.startswith("Website:"):
                if not current["website"]:
                    current["website"] = clean(joined.split(":", 1)[1]) or None
                continue

            # Otherwise: an office/name pair.
            office = first
            name = cells[1] if len(cells) > 1 else ""
            if not office or not name:
                continue
            key = office.lower().strip()
            if key not in HEAD_OFFICES and key not in ELECTED_OFFICER_OFFICES:
                skipped_appointed += 1
                continue
            person_phone, person_email = person_contact(cells)
            person_phone = normalize_phone(person_phone)
            # A "personal" number that is just the village hall's main line is
            # not a direct line; carrying it on the person would imply one.
            if person_phone and person_phone == current["phone"]:
                person_phone = None
            if person_email and person_email == current["email"]:
                person_email = None
            records.append({
                "jurisdiction": current["jurisdiction"],
                "office": office,
                "district": None,
                "name": name,
                "person_phone": person_phone,
                "person_email": person_email,
                "office_address": current["address"],
                "office_city": current["city"],
                "office_state": current["state"],
                "office_zip": current["zip"],
                "office_phone": current["phone"],
                "office_email": current["email"],
                "website": current["website"],
                "source_url": PAGE_URL,
                "scraped_at": scraped_at,
            })
    return records, skipped_appointed


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", default="mchenry_municipal_officials.json")
    parser.add_argument("--engine", choices=("auto", "requests", "playwright", "wayback"),
                        default="auto",
                        help="fetch rung; auto walks requests -> playwright -> wayback")
    parser.add_argument("--html", help="parse a local HTML file instead of fetching")
    args = parser.parse_args()

    scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if args.html:
        with open(args.html, encoding="utf-8", errors="replace") as f:
            html = f.read()
    else:
        html = fetch(PAGE_URL, args.engine)

    records, skipped = parse(html, scraped_at)

    municipalities = sorted({r["jurisdiction"] for r in records})
    heads = [r for r in records if r["office"].lower().strip() in HEAD_OFFICES]
    if len(municipalities) < MIN_MUNICIPALITIES:
        print("FATAL: parsed %d municipalities (expected >= %d) — page structure changed "
              "or the fetch was partial" % (len(municipalities), MIN_MUNICIPALITIES),
              file=sys.stderr)
        sys.exit(1)
    if len(heads) < MIN_HEADS:
        print("FATAL: parsed %d heads of government (expected >= %d)"
              % (len(heads), MIN_HEADS), file=sys.stderr)
        sys.exit(1)

    payload = {
        "county": "McHenry",
        "directory_url": PAGE_URL,
        "scraped_at": scraped_at,
        "officials": records,
    }
    with open(args.out, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print("scraped %d municipalities, %d elected officials (%d heads of government; "
          "%d appointed staff rows skipped) -> %s"
          % (len(municipalities), len(records), len(heads), skipped, args.out),
          file=sys.stderr)


if __name__ == "__main__":
    main()
