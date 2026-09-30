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


def client_for(verdict):
    """(label, user_agent, headers) — the client this host is crawled with."""
    if verdict in BROWSER_VERDICTS:
        headers = dict(sc.UA_HINTS_CHROME_126)
        headers["User-Agent"] = sc.UA_CHROME_WIN_126
        return "chrome+hints", sc.UA_CHROME_WIN_126, headers
    return "token", sc.UA_ROSTER_BOT, {"User-Agent": sc.UA_ROSTER_BOT}


def read_verdicts(path=MEASUREMENTS):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def probe_host(host, url, verdict_kind):
    label, agent, headers = client_for(verdict_kind)
    # The scheme of the url a scraper actually reads, because a host served over
    # http publishes its policy there and asking https would measure a different
    # server or none at all.
    scheme = urlsplit(url).scheme or "https"
    robots_url = "%s://%s/robots.txt" % (scheme, host)
    try:
        v = robots_policy.fetch_verdict(robots_url, agent, headers=headers)
    except Exception as exc:                      # a reader error is a reading
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
    hosts = sorted(ua.subject_hosts(inventory))
    if args.host:
        hosts = [h for h in hosts if h in set(args.host)]
    rows = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(probe_host, h, ua.choose_url(inventory[h]),
                        (measured.get(h) or {}).get("verdict", "")): h
            for h in hosts
        }
        for fut in concurrent.futures.as_completed(futures):
            row = fut.result()
            rows[row["host"]] = row
            print("  %-42s %-7s %s" % (row["host"],
                                       "allow" if row["allows"] else "REFUSE",
                                       row["why"][:90]))
    payload = {
        "measured": datetime.date.today().isoformat(),
        "vantage": vantage(),
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
    if not os.path.exists(args.out):
        print("probe-robots-verdicts: SKIP — %s has not been measured yet; "
              "dispatch .github/workflows/probe-robots-verdicts.yml to take it "
              "from a runner" % os.path.basename(args.out))
        return 0
    payload = json.load(open(args.out, encoding="utf-8"))
    rows = payload.get("hosts", {})
    hosts = set(ua.subject_hosts(ua.build_inventory()))
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
          "the tree not yet measured"
          % (len(rows), payload.get("measured"), payload.get("vantage"),
             len(missing)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="offline audit of the record against the tree")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--host", action="append",
                    help="measure only this host (repeatable)")
    args = ap.parse_args(argv)
    return check(args) if args.check else run(args)


if __name__ == "__main__":
    sys.exit(main())
