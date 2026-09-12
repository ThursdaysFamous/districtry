# Engine Sync — keeping the metro forks' shared engine identical

*This file is itself part of the shared engine: the SAME copy ships in every
metro fork. Never edit it in one fork only.*

> **SUPERSEDED AGAIN — R2.1 (recorded 2026-09-02).** The release channel the
> note below describes was itself retired when the forks became folders of
> this one repo: there is ONE copy of every block under `engine/`,
> `scripts/compose_app.py` splices it into every instance and its `--check`
> is the CI gate; `engine.lock.json`, `apply_engine.py`, `engine-bump.yml` and
> the release workflows no longer exist (`docs/DEV_PROCESS_ASSESSMENT.md`).
> What survives of this file is the block inventory — which omits the two
> `engine/shared/` blocks; `ls engine/` is the authority — and the tombstone
> convention. Read it as history, not procedure.
> \
> **The flag that assertion used is gone too (2026-09-12).**
> `check_engine_parity.py --against-bundle` read an `engine.manifest.json`
> that `apply_engine.py` produced, so it could not run once both were deleted;
> it was removed rather than left as a mode that names three absent files.
> `scripts/compose_app.py --check` asserts the splice now, against `engine/`
> rather than a downloaded artifact, and
> `check_engine_parity.py --fleet` compares every instance's fence interiors
> and names the blocks only some instances carry.
>
> **SUPERSEDED IN PART — 2026-07-13.** The manual porting loop below (struck
> through) is retired by `docs/MECHANIZATION_PLAYBOOK.md` Conversion 1 in the
> Chicago repo: the engine is now distributed as a **published, hash-verified
> release artifact**. Each fork pins a version + sha256 in `engine.lock.json`;
> deploy-time assembly downloads the pinned release, verifies the hash,
> splices the ENGINE blocks between the fences, and asserts the result
> (`apply_engine.py`, then `check_engine_parity.py --against-bundle … --strict`);
> new releases fan out as gated `engine-bump.yml` PRs that also refresh the
> shared scripts. Parity is true by construction — nobody hand-ports engine
> diffs between forks anymore. The demotion condition (first automated bump
> PR merged green in NYC) fired with DistrictExplorer-NYC#23.
>
> What survives unchanged: the fences (now assembly markers), the METRO
> config seam, the block inventory, and the principle **"port the diff, not
> the prompt"** — the release artifact IS the diff, distributed mechanically.
> The "model" section below still describes how engine code is written;
> only the human porting loop is gone.

## The problem this solves

Each District Explorer metro is its own fork — separate repo, separate site,
separate data layers (see `docs/METRO_EXPANSION_PLAYBOOK.md`, which lives in
the Chicago repo). But ~60% of `index.html` is a metro-agnostic engine, and
"apply the same feature to every fork" **cannot be done by giving each fork's
coding session the same prose prompt**. A prompt is a lossy spec: the same
request produced two different "Explore other metros" footers (different
element ids, class names, label text, and list format) in Chicago and NYC.
Multiply that by every engine change and the forks stop being the same app.

**The rule: port the diff, not the prompt.**

## The model

- **Chicago (`DistrictExplorer-CHI`) is the reference implementation.** A
  region-agnostic engine change lands there first (or, if it was born in
  another fork, is backported there first). Chicago's copy of an engine block
  is canonical whenever forks disagree.
- **Engine code is fenced** so "region-agnostic" is machine-checkable, not a
  judgement call:

  ```js
  /* ==== ENGINE:BEGIN block-name ==== */
  ...byte-identical in every fork...
  /* ==== ENGINE:END block-name ==== */
  ```

  HTML regions use the same markers inside `<!-- ... -->` comments. Blocks
  cannot nest; names are unique per file.
- **Everything metro-specific that engine code needs lives in the `METRO`
  config block** near the top of the script (`/* ==== METRO:BEGIN config
  ==== */`): `THIS_METRO`, `METRO_NAME`, `METRO_BBOX`, `METRO_CENTER`,
  `PERMALINK_GATE`, `SOCRATA_HOST`, `SOCRATA_APP_TOKEN`, `REPO_ISSUES`,
  `FEEDBACK_SUBJECT`, `METRO_EXPLORERS`. An engine block may *reference* these
  names but never defines them. If a new engine block needs a per-city value,
  add a config variable — don't inline the value.
- Code outside ENGINE fences is the fork's own (layer modules, branding,
  marker art, geocoder provider, city constants). It never has to match.
- Fences pin a block's **content**, not its **position**. Where position is
  user-visible it is part of the contract too: `metro-links-html` sits between
  the source-attribution row (`.footer-sources`) and the footer-links row
  (`.footer-links`, the bug-report/source/sponsor line) in every fork. The
  parity check cannot see placement, so a port places the block at the same
  relative slot by hand — a mismatch is drift all the same (CHI and NYC
  shipped the "Explore another metro" row on opposite sides of the bug-report
  row before this rule was written down).

  **`gaps-html` moved out of that footer row and into the masthead**
  (2026-08-18). It sits in a `.masthead-actions` row directly under the
  `h1.title`, pinned right of the wordmark, in all three forks. The reason is
  the one the panel exists for — it is the standing caveat on every answer the
  app gives, and at the bottom of a long page a reader concluded the app was
  wrong before ever finding it. **This cost no engine release, and that is the
  pattern worth copying:** the fence and its body moved *verbatim*, so the
  block's bytes are unchanged, the deploy-time splice is a no-op, and the
  masthead treatment is applied from OUTSIDE the fence by a fork-owned
  `.masthead-actions .footer-link-btn` rule. Restyling the button by editing
  the fence would have owed a release and a fan-out; wrapping it did not. Born
  in CHI (#367/#368), ported to NYC (#84) and SF (#47) the same day. Each
  fork's `smoke_test.mjs` now pins the placement, because nothing else can:
  the fences pin a block's bytes, never its position, and every other check
  clicks the button by id.

## The porting workflow (superseded 2026-07-13 — see banner above)

The release workflow that replaces this loop: an engine change lands in
Chicago inside the fences → a reviewed PR bumps `engine.lock.json` → the
`engine-v*` tag publishes an immutable release (`release-engine.yml`
self-checks round-trip + gates before publishing) → the fan-out opens a
gated bump PR in every sibling → each fork's deploy assembles and asserts
the pinned bytes. Fork-born engine improvements still land in Chicago first,
as reviewed PRs, then ship in the next release.

1. ~~**Make the change in the Chicago repo**, inside the relevant ENGINE
   block(s) (or add a new block). Run the gates; commit with a message that
   names the blocks touched, e.g. `engine(metro-links): …`.~~
2. ~~**Port to each sibling by handing its session the actual diff** —
   `git show <sha>` output, or the PR's `.diff` URL — with the standing
   instruction: *"Apply this engine diff verbatim. Text inside ENGINE blocks
   must be byte-identical after the port; only METRO config values may
   differ. Then run `python3 scripts/check_engine_parity.py index.html
   --against <chicago file or https://chidistricts.com/> --strict` and the
   repo's normal gates."*~~
3. ~~**Verify before pushing**: the parity check must report the ported blocks
   identical. If a hunk doesn't apply because the fork genuinely diverges
   there, that code wasn't engine — either reconcile it first or move it out
   of the fence; never "adapt" a hunk inside a fence.~~
4. ~~New-metro forks inherit the fences by construction (they start as a clone
   of Chicago), so this protocol applies from their first commit.~~ New-metro
   forks now start from a clone of Chicago and **add** the consumer half of the
   artifact model — `engine.lock.json`, `apply_engine.py`, the *consumer*
   `engine-bump.yml`, and the deploy assembly steps. (Chicago itself carries
   only the *producer* side: `release-engine.yml` + `create-engine-tag.yml`;
   it has no `engine-bump.yml`.) The artifact model applies from the fork's
   first commit.

## The tooling

- `scripts/build_engine_artifact.py` (Chicago only) — builds the
  byte-deterministic `engine.bundle.js` + `engine.manifest.json` a release
  publishes; `scripts/apply_engine.py` (every fork) — downloads, hash-verifies
  against `engine.lock.json`, and splices the pinned release between the
  fences, failing hard with nothing written on any mismatch. Both ship as
  release assets — the release is the shared scripts' distribution channel,
  and bump PRs refresh them automatically.

  > **A shared-script change must be inert in a fork that hasn't opted in.**
  > `generate_metro_files.py` and `metro-worksheet.schema.json` ride the same
  > channel, and the consumer `engine-bump.yml` **applies the release and copies
  > the scripts but never runs the generator** — it only validates afterwards.
  > So a generator change that emits *any* new GENERATED-region content fails
  > every sibling's drift gate, and a schema change that adds a `required` key
  > fails their worksheet validation. Neither is caught on this side: Chicago's
  > worksheet has whatever the change needs, so its own gates stay green, and
  > the release job's self-checks exercise the *bundle*, which never reads a
  > worksheet. Both failure modes were shipped for real in the same week
  > (`engine-v1.0.16` made a key required; `v1.0.17`'s default-and-always-emit
  > fix then tripped the drift gate instead; `v1.0.18` made emission
  > conditional). The working rule is stronger than "default to the old value":
  > **a fork that has not opted in must see a byte-identical file.** Gate a new
  > emitted line behind `if "<key>" in w:` and keep the key optional. The
  > eventual structural fix is for `engine-bump.yml` to regenerate after
  > applying — that lives in the sibling repos, so it is a coordinated change,
  > not a Chicago one.
- `scripts/check_engine_parity.py` — extract, lint, and compare ENGINE
  blocks. Lint mode (`… index.html`) runs in `deploy-pages.yml`, against
  `il/index.html` and `il/sw.js`. **The `--against-bundle` post-assembly
  assertion this bullet used to describe was removed on 2026-09-12**, with
  `apply_engine.py` and `engine.manifest.json`, which it read, already deleted
  at R2.1. `compose_app.py --check` asserts the splice now. `--fleet`
  (added 2026-09-12, runs in `smoke-test.yml`) compares every instance's fence
  interiors and reports the blocks only some instances carry. The compare mode
  (`--against <path-or-URL>`) remains for reading a deployed page.
- **Cutting a release is three steps, and the middle of it races the deploy.**
  Bump `engine.lock.json` on main → `create-engine-tag.yml` → `release-engine.yml`
  at the new tag ref (a tag created with `GITHUB_TOKEN` does not fire
  `on:push:tags`, hence the separate dispatch). The bump merge fires
  `deploy-pages.yml` immediately, so for the minutes until the release
  publishes, **main legitimately pins a release that does not exist** and the
  deploy's `gh release download` fails with a bare `release not found`. That is
  not a broken pin — it is the window, and it cost a manual re-run on both
  `engine-v1.0.17` and `v1.0.18` before being fixed. Two guards now close it,
  either of which is sufficient alone: the deploy **waits** up to 15 minutes for
  the release it pins (already-published costs one API call and no delay), and
  `release-engine.yml` **re-dispatches** the deploy after publishing when main
  pins that release — so a deploy that timed out, or failed before the fix,
  heals without anyone touching it. Do not "fix" a red deploy in that window by
  reverting the pin; publish the release.
- `.github/workflows/engine-parity.yml` — the old scheduled cross-fork
  watcher, superseded by construction. Siblings carry no copy (NYC deleted
  its under work order 1.6 after its first clean assembled deploy; SF's
  inherited copy was removed 2026-07). **Decision (2026-07): Chicago's weekly
  run is retained indefinitely** as a deployed-site belt-and-suspenders check
  — it costs one scheduled job and catches the class of drift the assemble
  gate can't (a fork deploying outside the pipeline).

## Definition of done for fork-born engine improvements (Conversion 3)

An engine-quality improvement born in a fork (a new validator check, a
hardened loader, a factory fix) is **not done when the fork's PR merges — it
is done when the CHI release containing the back-port is tagged.** Every
fork's `validate_index.py` declares a module-level `CAPABILITIES` list
(kebab-case strings, one per check the code actually performs; CHI's copy
defines the shape). The weekly fleet-status workflow in the CHI repo diffs
each fork's list against CHI's: a capability present in a fork but absent in
CHI is a **reverse-parity WARN** on the fleet-status tracking issue, and it
stays there until the CHI release ships. The fork PR description must link
that tracking issue. Discretionary back-porting is dead; the WARN is the
debt collector.

> **A new ENGINE block breaks the REFERENCE fork's own deploy, immediately.**
> The mirror image of the sibling trap below, and it is not caught by any PR
> gate: `check_engine_parity.py` lints Chicago's fences against Chicago's file
> and is happy, while `deploy-pages.yml`'s assemble step is the first thing that
> compares them to the *pinned* manifest — where it fails with
> `apply-engine: FAIL — fence-count mismatch: index.html has ENGINE block(s) the
> manifest does not know`. So a new block is **not shippable in one PR**: the
> block lands green, the deploy then fails, and the release that ships the block
> is what repairs it. Cut that release in the same sitting (learned shipping
> `engine-v1.0.19`, the Data gaps panel).

**Releases that ship NEW blocks need sibling fence seeding first**
(learned shipping engine-v1.0.10, backlog item 11): `apply_engine.py`
fills existing fences only — it cannot decide where a brand-new block
belongs in a fork's file — so before (or immediately after) tagging such a
release, land a markers-only PR in each sibling adding the empty
`ENGINE:BEGIN/END` pair at the reference fork's placement; the bump then
splices the pinned body in. Without it the sibling's `engine-bump` run
fails with "index.html is missing ENGINE block(s) the manifest requires".
Note the re-run trap: a failed `repository_dispatch` run RE-RUNS at its
original head SHA — after fixing the fork's main, trigger a fresh fan-out
(re-run the CHI release workflow; publish self-skips, dispatch repeats)
rather than re-running the failed sibling run.

> **"Nothing outside the fences" is a claim about the ENGINE, not about the
> RELEASE.** Changing what `generate_metro_files.py` EMITS is an engine-adjacent
> change that no fence contains, and a bump PR cannot apply it: the generator
> is a script, its output lands in a GENERATED region of each fork's own files,
> and the code that CONSUMES the new output may sit outside every generated
> region. Learned shipping `engine-v1.0.22`, whose changelog said adopting forks
> needed "nothing outside the fences" — true of the two changed blocks, wrong
> about the release. The fork half of that change (a new `DYNAMIC_REFERENCE`
> frozenset emitted into the validator-config region, plus the two-line check in
> `validate_index.py` that reads it) meant both siblings' bump PRs failed CI in
> nine seconds on `generate_metro_files.py --check` drift, and had to be fixed
> by hand on their `bot/engine-bump` branches: regenerate the region, then patch
> the consuming line.
>
> So: **before tagging a release, ask separately whether the change touches the
> GENERATOR'S OUTPUT SHAPE.** If it does, the release needs the same treatment
> as a new ENGINE block — land the regeneration and any out-of-region consumer
> in each sibling (a small PR, or in the bump branch before merging), and say so
> in the changelog. A changelog that promises a clean adoption and doesn't
> deliver one costs every sibling a red CI run and a manual repair.

## Current ENGINE block inventory (61 in index.html + 2 in sw.js)

index.html: `app-token`, `arcgis-loader`, `arcgis-paged-loader`,
`basemap`, `body-map-toolbar`, `brand-names`, `cached-loaders`, `card-helpers`,
`chamber-factory`, `county-layer-dispatcher`, `coverage-gaps`,
`cps-network-factory`, `districtry-behavior`, `districtry-theme`,
`exports`, `extract-district-number`, `feedback`,
`fetch-retry`, `find-prop-ci`, `footer-independence`, `gaps-html`,
`gaps-modal-html`,
`geocoder-search`, `geocoder-shell`, `geolocation`, `groups`, `haversine`,
`hover-explorer`, `int-field`, `layer-registry`, `map-chrome-classes`,
`map-pan-filter`, `metro-links`, `metro-links-html`, `metro-portal`,
`nearest-point-factory`, `office-helpers`, `overlay-cards`, `permalink`,
`poi-geocode`, `point-in-polygon`, `polygon-containment`,
`polygon-factory`, `probe-geometry-column`, `relationship-pinning`,
`render-helper`, `sanitize`, `school-zone-factory`, `scope-mask`,
`selection-controls`, `socrata-loader`, `socrata-point-loader`, `state`,
`styles-app`, `styles-card-v2`, `styles-core`, `styles-districtry-skin`,
`styles-footer`, `styles-hover-responsive`, `styles-markers`,
`styles-sibling-result`.
(Count and list re-synced against `check_engine_parity.py` output while
adding the two card blocks — the previous list said 45 but had drifted,
missing `map-chrome-classes`, `map-pan-filter`, and `styles-markers`.
Re-synced again 2026-08-26 while promoting `districtry-behavior`: the list
had drifted a second time, missing `body-map-toolbar`, `districtry-theme`
and `styles-districtry-skin` — the skin blocks that shipped with the
redesign. Re-synced a third time 2026-09-12: the list said 59 against 61
real fences, missing `footer-independence` (added 2026-09-11 by #885) and
`county-layer-dispatcher` (added by #903). Neither PR updated this list,
and no gate fails on it — `scripts/fleet_status.py` names the missing
blocks, but it is WARN-only on a weekly issue, so a stale list stays
stale until someone reads that issue. The count line is a claim
`check_engine_parity.py` can refute; re-run it whenever a fence is added.)

(`basemap` — promoted 2026-08-26, the day the basemap went vector: the
CARTO-vector-with-raster-fallback boot, the WebGL2 probe and half-added-layer
unwind, and the dual tile-failure banner wiring, all previously a 5-line
unfenced raster block and now ~140 shared lines the fenced `districtry-theme`
and `exports` blocks reach into (`baseTiles`, `baseIsVector`, `baseStyleUrl`,
`baseRasterUrl`, `baseStyleRequested`). Fenced for the same reason
`districtry-behavior` was: shared code that fenced code depends on must not
sit where no gate watches it. The MapLibre canvas-scaffold CSS stays unfenced
beside the inlined Leaflet CSS on the same footing — third-party support
rules, byte-stable, with the re-inline command in the comment.)

(`districtry-behavior` — promoted 2026-08-26 — is the skin's companion
JS: highlight-alpha compositing for stacked selections, the mobile
"show only my layers" collapse, the legend's phone-default disclosure,
and `dstPlaceDoors`, which moves the masthead's four "about the data"
doors into the results-panel foot below 768px. It was born as unfenced
Chicago tail code in the 2026-08-21 mobile review while the skin CSS
that DEPENDS on it went into the engine — so every other instance
rendered the masthead doors absolutely-positioned over the brand on
phones with nothing relocating them, which is exactly the drift class
this file exists to prevent. The block is DOM-generic (engine-skin class
names only); it sits at the tail of the init function, after the
`districtry-theme` fence.)

(`card-helpers` + `styles-card-v2` are the card-system redesign surface —
docs/CARD_RENDER_API.md. `renderFieldList` and its `.result-row` CSS were
retired in engine-v1.0.13 once the fleet-wide grep hit zero call sites;
`render-helper` is kept as an empty tombstone-comment fence rather than
deleted — see the retirement note under the sequencing section below.)

(`geocoder-shell`/`geocoder-search`/`poi-geocode` fence the geocoder UI —
search-shell expander, result rendering, submit/debounce wiring, the
sibling-metro search fallback, and the serial >=1s POI queue. They call
three fork-defined providers, declared with each fork's unfenced GEOCODER
section: `geocodeAddress()` (city-scoped type-ahead), `geocodeUnbounded()`
(whole-coverage, feeds the sibling lookup), and `poiGeocodeRequest()`
(office-address pin lookup). Provider code stays unfenced even where the
forks' implementations currently coincide — the provider choice is
per-metro by design.)

(`layer-registry`/`overlay-cards` fence the registry, styling/highlight
machinery, and card framework; `HIGHLIGHT_CLASS`/`POI_PIN_CLASS` are METRO
config so the fork-branded CSS class names stay out of the fences. The
factory blocks keep their Chicago-born function names (`registerIlgaChamber`,
`registerCpsNetwork`) as shared engine names; per-city dataset schemas enter
through fork-side wrapper functions at the call sites — Chicago's
`registerCpsZone`, NYC's `registerNycZone` — so the fenced factories never
carry a city key list.)

sw.js: `sw-header`, `sw-handlers` — the config between them (cache name +
URL lists) is the service worker's METRO section.

(The four `styles-*` blocks fence the shared layout CSS on the neutral
`--accent`/`--accent-deep`/`--accent-warm`/`--accent-warm-deep` custom
properties; each fork's `:root` palette *values* stay fork code, as do the
fork-only style islands between the fences — see backlog item 6's leftovers.)

(`metro-portal` — the sibling-metro portal easter egg — reads per-metro
`bbox`/`emoji` fields on `METRO_EXPLORERS` entries; its card CSS is engine
too (inside `styles-app`), as are the `.sibling-result*` styles
(`styles-sibling-result`). It sits between the `feedback` fence and the
geocoder.
Entries without a bbox opt out of the portal; overlapping bboxes resolve to
the nearest bbox center; per-metro dismissals re-arm on leaving that bbox —
all so the block survives N metros unchanged. Each fork's
`validate_index.py` lints the list (see that script). The *search* trigger —
one unbounded retry of a zero-result query, hits classified into sibling
bboxes via `siblingMetroAt`, matches rendered as hand-off rows — is fenced
in `geocoder-search`, with the whole-coverage lookup behind the fork's
`geocodeUnbounded()` provider.)

(`scope-mask` shows the seam pattern for engine code that needs a per-metro
*function*, not a config constant: `drawOutOfScopeMask(loadCoverageGeometry)`
takes the fork's coverage-geometry loader as a parameter at its unfenced BOOT
call site, so the block body stays byte-identical. The geocoder blocks use
the same shape via their three fork-defined provider functions.)

Growing this inventory is encouraged: when you touch shared-looking code that
isn't fenced yet, reconcile it across forks and fence it as part of the
change.

## Reconciliation backlog (known structural drift, July 2026)

These engine-quality areas had forked between Chicago and NYC before the
fences existed. **All of them are now reconciled and fenced** — the struck
entries below record what moved where. When new shared-looking drift
appears, start a fresh numbered entry here: drift can run in *both*
directions, so reconciling means merging features, not overwriting:

1. ~~Geocoder (search box + POI geocode)~~ — **resolved July 2026**: the
   engine UI (search-shell expander, result rendering, submit/debounce
   wiring, the sibling-metro search fallback, and the serial >=1s POI
   queue + address cleaner) is fenced as `geocoder-shell` /
   `geocoder-search` / `poi-geocode`. Each fork defines three providers
   with its unfenced GEOCODER section: `geocodeAddress()` (type-ahead,
   city-scoped), `geocodeUnbounded()` (whole-coverage, for the sibling
   lookup), and `poiGeocodeRequest()` (office-address pin lookup) —
   Chicago: Photon / Photon / Nominatim; NYC: GeoSearch / Photon /
   GeoSearch. The sibling-search fallback thereby reached NYC (with the
   `styles-sibling-result` CSS and a Photon/OSM credit in its footer);
   provider code stays unfenced even where the forks currently coincide,
   because the provider choice is per-metro by design.
2. ~~Result-card / overlay styling framework + factories~~ — **resolved July
   2026**: NYC adopted Chicago's `styleForFeature` threading (a dormant seam
   there until a layer defines it), the factories were reconciled to byte
   parity and fenced (`polygon-factory`, `nearest-point-factory`,
   `school-zone-factory`, `cps-network-factory`, `chamber-factory`,
   `office-helpers`, `int-field`), and the registry + card framework fenced
   as `groups`/`layer-registry`/`overlay-cards`. The school-zone merge moved
   city dataset schemas into opts fed by fork wrappers (`registerCpsZone` /
   `registerNycZone`) and converged Chicago's card headline on NYC's more
   precise "Zoned school" copy; the chamber merge kept Chicago's ILGA copy
   via `profileLabel`/`directoryLabel`/`capitolLabel` opts at its call sites.
3. ~~Hover explorer~~ — **resolved July 2026**: NYC adopted the
   `hoverDotColor` per-feature dot override (dormant there until a layer
   defines it), `HOVER_NUMBER_KEYS`/`HOVER_NAME_KEYS` moved into each fork's
   METRO config block (they are city dataset vocabulary, per their own
   comments), and the machinery is fenced as `hover-explorer`,
   `relationship-pinning`, and `extract-district-number`.
4. ~~`LAYER_AREA_RANK`/`LAYER_ORDER` + `GROUPS`~~ — **resolved July 2026**
   with (2): `GROUPS` turned out identical and is fenced, and the consuming
   machinery (`reorderActiveLayers`, the highlight/rescale sweeps) is fenced
   inside `layer-registry`. `LAYER_AREA_RANK`'s entries stay city data
   outside the fences, as designed.
5. ~~Exports namespace~~ — **resolved July 2026**: the member list is built
   in the fenced `exports` block (`var EXPLORER_EXPORTS = {…}`); only the
   fork-branded window assignment (`window.ChiExplorer` /
   `window.NycExplorer`, twinned with each fork's `smoke_test.mjs`) stays
   fork code. The `.chi-*`/`.nyc-*` CSS class prefixes on the marker /
   region-highlight styles were the same flavor of namespace drift —
   **resolved in item 10.**
6. ~~CSS palette namespace~~ — **resolved July 2026**: both palettes renamed
   to neutral `--accent`/`--accent-deep`/`--accent-warm`/`--accent-warm-deep`
   (values stay per-fork in `:root`) and the shared layout CSS fenced as
   `styles-core`/`styles-app`/`styles-footer`/`styles-hover-responsive`.
   Still deliberately fork CSS: the `:root` palette values, `.sibling-result*`
   (rides with the geocoder, item 1), Chicago's School Location styles, and the
   fork-specific marker *art* (NYC's borough-seal, Chicago's water-taxi /
   county-seal, and each fork's palette-colored selection-marker divIcon — which
   carry no shared CSS rule, just a divIcon className). The shared marker /
   region-highlight *chrome* that used to sit unfenced beside them was
   neutralized and fenced — **item 10.**
7. ~~`sw.js`~~ — **resolved July 2026**: comments neutralized, handler logic
   fenced (`sw-header`/`sw-handlers`, METRO config between them),
   `validate_index.py` lints the fences, and `engine-parity.yml` compares
   `sw.js` alongside `index.html` in every fork.
8. ~~`validate_index.py` / `smoke_test.mjs`~~ — **resolved July 2026**, both
   directions: Chicago adopted NYC's `check_sw_lists()` and `cardText()`;
   NYC adopted Chicago's `check_metro_explorers()` (with
   `_split_object_literals`). The rest of both files is legitimately
   fork-specific config (layer rosters, ground-truth points, data floors) —
   port *checks*, not bytes, when reconciling them.
9. ~~Duplicated playbook copies~~ — **resolved July 2026**: the master
   `METRO_EXPANSION_PLAYBOOK.md` lives in the Chicago repo under `docs/`
   (sibling forks carry a pointer stub at `docs/METRO_EXPANSION_PLAYBOOK.md`
   — all doc stubs live under `docs/`), and the raw NYC research notes are
   archived at `docs/archive/METRO_EXPANSION_NYC.md` in the Chicago repo.
   The authoritative stubbed-vs-not-carried list is
   `METRO_EXPANSION_PLAYBOOK.md` §3.1 item 11.
10. ~~Marker / region-highlight class namespace~~ — **resolved July 2026**
   (the last leftover of items 5–6): the three shared map-chrome classes were
   fork-prefixed (`chi-`/`nyc-`/`sf-region-highlight`, `-poi-pin`, `-panning`)
   with their CSS sitting unfenced beside fork content, the class strings
   worksheet-driven (`highlight_class`/`poi_pin_class`), and NYC missing the
   pan-pause optimization entirely. Neutralized to `region-highlight` /
   `poi-pin` / `map-panning` and fenced three ways: the CSS trio as
   `styles-markers`, the JS constants (`HIGHLIGHT_CLASS` / `POI_PIN_CLASS` /
   `PANNING_CLASS`) as `map-chrome-classes` (promoted out of the worksheet +
   generator + schema into byte-identical engine constants — the "they carry
   the fork's palette" comment was false; the rules are identical dark
   drop-shadows), and the movestart/moveend toggle as `map-pan-filter`.
   Reconciling merged features rather than overwriting: **NYC gained the
   pan-pause drop-shadow optimization** (CSS rule + toggle JS) it had never
   adopted. Result: **48/48 ENGINE blocks byte-identical across CHI/NYC/SF**
   (strict parity, 0 drift). Each fork's `smoke_test.mjs` highlight selector
   moved to `.region-highlight`. The only still-fork-named map classes are the
   genuine marker *art* divIcons (item 6).
11. **Card-system redesign rollout (engine-v1.0.10, July 2026)** — the first
   release to ship NEW blocks through the pipeline (`card-helpers`,
   `styles-card-v2`, + 7 changed blocks; contract in
   `docs/CARD_RENDER_API.md`). Both siblings are bumped and deployed:
   **50/50 ENGINE blocks byte-identical across CHI/NYC/SF**, verified
   against the deployed sites post-rollout. The rollout surfaced three
   fork-adoption requirements, recorded in
   `docs/engine-changelog/v1.0.10.md`: seed new-block fence pairs before
   the bump (NYC #66 / SF #30), adopt the pill-aware smoke card reader
   where smoke asserts factory-card text (SF #31), and migrate role-label
   roster assertions to person-row presence (SF #32). **Residual cleared
   (July 2026):** NYC (#68) and SF (#34) migrated their fork-local cards
   onto the helper vocabulary the same week (CHI PRs #172/#173 were the
   reference), taking the fleet-wide `renderFieldList` grep to zero call
   sites. The retirement release shipped as `engine-v1.0.13` (item 13).
12. **Design-review polish + Handoff 3 (engine-v1.0.11 + v1.0.12, July
   2026)** — two follow-on releases from a design review of the redesign's
   first pass, both **changed-blocks-only** (no new fences, so no sibling
   seeding). `v1.0.11` (changed `styles-card-v2`, `card-helpers`,
   `polygon-factory`): restored the layer-colored card accent/shadow tie,
   made `<details>` expanders default closed fleet-wide (the desktop-width
   auto-open + its `cardDesktopWidth` helper removed), and added the
   `pill`/`dotColor` opts. `v1.0.12` (changed `styles-card-v2`,
   `card-helpers`, `school-zone-factory`): Handoff 3's engine surface —
   card shadow + id pill tinted with the layer color (5a),
   `cardTitleCase`/`cardGradeRange` + `renderNearestRows` `tag`/`accentColor`
   (6a/8a), and the `school-zone-factory` `titleCaseData` opt + grade-range
   identifier pill (6a). Both fanned out and merged clean (NYC #69/#70, SF
   #35/#36); the engine block count is unchanged at **50/50 byte-identical**.
   Fork adoption this round was **card-side, not seeding**: each sibling took
   a fork pass on the `v1.0.12` bump (NYC #71, SF #37) adding universal id
   pills, a compact neighborhood card, and the 8a/8b School Location chips
   rebuild — plus the now-standard pill-aware/compact-aware smoke reader
   adjustments where those cards are asserted (NYC judicial-district; SF
   `cardText` gained compact value/meta reading for the now-compact
   neighborhood). Recorded in `docs/engine-changelog/v1.0.11.md` and
   `v1.0.12.md`.
13. **`renderFieldList` retirement (engine-v1.0.13, July 2026)** — the last
   step of the redesign, once the fleet-wide grep hit zero call sites (item
   11). Changed blocks only (`render-helper`, `styles-app`,
   `polygon-factory`, `polygonCountyEntry`, `school-zone-factory`,
   `exports`); **no new fences, no fence-set change, no sibling seeding or
   pre-clean.** `renderFieldList`, its `.result-row`/`.result-fields` CSS,
   the factories' legacy caller-HTML branches, and the debug-namespace
   export are all gone. **Tombstone, not deletion:** the `render-helper`
   fence is kept as an ~8-line comment rather than removed, because
   `build_engine_artifact.py` rejects an empty fence pair and `apply_engine.py`
   fails a fork carrying a fence the manifest lacks — so a true deletion
   would force a pre-clean PR in every sibling (the mirror of v1.0.10's
   seeding) plus a transient window where the fork's export references an
   undefined function. Tombstoning keeps the block set stable so the release
   fans out atomically like any changed-blocks cut. **This is the fleet's
   convention for retiring a shared engine helper:** empty its fence to a
   tombstone comment, never delete the fence. Recorded in
   `docs/engine-changelog/v1.0.13.md`. Fanned out to NYC/SF and merged clean;
   block count unchanged at **52 (50 index.html + 2 sw.js)**.
14. **This file itself had drifted — 164 lines (2026-08-18).** The doc that
   opens "the SAME copy ships in every fork; never edit it in one fork only"
   was 463 lines in CHI and 299 in both siblings, which were byte-identical to
   each other: they had simply stopped receiving updates after item 9, so
   items 10–13 were missing and items 5–6 still said the marker/region-highlight
   class-namespace drift "remains open" — a statement item 10 had made false in
   the code months earlier. **Nothing was lost by adopting CHI's copy**, checked
   line by line rather than assumed: the only sibling-exclusive lines were that
   stale wording. Two things were wrong in CHI's copy too, and were fixed in the
   same pass rather than propagated: the block inventory said **50 index.html
   blocks when the fences held 53** (`coverage-gaps`, `gaps-html`,
   `gaps-modal-html` — the Data gaps panel, shipped by engine-v1.0.19 and never
   added to the list), and the `gaps-html` placement note was written from
   Chicago's point of view before the ports landed. The inventory is now
   **generated from the real fences**, not hand-maintained — regenerate it
   rather than editing it by hand, which is how it went stale.
   **The lesson was that nothing enforced this file** — `check_engine_parity.py`
   compares fenced *code*, so the document describing the fence system drifted
   silently and was discovered only when somebody read two copies side by side.
   **That gap is now closed** (2026-08-18): the weekly `fleet-status.yml` run in
   the CHI repo carries two checks, reported as **SYNC WARN** on the standing
   fleet-status issue.
   - **Cross-fork identity** — every fork's copy of this file is fetched and
     compared against CHI's. Drift is reported in BOTH directions, deliberately:
     a fork behind CHI reads "CHI's copy supersedes it", but a fork holding
     lines CHI lacks reads "**reconcile both ways** — the fork may hold content
     CHI needs", because this file's own rule is that reconciling means merging,
     not overwriting. A raw line count cannot tell those two cases apart, and
     "just copy CHI's over" is the wrong instinct to automate.
   - **Inventory vs the live fences** — the block list above is compared against
     the fences actually present in CHI's `index.html` and `sw.js`, using the
     parity checker's own parser rather than a second copy of it. This is what
     catches a release that adds blocks and never updates the list, which is how
     the count sat at 50 while the fences held 53.
   The checks are CHI-only, like the guidebook ones: identity guarantees every
   fork carries the same file, and the release pipeline guarantees every fork
   carries the same fences, so re-reading each sibling's fences would add
   network for no new signal — and would fire a spurious WARN during a bump
   window where a fork is legitimately one release behind (already its own
   WARN). **The standing rule survives the automation:** a change here is done
   only when it has landed in all three repos. The gate now says so out loud
   instead of waiting for someone to notice.
