#!/usr/bin/env python3
"""
Tell readers, before an election, what districtry will do with its results.

Adam, 2026-11-15: "Most of my traffic came in the lead up to the midterms. I
want visitors to know I'll have election results after, in the lead up to the
election." Until that day nothing on the site said results would be posted: a
reader who came in October to look up a district had no reason to come back in
November.

ONE FILE PER STATE SAYS WHAT IS COMING, AND THIS SCRIPT OWNS EVERY WORD ABOUT IT.
`<tag>/data/source/election-calendar.json` lists each regularly scheduled
election an app tells its readers about: the date, the place, what is on the
ballot, the office that publishes the results, that office's own results page,
and which of three wordings applies (`kind`):

    posted    "results will be posted here". Allowed only where this app has
              already posted THIS OFFICE'S results from a real election; the
              check reads the app's shipped results file for the office's name.
    plans     "districtry plans to post results here". The office publishes a
              file a program may read and it has not been used in a real
              election yet. The office's own page is linked beside it.
    official  "districtry cannot post results for this election", why, and a
              link to the office's own page.

Moving a place from one wording to another is one edit to `kind`. The wording
never says "election night": results refresh on a schedule, so every sentence
says "as the office publishes them".

WHERE THE NOTICE APPEARS, and who writes each place:

    the Next election box on <tag>/election-results.html
                                   scripts/build_results_pages.py, results_box()
    the closing line on a candidates page
                                   scripts/build_candidates_page.py, candidates_closing()
    the front page's dated line and its results tile
                                   scripts/build_landing_page.py, landing_line()
                                   and landing_tile_note()
    the line in the map's Elections section, and the closing line on a polling
    place card                     THIS script, as the `election-calendar`
                                   GENERATED region of <tag>/index.html, which
                                   engine block `next-election` reads
    the calendar reminder          THIS script, <tag>/calendar/<id>.ics

NOTHING HERE READS TODAY'S DATE. A page whose words changed when a date passed
would turn every `--check` red that morning with no change to the tree, so each
place is written once and a small script in the page shows it by the READER'S
clock, in the election's own time zone: the box and the map's line while the
election is ahead, the front page's line in the 60 days before it. With no
script a page shows none of it, which is what it showed before.

THE BOX OUTLIVES ELECTION DAY BY A WEEK, ON PURPOSE. The evening of an election
is when a reader most needs to be told the results are not on the page yet, so
the box stays, headed "Results not posted yet", until build_results_pages.py
finds the results file has moved on to that election and stops writing it, or
for GRACE_DAYS if that never happens. The map's line has no such second state
and goes at the end of election day.

THE REMINDER COLLECTS NOTHING. It is a calendar file on this site for the day
after the election, linking back to the results page; a reader's calendar app
opens it and nothing is sent anywhere. Its link carries ref=reminder, which the
traffic report reads as the referrer of that later visit, so whether reminders
bring anyone back can be seen without counting who saved one.

TWO LINKS DEPEND ON OTHER FILES, IN DIFFERENT WAYS. A candidates link is
written whenever the calendar names a candidates page, and the check FAILS when
that page's list is for an earlier election; the link is shown only until the
end of election day, so a list that moves on to a later election afterwards
changes nothing here. A polling place link is written only once the polling
list is for this election, so the workflow that refreshes that list must run
this script and commit the app, which the check holds it to.

    python3 scripts/build_election_notices.py             # write
    python3 scripts/build_election_notices.py --check     # the CI gate
    python3 scripts/build_election_notices.py --selftest  # the three wordings
"""

import argparse
import datetime
import glob
import html
import json
import os
import re
import sys

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOWS = os.path.join(REPO_ROOT, ".github", "workflows")
CALENDAR = os.path.join("data", "source", "election-calendar.json")
RESULTS_INDEX = os.path.join("data", "app", "election-results.json")
RESULTS_PAGE = "election-results.html"
REMINDER_DIR = "calendar"
REGION = "election-calendar"
REGION_BEGIN = "  /* ==== GENERATED:BEGIN %s ==== */" % REGION
REGION_END = "  /* ==== GENERATED:END %s ==== */" % REGION
KINDS = ("posted", "plans", "official")
FRONT_PAGE_DAYS = 60   # the front page names an election for this long before it
GRACE_DAYS = 7         # the results page's box stays this long after election day
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ENTRY_KEYS = {"id", "date", "place", "election", "ballot", "area", "office", "officeShort",
              "officialResults", "kind", "why", "frontPage", "candidates", "polling",
              "dateSource", "checked"}


class NoticeError(Exception):
    pass


def esc(s):
    return html.escape(str(s), quote=True)


def site_host():
    with open(os.path.join(REPO_ROOT, "CNAME"), encoding="utf-8") as f:
        host = f.read().strip()
    if not re.match(r"^[a-z0-9.-]+$", host):
        raise NoticeError("CNAME does not hold a host name")
    return host


# ---------------------------------------------------------------- the calendar

def calendar_tags():
    return [os.path.relpath(p, REPO_ROOT).split(os.sep)[0]
            for p in sorted(glob.glob(os.path.join(REPO_ROOT, "*", CALENDAR)))]


def _read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def results_publishers(tag):
    """Every office whose results this app's shipped results file holds: the
    witness that a "posted" promise is about an office already read in a real
    election."""
    out = set()
    path = os.path.join(REPO_ROOT, tag, RESULTS_INDEX)
    if not os.path.exists(path):
        return out
    idx = _read_json(path)
    for s in idx.get("sources") or []:
        if s.get("publisher"):
            out.add(str(s["publisher"]))
    app = os.path.join(REPO_ROOT, tag, "index.html")
    with open(app, encoding="utf-8") as f:
        text = f.read()
    i = text.find("registerElectionResultsLayer({")
    if i >= 0:
        m = re.search(r"\bpublisher:\s*\"((?:[^\"\\]|\\.)*)\"", text[i:i + 4000])
        if m:
            out.add(json.loads('"%s"' % m.group(1)))
    return out


def _https(url):
    return isinstance(url, str) and re.match(r"^https://[^\s\"'<>]+$", url) is not None


def validate(tag, cal, where, publishers=None, files=True):
    """Every rule a calendar is held to. `files` False skips the rules that
    read the tree, for the selftest's fixtures."""
    def bad(msg):
        raise NoticeError("%s: %s" % (where, msg))

    if not isinstance(cal, dict) or not isinstance(cal.get("elections"), list):
        bad("must be an object with an `elections` list")
    tz = cal.get("timeZone")
    if not isinstance(tz, str) or not tz:
        bad("names no timeZone")
    if ZoneInfo:
        try:
            ZoneInfo(tz)
        except Exception:
            bad("timeZone %r is not a time zone this system knows" % tz)
    seen = set()
    for e in cal["elections"]:
        if not isinstance(e, dict):
            bad("an election is not an object")
        eid = e.get("id")
        if not isinstance(eid, str) or not ID_RE.match(eid):
            bad("an election's id %r is not lowercase words joined by hyphens" % (eid,))
        if eid in seen:
            bad("two elections share the id %s" % eid)
        seen.add(eid)

        def ebad(msg, eid=eid):
            bad("%s: %s" % (eid, msg))

        unknown = sorted(set(e) - ENTRY_KEYS)
        if unknown:
            ebad("unknown key(s) %s" % ", ".join(unknown))
        for key in ("date", "checked"):
            v = e.get(key)
            if not isinstance(v, str) or not DATE_RE.match(v):
                ebad("%s must be a YYYY-MM-DD date" % key)
            try:
                datetime.date.fromisoformat(v)
            except ValueError:
                ebad("%s %r is not a real date" % (key, v))
        for key in ("place", "election", "ballot", "area", "office"):
            v = e.get(key)
            if not isinstance(v, str) or not v.strip() or v != v.strip():
                ebad("%s must be a non-empty string with no space at either end" % key)
        if not ID_RE.match(e["area"]):
            ebad("area %r is not lowercase words joined by hyphens" % e["area"])
        if e["ballot"].endswith("."):
            ebad("ballot is the middle of a sentence and must not end in a full stop")
        if e.get("kind") not in KINDS:
            ebad("kind must be one of %s" % ", ".join(KINDS))
        for key in ("officialResults", "dateSource"):
            if not _https(e.get(key)):
                ebad("%s must be an https address" % key)
        if e["kind"] in ("posted", "plans"):
            short = e.get("officeShort")
            if not isinstance(short, str) or not short.strip():
                ebad("a %r election needs officeShort, the words the certifying office "
                     "is called the second time (\"the Board\")" % e["kind"])
            if "why" in e:
                ebad("`why` is only for kind \"official\"")
        else:
            why = e.get("why")
            if not isinstance(why, str) or not why.strip().endswith("."):
                ebad("an \"official\" election needs `why`: one sentence, ending in a full "
                     "stop, saying why districtry cannot post its results")
        if not isinstance(e.get("frontPage", False), bool):
            ebad("frontPage must be true or false")
        if e["kind"] == "posted" and publishers is not None and e["office"] not in publishers:
            ebad("kind \"posted\" promises results from the %s, and %s/%s holds no results "
                 "from an office of that name (it holds: %s). The full promise is only for "
                 "an office this app has already posted results from; use \"plans\""
                 % (e["office"], tag, RESULTS_INDEX.replace(os.sep, "/"),
                    ", ".join(sorted(publishers)) or "none"))
        if files and e["kind"] in ("posted", "plans") and not has_results_page(tag):
            ebad("kind %r says the results will be on this app's election results page, "
                 "and %s/%s does not exist" % (e["kind"], tag, RESULTS_PAGE))
        cand = e.get("candidates")
        if cand is not None:
            if not isinstance(cand, dict) or set(cand) != {"page", "data"}:
                ebad("candidates must be {page, data}")
            if files:
                if not os.path.exists(os.path.join(REPO_ROOT, tag, cand["page"])):
                    ebad("candidates.page %s/%s does not exist" % (tag, cand["page"]))
                dpath = os.path.join(REPO_ROOT, tag, cand["data"])
                if not os.path.exists(dpath):
                    ebad("candidates.data %s/%s does not exist" % (tag, cand["data"]))
                listed = str(_read_json(dpath).get("electionDate") or "")
                if not DATE_RE.match(listed):
                    ebad("candidates.data names no electionDate")
                if listed < e["date"]:
                    ebad("the candidates page lists the election of %s, which is before "
                         "this one. Drop `candidates` until its own list is published"
                         % listed)
        poll = e.get("polling")
        if poll is not None:
            if not isinstance(poll, dict) or set(poll) != {"layers", "list"} or \
                    not isinstance(poll["layers"], list) or not poll["layers"]:
                ebad("polling must be {layers: [layer ids, parent first], list}")
            if files:
                if not os.path.exists(os.path.join(REPO_ROOT, tag, poll["list"])):
                    ebad("polling.list %s/%s does not exist" % (tag, poll["list"]))
                own = os.path.join(REPO_ROOT, tag, "metro-worksheet.json")
                ws = _read_json(own if os.path.exists(own)
                                else os.path.join(REPO_ROOT, "metro-worksheet.json"))
                ids = {l["id"] for l in ws["layers"]}
                missing = [l for l in poll["layers"] if l not in ids]
                if missing:
                    ebad("polling.layers names %s, which this app does not register"
                         % ", ".join(missing))
    return cal


_CACHE = {}


def load(tag):
    """One instance's validated calendar, or None when it has none."""
    if tag in _CACHE:
        return _CACHE[tag]
    path = os.path.join(REPO_ROOT, tag, CALENDAR)
    cal = None
    if os.path.exists(path):
        cal = validate(tag, _read_json(path), "%s/%s" % (tag, CALENDAR.replace(os.sep, "/")),
                       publishers=results_publishers(tag))
        cal["elections"].sort(key=lambda e: (e["date"], e["id"]))
    _CACHE[tag] = cal
    return cal


# ---------------------------------------------------------------- the words

def _date(e):
    return datetime.date.fromisoformat(e["date"])


def when(e):
    """"Tuesday, February 23, 2027"."""
    d = _date(e)
    return "%s, %s %d, %d" % (d.strftime("%A"), d.strftime("%B"), d.day, d.year)


def short_when(e):
    """"February 23, 2027"."""
    d = _date(e)
    return "%s %d, %d" % (d.strftime("%B"), d.day, d.year)


def title(e):
    """"Chicago municipal election"."""
    return "%s %s" % (e["place"], e["election"])


def after_label(e):
    """What the box is headed once election day has passed and the results
    are not on the page."""
    return "Official results" if e["kind"] == "official" else "Results not posted yet"


def has_results_page(tag):
    return os.path.exists(os.path.join(REPO_ROOT, tag, RESULTS_PAGE))


def sentence(e, where, results_href=None):
    """The notice's own sentence, for one of five places.

    page    the results page itself (HTML)
    site    another page of this site, which links the results page (HTML)
    front   the front page's line, which also names the day (HTML)
    map     the line in the map's Elections section (plain text)
    card    the closing line of a card about this election (plain text)
    """
    office = e["office"]
    place = e["place"]
    kind = e["kind"]
    official = '<a href="%s">the %s\'s own page</a>' % (esc(e["officialResults"]), esc(office))
    link = (lambda words: '<a href="%s">%s</a>' % (esc(results_href), esc(words))
            if results_href else esc(words))
    day = "<strong>%s's %s is %s.</strong> " % (esc(place), esc(e["election"]), esc(when(e)))
    if kind == "posted":
        certify = " They stay marked unofficial until %s certifies them." % e["officeShort"]
        if where == "page":
            return esc("After the polls close on %s, precinct results for %s's %s will be "
                       "posted on this page as the %s publishes them.%s"
                       % (when(e), place, e["election"], office, certify))
        if where == "site":
            return ("After the polls close on %s, precinct results for this election will "
                    "be posted on %s as the %s publishes them.%s"
                    % (esc(when(e)), link("districtry's election results page"),
                       esc(office), esc(certify)))
        if where == "front":
            return (day + "After the polls close, precinct results will be posted on %s as "
                    "the %s publishes them."
                    % (link("districtry's results page for %s" % place), esc(office)))
        if where == "map":
            return ("After the polls close, precinct results will be posted here as the %s "
                    "publishes them." % office)
        if where == "card":
            return ("After the polls close, precinct results for this election will be "
                    "posted on districtry as the %s publishes them." % office)
    elif kind == "plans":
        if where == "page":
            return (esc("districtry plans to post precinct results for %s's %s on this page "
                        "after the polls close on %s, as the %s publishes them. It has not "
                        "posted this office's results from a real election before."
                        % (place, e["election"], when(e), office))
                    + " Official results will be on %s." % official)
        if where == "site":
            return ("districtry plans to post precinct results for this election on %s after "
                    "the polls close on %s, as the %s publishes them. Official results will "
                    "be on %s."
                    % (link("its election results page"), esc(when(e)),
                       esc(office), official))
        if where == "front":
            return (day + "districtry plans to post precinct results on %s after the polls "
                    "close, as the %s publishes them."
                    % (link("its results page for %s" % place), esc(office)))
        if where == "map":
            return ("districtry plans to post precinct results here after the polls close, "
                    "as the %s publishes them." % office)
        if where == "card":
            return ("districtry plans to post precinct results for this election after the "
                    "polls close, as the %s publishes them." % office)
    else:
        if where in ("page", "site"):
            return (esc("districtry cannot post results for this election. %s" % e["why"])
                    + " Official results will be on %s." % official)
        if where == "front":
            return day + "Official results will be on %s." % official
        if where in ("map", "card"):
            return ("districtry cannot post results for this election. Official results "
                    "will be on the %s's own page." % office)
    raise NoticeError("no wording for kind %r in place %r" % (kind, where))


# ---------------------------------------------------------------- the page script

def reveal_script(root_expr, indent="    "):
    """The script that shows a notice by the reader's clock. `root_expr` is
    the element to look in: one carrying data-election-notice, or an ancestor
    of several. Each item inside carries data-date, data-until and data-tz,
    and optionally data-from; an element with data-after takes that text once
    election day has passed, and one with data-before goes then."""
    lines = [
        "<script>",
        "/* Shows an election notice while it applies, by the reader's own clock in the",
        "   election's time zone (scripts/build_election_notices.py). The page is the",
        "   same file every day, so nothing in it was written from today's date. */",
        "(function (root) {",
        "  if (!root || !root.querySelectorAll) return;",
        "  var boxes = root.hasAttribute(\"data-election-notice\") ? [root] :",
        "    root.querySelectorAll(\"[data-election-notice]\");",
        "  for (var b = 0; b < boxes.length; b++) {",
        "    var box = boxes[b], items = box.querySelectorAll(\"[data-date]\"), shown = 0;",
        "    for (var i = 0; i < items.length; i++) {",
        "      if (shown && box.getAttribute(\"data-election-notice\") === \"first\") break;",
        "      var it = items[i], now = new Date(), today = \"\";",
        "      try { today = now.toLocaleDateString(\"en-CA\", { timeZone: it.getAttribute(\"data-tz\") }); }",
        "      catch (e) { today = \"\"; }",
        "      if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(today)) {",
        "        today = now.getFullYear() + \"-\" + (\"0\" + (now.getMonth() + 1)).slice(-2) + \"-\" +",
        "          (\"0\" + now.getDate()).slice(-2);",
        "      }",
        "      var from = it.getAttribute(\"data-from\");",
        "      if ((from && today < from) || today > it.getAttribute(\"data-until\")) continue;",
        "      if (today > it.getAttribute(\"data-date\")) {",
        "        var late = it.querySelectorAll(\"[data-after]\");",
        "        for (var j = 0; j < late.length; j++) late[j].textContent = late[j].getAttribute(\"data-after\");",
        "        var gone = it.querySelectorAll(\"[data-before]\");",
        "        for (var k = 0; k < gone.length; k++) gone[k].hidden = true;",
        "      }",
        "      it.hidden = false;",
        "      shown++;",
        "    }",
        "    if (shown) box.hidden = false;",
        "  }",
        "})(%s);" % root_expr,
        "</script>",
    ]
    return "\n".join(indent + l for l in lines) + "\n"


def _item_attrs(e, tz, until, start=None):
    out = 'data-date="%s" data-until="%s" data-tz="%s"' % (e["date"], until, esc(tz))
    if start:
        out = 'data-from="%s" ' % start + out
    return out


def _plus(e, days):
    return (_date(e) + datetime.timedelta(days=days)).isoformat()


# ---------------------------------------------------------------- the results page

BOX_CSS = """/* The Next election box (scripts/build_election_notices.py). It ships hidden
   and the script after it shows it while an election is ahead. */
.next-election { margin: 0 0 22px; }
.next-election-item + .next-election-item {
  margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--line);
}
.next-election-label {
  margin: 0 0 4px; font-size: 13.5px; font-weight: 600; color: var(--accent-deep);
}
.next-election-what { margin: 0 0 8px; font-size: 18px; line-height: 1.3; }
.next-election p { margin: 0 0 8px; }
/* a row of links, so each is a box at least 24px tall (WCAG 2.5.8). Only a
   link still shown takes the box: a bare display rule here would outrank the
   browser's own rule for the hidden attribute, and the candidates link is
   hidden once election day has passed. */
.next-election-links a:not([hidden]) { display: inline-block; padding: 4px 0; margin-right: 20px; font-weight: 600; }
.next-election-small { font-size: 14px; color: var(--slate); }
.next-election p:last-child { margin-bottom: 0; }
"""


def results_box(tag, results_date):
    """The Next election box for <tag>/election-results.html, or "" when the
    calendar holds nothing the page's own results are not already for.
    `results_date` is the election the page's results are from."""
    cal = load(tag)
    if not cal:
        return ""
    items = []
    for e in cal["elections"]:
        if results_date and e["date"] <= str(results_date):
            continue  # the page's results are this election's, or a later one's
        links = []
        if e.get("candidates"):
            links.append('<a href="%s" data-before>Who is running</a>'
                         % esc(e["candidates"]["page"]))
        links.append('<a href="%s/%s.ics">Add a reminder to my calendar</a>'
                     % (REMINDER_DIR, e["id"]))
        day_after = _date(e) + datetime.timedelta(days=1)
        items.append(
            '      <div class="next-election-item" %(attrs)s hidden>\n'
            '        <p class="next-election-label" data-after="%(after)s">Next election</p>\n'
            '        <p class="next-election-what"><strong>%(title)s</strong>, %(when)s</p>\n'
            '        <p>On the ballot: %(ballot)s.</p>\n'
            '        <p>%(sentence)s</p>\n'
            '        <p class="next-election-links">%(links)s</p>\n'
            '        <p class="next-election-small">The reminder is a calendar entry for '
            '%(day_after)s, the day after the election, that links back to this page. '
            'Saving it sends nothing to districtry.</p>\n'
            '      </div>\n'
            % dict(attrs=_item_attrs(e, cal["timeZone"], _plus(e, GRACE_DAYS)),
                   after=esc(after_label(e)), title=esc(title(e)), when=esc(when(e)),
                   ballot=esc(e["ballot"]), sentence=sentence(e, "page"),
                   links="".join(links),
                   day_after=esc("%s %d" % (day_after.strftime("%B"), day_after.day))))
    if not items:
        return ""
    return ('<aside class="answer-card next-election" id="next-election" '
            'aria-label="Next election" data-election-notice hidden>\n%s    </aside>\n%s    '
            % ("".join(items), reveal_script("document.currentScript.previousElementSibling")))


# ---------------------------------------------------------------- the candidates page

def candidates_closing(tag, page, election_date):
    """The closing paragraph of a candidates page about one election: what
    happens to that election's results. "" when the calendar names no such
    election for this page. Its words are true on any day before the results
    are posted, so no script shows or hides it."""
    cal = load(tag)
    if not cal:
        return ""
    for e in cal["elections"]:
        if e["date"] == str(election_date) and (e.get("candidates") or {}).get("page") == page:
            return sentence(e, "site", RESULTS_PAGE if has_results_page(tag) else None)
    return ""


# ---------------------------------------------------------------- the front page

def _front_entries():
    out = []
    for tag in calendar_tags():
        cal = load(tag)
        for e in cal["elections"]:
            out.append((e["date"], tag, e["id"], e, cal["timeZone"]))
    out.sort(key=lambda t: t[:3])
    return [(tag, e, tz) for _, tag, _, e, tz in out]


def _front_href(tag, e):
    return "/%s/%s" % (tag, RESULTS_PAGE) if has_results_page(tag) else None


def landing_line():
    """The front page's dated line, under the address box: every election
    marked frontPage, each shown for FRONT_PAGE_DAYS before its day. "" when
    no calendar marks one."""
    items = []
    for tag, e, tz in _front_entries():
        if not e.get("frontPage"):
            continue
        items.append('          <span class="election-line-item" %s hidden>%s</span>\n'
                     % (_item_attrs(e, tz, e["date"], _plus(e, -FRONT_PAGE_DAYS)),
                        sentence(e, "front", _front_href(tag, e))))
    if not items:
        return ""
    return ('        <p class="election-line" id="election-line" data-election-notice hidden>\n'
            '%s        </p>\n%s'
            % ("".join(items),
               reveal_script("document.currentScript.previousElementSibling", "        ")))


def landing_tile_note():
    """What the "How did my area vote?" tile adds while an election is ahead:
    the soonest one a calendar names. Shown by the script landing_tile_script
    returns. "" when no calendar names one."""
    items = []
    for tag, e, tz in _front_entries():
        items.append('<span %s hidden>Next: %s, %s</span>'
                     % (_item_attrs(e, tz, e["date"]), esc(e["place"]), esc(short_when(e))))
    if not items:
        return ""
    # the middle dot is inside the hidden span, so the tile's count reads as
    # it always has when nothing is ahead
    return ('<span class="ask-next" data-election-notice="first" hidden> &#183; %s</span>'
            % "".join(items))


def landing_tile_script(root_expr):
    return reveal_script(root_expr) if landing_tile_note() else ""


# ---------------------------------------------------------------- the app

def app_calendar(tag):
    """ELECTION_CALENDAR for one app: each election with its words already
    written, so engine block next-election writes none of its own."""
    cal = load(tag)
    out = []
    for e in cal["elections"]:
        links = []
        if e.get("candidates"):
            links.append({"what": "candidates", "label": "Who is running",
                          "href": e["candidates"]["page"]})
        poll = e.get("polling")
        if poll:
            listed = str(_read_json(os.path.join(REPO_ROOT, tag, poll["list"]))
                         .get("electionDate") or "")
            if listed == e["date"]:
                links.append({"what": "polling", "label": "Where you vote",
                              "layers": list(poll["layers"])})
        if e["kind"] != "posted":
            links.append({"what": "official", "label": "Official results page",
                          "href": e["officialResults"]})
        links.append({"what": "reminder", "label": "Add a reminder to my calendar",
                      "href": "%s/%s.ics" % (REMINDER_DIR, e["id"]), "file": True})
        if e["kind"] != "official" and has_results_page(tag):
            closing = {"label": "Election results page", "href": RESULTS_PAGE}
        else:
            closing = {"label": "Official results page", "href": e["officialResults"]}
        closing["title"] = "Results"
        closing["note"] = sentence(e, "card")
        out.append({"id": e["id"], "date": e["date"], "timeZone": cal["timeZone"],
                    "area": e["area"], "title": title(e), "when": when(e),
                    "text": sentence(e, "map"), "links": links, "closing": closing})
    return out


def app_region(tag):
    body = json.dumps(app_calendar(tag), indent=2, ensure_ascii=False)
    body = body.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029").replace("</", "<\\/")
    lines = [
        REGION_BEGIN,
        "  // The elections this app names before they happen, each with its words",
        "  // already written (engine next-election reads it). GENERATED by",
        "  // scripts/build_election_notices.py from %s/%s:" % (tag, CALENDAR.replace(os.sep, "/")),
        "  // edit that file and run the script, never this region.",
        "  var ELECTION_CALENDAR = " + body.replace("\n", "\n  ") + ";",
        REGION_END,
    ]
    return "\n".join(lines)


def put_app_region(tag, text):
    path = "%s/index.html" % tag
    b, e = text.find(REGION_BEGIN + "\n"), text.find(REGION_END)
    if b < 0 or e < b:
        raise NoticeError("%s carries no %s region. An app with an election calendar needs "
                          "the two marker lines, followed by its registerNextElection call"
                          % (path, REGION))
    return text[:b] + app_region(tag) + text[e + len(REGION_END):]


def registered_areas(text, path):
    m = re.search(r"\bregisterNextElection\(\{\s*calendar:\s*ELECTION_CALENDAR\s*,"
                  r"\s*areas:\s*\{([^}]*)\}\s*\}\);", text)
    if not m:
        raise NoticeError("%s has an election calendar and makes no call of the shape "
                          "registerNextElection({ calendar: ELECTION_CALENDAR, areas: { ... } });"
                          % path)
    return set(re.findall(r"(?:^|,)\s*\"?([a-z0-9-]+)\"?\s*:", m.group(1)))


# ---------------------------------------------------------------- the reminder

def _ics_text(s):
    return (str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\r\n", "\\n").replace("\n", "\\n"))


def _fold(line):
    """RFC 5545 3.1: no line longer than 75 octets; a continuation begins
    with one space. Never splits a UTF-8 character."""
    out, cur = [], b""
    limit = 75
    for ch in line:
        enc = ch.encode("utf-8")
        if len(cur) + len(enc) > limit:
            out.append(cur)
            cur = b" "
            limit = 75
        cur += enc
    out.append(cur)
    return b"\r\n".join(out)


def reminder_ics(tag, e, host):
    """The calendar file for one election: an all-day entry on the day after
    it. Every byte is fixed by the calendar entry (DTSTAMP is the day the
    entry was last checked), so the file is the same on every build."""
    day = _date(e) + datetime.timedelta(days=1)
    # ref=reminder: the traffic report reads it as the later visit's referrer
    if has_results_page(tag):
        url = "https://%s/%s/%s?ref=reminder" % (host, tag, RESULTS_PAGE)
    else:
        url = e["officialResults"]
    if e["kind"] == "posted":
        summary = "%s election results on districtry" % e["place"]
        text = ("Precinct results for %s's %s of %s are posted on districtry as the %s "
                "publishes them. They stay marked unofficial until %s certifies them."
                % (e["place"], e["election"], short_when(e), e["office"], e["officeShort"]))
    elif e["kind"] == "plans":
        summary = "%s election results" % e["place"]
        text = ("districtry plans to post precinct results for %s's %s of %s as the %s "
                "publishes them. Official results: %s"
                % (e["place"], e["election"], short_when(e), e["office"], e["officialResults"]))
    else:
        summary = "%s election results" % e["place"]
        text = ("Official results for %s's %s of %s are on the %s's own page: %s"
                % (e["place"], e["election"], short_when(e), e["office"], e["officialResults"]))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//districtry//election reminder//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        "UID:%s-%s@%s" % (tag, e["id"], host),
        "DTSTAMP:%sT000000Z" % e["checked"].replace("-", ""),
        "DTSTART;VALUE=DATE:%s" % day.strftime("%Y%m%d"),
        "DTEND;VALUE=DATE:%s" % (day + datetime.timedelta(days=1)).strftime("%Y%m%d"),
        "SUMMARY:%s" % _ics_text(summary),
        "DESCRIPTION:%s" % _ics_text("%s\n\n%s" % (text, url)),
        "URL:%s" % url,
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return b"\r\n".join(_fold(l) for l in lines) + b"\r\n"


# ---------------------------------------------------------------- the workflows

def check_workflows(tag, cal):
    """A workflow that commits a polling list an election's link waits on must
    run this script and commit the app, or the pull request it opens fails
    this check on the day the list moves to that election."""
    lists = sorted({"%s/%s" % (tag, e["polling"]["list"])
                    for e in cal["elections"] if e.get("polling")})
    if not lists:
        return []
    held = []
    for name in sorted(os.listdir(WORKFLOWS)):
        if not name.endswith((".yml", ".yaml")):
            continue
        with open(os.path.join(WORKFLOWS, name), encoding="utf-8") as f:
            text = f.read()
        for data in lists:
            if not re.search(r"git add[^\n]*%s" % re.escape(data), text):
                continue
            need = ["scripts/build_election_notices.py", "%s/index.html" % tag]
            missing = [n for n in need if n not in text]
            if missing:
                raise NoticeError(
                    ".github/workflows/%s commits %s and never names %s. The map's "
                    "\"Where you vote\" link appears when that list is for the coming "
                    "election, so add a step running python3 scripts/build_election_notices.py "
                    "and `git add` %s/index.html" % (name, data, ", ".join(missing), tag))
            held.append(name)
    return held


# ---------------------------------------------------------------- run

def targets(host):
    """{relative path: bytes} for every file this script owns, and the notes
    the OK line prints."""
    out, notes = {}, []
    for tag in calendar_tags():
        cal = load(tag)
        app_path = "%s/index.html" % tag
        with open(os.path.join(REPO_ROOT, app_path), encoding="utf-8") as f:
            text = f.read()
        if "ENGINE:BEGIN next-election" not in text:
            raise NoticeError("%s carries no next-election engine fence" % app_path)
        areas = registered_areas(text, app_path)
        for e in cal["elections"]:
            if e["area"] not in areas:
                raise NoticeError("%s/%s: %s is held in the area %r, and %s's "
                                  "registerNextElection call names no such area (it names: %s)"
                                  % (tag, CALENDAR.replace(os.sep, "/"), e["id"], e["area"],
                                     app_path, ", ".join(sorted(areas)) or "none"))
            out["%s/%s/%s.ics" % (tag, REMINDER_DIR, e["id"])] = reminder_ics(tag, e, host)
        out[app_path] = put_app_region(tag, text).encode("utf-8")
        held = check_workflows(tag, cal)
        kinds = {}
        for e in cal["elections"]:
            kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
        notes.append("%s: %d election(s) (%s)%s" % (
            tag, len(cal["elections"]),
            ", ".join("%d %s" % (kinds[k], k) for k in KINDS if k in kinds),
            ", polling list held by %s" % ", ".join(held) if held else ""))
    # a reminder whose election has left the calendar
    for path in sorted(glob.glob(os.path.join(REPO_ROOT, "*", REMINDER_DIR, "*.ics"))):
        rel = os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")
        if rel not in out:
            raise NoticeError("%s is a reminder for an election no calendar lists. Delete "
                              "it, or restore its entry" % rel)
    # an app carrying the region with no calendar behind it
    for path in sorted(glob.glob(os.path.join(REPO_ROOT, "*", "index.html"))):
        rel = os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")
        if rel in out or not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            if REGION_BEGIN in f.read():
                raise NoticeError("%s carries an %s region and its instance has no %s"
                                  % (rel, REGION, CALENDAR.replace(os.sep, "/")))
    return out, notes


def run(args):
    out, notes = targets(site_host())
    drift, written = [], 0
    for rel in sorted(out):
        path = os.path.join(REPO_ROOT, rel)
        try:
            with open(path, "rb") as f:
                current = f.read()
        except OSError:
            current = None
        if current == out[rel]:
            continue
        if args.check:
            drift.append(rel)
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(out[rel])
        written += 1
    if args.check:
        if drift:
            raise NoticeError("%s out of date — run python3 scripts/build_election_notices.py"
                              % ", ".join(drift))
        print("build-election-notices: OK — %s"
              % ("; ".join(notes) if notes else "no instance has an election calendar"))
    else:
        print("build-election-notices: OK — %d file(s) written; %s" % (written, "; ".join(notes)))


def selftest():
    """The three wordings in each of the five places, the rules a calendar is
    held to, and the reminder file's shape, on fixtures: no real calendar uses
    "plans" or "official" yet, and these are the sentences the first one that
    does will print."""
    def check(cond, msg):
        if not cond:
            raise NoticeError("selftest: " + msg)

    base = {"id": "springfield-2031-04-01", "date": "2031-04-01", "place": "Springfield",
            "election": "consolidated election", "ballot": "mayor and city council",
            "area": "springfield", "office": "Sangamon County Clerk", "officeShort": "the Clerk",
            "officialResults": "https://example.gov/results", "kind": "posted",
            "dateSource": "https://example.gov/calendar", "checked": "2031-01-02"}

    def cal(**over):
        e = dict(base)
        e.update(over)
        for k in [k for k, v in e.items() if v is None]:
            del e[k]
        return {"timeZone": "America/Chicago", "elections": [e]}

    def refuses(c, why, publishers=None):
        try:
            validate("zz", c, "fixture", publishers=publishers, files=False)
        except NoticeError:
            return
        raise NoticeError("selftest: validate accepted " + why)

    validate("zz", cal(), "fixture", publishers={"Sangamon County Clerk"}, files=False)
    refuses(cal(), "a posted promise from an office with no posted results", publishers={"Other"})
    refuses(cal(kind="official", officeShort=None), "an official entry with no why")
    refuses(cal(why="Because."), "a why on a posted entry")
    refuses(cal(kind="maybe"), "an unknown kind")
    refuses(cal(date="2031-02-30"), "a date that does not exist")
    refuses(cal(officialResults="http://example.gov/"), "a results link that is not https")
    refuses(cal(extra=1), "an unknown key")
    refuses(cal(ballot="mayor."), "a ballot ending in a full stop")
    refuses({"timeZone": "America/Chicago", "elections": [dict(base), dict(base)]}, "a repeated id")

    posted = base
    plans = dict(base, kind="plans")
    official = dict(base, kind="official", why="The Clerk publishes results only as scanned pages.")
    official.pop("officeShort")
    check(when(posted) == "Tuesday, April 1, 2031", "when() reads %r" % when(posted))
    check(sentence(posted, "page") ==
          "After the polls close on Tuesday, April 1, 2031, precinct results for "
          "Springfield&#x27;s consolidated election will be posted on this page as the "
          "Sangamon County Clerk publishes them. They stay marked unofficial until the "
          "Clerk certifies them.", "the posted sentence moved: %s" % sentence(posted, "page"))
    for e in (posted, plans, official):
        for where in ("page", "site", "front", "map", "card"):
            s = sentence(e, where, "/zz/election-results.html")
            check("election night" not in s.lower(), "%s/%s says election night" % (e["kind"], where))
            check(s.rstrip().endswith("."), "%s/%s does not end a sentence" % (e["kind"], where))
            if where in ("map", "card"):
                check("<" not in s and "&" not in s, "%s/%s is not plain text" % (e["kind"], where))
    check("plans to post" in sentence(plans, "page") and "example.gov/results" in sentence(plans, "page"),
          "the plans sentence must say so and link the office")
    check("posted on" not in sentence(official, "page") and
          "cannot post results" in sentence(official, "page") and
          "scanned pages" in sentence(official, "page"),
          "the official sentence must refuse, say why and promise nothing")
    check("will be posted" not in sentence(plans, "map") and "will be posted" not in sentence(official, "map"),
          "only a posted election may say results will be posted")

    ics = reminder_ics("zz", dict(posted, place="Springfield, Illinois; the capital"), "example.org")
    check(ics.endswith(b"END:VCALENDAR\r\n") and b"\n" not in ics.replace(b"\r\n", b""),
          "the reminder must use CRLF line ends throughout")
    check(all(len(l) <= 75 for l in ics.split(b"\r\n")), "a reminder line is longer than 75 octets")
    unfolded = ics.replace(b"\r\n ", b"").decode("utf-8")
    check("DTSTART;VALUE=DATE:20310402" in unfolded and "DTEND;VALUE=DATE:20310403" in unfolded,
          "the reminder is not the day after the election")
    check("SUMMARY:Springfield\\, Illinois\\; the capital election results on districtry" in unfolded,
          "commas and semicolons must be escaped in the reminder")
    check("DTSTAMP:20310102T000000Z" in unfolded, "DTSTAMP must come from the entry, not the clock")
    check(reminder_ics("zz", posted, "example.org") == reminder_ics("zz", posted, "example.org"),
          "the reminder is not the same bytes twice")
    script = reveal_script("document.currentScript.previousElementSibling")
    check(script.count("</script>") == 1, "the reveal script must close exactly once")
    print("build-election-notices: selftest OK — three wordings in five places, ten refused "
          "calendars, the reminder file's shape")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="drift gate: fail rather than write")
    ap.add_argument("--selftest", action="store_true", help="hold the wording and rules to fixtures")
    args = ap.parse_args()
    try:
        if args.selftest:
            return selftest()
        return run(args)
    except NoticeError as exc:
        print("build-election-notices: FAIL — %s" % exc, file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
