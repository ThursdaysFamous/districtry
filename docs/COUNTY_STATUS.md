# Illinois county completion status

<!-- ==== GENERATED FILE — DO NOT HAND-EDIT ==== -->
<!-- Emitted by scripts/build_county_status.py from the coverage-ring
     lists (scripts/build_metro_outline.py), index.html's dispatch
     tables, data/app/coverage-gaps.json and
     data/app/il-county-commissioners.json. Regenerate:
         python3 scripts/build_county_status.py
     CI drift gate (smoke-test.yml):
         python3 scripts/build_county_status.py --check -->

**91 of 102 Illinois counties are served** — 91 through their own dispatch entries, 0 through a shipped judicial circuit, and 0 through the County card alone. 11 more are researched-but-unserved (every one carries a recorded gap saying why), leaving 0 unresearched.

## How to read this

- **Served through** — `dispatch`: the county has its own entries in index.html's county dispatch tables; `judicial circuit`: a secondary county of a shipped judicial circuit (its only county-specific card is the subcircuit); `County card`: an at-large county with no district geometry, its board riding the County card (`docs/EXPANSION_GUIDE.md` §3.5.1).
- **Board** — how the county board surfaces: `districted` (own `county-board` dispatch entry), `at-large — County card` (data/app/il-county-commissioners.json), or `no board layer` for a served county whose board does not surface at all. That last one comes in two kinds, and the difference is the point: `see gaps` means a record says why, **`no gap record`** means nothing does — an unexplained absence, and a debt against this project's own rule that every absence is recorded.
- **County-keyed dispatch entries** — read from index.html itself, the same scan `validate_index.py` check 8 gates on.
- **Open gaps** — records from the guidebook's gaps block (`data/app/coverage-gaps.json`, the app's Data gaps panel). A record naming several counties appears in each of their rows.
- **"Complete"** here means: served, and `none` in the gaps column. A served county with open gaps is honest-but-unfinished; what each gap needs is the record's `wanted` line in the guidebook. One exception worth naming: a row reading **`no gap record`** in the Board column is NOT complete even though its gaps column says `none` — nobody has measured what it is missing, which is a weaker claim than having nothing missing.

## Served counties (91)

| County | FIPS | Served through | Board | County-keyed dispatch entries | Open gaps |
|---|---|---|---|---|---|
| Adams | 17001 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district` | 2 — `adams-county-board-roster` (no-source); `quincy-ward-officeholders` (no-source) |
| Alexander | 17003 | dispatch | at-large — County card | `library-district` | none |
| Bond | 17005 | dispatch | no board layer — see gaps | `library-district` | 1 — `bond-county-board-districts` (no-source) |
| Boone | 17007 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 3 — `boone-fire-belvidere-city` (data-quality); `boone-fire-names` (data-quality); `county-board-office-addresses` (no-source) |
| Brown | 17009 | dispatch | at-large — County card | `library-district` | 1 — `brown-precinct-geometry` (no-source) |
| Calhoun | 17013 | dispatch | at-large — County card | `county-precinct`, `library-district` | none |
| Carroll | 17015 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 3 — `carroll-special-districts` (no-source); `carroll-ward-geometry` (no-source); `county-board-office-addresses` (no-source) |
| Cass | 17017 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 1 — `pass9-ward-seats-without-maps` (no-source) |
| Clark | 17023 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 2 — `clark-board-contact` (data-quality); `clark-precinct-polling` (data-quality) |
| Clay | 17025 | dispatch | districted | `county-board`, `library-district` | none |
| Clinton | 17027 | dispatch | districted | `county-board`, `library-district` | 2 — `clinton-precinct-geometry` (no-source); `county-board-office-addresses` (no-source) |
| Coles | 17029 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | none |
| Cook | 17031 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `judicial-subcircuit`, `library-district`, `park-district` | none |
| Crawford | 17033 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 1 — `county-board-office-addresses` (no-source) |
| Cumberland | 17035 | dispatch | no board layer — see gaps | `county-precinct`, `library-district` | 1 — `cumberland-county-board` (no-source) |
| De Witt | 17039 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 1 — `dewitt-township-officials` (data-quality) |
| DeKalb | 17037 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 2 — `blocked-crawlers` (blocked); `county-board-office-addresses` (no-source) |
| Douglas | 17041 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | none |
| DuPage | 17043 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `judicial-subcircuit`, `library-district`, `park-district` | 3 — `aurora-council-contact` (blocked); `dupage-municipal-phones` (data-quality); `dupage-ward-cities` (no-source) |
| Edgar | 17045 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | none |
| Edwards | 17047 | dispatch | at-large — County card | `library-district` | 1 — `edwards-county-precincts` (no-source) |
| Effingham | 17049 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 1 — `effingham-municipal-officials` (no-source) |
| Franklin | 17055 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 1 — `county-board-office-addresses` (no-source) |
| Fulton | 17057 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 1 — `county-board-office-addresses` (no-source) |
| Gallatin | 17059 | dispatch | at-large — County card | `county-precinct`, `library-district` | 1 — `gallatin-board-contact` (data-quality) |
| Greene | 17061 | dispatch | at-large — County card | `county-precinct`, `library-district` | none |
| Grundy | 17063 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 3 — `grundy-special-district-boards` (data-quality); `morris-ward-geometry` (no-source); `municipal-website-dead-ends` (data-quality) |
| Hamilton | 17065 | dispatch | at-large — County card | `county-precinct`, `fire-district`, `library-district` | 1 — `hamilton-municipal-officials` (no-source) |
| Hancock | 17067 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 1 — `county-board-office-addresses` (no-source) |
| Hardin | 17069 | dispatch | no board layer — see gaps | `county-precinct`, `library-district` | 1 — `hardin-county-board` (no-source) |
| Henry | 17073 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 1 — `pass9-ward-seats-without-maps` (no-source) |
| Iroquois | 17075 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district` | none |
| Jackson | 17077 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | none |
| Jefferson | 17081 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | none |
| Jersey | 17083 | dispatch | no board layer — see gaps | `library-district` | 2 — `jersey-county-board-districts` (no-source); `jodaviess-jersey-precinct-geometry` (no-source) |
| Jo Daviess | 17085 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | none |
| Johnson | 17087 | dispatch | no board layer — see gaps | `county-precinct`, `library-district` | 1 — `johnson-county-board` (no-source) |
| Kane | 17089 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `judicial-subcircuit`, `library-district`, `park-district` | 1 — `aurora-council-contact` (blocked) |
| Kankakee | 17091 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 4 — `kankakee-city-wards` (no-source); `kankakee-municipal-officials` (no-source); `kankakee-special-districts` (data-quality); `momence-ward-geometry` (no-source) |
| Kendall | 17093 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 4 — `aurora-council-contact` (blocked); `blocked-crawlers` (blocked); `county-board-office-addresses` (no-source); `plano-ward-officials` (no-source) |
| Knox | 17095 | dispatch | districted | `county-board`, `library-district` | 1 — `knox-precinct-geometry` (no-source) |
| LaSalle | 17099 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 4 — `lasalle-board-districts-stale` (no-source); `lasalle-municipal-wards` (no-source); `ogle-lasalle-special-districts` (no-source); `wenona-two-clerks-disagree` (data-quality) |
| Lake | 17097 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `judicial-subcircuit`, `library-district`, `park-district` | 2 — `lake-municipal-names` (no-source); `park-city-wards` (no-source) |
| Lee | 17103 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district` | 2 — `lee-municipal-officials` (no-source); `lee-park-library-districts` (no-source) |
| Livingston | 17105 | dispatch | districted | `county-board`, `library-district` | 2 — `livingston-precincts` (no-source); `livingston-special-districts` (no-source) |
| Logan | 17107 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 1 — `logan-fire-districts` (no-source) |
| Macon | 17115 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 2 — `macon-board-phone-area-code` (data-quality); `macon-district-name-formatting` (data-quality) |
| Macoupin | 17117 | dispatch | no board layer — see gaps | `county-precinct`, `library-district` | 3 — `macoupin-county-board-districts` (no-source); `macoupin-special-districts` (no-source); `macoupin-ward-geometry` (no-source) |
| Madison | 17119 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `judicial-subcircuit`, `library-district`, `park-district` | 1 — `madison-ward-officials` (no-source) |
| Marshall | 17123 | dispatch | districted | `county-board`, `library-district` | 3 — `county-board-office-addresses` (no-source); `marshall-precinct-geometry` (no-source); `wenona-two-clerks-disagree` (data-quality) |
| Mason | 17125 | dispatch | districted | `county-board`, `library-district` | 2 — `county-board-office-addresses` (no-source); `mason-precinct-vintage` (data-quality) |
| Massac | 17127 | dispatch | at-large — County card | `library-district` | 1 — `massac-precinct-geometry` (no-source) |
| McDonough | 17109 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | none |
| McHenry | 17111 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `judicial-subcircuit`, `library-district` | 4 — `blocked-crawlers` (blocked); `county-board-office-addresses` (no-source); `mchenry-park-district` (no-source); `mchenry-ward-cities` (blocked) |
| McLean | 17113 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 1 — `mclean-special-districts` (no-source) |
| Menard | 17129 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | none |
| Mercer | 17131 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 1 — `county-board-office-addresses` (no-source) |
| Monroe | 17133 | dispatch | at-large — County card | `county-precinct`, `fire-district`, `library-district` | none |
| Montgomery | 17135 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 1 — `county-board-office-addresses` (no-source) |
| Morgan | 17137 | dispatch | at-large — County card | `county-precinct`, `library-district` | none |
| Moultrie | 17139 | dispatch | at-large — County card | `county-precinct`, `library-district` | none |
| Ogle | 17141 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 2 — `ogle-lasalle-special-districts` (no-source); `ogle-municipal-wards` (no-source) |
| Peoria | 17143 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 2 — `pass9-ward-seats-without-maps` (no-source); `peoria-fire-park-library-contact` (data-quality) |
| Perry | 17145 | dispatch | no board layer — see gaps | `county-precinct`, `library-district` | 1 — `perry-county-website-blocked` (blocked) |
| Pike | 17149 | dispatch | at-large — County card | `library-district` | 1 — `pike-precinct-geometry` (no-source) |
| Pulaski | 17153 | dispatch | at-large — County card | `county-precinct`, `library-district` | none |
| Putnam | 17155 | dispatch | at-large — County card | `library-district` | 1 — `putnam-precinct-geometry` (no-source) |
| Randolph | 17157 | dispatch | at-large — County card | `county-precinct`, `library-district` | 3 — `coulterville-library-extent` (data-quality); `randolph-fire-park-library` (no-source); `randolph-precinct-polling` (data-quality) |
| Richland | 17159 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 1 — `county-board-office-addresses` (no-source) |
| Rock Island | 17161 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 1 — `rock-island-andalusia-township-library` (no-source) |
| Saline | 17165 | dispatch | at-large — County card | `library-district` | 1 — `saline-precinct-geometry` (no-source) |
| Sangamon | 17167 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `judicial-subcircuit`, `library-district` | 2 — `municipal-website-dead-ends` (data-quality); `sangamon-park-library-districts` (no-source) |
| Schuyler | 17169 | dispatch | at-large — County card | `county-precinct`, `library-district` | none |
| Scott | 17171 | dispatch | no board layer — see gaps | `county-precinct`, `library-district` | 1 — `scott-county-commissioners` (no-source) |
| Shelby | 17173 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 1 — `county-board-office-addresses` (no-source) |
| St. Clair | 17163 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district` | 2 — `st-clair-board-contact` (data-quality); `st-clair-park-library-districts` (no-source) |
| Stark | 17175 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | none |
| Stephenson | 17177 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district` | 2 — `stephenson-freeport-precincts` (data-quality); `stephenson-park-library-districts` (no-source) |
| Tazewell | 17179 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | none |
| Union | 17181 | dispatch | at-large — County card | `library-district` | 1 — `captcha-county-commissioner-contact` (blocked) |
| Vermilion | 17183 | dispatch | districted | `county-board`, `library-district` | 1 — `vermilion-precinct-geometry` (no-source) |
| Wabash | 17185 | dispatch | at-large — County card | `library-district` | 1 — `wabash-precinct-geometry` (no-source) |
| Warren | 17187 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 1 — `pass10-frontier-unasked` (no-source) |
| Washington | 17189 | dispatch | districted | `county-board`, `library-district` | 1 — `washington-precinct-geometry` (no-source) |
| Wayne | 17191 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 1 — `county-board-office-addresses` (no-source) |
| White | 17193 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 1 — `white-special-districts` (no-source) |
| Whiteside | 17195 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 4 — `whiteside-municipal-officials` (no-source); `whiteside-precinct-polling` (data-quality); `whiteside-special-district-boards` (no-source); `whiteside-special-districts` (blocked) |
| Will | 17197 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `judicial-subcircuit`, `library-district`, `park-district` | 3 — `aurora-council-contact` (blocked); `crete-municipal-clerk` (no-source); `joliet-municipal-contact` (blocked) |
| Williamson | 17199 | dispatch | at-large — County card | `library-district` | 1 — `captcha-county-commissioner-contact` (blocked) |
| Winnebago | 17201 | dispatch | districted | `county-board`, `county-precinct`, `judicial-subcircuit`, `library-district` | 2 — `rockford-city-precincts` (no-source); `winnebago-special-districts` (no-source) |
| Woodford | 17203 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 1 — `woodford-special-district-boards` (data-quality) |

## Researched frontier (11) — gap-recorded, not yet served

Counties outside the coverage ring that a research pass has already measured; each row's records say what blocks it and what a submission would need to contain.

| County | FIPS | Gap records |
|---|---|---|
| Bureau | 17011 | 1 — `bureau-county-board-districts` (no-source) |
| Champaign | 17019 | 1 — `champaign-piatt-ccgisc-license` (blocked) |
| Christian | 17021 | 1 — `christian-county-board-districts` (no-source) |
| Fayette | 17051 | 1 — `fayette-county-board-geometry` (no-source) |
| Ford | 17053 | 1 — `ford-county-board-vintage` (no-source) |
| Henderson | 17071 | 1 — `henderson-county-website` (no-source) |
| Jasper | 17079 | 1 — `jasper-county-board` (no-source) |
| Lawrence | 17101 | 1 — `lawrence-county-board` (no-source) |
| Marion | 17121 | 1 — `marion-county-board-districts` (no-source) |
| Piatt | 17147 | 1 — `champaign-piatt-ccgisc-license` (blocked) |
| Pope | 17151 | 1 — `pope-county-board` (no-source) |

## Unresearched (0)

.

## Gap records not tagged to a county (1)

City- or app-scoped records with no `counties` tag, listed so the table reconciles with the 101 records in the Data gaps panel: `chicago-amenity-phones`.
