#!/usr/bin/env python3
"""
Asset gate: every same-origin file a page asks for must actually be in the tree.

WHY THIS EXISTS. Michigan's go-live PR found two of these by hand, minutes
apart, in an instance that had already passed the whole 38-gate battery twice:

  * mi/index.html declared 18 @font-face rules reading `src: url(fonts/*.woff2)`
    — a block BYTE-IDENTICAL to the one in ia/index.html — and mi/fonts/ did not
    exist. Every other instance carries the directory. On publish all 18 would
    have 404'd and the app would have fallen back to system fonts: no error, no
    red gate, just a page in the wrong typeface forever.
  * mi/index.html named https://districtry.com/mi/og-image.png in og:image,
    twitter:image and its JSON-LD, and the file did not exist, so every social
    share of the Michigan app would have rendered a broken card.

NOTHING WAS GOING TO CATCH EITHER, and the reason is written in two other
gates' own comments. validate_card_links.py probes ABSOLUTE urls over the
network, monthly — a relative href "is not its subject at all"
(scripts/landing_test.mjs says exactly that) — and an absolute url pointing at
our own not-yet-published path is indistinguishable from a site that is merely
down. landing_test.mjs boots real browsers but only for the ROOT's generated
pages. Each instance's smoke test boots its own app, but a 404 on a font or a
preview image throws no console error and fails no assertion. So the surface
between "the HTML asks for it" and "the repo contains it" had no gate at all.

WHAT IS CANONICAL: the TREE, the same rule validate_instance_registration.py
and validate_card_links.py discover by — a top-level directory carrying both an
index.html and a data/app/ is an instance. Nothing here is hand-listed, so an
instance is covered the day its folder exists.

WHAT IT REFUSES TO JUDGE, and why each exclusion is narrow rather than
convenient. <script> bodies are stripped before the attribute scan: a page that
builds `'<a href="' + url + '">'` is not naming a file, and reading it as one
produced 40-odd findings like `ny/i.cb_website.url` on the first run. A
reference is then only considered when it carries a known asset extension or
ends in `/`, because a prefix is not an address — the same rule
validate_card_links.py applies to its concatenated urls. Anything holding a
template character never resolves at all.

WHAT IT DOES NOT CHECK. That the asset is CORRECT (right glyphs, right image),
that an external host is up (validate_card_links.py's job, monthly and
network-bound), or that the file survives the Pages deploy's exclude list —
deploy-pages.yml asserts that itself, against the real assembled _site, where
there are no rsync-pattern semantics to re-implement and get subtly wrong.

Usage:
    python3 scripts/validate_instance_assets.py
    python3 scripts/validate_instance_assets.py --report   # list every ref checked
"""

import argparse
import os
import re
import sys
from urllib.parse import unquote, urlsplit

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The fleet's own origin. An absolute url on it is a claim about THIS repo's
# tree, which is why og-image.png could be missing while every link gate stayed
# green: to a network probe it looks like somebody else's outage.
SELF_ORIGINS = ("https://districtry.com", "http://districtry.com",
                "https://www.districtry.com")

# `content` is in here for og:image / twitter:image, and it is not optional: a
# first draft of this gate scanned src/href only, caught the missing fonts, and
# sailed straight past the missing og-image.png that was found in the same
# hour — the preview image is named in a <meta content="…"> and nowhere else.
# Non-path content values (a description, "width=device-width") fall out at the
# extension test below rather than needing a list of which meta names to read.
ATTR_RE = re.compile(r'(?:src|href|content)\s*=\s*"([^"]*)"', re.I)
# CSS url() — the half that mattered for the fonts, since @font-face declares
# its files here and they never appear in an attribute.
CSS_URL_RE = re.compile(r'url\(\s*([^)\s]+?)\s*\)', re.I)
# Script bodies are stripped before the attribute scan (a page that builds
# `'<a href="' + url + '">'` is not naming a file) — EXCEPT ld+json, which is
# data, not code: it carries the same preview-image url as the meta tags and
# concatenates nothing, so stripping it would reopen exactly the hole above.
SCRIPT_RE = re.compile(
    r'<script\b(?![^>]*application/ld\+json).*?</script\s*>', re.I | re.S)
# Any absolute url on this fleet's own origin, wherever it appears in the
# surviving markup — which is how the ld+json block's "image"/"url" values are
# read without hand-listing JSON-LD's key names.
JSONLD_URL_RE = re.compile(r'"(https?://(?:www\.)?districtry\.com/[^"\s]*)"')
# <meta http-equiv="refresh" content="0; url=/il/sources.html">
REFRESH_RE = re.compile(r'^\s*\d+\s*;\s*url\s*=\s*(.*)$', re.I)

SKIP_PREFIXES = ("http://", "https://", "//", "data:", "mailto:", "tel:",
                 "javascript:", "blob:", "#", "about:")

# A reference the page BUILDS rather than states.
TEMPLATE_CHARS = ("{", "}", "$", "+", "\\", "*", "`")

# Only these are treated as a file claim. A bare word with no extension is a
# fragment of something, not a path — the distinction that keeps this gate
# precise enough to be worth running.
ASSET_EXTS = (".woff2", ".woff", ".ttf", ".otf", ".png", ".jpg", ".jpeg",
              ".webp", ".svg", ".ico", ".gif", ".avif", ".css", ".js", ".mjs",
              ".json", ".webmanifest", ".html", ".xml", ".txt", ".pdf")

# ---------------------------------------------------------------------------
# KNOWN_ABSENT — references this repo deliberately does not satisfy, each with
# its reason and the date it was recorded. Same posture as
# validate_card_links.py's EXPECTED_UNREACHABLE and check_roster_retention.py's
# ACCEPTED_DROPS: a measured exception is written down, never silenced, and it
# is re-audited on every run so it cannot rot into a permanent hole. An entry
# that stops being referenced by any page FAILS, because that means the reason
# has passed and the exemption is now hiding nothing but itself.
# ---------------------------------------------------------------------------
KNOWN_ABSENT = {
    "images/layers.png": (
        "2026-09-03 — Leaflet's own default control sprite, referenced by the "
        "vendored leaflet.css this repo inlines verbatim. The app builds its "
        "own controls and never renders the layers control, so the rule never "
        "matches and the file is never requested. Shipping Leaflet's image "
        "directory to satisfy a rule nothing triggers would be dead bytes in "
        "every instance."),
    "images/layers-2x.png": (
        "2026-09-03 — the retina twin of the sprite above, same rule, same "
        "reason."),
    "images/marker-icon.png": (
        "2026-09-03 — Leaflet's default marker icon, from the same inlined "
        "vendor CSS. Every marker this fleet draws sets its own icon or is a "
        "circleMarker, so the default icon path is never taken."),
}


def instances():
    """Every top-level directory that IS an instance — index.html + data/app/."""
    found = []
    for name in sorted(os.listdir(REPO_ROOT)):
        full = os.path.join(REPO_ROOT, name)
        if not os.path.isdir(full) or name.startswith("."):
            continue
        if (os.path.isfile(os.path.join(full, "index.html"))
                and os.path.isdir(os.path.join(full, "data", "app"))):
            found.append(name)
    return found


def surfaces():
    """Every authored HTML page: the root's, and each instance's own.

    Discovered rather than listed, for the reason validate_card_links.py
    records: its own hand-kept list of fourteen pages named four instances out
    of five, and Iowa shipped three unwatched pages in the very commit whose
    comment said a new one needs no update.
    """
    out = [(f, os.path.join(REPO_ROOT, f))
           for f in sorted(os.listdir(REPO_ROOT)) if f.endswith(".html")]
    for tag in instances():
        d = os.path.join(REPO_ROOT, tag)
        for f in sorted(os.listdir(d)):
            if f.endswith(".html"):
                out.append(("%s/%s" % (tag, f), os.path.join(d, f)))
            # Concept SUBDIRECTORIES too, one level deep: il/county-board/
            # holds 73 generated per-county pages
            # (scripts/build_county_pages.py) and every gate here discovered
            # pages one level up, so all 73 would have shipped unwatched — the
            # same miss validate_card_links.py made when Iowa arrived as a
            # fifth instance. These pages reference the fonts and the mark by
            # a ../ hop, which is exactly what this gate exists to resolve.
            sub = os.path.join(d, f)
            if os.path.isdir(sub):
                for g in sorted(os.listdir(sub)):
                    if g.endswith(".html"):
                        out.append(("%s/%s/%s" % (tag, f, g), os.path.join(sub, g)))
    return out


def to_repo_path(ref, page_rel):
    """The repo-relative path a reference resolves to, or None if it is not one."""
    ref = ref.strip().strip("'\"")
    if not ref or any(c in ref for c in TEMPLATE_CHARS):
        return None

    # <meta http-equiv="refresh" content="0; url=/il/sources.html"> — the
    # target is inside the content value, not the whole of it. These are the
    # root's redirect shells, whose url is the only machine-readable record of
    # where each pre-R5 path now forwards a reader, so the redirect target is
    # extracted and checked rather than skipped.
    refresh = REFRESH_RE.match(ref)
    if refresh:
        ref = refresh.group(1).strip().strip("'\"")
        if not ref:
            return None

    for origin in SELF_ORIGINS:
        if ref.startswith(origin):
            ref = ref[len(origin):] or "/"
            break
    else:
        if ref.startswith(SKIP_PREFIXES):
            return None

    # Strip query and fragment: districtry.com/il/?x=1#point=… is a request for
    # il/index.html either way.
    path = unquote(urlsplit(ref).path)
    if not path:
        return None

    directory = path.endswith("/")
    if path.startswith("/"):
        rel = path.lstrip("/")
    else:
        rel = os.path.normpath(os.path.join(os.path.dirname(page_rel), path))

    if directory or rel in ("", "."):
        rel = os.path.join("" if rel in ("", ".") else rel, "index.html")
    elif os.path.isdir(os.path.join(REPO_ROOT, rel)):
        rel = os.path.join(rel, "index.html")
    elif not path.lower().endswith(ASSET_EXTS):
        # No extension and not a directory: a fragment of a path the page
        # assembles, not an address this gate can judge.
        return None

    rel = os.path.normpath(rel)
    if rel.startswith(".."):        # escapes the repo — not ours to judge
        return None
    return rel


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true",
                    help="print every same-origin reference checked, not just failures")
    args = ap.parse_args()

    pages = surfaces()
    if len(pages) < 2:
        print("validate-instance-assets: FAIL — found %d authored page(s) in %s. "
              "Nothing was verified; run this from the repo root."
              % (len(pages), REPO_ROOT), file=sys.stderr)
        sys.exit(1)

    problems = []
    missing = []
    checked = 0
    seen_known = set()

    for page_rel, page_path in pages:
        with open(page_path, encoding="utf-8") as fh:
            src = fh.read()
        markup = SCRIPT_RE.sub(" ", src)
        refs = set(ATTR_RE.findall(markup)) | set(CSS_URL_RE.findall(markup))
        # ld+json survives the strip above; its own url values are JSON strings
        # rather than attributes, so they need their own read.
        refs |= set(JSONLD_URL_RE.findall(markup))
        for ref in sorted(refs):
            bare = ref.strip().strip("'\"")
            if bare in KNOWN_ABSENT:
                seen_known.add(bare)
                continue
            rel = to_repo_path(ref, page_rel)
            if rel is None:
                continue
            checked += 1
            if args.report:
                print("  %-34s %s" % (page_rel, rel))
            if not os.path.isfile(os.path.join(REPO_ROOT, rel)):
                missing.append((page_rel, ref, rel))

    # Re-audit every exemption against the tree, so one cannot outlive its
    # reason: the failure mode check_roster_retention.py's docstring describes,
    # where an accepted exception goes silent the day after it merges.
    for ref in sorted(KNOWN_ABSENT):
        if ref not in seen_known:
            problems.append(
                "KNOWN_ABSENT records %r, and no page references it any more. "
                "The reason has passed — delete the entry rather than leaving a "
                "hole in this gate that hides nothing." % ref)
        elif os.path.isfile(os.path.join(REPO_ROOT, ref)):
            problems.append(
                "KNOWN_ABSENT records %r as deliberately absent, and the file "
                "now exists. Retire the entry." % ref)

    if missing:
        # Group by the absent file's directory: 18 missing woff2 is ONE fonts
        # directory that was never copied, and eighteen identical lines would
        # bury that.
        by_dir = {}
        for row in missing:
            by_dir.setdefault(os.path.dirname(row[2]) or ".", []).append(row)
        for directory in sorted(by_dir):
            rows = by_dir[directory]
            print("FAIL: %d reference(s) resolve into %s/ and the file is not in "
                  "the tree:" % (len(rows), directory), file=sys.stderr)
            for page_rel, ref, rel in rows[:6]:
                print("        %s asks for %r -> %s" % (page_rel, ref, rel),
                      file=sys.stderr)
            if len(rows) > 6:
                print("        ... and %d more in the same directory"
                      % (len(rows) - 6), file=sys.stderr)

    for p in problems:
        print("FAIL: %s" % p, file=sys.stderr)

    if missing or problems:
        print("validate-instance-assets: FAIL — %d same-origin reference(s) point "
              "at a file this repo does not contain%s. Each one is a 404 the "
              "moment the page is published, and nothing else here would have "
              "said so."
              % (len(missing),
                 "; %d exemption problem(s)" % len(problems) if problems else ""),
              file=sys.stderr)
        sys.exit(1)

    print("validate-instance-assets: OK — %d same-origin reference(s) across %d "
          "authored page(s) in %d instance(s) all resolve to a file in the tree "
          "(%d recorded exemption(s), each still referenced)"
          % (checked, len(pages), len(instances()), len(KNOWN_ABSENT)))


if __name__ == "__main__":
    main()
