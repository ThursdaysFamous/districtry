"""Marquette County: the county's Directory 2026-2027 (PDF, file dated
06.30.2026).

Its "Town, Village, and City Officers" pages list each town under a "Town of
<Name>" heading, then the board laid out in two columns: one text line carries
up to two "Role Name" pairs ("Chairperson Scott Kempley Supervisor Roger
Wallis"), followed by the two people's home addresses, phones and e-mails. The
names are read from the lines that open with Chairperson or Supervisor. Each
person's number is read by position: on the rows below the role line, the part
of a row that sits in that person's column (from their role word to the next
role word) is read only when it holds nothing but telephone numbers, so a
number is never handed across columns and an address is never read. Read with
the token on 2026-10-15 (robots.txt: 190 bytes, no rule matches the file)."""

import re

from . import clean, norm_role, phone_line_numbers, person, split_blocks

COUNTY_FIPS = "077"
COUNTY_NAME = "Marquette"
SOURCES = ["https://www.marquettecountywi.gov/wp-content/uploads/2026/06/"
           "2026-2027-County-Directory-in-Publisher-06.30.2026.pdf"]

# A role as the county prints it, with an optional seat number and the en dash
# some rows put after it ("Supervisor 1– Dennis Daye").
_ROLE = re.compile(r"\b(Chairperson|Supervisor(?:\s+\d)?)\s*[–-]?\s+")
_LINE = re.compile(r"^(Chairperson|Supervisor)\b")


def _rows(words):
    """A page's words grouped into rows by their top position."""
    rows = []
    for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])):
        if rows and abs(rows[-1][0] - w["top"]) < 3:
            rows[-1][1].append(w)
        else:
            rows.append([w["top"], [w]])
    return [sorted(ws, key=lambda w: w["x0"]) for _, ws in rows]


def _key(text):
    return re.sub(r"\s+", " ", text).strip()


def _numbers_by_line(ctx):
    """{role line: [the numbers in each role's column]}, read from the
    directory's word positions. A column runs from its role word to 20 points
    before the next one; on the six rows below the role line (up to the next
    role line or town), the first part of each column that holds nothing but
    telephone numbers is that person's. A role line printed twice is left
    out, so a number cannot be given to the wrong one."""
    out, twice = {}, set()
    for _, words in ctx.pdf_words(SOURCES[0]):
        rows = _rows(words)
        for k, row in enumerate(rows):
            text = " ".join(w["text"] for w in row)
            if not _LINE.match(text):
                continue
            xs = [w["x0"] for w in row if re.match(r"^(Chairperson|Supervisor)",
                                                    w["text"])]
            cols = [[] for _ in xs]
            for below in rows[k + 1:k + 7]:
                if re.match(r"^(Chairperson|Supervisor)\b|^-?\s*Town of ",
                            " ".join(w["text"] for w in below)):
                    break
                for c, x in enumerate(xs):
                    if cols[c]:
                        continue
                    hi = xs[c + 1] - 20 if c + 1 < len(xs) else float("inf")
                    part = " ".join(w["text"] for w in below
                                    if x - 20 <= w["x0"] < hi)
                    cols[c] = phone_line_numbers(part)
            key = _key(text)
            if key in out:
                twice.add(key)
            out[key] = cols
    for key in twice:
        del out[key]
    return out


def _people(block, numbers):
    out = []
    for line in block.split("\n"):
        line = line.strip()
        if not _LINE.match(line):
            continue
        hits = list(_ROLE.finditer(line))
        cols = numbers.get(_key(line))
        if not cols or len(cols) != len(hits):
            cols = [[] for _ in hits]
        for i, m in enumerate(hits):
            end = hits[i + 1].start() if i + 1 < len(hits) else len(line)
            name = re.sub(r"\(\d{4}\)", "", line[m.end():end])
            role = norm_role(m.group(1))
            if role and clean(name):
                out.append(person(clean(name), role, cols[i]))
    return out


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = text.find("Town, Village, and City Officers")
    if start < 0:
        raise RuntimeError("the 'Town, Village, and City Officers' pages "
                           "were not found")
    section = text[start:]
    end = re.search(r"(?m)^-?\s*(Village|City) of ", section)
    if end:
        section = section[:end.start()]
    numbers = _numbers_by_line(ctx)
    towns = {}
    for town, block in split_blocks(section,
                                    r"(?m)^-?\s*Town of ([A-Z][a-z]+"
                                    r"(?: [A-Z][a-z]+)?)\b.*$"):
        people = _people(block, numbers)
        if people:
            towns[town] = people
    m = re.search(r"\b(20\d\d)\s*[-–]?\s*(20\d\d)\b", text[:400])
    return {"towns": towns,
            "edition": ("%s-%s" % m.groups()) if m else None}
