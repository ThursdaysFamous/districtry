#!/usr/bin/env python3
"""
Read the Macoupin County Clerk's elected-officials directory into the payload
build_municipal_officials_roster.py consumes.

SOURCE, AND WHY IT TOOK A CAPTURE TO FIND. The Clerk's directory lives at
macoupinvotes.gov/election-results/elected-officials/ and that page is EMPTY:
78,839 bytes containing zero occurrences of Mayor, President, Alderman,
Trustee, Ward, "Village of" or "City of". The names are drawn in afterwards by
a vendor WordPress plugin (soe_elected_officials, SOE Software), whose own
scripts carry no endpoint, and the page localises admin-ajax.php only for its
event calendar. That is why five plausible WordPress action names each came
back "0"/HTTP 400 on 2026-08-20 and the gap record was left saying the address
would need "one look at the page in a browser's developer tools."

The look was taken, on 2026-08-20, and the reason no WordPress action was ever
going to answer is that THE DIRECTORY IS NOT WORDPRESS. The plugin calls out to
a separate Java/Seam REST service mounted beside the CMS at /ce/, and it calls
it as JSONP:

    GET /ce/mobile/seam/resource/rest/voter/getelectedofficials
        ?lang=en&callback=soeElectedOfficials.initCallBack

Unauthenticated, GET, no body, no cookie required — the service issues its own
session on first contact. So the "browser-only" directory needs no browser at
all once the address is known; this module is an ordinary requests client.

DEPTH. All 27 of Macoupin's incorporated places, complete governing bodies:
8 ward cities (28 wards between them) and 19 villages, 252 offices.

THE FIELD THAT MEANS THE OPPOSITE OF ITS NAME. Each office carries
`effectiveAtLarge`, and reading it as "elected at large" would be a fabricated
fact on six rows. The vendor's own client script appends " *" to an office
title when the flag is set (soe_elected_officials_4.0.js), and the site's text
map defines that asterisk:

    ELECTED_OFFICIALS_DETAIL_AT_LARGE_INDICATOR = "*"
    ELECTED_OFFICIALS_DETAIL_AT_LARGE_LEGEND    = "Appointed to Fill Unexpired Term"

So on this deployment the flag means APPOINTED TO FILL AN UNEXPIRED TERM. It is
mapped to the builder's `appointed`, and the legend is re-read and asserted on
every run: if the county ever re-words it, this refuses to write rather than
silently re-interpreting six people's seats.

HOME ADDRESSES ARE NEVER READ. The per-office detail endpoint returns an
`address` array with the officeholder's RESIDENCE in it — `person.address`, and
`office.address2`, which is the same house on 149 of the 245 offices that carry
one. Only `office.address1` is read, and only when the service labels it
"Village Hall", "City Office" or "Village Office"; the shipped address is then
asserted not to equal any officeholder's residence in that municipality. The
Cass rule, made explicit: a whole field is discarded rather than filtered.

CONTACT IS MUNICIPALITY-LEVEL ONLY, and that is a measurement, not a default.
The service's `office.email` looks per-person and is not reliably so: Staunton's
Ward 4 alderman Matthew McKee carries jmoore@stauntonil.com — his predecessor's
address — and four different Virden officeholders carry mlackey@virdenonline.com.
Attributing either to the person named beside it would be wrong, so no
`person_email` and no `person_phone` ship. What ships is the municipality's own
hall contact, chosen as the MODAL value across that municipality's offices,
which also disposes of the county's transcription typos in the same stroke
(Brighton's hall is (618)372-8860 on eight rows and (608)372-8860 on the ninth;
Carlinville's is (217)854-4076 on ten and (217)954-4076 on one). An e-mail must
additionally appear on offices held by at least two DIFFERENT people before it
can be called the municipality's — otherwise the mayor's own address would
become the city's (Carlinville: ddowney@ appears twice, the second time on a
vacant seat).

`office.phone2` / `email2` / `website2` are the vendor's second-contact slot and
sit beside address2, the residence; a county board member's pair there is a
mobile number and a gmail address. They are not read.

Usage:
    python3 scripts/macoupin_municipal_officials_scraper.py --out macoupin_muni.json
    python3 scripts/macoupin_municipal_officials_scraper.py --out out.json --skip-contact
"""

import argparse
import collections
import datetime
import json
import re
import sys
import time

import requests
from scraper_common import require_robots_once, UA_CHROME_WIN_126  # noqa: E402  (shared machinery — do not fork)

REST = "https://www.macoupinvotes.gov/ce/mobile/seam/resource/rest/voter/"
# The callback the page itself uses, sent verbatim so the request this makes is
# the request the directory makes.
CALLBACK = "soeElectedOfficials.initCallBack"
LIST_URL = REST + "getelectedofficials?lang=en&callback=" + CALLBACK
TEXT_URL = REST + "getelectedofficialstext?lang=en&callback=" + CALLBACK
DETAIL_URL = REST + "getelectedofficial?officeId=%d&lang=en&callback=" + CALLBACK

# The reader-facing page, which is what a card links to. The REST address above
# is an implementation detail of that page, not somewhere to send a person.
OFFICIALS_PAGE = "https://www.macoupinvotes.gov/election-results/elected-officials/"
SOURCE_NOTE = ("Macoupin County Clerk, Elected Officials directory "
               "(macoupinvotes.gov), read from the SOE Connect elected-officials "
               "service the page itself queries")

HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
    "Accept": "*/*",
}
REQUEST_TIMEOUT = 60
# 285 requests at this pace is about two minutes. The service answered all of
# them without a single error at 0.35s; 0.4s leaves headroom.
DETAIL_PAUSE = 0.4

MUNICIPAL_LEVEL = "City and Village"

# The legend that fixes what `effectiveAtLarge` means here. Re-read every run.
AT_LARGE_LEGEND_KEY = "ELECTED_OFFICIALS_DETAIL_AT_LARGE_LEGEND"
AT_LARGE_LEGEND = "Appointed to Fill Unexpired Term"

# Every "City and Village" district the service publishes, mapped to the
# municipality it belongs to in the Census's own spelling — which is the join
# key build_municipal_officials_roster.py resolves against. Two of the county's
# spellings would not match without it ("City of Gillepsie" is a typo for
# Gillespie, and "Bunker Ward 1" abbreviates Bunker Hill), and three abbreviate
# a name Census writes out (Mt Olive, Mt Clare). A district outside this table
# is a HARD FAILURE, never a guess: it means the county added a municipality or
# re-worded one, and both need a human.
JURISDICTIONS = {
    "City of Benld": "City of Benld",
    "Benld Ward 1": "City of Benld",
    "Benld Ward 2": "City of Benld",
    "Benld Ward 3": "City of Benld",
    "City of Bunker Hill": "City of Bunker Hill",
    "Bunker Ward 1": "City of Bunker Hill",
    "Bunker Ward 2": "City of Bunker Hill",
    "City of Carlinville": "City of Carlinville",
    "Carlinville Ward 1": "City of Carlinville",
    "Carlinville Ward 2": "City of Carlinville",
    "Carlinville Ward 3": "City of Carlinville",
    "Carlinville Ward 4": "City of Carlinville",
    "City of Gillepsie": "City of Gillespie",
    "Gillespie Ward 1": "City of Gillespie",
    "Gillespie Ward 2": "City of Gillespie",
    "Gillespie Ward 3": "City of Gillespie",
    "Gillespie Ward 4": "City of Gillespie",
    "City of Girard": "City of Girard",
    "Girard Ward 1": "City of Girard",
    "Girard Ward 2": "City of Girard",
    "Girard Ward 3": "City of Girard",
    "City of Mt Olive": "City of Mount Olive",
    "Mt Olive Ward 1": "City of Mount Olive",
    "Mt Olive Ward 2": "City of Mount Olive",
    "Mt Olive Ward 3": "City of Mount Olive",
    "Mt Olive Ward 4": "City of Mount Olive",
    "City of Staunton": "City of Staunton",
    "Staunton Ward 1": "City of Staunton",
    "Staunton Ward 2": "City of Staunton",
    "Staunton Ward 3": "City of Staunton",
    "Staunton Ward 4": "City of Staunton",
    "City of Virden": "City of Virden",
    "Virden Ward 1": "City of Virden",
    "Virden Ward 2": "City of Virden",
    "Virden Ward 3": "City of Virden",
    "Virden Ward 4": "City of Virden",
    "Village of Brighton": "Village of Brighton",
    "Village of Chesterfield": "Village of Chesterfield",
    "Village of Dorchester": "Village of Dorchester",
    "Village of Eagarville": "Village of Eagarville",
    "Village of East Gillespie": "Village of East Gillespie",
    "Village of Hettick": "Village of Hettick",
    "Village of Lake Ka-Ho": "Village of Lake Ka-Ho",
    "Village of Medora": "Village of Medora",
    "Village of Modesto": "Village of Modesto",
    "Village of Mt Clare": "Village of Mount Clare",
    "Village of Nilwood": "Town of Nilwood",
    "Village of Palmyra": "Village of Palmyra",
    "Village of Royal Lakes": "Village of Royal Lakes",
    "Village of Sawyerville": "Village of Sawyerville",
    "Village of Scottville": "Village of Scottville",
    "Village of Shipman": "Town of Shipman",
    "Village of Standard City": "Village of Standard City",
    "Village of White City": "Village of White City",
    "Village of Wilsonville": "Village of Wilsonville",
}

# Office titles, normalised to the builder's vocabulary. A title outside this
# table is a HARD FAILURE for the same reason a district is: the county changed
# its wording, or a new kind of office appeared. Each entry is
# (office, appointed) or, where one printed office holds two, a tuple of them.
OFFICE_TITLES = {
    "Mayor": [("Mayor", False)],
    "President": [("President", False)],
    "Trustee": [("Trustee", False)],
    "Trustee (Appointed)": [("Trustee", True)],
    # Lake Ka-Ho prints one of its six trustees with the village's name on it.
    "Lake KaHo Trustee": [("Trustee", False)],
    "Clerk": [("Clerk", False)],
    "City Clerk": [("City Clerk", False)],
    "Village Clerk": [("Village Clerk", False)],
    "Village Clerk (Appointed)": [("Village Clerk", True)],
    "Treasurer": [("Treasurer", False)],
    "Treasurer (Appointed)": [("Treasurer", True)],
    "Village Treasurer": [("Treasurer", False)],
    # Scottville fills two offices with one officer and prints them as one row.
    # Split, so the trustee half is counted as the board seat it is and the
    # clerk half carries its own appointed flag — the Oak Grove / Waynesville
    # precedent, taken one step further because these two are not the same kind
    # of office.
    "Clerk (Appointed) / Trustee": [("Clerk", True), ("Trustee", False)],
}
WARD_TITLE_RE = re.compile(r"^Alderman Ward (\d+)$")
WARD_DISTRICT_RE = re.compile(r"\bWard (\d+)$")

# Offices the county files under a municipality that are not that municipality's
# government. Skipped by name rather than by heuristic, and reported.
NOT_MUNICIPAL_OFFICES = {
    # A regional school office, filed under the City of Bunker Hill, unfilled.
    "EDUCATIONAL SERVICE REG 3(BROWN-CASS-MORGAN-SCOTT)",
}

# The service's own labels for the municipal office address. Anything else in
# the address1 slot is not shipped, because the only other address the payload
# carries is a residence.
HALL_LABELS = {"village hall", "city office", "village office"}

MIN_MUNICIPALITIES = 27
MIN_OFFICIALS = 220
MIN_HEADS = 26           # Hettick's presidency is published vacant
# 58 aldermanic offices across 28 wards (Bunker Hill seats three per ward, the
# other seven cities two), of which five are published vacant: 53 live.
MIN_WARD_SEATS = 50
MIN_OFFICE_PHONES = 24   # of 27; Eagarville publishes none


def strip_jsonp(text, url):
    """Unwrap `callback({...})`. The callback name is dotted, so the opening
    parenthesis is found by position rather than by pattern."""
    start = text.find("(")
    end = text.rfind(")")
    if start < 0 or end <= start:
        sys.exit("FATAL: %s did not answer with JSONP (%d bytes)" % (url, len(text)))
    try:
        return json.loads(text[start + 1:end])
    except ValueError as exc:
        sys.exit("FATAL: %s carried unreadable JSON (%s)" % (url, exc))


def get_json(session, url):
    try:
        require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                            label="il-macoupin-municipal-officials-scraper")
        resp = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001 — any failure is a refusal to write
        sys.exit("FATAL: could not read %s (%s: %s)" % (url, type(exc).__name__, exc))
    return strip_jsonp(resp.text, url)


def assert_at_large_legend(session):
    """The `effectiveAtLarge` -> appointed mapping rests entirely on this text.

    Re-read rather than remembered: if the county re-words the legend, the flag
    may no longer mean what this module says it means, and the honest response
    is to stop rather than to relabel six seats.
    """
    text_map = get_json(session, TEXT_URL)
    entry = (text_map or {}).get(AT_LARGE_LEGEND_KEY) or {}
    value = (entry.get("pageTextValue") or "").strip()
    if value != AT_LARGE_LEGEND:
        sys.exit("FATAL: %s now reads %r, not %r — the `effectiveAtLarge` flag "
                 "can no longer be read as 'appointed' without a human "
                 "re-checking what the page tells its readers"
                 % (AT_LARGE_LEGEND_KEY, value, AT_LARGE_LEGEND))
    return value


def holder_name(office):
    holder = office.get("officeHolder") or {}
    return (holder.get("ballotDisplay") or "").strip()


def election_year(value):
    """'Apr 3, 2029 12:00:00 AM' -> '2029'."""
    match = re.search(r"\b(20\d{2})\b", value or "")
    return match.group(1) if match else None


def collect_offices(payload, warnings):
    """-> ([(municipality, district_name, office_json)], vacancies, skipped)."""
    rows = []
    vacancies = 0
    skipped = []
    for district in payload.get("districts") or []:
        if district.get("jurisdictionLevel") != MUNICIPAL_LEVEL:
            continue
        name = (district.get("name") or "").strip()
        if name not in JURISDICTIONS:
            sys.exit("FATAL: unknown municipal district %r — the county added or "
                     "re-worded a municipality and JURISDICTIONS needs a human"
                     % name)
        municipality = JURISDICTIONS[name]
        for office in district.get("offices") or []:
            title = (office.get("title") or "").strip()
            if title in NOT_MUNICIPAL_OFFICES:
                skipped.append("%s: %s" % (municipality, title))
                continue
            if office.get("hideOnWebpage"):
                skipped.append("%s: %s (the county hides this row)"
                               % (municipality, title))
                continue
            rows.append((municipality, name, office))
            if not holder_name(office) or office.get("postAtVacant"):
                vacancies += 1
    return rows, vacancies, skipped


def address_text(entry):
    """A hall address as one line. address3 is never populated on this source
    and is read anyway so a future edition does not lose half a street."""
    parts = [(entry.get(key) or "").strip()
             for key in ("address1", "address2", "address3")]
    return " ".join(part for part in parts if part).strip()


def fetch_contact(session, rows, warnings):
    """-> {office_id: {...}} plus the residences to assert the hall against.

    One request per office. Only the fields named in the module docstring are
    kept; the address array is reduced to the single hall entry the office
    points at, and the officeholder's residence is kept ONLY to assert that the
    hall is not it, never to ship.
    """
    contact = {}
    residences = collections.defaultdict(set)
    for index, (municipality, _district, office) in enumerate(rows):
        office_id = office.get("id")
        if not isinstance(office_id, int):
            continue
        detail = get_json(session, DETAIL_URL % office_id)
        block = detail.get("office") or {}
        by_id = {entry.get("id"): entry
                 for entry in (detail.get("address") or [])
                 if isinstance(entry, dict)}
        hall = by_id.get(block.get("address1")) or {}
        label = (block.get("officeName1") or "").strip().lower()
        hall_text = address_text(hall) if label in HALL_LABELS else ""
        if hall and not hall_text:
            if label in HALL_LABELS:
                warnings.append("%s office %d: its %s entry carries no street — "
                                "not shipped"
                                % (municipality, office_id, block.get("officeName1")))
            else:
                warnings.append("%s office %d: address1 is labelled %r, which is "
                                "not one of the service's hall labels — not "
                                "shipped" % (municipality, office_id,
                                             block.get("officeName1")))
        person = (detail.get("person") or {}).get("address") or {}
        residence = address_text(person)
        if residence:
            residences[municipality].add(residence.lower())
        # address2 is the officeholder's own address on 149 of the 245 offices
        # that carry one; it is read here only to add to the residence set the
        # hall is asserted against, and never as a shippable address.
        second = by_id.get(block.get("address2")) or {}
        second_text = address_text(second)
        if second_text:
            residences[municipality].add(second_text.lower())
        contact[office_id] = {
            "phone": (block.get("phone") or "").strip(),
            "email": (block.get("email") or "").strip(),
            "website": (block.get("website") or "").strip(),
            "address": hall_text,
            "city": (hall.get("city") or "").strip(),
            "state": (hall.get("state") or "").strip(),
            "zip": (hall.get("zip") or "").strip(),
        }
        if index + 1 < len(rows):
            time.sleep(DETAIL_PAUSE)
    return contact, residences


def modal(counter, minimum=2):
    """The value a municipality's offices agree on, or nothing.

    `minimum` is what keeps one officer's own contact from becoming the town's:
    a value printed on a single office is that office's, and this source has
    been measured to be unreliable about which person that office belongs to.
    """
    if not counter:
        return None
    value, count = counter.most_common(1)[0]
    return value if count >= minimum else None


def municipality_contact(rows, contact, residences, warnings):
    """-> {municipality: {office_phone, office_email, office_address, website}}."""
    phones = collections.defaultdict(collections.Counter)
    emails = collections.defaultdict(collections.Counter)
    email_holders = collections.defaultdict(lambda: collections.defaultdict(set))
    sites = collections.defaultdict(collections.Counter)
    halls = collections.defaultdict(collections.Counter)
    hall_parts = {}
    for municipality, _district, office in rows:
        found = contact.get(office.get("id"))
        if not found:
            continue
        if found["phone"]:
            phones[municipality][found["phone"]] += 1
        if found["email"]:
            key = found["email"].lower()
            emails[municipality][key] += 1
            name = holder_name(office)
            if name:
                email_holders[municipality][key].add(name)
        if found["website"]:
            sites[municipality][found["website"]] += 1
        if found["address"]:
            halls[municipality][found["address"]] += 1
            hall_parts.setdefault((municipality, found["address"]), found)

    out = {}
    for municipality in sorted({row[0] for row in rows}):
        entry = {}
        phone = modal(phones[municipality])
        if phone:
            entry["office_phone"] = phone
        elif phones[municipality]:
            warnings.append("%s: no phone appears on two offices — none shipped"
                            % municipality)
        # An e-mail becomes the municipality's only when at least two DIFFERENT
        # people are published behind it. Carlinville's mayor's address appears
        # twice, the second time on a vacant seat, and is not the city's.
        shared = [(value, count) for value, count in emails[municipality].most_common()
                  if count >= 2 and len(email_holders[municipality][value]) >= 2]
        if shared:
            entry["office_email"] = shared[0][0]
        elif emails[municipality]:
            warnings.append("%s: every published e-mail belongs to one officer — "
                            "none shipped as the municipality's" % municipality)
        site = modal(sites[municipality], minimum=1)
        if site:
            entry["website"] = site
        hall = modal(halls[municipality])
        if hall:
            if hall.lower() in residences.get(municipality, set()):
                sys.exit("FATAL: %s's hall address %r is an officeholder's "
                         "residence — refusing to write" % (municipality, hall))
            entry["office_address"] = hall
            parts = hall_parts.get((municipality, hall)) or {}
            for key in ("city", "state", "zip"):
                if parts.get(key):
                    entry["office_" + key] = parts[key]
        elif halls[municipality]:
            warnings.append("%s: no hall address appears on two offices — none "
                            "shipped" % municipality)
        out[municipality] = entry
    return out


def build_records(rows, halls, warnings):
    officials = []
    ward_seats = 0
    for municipality, district_name, office in rows:
        title = (office.get("title") or "").strip()
        name = holder_name(office)
        if not name or office.get("postAtVacant"):
            continue

        ward = WARD_TITLE_RE.match(title)
        if ward:
            district = ward.group(1)
            from_district = WARD_DISTRICT_RE.search(district_name)
            if not from_district or from_district.group(1) != district:
                sys.exit("FATAL: %s prints %r inside district %r — the ward the "
                         "office names and the ward it sits in disagree"
                         % (municipality, title, district_name))
            entries = [("Alderman", False)]
            ward_seats += 1
        else:
            if title not in OFFICE_TITLES:
                sys.exit("FATAL: unknown office title %r in %s — a new kind of "
                         "office appeared and OFFICE_TITLES needs a human"
                         % (title, municipality))
            district = None
            entries = OFFICE_TITLES[title]

        # The county's asterisk: appointed to fill an unexpired term, asserted
        # against the site's own legend before any of this runs.
        unexpired = bool(office.get("effectiveAtLarge"))
        if unexpired:
            warnings.append("%s: %s (%s) is marked appointed to fill an "
                            "unexpired term" % (municipality, name, title))
        hall = halls.get(municipality) or {}
        for office_name, appointed in entries:
            record = {
                "jurisdiction": municipality,
                "office": office_name,
                "name": name,
                "district": district,
                "appointed": bool(appointed or unexpired),
                "source_url": OFFICIALS_PAGE,
                "source_note": SOURCE_NOTE,
            }
            year = election_year(office.get("nextElectionDate"))
            if year:
                record["next_election"] = year
            for key in ("office_phone", "office_email", "office_address",
                        "office_city", "office_state", "office_zip", "website"):
                if hall.get(key):
                    record[key] = hall[key]
            officials.append(record)
    return officials, ward_seats


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", default="macoupin_municipal_officials.json")
    parser.add_argument("--skip-contact", action="store_true",
                        help="names and offices only; skips the 252 per-office "
                             "detail requests that carry the hall contact")
    args = parser.parse_args()

    warnings = []
    session = requests.Session()

    legend = assert_at_large_legend(session)
    payload = get_json(session, LIST_URL)
    rows, vacancies, skipped = collect_offices(payload, warnings)

    if args.skip_contact:
        contact, residences = {}, {}
    else:
        contact, residences = fetch_contact(session, rows, warnings)
    halls = municipality_contact(rows, contact, residences, warnings)
    officials, ward_seats = build_records(rows, halls, warnings)

    places = sorted({row[0] for row in rows})
    heads = sum(1 for record in officials
                if record["office"] in ("Mayor", "President"))
    phones = sum(1 for entry in halls.values() if entry.get("office_phone"))

    problems = []
    if len(places) < MIN_MUNICIPALITIES:
        problems.append("%d municipalities < floor %d"
                        % (len(places), MIN_MUNICIPALITIES))
    if len(officials) < MIN_OFFICIALS:
        problems.append("%d officials < floor %d" % (len(officials), MIN_OFFICIALS))
    if heads < MIN_HEADS:
        problems.append("%d heads of government < floor %d" % (heads, MIN_HEADS))
    if ward_seats < MIN_WARD_SEATS:
        problems.append("%d ward seats < floor %d — a parse that lost the ward "
                        "numbers would still look like a plausible at-large "
                        "roster" % (ward_seats, MIN_WARD_SEATS))
    if not args.skip_contact and phones < MIN_OFFICE_PHONES:
        problems.append("%d municipalities with a hall phone < floor %d"
                        % (phones, MIN_OFFICE_PHONES))
    # The privacy invariant, asserted rather than assumed: nothing that reached a
    # record may be a residence, and no record may carry a person-level contact.
    for record in officials:
        shipped = (record.get("office_address") or "").lower()
        if shipped and shipped in residences.get(record["jurisdiction"], set()):
            problems.append("a residence reached %s's address" % record["jurisdiction"])
        for banned in ("person_phone", "person_email"):
            if record.get(banned):
                problems.append("%s carries %s" % (record["name"], banned))
    if problems:
        for problem in problems:
            print("  FAIL: %s" % problem, file=sys.stderr)
        sys.exit("FATAL: refusing to write a payload that lost coverage or leaked")

    output = {
        "county": "Macoupin",
        "officials_page": OFFICIALS_PAGE,
        "source_note": SOURCE_NOTE,
        "scraped_at": datetime.datetime.now(datetime.timezone.utc)
                              .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "municipalities": places,
        "officials": officials,
        "vacancies": vacancies,
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, ensure_ascii=False)

    per = collections.Counter(record["jurisdiction"] for record in officials)
    print("scraped %d municipalities, %d officials (%d heads, %d ward seats, "
          "%d marked appointed), %d vacant seats counted -> %s"
          % (len(places), len(officials), heads, ward_seats,
             sum(1 for r in officials if r["appointed"]), vacancies, args.out),
          file=sys.stderr)
    print("    the county's asterisk still reads %r" % legend, file=sys.stderr)
    print("    hall contact: %d phones, %d e-mails, %d addresses, %d websites"
          % (phones,
             sum(1 for e in halls.values() if e.get("office_email")),
             sum(1 for e in halls.values() if e.get("office_address")),
             sum(1 for e in halls.values() if e.get("website"))), file=sys.stderr)
    for place in places:
        print("    %-26s %d" % (place, per[place]), file=sys.stderr)
    for item in skipped:
        print("  not this municipality's government: %s" % item, file=sys.stderr)
    for warning in warnings:
        print("  note: %s" % warning, file=sys.stderr)


if __name__ == "__main__":
    main()
