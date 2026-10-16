"""Ozaukee County: the county clerk's Official Directory 2026-2027 (PDF).

Its Town Officials pages give each town under a "TOWN OF <NAME>" heading (a town
whose list runs onto a second page repeats the heading there). Each officer is
one line, the office in capitals, a dot leader, then the name
("CHAIRPERSON……Thomas Winker", "SEAT 1 SUPERVISOR……Wayne Pipkorn"), followed by
lines of e-mail, phone and home address that are never read. Read with the
token on 2026-10-15 (robots.txt: 816 bytes, no rule matches the file)."""

import re

from . import clean

COUNTY_FIPS = "089"
COUNTY_NAME = "Ozaukee"
SOURCES = ["https://ozaukeecounty.gov/DocumentCenter/View/57"]

_TOWN = re.compile(r"^TOWN OF ([A-Z][A-Z .']+?)\s*$")
_ROW = re.compile(r"^(?:SEAT\s+(\d+)\s+)?(CHAIRPERSON|CHAIRMAN|SUPERVISOR)"
                  r"\s*[.…]+\s*(.+)$")


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = text.find("\nTOWN OF ")
    if start < 0:
        raise RuntimeError("no 'TOWN OF' heading was found")
    end = text.find("\nVILLAGE OF ", start)
    section = text[start:end] if end > 0 else text[start:]
    towns = {}
    town = None
    for line in section.split("\n"):
        line = line.strip()
        m = _TOWN.match(line)
        if m:
            town = m.group(1).title()
            continue
        r = _ROW.match(line)
        if not (town and r):
            continue
        role = "Chairperson" if r.group(2).startswith("CHAIR") else (
            "Supervisor" + (" #" + r.group(1) if r.group(1) else ""))
        towns.setdefault(town, []).append({"name": clean(r.group(3)),
                                           "role": role})
    m = re.search(r"\b(20\d\d)\s*[-–]\s*(20\d\d)\b", text[:400])
    return {"towns": towns,
            "edition": ("%s-%s" % m.groups()) if m else None}
