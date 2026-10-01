#!/usr/bin/env python3
"""
Scrape stage 1: e-mail addresses for the county TREASURER and SHERIFF, cached
for build_ia_county_officers.py.

WHY THESE TWO OFFICES
----------------------
data/app/ia-county-officers.json ships six elected county offices. Four of them
already carry an address from a statewide directory (the auditor from
sos.iowa.gov, the recorder from Iowa Land Records, the county attorney from the
ICAA roster, most sheriffs from the ISSDA directory). Two do not:

  * TREASURER -- 0 of 99. The ISAC member portal is the only statewide source
    that names Iowa's treasurers at all, and it HAS NO E-MAIL COLUMN: re-checked
    2026-08-29, zero `mailto:` and zero `@` anywhere on a county page, columns
    Name / Office / Address / City / State / Zip / Phone / Fax / Party.
  * SHERIFF -- 15 of 98 missing, the gaps in a dated ISSDA PDF.

AN ADDRESS SHIPS TWO WAYS AND NO THIRD
---------------------------------------
  1. WITNESSED -- the local part carries the officeholder's own name, the
     Wisconsin witness_window rule; or
  2. OFFICE -- the local part is the office itself (`treas@`, `bctreas@`,
     `polkcounty.sheriff@`), which is the county's published mailbox for that
     office and is correct whoever holds it.

**A PAGE WINDOW IS NOT A WITNESS.** The first version of this probe took the
address nearest the word "treasurer" and returned a DEPUTY's personal address in
four of the first seven counties tried -- Appanoose, Boone, Bremer and Buchanan
-- which would have put a staffer's address under an elected officer's name. The
office/witness gate is the whole method, not a refinement of it.

Two smaller rules, each from a real defect this found:

  * A LEADING RUN OF DIGITS IS A PHONE NUMBER, NOT PART OF THE ADDRESS. Taylor
    County's page yielded `712-523-2384treasurer@taylorcounty.iowa.gov`, which
    is a dead address that looks alive. A run of 7+ digits is stripped; `treas1@`
    is untouched.
  * THE DOMAIN MUST FIT THE COUNTY. See below -- this is what catches the
    contamination in the second source.

THE SECOND SOURCE, AND THE CONTAMINATION IT CARRIES
-----------------------------------------------------
`iowatreasurers.org` publishes a per-county treasurer page at
`index.php?module=treashome&idCounty=<N>`, N running 1..99 in alphabetical county
order. An earlier record in this repo called that site "a payment portal that
names nobody"; it is not, and it carries addresses the ISAC portal has no column
for.

**IT ALSO SERVES THE WRONG COUNTY, WITH NO ERROR AND NO 404, ON A COMPLETE AND
PLAUSIBLE PAGE.** Swept 2026-08-29, all 99 ids, fresh session each:

  * EIGHT ids serve another county's page outright. Five (Buchanan, Johnson,
    Linn, Montgomery, Poweshiek) return byte-near-identical CLARKE County pages;
    three (Floyd, Iowa, Polk) return byte-IDENTICAL JEFFERSON County pages,
    92,419 bytes each.
  * THREE MORE ids serve the right county's page carrying JEFFERSON's address
    anyway (Dallas, Kossuth, Muscatine) -- so a page-level county check is
    necessary and NOT sufficient.
  * One (Webster) publishes the placeholder `treasurer@mycounty.gov`.

Nothing here is keyed on `idCounty` alone. Every page must independently
identify as the county it is supposed to be (its own `<h1>`, else the county
named most often in its body), AND the address's domain must fit that county.
Linn is Iowa's second-largest county; shipping Clarke County's treasurer under
it is the kind of error no count guard would ever notice.

Usage:
    python3 ia/scripts/ia_county_officer_email_scraper.py
    python3 ia/scripts/ia_county_officer_email_scraper.py --office sheriff
"""

import argparse
import html as html_mod
import json
import os
import re
import sys
import time

import requests

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import (UA_HEADERS_ROSTER_BOT,  # noqa: E402  (FLEET_SHARED)
                            require_robots_once)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ia/
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
OUT_PATH = os.path.join(CACHE_DIR, "ia_county_officer_emails.json")

OFFICERS = os.path.join(APP_DATA_DIR, "ia-county-officers.json")
DIRECTORY = os.path.join(APP_DATA_DIR, "ia-county-board-directory.json")
AUDITORS = os.path.join(APP_DATA_DIR, "ia-county-auditors.json")

# OUR OWN IDENTITY, MEASURED RATHER THAN ASSUMED (2026-10-01). This file
# used to send a Chrome string. Every page it fetches was re-read with
# scraper_common's districtry token on this file's own HTTP stack and
# answered in full, so the browser string was claiming a client this
# project does not run for no measured gain. A site that measurably
# refuses the token gets the browser rung back, per host, with the
# measurement written here.
HEADERS = dict(UA_HEADERS_ROSTER_BOT)
TREASHOME = "https://www.iowatreasurers.org/index.php?module=treashome&idCounty=%d"

# AN href AND ITS OWN LINK TEXT CAN NAME DIFFERENT PEOPLE, and this is why the
# addresses here are read out of the whole page rather than out of hrefs.
# Measured 2026-09-04 on iowatreasurers.org's Monroe page, which publishes
#
#     <a href="mailto:cchambers@monroecounty.iowa.gov">fpowless@...gov</a>
#
# under a photo captioned Faith Powless. An href-first parser ships Chambers's
# address for Powless's office and every count guard stays green. classify()
# settles it the right way round for the right reason -- the local part carries
# the OFFICEHOLDER's name, so fpowless@ is "witnessed" and the other four
# addresses on that page are rejected -- and that is a property to preserve if
# this ever moves to parsing links.
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
CFEMAIL_RE = re.compile(r'data-cfemail="([0-9a-fA-F]+)"')
OFFICE_WORD = {
    "treasurer": ("treasurersoffice", "treasurer", "treas"),
    "sheriff": ("sheriffsoffice", "sheriffoffice", "sheriff", "so"),
}
JUNK_DOMAINS = ("example.com", "sentry", "wixpress", "godaddy", "revize.com",
                "mycounty.gov", "iowatreasurers.org")
WINDOW_BEFORE, WINDOW_AFTER = 1500, 2500


def decode_cfemail(hexstr):
    b = bytes.fromhex(hexstr)
    key = b[0]
    return "".join(chr(c ^ key) for c in b[1:])


def clean_local(email):
    """Strip a phone number glued to the front of an address (Taylor County)."""
    local, _, dom = email.partition("@")
    local = re.sub(r"^[0-9]{7,}", "", local)
    return (local + "@" + dom) if local and dom else None


def emails_in(text):
    out = set(EMAIL_RE.findall(text))
    for h in CFEMAIL_RE.findall(text):
        try:
            out.add(decode_cfemail(h))
        except Exception:
            pass
    keep = set()
    for e in out:
        c = clean_local(e)
        if not c:
            continue
        if re.search(r"\.(png|jpg|jpeg|gif|svg|webp|css|js)$", c, re.I):
            continue
        if any(j in c.lower() for j in JUNK_DOMAINS):
            continue
        keep.add(c)
    return keep


def domain_fits(county, email):
    """The domain must plausibly belong to THIS county.

    iowatreasurers.org served Dallas, Kossuth and Muscatine a
    jeffersoncountyia.com address on pages that each identified correctly as
    themselves, so the page-level check alone would have shipped all three.
    """
    dom = email.split("@")[1].lower()
    flat = dom.replace("-", "").replace(".", "")
    c = re.sub(r"[^a-z]", "", county.lower())
    if c in flat:
        return True
    initials = "".join(w[0] for w in county.lower().split())
    return bool(re.match(r"^(%s|%s)" % (re.escape(initials), re.escape(c[:4])), flat))


def classify(email, person, office, county):
    """'office', 'witnessed', or 'rejected' -- see the module docstring."""
    local = email.split("@")[0].lower()
    flat = re.sub(r"[^a-z]", "", local)
    cty = re.sub(r"[^a-z]", "", county.lower())
    for word in OFFICE_WORD[office]:
        if word not in flat:
            continue
        rest = flat.replace(word, "", 1)
        if (rest == "" or rest in (cty, cty[:3], "county" + cty, cty + "county",
                                   "co", "county", "cnty")
                or (len(rest) <= 3 and rest.isalpha())):
            return "office"
    toks = [t.lower() for t in re.findall(r"[A-Za-z]{3,}", person or "")]
    if any(t in flat for t in toks):
        return "witnessed"
    parts = [t.lower() for t in re.findall(r"[A-Za-z]{2,}", person or "")]
    if len(parts) >= 2:
        for sur in parts[1:]:
            if flat.startswith(parts[0][0] + sur):
                return "witnessed"
    return "rejected"


def get(url, timeout=25):
    try:
        require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                            label="ia-ia-county-officer-email-scraper")
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return str(r.status_code), (r.text if r.status_code == 200 else "")
    except Exception as e:
        return type(e).__name__, ""


def probe_county_site(base, office, person, county):
    """Follow a link naming the office on the county's OWN site, read there."""
    status, home = get(base)
    if not home:
        return status, None, []
    links = set()
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', home, re.S | re.I):
        href, txt = m.group(1), re.sub(r"<[^>]+>", " ", m.group(2))
        if office in html_mod.unescape(href + " " + txt).lower():
            u = href if href.startswith("http") else base.rstrip("/") + "/" + href.lstrip("/")
            links.add(u)
    rejected = []
    for u in sorted(links)[:4]:
        _, page = get(u)
        if not page:
            continue
        low = page.lower()
        for m in re.finditer(office, low):
            win = page[max(0, m.start() - WINDOW_BEFORE): m.start() + WINDOW_AFTER]
            for e in emails_in(win):
                why = classify(e, person, office, county)
                if why != "rejected" and domain_fits(county, e):
                    return status, {"email": e, "why": why, "source": u}, rejected
                rejected.append({"email": e, "why": why})
    return status, None, rejected[:4]


def identify_county(page, counties):
    """Which county does this page CLAIM to be? <h1> first, then body frequency."""
    plain = re.sub(r"<(script|style).*?</\1>", " ", page, flags=re.S | re.I)
    h1 = re.sub(r"\s+", " ", html_mod.unescape(" ".join(
        re.sub(r"<[^>]+>", " ", m) for m in re.findall(r"<h1[^>]*>(.*?)</h1>", plain, re.S | re.I))))
    body = re.sub(r"\s+", " ", html_mod.unescape(re.sub(r"<[^>]+>", " ", plain)))
    for c in sorted(counties, key=len, reverse=True):
        if re.search(r"\b%s\b\s+County" % re.escape(c), h1, re.I):
            return c
    hits = {c: len(re.findall(r"\b%s\b\s+County" % re.escape(c), body, re.I)) for c in counties}
    best = max(hits, key=hits.get)
    return best if hits[best] else None


def probe_treashome(idx, county, counties):
    """iowatreasurers.org, gated on the page identifying as this county."""
    status, page = get(TREASHOME % idx)
    if not page:
        return status, None, "unreachable"
    claims = identify_county(page, counties)
    if claims != county:
        return status, None, "page identifies as %s" % (claims or "no county")
    for e in sorted(emails_in(page)):
        if classify(e, None, "treasurer", county) == "office" and domain_fits(county, e):
            return status, {"email": e, "why": "office", "source": TREASHOME % idx}, None
    return status, None, "no office-form address whose domain fits the county"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--office", choices=["treasurer", "sheriff", "both"], default="both")
    args = ap.parse_args()

    officers = {r["county"]: r for r in json.load(open(OFFICERS)).values()}
    counties = sorted(officers)
    aud = {v["county"]: v for v in json.load(open(AUDITORS)).values()}
    fips = {v["county"]: k for k, v in
            {k: v for k, v in json.load(open(AUDITORS)).items()}.items()}
    board = json.load(open(DIRECTORY))
    urls = {}
    for k, v in board.items():
        if v.get("url"):
            for c, g in fips.items():
                if g[2:] == k:
                    urls[c] = v["url"]

    want = ["treasurer", "sheriff"] if args.office == "both" else [args.office]
    out = {}
    for office in want:
        found = 0
        for i, county in enumerate(counties, start=1):
            rec = officers[county].get(office) or {}
            if not rec.get("name") or rec.get("email"):
                continue                       # nothing to add
            base = urls.get(county)
            hit = note = None
            status = "no url"
            if base:
                status, hit, rej = probe_county_site(base, office, rec["name"], county)
                if not hit and rej:
                    note = "county site rejected " + ", ".join(
                        "%s (%s)" % (r["email"], r["why"]) for r in rej[:2])
            if not hit and office == "treasurer":
                st2, hit, why2 = probe_treashome(i, county, counties)
                if not hit:
                    note = (note + "; " if note else "") + "iowatreasurers: " + str(why2)
            entry = {"office": office, "county": county, "status": status}
            if hit:
                entry.update(hit); found += 1
            elif note:
                entry["note"] = note
            out.setdefault(office, {})[county] = entry
            print("%-10s %-14s %s" % (office, county,
                  ("%s  (%s)" % (hit["email"], hit["why"])) if hit else "—"), flush=True)
            time.sleep(0.6)
        print("%s: %d address(es) accepted" % (office, found), file=sys.stderr)

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
        f.write("\n")
    print("wrote %s" % OUT_PATH, file=sys.stderr)


if __name__ == "__main__":
    main()
