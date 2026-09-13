#!/usr/bin/env python3
"""
One crawlable page per county board in the fleet, naming every member.

WHY THIS EXISTS. Measured 2026-09-13: across all 51 authored HTML pages on
this site, NOT ONE OFFICEHOLDER NAME appears. The rosters are real — 2,574
seats across 164 counties in three states, every seat named, most with an
e-mail or a phone — and every one of them reaches a reader only after
JavaScript fetches a JSON file and renders a card. A crawler sees a map and a
toggle list. So the site that knows who holds those seats publishes that fact
nowhere a search engine can read it, and someone typing "who is on the LaSalle
County board" is answered by everyone except the project built to answer it.

WHY A PAGE PER COUNTY AND NOT PER DISTRICT. The obvious reading is one page per
seat, which is 2,574 of them. Two reasons not to: the queries people actually
type are county-level far more often than district-level, and a page whose
whole content is one name and a phone number is the shape search engines treat
as thin. A county page carries every name in the county — the same crawlable
text at a fraction of the page count, with an anchor per district so a link to
one seat still lands on it. Per-district pages remain possible later; this
decides nothing against them.

WHAT IS ON A PAGE, AND WHAT IS NOT. Everything comes from the shipped roster
the app itself reads, so the page and the card cannot disagree — that is the
point of generating it rather than writing it. A field the roster does not
carry is absent from the page rather than blank: no "email: —", no invented
office. A district the roster leaves empty says so in the app's own words
rather than being skipped, because a board of eighteen showing seventeen seats
reads as complete and is not. Nothing here is guessed, and nothing is
reformatted beyond escaping and one stated party-spelling table.

HOW A NEW STATE'S COUNTIES GET PAGES. Two halves, and the second is the one
that makes it automatic.

  The INSTANCES registry holds one entry per state that publishes county
  officeholders, and the entry holds WORDING and an ADAPTER NAME. It never
  holds a list of counties: every adapter enumerates whatever its roster
  carries, so a county's page appears the run after its roster ships and
  disappears the run after it leaves. Illinois gained Menard and Lake that way
  on introduction; no list was edited.

  check_registration() is what covers a state that is not in the registry at
  all. It walks every instance's data/app, finds each file whose records name
  people and look county-shaped, subtracts what the adapters read, and FAILS on
  anything left over — naming the file and the two ways to clear it: write an
  adapter, or record in NOT_COUNTY_BOARDS why these pages are the wrong home
  for it. So a new state's county roster cannot land quietly. Nobody has to
  remember, and nothing is generated from a guess about a shape nobody has
  looked at. Michigan is the case it is written for: it ships county
  commissioner DISTRICTS and no names, so it has no entry and nothing to flag,
  and the day a roster arrives this gate asks for one.

FOUR ROSTER SHAPES, because the three states genuinely differ and a schema
describing all four would be longer than the four adapter functions:

  il_districted  55 files, one per county, keyed by district. Three record
                 shapes share those files — see the adapter.
  il_at_large    one file for the 20 counties that elect countywide. These
                 pages say so outright, which is the answer to "what district
                 am I in" for a fifth of the counties Illinois serves.
  wi_seats       one file keyed by SEAT, every record naming its own county.
                 Four things a record can be: a name, a vacancy, a withheld
                 district with a printed reason, or a county's at-large list.
  ia_supervisors one file keyed by county with districts nested, plus a
                 separate chairs file joined by name onto the members.

THE COUNTY NAME AND SLUG ARE NOT A NEW TABLE. Illinois's come from
build_county_status.py's ALL_COUNTIES and slug_of(), which the county-status
page and the coverage ring already use; Wisconsin's and Iowa's records name
their own county, so those slugs are derived and no list can go stale. A roster
file this script cannot place is a failure, not a skip.

  python3 scripts/build_county_pages.py            # (re)generate in place
  python3 scripts/build_county_pages.py --check    # the CI drift gate
"""

import glob
import json
import os
import re
import sys
import urllib.parse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def fail(msg):
    """Stop, naming THIS script. build_privacy_page exports a fail() and this
    file used to borrow it, so a missing GENERATED region in wi/county-board.html
    reported itself as `build-privacy-page: FAIL` — a reader's first move on
    that line is to open the wrong generator."""
    print("build-county-pages: FAIL — %s" % msg, file=sys.stderr)
    raise SystemExit(1)

from build_landing_page import (  # noqa: E402
    FAVICON, FONTFACE, TOKENS, parse_token_block, read, token_css,
)
from build_privacy_page import (  # noqa: E402
    DARK_EXTRA, DARK_TOKENS, LIGHT_TOKENS, esc,
)
from build_history_page import shared_footer_byline  # noqa: E402
from build_county_status import ALL_COUNTIES, slug_of  # noqa: E402

# A county whose shipped roster names NOBODY. A page for it would be a page
# about a county board with no officeholder on it, which is the opposite of
# why these pages exist — and it would fail this work's own test that a
# generated URL names someone. Recorded with what the roster does carry, and
# re-audited: the moment the roster starts naming people the entry is stale
# and the build fails, which is the property ACCEPTED_DROPS had to be given
# after the fact.
#
# KEYED "<instance tag>/<county>", not by county name. Illinois and Wisconsin
# both have a Winnebago County, Wisconsin has a county named IOWA, and eleven
# other names are shared between the two states — a bare county name would let
# an entry written about one state silence a real regression in another.
NAMES_NOBODY = {
    "il/Winnebago": dict(
        date="2026-09-13",
        reason="all 20 district keys are flat records carrying an e-mail, a "
               "phone and the county's source URL, and no name field anywhere "
               "in the file. The county publishes per-district contact details "
               "rather than a member list; wincoil.gov's board page is the "
               "roster and nothing here parses names out of it yet.",
    ),
}

# ——— the fleet registry ———
#
# One entry per instance that publishes county-level officeholders. `adapters`
# names the reader functions below; everything else is reader-facing wording.
# WHAT IS NEVER CONFIGURED IS WHICH COUNTIES EXIST — every adapter enumerates
# whatever its roster carries, so a county's page appears the run after its
# roster ships and disappears the run after it leaves. That is the whole
# mechanism for "as counties come online": there is no list to update.
#
# An adapter is CODE rather than a schema because the three shipped roster
# shapes are genuinely different (per-county files keyed by district; one file
# keyed by seat; one file keyed by county with districts nested), and a
# declarative description of all three would be longer than the three
# functions. The instance's OWN county names come from the roster wherever the
# roster carries them (wi, ia) and from the state's canonical list only where
# it does not (il, whose filenames are slugs).
# WORDING IS FIVE KEYS RATHER THAN ONE, because one noun cannot do all five
# jobs and a single `body` key produced "Menominee County County Board" on
# every Wisconsin page in the first draft:
#
#   heading      what follows the county name — the h1, the schema name, the
#                description subject. "Adams County Board", "Adams County
#                Board of Supervisors".
#   page_title   the <title>, which is the search result's own line, so it
#                carries the word a reader would type. Illinois's board has
#                "members"; Wisconsin's members are supervisors.
#   phrase       the body's name in running prose, lower case.
#   index_label  the breadcrumb's middle step and the topic page's own name.
#   all_label    the footer link back to that page.
INSTANCES = [
    dict(tag="il", state="Illinois", concept="county-board",
         index_page="county-board.html",
         heading="%(county)s County Board",
         page_title="%(county)s County Board members",
         phrase="county board", index_label="County boards",
         all_label="All Illinois county boards",
         app_name="districtry Illinois", app_url="https://districtry.com/il/",
         district_word="District", adapters=("il_districted", "il_at_large")),
    dict(tag="wi", state="Wisconsin", concept="county-board",
         index_page="county-board.html",
         heading="%(county)s County Board",
         page_title="%(county)s County Board supervisors",
         phrase="county board", index_label="County boards",
         all_label="All Wisconsin county boards",
         app_name="districtry Wisconsin", app_url="https://districtry.com/wi/",
         district_word="District", adapters=("wi_seats",)),
    dict(tag="ia", state="Iowa", concept="county-supervisor",
         index_page="county-supervisor.html",
         heading="%(county)s County Board of Supervisors",
         page_title="%(county)s County Board of Supervisors",
         phrase="board of supervisors", index_label="Boards of supervisors",
         all_label="All Iowa boards of supervisors",
         app_name="districtry Iowa", app_url="https://districtry.com/ia/",
         district_word="District", adapters=("ia_supervisors",)),
]


def heading_of(inst, county):
    return inst["heading"] % {"county": county}


INDEX_REGION = "county-index"

# Illinois alone needs a name table: its roster FILENAMES are slugs and its
# records carry no county field. Wisconsin's and Iowa's records name their own
# county, so those slugs are derived and no list can go stale.
IL_NAME_BY_SLUG = {slug_of(n): n for n, _ in ALL_COUNTIES}
IL_NAME_BY_UPPER = {n.upper(): n for n, _ in ALL_COUNTIES}


def county_slug(name):
    """A county name to its URL slug. Measured on the shipped rosters: 72
    Wisconsin and 17 Iowa names produce 72 and 17 distinct slugs, no
    collisions, and the five two-word Wisconsin names (Eau Claire, Fond Du Lac,
    Green Lake, La Crosse, St Croix) hyphenate cleanly."""
    return (name.lower().replace(".", "").replace("'", "")
            .replace(" ", "-").replace("--", "-"))


def app_data(tag):
    return os.path.join(REPO_ROOT, tag, "data", "app")


def out_dir(inst):
    return os.path.join(REPO_ROOT, inst["tag"], inst["concept"])


def index_page(inst):
    return os.path.join(REPO_ROOT, inst["tag"], inst["index_page"])


def district_sort_key(key):
    """Districts are '1'..'30' in most counties and letters ('A'..'N') in Clay.
    Sort numerics numerically and letters after them, so a page reads 1, 2, 10
    rather than 1, 10, 2."""
    return (0, int(key), "") if key.isdigit() else (1, 0, key)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def district(label, members=(), vacancies=0, note=None):
    """One district on a page. A DICT rather than a tuple because a district
    that names nobody can be three different things and a reader has to be told
    which: the county says the seat is vacant (`vacancies`), somebody says why
    no name can be shown (`note` — Wisconsin's one withheld district), or
    nothing is published at all (neither). Wisconsin's own card has drawn that
    distinction since it shipped; these pages draw the same one."""
    return {"label": str(label), "members": list(members),
            "vacancies": vacancies, "note": note}


def il_districted(inst):
    """Illinois: one file per county, keyed by district.

    THREE RECORD SHAPES SHARE THESE FILES, surveyed key by key rather than
    assumed, and the survey is what makes this correct:

      members[]     53 files. The district and its member list.
      a flat EXTRA  11 files carry one beside the districts — an office
                    address, a clerk phone, a meeting time, a results URL.
                    No `members`, no `name`: not a district, skipped, counted.
      a flat NAMED  the board chair in five files, and in Lake County EVERY
                    district (20 of them, `{"1": {"name": "..."}}`). A flat
                    record that names somebody is a person either way — the
                    `chair` key is the chair, anything else is that district's
                    member.

    THE FILENAME GLOB IS THREE PATTERNS, NOT ONE, and that is a defect this
    generator shipped with: `*-county-board-members.json` alone missed Menard,
    whose file is `menard-commissioner-members.json` (a commission-form county,
    named for what it elects), and Lake, whose file is
    `lake-county-board-roles.json`. Both are real Illinois counties with real
    published members and neither had a page for a day. The registration gate
    below is what found them."""
    data_dir = app_data(inst["tag"])
    paths = sorted(set(glob.glob(os.path.join(data_dir, "*-county-board-members.json"))
                       + glob.glob(os.path.join(data_dir, "*-commissioner-members.json"))
                       + glob.glob(os.path.join(data_dir, "*-county-board-roles.json"))))
    out, problems, nameless, used = {}, [], set(), []
    for path in paths:
        slug = re.sub(r"-(county-board-members|commissioner-members|"
                      r"county-board-roles)\.json$", "", os.path.basename(path))
        name = IL_NAME_BY_SLUG.get(slug)
        if name is None:
            problems.append(
                "%s names county slug %r, which build_county_status.ALL_COUNTIES "
                "does not carry — the two lists have diverged"
                % (os.path.relpath(path, REPO_ROOT), slug))
            continue
        used.append(path)
        data = _read(path)
        districts, skipped, source, extras = [], [], None, []
        for key in sorted(data, key=district_sort_key):
            entry = data[key]
            if not isinstance(entry, dict):
                skipped.append(key)
                continue
            source = source or entry.get("sourceUrl")
            if isinstance(entry.get("members"), list):
                districts.append(district(key, entry["members"],
                                          entry.get("vacancies") or 0))
            elif not (entry.get("name") or "").strip():
                skipped.append(key)          # a per-county extra, not a district
            elif key == "chair":
                chair = dict(entry)
                chair.setdefault("role", "Chair")
                extras.append(("chair", "Board chair", [chair]))
            else:
                # A district whose one member is written flat rather than in a
                # members[] list — Lake County's whole file.
                districts.append(district(key, [dict(entry)]))
        named = _count_named(districts, extras)
        if not named:
            if _nobody_key(inst, name) not in NAMES_NOBODY:
                problems.append(
                    "%s names nobody — %d key(s), no name field on any of them. "
                    "Either the roster regressed, or this county belongs in "
                    "NAMES_NOBODY with a reason"
                    % (os.path.relpath(path, REPO_ROOT), len(data)))
            nameless.add(name)
            continue
        out[name] = {"districts": districts, "sourceUrl": source, "extras": extras,
                     "skipped": skipped, "slug": slug, "at_large": False}
    return out, problems, nameless, used, None


def il_at_large(inst):
    """Illinois: the shared file for counties that elect their board countywide."""
    path = os.path.join(app_data(inst["tag"]), "il-county-commissioners.json")
    out, problems = {}, []
    for key, entry in sorted(_read(path).items()):
        name = IL_NAME_BY_UPPER.get(key)
        if name is None:
            problems.append(
                "il-county-commissioners.json names %r, which "
                "build_county_status.ALL_COUNTIES does not carry" % key)
            continue
        out[name] = {"members": entry.get("members", []),
                     "structure": entry.get("structure"),
                     "verified": entry.get("verified"),
                     "sourceUrl": entry.get("sourceUrl"),
                     "sourceDocument": entry.get("sourceDocument"),
                     "seats": entry.get("seats"),
                     "slug": slug_of(name), "at_large": True}
    return out, problems, set(), [path], None


def wi_seats(inst):
    """Wisconsin: ONE file, keyed by SEAT — <5-digit county GEOID><2-digit
    district> — with the county name on every record, so the counties are
    read from the data and nothing here lists them.

    FOUR THINGS A SEAT RECORD CAN BE, and the app's own card already draws all
    four distinctions, so these pages draw them too rather than flattening
    three of them into silence:

      a name          1,573 of 1,591 seats.
      `vacant: true`  16 seats. The county says nobody holds it.
      `withheld`      one, Lincoln District 21: the county's map and the
                      state's filing put the boundary in different places, so
                      `withheldWhy` is printed instead of a name.
      `<fips>-at-large`
                      not a district at all. Menominee seats seven for five
                      districts, the other two elected countywide, under a key
                      carrying an `atLarge` LIST. Placing those two in a
                      district would say they represent ground they do not.

    A county's `seats` count comes from county-board-directory.json where that
    file carries one, because a board of twenty showing nineteen members reads
    as complete: the difference is printed rather than left for a reader to
    notice."""
    data_dir = app_data(inst["tag"])
    path = os.path.join(data_dir, "county-board-members.json")
    dir_path = os.path.join(data_dir, "county-board-directory.json")
    directory = _read(dir_path) if os.path.exists(dir_path) else {}
    by_county, problems, nameless = {}, [], set()
    for seat, rec in sorted(_read(path).items()):
        name = (rec.get("county") or "").strip()
        if not name:
            problems.append("wi county-board-members.json seat %r carries no "
                            "county — it cannot be placed on a page" % seat)
            continue
        d = by_county.setdefault(name, {"seats": {}, "at_large": [],
                                        "geoid": seat[:5], "source": None})
        d["source"] = d["source"] or rec.get("sourceUrl")
        if isinstance(rec.get("atLarge"), list):
            for m in rec["atLarge"]:
                m = dict(m)
                m.setdefault("readOn", rec.get("readOn"))
                d["at_large"].append(m)
            continue
        if rec.get("district") is None:
            problems.append("wi county-board-members.json seat %r carries "
                            "neither a district nor an atLarge list" % seat)
            continue
        d["seats"][str(rec["district"])] = rec
    out = {}
    for name, d in sorted(by_county.items()):
        districts = []
        for label in sorted(d["seats"], key=district_sort_key):
            rec = d["seats"][label]
            if rec.get("withheld"):
                districts.append(district(label, note=rec.get("withheldWhy")))
            elif rec.get("vacant"):
                districts.append(district(label, vacancies=1))
            else:
                districts.append(district(label, [rec]))
        extras = ([("at-large", "Elected at large", d["at_large"])]
                  if d["at_large"] else [])
        named = _count_named(districts, extras)
        if not named:
            if _nobody_key(inst, name) not in NAMES_NOBODY:
                problems.append("wi %s County names nobody" % name)
            nameless.add(name)
            continue
        entry = directory.get(d["geoid"], {})
        out[name] = {"districts": districts, "sourceUrl": d["source"],
                     "extras": extras, "skipped": [], "slug": county_slug(name),
                     "at_large": False, "seats": entry.get("seats")}
    used = [path] + ([dir_path] if directory else [])
    return out, problems, nameless, used, None


def ia_supervisors(inst):
    """Iowa: ONE file keyed by county code, each carrying a `districts` object
    of {label: {name, party}} and the board's own phone.

    THE CHAIR IS A ROLE ON A SUPERVISOR, NOT A SEPARATE OFFICEHOLDER, which is
    the opposite of Illinois: an Illinois county that publishes a chair elects
    that person countywide and names them in no district, while Iowa's chair is
    one of the supervisors the board itself picks. So ia-county-board-chairs.json
    sets a `role` on the matching member rather than adding a section, and a
    chair who matches nobody in the county's own district list is reported
    rather than shipped as an extra person.

    That file names a chair for 43 counties and this roster covers 17, so 26
    counties have a chair and no board list. They get no page: one name and a
    link is the thin shape the per-county decision rejected in the first place,
    and the count is printed on every run so the absence is visible."""
    data_dir = app_data(inst["tag"])
    path = os.path.join(data_dir, "ia-supervisor-members.json")
    chair_path = os.path.join(data_dir, "ia-county-board-chairs.json")
    chairs = {}
    if os.path.exists(chair_path):
        for rec in _read(chair_path).values():
            if (rec.get("county") or "").strip() and (rec.get("chair") or "").strip():
                chairs[rec["county"].strip()] = rec["chair"].strip()
    out, problems, nameless, chaired = {}, [], set(), 0
    for code, rec in sorted(_read(path).items()):
        name = (rec.get("county") or "").strip()
        if not name:
            problems.append("ia-supervisor-members.json %r carries no county" % code)
            continue
        districts = []
        for label in sorted(rec.get("districts") or {}, key=district_sort_key):
            m = dict((rec["districts"] or {})[label])
            if rec.get("boardPhone") and not m.get("phone"):
                # The board's own number, the only one the roster carries, and
                # the same one the app's card shows for every supervisor.
                m["phone"] = rec["boardPhone"]
            districts.append(district(label, [m]))
        chair = chairs.get(name)
        if chair:
            hit = [m for d in districts for m in d["members"]
                   if (m.get("name") or "").strip() == chair]
            if hit:
                hit[0]["role"] = "Chair"
                chaired += 1
            else:
                problems.append(
                    "ia-county-board-chairs.json names %s as %s County's chair "
                    "and no supervisor in ia-supervisor-members.json has that "
                    "name — the two rosters disagree about who is on the board"
                    % (chair, name))
        named = _count_named(districts, [])
        if not named:
            if _nobody_key(inst, name) not in NAMES_NOBODY:
                problems.append("ia %s County names nobody" % name)
            nameless.add(name)
            continue
        out[name] = {"districts": districts, "sourceUrl": rec.get("sourceUrl"),
                     "extras": [], "skipped": [], "slug": county_slug(name),
                     "at_large": False}
    note = ("%d of %d chair(s) joined; %d Iowa county board(s) have a published "
            "chair and no member list, so no page"
            % (chaired, len(out), max(0, len(chairs) - len(out))))
    return out, problems, nameless, [path] + ([chair_path] if chairs else []), note


def _nobody_key(inst, county):
    return "%s/%s" % (inst["tag"], county)


def _count_named(districts, extras):
    n = sum(1 for d in districts for m in d["members"]
            if (m.get("name") or "").strip())
    return n + sum(1 for _a, _h, ms in extras for m in ms
                   if (m.get("name") or "").strip())


# Every adapter returns (counties, problems, nameless, paths_read, note):
#   counties    {county name: record} — the pages to write.
#   problems    anything that should fail the build, in words.
#   nameless    counties whose roster named nobody, checked against NAMES_NOBODY.
#   paths_read  the roster files it read, which is what check_workflows() holds
#               the weekly jobs to. Derived, so a new roster file is covered by
#               the gate the moment an adapter reads it.
#   note        one line for the OK output, or None.
ADAPTERS = {"il_districted": il_districted, "il_at_large": il_at_large,
            "wi_seats": wi_seats, "ia_supervisors": ia_supervisors}


# Party, as the fleet's rosters actually spell it. MEASURED 2026-09-13 across
# the three instances: five spellings for two parties — Republican 1,347 / R
# 170 / (R) 7, and Democratic 365 / Democrat 152 / D 33 / (D) 18 — plus
# Independent 24, "No party" 10 and one Libertarian. Each county's own page is
# internally consistent and the fleet is not, so a page printing them verbatim
# says "R" beside one name and "Republican" beside the next.
#
# THIS NORMALISES NOTATION AND DECIDES NOTHING ABOUT A PERSON: every entry is
# one party under another spelling, and a value not in the table ships exactly
# as the county published it rather than being guessed at.
PARTY_NAMES = {
    "r": "Republican", "(r)": "Republican", "rep": "Republican",
    "republican": "Republican",
    "d": "Democratic", "(d)": "Democratic", "dem": "Democratic",
    "democrat": "Democratic", "democratic": "Democratic",
    "i": "Independent", "(i)": "Independent", "independent": "Independent",
    "l": "Libertarian", "libertarian": "Libertarian",
}


def party_name(value):
    v = (value or "").strip()
    return PARTY_NAMES.get(v.lower(), v)


def member_html(m):
    """One member. Every field is optional and an absent one is absent from the
    markup — a roster that does not publish a phone must not render an empty
    row that reads as one.

    `url` and `profileUrl` are the SAME FIELD under two names: Illinois's
    builders write the first, Wisconsin's the second, and reading only one
    would drop 164 Wisconsin supervisor pages without anything saying so.
    `documentUrl` is a third thing rather than a third name — where a county
    publishes its board in a document and not on a page, that document is the
    only place the name is checkable (Adams County's board page names none of
    its twenty supervisors), so it is labelled for what it is."""
    name = (m.get("name") or "").strip()
    if not name:
        return None
    bits = ['<span class="m-name">%s</span>' % esc(name)]
    role = (m.get("role") or "").strip()
    if role:
        bits.append('<span class="m-role">%s</span>' % esc(role))
    party = party_name(m.get("party"))
    if party:
        bits.append('<span class="m-party">%s</span>' % esc(party))
    contact = []
    email = (m.get("email") or "").strip()
    if email:
        contact.append('<a href="mailto:%s">%s</a>' % (esc(email), esc(email)))
    phone = (m.get("phone") or "").strip()
    if phone:
        contact.append('<a href="tel:%s">%s</a>'
                       % (esc(re.sub(r"[^0-9+]", "", phone)), esc(phone)))
    for field, label in (("url", "Official profile"),
                         ("profileUrl", "Official profile"),
                         ("documentUrl", "County directory")):
        url = (m.get(field) or "").strip()
        if url.startswith("http"):
            contact.append('<a href="%s" rel="noopener" target="_blank">%s</a>'
                           % (esc(url), label))
            if label == "Official profile":
                break
    if contact:
        bits.append('<span class="m-contact">%s</span>' % " · ".join(contact))
    fresh = freshness(m)
    if fresh:
        bits.append('<span class="m-asof">%s</span>' % fresh)
    return '<li class="member">%s</li>' % "".join(bits)


def freshness(m):
    """How old this name is, in the app's own three branches.

    A NAME WITH NO DATE READS AS TODAY'S. Wisconsin's card learned that the
    hard way — the row was lost in a merge and 63 dated captures read as weekly
    re-reads for as long as it was gone — so where the roster carries the date,
    the page carries it too. Illinois's per-county rosters carry none of these
    fields and render nothing, exactly as before."""
    as_of = (m.get("asOf") or "").strip()
    if as_of:
        why = (m.get("asOfWhy") or "").strip()
        return esc("From %s. %s" % (as_of, why or
                   "The county's website refuses automated readers, so this "
                   "name is a dated capture rather than the weekly re-read the "
                   "other named counties get."))
    read_on = (m.get("readOn") or "").strip()
    if not read_on:
        return ""
    via = (m.get("readVia") or "").strip()
    if via:
        return esc("Read from %s's capture of %s. That is the day the copy was "
                   "taken, not the day it was fetched." % (via, read_on))
    return esc("Read on %s, and re-read every week." % read_on)


def districted_body(inst, name, rec):
    seats = sum(len(d["members"]) for d in rec["districts"])
    named = _count_named(rec["districts"], [])
    extra_named = _count_named([], rec.get("extras") or [])
    n_dist = len(rec["districts"])
    out = []
    out.append(
        '<p class="lede">The %s is elected by district. This page '
        'lists %s %s and the %s who %s them, exactly as the county publishes '
        'them — it is the same roster the map\'s %s card reads.</p>'
        % (esc(heading_of(inst, name)), n_dist,
           "district" if n_dist == 1 else "districts",
           "member" if named == 1 else "%d members" % named,
           "holds" if named == 1 else "hold", esc(inst["phrase"])))
    out.append('<a class="cta" href="../#layers=%s,county">'
               'Find your %s County district on the map →</a>'
               % (esc(inst["concept"]), esc(name)))
    out.append('<p class="cta-note">Opens the map with the county and %s '
               'layers on. Search your address or ZIP, or tap your location.</p>'
               % esc(inst["phrase"]))
    for anchor, heading, members in rec.get("extras") or []:
        rows = [h for h in (member_html(m) for m in members) if h]
        if not rows:
            continue
        out.append('<section class="district" id="%s">' % esc(anchor))
        out.append('<h2>%s</h2>' % esc(heading))
        out.append('<ul class="members">%s</ul>' % "".join(rows))
        out.append('</section>')
    for d in rec["districts"]:
        label = d["label"]
        anchor = "district-%s" % re.sub(r"[^A-Za-z0-9]+", "-", label).lower()
        out.append('<section class="district" id="%s">' % esc(anchor))
        out.append('<h2>%s %s</h2>' % (esc(inst["district_word"]), esc(label)))
        rows = [h for h in (member_html(m) for m in d["members"]) if h]
        if rows:
            out.append('<ul class="members">%s</ul>' % "".join(rows))
        if d["vacancies"]:
            # A VACANCY IS NOT AN ABSENT NAME, and saying "not listed" about a
            # seat the county has explicitly reported open is a false statement
            # about the county rather than a gap in this project. The app's own
            # card has always distinguished the two ("N of M seats is vacant");
            # the first draft of this page did not, and Jo Daviess's District 10
            # is exactly the case — filled last week, reported vacant this week.
            out.append('<p class="unlisted">%d of %d seat%s here %s vacant, '
                       'as the county reports it.</p>'
                       % (d["vacancies"], len(rows) + d["vacancies"],
                          "" if len(rows) + d["vacancies"] == 1 else "s",
                          "is" if d["vacancies"] == 1 else "are"))
        elif d["note"]:
            # A THIRD STATE: somebody holds this seat and this project will not
            # say who, with the reason printed. Wisconsin's Lincoln District 21
            # is the one — its county's map and the state's filing disagree
            # about the boundary — and reading that as a vacancy or as silence
            # would both be false.
            out.append('<p class="unlisted">Not named — %s</p>' % esc(d["note"]))
        elif not rows:
            # No name, no vacancy, no stated reason: the county's own source
            # does not say. A district dropped from the page would read as a
            # board of n-1.
            out.append('<p class="unlisted">Not listed in the county\'s '
                       'directory.</p>')
        out.append('</section>')
    unnamed = seats - named
    if unnamed:
        out.append('<p class="unlisted">%d of %d listed seats are not named by '
                   'the county\'s own source.</p>' % (unnamed, seats))
    board_seats = rec.get("seats")
    if board_seats and board_seats > n_dist:
        # The board's OWN size, where the county publishes one and it is bigger
        # than the district count — Menominee seats seven for five districts.
        # A page listing five districts beside a board of seven has to say so.
        out.append('<p class="unlisted">The county reports a board of %d seat%s, '
                   'which is %d more than the %d district%s above.</p>'
                   % (board_seats, "" if board_seats == 1 else "s",
                      board_seats - n_dist, n_dist, "" if n_dist == 1 else "s"))
    return "\n".join(out), n_dist, named + extra_named


def at_large_body(inst, name, rec):
    members = rec["members"]
    named = sum(1 for m in members if (m.get("name") or "").strip())
    out = []
    out.append(
        '<p class="lede">%s County elects its %s <b>at large</b> — every '
        'member is chosen countywide, so there are no board districts to be in. '
        'These %s represent the whole county.</p>'
        % (esc(name), esc(inst["phrase"]),
           "is the one member who represents" if named == 1
           else "%d members" % named))
    if rec.get("structure"):
        out.append('<p class="structure">%s</p>' % esc(rec["structure"]))
    rows = [h for h in (member_html(m) for m in members) if h]
    out.append('<section class="district" id="members">')
    out.append('<h2>Members</h2>')
    out.append('<ul class="members">%s</ul>' % "".join(rows) if rows else
               '<p class="unlisted">Not listed in the county\'s directory.</p>')
    out.append('</section>')
    if rec.get("seats") and rec["seats"] > named:
        out.append('<p class="unlisted">%d of %d seats are not named by the '
                   'county\'s own source.</p>' % (rec["seats"] - named, rec["seats"]))
    out.append('<a class="cta" href="../#layers=county">'
               'See %s County on the map →</a>' % esc(name))
    out.append('<p class="cta-note">Opens the map with the county layer on. An '
               'at-large board has no district geometry, so the members above '
               'are the answer for anywhere in the county.</p>')
    return "\n".join(out), 0, named


def source_note(rec, at_large):
    """Where the names came from, in the page's own words. A page that names
    people without saying who published them is the thing this project refuses
    everywhere else."""
    bits = []
    if at_large:
        if rec.get("sourceDocument"):
            bits.append("Source: %s." % esc(rec["sourceDocument"]))
        elif rec.get("sourceUrl"):
            bits.append('Source: <a href="%s" rel="noopener" target="_blank">the '
                        "county's own published roster</a>." % esc(rec["sourceUrl"]))
        if rec.get("verified"):
            bits.append("Verified %s." % esc(rec["verified"]))
    elif rec.get("sourceUrl"):
        bits.append('Source: <a href="%s" rel="noopener" target="_blank">the '
                    "county's own published roster</a>, re-read on a schedule "
                    "and landed as a reviewed pull request." % esc(rec["sourceUrl"]))
    if not bits:
        return ""
    return '<p class="source-note">%s</p>' % " ".join(bits)


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>%(title)s</title>
<meta name="description" content="%(desc)s" />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="%(canonical)s" />
<link rel="icon" href="%(favicon)s" type="image/svg+xml" />
<meta property="og:type" content="article" />
<meta property="og:site_name" content="%(app_name)s" />
<meta property="og:title" content="%(title)s" />
<meta property="og:description" content="%(desc)s" />
<meta property="og:url" content="%(canonical)s" />
<meta property="og:image" content="%(og_image)s" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:locale" content="en_US" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="%(title)s" />
<meta name="twitter:description" content="%(desc)s" />
<meta name="twitter:image" content="%(og_image)s" />
<!-- GENERATED by scripts/build_county_pages.py from the shipped roster this
     county's own card reads. Do NOT hand-edit: `--check` fails the build, and
     a hand edit here would make the page and the card disagree about a real
     person. Fix the roster, or the scraper that writes it. -->
<script>
(function () {
  try {
    var stored = localStorage.getItem("districtry-theme");
    if (stored === "dark" || stored === "light") {
      document.documentElement.setAttribute("data-theme", stored);
    }
  } catch (e) { /* blocked storage — prefers-color-scheme decides */ }
})();
</script>
<style>
%(fontface)s

:root {
  color-scheme: light dark;
%(light)s
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
%(dark)s
  }
}
:root[data-theme="dark"] {
%(dark)s
}

* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font: 400 16px/1.6 var(--font-body);
  -webkit-text-size-adjust: 100%%;
}
a { color: var(--brand-700); }
:focus-visible { outline: 3px solid var(--brand-600); outline-offset: 2px; }

/* Focus-only, and the pair validate_contrast.py measures as (paper, ink):
   16.08:1 light and 15.36:1 dark. */
.skip-link {
  position: absolute; left: -9999px; top: 0;
  background: var(--ink); color: var(--paper);
  padding: 10px 16px; z-index: 10; border-radius: 0 0 6px 0;
}
.skip-link:focus { left: 0; }

main { max-width: 760px; margin: 0 auto; padding: 40px 20px 64px; }
.kicker {
  font: 600 13px/1 var(--font-body); letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--muted); margin: 0 0 10px;
}
.kicker a { color: inherit; text-decoration: none; }
h1 {
  font: var(--font-heading-weight, 700) clamp(26px, 5vw, 34px)/1.15 var(--font-heading);
  margin: 0 0 6px; text-transform: uppercase; letter-spacing: 0.01em;
}
.title-sub { color: var(--ink-3); margin: 0 0 18px; font-size: 15px; }
.lede { color: var(--ink-2); margin: 0 0 16px; }
.structure {
  font-size: 14px; color: var(--muted); border-left: 3px solid var(--brand-border);
  padding: 2px 0 2px 12px; margin: 0 0 16px;
}
.cta {
  display: inline-block; margin: 6px 0 4px; padding: 11px 18px;
  background: var(--brand-700); color: var(--paper);
  border-radius: var(--radius-btn); font-weight: 600; text-decoration: none;
}
.cta:hover { background: var(--brand-600); }
.cta-note { font-size: 13px; color: var(--muted); margin: 6px 0 26px; }

.district { margin: 0 0 6px; padding: 14px 0 2px; border-top: 1px solid var(--border); }
.district h2 {
  font: var(--font-heading-weight, 700) 19px/1.2 var(--font-heading);
  margin: 0 0 8px; text-transform: uppercase; letter-spacing: 0.02em;
}
.members { list-style: none; margin: 0; padding: 0; }
.member { margin: 0 0 12px; }
.m-name { display: block; font-weight: 650; }
.m-role { display: block; font-size: 13px; color: var(--muted); }
.m-party { display: block; font-size: 13px; color: var(--muted); }
/* How old the name is. Small, and under the contact details rather than over
   them, because it qualifies the name rather than competing with it — but it is
   on the page, because a name with no date reads as today's. */
.m-asof { display: block; font-size: 12.5px; color: var(--muted); margin-top: 2px; }
/* line-height 28px, the WCAG 2.5.8 spacing floor the landing and history
   footers were fixed to on 2026-09-13: these are 13.5px links that wrap. */
.m-contact { display: block; font-size: 13.5px; line-height: 28px; }
.unlisted { color: var(--muted); font-size: 14px; margin: 0 0 12px; }
.source-note {
  margin: 22px 0 0; padding: 12px 14px; font-size: 13.5px; color: var(--ink-3);
  background: var(--surface-2); border-radius: var(--radius-card);
}
.disclaimer { font-size: 13px; color: var(--muted); margin: 14px 0 0; }
.foot {
  margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--border);
  font-size: 14px; line-height: 28px; color: var(--muted);
}
.foot a { margin-right: 14px; }
</style>
<script type="application/ld+json">
%(jsonld)s
</script>
</head>
<body>
<a href="#page-main" class="skip-link">Skip to content</a>
<main id="page-main">
<p class="kicker">%(mark)s<a href="../">districtry / illinois</a></p>
<h1>%(h1)s</h1>
<p class="title-sub">%(standfirst)s</p>
%(body)s
%(source)s
<p class="disclaimer">districtry is an independent, unofficial civic reference.
It never guesses at who holds a seat: every name above is published by the
county itself, and where a county publishes none this page says so rather than
filling the gap.</p>
<p class="foot">
<a href="../%(index_page)s">%(all_label)s</a>
<a href="../">Back to the map</a>
<a href="../sources.html">Sources &amp; data layers</a>
<a href="../faq.html">Common questions</a>
<a href="../../privacy.html">Privacy</a>
<a href="https://overberg.co/why/" target="_blank" rel="noopener">Why this exists</a>
</p>
%(byline)s
</main>
</body>
</html>
"""


def mark_svg():
    """The same inline mark the history pages carry, read from the one file."""
    svg = read(FAVICON, "the brand mark").strip()
    svg = svg.replace("<svg ", '<svg class="districtry-mark" width="18" height="18" '
                               'aria-hidden="true" style="vertical-align:-3px;'
                               'margin-right:6px" ', 1)
    return svg


def build_page(inst, name, rec, at_large, shell):
    slug = rec["slug"]
    canonical = "%s%s/%s.html" % (inst["app_url"], inst["concept"], slug)
    body, n_dist, named = (at_large_body(inst, name, rec) if at_large
                           else districted_body(inst, name, rec))[:3]
    head = heading_of(inst, name)
    title = "%s — %s" % (inst["page_title"] % {"county": name}, inst["app_name"])
    if at_large:
        desc = ("Who sits on the %s: %d members elected at "
                "large across the whole county, with contact details, from the "
                "county's own published roster." % (head, named))
    else:
        # `named` counts the EXTRA sections too — Illinois's elected chair,
        # Menominee's two at-large supervisors — and none of those people is in
        # any district (checked: no chair's name appears in that county's own
        # district list). So the description gives the district figure and says
        # what the extras are rather than printing a total the page never shows.
        extras = rec.get("extras") or []
        extra_n = sum(1 for _a, _h, ms in extras for m in ms
                      if (m.get("name") or "").strip())
        extra_words = {"chair": "the elected chair",
                       "at-large": "%d elected at large" % extra_n}
        # 155 characters is the gate's ceiling (scripts/validate_serp_lengths.py)
        # and the longest county name plus the longest suffix ran to 160, so
        # the contact clause goes rather than the counts, which are what make
        # one of these 73 descriptions different from the next.
        suffix = ", ".join(extra_words.get(a, "%d more" % extra_n)
                           for a, _h, ms in extras if ms)
        desc = ("Who represents you on the %s — %d members across "
                "%d districts%s, from the county's own published roster."
                % (head, named - extra_n, n_dist,
                   " plus " + suffix if suffix else ""))
    standfirst = ("Every member of the %s, from the county's own "
                  "published roster." % head)

    graph = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": canonical,
        "url": canonical,
        "name": title,
        "description": desc,
        "inLanguage": "en-US",
        "about": {"@type": "GovernmentOrganization",
                  "name": head,
                  "areaServed": {"@type": "AdministrativeArea",
                                 "name": "%s County, %s"
                                         % (name, inst["state"])}},
        "author": {
            "@type": "Person",
            "@id": "https://districtry.com/#author",
            "name": "Adam Overberg",
            "url": "https://overberg.co",
            "email": "hello@overberg.co",
        },
        "isPartOf": {"@id": inst["app_url"] + "#website"},
        "breadcrumb": {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": inst["app_name"],
                 "item": inst["app_url"]},
                {"@type": "ListItem", "position": 2,
                 "name": inst["index_label"],
                 "item": inst["app_url"] + inst["index_page"]},
                {"@type": "ListItem", "position": 3,
                 "name": "%s County" % name},
            ],
        },
    }
    jsonld = json.dumps(graph, indent=2, ensure_ascii=False).replace("</", "<\\/")

    return PAGE % dict(
        shell,
        title=esc(title), desc=esc(desc), canonical=esc(canonical),
        h1=esc(head), standfirst=esc(standfirst),
        body=body, source=source_note(rec, at_large), jsonld=jsonld,
        og_image=esc(inst["app_url"] + "og-image.png"),
        app_name=esc(inst["app_name"]), index_page=esc(inst["index_page"]),
        all_label=esc(inst["all_label"]),
    )


def render_index(inst, rows):
    """rows: [(county name, slug, at_large, seats)] — the index the topic page
    carries. Alphabetical, one flat list: a reader looking for their county
    scans a name, and a crawler gets 73 internal links from a page that already
    ranks for the concept."""
    out = ['    <p class="matrix-lede">Every %s county whose roster this '
           'project has: <b>%d counties</b>, <b>%d people</b>, each name published '
           'by the county itself.%s</p>'
           % (esc(inst["state"]), len(rows), sum(r[3] for r in rows),
              (" %d elect at large, with no districts." % sum(1 for r in rows if r[2]))
              if any(r[2] for r in rows) else ""),
           '    <ul class="county-index">']
    for name, slug, at_large, seats in rows:
        out.append('      <li><a href="%s/%s.html">%s County</a> '
                   '<span class="county-index-n">%d %s%s</span></li>'
                   % (esc(inst["concept"]), esc(slug), esc(name), seats,
                      "member" if seats == 1 else "members",
                      ", at large" if at_large else ""))
    out.append("    </ul>")
    return "\n".join(out)


def write_index(inst, rows, check):
    """Splice render_index() into the topic page's GENERATED region."""
    page = index_page(inst)
    with open(page, encoding="utf-8", newline="") as f:
        text = f.read()
    begin = "<!-- ==== GENERATED:BEGIN %s ==== -->" % INDEX_REGION
    end = "<!-- ==== GENERATED:END %s ==== -->" % INDEX_REGION
    if begin not in text or end not in text:
        fail("%s carries no GENERATED region %r — the index has nowhere to go"
             % (os.path.relpath(page, REPO_ROOT), INDEX_REGION))
    head, rest = text.split(begin, 1)
    _, tail = rest.split(end, 1)
    new = head + begin + "\n" + render_index(inst, rows) + "\n    " + end + tail
    if new == text:
        return False
    if not check:
        with open(page, "w", encoding="utf-8", newline="") as f:
            f.write(new)
    return True


def roster_names(rec, at_large):
    """Every person the roster names for this county, chair included."""
    names = []
    if at_large:
        names += [m.get("name") for m in rec["members"]]
    else:
        names += [m.get("name") for d in rec["districts"] for m in d["members"]]
        names += [m.get("name") for _a, _h, ms in rec.get("extras") or []
                  for m in ms]
    return [n.strip() for n in names if (n or "").strip()]


def verify_page(inst, name, rec, at_large, html):
    """The check this work exists to pass: the page NAMES THE PEOPLE.

    Byte-equality against a regenerate already proves the page matches the
    template. It cannot prove the template puts the roster on the page — a
    generator that emitted a beautiful, correct, empty page would pass it every
    time. So this reads the shipped HTML back and asserts, per county, that
    every name in the roster appears in it and that at least one does.

    Names are compared HTML-ESCAPED, because that is what is on the page:
    O'Brien ships as O&#x27;Brien, and comparing the raw name would report a
    real, present officeholder as missing.
    """
    problems = []
    names = roster_names(rec, at_large)
    if not names:
        return ["%s: the page names nobody" % name]
    missing = [n for n in names if esc(n) not in html]
    if missing:
        problems.append(
            "%s: %d roster name(s) do not appear on the page it generated — %s"
            % (name, len(missing), ", ".join(missing[:4])))
    # Every district heading, too: a district dropped from the page reads to a
    # reader as a board one seat smaller than it is.
    if not at_large:
        for d in rec["districts"]:
            if ("<h2>%s %s</h2>"
                    % (esc(inst["district_word"]), esc(d["label"]))) not in html:
                problems.append("%s: district %s has no section on its page"
                                % (name, d["label"]))
    return problems


WORKFLOW_DIR = os.path.join(REPO_ROOT, ".github", "workflows")


def check_workflows(read_by_instance):
    """Every weekly job that rewrites a roster these pages read must regenerate
    them in the same run, and must stage THAT INSTANCE'S pages.

    60 workflows rewrite one, and a job that refreshes a roster without
    regenerating opens a bot PR carrying last week's names on a page and this
    week's in the JSON — and fails --check on a PR nobody wrote by hand, which
    is the worst place to discover a convention. The history page has needed
    exactly this rule since it shipped and enforces it nowhere; three workflows
    carry it because someone remembered.

    THE ROSTER LIST IS DERIVED FROM WHAT THE ADAPTERS ACTUALLY READ, not from a
    filename pattern, and the first version was a pattern
    (`[a-z-]+-county-board-members\.json`) which had two defects at once. It
    missed Menard and Lake, whose files are named for what those counties elect
    rather than to the pattern — so two workflows rewrote a roster this builder
    reads and were never asked to regenerate. And it matched Wisconsin's
    `county-board-members.json` by accident, so the one workflow that DID have
    to learn something new passed by staging Illinois's pages for a change to
    Wisconsin's roster. A pattern cannot tell which instance a file belongs to;
    the path can, so the check is per (instance, file).

    A workflow that WRITES no file is not asked to regenerate: the Mason
    watcher reads its source and opens nothing, so requiring a build step of it
    would be requiring a no-op.
    """
    problems = []
    for path in sorted(glob.glob(os.path.join(WORKFLOW_DIR, "*.yml"))):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if "git add " not in text:
            continue                      # a watcher: reads, commits nothing
        rel = os.path.relpath(path, REPO_ROOT)
        for inst in INSTANCES:
            hits = [r for r in read_by_instance.get(inst["tag"], ())
                    if "%s/data/app/%s" % (inst["tag"], r) in text]
            if not hits:
                continue
            if "scripts/build_county_pages.py" not in text:
                problems.append(
                    "%s rewrites %s and never runs scripts/build_county_pages.py "
                    "— its bot PR would ship a page naming the members it just "
                    "replaced" % (rel, ", ".join(sorted(hits))))
            staged = [ln for ln in text.splitlines() if "git add " in ln]
            want = "%s/%s" % (inst["tag"], inst["concept"])
            if not any(want in ln for ln in staged):
                problems.append(
                    "%s rewrites %s and stages no %s/ — the regenerated pages "
                    "would not be in its commit"
                    % (rel, ", ".join(sorted(hits)), want))
    return problems


# A roster this builder does NOT read, and why that is right rather than an
# oversight. The detector below finds every data/app file whose records name
# people and look county-shaped; everything it finds has to be either consumed
# by an adapter or named here with a reason and a date. Re-audited every run:
# an entry naming a file that has left the tree FAILS, which is the property
# ACCEPTED_DROPS had to be given after the fact.
#
# THIS IS THE WHOLE "AS COUNTIES COME ONLINE IN NEW STATES" MECHANISM, and it
# is deliberately a gate rather than a generator. A new state's county roster
# cannot ship quietly: the day it lands, this check fails with the file's name
# and the two ways to clear it — add an adapter, or write down why these pages
# are the wrong home for it. Nobody has to remember, and nothing is generated
# from a guess about a shape nobody has looked at.
NOT_COUNTY_BOARDS = {
    "il/data/app/municipal-officials.json": dict(
        date="2026-09-13",
        reason="mayors, clerks and council members of 1,300 Illinois "
               "municipalities. Real officeholders, named, and not county "
               "government — a village trustee belongs on a municipal page, "
               "which is its own piece of work.",
    ),
    "il/data/app/township-officials.json": dict(
        date="2026-09-13",
        reason="township supervisors, clerks and assessors. A township is a "
               "unit below the county, not the county board.",
    ),
    "wi/data/app/wi-county-clerks.json": dict(
        date="2026-09-13",
        reason="the county CLERK, an administrative officer, one per county. "
               "Not a board member, and a page per clerk would be one name.",
    ),
    "wi/data/app/wi-municipal-clerks.json": dict(
        date="2026-09-13",
        reason="municipal clerks, 1,850 of them. Municipal, not county.",
    ),
    "ia/data/app/ia-county-auditors.json": dict(
        date="2026-09-13",
        reason="the county auditor, who runs elections. One per county, not a "
               "supervisor.",
    ),
    "wi/data/app/wi-county-officers.json": dict(
        date="2026-09-13",
        reason="the county's other elected officers — sheriff, treasurer, "
               "register of deeds, clerk of circuit court, district attorney — "
               "plus the board chair's name. Row officers are a different "
               "concept from the board, and the chair is already a supervisor "
               "on these pages where the two rosters agree: 58 of the 69 chairs "
               "it names appear in wi/data/app/county-board-members.json by "
               "name, 11 do not (measured 2026-09-13), so joining on it would "
               "have to settle eleven disagreements first.",
    ),
    "ia/data/app/ia-county-officers.json": dict(
        date="2026-09-13",
        reason="the county's other elected officers — sheriff, treasurer, "
               "recorder, county attorney — for all 99 counties. Row officers, "
               "not supervisors; the supervisors are in "
               "ia/data/app/ia-supervisor-members.json, which these pages read.",
    ),
    "ca/data/app/sf-supervisor-members.json": dict(
        date="2026-09-13",
        reason="San Francisco's Board of Supervisors is a CITY council that "
               "happens to be called a board of supervisors — the city and the "
               "county are one government. It has no county siblings to index "
               "beside, so these pages have no shape to put it in.",
    ),
}

_NAME_FIELDS = ("name", "chair", "member", "supervisor", "commissioner")
_COUNTY_WORDS = re.compile(r"county-board|county-commission|commissioner|"
                           r"supervisor|county-officer")


def _names_people(obj):
    """Does this record name a person? Any of a handful of fields carrying a
    non-empty string, at any nesting this project's rosters actually use."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in _NAME_FIELDS and isinstance(v, str) and v.strip():
                return True
            if isinstance(v, (dict, list)) and _names_people(v):
                return True
    elif isinstance(obj, list):
        return any(_names_people(v) for v in obj)
    return False


def check_registration(read_paths):
    """Find a county officeholder roster nothing here has looked at.

    THE TREE IS CANONICAL, NEVER A TABLE — the same rule
    validate_instance_registration.py discovers instances by, and for the same
    reason: a hand-kept list of rosters would let this gate agree with itself
    about a state nobody registered. So it walks every instance's data/app and
    flags a file whose records mostly name people AND whose shape or filename
    says county, then subtracts what the adapters read and what
    NOT_COUNTY_BOARDS accounts for.

    Two signals, not one, because each alone is wrong. A filename match alone
    flags county-officers files that carry no names. A name match alone flags
    every roster in the fleet, 222 of them, which is a gate nobody would keep.
    """
    problems = []
    read = {os.path.relpath(p, REPO_ROOT) for p in read_paths}
    found = []
    for tag in sorted(d for d in os.listdir(REPO_ROOT)
                      if os.path.isdir(os.path.join(REPO_ROOT, d, "data", "app"))
                      and os.path.exists(os.path.join(REPO_ROOT, d, "index.html"))):
        for path in sorted(glob.glob(os.path.join(app_data(tag), "*.json"))):
            rel = os.path.relpath(path, REPO_ROOT)
            if rel in read:
                continue
            try:
                data = _read(path)
            except (ValueError, OSError):
                continue
            if isinstance(data, dict) and data.get("type") == "FeatureCollection":
                # GEOMETRY, NOT A ROSTER, and it has to be excluded
                # STRUCTURALLY rather than by name: four of these carry a
                # district's representative in the feature properties, so they
                # name real people and a name test alone flags them. A
                # FeatureCollection is boundaries — the thing the county
                # dispatch table reads — and a page cannot be built from it.
                continue
            recs = (list(data.values()) if isinstance(data, dict)
                    else data if isinstance(data, list) else [])
            if not recs:
                continue
            named = sum(1 for r in recs if _names_people(r))
            if named * 2 < len(recs):
                continue
            county_keyed = sum(1 for r in recs if isinstance(r, dict)
                               and (r.get("county") or "").strip())
            if not (county_keyed * 2 >= len(recs)
                    or _COUNTY_WORDS.search(os.path.basename(path))):
                continue
            found.append((rel, len(recs), named))
    for rel, n, named in found:
        if rel in NOT_COUNTY_BOARDS:
            continue
        problems.append(
            "%s names people (%d of %d records) and looks like county "
            "officeholders, and no adapter reads it. Either add one to "
            "INSTANCES/ADAPTERS so its counties get pages, or record it in "
            "NOT_COUNTY_BOARDS with a reason" % (rel, named, n))
    for rel, entry in sorted(NOT_COUNTY_BOARDS.items()):
        if not os.path.exists(os.path.join(REPO_ROOT, rel)):
            problems.append(
                "NOT_COUNTY_BOARDS records %s (%s) and that file is not in the "
                "tree — drop the entry" % (rel, entry["date"]))
        elif rel in read:
            problems.append(
                "NOT_COUNTY_BOARDS records %s (%s) as not a county board and an "
                "adapter now reads it — drop the entry" % (rel, entry["date"]))
    return problems, found


def shell_for_pages():
    """The styling every page shares, read from the files that own it."""
    tokens_css = read(TOKENS, "the design tokens")
    favicon = read(FAVICON, "the brand mark").strip()
    if not favicon.startswith("<svg"):
        fail("favicon.svg does not start with <svg — is it still an SVG?")
    # The font CSS is written for a page at the instance ROOT — `url(fonts/…)`
    # — and these pages sit one level deeper under <tag>/<concept>/, where that
    # resolves to <tag>/<concept>/fonts/ and 404s. Every face, silently, on
    # every page: the app would render in system fonts and nothing would say
    # so. That is the defect Michigan's go-live found the hard way (mi/fonts/
    # did not exist while 18 @font-face rules named it); here
    # scripts/validate_instance_assets.py named all 584 references before the
    # pages shipped, which is the gate doing exactly what it was written for.
    fontface = read(FONTFACE, "the self-hosted font CSS").rstrip("\n")
    depth_fixed = fontface.replace("url(fonts/", "url(../fonts/")
    if depth_fixed == fontface and "url(" in fontface:
        fail("the font CSS no longer writes url(fonts/…), so the ../ hop these "
             "pages need was not applied — check %s"
             % os.path.relpath(FONTFACE, REPO_ROOT))
    return {
        "fontface": depth_fixed,
        "light": token_css(LIGHT_TOKENS, parse_token_block(tokens_css, ":root", TOKENS),
                           ":root"),
        "dark": token_css(DARK_TOKENS,
                          parse_token_block(tokens_css, '[data-theme="dark"]', TOKENS),
                          '[data-theme="dark"]', DARK_EXTRA, indent="    "),
        "favicon": "data:image/svg+xml," + urllib.parse.quote(favicon, safe=""),
        "mark": mark_svg(),
        "byline": shared_footer_byline(),
    }


def load_instance(inst):
    """Every adapter this instance declares, merged. A county that turns up in
    two of them is an error rather than a pick: Illinois's districted and
    at-large rosters are two ways of electing one board, so a county in both
    means one of the two files is wrong about it."""
    counties, problems, nameless, paths, notes = {}, [], set(), [], []
    for key in inst["adapters"]:
        if key not in ADAPTERS:
            fail("instance %s names adapter %r, which ADAPTERS does not carry"
                 % (inst["tag"], key))
        out, probs, none_named, used, note = ADAPTERS[key](inst)
        both = sorted(set(counties) & set(out))
        if both:
            problems.append(
                "%s: %s appear in two of this instance's rosters — one county "
                "cannot elect its board two ways, and a page would have to pick"
                % (inst["tag"], ", ".join(both)))
        counties.update(out)
        problems += probs
        nameless |= none_named
        paths += used
        if note:
            notes.append(note)
    return counties, problems, nameless, paths, notes


def main():
    check = "--check" in sys.argv[1:]
    loaded, problems, all_paths, read_by_instance = {}, [], [], {}
    nameless_keys = set()
    for inst in INSTANCES:
        counties, probs, nameless, paths, notes = load_instance(inst)
        loaded[inst["tag"]] = (inst, counties, notes)
        problems += probs
        all_paths += paths
        nameless_keys |= {_nobody_key(inst, c) for c in nameless}
        read_by_instance[inst["tag"]] = {os.path.basename(p) for p in paths}
    problems += check_workflows(read_by_instance)
    reg_problems, candidates = check_registration(all_paths)
    problems += reg_problems
    for key, rec in sorted(NAMES_NOBODY.items()):
        if key not in nameless_keys:
            problems.append(
                "NAMES_NOBODY records %s (%s) and its roster now names someone, "
                "or has left the tree — drop the entry and let the page "
                "generate: %s" % (key, rec["date"], rec["reason"]))
    if problems:
        for p in problems:
            print("build-county-pages: FAIL — %s" % p, file=sys.stderr)
        raise SystemExit(1)
    for key, rec in sorted(NAMES_NOBODY.items()):
        print("  ~ no page for %s: its roster names nobody (recorded %s) — %s"
              % (key, rec["date"], rec["reason"]))
    for rel, entry in sorted(NOT_COUNTY_BOARDS.items()):
        print("  ~ not a county board: %s (%s) — %s"
              % (rel, entry["date"], entry["reason"]))

    shell = shell_for_pages()
    stale, orphans, totals, wrong = [], [], [], []
    for inst in INSTANCES:
        _i, counties, notes = loaded[inst["tag"]]
        pages, people, skipped, rows = {}, 0, 0, []
        for name, rec in sorted(counties.items()):
            at_large = rec["at_large"]
            html = build_page(inst, name, rec, at_large, shell)
            pages[rec["slug"]] = html
            wrong += ["%s: %s" % (inst["tag"], w)
                      for w in verify_page(inst, name, rec, at_large, html)]
            if at_large:
                seats = len(rec["members"])
            else:
                # District members plus whoever the extras name — the same total
                # the index prints, because two adjacent numbers five apart read
                # as one of them being wrong.
                seats = (sum(len(d["members"]) for d in rec["districts"])
                         + sum(len(ms) for _a, _h, ms in rec.get("extras") or []))
                skipped += len(rec["skipped"])
            people += seats
            rows.append((name, rec["slug"], at_large, seats))
        rows.sort()
        totals.append((inst, pages, people, skipped, rows, notes))

    if wrong:
        for w in wrong:
            print("build-county-pages: FAIL — %s" % w, file=sys.stderr)
        raise SystemExit(1)

    for inst, pages, _people, _skipped, _rows, _notes in totals:
        d = out_dir(inst)
        os.makedirs(d, exist_ok=True)
        existing = {os.path.basename(p)[:-len(".html")]
                    for p in glob.glob(os.path.join(d, "*.html"))}
        gone = sorted(existing - set(pages))
        orphans += ["%s/%s.html" % (inst["concept"], o) for o in gone]
        for slug, html in sorted(pages.items()):
            out = os.path.join(d, slug + ".html")
            current = ""
            if os.path.exists(out):
                with open(out, encoding="utf-8") as f:
                    current = f.read()
            if check:
                if current != html:
                    stale.append(os.path.relpath(out, REPO_ROOT))
            elif current != html:
                with open(out, "w", encoding="utf-8") as f:
                    f.write(html)
        if not check:
            for o in gone:
                os.remove(os.path.join(d, o + ".html"))

    index_stale = []
    for inst, _pages, _people, _skipped, rows, _notes in totals:
        if write_index(inst, rows, check) and check:
            index_stale.append("%s's %r region"
                               % (os.path.relpath(index_page(inst), REPO_ROOT),
                                  INDEX_REGION))

    if check and (stale or orphans or index_stale):
        if stale:
            print("build-county-pages: FAIL — %d page(s) stale, starting with %s. "
                  "Run `python3 scripts/build_county_pages.py`."
                  % (len(stale), ", ".join(stale[:4])), file=sys.stderr)
        for o in orphans:
            print("build-county-pages: FAIL — %s has no roster behind it any "
                  "more; delete it" % o, file=sys.stderr)
        for i in index_stale:
            print("build-county-pages: FAIL — %s is stale. Run `python3 "
                  "scripts/build_county_pages.py`." % i, file=sys.stderr)
        raise SystemExit(1)

    for inst, pages, people, skipped, rows, notes in totals:
        at_large = sum(1 for r in rows if r[2])
        print("  %s  %3d page(s) %s, %4d people named and each one verified onto "
              "its page (%d districted, %d at large%s)%s"
              % (inst["tag"], len(pages), "current" if check else "written",
                 people, len(rows) - at_large, at_large,
                 ", %d non-district key(s) skipped" % skipped if skipped else "",
                 "; " + "; ".join(notes) if notes else ""))
    print("build-county-pages: OK — %d page(s) across %d instance(s), %d people "
          "named, %d candidate roster(s) classified%s"
          % (sum(len(t[1]) for t in totals), len(totals),
             sum(t[2] for t in totals), len(candidates) + len(all_paths),
             "; removed %d orphan(s)" % len(orphans) if orphans and not check else ""))


if __name__ == "__main__":
    main()
