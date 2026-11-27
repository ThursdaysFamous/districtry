#!/usr/bin/env python3
"""
Build oh/data/app/oh-county-commissioners.json: who sits on each of Ohio's 88
county governments, written down by hand from each county's own website and
proved against it on every build.

    python3 oh/scripts/build_oh_county_commissioners.py          # read every page, prove every name, write
    python3 oh/scripts/build_oh_county_commissioners.py --check  # offline, writes nothing

WHO GOVERNS AN OHIO COUNTY. Eighty-six counties are governed by a board of
three commissioners, each elected by the whole county to a four-year term
(Ohio Revised Code 305.01): two are elected in the presidential year and take
office on 2 and 3 January, and one is elected in the year between and takes
office on 1 January. So one seat in every one of those counties was on the
ballot on 3 November 2026 and its winner takes office on 1 January 2027, and
the card says one name may change then. Cuyahoga and Summit are governed under
charters by an elected county executive and a county council: Cuyahoga's 11
members are each elected from a district, Summit's 8 from districts and 3 by
the whole county. This app draws neither council's districts, so a card there
names the executive and any at-large members and links the council's own page
for the rest.

WHERE THE NAMES COME FROM. Each county's own website. No state office lists
Ohio's county commissioners: the Secretary of State lists county boards of
elections, and the County Commissioners Association of Ohio's yearly roster is
an association's publication, used only to find each county's website and to
cross-check, never as a source of a name. The seats file,
oh/data/source/oh-county-commissioner-seats.json, holds each county's page and
the names it prints, and this build re-reads every page and refuses to write
unless every name is on it, with the proof scripts/city_councils.py uses (a
name's words whole and in order in the page's text, both normalised alike).
The page's text here also takes in the pictures' alt text, because Champaign
County's page names its commissioners only under their photographs.

THREE PAGES ARE READ IN THEIR OWN SCRIPT FILE. Carroll's and Scioto's sites,
and Jefferson's commissioners page, are single-page programs whose HTML holds
no name: each page loads a script file that carries the names, and the file's
name changes when the site is rebuilt. So the seat carries a pattern
(`bundle`), and the build finds the file the page loads now and proves the
names in it (the read-the-page-first rule in CLAUDE.md).

FOUR PAGES WERE READ BY HAND IN ADAM'S CHROME (Adam, 2026-11-25: one-off
reads of a public page that refuses automated readers). Greene's, Montgomery's
and Portage's sites answer this project's reader with HTTP 403, and Pike's
fills its page in with a WebAssembly program and a POST feed. Each read is
kept as a dated excerpt in oh/data/source/commissioners/, the build proves
those names against the excerpt and does not fetch the page, and the card says
the page was read by hand on that date. Never a weekly source.

ONE PAGE IS CARRIED FROM THIS PROJECT'S OWN EARLIER READ. Adams County's
page was read by this project's reader earlier on 2026-11-27, and later
that day the site's robots.txt answered with a managed challenge, an
access control that is never worked around. A refusal never unpublishes what
was read while the page was serving (Adam, 2026-09-19), so that read is kept
as a dated excerpt (`readBy: reader`) and proved the same way.

THREE COUNTIES NAME NOBODY, each for the reason in its `unnamed` sentence,
which the card prints: Ashland (its certificate had expired), Holmes (a
captcha) and Lawrence (no county website names them).

WHAT IS NOT CARRIED. Contacts, roles and terms: the card names the members
and links the county's page. The county's other elected officers (auditor,
treasurer, prosecutor and the rest) are not named; gap oh-county-officials.

A PAGE THAT CANNOT BE READ STOPS THE BUILD, and the file already shipped stays
as it is (Adam, 2026-09-19: a refusal never unpublishes what we have).
shortcut: no per-county carry-forward or --watch mode; add them when this gets
a scheduled re-read (the re-read after 1 January 2027 is a row in oh/WATCH.md).
"""

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
sys.path.insert(0, os.path.join(REPO, "scripts"))

import city_councils as cc  # noqa: E402
import scraper_common as sc  # noqa: E402

LABEL = "build-oh-county-commissioners"
SEATS = os.path.join(INSTANCE, "data", "source", "oh-county-commissioner-seats.json")
SOURCE_DIR = os.path.join(INSTANCE, "data", "source")
COUNTIES = os.path.join(INSTANCE, "data", "app", "state-counties.json")
OUT = os.path.join(INSTANCE, "data", "app", "oh-county-commissioners.json")
HEADERS = dict(sc.UA_HEADERS_ROSTER_BOT)
CHARTER = {"Cuyahoga", "Summit"}
MIN_NAMED = 83  # measured 2026-11-27: 83 boards named, 3 counties unnamed, 2 charter counties
JS_QUOTES_RE = re.compile(r"[`'\"]")
ALT_RE = re.compile(r"""(?is)\balt\s*=\s*(?:"([^"]*)"|'([^']*)')""")
SEAT_KEYS = {"page", "names", "as", "bundle", "excerpt", "readBy", "why", "unnamed", "charter"}
CHARTER_KEYS = {"body", "executive", "executivePage", "councilPage", "districtSeats", "atLarge"}


class Spec(object):
    label = LABEL


def fail(msg):
    sys.exit("%s: FAIL — %s" % (LABEL, msg))


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def county_geoids():
    out = {}
    for f in load(COUNTIES)["features"]:
        p = f["properties"]
        out[p["BASENAME"]] = p["GEOID"]
    if len(out) != 88:
        fail("state-counties.json carries %d counties, not Ohio's 88" % len(out))
    return out


def check_seats(seats, geoids):
    counties = seats.get("counties") or {}
    if set(counties) != set(geoids):
        fail("the seats file's counties differ from state-counties.json: missing %s, extra %s"
             % (sorted(set(geoids) - set(counties)), sorted(set(counties) - set(geoids))))
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", seats.get("read") or ""):
        fail("the seats file carries no read date")
    for name, rec in counties.items():
        bad = set(rec) - SEAT_KEYS
        if bad:
            fail("%s carries keys this build does not know: %s" % (name, sorted(bad)))
        if name in CHARTER:
            ch = rec.get("charter") or {}
            if set(ch) != CHARTER_KEYS or not ch["executive"] or not isinstance(ch["atLarge"], list):
                fail("%s is a charter county and its record is not one" % name)
            continue
        if rec.get("charter"):
            fail("%s is not a charter county" % name)
        if rec.get("unnamed"):
            if rec.get("names"):
                fail("%s both names people and says it names nobody" % name)
            continue
        names = rec.get("names") or []
        if len(names) != 3 or len(set(names)) != 3:
            fail("%s names %d commissioners, not three" % (name, len(names)))
        if not str(rec.get("page") or "").startswith(("https://", "http://")):
            fail("%s carries no page" % name)
        for spelt in (rec.get("as") or {}):
            if spelt not in names:
                fail("%s spells %r on its page and names no such person" % (name, spelt))
        if rec.get("excerpt") and not (rec.get("readBy") in ("hand", "reader")
                                       and rec.get("why")):
            fail("%s is proved against an excerpt and says neither who read it "
                 "(hand or reader) nor why" % name)


def proof_of(rec, name):
    return (rec.get("as") or {}).get(name, name)


def text_of(body):
    raw = body.decode("utf-8", "replace")
    alts = " ".join(html.unescape(a or b) for a, b in ALT_RE.findall(raw))
    return cc.page_text(body) + "\n" + alts


def read_page(county, rec):
    """The text a county's names are proved in: its page (and the script file
    the page loads, where the seat says so), or the hand-read excerpt."""
    if rec.get("excerpt"):
        with open(os.path.join(SOURCE_DIR, rec["excerpt"]), encoding="utf-8") as fh:
            return fh.read()
    url, body = cc.get(Spec, rec["page"], HEADERS)
    text = text_of(body)
    if rec.get("bundle"):
        found = re.findall(rec["bundle"], body.decode("utf-8", "replace"))
        if len(set(found)) != 1:
            fail("%s: the page loads %d script files matching %r, not one"
                 % (county, len(set(found)), rec["bundle"]))
        time.sleep(cc.PACE_SECONDS)
        _u, js = cc.get(Spec, urllib.parse.urljoin(url, found[0]), HEADERS)
        # a script quotes its strings with backticks and quote marks, which the
        # proof would otherwise read as part of the first and last word
        text += "\n" + JS_QUOTES_RE.sub(" ", cc.page_text(js))
    return text


def prove(seats, offline):
    """Every name on its page; offline, only the hand-read excerpts."""
    missing, unread = [], []
    for county, rec in sorted(seats["counties"].items()):
        if county in CHARTER or rec.get("unnamed"):
            continue
        if offline and not rec.get("excerpt"):
            continue
        try:
            text = cc.norm(read_page(county, rec))
        except (OSError, SystemExit) as e:
            # a refusal or a dropped connection is reported with the others
            # at the end, and nothing is written
            unread.append("%s (%s)" % (county, str(e).splitlines()[0][:120]))
            continue
        for name in rec["names"]:
            if not cc.on_page(proof_of(rec, name), text):
                missing.append("%s: %s" % (county, name))
        if not offline:
            time.sleep(cc.PACE_SECONDS)
    for county in sorted(CHARTER):
        if offline:
            continue
        ch = seats["counties"][county]["charter"]
        for page, names in ((ch["executivePage"], [ch["executive"]]),
                            (ch["councilPage"], ch["atLarge"])):
            if not names:
                continue
            try:
                _u, body = cc.get(Spec, page, HEADERS)
            except (OSError, SystemExit) as e:
                unread.append("%s (%s)" % (county, str(e).splitlines()[0][:120]))
                continue
            text = cc.norm(text_of(body))
            missing += ["%s: %s" % (county, n) for n in names if not cc.on_page(n, text)]
            time.sleep(cc.PACE_SECONDS)
    if missing or unread:
        fail("%d name(s) are not on the page their county cites: %s. %d page(s) "
             "could not be read: %s" % (len(missing), "; ".join(missing) or "none",
                                        len(unread), "; ".join(unread) or "none"))


def build(seats, geoids):
    out = {}
    read = seats["read"]
    for county, rec in sorted(seats["counties"].items()):
        entry = {"county": county + " County", "read": read}
        if county in CHARTER:
            ch = rec["charter"]
            entry.update(kind="charter", body=ch["body"], executive=ch["executive"],
                         executiveUrl=ch["executivePage"], councilUrl=ch["councilPage"],
                         districtSeats=ch["districtSeats"], atLarge=list(ch["atLarge"]))
        elif rec.get("unnamed"):
            entry.update(kind="commissioners", members=[], unnamed=rec["unnamed"])
            if rec.get("page"):
                entry["sourceUrl"] = rec["page"]
        else:
            entry.update(kind="commissioners", members=list(rec["names"]),
                         sourceUrl=rec["page"])
            if rec.get("readBy") == "hand":
                entry["readByHand"] = True
        out[geoids[county]] = entry
    named = sum(1 for e in out.values() if e.get("members"))
    if named < MIN_NAMED:
        fail("only %d counties name their commissioners, below the floor of %d"
             % (named, MIN_NAMED))
    return out


def dump(obj):
    return json.dumps(obj, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: the shipped file is what the seats file builds, and "
                         "every hand-read name is in its excerpt")
    args = ap.parse_args()
    geoids = county_geoids()
    seats = load(SEATS)
    check_seats(seats, geoids)
    prove(seats, offline=args.check)
    want = dump(build(seats, geoids))
    if args.check:
        have = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if have != want:
            fail("%s is not what the seats file builds; run this script without --check"
                 % os.path.relpath(OUT, REPO))
        print("%s: OK — 88 counties, every hand-read name in its excerpt" % LABEL)
        return
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(want)
    print("%s: wrote %s" % (LABEL, os.path.relpath(OUT, REPO)))


if __name__ == "__main__":
    main()
