"""Putnam County elects 24 commissioners, two from each of 12 districts (every
district race on the 6 August 2026 ballot was "VOTE FOR 2"; the ballot names
no seat or position, so no seat is recorded).

The county's commission page (Drupal) carries a "County Commissioners" view:
an accordion whose headers are `<h3 class="views-accordion-commissioners-
block-header">District N <p>area</p></h3>`, each followed by one <div> holding
that district's `views-row` entries, and each row a photo, a
`<div class="title">` with the member's name, a `<div class="phone">` and an
(empty) `<div class="email">`. A name is paired with the header of the
accordion panel it sits in; every row in a panel must carry exactly one
title, and a panel must hold the seats the county elects there, so nothing is
read from page order.

PRIVACY: the phone in each row is the member's own. The county's "COUNTY
COMMISSIONERS 8-14-2026" PDF (putnamcountytn.gov, created 2026-08-28) prints
21 of this page's 24 numbers beside the members' home street addresses and
personal e-mails (gmail, yahoo, an employer's domain), so they are personal
lines. Each row's "phone" field is recorded as printed, under Adam's ruling
of 2026-10-17 that a number a government publishes beside an official ships
whosever line it is. That PDF is not read by this parser. The page prints no
address. The e-mail fields on the page are empty on 2026-10-11; if one fills
in, only an address on putnamcountytn.gov is kept.

Currency: checked 2026-10-11 against the Putnam County Election Commission's
"Election Summary Report" for 6 August 2026 on the county's own host
(putnamcountytn.gov/electionresults/2026-08/, report time 8/13/2026
8:17:47 AM, 21 of 21 precincts reported; the report is not labelled official
or unofficial). In each of the 12 "County Commission District N" contests the
two highest totals are the two names this page lists for that district.
Ballot forms differ only by initials and full names (Terry C Randolph,
Jonathan A. D. Williams, Stacye L Choate, Junior C. Phipps, Robert E Riddle,
David K. Andrews). The closest seat is District 1, where Jonathan A. D.
Williams (676) finished nine votes ahead of Morgan Franklin (667). The page
names no chair, so no role is recorded."""
import re
from ._common import txt, mailtos, county_email, district_number, member, read_phones

COUNTY = "Putnam"; FIPS = "141"
DOMAINS = ("putnamcountytn.gov",)
URLS = ["https://putnamcountytn.gov/county-commission"]
SEATS = {str(i): 2 for i in range(1, 13)}
AT_LARGE = 0

HEADER = re.compile(r'<h3 class="views-accordion-commissioners-block-header">(.*?)</h3>', re.S)
ROW = re.compile(r'<div class="views-row\b')
LABEL = re.compile(r"^District (\d{1,2})\b")


def parse(pages):
    page = pages[URLS[0]]
    view = re.search(r'<div class="view view-commissioners\b', page)
    if not view:
        raise ValueError("no commissioners view on the page")
    content = page[view.start():]
    stop = content.find('<div id="navigation"')
    if stop < 0:
        raise ValueError("cannot find where the commissioners view ends")
    content = content[:stop]
    heads = list(HEADER.finditer(content))
    if not heads:
        raise ValueError("no 'District N' accordion headers in the view")
    if ROW.search(content, 0, heads[0].start()):
        raise ValueError("a commissioner row sits before the first District header")
    districts = {}
    for k, h in enumerate(heads):
        # The header's own text is "District N" followed by a <p> naming the area.
        label = txt(re.sub(r"<p\b.*?</p>", " ", h.group(1), flags=re.S))
        m = LABEL.match(label)
        if not m or label != "District %s" % m.group(1) or district_number(label) != int(m.group(1)):
            raise ValueError("accordion header %r is not 'District N'" % txt(h.group(1)))
        n = m.group(1)
        if n in districts:
            raise ValueError("District %s has two headers" % n)
        panel = content[h.end():heads[k + 1].start() if k + 1 < len(heads) else len(content)]
        rows = ROW.split(panel)[1:]
        seats = []
        for r in rows:
            titles = re.findall(r'<div class="title">(.*?)</div>', r, re.S)
            if len(titles) != 1:
                raise ValueError("District %s: a row with %d name fields" % (n, len(titles)))
            name = txt(titles[0])
            if re.search(r"\bvacan", name, re.I) or not re.fullmatch(r"[A-Z][A-Za-z.'’ -]+", name):
                raise ValueError("District %s: %r does not look like a name" % (n, name))
            em = re.search(r'<div class="email">(.*?)</div>', r, re.S)
            addrs = mailtos(em.group(1)) + re.findall(r"[\w.+-]+@[\w.-]+\.\w+", txt(em.group(1))) if em else []
            ph = re.findall(r'<div class="phone">(.*?)</div>', r, re.S)
            if len(ph) > 1:
                raise ValueError("District %s: %r's row has %d phone fields" % (n, name, len(ph)))
            seats.append(member(name, email=county_email(addrs, DOMAINS),
                                phones=read_phones(ph[0], strict=True) if ph else None))
        if len(seats) != SEATS.get(n):
            raise ValueError("District %s panel has %d rows, the county elects %s"
                             % (n, len(seats), SEATS.get(n)))
        districts[n] = seats
    return {"districts": districts, "atLarge": []}
