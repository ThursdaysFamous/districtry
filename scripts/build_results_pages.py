#!/usr/bin/env python3
"""
Election results a search engine can read: one page per place, and a section
on each county page, written from the files the results map already reads.

WHY. Until 2026-11-10 every precinct result this site holds reached a reader
only after JavaScript fetched a file and drew the map, so a search for
"<county> county election results" found the county's page of board members
(Search Console put it at positions 7 to 10 for four such searches, measured
2026-11-10) and nothing on it answered the question. Adam chose, that day, a results page for each place the
map has results for and a results section on every county page in those
states, published at once and marked unofficial ("Counties now"), and said the
aim is Chicago's February 2027 municipal election and the 2028 general. So the
pages keep ONE address each and take the year, the election's name and every
race from the results file: when a results file moves on to the next election
the same pages carry it, and keep whatever standing in search they have built.

    <tag>/election-results.html    every race decided across the place: the
                                   statewide offices, the U.S. House, the
                                   legislature and the courts elected by
                                   district (PLACE_GROUPS), plus any race on
                                   the ballot in every county with results;
                                   in a city instance (New York, San
                                   Francisco), every race
    <county page>#election-results every race on the ballot in that county,
                                   with that county's own votes

WHAT IS STATED AND WHERE IT COMES FROM. Every number on these pages is in the
results files (scripts/election_results_common.py describes them); nothing is
computed that the map's own cards do not also show, and the words follow the
cards' words (engine election-results): "Most votes so far" until the
publisher certifies, the publisher named, the date each office's results were
read, and the office's own note on what it is still counting. A county's votes
in a race are, in order of preference:

  * the race's own totals, where every precinct it is on the ballot in lies in
    that county (those totals include votes the publisher counts in no
    precinct, which is why they are preferred);
  * Illinois: the sum of the per-office totals (`bySource`) of the offices
    that count that county, which is exact, because each office reports its
    own totals;
  * Minnesota and Virginia: the sum of the county's precincts, which is the
    whole of the county's votes because neither publisher counts any vote
    outside a precinct (no contest in either file carries `outside`);
  * North Carolina: NOTHING, for a race crossing a county line, because the
    State Board reports early, absentee and provisional votes apart from
    precincts and the results file keeps them per race, not per county. The
    page names the race and links its whole count rather than printing a
    county figure that leaves those votes out (28% of the U.S. Senate race's
    votes, and more than half in most of its races, measured 2026-11-10).

WHAT THIS SCRIPT OWNS. The place pages' head, prose and structure (through
scripts/question_page.py's shell, whose five regions other generators fill),
and two GENERATED regions on each county page build_county_pages.py writes:
`election-results-css` inside its <style> and `election-results` before its
footer. build_county_pages.py writes both EMPTY and splices back whatever is on
disk, so the two scripts' --checks pass in either order. A county page with no
results keeps both regions empty, and --check holds them empty.

AND THE DAILY REFRESH WRITES THEM. Each results workflow rebuilds its file
every day until certification and opens a pull request; check_workflows()
fails a workflow that commits an election-results.json without running this
script and committing the pages and sitemap.xml it changes, so a refresh
cannot ship numbers on the map that its pages contradict.

    python3 scripts/build_results_pages.py           # write the pages
    python3 scripts/build_results_pages.py --check   # drift gate for CI
"""

import argparse
import datetime
import difflib
import glob
import html
import json
import os
import re
import sys

try:
    from zoneinfo import ZoneInfo
except ImportError:                                       # pragma: no cover
    ZoneInfo = None

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from question_page import (METROS, PageError, check_layer, head, load,  # noqa: E402
                           MARK_RE, preserved_from_disk, shared_head_block,
                           shell, THEMEBOOT_RE)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOWS = os.path.join(REPO_ROOT, ".github", "workflows")
PAGE_FILE = "election-results.html"
INDEX_NAME = "election-results.json"
LAYER = "election-results"
LAYER_CODE = "er"

# The county pages a state's results go on: build_county_pages.py's concept
# folder for that instance. An instance with results and no entry here (New
# York's results are the city's, whose boroughs have no county page; San
# Francisco is one county) carries every race on its place page instead.
COUNTY_PAGES = {
    "il": "county-board",
    "mn": "county-commissioner",
    "nc": "county-commissioner",
    "va": "local-government",
}

# Which race types are decided across the place rather than inside a county,
# by the group ids each builder writes. EVERY group of a county-page instance
# must be named here or in COUNTY_GROUPS: a new group fails the build rather
# than landing on one kind of page by default.
PLACE_GROUPS = {
    "il": {"statewide", "congress", "il-senate", "il-house"},
    "mn": {"statewide", "us-house", "mn-senate", "mn-house", "appellate",
           "district-court"},
    "nc": {"statewide", "us-house", "nc-senate", "nc-house", "appellate",
           "superior-court", "district-court", "district-attorney"},
    "va": {"statewide", "questions", "us-house", "va-house"},
}
COUNTY_GROUPS = {
    "il": {"mwrd", "county", "county-board", "ccbr", "regional", "judges",
           "judicial-subcircuit", "retention", "school-board", "local",
           "questions"},
    "mn": {"county", "county-commissioner", "county-park", "conservation",
           "city-ward", "city", "town", "school-board-district", "school-board",
           "other-local", "questions"},
    "nc": {"questions", "county", "county-commissioner", "school-board",
           "conservation", "city-ward", "city", "other-local"},
    "va": {"locality", "locality-questions", "supervisor-district",
           "school-board-district", "shared", "town", "town-ward"},
}

# Where a precinct's county is read from. Minnesota's, North Carolina's and
# Virginia's precinct keys open with the five-digit county code; Illinois's
# name the office that counted them ("cook:…", or a bare Chicago key), and
# each office is one county's.
GEOID_KEYS = {"mn", "nc", "va"}
IL_SOURCE_COUNTY = {"chicago": "Cook", "cook": "Cook", "bloomington": "McLean"}

# Two offices that between them count one whole county. The card names each
# office's own area; a county page that adds them up may call the sum the
# county's only where the two areas are the county's two halves.
WHOLE_COUNTY_PAIRS = {
    frozenset({"Chicago", "Suburban Cook County"}): "Cook County",
    frozenset({"McLean County outside Bloomington",
               "the City of Bloomington"}): "McLean County",
}

# The clock each place's readers keep, so "read on November 9" is their date.
TIME_ZONES = {"il": "America/Chicago", "mn": "America/Chicago",
              "nc": "America/New_York", "va": "America/New_York",
              "ny": "America/New_York", "ca": "America/Los_Angeles"}

CSS_REGION = "election-results-css"
HTML_REGION = "election-results"


def region_markers(name, style):
    body = "==== GENERATED:%s %s ===="
    if style == "css":
        return ("/* %s */" % (body % ("BEGIN", name)),
                "/* %s */" % (body % ("END", name)))
    return ("<!-- %s -->" % (body % ("BEGIN", name)),
            "<!-- %s -->" % (body % ("END", name)))


def empty_regions():
    """What build_county_pages.py writes into a page it creates: both regions,
    empty, each marker on its own line."""
    cb, ce = region_markers(CSS_REGION, "css")
    hb, he = region_markers(HTML_REGION, "html")
    return cb + "\n" + ce + "\n", hb + "\n" + he + "\n"


def read_region(text, name, style):
    b, e = region_markers(name, style)
    if b not in text or e not in text:
        return None
    i, j = text.index(b) + len(b), text.index(e)
    return text[i:j].strip("\n")


def put_region(text, name, style, body):
    b, e = region_markers(name, style)
    i, j = text.index(b) + len(b), text.index(e)
    return text[:i] + "\n" + (body + "\n" if body else "") + text[j:]


def splice_from_disk(new_html, current):
    """For build_county_pages.py: carry both regions' bodies over from the page
    on disk, so that script never rewrites what this one owns."""
    if not current:
        return new_html
    for name, style in ((CSS_REGION, "css"), (HTML_REGION, "html")):
        if read_region(new_html, name, style) is None:
            continue
        old = read_region(current, name, style)
        if old:
            new_html = put_region(new_html, name, style, old)
    return new_html


def wants_regions(tag, concept):
    return COUNTY_PAGES.get(tag) == concept


def esc(s):
    return html.escape(str(s), quote=True)


def upper_first(text):
    """The first letter in capitals, the rest as written ("the City of ..." -> "The City of ...")."""
    return text[:1].upper() + text[1:]


def pct(n, of):
    """The cards' electionPercent: one decimal, none at the ends."""
    if not of:
        return "0%"
    p = 100.0 * n / of
    return ("%.0f" if (p >= 99.95 or p < 0.05) else "%.1f") % p + "%"


def num(n):
    return "{:,}".format(n)


def long_date(iso, tag):
    """"November 3, 2026". A reading time is shown as the date it was in the
    place's own time zone."""
    s = str(iso or "")
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        d = datetime.date.fromisoformat(s)
    else:
        try:
            t = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return s
        if ZoneInfo and tag in TIME_ZONES:
            t = t.astimezone(ZoneInfo(TIME_ZONES[tag]))
        d = t.date()
    return "%s %d, %d" % (d.strftime("%B"), d.day, d.year)


def election_title(idx):
    """The cards' electionTitle: "2026 General Election"."""
    name = str(idx.get("election") or "Election")
    year = str(idx.get("electionDate") or "")[:4]
    return "%s %s" % (year, name) if year.isdigit() and year not in name else name


def election_phrase(idx):
    """"general election", as a sentence names it."""
    return str(idx.get("election") or "election").lower()


def worksheet_path(tag):
    own = os.path.join(tag, "metro-worksheet.json")
    return own if os.path.exists(os.path.join(REPO_ROOT, own)) else "metro-worksheet.json"


def layer_options(tag):
    """The publisher, area and still-counting note the app's own results layer
    is registered with, read from its index.html rather than restated."""
    path = os.path.join(REPO_ROOT, tag, "index.html")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    i = text.find("registerElectionResultsLayer({")
    if i < 0:
        raise PageError("%s/index.html registers no election results layer" % tag)
    block = text[i:i + 4000]
    out = {}
    for key in ("publisher", "areaName", "uncountedNote"):
        m = re.search(r"\b%s:\s*\"((?:[^\"\\]|\\.)*)\"" % key, block)
        if not m:
            raise PageError("%s/index.html's results layer names no %s" % (tag, key))
        out[key] = json.loads('"%s"' % m.group(1))
    return out


# ---------------------------------------------------------------- the data

class Results:
    """One instance's index, with each precinct's county and each contest's
    counties worked out once."""

    def __init__(self, tag):
        self.tag = tag
        path = os.path.join(REPO_ROOT, tag, "data", "app", INDEX_NAME)
        with open(path, encoding="utf-8") as f:
            self.idx = json.load(f)
        self.opts = layer_options(tag)
        self.groups = [g["id"] for g in self.idx["groups"]]
        self.group_label = {g["id"]: g["label"] for g in self.idx["groups"]}
        self.sources = {s["id"]: s for s in self.idx.get("sources") or []}
        self.county_name = {}          # county key -> display name
        self.precinct_county = self._precinct_counties()
        self.contest_counties = {c["id"]: self._on_ballot(c)
                                 for c in self.idx["contests"]}
        self._sums = None
        self.check_groups()

    # -- counties
    def _precinct_counties(self):
        keys = self.idx["precincts"]
        if self.tag in GEOID_KEYS:
            with open(os.path.join(REPO_ROOT, self.tag, "data", "app",
                                   "state-counties.json"), encoding="utf-8") as f:
                feats = json.load(f)["features"]
            names = {}
            for ft in feats:
                p = ft["properties"]
                name = p["NAME"]
                if name.endswith(" city"):
                    name = name[:-len(" city")] + " City"
                names[p["GEOID"]] = (name, p["BASENAME"], p["NAME"])
            out = []
            for k in keys:
                g = k[:5]
                if g not in names:
                    raise PageError("%s: precinct %s names county %s, which "
                                    "state-counties.json does not hold"
                                    % (self.tag, k, g))
                self.county_name[g] = names[g][0]
                out.append(g)
            self._county_files = names
            return out
        if self.tag == "il":
            self.source_county = {}
            for sid, s in self.sources.items():
                county = IL_SOURCE_COUNTY.get(sid)
                if not county:
                    m = re.match(r"^(?:Suburban )?(.+?) County\b", s.get("areaName") or "")
                    if not m:
                        raise PageError("il: cannot tell which county the %r office "
                                        "(%s) counts — add it to IL_SOURCE_COUNTY"
                                        % (sid, s.get("areaName")))
                    county = m.group(1)
                self.source_county[sid] = county
                self.county_name[county] = county + " County"
            out = []
            for k in keys:
                sid = k.split(":", 1)[0] if ":" in k else "chicago"
                if sid not in self.source_county:
                    raise PageError("il: precinct %s names no office in sources[]" % k)
                out.append(self.source_county[sid])
            return out
        return [None] * len(keys)

    def _on_ballot(self, c):
        start = c.get("from", 0)
        found = set()
        for i, ch in enumerate(c["leaders"]):
            if ch != "-":
                found.add(self.precinct_county[start + i])
        found.discard(None)
        return found

    def check_groups(self):
        if self.tag not in COUNTY_PAGES:
            return
        known = PLACE_GROUPS[self.tag] | COUNTY_GROUPS[self.tag]
        both = PLACE_GROUPS[self.tag] & COUNTY_GROUPS[self.tag]
        if both:
            raise PageError("%s: group(s) %s are in both PLACE_GROUPS and "
                            "COUNTY_GROUPS" % (self.tag, ", ".join(sorted(both))))
        new = [g for g in self.groups if g not in known]
        if new:
            raise PageError("%s's results name race type(s) %s that this script "
                            "has not placed — add each to PLACE_GROUPS (decided "
                            "across the state) or COUNTY_GROUPS (decided inside a "
                            "county) in scripts/build_results_pages.py"
                            % (self.tag, ", ".join(repr(g) for g in new)))
        gone = sorted(known - set(self.groups))
        if gone:
            raise PageError("%s: PLACE_GROUPS/COUNTY_GROUPS name %s, which the "
                            "results no longer carry — drop them"
                            % (self.tag, ", ".join(gone)))

    # -- status
    def certified(self, src=None):
        return bool((src or self.idx).get("certified"))

    def offices(self):
        """[(publisher, area, read, certified, certifiedDate, note)], one per
        office whose counts are in the file."""
        if self.sources:
            return [(s["publisher"], s.get("areaName"), s.get("read"),
                     bool(s.get("certified")), s.get("certifiedDate"),
                     s.get("uncountedNote") or "")
                    for s in self.idx["sources"]]
        return [(self.opts["publisher"], self.opts["areaName"], self.idx.get("read"),
                 bool(self.idx.get("certified")), self.idx.get("certifiedDate"),
                 self.opts["uncountedNote"])]

    # -- place
    def all_counties(self):
        return sorted(set(c for c in self.precinct_county if c))

    def on_place_page(self, c):
        if self.tag not in COUNTY_PAGES:
            return True
        if c["group"] in PLACE_GROUPS[self.tag]:
            return True
        everywhere = set(self.all_counties())
        return len(everywhere) > 1 and self.contest_counties[c["id"]] >= everywhere

    def place_complete(self, c):
        """True where the race's totals are the whole race, as far as the file
        says: the card's own `beyond`, read per office in Illinois."""
        if not self.sources:
            return not c.get("beyond")
        by = c.get("bySource")
        if not by:
            return not c.get("beyond")
        if all(not v.get("beyond") for v in by.values()):
            return True
        counties = self.contest_counties[c["id"]]
        if len(counties) == 1:
            county = next(iter(counties))
            mine = {s for s, cty in self.source_county.items() if cty == county}
            areas = frozenset(self.sources[s].get("areaName") for s in mine)
            return set(by) == mine and areas in WHOLE_COUNTY_PAIRS
        return False

    # -- county figures
    def county_sources(self, county):
        return sorted(s for s, cty in self.source_county.items() if cty == county)

    def county_area(self, county):
        if self.tag != "il":
            return self.county_name[county]
        areas = [self.sources[s].get("areaName") for s in self.county_sources(county)]
        whole = self.county_name[county]
        if whole in areas:
            return whole
        pair = WHOLE_COUNTY_PAIRS.get(frozenset(areas))
        return pair or " and ".join(areas)

    def _precinct_sums(self):
        if self._sums is not None:
            return self._sums
        sums = {}
        part_dir = os.path.join(REPO_ROOT, self.tag, "data", "app", "election-results")
        for path in sorted(glob.glob(os.path.join(part_dir, "*.json"))):
            with open(path, encoding="utf-8") as f:
                part = json.load(f)
            for key, rec in part["precincts"].items():
                g = key[:5]
                for row in rec.get("contests") or []:
                    cid = row[0]
                    vals = row[1:]
                    cur = sums.setdefault((g, cid), [0] * len(vals))
                    for n, v in enumerate(vals):
                        if v is None or cur[n] is None:
                            cur[n] = None
                        else:
                            cur[n] += v
        self._sums = sums
        return sums

    def county_figures(self, c, county):
        """(total, which choices, complete-in-county, reason-if-none) for one
        race in one county. total is [votes in the race, one count per choice]
        or None where this county's share cannot be told."""
        counties = self.contest_counties[c["id"]]
        alone = counties == {county}
        every = list(range(len(c["choices"])))
        if self.tag == "il":
            mine = self.county_sources(county)
            by = c.get("bySource")
            if not by:
                if "chicago" in mine:
                    return c["total"], every, alone and not c.get("beyond"), None
                return None, every, alone, "uncounted"
            total = [0] * len(c["total"])
            which, used = set(), []
            for s in mine:
                if s in by:
                    used.append(s)
                    for n, v in enumerate(by[s]["total"]):
                        total[n] += v
                    which |= set(by[s].get("choices") or every)
            if not used:
                return None, every, alone, "uncounted"
            whole_here = alone and all(not by[s].get("beyond") for s in used) or (
                alone and frozenset(self.sources[s].get("areaName") for s in mine)
                in WHOLE_COUNTY_PAIRS and set(used) == set(mine))
            return total, sorted(which), whole_here, None
        if alone:
            return c["total"], every, True, None
        if c.get("outside") and any(c["outside"]):
            return None, every, False, "outside"
        got = self._precinct_sums().get((county, c["id"]))
        if got is None or any(v is None for v in got):
            return None, every, False, "withheld"
        return got, every, False, None

    # -- county page files
    def county_page(self, county):
        """The county page's file name in its concept folder, or None."""
        concept = COUNTY_PAGES.get(self.tag)
        if not concept:
            return None
        from build_county_pages import county_slug
        d = os.path.join(REPO_ROOT, self.tag, concept)
        if self.tag == "il":
            names = [county]
        else:
            _disp, base, full = self._county_files[county]
            names = [base, full]
        for n in names:
            slug = county_slug(n)
            if os.path.exists(os.path.join(d, slug + ".html")):
                return slug + ".html"
        return None


# ---------------------------------------------------------------- rendering

def race_table(c, total, which, lead_word, cls):
    """The card's raceTable as HTML: a row per choice, the leader marked."""
    counts = [total[n + 1] for n in which]
    known = all(v is not None for v in counts)
    top = max(counts + [0]) if known else -1
    tied = counts.count(top) > 1 if top > 0 else False
    rows = []
    for n in which:
        v = total[n + 1]
        mark = ""
        if top > 0 and v == top:
            mark = ' <span class="lead">%s</span>' % ("Tied for most votes" if tied else lead_word)
        rows.append('<tr><th scope="row">%s%s</th><td class="n">%s</td><td class="n">%s</td></tr>'
                    % (esc(c["choices"][n]), mark,
                       num(v) if v is not None else "Withheld",
                       pct(v, total[0]) if v is not None and total[0] is not None else "—"))
    return ('<table class="%s">\n<thead><tr><th scope="col">Choice</th>'
            '<th scope="col" class="n">Votes</th><th scope="col" class="n">Share</th>'
            '</tr></thead>\n<tbody>\n%s\n</tbody>\n</table>' % (cls, "\n".join(rows)))


def leader_line(c, total, which, lead_word):
    counts = [total[n + 1] for n in which]
    if not counts or any(v is None for v in counts):
        return ""
    top = max(counts)
    if top <= 0:
        return "No votes counted yet"
    leaders = [c["choices"][n] for n in which if total[n + 1] == top]
    if len(leaders) > 1:
        return "Tied for most votes: " + ", ".join(leaders)
    return "%s: %s, %s" % (lead_word, leaders[0], pct(top, total[0]))


def multiple_note(c):
    if c.get("multiple"):
        return (" Voters could choose more than one candidate in this race, so each "
                "share is of all the votes cast in it, not of the people who voted.")
    return ""


def status_paragraph(res, tag, offices):
    """The card's notice, for the offices a page or section reads."""
    if all(o[3] for o in offices):
        parts = ["the %s on %s" % (esc(o[0]), long_date(o[4], tag)) if o[4]
                 else "the %s" % esc(o[0]) for o in offices]
        return ('<p class="results-status"><strong>Official results,</strong> certified by %s.</p>'
                % join_words(parts))
    if len(offices) > 3:
        return ('<p class="results-status"><strong>Unofficial results.</strong> These '
                'numbers are not certified and will change. Each office\'s results were '
                'read on the date in the table below.</p>')
    notes = []
    for o in offices:
        if o[5] and o[5] not in notes:
            notes.append(o[5])
    reads = {}
    for o in offices:
        reads.setdefault(long_date(o[2], tag), []).append("the " + o[0])
    read_txt = "; ".join("%s on %s" % (join_words(v), d) for d, v in sorted(
        reads.items(), key=lambda kv: datetime.datetime.strptime(kv[0], "%B %d, %Y")))
    return ('<p class="results-status"><strong>Unofficial results.</strong> %s'
            'These numbers are not certified and will change. Read from %s.</p>'
            % ("".join(esc(n) + " " for n in notes), esc(read_txt)))


def join_words(items):
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return "%s and %s" % tuple(items)
    return "%s and %s" % (", ".join(items[:-1]), items[-1])


def map_link(prefix, cid):
    return "%s#l=%s&amp;r=%s" % (prefix, LAYER_CODE, esc(cid))


# -- the place page

def place_race(res, c, lead_word, opened):
    total = c["total"]
    which = list(range(len(c["choices"])))
    notes = []
    if total[0]:
        notes.append("Votes counted in this race: %s." % num(total[0]) + (
            multiple_note(c) or " Each share is of those votes."))
    if not res.place_complete(c):
        if res.sources:
            notes.append("These totals add up only the offices listed above; any part "
                         "of this race outside the places they count is not included.")
        else:
            notes.append("This race reaches beyond %s, so these totals are not the "
                         "whole race." % esc(res.opts["areaName"]))
    out = c.get("outside")
    if out and out[0] and total[0]:
        share = pct(out[0], total[0])
        notes.append("%s were counted outside any precinct, so they are in the totals "
                     "above and not in the map's colours."
                     % ("%s votes" % num(out[0]) if share in ("0%", "0.0%")
                        else "%s of these votes (%s)" % (share, num(out[0]))))
    line = leader_line(c, total, which, lead_word)
    return """      <details id="r-%(id)s"%(open)s>
        <summary><span>%(name)s<small>%(line)s</small></span></summary>
        <div class="flow-table-wrap">
        %(table)s
        </div>
%(notes)s        <p class="race-map"><a href="%(map)s">See this race precinct by precinct on the map →</a></p>
      </details>
""" % dict(id=esc(c["id"]), open=" open" if opened else "", name=esc(c["name"]),
           line=esc(line), table=race_table(c, total, which, lead_word, "flow results-table"),
           notes="".join('        <p class="race-note">%s</p>\n' % n for n in notes),
           map=map_link("./", c["id"]))


def place_page(res, worksheet, metros):
    tag, idx = res.tag, res.idx
    brand = worksheet["brand"]
    app_name = brand["app_name"]
    landing = next(m["landing_name"] for m in metros if m["tag"] == tag)
    title_e = election_title(idx)
    year = str(idx.get("electionDate") or "")[:4]
    when = long_date(idx.get("electionDate"), tag)
    offices = res.offices()
    certified = all(o[3] for o in offices)
    lead_word = "Most votes" if certified else "Most votes so far"
    status_word = "Official" if certified else "Unofficial"

    if res.sources:
        counted = "as %d election offices across %d counties publish them" % (
            len(offices), len(set(res.source_county.values())))
    else:
        counted = "as the %s publishes them" % res.opts["publisher"]
    lede_html = (
        '<p class="lede"><strong>%s results of %s\'s %s %s, %s.</strong> Each race lists '
        'every choice\'s votes and share of the vote. The map colours each precinct by '
        'who got the most votes there.</p>\n    %s'
        % (status_word, esc(landing), esc(when), esc(election_phrase(idx)),
           esc(counted), status_paragraph(res, tag, offices)))
    lede = dict(
        html=lede_html,
        cta='    <a class="cta" href="./#layers=%s">See your precinct\'s results →</a>\n'
            '    <p class="cta-note">Opens the map with the election results on. Pick a '
            'race, then pick a precinct.</p>' % LAYER)

    # -- where the numbers come from
    src_rows = []
    for s in (idx.get("sources") or []):
        src_rows.append('      <tr><td class="who">%s</td><td><a href="%s">%s</a></td>'
                        '<td>%s</td><td>%s</td></tr>'
                        % (esc(upper_first(s.get("areaName") or "")), esc(s["source"]), esc(s["publisher"]),
                           long_date(s.get("read"), tag),
                           ("Certified %s" % long_date(s.get("certifiedDate"), tag))
                           if s.get("certified") else "Unofficial"))
    if src_rows:
        sources_html = """  <section>
    <h2>Where these numbers come from</h2>
    <p>The map reads each office's own results, and these pages add them up. They are not
      all of %(landing)s: the races below count only the places in this table.</p>
    <div class="flow-table-wrap">
    <table class="flow">
      <thead><tr><th>Area</th><th>Counted by</th><th>Read on</th><th>Status</th></tr></thead>
      <tbody>
%(rows)s
      </tbody>
    </table>
    </div>
  </section>
""" % dict(landing=esc(landing), rows="\n".join(src_rows))
    else:
        extra = ""
        if any(c.get("outside") and any(c["outside"]) for c in idx["contests"]):
            extra = (" The %s reports some votes (early, absentee and provisional ballots) "
                     "apart from precincts: they are in each race's totals and not in the "
                     "map's colours." % esc(res.opts["publisher"]))
        sources_html = """  <section>
    <h2>Where these numbers come from</h2>
    <p>Every number here is from the <a href="%(src)s">%(pub)s</a>, read on %(read)s.%(extra)s</p>
  </section>
""" % dict(src=esc(idx["source"]), pub=esc(res.opts["publisher"]),
           read=long_date(idx.get("read"), tag), extra=extra)

    # -- the races
    shown = [c for c in idx["contests"] if res.on_place_page(c)]
    by_group = {}
    for c in shown:
        by_group.setdefault(c["group"], []).append(c)
    race_sections = []
    first = True
    for g in res.groups:
        cs = by_group.get(g)
        if not cs:
            continue
        body = "".join(place_race(res, c, lead_word, first and len(cs) <= 6) for c in cs)
        race_sections.append('  <section class="results-group">\n    <h2>%s</h2>\n%s  </section>\n'
                             % (esc(res.group_label[g]), body))
        first = False

    # -- by county
    county_html = ""
    if tag in COUNTY_PAGES:
        rows = []
        for county in sorted(res.all_counties(), key=lambda k: res.county_name[k]):
            n = sum(1 for c in idx["contests"] if county in res.contest_counties[c["id"]])
            page = res.county_page(county)
            name = esc(res.county_area(county))
            if page:
                rows.append('      <li><a href="%s/%s#election-results">%s</a> '
                            '<span>%d race%s</span></li>'
                            % (COUNTY_PAGES[tag], page, name, n, "" if n == 1 else "s"))
            else:
                rows.append('      <li>%s <span>%d race%s</span></li>'
                            % (name, n, "" if n == 1 else "s"))
        county_html = """  <section>
    <h2>Results by county</h2>
    <p>Every race on the ballot in a county, with that county's own votes, is on its page:
      the county board, the city and town offices, the school boards and the questions as well
      as the races above.</p>
    <ul class="results-counties">
%s
    </ul>
  </section>
""" % "\n".join(rows)

    about = """  <section>
    <h2>About these results</h2>
    <p>These pages and the map read the same files, rebuilt each day from the publishers' own
      results until they are certified. A race's totals here are the publisher's; where the
      publisher reports a race by precinct, the map shows the same race one precinct at a time.
      A race is listed under the kind of office it elects, in the order the map's race menu
      lists them.</p>
    <div class="disclaimer">
      <strong>Not for legal or official use.</strong> These are the results as published on the
      dates above, and %(unofficial)s. For the official count, ask the office that ran the
      election.
    </div>
  </section>
""" % dict(unofficial="certified results can differ from them" if not certified
           else "the certifying office's own record is the official one")

    sections = sources_html + "\n" + "\n".join(race_sections) + "\n" + county_html + "\n" + about

    title = "%s precinct election results" % year
    subtitle = ("%s results of the %s, race by race, with every precinct on the map."
                % (status_word, title_e))
    desc = ("%s results of the %s %s in %s: each race's candidates, votes and "
            "share, and every precinct on the map." % (status_word, year,
                                                      election_phrase(idx), landing))
    if len(desc) > 155:
        desc = ("%s %s %s results in %s, race by race, with every precinct on the map."
                % (status_word, year, election_phrase(idx), landing))
    og = desc

    related = related_rows(tag, landing)
    page_path = os.path.join(REPO_ROOT, tag, PAGE_FILE)
    text = head(tag, brand, app_name, PAGE_FILE, title, desc, og)
    text += shell(app_name, title, subtitle, lede, sections, related,
                  preserved_from_disk(page_path),
                  shared_head_block(tag, THEMEBOOT_RE, "theme boot script"),
                  shared_head_block(tag, MARK_RE, "districtry mark"), tag,
                  extra_css=PLACE_CSS)
    return page_path, text, len(shown)


PLACE_CSS = """/* The results pages' own few rules (scripts/build_results_pages.py): a race's
   summary carries its leader under its name, and the table's numbers line up. */
.results-group details summary > span { display: block; }
.results-group details summary small {
  display: block; font-weight: 400; font-size: 14px; color: var(--slate); margin-top: 3px;
}
table.results-table { min-width: 0; }
table.results-table .n { text-align: right; white-space: nowrap; }
table.results-table .lead {
  display: inline-block; margin-left: 6px; font-size: 12.5px; font-weight: 600;
  color: var(--accent-deep);
}
.race-note { font-size: 14px; }
.race-map { font-size: 14.5px; margin: 0 0 18px; }
.results-counties { columns: 2 16em; padding-left: 20px; }
.results-counties li { margin: 0 0 6px; break-inside: avoid; line-height: 28px; }
.results-counties span { color: var(--slate); font-size: 13.5px; margin-left: 4px; }
.results-status { font-size: 15px; }
"""


def related_rows(tag, landing):
    rows = ['      <li><a href="./">What district am I in?</a><span>Every district that '
            'covers one point in %s, and who represents you there.</span></li>' % esc(landing)]
    concept = COUNTY_PAGES.get(tag)
    if concept and os.path.exists(os.path.join(REPO_ROOT, tag, concept + ".html")):
        rows.append('      <li><a href="%s.html">Who is on my county board?</a><span>Every '
                    'county board this map names, county by county.</span></li>' % concept)
    if os.path.exists(os.path.join(REPO_ROOT, tag, "precinct.html")):
        rows.append('      <li><a href="precinct.html">What precinct am I in?</a><span>Your '
                    'voting precinct and, where the county publishes it, your polling '
                    'place.</span></li>')
    if os.path.exists(os.path.join(REPO_ROOT, tag, "congress.html")):
        rows.append('      <li><a href="congress.html">Who is my member of Congress?</a>'
                    '<span>Your U.S. House district and who holds it.</span></li>')
    return "\n".join(rows)


# -- the county sections

COUNTY_CSS = """/* The results section (scripts/build_results_pages.py). */
.results { margin: 30px 0 0; padding: 16px 0 0; border-top: 1px solid var(--border); }
.results h2 {
  font: var(--font-heading-weight, 700) 19px/1.2 var(--font-heading);
  margin: 0 0 10px; text-transform: uppercase; letter-spacing: 0.02em;
}
.results p { font-size: 14.5px; margin: 0 0 10px; }
.results .results-links { line-height: 28px; }
.results details { border-top: 1px solid var(--border); }
.results summary { cursor: pointer; padding: 10px 0; font-weight: 700; line-height: 28px; }
.results h3 { font-size: 16px; margin: 14px 0 6px; }
.results .race-lead { display: block; font-size: 13.5px; font-weight: 400; color: var(--muted); }
.results-wrap { overflow-x: auto; max-width: 100%; }
.results table { border-collapse: collapse; width: 100%; font-size: 14px; margin: 0 0 6px; }
.results th, .results td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); }
.results thead th { font-size: 12px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
.results .n { text-align: right; white-space: nowrap; }
.results .lead { display: inline-block; margin-left: 6px; font-size: 12px; font-weight: 600; color: var(--brand-700); }
.results .race-note { font-size: 13px; color: var(--muted); margin: 4px 0 4px; }
.results .race-map { font-size: 13.5px; line-height: 28px; margin: 0 0 8px; }"""


def county_race(res, c, county, lead_word):
    total, which, whole_here, why = res.county_figures(c, county)
    area = res.county_area(county)
    notes = []
    if total is not None:
        table = '<div class="results-wrap">\n%s\n</div>' % race_table(
            c, total, which, lead_word, "results-table")
        line = leader_line(c, total, which, lead_word)
        if total[0]:
            notes.append("Votes counted in this race in %s: %s.%s"
                         % (esc(area), num(total[0]), multiple_note(c)))
        if not whole_here:
            notes.append("This race also includes voters outside %s; these are %s's "
                         "votes only." % (esc(area), esc(area)))
    else:
        table, line = "", ""
        if why == "outside":
            notes.append("The %s reports early, absentee and provisional votes apart from "
                         "precincts, so its count of this race cannot be split by county."
                         % esc(res.opts["publisher"]))
        else:
            notes.append("This page cannot split this race's count by county.")
    links = ['<a href="%s">Precinct by precinct on the map →</a>' % map_link("../", c["id"])]
    if res.on_place_page(c):
        links.append('<a href="../%s#r-%s">The whole race →</a>' % (PAGE_FILE, esc(c["id"])))
    return ("<h3 id=\"r-%s\">%s%s</h3>\n%s%s\n<p class=\"race-map\">%s</p>"
            % (esc(c["id"]), esc(c["name"]),
               '<span class="race-lead">%s</span>' % esc(line) if line else "",
               table + "\n" if table else "",
               "".join('<p class="race-note">%s</p>' % n for n in notes),
               " · ".join(links)))


def county_section(res, county, landing):
    tag, idx = res.tag, res.idx
    contests = [c for c in idx["contests"] if county in res.contest_counties[c["id"]]]
    if not contests:
        return ""
    if res.sources:
        mine = res.county_sources(county)
        offices = [o for o, s in zip(res.offices(), idx["sources"]) if s["id"] in mine]
    else:
        offices = res.offices()
    certified = all(o[3] for o in offices)
    lead_word = "Most votes" if certified else "Most votes so far"
    area = res.county_area(county)
    groups = []
    for g in res.groups:
        cs = [c for c in contests if c["group"] == g]
        if not cs:
            continue
        races = "\n".join(county_race(res, c, county, lead_word) for c in cs)
        groups.append('<details%s>\n<summary>%s (%d)</summary>\n%s\n</details>'
                      % (" open" if not groups else "", esc(res.group_label[g]), len(cs), races))
    return """<section class="results" id="election-results">
<h2>%(title)s results</h2>
%(status)s
<p>The votes counted in %(area)s in each race on the ballot here, as the results map reads
them. A race that crosses the county line shows this county's votes only.</p>
<p class="results-links"><a href="../%(page)s">All of %(landing)s's results</a> · <a href="../#layers=%(layer)s">See your precinct on the map</a></p>
%(groups)s
</section>""" % dict(title=esc(election_title(idx)), status=status_paragraph(res, tag, offices),
                     area=esc(area), page=PAGE_FILE, landing=esc(landing), layer=LAYER,
                     groups="\n".join(groups))


# ---------------------------------------------------------------- gates

def check_workflows(tags):
    """A workflow that commits a results file must rebuild these pages and
    commit them, with the sitemap whose dates they move."""
    seen = {}
    for name in sorted(os.listdir(WORKFLOWS)):
        if not name.endswith((".yml", ".yaml")):
            continue
        with open(os.path.join(WORKFLOWS, name), encoding="utf-8") as f:
            text = f.read()
        if "git add" not in text:
            continue
        for tag in tags:
            data = "%s/data/app/%s" % (tag, INDEX_NAME)
            if data not in text:
                continue
            seen[tag] = name
            need = ["scripts/build_results_pages.py", "%s/%s" % (tag, PAGE_FILE),
                    "scripts/build_sitemap.py", "sitemap.xml"]
            if tag in COUNTY_PAGES:
                need.append("%s/%s" % (tag, COUNTY_PAGES[tag]))
            missing = [n for n in need if n not in text]
            if missing:
                raise PageError(
                    ".github/workflows/%s commits %s and never %s — add a step running "
                    "python3 scripts/build_results_pages.py and python3 "
                    "scripts/build_sitemap.py, and `git add` the pages and sitemap.xml"
                    % (name, data, "names " + ", ".join(missing)))
            if "fetch-depth: 0" not in text:
                raise PageError(".github/workflows/%s rebuilds sitemap.xml, which reads "
                                "each page's date from git, without `fetch-depth: 0`" % name)
    return seen


def instances():
    out = []
    for path in sorted(glob.glob(os.path.join(REPO_ROOT, "*", "data", "app", INDEX_NAME))):
        out.append(os.path.relpath(path, REPO_ROOT).split(os.sep)[0])
    return out


def run(args):
    metros = load(METROS)["metros"]
    live = {m["tag"] for m in metros}
    tags = [t for t in instances() if t in live]
    if len(tags) < 2:
        raise PageError("found results for %d live instance(s); the discovery rule "
                        "is broken" % len(tags))
    wf = check_workflows(tags)
    drift, written, summary = [], 0, []
    for tag in tags:
        res = Results(tag)
        worksheet = load(worksheet_path(tag))
        check_layer(worksheet, LAYER, "%s/%s" % (tag, PAGE_FILE))
        landing = next(m["landing_name"] for m in metros if m["tag"] == tag)
        path, text, n_place = place_page(res, worksheet, metros)
        targets = [(path, text)]
        n_county = 0
        concept = COUNTY_PAGES.get(tag)
        if concept:
            d = os.path.join(REPO_ROOT, tag, concept)
            by_file = {}
            for county in res.all_counties():
                page = res.county_page(county)
                if page:
                    by_file[page] = county
            for fpath in sorted(glob.glob(os.path.join(d, "*.html"))):
                with open(fpath, encoding="utf-8") as f:
                    current = f.read()
                if read_region(current, HTML_REGION, "html") is None or \
                        read_region(current, CSS_REGION, "css") is None:
                    raise PageError("%s carries no %s region — run python3 "
                                    "scripts/build_county_pages.py first"
                                    % (os.path.relpath(fpath, REPO_ROOT), HTML_REGION))
                county = by_file.get(os.path.basename(fpath))
                body = county_section(res, county, landing) if county else ""
                new = put_region(current, CSS_REGION, "css", COUNTY_CSS if body else "")
                new = put_region(new, HTML_REGION, "html", body)
                if body:
                    n_county += 1
                targets.append((fpath, new))
        if tag not in wf:
            raise PageError("no workflow commits %s/data/app/%s, so nothing would keep "
                            "its pages current" % (tag, INDEX_NAME))
        for fpath, text in targets:
            try:
                with open(fpath, encoding="utf-8") as f:
                    current = f.read()
            except OSError:
                current = None
            if current == text:
                continue
            rel = os.path.relpath(fpath, REPO_ROOT)
            if args.check:
                drift.append((rel, current, text))
                continue
            with open(fpath, "w", encoding="utf-8", newline="") as f:
                f.write(text)
            written += 1
        summary.append("%s: %d race(s) on its page%s" % (
            tag, n_place, ", %d county page(s) with results" % n_county if concept else ""))

    if args.check:
        for rel, current, text in drift[:5]:
            if current is None:
                print("build-results-pages: %s does not exist" % rel, file=sys.stderr)
                continue
            print("build-results-pages: DRIFT in %s" % rel, file=sys.stderr)
            for i, line in enumerate(difflib.unified_diff(
                    current.splitlines(), text.splitlines(), fromfile="committed",
                    tofile="regenerated", lineterm="", n=1)):
                if i > 30:
                    print("  …", file=sys.stderr)
                    break
                print("  " + line, file=sys.stderr)
        if drift:
            raise PageError("%d page(s) out of date — run python3 "
                            "scripts/build_results_pages.py" % len(drift))
        print("build-results-pages: OK — " + "; ".join(summary))
    else:
        print("build-results-pages: OK — %d file(s) written; %s"
              % (written, "; ".join(summary)))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="drift gate: fail rather than write")
    args = ap.parse_args()
    try:
        return run(args)
    except PageError as exc:
        print("build-results-pages: FAIL — %s" % exc, file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
