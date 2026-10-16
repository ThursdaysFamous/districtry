# Mississippi court district pages and redistricting laws, as published

These are the pages `ms/scripts/build_ms_court_districts.py` reads to draw the
four court maps. Every Mississippi court whose judges are elected from
districts has its districts written as lists of whole counties (the Court of
Appeals also splits ten counties by named precincts), so these lists are the
boundary source and nothing else is read. Each file is the page exactly as it
was served on 2026-10-15 to this project's client
(`districtry/1.0 (+https://districtry.com/ms/)`); the builder's `SOURCES` table
records the address each came from and its SHA-256, and `--check` recomputes
every hash, so a copy edited by hand fails rather than parsing into a
different map.

The files are saved as `.htm` and not `.html` on purpose: the site's page gates
treat every `.html` file in an instance folder as a page a reader is served.

| file | from | what it settles |
|---|---|---|
| `sc-districts.htm` | the Supreme Court's district page | the 3 Supreme Court districts, county by county |
| `coa-districts.htm` | the Court of Appeals' district page | the 5 Court of Appeals districts, and the precincts by which they split Attala, Grenada, Hinds, Jones, Leake, Madison, Montgomery, Panola, Tallahatchie and Wayne Counties |
| `chancery-districts.htm` | the chancery courts' page | the 20 chancery districts in force now |
| `circuit-districts.htm` | the circuit courts' page | the 23 circuit districts in force now |
| `SB2768SG.htm` | Senate Bill 2768 (2025), as sent to the Governor | the chancery districts until and from 1 January 2027 (and George County's move on 1 January 2031) |
| `HB1544SG.htm` | House Bill 1544 (2025), as sent to the Governor | the circuit districts until and from 1 January 2027, and until and from 1 January 2031 |
| `HB0580SG.htm` | House Bill 580 (2026), as sent to the Governor | the Fourth and Seventh Circuit Districts again, with the same counties and new subdistricts |
| `HB0001SG.htm` | House Bill 1 (2026), as sent to the Governor | the Third Chancery District's 2027 section again, with the same counties, and three chancellors from 2027 where Senate Bill 2768 had given it two |

How a bill marks its changes matters to the parse: struck words are in `<s>`
tags and are dropped, inserted words are kept, and each amended section is
written once per date range under a heading such as "[From and after January
1, 2027, this section shall read as follows:]".

**WHICH LAWS ARE HERE, AND HOW THAT WAS DECIDED.** The Senate Legislative
Services Office's summary of the 2025 judicial redistricting laws (dated 5
August 2025, `https://www.legislature.ms.gov/media/1364/2025-judicial-redistricting-summary.pdf`)
names Senate Bill 2768 and House Bill 1544 and no other, and every county move
it describes matches the parse, compared by hand on 2026-10-15. The two 2026
laws were found by reading the short title of every measure the Legislature's
bill status system lists for the 2025 Regular Session, the 2025 First
Extraordinary Session, the 2026 Regular Session and the 2026 First
Extraordinary Session (`/<session>/pdf/all_measures/allmsrs.xml`, 15 October
2026). Of the enacted measures whose short titles name a court, a judge or a
judicial district, five concern a district, and those five were read in full:
these four, which write a chancery or circuit district's counties, and House
Bill 49 of the 2025 First Extraordinary Session, which changes only the number
of assistant district attorneys. A Supreme
Court districts bill (Senate Bill 2138, 2026) died in conference, so the
Supreme Court's districts are still the ones its page lists.

**THE HOSTS.** `courts.ms.gov` publishes a robots.txt (871 bytes on 2026-10-15)
that permits all four pages read; the host dropped connections now and then,
so requests were spaced three seconds apart and retried. `billstatus.ls.state.ms.us`
publishes no robots.txt (HTTP 404, which RFC 9309 §2.3.1.3 reads as allow-all)
and serves only its own certificate without the intermediate that issued it,
so the fetch completed the chain from the GlobalSign intermediate pinned in
`scripts/aia_bundle.py` (`globalsign-rsa-ov-2018`) rather than turning
verification off.

To re-read a page on purpose, fetch it with the same client, replace the file
here, and record its new hash and date in `SOURCES`.
