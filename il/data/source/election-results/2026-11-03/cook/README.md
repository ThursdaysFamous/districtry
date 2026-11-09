# Suburban Cook County precinct results, 3 Nov 2026 (unofficial snapshot)

Each `.xlsx` is the Cook County Clerk's `ElectionResults.xlsx` for one race,
saved from the Clerk's results site (results1126.cookcountyclerkil.gov) in a
browser on 9 Nov 2026. The Clerk counts suburban Cook County's 1,430
precincts; Chicago's Board of Election Commissioners counts the city. The
numbers are **unofficial** until the Clerk canvasses, about 24 Nov 2026.

The files are saved by hand because the Clerk's results site answers this
project's readers with a Cloudflare block page, which is an access control
and is not worked around. `record.json` holds each file's SHA-256 and when it
was saved (the file itself carries no report time).

`scripts/il_cook_election_results_reader.py` reads every file here into
`il/data/source/election-results-cook-raw.json`, which the Illinois Election
Results layer's daily rebuild folds in beside Chicago's and the other
counties'. The rebuild never downloads anything from the Clerk, so suburban
Cook stays at the numbers saved here. `il/data/source` is not published by
the deploy.

What is here: U.S. Senator, Governor, the four other statewide offices, and
every U.S. Representative, State Senator and State Representative race on a
suburban Cook ballot. The county's own offices, judges, retention questions
and referendums are not here yet.

A district race lists only its own precincts. A precinct split between two
districts appears in both districts' files, each with the ballots cast on its
side, so on the map such a precinct offers both races.
