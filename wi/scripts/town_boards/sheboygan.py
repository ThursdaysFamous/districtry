"""Sheboygan County: the county clerk's Directory of Officials 2025-2026 (PDF).

Each town is a page under a "TOWN OF <NAME>" heading. The chair is one dot-
leader line, "Chairperson ........ Michael Limberg". The supervisors follow a
bare "Supervisors" line, one per line as "Daniel Klahn ....... (920) 526-3368"
(the Town of Sheboygan writes "Supervisor #1-Tim Winkel ....."), each usually
followed by a home-address line, which is skipped; the list ends at the next
line that is neither a leader line nor an address (Constable, a page number) or at a leader line ending in something other than
a telephone number ("Ordinance Enforcement Officer ..... <name>").

CLIENT: on 2026-10-15 this project's token got HTTP 403 from
sheboygancounty.com on both robots.txt and the document; read as Chrome the
robots.txt (6,706 bytes) has no rule matching the document, which then served
in full."""

import re

from . import clean, looks_like_person, norm_role, person

COUNTY_FIPS = "117"
COUNTY_NAME = "Sheboygan"
SOURCES = ["https://sheboygancounty.com/home/showpublisheddocument/20385/"
           "638870528138070000"]
CLIENT = "chrome"  # token re-measured 2026-10-15 at SOURCES[0]: HTTP 403 Forbidden

_LEAD = re.compile(r"\s*(?:\.{3,}|…+).*$")
_ADDR = re.compile(r"^([NSEW]?\d|P\.?\s?O\.?\s|\()", re.I)


def before_leader(line):
    """'Daniel Klahn ....... (920) 526-3368' -> 'Daniel Klahn'; None when the
    line has no leader."""
    m = re.search(r"\.{3,}|…+", line)
    return clean(line[:m.start()]) if m else None


def after_leader(line):
    m = re.search(r"(?:\.{3,}|…+)\s*(.*)$", line)
    return clean(m.group(1)) if m else None


def read_block(block):
    people = []
    in_supv = False
    for ln in (x.strip() for x in block.split("\n")):
        if not ln:
            continue
        if re.match(r"^Chair(person|man|woman)?\s*(\.{3,}|…)", ln):
            in_supv = False
            name = after_leader(ln)
            if name and looks_like_person(name):
                people.append(person(name, "Chairperson"))
            continue
        if re.match(r"^Supervisors?\s*$", ln):
            in_supv = True
            continue
        if not in_supv:
            continue
        name = before_leader(ln)
        if name is None:
            if _ADDR.match(ln):
                continue          # a supervisor's address or phone line
            in_supv = False       # Constable, Code Enforcement, page number
            continue
        if not re.search(r"\d{3}\)?[-. ]?\s*\d{3}[-. ]\d{4}", after_leader(ln) or ""):
            in_supv = False       # "Ordinance Enforcement Officer .... Steve Wimmer"
            continue
        role = "Supervisor"
        m = re.match(r"^(Supervisor\s*#?\s*\d+)\s*[-–]\s*(.+)$", name)
        if m:
            role, name = norm_role(m.group(1)), clean(m.group(2))
        if looks_like_person(name):
            people.append(person(name, role))
    return people


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    first = re.search(r"(?m)^TOWN OF GREENBUSH\s*$", text)
    end = re.search(r"(?m)^VILLAGE OF ", text[first.start():]) if first else None
    if not first or not end:
        raise RuntimeError("the town pages were not found")
    section = text[first.start():first.start() + end.start()]
    hits = list(re.finditer(r"(?m)^TOWN OF ([A-Z .'\-]+?)\s*$", section))
    towns = {}
    for i, m in enumerate(hits):
        stop = hits[i + 1].start() if i + 1 < len(hits) else len(section)
        people = read_block(section[m.end():stop])
        if people:
            towns[clean(m.group(1)).title()] = people
    ed = re.search(r"(\d{4}\s*[-–]\s*\d{4})\s*\n\s*D\s*O", text)
    edition = re.sub(r"\s*[-–]\s*", "-", ed.group(1)) if ed else None
    return {"towns": towns, "edition": edition}
