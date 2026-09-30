#!/usr/bin/env python3
"""
Scrape LaSalle County's Municipality Officials directory into the payload
build_municipal_officials_roster.py consumes.

SOURCE. The county clerk publishes one PDF listing every municipality's FULL
governing body — head of government, clerk, treasurer, and every trustee /
alderperson / commissioner, with ward numbers where a city elects by ward, plus
each official's mailing address and phone. That is Cook/Will depth from a single
county document, and it is why LaSalle joined the roster as a full-governing-body
county rather than a mayor-level one.

FETCH POSTURE: open. The document is served by the county's CivicEngage site to
an ordinary browser UA with no challenge; plain `requests` succeeds.

WHY A GEOMETRIC PARSER. This is the repo's first PDF source, and the naive route
does not work: `extract_text()` interleaves the six columns with the left-hand
hall-address block, so lines come out mixing an official's title with a fragment
of the municipality's own address, and some phone numbers arrive with every
character doubled ("8 8 1 1 5 5 - - 2 2 ..."). So the parser works from word
POSITIONS instead of lines:

  1. Column bands, read off the header row's x positions and confirmed against
     an x0 histogram of every word on the page: there are real gutters between
     the six columns, so a word's x0 alone identifies its column.
  2. Records ANCHORED on the title+name columns, with the other columns attached
     by proximity. This is the part that has to be got right, and the obvious
     approaches both fail on measurement: a fixed row grid splits a record from
     its own phone (the phone renders ~2 pt above the name), and single-linkage
     clustering over all words MERGES adjacent records — the y-gap histogram for
     this document runs continuously from 0 to 15 pt with no empty band, because
     the left-hand hall-address block and the phone column each have their own
     line rhythm that interleaves with the officials' ~12.6 pt one, so any
     threshold chains through them. Anchoring on title+name (which sit within
     ~1 pt of each other and keep a clean 12.6 pt rhythm) and then attaching the
     nearest unclaimed address/city/phone within 3.5 pt cannot chain: the
     interleaved columns are never anchors, only attachments.
  3. Municipality attribution by ORDER, not by row. The header ("Village of
     Dana") does not reliably share a row with the official it heads — after a
     page break it can land one row BELOW its own village president. But every
     block starts with a head-of-government row, and the count of headers
     equals the count of head rows exactly, so the two ordered sequences pair
     1:1. The parser asserts that equality and refuses to emit if it breaks,
     rather than silently mis-filing the first official of a block.

TWO SEATS PER WARD. The cities print each ward twice — "Alderperson ward 1" and
"City Alderperson ward 1" are the two aldermen of ward 1, not two different
offices. Both normalise to Alderperson with district = 1.

Usage:
    python3 scripts/lasalle_municipal_officials_scraper.py --out lasalle.json
"""

import argparse
import collections
import datetime
import io
import json
import re
import sys

import pdfplumber
import requests
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

DIRECTORY_URL = ("https://lasallecountyil.gov/DocumentCenter/View/1425/"
                 "Municipality-Officials-PDF")
OFFICIALS_PAGE = "https://lasallecountyil.gov/294/Officials"
BROWSER_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
REQUEST_TIMEOUT = 60

# Column bands: (x0_low, x0_high, name). Derived from the header row and
# verified against the whole-page x0 histogram — every boundary sits inside a
# gutter no word occupies.
COLUMNS = [(0, 130, "MUNI"), (130, 210, "TITLE"), (210, 300, "NAME"),
           (300, 425, "ADDRESS"), (425, 475, "CITY"), (475, 10 ** 6, "PHONE")]
ANCHOR_COLUMNS = ("TITLE", "NAME")   # the two that define a record
ANCHOR_LINKAGE_PT = 3.0              # title and name sit ~1 pt apart
ATTACH_TOLERANCE_PT = 3.5            # how far a phone/address may sit from its record

MUNI_HEADER = re.compile(r"^(Village|City|Town)\s+of\s+[A-Z]", re.I)
# Elected offices this directory prints. An office outside this vocabulary is
# NOT dropped silently — it is reported and skipped, so a new office type gets a
# human's attention (the repo's convention for unknown office names).
HEAD_TITLES = {"mayor", "village president", "president"}
BOARD_TITLES = {"trustee", "alderperson", "alderman", "councilperson",
                "councilman", "councilwoman", "commissioner", "council member"}
OFFICER_TITLES = {"clerk", "village clerk", "city clerk", "treasurer",
                  "city treasurer", "village treasurer", "collector"}
# Appointed staff the directory lists beside the elected officials. Kept, but
# flagged, because the card must not imply these were elected.
APPOINTED_TITLES = {"deputy clerk", "village administrator", "city administrator",
                    "administrator", "village clerk/administrator"}

MIN_MUNICIPALITIES = 22   # 26 live 2026-07
MIN_OFFICIALS = 170       # 209 live
MIN_HEADS = 22            # 26 live — one per municipality
MIN_PHONES = 150          # 191 live


def dedouble(text):
    """Collapse the PDF's doubled-glyph artifact ("TTIITTLLEE" -> "TITLE").

    Some header and phone cells carry two overlapping text layers, which
    extraction interleaves character by character. Only collapse when EVERY
    character pairs up — anything else is left alone, so a legitimately
    repeated letter is never eaten.
    """
    s = text.replace(" ", "")
    if len(s) < 4 or len(s) % 2:
        return text
    if all(s[i] == s[i + 1] for i in range(0, len(s), 2)):
        return s[::2]
    return text


PHONE_RE = re.compile(r"^\(?(\d{3})\)?[\s.-]*(\d{3})[\s.-]*(\d{4})$")


def clean_phone(raw):
    """Accept only a complete, unambiguous 10-digit number.

    The doubled-layer artifact turns some cells into "8 8 1 1 5 5 - - 2 2 4 4
    ..." — digits that could be de-interleaved two different ways. Rather than
    guess which reading is the real number, drop it: a missing phone is a gap,
    a wrong phone sends someone to a stranger.
    """
    if not raw:
        return None
    s = " ".join(str(raw).split())
    fixed = dedouble(s)
    m = PHONE_RE.match(fixed.strip())
    if m:
        return "%s-%s-%s" % m.groups()
    m = PHONE_RE.match(re.sub(r"[^\d]", "", s)) if len(re.sub(r"[^\d]", "", s)) == 10 else None
    return "%s-%s-%s" % m.groups() if m else None


def column_of(x0):
    for lo, hi, name in COLUMNS:
        if lo <= x0 < hi:
            return name
    return None


def ycenter(w):
    return (w["top"] + w["bottom"]) / 2.0


def cluster(words, linkage):
    """Single-linkage grouping on vertical centre. Safe ONLY on the anchor
    columns — see the module docstring for why it cannot be used on all words."""
    ordered = sorted(words, key=ycenter)
    groups, current, last = [], [], None
    for w in ordered:
        y = ycenter(w)
        if last is not None and y - last > linkage:
            groups.append(current)
            current = []
        current.append(w)
        last = y
    if current:
        groups.append(current)
    return groups


def join(words):
    return " ".join(w["text"] for w in sorted(words, key=lambda w: w["x0"])).strip()


def extract_rows(pdf_bytes):
    """One dict per record, plus one per municipality header, in document order.

    A header row is emitted as {"MUNI": ...} with no TITLE/NAME so the caller's
    two sequences (headers, records) stay in document order.
    """
    rows = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            by_col = collections.defaultdict(list)
            for w in words:
                col = column_of(w["x0"])
                if col:
                    by_col[col].append(w)

            # anchors: the title+name pairs that define each record
            anchors = []
            anchor_words = by_col["TITLE"] + by_col["NAME"]
            for group in cluster(anchor_words, ANCHOR_LINKAGE_PT):
                cells = collections.defaultdict(list)
                for w in group:
                    cells[column_of(w["x0"])].append(w)
                anchors.append({
                    "y": sum(ycenter(w) for w in group) / len(group),
                    "TITLE": join(cells.get("TITLE", [])),
                    "NAME": join(cells.get("NAME", [])),
                })

            # attachments: nearest unclaimed line of each satellite column
            for col in ("ADDRESS", "CITY", "PHONE"):
                lines = [{"y": sum(ycenter(w) for w in g) / len(g), "text": join(g),
                          "used": False}
                         for g in cluster(by_col[col], ANCHOR_LINKAGE_PT)]
                for a in anchors:
                    best, best_d = None, None
                    for ln in lines:
                        if ln["used"]:
                            continue
                        d = abs(ln["y"] - a["y"])
                        if d <= ATTACH_TOLERANCE_PT and (best_d is None or d < best_d):
                            best, best_d = ln, d
                    if best:
                        best["used"] = True
                        a[col] = best["text"]

            # municipality headers, clustered on their own column so a wrapped
            # hall address can never be mistaken for one
            headers = []
            for g in cluster(by_col["MUNI"], ANCHOR_LINKAGE_PT):
                text = join(g)
                if MUNI_HEADER.match(text):
                    headers.append({"y": sum(ycenter(w) for w in g) / len(g), "MUNI": text})

            for item in sorted(anchors + headers, key=lambda d: d["y"]):
                rows.append(item)
    return rows


TITLE_NOISE = {"title", "name", "municipality", "address", "city", "phone"}


ALL_OFFICES = set(HEAD_TITLES) | set(BOARD_TITLES) | set(OFFICER_TITLES) | set(APPOINTED_TITLES)


def split_bled_title(title):
    """-> (office_text, name_prefix). Undo a first name that crossed the gutter.

    A few names start left of the name column's left edge, so the title cell
    reads "Commissioner Gregory" with the surname alone in the name cell. Detect
    it by taking the LONGEST leading run of words that is a known office and
    handing the remainder back to the name — so nothing is dropped and no office
    is invented. A title that is not a known office plus extra words is left
    untouched for the caller to report.
    """
    words = title.split()
    for take in range(len(words), 0, -1):
        candidate = " ".join(words[:take])
        probe = re.sub(r"\b(City|Village|Town)\b", "", candidate, flags=re.I)
        probe = re.sub(r"\bwards?\s*[0-9]+\b", "", probe, flags=re.I)
        probe = " ".join(probe.split()).strip(" ,-").lower()
        if probe in ALL_OFFICES:
            return candidate, " ".join(words[take:])
    return title, ""


def parse_title(raw):
    """-> (office, district, appointed) or (None, None, None) to skip.

    Handles the two-seats-per-ward printing ("City Alderperson ward 2") and the
    repeated column header that appears at the top of every page.
    """
    t = " ".join(str(raw or "").split())
    if not t:
        return None, None, None
    if dedouble(t).strip().lower() in TITLE_NOISE:
        return None, None, None       # a page's repeated column header
    district = None
    m = re.search(r"\bwards?\s*([0-9]+)\b", t, re.I)
    if m:
        district = m.group(1)
        t = (t[:m.start()] + t[m.end():]).strip()
    # "City Alderperson" / "Alderperson City" are the SAME office as
    # "Alderperson" — the directory's label for the ward's second seat.
    t = re.sub(r"\b(City|Village|Town)\b", "", t, flags=re.I).strip()
    t = re.sub(r"\s{2,}", " ", t).strip(" ,-")
    key = t.lower()
    if key in HEAD_TITLES:
        return t.title(), None, False
    if key in BOARD_TITLES:
        return t.title(), district, False
    if key in OFFICER_TITLES:
        return t.title(), None, False
    if key in APPOINTED_TITLES:
        return t.title(), None, True
    return None, None, None           # unknown — reported by the caller


def looks_like_person(name):
    n = " ".join(str(name or "").split())
    if len(n) < 4 or not re.search(r"[A-Za-z]{2}", n):
        return False
    # a cell that is only a column header is not a person — including the
    # doubled-glyph form ("NNAAMMEE"), which is how the repeated page header
    # renders when its two text layers interleave
    return n.lower() not in TITLE_NOISE and dedouble(n).strip().lower() not in TITLE_NOISE


def fetch_pdf(url):
    require_robots_once(url, BROWSER_UA, headers={"User-Agent": BROWSER_UA},
                        label="il-lasalle-municipal-officials-scraper")
    resp = requests.get(url, headers={"User-Agent": BROWSER_UA},
                        timeout=REQUEST_TIMEOUT, allow_redirects=True)
    resp.raise_for_status()
    if not resp.content.startswith(b"%PDF"):
        raise RuntimeError("%s did not return a PDF (got %d bytes starting %r)"
                           % (url, len(resp.content), resp.content[:16]))
    return resp.content


def parse(rows, warnings):
    headers = [" ".join(r["MUNI"].split()) for r in rows
               if MUNI_HEADER.match(r.get("MUNI", "") or "")]

    # First pass: the official records, in document order.
    records = []
    for r in rows:
        raw_title = " ".join((r.get("TITLE") or "").split())
        name = " ".join((r.get("NAME") or "").split())
        # a first name that crossed the gutter belongs back on the name
        office_text, bled = split_bled_title(raw_title)
        if bled:
            name = (bled + " " + name).strip()
        office, district, appointed = parse_title(office_text)
        if office is None:
            if raw_title and looks_like_person(name):
                warnings.append("unrecognised office %r (name %r) — skipped"
                                % (raw_title, name))
            continue
        if not looks_like_person(name):
            continue
        records.append({"office": office, "district": district,
                        "appointed": appointed, "name": name,
                        "phone": clean_phone(r.get("PHONE"))})

    heads = [i for i, rec in enumerate(records)
             if rec["office"].lower() in HEAD_TITLES]
    if len(heads) != len(headers):
        raise RuntimeError(
            "municipality attribution is unsafe: %d headers vs %d head-of-government "
            "rows. Each block starts with a head row, so these must pair 1:1; a "
            "mismatch means the layout changed and officials would be filed under "
            "the wrong municipality." % (len(headers), len(heads)))

    # Second pass: attribute by ORDER. Block i runs from head row i to the row
    # before head row i+1, and takes header i.
    officials, municipalities = [], []
    for i, start in enumerate(heads):
        end = heads[i + 1] if i + 1 < len(heads) else len(records)
        jurisdiction = headers[i]
        municipalities.append(jurisdiction)
        for rec in records[start:end]:
            person = {"jurisdiction": jurisdiction, "office": rec["office"],
                      "name": rec["name"]}
            if rec["district"]:
                person["district"] = rec["district"]
            if rec["appointed"]:
                person["appointed"] = True
            if rec["phone"]:
                person["person_phone"] = rec["phone"]
            officials.append(person)
    return municipalities, officials


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--pdf", help="parse a local copy instead of fetching")
    args = ap.parse_args()

    pdf_bytes = open(args.pdf, "rb").read() if args.pdf else fetch_pdf(DIRECTORY_URL)
    warnings = []
    try:
        municipalities, officials = parse(extract_rows(pdf_bytes), warnings)
    except Exception as e:
        print("FATAL: %s" % e, file=sys.stderr)
        sys.exit(1)

    for w in sorted(set(warnings)):
        print("  warning: %s" % w, file=sys.stderr)

    heads = sum(1 for p in officials if p["office"].lower() in HEAD_TITLES)
    seats = sum(1 for p in officials if p.get("district"))
    phones = sum(1 for p in officials if p.get("person_phone"))
    problems = []
    if len(municipalities) < MIN_MUNICIPALITIES:
        problems.append("%d municipalities < floor %d" % (len(municipalities), MIN_MUNICIPALITIES))
    if len(officials) < MIN_OFFICIALS:
        problems.append("%d officials < floor %d" % (len(officials), MIN_OFFICIALS))
    if heads < MIN_HEADS:
        problems.append("%d heads of government < floor %d" % (heads, MIN_HEADS))
    if phones < MIN_PHONES:
        problems.append("%d phones < floor %d" % (phones, MIN_PHONES))
    if problems:
        for p in problems:
            print("  FAIL: %s" % p, file=sys.stderr)
        print("FATAL: refusing to write a payload that lost coverage", file=sys.stderr)
        sys.exit(1)

    scraped_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for p in officials:
        p["source_url"] = DIRECTORY_URL
        p["scraped_at"] = scraped_at
    payload = {
        "county": "LaSalle",
        "directory_url": DIRECTORY_URL,
        "officials_page": OFFICIALS_PAGE,
        "scraped_at": scraped_at,
        "municipalities": [{"name": n, "source_url": DIRECTORY_URL,
                            "scraped_at": scraped_at} for n in municipalities],
        "officials": officials,
    }
    with open(args.out, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print("scraped %d municipalities, %d officials (%d heads, %d ward seats, %d phones) -> %s"
          % (len(municipalities), len(officials), heads, seats, phones, args.out),
          file=sys.stderr)


if __name__ == "__main__":
    main()
