#!/usr/bin/env python3
"""Ask each Iowa county that does NOT ship city officials whether it publishes them.

WHY THIS EXISTS AT ALL, GIVEN THE SWEEP ALREADY HAPPENED
---------------------------------------------------------
`ia-municipal-officeholders`'s blocker records a 99-county sweep on 2026-09-05,
run twice, and it was thorough: each county's homepage plus up to fourteen
followed links plus eight guessed paths, 562 pages cached, scored offline. It
found twelve counties publishing, of which nine ship.

ITS PER-COUNTY VERDICTS WERE NEVER RETAINED. The cache it wrote is
`ia/scripts/.cache/`, which is untracked, and the only tracked products are the
twelve POSITIVE results in `ia-county-city-officials.json`. So for the other 87
counties nothing in the tree says which were measured absent, which refused,
and which never answered -- that survives only as prose in a 30 KB blocker
naming about a dozen of them. This project's own rule covers it exactly: a
measurement filed in a backlog and nowhere else is a measurement the next pass
repeats. It was asked for a second time on 2026-09-25, which is the proof.

So this script's product is the ARTIFACT, not the finding: one row per county,
written to `ia/data/source/ia-city-officials-sweep.json`, so the next pass reads
it instead of re-probing 87 counties.

WHAT IT ASKS, AND THE BUDGET IT HOLDS TO
-----------------------------------------
ONE page request per county, to `/about/elected_officials/city/` -- the shared
CMS path all twelve publishers answer on, so a hit is directly comparable to a
county that already ships. robots.txt is read first, by the same client that
fetches, through `robots_gate.RobotsGate`; a county whose robots refuses the
path is recorded refused and its page is never requested.

A HOST RECORDED AS A CHALLENGE IS NOT PROBED AT ALL. Osceola answers 202 with
an sgcaptcha body on every path (the "202 is never a document" shape). That is
an access control, it is already measured, and nothing here tries one again.

THE HOST COMES FROM THE REPO'S OWN FILES FIRST, WHICH IS THE ONE THING THE 2026-09-05
SWEEP GOT WRONG. That sweep took all 99 domains from the auditor's e-mail
address, and Jasper's auditor mails from `jaspercounty.iowa.gov`, which has NO A
record -- so its 502 was never evidence about the county, and the page was found
later on `jasperia.org`, a host sitting in three of this app's own data files the
whole time. Measured 2026-09-25: SIXTEEN counties' repo-known host differs from
their auditor mail domain, Jasper among them. So the host is picked from every
`https://` literal the Iowa `data/app` files carry for that county, preferring a
`.iowa.gov` CMS host, and the auditor mail domain is only the fallback. Each row
records WHICH source supplied the host, because a negative on a mail-only domain
is a weaker statement than a negative on the county's real site.

A NEGATIVE HERE IS ABOUT THIS PATH ON THIS HOST, and the rows say so. It is not
a claim that the county publishes nothing anywhere: the 2026-09-05 re-sweep
established that reading a 404 on a path a site does not use as absence is a
wrong-path error, not a measurement. What this artifact settles is the one
question a builder needs -- does this county answer the CMS page the nine
shipping counties answer -- and it names the rest as leads rather than verdicts.

TWO SETS THAT ARE EASY TO CONFUSE, AND THE FIRST DRAFT OF THIS CHANGE CONFUSED
THEM. `derive_caveats` states both with their counts, because a sentence naming
the wrong one reaches a reader through the gap record's `wanted`. No count is
repeated HERE, deliberately -- this docstring says which sets exist and how each
is constructed, and the output says how big they are.
  * THE PAGE WAS NEVER ASKED -- robots-refused plus unreachable. That is the
    honest bound on the remaining upside, because nothing was requested from
    those counties at all.
  * NO SITE HOST IN THE REPO, which is exactly `hostSource ==
    "auditor-mail-domain"`: `pick_host` reaches the mail domain ONLY when the
    repo knows no site host, so those two are one set by construction, and most
    of it falls inside the non-answers.
They are different sizes and different claims, and the first draft wrote the
smaller one's figure for both.

THE REFUSAL TALLY IS ENTIRELY AN ARTIFACT OF PROBING A MAIL DOMAIN: not ONE
refusal is on a host the repo knows. Only some are a county's own statement
(robots.txt answering 202, or serving a rule that disallows); the rest are a
FAILED ROBOTS READ, which policy makes disallow-all and which nobody stated, and
those are not one shape either. `refusal_shape` splits them, so the proxy 502s
that are this sandbox's egress rather than the host (the
docs.legis.wisconsin.gov distinction) and the
`unable to get local issuer certificate` are visible per row instead of folded
into "mostly TLS failures". That last is the Coles/Gallatin/Vermilion
incomplete-chain shape `scripts/probe_incomplete_tls_chains.py` exists for, and
a pinned intermediate by AIA would OPEN the host rather than refuse it -- never
by disabling verification.
"""
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from robots_gate import RobotsGate, HostPacer  # noqa: E402

APP = os.path.join(HERE, "..", "data", "app")
OUT = os.path.join(HERE, "..", "data", "source", "ia-city-officials-sweep.json")
PATH = "/about/elected_officials/city/"
HEADERS = {"User-Agent": "districtry/1.0 (+https://districtry.com/ia/)",
           "Accept": "text/html,application/xhtml+xml"}
TIMEOUT = 45

# Recorded as an access control in the gap blocker, 2026-09-05: 202 with an
# sgcaptcha body on every path. Never probed again.
RECORDED_CHALLENGE = {"19143": "Osceola — 202 sgcaptcha on every path (2026-09-05)"}

# Hosts that are not the county's own site and must never be picked for it.
NOT_A_COUNTY_SITE = re.compile(
    r"arcgis|google|facebook|youtube|twitter|linkedin|census|tigerweb|granicus"
    r"|legis\.iowa\.gov|sos\.iowa\.gov|iowatreasurers|revize|civicplus|wikipedia")

# The markers the twelve publishers' pages carry, used to tell a real
# city-officials page from a CMS stub that answers 200 with nothing in it.
#
# `offName` IS THE ONE THAT DECIDES, because it is the only one that carries a
# PERSON: the shipping scraper reads every name out of `div.offName`, and
# `positionTitle` and `filterDiv` are the role heading and the per-city filter
# block, both of which a county gets from the CMS module whether or not it has
# filled anybody in. WORTH COUNTY IS WHY THIS IS SPELLED OUT: measured
# 2026-09-25 its page answers 200 with SEVEN filterDiv blocks and SEVEN
# positionTitle headings and ZERO offName divs, so the first draft of this
# classifier called it a publisher and the shipping parser returned 0 cities
# and 0 people from the same URL. A page with the module and nobody in it is a
# real and separate finding — the county already uses the route, which makes it
# a better lead than absence and a different thing to ask its auditor — so it
# gets its own verdict rather than being counted either way.
NAME_MARKER = "offName"
MARKERS = (NAME_MARKER, "positionTitle", "filterDiv")
ROLE_WORDS = ("City Clerk", "Mayor", "City Council", "City Administrator")


def county_hosts():
    """Every http host the Iowa data files name, per county FIPS."""
    hosts = {}
    for fn in sorted(os.listdir(APP)):
        if not fn.endswith(".json"):
            continue
        try:
            data = json.load(open(os.path.join(APP, fn), encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        for fips, rec in data.items():
            if not (isinstance(fips, str) and len(fips) == 5 and fips.startswith("19")):
                continue
            for m in re.finditer(r"https?://([A-Za-z0-9.\-]+)", json.dumps(rec)):
                h = m.group(1).lower()
                if not NOT_A_COUNTY_SITE.search(h):
                    hosts.setdefault(fips, set()).add(h)
    return hosts


def publishers():
    """The counties pinned in the shipping scraper — they already answer."""
    src = open(os.path.join(HERE, "ia_county_city_officials_scraper.py"),
               encoding="utf-8").read()
    return dict(re.findall(r'\("(\d{5})",\s*"([^"]+)",\s*"https?://', src))


def pick_host(fips, aud, hosts):
    hs = hosts.get(fips) or set()
    if hs:
        # A .iowa.gov CMS host first, then a www. form, then the shortest.
        best = sorted(hs, key=lambda h: (0 if h.endswith("iowa.gov") else 1,
                                         0 if h.startswith("www.") else 1, len(h)))[0]
        return best, "repo-known"
    em = aud[fips].get("email") or ""
    return (em.split("@")[1].lower() if "@" in em else None), "auditor-mail-domain"


def probe(row, gate, pacer):
    url = "https://%s%s" % (row["host"], PATH)
    row["url"] = url
    try:
        ok, why = gate.allows(url)
    except Exception as exc:
        row["verdict"] = "robots-unreadable"
        row["note"] = "robots read failed: %s" % type(exc).__name__
        return row
    row["robots"] = why
    if not ok:
        row["verdict"] = "robots-refused"
        row["note"] = "not fetched — %s" % why
        return row
    try:
        with pacer.hold(url):
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    except Exception as exc:
        row["verdict"] = "unreachable"
        row["note"] = "%s" % type(exc).__name__
        return row
    row["status"] = r.status_code
    row["bytes"] = len(r.content)
    if r.status_code == 202:
        row["verdict"] = "challenge"
        row["note"] = "202 is never a document"
        return row
    if r.status_code != 200:
        row["verdict"] = "no-page"
        row["note"] = "HTTP %d at this path" % r.status_code
        return row
    body = r.text
    found = [m for m in MARKERS if m in body]
    roles = [w for w in ROLE_WORDS if w in body]
    row["markers"] = found
    row["roleWords"] = roles
    if NAME_MARKER in found and roles:
        row["verdict"] = "publishes"
        row["note"] = "markers %s; roles %s" % (",".join(found), ",".join(roles))
    elif found:
        row["verdict"] = "scaffold-no-names"
        row["note"] = ("HTTP 200, %d bytes, CMS module present (%s) and no %s — "
                       "the county uses this route and has filled nobody in"
                       % (len(r.content), ",".join(found), NAME_MARKER))
    elif roles:
        row["verdict"] = "roles-no-markers"
        row["note"] = "roles %s but none of the CMS markers" % ",".join(roles)
    else:
        row["verdict"] = "page-names-nobody"
        row["note"] = "HTTP 200, %d bytes, no role word" % len(r.content)
    return row


def refusal_shape(why):
    """Why a robots read refused, from the reader's own message.

    The sixteen failed reads are NOT one shape, and folding them into "TLS
    failures" hides the two that are this sandbox rather than the host.
    """
    if "202" in why:
        return "robots.txt answered 202 — an access control the county states"
    if "Disallow" in why or "disallow" in why:
        return "robots.txt served and disallows the path — the county states it"
    if "ProxyError" in why or "Tunnel connection failed" in why:
        return "proxy 502 — THIS VANTAGE, not the host"
    if "local issuer" in why:
        return "incomplete TLS chain — unable to get local issuer"
    if "SSLError" in why:
        return "other TLS failure"
    return "connection reset"


STATED = ("an access control the county states", "the county states it")


def derive_caveats(rows, hosts, aud, pub):
    """Every figure the write-up quotes, DERIVED from the rows that carry them.

    WHY THIS IS A FUNCTION AND NOT A PARAGRAPH, which is the whole point of the
    change it sits in. The first version of this block was hand-typed into the
    JSON after the run, so `main()` wrote four keys and the next invocation of
    this script would have silently deleted the correction -- in a change whose
    subject is that a measurement filed where nothing maintains it gets
    repeated. The docstring above asserted "the output's caveats block states
    both, measured" while the output did not. Now it does.
    """
    ref = [r for r in rows if r["verdict"] == "robots-refused"]
    unreach = [r for r in rows if r["verdict"] == "unreachable"]
    mail = [r for r in rows if r.get("hostSource") == "auditor-mail-domain"]
    nonans = [r for r in rows
              if r["verdict"] in ("no-page", "robots-refused", "unreachable")]
    shapes = {}
    for r in ref:
        s = refusal_shape(r.get("robots") or "")
        shapes[s] = shapes.get(s, 0) + 1
    stated = sum(n for s, n in shapes.items() if any(t in s for t in STATED))

    def named(match):
        return sorted(r["county"] for r in ref
                      if match in (r.get("robots") or ""))

    # The host comparison, on the same rule pick_host uses.
    strip = lambda h: re.sub(r"^www\.", "", h)
    raw = raw_nonpub = www_only = subst = 0
    for fips in aud:
        em = aud[fips].get("email") or ""
        md = em.split("@")[1].lower() if "@" in em else None
        hs = hosts.get(fips) or set()
        if not (md and hs):
            continue
        best = sorted(hs, key=lambda h: (0 if h.endswith("iowa.gov") else 1,
                                         0 if h.startswith("www.") else 1, len(h)))[0]
        if best == md:
            continue
        raw += 1
        if fips not in pub:
            raw_nonpub += 1
        if strip(best) == strip(md):
            www_only += 1
        else:
            subst += 1

    proxy, chain = named("ProxyError"), named("local issuer")
    return {
      "pageNeverAsked": {
        "n": len(ref) + len(unreach),
        "means": ("robots-refused (%d) + unreachable (%d). THIS is the set the bound "
                  "belongs to: these counties' page was never requested, so nothing "
                  "here is a statement about whether they publish."
                  % (len(ref), len(unreach))),
        "refusalShapes": shapes,
        "ownStatement": ("Only %d of the %d refusals are the county's own statement "
                         "(robots.txt answering 202, or serving a rule that "
                         "disallows). The rest are a FAILED ROBOTS READ, which policy "
                         "makes disallow-all and which nobody stated."
                         % (stated, len(ref)))},
      "noSiteHostInRepo": {
        "n": len(mail),
        "means": ("hostSource == auditor-mail-domain. pick_host reaches the mail "
                  "domain ONLY when the repo knows no site host for that county, so "
                  "these two are the same set. %d of them are among the %d "
                  "non-answers, and a negative on a mail domain is a weaker statement "
                  "than one on a county's real site — the Jasper shape."
                  % (sum(1 for r in nonans
                         if r.get("hostSource") == "auditor-mail-domain"), len(nonans)))},
      "everyRefusalIsAMailDomain": {
        "repoKnownHostRefusals": sum(1 for r in ref if r.get("hostSource") == "repo-known"),
        "means": ("NOT ONE of the %d refusals is on a host the repo knows; all %d are "
                  "the auditor mail domain. So the refusal tally is entirely an "
                  "artifact of probing a mail domain, which strengthens the caveat "
                  "above rather than qualifying it." % (len(ref), len(ref)))},
      "hostDiffersFromAuditorMailDomain": {
        "substantive": subst, "rawStringDifference": raw,
        "wwwOnlyOfThoseRaw": www_only, "rawAcrossNonPublishers": raw_nonpub,
        "method": ("%d is the count ignoring a leading `www.`, across all %d counties. "
                   "A RAW string comparison gives %d, of which %d differ by `www.` "
                   "alone; across the non-publishers alone the raw figure is %d. State "
                   "the method with the number or a reader reproducing it gets %d."
                   % (subst, len(aud), raw, www_only, raw_nonpub, raw))},
      "failuresThatAreThisVantage": {
        "counties": proxy,
        "means": ("Failed with a proxy 502 (Tunnel connection failed), which is this "
                  "sandbox's agent egress and not the host — the "
                  "docs.legis.wisconsin.gov distinction this repo already draws. "
                  "Calling the failed reads 'mostly TLS failures on legacy domains' "
                  "folds these in wrongly.")},
      "failuresThatAreTheIncompleteChainShape": {
        "counties": chain,
        "hosts": sorted(r["host"] for r in ref if "local issuer" in (r.get("robots") or "")),
        "means": ("SSLError 'unable to get local issuer certificate' is the "
                  "Coles/Gallatin/Vermilion shape that "
                  "scripts/probe_incomplete_tls_chains.py exists for, and a pinned "
                  "intermediate by AIA would OPEN the host rather than refuse it — "
                  "never by disabling verification. The 2026-09-05 record says of its "
                  "own re-probe that the chain probe was run and found none, so one of "
                  "those two statements has moved and this row is the newer "
                  "measurement.")}}


def main():
    aud = json.load(open(os.path.join(APP, "ia-county-auditors.json"), encoding="utf-8"))
    hosts, pub = county_hosts(), publishers()
    rows = []
    for fips in sorted(aud):
        cty = aud[fips].get("county")
        if fips in pub:
            rows.append({"fips": fips, "county": cty, "verdict": "ships",
                         "note": "already pinned in ia_county_city_officials_scraper.py"})
            continue
        if fips in RECORDED_CHALLENGE:
            rows.append({"fips": fips, "county": cty, "verdict": "challenge",
                         "note": RECORDED_CHALLENGE[fips] + " — not probed again"})
            continue
        host, how = pick_host(fips, aud, hosts)
        if not host:
            rows.append({"fips": fips, "county": cty, "verdict": "no-host",
                         "note": "no site host in the repo and no auditor mail domain"})
            continue
        rows.append({"fips": fips, "county": cty, "host": host, "hostSource": how})

    todo = [r for r in rows if "verdict" not in r]
    print("counties: %d | already shipping: %d | recorded challenge: %d | to probe: %d"
          % (len(rows), sum(1 for r in rows if r.get("verdict") == "ships"),
             sum(1 for r in rows if r.get("verdict") == "challenge"), len(todo)))
    print("  host from the repo's own files: %d | only the auditor mail domain: %d"
          % (sum(1 for r in todo if r["hostSource"] == "repo-known"),
             sum(1 for r in todo if r["hostSource"] == "auditor-mail-domain")))

    session = requests.Session()
    gate = RobotsGate(session, HEADERS["User-Agent"])
    pacer = HostPacer(gate)
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(lambda r: probe(r, gate, pacer), todo))

    out = {"measured": time.strftime("%Y-%m-%d"),
           "path": PATH,
           "method": ("one GET per county at the shared CMS path all twelve "
                      "publishers answer on; robots.txt read first by the same "
                      "client; a host recorded as a challenge is not probed"),
           "classifierNote": ("`publishes` requires the name-bearing offName marker. An "
                              "earlier version accepted any marker and called Worth a "
                              "publisher, where the shipping parser returns nobody; a "
                              "module with nobody filled in gets its own verdict."),
           "caveats": derive_caveats(rows, hosts, aud, pub),
           "counties": rows}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True)
        f.write("\n")

    tally = {}
    for r in rows:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    print()
    for v, n in sorted(tally.items(), key=lambda kv: -kv[1]):
        print("  %-22s %d" % (v, n))
    print()
    print("wrote", os.path.relpath(OUT, os.path.join(HERE, "..", "..")))


if __name__ == "__main__":
    main()
