#!/usr/bin/env python3
"""
Scrape Carroll County's clerk yearbook into the payload
build_municipal_officials_roster.py consumes.

SOURCE. The clerk's annual yearbook carries a "Cities and Village Officers"
section listing all seven of the county's municipalities with the hall address,
phone, head of government and clerk. That is mayor-level depth — the county
publishes no trustees anywhere — so Carroll joins on the same footing as
DuPage, Kane, McHenry and Kendall rather than as a full-governing-body county.

THE URL IS DISCOVERED, NOT HARDCODED. The yearbook filename carries its edition
("2025-2026 YEARBOOK.pdf") and is renamed every year, so a fixed URL is a
scraper that works until the county does its job. The clerk page's "County
Yearbook" link is read for the current filename instead. That link is RELATIVE
and resolving it against the page gives a 404: the site redirects PDFs to its
Revize CDN, which serves them from the site root rather than from the page's
directory. Both forms are therefore tried, CDN first, and the first one that
returns actual PDF bytes wins.

THE CDN'S POLICY ALLOWS THIS DOCUMENT AND REFUSES GENERAL CRAWLING (measured
2026-09-30, five reads). `cms9files.revize.com` serves a 312-byte robots.txt
whose `*` group is a list of document extensions followed by a blanket refusal:

    User-agent: *
    Allow: /*.pdf$         (plus .DOC$ .DOCX$ .PPT$ .PPTX$)
    Disallow: /

The yearbook path ends `.pdf`, so `Allow: /*.pdf$` is the longest matching rule
and RFC 9309 §2.2.2 gives it the decision. A FIRST READING OF THIS SAID THE
OPPOSITE, because it was taken at `/carrollil/` -- the DIRECTORY, which this
scraper never fetches, and where `Disallow: /` is the only match. Measure the
path the scraper fetches, never a directory above it; a CMS host that serves
documents and refuses crawling cannot be judged from one path. The same wrong
reading was made the same day about Knox County's sibling host
`cms2.revize.com`, whose `*` group has the identical shape.

EVERY HOP IS ASKED, BECAUSE THE ROUTE CROSSES TWO HOSTS. The county's own host
answers 302 to that CDN on both spellings -- `/2025-2026%20YEARBOOK.pdf` and the
page-relative form -- so a redirect target's policy is what decides whether the
document may be read (the Rochester Hills reading already in CLAUDE.md: read the
stub's target, not the stub). `fetch_gated` asks each hop in turn rather than
following the chain blind, which is what makes the permission a measurement of
the host actually serving the bytes rather than of the host that pointed at it.

READ IT WITH A PAUSE. Five rapid reads of these two hosts inside one process
answered 403, 404, a 312-byte policy and a 685 KB body; five reads sixteen
seconds apart answered the identical 312 bytes every time. The variation is
rate limiting under rapid-fire requests and not the host deciding differently,
so a verdict taken from a tight loop over many hosts is not a measurement.

WHY A LINE PARSER. The section is single-column, one officer per line in
"<office> ....dot leaders.... <name>" form, which pypdf's line extraction
preserves exactly. LaSalle's geometric word-position parser exists because its
directory is a six-column table whose columns interleave; nothing here needs it.

TWO THINGS THE EXTRACTED TEXT DOES THAT THE PAGE DOES NOT. The post-office
listings sit in a facing column and pypdf interleaves them into the middle of
the municipal section, so ~40 lines of window hours land between Mt. Carroll
and Savanna. They are skipped structurally rather than by a blocklist: a
municipality begins only at a "City/Village of X" line, its address is the line
directly beneath that header rather than the first address-looking line in the
block, and an officer is only a line with dot leaders. And the yearbook writes
the county seat "Mt. Carroll" where the Census writes "Mount Carroll"; the
builder's norm_place expands the abbreviation, so no alias is needed here.

A SEAT WITH NO HOLDER IS NOT AN OFFICEHOLDER. Thomson's president reads
"Vacant". It is dropped and reported, never shipped as a person's name.

Usage:
    python3 carroll_municipal_officials_scraper.py --out carroll_municipal_officials.json
    python3 carroll_municipal_officials_scraper.py --out out.json --pdf local.pdf
"""

import argparse
import datetime
import io
import json
import re
import sys
import urllib.parse

import requests
from scraper_common import (  # noqa: E402  (shared machinery — do not fork)
    UA_CHROME_WIN_126,
    fetch as fetch_with_retry,
    require_robots_once,
)

try:
    import pypdf
except ImportError:  # pragma: no cover
    pypdf = None

CLERK_PAGE = ("https://www.carrollcountyil.gov/county_departments/"
              "clerk___recorder/index.php")
# Where the site's own redirect lands PDFs. Kept as a constant because the
# discovered link is relative and this is the only form that actually serves.
CDN_ROOT = "https://cms9files.revize.com/carrollil/"
HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
}
REQUEST_TIMEOUT = 120

YEARBOOK_LINK_RE = re.compile(r'href="([^"]*[Yy][Ee][Aa][Rr][Bb][Oo][Oo][Kk][^"]*\.pdf)"')
START_RE = re.compile(r"Cities and Village Officers", re.I)
END_RE = re.compile(r"Carroll County Township Officials", re.I)

MUNI_RE = re.compile(r"^(City|Village|Town) of ([A-Z][A-Za-z .'/-]+?)\s*$")
# "302 N. Main, Mt. Carroll IL 61053 |  (815) 244-4424" — the comma before the
# state is optional because the Mt. Carroll line omits it.
CONTACT_RE = re.compile(r"^(?P<street>.+?),\s*(?P<city>[A-Za-z .'-]+?),?\s+"
                        r"(?P<state>IL)\s+(?P<zip>\d{5})\s*(?:\|\s*(?P<phone>.+?))?\s*$")
# "President .............................................. Matthew Balsiger".
# Three or more leaders, so an ordinary sentence with an ellipsis cannot match.
OFFICER_RE = re.compile(r"^([A-Za-z][A-Za-z .'-]*?)\s*\.{3,}\s*(.+?)\s*$")
PHONE_RE = re.compile(r"(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})")

HEAD_TITLES = {"mayor", "president", "village president"}
NON_PERSON_NAMES = {"vacant", "vacancy", "unassigned", "open", "tbd", "none"}

# 2026-07 live: 7 municipalities / 13 officials / 6 heads (Thomson's president
# is vacant). Deliberate under-tolerances: ordinary turnover and one more
# vacancy pass, a section that stopped parsing does not.
MIN_MUNICIPALITIES = 6
MIN_OFFICIALS = 11
MIN_HEADS = 5


def clean(value):
    value = re.sub(r"\s+", " ", (value or "")).strip(" .")
    return value or None


def fetch(url):
    # scraper_common.fetch retries 429/5xx (numeric Retry-After honoured,
    # capped) and refuses to retry 401/403/404 — the Henry rule. Parsing and
    # every page check stay in this file.
    return fetch_with_retry(url, HEADERS, timeout=REQUEST_TIMEOUT)


def fetch_gated(url, max_hops=5):
    """Fetch `url`, asking EVERY host in the redirect chain for its robots.txt.

    The clerk's own host permits us and 302s the yearbook to its CMS vendor's
    CDN, which does not. Following that chain with `allow_redirects=True` would
    crawl the refusing host while every request this scraper makes by hand read
    as permitted -- so each hop is asked in turn, and the seam raises on the one
    that refuses.
    """
    for _ in range(max_hops):
        require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                            label="il-carroll-municipal-officials")
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT,
                            allow_redirects=False)
        if resp.status_code in (301, 302, 303, 307, 308):
            target = resp.headers.get("Location")
            if not target:
                return resp
            url = urllib.parse.urljoin(url, target)
            continue
        return resp
    raise RuntimeError("more than %d redirects from the clerk page's yearbook "
                       "link -- the site's PDF routing changed" % max_hops)


def discover_yearbook():
    """-> (pdf_bytes, url) for the edition the clerk page currently links."""
    require_robots_once(CLERK_PAGE, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-carroll-municipal-officials")
    page = fetch(CLERK_PAGE).text
    link = YEARBOOK_LINK_RE.search(page)
    if not link:
        raise RuntimeError("no yearbook PDF link on %s — the clerk page changed"
                           % CLERK_PAGE)
    href = html_unescape(link.group(1))
    filename = urllib.parse.quote(href.rsplit("/", 1)[-1])
    candidates = [CDN_ROOT + filename, urllib.parse.urljoin(CLERK_PAGE,
                                                            urllib.parse.quote(href))]
    problems = []
    for url in candidates:
        try:
            resp = fetch_gated(url)
        except Exception as exc:  # noqa: BLE001
            problems.append("%s: %s" % (url, exc))
            continue
        if resp.content.startswith(b"%PDF"):
            return resp.content, url
        problems.append("%s: %d bytes of %s, not a PDF"
                        % (url, len(resp.content), resp.headers.get("Content-Type")))
    raise RuntimeError("could not fetch the linked yearbook (%s) — %s"
                       % (href, "; ".join(problems)))


def html_unescape(value):
    import html as _html
    return _html.unescape(value)


def section_lines(pdf_bytes):
    if pypdf is None:
        raise RuntimeError("pypdf is required (pip install -c scripts/requirements.txt pypdf)")
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    start = START_RE.search(text)
    if not start:
        raise RuntimeError("could not find the 'Cities and Village Officers' "
                           "heading — the yearbook's layout changed")
    # Searched FROM the heading: the table of contents names the township
    # section far earlier in the document.
    end = END_RE.search(text, start.end())
    body = text[start.end(): end.start() if end else len(text)]
    return [line.rstrip() for line in body.split("\n")]


def parse(lines, warnings, dropped):
    municipalities, officials = [], []
    index = 0
    while index < len(lines):
        header = MUNI_RE.match(lines[index].strip())
        if not header:
            index += 1
            continue
        kind, name = header.group(1), clean(header.group(2))
        index += 1

        # The contact line is the first non-blank line UNDER the header, not the
        # first address-shaped line in the block — the post-office column that
        # pypdf interleaves is full of address-shaped lines.
        while index < len(lines) and not lines[index].strip():
            index += 1
        street = city = state = zipcode = phone = None
        if index < len(lines):
            contact = CONTACT_RE.match(lines[index].strip())
            if contact:
                street = clean(contact.group("street"))
                city = clean(contact.group("city"))
                state, zipcode = contact.group("state"), contact.group("zip")
                found = PHONE_RE.search(contact.group("phone") or "")
                phone = found.group(1) if found else None
                index += 1
            else:
                warnings.append("%s: no address line under the header — office "
                                "location omitted" % name)

        shared = {
            "jurisdiction": "%s of %s" % (kind, name),
            "office_address": street,
            "office_city": city,
            "office_state": state,
            "office_zip": zipcode,
            "office_phone": phone,
            "office_email": None,
            "website": None,
        }

        found_any = 0
        while index < len(lines):
            line = lines[index].strip()
            if MUNI_RE.match(line):
                break
            officer = OFFICER_RE.match(line)
            index += 1
            if not officer:
                continue
            office, person = clean(officer.group(1)), clean(officer.group(2))
            if not office or not person:
                continue
            if person.lower() in NON_PERSON_NAMES:
                dropped.append("%s: %s seat listed as '%s' — no officeholder"
                               % (name, office, person))
                continue
            officials.append(dict(shared, office=office, name=person, district=None))
            found_any += 1
        if not found_any:
            warnings.append("no officers parsed for %s — check the yearbook layout"
                            % name)
        municipalities.append(name)
    if not municipalities:
        raise RuntimeError("no 'City/Village of X' headers in the section")
    return municipalities, officials


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--pdf", help="parse a local copy instead of fetching")
    args = parser.parse_args()

    warnings, dropped = [], []
    try:
        if args.pdf:
            pdf_bytes, source_url = open(args.pdf, "rb").read(), CLERK_PAGE
        else:
            pdf_bytes, source_url = discover_yearbook()
        municipalities, officials = parse(section_lines(pdf_bytes), warnings, dropped)
    except Exception as exc:  # noqa: BLE001
        print("FATAL: %s" % exc, file=sys.stderr)
        sys.exit(1)

    for warning in sorted(set(warnings)):
        print("  warning: %s" % warning, file=sys.stderr)
    for drop in sorted(set(dropped)):
        print("  dropped: %s" % drop, file=sys.stderr)

    heads = sum(1 for p in officials if (p["office"] or "").lower() in HEAD_TITLES)
    problems = []
    if len(municipalities) < MIN_MUNICIPALITIES:
        problems.append("%d municipalities < floor %d"
                        % (len(municipalities), MIN_MUNICIPALITIES))
    if len(officials) < MIN_OFFICIALS:
        problems.append("%d officials < floor %d" % (len(officials), MIN_OFFICIALS))
    if heads < MIN_HEADS:
        problems.append("%d heads of government < floor %d" % (heads, MIN_HEADS))
    if problems:
        for problem in problems:
            print("  FAIL: %s" % problem, file=sys.stderr)
        print("FATAL: refusing to write a payload that lost coverage", file=sys.stderr)
        sys.exit(1)

    scraped_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    for person in officials:
        person["source_url"] = source_url
        person["scraped_at"] = scraped_at
    payload = {
        "county": "Carroll",
        "directory_url": source_url,
        "officials_page": CLERK_PAGE,
        "scraped_at": scraped_at,
        "municipalities": [{"name": n, "source_url": source_url,
                            "scraped_at": scraped_at} for n in municipalities],
        "officials": officials,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("scraped %d municipalities, %d officials (%d heads) from %s -> %s"
          % (len(municipalities), len(officials), heads, source_url, args.out),
          file=sys.stderr)


if __name__ == "__main__":
    main()
