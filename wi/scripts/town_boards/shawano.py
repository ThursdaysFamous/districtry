"""Shawano County: the county clerk's County Directory (PDF).

Each town opens with a "TOWN OF <NAME>" heading and continues on the next page
under "TOWN OF <NAME> - continued" (Herman's supervisors are on its
continuation, for example), so the parts of one town are joined before reading.
Offices are capitalised labels: "CHAIRMAN: Dan Lex", "SUPERVISOR 1: Robert
Sippl", or "SUPERVISORS:" followed by one name per line ("1 - Terry Moede
.... 2026" in Wescott, with a dot leader to the term year), each name followed
by its home address and a telephone/e-mail line ("Phone: 715-555-0100 E-mail:
..."), sometimes with a second number on a line of its own ("920-555-0101
(Cell)"). The telephone lines below a name ship, up to the next office or name,
each with its label; a number marked as a place's ("(Town Hall)") does not, and
the home address and e-mail address are not read. Read with the token on
2026-10-15 (robots.txt served empty: allow all)."""

import re

from . import (clean, following_phones, looks_like_person, norm_role, person,
               strip_contact)

COUNTY_FIPS = "115"
COUNTY_NAME = "Shawano"
SOURCES = ["https://www.co.shawano.wi.us/i_shawano/d/County_Clerk/"
           "shawano_county_directory.pdf"]

_HEAD = re.compile(r"(?m)^TOWN OF ([A-Z .'\-]+?)(\s*[-–]\s*continued)?\s*$", re.I)
_LABEL = re.compile(r"^([A-Z][A-Z .]*?(?:\s*\d+)?)\s*:\s*(.*)$")
# address, contact and page-number lines inside a block
_SKIP = re.compile(r"^([NSEW]?\d|P\.?\s?O\.?\s|Phone|E-?mail|Cell|Fax|Office)",
                   re.I)


def role_of(label):
    label = re.sub(r"(?i)\bsupervisors\b", "Supervisor", label)
    return norm_role(label)


def read_block(block):
    people = []
    plural = None          # role a "SUPERVISORS:" list is collecting under
    lines = [x.strip() for x in block.split("\n") if x.strip()]

    def phones(i):
        # the telephone lines below the name on line i, up to the next office
        # or name
        return following_phones(lines, i + 1, limit=3, stop_re=_LABEL.pattern)

    for i, ln in enumerate(lines):
        m = _LABEL.match(ln)
        if m:
            plural = None
            role = role_of(m.group(1))
            rest = strip_contact(m.group(2))
            if not role:
                continue
            if rest:
                if looks_like_person(rest):
                    people.append(person(rest, role, phones(i)))
            else:
                plural = role
            continue
        seat = re.match(r"^(\d)\s*-\s*(.+)$", ln)
        if plural and seat:
            # Wescott numbers its list: "1 - Terry Moede ........ 2026"
            name = strip_contact(seat.group(2))
            if looks_like_person(name):
                people.append(person(name, plural + " " + seat.group(1),
                                     phones(i)))
            continue
        if plural and not _SKIP.match(ln):
            name = strip_contact(ln)
            if looks_like_person(name):
                people.append(person(name, plural, phones(i)))
            else:
                plural = None
    return people


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    end = re.search(r"(?m)^VILLAGE OF ", text)
    hits = list(_HEAD.finditer(text[:end.start()] if end else text))
    if not hits:
        raise RuntimeError("no TOWN OF headings found")
    parts = {}
    order = []
    for i, m in enumerate(hits):
        stop = hits[i + 1].start() if i + 1 < len(hits) else (end.start() if end else len(text))
        town = clean(m.group(1)).title()
        if town not in parts:
            parts[town] = ""
            order.append(town)
        parts[town] += "\n" + text[m.end():stop]
    towns = {}
    for town in order:
        people = read_block(parts[town])
        if people:
            towns[town] = people
    m = re.search(r"(\d{4}\s*[-–]\s*\d{4})\s+(?:Shawano County\s+)?Directory", text)
    return {"towns": towns, "edition": m.group(1) if m else None}
