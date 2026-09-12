#!/usr/bin/env python3
"""
Check that every URL this instance's weekly scrapers FETCH is permitted by its
host's own robots.txt.

WHY THIS EXISTS
---------------
On 2026-08-31, adding Pepin County turned up seven county hosts publishing a
robots.txt whose `User-agent: *` group disallows the entire site — and this
repo was fetching all seven weekly, four of them for shipped board rosters.
Nothing in the repo could have noticed. `validate_sources.py` asks whether a
source still resolves; `validate_card_links.py` asks whether a link is alive;
neither asks whether the publisher wants an automated client there at all.

The scraper's COUNTIES table already carried a robots.txt note, and its whole
argument turned on the `*` group PERMITTING the board path for the two counties
it discussed (Iowa and Waushara, which disallow only /calendar, /meetings and
similar). That reasoning was right and was applied to two counties by hand. This
script applies it to every host, every month, so the answer cannot go stale and
a new county cannot be added against a host that has said no.

WHAT IT CHECKS, AND WHAT IT DELIBERATELY DOES NOT
-------------------------------------------------
It checks the URLs that are actually REQUESTED on a schedule, and it finds
them BY DISCOVERY rather than from a list of tables:

  * every http string in every upper-case attribute of BOTH scrapers —
    wi_county_board_scraper (weekly) and wi_county_officer_contact_scraper,
    which runs in TWO weekly workflows and so fetches its hosts twice a week,
  * a DOCUMENT_ROSTERS entry ONLY when it carries a `live` key, because that
    is the one thing in that table that makes a request. An entry without one
    is a transcription and is not a fetch — six of the nine are exactly that,
    and they must not be reported as a crawl of hosts they never touch.
  * everything EXCEPT the names in NOT_FETCHED (below), which are tables of
    already-read values the app displays. The default is to include, so a table
    added tomorrow is checked whether or not anyone remembers this file.

THE BOARD SIDE NAMED SIX TABLES BY HAND UNTIL 2026-09-02 and the paragraph
above claimed discovery of both. Three carriers written after it — Clark's
Official Directory, Pierce's annual directory, Marathon's members table — sat
outside all six, so this gate was not looking at `cms5.revize.com` or
`www.marathoncounty.gov` at all, and reported Clark's host green on four paths
the OFFICER scraper happens to read there. A hand-kept list of what a gate
covers is the one thing the gate cannot check. See NOT_FETCHED for what the
sweep then found that nobody had listed.

AND IT READS EACH POLICY WITH THE CLIENT THAT DOES THE CRAWLING (robots_headers
below). Sending a weaker client than the scraper's own turned seven counties'
readable policies into "unreadable — not assumed", which looks like caution and
means the rules were never read.

IT DOES NOT CHECK LINKS THE APP MERELY SHOWS. A `sourceUrl` on a card is an
address a reader clicks; robots.txt governs automated retrieval, not what a
page is allowed to link to. Mixing the two would report every carried county as
a violation of a rule it is the compliance with.

ROBOTS.TXT ITSELF IS ALWAYS FETCHED, by every agent, always — it is the file
whose entire purpose is to be read before deciding. A host that 404s it has no
policy and permits everything; a host whose file is unreachable (5xx, a
network failure) or refused to this client (401, 403) is reported as unknown
rather than assumed either way.

WHICH GROUP APPLIES is RFC 9309's answer, read by scripts/robots_policy.py
since 2026-09-12 (the fleet's one parser; this script's own was retired into
it, wildcard cases and all): every group whose token names the client that
fetches the host, merged; if none does, every `*` group, merged. Where a file
names ClaudeBot or GPTBot and disallows them, that is recorded in the
scraper's own note and binds those crawlers, not this client. The old
paragraph here said this script reads `*` and nothing narrower, "because
reading a narrower group to get a friendlier answer would be picking the rule
that suits" — but a group that names this client by its token is the rule the
site wrote FOR it, not a friendlier one it picked, and a file with two `*`
groups (the Cloudflare managed block above a site's own rules) is read as one
group, which is the shape that was misread on wyomingmi.gov. A host stating
a Crawl-delay in a binding group has it printed here; honouring it is the
scraper's job and is hand-set per host (wi_county_clerk_scraper's
CRAWL_DELAY_S), which this script does not yet check.

A host that answers 401 or 403 to its OWN robots.txt stays UNKNOWN here, and
that was re-measured rather than kept by habit: a 2026-09-12 draft made it a
STOP, and the run reported 32 scheduled fetches disallowed — every one on
services1/2/3/8/9.arcgis.com, carto.nationalmap.gov, data.openstates.org and
the two Milwaukee hosts. The API hosts answer 403 to /robots.txt from their
CDN while serving their layers to everyone; the Milwaukee hosts were a
Cloudflare challenge this sandbox meets and the CI runner does not. Neither
is a site refusing its data. RFC 9309 files a 403 with a 404 (allow) and
scripts/robots_policy.py keeps that default while leaving the status visible,
so a scraper reading a municipal WEBSITE — where a 403 there is a WAF refusing
the client — can choose refusal explicitly, as the DuPage scraper does.

Usage:
    python3 wi/scripts/validate_robots.py            # fetch and check
    python3 wi/scripts/validate_robots.py --offline  # list the surface only
"""

import glob
import gzip
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
# THE ROBOTS READER IS ONE COPY at the repo root, scripts/robots_policy.py
# (2026-09-12; this file's own `*`-group parser was retired into it, and so
# was the `robots_rules` module that had briefly carried it). APPENDED rather
# than inserted, so this instance's own modules still win any name collision
# — inserting the root scripts/ first is how a bare `import validate_sources`
# once resolved to Illinois's and made this sweep report Kane and Coles hosts
# as Wisconsin's.
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)),
                             "scripts"))
from robots_policy import RobotsPolicy, resolve_template  # noqa: E402

def robots_headers(host):
    """The header set THIS host's own pages are already crawled with.

    ROBOTS.TXT MUST BE READ BY THE CLIENT THAT DOES THE CRAWLING, and until
    2026-09-02 this script sent its own bare User-Agent — one line, no Accept,
    no client hints — while the scraper it audits sends three carefully pinned
    header sets. That asymmetry is not a detail: `www.marathoncounty.gov`
    serves its board page to the scraper every week and answered THIS script
    403, so its policy was filed as "unreadable — not assumed", which reads
    like caution and means the rules were never read. It serves a 6,641-byte
    robots.txt to the scraper's own default client on the first try.

    Reading the policy with a WEAKER client than the crawl is the one
    asymmetry a compliance gate must not have. (The opposite — reaching for a
    stronger client than the crawl uses — would be defeating a control, and is
    not what this does: the pins below are exactly the scraper's own, host for
    host, and nothing is retried up the ladder.)
    """
    import wi_county_board_scraper as board
    if host in getattr(board, "HONEST_UA_HOSTS", ()):
        return board.HONEST_UA
    if host in _browser_header_hosts():
        return board.BROWSER
    return board.UA


def _browser_header_hosts():
    """Hosts whose county is pinned to the scraper's Chrome-navigation set."""
    import wi_county_board_scraper as board
    pinned = getattr(board, "BROWSER_HEADER_COUNTIES", set())
    return {urllib.parse.urlsplit(url).hostname
            for fips, _n, _s, _d, url in board.COUNTIES if fips in pinned}


def read_body(response):
    """The response text, gunzipped when the pinned header set asked for gzip.

    urllib does not decompress, and one of the three header sets sends
    `Accept-Encoding: gzip` — so without this, a host on that pin returns a
    robots.txt of binary noise that parses to zero rules and reports as
    permitting everything.
    """
    raw = response.read()
    if (response.headers.get("Content-Encoding") or "").lower() == "gzip":
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", "replace")


def scheduled_scraper_modules():
    """[(module, label)] for every *_scraper.py a workflow runs on a schedule.

    The workflow files are the authority on "scheduled": a scraper nothing
    dispatches makes no requests, and sweeping it would report policies for
    fetches that never happen.
    """
    import importlib
    texts = workflow_texts()
    out = []
    # SCRAPERS AND BUILDERS BOTH FETCH. Globbing *_scraper.py alone left the
    # scheduled build_*.py fetchers outside a sweep whose stated contract is
    # "every address this instance requests on a schedule" — the Open States CSV
    # in build_wi_legislature_roster.py and the two in
    # build_rusd_school_board_districts.py among them. The contract was right;
    # the glob was narrower than the sentence.
    for pattern in ("*_scraper.py", "build_*.py"):
        for path in sorted(glob.glob(os.path.join(SCRIPT_DIR, pattern))):
            stem = os.path.basename(path)[:-3]
            if any(stem == m.__name__ for m, _l in out):
                continue
            runs = [n for n, t in texts if stem in t]
            if not runs:
                continue
            try:
                mod = importlib.import_module(stem)
            except Exception as exc:  # noqa: BLE001
                raise SystemExit(
                    "robots: %s is run by %s but could not be imported (%s: %s) — "
                    "a module this sweep cannot read is a module whose fetches go "
                    "unchecked, which is the state this gate exists to prevent"
                    % (stem, ", ".join(runs), type(exc).__name__, exc))
            out.append((mod, "%s [%s]" % (stem, ", ".join(runs))))
    if len(out) < 2:
        raise SystemExit("robots: discovered %d scheduled scraper(s) under %s — "
                         "that cannot be right, and a narrowed sweep reporting "
                         "OK is exactly what this gate must never do"
                         % (len(out), SCRIPT_DIR))
    return out


def workflow_texts():
    """[(filename, text)] for every workflow file."""
    root = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)),
                        ".github", "workflows")
    out = []
    for name in sorted(os.listdir(root)):
        if name.endswith((".yml", ".yaml")):
            with open(os.path.join(root, name), encoding="utf-8") as f:
                out.append((name, f.read()))
    return out


def fetched_urls():
    """[(url, why)] — every address this instance requests on a schedule."""
    texts = workflow_texts()
    import wi_county_board_scraper as board
    import wi_county_officer_contact_scraper as officers
    _excluded_specs_are_unscheduled(board)
    out = []
    for fips, name, seats, strategy, url in board.COUNTIES:
        out.append((url, "%s board roster (%s)" % (name, strategy)))
    # A CARRIED ROSTER IS NOT A FETCH unless it re-tries its live page.
    for spec in getattr(board, "DOCUMENT_ROSTERS", []):
        if spec.get("live"):
            out.append((spec["source_url"],
                        "%s carried roster, live re-try each run" % spec["name"]))
    # THE MODULE LIST IS DISCOVERED, NOT KEPT. It used to name three modules by
    # hand while eight other scheduled scrapers sat outside the sweep entirely —
    # this file's own comment called that "an open gap rather than a statement
    # that their hosts permit anything", and it was right: widening it found
    # milwaukeemaps.milwaukee.gov publishing `User-agent: * / Disallow: /` under
    # a fetch this repo had been making every week.
    #
    # A hand-kept list across modules is the same shape as the miss recorded
    # below, one level up, and the fleet has learned it twice elsewhere
    # (validate_card_links.py naming four instances of five;
    # check_roster_retention.py pointed at one instance's data/app). So the
    # subject is now every wi/scripts/*_scraper.py that a workflow actually
    # RUNS — which is exactly this gate's contract, "every address this
    # instance requests on a schedule". A scraper written tomorrow is swept the
    # day its workflow lands, and one that exists but is not scheduled is
    # correctly left alone.
    _module_exclusions_still_unscheduled(texts)
    for module, label in scheduled_scraper_modules():
        skip = NOT_FETCHED_BY_MODULE.get(module.__name__, {})
        for nm in dir(module):
            if not nm.isupper() or nm in NOT_FETCHED or nm in skip:
                continue
            for url in _strings(getattr(module, nm)):
                out.append((url, "%s %s" % (label, nm)))
    # THE MONTHLY MANIFEST FETCHES TOO. validate_sources.py's PROVENANCE and
    # ENDPOINTS rows are requested by wi-validate-sources on the 1st of every
    # month, which is a schedule, and one of them was still requesting the very
    # host this gate had just found publishing a blanket Disallow. A row that
    # declares `robots_disallowed` is not fetched and is skipped here too.
    # BY PATH, NEVER BY NAME. `validate_sources` exists in every instance's
    # scripts/ AND at the repo root, and by the time this runs the modules swept
    # above have already put the ROOT scripts/ on sys.path — one of them imports
    # the fleet-wide `undeliverable` from there. A bare `import validate_sources`
    # therefore resolved to ILLINOIS's, and this sweep quietly began reporting
    # Kane and Coles County hosts as Wisconsin's scheduled fetches. Caught
    # because two Illinois hostnames appeared in a Wisconsin run's output.
    import importlib.util
    _vs_path = os.path.join(SCRIPT_DIR, "validate_sources.py")
    _spec = importlib.util.spec_from_file_location("wi_validate_sources", _vs_path)
    try:
        vs = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(vs)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit("robots: %s could not be imported (%s) — its monthly "
                         "fetches would go unswept" % (_vs_path, type(exc).__name__))
    if os.path.dirname(os.path.abspath(vs.__file__)) != SCRIPT_DIR:
        raise SystemExit("robots: loaded %s, which is not this instance's — a sweep "
                         "reporting another state's hosts is not this gate"
                         % vs.__file__)
    for row in getattr(vs, "PROVENANCE", []):
        if row.get("robots_disallowed") or not row.get("source_url"):
            continue
        out.append((row["source_url"],
                    "validate_sources PROVENANCE [%s] (monthly)" % row.get("layer")))
    for row in getattr(vs, "ENDPOINTS", []):
        if row.get("url"):
            out.append((row["url"],
                        "validate_sources ENDPOINTS [%s] (monthly)" % row.get("layer")))

    seen, uniq = set(), []
    for url, why in out:
        if url.startswith("http") and url not in seen:
            seen.add(url)
            uniq.append((url, why))
    return sorted(uniq)


# THE SWEEP IS BY DISCOVERY, NOT BY A LIST: it takes EVERY http string in every
# upper-case attribute of BOTH scrapers, so a table added tomorrow is checked
# whether or not anyone remembers this file. Over-reporting is the safe
# direction for a gate whose whole job is to never miss a fetch.
#
# THAT WAS TRUE OF THE CONTACT SCRAPER ONLY UNTIL 2026-09-02, and the docstring
# above claimed it of both. The board side named six tables by hand, and three
# carriers added after it was written — Clark's Official Directory, Pierce's
# annual directory and Marathon's members table — sat outside all six. So the
# gate whose entire purpose is to never miss a fetch was silently missing
# `cms5.revize.com` and `www.marathoncounty.gov` altogether; Clark's host was
# reported only because the OFFICER scraper happens to read four other paths
# there, which is the most misleading possible pass. Discovery also swept in
# four hosts nobody had listed at all: `web.archive.org` and `archive.org` (the
# archive ladder genuinely fetches them every run), `services1.arcgis.com` for
# the LTSB ward-witness query, and the second URL inside three specs whose
# key was not one of the three the hand list looked at. A HAND-KEPT LIST OF
# WHAT A GATE COVERS IS THE THING THE GATE CANNOT CHECK.
#
# Names listed below are the exceptions, and listing one is a CLAIM — that
# nothing in this repo requests those URLs — which is worth as much as the
# reading of the module that backs it.
#
#   CARRIED_CONTACTS holds the office contact of the four counties whose hosts
#   disallow this client. Its URLs are what the CARD SHOWS a reader, taken from
#   a capture made before the policy was read; `main()` emits them and makes no
#   request. It is the DOCUMENT_ROSTERS case one file over, and the same rule
#   applies for the same reason: a transcription is not a fetch. Note that this
#   table has no `live` escape hatch at all, so unlike a roster entry it cannot
#   drift back into being fetched without an edit here too.
#
#   Discovery also swept in four things nobody had listed: `web.archive.org`
#   and `archive.org`, which the archive ladder genuinely requests every run;
#   `services1.arcgis.com` for the LTSB ward-witness query that checks every
#   new county's district numbers; and the SECOND url inside three specs,
#   whose key was not one of the three the hand list looked at.
#
#   DOCUMENT_ROSTERS is the board scraper's own carried table — nine counties
#   read once and dated, six of them because their hosts ask automated readers
#   to stay off. Fetching those hosts to check a policy this project has ALREADY
#   read and complied with would be the one request the compliance forbids, so
#   the whole table is excepted here and its `live` entries are added back by
#   name in the loop above. That inversion is deliberate: an entry that starts
#   re-trying its page appears in this surface the moment it gains the key.
NOT_FETCHED = {"CARRIED_CONTACTS", "DOCUMENT_ROSTERS",
               # ASHLAND_BOARD is a reader kept for the day the county says
               # yes, not a schedule: ashlandcountywi.gov disallows the whole
               # site to every agent it does not name, so the roster moved to
               # DOCUMENT_ROSTERS and nothing dispatches this spec. The spec
               # stays because the reader needs it if the crawl is ever
               # re-enabled — see the scraper's Ashland section.
               "ASHLAND_BOARD"}
# AN EXCLUSION THAT CANNOT SILENTLY BECOME A LIE. Naming a spec here says
# "nothing fetches this", and the one way that stops being true is somebody
# re-registering it in SINGLE_COUNTY_CARRIERS — at which point the gate that
# exists to notice a disallowed crawl would be looking away from exactly the
# county it was hidden for. So the claim is CHECKED rather than trusted.
CARRIER_REGISTERED = "SINGLE_COUNTY_CARRIERS"


# ATTRIBUTES A SCHEDULED MODULE OWNS BUT A SCHEDULED RUN NEVER FETCHES.
# Widening the sweep to build_*.py immediately over-reported two counties whose
# robots.txt disallows the path this repo has in a table — Jackson and Polk in
# build_wi_county_board_directory.COUNTY_SITES — and the report was wrong,
# because that table is 72 CARD-LINK TARGETS. Only `--probe` fetches them, and
# smoke-test.yml runs `--check`, whose own step comment says "and fetches
# nothing". Robots governs crawling, not linking, and a gate that cannot tell
# the two apart would end up arguing that the app must stop LINKING a county to
# its own website.
#
# THE EXCLUSION IS MECHANICALLY CHECKED, not asserted: every workflow that runs
# the module must invoke it with `needs` and never with `fetches`. Put --probe
# in CI and this fires, which is the property NOT_FETCHED's own comment demands
# of an exclusion.
NOT_FETCHED_BY_MODULE = {
    "build_wi_county_board_directory": {
        "COUNTY_SITES": {
            "needs": "--check",
            "fetches": "--probe",
            "why": "72 county-website link targets for the board card; only the "
                   "operator's --probe requests them, and CI runs --check, "
                   "which fetches nothing.",
        },
    },
}


def _module_exclusions_still_unscheduled(texts):
    """A per-module exclusion must match how the workflows actually invoke it."""
    for module, attrs in sorted(NOT_FETCHED_BY_MODULE.items()):
        runs = [(n, t) for n, t in texts if module in t]
        for attr, spec in sorted(attrs.items()):
            for name, text in runs:
                if spec["fetches"] and ("%s.py %s" % (module, spec["fetches"])) in text:
                    raise SystemExit(
                        "robots: FAIL — %s.%s is excluded from the sweep because "
                        "only %s fetches it, but %s now runs exactly that. Its "
                        "hosts are being requested on a schedule and unchecked."
                        % (module, attr, spec["fetches"], name))
                if spec["needs"] and ("%s.py %s" % (module, spec["needs"])) not in text:
                    raise SystemExit(
                        "robots: FAIL — %s.%s is excluded on the grounds that %s "
                        "runs %s, and it no longer does. Re-establish how that "
                        "workflow invokes the module before trusting the exclusion."
                        % (module, attr, name, spec["needs"]))


def _excluded_specs_are_unscheduled(board):
    """A NOT_FETCHED spec must not be registered as a live carrier."""
    registered = {id(spec) for spec, _strategy
                  in getattr(board, CARRIER_REGISTERED, ())}
    wrong = sorted(n for n in NOT_FETCHED
                   if id(getattr(board, n, None)) in registered)
    if wrong:
        raise SystemExit(
            "robots: FAIL — %s is listed in NOT_FETCHED (as not fetched) and is "
            "ALSO registered in %s, so it IS fetched weekly and this gate would "
            "not have checked its host. Either take it out of NOT_FETCHED or out "
            "of the carrier list." % (", ".join(wrong), CARRIER_REGISTERED))


def _strings(obj):
    """Every http string anywhere inside a nested structure."""
    if isinstance(obj, str):
        return [obj] if obj.startswith("http") else []
    if isinstance(obj, dict):
        return [u for v in obj.values() for u in _strings(v)]
    if isinstance(obj, (list, tuple, set)):
        return [u for v in obj for u in _strings(v)]
    return []


# The parser, the longest-match evaluator and resolve_template() that used to
# sit here were retired into scripts/robots_policy.py on 2026-09-12, with the
# two cases they had been written for asserted in its --selftest:
# cms5.revize.com's `Allow: /*.pdf$` over `Disallow: /` (documents yes,
# everything else no — a startswith matcher read it as a flat refusal), and
# Clark's `Disallow: *?lightbox=`, which only a match against path AND query
# can see.


def main():
    offline = "--offline" in sys.argv[1:]
    urls = fetched_urls()
    by_host = {}
    for url, why in urls:
        parts = urllib.parse.urlparse(resolve_template(url))
        # RFC 9309 section 2.2.2: the string a rule is matched against is the
        # path AND the query. Matching the path alone would let a rule like
        # `Disallow: /*?lightbox=` — which exists on one county's host — miss
        # the very URLs it names, and would call a cache-busted `.pdf?t=...`
        # permitted under an `Allow: /*.pdf$` that does not actually reach it.
        target = (parts.path or "/") + (("?" + parts.query) if parts.query else "")
        by_host.setdefault(parts.netloc, []).append((target, why, url))
    print("robots: %d scheduled URLs across %d hosts" % (len(urls), len(by_host)),
          file=sys.stderr)
    if offline:
        for host in sorted(by_host):
            print("  %-34s %d URL(s)" % (host, len(by_host[host])))
        return 0

    disallowed, unknown = [], []
    for host in sorted(by_host):
        headers = robots_headers(host)
        client = headers["User-Agent"]
        try:
            req = urllib.request.Request("https://%s/robots.txt" % host, headers=headers)
            with urllib.request.urlopen(req, timeout=25) as r:
                body = read_body(r)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                # Not assumed either way. RFC 9309 says allow; this audit says
                # "policy unknown" and does not fail on it, as it always has,
                # because the hosts that do this are API hosts (every ArcGIS
                # Online FeatureServer, carto.nationalmap.gov, data.openstates.org)
                # serving their data to everyone, and — from a sandbox — sites
                # behind a Cloudflare challenge the CI runner does not meet.
                unknown.append((host, "HTTP %d" % e.code))
                print("  ?    %-34s robots.txt refused to this client (HTTP %d) — "
                      "policy unread, not assumed" % (host, e.code))
                continue
            if 400 <= e.code < 500:
                print("  ok   %-34s no robots.txt (HTTP %d, nothing disallowed)" % (host, e.code))
                continue
            unknown.append((host, "HTTP %d" % e.code))
            print("  ?    %-34s robots.txt unreadable (HTTP %d)" % (host, e.code))
            continue
        except Exception as e:          # noqa: BLE001 - reachability, not policy
            unknown.append((host, str(e)[:50]))
            print("  ?    %-34s robots.txt unreadable (%s)" % (host, str(e)[:44]))
            continue
        policy = RobotsPolicy(body)
        groups = policy.binding_groups(client)
        if not groups:
            print("  ok   %-34s no group binds this client (nothing disallowed to us)" % host)
            continue
        bound_by = "`*`" if all(g.is_catch_all() for g in groups) else "a group naming this client"
        bad = [(p, why) for p, why, _u in by_host[host] if not policy.allows(client, p)]
        delay = policy.crawl_delay(client)
        note = ("; Crawl-delay %g s stated" % delay) if delay else ""
        if bad:
            for path, why in bad:
                disallowed.append((host, path, why))
            print("  STOP %-34s %s disallows %d of %d scheduled path(s)%s"
                  % (host, bound_by, len(bad), len(by_host[host]), note))
        else:
            print("  ok   %-34s %s permits our %d path(s)%s"
                  % (host, bound_by, len(by_host[host]), note))
        time.sleep(0.2)

    print(file=sys.stderr)
    if unknown:
        print("robots: %d host(s) would not serve robots.txt — policy unknown, "
              "not assumed: %s" % (len(unknown), ", ".join(h for h, _ in unknown)),
              file=sys.stderr)
    if disallowed:
        print("robots: FAIL — %d scheduled fetch(es) are disallowed by the host's "
              "own robots.txt:" % len(disallowed), file=sys.stderr)
        for host, path, why in disallowed:
            print("  %s%s  — %s" % (host, path, why), file=sys.stderr)
        print("\nA county that asks not to be crawled has not refused to publish: "
              "the routes are to carry the roster as a dated document "
              "(DOCUMENT_ROSTERS, no `live` key), to let the county go unnamed "
              "with a gap record, or to ask the county. Do not simply rename the "
              "user agent.", file=sys.stderr)
        return 1
    print("robots: OK — every scheduled fetch is permitted by its host's robots.txt, "
          "read for the client that fetches it", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
