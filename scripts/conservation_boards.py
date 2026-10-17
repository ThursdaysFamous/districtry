#!/usr/bin/env python3
"""
Build a state's county conservation district boards for its County card: who
sits on the board of the soil and water conservation district that covers
each county, read from the one publication the state keeps of them.

    python3 <tag>/scripts/build_<tag>_conservation_boards.py            # read, parse, write
    python3 <tag>/scripts/build_<tag>_conservation_boards.py --check    # offline
    python3 <tag>/scripts/build_<tag>_conservation_boards.py --watch    # has any name changed?

Each state that uses this has a short builder of its own, which says where its
publication is, how to read it, how many members each board has, and what the
card says about how they are chosen. Everything else lives here once. Used by
ky/scripts/build_ky_conservation_boards.py,
nc/scripts/build_nc_conservation_boards.py,
sc/scripts/build_sc_conservation_boards.py and
tn/scripts/build_tn_conservation_boards.py (all 2026-10-16).

WHY THESE BOARDS. Every county in Kentucky, North Carolina, South Carolina and
Tennessee is covered by a soil and water conservation district, a unit of
government the state's own law creates, and most of each board is elected.
Those four states publish no map of any other special district, so on Adam's
choice of 2026-10-16 ("Count them") the County card names the conservation
district's board, and the done standard's special-districts level counts it.
A district follows its county's lines (North Carolina's Albemarle district
covers five whole counties, and Kentucky's Logan County is split between a
North and a South district), so the card names it without a drawn layer.

WHAT IS READ. One publication per state, read whole, because each state keeps
its boards in one place and in one format: a directory PDF (North Carolina,
Tennessee), a sheet per district linked from one page (Kentucky), or a page per
county linked from one page (South Carolina). The builder parses it and refuses
to write unless every county in the state's own county file has a board and
every board has the number of members the builder states. Unlike the city
councils, no person writes the names down: a parser that stops matching the
publication fails on the count, and the publication is the only copy there is.

WHAT IS CARRIED. A member's name exactly as published, and where the
publication gives them, the member's office on the board, whether the seat is
elected or appointed, and the term. NEVER a contact detail: the publications
also carry district offices' telephone numbers and e-mail addresses, staff
names and their e-mail addresses and mobile numbers, and (North Carolina's
commission papers, which are not read) nominees' home addresses. The parsers
read only the members' lines, and this module refuses to write a file in which
any value carries an "@" or a telephone number's shape.

A PUBLICATION THAT CANNOT BE READ KEEPS WHAT IT LAST SAID, the operator's
ruling of 2026-09-19 (a refusal stops the fetch and never unpublishes what was
fetched while it was serving). Each district carries the date its source was
last read, and a source that fails keeps its districts from the shipped file
with their old date; one that has never been read must be read.

THE FILES:
  * the app's file, <tag>/data/app/<tag>-conservation-boards.json, keyed by
    county GEOID: `{districts: [{name, members, sourceUrl, read}]}`, plus
    `dated` (the source's own date, where it has one), `counties` (every county
    a district covers, where it covers more than one) and `note` (a sentence
    the card shows). A member is `{name}` plus `role`, `chosen` ("elected" or
    "appointed"), `term` ("2022-2026") or `termEnds` ("2026" or "2027-01-31")
    where the publication gives them, and `vacant: true` (the publication says
    the seat is vacant) or `unlisted: true` (it lists the seat with no name) in
    place of a name.
  * the record, <tag>/data/source/<tag>-conservation-boards.source.json,
    written by the build: every page and document read, with its read date,
    final address, size and hash, and for each document how many boards and
    names it gave.

`--check` is offline: the app's file names every county in the state's own
county file, every district has the number of members the builder states, no
member carries a field the builder does not declare or a contact detail, every
district's source is in the record with the same read date, and the County
card in the instance's index.html says the things the builder says it must.
`--watch` re-reads every source and reports any county whose names changed,
writing nothing.
"""

import argparse
import datetime
import hashlib
import http.client
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

PACE_SECONDS = 2.0
TIMEOUT = 60
RETRY_WAITS = (10, 30)
MAX_HOPS = 8

# What a failed read raises when no HTTP status answered it: a reset, a
# timeout, a body cut short (http.client.IncompleteRead, which Kentucky's
# server sent once on 2026-10-16), too many redirects.
NETWORK_ERRORS = (urllib.error.URLError, OSError, RuntimeError, http.client.HTTPException)

DISTRICT_KEYS = {"name", "members", "sourceUrl", "read", "dated", "counties", "note"}
MEMBER_STATES = ("name", "vacant", "unlisted")
CHOSEN = ("elected", "appointed")
CONTACT_RE = re.compile(r"@|\(?\b\d{3}\)?[ .-]\d{3}[.-]\d{4}\b")


class Spec(object):
    """What a state's builder supplies.

    `index` is the page that links every document, or None where the state
    publishes one document at a fixed address (`documents`). `links(body,
    url)` turns the index into [(document url, county name or None)]. `parse(url,
    body, county)` turns one document into a list of boards, each
    {county, name, members} plus `dated`, `counties` and `note` where they
    apply; `county` is the county the index linked the document from, or None.
    `seats(board)` is how many members the board must have. `member_keys` are
    the member fields this state's publication gives, beyond the name.
    `multi` is {county name: number of districts} for a county with more than
    one. `card_claims` are sentences (or parts of one) the County card in the
    instance's index.html must contain, so the card cannot come to say
    something about how the boards are chosen that the builder does not."""

    def __init__(self, tag, label, user_agent, parse, seats, member_keys,
                 index=None, links=None, documents=(), multi=None, card_claims=()):
        self.tag = tag
        self.label = label
        self.user_agent = user_agent
        self.parse = parse
        self.seats = seats
        self.member_keys = set(member_keys)
        self.index = index
        self.links = links
        self.documents = tuple(documents)
        self.multi = dict(multi or {})
        self.card_claims = tuple(card_claims)
        instance = os.path.join(REPO_ROOT, tag)
        self.instance = instance
        self.counties_path = os.path.join(instance, "data", "app", "state-counties.json")
        self.out_path = os.path.join(instance, "data", "app", "%s-conservation-boards.json" % tag)
        self.record_path = os.path.join(instance, "data", "source",
                                        "%s-conservation-boards.source.json" % tag)
        self.index_html = os.path.join(instance, "index.html")


def fail(spec, msg):
    raise SystemExit("%s: FATAL: %s" % (spec.label, msg))


# ---------- reading ----------
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def quote_url(url):
    """An address with its spaces and commas escaped, as Kentucky's page links
    its sheets ("Conservation Districts/Adair County.pdf")."""
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(urllib.parse.unquote(parts.path), safe="/")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))


def get(spec, url):
    """GET one redirect hop at a time, reading each hop's robots.txt with the
    same client first. Returns (final url, body). A robots refusal raises
    SystemExit, as scraper_common's seam does everywhere."""
    headers = {"User-Agent": spec.user_agent}
    opener = urllib.request.build_opener(_NoRedirect)
    url = quote_url(url)
    for _hop in range(MAX_HOPS):
        sc.require_robots_once(url, spec.user_agent, headers=headers, label=spec.label)
        req = urllib.request.Request(url, headers=headers)
        try:
            with opener.open(req, timeout=TIMEOUT) as resp:
                return url, resp.read()
        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location")
            if e.code in (301, 302, 303, 307, 308) and loc:
                url = quote_url(urllib.parse.urljoin(url, loc))
                continue
            raise
    raise RuntimeError("more than %d redirects" % MAX_HOPS)


def read(spec, url):
    """(final url, body), trying twice more on a failure no HTTP status
    answered: South Carolina's department reset six of 47 connections right
    after the TLS handshake began on 2026-10-16, every one answering a later
    try, and Kentucky's cut one body short. An HTTP error is an answer and is
    not retried."""
    last = None
    for attempt in range(len(RETRY_WAITS) + 1):
        try:
            return get(spec, url)
        except urllib.error.HTTPError:
            raise
        except NETWORK_ERRORS as e:
            last = e
            if attempt < len(RETRY_WAITS):
                time.sleep(RETRY_WAITS[attempt])
    raise last


def pdf_text(body):
    """A PDF's text with its columns kept, as pdftotext -layout writes it, with
    each page break (a form feed) made a line break and the text
    compatibility-normalised (Tennessee's directory writes "Jeff" with a
    ligature)."""
    if body[:5] != b"%PDF-":
        raise RuntimeError("expected a PDF and got something else")
    try:
        done = subprocess.run(["pdftotext", "-layout", "-", "-"], input=body,
                              capture_output=True, check=True, timeout=180)
    except FileNotFoundError:
        raise RuntimeError("this source is a PDF and pdftotext (poppler-utils) is not "
                           "installed")
    text = done.stdout.decode("utf-8", "replace").replace("\f", "\n")
    return unicodedata.normalize("NFKC", text)


PDF_DATE_RE = re.compile(r"^(ModDate|CreationDate):\s+(\d{4}-\d{2}-\d{2})", re.M)


def pdf_date(body):
    """The date the PDF file was last changed (its ModDate, else its
    CreationDate), or None. The file's own metadata, which says when the file
    was made and not when anyone checked the names in it."""
    try:
        done = subprocess.run(["pdfinfo", "-isodates", "-"], input=body,
                              capture_output=True, check=True, timeout=60)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    dates = dict(PDF_DATE_RE.findall(done.stdout.decode("utf-8", "replace")))
    return dates.get("ModDate") or dates.get("CreationDate")


def clean(text):
    """One line of published text, compatibility-normalised (Tennessee's PDF
    writes "Jeff" with a ligature) and with its spaces collapsed."""
    return " ".join(unicodedata.normalize("NFKC", text or "").split())


# ---------- the state's counties ----------
def load_counties(spec):
    """{county name as the Census's BASENAME: GEOID}."""
    with open(spec.counties_path, encoding="utf-8") as fh:
        feats = json.load(fh)["features"]
    return {f["properties"]["BASENAME"]: f["properties"]["GEOID"] for f in feats}


def county_key(name):
    """Compare county names without case, accents, punctuation or spacing, so
    "DeKalb" matches "Dekalb" and "McNairy" matches "Mc Nairy"."""
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z]", "", text.casefold())


# ---------- checking what a parse gave ----------
def check_boards(spec, boards, counties):
    """Problems with a parse, before anything is written: every county has
    its boards, each board its members, and no value a contact detail."""
    problems = []
    by_key = {county_key(n): n for n in counties}
    seen = {}
    for b in boards:
        name = by_key.get(county_key(b.get("county") or ""))
        if not name:
            problems.append("a board names county %r, which is not in %s"
                            % (b.get("county"), os.path.relpath(spec.counties_path, REPO_ROOT)))
            continue
        seen.setdefault(name, []).append(b)
        problems += check_board(spec, b, name)
    for name in sorted(counties):
        want = spec.multi.get(name, 1)
        got = len(seen.get(name, []))
        if got != want:
            problems.append("%s County has %d conservation district%s in this parse and the "
                            "builder states %d" % (name, got, "" if got == 1 else "s", want))
    return problems


def check_board(spec, b, where):
    problems = []
    if not isinstance(b.get("name"), str) or not b["name"].strip():
        problems.append("%s: a board has no district name" % where)
    members = b.get("members") or []
    want = spec.seats(b)
    if len(members) != want:
        problems.append("%s: %s lists %d members and the builder states %d"
                        % (where, b.get("name"), len(members), want))
    allowed = spec.member_keys | set(MEMBER_STATES)
    for m in members:
        odd = set(m) - allowed
        if odd:
            problems.append("%s: a member carries fields this state's builder does not "
                            "declare: %s" % (where, ", ".join(sorted(odd))))
        states = [k for k in MEMBER_STATES if k in m]
        if len(states) != 1:
            problems.append("%s: a member must carry exactly one of name, vacant and "
                            "unlisted, and carries %s: %r"
                            % (where, ", ".join(states) or "none", m))
        if "name" in m:
            n = m["name"]
            if not isinstance(n, str) or not n.strip() or n != n.strip():
                problems.append("%s: a member's name is empty or padded: %r" % (where, n))
            elif re.search(r"[0-9]", n) or n.casefold() in ("vacant", "tbd", "none"):
                problems.append("%s: %r is not a person's name" % (where, n))
        for key in ("vacant", "unlisted"):
            if key in m and m[key] is not True:
                problems.append("%s: %s must be true where it is set: %r" % (where, key, m))
        if "chosen" in m and m["chosen"] not in CHOSEN:
            problems.append("%s: chosen must be elected or appointed: %r" % (where, m))
        if "term" in m and not re.fullmatch(r"20\d\d-20\d\d", str(m["term"])):
            problems.append("%s: a term must read like 2022-2026: %r" % (where, m))
        if "termEnds" in m and not re.fullmatch(r"20\d\d(-\d\d-\d\d)?", str(m["termEnds"])):
            problems.append("%s: termEnds must be a year or a date: %r" % (where, m))
    for value in strings_in(b):
        if CONTACT_RE.search(value):
            problems.append("%s: %r looks like a contact detail, which this file never "
                            "carries" % (where, value))
    return problems


def strings_in(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            for s in strings_in(v):
                yield s
    elif isinstance(obj, list):
        for v in obj:
            for s in strings_in(v):
                yield s


# ---------- the record and the app's file ----------
def dumps(doc):
    return json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def record_doc(index, documents):
    return {
        "_about": ("Written by the builder, never by hand: every page and document read "
                   "for this file, the date it was last read, the address it ended at, "
                   "its size and hash, and for each document how many boards and names "
                   "it gave."),
        "index": index,
        "documents": documents,
    }


def district_entry(b, url, read_on):
    entry = {"name": b["name"], "members": b["members"], "sourceUrl": url, "read": read_on}
    for key in ("dated", "counties", "note"):
        if b.get(key):
            entry[key] = b[key]
    return entry


def names_of(entry):
    return sorted(m.get("name") or ("(vacant)" if m.get("vacant") else "(not listed)")
                  for d in entry.get("districts") or [] for m in d.get("members") or [])


# ---------- the build ----------
def discover(spec, prior_record):
    """[(document url, county or None)], and the index's record entry. An
    index that cannot be read falls back to the documents the last build read,
    so a failed index does not unpublish anything."""
    if not spec.index:
        return [(u, None) for u in spec.documents], {}
    try:
        final, body = read(spec, spec.index)
    except SystemExit as e:
        return fallback_documents(spec, prior_record, "robots.txt refused this client: %s" % e)
    except NETWORK_ERRORS as e:
        return fallback_documents(spec, prior_record, "%s: %s" % (type(e).__name__, e))
    found = spec.links(body.decode("utf-8", "replace"), final)
    entry = {spec.index: {"read": datetime.date.today().isoformat(), "final": final,
                          "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                          "documents": len(found)}}
    print("%s: read %s (%d bytes): %d documents linked" % (spec.label, spec.index, len(body),
                                                           len(found)))
    return found, entry


def fallback_documents(spec, prior_record, why):
    docs = prior_record.get("documents") or {}
    if not docs:
        fail(spec, "the index %s could not be read and has never been read: %s"
             % (spec.index, why))
    print("%s: NOT READ %s (%s); reading the %d documents the last build found there"
          % (spec.label, spec.index, why, len(docs)))
    return [(u, d.get("county")) for u, d in sorted(docs.items())], prior_record.get("index") or {}


def run_build(spec):
    counties = load_counties(spec)
    prior_record = load_json(spec.record_path, {})
    shipped = load_json(spec.out_path, {})
    found, index_entry = discover(spec, prior_record)
    today = datetime.date.today().isoformat()
    documents, boards, carried, problems = {}, [], [], []
    for i, (url, county) in enumerate(found):
        if i:
            time.sleep(PACE_SECONDS)
        key = quote_url(url)
        try:
            final, body = read(spec, url)
        except SystemExit as e:
            problems.append((key, "robots.txt refused this client: %s" % e))
            continue
        except NETWORK_ERRORS as e:
            problems.append((key, "%s: %s" % (type(e).__name__, e)))
            continue
        got = spec.parse(key, body, county)
        names = sum(1 for b in got for m in b["members"] if "name" in m)
        documents[key] = {"read": today, "final": final, "bytes": len(body),
                          "sha256": hashlib.sha256(body).hexdigest(), "boards": len(got),
                          "names": names}
        if county:
            documents[key]["county"] = county
        for b in got:
            b["_url"] = key
        boards += got
        print("%s: read %s (%d bytes): %d board%s, %d names"
              % (spec.label, key, len(body), len(got), "" if len(got) == 1 else "s", names))
    # A document that could not be read keeps the districts it gave last time.
    unread = []
    for key, why in problems:
        old = (prior_record.get("documents") or {}).get(key)
        kept = [(g, d) for g, e in shipped.items() for d in e.get("districts") or []
                if d.get("sourceUrl") == key]
        if not old or not kept:
            unread.append("%s could not be read and has never been read: %s" % (key, why))
            continue
        documents[key] = old
        carried.append(key)
        for geoid, d in kept:
            county = next(n for n, g in counties.items() if g == geoid)
            b = {"county": county, "name": d["name"], "members": d["members"],
                 "_url": key, "_read": d["read"]}
            for k in ("dated", "counties", "note"):
                if d.get(k):
                    b[k] = d[k]
            boards.append(b)
        print("%s: NOT READ %s (%s); keeping what it said on %s" % (spec.label, key, why,
                                                                   old.get("read")))
    if unread:
        fail(spec, "; ".join(unread))
    report(spec, check_boards(spec, boards, counties), "build")
    out = {}
    for b in boards:
        geoid = counties[next(n for n in counties if county_key(n) == county_key(b["county"]))]
        entry = district_entry(b, b["_url"], b.get("_read") or documents[b["_url"]]["read"])
        out.setdefault(geoid, {"districts": []})["districts"].append(entry)
    for entry in out.values():
        entry["districts"].sort(key=lambda d: d["name"])
    with open(spec.record_path, "w", encoding="utf-8") as fh:
        fh.write(dumps(record_doc(index_entry, documents)))
    with open(spec.out_path, "w", encoding="utf-8") as fh:
        fh.write(dumps(out))
    changed = sorted(g for g in set(out) | set(shipped)
                     if names_of(out.get(g, {})) != names_of(shipped.get(g, {})))
    print("wrote %s: %s" % (os.path.relpath(spec.out_path, REPO_ROOT), summary(out)))
    if shipped and changed:
        print("%s: names changed in %d counties since the last build: %s"
              % (spec.label, len(changed), ", ".join(changed)))


def summary(out):
    districts = [d for e in out.values() for d in e["districts"]]
    members = [m for d in districts for m in d["members"]]
    named = sum(1 for m in members if "name" in m)
    return ("%d counties, %d districts, %d seats, %d named, %d vacant, %d listed with no name"
            % (len(out), len(districts), len(members), named,
               sum(1 for m in members if m.get("vacant")),
               sum(1 for m in members if m.get("unlisted"))))


# ---------- the offline check and the watch ----------
def report(spec, problems, mode):
    for p in problems:
        print("%s %s: FAIL: %s" % (spec.label, mode, p))
    if problems:
        raise SystemExit(1)


def run_check(spec):
    counties = load_counties(spec)
    by_geoid = {g: n for n, g in counties.items()}
    out = load_json(spec.out_path, None)
    record = load_json(spec.record_path, None)
    problems = []
    if out is None:
        fail(spec, "%s does not exist; run the build" % os.path.relpath(spec.out_path, REPO_ROOT))
    if record is None:
        fail(spec, "%s does not exist; run the build"
             % os.path.relpath(spec.record_path, REPO_ROOT))
    with open(spec.out_path, encoding="utf-8") as fh:
        if fh.read() != dumps(out):
            problems.append("%s is not written the way the build writes it; run the build "
                            "rather than editing it by hand"
                            % os.path.relpath(spec.out_path, REPO_ROOT))
    missing = sorted(set(by_geoid) - set(out))
    extra = sorted(set(out) - set(by_geoid))
    if missing:
        problems.append("no board for %s" % ", ".join("%s (%s)" % (by_geoid[g], g)
                                                      for g in missing))
    if extra:
        problems.append("boards keyed to %s, which is not a county in %s"
                        % (", ".join(extra), os.path.relpath(spec.counties_path, REPO_ROOT)))
    docs = record.get("documents") or {}
    boards = []
    for geoid, entry in sorted(out.items()):
        if set(entry) != {"districts"}:
            problems.append("%s: a county entry carries %s" % (geoid, sorted(entry)))
        for d in entry.get("districts") or []:
            odd = set(d) - DISTRICT_KEYS
            if odd:
                problems.append("%s: a district carries %s" % (geoid, ", ".join(sorted(odd))))
            url = d.get("sourceUrl")
            if not (isinstance(url, str) and url.startswith("https://")):
                problems.append("%s: %s cites no https source" % (geoid, d.get("name")))
            elif url not in docs:
                problems.append("%s: %s cites %s, which the record has never read"
                                % (geoid, d.get("name"), url))
            elif docs[url].get("read") != d.get("read"):
                problems.append("%s: %s says it was read on %s and the record says %s"
                                % (geoid, d.get("name"), d.get("read"), docs[url].get("read")))
            b = dict(d, county=by_geoid.get(geoid, geoid))
            boards.append(b)
    problems += check_boards(spec, boards, counties)
    used = {d.get("sourceUrl") for e in out.values() for d in e.get("districts") or []}
    for url in sorted(set(docs) - used):
        problems.append("the record holds %s, which no district cites; run the build" % url)
    with open(spec.index_html, encoding="utf-8") as fh:
        page = fh.read()
    for claim in spec.card_claims:
        if claim not in page:
            problems.append("%s's County card no longer says %r, which this builder says it "
                            "must" % (os.path.relpath(spec.index_html, REPO_ROOT), claim))
    report(spec, problems, "--check")
    reads = sorted(d["read"] for e in out.values() for d in e["districts"])
    print("%s --check: OK — %s (sources read %s to %s)"
          % (spec.label, summary(out), reads[0], reads[-1]))


def run_watch(spec):
    counties = load_counties(spec)
    shipped = load_json(spec.out_path, {})
    prior_record = load_json(spec.record_path, {})
    found, _index = discover(spec, prior_record)
    fresh, unread = {}, []
    for i, (url, county) in enumerate(found):
        if i:
            time.sleep(PACE_SECONDS)
        key = quote_url(url)
        try:
            _final, body = read(spec, url)
        except (SystemExit,) + NETWORK_ERRORS as e:
            unread.append("%s: %s" % (key, e))
            continue
        for b in spec.parse(key, body, county):
            name = next((n for n in counties if county_key(n) == county_key(b["county"])), None)
            if name:
                fresh.setdefault(counties[name], {"districts": []})["districts"].append(b)
    changed = sorted(g for g in fresh if names_of(fresh[g]) != names_of(shipped.get(g, {})))
    for geoid in changed:
        name = next(n for n, g in counties.items() if g == geoid)
        gone = sorted(set(names_of(shipped.get(geoid, {}))) - set(names_of(fresh[geoid])))
        new = sorted(set(names_of(fresh[geoid])) - set(names_of(shipped.get(geoid, {}))))
        print("%s --watch: %s County changed: %s%s"
              % (spec.label, name, ("gone " + ", ".join(gone)) if gone else "",
                 ("%snew %s" % ("; " if gone else "", ", ".join(new))) if new else ""))
    for msg in unread:
        print("%s --watch: NOT READ %s" % (spec.label, msg))
    if changed or unread:
        print("%s --watch: run the build to bring the file up to date" % spec.label)
        raise SystemExit(1)
    print("%s --watch: no names changed (%d sources read)" % (spec.label, len(found)))


def main(spec, doc):
    ap = argparse.ArgumentParser(description=(doc or "").strip().split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the app's file to the record, the counties and the card")
    ap.add_argument("--watch", action="store_true",
                    help="re-read every source and report any county whose names changed; "
                         "writes nothing")
    args = ap.parse_args()
    if args.check:
        run_check(spec)
    elif args.watch:
        run_watch(spec)
    else:
        run_build(spec)
