#!/usr/bin/env python3
"""Scrape stage 1: Detroit's nine City Council members, cached for
build_mi_detroit_council_roster.py (stage 2).

WHAT DETROIT ELECTS
--------------------
Detroit's 2012 charter, Art. 4 §4-101: a nine-member Council, "seven members
elected by district and two members elected at large". So SEVEN of the nine
sit on the boundaries this app draws and TWO represent the whole city. The
mayor is a separate office and is not a council member, so nothing here reads
one. A district layer that named only the district member would answer seven
ninths of the question and look complete doing it, which is why the citywide
pair ships beside the districts rather than being dropped.

THE LIVE SITE REFUSES THIS CLIENT AND THE ARCHIVE DOES NOT
-----------------------------------------------------------
Measured 2026-09-05, both stacks, both paths:

    requests, browser UA          detroitmi.gov/government/city-council  403
    stdlib + Chrome client hints  (the rung that unblocked Kendall)       403

Both return Cloudflare's interactive `Just a moment...` page. That is a
MANAGED CHALLENGE, and this project does not defeat one: there is deliberately
no headless-browser rung here, unlike the Illinois ladder, because a rung whose
job is to sit and wait for a challenge to clear is the thing the rule is about.

The Internet Archive's crawler is NOT refused — the page has a dense snapshot
history — so the terminal rung reads a public archive of the city's own page,
exactly as scripts/kendall_county_board_scraper.py and
scripts/mchenry_county_board_scraper.py have since 2026-07. The snapshot's
timestamp rides through to the shipped file and onto the card, and a snapshot
older than WAYBACK_MAX_AGE_DAYS is REFUSED rather than served: stale
officeholder data presented as current is worse than a loud failed run.

AND THE CRAWL POLICY PERMITS THE PAGE, WHICH HAD TO BE READ TO KNOW
--------------------------------------------------------------------
detroitmi.gov/robots.txt is itself behind the challenge, so the policy cannot
be read from the live site. It CAN be read from the Archive, and it is stock
Drupal: /core/, /profiles/, /admin/, /user/*, /search*, query strings. Nothing
disallows /government/. Reading half of that file is how you get the opposite
answer — the block of `Disallow:` lines begins `Disallow: /admin/`, and a read
truncated mid-line says `Disallow: /`.

THE GROUPING HEADING IS THE AUTHORITY (the Jackson County rule)
----------------------------------------------------------------
The page is Drupal, and each member is an `<article class="profile">` inside
the view under `<h2 class="block__title">Members</h2>`. Nothing else on the
page currently uses that markup — but "currently" is the whole risk, because a
staff or commission profile added anywhere else would be indistinguishable to a
parser that walks every `article.profile` in the document. So this reads only
inside the Members block AND refuses if the document carries more profiles than
that block does.

The page also declares its own count: the list is `class="... b-count-9 ..."`,
written by the view from the number of rows it rendered. That is a publisher-
maintained count guard and it is asserted against the parse, so a member
dropping out of the markup fails the run instead of shipping an eight-member
council.

TWO SMALLER TRAPS, BOTH MEASURED
---------------------------------
  * FOUR of the nine seat strings carry a DOUBLE space ("City Council  District
    3") and five do not — districts 3, 4, 6 and 7. Whitespace is normalised
    before any match, so the district regex does not silently miss them.
  * The name is followed by an inline `<svg>` chevron INSIDE the anchor, so the
    anchor's naive text is "James Tate \n <path .../>". The name is cut at the
    `<svg`, not at `</a>`.

WHAT THE CITY PUBLISHES, AND AT WHICH LEVEL — THE SWITCHBOARD RULE
--------------------------------------------------------------------
NO PER-MEMBER CONTACT EXISTS: zero `mailto:` and zero `tel:` links across all
nine, on the listing and on a member's own profile page alike, both read through
the Archive. So no member row carries a number, and nothing here invents one.

But the page DOES publish the body's own office, exactly once:

    City Council Office, 2 Woodward Ave. Suite 1340, Detroit, MI 48226
    (313) 224-3443

That is `docs/EXPANSION_GUIDE.md` Part 5's switchboard case — a number that
belongs to the BODY and not to any member — so it is parsed here, shipped once
at the top level, and rendered on the card as the Council's office rather than
attached to whoever's district you clicked. An earlier version of this scraper
said the page carried no contact at all, which was true of its LINKS and false
of its text, and would have thrown away the one contact route Detroit does
publish.

The parse is gated on the number appearing EXACTLY ONCE. If the city ever gives
each member their own line, this stops being a switchboard and the run fails
rather than quietly hoisting one member's direct number onto all nine.

    python3 mi/scripts/mi_detroit_council_scraper.py            # refresh cache
    python3 mi/scripts/mi_detroit_council_scraper.py --engine wayback
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache", "mi_detroit_council.json")

COUNCIL_URL = "https://detroitmi.gov/government/city-council"
SITE_ROOT = "https://detroitmi.gov"

# Detroit City Charter (2012) Art. 4 §4-101.
EXPECT_DISTRICTS = tuple(range(1, 8))   # seven single-member districts
EXPECT_AT_LARGE = 2                     # two elected citywide
EXPECT_SEATS = len(EXPECT_DISTRICTS) + EXPECT_AT_LARGE

# A snapshot older than this is refused outright. Officeholder data that is
# quietly months stale is worse than a run that fails loudly and gets a human's
# attention -- the same reasoning, and the same number, as the Illinois ladder.
WAYBACK_MAX_AGE_DAYS = 45

# The fleet's genuine-browser header set (scripts/scraper_common.py's
# UA_HINTS_CHROME_126), copied rather than imported. THE STATED REASON IS NO
# LONGER THE WHOLE TRUTH: validate_workflow_deps.py permits the reach for a
# module named in its own FLEET_SHARED set, which scraper_common is, and this
# file now imports the robots seam from exactly there. The copy is left alone
# because replacing it would change what a host is told, which is a separate
# change; it is byte-identical to the shared set today.
UA_HINTS_CHROME_126 = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "sec-ch-ua": '"Chromium";v="126", "Not;A=Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


def fail(msg):
    print("detroit-council-scraper: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def _get(url, timeout=90):
    # Read the site's policy before the first fetch of its host, with the SAME
    # client that does the fetching — the header set below, browser string and
    # client hints included, because which client crawls decides which group
    # binds. Asked once per (host, client) by require_robots_once, so the
    # wayback rung asks about web.archive.org on its own.
    #
    # BOTH HOSTS PERMIT THE FETCH AND NEITHER BY PUBLISHING A PERMISSION.
    # Measured from a runner 2026-09-30: detroitmi.gov answers the robots
    # request itself with HTTP 403, which under RFC 9309 2.3.1.3 is no published
    # policy and therefore allows -- the reading the operator settled on
    # 2026-09-29 -- and web.archive.org answers 404, allow all. That second one
    # was in ROBOTS_DEFERRED_HOSTS until the runner measurement retired the
    # deferral, so a comment citing that record would already be out of date.
    #
    # The address is whatever the caller passes rather than a constant, so the
    # reading goes here and not at the top of the file: this scraper's rungs
    # include a url built from the live page's own markup.
    require_robots_once(url, UA_HINTS_CHROME_126["User-Agent"],
                        headers=dict(UA_HINTS_CHROME_126),
                        label="mi-detroit-council-scraper")
    req = urllib.request.Request(url, headers=dict(UA_HINTS_CHROME_126))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def _looks_challenged(html):
    return ("Just a moment" in html) or ("cf_chl" in html) or ("__cf_bm" in html)


# --------------------------------------------------------------------------
# Rung 1 — the live site, with a real browser's client hints.
# --------------------------------------------------------------------------
def fetch_direct(url):
    """The city's own page. Measured 403 on 2026-09-05; kept as the FIRST rung
    so the day Detroit stops refusing this client, the roster silently stops
    riding an archive and goes back to the source."""
    html = _get(url)
    if _looks_challenged(html):
        raise RuntimeError("live page is a Cloudflare challenge interstitial")
    return html, None


# --------------------------------------------------------------------------
# Rung 2 — the Internet Archive.
# --------------------------------------------------------------------------
def _newest_snapshot(url):
    try:
        body = _get("https://archive.org/wayback/available?"
                    + urllib.parse.urlencode({"url": url}), timeout=60)
        snap = (json.loads(body).get("archived_snapshots") or {}).get("closest") or {}
        return snap.get("timestamp") if snap.get("available") else None
    except (urllib.error.URLError, ValueError, OSError):
        return None


def fetch_wayback(url, retries=2):
    """Read a public archive of the city's own page. Not evasion and not a
    challenge bypass: the Archive's crawler reaches the page on its own terms
    and publishes the copy; this reads that copy and surfaces its date."""
    last = None
    for attempt in range(retries + 1):
        ts = _newest_snapshot(url)
        if ts is None:
            last = "no archive snapshot available"
            time.sleep(3 * (attempt + 1))
            continue
        age = (datetime.now(timezone.utc)
               - datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)).days
        if age > WAYBACK_MAX_AGE_DAYS:
            raise RuntimeError("newest archive snapshot is %d days old (max %d) — "
                               "refusing stale officeholder data" % (age, WAYBACK_MAX_AGE_DAYS))
        try:
            html = _get("https://web.archive.org/web/%sid_/%s" % (ts, url), timeout=120)
            if _looks_challenged(html):
                last = "archived copy is itself a challenge page"
            else:
                return html, ts
        except (urllib.error.URLError, OSError) as exc:
            last = str(exc)
        time.sleep(3 * (attempt + 1))
    raise RuntimeError("Internet Archive: %s" % last)


ENGINES = {"direct": fetch_direct, "wayback": fetch_wayback}
LADDER = ("direct", "wayback")


def fetch(url, engine="auto"):
    """Returns (html, archived_at | None). `archived_at` is the snapshot
    timestamp when the copy came from the Archive, and None when the city's own
    page answered — which is exactly what the card needs to say."""
    order = LADDER if engine == "auto" else (engine,)
    errors = []
    for name in order:
        try:
            html, ts = ENGINES[name](url)
            print("  rung %-8s OK (%d bytes)%s"
                  % (name, len(html), " snapshot %s" % ts if ts else ""), file=sys.stderr)
            return html, ts
        except Exception as exc:                      # noqa: BLE001 — a rung failing is data
            errors.append("%s: %s" % (name, exc))
            print("  rung %-8s no (%s)" % (name, exc), file=sys.stderr)
    fail("every fetch rung failed — " + "; ".join(errors))


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------
def _text(fragment):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment)).strip()


PROFILE_RE = re.compile(r'<article class="profile">(.*?)</article>', re.S)
NAME_RE = re.compile(r'<h5>\s*<a href="([^"]+)">(.*?)(?:<svg|</a>)', re.S)
SEAT_RE = re.compile(r"<p>(.*?)</p>", re.S)


def parse(html):
    """The Members block only, held to the page's own declared count."""
    start = html.find('class="block__title">Members</h2>')
    if start < 0:
        fail("no `Members` heading — the council page has been restructured")
    end = html.find("</ul>", start)
    if end < 0:
        fail("`Members` heading found but its list never closes")
    block = html[start:end]

    in_block = len(PROFILE_RE.findall(block))
    in_page = len(PROFILE_RE.findall(html))
    if in_block != in_page:
        fail("%d member profiles inside the Members block but %d on the page — "
             "profile markup is now used outside the block, so the grouping "
             "heading no longer isolates the council" % (in_block, in_page))

    declared = re.search(r"b-count-(\d+)", block)
    if not declared:
        fail("the members list no longer declares its own row count (b-count-N)")

    members = []
    for match in PROFILE_RE.finditer(block):
        frag = match.group(1)
        name_m, seat_m = NAME_RE.search(frag), SEAT_RE.search(frag)
        if not (name_m and seat_m):
            fail("a member profile carries no name/seat pair")
        seat = _text(seat_m.group(1))
        district = None
        dm = re.search(r"\bDistrict\s+(\d+)\b", seat)
        at_large = bool(re.search(r"\bAt[\s\-]Large\b", seat, re.I))
        if dm:
            district = int(dm.group(1))
        elif not at_large:
            fail("seat %r names neither a district nor an at-large office" % seat)
        members.append({
            "name": _text(name_m.group(2)),
            "seat": seat,
            "district": district,
            "profileUrl": urllib.parse.urljoin(SITE_ROOT, name_m.group(1)),
        })

    if int(declared.group(1)) != len(members):
        fail("the page's own list declares %s members and %d parsed"
             % (declared.group(1), len(members)))
    return members


OFFICE_RE = re.compile(r"City Council Office(.{0,300}?\(\d{3}\)\s?\d{3}-\d{4})", re.S)
PHONE_RE = re.compile(r"\((\d{3})\)\s?(\d{3})-(\d{4})")


def parse_office(html):
    """The BODY's own office block — address plus switchboard, published once.

    Returns {lines: [...], phone: "..."} or None. Refuses rather than guessing
    if the number stops being unique on the page, because a per-member number
    hoisted onto all nine would read as nine direct lines that are not."""
    hits = PHONE_RE.findall(html)
    if not hits:
        return None
    uniq = set(hits)
    if len(uniq) != 1:
        fail("the council page now publishes %d distinct phone numbers (%s) — this "
             "parser hoists ONE switchboard to the body and must not guess which "
             "of several belongs to whom" % (len(uniq), sorted(uniq)))
    area, exch, last = hits[0]
    phone = "(%s) %s-%s" % (area, exch, last)

    block = OFFICE_RE.search(html)
    if not block:
        return {"lines": [], "phone": phone}
    text = _text(block.group(1))
    # drop the trailing phone; the address is what is left
    text = PHONE_RE.sub("", text).strip(" ,")
    # The archived markup collapses the address onto one line, so split it
    # before the city/state/ZIP rather than on whitespace that is not there.
    lines = [seg.strip(" ,") for seg
             in re.split(r"\s+(?=[A-Z][A-Za-z.\- ]*,\s*[A-Z]{2}\s+\d{5})", text)
             if seg.strip(" ,")]
    if not lines:
        lines = [text] if text else []
    return {"lines": lines, "phone": phone}


def validate(members):
    seats = sorted(m["district"] for m in members if m["district"] is not None)
    at_large = [m for m in members if m["district"] is None]
    if len(members) != EXPECT_SEATS:
        fail("parsed %d members, charter seats %d" % (len(members), EXPECT_SEATS))
    if tuple(seats) != EXPECT_DISTRICTS:
        fail("districts %s, expected %s" % (seats, list(EXPECT_DISTRICTS)))
    if len(at_large) != EXPECT_AT_LARGE:
        fail("%d at-large members, expected %d" % (len(at_large), EXPECT_AT_LARGE))
    if len({m["name"] for m in members}) != len(members):
        fail("two seats carry the same name")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", choices=("auto",) + LADDER, default="auto")
    args = ap.parse_args()

    print("Fetching Detroit's council roster…", file=sys.stderr)
    html, archived_at = fetch(COUNCIL_URL, args.engine)
    members = parse(html)
    validate(members)
    office = parse_office(html)

    payload = {
        "sourceUrl": COUNCIL_URL,
        "archivedAt": archived_at,
        "members": members,
        "office": office,
    }
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    print("Wrote %s — %d members%s"
          % (CACHE, len(members),
             " (archive snapshot %s)" % archived_at if archived_at else " (live)"),
          file=sys.stderr)


if __name__ == "__main__":
    main()
