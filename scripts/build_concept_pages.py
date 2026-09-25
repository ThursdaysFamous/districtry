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
# The three Illinois special-district pages name the districts the officeholder
# table names, and the table's own module already answers the hard half of that
# question — which entries in a county-keyed roster are one district filed twice.
# Importing it keeps ONE reader of that question; grouping the file again here
# is how the page and the table come to disagree about how many districts exist.
from build_officeholder_tables import afr_people, afr_units  # noqa: E402

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


def borough_page(tag, spec, worksheet):
    """New York City's boroughs, and the three offices each one fills.

    THE COUNTS ARE READ, including how many of the fifteen offices the roster
    names, because an office between officeholders is a real state and a page
    that says "fifteen" while naming fourteen is wrong about a vacancy.
    """
    boroughs = load(spec["counts"][0])
    offices = sum(len(rec) for rec in boroughs.values())
    named = sum(1 for rec in boroughs.values() for v in rec.values()
                if isinstance(v, dict) and v.get("name"))

    lede = dict(
        html='<p class="lede"><strong>A borough is also a county, and it fills three '
             'offices of its own.</strong> New York City\'s %d boroughs each elect a '
             'borough president and a district attorney, and each has a county clerk; '
             'this names <strong>%d</strong> of the %d.</p>'
             % (len(boroughs), named, offices),
        cta='    <a class="cta" href="./#layers=%s">Find your borough →</a>\n'
            '    <p class="cta-note">Opens the map with the borough layer on. Search your '
            'address or ZIP, or tap your location.</p>' % spec["layers"])

    sections = """  <section>
    <h2>What the lookup shows</h2>
    <div class="answer-card">
      <p>Select any point in the city and the card names the <strong>borough</strong>
        covering it. The table below names that borough's president, its district attorney
        and its county clerk, with a link to each office.</p>
      <p>These are borough-wide offices, so the answer is the same anywhere inside the
        borough — there are no districts within them to be in.</p>
    </div>
  </section>

  <section>
    <h2>Two of the three are on your ballot</h2>
    <p>The borough president and the district attorney are elected by the borough's own
      voters. The county clerk in the five boroughs is appointed by the court rather than
      elected, and is here because it is the office to go to for county records — the
      table names each office so the difference is visible rather than implied.</p>
  </section>

  <section>
    <h2>Where the names come from</h2>
    <p>Each office's own published page, checked by hand and landing as a reviewed pull
      request. An office the roster does not name is shown as unnamed rather than left
      out.</p>
%(disclaimer)s
  </section>

""" % dict(disclaimer=DISCLAIMER)

    subtitle = "New York City borough lookup — free, by address, ZIP, or a tap on the map."
    desc = ("Which New York City borough you are in, and who holds its three offices — "
            "borough president, district attorney and county clerk.")
    og = ("Find your New York City borough and the %d people who hold its borough-level "
          "offices." % named)
    return dict(title="Who is my borough president?", subtitle=subtitle, desc=desc, og=og,
                lede=lede, sections=sections, named=named)


def supreme_court_page(tag, spec, worksheet):
    """Illinois's two highest elected courts, drawn on one set of districts.

    ONE PAGE FOR BOTH, because they share the geometry: an Illinois judicial
    district elects its Supreme Court justice AND its Appellate Court justices,
    so a reader who has found their district has found both answers. Splitting
    them would be two pages over one map.

    EVERY COUNT IS READ, including how many justices each court seats, because
    Cook County elects three of the seven Supreme Court justices and one
    retirement moves the appellate figure.
    """
    courts = load(spec["counts"][0])
    supreme = sum(len(d["supreme"]) for d in courts.values())
    appellate = sum(len(d["appellate"]["justices"]) for d in courts.values())
    cook = len(courts["1"]["supreme"])

    lede = dict(
        html='<p class="lede"><strong>Illinois elects its judges, and the district you '
             'live in decides which ones you vote on.</strong> The state is divided into '
             '%d judicial districts; each elects justices to the Supreme Court and to the '
             'Appellate Court, and this names all <strong>%d</strong> of them — %d on the '
             'Supreme Court, %d on the Appellate Court.</p>'
             % (len(courts), supreme + appellate, supreme, appellate),
        cta='    <a class="cta" href="./#layers=%s">Find your judicial district →</a>\n'
            '    <p class="cta-note">Opens the map with the judicial district layer on. '
            'Search your address or ZIP, or tap your location.</p>' % spec["layers"])

    sections = """  <section>
    <h2>What the lookup shows</h2>
    <div class="answer-card">
      <p>Select any point in Illinois and the card names the <strong>judicial
        district</strong> covering it. The tables below name the justices that district
        elects to each court.</p>
      <p>The First District is Cook County alone and elects %(cook)d of the Supreme
        Court's %(supreme)d justices; the other four districts cover the rest of the state
        and elect one each.</p>
    </div>
  </section>

  <section>
    <h2>A judicial district is not a subcircuit</h2>
    <p>A judicial district elects the justices of the two courts above the trial court. A
      <a href="judicial-subcircuit.html">judicial subcircuit</a> is a smaller shape inside
      one county that elects a CIRCUIT judge — who then sits across the whole circuit, which
      is why no judge belongs to a subcircuit once elected. The two answer different
      questions and this map draws both.</p>
  </section>

  <section>
    <h2>Where the names come from</h2>
    <p>The Illinois courts' own published rosters, re-read on a schedule and landing as a
      reviewed pull request. The Supreme Court publishes which of its justices is Chief
      Justice, and that is carried; the Appellate Court publishes no such role and none is
      supplied.</p>
%(disclaimer)s
  </section>

""" % dict(disclaimer=DISCLAIMER, cook=cook, supreme=supreme)

    subtitle = "Illinois judicial district lookup — free, by address, ZIP, or a tap on the map."
    desc = ("Which Illinois judicial district you live in, and the Supreme Court and "
            "Appellate Court justices it elects.")
    og = ("Find your Illinois judicial district and the %d justices it elects to the "
          "Supreme and Appellate Courts." % (supreme + appellate))
    return dict(title="Who is my Supreme Court justice?", subtitle=subtitle,
                desc=desc, og=og, lede=lede, sections=sections,
                named=supreme + appellate)


def county_auditor_page(tag, spec, worksheet):
    """Who runs elections in an Iowa county, and keeps its records.

    ONE OFFICER PER COUNTY, so every number here is read off the roster on the
    run that writes the page: how many counties it names, and how many of them
    publish a party. "Iowa has 99 counties" is stated because it cannot move;
    everything else is counted.

    THE OFFICE IS DESCRIBED BY WHAT IT DOES AND NOT BY ITS TERM. Iowa Code
    fixes the term and this page cites no statute, so it says what the auditor
    is — the county's commissioner of elections and the keeper of its records —
    and leaves the law to the law.
    """
    auditors = load(spec["counts"][0])
    named = sum(1 for rec in auditors.values() if rec.get("name"))
    with_party = sum(1 for rec in auditors.values() if rec.get("party"))

    lede = dict(
        html='<p class="lede"><strong>The county auditor is the person who runs your '
             'election.</strong> Every Iowa county elects one, countywide, and the same '
             'officer keeps the county\'s records and pays its bills. This names '
             '<strong>%s</strong>, with the office and a telephone number for each.</p>'
             % ("all 99" if named == 99 else "%d of the 99" % named),
        cta='    <a class="cta" href="./#layers=%s">Find your county →</a>\n'
            '    <p class="cta-note">Opens the map with the county layer on. Search your '
            'address or ZIP, or tap your location.</p>' % spec["layers"])

    sections = """  <section>
    <h2>What the lookup shows</h2>
    <div class="answer-card">
      <p>Select any point in Iowa and the card names the <strong>county</strong> covering
        it. The table below names that county's auditor, the office they work from and a
        number to call.</p>
      <p>An auditor answers for the whole county, so the answer is the same anywhere
        inside it — there are no auditor districts to be in.</p>
    </div>
  </section>

  <section>
    <h2>Why this is the office to call about an election</h2>
    <p>In Iowa the county auditor is the commissioner of elections: the office that
      registers voters, sets the polling places, prints the ballot and certifies the
      result. A question about where you vote, whether you are registered, or what a
      result was is a question for this office rather than for the county board.</p>
  </section>

  <section>
    <h2>Where the names come from</h2>
    <p>Each county's own published directory, re-read on a schedule and landing as a
      reviewed pull request. %(party_note)s</p>
%(disclaimer)s
  </section>

""" % dict(disclaimer=DISCLAIMER,
           party_note=(
               "Every one of them names a party."
               if with_party == named else
               "%d of the %d name a party; the rest publish none, and this page "
               "prints none for them rather than supplying one."
               % (with_party, named)))

    subtitle = "Iowa county auditor lookup — free, by address, ZIP, or a tap on the map."
    desc = ("Who is your Iowa county auditor — the officer who runs your election — "
            "by address or ZIP.")
    og = ("Find your Iowa county auditor, the county's own commissioner of elections, "
          "across %d counties." % named)
    return dict(title="Who is my county auditor?", subtitle=subtitle, desc=desc, og=og,
                lede=lede, sections=sections, named=named)


def city_council_page(tag, spec, worksheet):
    """Who sits on a city council, in the states that draw city wards.

    ONE FUNCTION, TWO INSTANCES, because it is one concept: a city elects some
    members from wards and some at large, and the map already draws the wards.
    Everything the prose states is COUNTED on the run that writes the page —
    how many cities have ward geometry, how many of those have a roster, and
    how many people it names — because "Michigan draws six cities' wards" is
    exactly the sentence that survives a seventh city unread.

    THE CITIES DRAWN WITHOUT A ROSTER ARE NAMED RATHER THAN OMITTED. Michigan
    draws Flint, Warren and Rochester Hills and names nobody in them; a page
    that listed three cities and said nothing about the other three would read
    as though the map covered three.
    """
    wards = {name: len(load(path)["features"])
             for name, path in spec["wards"]}
    # THE TWO COUNTS ARE KEPT APART BECAUSE THEY DESCRIBE DIFFERENT PLACES.
    # Iowa's page names 22 people in the three cities whose wards this map
    # draws and 24 more in four cities it does not draw at all, and one total
    # of 46 beside "draws the wards of 3 cities" reads as though all 46 sat in
    # those three. The first draft printed exactly that.
    in_wards, at_large_cities, at_large_named = 0, 0, 0
    for _label, path, adapter in spec["rosters"]:
        data = load(path)
        if adapter == "city_officials":
            at_large_cities += len(data)
            at_large_named += sum(1 for rec in data.values()
                                  for m in rec.get("members") or [] if m.get("name"))
            continue
        in_wards += sum(1 for m in data.get("citywide") or [] if m.get("name"))
        inner = data.get("wards") or data.get("districts") or {}
        for value in inner.values():
            for m in (value if isinstance(value, list) else [value]):
                if m.get("name"):
                    in_wards += 1
    named = in_wards + at_large_named
    rostered = {label for label, _p, a in spec["rosters"] if a != "city_officials"}
    unrostered = sorted(c for c in wards if c not in rostered)
    place = spec["place"]

    missing = ("" if not unrostered else
               " The map also draws %s, where no roster this project can read "
               "names the members, so those wards answer with the ward number "
               "and nothing else." % _join(unrostered))
    elsewhere = ("" if not at_large_named else
                 " %d more sit on the councils of %d smaller %s cities that "
                 "elect at large and have no wards to draw; their own county "
                 "publishes the names."
                 % (at_large_named, at_large_cities, esc(spec["place"])))
    lede = dict(
        html='<p class="lede"><strong>A city council seat is the one on your ballot '
             'closest to your street.</strong> %s draws the wards of %d %s, and this '
             'names the <strong>%d people</strong> who hold their seats — the members '
             'elected by one ward, and the mayor and at-large members elected by the '
             'whole city.%s%s</p>'
             % (esc(place), len(wards), "city" if len(wards) == 1 else "cities",
                in_wards, missing, elsewhere),
        cta='    <a class="cta" href="./#layers=%s">Find your ward →</a>\n'
            '    <p class="cta-note">Opens the map with the city ward layer on. Search '
            'your address or ZIP, or tap your location.</p>' % spec["layers"])

    sections = """  <section>
    <h2>What the lookup shows</h2>
    <div class="answer-card">
      <p>Select any point inside one of these cities and the card names the
        <strong>ward</strong> covering it. The table below names the member who holds
        that ward's seat, and the members elected by the city as a whole.</p>
      <p>Outside those cities the map still answers with the county, the school district
        and everything else drawn over that point; a city with no wards drawn here simply
        has no ward card.</p>
    </div>
  </section>

  <section>
    <h2>A ward seat and an at-large seat are not the same job</h2>
    <p>A ward member is elected by the voters of one part of the city and is the person to
      write to about that part of it. An at-large member and the mayor are elected by
      everyone, so they answer for the whole city and appear against every address in it.
      Both are on this page, labelled as the city itself labels them.</p>
  </section>

  <section>
    <h2>Where the names come from</h2>
    <p>Each city's own published roster, re-read on a schedule and landing as a reviewed
      pull request. A seat the city reports open is shown as vacant rather than left out,
      because leaving it out would make the council look smaller than the city elects.</p>
%(disclaimer)s
  </section>

""" % dict(disclaimer=DISCLAIMER)

    subtitle = "%s city council lookup — free, by address, ZIP, or a tap on the map." % place
    desc = ("Who represents you on your %s city council — your ward and the member who "
            "holds it, by address or ZIP." % place)
    og = ("Find your city ward in %s and the council member who holds it, across %d "
          "cities." % (place, len(wards)))
    return dict(title="Who is on my city council?", subtitle=subtitle, desc=desc, og=og,
                lede=lede, sections=sections, named=named)


def _join(names):
    if len(names) == 1:
        return names[0]
    return "%s and %s" % (", ".join(names[:-1]), names[-1])


# ----------------------------------- il fire, park and library districts

SPECIAL_ROSTER = "il/data/app/il-special-district-officials.json"
LIBRARY_ROSTER = "il/data/app/il-library-district-officials.json"
LIBRARY_SITE_ROSTER = "il/data/app/il-library-trustees.json"


def dispatch_counties(layer):
    """How many counties il/index.html dispatches a concept layer in.

    Parsed out of the app's own dispatch table for the reason
    subcircuit_entries() already states: a hand-kept county list here would go
    stale at the speed the Illinois frontier moves. Seventy-two of the library
    layer's entries are built by a factory, so the count is taken from the
    `key:` literals every entry still spells out — which is exactly why
    statewideLibraryEntry keeps them.
    """
    with open(os.path.join(REPO_ROOT, "il", "index.html"), encoding="utf-8") as f:
        text = f.read()
    mark = '    id: "%s",\n' % layer
    if mark not in text:
        raise PageError("il/index.html no longer registers %s in the shape this "
                        "parser reads" % layer)
    start = text.index(mark)
    end = re.compile(r"\n  \}\);\n").search(text, start)
    if not end:
        raise PageError("cannot find the end of the %s registration" % layer)
    keys = set(re.findall(r'key: "([a-z-]+)"', text[start:end.start()]))
    if len(keys) < 2:
        raise PageError("parsed %d counties out of the %s dispatch table — it "
                        "has changed shape" % (len(keys), layer))
    return len(keys)


def office_table(units, noun, plural):
    """One row per district that publishes an office, from the same filings.

    THE ADDRESS AND THE TELEPHONE BELONG TO THE DISTRICT, NOT TO A PERSON, so
    they sit here rather than beside a name in the table above — the rule the
    township-hall table already follows, and for the same reason: a filing
    publishes one office per district and one telephone, often a named
    officer's own line, and printing it next to one trustee would make it
    theirs.

    NO E-MAIL COLUMN. About a third of these filings carry one and it is
    almost always a named officer's work address rather than the district's, so
    it stays on the map's card where the question is who to contact about this
    district, and off a page that would publish several hundred of them in one
    scrapeable block.
    """
    rows = []
    for name, rec in units:
        office = rec.get("office") or {}
        where = ", ".join(x for x in (office.get("address"), office.get("city")) if x)
        phone = office.get("phone")
        if not where and not phone:
            continue
        rows.append(
            "      <tr><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (esc(name), esc(where),
               ('<a href="tel:%s">%s</a>'
                % (re.sub(r"[^0-9+]", "", phone), esc(phone))) if phone else ""))
    if not rows:
        raise PageError("no %s publishes an office in its filing — the page's "
                        "office table would be empty" % noun)
    return """  <section>
    <h2>Where to reach each %(noun)s</h2>
    <p>Where %(n)d of these %(plural)s say to reach them, in their own filings. The address and
      the telephone belong to the <strong>%(noun)s</strong> rather than to any one person on
      it: a filing publishes one of each, often a named officer's own line, so this
      site never prints either beside a name.</p>
    <div class="flow-table-wrap">
    <table class="flow">
      <thead><tr><th>%(head)s</th><th>Office</th><th>Telephone</th></tr></thead>
      <tbody>
%(rows)s
      </tbody>
    </table>
    </div>
  </section>

""" % dict(n=len(rows), rows="\n".join(rows), noun=esc(noun), plural=esc(plural),
           head=esc(noun[0].upper() + noun[1:]))


def afr_provenance(noun, name_note):
    """The section every filing-sourced page ends with.

    THE FORM'S FOUR-NAME LIMIT IS THE LOAD-BEARING SENTENCE. An Annual Financial
    Report has room for four officers, so a board of seven can only ever file
    some of them, and a heading over two names would otherwise read as the whole
    board. The app's own card says the same thing for the same reason.

    The last paragraph differs by page because the join does: a fire or park
    district's row is named from the Comptroller's unit table while the map's
    card prints whatever the county's boundary layer calls it, and a library's
    row and card are the same name.
    """
    return """  <section>
    <h2>Where the names come from</h2>
    <p>Every name here is from the %(noun)s's own <strong>Annual Financial Report</strong>,
      filed with the Illinois Comptroller, re-read on a schedule and landing as a reviewed
      pull request. Each filing names the fiscal year it covers, and the form has room for
      four names — so a board of seven can only ever file some of them, and a short list here
      is the form's limit rather than the whole board.</p>
    <p>A %(noun)s that crosses a county line files <strong>once</strong>, under the county it
      is based in, which is why one you meet in one county can be named for another.
      %(name_note)s</p>
%(disclaimer)s
  </section>

""" % dict(noun=esc(noun), name_note=name_note, disclaimer=DISCLAIMER)


DISTRICT_NAME_NOTE = (
    "The name on each row is the one the district files under; the map's card uses whatever "
    "label the county's own boundary layer prints, which is sometimes just a village name or "
    "a number.")

LIBRARY_NAME_NOTE = (
    "The name on each row is the library's own, and it is the name the map's card prints too "
    "— the boundary layer and the filing agree on it, which is why this page is keyed by "
    "library rather than by county.")


def fire_district_page(tag, spec, worksheet):
    units = afr_units(load(SPECIAL_ROSTER), "fire")
    people = sum(len(afr_people(rec)) for _n, rec in units)
    counties = dispatch_counties("fire-district")

    lede = dict(
        html='<p class="lede"><strong>A fire protection district is a government of its '
             'own — its own board, its own tax levy, and no city or county above '
             'it.</strong> Where you are not inside a municipality that runs its own fire '
             'department, a district is what answers when you call 911. This names the %d '
             'trustees and officers of the %d Illinois districts that file an annual report '
             'with the state.</p>' % (people, len(units)),
        cta='    <a class="cta" href="./#layers=%s">Find your fire district →</a>\n'
            '    <p class="cta-note">Opens the map with the fire protection district layer '
            'on. Search your address or ZIP, or tap your location.</p>' % spec["layers"])

    sections = """  <section>
    <h2>What the lookup shows</h2>
    <div class="answer-card">
      <p>Select any point and the card names the <strong>fire protection district</strong>
        covering it, the people its latest filing names, and the district's office and
        telephone.</p>
      <p>The map draws these districts in %(counties)d Illinois counties. This page names the
        %(units)d districts among them that file an annual report the state publishes. A
        district the filings do not reach still draws on the map, and its card may still name
        people from its own county's data — this page is the filings, not everything the map
        knows.</p>
    </div>
  </section>

  <section>
    <h2>You may not elect these trustees</h2>
    <p>A fire protection district's trustees are normally <strong>appointed by the county
      board</strong>, and elected only where the district's own voters chose that at a
      referendum. Nothing in the filings says which applies to a given district, so this page
      does not say it either — and it is the one board on this site where "who represents you"
      may have no ballot behind it. The county board that does the appointing
      <a href="county-board.html">has its own lookup</a>.</p>
    <p>The <strong>Role</strong> column is what tells the two kinds of name apart. A president,
      treasurer, secretary or trustee sits on the board; a chief, administrator, accountant or
      finance officer is appointed staff the board employs.</p>
  </section>

"""  % dict(counties=counties, units=len(units))
    sections += office_table(units, "district", "fire protection districts")
    sections += afr_provenance("district", DISTRICT_NAME_NOTE)

    return dict(
        title="Who runs my fire protection district?",
        subtitle="Illinois fire protection district lookup — free, by address, ZIP, or a "
                 "tap on the map.",
        desc="Your Illinois fire protection district by address or ZIP — its trustees, its "
             "officers, and where to reach it.",
        og="Find your Illinois fire protection district by address or ZIP, and the %d "
           "people its own filings name." % people,
        lede=lede, sections=sections, named=people)


def park_district_page(tag, spec, worksheet):
    units = afr_units(load(SPECIAL_ROSTER), "park")
    people = sum(len(afr_people(rec)) for _n, rec in units)
    counties = dispatch_counties("park-district")

    lede = dict(
        html='<p class="lede"><strong>An Illinois park district is a government you elect '
             'and most people never vote in.</strong> It levies its own tax, runs the pools '
             'and the playing fields, and its commissioners are on the same ballot as the '
             'offices everybody has heard of. This names the %d commissioners and officers '
             'of the %d districts that file an annual report with the state.</p>'
             % (people, len(units)),
        cta='    <a class="cta" href="./#layers=%s">Find your park district →</a>\n'
            '    <p class="cta-note">Opens the map with the park district layer on. Search '
            'your address or ZIP, or tap your location.</p>' % spec["layers"])

    sections = """  <section>
    <h2>What the lookup shows</h2>
    <div class="answer-card">
      <p>Select any point and the card names the <strong>park district</strong> covering it,
        the people its latest filing names, and the district's office and telephone.</p>
      <p>The map draws park districts in %(counties)d Illinois counties. This page names the
        %(units)d districts among them that file an annual report the state publishes. A
        district the filings do not reach still draws on the map, and its card may still name
        people from its own county's data — this page is the filings, not everything the map
        knows.</p>
    </div>
  </section>

  <section>
    <h2>Elected commissioners, appointed staff</h2>
    <p>Park district commissioners are <strong>elected</strong>, and a park district is its own
      unit of government rather than a department of the city it is named after. The
      <strong>Role</strong> column tells the two kinds of name apart: a president, treasurer,
      secretary or commissioner sits on the elected board, while a director, superintendent,
      accountant or finance officer is staff the board employs.</p>
    <p>These filings name more staff than commissioners, and that is the form rather than the
      board: an Annual Financial Report is about money, so a district files whoever signs for
      it. A short board here is what the form had room for, never a claim about the board's
      size.</p>
  </section>

"""  % dict(counties=counties, units=len(units))
    sections += office_table(units, "district", "park districts")
    sections += afr_provenance("district", DISTRICT_NAME_NOTE)

    return dict(
        title="Who runs my park district?",
        subtitle="Illinois park district lookup — free, by address, ZIP, or a tap on the map.",
        desc="Your Illinois park district by address or ZIP — its elected commissioners, its "
             "officers, and where to reach it.",
        og="Find your Illinois park district by address or ZIP, and the %d people its own "
           "filings name." % people,
        lede=lede, sections=sections, named=people)


def library_district_page(tag, spec, worksheet):
    roster = load(LIBRARY_ROSTER)["libraries"]
    units = [(name, roster[name]) for name in sorted(roster, key=lambda s: s.lower())]
    filed_people = sum(len(afr_people(rec)) for _n, rec in units)
    counties = dispatch_counties("library-district")
    districts = sum(1 for name, _r in units if "District" in name)
    # THE SECOND PUBLISHER, and the page's own sentences have to stay true of
    # both. Only a district-governed library files an annual report, so the
    # municipal and township libraries appear in no filing at all and their
    # trustees are read off the library's own website; both tables are on this
    # page and neither claims the other's source.
    site = load(LIBRARY_SITE_ROSTER)["libraries"]
    site_people = sum(len(afr_people(rec)) for rec in site.values())
    people = filed_people + site_people

    lede = dict(
        html='<p class="lede"><strong>A library district is a taxing body you live inside, '
             'with a board you elect.</strong> It is not a department of the village it is '
             'named after, and its trustees stand for election on their own. This names the '
             '%d trustees and officers of %d Illinois libraries — %d of them from the '
             'annual report the library files with the state, and %d from the '
             'library\'s own website, which is the only publisher for a library that '
             'files no report of its own.</p>'
             % (people, len(units) + len(site), filed_people, site_people),
        cta='    <a class="cta" href="./#layers=%s">Find your library district →</a>\n'
            '    <p class="cta-note">Opens the map with the library district layer on. '
            'Search your address or ZIP, or tap your location.</p>' % spec["layers"])

    sections = """  <section>
    <h2>What the lookup shows</h2>
    <div class="answer-card">
      <p>Select any point and the card names the <strong>library</strong> serving it, whether
        it is a district you live inside or a municipal library whose area is simply the
        village, the people its latest filing names, and its office and telephone.</p>
      <p>The map draws library boundaries in %(counties)d Illinois counties. This page names
        %(units)d of them from the annual report the library files with the state and
        %(site)d more from the library's own website. A library in neither table still draws
        on the map, and its card may still name an administrator from the library systems'
        shared directory — these are the two publishers that name a BOARD, not everything the
        map knows.</p>
    </div>
  </section>

  <section>
    <h2>A district is not the same as a village library</h2>
    <p>An Illinois library <strong>district</strong> is a unit of government with its own
      boundary and its own elected trustees; a municipal library's area is simply the city or
      village, and its board is appointed by the municipality rather than elected. %(districts)d
      of the %(units)d libraries here name themselves districts and the rest do not, and
      nothing in a filing says how a particular board was chosen — so this page does not say it
      for any one of them.</p>
    <p>The <strong>Role</strong> column tells the two kinds of name apart either way: a
      president, treasurer, secretary or trustee sits on the board, while a director,
      librarian, manager or accountant is staff the board employs.</p>
  </section>

  <section>
    <h2>Where each name comes from</h2>
    <p>A library <strong>district</strong> files an Annual Financial Report with the Illinois
      Comptroller, and that filing names its board with the title the library itself filed. A
      <strong>municipal</strong> or <strong>township</strong> library files no report of its
      own — it is covered by its city's, village's or township's — so no filing names its
      trustees, and the library's own website is the only publisher that does. The second
      table below is read from that website, and every row names the page it came from and the
      day it was read, because a website carries no fiscal year and that is the only claim a
      reading of one can make.</p>
  </section>

"""  % dict(counties=counties, units=len(units), districts=districts, site=len(site))
    sections += office_table(units, "library", "libraries")
    sections += afr_provenance("library", LIBRARY_NAME_NOTE)

    return dict(
        title="Who runs my library district?",
        subtitle="Illinois library district lookup — free, by address, ZIP, or a tap on the "
                 "map.",
        desc="Your Illinois library district by address or ZIP — its trustees, its officers, "
             "and where to reach it.",
        # `people` now counts two publishers, so "its own filings name" would be
        # false of the website-read half.
        og="Find your Illinois library district by address or ZIP, and the %d people "
           "its own filing or its own website names." % people,
        lede=lede, sections=sections, named=people)


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
    dict(tag="mi", file="city-council.html", worksheet="mi/metro-worksheet.json",
         layers="city-ward", make=city_council_page, place="Michigan",
         wards=[("Battle Creek", "mi/data/app/mi-battle-creek-wards.json"),
                ("Detroit", "mi/data/app/mi-detroit-council-districts.json"),
                ("Flint", "mi/data/app/mi-flint-wards.json"),
                ("Grand Rapids", "mi/data/app/mi-grand-rapids-wards.json"),
                ("Rochester Hills", "mi/data/app/mi-rochester-hills-wards.json"),
                ("Warren", "mi/data/app/mi-warren-wards.json")],
         rosters=[("Detroit", "mi/data/app/mi-detroit-council-members.json", "city_council"),
                  ("Grand Rapids", "mi/data/app/mi-grand-rapids-council-members.json",
                   "city_council"),
                  ("Battle Creek", "mi/data/app/mi-battle-creek-commission-members.json",
                   "city_council")],
         counts=["mi/data/app/mi-detroit-council-members.json",
                 "mi/data/app/mi-grand-rapids-council-members.json",
                 "mi/data/app/mi-battle-creek-commission-members.json",
                 "mi/data/app/mi-battle-creek-wards.json",
                 "mi/data/app/mi-detroit-council-districts.json",
                 "mi/data/app/mi-flint-wards.json",
                 "mi/data/app/mi-grand-rapids-wards.json",
                 "mi/data/app/mi-rochester-hills-wards.json",
                 "mi/data/app/mi-warren-wards.json"],
         sibling=dict(page="county-commissioner.html",
                      label="Who is my county commissioner?",
                      note="The government your city sits inside.")),
    dict(tag="ia", file="county-auditor.html", worksheet="ia/metro-worksheet.json",
         layers="county", make=county_auditor_page,
         counts=["ia/data/app/ia-county-auditors.json"],
         sibling=dict(page="county-supervisor.html",
                      label="Who is my county supervisor?",
                      note="The board the auditor reports the election to.")),
    dict(tag="ia", file="city-council.html", worksheet="ia/metro-worksheet.json",
         layers="city-ward", make=city_council_page, place="Iowa",
         wards=[("Cedar Rapids", "ia/data/app/cedar-rapids-wards.json"),
                ("Des Moines", "ia/data/app/dsm-wards.json"),
                ("Waterloo", "ia/data/app/waterloo-wards.json")],
         rosters=[("Des Moines", "ia/data/app/dsm-council-members.json", "city_council"),
                  ("Cedar Rapids", "ia/data/app/cedar-rapids-council-members.json",
                   "city_council"),
                  ("Waterloo", "ia/data/app/waterloo-council-members.json", "city_council"),
                  ("small cities", "ia/data/app/ia-city-officials.json", "city_officials")],
         counts=["ia/data/app/dsm-council-members.json",
                 "ia/data/app/cedar-rapids-council-members.json",
                 "ia/data/app/waterloo-council-members.json",
                 "ia/data/app/ia-city-officials.json",
                 "ia/data/app/cedar-rapids-wards.json",
                 "ia/data/app/dsm-wards.json",
                 "ia/data/app/waterloo-wards.json"],
         sibling=dict(page="county-supervisor.html",
                      label="Who is my county supervisor?",
                      note="The government your city sits inside.")),
    dict(tag="ny", file="borough.html", worksheet="ny/metro-worksheet.json",
         layers="borough", make=borough_page,
         counts=["ny/data/app/borough-officials.json"],
         sibling=dict(page="council-district.html",
                      label="Who is my Council Member?",
                      note="The seat inside the borough, drawn smaller.")),
    dict(tag="il", file="supreme-court.html", worksheet="metro-worksheet.json",
         layers="il-supreme-court", make=supreme_court_page,
         counts=["il/data/app/il-court-justices.json"],
         sibling=dict(page="judicial-subcircuit.html",
                      label="What is a judicial subcircuit?",
                      note="The other judicial shape on this map, and a different court.")),
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
    # THE THREE ILLINOIS SPECIAL DISTRICTS. Each counts the roster it names on
    # the run that writes it, so no district count or seat count is typed into
    # the prose. Both rosters are counted by the fire page and only one by each
    # of the others, which is what `counts` is for: the weekly job that rewrites
    # either file has to regenerate every page that reads it.
    dict(tag="il", file="fire-district.html", worksheet="metro-worksheet.json",
         layers="fire-district", make=fire_district_page,
         counts=[SPECIAL_ROSTER],
         sibling=dict(page="park-district.html", label="Who runs my park district?",
                      note="Another special district drawn on its own lines — and one "
                           "whose board you do elect.")),
    dict(tag="il", file="park-district.html", worksheet="metro-worksheet.json",
         layers="park-district", make=park_district_page,
         counts=[SPECIAL_ROSTER],
         sibling=dict(page="library-district.html",
                      label="Who runs my library district?",
                      note="The other special district with an elected board on the same "
                           "ballot.")),
    dict(tag="il", file="library-district.html", worksheet="metro-worksheet.json",
         layers="library-district", make=library_district_page,
         counts=[LIBRARY_ROSTER],
         sibling=dict(page="fire-district.html",
                      label="Who runs my fire protection district?",
                      note="The special district that answers a 911 call, and the one "
                           "here whose board you may not elect.")),
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
