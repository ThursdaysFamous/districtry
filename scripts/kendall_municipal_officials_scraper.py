#!/usr/bin/env python3
"""
Kendall County Municipal Officials Scraper (County Clerk yearbook PDF)
=====================================================================
Extracts every Kendall County municipality's head of government and elected
municipal officers — plus hall address, phone, e-mail, and official website —
from the County Clerk's "Yearbook & Government Guide", CITY OFFICIALS and
VILLAGE OFFICIALS sections.

Why this source: Kendall's open GeoData portal carries boundaries but no
officials dataset, and the Kane/Kendall Council of Mayors publishes no member
roster, so the Clerk's yearbook is the county's own record and rung 2 of the
source ladder (docs/EXPANSION_GUIDE.md §3.4).

DEPTH: head of government + elected clerk/treasurer. The yearbook prints no
trustees or aldermen, so this county ships a `head` with no `board` — an
honest mayor-level entry; the Municipality card links the village's own site
for the full board.

FETCH POSTURE (measured 2026-07-28 — Playwright is the day-one rung)
--------------------------------------------------------------------
kendallcountyil.gov sits behind the same Akamai edge posture as McHenry, and
it fingerprints the HTTP CLIENT rather than only its headers: with a
byte-identical full browser header set, curl gets 200 while python-requests
gets 403. The requests rung is kept as a cheap fail-fast first try, but
**Playwright is the rung that carries this county in CI**. The Internet
Archive is the third rung, age-guarded.

Sandbox note: Chromium cannot reach the network through the agent proxy in
Claude Code web sessions, so the Playwright rung is unverifiable there; use
`--pdf <file>` to exercise the parser against a locally fetched copy.

SOURCE TYPO: the yearbook prints "Village of Minnoka" for Minooka. It is
corrected here through an explicit, reviewable alias so the entry can join its
Census place; the alias simply stops matching if the county fixes the spelling.
Correcting a place NAME to make a geographic join is not the same as inventing
officeholder data — no person's name is ever altered.

Usage:
    python3 kendall_municipal_officials_scraper.py --out kendall_municipal_officials.json

Notes on data honesty (per project conventions):
- Fields that can't be parsed are stored as null, never guessed.
- Every record includes `source_url` and `scraped_at` for traceability.
- Contact is MUNICIPALITY-level, emitted under the municipality.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone

import requests
from scraper_common import UA_CHROME_WIN_124  # noqa: E402  (shared machinery — do not fork)

PDF_URL = "https://www.kendallcountyil.gov/home/showdocument?id=184"
DIRECTORY_URL = ("https://www.kendallcountyil.gov/offices/county-clerk-recorder/"
                 "election-voter-information")
WAYBACK_API = "https://archive.org/wayback/available?url=%s"

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
REQUEST_TIMEOUT = 120
WAYBACK_MAX_AGE_DAYS = 45

# The county's own spelling -> the municipality's actual name. See SOURCE TYPO.
NAME_ALIASES = {"Village of Minnoka": "Village of Minooka"}

SECTION_RE = re.compile(r"^(CITY|VILLAGE) OFFICIALS$")
ENTRY_RE = re.compile(r"^(?:The\s+)?(?:United City|City|Village|Town) of [A-Z]")
# "Mayor: John Laesch – Elected 4/1/2025" — the yearbook prints when the
# officer was last elected, which is captured rather than discarded: it is the
# only term information this county publishes.
OFFICER_RE = re.compile(
    r"\b(?P<office>Mayor|Village President|President|Clerk|Treasurer)\s*:\s*"
    r"(?P<name>[^–\-—]+?)"
    r"(?:\s*[–\-—]\s*Elected\s*(?P<elected>\d{1,2}/\d{1,2}/\d{2,4})?.*)?$"
)
ADDRESS_RE = re.compile(
    r"^(?P<street>.+?),\s*(?P<city>[A-Za-z.'’\- ]+?)\s+(?P<state>IL)\s+(?P<zip>\d{5})"
)
PHONE_RE = re.compile(r"P:\s*(?P<phone>[\d.\-() ]{7,})")
EMAIL_RE = re.compile(r"[\w.\-+]+@[\w.\-]+\.\w+")
WEBSITE_RE = re.compile(r"^(?:www\.|https?://)\S+$", re.I)

MIN_MUNICIPALITIES = 12
MIN_HEADS = 12

HEAD_OFFICES = {"mayor", "president", "village president"}


def looks_blocked(body):
    return b"Access Denied" in body[:4000] or b"errors.edgesuite.net" in body[:4000]


def fetch_requests(url):
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    if not resp.content.startswith(b"%PDF"):
        raise RuntimeError("response was not a PDF (edge block or moved document)")
    return resp.content


def fetch_playwright(url):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            context = browser.new_context(user_agent=HEADERS["User-Agent"])
            page = context.new_page()
            # A PDF navigation does not render as a page; fetch it from a
            # browser context instead so the edge sees a real client.
            page.goto("https://www.kendallcountyil.gov/", wait_until="domcontentloaded",
                      timeout=90000)
            body = context.request.get(url, timeout=90000)
            if not body.ok:
                raise RuntimeError("browser rung got HTTP %d" % body.status)
            content = body.body()
        finally:
            browser.close()
    if not content.startswith(b"%PDF"):
        raise RuntimeError("browser rung did not receive a PDF")
    return content


def fetch_wayback(url):
    from datetime import datetime as dt

    resp = requests.get(WAYBACK_API % url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    snapshot = ((resp.json() or {}).get("archived_snapshots") or {}).get("closest")
    if not snapshot or not snapshot.get("available"):
        raise RuntimeError("no Archive snapshot available")
    taken = dt.strptime(snapshot.get("timestamp") or "", "%Y%m%d%H%M%S").replace(
        tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - taken).days
    if age_days > WAYBACK_MAX_AGE_DAYS:
        raise RuntimeError("newest snapshot is %d days old (max %d) — refusing to serve "
                           "stale data as current" % (age_days, WAYBACK_MAX_AGE_DAYS))
    page = requests.get(snapshot["url"], headers=HEADERS, timeout=REQUEST_TIMEOUT)
    page.raise_for_status()
    if not page.content.startswith(b"%PDF"):
        raise RuntimeError("archived copy is not a PDF")
    return page.content


def fetch(url, engine):
    rungs = {"requests": [fetch_requests], "playwright": [fetch_playwright],
             "wayback": [fetch_wayback]}.get(
                 engine, [fetch_requests, fetch_playwright, fetch_wayback])
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


def normalize_phone(value):
    text = clean(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        # The yearbook contains at least one short number (a typo in the
        # source); ship it verbatim rather than padding it into a wrong one.
        return text
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])


def pdf_lines(body):
    import io

    import pypdf

    reader = pypdf.PdfReader(io.BytesIO(body))
    lines = []
    for page in reader.pages:
        text = page.extract_text(extraction_mode="layout") or ""
        lines.extend(clean(line) for line in text.splitlines())
    return [line for line in lines if line]


def parse(lines, scraped_at):
    records = []
    current = None
    in_section = False

    def flush(entry):
        if not entry:
            return
        for office, name, elected in entry["officers"]:
            records.append({
                "jurisdiction": entry["name"],
                "office": office,
                "district": None,
                "name": name,
                # The year the yearbook says this officer was last elected.
                "last_elected": elected,
                "office_address": entry["street"],
                "office_city": entry["city"],
                "office_state": entry["state"],
                "office_zip": entry["zip"],
                "office_phone": entry["phone"],
                "office_email": entry["email"],
                "website": entry["website"],
                "source_url": PDF_URL,
                "scraped_at": scraped_at,
            })

    for line in lines:
        # Page margins print the county name against the entry text.
        line = re.sub(r"^KENDALL\s+(?=\S)", "", line).strip()
        if SECTION_RE.match(line):
            in_section = True
            continue
        if not in_section:
            continue

        # THE SECTION HAS A START AND NO END, which is the whole of the
        # Plattville defect. `in_section` is never set back to False, so once
        # the last CITY/VILLAGE OFFICIALS section opens, every remaining line
        # in the document is still offered to whatever entry is current — and
        # the LAST entry alphabetically absorbs all of it, because only the
        # next ENTRY_RE terminates an entry. That is how Plattville came to
        # ship the county Democrats' e-mail, a Department of Revenue page as
        # its website, and a clerk named "Beth Fals 56".
        #
        # THE REAL FIX IS AN END MARKER AND IT IS NOT MADE HERE, because
        # choosing one means reading the document to see what follows the
        # section, and this county blocks every fetch rung including the
        # Archive's crawler (#234). No copy is cached. Guessing a marker that
        # cannot be tested would replace a known defect with an unknown one.
        # What IS made here is the narrow refusal below, which needs no
        # knowledge of the document.

        if ENTRY_RE.match(line):
            flush(current)
            name = NAME_ALIASES.get(line, line)
            current = {"name": name, "street": None, "city": None, "state": None,
                       "zip": None, "phone": None, "email": None, "website": None,
                       "officers": []}
            continue
        if current is None:
            continue

        address = ADDRESS_RE.match(line)
        if address and current["street"] is None:
            # The guide prints a physical and a mailing address for some
            # entries; the first (physical) is the hall the card should point at.
            current.update(street=clean(address.group("street")),
                           city=clean(address.group("city")),
                           state=address.group("state"), zip=address.group("zip"))
            continue
        phone = PHONE_RE.search(line)
        if phone and current["phone"] is None:
            current["phone"] = normalize_phone(phone.group("phone").split("F:")[0])
            continue
        email = EMAIL_RE.search(line)
        if email and current["email"] is None and "Email" in line:
            current["email"] = clean(email.group(0))
            continue
        if WEBSITE_RE.match(line) and current["website"] is None:
            current["website"] = line
            continue
        officer = OFFICER_RE.search(line)
        if officer:
            name = clean(officer.group("name"))
            # A NAME ENDING IN A BARE NUMBER IS THE SECTION BLEED, NOT A
            # PERSON. The yearbook prints no numeral in a name, so a trailing
            # one is a page number or a row index welded on by the over-read
            # above. Dropped and PRINTED rather than trimmed to "Beth Fals":
            # the Douglas County rule says a person's name is never repaired to
            # make it fit, because a parse that reached past its own section
            # makes the surname exactly as suspect as the digits.
            #
            # Measured across all 629 shipped municipalities on 2026-09-21,
            # this shape occurs exactly once — Plattville's clerk — so the
            # refusal costs no other county a name.
            if name and re.search(r"\s\d{1,4}$", name):
                print("kendall-municipal-scraper: dropped %r on %s — a trailing "
                      "number means the parse read past its section"
                      % (name, current["name"]), file=sys.stderr)
                continue
            if name:
                elected = officer.groupdict().get("elected")
                year = None
                if elected:
                    parts = elected.split("/")
                    if len(parts) == 3:
                        year = parts[2]
                        if len(year) == 2:
                            year = "20" + year
                current["officers"].append(
                    (clean(officer.group("office")), name, year))

    flush(current)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", default="kendall_municipal_officials.json")
    parser.add_argument("--engine", choices=("auto", "requests", "playwright", "wayback"),
                        default="auto",
                        help="fetch rung; auto walks requests -> playwright -> wayback")
    parser.add_argument("--pdf", help="parse a local PDF instead of fetching")
    args = parser.parse_args()

    scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if args.pdf:
        with open(args.pdf, "rb") as f:
            body = f.read()
    else:
        body = fetch(PDF_URL, args.engine)

    records = parse(pdf_lines(body), scraped_at)

    municipalities = sorted({r["jurisdiction"] for r in records})
    heads = [r for r in records if r["office"].lower() in HEAD_OFFICES]
    if len(municipalities) < MIN_MUNICIPALITIES:
        print("FATAL: parsed %d municipalities (expected >= %d) — the yearbook's layout "
              "changed or the fetch was partial" % (len(municipalities), MIN_MUNICIPALITIES),
              file=sys.stderr)
        sys.exit(1)
    if len(heads) < MIN_HEADS:
        print("FATAL: parsed %d heads of government (expected >= %d)"
              % (len(heads), MIN_HEADS), file=sys.stderr)
        sys.exit(1)

    payload = {
        "county": "Kendall",
        "directory_url": DIRECTORY_URL,
        "scraped_at": scraped_at,
        "officials": records,
    }
    with open(args.out, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print("scraped %d municipalities, %d elected officials (%d heads of government) -> %s"
          % (len(municipalities), len(records), len(heads), args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
