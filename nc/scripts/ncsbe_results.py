#!/usr/bin/env python3
"""
Turn one of the North Carolina State Board of Elections' precinct results
files into the list of who won each municipal contest, for
nc/scripts/build_nc_city_councils.py.

    python3 nc/scripts/ncsbe_results.py results_pct_20241105.zip "CITY OF RALEIGH"

The State Board publishes each election's results as a zip holding one
tab-separated file (Latin-1), one row per contest, choice and precinct, at
https://dl.ncsbe.gov/ENRS/<yyyy_mm_dd>/results_pct_<yyyymmdd>.zip. A row
carries the contest's name, the number of seats it fills ("Vote For") and the
votes each choice got in that precinct. It carries no winner: no column says
who was elected, so this sums each choice's "Total Votes" over the precincts
and takes the "Vote For" highest. The county boards certify each result and
the file does not say whether its counts are the certified ones, so the card's
note names the file's election rather than calling anyone certified.

Only contests named "CITY OF ...", "TOWN OF ..." or "VILLAGE OF ..." are kept,
and of those only the winners, one line per winner:

    CITY OF RALEIGH CITY COUNCIL DISTRICT A: Mitchell Silver

A seat whose names come from such a file carries that line as its `as` in the
seats file, so the build proves the contest as well as the name: a losing
candidate is in no line, and a winner of District A is not a winner of
District B. Where two choices tie for a contest's last seat, neither is
listed, because the file cannot say how the county board broke the tie (the
State Board's file for 4 November 2025 has one, for Wadesboro's council, at
295 votes each); a seat this builder names from such a contest is then missing
and the build says so.
"""

import collections
import csv
import io
import sys
import zipfile

PREFIXES = ("CITY OF ", "TOWN OF ", "VILLAGE OF ")

# The results files nc/scripts/build_nc_city_councils.py reads, each named as
# a place's `results` source in nc/data/source/nc-city-council-seats.json.
# They are here, beside the reader that understands them, rather than in the
# builder: the builder sends a browser's client to the seven council pages
# that refuse this project's own, and scripts/probe_user_agents.py judges
# every host a file names by the strongest client that file sends, while
# these files are fetched with the project's own token like every page not in
# that list.
RESULTS = (
    "https://dl.ncsbe.gov/ENRS/2024_11_05/results_pct_20241105.zip",
    "https://dl.ncsbe.gov/ENRS/2025_11_04/results_pct_20251104.zip",
)


def winners(body):
    """{contest: [winner, ...]} from the zip's bytes, municipal contests only."""
    totals = collections.defaultdict(collections.Counter)
    seats = {}
    with zipfile.ZipFile(io.BytesIO(body)) as zf:
        members = [n for n in zf.namelist() if n.lower().endswith(".txt")]
        if not members:
            raise RuntimeError("the results zip holds no .txt file")
        for member in members:
            with zf.open(member) as raw:
                rows = csv.DictReader(io.TextIOWrapper(raw, encoding="latin-1", newline=""),
                                      delimiter="\t")
                for row in rows:
                    contest = (row.get("Contest Name") or "").strip()
                    if not contest.startswith(PREFIXES):
                        continue
                    try:
                        votes = int(row.get("Total Votes") or 0)
                    except ValueError:
                        votes = 0
                    totals[contest][(row.get("Choice") or "").strip()] += votes
                    seats[contest] = int(row.get("Vote For") or 1)
    out = {}
    for contest, counter in totals.items():
        ranked = counter.most_common()
        n = seats[contest]
        if len(ranked) > n:
            # Only a choice with more votes than the first one left out has
            # won; a tie at the last seat elects neither of the tied here.
            cut = ranked[n][1]
            out[contest] = [name for name, v in ranked[:n] if v > cut]
        else:
            out[contest] = [name for name, _v in ranked]
    return out


def text(body):
    """The reader build_nc_city_councils.py names: one line per winner."""
    lines = []
    for contest, names in sorted(winners(body).items()):
        for name in names:
            lines.append("%s: %s" % (contest, name))
    return "\n".join(lines)


def main(argv):
    if len(argv) < 2 or argv[1].startswith("-"):
        print(__doc__.strip())
        return 0
    with open(argv[1], "rb") as fh:
        body = fh.read()
    prefixes = tuple(p.upper() for p in argv[2:])
    for line in text(body).splitlines():
        if not prefixes or line.startswith(prefixes):
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
