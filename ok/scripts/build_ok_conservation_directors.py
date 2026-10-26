#!/usr/bin/env python3
"""
Build ok/data/app/ok-conservation-directors.json: the five directors of each
Oklahoma conservation district that names its board on a website of its own.

    python3 ok/scripts/build_ok_conservation_directors.py              # fetch, check, write
    python3 ok/scripts/build_ok_conservation_directors.py --source DIR # parse saved copies (DIR/<key>.html)
    python3 ok/scripts/build_ok_conservation_directors.py --check      # offline

WHY ONLY SOME DISTRICTS. Each district is governed by five directors, three
elected and two appointed (27A O.S. § 3-3-201). The Oklahoma Conservation
Commission's directory of district offices names none of them, and no list
the Commission publishes does (ok/scripts/build_ok_conservation_offices.py).
So on 2026-10-25 every one of the 84 districts was looked for on a website of
its own. Five named all five directors there, and all five are read here
(SOURCES); the rest have no site, a Facebook page only, or a site that names
no board. Lincoln County's page may be out of date: every meeting its site
lists is from 2020 and nothing on it is later than a 2023 copyright line. Adam
chose on 2026-10-26 to show it anyway, so its record carries a caution
(CAUTIONS) that the card prints beside the names, saying exactly that. The
rest of the state waits on the letter to the Commission (docs/ASK_DRAFTS.md,
Ask ok-occ-conservation-directors), and the gap stays recorded as
ok-conservation-district-directors.

WHAT IS CARRIED: each director's name as the page prints it, and the office
on the board (chair, vice-chair, treasurer) where the page gives one.
Associate directors are advisers rather than board members and are not
carried, and neither is anything else these pages say about a person (where
they work, how long they have served). Each district's record carries the
page it was read from and the day it was read, which the card prints.

EVERY DISTRICT MUST GIVE EXACTLY FIVE DIRECTORS, or the build stops: the law
seats five, so four means the parser missed one and six means it took an
associate. A page that stops parsing is read against the page, never
loosened.

THE PAGES state no licence. They are the districts' own publications of who
holds a public office, and the card names each person with a link back to
the page that names them.
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

USER_AGENT = "districtry/1.0 (+https://districtry.com/ok/)"
HEADERS = {"User-Agent": USER_AGENT, "Accept": "text/html", "Accept-Encoding": "identity"}
MAP_FILE = os.path.join(INSTANCE, "data", "app", "ok-conservation-districts.json")
OUT = os.path.join(INSTANCE, "data", "app", "ok-conservation-directors.json")
LABEL = "build-ok-conservation-directors"
SEATS = 5

# The district's number on the Commission's map -> the page that names its
# board. Tulsa County's is read over http: its https answers with a
# self-signed certificate (2026-10-26), and robots.txt is read over the same
# scheme as the page.
SOURCES = {
    "2": "http://tulsaccd.org/about-tccd/meet-our-board/",
    "43": "https://lincolnccd.wixsite.com/lincolncountycd/about_us",
    "53": "https://www.deweycountyconservation.com/",
    "54": "https://www.rogerscountyconservationdistrict.org/the-district/",
    "68": "https://deercreekconservation.com/administration/",
}

# Districts whose page may name a board that has since changed, and the
# sentence the card prints beside the names to say so.
CAUTIONS = {
    "43": ("Every meeting this district's website lists is from 2020, and nothing "
           "on it is dated later than 2023, so this board may have changed."),
}

ROLES = {
    "chair": "Chair", "chairman": "Chair",
    "vice-chair": "Vice-Chair", "vice chair": "Vice-Chair", "vice chairman": "Vice-Chair",
    "treasurer": "Treasurer", "secretary/treasurer": "Secretary-Treasurer",
}
NAME = re.compile(r"^[A-Z][A-Za-z.'-]+(?: [A-Z][A-Za-z.'-]*)+$")


def fail(msg):
    print("%s: FAIL: %s" % (LABEL, msg))
    raise SystemExit(1)


def lines(page):
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", t))
    out = []
    for raw in t.split("\n"):
        s = re.sub(r"[\s\xa0]+", " ", raw).strip()
        if s:
            out.append(s)
    return out


def between(ls, start, stop):
    try:
        i = ls.index(start)
        j = ls.index(stop, i + 1)
    except ValueError:
        fail("a marker is missing (%r .. %r)" % (start, stop))
    return ls[i + 1:j]


def role(word):
    r = ROLES.get(word.strip().lower())
    if r is None:
        fail("an office the parser does not know: %r" % word)
    return r


def parse_rogers(ls):
    # "RCCD Board from left to right:  Ken Froese, Joe Parker (Secretary/Treasurer), ..."
    hits = [l for l in ls if l.startswith("RCCD Board from left to right:")]
    if len(hits) != 1:
        fail("Rogers: the board caption is missing or doubled")
    out = []
    for part in hits[0].split(":", 1)[1].split(","):
        m = re.match(r"^\s*(.+?)\s*(?:\(([^)]+)\))?\s*$", part)
        d = {"name": m.group(1)}
        if m.group(2):
            d["role"] = role(m.group(2))
        out.append(d)
    return out


def parse_dewey(ls):
    return [{"name": n} for n in between(ls, "Board Members", "Associate member")]


def parse_tulsa(ls):
    sec = between(ls, "Meet Our Board", "Associate Board Members:")
    joined = re.sub(r"\n:\s*", ": ", "\n".join(sec))
    joined = re.sub(r":\n", ": ", joined)
    out = []
    for line in joined.split("\n"):
        m = re.match(r"^(Chairman|Vice Chair|Treasurer|Member)\s*:\s*(.+?),?$", line)
        if not m:
            continue
        d = {"name": m.group(2).strip()}
        if m.group(1) != "Member":
            d["role"] = role(m.group(1))
        out.append(d)
    return out


def parse_lincoln(ls):
    # "Board Members", then one director per line, an office either after a
    # comma on the same line or on the line after one that ends in a comma.
    try:
        i = ls.index("Board Members")
    except ValueError:
        fail("Lincoln: the board heading is missing")
    sec = []
    for l in ls[i + 1:]:
        if l.replace("\u200b", "").strip() == "District Staff":
            break
        sec.append(l)
    else:
        fail("Lincoln: the staff heading after the board is missing")
    out, k = [], 0
    while k < len(sec):
        line = sec[k]
        if line.endswith(",") and k + 1 < len(sec):
            line, k = line + " " + sec[k + 1], k + 1
        name, _, office = line.partition(",")
        d = {"name": name.strip()}
        if office.strip():
            d["role"] = role(office)
        out.append(d)
        k += 1
    return out


def parse_deer_creek(ls):
    out = []
    for line in between(ls, "Board of Directors", "Associate Directors"):
        m = re.match(r"^(.+?)\s+[\u2013-]\s+(.+)$", line)
        if not m:
            fail("Deer Creek: a board line that does not read 'Name - Office': %r" % line)
        d = {"name": m.group(1)}
        if m.group(2) != "Board Director":
            d["role"] = role(m.group(2))
        out.append(d)
    return out


PARSERS = {"2": parse_tulsa, "43": parse_lincoln, "53": parse_dewey, "54": parse_rogers, "68": parse_deer_creek}


def fetch(url):
    verdict = require_robots_once(url, USER_AGENT, headers=HEADERS, label=LABEL)
    print("robots: %s" % verdict)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        if resp.status != 200:
            fail("%s answered HTTP %d" % (url, resp.status))
        return resp.read().decode("utf-8", errors="replace")


def drawn_districts():
    with open(MAP_FILE, encoding="utf-8") as fh:
        geo = json.load(fh)
    return {str(f["properties"]["key"]) for f in geo["features"]}


def check(data):
    problems = []
    drawn = drawn_districts()
    if set(data) != set(SOURCES):
        problems.append("the file's districts %s are not SOURCES' %s"
                        % (sorted(data), sorted(SOURCES)))
    for key, rec in sorted(data.items()):
        if key not in drawn:
            problems.append("district %s is not on the map" % key)
        if rec.get("caution") != CAUTIONS.get(key):
            problems.append("district %s: caution is not the one CAUTIONS gives" % key)
        if rec.get("sourceUrl") != SOURCES.get(key):
            problems.append("district %s: sourceUrl is not the page SOURCES names" % key)
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", rec.get("read", "")):
            problems.append("district %s: no read date" % key)
        dirs = rec.get("directors") or []
        if len(dirs) != SEATS:
            problems.append("district %s: %d directors, not %d" % (key, len(dirs), SEATS))
        names = set()
        for d in dirs:
            n = d.get("name", "")
            if not NAME.match(n):
                problems.append("district %s: %r does not read as a name" % (key, n))
            if n in names:
                problems.append("district %s: %s twice" % (key, n))
            names.add(n)
            if set(d) - {"name", "role"}:
                problems.append("district %s: %s carries more than a name and office" % (key, n))
            if "role" in d and d["role"] not in set(ROLES.values()):
                problems.append("district %s: unknown office %r" % (key, d["role"]))
    for key in CAUTIONS:
        if key not in SOURCES:
            problems.append("CAUTIONS names district %s, which SOURCES does not read" % key)
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped file to SOURCES and the shipped map")
    ap.add_argument("--source", help="a directory of saved pages, <key>.html")
    args = ap.parse_args()
    if args.check:
        with open(OUT, encoding="utf-8") as fh:
            data = json.load(fh)
        problems = check(data)
        if problems:
            for p in problems:
                print("%s: FAIL: %s" % (LABEL, p))
            raise SystemExit(1)
        print("%s --check: OK — %d districts' boards, %d directors, %d with a caution"
              % (LABEL, len(data), sum(len(r["directors"]) for r in data.values()),
                 len(CAUTIONS)))
        return
    today = datetime.date.today().isoformat()
    data = {}
    for key, url in sorted(SOURCES.items(), key=lambda kv: int(kv[0])):
        if args.source:
            with open(os.path.join(args.source, key + ".html"), encoding="utf-8",
                      errors="replace") as fh:
                page = fh.read()
        else:
            page = fetch(url)
        data[key] = {"sourceUrl": url, "read": today, "directors": PARSERS[key](lines(page))}
        if key in CAUTIONS:
            data[key]["caution"] = CAUTIONS[key]
    problems = check(data)
    if problems:
        for p in problems:
            print("%s: FAIL: %s" % (LABEL, p))
        raise SystemExit(1)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    print("wrote %s: %d districts' boards (read %s)"
          % (os.path.relpath(OUT, os.path.dirname(INSTANCE)), len(data), today))


if __name__ == "__main__":
    main()
