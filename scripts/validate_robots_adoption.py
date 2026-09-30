#!/usr/bin/env python3
"""
A new scraper can ship today without ever reading robots.txt, with every gate
green. This is the gate that stops that.

WHY. CLAUDE.md's rule is that robots.txt is read before the first fetch of a
host, through `scripts/robots_policy.py`, with the same client that will crawl.
`scraper_common.require_robots_allowed` is the seam that enacts it. Adoption was
per caller and unmeasured, and every measurement of it has been an undercount
taken off a hand-written list: the 2026-09-12 sweep named seven files, #1271's
follow-on named four more, and the re-measurement of 2026-09-30 found the gap
two orders of magnitude wider than either. Nothing compared the tree against
the rule, so the only thing standing between a new unwired scraper and `main`
was somebody remembering.

WHAT IT MEASURES. Every tracked `*.py` file, split three ways:

  * it FETCHES if it calls a network entry point — `requests` or `httpx` at
    module or Session level, `urllib.request.urlopen`/`urlretrieve`, this
    fleet's own `scraper_common.fetch`/`fetch_stdlib`, or Playwright's
    `page.goto`. Read by AST, never by a text match, because a text match
    counts a docstring that merely NAMES one of those (this module would count
    itself twice over) and misses a call spelled across two lines.
  * it READS THE POLICY if it reaches `require_robots_allowed`, `RobotsGate` or
    `robots_deferred`. Also AST, for the same reason: `docs`-style prose about
    robots.txt is not a reading of it, and half a dozen builders write an
    `elections.il.gov` url into their output without ever requesting it — a
    CITATION IS NOT A FETCH, and by the same token a MENTION IS NOT A GATE.
  * otherwise it is neither and this gate says nothing about it.

A file that fetches and does not read the policy must be DECLARED, and the
declarations are re-audited every run in the `ACCEPTED_DROPS` shape this fleet
already uses for `EXPECTED_UNREACHABLE`, `ACCEPTED_SHORTFALLS` and
`ROBOTS_DECLINED`: an entry FAILS when it stops describing the tree — the file
gone, or no longer fetching, or now reading the policy — so the list can only
shrink and cannot rot into a permanent hole with nothing saying so.

TWO TABLES, BECAUSE THEY ARE TWO DIFFERENT CLAIMS.

  `UNWIRED_AT_SWEEP` is a BACKLOG. Its entries share one reason, stated once
  here rather than copied 200 times into strings that would all say the same
  thing: as of the sweep date below, nobody had wired these. It is seeded with
  exactly what the tree had that day, so this gate lands green and its only
  possible movement is downward. Removing a name from it is the unit of
  progress, and adding one is not available to a new scraper — a file that
  fetches, reads nothing and is not already listed FAILS.

  `DECLARED_EXEMPT` is for a file whose fetch genuinely must not be gated, each
  with its own reason and date. It is EMPTY on introduction, which is a
  measurement rather than an omission: the three candidates considered were the
  two `indexnow_submit.py` submitters and `scripts/mirror_*_tiles.py`, and all
  three are ordinary automatic clients fetching somebody else's host, so all
  three belong in the backlog and none is exempt. The one real class of
  unreadable policy already has a home in
  `scraper_common.ROBOTS_DEFERRED_HOSTS`, which is per HOST and records the
  measurement; a per-FILE exemption would hide the same fact where nobody
  measures it.

WHAT IT CANNOT SEE, stated rather than implied. It asks whether a file reaches
the seam, never whether it reaches it BEFORE its first fetch or for EVERY host
it touches. A scraper that gates one rung of a three-client ladder and fetches
on the other two passes here. That is a reading of control flow this does not
attempt, and it is why the seam raises rather than returning False.
"""

import ast
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SWEEP_DATE = "2026-09-30"

# Attribute names that open a connection, whatever the object they hang off.
NET_ATTRS_ANY = {"urlopen", "urlretrieve", "goto"}
# Attribute names that open a connection only on an HTTP client object.
NET_ATTRS_CLIENT = {"get", "post", "head", "put", "patch", "delete", "request",
                    "Session", "Client"}
# Module names whose attributes above are network calls.
CLIENT_MODULES = {"requests", "httpx"}
# Bare names that are network calls once imported from these modules.
IMPORTABLE_NET = {
    "urllib.request": {"urlopen", "urlretrieve"},
    "requests": NET_ATTRS_CLIENT,
    "httpx": NET_ATTRS_CLIENT,
    "scraper_common": {"fetch", "fetch_stdlib"},
}
ROBOTS_NAMES = {"require_robots_allowed", "require_robots_once", "RobotsGate",
                "robots_deferred"}
# Modules whose job IS the policy, so anything imported from one and called is a
# reading. `robots_gate` is the per-instance shim validate_workflow_deps allows.
ROBOTS_MODULES = {"robots_policy", "robots_gate", "scraper_common"}
# Entry points those modules expose. CORRECTED 2026-09-30, hours after the sweep:
# the first version knew only the four names above, and SEVEN files that read the
# policy through `robots_policy.classify` or `fetch_verdict` were therefore
# recorded as unwired -- an overcount, so the published figure overstated the
# problem. A detector that knows only some of a module's doors reports the rest of
# the building as unlocked.
ROBOTS_ENTRY = ROBOTS_NAMES | {"classify", "fetch_verdict", "RobotsPolicy",
                               "Verdict", "HostPacer"}


def _root_name(node):
    """The leftmost Name of an attribute chain, or None."""
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


class _Reader(ast.NodeVisitor):
    def __init__(self):
        self.net_names = set()      # bare names bound to a network entry point
        self.client_objs = set()    # names holding a requests/httpx client
        self.fetches = []
        self.robots = []
        self.robots_names = set(ROBOTS_NAMES)  # bare names bound to a reading
        self.robots_mods = set(ROBOTS_MODULES)  # local names of a policy module

    def visit_Import(self, node):
        # `import robots_policy as rp` — two files read the policy that way, and
        # the first version of this reader knew only the `from ... import` shape,
        # so both were recorded as unwired.
        for alias in node.names:
            if alias.name in ROBOTS_MODULES:
                self.robots_mods.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        mod = node.module or ""
        wanted = IMPORTABLE_NET.get(mod, set())
        for alias in node.names:
            local = alias.asname or alias.name
            if alias.name in wanted:
                self.net_names.add(local)
            if mod in ROBOTS_MODULES and alias.name in ROBOTS_ENTRY:
                self.robots_names.add(local)  # importing is not calling; see visit_Call
        self.generic_visit(node)

    def visit_Assign(self, node):
        val = node.value
        if isinstance(val, ast.Call):
            attr = getattr(val.func, "attr", None)
            root = _root_name(val.func) if isinstance(val.func, ast.Attribute) else None
            if attr in {"Session", "Client"} and root in CLIENT_MODULES:
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name):
                        self.client_objs.add(tgt.id)
        self.generic_visit(node)

    def visit_Call(self, node):
        f = node.func
        if isinstance(f, ast.Name):
            if f.id in self.net_names:
                self.fetches.append((f.id, node.lineno))
            if f.id in self.robots_names:
                self.robots.append((f.id, node.lineno))
        elif isinstance(f, ast.Attribute):
            root = _root_name(f)
            if f.attr in NET_ATTRS_ANY:
                self.fetches.append((f.attr, node.lineno))
            elif f.attr in NET_ATTRS_CLIENT and (root in CLIENT_MODULES
                                                 or root in self.client_objs):
                self.fetches.append(("%s.%s" % (root, f.attr), node.lineno))
            elif (root == "scraper_common"
                  and f.attr in IMPORTABLE_NET["scraper_common"]):
                self.fetches.append(("%s.%s" % (root, f.attr), node.lineno))
            elif f.attr in ROBOTS_ENTRY or f.attr in {"allows"}:
                if root in self.robots_mods or f.attr in ROBOTS_NAMES:
                    self.robots.append((f.attr, node.lineno))
        self.generic_visit(node)


def classify(path):
    """(fetches, reads_policy) for one file; a syntax error is a hard failure."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    tree = ast.parse(src, filename=path)
    r = _Reader()
    r.visit(tree)
    # A name used as a decorator or bare reference also counts as reaching the
    # seam: `gate = require_robots_allowed` then `gate(...)` is one indirection
    # this does not follow, so the reference itself is taken as the reading.
    if not r.robots:
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in ROBOTS_NAMES:
                r.robots.append((node.id, node.lineno))
                break
    return bool(r.fetches), bool(r.robots)


def tracked_python():
    out = subprocess.run(["git", "-C", REPO, "ls-files", "*.py"],
                         capture_output=True, text=True, check=True).stdout
    return sorted(out.split())


# ---------------------------------------------------------------------------
# Every file that fetched without reading the policy on the sweep date. One
# shared reason, stated in this module's docstring: nobody had wired it yet.
# The list can only shrink; the gate FAILS on an entry that no longer describes
# the tree, and on a fetching file that is not here and reads nothing.
# ---------------------------------------------------------------------------
UNWIRED_AT_SWEEP = frozenset("""
    ca/scripts/build_ca_legislature_roster.py
    ca/scripts/build_sf_supervisor_roster.py
    ca/scripts/indexnow_submit.py
    ca/scripts/validate_sources.py
    ia/scripts/build_ia_community_colleges.py
    ia/scripts/build_ia_gap_outlines.py
    ia/scripts/build_ia_judicial_district.py
    ia/scripts/build_ia_legislature_roster.py
    ia/scripts/build_ia_precincts.py
    ia/scripts/build_ia_school_sites.py
    ia/scripts/cedar_rapids_council_scraper.py
    ia/scripts/dsm_council_scraper.py
    ia/scripts/ia_county_directory_scraper.py
    ia/scripts/ia_legislature_scraper.py
    ia/scripts/waterloo_council_scraper.py
    in/scripts/validate_sources.py
    mi/scripts/build_mi_gap_outlines.py
    mi/scripts/build_mi_legislature_roster.py
    mi/scripts/build_mi_precincts.py
    mi/scripts/mi_detroit_council_scraper.py
    mi/scripts/mi_grand_rapids_council_scraper.py
    mi/scripts/mi_senate_scraper.py
    mi/scripts/validate_sources.py
    nc/scripts/build_nc_legislature_roster.py
    nc/scripts/validate_sources.py
    ny/scripts/build_tompkins_legislature.py
    ny/scripts/cec_scraper.py
    ny/scripts/indexnow_submit.py
    ny/scripts/ny_legislature_scraper.py
    ny/scripts/nypd_precinct_scraper.py
    ny/scripts/validate_sources.py
    scripts/adams_county_board_scraper.py
    scripts/aia_bundle.py
    scripts/bing_fetch.py
    scripts/boone_district_officials_scraper.py
    scripts/boone_municipal_officials_scraper.py
    scripts/build_block_population.py
    scripts/build_carroll_precinct_polling.py
    scripts/build_county_clerk_roster.py
    scripts/build_county_outline.py
    scripts/build_district_search.py
    scripts/build_hamilton_precinct_polling.py
    scripts/build_henry_precinct_polling.py
    scripts/build_jodaviess_board_districts.py
    scripts/build_knox_board_districts.py
    scripts/build_lasalle_board_districts.py
    scripts/build_logan_park_districts.py
    scripts/build_logan_precinct_polling.py
    scripts/build_macon_board_district_labels.py
    scripts/build_municipal_ward_coverage.py
    scripts/build_parcel_fabric_districts.py
    scripts/build_statewide_library_districts.py
    scripts/build_stclair_precinct_polling.py
    scripts/build_stephenson_fire_districts.py
    scripts/build_stephenson_precincts.py
    scripts/build_vermilion_boundaries.py
    scripts/build_winnebago_county_board_roster.py
    scripts/carroll_municipal_officials_scraper.py
    scripts/cass_municipal_officials_scraper.py
    scripts/ccbr_scraper.py
    scripts/ccpsa_scraper.py
    scripts/check_engine_parity.py
    scripts/check_roster_workflow_health.py
    scripts/clay_county_board_scraper.py
    scripts/coles_county_board_scraper.py
    scripts/comptroller_afr.py
    scripts/cook_municipal_officials_scraper.py
    scripts/cpd_district_scraper.py
    scripts/dekalb_county_board_scraper.py
    scripts/dekalb_municipal_officials_scraper.py
    scripts/douglas_county_board_scraper.py
    scripts/dupage_county_board_scraper.py
    scripts/edgar_county_board_scraper.py
    scripts/fleet_status.py
    scripts/franklin_county_board_scraper.py
    scripts/fulton_county_board_scraper.py
    scripts/generate_metro_files.py
    scripts/goatcounter_fetch.py
    scripts/gsc_fetch.py
    scripts/henry_county_board_scraper.py
    scripts/henry_municipal_officials_scraper.py
    scripts/il_county_commissioners_scraper.py
    scripts/il_library_contacts_scraper.py
    scripts/il_special_district_officials_scraper.py
    scripts/indexnow_submit.py
    scripts/jackson_county_board_scraper.py
    scripts/jodaviess_county_board_scraper.py
    scripts/kane_county_board_scraper.py
    scripts/kane_municipal_officials_scraper.py
    scripts/kankakee_district_officials_scraper.py
    scripts/kankakee_municipal_officials_scraper.py
    scripts/lake_county_board_roles_scraper.py
    scripts/lake_municipal_officials_scraper.py
    scripts/lasalle_municipal_officials_scraper.py
    scripts/macoupin_municipal_officials_scraper.py
    scripts/marshall_county_board_scraper.py
    scripts/mcdonough_county_board_scraper.py
    scripts/peoria_county_board_scraper.py
    scripts/peoria_municipal_officials_scraper.py
    scripts/plano_council_scraper.py
    scripts/probe_incomplete_tls_chains.py
    scripts/richland_county_board_scraper.py
    scripts/sangamon_county_board_scraper.py
    scripts/selftest_scraper_common.py
    scripts/shelby_county_board_scraper.py
    scripts/skokie_trustee_districts_scraper.py
    scripts/stark_county_board_scraper.py
    scripts/tazewell_county_board_scraper.py
    scripts/verify_google_api_access.py
    scripts/vermilion_county_board_scraper.py
    scripts/vtd_board_districts.py
    scripts/warren_county_board_scraper.py
    scripts/wayne_county_board_scraper.py
    scripts/whiteside_municipal_officials_scraper.py
    scripts/will_city_councils_scraper.py
    scripts/will_county_board_scraper.py
    scripts/will_municipal_officials_scraper.py
    scripts/winnebago_municipal_officials_scraper.py
    scripts/woodford_county_board_scraper.py
    wi/scripts/build_rusd_school_board_districts.py
    wi/scripts/build_wi_county_board_directory.py
    wi/scripts/build_wi_legislature_roster.py
    wi/scripts/build_wi_libraries.py
    wi/scripts/build_wi_municipal_clerks.py
    wi/scripts/build_wi_school_sites.py
    wi/scripts/rusd_school_board_scraper.py
    wi/scripts/validate_sources.py
    wi/scripts/verify_kenosha_supervisory_map.py
    wi/scripts/wi_alderperson_scraper.py
    wi/scripts/wi_bluebook_municipal_scraper.py
    wi/scripts/wi_circuit_judges_scraper.py
    wi/scripts/wi_coa_scraper.py
    wi/scripts/wi_coa_staleness.py
    wi/scripts/wi_county_clerk_scraper.py
    wi/scripts/wi_county_officer_contact_scraper.py
    wi/scripts/wi_wec_probe.py
    wi/scripts/wi_wec_recon.py
""".split())

# path -> (reason, date). EMPTY on introduction, deliberately; see the docstring.
DECLARED_EXEMPT = {}


def main(argv):
    if "--selftest" in argv:
        return _selftest()

    files = tracked_python()
    fetchers, unwired = [], []
    for rel in files:
        full = os.path.join(REPO, rel)
        if not os.path.exists(full):
            continue
        fetches, reads = classify(full)
        if not fetches:
            continue
        fetchers.append(rel)
        if not reads:
            unwired.append(rel)

    problems = []

    undeclared = [p for p in unwired
                  if p not in UNWIRED_AT_SWEEP and p not in DECLARED_EXEMPT]
    for p in undeclared:
        problems.append("%s fetches over HTTP and never reads robots.txt. Reach "
                        "scraper_common.require_robots_allowed() before its "
                        "first fetch, with the same client that will crawl."
                        % p)

    on_disk = set(files)
    wired_now = set(fetchers) - set(unwired)
    for p in sorted(UNWIRED_AT_SWEEP):
        if p not in on_disk:
            problems.append("%s is in UNWIRED_AT_SWEEP and is not in the tree — "
                            "remove the entry." % p)
        elif p in wired_now:
            problems.append("%s now reads robots.txt — remove it from "
                            "UNWIRED_AT_SWEEP, which is how this list shrinks."
                            % p)
        elif p not in set(fetchers):
            problems.append("%s is in UNWIRED_AT_SWEEP and no longer fetches "
                            "over HTTP — remove the entry." % p)
    for p in sorted(DECLARED_EXEMPT):
        if p not in on_disk:
            problems.append("%s is in DECLARED_EXEMPT and is not in the tree — "
                            "remove the entry." % p)
        elif p not in set(fetchers):
            problems.append("%s is in DECLARED_EXEMPT and no longer fetches — "
                            "remove the entry." % p)
        elif p in wired_now:
            problems.append("%s is in DECLARED_EXEMPT and now reads robots.txt "
                            "— remove the entry." % p)

    if problems:
        print("validate-robots-adoption: FAIL\n    %s"
              % "\n    ".join(problems), file=sys.stderr)
        return 1

    print("validate-robots-adoption: OK — %d of %d fetching script(s) read "
          "robots.txt before crawling; %d recorded as not yet wired (swept %s), "
          "%d declared exempt"
          % (len(fetchers) - len(unwired), len(fetchers),
             len(UNWIRED_AT_SWEEP), SWEEP_DATE, len(DECLARED_EXEMPT)))
    return 0


def _selftest():
    import tempfile
    cases = [
        ("import requests\nrequests.get(u)\n", True, False),
        ("import requests\ns = requests.Session()\ns.get(u)\n", True, False),
        ("from urllib.request import urlopen\nurlopen(u)\n", True, False),
        ("import urllib.request\nurllib.request.urlopen(u)\n", True, False),
        ("from scraper_common import fetch\nfetch(u, h)\n", True, False),
        ("from scraper_common import fetch_stdlib\nfetch_stdlib(u)\n", True, False),
        ("page.goto(u)\n", True, False),
        # a mention is not a gate
        ('"""reads robots.txt and require_robots_allowed"""\n'
         "import requests\nrequests.get(u)\n", True, False),
        # the real thing, both spellings
        ("import requests\nfrom scraper_common import require_robots_allowed\n"
         "require_robots_allowed(u, ua)\nrequests.get(u)\n", True, True),
        ("import requests\nfrom robots_policy import RobotsGate\n"
         "RobotsGate(None, ua).allows(u)\nrequests.get(u)\n", True, True),
        ("import scraper_common\n"
         "scraper_common.robots_deferred(u)\nscraper_common.fetch(u, h)\n",
         True, True),
        # A POLICY MODULE HAS MORE THAN ONE DOOR. These four shapes were all
        # read as unwired by the first version of this reader, and the seven
        # files that use them were published as part of the problem. Each is a
        # real spelling taken from the tree.
        ("import requests\nimport robots_policy as rp\n"
         "rp.fetch_verdict(r, ua)\nrequests.get(u)\n", True, True),
        ("import requests\nimport robots_policy as rp\n"
         "rp.classify(200, body)\nrequests.get(u)\n", True, True),
        ("import requests\nfrom robots_policy import classify\n"
         "classify(200, body)\nrequests.get(u)\n", True, True),
        ("import requests\nfrom robots_gate import RobotsGate, HostPacer\n"
         "RobotsGate(s, ua).allows(u)\nrequests.get(u)\n", True, True),
        ("import requests\nfrom scraper_common import require_robots_once\n"
         "require_robots_once(u, ua)\nrequests.get(u)\n", True, True),
        # An unrelated module's `classify` is not a policy reading: this repo has
        # `dropped_rings.classify`, so the name alone must not count.
        ("import requests\nfrom dropped_rings import classify\n"
         "classify(x)\nrequests.get(u)\n", True, False),
        # neither
        ("import json\njson.load(open('x'))\n", False, False),
        # a citation is not a fetch
        ('URL = "https://elections.il.gov/x"\n', False, False),
    ]
    bad = []
    for i, (src, want_fetch, want_robots) in enumerate(cases):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
            fh.write(src)
            name = fh.name
        try:
            got = classify(name)
        finally:
            os.unlink(name)
        if got != (want_fetch, want_robots):
            bad.append("case %d: wanted %s, got %s for %r"
                       % (i, (want_fetch, want_robots), got, src))
    if bad:
        print("validate-robots-adoption --selftest: FAIL\n    %s"
              % "\n    ".join(bad), file=sys.stderr)
        return 1
    print("validate-robots-adoption --selftest: OK — %d detector case(s), "
          "including a docstring that names the seam without reaching it, "
          "five spellings of a policy module's own doors, and an unrelated "
          "module's classify() that is not one"
          % len(cases))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
