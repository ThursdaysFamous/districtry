#!/usr/bin/env python3
"""Self-host the app's Google Fonts into fonts/ and emit the @font-face CSS.

Why this exists: the fonts used to load from fonts.googleapis.com (+ the woff2
from fonts.gstatic.com). Even loaded non-render-blocking (R2-1), that's two
third-party origins the page must preconnect — and a production PageSpeed run
(2026-07-16) showed the LCP is a basemap tile that wants those preconnect slots
for the CARTO tile shards, plus a small CLS from the cross-origin font swap
landing late. Self-hosting fixes both: it drops the two font preconnects (freeing
them for the tile shards) and, served same-origin + service-worker-precached,
the font arrives early enough that the swap barely shifts layout.

This fetches Google's own per-subset woff2 (latin + latin-ext — civic officeholder
names need the latin-ext accents), dedupes by URL (Big Shoulders Display and Inter
are variable fonts, one file per subset shared across weights), writes them to
fonts/, and prints the @font-face CSS to stdout. Paste that block into index.html's
<style> (just after the inlined Leaflet CSS), between the SELF-HOSTED FONTS markers
— same "inline third-party CSS with a regenerate comment" pattern as the Leaflet
block. Re-run on any family/weight change and re-paste.

Like build_embedded_boundaries.py / build_legislative_boundaries.py this is an
occasional OPERATOR step, not weekly CI. Prerequisite: curl (through the proxy).

Usage:
    python3 scripts/build_fonts.py            # -> il/fonts/*.woff2 + @font-face on stdout
    python3 scripts/build_fonts.py landing > fonts/barlow-fontface.css
    python3 scripts/build_fonts.py traffic   # -> fonts/ibm-plex-mono-400-*.woff2,
                                             #    block pasted into traffic.html
"""

import argparse
import os
import re
import subprocess
import sys
from collections import defaultdict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# WHICH PAGE'S FONTS, and where they land. This used to be two module constants
# aimed at the repo root, which was right while the Illinois app WAS the repo
# root and silently wrong from the moment R2.3 moved it to il/: the script would
# have fetched into a top-level fonts/ that nothing reads, leaving il/fonts/
# untouched. Nothing caught it because this is an occasional operator step, not
# CI — the same shape as vendor_leaflet.sh reading the redirect stub.
#
# Each target names its own families and its own output directory, and every
# consuming page sits exactly one level above its fonts dir, so the CSS `src:`
# prefix stays "fonts/" for all of them.
#
#   il        the Illinois app (il/index.html's --font-display/-body/-mono)
#   landing   the fleet landing page at the repo root — districtry's wordmark
#             and body type (districtry/tokens/districtry.tokens.css:
#             --font-heading Barlow Condensed 600, --font-body Barlow)
#
# ca/ and ny/ keep their own copies of this script, which self-locate into
# their own trees correctly and are NOT redundant with this one.
TARGETS = {
    "il": {
        "fonts_dir": "il/fonts",
        # Barlow Condensed (display) + Barlow (body) replaced Big Shoulders
        # Display + Inter when the app adopted the districtry skin (R4.2). The
        # MONO is unchanged and deliberately so: it sets coordinates and ids,
        # where IBM Plex Mono's disambiguated zero is doing real work.
        "families": ("?family=Barlow+Condensed:wght@400;600;700"
                     "&family=Barlow:wght@400;500;600;700"
                     "&family=IBM+Plex+Mono:wght@400;500"),
    },
    "landing": {
        "fonts_dir": "fonts",
        # The faces the ROOT PAGES paint, measured in a browser rather than read
        # off their stylesheets -- which is the whole reason this list was wrong.
        # Barlow Condensed 600 (wordmark + headings) and 400 (the instance tag,
        # per the brand spec); Barlow 400 (body), 500 (small labels), 600 and
        # 700.
        #
        # 600 AND 700 WERE MISSING UNTIL 2026-09-18 and the pages painted them
        # anyway, synthesised from 500 by the browser. Neither is visible in a
        # `font-weight:` grep of those files, which is how a list written from
        # the CSS came to say "exactly the four faces the landing page uses":
        # 600 arrives through the shell's `font: 600 13.5px/1 var(--font-body)`
        # on the masthead pills, and 700 through no rule at all -- it is the
        # browser's default bold for <strong>, <b> and <th>, of which
        # about.html alone paints fifteen. A synthesised bold is smeared rather
        # than drawn, at the weight a reader meets most often in prose.
        #
        # The rule "shipping a weight the page never sets is dead bytes" still
        # holds; the mistake was reading "sets" as "names in a declaration".
        # Re-measure with a browser (computed fontFamily + fontWeight over every
        # text-bearing element) before trimming this list. SINCE 2026-09-18 A GATE
        # DOES THAT MEASURING: page_consistency_test.mjs boots every sitemap
        # page and fails on a painted (family, weight) the page declares no
        # face for. It found the other half of this defect the same day — the
        # 40 instance sub-pages, the four history pages and all six apps were
        # asking for weights nothing here ships — and it is what makes trimming
        # safe, because the list can now be wrong in only one direction.
        #
        # AND THIS SET IS NOT THE ROOT'S ALONE. fonts/barlow-fontface.css is
        # read by build_landing_page, build_privacy_page (privacy + about),
        # build_coverage_map, build_history_page and build_county_pages -- so a
        # weight added here also reaches the four instance history pages and the
        # 188 per-county pages, which resolve `url(fonts/...)` against their own
        # instance's directory (the county pages rewrite it to `../fonts/`).
        # Every instance already carries Barlow 600 and 700, so those 192 pages
        # stopped synthesising their <strong> on the same change. Regenerate
        # them when this list moves; their --checks fail if you do not.
        "families": ("?family=Barlow+Condensed:wght@400;600"
                     "&family=Barlow:wght@400;500;600;700"),
    },
    "traffic": {
        "fonts_dir": "fonts",
        # traffic.html's mono, and ITS OWN TARGET rather than an addition to
        # `landing` above, because the two write to the same directory and only
        # one of them writes fonts/barlow-fontface.css. That file is read by
        # build_landing_page, build_privacy_page, build_coverage_map,
        # build_history_page and build_county_pages — about 195 pages — and
        # exactly one of them paints mono through the design system's stack.
        # Adding Plex there would declare a face 194 pages never ask for; a
        # separate target fetches the same two files into the same fonts/ and
        # prints a block that goes into traffic.html alone.
        #
        # 400 ONLY. The page paints one mono weight (the `code` cells holding
        # path prefixes, measured in a browser), and the sources pages' 500 is
        # for a <th> this page does not have.
        "families": "?family=IBM+Plex+Mono:wght@400",
    },
}
# A real browser UA so Google serves woff2 (not the legacy ttf it hands old UAs).
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
SUBSETS = ("latin", "latin-ext")


def slug(fam):
    return re.sub(r"[^a-z0-9]+", "-", fam.lower()).strip("-")


def fetch_css(families):
    url = "https://fonts.googleapis.com/css2" + families + "&display=swap"
    return subprocess.run(
        ["curl", "-sS", "--fail", "--max-time", "60", "-A", UA, url],
        check=True, capture_output=True,
    ).stdout.decode("utf-8")


def parse_faces(css):
    faces = []
    for sub, body in re.findall(r"/\* ([a-z-]+) \*/\s*@font-face \{([^}]*)\}", css):
        if sub not in SUBSETS:
            continue
        faces.append({
            "sub": sub,
            "fam": re.search(r"font-family: '([^']+)'", body).group(1),
            "wght": re.search(r"font-weight: (\d+)", body).group(1),
            "style": (re.search(r"font-style: (\w+)", body) or [None, "normal"])[1],
            "url": re.search(r"url\((https://[^)]+\.woff2)\)", body).group(1),
            "urange": re.search(r"unicode-range: ([^;]+);", body).group(1).strip(),
        })
    if not faces:
        raise RuntimeError("no latin/latin-ext @font-face blocks parsed — did the CSS format change?")
    return faces


def name_files(faces):
    """One local filename per UNIQUE url. A url serving SEVERAL weights is a
    variable font and its weight is not in the name -> <slug>-<subset>.woff2;
    a url serving one weight is a static face -> <slug>-<weight>-<subset>.woff2.

    THE TEST IS THE URL'S OWN WEIGHTS, not how many urls the target asked for.
    It used to read "this family+subset resolved to a single url, so it must be
    variable", which is true only when the request covers more than one weight:
    ask a STATIC family for one weight and it resolves to one url too, and the
    file lands as `ibm-plex-mono-latin.woff2` — a name claiming the whole family
    for one of its weights, which the next weight added would have to rename.
    Found 2026-09-18 fetching Plex 400 for traffic.html, where every other Plex
    file in the fleet is already `ibm-plex-mono-400-latin.woff2`."""
    weights_by_url = defaultdict(set)
    for f in faces:
        weights_by_url[f["url"]].add(f["wght"])
    url_name = {}
    for f in faces:
        variable = len(weights_by_url[f["url"]]) > 1
        url_name[f["url"]] = (
            "%s-%s.woff2" % (slug(f["fam"]), f["sub"]) if variable
            else "%s-%s-%s.woff2" % (slug(f["fam"]), f["wght"], f["sub"])
        )
    return url_name


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", default="il", choices=sorted(TARGETS),
                    help="which page's fonts to fetch (default: il)")
    args = ap.parse_args()
    spec = TARGETS[args.target]
    fonts_dir = os.path.join(REPO_ROOT, spec["fonts_dir"])

    css = fetch_css(spec["families"])
    faces = parse_faces(css)
    url_name = name_files(faces)

    os.makedirs(fonts_dir, exist_ok=True)
    for url, name in sorted(set(url_name.items())):
        dest = os.path.join(fonts_dir, name)
        subprocess.run(["curl", "-sS", "--fail", "--max-time", "60", url, "-o", dest], check=True)
        print("  %s (%d b)" % (name, os.path.getsize(dest)), file=sys.stderr)
    print("%d faces, %d unique woff2 in %s/" % (len(faces), len(set(url_name.values())),
                                                 spec["fonts_dir"]), file=sys.stderr)

    out = ["/* ==== SELF-HOSTED FONTS:BEGIN — generated by scripts/build_fonts.py; do",
           "   NOT hand-edit. Was fonts.googleapis.com; self-hosted so the two font",
           "   preconnects free up for the basemap tile shards (PSI LCP) and the",
           "   same-origin + SW-precached woff2 lands early enough to avoid the swap",
           "   CLS. Re-run scripts/build_fonts.py and re-paste on a font change. ==== */"]
    for f in faces:
        out += ["@font-face {",
                "  font-family: '%s';" % f["fam"],
                "  font-style: %s;" % f["style"],
                "  font-weight: %s;" % f["wght"],
                "  font-display: swap;",
                "  src: url(fonts/%s) format('woff2');" % url_name[f["url"]],
                "  unicode-range: %s;" % f["urange"],
                "}"]
    out.append("/* ==== SELF-HOSTED FONTS:END ==== */")
    print("\n".join(out))


if __name__ == "__main__":
    main()
