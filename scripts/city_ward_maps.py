#!/usr/bin/env python3
"""
Build one state's layer of city council districts from a map per city, for
the app to read same-origin.

scripts/published_district_layers.py builds a layer from ONE map a state
office publishes, and Arkansas's wards come from such a map. Where no one map
is current for every city, each city's districts are read from a map of its
own, and this module does that builder's work over a list of sources instead
of one layer. Used on 2026-10-16 by sc/scripts/build_sc_city_wards.py and
tn/scripts/build_tn_city_wards.py, and by nc/scripts/build_nc_city_wards.py,
each of which says why its state's are read this way. In order:

  1. WHICH CITIES are drawn is read from the seats file the council roster is
     built from (<tag>/data/source/<tag>-city-council-seats.json, through
     scripts/city_councils.py, whose drawn_wards says which districts): a
     city with a seat its own district's voters elect is drawn unless the
     council builder declares it undrawn (its
     `undrawn` table, which the state's builder passes in rather than
     copying), and every drawn city has one source, or one per kind of
     district where its council elects by two kinds (Memphis's seven
     districts and two super districts, each its own map): those sources
     then say which districts each draws, and together they must draw
     every district the seats file elects by, none of them twice.
  2. Each source is read with the precinct builder's fetcher
     (scripts/statewide_precincts.py): robots.txt first, retries, an error
     envelope refused, every record fetched by object id. A source names the
     field carrying the district number, a pattern that reads the number out
     of it, how many records the layer publishes and how many of those are
     further parts of a district already read, and both counts must match
     exactly. It also says whose map it is, in words each district carries
     for its card ("the City of Greer's own map").
  3. The districts a source draws must be exactly the ones its city's seats
     file names, and each is labelled with the city's own word for one
     ("District 3", "Ward 3", "District A", "East Ward"), or with the source's
     own where it is a second kind ("Super District 8"), which
     scripts/city_councils.py's --check
     holds the map to as well. The two kinds of district overlap, so a point
     in such a city lies in one of each, and the app's card names both.
  4. A source must be a map of the city it is listed for. At every build the
     union of its districts is compared with the Census Bureau's current
     outline of the place (TIGERweb), and must cover at least the share of
     the place the builder states and lie outside it by no more than the
     share it states. A map of the wrong city or of a county's districts
     fails this, and a few annexed blocks do not; the measured shares go in
     the record.
  5. From there it is the shared builder's work, imported from
     scripts/published_district_layers.py: one Douglas-Peucker run at
     `interval` metres over every city, the drawn file held to the sources by
     points sampled over each city's extent, named points that must land in a
     named district or in none, a record that --check holds the shipped file
     to offline, and the sentences the card must carry.

`--watch` reads every source again, with geometry because these layers are
small, and compares each city's fingerprint, which includes each district's
area to the nearest 1,000 square metres, so a redrawn line is noticed even
when the number of districts stays the same.

WHERE `--check` RUNS: where published_district_layers.py's does, at every
rebuild and at the quarterly re-check the instance's WATCH.md schedules.
"""

import argparse
import datetime
import hashlib
import json
import math
import os
import re
import sys

FLEET_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(FLEET_SCRIPTS)
if FLEET_SCRIPTS not in sys.path:
    sys.path.insert(0, FLEET_SCRIPTS)

import city_councils as cc  # noqa: E402
import published_district_layers as psb  # noqa: E402
import statewide_precincts as sp  # noqa: E402

TIGER_PLACES = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "Places_CouSub_ConCity_SubMCD/MapServer/4")


class Source(object):
    """One city's map. `covers` is the least share of the Census place, in
    percent, the districts must cover, and `outside` the most share of the
    districts, in percent, that may lie outside the place. `drawn_from` says whose
    map it is, in words the card prints after "Drawn from".

    For a city whose council elects by two kinds of district, each kind is a
    source of its own: `wards` names the districts it draws, `word` what it
    calls one where that differs from the city's word in the seats file, and
    `key` tells it apart from the city's other source in the record.

    `pattern`'s first group is the district: a number is read as a number
    ("07" is district 7) and anything else as written, unless `rename` maps it
    to the seats file's name for it ({"EAST": "East"})."""

    def __init__(self, geoid, layer, field, pattern, records, covers, outside, drawn_from,
                 where="1=1", parts=0, word=None, wards=None, key=None, rename=None):
        self.geoid = geoid
        self.key = key or geoid
        self.word = word
        self.rename = dict(rename or {})
        self.wards = tuple(str(w) for w in wards) if wards else None
        self.drawn_from = drawn_from
        self.layer = layer.rstrip("/")
        self.field = field
        self.pattern = re.compile(pattern)
        self.records = records
        self.parts = parts
        self.where = where
        self.covers = covers
        self.outside = outside

    def ward_of(self, text):
        if text in self.rename:
            return self.rename[text]
        return str(int(text)) if text.isdigit() else text


class _Layer(object):
    """The attributes statewide_precincts.fetch reads from a spec, for one layer."""

    def __init__(self, spec, layer, where, out_fields):
        self.label = spec.label
        self.user_agent = spec.user_agent
        self.pace = spec.pace
        self.page = None
        self.layer = layer
        self.where = where
        self.out_fields = out_fields


class Spec(object):
    def __init__(self, tag, label, user_agent, seats_file, out_file, sources, undrawn,
                 card_claims=(), inside=(), outside=(), interval="4", pace=1.0):
        self.tag = tag
        self.label = label
        self.user_agent = user_agent
        self.pace = pace
        self.undrawn = dict(undrawn)
        self.sources = {}
        for s in sources:
            if s.key in self.sources:
                raise SystemExit("%s: FATAL: two sources keyed %s" % (label, s.key))
            self.sources[s.key] = s
        self.instance = os.path.join(REPO_ROOT, tag)
        self.seats_path = os.path.join(self.instance, "data", "source", seats_file)
        self.cities = self._ward_cities()
        self.base = psb.Spec(
            tag=tag, label=label, layer="one map per city, listed in the record",
            user_agent=user_agent, out_fields="",
            expect=sum(len(c["wards"]) for c in self.cities.values()),
            expect_groups=len(self.cities), read=None, out_file=out_file, group="geoid",
            group_nouns=("city", "cities"), card_noun="city council district card",
            interval=interval, pace=pace, card_claims=card_claims, inside=inside,
            outside=outside)

    def _ward_cities(self):
        with open(self.seats_path, encoding="utf-8") as fh:
            cities = json.load(fh)["cities"]
        out = {}
        for geoid, c in sorted(cities.items()):
            wards = cc.drawn_wards(c)
            if wards and geoid not in self.undrawn:
                out[geoid] = {"name": c["name"], "word": c.get("wardWord") or "Ward",
                              "wards": wards}
        geoids = {s.geoid for s in self.sources.values()}
        missing = sorted(set(out) - geoids)
        extra = sorted(geoids - set(out))
        if missing or extra:
            raise SystemExit(
                "%s: FATAL: the seats file elects by district in %s, and the builder has "
                "no source for %s and a source for %s, which elects no seat by district "
                "or is declared undrawn"
                % (self.label, ", ".join(c["name"] for c in out.values()),
                   ", ".join(out[g]["name"] for g in missing) or "none",
                   ", ".join(extra) or "none"))
        for geoid, city in out.items():
            mine = [s for s in self.sources.values() if s.geoid == geoid]
            if len(mine) == 1 and mine[0].wards is None:
                continue
            drawn = [w for s in mine for w in (s.wards or ())]
            if (any(s.wards is None for s in mine) or len(drawn) != len(set(drawn))
                    or sorted(drawn, key=cc.ward_sort_key) != city["wards"]):
                raise SystemExit(
                    "%s: FATAL: %s's %d sources draw %s, and the seats file elects by %s; "
                    "a city with more than one source names the districts each draws, and "
                    "together they draw each district once"
                    % (self.label, city["name"], len(mine),
                       "; ".join("%s %s" % (s.key, ",".join(s.wards or ("every one",)))
                                 for s in mine),
                       ", ".join(city["wards"])))
        return out

    def wards_of(self, src):
        """The districts one source draws, as the seats file numbers them."""
        return list(src.wards) if src.wards else self.cities[src.geoid]["wards"]

    def word_of(self, src):
        return src.word or self.cities[src.geoid]["word"]

    def name_of(self, src):
        """The city, and which of its maps where it has two, for messages."""
        name = self.cities[src.geoid]["name"]
        return name if src.wards is None else "%s (%ss)" % (name, self.word_of(src))

    def source_for(self, geoid, ward):
        for s in self.sources.values():
            if s.geoid == geoid and str(ward) in self.wards_of(s):
                return s
        return None

    def feats_of(self, src, feats):
        wards = set(self.wards_of(src))
        return [f for f in feats if f["properties"]["geoid"] == src.geoid
                and f["properties"]["ward"] in wards]


def fail(spec, msg):
    raise SystemExit("%s: FATAL: %s" % (spec.label, msg))


# ---------- read ----------
def _ring_area(ring, k):
    s = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i][0] * k, ring[i][1]
        x2, y2 = ring[i + 1][0] * k, ring[i + 1][1]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0 * 111320.0 * 110574.0


def area_m2(geom):
    """A district's area in square metres, holes subtracted, on a local
    equirectangular projection; enough to notice a redrawn line."""
    polys = sp._polygons(geom)
    k = math.cos(math.radians(polys[0][0][0][1]))
    total = 0.0
    for poly in polys:
        for i, ring in enumerate(poly):
            total += _ring_area(ring, k) * (1 if i == 0 else -1)
    return total


def read_source(spec, src, records, with_geometry=True):
    """The city's districts from one layer's records: (features, problems)."""
    city = spec.cities[src.geoid]
    word, expected, name = spec.word_of(src), spec.wards_of(src), spec.name_of(src)
    feats, by_key, parts, problems = [], {}, 0, []
    for rec in records:
        props = rec.get("properties") or {}
        raw = props.get(src.field)
        m = src.pattern.fullmatch(str(raw).strip()) if raw is not None else None
        if not m:
            fail(spec, "%s: a record's %s reads %r, which the builder does not know how to "
                 "read as a district number" % (name, src.field, raw))
        n = src.ward_of(m.group(1))
        key = "%s-%s" % (src.geoid, n)
        geom = rec.get("geometry")
        if with_geometry and not geom:
            fail(spec, "%s district %s has no geometry" % (name, n))
        prior = by_key.get(key)
        if prior is not None:
            parts += 1
            if with_geometry:
                prior["geometry"] = {"type": "MultiPolygon", "coordinates":
                                     sp._polygons(prior["geometry"]) + sp._polygons(geom)}
            continue
        feat = {"type": "Feature", "geometry": geom, "properties": {
            "key": key, "geoid": src.geoid, "city": city["name"], "ward": n,
            "label": cc.ward_label(word, n), "drawnFrom": src.drawn_from}}
        by_key[key] = feat
        feats.append(feat)
    if with_geometry:
        for f in feats:
            f["properties"]["_measure"] = area_m2(f["geometry"]) / 1000.0
    if len(records) != src.records:
        problems.append("%s's layer published %d records, and the builder expects %d. Read "
                        "the layer before changing the number" % (name, len(records),
                                                                  src.records))
    if parts != src.parts:
        problems.append("%d of %s's records are further parts of a district already read, "
                        "and the builder declares %d" % (parts, name, src.parts))
    drawn = sorted((f["properties"]["ward"] for f in feats), key=cc.ward_sort_key)
    if drawn != expected:
        problems.append("%s's layer draws %s %s, and the seats file elects by %s %s"
                        % (name, word.lower() + "s", ", ".join(drawn),
                           word.lower() + "s", ", ".join(expected)))
    return feats, problems


# ---------- is each map the city's? ----------
def coverage(spec, feats, places):
    """Each city's districts against the Census outline of the place:
    (problems, {geoid: (covers %, outside %)})."""
    from shapely.geometry import shape  # noqa: PLC0415  (build-time only)
    from shapely.ops import transform, unary_union  # noqa: PLC0415

    problems, measured = [], {}
    for key, src in sorted(spec.sources.items()):
        name = spec.name_of(src)
        place = places[src.geoid]
        wards = unary_union([shape(f["geometry"]).buffer(0) for f in spec.feats_of(src, feats)])
        k = math.cos(math.radians(place.centroid.y))
        proj = lambda x, y, z=None: (x * 111320.0 * k, y * 110574.0)  # noqa: E731
        p, w = transform(proj, place), transform(proj, wards)
        covers = round(100.0 * w.intersection(p).area / p.area, 1)
        outside = round(100.0 * w.difference(p).area / w.area, 1)
        measured[key] = (covers, outside)
        if covers < src.covers:
            problems.append("%s's districts cover %.1f%% of the Census outline of the city, "
                            "and the builder wants at least %.1f%%: is this still the city's "
                            "map?" % (name, covers, src.covers))
        if outside > src.outside:
            problems.append("%.1f%% of %s's districts lie outside the Census outline of the "
                            "city, and the builder allows %.1f%%: is this still the city's "
                            "map?" % (outside, name, src.outside))
    return problems, measured


def fetch_places(spec):
    from shapely.geometry import shape  # noqa: PLC0415  (build-time only)

    geoids = sorted({s.geoid for s in spec.sources.values()})
    where = "GEOID IN (%s)" % ",".join("'%s'" % g for g in geoids)
    records, _meta = sp.fetch(_Layer(spec, TIGER_PLACES, where, "GEOID,BASENAME"), geometry=True)
    places = {}
    for rec in records:
        p = rec.get("properties") or {}
        geoid = str(p.get("GEOID"))
        if geoid not in geoids:
            fail(spec, "TIGERweb answered place %r, which was not asked for" % geoid)
        if p.get("BASENAME") != spec.cities[geoid]["name"]:
            fail(spec, "TIGERweb names place %s %r and the seats file %r"
                 % (geoid, p.get("BASENAME"), spec.cities[geoid]["name"]))
        places[geoid] = shape(rec["geometry"]).buffer(0)
    missing = sorted(set(geoids) - set(places))
    if missing:
        fail(spec, "TIGERweb has no outline for %s" % ", ".join(missing))
    return places


# ---------- the record ----------
def city_fingerprints(spec, feats):
    out = {}
    for key, src in spec.sources.items():
        out[key] = psb.fingerprint(spec.base, spec.feats_of(src, feats))
    return out


def write_record(spec, metas, feats, measured, shipped_bytes):
    base = spec.base
    prints = city_fingerprints(spec, feats)
    sources = {}
    for key, src in sorted(spec.sources.items()):
        covers, outside = measured[key]
        sources[key] = {
            "city": spec.cities[src.geoid]["name"],
            "layer": src.layer,
            "where": src.where,
            "field": src.field,
            "layer_edited": metas[key].get("layer_edited"),
            "item": metas[key].get("item"),
            "records": src.records,
            "part_records_joined": src.parts,
            "covers_place_pct": covers,
            "outside_place_pct": outside,
            "fingerprint": prints[key],
        }
        if src.wards:
            sources[key]["districts"] = list(src.wards)
    record = {
        "fetched": datetime.date.today().isoformat(),
        "places_layer": TIGER_PLACES,
        "sources": sources,
        "fingerprint": psb.fingerprint(base, feats),
        psb.record_key(base): psb.per_group(base, feats),
        "shipped_sha256": hashlib.sha256(shipped_bytes).hexdigest(),
    }
    os.makedirs(os.path.dirname(base.record_path), exist_ok=True)
    with open(base.record_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1, sort_keys=True)
        fh.write("\n")


def check_labels(spec, feats):
    """Every drawn district against the seats file, offline."""
    problems = []
    drawn = {}
    for f in feats:
        p = f["properties"]
        drawn.setdefault(p["geoid"], []).append(p)
    for geoid, city in sorted(spec.cities.items()):
        props = drawn.get(geoid, [])
        wards = sorted((p["ward"] for p in props), key=cc.ward_sort_key)
        if wards != city["wards"]:
            problems.append("the file draws %s %s %s, and the seats file elects by %s"
                            % (city["name"], city["word"].lower() + "s", ", ".join(wards),
                               ", ".join(city["wards"])))
        for p in props:
            src = spec.source_for(geoid, p["ward"])
            want = cc.ward_label(spec.word_of(src) if src else city["word"], p["ward"])
            if p["label"] != want or p["city"] != city["name"] or p["key"] != "%s-%s" % (
                    geoid, p["ward"]):
                problems.append("%s: a district reads %r, %r, %r; the seats file makes it %r"
                                % (city["name"], p["key"], p["city"], p["label"], want))
            if src is not None and p.get("drawnFrom") != src.drawn_from:
                problems.append("%s %s says it is drawn from %r, and the builder says %r"
                                % (city["name"], p["label"], p.get("drawnFrom"), src.drawn_from))
    for geoid in sorted(set(drawn) - set(spec.cities)):
        problems.append("the file draws districts for %s, which the seats file does not draw"
                        % geoid)
    return problems


# ---------- the three modes ----------
def run_check(spec):
    base = spec.base
    with open(base.out_path, "rb") as fh:
        raw = fh.read()
    feats = json.loads(raw).get("features") or []
    with open(base.record_path, encoding="utf-8") as fh:
        record = json.load(fh)
    problems = psb.gate_counts(base, feats) + check_labels(spec, feats)
    if hashlib.sha256(raw).hexdigest() != record.get("shipped_sha256"):
        problems.append("the shipped file does not hash to what the builder recorded — "
                        "rebuild it rather than editing it by hand")
    if psb.per_group(base, feats) != record.get(psb.record_key(base)):
        problems.append("the shipped file's districts per city differ from the record")
    recorded = record.get("sources") or {}
    for key, src in sorted(spec.sources.items()):
        r = recorded.get(key)
        if r is None:
            problems.append("the record has never read %s's map; run the build"
                            % spec.name_of(src))
        elif (r.get("layer"), r.get("where"), r.get("field"), r.get("records"),
              r.get("part_records_joined")) != (src.layer, src.where, src.field,
                                                src.records, src.parts):
            problems.append("%s's map was last read from %s and the builder now reads %s; "
                            "run the build" % (spec.name_of(src), r.get("layer"),
                                               src.layer))
    for key in sorted(set(recorded) - set(spec.sources)):
        problems.append("the record holds a map for %s, which the builder no longer reads; "
                        "run the build" % key)
    problems += psb.check_points(base, feats)
    problems += sp.check_card(base, base.card_noun)
    if problems:
        for p in problems:
            print("%s --check: FAIL: %s" % (spec.label, p))
        raise SystemExit(1)
    print("%s --check: OK — %d districts in %d cities, matching the record of %s and the "
          "seats file; the card says %s"
          % (spec.label, len(feats), len(spec.cities), record["fetched"],
             "; ".join(repr(c) for c in sp.card_claims(base))))


def run_watch(spec):
    base = spec.base
    with open(base.record_path, encoding="utf-8") as fh:
        record = json.load(fh)
    moved = []
    for key, src in sorted(spec.sources.items()):
        name = spec.name_of(src)
        records, _meta = sp.fetch(_Layer(spec, src.layer, src.where, src.field), geometry=True)
        feats, problems = read_source(spec, src, records)
        live = psb.fingerprint(base, feats)
        was = (record.get("sources") or {}).get(key, {}).get("fingerprint")
        if problems or live != was:
            moved.append(name)
            for p in problems:
                print("%s --watch: %s" % (spec.label, p))
            print("%s --watch: %s's map HAS CHANGED since %s (fingerprint %s -> %s)"
                  % (spec.label, name, record["fetched"], (was or {}).get("sha256", "")[:12],
                     live["sha256"][:12]))
    if moved:
        print("%s --watch: rebuild the file, bump the service worker's cache name, and say "
              "which cities moved: %s" % (spec.label, ", ".join(moved)))
        raise SystemExit(1)
    print("%s --watch: every city's map unchanged since %s (%d districts in %d cities)"
          % (spec.label, record["fetched"], record["fingerprint"]["districts"],
             len(spec.sources)))


def run_build(spec, source_path=None, save_source=None):
    base = spec.base
    stale = sp.check_card(base, base.card_noun)
    if stale:
        fail(spec, "; ".join(stale) + " — change the card before building, so the file "
             "and what the card says about it ship together")
    if source_path:
        with open(source_path, encoding="utf-8") as fh:
            saved = json.load(fh)
    else:
        saved = {"sources": {}}
        for key, src in sorted(spec.sources.items()):
            records, meta = sp.fetch(_Layer(spec, src.layer, src.where, src.field),
                                     geometry=True)
            saved["sources"][key] = {"records": records, "meta": meta}
        if save_source:
            with open(save_source, "w", encoding="utf-8") as fh:
                json.dump(saved, fh)
    feats, problems, metas = [], [], {}
    for key, src in sorted(spec.sources.items()):
        got = saved["sources"].get(key)
        if got is None:
            fail(spec, "the saved fetch has no map for %s" % spec.name_of(src))
        found, why = read_source(spec, src, got["records"])
        feats += found
        problems += why
        metas[key] = got["meta"]
    problems += psb.gate_counts(base, feats) + psb.check_points(base, feats)
    found, measured = coverage(spec, feats, fetch_places(spec))
    problems += found
    for key, (covers, outside) in sorted(measured.items()):
        print("  %-28s covers %5.1f%% of the place, %4.1f%% outside it"
              % (spec.name_of(spec.sources[key]), covers, outside))
    if problems:
        for p in problems:
            print("%s: FAIL: %s" % (spec.label, p))
        raise SystemExit(1)

    drawn = sp.simplify(base, feats)
    problems = []
    if len(drawn["features"]) != len(feats):
        problems.append("%d districts after simplifying, %d before — a whole district was "
                        "lost" % (len(drawn["features"]), len(feats)))
    found, line = psb.validate(base, feats, drawn["features"])
    problems += found
    problems += psb.check_points(base, drawn["features"])
    print("agreement: " + line)
    if problems:
        for p in problems:
            print("%s: FAIL: %s" % (spec.label, p))
        raise SystemExit(1)

    compact = json.dumps(drawn, separators=(",", ":"), ensure_ascii=False)
    if json.loads(compact) != drawn:
        fail(spec, "round-trip mismatch before writing")
    data = compact.encode("utf-8")
    with open(base.out_path, "wb") as fh:
        fh.write(data)
    write_record(spec, metas, feats, measured, data)
    print("wrote %s: %d districts in %d cities, %d bytes (dp interval=%s m, 6dp)"
          % (os.path.relpath(base.out_path, REPO_ROOT), len(drawn["features"]),
             len(spec.cities), len(data), base.interval))


def main(spec, doc):
    ap = argparse.ArgumentParser(description=(doc or "").strip().split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped file to its record and the seats file")
    ap.add_argument("--watch", action="store_true",
                    help="read every city's map again; exit 1 if any has changed")
    ap.add_argument("--source", help="build from a saved fetch (written by --save-source)")
    ap.add_argument("--save-source", help="also write the raw fetch here")
    args = ap.parse_args()
    if args.check:
        run_check(spec)
    elif args.watch:
        run_watch(spec)
    else:
        run_build(spec, args.source, args.save_source)
