#!/usr/bin/env python3
"""Derive the dark-theme map palette from the app's own layer colours.

WHY THIS IS GENERATED. Dark mode (R4.2) needs a dark counterpart for every
layer stroke and fill in the app — ~59 colours. Those counterparts are NOT
hand-picked: they are an order-preserving remap of the light palette, and the
reasoning for that is recorded in full below because it is the whole reason
this file exists rather than a table someone eyeballed.

The table therefore has a SOURCE, and a table with a source must not be a
second copy of it. The re-skin preview computed this at build time and inlined
the result; adopting that as a static literal would have been fine on the day
and wrong on the day someone changes a layer colour, because the dark
counterpart would keep the old hue with nothing to say so. So the derivation
ships as a generator over a GENERATED region, with a --check that fails when
the app's colours and the emitted table disagree — the same contract as every
other generated region in this repo.

    python3 scripts/build_dark_map_palette.py            # write the region
    python3 scripts/build_dark_map_palette.py --check    # drift gate

Stdlib only.
"""

import argparse
import difflib
import json
import math
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# EVERY INSTANCE THAT CARRIES THE REGION, not just Chicago. This script pointed
# at il/index.html alone for as long as Chicago was the only app with dark mode.
# When NYC and SF adopted the skin they gained the same GENERATED region and the
# same need for a derived table — and a builder hardcoded to one instance would
# have left both regions EMPTY while its own --check went on passing, because it
# was only ever looking at the one file it knew about. That is the same shape as
# the two half-blind gates found on 2026-08-24: a check that quietly excludes its
# newest subjects reports OK.
#
# The set is discovered rather than listed: an instance is a target when its
# index.html actually carries the fences, so an app WITHOUT dark mode is skipped
# instead of failing, and an app that adopts it is picked up with nothing here to
# edit.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from generate_metro_files import INSTANCES
except ImportError:  # pragma: no cover
    INSTANCES = {"il": {"app": "il"}}


def targets():
    out = []
    for tag in sorted(INSTANCES):
        rel = os.path.join(INSTANCES[tag]["app"], "index.html")
        path = os.path.join(REPO_ROOT, rel)
        try:
            with open(path, encoding="utf-8", newline="") as f:
                text = f.read()
        except OSError:
            continue
        if ("GENERATED:BEGIN %s" % REGION) in text:
            out.append((rel, path, text))
    if not out:
        fail("no instance carries a GENERATED:%s region — add the fences first" % REGION)
    return out
REGION = "dark-map-palette"


def fail(msg):
    print("build-dark-map-palette: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


# The dark map palette, DERIVED rather than hand-picked.
#
# The layer palette is ~59 literals chosen against a light basemap, and it does
# not transfer: measured against CARTO dark_all's ground (#1a1a1a, which the
# app's own tile filter lifts to about #232323), 28 of 37 stroke colours fall
# below the 3:1 that WCAG 1.4.11 asks of a non-text boundary, and four —
# #14181C, #06375E, #7A0A1C, #7A0B1E — sit under 1.5:1, which is to say gone.
#
# The obvious fix is the wrong one. Lifting each colour by the MINIMUM needed to
# clear 3:1 collapses the palette, because in the light set a great deal of the
# categorical separation IS lightness: measured, 314 of 703 pairs move closer
# and 66 land inside dE 0.05 of each other (U.S. House and County both become
# the same grey; City Ward and County Board District the same blue). Hue was
# preserved and the encoding still broke.
#
# So the transform is an ORDER-PRESERVING remap instead: one monotonic affine
# map on OKLCH lightness across the whole palette, hue untouched, chroma lifted
# 1.25x to buy back the separation that compressing lightness costs. Monotonic
# means every within-layer relationship survives by construction — a stroke
# darker than its fill stays darker than its fill.
#
# The bar it is held to is not "looks nice" but a measurement against the light
# palette's own record: the light set has 25 pairs inside dE 0.05 and a p5 dE of
# 0.056; this dark set has 24 and 0.052. It is no more collision-prone than the
# palette it derives from, and every stroke clears 3.10:1.
DARK_L_LO, DARK_L_HI, DARK_CHROMA = 0.54, 0.92, 1.25


def _srgb_to_lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _lin_to_srgb(c):
    c = max(0.0, min(1.0, c))
    v = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
    return int(round(max(0.0, min(1.0, v)) * 255))


def _to_oklab(hexs):
    r, g, b = [_srgb_to_lin(int(hexs[i:i + 2], 16)) for i in (1, 3, 5)]
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s_ = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s_ = [x ** (1 / 3) if x > 0 else 0.0 for x in (l, m, s_)]
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s_,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s_,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s_)


def _from_oklab(L, a, b):
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
            -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
            -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)


def _in_gamut(L, a, b):
    return all(-0.0005 <= c <= 1.0005 for c in _from_oklab(L, a, b))


def _hex(L, a, b):
    r, g, bl = _from_oklab(L, a, b)
    return "#%02X%02X%02X" % (_lin_to_srgb(r), _lin_to_srgb(g), _lin_to_srgb(bl))


def _oklch(hexs):
    L, a, b = _to_oklab(hexs)
    return L, math.hypot(a, b), math.atan2(b, a)


def _lch_to_lab(L, C, H):
    return L, C * math.cos(H), C * math.sin(H)


def layer_colours(index_html):
    """Every layer stroke/fill literal in one app's index.html."""
    strokes = re.findall(r'\bcolor:\s*"(#[0-9A-Fa-f]{6})"', index_html)
    fills = re.findall(r'fillColor:\s*"(#[0-9A-Fa-f]{6})"', index_html)
    palette = sorted({c.upper() for c in strokes + fills})
    if not palette:
        fail("found no layer colours to derive a dark palette from — did the\n             color:/fillColor: literal style change?")
    return palette


# ONE LIGHTNESS RANGE FOR THE WHOLE FLEET (2026-10-13). The remap stretches
# lightness between the darkest and the lightest colour it is given, and until
# the layer colours were unified across the apps (layer-concepts.json
# `colors`) each app passed only its own: measured that day, the lightest
# literal was #41B6E6 in eight apps and #7CC49B, #6FBF7F or #7FC4A3 in the
# other five, so one light colour could have two dark ones, and a layer drawn
# alike in every app in daylight would not have been at night. The range is now taken over every app's colours at
# once, so the same light colour maps to the same dark colour everywhere. The
# darkest colour still maps to DARK_L_LO, so the contrast floor recorded
# above does not move.
def fleet_bounds(texts):
    ls = [_oklch(c)[0] for t in texts for c in layer_colours(t)]
    return min(ls), max(ls)


def dark_twin(colour, bounds):
    """One light colour -> its dark counterpart, remapped over `bounds`.

    Split out so the front page's question tiles (build_landing_page.py), which
    show each question in its concept's map colour, take the same dark colour
    the apps draw that concept in rather than a second derivation of it."""
    lo, hi = bounds
    span = (hi - lo) or 1.0
    L, C, H = _oklch(colour)
    Ln = DARK_L_LO + (L - lo) * (DARK_L_HI - DARK_L_LO) / span
    Cn = C * DARK_CHROMA
    while Cn > 0 and not _in_gamut(*_lch_to_lab(Ln, Cn, H)):
        Cn -= 0.004
    return _hex(*_lch_to_lab(Ln, Cn, H))


def dark_map_palette(index_html, bounds=None):
    """Every layer stroke/fill literal in index.html -> its dark counterpart,
    remapped over `bounds` (the fleet's lightness range) when given."""
    palette = layer_colours(index_html)
    if bounds is None:
        ls = [_oklch(c)[0] for c in palette]
        bounds = (min(ls), max(ls))
    return {c: dark_twin(c, bounds) for c in palette}

def render(index_html, bounds=None):
    """The region body: one JS object literal, sorted, wrapped to stay readable."""
    table = dark_map_palette(index_html, bounds)
    pairs = ['"%s": "%s"' % (k, v) for k, v in sorted(table.items())]
    lines, cur = [], "  var DST_DARK_MAP_COLORS = {"
    for i, pair in enumerate(pairs):
        piece = pair + ("," if i < len(pairs) - 1 else "")
        if len(cur) + 1 + len(piece) > 96:
            lines.append(cur)
            cur = "    " + piece
        else:
            cur += (" " if cur.endswith("{") else " ") + piece
    lines.append(cur + "};")
    return "\n".join(lines), len(table)


def split_region(text):
    begin = "  /* ==== GENERATED:BEGIN %s ==== */" % REGION
    end = "  /* ==== GENERATED:END %s ==== */" % REGION
    if text.count(begin) != 1 or text.count(end) != 1:
        fail("no single GENERATED:%s region — add the fences first" % REGION)
    i = text.index(begin) + len(begin)
    j = text.index(end)
    return text[:i], text[i:j], text[j:]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="verify the emitted table matches the app's colours; exit 1 on drift")
    args = ap.parse_args()

    totals = []
    apps = targets()
    bounds = fleet_bounds([text for _, _, text in apps])
    for rel, path, text in apps:
        head, current, tail = split_region(text)
        body, n = render(text, bounds)
        rendered = "\n" + body + "\n"
        totals.append((rel, n))

        if args.check:
            if current != rendered:
                for dl in list(difflib.unified_diff(
                        current.splitlines(), rendered.splitlines(),
                        fromfile="committed " + rel, tofile="derived",
                        lineterm="", n=1))[:24]:
                    print("  " + dl, file=sys.stderr)
                fail("%s: the dark map palette has drifted from that app's layer "
                     "colours. A layer colour changed and its dark counterpart did "
                     "not; re-run scripts/build_dark_map_palette.py." % rel)
            continue

        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(head + rendered + tail)
        print("build-dark-map-palette: %s — wrote %d derived dark colour(s)" % (rel, n))

    summary = ", ".join("%s %d" % (rel.split("/")[0], n) for rel, n in totals)
    if args.check:
        print("build-dark-map-palette: OK — layer colours match their derived dark "
              "counterparts in %d instance(s): %s" % (len(totals), summary))


if __name__ == "__main__":
    main()
