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

**NO HOME TOWN IS COPIED.** The roster prints each judge's name and home town
under the office heading. The two files above keep only the heading. Since
2026-11-25 `ok-roster-2024-district-judges.txt` keeps the name too, for the
Judicial District card, and still never the home town: this project never
writes an officeholder's home town.

## The judges' names (read 2026-11-25)

`ok/scripts/build_ok_district_judges.py` builds `ok/data/app/ok-district-judges.json`
from these, offline. Each file's header says where and how it was read.

| file | what it settles |
|---|---|
| `ok-roster-2024-district-judges.txt` | the name the roster prints under each of the 75 offices (same PDF and hash as above) |
| `ok-jnc-appointments-district-judges.txt` | the Judicial Nominating Commission's list of the Governor's district judge appointments, to lay those made since the roster over it |
| `ok-candidates-2026-district-judges.txt` | every candidate who filed for each office in April 2026 (the Election Board's candidate list) |
| `ok-results-2026-district-judges.txt` | the Election Board's official 2026 results for every district judge race, read once by hand in a browser because the results site refuses this project's reader |
| `oscn-adair-district-judges-2026-11-25.txt` | the four District 15 judges on the courts' own Adair County page, the one court page read (by hand, in a browser); the build must name the same four |

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
