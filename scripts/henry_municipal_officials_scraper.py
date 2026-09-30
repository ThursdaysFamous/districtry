#!/usr/bin/env python3
"""
Scrape Henry County's clerk handbook into the payload
build_municipal_officials_roster.py consumes.

SOURCE. The County Clerk/Recorder publishes a "Handbook of Elected & Appointed
Officials" — a 75-page PDF, "Printed June 1, 2025, Updated January 29, 2026".
That date is the whole reason this county is buildable: the update lands AFTER
the April 2025 consolidated election, so every municipal seat in it reflects the
current term. A directory that predates that election would be a roster of
former officeholders wearing current names, which is the failure the honesty
rules exist to prevent.

The clerk pointed at it directly (2026-08-03) after this project asked whether
the county published a municipal list; nothing on the site's search surfaced it,
because it is a CivicPlus DocumentCenter file linked only from the left-hand nav
of /221/County-Clerk. **When a county's list cannot be found, ask the clerk** —
that is now twice this pass (McDonough, Henry) that the answer was "yes, here".

DEPTH. The handbook names the FULL governing body of all fifteen
municipalities: head of government, clerk, and every trustee / alderperson /
council member, with term-expiry years throughout and WARD NUMBERS for the three
ward-electing municipalities (Colona, Galva, Geneseo). That is DeKalb/LaSalle
depth, so Henry joins as a full-governing-body county.

WHY LINE PARSING HERE, NOT POSITIONAL. LaSalle and Tazewell needed word
positions because their offices and names extract as separate blocks. This
document does not: every officer extracts on one line with the office or place
that owns it. Positional parsing would be ceremony, not safety. What this
document needs instead is an ANCHORED place list — see below.

THE PLACE LIST IS THE ANCHOR. Four sections describe the same fifteen
municipalities with four different separators — "ALPHA ----------", "(V)
ALPHA----", "(H) BISHOP HILL—---" (em-dash), "(C) GALVA-----–" (en-dash), and a
bare "V ALPHA 102 S 2nd St" where nothing but a digit separates the place from
its address. Writing a regex per shape invites a silent miss. So the MAYORS
section is parsed first and establishes the canonical fifteen; every later
section matches its lines against that set, longest name first. A place that
appears in a later section but not in the mayors list is a warning, never a
guess.

THE HEAD'S TITLE IS THE DOCUMENT'S, NOT AN ASSUMPTION. The mayors section is
headed "MAYOR OR VILLAGE PRESIDENT" and never says which of the two any given
municipality has, so labelling all fifteen "Mayor" would assert something the
source declines to. The TRUSTEES section does say: every heading names the legal
form ("Village of Alpha", "City of Colona Aldermen"), so the head's title is
read from there — City -> Mayor, Village or Town -> President. Fifteen headings
for fifteen municipalities, so nothing falls through.

ADDRESSES COME FROM ONE SECTION ONLY, and this is a privacy rule, not a parsing
convenience. The trustee lines print each member's HOME address ("Brad Barton
(unexpired term 2027) 305 N Park St Alpha 61413"), and in the smaller villages
so do the mayor and clerk lines — Alpha's mayor is listed at 208 W E St while
Alpha's village office is 102 S 2nd St. Only the "CLERKS OFFICES" section is
labelled as offices, so only it supplies an address. Every other section's
address text is discarded on the way in and never reaches the payload. Hooppole
is absent from that section and therefore ships with no address rather than with
its president's house.

TWO MARKERS THIS DOCUMENT PRINTS AND THIS SCRAPER DOES NOT INTERPRET:

  * "(A)" after a clerk is defined by the section's own legend as Appointed, so
    it maps to the payload's `appointed` flag.
  * "(V)" appears after three mayors and beside a second Cleveland phone. The
    handbook defines "V" as Village in one section's legend, but Colona and
    Kewanee are cities and Cambridge is a village, so that reading does not
    hold. It is stripped and reported once, never shipped as a meaning. An
    unexplained marker is not data.

"Vacancy" is counted and never named — the Livingston/Stephenson posture.

TWO FLEET RULES THIS SOURCE TRIGGERS:

  * A PHONE THAT IS THE HALL'S IS NOT A DIRECT LINE. The handbook prints a
    number beside every mayor and clerk, and for nine of them it is simply the
    village office number already carried under `office`. Shipping it on the
    person would tell a resident they can reach the mayor directly when the
    document says no such thing, so a person phone equal to the hall phone is
    dropped. The ones that differ — Alpha's mayor, Hooppole's president and
    clerk on two different area codes — are genuine and kept.
  * AN ELECTED HEAD DOES NOT ALSO HOLD A BOARD SEAT, so a board row naming the
    person already published as head is dropped — matched the way the builder
    matches people (surname plus a given-name truncation), never on the exact
    string. It fires nowhere in the current edition and is carried as a guard.

    ORION LOOKS LIKE THAT CASE AND IS NOT, which is why the rule is written to
    miss it rather than widened to catch it. The handbook prints "Steve Newman"
    as head and "Stephen R. Newman" (term 2027) among the trustees, and those
    are one man: Orion's April 2025 winner could not take the oath, and the
    board elected a sitting trustee to the presidency in his place. He holds
    both offices, so both rows are true and both ship. This is the builder's
    documented "acting president" posture — a sitting trustee wearing the gavel
    — reached by a different route. A looser surname-only rule would have
    "fixed" Orion by deleting a seat its village really fills.

URL DISCOVERY, not a hardcoded path: CivicPlus DocumentCenter ids restamp when a
document is replaced, so the link is read off the clerk page and the constant
below is only a fallback.

Usage:
    python3 henry_municipal_officials_scraper.py --out henry_municipal_officials.json
    python3 henry_municipal_officials_scraper.py --out out.json --pdf local.pdf
"""

import argparse
import datetime
import io
import json
import re
import sys

import requests
from scraper_common import require_robots_once, UA_CHROME_WIN_126  # noqa: E402  (shared machinery — do not fork)

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

CLERK_PAGE = "https://www.henrycty.com/221/County-Clerk"
HANDBOOK_FALLBACK = "https://www.henrycty.com/DocumentCenter/View/1102/THEHANDBOOK"
HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
}
REQUEST_TIMEOUT = 120

# Section boundaries, matched against a whole extracted line.
SEC_MAYORS = re.compile(r"^MAYOR OR VILLAGE PRESIDENT$")
SEC_CLERKS = re.compile(r"^CLERKS$")
SEC_OFFICES = re.compile(r"^CLERKS OFFICES$")
SEC_TRUSTEES = re.compile(r"^TRUSTEES$")
SEC_END = re.compile(r"^TOWNSHIP SUPERVISORS$")

# "ALPHA ----------Rebecca Brown (2029) (309)236-9236". The separator run mixes
# hyphen, en-dash and em-dash across the document, so all three are accepted.
DASHES = "\\-\u2010\u2011\u2012\u2013\u2014\u2015"
MAYOR_RE = re.compile(r"^([A-Z][A-Z .'&]*?)\s*[%s]{2,}\s*(.+)$" % DASHES)

PAGE_NUM_RE = re.compile(r"^\[\s*\d+\s*\]$")
PHONE_RE = re.compile(r"\((\d{3})\)\s*(\d{3})[\-\s]?(\d{4})")
YEAR_RE = re.compile(r"\((?:[^()]*?\b)?(20\d{2})\)")
APPOINTED_RE = re.compile(r"\(A\)")
# Stripped and reported, never interpreted — see the module docstring.
UNEXPLAINED_V_RE = re.compile(r"\(V\)")
WARD_RE = re.compile(r"^Ward\s+(\d+)$")
ZIP_RE = re.compile(r"\b(6\d{4})\b")
NA_RE = re.compile(r"(?i)\bN/?A\b")
TRUSTEE_HEAD_RE = re.compile(
    r"^(?:Village|City|Town)\s+of\s+(.+?)"
    r"(?:\s+(Aldermen|Councilmen|Council\s*Members?|Trustees))?$")
# "Lisa Sides – Treasurer 404 N Maple St" / "City Administrator – JoAnn Hollenkamp"
INLINE_ROLE_RE = re.compile(r"^(.*?)\s*[\u2013\u2014-]\s*(.*?)$")
NON_PERSON = ("vacancy", "vacant", "(vacancy)", "n/a")

# Office titles the trustee section prints as its own sub-heading or inline.
OFFICER_TITLES = {
    "treasurer": "Treasurer",
    "city administrator": "City Administrator",
    "village administrator": "Village Administrator",
    "administrator": "Administrator",
    "city manager": "City Manager",
    "village manager": "Village Manager",
    "clerk": "Clerk",
    "deputy clerk": "Deputy Clerk",
}
# Titles the county prints that nobody elected; flagged so a card can never
# imply otherwise.
APPOINTED_TITLES = {"city administrator", "village administrator", "administrator",
                    "city manager", "village manager", "deputy clerk"}

# Deliberate under-tolerances against the 2026-01-29 edition (15 municipalities
# / 15 heads / ~120 officials). Henry has fifteen incorporated places and the
# handbook covers every one, so these sit only two under the full set: this
# county cannot lose three municipalities without something being wrong.
MIN_MUNICIPALITIES = 13
MIN_HEADS = 13
MIN_OFFICIALS = 100
# The three ward-electing municipalities. A parse that lost the "Ward n"
# sub-headings would still produce a plausible roster — every alderperson would
# simply be at-large — so the ward seats are floored separately.
MIN_WARD_SEATS = 18


def discover_pdf_url(session, warnings):
    """Read the handbook link off the clerk page; fall back to the known id."""
    try:
        require_robots_once(CLERK_PAGE, HEADERS["User-Agent"], headers=HEADERS,
                            label="il-henry-municipal-officials-scraper")
        resp = session.get(CLERK_PAGE, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001 — discovery is best-effort
        warnings.append("could not read %s (%s) — using the recorded handbook URL"
                        % (CLERK_PAGE, type(exc).__name__))
        return HANDBOOK_FALLBACK
    match = re.search(r'href="(/DocumentCenter/View/\d+/[^"]*)"[^>]*>\s*'
                      r'Handbook of Elected', resp.text, re.I)
    if not match:
        warnings.append("the clerk page no longer links a 'Handbook of Elected …' "
                        "document — using the recorded URL, which may be stale")
        return HANDBOOK_FALLBACK
    return "https://www.henrycty.com" + match.group(1)


def fetch_pdf(session, url):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-henry-municipal-officials-scraper")
    resp = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    if not resp.content.startswith(b"%PDF"):
        raise RuntimeError("%s did not return a PDF (got %d bytes of %s)"
                           % (url, len(resp.content), resp.headers.get("Content-Type")))
    return resp.content


def lines_of(pdf_bytes):
    if pdfplumber is None:
        raise RuntimeError("pdfplumber is required "
                           "(pip install -c scripts/requirements.txt pdfplumber)")
    out = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for line in (page.extract_text() or "").splitlines():
                line = line.strip()
                if line and not PAGE_NUM_RE.match(line):
                    out.append(line)
    return out


def section(lines, start_re, end_res):
    """Lines strictly between the first `start_re` match and the next end marker."""
    try:
        i = next(n for n, l in enumerate(lines) if start_re.match(l))
    except StopIteration:
        return []
    out = []
    for line in lines[i + 1:]:
        if any(r.match(line) for r in end_res):
            break
        out.append(line)
    return out


def strip_markers(text, place, warnings):
    """Remove the markers this document prints, reporting the undefined one."""
    if UNEXPLAINED_V_RE.search(text):
        warnings.append("%s: the handbook prints an undefined '(V)' marker — "
                        "stripped, not interpreted" % place)
        text = UNEXPLAINED_V_RE.sub(" ", text)
    return text


def person_and_year(text):
    """-> (name, term_expiry_year or None) from 'Jane Doe (2029)' shapes."""
    year = None
    match = YEAR_RE.search(text)
    if match:
        year = match.group(1)
    name = YEAR_RE.sub(" ", text)
    name = re.sub(r"\((?:[^()]*)\)", " ", name)      # any remaining parenthetical
    # "Charity VanDamme (2029) N/A" — the handbook writes N/A where a member
    # publishes no address. Stripped here so it cannot end up inside a name.
    name = NA_RE.sub(" ", name)
    name = re.sub(r"\s+", " ", name).strip(" ,.;")
    return name, year


def parse_mayors(lines, warnings, zips):
    """-> ([place names in document order], [official records]).

    Also harvests each municipality's ZIP, which the CLERKS OFFICES section
    omits. Only the five digits are taken: a ZIP names a town, not a household,
    so it is the one part of these address lines that is safe to keep.
    """
    places, officials = [], []
    for index, line in enumerate(lines):
        match = MAYOR_RE.match(line)
        if not match:
            continue
        place = match.group(1).strip()
        rest = strip_markers(match.group(2), place, warnings)
        phone = PHONE_RE.search(rest)
        # The officer's address is on the FOLLOWING line, and everything on it
        # except the ZIP is discarded unread.
        following = lines[index + 1] if index + 1 < len(lines) else ""
        zipcode = ZIP_RE.search(following) if not MAYOR_RE.match(following) else None
        if zipcode:
            zips[place] = zipcode.group(1)
        # The address on this line is the officer's, not the hall's, in the
        # smaller villages — dropped here and never carried forward.
        name, year = person_and_year(PHONE_RE.sub(" ", rest))
        name = re.sub(r"\d.*$", "", name).strip(" ,.")   # trailing address text
        if not name or name.lower() in NON_PERSON:
            warnings.append("%s: no mayor/president named — counted, not named" % place)
            places.append(place)
            continue
        places.append(place)
        officials.append({
            "jurisdiction": place,
            "office": "Mayor",
            "name": name,
            "term_expires": year,
            "person_phone": "%s-%s-%s" % phone.groups() if phone else None,
        })
    return places, officials


def match_place(line, places):
    """Longest-first match of a line's opening against the canonical place list.

    Four sections spell the separator four ways; anchoring on the known places
    is what makes one rule cover all of them.
    """
    upper = line.upper()
    for place in sorted(places, key=len, reverse=True):
        # Allow the "(V) " / "V " prefixes the clerk sections carry.
        for prefix in ("", "(V) ", "(C) ", "(H) ", "(T) ", "V ", "C ", "T "):
            head = prefix + place
            if upper.startswith(head.upper()):
                return place, line[len(head):]
    return None, None


def parse_clerks(lines, places, warnings):
    officials = []
    for line in lines:
        place, rest = match_place(line, places)
        if place is None:
            continue
        rest = rest.lstrip(DASHES.replace("\\", "") + " \u2013\u2014")
        rest = strip_markers(rest, place, warnings)
        appointed = bool(APPOINTED_RE.search(rest))
        phone = PHONE_RE.search(rest)
        name, year = person_and_year(APPOINTED_RE.sub(" ", PHONE_RE.sub(" ", rest)))
        name = re.sub(r"\d.*$", "", name).strip(" ,.")
        if not name or name.lower() in NON_PERSON:
            warnings.append("%s: clerk seat published with no name — counted, not "
                            "named" % place)
            continue
        officials.append({
            "jurisdiction": place,
            "office": "Clerk",
            "name": name,
            "term_expires": None if appointed else year,
            "appointed": appointed,
            "person_phone": "%s-%s-%s" % phone.groups() if phone else None,
        })
    return officials


def parse_offices(lines, places, warnings):
    """-> {place: {office_address, office_phone}} — the ONLY source of addresses."""
    contact = {}
    for line in lines:
        if line.lower().startswith("hours:"):
            continue
        place, rest = match_place(line, places)
        if place is None:
            continue
        phone = PHONE_RE.search(rest)
        address = PHONE_RE.sub(" ", rest)
        address = NA_RE.sub(" ", address)
        # Bishop Hill's row repeats the town inside the address ("PO Box 117
        # Bishop Hill"); the builder appends the locality itself, so a trailing
        # repetition would print the town twice.
        address = re.sub(r"(?i)[\s,]*%s\s*$" % re.escape(place), "", address.strip())
        address = re.sub(r"\s+", " ", address).strip(" ,.")
        contact[place] = {
            "office_address": address or None,
            "office_phone": "%s-%s-%s" % phone.groups() if phone else None,
        }
    for place in places:
        if place not in contact:
            warnings.append("%s: absent from the CLERKS OFFICES section — ships "
                            "with no address rather than an officer's home" % place)
    return contact


HEAD_OFFICES = ("Mayor", "President")


def head_titles(lines, places, warnings):
    """-> {place: 'Mayor'|'President'} from the trustee section's own headings.

    The mayors section refuses to distinguish the two; these headings do not.
    A municipality with no heading falls back to "Mayor" — the word the mayors
    section leads with — and says so loudly, because that fallback is the one
    place in this parse where a title is assumed rather than read.
    """
    titles = {}
    for line in lines:
        head = TRUSTEE_HEAD_RE.match(line)
        if not head or PHONE_RE.search(line):
            continue
        raw = head.group(1).strip()
        match = next((p for p in places if p.upper() == raw.upper()), None)
        if match is None:
            continue
        titles[match] = "Mayor" if line.lower().startswith("city of") else "President"
    for place in places:
        if place not in titles:
            warnings.append("%s: the trustees section names no legal form for it "
                            "(City of / Village of), so its head is labelled "
                            "'Mayor' by assumption — verify it" % place)
    return titles


def board_office_for(suffix):
    key = re.sub(r"\s+", " ", (suffix or "").strip().lower())
    if key.startswith("alder"):
        return "Alderperson"
    if key.startswith("council"):
        return "Council Member"
    return "Trustee"


def parse_trustees(lines, places, warnings):
    officials = []
    current = None
    board_office = "Trustee"
    ward = None
    officer_title = None
    for line in lines:
        head = TRUSTEE_HEAD_RE.match(line)
        if head and not PHONE_RE.search(line):
            raw = head.group(1).strip()
            match = next((p for p in places if p.upper() == raw.upper()), None)
            if match is None:
                warnings.append("trustee heading '%s' names a municipality the "
                                "mayors section does not — skipped rather than "
                                "guessed" % raw)
                current = None
                continue
            current = match
            board_office = board_office_for(head.group(2))
            ward, officer_title = None, None
            continue
        if current is None:
            continue
        ward_m = WARD_RE.match(line)
        if ward_m:
            ward = "Ward %s" % ward_m.group(1)
            officer_title = None
            continue
        bare = line.strip().lower()
        if bare in OFFICER_TITLES:
            # A sub-heading naming an office; the rows under it are that office.
            officer_title = OFFICER_TITLES[bare]
            continue
        if bare.startswith("(vacancy") or bare.startswith("vacancy"):
            warnings.append("%s: a %s seat is published as Vacancy — counted, "
                            "never named" % (current, board_office))
            continue

        office = officer_title or board_office
        district = None if officer_title else ward
        text = line

        # "Lisa Sides – Treasurer 404 N Maple St" / "City Administrator – JoAnn
        # Hollenkamp": an inline role on either side of the dash.
        inline = INLINE_ROLE_RE.match(line)
        if inline and not officer_title:
            left, right = inline.group(1).strip(), inline.group(2).strip()
            left_key = re.sub(r"\s+", " ", left.lower())
            right_role = re.sub(r"\d.*$", "", right).strip().lower()
            if left_key in OFFICER_TITLES:
                office, district, text = OFFICER_TITLES[left_key], None, right
            elif right_role in OFFICER_TITLES:
                office, district, text = OFFICER_TITLES[right_role], None, left

        name, year = person_and_year(text)
        name = re.sub(r"\d.*$", "", name).strip(" ,.")   # the home address
        if not name or name.lower() in NON_PERSON:
            continue
        officials.append({
            "jurisdiction": current,
            "office": office,
            "name": name,
            "district": district,
            "term_expires": year,
            "appointed": office.lower() in APPOINTED_TITLES,
        })
    return officials


def name_tokens(name):
    return [t for t in re.split(r"[^A-Za-z]+", str(name or "").lower()) if t]


def same_person(a, b):
    """Surname agreement plus a given-name match or truncation.

    Mirrors build_municipal_officials_roster.same_person on purpose: the two
    have to agree about who is one person, and the case this exists for —
    "Steve Newman" against "Stephen R. Newman" — is exactly a truncation.
    """
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb or ta[-1] != tb[-1]:
        return False
    given_a, given_b = ta[:-1], tb[:-1]
    if not given_a or not given_b:
        return False
    for x in given_a:
        for y in given_b:
            if x == y:
                return True
            if len(x) >= 3 and len(y) >= 3 and (x.startswith(y) or y.startswith(x)):
                return True
    return False


def drop_head_duplicates(officials, warnings):
    """Remove a board/officer row naming the person already published as head."""
    heads = {}
    for person in officials:
        if person["office"] in HEAD_OFFICES:
            heads[person["jurisdiction"]] = person["name"]
    kept = []
    for person in officials:
        head = heads.get(person["jurisdiction"])
        if person["office"] not in HEAD_OFFICES and head and \
                same_person(head, person["name"]):
            warnings.append("%s: dropped the %s row for %s — the same person is "
                            "published as the head of government"
                            % (person["jurisdiction"], person["office"], person["name"]))
            continue
        kept.append(person)
    return kept


def parse(pdf_bytes, source_url, warnings):
    lines = lines_of(pdf_bytes)
    mayor_lines = section(lines, SEC_MAYORS, [SEC_CLERKS, SEC_END])
    clerk_lines = section(lines, SEC_CLERKS, [SEC_OFFICES, SEC_END])
    office_lines = section(lines, SEC_OFFICES, [SEC_TRUSTEES, SEC_END])
    trustee_lines = section(lines, SEC_TRUSTEES, [SEC_END])
    for label, block in (("MAYOR OR VILLAGE PRESIDENT", mayor_lines),
                         ("CLERKS", clerk_lines),
                         ("CLERKS OFFICES", office_lines),
                         ("TRUSTEES", trustee_lines)):
        if not block:
            raise RuntimeError("the handbook's '%s' section is empty or missing — "
                               "the document's structure has changed" % label)

    zips = {}
    places, officials = parse_mayors(mayor_lines, warnings, zips)
    if not places:
        raise RuntimeError("no municipalities parsed from the mayors section — "
                           "every later section anchors on that list")
    titles = head_titles(trustee_lines, places, warnings)
    for person in officials:
        person["office"] = titles.get(person["jurisdiction"], person["office"])
    officials += parse_clerks(clerk_lines, places, warnings)
    officials += parse_trustees(trustee_lines, places, warnings)
    officials = drop_head_duplicates(officials, warnings)

    contact = parse_offices(office_lines, places, warnings)
    for person in officials:
        person.setdefault("district", None)
        person.setdefault("appointed", False)
        person.update(contact.get(person["jurisdiction"], {}))
        person["office_zip"] = zips.get(person["jurisdiction"])
        person["office_city"] = person["jurisdiction"].title()
        person["office_state"] = "IL"
        # A number the document also prints as the hall's is the hall's.
        if person.get("person_phone") and \
                person["person_phone"] == person.get("office_phone"):
            warnings.append("%s: the phone beside the %s is the village office "
                            "line — not shipped as a direct number"
                            % (person["jurisdiction"], person["office"]))
            person["person_phone"] = None
        person["source_url"] = source_url
    return places, officials


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--pdf", help="parse a local copy instead of fetching")
    args = ap.parse_args()

    warnings = []
    session = requests.Session()
    try:
        if args.pdf:
            source_url, pdf_bytes = HANDBOOK_FALLBACK, open(args.pdf, "rb").read()
        else:
            source_url = discover_pdf_url(session, warnings)
            pdf_bytes = fetch_pdf(session, source_url)
        places, officials = parse(pdf_bytes, source_url, warnings)
    except Exception as exc:  # noqa: BLE001
        print("FATAL: %s" % exc, file=sys.stderr)
        sys.exit(1)

    for warning in sorted(set(warnings)):
        print("  warning: %s" % warning, file=sys.stderr)

    heads = sum(1 for o in officials if o["office"] in HEAD_OFFICES)
    ward_seats = sum(1 for o in officials if o.get("district"))
    problems = []
    if len(places) < MIN_MUNICIPALITIES:
        problems.append("%d municipalities < floor %d" % (len(places), MIN_MUNICIPALITIES))
    if len(officials) < MIN_OFFICIALS:
        problems.append("%d officials < floor %d" % (len(officials), MIN_OFFICIALS))
    if heads < MIN_HEADS:
        problems.append("%d heads of government < floor %d" % (heads, MIN_HEADS))
    if ward_seats < MIN_WARD_SEATS:
        problems.append("%d ward seats < floor %d — the 'Ward n' sub-headings may "
                        "have stopped parsing" % (ward_seats, MIN_WARD_SEATS))
    if problems:
        for problem in problems:
            print("  FAIL: %s" % problem, file=sys.stderr)
        print("FATAL: refusing to write a payload that lost coverage", file=sys.stderr)
        sys.exit(1)

    payload = {
        "county": "Henry",
        "directory_url": source_url,
        "officials_page": CLERK_PAGE,
        "scraped_at": datetime.datetime.now(datetime.timezone.utc)
                              .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "municipalities": places,
        "officials": officials,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("scraped %d municipalities, %d officials (%d heads, %d ward seats) -> %s"
          % (len(places), len(officials), heads, ward_seats, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
