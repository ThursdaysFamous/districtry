#!/usr/bin/env python3
"""
Build one state's layer of districts from the map a government office
publishes of them, for the app to read same-origin.

Each layer that uses this has a short builder of its own, which says where
the layer is, how to read one record, what to expect and what its card must
say; everything else lives here once. Measured on 2026-10-16:

  * School board election districts, through
    <tag>/scripts/build_<tag>_school_board_districts.py: South Carolina (the
    Revenue and Fiscal Affairs Office's map of every school district's board
    districts), Arkansas (the GIS Office's map of school board zones, which
    the Secretary of State compiles), Tennessee (the Comptroller of the
    Treasury's map of new school board districts, for eighteen counties) and
    Indiana (the City of Indianapolis's map, from which only the Indianapolis
    Public Schools districts are taken).

A builder names the property its districts are grouped by (`group`): the
school board, for a school board district. The counts, the record and the
agreement test below are all made per group, and the default is "board".

THE SHAPE IS THE PRECINCT BUILDER'S (scripts/statewide_precincts.py), whose
fetch, simplification and card check this imports rather than copies: fetch the
whole layer, check it, simplify it with Douglas-Peucker, refuse to write unless
the simplified file answers as the source does, and ship it as a data/app file.
A reader's click is answered from that file, so no point is sent to anyone.

WHAT IS DIFFERENT FROM PRECINCTS. A precinct map tiles its state, so the
precinct builder checks every county is covered. These layers tile only part
of a state (board districts cover only the school districts that elect by
district), so there is no county test here. Instead:
  1. Every record goes through the state's `read()`, which returns the
     feature's properties, or None for a record the builder declares it skips
     (Tennessee's layer carries one record with no county and no shape). The
     number skipped must equal the builder's declaration.
  2. Two records with the same key are joined into one district only when the
     builder declares how many such further parts it expects (Arkansas
     publishes one zone of the Jasper district in two pieces), and their
     properties must agree.
  3. The count after reading equals EXPECT exactly, and so does the number of
     groups (for school board districts, the boards) the file draws; the key
     is unique and every property the card prints is populated.
  4. Douglas-Peucker at `interval` metres with keep-shapes, in one mapshaper
     run, so a line two districts share is simplified once, and the drawn line
     strays no further than the interval by construction.
  5. No district is lost in simplification, and points sampled inside each
     group's own extent get the same district from the drawn file as from the
     source at least 99.5% of the time overall and 98% for every group, with
     no point in two drawn districts where the source has one.
  6. Points the builder names (`inside`, `outside`) must land where it says:
     a known district, or no district at all. Tennessee uses the second to
     hold the measurement that its Shelby County districts leave out the
     suburban municipal school districts.
  7. A record (data/source/<file>.source.json) keeps the fetch date, the
     layer's own edit date where it publishes one, a fingerprint of what a
     redistricting changes, the count of districts in every group and the
     shipped file's hash. `--check` holds the shipped file to it offline;
     `--watch` reads the live layer's attributes, no geometry, and compares
     the fingerprint.
  8. The card says what the file is: the module that loads it in
     <tag>/index.html must say "drawn here to within <interval> metres" and
     each sentence the builder lists in `card_claims`, checked by the precinct
     builder's own reader.

WHERE `--check` RUNS. When a person runs it: at every rebuild and at the
quarterly re-check each instance's WATCH.md schedules. It is not in the CI
battery, for the reason the precinct builders' is not (a step in
.github/workflows/smoke-test.yml is a workflow change); the battery's own gate
on these files is each instance's validate_index.py, which holds the feature
count.
"""

import argparse
import datetime
import hashlib
import json
import os
import random
import sys

FLEET_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(FLEET_SCRIPTS)
if FLEET_SCRIPTS not in sys.path:
    sys.path.insert(0, FLEET_SCRIPTS)

import statewide_precincts as sp  # noqa: E402

SAMPLES_PER_GROUP = 400
MIN_AGREE_ALL = 99.5
MIN_AGREE_GROUP = 98.0


class Spec(object):
    """What a state's builder supplies. Every argument without a default is
    required, so a builder cannot leave one out by accident."""

    def __init__(self, tag, label, layer, user_agent, out_fields, expect,
                 expect_groups, read, out_file, group="board",
                 group_nouns=("board", "boards"), card_noun="school board card",
                 interval="4", pace=0.0, page=None, where="1=1",
                 measure_field=None, skipped_records=0, multipart_records=0,
                 required=None, extra_check=None, card_claims=(), inside=(),
                 outside=()):
        self.tag = tag
        self.label = label
        self.layer = layer.rstrip("/")
        self.user_agent = user_agent
        self.out_fields = out_fields
        self.expect = expect
        self.expect_groups = expect_groups
        # the property districts are counted and sampled by, and what to call
        # one and several of them in a message
        self.group = group
        self.group_nouns = tuple(group_nouns)
        self.card_noun = card_noun
        self.read = read
        self.out_file = out_file
        self.interval = interval
        self.pace = pace
        self.page = page
        self.where = where
        self.measure_field = measure_field
        self.skipped_records = skipped_records
        self.multipart_records = multipart_records
        self.required = tuple(required or ("key", group, "label"))
        # extra_check(features) raises through fail() on anything wrong; it
        # runs in all three modes, on what the builder read.
        self.extra_check = extra_check
        self.card_claims = tuple(card_claims)
        # (lng, lat, key, why): the point must fall in the district with that key
        self.inside = tuple(inside)
        # (lng, lat, why): the point must fall in no district at all
        self.outside = tuple(outside)
        if measure_field and measure_field not in out_fields.split(","):
            self.out_fields = out_fields + "," + measure_field
        self.instance = os.path.join(REPO_ROOT, tag)
        self.out_path = os.path.join(self.instance, "data", "app", out_file)
        self.record_path = os.path.join(
            self.instance, "data", "source", out_file.replace(".json", ".source.json"))


def fail(spec, msg):
    raise SystemExit("%s: FATAL: %s" % (spec.label, msg))


# ---------- read ----------
def normalise(spec, records, with_geometry=True):
    feats, by_key, skipped, parts = [], {}, 0, 0
    for rec in records:
        props = rec.get("properties") or {}
        out = spec.read(props)
        if out is None:
            skipped += 1
            continue
        if not isinstance(out, dict):
            fail(spec, "read() returned %r for %r" % (out, props))
        for key in spec.required:
            if out.get(key) in (None, ""):
                fail(spec, "a record reads with no %s: %r" % (key, props))
        if with_geometry and not rec.get("geometry"):
            fail(spec, "district %s has no geometry" % out["key"])
        if spec.measure_field:
            if props.get(spec.measure_field) is None:
                fail(spec, "district %s carries no %s, which the fingerprint reads"
                     % (out["key"], spec.measure_field))
            out["_measure"] = float(props.get(spec.measure_field))
        prior = by_key.get(out["key"])
        if prior is not None:
            a = {k: v for k, v in prior["properties"].items() if k != "_measure"}
            b = {k: v for k, v in out.items() if k != "_measure"}
            if a != b:
                fail(spec, "two records read with the key %s and differ in what they say: "
                     "%r and %r" % (out["key"], a, b))
            if not spec.multipart_records:
                fail(spec, "two records read with the key %s; this builder declares no "
                     "district published in parts" % out["key"])
            if spec.measure_field:
                prior["properties"]["_measure"] += out["_measure"]
            if with_geometry:
                prior["geometry"] = {
                    "type": "MultiPolygon",
                    "coordinates": sp._polygons(prior["geometry"]) + sp._polygons(rec["geometry"])}
            parts += 1
            continue
        feat = {"type": "Feature", "properties": out, "geometry": rec.get("geometry")}
        by_key[out["key"]] = feat
        feats.append(feat)
    if skipped != spec.skipped_records:
        fail(spec, "%d records were skipped by read(), and the builder declares %d. Read the "
             "layer before changing the declaration" % (skipped, spec.skipped_records))
    if parts != spec.multipart_records:
        fail(spec, "%d records are further parts of a district already read, and the builder "
             "declares %d. Read the layer before changing the declaration"
             % (parts, spec.multipart_records))
    return feats


def per_group(spec, feats):
    out = {}
    for f in feats:
        b = f["properties"][spec.group]
        out[b] = out.get(b, 0) + 1
    return dict(sorted(out.items()))


def record_key(spec):
    return "districts_per_" + spec.group


def nouns(spec, n):
    return spec.group_nouns[0] if n == 1 else spec.group_nouns[1]


def fingerprint(spec, feats):
    """A digest of what a redistricting changes: every district's key, label
    and group and, where the layer publishes one, its area in whole units of
    the layer's own. Sorted, so record order cannot move it."""
    lines = []
    for f in feats:
        p = f["properties"]
        measure = p.get("_measure")
        lines.append("%s|%s|%s|%s" % (p["key"], p["label"], p[spec.group],
                                      "" if measure is None else int(round(float(measure)))))
    lines.sort()
    return {"districts": len(lines),
            "sha256": hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()}


def gate_counts(spec, feats):
    problems = []
    if len(feats) != spec.expect:
        problems.append("%d districts, expected %d. A redistricting moves this number "
                        "legitimately: read the layer, then change EXPECT deliberately"
                        % (len(feats), spec.expect))
    groups = per_group(spec, feats)
    if len(groups) != spec.expect_groups:
        problems.append("%d %s drawn, expected %d" % (len(groups), spec.group_nouns[1],
                                                      spec.expect_groups))
    keys = [f["properties"]["key"] for f in feats]
    if len(set(keys)) != len(keys):
        problems.append("a district key appears twice")
    return problems


# ---------- point lookup ----------
class Index(object):
    """A grid of district bounding boxes, the precinct builder's, keyed on the
    district key."""

    def __init__(self, feats):
        self.items, self.cells = [], {}
        for f in feats:
            bb = sp.bbox(f["geometry"])
            n = len(self.items)
            self.items.append((f["properties"]["key"], f["geometry"], bb))
            for gx in range(int(bb[0] // sp.GRID), int(bb[2] // sp.GRID) + 1):
                for gy in range(int(bb[1] // sp.GRID), int(bb[3] // sp.GRID) + 1):
                    self.cells.setdefault((gx, gy), []).append(n)

    def at(self, pt):
        hits = []
        for n in self.cells.get((int(pt[0] // sp.GRID), int(pt[1] // sp.GRID)), ()):
            key, geom, bb = self.items[n]
            if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3] and sp.point_in_geometry(pt, geom):
                hits.append(key)
        return hits


def group_extents(spec, feats):
    out = {}
    for f in feats:
        b = f["properties"][spec.group]
        bb = sp.bbox(f["geometry"])
        e = out.get(b)
        out[b] = bb if e is None else [min(e[0], bb[0]), min(e[1], bb[1]),
                                       max(e[2], bb[2]), max(e[3], bb[3])]
    return out


def validate(spec, source_feats, drawn_feats, seed=2026):
    """Points sampled over each group's extent, compared between the source
    and the drawn file. Returns (problems, report line)."""
    src, new = Index(source_feats), Index(drawn_feats)
    rng = random.Random(seed)
    problems = []
    agree = total = overlaps = 0
    worst = (101.0, None)
    extents = group_extents(spec, source_feats)
    for group, bb in sorted(extents.items()):
        a = 0
        for _ in range(SAMPLES_PER_GROUP):
            pt = (rng.uniform(bb[0], bb[2]), rng.uniform(bb[1], bb[3]))
            s = sorted(src.at(pt))
            d = sorted(new.at(pt))
            if len(d) > 1 and len(s) <= 1:
                overlaps += 1
            a += s == d
        pct = 100.0 * a / SAMPLES_PER_GROUP
        if pct < worst[0]:
            worst = (pct, group)
        if pct < MIN_AGREE_GROUP:
            problems.append("%s: the drawn file agrees with the source at only %.2f%% of "
                            "points over its extent (need %.1f%%)" % (group, pct, MIN_AGREE_GROUP))
        agree += a
        total += SAMPLES_PER_GROUP
    pct_all = 100.0 * agree / total
    if pct_all < MIN_AGREE_ALL:
        problems.append("the drawn file agrees with the source at only %.2f%% of points "
                        "(need %.1f%%)" % (pct_all, MIN_AGREE_ALL))
    if overlaps:
        problems.append("%d points fell in two drawn districts where the source has one "
                        "or none" % overlaps)
    line = ("%d/%d (%.2f%%) agreement over %d %s' extents, %d overlaps; lowest %s "
            "%.2f%% (%s)" % (agree, total, pct_all, len(extents), spec.group_nouns[1],
                             overlaps, spec.group_nouns[0], worst[0], worst[1]))
    return problems, line


def check_points(spec, feats):
    index = Index(feats)
    problems = []
    for lng, lat, key, why in spec.inside:
        hits = index.at((lng, lat))
        if hits != [key]:
            problems.append("%.5f,%.5f should fall in %s (%s) and falls in %r"
                            % (lat, lng, key, why, hits))
    for lng, lat, why in spec.outside:
        hits = index.at((lng, lat))
        if hits:
            problems.append("%.5f,%.5f should fall in no district (%s) and falls in %r"
                            % (lat, lng, why, hits))
    return problems


# ---------- the record ----------
def write_record(spec, meta, feats, shipped_bytes):
    os.makedirs(os.path.dirname(spec.record_path), exist_ok=True)
    record = {
        "layer": spec.layer,
        "fetched": datetime.date.today().isoformat(),
        "layer_edited": meta.get("layer_edited"),
        "item": meta.get("item"),
        "skipped_records": spec.skipped_records,
        "part_records_joined": spec.multipart_records,
        "fingerprint": fingerprint(spec, feats),
        record_key(spec): per_group(spec, feats),
        "shipped_sha256": hashlib.sha256(shipped_bytes).hexdigest(),
    }
    with open(spec.record_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1, sort_keys=True)
        fh.write("\n")


def load_record(spec):
    with open(spec.record_path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------- the three modes ----------
def run_check(spec):
    with open(spec.out_path, "rb") as fh:
        raw = fh.read()
    geo = json.loads(raw)
    record = load_record(spec)
    feats = geo.get("features") or []
    if spec.extra_check:
        spec.extra_check(feats)
    problems = gate_counts(spec, feats)
    for f in feats:
        p = f["properties"]
        for key in spec.required:
            if p.get(key) in (None, ""):
                problems.append("district %s has no %s" % (p.get("key"), key))
    if hashlib.sha256(raw).hexdigest() != record.get("shipped_sha256"):
        problems.append("the shipped file does not hash to what the builder recorded — "
                        "rebuild it rather than editing it by hand")
    if per_group(spec, feats) != record.get(record_key(spec)):
        problems.append("the shipped file's districts per %s differ from the record"
                        % spec.group_nouns[0])
    problems += check_points(spec, feats)
    problems += sp.check_card(spec, spec.card_noun)
    if problems:
        for p in problems:
            print("%s --check: FAIL: %s" % (spec.label, p))
        raise SystemExit(1)
    n = len(per_group(spec, feats))
    print("%s --check: OK — %d districts in %d %s, matching the record of %s; the card "
          "says %s" % (spec.label, len(feats), n, nouns(spec, n), record["fetched"],
                       "; ".join(repr(c) for c in sp.card_claims(spec))))


def run_watch(spec):
    record = load_record(spec)
    records, meta = sp.fetch(spec, geometry=False)
    feats = normalise(spec, records, with_geometry=False)
    if spec.extra_check:
        spec.extra_check(feats)
    live = fingerprint(spec, feats)
    if live != record["fingerprint"]:
        before = record.get(record_key(spec)) or {}
        after = per_group(spec, feats)
        changed = sorted(b for b in set(before) | set(after) if before.get(b) != after.get(b))
        print("%s --watch: THE LAYER HAS CHANGED since %s: %d districts recorded, %d now "
              "(fingerprint %s -> %s). %s whose count moved: %s. Rebuild the file, bump "
              "the service worker's cache name, and say which %s moved."
              % (spec.label, record["fetched"], record["fingerprint"]["districts"],
                 live["districts"], record["fingerprint"]["sha256"][:12], live["sha256"][:12],
                 spec.group_nouns[1].capitalize(), ", ".join(changed) or
                 "none (labels or areas moved within a %s)" % spec.group_nouns[0],
                 spec.group_nouns[1]))
        raise SystemExit(1)
    note = ""
    if (meta.get("layer_edited") and record.get("layer_edited")
            and meta["layer_edited"] != record["layer_edited"]):
        note = (" The layer's own edit date moved (%s -> %s) without changing any district's "
                "key, label, %s or area." % (record["layer_edited"], meta["layer_edited"],
                                              spec.group_nouns[0]))
    print("%s --watch: unchanged since %s (%d districts).%s"
          % (spec.label, record["fetched"], live["districts"], note))


def run_build(spec, source_path=None, save_source=None):
    stale = sp.check_card(spec, spec.card_noun)
    if stale:
        fail(spec, "; ".join(stale) + " — change the card before building, so the file "
             "and what the card says about it ship together")
    if source_path:
        with open(source_path, encoding="utf-8") as fh:
            saved = json.load(fh)
        records, meta = saved["records"], saved["meta"]
    else:
        records, meta = sp.fetch(spec, geometry=True)
        if save_source:
            with open(save_source, "w", encoding="utf-8") as fh:
                json.dump({"records": records, "meta": meta}, fh)
    feats = normalise(spec, records)
    if spec.extra_check:
        spec.extra_check(feats)
    problems = gate_counts(spec, feats) + check_points(spec, feats)
    if problems:
        for p in problems:
            print("%s: FAIL: %s" % (spec.label, p))
        raise SystemExit(1)

    drawn = sp.simplify(spec, feats)
    problems = []
    if len(drawn["features"]) != len(feats):
        problems.append("%d districts after simplifying, %d before — a whole district was "
                        "lost" % (len(drawn["features"]), len(feats)))
    found, line = validate(spec, feats, drawn["features"])
    problems += found
    problems += check_points(spec, drawn["features"])
    print("agreement: " + line)
    if problems:
        for p in problems:
            print("%s: FAIL: %s" % (spec.label, p))
        raise SystemExit(1)

    compact = json.dumps(drawn, separators=(",", ":"), ensure_ascii=False)
    if json.loads(compact) != drawn:
        fail(spec, "round-trip mismatch before writing")
    data = compact.encode("utf-8")
    with open(spec.out_path, "wb") as fh:
        fh.write(data)
    write_record(spec, meta, feats, data)
    n = len(per_group(spec, feats))
    print("wrote %s: %d districts in %d %s, %d bytes (dp interval=%s m, 6dp)"
          % (os.path.relpath(spec.out_path, REPO_ROOT), len(drawn["features"]), n,
             nouns(spec, n), len(data), spec.interval))


def main(spec, doc):
    ap = argparse.ArgumentParser(description=(doc or "").strip().split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped file to its record")
    ap.add_argument("--watch", action="store_true",
                    help="compare the live layer's fingerprint with the record; exit 1 on a change")
    ap.add_argument("--source", help="build from a saved fetch (written by --save-source)")
    ap.add_argument("--save-source", help="also write the raw fetch here")
    args = ap.parse_args()
    if args.check:
        run_check(spec)
    elif args.watch:
        run_watch(spec)
    else:
        run_build(spec, args.source, args.save_source)
