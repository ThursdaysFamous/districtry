"""Walworth County: the county's Local Officials list ("Municipal Officials",
PDF, Document Center item 20494).

Under "TOWNSHIPS:" each town is an upper-case heading ("DARIEN"), followed by
labelled entries: "Chairperson: Kevin Schutt, <home address>, <phone>" and
"Supervisors: Mark Radtke, <address>" with each further supervisor on a line
of its own, "Rich Keyzer, <address>". Address, telephone and e-mail text wraps
onto following lines; a line that follows one ending in a comma is that
wrap, never a new person. The name is the text before the first comma of an
entry. The entry's telephone numbers ship: a part of the entry or of its wrap
lines that holds nothing but numbers and an e-mail address, and a number that
ends the entry's address ("..., Elkhorn, WI 53121, 262-555-0100"), read on its
own. The address and the e-mail address are not read. Read with the token on
2026-10-15 (robots.txt: 816 bytes, no rule matches the document)."""

import re

from . import clean, end_phones, looks_like_person, norm_role, person, phones_in

COUNTY_FIPS = "127"
COUNTY_NAME = "Walworth"
SOURCES = ["https://co.walworth.wi.us/DocumentCenter/View/20494/"
           "Municipal-Officials"]

_LABEL = re.compile(r"^([A-Z][A-Za-z./ ]{0,30}?)\s*:\s*(.*)$")
_HEAD = re.compile(r"(?m)^([A-Z][A-Z .'\-]+)\s*$")


def first_part(s):
    return clean(s.split(",")[0])


def _numbers(text):
    """The numbers in an entry's text after the name, or in a wrap line: the
    whole text when it holds nothing but numbers and an e-mail address, else
    the number that ends it."""
    return phones_in(text) or end_phones(text)


def read_block(block):
    people = []            # [name, role, numbers]
    plural = None
    current = None         # the entry whose wrap lines are being read
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
            plural = current = None
            if not role or not re.match(r"(?i)^(chair|supervisor)", label):
                continue
            name = first_part(m.group(2))
            if looks_like_person(name):
                current = [name, role, _numbers(m.group(2)[m.group(2).find(",") + 1:]
                                                if "," in m.group(2) else "")]
                people.append(current)
            if m.group(1).lower().startswith("supervisors"):
                plural = role
            continue
        if plural and not wrapped and not re.match(r"^[\d(]", ln) and "@" not in ln:
            name = first_part(ln)
            if looks_like_person(name):
                current = [name, plural, _numbers(ln[ln.find(",") + 1:]
                                                  if "," in ln else "")]
                people.append(current)
                continue
        if current is not None:
            current[2].extend(_numbers(ln))
    return [person(name, role, numbers) for name, role, numbers in people]


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
