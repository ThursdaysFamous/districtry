#!/usr/bin/env python3
"""Scrape stage 1: Grand Rapids's City Commission, cached for
build_mi_grand_rapids_council.py (stage 2).

WHAT GRAND RAPIDS ELECTS, QUOTED FROM THE CITY
------------------------------------------------
grandrapidsmi.gov/Government/City-Commission states the arithmetic outright:

    "This legislative body consists of the Mayor and six Commissioners. The
     City is divided into three legislative districts called Wards. The
     residents of each Ward directly elect two commissioners to represent
     them. Commissioners serve four-year overlapping terms. Every two years,
     the community elects one commissioner from each ward."

Seven seats: two per ward on the polygons, plus a Mayor elected at large who
sits on none of them. The Mayor ships in a `citywide` block rather than being
dropped, because a ward card naming two of seven would look complete.

THE CITY PUBLISHES SIX OF THE SEVEN, AND THAT IS SHIPPED AS A SHORTFALL
-------------------------------------------------------------------------
Measured 2026-09-05: the commission page links exactly six commissioner pages
— one for Ward 1, two for Ward 2, two for Ward 3, and the Mayor — and the word
"vacant" appears nowhere ON IT.

THE SEAT IS VACANT AND THE CITY DOES SAY SO, JUST NOT THERE. An earlier version
of this docstring concluded "the city says neither", having measured only the
commission page. The city's own news post of 2026-04-17 — "Committee on
Appointments names three finalists for First Ward City Commissioner vacancy" —
states: "The vacancy was created following the resignation of former
Commissioner Drew Robbins." A 2026-03-31 post names ten applicants advancing.
ONE PAGE IS NOT THE CITY, which is the same error that once called Detroit's
open-data portal blocked.

So the card names the vacancy and its cause. What it does NOT say is anything
about how the vacancy has since been handled: no city source found on
2026-09-05 states an appointment outcome, and the commission page still lists
one Ward 1 commissioner. That silence ships as silence.

The rest is the Alexander County case: ship the six the city names, carry
`seats` beside them, and let the card account for the seventh. Guessing a name
is forbidden; silently shipping six for a seven-seat body would conceal a seat.

A TRAP THIS PARSER AVOIDS BY CONSTRUCTION: the departed commissioner's own page
(/government/city-commission/commissioners/drew-robbins/) STILL ANSWERS 200 and
is still in the city's sitemap. A scraper walking sitemap entries or guessing
commissioner URLs would ship him as sitting. This one reads the commission
listing, which no longer links him — the Alexander nav-menu rule.

THIS SITE IS READABLE, WHICH IS WHY THERE IS NO ARCHIVE RUNG
--------------------------------------------------------------
Unlike Detroit, www.grandrapidsmi.gov answers 200 to a plain client and its
robots.txt is readable and permits /government/ (it disallows /bin/, /config/,
/install/, /umbraco/, /views/ and /sandbox/ only). So this fetches the city
directly and FAILS LOUDLY if that ever stops working, rather than carrying a
fallback nothing has needed. The Detroit scraper next door is the pattern to
copy on the day it is needed.

THREE TRAPS, ALL MEASURED
---------------------------
  * THE E-MAIL DOMAIN IS NOT THE WEBSITE'S. Members are reachable at
    `@grcity.us` while the site is `grandrapidsmi.gov`. A scraper keyed to the
    site's own hostname finds ZERO addresses on a page that plainly has one —
    which is exactly what the first pass here did.
  * THE ROLE IS A STANDALONE LINE ON ONLY THREE OF THE SIX member pages. Read
    with an exact line match, Knight, Ysasi and Perdue come back with no ward
    at all; read from the page's flattened text they are unambiguous. So the
    ward is taken from the text and REQUIRED to be a single distinct value,
    and the listing page's own grouping is kept as the cross-check.
  * THE ADDRESS IS THE CITY'S, NOT THE COMMISSION'S, AND IS LABELLED THAT WAY.
    Detroit's council page carries an explicit "City Council Office" block with
    its own suite number; Grand Rapids carries 300 Monroe Avenue NW only in the
    site FOOTER, on every page of the site. So it ships as City Hall rather
    than as the Commission's office — the same address either way, but not a
    claim the city makes.
  * ONE PHONE IS ON EVERY PAGE AND IS NOT ANYONE'S. 616.456.3000 is the city
    switchboard; each member also has a distinct direct line. The switchboard
    is DETECTED as the number common to every member rather than hardcoded, so
    the day the city changes it this still hoists the right one — and if no
    single number is common to all, that is a refusal rather than a guess
    (docs/EXPANSION_GUIDE.md Part 5).

    python3 mi/scripts/mi_grand_rapids_council_scraper.py
"""

import argparse
import html as htmllib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import (UA_HEADERS_ROSTER_BOT,  # noqa: E402  (FLEET_SHARED)
                            require_robots_once)

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache", "mi_grand_rapids_council.json")

SITE = "https://www.grandrapidsmi.gov"
LISTING = SITE + "/Government/City-Commission"
MEMBER_PREFIX = "/government/city-commission/commissioners/"

# The city's own statement, above.
EXPECT_WARDS = ("1", "2", "3")
COMMISSIONERS_PER_WARD = 2
EXPECT_SEATS = len(EXPECT_WARDS) * COMMISSIONERS_PER_WARD + 1   # + the Mayor

# OUR OWN IDENTITY, MEASURED RATHER THAN ASSUMED (2026-10-01). This file
# used to send a Chrome string. Every page it fetches was re-read with
# scraper_common's districtry token on this file's own HTTP stack and
# answered in full, so the browser string was claiming a client this
# project does not run for no measured gain. A site that measurably
# refuses the token gets the browser rung back, per host, with the
# measurement written here.
UA = dict(UA_HEADERS_ROSTER_BOT)

PAUSE_S = 1.0   # the city sets no Crawl-delay; this is politeness, not policy

# WHY A VACANCY NEEDS ITS OWN SOURCE. A short ward is visible from the
# commission page — a ward listing fewer commissioners than the city elects —
# but WHY it is short is not on that page at all. The cause is stated in a
# separate city news post, so it is fetched and VERIFIED here rather than typed
# into a card: keyed by ward, and dropped (never guessed, never left stale) if
# the post stops saying it.
#
# The ordinal is how the post names the ward, and is checked, so this cannot
# attach one ward's vacancy to another's card.
VACANCY_SOURCES = {
    "1": {
        "url": (SITE + "/city-news/posts/committee-on-appointments-names-three-"
                       "finalists-for-first-ward-city-commissioner-vacancy/"),
        "ordinal": "First Ward",
    },
}
# The name stops at the sentence boundary. A period is allowed only on a
# single-letter token (a middle initial) — the first draft let it ride on any
# token and captured "Drew Robbins. The", which is the sentence, not the name.
RESIGNATION_RE = re.compile(
    r"vacancy was created following the resignation of former Commissioner\s+"
    r"((?:(?:[A-Z]\.|[A-Z][a-z\u2019'\-]+)\s+){1,3}[A-Z][a-z\u2019'\-]+)")
# THE DATE COMES FROM THE POST'S OWN DATE ELEMENT, NOT FROM THE PAGE. The first
# draft searched the whole flattened page for a "Month D, YYYY" and took the
# first hit. Measured 2026-09-05 there is exactly one on this page, so it was
# right — and it was right by luck: a dated banner, a "latest news" rail or a
# related-posts block ahead of the article would have displaced it silently,
# and the card would then state a wrong date about a named person's seat.
#
# The page carries NO semantic date: no <time datetime>, no
# article:published_time, no datePublished in ld+json (all three checked). What
# it does carry is the CMS's own date span, which is the narrowest anchor
# available, so that is what this reads. If the span goes away the date is
# simply not shipped — the card omits the clause and still reads correctly —
# rather than falling back to a page-wide scan, which is the guess this
# replaces.
POST_DATE_RE = re.compile(
    r'<span[^>]*class="[^"]*gs-news-details-date[^"]*"[^>]*>\s*'
    r'([A-Z][a-z]+ \d{1,2}, 20\d\d)\s*</span>')


def fail(msg):
    print("grand-rapids-council-scraper: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def get(url, timeout=60):
    require_robots_once(url, UA["User-Agent"], headers=dict(UA),
                        label="mi-mi-grand-rapids-council-scraper")
    req = urllib.request.Request(url, headers=dict(UA))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", "replace")
    if "Just a moment" in body or "cf_chl" in body:
        raise RuntimeError("the city has started challenging this client — see the "
                           "Detroit scraper next door for the Archive rung")
    return body


def flat(fragment):
    t = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", fragment)
    t = htmllib.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t).strip()


ADDRESS_RE = re.compile(r"(\d{2,4}\s+Monroe\s+Avenue\s+NW)\s+(Grand Rapids,\s*Michigan\s+\d{5})")
PHONE_RE = re.compile(r"\b(\d{3}\.\d{3}\.\d{4})\b")
EMAIL_RE = re.compile(r"\b([\w.\-+]+@[\w.\-]+\.[A-Za-z]{2,})\b")
WARD_RE = re.compile(r"\bWard\s*(\d)\b")


def parse_listing(page):
    """The member set and the page's own role grouping — the cross-check."""
    slugs, roles = [], {}
    for m in re.finditer(r'href="(%s([a-z0-9\-]+)/)"' % re.escape(MEMBER_PREFIX), page):
        if m.group(2) not in slugs:
            slugs.append(m.group(2))
    if not slugs:
        fail("no commissioner links on %s — the page has been restructured" % LISTING)
    # Role labels as the listing groups them, paired with the NAME that follows
    # them in the rendered text. Used only to CONFIRM each member page's own
    # ward.
    #
    # PAIRING THE ROLE WITH THE NEXT LINK IS WRONG AND LOOKS RIGHT, which the
    # first draft here did: in this page's DOM a role label sits near an anchor
    # that is not its own, so "Ward 1 Commissioner" resolved to Marshall
    # Kilgore, who is Ward 3. That is the Franklin County grid trap — a role in
    # the column before its own row's name — and it was caught only because the
    # member pages disagreed. The rendered ORDER is what holds: each role line
    # is immediately followed by that member's name.
    text = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", page)
    text = htmllib.unescape(re.sub(r"<[^>]+>", "\n", text))
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for i, line in enumerate(lines):
        if re.fullmatch(r"Ward\s*\d\s*Commissioner|Mayor of Grand Rapids", line):
            if i + 1 < len(lines):
                nxt = re.sub(r"^Mayor\s+", "", lines[i + 1]).strip()
                roles.setdefault(nxt, line)
    body = flat(page)
    if "consists of the Mayor and six Commissioners" not in body:
        fail("the city's own composition sentence is gone from the commission page — "
             "re-read it before trusting the %d-seat arithmetic here" % EXPECT_SEATS)
    return slugs, roles


def parse_member(slug, page):
    h1 = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", page)
    if not h1:
        fail("%s has no <h1> — cannot read a name" % slug)
    name = flat(h1.group(1))
    body = flat(page)

    is_mayor = "Mayor of Grand Rapids" in body
    wards = sorted(set(WARD_RE.findall(body)))
    ward = None
    if not is_mayor:
        if len(wards) != 1:
            fail("%s names %d distinct wards (%s) — a member page must name exactly one"
                 % (slug, len(wards), wards))
        ward = wards[0]

    emails = sorted(set(EMAIL_RE.findall(page)))
    phones = sorted(set(PHONE_RE.findall(page)))
    if not phones:
        fail("%s carries no phone at all" % slug)
    return {"slug": slug, "name": name, "ward": ward, "isMayor": is_mayor,
            "emails": emails, "phones": phones,
            "profileUrl": SITE + MEMBER_PREFIX + slug + "/"}


def fetch_vacancy(ward):
    """The stated cause of one ward's vacancy, from the city's own post.

    Returns a dict or None. NEVER raises for a missing or changed post: a
    vacancy this cannot verify simply does not ship, and the card falls back to
    saying the seat is not listed — which is still true. What it must not do is
    keep asserting a resignation the city has stopped describing."""
    src = VACANCY_SOURCES.get(ward)
    if not src:
        return None
    try:
        page = get(src["url"])
    except Exception as exc:                          # noqa: BLE001 — an absent post is data
        print("  vacancy source for ward %s unreadable (%s) — shipping the neutral "
              "wording instead" % (ward, exc), file=sys.stderr)
        return None
    body = flat(page)
    if src["ordinal"] not in body:
        print("  vacancy source for ward %s no longer names %r — not shipping it"
              % (ward, src["ordinal"]), file=sys.stderr)
        return None
    m = RESIGNATION_RE.search(body)
    if not m:
        print("  vacancy source for ward %s no longer states the cause — not shipping it"
              % ward, file=sys.stderr)
        return None
    # Against the RAW page, because the anchor is the markup: flattening the
    # tags away is exactly what made the old page-wide search possible.
    d = POST_DATE_RE.search(page)
    if not d:
        print("  vacancy source for ward %s carries no date element — shipping the "
              "vacancy without a date rather than guessing one from the page"
              % ward, file=sys.stderr)
    return {"ward": ward, "cause": "resignation", "predecessor": m.group(1).strip(),
            "postedOn": d.group(1) if d else None, "sourceUrl": src["url"]}


def detect_switchboard(members):
    """The number on EVERY member page belongs to the body, not to anyone on it.

    Refuses rather than guessing when there is not exactly one such number: a
    per-member line hoisted onto all seven would read as several direct lines
    that are not, and hoisting nothing would leave the body unreachable."""
    common = set(members[0]["phones"])
    for m in members[1:]:
        common &= set(m["phones"])
    if len(common) != 1:
        fail("%d phone numbers appear on every member page (%s) — exactly one is "
             "expected, and this hoists the body's switchboard rather than guessing "
             "which of several belongs to whom" % (len(common), sorted(common)))
    return common.pop()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()

    print("Fetching Grand Rapids's commission listing…", file=sys.stderr)
    try:
        listing = get(LISTING)
    except (urllib.error.URLError, RuntimeError, OSError) as exc:
        fail("could not read %s: %s" % (LISTING, exc))
    slugs, roles = parse_listing(listing)
    print("  %d commissioner page(s) linked" % len(slugs), file=sys.stderr)

    members = []
    for slug in slugs:
        url = SITE + MEMBER_PREFIX + slug + "/"
        try:
            page = get(url)
        except (urllib.error.URLError, RuntimeError, OSError) as exc:
            fail("could not read %s: %s" % (url, exc))
        rec = parse_member(slug, page)
        # The Douglas rule: a listing's own labelling is a cross-check on the
        # member's page, never a substitute for it. Keyed by NAME, because the
        # listing's role labels do not sit next to their own member's link.
        label = roles.get(rec["name"])
        if label:
            want = None if label.startswith("Mayor") else WARD_RE.search(label).group(1)
            got = None if rec["isMayor"] else rec["ward"]
            if want != got:
                fail("the listing files %s under %r while their own page says %s — "
                     "the two surfaces disagree and neither is assumed right"
                     % (rec["name"], label, "Mayor" if rec["isMayor"] else "Ward " + str(got)))
        members.append(rec)
        print("    %-24s %s" % (rec["name"], "Mayor" if rec["isMayor"] else "Ward " + rec["ward"]),
              file=sys.stderr)
        time.sleep(PAUSE_S)

    matched = [m for m in members if m["name"] in roles]
    if len(matched) != len(members):
        fail("the listing's role labels covered %d of %d members (missing %s) — the "
             "cross-check is not optional, because each member page's ward is the only "
             "other place the ward is stated"
             % (len(matched), len(members),
                [m["name"] for m in members if m["name"] not in roles]))

    switchboard = detect_switchboard(members)
    for m in members:
        direct = [p for p in m["phones"] if p != switchboard]
        if len(direct) > 1:
            fail("%s carries %d numbers besides the switchboard (%s) — one direct line "
                 "is expected and this will not choose" % (m["name"], len(direct), direct))
        m["phone"] = direct[0] if direct else None
        m["email"] = m["emails"][0] if len(m["emails"]) == 1 else None
        if len(m["emails"]) > 1:
            fail("%s's page carries %d e-mail addresses (%s) — one is expected and this "
                 "will not choose" % (m["name"], len(m["emails"]), m["emails"]))
        del m["phones"], m["emails"]

    mayors = [m for m in members if m["isMayor"]]
    if len(mayors) != 1:
        fail("%d mayors found, expected 1" % len(mayors))
    for w in EXPECT_WARDS:
        n = len([m for m in members if m["ward"] == w])
        if n > COMMISSIONERS_PER_WARD:
            fail("ward %s has %d commissioners, more than the %d the city's charter "
                 "arithmetic allows" % (w, n, COMMISSIONERS_PER_WARD))

    # City Hall, as printed in the footer of every page this scrape read. Taken
    # from the LISTING rather than a member page so it is the body's own page
    # that supplies it, and shipped only if every member page agrees with it.
    addr = ADDRESS_RE.search(flat(listing))
    address = [addr.group(1), addr.group(2)] if addr else None
    if address is None:
        print("  note: no City Hall address found in the page footer; the card will "
              "carry the switchboard alone", file=sys.stderr)

    # A vacancy is looked up only for a ward the roster actually shows short, so
    # a recorded source cannot outlive the shortfall it explains.
    vacancies = {}
    for w in EXPECT_WARDS:
        held = len([m for m in members if m["ward"] == w])
        if held < COMMISSIONERS_PER_WARD:
            v = fetch_vacancy(w)
            if v:
                vacancies[w] = v
                print("    ward %s short %d of %d — vacancy verified: %s, %s"
                      % (w, held, COMMISSIONERS_PER_WARD, v["cause"], v["predecessor"]),
                      file=sys.stderr)
            else:
                print("    ward %s short %d of %d — no verified cause; the card will say "
                      "only that the seat is not listed" % (w, held, COMMISSIONERS_PER_WARD),
                      file=sys.stderr)

    payload = {"sourceUrl": LISTING, "seats": EXPECT_SEATS,
               "switchboard": switchboard, "address": address,
               "vacancies": vacancies, "members": members}
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    print("Wrote %s — %d of %d seats named, switchboard %s"
          % (CACHE, len(members), EXPECT_SEATS, switchboard), file=sys.stderr)


if __name__ == "__main__":
    main()
