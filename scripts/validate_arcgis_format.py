#!/usr/bin/env python3
"""No shipped app may ask an ArcGIS service for `f=geojson`.

WHY. ArcGIS's GeoJSON export is lossy in two directions and both silently claim
ground a publisher cut out. It can UNNEST a feature's interior rings, returning
holes as separate shells, so `pointInGeometry`'s per-part even-odd test puts a
click inside the cutout inside the district; and on at least one org it
FLATTENS a multipart polygon into a single ring list, so a part inside another
part becomes a false hole. Esri JSON carries the structure in ring WINDING and
loses neither. Measured 2026-09-05 across every ArcGIS layer the six shipped
apps fetch: 41 of 156 polygon layers lost 1,376 interior rings, 1,135 hole
points got a card naming a district that does not cover them, and 298.2 km2 was
claimed. docs/DATA_LAYER_GUIDEBOOK.md carries the table.

Every loader now asks for `f=json` and nests the rings itself, and
`fetchArcGISAsGeoJSON` REFUSES a url that does not — but that refusal happens at
fetch time, on a layer a reader has to reach before anyone learns of it. Several
of the affected layers serve one county each, and the app's per-layer failure
isolation renders a broken fetch as its honest "data source didn't respond"
card, which is exactly the state Kane's park and library districts sat in
unnoticed. So the check is STATIC: a url asking for the lossy format fails the
merge rather than a reader's click.

Prose is not a url. The token is only a finding INSIDE A QUOTED STRING —
this file's own docstring, and every comment in every instance explaining the
defect, say `f=geojson` freely and must keep being able to.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = "f=geojson"


def string_hits(src):
    """Every (line, literal) where TOKEN appears inside a JS string literal.

    A hand-rolled scanner rather than a regex, because the token has to be
    findable in PROSE: this file, and every comment in every instance that
    explains the defect, quote `f=geojson` — one of them inside double quotes
    ("produce what f=geojson should have produced"), which a
    quoted-span regex reports as six urls that do not exist. Comments are
    therefore skipped properly rather than by a line-prefix guess.

    Its one accepted limit, stated rather than papered over: a `/` that begins
    a REGEX LITERAL is read as a possible comment start, so a regex containing
    an unbalanced quote could desynchronise the scan. The apps' regexes are
    simple and none contains one; if that ever changes, this gate goes noisy
    rather than quiet, which is the failure direction to prefer.
    """
    hits = []
    i, n, line = 0, len(src), 1
    while i < n:
        c = src[i]
        if c == "\n":
            line += 1
            i += 1
        elif c == "/" and i + 1 < n and src[i + 1] == "/":
            while i < n and src[i] != "\n":
                i += 1
        elif c == "/" and i + 1 < n and src[i + 1] == "*":
            i += 2
            while i + 1 < n and not (src[i] == "*" and src[i + 1] == "/"):
                if src[i] == "\n":
                    line += 1
                i += 1
            i += 2
        elif c in "\"'`":
            quote, start, start_line = c, i, line
            i += 1
            while i < n:
                if src[i] == "\\":
                    i += 2
                    continue
                if src[i] == "\n":
                    line += 1
                    if quote != "`":
                        break            # an unterminated ordinary string
                if src[i] == quote:
                    i += 1
                    break
                i += 1
            lit = src[start:i]
            if TOKEN in lit:
                hits.append((start_line, lit))
        else:
            i += 1
    return hits


def instances():
    """A top-level directory with its own index.html and data/app — the rule
    validate_card_links.py and validate_instance_registration.py discover by, so
    a seventh state is checked the day it lands with nothing here to edit."""
    out = []
    for name in sorted(os.listdir(REPO_ROOT)):
        d = os.path.join(REPO_ROOT, name)
        if (os.path.isdir(d) and os.path.exists(os.path.join(d, "index.html"))
                and os.path.isdir(os.path.join(d, "data", "app"))):
            out.append(name)
    return out


def main():
    tags = instances()
    if len(tags) < 2:
        print("validate-arcgis-format: FAIL — found %d instance(s); the tree "
              "layout has changed and this gate would pass vacuously" % len(tags))
        return 1
    problems, checked = [], 0
    for tag in tags:
        path = os.path.join(REPO_ROOT, tag, "index.html")
        src = open(path, encoding="utf-8").read()
        checked += 1
        for line, lit in string_hits(src):
            problems.append("%s/index.html:%d asks for f=geojson: %s"
                            % (tag, line, lit[:80]))
    if problems:
        print("validate-arcgis-format: FAIL — %d url(s) request the lossy "
              "GeoJSON export (use f=json + fetchArcGISAsGeoJSON):" % len(problems))
        for p in problems:
            print("  " + p)
        return 1
    print("validate-arcgis-format: OK — %d instance(s), no url asks an ArcGIS "
          "service for f=geojson" % checked)
    return 0


if __name__ == "__main__":
    sys.exit(main())
