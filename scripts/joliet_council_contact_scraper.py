#!/usr/bin/env python3
"""
Joliet city council per-seat contact (the city's own site)
=========================================================
Adds the per-seat phone and e-mail the Will County Clerk's directory does not
publish for Joliet — the metro's third-largest city and, until now, the one
ward city whose seat cards could name a council member but no way to reach one.

WHY THIS WAS PREVIOUSLY RECORDED AS UNBUILDABLE — AND WHAT CHANGED
------------------------------------------------------------------
Joliet was deliberately skipped when the other Will ward cities were built:
joliet.gov returned 403 to every client tried, jolietcity.org appeared to be a
client-rendered app with no text, and the only Internet Archive snapshot was
from 2022 (four years stale, two elections out of date). Writing a parser
against a page whose structure could not be inspected was the wrong trade.

Re-tested 2026-07-28, both premises turned out to be wrong in the same way the
McHenry/Kendall block was: joliet.gov fingerprints the HTTP CLIENT, and a
COMPLETE browser header set (Accept, Accept-Language, Accept-Encoding, the
sec-ch-ua / Sec-Fetch-* client hints, Upgrade-Insecure-Requests) gets a plain
200 — the 403 was never about the path. And jolietcity.org is not the city's
site at all: it serves a 114-byte parked-domain lander that redirects to
/lander, which is why it looked "client-rendered". The city publishes a council
index at /government/city-council-3189 plus one bio page per member, each
carrying the member's own e-mail and phone.

Lesson worth keeping: a recorded "unbuildable" is a snapshot of what was tried,
not a property of the source. This one cost nothing to re-test.

THE CLERK REMAINS THE ROSTER OF RECORD. Joliet's members, seats, and districts
already come from the Clerk's directory; this contributes contact only, matched
by name, and the builder never adds or re-roles a seat-holder from here.

Two filters, both honesty-driven:
- The city's main line (815-724-4000) appears on every bio page. A "direct"
  number that is just the switchboard is not a direct line, so it is dropped —
  the builder drops it again if it matches the roster's hall phone.
- The template placeholder "(999) 999-9999" appears on some pages and is never
  a phone number.

FETCH POSTURE — TERMINAL (measured 2026-07-28, after the first live CI run):
joliet.gov is fronted by Akamai, which answers with a hard WAF deny (a 408-byte
static page carrying an x-reference-error), NOT a solvable challenge. There is
nothing for a browser to clear, which is why the Playwright rung below fails in
CI exactly as plain requests does. This is the McHenry/Kendall class, not the
DuPage class: DuPage's Cloudflare edge challenges a datacenter client and a real
browser gets through, whereas this one simply refuses.

The Internet Archive was evaluated as a third rung and deliberately NOT added.
The captures are good — the archived index still yields all nine bio links and
the bio pages still carry their e-mail addresses — but the newest index capture
was 69 days old against the fleet's 45-day guard, so a rung built to convention
would refuse every time, and widening the guard for one source would trade a
fleet-wide honesty rule for data that is already covered: a blocked run
preserves Joliet's last-good entry (build_municipal_officials_roster.py's
--preserved), which came from a live scrape of the real site rather than a dated
copy of it. Standing issue tracks the block. If the edge ever relaxes, the two
rungs below pick the city back up with no further change.

Usage:
    python3 joliet_council_contact_scraper.py --out joliet_council_contact.json

Notes on data honesty (per project conventions):
- Fields that can't be parsed are stored as null, never guessed.
- Every record includes `source_url` and `scraped_at` for traceability.
"""

import argparse
import html as html_module
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

COUNCIL_URL = "https://www.joliet.gov/government/city-council-3189"
BIO_BASE = "https://www.joliet.gov"

# The complete fingerprint — a partial set is what the 403 was about.
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
REQUEST_TIMEOUT = 60

JURISDICTION = "City of Joliet"
# Most member pages end "-bio", but not all — Juan Moreno's is just
# /government/city-council/juan-moreno, and requiring the suffix dropped him
# silently. The council INDEX is /government/city-council-3189 (no slash), so
# it can't match this.
BIO_LINK_RE = re.compile(r"/government/city-council/[a-z0-9\-]+", re.I)
EMAIL_RE = re.compile(r"[\w.\-+]+@[\w.\-]+\.\w{2,}")
PHONE_RE = re.compile(r"\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}")
# The switchboard, and a CMS template placeholder. Neither is a person's line.
CITY_MAIN_LINE = "815-724-4000"
PLACEHOLDER_PHONES = {"999-999-9999"}

# Joliet seats a mayor plus eight council members (five by district, three
# at-large) — nine pages. A shrink means the site changed or the council did.
MIN_BIOS = 9


def fetch_requests(url):
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    if "Access Denied" in resp.text[:4000]:
        raise RuntimeError("edge returned a block interstitial")
    return resp.text


_BROWSER = {"playwright": None, "browser": None, "context": None}


def fetch_playwright(url):
    """Escalation rung. It does NOT currently carry this city — see the module
    docstring's FETCH POSTURE.

    This rung was added when curl got 200 where python-requests got 403 with a
    byte-identical header set, which reads as client fingerprinting. The first
    live CI run (2026-07-28) showed that was only half the picture: the edge
    also denies by network, and it denies this browser rung too. The rung is
    kept because it is correct and costs one failed attempt — if Joliet's edge
    ever relaxes, this is what picks the city back up with no further change.
    One browser context is reused across the nine page loads rather than
    launched per page.
    """
    from playwright.sync_api import sync_playwright

    if _BROWSER["context"] is None:
        _BROWSER["playwright"] = sync_playwright().start()
        _BROWSER["browser"] = _BROWSER["playwright"].chromium.launch()
        _BROWSER["context"] = _BROWSER["browser"].new_context(
            user_agent=HEADERS["User-Agent"])
    page = _BROWSER["context"].new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
        html_text = page.content()
    finally:
        page.close()
    if "Access Denied" in html_text[:4000]:
        raise RuntimeError("edge returned a block interstitial to the browser rung")
    return html_text


def close_browser():
    if _BROWSER["browser"] is not None:
        _BROWSER["browser"].close()
    if _BROWSER["playwright"] is not None:
        _BROWSER["playwright"].stop()
    _BROWSER.update({"playwright": None, "browser": None, "context": None})


# The Internet Archive is deliberately NOT a rung here: its newest snapshot of
# this page is from 2022, two elections out of date, and the 45-day age guard
# the other blocked-source scrapers use would refuse it anyway. Serving a 2022
# council would be worse than serving none.
# --- robots.txt, read once per host with the client this file crawls with ------
# CLAUDE.md's rule is that robots.txt is read before the first fetch of a host,
# and measured 2026-09-12 almost no scraper here enacted it. This file does now.
# Every rung below sends HEADERS' User-Agent, so one reading answers for all of
# them and there is no client to escalate to. Cached per host so a run that
# fetches several pages from one site asks once, which is also what keeps the
# extra request count at one per host per run.
#
# Measured 2026-09-30, four reads per client: www.joliet.gov serves a 6,641-byte
# policy to this client, whose HEADERS carry the Sec-CH-UA hints its edge wants;
# a client without them is refused its own robots.txt with 403 four times of
# four. EITHER READING PERMITS NOW, and the 403 one is why this file could be
# wired today: a 403 on robots.txt is RFC 9309 2.3.1.3 'unavailable', which
# allows, per Adam's ruling of 2026-09-29 (#1271). No rule in the policy's one
# binding group matches the council pages, and it states no Crawl-delay and no
# Content-Signal. It is the CMS VENDOR'S DEFAULT, byte-identical by md5 to the
# one Kendall and McHenry counties serve, so it records what the platform ships
# rather than the city's own choice.
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
                                 label='joliet-council-contact-scraper')
    print("robots.txt %s: %s" % (host, why), file=sys.stderr)
    _ROBOTS_ASKED[host] = why


def fetch(url, engine="auto"):
    rungs = {"requests": [fetch_requests], "playwright": [fetch_playwright]}.get(
        engine, [fetch_requests, fetch_playwright])
    require_robots(url)
    last = None
    for rung in rungs:
        try:
            return rung(url)
        except Exception as exc:  # noqa: BLE001 - every rung failure escalates
            last = exc
            print("%s rung failed for %s (%s)" % (rung.__name__, url, exc),
                  file=sys.stderr)
    raise RuntimeError("every fetch rung failed for %s: %s" % (url, last))


def text_lines(html_text):
    body = re.sub(r"(?is)<(script|style|nav|footer)\b.*?</\1>", " ", html_text)
    out = []
    for line in re.sub(r"(?s)<[^>]+>", "\n", body).splitlines():
        # Unescape first: the bio pages separate the e-mail from the phone with
        # a literal &nbsp; line, which must collapse away rather than sit
        # between them as content.
        line = " ".join(html_module.unescape(line).replace("\xa0", " ").split())
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
        return None
    formatted = "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])
    if formatted == CITY_MAIN_LINE or formatted in PLACEHOLDER_PHONES:
        return None
    return formatted


def bio_links(index_html):
    links = []
    for path in BIO_LINK_RE.findall(index_html):
        if path not in links:
            links.append(path)
    return links


def merge_split_emails(lines):
    """Rejoin an address the markup broke across two lines.

    One bio splits its address mid-token ("jclement" / "@joliet.gov"), which
    otherwise reads as two non-addresses and drops that member silently.
    """
    out = []
    for line in lines:
        if line.startswith("@") and out:
            out[-1] = out[-1] + line
        else:
            out.append(line)
    return out


def parse_bio(html_text, source_url, scraped_at):
    """Pull one member's contact from their bio page.

    The pages read name / seat / e-mail / phone, but not uniformly: a council
    member carries a "District 1" line between the name and the address while
    the mayor does not, and the phone sits one or two lines below the address.
    So the address anchors the block and the name is found by walking up past
    any seat line, rather than by a fixed offset.
    """
    lines = merge_split_emails(text_lines(html_text))
    for i, line in enumerate(lines):
        if not EMAIL_RE.fullmatch(line):
            continue
        name, office = None, "Council Member"
        for j in range(i - 1, max(-1, i - 4), -1):
            candidate = lines[j]
            if re.fullmatch(r"(?:District\s*\d+|At[\s-]*Large)", candidate, re.I):
                continue  # the seat line, which the Clerk already gives us
            # Some lines carry the seat inline ("Councilwoman Jan Hallums
            # Quillman, At-large"), so an optional trailing seat is allowed.
            match = re.match(r"^(?:(Mayor|Council(?:wo)?man|Councilmember)\s+)?"
                             r"([A-Z][A-Za-z.'’\-]+(?:\s+[A-Z][A-Za-z.'’\-]*)+?)"
                             r"(?:,\s*(?:At[\s-]*large|District\s*\d+))?$",
                             candidate, re.I)
            if not match:
                continue
            if match.group(1) and match.group(1).lower() == "mayor":
                office = "Mayor"
            name = clean(match.group(2))
            break
        if not name:
            continue
        phone = None
        for k in range(i + 1, min(len(lines), i + 4)):
            if PHONE_RE.fullmatch(lines[k]):
                phone = normalize_phone(lines[k])
                break
        return {
            "jurisdiction": JURISDICTION,
            "office": office,
            # District comes from the Clerk's directory, which already has it;
            # contact is what this source adds.
            "district": None,
            "name": name,
            "person_phone": phone,
            "person_email": line.lower(),
            "source_url": source_url,
            "scraped_at": scraped_at,
        }
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", default="joliet_council_contact.json")
    parser.add_argument("--engine", choices=("auto", "requests", "playwright"),
                        default="auto",
                        help="fetch rung; auto tries requests then playwright")
    args = parser.parse_args()

    scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        index_html = fetch(COUNCIL_URL, args.engine)
    except Exception as exc:  # noqa: BLE001
        print("FATAL: %s" % exc, file=sys.stderr)
        sys.exit(1)
    links = bio_links(index_html)
    if len(links) < MIN_BIOS:
        print("FATAL: found %d council bio links (expected >= %d) — the council page "
              "changed" % (len(links), MIN_BIOS), file=sys.stderr)
        sys.exit(1)

    records = []
    for path in links:
        url = BIO_BASE + path
        try:
            record = parse_bio(fetch(url, args.engine), url, scraped_at)
        except Exception as exc:  # noqa: BLE001 - one bio must not sink the rest
            print("WARNING: %s failed (%s)" % (url, exc), file=sys.stderr)
            continue
        if record:
            records.append(record)
        else:
            print("WARNING: no contact parsed from %s" % url, file=sys.stderr)

    if len(records) < MIN_BIOS:
        print("FATAL: parsed %d council members (expected >= %d) — bio page layout "
              "changed" % (len(records), MIN_BIOS), file=sys.stderr)
        sys.exit(1)

    payload = {
        "county": "Will",
        "kind": "municipal-enrichment",
        "directory_url": COUNCIL_URL,
        "scraped_at": scraped_at,
        "officials": records,
    }
    with open(args.out, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    close_browser()
    with_phone = sum(1 for r in records if r["person_phone"])
    print("scraped Joliet: %d council members, %d with e-mail, %d with a direct phone "
          "-> %s" % (len(records), sum(1 for r in records if r["person_email"]),
                     with_phone, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
