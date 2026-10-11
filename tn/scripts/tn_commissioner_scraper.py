#!/usr/bin/env python3
"""
Scrape stage 1: who sits on each Tennessee county's legislative body, by
district, read from each county's own published page, cached for
build_tn_commissioner_roster.py (stage 2).

WHY THIS EXISTS
----------------
tn/data/app/tn-commission-districts.json draws all 859 county commission
districts in 95 counties and names nobody, because no state office publishes
who holds them: the Comptroller of the Treasury's statewide layer carries no
member field, and the Division of Elections' results of the 6 August 2026
election carry 219 offices and no county race. The University of Tennessee's
County Technical Assistance Service keeps a list of commissioners with no
districts; it is not a government publication and nothing here reads it. So
the names come from each county, a TRANCHE of counties at a time, and the
weekly run re-reads every county that has a module in tn_commission_parsers/
(one module per county, discovered, so there is no list here to keep in step).

A DISTRICT IS NOT A SEAT. Most Tennessee counties elect two or three
commissioners from one district, some an uneven number (Blount 2 everywhere
but District 4, which elects 3), and Knox and Davidson also elect members
countywide. Each county's module states the seats per district AS THE
COUNTY ELECTS THEM (`SEATS`) and the countywide seats (`AT_LARGE`), read off
the county's own page on the day the parser was written and checked against
that county's August 2026 results, or the county's own record of the new
commission where those results cannot be read. The builder refuses a county whose parse
does not match its module exactly, so a board resize
or a redistricting turns the run red rather than shipping a roster keyed to
lines that moved.

CURRENCY WAS CHECKED BEFORE A COUNTY JOINED, AND IT IS WHY SOME DID NOT.
Terms began 1 September 2026. The survey of 2026-10-11 found six county pages
still listing members from before that date, so a county joins only once its
page's names match its own August 2026 results, and what each county was
checked against is recorded in its module's docstring. Where no results can be
read on a government host (a results file behind a robots.txt refusal, or none
published), a county joins on county documents from after 1 September 2026
instead — a roster headed with the new term, the new commission's minutes or
committee list, an election commission's list of officeholders — and its
docstring says which, and what they did NOT establish. Five counties were held
back on 2026-10-11 for failing this; tn/WATCH.md names them and why.

THE CLIENT, AND WHAT IT ASKS FIRST
-----------------------------------
Every host's robots.txt is read through scripts/robots_policy.py with
UA_ROSTER_BOT and the header set it crawls with BEFORE the first page fetch,
and again at every redirect hop, and a stated Crawl-delay is honoured per
host by HostPacer, with what it honoured printed at the end of the run. No
county here needs a browser user-agent: every one served this project's own
token its page on the day it joined. A managed challenge (Cloudflare says so in its own `Cf-Mitigated`
header) is an access control and is never worked around; a county that
answers with one is recorded as unread and the builder carries its last good
record forward.

PRIVACY. Many of these pages print each commissioner's home address and home
or cell telephone beside the name. No parser reads an address, a town or a ZIP
code; an e-mail is kept only on the county's own domain (`DOMAINS`); and a
telephone is kept only where the page makes plain it is a government office
line. A module keeps a phone only where it says PHONES = True, and the
builder refuses a record that breaks any of this, whatever a parser returns.

NO PARSER INFERS A DISTRICT FROM LIST ORDER. Each pairs a name with the
district label inside the same block, row or heading, and raises ValueError
when the page is not shaped the way it was when the parser was written.

Usage:
    python3 tn/scripts/tn_commissioner_scraper.py               # every county
    python3 tn/scripts/tn_commissioner_scraper.py --county Knox # one, merged
    python3 tn/scripts/build_tn_commissioner_roster.py
"""

import argparse
import importlib
import json
import os
import pkgutil
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
# APPENDED, not inserted: tn/scripts carries modules of its own whose names the
# shared directory also uses, and an instance file must resolve its own first.
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(HERE)), "scripts"))
from robots_policy import RobotsGate, HostPacer  # noqa: E402  (FLEET_SHARED)
from scraper_common import UA_ROSTER_BOT, UA_HEADERS_ROSTER_BOT  # noqa: E402  (FLEET_SHARED)
from tn_commission_parsers._common import strip_comments  # noqa: E402  (same tree)

CACHE = os.path.join(HERE, ".cache", "tn_commissioner_roster.json")
TIMEOUT = 60


# ——— the counties ———
#
# ONE MODULE PER COUNTY in tn_commission_parsers/, and a county joins by having
# one: this table is DISCOVERED from that package, so there is no second list to
# keep in step with it. The package's own docstring says what a module states.

def load_counties():
    import tn_commission_parsers as pkg
    rows = []
    for info in sorted(pkgutil.iter_modules(pkg.__path__), key=lambda m: m.name):
        if info.name.startswith("_"):
            continue
        mod = importlib.import_module("tn_commission_parsers." + info.name)
        rows.append({"fips": mod.FIPS, "county": mod.COUNTY, "parse": mod.parse,
                     "urls": list(mod.URLS), "seats": dict(mod.SEATS),
                     "source": getattr(mod, "SOURCE_URL", mod.URLS[0]),
                     "at_large": mod.AT_LARGE, "domains": list(mod.DOMAINS),
                     "phones": bool(getattr(mod, "PHONES", False)),
                     "title": getattr(mod, "TITLE", None),
                     "body": getattr(mod, "BODY", None), "module": info.name})
    seen = {}
    for row in rows:
        # TITLE and BODY are words a card prints. A parser is free to keep a
        # compiled pattern of its own, and the obvious name for one that reads
        # a member's title line is TITLE: three of the second tranche's twenty
        # did exactly that (2026-10-11), and the module would have handed the
        # roster a regex object as the seat title.
        for key in ("title", "body"):
            if row[key] is not None and not isinstance(row[key], str):
                raise SystemExit("tn-commissioner-scraper: FAIL - %s.%s is %s, not text; "
                                 "name a pattern of your own something else"
                                 % (row["module"], key.upper(), type(row[key]).__name__))
        if row["fips"] in seen:
            raise SystemExit("tn-commissioner-scraper: FAIL - %s and %s both claim "
                             "county %s" % (seen[row["fips"]], row["module"], row["fips"]))
        seen[row["fips"]] = row["module"]
    return tuple(rows)


COUNTIES = load_counties()
COUNTY_BY_NAME = {c["county"]: c for c in COUNTIES}


def ua_session():
    s = requests.Session()
    s.headers.update(UA_HEADERS_ROSTER_BOT)
    s.headers["User-Agent"] = UA_ROSTER_BOT
    return s


MAX_HOPS = 5


def _robots(url, session, gate, pacer):
    """The robots verdict for one URL, re-asked up to three times when the file
    itself could not be read (an unreadable robots.txt disallows, and one
    flaky read must not drop a county for a week)."""
    verdict = gate.verdict(url)
    for attempt in range(3):
        if verdict.status != "unreachable":
            break
        time.sleep(2 * (attempt + 1))
        gate = RobotsGate(session, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
        pacer = HostPacer(gate)
        verdict = gate.verdict(url)
    allowed, why = verdict.allows(UA_ROSTER_BOT, url)
    return allowed, "robots %s: %s" % (verdict.status, why), gate, pacer


def read_page(url, session, gate, pacer):
    """Robots verdict, then the page. -> (response, why, kind, gate, pacer).

    `response` is None when the page was not read and `why` says so; `kind` is
    "robots" for a refusal, "challenge" for a managed challenge, or "fetch" for
    a failure that says nothing about the county's policy. Only a transport
    failure is retried: a robots refusal and an HTTP status are answers.

    REDIRECTS ARE FOLLOWED ONE HOP AT A TIME, and robots.txt is asked again at
    every hop, because a redirect can hand the request to another host (a
    county site's vendor, a document store) whose policy is its own.
    """
    hops = 0
    while True:
        allowed, why, gate, pacer = _robots(url, session, gate, pacer)
        if not allowed:
            return None, why, "robots", gate, pacer
        resp, last = None, None
        for attempt in range(3):
            try:
                with pacer.hold(url):
                    resp = session.get(url, timeout=TIMEOUT, allow_redirects=False)
                break
            except requests.RequestException as exc:
                last = exc
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
        if resp is None:
            return None, "FETCH FAILED after 3 tries - %s" % last, "fetch", gate, pacer
        if resp.status_code in (301, 302, 303, 307, 308) and resp.headers.get("Location"):
            hops += 1
            if hops > MAX_HOPS:
                return None, "more than %d redirects" % MAX_HOPS, "fetch", gate, pacer
            nxt = urljoin(url, resp.headers["Location"])
            if urlsplit(nxt).scheme != "https":
                return (None, "redirected off https to %s" % nxt, "fetch", gate, pacer)
            url = nxt
            continue
        break
    if resp.status_code != 200:
        # Cloudflare names a managed challenge in its own header; asking the
        # header rather than searching the body for "captcha" is the lesson
        # scripts/probe_user_agents.py records.
        marker = (resp.headers.get("Cf-Mitigated")
                  or ("cloudflare" if resp.headers.get("Server", "").lower()
                      == "cloudflare" and resp.status_code == 403 else ""))
        how = (" - Cloudflare managed challenge (%s), an access control" % marker
               if marker else "")
        return (None, "HTTP %s (%d bytes)%s" % (resp.status_code, len(resp.content), how),
                "challenge" if marker else "fetch", gate, pacer)
    return resp, None, None, gate, pacer


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--county", help="scrape one county by name and merge it into the cache")
    args = ap.parse_args()

    wanted = [c for c in COUNTIES
              if not args.county or c["county"].lower() == args.county.lower()]
    if not wanted:
        print("tn-commissioner-scraper: FAIL - no county named %r; known: %s"
              % (args.county, ", ".join(c["county"] for c in COUNTIES)), file=sys.stderr)
        return 1

    session = ua_session()
    gate = RobotsGate(session, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    pacer = HostPacer(gate)
    read_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entries, unread = {}, []
    for spec in wanted:
        county = spec["county"]
        pages, failed = {}, None
        for url in spec["urls"]:
            resp, why, kind, gate, pacer = read_page(url, session, gate, pacer)
            if resp is None:
                failed = (why, kind)
                break
            resp.encoding = resp.encoding or "utf-8"
            pages[url] = strip_comments(resp.text)
        if failed:
            # A COUNTY THAT WAS NOT READ IS RECORDED, NOT DROPPED, so the
            # builder can carry its last good record forward (the operator's
            # ruling of 2026-09-19: a refusal stops the fetch and never
            # unpublishes what was already read).
            unread.append({"fips": spec["fips"], "county": county,
                           "why": failed[0], "kind": failed[1]})
            print("  %-10s NOT READ - %s" % (county, failed[0]))
            continue
        try:
            parsed = spec["parse"](pages)
        except (ValueError, KeyError, IndexError) as exc:
            unread.append({"fips": spec["fips"], "county": county,
                           "why": "PARSE REFUSED - %s" % exc, "kind": "parse"})
            print("  %-10s PARSE REFUSED - %s" % (county, exc))
            continue
        districts = parsed.get("districts") or {}
        entries[spec["fips"]] = {
            "county": county,
            "sourceUrl": spec["source"],
            "seatsByDistrict": spec["seats"],
            "atLargeSeats": spec["at_large"],
            "domains": spec["domains"],
            "phones": bool(spec.get("phones")),
            "seatTitle": spec.get("title") or "Commissioner",
            "bodyName": spec.get("body") or "County Commission",
            "districts": districts,
            "atLarge": parsed.get("atLarge") or [],
            # PER COUNTY, never the run's own timestamp: --county merges, so a
            # global stamp would date every county to a run that read one.
            "readAt": read_date,
        }
        print("  %-10s %2d districts, %3d seats, %d at-large (%s)"
              % (county, len(districts), sum(len(v) for v in districts.values()),
                 len(parsed.get("atLarge") or []), spec["urls"][0]))

    if args.county and os.path.exists(CACHE):
        # --county MERGES; a full run REPLACES, and its `unread` list is what
        # lets the builder tell a county not read from one nobody tracks.
        with open(CACHE) as handle:
            prior = json.load(handle)
        for fips, entry in (prior.get("counties") or {}).items():
            entries.setdefault(fips, entry)
        for row in prior.get("unread") or []:
            if row.get("fips") not in entries and \
                    row.get("fips") not in {u["fips"] for u in unread}:
                unread.append(row)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w") as handle:
        json.dump({"scrapedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "userAgent": UA_ROSTER_BOT, "counties": entries,
                   "unread": sorted(unread, key=lambda u: u["fips"])},
                  handle, indent=1, sort_keys=True)
        handle.write("\n")
    for line in pacer.report():
        print(line)
    print("tn-commissioner-scraper: %d counties read, %d not read -> %s"
          % (len(entries), len(unread), os.path.relpath(CACHE, os.path.dirname(HERE))))
    return 0 if entries else 1


if __name__ == "__main__":
    raise SystemExit(main())
