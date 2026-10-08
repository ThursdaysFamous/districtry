#!/usr/bin/env python3
"""
Source freshness gate for the app's data layers.

Why this exists: unlike the roster scrapers (which re-pull the same page every
week), several layers point at a *specific* upstream dataset that the publisher
silently supersedes with a new one:

  * Socrata portal datasets can be versioned by year. The reference fork's CPS
    attendance-boundary layers, for example, are published fresh every school
    year under a BRAND NEW dataset id (…SY2526 → …SY2627), so the id hardcoded
    in index.html keeps returning last year's boundaries long after a newer one
    exists. Nothing errors; the data just quietly goes stale.
  * Pre-built boundary layers (in this instance: the TIGERweb-derived district
    files) were downloaded at build time. The check there is provenance: is
    the source we cite still reachable, and a reminder to re-verify after
    each redistricting cycle.

This script does NOT edit index.html or any data file — swapping a dataset id
is a judgement call (the "newer" dataset may have a different schema), so, like
the roster workflows, it surfaces drift for a human instead of auto-applying it.

What it checks (findings carry a severity — FAIL, WARN, or OK):
  1. Manifest ↔ app coherence: every dataset id / data file the manifest knows
     about is still referenced in index.html (guards this file drifting from the
     app it validates).                                                   [FAIL]
  2. Socrata datasets: each id still resolves and still carries the stable part
     of its expected name (a rename usually means it was replaced).       [FAIL]
     For year-versioned datasets, the portal catalog is searched for a newer
     edition than the one in use.                                         [WARN]
  3. Shapefile provenance: the cited source URL is reachable and the built
     data/app file is present.                             [WARN / FAIL if gone]
  4. Live service endpoints (Census TIGERweb): reachable.                  [WARN]

Crawl-delay: this file probes TWO pages on www.iowacourts.gov, which states
`Crawl-delay: 30` in a group that binds every token this project sends, and
one PDF on www.issda.org, which states 10. Measured 2026-09-12, it honoured
neither — the two iowacourts.gov probes went out back to back. They are now
paced by scripts/robots_policy.py's HostPacer, the same object the six-worker
board-chair scrape uses, and the hosts it held are printed to stderr at the
end of the run so an honoured delay can be told from an ignored one. A single
request to a host is never paced by anything, so issda.org's 10 seconds cost
this run nothing; the pacer is there for the day a second issda.org URL is
added.

WHAT THIS FILE STILL DOES NOT DO, stated rather than left to be assumed: it
reads robots.txt for the DELAY and does not act on the file's allow/disallow.
That is deliberate for now and not an oversight. RFC 9309 makes an UNREACHABLE
robots.txt disallow-all, and this script's whole question is "is this source
still there" — a transient robots.txt outage would turn into a source-freshness
finding about the wrong thing, so declining a probe needs its own decision
about how that is reported (scripts/validate_card_links.py's ROBOTS_DECLINED is
the shape). CLAUDE.md already records the fleet-level follow-up: several
scrapers fetch without asking, and that is the next thing to fix.

Exit status: 0 when nothing needs a human (OK or WARN only), 1 on any FAIL.
Newer-edition detection is deliberately WARN, not FAIL — the current dataset
still works and a person decides whether/when to migrate. The scheduled
workflow (.github/workflows/ky-validate-sources.yml, monthly) opens an issue on WARN or
FAIL so drift is never silent, without turning the build red.

Usage:
    python3 ky/scripts/validate_sources.py                 # human-readable report
    python3 ky/scripts/validate_sources.py --report r.md   # also write markdown
    python3 ky/scripts/validate_sources.py --status-file s.txt   # ok|warn|fail
    python3 ky/scripts/validate_sources.py --offline       # manifest↔app checks only
"""

import argparse
import json
import os
import re
import sys

try:
    import requests
except ImportError:  # pragma: no cover - requests is pinned in requirements.txt
    requests = None

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # sibling, not a package
from robots_gate import RobotsGate, HostPacer  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.path.join(REPO_ROOT, "index.html")
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")

HTTP_TIMEOUT = 25
# The gate must ask a host's robots.txt about the token the fetch actually
# sends, so there is one literal and both read it.
USER_AGENT = "districtry source validator (+https://districtry.com/ky/)"

# The freshness gate's source manifest for the Iowa instance. Every layer this
# instance adds gets its rows here in the same change (CLAUDE.md's
# conventions; the reference repo's validate_sources.py shows a mature
# manifest's full shape, including year-search patterns and the `blocked`
# inversion).
SOCRATA_DOMAIN = "data.invalid"  # this fork's Socrata portal, if it adopts one
CATALOG_API = "https://api.us.socrata.com/api/catalog/v1"

# Socrata dataset ids the app hardcodes (none in the starter set).
SOCRATA = []

# Same-origin data/app files and the upstream source each was built from.
PROVENANCE = [
    {
        "layer": "county",
        "app_file": "state-counties.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1",
        "note": (
            "Kentucky's 120 counties pre-built from TIGERweb by "
            "ky/scripts/build_state_counties.py. The same file is dissolved into "
            "metro-outline.json for the coverage wash, so a change here moves "
            "both. THE FABRIC FOLLOWS THE OHIO RIVER'S NORTH BANK, so the river "
            "is inside Kentucky rather than outside it, which is why this "
            "instance's negative point is on land in Tennessee rather than on "
            "water at the northern border."
        ),
    },
    {
        "layer": "county",
        "app_file": "metro-outline.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1",
        "note": (
            "The whole-state outline the coverage wash paints, dissolved from "
            "the county fabric by ky/scripts/build_metro_outline.py. Its anchor "
            "registry is checked offline on every build and every --check. IT IS "
            "A MULTIPOLYGON: the Kentucky Bend, the piece of Fulton County the "
            "Mississippi loops around, is a second outer ring and carries an "
            "anchor of its own because Fulton's is on the mainland."
        ),
    },
    {
        "layer": "us-house",
        "app_file": "congress-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/0",
        "note": (
            "Kentucky's 6 congressional districts, pre-built from TIGERweb's "
            "120th-Congress layer (field CD120) by "
            "ky/scripts/build_legislative_boundaries.py. That builder takes no "
            "per-chamber argument: all three chambers are simplified in ONE "
            "mapshaper combine-files topology, because a shared edge only "
            "survives identically if both sides came off one run."
        ),
    },
    {
        "layer": "us-house",
        "app_file": "congress-roster.json",
        "source_url": "https://unitedstates.github.io/congress-legislators/legislators-current.json",
        "note": (
            "Delegation roster from the public-domain congress-legislators "
            "project; refreshed weekly by update-ky-congress-roster.yml as a "
            "reviewed pull request. It is the only roster this instance ships."
        ),
    },
    {
        "layer": "ky-senate",
        "app_file": "ky-senate-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/1",
        "note": (
            "38 state senate districts from TIGERweb's SLDU layer, built in the "
            "same combine-files run as the House and Congress. NO ROSTER SHIPS: "
            "the card names the district and links the General Assembly's own "
            "member directory, recorded as gap ky-legislature-roster."
        ),
    },
    {
        "layer": "ky-house",
        "app_file": "ky-house-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/2",
        "note": (
            "100 state house districts from TIGERweb's SLDL layer. KENTUCKY'S "
            "CHAMBERS DO NOT NEST, so the builder has no nesting gate; what it "
            "holds exactly instead is that all three layers draw the same state "
            "border, edge for edge, which its --check re-runs offline in CI."
        ),
    },
    {
        "layer": "ky-supreme-court",
        "app_file": "ky-judge-roster.json",
        "source_url": "https://www.kycourts.gov/Courts/County-Information/Pages/Adair.aspx",
        "note": (
            "Kentucky's judges for all four courts, keyed by the numbered "
            "district or circuit the Court of Justice itself prints beside each "
            "one — the join Ask ky-judge-district-join asked for and got on "
            "2026-10-01. The two appellate tiers come from the Supreme Court's "
            "and the Court of Appeals' own statewide pages; the two trial tiers "
            "are assembled from the 120 county pages, of which this url is the "
            "first, because neither trial tier has a statewide page. Refreshed "
            "weekly by update-ky-judges-roster.yml as a reviewed pull request. "
            "Jefferson's county page leaves its judges out, and it is the sole "
            "county of circuit 30 and district 30, so those two units are read "
            "from the Jefferson Circuit, Family and District Courts' own sites, "
            "which that page links (2026-10-07). The directory search the same reply named, "
            "kcoj.kycourts.net, is NOT read — its robots.txt refuses every "
            "client, and that refusal is obeyed rather than worked around."
        ),
    },
]

ENDPOINTS = [
    # Every layer this instance ships draws from a same-origin file, so these
    # rows are about the REBUILD rather than about a runtime fetch: the four
    # TIGERweb layers the builders read. Each is the app's own enveloped query
    # shape with a count floor, not a metadata probe -- Iowa's #718 is the
    # measurement behind that choice, where a reachable /11?f=json passed for
    # weeks while the query the app actually sent answered HTTP 200 with an
    # Esri error envelope and no features.
    #
    # THE LAYER INDICES ARE THE BUILDER'S, NOT GUESSED: TIGERweb's Legislative
    # MapServer is 0 US House, 1 upper chamber, 2 lower chamber (LAYERS in
    # ky/scripts/build_legislative_boundaries.py). A first draft of this file
    # in the Minnesota instance it was ported from wrote 2 and 4 for the two
    # state chambers, and the count floors are what caught it -- layer 2
    # answered the HOUSE's count under the heading for the Senate, and layer 4
    # answered Congress's. A reachability probe would have called all four rows
    # OK. Kentucky's count floors are 6, 38 and 100, which are all different
    # numbers, so the same mistake would fail here too.
    {
        "layer": "county",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "State_County/MapServer/1/query?where=STATE%3D%2721%27"
                "&returnCountOnly=true&f=json"),
        "min_count": 120,  # Kentucky's county count is fixed by statute
    },
    {
        "layer": "us-house",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "Legislative/MapServer/0/query?where=STATE%3D%2721%27"
                "&returnCountOnly=true&f=json"),
        "min_count": 6,
    },
    {
        "layer": "ky-senate",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "Legislative/MapServer/1/query?where=STATE%3D%2721%27"
                "&returnCountOnly=true&f=json"),
        "min_count": 38,
    },
    {
        "layer": "ky-house",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "Legislative/MapServer/2/query?where=STATE%3D%2721%27"
                "&returnCountOnly=true&f=json"),
        "min_count": 100,
    },
]

FAIL, WARN, OK = "FAIL", "WARN", "OK"


class Findings(object):
    """Collects (severity, layer, message) rows and tracks the worst seen."""

    def __init__(self):
        self.rows = []

    def add(self, severity, layer, message):
        self.rows.append((severity, layer, message))

    def status(self):
        if any(s == FAIL for s, _, _ in self.rows):
            return "fail"
        if any(s == WARN for s, _, _ in self.rows):
            return "warn"
        return "ok"


PACER = None


def pacer():
    """The run's one HostPacer, built on first use.

    Lazy because --offline never fetches anything and should not open a
    session or read anybody's robots.txt to say so.
    """
    global PACER
    if PACER is None:
        PACER = HostPacer(RobotsGate(requests.Session(), USER_AGENT,
                                     timeout=HTTP_TIMEOUT))
    return PACER


def http_get(url, want_json=True, params=None):
    """GET with a sane UA; returns (ok, payload_or_error). Never raises."""
    if requests is None:
        return False, "requests not installed"
    try:
        with pacer().hold(url):
            resp = requests.get(
                url,
                params=params,
                timeout=HTTP_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
            )
    except Exception as e:  # network/TLS/proxy errors are a finding, not a crash
        return False, "request failed: %s" % e
    if resp.status_code >= 400:
        return False, "HTTP %d" % resp.status_code
    # 202 is never a real document. "Accepted" means the request was taken for
    # later processing, and the bot-management fronts in front of several
    # government sites use it for their interstitial. Treat it as unreachable
    # and say why, so the two signals agree.
    if resp.status_code == 202:
        return False, "HTTP 202 — bot-management interstitial, not the document"
    if not want_json:
        return True, resp
    try:
        return True, resp.json()
    except ValueError as e:
        return False, "non-JSON response: %s" % e


# ---- check 1: the manifest still matches what index.html actually uses -------
def check_manifest_matches_app(html, findings):
    for d in SOCRATA:
        if d["id"] not in html:
            findings.add(FAIL, d["layer"],
                         "dataset id %s not found in index.html — manifest is "
                         "out of sync with the app (update ky/scripts/validate_sources.py)"
                         % d["id"])
    for p in PROVENANCE:
        # A file the app addresses by a slug built at RUNTIME has no literal to
        # find — the same `dynamic_reference` exemption validate_index.py
        # grants. The entry names the suffix instead, and the drift check
        # looks for THAT: a card that stopped fetching the family at all
        # still fails here. (No such entries yet in this instance.)
        needle = p.get("app_file_pattern") or ("data/app/" + p["app_file"])
        if needle not in html:
            findings.add(FAIL, p["layer"],
                         "index.html no longer references %s — manifest drift"
                         % needle)


# ---- check 2: Socrata datasets resolve, keep their name, aren't superseded ---
def newest_edition(cfg):
    """Search the portal catalog for the newest edition matching cfg.

    Returns (id, name, year_int) for the highest `pattern` capture, or None if
    the search is unavailable / finds nothing usable.
    """
    ys = cfg["year_search"]
    ok, payload = http_get(CATALOG_API, params={
        "domains": SOCRATA_DOMAIN,
        "q": ys["query"],
        "only": "dataset,map,geospatial",
        "limit": 200,
    })
    if not ok or not isinstance(payload, dict):
        return None
    rx = re.compile(ys["pattern"])
    best = None
    for r in payload.get("results", []):
        res = r.get("resource", {})
        name = res.get("name", "")
        if cfg["name_contains"] not in name:
            continue
        m = rx.search(name)
        if not m:
            continue
        year = int(m.group(1))
        if best is None or year > best[2]:
            best = (res.get("id"), name, year)
    return best


def check_socrata(findings, offline):
    for cfg in SOCRATA:
        layer = cfg["layer"]
        if offline:
            continue
        ok, meta = http_get("https://%s/api/views/%s.json" % (SOCRATA_DOMAIN, cfg["id"]))
        if not ok:
            findings.add(FAIL, layer,
                         "dataset %s does not resolve on the portal (%s) — likely "
                         "retired or replaced" % (cfg["id"], meta))
            continue
        name = meta.get("name", "") if isinstance(meta, dict) else ""
        if cfg["name_contains"] not in name:
            findings.add(FAIL, layer,
                         "dataset %s is now named %r — expected it to contain %r; "
                         "the id may have been repurposed"
                         % (cfg["id"], name, cfg["name_contains"]))
            continue

        if "year_search" not in cfg:
            findings.add(OK, layer, "%s — %r" % (cfg["id"], name))
            continue

        # year-versioned: is a newer edition published?
        cur = re.search(cfg["year_search"]["pattern"], name)
        cur_year = int(cur.group(1)) if cur else None
        newest = newest_edition(cfg)
        if newest is None or cur_year is None:
            findings.add(OK, layer,
                         "%s — %r (newer-edition search unavailable)" % (cfg["id"], name))
        elif newest[2] > cur_year and newest[0] != cfg["id"]:
            findings.add(WARN, layer,
                         "in use: %s (%r). NEWER edition on the portal: %s (%r). "
                         "Review the newer dataset's schema, then update the id in index.html."
                         % (cfg["id"], name, newest[0], newest[1]))
        else:
            findings.add(OK, layer, "%s — %r (newest edition)" % (cfg["id"], name))


# ---- check 3: shapefile provenance reachable, built file present ------------
def check_provenance(findings, offline):
    for p in PROVENANCE:
        layer = p["layer"]
        fpath = os.path.join(APP_DATA_DIR, p["app_file"])
        if not os.path.exists(fpath):
            findings.add(FAIL, layer, "built data file data/app/%s is missing" % p["app_file"])
        if offline:
            continue
        ok, res = http_get(p["source_url"], want_json=False)
        blocked = p.get("blocked")
        if ok and blocked:
            # The block LIFTING is the news — see il/scripts/validate_sources.py
            # for the fuller rationale (the fleet-wide `blocked` inversion).
            findings.add(WARN, layer,
                         "source is REACHABLE again (%s) — its recorded block appears to "
                         "have LIFTED. Re-test the scraper; if it works, drop the "
                         "`blocked` flag on this entry so a future outage warns again. "
                         "Recorded block: %s" % (p["source_url"], blocked))
        elif ok:
            findings.add(OK, layer, "source reachable: %s — %s" % (p["source_url"], p["note"]))
        elif blocked:
            findings.add(OK, layer,
                         "unreachable AS EXPECTED (%s) — %s. %s"
                         % (res, blocked, p["source_url"]))
        else:
            findings.add(WARN, layer,
                         "source not reachable (%s): %s. Boundaries change ~once a "
                         "decade; verify the source still exists and re-download if redrawn. %s"
                         % (res, p["source_url"], p["note"]))


# ---- check 4: live endpoints reachable --------------------------------------
def check_endpoints(findings, offline):
    if offline:
        return
    for e in ENDPOINTS:
        # An entry carrying `min_count` is checked for CONTENT, not just
        # reachability, and the difference is the whole point of the flag.
        # HTTP STATUS CANNOT SEE AN ESRI ERROR ENVELOPE: a malformed query
        # answers 200 with {"error": {"code": 400}} and no rows, which every
        # status-based check reads as healthy. That is exactly how ia/ shipped
        # a dead ZIP overlay for weeks (#718) while its own source validator
        # reported the layer reachable — the endpoint it probed was the layer's
        # METADATA, which was reachable and always would be. A count query with
        # a floor is the smallest check that could actually have caught it.
        want_json = "min_count" in e
        ok, res = http_get(e["url"], want_json=want_json)
        if not ok:
            findings.add(WARN, e["layer"],
                         "endpoint not reachable (%s): %s — the service may have been "
                         "renamed or retired" % (res, e["url"]))
            continue
        if not want_json:
            findings.add(OK, e["layer"], "endpoint reachable")
            continue
        if isinstance(res, dict) and "error" in res:
            findings.add(FAIL, e["layer"],
                         "the query answered HTTP 200 with an Esri ERROR ENVELOPE "
                         "(%s) — the request is malformed or the service rejected "
                         "it, and nothing about the status code says so. Check the "
                         "envelope's KEY NAMES against the app's own loader first; "
                         "that is what broke last time: %s"
                         % (res.get("error"), e["url"]))
            continue
        count = res.get("count") if isinstance(res, dict) else None
        if count is None:
            findings.add(FAIL, e["layer"],
                         "the count query returned no `count` field, so the layer "
                         "cannot be confirmed to be answering: %s" % e["url"])
        elif count < e["min_count"]:
            findings.add(WARN, e["layer"],
                         "the query returns %d features, below the floor of %d "
                         "recorded when the layer shipped — the source may have "
                         "moved, been re-scoped, or started truncating: %s"
                         % (count, e["min_count"], e["url"]))
        else:
            findings.add(OK, e["layer"], "endpoint answering — %d features" % count)


def render(findings):
    order = {FAIL: 0, WARN: 1, OK: 2}
    rows = sorted(findings.rows, key=lambda r: (order[r[0]], r[1]))
    n_fail = sum(1 for s, _, _ in rows if s == FAIL)
    n_warn = sum(1 for s, _, _ in rows if s == WARN)
    n_ok = sum(1 for s, _, _ in rows if s == OK)
    lines = []
    lines.append("# Layer source validation")
    lines.append("")
    lines.append("**%d FAIL · %d WARN · %d OK**" % (n_fail, n_warn, n_ok))
    lines.append("")
    if n_fail or n_warn:
        lines.append("Sources below need a human look. Nothing is auto-changed — "
                     "review, then update `index.html` (dataset ids) or re-download the "
                     "boundary shapefile as needed.")
        lines.append("")
    for sev in (FAIL, WARN, OK):
        group = [r for r in rows if r[0] == sev]
        if not group:
            continue
        lines.append("## %s (%d)" % (sev, len(group)))
        for _, layer, msg in group:
            lines.append("- **%s** — %s" % (layer, msg))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser(description="Validate the app's data-layer sources are current.")
    ap.add_argument("--report", metavar="PATH", help="write the markdown report to PATH (also printed to stdout)")
    ap.add_argument("--status-file", metavar="PATH", help="write ok|warn|fail to PATH (for CI)")
    ap.add_argument("--offline", action="store_true", help="run only the manifest↔index.html checks (no network)")
    args = ap.parse_args()

    if not os.path.exists(INDEX_HTML):
        print("validate_sources: FAIL — index.html not found at %s" % INDEX_HTML, file=sys.stderr)
        sys.exit(1)
    html = open(INDEX_HTML).read()

    if not args.offline and requests is None:
        print("validate_sources: requests not installed; run with --offline or "
              "`pip install -c ia/scripts/requirements.txt requests`", file=sys.stderr)
        sys.exit(1)

    findings = Findings()
    check_manifest_matches_app(html, findings)
    check_socrata(findings, args.offline)
    check_provenance(findings, args.offline)
    check_endpoints(findings, args.offline)

    # Which hosts asked to be slowed down, and by how much. On stderr, because
    # stdout is the markdown report that becomes the monthly issue body.
    if not args.offline and PACER is not None:
        for line in PACER.report(prefix=""):
            print(line, file=sys.stderr)

    report = render(findings)
    sys.stdout.write(report)
    if args.report:
        with open(args.report, "w") as f:
            f.write(report)

    status = findings.status()
    if args.status_file:
        with open(args.status_file, "w") as f:
            f.write(status)

    sys.exit(1 if status == "fail" else 0)


if __name__ == "__main__":
    main()
