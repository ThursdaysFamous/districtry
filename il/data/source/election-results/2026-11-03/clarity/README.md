# Clarity precinct results, 3 Nov 2026 (unofficial snapshot)

Each zip is the `detailxml.zip` report Clarity Elections publishes for one
Illinois results site: every race, every candidate, every precinct. They are
the counties' **unofficial** election-night numbers. Each county canvasses by
about 24 Nov 2026, and the canvassed numbers can differ. Nothing in the apps
reads these files yet; they are build inputs for county results readers, and
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
made the same way, recorded in `record.json`.
