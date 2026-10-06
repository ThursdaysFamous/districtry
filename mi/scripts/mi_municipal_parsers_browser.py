"""Unit table and parsers: the townships whose sites serve only a browser-class
client. Contract in mi_municipal_common.py.

WHY A MODULE OF ITS OWN. These units are the only ones in the Michigan
municipal scrape that are read with a browser string rather than the fleet's
roster token, and CLAUDE.md's browser-string rule asks that the measurement
licensing it sit in the calling file. Keeping them apart also keeps the other
batches honest: scripts/probe_user_agents.py classifies a whole FILE by the
client it sends, so putting these two units in mi_municipal_parsers_townships.py
would have reported all of that module's township hosts as reached by a
browser string, which none of them is.

Each unit carries `headers`: the header set the scraper sends for it, and the
one it reads that host's robots.txt with, on the stdlib client. The policy is
read with exactly the client that crawls.

THE MEASUREMENT, 2026-10-01, through scripts/probe_user_agents.probe_host on
the exact page each unit reads (four rungs: each HTTP stack with the roster
token and with Chrome/126 plus its client hints):

    www.shelbytwp.org/government/board-of-trustees
        requests+token   HTTP 403
        stdlib+token     HTTP 403
        requests+chrome  HTTP 403
        stdlib+chrome    HTTP 200, 148,379 bytes, the board table
    www.twp.northville.mi.us/your-government/board-of-trustees
        requests+token   HTTP 403
        stdlib+token     HTTP 403
        requests+chrome  HTTP 403
        stdlib+chrome    HTTP 200, 139,793 bytes, the board table

So each host refuses BOTH the token and the requests stack, and serves only the
browser string on the stdlib stack: the Kendall and McHenry shape, an edge that
fingerprints the client rather than a site that refuses automation. Read with
that same client, each robots.txt is served (6,641 bytes, the website vendor's
default, byte-for-byte the file Kendall, McHenry and Joliet serve) and no rule
in its one binding group matches the board page. The probe flagged "page
carries a captcha widget"; on both pages that is the CMS's own configuration
naming a reCAPTCHA key for its contact forms, not a challenge in front of the
page, which arrives whole.

THE EARLIER RECORD WAS WRONG AND A LETTER WENT OUT ON IT. Both units were
recorded that morning as "Access Denied, no other client tried", and the clerk
letters of docs/ASK_DRAFTS.md (Ask mi-city-township-boards) repeated it. The
operator sent each clerk a correction the same afternoon. A record
that says no other client was tried has not been measured yet.

If either host starts refusing this client too, the scraper records the refusal
and the builder carries the last good read forward; no thinner client is tried
after a refusal, and a challenge is never worked around.
"""

import os
import re
import sys

_ROOT_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "scripts")
if _ROOT_SCRIPTS not in sys.path:
    sys.path.insert(0, _ROOT_SCRIPTS)

from scraper_common import UA_HINTS_CHROME_126  # noqa: E402  (one copy, the one the probe measured)
from mi_municipal_common import member, phones_in, txt  # noqa: E402
from mi_municipal_parsers_townships import _finish, _name, _need, _role  # noqa: E402


def _flip(s):
    """'Grot, Stanley T.' -> 'Stanley T. Grot'. Both pages print every member
    surname first; a name without the comma is refused rather than guessed."""
    t = txt(s)
    _need(t.count(",") == 1, "%r is not 'Surname, Given'" % t[:80])
    last, first = [p.strip() for p in t.split(",")]
    return _name("%s %s" % (first, last))


def _rows(h):
    return [re.findall(r"<td\b[^>]*>(.*?)</td>", r, re.S)
            for r in re.findall(r"<tr\b[^>]*>(.*?)</tr>", h, re.S)]


def parse_shelby(h, also):
    """A CivicPlus staff-directory table: Staff, Title, Departments, Phone,
    Email. The e-mail cell is a script link that carries no address, so no
    member address ships; each member's phone does, and a number printed for
    two members moves to the board's shared line (the supervisor's office line
    is printed for one trustee too)."""
    table = re.search(r'<table class="listtable">(.*?)</table>', h, re.S)
    _need(table, "Shelby: no staff-directory table")
    out = []
    for cells in _rows(table.group(1)):
        if not cells:
            continue
        _need(len(cells) == 5, "Shelby: a row of %d cells, expected 5" % len(cells))
        _need(txt(cells[2]) == "Board of Trustees",
              "Shelby: department %r, expected Board of Trustees" % txt(cells[2]))
        tel = phones_in(cells[3])
        out.append(member(_flip(cells[0]), _role(cells[1]),
                          phone_=tel[0] if len(tel) == 1 else None))
    return _finish(out)


def parse_northville(h, also):
    """A hand-built 'Meet the Board' table: Name, Title, Contact. The contact
    cell links each member's web form, not an address, so no address ships."""
    body = re.search(r"Meet the Board</h3>\s*<table\b.*?</table>", h, re.S)
    _need(body, "Northville: no 'Meet the Board' table")
    out = []
    rows = _rows(body.group(0))
    _need(rows and [txt(c) for c in rows[0][:2]] == ["Name", "Title"],
          "Northville: header row is not Name, Title")
    for cells in rows[1:]:
        _need(len(cells) == 3, "Northville: a row of %d cells, expected 3" % len(cells))
        out.append(member(_flip(cells[0]), _role(cells[1])))
    return _finish(out)


def _u(geoid, name, body, url, parse, seats=7):
    return {"geoid": geoid, "name": name, "kind": "township", "body": body,
            "url": url, "seats": seats, "parse": parse,
            "headers": dict(UA_HINTS_CHROME_126)}


UNITS = [
    _u("2609972820", "Shelby", "Board of Trustees",
       "https://www.shelbytwp.org/government/board-of-trustees", parse_shelby),
    _u("2616359000", "Northville", "Board of Trustees",
       "https://www.twp.northville.mi.us/your-government/board-of-trustees",
       parse_northville),
]
