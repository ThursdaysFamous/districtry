// Fixture tests for the engine's Esri-ring nesting, run OFFLINE.
//
// WHY THIS EXISTS. `esriRingsToParts` decides, for every ArcGIS polygon the
// fleet fetches, which rings are holes and which shell owns each one. Getting
// it wrong claims ground a publisher cut out — the defect measured on
// 2026-09-05 at 41 of 156 live layers, 1,376 rings, 298.2 km². Until now its
// only coverage was those live services: the smoke tests stub every ArcGIS
// response they touch, so the polygon path ran in CI only when a county server
// answered, and the branches that matter most — an orphaned counter-clockwise
// ring, a degenerate ring, a zero-area shell — are ones no county happens to
// publish today. This asserts them directly.
//
// The function is LIFTED FROM THE SHIPPED APP rather than copied here, for the
// same reason scripts/probe_arcgis_ring_nesting.mjs lifts it: a second copy is
// a copy that drifts, and what this needs to test is what readers actually run.
//
//     node scripts/esri_rings_test.mjs
//
// No network, no browser: it is a plain node script and belongs in CI beside
// the other static gates.

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const TAG = process.env.INSTANCE || "il";

function lift(tag) {
  const src = readFileSync(join(ROOT, tag, "index.html"), "utf8");
  const grab = (name) => {
    const m = src.match(new RegExp("\\n  function " + name + "\\([\\s\\S]*?\\n  \\}\\n"));
    if (!m) throw new Error(`${tag}/index.html no longer defines ${name}`);
    return m[0];
  };
  const body = grab("esriSignedRingArea") + grab("esriRingsToParts") + grab("pointInRing") +
    grab("esriGeometryToGeoJSON") + grab("esriToGeoJSON") +
    "\nreturn { esriRingsToParts, esriGeometryToGeoJSON, esriToGeoJSON };";
  // eslint-disable-next-line no-new-func
  return new Function(body)();
}

const { esriRingsToParts, esriGeometryToGeoJSON, esriToGeoJSON } = lift(TAG);

// Esri winding: a CLOCKWISE ring is a shell, COUNTER-CLOCKWISE is a hole.
// In screen/lng-lat order that makes a shell's signed area NEGATIVE.
const cw = (x, y, s) => [[x, y], [x, y + s], [x + s, y + s], [x + s, y], [x, y]];
const ccw = (x, y, s) => cw(x, y, s).slice().reverse();

let failures = 0;
function check(name, got, want) {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) failures++;
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${name}` +
              (ok ? "" : `\n          got  ${JSON.stringify(got)}\n          want ${JSON.stringify(want)}`));
}
const shape = (parts) => parts.map((p) => p.length);   // rings per part

console.log(`esri-rings-test (${TAG}/index.html)`);

// 1. A HOLE IS NESTED INTO THE SHELL THAT CONTAINS IT — the whole point.
check("hole nests into its shell",
  shape(esriRingsToParts([cw(0, 0, 10), ccw(2, 2, 4)])), [2]);

// 2. TWO SEPARATE SHELLS STAY TWO PARTS, and a hole goes to the right one.
check("two shells, hole to the containing one",
  shape(esriRingsToParts([cw(0, 0, 10), cw(20, 0, 10), ccw(21, 1, 4)])), [1, 2]);

// 3. THE SMALLEST CONTAINING SHELL OWNS THE HOLE — nested shells are legal
//    (a district inside a district's cutout) and the inner one must win.
check("smallest containing shell owns the hole",
  shape(esriRingsToParts([cw(0, 0, 40), cw(5, 5, 20), ccw(10, 10, 4)])), [1, 2]);

// 4. AN ORPHANED COUNTER-CLOCKWISE RING BECOMES ITS OWN SHELL, never dropped:
//    dropping it would LOSE ground the service publishes.
check("orphan CCW ring becomes its own part",
  shape(esriRingsToParts([cw(0, 0, 10), ccw(50, 50, 4)])), [1, 1]);

// 5. ALL RINGS COUNTER-CLOCKWISE means the winding signal is absent on that
//    service; treat them all as shells rather than inventing holes.
check("no clockwise ring at all: every ring is a shell",
  shape(esriRingsToParts([ccw(0, 0, 10), ccw(20, 0, 10)])), [1, 1]);

// 6. A DEGENERATE RING (fewer than 4 positions cannot close) is kept as its own
//    part rather than silently discarded.
check("degenerate ring is kept as a part",
  shape(esriRingsToParts([cw(0, 0, 10), [[2, 2], [3, 2], [2, 2]]])), [1, 1]);

// 7. A COLLAPSED RING IS NEVER A SHELL. Its signed area is exactly 0, which is
//    not < 0, so the winding split sends it to the holes — where, contained by
//    the real shell, it nests. Asserted because the first draft of this file
//    expected the opposite and the CODE was right: an even-odd test against a
//    zero-area ring is unreliable, so it must never be on the owning side of
//    one (Wisconsin measured such a sliver "containing" a hole it could not,
//    Marathon County, 2026-09-05).
check("collapsed ring is never a shell",
  shape(esriRingsToParts([cw(0, 0, 10), [[3, 3], [5, 3], [3, 3], [3, 3]]])), [2]);

// 7b. AND A SHELL NO LARGER THAN THE HOLE CANNOT OWN IT. This is the guard the
//    Marathon sliver actually needed: "smallest containing shell" alone would
//    hand this hole to the equal-sized shell sitting exactly on top of it, and
//    the hole would never be subtracted from the district that really has it.
check("shell no larger than the hole cannot own it",
  shape(esriRingsToParts([cw(0, 0, 10), cw(2, 2, 4), ccw(2, 2, 4)])), [2, 1]);

// 8. GEOMETRY SHAPES. One part is a Polygon, more than one a MultiPolygon;
//    points and lines pass through; a shapeless row is null, exactly as
//    ArcGIS's own GeoJSON export emits it.
check("one part -> Polygon", esriGeometryToGeoJSON({ rings: [cw(0, 0, 10)] }).type, "Polygon");
check("two parts -> MultiPolygon",
  esriGeometryToGeoJSON({ rings: [cw(0, 0, 10), cw(20, 0, 10)] }).type, "MultiPolygon");
check("point passes through", esriGeometryToGeoJSON({ x: 1, y: 2 }), { type: "Point", coordinates: [1, 2] });
check("single path -> LineString", esriGeometryToGeoJSON({ paths: [[[0, 0], [1, 1]]] }).type, "LineString");
check("two paths -> MultiLineString",
  esriGeometryToGeoJSON({ paths: [[[0, 0], [1, 1]], [[2, 2], [3, 3]]] }).type, "MultiLineString");
check("no geometry -> null", esriGeometryToGeoJSON(null), null);

// 9. THE ENVELOPE. Attributes become properties, every one of them when no
//    field list is given, and the transfer-cap flag is carried through —
//    loadArcGISPaged pages on it, so losing it truncates a layer silently.
const fc = esriToGeoJSON({
  exceededTransferLimit: true,
  features: [{ attributes: { A: 1, B: "x" }, geometry: { rings: [cw(0, 0, 10)] } },
             { attributes: { A: 2, B: "y" }, geometry: null }],
});
check("attributes become properties", fc.features[0].properties, { A: 1, B: "x" });
check("field list narrows the properties",
  esriToGeoJSON({ features: [{ attributes: { A: 1, B: "x" } }] }, ["A"]).features[0].properties, { A: 1 });
check("shapeless row is kept with null geometry", fc.features[1].geometry, null);
check("exceededTransferLimit carries through", fc.exceededTransferLimit, true);

if (failures) {
  console.error(`\n${failures} esri-ring check(s) failed`);
  process.exit(1);
}
console.log("\nAll esri-ring checks passed.");
