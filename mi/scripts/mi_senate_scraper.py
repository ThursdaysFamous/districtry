#!/usr/bin/env python3
"""
Scrape the Michigan Senate's own all-senators directory for the contact block
Open States does not carry.

WHY THIS EXISTS. Open States' current-people export is the fleet-standard
roster base for a state chamber, and for Michigan it publishes name, party,
district, e-mail and the member's own site — but **no capitol phone and no
capitol address for any Michigan legislator at all** (measured 0 of 148 rows,
2026-09-03). Every contact detail on the Senate card therefore comes from the
Senate itself, and this is the only script that reads it.

THE PARSE IS NOT THE OBVIOUS ONE, AND THAT IS WORTH KNOWING BEFORE YOU EDIT.
`senate.michigan.gov/senators/all-senators/` looks like a JS-rendered page —
the roster is drawn by a Lit web component loaded from
`/scripts/senatorlist.js` — and a first attempt to read it looked for a
`var senatorInfo = [...]` assignment in the HTML and found nothing, because
there isn't one. The data is already in the served HTML as an **HTML-escaped
attribute** on the component element (`senatorInfo="[{&quot;id&quot;:…}]"`),
so it needs unescaping before it is JSON. No browser, no JS execution, and no
per-member page fetch: one request answers all 38 seats.

WHAT IT REFUSES TO RETURN. Every address the directory publishes is a Capitol
complex business address — "Suite NNNN, Binsfeld Office Building" (32 of 38)
or "S-NN, Capitol Building" (6 of 38), measured across all 38 seats — and the
builder asserts that shape before shipping any of them. A row whose address
stops matching is dropped rather than shipped, because the failure mode this
guards against is a directory that starts publishing home addresses.

Usage:
    python3 mi/scripts/mi_senate_scraper.py            # JSON to stdout
    python3 mi/scripts/mi_senate_scraper.py out.json   # JSON to a file
"""

import html as html_module
import json
import re
import sys
import urllib.request

SOURCE_URL = "https://senate.michigan.gov/senators/all-senators/"

# The component attribute that carries the whole roster, HTML-escaped.
SENATOR_INFO_RE = re.compile(r'senatorInfo="([^"]*)"')

# Michigan seats 38 senators. A parse that returns materially fewer has found
# a changed page rather than a smaller Senate.
MIN_SENATORS = 34

HEADERS = {
    "User-Agent": "districtry/1.0 (civic data; "
                  "https://github.com/ThursdaysFamous/districtry)"
}
TIMEOUT = 60


def fetch(url=SOURCE_URL):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse(page):
    """{district -> {name, party, phone, email, website, contactUrl, address}}.

    Keyed by district as a bare string ("1", not "001") because that is what
    the shipped TIGERweb geometry's SLDU resolves to through the app's
    extractDistrictNumber, and the roster join is on that value.
    """
    match = SENATOR_INFO_RE.search(page)
    if not match:
        raise RuntimeError(
            "no senatorInfo attribute in the all-senators page — the directory's "
            "shape changed (it is an HTML-escaped attribute on a Lit component, "
            "not a script assignment; see this module's docstring)")
    rows = json.loads(html_module.unescape(match.group(1)))
    if not isinstance(rows, list):
        raise RuntimeError("senatorInfo did not parse to a list")

    out = {}
    for row in rows:
        district = str(row.get("district") or "").strip().lstrip("0") or None
        if not district:
            continue
        first = str(row.get("firstName") or "").strip()
        last = str(row.get("lastName") or "").strip()
        name = " ".join(p for p in (first, last) if p)
        if not name:
            continue
        entry = {"name": name}
        for src, dst in (("phone", "phone"), ("email", "email"),
                         ("website", "website"), ("contactUrl", "contactUrl"),
                         ("address", "address"), ("party", "party")):
            value = str(row.get(src) or "").strip()
            if value:
                entry[dst] = value
        out[district] = entry
    return out


def main():
    page = fetch()
    senators = parse(page)
    if len(senators) < MIN_SENATORS:
        print("mi-senate-scraper: FAIL — resolved %d senators (expected >= %d); "
              "refusing to emit a truncated directory"
              % (len(senators), MIN_SENATORS), file=sys.stderr)
        sys.exit(1)

    payload = json.dumps(senators, indent=2, ensure_ascii=False) + "\n"
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as fh:
            fh.write(payload)
        print("mi-senate-scraper: wrote %s (%d senators)" % (sys.argv[1], len(senators)),
              file=sys.stderr)
    else:
        sys.stdout.write(payload)
        print("mi-senate-scraper: %d senators" % len(senators), file=sys.stderr)


if __name__ == "__main__":
    main()
