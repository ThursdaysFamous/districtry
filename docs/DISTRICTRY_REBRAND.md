# districtry rebrand — decision record & staged rollout

**What this is.** The record for the *districtry* rebrand: the decisions that carried it, the
staged rollout plan, and the fix-list the package still owes before production adoption. The
reviewable package itself is deployed as an **unlisted preview at `/districtry/`** on the live
site (a new root directory ships automatically with the Pages deploy; `docs/` never ships, which
is why this file lives here and the preview does not).

**Hiddenness contract.** The preview is unlinked from the app, carries
`<meta name="robots" content="noindex, nofollow">` on every page, and stays out of
`sitemap.xml`. Deliberately **no** `robots.txt` `Disallow` — that would advertise the path while
preventing crawlers from ever reading the noindex. The repo is public, so this is soft-hidden:
the files are visible in the GitHub tree regardless. Accepted.

## Decisions of record

- **Name:** *districtry* (district + directory) — never "Districtory". One indivisible lowercase
  word; instance tag suffix in Barlow Condensed 400 at 80%. **The tag is the TWO-LETTER
  code, lowercase — `districtry / il`** (operator-directed 2026-08-20, superseding the brand
  spec's spelled-out `/ illinois` example). Every future state uses its own code the same way;
  the canvas still shows the old form and owes this correction on the next sync.
- **Mark:** 5c — geometric lowercase *d* (ring + ascender, never typeset) over three translucent
  irregular polygons whose fills echo the map's layer encoding (brand violet #6d3fd1, data blue
  #1d5fd6, municipality magenta #b0316e). Multiply blends on light, screen on dark; flat
  one-polygon fallback below 24px. Full spec: `/districtry/Districtry Brand Spec.dc.html`.
- **Color, three tiers** (`/districtry/tokens/districtry.tokens.css`): **brand violet = chrome
  only** (buttons, links, pills, checked states — never map data); **chrome neutrals** = warm
  paper + inks; **data tier = map only** (blue #1d5fd6 selection/marker + per-layer colors).
  The current card system's `--card-accent #1d5fd6` *is* the data tier — the tokens keep the
  same hex on purpose; the rebrand moves interface chrome off blue so chrome and data never
  collide.
- **Type & spacing:** adopted from the bundled *Industry* design system — Barlow Condensed 600
  headings over Barlow body; card metrics keep the proven card-system values (16 / 14.5 /
  12.5px).
- **Positioning:** fleet-by-state, Illinois first; metro instances ride subdomains under one
  brand. Domain migration to districtry.com **is planned** (operator confirmed) and is the last,
  independent rollout phase.

## Provenance (package ↔ repo)

Package `districtry_rebrand_refinement.zip`, rebuilt 2026-08-19 from this repo's ground truth
(sync record `github.md`, not committed — its content is this table):

| Deliverable | Built from |
|---|---|
| `Districtry App.dc.html` | `docs/design_handoff_card_system/Info Card Explorations.dc.html`, `docs/CARD_RENDER_API.md`, `sw.js`, `README.md`, `data/app/metro-outline.json` |
| `Districtry Brand Spec.dc.html` | card-handoff layer colors, `metros.json` |
| `Districtry Logo Wireframes.dc.html` | brand work; layer colors from the card handoff |
| `tokens/districtry.tokens.css` | card-handoff chrome grays + card metrics |

Not committed from the package: `icons/icon-192/512.png` and `og-image.png` (byte-identical
copies of the *current* brand, reference only), `data/app/metro-outline.json` (byte-identical
duplicate — the App canvas now fetches `../data/app/metro-outline.json` so its coverage map
tracks reality), `.thumbnail`, `github.md`.

## Functionality scope (operator decisions, 2026-08-20)

Everything the mockup shows that **already exists** in the app is *maintained* by the redesign —
verified existing: CARTO `light_all` basemap (identical tile URL, index.html:3255), the layer
toggle checkbox in the card header, the offices `<details>` accordion (`renderOfficeGroup`),
"Pin as parent" + relationship outlines, Copy link, hash permalinks, per-card
loading/empty/error states. **The single truly-new function is dark mode** (+ theme toggle,
`dark_all` basemap, dark icon variants, theme persistence) — zero dark-mode support exists
today; it is **deferred to its own approval** and is *not* part of Stage B or the base adoption.
The "N of 39 layers on" label is presentation of existing state — in scope as re-skin.

## Stage log

- **STAGE B IS ADOPTED — the skin is the app (2026-08-24, R4.2).** The preview and its builder
  are DELETED: `scripts/build_districtry_preview.py` (2,440 lines) and `districtry-app.html`
  (27,331 lines). A preview earns its keep until the thing it previews exists, and it did — every
  design decision recorded below was reviewed there before it shipped here.
  **What adoption changed about the plan.** The preview's 43 exactly-once transforms did not port
  one-for-one. The head hunks were almost entirely preview *de*-productionisation (analytics
  stripped, `noindex`, OG and JSON-LD removed) and were skipped. The palette became worksheet
  data rather than island CSS, because R1's `brand-palette` region already emitted those four
  accents — restating them would have been two copies of one fact. Fonts self-host through
  `build_fonts.py`, which is what this document always said production would do, and the
  metric-matched fallback had to be RECALIBRATED: those four percentages are tuned to one
  typeface, and carrying Inter's forward would have left an Arial shaped like Inter standing in
  for Barlow. The dark map palette became a generator with a `--check` instead of an inlined
  literal, because a derived table with a live source must not be a second copy of it.
  **Two things the preview got wrong for production, found by adopting it.** Its CSS hides the
  document footer, where three elements the boot script binds by id live — the verified date, the
  feedback button and the fleet links — so adopting the CSS without the relocation transform
  would have retired all three in one rule while every gate stayed green. And it hides the
  in-page FAQ in favour of a `districtry-faq.html` that never shipped, still linked the preview,
  and referenced assets that do not resolve from `il/`; the in-page FAQ is what is live and
  indexed today, so that hide is NOT adopted. Giving the FAQ its own page remains the better end
  state — deferred, not abandoned.
  **Dark mode shipped with it** rather than waiting for a separate approval, at the operator's
  direction. It is gated in CI by four smoke assertions, and the one that checks a live overlay
  repainting from the derived palette FAILED on first run and caught a real omission — the
  theme-aware colour getters sit in a different hunk than the controller. Without it the app
  would have shipped looking dark while every district boundary kept its light colour.

- **Stage A — SHIPPED (this change):** `/districtry/` microsite: landing page + the five design
  canvases (noindexed) + tokens + icons + OG card + manifest/head-snippet for later adoption.
  Purely additive — zero existing tracked files modified. Two package fixes applied: header stat
  60→69 counties (the mockup copied README's stale count), and the coverage fetch re-pointed at
  the live outline.
- **Stage B — SHIPPED (2026-08-20):** the working re-skinned copy of the real app lives at
  `/districtry-app.html` (root-level sibling, so every relative fetch resolves identically —
  zero path rewrites), generated by `scripts/build_districtry_preview.py`, which applies an
  exactly-once-asserted substitution table to current `index.html`: strips GA (its hostname
  gate would pass on the preview URL!) **and GoatCounter (ungated)**, strips
  canonical/OG/JSON-LD/manifest-link/SW-registration, adds noindex, retitles, swaps
  favicon/theme-color, loads Barlow via Google Fonts (preview shortcut — adoption self-hosts
  via `build_fonts.py`), and appends a `<style id="districtry-skin">` override island (the
  blessed outside-the-fence pattern, ENGINE_SYNC.md) carrying the violet chrome + Barlow
  tokens; the point marker joins the data tier (`#1d5fd6`). The masthead star SVG is
  **hidden, never removed** — `#star-path-header` is written by JS. **The full Playwright
  smoke test passes with `BASE_URL` pointed at the preview file** — every behavior gate
  (boot, 39 layers, ground-truth classification, coverage hiding, permalink aliases, error
  isolation) green on the re-skin, which is the "every existing function is maintained" proof.
  Refresh after index.html moves: re-run the script and commit;
  `build_districtry_preview.py --check` detects staleness on demand (deliberately not in CI).
  **Open review items on the skin:** all three resolved 2026-08-20 — see "Skin review items"
  below. Still accepted as-is: engine-fenced `METRO_NAME + " District Explorer"` strings show
  the old name in dialogs, which is precisely the Phase-3 engine release.
  **Fix round (2026-08-20, post-deploy):** `.flag-stripe` — the Chicago flag's
  accent/white/accent bands above and below the map, that fork's signature device — rendered
  as meaningless violet bands under the token swap; the districtry design carries no stripe,
  so the skin island now hides it.

## Footer elimination (operator-directed 2026-08-20 — IMPLEMENTED in the preview)

The redesign removes the document footer entirely: the map owns the left and bottom viewport
bounds (app-frame layout, desktop ≥901px; mobile keeps the stacked flow pending its own
design). Consequences, as built into `districtry-app.html` by the transform script:

- **FAQ → its own page**, `districtry-faq.html` (generated by the same script from the
  `.faq-section` markup verbatim, so the two can never drift within a generation; noindexed,
  tokens-styled, back-linked).
- **The footer's surviving content moves to a results-panel foot** (matching the canvas,
  which pins the disclaimer at the panel's bottom edge): the not-for-official-use
  disclaimer; the relocated `#footer-meta` (verified date — the boot script fills
  `#verified-date` by id, so the element MOVES, never duplicates); links to sources.html,
  the FAQ page, GitHub, sponsors, overberg.co; **the OSM geocoding attribution** (license
  requires it near the map — tile attribution stays on the Leaflet control); the relocated
  `#feedback-btn` (keeps the feedback-modal binding); and the relocated `metro-links-html`
  ENGINE fence (`#footer-metros` — sibling-metro links still inject at boot; fences pin
  content, not placement — the gaps-html masthead move is the precedent).
- The footer and in-page FAQ husks stay in the DOM `display: none` — nothing the boot
  script targets by id is ever deleted.
- Verified: full smoke test passes against the preview; every relocated id exists exactly
  once; map/panel fill viewport-minus-masthead exactly.
- **Adoption note (Phase 3):** on the real app this is fork-local markup/CSS except the two
  fence relocations (placement is fork-owned, so still no engine release) — but the FAQ
  page's head JSON-LD (FAQPage) and `sitemap.xml` entry become REQUIRED at adoption, since
  the production FAQ page must be indexable, unlike this preview.

## Canvas version history — CORRECTED (2026-08-20, second look)

An earlier revision of this section claimed the canvas had "iterated past the zip". It had
not: the Claude Design handoff bundle (uploaded 2026-08-20) is **byte-identical to the
original package** for every load-bearing file (App canvas, tokens, support.js, Industry
styles; same sync record 2026-08-19T20:52Z). There is exactly ONE canvas version. The
refinement rounds visible in the canvas chat (gradient border replacing the rejected dashed
line, dark-mode dot rings, merged card/toggle rebuild) are the history that PRODUCED the
2026-08-19 rebuild — they are IN the shipped `/districtry/` canvas, not after it. The
"5 pages" in the editor are the project's five .dc.html files, not new content.

## Canvas app-shell implementation (operator-directed "Implement Districtry App.dc.html", 2026-08-20 — SHIPPED in the preview)

The canvas's remaining unimplemented design landed in `/districtry-app.html` via the
transform script, same relocate-don't-delete discipline as the footer round:

1. **Three-zone coverage treatment** — the engine's single out-of-coverage wash is replaced
   AT ITS FORK-LOCAL CALL SITE (the scope-mask ENGINE fence is untouched;
   `coverageMaskRings` still gets set from `coverageOutlineRings`, preserving the engine's
   point-in-coverage test): gray outside Illinois, violet "Data coming — not yet sourced"
   wash on in-state unserved ground, soft violet glow + hairline on the state border
   (TIGERweb, fail-fast — an unreachable TIGERweb degrades to the old single-wash), and a
   map legend. Values are the canvas's own.
2. **Search relocates into the masthead** — the whole `.map-toolbar` moves verbatim (the
   geocoder binds `#geocode-form`/`#geocode-input`/… by id); `.search-extra` becomes an
   absolute dropdown under the header field.
3. **Header stat row** — "N counties · M layers · Sources", with N read from
   `docs/COUNTY_STATUS.md` and M from `metro-worksheet.json` at generation time, so a
   regeneration after a new county updates it.
4. **Panel header row** — `#point-chip` (coords + Share) relocates from the map's
   bottom-left to the top of the results panel; `position: relative` kept (it anchors the
   engine's share popover).

Not implemented, deliberately: the **Dark toggle** (dark mode remains deferred pending its
own approval) and the **live "N of 39 layers on" counter** (a live-state label needing a JS
hook into `state.layersOn`; the static stat row covers the header, the counter can join a
later round). Verified: full Playwright smoke test passes; every relocated id exists exactly
once; the coverage function schedules with an idle TIMEOUT so a busy main thread can't
starve it forever.

## Superseded delta list (kept for the record — all now resolved as above)

1. **Statewide coverage visualization** (operator-directed): soft light-violet gradient glow
   on the Illinois border — the dashed border was explicitly rejected — a light violet wash
   over in-state unserved counties labeled "Data coming — not yet sourced" (deliberately
   optimistic: *"the internal unserved counties are just areas that I haven't sourced the
   data for yet — I don't want to give the impression they won't be unlocked"*), gray
   "Outside Illinois" mask, and a map legend. The live app's scope-mask washes everything
   outside the 69-county ring identically; this design distinguishes three zones. Feasible
   (the app already has `metro-outline.json`, and TIGERweb serves the state boundary) but it
   is a map-semantics change, not a re-skin.
2. **Search moves into the header** (live app: floating overlay on the map — engine layout).
3. **Header stat row** ("N counties · 39 layers · Sources") + theme toggle placement.
4. **Results-panel header row**: coordinates + "N of 39 layers on" + Copy link at the top of
   the panel (live app: selected-point chip bottom-left on the map).
5. **Dark mode** iteration continues in the canvas (layer dots gained WCAG rings; operator
   noted the dark map is still hard to read) — remains the deferred functional addition.
6. **Regenerated package assets** (icons/OG/manifest/head-snippet) — refresh `/districtry/`
   from the canvas when the pin moves; when syncing, re-apply this repo's two fixes INTO the
   canvas (69 counties, live-outline fetch), which it still lacks.
- **Phase 3 — ROADMAP** (each step gated on explicit approval):
  1. Brand becomes worksheet data: add brand keys (product name, wordmark tag, palette tiers) to
     `metro-worksheet.json` + generator emission — no product-name key exists today.
  2. Engine release: parameterize the seven fenced `" District Explorer"` composition sites
     (index.html:3665, 3816, 3871, 3877, 4346, 4350, 4579); engine-v* + fan-out PRs to NYC/SF.
  3. Fork-local branding rows per `EXPANSION_GUIDE.md` §4.2 (head meta/OG/JSON-LD/theme-color/
     favicon, masthead mark/wordmark, `:root` palette values, analytics).
  4. `sources.html` hand-mirrored palette (lines 140–154) re-pointed.
  5. Assets + SW — **manifests + icons SHIPPED (2026-08-24)**, **og-image SHIPPED (2026-08-28)**.
     The head-snippet's `og:image` (`districtry/pwa/head-snippet.html`) is a paste-in reference
     with no live consumer and still shows a relative path — a documentation-only loose end, not
     a shipped-surface gap. The manifest was the one branded surface nothing generated,
     and it rotted exactly there: every other surface had said districtry since the rebrand while
     `il/manifest.webmanifest` still read `"Chicago District Explorer"` in the pre-rebrand navy
     `#0b3d91`, pointing at the old Chicago-flag star icons — so **installing to an Android home
     screen produced the old name and the old icon**, which is how it was found. NY and SF were
     the same with their own old names. `scripts/build_manifests.py` now emits all three from the
     worksheet `brand` block and `--check` gates them in `smoke-test.yml`. Icons were replaced in
     **place** (`sw.shell_urls` pins the filenames; NY's live under `icons/app/`), a padded
     `icon-maskable-512.png` added per instance and to each shell list, and each
     `sw.cache_name` bumped so returning installs re-precache. **iOS was worse than stale — it was
     absent**: Safari ignores the manifest's icons entirely when adding to the Home Screen and
     reads `<link rel="apple-touch-icon">`, which no instance had ever carried, so an iPhone
     install has never had a branded icon to use. `brand.apple_touch_icon` now names the
     180x180 opaque asset per instance and `head-theme` emits it alongside
     `apple-mobile-web-app-title` (without which iOS labels the shortcut from `<title>` — the
     question-led SEO string, truncated mid-question).
  6. Tooling: `build_fonts.py` → self-hosted Barlow woff2s (no font CDN in production);
     `build_og_image.mjs` rebuilt from `OG Card.dc.html` — **DONE (2026-08-28)**, triggered by
     Iowa's launch: the script still rendered the pre-rebrand Chicago-flag design, so Iowa's
     first pass at an og-image was hand-drawn instead of using the real one, and checking why
     turned up Wisconsin's live og-image.png shipping `districtry/og-districtry.png` verbatim —
     labeled "districtry / illinois". The rebuilt script takes an instance + label and renders
     `OG Card.dc.html`'s actual design (same SVG shapes, same Barlow/Barlow Condensed type) using
     that instance's own self-hosted fonts, no network dependency. Re-run for `ia` and `wi`; `il`,
     `ny` and `ca` keep their existing images (Illinois's is this same design, correctly labeled;
     NY/SF predate it and are their own pre-rebrand assets, out of scope here).
  7. **Dark mode** — its own proposal and approval (greenfield engine work).
  8. **Domain migration, last and independent:** districtry.com — CNAME ×3 forks, Pages custom
     domains/DNS, `metros.json` URLs + `--sync-fleet` regen everywhere, GA hostname gate,
     GoatCounter site code, canonicals/og:url/JSON-LD, sitemap, search re-verification, redirect
     story for chidistricts.com, subdomain scheme (il./chicago.districtry.com — operator call
     for CHI-as-statewide).

## Usability round (operator review of the deployed preview, 2026-08-20)

Six findings from driving the live preview, all fixed in the transform script:

1. **Search field read as a grey box.** `.search-shell` carries a panel fill + drop shadow drawn
   to float over a basemap; in a header that reads as a grey slab. The shell is now transparent
   and the INPUT carries the affordance (white, hairline border, violet focus ring).
2. **Prompt text** is now "Search an Illinois address" — the app stopped being Chicago-only.
3. **Share popover opened off-screen.** It anchors `bottom: calc(100% + 10px)` — correct while
   the chip sat at the map's bottom-left, fatal once the chip became the panel's TOP row, where
   the card rendered above the viewport: open, invisible, unreachable. In the panel it opens
   downward, clamped to the panel width.
4. **Pills lost their emoji and became one segmented group** (hairline container, rules between
   items) rather than three separately-outlined pills. ADOPTION NOTE: the gaps label lives inside
   the `gaps-html` ENGINE fence — safe to edit in a copy that is never deploy-spliced, but in
   production that same edit is an engine release, or the label becomes a config string.
5. **The Layers button appeared to close the MAP.** `.results-col { display: flex }` (added with
   the panel foot) outranks the UA's `[hidden] { display: none }`, so setting the hidden
   attribute left the panel on screen while the grid collapsed to one column around it. Scoped
   to `:not([hidden])` — a reminder that `display` on a class silently defeats `hidden`.
6. **State names abbreviate to USPS codes** in geocoder results ("…, Springfield, IL, 62701")
   and in the map legend ("IL" / "Outside IL"). Unknown values pass through unchanged, so a
   geocoder answering with something unexpected prints what it said.

Self-inflicted regression caught in the same pass: the stat row was the segmented group's first
child, so `overflow: hidden` clipped its "Sources" link; stats and group are now siblings in one
right-aligned header cluster.

## Header/chrome round (operator review, 2026-08-20)

- **The stat row left the masthead for the results panel's header bar**: coords + Share on the
  left, `69 counties · 39 layers` flush to the page's right edge across from the Share button.
  The stats sit OUTSIDE the chip on purpose — the chip is hidden until a point is selected and
  the counts are true either way.
- **Both redundant "Sources" links removed** — the trailing link in the stat row and the one in
  the panel foot. The masthead pill is the single door; the OSM line that remains in the foot is
  a licence obligation, not a repeat.
- **The FAQ moved up into the pills** (`Common questions`), so all four "about the data" doors
  sit together instead of one hiding in the panel foot.
- **Instance tag is now the two-letter state code** (`districtry / il`) in the wordmark, the
  page title, and the FAQ page — see the rule under Decisions of record.

Regression caught by looking at the render rather than the diff: moving the chip into a new
panel-head wrapper broke `.results-col > .selected-point-chip`, which silently un-did BOTH the
chip's light restyle and the share-popover reposition (the popover would have gone back to
opening off-screen). Re-scoped to `.districtry-panel-head .selected-point-chip`. A child
combinator is a promise about depth, and moving markup breaks it quietly.

## Header nav treatment (design review, 2026-08-20)

The segmented bordered group was retired after an options review — seven treatments rendered
live in the real masthead and compared side by side (artifact
`ec042cef-798d-477d-ae86-da05b8a03469`). The complaint that started it was correct: a bordered
container put a second hard rectangle beside the search field and gave four secondary links a
toolbar's weight.

**Shipped: emphasis matched to stated priority.** `index.html`'s own comment records that the
gaps button was moved into the masthead *because it is the standing caveat on every answer this
app gives* — so flattening all four to equal weight contradicted the project's own doctrine.
The pill is now the shape of an action in this row: **"What data is missing?" wears one
permanently and inverts to a solid violet fill on hover/focus**; its three peers are bare text
that earn the same pill shape as a soft tint on approach. One family, two ranks.

Rejected, with reasons worth keeping: a tab rail (form would promise view-switching with an
active tab; these four open a modal, two pages and an external site); condensed uppercase (most
on-brand, but four shouted phrases for secondary links, and 130px wider than any alternative);
fully quiet text for all four (lightest, but under-signals the one item the project wants seen).

## Map legend rebuild (operator-directed, 2026-08-20)

The corner legend was a flat wrapping run of **loose** swatches and labels — nothing bound a
swatch to the label it defines — so at the 340px cap the wrap fell between the blue dot and
"Selected point", stranding a swatch from its own text. Seven treatments were rendered over the
live map and compared (artifact `58ce7ef8-c196-4ae2-86d9-ca854c426cfa`); the operator chose the
titled vertical list. Each row is now a grid whose swatch and label cannot be separated, so the
defect is gone **by construction** rather than by picking a lucky width; the row-gap is 2px, not
the shorthand 8px, because a why-line spaced as far from its own label as from the next row
belongs to neither. The legend also gained a `COVERAGE` kicker — nothing previously named what
the colours were a legend *of* — and a rule separating the three coverage zones from the point
marker, which are two different kinds of fact.

**The copy fix matters more than the layout.** "Data coming — not yet sourced" implied the violet
counties hold no data at all. They are not empty: measured empirically by selecting a point in
the Bureau County enclave, **the great majority of layers still answer there** — U.S. House, both
Illinois chambers, IL Supreme Court, county, municipality, ZIP, school districts and zones, and
the nearest-N station layers. What actually hides is that county's **own** local districts:
county board, board of review, judicial subcircuit, fire protection, park, library, precinct,
township and TIF. The swatch now reads **"Statewide layers only"** over a why-line — **"County
board and local districts not sourced yet"** — which is the honest distinction and the one a
reader in an unserved county actually needs. Deliberately **no count is printed**: which layers
answer varies by county, and a sandboxed measurement is no basis for a live figure.

**Adoption note (Phase 3):** this legend is created by the preview's own coverage script, so it
is preview-local today. If the three-zone treatment is adopted into production, the legend and
this copy travel with it, and the wording becomes a fork-owned string — worth a worksheet key so
NYC/SF can say "Statewide layers only" about their own states without an engine release.

**ADOPTED 2026-08-25 — and the note above turned out to be the whole specification.** It named
the worksheet key, it named who the key was for, and it was written three days before the thing
it describes went missing. See "The coverage key, and the wash it reads" below.

## The coverage key, and the wash it reads (operator-reported, 2026-08-25)

**The rebrand shipped the key's CSS, its phone behaviour and its theme controller, and never
shipped the key.** `R4.2b` adopted the skin as an appended override island — 36 of 39 hunks
outside every ENGINE fence, which is why it was safe — and the island is CSS. The legend itself
was built in JavaScript, by the preview's own coverage script, and that script was not part of
the island. So production went out with 27 rules for `.districtry-map-legend`, a
`dstSyncLegendDisclosure()` whose `querySelector` returned null on every call, a `.dst-glow` blur
class nothing wore, and a `styleDistrictryCoverage()` writing into a `districtryCoverageLayers`
that nothing ever filled — while `drawOutOfScopeMask` went on painting the pre-rebrand flat grey
it had always painted. Every gate stayed green, because no gate anywhere asks whether a rule has
a subject.

**The three-zone wash went missing with it, and that is why the key could not simply be pasted
back.** A key naming a violet "Statewide layers only" band over a map that draws one flat grey is
worse than no key. So the two are one change: the wash draws the bands and the key names *the
bands that were actually painted* — `buildCoverageKey()` is handed what the draw produced, never
what the instance intended, so a region ring that is declared and fails to load degrades the wash
and the key together.

**Illinois is the only three-band instance in the fleet, and that is a measurement rather than a
policy.** A middle band exists only where full coverage is a proper SUBSET of a wider region the
statewide layers still answer in. Illinois qualifies: its county layers cover the served counties
while county, township, municipality, school district and ZIP answer anywhere in the state.
Wisconsin's `metro-outline.json` **is** the Wisconsin state outline — coverage *is* the region, so
there is nothing in between — and San Francisco and New York City have no wider region in play.
All three pass one geometry and get two bands and a one-row key, which is not a degraded key: the
grey was unexplained in all four apps until now.

**The words are a worksheet key, exactly as the note above predicted.** `coverage_key.outside`
names the outer band; the optional `coverage_key.region` (`edge`, `label`, `sub`) names the middle
one. It is **not derivable** and that is the reason it is data: Chicago's `METRO_NAME` is
"Chicago" while its coverage is 89 Illinois counties, so a generated `"Outside " + METRO_NAME`
would be plainly wrong in the one instance that most needs the key. Absent, the generator emits
nothing and the engine's `typeof` guard draws the wash with no key — the same inertness rule
`brand` and `poi_geocode_bbox` follow.

**The state ring is PRE-BUILT, and the preview's own version is the counter-example.** The
preview queried TIGERweb for Illinois at boot. Measured, that answer is **332 KB over 19,789
vertices** — four times the 83 KB school-board fetch `build_metro_outline.py` exists to have
removed from the critical chain, for this very wash. It is now the second output of that same
builder, from layer 0 of the same MapServer the county dissolve uses (so no new host, no new
service, nothing new for `validate_sources.py`), simplified by the same Douglas-Peucker at the
**same tolerance** — deliberately, because where a served county fronts the state line the two
rings trace the same river, and simplified apart they would open slivers of false "unserved
Illinois" along the Mississippi and the Ohio.

**The key names bands, and only bands.** The preview's fourth row was a blue dot for "Selected
point", and it does not survive: the selected marker is `#1d5fd6` in Illinois but a red star in
San Francisco, an orange pin in New York City and an amber star in Wisconsin — and inside Chicago
Illinois itself swaps to the flag star in flag red. One hardcoded swatch could not be right in
more than one of those. `.dml-rule` earns its keep as the separator between the region bands and
the outside band instead; `.dml-dot` is now unused and is left in the skin rather than swept,
because an instance that gives every point one marker could still want that row.

## The share control comes off the map (operator-reported, 2026-08-25)

The same shape, on the same day. `.districtry-panel-head` shipped in the skin — with a comment
describing "coords + Share on the left, the counts flush right" and a rule aiming the share
popover DOWNWARD because "the chip used to sit at the map's bottom-left" — and the markup that
would have created that bar never shipped. `#point-chip` stayed in `.map-bottom-left`, so the one
control that hands this view to someone else sat on top of the view it was handing over, and the
reader's own coordinates competed with the map for the corner.

Three things had to be true for the move to be an improvement rather than a relocation:

- **The popover had to stop clamping to the chip.** The skin's rule sets `left:0; right:0` and
  says it clamps to the panel's width. It does not: the popover is anchored to
  `.selected-point-chip`, so it clamped to a content-width chip — about 190px — and truncated the
  permalink it exists to hand over. The chip now fills the bar (`flex: 1 1 auto`), which is what
  makes that rule mean what it already said. The counts keep their edge: with the chip absorbing
  the free space there is none left for their `margin-left:auto` to take.
- **It had to survive a phone.** Anchored at the top of a scrolling panel the card opens 295px
  tall against about 255px of room on a 390x844 phone. Opening it now calls
  `scrollIntoView({block: "nearest"})`, which scrolls the least that makes it whole and does
  nothing when it already fits, so desktop is untouched. (`block: "nearest"` matters; an earlier
  draft guarded the call on `scrollIntoView.length !== 0`, which is always false — optional
  parameters do not count toward `Function.length` — so the guard silently skipped it.)
- **The counts had to be worth printing.** `.districtry-stats` reads "N of M layers on", and
  **both** numbers are relevance-aware. `M` is not `layers.length`: outside a layer's coverage the
  app hides it outright, so a reader in a county the local layers do not reach sees 21 toggles
  while the app registers 39, and "2 of 39" would count 18 layers they have no way to turn on.
  The numerator is `activeLayerCount()`, which the opacity scaler already uses for the same
  reason — on-and-hidden is not on. Downtown Chicago reads "2 of 32", and 32 is the figure this
  project's own notes give for what Chicago resolves. **Corrected 2026-09-23:** the numerator is
  no longer `activeLayerCount()`. That function counts nested sub-layers (Ward Precinct, Police
  Beat, Township) while `M` does not, so with every layer on at the Loop the panel read "36 of 33
  layers on". `syncPanelStats()` now counts both numbers in one pass over top-level toggles, and
  smoke check 2i holds the header to the sidebar a reader sees.

**The lesson both halves share:** a CSS rule with no subject is invisible to every gate in this
repo, and a comment describing markup is not markup. When a rebrand lands as an override island,
the island's JavaScript is the part that gets left behind — CSS drifts loudly the moment anyone
looks at the page, and a `querySelector` that returns null looks exactly like a feature nobody
turned on.

## Skin review items — RESOLVED (2026-08-20)

The three items left open when Stage B shipped, each investigated before deciding. Two were the
same finding: **Chicago motifs that survived the re-skin because a token swap recolours a shape
without questioning it.**

1. **Warm accent — KEPT as a distinct hue, and the alternative disproven.** The open question was
   whether `--accent-warm` should simply become violet ("one hue for both slots"). It must not:
   the engine paints the **Public Safety group dot** with it (`.group-safety .dot`, index.html
   ~1612) beside Political (`--accent`), Schools (`#E8A324`) and Geography (`#5C8F6B`). Violet in
   both slots would render two of the four group dots identically — a categorical encoding
   collapsing, not a taste call. It is also `--focus-ring`, where contrast *against* violet
   controls is the point. `#b0316e` stays: it is the mark's own third polygon, so the hue is
   on-brand without borrowing from the data tier (the police/fire reds are map colours and stay
   map colours). Measured after the change: the four dots are four distinct hues.
   `--accent-warm-deep` is referenced **nowhere** in the engine today; the override is kept only
   so no Chicago flag red survives anywhere in the cascade.
2. **Empty state — the Chicago flag star retired.** A six-pointed star is that city's emblem;
   recoloured violet it was an off-brand city motif sitting in a districtry app. It is now the 5c
   mark drawn as a quiet outline. The `#star-path-empty` element **stays in the DOM, hidden** —
   the boot script writes its `d` by id and would throw on a missing node (the same discipline as
   the masthead star).
3. **Selection marker — now the canvas's own answer.** The marker kept the star *shape* while
   only its fill moved to data blue, so a Chicago emblem was still marking "your point". The
   design canvas had already answered this: a circle with a white ring. It is now
   `<circle r="17" fill="#1d5fd6" stroke="#fff">`. One transform owns shape **and** colour; the
   earlier fill-only swap was deleted so two transforms cannot disagree about what the marker is.
   *(This is the BASE marker. The hierarchy that overrides it was settled separately — see*
   *"Marker hierarchy" below, which supersedes the badge bullet and the open question in this*
   *section.)*

**The marker is a hierarchy, and only its first branch was re-skinned.** `selectPointMarker()`
walks four cases: inside Chicago → the base marker (now the circle); on Lake Michigan → the Water
Taxi seal; inside an Illinois county → **that county's seal** where one ships (9 counties) or a
**county-name badge** otherwise; outside Illinois → the base marker. Two consequences were found
by reading that chain:

- **The county name badge hardcoded `#0B5394` — the Chicago flag deep blue — inside a JS string**,
  where no token swap could reach it. Exactly the same class of survival as the flag stripe and
  the star: a city colour outliving the re-skin because it was written as a literal, not a token.
  Moved to the data-tier `#1d5fd6` so it matches the circle the legend describes, and its
  system-font stack moved to Barlow. **SUPERSEDED the same day** — the badge is retired
  outright, so both of those transforms were deleted; see "Marker hierarchy" below.
- **Two relationship-legend swatches (`.rel-sw-in`, `.rel-sw-cross`) carried the same literal.**
  These are illustrative — the outlines the map actually draws take each layer's own colour,
  darkened — so as Chicago blue they demonstrated a hue this app never draws. Now the data-tier
  blue, sampling the tier they illustrate.

**The county seals themselves are KEPT, and the open question is the operator's.** *(Answered —*
*see "Marker hierarchy" below. The paragraph is kept for the reasoning that framed the question.)* They are each
county's own emblem, not Chicago branding, and for a state-then-national product showing the seal
of the county under your point is arguably an asset — they also carry researched licensing
(`icons/source/README.md`, `docs/COUNTY_SEALS_REVIEW.md`). But note the tension the new legend
makes visible: it says "● Selected point", which is true inside Chicago and outside Illinois,
while in the rest of Illinois the marker is a seal or a name pill. The design canvas's own answer
was a single circle everywhere. Retiring or keeping the seal/badge branch is a **product** call,
not a re-skin one, so it is flagged rather than taken.

Three `#0B5394` uses remain in the preview and are correctly out of scope: the `:root` definition
(overridden by the skin), a `var(--accent-deep, #0B5394)` fallback that never applies, and the
police-district / early-voting **map layer** colours — data tier, which the three-tier rule keeps.
The districtry token set itself retains `#0b5394` as `--layer-zip`.

**Related finding, NOT changed:** the water-taxi marker (`icons/water-taxi.png`, swapped in when a
point lands on Lake Michigan) is a third Chicago motif — the Chicago Water Taxi seal. It is a
deliberate easter egg rather than chrome, so retiring or replacing it is a product call, not a
re-skin one. Flagged here rather than silently changed.

## Marker hierarchy — operator decision (2026-08-20)

The question flagged above came back answered in three parts: **retire the county-name badge in
favour of the default circle, restore the Chicago flag star for the city in its original colour,
and leave the seal counties alone.** The re-skin had been treating the four branches as one
question with one answer; the decision splits them by what each actually says.

The shipped hierarchy in `selectPointMarker()`, in the order the function walks it:

| Where the point lands | Marker | Why |
|---|---|---|
| Inside Chicago | **Six-pointed flag star, `#C8102E`** | The city's own emblem, for the city. What was wrong was using it as the default for all of Illinois — not using it at all. |
| Lake Michigan | Water Taxi seal | Unchanged; still the flagged easter egg (below). |
| An Illinois county **with** a shipped seal (9) | That county's seal | Unchanged. Each county's own emblem, licence-researched. |
| Anywhere else — an Illinois county with no seal, or outside Illinois | **Circle, `#1d5fd6`** | The canvas's own answer, and now the genuine default. |

Three consequences worth recording:

- **`makeCountyBadgeDivIcon` is now dead code in the preview** — the definition survives (it is
  engine text the transform script does not delete) but **zero call sites remain**. Both branches
  that reached it are gone: the seal branch sets an icon only `if (ok)`, and the no-seal branch is
  deleted entirely. The two transforms that had recoloured the badge went with it — a colour fix
  on a shape that can no longer render is drift waiting to happen.
- **The engine's early return had to be split.** `if (!live() || inCity) return;` conflated "the
  selection is stale" with "Chicago needs no override", which is precisely why the base icon was
  doing double duty as both *Chicago's marker* and *everywhere else's*. It is now
  `if (!live()) return;` followed by `if (inCity) { marker.setIcon(chiFlagStarDivIcon); return; }`,
  so the two facts are separate. `chiFlagStarDivIcon` is defined beside the base icon and reuses
  the engine's `starPath()`, already in scope.
- **The legend's "● Selected point" is now a simplification rather than a near-falsehood.** It is
  literally true for the great majority of Illinois — every county without a seal, which is 60 of
  the 69 served — and the two exceptions (Chicago's star, the nine seals) are self-evident on
  sight. Before this change the pill rendered across most of the state, so the legend disagreed
  with the map nearly everywhere it was read.

Verified in Chromium against the built preview: Chicago Loop → `STAR` fill `#C8102E`;
Bureau, Madison and Champaign (no seal) → `CIRCLE` fill `#1d5fd6`; a point in Indiana → `CIRCLE`.
The seal branch is **not reachable in this sandbox** — `chicagoCoverage` awaits
`loadCommunityAreas()` against Socrata, which is blocked here and never settles, so branches 2–4
never run locally. That is pre-existing and unrelated to the change (identical before it), so
correctness on the seal path was established by diffing the hierarchy instead: the seal call site
is byte-identical apart from losing its `: makeCountyBadgeDivIcon(name)` alternative.

## Dark mode (operator-approved 2026-08-20 — the one function this re-skin ADDS)

Dark mode was the single item held back when Stage B shipped: everything else in the
redesign already existed in the app and was *maintained*, while this was genuinely new and
so waited for its own approval. It now ships in the preview, and only in the preview —
`index.html` is untouched, as it has been for every round of this work.

**The palette was not invented here.** `districtry/tokens/districtry.tokens.css` has carried a
complete `[data-theme="dark"]` block since the package landed, and `Districtry App.dc.html`
already implemented the control, the persistence key, the basemap swap and the tile filter.
This change wires that decided design to the real app's token names; where the canvas and the
app disagreed, the canvas won on appearance and the app won on structure.

### What it does

| Surface | Light | Dark |
|---|---|---|
| Chrome tokens | paper `#f4f2ee` / panel `#fff` / ink `#17161c` | `#15131b` / `#201d29` / `#ece9f4` |
| Brand | `--accent #6d3fd1`, `--accent-deep #5730ab` | `#a78bfa`, **`#c4b0ff`** |
| Warm slot (Safety dot + focus ring) | `#b0316e` | `#e879b9` |
| Card data tier | `--card-accent #1d5fd6` | `#6ea8ff` |
| Basemap | CARTO Positron (vector; raster `light_all` fallback) | CARTO Dark Matter (vector; raster `dark_all` fallback) + `brightness(1.35) saturate(.92)` on either kind's surface |
| Selection marker | circle `#1d5fd6` | circle `#6ea8ff` (Chicago's flag star stays flag red) |
| Coverage wash | grey outside IL, violet "data coming" | near-black outside IL, lifted violet |

"Deep" means **more contrast against the ground, not darker** — on a dark ground that is
*lighter*. Inverting that one word is why dark-mode links so often come out unreadable.

### The decisions worth recording

- **Default is the OS preference; an explicit choice wins and persists.** The canvas hard-defaults
  to light; a reader whose machine already says "dark" should not have to say it again, so the
  fallback follows `prefers-color-scheme` and only a click writes `districtry-theme` to
  `localStorage`. While no choice is on record the page keeps following the OS live. One line to
  reverse if the operator prefers a hard light default for a design-review preview.
- **The toggle is a control, not a fifth door.** It sits at the end of the masthead pill row behind
  a hairline, and it is **text-only** — the standing instruction for that row is that its pills
  carry no icons, and a sun/moon glyph would walk that back. The label names what the button
  *does* ("Dark" while light), which is also the canvas's own semantics.
- **Set before first paint.** The theme attribute is written by a blocking inline script in the
  head, not by the app boot. Deferring one attribute is a flash of the wrong ground on every load.
- **The FAQ page shares the key.** It already linked the token sheet, so it needed only the same
  boot script and a toggle; a choice made on the map carries to it and back.

### What a token swap could not reach — again

The recurring defect of this whole project is a **colour written as a literal rather than a token**,
and dark mode is where every remaining one becomes visible at once. Four classes needed explicit
rules:

1. **The UA's own controls.** `color-scheme: dark` on the root. Without it the 39 layer checkboxes
   stayed bright white squares on the dark cards — the single most visible thing wrong with the
   first dark build, and invisible to any amount of CSS aimed at the app's own selectors.
2. **The mark's blend mode is an inline `style` attribute**, which no selector outranks, so the
   three polygons stayed `multiply` and vanished into the dark ground leaving a bare "d".
   `!important` is the correct tool for exactly this case, and is used only here.
3. **Leaflet's chrome and the engine's white surfaces** — popups, tooltips, the zoom bar, the
   attribution strip, the share popover, the hover card, every `#fff`/`#EEF4F7` hover. Leaflet's
   CSS is inlined in this app, so all of it is ordinary text in one stylesheet.
4. **The map's own data.** Forty-odd layer stroke colours are JS literals picked for a light
   basemap. Rather than fork the palette — which would break both the card-to-overlay tie and the
   categorical encoding — the overlay pane is lifted as a whole with
   `brightness(1.45) saturate(1.06)`, a hue-preserving colour matrix, so every layer keeps its
   identity *and* its relationships. It is deliberately **not** paused during pan the way the
   highlight drop-shadow is (`.map-panning`): a colour matrix is cheap where a per-frame
   drop-shadow rasterisation is not, and flipping it mid-pan would flash the whole map.
   **Known limit:** a lift cannot rescue near-black. `#14181C` and `#06375E` stay hard to see on a
   dark basemap. The honest fix is per-layer dark colours in the layer definitions, which is a
   data-tier change with its own review — not a re-skin. The one near-black that *is* handled is
   the pinned-parent outline, which inverts to near-white because it is chrome, not a layer.

### Two things fixed on the way past

Both found by auditing what a token swap cannot reach, both light-mode bugs that predate this
change:

- **`--faint` was referenced and never defined.** The map legend has used it for its "COVERAGE"
  kicker and the why-line since the legend shipped, so both silently fell back to inheriting
  `--slate` and rendered at full label weight. Defined now; the legend's intended hierarchy
  (kicker and why-line quieter than the labels they qualify) appears for the first time.
- **Three Chicago-flag literals were still in the hover states of violet buttons** — `#08406e` on
  the search and metro-portal buttons, `#094377` on the feedback primary, `rgba(11,83,148,…)` on
  the share-copy button — so each flashed Chicago navy on approach. Same class as the flag stripe
  and the star.

Fifteen `rgba()` tint literals at their *winning* call sites became tokens (`--dst-brand-tint`,
`--dst-ink-tint`, `--dst-shadow`, …) so the dark block has something to override. Light values are
the ones already in force, so light mode is unchanged by the refactor.

### How it was verified

Behaviour, in real Chromium: OS-light-no-choice → light; OS-dark-no-choice → dark with the
attribute already set before body paint; the toggle flips, persists, and survives reload against a
contrary OS setting; the basemap swaps to the dark cartography (Dark Matter on the vector path, `dark_all` on the raster fallback — both lifted by the same filter the dark palette was derived against); `theme-color` follows; the choice carries between
the app and the FAQ page. No non-network console errors in either theme (the `ERR_CONNECTION_RESET`
lines are the sandbox's blocked live APIs, identical in both).

Appearance, by **pixel-diffing light mode against the shipped build**: on a clean load exactly two
regions differ — the masthead pill row (the new toggle, and the four pills shifting left to make
room) and the legend's kicker and why-line (the `--faint` fix). Nothing else in light mode moved,
which is what "maintain existing functionality" has to mean in practice. That diff also caught a
regression worth naming: the toggle was **1px taller** than its neighbours because a `<button>`
defaults to `line-height: normal` where the row's links inherit `12.5px`, and it pushed the whole
app down a pixel. Matched, so adding a control to that row now costs no layout at all.

**Not verified here:** the real CARTO basemaps. The sandbox cannot reach the tile CDN, so both
themes were driven against synthesised flat tiles at CARTO's own ground colours — good enough to
judge overlay readability, not a substitute for looking at the deployed page.

## Per-layer dark map colours (2026-08-20, second dark-mode round)

Dark mode shipped with a **stopgap on the map**: a `brightness(1.45) saturate(1.06)`
filter over the whole overlay pane, with a note that near-black layer colours would
survive it and that the honest fix was per-layer dark colours. This is that fix. The
filter is retired.

### The problem, measured

The layer palette is 59 colour literals chosen against a light basemap. Measured against
CARTO `dark_all`'s ground (`#1a1a1a`, which the app's own tile filter lifts to about
`#232323`):

- **28 of 37 stroke colours fall below 3:1**, the ratio WCAG 1.4.11 asks of a non-text
  boundary.
- **Four sit under 1.5:1** — `#14181C` (1.14), `#06375E` (1.28), `#7A0A1C` (1.41),
  `#7A0B1E` (1.42). That is not "dim", that is gone.
- On the *light* ground the same palette's worst case is 3.38:1. It was never a bad
  palette; it simply does not transfer.

A brightness multiply cannot fix the bottom of that list — `#14181C × 1.45` is still
near-black — which is exactly why the stopgap was labelled one.

### Why the obvious fix was rejected

The first attempt lifted each colour by the **minimum needed to clear 3:1**, preserving
hue. Every colour passed. The palette broke anyway:

- **314 of 703 pairs moved closer together**, and **66 landed inside dE 0.05** — close
  enough to read as the same colour.
- U.S. House District and County both became the same grey. City Ward and County Board
  District became the same blue. Post Office and Judicial Subcircuit the same violet.

The reason is worth writing down, because it is not obvious: **in the light palette a
great deal of the categorical separation IS lightness.** Navy vs mid-blue vs sky are one
hue family distinguished by how dark they are. Push them all to one contrast target and
the encoding collapses, hue preserved or not.

### What shipped instead

One **order-preserving affine remap** of OKLCH lightness across the whole palette, hue
untouched, chroma lifted ×1.25 to buy back the separation that compressing lightness
costs. Parameters `L 0.54–0.92, chroma ×1.25`, chosen by sweeping for the fewest
collisions subject to every stroke clearing 3:1.

Monotonic matters twice over: relative order between layers survives, and every
**within-layer** relationship survives by construction — a stroke darker than its fill
stays darker than its fill (measured: 0 flips).

**The bar is a measurement, not a taste call.** The dark palette is held against the light
palette's own record:

| | worst contrast | pairs inside dE 0.05 | p5 dE |
|---|---|---|---|
| light palette, light ground | 3.38 | 25 | 0.056 |
| light palette, **dark** ground | **1.14** | 25 | 0.056 |
| derived dark palette, dark ground | **3.10** | **24** | 0.052 |

It is *no more* collision-prone than the palette it derives from — marginally less — and
it fixes all 28 contrast failures. Derivation lives in `dark_map_palette()` in
`scripts/build_districtry_preview.py`; the 59-entry table is emitted into the preview so
it is inspectable and hand-adjustable.

### How it reaches the map without an engine edit

`baseStyleFor()` is the engine's single funnel for every path it paints, and
`moduleColor()` is the single source for the card accent, the sidebar dot and the hover
swatch. Both read `mod.overlay.style` directly. So the palette is installed as **getters on
the layer style objects** — `Object.defineProperty` with a getter that returns light or
dark, and a setter so any assignment degrades to plain data rather than throwing on a
read-only property. Every downstream read becomes theme-correct with no engine edit and no
second copy of the state to keep in sync. One install pass at the end of the script covers
all 43 polygon layers, the two nearest-N point layers' `mod.color`, and the School Location
type table.

The getter is on the **paint path**, so the theme is cached in a variable rather than read
off the DOM: `baseStyleFor()` reads two colours per path and a full repaint runs over every
path of every active layer. A `getAttribute` in there would put a document access inside
the loop this repo has already optimised twice (P7, P8).

Repainting on a flip goes through the engine's own `updateLayerHighlight()`, which already
handles all three cases (a matched region, no selection, a per-feature-styled layer) and
re-derives each from `baseStyleFor()`. `highlightApplied` is cleared first to force the full
sweep — the P7 fast path repaints only the two paths whose match role changed, and here
every path's colour moved.

### The highlight was pointing the wrong way

`highlightStyleFor()` builds the selected region's outline as
`darkenHexColor(moduleColor(mod), …)` — "the layer's own colour, shifted away from it so
the match pops". **Darken is right on light paper and exactly backwards on a dark map**,
where a darker outline recedes into the ground instead of standing out. This is the same
error as `--accent-deep`, one layer down.

`darkenHexColor` is a *fenced* engine function, but a function declaration's binding is
writable, so fork-local code rebinds it to shift toward white in dark mode — no fence edit.
Measured on the shipped build: U.S. House paints `#696F76` with its highlight at `#9EA1A6`
(3.10 → 6.06:1); IL Senate `#9B7CFD` with `#BEAAFE` (5.01 → 7.76:1). At adoption the honest
fix is for the engine to shift away from the *ground* rather than toward black.

### Verification

Driven in Chromium: flipping the theme repaints every stroke and all 37 card accents, with
**no colour surviving the flip** in either direction, and no page errors. Light mode was
pixel-diffed against the shipped build and differs in **one band of 687 pixels — the
generation stamp, because the source SHA changed.** Nothing else in light mode moved, which
is what the getter design is for: in light the getter returns the original literal.

Gates: `build_districtry_preview.py --check`, `validate_index.py`,
`generate_metro_files.py --check`, `check_engine_parity.py` and the full smoke test all
pass; `index.html`, `sw.js`, `sources.html` and `data/` untouched.

**Still not verified here:** the real CARTO tiles, for the same sandbox reason as before —
the `#232323` ground the whole derivation targets is CARTO's published dark_all land colour
with the app's own tile filter applied, not a sampled pixel.

**Left alone, deliberately:** the two nearest-N point layers paint `circleMarker`s from
colours captured in the factory closure, so their pins keep the light colours; their fills
(`#41B6E6`, and the fire red) are bright enough on dark that this reads as a non-problem
rather than a debt. The hover popup's `hoverDotIsInvisible()` fallback still assumes a
too-LIGHT dot is the failure case; in dark that assumption inverts, but the dot ring keeps
it legible.

## The phone layout (mobile review, 2026-08-21) — A + B shipped

A measured review of the preview on phones, and the first two of its four options.
The review itself is the artifact published on 2026-08-21; this is the record of what it
found and what changed.

### What the review found

Every number measured in Chromium at real device sizes, both themes, touch emulation on.

| | iPhone SE 375×667 | iPhone 14 Pro 393×852 |
|---|---|---|
| masthead | 247px (**37% of the viewport**) | 245px |
| first result card | y=847 | panel *header* at y≈840 of 852 |
| pinned column | 500px of 667 | 569px of 852 |
| reading slot | **167px** | 283px |
| document | 3,780px (5.7 screens) | — |

**The root cause is one line.** All of the re-skin's LAYOUT work sits inside a single
`@media (min-width: 901px)`; below that the engine's original mobile design governs. But the
re-skin's CHROME rules — search moved into the masthead, the pill row, the coverage legend —
apply at every width. A composition built for a wide screen was being stacked onto a narrow
one, and the parts that cost nothing on desktop were charged full price on a phone.

Three findings, and two were mine:

1. **The sticky column pinned 500px of 667.** The engine makes `.map-col` `position: sticky`
   below 900px so the map stays put while results scroll under it — and the strip beneath the
   map is inside that column, so whatever is in it is on screen for the entire page.
2. **143px of that was the coverage legend.** It floats over the map on desktop and costs
   nothing. The engine reflows that corner into a static strip on mobile *deliberately* — its
   own comment says a 48vh map is too short to float things over — and the legend rebuild
   turned the slim strip into a 160px block. Invisible on desktop, which is why it shipped.
3. **Every masthead pill was 29px tall**, against Apple's 44 and Material's 48dp. That row was
   sized for a mouse.

**Scoping fact that shaped the options:** all six mobile media queries live inside
`styles-core` / `styles-app` fences. The sticky map, the 48vh height and the 900px breakpoint
are ENGINE, shared with NYC and SF — so anything touching them is a release, not a fork tweak.
Everything below overrides from OUTSIDE those fences at higher specificity.

### A — the legend stops being pinned furniture

The legend is now a `<details>`. Authored `open`, which is what desktop wants; a boot pass
closes it below 900px, where it becomes a ~34px "Coverage" chip beside the hover toggle, with
the three swatches inline so colours can still be matched without opening. **The "why" line
survives one tap away rather than being cut** — it was an explicit operator requirement that
the wash explain itself, and a compact-legend-by-deletion would have thrown it away.

Driven by JS rather than CSS because `open` is an attribute, not a style, and it re-syncs on
every breakpoint crossing.

### B — a masthead in the shape of a phone

- The tagline and the preview stamp are hidden below 900px. The empty state already carries the
  same sentence, where a reader actually meets it.
- The four "about the data" doors **move into the panel foot** and back on resize. They are
  *moved*, never duplicated — two copies of `#gaps-btn` would break the engine's
  `getElementById` binding — and re-inserted before the toggle's separator so order survives.
- The theme toggle is lifted out of flow into the wordmark row, so it costs no height at all.
- Every remaining target is `min-height: 44px`.

**The doors placement was measured twice, and the first answer was wrong.** They were first put
at the *top* of the results panel, on the reasoning that "What data is missing?" is the standing
caveat and should stay prominent. Measured, that block is **107px** — I had estimated 56 — and at
the top of the panel it sits between the reader's coordinates and the reader's answer. On a
393×852 phone that is the difference between 48px of the first card showing and 159px. The
review had said panel foot; the measurement agreed with the review; the estimate was what was
wrong. **Named cost:** on mobile, "What data is missing?" loses the promoted position it was
deliberately given in the masthead.

### Measured result

| | before | after |
|---|---|---|
| masthead | 247px (37%) | **121px (18%)** |
| pinned column | 500px | 403px |
| reading slot | 167px | **264px (+58%)** |
| first card, 375×667 | y=847 (below the fold) | **y=624 — above it** |
| first card, 393×852 | below the panel header | **y=693, 159px visible** |
| header tap targets | 29px | **≥44px** |

Round-tripped across the breakpoint four times: order preserved, exactly one `#gaps-btn`
throughout, legend open state tracking, no errors.

**Desktop is pixel-identical in both themes** except the generation stamp — verified by diff,
which also caught the one regression this change introduced: moving the flex column from the
legend card onto a new `.dml-items` wrapper left the summary outside the `gap: 5px`, tightening
the desktop legend by 5px. An eye would not have caught it.

### The map gives back 60px — RESOLVED (operator-directed, same day)

The lever above was put to the operator and answered: **42vh / min-height 260**, with the
caveat staying in the panel foot.

The floor was the part that mattered. The engine sets `#map` to `48vh` with `min-height: 340px`,
and on a 375×667 phone 48vh is only 320 — so the FLOOR binds, and the shortest screens, where
space is scarcest, were the ones held to the tallest map. Overriding both from outside the
`styles-core` fence costs no engine release and does not reach the NYC or SF forks.

| device | card visible above the fold, before → after |
|---|---|
| iPhone SE 375×667 | 43px (an edge) → **103px** |
| iPhone 14 Pro 393×852 | 159px → **210px** (the whole card) |
| Pixel 7 412×915 | — → **247px** |
| iPad mini 768×1024 | — → **358px** |

On the smallest phone the app now answers its own question without a scroll: wordmark, search,
map with the point on it, coverage chip, coordinates, and **"U.S. House District IL-7 — Danny K.
Davis"**. Three rounds ago that card was at y=847. Tiles and the selection marker verified
present at every size; desktop pixel-identical in both themes bar the generation stamp.

### C — lead with the answers (approved, and adapted for a reason)

39 cards stack vertically on a phone and the ones the reader has not picked dominate: with two
layers on, 37 unanswered rows sit between them and the panel foot.

**Implemented literally, C would have been a regression, and the measurement is what caught it.**
`state.layersOn` starts EMPTY — verified on a clean load: 39 cards, **0 checked**. "Show only the
layers that answered" would therefore show a reader who has just dropped their first pin an
*empty panel*. The layer list is not clutter standing in front of the app; for a new visitor it
**is** the way in.

So the collapse is **conditional**: it applies only once at least one layer is on, which is
exactly when there is something to lead with. With none on, the chooser is the whole panel, as
before. The first layer a reader turns on is the moment the panel collapses to it.

`:has(input:checked)` does the hiding, so a card reappears the instant its box is ticked with no
state to keep in sync — the engine's own error/empty-state rules already rely on `:has()`, so
support is established here. The control is a full-width button after `#groups-root`:
*"Show all 39 layers"* ⇄ *"Show only my 2 layers"*, hidden entirely on desktop and whenever
nothing is on (there is then no shorter state to offer).

| | collapsed | expanded |
|---|---|---|
| cards shown | 2 | 32 |
| group sections | 1 | 4 |
| document, 375×667 | **1,529px** | 3,680px |
| document, 393×852 | **1,590px** | 3,737px |

**58% shorter**, round-tripping to the exact same height, no page errors. Desktop is
pixel-identical bar the generation stamp, with the button `display: none` and 32 cards as before.

**One bug worth recording**, because it is a class this project keeps meeting: the button's base
`display: none` was emitted *after* the mobile `display: block` rule. Media queries add no
specificity, so source order decided it and the control was never visible at any width. Moving
the base styles above the media block fixed it — the same "later rule of equal specificity wins"
trap as the `.masthead-actions` overrides.

**Also recorded:** `offsetParent !== null` is not a usable visibility test in this app and misled
two separate measurements in this session (an SVG mark, then these cards). `getComputedStyle(e)
.display !== "none"` is the one that tells the truth.

### D — tablets get the two-column layout (approved)

The engine's breakpoint is 900px, so an iPad mini at 768×1024 was handed the phone design.
Measured on the two sides of that boundary at the same height, one pixel apart:

| at 1024px tall | 900px (phone layout) | 901px (two-column) |
|---|---|---|
| map | 900 × 430, full width | **561 × 817** |
| results panel | full width, in the page scroll | **340px, scrolls independently** |
| page scroll | 1,475px | **1,024px — none** |

At 768 the two-column gives a 428 × 824 map and the same 340px panel, still with no page
scroll. That is plainly the better deal, and the breakpoint was simply set for phones.

**Done fork-locally, not as an engine release.** The seven mobile media queries live inside
`styles-core` / `styles-app`, so moving the engine's breakpoint means a release tag plus fan-out
PRs into NYC and SF — and this preview is a sandbox whose production adoption is Phase 3. So the
shell starts at 768 here, and the engine's mobile rules that would otherwise leak into 768–900
are answered from outside the fence at the same specificity. **At adoption this should become
the engine change**, so the siblings get it too; the fork-local version is 11 breakpoint sites
(8 CSS, 2 `matchMedia`, 1 comment) against the engine's 7 fenced queries.

The 767/768 boundary flips every piece together, verified in both directions: at 767 the map is
sticky at 42vh, the strip is static, the doors are relocated, the legend is closed, C's collapse
is on and its button visible; at 768 all of it turns off and the legend floats back into the map
corner. No horizontal overflow at any width, no page errors.

**The regression this introduced, and the shape of it.** The first cut applied the undo rules at
*every* width ≥768, and two of their values — `masthead-inner`'s gap and `.masthead-actions`'
alignment — were written from assumption rather than read from the engine. Desktop moved by
**147,868 pixels, 11% of the viewport.** Scoping the undo to `768–900` makes the mistake
unavailable: above 900 there is nothing to undo. The fix is structural, not a corrected guess.

Verified after: **desktop 729px (light) / 734px (dark) differ — the generation stamp alone — and
the 375×667 phone differs by ZERO pixels.**

### The four options, closed

| | what | scope | shipped |
|---|---|---|---|
| A | legend stops being pinned furniture | fork-local | #415 |
| B | a masthead in the shape of a phone | fork-local | #415 |
| — | the phone map gives back 60px | fork-local | #416 |
| C | lead with the answers | fork-local | #418 |
| D | tablets get the two-column layout | fork-local (engine at adoption) | this change |

**What the pixel-diff caught that review would not have**, across the four: a 5px tightening of
the desktop legend (A), a 1px growth of the whole app from a `<button>`'s default line-height
(B), a control invisible at every width from a media query losing a source-order race (C), and
an 11% desktop shift from an over-broad media query (D). Four for four.
- **C** (lead with the answers, collapse the 39-layer checklist) and **D** (let tablets have the
  two-column layout — an engine release plus NYC/SF fan-out) are approved and not yet built.

## Both collapse controls graduate to desktop (operator-directed, 2026-08-21)

Two controls built for the phone fold turned out to be worth having everywhere, so
both leave the `max-width: 767px` block.

**The layer chooser.** *"Show all 39 layers"* ⇄ *"Show only my N layers"* now appears at every
width. What does NOT graduate is the phone's **auto-collapse**: there, the fold forces a choice
and the first layer a reader ticks is the moment the panel collapses to it. A desktop panel
scrolls on its own, and a list that silently shrank on the first tick would be a surprise rather
than a service — so on desktop and tablet the control is *offered*, never applied. Defaults are
untouched: 32 cards showing, nothing collapsed, exactly as before.

**The coverage legend.** It was a tap-to-open chip on the phone only, because there it was pinned
furniture inside the sticky map column; on desktop it was a static caption. It is now collapsible
on both, still **open by default** on desktop so first paint is unchanged. The summary takes
`cursor: pointer` and a **chevron drawn from two borders** — not a glyph, so it inherits the
label's colour in both themes and needs no font.

**One thing the change forced, and it is the interesting part.** `dstSyncLegendDisclosure()` used
to assert the per-viewport default on every breakpoint crossing: closed on a phone, open on
desktop. Once the legend is collapsible on desktop, that assertion becomes an override — close it,
resize past 768 and back, and it silently reopens. So the sync now sets only the DEFAULT and stops
having an opinion once the reader has expressed one, recorded as `data-dst-user-set` on the
element.

The flag hangs off a **click on the summary, not the `toggle` event**, and that is deliberate:
`toggle` fires asynchronously and fires for the sync's own writes too, so a flag set there could
not tell the reader apart from the code. A click is synchronous and only ever the reader.
Keyboard activation of a `<summary>` raises click as well, so it costs no accessibility.

Verified: close on desktop → cross to phone → cross back → **still closed**. Phone, tablet and
desktop each drive both controls with no page errors. Desktop differs from the previous build by
**731 px in light and 734 in dark — the generation stamp plus the 34px chevron**; the new button
lives at the end of the 39-card list, below the fold at 1440x900, so nothing visible at rest moved.

## Map legibility under stacked layers (operator-reported, 2026-08-21)

*"It's difficult to see the streets and other map features once you toggle on multiple layers."*
Carried over from the live design, and it has one specific cause rather than being general
translucency.

### The engine already fights this, and exempts the one case that matters

`scaleFactorForActiveCount()` scales every active layer's fill down as the count grows, and
measured, it works: base fills plateau at about **11% obscuration however many layers are on**.

But `highlightStyleFor()` returns a flat `fillOpacity: 0.32`, and `rescaleLayerFill()` explicitly
skips any layer showing a highlight — its comment reasons that highlight opacities are
"count-independent", which is true of each one alone and false of the stack.

**That is the one fill where overlap is guaranteed rather than incidental.** Every active layer's
matched region contains the selected point, so every highlight lands in the same place — which is
exactly where the reader is looking. The composite is `0.68^n`:

| layers on | basemap still visible |
|---|---|
| 1 | 68% |
| 2 | 46% |
| 4 | 21% |
| 6 | **9.9%** |
| 8 | **4.6%** |

Measured on a stand-in basemap (white streets, dark labels, CARTO's land colour): the land falls
from luminance **0.81 to 0.08** and the white streets from **1.00 to 0.10** between one layer and six.

### What shipped

Each of *n* stacked highlights takes `alpha = 1 - 0.68^(1/n)`, which composites to exactly 68% at
any *n*. One sentence: **the stack never costs more than one layer's worth.** At n=1 that evaluates
to 0.32, so a single layer is untouched — verified pixel-identical, 0 px differ.

Measured on the built preview: 1 → 0.3200, 2 → 0.1754, 3 → 0.1206, 4 → 0.0919, 6 → 0.0623, with
the composite reading 68.0% at every count.

### Why this needed no engine release

Every function involved — `highlightStyleFor`, `fadedStyle`, `scaledFillOpacity`,
`scaleFactorForActiveCount` — lives inside the `layer-registry` fence. But **Leaflet writes
`fill-opacity` as a presentation attribute**, and CSS outranks presentation attributes. So a
fork-local rule reading a custom property wins outright, with no `!important` and no fence edit.
Confirmed empirically rather than assumed: Leaflet still writes `fill-opacity="0.32"` and the
*computed* value comes out as the variable.

Two implementation choices worth keeping:

- **Counted off the DOM, not `activeLayerCount()`.** What matters is how many highlights are
  actually PAINTED: an outline-only layer contributes no fill, and neither does a layer whose
  region does not contain the point. Counting `path.region-highlight` gets the real stack.
- **Driven by a MutationObserver on the overlay pane**, filtered to `class` and `childList` —
  precisely how the engine marks and unmarks a highlight — so point moves, toggles and coverage
  changes are all covered without hooking a fenced function. Setting a custom property on `<html>`
  mutates nothing inside the pane, so it cannot feed itself, and a rAF debounce makes a burst of
  `setStyle` calls during one sweep cost a single recompute.

**Not addressed, and the next thing a reader would notice:** each matched region also draws a
`weight: 4, opacity: 1` outline, so six layers means six heavy lines. Far less damaging than the
fill — the lines are signal, and they do not stack on the same pixels — so it is recorded rather
than changed. **At adoption** the honest fix is for the engine to scale the highlight the way it
already scales base fills, so the siblings get it too.

## The highlight outlines follow the fills (operator-directed, 2026-08-21)

The fill fix left the map's remaining murk in two places, both flagged rather than taken at the
time. Asked for, and now done.

**The drop shadow is a singleton affordance.** `.region-highlight` carries **two** stacked
near-black `drop-shadow()`s, so six active layers put **twenty-four** blurred darkenings across the
view — every one centred on a boundary the reader is trying to follow. What the shadow says
("this region is lifted off the faded rest of its layer") is said perfectly by one and not at all
by six. So: full at one highlight, a single lighter shadow at two, `none` from three on, where the
stroke alone already separates matched from faded.

Held as a variable containing the WHOLE filter rather than an alpha inside it, so switching it off
yields `filter: none` instead of two zero-alpha drop-shadows still being rasterised — this app
measured stacked `drop-shadow()` at **~3.7x pan-frame cost** (OPTIMIZATION_PLAYBOOK P9/R2-5), so a
free one is worth taking. Verified that the engine's own `.map-panning .region-highlight { filter:
none }` still wins on specificity — two classes to one — so that optimisation is untouched:
measured `none` while panning and the shadow back at rest.

**The outline tapers, it does not vanish.** Unlike the fill, each outline is a DIFFERENT district
the reader may want to trace, so this is signal, not decoration. Weight goes `max(2.25, 4 −
0.45(n−1))` — 4px at one layer, 2.25px floor from five on. That still reads heavier than a faded
sibling, which the engine draws at weight−0.5 and opacity 0.18. **Stroke opacity stays at 1**
deliberately: thinning a line keeps it legible where dimming it would not.

### Measured, six active layers, same patch

| | street luminance | land luminance | separation |
|---|---|---|---|
| before both fixes | 0.104 | 0.077 | 0.027 |
| **after both fixes** | **0.651** | **0.540** | **0.111** |
| no layers at all (ceiling) | 1.000 | 0.808 | 0.192 |

Street/land separation recovers from 14% of the unobstructed baseline to **58%**, with six
districts still individually traceable. The single-layer case is untouched at every property —
fill 0.32, stroke 4px, both shadows — so nothing changes for the common case.

Same mechanism as the fill: Leaflet writes `stroke-width` as a presentation attribute, which CSS
outranks, so this too costs no engine release despite `highlightStyleFor()` and the
`.region-highlight` rule both living inside fences.

## The search bar reads the same in both themes (operator-reported, 2026-08-24)

Reported as a **layout** difference between light and dark, so it was measured as one before
anything was changed: every box in the search bar — `.map-toolbar`, `.search-shell`, `.search-row`,
the input, the Search button, `.search-extra` and its four children — read for
`getBoundingClientRect()` plus twenty computed box properties, at **390px and 1400px**, **idle and
expanded-with-a-query**, in both themes.

**Every rect was identical.** Nothing moved, nothing resized, no padding or border-width or
line-height differed anywhere in the control. Across all four states the only non-colour difference
in the entire component was one property on one element:

    .search-shell   box-shadow: none  ->  0 4px 18px rgba(0, 0, 0, 0.55)

That is a real fault and it is the one the eye was reporting. In the engine, `.search-shell` is a
**card floating over the map** — `.map-toolbar` is `position: absolute` above the tiles — so the
shell carries panel background, a border, 8px of padding and a shadow, and the shadow is what lifts
it off the basemap. This skin **relocates the toolbar into the masthead** (a markup move in the
build script, not a media query — the shell is a `.masthead` descendant in every state at every
width) and **flattens the shell to nothing**: transparent, no border, no padding, `box-shadow:
none`. The input alone is the control; the shell is now just a wrapper.

The dark block re-shadowed it anyway, grouped with `.layer-toggle-btn` and `.map-tile-banner` —
two elements that genuinely do still float over the map and genuinely do still need the lift. On
the flattened shell the same declaration painted a soft black plate roughly 210 x 60px behind the
search field, sitting on the masthead where light mode has nothing at all. So light showed a crisp
outlined input on a flat header and dark showed an input on a floating slab: **the two themes had
stopped describing the same object**, which is exactly what "the layout isn't the same" means when
no box has actually moved.

Fixed by dropping `.search-shell` from that selector list, leaving the skin's own
`.masthead .search-shell { box-shadow: none }` to govern in both themes. The comment left in its
place says why it is absent, so the next person adding a dark shadow does not put it back.

### Verification

Both builds generated from the **same** `index.html` (`e2dbaaf`), so the diff is the CSS change
alone and nothing the base moved underneath it:

| | pixels differing | bounding box |
|---|---|---|
| light theme | **0** | none |
| dark theme | 27,359 | x 798-1400, y 0-82 |

Zero in light is the guarantee that mattered — the rule is `[data-theme="dark"]`-scoped, and the
render agrees. In dark the delta is confined to the search bar's own corner of the masthead with no
knock-on anywhere else on the page. Re-measured after the fix, `.search-shell` reports
**identical** on every property.

The one remaining geometric difference between the themes is `.masthead-actions` at 0.7px, because
the theme toggle's own label is "Dark" in one and "Light" in the other. That is the control naming
what it does, not a layout bug.

Costs no engine release: `.search-shell`'s engine rule is untouched, and the change is a deletion
from a fork-local dark block that only ever existed in the skin island.

## The theme toggle stops moving the masthead (operator-reported, 2026-08-24)

The follow-up to the search-shell fix, and a **different fault with the same symptom**: the search
bar was not in the same place in the two themes. The previous round measured every box in the
control and found them identical — which was true, and at the widths measured. It was not true
everywhere, and the reason the first pass missed it is worth keeping: **the sweep ran at 390px and
1400px, and the band where the themes disagree is four pixels wide.**

### The measurement that found it

Binary-searching the width at which `.masthead-actions` stops sharing a row with the toolbar, per
theme:

| | one row from | wraps at and below | `.masthead-actions` | toggle |
|---|---|---|---|---|
| light | 1586px | 1585px | 641px | "Dark" 53px |
| dark | 1590px | 1589px | 645px | "Light" 57px |

**1586-1589px is a band where light fits on one line and dark wraps.** Wrapping also frees the
line, so `.map-toolbar`'s `flex-grow` takes the space up to its `max-width: 560px` — which is why
the dark search bar looked not merely displaced but much wider, and why the reporter's screenshots
showed one masthead of one row and one of two.

The whole 4px is the toggle: the actions row is 641 against 645, and the button is 53 against 57.
**The label names what the button does** — "Dark" while light, "Light" while dark — so the control's
own box changes with the theme, and it sits in a flex row that is one line only while it fits.

This needed the real webfont to reproduce. In the sandbox's fallback font the two labels differ by
**0.7px** and both themes wrapped at the same integer width, so the first sweep saw nothing. Barlow
was vendored (`fonts.googleapis.com` + `fonts.gstatic.com` fulfilled from disk through
`page.route`, the same trick the smoke test uses for Leaflet) and the band appeared immediately.
**A layout bug that lives in text metrics cannot be measured in a fallback font.**

### The fix

Both words ship in the DOM, stacked in one grid cell, so the button is always as wide as the wider
of them:

    .dtt-labels { display: inline-grid; justify-items: center; }
    .dtt-labels > span { grid-area: 1 / 1; }
    :root:not([data-theme="dark"]) .dtt-light,
    :root[data-theme="dark"] .dtt-dark { visibility: hidden; }

Which word shows is now a CSS question keyed on `data-theme`, so both controllers (the app's and the
FAQ page's) stop writing `textContent` and set only the accessible name. `visibility: hidden` keeps
the inactive word out of the accessibility tree as well as out of sight — the button's computed name
is "Switch to the dark theme", never "DarkLight".

Two details that are load-bearing rather than incidental. The labels are wrapped in **their own
span** instead of gridding the button, because the phone rule re-declares the button as
`inline-flex`, which would lay the two words side by side and double the width instead of
overlapping them. And the button's height is unchanged at **28.5px**, matching its neighbouring
pills exactly — the same parity the toggle's own `line-height: 12.5px` was added to preserve.

Measured after: `.masthead-actions` **645px in both themes**, threshold gap **0px**, and every box
in the masthead — masthead, actions, toolbar, search input, map — **identical** light against dark
at 1400px, 1587px and 1700px. The cost is stated plainly: pinning to the wider label means the
wrap threshold is now uniformly the dark one (1590px), so light wraps 4px earlier than it used to.
Pinning to the narrower label would clip "Light", so this is the only direction available.

### And a two-pixel misdraw that the pixel diff caught

Diffing the two builds at 1587px showed 23,393 pixels moving in the **dark** theme, where every
measured box was identical — so it was chased rather than dismissed, and it was not this change.
Tracing `#map`'s height across the load:

    base:  741px at 62ms  ->  739px at 194ms
    post:  741px at 36ms  ->  739px at 148ms

Barlow is loaded with `font-display: swap` and its metrics are not the fallback's, so **the masthead
re-lays out after Leaflet has already measured its container**. Leaflet caches the size at init and
never re-reads it, so from the swap onward the map draws two pixels out of register with the element
it lives in — every overlay, marker and the coverage wash, in both themes, for the whole session.
Nobody had noticed because two pixels of a map look like a map; it surfaced only because a hair of
extra parse work moved which frame the wash landed on. A single `map.invalidateSize({pan: false})`
on `document.fonts.ready` re-reads the box for good — verified: the cached size goes from
`[1040, 741]` against a 739px element to `[1040, 739]`, and forcing the same call by hand made the
two builds render **0 pixels apart**. Guarded, so a browser without the Font Loading API keeps
today's behaviour.

Neither change touches an ENGINE fence: the toggle is fork-local markup and skin CSS, and the
`invalidateSize` call sits in the fork-local controller that already closes over `map`.

## The pills come back up beside the search (operator-directed, 2026-08-24)

*"Move the pills closer to the search bar to narrow the masthead."* Measured first, because the
pills are **already adjacent** whenever the row is one line — at 1700px the gap between the Search
button and the first pill was exactly the row's own 28px column gap, with no slack anywhere. What
separates them is the **wrap**, and what causes the wrap is the row's minimum width:

    title 529 + gap 28 + search basis 320 + gap 28 + pills 645 + padding 40 = 1590px

which was the wrap threshold to the pixel. Below it the pills drop to a second row and the masthead
goes from **118px to 162px** — the tall, spread-out masthead the request is about.

So the thing to move is that sum. Two levers do it without touching the copy or the pill spec:

- **the inner column gap 28 -> 20** (twice over: 16px), which is also literally "closer"
- **the search's flex-basis 320 -> 250** (70px). It still `flex-grow`s to fill, so at any width
  where the row already fitted **nothing changes at all** — only the point at which it stops
  fitting moves.

Measured after: threshold **1590px -> 1530px**, and at 1560px the masthead goes 162px -> 118px in
both themes with the pills sitting immediately after the Search button. Light and dark stay
byte-for-byte identical in layout at 1400px, 1587px and 1700px, so #468's parity is intact.

**Stated as a threshold, not a cure.** Any fixed row wraps eventually; below 1530px this one still
does, and at 1400px the masthead is still two rows. If more is wanted, the remaining levers are all
look changes rather than layout ones and are deliberately left for a decision: the pill spec's own
padding (`7px 13px` / `7px 14px`), the pill font-size (12.5px), and the title block's subtitle
sentence, which is 529px of the 1590 by itself.

Two things were tried in the first draft and **dropped as measured no-ops**, which is why they are
not in the diff: a `.masthead-actions { gap: 6px }` override (the skin already sets 6px further down
the same island) and a pill-padding override (it loses to the pill spec below it). Both were
written, both changed the threshold by 0px, and both were removed rather than left in looking
load-bearing.

## The subtitle and the stamp, shortened (operator-directed, 2026-08-24)

Follows the pill move. The masthead's left column is a flex item **as wide as its widest child**,
and the three children were measured before either was touched:

| | width | note |
|---|---|---|
| subtitle (13px) | **529px** | the binding one |
| generation stamp (11px) | 430px | the next one |
| wordmark row (32px + mark) | 231px | never binding |

That arithmetic is the reason the operator asked for **both**: shortening only the subtitle would
have bought 99px and then stopped dead at the stamp. Cutting one without the other is wasted work,
and the column would have looked untouched below 430px.

**Subtitle**, 529px → **371px**: *"Click the map or search an address to see every district that
covers it, and who represents it."* → *"Click the map for every district you're in, and who
represents you."* What went is the naming of the search box, which now sits **immediately to the
right in the same row** since the pill move and is labelled "Search an Illinois address" — a
sentence spending 158px to point at a control the reader is already looking at. What stayed is both
halves of the promise, the districts and the people, because that pairing is the product. The
trailing "represents **it**" also became "represents **you**", which is what was meant: a district
does not have a representative on its own behalf.

Rewritten **in the preview only** — the transform already rewrote that line to append the stamp, so
this is one more substitution in the same `sub_once`. `index.html` keeps its own subtitle and is
byte-unchanged.

**Stamp**, 430px → **250px**: *"districtry re-skin preview (unlisted) — generated from index.html @
`<sha>` on `<date>`"* → *"unlisted preview · index.html @ `<sha>` · `<date>`"*. It has to carry
exactly four facts — unlisted, generated, from which commit, and when — and all four survive; what
went was re-announcing the brand to a reader looking straight at the wordmark above it. `STAMP_RE`
reads whatever text is committed and rebuilds with it, so `--check` is indifferent to the format.

The FAQ page's footer opened *"Unlisted re-skin preview."* and then printed the stamp two sentences
later, so with the new wording it said "unlisted" twice in one paragraph. The lead-in went; the
stamp says it.

### Measured

| | before | after |
|---|---|---|
| title column | 529px | **371px** |
| masthead one row from | 1530px | **1372px** |
| masthead height at 1400px | 162px | **118px** |
| map height at 1400px | 838px | **882px** |

The threshold moved by exactly the 158px the column lost, which is the check that nothing else
changed. **1400px now sits on one row where it wrapped before**, and the map takes back the 44px the
second row was holding. Light against dark is **identical at 1400px, 1530px and 1700px** — the
toggle fix holds. Gates green including the smoke test against both `index.html` and the preview.

## The state code becomes the fleet switch (operator-directed, 2026-08-24)

Hovering `/ il` in the wordmark now opens a menu of the other explorers, and the panel foot's
"Explore another metro" row is retired. Both halves of one idea: the fleet belongs beside the name
of the thing you are looking at, not at the bottom of a column nobody scrolls.

**On Wisconsin — this record was wrong for about an hour, and here is the correction.** The
operator asked for "NYC, SF, and wi". When this shipped, `metros.json` — the fleet's single source,
from which `--sync-fleet` projects each fork's `METRO_EXPLORERS` — held exactly three entries, and
nothing in *this* repo referenced a WI fork, so the change went out saying there was no such thing.
**There is.** `ThursdaysFamous/DistrictExplorer-WI` was created at 03:39 UTC on 2026-08-24, about
fifteen minutes before that claim was written, and it is **the first state through the template
route**; #474 landed on `main` the same evening fixing a localization fingerprint that
`wi.chidistricts.com` itself had tripped. **Searching one repository is not searching the fleet** —
`list_repos` answers in a single call what no `grep` across this tree can.

**It is still not in the menu, and that is now a measurement rather than an oversight.**
`wi.chidistricts.com` has **no DNS record** — NYC and SF both resolve to `thursdaysfamous.github.io`
and WI resolves to nothing — so the site is not live and a link to it would be dead on arrival,
which is the exact thing `validate_card_links.py` exists to catch. `metros.json`'s own comment makes
adding an entry a **launch** step rather than a pre-launch one, and it is not a local step either:
`--sync-fleet` projects that entry into every fork, so a WI row would appear in the LIVE Chicago
app's footer and its metro portal, not only in this preview.

So the menu ships the two that are reachable. **It is built from `METRO_EXPLORERS` rather than from
a hand-written list precisely so the third costs nothing here**: point the subdomain, add the entry
to `metros.json`, `--sync-fleet` into the worksheet, regenerate, and Wisconsin appears in the menu,
in the portal, and in the (hidden) footer row together — with no change to any of this code.

### What it is

The state code becomes a `<button>` inside a positioned wrapper, with an empty `role="menu"` span
that the controller fills at boot. It skips the current metro the way `renderMetroLinks()` does —
you do not offer someone the page they are on — and if that leaves nothing, it **unwraps itself back
into the plain `<span class="title-metro">`**, which is what a one-metro fleet should look like.

Opening is CSS: `:hover` and `:focus-within`, so mouse and keyboard both work with no script. Three
details that are the difference between a menu and a nuisance:

- **The gap is bridged.** The menu sits 8px below the button, and that 8px belongs to no element, so
  a pointer travelling down would drop `:hover` halfway and shut the menu in its own face. An
  invisible strip is drawn as a **child of the menu**, so crossing it keeps
  `.dst-metro-switch:hover` true.
- **Escape actually closes it.** `:focus-within` holds the menu open, and Escape returns focus to
  the button — which is still inside the switch — so without help the only dismissal a keyboard has
  does nothing. A `data-dismissed` flag beats the hover rules on source order, and clears on
  `mouseleave` and on focus leaving the wrapper, so it can never latch the menu shut. Verified:
  focus opens, Escape closes and holds, focus elsewhere re-arms, focus back opens, Tab walks into
  the links.
- **Touch has no hover.** The button also owns a real `aria-expanded` that a tap toggles, an
  outside click closes, and `focusout` closes — the same attribute that keeps the control honest to
  a screen reader. Its accessible name reads "Illinois — switch explorer".

`.title-text` lowercases everything beneath it, which is right for the wordmark and wrong for place
names, so the menu resets `text-transform`.

### The footer row is hidden, not deleted

`#footer-metros` sits inside the `metro-links-html` ENGINE fence, and the engine's
`renderMetroLinks()` does `getElementById(...)` then `appendChild` **with no null guard** — removing
the element would throw at boot and take the rest of the boot tail with it. So it is hidden in CSS
and the engine goes on filling it, exactly as the masthead star is hidden rather than removed.
Verified after: the row computes `display: none` and still holds its two engine-rendered links.

Nothing here touches a fence: the wordmark is fork-local markup, the styles are skin-island, and the
controller is inserted **after** `ENGINE:END metro-links`, which is where `METRO_EXPLORERS` and
`THIS_METRO` are both in scope and where the engine has just finished with the row.

Measured: menu 208×99px opening under the state code, painting **over** the map (its own links
answer `elementFromPoint` 45px below the masthead's edge), identical in both themes, no page errors,
and the title column unchanged at 371px — the switch adds a caret, not a row.

## Known package flaws / adoption fix-list

- `pwa/head-snippet.html` uses a **relative** `og:image` — scrapers require an absolute URL;
  fix at adoption.
- ~~`manifest.webmanifest` `start_url: ./index.html`~~ — **resolved at adoption (2026-08-24).**
  The generated manifests use `start_url: "./"`, which is what the service worker precaches; the
  package's `./index.html` would have made an installed app's first offline launch miss the shell
  cache. (Navigations are network-first with a `"./"` fallback, so a deep `/index.html` bookmark
  still boots offline — see `OPTIMIZATION_PLAYBOOK.md` item 22.)
- Mockup stats are hand-set snapshots and will drift (the 60→69 fix is already one instance);
  production surfaces must derive counts from the worksheet, never hardcode them.
- Dark-mode tokens exist in the tokens file; dark mode itself is out of scope until approved.
- The canvases need network to unpkg (React, SRI-pinned) — blank page offline/sandboxed; the
  landing page is framework-free so the microsite index always renders.

## Invariants for anyone touching this work

- Never place a file in root `data/app/` for the preview — `validate_index.py` fails the deploy
  on any JSON there that no sw.js cache list names.
- Never edit inside ENGINE or GENERATED fences for preview work; the Stage B skin is an appended
  override island.
- The preview stays out of `sitemap.xml` and is never linked from `index.html`/`sources.html`
  (linking from index.html would also drag its URLs into gate surfaces).
- Root filename collisions to avoid: `manifest.webmanifest`, `og-image.png`,
  `icons/icon-192/512.png` are SHELL_URLS-pinned — districtry assets keep distinct names/paths
  until the adoption step swaps them in place.
- **A skin hunk that styles something is not the same as shipping it.** The coverage key and the
  panel head both shipped as CSS with no markup and stayed that way through a release, because
  nothing in this repo fails when a rule has no subject. When adopting a design that adds an
  element rather than restyling one, adopt the JavaScript that builds it in the same change, and
  open the page.
- **A legend may only name what was drawn.** `buildCoverageKey()` takes the bands the draw
  produced, not the bands the worksheet declares. A label with no geometry behind it is a claim
  the map does not support, which is the honesty rule applied to chrome.
- **Engine blocks are edited in `engine/`, never in an instance file.** `compose_app.py --check`
  is what notices; it is also what caught this work editing all four `index.html` files directly.
  Edit `engine/index.html/<block>.txt` and recompose.
