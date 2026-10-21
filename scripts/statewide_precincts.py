#!/usr/bin/env python3
"""
Build one state's election-precinct file from the one layer that state
publishes for every precinct, for the app to read same-origin.

Seven states use this, each through a short builder of its own
(<tag>/scripts/build_<tag>_precincts.py): Kentucky, North Carolina, Indiana,
South Carolina, Arkansas and Tennessee, all measured 2026-10-15 to publish a
current statewide precinct layer from a government office (the research is
/mnt/project-files/research/precinct-sources-six-states-2026-10-15.md in the
project's shared folder), and Louisiana since 2026-10-21. A state's builder
says where its layer is, how to read one record and what to expect;
everything else lives here once, because seven copies of Minnesota's builder
would be seven readers of one question.

THE SHAPE IS MINNESOTA'S (mn/scripts/build_mn_precincts.py): fetch the whole
layer, check it, simplify it with Douglas-Peucker, refuse to write unless the
simplified file answers as the source does, and ship it as a data/app file. A
reader's click is answered from that file, so no point is sent to a state
server, and the privacy page has nothing to add.

A STATE WHOSE PRECINCTS ARE A FILE (Louisiana, 2026-10-21: the Legislature's
redistricting office publishes them as one zipped shapefile, edition by
edition) names a `fetcher` instead of reading an ArcGIS layer. ShapefileZip
is that fetcher: robots.txt first, the listing page held to the edition the
builder names, the whole zip read through mapshaper, and the file's own
digest kept in the record. Everything after the fetch is the same code.

WHAT IS HELD, IN ORDER
  1. robots.txt is read before the first request with the client that crawls,
     and a Crawl-delay the host states, or the builder's own pace, separates
     every request after the first.
  2. An ArcGIS error inside a 200 answer stops the build; it is never read as
     a page with no precincts in it.
  3. Every record goes through the state's `read()`. A record it cannot read
     stops the build. Two records with the same key are dropped to one only
     when their geometry is identical AND the builder declares how many such
     pairs it expects, so a publisher's duplicate is measured, not absorbed.
     A layer that publishes one record per PART of a precinct (Arkansas's
     does, for a precinct in pieces) declares how many records are further
     parts, and those are joined into one precinct whose properties must
     agree, bar the fields the builder names as allowed to differ between
     parts, of which the latest is kept. A builder declares one of the two
     shapes, never both, because the watch reads no geometry and could not
     tell a repeat from a part.
  4. The count after reading equals the builder's EXPECT exactly, every
     county in the instance's own county file appears, the key is unique and
     every property the card prints is populated.
  5. Douglas-Peucker at `interval` metres with keep-shapes, in ONE mapshaper
     run so an edge two precincts share is simplified once. DP removes a
     vertex only when it lies within the interval of the line kept in its
     place, so the drawn line strays no further than that by construction,
     which area thresholding does not give (the fleet's finding three times).
     THE INTERVAL IS CHOSEN BY ONE RULE, measured per state: the smallest of
     4, 8 and 12 metres that brings the gzipped file to 2.5 MB or under,
     because a reader's card waits for the whole file and Minnesota's, the
     sibling nearest in kind, is 1.67 MB. Kentucky's precincts follow creeks
     and roads rather than a survey grid, so at Minnesota's 4 m its file was
     14.1 MB raw and 3.5 MB gzipped; at 8 m it is 10.2 MB and 2.49 MB, at
     12 m 8.4 MB and 2.0 MB (measured 2026-10-15). The card states the
     interval, so a reader near a line knows how far it can be off.
  6. No precinct is lost in simplification; 6,000 random points over the
     state's envelope get the same precinct from the drawn file as from the
     source at least 99.5% of the time, with no point in two precincts; and
     points sampled inside each county, as the Census draws it in the
     instance's own county file, land in that county's precincts at the
     rate the builder sets from its first measured build. A county the
     precinct file leaves partly undefined (Louisiana's five parishes on
     Lake Pontchartrain) gets a floor of its own, which the builder states
     with the share it measured; every other county keeps the general one.
  7. A record (data/source/<file>.source.json) keeps the fetch date, the
     layer's own edit date where it publishes one, a fingerprint of what a
     re-precincting changes, the count in every county and the shipped file's
     hash. `--check` holds the shipped file to it offline; `--watch` reads the
     live layer's attributes, no geometry, and compares the fingerprint.
  8. The card says what the file is, and the builder holds it to that: the
     precinct module in <tag>/index.html must contain "drawn here to within
     <interval> metres" and each sentence the builder lists in
     `card_claims` (an edition, a file's date), with the page's "..." + "..."
     string joins read through. A build refuses to start, and `--check`
     fails, when the card no longer says them, so a rebuild at another
     interval or from a newer edition cannot leave the card describing the
     old one.

WHERE `--check` RUNS. When a person runs it: at every rebuild and at the
quarterly re-check each instance's WATCH.md schedules. It is not in the CI
battery, as Minnesota's precinct builder's is not, because adding a step to
.github/workflows/smoke-test.yml is a workflow change; the battery's own
gate on these files is each instance's validate_index.py, which holds the
exact precinct count.

WHAT IS NOT CLAIMED. Wisconsin's dropped-ring classifier and per-vertex stray
ceiling are not applied, as in Minnesota's builder, so a small hole or
detached part that simplification loses would be reported by nothing unless
a sample point landed in it.
"""

import argparse
import datetime
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time

FLEET_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(FLEET_SCRIPTS)
if FLEET_SCRIPTS not in sys.path:
    sys.path.insert(0, FLEET_SCRIPTS)

MAPSHAPER = "mapshaper@0.6.102"  # pinned, as every boundary builder in the fleet
PRECISION = "0.000001"           # 6 decimals, about 0.11 m
VALIDATE_SAMPLES = 6000          # Minnesota's figure: precincts are small
GRID = 0.05                      # degrees per cell of the point-lookup index


class Spec(object):
    """What a state's builder supplies. Every argument is required unless it
    has a default, so a builder cannot leave one out by accident."""

    def __init__(self, tag, label, layer, user_agent, out_fields, expect,
                 expect_counties, state_bbox, read, out_file, interval="4",
                 pace=0.0, page=None, where="1=1", measure_field=None,
                 identical_duplicates=0, tiling_min_same=0.97,
                 tiling_max_other=0.02, tiling_samples=200, edit_date=None,
                 required=("key", "name", "countyFips"), extra_check=None,
                 multipart_records=0, part_latest=(), card_claims=(),
                 fetcher=None, tiling_floor_by_county=None):
        self.tag = tag
        self.label = label
        self.layer = layer.rstrip("/")
        self.user_agent = user_agent
        self.out_fields = out_fields
        self.expect = expect
        self.expect_counties = expect_counties
        self.state_bbox = state_bbox
        self.read = read
        self.out_file = out_file
        self.interval = interval
        self.pace = pace
        self.page = page
        self.where = where
        self.measure_field = measure_field
        self.identical_duplicates = identical_duplicates
        self.tiling_min_same = tiling_min_same
        self.tiling_max_other = tiling_max_other
        self.tiling_samples = tiling_samples
        self.edit_date = edit_date
        self.required = required
        # A state's own check on the read records, run in all three modes:
        # extra_check(features) raises through fail() on anything wrong.
        self.extra_check = extra_check
        # Records that are further parts of a precinct already read, joined
        # into it; part_latest names the properties that may differ between
        # parts, of which the largest (for a date, the latest) is kept.
        self.multipart_records = multipart_records
        self.part_latest = tuple(part_latest)
        # Sentences the card must carry beyond the interval, each stating
        # something this builder knows (an edition, a file's date).
        self.card_claims = tuple(card_claims)
        # A state whose precincts are a file rather than an ArcGIS layer
        # supplies fetcher(spec, geometry) -> (records, meta), records shaped
        # as fetch() returns them; ShapefileZip below is the one in use.
        self.fetcher = fetcher
        # A county whose own share is lower for a reason the builder measured
        # and states (Louisiana's precinct file leaves Lake Pontchartrain
        # undefined, and the county file carries the lake): GEOID -> its own
        # floor, each below tiling_min_same. Every other county keeps that.
        self.tiling_floor_by_county = dict(tiling_floor_by_county or {})
        for geoid, floor in self.tiling_floor_by_county.items():
            if not floor < tiling_min_same:
                raise SystemExit("%s: county %s's tiling floor %r is not below the general "
                                 "%r, so it declares nothing" % (label, geoid, floor,
                                                                 tiling_min_same))
        if multipart_records and identical_duplicates:
            raise SystemExit("%s: a builder declares repeated records or records in parts, "
                             "not both" % label)
        # The measure goes into the fingerprint, so it is always asked for:
        # a first draft left it out of the request and the fingerprint
        # silently carried no shape at all.
        if measure_field and measure_field not in out_fields.split(","):
            self.out_fields = out_fields + "," + measure_field
        self.instance = os.path.join(REPO_ROOT, tag)
        self.out_path = os.path.join(self.instance, "data", "app", out_file)
        self.record_path = os.path.join(
            self.instance, "data", "source", out_file.replace(".json", ".source.json"))
        self.counties_path = os.path.join(self.instance, "data", "app", "state-counties.json")


def fail(spec, msg):
    raise SystemExit("%s: FATAL: %s" % (spec.label, msg))


# ---------- the instance's own county fabric ----------
def load_counties(spec):
    with open(spec.counties_path, encoding="utf-8") as fh:
        feats = json.load(fh)["features"]
    out = {}
    for f in feats:
        p = f["properties"]
        out[str(p["GEOID"])] = {"name": p["NAME"], "geometry": f["geometry"]}
    if len(out) != spec.expect_counties:
        fail(spec, "%s holds %d counties, expected %d"
             % (os.path.relpath(spec.counties_path, REPO_ROOT), len(out), spec.expect_counties))
    return out


# ---------- fetch ----------
class Fetcher(object):
    """Reads one ArcGIS layer: robots.txt first, then every request paced."""

    def __init__(self, spec):
        import requests  # noqa: PLC0415  (fleet scraper dependency)
        import robots_policy  # noqa: PLC0415

        self.spec = spec
        self.session = requests.Session()
        self.session.headers["User-Agent"] = spec.user_agent
        gate = robots_policy.RobotsGate(self.session, spec.user_agent)
        probe = spec.layer + "/query"
        ok, why = gate.allows(probe)
        print("robots.txt: %s — %s" % ("allowed" if ok else "REFUSED", why), file=sys.stderr)
        if not ok:
            fail(spec, "the host refuses this client in its robots.txt — not fetching. %s" % why)
        stated = gate.crawl_delay(probe) or 0.0
        self.pace = max(float(stated), float(spec.pace))
        if stated:
            print("robots.txt states Crawl-delay %s; pacing %.0f s" % (stated, self.pace),
                  file=sys.stderr)
        self.requests = 0

    def get(self, url, params):
        if self.requests:
            time.sleep(self.pace)
        self.requests += 1
        last = None
        for attempt in range(4):
            try:
                resp = self.session.get(url, params=params, timeout=600)
                resp.raise_for_status()
                doc = resp.json()
                break
            except Exception as exc:  # noqa: BLE001  (retried, then reported)
                last = exc
                time.sleep(max(self.pace, 5.0) * (attempt + 1))
        else:
            fail(self.spec, "%s did not answer after four tries: %s" % (url, last))
        if "error" in doc:
            fail(self.spec, "the layer answered an error envelope: %r" % doc["error"])
        return doc

    def metadata(self):
        return self.get(self.spec.layer, {"f": "json"})

    def object_ids(self, oid_field):
        doc = self.get(self.spec.layer + "/query",
                       {"where": self.spec.where, "returnIdsOnly": "true", "f": "json"})
        ids = doc.get("objectIds")
        if ids is None:
            fail(self.spec, "the layer returned no objectIds list")
        return sorted(ids)

    def records(self, oid_field, page, geometry):
        """Every record, fetched in runs of consecutive object ids so a page
        boundary cannot move under the fetch and no record is read twice."""
        ids = self.object_ids(oid_field)
        out = []
        for i in range(0, len(ids), page):
            run = ids[i:i + page]
            where = "(%s) AND %s >= %d AND %s <= %d" % (
                self.spec.where, oid_field, run[0], oid_field, run[-1])
            params = {"where": where, "outFields": self.spec.out_fields,
                      "returnGeometry": "true" if geometry else "false",
                      "orderByFields": oid_field, "f": "geojson" if geometry else "json"}
            if geometry:
                params.update({"outSR": "4326", "geometryPrecision": "6"})
            doc = self.get(self.spec.layer + "/query", params)
            feats = doc.get("features")
            if feats is None:
                fail(self.spec, "a page carried no features key")
            if len(feats) != len(run):
                fail(self.spec, "asked for %d records by object id and got %d — the "
                     "layer changed during the fetch or truncated a page"
                     % (len(run), len(feats)))
            if geometry:
                out.extend(feats)
            else:
                out.extend({"properties": f.get("attributes") or {}, "geometry": None}
                           for f in feats)
            print("  fetched %d of %d" % (len(out), len(ids)), file=sys.stderr)
        if len(out) != len(ids):
            fail(self.spec, "fetched %d records for %d object ids" % (len(out), len(ids)))
        return out


def fetch(spec, geometry=True):
    # getattr: the other fleet modules hand this function spec-like objects
    # of their own, which carry no fetcher.
    fetcher = getattr(spec, "fetcher", None)
    if fetcher is not None:
        return fetcher(spec, geometry)
    f = Fetcher(spec)
    meta = f.metadata()
    oid = meta.get("objectIdField") or next(
        (x["name"] for x in meta.get("fields") or [] if x.get("type") == "esriFieldTypeOID"),
        None)
    if not oid:
        fail(spec, "the layer names no object id field")
    page = spec.page or int(meta.get("maxRecordCount") or 1000)
    page = min(page, int(meta.get("maxRecordCount") or page))
    edit = (meta.get("editingInfo") or {}).get("lastEditDate")
    edited = (datetime.datetime.fromtimestamp(edit / 1000.0, datetime.timezone.utc)
              .strftime("%Y-%m-%dT%H:%M:%SZ") if edit else None)
    records = f.records(oid, page, geometry)
    return records, {"layer_edited": edited, "item": meta.get("serviceItemId") or None}


class ShapefileZip(object):
    """A spec's fetcher for precincts published as one zipped shapefile, the
    shape Louisiana's Legislature uses. robots.txt is read first with the
    client that crawls, for the listing page as well as the file; the zip is
    read whole (a file has no attribute-only route, so --watch reads it too)
    and converted to WGS84 GeoJSON through mapshaper. The meta carries the
    file's Last-Modified as `layer_edited` and its SHA-256 as `source_sha256`.

    `listing`, when given, is the page that links every edition, and
    `edition_re` a pattern with one group per part of a link's date (year,
    month, day, named y, m and d). The newest edition listed must be the one
    `spec.layer` names, or the build stops: a newer edition is read by a person
    before it ships, never picked up because it appeared."""

    def __init__(self, listing=None, edition_re=None):
        self.listing = listing
        self.edition_re = re.compile(edition_re) if edition_re else None
        if bool(listing) != bool(edition_re):
            raise SystemExit("ShapefileZip: a listing and its edition pattern come together")

    def _edition(self, spec, text):
        m = self.edition_re.search(text)
        if not m:
            return None
        return datetime.date(int(m.group("y")), int(m.group("m")), int(m.group("d")))

    def __call__(self, spec, geometry=True):
        import urllib.parse  # noqa: PLC0415
        import requests  # noqa: PLC0415  (fleet scraper dependency)
        import robots_policy  # noqa: PLC0415

        session = requests.Session()
        session.headers["User-Agent"] = spec.user_agent
        gate = robots_policy.RobotsGate(session, spec.user_agent)

        def get(url, **kw):
            ok, why = gate.allows(url)
            print("robots.txt: %s — %s (%s)" % ("allowed" if ok else "REFUSED", why, url),
                  file=sys.stderr)
            if not ok:
                fail(spec, "the host refuses this client in its robots.txt — not fetching. %s"
                     % why)
            delay = max(float(gate.crawl_delay(url) or 0.0), float(spec.pace))
            last = None
            for attempt in range(4):
                if attempt or get.count:
                    time.sleep(max(delay, 5.0 * attempt))
                get.count += 1
                try:
                    resp = session.get(url, timeout=600, **kw)
                    resp.raise_for_status()
                    return resp
                except Exception as exc:  # noqa: BLE001  (retried, then reported)
                    last = exc
            fail(spec, "%s did not answer after four tries: %s" % (url, last))
        get.count = 0

        pinned = self._edition(spec, urllib.parse.unquote(spec.layer)) if self.edition_re else None
        if self.listing:
            if pinned is None:
                fail(spec, "the file the builder names does not match its own edition pattern")
            page = get(self.listing).text
            listed = sorted({d for d in (self._edition(spec, urllib.parse.unquote(h))
                                         for h in re.findall(r'href="([^"]+)"', page)) if d})
            if not listed:
                fail(spec, "%s lists no edition the pattern recognises — the page changed; "
                     "read it before building" % self.listing)
            if pinned not in listed:
                fail(spec, "%s no longer lists the edition of %s that the builder names"
                     % (self.listing, pinned.isoformat()))
            if listed[-1] != pinned:
                fail(spec, "%s lists a newer edition, of %s, than the %s the builder names: "
                     "read it, then point the builder at it deliberately"
                     % (self.listing, listed[-1].isoformat(), pinned.isoformat()))
            print("listing: the newest edition is the one named (%s)" % pinned.isoformat(),
                  file=sys.stderr)
        resp = get(spec.layer)
        body = resp.content
        stamp = resp.headers.get("Last-Modified")
        edited = None
        if stamp:
            import email.utils  # noqa: PLC0415
            edited = email.utils.parsedate_to_datetime(stamp).astimezone(
                datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "source.zip")
            dst = os.path.join(tmp, "source.geojson")
            with open(src, "wb") as fh:
                fh.write(body)
            proc = subprocess.run(["npx", "-y", MAPSHAPER, "-i", src, "-proj", "wgs84",
                                   "-o", "format=geojson", dst],
                                  capture_output=True, text=True, cwd=spec.instance)
            if proc.returncode != 0 or not os.path.exists(dst):
                fail(spec, "mapshaper could not read the zip (%d): %s"
                     % (proc.returncode, (proc.stderr or "")[-800:]))
            with open(dst, encoding="utf-8") as fh:
                doc = json.load(fh)
        records = [{"properties": f.get("properties") or {},
                    "geometry": f.get("geometry") if geometry else None}
                   for f in doc.get("features") or []]
        print("  read %d records from %d bytes" % (len(records), len(body)), file=sys.stderr)
        return records, {"layer_edited": edited, "item": None,
                         "source_sha256": hashlib.sha256(body).hexdigest()}


# ---------- read ----------
def _geometry_digest(geom):
    return hashlib.sha256(json.dumps(geom, sort_keys=True, separators=(",", ":"))
                          .encode()).hexdigest()


def _polygons(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return list(geom["coordinates"])
    raise SystemExit("a precinct's geometry is a %s, not a polygon" % geom["type"])


def _join_part(spec, prior, out, geom, with_geometry):
    """Join a further part of a precinct into the feature already read."""
    skip = ("_measure",) + spec.part_latest
    a = {k: v for k, v in prior["properties"].items() if k not in skip}
    b = {k: v for k, v in out.items() if k not in skip}
    if a != b:
        fail(spec, "two parts of precinct %s differ in what they say: %r and %r"
             % (out["key"], a, b))
    p = prior["properties"]
    if spec.measure_field:
        p["_measure"] = float(p["_measure"]) + float(out["_measure"])
    for field in spec.part_latest:
        values = [v for v in (p.get(field), out.get(field)) if v not in (None, "")]
        if values:
            p[field] = max(values)
    if with_geometry:
        prior["geometry"] = {"type": "MultiPolygon",
                             "coordinates": _polygons(prior["geometry"]) + _polygons(geom)}


def normalise(spec, records, counties, with_geometry=True):
    feats, by_key, dupes, parts = [], {}, 0, 0
    for rec in records:
        props = rec.get("properties") or {}
        out = spec.read(props)
        if not isinstance(out, dict):
            fail(spec, "read() returned %r for %r" % (out, props))
        fips = out.get("countyFips")
        if fips not in counties:
            fail(spec, "a record names county %r, which is not in the county file: %r"
                 % (fips, props))
        out["county"] = counties[fips]["name"]
        for key in spec.required:
            if out.get(key) in (None, ""):
                fail(spec, "a record reads with no %s: %r" % (key, props))
        if with_geometry and not rec.get("geometry"):
            fail(spec, "precinct %s has no geometry" % out["key"])
        if spec.measure_field:
            if props.get(spec.measure_field) is None:
                fail(spec, "precinct %s carries no %s, which the fingerprint reads"
                     % (out["key"], spec.measure_field))
            out["_measure"] = props.get(spec.measure_field)
        prior = by_key.get(out["key"])
        if prior is not None and spec.multipart_records:
            _join_part(spec, prior, out, rec.get("geometry"), with_geometry)
            parts += 1
            continue
        if prior is not None:
            same = (not with_geometry) or (
                _geometry_digest(prior["geometry"]) == _geometry_digest(rec["geometry"]))
            if not same:
                fail(spec, "two different precincts read with the key %s" % out["key"])
            if {k: v for k, v in prior["properties"].items() if k != "_measure"} != \
                    {k: v for k, v in out.items() if k != "_measure"}:
                fail(spec, "two records share the key %s and differ in what they say"
                     % out["key"])
            dupes += 1
            continue
        feat = {"type": "Feature", "properties": out, "geometry": rec.get("geometry")}
        by_key[out["key"]] = feat
        feats.append(feat)
    if dupes != spec.identical_duplicates:
        fail(spec, "%d records repeat another record exactly, and the builder declares %d. "
             "Read the layer before changing the declaration" % (dupes, spec.identical_duplicates))
    if parts != spec.multipart_records:
        fail(spec, "%d records are further parts of a precinct already read, and the builder "
             "declares %d. Read the layer before changing the declaration"
             % (parts, spec.multipart_records))
    return feats, dupes


def per_county(feats):
    out = {}
    for f in feats:
        c = f["properties"]["countyFips"]
        out[c] = out.get(c, 0) + 1
    return dict(sorted(out.items()))


def fingerprint(feats):
    """A digest of what a re-precincting changes: every precinct's key, name
    and county and, where the layer publishes one, a measure of its shape (its
    area, or where it publishes no area its perimeter), rounded to a whole
    unit of the layer's own. Sorted, so record order cannot move it."""
    lines = []
    for f in feats:
        p = f["properties"]
        measure = p.get("_measure")
        lines.append("%s|%s|%s|%s" % (p["key"], p["name"], p["countyFips"],
                                      "" if measure is None else int(round(float(measure)))))
    lines.sort()
    return {"precincts": len(lines),
            "sha256": hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()}


def gate_counts(spec, feats, counties):
    problems = []
    if len(feats) != spec.expect:
        problems.append("%d precincts, expected %d. A re-precincting moves this number "
                        "legitimately: read the layer, then change EXPECT deliberately"
                        % (len(feats), spec.expect))
    seen = per_county(feats)
    missing = sorted(set(counties) - set(seen))
    if missing:
        problems.append("no precinct in %d counties: %s" % (
            len(missing), ", ".join(counties[c]["name"] for c in missing)))
    return problems


# ---------- simplify ----------
def simplify(spec, feats):
    src = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": f["geometry"],
         "properties": {k: v for k, v in f["properties"].items() if k != "_measure"}}
        for f in feats]}
    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, "src.geojson")
        out_path = os.path.join(tmp, "out.geojson")
        with open(src_path, "w", encoding="utf-8") as fh:
            json.dump(src, fh)
        subprocess.run(
            ["npx", "-y", MAPSHAPER, src_path,
             "-simplify", "dp", "keep-shapes", "interval=" + spec.interval,
             "-o", "precision=" + PRECISION, "format=geojson", out_path],
            check=True, cwd=spec.instance)
        with open(out_path, encoding="utf-8") as fh:
            drawn = json.load(fh)
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": f["properties"], "geometry": f["geometry"]}
        for f in drawn["features"]]}


# ---------- point lookup, the app's even-odd rule ----------
def _point_in_ring(pt, ring):
    x, y = pt
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def point_in_geometry(pt, geom):
    if not geom:
        return False
    if geom["type"] == "Polygon":
        inside = False
        for ring in geom["coordinates"]:
            if _point_in_ring(pt, ring):
                inside = not inside
        return inside
    if geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            inside = False
            for ring in poly:
                if _point_in_ring(pt, ring):
                    inside = not inside
            if inside:
                return True
    return False


def bbox(geom):
    b = [1e9, 1e9, -1e9, -1e9]

    def walk(c):
        if c and isinstance(c[0], (int, float)):
            b[0], b[1] = min(b[0], c[0]), min(b[1], c[1])
            b[2], b[3] = max(b[2], c[0]), max(b[3], c[1])
        else:
            for x in c:
                walk(x)

    walk(geom["coordinates"])
    return b


class Index(object):
    """A grid of feature bounding boxes, so a point is tested against the
    few precincts near it rather than all of them."""

    def __init__(self, feats):
        self.items = []
        self.cells = {}
        for f in feats:
            bb = bbox(f["geometry"])
            n = len(self.items)
            self.items.append((f["properties"]["key"], f["properties"]["countyFips"],
                               f["geometry"], bb))
            for gx in range(int(bb[0] // GRID), int(bb[2] // GRID) + 1):
                for gy in range(int(bb[1] // GRID), int(bb[3] // GRID) + 1):
                    self.cells.setdefault((gx, gy), []).append(n)

    def at(self, pt):
        hits = []
        for n in self.cells.get((int(pt[0] // GRID), int(pt[1] // GRID)), ()):
            key, county, geom, bb = self.items[n]
            if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3] and point_in_geometry(pt, geom):
                hits.append((key, county))
        return hits


def validate(spec, source_feats, drawn_feats, seed=2024):
    src, new = Index(source_feats), Index(drawn_feats)
    rng = random.Random(seed)
    bb = spec.state_bbox
    agree = overlaps = 0
    for _ in range(VALIDATE_SAMPLES):
        pt = (rng.uniform(bb["minLng"], bb["maxLng"]), rng.uniform(bb["minLat"], bb["maxLat"]))
        s_hits = [k for k, _ in new.at(pt)]
        if len(s_hits) > 1:
            overlaps += 1
        o_hits = [k for k, _ in src.at(pt)]
        o = o_hits[0] if len(o_hits) == 1 else (None if not o_hits else "MULTI")
        s = s_hits[0] if len(s_hits) == 1 else (None if not s_hits else "MULTI")
        agree += o == s
    pct = 100.0 * agree / VALIDATE_SAMPLES
    if overlaps:
        return False, "%d of %d points fell in more than one drawn precinct" % (
            overlaps, VALIDATE_SAMPLES)
    if pct < 99.5:
        return False, "the drawn file agrees with the source at only %.2f%% of points " \
                      "(need 99.5%%)" % pct
    return True, "%d/%d (%.2f%%) agreement over the state envelope, 0 overlaps" % (
        agree, VALIDATE_SAMPLES, pct)


def check_tiling(spec, feats, counties, seed=2026):
    """Points sampled inside each county, as the instance's own county file
    draws it, must land in one of that county's precincts. Returns
    (problems, report lines)."""
    index = Index(feats)
    rng = random.Random(seed)
    problems, rows = [], []
    multi = 0
    for geoid, c in sorted(counties.items()):
        geom = c["geometry"]
        bb = bbox(geom)
        same = other = none = n = tries = 0
        while n < spec.tiling_samples and tries < spec.tiling_samples * 60:
            tries += 1
            pt = (rng.uniform(bb[0], bb[2]), rng.uniform(bb[1], bb[3]))
            if not point_in_geometry(pt, geom):
                continue
            n += 1
            hits = index.at(pt)
            if len(hits) > 1:
                multi += 1
            if any(cf == geoid for _, cf in hits):
                same += 1
            elif hits:
                other += 1
            else:
                none += 1
        rows.append((same / float(n), c["name"], same, other, none, n))
        floor = spec.tiling_floor_by_county.get(geoid, spec.tiling_min_same)
        if same / float(n) < floor:
            problems.append("%s: only %d of %d points inside the county land in one of "
                            "its own precincts (%d in another county's, %d in none; floor %.2f)"
                            % (c["name"], same, n, other, none, floor))
        if other / float(n) > spec.tiling_max_other:
            problems.append("%s: %d of %d points inside the county land in another "
                            "county's precinct" % (c["name"], other, n))
    if multi:
        problems.append("%d county sample points fell in more than one precinct" % multi)
    for geoid in sorted(set(spec.tiling_floor_by_county) - set(counties)):
        problems.append("a tiling floor is declared for county %s, which is not in the "
                        "county file" % geoid)
    rows.sort()
    most_other = max(rows, key=lambda r: r[3])
    most_none = max(rows, key=lambda r: r[4])
    lines = [
        "tiling: lowest own-precinct share %.4f (%s: %d own, %d other, %d none of %d)"
        % rows[0],
        "tiling: most in another county's precinct: %s %d; most in none: %s %d"
        % (most_other[1], most_other[3], most_none[1], most_none[4]),
        "tiling: %d counties, %d points each; floor %.2f own, ceiling %.2f other"
        % (len(rows), spec.tiling_samples, spec.tiling_min_same, spec.tiling_max_other),
    ]
    if spec.tiling_floor_by_county:
        lines.append("tiling: declared floors %s" % ", ".join(
            "%s %.2f" % (counties[g]["name"] if g in counties else g, f)
            for g, f in sorted(spec.tiling_floor_by_county.items())))
    return problems, lines


# ---------- the record ----------
def write_record(spec, meta, feats, shipped_bytes, dupes):
    os.makedirs(os.path.dirname(spec.record_path), exist_ok=True)
    record = {
        "layer": spec.layer,
        "fetched": datetime.date.today().isoformat(),
        "layer_edited": meta.get("layer_edited"),
        "item": meta.get("item"),
        "identical_duplicates_dropped": dupes,
        "part_records_joined": spec.multipart_records,
        "fingerprint": fingerprint(feats),
        "precincts_per_county": per_county(feats),
        "shipped_sha256": hashlib.sha256(shipped_bytes).hexdigest(),
    }
    # A file source (ShapefileZip) also records the file it read, so --watch
    # can say whether the publisher replaced it in place.
    if meta.get("source_sha256"):
        record["source_sha256"] = meta["source_sha256"]
    with open(spec.record_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1, sort_keys=True)
        fh.write("\n")


def load_record(spec):
    with open(spec.record_path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------- the card ----------
def card_claims(spec):
    return ("drawn here to within %s metres" % spec.interval,) + spec.card_claims


def check_card(spec, what="precinct card"):
    """The sentences the precinct card must carry, looked for in the module
    that loads this builder's file: from the module comment above its loader
    to the next module's. Returns the problems found. `what` names the card
    in the messages, for the school board builders that share this."""
    path = os.path.join(spec.instance, "index.html")
    with open(path, encoding="utf-8") as fh:
        html = fh.read()
    ref = '"data/app/%s"' % spec.out_file
    if html.count(ref) != 1:
        return ["%s/index.html names %s %d times; the %s's loader names it once"
                % (spec.tag, ref, html.count(ref), what)]
    at = html.index(ref)
    start = html.rfind("/* ----------", 0, at)
    end = html.find("/* ----------", at)
    if start < 0 or end < 0:
        return ["%s/index.html: no module comment around the loader of %s" % (spec.tag, ref)]
    module = re.sub(r'"\s*\+\s*"', "", html[start:end])
    return ["the %s in %s/index.html does not say %r" % (what, spec.tag, claim)
            for claim in card_claims(spec) if claim not in module]


# ---------- the three modes ----------
def run_check(spec):
    counties = load_counties(spec)
    with open(spec.out_path, "rb") as fh:
        raw = fh.read()
    geo = json.loads(raw)
    record = load_record(spec)
    feats = geo.get("features") or []
    if spec.extra_check:
        spec.extra_check(feats)
    problems = gate_counts(spec, feats, counties)
    keys = [f["properties"].get("key") for f in feats]
    if len(set(keys)) != len(keys):
        problems.append("a precinct key appears twice in the shipped file")
    for f in feats:
        p = f["properties"]
        for key in spec.required + ("county",):
            if p.get(key) in (None, ""):
                problems.append("precinct %s has no %s" % (p.get("key"), key))
        if p.get("countyFips") in counties and p.get("county") != counties[p["countyFips"]]["name"]:
            problems.append("precinct %s names its county %r, the county file %r"
                            % (p.get("key"), p.get("county"), counties[p["countyFips"]]["name"]))
    if hashlib.sha256(raw).hexdigest() != record.get("shipped_sha256"):
        problems.append("the shipped file does not hash to what the builder recorded — "
                        "rebuild it rather than editing it by hand")
    if per_county(feats) != record.get("precincts_per_county"):
        problems.append("the shipped file's precincts per county differ from the record")
    tiling, lines = check_tiling(spec, feats, counties)
    problems += tiling
    problems += check_card(spec)
    for line in lines:
        print(line)
    if problems:
        for p in problems:
            print("%s --check: FAIL: %s" % (spec.label, p))
        raise SystemExit(1)
    print("%s --check: OK — %d precincts in %d counties, each county covered by its own, "
          "matching the record of %s; the card says %s"
          % (spec.label, len(feats), len(counties), record["fetched"],
             "; ".join(repr(c) for c in card_claims(spec))))


def run_watch(spec):
    counties = load_counties(spec)
    record = load_record(spec)
    records, meta = fetch(spec, geometry=False)
    feats, _ = normalise(spec, records, counties, with_geometry=False)
    if spec.extra_check:
        spec.extra_check(feats)
    live = fingerprint(feats)
    moved = live != record["fingerprint"]
    edit_moved = (meta.get("layer_edited") and record.get("layer_edited")
                  and meta["layer_edited"] != record["layer_edited"])
    if moved:
        before = record.get("precincts_per_county") or {}
        after = per_county(feats)
        changed = sorted(c for c in set(before) | set(after) if before.get(c) != after.get(c))
        print("%s --watch: THE LAYER HAS CHANGED since %s: %d precincts recorded, %d now "
              "(fingerprint %s -> %s). Counties whose count moved: %s. Rebuild the file, "
              "bump the service worker's cache name, and say which counties moved."
              % (spec.label, record["fetched"], record["fingerprint"]["precincts"],
                 live["precincts"], record["fingerprint"]["sha256"][:12], live["sha256"][:12],
                 ", ".join(counties[c]["name"] for c in changed if c in counties) or
                 "none (names or areas moved within a county)"))
        raise SystemExit(1)
    note = ""
    if edit_moved:
        note = (" The layer's own edit date moved (%s -> %s) without changing any "
                "precinct's key, name, county or area." % (record["layer_edited"],
                                                          meta["layer_edited"]))
    if (meta.get("source_sha256") and record.get("source_sha256")
            and meta["source_sha256"] != record["source_sha256"]):
        note += (" The file was replaced in place (SHA-256 %s -> %s) without changing any "
                 "precinct's key, name, county or measure; rebuild to ship its lines."
                 % (record["source_sha256"][:12], meta["source_sha256"][:12]))
    print("%s --watch: unchanged since %s (%d precincts).%s"
          % (spec.label, record["fetched"], live["precincts"], note))


def run_build(spec, source_path=None, save_source=None):
    counties = load_counties(spec)
    stale = check_card(spec)
    if stale:
        fail(spec, "; ".join(stale) + " — change the card before building, so the file "
             "and what the card says about it ship together")
    if source_path:
        with open(source_path, encoding="utf-8") as fh:
            saved = json.load(fh)
        records, meta = saved["records"], saved["meta"]
    else:
        records, meta = fetch(spec, geometry=True)
        if save_source:
            with open(save_source, "w", encoding="utf-8") as fh:
                json.dump({"records": records, "meta": meta}, fh)
    feats, dupes = normalise(spec, records, counties)
    if spec.extra_check:
        spec.extra_check(feats)
    problems = gate_counts(spec, feats, counties)
    if problems:
        for p in problems:
            print("%s: FAIL: %s" % (spec.label, p))
        raise SystemExit(1)

    drawn = simplify(spec, feats)
    problems = []
    if len(drawn["features"]) != len(feats):
        problems.append("%d precincts after simplifying, %d before — a whole precinct was "
                        "lost" % (len(drawn["features"]), len(feats)))
    ok, msg = validate(spec, feats, drawn["features"])
    if not ok:
        problems.append(msg)
    tiling, lines = check_tiling(spec, drawn["features"], counties)
    problems += tiling
    for line in lines:
        print(line)
    print("agreement: " + msg)
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
    # The fingerprint comes from the same fetch the geometry did, so the record
    # cannot describe a different version of the layer.
    write_record(spec, meta, feats, data, dupes)
    print("wrote %s: %d precincts in %d counties, %d bytes (dp interval=%s m, 6dp)%s"
          % (os.path.relpath(spec.out_path, REPO_ROOT), len(drawn["features"]),
             len(per_county(feats)), len(data), spec.interval,
             ("; %d identical duplicate record(s) dropped" % dupes) if dupes else ""))


def main(spec, doc):
    ap = argparse.ArgumentParser(description=(doc or "").strip().split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped file to its record and the county file")
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
