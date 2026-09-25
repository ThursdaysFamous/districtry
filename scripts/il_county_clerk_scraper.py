#!/usr/bin/env python3
"""
Illinois County Clerk Scraper (ISBE election-authority directory)
=================================================================
Extracts every Illinois county clerk (name + office address + phone + email)
from the State Board of Elections' own election-authority directory at
elections.il.gov/ElectionOperations/ElectionAuthorities.aspx.

Why this source: the county card is the app's statewide TIGERweb county
layer, so surfacing the clerk needs an authoritative directory covering all
102 counties at once — and ISBE maintains exactly that, because every county
clerk is an election authority under 10 ILCS 5. The page is an ASP.NET
postback form whose county dropdown includes an "All Election Authorities"
option (-1): one GET for the form tokens + one POST returns the complete
directory as a single GridView table (Jurisdiction | Name | Title | Email |
Address | Phone | Fax), 108 rows = 102 county clerks + the municipal boards
of election commissioners (Jurisdiction "CITY OF …"), which the builder
filters out.

Emails are Cloudflare-obfuscated (`data-cfemail`) and decoded with the
standard XOR scheme (first byte is the key).

FETCH POSTURE (measured 2026-07-28, after the weekly run began failing on
2026-07-25): the site is Cloudflare-fronted and now 403s GitHub's runner
network while still answering a developer machine 200 for a byte-identical
request — the DuPage class of block, keyed on the client's network rather than
its fingerprint. So `requests` works in development and cannot be relied on in
CI, and the ladder is requests -> playwright.

The browser rung does NOT replay the postback. The county dropdown carries an
ASP.NET AutoPostBack, so selecting the option IS the submit and the browser
produces __VIEWSTATE/__EVENTVALIDATION itself. That makes the fallback both the
answer to the edge block and structurally sturdier than the primary rung —
nothing in it can drift out of sync with the form's tokens.

This is the build-time half of the usual two-stage roster pattern; the raw
output is resolved into data/app/il-county-clerks.json by
scripts/build_county_clerk_roster.py.

Usage:
    python3 il_county_clerk_scraper.py --out il_county_clerks.json
    python3 il_county_clerk_scraper.py --engine playwright   # forced rung

Notes on data honesty (per project conventions):
- Fields that can't be parsed are stored as null, never guessed.
- Every record includes `source_url` and `scraped_at` for traceability.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from scraper_common import UA_CHROME_WIN_124, require_robots_allowed  # noqa: E402  (shared machinery — do not fork)

URL = "https://www.elections.il.gov/ElectionOperations/ElectionAuthorities.aspx"
HEADERS = {
    "User-Agent": UA_CHROME_WIN_124,
}
REQUEST_TIMEOUT = 40


def decode_cfemail(enc):
    """Cloudflare email obfuscation: hex string, first byte XOR key."""
    try:
        key = int(enc[:2], 16)
        return "".join(chr(int(enc[i:i + 2], 16) ^ key) for i in range(2, len(enc), 2))
    except (ValueError, IndexError):
        return None


def cell_text(td):
    return " ".join(td.get_text(" ", strip=True).split()) or None


def cell_email(td):
    a = td.find(attrs={"data-cfemail": True})
    if a is not None:
        return decode_cfemail(a["data-cfemail"])
    m = td.find("a", href=re.compile(r"^mailto:", re.IGNORECASE))
    if m is not None:
        return m["href"].split(":", 1)[1].split("?")[0].strip() or None
    return cell_text(td)


RESULTS_TABLE_ID = "ContentPlaceHolder1_gvAllJurisdictions"
COUNTY_SELECT_ID = "ContentPlaceHolder1_ddlCounty"
ALL_AUTHORITIES = "-1"


def rung_requests():
    """Replay the ASP.NET postback directly: GET the form, carry its three
    tokens into a POST that selects "All Election Authorities"."""
    session = requests.Session()
    form = session.get(URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    form.raise_for_status()
    soup = BeautifulSoup(form.text, "html.parser")

    def token(name):
        el = soup.find(id=name)
        if el is None or not el.get("value"):
            raise RuntimeError("ASP.NET form token %s missing — page structure changed" % name)
        return el["value"]

    resp = session.post(URL, headers=HEADERS, timeout=REQUEST_TIMEOUT, data={
        "__VIEWSTATE": token("__VIEWSTATE"),
        "__VIEWSTATEGENERATOR": token("__VIEWSTATEGENERATOR"),
        "__EVENTVALIDATION": token("__EVENTVALIDATION"),
        "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ddlCounty",
        "ctl00$ContentPlaceHolder1$ddlCounty": ALL_AUTHORITIES,
    })
    resp.raise_for_status()
    return resp.text


def rung_playwright():
    """Drive the real page instead of replaying its postback.

    The county dropdown carries an ASP.NET AutoPostBack, so selecting the
    option IS the submit — the browser produces the tokens itself. That makes
    this rung both the answer to the edge block and structurally sturdier than
    rung_requests: nothing here can drift out of sync with __VIEWSTATE.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            context = browser.new_context(user_agent=HEADERS["User-Agent"])
            page = context.new_page()
            resp = page.goto(URL, wait_until="domcontentloaded", timeout=90000)
            # SAY WHAT ACTUALLY HAPPENED. A 403 body is still a page: goto()
            # succeeds, domcontentloaded fires on the edge's error document, and
            # the next line then waits thirty seconds for a <select> that is not
            # in it — reporting "Timeout ... waiting for locator
            # #ContentPlaceHolder1_ddlCounty", which reads exactly like ISBE
            # having redesigned the form. It had not. On 2026-08-29 both rungs
            # were refused by the same network-keyed edge block, and the run's
            # last line named a selector instead of the 403 above it; the
            # refresh was then read as a site change and left red for eleven
            # days, over which Fayette County swore in a new clerk that the
            # shipped card went on not naming.
            if resp is not None and resp.status != 200:
                raise RuntimeError(
                    "the browser rung was refused too: HTTP %d from %s. Both rungs "
                    "leave from the same runner, and this edge blocks by NETWORK "
                    "rather than by client fingerprint (PR #212), so a browser is "
                    "no answer to it. Measured intermittent — 3 of the first 7 "
                    "scheduled runs — and it has always cleared on a later run "
                    "from a different runner address. Re-run before treating it "
                    "as a source change."
                    % (resp.status, URL))
            page.select_option("#" + COUNTY_SELECT_ID, ALL_AUTHORITIES)
            # The postback replaces the table; waiting for it is the real
            # completion signal, so this neither races the round-trip nor
            # pads it with a fixed sleep.
            page.wait_for_selector("#" + RESULTS_TABLE_ID, timeout=90000)
            return page.content()
        finally:
            browser.close()


def fetch_results(engine):
    rungs = {"requests": [rung_requests], "playwright": [rung_playwright]}.get(
        engine, [rung_requests, rung_playwright])
    last = None
    for rung in rungs:
        try:
            return rung()
        except Exception as exc:  # noqa: BLE001 - every rung failure escalates
            last = exc
            print("%s failed (%s)" % (rung.__name__, exc), file=sys.stderr)
    print("FATAL: every fetch rung failed for %s — last error: %s" % (URL, last),
          file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", default="il_county_clerks.json")
    parser.add_argument("--engine", choices=("auto", "requests", "playwright"),
                        default="auto",
                        help="fetch rung; auto tries requests then playwright")
    args = parser.parse_args()

    # ISBE REFUSES THIS PROJECT, AND HAS SINCE BEFORE THIS SCRAPER WAS WRITTEN.
    # https://www.elections.il.gov/robots.txt is 29 bytes — a byte-order mark,
    # then `User-agent: * / Disallow: /` — served with `Last-Modified: Thu, 12
    # Jun 2025 06:39:17 GMT`, confirmed 2026-09-25 from two clients against the
    # origin's own headers. No group names any client here, so the `*` group
    # binds this scraper whatever token it sends, and CLAUDE.md is unconditional:
    # "A `*` group that disallows binds this project fully."
    #
    # It went unseen because the fleet's own reader could not read it: the BOM
    # made `robots_policy._parse` open no group at all, so a full refusal
    # answered `(True, 'no group binds this client')`. Fixed there, with ISBE's
    # own bytes as a selftest fixture.
    #
    # The shipped roster is NOT emptied. Adam's ruling of 2026-09-19 — "Preserve
    # data we have already fetched" — means `il-county-clerks.json` keeps the 101
    # clerks it last read, and the weekly job now stops here instead of fetching.
    require_robots_allowed(URL, HEADERS["User-Agent"], headers=HEADERS,
                           label="il-county-clerk-scraper")

    html = fetch_results(args.engine)
    table = BeautifulSoup(html, "html.parser").find(id=RESULTS_TABLE_ID)
    if table is None:
        print("FATAL: all-jurisdictions table not found — page structure changed", file=sys.stderr)
        sys.exit(1)

    scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    records = []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 7:
            continue  # header row (th) or malformed
        records.append({
            "jurisdiction": cell_text(tds[0]),
            "name": cell_text(tds[1]),
            "title": cell_text(tds[2]),
            "email": cell_email(tds[3]),
            "address": cell_text(tds[4]),
            "phone": cell_text(tds[5]),
            "fax": cell_text(tds[6]),
            "source_url": URL,
            "scraped_at": scraped_at,
        })

    with open(args.out, "w") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    n_clerk = sum(1 for r in records if r["title"] and "COUNTY CLERK" in r["title"].upper())
    print("scraped %d election authorities (%d county clerks) -> %s"
          % (len(records), n_clerk, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
