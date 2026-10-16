"""Sauk County: the county clerk's Official Directory, May 2026 - April 2027 (PDF).

"TOWNSHIP OFFICIALS" lists each town under a "Township of <Name>" heading. Each
office is a line of its own ("Chair (2-Year Term Expires April 2027)",
"Supervisor I (...)", "Supervisor #1 (...)") and the next line holds the
officer's name, then a comma and the home address; telephone and e-mail lines
follow. Only the text before the address is kept. Read with the token on
2026-10-15 (robots.txt: 5,869 bytes, no rule matches the file)."""

import re

from . import clean, looks_like_person, norm_role, person, split_blocks

COUNTY_FIPS = "111"
COUNTY_NAME = "Sauk"
SOURCES = ["https://www.co.sauk.wi.us/sites/default/files/fileattachments/"
           "county_clerk/page/2101/saukdirectory2026to2027.pdf"]

_ROLE = re.compile(r"^(Chair(?:person|man)?|Supervisor(?:\s*#?\s*\d+|\s+[IVX]+)?)"
                   r"\s*(?:\(.*)?$")
# an address part: a rural number ("E10003 Hoot Owl"), a street number, or a
# P.O. Box
_ADDR = re.compile(r"^([NSEW]?\d|P\.?\s?O\.?\s)", re.I)


def name_part(line):
    """The name in "William F. Klemm, E10003 Hoot Owl Valley Road, Baraboo,
    WI 53913": the comma-separated parts before the first that is an address
    ("Bob Giebel, Jr., E9304 ..." keeps "Bob Giebel, Jr.")."""
    parts = [p.strip() for p in line.split(",")]
    keep = []
    for p in parts:
        if _ADDR.match(p):
            break
        keep.append(p)
    if len(keep) == len(parts) and len(parts) > 1:
        # nothing looked like an address; the line is not a plain name
        return None
    return clean(", ".join(keep))


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = text.find("TOWNSHIP OFFICIALS")
    end = text.find("VILLAGE OFFICIALS", start)
    if start < 0 or end < 0:
        raise RuntimeError("the TOWNSHIP OFFICIALS section was not found")
    section = text[start:end]
    towns = {}
    for town, block in split_blocks(section, r"(?m)^Township of ([A-Za-z .'\-]+?)\s*$"):
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        people = []
        for i, ln in enumerate(lines[:-1]):
            m = _ROLE.match(ln)
            if not m:
                continue
            role = norm_role(m.group(1))
            name = name_part(lines[i + 1])
            if role and name and looks_like_person(name):
                people.append(person(name, role))
        if people:
            towns[town] = people
    m = re.search(r"(May\s+\d{4}\s*[-–]\s*April\s+\d{4})", text)
    return {"towns": towns, "edition": clean(m.group(1)) if m else None}
