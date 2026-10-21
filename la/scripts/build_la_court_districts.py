#!/usr/bin/env python3
"""
Build Louisiana's three court layers, the courts whose judges are elected by
district:

  la/data/app/la-supreme-court-districts.json    the Supreme Court's 7 districts
  la/data/app/la-court-of-appeal-districts.json  the 15 districts of the 5 courts of appeal
  la/data/app/la-district-court-districts.json   the 41 judicial districts, and Orleans

    python3 la/scripts/build_la_court_districts.py          # writes (needs shapely and Node)
    python3 la/scripts/build_la_court_districts.py --check  # offline, stdlib only
    python3 la/scripts/build_la_court_districts.py --fetch  # re-read the two laws

This file draws the districts. Who holds each seat is
la/scripts/build_la_judges.py's, from the Secretary of State's list of elected
officials, and that builder holds its parish lists to these files.

THE SUPREME COURT IS DRAWN FROM THE LEGISLATURE'S OWN FILE. Act 7 of the 2024
Regular Session (Senate Bill 255) enacted La. R.S. 13:101.2, which divides the
state into seven Supreme Court districts, each electing one justice. The
Legislature's redistricting office publishes the act's districts as a zipped
shapefile on its page for the act (PAGE), and the builder holds the file to
the SHA-256 it was read with on 2026-10-21 (ZIP_SHA256): a file replaced in
place stops the build until a person has read it. Its seven districts are
drawn from precincts, so twelve parishes are split between two or three of
them. A parish counts as split when the act gives at least PART_PCT of it to
two or more districts. The parish fabric and the act's precincts trace the
same parish lines from different files, so every parish also touches
neighbouring districts by slivers: measured 2026-10-21, the largest sliver is
0.0059% of a parish (Richland, in District 4) and the smallest real part
2.29% (the part of Orleans in District 6), and a share between SLIVER_PCT and
PART_PCT stops the build. The twelve the overlay finds must be the twelve
parishes the page publishes a split-parish map for, and must be SPLIT_PARISHES.

Act 7 also decides how the card reads, in La. R.S. 13:101.3: each justice in
office when the act took effect is assigned to the district with the same
number as the one the justice was elected from, and may finish the term; the
justice's successor is elected from the district the act draws. So a justice
can sit for a district whose lines changed after the justice was elected, and
the card says so.

THE COURTS OF APPEAL AND THE DISTRICT COURTS ARE WHOLE PARISHES, so they are
dissolved from the shipped parish fabric by scripts/whole_county_courts.py,
which the other states' court builders share. Their parish lists are read from
the two laws that name them, La. R.S. 13:312 (the five circuits and their
districts) and La. R.S. 13:477 (the judicial districts), as the Legislature
publishes them at legis.la.gov. Each is kept in la/data/source/courts/ as the
page's text, with its address, read date and SHA-256 in the file's header; see
that folder's README. `--fetch` reads both again and says whether either
changed.

ONE PARISH IS SPLIT BY THE RIVER. La. R.S. 13:312 puts the part of St. John
the Baptist Parish east of the Mississippi River in the second district of the
fifth circuit, with St. James Parish, and the part west of it in the third,
with St. Charles Parish. This builder does not draw the river, so St. John the
Baptist ships as one feature carrying both districts and which side of the
river each takes, and its card names both.

ORLEANS HAS COURTS OF ITS OWN. La. R.S. 13:477 names 41 judicial districts and
leaves Orleans Parish out: the parish has a civil district court and a
criminal district court of its own. So the district-court file carries the 41
districts and one more unit, Orleans, and the build stops unless Orleans is
the one parish the law leaves out. The law's 41st district, which once was
to merge the Orleans courts, was repealed by Act 474 of 2012, so the
districts are numbered 1 to 40 and 42.

THE ELECTION SECTIONS ARE NOT DRAWN. Several districts elect some of their
judges from sections or subdistricts, which the two laws and other statutes
set by precinct. A district is drawn whole, and each judge's seat names the
section, as the Secretary of State's list prints it.

PARISH NAMES are matched to the fabric's letters only, so the law's "DeSoto"
is the fabric's "De Soto".
"""

import argparse
import datetime
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
sys.path.insert(0, HERE)
sys.path.append(os.path.join(REPO, "scripts"))

import whole_county_courts as wcc  # noqa: E402  (FLEET_SHARED)
# The instance's own copy, which a root script of the same name would shadow.
import build_legislative_boundaries as blb  # noqa: E402  (same instance tree)
assert os.path.dirname(os.path.abspath(blb.__file__)) == HERE, blb.__file__

LABEL = "build-la-court-districts"
USER_AGENT = "districtry/1.0 (+https://districtry.com/la/)"
SOURCE = os.path.join(INSTANCE, "data", "source", "courts")
APP = os.path.join(INSTANCE, "data", "app")
COUNTIES = os.path.join(APP, "state-counties.json")

# ------------------------------------------------------------- the two laws --
LAWS = {
    "rs13-477.txt": {
        "title": "La. R.S. 13:477, Judicial districts",
        "url": "https://legis.la.gov/legis/Law.aspx?d=149496",
        "start": "§477. Judicial districts",
    },
    "rs13-312.txt": {
        "title": "La. R.S. 13:312, Courts of appeal; circuits and districts",
        "url": "https://legis.la.gov/legis/Law.aspx?d=77438",
        "start": "§312. Courts of appeal; circuits and districts",
    },
}
# Where every page of the site's laws ends: the site's own footer.
PAGE_END = "If you experience any technical difficulties"

JUDICIAL_DISTRICTS = 41
REPEALED = {41}
ORLEANS = "Orleans"
CIRCUITS = 5
DISTRICTS_PER_CIRCUIT = 3
RIVER_PARISHES = ("St. John the Baptist",)
DISTRICT_AUTHORITY = ("La. R.S. 13:477, which names the parishes of the 41 judicial "
                      "districts and leaves out Orleans Parish, which has a civil "
                      "district court and a criminal district court of its own")
APPEAL_AUTHORITY = "La. R.S. 13:312, which names each district's parishes"

# ------------------------------------------------------- the Supreme Court --
PAGE = "https://redist.legis.la.gov/2024_Files/2024LASSCAct7.aspx"
ZIP_PATH = "2024_RS/2024LASSCAct7/Shapefile/Act_7_-__RS_(2024)_-_LASC.zip"
ZIP_URL = "https://redist.legis.la.gov/2024_Files/" + ZIP_PATH
ZIP_SHA256 = "d645d4068c3bd685b945ca58b6f7e9ac7bed28f97ea302889d58075fec62fc33"
ZIP_MEMBERS = {".shp", ".shx", ".dbf", ".prj"}
SUPREME_DISTRICTS = 7
SUPREME_OUT = "la-supreme-court-districts.json"
SUPREME_RECORD = os.path.join(INSTANCE, "data", "source", "la-supreme-court-districts.source.json")
SUPREME_AUTHORITY = ("La. R.S. 13:101.2, enacted by Act 7 of the 2024 Regular Session, "
                     "as the Legislature's redistricting office publishes its districts")
SIMPLIFY = "interval=5"
PART_PCT = 0.5
SLIVER_PCT = 0.05
SPLIT_PARISHES = ("Ascension", "Caddo", "East Baton Rouge", "Jefferson", "Lafayette",
                  "Orleans", "Ouachita", "Rapides", "St. Charles", "St. James",
                  "St. John the Baptist", "St. Landry")
# The page names two of its split-parish maps short.
PAGE_NAMES = {"EBR": "East Baton Rouge", "St. John": "St. John the Baptist"}
SPLIT_MAP_RE = re.compile(r"Act 7 of the 2024 RS \(SB255\) - LASC - ([^\"/<>]+?)\.pdf")


def fold(name):
    return re.sub(r"[^A-Z]", "", (name or "").upper())


def fabric_names():
    """{folded name: BASENAME} from the shipped parish fabric."""
    with open(COUNTIES) as fh:
        feats = json.load(fh)["features"]
    out = {}
    for f in feats:
        base = f["properties"]["BASENAME"]
        if fold(base) in out:
            wcc.fail(LABEL, "two parishes in the fabric fold to %r" % fold(base))
        out[fold(base)] = base
    return out


def resolve(names, fabric, where):
    out = []
    for n in names:
        base = fabric.get(fold(n))
        if base is None:
            wcc.fail(LABEL, "%s names %r, which is no parish in the fabric" % (where, n))
        out.append(base)
    return out


def split_names(text):
    return [p.strip() for p in re.split(r",\s*(?:and\s+)?|\s+and\s+", text) if p.strip()]


# ----------------------------------------------------------- reading a law --
def page_text(raw):
    """The page's text: scripts, styles and tags removed, one line per line."""
    t = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", raw)
    t = re.sub(r"<br\s*/?>|</p>|</div>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    t = re.sub(r"[ \t\xa0]+", " ", t)
    return [ln.strip() for ln in t.split("\n") if ln.strip()]


def reduce_law(raw, start):
    lines = page_text(raw)
    try:
        a = lines.index(start)
    except ValueError:
        wcc.fail(LABEL, "the page no longer carries the heading %r" % start)
    b = next((i for i in range(a, len(lines)) if lines[i].startswith(PAGE_END)), None)
    if b is None:
        wcc.fail(LABEL, "the page for %r has no footer after it" % start)
    return lines[a:b]


def law_lines(name):
    path = os.path.join(SOURCE, name)
    if not os.path.exists(path):
        wcc.fail(LABEL, "%s is missing; --fetch reads it" % os.path.relpath(path, REPO))
    with open(path, encoding="utf-8") as fh:
        lines = [ln.rstrip("\n") for ln in fh]
    body = [ln for ln in lines if ln and not ln.startswith("#")]
    if not body or body[0] != LAWS[name]["start"]:
        wcc.fail(LABEL, "%s does not start with the heading %r" % (name, LAWS[name]["start"]))
    return body


ATTEMPTS = 3
RETRY_SECONDS = 5.0


def _get(url):
    """One page, robots.txt read first with the same client, tried three times."""
    import time

    import requests
    from scraper_common import require_robots_once

    require_robots_once(url, USER_AGENT, label=LABEL)
    last = None
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_SECONDS * attempt)
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=120)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:  # reset, timeout, 5xx
            last = exc
    wcc.fail(LABEL, "%s did not answer after %d attempts (%s)" % (url, ATTEMPTS, last))


def fetch_laws():
    today = datetime.date.today().isoformat()
    for name, law in sorted(LAWS.items()):
        raw = _get(law["url"]).content
        lines = reduce_law(raw.decode("utf-8", "replace"), law["start"])
        path = os.path.join(SOURCE, name)
        old = law_lines(name) if os.path.exists(path) else None
        header = [
            "# %s" % law["title"],
            "# Read %s from %s with the client" % (today, law["url"]),
            "# %s, after its robots.txt." % USER_AGENT,
            "# The page was %s bytes, SHA-256 %s." % (format(len(raw), ","),
                                                       hashlib.sha256(raw).hexdigest()),
            "# Kept: the page's text from the section's heading to the end of its",
            "# history notes, with scripts, styles and tags removed, one line per line.",
        ]
        if old == lines:
            print("%s: %s is unchanged since it was last read" % (LABEL, name))
            continue
        os.makedirs(SOURCE, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(header + lines) + "\n")
        print("%s: %s %s — read it before building"
              % (LABEL, name, "CHANGED" if old else "written"))


# ------------------------------------------------------------- R.S. 13:477 --
def _ordinal_words():
    ones = "first second third fourth fifth sixth seventh eighth ninth".split()
    teens = ("tenth eleventh twelfth thirteenth fourteenth fifteenth sixteenth "
             "seventeenth eighteenth nineteenth").split()
    out = {w: i + 1 for i, w in enumerate(ones)}
    out.update({w: i + 10 for i, w in enumerate(teens)})
    for tens, word, flat in ((20, "twenty", "twentieth"), (30, "thirty", "thirtieth"),
                             (40, "forty", "fortieth")):
        out[flat] = tens
        for i, w in enumerate(ones):
            out["%s-%s" % (word, w)] = tens + i + 1
    return out


ORDINALS = _ordinal_words()
PARA_RE = re.compile(r"^The (?:parish|parishes) of (?P<names>.+?) shall compose the "
                     r"(?P<ord>[A-Za-z]+(?:-\s?[A-Za-z]+)?) District\.")
REPEAL_RE = re.compile(r"^Repealed by Acts \d{4}, No\. \d+")


def paragraphs(lines):
    out, cur = [], None
    for ln in lines[1:]:
        m = re.match(r"^\((\d{1,2})\) (.*)$", ln)
        if m:
            cur = [int(m.group(1)), [m.group(2)]]
            out.append(cur)
        elif re.match(r"^(Amended by|Added by|NOTE:)", ln):
            cur = None
        elif cur is not None:
            cur[1].append(ln)
    return [(n, " ".join(parts)) for n, parts in out]


def read_477(fabric):
    lines = law_lines("rs13-477.txt")
    head = " ".join(lines[1:3])
    if "There shall be forty-one judicial districts in the state" not in head:
        wcc.fail(LABEL, "13:477 no longer says there are forty-one judicial districts; "
                 "read it before building")
    paras = paragraphs(lines)
    numbers = [n for n, _t in paras]
    if numbers != list(range(1, len(numbers) + 1)):
        wcc.fail(LABEL, "13:477's paragraphs run %s, not 1 to %d in order"
                 % (numbers, len(numbers)))
    rows = []
    for n, text in paras:
        if REPEAL_RE.match(text):
            if n not in REPEALED:
                wcc.fail(LABEL, "13:477 paragraph (%d) is repealed; read it before building" % n)
            continue
        m = PARA_RE.match(text)
        if not m:
            wcc.fail(LABEL, "13:477 paragraph (%d) does not read as a district: %r"
                     % (n, text[:120]))
        word = re.sub(r"-\s+", "-", m.group("ord")).lower()
        if ORDINALS.get(word) != n:
            wcc.fail(LABEL, "13:477 paragraph (%d) composes the %s District" % (n, m.group("ord")))
        rows.append((str(n), resolve(split_names(m.group("names")), fabric,
                                     "13:477 paragraph (%d)" % n), {}))
    if len(rows) != JUDICIAL_DISTRICTS:
        wcc.fail(LABEL, "13:477 composes %d districts, and says there are %d"
                 % (len(rows), JUDICIAL_DISTRICTS))
    named = {c for _u, cs, _e in rows for c in cs}
    left = sorted(set(fabric.values()) - named)
    if left != [ORLEANS]:
        wcc.fail(LABEL, "13:477 leaves out %s, where only %s was expected" % (left, ORLEANS))
    rows.append((ORLEANS, [ORLEANS], {}))
    return rows


# ------------------------------------------------------------- R.S. 13:312 --
CIRCUIT_WORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}
# A list of names never holds "shall ", "the parish(es) of" or "(", which is what
# keeps a match from starting in an election section's sentence and running on
# into the next district's.
_NAMES = r"(?P<names>(?:(?!shall |[Tt]he parish(?:es)? of |\().)+?)"
CIRCUIT_RE = re.compile(r"\bThe parishes of " + _NAMES + r" shall compose the "
                        r"(?P<c>first|second|third|fourth|fifth) circuit\b")
DISTRICT_RE = re.compile(r"\b[Tt]he (?:parish|parishes) of " + _NAMES + r" shall compose "
                         r"the (?P<d>first|second|third) district of the "
                         r"(?P<c>first|second|third|fourth|fifth) circuit\b")
PORTION_RE = re.compile(r"\s*,?\s*(?:and\s+)?that portion of (?P<p>.+?) Parish "
                        r"(?P<side>(?:east|west) of the Mississippi River)")


def read_312(fabric):
    text = " ".join(law_lines("rs13-312.txt"))
    if "There shall be five court of appeal circuits" not in text:
        wcc.fail(LABEL, "13:312 no longer says there are five circuits; read it before building")
    circuits = {}
    for m in CIRCUIT_RE.finditer(text):
        c = CIRCUIT_WORDS[m.group("c")]
        if c in circuits:
            wcc.fail(LABEL, "13:312 composes the %s circuit twice" % m.group("c"))
        circuits[c] = set(resolve(split_names(m.group("names")), fabric, "13:312 circuit %d" % c))
    if sorted(circuits) != list(range(1, CIRCUITS + 1)):
        wcc.fail(LABEL, "13:312 composes circuits %s" % sorted(circuits))
    districts, portions = {}, {}
    for m in DISTRICT_RE.finditer(text):
        c, d = CIRCUIT_WORDS[m.group("c")], CIRCUIT_WORDS[m.group("d")]
        unit = "%d-%d" % (c, d)
        if unit in districts:
            wcc.fail(LABEL, "13:312 composes district %s twice" % unit)
        found = []

        def take(pm):
            found.append((pm.group("p"), pm.group("side")))
            return ""

        rest = PORTION_RE.sub(take, m.group("names"))
        whole = resolve(split_names(rest), fabric, "13:312 district %s" % unit)
        districts[unit] = (c, d, whole)
        for p, side in found:
            base = resolve([p], fabric, "13:312 district %s" % unit)[0]
            portions.setdefault(base, {})[unit] = side
    want = ["%d-%d" % (c, d) for c in range(1, CIRCUITS + 1)
            for d in range(1, DISTRICTS_PER_CIRCUIT + 1)]
    if sorted(districts) != want:
        wcc.fail(LABEL, "13:312 composes districts %s" % sorted(districts))
    for c, parishes in sorted(circuits.items()):
        mine = set()
        for unit, (cc, _d, whole) in districts.items():
            if cc == c:
                mine |= set(whole)
        mine |= {p for p, units in portions.items() if any(u.startswith("%d-" % c) for u in units)}
        if mine != parishes:
            wcc.fail(LABEL, "13:312's circuit %d is %s but its districts are %s"
                     % (c, sorted(parishes), sorted(mine)))
    if sorted(portions) != sorted(RIVER_PARISHES):
        wcc.fail(LABEL, "13:312 splits %s by the river, expected %s"
                 % (sorted(portions), sorted(RIVER_PARISHES)))
    rows = []
    for unit in want:
        c, d, whole = districts[unit]
        for p in whole:
            if p in portions:
                wcc.fail(LABEL, "13:312 puts %s in district %s whole and in part elsewhere"
                         % (p, unit))
        rows.append((unit, whole, {"circuit": c, "district": d}))
    for p, units in sorted(portions.items()):
        sides = sorted(units.values())
        if len(units) != 2 or sides != ["east of the Mississippi River",
                                         "west of the Mississippi River"]:
            wcc.fail(LABEL, "13:312 gives parts of %s to %s" % (p, units))
        circuit = {int(u.split("-")[0]) for u in units}
        if len(circuit) != 1:
            wcc.fail(LABEL, "13:312 gives parts of %s to two circuits" % p)
        order = sorted(units)
        rows.append(("/".join(order), [p], {"circuit": circuit.pop(), "units": order,
                                            "portions": {u: units[u] for u in order}}))
    return rows


def tilings():
    fabric = fabric_names()
    appeal = read_312(fabric)
    district = read_477(fabric)
    print("%s: 13:312 names %d circuits and %d districts, %s split by the river; "
          "13:477 names %d judicial districts, and Orleans has courts of its own"
          % (LABEL, CIRCUITS, CIRCUITS * DISTRICTS_PER_CIRCUIT, ", ".join(RIVER_PARISHES),
             JUDICIAL_DISTRICTS))
    return [
        wcc.Tiling("la-court-of-appeal-districts.json", "court of appeal district", appeal,
                   CIRCUITS * DISTRICTS_PER_CIRCUIT + len(RIVER_PARISHES), APPEAL_AUTHORITY),
        wcc.Tiling("la-district-court-districts.json", "judicial district", district,
                   JUDICIAL_DISTRICTS + 1, DISTRICT_AUTHORITY),
    ]


# -------------------------------------------------------- Supreme Court build --


def page_split_parishes(raw, fabric):
    if ZIP_PATH not in raw:
        wcc.fail(LABEL, "the Act 7 page no longer links %s; read it before building" % ZIP_PATH)
    names = sorted({html.unescape(m.group(1)).strip() for m in SPLIT_MAP_RE.finditer(raw)})
    names = [PAGE_NAMES.get(n, n) for n in names if n != "Statewide"]
    return sorted(resolve(names, fabric, "the Act 7 page's split-parish maps"))


def unpack(zip_path, into):
    """The four shapefile members, and nothing else, flat in `into`."""
    with zipfile.ZipFile(zip_path) as z:
        members = z.namelist()
        exts = sorted(os.path.splitext(m)[1].lower() for m in members)
        if sorted(ZIP_MEMBERS) != exts or any("/" in m or "\\" in m for m in members):
            wcc.fail(LABEL, "the Act 7 zip holds %r, not one flat shapefile" % members)
        for m in members:
            with z.open(m) as src, open(os.path.join(into, "act7" + os.path.splitext(m)[1].lower()),
                                        "wb") as dst:
                shutil.copyfileobj(src, dst)
    return os.path.join(into, "act7.shp")


def parish_shares(districts, fabric_path):
    """{parish: {unit: percent of the parish}}, every share over 0.0001%."""
    from shapely.geometry import shape

    shapes = {f["properties"]["unit"]: shape(f["geometry"]).buffer(0) for f in districts}
    with open(fabric_path) as fh:
        parishes = json.load(fh)["features"]
    out = {}
    for p in parishes:
        g = shape(p["geometry"]).buffer(0)
        shares = {u: 100.0 * g.intersection(s).area / g.area for u, s in shapes.items()}
        out[p["properties"]["BASENAME"]] = {u: v for u, v in shares.items() if v > 0.0001}
    return out


def classify(shares):
    """{unit: (whole, part)} from the shares, and the split parishes."""
    whole = {str(u): [] for u in range(1, SUPREME_DISTRICTS + 1)}
    part = {str(u): [] for u in range(1, SUPREME_DISTRICTS + 1)}
    split = []
    for parish, by in sorted(shares.items()):
        mid = {u: v for u, v in by.items() if SLIVER_PCT <= v < PART_PCT}
        if mid:
            wcc.fail(LABEL, "%s has %s in Supreme Court district(s) %s, between a sliver "
                     "(%.2f%%) and a part (%.1f%%); read the act's map before building"
                     % (parish, ", ".join("%.3f%%" % v for v in mid.values()),
                        ", ".join(sorted(mid)), SLIVER_PCT, PART_PCT))
        big = sorted(u for u, v in by.items() if v >= PART_PCT)
        if not big:
            wcc.fail(LABEL, "no Supreme Court district holds %.1f%% of %s" % (PART_PCT, parish))
        if len(big) == 1:
            whole[big[0]].append(parish)
        else:
            split.append(parish)
            for u in big:
                part[u].append(parish)
    return whole, part, split


def build_supreme(fabric):
    page = _get(PAGE).text
    listed = page_split_parishes(page, fabric)
    resp = _get(ZIP_URL)
    body = resp.content
    sha = hashlib.sha256(body).hexdigest()
    if sha != ZIP_SHA256:
        wcc.fail(LABEL, "the Act 7 file now has SHA-256 %s, not the %s it was read with; "
                 "read the new file before changing ZIP_SHA256" % (sha, ZIP_SHA256))
    with tempfile.TemporaryDirectory() as tmp:
        zpath = os.path.join(tmp, "act7.zip")
        with open(zpath, "wb") as fh:
            fh.write(body)
        shp_dir = os.path.join(tmp, "shp")
        os.makedirs(shp_dir)
        shp = unpack(zpath, shp_dir)
        src_path = os.path.join(tmp, "src.geojson")
        subprocess.run(["npx", "-y", blb.MAPSHAPER, "-i", shp, "-proj", "wgs84",
                        "-o", "format=geojson", src_path], check=True, cwd=REPO)
        with open(src_path) as fh:
            src = json.load(fh)["features"]
        units = sorted(int(f["properties"]["DISTRICT_I"]) for f in src)
        if units != list(range(1, SUPREME_DISTRICTS + 1)):
            wcc.fail(LABEL, "the Act 7 file's districts are %s" % units)
        for f in src:
            f["properties"] = {"unit": str(int(f["properties"]["DISTRICT_I"]))}
        with open(src_path, "w") as fh:
            json.dump({"type": "FeatureCollection", "features": src}, fh)
        out_path = os.path.join(tmp, "out.geojson")
        blb.run_mapshaper(src_path, SIMPLIFY, out_path)
        with open(out_path) as fh:
            drawn = json.load(fh)["features"]
    ok, msg = blb.validate(src, drawn, "unit")
    if not ok:
        wcc.fail(LABEL, "the drawn Supreme Court districts %s" % msg)
    step = blb.median_source_step_m(src)
    worst, over = blb.check_fidelity(src, drawn, "unit")
    if over:
        wcc.fail(LABEL, "district(s) %s stray past the %.0f m ceiling (worst %.1f m)"
                 % (", ".join(sorted(over)), blb.FIDELITY_CEILING_M, worst))
    shares = parish_shares(src, COUNTIES)
    whole, part, split = classify(shares)
    if split != sorted(SPLIT_PARISHES):
        wcc.fail(LABEL, "the act splits %s, where SPLIT_PARISHES says %s"
                 % (split, sorted(SPLIT_PARISHES)))
    if split != listed:
        wcc.fail(LABEL, "the overlay splits %s and the Act 7 page maps %s as split"
                 % (split, listed))
    slivers = [v for by in shares.values() for v in by.values() if v < SLIVER_PCT]
    parts = [v for p in split for v in shares[p].values() if v >= PART_PCT]
    feats = []
    for f in sorted(drawn, key=lambda f: int(f["properties"]["unit"])):
        u = f["properties"]["unit"]
        feats.append({"type": "Feature",
                      "properties": {"unit": u, "whole": whole[u], "part": part[u],
                                     "authority": SUPREME_AUTHORITY},
                      "geometry": f["geometry"]})
    body_out = json.dumps({"type": "FeatureCollection", "features": feats},
                          separators=(",", ":"))
    with open(os.path.join(APP, SUPREME_OUT), "w") as fh:
        fh.write(body_out)
    record = {
        "_about": ("GENERATED by la/scripts/build_la_court_districts.py. What the shipped "
                   "Supreme Court districts were drawn from and measured against; --check "
                   "holds the shipped file to this record."),
        "built": datetime.date.today().isoformat(),
        "page": PAGE,
        "zip": ZIP_URL,
        "zip_sha256": sha,
        "zip_bytes": len(body),
        "zip_last_modified": resp.headers.get("Last-Modified"),
        "simplify": "dp keep-shapes " + SIMPLIFY,
        "ceiling_m": blb.FIDELITY_CEILING_M,
        "median_source_step_m": round(step, 2),
        "worst_stray_m": round(worst, 2),
        "validation": msg,
        "split": {p: {u: round(v, 2) for u, v in sorted(shares[p].items()) if v >= PART_PCT}
                  for p in split},
        "largest_sliver_pct": round(max(slivers), 4) if slivers else 0.0,
        "smallest_part_pct": round(min(parts), 2),
        "shipped_sha256": hashlib.sha256(body_out.encode("utf-8")).hexdigest(),
    }
    with open(SUPREME_RECORD, "w") as fh:
        json.dump(record, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("%s: wrote %s — %d districts, %.1f KB; %s; median source step %.2f m, worst "
          "stray %.1f m against an %.0f m ceiling; %d split parishes, the largest sliver "
          "%.4f%% and the smallest part %.2f%%"
          % (LABEL, SUPREME_OUT, len(feats), len(body_out) / 1024.0, msg, step, worst,
             blb.FIDELITY_CEILING_M, len(split), record["largest_sliver_pct"],
             record["smallest_part_pct"]))


def check_supreme(fabric):
    path = os.path.join(APP, SUPREME_OUT)
    if not os.path.exists(path) or not os.path.exists(SUPREME_RECORD):
        wcc.fail(LABEL, "%s or its record is missing; run this builder" % SUPREME_OUT)
    with open(path, "rb") as fh:
        raw = fh.read()
    with open(SUPREME_RECORD) as fh:
        record = json.load(fh)
    if hashlib.sha256(raw).hexdigest() != record.get("shipped_sha256"):
        wcc.fail(LABEL, "%s is not the file its record describes; rebuild it" % SUPREME_OUT)
    if record.get("zip_sha256") != ZIP_SHA256 or record.get("zip") != ZIP_URL:
        wcc.fail(LABEL, "the record was built from another file than ZIP_URL and ZIP_SHA256")
    feats = json.loads(raw)["features"]
    units = [f["properties"].get("unit") for f in feats]
    if units != [str(u) for u in range(1, SUPREME_DISTRICTS + 1)]:
        wcc.fail(LABEL, "%s ships districts %s" % (SUPREME_OUT, units))
    names = set(fabric.values())
    where = {}
    for f in feats:
        p = f["properties"]
        if set(p) != {"unit", "whole", "part", "authority"} or p["authority"] != SUPREME_AUTHORITY:
            wcc.fail(LABEL, "district %s ships properties %s" % (p.get("unit"), sorted(p)))
        for kind in ("whole", "part"):
            if p[kind] != sorted(p[kind]) or not set(p[kind]) <= names:
                wcc.fail(LABEL, "district %s's %s list is %s" % (p["unit"], kind, p[kind]))
            for parish in p[kind]:
                where.setdefault(parish, []).append((kind, p["unit"]))
    if set(where) != names:
        wcc.fail(LABEL, "%s leaves out %s" % (SUPREME_OUT, sorted(names - set(where))))
    split = []
    for parish, places in sorted(where.items()):
        kinds = {k for k, _u in places}
        if kinds == {"whole"} and len(places) == 1:
            continue
        if kinds == {"part"} and len(places) >= 2:
            split.append(parish)
            continue
        wcc.fail(LABEL, "%s is in %s" % (parish, places))
    if split != sorted(SPLIT_PARISHES) or split != sorted(record.get("split", {})):
        wcc.fail(LABEL, "%s splits %s, where SPLIT_PARISHES says %s"
                 % (SUPREME_OUT, split, sorted(SPLIT_PARISHES)))
    if record.get("worst_stray_m", 99) > record.get("ceiling_m", 0):
        wcc.fail(LABEL, "the record's worst stray is over its ceiling")
    print("%s: %s — %d districts, every parish whole in one or split among two or more, "
          "the %d split parishes as pinned; worst stray %.1f m of %.0f m"
          % (LABEL, SUPREME_OUT, len(feats), len(split), record["worst_stray_m"],
             record["ceiling_m"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--check", action="store_true", help="verify the shipped files, write nothing")
    ap.add_argument("--fetch", action="store_true", help="re-read the two laws into "
                    "la/data/source/courts/ and say whether either changed")
    args = ap.parse_args()
    if args.fetch:
        fetch_laws()
        return
    if args.check:
        wcc.check("la", LABEL, tilings())
        check_supreme(fabric_names())
        print("%s: OK" % LABEL)
        return
    wcc.build("la", LABEL, tilings())
    build_supreme(fabric_names())


if __name__ == "__main__":
    main()
