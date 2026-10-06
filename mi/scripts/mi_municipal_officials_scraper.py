#!/usr/bin/env python3
"""
Scrape stage 1: the elected boards of Michigan's large cities and townships,
each from the unit's own website, cached for build_mi_municipal_officials.py.

WHY THESE UNITS. The done standard (docs/DONE_STANDARD.md) asks that a reader
inside any general-purpose local government over 25,000 people be told who
governs it. In Michigan that is 48 cities and 34 townships (the township
counts because a Michigan township is a general-purpose government in its own
right, MCL 41.61 and 42.3). On 2026-10-01 every one of them was surveyed for a
page naming its council, commission or board; the units here are the ones
whose own page names every seat. The rest are recorded, unit by unit, in the
`mi-municipal-officeholders` and `mi-township-officers` gap records.

THE UNITS AND THEIR PARSERS LIVE IN FOUR SIBLING MODULES, described in
mi_municipal_common.py, so a batch can be fixed without touching the others.
The fourth, mi_municipal_parsers_browser.py, holds the two townships whose
sites serve only a browser-class client, with the measurement that licenses it.
Detroit, Grand Rapids, Jackson and Battle Creek are not in them: each already
has its own weekly roster, read for the City Council District card.

FETCH RULES. Every URL is asked of its host's robots.txt first, with the same
client that then fetches it, and a stated Crawl-delay is honoured per host. For
almost every unit that client is the fleet's roster token on one `requests`
session. A unit that carries `headers` is read, robots.txt included, with
exactly those headers on the stdlib client instead, because that is the only
client its host was measured to serve. A refusal, a 403 or a
managed challenge is recorded as what it is and the host is left alone; a
captcha is never worked around and no other client is tried.

A UNIT THAT WAS NOT READ IS RECORDED, NOT DROPPED. The builder carries it
forward on its last good read, per Adam's 2026-09-19 ruling that a refusal
stops the fetch and never unpublishes what was fetched legitimately.

Usage:
    python3 mi/scripts/mi_municipal_officials_scraper.py            # every unit
    python3 mi/scripts/mi_municipal_officials_scraper.py --unit 2684000
    python3 mi/scripts/mi_municipal_officials_scraper.py --list
    python3 mi/scripts/mi_municipal_officials_scraper.py --unit 2684000 --dry-run
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("mi-municipal-officials-scraper: FAIL — requests is not installed "
          "(pip install -c mi/scripts/requirements.txt requests)", file=sys.stderr)
    raise SystemExit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from robots_gate import RobotsGate, HostPacer  # noqa: E402
from mi_municipal_common import (UA_ROSTER_BOT, strip_comments,  # noqa: E402
                                 check_roster)
import mi_municipal_parsers_cities_a  # noqa: E402
import mi_municipal_parsers_cities_b  # noqa: E402
import mi_municipal_parsers_townships  # noqa: E402
import mi_municipal_parsers_browser  # noqa: E402

CACHE = os.path.join(HERE, ".cache", "mi_municipal_officials.json")
TIMEOUT = 60
LABEL = "mi-municipal-officials-scraper"


def all_units():
    units = (mi_municipal_parsers_cities_a.UNITS
             + mi_municipal_parsers_cities_b.UNITS
             + mi_municipal_parsers_townships.UNITS
             + mi_municipal_parsers_browser.UNITS)
    seen = set()
    for u in units:
        for key in ("geoid", "name", "kind", "body", "url", "seats", "parse"):
            if key not in u:
                raise SystemExit("%s: FAIL — unit %r has no %r" % (LABEL, u.get("name"), key))
        if u["kind"] not in ("city", "township"):
            raise SystemExit("%s: FAIL — %s: kind %r" % (LABEL, u["name"], u["kind"]))
        if u["geoid"] in seen:
            raise SystemExit("%s: FAIL — geoid %s appears twice" % (LABEL, u["geoid"]))
        seen.add(u["geoid"])
    return units


def ua_session():
    s = requests.Session()
    s.headers["User-Agent"] = UA_ROSTER_BOT
    return s


def read_page(url, session, gate, pacer, headers=None):
    """(response, why, kind, gate, pacer). Same shape and the same retry rules
    as mi_commissioner_scraper.read_page: only an unreachable robots.txt and a
    transport failure are retried; a refusal, an HTTP status and a challenge
    are answers. A gate caches its verdict per site, so each robots retry
    needs a fresh gate and pacer, which come back to the caller."""
    verdict = gate.verdict(url)
    for attempt in range(5):
        if verdict.status != "unreachable":
            break
        time.sleep(2 * (attempt + 1))
        gate = RobotsGate(session, UA_ROSTER_BOT)
        pacer = HostPacer(gate)
        verdict = gate.verdict(url)
    allowed, why = verdict.allows(UA_ROSTER_BOT, url)
    if not allowed:
        return None, "robots %s: %s" % (verdict.status, why), "robots", gate, pacer
    resp, last = None, None
    for attempt in range(3):
        try:
            with pacer.hold(url):
                resp = session.get(url, timeout=TIMEOUT, headers=headers)
            break
        except Exception as exc:                              # noqa: BLE001
            last = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    if resp is None:
        return None, "FETCH FAILED after 3 tries — %s" % last, "fetch", gate, pacer
    if resp.status_code != 200:
        marker = (resp.headers.get("Cf-Mitigated")
                  or ("cloudflare" if resp.headers.get("Server", "").lower()
                      == "cloudflare" and resp.status_code == 403 else ""))
        how = (" — Cloudflare managed challenge (%s), an access control" % marker
               if marker else "")
        return (None, "HTTP %s (%d bytes)%s" % (resp.status_code, len(resp.content), how),
                "challenge" if marker else "fetch", gate, pacer)
    # requests follows a redirect; each hop's host must permit us too.
    if resp.history:
        for hop in [r.url for r in resp.history[1:]] + [resp.url]:
            ok, why2 = gate.verdict(hop).allows(UA_ROSTER_BOT, hop)
            if not ok:
                return (None, "robots on redirect target %s: %s" % (hop, why2),
                        "robots", gate, pacer)
    return resp, None, None, gate, pacer


class _Page(object):
    """The two attributes scrape() reads, for a page read on the stdlib client."""

    def __init__(self, text, url):
        self.text, self.url = text, url


def read_page_stdlib(url, headers, gate):
    """(page, why, kind) for a unit carrying its own `headers`: robots.txt is
    read with those headers on the stdlib client (the gate was built with
    them), then the page with the same. One attempt per page, the shape
    scraper_common.fetch_stdlib takes: a refusal is an answer, and nothing
    thinner is tried after one."""
    ua = headers["User-Agent"]
    ok, why = gate.allows(url)
    if not ok:
        return None, "robots %s" % why, "robots"
    req = urllib.request.Request(url, headers=dict(headers))
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body, final = resp.read().decode("utf-8", "replace"), resp.geturl()
    except urllib.error.HTTPError as exc:
        marker = exc.headers.get("Cf-Mitigated") if exc.headers else None
        how = (" — Cloudflare managed challenge (%s), an access control" % marker
               if marker else "")
        return (None, "HTTP %s on the stdlib client%s" % (exc.code, how),
                "challenge" if marker else "fetch")
    except Exception as exc:                                  # noqa: BLE001
        return None, "FETCH FAILED — %s" % exc, "fetch"
    if final != url:
        ok2, why2 = gate.verdict(final).allows(ua, final)
        if not ok2:
            return None, "robots on redirect target %s: %s" % (final, why2), "robots"
    return _Page(body, final), None, None


HCMS_CONF = re.compile(r'hcmsReadOnlyConfiguration:\{baseUrl:"([a-z0-9.-]+)",appName:"([a-z0-9-]+)"')
HCMS_TOKEN = re.compile(r'hcmsClientToken="(Bearer [A-Za-z0-9._-]+)"')
HCMS_PAGE = 200
HCMS_MAX_PAGES = 10


def read_hcms(unit, page_html, read, gate, pacer):
    """(json_text, why, kind, gate, pacer) for a unit whose page draws its
    members from the CivicPlus content service rather than its own HTML.

    The service's address, the site's app name and a read-only key are all
    written into the page every visitor is served. Measured on Lansing's page
    on 2026-10-06: the key is issued to the client "<app>:default" with read
    scopes only, to a visitor the page itself records as not logged in, and is
    reissued with each page. It is the access every browser opening the page
    is given, not a sign-in, so it is read from the page on each run and
    never stored. Each request still asks the service host's robots.txt first,
    with the same client, through the same `read` as every other page.

    The whole schema is read, paged, and the parser picks the council out of
    it, because that is the filter the page applies and the service's own
    query language for categories was not measured."""
    conf, tok = HCMS_CONF.search(page_html), HCMS_TOKEN.search(page_html)
    if not conf or not tok:
        return (None, "the page no longer carries its content-service address and key",
                "parse", gate, pacer)
    base, app = conf.group(1), conf.group(2)
    headers = {"Authorization": tok.group(1), "Accept": "application/json"}
    items, total = [], None
    for n in range(HCMS_MAX_PAGES):
        url = "https://%s/api/content/%s/%s?$top=%d&$skip=%d" % (
            base, app, unit["hcms"]["schema"], HCMS_PAGE, n * HCMS_PAGE)
        resp, why, kind, gate, pacer = read(url, gate, pacer, headers)
        if resp is None:
            return None, "content service %s — %s" % (url, why), kind, gate, pacer
        try:
            body = json.loads(resp.text)
        except ValueError:
            return None, "content service answered something not JSON", "parse", gate, pacer
        items += body.get("items") or []
        total = body.get("total")
        if not body.get("items") or total is None or len(items) >= total:
            break
    else:
        return (None, "content service still paging after %d pages" % HCMS_MAX_PAGES,
                "parse", gate, pacer)
    if total is None or len(items) != total:
        return (None, "content service gave %d items of %r" % (len(items), total),
                "parse", gate, pacer)
    return json.dumps({"items": items}), None, None, gate, pacer


def scrape(unit, session, gate, pacer, header_gates):
    """(roster, why, kind, gate, pacer)."""
    if unit.get("headers"):
        headers = unit["headers"]
        key = tuple(sorted(headers.items()))
        if key not in header_gates:
            header_gates[key] = RobotsGate(None, headers["User-Agent"], headers=headers)
        hgate = header_gates[key]

        def read(u, g, p):
            page, why_, kind_ = read_page_stdlib(u, headers, hgate)
            return page, why_, kind_, g, p
    else:
        read = lambda u, g, p, h=None: read_page(u, session, g, p, h)  # noqa: E731
    resp, why, kind, gate, pacer = read(unit["url"], gate, pacer)
    if resp is None:
        return None, why, kind, gate, pacer
    also = []
    if unit.get("hcms"):
        if unit.get("headers"):
            raise SystemExit("%s: FAIL — %s: hcms on the stdlib client is not built"
                             % (LABEL, unit["name"]))
        data, why, kind, gate, pacer = read_hcms(unit, resp.text, read, gate, pacer)
        if data is None:
            return None, why, kind, gate, pacer
        also.append(data)
    for extra in unit.get("also") or []:
        r2, why2, kind2, gate, pacer = read(extra, gate, pacer)
        if r2 is None:
            return (None, "second page %s not read — %s" % (extra, why2), kind2,
                    gate, pacer)
        also.append(strip_comments(r2.text))
    try:
        roster = check_roster(unit, unit["parse"](strip_comments(resp.text), also))
    except ValueError as exc:
        return None, "PARSE REFUSED — %s" % exc, "parse", gate, pacer
    return roster, None, None, gate, pacer


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--unit", action="append", help="scrape one unit by geoid (repeatable)")
    ap.add_argument("--list", action="store_true", help="list the units and exit")
    ap.add_argument("--dry-run", action="store_true",
                    help="read and print, write nothing (for testing a parser)")
    args = ap.parse_args()

    units = all_units()
    if args.list:
        for u in units:
            print("%-10s %-9s %-28s %2d  %s" % (u["geoid"], u["kind"], u["name"], u["seats"], u["url"]))
        print("%d units" % len(units))
        return 0
    wanted = [u for u in units if not args.unit or u["geoid"] in args.unit]
    if not wanted:
        print("%s: FAIL — no unit matches %r" % (LABEL, args.unit), file=sys.stderr)
        return 1

    session = ua_session()
    gate = RobotsGate(session, UA_ROSTER_BOT)
    pacer = HostPacer(gate)
    read_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entries, unread, header_gates = {}, [], {}
    for u in wanted:
        roster, why, kind, gate, pacer = scrape(u, session, gate, pacer, header_gates)
        if roster is None:
            unread.append({"geoid": u["geoid"], "name": u["name"], "why": why, "kind": kind})
            print("  %-22s %s" % (u["name"], why))
            continue
        entry = {
            "name": u["name"],
            "kind": u["kind"],
            "body": u["body"],
            "seats": u["seats"],
            "members": roster["members"],
            "sourceUrl": u["url"],
            "readAt": read_date,
        }
        if roster.get("vacant"):
            entry["vacant"] = roster["vacant"]
        if roster.get("office"):
            entry["office"] = roster["office"]
        entries[u["geoid"]] = entry
        print("  %-22s %2d/%2d named%s" % (u["name"], len(roster["members"]), u["seats"],
                                           " (%d vacant)" % len(roster.get("vacant") or [])
                                           if roster.get("vacant") else ""))

    if args.dry_run:
        print(json.dumps({"units": entries, "unread": unread}, indent=1, ensure_ascii=False))
        return 0 if not unread else 1
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    if args.unit and os.path.exists(CACHE):
        # --unit MERGES; a full run REPLACES (mi_commissioner_scraper.py's rule,
        # and its unread-list lesson: an unread row stays until a run reads it).
        with open(CACHE) as fh:
            prior = json.load(fh)
        for g, e in (prior.get("units") or {}).items():
            if g not in entries and g not in {x["geoid"] for x in unread}:
                entries[g] = e
        for row in prior.get("unread") or []:
            if row["geoid"] not in entries and row["geoid"] not in {x["geoid"] for x in unread}:
                unread.append(row)
    payload = {
        "scrapedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "userAgent": UA_ROSTER_BOT,
        "units": dict(sorted(entries.items())),
        "unread": sorted(unread, key=lambda x: x["geoid"]),
    }
    with open(CACHE, "w") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("%s: %d of %d unit(s) read, %d not read; wrote %s"
          % (LABEL, len([g for g in entries if g in {u['geoid'] for u in wanted}]),
             len(wanted), len(unread), os.path.relpath(CACHE)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
