#!/usr/bin/env python3
"""
Tompkins County Legislature roster scraper
==========================================
Reads the sixteen legislators from the county's OWN two surfaces and writes an
intermediate JSON file for build_tompkins_legislature_roster.py.

WHY THE PEOPLE DO NOT COME FROM THE MAP. The county's district layer carries a
`Member` column, and reading it would be one fetch instead of three. Coles
County's board layer carried exactly such a column and named six of twelve
people who had left the board, so this project's rule is geometry from
whatever proves the lines and people from whatever the county maintains as
people. The column is still read here — as a DRIFT WITNESS. It agrees 16 of 16
today; a disagreement is printed and never shipped, and that check costs one
request a week.

THE TWO SURFACES, and what each is the authority for.

  1. www.tompkinscountyny.gov/.../Tompkins-County-Legislators — the Legislature's
     own roster page. THE NAME OF RECORD, plus each member's committees and, for
     13 of 16, a link to their own page. It publishes no telephone and no e-mail.
  2. .../2026-tompkins-county-legislators.pdf — the county's own one-page contact
     sheet, linked from that page. Party, an e-mail for all sixteen, a telephone,
     the Legislature's CHAIR and VICE CHAIR (named on no other surface read
     here), and the body's own office and switchboard.

THE JOIN IS BY DISTRICT NUMBER, NEVER BY NAME, because the three surfaces write
the same people three ways: the page says "Travis L. Brooks", "Deborah Dawson",
"Randy B. Brown" where the map column says "Travis Brooks", "Deb Dawson",
"Randy Brown", and the PDF says "Veronica D. Pillar" and "Michael J. Sigler"
where the page says "Veronica Pillar" and "Mike Sigler". The page's form ships.
The scraper FAILS if any district's SURNAME stops agreeing across the surfaces —
that is the check a name-keyed join could not make.

FOUR PARSE TRAPS ON THE ROSTER PAGE, every one of them live today, and each of
them silently costs districts rather than failing:

  1. DISTRICT 10'S HEADING IS NOT A HEADING. Fifteen districts are
     `<h2>District No. N</h2>`; District 10 is a `<p>` holding a `<span>` with
     `font-size: 2em; font-weight: bold` inline. Splitting on `<h2>` returns
     FIFTEEN of sixteen and every floor set at fifteen passes. So the split is
     on the TEXT "District No. N", never on an element.
  2. THE LABEL'S COLON MOVES: `<strong>Legislator:</strong>` for District 1 and
     `<strong>Legislator</strong>:` for the rest. Either pattern alone finds one
     district or fifteen.
  3. DISTRICT 11 NESTS THE TAG: `<strong><strong>Legislator</strong>:&nbsp;</strong>`.
  4. DISTRICTS 10, 12 AND 13 ARE NOT LINKED — the name is plain text after the
     label. A parser requiring an `<a>` drops three.

TWO THINGS THE CONTACT SHEET PUBLISHES THAT NEVER SHIP.

  * A HOME ADDRESS for every one of the sixteen. Home addresses never ship
    anywhere in this project. They are dropped by construction here, and the
    scraper FAILS if it stops seeing them — a parser that silently stops
    recognising the address is a parser that may start shipping it.
  * SEVEN OF THE SIXTEEN PRINTED TELEPHONES ARE (607) 274-5434, which is the
    Legislature's own switchboard printed at the top of the same sheet. That is
    Cook County's second-address lesson: a value repeated across members is the
    BODY's, not the member's. The switchboard ships once, at board level; a
    member whose printed number is the switchboard gets no personal line, and
    the nine with a distinct number get theirs.

Usage:
    python3 ny/scripts/tompkins_legislature_scraper.py --out <path>
"""
import argparse
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from scraper_common import require_robots_allowed  # noqa: E402

UA = "districtry-newyork/1.0 (+https://districtry.com/ny/)"

ROSTER_URL = ("https://www.tompkinscountyny.gov/Government-Resources/County-Legislature/"
              "Tompkins-County-Legislators")
CONTACT_PDF = ("https://www.tompkinscountyny.gov/files/assets/county/v/1/legislature/documents/"
               "2026-tompkins-county-legislators.pdf")
# The drift witness. The same service build_tompkins_legislature.py draws from;
# only the Member column is read, and only to be compared.
WITNESS_URL = ("https://services.arcgis.com/oJbAAWNInLrxvF0A/arcgis/rest/services/"
               "LegislativeDistrictBoundaries/FeatureServer/0/query")

DISTRICTS = 16
PARTY_NAMES = {"D": "Democratic", "R": "Republican", "I": "Independent",
               "C": "Conservative", "WF": "Working Families"}


def fetch(url, timeout=90, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    return body if binary else body.decode("utf-8", "replace")


def text_of(fragment):
    out = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(out)).replace(" ", " ").strip()


def parse_roster_page(page):
    """district -> {name, profileUrl, committees[]}, plus the term sentence.

    Trap 1: split on the TEXT, so District 10's styled `<p>` heading is found
    exactly like the fifteen real `<h2>`s."""
    # Anchored on the PARAGRAPH, not on the words: the page's own description
    # <meta> repeats this sentence inside an attribute, and an unanchored search
    # returned the truncated meta value with its closing `" />` attached.
    term = None
    m = re.search(r"<p>\s*(Legislators are elected.*?)</p>", page, re.S)
    if m:
        term = text_of(m.group(1))

    marks = [(int(mm.group(1)), mm.start(), mm.end())
             for mm in re.finditer(r"District\s+No\.\s*(\d+)", page)]
    # The page's own navigation and prose can name a district too, so keep only
    # the run that is in ascending order from 1 — the roster block itself.
    rows = {}
    for idx, (num, _start, end) in enumerate(marks):
        stop = marks[idx + 1][1] if idx + 1 < len(marks) else len(page)
        body = page[end:stop]
        # TRAP 6: the LAST district has no next-district boundary, so its body
        # ran to the end of the document and swallowed the page footer's own
        # <ul> lists — District 16 read as 17 committees. Every district block
        # is closed by the <hr> the page draws between them, so cut there; this
        # is the same "the last contest has no next contest" arithmetic trap the
        # Jackson County canvass parser records, one document type over.
        rule = re.search(r"<hr\b", body)
        if rule:
            body = body[:rule.start()]
        # Trap 2 (the colon moves), trap 3 (nested <strong>), trap 4 (three
        # districts are unlinked): one pattern that allows all of them.
        label = re.search(r"<strong>(?:\s*<strong>)?\s*Legislator\s*:?\s*</strong>\s*:?", body, re.I)
        if not label:
            continue
        after = body[label.end():]
        # Trap 3's tail: District 11 wraps the whole label in a second <strong>,
        # so the closing tag and an &nbsp; sit BETWEEN the label and the name.
        # Consuming that run is what makes one pattern cover all sixteen — the
        # first draft matched the nested label and then found `</strong>` where
        # it wanted a name, and dropped District 11 while reporting District 10.
        after = re.sub(r"^(?:&nbsp;|\s|</?strong>|</?em>|</?b>|</?span[^>]*>)+", "", after)
        link = re.match(r"<a\s+href=\"([^\"]+)\"[^>]*>(.*?)</a>", after, re.S)
        if link:
            url = html.unescape(link.group(1))
            name = text_of(link.group(2))
        else:
            plain = re.match(r"([^<]+)", after)
            if not plain:
                continue
            url = None
            name = text_of(plain.group(1))
        name = name.strip(" ,;:")
        if not name:
            continue
        # TRAP 5: District 8's list is `<ul type="disc">`, so a bare `<ul>`
        # pattern loses its two committees and nothing fails — found only by
        # asking why a district showed zero. Every tag here allows attributes.
        #
        # A list is taken because it FOLLOWS A "Committees" LABEL, not because it
        # sits inside the district's byte range. That is trap 6's real fix: the
        # sixteenth district is closed by no <hr> at all, so its body runs to the
        # end of the document and a positional rule swallowed the page footer's
        # own link lists — District 16 read as seventeen committees, fourteen of
        # them "Like us on Facebook" and its siblings. The footer has no such
        # label before it, so a semantic rule cannot reach it however far the
        # body extends. The label covers both headings the page uses
        # ("Committees:" and "Special/Advisory Committees:").
        committees = []
        for label_m in re.finditer(r"<strong>[^<]*Committees[^<]*</strong>", body, re.I):
            block = re.search(r"<ul[^>]*>(.*?)</ul>", body[label_m.end():], re.S)
            if not block:
                continue
            for li in re.finditer(r"<li[^>]*>(.*?)</li>", block.group(1), re.S):
                c = text_of(li.group(1))
                if c:
                    committees.append(c)
        if num in rows:
            raise SystemExit("tompkins-legislature-roster: district %d appears twice on the roster "
                             "page — the split found a heading outside the roster block" % num)
        rows[num] = {"name": name, "profileUrl": url, "committees": committees}
    return rows, term


PHONE = r"\(?\d{3}\)?[ \-]?\d{3}[-.]?\d{4}"


def parse_contact_pdf(path):
    """district -> {party, email, phone}, plus the body's own office and officers.

    Every line carries a HOME ADDRESS between the name and the telephone. It is
    matched so the parser can prove it saw it, and then discarded — see the
    module docstring."""
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)

    office = {}
    m = re.search(r"^(.*Building)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*$", text, re.M)
    if m:
        office["lines"] = [m.group(1).strip(), m.group(2).strip(), m.group(3).strip()]
    m = re.search(r"Phone:\s*(" + PHONE + r")", text)
    if m:
        office["phone"] = m.group(1).strip()
    m = re.search(r"Fax:\s*(" + PHONE + r")", text)
    if m:
        office["fax"] = m.group(1).strip()

    officers = {}
    for role in ("Chair", "Vice Chair"):
        # Vice Chair first would also match "Chair", so anchor on the line start
        # and take the longest role the line names.
        for mm in re.finditer(r"^([A-Z][^,\n]+),\s*(Vice Chair|Chair)\s*$", text, re.M):
            officers[mm.group(2)] = mm.group(1).strip()
        if role in officers:
            continue

    rows = {}
    addresses_seen = 0
    pattern = re.compile(
        r"^(\d{1,2})\s*\(([A-Z]{1,2})\)\s*([^,]+),\s*(.+?)\s*(" + PHONE + r")\s*$\s*"
        r"E-mail:\s*(\S+@\S+)", re.M)
    for mm in pattern.finditer(text):
        num = int(mm.group(1))
        party = mm.group(2)
        name = mm.group(3).strip()
        home = mm.group(4).strip()          # matched so its absence is detectable
        phone = mm.group(5).strip()
        email = mm.group(6).strip().rstrip(".")
        if home:
            addresses_seen += 1
        del home                            # and never carried past this line
        rows[num] = {"party": PARTY_NAMES.get(party, party), "partyCode": party,
                     "email": email, "phone": phone, "pdfName": name}
    if addresses_seen != len(rows):
        raise SystemExit("tompkins-legislature-roster: the contact sheet stopped printing a home "
                         "address on %d of %d rows. That is not a reason to relax the pattern — the "
                         "pattern's job is to RECOGNISE the address so it can be dropped, and a "
                         "pattern that no longer recognises it may start shipping it."
                         % (len(rows) - addresses_seen, len(rows)))
    return rows, office, officers


def fetch_witness():
    """The map layer's own Member column, read only to be compared."""
    q = WITNESS_URL + "?" + urllib.parse.urlencode({
        "where": "1=1", "outFields": "LegDist,Member", "returnGeometry": "false", "f": "json"})
    data = json.loads(fetch(q))
    return {int(f["attributes"]["LegDist"]): (f["attributes"]["Member"] or "").strip()
            for f in data.get("features", [])}


def surname(name):
    parts = [p for p in re.split(r"[\s]+", name) if p]
    return parts[-1].lower().strip(".,") if parts else ""


def main(argv):
    ap = argparse.ArgumentParser(description="Scrape Tompkins County's legislature roster.")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    for url in (ROSTER_URL, CONTACT_PDF, WITNESS_URL):
        why = require_robots_allowed(url, UA, label="tompkins-legislature-roster")
        print("tompkins-legislature-roster: robots %s — %s" % (urllib.parse.urlparse(url).netloc, why))

    page = fetch(ROSTER_URL)
    rows, term = parse_roster_page(page)
    if sorted(rows) != list(range(1, DISTRICTS + 1)):
        raise SystemExit("tompkins-legislature-roster: the roster page yielded districts %s, not "
                         "1..%d. District 10's heading is a styled <p> rather than an <h2> — if "
                         "that is what went missing, the split stopped reading the TEXT."
                         % (sorted(rows), DISTRICTS))

    pdf_path = os.path.join(os.path.dirname(os.path.abspath(args.out)), "tompkins-contacts.pdf")
    with open(pdf_path, "wb") as fh:
        fh.write(fetch(CONTACT_PDF, binary=True))
    contacts, office, officers = parse_contact_pdf(pdf_path)
    if sorted(contacts) != list(range(1, DISTRICTS + 1)):
        raise SystemExit("tompkins-legislature-roster: the contact sheet yielded districts %s, not "
                         "1..%d" % (sorted(contacts), DISTRICTS))
    if not office.get("phone"):
        raise SystemExit("tompkins-legislature-roster: the contact sheet published no switchboard, "
                         "so a member's telephone can no longer be told from the body's")

    witness = fetch_witness()
    drift = []
    for num in range(1, DISTRICTS + 1):
        page_s = surname(rows[num]["name"])
        pdf_s = surname(contacts[num]["pdfName"])
        map_s = surname(witness.get(num, ""))
        if page_s != pdf_s:
            raise SystemExit("tompkins-legislature-roster: district %d — the roster page says %r "
                             "and the county's own contact sheet says %r. The join is by district "
                             "number and the two surfaces have stopped naming the same person; "
                             "nothing ships until a human reads both."
                             % (num, rows[num]["name"], contacts[num]["pdfName"]))
        if map_s != page_s:
            drift.append((num, rows[num]["name"], witness.get(num, "")))
    for num, page_name, map_name in drift:
        print("tompkins-legislature-roster: DRIFT district %d — the map layer's Member column says "
              "%r where the county's roster page says %r. The page ships; this is the Coles witness "
              "reporting, not failing." % (num, map_name, page_name), file=sys.stderr)

    switchboard = re.sub(r"\D", "", office["phone"])
    members = {}
    for num in range(1, DISTRICTS + 1):
        c = contacts[num]
        personal = re.sub(r"\D", "", c["phone"]) != switchboard
        members[str(num)] = {
            "district": num,
            "name": rows[num]["name"],
            "party": c["party"],
            "email": c["email"],
            # a number equal to the body's switchboard is the BODY's, not theirs
            "phone": c["phone"] if personal else None,
            "profileUrl": rows[num]["profileUrl"],
            "committees": rows[num]["committees"],
            "role": None,
        }
    for role, who in officers.items():
        hits = [k for k, v in members.items() if surname(v["name"]) == surname(who)]
        if len(hits) != 1:
            raise SystemExit("tompkins-legislature-roster: the contact sheet's %s %r matches %d of "
                             "the sixteen by surname — the role join needs a unique surname"
                             % (role, who, len(hits)))
        members[hits[0]]["role"] = role
        print("tompkins-legislature-roster: role %s -> district %s (%s), joined on surname %r"
              % (role, hits[0], members[hits[0]]["name"], surname(who)))

    doc = {"members": members, "office": office, "term": term,
           "sources": {"roster": ROSTER_URL, "contacts": CONTACT_PDF, "witness": WITNESS_URL},
           "drift": [{"district": d, "page": p, "layer": m} for d, p, m in drift]}
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    personal_phones = sum(1 for v in members.values() if v["phone"])
    print("tompkins-legislature-roster: OK %d legislators, %d with a personal telephone (%d print "
          "the Legislature's own switchboard and get none), %d with an e-mail, %d with a profile "
          "link, roles %s, %d map-column drift(s)" %
          (len(members), personal_phones, DISTRICTS - personal_phones,
           sum(1 for v in members.values() if v["email"]),
           sum(1 for v in members.values() if v["profileUrl"]),
           sorted(officers) or "none", len(drift)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
