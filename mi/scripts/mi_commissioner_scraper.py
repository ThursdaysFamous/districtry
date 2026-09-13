#!/usr/bin/env python3
"""
Scrape stage 1: which commissioner holds each Michigan county commissioner
district, read from each county's own board page, cached for
build_mi_commissioner_roster.py (stage 2).

WHY THIS EXISTS
----------------
mi/data/app/mi-commissioner-districts.json draws all 619 districts and names
nobody. The state's own layer carries a Commissioner and a Party on every
polygon, and build_mi_commissioner_districts.py drops both, because that
column holds the certified November 2024 election winners rather than the
people in office now. This file gets the names from the counties instead.

The column is not merely old. Measured against the six counties here on
2026-09-13, it names a DIFFERENT PERSON in 7 of 76 seats:

    Macomb 1     state: Don Brown          county: Ken Goike
    Muskegon 4   state: Dan Potts          county: Chris McGuigan
    Muskegon 5   state: Nicole Larson      county: Charles Nash
    Muskegon 6   state: Doug Brown         county: Jessica Cook
    Muskegon 7   state: Darrell L. Paige   county: Kimberly D. Sims
    Wayne 5      state: Irma Clark-Coleman county: Angelique Peterson-Mayberry
    Wayne 8      state: David Knezek       county: Hassan M. Ahmad

Wayne 5 is the seat whose named commissioner died on 10 June 2025. Fourteen
more seats differ only in how the name is written (Kent 2 "Elizabeth Morse"
against the county's "Liz Morse"; Saginaw 4 "Sheldon Mattews" against
"Sheldon Matthews", a typo in the state column). THE COUNTY PAGE WINS in every
case and the state column ships nowhere; stage 2 prints every disagreement so
the drift stays visible rather than being quietly resolved.

WHAT A TRANCHE IS
------------------
Michigan has 83 counties and no statewide roster. This is the first tranche:
the counties whose own board page yields a district-keyed roster to the client
this scraper sends. Every county tried in tranche 1 is recorded in PROBES
below, whether it yielded or not — host, robots reading, what it answered, the
date — so the next tranche starts from measurements instead of guesses. The
twelve tried are Michigan's twelve most populous, 67.8% of the state by the
district layer's own 2020 populations.

THE CLIENT, AND WHAT IT ASKS FIRST
-----------------------------------
Every host's robots.txt is read through scripts/robots_policy.py (via this
instance's robots_gate shim) with UA_ROSTER_BOT BEFORE its first page fetch,
and a stated Crawl-delay is honoured per host by HostPacer. No county here
needs a browser user-agent: all six serve this token a full page. A county
that refuses is skipped with its reason printed and its page never requested;
it stays in PROBES so the weekly run re-asks and a county that changes its
file re-enters by itself.

A captcha is an access control. Livingston and Ottawa answer HTTP 202 on
robots.txt itself — 202 is never a document — and nothing here tries to get
past that. Oakland's edge answers 403 to the districtry token AND to Chrome
126 with its client hints, so the refusal is of this client's stack rather
than its name and a browser string buys nothing.

WHAT EACH PARSER READS, AND THE TRAP IN IT
--------------------------------------------
Six counties, five page shapes. Each parser pairs a district with a name
INSIDE ONE BLOCK rather than by document order, because three of the six print
the name before the district and one prints the role before the name:

  Kalamazoo  CivicPlus staff directory. District is in the JOB TITLE field
             ("District 2 – Chair"), so the district and the role arrive
             together. The page carries a tenth p-name with no district — the
             board's administrative contact — and rows without a "District N"
             job title are dropped rather than numbered by position.
  Kent       CivicPlus staff directory, one widget per district: the district
             is the widget's own <h3> heading and the name is the p-name
             inside it. Its e-mails are CLOUDFLARE-OBFUSCATED, the markup that
             silently emptied Brown County's seven addresses, so the hex is
             decoded and markup-present-but-nothing-decoded is a hard failure.
  Macomb     The BOARD'S OWN SITE, bocmacomb.org, linked from the county's
             board page; macombgov.org's board page names nobody. Name and
             district sit in sibling columns whose CSS order is reversed
             (order-2 before order-1), so a flat read pairs them wrongly. Its
             index page carries no party; each member's OWN profile page does
             ("Ken Goike (R) District 1", read 2026-09-13). That is thirteen
             more fetches a week for one field and is left for a later tranche
             rather than taken now — recorded so it is a decision instead of an
             oversight.
  Muskegon   Hand-written editor HTML: <h2>DISTRICT N</h2><h3>Name (R)</h3>.
             The only county of the six publishing PARTY on its own page.
             HTML COMMENTS ARE STRIPPED FIRST: District 7's telephone is
             commented out, and a parser that ignores comments ships a number
             the county deliberately took down. Each block is BOUNDED at its
             own contact paragraph's </p>: District 7 is the last on the page,
             so a block that runs to the next <h2> runs to the end of the
             document instead, and District 7 picks up the county's general
             number from the section below. That is the trap twice in one
             county — a commented-out number and an unbounded last block, both
             producing a plausible telephone for a commissioner who publishes
             none.
  Saginaw    Card grid, name in the card title and district in a <strong>
             below it.
  Wayne      The roster exists ONLY in the commission section's navigation,
             which is a CMS page tree rather than a hand-built menu — every
             entry resolves to a live page and the district is in the slug
             ("...-Dist-5"). Checked against the Alexander trap on
             2026-09-13: all 15 slugs answer 200.

NO PARSER INFERS A DISTRICT FROM LIST ORDER. Each returns only the pairs its
own page states, and stage 2 refuses any county whose districts are not
exactly 1..N for the seat count the shipped geometry carries.

WHAT NEVER SHIPS. A home address (none of these six publishes one, and the
parsers read no address field at all). A party taken from the state column. A
name from anywhere but the county's own page.

Usage:
    python3 mi/scripts/mi_commissioner_scraper.py
    python3 mi/scripts/mi_commissioner_scraper.py --county Wayne
"""

import argparse
import html as _html
import json
import os
import re
import sys
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("mi-commissioner-scraper: FAIL — requests is not installed "
          "(pip install -c mi/scripts/requirements.txt requests)", file=sys.stderr)
    raise SystemExit(1)

from robots_gate import RobotsGate, HostPacer

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache", "mi_commissioner_roster.json")

# The fleet's own roster token (scripts/scraper_common.py's UA_ROSTER_BOT).
# Copied rather than imported: instance scripts resolve imports inside their
# own tree, and scripts/validate_workflow_deps.py fails a sys.path reach across
# trees. robots_gate.py is the one sanctioned exception, because
# validate_workflow_deps lists robots_policy in FLEET_SHARED.
UA_ROSTER_BOT = "districtry.com roster bot (civic data; contact via site)"

# The state's own district layer, queried for its Commissioner column ONLY so
# stage 2 can print where the county disagrees. Nothing from this query ships.
STATE_SERVICE = ("https://gisagocss.state.mi.us/arcgis/rest/services/OpenData/"
                 "boundaries/MapServer/10")

TIMEOUT = 60


def txt(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def strip_comments(h):
    """Remove HTML comments before parsing. Muskegon comments out District 7's
    telephone; a parser that leaves comments in ships a number the county
    took down."""
    return re.sub(r"<!--.*?-->", " ", h or "", flags=re.S)


def cf_decode(hexstr):
    """Decode a Cloudflare-obfuscated e-mail token (data-cfemail /
    /cdn-cgi/l/email-protection#<hex>): first byte is the XOR key."""
    try:
        key = int(hexstr[:2], 16)
        out = "".join(chr(int(hexstr[i:i + 2], 16) ^ key)
                      for i in range(2, len(hexstr), 2))
    except (ValueError, IndexError):
        return None
    return out if "@" in out else None


def phone(raw):
    """A 10-digit US number as ###-###-####, or None. Michigan's six pages
    write it four ways (bare digits, +1-prefixed, punctuated, tel: href)."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:]) if len(digits) == 10 else None


# ---------------------------------------------------------------- parsers ---

def parse_kalamazoo(page):
    out = {}
    for blk in re.findall(r'<li class="widgetItem h-card">(.*?)</li>', page, re.S):
        name = re.search(r'class="widgetTitle field p-name">\s*(.*?)\s*</h4>', blk, re.S)
        job = re.search(r'class="field p-job-title">(.*?)</div>', blk, re.S)
        if not (name and job):
            continue
        # "District 5 – Vice Chair": the district and the role in one field.
        keyed = re.match(r"District\s+(\d+)\s*(?:[–—-]\s*(.+))?$", txt(job.group(1)))
        if not keyed:
            continue          # the board's administrative contact, not a member
        rec = {"name": txt(name.group(1))}
        if keyed.group(2):
            rec["role"] = keyed.group(2).strip()
        tel = re.search(r'href="tel:([^"]+)"', blk)
        if tel and phone(tel.group(1)):
            rec["phone"] = phone(tel.group(1))
        out[keyed.group(1)] = rec
    return out


def parse_kent(page):
    out, obfuscated, decoded = {}, 0, 0
    for blk in re.split(r'<div class="widgetHeader">', page)[1:]:
        head = re.search(r"<h3>(.*?)</h3>", blk, re.S)
        name = re.search(r'class="widgetTitle field p-name">\s*(.*?)\s*</h4>', blk, re.S)
        if not (head and name):
            continue
        keyed = re.search(r"District\s+(\d+)", txt(head.group(1)))
        if not keyed:
            continue
        rec = {"name": txt(name.group(1))}
        job = re.search(r'class="field p-job-title">(.*?)</div>', blk, re.S)
        if job and txt(job.group(1)) and txt(job.group(1)) != "Commissioner":
            rec["role"] = txt(job.group(1))
        for hexstr in re.findall(r"/cdn-cgi/l/email-protection#([0-9a-fA-F]+)", blk):
            obfuscated += 1
            addr = cf_decode(hexstr)
            if addr:
                decoded += 1
                rec.setdefault("email", addr)
        tel = re.search(r'href="tel:([^"]+)"', blk)
        if tel and phone(tel.group(1)):
            rec["phone"] = phone(tel.group(1))
        out[keyed.group(1)] = rec
    if obfuscated and not decoded:
        raise ValueError("Kent: %d Cloudflare-obfuscated e-mail tokens and none decoded — "
                         "the obfuscation changed and every address would ship empty"
                         % obfuscated)
    return out


def parse_macomb(page):
    out = {}
    for blk in re.split(r'<div class="col-12 col-md-6 col-lg-4 post commissioner', page)[1:]:
        # The district's own <h3> and the name's own <p>, paired inside one
        # card. Their CSS order is reversed (order-2 carries the name, order-1
        # the district), so document order is not the reading order.
        keyed = re.search(r'<h3 class="mb-0">\s*District\s+(\d+)\s*</h3>', blk)
        name = re.search(r'<p class="byline">\s*(.*?)\s*</p>', blk, re.S)
        if not (keyed and name):
            continue
        rec = {"name": txt(name.group(1))}
        role = re.search(r'<span class="title-banner">\s*(.*?)\s*</span>', blk, re.S)
        if role and txt(role.group(1)):
            rec["role"] = txt(role.group(1))
        prof = re.search(r'href="(https://bocmacomb\.org/commissioners/[^"]+)"', blk)
        if prof:
            rec["profileUrl"] = prof.group(1)
        out[keyed.group(1)] = rec
    return out


PARTY = {"R": "Republican", "D": "Democratic", "I": "Independent"}


def parse_muskegon(page):
    out = {}
    for blk in re.finditer(r"<h2>\s*DISTRICT\s+(\d+)\s*</h2>\s*<h3>(.*?)</h3>(.*?)</p>",
                           page, re.S | re.I):
        district, heading, rest = blk.group(1), txt(blk.group(2)), blk.group(3)
        # "Kim Cyr (R)" — the only one of the six publishing party itself.
        # Read from the <h3>, never the image alt: District 3's alt misspells
        # the name the heading gives as Hazekamp.
        tagged = re.match(r"(.*?)\s*\((R|D|I)\)\s*$", heading)
        rec = {"name": tagged.group(1) if tagged else heading}
        if tagged:
            rec["party"] = PARTY[tagged.group(2)]
        mail = re.search(r'href="mailto:([^"?]+)"', rest)
        if mail:
            rec["email"] = mail.group(1).strip()
        tel = re.search(r'href="tel:([^"]+)"', rest)
        if tel and phone(tel.group(1)):
            rec["phone"] = phone(tel.group(1))
        out[district] = rec
    return out


def parse_saginaw(page):
    out = {}
    for blk in re.split(r'<div class="card text-center h-100">', page)[1:]:
        name = re.search(r'<h3 class="card-title p-1">\s*(.*?)\s*</h3>', blk, re.S)
        keyed = re.search(r"<strong>\s*District\s+(\d+)\s*</strong>", blk)
        if not (name and keyed):
            continue
        rec = {"name": txt(name.group(1))}
        prof = re.search(r'href="(/departments/board-of-commissioners/'
                         r'commissioner-roster/[^"]+)"', blk)
        if prof:
            rec["profileUrl"] = "https://www.saginawcountymi.gov" + prof.group(1)
        out[keyed.group(1)] = rec
    return out


def parse_wayne(page):
    """Wayne's roster lives in the commission section's navigation and nowhere
    else — the page body is prose about what the commission does. That
    navigation is the CMS's own page tree, not a hand-built menu that could
    outlive its subjects: every slug was fetched on 2026-09-13 and all 15
    answered 200."""
    out = {}
    for m in re.finditer(r'href="(https://www\.waynecountymi\.gov/Government/Elected-Officials/'
                         r'Commission/Commissioners/[^"]*?-Dist-(\d+))"[^>]*>([^<]+)</a>', page):
        out[m.group(2)] = {"name": txt(m.group(3)), "profileUrl": m.group(1)}
    return out


# ------------------------------------------------------------- the tranche ---

COUNTIES = (
    {"fips": "077", "county": "Kalamazoo", "seats": 9, "parse": parse_kalamazoo,
     "url": "https://www.kalcounty.gov/479/Board-of-Commissioners"},
    {"fips": "081", "county": "Kent", "seats": 21, "parse": parse_kent,
     "url": "https://www.kentcountymi.gov/1464/Meet-the-Commissioners"},
    {"fips": "099", "county": "Macomb", "seats": 13, "parse": parse_macomb,
     "url": "https://bocmacomb.org/find-your-commissioner/"},
    {"fips": "121", "county": "Muskegon", "seats": 7, "parse": parse_muskegon,
     "url": "https://co.muskegon.mi.us/1965/Your-Muskegon-County-Commissioners"},
    {"fips": "145", "county": "Saginaw", "seats": 11, "parse": parse_saginaw,
     "url": "https://www.saginawcountymi.gov/departments/board-of-commissioners/"},
    {"fips": "163", "county": "Wayne", "seats": 15, "parse": parse_wayne,
     "url": "https://www.waynecountymi.gov/Government/Elected-Officials/Commission"},
)

# Every county tried in tranche 1, measured 2026-09-13 from this project's
# sandbox with UA_ROSTER_BOT, robots.txt read first in every case. The six
# above are the ones that yielded; these six are the ones that did not, and
# each says what stopped it rather than "no page found". Re-measure before
# writing any of them off again — a robots file changes, an edge rule is
# lifted, a county moves CMS.
PROBES = (
    {"county": "Oakland", "fips": "125", "seats": 19,
     "host": "www.oakgov.com",
     "robots": "refused — HTTP 403 from the site's own edge (server: AkamaiGHost, "
               "errors.edgesuite.net reference), not from this sandbox's proxy",
     "answered": "403 on / as well, to UA_ROSTER_BOT and to Chrome/126 with its "
                 "client hints alike — the stack is refused, not the token, so a "
                 "browser string buys nothing",
     "date": "2026-09-13"},
    {"county": "Genesee", "fips": "049", "seats": 9,
     "host": "www.geneseecountymi.gov (and www.gc4me.com)",
     "robots": "served — one `*` group, `Disallow: /` (line 18). gc4me.com serves a "
               "second file allowing only *.pdf/*.DOC/*.DOCX/*.PPT/*.PPTX and "
               "disallowing / (line 22)",
     "answered": "not fetched. The document allowances on gc4me.com do not help: "
                 "finding a roster PDF means reading the HTML that links it, and "
                 "that is the part the file refuses",
     "date": "2026-09-13"},
    {"county": "Ingham", "fips": "065", "seats": 15,
     "host": "www.ingham.org",
     "robots": "served — one `*` group, `Disallow: /` (line 18)",
     "answered": "not fetched",
     "date": "2026-09-13"},
    {"county": "Ottawa", "fips": "139", "seats": 11,
     "host": "www.miottawa.org",
     "robots": "challenge — robots.txt itself answers HTTP 202 in 169 bytes "
               "(the sgcaptcha shape). 202 is never a document",
     "answered": "not fetched. A captcha is an access control and this project "
                 "does not route around one",
     "date": "2026-09-13"},
    {"county": "Livingston", "fips": "093", "seats": 9,
     "host": "www.livgov.com",
     "robots": "challenge — robots.txt itself answers HTTP 202, same shape as Ottawa",
     "answered": "not fetched",
     "date": "2026-09-13"},
    {"county": "Washtenaw", "fips": "161", "seats": 9,
     "host": "www.washtenaw.org",
     "robots": "served — no rule in the binding `*` group matches, Crawl-delay 20",
     "answered": "200, and the roster is not keyable. www.washtenaw.org/commissioners "
                 "lists District 1-9 with a free-prose bio under each and no name "
                 "field; the bios name the commissioner in seven different sentence "
                 "shapes and District 8's does not begin with the name at all. The "
                 "per-district pages (/district-N) carry the district as their only "
                 "heading and no name. Taking a name out of that prose would be a "
                 "guess, so Washtenaw ships nothing",
     "date": "2026-09-13"},
)


def ua_session():
    s = requests.Session()
    s.headers["User-Agent"] = UA_ROSTER_BOT
    s.headers["Accept"] = "text/html,application/xhtml+xml,*/*;q=0.8"
    return s


def state_commissioners(session, fips_list):
    """The state layer's own Commissioner column, for the comparison stage 2
    prints. Never shipped — see the module docstring."""
    where = "CountyFIPS IN (%s)" % ",".join("'%s'" % f for f in fips_list)
    url = STATE_SERVICE + "/query"
    params = {"where": where, "outFields": "CountyFIPS,DistrictName,Commissioner",
              "returnGeometry": "false", "f": "json", "resultRecordCount": 1000}
    out = {}
    try:
        data = session.get(url, params=params, timeout=TIMEOUT).json()
    except Exception as exc:                                  # noqa: BLE001
        print("  state column unavailable (%s) — the comparison is skipped, "
              "the roster is not" % exc)
        return out
    for feat in data.get("features", []):
        att = feat.get("attributes", {})
        num = re.search(r"(\d+)", att.get("DistrictName") or "")
        if num:
            out.setdefault(att["CountyFIPS"], {})[num.group(1)] = att.get("Commissioner")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--county", help="scrape one county by name")
    args = ap.parse_args()

    wanted = [c for c in COUNTIES
              if not args.county or c["county"].lower() == args.county.lower()]
    if not wanted:
        print("mi-commissioner-scraper: FAIL — no county named %r; known: %s"
              % (args.county, ", ".join(c["county"] for c in COUNTIES)), file=sys.stderr)
        return 1

    session = ua_session()
    gate = RobotsGate(session, UA_ROSTER_BOT)
    pacer = HostPacer(gate)

    entries, refused = {}, []
    for spec in wanted:
        url, county = spec["url"], spec["county"]
        verdict = gate.verdict(url)
        allowed, why = gate.allows(url)
        if not allowed:
            refused.append((county, why))
            print("  %-10s SKIPPED — robots %s: %s" % (county, verdict.status, why))
            continue
        try:
            with pacer.hold(url):
                resp = session.get(url, timeout=TIMEOUT)
        except Exception as exc:                              # noqa: BLE001
            print("  %-10s FETCH FAILED — %s" % (county, exc))
            continue
        if resp.status_code != 200:
            print("  %-10s HTTP %s (%d bytes)" % (county, resp.status_code, len(resp.content)))
            continue
        try:
            keyed = spec["parse"](strip_comments(resp.text))
        except ValueError as exc:
            print("  %-10s PARSE REFUSED — %s" % (county, exc))
            continue
        entries[spec["fips"]] = {
            "county": county,
            "seats": spec["seats"],
            "sourceUrl": url,
            "finalUrl": resp.url,
            "districts": keyed,
        }
        print("  %-10s %2d/%2d districts (%s, %d bytes)"
              % (county, len(keyed), spec["seats"], url, len(resp.content)))

    if not entries:
        print("mi-commissioner-scraper: FAIL — no county yielded a roster", file=sys.stderr)
        return 1

    state = state_commissioners(session, sorted(entries))
    for fips, entry in entries.items():
        for district, rec in entry["districts"].items():
            named = (state.get(fips) or {}).get(district)
            if named is not None:
                rec["stateColumnName"] = named

    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    payload = {
        "scrapedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "userAgent": UA_ROSTER_BOT,
        "counties": entries,
        "refused": [{"county": c, "why": w} for c, w in refused],
    }
    with open(CACHE, "w") as handle:
        json.dump(payload, handle, indent=1, sort_keys=True)
        handle.write("\n")
    total = sum(len(e["districts"]) for e in entries.values())
    print("mi-commissioner-scraper: %d counties, %d districts -> %s"
          % (len(entries), total, os.path.relpath(CACHE, os.path.dirname(HERE))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
