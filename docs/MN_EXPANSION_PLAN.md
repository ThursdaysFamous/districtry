# districtry Minnesota — the record of the launch

> **SHIPPED 2026-09-30 — three PRs over two days: #1265 (instance + four pre-built layers, dark),
> #1274 (the rest of the national tier, still dark), and the go-live change.** Live at
> districtry.com/mn/ with thirteen layers.
>
> **THIS FILE WAS WRITTEN AT GO-LIVE, NOT BEFORE THE BUILD, and that is stated rather than
> disguised.** `docs/IA_EXPANSION_PLAN.md` and `docs/MI_EXPANSION_PLAN.md` are genuine planning
> documents — researched, committed, and then appended to as each phase shipped. Minnesota's
> planning lived in a session artifact instead, so a file here claiming to be "the plan" would be
> a reconstruction wearing a plan's clothes, and this project's own standard is that a record says
> which of its claims were measured and when. So this is the RECORD: what the three changes did,
> what was measured on the way, and what is still owed. The shipped instance —
> `mn/metro-worksheet.json`, `mn/CLAUDE.md`, `mn/WATCH.md`, the guidebook's Minnesota column —
> remains the record of what IS.

## What ships

Thirteen layers, the whole national tier: everything a U.S. state can serve from national
publishers with no state-specific source between them.

| Layer | Count | Ships as | Who it names |
|---|---|---|---|
| County | 87 | pre-built | nobody (gap `mn-county-officers`) |
| U.S. House | 8 | pre-built | the representative, refreshed weekly |
| Minnesota Senate | 67 | pre-built | nobody (gap `mn-legislature-roster`) |
| Minnesota House | 134 | pre-built | nobody (same gap) |
| School District (Unified) | 322 | live | nobody (gap `mn-school-board-members`) |
| School District (Elementary) | 8 | live | nobody (same gap) |
| School District (Secondary) | 1 | live | nobody (same gap) |
| ZIP Code | 1,385 in envelope | live | — |
| Township or City | 2,762 | live | nobody (gap `mn-township-officers`) |
| City | 856 | live | nobody (gap `mn-municipal-officeholders`) |
| Police Station | 694 | live | — (a station is a facility) |
| Fire & EMS Station | 1,484 | live | — |
| Post Office | 1,199 | live | — |

Counts measured 2026-09-29. One roster ships, so one weekly workflow exists.

## Three things about Minnesota that a port would have got wrong

Each was found by measuring rather than by copying a sibling, and each is recorded in
`mn/CLAUDE.md` at length.

**Minnesota is the Iowa shape, not Michigan's.** There is no village among the 856 incorporated
places — every one carries the Census's city descriptor — and a Minnesota city is not inside a
township. So neither the city card nor the township card names the other, the way Michigan's
village card must.

**The Census files eight school districts as elementary-only and then records seven of them as
running PK through 12.** Every sibling's elementary card says the district "runs no high school
of its own". That sentence is false here, so these cards do not print it: they give the grade
range TIGER gives, say which tiling the district sits in, and claim nothing about which grades
it operates. Exclusivity against the unified tiling is clean in both directions, so the tiling
is trustworthy; what the Census MEANS by placing a PK-12 district in the elementary tiling is
not established and is not guessed at — gap `mn-elementary-district-grades`.

**The secondary tiling has exactly one feature and ships anyway.** Park Rapids for grades 9-12
over the Pine Point district, 13.3 km². Iowa and Michigan both measure a zero there and
correctly ship nothing. One feature is not zero, and a reader standing inside it would otherwise
be told no such district exists.

## What the go-live change cost, and the one thing it nearly published without

**`sources.html` did not exist when this instance was ready to publish.** PR 1 recorded the
reason in `mn/index.html` itself and the reason was correct while the instance was dark: a
masthead link to a file the tree does not contain is a 404 the moment the page is published,
which `validate_instance_assets.py` says out loud. What that reasoning does not answer is what a
PUBLISHED instance owes a reader. `sources.html` is where this project answers *where did THIS
answer come from*; every sibling carries it; Minnesota would have been the only live instance
with no way to ask. So the go-live change shipped the page.

It cost no research. Every one of the thirteen `layers[]` entries already carried a full `source`
block — `generate_metro_files.py` refuses a `sources_page` instance where one does not — so the
layer matrix and the credit rows generated from what was already in the worksheet. The shell was
cloned from `in/sources.html` and localized; the Indiana sweep is 0 hits.

**No gate asks this question and none is proposed.** The asset gate proves every link resolves,
and a page nobody links resolves trivially; `validate_instance_registration.py` asks whether an
instance is registered, not whether it is furnished. **A correct reason for an omission while
dark is not a reason for it once live** — that is a review responsibility, and it is now in the
root `CLAUDE.md` where the next go-live will read it.

**The fleet hand-off bbox had to be clipped, which is the Michigan case from the other side.**
Minnesota's easternmost land is -89.4834, Cook County's Grand Portage tip, and Wisconsin's own
centre sits at -89.565 — so any box reaching Minnesota's true eastern point contains that centre
and fails `wi`'s own `validate_index.py`. The shipped box clips to -89.58, the nearest hundredth
strictly west of it. The cost is the eastern 6.2% of one county's width and no sibling box covers
that strip either, but since 2026-09-27 `fleet-outlines.json` settles every selection and
Minnesota's own outline covers Grand Portage, so the clip decides nothing a reader can see unless
that file cannot be read. The rectangle cannot be made to fit: at Wisconsin's centre latitude
Minnesota's eastern boundary is the St. Croix, about -92.8, so the conflict is the rectangle's
corner reaching over central Wisconsin where Minnesota is nowhere near. The whole measurement is
in `metros.json`'s own `$comment`.

**Two siblings' negative points sit inside Minnesota and both were settled before publishing.**
Iowa's (43.65, -93.37) and Wisconsin's (47.39, -92.97), in #1267 and #1268 — by having those
instances' checks REFUSE `fleet-outlines.json` rather than by moving a point that had been
measured correctly. That is the better remedy: the point stays where it was measured and the
check stops reading a file that will legitimately change every time a state ships. The fleet was
then swept for every other coordinate Minnesota's outline would claim — 48 pairs across every
`scripts/*.mjs`, `*/scripts/*.mjs`, `*/metro-worksheet.json` and `metros.json` — and those two
were the only ones.

## The recon that scored Minnesota RED, and what was actually there

`docs/MI_EXPANSION_PLAN.md`'s five-state recon of 2026-09-03 scored Minnesota **RED** on one
sentence: *"The Secretary of State states outright it has no commissioner-district maps online;
MnGeo's statewide catalog carries none either; the shapefile page is bot-gated."*

**Two of those three clauses are right and the conclusion is wrong.** MnGeo's `www` host does
serve a Radware Bot Manager captcha to this project's token — obeyed, never worked around — and
it costs nothing, because the data is on a different host. `enterprise.gisdata.mn.gov` serves
`us_mn_state_sos/bdry_votingdistricts/FeatureServer/0`: 4,105 precincts whose own attributes
carry **`ctycomdist` — all 447 county commissioner districts in all 87 counties** — plus six
more dissolvable layers (precincts, 10 judicial districts, 117 soil & water, 16 hospital, 3 park,
274 wards in 76 cities). robots.txt allows this client with `Crawl-delay: 60` binding on `*`,
honoured, which makes a full page-through slow rather than impossible.

**This is the Knox shape**: a blocked HOST read as a state that publishes nothing. It is recorded
here because the RED verdict is in a committed file that the next recon will read, and a
measurement filed in one document and contradicted in another is how they come to disagree.

## What is still owed

`mn/WATCH.md` is the live list; this is the shape of it.

**The flagship layer, and the one open research question.** County commissioner districts are
the instance's growth path and the geometry is in hand. The ROSTER route is **unproven rather
than closed**, and the difference is one measurement: the Secretary of State's companion results
service carries federal and state contests only, so composing a roster from certified returns is
shut there, but its `LocalRacesInCounty` pages were read for ONE county at ONE election id with
no commissioner contest found — which is one reading and not a finding. If those pages carry
commissioner contests, all 447 seats come from one publisher. If they do not, this is the
Michigan shape: 87 counties in tranches off their own board pages. **That answer decides whether
the flagship ships with names or without, which is why go-live did not wait for it.**

**Four more rosters nobody publishes in one place** — the two chambers (ours to build), the
county officers, 331 school boards, 1,797 townships each electing five people (the largest
per-unit roster task recorded in this fleet) and 856 cities. All recorded as gaps, none an ask.

**Two sub-pages and one latent test dependency**, all in `mn/WATCH.md`'s "Still owed after
go-live" section: `faq.html`, `history.html`, and this instance's own smoke test still reading
`fleet-outlines.json`, which breaks silently the day a Dakotas instance ships.

**Tribal government** is the fleet-wide thread's, not this instance's — including Minnesota's
gap record, so nothing here opens a second record for the same absence. That thread settled the
one boundary question raised here: the Lake Traverse reservation's intersection with Minnesota
is a zero-area line, because the reservation's eastern edge IS the state line. The 0.139 km²
measured here first was a simplified state outline against a full-precision reservation — an
artefact of two detail levels, not ground.
