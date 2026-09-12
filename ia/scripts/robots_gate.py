#!/usr/bin/env python3
"""Ask a host's robots.txt before fetching it, for this instance's scrapers.

SINCE 2026-09-12 THIS IS A SHIM. The reading lives in scripts/robots_policy.py,
one copy for the fleet, and this file exists so the four Iowa callers keep
the import and the two-tuple they have used since 2026-09-06:

    from robots_gate import RobotsGate
    gate = RobotsGate(session, USER_AGENT)
    ok, why = gate.allows(url)

WHAT CHANGED, AND WHY IT HAD TO. The 2026-09-06 module parsed with Python's
urllib.robotparser, and on 2026-09-12 that parser was measured keeping only
the FIRST `User-agent: *` group of a file and dropping every later one — two
`*` groups, the second `Disallow: /Portals/`, and can_fetch answered True.
That is the wyomingmi.gov misreading this project had already made once by
hand (docs/DATA_LAYER_GUIDEBOOK.md), reproduced in the one gate that decides
fetches for 108 hosts a week, and it is the shape Cloudflare produces whenever
it inserts its managed block above a site's own rules. The same parser also
took the FIRST matching rule rather than the longest, and could never be
bound by a group naming one of the fleet's `Mozilla/5.0 (compatible; ...)`
tokens. None of the 108 hosts measured on 2026-09-12 carried a split `*`
block, so no Iowa unit was mis-gated; the defect was latent here and live in
the reading of wyomingmi.gov.

Three readings the old module got wrong at the status level are also
different now, and each is printed rather than silent:
  * a robots.txt that answers 200 with an EMPTY body used to DISALLOW (it fell
    through to "unreachable"); RFC 9309 makes it allow-all, and it does now.
  * 401 and 403 are still allow-all, as RFC 9309 says and as this gate always
    read them, but the verdict now carries status `refused` so a caller can
    see it. The fleet had two readings of that status (the DuPage scraper
    fetches nothing on it) and a first draft of the shared module took the
    strict side for everyone; measured the same hour, that would have called
    every ArcGIS Online FeatureServer disallowed. The RFC reading stays the
    default; a website scraper opts into the strict one by argument.
  * the FINAL URL of a redirected robots.txt is kept on the verdict, so a
    county whose file is served by its CMS vendor (Revize, for Cherokee and
    Hamilton) can be seen to be.

The gate also exposes two readings the old one could not give and no Iowa
caller yet uses: gate.crawl_delay(url) and gate.content_signal(url). What a
caller does with them is policy (CLAUDE.md, the honesty rules).

THE 2026-09-06 MEASUREMENT STANDS AND IS KEPT HERE, because it is why any of
this exists. FOUR Iowa scrapers fetch other people's pages on a weekly schedule
under `districtry/1.0`, across 108 distinct hosts, of which FOUR say no:

  cityofpalo.com                 city-officials scrape
  johnson-county.granicus.com    minutes chair scrape
  www.cherokeecounty.iowa.gov    board-chair scrape (Revize CMS)
  www.hamiltoncounty.iowa.gov    board-chair scrape (Revize CMS)

All four are the same file: a handful of big-name crawlers allowed everything,
then `User-agent: * / Disallow: /` in the last two lines — a VENDOR DEFAULT on
the two county sites, served from cms7files.revize.com and cms2.revize.com,
which is the reason to keep asking per host rather than reasoning about who a
county is. Both files read as permissive for four hundred bytes and refuse in
the last two lines; do not read one by eye. The other 104: 49 serve no
robots.txt (404, allow all), 44 permit the paths read, 8 answer HTTP 202 (the
captcha shape, an access control, left alone), 3 were unreachable on the
measuring run and are treated as disallow.

A refused unit is SKIPPED with its reason printed and its page never
requested. It is NOT removed from the caller's table: the check runs every
week, so a host that changes its file re-enters by itself. What makes that
safe is the caller's own count floor — one unit leaving is ordinary, a
collapse is not.
"""
import os
import sys

_ROOT_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "scripts")
if _ROOT_SCRIPTS not in sys.path:
    sys.path.insert(0, _ROOT_SCRIPTS)

from robots_policy import RobotsGate  # noqa: E402,F401  (shared machinery — do not fork)

__all__ = ["RobotsGate"]
