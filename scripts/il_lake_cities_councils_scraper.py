#!/usr/bin/env python3
"""Read six Lake County cities' own council pages into municipal-officials payloads.

WHY LAKE COUNTY GETS ITS OWN FILE. The fourth test of the done standard
(`docs/DONE_STANDARD.md`) asks that every general-purpose local government above
25,000 people name a governing body. Measured 2026-10-01, eight Illinois units
above that line named nobody, and SEVEN of the eight are in Lake County. That is
not a coincidence: Lake is in the municipal pipeline at the CONTACT-ONLY rung —
the county's open data portal publishes a hall address, telephone and website
for all 41 of its municipalities and names not one official — so every Lake
municipality above the line arrives with an address and no people.

`scripts/il_large_city_councils_scraper.py` says in as many words that "seven
city sites is past any bounded exception, so Lake wants its own decision rather
than a quiet seventh entry here", and left them out. This file IS that decision,
taken on 2026-10-01 after the eight were measured one by one: the county's own
source cannot be deepened (it is a boundary feed with contact attributes, not a
directory), the Lake County Municipal League republishes exactly the same
address and telephone, and the standard now requires these seven.

So this is the GALESBURG SHAPE applied to a whole county at once — a county with
no municipal officials source at all — and it is bounded the same way: the
places are named in `PRESERVABLE`, one at a time, and an eighth city cannot be
added by this file alone.

SIX OF SEVEN, AND GURNEE IS THE SEVENTH. Gurnee's board page
(`gurneeil.gov/government/village_board/index.php`) reads "Current Village Board
members are listed below:" and then lists nobody: measured 2026-10-01, 189,943
bytes of served HTML containing the word Trustee exactly once, in the sentence
describing the terms. Its appointed-officials page and its "how to write your
officials" page name no trustee either, and the site publishes no sitemap. The
names are evidently rendered by a component this client is not served. That is a
measured absence, recorded as the gap `gurnee-village-board-names` with an ask
drafted for the operator, and NOT worked around.

FETCH CLASS, MEASURED 2026-10-01 WITH THE CLIENT THIS FILE SENDS. All six hosts
answer `requests` plus the districtry token with HTTP 200 and a full page. No
browser string is needed anywhere here and none is sent.

ROBOTS. Each host's policy is read once, by `require_robots_once`, with the
exact client this file crawls with. Measured 2026-10-01: all six serve a
robots.txt and none disallows the paths read here. Two pairs share a CMS
vendor's default file published at each city's own host — it binds for that
reason and is never cited as something the city chose.

TWO HOSTS REDIRECT TO A DIFFERENT DOMAIN and the policy is read at the
destination, not at the name in a directory: `gurnee.il.us` answers from
`gurneeil.gov` and `villageofroundlakebeach.com` from `roundlakebeachil.gov`.
Asking the first host and fetching the second is the wrong-address defect this
repository has already paid for sixty times over.

WHAT EACH PAGE PUBLISHES.

  Highland Park     An index linking one page per member. The council is read
                    from those links rather than from the body, and the mayor's
                    link is the one whose text begins "Mayor". Elected at large,
                    so there is no district to draw. ONE NAME CARRIES AN ACCENT
                    IN ITS OWN URL (`andrés_tapia.php`): a first draft's
                    character class dropped it silently and shipped five of six,
                    which is why the floor is six and not "about six".
  Mundelein         The staff directory, whose Elected Officials entries read
                    "<name> <role> <role> Elected Officials Email <name>
                    <telephone>". Elected at large.
  North Chicago     A council table of "Ward N / <name> / [direct line] /
                    Alderman / <e-mail> / <hall line> .ext N". Seven wards. The
                    extension is dropped with the hall line it belongs to, so a
                    member with no second number ships none rather than shipping
                    the switchboard under their name.
  Round Lake Beach  The village board page names six trustees as "<name>,
                    Trustee"; the mayor is on his own page. Elected at large.
  Vernon Hills      The elected-officials directory, "<name> <role> <role>
                    <e-mail> <telephone>". Elected at large. 847-367-3700 is the
                    village switchboard and stands against four of the seven
                    names, so a per-person value equal to it is dropped.
  Waukegan          A council page of "<N>th Ward Alderperson / <NAME> / Term:
                    <from> - <to>" over nine wards, with the mayor on the city
                    officials page. THE NAMES ARE PUBLISHED IN CAPITALS and are
                    title-cased for display, which is a rendering decision about
                    letter case and never a correction to anybody's name; the
                    run prints every name it re-cases.

Usage:
    python3 scripts/il_lake_cities_councils_scraper.py --out-dir /tmp
    python3 scripts/il_lake_cities_councils_scraper.py --out-dir /tmp --only waukegan
"""

import argparse
import datetime
import html
import json
import os
import re
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_common import UA_ROSTER_BOT, require_robots_once  # noqa: E402

HEADERS = {"User-Agent": UA_ROSTER_BOT}
TIMEOUT = 60
ATTEMPTS = 4

ORDINAL = re.compile(r"^(\d+)(?:st|nd|rd|th)$", re.I)


def now():
    return (datetime.datetime.now(datetime.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"))


def get(url):
    """One paced GET with retries, through the client this file declares."""
    last = None
    for attempt in range(ATTEMPTS):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:          # noqa: BLE001 — retried, then raised
            last = exc
            if attempt + 1 < ATTEMPTS:
                import time
                time.sleep(1.5 * (attempt + 1))
    raise last


def visible(markup):
    t = re.sub(r"(?is)<(script|style).*?</\1>", "\n", markup)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", t))
    # A NON-BREAKING SPACE IS NOT A SPACE TO `re`, and Waukegan prints
    # "Term:&nbsp; May 2023" — a first draft read one alderperson of nine
    # because `Term: ?` could not cross it.
    t = t.replace("\u00a0", " ")
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r"\s*\n\s*", "\n", t)
    return re.sub(r"\n{2,}", "\n", t)


def clean(value):
    if not value:
        return None
    value = " ".join(str(value).split())
    return value or None


def recase(name, warn):
    """Title-case a name a city publishes in capitals, and say that we did.

    This is a decision about LETTER CASE in a display string and nothing else:
    no letter is added, removed or changed. A name that is not shouting is
    returned untouched, so a city that stops shouting needs no edit here.
    """
    name = clean(name)
    if not name or not name.isupper():
        return name
    out = []
    for word in name.split():
        if re.fullmatch(r"[IVX]+\.?", word):          # Henry IV, not Henry Iv
            out.append(word)
        elif word in ("MD", "MMC", "JD"):
            out.append(word)
        else:
            out.append(word.title())
    fixed = " ".join(out)
    warn("re-cased a name the city publishes in capitals: %r -> %r"
         % (name, fixed))
    return fixed


def phone(raw, city=None):
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None
    number = "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])
    if city and number in city.get("shared_lines", ()):
        return None
    # The hall's own switchboard printed in a person's row: a way to reach the
    # office, which the card already names, and not a way to reach the person.
    if city and number == city["office"].get("office_phone"):
        return None
    return number


def record(city, office, name, district=None, person_phone=None,
           person_email=None, term=None, source_url=None):
    return dict(
        city["office"],
        jurisdiction=city["jurisdiction"],
        office=office,
        district=district,
        name=clean(name),
        person_phone=person_phone,
        person_email=person_email,
        term=term,
        source_url=source_url or city["page"],
        scraped_at=now(),
    )


# ------------------------------------------------------------- Highland Park

HP_SKIP = {"index", "city_council_recap", "council_meeting_agendas_minutes"}
HP_LINK = re.compile(
    r'href="([^"]*mayor_and_city_council/([^"/]+)\.php)"[^>]*>(.*?)</a>',
    re.S | re.I)


def read_highland_park(city, warn):
    markup = get(city["page"])
    out, seen = [], set()
    for match in HP_LINK.finditer(markup):
        slug = match.group(2)
        text = clean(html.unescape(re.sub(r"<[^>]+>", "", match.group(3))))
        if slug in HP_SKIP or not text or slug in seen:
            continue
        seen.add(slug)
        is_mayor = text.lower().startswith("mayor ")
        name = text[6:] if is_mayor else text
        out.append(record(
            city, "Mayor" if is_mayor else "Council Member", name,
            district=None if is_mayor else "At Large",
            source_url="https://www.cityhpil.com/government/"
                       "mayor_and_city_council/%s.php" % slug))
    return out


# ----------------------------------------------------------------- Mundelein

MUNDELEIN_RE = re.compile(
    r"\n([A-Z][\w.'’-]+(?: [A-Z][\w.'’-]+){1,3})\n"
    r"(Trustee|Mayor|Village President)\n\2\n"
    r"Elected Officials\n"
    # THE TELEPHONE IS OPTIONAL. One trustee publishes an e-mail link and no
    # number, and a required group dropped her silently — six of seven, caught
    # by the floor and not by eye.
    r"Email \1(?:\n([0-9()\- .]{10,20}))?(?=\n)")


def read_mundelein(city, warn):
    text = visible(get(city["page"]))
    out, seen = [], set()
    for match in MUNDELEIN_RE.finditer(text):
        name, role, tel = clean(match.group(1)), match.group(2), match.group(3)
        if name in seen:
            continue
        seen.add(name)
        head = role != "Trustee"
        out.append(record(
            city, "Mayor" if head else "Trustee", name,
            district=None if head else "At Large",
            person_phone=phone(tel, city)))
    return out


# ------------------------------------------------------------- North Chicago

NC_RE = re.compile(
    r"\nWard (\d+)\n"
    r"([A-Z][\w.'’-]+(?: [A-Z][\w.'’-]+){1,3})\n"
    r"(?:([0-9()\- .]{10,20})\n)?"
    r"(?:Alderman|Alderperson)\n"
    r"([^\s@]+@[^\s@]+)\n"
    r"([0-9()\- .]{10,20})")
NC_MAYOR_RE = re.compile(r"Mayor ([A-Z][\w.'’, -]{3,40}?) - ")


def read_north_chicago(city, warn):
    text = visible(get(city["page"]))
    out, seen = [], set()
    for match in NC_RE.finditer(text):
        ward = int(match.group(1))
        if ward in seen:
            continue
        seen.add(ward)
        out.append(record(
            city, "Alderman", match.group(2), district="Ward %d" % ward,
            # Group 3 is a direct line where the member publishes one; group 5
            # is the hall's switchboard with that ward's extension, which
            # `phone` drops as the office number it is.
            person_phone=phone(match.group(3), city)
                         or phone(match.group(5), city),
            person_email=clean(match.group(4))))
    mayor_page = "https://www.northchicago.org/government/mayor.php"
    found = NC_MAYOR_RE.search(visible(get(mayor_page)))
    if found:
        out.append(record(city, "Mayor", found.group(1),
                          source_url=mayor_page))
    else:
        warn("north-chicago: the mayor's page no longer introduces the mayor "
             "in its heading — nobody is shipped for that seat")
    return out


# ---------------------------------------------------------- Round Lake Beach

RLB_RE = re.compile(
    r"\n([A-Z][\w.'’-]+(?: [A-Z][\w.'’-]+){1,3}), Trustee(?=\n)")
RLB_MAYOR_RE = re.compile(r"\nMayor ([A-Z][\w.'’-]+(?: [A-Z][\w.'’-]+){1,3})\n")


def read_round_lake_beach(city, warn):
    text = visible(get(city["page"]))
    out, seen = [], set()
    for match in RLB_RE.finditer(text):
        name = clean(match.group(1))
        if name in seen:
            continue
        seen.add(name)
        out.append(record(city, "Trustee", name, district="At Large"))
    mayor_page = "https://www.roundlakebeachil.gov/government/mayor/index.php"
    found = RLB_MAYOR_RE.search(visible(get(mayor_page)))
    if found:
        out.append(record(city, "Mayor", found.group(1),
                          source_url=mayor_page))
    else:
        warn("round-lake-beach: the mayor's page no longer names the mayor in "
             "its navigation — nobody is shipped for that seat")
    return out


# -------------------------------------------------------------- Vernon Hills

VH_RE = re.compile(
    r"\n([A-Z][\w.'’-]+(?:[. ]+[A-Z][\w.'’-]+){1,3})\n"
    r"(Trustee|Village President|Mayor)\n\2\n"
    r"([^\s@]+@[^\s@]+)\n"
    r"([0-9()\- .]{10,20})(?=\n)")


def read_vernon_hills(city, warn):
    text = visible(get(city["page"]))
    out, seen = [], set()
    for match in VH_RE.finditer(text):
        name, role = clean(match.group(1)), match.group(2)
        if name in seen:
            continue
        seen.add(name)
        head = role != "Trustee"
        out.append(record(
            city, "Village President" if head else "Trustee", name,
            district=None if head else "At Large",
            person_email=clean(match.group(3)),
            person_phone=phone(match.group(4), city)))
    return out


# ------------------------------------------------------------------ Waukegan

WK_RE = re.compile(
    r"\n(\d+)(?:st|nd|rd|th) Ward Alderperson\n"
    r"([A-Z][A-Z.'’ ,-]{3,44}?)\n"
    r"Term: ?([A-Za-z]+ \d{4} ?- ?[A-Za-z]+ \d{4})")
WK_MAYOR_RE = re.compile(
    r"\nMayor\n([A-Z][\w.'’ ,-]{3,44}?)\n"
    r"Term: ?([A-Za-z]+ \d{4} ?- ?[A-Za-z]+ \d{4})")


def read_waukegan(city, warn):
    text = visible(get(city["page"]))
    out, seen = [], set()
    for match in WK_RE.finditer(text):
        ward = int(match.group(1))
        if ward in seen:
            continue
        seen.add(ward)
        out.append(record(
            city, "Alderperson", recase(match.group(2), warn),
            district="Ward %d" % ward,
            term=" ".join(match.group(3).split())))
    officials = "https://www.waukeganil.gov/187/City-Officials"
    found = WK_MAYOR_RE.search(visible(get(officials)))
    if found:
        out.append(record(city, "Mayor", recase(found.group(1), warn),
                          term=" ".join(found.group(2).split()),
                          source_url=officials))
    else:
        warn("waukegan: the city officials page no longer prints the mayor "
             "above a term — nobody is shipped for that seat")
    return out


CITIES = {
    "highland-park": {
        "jurisdiction": "City of Highland Park",
        "county": "Lake",
        "page": "https://www.cityhpil.com/government/"
                "mayor_and_city_council/index.php",
        "office": {"office_address": "1707 St. Johns Ave.",
                   "office_city": "Highland Park", "office_state": "IL",
                   "office_zip": "60035", "office_phone": "847-432-0800",
                   "office_email": None},
        "read": read_highland_park,
        # Mayor and six council members, all elected at large.
        "min_officials": 7, "min_districts": 0, "min_heads": 1,
    },
    "mundelein": {
        "jurisdiction": "Village of Mundelein",
        "county": "Lake",
        "page": "https://www.mundelein.org/directory.aspx",
        "office": {"office_address": "300 Plaza Circle",
                   "office_city": "Mundelein", "office_state": "IL",
                   "office_zip": "60060", "office_phone": "847-949-3200",
                   "office_email": None},
        "read": read_mundelein,
        # Mayor and six trustees, all elected at large.
        "min_officials": 7, "min_districts": 0, "min_heads": 1,
    },
    "north-chicago": {
        "jurisdiction": "City of North Chicago",
        "county": "Lake",
        "page": "https://www.northchicago.org/government/"
                "city_council/index.php",
        "office": {"office_address": "1850 Lewis Avenue",
                   "office_city": "North Chicago", "office_state": "IL",
                   "office_zip": "60064", "office_phone": "847-596-8889",
                   "office_email": None},
        "read": read_north_chicago,
        # Mayor and one alderman in each of seven wards.
        "min_officials": 8, "min_districts": 7, "min_heads": 1,
    },
    "round-lake-beach": {
        "jurisdiction": "Village of Round Lake Beach",
        "county": "Lake",
        "page": "https://www.roundlakebeachil.gov/government/"
                "village_board_2.php",
        "office": {"office_address": "1937 N. Municipal Way",
                   "office_city": "Round Lake Beach", "office_state": "IL",
                   "office_zip": "60073", "office_phone": "847-546-2351",
                   "office_email": None},
        "read": read_round_lake_beach,
        # Mayor and six trustees, all elected at large.
        "min_officials": 7, "min_districts": 0, "min_heads": 1,
    },
    "vernon-hills": {
        "jurisdiction": "Village of Vernon Hills",
        "county": "Lake",
        "page": "https://www.vernonhills.org/directory.aspx?did=11",
        "office": {"office_address": "290 Evergreen Drive",
                   "office_city": "Vernon Hills", "office_state": "IL",
                   "office_zip": "60061", "office_phone": "847-367-3700",
                   "office_email": None},
        "shared_lines": ("847-367-3700",),
        "read": read_vernon_hills,
        # Village President and six trustees, all elected at large.
        "min_officials": 7, "min_districts": 0, "min_heads": 1,
    },
    "waukegan": {
        "jurisdiction": "City of Waukegan",
        "county": "Lake",
        "page": "https://www.waukeganil.gov/188/Council-Members",
        "office": {"office_address": "100 N. Martin Luther King Jr. Ave.",
                   "office_city": "Waukegan", "office_state": "IL",
                   "office_zip": "60085", "office_phone": "847-599-2500",
                   "office_email": None},
        "read": read_waukegan,
        # Mayor and one alderperson in each of nine wards.
        "min_officials": 10, "min_districts": 9, "min_heads": 1,
    },
}


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--only", choices=sorted(CITIES))
    args = ap.parse_args()

    wanted = [args.only] if args.only else sorted(CITIES)
    problems = []
    for key in wanted:
        city = CITIES[key]
        warnings = []
        require_robots_once(city.get("robots_url", city["page"]),
                            HEADERS["User-Agent"], headers=HEADERS,
                            label="il-%s-council-scraper" % key)
        officials = city["read"](city, warnings.append)
        districts = sum(1 for r in officials
                        if r["district"] and r["district"] != "At Large")
        heads = sum(1 for r in officials
                    if r["office"] in ("Mayor", "Village President"))
        trouble = []
        if len(officials) < city["min_officials"]:
            trouble.append("%d officials < floor %d"
                           % (len(officials), city["min_officials"]))
        if districts < city["min_districts"]:
            trouble.append("%d ward or district seats < floor %d"
                           % (districts, city["min_districts"]))
        if heads < city["min_heads"]:
            trouble.append("%d heads < floor %d" % (heads, city["min_heads"]))
        for warning in warnings:
            print("  warning: %s" % warning, file=sys.stderr)
        if trouble:
            problems.append("%s: %s" % (key, "; ".join(trouble)))
            continue
        stamp = now()
        payload = {
            "county": city["county"],
            "kind": "municipal-enrichment",
            "directory_url": city["page"],
            "officials_page": city["page"],
            "scraped_at": stamp,
            "municipalities": [{"name": city["jurisdiction"],
                                "source_url": city["page"],
                                "scraped_at": stamp}],
            "officials": officials,
        }
        out = os.path.join(args.out_dir, "%s_council.json" % key)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        print("scraped %s: %d officials (%d seated by ward or district, %d head)"
              " -> %s" % (city["jurisdiction"], len(officials), districts,
                          heads, out), file=sys.stderr)

    if problems:
        raise SystemExit("il-lake-cities-councils: " + "; ".join(problems)
                         + " — refusing to write")


if __name__ == "__main__":
    main()
