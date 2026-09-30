#!/usr/bin/env python3
"""
Resolve scripts/il_county_clerk_scraper.py's raw ISBE output into one record
per Illinois county and write it as the JSON app-data file the County card
reads: data/app/il-county-clerks.json.

Keys are the county name NORMALIZED to uppercase letters only ("STCLAIR",
"DEKALB", "LASALLE") because the two sides of the join spell counties
differently — ISBE writes "ST. CLAIR"/"DuPAGE"/"JoDAVIESS" while the TIGERweb
county layer's NAME field writes "St. Clair"/"DuPage"/"JoDaviess". index.html
applies the same normalization (uppercase, strip non-letters) to the TIGER
name before the lookup, so the two can't drift apart on punctuation or
casing.

Municipal boards of election commissioners (Jurisdiction "CITY OF …") are
election authorities but not county clerks; they are filtered out here.

Usage:
    python3 build_county_clerk_roster.py il_county_clerks.json [output_dir]

output_dir defaults to the repo's data/app/ directory.

NOT GATED ON robots.txt: ITS ONE FETCH IS A NAME LOOKUP, NOT A READ OF ANYBODY'S
PAGES. `mx_report` asks dns.google/resolve whether each shipped clerk address's
domain has a mail route, over DNS-over-HTTPS because plain DNS and SMTP are
commonly blocked on CI runners. What comes back is a DNS answer, in the protocol
that endpoint documents for exactly this; there is no page, no link to follow and
no url discovered, and the thing being asked about is a domain rather than a
site's content.

THE TEST IS WHETHER SOMEBODY'S PAGES ARE BEING READ, never which host answers. A
resolver is the layer BELOW the one robots.txt governs -- every gated fetch in
this repository resolves a name first, including the fetch of robots.txt itself,
so reading a policy before a name lookup would have to resolve a name to do it.
An unauthenticated read of an ordinary page on a Google host would be gated in
full. The argument is made here at length so it cannot be applied by analogy from
the exemption table.
"""

import argparse
import json
import os
import re
import sys

# Illinois has 102 counties, but ISBE's directory lists each county's
# ELECTION AUTHORITY — which is the elected county clerk everywhere except
# Peoria, whose authority is the appointed Peoria County Election Commission
# (its row carries an EXECUTIVE DIRECTOR title, not the clerk). Attributing
# the commission's director to the "County Clerk" card row would be wrong, so
# Peoria is a known, deliberate absence: its county card simply shows no
# clerk rows. The guard pins BOTH facts — 101 clerks AND Peoria being the one
# missing — so if another county adopts a commission, Peoria reverts to a
# clerk authority, or the parse breaks, the build fails for a human look
# instead of silently shifting coverage.
EXPECTED_COUNTIES = 101
EXPECTED_MISSING = {"PEORIA"}

# ---------------------------------------------------------------------------
# THE BOUNCE GUARD — addresses ISBE publishes that provably do not deliver.
#
# Why this exists, and why it is a hand-kept list rather than a check: on
# 2026-07-31 an e-mail to White County's published clerk address failed
# permanently after five days of retries ("421 Network error when connecting to
# MX server pro.i7mail.net"). The app had been rendering that address as a
# mailto link on the County card — telling a White County resident "write to
# your clerk here" when nothing they sent could arrive. That is the honesty
# rule failing quietly, and no gate saw it, because the address parses, the
# roster count is right, and ISBE still publishes it.
#
# WHAT A DNS CHECK CANNOT SEE — measured 2026-08-05, before this list was
# written, so the limitation is recorded rather than assumed: whitecounty-il.gov
# HAS a valid MX record, and that MX host (pro.i7mail.net) resolves to a live A
# record. Every DNS-visible signal about this address is healthy. The failure
# was at SMTP delivery time. So the --verify-mx pass below is a guard against a
# DIFFERENT failure (a domain with no mail route at all), and it would NOT have
# caught White. Only a real bounce catches this class, which is why the
# evidence for each entry here is a bounce, not an inference.
#
# EFFECT: the address is dropped from the shipped roster; the clerk's NAME,
# PHONE and ADDRESS still ship, so the card keeps every contact route that
# works and simply stops offering one that doesn't. No app change is needed —
# the card already renders the e-mail row only when the field is present.
#
# RETIRING AN ENTRY: when ISBE publishes a different address for the county,
# this list stops matching, the new address ships, and the build prints a
# RETIRE line naming the stale entry. Delete it then — and if a bounce is ever
# resolved rather than re-addressed, verify by sending, never by assuming.
KNOWN_UNDELIVERABLE = {
    "clerk@whitecounty-il.gov": (
        "Hard-bounced 2026-07-31 after five days of retries (permanent failure; "
        "'421 Network error when connecting to MX server pro.i7mail.net'). "
        "Domain MX and MX-host A records were both healthy at the time — this is "
        "an SMTP-delivery failure DNS cannot see. Phone (618) 382-7211 x1 is the "
        "working route until the county publishes a deliverable address."
    ),
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")

DOH_URL = "https://dns.google/resolve"


def mx_report(roster, timeout=15):
    """Secondary guard: every shipped address's domain must have a mail route.

    Catches the failure mode the bounce list cannot anticipate — a domain that
    was decommissioned, mistyped at the source, or never had mail — by asking
    for MX over DNS-over-HTTPS (plain DNS and SMTP are commonly blocked on CI
    runners; DoH is not). A domain with MX records whose hosts all fail to
    resolve is reported too: that is a mail route pointing nowhere.

    Returns a list of (address, finding) pairs. NETWORK TROUBLE IS NOT A
    FINDING — a query that fails to complete is skipped and counted, because a
    flaky runner must never look like a dead county.
    """
    import requests  # imported here so the offline build stays dependency-free

    session = requests.Session()
    findings, checked, skipped = [], 0, 0
    cache = {}

    def query(name, rtype):
        key = (name, rtype)
        if key in cache:
            return cache[key]
        resp = session.get(DOH_URL, params={"name": name, "type": rtype},
                           headers={"Accept": "application/dns-json"}, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        code = {"MX": 15, "A": 1, "AAAA": 28}[rtype]
        answers = [a.get("data") for a in (data.get("Answer") or [])
                   if a.get("type") == code]
        cache[key] = answers
        return answers

    for county in sorted(roster):
        email = roster[county].get("email")
        if not email or "@" not in email:
            continue
        domain = email.rsplit("@", 1)[1].strip().lower()
        try:
            mx = query(domain, "MX")
            if not mx:
                findings.append((email, "no MX record for %s — mail cannot be "
                                        "delivered to this domain" % domain))
                checked += 1
                continue
            hosts = [m.split()[-1].rstrip(".") for m in mx if m.split()]
            live = [h for h in hosts if query(h, "A") or query(h, "AAAA")]
            if not live:
                findings.append((email, "MX host(s) %s do not resolve — the mail "
                                        "route points nowhere" % ", ".join(hosts)))
            checked += 1
        except Exception as exc:  # network trouble, never a finding
            skipped += 1
            print("  mx-check: skipped %s (%s)" % (domain, type(exc).__name__),
                  file=sys.stderr)
    print("mx-check: %d address(es) verified, %d skipped for network trouble, "
          "%d finding(s)" % (checked, skipped, len(findings)), file=sys.stderr)
    return findings


def norm_county(name):
    return re.sub(r"[^A-Z]", "", (name or "").upper())


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("scraper_output", help="raw JSON from il_county_clerk_scraper.py")
    ap.add_argument("out_dir", nargs="?", default=DEFAULT_OUT_DIR)
    ap.add_argument("--verify-mx", action="store_true",
                    help="also check every shipped address's domain has a live "
                         "mail route (DNS-over-HTTPS; needs network)")
    ap.add_argument("--report", help="write the bounce-guard report here (markdown)")
    args = ap.parse_args()

    with open(args.scraper_output) as f:
        records = json.load(f)
    out_dir = args.out_dir

    roster = {}
    dropped = []
    for r in records:
        title = (r.get("title") or "").upper()
        jurisdiction = r.get("jurisdiction") or ""
        # county rows only: municipal boards ("CITY OF …") are not county
        # clerks, and a title without COUNTY CLERK (e.g. EXECUTIVE DIRECTOR)
        # isn't the elected officer this roster exists to name.
        if jurisdiction.upper().startswith("CITY OF") or "COUNTY CLERK" not in title:
            continue
        name = (r.get("name") or "").strip()
        key = norm_county(jurisdiction)
        if not name or not key:
            continue
        if key in roster:
            print("FATAL: two clerk rows resolved to county %s" % key, file=sys.stderr)
            sys.exit(1)
        entry = {"name": name}
        for field in ("address", "phone", "email"):
            value = (r.get(field) or "").strip()
            if not value:
                continue
            # THE BOUNCE GUARD: a proven-undeliverable address never ships. The
            # rest of the record does, so the card keeps the routes that work.
            if field == "email" and value.lower() in KNOWN_UNDELIVERABLE:
                dropped.append((key, value, KNOWN_UNDELIVERABLE[value.lower()]))
                continue
            entry[field] = value
        roster[key] = entry

    if len(roster) != EXPECTED_COUNTIES:
        print("FATAL: resolved %d county clerks, expected exactly %d — refusing to write"
              % (len(roster), EXPECTED_COUNTIES), file=sys.stderr)
        sys.exit(1)
    if EXPECTED_MISSING & set(roster):
        print("FATAL: %s resolved a county-clerk row but is expected to be an "
              "election-commission county — source changed, review before shipping"
              % sorted(EXPECTED_MISSING & set(roster)), file=sys.stderr)
        sys.exit(1)

    # Bounce-guard reporting. A dropped address is expected and quiet-ish; a
    # STALE entry is the loud one, because it means ISBE moved on and this list
    # is now carrying a fact about an address nobody publishes any more.
    lines = []
    for key, email, reason in dropped:
        msg = "bounce-guard: dropped %s from %s — %s" % (email, key, reason)
        print(msg, file=sys.stderr)
        lines.append("- **%s** — dropped `%s`. %s" % (key.title(), email, reason))
    matched = {email.lower() for _, email, _ in dropped}
    for addr in sorted(set(KNOWN_UNDELIVERABLE) - matched):
        msg = ("bounce-guard: RETIRE %s — it is no longer published by the source, "
               "so the KNOWN_UNDELIVERABLE entry is stale and should be deleted" % addr)
        print(msg, file=sys.stderr)
        lines.append("- **RETIRE** `%s` — no longer published by ISBE; delete its "
                     "KNOWN_UNDELIVERABLE entry." % addr)

    if args.verify_mx:
        for email, finding in mx_report(roster):
            msg = "mx-check: %s — %s" % (email, finding)
            print(msg, file=sys.stderr)
            lines.append("- **MX** `%s` — %s" % (email, finding))

    if args.report:
        with open(args.report, "w") as f:
            f.write("### Clerk-roster bounce guard\n\n")
            f.write("\n".join(lines) + "\n" if lines
                    else "No undeliverable addresses dropped and no mail-route findings.\n")

    out_path = os.path.join(out_dir, "il-county-clerks.json")
    with open(out_path, "w") as f:
        json.dump(roster, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    print("wrote %s: %d county clerks (%d e-mail(s) withheld by the bounce guard)"
          % (out_path, len(roster), len(dropped)), file=sys.stderr)


if __name__ == "__main__":
    main()
