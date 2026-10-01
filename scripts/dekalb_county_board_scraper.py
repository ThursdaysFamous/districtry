#!/usr/bin/env python3
"""
Stage 1 of the DeKalb County Board roster pipeline: scrape the county's
board-members directory into raw JSON for build_dekalb_county_board_roster.py.

WHY A SCRAPER WHEN THE BOUNDARY GIS ALREADY CARRIES OFFICEHOLDERS.
DeKalb's District_AreaEffective2022 feature layer declares Member1/Member2 with
their own phone and e-mail columns, which looks like a rule-4 branch 1 county —
name rides the boundary, no pipeline needed. Measured, it isn't: the two phone
columns are populated on 0 of 12 districts and Member2_EMail on 10 of 12, while
the county's own members page carries party, term, 22 phones and 24 e-mails.
A schema is not data. The GIS supplies the geometry; this supplies the people.

PAGE SHAPE. One <li class="team-pic-container"> per member, carrying the name in
an <h1>, the district and party together as "<b>District:</b> 5/D", the term
under "Consecutive Service:", an optional "Phone:" line and a mailto link — plus
a "Map of County Board District N" link that repeats the district. That repeat is
parsed and cross-checked against the declared district, because a member block
that disagrees with itself is the signal that the markup drifted.

THE BUG THIS PARSER IS SHAPED AROUND. Two members publish no phone. A first
attempt scanned a fixed line window after the name and, on those two, ran past
the end of the block and picked up the NEXT member's phone number — attributing
a real person's phone to someone else, silently, on a card that looks fine. Each
block is therefore bounded by the next block's start before any field is read.

THE CHAIR comes from a second page, the county's own "Past & Present
Chairpersons" table, whose first data row is the sitting chair. The role is
applied only if that name matches exactly one scraped member; a chair who has
left the board resolves to no match and the role is dropped rather than guessed
onto someone. If that page fails, the members scrape still succeeds without it.

FETCHING — AND THE THING THAT WAS MISREAD ABOUT IT. dekalbcounty.org answers
some requests with a ~220-byte captcha-redirect stub instead of the page. The
original read of that was "intermittent, roughly two in three, so retry"; the
retry loop below is still here and still correct, but the premise was wrong in
the way that decides whether retrying can ever work.

The stub is SiteGround's SG-Captcha, and its own headers say what it keys on:
`SG-Captcha: challenge` alongside a refresh to
`/.well-known/sgcaptcha/?r=<path>&y=ipr:<CALLER IP>:<nonce>` — `ipr` for IP
reputation. It is not sampling requests, it is scoring the CLIENT ADDRESS. So
"how often is it blocked" has no single answer: measured 2026-08-02 from a
well-reputed egress it alternates roughly 1-in-2 and six attempts clear it
comfortably, while from a GitHub Actions runner the first scheduled run
(2026-07-31) took the stub on all six attempts in 33 seconds and failed the job.
Six independent draws at the observed rate would be a 1-in-700 coincidence; the
runner's address is simply on the wrong side of the score.

That distinction is the whole design of the fetch below. Raising FETCH_ATTEMPTS
buys nothing where it matters — the address is the variable, not the count — so
the escalation is the fleet's standard engine ladder instead:

    requests (with the retry loop)  ->  playwright  ->  wayback

Playwright is a real browser and nothing more; no challenge is decoded or
replayed, so if the edge wants a human this fails like it should.

AND SOMETIMES IT DOES — WHICH TOOK FOUR CI RUNS TO SEE. Measured 2026-08-02 by
dispatching this workflow repeatedly, plus the scheduled run of 07-31:

    runner A   requests 6/6 stub                                    REFUSED
    runner B   requests 6/6 stub; Chromium held 24s on the
               interstitial; Archive 144 days old vs the 45-day guard REFUSED
    runner C   requests 6/6 stub                                    REFUSED
    runner D   carried on the FIRST request, 0.9s                   CLEARED

Same commit, same hour, four different runner addresses. After runs A-C the
obvious conclusion was "blocked from CI, every rung, give it the McHenry
posture" — and that conclusion is wrong in a way three consecutive failures
cannot show you. There is no per-CI verdict to reach, because CI is not one
caller: GitHub hands out addresses from a pool and DeKalb's edge scores them
individually. The honest statement is a RATE, and even 3-of-4 is a small sample.

The posture that follows is the same one, for a better reason. The scrape step
is continue-on-error and reports on a standing issue not because the source is
gone, but because a job that fails on address luck should not turn red — the
weekly cadence covers it, since a week that draws a scored address is followed
by one that may not. Nothing needs to change for automation to resume; the run
that succeeds simply opens its PR as usual, which is exactly what runner D did.

Note the block is scoped to dekalbcounty.org: the clerk's own domain
(dekalbcountyclerkil.gov, which serves the yearbook PDF) is open, so a DeKalb
failure here says nothing about DeKalb sources generally.

Committee assignments and the per-district map PDFs are on the page and
deliberately not collected — neither is card material, matching the McHenry and
Livingston rosters. No street addresses appear on this page at all.

Usage:
    python3 dekalb_county_board_scraper.py [output.json]
    python3 dekalb_county_board_scraper.py out.json --engine playwright
"""

import argparse
import html
import json
import re
import sys
import time
from datetime import datetime, timezone

import requests
from scraper_common import (  # noqa: E402  (shared machinery — do not fork)
    require_robots_once, UA_CHROME_WIN_126,
)

SOURCE_URL = "https://dekalbcounty.org/government/county-board/county-board-members/"
CHAIR_URL = "https://dekalbcounty.org/government/county-board/past-county-board-chairpersons/"
# A browser UA is table stakes, not the fix: SG-Captcha scores the address, so
# the same headers pass from one host and fail from another.
HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
}
REQUEST_TIMEOUT = 60
FETCH_ATTEMPTS = 6

# The browser rung polls rather than reading once: see fetch_playwright.
PW_SETTLE_MS = 3000
PW_POLLS = 8

WAYBACK_API = "https://archive.org/wayback/available?url=%s"
# Same guard as the McHenry/Kendall rungs: an archived roster older than this is
# not "the current board", so the rung refuses rather than shipping it as one.
WAYBACK_MAX_AGE_DAYS = 45

# Sucuri's stub is a bare <html> with a meta-refresh to /.well-known/sgcaptcha/.
# The generic markers follow the McHenry/Kendall list so one convention covers
# every bot-managed county source in the fleet.
BLOCK_MARKERS = (
    "sgcaptcha",
    "just a moment",
    "attention required",
    "checking your browser",
    "access denied",
    "cf-chl",
)

BLOCK_SPLIT = re.compile(r'(?=<li class="team-pic-container)')
NAME_RE = re.compile(r"<h1>(.*?)</h1>", re.S)
DISTRICT_RE = re.compile(r"<b>\s*District:\s*</b>\s*(\d{1,2})\s*/\s*([A-Za-z])", re.I)
PHONE_RE = re.compile(r"Phone:\s*([0-9][0-9\-().\s]{6,})")
EMAIL_RE = re.compile(r'mailto:([^"?\s]+)')
TERM_RE = re.compile(r"<b>\s*Consecutive Service:\s*</b>\s*(?:<br\s*/?>\s*)*"
                     r"([0-9/]{6,10}\s*-\s*[0-9/]{6,10})", re.I)
MAP_RE = re.compile(r"Map of County Board District\s*(\d{1,2})", re.I)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)

CHAIR_ROW_RE = re.compile(
    r"<tr[^>]*>\s*<td[^>]*>(?P<elected>[^<]*)</td>\s*<td[^>]*>(?P<years>[^<]*)</td>"
    r"\s*<td[^>]*>(?P<party>[^<]*)</td>\s*<td[^>]*>(?P<name>[^<]*)</td>", re.I | re.S)

PARTY = {"r": "R", "d": "D", "i": "I"}


def text_of(fragment):
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", fragment))).strip()


def parse_members(page):
    page = SCRIPT_RE.sub(" ", page)
    records = []
    for block in BLOCK_SPLIT.split(page)[1:]:
        name_m = NAME_RE.search(block)
        dist_m = DISTRICT_RE.search(block)
        if not (name_m and dist_m):
            continue
        name = text_of(name_m.group(1))
        if not name:
            continue
        rec = {"district": dist_m.group(1).lstrip("0") or "0", "name": name}
        party = PARTY.get(dist_m.group(2).lower())
        if party:
            rec["party"] = party
        phone = PHONE_RE.search(block)
        if phone:
            rec["phone"] = re.sub(r"\s+", " ", phone.group(1)).strip(" .-")
        email = EMAIL_RE.search(block)
        if email:
            rec["email"] = html.unescape(email.group(1)).strip()
        term = TERM_RE.search(block)
        if term:
            rec["term"] = re.sub(r"\s+", " ", term.group(1)).strip()
        # self-check: the block's own map link names its district a second time
        map_d = MAP_RE.search(block)
        if map_d:
            rec["map_district"] = map_d.group(1).lstrip("0") or "0"
        records.append(rec)
    return records


def parse_chair(page):
    """First data row of the chairperson table = the sitting chair."""
    body = re.search(r"<tbody[^>]*>(.*?)</tbody>", page, re.S | re.I)
    if not body:
        return None
    row = CHAIR_ROW_RE.search(body.group(1))
    if not row:
        return None
    name = text_of(row.group("name"))
    if not name:
        return None
    return {"name": name,
            "party": PARTY.get(text_of(row.group("party")).lower()),
            "elected": text_of(row.group("elected")),
            "fiscal_years": text_of(row.group("years"))}


def _looks_blocked(page):
    low = (page or "").lower()
    return any(marker in low for marker in BLOCK_MARKERS)


def fetch_requests(url, attempts=FETCH_ATTEMPTS):
    """Rung 1: plain requests, retried past the captcha stub."""
    session = requests.Session()
    last = None
    try:
        for attempt in range(attempts):
            try:
                resp = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
                # SG-Captcha serves the stub as 202, not an error status, so
                # status alone can't tell a challenge from the page — the marker
                # test is what decides, and any 2xx/3xx is a candidate for it.
                if resp.ok and not _looks_blocked(resp.text):
                    return resp.text
                last = ("bot-management interstitial (HTTP %d)" % resp.status_code
                        if resp.ok else "HTTP %d" % resp.status_code)
            except requests.RequestException as exc:
                last = str(exc)
            time.sleep(1.5 * (attempt + 1))
    finally:
        session.close()
    raise RuntimeError("%d attempts, last: %s" % (attempts, last))


def fetch_playwright(url, settle_ms=PW_SETTLE_MS, polls=PW_POLLS):
    """Rung 2: a real browser, no evasion beyond being a real browser.

    SG-Captcha's IP-reputation interstitial is a meta-refresh into a JS
    challenge that a genuine browser completes unprompted, so this rung waits
    for the navigation to settle on a real document. No challenge is solved,
    decoded or replayed here — if the edge wants a human, this fails.

    IT MUST POLL, AND THE FIRST VERSION DID NOT. The stub's refresh is
    content="0;…", so the browser is mid-navigation almost exactly when the
    content is asked for, and Playwright answers that with a hard error rather
    than a page: "Unable to retrieve content because the page is navigating and
    changing the content." That error propagated as a rung failure on the first
    CI run, which read as "a real browser doesn't clear it either" — a
    conclusion this rung had not actually tested. A document in motion is the
    challenge WORKING; only a settled interstitial is a refusal.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        markup, last = "", "no document"
        try:
            page = browser.new_page(user_agent=HEADERS["User-Agent"])
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
            for _ in range(polls):
                try:
                    markup = page.content()
                except Exception as exc:  # noqa: BLE001 — mid-navigation, not a failure
                    markup, last = "", "still navigating (%s)" % type(exc).__name__
                if markup and not _looks_blocked(markup):
                    return markup
                if markup:
                    last = "interstitial still served"
                page.wait_for_timeout(settle_ms)
        finally:
            browser.close()
    raise RuntimeError("browser never reached the document after %.0fs (%s)"
                       % (polls * settle_ms / 1000.0, last))


def fetch_wayback(url):
    """Rung 3: the Internet Archive's newest snapshot, refused if it is stale.

    THE ARCHIVE IS ITS OWN HOST and is asked separately. It is recorded in
    scraper_common.ROBOTS_DEFERRED_HOSTS because its robots.txt resets the
    connection from this project's sandbox, so the seam prints NOT READ with
    that reason rather than passing silently.
    """
    require_robots_once(WAYBACK_API % url, HEADERS["User-Agent"],
                        headers=HEADERS, label="dekalb-scraper-archive")
    resp = requests.get(WAYBACK_API % url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    snapshot = ((resp.json() or {}).get("archived_snapshots") or {}).get("closest")
    if not snapshot or not snapshot.get("available"):
        raise RuntimeError("no Archive snapshot available")
    taken = datetime.strptime(snapshot.get("timestamp") or "",
                              "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - taken).days
    if age_days > WAYBACK_MAX_AGE_DAYS:
        raise RuntimeError("newest snapshot is %d days old (max %d) — refusing to "
                           "serve a stale board as the current one"
                           % (age_days, WAYBACK_MAX_AGE_DAYS))
    page = requests.get(snapshot["url"], headers=HEADERS, timeout=REQUEST_TIMEOUT)
    page.raise_for_status()
    return page.text


def fetch(url, engine="auto"):
    """Walk the ladder, naming the rung that carried the fetch (or failed).

    THE COUNTY'S RULES ARE READ BEFORE ANY RUNG, with the identity every rung
    sends, so a refusal stops the ladder rather than being met by the next rung
    down. dekalbcounty.org had been recorded as answering every client with a
    managed challenge; re-measured from a GitHub runner on 2026-10-01, the
    vantage the weekly job crawls from, it serves a 37-byte policy whose binding
    group matches none of the paths read here, on all three reads of a
    deliberate re-measurement fifteen seconds apart. The challenge is on the
    PAGE and not on the policy, which is why the ladder below still exists.
    """
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="dekalb-scraper")
    rungs = {"requests": [fetch_requests], "playwright": [fetch_playwright],
             "wayback": [fetch_wayback]}.get(
                 engine, [fetch_requests, fetch_playwright, fetch_wayback])
    last = None
    for rung in rungs:
        try:
            markup = rung(url)
            print("dekalb-scraper: %s carried by the %s rung"
                  % (url, rung.__name__.replace("fetch_", "")), file=sys.stderr)
            return markup
        except Exception as exc:  # noqa: BLE001 - every rung failure escalates
            last = exc
            print("dekalb-scraper: %s rung failed for %s (%s)"
                  % (rung.__name__.replace("fetch_", ""), url, exc), file=sys.stderr)
    raise RuntimeError("every fetch rung failed for %s — last: %s" % (url, last))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out_path", nargs="?", default="dekalb_county_board_raw.json")
    parser.add_argument("--engine", choices=("auto", "requests", "playwright", "wayback"),
                        default="auto",
                        help="fetch rung; auto walks requests -> playwright -> wayback")
    args = parser.parse_args()
    out_path = args.out_path
    records = parse_members(fetch(SOURCE_URL, args.engine))
    if not records:
        print("dekalb-scraper: FAIL — parsed 0 member blocks; the directory "
              "markup changed", file=sys.stderr)
        sys.exit(1)

    mismatched = [r for r in records
                  if r.get("map_district") and r["map_district"] != r["district"]]
    if mismatched:
        print("dekalb-scraper: FAIL — %d member block(s) disagree with their own "
              "district map link (%s); the page structure changed and blocks are "
              "no longer being read whole"
              % (len(mismatched),
                 ", ".join("%s: %s vs %s" % (r["name"], r["district"], r["map_district"])
                           for r in mismatched[:4])),
              file=sys.stderr)
        sys.exit(1)

    # The chair is enrichment: its absence must not fail a good members scrape.
    chair = None
    try:
        chair = parse_chair(fetch(CHAIR_URL, args.engine))
    except Exception as exc:  # noqa: BLE001 — any transport/parse failure is non-fatal
        print("dekalb-scraper: note — chairperson page unavailable (%s); shipping "
              "the roster without a chair role" % exc, file=sys.stderr)

    payload = {"source_url": SOURCE_URL, "chair_source_url": CHAIR_URL,
               "chair": chair, "records": records}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("dekalb-scraper: wrote %s — %d members, %d districts, %d phones, "
          "%d e-mails, chair %s"
          % (out_path, len(records), len({r["district"] for r in records}),
             sum(1 for r in records if r.get("phone")),
             sum(1 for r in records if r.get("email")),
             (chair or {}).get("name") or "unresolved"))


if __name__ == "__main__":
    main()
