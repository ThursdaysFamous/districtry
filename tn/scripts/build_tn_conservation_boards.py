#!/usr/bin/env python3
"""
Build tn/data/app/tn-conservation-boards.json: the supervisors of the soil
and water conservation district in each of Tennessee's 95 counties, read from
the Department of Agriculture's directory, for the County card.

    python3 tn/scripts/build_tn_conservation_boards.py            # read, parse, write
    python3 tn/scripts/build_tn_conservation_boards.py --check    # offline
    python3 tn/scripts/build_tn_conservation_boards.py --watch    # has any name changed?

The work is scripts/conservation_boards.py, which says what is read, what is
carried and what the checks prove. This file says where Tennessee publishes
its boards and how to read the publication.

THE SOURCE. The Tennessee Department of Agriculture's "Tennessee Soil and
Water Conservation District Directory", one PDF (DIRECTORY below). The
department's directory page links it, and that page answered this project's
client with HTTP 403 twice on 2026-10-16 while the PDF it leads to was served
(HTTP 200, 230,324 bytes), so the PDF is read at its own address and the page
is never fetched. No other client was tried on the page. The PDF prints no
date; its own metadata says it was made on 3 September 2026 and last changed
on 4 September 2026, and the card shows the second as the directory's date.
The address has a space in its file name under the department's document
store, so it may change when the department replaces the file (inferred);
a build that cannot read it keeps what it last read, and WATCH.md carries the
re-read.

REFUSED ON MOST READS, AND SO NOT BUILT. Read again from 22:55 to 22:58 UTC
on 2026-10-16, the PDF answered 403, 200, 200, 403, 200, 403: each 403 a
118-byte body from awselb/2.0, the state's AWS load balancer, and each 200 the
same file from Apache. Read three times 20 seconds apart from 23:10 UTC it
answered 403 all three times. robots.txt answered 403 too, which RFC 9309
reads as no policy. No other client was tried. A control that refuses on some
reads and serves on others is treated as an access control, the rule
CLAUDE.md sets for a managed challenge, so the file is not built from a read
that happened to be served: this builder is not to be run until the host
serves three consecutive reads at least 15 seconds apart, re-measured
deliberately and recorded here with its date (tn/WATCH.md carries it). Whether this project's own
reads tripped a rate rule is not established. Re-measured on 2026-10-23 with
this builder's own client: robots.txt was served this time (23 bytes,
"Allow: /"), and the PDF answered 403 on all three reads, at 15:04:48,
15:05:06 and 15:05:23 UTC, each the same 118-byte awselb/2.0 body, so it is
still not built. What follows describes the
copy read that morning, which the parser was written and tested against.

WHAT IT GIVES. One block per county, the 95 in alphabetical order: the
district's office address, telephone, one member of staff, an e-mail address,
and five supervisor lines, each a name and a label ("SWCD Supervisor" on 473,
"SCD Supervisor" on one in Dyer County and "Supervisor" on one in Rutherford),
or "Vacant" (two on 2026-10-16, in Hancock and Unicoi). Carried: each
supervisor's name exactly as printed, or a vacancy. The directory names no
officers and gives no terms, and does not say whether a seat is elected or
appointed: the words elect, appoint, term, chair and treasurer appear nowhere
in it. So the card names the five and says the directory does not say how
they are chosen; nothing here claims that the voters elect them.

PRIVACY. Only the supervisor lines are read. Each block also carries the
district office's address, telephone and e-mail address and its staff
member's name; three of the e-mail addresses are named after a person at a
consumer mail provider and four telephone lines carry a second number nobody
labels, and none of it is copied. The PDF's metadata names its author; that
is not recorded.

TERMS OF USE. The PDF carries no notice. The department's pages on tn.gov,
where its terms would be, answered this project's client with HTTP 403 on
2026-10-16, so they could not be read. Names are printed exactly as the
directory prints them, and every card cites it.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
tn-conservation-boards): the state's only list of who sits on these boards is
a PDF with no date printed in it, at an address that changes with the file;
it names no officers, no terms and nothing about how a seat is filled; no
state office publishes when supervisors are elected or appointed, or the
results; and the department's directory page refuses this project's client
while the document it links is served.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import conservation_boards as cb  # noqa: E402

DIRECTORY = ("https://www.tn.gov/content/dam/tn/agriculture/documents/landwaterstewardship/"
             "ada-compliant-forms/SWCD%20Directory-ADA.pdf")

HEADER_RE = re.compile(r"^(?P<county>.+?) County SWCD$")
EMAIL_RE = re.compile(r"^E-?mail:", re.I)
SUPERVISOR_RE = re.compile(r"^(?P<name>.+), (?P<label>(?:SWCD |SCD )?Supervisor)$")


def parse(url, body, county):
    text = cb.pdf_text(body)
    blocks = []
    cur = None
    for raw in text.split("\n"):
        line = cb.clean(raw)
        if not line:
            continue
        m = HEADER_RE.match(line)
        if m:
            cur = {"county": m.group("county"), "lines": []}
            blocks.append(cur)
        elif cur is not None:
            cur["lines"].append(line)
    if not blocks:
        raise RuntimeError("no county block found in the directory")
    dated = cb.pdf_date(body)
    boards = []
    for b in blocks:
        emails = [i for i, line in enumerate(b["lines"]) if EMAIL_RE.match(line)]
        if len(emails) != 1:
            raise RuntimeError("%s County: %d e-mail lines where the directory prints one"
                               % (b["county"], len(emails)))
        seats = b["lines"][emails[0] + 1:]
        members = []
        for line in seats:
            m = SUPERVISOR_RE.match(line)
            if not m:
                raise RuntimeError("%s County: a line after the e-mail line that is not a "
                                   "supervisor: %r" % (b["county"], line))
            name = m.group("name").strip()
            members.append({"vacant": True} if name.casefold() == "vacant" else {"name": name})
        board = {
            "county": b["county"],
            "name": "%s County Soil and Water Conservation District" % b["county"],
            "members": members,
        }
        if dated:
            board["dated"] = dated
        boards.append(board)
    return boards


SPEC = cb.Spec(
    tag="tn",
    label="build_tn_conservation_boards",
    user_agent="districtry/1.0 (+https://districtry.com/tn/)",
    parse=parse,
    seats=lambda board: 5,
    member_keys=(),
    documents=(DIRECTORY,),
    card_claims=(
        "The state's directory does not say how they are chosen",
    ),
)

if __name__ == "__main__":
    cb.main(SPEC, __doc__)
