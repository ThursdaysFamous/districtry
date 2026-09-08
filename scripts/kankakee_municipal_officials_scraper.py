#!/usr/bin/env python3
"""Kankakee County's municipal heads, from KATS Policy Committee minutes.

Kankakee is a rung-3 county (docs/EXPANSION_GUIDE.md §3.4): no county source
names a municipal officer, so the head of government comes from the regional
council. The five-rung ladder was walked on 2026-09-08 and every rung above
this one is measured shut, each at the URL it was measured at:

  1. The county is CivicPlus; /directory.aspx resolves to /m/directory and
     lists 45 COUNTY DEPARTMENTS, no municipality. k3county.net serves that
     same site byte-for-byte -- an alias, not a second source. The Clerk is
     WordPress: /wp-json/wp/v2/pages returns 58 pages, none a directory.
     The Statements of Economic Interests looked like the answer, because
     every elected Illinois municipal officer files one with the county
     clerk. It is not: the clerk publishes 852 filers as NAME AND DATE ONLY,
     with no office and no unit of government, and the underlying Jetpack
     `feedback` store returns 401. A name that cannot be attached to a town
     is not a roster row.
  2. /county-information/population-county-officials/ carries the county's
     own elected and appointed officials with phones, then township and
     MUNICIPAL POPULATION for exactly 21 municipalities. It names the 21 and
     names no municipal officer.
  4. https://k3gis.com/arcgis/rest/services/BASE/Taxing_Districts/MapServer/0
     ("Municpalities", the county's own spelling) HAS the fields -- name,
     addrdeliv, city, zip5, telephone, website, email -- and every one of
     them is empty on all 21 features.

WHY THE MINUTES AND NOT THE COMMITTEE PAGE. KATS publishes a Policy Committee
membership page that names five municipal heads and carries no date; its site
footer reads 2023. It is STALE ON TWO OF THE FIVE. Against the union of the
2026 minutes it says Paul Schore for Bourbonnais (the county's second-largest
municipality) where every 2026 meeting records Mayor Jeff Keast, and Tim
Nugent for Manteno where the 6 May 2026 minutes record Mayor Annette LaMore --
and villageofmanteno.com/village-board/ names LaMore too. Reading that page
would have published two wrong officeholders. Currency is a measurement, not
a reading of a page.

THE CURRENCY RULE THIS ENCODES. Illinois municipal terms turn over at the
consolidated election, the first Tuesday in April of odd years. Only meetings
held after the following 1 May are read, so a minute-book entry from before
the last turnover can never name a head. That is why this does not simply
take "the last two years".

WHAT THE ROUTE CANNOT DO, stated so nobody re-derives it:
  * HEADS ONLY. The Policy Committee seats one chief elected officer per
    member municipality; it never names a trustee, so no `board` is emitted.
  * FIVE MUNICIPALITIES, NOT 21. Only the MPO members sit on it. The other
    16 towns stay dark whatever this scraper does, and the
    kankakee-municipal-officials gap record says so.
  * It is an ATTENDANCE roll. A head who stops attending leaves the source;
    the builder's floors and check_roster_retention.py are what catch that.

TITLE. The minutes print "Mayor" for every municipal head, Bradley's included,
where bradleyil.org describes the village as having a "Village President".
Illinois villages commonly style their president mayor -- Manteno's own site
does -- so the label is carried AS THE SOURCE PRINTS IT rather than derived
from "Village of", which would be inventing an office. HEAD_OFFICES in
build_municipal_officials_roster.py accepts "mayor".

THE MINUTES HOST IS HTTP. files.kats-mpo.org answers https with a certificate
that does not cover that subdomain ("no alternative certificate subject name
matches"), while http serves the PDFs and is how the site's own pages link
them. The URL is carried exactly as published rather than rewritten to https,
which does not resolve; a plain link navigates normally from an https page.

PROXIES ARE NOT OFFICEHOLDERS. A row reads "Mayor Jeff Keast (via proxy of
Mr. Jared Gingerich)". The member is Keast; Gingerich is a stand-in who holds
no office and is never emitted.
"""

import argparse
import datetime
import io
import json
import re
import sys

import requests
from scraper_common import UA_ROSTER_COMPACT  # noqa: E402  (shared machinery — do not fork)

BASE = "https://www.kats-mpo.org"
# Any KATS page carries the year links in its nav; the committee page is the
# one this route already depends on, so it is the one read.
NAV_PAGE = BASE + "/committees/policy-committee"
YEAR_LINK_RE = re.compile(r'href="(/meetings/agendas-minutes/(?!archive/)[^"]+)"')
YEAR_IN_PATH_RE = re.compile(r"/(\d{4})")
PC_MINUTES_RE = re.compile(r'href="([^"]*?(\d{4})_(\d{2})_(\d{2})_PC_Minutes\.pdf)"', re.I)

HEADERS = {"User-Agent": UA_ROSTER_COMPACT}
TIMEOUT = 45

# A member row: an optional courtesy title, the name, an optional "(via proxy
# of ...)", a dash, then the unit. The dash the minutes use is an EN DASH; a
# hyphen appears too, so both are accepted.
MEMBER_RE = re.compile(
    r"^\s*(?:Mr\.|Mrs\.|Ms\.|Dr\.|Mayor|President)?\s*"
    r"(?P<name>[^–\-()]+?)\s*"
    r"(?:\((?:via\s+proxy\s+of[^)]*)\)\s*)?"
    r"[–\-]\s*"
    r"(?P<unit>.+?)\s*$")

# Only a unit the minutes name as a municipality is emitted. The committee
# also seats the county, the airport authority, the transit district and the
# state and federal agencies; none is a municipal head.
UNIT_RE = re.compile(r"^(?P<kind>City|Village|Town)\s+of\s+(?P<place>.+?)\s*$", re.I)

# The title the minutes print, normalised only in case.
TITLE_RE = re.compile(r"^\s*(Mayor|President|Village President)\b", re.I)

MIN_MUNICIPALITIES = 4   # measured 5 across the four 2026 meetings; one under,
MIN_HEADS = 4            # so one town's year of absence cannot freeze the county


def fail(msg):
    sys.exit("kankakee-municipal: FATAL — " + msg)


def get(url, what):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r
    except requests.RequestException as exc:
        fail("could not fetch %s (%s): %s" % (what, url, exc))


def turnover_cutoff(today=None):
    """The 1 May following the most recent consolidated municipal election.

    Illinois elects municipal officers on the first Tuesday in April of odd
    years and seats them within weeks, so minutes older than the following
    1 May can name a head who has since left. Returns a date.
    """
    today = today or datetime.date.today()
    year = today.year if today.year % 2 else today.year - 1
    cutoff = datetime.date(year, 5, 1)
    if cutoff > today:                       # early in an odd year, before the
        cutoff = datetime.date(year - 2, 5, 1)   # election has been held
    return cutoff


def discover_year_pages(html, into=None):
    """Merge {year: index-page path} out of one page's nav.

    NEVER a hardcoded year-stamped URL, and never ONE page's nav either: KATS
    renders a different subset per page. On 2026-09-08 the committee page
    listed 2026, 2023 and 2022 and omitted 2024 and 2025, which silently cost
    three post-turnover meetings; the 2026 index page listed all five. So this
    accumulates across every page fetched and main() asserts the years it
    needs are covered.
    """
    pages = {} if into is None else into
    for href in YEAR_LINK_RE.findall(html):
        years = [int(y) for y in YEAR_IN_PATH_RE.findall(href) if 2000 <= int(y) <= 2100]
        if years:
            pages.setdefault(max(years), href)
    return pages


def discover_minutes(html):
    """(date, absolute url) for every Policy Committee minutes PDF on a page."""
    out = []
    for href, y, m, d in PC_MINUTES_RE.findall(html):
        try:
            when = datetime.date(int(y), int(m), int(d))
        except ValueError:
            continue
        url = href if href.startswith("http") else BASE + href
        out.append((when, url))
    return out


def attendance_block(text):
    """The attendance lines, up to the next section heading.

    TWO HEADINGS, measured: the 2026 minutes say "Members in attendance:" and
    the 2025 ones "Policy Committee Members Present:". A parser keyed on one
    reads the other as a meeting with no members, which is silent — it just
    contributes nothing — so both are matched and a block that still comes
    back empty is WARNED about by the caller.
    """
    text = re.sub(r"[ \t]*\d+[ \t]*\n", "\n", text)     # strip line numbers
    m = re.search(r"(?:Members?\s+in\s+attendance"
                  r"|(?:Policy\s+Committee\s+)?Members?\s+Present)\s*:(.*?)"
                  r"(?:Others?\s+Present|Present\s+via|Open\s+Meeting)\s*:",
                  text, re.S | re.I)
    return m.group(1) if m else ""


def parse_minutes(pdf_bytes, when, url, warnings):
    """{place: {...}} for every municipal head named at one meeting."""
    try:
        from pypdf import PdfReader
    except ImportError:                       # pragma: no cover
        from PyPDF2 import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    block = attendance_block(text)
    if not block.strip():
        warnings.append("%s: no 'Members in attendance' block — layout changed?"
                        % when.isoformat())
        return {}
    found = {}
    for line in block.split("\n"):
        line = line.strip()
        if not line:
            continue
        member = MEMBER_RE.match(line)
        if not member:
            continue
        unit = UNIT_RE.match(member.group("unit").strip())
        if not unit:
            continue                          # county, KVAA, transit, IDOT…
        name = re.sub(r"\s+", " ", member.group("name")).strip(" .,")
        if not name:
            continue
        title = TITLE_RE.match(line)
        found[unit.group("place").strip()] = {
            "name": name,
            "office": (title.group(1).title() if title else "Mayor"),
            "kind": unit.group("kind").title(),
            "meeting": when.isoformat(),
            "source_url": url,
        }
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    warnings = []
    cutoff = turnover_cutoff()
    wanted = set(range(cutoff.year, datetime.date.today().year + 1))

    year_pages = discover_year_pages(get(NAV_PAGE, "the KATS committee page").text)
    if not year_pages:
        fail("no meeting-year pages found in the KATS nav — the site changed")

    minutes, visited = [], set()
    while True:
        todo = sorted((y for y in wanted if y in year_pages and y not in visited),
                      reverse=True)
        if not todo:
            break
        for year in todo:
            visited.add(year)
            html = get(BASE + year_pages[year],
                       "the KATS %d minutes index" % year).text
            minutes.extend(discover_minutes(html))
            # Each index page carries its own nav, and they disagree — merge
            # so a year missing from one page is still reached from another.
            discover_year_pages(html, year_pages)

    missing = sorted(wanted - visited)
    if missing:
        # Stated, never silent: a year nothing links is a year of meetings this
        # run could not read, and it may hold the newest name for a town.
        warnings.append("no index page found for %s — those meetings were not "
                        "read" % ", ".join(str(y) for y in missing))

    fresh = sorted([(w, u) for w, u in minutes if w >= cutoff])
    if not fresh:
        fail("no Policy Committee minutes dated on or after %s — every meeting "
             "on the site predates the last municipal turnover, so none can "
             "name a current head" % cutoff.isoformat())

    # Later meetings win: a head who changes mid-term is named by the newest
    # minutes that record their municipality.
    #
    # SURNAME-ONLY ROWS. The 2025 minutes print "Mayor Curtis" where the 2026
    # ones print "Mayor Chris Curtis". A bare surname is not a person's name
    # and is never shipped, so only a row carrying a forename can seat a head.
    # But a newer surname-only row still CARRIES INFORMATION: if its surname
    # disagrees with the full name we would otherwise ship, that municipality
    # has changed hands since, and the older full name is wrong. That town is
    # dropped rather than shipped stale — the whole reason this reads minutes
    # instead of the committee page.
    heads, seen_at, surname_only = {}, {}, {}
    for when, url in fresh:
        body = get(url, "minutes of %s" % when.isoformat()).content
        for place, rec in parse_minutes(body, when, url, warnings).items():
            seen_at.setdefault(place, []).append(when.isoformat())
            if " " in rec["name"]:
                heads[place] = rec
            else:
                surname_only[place] = rec

    for place, partial in sorted(surname_only.items()):
        held = heads.get(place)
        if held is None:
            warnings.append("%s: named only by surname (%s, %s) — no meeting "
                            "gives a forename, so no head is shipped"
                            % (place, partial["name"], partial["meeting"]))
        elif partial["meeting"] > held["meeting"] and \
                partial["name"].lower() != held["name"].split()[-1].lower():
            warnings.append("%s: %s (%s) names a different surname than %s "
                            "(%s) — the town has changed hands since, and no "
                            "meeting gives the new head's forename, so it is "
                            "dropped rather than shipped stale"
                            % (place, partial["name"], partial["meeting"],
                               held["name"], held["meeting"]))
            heads.pop(place, None)

    if len(heads) < MIN_MUNICIPALITIES:
        fail("%d municipality(ies) named across %d meeting(s) since %s "
             "(floor %d) — the attendance block or the roster shrank"
             % (len(heads), len(fresh), cutoff.isoformat(), MIN_MUNICIPALITIES))
    if len(heads) < MIN_HEADS:
        fail("%d head(s) < floor %d" % (len(heads), MIN_HEADS))

    scraped_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    officials, municipalities = [], []
    for place, rec in sorted(heads.items()):
        jurisdiction = "%s of %s" % (rec["kind"], place)
        officials.append({
            "jurisdiction": jurisdiction,
            "office": rec["office"],
            "name": rec["name"],
            "district": None,
            "office_address": None, "office_city": None, "office_state": None,
            "office_zip": None, "office_phone": None, "office_email": None,
            # The county's own municipal link list is NOT carried: two of its
            # 14 links do not point at the municipality at all (Hopkins Park
            # resolves to a lapsed domain someone else re-registered, Sammons
            # Point to a commercial directory), and both answer 200, so no
            # reachability check would catch them.
            "website": None,
            "source_url": rec["source_url"],
            "scraped_at": scraped_at,
            # Every row names the meeting it was read from: an attendance roll
            # states who was there on a date, never who holds office today.
            "read_from_meeting": rec["meeting"],
            "also_present_at": sorted(set(seen_at[place])),
        })
        municipalities.append({"name": place, "source_url": rec["source_url"],
                               "scraped_at": scraped_at})

    payload = {
        "county": "Kankakee",
        # NO `directory_url`, deliberately — do not add one. The builder uses it
        # for every municipality's sourceUrl when present and falls back to the
        # per-official source_url when absent, and the per-official URL is the
        # DATED MINUTES that name that town's own mayor. The obvious candidate,
        # the KATS committee membership page, is the one page this route must
        # never cite: it is undated and was stale on two of the five heads when
        # this was written, so a card sourced to it would send a reader to a
        # page contradicting the name on the card.
        "officials_page": year_pages[max(visited)] and BASE + year_pages[max(visited)],
        "scraped_at": scraped_at,
        "municipalities": municipalities,
        "officials": officials,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    for w in warnings:
        print("  WARN: %s" % w, file=sys.stderr)
    print("scraped %d municipal head(s) from %d KATS Policy Committee meeting(s) "
          "since %s -> %s" % (len(officials), len(fresh), cutoff.isoformat(), args.out),
          file=sys.stderr)
    for o in officials:
        print("    %-26s %-8s %-22s (%s)" % (o["jurisdiction"], o["office"],
                                             o["name"], o["read_from_meeting"]),
              file=sys.stderr)


if __name__ == "__main__":
    main()
