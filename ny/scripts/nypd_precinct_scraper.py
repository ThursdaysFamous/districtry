#!/usr/bin/env python3
"""
Scrape each NYPD precinct's commanding officer from its nyc.gov precinct page
(METRO_EXPANSION_PLAYBOOK §9). Stage 1 of the pipeline: the precinct list is
driven from the Socrata precinct boundary dataset (y76i-bdw7) — NYPD's precinct
numbers are irregular, so never loop 1..N — and each precinct's ordinal page
(…/precincts/{Nth}-precinct.page) yields the "Commanding Officer:" line.

THREE PRECINCTS ARE NAMED, NOT NUMBERED, ON NYC.GOV. The ordinal pattern holds
for 75 of 78 and 404s for precincts 14, 18 and 22, whose pages are
midtown-south / midtown-north / central-park. That cost twice over and quietly:
those three lost their commanding officer (a 404 yields no name, correctly) AND
their dead URL was still written as `source_url`, so the card rendered a link to
a 404. Caught 2026-08-25 when validate_card_links.py grew to scan every
instance's data/app.

The mapping is not taken from the pages, which never state their own precinct
number, nor from the names looking obvious. It is PROVEN SPATIALLY from the
city's own data: each named station house in FacDB (ji82-xba5) is tested against
the numbered precinct polygons in y76i-bdw7, and each falls inside exactly one —
Midtown South, 357 W 35 St, inside precinct 14; Midtown North, 306 W 54 St,
inside 18; Central Park inside 22. NYPD's own precinct landing page independently
confirms these are the only three named precincts.

THE STATION HOUSE COMES FROM THIS PAGE TOO, NOT FROM THE CITY'S FACILITIES LIST
(2026-10-16). The card used to take its station address from FacDB (ji82-xba5),
the first `factype='POLICE STATION'` row whose `policeprct` matched — and
`policeprct` is the precinct a facility SITS IN, not the one it houses. Measured
that day against each precinct's own page: precinct 90's card named "ENG 216, LAD
108, BAT. 35, 187 Union Avenue", a firehouse, where NYPD gives 211 Union Avenue;
84 named Engine 207 at 172 Tillary where NYPD gives 301 Gold Street; 23 named
Engine 53 at 1836 Third Avenue where NYPD gives 164 East 102 Street. Other rows
are a firehouse name on the right shared building (7, 100), a stray unit that
happened to come first (18's Mounted Unit, 40's planned station, 121's landfill
garage), or a spreadsheet date where an address was ("May-47 50 Avenue" for
108's 5-47 50 Avenue). Each page's "Contact Information" block states the
station's address and its desk telephone, so both are read here.

THE STATION'S MAP POINT IS GEOCODED FROM THAT ADDRESS, and only kept when two
tests agree (2026-10-16). The nearest-station card used the same FacDB rows, so
it listed firehouses, a juvenile centre and a landfill garage as police
stations, and put the 40th at 257 Alexander Avenue where NYPD now gives 567 East
149th Street. Each address is sent to NYC Planning's GeoSearch
(geosearch.planninglabs.nyc), the city's own geocoder over its address
database, and the answer is kept only if (1) the house number it returns is the
one NYPD printed and (2) the point lies inside that precinct's own polygon in
y76i-bdw7. Measured that day: 75 of 78 pass on the first query. Two pass on a
narrower retry — 19 1/2 Pitt Street (the 7th) matches as 19 Pitt Street, and
the Central Park precinct, whose address is "86th and Transverse Rd", is found
by name as GeoSearch's "Central Park Precinct" venue — and both still have to
land inside their own precinct. A precinct that passes neither gets no point
and is printed; it is never placed by guess.

Writes an intermediate JSON with source_url + scraped_at per record. A page
that WAF-blocks or omits a label yields a null field — never guessed. build_nypd_roster.py resolves this into data/app/nypd-precinct-info.json.

Usage:
    python3 scripts/nypd_precinct_scraper.py [--out PATH] [--limit N]
"""

import html as html_lib
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
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

SOCRATA = "https://data.cityofnewyork.us/resource/y76i-bdw7.geojson?$limit=1000"
GEOSEARCH = "https://geosearch.planninglabs.nyc/v2/search?"
PAGE = "https://www.nyc.gov/site/nypd/bureaus/patrol/precincts/{slug}-precinct.page"
# precinct number -> the slug nyc.gov actually serves, for the three that are
# named rather than numbered (see the module docstring for how each was proven).
# A number absent here uses its ordinal.
NAMED_PAGES = {14: "midtown-south", 18: "midtown-north", 22: "central-park"}

# Words that begin the body paragraph after the officer's name — never part of
# a name, and the boundary the capture stops at.
_STOP = (r"(?:The|This|As|New|Its|It|Located|NYPD|Officers|Police|Precinct|In|"
         r"Situated|Bounded|Covering|Home)")
_RANK = r"(?:Deputy\s+|Assistant\s+)?(?:Inspector|Chief|Captain|Lieutenant|Sergeant)"
NAME_RE = re.compile(
    r"Commanding Officer:\s*(" + _RANK +
    r"(?:\s+(?!" + _STOP + r"\b)[A-Z][A-Za-z'\u2019.,\-]*){1,4})"
)
UA = "Mozilla/5.0 (compatible; districtry-nyc/1.0; +https://districtry.com/ny/)"
DEFAULT_OUT = os.path.join(os.path.dirname(__file__), ".cache", "nypd_precincts_raw.json")


def ordinal(n):
    n = int(n)
    v = n % 100
    suffix = "th" if 11 <= v <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return "%d%s" % (n, suffix)


def page_url(n):
    """The precinct's page on nyc.gov — its name where it has one, else its ordinal."""
    return PAGE.format(slug=NAMED_PAGES.get(int(n)) or ordinal(n))


def _get(url, timeout=45):
    headers = {"User-Agent": UA, "Accept": "text/html,application/json"}
    token = os.environ.get("SOCRATA_APP_TOKEN")
    if token and "data.cityofnewyork.us" in url:
        headers["X-App-Token"] = token
    require_robots_once(url, UA,
                        headers=headers, label="ny-nypd-precinct-scraper")
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def precinct_shapes():
    """precinct number -> its boundary geometry, from the same dataset the map draws."""
    shapes = {}
    for f in json.loads(_get(SOCRATA)).get("features", []):
        pct = (f.get("properties") or {}).get("precinct")
        if pct not in (None, "") and f.get("geometry"):
            shapes[int(pct)] = f["geometry"]
    return shapes


def _in_ring(x, y, ring):
    inside = False
    for i in range(len(ring)):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[i - 1][0], ring[i - 1][1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def in_geometry(pt, geom):
    """Even-odd within a Polygon, any part of a MultiPolygon — the app's own rule."""
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return any(sum(_in_ring(pt[0], pt[1], r) for r in poly) % 2 == 1 for poly in polys)


def _house(text):
    """The house number a street line starts with, in one shape: "64-2" and
    "64-02" are the same Queens number, and "2271-89" (a range) is its first."""
    m = re.match(r"^\s*(\d+)(?:-(\d+))?", text or "")
    if not m:
        return None
    if m.group(2) is None:
        return m.group(1)
    # A Queens number keeps its second part; a Manhattan-style range does not.
    # GeoSearch answers the first number alone for a range, so both are accepted.
    return m.group(1) + "-" + str(int(m.group(2)))


def _search(text):
    url = GEOSEARCH + urllib.parse.urlencode({"text": text, "size": 1})
    feats = json.loads(_get(url)).get("features") or []
    return feats[0] if feats else None


def geocode_station(street, city, name, shape):
    """[lng, lat] for the station, or None. See the module docstring for the
    two tests every answer has to pass."""
    want = _house(street)
    tries = [(street + ", " + city, "house")]
    whole = re.match(r"^(\d+)\s+\d+/\d+\s+(.*)$", street)
    if whole:  # "19 1/2 Pitt Street" -> "19 Pitt Street"
        tries.append((whole.group(1) + " " + whole.group(2) + ", " + city, "house-whole"))
    tries.append((name + " Precinct", "venue"))
    for text, kind in tries:
        f = _search(text)
        if not f:
            continue
        props = f.get("properties") or {}
        pt = (f.get("geometry") or {}).get("coordinates")
        if not pt or not in_geometry(pt, shape):
            continue
        if kind == "house":
            got = _house(props.get("housenumber"))
            if not (got and want and (got == want or want.startswith(got + "-"))):
                continue
        elif kind == "house-whole":
            if _house(props.get("housenumber")) != whole.group(1):
                continue
        elif "PRECINCT" not in (props.get("name") or "").upper():
            continue
        return [round(pt[0], 6), round(pt[1], 6)], kind
    return None, None


def station_name(n):
    """What NYPD calls the precinct: its name where it has one, else its ordinal."""
    slug = NAMED_PAGES.get(int(n))
    return slug.replace("-", " ").title() if slug else ordinal(n)


def commander_from_html(page_html):
    # Entities are UNESCAPED before matching, and that is load-bearing rather
    # than tidiness: the three named precinct pages write the CO line as
    # "Commanding Officer:&nbsp;Deputy Inspector&nbsp;Christopher Treubig", and
    # a raw match sees "&nbsp;" where it expects a space — so those three
    # returned no commander even once their URLs were right.
    text = re.sub(r"<[^>]+>", " ", page_html)
    text = html_lib.unescape(text).replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)

    # ANCHOR ON THE RANK AND TAKE NAME TOKENS, rather than trying to recognise
    # where the body paragraph begins. The previous version enumerated the
    # openings it had seen — "The 13th Precinct serves…", "This precinct…" —
    # and so missed every page that opened differently: the three named
    # precincts' "As its name implies, the Midtown South Precinct…", and the
    # 42nd's "New York City's 42nd Precinct serves…". Precinct 42 had no
    # commanding officer on its card for that reason alone, with a live page
    # and a perfectly readable name on it.
    #
    # A generic "stop before the sentence that mentions Precinct" lookahead was
    # tried and is WRONG, worth recording so it is not tried again: the capture
    # is non-greedy, so it stops at the EARLIEST position satisfying the
    # lookahead — which is inside the name itself — and it truncated 58 of 78
    # names to their bare rank while looking plausible.
    #
    # So the rank is the anchor (NYPD commanding officers are Captains,
    # Inspectors, Deputy Inspectors and Chiefs), followed by up to four
    # capitalised tokens that are not sentence-openers. That reads initials
    # ("Timothy V. Magliente"), suffixes ("James H. Moore III"), hyphenated
    # surnames ("Michael Black-Larkins") and the county's own punctuation typos
    # ("Anthony M, Lavino") exactly as published, and resolves all 78.
    m = NAME_RE.search(text)
    if not m:
        return None
    name = m.group(1).strip(" .,")
    # sanity: a rank + name, not a stray sentence
    return name if 4 <= len(name) <= 60 else None


# The "Contact Information" heading (an h2 on most pages, an h3 on some) is
# followed by the address paragraph (street, <br>, "City, NY, ZIP") and then the
# telephone paragraph whose first entry is the precinct's own desk line.
CONTACT_RE = re.compile(
    r"<h[23]>\s*Contact Information\s*</h[23]>\s*<p>(.*?)</p>\s*<p>(.*?)</p>",
    re.S | re.I)
PHONE_RE = re.compile(r"^\s*Precinct\s*:\s*\((\d{3})\)\s*(\d{3})\s*-\s*(\d{4})\b")
CITY_RE = re.compile(r"^(.+?),\s*NY,?\s*(\d{5})(?:-\d{4})?$")


def _plain(fragment):
    text = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html_lib.unescape(text).replace("\u00a0", " ")).strip()


def contact_from_html(page_html):
    """The station address lines and the precinct desk telephone, or Nones.

    The address is kept only in its exact published shape — a street line,
    then "City, NY, ZIP" — so a page that changes layout yields nothing rather
    than a half-parsed address on a card."""
    m = CONTACT_RE.search(page_html)
    if not m:
        return None, None
    lines = [_plain(x) for x in re.split(r"<br\s*/?>", m.group(1), flags=re.I)]
    lines = [x for x in lines if x]
    address = None
    if len(lines) == 2 and re.match(r"^\d", lines[0]):
        cm = CITY_RE.match(lines[1])
        if cm:
            address = [lines[0].rstrip(" ,"), "%s, NY %s" % (cm.group(1).strip(), cm.group(2))]
    first = _plain(re.split(r"<br\s*/?>", m.group(2), flags=re.I)[0])
    pm = PHONE_RE.match(first)
    # Spacing inside the number varies by page ("(718)590-5511", "439- 4211"),
    # so it is written back in one shape.
    phone = "(%s) %s-%s" % pm.groups() if pm else None
    return address, phone


def main():
    argv = sys.argv[1:]
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None

    shapes = precinct_shapes()
    nums = sorted(shapes)
    if limit:
        nums = nums[:limit]
    scraped_at = os.environ.get("SCRAPED_AT") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    records = {}
    found = with_address = with_point = 0
    unplaced = []
    for n in nums:
        url = page_url(n)
        commander = address = phone = None
        try:
            page = _get(url)
            commander = commander_from_html(page)
            address, phone = contact_from_html(page)
        except urllib.error.HTTPError as e:
            commander = None  # 404/403 -> no CO for this precinct, never guessed
        except Exception:
            commander = None
        if commander:
            found += 1
        point = how = None
        if address:
            with_address += 1
            try:
                point, how = geocode_station(address[0], address[1], station_name(n), shapes[n])
            except Exception:
                point = None
            if point:
                with_point += 1
            else:
                unplaced.append(n)
        records[str(n)] = {"commander": commander, "name": station_name(n),
                           "address": address, "phone": phone, "point": point,
                           "point_how": how, "source_url": url, "scraped_at": scraped_at}
        time.sleep(0.3)  # courteous to nyc.gov

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"precincts": records}, f, indent=2, ensure_ascii=False)
    print("wrote %s: %d precincts, %d with a commander, %d with a station address, "
          "%d with a map point" % (out_path, len(records), found, with_address, with_point),
          file=sys.stderr)
    for n in unplaced:
        print("  no map point for precinct %d: %s" % (n, ", ".join(records[str(n)]["address"])),
              file=sys.stderr)


if __name__ == "__main__":
    main()
