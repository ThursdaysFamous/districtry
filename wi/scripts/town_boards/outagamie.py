"""Outagamie County: the county clerk's Directory of Public Officials
2026-2027 ("Last Revised: 10/14/2026"), a PDF served at the directory page's
own address.

Each town opens with a "TOWN OF <NAME>" heading; where its officers run onto
the next page, that page repeats the heading as "TOWN OF <NAME> (Cont'd…)"
(Bovina, Kaukauna, Oneida and others), so the two parts are read as one town.
Under upper-case office headings (CHAIRPERSON, SUPERVISORS, CLERK, ...) each
officer has one line, "#1 – Name – home address • town ...... phone", and a
second line of term and e-mail. The name is the text before the first dash
after the seat number; the telephone number is the part of that line after
its dot leader, read only when it holds nothing but a number. The home address
before the leader and the e-mail line are not read. The PDF draws some names
without a space character ("JosephCoenen"), so the text is extracted with a
one-point x tolerance, which restores the gap. Read with the token on
2026-10-15 (robots.txt: 16,010 bytes, no rule matches the page)."""

import re

from . import clean, person, phones_after_name

COUNTY_FIPS = "087"
COUNTY_NAME = "Outagamie"
SOURCES = ["https://www.outagamie.gov/Our-County/County-Clerk/"
           "County-Board-Information/Directory-of-Public-Officials"]

_TOWN = re.compile(r"^TOWN OF ([A-Z][A-Z .']+?)(\s*\(Cont.*\))?\s*$")
_HEADING = re.compile(r"^[A-Z][A-Z /&’'.,()-]+$")
_ROW = re.compile(r"^(?:#\s*(\d+)\s*[–-]\s*)?(.+?)\s*–")


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0], x_tolerance=1)
    start = text.find("\nTOWN OF ")
    if start < 0:
        raise RuntimeError("no 'TOWN OF' heading was found")
    end = text.find("\nVILLAGE OF ", start)
    section = text[start:end] if end > 0 else text[start:]
    towns = {}
    town = role = None
    for line in section.split("\n"):
        line = line.strip()
        if not line or re.match(r"^-\s*\d+\s*-$", line):
            continue
        m = _TOWN.match(line)
        if m:
            town = m.group(1).title()
            if not m.group(2):
                role = None
            continue
        if _HEADING.match(line) and len(line) > 2:
            role = {"CHAIRPERSON": "Chairperson", "CHAIRMAN": "Chairperson",
                    "SUPERVISORS": "Supervisor",
                    "SUPERVISOR": "Supervisor"}.get(line)
            continue
        if not (town and role) or line.startswith("."):
            continue
        r = _ROW.match(line)
        if not r or re.search(r"\bvacant\b", line, re.I):
            continue
        label = role + (" #" + r.group(1) if role == "Supervisor" and r.group(1)
                        else "")
        name = clean(r.group(2))
        towns.setdefault(town, []).append(
            person(name, label, phones_after_name(line, name)))
    m = re.search(r"\b(20\d\d)\s*[-–]\s*(20\d\d)\b", text[:600])
    return {"towns": towns,
            "edition": ("%s-%s" % m.groups()) if m else None}
