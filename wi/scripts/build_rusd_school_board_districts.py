#!/usr/bin/env python3
"""
Build data/app/rusd-school-board-districts.json — Racine Unified's nine board
election districts, the other half of Wisconsin's districted-school-board pair.

WHY THIS EXISTS AND WHY IT LOOKS NOTHING LIKE THE MPS BUILD. Statute names the
districted school boards exactly: MPS (ch. 119) and Racine Unified
(s. 120.42(1)(d)2). MPS publishes real geometry and ships from it. RUSD does
not, and gap `rusd-school-board` recorded that correctly for over a week —
while recording the ROUTES OUT wrongly. It listed exactly two: a Jackson-style
vector-path extraction from RUSD's ArcMap PDFs "IF the PDFs carry real path
objects", or asking RUSD for the boundary file.

BOTH OF THOSE ARE BESIDE THE POINT, AND THE FIRST IS MEASURED SHUT.

Shut, first, so nobody re-tries it: all 21 of RUSD's district-map PDFs were
read on 2026-09-03 and carry ZERO filled path objects. District 1's content
stream is 4,881 `S` (stroke) operators and 73 `Do` (draw XObject — the raster
basemap tiles), with two `f*` and three `B*` fills, and those are the legend
swatches. The overview sheet is the same shape with 25. The Jackson method
reads the fill OBJECTS whose colours pair one-for-one with a legend; there are
no filled district polygons here to read. That question is answered.

Beside the point, second, because RUSD'S DISTRICTS ARE UNIONS OF WHOLE WARDS
AND RUSD PUBLISHES THE COMPOSITION AS A TABLE. The maps say so themselves —
each prints "District Boundaries generated from WSL LTSB's WISE-LR software"
over "U.S. Census Bureau 2020 TIGER Municipal Boundary and Block Data" — and
the district's own board-election documents page carries a one-page PDF titled
"Election District by Municipality" listing every ward in every district. So
the geometry is a DISSOLVE of the LTSB ward layer this instance already
fetches live, and no map is read, nothing is georeferenced, and nothing is
traced. The gap record's blocker was a fact about two routes it had thought
of, published as a fact about the world.

THE FILENAME LIES AND THE CONTENT DOES NOT. That PDF is served as
`Districts-Up-for-Election-2026.pdf`, which reads like a list of the seats on
one ballot; it is the FULL nine-district composition. RUSD's board page says
districts 2, 4, 5 and 6 are up in April 2027, so a future
`Districts-Up-for-Election-2027.pdf` may well carry four districts under a
near-identical name. This build therefore discovers the document BY CONTENT —
every PDF on the documents page is fetched and the one whose first page is
titled "Election District by Municipality" is the input — and the partition
gate below fails loudly on a four-district document rather than shipping a
third of a map.

THE PARSE IS POSITIONAL, for the reason the WEC clerk build already records:
the page is THREE column-groups of (District, Municipality, Ward) side by
side, so a flattened `extract_text()` reads across them and interleaves
District 1's wards with District 4's and District 7's. The x-windows are read
off the three header triples on the page, never guessed, and District and
Municipality carry forward down a group because the table prints each only
when it changes.

FOUR GATES, EACH CATCHING A DIFFERENT WAY THIS CAN GO WRONG:

  1. EXACT PARTITION. Nine districts, 116 wards, and within each of the seven
     municipalities the wards run 1..n with no gap and no ward claimed twice.
     A district dropped by the parse, a column misread, or next year's
     four-district document all fail here.
  2. TOTAL JOIN to LTSB's CURRENT Racine County wards — 116 of 116, with no
     ward in an RUSD municipality left unclaimed. This is the Jasper test in
     Wisconsin clothing: it fails the day Racine re-wards, which is exactly
     when a composition drawn against the old fabric must stop shipping.
  3. INDEPENDENT WITNESS. The union of the nine reproduces the Census's own
     Racine School District — a different publisher entirely — on sampled
     points. Measured 2026-09-03: 99.97% of 4,000 points agree, the one
     disagreement a boundary sliver from the shipped TIGER file's own
     simplification, and the two bounding boxes identical to four decimals.
  4. NO EMPTY DISTRICT after the dissolve.

ONE ALIAS, and it is the class this instance already carries: RUSD writes
"Mt. Pleasant" where LTSB writes "Mount Pleasant". No other name differs.

An OPERATOR rebuild, not a weekly one — the composition moves when RUSD
redistricts (decennial) or Racine re-wards (the 15 Jan / 15 Jul LTSB windows),
both of which are WATCH.md rows. The PEOPLE are weekly and separate:
`rusd_school_board_scraper.py` reads the district's own board page.
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
OUT_PATH = os.path.join(REPO_ROOT, "data", "app", "rusd-school-board-districts.json")
TIGER_UNIFIED = os.path.join(REPO_ROOT, "data", "app", "school-districts-unified.json")

DOCS_PAGE = ("https://www.rusd.org/documents/about/board-of-education"
             "/board-election-information/642739")
DOC_TITLE = "Election District by Municipality"

LTSB_WARDS = ("https://mapservices.legis.wisconsin.gov/arcgis/rest/services"
              "/BAS_Collection/BAS_Live_Collection_Wards/FeatureServer/0/query")

# TIGER's own GEOID for the Racine School District, in the unified-district
# file this instance already ships. The witness comparand.
TIGER_GEOID = "5512360"

MAPSHAPER = "mapshaper@0.6.102"          # pinned, fleet convention

EXPECT_DISTRICTS = [str(n) for n in range(1, 10)]
EXPECT_WARDS = 116
EXPECT_MUNICIPALITIES = {
    "Caledonia": 21, "Elmwood Park": 1, "Mount Pleasant": 25, "North Bay": 1,
    "Racine": 57, "Sturtevant": 8, "Wind Point": 3,
}
MIN_TIGER_AGREEMENT = 0.99
SAMPLE_POINTS = 4000
SAMPLE_SEED = 20260903

# RUSD's spelling -> LTSB's. The only one; a second appearing is a page
# reshape and the join gate below is what says so.
MUNI_ALIASES = {"Mt. Pleasant": "Mount Pleasant"}

UA = {"User-Agent": "districtry-wisconsin/1.0 (+https://districtry.com/wi/)"}


def fetch(url, binary=False, tries=4, timeout=90):
    """The instance's standard ladder — a single un-retried timeout is what
    left two of these workflows never once green."""
    # THE SITE'S RULES ARE READ BEFORE THE FIRST FETCH, with the identity this
    # fetch sends, once per host. Measured from a GitHub runner on 2026-10-01,
    # which is the vantage this builder runs from: mapservices.legis.wisconsin.gov
    # answers HTTP 404 for robots.txt, so it publishes no rules and every path is
    # permitted. Its earlier reading as unreadable was a timeout on one runner
    # moment, which RFC 9309 files as disallow-all and is not a policy.
    require_robots_once(url, UA["User-Agent"], headers=UA,
                        label="wi-rusd-school-board-districts")
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            return data if binary else data.decode("utf-8", "replace")
        except Exception as exc:                      # noqa: BLE001
            last = exc
            if i + 1 < tries:
                time.sleep(2 * (i + 1))
    raise SystemExit("fetch failed after %d tries: %s\n  %s" % (tries, url, last))


# --------------------------------------------------------------------------
# 1. Find the composition document BY CONTENT
# --------------------------------------------------------------------------

def find_composition_pdf():
    import pdfplumber
    import io

    page = fetch(DOCS_PAGE)
    urls = sorted(set(re.findall(r'https://files-backend\.assets\.thrillshare\.com'
                                 r'/[^"\'\\ <]+?\.pdf', page)))
    if not urls:
        raise SystemExit("no PDFs found on %s — the documents page has reshaped"
                         % DOCS_PAGE)
    hits = []
    for u in urls:
        blob = fetch(u, binary=True)
        if not blob.startswith(b"%PDF"):
            continue                                   # a login page served 200
        try:
            with pdfplumber.open(io.BytesIO(blob)) as pdf:
                first = pdf.pages[0].extract_text() or ""
        except Exception:                              # noqa: BLE001
            continue
        if first.lstrip().startswith(DOC_TITLE):
            hits.append((u, blob))
    if len(hits) != 1:
        raise SystemExit(
            "expected exactly one PDF on the documents page titled %r, found %d "
            "— identify the current one by hand before shipping a composition"
            % (DOC_TITLE, len(hits)))
    print("composition document: %s" % hits[0][0].rsplit("/", 1)[-1], file=sys.stderr)
    return hits[0]


# --------------------------------------------------------------------------
# 2. Parse it POSITIONALLY
# --------------------------------------------------------------------------

def parse_composition(blob):
    import pdfplumber
    import io

    with pdfplumber.open(io.BytesIO(blob)) as pdf:
        if len(pdf.pages) != 1:
            raise SystemExit("composition PDF has %d pages, expected 1 — reshaped"
                             % len(pdf.pages))
        words = pdf.pages[0].extract_words()

    # The three column-groups announce themselves: each prints the header
    # triple "Election District | Municipality | Ward" on one line. Read the
    # windows off THOSE rather than pinning coordinates.
    #
    # ANCHOR ON "Ward", NOT ON "Municipality". The page's own TITLE is
    # "Election District by Municipality", so the topmost row carrying the
    # word Municipality is the title and its band holds one of each header
    # word and no Ward at all. Anchoring there finds 1/1/0 column groups and
    # the gate below refuses — correctly, but for the wrong reason, which is
    # a day lost. The title contains no "Ward".
    tops = [w["top"] for w in words if w["text"] == "Ward"]
    if not tops:
        raise SystemExit("no 'Ward' column header on the composition page")
    hdr_top = min(tops)
    band = [w for w in words if abs(w["top"] - hdr_top) < 2]
    starts = sorted(w["x0"] for w in band if w["text"] == "Election")
    munis = sorted(w["x0"] for w in band if w["text"] == "Municipality")
    wards = sorted(w["x0"] for w in band if w["text"] == "Ward")
    if not (len(starts) == len(munis) == len(wards) == 3):
        raise SystemExit(
            "expected three (Election District, Municipality, Ward) column groups, "
            "found %d/%d/%d — the page has reshaped and a flattened read would "
            "interleave three districts' wards" % (len(starts), len(munis), len(wards)))

    groups = []
    for i in range(3):
        nxt = starts[i + 1] if i + 1 < 3 else 10 ** 6
        groups.append(((starts[i] - 20, munis[i] - 10),          # district
                       (munis[i] - 10, wards[i] - 10),           # municipality
                       (wards[i] - 10, nxt - 20)))               # ward

    rows = {}
    for w in words:
        if w["top"] <= hdr_top + 2:
            continue                                   # title + header band
        for gi, cols in enumerate(groups):
            for kind, (lo, hi) in zip("dmw", cols):
                if lo <= w["x0"] < hi:
                    rows.setdefault((gi, round(w["top"], 1)), {}) \
                        .setdefault(kind, []).append((w["x0"], w["text"]))

    def cell(r, k):
        v = r.get(k)
        return " ".join(t for _, t in sorted(v)) if v else None

    comp = {}
    for gi in range(3):
        cur_d = cur_m = None
        for key in sorted((k for k in rows if k[0] == gi), key=lambda k: k[1]):
            r = rows[key]
            d, m, ward = cell(r, "d"), cell(r, "m"), cell(r, "w")
            if d is not None:
                cur_d, cur_m = d, None
            if m is not None:
                cur_m = m
            if ward is None:
                continue
            if cur_d is None or cur_m is None:
                raise SystemExit("ward %r at %r has no district or municipality "
                                 "above it — the column windows are wrong" % (ward, key))
            comp.setdefault(cur_d, {}).setdefault(cur_m, []).append(ward)
    return comp


# --------------------------------------------------------------------------
# 3. GATE 1 — an exact partition
# --------------------------------------------------------------------------

def keyed_wards(comp):
    if sorted(comp, key=int) != EXPECT_DISTRICTS:
        raise SystemExit(
            "composition names districts %s, expected %s — a partial document "
            "(the filename says which election, the CONTENT is the whole map) "
            "or a parse that lost a column"
            % (sorted(comp, key=int), EXPECT_DISTRICTS))

    want = {}
    for d, munis in comp.items():
        for m, ws in munis.items():
            muni = MUNI_ALIASES.get(m, m)
            for w in ws:
                if not w.isdigit():
                    raise SystemExit("ward %r in district %s is not a number" % (w, d))
                key = (muni, int(w))
                if key in want:
                    raise SystemExit("ward %s %s is claimed by districts %s and %s"
                                     % (muni, w, want[key], d))
                want[key] = int(d)

    by_muni = {}
    for (muni, w) in want:
        by_muni.setdefault(muni, []).append(w)
    if set(by_muni) != set(EXPECT_MUNICIPALITIES):
        raise SystemExit("composition covers %s, expected %s"
                         % (sorted(by_muni), sorted(EXPECT_MUNICIPALITIES)))
    for muni, ws in sorted(by_muni.items()):
        ws = sorted(ws)
        if ws != list(range(1, len(ws) + 1)):
            raise SystemExit("%s's wards are not 1..n with no gap: %s" % (muni, ws))
        if len(ws) != EXPECT_MUNICIPALITIES[muni]:
            raise SystemExit("%s contributes %d wards, expected %d — the municipality "
                             "has re-warded, or the parse dropped a row"
                             % (muni, len(ws), EXPECT_MUNICIPALITIES[muni]))
    if len(want) != EXPECT_WARDS:
        raise SystemExit("composition holds %d wards, expected %d"
                         % (len(want), EXPECT_WARDS))
    print("partition: %d districts, %d wards over %d municipalities, each 1..n"
          % (len(comp), len(want), len(by_muni)), file=sys.stderr)
    return want


# --------------------------------------------------------------------------
# 4. GATE 2 — a TOTAL join to LTSB's current wards
# --------------------------------------------------------------------------

def join_ltsb(want):
    url = (LTSB_WARDS + "?where=" + urllib.parse.quote("CNTY_NAME='Racine'")
           + "&outFields=GEOID,MCD_NAME,CTV,WARDID&outSR=4326&f=geojson")
    geo = json.loads(fetch(url))
    have = {}
    for f in geo.get("features", []):
        p = f["properties"]
        have[(p["MCD_NAME"], int(p["WARDID"]))] = f

    missing = sorted(k for k in want if k not in have)
    if missing:
        raise SystemExit(
            "RUSD names %d ward(s) LTSB's current filing does not have: %s — the "
            "municipality has re-warded and this composition is drawn against the "
            "old fabric" % (len(missing), missing[:8]))
    stray = sorted(k for k in have
                   if k[0] in EXPECT_MUNICIPALITIES and k not in want)
    if stray:
        raise SystemExit(
            "LTSB files %d ward(s) in an RUSD municipality that no district claims: "
            "%s — the composition no longer covers these municipalities"
            % (len(stray), stray[:8]))

    out = {"type": "FeatureCollection", "features": []}
    for key, d in sorted(want.items(), key=lambda kv: (kv[1], kv[0])):
        f = dict(have[key])
        f["properties"] = {"district": str(d), "muni": key[0], "ward": key[1]}
        out["features"].append(f)
    print("join: %d of %d wards matched LTSB's current Racine County filing, "
          "no unclaimed ward in an RUSD municipality" % (len(out["features"]), len(want)),
          file=sys.stderr)
    return out


# --------------------------------------------------------------------------
# 5. Dissolve, and GATE 3 — the independent witness
# --------------------------------------------------------------------------

def rings_of(g):
    return [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]


def contains(pt, g):
    x, y = pt
    for poly in rings_of(g):
        def inring(ring):
            c = False
            n = len(ring)
            for a in range(n):
                x1, y1 = ring[a][:2]
                x2, y2 = ring[(a + 1) % n][:2]
                if (y1 > y) != (y2 > y):
                    if x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                        c = not c
            return c
        if inring(poly[0]) and not any(inring(h) for h in poly[1:]):
            return True
    return False


def bbox(g):
    xs, ys = [], []
    for poly in rings_of(g):
        for ring in poly:
            for p in ring:
                xs.append(p[0])
                ys.append(p[1])
    return min(xs), min(ys), max(xs), max(ys)


def run_mapshaper(src, args, out):
    subprocess.run(["npx", "-y", MAPSHAPER, src] + args
                   + ["-o", "format=geojson", "precision=0.000001", out],
                   check=True, stdout=subprocess.DEVNULL)


def witness_against_tiger(union_geom):
    import random
    tiger = None
    for f in json.load(open(TIGER_UNIFIED))["features"]:
        if f["properties"]["GEOID"] == TIGER_GEOID:
            tiger = f["geometry"]
    if tiger is None:
        raise SystemExit("TIGER GEOID %s absent from %s — the shipped unified-district "
                         "file has changed" % (TIGER_GEOID, TIGER_UNIFIED))

    ub, tb = bbox(union_geom), bbox(tiger)
    random.seed(SAMPLE_SEED)
    X0, Y0 = min(ub[0], tb[0]), min(ub[1], tb[1])
    X1, Y1 = max(ub[2], tb[2]), max(ub[3], tb[3])
    both = only_u = only_t = 0
    tries = 0
    while both + only_u + only_t < SAMPLE_POINTS and tries < SAMPLE_POINTS * 200:
        tries += 1
        p = (random.uniform(X0, X1), random.uniform(Y0, Y1))
        a, b = contains(p, union_geom), contains(p, tiger)
        if a and b:
            both += 1
        elif a:
            only_u += 1
        elif b:
            only_t += 1
    tot = both + only_u + only_t
    share = both / tot if tot else 0.0
    print("witness: %.2f%% of %d points agree with the Census's own Racine School "
          "District (ward-union only %d, TIGER only %d)"
          % (100 * share, tot, only_u, only_t), file=sys.stderr)
    if share < MIN_TIGER_AGREEMENT:
        raise SystemExit(
            "the nine districts' union agrees with TIGER's Racine School District on "
            "only %.2f%% of %d points (floor %.0f%%) — two publishers disagree about "
            "where this district is and neither is checked by the other"
            % (100 * share, tot, 100 * MIN_TIGER_AGREEMENT))


def main():
    import tempfile

    _url, blob = find_composition_pdf()
    comp = parse_composition(blob)
    want = keyed_wards(comp)
    keyed = join_ltsb(want)

    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "wards.json")
        json.dump(keyed, open(src, "w"))
        dis = os.path.join(tmp, "districts.json")
        uni = os.path.join(tmp, "union.json")
        run_mapshaper(src, ["-dissolve", "district", "copy-fields=district"], dis)
        run_mapshaper(src, ["-dissolve"], uni)
        districts = json.load(open(dis))
        u = json.load(open(uni))

    union_geom = (u["geometries"][0] if u.get("type") == "GeometryCollection"
                  else u["features"][0]["geometry"])
    witness_against_tiger(union_geom)

    feats = sorted(districts["features"], key=lambda f: int(f["properties"]["district"]))
    if [f["properties"]["district"] for f in feats] != EXPECT_DISTRICTS:
        raise SystemExit("dissolve produced %s, expected %s"
                         % ([f["properties"]["district"] for f in feats], EXPECT_DISTRICTS))
    for f in feats:                                     # GATE 4
        if not f.get("geometry") or not f["geometry"].get("coordinates"):
            raise SystemExit("district %s dissolved to nothing"
                             % f["properties"]["district"])

    # Sorted by (municipality, ward NUMBER) — a lexical sort on the rendered
    # string puts Racine 10 between Racine 1 and Racine 2 on the card.
    wards_by_district = {}
    for f in keyed["features"]:
        p = f["properties"]
        wards_by_district.setdefault(p["district"], []).append((p["muni"], p["ward"]))

    out = {"type": "FeatureCollection", "features": []}
    for f in feats:
        d = f["properties"]["district"]
        out["features"].append({
            "type": "Feature",
            "properties": {"district": d,
                           "wards": ["%s %d" % mw
                                     for mw in sorted(wards_by_district[d])]},
            "geometry": f["geometry"],
        })
    with open(OUT_PATH, "w") as fh:
        json.dump(out, fh)
    print("wrote data/app/%s — %d districts dissolved from %d whole wards "
          "(composition: RUSD's own %r; geometry: LTSB's live ward layer; "
          "witnessed against the Census's Racine School District)"
          % (os.path.basename(OUT_PATH), len(out["features"]),
             len(keyed["features"]), DOC_TITLE), file=sys.stderr)


if __name__ == "__main__":
    main()
