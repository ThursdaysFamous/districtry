# Illinois county completion status

<!-- ==== GENERATED FILE — DO NOT HAND-EDIT ==== -->
<!-- Emitted by scripts/build_county_status.py from the coverage-ring
     lists (scripts/build_metro_outline.py), index.html's dispatch
     tables, data/app/coverage-gaps.json and
     data/app/il-county-commissioners.json. Regenerate:
         python3 scripts/build_county_status.py
     CI drift gate (smoke-test.yml):
         python3 scripts/build_county_status.py --check -->

**91 of 102 Illinois counties are served** — 79 through their own dispatch entries, 2 through a shipped judicial circuit, and 10 through the County card alone. 11 more are researched-but-unserved (every one carries a recorded gap saying why), leaving 0 unresearched.

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
| Alexander | 17003 | County card | at-large — County card | — | 1 — `library-districts-unmapped-counties` (no-source) |
| Bond | 17005 | judicial circuit | no board layer — see gaps | — | 2 — `bond-county-board-districts` (no-source); `library-districts-unmapped-counties` (no-source) |
| Boone | 17007 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 3 — `boone-fire-belvidere-city` (data-quality); `boone-fire-names` (data-quality); `county-board-office-addresses` (no-source) |
| Brown | 17009 | County card | at-large — County card | — | 2 — `brown-precinct-geometry` (no-source); `library-districts-unmapped-counties` (no-source) |
| Calhoun | 17013 | dispatch | at-large — County card | `county-precinct` | 1 — `library-districts-unmapped-counties` (no-source) |
| Carroll | 17015 | dispatch | districted | `county-board`, `county-precinct`, `library-district` | 3 — `carroll-special-districts` (no-source); `carroll-ward-geometry` (no-source); `county-board-office-addresses` (no-source) |
| Cass | 17017 | dispatch | districted | `county-board`, `county-precinct` | 3 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source); `pass9-ward-seats-without-maps` (no-source) |
| Clark | 17023 | dispatch | districted | `county-board`, `county-precinct` | 3 — `clark-board-contact` (data-quality); `clark-precinct-polling` (data-quality); `library-districts-unmapped-counties` (no-source) |
| Clay | 17025 | dispatch | districted | `county-board` | 2 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source) |
| Clinton | 17027 | dispatch | districted | `county-board` | 3 — `clinton-precinct-geometry` (no-source); `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source) |
| Coles | 17029 | dispatch | districted | `county-board`, `county-precinct` | 1 — `library-districts-unmapped-counties` (no-source) |
| Cook | 17031 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `judicial-subcircuit`, `library-district`, `park-district` | none |
| Crawford | 17033 | dispatch | districted | `county-board`, `county-precinct` | 2 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source) |
| Cumberland | 17035 | dispatch | no board layer — see gaps | `county-precinct` | 2 — `cumberland-county-board` (no-source); `library-districts-unmapped-counties` (no-source) |
| De Witt | 17039 | dispatch | districted | `county-board`, `county-precinct` | 3 — `county-board-office-addresses` (no-source); `dewitt-township-officials` (data-quality); `library-districts-unmapped-counties` (no-source) |
| DeKalb | 17037 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 2 — `blocked-crawlers` (blocked); `county-board-office-addresses` (no-source) |
| Douglas | 17041 | dispatch | districted | `county-board`, `county-precinct` | 2 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source) |
| DuPage | 17043 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `judicial-subcircuit`, `library-district`, `park-district` | 4 — `aurora-council-contact` (blocked); `county-board-office-addresses` (no-source); `dupage-municipal-phones` (data-quality); `dupage-ward-cities` (no-source) |
| Edgar | 17045 | dispatch | districted | `county-board`, `county-precinct` | 2 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source) |
| Edwards | 17047 | County card | at-large — County card | — | 2 — `edwards-county-precincts` (no-source); `library-districts-unmapped-counties` (no-source) |
| Effingham | 17049 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 2 — `county-board-office-addresses` (no-source); `effingham-municipal-officials` (no-source) |
| Franklin | 17055 | dispatch | districted | `county-board`, `county-precinct` | 2 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source) |
| Fulton | 17057 | dispatch | districted | `county-board`, `county-precinct` | 2 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source) |
| Gallatin | 17059 | dispatch | at-large — County card | `county-precinct` | 2 — `gallatin-board-contact` (data-quality); `library-districts-unmapped-counties` (no-source) |
| Greene | 17061 | dispatch | at-large — County card | `county-precinct` | 1 — `library-districts-unmapped-counties` (no-source) |
| Grundy | 17063 | dispatch | districted | `county-board`, `county-precinct` | 4 — `grundy-special-districts` (no-source); `library-districts-unmapped-counties` (no-source); `morris-ward-geometry` (no-source); `municipal-website-dead-ends` (data-quality) |
| Hamilton | 17065 | dispatch | at-large — County card | `county-precinct`, `fire-district` | 2 — `hamilton-municipal-officials` (no-source); `library-districts-unmapped-counties` (no-source) |
| Hancock | 17067 | dispatch | districted | `county-board`, `county-precinct` | 2 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source) |
| Hardin | 17069 | dispatch | no board layer — see gaps | `county-precinct` | 2 — `hardin-county-board` (no-source); `library-districts-unmapped-counties` (no-source) |
| Henry | 17073 | dispatch | districted | `county-board`, `county-precinct` | 3 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source); `pass9-ward-seats-without-maps` (no-source) |
| Iroquois | 17075 | dispatch | districted | `county-board`, `county-precinct`, `fire-district` | 2 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source) |
| Jackson | 17077 | dispatch | districted | `county-board`, `county-precinct` | 1 — `library-districts-unmapped-counties` (no-source) |
| Jefferson | 17081 | dispatch | districted | `county-board`, `county-precinct` | 1 — `library-districts-unmapped-counties` (no-source) |
| Jersey | 17083 | judicial circuit | no board layer — see gaps | — | 3 — `jersey-county-board-districts` (no-source); `jodaviess-jersey-precinct-geometry` (no-source); `library-districts-unmapped-counties` (no-source) |
| Jo Daviess | 17085 | dispatch | districted | `county-board`, `county-precinct` | 1 — `library-districts-unmapped-counties` (no-source) |
| Johnson | 17087 | dispatch | no board layer — see gaps | `county-precinct` | 2 — `johnson-county-board` (no-source); `library-districts-unmapped-counties` (no-source) |
| Kane | 17089 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `judicial-subcircuit`, `library-district`, `park-district` | 2 — `aurora-council-contact` (blocked); `county-board-office-addresses` (no-source) |
| Kankakee | 17091 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 5 — `county-board-office-addresses` (no-source); `kankakee-city-wards` (no-source); `kankakee-municipal-officials` (no-source); `kankakee-special-districts` (data-quality); `momence-ward-geometry` (no-source) |
| Kendall | 17093 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 4 — `aurora-council-contact` (blocked); `blocked-crawlers` (blocked); `county-board-office-addresses` (no-source); `plano-ward-officials` (no-source) |
| Knox | 17095 | dispatch | districted | `county-board` | 2 — `knox-precinct-geometry` (no-source); `library-districts-unmapped-counties` (no-source) |
| LaSalle | 17099 | dispatch | districted | `county-board`, `county-precinct` | 6 — `county-board-office-addresses` (no-source); `lasalle-board-districts-stale` (no-source); `lasalle-municipal-wards` (no-source); `library-districts-unmapped-counties` (no-source); `ogle-lasalle-special-districts` (no-source); `wenona-two-clerks-disagree` (data-quality) |
| Lake | 17097 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `judicial-subcircuit`, `library-district`, `park-district` | 2 — `lake-municipal-names` (no-source); `park-city-wards` (no-source) |
| Lee | 17103 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district` | 3 — `county-board-office-addresses` (no-source); `lee-municipal-officials` (no-source); `lee-park-library-districts` (no-source) |
| Livingston | 17105 | dispatch | districted | `county-board` | 4 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source); `livingston-precincts` (no-source); `livingston-special-districts` (no-source) |
| Logan | 17107 | dispatch | districted | `county-board`, `county-precinct` | 2 — `library-districts-unmapped-counties` (no-source); `logan-fire-districts` (no-source) |
| Macon | 17115 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 3 — `county-board-office-addresses` (no-source); `macon-board-phone-area-code` (data-quality); `macon-district-name-formatting` (data-quality) |
| Macoupin | 17117 | dispatch | no board layer — see gaps | `county-precinct`, `library-district` | 3 — `macoupin-county-board-districts` (no-source); `macoupin-special-districts` (no-source); `macoupin-ward-geometry` (no-source) |
| Madison | 17119 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `judicial-subcircuit`, `library-district`, `park-district` | 2 — `county-board-office-addresses` (no-source); `madison-ward-officials` (no-source) |
| Marshall | 17123 | dispatch | districted | `county-board` | 4 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source); `marshall-precinct-geometry` (no-source); `wenona-two-clerks-disagree` (data-quality) |
| Mason | 17125 | dispatch | districted | `county-board` | 3 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source); `mason-precinct-vintage` (data-quality) |
| Massac | 17127 | County card | at-large — County card | — | 2 — `library-districts-unmapped-counties` (no-source); `massac-precinct-geometry` (no-source) |
| McDonough | 17109 | dispatch | districted | `county-board`, `county-precinct` | 2 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source) |
| McHenry | 17111 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `judicial-subcircuit`, `library-district` | 4 — `blocked-crawlers` (blocked); `county-board-office-addresses` (no-source); `mchenry-park-district` (no-source); `mchenry-ward-cities` (blocked) |
| McLean | 17113 | dispatch | districted | `county-board`, `county-precinct` | 3 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source); `mclean-special-districts` (no-source) |
| Menard | 17129 | dispatch | districted | `county-board`, `county-precinct` | 2 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source) |
| Mercer | 17131 | dispatch | districted | `county-board`, `county-precinct` | 2 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source) |
| Monroe | 17133 | dispatch | at-large — County card | `county-precinct`, `fire-district` | 1 — `library-districts-unmapped-counties` (no-source) |
| Montgomery | 17135 | dispatch | districted | `county-board`, `county-precinct` | 2 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source) |
| Morgan | 17137 | dispatch | at-large — County card | `county-precinct` | 1 — `library-districts-unmapped-counties` (no-source) |
| Moultrie | 17139 | dispatch | at-large — County card | `county-precinct` | 1 — `library-districts-unmapped-counties` (no-source) |
| Ogle | 17141 | dispatch | districted | `county-board`, `county-precinct` | 4 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source); `ogle-lasalle-special-districts` (no-source); `ogle-municipal-wards` (no-source) |
| Peoria | 17143 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 3 — `county-board-office-addresses` (no-source); `pass9-ward-seats-without-maps` (no-source); `peoria-fire-park-library-contact` (data-quality) |
| Perry | 17145 | dispatch | no board layer — see gaps | `county-precinct` | 2 — `library-districts-unmapped-counties` (no-source); `perry-county-website-blocked` (blocked) |
| Pike | 17149 | County card | at-large — County card | — | 2 — `library-districts-unmapped-counties` (no-source); `pike-precinct-geometry` (no-source) |
| Pulaski | 17153 | dispatch | at-large — County card | `county-precinct` | 1 — `library-districts-unmapped-counties` (no-source) |
| Putnam | 17155 | County card | at-large — County card | — | 2 — `library-districts-unmapped-counties` (no-source); `putnam-precinct-geometry` (no-source) |
| Randolph | 17157 | dispatch | at-large — County card | `county-precinct`, `library-district` | 2 — `randolph-fire-park-library` (no-source); `randolph-precinct-polling` (data-quality) |
| Richland | 17159 | dispatch | districted | `county-board`, `county-precinct` | 2 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source) |
| Rock Island | 17161 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 2 — `county-board-office-addresses` (no-source); `rock-island-andalusia-township-library` (no-source) |
| Saline | 17165 | County card | at-large — County card | — | 2 — `library-districts-unmapped-counties` (no-source); `saline-precinct-geometry` (no-source) |
| Sangamon | 17167 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `judicial-subcircuit`, `library-district` | 3 — `county-board-office-addresses` (no-source); `municipal-website-dead-ends` (data-quality); `sangamon-park-library-districts` (no-source) |
| Schuyler | 17169 | dispatch | at-large — County card | `county-precinct` | 1 — `library-districts-unmapped-counties` (no-source) |
| Scott | 17171 | dispatch | no board layer — see gaps | `county-precinct` | 2 — `library-districts-unmapped-counties` (no-source); `scott-county-commissioners` (no-source) |
| Shelby | 17173 | dispatch | districted | `county-board`, `county-precinct` | 2 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source) |
| St. Clair | 17163 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district` | 3 — `county-board-office-addresses` (no-source); `st-clair-board-contact` (data-quality); `st-clair-park-library-districts` (no-source) |
| Stark | 17175 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 1 — `county-board-office-addresses` (no-source) |
| Stephenson | 17177 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district` | 3 — `county-board-office-addresses` (no-source); `stephenson-freeport-precincts` (data-quality); `stephenson-park-library-districts` (no-source) |
| Tazewell | 17179 | dispatch | districted | `county-board`, `county-precinct` | 2 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source) |
| Union | 17181 | County card | at-large — County card | — | 2 — `captcha-county-commissioner-contact` (blocked); `library-districts-unmapped-counties` (no-source) |
| Vermilion | 17183 | dispatch | districted | `county-board` | 2 — `library-districts-unmapped-counties` (no-source); `vermilion-precinct-geometry` (no-source) |
| Wabash | 17185 | County card | at-large — County card | — | 2 — `library-districts-unmapped-counties` (no-source); `wabash-precinct-geometry` (no-source) |
| Warren | 17187 | dispatch | districted | `county-board`, `county-precinct` | 3 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source); `pass10-frontier-unasked` (no-source) |
| Washington | 17189 | dispatch | districted | `county-board` | 3 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source); `washington-precinct-geometry` (no-source) |
| Wayne | 17191 | dispatch | districted | `county-board`, `county-precinct` | 2 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source) |
| White | 17193 | dispatch | districted | `county-board`, `county-precinct` | 2 — `library-districts-unmapped-counties` (no-source); `white-special-districts` (no-source) |
| Whiteside | 17195 | dispatch | districted | `county-board`, `county-precinct` | 6 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source); `whiteside-municipal-officials` (no-source); `whiteside-precinct-polling` (data-quality); `whiteside-special-district-boards` (no-source); `whiteside-special-districts` (blocked) |
| Will | 17197 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `judicial-subcircuit`, `library-district`, `park-district` | 4 — `aurora-council-contact` (blocked); `county-board-office-addresses` (no-source); `crete-municipal-clerk` (no-source); `joliet-municipal-contact` (blocked) |
| Williamson | 17199 | County card | at-large — County card | — | 2 — `captcha-county-commissioner-contact` (blocked); `library-districts-unmapped-counties` (no-source) |
| Winnebago | 17201 | dispatch | districted | `county-board`, `county-precinct`, `judicial-subcircuit` | 4 — `county-board-office-addresses` (no-source); `library-districts-unmapped-counties` (no-source); `rockford-city-precincts` (no-source); `winnebago-special-districts` (no-source) |
| Woodford | 17203 | dispatch | districted | `county-board`, `county-precinct`, `fire-district`, `library-district`, `park-district` | 2 — `county-board-office-addresses` (no-source); `woodford-special-district-boards` (data-quality) |

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
