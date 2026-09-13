#!/usr/bin/env python3
"""
Every text colour this site paints, measured against the ground it sits on.

WHY THIS EXISTS. districtry/tokens/districtry.tokens.css is the ONE source of
the brand surface, and build_brand_tokens.py makes that true: every consumer's
values are gated as identical to it. But identical to WHAT was never measured.
The palette carries 54 aria attributes' worth of care in the app, 17
focus-visible rules and a reduced-motion query — and not one number saying
that the text a reader must read is legible against the ground it is painted
on. For a public civic tool whose standing rule is that a claim gets measured
rather than asserted, an unmeasured legibility claim is the shape of thing
this repo refuses everywhere else.

It was not an idle gap. Measured on the day this was written (2026-09-02):

  --faint  light  #9aa3b2  on --surface #ffffff   2.54:1   footer meta at 11px,
                                                           placeholders, menu
                                                           labels, the landing
                                                           page's own h2
  --faint  dark   #746e86  on --surface #201d29   3.40:1
  --muted  light  #6b7280  on --paper   #f4f2ee   4.32:1
  #fff     dark            on --brand   #a78bfa   2.72:1   the search button,
                                                           every primary CTA
  #fff     dark            on --brand-700 #c4b0ff 1.91:1   its hover, .cta, the
                                                           sub-page shell's
                                                           primary action
  #fff     dark            on --ink     #ece9f4   1.20:1   the SKIP LINK — fixed
                                                           in this change, in
                                                           the app AND the
                                                           sub-page shell
  --line-strong  light  #c9c5d4 on --surface      1.69:1   the gaps modal's
                                                           open/closed caret —
                                                           repainted --slate

against the 4.5:1 that WCAG 1.4.3 asks of body text and the 3:1 it asks of
large text and UI parts (1.4.11). Light --faint clears NEITHER — it is below
the bar for text a reader is not even expected to read closely — and the dark
tier's button faces are the polarity inversion the sub-page shell's own
comments describe: "deep" means more contrast against the ground, which on a
dark ground is LIGHTER, and the engine paints white text on it.

WHAT THIS DOES. Reads the token file — both tiers, the dark one composed over
the light one exactly as the cascade does it, since [data-theme="dark"]
redefines 25 tokens and inherits the rest — and tests an explicit table of
(foreground, background, role) PAIRS: the pairs the product actually paints,
mapped from every CSS surface (the app's style blocks under engine/index.html/,
the sub-page shell, and the CSS the four root-page builders emit), never a
cartesian product. A translucent value is composited over its ground before
measuring, because rgba(236,233,244,0.1) is not a colour until it is on
something. Each role carries the floor WCAG sets for it.

WHY A PAIR TABLE AND NOT THE CSS. The cascade decides what text sits on, and
no regex over 1,000 lines of skin can follow `color:` through inheritance to
the background four ancestors up. So the pairs are STATED, with the selector
that proves each one, and the table is the claim — the same shape as
build_brand_tokens.py's ALIASES: a row is an assertion that this text is
painted on this ground, and the gate is what makes it a measurement rather
than a hope. A new text colour ships by adding its row.

WHERE A GROUND SITS. A translucent token is not a colour until it is on
something, and WHICH opaque thing matters: dark --brand-tint is
rgba(167,139,250,0.16), and the same --muted text on it measures 4.94:1 over
--paper and 4.33:1 over --surface — one side of the 4.5 floor each. So a row
names the opaque ground under a translucent background with `@`:
`brand-tint@surface` is the coverage-map legend's hover, which sits on a
--surface panel; bare `brand-tint` is the landing page's pill, which sits on
the body. A translucent FOREGROUND takes the same suffix (`border@paper` is
the search input's border composited over its own dark interior before it is
seen against the masthead). Without `@`, a translucent background is
composited over --paper, the body ground, and a translucent foreground over
its row's background. The first draft of this gate composited every
translucent ground over --paper and passed the legend hover at 4.94:1 while
the browser paints it at 4.33:1; the review that caught it is why the ground
is now written down per row. Composited channels are rounded to 8 bits
before measuring, so a recorded ratio is one a rasteriser can reproduce.

WHAT THE TABLE COVERS, AND WHAT IT DOES NOT — measured, not assumed. The five
CSS surfaces (engine/index.html/styles-*.txt, engine/shared/styles-subpage.txt
and the CSS the four root-page builders emit) were mapped rule by rule on
2026-09-02, and every paint that puts one brand token on another is a row
here. A SIXTH was mapped on 2026-09-12 — the CSS each instance's sources.html
carries outside its fences, six hand-kept copies of one stylesheet — because a
browser sweep found its row-header band was rgba(244,247,249,0.6) with no dark
counterpart, compositing over --panel to a light grey block under light text
(the layer name 2.18:1, its id 1.25:1, the guide link 1.37:1). That is now
var(--paper) and falls on the ink/paper, ink-3/paper and brand-700/paper rows
below. Two literals in that stylesheet remain and are NOT measured: the
:target row highlight rgba(65,182,230,0.12) and .matrix-nav a:hover's
rgba(11,83,148,0.06), both pre-rebrand blues, both states no sweep reaches, and
both legible in either tier by calculation (the target row grounds --ink at
13.2:1 dark and 16.0:1 light). The only counts this file claims are the ones the OK line prints —
rows, tier-pairs and gated pairs — because a row is a (fg, bg, role) that
stands for every selector in its `where` in both tiers, and an earlier
docstring quoted totals from the map that did not sum. What the map found
and this gate does NOT measure: literal colours the token file does not own —
the engine's --card-* palette (styles-card-v2: #111827 on #fff, --card-link
#1a56c4, and their dark counterparts in the skin; where a card literal EQUALS
a token the row says so and measures the token), the pre-rebrand navy the
hover popup and the footer still declare (#08406e, #0B5394, #C9D4DB — much of
it dead under the skin's cascade, some of it live), Leaflet's own popup chrome
(#333 on white), the three gap-kind indicators, and --layer-accent, which is
set INLINE per card at runtime and no static gate can read; the skin's OWN
tints (--dst-ink-tint, --dst-raised-hover), which are skin literals rather
than brand tokens and ground the metro menu's focus state — but NOT
--dst-brand-tint-soft, which this list named until 2026-09-12 and which
grounds .dpf-support, whose text is the brand's --faint at 11px reading
2.30:1, so a brand token was going unmeasured behind an exclusion written
about the tint (see skin_grounds); opacity on text (.locate-btn:disabled at 0.6,
.rel-note at 0.7) and color-mix() grounds (.disclaimer, the sub-page pill
hover); and the TEMPLATE style blocks an instance's index.html carries
between the fences (Illinois's .empty-state-lede, its school chips), which
sit outside those five surfaces and were not mapped as a whole — the one
faint pair a completeness critic found in them is in the table. One rule is
DORMANT rather than unmeasured: styles-app's .stub-badge paints #fff on
--accent-warm (2.67:1 in dark), and no module in any instance sets `stub`,
so it has no row until one does. This gate measures the brand. The card
palette is the next gate's subject, and until it exists the one place the
repo has measured it is a comment in styles-hover-responsive.txt, which
records "#8b93a1 measures 3.09:1 and fails AA" as the reason its labels are
#6b7280 — by hand, once, for one file.

TWO PALETTES, AND WHY THE SECOND ONE EARNS ITS CODE. The brand tokens are one
palette; traffic.html declares a second, fifteen colours of its own in its own
<style> block, using not one brand token. It is a districtry page in the
sitemap, so its text is held to the same floors — and nothing measured it. On
2026-09-12 a browser sweep of every text node on all 36 pages found nine
selectors there between 12 and 13px at 2.93:1 and 3.04:1 in light and 4.49:1 in
dark, all from one token, --muted. That token is the page's own, so it was
DARKENED in the same change rather than recorded: the decision the brand
--faint and --muted entries are still waiting on does not arise where one page
owns the value and one page reads it.

A second palette also buys the check the first cannot have. The brand tokens
are painted across five CSS files, so "is this colour measured?" is argued in
prose above, surface by surface. traffic.html's are all in one block, so the
question has a mechanical answer: every colour it declares must be named by a
pair row or listed with a reason, and its first run named --brand and
--mark-ink, declared in all three of the page's blocks and referenced by no
rule. That page also states its dark tier TWICE — once under the attribute and
once under the media query — so every copy after the first must declare the
same tokens with the same values; two hand-kept copies of one value is the
drift class this repo generates files to avoid.

WHAT IT DOES WITH A SHORTFALL. A pair under its floor FAILS, unless it is
recorded in ACCEPTED_SHORTFALLS with the MEASURED ratio, a reason and a date
— the posture check_roster_retention.py takes with ACCEPTED_DROPS and
validate_card_links.py with EXPECTED_UNREACHABLE. An accepted entry is not a
silence: every run prints it, it FAILS if the ratio moves in either direction
(a fix must retire the entry; a regression must not hide behind it), and it
fails if the pair it names stops being tested. The floor is compared against
the UNROUNDED ratio — 4.4986:1 is short, however it prints — and only the
recorded value is compared at two decimals. An entry recorded at
introduction with no decision is marked so, and stays visible until someone
either fixes the token or writes down why not.

Stdlib only.

    python3 scripts/validate_contrast.py            # gate: exit 1 on any failure
    python3 scripts/validate_contrast.py --report   # every pair, both tiers
"""

import argparse
import json
import math
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKENS = os.path.join(REPO_ROOT, "districtry", "tokens", "districtry.tokens.css")
SKIN = os.path.join(REPO_ROOT, "engine", "index.html", "styles-districtry-skin.txt")
TRAFFIC = os.path.join(REPO_ROOT, "traffic.html")

# WCAG 2.x floors by role. `text` is 1.4.3 (AA, normal-size text); `large`
# is the same criterion's relaxation for text >= 24px, or >= 18.66px bold;
# `ui` is 1.4.11 (non-text contrast) for the parts of a component a reader
# must perceive to use it — a button face, an input's border, a focus ring,
# an open/closed indicator. `decorative` is measured and printed and never
# gated: card rules, row dividers and the empty-state stripe carry no
# information a reader needs, and 1.4.11 says so in as many words.
FLOORS = {"text": 4.5, "large": 3.0, "ui": 3.0, "decorative": None}

# (foreground, background, role, where it is painted).
#
# Tokens are CANONICAL names from the token file. The app's alias vocabulary
# maps through build_brand_tokens.ALIASES (--slate-soft is faint, --panel is
# surface, --accent-deep is brand-700); the root pages use these names
# directly. "#fff" is the one literal the skin paints as text — a primary
# button's face — and it is listed because the token file cannot see it.
# `name@under` composites a translucent `name` over the opaque token `under`
# first (see WHERE A GROUND SITS in the docstring).
#
# The `where` column is the evidence: a selector that paints this pair, from
# the surface named. Keep it honest — a row nothing paints is a row that
# should go, and a colour painted with no row here is a colour this gate is
# not measuring. Where a literal in the engine happens to EQUAL a token the
# row says "literal equals token": the measurement is the token's, and the
# literal is the card palette's, which is the next gate's subject.
PAIRS = [
    # — body text on the grounds —
    ("ink",        "surface",    "text", "cards, panels, masthead: header.masthead, .layer-block, .share-popover (skin); the sub-page shell's .answer-card body"),
    ("ink",        "paper",      "text", "app ground: body (styles-app); every root page's body"),
    ("ink",        "surface-2",  "text", ".layer-block-head in DARK only — the skin repaints it #262331 (== --surface-2 dark) under --card-ink #ece9f4 (== --ink dark); in light the head is styles-card-v2's literal #fff (== --surface), so the light half of this row re-measures (ink, surface). The --surface-2 VALUE reaches a light-tier reader through .card-section-label (the muted row below)"),
    ("ink",        "brand-tint", "text", "landing .notice-h and .pill; privacy .tldr (build_landing_page, build_privacy_page — children of body or of an unpainted main, i.e. on --paper)"),
    ("ink",        "brand-tint@surface", "text", "privacy .k inline code inside .card, a --surface panel (build_privacy_page)"),
    ("ink",        "border",     "text", ".gap-suggest:hover — text with the border colour as its ground (styles-footer; the gaps modal is composed outside the hidden footer)"),
    ("ink-2",      "surface",    "text", "history.html .tile-l (build_history_page)"),
    ("ink-2",      "paper",      "text", "history.html .intro, .entry p, code (build_history_page)"),
    ("ink-3",      "surface",    "text", "h1.title small, .masthead-action-link (skin, as --slate); .share-popover-note / -label (styles-app, on the #fff popover); the gaps panel's .gap-area, .gap-detail, .gaps-credit and its group caret .gaps-section-label::before — a state indicator repainted from --line-strong on 2026-09-02 (styles-footer); renderSourceUnavailable paints it from JS"),
    ("ink-3",      "paper",      "text", "sub-page details body, landing h1 at <=560px, .kbd-select-btn (shell, root, styles-app)"),
    ("ink-3",      "surface-2",  "text", "privacy.html thead th at 12px (build_privacy_page)"),
    ("ink-3",      "brand-tint", "text", "landing .notice-b, footer .support (build_landing_page — on body)"),
    ("ink-3",      "border",     "text", ".gap-badge at 10px — text on the border colour (styles-footer)"),
    ("muted",      "surface",    "text", "privacy .masthead h1 small, .which, .footer-inner; coverage-map attribution at 10px"),
    ("muted",      "paper",      "text", "landing .lede, .coverage-caption, .not-yet-list; history .kicker and its scheduled-jobs th at 12px"),
    ("muted",      "surface-2",  "text", ".card-section-label and .card-tinted (styles-card-v2) on --card-section-bg, which the skin sets to --surface-2's value in both tiers, under --card-muted, which equals --muted — literal equals token"),
    ("muted",      "brand-tint", "text", "landing #notice-dismiss at 11.5px (build_landing_page — on body)"),
    ("muted",      "brand-tint@surface", "text", "coverage-map .legend a:hover .mt at 11.5px — the legend is a --surface panel (build_coverage_map)"),

    # — the quiet tier: small labels, meta, placeholders — still TEXT —
    ("faint",      "surface",    "text", ".dst-metro-menu-label 10px, .footer-meta 11px, .title-metro at 40px (large text, whose floor is 3.0 — this row holds the pair to the stricter 4.5 and it clears neither), .hover-foot (skin, as --slate-soft; .hover-foot is the literal #9aa3b2 on literal #fff in light); the app's search placeholder in LIGHT, whose --dst-sunken interior is #ffffff (== --surface); .empty-state-lede 12.5px (il TEMPLATE block); privacy td small 12px; coverage-map .legend h3 11px; landing .pill-n at rest"),
    ("faint",      "paper",      "text", "landing h2 at 15px, .cta-note 13px (build_landing_page, shell); the app's search placeholder in DARK, whose --dst-sunken interior is #15131b (== --paper dark)"),
    ("faint",      "brand-tint", "text", "landing .pill:hover .pill-n at 12px (build_landing_page — on body)"),
    ("faint",      "brand-tint@surface", "text", "privacy.html `td small code.k` at 10.8px — .k sets a background and no colour, so inside the table's small text it inherits --faint and sits on the tint over the --surface card (build_privacy_page). The (ink, brand-tint@surface) row above is the same .k in body prose"),
    ("faint",      "dst-brand-tint-soft@surface", "text", ".dpf-support at 11px on all six app pages (styles-districtry-skin) — the one line in the panel foot a reader is asked to act on, as --slate-soft on the skin's own tint over the --panel foot"),

    # — links and accents as text —
    ("brand-700",  "surface",    "text", "links on panels: .dpf-links a, .sibling-result-hint (skin, as --accent-deep). NOT .dpf-support a — its ground is the skin's own --dst-brand-tint-soft — and NOT footer.site-footer a, which the skin hides"),
    ("brand-700",  "paper",      "text", "links on the app ground; privacy and history `a`; .locate-btn, .btn-secondary (styles-app, styles-footer)"),
    ("brand-700",  "brand-tint", "text", "landing footer .support a:hover (build_landing_page — on body)"),
    ("brand-700",  "brand-tint@surface", "text", "privacy .masthead-actions a:hover — the masthead is a --surface panel (build_privacy_page)"),
    ("brand-700",  "surface-2",  "text", "the UNPRESSED .hover-toggle-btn and .pin-parent-btn in dark: --accent-deep (styles-app) on --dst-raised #262331 (skin), which equals --surface-2 dark — literal equals token"),
    ("brand",      "surface",    "text", "coverage-map attribution links at 10px; .dst-wordmark-link:hover (skin, as --accent)"),
    ("brand",      "paper",      "text", "landing footer a; sub-page summary::after glyph at 24px"),
    ("brand",      "brand-tint", "text", "landing footer .support a (build_landing_page — on body)"),

    # — error state —
    ("error-ink",  "surface",    "text", ".layer-card-body.state-error — styles-card-v2's literal #7c2d12 wins by source order over styles-app's var(--err) and equals --error-ink light; the skin's dark #fdba74 equals --error-ink dark — literal equals token"),
    ("error",      "surface",    "text", "landing .search-status.err at 13.5px (build_landing_page)"),
    ("error",      "surface",    "ui",   ".layer-block:has(> .layer-card-body.state-error) border-left (styles-card-v2 literal == --error; skin dark #f97316 == --error dark)"),

    # — literal white as text: the engine's button faces, on every accent —
    # The token file cannot see these; they are listed because the dark tier
    # lifts every accent to a tint chosen so LINKS read on a dark ground, and
    # the same tokens are BUTTON FACES under white text (the polarity
    # inversion the sub-page reader named). build_landing_page.py already
    # flips its own button to --paper text in dark, and records why.
    ("#fff",       "brand",      "text", ".search-row button (styles-core colour, skin ground), .masthead-actions a.is-primary:hover (shell), .footer-link-btn:hover (skin)"),
    ("#fff",       "brand-700",  "text", ".cta and the RESTING .masthead-actions a.is-primary (shell, on every sub-page), .search-row button:hover, .btn-primary:hover (styles-core) — NOT the pressed/pinned toggles in dark: the skin's later [data-theme=dark] .hover-toggle-btn / .pin-parent-btn rules repaint those on --dst-raised, which is its own defect (see the entry below)"),
    ("paper",      "brand",      "text", "landing .search-button in dark — the flip that HOLDS: build_landing_page records white on #a78bfa = 2.72 and paints --paper instead"),
    ("paper",      "brand-700",  "text", "landing .search-button:hover in dark"),
    ("paper",      "ink",        "text", ".skip-link — the app's (styles-core) and, since 2026-09-02, the sub-page shell's (engine/shared/styles-subpage); the root pages' skip links already painted this pair. Focus-only, and the one masthead element the skin does not restyle"),

    # — UI parts a reader must perceive to use (1.4.11) —
    ("brand-warm", "paper",      "ui",   "--focus-ring: 3px solid var(--accent-warm) on the app ground and every sub-page summary"),
    ("brand-warm", "surface",    "ui",   "focus ring on a card or the masthead; .group-safety .dot"),
    ("brand",      "surface",    "ui",   "focused input border: .masthead .search-row input:focus (skin); .group-political .dot; the landing .search-input / .search-button rings inside .search-card"),
    ("brand",      "paper",      "ui",   "focus rings on the page ground: privacy :focus-visible on body links (build_privacy_page); landing .pill:focus-visible, drawn outside the pill over .pills, which has no background (build_landing_page)"),
    ("data-500",   "surface",    "ui",   "legend dot / selected-boundary swatch: .dml-dot (skin; literals #1d5fd6 / #6ea8ff equal the token's two tiers)"),
    ("border@paper", "surface",  "ui",   "the masthead search input's RESTING border, composited over its own interior (--dst-sunken: #ffffff in light, where --border is opaque anyway; #15131b == --paper in dark) and seen against the --panel masthead — 1.4.11's text-input case, where the boundary is the field's only indicator once a reader types"),

    # — decorative: measured, printed, never gated —
    # border-dot outlines LABELLED controls; 1.4.11 holds a boundary to 3:1
    # only where it is what identifies the component, and these carry text.
    # One caveat is recorded rather than argued away: the shell's masthead
    # pills carry text-decoration: none and the same --slate as the subtitle
    # beside them, so the border is what says "this is a link" — a 1.4.1
    # Use-of-Colour question the 1.4.11 exemption does not answer.
    ("border-dot", "surface",    "decorative", "outlined labelled controls: .dst-metro-menu (skin) and the shell's .masthead-actions a, as --line-strong; .school-chip (il TEMPLATE)"),
    ("border",     "paper",      "decorative", "landing .search-card, sub-page details rules"),
    ("border-soft","surface",    "decorative", "row rules; privacy th/td rules"),
    ("empty",      "surface",    "decorative", "empty-state stripe: .layer-block:has(> .layer-card-body.state-empty) border-left"),
]

# A shortfall someone has looked at. Keyed (fg, bg, role, tier) — the role
# too, because one (fg, bg) can be painted as text in one place and as a UI
# part in another, at different floors. `measured` is the ratio on the day
# it was recorded, to two decimals, and the gate FAILS if the live value
# differs — a fix retires the entry, a regression cannot shelter under it.
# `decided` is False for the ones recorded at introduction: they are
# measured, visible on every run, and awaiting either a token change or a
# written reason. Nothing here is a threshold being lowered; the floor is the
# floor, and this is the list of places the palette is known not to meet it.
ACCEPTED_SHORTFALLS = {
    # (a) --faint: one token, one decision, six grounds. For it to clear
    # 4.5:1 on the paper ground it must become #696f79, which is DARKER than
    # --muted #6b7280 — the quiet tier cannot stay quiet and meet AA on every
    # ground. The decision is which: darken the ramp, or move the 10-15px
    # text off --faint (menu labels, footer meta, placeholders, the landing
    # page's own h2) onto --muted / --ink-3 and keep --faint for large text
    # and decoration. The app's legend chevron (.dml-kicker, currentColor at
    # opacity .8) rides the same token as an open/closed indicator, so a
    # decision to move small text off --faint should take the chevron with it.
    ("faint", "surface", "text", "light"): dict(
        measured=2.54, decided=False, date="2026-09-02",
        reason="#9aa3b2, luminance 0.363 against a 0.183 ceiling for 4.5:1 on "
               "white; recorded at the gate's introduction — the token predates it"),
    ("faint", "paper", "text", "light"): dict(
        measured=2.28, decided=False, date="2026-09-02",
        reason="same token on the app ground, whose ceiling is 0.159 — this is "
               "the landing page's h2 at 15px"),
    ("faint", "brand-tint", "text", "light"): dict(
        measured=2.15, decided=False, date="2026-09-02",
        reason="same token on the landing page's pill tint at 12px"),
    ("faint", "surface", "text", "dark"): dict(
        measured=3.40, decided=False, date="2026-09-02",
        reason="#746e86 clears the 3:1 large-text bar and not the 4.5:1 text bar"),
    ("faint", "paper", "text", "dark"): dict(
        measured=3.78, decided=False, date="2026-09-02",
        reason="same token on the dark app ground"),
    ("faint", "brand-tint", "text", "dark"): dict(
        measured=2.96, decided=False, date="2026-09-02",
        reason="same token on the dark pill tint over the body — under even the 3:1 bar"),
    # The two grounds this gate could not see until 2026-09-12. Both were
    # found by measuring every text node in a browser, which is the check the
    # pair table cannot be: the table's row for each ground existed for
    # --muted and --ink and not for --faint, so a tint with faint text on it
    # read as covered. Neither is a new defect and neither is a new decision —
    # they are two more grounds under entry (a)'s one token. Three of the four
    # ratios here sit one hundredth off the browser sweep's figure (2.61, 2.75,
    # 2.29) because that sweep read the unrounded composite and this gate
    # rounds to 8 bits first; the painted pixel is the 8-bit one, so these are
    # the values recorded.
    ("faint", "brand-tint@surface", "text", "light"): dict(
        measured=2.15, decided=False, date="2026-09-12",
        reason="privacy.html's `td small code.k`: light --brand-tint is opaque, so "
               "this is the same 2.15 as the pill tint above, on a different page"),
    ("faint", "brand-tint@surface", "text", "dark"): dict(
        measured=2.60, decided=False, date="2026-09-12",
        reason="the same .k in dark, where --brand-tint is rgba(167,139,250,0.16) "
               "over the --surface card rather than over the body"),
    ("faint", "dst-brand-tint-soft@surface", "text", "light"): dict(
        measured=2.30, decided=False, date="2026-09-12",
        reason=".dpf-support at 11px, on the skin's own rgba(109,63,209,0.07) over "
               "the white panel foot"),
    ("faint", "dst-brand-tint-soft@surface", "text", "dark"): dict(
        measured=2.76, decided=False, date="2026-09-12",
        reason="the same line in dark, rgba(167,139,250,0.13) over --surface"),
    # (b) --muted misses by a step on the tinted grounds and clears --surface.
    ("muted", "paper", "text", "light"): dict(
        measured=4.32, decided=False, date="2026-09-02",
        reason="#6b7280 (luminance 0.167) on the paper ground, whose ceiling for "
               "4.5:1 is 0.159; #686f7c clears both grounds (4.52 on paper) — a "
               "one-step darkening"),
    ("muted", "brand-tint", "text", "light"): dict(
        measured=4.08, decided=False, date="2026-09-02",
        reason="same token on the landing page's pill tint, at 11.5px"),
    ("muted", "brand-tint@surface", "text", "light"): dict(
        measured=4.08, decided=False, date="2026-09-02",
        reason="the coverage-map legend's hover: light --brand-tint is opaque, so "
               "the ground under it changes nothing here"),
    ("muted", "brand-tint@surface", "text", "dark"): dict(
        measured=4.33, decided=False, date="2026-09-02",
        reason="the same hover in dark, where --brand-tint is rgba(167,139,250,0.16) "
               "over the legend's --surface panel — the pair the first draft of this "
               "gate passed at 4.94:1 by compositing over --paper instead"),
    # (c) White on the dark accents: the polarity inversion. The dark tier
    # lifts every accent to a tint chosen so LINKS read on a dark ground, and
    # the engine paints the same tokens as BUTTON FACES under literal #fff.
    # The fix exists in-repo — build_landing_page.py flips its button to
    # --paper text in dark and records why — and porting it to styles-core's
    # button rules is a visible change on every instance's dark mode, so it
    # is recorded here rather than made.
    # (e) The same tokens' PRESSED states are a separate, unmeasured defect:
    # in dark the skin repaints .hover-toggle-btn[aria-pressed=true] and
    # .pin-parent-btn.is-pinned on --dst-raised, so the pressed fill is lost
    # and pressed differs from unpressed only by text colour — 1.4.11 asks
    # the state indicator itself to be perceivable. Restoring the fill would
    # put #fff back on --brand-700 at 1.91:1, so both halves are one decision.
    ("#fff", "brand", "text", "dark"): dict(
        measured=2.72, decided=False, date="2026-09-02",
        reason="white on --accent #a78bfa: the search button, the primary "
               "masthead action, the footer-link hover — --paper on the same "
               "ground reads ~6.8:1"),
    ("#fff", "brand-700", "text", "dark"): dict(
        measured=1.91, decided=False, date="2026-09-02",
        reason="white on --accent-deep #c4b0ff: the search button's HOVER, the "
               "sub-page .cta and its resting primary action, the primary "
               "button's hover — 'deep' means more contrast against the ground, "
               "which on a dark ground is LIGHTER, and white text on it is the "
               "worst pair in the palette"),
    # (d) The text-input case, which the first draft argued out of 1.4.11 and
    # the review argued back in: the placeholder is --faint at 2.54:1, so it
    # is not a perceivable indicator under 1.4.11's own floor, and it vanishes
    # the moment a reader types, leaving the border as the only thing that
    # says where the field is. --border-dot would not clear it either (1.69);
    # a >= 3:1 border (--muted reads 4.83 on white) or a visibly sunken
    # interior would.
    ("border@paper", "surface", "ui", "light"): dict(
        measured=1.23, decided=False, date="2026-09-02",
        reason="the masthead search input's resting border, opaque #e8e7ef on the "
               "white masthead; the input's interior is white too"),
    ("border@paper", "surface", "ui", "dark"): dict(
        measured=1.14, decided=False, date="2026-09-02",
        reason="the same border, rgba(236,233,244,0.1) over the input's #15131b "
               "interior, against the #201d29 masthead; the interior itself "
               "reads 1.11:1 against the masthead, so neither edge is perceivable"),
}

# ——— traffic.html's own palette ———
#
# The traffic report declares fifteen colour tokens of its own in its <style>
# block and uses not one brand token. It is a districtry page in the sitemap,
# so its text is held to the same floors; it is not the brand surface, so it
# gets its own table rather than rows in the one above. What a second palette
# buys is the completeness check the brand table cannot have: this page's
# tokens are all in one block, so every one of them must be NAMED by a row
# below or listed in TRAFFIC_NOT_PAINTED with a reason, and adding a token
# without a row fails.
#
# Measured 2026-09-12, which is how this page got into the gate: a browser
# sweep of every text node on all 36 pages found nine selectors here between
# 12 and 13px at 2.93:1 and 3.04:1 in light and 4.49:1 in dark, against a
# 4.5:1 floor, with nothing measuring them. The cause was --muted #8a949b /
# #77828a. That token is this page's alone, so it was DARKENED to #6b737b /
# #7b868e in the same change rather than recorded as a shortfall — the
# decision the brand --faint and --muted entries above are still waiting on
# does not arise where one page owns the value.
TRAFFIC_PAIRS = [
    ("ink",         "plane",       "text", "body, and .backlink a:hover — .wrap paints nothing, so the page ground is --plane"),
    ("ink",         "surface",     "text", ".caveat strong, .note strong, .meter-label b, .barrow .name 13px, td:first-child — all inside .card or .caveat, which paint --surface"),
    ("ink-2",       "plane",       "text", ".eyebrow 11px, .period 14px, .backlink a 13px, footer .standing a 12.5px"),
    ("ink-2",       "surface",     "text", ".caveat 13.5px, .tile .sub 12.5px, .card .sub 13px, .legend 13px, .bar value 12.5px, .note 13px, .empty code 12px, .meter-label 13px, summary 13px, td"),
    ("muted",       "plane",       "text", "footer 12.5px"),
    ("muted",       "surface",     "text", ".tile .label 12px, th 12px, .muted-note, .empty 13px — the nine selectors the browser sweep found short"),
    ("tooltip-ink", "tooltip-bg",  "text", ".tooltip 12.5px, which inverts the tiers: the light tier's tooltip is the dark ink ground"),
    ("s1",          "surface",     "ui",   "the page-visit series: .barrow .bar and the daily chart's columns on a --surface card, the .legend .swatch that names the series, and .hitcol:focus-visible's 2px outline"),
    ("s1",          "s1-track",    "ui",   ".meter .fill against its own track — the meter has no number beside the bar, so the fill's edge is what states the value"),
    ("s2",          "surface",     "ui",   "the interaction series: the chart's second column and its .legend .swatch and .tooltip .dot"),
    # Gridlines are the 1.4.11 exemption the criterion spells out: the marks
    # that carry the data are gated above, and a reader needs no gridline to
    # read a bar's length or a column's height. --baseline is the t === 0
    # line, the darkest member of the same set (1.58:1 light, 1.70:1 dark).
    ("baseline",    "surface",     "decorative", "the chart's zero line, drawn by the same gridline loop at t === 0"),
    ("grid",        "surface",     "decorative", "chart gridlines; th/td rules; .subpanel's top rule"),
    ("ring@plane",  "surface",     "decorative", "the 1px box-shadow outline round .caveat, .tile and .card, composited over the --plane it is drawn on and seen against the card it encloses"),
]

# Declared and painted nowhere. Empty, and that is the measurement: --brand
# #6d3fd1 / #8b63e0 and --mark-ink #ffffff / #16191c were declared in all
# three of this page's blocks and referenced by no rule, so this check's first
# run named them and they were deleted. The theme-color meta tag carries the
# brand hex as its own literal, which is where that value is actually used.
TRAFFIC_NOT_PAINTED = {}

# Empty after the --muted darkening above. An entry here takes the same shape
# as ACCEPTED_SHORTFALLS and is audited the same way.
TRAFFIC_SHORTFALLS = {}

problems = []
warnings = []


class Unresolvable(Exception):
    """A var() chain the resolver cannot follow — deeper than its cap, or
    cyclic. Distinct from a missing token so the report names the cause."""


def fail(msg):
    print("validate-contrast: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def token_block(css, selector, path=TOKENS):
    """The same shape build_brand_tokens.py reads, so the two cannot disagree
    about what a block is. Comments are stripped first — the token file
    annotates values with '(was #e8eaef)' remarks, one edit from a
    commented-out declaration that would otherwise win as the last match —
    and a token declared twice in one block is a failure, not a last-wins.

    The block's END is found by matching braces, not by looking for a `}` in
    the first column. The token file's blocks close there and the two other
    files this gate now reads do not: the skin block is indented two spaces
    inside its fence, and traffic.html's three are indented inside a <style>.
    A column-anchored reader silently ran past the end of both.

    The selector must be followed by whitespace and `{`, which is what keeps
    `:root` from matching `:root[data-theme="dark"]` or `:root … .mk-blend`.

    Comments go before the braces are counted, not after, so a `{` inside a
    comment cannot move the end of the block. `css` must therefore be CSS:
    traffic.html's <style> contents are sliced out by the caller rather than
    the whole document handed over, because that document's <script> is full
    of braces this reader has no business counting."""
    rel = os.path.relpath(path, REPO_ROOT)
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    m = re.search(re.escape(selector) + r"\s*\{", css)
    if not m:
        fail("no %r block in %s" % (selector, rel))
    depth, i = 0, m.end() - 1
    for i in range(m.end() - 1, len(css)):
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
            if depth == 0:
                break
    else:
        fail("%r block in %s is never closed" % (selector, rel))
    pairs = re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", css[m.end():i])
    seen = {}
    for k, v in pairs:
        if k in seen:
            fail("%s declares %s twice in %s — which value is current?"
                 % (rel, k, selector))
        seen[k] = v.strip()
    return seen


def resolve(table, name, depth=0):
    """Follow var() indirection to a colour. The token file uses one level
    (--brand is var(--brand-600)); allowing a few more costs nothing and
    means a future ramp alias cannot silently read as unresolved. A var()
    fallback is honoured when its target is missing."""
    if depth > 5:
        raise Unresolvable("var() chain deeper than 5 (or cyclic) at --%s" % name)
    v = table.get("--" + name)
    if v is None:
        return None
    m = re.fullmatch(r"var\((--[a-z0-9-]+)(?:\s*,\s*(.+))?\)", v.strip())
    if not m:
        return v
    target = resolve(table, m.group(1)[2:], depth + 1)
    if target is None and m.group(2):
        return m.group(2).strip()
    return target


def _channel(p):
    v = float(p[:-1]) * 255.0 / 100.0 if p.endswith("%") else float(p)
    if not math.isfinite(v) or v < 0 or v > 255:
        raise ValueError(p)
    return v


def _alpha(p):
    v = float(p[:-1]) / 100.0 if p.endswith("%") else float(p)
    if not math.isfinite(v) or v < 0 or v > 1:
        raise ValueError(p)
    return v


def parse_color(v):
    """-> (r, g, b, a) with channels 0-255 and alpha 0-1. Hex in 3, 4, 6 or 8
    digits; rgb()/rgba() in the comma form or the CSS Color 4 space form with
    an optional `/ alpha`, channels as numbers or percentages, every value
    range-checked and finite. Anything else — a named colour, hsl(), a
    color-mix(), a hybrid of the two rgb syntaxes, an out-of-range channel —
    is a colour this gate cannot measure, which is a failure rather than a
    skip: a NaN that slipped through would compare False against every floor
    and read as 'ok'."""
    s = v.strip().lower()
    if s.startswith("#"):
        h = s[1:]
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) not in (6, 8) or not re.fullmatch(r"[0-9a-f]+", h):
            return None
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        a = int(h[6:8], 16) / 255.0 if len(h) == 8 else 1.0
        return (r, g, b, a)
    m = re.fullmatch(r"rgba?\((.*)\)", s)
    if not m:
        return None
    inner = m.group(1).strip()
    if "," in inner:
        if "/" in inner:
            return None
        parts = [p.strip() for p in inner.split(",")]
    elif "/" in inner:
        chans, _, alpha = inner.partition("/")
        parts = chans.split() + [alpha.strip()]
    else:
        parts = inner.split()
    if len(parts) not in (3, 4) or any(not p for p in parts):
        return None
    try:
        r, g, b = (_channel(p) for p in parts[:3])
        a = _alpha(parts[3]) if len(parts) == 4 else 1.0
    except ValueError:
        return None
    return (r, g, b, a)


def composite(fg, bg):
    """Source-over: what the eye sees when a translucent colour sits on an
    opaque one. The result is opaque by construction, and its channels are
    rounded to 8 bits, because the painted pixel is 8-bit — a recorded ratio
    should be one a screenshot or DevTools can reproduce, and on four of the
    five dark composited pairs the float and the 8-bit value differ at two
    decimals."""
    r, g, b, a = fg
    R, G, B, _ = bg
    return (round(r * a + R * (1 - a)), round(g * a + G * (1 - a)),
            round(b * a + B * (1 - a)), 1.0)


def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(c):
    """WCAG relative luminance: the sRGB transfer function per channel, then
    the Rec. 709 weights. This is the same _srgb_to_lin that
    build_dark_map_palette.py uses on the way into OKLCH."""
    return 0.2126 * _lin(c[0]) + 0.7152 * _lin(c[1]) + 0.0722 * _lin(c[2])


def contrast(fg, bg):
    """(L1 + 0.05) / (L2 + 0.05), lighter over darker. A RATIO of two
    colours — a single colour has no contrast, which is the mistake a
    reference this gate was measured against had made."""
    l1, l2 = luminance(fg), luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def tiers(css, path, light_sel, dark_sels):
    """Light is the light selector's block as written. Dark is that block with
    each dark block laid over it — the cascade's own answer, so a token the
    dark block does not redefine (every --brand-N00 ramp step, the spacing and
    layer tokens) keeps its light value here exactly as it does in the browser.

    `dark_sels` is a list because a page can state its dark tier TWICE: the
    token file is consumed by a `[data-theme="dark"]` attribute alone, while
    traffic.html hand-writes the same 13 values under the attribute and again
    under `@media (prefers-color-scheme: dark)`. Two hand-kept copies of one
    value is the drift class this repo generates files to avoid, so every copy
    after the first must declare exactly the same tokens with exactly the same
    values; a difference fails rather than being resolved by order."""
    light = token_block(css, light_sel, path)
    first = None
    for sel in dark_sels:
        block = token_block(css, sel, path)
        if first is None:
            first, first_sel = block, sel
        elif block != first:
            only = set(block) ^ set(first)
            moved = ["%s: %s vs %s" % (k, first[k], block[k])
                     for k in sorted(set(block) & set(first)) if block[k] != first[k]]
            fail("%s states its dark tier twice and the copies disagree — %r vs %r: %s"
                 % (os.path.relpath(path, REPO_ROOT), first_sel, sel,
                    "; ".join(moved + ["only in one copy: " + ", ".join(sorted(only))]
                              if only else moved)))
    dark = dict(light)
    dark.update(first)
    return {"light": light, "dark": dark}


def colour_of(table, spec, under):
    """Resolve a token (or a literal) to an opaque colour. `spec` may carry
    `@under-token`, which names the opaque ground a translucent value sits
    on; otherwise `under` (the caller's ground) is used. Returns
    (colour, None) or (None, why)."""
    name, _, at = spec.partition("@")
    if at:
        under, err = colour_of(table, at, None)
        if err:
            return None, "ground under %s: %s" % (spec, err)
    try:
        raw = name if name.startswith("#") or name.startswith("rgb") else resolve(table, name)
    except Unresolvable as e:
        return None, str(e)
    if raw is None:
        return None, "no token --%s" % name
    c = parse_color(raw)
    if c is None:
        return None, "--%s is %r, which this gate cannot parse" % (name, raw)
    if c[3] < 1.0:
        if under is None:
            return None, "--%s is translucent (%s) and nothing names its ground" % (name, raw)
        c = composite(c, under)
    return c, None


def measure(table, tier, pairs, body_ground, label):
    """-> list of rows: (fg, bg, role, ratio, floor, status, where). `ratio`
    is the unrounded value; callers round for display.

    `body_ground` is the token a translucent value with no `@` sits on: the
    brand palette's body is --paper and traffic.html's is --plane. It was
    hardcoded while there was one palette."""
    rows = []
    paper, err = colour_of(table, body_ground, None)
    if err:
        fail("%s %s tier: %s" % (label, tier, err))
    for fg, bg, role, where in pairs:
        # a translucent GROUND with no `@` sits on the body ground
        ground, err = colour_of(table, bg, paper)
        if err:
            problems.append("%s %s tier: background %s" % (label, tier, err))
            continue
        fore, err = colour_of(table, fg, ground)
        if err:
            problems.append("%s %s tier: foreground %s" % (label, tier, err))
            continue
        ratio = contrast(fore, ground)
        floor = FLOORS[role]
        status = "ok"
        if floor is not None and ratio < floor:
            status = "short"
        rows.append((fg, bg, role, ratio, floor, status, where, fore[:3], ground[:3]))
    return rows


def judge(rows_by_tier, accepted, label, table_name):
    """Apply a palette's accepted shortfalls. Every accepted entry must name a
    pair that is still tested and still short by exactly the recorded amount."""
    seen = set()
    for tier, rows in rows_by_tier.items():
        for fg, bg, role, ratio, floor, status, where, _f, _g in rows:
            key = (fg, bg, role, tier)
            acc = accepted.get(key)
            shown = round(ratio, 2)
            if status == "short":
                if acc is None:
                    problems.append(
                        "%s %s: %s on %s (%s) is %.2f:1, floor %.1f — %s"
                        % (label, tier, fg, bg, role, shown, floor, where))
                else:
                    seen.add(key)
                    if abs(acc["measured"] - shown) > 0.005:
                        problems.append(
                            "%s %s: %s on %s (%s) is %.2f:1 but %s records %.2f — the "
                            "palette moved; re-measure and re-decide, or retire the entry"
                            % (label, tier, fg, bg, role, shown, table_name, acc["measured"]))
                    else:
                        warnings.append(
                            "%s %s: %s on %s (%s) %.2f:1 < %.1f — accepted %s%s: %s"
                            % (label, tier, fg, bg, role, shown, floor, acc["date"],
                               "" if acc["decided"] else ", NOT YET DECIDED",
                               acc["reason"]))
            elif acc is not None:
                seen.add(key)
                problems.append(
                    "%s %s: %s on %s (%s) now measures %.2f:1 and clears its floor — "
                    "retire its %s entry (recorded %.2f)"
                    % (label, tier, fg, bg, role, shown, table_name, acc["measured"]))
    for key in accepted:
        if key not in seen:
            problems.append(
                "%s names %s on %s as %s (%s), which no pair in the %s table tests — "
                "an accepted shortfall must stay measured"
                % ((table_name,) + key + (label,)))


def report(rows_by_tier, label):
    for tier, rows in rows_by_tier.items():
        print("\n%s — %s tier" % (label, tier.upper()))
        print("  %-14s %-28s %-11s %7s %6s  %s" % ("fg", "bg", "role", "ratio", "floor", "status"))
        for fg, bg, role, ratio, floor, status, where, _f, _g in rows:
            fl = "%.1f" % floor if floor is not None else "—"
            print("  %-14s %-28s %-11s %6.2f:1 %6s  %s" % (fg, bg, role, ratio, fl, status))


def skin_grounds(table, tier):
    """The skin's own tints, read from the skin rather than retyped here.

    --dst-brand-tint-soft grounds .dpf-support, whose text is the brand's
    --faint, and the docstring above used to name that tint as something this
    gate does not measure. That was the right call about the TINT and the wrong
    one about the TEXT on it: a brand token at 11px reading 2.29:1 is this
    gate's subject wherever it is painted. So the --dst-* names join the tier
    table and a pair row can say `dst-brand-tint-soft@surface`.

    They are read, not copied, so changing the skin changes the measurement.
    A collision with a brand token name fails: the skin also declares --ink,
    --paper and --panel with the brand's own values, and letting the skin's
    copy win here would make this gate measure the skin where it claims to
    measure the brand."""
    css = read(SKIN)
    sel = ":root" if tier == "light" else ':root[data-theme="dark"]'
    block = token_block(css, sel, SKIN)
    out = dict(table)
    for k, v in block.items():
        if not k.startswith("--dst-"):
            continue
        if k in out:
            fail("%s declares %s, which the brand token file also declares — "
                 "one name, two values" % (os.path.relpath(SKIN, REPO_ROOT), k))
        out[k] = v
    return out


def traffic_css():
    """traffic.html's <style> contents. The document's <script> builds the
    chart and is full of braces, so the block reader is handed the CSS alone
    (see token_block)."""
    html = read(TRAFFIC)
    m = re.search(r"<style[^>]*>(.*?)</style>", html, re.S)
    if not m:
        fail("%s has no <style> block" % os.path.relpath(TRAFFIC, REPO_ROOT))
    return m.group(1)


# Each palette: its label, the CSS it is read from, the selectors for its two
# tiers, the token a translucent value with no `@` sits on, its pair table,
# its accepted shortfalls, and — where every colour it declares lives in one
# block — the completeness check.
PALETTES = [
    dict(label="brand", css=lambda: read(TOKENS), path=TOKENS,
         light=":root", dark=['[data-theme="dark"]'], body="paper",
         pairs=PAIRS, accepted=ACCEPTED_SHORTFALLS,
         accepted_name="ACCEPTED_SHORTFALLS",
         extra=skin_grounds,
         # The brand table's completeness is argued in the docstring, surface
         # by surface, because its tokens are painted across five CSS files
         # and a name-by-name check would demand a row for every ramp step,
         # spacing value and map-layer colour.
         complete=None, not_painted=None),
    dict(label="traffic", css=traffic_css, path=TRAFFIC,
         light=":root", dark=[':root[data-theme="dark"]',
                              ':root:not([data-theme="light"])'],
         body="plane",
         pairs=TRAFFIC_PAIRS, accepted=TRAFFIC_SHORTFALLS,
         accepted_name="TRAFFIC_SHORTFALLS",
         extra=None,
         complete=True, not_painted=TRAFFIC_NOT_PAINTED),
]


def check_complete(table, pairs, not_painted, label, path):
    """Every colour token the palette declares must be named by a pair row —
    as a foreground, a background, or the ground after an `@` — or listed in
    the palette's not-painted table with a reason.

    This is the check the brand table cannot have and the reason a second
    palette is worth its code: traffic.html's fifteen tokens are all in one
    block, so "is this colour measured?" has a mechanical answer. Its first run
    named --brand and --mark-ink, declared in all three of the page's blocks
    and referenced by no rule."""
    named = set()
    for fg, bg, _role, _where in pairs:
        for spec in (fg, bg):
            for part in spec.split("@"):
                named.add("--" + part)
    rel = os.path.relpath(path, REPO_ROOT)
    for name, value in sorted(table.items()):
        if parse_color(value) is None:
            continue                      # not a colour: a length, a font stack
        if name in named or name[2:] in not_painted:
            continue
        problems.append(
            "%s declares %s: %s and no pair row names it — add a row, or record it "
            "in the palette's not-painted table with a reason" % (rel, name, value))
    for name, reason in sorted(not_painted.items()):
        if ("--" + name) not in table:
            problems.append(
                "the %s palette records --%s as painted nowhere (%s) and %s no longer "
                "declares it — drop the entry" % (label, name, reason, rel))
        elif ("--" + name) in named:
            problems.append(
                "the %s palette records --%s as painted nowhere (%s) and a pair row "
                "now names it — drop the entry" % (label, name, reason))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true",
                    help="print every pair's ratio in both tiers, per palette")
    ap.add_argument("--check", action="store_true",
                    help="accepted for symmetry with the other gates; the bare run is the check")
    ap.add_argument("--json", action="store_true",
                    help="print every measured pair as JSON, with the 8-bit colours it "
                         "resolved to — what scripts/probe_contrast_pairs.mjs joins a "
                         "browser's own measurements against")
    args = ap.parse_args()

    totals = []
    emitted = []
    for pal in PALETTES:
        css = pal["css"]()
        by_tier = {}
        for tier, table in tiers(css, pal["path"], pal["light"], pal["dark"]).items():
            if pal["extra"]:
                table = pal["extra"](table, tier)
            by_tier[tier] = measure(table, tier, pal["pairs"], pal["body"], pal["label"])
            if pal["complete"] and tier == "light":
                check_complete(table, pal["pairs"], pal["not_painted"],
                               pal["label"], pal["path"])
        judge(by_tier, pal["accepted"], pal["label"], pal["accepted_name"])
        for tier, rows in by_tier.items():
            for fg, bg, role, ratio, floor, status, where, f, g in rows:
                emitted.append(dict(
                    palette=pal["label"], tier=tier, fg=fg, bg=bg, role=role,
                    ratio=round(ratio, 2), floor=floor, status=status, where=where,
                    rgb_fg=[int(v) for v in f], rgb_bg=[int(v) for v in g]))
        if args.report:
            report(by_tier, pal["label"])
        totals.append(pal)

    if args.json:
        print(json.dumps(emitted, indent=1))
        return

    if args.report:
        print()

    for w in warnings:
        print("  ~ " + w)
    if problems:
        for p in problems:
            print("  - " + p, file=sys.stderr)
        fail("%d problem(s): a pair below its floor, a recorded ratio that moved, "
             "or a declared colour nothing measures" % len(problems))

    n_pairs = sum(len(p["pairs"]) for p in totals)
    n_gated = sum(1 for p in totals for _fg, _bg, role, _w in p["pairs"]
                  if FLOORS[role] is not None)
    n_acc = sum(len(p["accepted"]) for p in totals)
    n_open = sum(1 for p in totals for a in p["accepted"].values() if not a["decided"])
    print("validate-contrast: OK — %d pair(s) across %d palette(s) measured in 2 tiers, "
          "%d gated; %d accepted shortfall(s)%s"
          % (n_pairs, len(totals), n_gated, n_acc,
             ", %d awaiting a decision" % n_open if n_open else ""))


if __name__ == "__main__":
    main()
