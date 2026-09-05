#!/usr/bin/env python3
"""
Build the two statewide NG911 emergency-service-area files from the
Wisconsin Office of Emergency Communications' own aggregate — the route
the phase-2 research recorded and the guidebook backlog queued:

  data/app/fire-service-areas.json  which fire department responds at a
                                    point (FireBoundary, layer 3)
  data/app/law-service-areas.json   which law-enforcement agency serves a
                                    point (LawEnforcementBoundary, layer 4)
  data/app/psap-areas.json          which PSAP — public safety answering
                                    point — answers a 911 call placed at
                                    the point (PSAPBoundary, layer 6)
  data/app/ems-service-areas.json   which emergency medical service is
                                    dispatched at the point
                                    (EmergencyMedicalServicesBoundary,
                                    layer 2)

SOURCE. The OEC publishes every county's NG911 GIS filing as one public
feature service (org WI_OEC_GIS, item 593d0da225b24601ad0c21598ef52fb0,
updated roughly weekly) under an explicit licence: "This data is free and
open for use by the public." The schema is the WI NG911 GIS Data
Standards, "nearly identical to the NENA NG911 Standard". These are
RESPONSE areas — who is dispatched where — never taxing districts and
never electing bodies, which is why the cards name no officeholder; the
guidebook's fire cell calls this "the NYC operational shape, not the IL
taxing shape", and Illinois' own Lee County fire entry already ships the
same product one county at a time.

PER-AGENCY DISSOLVE, AND WHY THE KEY IS A PAIR. Counties file one polygon
per ESN-ish sub-area, so one department arrives as several rows (3,046
fire rows over 1,046 agencies at first build). The dissolve key is
DsplayName + Agency_ID, never DsplayName alone, because the bare name is
wrong in both directions at once: two UNRELATED departments share a name
across counties ("Rome Fire Department" files under both a Jefferson
County town's authority and Wood County's, ~100 miles apart), while one
REAL cross-county agency files under both its counties' authorities
(Appleton Fire under Outagamie's and Winnebago's). The pair keeps the two
Romes apart; a genuine cross-county agency ships as one feature per
filing authority, same name on each, which draws the county line inside
its area exactly as the source draws it — the card answer at any point is
identical either way.

EXPIRED ROWS ARE DROPPED BY DATE, NEVER BY COUNT. NENA carries an Expire
column; every expired fire/law row at first build (37 + 18) was
superseded history, and a FUTURE Expire date is a still-effective row
that must ship. The drop is computed against the clock each run.

WHAT THE DATA DOES NOT COVER IS MEASURED AND PINNED. Five authorities'
filings are absent or partial (Iowa, Vilas and Walworth file none of the
four tilings; Jefferson files law and PSAP but neither fire nor EMS;
Polk's law filing covers ~60% while its other three file in full),
and LANGLADE COUNTY HAS NO PROVISIONING BOUNDARY AT ALL — 72 provisioning
polygons where the other 71 counties plus the City of Milwaukee each
carry one. Every rate is recomputed per run inside the counties' own
provisioning polygons and gated against UNFILED below, so a county
completing its filing fails the build loudly and the operator retires the
entry (and the matching gap record) with eyes open. The remaining
"uncovered" area in a naive statewide sample is Great Lakes water inside
TIGER county polygons — measured, not a gap.

AN OPERATOR REBUILD WHOSE DRIFT NOBODY WAS MEASURING, until 2026-09-05. This
docstring used to end "the monthly source report watches the layer counts",
and validate_sources.py's own comment on these four rows called a count change
"the operator's rebuild trigger". Both were true of the INTENT and false of the
code: those rows asked the service for `returnCountOnly=true` and the checker
read only whether the endpoint answered, throwing the number away — so nothing
anywhere held last month's count and nothing could see it move. A trigger with
no baseline is a sentence, which is the same shape as sw.js's "bump CACHE_NAME
whenever…" before check_cache_version.py existed.

WHAT THAT COST, MEASURED THE FIRST TIME ANYONE COMPARED. The EMS layer had
gained an agency the shipped file did not have: 580 live against 579 shipped,
the new key being `Berlin` under wausharacountywi.gov. It was not a hole being
filled. The CITY OF BERLIN straddles the Green Lake / Waushara county line, and
Waushara had filed the city's OWN ambulance service over the city's Waushara
half — 2.1 km2, Census place 5506925, county subdivision 5513706925 — where
this project was still answering `Poy Sippi`, the rural service, for everyone
in it. 400 of 400 sampled points inside that polygon said Poy Sippi on the
shipped file and Berlin on the source, and the live source no longer files Poy
Sippi there at all, so it was a TRANSFER and not one of the concurrent
jurisdictions this layer legitimately carries.

WHAT A 20,000-POINT SAMPLE SAID ABOUT THAT, AND WHY IT WAS WORTHLESS. Such a
sample across all four layers found ZERO changed answers, and a first version of
this docstring concluded from it that the other three layers had "changed BYTES
while changing no answer". THAT WAS FALSE, and review caught it: measured
against main, this rebuild changes the geometry of 138 fire, 161 law, 19 PSAP
and 79 EMS features (PER FEATURE — a first count said 136 and 74 because it
keyed on DsplayName, which collapses the 12 fire and 14 EMS agencies that file
under more than one authority; keying a measurement on the name alone, in the
builder whose whole dissolve key exists because the name alone is not one). The sample could not see any of it — 2.1 km2 of a 169,000
km2 state is one part in eighty thousand, so a 20,000-point sample expects
FEWER THAN ONE hit — and a null result from an instrument with no power is not
evidence of no change. That is the real lesson: the question a staleness check
must ask is "did the source move at all", which is a COUNT and an EDIT DATE,
never a sample; and byte churn is not evidence of a reader-visible change in
either direction.

THE FIX IS A SIDECAR, NOT A CONSTANT. wi/data/source/ng911/built-rows.json is
written by this build on every successful run and carries the row counts the
OEC's own count endpoints reported at that moment; validate_sources.py reads it
monthly and WARNs when the live counts have moved. It is a file rather than a
hand-edited constant because the two must never disagree, and one run writes
both. Its blind spot is stated where it is read: a county REDRAWING a boundary
without changing its row count does not show up.

Prerequisites: curl and Node.js (mapshaper).
"""

import datetime
import json
import os
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from build_wi_supervisory_districts import (  # noqa: E402
    fetch_layer, _model, _districts_at, _bbox, _point_in_geometry,
    _curl, MAPSHAPER, STATE_BBOX)

REPO_ROOT = os.path.dirname(SCRIPT_DIR)
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")

OEC = ("https://services3.arcgis.com/GoOAGCoqFEhZEh7f/arcgis/rest/services"
       "/WI_NG911_GIS_Service_Polygons_and_Road_Centerline_Data_v2/FeatureServer")
EMS = OEC + "/2"
FIRE = OEC + "/3"
LAW = OEC + "/4"
PROVISIONING = OEC + "/5"
PSAP = OEC + "/6"

LAYERS = [
    {"name": "fire", "url": FIRE, "out": "fire-service-areas.json",
     "min_rows": 2800, "min_agencies": 950},
    {"name": "law", "url": LAW, "out": "law-service-areas.json",
     "min_rows": 2900, "min_agencies": 600},
    # PSAP is the tiling where the date filter EARNS its by-date form: 11 of
    # its 208 raw rows carried FUTURE Expire dates at first measurement —
    # still-effective rows a drop-anything-with-Expire filter would delete.
    # 205 effective rows over 95 answering points; its rare overlaps
    # (a county PSAP and a city PD's own dispatch both filed, ~0.1% of
    # points) render like law's, every center at the point.
    {"name": "psap", "url": PSAP, "out": "psap-areas.json",
     "min_rows": 190, "min_agencies": 88},
    # EMS re-proves the pair key on ambulance services: regional providers
    # (Emplify, Tri State) file under multiple counties' authorities, and a
    # few EMS Agency_IDs are not county domains at all (BVEM files under
    # BVEM1/BVEM2) — the pair still keys them correctly. 2,443 effective
    # rows over 579 services at first measurement (2026-08-26); 2,444 over
    # 580 at the 2026-09-05 rebuild, the extra one being Berlin. Essentially
    # no cross-name overlap (1 same-name multi-hit in 3,000 points).
    {"name": "ems", "url": EMS, "out": "ems-service-areas.json",
     "min_rows": 2300, "min_agencies": 530},
]

# Filing absences, pinned exactly as measured 2026-08-26 (40 seeded sample
# points inside each authority's own provisioning polygon; flagged under
# 90% coverage). Keyed by the provisioning DiscrpAgID; the value is the
# set of layers that authority has NOT (fully) filed. Mirrored by the gap
# records ng911-fire-filings / ng911-law-filings — retire both together.
UNFILED = {
    "iowacounty.org": {"fire", "law", "psap", "ems"},
    "vilascountywi.gov": {"fire", "law", "psap", "ems"},
    "co.walworth.wi.us": {"fire", "law", "psap", "ems"},
    "jeffersoncountywi.gov": {"fire", "ems"},  # law and PSAP file in full
    "polkcountywi.gov": {"law"},          # partial: ~60% covered at pin time
}
EXPECT_PROVISIONING = 72   # 71 counties + the City of Milwaukee; Langlade absent
NO_PROVISIONING = "langlade"

SIMPLIFY = "8%"
PRECISION = "0.000001"     # 6 decimals ~= 0.11 m
COVERAGE_SAMPLES = 40      # per provisioning polygon, seeded
VALIDATE_SAMPLES = 4000    # statewide dissolve+simplify agreement gate
SEP = "\x1f"               # KEY separator; never appears in either field


def fetch_retry(url, fields, attempts=3):
    """services3.arcgis.com drops the occasional mid-paging request (curl
    exit 92, an HTTP/2 stream reset — measured on the first live build);
    the shared pager has no retry, so the whole fetch retries here."""
    import time
    for attempt in range(attempts):
        try:
            return fetch_layer(url, fields)
        except subprocess.CalledProcessError:
            if attempt == attempts - 1:
                raise
            time.sleep(5 * (attempt + 1))


def effective(features):
    """Drop rows whose Expire date has passed — superseded filings. A future
    Expire is still in force and ships; the counts are printed, never pinned,
    because they move with the OEC's weekly refresh."""
    now_ms = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
              ).total_seconds() * 1000
    keep, dropped, future = [], 0, 0
    for f in features:
        exp = f["properties"].get("Expire")
        if exp and exp < now_ms:
            dropped += 1
            continue
        if exp:
            future += 1
        keep.append(f)
    return keep, dropped, future


def keyed(features, layer_name):
    """Attach the dissolve KEY; refuse rows a card could not answer from."""
    for f in features:
        p = f["properties"]
        name = (p.get("DsplayName") or "").strip()
        agency = (p.get("Agency_ID") or "").strip()
        if not name or not agency:
            raise RuntimeError("%s: a row is missing DsplayName or Agency_ID "
                               "(NGUID %r) — the schema moved, re-measure"
                               % (layer_name, p.get("NGUID")))
        if SEP in name or SEP in agency:
            raise RuntimeError("%s: the KEY separator appears in %r" % (layer_name, name))
        f["properties"] = {"KEY": name + SEP + agency, "NAME": name}
    return features


def sample_inside(geom, n, seed):
    """n seeded uniform points inside a polygon (rejection over its bbox)."""
    import random
    rng = random.Random(seed)
    bb = _bbox(geom)
    pts, tries = [], 0
    while len(pts) < n and tries < n * 200:
        tries += 1
        pt = (rng.uniform(bb[0], bb[2]), rng.uniform(bb[1], bb[3]))
        if _point_in_geometry(pt, geom):
            pts.append(pt)
    return pts


def gate_against_server(layer, out_feats, samples=25):
    """Ask the SERVICE which agencies cover a point, and compare to what the
    shipped file answers there. THIS IS THE ONLY GATE HERE THAT IS INDEPENDENT.

    validate() below samples 4,000 points, but it compares the dissolved output
    against the SAME fetch it was built from, so it agrees with itself by
    construction — which is exactly how the MASON hole (see fetch_layer's
    esri_rings_to_geojson) passed every gate while shipping a wrong card. This
    one asks the server, whose geometry this project does not hold, so a defect
    introduced anywhere between the query and the written file shows up.

    Deliberately small: 25 points is 25 round trips per layer, enough to catch a
    systematic defect and not a proof of per-point correctness. A disagreement
    FAILS the build rather than warning — the server is the authority here.
    """
    import random
    import urllib.parse
    model = _model(out_feats, "NAME")
    rng = random.Random(4242)
    bb = STATE_BBOX
    checked = 0
    attempts = 0
    while checked < samples and attempts < samples * 40:
        attempts += 1
        pt = (rng.uniform(bb["minLng"], bb["maxLng"]),
              rng.uniform(bb["minLat"], bb["maxLat"]))
        ours = set(_districts_at(model, pt))
        if not ours:
            continue          # outside coverage; the server has nothing to compare
        params = {
            "geometry": "%f,%f" % pt,
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "DsplayName",
            "returnGeometry": "false",
            "where": "1=1",
            "f": "json",
        }
        data = json.loads(_curl(layer["url"] + "/query?" + urllib.parse.urlencode(params)))
        theirs = {(f["attributes"].get("DsplayName") or "").strip()
                  for f in (data.get("features") or [])}
        theirs.discard("")
        # Expired rows this build drops can still answer on the server, so the
        # server may legitimately name MORE than we do; it must never name FEWER.
        if not ours <= theirs:
            raise RuntimeError(
                "%s: the shipped file answers %s at %.5f,%.5f where the service "
                "answers %s — the built geometry claims coverage the source does "
                "not. Re-read fetch_layer's esri_rings_to_geojson before touching "
                "anything else."
                % (layer["name"], sorted(ours), pt[0], pt[1], sorted(theirs)))
        checked += 1
    if checked < samples:
        raise RuntimeError("%s: only %d of %d sample points landed in coverage"
                           % (layer["name"], checked, samples))
    print("%s: %d/%d sampled points agree with the service's own point query"
          % (layer["name"], checked, samples), file=sys.stderr)


def gate_filings(feats_by_layer):
    """Recompute per-authority coverage inside the provisioning polygons and
    refuse the build if it disagrees with the pinned UNFILED map."""
    prov = fetch_layer(PROVISIONING, "DiscrpAgID")
    if len(prov) != EXPECT_PROVISIONING:
        raise RuntimeError("provisioning layer carries %d polygons, expected %d — "
                           "an authority joined or left; re-measure UNFILED and the "
                           "gap records before moving this number"
                           % (len(prov), EXPECT_PROVISIONING))
    if any(NO_PROVISIONING in (f["properties"].get("DiscrpAgID") or "").lower()
           for f in prov):
        raise RuntimeError("Langlade County now carries a provisioning polygon — "
                           "its no-provisioning record (and the gap records) are "
                           "stale; re-measure")
    models = {name: _model(feats, "KEY") for name, feats in feats_by_layer.items()}
    computed = {}
    for i, f in enumerate(prov):
        agid = (f["properties"].get("DiscrpAgID") or "").strip()
        pts = sample_inside(f["geometry"], COVERAGE_SAMPLES, seed=7 + i)
        if not pts:
            raise RuntimeError("no sample points landed inside provisioning %r" % agid)
        missing = set()
        for lname, model in models.items():
            hit = sum(1 for pt in pts if _districts_at(model, pt))
            if 100.0 * hit / len(pts) < 90:
                missing.add(lname)
        if missing:
            computed[agid] = missing
    if computed != UNFILED:
        raise RuntimeError(
            "measured filing absences differ from the pinned UNFILED map — a county "
            "filed (or a filing broke). Re-measure, then move UNFILED and the gap "
            "records together.\n  computed: %s\n  pinned:   %s"
            % (sorted((k, sorted(v)) for k, v in computed.items()),
               sorted((k, sorted(v)) for k, v in UNFILED.items())))
    return len(prov)


def validate(source_feats, result_feats):
    """Statewide seeded sample: wherever the full-precision source answers a
    NAME set, the dissolved+simplified output must answer the same set. Name
    sets, not single names, because law jurisdictions genuinely overlap (a
    sheriff and a municipal PD both filed over ~0.5% of points at first
    build) and the card renders every agency at the point."""
    import random
    src = _model(source_feats, "NAME")
    new = _model(result_feats, "NAME")
    rng = random.Random(2026)
    tested = agree = 0
    while tested < VALIDATE_SAMPLES:
        pt = (rng.uniform(STATE_BBOX["minLng"], STATE_BBOX["maxLng"]),
              rng.uniform(STATE_BBOX["minLat"], STATE_BBOX["maxLat"]))
        o_hits = _districts_at(src, pt)
        if not o_hits:
            continue
        tested += 1
        if set(_districts_at(new, pt)) == set(o_hits):
            agree += 1
    pct = 100.0 * agree / tested
    if pct < 99.9:
        raise RuntimeError("dissolve+simplify agreement only %.3f%% (need >= 99.9%%)"
                           % pct)
    return "%d/%d (%.3f%%) name-set agreement" % (agree, tested, pct)


def build(layer, check_only):
    feats = fetch_retry(layer["url"], "DsplayName,Agency_ID,NGUID,Expire")
    feats, dropped, future = effective(feats)
    # TOTAL is what returnCountOnly reports — effective rows PLUS the expired
    # ones this build drops. The monthly staleness check (below) compares the
    # live count endpoint against it, so the two must be the same quantity;
    # comparing against the effective count would drift on its own every time
    # a row's Expire date passed, with no source change at all.
    total = len(feats) + dropped
    if len(feats) < layer["min_rows"]:
        raise RuntimeError("%s: %d effective rows, floor %d — the service shrank; "
                           "re-measure before shipping"
                           % (layer["name"], len(feats), layer["min_rows"]))
    feats = keyed(feats, layer["name"])
    keys = {f["properties"]["KEY"] for f in feats}
    if len(keys) < layer["min_agencies"]:
        raise RuntimeError("%s: %d agencies, floor %d"
                           % (layer["name"], len(keys), layer["min_agencies"]))
    print("%s: %d effective rows (%d expired dropped, %d future-dated kept) "
          "-> %d agency keys (%d rows total)"
          % (layer["name"], len(feats), dropped, future, len(keys), total),
          file=sys.stderr)
    if check_only:
        return feats, None, total

    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, layer["name"] + "-src.geojson")
        with open(src_path, "w") as f:
            json.dump({"type": "FeatureCollection", "features": feats}, f)
        out_tmp = os.path.join(tmp, layer["name"] + ".geojson")
        subprocess.run(
            # -dissolve, NEVER -dissolve2: dissolve2 flattens the layer into
            # a shared-topology mosaic and assigns each face to ONE group,
            # which silently deletes the real concurrent-jurisdiction
            # overlaps the law layer carries (a sheriff and a municipal PD
            # both filed over ~0.5% of points) — measured as a 98.750%
            # name-set agreement before the swap, 100.000% after it.
            ["npx", "-y", MAPSHAPER, src_path,
             "-dissolve", "KEY", "copy-fields=NAME",
             "-simplify", "visvalingam", "keep-shapes", SIMPLIFY,
             "-o", "precision=" + PRECISION, "format=geojson", out_tmp],
            check=True, cwd=REPO_ROOT)
        with open(out_tmp) as f:
            dissolved = json.load(f)

    out_feats = dissolved["features"]
    if len(out_feats) != len(keys):
        raise RuntimeError("%s: dissolve produced %d features, expected %d"
                           % (layer["name"], len(out_feats), len(keys)))
    out_feats.sort(key=lambda f: f["properties"]["KEY"])
    for f in out_feats:
        f["properties"] = {"NAME": f["properties"]["NAME"]}

    msg = validate(feats, out_feats)
    gate_against_server(layer, out_feats)
    compact = json.dumps({"type": "FeatureCollection", "features": out_feats},
                         separators=(",", ":"), ensure_ascii=False)
    path = os.path.join(APP_DATA_DIR, layer["out"])
    with open(path, "w") as f:
        f.write(compact)
    print("%s: wrote %s — %d agency areas, %d bytes; %s"
          % (layer["name"], layer["out"], len(out_feats), len(compact), msg),
          file=sys.stderr)
    return feats, len(out_feats), total


# WHERE THE STALENESS PIN LIVES, AND WHY IT IS A FILE RATHER THAN A CONSTANT.
# This is an OPERATOR build with no schedule, reading a source the OEC refreshes
# roughly weekly — so its output drifts from the source with nothing measuring
# the drift. `validate_sources.py` already asks each of these four layers for
# `returnCountOnly=true` every month and its own comment calls a count change
# "the operator's rebuild trigger", but the checker READ ONLY REACHABILITY and
# threw the number away, so the trigger was a sentence and never a mechanism —
# exactly the defect that file records for the nearest-3 rows and fixed only
# there. Measured 2026-09-05: the shipped EMS file was one agency behind, and
# the difference was not cosmetic (see the Berlin note in the module docstring).
#
# The pin is a SIDECAR written by this build rather than a constant edited by
# hand, because a hand-edited pin is one an operator can forget while the data
# files move — and a staleness gate comparing against a stale pin is worse than
# no gate. Written by the same run that writes the data, it cannot disagree with
# them. It sits under data/source/, which the Pages deploy excludes, because it
# is build metadata and not something a reader fetches.
BUILT_ROWS_PATH = os.path.join(REPO_ROOT, "data", "source", "ng911",
                               "built-rows.json")


def layer_last_edit(url):
    """The layer's own `editingInfo.dataLastEditDate`, as an ISO date.

    A ROW COUNT CANNOT SEE A REDRAW. That was written into this file as a
    stated blind spot on 2026-09-05 and the very rebuild that stated it hit
    the case: the OEC edited all four layers on 2026-08-31, moving boundaries
    in 397 features (138 fire, 161 law, 19 PSAP, 79 EMS), while three of
    the four row counts did not move at all.
    The service publishes the edit timestamp, so the blind spot was avoidable
    rather than inherent, and the monthly check now reads both.
    """
    import urllib.parse  # noqa: F401  (kept local; _curl takes a full url)
    meta = json.loads(_curl(url + "?f=json"))
    ms = (meta.get("editingInfo") or {}).get("dataLastEditDate")
    if not isinstance(ms, (int, float)):
        return None
    return datetime.datetime.fromtimestamp(
        ms / 1000.0, datetime.timezone.utc).date().isoformat()


def read_built_rows():
    """The pin, or None when this build has never run since the pin existed."""
    try:
        with open(BUILT_ROWS_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def write_built_rows(totals, agencies, last_edits):
    os.makedirs(os.path.dirname(BUILT_ROWS_PATH), exist_ok=True)
    payload = {
        "_comment": ("What the OEC's own service reported at the last operator "
                     "build of build_wi_ng911_service_areas.py: `rows` as its "
                     "returnCountOnly endpoints answered, and `dataLastEdit` as "
                     "its editingInfo.dataLastEditDate. validate_sources.py "
                     "compares BOTH monthly and WARNs when either has moved — a "
                     "REDRAW does not change a row count, which is how the "
                     "2026-08-31 edit moved 397 features silently. Written by "
                     "the build; never edit by hand."),
        "builtOn": datetime.date.today().isoformat(),
        "rows": totals,
        "agencies": agencies,
        "dataLastEdit": last_edits,
    }
    with open(BUILT_ROWS_PATH, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    print("wrote %s — rows %s" % (os.path.relpath(BUILT_ROWS_PATH, REPO_ROOT),
                                  totals), file=sys.stderr)


def check_built_rows(totals, last_edits=None):
    """--check: is the shipped tree still current with the source?

    This is the local half of the monthly staleness check. It compares what the
    source holds NOW against what it held when these files were built. It cannot
    see a county REDRAWING a boundary without changing its row count — that is a
    real blind spot and is why the OEC row is a WARN a human reads rather than a
    claim of freshness.
    """
    pin = read_built_rows()
    if pin is None:
        raise RuntimeError(
            "no %s — run this builder without --check once to write the pin"
            % os.path.relpath(BUILT_ROWS_PATH, REPO_ROOT))
    behind = {name: (pin["rows"].get(name), total)
              for name, total in sorted(totals.items())
              if pin["rows"].get(name) != total}
    if behind:
        raise RuntimeError(
            "the shipped NG911 files are STALE — the source has moved since they "
            "were built on %s. %s. Re-run this builder without --check, bump "
            "cache_name in wi/metro-worksheet.json (these are cache-first), and "
            "commit the rebuilt files with the refreshed pin."
            % (pin.get("builtOn", "an unrecorded date"),
               "; ".join("%s %s -> %s" % (n, was, now)
                         for n, (was, now) in behind.items())))
    moved = {}
    for name, live in sorted((last_edits or {}).items()):
        was = (pin.get("dataLastEdit") or {}).get(name)
        if live and was and live != was:
            moved[name] = (was, live)
    if moved:
        raise RuntimeError(
            "the shipped NG911 files are STALE — the row counts still match, but "
            "the service EDITED %s since the build on %s (%s). A redraw does not "
            "move a row count, which is exactly the blind spot this second signal "
            "closes. Re-run this builder without --check, bump cache_name, and "
            "commit the rebuilt files."
            % (", ".join(sorted(moved)), pin.get("builtOn", "an unrecorded date"),
               "; ".join("%s %s -> %s" % (n, w, l) for n, (w, l) in moved.items())))
    print("staleness: all 4 layers still carry the row counts AND the edit dates "
          "they were built from on %s"
          % pin.get("builtOn", "an unrecorded date"), file=sys.stderr)


def main():
    check_only = "--check" in sys.argv[1:]
    built = {}
    for layer in LAYERS:
        built[layer["name"]] = build(layer, check_only)
    n_prov = gate_filings({name: t[0] for name, t in built.items()})
    print("gates: filing absences match the pinned UNFILED map across all %d "
          "provisioning authorities (Langlade still absent)" % n_prov,
          file=sys.stderr)
    totals = {name: t[2] for name, t in built.items()}
    last_edits = {layer["name"]: layer_last_edit(layer["url"]) for layer in LAYERS}
    if check_only:
        check_built_rows(totals, last_edits)
    else:
        write_built_rows(totals, {name: t[1] for name, t in built.items()},
                         last_edits)


if __name__ == "__main__":
    main()
