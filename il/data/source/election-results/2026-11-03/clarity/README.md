# Clarity precinct results, 3 Nov 2026 (unofficial snapshot)

Each zip is the `detailxml.zip` report Clarity Elections publishes for one
Illinois results site: every race, every candidate, every precinct. They are
the counties' **unofficial** election-night numbers. Each county canvasses by
about 24 Nov 2026, and the canvassed numbers can differ.

`scripts/il_clarity_election_results_reader.py` reads every file here except
Madison's into `il/data/source/election-results-clarity-raw.json`, which the
Illinois Election Results layer's daily rebuild folds in beside Chicago's and
the other counties' results. The rebuild never downloads anything from
Clarity, so these counties stay at the numbers of the last hand download, and
each card gives the time of its own report. Madison's file is not read: on
9 Nov 2026 the county's precinct layer, which the map draws, answered every
request with an ArcGIS error page, so its precincts could not be matched.
`il/data/source` is not published by the deploy.

| File | Results site | Precincts |
|---|---|---|
| `dupage-detailxml.zip` | DuPage County | 605 (600 match our shapes; 5 are "FEDERAL - Fxx" rows) |
| `lake-detailxml.zip` | Lake County | 431 |
| `macoupin-detailxml.zip` | Macoupin County | 45 |
| `madison-detailxml.zip` | Madison County | 191 |
| `mchenry-detailxml.zip` | McHenry County | 223 |
| `mclean-detailxml.zip` | McLean County, outside Bloomington | 81 |
| `bloomington-detailxml.zip` | City of Bloomington (its own election authority) | 60 |
| `sangamon-detailxml.zip` | Sangamon County | 166 |
| `winnebago-detailxml.zip` | Winnebago County and Rockford | 94 |
| `will-detailxml.zip` | Will County | 310 |

`record.json` gives, for each file, the exact URL, Clarity's version number,
the report's own timestamp, the byte count, the SHA-256 and when it was
fetched.

## Why these were downloaded by hand and committed

On 5 Nov 2026 `https://results.enr.clarityelections.com/robots.txt` answered
our reader from a GitHub runner with **HTTP 202 and an empty body**, served by
CloudFront, on three reads 20 seconds apart, on both HTTP stacks (Actions run
42069482060). Our rules read that as an access control, so **no scheduled job
may fetch Clarity**. From the research sandbox the same file answered 404 (no
policy, allow all).

Adam (the operator) ruled at 17:50 UTC that day, choosing "relay": "You are
just doing the download for me, which i can get to manually." So these files
were downloaded once from the sandbox, robots.txt read first, with the
project's own reader (`districtry.com roster bot`), and committed here. That
ruling covers these one-off downloads. It does not make Clarity a source a
workflow may read. A refresh, or the canvassed numbers, is another download
made the same way, recorded in `record.json`
(`scripts/il_clarity_election_results_download.py`, run by hand only). The
DuPage, Lake and Madison reports were downloaded again that way on 9 Nov 2026,
their versions having moved; the others had not moved since 5 Nov. After a new
download, run the reader again and commit its output with the files, or CI
fails.

Will County's report was downloaded on 9 Nov 2026 at Adam's request, after he
found the county's Clarity site (election 127394) and sent its address. The
county's own site, willcountyclerk.gov, answers our robots.txt request with an
AWS WAF challenge, and Clarity's listing for Will does not name the election,
so it had not been found before. Its report is Clarity's version 384833, of
3 Nov 2026 at 9:37 PM CST, and its counts equal the text download Adam made
from the same page that day.
