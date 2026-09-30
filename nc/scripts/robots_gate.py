#!/usr/bin/env python3
"""Ask a host's robots.txt before fetching it, for this instance's scrapers.

A SHIM, exactly like ia/scripts/robots_gate.py. The reading lives in
scripts/robots_policy.py, one copy for the fleet, and this file exists so this
instance's callers get that reader without a sys.path reach written into every
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

MEASURED FOR NORTH CAROLINA, 2026-09-29. www.ncleg.gov — the only host this
instance's scrapers read — serves a 73-byte robots.txt disallowing /WHPTest/
and /Ethics/ under a single `*` group, with `Crawl-delay: 2`. So /Members/ is
allowed and the pace is honoured through HostPacer.

THAT FILE BEGINS WITH A BYTE-ORDER MARK, which is the exact shape that made
this project read the Illinois State Board of Elections' `Disallow: /` as a
permission for over a year: `\ufeff` is not whitespace to str.lstrip(), so a
parser sees a field named `\ufeffuser-agent`, opens no group and answers "no
group binds this client" for every path. robots_policy._parse strips it, with
ISBE's own bytes as a selftest fixture — which is why this host reads
correctly here and would not have before 2026-09-25.
"""
import os
import sys

_ROOT_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "scripts")
if _ROOT_SCRIPTS not in sys.path:
    sys.path.insert(0, _ROOT_SCRIPTS)

from robots_policy import RobotsGate, HostPacer  # noqa: E402,F401  (shared machinery — do not fork)

__all__ = ["RobotsGate", "HostPacer"]
