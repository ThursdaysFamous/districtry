#!/usr/bin/env python3
"""
Turn the Muskogee County Election Board's official results for the City of
Muskogee's election of 10 February 2026 into the list of who won each
contest, for ok/scripts/build_ok_city_councils.py.

    python3 ok/scripts/muskogee_results.py results.pdf

The county's results are a two-page PDF, "Official Results - Elections -
February", printed 2 March 2026, with one block per contest: a heading line
("FOR CITY COUNCIL WARD 1 CITY OF MUSKOGEE", then how many of the contest's
precincts reported) and one line per candidate giving the absentee, early,
election-day and total votes and the candidate's share. The copy read here is
the one KJRH, a Tulsa television station, published with its report of the
results, at the address in RESULTS below: the county's own results are served
by the State Election Board's results system, which does not let this project
read it, and the City of Muskogee's website does not either.

A candidate wins a contest here only with more than half its votes. That is
the rule in Muskogee's elections: in this file Ward 4's contest and the
contest for the rest of Ward 1's unexpired term had no such candidate, both
went to a runoff on 7 April 2026, and those two seats are named from news
reports instead. So this reader writes only the four contests decided on 10
February, one line per winner, the contest heading as printed and the name
as printed:

    FOR CITY COUNCIL WARD 1 CITY OF MUSKOGEE: SHIRLEY F. HILTON-FLANARY

A seat whose name comes from this file carries that line as its `as` in the
seats file, so the build proves the contest as well as the name: a losing
candidate is in no line, and the winner of Ward 1 is not the winner of Ward 2.
"""

import re
import subprocess
import sys

# The results file ok/scripts/build_ok_city_councils.py reads, named as
# Muskogee's `results` source in ok/data/source/ok-city-council-seats.json.
# It is here, beside the reader that understands it, rather than in the
# builder: the builder sends a browser's client to Broken Arrow's council page,
# which refuses this project's own, and scripts/probe_user_agents.py judges
# every host a file names by the strongest client that file sends, while this
# file is fetched with the project's own token like every other page.
RESULTS = (
    "https://ewscripps.brightspotcdn.com/26/56/3408f6ec43dba01d05a6b907900c/results.pdf",
)

PRECINCTS_RE = re.compile(r"\s{2,}\d+ of \d+ Precincts.*$")
CANDIDATE_RE = re.compile(
    r"^(\S.*?)\s{2,}[\d,]+\s+[\d,]+\s+[\d,]+\s+([\d,]+)\s+([\d.]+)%\s*$")


def layout_text(body):
    """The PDF's text with its columns kept, as pdftotext -layout writes it."""
    try:
        done = subprocess.run(["pdftotext", "-layout", "-", "-"], input=body,
                              capture_output=True, check=True, timeout=120)
    except FileNotFoundError:
        raise RuntimeError("this results file is a PDF and pdftotext (poppler-utils) is "
                           "not installed")
    return done.stdout.decode("utf-8", "replace")


def winners(body):
    """{contest heading: winner} for every contest a candidate won outright."""
    if body[:5] != b"%PDF-":
        raise RuntimeError("the Muskogee results file is not a PDF")
    contest = None
    shares = {}
    for raw in layout_text(body).splitlines():
        line = raw.strip()
        if line.startswith("FOR "):
            contest = PRECINCTS_RE.sub("", line).strip()
            shares.setdefault(contest, [])
            continue
        m = CANDIDATE_RE.match(line)
        if m and contest:
            shares[contest].append((m.group(1).strip(), float(m.group(3))))
    if not shares:
        raise RuntimeError("no contest found in the Muskogee results file")
    out = {}
    for name, rows in shares.items():
        if not rows:
            raise RuntimeError("contest %r lists no candidate this reader can read" % name)
        top = [cand for cand, pct in rows if pct > 50.0]
        if len(top) == 1:
            out[name] = top[0]
    return out


def text(body):
    """The reader build_ok_city_councils.py names: one line per winner."""
    return "\n".join("%s: %s" % (contest, name)
                     for contest, name in sorted(winners(body).items()))


def main(argv):
    if len(argv) < 2 or argv[1].startswith("-"):
        print(__doc__.strip())
        return 0
    with open(argv[1], "rb") as fh:
        print(text(fh.read()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
