"""St. Croix County: the county clerk's Official Directory 2026-2027.

The link says PDF and serves a Word document (.docx), read here as paragraph
text. Under "TOWNS" each town opens with a "TOWN OF <NAME>" heading (Baldwin
writes "Town of Baldwin"); each officer is one paragraph, "Chair<TAB>Douglas
Veenendall – 715-222-9408" (one Warren line uses a dot leader instead of the
tab), followed by home-address and e-mail paragraphs. The numbers after the
name ship, with the label the county gives a second one ("715-... (Cell)
715-..."); so does a number at the end of the address paragraph below when a
label naming a person's line stands before it. The address and the e-mail
address are not read. A label such as "Supervisor/Plan Committee Chairman" is
read by its first part only, so it stays a supervisor. Read with the token on
2026-10-15 (robots.txt: 816 bytes, no rule matches the document)."""

import re

from . import (clean, following_phones, looks_like_person, norm_role, person,
               phones_after_name)

COUNTY_FIPS = "109"
COUNTY_NAME = "St. Croix"
SOURCES = ["https://sccwi.gov/DocumentCenter/View/3000/"
           "Official-St-Croix-County-Directory-PDF"]

_LINE = re.compile(r"^(Chair(?:person|man)?|Supervisor(?:\s*#?\s*\d+)?)"
                   r"(?:/[^\t]*)?\s*(?:\t|[.…]{3,})[\s.…]*(.+)$")


def scrape(ctx):
    text = ctx.docx_text(SOURCES[0])
    start = re.search(r"(?m)^TOWNS\s*$", text)
    end = re.search(r"(?m)^VILLAGES\s*$", text[start.end():]) if start else None
    if not start or not end:
        raise RuntimeError("the TOWNS section was not found")
    section = text[start.end():start.end() + end.start()]
    hits = list(re.finditer(r"(?m)^TOWN OF ([A-Za-z .'\-]+?)\s*$", section, re.I))
    towns = {}
    for i, m in enumerate(hits):
        stop = hits[i + 1].start() if i + 1 < len(hits) else len(section)
        people = []
        lines = [ln.strip() for ln in section[m.end():stop].split("\n")
                 if ln.strip()]
        for k, ln in enumerate(lines):
            lm = _LINE.match(ln)
            if not lm:
                continue
            role = norm_role(lm.group(1))
            # the name runs to the dash before the telephone number
            name = clean(re.split(r"\s*[–—]\s*(?=\(?\d)|\s+-\s*(?=\(?\d)",
                                      lm.group(2))[0])
            if role and looks_like_person(name):
                phones = phones_after_name(ln, name)
                phones += following_phones(lines, k + 1, limit=2,
                                           stop_re=_LINE.pattern)
                people.append(person(name, role, phones))
        if people:
            towns[clean(m.group(1)).title()] = people
    ed = re.search(r"(\d{4}\s*[-–]\s*\d{4})", text[:2000])
    return {"towns": towns,
            "edition": re.sub(r"\s*[-–]\s*", "-", ed.group(1)) if ed else None}
