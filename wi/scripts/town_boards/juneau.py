"""Juneau County: the county clerk's Master Directory 2026-2027 (PDF).

Each town has a page headed "TOWN OF <NAME>". An office is printed as a
heading on its own line ("Chairperson", "Supervisors", "Clerk/Treasurer"),
followed by each holder's name with a dot leader and telephone, then the
holder's street address, town and e-mail on the lines below. The telephone
after the leader ships on the officer, and so does the e-mail address on the
entry's last line; the address lines are not read. A
heading can cover two names ("Supervisors"). Read with the token on 2026-10-15 (the file
is served from cms2.revize.com, whose robots.txt allows /*.pdf; the county
host has no robots.txt)."""

import re

from . import (add_emails, line_emails, looks_like_person, norm_role, person,
               phones_after_name, split_blocks, strip_contact)

COUNTY_FIPS = "057"
COUNTY_NAME = "Juneau"
SOURCES = ["https://www.co.juneau.wi.gov/Department/County%20Clerk/"
           "Master%20Directory%202026-2027%20Digital%203.pdf"]

_HEADING = re.compile(r"^(Chair\w*|Vice\s+Chair\w*|Supervisors?|Clerk\S*|"
                      r"Treasurer|Deputy\b.*|Assessor|Constable|Zoning\b.*|"
                      r"Trustee|Building\b.*|Patrol\w*|Road\b.*|Polling\b.*)"
                      r"\s*[:.]?\s*$", re.I)
_LEADER = re.compile(r"…|\.{3,}")
_CUT = re.compile(r"\s*(…|\.{2,}).*$")
_ADDRESS = re.compile(r"^([NWES]\d|\d|P\.?\s?O\.?\s+Box\b)|,\s*WI\b|@", re.I)


def _officers(block):
    people = []
    role = None
    after_heading = False
    last = None         # the board member whose entry the lines below are
    for ln in (x.strip() for x in block.split("\n")):
        if not ln or ln.startswith("=====") or re.fullmatch(r"\d+", ln):
            continue
        h = _HEADING.match(ln)
        if h:
            word = h.group(1)
            role = norm_role(re.sub(r"(?i)^supervisors$", "Supervisor", word))
            after_heading = True
            last = None
            continue
        if _LEADER.search(ln):
            name = strip_contact(_CUT.sub("", ln))
            last = None
            if role and looks_like_person(name):
                last = person(name, role, phones_after_name(ln, name))
                people.append(last)
            elif not looks_like_person(name):
                # a leader line that is a place ("Polling Place ......") ends
                # the office it follows
                role = None
            after_heading = False
            continue
        if _ADDRESS.search(ln):
            # the entry's e-mail line; its address lines are not read
            if last is not None and "@" in ln:
                add_emails(last, line_emails(ln))
            continue
        # a name printed without a leader is read only directly under its
        # heading; any other line ends the office
        last = None
        if after_heading and role and looks_like_person(ln):
            last = person(ln, role)
            people.append(last)
        else:
            role = None
        after_heading = False
    return people


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    first = re.search(r"(?m)^TOWN OF [A-Z]", text)
    if not first:
        raise RuntimeError("no 'TOWN OF' page was found")
    section = text[first.start():]
    end = re.search(r"(?m)^(VILLAGE|CITY) OF ", section)
    if end:
        section = section[:end.start()]
    towns = {}
    for town, block in split_blocks(section, r"(?m)^TOWN OF ([A-Z .'\-]+?)\s*$"):
        people = _officers(block)
        if people:
            towns[town.title()] = people
    m = re.search(r"\b(20\d\d\s*-\s*20\d\d)\b", text[:3000])
    return {"towns": towns, "edition": m.group(1) if m else None}
