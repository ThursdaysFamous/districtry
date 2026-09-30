#!/usr/bin/env python3
"""
What every host this project fetches says about us — measured from wherever this
runs, and recorded with that vantage.

WHY. `validate_robots_adoption.py` says which scripts read robots.txt before
crawling; 224 of 266 do not, and wiring them is a behaviour change to scheduled
refreshes that work today. Two questions have to be answered before a scraper is
switched over, and neither is answerable from the tree: does this host's policy
PERMIT the path that scraper reads, and can its policy be READ at all. An
unreadable robots.txt disallows under RFC 9309 §2.3.1.4, so a host nobody can
read is a refresh that stops.

THE VANTAGE IS THE POINT, AND IT IS WHY THIS EXISTS RATHER THAN A SWEEP FROM A
SANDBOX. This project's own record already says reachability moves with the
address it is measured from — `HostPacer`'s docstring names two counties whose
sites answer from one sandbox and not another, and `user-agent-measurements.json`
carries 33 hosts whose robots.txt read as unreadable there, among them four whose
only symptom is a TLS chain error that a Claude Code sandbox's egress proxy is
known to produce and a GitHub runner is not. Ruling on those readings would be
ruling on this address. So this writes `vantage` into its own output, the way the
user-agent probe does, and `.github/workflows/probe-robots-verdicts.yml`
dispatches it on a runner, which is the vantage the scheduled scrapers actually
crawl from. CLAUDE.md names that as the honest fix for the one host already
deferred (`web.archive.org`).

ONE READER, TWICE OVER. The host inventory and the url chosen per host come from
`probe_user_agents.build_inventory()`/`choose_url()`, not from a second scan —
that module's own record is that a hand-written extraction measured 60 hosts at
the wrong address, a directory rather than the page a scraper reads, and moved
25 verdicts when it was fixed. The policy itself is read by
`robots_policy.fetch_verdict`, which is the reader every gate in the fleet uses,
with the retry that exists because one flaky read must not decide a host.

WHICH CLIENT IT ASKS AS. CLAUDE.md: robots.txt is read with the EXACT client
that will crawl. The crawling client is recorded per host in
`user-agent-measurements.json` — a host whose verdict is `token-ok` is crawled
with the districtry token, one recorded as answering only a browser string is
crawled with that string and its client hints — so this reads each host as
whatever that file says serves it, and names the rung in its output. It NEVER
tries a second client on a host that answered the first: that is the Minnesota
measurement of 2026-09-29, where probing a browser string on a host already
serving the token got this address redirected for every request afterwards.

A `refuse` VERDICT OF STATUS `unreachable` IS NOT A POLICY AND MUST NOT BE WIRED
ON. Measured on the first full run, 2026-09-30, 16 of the 58 non-allowing hosts
answered nothing rather than a refusal, and most of those were TIMEOUTS from the
runner on hosts that serve this sandbox a policy within a second --
www.wicourts.gov, docs.legis.wisconsin.gov, mapservices.legis.wisconsin.gov,
gisservices.its.ny.gov, gis.lasallecounty.org, librarylearning.org,
www.revenue.wi.gov among them. A seventeenth was 127.0.0.1, which was never a
crawl subject at all -- a loopback server this repository starts itself, read at a
literal `%d` port template with nothing listening -- and it is out of the record
now, with the reason in the record's own summary. It is the same defect as the
timeouts in miniature and the easiest to see: the row said a host refuses us when
what happened was that nobody answered. Three attempts apart, the timeout is the runner's
route rather than the host's answer, and this project has already paid once for
treating an unreadable read as a decision: four hosts whose only symptom was an
incomplete TLS chain read as refusing while their pages were being fetched
successfully in the same week. So a wiring pass reads `served` with a matching
Disallow as a refusal, and takes an `unreachable` as a question to re-measure --
from both vantages, and with the client that crawls.

www.colesco.illinois.gov IS THE ONE TO LOOK AT FIRST AND IS THE ONE CASE THIS
SANDBOX CANNOT ANSWER. Its entry is `unable to get local issuer certificate`
although PINNED_CHAINS covers it, so on the runner either the pin is not reaching
this read or that host needs a different intermediate than the three beside it --
and a re-read from here settles neither, because this environment's egress
gateway terminates TLS and re-issues every certificate under its own CA (measured
2026-09-30: the leaf served here for that host has issuer `O = Anthropic,
CN = Egress Gateway SDS Issuing CA (production)`). So a sandbox SSLError on a
pinned host is this proxy and says nothing about the chain the host serves, and a
sandbox SUCCESS would say nothing either, since the proxy's own CA is what
verified it. THE RE-MEASUREMENT HAS TO RUN ON THE RUNNER, where the pin was
applied and the failure was recorded.

SOME RECORDED HOSTS ARE NOT CRAWL SUBJECTS AT ALL and their refusals mean nothing
here: photon.komoot.io and www.komoot.com are the geocoder a READER's browser
calls, and districtry.goatcounter.com is this site's own analytics. They are in
the inventory because they are url literals in app files, and a policy aimed at
crawlers has nothing to say about a request a person's browser makes.

IT FETCHES ROBOTS.TXT AND NOTHING ELSE. One request per host, no page, no
retry beyond the shared reader's own, and a host stating a Crawl-delay is not
paced because a delay inside a file cannot govern the fetch that reads it.
"""

import argparse
import concurrent.futures
import datetime
import json
import os
import socket
import sys
import time
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import probe_user_agents as ua          # noqa: E402  the one inventory
import robots_policy                    # noqa: E402  the one reader
import scraper_common as sc             # noqa: E402  the pinned clients

OUT = os.path.join(REPO, "robots-verdicts.json")
MEASUREMENTS = os.path.join(REPO, "user-agent-measurements.json")

# The rung a host is crawled with, from its recorded user-agent verdict. A
# verdict this table does not name is crawled with the districtry token, which
# is what a scraper sends unless its own file records a measured reason not to.
BROWSER_VERDICTS = {"stack-not-token", "token-refused", "token-refused-and-stack",
                    "browser-only", "all-refused", "challenged", "proxy-denied"}


# HOSTS THAT SERVE ONLY THEIR LEAF CERTIFICATE, and the pinned intermediate each
# scraper already completes the chain with. Read with the default trust store
# these four answer CERTIFICATE_VERIFY_FAILED, which RFC 9309 2.3.1.4 files as
# unreachable and therefore disallows -- measured from a GitHub runner on
# 2026-09-30, all four, while `update-ilga-roster.yml` was reading www.ilga.gov's
# pages on that same runner and succeeding. So the refusal was this probe's trust
# store rather than any host's policy, which is CLAUDE.md's consistency rule --
# read the policy with the client that crawls -- reaching down into the handshake.
#
# THE KEY IS NOT GUESSED: each entry names the file that already reads that host
# with that intermediate, and `audit_pinned_chains` re-reads it every run, failing
# on an entry whose file has gone or has stopped naming the host or the key. An
# entry can therefore only describe the tree, and a scraper that drops its pinning
# turns this red rather than leaving a stale permission behind.
PINNED_CHAINS = {
    "www.ilga.gov": ("sectigo-ov-r40", "scripts/ilga_scraper.py"),
    "gallatinco.illinois.gov": ("sectigo-ov-r40",
                                "scripts/il_county_commissioners_scraper.py"),
    "www.colesco.illinois.gov": ("godaddy-g2",
                                 "scripts/coles_county_board_scraper.py"),
    "www.vercounty.org": ("gogetssl-rsa-dv",
                          "scripts/vermilion_county_board_scraper.py"),
}


def audit_pinned_chains(repo=REPO):
    """Reasons each PINNED_CHAINS entry no longer describes the tree, or []."""
    problems = []
    for host, (key, path) in sorted(PINNED_CHAINS.items()):
        full = os.path.join(repo, path)
        if not os.path.exists(full):
            problems.append("%s: %s is not in the tree" % (host, path))
            continue
        with open(full, encoding="utf-8") as fh:
            text = fh.read()
        if host not in text:
            problems.append("%s: %s no longer names that host" % (host, path))
        if key in text:
            continue
        # A CALL WITH NO KEY TAKES `aia_bundle`'s DEFAULT, and Coles's does, so the
        # key does not appear in that file at all. The first draft of this table
        # recorded the key by reading the fleet's other three callers and assuming
        # the fourth spelled it too; this audit caught that on its first run, which
        # is what it is for. Accepting a defaulted call therefore means checking the
        # DEFAULT, so a change to it fails here rather than silently re-pointing
        # this host at another authority's intermediate.
        import inspect

        import aia_bundle
        default = inspect.signature(aia_bundle.ca_bundle).parameters["key"].default
        if "aia_bundle.ca_bundle(" in text and default == key:
            continue
        problems.append("%s: %s no longer pins %s (nor calls ca_bundle for the "
                        "default, which is now %s)" % (host, path, key, default))
    return problems


def pinned_session(host):
    """A requests session trusting `host`'s omitted intermediate, or None.

    The bundle is a temp file `aia_bundle` writes per call; the probe is one
    process that exits, so it is not deleted here -- deleting it would need the
    session's lifetime threaded through `probe_host`'s return, for a few KB in
    the runner's own temp directory.
    """
    entry = PINNED_CHAINS.get(host)
    if entry is None:
        return None
    import aia_bundle
    import requests

    session = requests.Session()
    session.verify = aia_bundle.ca_bundle("robots-verdicts", entry[0])
    return session


def client_for(verdict):
    """(label, user_agent, headers) — the client this host is crawled with."""
    if verdict in BROWSER_VERDICTS:
        headers = dict(sc.UA_HINTS_CHROME_126)
        headers["User-Agent"] = sc.UA_CHROME_WIN_126
        return "chrome+hints", sc.UA_CHROME_WIN_126, headers
    return "token", sc.UA_ROSTER_BOT, {"User-Agent": sc.UA_ROSTER_BOT}


# Hosts this tree crawls that `probe_user_agents.SKIP_HOST_RE` leaves out — see
# subject() for why the two readers differ here. Each one is fetched by a
# scraper, so each one's robots.txt is a question about our own crawling.
ALWAYS_ASKED = {
    "web.archive.org": "archived county pages, read as a fallback rung by "
                       "lake/mchenry/kendall/shelby and mi_detroit",
    "archive.org": "the wayback availability API those rungs ask first",
}


def subject(inventory):
    """Every host the tree fetches, which is what the robots question is about.

    NOT `probe_user_agents.subject_hosts`, WHICH THIS USED AND WHICH ANSWERS A
    DIFFERENT QUESTION. That one returns the hosts a browser-string caller
    reaches, because the user-agent question is only ever about those: a host
    nothing sends a browser string to has nothing to measure there. The robots
    question is about every host anything fetches, and measured 2026-09-30 the
    two differ by more than half -- 266 against 508 -- so the first record this
    probe wrote carried the sentence "robots.txt of every host the tree fetches"
    over a reading of 52% of them. THE SUBJECT LINE WAS THE CLAIM AND THE CODE
    DID NOT MEET IT, which is this fleet's recurring defect rather than a
    miscount: a figure taken from the wrong reader reads exactly like a figure.

    The 242 it adds are hosts only token-sending callers reach, and a token
    sender is bound by robots.txt exactly as a browser-string sender is.

    THE DEFERRED HOSTS ARE ASKED TOO, and they are the reason this function does
    not simply return the inventory's keys. `scraper_common.ROBOTS_DEFERRED_HOSTS`
    records a host whose policy nobody here has managed to read, with
    web.archive.org's entry saying in as many words that the honest fix is to
    measure it from a runner -- and this probe IS that runner, so leaving it out
    kept the one host the deferral was waiting on out of the measurement it was
    waiting for. It is in the inventory or it is not, and either way it is asked.

    AND SO ARE THE INTERNET ARCHIVE'S TWO HOSTS, WHICH THE INVENTORY SKIPS ON
    PURPOSE AND THIS QUESTION MUST NOT. `probe_user_agents.SKIP_HOST_RE` excludes
    them along with GitHub, the package indexes, the CDNs and the certificate
    authorities: infrastructure a user-agent measurement has nothing to say
    about. But five scrapers CRAWL the Archive for a page a county's own site
    would not serve, and robots.txt binds a crawl of it exactly as it binds a
    crawl of a county. Until 2026-09-30 they were in this subject only because
    web.archive.org happened to be DEFERRED, so retiring that deferral for the
    right reason took the host out of the measurement -- a subject that depended
    on a backlog entry rather than on what the tree fetches. Named here instead,
    with that reason, so the record keeps describing the crawl.
    """
    hosts = set(inventory)
    hosts.update(sc.ROBOTS_DEFERRED_HOSTS)
    hosts.update(ALWAYS_ASKED)
    return sorted(hosts)


def read_verdicts(path=MEASUREMENTS):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def url_for(inventory, host):
    """The address this host is asked about — a url a scraper actually reads.

    A deferred host may not be in the inventory at all (its callers can reach it
    by a composed url rather than a literal), and there is still a policy to read,
    so the host root stands in. The row records the url asked about either way,
    so a reader can tell which of the two it was.
    """
    entry = inventory.get(host)
    return ua.choose_url(entry) if entry else "https://%s/" % host


def probe_host(host, url, verdict_kind, reads=1, gap=0):
    """One host's verdict, or the honest reading of `reads` of them.

    WHY REPEATED READS EXIST AT ALL. A managed challenge answers
    non-deterministically -- CLAUDE.md records ten of twenty-four reads
    challenged on one host, with seven of eight host-and-client pairs giving
    BOTH answers -- so one read decides nothing and the fleet's rule for such a
    host is a DELIBERATE re-measurement: the crawling client serving on three
    consecutive reads at least fifteen seconds apart. Nothing here could take
    that reading, so a host was entered in the sticky table on one challenge and
    could only ever leave it by hand.

    THE MOST RESTRICTIVE READING IS THE ANSWER, never the last or the luckiest:
    getting in on the reads where the control happens to be off is working
    around it. Every reading is kept beside it, so a reader can see the split
    rather than a verdict that hides it.
    """
    label, agent, headers = client_for(verdict_kind)
    # The scheme of the url a scraper actually reads, because a host served over
    # http publishes its policy there and asking https would measure a different
    # server or none at all.
    scheme = urlsplit(url).scheme or "https"
    robots_url = "%s://%s/robots.txt" % (scheme, host)
    session = pinned_session(host)
    if session is not None:
        label += "+pinned-chain"

    def one_read():
        try:
            v = robots_policy.fetch_verdict(robots_url, agent, session=session,
                                            headers=headers)
        except Exception as exc:                  # a reader error is a reading
            return {"host": host, "url": url, "client": label,
                    "status": "error", "why": "%s: %s" % (type(exc).__name__, exc),
                    "allows": None}
        allowed, why = v.allows(agent, url)
        row = {
            "host": host,
            "url": url,
            "client": label,
            "status": v.status,
            "why": why,
            "allows": bool(allowed),
            "http_status": v.http_status,
        }
        delay = v.crawl_delay(agent) if v.policy else None
        if delay:
            row["crawl_delay"] = delay
        signal = v.content_signal(agent) if v.policy else None
        if signal:
            row["content_signal"] = signal
        return row

    readings = []
    for i in range(max(1, int(reads))):
        if i and gap:
            time.sleep(gap)
        readings.append(one_read())
    if len(readings) == 1:
        return readings[0]
    row = dict(_most_restrictive(readings))
    row["reads"] = len(readings)
    row["gap_seconds"] = gap
    row["readings"] = [{k: r[k] for k in ("status", "why", "allows", "http_status")
                        if k in r} for r in readings]
    return row


# Worst first: a challenge outranks everything, then a read nobody could take,
# then a policy that refuses, and a plain allow is the answer only when every
# reading gave one.
_READING_RANK = ("challenge", "error", "unreachable")


def _most_restrictive(readings):
    for status in _READING_RANK:
        for r in readings:
            if r["status"] == status:
                return r
    for r in readings:
        if not r["allows"]:
            return r
    return readings[0]


def vantage():
    try:
        host = socket.gethostname()
    except Exception:
        host = "unknown"
    return "%s on %s" % (os.environ.get("GITHUB_ACTIONS")
                         and "GitHub Actions runner" or "local/sandbox", host)


def run(args):
    inventory = ua.build_inventory()
    measured = read_verdicts().get("hosts", {})
    hosts = subject(inventory)
    targeted = bool(args.host)
    if targeted:
        hosts = [h for h in hosts if h in set(args.host)]
    # A TARGETED RUN MERGES; IT USED TO REPLACE. `--host` wrote a record holding
    # only the hosts it asked about, so re-measuring one host deleted the other
    # 508 -- and `--check` passed, because it fails on a host in the record that
    # nothing fetches and only COUNTS the ones missing from it. So the one flag
    # meant for settling a single host's disputed reading threw away every other
    # host's, silently, on the honest path.
    previous = {}
    if targeted:
        if not os.path.exists(args.out):
            print("probe-robots-verdicts: --host re-measures one host inside an "
                  "existing record and %s has not been written yet; run the full "
                  "sweep first" % os.path.basename(args.out), file=sys.stderr)
            return 1
        previous = json.load(open(args.out, encoding="utf-8"))
    rows = dict(previous.get("hosts", {}))
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(probe_host, h, url_for(inventory, h),
                        (measured.get(h) or {}).get("verdict", ""),
                        args.reads, args.gap): h
            for h in hosts
        }
        for fut in concurrent.futures.as_completed(futures):
            row = fut.result()
            if targeted:
                # The file's own `measured`/`vantage` describe the sweep that
                # wrote most of it, so a row taken on its own day carries its
                # own stamp rather than restating the file's.
                row["measured"] = datetime.date.today().isoformat()
                row["vantage"] = vantage()
            rows[row["host"]] = row
            print("  %-42s %-7s %s" % (row["host"],
                                       "allow" if row["allows"] else "REFUSE",
                                       row["why"][:90]))
    payload = {
        "measured": previous.get("measured") if targeted
                    else datetime.date.today().isoformat(),
        "vantage": previous.get("vantage") if targeted else vantage(),
        "subject": "robots.txt of every host the tree fetches, read with the "
                   "client user-agent-measurements.json records as serving it",
        "summary": {
            "hosts": len(rows),
            "allow": sum(1 for r in rows.values() if r["allows"]),
            "refuse": sum(1 for r in rows.values() if not r["allows"]),
            "unreadable": sum(1 for r in rows.values()
                              if r["status"] in ("unreachable", "error")),
        },
        "hosts": dict(sorted(rows.items())),
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=False)
        fh.write("\n")
    print("probe-robots-verdicts: wrote %s — %d host(s), %d allow, %d refuse, "
          "%d unreadable, from %s"
          % (args.out, payload["summary"]["hosts"], payload["summary"]["allow"],
             payload["summary"]["refuse"], payload["summary"]["unreadable"],
             payload["vantage"]))
    return 0


def check(args):
    """Offline audit: the record still describes the tree it was taken over."""
    # THE PINNED-CHAIN AUDIT RUNS WHETHER OR NOT THE RECORD EXISTS, because it is
    # a claim about the tree rather than about the measurement: an entry that has
    # stopped describing a scraper is wrong on the day that scraper changes, not
    # on the day somebody next dispatches the probe.
    stale = audit_pinned_chains()
    if stale:
        print("probe-robots-verdicts: FAIL — PINNED_CHAINS no longer describes "
              "the tree\n    %s" % "\n    ".join(stale), file=sys.stderr)
        return 1
    if not os.path.exists(args.out):
        print("probe-robots-verdicts: SKIP — %s has not been measured yet; "
              "dispatch .github/workflows/probe-robots-verdicts.yml to take it "
              "from a runner (%d pinned chain(s) verified)"
              % (os.path.basename(args.out), len(PINNED_CHAINS)))
        return 0
    payload = json.load(open(args.out, encoding="utf-8"))
    rows = payload.get("hosts", {})
    hosts = set(subject(ua.build_inventory()))
    problems = []
    for host in sorted(set(rows) - hosts):
        problems.append("%s is in the record and nothing in the tree fetches it "
                        "— remove the entry" % host)
    missing = sorted(hosts - set(rows))
    if problems:
        print("probe-robots-verdicts: FAIL\n    %s" % "\n    ".join(problems),
              file=sys.stderr)
        return 1
    print("probe-robots-verdicts: OK — %d host(s) recorded %s from %s; %d in "
          "the tree not yet measured; %d pinned chain(s) verified"
          % (len(rows), payload.get("measured"), payload.get("vantage"),
             len(missing), len(PINNED_CHAINS)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="offline audit of the record against the tree")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--host", action="append",
                    help="re-measure only this host inside the existing record "
                         "(repeatable); every other host's row is kept")
    ap.add_argument("--reads", type=int, default=1,
                    help="read this host's robots.txt this many times and report "
                         "the most restrictive reading, keeping them all — the "
                         "deliberate re-measurement a challenge-fronted host needs")
    ap.add_argument("--gap", type=float, default=15,
                    help="seconds between repeated reads (default 15, the fleet's "
                         "own bar for a deliberate re-measurement)")
    args = ap.parse_args(argv)
    return check(args) if args.check else run(args)


if __name__ == "__main__":
    sys.exit(main())
