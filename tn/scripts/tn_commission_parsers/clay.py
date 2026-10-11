"""Clay County elects 10 commissioners, two from each of its 5 districts (the
August 2026 ballot reads "VOTE FOR 2" in every County Commissioner District
race and names no seat or position, so no seat is recorded; CTAS gives
"Number of Commissioners: 10, Number of Commission Districts: 5").

The page is the county government's own Commissioners page on
www.claycountytngov.com, the county's website as CTAS lists it
(ctas.tennessee.edu/county/clay, read 2026-10-11; an earlier survey had
looked for the county at guessed domains that do not resolve). It is a
Squarespace page built with the "Fluid Engine" layout, in which every heading,
name, contact paragraph and date is its own block placed on a grid by CSS, so
the HTML order of the blocks is NOT the order a reader sees (in the 3rd
District, Clifton Boles's contact block comes before his name in the HTML).
The page is therefore never read in order. What it does have is one page
section per district: each of the five <section data-test="page-section">
elements inside <main> holds exactly one <h3> "Nth District" heading (the
first also holds the page title "Clay County Commissioners") and that
district's members, each name an <h4> in its own block, each with a block
giving the date that member's service began ("9-1-2006", "9-1-2026",
"9/1/2026"). Every <h4> name is paired with the one district heading in its
own section. A section holding names and no district heading, or two district
headings, raises; so does an <h3> or <h4> in <main> that is neither, and a
section whose number of start-date blocks differs from its number of names
(a name block without its card). The <h4> blocks after </main> (the
footer's "Location" and "Contact for County Mayor") are not read.

PRIVACY: every member's contact block prints a home street name, town and
ZIP, a personal phone and (for nine of the ten) a personal e-mail (yahoo,
gmail, hotmail, icloud). None of it is read: only the <h4> name. The footer
prints the County Mayor's office address, phone and mayor@claycountytn.gov,
which belong to no member and are not read either. No e-mail, phone or
profile is recorded.

Names are kept as the page prints them ("J. Bryan Coons", "Dale McLerran",
"J. Tanner Harvey", "J. Elijah Watson").

Currency: checked 2026-10-11 against the Clay County Election Commission's
"Election Summary Report, 2026 State Primary and County General, Election
Date 8/6/2026" (claycountytnelections.com/wp-content/uploads/2026/08/
08-06-2026_ElectionResults.pdf, linked from the commission's home page; a
scanned PDF, read as images; the report is printed 8/11/2026 10:12 AM and
was scanned on 20 August 2026, the day of the commission's posted
"Election Results Certification" meeting, but does not itself say
certified). In every district the two names here are the two winners of the
"VOTE FOR 2" race: D1 Glyeen Dale Mclerran 267, J. Bryan Coons 221 (Hugh
Brian Cherry 182, Terry Wayne Scott 140, Derek L. Scott 125, Robert "Bobby"
Jacoby 86, Anthony Smith 74); D2 Jeff Gentry 310, Parrish Wright 254 (Casie
R Skulley 193); D3 Clifton Boles 277, Kristen Mathews 190 (Dorothy
Burchett-Forney 166, James (Cornbread) Maxwell 138, James (Jay) Reagan 78);
D4 Anthony Boles 256, Winton E. Young 197 (John L Carman II 145, Aaron T.
Rohyans 128); D5 Eli Watson 366, Tanner Harvey 300 (Kyle Haney 135,
Elizabeth Boles 125). The page's start dates agree: the six members new in
2026 (McLerran, both 3rd District members, Anthony Boles, Harvey, Watson)
are each dated 9-1-2026, and the four re-elected carry earlier dates. The
page carries no modification date of its own."""
import re
from ._common import txt, member, district_number

COUNTY = "Clay"; FIPS = "027"
DOMAINS = ("claycountytngov.com", "claycountytn.gov")
URLS = ["https://www.claycountytngov.com/commissioners"]
SEATS = {str(i): 2 for i in range(1, 6)}
AT_LARGE = 0

PAGE_TITLE = "Clay County Commissioners"
SECTION_RE = re.compile(r'<section\s+data-test="page-section"')
H_RE = re.compile(r"<h([34])\b[^>]*>(.*?)</h\1>", re.S)
DISTRICT_RE = re.compile(r"^(\d{1,2})(?:st|nd|rd|th) District$")
DATE_RE = re.compile(r"<p\b[^>]*>\s*<em>\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})\s*</em>\s*</p>")
NAME_RE = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")


def parse(pages):
    page = pages[URLS[0]]
    s, e = page.find("<main"), page.find("</main>")
    if s < 0 or e < 0:
        raise ValueError("no <main> element")
    main = page[s:e]
    starts = [m.start() for m in SECTION_RE.finditer(main)]
    if not starts:
        raise ValueError("no page sections inside <main>")
    if H_RE.search(main, 0, starts[0]):
        raise ValueError("a heading sits before the first page section")
    titles, districts = 0, {}
    for k, at in enumerate(starts):
        end = main.find("</section>", at)
        if end < 0 or (k + 1 < len(starts) and end > starts[k + 1]):
            raise ValueError("page section %d does not close before the next one opens" % (k + 1))
        if H_RE.search(main, end, starts[k + 1] if k + 1 < len(starts) else len(main)):
            raise ValueError("a heading sits between page sections")
        sec = main[at:end]
        heads, names = [], []
        for m in H_RE.finditer(sec):
            level, text = m.group(1), txt(m.group(2))
            if level == "3":
                if text == PAGE_TITLE and k == 0:
                    titles += 1
                    continue
                d = DISTRICT_RE.match(text)
                if not d or district_number(text) != int(d.group(1)):
                    raise ValueError("section %d: an <h3> that is not 'Nth District': %r" % (k + 1, text))
                heads.append(d.group(1))
            else:
                if not NAME_RE.match(text) or re.search(r"\bvacan", text, re.I):
                    raise ValueError("section %d: an <h4> that is not a name: %r" % (k + 1, text))
                names.append(text)
        if not heads and not names:
            continue
        if len(heads) != 1:
            raise ValueError("section %d has district headings %s and names %s" % (k + 1, heads, names))
        n = heads[0]
        if not names:
            raise ValueError("District %s's section names nobody" % n)
        if n in districts:
            raise ValueError("District %s has two sections" % n)
        dates = DATE_RE.findall(sec)
        if len(dates) != len(names):
            raise ValueError("District %s: %d names but %d start-date blocks" % (n, len(names), len(dates)))
        districts[n] = [member(x) for x in names]
    if titles != 1:
        raise ValueError("the page title %r is not in the first section" % PAGE_TITLE)
    return {"districts": districts, "atLarge": []}
