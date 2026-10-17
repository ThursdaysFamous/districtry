"""Door County: the county clerk's Official Directory 2026-2027 (PDF; the
county's "Official County Directory" page at co.door.wi.gov/340 serves the PDF
itself).

"TOWN, VILLAGE AND CITY OFFICERS OF DOOR COUNTY" opens each town with its bare
name and "Terms Expire April 2027" on one line; villages and the city are
headed "Village of ..." and "City of ..." and are skipped. Each officer is two
lines: the name with a dotted leader to a telephone number, then the office
("Chairman", "Supervisor #1") with a leader to the home address; one entry
prints the name and the office on the same line. The telephone at the end of
the name line ships on the officer; an address after the office is not read.
A note such as "(Term expires April 2028)" after a name is dropped. Read with
the token on 2026-10-15 (robots.txt: 816 bytes, no rule matches the page's
path)."""

import re

from . import clean, looks_like_person, norm_role, person, phones_after_name

COUNTY_FIPS = "029"
COUNTY_NAME = "Door"
SOURCES = ["https://co.door.wi.gov/340/Official-County-Directory"]

_HEAD = re.compile(r"^([A-Z][A-Za-z .']+?)\s*[.… ]*\s*Terms Expire\b(.*)$")


def _lead(line):
    """The text before a dotted leader or an opening bracket."""
    return clean(re.split(r"\(|[.…]{3,}", line)[0])


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = text.find("TOWN, VILLAGE AND CITY OFFICERS")
    if start < 0:
        raise RuntimeError("the town, village and city officers section was not found")
    lines = [ln.strip() for ln in text[start:].split("\n") if ln.strip()]
    towns, town, prev, prev_line = {}, None, None, None
    for ln in lines:
        m = _HEAD.match(ln)
        if m:
            name = clean(m.group(1))
            if re.match(r"^(Village|City) of\b", name):
                if town is not None and name.startswith("City"):
                    break           # the city is the last entry
                town = None
            else:
                town = name
            prev = prev_line = None
            continue
        if re.fullmatch(r"\d{1,3}", ln):
            continue                # a page number between a name and its office
        lead = _lead(ln)
        role = norm_role(lead) if re.match(r"^(Chair|Supervisor)", ln, re.I) else None
        if town and role and prev and looks_like_person(prev):
            towns.setdefault(town, []).append(
                person(prev, role, phones_after_name(prev_line, prev)))
        elif town and not role:
            # the name and the office on one line ("Steven Sullivan Chairman")
            both = re.match(r"^(.+?)\s+((?:Chair\w*|Supervisor)\b.*)$", lead)
            if both and norm_role(both.group(2)) and looks_like_person(both.group(1)):
                # the leader after the office runs to the telephone
                towns.setdefault(town, []).append(
                    person(both.group(1), norm_role(both.group(2)),
                           phones_after_name(ln, both.group(1))))
                lead = None
        prev, prev_line = lead, ln
    m = re.search(r"OFFICIAL\s*\nDIRECTORY\s*\n(\d{4})\s*-\s*(\d{4})", text)
    edition = ("%s-%s" % m.groups()) if m else None
    return {"towns": towns, "edition": edition}
