#!/usr/bin/env python3
"""Read five large Illinois cities' own council pages into municipal-officials payloads.

WHY FIVE CITIES AND NOT FIVE COUNTIES. The fourth test of the done standard
(`docs/DONE_STANDARD.md`) asks that every general-purpose local government above
25,000 people name a governing body. Measured 2026-10-01 by
`scripts/build_eam_status.py`, thirteen Illinois units above that line named
nobody. Five of them are the only unit above the line in a county whose
municipal directory this project cannot read at all:

    Champaign  (Champaign County — no county municipal source)
    Decatur    (Macon County     — no county municipal source)
    Normal     (McLean County    — the county source names three villages and
                                   omits the town wholesale)
    Quincy     (Adams County     — no county municipal source)
    Danville   (Vermilion County — no county municipal source)

That is the GALESBURG SHAPE and the FREEPORT SHAPE, the two bounded exceptions
`docs/EXPANSION_GUIDE.md` §3.4 already allows to the rule against scraping
municipal sites: a county with no municipal source at all, and a municipality a
county directory omits wholesale. Nothing here is a sweep — the five places are
named in `PRESERVABLE`, and a sixth city cannot be added by this file alone.

THE OTHER EIGHT ARE NOT HERE AND EACH HAS ITS OWN REASON. Seven are in Lake
County, which IS in the pipeline but at the contact-only rung: the county's open
data portal publishes a hall address for all 41 of its municipalities and names
nobody, and the Lake County Municipal League's member pages were measured on
2026-10-01 and republish exactly the same address and telephone. Seven city
sites is past any bounded exception, so Lake wants its own decision rather than
a quiet seventh entry here. The eighth is Urbana, whose host
`urbanaillinois.us` reset the connection on every attempt from this project's
sandbox on 2026-10-01 (stdlib and `requests`, both clients, www and bare). That
is a measurement of this vantage and not of the city, so it is recorded to be
re-measured from a GitHub runner rather than written up as a refusal.

FETCH CLASS, MEASURED 2026-10-01 WITH THE CLIENT THIS FILE SENDS. All five
hosts answer `requests` + the districtry token with HTTP 200 and a full page
(champaignil.gov 5,284 bytes of JSON; decaturil.gov 109,440; normalil.gov
123,796; quincyil.gov 116,904; cityofdanville.org 132,624). No browser string is
needed anywhere here and none is sent. For contrast, and because it is the
reason Lake stayed contact-only rather than being read from the county site:
`www.lakecountyil.gov` answers the same token 403 on `requests` and 200 on the
stdlib client — the stack, not the name.

ROBOTS. Each host's policy is read once, by `require_robots_once`, with the
exact client this file crawls with. Measured 2026-10-01: all five serve a
robots.txt and none of them disallows the paths read here. Four of the five
serve the same 801-816 byte CivicPlus/Granicus default, which is one CMS
vendor's file published at each city's own host — it binds for that reason and
is never cited as something the city chose.

ADDRESSES. Only the city hall is shipped, as the municipality-level office, and
it is a constant per city read off the city's own contact block. Quincy's
alderman pages print a street address per person — 600 Adams St. on one of them,
which is not the City Hall at 730 Maine St. — and nothing on the page says
whether that is an office or a home. The Madison/Peoria rule applies: an
address that cannot be shown to be an office is not shipped, so none of them is.

WHAT EACH PAGE PUBLISHES, AND THE ONE PARSE THAT IS DELIBERATELY SOFT.

  Champaign  WordPress REST. The member pages are children of the page with
             slug `members`, discovered by slug rather than by its id, so a
             re-publish does not strip the council. Each child's title is the
             name and its body reads "<name> <role> <phone> ... <seat>", the
             seat being "District N", "At Large" or "Deputy Mayor, At Large".
             217-403-8720 is the council's shared line and appears on six of
             nine pages, so a per-person phone equal to it is dropped.
  Decatur    One page, "<name>\\n<Councilman|Councilwoman|Mayor>". Decatur
             elects its council at large, so there is no district to draw.
  Normal     One page whose council block is `data-headertext` on each photo
             widget, the mayor's reading "Mayor <name>". Elected at large.
  Quincy     An index linking one page per alderman; each prints
             "Ward N Alderman" with a direct telephone and e-mail. THE MAYOR IS
             A WARNING AND NOT A FLOOR: the mayor's page introduces her inside a
             first-person letter ("I'm Dr. Linda K. Moore, and it is my honor to
             serve as Mayor"), and a regex against a letter is a parser that
             breaks silently the week the letter is rewritten. So the mayor is
             read if an anchored pattern matches and the run prints a warning
             if it does not; the fourteen aldermen are what the floors hold.
  Danville   One page carrying the mayor and all fourteen aldermen, each with a
             ward and a direct telephone.

Usage:
    python3 scripts/il_large_city_councils_scraper.py --out-dir /tmp
    python3 scripts/il_large_city_councils_scraper.py --out-dir /tmp --only champaign
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

# The council's own shared line, printed on a member page where that member
# publishes no direct number. A per-person value equal to it is the hall line
# wearing a person's name and is dropped (§3.4, "a per-person value equal to
# the hall line is dropped").
SHARED_LINES = {"217-403-8720"}


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
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r"\s*\n\s*", "\n", t)
    return re.sub(r"\n{2,}", "\n", t)


def clean(value):
    if not value:
        return None
    value = " ".join(str(value).split())
    return value or None


def phone(raw, city=None):
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None
    number = "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])
    if number in SHARED_LINES:
        return None
    # The city hall's own switchboard, printed in a person's row. Danville's
    # mayor's row carries exactly this: it is a way to reach the office, which
    # the card already names, and not a way to reach the person.
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


# ---------------------------------------------------------------- Champaign

def read_champaign(city, warn):
    api = "https://champaignil.gov/wp-json/wp/v2/pages"
    parents = json.loads(get(api + "?slug=members"))
    if len(parents) != 1:
        raise SystemExit("champaign: %d pages have the slug `members`, expected "
                         "1 — the council index has moved" % len(parents))
    children = json.loads(get("%s?parent=%d&per_page=100" % (api, parents[0]["id"])))
    out = []
    for page in children:
        name = html.unescape(page["title"]["rendered"])
        body = html.unescape(re.sub(r"\s+", " ",
                                    re.sub(r"<[^>]+>", " ",
                                           page["content"]["rendered"])))
        seat = re.search(r"\b(District \d+|At[- ]Large)\b", body, re.I)
        is_mayor = re.search(re.escape(name) + r"\s+Mayor\b", body) is not None
        tel = re.search(r"\b(\d{3}[-.]\d{3}[-.]\d{4})\b", body)
        term = re.search(r"Serving from (\d{4}) to (\d{4})", body)
        district = None
        if not is_mayor:
            if not seat:
                warn("champaign: %s names no seat — dropped rather than guessed"
                     % name)
                continue
            district = ("At Large" if seat.group(1).lower().startswith("at")
                        else seat.group(1).title())
        out.append(record(
            city, "Mayor" if is_mayor else "Council Member", name,
            district=district,
            person_phone=phone(tel.group(1), city) if tel else None,
            term="%s-%s" % (term.group(1), term.group(2)) if term else None,
            source_url=page["link"],
        ))
    return out


# ------------------------------------------------------------------ Decatur

DECATUR_RE = re.compile(
    r"^([A-Z][A-Za-z.'’-]+(?: [A-Z][A-Za-z.'’-]+){1,3})\n"
    r"(Councilman|Councilwoman|Council Member|Mayor)$", re.M)


def read_decatur(city, warn):
    text = visible(get(city["page"]))
    out, seen = [], set()
    for match in DECATUR_RE.finditer(text):
        name, role = clean(match.group(1)), match.group(2)
        if name in seen:
            continue
        seen.add(name)
        out.append(record(
            city, "Mayor" if role == "Mayor" else "Council Member", name,
            district=None if role == "Mayor" else "At Large"))
    return out


# ------------------------------------------------------------------- Normal

NORMAL_RE = re.compile(r'data-headertext="([^"]{3,60})"')


def read_normal(city, warn):
    markup = get(city["page"])
    out, seen = [], set()
    for raw in NORMAL_RE.findall(markup):
        label = clean(html.unescape(raw))
        mayor = label.startswith("Mayor ")
        name = label[len("Mayor "):] if mayor else label
        if not re.match(r"^[A-Z][A-Za-z.'’-]+(?: [A-Z][A-Za-z.'’-]+){1,3}$",
                        name):
            continue
        if name in seen:
            continue
        seen.add(name)
        out.append(record(city, "Mayor" if mayor else "Council Member", name,
                          district=None if mayor else "At Large"))
    return out


# ------------------------------------------------------------------- Quincy

QUINCY_WARD_RE = re.compile(
    r"\n([A-Z][A-Za-z.'’ -]{3,40})\nWard (\d+) (Alderman|Alderperson)\b")
QUINCY_TEL_RE = re.compile(r"\nTelephone\n([0-9()\- .]{10,20})\n")
QUINCY_MAIL_RE = re.compile(r"\n([A-Za-z0-9._%+-]+@quincyil\.gov)\b")
# Anchored on the sentence the mayor's own page uses to introduce her. A letter
# is not a roster, so a miss here warns and never fails — see the docstring.
QUINCY_MAYOR_RE = re.compile(
    r"I[’']m ([A-Z][A-Za-z.'’-]+(?: [A-Z][A-Za-z.'’-]+){1,3}),"
    r"[^.]{0,80}serve as Mayor")


def read_quincy(city, warn):
    index = get(city["page"])
    links = sorted({u for u in re.findall(
        r'href="(https://www\.quincyil\.gov/Government/City-Council/[A-Za-z-]+)"',
        index)})
    skip = {"City-Council-Meeting-Archive", "Municipal-Codebook",
            "Quincy-Strategic-Plan", "Quincy-Ward-Maps"}
    out = []
    for url in links:
        if url.rsplit("/", 1)[-1] in skip:
            continue
        text = visible(get(url))
        seat = QUINCY_WARD_RE.search(text)
        if not seat:
            warn("quincy: %s names no ward — dropped rather than guessed" % url)
            continue
        tel = QUINCY_TEL_RE.search(text)
        mail = QUINCY_MAIL_RE.search(text)
        out.append(record(
            city, seat.group(3), seat.group(1),
            district="Ward %d" % int(seat.group(2)),
            person_phone=phone(tel.group(1), city) if tel else None,
            person_email=mail.group(1) if mail else None,
            source_url=url))
    mayor_page = "https://www.quincyil.gov/Government/Mayors-Office"
    mayor = QUINCY_MAYOR_RE.search(visible(get(mayor_page)))
    if mayor:
        out.append(record(city, "Mayor", mayor.group(1), source_url=mayor_page))
    else:
        warn("quincy: the mayor's page no longer introduces her in the sentence "
             "this parser reads — the council ships without a head")
    return out


# ----------------------------------------------------------------- Danville

DANVILLE_RE = re.compile(
    r"\n([A-Z][A-Za-z.'’, -]{3,40}?)\n"
    r"(Mayor|Ward (\d+) (?:Alderman|Alderperson))[^\n]*\n"
    # A LOOKAHEAD, NOT A NEWLINE. Consuming the line break after the telephone
    # eats the one the NEXT seat's name needs, so every other seat is skipped:
    # the first draft read 9 of this page's 15 and the floor caught it.
    r"Email [^\n]*\nPhone:\n([0-9()\- .]{10,20})(?=\n)")


def read_danville(city, warn):
    text = visible(get(city["page"]))
    out, seen = [], set()
    for match in DANVILLE_RE.finditer(text):
        name = clean(match.group(1))
        if name in seen:
            continue
        seen.add(name)
        is_mayor = match.group(2) == "Mayor"
        out.append(record(
            city, "Mayor" if is_mayor else "Alderman", name,
            district=None if is_mayor else "Ward %d" % int(match.group(3)),
            person_phone=phone(match.group(4), city)))
    return out


# ------------------------------------------------------------------- cities

CITIES = {
    "champaign": {
        "jurisdiction": "City of Champaign",
        "county": "Champaign",
        "page": "https://champaignil.gov/city-council/",
        "robots_url": "https://champaignil.gov/wp-json/wp/v2/pages?slug=members",
        "office": {"office_address": "102 N Neil St.", "office_city": "Champaign",
                   "office_state": "IL", "office_zip": "61820",
                   "office_phone": "217-403-8720", "office_email": None},
        "read": read_champaign,
        # Mayor, five district seats, three at large.
        "min_officials": 9, "min_districts": 5, "min_heads": 1,
    },
    "decatur": {
        "jurisdiction": "City of Decatur",
        "county": "Macon",
        "page": "https://www.decaturil.gov/300/Mayor-Council",
        "office": {"office_address": "1 Gary K. Anderson Plaza",
                   "office_city": "Decatur", "office_state": "IL",
                   "office_zip": "62523", "office_phone": None,
                   "office_email": None},
        "read": read_decatur,
        # Mayor and six council members, all elected at large.
        "min_officials": 7, "min_districts": 0, "min_heads": 1,
    },
    "normal": {
        "jurisdiction": "Town of Normal",
        "county": "McLean",
        "page": "https://normalil.gov/1135/Meet-the-Council",
        "office": {"office_address": "11 Uptown Circle", "office_city": "Normal",
                   "office_state": "IL", "office_zip": "61761",
                   "office_phone": "309-454-2444", "office_email": None},
        "read": read_normal,
        # Mayor and six trustees, all elected at large.
        "min_officials": 7, "min_districts": 0, "min_heads": 1,
    },
    "quincy": {
        "jurisdiction": "City of Quincy",
        "county": "Adams",
        "page": "https://www.quincyil.gov/Government/City-Council",
        "office": {"office_address": "730 Maine St", "office_city": "Quincy",
                   "office_state": "IL", "office_zip": "62301",
                   "office_phone": "217-228-4500", "office_email": None},
        "read": read_quincy,
        # Seven wards, two aldermen each. The mayor is read where the page
        # still introduces her and is deliberately not a floor.
        "min_officials": 14, "min_districts": 14, "min_heads": 0,
    },
    "danville": {
        "jurisdiction": "City of Danville",
        "county": "Vermilion",
        "page": "https://www.cityofdanville.org/220/City-Council",
        "office": {"office_address": "17 West Main Street",
                   "office_city": "Danville", "office_state": "IL",
                   "office_zip": "61832", "office_phone": "217-431-2400",
                   "office_email": None},
        "read": read_danville,
        # Mayor and fourteen aldermen, two per ward across seven wards.
        "min_officials": 15, "min_districts": 14, "min_heads": 1,
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
        robots_url = city.get("robots_url", city["page"])
        require_robots_once(robots_url, HEADERS["User-Agent"], headers=HEADERS,
                            label="il-%s-council-scraper" % key)
        officials = city["read"](city, warnings.append)
        districts = sum(1 for r in officials
                        if r["district"] and r["district"] != "At Large")
        heads = sum(1 for r in officials if r["office"] == "Mayor")
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
        print("scraped %s: %d officials (%d seated by ward or district, %d head) "
              "-> %s" % (city["jurisdiction"], len(officials), districts, heads,
                         out), file=sys.stderr)

    if problems:
        raise SystemExit("il-large-city-councils: " + "; ".join(problems)
                         + " — refusing to write")


if __name__ == "__main__":
    main()
