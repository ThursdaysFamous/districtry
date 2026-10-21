"""Portage County: the county clerk's Official Directory (PDF, "County
Directory PDF").

Its TOWN OFFICERS pages give each town under a "TOWN OF <NAME>" heading and a
three-column table (Name, Phone/Email/Fax, Address). In the extracted text each
officer is one line, "Chairperson: <name> <telephone> <home address>", with the
e-mail and the rest of the home address on the next line. The name is the text
between the office's colon and the telephone number; a row with no telephone
number to end the name is dropped rather than guessed at. The numbers that open
the phone column ship ("715-555-0100", "... Cell"), and so does a number that
opens the next line ("715-... Cell <town>"); reading stops at the first word
that is not a number or its label, so the home address after them is not read.
The e-mail address that opens the next line ships too; the post office and ZIP
code after it are not read. Read with the token on 2026-10-15 (robots.txt: 816
bytes, no rule matches the file)."""

import re

from . import clean, lead_phones, line_emails, norm_role, person, split_blocks

COUNTY_FIPS = "097"
COUNTY_NAME = "Portage"
SOURCES = ["https://www.co.portage.wi.gov/DocumentCenter/View/567/"
           "County-Directory-PDF"]

_ROW = re.compile(r"^(Chairperson|Chairman|Supervisor[^:]*):\s*(.+?)\s+"
                  r"\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b")


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = text.find("TOWN OFFICERS\nTOWN OF")
    if start < 0:
        raise RuntimeError("the TOWN OFFICERS pages were not found")
    section = text[start:]
    end = section.find("VILLAGE OFFICERS")
    if end > 0:
        section = section[:end]
    towns = {}
    for town, block in split_blocks(section,
                                    r"(?m)^TOWN OF ([A-Z][A-Z .']+?)\s*$"):
        people = []
        lines = [ln.strip() for ln in block.split("\n")]
        for i, line in enumerate(lines):
            m = _ROW.match(line)
            role = norm_role(m.group(1)) if m else None
            if role:
                phones = lead_phones(line[m.end(2):])
                emails = []
                if i + 1 < len(lines):
                    phones += lead_phones(lines[i + 1])
                    emails = line_emails(lines[i + 1])
                people.append(person(clean(m.group(2)), role, phones,
                                     emails=emails))
        if people:
            towns[town.title()] = people
    # the cover prints "Updated 10-14-2026"
    m = re.search(r"Updated\s+(\d{1,2}-\d{1,2}-20\d\d)", text[:1500])
    return {"towns": towns,
            "edition": ("updated " + m.group(1)) if m else None}
