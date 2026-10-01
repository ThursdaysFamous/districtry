#!/usr/bin/env python3
"""
Will County ward-city council scraper (the cities' own sites)
============================================================
Adds what the Will County Clerk's directory does not publish — PER-SEAT
council contact — and recovers the two ward cities the directory drops, by
reading each city's own official site.

WHY A PER-CITY SOURCE HERE, DELIBERATELY
----------------------------------------
The source ladder (docs/EXPANSION_GUIDE.md §3.4) puts individual municipal
sites below the link-only floor precisely so nobody scrapes 30+ heterogeneous
sites by default. This is the deliberate, bounded exception it allows, taken
for one reason: these are the cities whose seats the `ward` layer answers, so
the Municipality card now sends readers to a per-seat card — and that card
should be able to name a way to reach that seat's holder.

Scope is the four Will ward/district cities, not the county:
  Crest Hill  — per-alderperson phone (roster already comes from the Clerk)
  Lockport    — FULL roster; the Clerk's directory omits this city entirely
  Wilmington  — FULL roster + per-alderperson e-mail; also omitted by the Clerk
  Joliet      — NOT BUILT, see below

CREST HILL'S PHONES MOVED ON 2026-08-12, and the move nearly shipped as a
deletion. The city rethemed its CivicPlus site: the Elected Officials page
stopped linking the /directory.aspx?eid=N entries this scraper walked, the
per-person pages moved to /m/directory/employee?eid=N and LOST their phone
lines — and the numbers now appear only on the staff-directory INDEX, one
<li> per person with name, title and a tel: link. The old parser followed
the (now absent) links, found nobody, and the weekly refresh opened a PR
silently dropping all eight published numbers — caught in review (#338), not
by any guard, because the seat floor skipped a city with ZERO records and no
floor counted phones at all. Hence the shape below: the index is the primary
source, the old entry walk survives as a fallback in case the theme reverts,
and a run that cannot produce MIN_CREST_HILL_PHONES phone-bearing officials
FAILS — a failed run is preserved by the workflow (the shipped contact
carries forward), which is the honest degradation; an empty success is not.

Lockport and Wilmington are missing from `municipal-officials.json` because the
Clerk's flipbook directory omits their entry HEADERS from its text layer
(Wilmington's alderpersons appear orphaned after Naperville's entry; Lockport's
block is absent). That is a source-side defect no parser can recover, so their
own sites are the only route — and without it both cities resolve a ward
polygon with no seat-holder joined.

JOLIET IS DELIBERATELY NOT BUILT. joliet.gov returns 403 to non-browser
clients, jolietcity.org renders its council entirely client-side (zero text
without a browser), and the only Internet Archive snapshot is from March 2022 —
four years stale and past any age guard, listing a council two elections out of
date. Writing a parser against a page whose structure cannot be inspected, for
data that would need a browser rung to fetch, is how silent breakage ships.
Joliet's members are already in the roster from the Clerk's directory; only
their per-seat contact is missing, and that gap is recorded in the guidebook.

THE CLERK REMAINS THE ROSTER OF RECORD. For a municipality the county already
covers, this scraper contributes CONTACT ONLY — the builder matches each person
by name and fills a missing phone/e-mail, never adding, renaming, or re-roling a
seat-holder. Where the county publishes nobody (Lockport, Wilmington), the city
site supplies the entry outright.

Deliberately NOT taken from these pages: term years. Crest Hill's directory
entries carry visibly stale terms ("2021-2025" for a sitting alderwoman the
Clerk lists through 2027), and the Clerk's certified election data is the better
source. Contact is what these pages add.

Usage:
    python3 will_city_councils_scraper.py --out will_city_councils.json

Notes on data honesty (per project conventions):
- Fields that can't be parsed are stored as null, never guessed.
- Every record includes `source_url` and `scraped_at` for traceability.
- A per-person phone/e-mail equal to the city's own main line is dropped, so a
  row can't imply a direct line the city doesn't publish.
"""

import argparse
import html as html_mod
import json
import re
import sys
from datetime import datetime, timezone

import requests
from scraper_common import require_robots_once, UA_ROSTER_BOT, fetch as fetch_with_retry  # noqa: E402  (shared machinery — do not fork)

HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
}
REQUEST_TIMEOUT = 60

CREST_HILL_OFFICIALS = "https://www.cityofcresthill.com/201/Elected-Officials"
CREST_HILL_DIRECTORY = "https://www.cityofcresthill.com/directory.aspx?eid=%s"
CREST_HILL_DIRECTORY_INDEX = "https://www.cityofcresthill.com/directory.aspx"
# The city's main line. A directory row carrying it means "reach them via the
# hall", not a direct line, and the hall number already rides the hall fields.
CREST_HILL_HALL_PHONE = "815-741-5100"
LOCKPORT_OFFICIALS = "https://www.cityoflockport.net/153/Meet-the-Elected-Officials"
WILMINGTON_OFFICIALS = "https://www.wilmington-il.com/city-officials"

# Ordinals as these sites write them -> the seat label the roster/ward layer use.
ORDINAL_WARDS = {"1st": "Ward 1", "2nd": "Ward 2", "3rd": "Ward 3", "4th": "Ward 4",
                 "5th": "Ward 5", "6th": "Ward 6", "7th": "Ward 7", "8th": "Ward 8"}

EMAIL_RE = re.compile(r"[\w.\-+]+@[\w.\-]+\.\w{2,}")
PHONE_RE = re.compile(r"\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}")

# Floors: each city's published seat count. A shrink means the page changed.
MIN_SEATS = {"City of Crest Hill": 6, "City of Lockport": 8, "City of Wilmington": 8}
# Crest Hill contributes CONTACT only, so its floor must count records that
# CARRY contact: nine of the eleven elected publish a number today (eight
# direct lines + the Clerk's hall line, which the dedupe nulls), and six
# phoneless records would satisfy MIN_SEATS while shipping the same deletion
# the 2026-08-12 retheme nearly did.
MIN_CREST_HILL_PHONES = 6


def fetch(url):
    # scraper_common.fetch retries 429/5xx (numeric Retry-After honoured,
    # capped) and refuses to retry 401/403/404 — the Henry rule. Parsing and
    # every page check stay in this file.
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-will-city-councils-scraper")
    return fetch_with_retry(url, HEADERS, timeout=REQUEST_TIMEOUT).text


def text_lines(html_text):
    """Tag-stripped, whitespace-collapsed lines — these are plain CMS pages."""
    body = re.sub(r"(?is)<(script|style|nav|footer)\b.*?</\1>", " ", html_text)
    out = []
    for line in re.sub(r"(?s)<[^>]+>", "\n", body).splitlines():
        line = " ".join(line.replace("\xa0", " ").split())
        if line:
            out.append(line)
    return out


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
        return text
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])


def ward_label(text):
    match = re.search(r"\b(1st|2nd|3rd|4th|5th|6th|7th|8th)\b", text or "", re.I)
    if match:
        return ORDINAL_WARDS.get(match.group(1).lower())
    match = re.search(r"\bWard\s+(\d+)\b", text or "", re.I)
    return "Ward %s" % match.group(1) if match else None


def record(jurisdiction, office, name, source_url, scraped_at, district=None,
           person_phone=None, person_email=None, **office_fields):
    rec = {
        "jurisdiction": jurisdiction,
        "office": office,
        "district": district,
        "name": name,
        "person_phone": person_phone,
        "person_email": person_email,
        "source_url": source_url,
        "scraped_at": scraped_at,
    }
    rec.update(office_fields)
    return rec


def _crest_hill_office(title):
    """The elected offices only — the index lists department staff too, and
    a loose 'clerk' match would sweep in the Deputy City Clerk and three
    Administrative Clerks."""
    text = " ".join((title or "").split())
    if re.fullmatch(r"Mayor", text, re.I):
        return "Mayor"
    if re.search(r"\balder(?:man|woman|person)\b", text, re.I):
        return "Alderperson"
    if re.fullmatch(r"City Clerk", text, re.I):
        return "Clerk"
    if re.fullmatch(r"City Treasurer", text, re.I):
        return "Treasurer"
    return None


def scrape_crest_hill(scraped_at):
    """Per-person phone from the staff-directory INDEX (see the module header:
    the 2026-08 retheme removed the phones from the per-person pages)."""
    records = _crest_hill_from_index(scraped_at)
    with_phone = [r for r in records if r.get("person_phone")]
    if len(with_phone) < MIN_CREST_HILL_PHONES:
        # The theme may have reverted; the old entry walk knows that shape.
        legacy = _crest_hill_legacy(scraped_at)
        legacy_with_phone = [r for r in legacy if r.get("person_phone")]
        if len(legacy_with_phone) > len(with_phone):
            records, with_phone = legacy, legacy_with_phone
    if len(with_phone) < MIN_CREST_HILL_PHONES:
        raise RuntimeError(
            "Crest Hill parsed %d phone-bearing officials (floor %d) — the city "
            "restructured its directory again; failing so the workflow preserves "
            "the shipped contact instead of shipping a deletion"
            % (len(with_phone), MIN_CREST_HILL_PHONES))
    return records


def _crest_hill_from_index(scraped_at):
    """One <li class="list-group-item"> per person: bold name link, a title
    div rendered twice (desktop + mobile), and a tel: link when the city
    publishes a number for them."""
    raw = fetch(CREST_HILL_DIRECTORY_INDEX)
    records = []
    for chunk in re.split(r'<li class="list-group-item', raw)[1:]:
        name_m = re.search(r'class="fw-bold no-underline-link"[^>]*>\s*([^<]+?)\s*</a>', chunk)
        title_m = re.search(r'<div class="d-sm-block d-none">\s*([^<]+?)\s*</div>', chunk)
        if not name_m or not title_m:
            continue
        name = clean(html_mod.unescape(name_m.group(1)))
        title = clean(html_mod.unescape(title_m.group(1)))
        office = _crest_hill_office(title)
        if not office or not name:
            continue
        tel_m = re.search(r'href="tel:([^"]+)"', chunk)
        phone = normalize_phone(tel_m.group(1)) if tel_m else None
        if phone == CREST_HILL_HALL_PHONE:
            phone = None
        records.append(record("City of Crest Hill", office, name,
                              CREST_HILL_DIRECTORY_INDEX, scraped_at,
                              district=ward_label(title), person_phone=phone))
    return records


def _crest_hill_legacy(scraped_at):
    """The pre-2026-08 shape: the Elected Officials page links each person's
    /directory.aspx?eid=N entry, and the entry carries the phone."""
    html_text = fetch(CREST_HILL_OFFICIALS)
    # The index links each person's staff-directory entry; the entry itself
    # carries the authoritative name, title, and phone, so the link ids are all
    # this page is needed for (its own name/label order varies by tile).
    eids = []
    for eid in re.findall(r'/directory\.aspx\?eid=(\d+)', html_text, re.I):
        if eid not in eids:
            eids.append(eid)

    records = []
    for eid in eids:
        detail = fetch(CREST_HILL_DIRECTORY % eid)
        lines = text_lines(detail)
        # "<title>Staff Directory • Claudia Gazal</title>"
        heading = re.search(r"<title>\s*Staff Directory\s*[•·|-]\s*([^<]+)</title>",
                            detail, re.I)
        name = clean(heading.group(1)) if heading else None
        if not name:
            continue
        title = None
        phone = None
        for i, line in enumerate(lines):
            if re.match(r"^Title:", line, re.I):
                title = clean(re.sub(r"^Title:\s*", "", line, flags=re.I))
            if re.match(r"^Phone:?$", line, re.I) and i + 1 < len(lines):
                phone = normalize_phone(lines[i + 1])
            elif re.match(r"^Phone:", line, re.I):
                found = PHONE_RE.search(line)
                if found:
                    phone = normalize_phone(found.group(0))
        if not title or not phone:
            continue
        # Only council seats and the head/officers — skip department staff.
        district = ward_label(title)
        if re.search(r"alder", title, re.I):
            office = "Alderperson"
        elif re.search(r"^mayor", title, re.I):
            office = "Mayor"
        elif re.search(r"clerk", title, re.I):
            office = "Clerk"
        elif re.search(r"treasurer", title, re.I):
            office = "Treasurer"
        else:
            continue
        records.append(record("City of Crest Hill", office, name,
                              CREST_HILL_DIRECTORY % eid, scraped_at,
                              district=district, person_phone=phone))
    return records


def scrape_lockport(scraped_at):
    """Full roster: the Clerk's directory omits this city entirely."""
    lines = text_lines(fetch(LOCKPORT_OFFICIALS))
    hall = {
        "office_address": "222 East 9th Street",
        "office_city": "Lockport",
        "office_state": "IL",
        "office_zip": "60441",
        "office_phone": "815-838-0549",
        "website": "https://www.cityoflockport.net",
    }
    records = []
    for i, line in enumerate(lines):
        # "Steven Streit" then ", Mayor, Four-Year Term, 2025-2029"
        if not re.match(r"^[A-Z][A-Za-z.'’\-]+(?:\s+[A-Z][A-Za-z.'’\-]+){0,3}$", line):
            continue
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if not nxt.startswith(","):
            continue
        name = clean(line)
        role_text = nxt.lstrip(",").strip()
        district = ward_label(role_text)
        if district:
            office = "Alderperson"
        elif re.match(r"mayor", role_text, re.I):
            office = "Mayor"
        elif re.match(r"city clerk|clerk", role_text, re.I):
            office = "Clerk"
        elif re.match(r"treasurer", role_text, re.I):
            office = "Treasurer"
        else:
            continue
        records.append(record("City of Lockport", office, name, LOCKPORT_OFFICIALS,
                              scraped_at, district=district, **hall))
    return records


def scrape_wilmington(scraped_at):
    """Full roster + per-alderperson e-mail; also omitted by the Clerk."""
    lines = text_lines(fetch(WILMINGTON_OFFICIALS))
    hall = {
        "office_address": "1165 S. Water Street",
        "office_city": "Wilmington",
        "office_state": "IL",
        "office_zip": "60481",
        "office_phone": "815-476-2175",
        "website": "https://www.wilmington-il.com",
    }
    records = []
    current = None
    for line in lines:
        head = re.match(r"^Mayor\s+([A-Z][A-Za-z.'’\- ]+)$", line)
        alder = re.match(r"^Alder\s*person\s+(.+)$", line, re.I)
        if head:
            current = {"office": "Mayor", "name": clean(head.group(1).title()
                                                        if head.group(1).isupper()
                                                        else head.group(1)),
                       "district": None, "phone": None, "email": None}
            records.append(current)
            continue
        if alder:
            raw = clean(alder.group(1))
            name = raw.title() if raw and raw.isupper() else raw
            current = {"office": "Alderperson", "name": name, "district": None,
                       "phone": None, "email": None}
            records.append(current)
            continue
        if current is None:
            continue
        if current["district"] is None:
            ward = ward_label(line)
            if ward:
                current["district"] = ward
        found_email = EMAIL_RE.search(line)
        # The page carries a legacy .com block alongside the current .gov
        # addresses; take only the address that stands alone on its own line.
        if found_email and current["email"] is None and found_email.group(0) == line:
            current["email"] = found_email.group(0).lower()
        # A phone standing alone on its line belongs to the person above it;
        # allow the long-distance "1-" the mayor's listing carries.
        bare = re.sub(r"^1[\s.\-]", "", line).strip()
        found_phone = PHONE_RE.search(bare)
        if found_phone and current["phone"] is None and found_phone.group(0) == bare:
            current["phone"] = normalize_phone(found_phone.group(0))

    out = []
    for person in records:
        if not person["name"]:
            continue
        phone = person["phone"]
        if phone and phone == hall["office_phone"]:
            phone = None
        out.append(record("City of Wilmington", person["office"], person["name"],
                          WILMINGTON_OFFICIALS, scraped_at,
                          district=person["district"], person_phone=phone,
                          person_email=person["email"], **hall))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", default="will_city_councils.json")
    args = parser.parse_args()

    scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    records = []
    failures = []
    for label, scrape in (("Crest Hill", scrape_crest_hill),
                          ("Lockport", scrape_lockport),
                          ("Wilmington", scrape_wilmington)):
        try:
            records.extend(scrape(scraped_at))
        except Exception as exc:  # noqa: BLE001 - one city's site must not sink the rest
            failures.append("%s (%s)" % (label, exc))
            print("WARNING: %s scrape failed: %s" % (label, exc), file=sys.stderr)

    counts = {}
    for rec in records:
        counts[rec["jurisdiction"]] = counts.get(rec["jurisdiction"], 0) + 1
    # counts.get, not `in counts`: a city yielding ZERO records used to skip
    # its own floor entirely — five seats failed while none passed, which is
    # how the 2026-08-12 Crest Hill retheme reached a PR as a silent deletion.
    # A failed exit here means the workflow preserves the shipped contact.
    for jurisdiction, floor in MIN_SEATS.items():
        if counts.get(jurisdiction, 0) < floor:
            print("FATAL: %s produced %d officials (floor %d) — page layout changed"
                  % (jurisdiction, counts.get(jurisdiction, 0), floor), file=sys.stderr)
            sys.exit(1)

    payload = {
        "county": "Will",
        "kind": "municipal-enrichment",
        "directory_url": "https://www.wcgl.org/municipal-members.html",
        "scraped_at": scraped_at,
        "officials": records,
    }
    with open(args.out, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    contact = sum(1 for r in records if r["person_phone"] or r["person_email"])
    print("scraped %s -> %s (%d officials, %d with per-seat contact)%s"
          % (", ".join("%s %d" % (k, v) for k, v in sorted(counts.items())),
             args.out, len(records), contact,
             "; FAILED: " + "; ".join(failures) if failures else ""),
          file=sys.stderr)


if __name__ == "__main__":
    main()
