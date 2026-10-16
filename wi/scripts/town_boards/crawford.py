"""Crawford County: the County Directory 2026-2027 (PDF).

The "Town Officers" section lists each town under its bare name ("Bridgeport"),
then "Chairman ........ Name" with the chair's telephone and home address on the
lines after it, and "Supervisor ........ Name, Post office" for each
supervisor. The text after the last comma is the supervisor's post office and
is dropped unless it is a suffix such as "Jr". The section ends at "Village
Officers". The cover title is set in doubled letters in the text layer
("22002266--22002277"), so the edition is read from it by taking every second
character. Read with the token on 2026-10-15 (robots.txt: 156 bytes, Allow: /)."""

import re

from . import clean, looks_like_person, norm_role, person

COUNTY_FIPS = "023"
COUNTY_NAME = "Crawford"
SOURCES = ["https://www.crawfordcountywi.gov/media/Directory/"
           "countydirectory-2026.pdf"]

_ROLE = re.compile(r"^(Chair\w*|Supervisor)\s*[.…]{3,}\s*(.+)$", re.I)
_SUFFIX = re.compile(r"^(Jr|Sr|II|III|IV)\.?$", re.I)


def _name(text):
    text = clean(text)
    if "," in text:
        head, tail = text.rsplit(",", 1)
        if not _SUFFIX.match(tail.strip()):
            text = head
    return clean(text)


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    hits = [m.end() for m in re.finditer(r"(?m)^Town Officers\s*$", text)]
    if not hits:
        raise RuntimeError("the Town Officers section was not found")
    start = hits[-1]                     # the first match is the contents page
    end = re.search(r"(?m)^Village Officers\s*$", text[start:])
    section = text[start:start + end.start()] if end else text[start:]
    lines = [ln.strip() for ln in section.split("\n") if ln.strip()]
    towns, town = {}, None
    for i, ln in enumerate(lines):
        m = _ROLE.match(ln)
        if not m:
            # a town heading is the bare line just before its chairman
            if i + 1 < len(lines) and re.match(r"^Chair", lines[i + 1], re.I):
                town = clean(ln)
            continue
        role = norm_role(m.group(1))
        name = _name(m.group(2))
        if town and role and looks_like_person(name):
            towns.setdefault(town, []).append(person(name, role))
    edition = None
    m = re.search(r"(?m)^([\d\-]{18})\s*$", text[:2000])
    if m and m.group(1)[::2] == m.group(1)[1::2]:
        edition = m.group(1)[::2]
    return {"towns": towns, "edition": edition}
