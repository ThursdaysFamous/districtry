// The points, instances and vendor paths the fleet's browser probes share.
// scripts/probe_point_transmission.mjs and scripts/probe_layer_sources.mjs both
// select points inside each instance's coverage and both have to reach the
// coverage-gated layers; one list keeps them asking the same question.

import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));

// The point to select. Each instance's own worksheet anchor is used because it
// is chosen to be INSIDE that instance's coverage — a point outside it would
// suppress coverage-gated layers, which would then read as "does not send".
export function anchorOf(tag, problem) {
  const rel = tag === "il" ? "metro-worksheet.json" : join(tag, "metro-worksheet.json");
  const w = JSON.parse(readFileSync(join(ROOT, rel), "utf8"));
  const a = w.anchor_point;
  if (!a || typeof a.lat !== "number" || typeof a.lng !== "number")
    problem(`${tag}: no usable anchor_point in its worksheet`);
  return a || { lat: 0, lng: 0 };
}

// EXTRA POINTS, because coverage gating is real. A layer that declares
// `coverage(point)` is not queried outside it, and a probe that selects one
// point would report "does not send" for a layer it never asked. Illinois's
// elementary and high-school district layers declare
// `outsideChicagoSchoolCoverage` and are hidden inside the city, which is
// exactly where the worksheet anchor is — so the anchor alone leaves both
// unexercised. Evanston is an elementary + high-school PAIR (District 65 and
// Township 202) rather than unified territory, so it exercises both.
//
// Anything still unexercised after every point here is REPORTED, never counted
// as a no: this list is a way to reduce the unknowns, not to hide them.
export const EXTRA_POINTS = {
  il: [{ lat: 42.0451, lng: -87.6877, note: "Evanston — elementary D65 + high-school D202, outside Chicago" }],
  // NEW YORK'S EXTRA POINT INVERTED AT THE 2026-09-19 GO-LIVE, and the reason is
  // worth keeping because it is the same trap read from the other side. It used
  // to be Buffalo: the worksheet anchor was City Hall, so the STATEWIDE layers
  // (`nys-zip-code`, `nys-school-district`, which declare `outsideNycCoverage`)
  // were the ones hidden at the anchor. Go-live moved the anchor upstate to
  // Albany to ground-truth the statewide tier — which hid the CITY tier
  // instead, and the probe promptly reported eight city layers UNEXERCISED and
  // New York sending on one layer rather than five.
  //
  // So the extra point is now City Hall, the same literal ny/scripts/
  // smoke_test.mjs keeps as NYC_POINT for the same reason. A coverage-gated
  // fleet needs one point per BAND, and which band the anchor sits in decides
  // which one the extra point has to cover — not the other way round.
  ny: [{ lat: 40.71274, lng: -74.00602, note: "New York City Hall — the city tier, hidden at the upstate anchor" }],
};

// An instance is a top-level directory with its own index.html and data/app —
// the same rule validate_card_links.py and validate_instance_registration.py
// discover by, so a seventh state is measured the day it lands with nothing
// here to edit. Illinois keeps its scripts at the repo root (the R2.3
// asymmetry), which is the only reason this needs a branch at all.
export function instances() {
  return readdirSync(ROOT)
    .filter((d) => {
      try {
        return statSync(join(ROOT, d)).isDirectory() &&
          existsSync(join(ROOT, d, "index.html")) &&
          existsSync(join(ROOT, d, "data", "app"));
      } catch { return false; }
    })
    .sort();
}

export function vendorDir(tag) {
  // The SessionStart hook vendors Leaflet per instance for sandboxes whose
  // Chromium cannot reach cdnjs; absent (production, GitHub Actions) the
  // browser loads it from the CDN exactly as a reader's would.
  return tag === "il"
    ? join(ROOT, "scripts", "vendor", "leaflet")
    : join(ROOT, tag, "scripts", "vendor", "leaflet");
}
