#!/usr/bin/env python3
"""
Court districts and their judges for Kansas, Nebraska, North Dakota, Ohio and
South Dakota, read from each state's own court website.

    python3 scripts/build_state_courts.py --fetch ks   # re-read the court pages into ks/data/source/courts/
    python3 scripts/build_state_courts.py ks           # build the two app files (needs shapely)
    python3 scripts/build_state_courts.py --check      # every state, offline, stdlib only

EVERY DISTRICT HERE IS A SET OF WHOLE COUNTIES, so the county lists are the
boundary and no map is read: the dissolve, the partition gate and the offline
area check are scripts/whole_county_courts.py, shared with the other states.
This file says where each state's county lists and judges come from.

WHAT IS KEPT. `--fetch` reads the court pages (robots.txt first, this
project's own client) and writes ONE plain-text excerpt per state,
`<tag>/data/source/courts/<tag>-courts.txt`: a `district` line per district
with its counties as the court lists them, and a `judge` line per judge with
the title the court prints. Nothing else from the pages is copied: no address,
telephone or fax. The build reads only that excerpt, so a reviewer can read
what changed in a refresh as a text diff.

TWO FILES PER STATE. The districts (`<tag>-judicial-districts.json`) are
geometry, cache-first in the service worker, so they change only when a county
moves between districts. The judges (`<tag>-district-judges.json`) are a
roster keyed by district, network-first, so a new judge reaches a returning
reader at once.

A SEAT THE COURT PRINTS AS VACANT ships as vacant and never as a person named
"Vacant". A heading this file does not know stops the fetch rather than
becoming a judge's name.

No weekly job refreshes these; each state's WATCH.md carries the re-read, and
the card prints the date the pages were read.
"""

import argparse
import datetime
import html
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import whole_county_courts as wcc  # noqa: E402  (FLEET_SHARED)

LABEL = "build-state-courts"

ORDINALS = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh",
            "Eighth", "Ninth", "Tenth", "Eleventh", "Twelfth"]


def ordinal_suffix(n):
    if 10 <= n % 100 <= 20:
        return "%dth" % n
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


# Measured 2026-11-27 on the pages read that day. A count that moves stops the
# build; read the court's page before changing one.
STATES = {
    "ks": {
        "name": "Kansas",
        "districts": 31, "counties": 105, "min_judges": 250,
        "unit_word": "judicial district",
        "authority": "The Kansas Judicial Branch's district court pages (kscourts.gov)",
        "source": "https://www.kscourts.gov/About-the-Courts/District-Courts",
    },
    "ne": {
        "name": "Nebraska",
        "districts": 12, "counties": 93, "min_judges": 50,
        "unit_word": "district court judicial district",
        "authority": "The Nebraska Judicial Branch's district map and directory of district court judges (nebraskajudicial.gov)",
        "source": "https://nebraskajudicial.gov/directories/district-court-judges",
    },
    "nd": {
        "name": "North Dakota",
        "districts": 8, "counties": 53, "min_judges": 45,
        "unit_word": "judicial district",
        "authority": "North Dakota Supreme Court Administrative Rule 6 and the court system's list of district court judges (ndcourts.gov)",
        "source": "https://www.ndcourts.gov/district-court/district-court-judges",
    },
    "oh": {
        "name": "Ohio",
        "districts": 12, "counties": 88, "min_judges": 60,
        "unit_word": "appellate district",
        "authority": "The Supreme Court of Ohio's page on the courts of appeals (supremecourt.ohio.gov)",
        "source": "https://www.supremecourt.ohio.gov/courts/judicial-system/ohio-court-of-appeals/",
    },
    "sd": {
        "name": "South Dakota",
        "districts": 7, "counties": 66, "min_judges": 35,
        "unit_word": "judicial circuit",
        "authority": "The South Dakota Unified Judicial System's circuit pages (ujs.sd.gov)",
        "source": "https://ujs.sd.gov/court-finder/",
    },
}


def source_path(tag):
    return os.path.join(ROOT, tag, "data", "source", "courts", "%s-courts.txt" % tag)


# ---------------------------------------------------------------- reading pages

def page_lines(body):
    """The visible text of a page, one trimmed line per text node."""
    body = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", body)
    body = re.sub(r"<[^>]+>", "\n", body)
    body = html.unescape(body).replace("​", "").replace("\xa0", " ")
    return [re.sub(r"\s+", " ", ln).strip() for ln in body.split("\n")
            if ln.strip()]


class Reader(object):
    """GETs with robots.txt read first per host, paced two seconds apart."""

    def __init__(self):
        import scraper_common as sc
        self.sc = sc
        self.headers = sc.UA_HEADERS_ROSTER_BOT
        self.last = 0.0

    def get(self, url):
        self.sc.require_robots_once(url, self.headers["User-Agent"],
                                    headers=self.headers, label=LABEL)
        wait = 2.0 - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait)
        resp = self.sc.fetch(url, self.headers, timeout=60)
        self.last = time.time()
        return page_lines(resp.text)


NOT_A_NAME = re.compile(r"\b(Judges?|Division|Clerk|Administrator|Officer|"
                        r"Courthouse|District Court|Magistrates?)\b", re.I)


def name_problem(name):
    if not name or NOT_A_NAME.search(name) or not re.search(r"[a-z]", name) \
            or len(name.split()) < 2 or len(name) > 60:
        return "%r does not read as a judge's name" % name
    return None


def person(name, label):
    name = re.sub(r"\s+", " ", name).strip().rstrip(",")
    problem = name_problem(name)
    if problem:
        wcc.fail(label, problem + "; read the page before teaching this file "
                 "a new heading")
    return name


def fetch_ks(reader):
    roles = {"Chief Judge": "Chief Judge",
             "District Court Judge": "District Judge",
             "District Court Judges": "District Judge",
             "District Judge": "District Judge",
             "District Magistrate Judge": "District Magistrate Judge",
             "District Magistrate Judges": "District Magistrate Judge",
             "Juvenile Division": "Judge, Juvenile Division",
             "Pro Tem Division": "Judge, Pro Tem Division"}
    stop = ("District Court Administrator", "Chief Clerk", "Chief Court Services",
            "Court Administrator")
    out, counties = [], None
    for n in range(1, 32):
        url = ("https://www.kscourts.gov/About-the-Courts/District-Courts/"
               "Districts/%s-Judicial-District" % ordinal_suffix(n))
        lines = reader.get(url)
        if counties is None:
            # The district map every district page carries: "1", "st",
            # "Judicial District", "Atchison, Leavenworth", a long list
            # sometimes wrapped onto a second line after a trailing comma.
            counties = {}
            i = lines.index("Kansas District Map") + 1
            while i < len(lines) and len(counties) < 31:
                if re.match(r"^\d+$", lines[i]) and lines[i + 2] == "Judicial District":
                    text, j = lines[i + 3], i + 4
                    while text.endswith(","):
                        text, j = text + " " + lines[j], j + 1
                    counties[int(lines[i])] = [c.strip() for c in text.split(",")]
                    i = j
                else:
                    i += 1
            for d in sorted(counties):
                out.append("district | %d | %s" % (d, ", ".join(counties[d])))
        start = next(i for i, ln in enumerate(lines) if ln in roles)
        role = None
        for ln in lines[start:]:
            if ln.startswith(stop):
                break
            if ln in roles:
                role = roles[ln]
                continue
            m = re.match(r"^(.*?)(?:,| -) ([A-Z][A-Za-z. ]+?) County$", ln)
            name, county = (m.group(1), m.group(2)) if m else (ln, "")
            if name.strip().lower() == "vacant":
                out.append("vacant | %d | %s | | %s" % (n, role, county))
            else:
                out.append("judge | %d | %s | %s | %s"
                           % (n, role, person(name, "ks %d" % n), county))
    return out


def fetch_ne(reader):
    words = ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
             "Nine", "Ten", "Eleven", "Twelve"]
    out = []
    for n in range(1, 13):
        lines = reader.get("https://nebraskajudicial.gov/directories/district-map/"
                           "district-%d" % n)
        pat = re.compile(r"^District (?:Court )?%s (?:and Probation Dis[a-z]+ \w+ )?"
                         r"(?:is|are) comprised of (?:the following counties: )?(.+?)"
                         r"(?: [Cc]ount(?:y|ies))?\.$" % words[n - 1])
        hits = [pat.match(ln) for ln in lines]
        hits = [h for h in hits if h]
        if len(hits) != 1:
            wcc.fail(LABEL, "ne district %d: %d county sentences" % (n, len(hits)))
        names = re.split(r",\s*(?:and\s+)?|\s+and\s+", hits[0].group(1))
        out.append("district | %d | %s" % (n, ", ".join(c.strip() for c in names if c.strip())))
    lines = reader.get("https://nebraskajudicial.gov/directories/district-court-judges")
    unit = None
    for i, ln in enumerate(lines):
        m = re.match(r"^District: (\d+)$", ln)
        if m:
            unit = int(m.group(1))
        elif ln.startswith("Hon. ") and unit:
            county = lines[i + 2] if lines[i + 1] == "County:" else ""
            out.append("judge | %d | District Judge | %s | %s"
                       % (unit, person(ln[5:], "ne %d" % unit), county))
    return out


ND_DISTRICTS = ["Northwest", "North Central", "Northeast", "Northeast Central",
                "East Central", "Southeast", "South Central", "Southwest"]


def fetch_nd(reader):
    out = []
    lines = reader.get("https://www.ndcourts.gov/legal-resources/rules/ndsupctadminr/6")
    for i, ln in enumerate(lines):
        m = re.match(r"^(.+) Judicial District$", ln)
        if m and m.group(1) in ND_DISTRICTS and i + 1 < len(lines):
            c = re.match(r"^consists of the counties of (.+)\.$", lines[i + 1])
            if c:
                names = re.split(r",\s*(?:and\s+)?|\s+and\s+", c.group(1))
                out.append("district | %s | %s" % (m.group(1), ", ".join(
                    n.strip() for n in names if n.strip())))
    lines = reader.get("https://www.ndcourts.gov/district-court/district-court-judges")
    start = lines.index("District Court Judges", lines.index("District Court Judges") + 1)
    unit = None
    for ln in lines[start + 1:]:
        if ln == "Judicial Referees":
            break
        m = re.match(r"^(.+) District$", ln)
        if m and m.group(1) in ND_DISTRICTS:
            unit = m.group(1)
            continue
        if unit is None:
            continue
        role = "District Judge"
        if ln.endswith(" - Presiding Judge"):
            ln, role = ln[:-len(" - Presiding Judge")], "Presiding Judge"
        out.append("judge | %s | %s | %s | " % (unit, role, person(ln, "nd " + unit)))
    return out


def fetch_oh(reader):
    lines = reader.get(STATES["oh"]["source"])
    out, judges = [], []
    for i, ln in enumerate(lines):
        m = re.match(r"^(\w+) District Court of Appeals$", ln)
        if not m or m.group(1) not in ORDINALS or lines[i + 1] != "County:":
            continue
        n = ORDINALS.index(m.group(1)) + 1
        out.append("district | %d | %s" % (n, ", ".join(
            c.strip() for c in lines[i + 2].split(","))))
        j = lines.index("Appellate Judges:", i) + 1
        while lines[j] != "Online Resources":
            judges.append("judge | %d | Judge | %s | " % (n, person(lines[j], "oh %d" % n)))
            j += 1
    return out + judges


def fetch_sd(reader):
    out, judges = [], []
    roles = {"Presiding Circuit Judge": "Presiding Judge",
             "Circuit Judge": "Circuit Judge"}
    fabric = set(wcc.county_geometry("sd", LABEL))
    for n, word in enumerate(ORDINALS[:7], 1):
        w = word.lower()
        base = "https://ujs.sd.gov/court-finder/%s-judicial-circuit/" % w
        lines = reader.get(base)
        i = lines.index("%s Judicial Circuit Counties" % word) + 1
        names = []
        while re.sub(r" County$", "", lines[i]) in fabric:
            names.append(re.sub(r" County$", "", lines[i]))
            i += 1
        out.append("district | %d | %s" % (n, ", ".join(names)))
        # The Sixth Circuit's contacts page has its own address.
        kind = "court-contacts" if word == "Sixth" else "circuit-contacts"
        lines = reader.get(base + "%s-%s-judicial-circuit/" % (kind, w))
        for k, ln in enumerate(lines[:-1]):
            if ln.startswith("Judge ") and lines[k + 1] in roles:
                judges.append("judge | %d | %s | %s | " % (
                    n, roles[lines[k + 1]], person(ln[6:], "sd %d" % n)))
    return out + judges


FETCHERS = {"ks": fetch_ks, "ne": fetch_ne, "nd": fetch_nd, "oh": fetch_oh,
            "sd": fetch_sd}

SOURCES_READ = {
    "ks": "the 31 district pages under https://www.kscourts.gov/About-the-Courts/District-Courts/Districts/ (each lists its judges and carries the statewide district map's county lists)",
    "ne": "https://nebraskajudicial.gov/directories/district-map/district-1 to district-12 (counties; the district court's, which differ from the county court's for Otoe and Fillmore) and https://nebraskajudicial.gov/directories/district-court-judges (judges, with the county of each judge's home court)",
    "nd": "https://www.ndcourts.gov/legal-resources/rules/ndsupctadminr/6 (Administrative Rule 6, counties) and https://www.ndcourts.gov/district-court/district-court-judges (judges)",
    "oh": "https://www.supremecourt.ohio.gov/courts/judicial-system/ohio-court-of-appeals/ (counties and judges of all twelve districts)",
    "sd": "https://ujs.sd.gov/court-finder/<circuit>-judicial-circuit/ (counties) and each circuit's contacts page (circuit judges; magistrate judges are not kept)",
}


def write_source(tag, lines):
    path = source_path(tag)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    head = [
        "# %s court districts and judges, kept by scripts/build_state_courts.py --fetch %s"
        % (STATES[tag]["name"], tag),
        "# read: %s" % datetime.date.today().isoformat(),
        "# from: %s" % SOURCES_READ[tag],
        "# district | <district> | <counties, as the court lists them>",
        "# judge | <district> | <title> | <name> | <county the court prints beside the judge, if any>",
        "# vacant | <district> | <title> | | <county>",
    ]
    with open(path, "w") as fh:
        fh.write("\n".join(head + lines) + "\n")
    print("%s: wrote %s (%d lines)" % (LABEL, os.path.relpath(path, ROOT), len(lines)))


# ---------------------------------------------------------------- the build

def unit_key(tag, raw):
    return raw if tag == "nd" else int(raw)


def read_source(tag):
    cfg = STATES[tag]
    read, districts, seats = None, {}, {}
    with open(source_path(tag)) as fh:
        for ln in fh:
            ln = ln.rstrip("\n")
            if ln.startswith("# read: "):
                read = ln[len("# read: "):]
            if not ln.strip() or ln.startswith("#"):
                continue
            parts = [p.strip() for p in ln.split("|")]
            kind, unit = parts[0], unit_key(tag, parts[1])
            if kind == "district" and len(parts) == 3:
                if unit in districts:
                    wcc.fail(LABEL, "%s lists district %s twice" % (tag, unit))
                districts[unit] = [c.strip() for c in parts[2].split(",")]
            elif kind in ("judge", "vacant") and len(parts) == 5:
                seat = {"role": parts[2]}
                if kind == "judge":
                    seat["name"] = parts[3]
                else:
                    seat["vacant"] = True
                if parts[4]:
                    seat["county"] = parts[4]
                seats.setdefault(unit, []).append(seat)
            else:
                wcc.fail(LABEL, "%s: unreadable line %r" % (tag, ln))
    if not read or not re.match(r"^\d{4}-\d{2}-\d{2}$", read):
        wcc.fail(LABEL, "%s: the excerpt says no read date" % tag)
    if len(districts) != cfg["districts"]:
        wcc.fail(LABEL, "%s: %d districts, measured %d" % (tag, len(districts), cfg["districts"]))
    if set(seats) - set(districts):
        wcc.fail(LABEL, "%s: judges in districts %s that list no counties"
                 % (tag, sorted(set(seats) - set(districts), key=str)))
    named = sum(1 for v in seats.values() for s in v if "name" in s)
    if named < cfg["min_judges"]:
        wcc.fail(LABEL, "%s: %d judges named, measured at least %d"
                 % (tag, named, cfg["min_judges"]))
    for unit, rows in seats.items():
        for s in rows:
            if s.get("county") and s["county"] not in districts[unit]:
                wcc.fail(LABEL, "%s district %s: %s is beside a county outside "
                         "the district (%s)" % (tag, unit, s.get("name", "a vacancy"),
                                                s["county"]))
    return read, districts, seats


def tiling(tag, districts):
    cfg = STATES[tag]
    rows = [(u, sorted(districts[u]), {}) for u in districts]
    n = sum(len(v) for v in districts.values())
    if n != cfg["counties"]:
        wcc.fail(LABEL, "%s: the districts list %d counties, %s has %d"
                 % (tag, n, cfg["name"], cfg["counties"]))
    return wcc.Tiling("%s-judicial-districts.json" % tag, cfg["unit_word"], rows,
                      cfg["districts"], cfg["authority"])


def roster(read, districts, seats):
    return {str(u): {"read": read, "judges": seats.get(u, [])} for u in districts}


def roster_path(tag):
    return os.path.join(wcc.app_dir(tag), "%s-district-judges.json" % tag)


def build(tag):
    read, districts, seats = read_source(tag)
    wcc.build(tag, LABEL, [tiling(tag, districts)])
    with open(roster_path(tag), "w") as fh:
        json.dump(roster(read, districts, seats), fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("%s: wrote %s-district-judges.json (%d seats, read %s)"
          % (LABEL, tag, sum(len(v) for v in seats.values()), read))


def check(tag):
    read, districts, seats = read_source(tag)
    wcc.check(tag, LABEL, [tiling(tag, districts)])
    with open(roster_path(tag)) as fh:
        shipped = json.load(fh)
    if shipped != roster(read, districts, seats):
        wcc.fail(LABEL, "%s-district-judges.json is not what %s says; re-run "
                 "this builder" % (tag, os.path.relpath(source_path(tag), ROOT)))
    print("%s: %s OK — %d districts, %d seats, read %s"
          % (LABEL, tag, len(districts), sum(len(v) for v in seats.values()), read))


def selftest():
    assert ordinal_suffix(1) == "1st" and ordinal_suffix(12) == "12th" \
        and ordinal_suffix(22) == "22nd" and ordinal_suffix(13) == "13th"
    assert page_lines("<p>A&amp;B</p><script>x</script><b> C\xa0 D </b>") == ["A&B", "C D"]
    for bad in ("Chief Clerk", "Vacant", "JOHN", "Pro Tem Division"):
        assert name_problem(bad), "%r passed as a name" % bad
    assert person("Chas Neff, Jr.", "selftest") == "Chas Neff, Jr."
    print("%s: selftest OK" % LABEL)


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("states", nargs="*", help="ks ne nd oh sd (default: all)")
    ap.add_argument("--fetch", action="store_true", help="re-read the court pages")
    ap.add_argument("--check", action="store_true", help="verify, write nothing")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    tags = args.states or sorted(STATES)
    for tag in tags:
        if tag not in STATES:
            wcc.fail(LABEL, "no state %r here" % tag)
        if args.fetch:
            write_source(tag, FETCHERS[tag](Reader()))
        elif args.check:
            check(tag)
        else:
            build(tag)


if __name__ == "__main__":
    main()
