#!/usr/bin/env python3
"""Ask a host's robots.txt before fetching it, for this instance's scrapers.

A SHIM, exactly like ia/scripts/robots_gate.py. The reading lives in
scripts/robots_policy.py, one copy for the fleet, and this file exists so
Michigan's callers get that reader without a sys.path reach written into every
scraper:

    from robots_gate import RobotsGate, HostPacer
    gate = RobotsGate(session, USER_AGENT)
    ok, why = gate.allows(url)

scripts/validate_workflow_deps.py lists `robots_policy` in FLEET_SHARED, so a
workflow that installs `requests` satisfies this import chain.

WHY NOT WRITE THE READING HERE. Python's own urllib.robotparser keeps only the
FIRST `User-agent: *` group of a file and takes the first matching rule rather
than the longest. Cloudflare inserts a managed `*` block above a site's own
rules on any host it fronts, so that parser reads the managed block and drops
whatever the site itself said. One reader, tested once (robots_policy.py's
--selftest), is the whole point.

MEASURED FOR MICHIGAN, 2026-09-13. The tranche-1 sweep read robots.txt for
every candidate county host before any page fetch; the outcomes are recorded
per county in mi_commissioner_scraper.py's PROBES table, including the four
that refuse. Two of them refuse in their file (`Disallow: /` under a single `*`
group) and two answer HTTP 202 on robots.txt itself, which is a challenge and
not a document.
"""
import os
import sys

_ROOT_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "scripts")
if _ROOT_SCRIPTS not in sys.path:
    sys.path.insert(0, _ROOT_SCRIPTS)

from robots_policy import RobotsGate, HostPacer  # noqa: E402,F401  (shared machinery — do not fork)

__all__ = ["RobotsGate", "HostPacer"]
