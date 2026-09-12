#!/usr/bin/env python3
"""
Scrape the Lake County Board leadership roles (Chair / Vice-Chair) from the
county's own Board Members directory.

Why this scraper is ROLES-ONLY: Lake is the county whose boundary GIS
carries the officeholder data itself — member name, official phone/email,
and district page ride the LakeCounty_PoliticalBoundaries features, which
the county edits frequently (fresher than any weekly scrape could be), so
the card reads those live. The one officeholder fact the GIS does NOT
carry is board leadership: the directory page tags one member "Board
Chair" and one "Board Vice-Chair" (elected from among the 19 members —
unlike DuPage/Kane/McHenry, Lake's chair is not a separate countywide
office). This scraper captures exactly that, keyed by district, with every
member's name included so the builder can verify a full parse and the card
can refuse a stale role: index.html applies a role ONLY when the scraped
surname matches the GIS member name for that district, so a
reorganization the scrape hasn't caught yet degrades to role-less rows,
never a mislabeled chair.

Stage 2 is scripts/build_lake_county_board_roles.py ->
data/app/lake-county-board-roles.json.

Source page (Granicus/CivicPlus):
  https://www.lakecountyil.gov/2336/Board-Members
  -> per-district blocks reading "District N: NAME" + "Board Chair" /
     "Board Vice-Chair" / "Board Member". Parsed from the page text (the
     CMS markup carries no stable classes), with count guards downstream.

Fetch engines (`--engine auto`): the site's edge 403s the `requests`
stack, so the ladder is `requests`, then `stdlib`, then `wayback` (the
Internet Archive crawls Lake's site fine — recent snapshots exist — and
the newest snapshot is refused if older than WAYBACK_MAX_AGE_DAYS).
THE MIDDLE RUNG IS WHERE THE DATA COMES FROM, and this paragraph named
only two rungs until 2026-09-12, which read as though the archive were the
working path. Measured that day by scripts/probe_user_agents.py: the edge
serves /2336/Board-Members to the stdlib client — 117,290 bytes — with the
plain UA_ROSTER_BOT token, so what it refuses is urllib3's ClientHello and
not this project's name. `--engine stdlib` parses all 19 districts live.
The browser headers fetch_stdlib sends by default are therefore not what
unblocks this host; they are untested here and left alone, because a UA
change belongs with this scraper's own weekly run as the witness.
No Playwright rung: a single-page, secondary enrichment doesn't warrant a
browser install, and an edge 403 of this class doesn't clear for headless
Chromium anyway (verified on the Kendall/McHenry siblings).

Usage:
    python3 lake_county_board_roles_scraper.py [output.json]   # default: stdout
"""

import argparse
import gzip
import json
import re
import sys
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from scraper_common import fetch_stdlib, UA_CHROME_WIN_126_FULL  # noqa: E402  (shared machinery — do not fork)

DIRECTORY_URL = "https://www.lakecountyil.gov/2336/Board-Members"
HEADERS = {
    "User-Agent": UA_CHROME_WIN_126_FULL,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

BLOCK_MARKERS = (
    "errors.edgesuite.net",
    "access denied</h1>",
    "<title>access denied</title>",
    "just a moment",
    "attention required",
    "checking your browser",
    "cf-chl",
)

MEMBER_RE = re.compile(
    r"District\s+(\d+):\s*([A-Za-z.’' -]+?)\s+Board\s+(Chair|Vice-Chair|Member)\b")

WAYBACK_MAX_AGE_DAYS = 45


def _looks_blocked(html):
    low = (html or "").lower()
    return any(marker in low for marker in BLOCK_MARKERS)


def fetch_direct(retries=3, timeout=30):
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.get(DIRECTORY_URL, headers=HEADERS, timeout=timeout)
            if resp.status_code == 200 and not _looks_blocked(resp.text):
                return resp.text, None
            last_err = ("bot-management interstitial" if resp.status_code == 200
                        else "HTTP %d" % resp.status_code)
        except requests.RequestException as e:
            last_err = str(e)
        time.sleep(2 * (attempt + 1))
    raise RuntimeError("direct fetch failed: %s" % last_err)


def fetch_stdlib_rung(retries=3, timeout=30):
    """The stdlib stack with a real Chromium's client hints.

    Measured 2026-09-03: this county's Cloudflare edge answers `requests` 403
    and this stack 200 with the full 114 KB directory — the stack alone is
    enough here, unlike the Akamai counties that also need the hints. Sits
    between the direct rung and the Archive so a live page beats an archived
    one, which is the whole point of an enrichment that names who chairs what.
    """
    last_err = None
    for attempt in range(retries):
        try:
            html = fetch_stdlib(DIRECTORY_URL, timeout=timeout)
            if not _looks_blocked(html):
                return html, None
            last_err = "bot-management interstitial"
        except Exception as e:  # noqa: BLE001 — every rung failure escalates
            last_err = str(e)
        time.sleep(2 * (attempt + 1))
    raise RuntimeError("stdlib fetch failed: %s" % last_err)


def fetch_wayback():
    """Newest Internet Archive snapshot of the directory, age-guarded."""
    resp = requests.get("https://archive.org/wayback/available",
                        params={"url": DIRECTORY_URL}, headers=HEADERS, timeout=60)
    snap = (resp.json().get("archived_snapshots") or {}).get("closest") or {}
    ts = snap.get("timestamp")
    if not ts:
        raise RuntimeError("no archive snapshot available")
    age_days = (datetime.now(timezone.utc)
                - datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)).days
    if age_days > WAYBACK_MAX_AGE_DAYS:
        raise RuntimeError("newest archive snapshot is %d days old (max %d) — refusing "
                           "stale leadership data" % (age_days, WAYBACK_MAX_AGE_DAYS))
    r = requests.get("https://web.archive.org/web/%sid_/%s" % (ts, DIRECTORY_URL),
                     headers=HEADERS, timeout=120)
    body = r.content
    if body[:2] == b"\x1f\x8b":
        body = gzip.decompress(body)
    html = body.decode("utf-8", "replace")
    if r.status_code != 200 or _looks_blocked(html):
        raise RuntimeError("snapshot read failed (HTTP %d)" % r.status_code)
    return html, ts


def parse_members(html):
    text = BeautifulSoup(html, "html.parser").get_text(" ")
    text = re.sub(r"\s+", " ", text)
    records = []
    seen = set()
    for m in MEMBER_RE.finditer(text):
        district = m.group(1)
        if district in seen:
            continue
        seen.add(district)
        role = m.group(3)
        records.append({
            "district": district,
            "name": m.group(2).strip(),
            "role": None if role == "Member" else role,
        })
    return records


def main():
    ap = argparse.ArgumentParser(description="Scrape Lake County Board leadership roles.")
    ap.add_argument("out", nargs="?", default=None, help="output JSON path (default: stdout)")
    ap.add_argument("--engine", choices=["auto", "requests", "stdlib", "wayback"], default="auto")
    args = ap.parse_args()

    archived_at = None
    if args.engine == "requests":
        html, archived_at = fetch_direct()
    elif args.engine == "stdlib":
        html, archived_at = fetch_stdlib_rung()
    elif args.engine == "wayback":
        html, archived_at = fetch_wayback()
    else:
        try:
            html, archived_at = fetch_direct()
        except Exception as e:
            print("requests engine blocked (%s); trying the stdlib rung" % e,
                  file=sys.stderr)
            try:
                html, archived_at = fetch_stdlib_rung()
            except Exception as e2:
                print("stdlib rung blocked (%s); falling back to the Internet Archive" % e2,
                      file=sys.stderr)
                html, archived_at = fetch_wayback()

    records = parse_members(html)
    payload = {
        "source_url": DIRECTORY_URL,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "archived_at": archived_at,  # null when fetched live
        "members": records,
    }
    out = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w") as f:
            f.write(out + "\n")
    else:
        print(out)

    chairs = [r for r in records if r["role"] == "Chair"]
    vices = [r for r in records if r["role"] == "Vice-Chair"]
    print("Parsed %d districts (%d chair, %d vice-chair)%s"
          % (len(records), len(chairs), len(vices),
             " via archive snapshot %s" % archived_at if archived_at else " live"),
          file=sys.stderr)


if __name__ == "__main__":
    main()
