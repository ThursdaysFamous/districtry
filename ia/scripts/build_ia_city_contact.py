#!/usr/bin/env python3
"""
Build data/app/ia-city-contact.json — the office phone and website of every
Iowa city, read by ia/index.html's City card.

THIS DOES NOT NAME AN OFFICEHOLDER, AND THE CARD MUST NOT READ AS IF IT DOES.
The `ia-municipal-officeholders` gap record stays open: no statewide source
names Iowa's mayors, council members or clerks, measured across four routes on
2026-09-03. What this adds is the CITY OFFICE's own contact, which is a
different fact, and it takes the thinnest card in the instance -- a name and a
FIPS code, no link, no phone, no footer, on the layer with the most features --
and gives 939 of Iowa's cities their own front door.

THE SOURCE WAS ON FILE AS GATED AND IS NOT
------------------------------------------
`iowaleague.org/cities/` was recorded in this repo as "a membership directory
with no public officials export located" and, elsewhere, flatly as
"membership-gated". It answers HTTP 200 to an ordinary browser request with a
635 KB table of every Iowa city: City / Organization / County / Population /
Website / Phone. The old wording was right about the officeholders -- NO COLUMN
NAMES A PERSON -- and wrong about the directory.

One fetch detail that cost a measurement the first time: without an `Accept`
header the response arrives TRUNCATED at ~4.8 KB with zero anchors, which reads
exactly like a JavaScript-rendered page and is not one. Send browser headers.

THE JOIN IS TOTAL, WHICH IS WHAT MAKES IT SAFE
----------------------------------------------
Measured 2026-09-03/04: 948 League rows against TIGERweb's 939 Iowa
incorporated places (`LSADC` uniformly 25 -- Iowa has ONE place class, so this
join is simpler than Wisconsin's, which must separate cities from villages).
**No TIGER `BASENAME` repeats**, so the city name alone is a unique key and the
League's County column is never needed as a tiebreak -- which is just as well,
since that column can name TWO counties for a city on a line.

**939 of 939 TIGER places join**, with a ONE-ENTRY alias table: the League's
`Jewell` is TIGER's `Jewell Junction`. That totality is the gate. A city
renamed, dropped or added upstream breaks it loudly rather than quietly losing
a card's contact.

THE NINE LEAGUE ROWS THAT DO NOT JOIN ARE THE CHECK, NOT THE PROBLEM
--------------------------------------------------------------------
Two are COUNTY entries (Appanoose, Clayton -- population 0, county domains in
the website column), one is a repeated header artifact, and six name a place
TIGERweb's incorporated-places layer does not carry: Center Junction, Delphos,
Hepburn, Millville, Mount Union, Pioneer. All six are tiny (23-111 people) and
none publishes a website.

**Whether those six dissolved or TIGERweb lags is NOT established here**, and
the record says so rather than guessing. What IS established is that they are
absent from that layer: a prefix query returns zero for each, against a control
where `Adel` returns one row and `Jewell` returns `Jewell Junction city`, so
the zero is a measurement and not a broken query. Either way this app draws no
polygon for them, so there is no card for contact to reach.

The builder asserts the non-joining set has exactly this shape. A League table
that grows a column, loses its header, or starts listing school districts fails
here instead of shipping.

TWO WEBSITE CELLS HOLD AN E-MAIL, AND BOTH ARE OFFICE MAILBOXES
----------------------------------------------------------------
Dedham publishes `dedhamia@` and Shambaugh `cclerkshambaugh@` in the Website
column. Both pass the office-mailbox test `build_ia_county_officers.py` already
uses -- the local part names the CITY or the OFFICE, never a person -- so they
ship as an `email`, which the card helper renders as the word "Email" and never
as the address itself. A cell that is neither a URL nor an office-form mailbox
ships as nothing.

POPULATION IS MEASURED AND DELIBERATELY NOT SHIPPED
----------------------------------------------------
The League's table carries a population for all 948 rows and states no vintage
for it anywhere on the page. A bare "Population 791" on a card is an unsourced
number, so it is read here (to identify the county rows, which carry 0) and
never written.

THE URL KEY IS NAMED `url` ON PURPOSE
--------------------------------------
`validate_card_links.py`'s PUBLISHED_KEYS is {"url", "profileUrl"} -- the
"somebody else published this address" class, which caps a dead link at WARN.
These 532 are scraped from the League's table, not chosen by this repo. A
sample of 16 probed live: 13 answered 2xx/3xx, one 403 (a CDN refusing a
datacenter client) and two 202 (the challenge shape this repo already records
as "202 is never a document"). All three are classes that class exists for.

Usage:
    python3 ia/scripts/build_ia_city_contact.py
    python3 ia/scripts/build_ia_city_contact.py --check
"""

import html
import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ia/
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
OUT_NAME = "ia-city-contact.json"

LEAGUE = "https://iowaleague.org/cities/"
TIGERWEB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
            "Places_CouSub_ConCity_SubMCD/MapServer/4")
IA_FIPS = "19"

EXPECT_PLACES = 939        # TIGERweb Iowa incorporated places, all LSADC 25
MIN_LEAGUE_ROWS = 930      # measured 948
MIN_PHONES = 900           # measured 927
MIN_WEBSITES = 500         # measured 532

# The one name the two publishers spell differently. An entry that stops being
# needed FAILS the build, so a pin cannot outlive its reason.
NAME_ALIASES = {"JEWELL": "JEWELLJUNCTION"}

# League rows that correctly do not join, asserted by shape rather than ignored.
EXPECT_COUNTY_ROWS = 2     # "Appanoose County", "Clayton County" — population 0
EXPECT_HEADER_ROWS = 1     # a repeated header artifact inside the table body
EXPECT_ABSENT_FROM_TIGER = {
    "CENTERJUNCTION", "DELPHOS", "HEPBURN", "MILLVILLE", "MOUNTUNION", "PIONEER",
}

# THE TRUNCATION THIS FILE RECORDED IS GONE, AND THE BROWSER STRING WITH IT
# (2026-10-01). The note below used to read that without a browser claim the
# League page "arrives truncated at ~4.8 KB with zero anchors". Re-measured
# that day on this file's own stack -- curl with the districtry token and
# nothing else -- it answered HTTP 200, 634,438 bytes and 1,991 anchors. A
# RECORDED REFUSAL GOES STALE AND NOTHING RE-READS IT; this one had been
# licensing a browser claim for a page that serves us under our own name.
# The Accept headers stay: they are what a client asking for HTML sends, and
# they claim to be nobody.


def _curl(url, full_headers=False):
    cmd = ["curl", "-sS", "--fail", "-L", "--max-time", "180"]
    cmd += ["-H", "User-Agent: districtry/1.0 (+https://districtry.com/ia/)"]
    if full_headers:
        cmd += ["-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "-H", "Accept-Language: en-US,en;q=0.9"]
    return subprocess.run(cmd + [url], check=True, capture_output=True).stdout


def norm(name):
    n = (name or "").upper()
    n = re.sub(r"\bSAINT\b", "ST", n)
    return re.sub(r"[^A-Z0-9]+", "", n)


# ---------------------------------------------------------------- sources ---
def fetch_league():
    """Every row of the League's own city table, as a list of six cells."""
    page = _curl(LEAGUE, full_headers=True).decode("utf-8", "replace")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S | re.I)

    def cells(row):
        return [html.unescape(" ".join(re.sub(r"<[^>]+>", " ", c).split()))
                for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S | re.I)]

    out = [c for c in (cells(r) for r in rows) if len(c) == 6]
    body = [c for c in out if c[0] != "City"]
    if len(body) < MIN_LEAGUE_ROWS:
        raise RuntimeError(
            "the League's city table returned %d six-column rows, floor %d — the page's "
            "shape moved, or the fetch was truncated (send browser headers)"
            % (len(body), MIN_LEAGUE_ROWS))
    return body


def fetch_places():
    url = (TIGERWEB + "/query?where=STATE%3D%27" + IA_FIPS + "%27"
           "&outFields=GEOID,NAME,BASENAME,LSADC&returnGeometry=false&f=json")
    feats = json.loads(_curl(url)).get("features") or []
    if len(feats) != EXPECT_PLACES:
        raise RuntimeError(
            "TIGERweb returned %d Iowa incorporated places, expected %d — Iowa has "
            "incorporated or dissolved a city. Re-derive the join below, and check "
            "whether any of the six places recorded as absent has appeared"
            % (len(feats), EXPECT_PLACES))
    places = {}
    for f in feats:
        a = f["attributes"]
        if str(a.get("LSADC")) != "25":
            raise RuntimeError(
                "place %r carries LSADC %r — Iowa has grown a second incorporated-place "
                "class and the City card would need to say which" % (a["NAME"], a["LSADC"]))
        key = norm(a["BASENAME"])
        if key in places:
            raise RuntimeError(
                "two Iowa places normalize to %r — the city name is no longer a unique "
                "key and this join needs the League's County column as a tiebreak" % key)
        places[key] = a
    return places


# ------------------------------------------------------------------ clean ---
def clean_url(value):
    v = (value or "").strip()
    if not v or "@" in v:
        return None
    if v.startswith(("http://", "https://")):
        return v
    # 505 of the League's cells are written as a bare hostname with no scheme
    if re.match(r"^[a-z0-9.-]+\.[a-z]{2,}(/|$)", v, re.I):
        return "https://" + v
    return None


def clean_email(value, city):
    """An e-mail in the Website column ships only if it is an OFFICE mailbox —
    the local part naming the city or the office, never a person. The same test
    build_ia_county_officers.py uses, for the same reason."""
    v = (value or "").strip()
    if "@" not in v:
        return None
    m = re.match(r"^[^\s<>@]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", v)
    if not m:
        return None
    local = v.split("@", 1)[0].lower()
    stem = norm(city).lower()
    office = ("clerk", "cityhall", "cityof", "city")
    if stem and stem in re.sub(r"[^a-z0-9]+", "", local):
        return v
    if any(w in re.sub(r"[^a-z0-9]+", "", local) for w in office):
        return v
    return None


def clean_phone(value):
    v = (value or "").strip()
    return v if re.search(r"\d{3}\D*\d{3}\D*\d{4}", v) else None


# ------------------------------------------------------------------ build ---
def build(league, places):
    matched, leftover = {}, []
    for row in league:
        city, county, pop, website, phone = row[0], row[2], row[3], row[4], row[5]
        key = NAME_ALIASES.get(norm(city), norm(city))
        place = places.get(key)
        if place is None:
            leftover.append(row)
            continue
        rec = {"name": city}
        url = clean_url(website)
        email = clean_email(website, city)
        tel = clean_phone(phone)
        if tel:
            rec["phone"] = tel
        if url:
            rec["url"] = url
        if email:
            rec["email"] = email
        geoid = str(place["GEOID"])
        if geoid in matched:
            raise RuntimeError("two League rows resolve to place %s (%s and %s)"
                               % (geoid, matched[geoid]["name"], city))
        matched[geoid] = rec

    # THE GATE: every place this app draws must have a row.
    unmatched = [a["NAME"] for k, a in places.items() if str(a["GEOID"]) not in matched]
    if unmatched:
        raise RuntimeError(
            "%d Iowa place(s) got no League row: %s. The join is no longer total — "
            "reconcile it, never widen the alias table to paper over a rename"
            % (len(unmatched), unmatched[:6]))

    # And the rows that correctly do NOT join must still be the shape on record.
    counties = [r for r in leftover if r[0].upper().endswith(" COUNTY")]
    headers = [r for r in leftover if not r[0].strip() or r[3] == "Population"]
    absent = {norm(r[0]) for r in leftover} - {norm(r[0]) for r in counties + headers}
    if len(counties) != EXPECT_COUNTY_ROWS or len(headers) != EXPECT_HEADER_ROWS:
        raise RuntimeError(
            "the League table's non-city rows changed shape: %d county row(s) and %d "
            "header artifact(s), expected %d and %d"
            % (len(counties), len(headers), EXPECT_COUNTY_ROWS, EXPECT_HEADER_ROWS))
    if absent != EXPECT_ABSENT_FROM_TIGER:
        raise RuntimeError(
            "the set of League cities absent from TIGERweb moved.\n  now:      %s\n  "
            "on record: %s\nA city LEAVING that set has appeared in TIGERweb and should "
            "now join; one ENTERING it needs the same measurement the six on record got "
            "(a prefix query against a working control)"
            % (sorted(absent), sorted(EXPECT_ABSENT_FROM_TIGER)))

    # An alias that is no longer needed is an alias that can mis-key a future city.
    for stale, target in NAME_ALIASES.items():
        if stale in places:
            raise RuntimeError(
                "alias %r -> %r has outlived its reason: TIGERweb now carries a place "
                "normalizing to %r directly. Remove the alias" % (stale, target, stale))
    return matched


def main():
    check_only = "--check" in sys.argv[1:]
    out_path = os.path.join(APP_DATA_DIR, OUT_NAME)

    league = fetch_league()
    places = fetch_places()
    print("League rows %d | TIGERweb Iowa places %d" % (len(league), len(places)),
          file=sys.stderr)

    recs = build(league, places)
    phones = sum(1 for r in recs.values() if r.get("phone"))
    urls = sum(1 for r in recs.values() if r.get("url"))
    emails = sum(1 for r in recs.values() if r.get("email"))
    bare = sum(1 for r in recs.values() if not r.get("phone") and not r.get("url")
               and not r.get("email"))
    print("  joined %d/%d places (alias entries: %d)"
          % (len(recs), EXPECT_PLACES, len(NAME_ALIASES)), file=sys.stderr)
    print("  phone %d | website %d | office e-mail %d | neither %d"
          % (phones, urls, emails, bare), file=sys.stderr)

    if phones < MIN_PHONES:
        raise RuntimeError("only %d cities carry a phone, floor %d" % (phones, MIN_PHONES))
    if urls < MIN_WEBSITES:
        raise RuntimeError("only %d cities carry a website, floor %d" % (urls, MIN_WEBSITES))

    payload = json.dumps(recs, separators=(",", ":"), sort_keys=True) + "\n"
    if check_only:
        try:
            with open(out_path) as f:
                shipped = f.read()
        except OSError as e:
            raise RuntimeError("%s is missing (%s) — run without --check" % (OUT_NAME, e))
        if shipped != payload:
            raise RuntimeError("%s has drifted from the source. Re-run this builder."
                               % OUT_NAME)
        print("check: shipped roster matches the source", file=sys.stderr)
        return

    with open(out_path, "w") as f:
        f.write(payload)
    print("wrote data/app/%s — %d cities, %.1f KB"
          % (OUT_NAME, len(recs), len(payload) / 1024.0), file=sys.stderr)


if __name__ == "__main__":
    main()
