"""Bayfield County: the county clerk's Official County Directory 2026-2027
(PDF).

Each town has its own page under a "TOWN OF <NAME>" heading. Below the town
hall details, each office is an all-capital heading ("CHAIRPERSON",
"SUPERVISORS", "CLERK", ...) followed by one entry per officer: the name with a
telephone number on the first line, then the street address and an e-mail line.
An asterisk before a name marks a staggered even-year term and is dropped. Some
pages set the offices in two columns, so the page is rebuilt from word positions:
the left column is read before the right one. Read with the token on 2026-10-15
(robots.txt: 816 bytes, no rule matches the document's path).

The numbers printed after the name on its first line ship on the officer
("Cell:" kept as the label); the address line below it is not read."""

import re

from . import (clean, looks_like_person, person, phones_after_name,
               strip_contact)

COUNTY_FIPS = "007"
COUNTY_NAME = "Bayfield"
SOURCES = ["https://bayfieldcounty.wi.gov/DocumentCenter/View/21879/"
           "Official-County-Directory-2026-2027"]

# office headings that open a second column; their x position is the split
_HEADING = re.compile(r"^[A-Z][A-Z/&\- ]{3,}$")


def _lines(words):
    """Group a page's words into lines by their top position."""
    rows = []
    for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])):
        if rows and abs(rows[-1][0] - w["top"]) < 3:
            rows[-1][1].append(w)
        else:
            rows.append([w["top"], [w]])
    return [(top, sorted(ws, key=lambda w: w["x0"])) for top, ws in rows]


def _page_text(words):
    """The page as text, with a right-hand column read after the left one.
    A right column is recognised by an all-capital office heading starting
    right of centre on the same line as a left-hand one ("CHAIRPERSON
    ASSESSOR")."""
    rows = _lines(words)
    split = start = None
    for top, ws in rows:
        # a line holding nothing but two office headings, one at the left
        # margin and one right of centre
        if (len(ws) >= 2 and ws[0]["x0"] < 100
                and all(_HEADING.match(w["text"]) for w in ws)
                and any(w["x0"] > 300 for w in ws[1:])):
            split = min(w["x0"] for w in ws[1:] if w["x0"] > 300) - 5
            start = top
            break
    out, right = [], []
    for top, ws in rows:
        if split is None or top < start - 1:
            out.append(" ".join(w["text"] for w in ws))
            continue
        left = [w["text"] for w in ws if w["x0"] < split]
        rt = [w["text"] for w in ws if w["x0"] >= split]
        if left:
            out.append(" ".join(left))
        if rt:
            right.append(" ".join(rt))
    return "\n".join(out + right)


def _people(block):
    people = []
    role = None
    for ln in block.split("\n"):
        ln = ln.strip()
        if not ln:
            continue
        if _HEADING.match(ln):
            if re.match(r"^CHAIR(PERSON|MAN|WOMAN)?$", ln):
                role = "Chairperson"
            elif re.match(r"^SUPERVISORS?$", ln):
                role = "Supervisor"
            else:
                role = None
            continue
        if role is None:
            continue
        if re.match(r"^(e-?mail|phone|fax|website)\b", ln, re.I):
            continue
        # the name ends where a telephone number or "No Phone" starts
        name = re.split(r"\(|\bNo Phone\b|\d{3}-\d{4}", ln)[0]
        name = strip_contact(name).lstrip("*").strip()
        if looks_like_person(name):
            people.append(person(name, role, phones_after_name(ln, name)))
            if role == "Chairperson":
                role = None     # one chair; what follows is the address
    return people


def scrape(ctx):
    pages = ctx.pdf_words(SOURCES[0])
    text = "\n".join(_page_text(ws) for _, ws in pages)
    towns = {}
    hits = list(re.finditer(r"(?m)^TOWN OF ([A-Z .'\-]+?)\s*$", text))
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        nxt = re.search(r"(?m)^(VILLAGE|CITY) OF ", text[m.end():end])
        block = text[m.end():m.end() + nxt.start()] if nxt else text[m.end():end]
        people = _people(block)
        if people:
            towns[clean(m.group(1)).title()] = people
    m = re.search(r"Official County Directory\s+(\d{4}\s*-\s*\d{4})", text, re.I)
    return {"towns": towns, "edition": m.group(1) if m else "2026-2027"}
