#!/usr/bin/env python3
"""The gates every Michigan city-ward builder shares, in one copy.

Seven builders (Detroit's aside) each carried their own copy of the same twelve
helpers — the even-odd point test, the Esri error-envelope check, the
point-agreement sampler, the Census tiling gate — and the copies had already
begun to drift (Flint's curl sends no User-Agent; Jackson's does). The five
cities drawn on 2026-10-15 (Holland, Ann Arbor, Midland, Muskegon, Pontiac)
read these from here instead, so a fix lands once. The older builders are left
as they are: rewriting a builder that already ships, to change nothing it
writes, is a change with only downside.

WHAT A BUILDER SUPPLIES. A `cfg` dict and the source features keyed by ward:

  name            "Holland" — used in messages
  slug            "holland" — the build's log prefix and temp-file stem
  out_file        "mi-holland-wards.json"
  place_geoid     the Census 2020 place, whose NAME must equal place_name
  place_name      "Holland city"
  state_where     the SQL that selects this city's precincts in the state's
                  2026 fabric — always with COUNTYFIPS, because a city name is
                  not unique in Michigan
  expect_wards    ("1", .., "6")
  expect_state    {ward: precinct count} in the state's fabric
  agreement       "union", "lines" or "residents" (below)
  agreement_why   required with "residents": why area cannot answer for this city
  robots_urls     every URL the build fetches, so each host is asked first

THE TWO AGREEMENT RULES. Both compare the city's wards against the state's
precincts dissolved by their WARD column, at 4,000 random points inside either.

  "union"  same / (points in EITHER map) >= 99%. The rule every Michigan ward
           layer shipped under before 2026-10-15. It counts a point that one
           map covers and the other does not as a disagreement, so it fails
           a city whose ward map has not caught up with an annexation even
           when every ward LINE matches.
  "lines"  same / (points in BOTH maps) >= 99%, which is whether the two
           publishers draw the same ward lines, with the outer edge held
           separately by the Census tiling gate below (population inside the
           wards against population inside the Census city, within 0.2%, and
           at most 60 blocks on different sides of the two outlines). This is
           the rule recommended to the operator on 2026-10-15 for cities whose
           only difference from the state is the city's outer edge.

  "residents" same / (people in BOTH maps) >= 99%, counted over every
           populated Census 2020 block at its internal point, so it asks
           whether a person at home is told the same ward by both publishers.
           Added 2026-10-22 for Bay City, where the two maps divide the
           Saginaw River and the empty Middleground Island differently and
           agree on every resident (32,649 of 32,649), while the area rules
           read 98.4% "lines" because a river is mostly area. A builder must
           say why in `agreement_why`, and the area figures still print, so
           this rule cannot be picked to make a gap disappear quietly. Its
           cost is stated rather than hidden: a click on the river or the
           island can name a different ward from the state's precincts.

Both area figures are printed on every run whichever rule gates, so a reader
of the log sees the edge difference rather than having it hidden by the rule.
"""

import json
import os
import random
import re
import subprocess
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE_ROOT = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(INSTANCE_ROOT)
APP_DATA_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
MAPSHAPER = "mapshaper@0.6.25"
USER_AGENT = "districtry/1.0 (+https://districtry.com/mi/)"
PRECISION = "0.000001"

STATE_PRECINCTS = ("https://services3.arcgis.com/dxRQUfTDNtfqZ301/arcgis/rest/"
                   "services/2026_Voting_Precincts/FeatureServer/0")
BLOCKS = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
          "tigerWMS_Census2020/MapServer/10/query")
PLACE = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
         "tigerWMS_Census2020/MapServer/26/query")

MIN_AGREEMENT = 0.99
MAX_POP_DELTA_FRACTION = 0.002
MAX_EDGE_BLOCKS = 60
SHIPPED_FIELDS = ("WARD", "Ward")


class BuildError(Exception):
    pass


def fail(cfg, msg):
    print("build-mi-%s-wards: FAIL — %s" % (cfg["slug"], msg), file=sys.stderr)
    sys.exit(1)


# --- fetching ----------------------------------------------------------------
def curl_bytes(url, timeout=300):
    return subprocess.run(["curl", "-sS", "--fail", "--location", "--max-time", str(timeout),
                           "--retry", "3", "--retry-all-errors", "--retry-delay", "3",
                           "-A", USER_AGENT, url],
                          check=True, capture_output=True).stdout


def curl_json(url, timeout=300):
    d = json.loads(curl_bytes(url, timeout))
    if isinstance(d, dict) and "error" in d:
        raise BuildError("%s answered an error envelope: %r" % (url, d["error"]))
    return d


def esri(url, params, timeout=300):
    """GeoJSON from an ArcGIS query. An Esri error envelope arrives as HTTP 200,
    so an empty answer is read as 'the query or the service moved', never as
    'nothing there'."""
    p = {"f": "geojson", "outSR": 4326, "geometryPrecision": 6}
    p.update(params)
    u = url + ("/query?" if not url.endswith("/query") else "?") + urllib.parse.urlencode(p)
    d = curl_json(u, timeout)
    feats = d.get("features") or []
    if not feats:
        raise BuildError("%s returned no features — read this as 'the field list or the "
                         "service moved', not an outage" % url)
    if d.get("exceededTransferLimit"):
        raise BuildError("%s hit its transfer cap — needs paging" % url)
    return feats


def require_robots(cfg):
    sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
    from scraper_common import require_robots_once
    for url in list(cfg["robots_urls"]) + [STATE_PRECINCTS, BLOCKS]:
        print("  robots: %s -> %s" % (urllib.parse.urlsplit(url).hostname,
                                      require_robots_once(url, USER_AGENT,
                                                          label="build-mi-%s-wards" % cfg["slug"])))


def item_terms(item_id):
    """An ArcGIS Online item's licenseInfo, tags stripped."""
    item = curl_json("https://www.arcgis.com/sharing/rest/content/items/%s?f=json" % item_id, 120)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", item.get("licenseInfo") or "")).strip()


def service_text(url):
    """What an ArcGIS Server service or layer states about itself."""
    d = curl_json(url + ("&" if "?" in url else "?") + "f=json", 120)
    out = []
    for k in ("copyrightText", "serviceDescription", "description"):
        v = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", d.get(k) or "")).strip()
        if v:
            out.append("%s: %s" % (k, v))
    return out


# --- geometry ----------------------------------------------------------------
def _in_ring(pt, ring):
    x, y = pt
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-15) + xi):
            inside = not inside
        j = i
    return inside


def in_geometry(pt, geom):
    """index.html's rule: even-odd within a Polygon, ANY part of a MultiPolygon."""
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        if not poly or not _in_ring(pt, poly[0]):
            continue
        if any(_in_ring(pt, hole) for hole in poly[1:]):
            continue
        return True
    return False


def ward_number(v):
    """A ward key normalised NUMERICALLY, so "01", "Ward 1" and "1" agree."""
    if v in (None, ""):
        return None
    m = re.search(r"\d+", str(v))
    return str(int(m.group(0))) if m else None


def state_ward(props):
    return ward_number(props.get("WARD"))


def model(features, key):
    return [(key(f.get("properties") or {}), f["geometry"])
            for f in features if f.get("geometry")]


def bbox(features):
    xs, ys = [], []

    def walk(c):
        if isinstance(c[0], (int, float)):
            xs.append(c[0]); ys.append(c[1])
        else:
            for q in c:
                walk(q)
    for f in features:
        walk(f["geometry"]["coordinates"])
    return min(xs), min(ys), max(xs), max(ys)


def point_agreement(a, b, box, samples=4000, seed=20261015):
    rng = random.Random(seed)
    hit = same = diff = only_a = only_b = 0
    tried = 0
    while hit < samples and tried < samples * 80:
        tried += 1
        pt = (rng.uniform(box[0], box[2]), rng.uniform(box[1], box[3]))
        ha = [k for k, g in a if in_geometry(pt, g)]
        hb = [k for k, g in b if in_geometry(pt, g)]
        if not ha and not hb:
            continue
        hit += 1
        if ha and hb:
            if ha[0] == hb[0]:
                same += 1
            else:
                diff += 1
        elif ha:
            only_a += 1
        else:
            only_b += 1
    both = same + diff
    return {"hit": hit, "same": same, "diff": diff, "only_a": only_a, "only_b": only_b,
            "union": (same / hit) if hit else 0.0,
            "lines": (same / both) if both else 0.0}


def resident_agreement(cfg, a, b, blocks):
    """The share of people, among those both maps place in a ward, whom both
    maps place in the SAME ward, counted at each populated block's internal
    point. Everything it counts is printed."""
    same = diff = only_a = only_b = 0
    for lon, lat, pop in blocks:
        if not pop:
            continue
        ka = next((k for k, g in a if in_geometry((lon, lat), g)), None)
        kb = next((k for k, g in b if in_geometry((lon, lat), g)), None)
        if ka is None and kb is None:
            continue
        if ka is not None and kb is not None:
            if ka == kb:
                same += pop
            else:
                diff += pop
                print("    %d people at %.5f,%.5f: Ward %s here, Ward %s in the state's "
                      "precincts" % (pop, lat, lon, ka, kb))
        elif ka is not None:
            only_a += pop
        else:
            only_b += pop
    print("  residents: %d told the same ward by both maps, %d a different one; %d only "
          "inside %s's wards, %d only inside the state's (the outer edge, held by the "
          "tiling gate)" % (same, diff, only_a, cfg["name"], only_b))
    print("    rule reason: %s" % cfg["agreement_why"])
    if same + diff == 0:
        fail(cfg, "no resident is inside both maps — the block or precinct query moved")
    return same / (same + diff)


def overlaps(m, box, samples=2000, seed=7):
    rng = random.Random(seed)
    n = 0
    for _ in range(samples):
        pt = (rng.uniform(box[0], box[2]), rng.uniform(box[1], box[3]))
        if len([k for k, g in m if in_geometry(pt, g)]) > 1:
            n += 1
    return n


def counts_by(features, key):
    out = {}
    for f in features:
        k = key(f.get("properties") or {})
        out[k] = out.get(k, 0) + 1
    return out


def dissolve(cfg, features, key):
    """Dissolve source features on their ward with mapshaper, at the fleet's
    6-decimal precision and nothing else."""
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    src = os.path.join(APP_DATA_DIR, ".%s-wards-src.json" % cfg["slug"])
    out = os.path.join(APP_DATA_DIR, ".%s-wards-dissolved.json" % cfg["slug"])
    with open(src, "w") as f:
        json.dump({"type": "FeatureCollection",
                   "features": [{"type": "Feature",
                                 "properties": {"WARD": key(p.get("properties") or {})},
                                 "geometry": p["geometry"]} for p in features]}, f)
    try:
        subprocess.run(["npx", "-y", MAPSHAPER, src, "-dissolve", "WARD",
                        "-o", "precision=" + PRECISION, "format=geojson", out],
                       check=True)
        with open(out) as f:
            return json.load(f)["features"]
    finally:
        for p in (src, out):
            if os.path.exists(p):
                os.remove(p)


# --- Census tiling -------------------------------------------------------------
def fetch_blocks(box, minimum):
    env = "%2C".join("%.5f" % v for v in box)
    url = (BLOCKS + "?where=STATE%3D%2726%27&geometry=" + env +
           "&geometryType=esriGeometryEnvelope&inSR=4326"
           "&spatialRel=esriSpatialRelIntersects"
           "&outFields=POP100,INTPTLAT,INTPTLON&returnGeometry=false"
           "&outSR=4326&f=json&resultRecordCount=100000")
    d = curl_json(url, timeout=600)
    if d.get("exceededTransferLimit"):
        raise BuildError("TIGERweb capped the block fetch — needs paging")
    rows = []
    for f in d.get("features", []):
        a = f["attributes"]
        try:
            rows.append((float(a["INTPTLON"]), float(a["INTPTLAT"]), int(a["POP100"] or 0)))
        except (TypeError, ValueError, KeyError):
            continue
    if len(rows) < minimum:
        raise BuildError("only %d usable blocks over the city's envelope, expected at "
                         "least %d — read this as a capped or moved TIGERweb query"
                         % (len(rows), minimum))
    return rows


# --- the shipped file --------------------------------------------------------
def check_shipped(cfg, path=None):
    path = path or os.path.join(APP_DATA_DIR, cfg["out_file"])
    if not os.path.exists(path):
        return ["%s is missing" % path]
    with open(path) as f:
        feats = json.load(f).get("features") or []
    problems = []
    if len(feats) != len(cfg["expect_wards"]):
        problems.append("%d features, expected %d" % (len(feats), len(cfg["expect_wards"])))
    seen = tuple(sorted(((f.get("properties") or {}).get("Ward") or "?") for f in feats))
    if seen != tuple(sorted(cfg["expect_wards"])):
        problems.append("ward numbers are %s, expected %s"
                        % (list(seen), sorted(cfg["expect_wards"])))
    keys = {k for f in feats for k in (f.get("properties") or {})}
    stray = keys - set(SHIPPED_FIELDS)
    if stray:
        problems.append("shipped properties carry unexpected keys: %s" % sorted(stray))
    return problems


def check_main(cfg):
    problems = check_shipped(cfg)
    if problems:
        fail(cfg, "; ".join(problems))
    print("build-mi-%s-wards: OK — %d wards shipped" % (cfg["slug"], len(cfg["expect_wards"])))


# --- the build ---------------------------------------------------------------
def gate_and_write(cfg, wards, ward_key):
    """Run the three gates over the city's ward polygons (one feature per ward,
    keyed by `ward_key`) and write the shipped file. Anything failing exits."""
    expect = tuple(sorted(cfg["expect_wards"]))
    got = tuple(sorted(str(ward_key(f.get("properties") or {})) for f in wards))
    if len(wards) != len(expect) or got != expect:
        fail(cfg, "the source gives wards %s, expected %s" % (list(got), list(expect)))

    box = bbox(wards)
    wm = model(wards, ward_key)
    ov = overlaps(wm, box)
    if ov:
        fail(cfg, "the wards overlap at %d of 2000 sampled points" % ov)

    # ---- WITNESS: the state's own 2026 precincts --------------------------
    print("fetching the state's 2026 precincts for the witness gates…")
    sprecs = esri(STATE_PRECINCTS, {"where": cfg["state_where"], "outFields": "WARD,PRECINCT"})
    scounts = counts_by(sprecs, state_ward)
    if scounts != cfg["expect_state"]:
        fail(cfg, "the state assigns %s precincts per ward, expected %s — the precinct "
                  "fabric has moved and these wards must be re-checked against it"
                  % (scounts, cfg["expect_state"]))
    print("  state: %d precincts, per ward %s" % (len(sprecs), scounts))
    agree = point_agreement(wm, model(sprecs, state_ward), box)
    print("  city wards vs state precincts: %d same, %d differ, %d only in the city's map, "
          "%d only in the state's" % (agree["same"], agree["diff"], agree["only_a"],
                                      agree["only_b"]))
    print("    where both maps draw a ward: %.3f%%; over either map: %.3f%% (rule: %s)"
          % (100 * agree["lines"], 100 * agree["union"], cfg["agreement"]))
    blocks = None
    if cfg["agreement"] == "residents":
        if not cfg.get("agreement_why"):
            fail(cfg, "the residents rule needs agreement_why: say why area cannot answer")
        print("fetching Census 2020 blocks for the residents rule…")
        blocks = fetch_blocks(box, cfg.get("min_blocks", 500))
        agree["residents"] = resident_agreement(cfg, wm, model(sprecs, state_ward), blocks)
    elif cfg["agreement"] not in ("lines", "union"):
        fail(cfg, "unknown agreement rule %r" % cfg["agreement"])
    score = agree[cfg["agreement"]]
    if score < MIN_AGREEMENT:
        fail(cfg, "agreement %.3f%% (%s rule) is below the %.0f%% floor — find out which "
                  "publisher is right before touching this threshold"
                  % (100 * score, cfg["agreement"], 100 * MIN_AGREEMENT))

    # ---- TILING against the Census place -----------------------------------
    if blocks is None:
        print("fetching Census 2020 blocks…")
        blocks = fetch_blocks(box, cfg.get("min_blocks", 500))
    place = esri(PLACE, {"where": "GEOID = '%s'" % cfg["place_geoid"], "outFields": "NAME,GEOID"})
    if str(place[0]["properties"].get("NAME", "")) != cfg["place_name"]:
        fail(cfg, "place GEOID %s is not %s (got %r)" % (
            cfg["place_geoid"], cfg["place_name"], place[0]["properties"].get("NAME")))
    pgeom = place[0]["geometry"]
    per, total, place_pop, edge, edge_pop = {}, 0, 0, 0, 0
    for lon, lat, pop in blocks:
        pt = (lon, lat)
        inw = next((k for k, g in wm if in_geometry(pt, g)), None)
        inp = in_geometry(pt, pgeom)
        if inw is not None:
            per[inw] = per.get(inw, 0) + pop
            total += pop
        if inp:
            place_pop += pop
        if (inw is not None) != inp:
            edge += 1
            edge_pop += pop
    for k in sorted(per, key=lambda s: int(s)):
        print("    Ward %-3s %7d" % (k, per[k]))
    delta = total - place_pop
    print("  wards total %d against the Census place's %d (%+d); %d edge block(s) "
          "holding %d people" % (total, place_pop, delta, edge, edge_pop))
    if place_pop and abs(delta) > MAX_POP_DELTA_FRACTION * place_pop:
        fail(cfg, "the wards' population differs from the city's by %+d (%.3f%%), past the "
                  "%.1f%% tolerance" % (delta, 100.0 * abs(delta) / place_pop,
                                        100 * MAX_POP_DELTA_FRACTION))
    if edge > MAX_EDGE_BLOCKS:
        fail(cfg, "%d blocks fall on one side of the ward outline and the other side of "
                  "the Census place outline (ceiling %d)" % (edge, MAX_EDGE_BLOCKS))

    # ---- write -------------------------------------------------------------
    # A city's wards are few and small enough to ship unsimplified, at the
    # fleet's 6-decimal precision, so the shipped lines are the publisher's own.
    def r6(c):
        if isinstance(c[0], (int, float)):
            return [round(c[0], 6), round(c[1], 6)]
        return [r6(q) for q in c]
    out = {"type": "FeatureCollection",
           "features": [{"type": "Feature",
                         "properties": {"WARD": str(ward_key(f["properties"])),
                                        "Ward": str(ward_key(f["properties"]))},
                         "geometry": {"type": f["geometry"]["type"],
                                      "coordinates": r6(f["geometry"]["coordinates"])}}
                        for f in sorted(wards, key=lambda f: int(ward_key(f["properties"])))]}
    path = os.path.join(APP_DATA_DIR, cfg["out_file"])
    with open(path, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    problems = check_shipped(cfg, path)
    if problems:
        fail(cfg, "; ".join(problems))
    print("build-mi-%s-wards: wrote %s (%d wards, %d bytes)"
          % (cfg["slug"], path, len(expect), os.path.getsize(path)))


# --- GeoPDF: a georeferenced map exported from ArcGIS ------------------------
# A city that publishes its wards only as a map PDF still publishes them as
# GEOMETRY when the PDF is a GeoPDF: ArcGIS writes a /Measure /GEO viewport with
# ground control points (GPTS, latitude/longitude) against the viewport's unit
# square (LPTS) and the projection as WKT, and each map layer as an optional
# content group whose vector paths are the features themselves. Nothing here is
# traced or read off pixels. The fit is affine in the PDF's own projection, and
# its residual at the control points is printed and gated.
MAX_GEOREF_RESIDUAL_M = 1.0


def _nums(s):
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", s)]


def geopdf_projector(doc, pno=0):
    """(page point in PyMuPDF's y-down space) -> (lon, lat), from the page's
    largest georeferenced viewport. Returns (project, residual_m)."""
    import numpy as np
    from pyproj import CRS, Transformer
    page = doc[pno]
    pobj = doc.xref_object(page.xref)
    height = page.mediabox.height
    vps = []
    for m in re.finditer(r"/BBox\s*\[([^\]]+)\]", pobj):
        bb = _nums(m.group(1))
        tail = pobj[m.end():m.end() + 400]
        mm = re.search(r"/Measure\s+(\d+)\s+0\s+R", tail)
        meas = doc.xref_object(int(mm.group(1))) if mm else None
        if meas is None:
            seg = pobj[max(0, m.start() - 600):m.end() + 1500]
            if "/GPTS" in seg:
                meas = seg
        if meas and "/GPTS" in meas:
            vps.append((bb, meas))
    if not vps:
        raise BuildError("the PDF carries no georeferenced viewport — it is a picture "
                         "of a map, not a GeoPDF, and cannot be read as geometry")
    bb, meas = max(vps, key=lambda v: abs((v[0][2] - v[0][0]) * (v[0][3] - v[0][1])))
    gpts = _nums(re.search(r"/GPTS\s*\[([^\]]+)\]", meas).group(1))
    lpts = _nums(re.search(r"/LPTS\s*\[([^\]]+)\]", meas).group(1))
    g = re.search(r"/GCS\s+(\d+)\s+0\s+R", meas)
    gcs = doc.xref_object(int(g.group(1))) if g else meas
    wkt = re.search(r"/WKT\s*\((.*)\)\s*(?:/|>>)", gcs, re.S).group(1)
    crs = CRS.from_wkt(wkt.replace("\\(", "(").replace("\\)", ")"))
    to_proj = Transformer.from_crs(4326, crs, always_xy=True)
    to_ll = Transformer.from_crs(crs, 4326, always_xy=True)
    x0, y0, x1, y1 = bb
    rows, east, north = [], [], []
    for i in range(0, len(lpts), 2):
        u, v = lpts[i], lpts[i + 1]
        lat, lon = gpts[i], gpts[i + 1]
        # LPTS y runs from the BBox's FIRST y value, not from its lower edge.
        rows.append([x0 + u * (x1 - x0), y0 + v * (y1 - y0), 1.0])
        e, n = to_proj.transform(lon, lat)
        east.append(e); north.append(n)
    a = np.array(rows)
    ce = np.linalg.lstsq(a, np.array(east), rcond=None)[0]
    cn = np.linalg.lstsq(a, np.array(north), rcond=None)[0]
    unit = crs.axis_info[0].unit_conversion_factor
    resid = max(max(abs(a[i] @ ce - east[i]), abs(a[i] @ cn - north[i])) * unit
                for i in range(len(rows)))

    def project(x, y_fitz):
        py = height - y_fitz
        return to_ll.transform(ce[0] * x + ce[1] * py + ce[2], cn[0] * x + cn[1] * py + cn[2])
    return project, resid


def geopdf_subpaths(drawing):
    """A PyMuPDF drawing split into point sequences. Curves are sampled at four
    points; ArcGIS writes polygon edges as straight segments, so a curve here
    is rare and sampling it is a small, bounded approximation."""
    out, cur = [], []

    def close_cur():
        if cur:
            out.append(list(cur))
        del cur[:]
    for it in drawing["items"]:
        op = it[0]
        if op in ("l", "c"):
            p1 = it[1]
            if cur and (abs(cur[-1][0] - p1.x) > 1e-6 or abs(cur[-1][1] - p1.y) > 1e-6):
                close_cur()
            if not cur:
                cur.append((p1.x, p1.y))
            if op == "l":
                cur.append((it[2].x, it[2].y))
            else:
                p = it[1:5]
                for t in (0.25, 0.5, 0.75, 1.0):
                    cur.append(((1 - t) ** 3 * p[0].x + 3 * (1 - t) ** 2 * t * p[1].x
                                + 3 * (1 - t) * t ** 2 * p[2].x + t ** 3 * p[3].x,
                                (1 - t) ** 3 * p[0].y + 3 * (1 - t) ** 2 * t * p[1].y
                                + 3 * (1 - t) * t ** 2 * p[2].y + t ** 3 * p[3].y))
        elif op == "re":
            close_cur()
            r = it[1]
            out.append([(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1), (r.x0, r.y0)])
        elif op == "qu":
            close_cur()
            q = it[1]
            out.append([(q.ul.x, q.ul.y), (q.ur.x, q.ur.y), (q.lr.x, q.lr.y),
                        (q.ll.x, q.ll.y), (q.ul.x, q.ul.y)])
    close_cur()
    return out


def geopdf_texts(page):
    for b in page.get_text("dict")["blocks"]:
        for line in b.get("lines", []):
            t = "".join(s["text"] for s in line["spans"]).strip()
            if t:
                x0, y0, x1, y1 = line["bbox"]
                yield t, ((x0 + x1) / 2, (y0 + y1) / 2), line["spans"][0]["size"]
