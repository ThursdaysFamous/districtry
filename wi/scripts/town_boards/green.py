"""Green County: one page per town on the county website.

"Municipalities of Green County" (/356/Municipalities-of-Green-County) links a
page for each of the sixteen towns. Each town page lists its officers as a
label line ("Chair:", "1st Supervisor:", "2nd Supervisor:") followed by the
officer's name on the next line, then address, telephone and e-mail lines,
which are not kept. Read with the token on 2026-10-15 (robots.txt: 816 bytes,
no rule matches these paths)."""

import re
import urllib.parse

from . import clean, html_text, looks_like_person, norm_role, person

COUNTY_FIPS = "045"
COUNTY_NAME = "Green"
SOURCES = ["https://greencountywi.org/356/Municipalities-of-Green-County"]

# "Chair:" / "Town Chair:" / "1st Supervisor:" / "Supervisor 2:" alone on a line,
# or with the name after the colon
_ROLE = re.compile(
    r"^(?:town\s+)?(?:(1st|2nd|3rd|4th)\s+)?(chair\w*|supervisor)"
    r"(\s*#?\s*\d+|\s+[IVX]+)?\s*:\s*(.*)$", re.I)


def _town_links(page, base):
    out = {}
    for href, name in re.findall(
            r'<a [^>]*href="(/\d+/Town-of-[^"]+)"[^>]*>\s*Town of ([^<]+?)\s*</a>',
            page):
        out.setdefault(clean(name), urllib.parse.urljoin(base, href))
    return out


def _join_split_words(page):
    """A name split across two inline tags ("<strong>Tracy Signe</strong>
    <span>r</span>", Clarno) would read as two words in the page text; join
    inline tags that sit between two letters."""
    return re.sub(r"(?<=\w)(?:</?(?:span|strong|b|em|i|font)\b[^>]*>)+(?=\w)",
                  "", page)


def _board(text):
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    people = []
    for i, ln in enumerate(lines):
        m = _ROLE.match(ln)
        if not m:
            continue
        ordinal, word, seat, rest = m.groups()
        label = word + (seat or "")
        if ordinal:
            label = word + " " + ordinal
        role = norm_role(label)
        if not role:
            continue
        name = clean(rest) or (clean(lines[i + 1]) if i + 1 < len(lines) else "")
        if looks_like_person(name):
            people.append(person(name, role))
    return people


def scrape(ctx):
    index = ctx.fetch_text(SOURCES[0])
    links = _town_links(index, SOURCES[0])
    if len(links) < 12:
        raise RuntimeError("found %d town links on the index" % len(links))
    towns = {}
    for town, url in sorted(links.items()):
        text = html_text(_join_split_words(ctx.fetch_text(url)))
        # the town's own block follows its heading, printed twice (breadcrumb,
        # then title); the side menu above lists every town once
        head = "Town of %s\nTown of %s\n" % (town, town)
        start = text.find(head)
        if start < 0:
            continue
        end = text.find("Agendas & Minutes", start)
        people = _board(text[start:end if end > 0 else None])
        if people:
            towns[town] = people
    return {"towns": towns, "edition": None}
