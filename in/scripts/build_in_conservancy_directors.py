#!/usr/bin/env python3
"""
Build in/data/app/in-conservancy-directors.json: the boards of Indiana's
conservancy districts, from the Department of Natural Resources' Indiana
Conservancy District Directory.

    python3 in/scripts/build_in_conservancy_directors.py              # fetch, check, write
    python3 in/scripts/build_in_conservancy_directors.py --source F   # parse a saved copy
    python3 in/scripts/build_in_conservancy_directors.py --check      # offline

THE SOURCE. One page on www.in.gov, rebuilt by the department each year: the
Indiana Conservancy District Act requires each board's chair to tell the
department the names and addresses of the district's officers and directors
when they change (IC 14-33-5-17), and "the DNR publishes a directory every
year" (the department's conservancy district page, read 2026-10-16). The copy
read on 2026-10-16 carries a modified date of 1 May 2026 and 100 districts,
each with its id, purposes, annual meeting and the people its board reported.

WHAT IS CARRIED: each person's name and role, the telephone numbers and the
e-mail address the directory prints beside that one person, the district's
own telephone and e-mail, its annual meeting and, where the directory gives
one, its website. The directory lists a person's own telephone and e-mail in
a short list under their name, and the district's in the entry's opening
lines; for many districts that contact is a director's own telephone or
e-mail. Adam's two rulings of 2026-10-17, for every state, settle both: a
number or e-mail address a government source prints beside one official is
published whatever kind of line or mailbox it is, and one printed for two or
more people, or equal to the district's own, is the district's. So a value
the directory prints beside two or more different people anywhere in it is
shown on none of them (SHARED), and one equal to the district's own telephone
or e-mail is shown as the district's and not on the person. WHAT IS NOT: any
address (the directory gives every person's home town and ZIP code and many
districts a home address as the mailing address, and nothing here can tell a
district office from a home), a fax number, a contact on a line that names
two people, a contact line the directory gives on its own with no name
(CONTACT-only lines), an e-mail address the page misprints (it is never
corrected), one on scripts/undeliverable.py's list, and a number whose tel:
link dials a different number than the one printed. A board member's "Area"
or "District" number is dropped too, because no map of those areas is
published.

WHO IS SHOWN. The board of directors is elected by the property owners in the
district, and "the board may appoint ... a secretary ... a financial clerk ...
an engineer [and] employees" (IC 14-33-5-18, as the State Board of Accounts'
manual for conservancy districts quotes it). Directors, the board's officers
(chair, vice chair, president, secretary, treasurer, financial clerk and the
like) and the contracting officer are shown with their roles as the directory
gives them; staff a district hires (its attorney, engineer, managers,
operators and office staff) are not. ROLES lists every role the directory
uses and what the card shows for it, and a role it does not list stops the
build. A role the directory pairs with an officer's ("Secretary/Attorney")
is shown, because the person holds the office.

THE DIRECTORY'S IDS DO NOT ALL MATCH THE MAP'S, AND THE TABLE SAYS WHICH.
Each entry carries a "Conservancy District ID", the same numbering the
department's map uses (in/scripts/build_in_conservancy_districts.py), but four
entries carry another district's id: three repeat an id another entry also
carries, and one carries an id the map gives no active district.
DIRECTORY_ID_FIXES lists each with the id the map gives the district of that
name, and the build stops on an entry the table no longer matches. Every
joined pair is then held to two tests: the names must agree (NAME_RATIO,
which the three wrong ids the map draws fail and every right pair passes) and
the directory's counties must include the county the map draws most of the
district in or the court county the map gives. The one district whose court
county the map gives wrongly (Nature Works, filed under Noble, drawn in
Porter) carries no court in the map file (build_in_conservancy_districts.py,
COURT_NOT_SHOWN), and the directory's Porter matches where it is drawn.
Neither test can catch a swap between two neighbouring districts whose names
differ by one word, such as Northeast Lake and Northwest Lake in Johnson
County.

A DISTRICT THE MAP DRAWS AND THE DIRECTORY LEAVES OUT says so on its card
rather than naming anyone (NOT_IN_DIRECTORY), and so does one that sent the
department no list. An entry the map does not draw is reported and left out
(NOT_DRAWN). The page also lists the people in a few entries in a shape the
parser cannot read alone (a typo splitting a role, two people in one line, a
role written outside its bold label); ENTRY_FIXES lists each exactly as
published with what it says, and stops the build once the page changes it.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
in-conservancy-district-records): the directory mixes district contacts with
directors' home addresses and personal telephones; four entries carry the
wrong district id; one district on the map is missing from it; and it is a
web page of free text rather than a table, so every role is spelled however
the district sent it (50 spellings, measured 2026-10-16).
"""

import argparse
import collections
import datetime
import difflib
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(os.path.dirname(INSTANCE), "scripts"))

from scraper_common import require_robots_once  # noqa: E402
import undeliverable  # noqa: E402  (the fleet's withhold list)

DIRECTORY = "https://www.in.gov/dnr/water/publications/indiana-conservancy-district-directory"
USER_AGENT = "districtry/1.0 (+https://districtry.com/in/)"
HEADERS = {"User-Agent": USER_AGENT, "Accept": "text/html", "Accept-Encoding": "identity"}
MAP_FILE = os.path.join(INSTANCE, "data", "app", "in-conservancy-districts.json")
COUNTIES_FILE = os.path.join(INSTANCE, "data", "app", "state-counties.json")
OUT = os.path.join(INSTANCE, "data", "app", "in-conservancy-directors.json")
LABEL = "build-in-conservancy-directors"

# Floors, measured 2026-10-16: 100 entries, 99 joined to a drawn district, 543
# people listed of whom 470 hold a role shown here.
MIN_ENTRIES = 95
MIN_DISTRICTS = 95
MIN_PEOPLE = 420
# Contact floors, about two thirds of the counts measured on the copy read
# 2026-10-17 (MEASURED_CONTACTS), so a change to the page that stops these
# being read fails the build instead of emptying them quietly.
MEASURED_CONTACTS = {"person_phones": 145, "person_emails": 181,
                     "district_phones": 86, "district_emails": 83}
MIN_PERSON_PHONES = 97
MIN_PERSON_EMAILS = 121
MIN_DISTRICT_PHONES = 57
MIN_DISTRICT_EMAILS = 55

# role as the directory writes it (whitespace collapsed, trailing dashes
# dropped) -> what the card shows, or None for staff a district hires.
ROLES = {
    "Chair": "Chair",
    "Chair & Secretary": "Chair and Secretary",
    "Vice Chair": "Vice Chair",
    "Vice-Chair": "Vice Chair",
    "Vice - Chair": "Vice Chair",
    "Vice Chair/Director": "Vice Chair",
    "Vice Chair/Secretary": "Vice Chair and Secretary",
    "President": "President",
    "Vice President": "Vice President",
    "Board Member": "Board Member",
    "Director": "Director",
    "Secretary": "Secretary",
    "Treasurer": "Treasurer",
    "Assistant Treasurer": "Assistant Treasurer",
    "Treasurer/Director": "Treasurer",
    "Financial Clerk": "Financial Clerk",
    "Financial Cleark": "Financial Clerk",
    "Fiscal Clerk": "Fiscal Clerk",
    "Clerk": "Clerk",
    "Financial Secretary": "Financial Secretary",
    "Financial Clerk/Director": "Financial Clerk",
    "Financial Clerk/Secretary": "Financial Clerk and Secretary",
    "Secretary/Financial Clerk": "Secretary and Financial Clerk",
    "Secretary & Financial Clerk": "Secretary and Financial Clerk",
    "Secretary/Treasurer": "Secretary and Treasurer",
    "Secretary/Finance": "Secretary and Finance",
    "Recorder/Financial Clerk": "Recorder and Financial Clerk",
    "Secretary/Attorney": "Secretary and Attorney",
    "Attorney & Financial Clerk": "Financial Clerk and Attorney",
    "Finance President": "Finance President",
    "Fiscal Director": "Fiscal Director",
    "Contract Officer": "Contracting Officer",
    "Contracting Officer": "Contracting Officer",
    # staff a district hires
    "Attorney": None,
    "Engineer": None,
    "Superintendent": None,
    "Operations Manager": None,
    "District Manager": None,
    "General Manager": None,
    "Manager": None,
    "Utility Manager": None,
    "Plant Manager": None,
    "Office Manager": None,
    "Office Coordinator": None,
    "Admin Secretary": None,
    "Admin & Financial Manager": None,
    "Accountant": None,
    "Maintenance Supervisor": None,
    "Operator": None,
    "Water Operator": None,
}

# (directory name, id the directory gives) -> the id the map gives that
# district. Measured 2026-10-16 against the map's names, courts and drawings.
DIRECTORY_ID_FIXES = {
    ("Je-To Lake Conservancy District", "141"): "131",       # 141 is James Phillips
    ("Thirty Nine North Conservancy District", "64"): "94",  # 64 is no active district
    ("White Lake Conservancy District", "97"): "77",         # 97 is Simonton Lake
    ("West Vigo Levee Association Conservancy District", "84"): "133",  # 84 is West Central
}

# The directory's name and the map's must agree this closely once the words
# many names share are taken out (difflib's ratio, 0 to 1, in the words' own
# order or sorted, whichever is higher). Measured 2026-10-16: the three wrong
# ids above that the map draws score 0.31 to 0.48 against the district the map
# gives that id, and every right pair scores 0.69 or more (Battleground-
# Brookston against Battle Ground the lowest). The test cannot tell two
# districts whose names differ by one word apart: Northeast Lake against
# Northwest Lake scores 0.89. A pair of right names scoring under the line
# goes in ACCEPTED_NAME_PAIRS, id -> (directory name, why), which is empty.
NAME_RATIO = 0.6
ACCEPTED_NAME_PAIRS = {}

# id -> why the map's district is not in the directory
NOT_IN_DIRECTORY = {
    "142": "Geist Reservoir: not in the copy of the directory modified 2026-05-01",
}

# id -> why the directory's entry is not drawn
NOT_DRAWN = {
    "140": "Hidden Hills: the map's record for it carries no status, so the map "
           "does not draw it as active; the directory lists it with no officers",
}

# (district id, the line exactly as the page gives it once tags are taken out
# and spaces collapsed) -> the people it names, as (role as written, name).
ENTRY_FIXES = {
    ("73", "Board Membe r – Pat Conners – Mooresville, IN 46158"):
        (("Board Member", "Pat Conners"),),
    ("23", "Attorney & Financial Clerk – Dustin Howard– Salem, IN 47167"):
        (("Attorney & Financial Clerk", "Dustin Howard"),),
    ("59", "Vice Chairs – Michael Davis & Chandlor Weiss-Brinkman – Kentland, IN 47951"):
        (("Vice Chair", "Michael Davis"), ("Vice Chair", "Chandlor Weiss-Brinkman")),
    ("44", "Secretary/Financial Clerk/CONTACT – Charles Little – Ambia, IN 47917"):
        (("Secretary/Financial Clerk", "Charles Little"),),
}

NO_LIST = re.compile(r"^The district did not submit a list of officers in (\d{4})\.$")
SEPARATOR = re.compile(r"\s*–\s*|\s+-\s+|(?<=[a-z])-\s+")
AREA = re.compile(r"^(?:Area|District)\s+\d+$")
TOWN = re.compile(r"^[A-Z][A-Za-z.' ]*,?\s+(?:IN|[A-Z]{2}|Indiana)\.?(?:\s+\d{4,5}(?:-\d{4})?)?$")
NAME_TOWN = re.compile(r"^(.*?),\s*([A-Z][A-Za-z.' ]*,?\s+(?:IN|[A-Z]{2})\s+\d{4,5})$")
NAME = re.compile(r"^[A-Z][A-Za-z.'’ -]*[A-Za-z.]$")
CONTACT = re.compile(r"^(?:[\w.+-]+@[\w-]+(?:\.[\w-]+)+|\(?\d{3}\)?[-. ]\d{3}-\d{4})$")
# One e-mail address and nothing else. An address the page misprints (a stray
# character in it) does not match and is left out, never corrected.
EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
# One whole telephone number, with an extension where the page gives one. The
# spaces some entries put beside a hyphen are taken out; the digits never
# change.
PHONE = re.compile(r"^(?:1-)?\(?\d{3}\)?[-. ]?\d{3}-\d{4}(?: (?:Ext\.?|ext\.?|x) ?\d{1,5})?$")
FAX = re.compile(r"^fax\b", re.I)
VACANT = "Vacant"
GENERIC = set("conservancy district cd the of and assoc association sewer area "
              "watershed levee ditch lake lakes creek river".split())


def fail(msg):
    print("%s: FAIL: %s" % (LABEL, msg))
    raise SystemExit(1)


def text(fragment):
    fragment = re.sub(r"<sup>(.*?)</sup>", r"\1", fragment, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment))
    return re.sub(r"[\s\xa0]+", " ", t).strip()


def fetch():
    verdict = require_robots_once(DIRECTORY, USER_AGENT, headers=HEADERS, label=LABEL)
    print("robots: %s" % verdict)
    req = urllib.request.Request(DIRECTORY, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        if resp.status != 200:
            fail("the directory answered HTTP %d" % resp.status)
        return resp.read().decode("utf-8", errors="replace")


def fields(paragraph):
    """The entry's opening paragraph, as label -> (text, the first link in it).
    Each value runs from its bold label to the next, because the page does not
    always put a line break between two fields."""
    parts = re.split(r"<strong>(.*?)</strong>", paragraph, flags=re.S)
    out = {}
    for i in range(1, len(parts) - 1, 2):
        label = text(parts[i]).rstrip(":").strip()
        if not label:
            continue
        link = re.search(r'<a href="([^"]+)"', parts[i + 1])
        out[label] = (text(parts[i + 1]).lstrip(":").strip(),
                      link.group(1) if link else None)
    return out


def top_items(body):
    """The entry's list items as (item, nested): the item with any nested list
    taken out, and that nested list's own markup (the person's own telephone
    and e-mail), or "" where the item has none."""
    start = body.find("<ul>")
    if start < 0:
        return []
    depth, items = 0, []
    for tok in re.split(r"(<ul>|</ul>)", body[start:]):
        if tok == "<ul>":
            depth += 1
            if depth >= 2 and items:
                items[-1][1].append(tok)
        elif tok == "</ul>":
            depth -= 1
            if depth == 0:
                break
            if items:
                items[-1][1].append(tok)
        elif depth == 1:
            parts = tok.split("<li>")
            if items:
                items[-1][0].append(parts[0])
            for part in parts[1:]:
                items.append(([part], []))
        elif items:
            items[-1][1].append(tok)
    out = []
    for li, nested in items:
        li = "".join(li)
        if text(li):
            out.append((li, "".join(nested)))
    return out


def tel_digits(fragment):
    """The ten digits each tel: link in a fragment dials, a leading 1 dropped."""
    out = set()
    for href in re.findall(r'href="tel:([^"]*)"', fragment):
        digits = re.sub(r"\D", "", urllib.parse.unquote(html.unescape(href)))
        out.add(digits[1:] if len(digits) == 11 and digits.startswith("1") else digits)
    return out


def phone_digits(phone):
    """The ten digits a printed number dials, before any extension."""
    base = re.split(r"(?i)\s(?:ext|x)", phone)[0]
    digits = re.sub(r"\D", "", base)
    return digits[1:] if len(digits) == 11 and digits.startswith("1") else digits


def contacts(nested, notes):
    """The telephone numbers and e-mail addresses one person's nested list
    prints, as {"phones": [...], "emails": [...]}. Each list item is split at
    "|"; a fax number, a misprinted address and anything that is neither is
    left out and counted in NOTES, never printed."""
    phones, emails = [], []
    for item in re.findall(r"<li>(.*?)(?=<li>|</ul>|$)", nested, re.S):
        dialled = tel_digits(item)
        for part in text(item).split("|"):
            part = part.strip()
            if not part:
                continue
            if FAX.match(part):
                notes["fax"] += 1
                continue
            if "@" in part:
                if EMAIL.match(part):
                    emails.append(part)
                else:
                    notes["misprinted e-mail"] += 1
                continue
            phone = re.sub(r"\s*-\s*", "-", part)
            if not PHONE.match(phone):
                notes["not a whole telephone number"] += 1
                continue
            if dialled and phone_digits(phone) not in dialled:
                notes["tel: link dials another number"] += 1
                continue
            phones.append(phone)
    return {"phones": phones, "emails": emails}


def district_contact(info, notes):
    """The district's own telephone and e-mail from the entry's opening lines,
    or None for each the directory does not give in a whole, usable form."""
    phone = email = None
    raw = (info.get("Phone") or ("", None))[0]
    if raw:
        cand = re.sub(r"\s*-\s*", "-", raw.lstrip(":").strip())
        cand = re.sub(r"(?i)\s+ext\.?\s*", " Ext. ", cand)
        if PHONE.match(cand):
            phone = cand
        else:
            notes["district telephone not a whole number"] += 1
    raw = (info.get("Email") or ("", None))[0]
    if raw:
        cand = raw.lstrip(":").strip()
        if EMAIL.match(cand):
            email = cand
        else:
            notes["district e-mail misprinted"] += 1
    return phone, email


def person(key, li, used):
    """(role as written, name) pairs from one list item, or [] for a line that
    only repeats a contact."""
    whole = text(li)
    fix = ENTRY_FIXES.get((key, whole))
    if fix is not None:
        used.add((key, whole))
        return list(fix)
    m = re.match(r"\s*<strong>(.*?)</strong>(.*)$", li, re.S)
    if not m:
        if CONTACT.match(whole):
            return []
        fail("district %s lists %r, which is not a role and a name" % (key, whole))
    role = re.sub(r"[\s–-]+$", "", text(m.group(1)))
    rest = text(m.group(2))
    parts = []
    for part in SEPARATOR.split(rest):
        part = part.strip(" -–")
        if not part:
            continue
        nm = NAME_TOWN.match(part)
        if nm:
            parts.extend([nm.group(1), nm.group(2)])
        else:
            parts.append(part)
    names = [p for p in parts if not AREA.match(p) and not TOWN.match(p)]
    if len(names) != 1:
        fail("district %s lists %r: cannot tell the name from %r" % (key, whole, names))
    return [(role, names[0])]


def parse(page):
    stamp = re.search(r'<meta name="dcterms.modified" content="(\d{4}-\d{2}-\d{2})', page)
    if not stamp:
        fail("the directory no longer carries its modified date")
    modified = stamp.group(1)
    years = set()
    entries, used, contact_lines = [], set(), 0
    notes = collections.Counter()
    for item in re.split(r'<div class="accordion-item">', page)[1:]:
        head = re.search(r'aria-controls="[^"]*">\s*(.*?)\s*</button>', item, re.S)
        body = re.search(r'<div class="accordion-body"[^>]*>(.*?)</div>\s*</div>\s*</div>',
                         item, re.S)
        if not head or not body:
            fail("an entry no longer has the shape the parser reads: %r" % text(item[:300]))
        name, body = text(head.group(1)), body.group(1)
        para = re.search(r"<p>(.*?)</p>", body, re.S)
        info = fields(para.group(1)) if para else {}
        raw_id = (info.get("Conservancy District ID") or ("", None))[0]
        if not re.fullmatch(r"\d+", raw_id):
            fail("%s carries no district id: %r" % (name, raw_id))
        key = DIRECTORY_ID_FIXES.get((name, raw_id), raw_id)
        entry = {"name": name, "key": key, "raw_id": raw_id, "people": []}
        if "County" in info:
            entry["counties"] = [c.strip() for c in re.split(r",|/|\band\b|&", info["County"][0])
                                 if c.strip()]
        if "Annual Meeting" in info and info["Annual Meeting"][0]:
            entry["meeting"] = info["Annual Meeting"][0]
        if "Website" in info and info["Website"][1]:
            entry["url"] = info["Website"][1]
        entry["phone"], entry["email"] = district_contact(info, notes)
        for li, nested in top_items(body):
            said = NO_LIST.match(text(li))
            if said:
                years.add(said.group(1))
                entry["noList"] = True
                continue
            got = person(key, li, used)
            if not got:
                contact_lines += 1
            found = contacts(nested, notes) if nested else {"phones": [], "emails": []}
            if len(got) > 1 and (found["phones"] or found["emails"]):
                # one contact line under two names: whose it is cannot be told
                notes["contact under a line naming two people"] += 1
                found = {"phones": [], "emails": []}
            entry["people"].extend((role, name, found) for role, name in got)
        rest = text(re.sub(r"<p>.*?</p>", " ", body, count=1, flags=re.S))
        nolist = NO_LIST.search(rest)
        if nolist:
            years.add(nolist.group(1))
            entry["noList"] = True
        if not entry["people"] and not entry.get("noList"):
            fail("%s lists nobody and does not say it sent no list" % name)
        entries.append(entry)
    for fix in ENTRY_FIXES:
        if fix not in used:
            fail("ENTRY_FIXES names %r, which the directory no longer lists; read it again"
                 % (fix,))
    if len(years) != 1:
        fail("the directory's no-list sentences name the years %s, not one" % sorted(years))
    edition = years.pop()
    if edition != modified[:4]:
        fail("the directory's no-list year %s differs from its modified date %s"
             % (edition, modified))
    print("directory: %d entries, modified %s, %d contact-only lines left out"
          % (len(entries), modified, contact_lines))
    for why, n in sorted(notes.items()):
        print("  left out: %d %s" % (n, why))
    return entries, edition, modified


def tokens(name):
    n = re.sub(r"[^a-z0-9 ]", " ", name.lower().replace("&", " and "))
    return " ".join(t for t in n.split() if t not in GENERIC)


def name_ratio(a, b):
    ta, tb = tokens(a), tokens(b)
    return max(difflib.SequenceMatcher(None, ta, tb).ratio(),
               difflib.SequenceMatcher(None, " ".join(sorted(ta.split())),
                                       " ".join(sorted(tb.split()))).ratio())


def drawn_districts():
    with open(MAP_FILE, encoding="utf-8") as fh:
        return {f["properties"]["key"]: f for f in json.load(fh)["features"]}


def county_of_most_land(feature, counties):
    """The county holding most of the district's drawn vertices: a stand-in
    for where most of its land lies, good enough to catch a wrong join."""
    from build_in_conservancy_districts import in_geometry, ring_points  # noqa: E402
    best, best_n = None, 0
    pts = list(ring_points(feature["geometry"]))
    for name, geom in counties.items():
        n = sum(1 for x, y in pts if in_geometry(x, y, geom))
        if n > best_n:
            best, best_n = name, n
    return best


def phone_key(phone):
    """A printed number as every digit it carries, extension included, so two
    people on one main line with their own extensions are told apart."""
    digits = re.sub(r"\D", "", phone)
    return digits[1:] if phone.startswith("1-") else digits


def shared_values(entries):
    """Each telephone and e-mail the directory prints beside two or more
    different people, anywhere in it: the office's, not any one person's."""
    seen = collections.defaultdict(set)
    for e in entries:
        for _role, name, found in e["people"]:
            who = name.casefold()
            for phone in found["phones"]:
                seen[("phone", phone_key(phone))].add(who)
            for email in found["emails"]:
                seen[("email", email.casefold())].add(who)
    return {k for k, names in seen.items() if len(names) > 1}


def prefer_government(emails):
    """One address per person: a government domain where the person has two."""
    for email in emails:
        if re.search(r"\.(?:gov|in\.us)$", email.casefold()):
            return email
    return emails[0]


def join(entries, edition, modified):
    drawn = drawn_districts()
    shared = shared_values(entries)
    tally = collections.Counter()
    with open(COUNTIES_FILE, encoding="utf-8") as fh:
        counties = {f["properties"]["BASENAME"]: f["geometry"]
                    for f in json.load(fh)["features"]}
    for (name, raw_id), right in DIRECTORY_ID_FIXES.items():
        if not any(e["name"] == name and e["raw_id"] == raw_id for e in entries):
            fail("DIRECTORY_ID_FIXES names %s with id %s, which the directory no longer "
                 "lists; read it again" % (name, raw_id))
        if right not in drawn:
            fail("DIRECTORY_ID_FIXES sends %s to id %s, which the map does not draw"
                 % (name, right))
    by_key = {}
    for e in entries:
        if e["key"] in by_key:
            fail("two directory entries carry id %s: %s and %s; add the wrong one to "
                 "DIRECTORY_ID_FIXES" % (e["key"], by_key[e["key"]]["name"], e["name"]))
        by_key[e["key"]] = e
    for key in sorted(set(by_key) - set(drawn), key=int):
        if key not in NOT_DRAWN:
            fail("the directory lists %s (id %s), which the map does not draw; add it to "
                 "NOT_DRAWN with the reason, or DIRECTORY_ID_FIXES if its id is wrong"
                 % (by_key[key]["name"], key))
        print("  not drawn: %s (id %s): %s" % (by_key[key]["name"], key, NOT_DRAWN[key]))
    for key in NOT_DRAWN:
        if key not in by_key or key in drawn:
            fail("NOT_DRAWN names id %s, which no longer describes the two sources" % key)
    for key in sorted(set(drawn) - set(by_key), key=int):
        if key not in NOT_IN_DIRECTORY:
            fail("the map draws %s (id %s), which the directory does not list; add it "
                 "to NOT_IN_DIRECTORY with the reason"
                 % (drawn[key]["properties"]["label"], key))
        print("  not in the directory: %s" % NOT_IN_DIRECTORY[key])
    for key in NOT_IN_DIRECTORY:
        if key in by_key or key not in drawn:
            fail("NOT_IN_DIRECTORY names id %s, which no longer describes the two sources"
                 % key)
    out, shown, hidden = {}, 0, 0
    for key, e in sorted(by_key.items(), key=lambda kv: int(kv[0])):
        if key not in drawn:
            continue
        p = drawn[key]["properties"]
        ratio = name_ratio(p["label"], e["name"])
        accepted = ACCEPTED_NAME_PAIRS.get(key)
        if accepted is not None:
            if accepted[0] != e["name"]:
                fail("ACCEPTED_NAME_PAIRS holds %r for id %s, but the directory now says %r"
                     % (accepted[0], key, e["name"]))
        elif ratio < NAME_RATIO:
            fail("id %s is %r on the map and %r in the directory (%.2f): a wrong id, or a "
                 "spelling for ACCEPTED_NAME_PAIRS" % (key, p["label"], e["name"], ratio))
        if "counties" in e:
            places = {c.lower() for c in e["counties"]}
            mapped = {(p.get("court") or "").lower(),
                      (county_of_most_land(drawn[key], counties) or "").lower()}
            if not places & mapped:
                fail("id %s (%s): the directory's counties %s include neither the map's "
                     "court nor the county most of it is drawn in (%s)"
                     % (key, e["name"], e["counties"], sorted(mapped)))
        own_phone = phone_key(e["phone"]) if e.get("phone") else None
        own_email = e["email"].casefold() if e.get("email") else None
        people = []
        for role, name, found in e["people"]:
            if role not in ROLES:
                fail("district %s lists the role %r, which ROLES does not cover; say what "
                     "the card shows for it, or None for hired staff" % (key, role))
            if ROLES[role] is None:
                hidden += 1
                continue
            if name == VACANT:
                people.append({"role": ROLES[role], "vacant": True})
                shown += 1
                continue
            if not NAME.match(name) or re.search(r"\d|@", name):
                fail("district %s lists %r as a name" % (key, name))
            rec_p = {"role": ROLES[role], "name": name}
            phones = []
            for phone in found["phones"]:
                k = phone_key(phone)
                if ("phone", k) in shared:
                    tally["telephone printed for two or more people"] += 1
                elif k == own_phone:
                    tally["telephone equal to the district's own"] += 1
                elif phone not in phones:
                    phones.append(phone)
            emails = []
            for email in found["emails"]:
                k = email.casefold()
                if ("email", k) in shared:
                    tally["e-mail printed for two or more people"] += 1
                elif k == own_email:
                    tally["e-mail equal to the district's own"] += 1
                elif undeliverable.UNDELIVERABLE.get(k) is not None:
                    tally["e-mail on the undeliverable list"] += 1
                elif email not in emails:
                    emails.append(email)
            if phones:
                rec_p["phone"] = phones[0]
                if len(phones) > 1:
                    rec_p["phonesExtra"] = phones[1:]
            if emails:
                rec_p["email"] = prefer_government(emails)
            people.append(rec_p)
            shown += 1
        rec = {"edition": edition, "modified": modified, "name": e["name"],
               "sourceUrl": DIRECTORY}
        if e.get("phone"):
            rec["phone"] = e["phone"]
        if e.get("email"):
            if undeliverable.UNDELIVERABLE.get(e["email"].casefold()) is not None:
                tally["district e-mail on the undeliverable list"] += 1
            else:
                rec["email"] = e["email"]
        if e.get("noList"):
            if people:
                fail("district %s says it sent no list and names people" % key)
            rec["noList"] = True
        else:
            rec["people"] = people
        if e.get("meeting"):
            rec["meeting"] = e["meeting"]
        if e.get("url"):
            rec["url"] = e["url"]
        out[key] = rec
    for key in ACCEPTED_NAME_PAIRS:
        if key not in out:
            fail("ACCEPTED_NAME_PAIRS names id %s, which is no longer joined" % key)
    print("joined %d districts: %d people shown, %d hired staff left out"
          % (len(out), shown, hidden))
    for why, n in sorted(tally.items()):
        print("  not shown on a person: %d %s" % (n, why))
    return out


def contact_problems(where, rec):
    """A record's telephone and e-mail held to one number or one address each.
    WHERE names the district and person; a value is never printed."""
    problems = []
    for phone in [rec.get("phone")] + list(rec.get("phonesExtra") or []):
        if phone is not None and not PHONE.match(str(phone)):
            problems.append("%s carries a telephone that is not one whole number" % where)
    if rec.get("phonesExtra") is not None and not rec.get("phone"):
        problems.append("%s carries further numbers and no first one" % where)
    email = rec.get("email")
    if email is not None and not EMAIL.match(str(email)):
        problems.append("%s carries an e-mail that is not one address" % where)
    return problems


def check(data):
    """Offline: hold the shipped file to the shipped map and to its own rules."""
    drawn = drawn_districts()
    problems = []
    shown_roles = {v for v in ROLES.values() if v}
    people = 0
    counts = collections.Counter()
    holders = collections.defaultdict(set)
    for key, rec in data.items():
        problems.extend(contact_problems("id %s" % key, rec))
        counts["district_phones"] += 1 if rec.get("phone") else 0
        counts["district_emails"] += 1 if rec.get("email") else 0
        if key not in drawn:
            problems.append("id %s is not a district the map draws" % key)
        if rec.get("sourceUrl") != DIRECTORY:
            problems.append("id %s does not cite the directory" % key)
        if not re.fullmatch(r"\d{4}", str(rec.get("edition", ""))):
            problems.append("id %s carries no edition year" % key)
        if rec.get("noList"):
            if rec.get("people"):
                problems.append("id %s says it sent no list and names people" % key)
            continue
        for person in rec.get("people") or []:
            if person.get("role") not in shown_roles:
                problems.append("id %s shows the role %r" % (key, person.get("role")))
            if person.get("vacant"):
                if any(person.get(f) for f in ("phone", "phonesExtra", "email")):
                    problems.append("id %s gives a vacant seat a contact" % key)
                continue
            name = person.get("name") or ""
            if not NAME.match(name) or re.search(r"\d|@|,", name):
                problems.append("id %s carries %r as a name" % (key, name))
            people += 1
            where = "id %s, %s" % (key, person.get("role"))
            problems.extend(contact_problems(where, person))
            mine = [phone_key(p) for p in [person.get("phone")] + list(person.get("phonesExtra") or []) if p]
            if rec.get("phone") and phone_key(rec["phone"]) in mine:
                problems.append("%s carries the district's own telephone" % where)
            if rec.get("email") and person.get("email") and \
                    rec["email"].casefold() == person["email"].casefold():
                problems.append("%s carries the district's own e-mail" % where)
            for k in mine:
                holders[("phone", k)].add(name.casefold())
            if person.get("email"):
                holders[("email", person["email"].casefold())].add(name.casefold())
            counts["person_phones"] += 1 if person.get("phone") else 0
            counts["person_emails"] += 1 if person.get("email") else 0
        if not rec.get("people"):
            problems.append("id %s names nobody and does not say it sent no list" % key)
        url = rec.get("url")
        if url is not None and not re.match(r"^https?://", url):
            problems.append("id %s's website %r is not an address" % (key, url))
    missing = sorted(set(drawn) - set(data) - set(NOT_IN_DIRECTORY), key=int)
    if missing:
        problems.append("the map draws ids %s, which the file neither carries nor records "
                        "as missing from the directory" % ", ".join(missing))
    if len(data) < MIN_DISTRICTS:
        problems.append("%d districts, below the floor of %d" % (len(data), MIN_DISTRICTS))
    if people < MIN_PEOPLE:
        problems.append("%d people named, below the floor of %d" % (people, MIN_PEOPLE))
    shared = sum(1 for names in holders.values() if len(names) > 1)
    if shared:
        problems.append("%d telephone or e-mail value(s) are shown on two or more people"
                        % shared)
    for field, floor in (("person_phones", MIN_PERSON_PHONES),
                         ("person_emails", MIN_PERSON_EMAILS),
                         ("district_phones", MIN_DISTRICT_PHONES),
                         ("district_emails", MIN_DISTRICT_EMAILS)):
        if counts[field] < floor:
            problems.append("%d %s, below the floor of %d (measured %d)"
                            % (counts[field], field.replace("_", " "), floor,
                               MEASURED_CONTACTS[field]))
    return problems, people, counts


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped file to the shipped map")
    ap.add_argument("--source", help="parse a saved copy of the directory page")
    args = ap.parse_args()
    if args.check:
        with open(OUT, encoding="utf-8") as fh:
            problems, people, counts = check(json.load(fh))
        if problems:
            for p in problems:
                print("%s: FAIL: %s" % (LABEL, p))
            raise SystemExit(1)
        print("%s --check: OK — %d people named across the map's conservancy districts; "
              "%d with a telephone and %d with an e-mail of their own; %d districts with "
              "a telephone and %d with an e-mail" % (
                  LABEL, people, counts["person_phones"], counts["person_emails"],
                  counts["district_phones"], counts["district_emails"]))
        return
    if args.source:
        with open(args.source, encoding="utf-8", errors="replace") as fh:
            page = fh.read()
    else:
        page = fetch()
    entries, edition, modified = parse(page)
    if len(entries) < MIN_ENTRIES:
        fail("%d entries, below the floor of %d" % (len(entries), MIN_ENTRIES))
    data = join(entries, edition, modified)
    problems, people, counts = check(data)
    if problems:
        for p in problems:
            print("%s: FAIL: %s" % (LABEL, p))
        raise SystemExit(1)
    print("contacts: %d people with a telephone, %d with two or more, %d with an e-mail; "
          "%d districts with a telephone, %d with an e-mail" % (
              counts["person_phones"],
              sum(1 for r in data.values() for x in r.get("people") or [] if x.get("phonesExtra")),
              counts["person_emails"], counts["district_phones"], counts["district_emails"]))
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    print("wrote %s: %d districts, %d people named (read %s)"
          % (os.path.relpath(OUT, os.path.dirname(INSTANCE)), len(data), people,
             datetime.date.today().isoformat()))


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    main()
