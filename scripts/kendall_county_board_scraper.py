#!/usr/bin/env python3
"""
Scrape the Kendall County Board member roster from kendallcountyil.gov.

Stage 1 of the two-stage roster pipeline (same shape as
scripts/will_county_board_scraper.py + build_will_county_board_roster.py):
this script produces raw per-member records;
scripts/build_kendall_county_board_roster.py resolves them into
data/app/kendall-county-board-members.json, keyed by county-board district
("1"/"2"), which index.html's consolidated county-board layer joins to the
county's own County_Board_2010 boundary by district number.

Source (Granicus CMS pages):
  listing: https://www.kendallcountyil.gov/county-board/board-members
           -> one content_area div with <strong> section headings
              ("Chairman", "... District #1", "... District #2"), each
              followed by a <ul> of member links. The Chairman appears ONLY
              in his own section, suffixed "- District #N" — he is merged
              into that district with role "Chairman".
  member:  https://www.kendallcountyil.gov/county-board/board-members/<slug>
           -> <strong>District</strong>: District N
              <strong>Contact:</strong> block with the member's mailto link
              (HTML-entity-encoded href; BeautifulSoup decodes it) and, for
              some members, a phone number as plain text
              <strong>Term Expiration</strong>: <date>

Fetch engines (`--engine`): the county fronts the site with Akamai bot
management, which answers plain HTTP clients from datacenter egress with an
"Access Denied" (errors.edgesuite.net) page or a TCP reset — and the sibling
McHenry scraper's first CI run (2026-07-23) proved this class of block is
IP-reputation based: it never "clears" for a runner even in a genuine
headless Chromium. `--engine auto` (default) is therefore a three-rung
ladder: `requests` first, `playwright` second (covers JS-challenge fronts
and residential-ish egress), and `wayback` last — ask the Internet Archive's
Save Page Now to capture a fresh copy with the Archive's own crawler and
read the archived original, falling back to the newest existing snapshot
when a save fails, refused entirely if the newest snapshot is older than
WAYBACK_MAX_AGE_DAYS. VERIFIED 2026-07-23: the county currently blocks the
Archive's crawler too (authenticated SPN2 job -> status_ext
error:no-request), so every rung fails; the weekly workflow converts that
total failure into a standing tracking issue (green run), the shipped
roster keeps its last hand-verified state, and automation resumes
untouched the moment any rung unblocks. Manual refresh: re-verify against
the county's directory and rebuild via
build_kendall_county_board_roster.py on a hand-assembled raw file (see the
seeded initial roster's commit for the shape).

RESOLVED 2026-09-03 — the "every rung fails" state above lasted from
2026-07-23 to today and is over. The block was never total: the county's
Akamai edge refuses the `requests` stack and serves the STDLIB stack sending
a real Chromium's Sec-CH-UA client hints, and it needs BOTH — neither the
stack nor the hints alone moves it (the leave-one-out matrix is in
scraper_common beside UA_HINTS_CHROME_126). That second opinion is the one
validate_card_links has taken on a 403 since 2026-08-29; this ladder simply
never had it. It is now the rung between `requests` and `playwright`, and
`--engine auto` reaches it without a browser or the Archive.

The scrape reproduces the hand-verified roster EXACTLY — same members, same
districts, same contact details, the shipped file content-identical — which
is the check that matters: a rung that returns a page is not the same as a
rung that returns the right data. Read the two paragraphs above as history,
not as current state.

No evasion anywhere on the ladder: the content is
always the county's own page, fetched either directly or through a public
archive, and records fetched via the archive carry `archived_at` for
provenance.

Notes on data honesty (per project conventions):
- A field that can't be found is stored null, never guessed. The member's
  own mailto/phone are taken from the page's Contact block; a mailto anchor
  with no visible text is skipped (the live pages carry stray empty anchors
  from CMS editing).
- Home/street addresses on the member pages are deliberately NOT collected:
  the card convention surfaces office locations, and these are personal
  addresses.
- Every record includes `source_url` and `scraped_at` for traceability.

Usage:
    python3 kendall_county_board_scraper.py [output.json]
    python3 kendall_county_board_scraper.py --engine playwright out.json
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from scraper_common import (  # noqa: E402  (shared machinery — do not fork)
    UA_CHROME_WIN_126_FULL,
    UA_HINTS_CHROME_126,
    fetch_stdlib,
    require_robots_allowed,
)

BASE = "https://www.kendallcountyil.gov"
LISTING_PATH = "/county-board/board-members"
HEADERS = {
    "User-Agent": UA_CHROME_WIN_126_FULL,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Substrings that mean a bot-management interstitial (not the real page) came
# back. Kendall's is Akamai ("Access Denied" / errors.edgesuite.net); the
# Cloudflare markers are kept from the CPD scraper in case the county ever
# changes CDNs.
BLOCK_MARKERS = (
    "errors.edgesuite.net",
    "access denied</h1>",
    "<title>access denied</title>",
    "just a moment",
    "attention required",
    "checking your browser",
    "cf-chl",
)

MEMBER_LINK_RE = re.compile(r"/county-board/board-members/([a-z0-9-]+)$")
DISTRICT_RE = re.compile(r"district\s*#?\s*(\d+)", re.IGNORECASE)
PHONE_RE = re.compile(r"\b\d{3}[.\-\s]\d{3}[.\-\s]\d{4}\b")


def _looks_blocked(html):
    low = (html or "").lower()
    return any(marker in low for marker in BLOCK_MARKERS)


class RequestsFetcher:
    """Plain HTTP fetch — works if the runner's egress isn't challenged."""

    engine = "requests"
    # The client this rung crawls with, so its robots.txt read is made by
    # the same client (require_robots_for below). HEADERS carries a
    # User-Agent and no Sec-CH-UA hints, which is exactly the rung this
    # county's bot manager refuses — the file has to be asked for as this
    # client all the same, never as a heavier one.
    robots_client = ("requests", HEADERS)

    def __init__(self):
        self.session = requests.Session()

    def fetch(self, url, retries=3, timeout=25):
        last_err = None
        for attempt in range(retries):
            try:
                resp = self.session.get(url, headers=HEADERS, timeout=timeout)
                if resp.status_code == 200 and not _looks_blocked(resp.text):
                    return resp.text
                last_err = (
                    "bot-management interstitial"
                    if resp.status_code == 200
                    else "HTTP %d" % resp.status_code
                )
            except requests.RequestException as e:
                last_err = str(e)
            time.sleep(1.5 * (attempt + 1))
        raise RuntimeError("Failed to fetch %s: %s" % (url, last_err))

    def close(self):
        self.session.close()


class StdlibFetcher:
    """Fetch through the STDLIB stack with a real Chromium's client hints.

    Added 2026-09-03, when the block this county has been carried by hand
    since July was re-measured and found to answer. The county's Akamai bot
    manager needs BOTH a non-urllib3 TLS stack and the Sec-CH-UA hints; the
    leave-one-out matrix and the reasoning are in scraper_common beside the
    constants. That is the same second opinion validate_card_links has taken
    on a 403 since 2026-08-29 — this scraper's ladder simply never had it.

    No evasion: the content is the county's own page, fetched with headers a
    browser sends, and a managed challenge (which this is not) stays unanswered.
    """

    engine = "stdlib"
    # fetch_stdlib below is called with no headers, so it sends
    # UA_HINTS_CHROME_126 — a different client from the rung above, and the
    # one this county serves. It asks for robots.txt as itself.
    robots_client = ("stdlib", UA_HINTS_CHROME_126)

    def fetch(self, url, retries=3, timeout=30):
        last_err = None
        for attempt in range(retries):
            try:
                html = fetch_stdlib(url, timeout=timeout)
                if not _looks_blocked(html):
                    return html
                last_err = "bot-management interstitial"
            except Exception as e:  # noqa: BLE001 — every rung failure escalates
                last_err = str(e)
            time.sleep(1.5 * (attempt + 1))
        raise RuntimeError("Failed to fetch %s: %s" % (url, last_err))

    def close(self):
        pass


class PlaywrightFetcher:
    """Fetch through a real headless Chromium (mirrors cpd_district_scraper's
    fetcher: a genuine browser, no evasion)."""

    engine = "playwright"
    # A real Chromium sends the Sec-CH-UA hints itself, under the context's
    # own User-Agent (HEADERS's), so that is the pair its robots read uses.
    robots_client = ("playwright",
                     dict(UA_HINTS_CHROME_126, **{"User-Agent": HEADERS["User-Agent"]}))

    def __init__(self, timeout=45000, challenge_wait_s=15):
        from playwright.sync_api import sync_playwright

        self.timeout = timeout
        self.challenge_wait_s = challenge_wait_s
        self._pw = sync_playwright().start()
        self.browser = self._launch(self._pw)
        self.context = self.browser.new_context(
            user_agent=HEADERS["User-Agent"],
            locale="en-US",
            viewport={"width": 1366, "height": 900},
        )

    def _launch(self, pw):
        exe = os.environ.get("KENDALL_CHROMIUM_EXECUTABLE")
        if exe:
            return pw.chromium.launch(headless=True, executable_path=exe)
        try:
            return pw.chromium.launch(headless=True)
        except Exception:
            fallback = os.path.join(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", ""), "chromium")
            if fallback != "chromium" and os.path.exists(fallback):
                return pw.chromium.launch(headless=True, executable_path=fallback)
            raise

    def fetch(self, url, retries=2):
        last_err = None
        for attempt in range(retries + 1):
            page = self.context.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                start = time.time()
                while time.time() - start < self.challenge_wait_s and _looks_blocked(page.content()):
                    page.wait_for_timeout(1000)
                try:
                    page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass
                html = page.content()
                if not _looks_blocked(html):
                    return html
                last_err = "bot-management block did not clear within %ds" % self.challenge_wait_s
            except Exception as e:
                last_err = str(e)
            finally:
                page.close()
            time.sleep(1.5 * (attempt + 1))
        raise RuntimeError("Failed to fetch %s: %s" % (url, last_err))

    def close(self):
        try:
            self.context.close()
            self.browser.close()
        finally:
            self._pw.stop()


# Reject archive copies older than this: a stale snapshot could silently miss
# a new appointee for months, which is worse than a loud failed run (the
# weekly workflow just fails visibly and a human looks).
WAYBACK_MAX_AGE_DAYS = 45


class WaybackFetcher:
    """Terminal fallback: fetch the page through the Internet Archive. Save
    Page Now captures a fresh copy with the Archive's own crawler — which the
    county does not block (the site's existing snapshots prove it) — and the
    raw archived original (`id_` URL) is read back. If the save fails, the
    newest existing snapshot serves, but never one older than
    WAYBACK_MAX_AGE_DAYS. Not evasion: a public archive of the county's own
    page, with the copy's timestamp surfaced for provenance."""

    engine = "wayback"
    # None means this rung never fetches the COUNTY's host, so the county's
    # robots.txt is not its question: the Archive's own crawler fetches the
    # page and we read the Archive. The Archive's policy is therefore what
    # would gate this rung, and it is deliberately NOT wired yet, on a
    # measurement: archive.org serves a 238-byte policy permitting
    # /wayback/available, while web.archive.org could not be read at all from
    # this project's sandbox on 2026-09-30 — three reads through the shared
    # reader and a plain curl all reset the connection. That is a fact about
    # the sandbox and says nothing about the Internet Archive, so wiring a
    # reading nobody has taken would risk stopping a working weekly refresh
    # on an unreachable-robots verdict. Measure it from a runner first.
    robots_client = None

    def __init__(self):
        self.session = requests.Session()
        self.last_archived_at = None  # timestamp of the copy the last fetch used

    def _save_authenticated(self, url, key, secret):
        """SPN2 (POST + job polling) with an archive.org API key — the
        reliable path when the runner's shared IP has exhausted the anonymous
        quota. Keys ride the ARCHIVE_SPN_ACCESS_KEY / ARCHIVE_SPN_SECRET_KEY
        env vars (repo secrets in CI); absent keys skip straight to the
        anonymous route."""
        auth = {"Accept": "application/json", "Authorization": "LOW %s:%s" % (key, secret)}
        try:
            r = self.session.post("https://web.archive.org/save",
                                  headers=dict(HEADERS, **auth),
                                  data={"url": url}, timeout=60)
            if r.status_code != 200:
                print("SPN2 save POST (%s): HTTP %d — %s"
                      % (url, r.status_code, r.text[:200].replace("\n", " ")), file=sys.stderr)
                return None
            try:
                payload = r.json()
            except ValueError:
                print("SPN2 save POST (%s): non-JSON response — %s"
                      % (url, r.text[:200].replace("\n", " ")), file=sys.stderr)
                return None
            job = payload.get("job_id")
            if not job:
                print("SPN2 save POST (%s): no job_id — %s"
                      % (url, str(payload)[:200]), file=sys.stderr)
                return None
            for _ in range(30):  # up to ~2.5 minutes per capture
                time.sleep(5)
                s = self.session.get("https://web.archive.org/save/status/" + job,
                                     headers=dict(HEADERS, **auth), timeout=30).json()
                if s.get("status") == "success":
                    return s.get("timestamp")
                if s.get("status") == "error":
                    print("SPN2 job (%s) failed: %s" % (url, str(s)[:200]), file=sys.stderr)
                    return None
            print("SPN2 job (%s): still pending after polling window" % url, file=sys.stderr)
        except requests.RequestException as e:
            print("SPN2 save (%s): %s" % (url, e), file=sys.stderr)
        return None

    def _save(self, url):
        """Ask Save Page Now for a fresh capture; return its timestamp or None."""
        key = os.environ.get("ARCHIVE_SPN_ACCESS_KEY")
        secret = os.environ.get("ARCHIVE_SPN_SECRET_KEY")
        if key and secret:
            ts = self._save_authenticated(url, key, secret)
            if ts:
                return ts
        try:
            resp = self.session.get(
                "https://web.archive.org/save/" + url,
                headers=HEADERS, timeout=180, allow_redirects=True)
            m = re.search(r"/web/(\d{14})", resp.url or "")
            if not m:
                m = re.search(r"/web/(\d{14})", resp.headers.get("Content-Location", ""))
            if resp.status_code == 200 and m:
                return m.group(1)
        except requests.RequestException:
            pass
        return None

    def _latest(self, url):
        """Newest existing snapshot's timestamp, or None."""
        try:
            resp = self.session.get(
                "https://archive.org/wayback/available",
                params={"url": url}, headers=HEADERS, timeout=60)
            snap = (resp.json().get("archived_snapshots") or {}).get("closest") or {}
            return snap.get("timestamp") or None
        except (requests.RequestException, ValueError):
            return None

    def fetch(self, url, retries=1):
        last_err = None
        for attempt in range(retries + 1):
            ts = self._save(url) or self._latest(url)
            if ts is None:
                last_err = "no archive snapshot available"
                time.sleep(3 * (attempt + 1))
                continue
            age_days = (datetime.now(timezone.utc)
                        - datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)).days
            if age_days > WAYBACK_MAX_AGE_DAYS:
                last_err = ("newest archive snapshot is %d days old (max %d) — refusing "
                            "stale officeholder data" % (age_days, WAYBACK_MAX_AGE_DAYS))
                break
            try:
                resp = self.session.get(
                    "https://web.archive.org/web/%sid_/%s" % (ts, url),
                    headers=HEADERS, timeout=120)
                if resp.status_code == 200 and not _looks_blocked(resp.text):
                    self.last_archived_at = ts
                    return resp.text
                last_err = ("archived copy is itself a block page" if resp.status_code == 200
                            else "HTTP %d reading snapshot %s" % (resp.status_code, ts))
            except requests.RequestException as e:
                last_err = str(e)
            time.sleep(3 * (attempt + 1))
        raise RuntimeError("Failed to fetch %s via the Internet Archive: %s" % (url, last_err))

    def close(self):
        self.session.close()


def require_robots_for(fetcher, label):
    """Read this county's robots.txt before this rung's first fetch of it, with
    the client the rung will crawl with.

    WHY PER RUNG AND NOT ONCE. The ladder below is three different clients, and
    this county answers two of them differently. Measured 2026-09-30, four reads
    per client: the requests rung, whose HEADERS carry a User-Agent and no
    Sec-CH-UA hints, is refused its own robots.txt with HTTP 403 four times of
    four, while the stdlib rung (UA_HINTS_CHROME_126, which carries them) is
    served a 6,641-byte policy four times of four — no rule in its one binding
    group matches the pages this scraper reads, and it states no Crawl-delay and
    no Content-Signal. THE HINTS ARE THE WHOLE DIFFERENCE, which is the same
    discriminator #1271 measured on these two hosts' pages. An earlier reading
    of this called the host flaky, on a probe that silently varied the header set
    as well as the client; repeated with one variable it is stable both ways.

    Both readings permit — a 403 on robots.txt is RFC 9309 2.3.1.3
    "unavailable", which allows, per Adam's ruling of 2026-09-29 (#1271) — so
    asking per rung costs nothing here and keeps the fleet's consistency rule:
    read the file as the client that crawls, never escalate to a heavier client
    to obtain it, and never probe a second client on a host that already serves
    the first. Each read here accompanies a crawl by that same client, which is
    a different thing from probing.

    THE POLICY IS THE CMS VENDOR'S AND NOT THIS COUNTY'S. The same 6,641 bytes,
    byte-identical by md5, come back from www.kendallcountyil.gov,
    www.mchenrycountyil.gov and www.joliet.gov — three independent governments on
    one vendor's default, 226 Disallow rules aimed at that platform's own admin
    and asset paths. So a permission read out of it says what the vendor shipped
    rather than what the county chose, which is worth knowing before anybody
    cites it as a county's decision. It is still the policy published at the
    county's own host, so it is still what binds.

    IT EXITS RATHER THAN SKIPPING TO THE NEXT RUNG, and that is correct rather
    than a lost fallback: every reading that refuses is a property of the HOST
    and not of the client — a real `*` Disallow, a 5xx, an unreachable host, a
    challenge-fronted file — so a refusal read by one rung is a refusal to all
    of them. The one client-dependent answer, 403, now permits for everyone.

    A rung whose robots_client is None does not fetch this county's host at all
    (the Archive rung); see its own note.
    """
    if fetcher.robots_client is None:
        return None
    client, headers = fetcher.robots_client
    return require_robots_allowed(
        BASE + LISTING_PATH, headers["User-Agent"], headers=headers,
        label="%s (%s rung)" % (label, client))


def make_fetcher(engine):
    if engine == "requests":
        return RequestsFetcher()
    if engine == "stdlib":
        return StdlibFetcher()
    if engine == "playwright":
        return PlaywrightFetcher()
    if engine == "wayback":
        return WaybackFetcher()
    raise ValueError("unknown engine: %s" % engine)


def clean(text):
    if text is None:
        return None
    text = re.sub(r"[\s ]+", " ", text).strip()
    return text or None


def parse_listing(html):
    """Return ordered [{slug, name, url, district, role}] from the listing's
    content area. District comes from the section heading; the Chairman
    section's members get role "Chairman" and their district from the
    "- District #N" suffix on their own list line."""
    soup = BeautifulSoup(html, "html.parser")
    members = []
    seen = set()
    for area in soup.select("div.content_area"):
        section = None  # "chairman" | district number string
        for el in area.find_all(["p", "ul"]):
            if el.name == "p":
                strong = el.find("strong")
                text = clean(el.get_text()) or ""
                if strong:
                    if re.search(r"\bchairman\b", text, re.IGNORECASE):
                        section = "chairman"
                    else:
                        m = DISTRICT_RE.search(text)
                        section = m.group(1) if m else None
                continue
            if section is None:
                continue
            for li in el.find_all("li"):
                a = li.find("a", href=True)
                if not a:
                    continue
                m = MEMBER_LINK_RE.search(a["href"].split("?")[0].rstrip("/"))
                if not m:
                    continue
                slug = m.group(1)
                if slug in seen:
                    continue
                seen.add(slug)
                name = clean(a.get_text())
                li_text = clean(li.get_text()) or ""
                if section == "chairman":
                    dm = DISTRICT_RE.search(li_text)
                    district = dm.group(1) if dm else None
                    role = "Chairman"
                else:
                    district = section
                    role = None
                members.append({
                    "slug": slug,
                    "name": name,
                    "url": urljoin(BASE, "/county-board/board-members/" + slug),
                    "district": district,
                    "role": role,
                })
    return members


def parse_member_page(html):
    """Return {district, email, phone, term_expiration} from a member page's
    OWN content area (all nullable — never guessed).

    The pages carry several content_area divs — a general county-board
    contact widget (KCBoard@ email + the shared office number) renders
    before the member's block — so the member's area is identified by its
    signature labels (<strong>District</strong> / <strong>Term
    Expiration</strong> / <strong>Contact:</strong>), and email/phone are
    read ONLY inside it, never from the shared-office widget."""
    soup = BeautifulSoup(html, "html.parser")
    area = None
    for candidate in soup.select("div.content_area"):
        for strong in candidate.find_all("strong"):
            label = clean(strong.get_text()) or ""
            if re.fullmatch(r"(district|term expiration|contact)\s*:?", label, re.IGNORECASE):
                area = candidate
                break
        if area is not None:
            break
    if area is None:
        return {"district": None, "email": None, "phone": None, "term_expiration": None}

    district = None
    term = None
    for strong in area.find_all("strong"):
        label = clean(strong.get_text()) or ""
        # value = the text following THIS label inside the same paragraph
        # (some pages put two labels in one <p>, so slice after the label
        # rather than taking the whole paragraph)
        parent_text = clean(strong.parent.get_text()) or ""
        idx = parent_text.lower().find(label.lower())
        value = clean(parent_text[idx + len(label):].lstrip(" :")) if idx >= 0 else None
        if re.fullmatch(r"district\s*:?", label, re.IGNORECASE) and value:
            m = DISTRICT_RE.search(value)
            if m:
                district = m.group(1)
        elif re.fullmatch(r"term expiration\s*:?", label, re.IGNORECASE) and value:
            term = value

    # the member's own mailto; anchors with no visible text are CMS editing
    # strays on the live pages and are skipped
    email = None
    for a in area.find_all("a", href=re.compile(r"^mailto:", re.IGNORECASE)):
        visible = clean(a.get_text())
        addr = clean(a["href"][len("mailto:"):].split("?")[0])
        if visible and addr:
            email = addr
            break

    # a member phone, when present, is plain text inside the Contact block
    phone = None
    for p in area.find_all("p"):
        if p.find("strong") and re.search(r"contact", p.find("strong").get_text(), re.IGNORECASE):
            m = PHONE_RE.search(p.get_text())
            if m:
                phone = m.group(0)
            break
    if phone is None:
        m = PHONE_RE.search(area.get_text())
        if m:
            phone = m.group(0)

    return {"district": district, "email": email, "phone": phone, "term_expiration": term}


def scrape_all(fetcher, delay=0.75, verbose=True, listing_html=None):
    if listing_html is None:
        listing_html = fetcher.fetch(BASE + LISTING_PATH)
    listing = parse_listing(listing_html)
    if verbose:
        print("listing yielded %d member link(s) [engine=%s]" % (len(listing), fetcher.engine),
              file=sys.stderr)
    records = []
    for i, m in enumerate(listing, 1):
        if verbose:
            print("[%d/%d] fetching %s" % (i, len(listing), m["url"]), file=sys.stderr)
        rec = {
            "slug": m["slug"],
            "name": m["name"],
            "district": m["district"],
            "role": m["role"],
            "source_url": m["url"],
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            detail = parse_member_page(fetcher.fetch(m["url"]))
            # the member page's own District label wins over the listing
            # section when both exist and disagree (it never should; a
            # disagreement will show in review as a district change)
            if detail["district"]:
                rec["district"] = detail["district"]
            rec["email"] = detail["email"]
            rec["phone"] = detail["phone"]
            rec["term_expiration"] = detail["term_expiration"]
            archived = getattr(fetcher, "last_archived_at", None)
            if archived:
                rec["archived_at"] = archived  # provenance: the archive copy used
        except Exception as e:
            rec["error"] = str(e)
        records.append(rec)
        time.sleep(delay)
    return records


def scrape(engine, delay=0.75):
    """auto: walk the engine ladder (requests -> playwright -> wayback),
    probing each on the listing page; the first engine that can fetch it runs
    the whole scrape. The probe result is reused so the winning engine never
    refetches the listing (a Save Page Now capture is not free)."""
    if engine in ("requests", "playwright", "wayback"):
        fetcher = make_fetcher(engine)
        why = require_robots_for(fetcher, 'kendall-county-board-scraper')
        if why:
            print("robots.txt: %s" % why, file=sys.stderr)
        try:
            return scrape_all(fetcher, delay=delay)
        finally:
            fetcher.close()

    last_err = None
    for name in ("requests", "stdlib", "playwright", "wayback"):
        try:
            fetcher = make_fetcher(name)
        except Exception as e:  # e.g. playwright/Chromium not installed
            print("%s engine unavailable (%s); trying next" % (name, e), file=sys.stderr)
            last_err = e
            continue
        why = require_robots_for(fetcher, 'kendall-county-board-scraper')
        if why:
            print("robots.txt (%s rung): %s" % (name, why), file=sys.stderr)
        try:
            listing_html = fetcher.fetch(BASE + LISTING_PATH)
        except Exception as e:
            print("%s engine blocked (%s); trying next" % (name, e), file=sys.stderr)
            last_err = e
            fetcher.close()
            continue
        try:
            return scrape_all(fetcher, delay=delay, listing_html=listing_html)
        finally:
            fetcher.close()
    raise RuntimeError("all fetch engines failed; last error: %s" % last_err)


def main():
    ap = argparse.ArgumentParser(description="Scrape Kendall County Board member pages.")
    ap.add_argument("out", nargs="?", default=None, help="output JSON path (default: stdout)")
    ap.add_argument(
        "--engine",
        choices=["auto", "requests", "stdlib", "playwright", "wayback"],
        default="auto",
        help="Fetch engine: auto (the requests -> playwright -> wayback ladder), "
        "requests (browserless), playwright (real Chromium), or wayback "
        "(Internet Archive Save Page Now + snapshot read).",
    )
    ap.add_argument("--delay", type=float, default=0.75, help="Delay between requests (seconds)")
    args = ap.parse_args()

    records = scrape(args.engine, delay=args.delay)

    payload = json.dumps(records, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w") as f:
            f.write(payload + "\n")
    else:
        print(payload)

    ok = [r for r in records if not r.get("error")]
    fields = ("district", "email", "phone", "term_expiration")
    coverage = "  ".join("%s=%d/%d" % (f, sum(1 for r in ok if r.get(f)), len(ok)) for f in fields)
    print("Scraped %d members (%d without error)" % (len(records), len(ok)), file=sys.stderr)
    print("field coverage: %s" % coverage, file=sys.stderr)
    if not ok:
        # A listing recovered from a Wayback snapshot with every member page
        # errored is not a successful scrape — exiting 0 here sends the
        # workflow past its standing-issue report step and into the builder,
        # which refuses the empty data and turns the job red with no issue
        # update (McHenry hit exactly this on 2026-08-13, the standing block
        # plus an archive.org SPN2 outage). Failing makes the workflow's own
        # taxonomy do the work: the report step fires, the builder is
        # skipped, the job stays green.
        print("FATAL: no member page yielded data — the all-blocked shape",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
