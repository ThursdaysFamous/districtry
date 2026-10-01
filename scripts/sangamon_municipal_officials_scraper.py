#!/usr/bin/env python3
"""
Scrape Sangamon County's clerk per-municipality officials PDFs into the
payload build_municipal_officials_roster.py consumes.

SOURCE. The County Clerk's City / Village Officials page lists all 26 of the
county's published municipalities, each with a hall address / phone / website
/ e-mail block and a link to a PER-MUNICIPALITY OFFICIALS PDF — a uniform
machine-generated table (Office | First | Last | home address | Phone | Email
| Term Begins | Term Ends | Party | Appointed/Vacant Notes) covering the FULL
governing body. Springfield (10 wards) and Auburn (4 wards, two seats each)
elect aldermen by ward. That is full-governing-body depth with term years,
party and per-person contact — the county's clerk maintains the tables
(edition stamps like "Updated 10/15/2025" ride the sheets).

FETCH POSTURE: open, but DISCOVERY IS MANDATORY — the PDFs live on an Azure
blob container behind SAS-signed URLs whose signatures are embedded in the
page, so the links must be read off the page every run; no PDF URL can be
hardcoded.

PER-PERSON CONTACT RULES:
  * The tables print each official's HOME address; those are never collected
    (the app ships municipality-level office addresses only, from the page's
    own hall blocks).
  * A phone shared by three or more officials of one municipality is the
    hall/office line wearing per-person rows (all ten Springfield aldermen
    print the council office's number) — it ships at municipality level
    only, never as a person's direct line. Distinct per-person numbers
    (Auburn's) do ship.
  * E-mails ship per person as printed.

A row whose Notes column says "Appointed" ships with appointed=True — the
clerk says the seat was filled by appointment, and the card must not imply
an election that did not happen. A seat printed "Vacant" is not a person and
is dropped with a log line.

Usage:
    python3 sangamon_municipal_officials_scraper.py --out sangamon_municipal_officials.json
"""

import argparse
import datetime
import html as html_mod
import io
import json
import re
import sys
from collections import Counter

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_ROSTER_BOT,
    require_robots_once,
)

try:
    import pypdf
except ImportError:  # pragma: no cover
    pypdf = None

LISTING_URL = ("https://sangamonil.gov/departments/a-c/county-clerk/"
               "elected-officials/local-officials/city-village-officials")
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
}
REQUEST_TIMEOUT = 120

PDF_LINK_RE = re.compile(r'href=\s*"([^"]+)"[^>]*>\s*([^<]*?)\s+Officials\s*<', re.I)

# "Alderman - Ward 01 Jeff Cox 1530 W. Lake Shore Dr. …" — the office token
# anchors the row; the name is everything before the first house-number/PO
# token; phone/e-mail/terms/party are positional landmarks after it.
OFFICE_ROW_RE = re.compile(
    r"^(Mayor|Acting President|President|Clerk|Treasurer|Trustee|"
    r"Alderman(?:\s*-\s*Ward\s*(\d+))?)\s+(.*)$")
# Jerome's sheet omits the Office column entirely; each official's e-mail
# prefix carries it instead (villagepresidentlopez@, trusteecannella@,
# jeromeclerk@). Used only when a sheet matches no office rows at all.
EMAIL_OFFICE_PREFIXES = (("villagepresident", "President"), ("president", "President"),
                         ("trustee", "Trustee"), ("clerk", "Clerk"),
                         ("treasurer", "Treasurer"), ("mayor", "Mayor"))
PHONE_RE = re.compile(r"\((\d{3})\)\s*(\d{3})[-.\s]*(\d{4})")
EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
TERMS_RE = re.compile(r"(\d{4})\*?\s+(\d{4})\*?")
CITY_ZIP_RE = re.compile(r"^(?:(.*),\s*)?([A-Za-z][A-Za-z .'-]*),\s*IL\.?\s*(\d{5})")

HEAD_TITLES = {"mayor", "president", "acting president"}
NON_PERSON_NAMES = {"vacant", "vacancy", "unassigned", "open", "tbd", "none", "n/a"}

MIN_MUNICIPALITIES = 22
MIN_OFFICIALS = 170
MIN_HEADS = 20
MIN_WARD_SEATS = 15


def clean(value):
    value = re.sub(r"\s+", " ", (value or "")).strip().strip(",")
    return value or None


def fetch(url, binary=False):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-sangamon-municipal-officials-scraper")
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.content if binary else resp.text


def discover(warnings):
    """-> (page_html, {jurisdiction: signed pdf url}) off the clerk's page."""
    raw = fetch(LISTING_URL)
    links = {}
    for m in PDF_LINK_RE.finditer(raw):
        name = clean(html_mod.unescape(m.group(2)))
        href = html_mod.unescape(m.group(1))
        if name and ".pdf" in href.lower():
            links[name] = href
    if not links:
        raise RuntimeError("no '<municipality> Officials' PDF links on the clerk "
                           "page — its layout changed")
    return raw, links


def parse_halls(raw):
    """The page's own per-municipality hall blocks -> {jurisdiction: contact}."""
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S | re.I)
    # Websites/e-mails are links whose text is the municipality name; mark the
    # hrefs inline before flattening so the flat text keeps them.
    text = re.sub(r'<a[^>]+href=\s*"mailto:([^"]+)"[^>]*>', r"\nMAILTO:\1\n", text)
    text = re.sub(r'<a[^>]+href=\s*"(https?://[^"]+)"[^>]*>', r"\nLINK:\1\n", text)
    text = html_mod.unescape(re.sub(r"<[^>]+>", "\n", text))
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    halls = {}
    current = None
    seen_header = set()
    for line in lines:
        m = re.match(r"^(City|Village) of ([A-Z][A-Za-z .'-]+)$", line)
        if m:
            name = clean(line)
            # The index list at the top repeats every name once; the hall
            # block is the SECOND occurrence.
            if name in seen_header:
                current = halls.setdefault(name, {})
            else:
                seen_header.add(name)
                current = None
            continue
        if current is None:
            continue
        cz = CITY_ZIP_RE.match(line)
        if cz:
            current.setdefault("city", clean(cz.group(2)))
            current.setdefault("zip", cz.group(3))
            lead = clean(cz.group(1))
            if lead:
                current.setdefault("street", lead)
            continue
        pm = re.match(r"^Phone:\s*(.+)$", line, re.I)
        if pm:
            ph = PHONE_RE.search(pm.group(1))
            if ph:
                current.setdefault("phone", "%s-%s-%s" % ph.groups())
            continue
        if line.startswith("LINK:"):
            url = line[5:]
            if "sangamon" not in url.lower() and "blob.core" not in url.lower():
                current.setdefault("website", url.rstrip("/"))
            continue
        if line.startswith("MAILTO:"):
            current.setdefault("email", line[7:].lower())
            continue
        if re.search(r"^\d|^P\.?\s?O\.?\s?Box", line, re.I) and "street" not in current \
                and not re.match(r"^Mailing", line, re.I):
            current["street"] = clean(line)
    return halls


def parse_pdf(name, pdf_bytes, warnings):
    """One municipality's officials table -> raw rows."""
    if pypdf is None:
        raise RuntimeError("pypdf is required (pip install -c scripts/requirements.txt pypdf)")
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    rows = []
    for page in reader.pages:
        for raw_line in (page.extract_text() or "").split("\n"):
            line = clean(raw_line)
            if not line:
                continue
            m = OFFICE_ROW_RE.match(line)
            if not m:
                continue
            office_token, ward, rest = m.group(1), m.group(2), m.group(3)
            office = "Alderman" if office_token.startswith("Alderman") else office_token
            district = ("Ward %d" % int(ward)) if ward else None
            # Name = tokens before the first house-number / PO-box token.
            tokens = rest.split(" ")
            name_tokens = []
            for tok in tokens:
                if re.match(r"^\d", tok) or re.match(r"^P\.?O\.?$", tok, re.I):
                    break
                name_tokens.append(tok)
            person = clean(" ".join(name_tokens))
            if not person:
                continue
            phone = PHONE_RE.search(rest)
            email = EMAIL_RE.search(rest)
            terms = TERMS_RE.search(rest.split(email.group(1))[-1] if email else rest)
            appointed = bool(re.search(r"\bAppointed\b", rest))
            rows.append({
                "office": office, "district": district, "name": person,
                "phone": ("%s-%s-%s" % phone.groups()) if phone else None,
                "email": email.group(1).lower() if email else None,
                "term_expires": terms.group(2) if terms else None,
                "appointed": appointed,
            })
    if not rows:
        # The Jerome shape: no Office column; classify by e-mail prefix.
        for page in reader.pages:
            for raw_line in (page.extract_text() or "").split("\n"):
                line = clean(raw_line)
                if not line:
                    continue
                email = EMAIL_RE.search(line)
                if not email:
                    continue
                local = email.group(1).lower().split("@")[0]
                office = next((o for p, o in EMAIL_OFFICE_PREFIXES
                               if local.startswith(p)), None)
                if office is None:
                    # "jeromeclerk@…" — the office rides the END of the local
                    # part when the village prefixes its own name.
                    office = next((o for p, o in EMAIL_OFFICE_PREFIXES
                                   if local.endswith(p)), None)
                if office is None:
                    continue
                tokens = line.split(" ")
                name_tokens = []
                for tok in tokens:
                    if re.match(r"^\d", tok) or re.match(r"^P\.?O\.?$", tok, re.I):
                        break
                    name_tokens.append(tok)
                person = clean(" ".join(name_tokens))
                if not person:
                    continue
                phone = PHONE_RE.search(line)
                not_elected = bool(re.search(r"\bNot Elected\b", line))
                terms = None if not_elected else TERMS_RE.search(line.split(email.group(1))[-1])
                rows.append({
                    "office": office, "district": None, "name": person,
                    "phone": ("%s-%s-%s" % phone.groups()) if phone else None,
                    "email": email.group(1).lower(),
                    "term_expires": terms.group(2) if terms else None,
                    "appointed": not_elected or bool(re.search(r"\bAppointed|\bAppt\.", line)),
                })
        if rows:
            warnings.append("%s: sheet has no Office column — offices read from "
                            "the officials' own e-mail prefixes" % name)
    if not rows:
        warnings.append("%s: no officer rows parsed from its PDF" % name)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    warnings = []
    try:
        raw, links = discover(warnings)
        halls = parse_halls(raw)
        scraped_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        municipalities, officials = [], []
        for jurisdiction in sorted(links):
            pdf_bytes = fetch(links[jurisdiction], binary=True)
            if not pdf_bytes.startswith(b"%PDF"):
                warnings.append("%s: link did not return a PDF — skipped" % jurisdiction)
                continue
            rows = parse_pdf(jurisdiction, pdf_bytes, warnings)
            if not rows:
                continue
            hall = halls.get(jurisdiction, {})
            municipalities.append(jurisdiction)
            # A "per-person" phone repeated across three or more officials is
            # the office line wearing individual rows.
            phone_counts = Counter(r["phone"] for r in rows if r["phone"])
            shared_phones = {p for p, n in phone_counts.items() if n >= 3}
            # An ACTING president is a sitting trustee wearing the gavel — the
            # sheet legitimately prints both rows, so the head-duplicate rule
            # applies only to full heads (the DeKalb rationale: an ELECTED
            # president cannot simultaneously hold a trustee seat).
            head_names = {r["name"].lower() for r in rows
                          if r["office"].lower() in ("mayor", "president")}
            for row in rows:
                if row["name"].lower() in NON_PERSON_NAMES:
                    warnings.append("dropped a %s seat published as '%s' in %s"
                                    % (row["office"], row["name"], jurisdiction))
                    continue
                if row["office"].lower() not in HEAD_TITLES and \
                        row["name"].lower() in head_names:
                    warnings.append("dropped the %s row for %s in %s — the same "
                                    "person is published as the head of government"
                                    % (row["office"], row["name"], jurisdiction))
                    continue
                rec = {
                    "jurisdiction": jurisdiction,
                    "office": row["office"],
                    "district": row["district"],
                    "name": row["name"],
                    "office_address": hall.get("street"),
                    "office_city": hall.get("city"),
                    "office_state": "IL" if hall.get("city") else None,
                    "office_zip": hall.get("zip"),
                    "office_phone": hall.get("phone"),
                    "office_email": hall.get("email"),
                    "website": hall.get("website"),
                    "source_url": LISTING_URL,
                    "scraped_at": scraped_at,
                }
                if row["phone"] and row["phone"] not in shared_phones and \
                        row["phone"] != hall.get("phone"):
                    rec["person_phone"] = row["phone"]
                if row["email"] and row["email"] != hall.get("email"):
                    rec["person_email"] = row["email"]
                if row["term_expires"]:
                    rec["term_expires"] = row["term_expires"]
                if row["appointed"]:
                    rec["appointed"] = True
                officials.append(rec)
    except Exception as exc:  # noqa: BLE001
        print("FATAL: %s" % exc, file=sys.stderr)
        sys.exit(1)

    for warning in sorted(set(warnings)):
        print("  warning: %s" % warning, file=sys.stderr)

    heads = sum(1 for p in officials if p["office"].lower() in HEAD_TITLES)
    seats = sum(1 for p in officials if p.get("district"))
    problems = []
    if len(municipalities) < MIN_MUNICIPALITIES:
        problems.append("%d municipalities < floor %d" % (len(municipalities), MIN_MUNICIPALITIES))
    if len(officials) < MIN_OFFICIALS:
        problems.append("%d officials < floor %d" % (len(officials), MIN_OFFICIALS))
    if heads < MIN_HEADS:
        problems.append("%d heads of government < floor %d" % (heads, MIN_HEADS))
    # Springfield's 10 + Auburn's 8 ward-alderman rows are the part of this
    # payload the municipal-ward layer joins to.
    if seats < MIN_WARD_SEATS:
        problems.append("%d ward seats < floor %d" % (seats, MIN_WARD_SEATS))
    if problems:
        for problem in problems:
            print("  FAIL: %s" % problem, file=sys.stderr)
        print("FATAL: refusing to write a payload that lost coverage", file=sys.stderr)
        sys.exit(1)

    payload = {
        "county": "Sangamon",
        "directory_url": LISTING_URL,
        "scraped_at": scraped_at,
        "municipalities": [{"name": n, "source_url": LISTING_URL,
                            "scraped_at": scraped_at} for n in municipalities],
        "officials": officials,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("scraped %d municipalities, %d officials (%d heads, %d ward seats) -> %s"
          % (len(municipalities), len(officials), heads, seats, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
