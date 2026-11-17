#!/usr/bin/env python3
"""Write tx/data/app/tx-county-commissioners.json: the four commissioners of a
Texas county's commissioners court, read from that county's own website, for
the counties whose pages are read here. The County card names them beside the
county judge, who comes from tx-county-officials.json.

WHY COUNTY BY COUNTY. A Texas county is governed by a commissioners court: the
county judge, elected by the whole county, and four commissioners, each
elected from one commissioner precinct (Tex. Const. art. V, sec. 18). 254
counties, so 1,016 commissioners, and measured 2026-11-16 no state office
publishes a list of them: the Office of Court Administration's judicial
directory, which names the county judges, lists courts and so not the
commissioners; the Secretary of State's election results site answers this
project's reader with a managed challenge, which is never worked around; and
the Texas Association of Counties is an association of the counties, not a
government. Adam chose on 2026-11-17 to read each county's own website,
largest county first. COUNTIES below is that list as far as it has been read.

WHAT EACH COUNTY'S PAGE IS, MEASURED 2026-11-16 AND 2026-11-17 with this
script's own client (scraper_common.UA_HEADERS_ROSTER_BOT on the requests
stack), one GET each after a read of the host's robots.txt. The twelve are the
largest counties, by the 2020 census, whose own sites serve this client:

  Harris    The county's Precinct 4 office's page of the whole court, on the
            county's domain; the name above "Commissioner Precinct N".
  Dallas    Dallas calls its commissioner precincts DISTRICTS. The court page
            names the four in links to /government/comcrt/districtN/; the menu
            links the same addresses as "Commissioner District N".
  Tarrant   "Commissioner Precinct N -" and the name on the next line, printed
            in the page and again in its menu; both must agree.
  Travis    "Precinct One - <name>" to "Precinct Four - <name>".
  Collin    "Precinct N –" (an en dash) and the name on the next line, under
            "Elected Commissioners". The host publishes no robots.txt (404).
  Denton    The name above "Commissioner Precinct N".
  Fort Bend "Commissioner Pct N <name>" on one line, in the court page's menu.
  Hidalgo   "Commissioner Precinct N" and the name on the next line.
  El Paso   One page per commissioner; the name above "County Commissioner,
            Precinct 1", "Commissioner Pct 3" and the like.
  Cameron   "Commissioner Pct. N, <name>" in the menu every page carries, read
            from the home page.
  Webb      One page per commissioner; the name above "Commissioner Precinct
            N", printed with "Honorable" before it, which is dropped.
  Lubbock   One page per commissioner; "County Commissioner - Precinct N" and
            the name on the next line. Its robots.txt asks for 300 seconds
            between requests, so its four pages take about twenty minutes.

NOT READ, AND WHY, among the twenty largest:
  Bexar     www.bexar.org answered two of three reads with Cloudflare's managed
            challenge ("Just a moment..."). A host that challenges is
            challenge-fronted for every path, and getting in on the reads where
            the control happens to be off is working around it (CLAUDE.md). It
            waits for a deliberate re-measurement: three consecutive reads at
            least fifteen seconds apart serving the page.
  Montgomery, Bell
            www.mctx.org and www.bellcountytx.com publish `User-agent: *` /
            `Disallow: /` (the same 210 bytes on both), which binds this
            project. Not fetched.
  Williamson, McLennan, Hays
            www.wilcotx.gov, www.mclennan.gov and www.hayscountytx.gov answer
            this client with Cloudflare's "Sorry, you have been blocked" page
            (HTTP 403) on the page and on robots.txt.
  Brazoria, Galveston, Nueces
            Each answers this client with Akamai's "Access Denied" (HTTP 403)
            on the page and on robots.txt.
  The last six refuse this project's own client. CLAUDE.md allows a browser
  identity where a site measurably refuses ours by its fingerprint, with the
  measurement recorded; none has been tried yet, so they are recorded here and
  in the gap record instead.

A NAME IS PRINTED AS THE COUNTY PRINTS IT, honorific and all ("Dr. Elba
Garcia"), the fleet's practice; each must pass the fleet's officeholder-name
test, carry no digit and be one of four distinct names for precincts 1 to 4.
A page whose shape changes FAILS ITS PARSER rather than yielding a guess.

A COUNTY WHOSE PAGE CANNOT BE READ KEEPS ITS LAST RECORD (Adam's rule of
2026-09-19: a refusal stops the fetch and never unpublishes what was already
read). Each record's `asOf` is the date its four names were first read in
that form: a rebuild that reads the same names keeps the old date, so a week
with no change writes the same bytes and opens no pull request. A carried
record keeps its date too, so the date is never later than the last read, and
the card says the page is looked at weekly rather than claiming the date is
the last look. Because a carried county changes no byte, --unread FILE writes
the counties not read this run, one per line, and the weekly job's last step
fails on a non-empty list, so a page that stopped reading turns the run red
instead of staying quiet behind its last record.

THE PAGES ARE SNAPSHOTS. Commissioners elected on 3 November 2026 take office
on 1 January 2027, and a county's page changes when the county changes it.

Usage:
    python3 tx/scripts/build_tx_county_commissioners.py [OUT_DIR]
    python3 tx/scripts/build_tx_county_commissioners.py --check

--check reads the SHIPPED file and nothing else, offline and with the
standard library alone: every record a county the County layer draws and
COUNTIES lists, four seats numbered 1 to 4 with four distinct names that pass
the fleet's name test, its source address one COUNTIES gives, and a dated
`asOf`. It proves the file is what a build writes; it never proves a county
has not changed its page since.

--save DIR writes each fetched page into DIR, reading back any it already
holds; --offline DIR reads them back instead of fetching. --unread FILE writes
the names of the counties not read this run (see above).
"""

import datetime
import json
import os
import re
import sys
import time
from html.parser import HTMLParser
from urllib.parse import urlsplit

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts"))
from robots_policy import RobotsGate  # noqa: E402  (FLEET_SHARED)
from scraper_common import (  # noqa: E402  (FLEET_SHARED)
    UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, fetch as fetch_response)
from validate_officeholder_names import why_not_a_name  # noqa: E402  (FLEET_SHARED)

PACE_SECONDS = 1.0
INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
OUT_NAME = "tx-county-commissioners.json"
COUNTIES_FILE = os.path.join(DEFAULT_OUT_DIR, "state-counties.json")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NUMBER_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4}
# Words that name an office or a page part, never a person: a line carrying one
# is not a commissioner's name, whatever the line beside it says.
NOT_A_PERSON_RE = re.compile(
    r"\b(?:Commissioners?|Court|County|Judge|Precinct|Pct|District|Home|Connect|Menu|"
    r"Agenda|Agendas|Office|Contact|Us|Map|Maps|Directory|Services|Statement|Mission|"
    r"Newsletters?|Information|Resources|Welcome|Staff|Projects|Events|News|Links|"
    r"Documents|Forms|Calendar|Videos?|Live|Online|Search|Email|Biography|Meetings?)\b", re.I)
# The shape of a printed name: two to six words, each a capitalised word, an
# initial, a quoted nickname or a particle, with an optional ", Jr." and the
# like. A heading such as "Mission Statement" has this shape too, which is why
# NOT_A_PERSON_RE and the precinct label beside it are what make a line a name.
_WORD = r"(?:[A-ZÀ-Þ][A-Za-zÀ-ÿ'’.-]*|\"[^\"]+\"|“[^”]+”|de|del|la|los|van|von|y)"
NAME_RE = re.compile(r"^%s(?:\s+%s){1,5}(?:,\s+(?:Jr|Sr)\.?|,?\s+(?:II|III|IV))?$" % (_WORD, _WORD))
# A courtesy title some counties print before a name; it is not part of it.
# "Dr." is kept as printed, the fleet's practice.
HONORIFIC_RE = re.compile(r"^(?:The\s+)?(?:Honorable|Hon\.)\s+", re.I)
# The label most county pages print beside a commissioner's name.
LABEL = r"(?:County\s+)?Commissioner,?\s+(?:Precinct|Pct\.?)\s*(?P<n>[1-4])"

# Each county: where its names are printed and in which of four patterns.
#   name_above  the name on the line above the precinct label
#   name_below  the name on the line below it
#   inline      the label and the name on one line (a `name` group)
#   links       the name as a link's text, the precinct in the link's address
# `pages` maps each precinct to a page of its own, where a county prints each
# commissioner on that commissioner's page; only that precinct is read there.
COUNTIES = [
    dict(geoid="48201", county="Harris County", seat_word="Precinct",
         url="https://cp4.harriscountytx.gov/Connect/Commissioners-Court",
         mode="name_above", label=LABEL),
    dict(geoid="48113", county="Dallas County", seat_word="District",
         url="https://www.dallascounty.org/government/comcrt/", mode="links",
         href=r"/government/comcrt/district(?P<n>[1-4])/?$", skip=r"^Commissioner District"),
    dict(geoid="48439", county="Tarrant County", seat_word="Precinct",
         url="https://www.tarrantcountytx.gov/en/commissioners-court.html",
         mode="name_below", label=r"Commissioner Precinct (?P<n>[1-4]) -"),
    dict(geoid="48453", county="Travis County", seat_word="Precinct",
         url="https://www.traviscountytx.gov/commissioners-court",
         mode="inline", label=r"Precinct (?P<n>One|Two|Three|Four) - (?P<name>.+)"),
    dict(geoid="48085", county="Collin County", seat_word="Precinct",
         url="https://www.collincountytx.gov/government/commissioners-court",
         mode="name_below", label="Precinct (?P<n>[1-4]) –", after="Elected Commissioners"),
    dict(geoid="48121", county="Denton County", seat_word="Precinct",
         url="https://www.dentoncounty.gov/165/Commissioners-Court",
         mode="name_above", label=LABEL),
    dict(geoid="48157", county="Fort Bend County", seat_word="Precinct",
         url="https://www.fortbendcountytx.gov/government/departments/commissioners-court",
         mode="inline", label=r"Commissioner Pct (?P<n>[1-4]) (?P<name>.+)"),
    dict(geoid="48215", county="Hidalgo County", seat_word="Precinct",
         url="https://www.hidalgocounty.us/2179/Commissioners",
         mode="name_below", label=r"Commissioner Precinct (?P<n>[1-4])"),
    dict(geoid="48141", county="El Paso County", seat_word="Precinct",
         url="https://www.epcounty.com/165/Commissioners-Court", mode="name_above", label=LABEL,
         pages={1: "https://www.epcounty.com/194/Commissioner-Precinct-1",
                2: "https://www.epcounty.com/195/Commissioner-Precinct-2",
                3: "https://www.epcounty.com/196/Commissioner-Precinct-3",
                4: "https://www.epcounty.com/197/Commissioner-Precinct-4"}),
    dict(geoid="48061", county="Cameron County", seat_word="Precinct",
         url="https://www.cameroncountytx.gov/",
         mode="inline", label=r"Commissioner Pct\. (?P<n>[1-4]), (?P<name>.+)"),
    dict(geoid="48479", county="Webb County", seat_word="Precinct",
         url="https://www.webbcountytx.gov/170/Commissioners-Court", mode="name_above", label=LABEL,
         pages={1: "https://www.webbcountytx.gov/175/Commissioner-Pct-1",
                2: "https://www.webbcountytx.gov/176/Commissioner-Pct-2",
                3: "https://www.webbcountytx.gov/177/Commissioner-Pct-3",
                4: "https://www.webbcountytx.gov/178/Commissioner-Pct-4"}),
    dict(geoid="48303", county="Lubbock County", seat_word="Precinct",
         url="https://www.lubbockcounty.gov/department/division.php?structureid=223",
         mode="name_below", label=r"County Commissioner - Precinct (?P<n>[1-4])",
         pages={1: "https://www.lubbockcounty.gov/department/index.php?structureid=8",
                2: "https://www.lubbockcounty.gov/department/index.php?structureid=9",
                3: "https://www.lubbockcounty.gov/department/index.php?structureid=10",
                4: "https://www.lubbockcounty.gov/department/index.php?structureid=11"}),
]

_GATE = []
_LAST = {}


def gate():
    """One robots.txt reader for the run, with the client that fetches; it
    reads each host's file once."""
    if not _GATE:
        import requests  # the fetch below is requests too
        _GATE.append(RobotsGate(requests.Session(), UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT))
    return _GATE[0]


def fetch(url, label):
    """One GET with this project's own client, after the host's robots.txt has
    been read with that same client and asked about this address. A refusal
    raises, so the county keeps its last record. Requests to one host are
    spaced by the Crawl-delay its robots.txt states, and by PACE_SECONDS where
    it states none (Lubbock's asks for 300 seconds). Returns bytes.

    It reads the policy through robots_policy.RobotsGate rather than
    scraper_common.require_robots_allowed or require_robots_once because
    those two end the process on a refusal, and here one county's refusal must
    keep that county's last record while the other counties are read; the gate
    also gives the Crawl-delay. Every address is asked about, not only the
    first on each host."""
    ok, why = gate().allows(url)
    print("robots.txt %s: %s" % (label, why), file=sys.stderr)
    if not ok:
        raise RuntimeError("%s refuses this client: %s; nothing fetched" % (url, why))
    host = urlsplit(url).hostname
    delay = max(PACE_SECONDS, float(gate().crawl_delay(url) or 0))
    wait = delay - (time.time() - _LAST.get(host, 0.0))
    if wait > 0:
        print("waiting %.0f s for %s's crawl delay" % (wait, host), file=sys.stderr)
        time.sleep(wait)
    try:
        return fetch_response(url, UA_HEADERS_ROSTER_BOT, timeout=60, attempts=2).content
    finally:
        _LAST[host] = time.time()


class Files(object):
    """Fetch, or read back, each page by a name derived from its URL."""

    def __init__(self, offline=None, save=None):
        self.offline = offline
        self.save = save

    @staticmethod
    def name(url):
        return re.sub(r"[^A-Za-z0-9._-]+", "_", url.split("://", 1)[-1])

    def get(self, url, label):
        name = self.name(url)
        for d in (self.offline, self.save):
            if d and os.path.exists(os.path.join(d, name)):
                with open(os.path.join(d, name), "rb") as f:
                    return f.read()
        if self.offline:
            raise RuntimeError("%s is not saved in %s" % (url, self.offline))
        body = fetch(url, label)
        if self.save:
            os.makedirs(self.save, exist_ok=True)
            with open(os.path.join(self.save, name), "wb") as f:
                f.write(body)
        return body


class Page(HTMLParser):
    """A page's visible text as lines, one per block, and its links as
    (href, text) pairs. Scripts, styles and inline SVG are dropped."""

    BLOCKS = {"p", "div", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "td", "th",
              "span", "a", "strong", "section", "article", "header", "footer", "nav", "ul"}
    SKIP = {"script", "style", "noscript", "svg", "template"}

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts = []
        self.links = []
        self._href = None
        self._text = []
        self.feed(html)
        self.close()
        lines = (" ".join(l.split()) for l in "".join(self.parts).splitlines())
        self.lines = [l for l in lines if l]

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        if tag in self.BLOCKS:
            self.parts.append("\n")
        if tag == "a":
            self._href = dict(attrs).get("href") or ""
            self._text = []

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None
        if tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.skip:
            return
        self.parts.append(data)
        if self._href is not None:
            self._text.append(data)


def person(raw, where):
    """A commissioner's name as printed, less a courtesy title, or raise."""
    name = HONORIFIC_RE.sub("", " ".join((raw or "").split()))
    problem = why_not_a_name(name) if name else "nothing printed"
    if problem:
        raise RuntimeError("%s: %r is not a name (%s)" % (where, name, problem))
    if NOT_A_PERSON_RE.search(name) or re.search(r"\d", name) or len(name) > 60:
        raise RuntimeError("%s: %r reads as an office or a page part, not a name" % (where, name))
    if not NAME_RE.match(name):
        raise RuntimeError("%s: %r is not shaped like a printed name" % (where, name))
    return name


def maybe_person(raw, where):
    """person(raw), or None: a line beside a label that is not a name (a menu
    heading, another label) is passed over rather than read."""
    try:
        return person(raw, where)
    except RuntimeError:
        return None


def agree(found, where):
    """{number: name} from a list of (number, name) readings, each number read
    at least once and every reading of it the same name."""
    out = {}
    for number, name in found:
        if number in out and out[number] != name:
            raise RuntimeError("%s: precinct %d is printed as both %r and %r"
                               % (where, number, out[number], name))
        out[number] = name
    return out


def number(token):
    return NUMBER_WORDS.get(token) or int(token)


def readings(page, spec, where):
    """Every (precinct, name) the page prints in the county's pattern."""
    found = []
    lines = page.lines
    if spec.get("after"):
        try:
            lines = lines[lines.index(spec["after"]) + 1:]
        except ValueError:
            raise RuntimeError("%s: no %r heading" % (where, spec["after"]))
    mode = spec["mode"]
    if mode == "links":
        for href, text in page.links:
            m = re.search(spec["href"], href)
            if m and text and not re.match(spec["skip"], text):
                name = maybe_person(text, where)
                if name:
                    found.append((number(m.group("n")), name))
        return found
    label = re.compile("^%s$" % spec["label"])
    for i, line in enumerate(lines):
        m = label.match(line)
        if not m:
            continue
        if mode == "inline":
            raw = m.group("name")
        elif mode == "name_above":
            raw = lines[i - 1] if i > 0 else ""
        elif mode == "name_below":
            raw = lines[i + 1] if i + 1 < len(lines) else ""
        else:
            raise RuntimeError("%s: unknown mode %r" % (where, mode))
        name = maybe_person(raw, where)
        if name:
            found.append((number(m.group("n")), name))
    return found


def read_county(spec, files):
    """The county's record, freshly read, or raise."""
    pages = spec.get("pages") or {0: spec["url"]}
    found = []
    for want, url in sorted(pages.items()):
        where = "%s (%s)" % (spec["county"], url)
        page = Page(files.get(url, spec["county"]).decode("utf-8", "replace"))
        got = readings(page, spec, where)
        if want:
            got = [(n, name) for n, name in got if n == want]
            if not got:
                raise RuntimeError("%s: no name printed for precinct %d" % (where, want))
        found.extend(got)
    where = "%s (%s)" % (spec["county"], spec["url"])
    names = agree(found, where)
    if sorted(names) != [1, 2, 3, 4]:
        raise RuntimeError("%s: read precincts %s, not 1 to 4" % (where, sorted(names)))
    if len(set(names.values())) != 4:
        raise RuntimeError("%s: the four names are not four people" % where)
    seats = []
    for n in (1, 2, 3, 4):
        seat = {"seat": "Commissioner, %s %d" % (spec["seat_word"], n), "number": n,
                "name": names[n]}
        if spec.get("pages"):
            seat["sourceUrl"] = spec["pages"][n]
        seats.append(seat)
    return {
        "county": spec["county"],
        "seats": seats,
        "source": "%s's own website" % spec["county"],
        "sourceUrl": spec["url"],
    }


def counties():
    """{GEOID: NAME} for the 254 counties the County layer draws."""
    with open(COUNTIES_FILE) as f:
        feats = json.load(f)["features"]
    return {str(f["properties"]["GEOID"]): str(f["properties"]["NAME"]) for f in feats}


def build(files, previous, today):
    out, carried, fresh, unread = {}, [], [], []
    for spec in COUNTIES:
        old = previous.get(spec["geoid"])
        try:
            rec = read_county(spec, files)
        except Exception as e:  # noqa: BLE001 -- any failure keeps the last record
            print("NOT READ: %s: %s" % (spec["county"], str(e)[:300]), file=sys.stderr)
            unread.append(spec["county"])
            if old:
                out[spec["geoid"]] = old
                carried.append(spec["county"])
            continue
        same = old and {k: v for k, v in old.items() if k != "asOf"} == rec
        rec["asOf"] = old["asOf"] if same else today
        out[spec["geoid"]] = rec
        fresh.append(spec["county"])
    return out, fresh, carried, unread


def shape_problems(data, drawn):
    problems = []
    listed = {c["geoid"]: c for c in COUNTIES}
    for geoid, rec in data.items():
        where = "%s (%s)" % (geoid, rec.get("county") if isinstance(rec, dict) else "?")
        if geoid not in drawn:
            problems.append("%s: not a county the County layer draws" % where)
            continue
        spec = listed.get(geoid)
        if not spec:
            problems.append("%s: not a county this builder reads" % where)
            continue
        if rec.get("county") != drawn[geoid] or rec.get("county") != spec["county"]:
            problems.append("%s: county name %r" % (where, rec.get("county")))
        if rec.get("sourceUrl") != spec["url"]:
            problems.append("%s: source address is not the county page this builder reads" % where)
        if rec.get("source") != "%s's own website" % spec["county"]:
            problems.append("%s: source %r" % (where, rec.get("source")))
        if not ISO_DATE_RE.match(str(rec.get("asOf", ""))):
            problems.append("%s: asOf %r is not a date" % (where, rec.get("asOf")))
        seats = rec.get("seats")
        if not isinstance(seats, list) or [s.get("number") for s in seats] != [1, 2, 3, 4]:
            problems.append("%s: seats are not precincts 1 to 4 in order" % where)
            continue
        names = []
        for s in seats:
            want = "Commissioner, %s %d" % (spec["seat_word"], s["number"])
            if s.get("seat") != want:
                problems.append("%s: seat %r, not %r" % (where, s.get("seat"), want))
            page = (spec.get("pages") or {}).get(s["number"])
            if s.get("sourceUrl") != page or set(s) - {"seat", "number", "name", "sourceUrl"}:
                problems.append("%s: seat %d's fields or page address" % (where, s["number"]))
            try:
                names.append(person(s.get("name"), where))
            except RuntimeError as e:
                problems.append(str(e))
        if len(set(names)) != 4:
            problems.append("%s: the four names are not four people" % where)
        if set(rec) != {"county", "seats", "source", "sourceUrl", "asOf"}:
            problems.append("%s: fields %s" % (where, sorted(rec)))
    return problems


def load(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check():
    data = load(os.path.join(DEFAULT_OUT_DIR, OUT_NAME))
    if not data:
        print("FAIL: %s is missing or empty" % OUT_NAME, file=sys.stderr)
        sys.exit(1)
    problems = shape_problems(data, counties())
    for p in problems:
        print("FAIL: %s" % p, file=sys.stderr)
    if problems:
        sys.exit(1)
    print("tx-county-commissioners: OK — %d counties, %d commissioners named from the counties' "
          "own websites (%s)" % (len(data), 4 * len(data),
                                ", ".join(sorted(r["county"] for r in data.values()))))


def main(argv):
    args = list(argv)
    if "--check" in args:
        check()
        return
    opts = {}
    for flag in ("--save", "--offline", "--unread"):
        if flag in args:
            i = args.index(flag)
            opts[flag] = args[i + 1]
            del args[i:i + 2]
    save, offline = opts.get("--save"), opts.get("--offline")
    out_dir = args[0] if args else DEFAULT_OUT_DIR
    path = os.path.join(out_dir, OUT_NAME)
    previous = load(path)
    today = datetime.date.today().isoformat()
    data, fresh, carried, unread = build(Files(offline=offline, save=save), previous, today)
    if opts.get("--unread"):
        with open(opts["--unread"], "w", encoding="utf-8") as f:
            f.write("".join(c + "\n" for c in unread))
    if not data:
        raise SystemExit("No county was read and none was shipped before; nothing written.")
    problems = shape_problems(data, counties())
    if problems:
        for p in problems:
            print("FAIL: %s" % p, file=sys.stderr)
        raise SystemExit("Refusing to write %s" % path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(data.items())), f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("Wrote %s (%d counties: %d read now%s)"
          % (path, len(data), len(fresh),
             ", carried: " + ", ".join(carried) if carried else ""))


if __name__ == "__main__":
    main(sys.argv[1:])
