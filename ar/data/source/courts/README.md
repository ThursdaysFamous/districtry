# Arkansas courts: what the two court layers are built from

These files are what `ar/scripts/build_ar_court_districts.py` reads to draw the
Court of Appeals' seven districts and the 28 judicial circuits. Both are sets of
whole counties, so the county lists are the boundary: the builder dissolves the
county fabric this instance already ships (`ar/data/app/state-counties.json`),
and no map is traced. Every file was read on 2026-10-16 with this project's own
client after reading robots.txt (arcourts.gov's permits every path read;
gis.arkansas.gov serves none), and each file's header records the address, the
size and SHA-256 of what was read, and how it was reduced.

**NO JUDGE IS NAMED IN ANY OF THEM.** The court system's pages name every judge,
with telephone numbers, and this project does not publish them yet (gaps
`ar-appeals-judges` and `ar-circuit-judges`), so the extracts keep the county
lists, the division numbers and the position numbers and nothing else.

| file | what it settles |
|---|---|
| `coa-act-1812.txt` | which counties are in each of the seven Court of Appeals districts: Act 1812 of 2003, as the state GIS office's metadata quotes it |
| `coa-layer2-reading.tsv` | the second reading: the state's Appeals Court Districts layer overlaid on the counties, which must put every county where the act does |
| `coa-positions.tsv` | how many judges each district elects: two positions in Districts 1, 2, 3, 4 and 6, one in Districts 5 and 7, twelve in all, from the court's own district map page |
| `aoc-circuit-judge-directory.tsv` | which circuit each county is in and which of the circuit's divisions (judges) serve it, from the Administrative Office of the Courts' circuit judge directory |
| `circuit-layer3-reading.tsv` | the second reading: the state's Circuit Court Districts layer overlaid on the counties, its subdistricts counted as their circuit, which must put every county in the directory's circuit |
| `circuit-court-order.txt` | the federal court order (Hunt v. State of Arkansas) that created election subdistricts in five circuits, as the circuit layer's metadata quotes it |
| `circuit-courts-page.txt` | that circuit judges run in nonpartisan elections and serve six-year terms, from the court system's circuit courts page |

**THE ACT IS QUOTED, NOT READ AT SOURCE.** Arkansas's official Code is published
by LexisNexis behind a page that carries no text without a browser's scripts
and cookies, and the two free copies this project tried answered robots.txt
with HTTP 403 and the page with a managed challenge, which this project never
works around (measured 2026-10-15). The General Assembly's own site publishes
each session's acts but not the consolidated Code. So the county lists come
from the state GIS office's quotation of the act, held to the state's own
district layer county by county, and the court's own 2023 district map
(https://arcourts.gov/sites/default/files/court-of-appeals-district-map-2023.pdf,
an image with no text layer) was compared with them by eye on 2026-10-16 and
agrees. That the law setting these districts has no free, readable copy is
recorded as a data-publishing hurdle.

**THE CIRCUITS ARE READ FROM THE DIRECTORY, AND IT IS CHECKED AGAINST ITSELF.**
The directory lists each judge under every county the judge serves, so a
circuit is one electorate of whole counties only if every one of its judges
serves every one of its counties; the builder stops if any does not. It also
pins the statewide count of 126 judges, which becomes 127 on January 1, 2027,
when the 19th West's eighth judgeship (Act 220 of 2025) takes office.

**THE SUBDISTRICTS ARE NOT DRAWN.** In the 1st, 2nd, 6th, 10th and 11th West
circuits a federal court order created two election subdistricts, which split
fifteen counties (measured on the state layer 2026-10-15). Which judgeships
each subdistrict elects is set by the court and was not read, so the circuits
are drawn whole and their cards say the subdistricts exist.

**THE GIS LAYERS ARE OLDER THAN THE COUNTIES.** Both state layers were drawn on
Census 2000 blocks and the county fabric is the Census Bureau's 2020 one, so
their edges disagree by slivers: the least of any county inside its own unit
is 98.57% (Mississippi County, where the remainder is river the old layer
leaves uncovered), and no second unit holds as much as 1% of any county.

## How to re-read

`ar/WATCH.md` asks for this once a year and after any act that moves a county
or adds a judgeship. Nothing here fetches on its own; a session does it.

1. Read each host's robots.txt first, through `scripts/robots_policy.py`
   (`scraper_common.require_robots_once`), with the client this project
   crawls as, `districtry/1.0 (+https://districtry.com/ar/)`, and at every
   redirect. On `gis.arkansas.gov` the robots.txt address answers with an
   HTML page, which is no policy and disallows nothing; read it again rather
   than assume it still does.
2. Fetch the three arcourts.gov pages and the two metadata pages named in the
   headers above, and the two layer queries exactly as their headers write
   them, at least ten seconds apart on `gis.arkansas.gov`.
3. Reduce each into the file of the same name, keeping its header's form
   (address, date, client, and the size and SHA-256 of what was read):
   - the directory: one row per county, giving the county, its circuit as the
     directory writes it, and the division numbers listed under it. The page
     has a table per county with a row per judge (judge, circuit, division);
     keep only the circuit and the division.
   - the two layer readings: overlay each county of
     `ar/data/app/state-counties.json` on the layer, measure the share of its
     area in each unit on a local projection scaled by the cosine of the
     county's own latitude, and write the largest unit, its share, and every
     other unit holding 0.2% or more. On the circuit layer, drop a
     subdistrict's `.1` or `.2` suffix first, so a circuit's two subdistricts
     count as the circuit.
   - the act and the court order: copy the quoted sentences as published, the
     act one district to a line.
   - the positions: the district map page's table of district, position and
     next election, keeping the district and the position only.
   - the circuit courts page: its sentence on nonpartisan elections and
     six-year terms.
4. Run `python3 ar/scripts/build_ar_court_districts.py` (it needs shapely),
   then `python3 ar/scripts/build_ar_court_districts.py --check`. Either
   stopping is the finding: read what it names before changing anything.

No judge's name, address or telephone number goes into any file here.
