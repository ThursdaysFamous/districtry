#!/usr/bin/env python3
"""
Scrape Logan County's clerk Reference & Yearbook into the payload
build_municipal_officials_roster.py consumes.

SOURCE. The County Clerk's "Reference and Yearbook 2025-2026" (updated
edition — the 2026-07-31 validation-pass finding that retired the old
"salary publication only" blocker) carries CITY GOVERNMENT and VILLAGE
GOVERNMENT sections listing every one of the county's eleven municipalities
with its FULL governing body — head of government, clerk, treasurer,
administrator, and every trustee / ward alderperson — plus, uniquely among
the county sources in this repo, a PER-PERSON phone and e-mail for most
officials. Lincoln (4 wards), Mt. Pulaski (3) and Atlanta (3) elect
alderpersons by ward, two per ward.

FETCH POSTURE: the HTTP status is open and ROBOTS.TXT IS NOT, and this
paragraph said only the first half until 2026-09-12. Plain `requests` gets
both the clerk's Joomla page and the PDF. But www.logancountyil.gov's
`User-agent: *` group reads, among a dozen Joomla internals,

    Disallow: /images/

and the yearbook this scraper reads lives at
/images/Reference_and_Yearbook_2025-2026_updated.pdf — measured live that
day, both the rule and the link the clerk's page currently offers. The `*`
group is the one that binds this project (CLAUDE.md, settled 2026-09-08);
the file's GPTBot / CCBot / anthropic-ai / Claude-Web groups are another
vendor's crawlers and bind nothing here, and reading them instead would
have shut a host that in fact permits almost all of it. The clerk's page
itself (/index.php?option=com_content...) is permitted, so the county
board roster built from it is unaffected.

SO THE FETCH STOPPED. robots_verdict() below reads the policy before either
request and decline() exits non-zero on the yearbook, which is what routes
`logan` to --preserved in update-municipal-officials.yml: the builder
re-inserts every shipped municipality tagged Logan — 11 of them, 65 officials,
verified against the shipped file — and FATALs if it finds none, so the county
cannot silently drop. This is Ashland's precedent
(wi/scripts/wi_county_board_scraper.py): stop the crawl, keep the reader, carry
the roster as read. robots.txt governs RETRIEVAL, not what already-public
information may be shown.

THE READER BELOW IS KEPT rather than deleted, and the check runs every week, so
the day /images/ stops being disallowed — or the clerk moves the yearbook to a
permitted path — this resumes on its own with no edit. The monthly link check
declines the same path through ROBOTS_DECLINED_PATHS in
scripts/validate_card_links.py, because stopping the weekly fetch and leaving
the monthly one would be half a fix. An earlier version of this paragraph said
the fetch was "still running as this is written" and that stopping it was "its
own change rather than done here"; both were true for about an hour.

URL DISCOVERY, not a hardcoded path. The yearbook lives under
/images/Reference_and_Yearbook_*.pdf and the filename carries the edition;
the link is read off the clerk's page and the constant below is only the
fallback.

WHY A WORD-POSITION PARSER (the LaSalle lesson, different geometry). The
booklet is half-letter (306 pt) and prints officials as PAIRED CARDS — two
per row, left column anchored at x≈21, right at x≈156 — while municipality
headers, hall contact and section captions are CENTERED, straddling both.
A flattened line extraction glues each pair into one unparseable line
("Mayor   City Clerk"). Word x-positions separate the three streams
cleanly: a row whose first word starts at the left anchor is card content
(split at x=150), anything starting mid-page is a centered line.

PER-PERSON CONTACT: the phone and e-mail printed on an official's own card
ship as that person's, EXCEPT when they merely repeat the hall's own
phone/e-mail — a "direct line" that is just the main line is not a direct
line. The home addresses the yearbook prints for officials are never
collected: the app ships municipality-level office addresses only.

WHAT IS DELIBERATELY SKIPPED: appointed department heads (Chief of Police,
Fire Chief, Street Superintendent, Building and Safety Officer, Public
Works Director, Waste Water Plant Manager, City Secretary) — the card is
the governing body, not the org chart. The Administrator DOES ship, with
appointed=True (the office is statutorily appointed), matching the LaSalle
convention of carrying the staff its clerk prints beside the electeds.

Usage:
    python3 logan_municipal_officials_scraper.py --out logan_municipal_officials.json
    python3 logan_municipal_officials_scraper.py --out out.json --pdf local.pdf
"""

import argparse
import datetime
import io
import json
import re
import sys
import urllib.parse

import requests
from scraper_common import UA_ROSTER_BOT  # noqa: E402  (shared machinery — do not fork)
from robots_rules import permitted, star_disallows  # noqa: E402

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

REFERENCE_PAGE = ("https://www.logancountyil.gov/index.php?option=com_content"
                  "&view=article&id=167&Itemid=616&lang=en")
# Fallback only — the live URL is read off REFERENCE_PAGE (see module docstring).
YEARBOOK_URL = ("https://www.logancountyil.gov/images/"
                "Reference_and_Yearbook_2025-2026_updated.pdf")
# THE DISTRICTRY TOKEN, MEASURED RATHER THAN ASSUMED (2026-09-12). This file sent
# a pinned Chrome string with no measurement behind it — one of the 68
# scripts/probe_user_agents.py found in that state. Asked the same clerk page
# both ways on the same day, www.logancountyil.gov answered 108,250 bytes to
# each, discovered the same yearbook link, and served robots.txt to the token as
# well. So the browser string bought nothing here and the scraper now says what
# it is. The witness is this county's own weekly run, which is what
# scripts/scraper_common.py requires; if the host starts refusing the token, that
# run fails visibly and Logan's 11 municipalities carry forward through
# --preserved rather than dropping.
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
REQUEST_TIMEOUT = 120

YEARBOOK_LINK_RE = re.compile(
    r'href=\s*"([^"]*Reference_and_Yearbook[^"]*\.pdf[^"]*)"', re.I)

# Column geometry (points; page is 306 wide). Verified against the
# 2025-2026 edition: left cards anchor at x0 = 21, right cards at 156-182,
# centered lines start between those.
LEFT_ANCHOR_MAX = 45
RIGHT_COL_MIN = 150

SECTION_START_RE = re.compile(r"^CITY GOVERNMENT$", re.I)
SECTION_END_RE = re.compile(r"^UNINCORPORATED VILLAGES", re.I)
VILLAGE_SECTION_RE = re.compile(r"^VILLAGE GOVERNMENT$", re.I)
POPULATION_RE = re.compile(r"^Population:\s", re.I)
MUNI_NAME_RE = re.compile(r"^[A-Z][A-Z .'’-]+$")
WARD_RE = re.compile(r"^(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH)\s+WARD\s+"
                     r"ALDERPERSONS?\s*$", re.I)
# Latham prints the caption in the singular.
TRUSTEES_RE = re.compile(r"^Village Trustees?\s*$", re.I)
WARD_NUMBER = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
               "sixth": 6}

KEEP_TITLES = {
    "mayor": ("Mayor", False),
    "village president": ("President", False),
    "city clerk": ("Clerk", False),
    "village clerk": ("Clerk", False),
    "city treasurer": ("Treasurer", False),
    "village treasurer": ("Treasurer", False),
    "city administrator": ("Administrator", True),
    "village administrator": ("Administrator", True),
}
# Department heads the parser recognises and deliberately does not ship.
SKIP_TITLE_RE = re.compile(
    r"^(City Secretary|Chief of Police|Fire Chief|Police Chief|"
    r"Street Superintendent|Building and Safety|Public Works|"
    r"Waste Water|Water Plant|Zoning|Manager|Officer|Director)\b", re.I)

PHONE_RE = re.compile(r"\(?(\d{3})\)?[-.\s]*(\d{3})[-.\s]*(\d{4})")
EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+)")
CITY_ZIP_RE = re.compile(r",\s*IL\.?\s*\d{5}")
WEBSITE_RE = re.compile(r"^(?:https?://)?(www\.\S+)$", re.I)
VALID_TLD_RE = re.compile(r"\.(com|org|net|gov|edu|us|info)$", re.I)

NON_PERSON_NAMES = {"vacant", "vacancy", "unassigned", "open", "tbd", "none", "n/a"}
HEAD_TITLES = {"mayor", "president"}

MIN_MUNICIPALITIES = 10
MIN_OFFICIALS = 80
MIN_HEADS = 10
MIN_WARD_SEATS = 16


def clean(value):
    value = re.sub(r"\s+", " ", (value or "")).strip().strip(",")
    return value or None


def looks_like_name(text):
    """Two-plus capitalized alpha words, no digits or @ — a person, not contact."""
    if not text or "@" in text or re.search(r"\d", text):
        return False
    words = [w for w in re.split(r"\s+", text) if w]
    if len(words) < 2 or len(words) > 5:
        return False
    return all(re.match(r"^[A-Z(\"“'][A-Za-z().,\"“”'’-]*$", w) for w in words)


ROBOTS_TIMEOUT = 30


def robots_verdict(url):
    """(permitted, note) for one address, from its host's own `*` group.

    Read with THIS scraper's header set, because sending a weaker client than
    the crawl is the one asymmetry a compliance check must not have. An
    unreadable robots.txt is reported unknown and does not block the fetch —
    the fleet's posture, and the same one wi/scripts/validate_robots.py takes.
    """
    split = urllib.parse.urlsplit(url)
    robots = "%s://%s/robots.txt" % (split.scheme or "https", split.netloc)
    try:
        resp = requests.get(robots, headers=HEADERS, timeout=ROBOTS_TIMEOUT)
    except Exception as exc:  # noqa: BLE001
        return True, "robots.txt unreadable (%s) — policy unknown, not assumed" % (
            type(exc).__name__)
    if resp.status_code in (404, 410):
        return True, "no robots.txt (HTTP %d) — nothing disallowed" % resp.status_code
    if resp.status_code != 200 or not resp.content:
        return True, "robots.txt unreadable (HTTP %d) — policy unknown, not assumed" % (
            resp.status_code)
    rules = star_disallows(resp.text)
    if rules is None:
        return True, "robots.txt has no `*` group — nothing disallowed to this client"
    path = (split.path or "/") + (("?" + split.query) if split.query else "")
    if permitted(path, rules):
        return True, "the `*` group permits %s" % path
    return False, "the `*` group disallows %s" % path


def discover_pdf_url(warnings):
    try:
        resp = requests.get(REFERENCE_PAGE, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        warnings.append("could not read the clerk page (%s) — falling back to the "
                        "last known yearbook URL" % exc)
        return YEARBOOK_URL
    links = YEARBOOK_LINK_RE.findall(resp.text)
    if not links:
        warnings.append("no Reference_and_Yearbook link on the clerk page — "
                        "falling back to the last known yearbook URL")
        return YEARBOOK_URL
    # "_updated" editions sort after the plain one for the same year; a newer
    # year sorts after both.
    return sorted(urllib.parse.urljoin(resp.url, href) for href in links)[-1]


def fetch_pdf(url):
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    if not resp.content.startswith(b"%PDF"):
        raise RuntimeError("yearbook URL did not return a PDF (got %d bytes of %s)"
                           % (len(resp.content), resp.headers.get("Content-Type")))
    return resp.content


def page_rows(page):
    """-> [(kind, text)] rows for one page, in reading order.

    kind is 'center' (a full-width centered line) or 'cards' with the row's
    (left, right) column texts. Words cluster into rows on their top edge.
    """
    clusters = {}
    for w in page.extract_words():
        clusters.setdefault(round(w["top"] / 3), []).append(w)
    rows = []
    for key in sorted(clusters):
        words = sorted(clusters[key], key=lambda w: w["x0"])
        first_x = words[0]["x0"]
        if first_x > LEFT_ANCHOR_MAX and first_x < RIGHT_COL_MIN:
            rows.append(("center", " ".join(w["text"] for w in words)))
        else:
            left = " ".join(w["text"] for w in words if w["x0"] < RIGHT_COL_MIN)
            right = " ".join(w["text"] for w in words if w["x0"] >= RIGHT_COL_MIN)
            rows.append(("cards", (left, right)))
    return rows


class Card:
    def __init__(self, office, appointed, district):
        self.office = office
        self.appointed = appointed
        self.district = district
        self.name = None
        self.phone = None
        self.email = None
        self.email_pending = None   # a wrapped e-mail waiting for its tail

    def feed(self, text):
        """Attach one card line: the name if none yet, else contact."""
        if self.email_pending is not None:
            candidate = self.email_pending + text.strip()
            if VALID_TLD_RE.search(candidate):
                self.email = candidate.lower()
                self.email_pending = None
                return
            self.email_pending = None  # tail never arrived; drop the fragment
        m = EMAIL_RE.search(text)
        if m or text.strip().endswith("@"):
            candidate = (m.group(1) if m else text.strip()).rstrip(".")
            if VALID_TLD_RE.search(candidate):
                if not self.email:
                    self.email = candidate.lower()
            else:
                # "randyhagenbuch@" / "ahalley2000@yahoo.co" — the domain
                # finishes on the next line of the same card.
                self.email_pending = candidate
            return
        if CITY_ZIP_RE.search(text) or re.search(r"P\.?\s?O\.?\s?Box", text, re.I):
            return                      # a home address — never collected
        pm = PHONE_RE.search(text)
        if pm:
            if not self.phone:
                self.phone = "%s-%s-%s" % pm.groups()
            return
        if self.name is None and looks_like_name(text):
            self.name = clean(text)


def parse(pdf_bytes, warnings):
    if pdfplumber is None:
        raise RuntimeError("pdfplumber is required (pip install -c scripts/requirements.txt pdfplumber)")
    pdf = pdfplumber.open(io.BytesIO(pdf_bytes))

    in_section = False
    munis = []                 # [{name, hall_lines, cards: [Card]}]
    current = None
    hall_mode = False
    board_context = None       # ("Alderperson", "Ward N") or ("Trustee", None)
    columns = None             # (left_cards, right_cards) streams for pairing
    pending_name = None        # a centered muni-name candidate awaiting Population

    def close_columns():
        nonlocal columns
        if columns and current is not None:
            current["cards"].extend(columns[0] + columns[1])
        columns = None

    for page in pdf.pages:
        for kind, payload in page_rows(page):
            if kind == "center":
                text = clean(payload)
                if not text or re.match(r"^\d{1,3}$", text):
                    continue
                if SECTION_START_RE.match(text):
                    in_section = True
                    continue
                if not in_section:
                    continue
                if SECTION_END_RE.match(text):
                    close_columns()
                    in_section = False
                    break
                if VILLAGE_SECTION_RE.match(text):
                    continue
                if POPULATION_RE.match(text):
                    if pending_name:
                        close_columns()
                        current = {"name": pending_name.title(), "hall_lines": [],
                                   "cards": []}
                        munis.append(current)
                        hall_mode = True
                        board_context = None
                        pending_name = None
                    continue
                ward = WARD_RE.match(text)
                if ward:
                    close_columns()
                    hall_mode = False
                    pending_name = None
                    board_context = ("Alderperson",
                                     "Ward %d" % WARD_NUMBER[ward.group(1).lower()])
                    continue
                if TRUSTEES_RE.match(text):
                    close_columns()
                    hall_mode = False
                    pending_name = None
                    board_context = ("Trustee", None)
                    continue
                if MUNI_NAME_RE.match(text) and len(text) >= 4:
                    pending_name = text
                    continue
                pending_name = None
                if hall_mode and current is not None:
                    current["hall_lines"].append(text)
                continue

            if not in_section or current is None:
                continue
            left, right = payload
            # The end caption is wide-tracked enough to start at the left card
            # anchor, so it lands in this branch rather than the centered one.
            joined = clean("%s %s" % (left, right)) or ""
            if SECTION_END_RE.match(joined) or re.match(r"^TOWNSHIP GOVERNMENT$",
                                                        joined, re.I):
                close_columns()
                in_section = False
                break
            hall_mode = False
            if columns is None:
                columns = ([], [])
            for side, text in ((0, left), (1, right)):
                text = clean(text)
                if not text:
                    continue
                low = text.lower().rstrip(":")
                if low in KEEP_TITLES:
                    office, appointed = KEEP_TITLES[low]
                    board_context_local = None
                    columns[side].append(Card(office, appointed, None))
                    continue
                if SKIP_TITLE_RE.match(text) and not looks_like_name(text):
                    columns[side].append(Card(None, False, None))  # skip card
                    continue
                stream = columns[side]
                if board_context and (not stream or stream[-1].name is not None
                                      or stream[-1].office is None):
                    if looks_like_name(text):
                        card = Card(board_context[0], False, board_context[1])
                        stream.append(card)
                        card.feed(text)
                        continue
                if stream:
                    stream[-1].feed(text)
        # page loop continues; card pairs never span pages in this booklet

    close_columns()
    if not munis:
        raise RuntimeError("no municipality blocks found — the yearbook's layout changed")

    municipalities, officials = [], []
    for muni in munis:
        name = muni["name"]
        municipalities.append(name)
        street = city = zipcode = phone = email = website = None
        for line in muni["hall_lines"]:
            m = re.match(r"^(?:(.*),\s*)?([A-Za-z][A-Za-z .'-]*),\s*IL\.?\s*(\d{5})", line)
            if m:
                city, zipcode = clean(m.group(2)), m.group(3)
                if m.group(1) and not street:
                    street = clean(m.group(1))
                continue
            wm = WEBSITE_RE.match(line)
            if wm:
                website = wm.group(1).lower().rstrip("/")
                continue
            em = EMAIL_RE.search(line)
            if em:
                email = em.group(1).lower()
                continue
            pm = PHONE_RE.search(line)
            if pm:
                if not phone:
                    phone = "%s-%s-%s" % pm.groups()
                continue
            if re.search(r"\d", line) and not street and not re.match(r"^P\.?\s?O\.?", line, re.I):
                street = clean(line)
        shared = {
            "jurisdiction": name,
            "office_address": street,
            "office_city": city,
            "office_state": "IL" if city else None,
            "office_zip": zipcode,
            "office_phone": phone,
            "office_email": email,
            "website": website,
        }

        head_names = set()
        for card in muni["cards"]:
            if card.office and card.name and card.office.lower() in HEAD_TITLES:
                head_names.add(card.name.lower())
        for card in muni["cards"]:
            if card.office is None:
                continue                      # a recognised, skipped staff card
            person = card.name
            if not person:
                warnings.append("%s: a %s card carries no readable name — skipped"
                                % (name, card.office))
                continue
            if person.lower() in NON_PERSON_NAMES:
                warnings.append("dropped a %s seat published as '%s' in %s"
                                % (card.office, person, name))
                continue
            if card.office.lower() not in HEAD_TITLES and person.lower() in head_names:
                warnings.append("dropped the %s row for %s in %s — the same person "
                                "is published as the head of government"
                                % (card.office, person, name))
                continue
            record = dict(shared, office=card.office, district=card.district,
                          name=person)
            if card.appointed:
                record["appointed"] = True
            # A direct line that is just the hall's main line is not a direct
            # line; same for the hall's shared inbox.
            if card.phone and card.phone != phone:
                record["person_phone"] = card.phone
            if card.email and card.email != (email or ""):
                record["person_email"] = card.email
            officials.append(record)
    return municipalities, officials


def decline(url, note):
    """Stop, and say plainly that this is compliance rather than an outage.

    EXIT 1 IS HOW THE DATA SURVIVES. update-municipal-officials.yml routes a
    non-zero Logan scrape to `--preserved logan`, and the builder re-inserts
    every shipped municipality tagged Logan — FATALing if it finds none, so the
    county cannot silently drop. robots.txt governs RETRIEVAL, not what
    already-public information may be shown, which is the Ashland precedent
    (wi/scripts/wi_county_board_scraper.py): stop the crawl, keep the reader,
    carry the roster as read.

    Nothing here renames a client, tries another host, or reaches for a cached
    copy of the same path to get around the rule. The reader below is kept
    rather than deleted because it is what the county's own say-so, or a moved
    file, would re-enable — and the check above runs every week, so the day
    /images/ stops being disallowed this resumes on its own.
    """
    print("ROBOTS-DECLINED: %s — %s. Not fetched." % (url, note), file=sys.stderr)
    print("This is not an outage and not a block: the host serves the file to "
          "this client and asks automated clients not to take it. The shipped "
          "roster carries Logan's 11 municipalities forward (PRESERVABLE "
          "['logan'] in scripts/build_municipal_officials_roster.py).",
          file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--pdf", help="parse a local copy instead of fetching")
    args = parser.parse_args()

    warnings = []
    try:
        if args.pdf:
            source_url, pdf_bytes = YEARBOOK_URL, open(args.pdf, "rb").read()
        else:
            # THE CLERK'S PAGE IS ASKED ABOUT TOO, not only the PDF: robots.txt
            # is read before the FIRST fetch of a host, and this page is that
            # fetch. It is permitted today and the yearbook is not.
            ok, note = robots_verdict(REFERENCE_PAGE)
            print("  robots %s: %s" % (REFERENCE_PAGE, note), file=sys.stderr)
            if not ok:
                decline(REFERENCE_PAGE, note)
            source_url = discover_pdf_url(warnings)
            ok, note = robots_verdict(source_url)
            print("  robots %s: %s" % (source_url, note), file=sys.stderr)
            if not ok:
                decline(source_url, note)
            pdf_bytes = fetch_pdf(source_url)
        municipalities, officials = parse(pdf_bytes, warnings)
    except Exception as exc:  # noqa: BLE001
        print("FATAL: %s" % exc, file=sys.stderr)
        sys.exit(1)

    for warning in sorted(set(warnings)):
        print("  warning: %s" % warning, file=sys.stderr)

    heads = sum(1 for p in officials if (p["office"] or "").lower() in HEAD_TITLES)
    seats = sum(1 for p in officials if p.get("district"))
    problems = []
    if len(municipalities) < MIN_MUNICIPALITIES:
        problems.append("%d municipalities < floor %d" % (len(municipalities), MIN_MUNICIPALITIES))
    if len(officials) < MIN_OFFICIALS:
        problems.append("%d officials < floor %d" % (len(officials), MIN_OFFICIALS))
    if heads < MIN_HEADS:
        problems.append("%d heads of government < floor %d" % (heads, MIN_HEADS))
    # Lincoln's 8 + Mt. Pulaski's 6 + Atlanta's 6 ward-alderperson cards are
    # the part of this payload the municipal-ward layer joins to.
    if seats < MIN_WARD_SEATS:
        problems.append("%d ward seats < floor %d" % (seats, MIN_WARD_SEATS))
    if problems:
        for problem in problems:
            print("  FAIL: %s" % problem, file=sys.stderr)
        print("FATAL: refusing to write a payload that lost coverage", file=sys.stderr)
        sys.exit(1)

    display_url = source_url.split("?")[0]
    scraped_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for record in officials:
        record["source_url"] = display_url
        record["scraped_at"] = scraped_at
    payload = {
        "county": "Logan",
        "directory_url": display_url,
        "officials_page": REFERENCE_PAGE,
        "scraped_at": scraped_at,
        "municipalities": [{"name": n, "source_url": display_url,
                            "scraped_at": scraped_at} for n in municipalities],
        "officials": officials,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("scraped %d municipalities, %d officials (%d heads, %d ward seats) -> %s"
          % (len(municipalities), len(officials), heads, seats, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
