#!/usr/bin/env python3
"""Generate sitemap.xml, with every lastmod read from git.

WHY THIS EXISTS. The sitemap was hand-kept, and a hand-kept `lastmod` is
correct only on the day someone types it. Measured on 2026-09-12 against each
file's own last commit, 32 of the 36 entries claimed a date OLDER than the page
they describe, median 18 days, the worst 25 (il/sources.html said 18 August and
had changed that morning). The four accurate ones were the four pages added
that day.

That is the freshness signal working against the product. This project's whole
claim is that it knows who holds a seat today; steps 5 and 8 put a visible date
and a JSON-LD dateModified on all 36 pages, and the sitemap then told crawlers
those pages had not changed since August. Several gates already READ this file
to discover pages, and not one of them looked at its dates.

WHAT IS DERIVED, AND WHY THAT IS SAFE. Everything. Inclusion, lastmod,
changefreq and priority.

  * INCLUSION: every authored .html at the repo root or in an instance folder,
    minus redirect shells (a meta refresh) and noindex pages. That rule was
    checked against the hand-kept file before this script replaced it and
    reproduced all 37 URLs with nothing extra and nothing missing, which is
    what makes generating it safe rather than a guess. It also means a new
    topic page joins the sitemap the day it ships: il/precinct.html had to be
    added by hand, and that is the last time.

  * LASTMOD: the last commit that touched the page's own file, `git log -1
    --format=%cs`. Deliberately the page's own HTML and not its data: a roster
    refresh changes data/app and not the document, and claiming the document
    changed because a JSON file did would be the same overstatement in the
    other direction. A file with no commit yet (new, unstaged) falls back to
    today and says so on stderr.

    A page MODIFIED IN THE WORKING TREE takes today's date too, for the same
    reason and against a failure this script caused on its own second outing.
    A generated sitemap is regenerated before the commit, when `git log -1`
    still answers with the date of the change BEFORE this one — so a branch
    that touched five pages and regenerated shipped their old dates, and CI
    failed on the very commit that changed them (2026-09-13, PR #933: five
    pages "2 days behind"). Regenerating after committing fixes one instance
    and leaves the trap; reading the working tree fixes the class. In CI the
    tree is clean, so this changes nothing there.

  * CHANGEFREQ and PRIORITY are per page TYPE, from the table below. Google has
    ignored both since 2023; they are kept because they were already there and
    dropping them is an editorial change, not a drift fix. The table was
    derived from the hand-kept file and reproduces all 37 rows exactly.

WHAT THE GATE COMPARES, AND WHY IT PARSES. A sitemap is a document somebody
else's parser reads, so both paths run it through one: the build refuses to
write a sitemap that is not well-formed XML, and --check fails on a shipped one
that is not, before it compares a single field. That was learned the hard way.
The header comment below carried the check flag written with its leading double
hyphen; XML forbids that sequence inside a comment, so from 2026-09-12 (PR #906,
the change that generated this file for the first time) Google, Bing and every
browser rejected the whole document and all 110 URLs with it — while this gate
stayed green, because it read the shipped file with a regex that matched each
<url> block one at a time and never asked whether the file around them parsed.
The hand-kept sitemap it replaced was well-formed; the generator broke it on its
first outing, in its own provenance note.

WHY --check TOLERATES ONE DAY AND THE BUILD DOES NOT. This repo squash-merges,
so a file's last-commit date becomes the SQUASH commit's date at merge time. A
branch that regenerates this file on one day and merges after midnight UTC would
land a sitemap one day behind its own tree, and the next push to main would fail
this gate for a reason nobody could act on. So --check fails on a lastmod that is
stale by TWO days or more, and on any difference in the URL set, changefreq or
priority. The build path always writes the exact date. One day of slack does not
weaken the thing this gate exists for: the drift it was written against ran to a
median of 18 days.

Usage:
    python3 scripts/build_sitemap.py           # rewrite sitemap.xml
    python3 scripts/build_sitemap.py --check   # fail on real drift
"""

import argparse
import datetime
import glob
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITEMAP = os.path.join(REPO, "sitemap.xml")
BASE = "https://districtry.com/"

# The flagship instance keeps priority 1.0: it is the app, and the page that
# actually answers the queries this site ranks for.
FLAGSHIP = "il"

REFRESH = re.compile(r"<meta[^>]+http-equiv=[\"']refresh", re.I)
NOINDEX = re.compile(r"<meta[^>]+name=[\"']robots[\"'][^>]+noindex", re.I)


def instances():
    """A top-level directory with its own index.html and data/app IS an
    instance — the same rule validate_card_links.py and
    validate_instance_registration.py discover by. Never a hand-kept list."""
    out = []
    for name in sorted(os.listdir(REPO)):
        d = os.path.join(REPO, name)
        if (os.path.isdir(d) and os.path.isfile(os.path.join(d, "index.html"))
                and os.path.isdir(os.path.join(d, "data", "app"))):
            out.append(name)
    return out


def page_type(rel):
    """Page type from its path, which is what changefreq and priority key off."""
    base = os.path.basename(rel)
    top = "/" not in rel
    if rel == "index.html":
        return "root"
    if base == "index.html":
        return "flagship-hub" if rel.split("/")[0] == FLAGSHIP else "hub"
    if base == "sources.html":
        return "sources"
    if base == "history.html":
        return "history"
    if top:
        return {"traffic.html": "traffic"}.get(base, "root-static")
    if rel.count("/") > 1:
        # A generated per-county page under a concept folder
        # (il/county-board/adams.html). Below the topic page that indexes it,
        # because that page is what should rank for the concept and these are
        # its 73 children.
        return "county"
    return "topic"          # faq.html and every topic page


RULES = {
    "root":         ("monthly", "0.9"),
    "flagship-hub": ("weekly",  "1.0"),
    "hub":          ("weekly",  "0.9"),
    "topic":        ("monthly", "0.7"),
    "county":       ("weekly",  "0.6"),   # its roster is re-read weekly
    "sources":      ("monthly", "0.6"),
    "history":      ("monthly", "0.5"),
    "root-static":  ("yearly",  "0.3"),   # privacy.html, sponsorship.html
    "traffic":      ("weekly",  "0.3"),
}


# Files with no commit yet, collected rather than printed one line at a time:
# adding il/county-board/ put 73 of them in one run, which buried the result.
NEW_FILES = []


def _dirty():
    """Paths modified in the working tree or staged, relative to the repo. One
    git call, cached by the caller."""
    try:
        out = subprocess.run(["git", "diff", "--name-only", "HEAD"],
                             cwd=REPO, capture_output=True, text=True,
                             timeout=30).stdout
    except Exception:                                          # noqa: BLE001
        return set()
    return {line.strip() for line in out.splitlines() if line.strip()}


def last_commit_date(rel, dirty=frozenset()):
    if rel in dirty:
        # About to be committed, so its commit date is today, not the date of
        # whatever change came before. See LASTMOD in the docstring.
        return datetime.date.today().isoformat()
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", rel],
            cwd=REPO, capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:                                          # noqa: BLE001
        out = ""
    if not out:
        NEW_FILES.append(rel)
        return datetime.date.today().isoformat()
    return out


def collect():
    dirty = _dirty()
    files = sorted(glob.glob(os.path.join(REPO, "*.html")))
    for i in instances():
        files += sorted(glob.glob(os.path.join(REPO, i, "*.html")))
        # Concept SUBDIRECTORIES too, one level deep: il/county-board/ holds 73 generated per-county pages (scripts/build_county_pages.py) and every gate here discovered pages one level up, so all 73 would have shipped unwatched — the same miss validate_card_links.py made when Iowa arrived as a fifth instance.
        files += sorted(glob.glob(os.path.join(REPO, i, "*", "*.html")))
    rows = []
    for path in files:
        rel = os.path.relpath(path, REPO)
        text = open(path, encoding="utf-8", errors="replace").read()
        if REFRESH.search(text) or NOINDEX.search(text):
            continue
        loc = BASE + (rel[:-len("index.html")] if rel.endswith("index.html") else rel)
        freq, prio = RULES[page_type(rel)]
        rows.append((loc, last_commit_date(rel, dirty), freq, prio))
    # Sitemap order is priority first, then path, so the file reads as a
    # ranking rather than as whatever order the filesystem returned.
    rows.sort(key=lambda r: (-float(r[3]), r[0]))
    return rows


HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <!-- GENERATED by scripts/build_sitemap.py — do not hand-edit.
       Inclusion is every authored .html that is neither a redirect shell nor
       noindex; lastmod is that file's own last commit; changefreq and priority
       come from the page-type table in the script. Run it after adding a page;
       CI runs it with its check flag. No double hyphen appears in this comment
       on purpose: XML forbids that sequence inside one, and a comment carrying
       it makes the whole sitemap unparseable. One did, from 2026-09-12. -->
"""


XMLNS = "http://www.sitemaps.org/schemas/sitemap/0.9"
NS = "{%s}" % XMLNS


class SitemapError(Exception):
    """A sitemap no crawler can read."""


def parse_urlset(text, label):
    """Read a sitemap the way a crawler does: {loc: (lastmod, changefreq,
    priority)}, or raise SitemapError.

    WHY A PARSER AND NOT A REGEX. --check used to read the shipped file with
    one, and that is how sitemap.xml shipped UNPARSEABLE for a day with every
    gate green (2026-09-12, PR #906): the header comment above wrote the check
    flag with its leading double hyphen, XML forbids that sequence inside a
    comment, and Google, Bing and every browser rejected the document whole
    while the regex went on matching all 110 URLs one by one. The file exists
    to be parsed by somebody else's parser, so the gate uses one.

    It is also the only guard the ill-formed class needs: render() composes XML
    by hand, and parsing the result catches a bad comment, an unescaped `&` in
    a path and a dropped tag alike, rather than this one mistake again.
    """
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise SitemapError("%s is not well-formed XML: %s" % (label, exc))
    if root.tag != NS + "urlset":
        raise SitemapError("%s root element is <%s>, expected <urlset> in %s"
                           % (label, root.tag, XMLNS))
    def field(url, name):
        return (url.findtext(NS + name) or "").strip()

    out = {}
    for url in root.findall(NS + "url"):
        out[field(url, "loc")] = (field(url, "lastmod"),
                                  field(url, "changefreq"),
                                  field(url, "priority"))
    return out


def render(rows):
    out = [HEADER]
    for loc, mod, freq, prio in rows:
        out.append("  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>\n"
                   "    <changefreq>%s</changefreq>\n    <priority>%s</priority>\n  </url>\n"
                   % (loc, mod, freq, prio))
    out.append("</urlset>\n")
    return "".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="fail if the shipped sitemap differs from the generated one")
    args = ap.parse_args()

    rows = collect()
    if NEW_FILES:
        sys.stderr.write(
            "build-sitemap: %d file(s) have no commit yet — dated today (%s%s)\n"
            % (len(NEW_FILES), ", ".join(NEW_FILES[:3]),
               ", …" if len(NEW_FILES) > 3 else ""))
    new = render(rows)
    old = open(SITEMAP, encoding="utf-8").read() if os.path.exists(SITEMAP) else ""

    if args.check:
        try:
            shipped = parse_urlset(old, "sitemap.xml")
        except SitemapError as exc:
            sys.stderr.write(
                "build-sitemap: FAIL — %s\n"
                "  Every crawler rejects the document whole, so all %d URLs are "
                "unreadable.\n"
                "  Run `python3 scripts/build_sitemap.py`.\n" % (exc, len(rows)))
            return 1
        problems = []
        for loc, mod, freq, prio in rows:
            got = shipped.get(loc)
            if got is None:
                problems.append("MISSING  %s (would be %s)" % (loc, mod))
                continue
            if (got[1], got[2]) != (freq, prio):
                problems.append("FIELDS   %s  %s/%s -> %s/%s"
                                % (loc, got[1], got[2], freq, prio))
            behind = (datetime.date.fromisoformat(mod)
                      - datetime.date.fromisoformat(got[0])).days
            if behind >= 2:
                problems.append("STALE    %s  %s -> %s  (%d days behind)"
                                % (loc, got[0], mod, behind))
        for loc in shipped:
            if loc not in {r[0] for r in rows}:
                problems.append("EXTRA    %s" % loc)
        if problems:
            sys.stderr.write(
                "build-sitemap: FAIL — sitemap.xml is out of date. "
                "Run `python3 scripts/build_sitemap.py`.\n")
            for line in problems:
                sys.stderr.write("  %s\n" % line)
            return 1
        print("build-sitemap: OK — %d URL(s), no entry stale by more than a day, "
              "URL set and fields exact" % len(rows))
        return 0

    # render() composes XML by hand, so parsing the result is the only thing
    # that proves it IS XML. The round-trip then proves the parser reads back
    # exactly what was meant — an unescaped `&` in a path would parse and say
    # something else.
    try:
        parsed = parse_urlset(new, "the generated sitemap")
    except SitemapError as exc:
        sys.stderr.write("build-sitemap: FAIL — %s\n"
                         "  sitemap.xml left as it was.\n" % exc)
        return 1
    rendered = {loc: (mod, freq, prio) for loc, mod, freq, prio in rows}
    if parsed != rendered:
        sys.stderr.write(
            "build-sitemap: FAIL — the generated sitemap parses back as "
            "something else (%d entries in, %d out).\n"
            "  sitemap.xml left as it was.\n" % (len(rendered), len(parsed)))
        for loc in sorted(set(rendered) | set(parsed)):
            if rendered.get(loc) != parsed.get(loc):
                sys.stderr.write("  DIFFERS  %s  %s -> %s\n"
                                 % (loc or "<empty loc>", rendered.get(loc),
                                    parsed.get(loc)))
        return 1

    open(SITEMAP, "w", encoding="utf-8").write(new)
    print("build-sitemap: wrote %d URL(s), well-formed XML" % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
