"""Walworth County: the county's Local Officials list ("Municipal Officials",
PDF, Document Center item 20494).

Under "TOWNSHIPS:" each town is an upper-case heading ("DARIEN"), followed by
labelled entries: "Chairperson: Kevin Schutt, <home address>, <phone>" and
"Supervisors: Mark Radtke, <address>" with each further supervisor on a line
of its own, "Rich Keyzer, <address>". Address, telephone and e-mail text wraps
onto following lines; a line that follows one ending in a comma is that
wrap, never a new person, and only the text before the first comma of an entry
is kept. Read with the token on 2026-10-15 (robots.txt: 816 bytes, no rule
matches the document)."""

import re

from . import clean, looks_like_person, norm_role, person

COUNTY_FIPS = "127"
COUNTY_NAME = "Walworth"
SOURCES = ["https://co.walworth.wi.us/DocumentCenter/View/20494/"
           "Municipal-Officials"]

_LABEL = re.compile(r"^([A-Z][A-Za-z./ ]{0,30}?)\s*:\s*(.*)$")
_HEAD = re.compile(r"(?m)^([A-Z][A-Z .'\-]+)\s*$")


def first_part(s):
    return clean(s.split(",")[0])


def read_block(block):
    people = []
    plural = None
    prev = ""
    for ln in (x.strip() for x in block.split("\n")):
        if not ln:
            continue
        wrapped = prev.endswith(",")
        prev = ln
        m = _LABEL.match(ln)
        # a board label always opens a new entry, even after a line ending in
        # a comma ("Website: www.townoflyonswi.com," above Lyons's chair)
        if m and (not wrapped or re.match(r"(?i)^(chair|supervisor)", m.group(1))):
            label = re.sub(r"(?i)\bsupervisors\b", "Supervisor", m.group(1))
            role = norm_role(label)
            plural = None
            if not role or not re.match(r"(?i)^(chair|supervisor)", label):
                continue
            name = first_part(m.group(2))
            if looks_like_person(name):
                people.append(person(name, role))
            if m.group(1).lower().startswith("supervisors"):
                plural = role
            continue
        if plural and not wrapped and not re.match(r"^[\d(]", ln) and "@" not in ln:
            name = first_part(ln)
            if looks_like_person(name):
                people.append(person(name, plural))
    return people


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = text.find("TOWNSHIPS:")
    end = text.find("VILLAGES:", start)
    if start < 0 or end < 0:
        raise RuntimeError("the TOWNSHIPS section was not found")
    section = text[start + len("TOWNSHIPS:"):end]
    hits = list(_HEAD.finditer(section))
    towns = {}
    for i, m in enumerate(hits):
        stop = hits[i + 1].start() if i + 1 < len(hits) else len(section)
        people = read_block(section[m.end():stop])
        if people:
            towns[clean(m.group(1)).title()] = people
    return {"towns": towns, "edition": None}
