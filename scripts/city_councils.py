#!/usr/bin/env python3
"""
Build a state's city council roster from each city's own pages: a person
reads each page once and writes its seats down, and the build proves every
name is still on the page it cites.

    python3 <tag>/scripts/build_<tag>_city_councils.py            # read every page, prove, write
    python3 <tag>/scripts/build_<tag>_city_councils.py --check    # offline
    python3 <tag>/scripts/build_<tag>_city_councils.py --watch    # is every name still on its page?

Each state that uses this has a short builder of its own, which names its
files, the client it reads with, how many seats each city has, and any page
that must be read with a browser's client together with the measurement that
allows it. Everything else lives here once. Used by
ar/scripts/build_ar_city_councils.py, nc/scripts/build_nc_city_councils.py,
ok/scripts/build_ok_city_councils.py, sc/scripts/build_sc_city_councils.py and
tn/scripts/build_tn_city_councils.py (all 2026-10-16), whose --watch the
weekly job .github/workflows/watch-city-council-pages.yml runs (Adam's choice
of 2026-10-16 over a quarterly re-read by hand).

WHY A PERSON READS THE PAGES. No state office in Arkansas, North Carolina,
Oklahoma, South Carolina or Tennessee publishes who sits on each city council,
and each city publishes its own council its own way: a page of names and
seats, names in a block of data the page fills itself in from, a meeting
agenda. A parser for each city would break at that city's next redesign, and
the done standard counts 122 cities across the five newest states that elect
councils. So the seats are written into a file a person keeps,
<tag>/data/source/<tag>-city-council-seats.json, and the build re-reads every
page it cites and refuses to write when a name is missing from its page.

WHAT THE PROOF IS. A name is on its page when its words appear, whole and in
order, in the page's text, both normalised the same way: Unicode compatibility
form, case folded, curly quotes and dashes made plain, and the punctuation a
page puts in a name (full stops, commas, brackets) turned into spaces. The
page's text is its markup with the tags removed, and a second time with any
data block in it unescaped first, because some cities fill their council
pages in from a block of data the page itself carries (the read-the-page-first
rule in CLAUDE.md). A PDF's text comes from pdftotext. Where the seats file
writes a name differently from its page (it leaves out a title such as "Dr."
or a nickname in brackets), the seat carries the page's own spelling as `as`,
and that is what is proved.

WHAT IT CANNOT PROVE. That a name sits beside the seat it is written against.
A page lists names and seats, and a transcription could put Ward 2's member
under Ward 3 with every name still on the page. The cross-check against the
drawn wards catches a ward the map does not have, never a swap inside one
city, so which seat a person holds is the reading of whoever wrote it down,
and --watch re-reads only the names.

A PAGE THAT CANNOT BE READ KEEPS WHAT IT LAST SAID, the operator's ruling of
2026-09-19 (a refusal stops the fetch and never unpublishes what was fetched
while the page was serving). Its record entry is carried forward with the
date it was last read, the build says so, and the app's file dates each city
by the oldest read of its pages, so a card never claims a reading that did
not happen. A page that has never been read must be read. --watch reports a
page it cannot read, so the weekly job surfaces it in its tracking issue.

THE FILES:
  * the seats file (kept by hand): `cities`, keyed by Census place id, each
    with `name` (as the Census names the place, less " city" or " town", or
    with the Census's whole name in `census` where it is something else, as
    for Nashville's metropolitan government), `body`, `how`
    (how its seats are elected, in a sentence or two the card shows),
    `sources` (key -> page) and `seats`, each `{seat, by, name, from}` plus
    `ward` and `as` where they apply; `by` is "ward" for a seat the ward's own
    voters elect and "city" for one the whole city elects, whether or not it
    is tied to a ward. A ward is a number, a letter or a name, and is labelled
    "District 3", "District A" or "East Ward". A seat the city says is empty
    carries `vacant: true` instead of a name, with the page's own words saying
    so in `as`, which is what is proved; one whose holder the city's own pages
    disagree about carries `unnamed`, a sentence saying so, and claims nothing
    a page could prove. A city whose council calls its wards something else
    says so in `wardWord`, and one whose council elects by a second kind of
    district as well gives that kind's word for each of its districts in
    `wardWords` (Memphis's {"8": "Super District", "9": "Super District"}),
    which the map's labels are held to; one whose members are not called
    council members names them in `member` ("Director" on a board of
    directors), and `note` carries a sentence the card shows about where the
    names came from when that is not simply the city's own council page.
    `page` is the council's own page for the card to link where the pages
    its seats cite are not ones a reader would open (a block of data the
    council page fills itself in from, or a zip of election results); it is
    linked and never read, so it proves nothing.
  * the record (the seats file's name with .source.json, written by the
    build): each page's read date, the client it was read with, its final
    address, size and hash, and the names found on it. A page that is not a
    web page (North Carolina's election results, a zip of tab-separated
    files) is turned into text by a reader the builder names, and its size and
    hash are the file's as it was downloaded.
  * the app's file (<tag>/data/app/<out_file>): each city by its Census id,
    `{name, body, how, read, seats}` (`note`, `page` and `wardWord` where set, and
    `wardsDrawn: false` for a city whose wards elect seats and are not drawn),
    every seat `{seat, name, role, byWard, sourceUrl}` plus `ward` where it has
    one, and `vacant` or `unnamed` in place of `name` for a seat that names
    nobody. `role` is "Mayor" or "Vice Mayor" for a seat labelled so, whether
    the voters elect its holder to it or the council chooses one of its
    members (the city's `how` says which), and for every other seat the
    city's `member` word, or "Council member" where it has none.

`--check` is offline and is what the instance's own checks run: the seats
file is well formed, names exactly the state's cities at the done standard's
floor (docs/expected-governments.json) and gives each the number of seats the
builder states; the record covers exactly its pages and found every name on
the page its seat cites; the app's file is exactly what the two produce; and
where the state draws wards, the wards on the map and the wards the seats
name agree city by city and ward by ward, labels included. A city is drawn
when any of its seats is elected by its ward's own voters, and then every ward
a seat names is drawn, including a ward whose member the whole city elects
(Gastonia's wards 3, 4 and 6 until 2027). A city whose
wards elect seats and are not drawn is named by the builder (`undrawn`, with
the reason), so the cross-check passes it over only on purpose, and fails if
such a city has no seat elected by ward or appears on the map after all.
"""

import argparse
import datetime
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

FLEET_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(FLEET_SCRIPTS)
if FLEET_SCRIPTS not in sys.path:
    sys.path.insert(0, FLEET_SCRIPTS)

import scraper_common as sc  # noqa: E402

EXPECTED = os.path.join(REPO_ROOT, "docs", "expected-governments.json")
PACE_SECONDS = 2.0
RATE_LIMIT_WAIT = 60
RATE_LIMIT_WAIT_MAX = 180
TIMEOUT = 60
TRIES = 2
MAX_HOPS = 8

CITY_KEYS = {"name", "census", "body", "how", "note", "page", "sources", "seats", "wardWord",
             "wardWords", "member"}
OFFICES = ("Mayor", "Vice Mayor")
SEAT_KEYS = {"seat", "by", "ward", "name", "as", "from", "vacant", "unnamed"}
# A ward is a number, a letter (Raleigh's District A) or a name (Winston-Salem's
# East Ward).
WARD_RE = re.compile(r"[1-9][0-9]?|[A-Z]|[A-Z][a-z]+")


def ward_sort_key(ward):
    """Numbered wards in number order, then lettered and named ones in
    alphabetical order."""
    ward = str(ward)
    return (0, int(ward), "") if ward.isdigit() else (1, 0, ward)


def ward_label(word, ward):
    """'District 3' and 'District A', but 'East Ward': a name comes first."""
    ward = str(ward)
    if ward.isdigit() or len(ward) == 1:
        return "%s %s" % (word, ward)
    return "%s %s" % (ward, word)


def drawn_wards(city):
    """The wards a city's map must draw: none where no seat is elected by a
    ward's own voters, and otherwise every ward a seat names, so a city electing
    some ward seats by the whole city (Gastonia, until 2027) draws them all."""
    seats = city.get("seats") or []
    if not any(s.get("by") == "ward" for s in seats):
        return []
    return sorted({str(s["ward"]) for s in seats if s.get("ward")}, key=ward_sort_key)


class Spec(object):
    """What a state's builder supplies.

    `seats` is {Census id: number of seats}, mayor included, so a seat dropped
    while editing the seats file fails rather than shipping a smaller council.
    `browser` is {page: headers} for pages read with a browser's client; the
    builder that passes one records the measurement beside it (CLAUDE.md,
    browser user-agent strings). `wards_file` is the drawn wards' data/app
    file, whose features carry `geoid`, `ward` and `label`, and `undrawn` is
    {Census id: why} for a city whose wards elect seats and are not on it.
    `readers` is {page: function} for a page that is not a web page, such as
    a zip of election results: the function turns the page's bytes into the
    text its names are looked for in."""

    def __init__(self, tag, label, user_agent, seats_file, out_file, seats,
                 browser=None, wards_file=None, undrawn=None, readers=None):
        self.tag = tag
        self.label = label
        self.user_agent = user_agent
        self.seats = dict(seats)
        self.browser = dict(browser or {})
        self.readers = dict(readers or {})
        self.undrawn = dict(undrawn or {})
        self.instance = os.path.join(REPO_ROOT, tag)
        self.seats_path = os.path.join(self.instance, "data", "source", seats_file)
        self.record_path = self.seats_path.replace(".json", ".source.json")
        self.out_path = os.path.join(self.instance, "data", "app", out_file)
        self.wards_path = (os.path.join(self.instance, "data", "app", wards_file)
                           if wards_file else None)


def fail(spec, msg):
    raise SystemExit("%s: FATAL: %s" % (spec.label, msg))


# ---------- the seats file ----------
def load_seats(spec):
    with open(spec.seats_path, encoding="utf-8") as fh:
        doc = json.load(fh)
    return doc.get("cities") or {}


def expected_units(spec):
    with open(EXPECTED, encoding="utf-8") as fh:
        doc = json.load(fh)
    return {u["geoid"]: u for u in doc.get("units", {}).get(spec.tag, [])}


def check_seats(spec, cities):
    """Problems with the seats file as written, before anything is read."""
    problems = []
    units = expected_units(spec)
    if set(cities) != set(units):
        missing = sorted(set(units) - set(cities))
        extra = sorted(set(cities) - set(units))
        if missing:
            problems.append("the seats file leaves out %s, which the done standard counts"
                            % ", ".join("%s (%s)" % (units[g]["name"], g) for g in missing))
        if extra:
            problems.append("the seats file names %s, which is not a city at the floor"
                            % ", ".join(extra))
    if set(spec.seats) != set(units):
        problems.append("the builder states seat counts for %d cities and the floor holds %d"
                        % (len(spec.seats), len(units)))
    for geoid, c in sorted(cities.items()):
        where = "%s (%s)" % (c.get("name"), geoid)
        odd = set(c) - CITY_KEYS
        if odd:
            problems.append("%s carries keys this builder does not read: %s"
                            % (where, ", ".join(sorted(odd))))
        for key in ("name", "body", "how"):
            if not isinstance(c.get(key), str) or not c[key].strip():
                problems.append("%s has no %s" % (where, key))
        for key in ("member", "wardWord", "note", "census"):
            if key in c and (not isinstance(c[key], str) or not c[key].strip()):
                problems.append("%s: %s is set and empty" % (where, key))
        unit = units.get(geoid)
        census = ((c["census"],) if c.get("census")
                  else (c.get("name", "") + " city", c.get("name", "") + " town"))
        if unit and c.get("name") and unit["name"] not in census:
            problems.append("%s: the Census names this place %r" % (where, unit["name"]))
        sources = c.get("sources") or {}
        if not sources:
            problems.append("%s cites no page" % where)
        for key, url in sources.items():
            if not (isinstance(url, str) and url.startswith("https://")):
                problems.append("%s: page %s is not an https address: %r" % (where, key, url))
        page = c.get("page")
        if "page" in c and not (isinstance(page, str) and page.startswith("https://")):
            problems.append("%s: page is not an https address: %r" % (where, page))
        seats = c.get("seats") or []
        if len(seats) != spec.seats.get(geoid):
            problems.append("%s has %d seats in the seats file and the builder states %s"
                            % (where, len(seats), spec.seats.get(geoid)))
        used = set()
        for s in seats:
            odd = set(s) - SEAT_KEYS
            if odd:
                problems.append("%s: a seat carries keys this builder does not read: %s"
                                % (where, ", ".join(sorted(odd))))
            states = [k for k in ("name", "vacant", "unnamed") if k in s]
            if len(states) != 1:
                problems.append("%s: seat %r must carry exactly one of name, vacant and "
                                "unnamed, and carries %s"
                                % (where, s.get("seat"), ", ".join(states) or "none"))
            if "vacant" in s and (s["vacant"] is not True or not s.get("as")):
                problems.append("%s: seat %r is vacant, which needs vacant: true and the "
                                "page's own words saying so in as" % (where, s.get("seat")))
            if "unnamed" in s and (not isinstance(s["unnamed"], str)
                                   or not s["unnamed"].strip() or "as" in s):
                problems.append("%s: seat %r names nobody, which needs a sentence saying "
                                "why in unnamed and nothing in as" % (where, s.get("seat")))
            for key in ("seat", "from") + (("name",) if "name" in s else ()):
                if not isinstance(s.get(key), str) or not s[key].strip():
                    problems.append("%s: a seat has no %s: %r" % (where, key, s))
            if s.get("by") not in ("ward", "city"):
                problems.append("%s: seat %r says it is elected by %r, which is neither "
                                "'ward' nor 'city'" % (where, s.get("seat"), s.get("by")))
            if s.get("by") == "ward" and not s.get("ward"):
                problems.append("%s: seat %r is elected by a ward and names none"
                                % (where, s.get("seat")))
            if "ward" in s and not WARD_RE.fullmatch(str(s["ward"])):
                problems.append("%s: seat %r names ward %r" % (where, s.get("seat"), s["ward"]))
            if re.search(r"[0-9]", str(s.get("name", ""))):
                problems.append("%s: %r is not a person's name" % (where, s.get("name")))
            if s.get("from") not in sources:
                problems.append("%s: seat %r cites page %r, which the city does not list"
                                % (where, s.get("seat"), s.get("from")))
            used.add(s.get("from"))
        unused = sorted(set(sources) - used)
        if unused:
            problems.append("%s lists pages no seat cites: %s" % (where, ", ".join(unused)))
        if "wardWords" in c:
            words = c["wardWords"]
            wards = {str(s.get("ward")) for s in seats if s.get("by") == "ward"}
            if not isinstance(words, dict) or not words:
                problems.append("%s: wardWords is set and is not a table of words" % where)
            else:
                for ward, word in sorted(words.items()):
                    if not (isinstance(word, str) and word.strip()):
                        problems.append("%s: wardWords gives district %r no word"
                                        % (where, ward))
                    if ward not in wards:
                        problems.append("%s: wardWords names district %r, and no seat is "
                                        "elected by it" % (where, ward))
    return problems


def pages_of(cities):
    """{page: [(Census id, seat)]} for every page the seats file cites."""
    out = {}
    for geoid, c in sorted(cities.items()):
        for s in c.get("seats") or []:
            url = (c.get("sources") or {}).get(s.get("from"))
            if url:
                out.setdefault(url, []).append((geoid, s))
    return out


def proof_name(seat):
    """What must be on the seat's page: its `as`, else its name; None for a
    seat that names nobody, which claims nothing a page could prove."""
    return seat.get("as") or seat.get("name")


# ---------- reading a page ----------
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def get(spec, url, headers):
    """GET one redirect hop at a time, reading each hop's robots.txt with the
    same client first. Returns (final url, body). A robots refusal raises
    SystemExit, as scraper_common's seam does everywhere."""
    opener = urllib.request.build_opener(_NoRedirect)
    for _hop in range(MAX_HOPS):
        sc.require_robots_once(url, headers["User-Agent"], headers=headers,
                               label=spec.label)
        req = urllib.request.Request(url, headers=headers)
        try:
            with opener.open(req, timeout=TIMEOUT) as resp:
                return url, resp.read()
        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location")
            if e.code in (301, 302, 303, 307, 308) and loc:
                url = urllib.parse.urljoin(url, loc)
                continue
            raise
    raise RuntimeError("more than %d redirects" % MAX_HOPS)


TAG_RE = re.compile(r"<[^>]+>")
ESCAPE_RE = re.compile(r"\\(u[0-9a-fA-F]{4}|.)", re.S)
SIMPLE_ESCAPES = {"n": " ", "t": " ", "r": " ", "b": " ", "f": " "}


def _unescape_once(text):
    def repl(m):
        tok = m.group(1)
        if tok[0] == "u" and len(tok) == 5:
            return chr(int(tok[1:], 16))
        return SIMPLE_ESCAPES.get(tok, tok)
    return ESCAPE_RE.sub(repl, text)


def page_text(body):
    """The text a name is looked for in: the markup without its tags, then the
    same with any data block unescaped (twice, for a block inside a block)."""
    if body[:5] == b"%PDF-":
        try:
            done = subprocess.run(["pdftotext", "-layout", "-", "-"], input=body,
                                  capture_output=True, check=True, timeout=120)
        except FileNotFoundError:
            raise RuntimeError("this page is a PDF and pdftotext (poppler-utils) is not "
                               "installed")
        return done.stdout.decode("utf-8", "replace")
    raw = body.decode("utf-8", "replace")
    parts = [html.unescape(TAG_RE.sub(" ", raw))]
    data = raw
    for _ in range(2):
        nxt = _unescape_once(data)
        if nxt == data:
            break
        data = nxt
        parts.append(html.unescape(TAG_RE.sub(" ", data)))
    return "\n".join(parts)


QUOTES = {"‘": "'", "’": "'", "ʼ": "'", "`": "'"}
PUNCT_RE = re.compile(r"[.,;:()\[\]\"“”«»]")
DASH_RE = re.compile(r"[‐-―−]")


def norm(text):
    text = unicodedata.normalize("NFKC", text)
    for a, b in QUOTES.items():
        text = text.replace(a, b)
    text = DASH_RE.sub("-", text).casefold()
    text = PUNCT_RE.sub(" ", text)
    return " " + " ".join(text.split()) + " "


def on_page(name, normalised_text):
    needle = norm(name)
    return needle.strip() != "" and needle in normalised_text


def _retry_after(err):
    """Seconds an HTTP 429 asks the client to wait, within RATE_LIMIT_WAIT_MAX;
    RATE_LIMIT_WAIT when it names none this builder can read."""
    raw = (err.headers.get("Retry-After") or "").strip() if err.headers else ""
    if raw.isdigit():
        return min(int(raw), RATE_LIMIT_WAIT_MAX)
    return RATE_LIMIT_WAIT


def read_page(spec, url):
    """(client, final url, body). Retries once on a network failure, and once
    after waiting on HTTP 429, which asks the client to slow down rather than
    answering the request (Maryville's site answered one read with it on
    2026-10-16); any other HTTP error is an answer and is not retried."""
    headers = spec.browser.get(url)
    client = "browser" if headers else "token"
    if not headers:
        headers = {"User-Agent": spec.user_agent}
    last = None
    for attempt in range(TRIES):
        try:
            final, body = get(spec, url, dict(headers))
            return client, final, body
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt + 1 >= TRIES:
                raise
            wait = _retry_after(e)
            print("%s: %s answered HTTP 429 (too many requests); waiting %d s and "
                  "asking once more" % (spec.label, url, wait), file=sys.stderr)
            last = e
            time.sleep(wait)
        except (urllib.error.URLError, OSError, RuntimeError) as e:
            last = e
            if attempt + 1 < TRIES:
                time.sleep(5)
    raise last


def read_all(spec, cities, prior):
    """Read every page. Returns (record pages, problems, carried pages)."""
    pages = pages_of(cities)
    out, problems, carried = {}, [], []
    today = datetime.date.today().isoformat()
    first = True
    for url, seats in sorted(pages.items()):
        if not first:
            time.sleep(PACE_SECONDS)
        first = False
        try:
            client, final, body = read_page(spec, url)
        except SystemExit as e:
            entry = (prior or {}).get(url)
            problems.append(("unread", url, "robots.txt refused this client: %s" % e))
            if entry:
                out[url] = entry
                carried.append(url)
            continue
        except (urllib.error.URLError, OSError, RuntimeError) as e:
            entry = (prior or {}).get(url)
            problems.append(("unread", url, "%s: %s" % (type(e).__name__, e)))
            if entry:
                out[url] = entry
                carried.append(url)
            continue
        reader = spec.readers.get(url)
        text = norm(reader(body) if reader else page_text(body))
        wanted = {proof_name(s) for _g, s in seats if proof_name(s)}
        found = sorted(n for n in wanted if on_page(n, text))
        for geoid, s in seats:
            if proof_name(s) and proof_name(s) not in found:
                problems.append(("missing", url, "%s, %s: %r is not on the page"
                                 % (cities[geoid]["name"], s["seat"], proof_name(s))))
        out[url] = {"read": today, "client": client, "final": final, "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(), "names": found}
        print("%s: read %s (%s, %d bytes): %d of %d names found"
              % (spec.label, url, client, len(body), len(found), len(wanted)))
    return out, problems, carried


# ---------- the record and the app's file ----------
def load_record(spec):
    if not os.path.exists(spec.record_path):
        return {}
    with open(spec.record_path, encoding="utf-8") as fh:
        return json.load(fh).get("pages") or {}


def record_doc(pages):
    return {
        "_about": ("Written by the builder, never by hand: for every page the seats file "
                   "cites, the date it was last read, the client it was read with, the "
                   "address it ended at, its size and hash, and the names found on it."),
        "pages": pages,
    }


def app_doc(cities, pages, undrawn=()):
    out = {}
    for geoid, c in sorted(cities.items()):
        reads = [pages[c["sources"][s["from"]]]["read"] for s in c["seats"]]
        entry = {"name": c["name"], "body": c["body"], "how": c["how"],
                 "read": min(reads), "seats": []}
        for key in ("note", "page", "wardWord"):
            if c.get(key):
                entry[key] = c[key]
        if geoid in undrawn:
            entry["wardsDrawn"] = False
        for s in c["seats"]:
            seat = {"seat": s["seat"], "byWard": s["by"] == "ward",
                    "role": s["seat"] if s["seat"] in OFFICES
                    else c.get("member") or "Council member",
                    "sourceUrl": c["sources"][s["from"]]}
            for key in ("name", "vacant", "unnamed"):
                if key in s:
                    seat[key] = s[key]
            if s.get("ward"):
                seat["ward"] = str(s["ward"])
            entry["seats"].append(seat)
        out[geoid] = entry
    return out


def dumps(doc):
    return json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def check_record(spec, cities, pages):
    problems = []
    wanted = pages_of(cities)
    for url in sorted(set(wanted) - set(pages)):
        problems.append("the record has never read %s; run the build" % url)
    for url in sorted(set(pages) - set(wanted)):
        problems.append("the record holds %s, which no seat cites any more; run the build"
                        % url)
    for url, seats in sorted(wanted.items()):
        entry = pages.get(url)
        if not entry:
            continue
        want_client = "browser" if url in spec.browser else "token"
        if entry.get("client") != want_client:
            problems.append("%s was last read with the %s client and the builder now reads it "
                            "with the %s client; run the build"
                            % (url, entry.get("client"), want_client))
        names = set(entry.get("names") or [])
        for geoid, s in seats:
            if proof_name(s) and proof_name(s) not in names:
                problems.append("%s, %s: %r was not found on %s when it was last read (%s); "
                                "run the build" % (cities[geoid]["name"], s["seat"],
                                                   proof_name(s), url, entry.get("read")))
    return problems


def check_wards(spec, cities):
    """The wards the map draws and the seats their voters elect, matched."""
    problems = []
    for geoid in sorted(spec.undrawn):
        c = cities.get(geoid)
        if c is None:
            problems.append("the builder says %s's wards are not drawn, and the seats file "
                            "has no such city" % geoid)
        elif not any(s.get("by") == "ward" for s in c.get("seats") or []):
            problems.append("the builder says %s's wards are not drawn, and no seat there is "
                            "elected by a ward" % c.get("name"))
    if not spec.wards_path:
        return problems
    with open(spec.wards_path, encoding="utf-8") as fh:
        feats = json.load(fh).get("features") or []
    drawn = {}
    for f in feats:
        p = f.get("properties") or {}
        drawn[(str(p.get("geoid")), str(p.get("ward")))] = p.get("label")
    for key in sorted(k for k in drawn if k[0] in spec.undrawn):
        problems.append("the map draws %s %s, and the builder says that city's wards are "
                        "not drawn" % (cities.get(key[0], {}).get("name", key[0]), drawn[key]))
    elected = {}
    for geoid, c in cities.items():
        if geoid in spec.undrawn:
            continue
        for ward in drawn_wards(c):
            word = (c.get("wardWords") or {}).get(ward) or c.get("wardWord") or "Ward"
            elected[(geoid, ward)] = ward_label(word, ward)
    for key in sorted(set(drawn) - set(elected)):
        problems.append("the map draws %s %s and no seat in the seats file names it"
                        % (cities.get(key[0], {}).get("name", key[0]), drawn[key]))
    for key in sorted(set(elected) - set(drawn)):
        problems.append("%s's seats file names %s, which the map does not draw"
                        % (cities[key[0]]["name"], elected[key]))
    for key in sorted(set(drawn) & set(elected)):
        if drawn[key] != elected[key]:
            problems.append("%s: the map labels a ward %r and the seats file calls it %r"
                            % (cities[key[0]]["name"], drawn[key], elected[key]))
    return problems


# ---------- the three modes ----------
def report(spec, problems, mode):
    for p in problems:
        print("%s %s: FAIL: %s" % (spec.label, mode, p))
    if problems:
        raise SystemExit(1)


def run_check(spec):
    cities = load_seats(spec)
    problems = check_seats(spec, cities)
    report(spec, problems, "--check")
    pages = load_record(spec)
    problems = check_record(spec, cities, pages)
    report(spec, problems, "--check")
    with open(spec.out_path, encoding="utf-8") as fh:
        shipped = fh.read()
    if shipped != dumps(app_doc(cities, pages, spec.undrawn)):
        problems.append("%s is not what the seats file and the record produce; run the "
                        "build rather than editing it by hand"
                        % os.path.relpath(spec.out_path, REPO_ROOT))
    problems += check_wards(spec, cities)
    report(spec, problems, "--check")
    seats = sum(len(c["seats"]) for c in cities.values())
    oldest = min(e["read"] for e in pages.values())
    print("%s --check: OK — %d cities, %d seats, every name found on the page it cites "
          "(pages read %s to %s)%s"
          % (spec.label, len(cities), seats, oldest, max(e["read"] for e in pages.values()),
             "; the drawn wards and the wards the seats name agree" if spec.wards_path else ""))


def run_watch(spec):
    cities = load_seats(spec)
    report(spec, check_seats(spec, cities), "--watch")
    prior = load_record(spec)
    pages, problems, _carried = read_all(spec, cities, prior)
    changed = sorted(u for u in pages if prior.get(u) and
                     prior[u].get("sha256") != pages[u].get("sha256"))
    for url in changed:
        print("%s --watch: %s has changed since it was read on %s (every name on it is "
              "still checked above)" % (spec.label, url, prior[url].get("read")))
    if problems:
        for kind, url, msg in problems:
            print("%s --watch: %s: %s" % (spec.label, "NOT READ" if kind == "unread"
                                          else "NAME GONE", msg))
        print("%s --watch: re-read the pages above and update the seats file; a name that "
              "has gone from its page usually means the seat changed hands" % spec.label)
        raise SystemExit(1)
    print("%s --watch: every name is still on the page it cites (%d pages read)"
          % (spec.label, len(pages)))


def run_build(spec):
    cities = load_seats(spec)
    report(spec, check_seats(spec, cities), "build")
    prior = load_record(spec)
    pages, problems, carried = read_all(spec, cities, prior)
    hard = [msg for kind, url, msg in problems if kind == "missing"]
    hard += ["%s could not be read and has never been read: %s" % (url, msg)
             for kind, url, msg in problems if kind == "unread" and url not in carried]
    report(spec, hard, "build")
    for url in carried:
        print("%s: NOT READ %s; keeping what it said on %s, the last time it was read"
              % (spec.label, url, pages[url]["read"]))
    problems = check_record(spec, cities, pages) + check_wards(spec, cities)
    report(spec, problems, "build")
    with open(spec.record_path, "w", encoding="utf-8") as fh:
        fh.write(dumps(record_doc(pages)))
    with open(spec.out_path, "w", encoding="utf-8") as fh:
        fh.write(dumps(app_doc(cities, pages, spec.undrawn)))
    seats = sum(len(c["seats"]) for c in cities.values())
    print("wrote %s: %d cities, %d seats, every name found on the page it cites"
          % (os.path.relpath(spec.out_path, REPO_ROOT), len(cities), seats))


def main(spec, doc):
    ap = argparse.ArgumentParser(description=(doc or "").strip().split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the app's file to the seats file and the record")
    ap.add_argument("--watch", action="store_true",
                    help="re-read every page and report any name no longer on it; writes nothing")
    args = ap.parse_args()
    if args.check:
        run_check(spec)
    elif args.watch:
        run_watch(spec)
    else:
        run_build(spec)
