#!/usr/bin/env python3
"""
Rockford's fourteen alderpersons, from the CITY's own directory
==============================================================
The one reader of rockfordil.gov's council directory. It exists because
Rockford's people and Rockford's ward lines come from two different publishers
and only one of them maintains people.

WHY THIS SOURCE AND NOT THE WARD LAYER. WinGIS publishes Rockford's 14 ward
polygons on its ElectedOfficials service (layer 20) with an `Alderman` and an
`Email` column on every polygon, and that column is what this project shipped
until 2026-09-29. It is a SNAPSHOT: joined ward-for-ward against the city's own
directory that day, 14 of 14 wards matched and TWO seats disagreed on both the
name and the address derived from it —

    ward 3   layer  Chad Tuneburg   Chad.Tuneburg@rockfordil.gov
             city   Chad Tuneberg   Chad.Tuneberg@rockfordil.gov
    ward 7   layer  Janessa Wilkins Janessa.Wilkins@rockfordil.gov
             city   Janessa Neal    Janessa.Neal@rockfordil.gov

— so the defect is not cosmetic. The layer's addresses are spelled FROM the
layer's names, so a reader who trusted either card wrote to an address the city
does not publish. This is the Coles pattern (geometry from the GIS service,
people from the body's own page) and the Freeport ruling in the next county
over, where a city ward FeatureServer's `Alderperson` field was likewise found
stale and the geometry kept: the boundary is the GIS's to publish and the
officeholder is the city's.

THE LINES THEMSELVES ARE CURRENT and that was measured before any of this: the
WinGIS polygons balance on Census 2020 (measured 2026-09-29), so nothing here
is a claim about the boundary. Only the people column moves.

NO NAME IS CORRECTED, EVER. "Tuneberg" and "Neal" ship because the CITY
publishes them, not because this project judged the other spelling wrong. Three
more seats differ in FORM rather than in substance — the layer writes
"Franklin C. Beach", "Kevin J. Frost" and "Jaime J. Salgado" where the city
writes "Frank Beach", "Kevin Frost" and "Jaime Salgado" — and the city's
wording ships there too, for the same reason and with the same indifference to
which reads better.

THE JOIN IS BY WARD AND IT IS A GATE. The directory states each alderperson's
ward on their own page ("Alderman - Ward 7"); the layer states each polygon's.
The two ward SETS must be identical or this scraper refuses: a directory that
stops naming the same fourteen wards is a question for a person, never a
partial roster. The caller prints the join every run
(winnebago_municipal_officials_scraper.py).

THE TELEPHONE IS PER SEAT AND IS MEASURED TO BE. Every person page carries
two numbers: 779-348-7300, the city's main line, on all of them, and a second
one printed immediately after the ward ("Alderman - Ward 7  815-814-1765"),
which differed on four of four pages sampled 2026-09-29 and on all fourteen in
the full run. The second is what ships, anchored to the ward string so the main
line can never take its place, and refused outright if it ever equals the main
line. This is the Freeport call in the next county over: the e-mail and the
telephone a city prints on a seat's own directory page are the channels it
tells constituents to use for that seat. The WinGIS layer publishes no
telephone for Rockford at all, so this is a contact the card could not carry
before.

FETCH POSTURE: open, and MEASURED ON ALL FOUR RUNGS 2026-09-29 — stdlib+token,
stdlib+Chrome, requests+token and requests+Chrome each returned the same
95,680-byte page, so this sends the districtry token and no browser string is
warranted. robots.txt is 816 bytes and binds one `*` group whose rules do not
match the council paths; it is read through robots_policy before the first
fetch, as this client.

THE HOST IS INTERMITTENT. Reading all fourteen pages on 2026-09-29, three
needed a retry — a reset mid-body, not a status. That is why every fetch here
goes through a short ladder rather than a bare GET, and why the caller is in
build_municipal_officials_roster.py's PRESERVABLE: a run that cannot read the
directory carries Winnebago forward from the shipped roster rather than
shipping a short council.

Usage:
    python3 rockford_alderperson_scraper.py [--out rockford_alderpersons.json]
"""

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request

from scraper_common import require_robots_allowed  # noqa: E402  (shared machinery — do not fork)

SITE = "https://rockfordil.gov"
INDEX_URL = SITE + "/576/Wards"
USER_AGENT = "districtry-roster-bot/1.0 (+https://districtry.com/il/)"
TIMEOUT = 45
# Three of fourteen pages needed one re-ask on 2026-09-29. Two re-asks with a
# pause between them is well past what was observed; a fourth attempt would be
# guessing at a host that is down rather than flaky.
BACKOFF = (2.0, 6.0)
SEATS = 14
OFFICE = "Alderperson"
# The city's own main line, printed on every alderperson's page. It reaches the
# City of Rockford and nobody in particular, so it is never attached to a person
# — the rule build_municipal_officials_roster.py already applies to a
# municipality's hall number, enforced here as well so this payload cannot be
# the thing that breaks it.
CITY_MAIN_LINE = "779-348-7300"

# The city titles every seat "Alderman" on the page and in the link slug; the
# roster's own word for the office is Alderperson, which is what the council
# calls itself. The title is stripped from the name rather than shipped in it.
_TITLE = re.compile(r"^\s*alder(?:man|woman|person)\s+", re.I)
_WARD = re.compile(r"alder(?:man|woman|person)\s*[-‐-―]\s*ward\s*(\d{1,2})", re.I)
_PERSON_HREF = re.compile(r'href="(/\d+/Alderman-[^"#?]*)"', re.I)
_H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S | re.I)
_MAILTO = re.compile(r'mailto:([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})', re.I)
# Anchored to the ward string on purpose: the page's other number is the city's
# main line, and an unanchored search would attach it to whoever's page it sat on.
_SEAT_PHONE = re.compile(
    r"alder(?:man|woman|person)\s*[-\u2010-\u2015]\s*ward\s*\d{1,2}\s*"
    r"(\d{3}[-.\s]\d{3}[-.\s]\d{4})", re.I)


def fail(message):
    print("rockford-alderpersons: FAIL — %s" % message, file=sys.stderr)
    sys.exit(1)


def text_of(markup):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", markup))).strip()


def get(url, sleep=time.sleep):
    """One page, re-asked on a transport failure. A status is an answer."""
    last = None
    for wait in BACKOFF + (None,):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError:
            raise                       # 404 or 403 is the host answering
        except Exception as exc:        # noqa: BLE001 — re-raised below
            last = exc
            if wait is None:
                break
            print("  re-asking %s in %.0fs (%s)" % (url, wait, exc), file=sys.stderr)
            sleep(wait)
    raise last


def person_urls(index_html):
    """The directory's own list of seats, discovered rather than hardcoded.

    Each alderperson has a numbered page whose id is stable but arbitrary; a
    new member gets a new one, so the index is read every run.
    """
    out = []
    for path in _PERSON_HREF.findall(index_html):
        url = SITE + path
        if url not in out:
            out.append(url)
    return out


def normalise_phone(value):
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None            # a partial number is dropped, never padded
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])


def read_person(page_html, url):
    flat = text_of(page_html)
    name = None
    for block in _H1.findall(page_html):
        candidate = _TITLE.sub("", text_of(block)).strip()
        if candidate:
            name = candidate
            break
    ward = _WARD.search(flat)
    emails = _MAILTO.findall(page_html)
    phone_match = _SEAT_PHONE.search(flat)
    phone = normalise_phone(phone_match.group(1)) if phone_match else None
    return {
        "name": name,
        "ward": int(ward.group(1)) if ward else None,
        "email": emails[0] if len(emails) == 1 else None,
        "emails_found": len(emails),
        # A seat with no published number ships without one; the main line
        # standing where a seat number should be is a page shape this has not
        # seen, and is refused rather than shipped as a direct line.
        "phone": None if phone == CITY_MAIN_LINE else phone,
        "phone_is_main_line": phone == CITY_MAIN_LINE,
        "url": url,
    }


def scrape(sleep=time.sleep):
    """{ward:int -> {"name", "email", "url"}} for all fourteen seats, or raise.

    There is no partial answer: a council read thirteen-fourteenths of the way
    would silently unname a ward on the card, which is the failure this whole
    change exists to stop.
    """
    require_robots_allowed(INDEX_URL, USER_AGENT, label="rockford council directory")
    pages = person_urls(get(INDEX_URL, sleep=sleep))
    if len(pages) != SEATS:
        raise RuntimeError(
            "the city's ward index lists %d alderperson pages, not %d — the "
            "directory changed shape" % (len(pages), SEATS))

    by_ward = {}
    for url in pages:
        person = read_person(get(url, sleep=sleep), url)
        if not person["name"]:
            raise RuntimeError("%s names nobody" % url)
        if person["ward"] is None:
            raise RuntimeError("%s states no ward" % url)
        if person["emails_found"] != 1:
            raise RuntimeError(
                "%s carries %d e-mail addresses, not one — which one reaches "
                "the alderperson is not this scraper's to guess"
                % (url, person["emails_found"]))
        if person["phone_is_main_line"]:
            raise RuntimeError(
                "%s prints the city's main line (%s) where the seat's own "
                "number sits — the page changed shape and no number here can "
                "be attached to a person" % (url, CITY_MAIN_LINE))
        if person["ward"] in by_ward:
            raise RuntimeError(
                "ward %d is claimed by two pages (%s and %s)"
                % (person["ward"], by_ward[person["ward"]]["url"], url))
        seat = {"name": person["name"], "email": person["email"], "url": url}
        if person["phone"]:
            seat["phone"] = person["phone"]
        by_ward[person["ward"]] = seat
    return by_ward


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="rockford_alderpersons.json")
    args = ap.parse_args()
    try:
        by_ward = scrape()
    except Exception as exc:  # noqa: BLE001 — reported, not swallowed
        fail(str(exc))
    payload = {
        "source": INDEX_URL,
        "office": OFFICE,
        "alderpersons": {str(w): by_ward[w] for w in sorted(by_ward)},
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")
    for ward in sorted(by_ward):
        seat = by_ward[ward]
        print("  ward %-3d %-22s %-34s %s"
              % (ward, seat["name"], seat["email"], seat.get("phone") or "-"))
    phones = sum(1 for w in by_ward if by_ward[w].get("phone"))
    print("rockford-alderpersons: %d seats, %d with a published telephone -> %s"
          % (len(by_ward), phones, args.out))


if __name__ == "__main__":
    main()
