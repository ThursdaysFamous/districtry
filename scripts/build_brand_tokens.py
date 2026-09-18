#!/usr/bin/env python3
"""
districtry/tokens/districtry.tokens.css is the ONE source of the brand surface.

WHY THIS EXISTS. The fleet was carrying one palette under two vocabularies and
four hand-kept copies. The apps and the twelve instance sub-pages speak
--accent/--slate/--panel; the root pages (the landing page and privacy.html)
speak --brand-*/--ink-3/--surface, because those two are generated from the
design-token file and the others were typed. Measured across both tiers, the
neutral chrome was already IDENTICAL in both vocabularies — the same six colours
under two sets of names — so this was never two designs. It was one design with
nothing asserting it stayed one.

And it had already stopped. Three divergences were live when this was written:

  --accent-deep dark   app #c4b0ff   root pages #a78bfa   (a visible link colour)
  --accent-warm        app #b0316e   root pages had none
  font stacks          app carries 'Barlow Fallback'; the root pages do not

plus four the sub-page shell introduced the day it was written, by restating
the dark tier from memory: --accent-warm #fd88b8 against the app's #e879b9,
--slate-soft #8f8a9e against #746e86, and both --line values off by 0.02 alpha.
That shell exists BECAUSE thirteen hand-kept copies drifted. It drifted on day
one. Restating a palette is not a thing to do carefully; it is a thing not to do.

Two more were found on 2026-09-02, in the gate's OWN blind spots, after it had
been green for two weeks:

  --accent-warm-deep dark   app skin #f0a3cf   token file #f0a5cd
      The skin's dark block restates all four accents by hand and this checked
      none of them: the light accents ride the worksheet (gated below), and
      the dark ones rode nothing. Every instance's app painted one dark
      magenta while every sub-page — generated from the token file — painted
      the other, in the same tab.
  ia/metro-worksheet.json   accent_deep #4a2b8c, accent_warm_deep #8c2e4a
      against the fleet's #5730ab / #8f2659, from the day Iowa shipped, under
      a label reading "shared with the fleet, not state-themed by convention".
      check_worksheets named three worksheets of five.

A gate that checks a hand-kept list of consumers has the same failure mode as
the copies it guards: the newest one is the one it does not know about.

WHAT THIS DOES. Two jobs, one source:

  GENERATE  engine/shared/tokens-brand.txt — the sub-page palette, emitted in
            the app's vocabulary from the canonical values, and spliced into
            every sub-page by compose_app.py. Nobody types these again.
  CHECK     every other consumer against the same source, through the ALIASES
            table below: the app's own skin, each instance worksheet's palette
            keys, and the two generated root pages. A consumer keeps its own
            names — renaming --accent to --brand-600 across three 21,000-line
            apps would touch thousands of call sites and change nothing a reader
            sees — but it may not keep its own VALUES.

WHY NOT ONE VOCABULARY. Because the names are not the problem and never were.
--accent/--panel are an application's semantics; --brand-600/--surface are a
design system's ramp. Both are correct in their own document. The defect was
that two documents disagreed about what colour --accent-deep is in dark mode,
and that is what an alias table plus a gate fixes.

ORDER OF OPERATIONS: this script, then compose_app.py (which splices what this
emits), then generate_metro_files.py. --check is order-independent.

    python3 scripts/build_brand_tokens.py           # regenerate + report
    python3 scripts/build_brand_tokens.py --check   # drift gate; exit 1 on any
"""

import argparse
import glob
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKENS = os.path.join(REPO_ROOT, "districtry", "tokens", "districtry.tokens.css")
SHELL_BLOCK = os.path.join(REPO_ROOT, "engine", "shared", "tokens-brand.txt")
APP_SKIN = os.path.join(REPO_ROOT, "engine", "index.html", "styles-districtry-skin.txt")

# app vocabulary -> canonical token. Every row is a claim that these two names
# mean the same colour, and --check is what makes it a claim rather than a hope.
ALIASES = [
    ("--accent",           "brand"),
    ("--accent-deep",      "brand-700"),
    ("--accent-warm",      "brand-warm"),
    ("--accent-warm-deep", "brand-warm-deep"),
    ("--ink",              "ink"),
    ("--slate",            "ink-3"),
    ("--slate-soft",       "faint"),
    ("--paper",            "paper"),
    ("--panel",            "surface"),
    ("--line",             "border"),
    ("--line-strong",      "border-dot"),
]

# What the skin restates BY HAND, per tier — and every one of these must be
# PRESENT, not merely correct when present. The light :root sets the seven
# neutrals and not the accents, which arrive through the GENERATED brand-palette
# region the worksheet drives (gated in check_worksheets). The dark block has no
# generated region to lean on and restates all eleven aliases itself, which is
# where --accent-warm-deep sat two hex digits off the token file for two weeks
# while a check that only knew the neutrals stayed green. Presence is required
# because a dark alias that goes missing does not error — the browser falls
# through to the LIGHT value, which is a dark-mode link painted for white paper.
APP_SKIN_CHECKED = {
    "light": ["--ink", "--slate", "--slate-soft", "--paper", "--panel",
              "--line", "--line-strong"],
    "dark":  [prop for prop, _tok in ALIASES],
}
# The one canonical name the skin sets DIRECTLY rather than through an alias
# (--faint, defined for the map legend, which had referenced it undefined for
# weeks). It is a restatement all the same, and validate_contrast.py measures
# the token file's --faint on the assumption that this is the same colour.
APP_SKIN_DIRECT = [("--faint", "faint")]

# The fallback face, by its canonical text. Nine surfaces carry a copy — the
# shared shell, all six apps, and (via build_landing_page.FALLBACK_FACE) the two
# root pages — and the overrides are computed numbers, so a copy that drifts is
# a copy that stops holding the metrics without looking wrong.
#
# THIS LIST NAMED THREE APPS OUT OF SIX UNTIL MICHIGAN'S GO-LIVE, and the
# .claude/skills/new-state-instance skill has named it a day-one registration
# step the whole time — Wisconsin, Iowa and Michigan each skipped it, so
# following the last port's precedent perpetuated the hole rather than closing
# it. The omission was not harmless-because-redundant: the @font-face block
# sits in UNFENCED authored CSS in each app (nearest preceding marker is
# `GENERATED:END head-theme`), so compose_app.py's byte-parity never covered
# it. All nine carry an identical block today, measured, so adding the three
# was free. Note what the OK line counts is FILES, not instances.
FACE_RE = re.compile(
    r"@font-face\s*\{[^}]*font-family:\s*'Barlow Fallback'[^}]*\}", re.S)
FACE_CARRIERS = ["engine/shared/styles-subpage.txt",
                 "il/index.html", "ny/index.html", "ca/index.html",
                 "wi/index.html", "ia/index.html", "mi/index.html",
                 "index.html", "privacy.html"]

WORKSHEET_PALETTE = [("accent", "brand"), ("accent_deep", "brand-700"),
                     ("accent_warm", "brand-warm"),
                     ("accent_warm_deep", "brand-warm-deep")]

# The font stacks, stated once. The app's body stack names 'Barlow Fallback' —
# a metric-matched local face that stops the layout shifting while the webfont
# loads — and every other surface had quietly dropped it.
FONTS = [("--font-display", "font-heading"), ("--font-body", "font-body")]
# Mono is the one stack the token file does not carry: it is a system list with
# no webfont behind it, so there is nothing for a design system to own.
FONT_MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

problems = []


def fail(msg):
    print("build-brand-tokens: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def norm(v):
    """Compare colours by content, not by typing. `rgba(236, 233, 244, 0.10)`
    and `rgba(236,233,244,0.1)` are the same colour and two files spell it two
    ways; a gate that called that a drift would be reporting whitespace."""
    v = re.sub(r"\s+", "", v.strip().lower()).rstrip(";")
    v = re.sub(r"(\d)0+(?=[,)])", r"\1", v) if v.startswith("rgba") else v
    return v


def token_block(css, selector):
    m = re.search(re.escape(selector) + r"\s*\{(.*?)\n\}", css, re.S)
    if not m:
        fail("no %r block in %s" % (selector, os.path.relpath(TOKENS, REPO_ROOT)))
    return {k: v.strip() for k, v in
            re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", m.group(1))}


def resolve(table, name):
    """One level of var() indirection — --brand is `var(--brand-600)`."""
    v = table.get("--" + name)
    if v is None:
        return None
    m = re.fullmatch(r"var\((--[a-z0-9-]+)\)", v.strip())
    return table.get(m.group(1), v) if m else v


def render(light, dark):
    L = ["/* GENERATED by scripts/build_brand_tokens.py from",
         "   districtry/tokens/districtry.tokens.css — do not hand-edit. The",
         "   values are the design system's; the NAMES are the app's, so a",
         "   sub-page and the app it hangs off use one vocabulary. Rerun the",
         "   script, then compose_app.py. */",
         ":root {"]
    for prop, tok in ALIASES:
        L.append("  %s: %s;" % (prop, resolve(light, tok)))
    for prop, tok in FONTS:
        L.append("  %s: %s;" % (prop, resolve(light, tok)))
    L += ["  --font-mono: %s;" % FONT_MONO,
          "  --focus-ring: 3px solid var(--accent-warm);",
          "}",
          "/* The dark tier is reached FROM the app, which has a theme toggle; the",
          "   boot script in <head> sets data-theme before first paint from the",
          "   same localStorage key the app writes. */",
          ':root[data-theme="dark"] {']
    for prop, tok in ALIASES:
        v = resolve(dark, tok)
        if v is not None:
            L.append("  %s: %s;" % (prop, v))
    L.append("}")
    return "\n".join(L) + "\n"


def check_app_skin(light, dark):
    css = read(APP_SKIN)
    # the skin's own :root and its dark counterpart, as written
    for label, selector, table in (("light", ":root", light),
                                   ("dark", ':root[data-theme="dark"]', dark)):
        m = re.search(re.escape(selector) + r"\s*\{(.*?)\n  \}", css, re.S)
        if not m:
            problems.append("app skin: no %s palette block found" % label)
            continue
        got = {k: v.strip() for k, v in
               re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", m.group(1))}
        checked = [(prop, dict(ALIASES)[prop]) for prop in APP_SKIN_CHECKED[label]]
        for prop, tok in checked + APP_SKIN_DIRECT:
            want = resolve(table, tok)
            if prop not in got:
                problems.append(
                    "app skin %s: %s is not set — the %s block must restate it, "
                    "or the browser falls through to the other tier's value"
                    % (label, prop, label))
                continue
            if want is None or norm(got[prop]) != norm(want):
                problems.append(
                    "app skin %s: %s is %s, the token file says --%s is %s"
                    % (label, prop, got[prop], tok, want))


def check_fallback_face():
    """Every surface that NAMES 'Barlow Fallback' in its body stack must also
    define it, identically. Naming a family nobody defines is not an error
    anywhere — the stack just falls through — which is exactly why eleven
    surfaces did it for months without a symptom louder than a reflow."""
    seen = {}
    for rel in FACE_CARRIERS:
        path = os.path.join(REPO_ROOT, rel)
        if not os.path.exists(path):
            problems.append("%s: missing, but listed as a fallback-face carrier" % rel)
            continue
        m = FACE_RE.search(read(path))
        if not m:
            problems.append("%s: names 'Barlow Fallback' in --font-body but never "
                            "defines the face" % rel)
            continue
        seen[rel] = re.sub(r"\s+", " ", m.group(0)).strip()
    if len(set(seen.values())) > 1:
        for rel, txt in sorted(seen.items()):
            problems.append("fallback face differs in %s: %s" % (rel, txt[:90]))


def worksheets():
    """Every metro-worksheet.json in the tree: the root one plus one per
    instance folder. DISCOVERED, because the hand-kept ("", "ny", "ca") this
    replaced was written when those were the three instances and never
    learned about Wisconsin or Iowa — and Iowa's palette had been off the
    fleet's since the day it shipped."""
    found = ["metro-worksheet.json"]
    for name in sorted(os.listdir(REPO_ROOT)):
        rel = os.path.join(name, "metro-worksheet.json")
        if os.path.isfile(os.path.join(REPO_ROOT, rel)):
            found.append(rel)
    return found


def check_theme_colour_tags(light, dark):
    """Every <meta name="theme-color"> on the site, against the token file.

    WHY THIS EXISTS. That tag paints the BROWSER's chrome, and it is the one
    brand value a reader sees that no stylesheet owns, so nothing here compared
    it to anything. Four authored pages -- ny/council-district.html,
    ny/police-precinct.html, ny/community-board.html and
    ca/supervisor-district.html -- carried the pre-rebrand navy #0b3d91 from
    before the rebrand until 2026-09-18, through a rebrand, a fleet-wide social
    card fix and a theme-boot consolidation.

    IT SURVIVED BEING FOUND, WHICH IS THE PART WORTH GATING. The four were
    noticed and then blamed on `brand.theme_color` in the NY and SF worksheets;
    both worksheets said #6d3fd1 the whole time. question_page.py DOES restate
    the tag from the worksheet, so a generated page cannot drift -- but these
    four are authored, that generator never reaches them, and checking the
    worksheet returned a clean answer about the wrong file.

    The worksheet key is checked here too, so both ends of that mistake are
    held to one source rather than to each other.
    """
    want_light = resolve(light, "brand-600")
    want_dark = resolve(dark, "paper")
    if not want_light or not want_dark:
        fail("--brand-600 or the dark --paper is missing from the token file")
    tag_re = re.compile(r'<meta\s+name="theme-color"([^>]*)>')
    attr_re = re.compile(r'content="(#[0-9a-fA-F]{3,8})"')
    pages = 0
    for path in sorted(glob.glob(os.path.join(REPO_ROOT, "**", "*.html"),
                                 recursive=True)):
        rel = os.path.relpath(path, REPO_ROOT)
        if rel.startswith(("node_modules", "engine" + os.sep, "docs" + os.sep)):
            continue
        text = read(path)
        for attrs in tag_re.findall(text):
            got = attr_re.search(attrs)
            if not got:
                continue
            pages += 1
            # A media-qualified pair is the other way of doing this, used by
            # the paste-in PWA snippet: the dark one names the dark ground
            # rather than the accent.
            is_dark = "prefers-color-scheme: dark" in attrs
            want = want_dark if is_dark else want_light
            if norm(got.group(1)) != norm(want):
                problems.append(
                    "%s: theme-color is %s, --%s is %s"
                    % (rel, got.group(1), "paper (dark)" if is_dark else "brand-600", want))
    for rel in worksheets():
        brand = json.load(open(os.path.join(REPO_ROOT, rel),
                               encoding="utf-8")).get("brand", {})
        if "theme_color" in brand and norm(brand["theme_color"]) != norm(want_light):
            problems.append("%s: brand.theme_color is %s, --brand-600 is %s"
                            % (rel, brand["theme_color"], want_light))
    return pages


def check_worksheets(light):
    for rel in worksheets():
        path = os.path.join(REPO_ROOT, rel)
        pal = json.load(open(path, encoding="utf-8")).get("palette", {})
        for key, tok in WORKSHEET_PALETTE:
            want = resolve(light, tok)
            if key in pal and want and norm(pal[key]) != norm(want):
                problems.append("%s: palette.%s is %s, --%s is %s"
                                % (rel, key, pal[key], tok, want))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    css = read(TOKENS)
    light = token_block(css, ":root")
    dark = token_block(css, '[data-theme="dark"]')
    for _prop, tok in ALIASES:
        if resolve(light, tok) is None:
            fail("--%s is missing from the token file's :root — renamed upstream?" % tok)

    body = render(light, dark)
    current = read(SHELL_BLOCK) if os.path.exists(SHELL_BLOCK) else None

    check_app_skin(light, dark)
    check_worksheets(light)
    tags = check_theme_colour_tags(light, dark)
    check_fallback_face()

    if args.check:
        if current != body:
            problems.insert(0, "engine/shared/tokens-brand.txt does not match the "
                               "token file — rerun scripts/build_brand_tokens.py")
        if problems:
            for p in problems:
                print("  - " + p, file=sys.stderr)
            fail("%d consumer(s) disagree with districtry/tokens/districtry.tokens.css"
                 % len(problems))
        print("build-brand-tokens: OK — %d alias(es) agree across the shell, both "
              "tiers of the app skin and %d worksheet(s); the fallback face is "
              "identical on %d surface(s); %d theme-colour tag(s) carry the "
              "brand accent"
              % (len(ALIASES), len(worksheets()), len(FACE_CARRIERS), tags))
        return

    if problems:
        for p in problems:
            print("  - " + p, file=sys.stderr)
        fail("%d consumer(s) disagree; fix them or the token file, then rerun"
             % len(problems))
    os.makedirs(os.path.dirname(SHELL_BLOCK), exist_ok=True)
    with open(SHELL_BLOCK, "w", encoding="utf-8", newline="") as f:
        f.write(body)
    print("build-brand-tokens: wrote engine/shared/tokens-brand.txt — %d alias(es) "
          "from districtry/tokens/districtry.tokens.css" % len(ALIASES))


if __name__ == "__main__":
    main()
