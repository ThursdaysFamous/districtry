#!/usr/bin/env python3
"""Ask a host's robots.txt before fetching it, for this instance's scrapers.

WHY THIS EXISTS, AND WHAT IT COST TO NOT HAVE IT
-------------------------------------------------
FOUR Iowa scrapers fetch other people's pages on a weekly schedule under the
user-agent `districtry/1.0`, and none of them asked whether the site wanted
that. CORRECTED 2026-09-06: this docstring said THREE and gave 21 hosts, and
both were wrong in the same way -- the county BOARD-CHAIR scrape, which reads
up to 98 county sites every Friday and is by far the largest of the four, was
never counted. Re-measured across the real union: **108 distinct hosts, of
which FOUR say no**:

  cityofpalo.com                 city-officials scrape
  johnson-county.granicus.com    minutes chair scrape
  www.cherokeecounty.iowa.gov    board-chair scrape (Revize CMS)
  www.hamiltoncounty.iowa.gov    board-chair scrape (Revize CMS)

ALL FOUR ARE THE SAME FILE, AND THE LAST TWO SHOW WHY THAT MATTERS. Each names
a handful of big-name crawlers, allows them everything, and ends
`User-agent: * / Disallow: /`. On the two county sites that file is not the
county's own composition at all -- it is served by the Revize CMS from
`cms7files.revize.com` and `cms2.revize.com`, byte-identical at 210 bytes, and
`/robots.txt` on the county domain answers 200 by REDIRECTING there. So the
refusal is a VENDOR DEFAULT reaching however many of its customers, which is
the reason to keep asking per host rather than reasoning about who a county is.

BOTH FILES READ AS PERMISSIVE FOR THE FIRST FOUR HUNDRED BYTES AND REFUSE IN
THE LAST TWO LINES. That is the trap and it is why this module exists rather
than a note in a docstring: a human skimming any of them concludes it only
protects an admin path. READ THE WHOLE FILE, or better, do not read it by eye
at all.

The other 104 hosts break down as: 49 serve no robots.txt at all (a 404, which
RFC 9309 makes "allow all"), 44 serve one that permits the paths we read, 8
answer HTTP 202 -- the captcha shape, which is an access control and is left
alone -- and 3 were unreachable on the measuring run (2 connection resets and
one HTTP 500), which this module treats as disallow.

WHAT A REFUSAL DOES, AND WHY IT IS NOT A HAND LIST
----------------------------------------------------
A refused unit is SKIPPED, with its reason printed, and its page is never
requested. It is NOT removed from the caller's table: the check runs every
week, so a host that changes its file re-enters by itself and one that starts
refusing drops out the same way, which is the shape this instance's currency
gate already uses. What makes that safe is the caller's own count floor --
one unit leaving is ordinary, a collapse is not.

RFC 9309 IS FOLLOWED WHERE IT IS AWKWARD, NOT ONLY WHERE IT IS CONVENIENT:
an unavailable robots.txt (4xx) means allow all, and an UNREACHABLE one (5xx,
or a network failure) means DISALLOW all. So a transient outage on a host's
robots.txt can cost a unit for one run. That is the conservative direction and
it is printed, never silent.

Usage:
    from robots_gate import RobotsGate
    gate = RobotsGate(session, USER_AGENT)
    ok, why = gate.allows(url)
"""

import threading
import urllib.parse
from urllib.robotparser import RobotFileParser


class RobotsGate(object):
    """One robots.txt fetch per host, cached for the life of the run.

    THREAD-SAFE, because one of its four callers is not single-threaded: the
    county board-chair scrape runs six workers over 98 counties, and without
    the lock two of them racing the same host would each fetch its robots.txt
    and one would overwrite the other's cache entry. The lock is held across
    the FETCH, not just the dict write, so a host is requested exactly once
    however many workers want it at the same moment.
    """

    def __init__(self, session, user_agent, timeout=30):
        self._session = session
        self._ua = user_agent
        self._timeout = timeout
        self._cache = {}
        self._lock = threading.Lock()

    def _rules(self, root):
        if root in self._cache:                 # fast path, no lock
            return self._cache[root]
        with self._lock:
            if root in self._cache:             # another worker won the race
                return self._cache[root]
            return self._fetch(root)

    def _fetch(self, root):
        try:
            r = self._session.get(root, headers={"User-Agent": self._ua,
                                                 "Accept": "text/plain,*/*"},
                                  timeout=self._timeout, allow_redirects=True)
            status, body = r.status_code, r.text
        except Exception as exc:
            self._cache[root] = (None, "%s: %s" % (type(exc).__name__, exc))
            return self._cache[root]
        if status == 200 and body.strip():
            parser = RobotFileParser()
            parser.parse(body.splitlines())
            self._cache[root] = (parser, "robots.txt served (%d bytes)" % len(body))
        elif 400 <= status < 500:
            self._cache[root] = ("allow", "no robots.txt (HTTP %d)" % status)
        else:
            self._cache[root] = (None, "robots.txt unreachable (HTTP %d)" % status)
        return self._cache[root]

    def allows(self, url):
        """(True, why) if this user-agent may fetch `url`, else (False, why)."""
        parts = urllib.parse.urlparse(url)
        root = "%s://%s/robots.txt" % (parts.scheme, parts.netloc)
        rules, why = self._rules(root)
        if rules == "allow":
            return True, why
        if rules is None:
            return False, why
        return rules.can_fetch(self._ua, url), why
