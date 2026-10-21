# Louisiana court laws, as published

These are the two laws `la/scripts/build_la_court_districts.py` reads to draw the
courts of appeal and the district courts. Both courts' districts are lists of
whole parishes written into the law, so these lists are the boundary source and
nothing else is read for them. `la/scripts/build_la_judges.py` reads the first one
again for which parishes each court of appeal election section takes in.

| file | the law | read from | what it settles |
|---|---|---|---|
| `rs13-312.txt` | La. R.S. 13:312, Courts of appeal; circuits and districts | `https://legis.la.gov/legis/Law.aspx?d=77438` | the five circuits, the three districts of each, the election sections some districts are divided into, and that St. John the Baptist Parish is divided by the Mississippi River between the Fifth Circuit's second and third districts |
| `rs13-477.txt` | La. R.S. 13:477, Judicial districts | `https://legis.la.gov/legis/Law.aspx?d=149496` | the judicial districts and their parishes; it names 41, its 41st is repealed (Act 474 of 2012), so they are numbered 1 to 40 and 42, and it leaves out Orleans Parish, which has courts of its own |

Each file was read on 2026-10-21 with this project's client
(`districtry/1.0 (+https://districtry.com/la/)`) and opens with a header giving its
address, that date, and the page's size and SHA-256 as served (69,804 bytes for
13:312, 73,465 for 13:477). The rest is the page's text from the section's heading
to the end of its history notes, with scripts, styles and tags removed, one line per
line. Nothing else is changed, so the law's spelling stays: it writes "DeSoto",
which the builder matches to the Census's "De Soto" by letters alone.

The files are kept as `.txt` and not as the pages' HTML on purpose: the site's page
gates treat an `.html` file in an instance folder as a page a reader is served.

**WHAT HOLDS THEM.** The builder's offline `--check` re-reads every parish list out
of these two files and holds both shipped maps to it: every parish drawn once, and
each district's area its own parishes' area in `la/data/app/state-counties.json`.
`--fetch` reads both pages again and converts them the same way; a file whose text is
unchanged is left alone, header and all, and a changed one is rewritten with a new
header and named, for a person to read before rebuilding.

**THE SUPREME COURT IS NOT HERE**, because its districts are not written as parishes:
Act 7 of the 2024 Regular Session (Senate Bill 255) enacted La. R.S. 13:101.2, whose
seven districts are drawn from voting precincts, and 13:101.3, which keeps each
justice in office when the act took effect in the district with the same number until
the term ends. The map comes from the Legislature's own shapefile for the act, on the
redistricting office's page for it (`https://redist.legis.la.gov/2024_Files/2024LASSCAct7.aspx`):
`Act_7_-__RS_(2024)_-_LASC.zip`, 1,347,641 bytes, SHA-256
`d645d4068c3bd685b945ca58b6f7e9ac7bed28f97ea302889d58075fec62fc33`, last modified
3 June 2024, read 2026-10-21. The builder holds the file to that hash
(`ZIP_SHA256`), so a file replaced in place stops the build until a person has read
it, and `la/data/source/la-supreme-court-districts.source.json` records what the
shipped map was built from and measured against; `--check` holds the shipped map to
that record. The act itself was read the same day from
`https://legis.la.gov/legis/ViewDocument.aspx?d=1371415` (the enrolled act, a PDF of
88,702 bytes, SHA-256 `341b7604f197d4f90311adc4e92941a2e1807730397209470508abf4194a9669`)
and is not kept; its 13:101.3 is why the Supreme Court card says a sitting justice may
have been elected by voters inside different lines.

**THE HOSTS.** `legis.la.gov` and `redist.legis.la.gov` publish no robots.txt (HTTP
404 on 2026-10-21, which RFC 9309 §2.3.1.3 reads as allow-all), read with the same
client before the pages.

To re-read a law on purpose, run `python3 la/scripts/build_la_court_districts.py
--fetch`, read what changed in git, then rebuild the maps and `la-judges.json`, whose
parish lists are held to them.
