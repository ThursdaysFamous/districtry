# Indiana Court of Appeals districts: what the layer is built from

These files are what `in/scripts/build_in_appeals_districts.py` reads to draw
the Court of Appeals of Indiana's 1st, 2nd and 3rd Districts. Each is a set of
whole counties, so the county lists are the boundary: the builder dissolves the
county fabric this instance already ships (`in/data/app/state-counties.json`).
Both were read on 2026-10-16 from the court's own pages on in.gov, with this
project's own client, after reading robots.txt at every hop.

| file | what it settles |
|---|---|
| `coa-districts-page.txt` | that three judges come from each of the 1st, 2nd and 3rd Districts and stand for retention only there, while the 4th and 5th Districts' judges stand for retention statewide, which is why only the first three are drawn |
| `coa-district-map-reading.tsv` | which of the three districts each of the 92 counties is in, read from the court's own district map image; the file's header records the image's address, size and SHA-256 and the method |

**THE COUNTY LISTS ARE READ FROM A PICTURE**, because that is the only form in
which the court publishes them, and the Indiana Code that sets them could not
be read: the General Assembly publishes the Code only through a site that
serves an empty page to anything that does not run its scripts, robots.txt
included (measured 2026-10-15). That is recorded as a data-publishing hurdle:
which counties vote on which appeals judges is law, and the one readable copy is
an image.

**TWO GUARDS MAKE A MISREAD COUNTY STOP THE BUILD.** The counts per district
are pinned (53, 19 and 20, counted on the map), and every district must
dissolve to one piece of ground, since a county put in the wrong district
would almost always sit apart from the rest of it.
