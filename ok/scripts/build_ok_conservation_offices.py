#!/usr/bin/env python3
"""
Build ok/data/app/ok-conservation-offices.json: the office of each of
Oklahoma's conservation districts, from the Oklahoma Conservation
Commission's directory of district offices.

    python3 ok/scripts/build_ok_conservation_offices.py              # fetch, check, write
    python3 ok/scripts/build_ok_conservation_offices.py --source F   # parse a saved copy
    python3 ok/scripts/build_ok_conservation_offices.py --check      # offline

THE SOURCE. One page on conservation.ok.gov, "Conservation District Offices
Directory", which the Commission edits often (the copy read on 2026-10-16
carries a modified date of 15 October 2026). It lists 84 district offices
under the Commission's five areas, each with the district's name, its
office's address, a telephone number, often a fax number, the district's
e-mail address at conservation.ok.gov and, for a few, a website or a
Facebook page.

WHAT IS CARRIED: the district's name as the directory gives it, the office's
address as printed (a post office box with the street address in brackets
where the directory gives both, and a separate mailing address where it
gives one), the telephone number and its extension, the e-mail address and
the website. WHAT IS NOT: fax numbers, and Facebook pages, which are a
district's own posts rather than its office (and one entry's "Facebook" link
is its website). Every e-mail address is checked to be the district's at
conservation.ok.gov, so no one's personal address is carried. Two of the five
websites the directory links reach nobody (WEBSITE_DROPS): one name has no
DNS record and one domain is parked, so the card links neither.

THE DIRECTORY NAMES NO DIRECTOR. Each district is governed by five directors
(27A O.S. § 3-3-201), and the Commission issues every director's certificate
of election or appointment (§ 3-3-201 C, § 3-3-304 G) and keeps the list of
directors whose terms expire each year (its April 2024 training note on
director elections). Its meeting packets name directors a few at a time, as
they are appointed or elected; no page or file names each district's five.
So the card names no one, and the gap is recorded as
ok-conservation-district-directors, the evidence for the state-publishing
ask.

THE JOIN. The directory carries no district number, so each entry is joined
to the map (ok/scripts/build_ok_conservation_districts.py) by its name, with
"Conservation District" and "CD" taken off both sides: 83 of the 84 match
that way and NAME_JOIN gives the one that does not (the map shortens Central
North Canadian River to Central North Canadian). Every drawn district must
have exactly one entry, and every entry one district, or the build stops.
NAME_FIXES lists the two names the directory prints with a word missing or
a note added, with what the card shows; an entry stops the build once the
directory changes it.

THE TERMS. The directory page states no licence of its own, so the website's
general terms of use govern it (https://conservation.ok.gov/terms-of-use/,
modified 30 July 2021, read 2026-10-16). They say the site's "source code,
databases, functionality, software, website designs, audio, video, text,
photographs, and graphics" are "protected by copyright and trademark laws"
(6.1); that no part may be "copied, reproduced, aggregated, republished ...
or otherwise exploited for any commercial purpose whatsoever, without our
express prior written permission" (6.2); and they grant a licence to read,
download or print the content "solely for your personal, non-commercial use"
(6.3). They are a stock template rather than terms written for this
directory: they cite the United Kingdom's Contracts (Rights of Third Parties)
Act 1999 (13.9) and set terms for a mobile application the Commission does
not publish (12). They bind as published at the Commission's own host all the
same, and must never be described as a choice the Commission made about this
data. What this file carries is facts about public offices (an address, a
telephone number, an e-mail address), which copyright does not cover, and
districtry is free, non-commercial and credits the Commission on every card;
but a public website is not "personal" use, so whether to show these before
the Commission confirms was the operator's call, and on 2026-10-16 the
operator chose to show them now. The letter asking the Commission for each
district's directors (docs/ASK_DRAFTS.md) asks it to confirm this use as well.

PUBLISHING GAPS, recorded with the map's (gap
ok-conservation-district-directors): the directory names offices and not
directors; it carries no district number, so it joins to the map only by
name; one name is cut short and another carries a county in brackets; two of
its five website links reach no district; one entry's Facebook link points
at its website; and the website's terms of use, a stock template, allow only
personal, non-commercial use of a directory of public offices.
"""

import argparse
import datetime
import html
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(os.path.dirname(INSTANCE), "scripts"))

from scraper_common import require_robots_once  # noqa: E402

DIRECTORY = "https://conservation.ok.gov/conservation-district-directory/"
USER_AGENT = "districtry/1.0 (+https://districtry.com/ok/)"
HEADERS = {"User-Agent": USER_AGENT, "Accept": "text/html", "Accept-Encoding": "identity"}
MAP_FILE = os.path.join(INSTANCE, "data", "app", "ok-conservation-districts.json")
OUT = os.path.join(INSTANCE, "data", "app", "ok-conservation-offices.json")
LABEL = "build-ok-conservation-offices"

# Floors, measured 2026-10-16: 84 entries in five areas, every one with a
# telephone number and an e-mail address.
MIN_ENTRIES = 80
AREAS = ("Area I", "Area II", "Area III", "Area IV", "Area V")

# the directory's name, normalised -> the map's, normalised
NAME_JOIN = {
    "central north canadian river": "central north canadian",
}

# the name as the directory prints it -> (what the card shows, why)
NAME_FIXES = {
    "Cleveland County Conservation": (
        "Cleveland County Conservation District",
        "the directory drops the last word; the map names it Cleveland County CD"),
    "North Fork of Red River Conservation District (Beckham County)": (
        "North Fork of Red River Conservation District",
        "the bracketed county is a note, not part of the name the map gives"),
}

# the website the directory links -> why the card does not link it. Each was
# read on 2026-10-16; an entry the directory no longer prints stops the build.
# A domain with no DNS record, or one parked for sale, can be bought by anyone,
# so it is never linked.
WEBSITE_DROPS = {
    "http://hughesccd.webs.com/": "the name has no DNS record (Hughes County)",
    "https://www.okcountyconservation.com/": (
        "the domain is parked: it answers with a domain-parking page, not the "
        "district's (Oklahoma County)"),
}

LABELLED = re.compile(r"^(Phone|Fax|E-?mail|Web|Website|Facebook)\s*:\s*(.*)$", re.I)
PHONE = re.compile(r"^\(?(\d{3})\)?[-. ]?(\d{3})-(\d{4})(?:\s*,?\s*ext\.?\s*(\d+))?$", re.I)
EMAIL = re.compile(r"^[a-z0-9._-]+@conservation\.ok\.gov$")
MAILING = "Mailing address:"


def fail(msg):
    print("%s: FAIL: %s" % (LABEL, msg))
    raise SystemExit(1)


def text(fragment):
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment))
    return re.sub(r"[\s\xa0]+", " ", t).strip()


def fetch():
    verdict = require_robots_once(DIRECTORY, USER_AGENT, headers=HEADERS, label=LABEL)
    print("robots: %s" % verdict)
    req = urllib.request.Request(DIRECTORY, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        if resp.status != 200:
            fail("the directory answered HTTP %d" % resp.status)
        return resp.read().decode("utf-8", errors="replace")


def norm(name):
    n = re.sub(r"\(.*?\)", " ", name.lower())
    n = re.sub(r"\bconservation district\b|\bconservation\b|\bcd\b", " ", n)
    return " ".join(n.split())


def office_lines(lines):
    """The office's address as printed, and a separate mailing address where
    the directory gives one. A bracketed line is the street address of the
    post office box above it and stays beside it."""
    office, mailing, target = [], [], None
    for line in lines:
        if line == MAILING:
            target = mailing
            continue
        if target is None:
            target = office
        if line.startswith("(") and target:
            target[-1] = target[-1] + " " + line
        else:
            target.append(line)
    return ", ".join(office), (", ".join(mailing) or None)


def parse(page):
    m = re.search(r'<meta property="article:modified_time" content="(\d{4}-\d{2}-\d{2})', page)
    modified = m.group(1) if m else None
    areas = [(a.start(), a.group(1)) for a in re.finditer(r"<span>(Area [IVX]+)</span>", page)]
    if [a for _, a in areas] != list(AREAS):
        fail("the directory's areas are %s, not %s" % ([a for _, a in areas], list(AREAS)))
    entries, dropped = [], set()
    for para in re.finditer(r'<p class="wp-block-paragraph">(.*?)</p>', page, flags=re.S):
        body = para.group(1)
        head = re.match(r"\s*<strong>(.*?)</strong>", body, flags=re.S)
        if not head:
            continue
        name = text(head.group(1))
        area = None
        for pos, a in areas:
            if pos < para.start():
                area = a
        if area is None:
            fail("%r sits above the first area" % name)
        rec = {"printed": name, "area": area}
        address, labelled = [], {}
        for part in re.split(r"<br\s*/?>", body[head.end():]):
            t = text(part)
            if not t:
                continue
            lab = LABELLED.match(t)
            if not lab:
                if labelled:
                    fail("%s: %r follows its contact lines" % (name, t))
                address.append(t)
                continue
            kind = lab.group(1).lower().replace("-", "")
            kind = "web" if kind == "website" else kind
            if kind in labelled:
                fail("%s gives two %s lines" % (name, kind))
            labelled[kind] = (lab.group(2), re.findall(r'href="([^"]+)"', part))
        if not address:
            fail("%s gives no address" % name)
        rec["office"], mailing = office_lines(address)
        if mailing:
            rec["mailing"] = mailing
        if "phone" not in labelled:
            fail("%s gives no telephone number" % name)
        phone = PHONE.match(labelled["phone"][0].strip())
        if not phone:
            fail("%s's telephone %r is not one number" % (name, labelled["phone"][0]))
        rec["phone"] = "%s-%s-%s" % phone.group(1, 2, 3)
        if phone.group(4):
            rec["ext"] = phone.group(4)
        if "email" not in labelled:
            fail("%s gives no e-mail address" % name)
        mails = [h[len("mailto:"):].strip().lower() for h in labelled["email"][1]
                 if h.startswith("mailto:")]
        if len(mails) != 1 or not EMAIL.match(mails[0]):
            fail("%s's e-mail %r is not one district address at conservation.ok.gov"
                 % (name, labelled["email"]))
        rec["email"] = mails[0]
        if "web" in labelled:
            hrefs = [h for h in labelled["web"][1] if h.startswith(("http://", "https://"))]
            if len(hrefs) != 1:
                fail("%s's website line carries %r" % (name, labelled["web"]))
            if hrefs[0] in WEBSITE_DROPS:
                dropped.add(hrefs[0])
            else:
                rec["url"] = hrefs[0]
        entries.append(rec)
    stale = sorted(set(WEBSITE_DROPS) - dropped)
    if stale:
        fail("WEBSITE_DROPS names %s, which the directory no longer links; read it again"
             % ", ".join(stale))
    return entries, modified


def drawn_districts():
    with open(MAP_FILE, encoding="utf-8") as fh:
        return {f["properties"]["key"]: f["properties"]["label"]
                for f in json.load(fh)["features"]}


def join(entries, modified):
    drawn = drawn_districts()
    by_name = {}
    for key, label in drawn.items():
        n = norm(label)
        if n in by_name:
            fail("two drawn districts read as %r" % n)
        by_name[n] = key
    used_fixes, used_joins = set(), set()
    out = {}
    today = datetime.date.today().isoformat()
    for e in entries:
        printed = e.pop("printed")
        n = norm(printed)
        if n in NAME_JOIN:
            used_joins.add(n)
            n = NAME_JOIN[n]
        key = by_name.get(n)
        if key is None:
            fail("the directory's %r matches no drawn district" % printed)
        if key in out:
            fail("two directory entries join the map's %s" % drawn[key])
        name = printed
        if printed in NAME_FIXES:
            used_fixes.add(printed)
            name = NAME_FIXES[printed][0]
        elif not printed.endswith("Conservation District"):
            fail("the directory names a district %r; read it again" % printed)
        e["name"] = name
        e["sourceUrl"] = DIRECTORY
        e["read"] = today
        if modified:
            e["directoryModified"] = modified
        out[key] = e
    missing = sorted(set(drawn) - set(out), key=int)
    if missing:
        fail("the map draws %s, which the directory does not list"
             % ", ".join("%s (%s)" % (k, drawn[k]) for k in missing))
    for table, used, label in ((NAME_FIXES, used_fixes, "NAME_FIXES"),
                               (NAME_JOIN, used_joins, "NAME_JOIN")):
        stale = sorted(set(table) - used)
        if stale:
            fail("%s names %s, which the directory no longer prints" % (label, stale))
    return dict(sorted(out.items(), key=lambda kv: int(kv[0])))


def check(data):
    """Offline: hold the shipped file to the shipped map and to its own rules."""
    drawn = drawn_districts()
    problems = []
    for key, rec in data.items():
        if key not in drawn:
            problems.append("district %s is not one the map draws" % key)
        if rec.get("sourceUrl") != DIRECTORY:
            problems.append("district %s does not cite the directory" % key)
        if rec.get("area") not in AREAS:
            problems.append("district %s is in no area of the Commission's" % key)
        if not rec.get("office"):
            problems.append("district %s has no office address" % key)
        if not PHONE.match(rec.get("phone") or ""):
            problems.append("district %s's telephone %r is not a number" % (key, rec.get("phone")))
        if rec.get("ext") is not None and not re.fullmatch(r"\d+", rec["ext"]):
            problems.append("district %s's extension %r is not digits" % (key, rec["ext"]))
        if not EMAIL.match(rec.get("email") or ""):
            problems.append("district %s's e-mail %r is not a district address"
                            % (key, rec.get("email")))
        url = rec.get("url")
        if url is not None and not re.match(r"^https?://", url):
            problems.append("district %s's website %r is not an address" % (key, url))
        if not str(rec.get("name", "")).endswith("Conservation District"):
            problems.append("district %s is named %r" % (key, rec.get("name")))
    missing = sorted(set(drawn) - set(data), key=int)
    if missing:
        problems.append("the map draws %s, which the file does not carry" % ", ".join(missing))
    if len(data) < MIN_ENTRIES:
        problems.append("%d districts, below the floor of %d" % (len(data), MIN_ENTRIES))
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped file to the shipped map")
    ap.add_argument("--source", help="parse a saved copy of the directory page")
    args = ap.parse_args()
    if args.check:
        with open(OUT, encoding="utf-8") as fh:
            data = json.load(fh)
        problems = check(data)
        if problems:
            for p in problems:
                print("%s: FAIL: %s" % (LABEL, p))
            raise SystemExit(1)
        print("%s --check: OK — an office for each of the map's %d conservation districts"
              % (LABEL, len(data)))
        return
    if args.source:
        with open(args.source, encoding="utf-8", errors="replace") as fh:
            page = fh.read()
    else:
        page = fetch()
    entries, modified = parse(page)
    if len(entries) < MIN_ENTRIES:
        fail("%d entries, below the floor of %d" % (len(entries), MIN_ENTRIES))
    data = join(entries, modified)
    problems = check(data)
    if problems:
        for p in problems:
            print("%s: FAIL: %s" % (LABEL, p))
        raise SystemExit(1)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    web = sum(1 for r in data.values() if r.get("url"))
    print("wrote %s: %d district offices, %d with a website (read %s, directory modified %s)"
          % (os.path.relpath(OUT, os.path.dirname(INSTANCE)), len(data), web,
             datetime.date.today().isoformat(), modified))


if __name__ == "__main__":
    main()
