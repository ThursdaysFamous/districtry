# Tennessee judicial districts: what the court layer is built from

These files are what `tn/scripts/build_tn_judicial_districts.py` reads to draw
Tennessee's 32 judicial districts. Every district is a set of whole counties,
so a county list is the boundary: the builder dissolves the county fabric this
instance already ships (`tn/data/app/state-counties.json`), and no map is read
for the lines. All three were read on 2026-10-16 with this project's own
client, after reading robots.txt at every redirect hop.

| file | what it settles |
|---|---|
| `tndagc-county-selector.tsv` | which district each of the 95 counties is in, from the District Attorneys General Conference's "Find your District Attorney" selector. It is the only source read that names every county, so it is the one the build reads. |
| `tndagc-district-pages.tsv` | the sentence on each district's own page that names its counties. 31 of the 32 were read, and each must name exactly the counties the selector sends there. |
| `orea-fy2019-judicial-districts.txt` | the legend of the Comptroller's FY2019 judicial map (PDF of 2026-10-16: SHA-256 `b98adc07f9b2ce1cc2e387ba15b74f1551ff9c4384b7c104f2115f8b34a4a06b`). It must agree with the selector everywhere except the 21st, which was later split into the 21st and 32nd. |

**WHY NOT THE STATUTE.** The districts are set in the Tennessee Code, and the
state does not publish a copy this project can read:

- the public copy of the Code is published by LexisNexis, not by the state;
- the General Assembly's own site, capitol.tn.gov, admits eight named search
  and archive crawlers in its robots.txt and refuses every other client,
  this project's included;
- the courts' site, tncourts.gov, answers every request, robots.txt included,
  with a managed challenge, which is an access control and is never worked
  around.

Measured on 2026-10-15 and 2026-10-16, and recorded as a data-publishing
hurdle: which counties make up each of Tennessee's court districts is law, and
reading it took a prosecutors' association's website and a Comptroller map
drawn for fiscal year 2019.

**ONE PAGE WAS NOT READ.** District 2's page leads to the district attorney's
own site, sullivancountyda.com, whose robots.txt answered HTTP 521 on
2026-10-16. RFC 9309 reads an unreachable robots.txt as disallow-all, so
nothing was read there; the builder declares that one absence, and District 2
rests on the selector and the Comptroller's map alone.

**THE DISTRICT PAGES ALSO NAME EACH DISTRICT ATTORNEY GENERAL** (the 21st's
reads "Stacey B. Edmonson, 21st District Attorney General"). The court layer
does not carry them yet; that is gap `tn-judicial-district-officers`.
