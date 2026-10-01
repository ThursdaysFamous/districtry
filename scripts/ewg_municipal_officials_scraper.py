#!/usr/bin/env python3
"""
Scrape the East-West Gateway Public Officials Directory into TWO payloads —
Madison County and St. Clair County — for build_municipal_officials_roster.py.

SOURCE. EWG (the St. Louis region's COG, of which both counties are members)
publishes an annual Public Officials Directory covering every municipality in
its eight-county bi-state region. For each Illinois municipality it prints
the hall address / phone / website / e-mail, the MAYOR (with e-mail where the
city publishes one), the full BOARD OF TRUSTEES / BOARD OF ALDERMEN / CITY
COUNCIL — ward-keyed where the city elects by ward — and the CLERK and
TREASURER. One COG document is the officials source for two counties at once
(the 2026-07-31 validation-pass finding; the pass-7 discovery note).

FETCH POSTURE: open. The PDF lives under a month-stamped wp-content path;
the link is read off the directory's landing page and the constant below is
only the fallback.

WHY A WORD-POSITION PARSER. The directory is a TWO-COLUMN letter page whose
board lists are themselves multi-column — "Carla Crawford   Katie Scott" is
two trustees, and Granite City's ward rows seat two aldermen side by side —
so a flattened line cannot be split on whitespace alone. Word x-positions
give three clean streams: page columns split at the sheet's midline, and
cells within a line split on gaps wider than a word space. pypdf also breaks
section captions mid-word ("M/AYOR", "BO/ARD OF TRUSTEES:"); captions are
therefore matched on a squashed (letters-only) form across one- and two-line
windows.

WHAT IS DELIBERATELY SKIPPED: everything under PRINCIPAL STAFF (attorneys,
chiefs, engineers — the org chart, not the governing body), and the SCHOOL
DISTRICT / FIRE SERVICES / POPULATION / COUNCIL MEETING reference lines.
Monroe County (also in the directory) is not a served county and is skipped.

Usage:
    python3 ewg_municipal_officials_scraper.py \
        --out-madison madison_municipal_officials.json \
        --out-stclair stclair_municipal_officials.json
"""

import argparse
import datetime
import io
import json
import re
import sys
import urllib.parse

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_ROSTER_BOT,
    require_robots_once,
)

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

LANDING_URL = "https://www.ewgateway.org/research-center/public-officials-directory/"
# Fallback only — the live URL is read off LANDING_URL (see module docstring).
POD_URL = "https://www.ewgateway.org/wp-content/uploads/2026/05/2026-POD.pdf"
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
}
REQUEST_TIMEOUT = 300

POD_LINK_RE = re.compile(r'href=\s*"([^"]*POD[^"]*\.pdf[^"]*)"', re.I)

MID_X = 300          # letter page; municipality blocks flow left column then right
CELL_GAP = 10        # x-gap (pt) separating two names printed on one line
# Belleville's Ward 2 pair abuts with NO gap — the extractor fuses the two
# names into one token ("Carmen DucoGigi Dowling Urban"). An interior
# lowercase-to-uppercase boundary with 2+ lowercase letters before it marks
# the seam; "Mc"/"De"/"La" style name particles (one lowercase letter) never
# match it.
FUSED_RE = re.compile(r"(?<=[a-z]{2})(?=[A-Z][a-z])")

COUNTIES = {"MADISONCOUNTYILLINOIS": "Madison", "STCLAIRCOUNTYILLINOIS": "St. Clair"}

SECTIONS = {
    "MAYOR": ("head", "Mayor"),
    "VILLAGEPRESIDENT": ("head", "President"),
    "PRESIDENT": ("head", "President"),
    # Worden's gavel-holding trustee and Godfrey's dual office, as printed.
    "ACTINGVILLAGEPRESIDENT": ("head", "Acting President"),
    "ACTINGPRESIDENT": ("head", "Acting President"),
    "ACTINGMAYOR": ("head", "Acting President"),
    "VILLAGEPRESIDENTTREASURER": ("head", "President"),
    "MAYORTREASURER": ("head", "Mayor"),
    "BOARDOFTRUSTEES": ("board", "Trustee"),
    "TRUSTEES": ("board", "Trustee"),
    "VILLAGEBOARD": ("board", "Trustee"),
    "BOARDOFALDERMEN": ("board", "Alderman"),
    "ALDERMEN": ("board", "Alderman"),
    "CITYCOUNCIL": ("board", "Council Member"),
    "COUNCILMEMBERS": ("board", "Council Member"),
    "VILLAGECLERK": ("officer", "Clerk"),
    "CITYCLERK": ("officer", "Clerk"),
    "CLERK": ("officer", "Clerk"),
    "VILLAGETREASURER": ("officer", "Treasurer"),
    "CITYTREASURER": ("officer", "Treasurer"),
    "TREASURER": ("officer", "Treasurer"),
}
SKIP_SECTIONS = {"PRINCIPALSTAFF", "SCHOOLDISTRICT", "SCHOOLDISTRICTS",
                 "FIRESERVICES", "POPULATION", "COUNCILMEETING",
                 "BOARDMEETING", "MEETINGS", "VILLAGEMEETING"}

PHONE_RE = re.compile(r"\(?(\d{3})\)?[-.\s]*(\d{3})[-.\s]*(\d{4})")
EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
CITY_ZIP_RE = re.compile(r"^(?:(.*),\s*)?([A-Za-z][A-Za-z .'-]*),\s*IL\s*(\d{5})(?:-\d{4})?\s*$")
WARD_CELL_RE = re.compile(r"^Ward\s+(\d+)\s*:?\s*(.*)$", re.I)
NOISE_RE = re.compile(r"^(EWGCOG|Please notify|LEGEND|County Boundary|"
                      r"Municipal Boundary|Major Road|River|Miles|May 20\d\d|\d{1,3})\s*$", re.I)

NON_PERSON_NAMES = {"vacant", "vacancy", "unassigned", "open", "tbd", "none", "n/a"}
HEAD_TITLES = {"mayor", "president"}

FLOORS = {"Madison": {"munis": 24, "officials": 150, "heads": 22, "seats": 20},
          "St. Clair": {"munis": 22, "officials": 140, "heads": 20, "seats": 12}}


def clean(value):
    value = re.sub(r"\s+", " ", (value or "")).strip().strip(",")
    return value or None


def squash(text):
    return re.sub(r"[^A-Z]", "", (text or "").upper())


def jurisdiction_of(results, county, muni):
    for name, block in results.get(county, {}).items():
        if block is muni:
            return name
    return "?"


# THE DIRECTORY ABBREVIATES ONE PLACE INTO ANOTHER COUNTY'S CITY. EWG prints
# St. Clair's Washington Park as "VILLAGE OF WASHINGTON", and Illinois has
# exactly one place named plainly "Washington" — the CITY of Washington in
# TAZEWELL County, population ~16,000. So the name matched, cleanly and wrongly:
# Washington Park's six trustees shipped on Washington-in-Tazewell's Census
# GEOID (1779033), that city's own government never appeared, and Washington
# Park's own GEOID (1779085) held nothing at all. It went unnoticed because
# nothing else claimed 1779033 until Tazewell County was added and the two
# collided.
#
# Keyed by (county, jurisdiction) rather than by name alone: an alias that fires
# on "Village of Washington" everywhere would be a second version of the same
# bug. It stops matching if EWG prints the full name, which is the point — the
# Minooka posture.
NAME_ALIASES = {
    ("St. Clair", "Village of Washington"): "Village of Washington Park",
}


def looks_like_name(text):
    if not text or "@" in text or re.search(r"\d", text):
        return False
    words = [w for w in re.split(r"\s+", text) if w]
    if len(words) < 2 or len(words) > 5:
        return False
    return all(re.match(r"^[A-Z\"“][A-Za-z.,'’\"“”()-]*$", w) for w in words)


def discover_pdf_url(warnings):
    try:
        require_robots_once(LANDING_URL, HEADERS["User-Agent"], headers=HEADERS,
                            label="il-ewg-municipal-officials-scraper")
        resp = requests.get(LANDING_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        links = POD_LINK_RE.findall(resp.text)
        if links:
            # month-stamped uploads paths sort to the newest edition
            return sorted(urllib.parse.urljoin(resp.url, h) for h in links)[-1]
        warnings.append("no POD pdf link on %s — falling back" % LANDING_URL)
    except Exception as exc:  # noqa: BLE001
        warnings.append("could not read %s (%s) — falling back" % (LANDING_URL, exc))
    return POD_URL


def page_cell_rows(page):
    """-> [(column, [cell, ...])] rows in reading order (left col then right)."""
    columns = ([], [])
    clusters = {}
    for w in page.extract_words():
        clusters.setdefault((0 if w["x0"] < MID_X else 1, round(w["top"] / 3.2)), []).append(w)
    for (col, key) in sorted(clusters, key=lambda t: (t[0], t[1])):
        words = sorted(clusters[(col, key)], key=lambda w: w["x0"])
        cells, cur = [], [words[0]]
        for prev, nxt in zip(words, words[1:]):
            if nxt["x0"] - prev["x1"] > CELL_GAP:
                cells.append(cur)
                cur = [nxt]
            else:
                cur.append(nxt)
        cells.append(cur)
        columns[col].append([
            {"text": clean(" ".join(w["text"] for w in c)),
             "words": [(w["text"], w["x0"], w["x1"]) for w in c]}
            for c in cells])
    return [(0, row) for row in columns[0]] + [(1, row) for row in columns[1]]


# Tokens that mark a single long personal name rather than a fused pair.
SINGLE_NAME_TOKENS_RE = re.compile(r"^([A-Z]\.|Jr\.?,?|Sr\.?,?|II|III|IV|Van|Von|"
                                   r"De|Da|La|Le|Mac|Mc|St\.?|Del)$", re.I)


def split_board_cell(cell):
    """A board cell that fuses two side-by-side names -> [name, name] or None.

    Two signals, both required to be conservative: the cell has four-plus
    words with an interior word gap clearly wider than letter-spacing
    (>= 3.5 pt — measured intra-name gaps run 2-3), and both halves read as
    names. Cells carrying an initial or a suffix token are single long names
    and are never split.
    """
    words = cell["words"]
    if len(words) < 4:
        return None
    if any(SINGLE_NAME_TOKENS_RE.match(t) for t, _x0, _x1 in words):
        return None
    gaps = [(words[i + 1][1] - words[i][2], i + 1) for i in range(len(words) - 1)]
    widest, at = max(gaps)
    if widest < 3.5 or at < 2 or len(words) - at < 2:
        # Glen Carbon's pair prints with uniform 3 pt gaps — geometry is
        # silent there, so a plain FOUR-word cell (no initials, no suffixes,
        # no particles, per the guard above) falls back to the only split a
        # pair of ordinary given-name + surname pairs can have. Verified
        # against the village's own roster before this rule shipped.
        if len(words) == 4:
            at = 2
        else:
            return None
    first = clean(" ".join(t for t, _a, _b in words[:at]))
    second = clean(" ".join(t for t, _a, _b in words[at:]))
    if looks_like_name(first) and looks_like_name(second):
        return [first, second]
    return None


def parse(pdf_bytes, warnings):
    if pdfplumber is None:
        raise RuntimeError("pdfplumber is required (pip install -c scripts/requirements.txt pdfplumber)")
    pdf = pdfplumber.open(io.BytesIO(pdf_bytes))

    results = {"Madison": {}, "St. Clair": {}}   # county -> {muni: block}
    county = None
    muni = None                                  # current block dict
    section = None                               # (kind, office) or "skip" or None
    ward = None
    pending_caption = ""                         # split-caption repair buffer

    def new_muni(county_name, header_text):
        nonlocal muni, section, ward
        name = clean(re.sub(r"^(CITY|VILLAGE|TOWN)\s+OF\s+", "", header_text, flags=re.I))
        m = re.match(r"^(CITY|VILLAGE|TOWN)\s+OF\s+", header_text, re.I)
        jurisdiction = "%s of %s" % (m.group(1).capitalize(), name.title())
        jurisdiction = NAME_ALIASES.get((county_name, jurisdiction), jurisdiction)
        muni = results[county_name].setdefault(jurisdiction, {
            "hall": {}, "people": [], "in_hall": True})
        section = None
        ward = None

    # Any county banner that is NOT one of the two targets unsets the county:
    # the directory continues into Monroe County, St. Louis City and the
    # Missouri counties, and their municipalities must never be attributed to
    # St. Clair (the last Illinois section before them).
    ANY_COUNTY_RE = re.compile(r"([A-Z]{2,20}COUNTY(?:ILLINOIS|MISSOURI)?|STLOUISCITY)")

    for page in pdf.pages:
        page_text_squash = squash(page.extract_text() or "")
        seg = page_text_squash[:400]
        if "MADISONCOUNTYILLINOIS" in seg:
            county = "Madison"
        elif "STCLAIRCOUNTYILLINOIS" in seg:
            county = "St. Clair"
        elif re.search(r"COUNTY(ILLINOIS|MISSOURI)|STLOUISCITY|MISSOURI", seg):
            county = None
        for _col, cells in page_cell_rows(page):
            line = clean(" ".join(c["text"] for c in cells if c["text"])) or ""
            if not line or NOISE_RE.match(line):
                continue
            sq = squash(line)
            cm = ANY_COUNTY_RE.fullmatch(sq)
            if cm:
                county = COUNTIES.get(sq)
                muni = None
                section = None
                continue
            if county not in results:
                continue
            # Split-caption repair: "M" + "AYOR", "BO" + "ARD OF TRUSTEES:".
            candidate = squash(pending_caption + line).rstrip(":")
            matched_caption = None
            for table, outcome in ((SECTIONS, "section"), (None, None)):
                pass
            if candidate in SECTIONS or candidate in SKIP_SECTIONS:
                matched_caption = candidate
            elif len(sq) <= 2 and not pending_caption:
                # a stranded caption head ("M", "BO", "CI") — hold and try
                # joining with the next row
                pending_caption = line
                continue
            if pending_caption and matched_caption is None:
                # the held fragment plus this line is no caption — a muni
                # header can also split ("VILLAGE OF WASHIN"+"GTON PARK")
                joined = pending_caption + line
                if re.match(r"^(CITY|VILLAGE|TOWN)\s*OF\s+", joined, re.I):
                    pending_caption = ""
                    new_muni(county, joined)
                    continue
                pending_caption = ""
            if matched_caption:
                pending_caption = ""
                if matched_caption in SKIP_SECTIONS:
                    section = "skip"
                else:
                    kind_office = SECTIONS[matched_caption]
                    section = {"kind": kind_office[0], "office": kind_office[1],
                               "taken": False}
                    ward = None
                continue
            if re.match(r"^(CITY|VILLAGE|TOWN)\s+OF\s+[A-Z]", line) and len(line) < 46 \
                    and line.upper() == line:
                new_muni(county, line)
                continue
            if muni is None:
                continue

            # Hall block: everything before the first section caption.
            if section is None and muni["in_hall"]:
                hall = muni["hall"]
                cz = CITY_ZIP_RE.match(line)
                if cz:
                    hall.setdefault("city", clean(cz.group(2)))
                    hall.setdefault("zip", cz.group(3))
                    lead = clean(cz.group(1))
                    if lead:
                        hall.setdefault("street", lead)
                    continue
                pm = re.match(r"^Phone:\s*(.+)$", line, re.I)
                if pm:
                    ph = PHONE_RE.search(pm.group(1))
                    if ph:
                        hall.setdefault("phone", "%s-%s-%s" % ph.groups())
                    continue
                wm = re.match(r"^Website:\s*(\S+)", line, re.I)
                if wm:
                    hall.setdefault("website", wm.group(1).rstrip("/"))
                    continue
                em = re.match(r"^Email:\s*(\S+@\S+)", line, re.I)
                if em:
                    hall.setdefault("email", em.group(1).lower())
                    continue
                if re.search(r"^\d|P\.?\s?O\.?\s?Box|Village Hall|City Hall", line, re.I) \
                        and "street" not in hall:
                    if not re.match(r"^(Village|City) Hall$", line, re.I):
                        hall["street"] = clean(re.sub(r",?\s*P\.?\s?O\.?\s?Box\s+\d+.*$",
                                                      "", line, flags=re.I)) or None
                        if hall["street"] is None:
                            del hall["street"]
                continue

            if section == "skip" or section is None:
                continue
            muni["in_hall"] = False
            kind, office = section["kind"], section["office"]

            # Per-person contact attaches to the last person in this section.
            pm = re.match(r"^Phone:\s*(.+)$", line, re.I)
            em = re.match(r"^\s*Email:\s*(\S+@\S+)\s*$", line, re.I)
            if pm or em:
                target = next((p for p in reversed(muni["people"])
                               if p["office"] == office), None)
                if target is not None:
                    if em:
                        target.setdefault("person_email", em.group(1).lower())
                    else:
                        ph = PHONE_RE.search(pm.group(1))
                        if ph:
                            target.setdefault("person_phone", "%s-%s-%s" % ph.groups())
                continue

            for cell_obj in cells:
                cell = cell_obj["text"]
                if not cell:
                    continue
                wm = WARD_CELL_RE.match(cell)
                if wm and kind == "board":
                    ward = "Ward %d" % int(wm.group(1))
                    cell = clean(wm.group(2))
                    if not cell:
                        continue
                    # drop the "Ward N:" tokens from the geometry as well
                    cell_obj = {"text": cell,
                                "words": cell_obj["words"][-len(cell.split(" ")):]}
                if cell.lower() in NON_PERSON_NAMES:
                    warnings.append("dropped a %s seat published as '%s'" % (office, cell))
                    continue
                if kind == "board":
                    # Fused side-by-side pair (Belleville Ward 2 abuts with no
                    # gap): split at an interior case boundary first, then at
                    # the widest interior word gap (see split_board_cell).
                    pair = None
                    fused = [t for t in cell.split(" ") if FUSED_RE.search(t)]
                    if fused and len(cell.split(" ")) >= 4:
                        tok = fused[0]
                        left_part, right_part = FUSED_RE.split(tok, 1)
                        idx = cell.find(tok)
                        first = clean(cell[:idx] + left_part)
                        second = clean(right_part + cell[idx + len(tok):])
                        if looks_like_name(first) and looks_like_name(second):
                            pair = [first, second]
                    if pair is None:
                        pair = split_board_cell(cell_obj)
                    if pair:
                        warnings.append("split a fused board pair: '%s' -> '%s' + '%s'"
                                        % (cell, pair[0], pair[1]))
                        for part in pair:
                            muni["people"].append({"office": office,
                                                   "district": ward, "name": part})
                        continue
                    if len(cell.split(" ")) >= 4 and not looks_like_name(cell):
                        warnings.append("unsplit board cell in %s: '%s'"
                                        % (jurisdiction_of(results, county, muni), cell))
                if looks_like_name(cell):
                    # A head/officer caption names exactly one person; a second
                    # name-like cell under it means an unrecognised caption is
                    # leaking — surface it, never mint an extra mayor.
                    if kind != "board" and section["taken"]:
                        warnings.append("unexpected extra name under the %s caption "
                                        "in %s: '%s' — an unrecognised section?"
                                        % (office, jurisdiction_of(results, county, muni),
                                           cell))
                        continue
                    person = {"office": office,
                              "district": ward if kind == "board" else None,
                              "name": cell}
                    muni["people"].append(person)
                    section["taken"] = True
    # flush: nothing buffered

    payloads = {}
    for county_name, munis in results.items():
        officials, municipalities = [], []
        for jurisdiction, block in munis.items():
            people = block["people"]
            if not people:
                warnings.append("%s (%s): block parsed no officials" % (jurisdiction, county_name))
                continue
            municipalities.append(jurisdiction)
            hall = block["hall"]
            head_names = {p["name"].lower() for p in people
                          if p["office"].lower() in HEAD_TITLES}
            for p in people:
                if p["office"].lower() not in HEAD_TITLES and p["name"].lower() in head_names:
                    warnings.append("dropped the %s row for %s in %s — also published "
                                    "as the head of government" % (p["office"], p["name"],
                                                                   jurisdiction))
                    continue
                rec = {
                    "jurisdiction": jurisdiction,
                    "office": p["office"],
                    "district": p.get("district"),
                    "name": p["name"],
                    "office_address": hall.get("street"),
                    "office_city": hall.get("city"),
                    "office_state": "IL" if hall.get("city") else None,
                    "office_zip": hall.get("zip"),
                    "office_phone": hall.get("phone"),
                    "office_email": hall.get("email"),
                    "website": hall.get("website"),
                }
                if p.get("person_phone") and p["person_phone"] != hall.get("phone"):
                    rec["person_phone"] = p["person_phone"]
                if p.get("person_email") and p["person_email"] != hall.get("email"):
                    rec["person_email"] = p["person_email"]
                officials.append(rec)
        payloads[county_name] = (municipalities, officials)
    return payloads


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-madison", required=True)
    parser.add_argument("--out-stclair", required=True)
    parser.add_argument("--pdf", help="parse a local copy instead of fetching")
    args = parser.parse_args()

    warnings = []
    try:
        if args.pdf:
            source_url, pdf_bytes = POD_URL, open(args.pdf, "rb").read()
        else:
            source_url = discover_pdf_url(warnings)
            require_robots_once(source_url, HEADERS["User-Agent"], headers=HEADERS,
                                label="il-ewg-municipal-officials-scraper")
            resp = requests.get(source_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            pdf_bytes = resp.content
            if not pdf_bytes.startswith(b"%PDF"):
                raise RuntimeError("POD URL did not return a PDF")
        payloads = parse(pdf_bytes, warnings)
    except Exception as exc:  # noqa: BLE001
        print("FATAL: %s" % exc, file=sys.stderr)
        sys.exit(1)

    for warning in sorted(set(warnings)):
        print("  warning: %s" % warning, file=sys.stderr)

    scraped_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    outs = {"Madison": args.out_madison, "St. Clair": args.out_stclair}
    failed = False
    for county, (municipalities, officials) in payloads.items():
        heads = sum(1 for p in officials if p["office"].lower() in HEAD_TITLES)
        seats = sum(1 for p in officials if p.get("district"))
        f = FLOORS[county]
        problems = []
        if len(municipalities) < f["munis"]:
            problems.append("%d municipalities < floor %d" % (len(municipalities), f["munis"]))
        if len(officials) < f["officials"]:
            problems.append("%d officials < floor %d" % (len(officials), f["officials"]))
        if heads < f["heads"]:
            problems.append("%d heads < floor %d" % (heads, f["heads"]))
        if seats < f["seats"]:
            problems.append("%d ward seats < floor %d" % (seats, f["seats"]))
        if problems:
            for problem in problems:
                print("  FAIL (%s): %s" % (county, problem), file=sys.stderr)
            failed = True
            continue
        for record in officials:
            record["source_url"] = source_url
            record["scraped_at"] = scraped_at
        payload = {
            "county": county,
            "directory_url": source_url,
            "officials_page": LANDING_URL,
            "scraped_at": scraped_at,
            "municipalities": [{"name": n, "source_url": source_url,
                                "scraped_at": scraped_at} for n in municipalities],
            "officials": officials,
        }
        with open(outs[county], "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        print("scraped %s: %d municipalities, %d officials (%d heads, %d ward seats) -> %s"
              % (county, len(municipalities), len(officials), heads, seats, outs[county]),
              file=sys.stderr)
    if failed:
        print("FATAL: refusing to write a payload that lost coverage", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
