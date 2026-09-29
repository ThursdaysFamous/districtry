#!/usr/bin/env python3
"""Emit each instance's PWA manifest from its worksheet's brand block.

WHY THIS EXISTS. Every branded surface in this repo is generated from
`brand` in the instance worksheet — the head block, the favicon, the theme
colour, the analytics tag. The web app manifest was the one that was not, and
it is the one that rotted: after the rebrand shipped, `il/manifest.webmanifest`
still read `"Chicago District Explorer"` with the pre-rebrand navy
`#0b3d91` and the old Chicago-flag star icons, so **installing the app to an
Android home screen produced the old name and the old icon** while every
other surface said districtry. NY and SF were the same story with their own
old names. No gate could catch it, because nothing compared the manifest to
anything.

So the manifest is generated now, and `--check` fails the build on drift.

WHAT IS PRESERVED, DELIBERATELY. The icon *paths* are read out of the manifest
being replaced rather than invented, because `sw.shell_urls` in the worksheet
pins those exact filenames: NY keeps `icons/app/…`, IL and SF keep `icons/…`.
Renaming an icon here would silently break the service worker's precache,
which is a worse bug than the one this fixes. Replace the PNG bytes in place;
never rename the file.

A NOTE ON `start_url`. It is `./`, not `./index.html`. The two resolve to the
same document, and the service worker precaches only `./` for exactly that
reason — pointing the manifest at `./index.html` makes an installed app open a
URL the shell cache does not hold, so the first launch of an offline install
misses.

Usage:
    python3 scripts/build_manifests.py            # write
    python3 scripts/build_manifests.py --check    # drift gate; exit 1 on diff
"""

import argparse
import difflib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (instance dir, worksheet path relative to repo root). IL's worksheet is the
# repo-root one — the same asymmetry generate_metro_files.py carries.
INSTANCES = [
    ("il", "metro-worksheet.json"),
    ("ny", "ny/metro-worksheet.json"),
    ("ca", "ca/metro-worksheet.json"),
    ("wi", "wi/metro-worksheet.json"),
    ("ia", "ia/metro-worksheet.json"),
    ("mi", "mi/metro-worksheet.json"),
    ("mn", "mn/metro-worksheet.json"),
    ("nc", "nc/metro-worksheet.json"),
]

# The splash background. Not the theme colour: the brand icons sit on a light
# field, and a violet splash behind a light-field icon reads as a mistake on a
# phone. This is the app's own paper tone.
BACKGROUND = "#F4F7F9"


def fail(msg):
    print("build-manifests: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def short_name(app_name, product):
    """The label under the icon on a home screen — roughly 12 characters before
    Android truncates it. `app_name` is "districtry Illinois"; the product name
    alone is what fits and what the brand spec calls the indivisible word."""
    return product or app_name.split()[0]


def icon_paths(existing):
    """Icon srcs from the manifest being replaced — see the module docstring on
    why these are preserved rather than chosen."""
    srcs = [i.get("src") for i in (existing.get("icons") or []) if i.get("src")]
    small = next((s for s in srcs if "192" in s), None)
    large = next((s for s in srcs if "512" in s and "maskable" not in s), None)
    if not small or not large:
        return None
    # The maskable file sits beside the others; its name is fixed by this script
    # because it is new, and it is added to sw.shell_urls in the same change.
    maskable = large.replace("icon-512", "icon-maskable-512")
    return small, large, maskable


def build(inst, worksheet_path):
    wpath = os.path.join(REPO, worksheet_path)
    with open(wpath, encoding="utf-8") as fh:
        w = json.load(fh)
    brand = w.get("brand") or {}
    if not brand.get("app_name"):
        fail("%s: worksheet has no brand.app_name — the manifest cannot be "
             "generated without it (adopt the brand keys first)" % worksheet_path)

    mpath = os.path.join(REPO, inst, "manifest.webmanifest")
    if not os.path.exists(mpath):
        fail("%s: no manifest to replace at %s" % (inst, mpath))
    with open(mpath, encoding="utf-8") as fh:
        existing = json.load(fh)

    paths = icon_paths(existing)
    if not paths:
        fail("%s: could not read 192 and 512 icon paths out of the existing "
             "manifest; refusing to guess filenames the service worker pins" % inst)
    small, large, maskable = paths

    for rel in (small, large, maskable):
        if not os.path.exists(os.path.join(REPO, inst, rel)):
            fail("%s: manifest would name %s, which does not exist on disk" % (inst, rel))

    doc = {
        "name": brand["app_name"],
        "short_name": short_name(brand["app_name"], brand.get("product_name")),
        "description": (brand.get("head") or {}).get("description") or brand.get("tagline") or "",
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
        "background_color": BACKGROUND,
        "theme_color": brand.get("theme_color") or BACKGROUND,
        "icons": [
            {"src": small, "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": large, "sizes": "512x512", "type": "image/png", "purpose": "any"},
            # Without a maskable icon Android crops the square into its adaptive
            # shape and letterboxes it on a white plate. This one carries the
            # safe-zone padding the spec asks for.
            {"src": maskable, "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    return mpath, json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="fail if any manifest differs from what the worksheets describe")
    args = ap.parse_args()

    drift = []
    for inst, wpath in INSTANCES:
        mpath, want = build(inst, wpath)
        have = open(mpath, encoding="utf-8").read() if os.path.exists(mpath) else ""
        if args.check:
            if have != want:
                drift.append((inst, have, want))
        elif have != want:
            with open(mpath, "w", encoding="utf-8") as fh:
                fh.write(want)
            print("build-manifests: wrote %s/manifest.webmanifest" % inst)
        else:
            print("build-manifests: %s/manifest.webmanifest already current" % inst)

    if args.check:
        if drift:
            for inst, have, want in drift:
                print("\n--- %s/manifest.webmanifest (on disk) vs worksheet ---" % inst)
                sys.stdout.writelines(difflib.unified_diff(
                    have.splitlines(keepends=True), want.splitlines(keepends=True),
                    fromfile="on disk", tofile="from worksheet"))
            fail("%d manifest(s) drifted from the brand keys. Regenerate rather "
                 "than hand-editing: a manifest that disagrees with the app is "
                 "what puts the wrong name on someone's home screen."
                 % len(drift))
        print("build-manifests: OK — all %d manifest(s) match their worksheets"
              % len(INSTANCES))


if __name__ == "__main__":
    main()
