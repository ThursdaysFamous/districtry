#!/usr/bin/env python3
"""
One-shot WEC reachability probe, designed to run FROM GITHUB ACTIONS
(phase 4 PR 5, docs/WI_PHASE4_PLAN.md — a measurement, not a layer).

Three gap records wait on one untried route. elections.wi.gov and
myvote.wi.gov sit behind a Cloudflare managed (JS) challenge — measured
2026-08-25: HTTP 403 with `Cf-Mitigated: challenge` on every path tried,
including /media/<id>/download file URLs and MyVote's own API routes, to
curl with full browser headers and to WebFetch alike. That block gates
the statewide polling-place pairing (gap `ward-polling-places`), the
early-voting/drop-box cells, and the municipal-clerks bulk file. The one
route never tried is the CPD precedent (scripts/cpd_district_scraper.py):
a REAL headless Chromium executes a managed challenge's JavaScript and
reads the page a browser user sees — no CAPTCHA-solving, no evasion, no
fingerprint-spoofing, just a genuine browser — and the development
sandbox's Chromium has no egress, so from THERE the route is unavailable
rather than untried. GitHub's runners are the vantage this script exists
for; until it runs once, the block is recorded as measured-from-here,
not permanent.

WHAT IT DOES: for each target, try a plain requests fetch first (the
CPD `--engine auto` shape — if that reads the page, the site is simply
open and no browser is needed); when the plain client is refused, drive
headless Chromium at it and give the managed challenge a bounded window
to clear (WEC_CHALLENGE_WAIT_S, default 120 — the CPD knob's history:
20s cleared until 2026-07-28, 60s until ~2026-08-04, and Cloudflare
hands a datacenter IP a harder challenge than a residential one). A
challenge still on screen after the window is a REFUSAL and is recorded
as one — nothing here retries past it, and an interactive Turnstile is
an access control this project does not attempt. After a WEC page
clears, anchors matching bulk-data shapes (/media/<id>/download, .csv,
.xlsx, .zip) are harvested and up to HARVEST_CAP of them re-fetched
through the SAME browser session, because the 2026-08-25 measurement
found the file URLs blocked independently of the pages — a cleared front
door with refused downloads is a real, and different, outcome.

TWO SECONDARY TARGETS ride the same run because this vantage is exactly
what their records are owed: city.milwaukee.gov (gap
`mpd-district-leadership` — "refuses every automated client this project
can send", all of them sandbox-side) and badgersheriffs.com (the
phase-4 appendix's sheriff-roster second publisher: proxy CONNECT 502
from the sandbox, "CI probe owed").

WHAT IT NEVER DOES: parse, store, or ship any of the content. The
output is a measurement — per-target outcomes, headers, and harvested
link statuses — written to --out as JSON, echoed as a Markdown table to
GITHUB_STEP_SUMMARY when set, and uploaded as a run artifact by
.github/workflows/wi-wec-probe.yml. The outcome lands in
docs/DATA_LAYER_GUIDEBOOK.md (the gap blockers) by a follow-up PR,
whichever way it goes.

Exit status: 0 when every target produced a measurement (refused IS a
measurement); 1 only when the probe itself failed to run (browser
missing, script error) — so a red run means "measure again", never
"WEC said no".

Usage:
    python3 wi/scripts/wi_wec_probe.py --out wec-probe-results.json

THE DISPATCH WORKFLOW THAT RAN THIS IS RETIRED (2026-08-27). It was a
one-shot: it ran, its finding is recorded in the guidebook with the run
ids above, and a dispatch-only workflow that will never fire again is
dead weight in the workflow list. THIS SCRIPT STAYS because the finding
is a measurement somebody may need to re-take — access granted from CI
has been withdrawn before — and re-taking it means re-adding a
workflow_dispatch workflow that pip-installs the deps below and runs
this file. It CANNOT be re-run from a development sandbox: the whole
point of the original run was that the vantage is what differs.
"""

import argparse
import json
import os
import re
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests

# Same genuine-browser UA the CPD scraper sends (scripts/scraper_common.py's
# UA_CHROME_WIN_124 — inlined because wi/scripts has no path to that module).
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Substrings that mean a Cloudflare interstitial (not the real page) is on
# screen — the CPD scraper's marker list, used to tell blocked from fetched.
CHALLENGE_MARKERS = (
    "just a moment",
    "attention required",
    "checking your browser",
    "cf-chl",
    "challenges.cloudflare.com/turnstile",
)

BULK_LINK_RE = re.compile(
    r"/media/\d+/download|\.csv(?:$|[?#])|\.xlsx(?:$|[?#])|\.zip(?:$|[?#])",
    re.IGNORECASE)
HARVEST_CAP = 5

TARGETS = [
    {
        "id": "wec-front",
        "url": "https://elections.wi.gov/",
        "why": ("WEC's front door — the 2026-08-25 measurement got 403 "
                "Cf-Mitigated: challenge here from every sandbox client"),
        "harvest": True,
    },
    {
        "id": "myvote-front",
        "url": "https://myvote.wi.gov/en-us/",
        "why": ("MyVote's front door — the lookup the ward card links "
                "because the pairing behind it cannot be read as data"),
        "harvest": True,
    },
    {
        "id": "mke-police",
        "url": "https://city.milwaukee.gov/police",
        "why": ("secondary: gap mpd-district-leadership — MPD's district "
                "pages refused every sandbox client; CI vantage untried"),
        "harvest": False,
    },
    {
        "id": "badgersheriffs",
        "url": "https://badgersheriffs.com/",
        "why": ("secondary: sheriff-roster second publisher — proxy "
                "CONNECT 502 from the sandbox, CI probe owed"),
        "harvest": False,
    },
]


def looks_like_challenge(html):
    low = (html or "").lower()
    return any(m in low for m in CHALLENGE_MARKERS)


def page_title(html):
    m = re.search(r"<title[^>]*>(.*?)</title>", html or "",
                  re.IGNORECASE | re.DOTALL)
    return re.sub(r"\s+", " ", m.group(1)).strip()[:120] if m else None


def plain_fetch(session, url):
    """Rung 1: the plain-HTTP client. Returns (record, html_when_cleared).

    THE HOST'S RULES ARE READ FIRST, with the identity this probe sends.
    Measured from a GitHub runner on 2026-10-01, three of this file's four hosts
    publish a policy permitting the paths it reads. The fourth,
    badgersheriffs.com, has NO DNS RECORD AT ALL, so its robots.txt is
    unreachable and RFC 9309 2.3.1.4 disallows — which is the right answer for a
    domain that no longer exists, and the seam stops this probe at it.
    """
    require_robots_once(url, UA, headers=HEADERS, label="wi-wec-probe")
    rec = {"engine": "requests"}
    try:
        resp = session.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException as e:
        rec["outcome"] = "error"
        rec["detail"] = str(e)[:300]
        return rec, None
    rec["status"] = resp.status_code
    rec["cf_mitigated"] = resp.headers.get("Cf-Mitigated")
    rec["server"] = resp.headers.get("Server")
    rec["bytes"] = len(resp.content)
    rec["title"] = page_title(resp.text)
    if resp.status_code == 200 and not looks_like_challenge(resp.text):
        rec["outcome"] = "cleared"
        return rec, resp.text
    rec["outcome"] = "refused"
    rec["detail"] = ("challenge interstitial (HTTP %d)" % resp.status_code
                     if looks_like_challenge(resp.text)
                     else "HTTP %d" % resp.status_code)
    return rec, None


class BrowserProbe:
    """Rung 2: a real headless Chromium, the CPD PlaywrightFetcher's shape.
    The managed challenge's JS runs in a genuine browser; a bounded wait
    lets it clear, and a challenge still on screen after the window is a
    refusal — never retried past, never worked around."""

    def __init__(self):
        from playwright.sync_api import sync_playwright
        self.wait_s = int(os.environ.get("WEC_CHALLENGE_WAIT_S", "120"))
        self._pw = sync_playwright().start()
        exe = os.environ.get("WEC_CHROMIUM_EXECUTABLE")
        if exe:
            self.browser = self._pw.chromium.launch(headless=True,
                                                    executable_path=exe)
        else:
            self.browser = self._pw.chromium.launch(headless=True)
        self.context = self.browser.new_context(
            user_agent=UA, locale="en-US",
            viewport={"width": 1366, "height": 900})

    def fetch(self, url):
        rec = {"engine": "chromium", "challenge_wait_s": self.wait_s}
        page = self.context.new_page()
        try:
            start = time.time()
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            while (time.time() - start < self.wait_s
                   and looks_like_challenge(page.content())):
                page.wait_for_timeout(1000)
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            html = page.content()
            rec["seconds"] = round(time.time() - start, 1)
            rec["title"] = page_title(html)
            rec["final_url"] = page.url
            if looks_like_challenge(html):
                rec["outcome"] = "refused"
                rec["detail"] = ("challenge did not clear within %ds"
                                 % self.wait_s)
                return rec, None
            rec["outcome"] = "cleared"
            return rec, html
        except Exception as e:
            rec["outcome"] = "error"
            rec["detail"] = str(e)[:300]
            return rec, None
        finally:
            page.close()

    def fetch_link(self, url):
        """Re-fetch a harvested bulk link through the SAME browser session
        (its cookies carry any clearance), reading only status + headers."""
        rec = {"url": url}
        try:
            resp = self.context.request.get(url, timeout=45000)
            rec["status"] = resp.status
            rec["content_type"] = (resp.headers or {}).get("content-type")
            body = resp.body()
            rec["bytes"] = len(body)
            rec["challenge"] = looks_like_challenge(
                body[:4096].decode("utf-8", "replace"))
            resp.dispose()
        except Exception as e:
            rec["error"] = str(e)[:200]
        return rec

    def close(self):
        try:
            self.context.close()
            self.browser.close()
        finally:
            self._pw.stop()


def harvest_links(html, base_url):
    seen, out = set(), []
    for m in re.finditer(r"""href\s*=\s*["']([^"']+)["']""", html or "",
                         re.IGNORECASE):
        href = urljoin(base_url, m.group(1))
        if BULK_LINK_RE.search(href) and href not in seen:
            seen.add(href)
            out.append(href)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    session = requests.Session()
    browser = None
    operational_failure = None
    results = []

    for t in TARGETS:
        entry = {"id": t["id"], "url": t["url"], "why": t["why"], "rungs": []}
        plain, html = plain_fetch(session, t["url"])
        entry["rungs"].append(plain)
        if plain["outcome"] == "cleared":
            entry["outcome"] = "open"  # plain client reads it; no browser needed
        else:
            if browser is None:
                try:
                    browser = BrowserProbe()
                except Exception as e:
                    operational_failure = ("chromium unavailable: %s"
                                           % str(e)[:200])
                    entry["outcome"] = "not-measured"
                    entry["rungs"].append({"engine": "chromium",
                                           "outcome": "error",
                                           "detail": operational_failure})
                    results.append(entry)
                    continue
            brec, bhtml = browser.fetch(t["url"])
            entry["rungs"].append(brec)
            entry["outcome"] = ("cleared-by-browser"
                                if brec["outcome"] == "cleared"
                                else "refused" if brec["outcome"] == "refused"
                                else "not-measured")
            html = bhtml
        if t["harvest"] and html:
            links = harvest_links(html, t["url"])
            entry["bulk_links_found"] = len(links)
            entry["bulk_links"] = links[:25]
            probes = []
            for link in links[:HARVEST_CAP]:
                if browser is not None:
                    probes.append(browser.fetch_link(link))
                else:
                    prec, _ = plain_fetch(session, link)
                    prec["url"] = link
                    probes.append(prec)
            entry["bulk_link_probes"] = probes
        results.append(entry)
        print("%s: %s" % (t["id"], entry["outcome"]), file=sys.stderr)

    if browser is not None:
        browser.close()

    doc = {
        "probed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "vantage": ("github-actions" if os.environ.get("GITHUB_ACTIONS")
                    else "local"),
        "challenge_wait_s": int(os.environ.get("WEC_CHALLENGE_WAIT_S", "120")),
        "operational_failure": operational_failure,
        "targets": results,
    }
    with open(args.out, "w") as f:
        json.dump(doc, f, indent=1)
        f.write("\n")

    def cell(s):
        # Playwright errors are multiline call logs; a table cell is one line.
        return re.sub(r"\s+", " ", str(s)).strip()[:160]

    lines = ["## WEC probe — %s vantage" % doc["vantage"], "",
             "| target | outcome | plain rung | browser rung |",
             "|---|---|---|---|"]
    for e in results:
        plain = next((r for r in e["rungs"] if r["engine"] == "requests"), {})
        brow = next((r for r in e["rungs"] if r["engine"] == "chromium"), None)
        lines.append("| %s | **%s** | %s | %s |" % (
            e["id"], e["outcome"],
            cell(plain.get("detail") or "HTTP %s" % plain.get("status")),
            cell((brow.get("detail") or "cleared in %ss" % brow.get("seconds"))
                 if brow else "not needed")))
    for e in results:
        if e.get("bulk_link_probes"):
            lines.append("")
            lines.append("**%s** bulk links (%d found, %d probed):"
                         % (e["id"], e["bulk_links_found"],
                            len(e["bulk_link_probes"])))
            for p in e["bulk_link_probes"]:
                lines.append("- `%s` -> %s" % (
                    p["url"],
                    p.get("error") or "HTTP %s, %s, %s bytes%s" % (
                        p.get("status"), p.get("content_type"),
                        p.get("bytes"),
                        " (CHALLENGE BODY)" if p.get("challenge") else "")))
    summary = "\n".join(lines)
    print(summary)
    step = os.environ.get("GITHUB_STEP_SUMMARY")
    if step:
        with open(step, "a") as f:
            f.write(summary + "\n")

    if operational_failure:
        print("PROBE INCOMPLETE: %s" % operational_failure, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
