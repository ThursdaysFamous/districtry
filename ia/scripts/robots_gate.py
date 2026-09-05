#!/usr/bin/env python3
"""Ask a host's robots.txt before fetching it, for this instance's scrapers.

WHY THIS EXISTS, AND WHAT IT COST TO NOT HAVE IT
-------------------------------------------------
Two Iowa scrapers fetch other people's pages on a weekly schedule under the
user-agent `districtry/1.0`, and neither asked whether the site wanted that.
Reviewed 2026-09-05, and TWO of the 21 hosts they read say no:

  cityofpalo.com                 ends its robots.txt `User-agent: * /
                                 Disallow: /`, after naming Googlebot,
                                 bingbot, ia_archiver, archive.org_bot,
                                 W3C-checklink and CCBot and allowing each of
                                 them everything but /admin/ and /manager/.
  johnson-county.granicus.com    the same shape: Googlebot, Slurp, msnbot and
                                 search-one-scgov are allowed everything but
                                 /JSON.php, and `User-agent: *` is disallowed
                                 from `/`.

BOTH FILES READ AS PERMISSIVE FOR THE FIRST FOUR HUNDRED BYTES AND REFUSE IN
THE LAST TWO LINES. That is the trap and it is why this module exists rather
than a note in a docstring: a human skimming either file concludes it only
protects an admin path. READ THE WHOLE FILE, or better, do not read it by eye
at all.

The other nineteen hosts allow: sixteen serve no robots.txt at all (a 404,
which RFC 9309 makes "allow all"), and moraviaiowa.com,
www.marioncountyiowa.gov and www.dallascountyiowa.gov serve one that permits
the paths we read.

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

import urllib.parse
from urllib.robotparser import RobotFileParser


class RobotsGate(object):
    """One robots.txt fetch per host, cached for the life of the run."""

    def __init__(self, session, user_agent, timeout=30):
        self._session = session
        self._ua = user_agent
        self._timeout = timeout
        self._cache = {}

    def _rules(self, root):
        if root in self._cache:
            return self._cache[root]
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
