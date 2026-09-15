# Review casebook

Incidents the manager's rules were learned from, keyed by what they looked
like rather than by PR number. Each entry says what the symptom looked like,
what it actually was, and what check now catches it. `docs/MANAGER.md` names
the check; this file holds the story. Read once per session.

## A 403 identifies who refused only if you know which hop produced it

Three instances, three different hops.

- Boone's weekly run failed with 0 Belvidere Park board members. The log said
  `403 Client Error: Forbidden` a few lines above the FAIL. Reading only the
  FAIL line, then fetching the page by hand (it answered 200), produced a
  confident instruction to rewrite a parser that was fine. #835 shipped all
  five members unchanged. The 403 was the county's edge refusing the runner
  that hour.
- A first draft of the shared robots reader made a 403 on robots.txt a
  refusal fleet-wide. The Wisconsin audit run against it reported 32
  disallowed fetches, every one on an API host (ArcGIS Online,
  nationalmap.gov, openstates) that 403s robots.txt while serving everyone.
  Measured, reversed, recorded: a 403 on robots.txt itself is `refused` and
  allowed by default, and a municipal-website scraper opts into the strict
  reading.
- In the manager's sandbox, github.com answers 403 with the egress proxy's own
  JSON body. That is the proxy, not GitHub. Never record a host from a local
  run without checking who answered.

The same shape decides the user-agent question: a bare 403 is not evidence of
a user-agent refusal. Measure a browser string too, and measure the stack as
well as the token, because `requests` is refused as often as the name.

Check now: diagnose from the run's own log; the shared reader's 401/403
default; `scripts/probe_user_agents.py` asks each host four ways.

## A count that is a round multiple of the page size

A paged loader that stops silently at the transfer cap returns a clean count
that happens to be a multiple of the page size. Nothing fails. The count is
suspect until independently confirmed against a second source, such as the
service's own returnCountOnly answer.

Check now: the ArcGIS paged loader carries the cap; the monthly source report
prints envelope counts.

## 0 records from a failed fetch looks identical to 0 records from a failed parse

The Boone case above, generalised. A builder that reads an empty scrape and a
builder that reads a full scrape it cannot parse both report zero, and a floor
fires either way. Only the per-stage counts above the traceback separate them.

Check now: read the whole log; floors are read with their comments.

## A push that succeeds with the PR step failing after it

`update-ia-city-contact-roster.yml` scraped, built, committed and pushed
correctly, then died on opening its PR with "API rate limit already exceeded"
for the account, most likely spent by manager review traffic the same hour.
The data sat on a pushed branch with nothing reviewing it and nothing red. A
re-dispatch went green.

Check now: read to the end of the log; the cheap gate protects the budget; a
PR step that fails alone after a successful push is worth a retry on a rate
limit.

## A renamed key one level down reading as a difference

On #875 a comparison of top-level values reported a difference that was only a
key renamed one level down. The values were all still there. Flattening both
sides to scalar leaves and diffing as multisets shows an empty "values only in
base" set and a path change, which is the truth.

Check now: `scripts/review_roster_pr.py` compares leaves, not lines or
top-level values.

## A reorder reading as a substitution

#824 had 217 identical leaf values on both sides, reordered. A line diff shows
every one as removed and added again. A multiset diff shows nothing.

Check now: the same script.

## A name swap reading as a field loss

#829 swapped two names between records. A field-coverage count saw every
field present on as many records as before. A line diff read it as a loss.
Only comparing which names appear, and where, shows a swap.

Check now: the script reports names added, removed and moved between fields.

## Values permuted within one field, totals unmoved

#837 shipped thirteen judges each carrying a colleague's phone number. Every
total was unchanged: the same phones, the same count, the same coverage. The
signature is a field whose value multiset is identical on both sides while
the assignment of values to records changed.

Check now: the script reports permutation within a field.

## A headline count re-derived differently from the shipped data

#853's "175 offices" was 175 records with something in the office block
against 138 with a street address. #860's gap summary said 491 cards link a
library's site when it was 487. #876's body said 34 counties when the run
made 37. #887's body said 116 files, 297 hosts, 68 files, "nothing was
renamed" and "three weeks"; the tree said 115, 290, 57, one file and ten days.
A count can be right in a data file and wrong in the sentence describing it.

Check now: every headline count is re-derived from the shipped data before it
is repeated; the user-agent figures are gated by `probe_user_agents.py
--check`.

## A warning nothing reads

Peoria's scraper printed three WARN lines naming exactly the three members
missing from the county's index, and the run opened its PR anyway. #870 moved
that cross-check into the output as data and floored it in the builder.

Check now: ask of any pipeline what its warnings would do if the thing they
warn about happened.

## Two stages disagreeing about which file is the accumulator

Iowa's e-mail scraper was incremental against the shipped roster while the
builder rebuilt from the caches alone, dropping 61 addresses. The count was
short by an amount no source explained.

Check now: when a count is short by an unexplained amount, ask whether some
stage is treating the output as an input.

## A confident diagnosis that was a host move, not a user-agent refusal

San Francisco's 403 was read as a site refusing the districtry token. It was
the host moving. The confident wrong answer cost more than an explicit "here
is what I could not settle" would have.

Check now: say where you are unsure when routing a diagnosis.

## A parser that loses a block cannot report the block it lost

Nine Chicago SSA cards named no provider for a day. Every gate held: 49
records passed a floor of 40, the join gated one-to-one, retention saw no
field lost, the weekly workflow opened no PR because nothing changed. The
city's page named all nine. The heading pattern could not cross a line break
inside the bolded heading, so nine blocks were absorbed into the block above,
and the gap record then stated the absence as a fact about the city. #950
fixed it and made the scraper count every bolded heading against every block
it produced.

Check now: "the source does not publish X" is only as good as the proof the
source was read whole. A count floor is not that proof.

## A verified figure goes stale as fast as an unverified one

The battery figure in `CLAUDE.md` was re-measured, independently verified,
and stale two hours later when another PR added a gate. It moved seven times
in two days. The figure is now stated with its method, its date and the
commit it was measured against.

Check now: re-measure rather than increment, and state the method.

## A pending table whose orphan check could not fail

A table of hosts pending robots refusal had an orphan check that searched the
whole source file for the host, and the source file contained the table. A
host no other table named still passed. The check now searches the source
with the pending block excised.

Check now: a check that has never failed has not been tested. Witness it
failing on a doctored input before trusting it.

## A context manager called bare

`HostPacer.hold` is a context manager. Five call sites called it as a bare
statement, so the generator was built and never entered: no crawl delay was
ever honoured, the honoured set stayed empty, and the PR body said four hosts
were paced. Two bare calls against a 2 s delay elapsed 0.00 s; two `with`
calls elapsed 2.00 s.

Check now: the run prints the pacer's report, and each scraper's self-test
measures that two fetches of a delay-stating host are actually spaced.

## A TLS fallback that protected nothing

A scraper retried every request through a context with verification off, for
every host, behind a flag nothing read. Before removing it, every host the
module names was asked with a strict context: 75 verified, none failed, two
unreachable below the certificate layer. The fallback was protecting nothing.
Measured with the Python stack the scraper uses, not with `openssl s_client`,
which inside the sandbox sees only the egress intercept's certificate and
reports every chain as perfect.

Check now: measure TLS with the stack the caller uses.
