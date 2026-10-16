#!/usr/bin/env python3
"""
Build tn/data/app/tn-judicial-districts.json: Tennessee's 32 judicial
districts, each a group of whole counties, dissolved from the shipped county
fabric.

    python3 tn/scripts/build_tn_judicial_districts.py          # writes (needs shapely)
    python3 tn/scripts/build_tn_judicial_districts.py --check  # offline, stdlib only

The dissolve, the partition gate and the offline check are
scripts/whole_county_courts.py, shared with the other states; this file says
where Tennessee's county lists come from and how they are read.

WHAT A JUDICIAL DISTRICT IS. Tennessee's trial courts are divided into 32
judicial districts. Circuit and chancery courts sit in each, and some districts
have separate criminal courts. Circuit judges and chancellors are elected to
eight-year terms by the voters of the district (CTAS, "Trial Courts", citing
Tenn. Const. art. VI, sec. 4). Each district also has one district attorney
general.

THE STATUTE WAS NOT READ, which is why the county lists come from the
district attorneys. The districts are set in the Tennessee Code, whose public
copy is published by LexisNexis rather than by the state; the General
Assembly's own site (capitol.tn.gov) admits eight named search and archive
crawlers in its robots.txt and refuses every other client, this project's
included; and the courts' site (tncourts.gov) answers with a managed
challenge, which this project never works around. Measured 2026-10-15/16 and
recorded as a data-publishing hurdle.

THREE SOURCES, ONE ANSWER. All three were read 2026-10-16 and are kept in
tn/data/source/courts/ with their addresses (see its README):

  1. The District Attorneys General Conference's own county selector, which
     sends each of the 95 counties to its district's page. This is what the
     build reads, because it is the only one that names every county.
  2. Each district's own page, which says which counties it serves. All 31
     pages read must name exactly the selector's counties. District 2's page
     leads to the district attorney's own site, whose robots.txt answered HTTP
     521, so it was not read; that is the one declared absence.
  3. The Comptroller's FY2019 judicial map. It must agree with the selector in
     every district but one: its 21st is today's 21st and 32nd together, the
     32nd having been created after that map. Any other difference stops the
     build, because it would mean one of the two lists is wrong.
"""

import argparse
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts"))

import whole_county_courts as wcc  # noqa: E402  (FLEET_SHARED)

LABEL = "build-tn-judicial-districts"
SOURCE = os.path.join(os.path.dirname(_HERE), "data", "source", "courts")
SELECTOR = "tndagc-county-selector.tsv"
PAGES = "tndagc-district-pages.tsv"
OREA = "orea-fy2019-judicial-districts.txt"
DISTRICTS = 32
COUNTIES = 95
# The one district whose own page was not read, and why (see PAGES's header).
PAGES_NOT_READ = {2}
# The one change since the Comptroller's FY2019 map: its 21st is split.
SPLIT_SINCE_2019 = {21: (21, 32)}
PAGE_URL = re.compile(r"^https://tennesseeda\.gov/district-(\d+)/$")
# The sentence shapes the district pages use to name their counties, measured
# 2026-10-16 on all 31 pages read. A page in any other shape stops the build.
SENTENCES = (
    re.compile(r"^Serving (.*) Count(?:y|ies) \| Tennessee$"),
    re.compile(r"^The \d+(?:st|nd|rd|th) Judicial District includes (.*) Counties\.$"),
    re.compile(r"criminal cases that occur within (.*) County\.$"),
    re.compile(r"within Metropolitan Nashville and (Davidson) County$"),
    re.compile(r"residents across (.*) County\.$"),
)


def lines(name):
    with open(os.path.join(SOURCE, name)) as fh:
        return [ln.rstrip("\n") for ln in fh if ln.strip() and not ln.startswith("#")]


def split_names(text):
    return sorted(p.strip() for p in re.split(r",\s*(?:and\s+)?|\s+and\s+", text)
                  if p.strip())


def read_selector():
    """{district: [county, ...]} and {district: page url} from the selector."""
    by, urls = {}, {}
    for ln in lines(SELECTOR):
        county, url = ln.split("\t")
        m = PAGE_URL.match(url)
        if not m:
            wcc.fail(LABEL, "the selector sends %s to %r, which is not a district "
                     "page" % (county, url))
        d = int(m.group(1))
        by.setdefault(d, []).append(county)
        urls[d] = url
    if sum(len(v) for v in by.values()) != COUNTIES:
        wcc.fail(LABEL, "the selector names %d counties, expected %d"
                 % (sum(len(v) for v in by.values()), COUNTIES))
    return by, urls


def check_pages(by):
    read = {}
    for ln in lines(PAGES):
        d, _requested, _served, sentence = ln.split("\t")
        for pat in SENTENCES:
            m = pat.search(sentence)
            if m:
                read[int(d)] = split_names(m.group(1))
                break
        else:
            wcc.fail(LABEL, "district %s's page sentence is in a shape this "
                     "builder does not read: %r" % (d, sentence))
    absent = set(by) - set(read)
    if absent != PAGES_NOT_READ:
        wcc.fail(LABEL, "district pages not read: %s, and %s is declared"
                 % (sorted(absent), sorted(PAGES_NOT_READ)))
    for d, names in sorted(read.items()):
        if names != sorted(by.get(d, [])):
            wcc.fail(LABEL, "district %d's own page names %s and the selector "
                     "sends %s there" % (d, names, sorted(by.get(d, []))))
    return len(read)


def check_orea(by):
    orea = {}
    for ln in lines(OREA):
        m = re.match(r"^District (\d+) \((.*)\)$", ln)
        if not m:
            wcc.fail(LABEL, "%s: unreadable line %r" % (OREA, ln))
        orea[int(m.group(1))] = split_names(m.group(2))
    expected = {}
    for d, names in by.items():
        target = d
        for old, parts in SPLIT_SINCE_2019.items():
            if d in parts:
                target = old
        expected.setdefault(target, []).extend(names)
    expected = {d: sorted(v) for d, v in expected.items()}
    if orea != expected:
        diff = sorted(d for d in set(orea) | set(expected)
                      if orea.get(d) != expected.get(d))
        wcc.fail(LABEL, "the Comptroller's FY2019 map and today's selector differ "
                 "beyond the one recorded split, in district(s) %s" % diff)


def tilings():
    by, urls = read_selector()
    if sorted(by) != list(range(1, DISTRICTS + 1)):
        wcc.fail(LABEL, "the selector names districts %s, expected 1 to %d"
                 % (sorted(by), DISTRICTS))
    pages = check_pages(by)
    check_orea(by)
    print("%s: the selector's %d counties in %d districts agree with %d district "
          "pages and with the Comptroller's FY2019 map apart from the 21st's split"
          % (LABEL, COUNTIES, len(by), pages))
    rows = [(d, by[d], {"url": urls[d]}) for d in sorted(by)]
    return [wcc.Tiling("tn-judicial-districts.json", "judicial district", rows,
                       DISTRICTS,
                       "The Tennessee District Attorneys General Conference's list "
                       "of the counties each district attorney serves, read 16 "
                       "October 2026")]


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped file, write nothing")
    args = ap.parse_args()
    if args.check:
        wcc.check("tn", LABEL, tilings())
        print("%s: OK" % LABEL)
    else:
        wcc.build("tn", LABEL, tilings())


if __name__ == "__main__":
    main()
