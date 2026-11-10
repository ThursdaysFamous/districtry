#!/usr/bin/env python3
"""
il/chicago-candidates.html: who is running in Chicago's next municipal
election, ward by ward, written from il/data/source/chicago-candidates.json.

WHY. Adam asked on 2026-11-10 for a "who's running in my ward" page for the
February 23, 2027 election and chose to publish it from the filed list, marked
objections pending, rather than wait for the certified ballot ("now"), because
a page has to exist and be indexed before the searches for an election peak.
His stated aim is Chicago's 2027 municipal election and the 2028 general, so
the page keeps ONE address and takes the election's date, every race and every
name from the data file: when the Board publishes the next municipal list, the
same page carries it.

WHAT IT SAYS AND WHERE EACH PART COMES FROM.
  * names, statuses, order and each race's "vote for" number: the Board's list,
    as build_chicago_candidates.py wrote it, printed in capitals as the Board
    prints them (turning "MCDONALD" into "Mcdonald" would misspell people);
  * the time the list describes: the list's own "Status as of" line;
  * the last day the Board may certify the ballot: 68 days before the
    election, the deadline 10 ILCS 5/10-15 sets ("not less than 68 days before
    election"), which is how the Board's own 2027 calendar arrives at December
    17, 2026 for this election. It is computed, so it moves with the election;
  * who holds each ward's seat now: il/data/source/ward-members.json, the
    City's roster (scripts/build_chicago_ward_roster.py), printed as its own
    line and never matched against a candidate's name, because the two lists
    spell names differently and a match would be a guess.
Home addresses, which the Board's list prints, are not in the data file and so
cannot reach the page.

THE STATUS LINE IS DERIVED FROM THE LIST AND NEVER FROM THE CLOCK. While any
candidate is "Challenged" the page says objections are pending; when none is,
it says so. A sentence keyed to today's date would turn --check red on every
pull request the day a deadline passed, so none is. What the page does after
election day is the next change, not this one: until it is made the page goes
on describing who filed for that election.

THE MAP LINKS HERE, AND THE TWO ARE HELD TOGETHER. Chicago's ward card in
il/index.html links each ward's section until election day ends, using the
date in CHICAGO_CANDIDATES_ELECTION. --check fails when that date and the data
file's election date differ, so the card cannot offer one election's field as
another's.

AND THE DAILY REFRESH WRITES IT. update-chicago-candidates.yml rebuilds the
data file from the Board's list each day until certification and opens a pull
request; check_workflow() fails the build if that workflow stops running this
script or stops committing the page and sitemap.xml it changes.

WHAT THIS SCRIPT OWNS. The page's head, prose and structure, through
scripts/question_page.py's shell, whose other regions other generators fill
(the address box from build_question_forms.py, the engine fences from
compose_app.py) and which this reads back from disk on every run.

    python3 scripts/build_candidates_page.py           # write the page
    python3 scripts/build_candidates_page.py --check   # drift gate for CI
"""

import argparse
import datetime
import difflib
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from question_page import (METROS, PageError, check_layer, head, load,  # noqa: E402
                           MARK_RE, preserved_from_disk, shared_head_block,
                           shell, THEMEBOOT_RE)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAG = "il"
PAGE_FILE = "chicago-candidates.html"
DATA = os.path.join("il", "data", "source", "chicago-candidates.json")
ROSTER = os.path.join("il", "data", "source", "ward-members.json")
APP = os.path.join("il", "index.html")
WORKFLOW = os.path.join(".github", "workflows", "update-chicago-candidates.yml")
APP_DATE_RE = re.compile(r'var CHICAGO_CANDIDATES_ELECTION = "(\d{4}-\d{2}-\d{2})";')
# 10 ILCS 5/10-15: the Board certifies the ballot "not less than 68 days before
# election". The Board's 2027 calendar puts that day at December 17, 2026.
CERTIFY_DAYS = 68
CERTIFY_STATUTE = "10 ILCS 5/10-15"

STATUS_KEY = {
    "Candidate": "The Board lists this filing with no objection on file.",
    "Challenged": ("Someone has filed an objection to the candidate's nominating "
                   "petitions. The Board hears each objection and decides whether the "
                   "name goes on the ballot."),
}
NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}
MONTHS = ("January February March April May June July August September October "
          "November December").split()


def esc(s):
    return html.escape(str(s), quote=True)


def long_date(d):
    return "%s %d, %d" % (MONTHS[d.month - 1], d.day, d.year)


def clock(dt):
    h = dt.hour % 12 or 12
    return "%d:%02d %s" % (h, dt.minute, "a.m." if dt.hour < 12 else "p.m.")


def ordinal(n):
    if 10 <= n % 100 <= 20:
        return "%dth" % n
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def race_html(c, heading, anchor, holder=None):
    rows = []
    for p in c["candidates"]:
        st = p["status"]
        num = ('<span class="ballot-no">%d</span> ' % p["ballotNumber"]
               if p.get("ballotNumber") else "")
        rows.append('        <li>%s<span class="nm">%s</span>'
                    '<span class="st%s">%s</span></li>'
                    % (num, esc(p["name"]), " st-challenged" if st == "Challenged" else "",
                       esc(st)))
    if not rows:
        rows.append('        <li class="none">Nobody filed for this race.</li>')
    lines = []
    if holder:
        lines.append('      <p class="holder">Holds the seat now: %s</p>' % esc(holder))
    if c["voteFor"] > 1:
        lines.append('      <p class="vote-for">Vote for up to %s.%s</p>'
                     % (NUMBER_WORDS.get(c["voteFor"], c["voteFor"]),
                        (" Fewer people filed than the race has seats."
                         if 0 < len(c["candidates"]) < c["voteFor"] else "")))
    return ('    <div class="race" id="%s">\n      <h3>%s</h3>\n%s%s'
            '      <ul class="cands">\n%s\n      </ul>\n    </div>\n'
            % (anchor, esc(heading), "\n".join(lines) + ("\n" if lines else ""),
               "", "\n".join(rows)))


PAGE_CSS = """/* The candidates page's own few rules (scripts/build_candidates_page.py). */
.cand-status { font-size: 15px; }
.cand-jump { display: flex; flex-wrap: wrap; gap: 6px; list-style: none; padding: 0; margin: 10px 0 18px; }
.cand-jump a {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 36px; min-height: 32px; padding: 0 4px; border: 1px solid var(--border);
  border-radius: 6px; text-decoration: none; font-variant-numeric: tabular-nums;
}
.race-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 260px), 1fr)); gap: 6px 28px; }
.race { margin: 0 0 18px; scroll-margin-top: 16px; min-width: 0; }
.race h3 { margin: 0 0 4px; font-size: 17px; }
.race .holder, .race .vote-for { font-size: 14px; color: var(--slate); margin: 0 0 6px; }
.cands { list-style: none; padding: 0; margin: 0; }
.cands li {
  display: flex; justify-content: space-between; align-items: baseline; gap: 12px;
  padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 15px;
}
.cands li.none { color: var(--slate); }
.cands .nm { min-width: 0; overflow-wrap: anywhere; }
.cands .ballot-no { color: var(--slate); font-variant-numeric: tabular-nums; margin-right: 6px; }
.cands .st { font-size: 13.5px; color: var(--slate); white-space: nowrap; }
.cands .st-challenged { color: var(--ink); font-weight: 600; }
.status-key { margin: 8px 0 0; padding-left: 20px; font-size: 15px; }
.status-key li { margin: 0 0 6px; }
"""


def build_page(data, roster, worksheet, metros):
    brand = worksheet["brand"]
    app_name = brand["app_name"]
    check_layer(worksheet, "ward", PAGE_FILE)
    election = datetime.date.fromisoformat(data["electionDate"])
    as_of = datetime.datetime.fromisoformat(data["listAsOf"])
    certify_by = election - datetime.timedelta(days=CERTIFY_DAYS)
    year = election.year
    when = long_date(election)
    weekday = election.strftime("%A")

    contests = data["contests"]
    by_kind = {}
    for c in contests:
        by_kind.setdefault(c["kind"], []).append(c)
    people = [p for c in contests for p in c["candidates"]]
    challenged = sum(1 for p in people if p["status"] == "Challenged")
    n_ward = sum(len(c["candidates"]) for c in by_kind["ward"])
    n_police = len(by_kind["police-council"])

    # "4:01 p.m. on November 9, 2026": the time first, so no sentence ends on
    # "p.m." and its own full stop.
    stamp = "%s on %s" % (clock(as_of), long_date(as_of.date()))
    listed = "as of " + stamp
    # NOTHING HERE READS TODAY'S DATE. A sentence that changed when a deadline
    # passed would turn --check red on every pull request that day with no
    # change to the list, so each status sentence stays true on any date while
    # the list it describes is the current one.
    if challenged:
        status_html = (
            '<p class="cand-status"><strong>%d of them are marked Challenged</strong>: '
            'someone has filed an objection to their nominating petitions, and the Board '
            'decides each objection before it certifies the ballot, which it must do by '
            '%s. This page follows the Board\'s list as it changes.</p>'
            % (challenged, esc(long_date(certify_by))))
        lede_word = "Filed, objections pending"
    else:
        status_html = (
            '<p class="cand-status">No objection is pending on this list. The Board must '
            'certify the ballot by %s, and a candidate may withdraw until then. This page '
            'follows the Board\'s list as it changes.</p>' % esc(long_date(certify_by)))
        lede_word = "Filed"

    lede_html = (
        '<p class="lede"><strong>%s.</strong> These are the %d people who filed to run in '
        'Chicago\'s municipal election on %s, %s: for mayor, clerk and treasurer, for '
        'alderperson in each of the 50 wards, and for the %d police district councils. '
        'The list is the Chicago Board of Election Commissioners\' own, %s.</p>\n    %s'
        % (esc(lede_word), len(people), esc(weekday), esc(when), n_police, esc(listed),
           status_html))
    lede = dict(
        html=lede_html,
        cta='    <a class="cta" href="./#layers=ward&amp;frame=chicago">Find your ward →</a>\n'
            '    <p class="cta-note">Opens the map with Chicago\'s wards on. The ward card '
            'names your alderperson and links back to your ward\'s candidates here.</p>')

    citywide = "".join(race_html(c, c["office"], c["kind"])
                       for c in sorted(by_kind["mayor"] + by_kind["clerk"] + by_kind["treasurer"],
                                       key=lambda c: ("mayor", "clerk", "treasurer").index(c["kind"])))
    wards = sorted(by_kind["ward"], key=lambda c: c["district"])
    jump = "\n".join('      <li><a href="#ward-%d">%d</a></li>' % (c["district"], c["district"])
                     for c in wards)
    ward_blocks = "".join(
        race_html(c, "Ward %d" % c["district"], "ward-%d" % c["district"],
                  holder=(roster.get(str(c["district"])) or {}).get("name"))
        for c in wards)
    police = sorted(by_kind["police-council"], key=lambda c: c["district"])
    police_blocks = "".join(
        race_html(c, "%s District council" % ordinal(c["district"]),
                  "police-district-%d" % c["district"])
        for c in police)
    key_html = "\n".join('      <li><strong>%s</strong>: %s</li>' % (esc(k), esc(v))
                         for k, v in STATUS_KEY.items())

    sections = """  <section id="citywide">
    <h2>Mayor, clerk and treasurer</h2>
    <p>Every Chicago voter's ballot carries these three races.</p>
    <div class="race-grid">
%(citywide)s    </div>
  </section>

  <section id="wards">
    <h2>Alderperson, ward by ward</h2>
    <p>Each of the 50 wards elects one alderperson to the City Council; %(n_ward)d people filed
      across them. Don't know your ward? <a href="ward.html">Look it up by address</a>. Jump to
      a ward:</p>
    <ul class="cand-jump">
%(jump)s
    </ul>
    <div class="race-grid">
%(wards)s    </div>
  </section>

  <section id="police-councils">
    <h2>Police district councils</h2>
    <p>Each of Chicago's %(n_police)d police districts elects a council of three, and a voter picks
      up to three candidates in their own district's race. Your police district is not your ward:
      <a href="police-district.html">look up your police district</a>.</p>
    <div class="race-grid">
%(police)s    </div>
  </section>

  <section id="about-list">
    <h2>About this list</h2>
    <p>The names, their order and each status are the Chicago Board of Election Commissioners',
      from its <a href="%(src)s">candidate list</a> %(listed)s, linked from its
      <a href="%(page)s">Candidates page</a>. The Board titles the list "in ballot order".
      Names are printed in capitals, as the Board prints them. The Board's list also gives each
      candidate's home address; this page leaves it out.</p>
    <p>What each status means:</p>
    <ul class="status-key">
%(key)s
    </ul>
    <p>The Board must certify the names that go on the ballot by %(certify)s, 68 days before the
      election (%(statute)s).</p>
    <div class="disclaimer">
      <strong>Not the official ballot.</strong> This is the Board's list as it stood at %(stamp)s.
      Names can come off it before the ballot is certified. For the official list, ask the
      Chicago Board of Election Commissioners.
    </div>
  </section>
""" % dict(citywide=citywide, n_ward=n_ward, jump=jump, wards=ward_blocks,
           n_police=n_police, police=police_blocks, src=esc(data["sourceUrl"]),
           page=esc(data["sourcePage"]), listed=esc(listed), stamp=esc(stamp), key=key_html,
           certify=esc(long_date(certify_by)), statute=esc(CERTIFY_STATUTE))

    related = "\n".join([
        '      <li><a href="ward.html">Who is my alderman?</a><span>Your Chicago ward by address, '
        'and who represents it now.</span></li>',
        '      <li><a href="police-district.html">What police district am I in?</a><span>Your '
        'police district and beat, the nearest station, and your Police District '
        'Council.</span></li>',
        '      <li><a href="precinct.html">What precinct am I in?</a><span>Your voting precinct '
        'and polling place.</span></li>',
        '      <li><a href="election-results.html">How did my area vote?</a><span>The latest '
        'election results, race by race, precinct by precinct.</span></li>',
    ])

    # The search result's title and the page's heading differ on purpose: the
    # shell adds " — districtry Illinois" to the title, and
    # validate_serp_lengths.py holds the whole to 60 characters, which the
    # question a reader types does not fit beside the city and the year.
    title = "Chicago %d candidates by ward" % year
    heading = "Who is running in my Chicago ward?"
    subtitle = ("Everyone who filed for Chicago's %s election: mayor, clerk, treasurer, all "
                "50 wards and the police district councils." % when)
    desc = ("Who filed to run in Chicago's %s election: mayor, all 50 wards and the "
            "police district councils, as the Board of Elections lists them." % when)
    page_path = os.path.join(REPO_ROOT, TAG, PAGE_FILE)
    text = head(TAG, brand, app_name, PAGE_FILE, title, desc, desc)
    text += shell(app_name, heading, subtitle, lede, sections, related,
                  preserved_from_disk(page_path),
                  shared_head_block(TAG, THEMEBOOT_RE, "theme boot script"),
                  shared_head_block(TAG, MARK_RE, "districtry mark"), TAG,
                  extra_css=PAGE_CSS)
    return page_path, text, people


def check_app(data):
    """The ward card's date and the data file's election date must agree."""
    with open(os.path.join(REPO_ROOT, APP), encoding="utf-8") as f:
        dates = APP_DATE_RE.findall(f.read())
    if len(dates) != 1:
        raise PageError("%s: expected one CHICAGO_CANDIDATES_ELECTION date, found %d"
                        % (APP, len(dates)))
    if dates[0] != data["electionDate"]:
        raise PageError("%s links the candidates of the %s election while %s holds the %s "
                        "election's; set CHICAGO_CANDIDATES_ELECTION to the file's date"
                        % (APP, dates[0], DATA, data["electionDate"]))


def check_workflow():
    """The refresh that rewrites the data file must rebuild and commit the page."""
    path = os.path.join(REPO_ROOT, WORKFLOW)
    if not os.path.exists(path):
        raise PageError("%s is missing; nothing refreshes %s" % (WORKFLOW, DATA))
    with open(path, encoding="utf-8") as f:
        wf = f.read()
    for needle in ("build_chicago_candidates.py", "build_candidates_page.py",
                   "build_sitemap.py", "il/chicago-candidates.html", DATA.replace(os.sep, "/")):
        if needle not in wf:
            raise PageError("%s no longer mentions %s, so a refresh could ship a list the "
                            "page contradicts" % (WORKFLOW, needle))


def run(args):
    data = load(DATA)
    roster = load(ROSTER)
    worksheet = load("metro-worksheet.json")   # Illinois keeps its worksheet at the root
    metros = load("metros.json")
    check_app(data)
    check_workflow()
    path, text, people = build_page(data, roster, worksheet, metros)
    # Read the page BACK for every name: byte-equality alone would pass a correct
    # template that printed nobody.
    for p in people:
        if esc(p["name"]) not in text:
            raise PageError("%s is not on the page" % p["name"])
    rel = os.path.relpath(path, REPO_ROOT)
    if args.check:
        current = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        if current != text:
            diff = "".join(list(difflib.unified_diff(
                current.splitlines(True), text.splitlines(True), rel, rel + " (generated)"))[:40])
            print(diff, file=sys.stderr)
            raise PageError("%s is out of date; run python3 scripts/build_candidates_page.py"
                            % rel)
        print("OK %s matches %s (%d candidates)" % (rel, DATA, len(people)))
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("wrote %s (%d candidates)" % (rel, len(people)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    try:
        run(args)
    except PageError as e:
        print("build-candidates-page: FAIL — %s" % e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
