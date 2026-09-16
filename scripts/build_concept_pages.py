#!/usr/bin/env python3
"""
Four question pages for four shipped layers nobody could read.

WHY THESE FOUR. The search audit's phase 3 names them: judicial subcircuit,
school district, township and circuit court. Each is a layer every relevant app
already draws, and measured 2026-09-16 none of them had a page, so the data
behind them reached a reader only after JavaScript fetched a file and rendered
a card. Three carry officeholders and one does not, and that difference is the
whole design of this script.

  wi/circuit-court.html       69 circuits, 261 judges, most with a direct line
  il/township.html            29 Cook townships, 220 elected officials
  wi/school-board.html        the two Wisconsin boards elected by district
  il/judicial-subcircuit.html nine counties, nine circuits, NO judge named

THE SUBCIRCUIT PAGE NAMES NOBODY ON PURPOSE. An Illinois judge is elected FROM
a subcircuit and then sits circuit-wide, so there is no such thing as "the judge
for subcircuit 4" and the app's own card has said so since it shipped. The page
is built anyway because the boundary question is real and unanswered anywhere
else on this site: which counties have subcircuits, which circuit each belongs
to, and where each county's lines come from. Its officeholder-table region is
present and EMPTY, which is what an honest absence looks like in this machinery.

EVERY COUNT IS READ ON THE RUN THAT WRITES THE PAGE. No seat count, circuit
count or district count is typed into the prose — the same rule
build_legislator_pages.py states, for the same reason. The subcircuit table goes
further and is parsed out of il/index.html's own dispatch entries, because a
hand-kept county list here would go stale at the speed the Illinois frontier
moves; a parse that finds fewer than two entries, or an entry with no court
label, fails rather than publishing a short table.

WHAT THIS SCRIPT OWNS is the head, the prose, the structure and the two tables
that name no person (the township halls and the subcircuit inventory). It does
NOT own the five regions other generators fill — see scripts/question_page.py —
and splices them back from disk on every run.

    python3 scripts/build_concept_pages.py           # write the pages
    python3 scripts/build_concept_pages.py --check   # drift gate for CI
"""

import argparse
import difflib
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from question_page import (METROS, PageError, check_layer, head, load,  # noqa: E402
                           MARK_RE, preserved_from_disk, shared_head_block,
                           shell, THEMEBOOT_RE)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DISCLAIMER = """    <div class="disclaimer">
      <strong>Not for legal or official use.</strong> Boundary and roster data come from public
      sources that explicitly disclaim legal precision. Confirm district assignments and
      officeholders with the relevant government office before relying on them for anything
      official.
    </div>"""


def fail(msg):
    print("build-concept-pages: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def esc(s):
    return html.escape(str(s))


# ---------------------------------------------------------------- wi circuits

def circuit_court_page(tag, spec, worksheet):
    judges = load("wi/data/app/wi-circuit-judges.json")
    circuits = sorted(judges)
    people = [(k, j) for k in circuits for j in judges[k]["judges"]]
    counties = sorted({c for v in judges.values() for c in v["counties"]})
    shared = sorted(k for k in circuits if len(judges[k]["counties"]) > 1)
    if not shared:
        raise PageError("wi-circuit-judges.json has no multi-county circuit — the "
                        "page's second section describes the three the statute "
                        "pairs and must not claim they exist if they do not")
    names = " and ".join([", ".join(circuit_name(judges, k) for k in shared[:-1]),
                          circuit_name(judges, shared[-1])])

    lede = dict(
        html='<p class="lede"><strong>Wisconsin runs %d circuit courts over its %d '
             'counties, and %d judges sit in them.</strong> A circuit is the trial court '
             'for nearly everything — felonies, small claims, divorce, probate, traffic '
             '— and which one covers an address is a question of which county it is in, '
             'not which city.</p>' % (len(circuits), len(counties), len(people)),
        cta='    <a class="cta" href="./#layers=%s">Find your circuit court →</a>\n'
            '    <p class="cta-note">Opens the map with the circuit court layer on. Search '
            'your address or ZIP, or tap your location.</p>' % spec["layers"])

    sections = """  <section>
    <h2>What the lookup shows</h2>
    <div class="answer-card">
      <p>Select any point and the card names the <strong>circuit</strong> covering it, every
        <strong>judge</strong> sitting in it with their branch number and direct line, and the
        <strong>courthouse</strong> address for each county the circuit covers.</p>
      <p>Everyone is titled Judge and nothing else. An appointee filling a vacancy and an elected
        judge are indistinguishable in every source the state publishes, so this names neither;
        the only role shown is the one the court system itself prints.</p>
    </div>
  </section>

  <section>
    <h2>A circuit is counties, not lines on a map</h2>
    <p>No agency publishes circuit geometry, and this map never draws a boundary no agency
      publishes. Every circuit here is a union of whole counties taken from the Census Bureau's
      own county file, composed under two witnesses that agree exactly: the statute that
      establishes the circuits, and the court system's own circuit listing. %(shared)s cover
      more than one county; the rest are one county each.</p>
  </section>

  <section>
    <h2>Where the names come from</h2>
    <p>The bench is re-read on a schedule from the state court system's own judges table and
      enriched with each judge's branch and direct telephone from its contact directory, landing
      as a reviewed pull request. No e-mail address ships because the court system publishes
      none. A circuit whose roster comes back empty degrades to the circuit and a link to the
      directory — never to an invented name.</p>
%(disclaimer)s
  </section>

""" % dict(shared=esc(names), disclaimer=DISCLAIMER)

    subtitle = "Wisconsin circuit court lookup — free, by address, ZIP, or a tap on the map."
    desc = ("Your Wisconsin circuit court by address or ZIP — the circuit, the judges "
            "who sit in it, and the courthouse for your county.")
    og = ("Find your Wisconsin circuit court by address or ZIP, and the %d judges who sit "
          "in the state's circuits." % len(people))
    # "Which circuit court covers my address?" was the first title and ran the
    # page one character past validate_serp_lengths.py's 60. This one is four
    # words shorter, is what a reader actually types, and is what the page's own
    # table answers.
    return dict(title="Who is my circuit court judge?", subtitle=subtitle,
                desc=desc, og=og, lede=lede, sections=sections, named=len(people))


def circuit_name(judges, key):
    """A circuit's own name, from the counties it covers, never from its slug."""
    return " and ".join(c.replace(" County", "") for c in judges[key]["counties"])


# --------------------------------------------------------------- il townships

TOWNSHIP_ROSTER = "il/data/app/township-officials.json"


def township_people(roster):
    """Every named township official, in the order the page prints them: the
    elected head first, then the other county-wide officers, then the board."""
    out = []
    for geoid in sorted(roster, key=lambda k: roster[k]["name"]):
        rec = roster[geoid]
        slots = ([rec["head"]] if rec.get("head") else []) + \
            list(rec.get("officers") or []) + list(rec.get("board") or [])
        for person in slots:
            if person.get("name"):
                out.append((rec, person))
    return out


def township_page(tag, spec, worksheet):
    roster = load(TOWNSHIP_ROSTER)
    people = township_people(roster)
    counties = sorted({v["county"] for v in roster.values()})
    if len(counties) != 1:
        # The prose below names one county because one county publishes these.
        # A second one is good news and a rewrite, not a silent widening.
        raise PageError("township-officials.json now covers %s — the page's prose "
                        "names a single county and must be rewritten"
                        % ", ".join(counties))
    county = counties[0]
    halls = [v for v in sorted(roster.values(), key=lambda v: v["name"])
             if (v.get("office") or {}).get("address")]

    lede = dict(
        html='<p class="lede"><strong>A township is the layer of Illinois government most '
             'people never look up, and it is the one that assesses your house.</strong> '
             'Outside Chicago, township government runs property assessment, general '
             'assistance and — in most townships — the roads that no city or county '
             'maintains. This names the %d officials the %s County Clerk publishes for its '
             '%d townships.</p>'
             % (len(people), esc(county), len(roster)),
        cta='    <a class="cta" href="./#layers=%s">Find your township →</a>\n'
            '    <p class="cta-note">Opens the map with the township layer on. Search your '
            'address or ZIP, or tap your location.</p>' % spec["layers"])

    rows = []
    for rec in halls:
        office = rec["office"]
        site = rec.get("url")
        rows.append(
            "      <tr>"
            "<td>%s</td>"
            "<td>%s</td>"
            "<td>%s</td>"
            "<td>%s</td></tr>" % (
                esc(rec["name"]),
                esc(office["address"]),
                ('<a href="tel:%s">%s</a>' % (re.sub(r"[^0-9+]", "", office["phone"]),
                                              esc(office["phone"]))
                 if office.get("phone") else ""),
                ('<a href="%s" target="_blank" rel="noopener">Website</a>'
                 % html.escape(site, quote=True)) if site else ""))

    sections = """  <section>
    <h2>What the lookup shows</h2>
    <div class="answer-card">
      <p>Select any point and the card names the <strong>township</strong> containing it and,
        where the county publishes them, the <strong>supervisor, clerk, assessor, highway
        commissioner and trustees</strong> who hold its offices.</p>
      <p>The map draws a township for any point in Illinois, because the boundaries come from the
        Census Bureau's county-subdivision layer for the whole state. The names do not: they are
        published county by county, and today %(county)s County's clerk is the one publishing
        them. A township with no entry shows its name and nobody else's.</p>
    </div>
  </section>

  <section>
    <h2>Township, city and county are three different governments</h2>
    <p>They overlap and none contains the others. A township can hold several municipalities and
      parts of others; Chicago sits in no township at all, which is why the card is blank inside
      the city. Your property assessment comes from the township assessor, your street repair
      from whichever of the three actually owns the road, and your ballot carries all three.</p>
  </section>

  <section>
    <h2>Township halls</h2>
    <p>Where to ask, for each of the %(halls)d townships in the roster. The telephone number and
      the mailbox belong to the <strong>hall</strong>, not to any one officeholder: the county
      publishes one shared line per township, often a staff member's, so this site never prints
      it beside a person's name.</p>
    <div class="flow-table-wrap">
    <table class="flow">
      <thead><tr><th>Township</th><th>Hall</th><th>Telephone</th><th>Own site</th></tr></thead>
      <tbody>
%(rows)s
      </tbody>
    </table>
    </div>
  </section>

  <section>
    <h2>Where the names come from</h2>
    <p>The %(county)s County Clerk's directory of elected officials, re-read on a schedule and
      landing as a reviewed pull request. A township the directory does not name keeps its
      identity card and nobody is filled in.</p>
%(disclaimer)s
  </section>

""" % dict(county=esc(county), halls=len(halls), rows="\n".join(rows),
           disclaimer=DISCLAIMER)

    subtitle = "Illinois township lookup — free, by address, ZIP, or a tap on the map."
    desc = ("Your Illinois township by address or ZIP — the township name, and the "
            "supervisor, clerk, assessor and trustees where the county publishes them.")
    og = ("Find your Illinois township by address or ZIP, and the %d officials %s County "
          "publishes for its townships." % (len(people), county))
    return dict(title="What township am I in?", subtitle=subtitle, desc=desc, og=og,
                lede=lede, sections=sections, named=len(people))


# ------------------------------------------------------- il judicial subcircuits

SUBCIRCUIT_LAYER = 'registerCountyLayer({\n    id: "judicial-subcircuit",'


def subcircuit_entries():
    """The nine dispatch entries, parsed out of il/index.html.

    A hand-kept county list here would go stale at the speed the Illinois
    frontier moves, and there is no data file to read: four of the nine counties
    publish their subcircuits from a live service, so nothing on disk knows they
    exist. The dispatch table does, and it is the same table the app itself
    dispatches on.
    """
    with open(os.path.join(REPO_ROOT, "il", "index.html"), encoding="utf-8") as f:
        text = f.read()
    if SUBCIRCUIT_LAYER not in text:
        raise PageError("il/index.html no longer registers judicial-subcircuit in "
                        "the shape this parser reads")
    start = text.index(SUBCIRCUIT_LAYER)
    end = text.index("\n  });\n", start)
    block = text[start:end]

    out = []
    chunks = re.split(r'\n\s+(?:polygonCountyEntry\(\{|\{)\n', block)
    for chunk in chunks[1:]:
        key = re.search(r'key: "([a-z]+)"', chunk)
        court = re.search(r'\{ label: "Court", value: "([^"]+)" \}', chunk)
        loader = re.search(r'(?:loader|loadGeometry): (\w+)', chunk)
        if not key:
            continue
        if not court or not loader:
            raise PageError('the judicial-subcircuit entry for %r carries no court '
                            'label or no loader — this page states both'
                            % (key.group(1) if key else "?"))
        out.append(dict(key=key.group(1), court=court.group(1),
                        count=subcircuit_count(text, loader.group(1))))
    if len(out) < 2:
        raise PageError("parsed %d judicial-subcircuit entries out of il/index.html "
                        "— the dispatch block has changed shape" % len(out))
    return out


def subcircuit_count(text, loader):
    """How many subcircuits that county has, counted from the shipped file.

    Returns None where the county's boundaries are fetched live: the file is the
    only thing here that can be counted, and a number nobody measured is exactly
    what this project does not print.
    """
    found = re.search(r"var %s = makeCached\(function \(\) \{(.*?)\n  \}\);" % loader,
                      text, re.S)
    if not found:
        raise PageError("cannot find the definition of %s in il/index.html" % loader)
    path = re.search(r'"(data/app/[\w.-]+\.json)"', found.group(1))
    if not path:
        return None
    geo = load(os.path.join("il", path.group(1)))
    districts = set()
    for feature in geo["features"]:
        props = {k.lower(): v for k, v in (feature.get("properties") or {}).items()}
        value = props.get("district")
        districts.add(str(value) if value is not None else "")
    return len(districts)


COUNTY_TITLE = {"dupage": "DuPage", "mchenry": "McHenry", "lasalle": "LaSalle"}


def county_title(key):
    return COUNTY_TITLE.get(key, key.title())


def subcircuit_page(tag, spec, worksheet):
    entries = subcircuit_entries()
    counted = [e for e in entries if e["count"] is not None]
    rows = []
    for entry in entries:
        rows.append(
            "      <tr><td>%s County</td><td>%s</td><td>%s</td></tr>" % (
                esc(county_title(entry["key"])), esc(entry["court"]),
                (str(entry["count"]) if entry["count"] is not None
                 else "read from the county live")))

    lede = dict(
        html='<p class="lede"><strong>In %d Illinois counties, circuit judges are elected '
             'from a subcircuit rather than from the whole circuit.</strong> The subcircuit '
             'decides who may vote for a seat and who may run for it. It is not a court, it '
             'has no courthouse of its own, and most people who have one have never seen its '
             'boundary.</p>' % len(entries),
        cta='    <a class="cta" href="./#layers=%s">Find your judicial subcircuit →</a>\n'
            '    <p class="cta-note">Opens the map with the subcircuit layer on. Search your '
            'address or ZIP, or tap your location.</p>' % spec["layers"])

    sections = """  <section>
    <h2>What the lookup shows</h2>
    <div class="answer-card">
      <p>Select any point in one of these counties and the card names the
        <strong>subcircuit</strong> containing it and the <strong>circuit court</strong> it
        elects judges to, with a link to that court. In Cook County it also names the
        <strong>municipal district</strong> and the courthouse that serves the point, which is
        a different division of the same court and the one that decides where a case is heard.</p>
      <p>Outside these counties the layer hides rather than showing an empty card, which is
        what this site does everywhere a layer's data does not apply.</p>
    </div>
  </section>

  <section>
    <h2>No judge is named here, and that is deliberate</h2>
    <p>An Illinois judge is <em>elected from</em> a subcircuit and then sits across the whole
      circuit. There is no judge assigned to a subcircuit, so a roster keyed by subcircuit would
      be a claim nobody publishes and nobody could check. Each card links the court itself
      instead. Your ballot is the place a subcircuit shows up: in a year with a vacancy, the
      judicial races you vote on are the ones for your subcircuit and nobody else's.</p>
  </section>

  <section>
    <h2>Where subcircuits exist</h2>
    <p>Read from this app's own dispatch table on the run that built this page, so a county
      joining or leaving changes the table below by regenerating it. Counties not listed elect
      their circuit judges circuit-wide. Kendall County is the case worth naming: its 23rd
      Circuit received no subcircuits when the legislature drew the current set, so its absence
      here is the statute rather than a gap in this site.</p>
    <div class="flow-table-wrap">
    <table class="flow">
      <thead><tr><th>County</th><th>Circuit</th><th>Subcircuits</th></tr></thead>
      <tbody>
%(rows)s
      </tbody>
    </table>
    </div>
    <p class="cta-note">%(counted)d of the %(total)d counties publish their subcircuits as a file
      this site ships, so those are counted on the run that built this page. The rest are fetched
      from the county's own service when you select a point, and nothing here can count them, so
      no number is printed rather than a number nobody measured.</p>
  </section>

  <section>
    <h2>Where the boundaries come from</h2>
    <p>Each county's own GIS where it publishes one, and the enacted redistricting shapefile
      where it does not — a county whose service is permission-locked, or which publishes no
      subcircuit layer at all, still has the same boundary, and the act that drew it is public.
      <a href="sources.html">Which county uses which</a>.</p>
%(disclaimer)s
  </section>

""" % dict(rows="\n".join(rows), counted=len(counted), total=len(entries),
           disclaimer=DISCLAIMER)

    subtitle = "Illinois judicial subcircuit lookup — free, by address, ZIP, or a tap on the map."
    desc = ("Your Illinois judicial subcircuit by address or ZIP — the subcircuit you "
            "elect circuit judges from, and the court it belongs to.")
    og = ("Find your Illinois judicial subcircuit by address or ZIP, across the %d counties "
          "that elect circuit judges from one." % len(entries))
    return dict(title="What judicial subcircuit am I in?", subtitle=subtitle, desc=desc,
                og=og, lede=lede, sections=sections, named=0)


# ------------------------------------------------------------ wi school boards

def school_board_page(tag, spec, worksheet):
    boards = [load("wi/data/app/%s-school-board-members.json" % slug)
              for slug in ("mps", "rusd")]
    seats = sum(len(b["members"]) for b in boards)
    named = sum(1 for b in boards for v in b["members"].values() if v.get("name"))
    districts = load("wi/data/app/school-districts-unified.json")["features"]

    lede = dict(
        html='<p class="lede"><strong>Almost every Wisconsin school board is elected at '
             'large, and two are not.</strong> Milwaukee and Racine elect most of their '
             'board members from districts drawn inside the school district, so an address '
             'there has a board member of its own — %d seats between them, %d of them '
             'filled. Everywhere else in the state this names the school district covering '
             'your address, one of %d, and the board is elected by all of its voters '
             'together.</p>' % (seats, named, len(districts)),
        cta='    <a class="cta" href="./#layers=%s">Find your school district →</a>\n'
            '    <p class="cta-note">Opens the map with the school district and elected board '
            'layers on. Search your address or ZIP, or tap your location.</p>' % spec["layers"])

    sections = """  <section>
    <h2>What the lookup shows</h2>
    <div class="answer-card">
      <p>Select any point and the card names the <strong>school district</strong> covering it.
        In Milwaukee and Racine a second card names the <strong>board district</strong> and the
        <strong>member</strong> who holds that seat, with the term it runs to.</p>
      <p>Elementary and union high school districts are drawn separately from unified ones and
        cover different ground, so an address outside a unified district gets the pair that
        applies to it instead.</p>
    </div>
  </section>

  <section>
    <h2>A school district and a board district are different shapes</h2>
    <p>A school district is where the schools are. A board district is a slice of one, drawn to
      hold equal population so that each member represents about the same number of people.
      Only a board elected by district has the second shape, which is why this map draws board
      districts in two places and school districts everywhere.</p>
  </section>

  <section>
    <h2>Where the names come from</h2>
    <p>Each board's own published directory, re-read on a schedule and landing as a reviewed
      pull request. A seat the district reports as vacant is shown as vacant rather than left
      out, because leaving it out would make the board look smaller than it is.</p>
%(disclaimer)s
  </section>

""" % dict(disclaimer=DISCLAIMER)

    subtitle = "Wisconsin school district lookup — free, by address, ZIP, or a tap on the map."
    desc = ("Your Wisconsin school district by address or ZIP — and in Milwaukee and "
            "Racine, the board district and the member who holds it.")
    og = ("Find your Wisconsin school district by address or ZIP, across %d districts, and "
          "the elected board members in Milwaukee and Racine." % len(districts))
    return dict(title="Who is on my school board?", subtitle=subtitle, desc=desc, og=og,
                lede=lede, sections=sections, named=named)


# ------------------------------------------------------------------- the table

PAGES = [
    dict(tag="wi", file="circuit-court.html", worksheet="wi/metro-worksheet.json",
         layers="wi-circuit-court", make=circuit_court_page,
         counts=["wi/data/app/wi-circuit-judges.json"],
         sibling=dict(page="county-board.html", label="Who is my county supervisor?",
                      note="The other county-wide body on your ballot.")),
    dict(tag="wi", file="school-board.html", worksheet="wi/metro-worksheet.json",
         layers="school-district-unified,mps-school-board", make=school_board_page,
         counts=["wi/data/app/mps-school-board-members.json",
                 "wi/data/app/rusd-school-board-members.json",
                 "wi/data/app/school-districts-unified.json"],
         sibling=dict(page="circuit-court.html",
                      label="Who is my circuit court judge?",
                      note="The other lookup that answers by county rather than by city.")),
    dict(tag="il", file="township.html", worksheet="metro-worksheet.json",
         layers="township", make=township_page,
         counts=[TOWNSHIP_ROSTER],
         sibling=dict(page="county-board.html", label="Who is my county board member?",
                      note="The government a township sits inside.")),
    dict(tag="il", file="judicial-subcircuit.html", worksheet="metro-worksheet.json",
         layers="judicial-subcircuit", make=subcircuit_page,
         # No roster: this page counts dispatch entries out of il/index.html and
         # subcircuits out of five shipped boundary files, and no scheduled job
         # rewrites any of them. An app edit that moves them is a pull request a
         # person wrote, where --check is the right place to catch it.
         counts=[],
         sibling=dict(page="county-board.html", label="Who is my county board member?",
                      note="The other district drawn inside a single county.")),
]


WORKFLOWS = os.path.join(REPO_ROOT, ".github", "workflows")


def check_workflows():
    """A workflow that rewrites a file this page COUNTS must regenerate it.

    The same rule build_county_pages.py and build_officeholder_tables.py already
    enforce, and for the same reason: every count on these pages is read on the
    run that writes them, so a weekly job that refreshes a roster and leaves the
    page alone makes --check go red on the bot's own pull request, where nobody
    wrote the change that broke it.
    """
    for spec in PAGES:
        page = "%s/%s" % (spec["tag"], spec["file"])
        for roster in spec["counts"]:
            for name in sorted(os.listdir(WORKFLOWS)):
                if not name.endswith((".yml", ".yaml")):
                    continue
                with open(os.path.join(WORKFLOWS, name), encoding="utf-8") as f:
                    text = f.read()
                if ("git add" not in text) or (roster not in text):
                    continue
                if "build_concept_pages.py" not in text:
                    raise PageError(
                        ".github/workflows/%s rewrites %s and never regenerates "
                        "%s — add a step running python3 "
                        "scripts/build_concept_pages.py and `git add %s`"
                        % (name, roster, page, page))
                if page not in text:
                    raise PageError(
                        ".github/workflows/%s regenerates the page and never "
                        "commits it — add `git add %s`" % (name, page))
                print("build-concept-pages: %s regenerates %s" % (name, page))


def related_rows(spec, landing, metros):
    """The instance's own map, one sibling page in the same instance, and the
    next instance's map. The cross-instance row is DERIVED from metros.json
    order, so a new state joins these rows the day it is registered."""
    sib = spec["sibling"]
    # A sibling this script itself writes counts as present: on a fresh
    # checkout --check runs before anything is written, so testing the disk
    # alone would fail the one page whose sibling is the page after it.
    ours = {(p["tag"], p["file"]) for p in PAGES}
    path = os.path.join(REPO_ROOT, spec["tag"], sib["page"])
    if (spec["tag"], sib["page"]) not in ours and not os.path.isfile(path):
        raise PageError("%s/%s links %s, which does not exist"
                        % (spec["tag"], spec["file"], sib["page"]))
    order = [m["tag"] for m in metros]
    nxt = order[(order.index(spec["tag"]) + 1) % len(order)]
    nxt_name = next(m["landing_name"] for m in metros if m["tag"] == nxt)
    nxt_scope = next(m["scope"] for m in metros if m["tag"] == nxt)
    return "\n".join([
        '      <li><a href="./">What district am I in?</a><span>Every district that '
        'covers one point in %s, and who represents you there.</span></li>' % esc(landing),
        '      <li><a href="%s">%s</a><span>%s</span></li>'
        % (sib["page"], esc(sib["label"]), esc(sib["note"])),
        '      <li><a href="../%s/">%s</a><span>The same lookup, %s.</span></li>'
        % (nxt, esc(nxt_name), esc(nxt_scope)),
    ])


def build(spec, metros):
    worksheet = load(spec["worksheet"])
    brand = worksheet["brand"]
    app_name = brand["app_name"]
    tag = spec["tag"]
    rel = os.path.join(tag, spec["file"])
    for layer in spec["layers"].split(","):
        check_layer(worksheet, layer, rel)
    landing = next(m["landing_name"] for m in metros if m["tag"] == tag)

    page = spec["make"](tag, spec, worksheet)
    path = os.path.join(REPO_ROOT, tag, spec["file"])
    text = head(tag, brand, app_name, spec["file"], page["title"],
                page["desc"], page["og"])
    text += shell(app_name, page["title"], page["subtitle"], page["lede"],
                  page["sections"], related_rows(spec, landing, metros),
                  preserved_from_disk(path),
                  shared_head_block(tag, THEMEBOOT_RE, "theme boot script"),
                  shared_head_block(tag, MARK_RE, "districtry mark"))
    return rel, path, text, page["named"]


def run(args):
    check_workflows()
    metros = load(METROS)["metros"]
    drift, written, named = [], 0, 0
    for spec in PAGES:
        rel, path, text, count = build(spec, metros)
        named += count
        try:
            with open(path, encoding="utf-8") as f:
                current = f.read()
        except OSError:
            current = None
        if current == text:
            continue
        if args.check:
            drift.append((rel, current, text))
            continue
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        written += 1
        print("build-concept-pages: %s — written" % rel)

    if args.check:
        for rel, current, text in drift:
            if current is None:
                print("build-concept-pages: %s does not exist" % rel, file=sys.stderr)
                continue
            print("build-concept-pages: DRIFT in %s" % rel, file=sys.stderr)
            for line in difflib.unified_diff(current.splitlines(), text.splitlines(),
                                             fromfile="committed", tofile="regenerated",
                                             lineterm="", n=1):
                print("  " + line, file=sys.stderr)
        if drift:
            fail("%d page(s) out of date — run "
                 "python3 scripts/build_concept_pages.py" % len(drift))
        print("build-concept-pages: OK — %d page(s), %d officeholder(s) named"
              % (len(PAGES), named))
    else:
        print("build-concept-pages: OK — %d page(s) written, %d current, "
              "%d officeholder(s) named" % (written, len(PAGES) - written, named))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="drift gate: fail rather than write")
    args = ap.parse_args()
    try:
        return run(args)
    except PageError as exc:
        fail(str(exc))


if __name__ == "__main__":
    main()
