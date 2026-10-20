"""Marquette County: the county's Directory 2026-2027 (PDF, file dated
06.30.2026).

Its "Town, Village, and City Officers" pages list each town under a "Town of
<Name>" heading, then the board laid out in two columns: one text line carries
up to two "Role Name" pairs ("Chairperson Scott Kempley Supervisor Roger
Wallis"), followed by the two people's home addresses, phones and e-mails. The
names are read from the lines that open with Chairperson or Supervisor. Each
person's number and e-mail address are read by position: on the rows below the
role line, the part of a row that sits in that person's column (from their
role word to the next role word) is read only when it holds nothing but
telephone numbers or an e-mail address, so neither is ever handed across
columns and an address is never read. An e-mail address the directory breaks
over two rows is not read. Read with
the token on 2026-10-15 (robots.txt: 190 bytes, no rule matches the file)."""

import re

from . import (clean, contact_line, line_emails, norm_role,
               phone_line_numbers, person, split_blocks)

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
    """{role line: [(the numbers, the e-mail addresses) in each role's
    column]}, read from the directory's word positions. For numbers a column
    runs from its role word to 20 points before the next one; on the six rows
    below the role line (up to the next role line or town), the first part of
    each column that holds nothing but telephone numbers is that person's.
    For e-mail addresses each word goes to the column whose role word is
    nearest its start, because a long address can start further left of its
    column than 20 points (measured 2026-10-17: Newton's second column,
    25 points), and the first part of a column that holds nothing but an
    e-mail address is that person's. A role line printed twice is left out,
    so neither can be given to the wrong one."""
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
            mails = [[] for _ in xs]
            for below in rows[k + 1:k + 7]:
                if re.match(r"^(Chairperson|Supervisor)\b|^-?\s*Town of ",
                            " ".join(w["text"] for w in below)):
                    break
                for c, x in enumerate(xs):
                    hi = xs[c + 1] - 20 if c + 1 < len(xs) else float("inf")
                    part = " ".join(w["text"] for w in below
                                    if x - 20 <= w["x0"] < hi)
                    if not cols[c]:
                        cols[c] = phone_line_numbers(part)
                    near = " ".join(
                        w["text"] for w in below
                        if w["x0"] >= xs[0] - 20 and min(
                            range(len(xs)),
                            key=lambda n: abs(xs[n] - w["x0"])) == c)
                    if not mails[c] and contact_line(near):
                        mails[c] = line_emails(near)
            key = _key(text)
            if key in out:
                twice.add(key)
            out[key] = list(zip(cols, mails))
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
            cols = [([], []) for _ in hits]
        for i, m in enumerate(hits):
            end = hits[i + 1].start() if i + 1 < len(hits) else len(line)
            name = re.sub(r"\(\d{4}\)", "", line[m.end():end])
            role = norm_role(m.group(1))
            if role and clean(name):
                phones, emails = cols[i]
                out.append(person(clean(name), role, phones, emails=emails))
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
