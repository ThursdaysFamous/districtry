#!/usr/bin/env python3
"""
Scrape the current NY State Senate + Assembly membership from the NY Senate
Open Legislation API (METRO_EXPANSION_PLAYBOOK §9). Stage 1 of the two-stage
pipeline: fetch the raw member list and write an intermediate JSON file with a
`source_url` + `scraped_at` on every record; build_ny_roster.py resolves it into
the two data/app/*.json roster files with count guards.

The API is key-gated (401 without a key). Set NYSENATE_API_KEY (a repo secret in
CI; see §11.6). Party is NOT exposed by the /members endpoint; it — with the
district + Albany office addresses — comes from the optional Open States
enrichment below when OPENSTATES_API_KEY is set, else an honest null.

Usage:
    NYSENATE_API_KEY=... python3 scripts/ny_legislature_scraper.py [--out PATH]
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once, UA_STDLIB_DEFAULT  # noqa: E402  (FLEET_SHARED)

API = "https://legislation.nysenate.gov/api/3/members/{year}?full=true&limit=1000&key={key}"
DEFAULT_OUT = os.path.join(os.path.dirname(__file__), ".cache", "ny_legislature_raw.json")


def _office_lines(office):
    """Card-ready address lines for one Open States office: the ;-split street
    address, then the phone and fax when present. [] when there's no address
    (a phone with no address is not a mappable office — never a guessed one)."""
    if not office or not office.get("address"):
        return []
    lines = [p.strip() for p in re.split(r"[;\n]+", office["address"]) if p.strip()]
    if not lines:
        return []
    if office.get("voice"):
        lines.append("Phone: " + office["voice"])
    if office.get("fax"):
        lines.append("Fax: " + office["fax"])
    return lines


def _office_summary_line(office):
    """A one-line "Also: <address> · Phone: <n>" for a *secondary* district office.

    A member can have more than one district office (Sen. Addabbo has a Woodhaven
    and a Middle Village one), but Open States labels both "District Office" and the
    engine's card renders a single primary district office + the Albany office. The
    extra offices ride along as these one-liners appended to the primary's block.

    The embedded "Phone:"/number is load-bearing: the engine's map-pin geocoder
    (officeAddressForGeocode) drops any line that looks like a phone/fax, so the pin
    geocodes the primary office alone instead of two mashed-together addresses.
    Returns None when there is no phone/fax to embed — without one this line would
    be geocoded too and mis-pin the card, so such an office is skipped, not shown.
    """
    addr = re.sub(r"\s*;\s*", ", ", (office.get("address") or "").replace("\n", ", ")).strip()
    if office.get("voice"):
        contact = "Phone: " + office["voice"]
    elif office.get("fax"):
        contact = "Fax: " + office["fax"]
    else:
        return None
    return "Also: " + addr + " · " + contact if addr else None


def person_offices(person):
    """{'districtOffice'?: [...], 'capitolOffice'?: [...]} for one Open States
    person — each key present only when that office has an address. They feed the
    card's "District Office" and "Albany Office" blocks. Open States can't tell a
    member's primary district office from a satellite (both are labelled "District
    Office"), so rather than guess we show them all: the first district office is
    the primary (full lines, and the one the card pins) and any others follow as
    "Also:" one-liners. A record that classifies nothing is treated as district-
    only (so the common case still pins); a person with no addressed office -> {}.
    """
    offs = [o for o in (person.get("offices") or []) if o.get("address")]
    districts = [o for o in offs if o.get("classification") == "district"]
    capitol = next((o for o in offs if o.get("classification") == "capitol"), None)
    if not districts and capitol is None:
        districts = offs[:1]  # nothing classified — treat the first office as the district one
    result = {}
    if districts:
        lines = _office_lines(districts[0])
        for extra in districts[1:]:
            summary = _office_summary_line(extra)
            if summary:
                lines.append(summary)
        if lines:
            result["districtOffice"] = lines
    clines = _office_lines(capitol)
    if clines:
        result["capitolOffice"] = clines
    return result


def _openstates_get(url, key, attempts=4):
    """Fetch one Open States page as JSON, retrying with backoff on the transient
    5xx gateway errors (502/503/504) and timeouts its include=offices queries throw
    intermittently. A real client error (401/403/422) is not retried — it won't fix
    itself. Raises the last error when every attempt fails."""
    require_robots_once(url, UA_STDLIB_DEFAULT, label="ny-ny-legislature-scraper")
    req = urllib.request.Request(url, headers={"X-API-KEY": key, "Accept": "application/json"})
    last = None
    for i in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            last = e
            if e.code < 500 and e.code != 429:
                raise
        except Exception as e:  # noqa: BLE001 — timeout / URLError / transient network blip
            last = e
        if i < attempts - 1:
            time.sleep(3 * (2 ** i))  # 3s, 6s, 12s
    raise last


def _person_homepage(person):
    """The member's own official page from Open States `links` — the first
    http(s) entry (Open States lists the state-site member page first). Never
    guessed: no usable link -> None, and the card then shows the chamber
    directory honestly labeled as a directory (the chamber factory keys the
    link label off the presence of a member url)."""
    for link in person.get("links") or []:
        url = (link.get("url") or "").strip()
        if url.startswith("http://") or url.startswith("https://"):
            return url
    return None


def openstates_enrichment():
    """{(CHAMBER, district:int): {'districtOffice'?, 'capitolOffice'?, 'party'?, 'url'?}}
    from the Open States v3 API (`include=offices`, keyed by
    `current_role.district`; party is the person's top-level party string; url is
    the member's official page from `links`).
    Returns {} if OPENSTATES_API_KEY is unset; on a page that keeps failing it logs
    and keeps whatever earlier pages succeeded (partial enrichment beats none — an
    address or party is never guessed).
    """
    key = os.environ.get("OPENSTATES_API_KEY")
    if not key:
        return {}
    out = {}
    CH = {"upper": "SENATE", "lower": "ASSEMBLY"}
    for org, chamber in CH.items():
        page = 1
        while page <= 10:  # per_page=20: senate ~4 pp, assembly ~8 pp (both < cap)
            url = ("https://v3.openstates.org/people?jurisdiction=New%20York"
                   "&org_classification=" + org + "&include=offices&per_page=20&page=" + str(page))
            try:
                payload = _openstates_get(url, key)
            except Exception as e:  # noqa: BLE001 — best-effort; keep any pages already gathered
                print("Open States %s enrichment stopped at page %d: %s" % (chamber, page, e), file=sys.stderr)
                break
            for person in payload.get("results", []):
                role = person.get("current_role") or {}
                d = role.get("district")
                if d is None:
                    continue
                try:
                    dnum = int(str(d).strip())
                except ValueError:
                    continue
                entry = person_offices(person)
                party = (person.get("party") or "").strip()
                if party:
                    entry["party"] = party
                homepage = _person_homepage(person)
                if homepage:
                    entry["url"] = homepage
                if entry:
                    out[(chamber, dnum)] = entry
            pag = payload.get("pagination") or {}
            if page >= (pag.get("max_page") or page):
                break
            page += 1
            time.sleep(6)  # Open States free tier is rate-limited (~10/min)
    n_d = sum(1 for v in out.values() if v.get("districtOffice"))
    n_c = sum(1 for v in out.values() if v.get("capitolOffice"))
    n_p = sum(1 for v in out.values() if v.get("party"))
    n_u = sum(1 for v in out.values() if v.get("url"))
    print("Open States: %d district + %d Albany offices, %d parties, %d member pages across %d districts" % (n_d, n_c, n_p, n_u, len(out)), file=sys.stderr)
    return out


def main():
    out_path = DEFAULT_OUT
    argv = sys.argv[1:]
    if "--out" in argv:
        out_path = argv[argv.index("--out") + 1]

    key = os.environ.get("NYSENATE_API_KEY")
    if not key:
        print("NYSENATE_API_KEY is not set (Open Legislation API key required).", file=sys.stderr)
        sys.exit(2)
    year = os.environ.get("NY_SESSION_YEAR", "2025")

    try:
        require_robots_once(API.format(year=year, key=key), UA_STDLIB_DEFAULT, label="ny-ny-legislature-scraper")
        with urllib.request.urlopen(API.format(year=year, key=key), timeout=90) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        print("Open Legislation API HTTP %d (401 = bad/absent key)" % e.code, file=sys.stderr)
        sys.exit(1)
    if not data.get("success"):
        print("Open Legislation API returned success=false", file=sys.stderr)
        sys.exit(1)

    items = data.get("result", {}).get("items", [])
    scraped_at = os.environ.get("SCRAPED_AT") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    source_url = "https://legislation.nysenate.gov/api/3/members/%s" % year

    # Optional enrichment from the Open States v3 API — district + Albany office
    # addresses and party (structured; nysenate.gov WAF-blocks automated requests,
    # so it is not a viable CI source). Needs a free OPENSTATES_API_KEY (§11);
    # absent or on any error we ship names-only, never guessing an address or party.
    details = openstates_enrichment()

    records = []
    for m in items:
        person = m.get("person") or {}
        chamber = m.get("chamber")
        district = m.get("districtCode")
        enrich = details.get((chamber, int(district))) if district is not None else None
        rec = {
            "chamber": chamber,                     # "SENATE" | "ASSEMBLY"
            "district": district,
            "name": m.get("fullName") or person.get("fullName"),
            "incumbent": bool(m.get("incumbent")),
            # party isn't on the Open Legislation members endpoint; take it from
            # the Open States enrichment when present, else an honest null.
            "party": (enrich or {}).get("party"),
            "source_url": source_url,
            "scraped_at": scraped_at,
        }
        if enrich:
            if enrich.get("districtOffice"):
                rec["districtOffice"] = enrich["districtOffice"]
            if enrich.get("capitolOffice"):
                rec["capitolOffice"] = enrich["capitolOffice"]
            if enrich.get("url"):
                rec["url"] = enrich["url"]
        records.append(rec)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"session_year": year, "members": records}, f, indent=2, ensure_ascii=False)
    n_sen = sum(1 for r in records if r["chamber"] == "SENATE")
    n_asm = sum(1 for r in records if r["chamber"] == "ASSEMBLY")
    print("wrote %s: %d members (%d senate, %d assembly)" % (out_path, len(records), n_sen, n_asm), file=sys.stderr)


if __name__ == "__main__":
    main()
