#!/usr/bin/env python3
"""
Scrape the Will County Board member roster from willcountyboard.com.

Stage 1 of the two-stage roster pipeline (same shape as
scripts/ccpsa_scraper.py + build_ccpsa_roster.py): this script produces raw
per-member records; scripts/build_will_county_board_roster.py resolves them
into data/app/will-county-board-members.json, keyed by county-board district,
which index.html's "Will County Board District" layer joins to the county's
own boundary GIS by district number.

Source (static HTML, no JS needed):
  index:   https://www.willcountyboard.com/board-members.html
           -> "District N" headings, each with member links "Name, [Role,] City"
  profile: https://www.willcountyboard.com/<member>.html
           -> "Contact Me" block: Phone, E-mail, and "Committee Assignments"

Emails on the profile pages are Cloudflare-obfuscated (rendered as
"[email protected]" with the real address hex-encoded in a data-cfemail
attribute / an /cdn-cgi/l/email-protection#<hex> href). cf_decode() reverses
that public, deterministic client-side encoding — it yields exactly the address
a browser shows the visitor (e.g. sbalich@willcounty.gov), nothing hidden. The
member's own line is taken from the "Contact Me" block, never the shared county
office number/address that also appears on the page.

Honesty: a member whose profile fails to parse keeps whatever the index gave
(name/city/role) and simply carries no phone/email/committees — the builder and
card never invent contact data. The parser drops nothing silently; it records a
per-member error instead.

Usage:
    python3 will_county_board_scraper.py [output.json]

Writes raw records (a JSON list) to output.json (default: stdout).
"""

import json
import re
import sys
import time

# Not called directly any more — get() goes through scraper_common.fetch, which
# imports requests at CALL time so stdlib-only importers stay stdlib-only. The
# module-scope import stays because validate_workflow_deps.py walks module-scope
# closures: without it the gate stops demanding `requests` in this workflow's pip
# line, and the run would break the day someone tidied that line. Every other
# scraper_common consumer keeps it for the same reason.
import requests  # noqa: F401
from bs4 import BeautifulSoup, NavigableString
from scraper_common import fetch as fetch_with_retry  # shared machinery — do not fork

INDEX_URL = "https://www.willcountyboard.com/board-members.html"
BASE = "https://www.willcountyboard.com/"
HEADERS = {"User-Agent": "districtry-roster-bot/1.0 (+https://districtry.com/il/)"}
TIMEOUT = 30
FETCH_ATTEMPTS = 5
# pages that look like member links but aren't
NON_MEMBER = {"board-members", "about-the-board", "contact-us", "district-map", "committees"}


def cf_decode(hex_token):
    """Decode a Cloudflare-obfuscated email token (data-cfemail / #<hex>)."""
    b = bytes.fromhex(hex_token)
    key = b[0]
    return "".join(chr(c ^ key) for c in b[1:])


def get(url):
    """GET with backoff on throttling, via the fleet's one shared retry loop.

    The county's edge answered a COLD, first-of-run request with 429 on
    2026-08-27, and the bare raise_for_status() this replaces turned that into
    a traceback — which froze the weekly refresh for thirteen days, because a
    failing workflow opens no PR and the shipped roster simply keeps naming
    whoever it named last. 429 and 5xx are now retried (honouring a numeric
    Retry-After, capped); 403/404 still raise at once, since a refused or moved
    page is not fixed by waiting.

    Pacing is deliberately left alone. The 429 arrived on the first request of
    the run with no prior traffic, so it is the edge's answer to this client
    rather than to a rate, and slowing the profile loop would not have
    prevented it. A run that degrades mid-way is already caught downstream:
    build_will_county_board_roster.py refuses to write below MIN_EMAILS (15 of
    the 22 members), so a throttled run fails loudly instead of shipping a
    roster with the contact details missing.

    HEADERS stays this file's own. scraper_common consolidates the retry loop
    and deliberately not the User-Agent — several sites in this fleet treat
    clients by fingerprint, so changing the identity is a per-county change
    with that county's weekly run as the witness (see its module docstring).
    """
    return fetch_with_retry(url, HEADERS, timeout=TIMEOUT,
                            attempts=FETCH_ATTEMPTS).text


def parse_index(html):
    """Return [{district, name, city, role, profile_url}] from the index page.

    One document-order pass: a "District N" string sets the current district,
    and each following member profile link is attached to it. The link text is
    the member identity itself, "Name, [Role,] City".
    """
    soup = BeautifulSoup(html, "html.parser")
    out = []
    current = None
    for node in soup.descendants:
        if isinstance(node, NavigableString):
            # some headings carry a leading zero-width space (U+200B) that
            # str.strip() doesn't remove — e.g. "​District 8" — so drop it first
            m = re.fullmatch(r"District\s+(\d+)", node.replace("​", "").strip())
            if m:
                current = int(m.group(1))
        elif getattr(node, "name", None) == "a" and node.get("href"):
            href = node["href"].strip()
            slug = re.sub(r"^.*/", "", href).replace(".html", "")
            if not href.endswith(".html") or slug in NON_MEMBER or "-" not in slug:
                continue
            txt = node.get_text(" ", strip=True).replace("​", "").strip()
            name, role, city = _parse_member_text(txt)
            if not name:
                continue
            out.append({
                "district": current,
                "name": name,
                "role": role,
                "city": city,
                "profile_url": BASE + slug + ".html",
            })
    # de-dupe by profile page, preferring the entry that carries a district AND
    # a city (a bare nav link may repeat the name with neither)
    best = {}
    for r in out:
        key = r["profile_url"]
        cur = best.get(key)
        score = (r["district"] is not None, r["city"] is not None)
        if cur is None or score > (cur["district"] is not None, cur["city"] is not None):
            best[key] = r
    return [r for r in best.values() if r["district"] is not None]


def _parse_member_text(txt):
    """"Steve Balich, Homer Glen" -> (name, None, city);
    "Joe VanDuyne, County Board Speaker, Wilmington" -> (name, role, city)."""
    parts = [p.strip() for p in txt.split(",") if p.strip()]
    if not parts:
        return None, None, None
    if len(parts) == 1:
        return parts[0], None, None
    return parts[0], (", ".join(parts[1:-1]) or None), parts[-1]


def parse_profile(html):
    """Extract {phone, email, committees} from a member profile page."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")
    result = {"phone": None, "email": None, "committees": []}

    # member phone: the number under "Contact Me" / "Phone:"
    cm = text.find("Contact Me")
    scope = text[cm:cm + 600] if cm >= 0 else text
    pm = re.search(r"Phone:?\s*(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})", scope)
    if pm:
        result["phone"] = pm.group(1).strip()

    # member email: the Cloudflare token nearest the "Contact Me" E-mail label,
    # excluding the shared countyboard@ office address
    tokens = re.findall(r'data-cfemail="([0-9a-fA-F]+)"', html) + \
        re.findall(r"/cdn-cgi/l/email-protection#([0-9a-fA-F]+)", html)
    emails = []
    for t in tokens:
        try:
            e = cf_decode(t)
            if "@" in e and "." in e.split("@")[-1]:
                emails.append(e)
        except Exception:
            continue
    member_email = next((e for e in emails if not e.lower().startswith("countyboard@")), None)
    result["email"] = member_email

    # committee assignments: the list under that heading
    ca = text.find("Committee Assignments")
    if ca >= 0:
        block = text[ca + len("Committee Assignments"):ca + 800]
        lines = [ln.strip() for ln in block.split("\n")]
        committees = []
        for ln in lines:
            if not ln or ln.replace("​", "").strip() == "":
                if committees:
                    break
                continue
            if re.match(r"(Home|Contact|District|©|Copyright|Board Members)", ln):
                break
            committees.append(ln.replace("​", "").strip())
        result["committees"] = [c for c in committees if c][:12]
    return result


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else None
    members = parse_index(get(INDEX_URL))
    records = []
    for m in members:
        rec = dict(m)
        try:
            prof = parse_profile(get(m["profile_url"]))
            rec.update(prof)
            rec["error"] = None
        except Exception as e:  # per-member isolation — one bad page never kills the run
            rec.update({"phone": None, "email": None, "committees": []})
            rec["error"] = str(e)
        records.append(rec)
        time.sleep(0.4)  # be polite to the county site

    text = json.dumps(records, ensure_ascii=False, indent=2)
    if out_path:
        with open(out_path, "w") as f:
            f.write(text + "\n")
        print(f"Wrote {out_path}: {len(records)} members", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
