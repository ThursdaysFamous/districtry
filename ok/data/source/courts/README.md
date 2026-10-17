# Oklahoma judicial districts: excerpts of the State Election Board's roster

These files are what `ok/scripts/build_ok_judicial_districts.py` reads to draw
Oklahoma's 26 district court judicial districts. Every district is a set of
whole counties, so the county lists are the boundary: the builder dissolves the
county fabric this instance already ships (`ok/data/app/state-counties.json`),
and no map is read.

Both are excerpts of one document: the Oklahoma State Election Board's "Roster
of Oklahoma State and County Officers, Elected at the General Election November
5, 2024, Including Holdover State Officials", published March 18, 2025, read on
2026-10-16 from
`https://oklahoma.gov/content/dam/ok/en/elections/rosters/officer-roster-2024.pdf`
(460,946 bytes, SHA-256
`f8e6d97e5a40e13b3d03e4cce6fb75747e6276e1287950bb64890dbbbcb965d3`) with this
project's own client, after reading robots.txt at every hop.

| file | what it settles |
|---|---|
| `ok-roster-2024-district-judge-offices.txt` | every district judge office (75 of them) under its district, with the counties whose voters elect it |
| `ok-roster-2024-key-to-districts.txt` | each of the 77 counties' district judge district, from the roster's own key; the build requires it to agree with the offices on every county |

**NO NAME AND NO HOME TOWN IS COPIED.** The roster prints each judge's name and
home town under the office heading. Only the heading is kept: these maps name no
judge yet, and this project never writes an officeholder's home town.

**WHY NOT THE STATUTES.** The districts are set in the Oklahoma Statutes, and
both of the state's publishers of them refuse this project in robots.txt: the
`*` group in each, which is the one that binds this project, disallows every
page, while oklegislature.gov admits named search engines and oscn.net leaves
only its news feeds open. Measured on 2026-10-16 and recorded as a
data-publishing hurdle: the one readable statement of which counties make up
each court district is a roster of who won the last election.

**THE ROSTER IS A SNAPSHOT.** A new edition follows each general election.
`ok/WATCH.md` carries a row to re-read the district lists when the 2026 edition
is posted.
