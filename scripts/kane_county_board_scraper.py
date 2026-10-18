#!/usr/bin/env python3
"""
Scrape the Kane County Board member roster from the county's own SharePoint
list API.

Stage 1 of the two-stage roster pipeline (the Will/Kendall/McHenry shape);
scripts/build_kane_county_board_roster.py resolves the raw records into
data/app/kane-county-board-members.json, keyed by county-board district
("1".."24") plus a top-level "chair" for the countywide-elected Board Chair
(the DuPage roster shape), which index.html's consolidated county-board
layer joins to the county's own KaneCo_IL_County_Board boundary GIS by
district number (the GIS keeps carrying the sitting member's NAME — this
roster adds party, the official office phone, email, and a profile link).

Source: the directory page at
  https://www2.kanecountyil.gov/pages/countyboard/boardMembers.aspx
is a SharePoint page whose member table is rendered client-side from the
site's own REST API — the page's inline script calls

  GET /_api/web/lists/getbytitle('Board Members')/items?$orderby=District
  Accept: application/json;odata=nometadata

anonymously, and this scraper calls exactly that endpoint (no HTML parsing,
no browser, no bot-management ladder: unlike the Kendall/McHenry sites,
Kane's does not block automated clients — verified 2026-07-23). Fields
used: ID, FullName, District (null for the countywide Chair), Party,
Office/Home/Work/Cell (below), E_x002d_Mail (SharePoint's encoding of
"E-Mail", a mailto: URL), and the Chairman flag.

THE NUMBERS, LABELLED AND ORDERED AS THE COUNTY'S OWN PROFILE PAGE PRINTS
THEM. The member's profile page (BoardMember.aspx, which the directory links)
renders the list's numbers as "Home:", "Office:", "Work:", "Cell:" and "Fax:"
lines, in that order. Office is the member's own 630-444-12NN line at the
Government Center and stays first, as `phone` ("office 630-444-..."). Since
Adam's ruling of 2026-10-17 ("if the official government source uses personal
phone numbers, we publish those") the Home, Work and Cell numbers ship too, in
`phonesExtra` in the page's order, each led by the page's own label. Until that
day only the first non-empty of Office, Cell and Home shipped. Measured
2026-10-17: Office on 25 of 25 records, Cell on 4, Home on 1, Work on none.
Fax never ships. A number printed for two or more members, or equal to a
member's Office line or to the county's main number (COUNTY_MAIN_LINE, printed
in the footer of every county page), is an office line and is not shipped as
anyone's own.
The Chair's FullName carries a ", Madam Chair"-style suffix that is
stripped (the role is emitted separately); the record's Address (the
Government Center) and ServiceStart/Expires are not collected — the card
convention carries contact, not terms, and members' Address fields are
empty anyway.

Notes on data honesty (per project conventions):
- Values are read verbatim from the county's own list; a missing field is
  stored null, never guessed.
- Every record includes `source_url` (the member's own profile page, built
  from the list ID exactly as the county's directory links do) and
  `scraped_at` for traceability.

Usage:
    python3 kane_county_board_scraper.py [output.json]   # default: stdout
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone

import requests
from scraper_common import require_robots_once, UA_CHROME_WIN_126_FULL  # noqa: E402  (shared machinery — do not fork)

BASE = "https://www2.kanecountyil.gov"
LISTING_PAGE = BASE + "/pages/countyboard/boardMembers.aspx"
API_URL = BASE + "/_api/web/lists/getbytitle('Board%20Members')/items?$orderby=District"
PROFILE_URL = BASE + "/Pages/CountyBoard/BoardMember.aspx?bmID=%d"
HEADERS = {
    "User-Agent": UA_CHROME_WIN_126_FULL,
    "Accept": "application/json;odata=nometadata",
}

CHAIR_SUFFIX_RE = re.compile(r",\s*(madam\s+)?chair(man|woman)?\s*$", re.IGNORECASE)

# (list field, the label the profile page prints for it), in the page's order,
# Office excepted: Office leads, as `phone`, and the rest follow it.
FIRST_FIELD = ("Office", "office")
EXTRA_FIELDS = (("Home", "home"), ("Work", "work"), ("Cell", "cell"))
NUMBER_FIELDS = ("Office", "Home", "Work", "Cell", "Fax")
# The Kane County Government Center's main number, printed in the footer of the
# county's pages (read on a member profile page, 2026-10-17).
COUNTY_MAIN_LINE = "630-232-3400"


def clean(text):
    if text is None:
        return None
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text or None


def digits(text):
    return re.sub(r"\D", "", text or "")


def office_lines(items):
    """The digits of every number that belongs to an office rather than to one
    member: anything printed on two or more records, every member's Office
    line, and the county's main number."""
    seen = {}
    for item in items:
        for field in NUMBER_FIELDS:
            d = digits(clean(item.get(field)))
            if d:
                seen[d] = seen.get(d, 0) + 1
    shared = {d for d, n in seen.items() if n > 1}
    shared |= {digits(clean(item.get("Office"))) for item in items
               if clean(item.get("Office"))}
    shared.add(digits(COUNTY_MAIN_LINE))
    return shared


def member_numbers(item, shared):
    """-> (phone, phonesExtra): Office first, then Home, Work and Cell in the
    profile page's order, each led by the page's label. A member with no Office
    line leads with the first of the others."""
    numbers, taken = [], set()
    office = clean(item.get(FIRST_FIELD[0]))
    if office:
        numbers.append("%s %s" % (FIRST_FIELD[1], office))
        taken.add(digits(office))
    for field, label in EXTRA_FIELDS:
        value = clean(item.get(field))
        d = digits(value)
        if not d or d in taken:
            continue
        if d in shared and numbers:
            continue  # an office line, not this member's own
        numbers.append("%s %s" % (label, value))
        taken.add(d)
    return (numbers[0] if numbers else None), numbers[1:]


def fetch_items(retries=3, timeout=30):
    last_err = None
    for attempt in range(retries):
        try:
            require_robots_once(API_URL, HEADERS["User-Agent"], headers=HEADERS,
                                label="il-kane-county-board-scraper")
            resp = requests.get(API_URL, headers=HEADERS, timeout=timeout)
            if resp.status_code == 200:
                items = resp.json().get("value", [])
                if items:
                    return items
                last_err = "empty item list"
            else:
                last_err = "HTTP %d" % resp.status_code
        except (requests.RequestException, ValueError) as e:
            last_err = str(e)
        time.sleep(2 * (attempt + 1))
    raise RuntimeError("Failed to fetch %s: %s" % (API_URL, last_err))


def to_record(item, shared=frozenset()):
    raw_name = clean(item.get("FullName"))
    is_chair = bool(item.get("Chairman"))
    name = CHAIR_SUFFIX_RE.sub("", raw_name) if (raw_name and is_chair) else raw_name

    district = item.get("District")
    district = str(int(district)) if isinstance(district, (int, float)) else clean(district)

    phone, phones_extra = member_numbers(item, shared)

    email = clean(item.get("E_x002d_Mail"))
    if email and email.lower().startswith("mailto:"):
        email = email[len("mailto:"):].strip() or None

    list_id = item.get("ID")
    return {
        "id": list_id,
        "name": name,
        "district": district,
        "role": "Chair" if is_chair else None,
        "party": clean(item.get("Party")),
        "phone": phone,
        "phonesExtra": phones_extra,
        "email": email,
        "url": PROFILE_URL % list_id if isinstance(list_id, int) else None,
        "source_url": PROFILE_URL % list_id if isinstance(list_id, int) else LISTING_PAGE,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    ap = argparse.ArgumentParser(description="Scrape the Kane County Board SharePoint list.")
    ap.add_argument("out", nargs="?", default=None, help="output JSON path (default: stdout)")
    args = ap.parse_args()

    items = fetch_items()
    shared = office_lines(items)
    records = [to_record(i, shared) for i in items]

    payload = json.dumps(records, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w") as f:
            f.write(payload + "\n")
    else:
        print(payload)

    fields = ("district", "party", "phone", "phonesExtra", "email")
    coverage = "  ".join("%s=%d/%d" % (f, sum(1 for r in records if r.get(f)), len(records))
                         for f in fields)
    chairs = sum(1 for r in records if r.get("role") == "Chair")
    print("Scraped %d members (%d chair record)" % (len(records), chairs), file=sys.stderr)
    print("field coverage: %s" % coverage, file=sys.stderr)


if __name__ == "__main__":
    main()
