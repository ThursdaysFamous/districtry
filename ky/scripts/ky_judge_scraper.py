#!/usr/bin/env python3
"""
Kentucky judge scraper — the judge, and the numbered unit they were elected from
===============================================================================

Writes an intermediate roster to `data/source/ky-judges-scrape.json` for
`build_ky_judges.py` to turn into `data/app/ky-judge-roster.json`.

WHY THIS EXISTS, AND WHAT WAS ASKED. Kentucky's four court tilings shipped on
2026-10-01 drawn from statute alone (KRS 21A.010, 22A.010(2), 23A.020,
24A.030), and every one of the four cards could say which court covers a reader
and name nobody, because this project had not found a source stating which
district or circuit a SITTING judge was elected from. A judge's county of
residence is published and would place most of them by arithmetic; that is a
different fact from the one a ballot settled, and this project does not guess at
an officeholder. So Ask `ky-judge-district-join` went to the Administrative
Office of the Courts' Data Officer on 2026-10-01 and was answered 52 minutes
later. He named two surfaces, and they are not equivalent:

  * `kcoj.kycourts.net/ContactList/Search` — the Court of Justice directory
    search, in a tabular format. **IT REFUSES THIS PROJECT.** Its robots.txt is
    25 bytes of `User-agent: *` / `Disallow: /`, which binds every client this
    repo sends, so nothing is fetched from it and it is not a route here. A
    refusal is obeyed without exception; it is not an obstacle to route around.

  * `www.kycourts.gov` — which answers the ask, and is what this file reads.
    Its robots.txt is served, 190 bytes, and no rule in the one binding group
    matches any path read here.

THE SOURCE'S SHAPE, MEASURED 2026-10-01 RATHER THAN ASSUMED. Each judge is one
`div.card`: `<h3>` the name, `<h4>` the role with the court inside a
`span.court-name`, and a `<p>` naming the unit — `6th Supreme Court District`,
`6th Appellate District` + `Division 1`, `16th Judicial Circuit` + `Division 4`,
`16th Judicial District` + `Division 2`. So the number is printed beside the
person, which is exactly the join the ask was for.

THREE SURFACES, BECAUSE THE TWO TIERS ARE PUBLISHED DIFFERENTLY:

  * the Supreme Court's own page carries all seven justices against their seven
    districts, so one fetch answers that tier statewide;
  * the Court of Appeals' own page carries all fourteen judges against the seven
    appellate districts, two divisions each, so one fetch answers that tier too;
  * the trial tiers have NO statewide page — the Circuit, Family and District
    court landing pages carry no judge rows at all, measured — so they are
    assembled from the 120 county pages, which carry 818 numbered judge rows
    between them.

JEFFERSON IS THE ONE HOLE AND IT IS NOT SILENT HERE. Its county page ships the
judge list commented out in its own HTML (`<!--<div id="judges"></div>-->` with
no card row anywhere), and Jefferson is the SOLE county of circuit 30 and of
district 30, so Louisville's trial judges are named on no page of this source
while every other county's are. That is recorded as a known, asked-about
absence rather than discovered fresh on every run: `KNOWN_EMPTY` below carries
it with its date and reason, this scraper FAILS if any OTHER county's page comes
back empty, and it also FAILS if Jefferson's page starts carrying judges — the
`ACCEPTED_DROPS` property, so the day the Court of Justice fixes that page the
build turns red and a person re-reads this note instead of the fix going
unnoticed. The appellate tiers need nothing for Jefferson: both appellate pages
are statewide and already name its justice and its two appellate judges.

A DIVISION IS A SEAT, NOT A PLACE. A multi-judge circuit's numbered divisions
(KRS 23A.040 and after) are elected by the whole circuit and have no geometry,
so a division is carried as a label on a person and never as a district to join
on. The same word means real geography on a Kentucky school board, which is why
it is worth saying twice.

VACANCIES COME FROM THE COURT'S OWN WORD, AND ARE CONVERTED HERE RATHER THAN
CARRIED. Where a card's name is one of the words a publisher writes when nobody
holds a seat, the Court of Justice is stating that the seat is empty, which is
the one thing that licenses a vacancy claim (#1349): the row ships as
`vacant: true` with no name at all, from this page and this read date. The word
list has ONE reader in the fleet, `validate_officeholder_names.is_vacancy_marker`,
and the conversion happens at the PARSE rather than in the builder, because the
intermediate file is a roster too — it reaches a reader through
build_county_pages.py elsewhere in the fleet, and a `Vacant` sitting in it is a
person called Vacant waiting to be published.

Usage:
    python3 ky/scripts/ky_judge_scraper.py            # fetch and write
    python3 ky/scripts/ky_judge_scraper.py --selftest # offline, no network
"""

import argparse
import html
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
sys.path.insert(0, os.path.join(REPO, "scripts"))

import scraper_common as sc  # noqa: E402
from validate_officeholder_names import is_vacancy_marker  # noqa: E402  (one reader for the word)

HOST = "https://www.kycourts.gov"
COUNTY_URL = HOST + "/Courts/County-Information/Pages/{}.aspx"
SUPREME_URL = HOST + "/Courts/Supreme-Court/Pages/default.aspx"
APPEALS_URL = HOST + "/Courts/Court-of-Appeals/Pages/default.aspx"

OUT = os.path.join(INSTANCE, "data", "source", "ky-judges-scrape.json")
COUNTY_FABRIC = os.path.join(INSTANCE, "data", "app", "state-counties.json")

# One request a second. kycourts.gov states no Crawl-delay; this is politeness
# for 122 pages off one host rather than a rule being followed.
PACE_SECONDS = 1.0

# A county whose page carries no judge card, with the measurement that put it
# here. Re-audited every run in BOTH directions: another county going empty
# FAILS, and one of these starting to publish FAILS too, so the record cannot
# rot into an excuse for a source that has been fixed.
KNOWN_EMPTY = {
    "Jefferson": (
        "MEASURED 2026-10-01: the page ships its judge list commented out in "
        "its own HTML and carries no card row. Jefferson is the sole county of "
        "circuit 30 and of district 30, so Louisville's trial judges are named "
        "on no page of this source. Asked about on 2026-10-01 in the follow-up "
        "to Ask ky-judge-district-join; its appellate judges are unaffected, "
        "the two appellate pages being statewide."
    ),
}

# The four unit phrases this source prints, each mapped to the tier it belongs
# to. The tier is what the app's layers are keyed by; Family Court is a
# DIVISION of Circuit Court under Ky. Const. 112(6) and its judges are elected
# from the circuit, so its cards print a circuit number and it joins the
# circuit tier carrying its own court name.
UNIT_PHRASES = [
    ("supreme", re.compile(r"(\d+)(?:st|nd|rd|th)\s+Supreme Court District", re.I)),
    ("appeals", re.compile(r"(\d+)(?:st|nd|rd|th)\s+Appellate District", re.I)),
    ("circuit", re.compile(r"(\d+)(?:st|nd|rd|th)\s+Judicial Circuit", re.I)),
    ("district", re.compile(r"(\d+)(?:st|nd|rd|th)\s+Judicial District", re.I)),
]

DIVISION_RE = re.compile(r"Division\s+(\d+)", re.I)
CARD_RE = re.compile(r'<div class="card">(.*?)(?=<div class="card">|</div></div>\s*</div>\s*</div>\s*$|$)', re.S)
H3_RE = re.compile(r"<h3>(.*?)</h3>", re.S | re.I)
H4_RE = re.compile(r"<h4>(.*?)</h4>", re.S | re.I)
COURT_RE = re.compile(r'<span class="court-name">(.*?)</span>', re.S | re.I)
P_RE = re.compile(r"<p>(.*?)</p>", re.S | re.I)
HREF_RE = re.compile(r'<a href="([^"]+)"', re.I)
TAGS_RE = re.compile(r"<[^>]+>")


def fail(msg):
    sys.stderr.write("ky-judge-scraper: FAIL — %s\n" % msg)
    raise SystemExit(1)


def text_of(fragment):
    """Collapse an HTML fragment to one line of readable text."""
    s = TAGS_RE.sub(" ", fragment or "")
    s = html.unescape(s)
    s = re.sub(r"[\s ]+", " ", s)
    return s.strip()


def judge_block(page):
    """The region of a page that holds the judge cards, or '' when there is none.

    Scoped deliberately: a county page carries unrelated `div.card` markup
    elsewhere in its chrome, and taking every card on the page would read
    navigation furniture as people.
    """
    i = page.find('class="cbq-layout-main"')
    if i < 0:
        return ""
    return page[i:]


def parse_cards(page, where):
    """Every judge card on one page, as dicts. `where` names the page for errors."""
    out = []
    region = judge_block(page)
    if not region:
        return out
    for raw in CARD_RE.findall(region):
        h3 = H3_RE.search(raw)
        h4 = H4_RE.search(raw)
        if not h3 or not h4:
            continue
        name = re.sub(r"\s+", " ", text_of(h3.group(1))).strip()
        if not name:
            continue
        court = COURT_RE.search(h4.group(1))
        court_name = text_of(court.group(1)) if court else None
        role = text_of(COURT_RE.sub(" ", h4.group(1)))
        unit_text = " ".join(text_of(p) for p in P_RE.findall(raw))
        tier = None
        unit = None
        for name_, pattern in UNIT_PHRASES:
            m = pattern.search(unit_text)
            if m:
                tier, unit = name_, int(m.group(1))
                break
        if tier is None:
            # A Circuit Court Clerk's card carries no unit phrase. That is a
            # different office and is skipped rather than mis-filed.
            continue
        division = DIVISION_RE.search(unit_text)
        href = HREF_RE.search(raw)
        record = {}
        if is_vacancy_marker(name):
            # The court saying the seat is empty. It is a fact about the SEAT,
            # so it is recorded structurally and never as somebody's name.
            record["vacant"] = True
        else:
            record["name"] = name
        record.update({
            "role": role or None,
            "court": court_name,
            "tier": tier,
            "unit": unit,
            "division": int(division.group(1)) if division else None,
            "profileUrl": (HOST + href.group(1)) if href and href.group(1).startswith("/")
            else (href.group(1) if href else None),
            "readFrom": where,
        })
        if record.get("vacant"):
            # A vacant seat has no profile page; a href on such a card points at
            # the court, not at a person.
            record.pop("profileUrl", None)
        out.append(record)
    return out


# The shipped fabric names a county "Larue County" and the Court of Justice
# spells its own page LaRue, which is the county's own spelling — measured
# 2026-10-01, the only one of the 120 where the two differ once " County" is
# taken off. The alias decides the URL only; nothing a reader sees is renamed
# here, so there is no question of which spelling wins on a card.
PAGE_NAME_ALIAS = {"Larue": "LaRue"}


def counties():
    """Every Kentucky county, as (fabric name, the court's page name)."""
    with open(COUNTY_FABRIC) as fh:
        fabric = json.load(fh)
    names = []
    for feature in fabric.get("features", []):
        props = feature.get("properties", {}) or {}
        for key in ("name", "NAME", "county", "COUNTY"):
            if props.get(key):
                names.append(str(props[key]))
                break
    names = sorted(set(names))
    if len(names) != 120:
        fail("the county fabric gave %d county names, expected Kentucky's 120" % len(names))
    out = []
    for name in names:
        bare = re.sub(r"\s+County$", "", name).strip()
        out.append((bare, PAGE_NAME_ALIAS.get(bare, bare)))
    stray = sorted(set(PAGE_NAME_ALIAS) - {b for b, _ in out})
    if stray:
        fail("PAGE_NAME_ALIAS names %s, which the county fabric does not — the "
             "alias has outlived its county" % ", ".join(stray))
    return out


def scrape():
    sc.require_robots_once(SUPREME_URL, sc.UA_ROSTER_BOT,
                           headers=sc.UA_HEADERS_ROSTER_BOT, label="ky-judges")
    rows = []
    pages = {}

    for url, label in ((SUPREME_URL, "supreme-court-page"),
                       (APPEALS_URL, "court-of-appeals-page")):
        page = sc.fetch_stdlib(url, headers=sc.UA_HEADERS_ROSTER_BOT)
        found = parse_cards(page, label)
        if not found:
            fail("%s returned no judge cards — the page's shape has moved, and "
                 "a tier read as empty would silently drop every judge in it" % url)
        rows.extend(found)
        pages[label] = len(found)
        time.sleep(PACE_SECONDS)

    empty = []
    for county, page_name in counties():
        url = COUNTY_URL.format(page_name.replace(" ", "%20"))
        try:
            page = sc.fetch_stdlib(url, headers=sc.UA_HEADERS_ROSTER_BOT)
        except Exception as exc:
            fail("%s (%s) could not be read: %s. A county page this project "
                 "cannot fetch is not a county with no judges, so nothing is "
                 "written rather than shipping a roster short of a whole county."
                 % (county, url, exc))
        found = [r for r in parse_cards(page, county) if r["tier"] in ("circuit", "district")]
        if not found:
            empty.append(county)
        else:
            if county in KNOWN_EMPTY:
                fail("%s now publishes %d judge rows, and KNOWN_EMPTY still records "
                     "it as empty. That is the source being FIXED, which is good "
                     "news and must be read by a person: delete its KNOWN_EMPTY "
                     "entry, re-read the note in this file's docstring and the "
                     "ky-judges gap record, and re-run."
                     % (county, len(found)))
            rows.extend(found)
        time.sleep(PACE_SECONDS)

    unexpected = sorted(set(empty) - set(KNOWN_EMPTY))
    if unexpected:
        fail("these counties' pages carry no judge rows and are not recorded as "
             "empty: %s. Either the source has changed shape or these counties "
             "have genuinely stopped publishing; both want a person's eye before "
             "a roster ships missing them." % ", ".join(unexpected))

    payload = {
        "source": {
            "supremeCourt": SUPREME_URL,
            "courtOfAppeals": APPEALS_URL,
            "countyPages": COUNTY_URL.format("<County>"),
            "publisher": "Kentucky Court of Justice",
            "note": "Named in the Administrative Office of the Courts' reply to "
                    "Ask ky-judge-district-join, 2026-10-01. The directory "
                    "search the same reply named is not read: its robots.txt "
                    "refuses every client.",
        },
        "readOn": time.strftime("%Y-%m-%d", time.gmtime()),
        "pages": pages,
        "emptyCounties": sorted(empty),
        "rows": rows,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("ky-judge-scraper: wrote %s — %d judge rows (%d before de-duplication), "
          "%d county pages empty (%s)"
          % (os.path.relpath(OUT, REPO), len(rows), len(rows), len(empty),
             ", ".join(sorted(empty)) or "none"))


SELFTEST_PAGE = """
<h2>Justice, Judges &amp; Circuit Court Clerk</h2>
<div class="cbq-layout-main"><div class="card-row">
<div class="card"><a href="/Courts/Supreme-Court/Pages/6th-Supreme-Court-District.aspx">
<div class="media"><div class="media-body"><span class="hide">6</span>
<h3>Michelle M. Keller </h3><h4>Justice<span class="court-name">Supreme Court</span></h4>
<p>6th Supreme Court District</p><span class="profile">View Profile</span></div></div></a></div>
<div class="card"><div class="media"><div class="media-body"><span class="hide">416</span>
<h3>Patricia M. Summe </h3><h4>Chief Circuit Judge<span class="court-name">Circuit Court</span></h4>
<p>16th Judicial Circuit
    <br>Division 4</p></div></div></div>
<div class="card"><div class="media"><div class="media-body"><span class="hide">216</span>
<h3>Terri King Schoborg </h3><h4>Judge<span class="court-name">Family Court</span></h4>
<p>16th Judicial Circuit
    <br>Division 2</p></div></div></div>
<div class="card"><div class="media"><div class="media-body"><span class="hide">32</span>
<h3>Vacant</h3><h4>Judge<span class="court-name">Court of Appeals</span></h4>
<p>3rd Appellate District
    <br>Division 2</p></div></div></div>
<div class="card"><div class="media"><div class="media-body">
<h3>John C. Middleton </h3><h4>Circuit Court Clerk</h4></div></div></div>
</div></div>
"""


def selftest():
    rows = parse_cards(SELFTEST_PAGE, "selftest")
    assert len(rows) == 4, "the clerk's card must be skipped, got %d rows" % len(rows)
    by_name = {r["name"]: r for r in rows if r.get("name")}

    keller = by_name["Michelle M. Keller"]
    assert keller["tier"] == "supreme" and keller["unit"] == 6, keller
    assert keller["division"] is None, "a Supreme Court card names no division"
    assert keller["profileUrl"].startswith(HOST), keller["profileUrl"]
    assert keller["role"] == "Justice", keller["role"]

    summe = by_name["Patricia M. Summe"]
    assert summe["tier"] == "circuit" and summe["unit"] == 16, summe
    assert summe["division"] == 4 and summe["court"] == "Circuit Court", summe
    assert summe["role"] == "Chief Circuit Judge", summe["role"]

    # Family Court prints a CIRCUIT number, so it joins the circuit tier while
    # keeping its own court name. Filing it as its own tier would invent a
    # fifth tiling that no statute draws.
    schoborg = by_name["Terri King Schoborg"]
    assert schoborg["tier"] == "circuit" and schoborg["unit"] == 16, schoborg
    assert schoborg["court"] == "Family Court", schoborg

    # The court's "Vacant" card. The word is converted here, so the row carries
    # the seat's facts and nobody's name — a name would be published as a person.
    vacancies = [r for r in rows if r.get("vacant")]
    assert len(vacancies) == 1, vacancies
    vacant = vacancies[0]
    assert "name" not in vacant, vacant
    assert "profileUrl" not in vacant, vacant
    assert vacant["tier"] == "appeals" and vacant["unit"] == 3, vacant
    assert vacant["division"] == 2, vacant
    assert "vacant" not in {str(v).lower() for r in rows for v in r.values()}, rows

    # A page with no judge region yields nothing rather than reading chrome.
    assert parse_cards('<div class="card"><h3>Nav</h3><h4>x</h4><p>1st Judicial Circuit</p></div>',
                       "no-region") == []

    # And a unit phrase alone is not enough: a card with no name is not a person.
    nameless = SELFTEST_PAGE.replace("<h3>Vacant</h3>", "<h3> </h3>")
    assert len(parse_cards(nameless, "selftest")) == 3, "a card with no name at all"

    print("ky-judge-scraper: selftest OK — 4 judge rows, clerk skipped, "
          "Family Court filed under its circuit, the vacancy structural and "
          "nobody named Vacant")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true",
                    help="parse the recorded page shapes offline; no network")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    scrape()


if __name__ == "__main__":
    main()
