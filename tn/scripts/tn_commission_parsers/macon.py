"""Macon County's commission has 20 members, two from each of 10 districts,
as the county's August 2026 results hold them. No seat is called by a letter
or number, so no seat is recorded.

THE COUNTY HAS TWO COMMISSION PAGES AND THIS IS THE CURRENT ONE. The County
Commission page (government/county_commission/index.php, a Revize site) is a
table with one row per member: "District N - Name" in the first cell, the
member's home address in the second (NEVER read) and a telephone in the third.
The county's other page, government/county_commission/commissioner_list.php,
still lists the 2022-2026 commission on 2026-10-26 and differs in Districts 2,
3, 7, 8 and 9; it is not read. This page is taken as current on the evidence
below, not on its look. A name is paired with the district in its own cell;
nothing is read from order, and each district must hold exactly the two seats
the county elects there.

PRIVACY: each row prints one telephone number beside the member. Under Adam's
ruling of 2026-10-17 that a number a government publishes beside an official
ships whosever line it is, it is read from the row's third cell into `phone`,
as printed. The address cell is never read. The page prints no e-mail address.

Currency, checked 2026-10-26: every member on this page is a winner of the
6 August 2026 election in the district the page gives, by the Macon County
Election Commission's "Election Summary Report" of the 2026 State Primary and
County General (10 of 10 precincts, run 11 August 2026, marked "Final" by
hand), linked as "Unofficial Results for August 6, 2026" from the election
administrator's page on maconcountytn.gov and served from cms2.revize.com,
whose robots.txt permits the read. Two are elected in each district: District 1
Phillip Snow and Todd Gentry; District 2 Maverick Hesson and Keith Newberry;
District 3 Aaron Shipley and Caleb Fleming; District 4 Billy A Wilmore and
Justin Dyer; District 5 Barry Marshall and Dan Hill; District 6 Michael
Slayton and Tony W. Wix; District 7 Joshua Eakles and Barry King; District 8
Lisa Spivey and Kristie Turner Doss; District 9 Jason Brawner and Cameron
Roberts; District 10 Helen Hesson and Larry West (the only two candidates).
The commission's Committee of the Whole minutes of 8 September 2026 (posted
14 October) say "Commissioners were sworn in" and list 17 of the 20 present
(Dan Hill, Helen Hesson and Larry West are not listed), without districts; none
of the eight members only the older page names appears in them. Those minutes
record a chairman (the County Mayor, who holds no seat) and a vice-chairman;
the page names neither role, so none is recorded. The county's October agendas
carry an item "Commissioner Position" under the County Mayor whose meaning is
not established; the next reading of the October minutes should settle it.
Names are kept as the page prints them.

Held until then: on 2026-10-13 and 2026-10-15 the two pages disagreed and
nothing published said which was current."""
import re
from ._common import txt, district_number, member, read_phones

COUNTY = "Macon"; FIPS = "111"
DOMAINS = ("maconcountytn.gov",)
URLS = ["https://maconcountytn.gov/government/county_commission/index.php"]
SEATS = {str(n): 2 for n in range(1, 11)}
AT_LARGE = 0
OFFICE_LINES = ()

ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S)
CELL_RE = re.compile(r"<td\b[^>]*>(.*?)</td>", re.S)
FIRST_RE = re.compile(r"^District (\d{1,2}) - (.+)$")


def parse(pages):
    page = pages[URLS[0]]
    start = page.find('class="subheader"')
    if start < 0 or "Commissioners" not in txt(page[start:start + 200]):
        raise ValueError("no 'Commissioners' subheader on the County Commission page")
    end = page.find("</table>", start)
    if end < 0:
        raise ValueError("no table after the 'Commissioners' subheader")
    districts = {}
    for row in ROW_RE.findall(page[start:end]):
        cells = CELL_RE.findall(row)
        if len(cells) != 3:
            raise ValueError("a commissioner row has %d cells, not 3" % len(cells))
        first = txt(cells[0])
        m = FIRST_RE.match(first)
        if not m or district_number("District " + m.group(1)) != int(m.group(1)):
            raise ValueError("row %r is not 'District N - Name'" % first)
        n, name = m.group(1), m.group(2).strip()
        if re.search(r"\bvacan", name, re.I) or not re.fullmatch(r"[A-Z][A-Za-z.'’ -]+", name):
            raise ValueError("District %s: %r does not look like a name" % (n, name))
        districts.setdefault(n, []).append(member(name, phones=read_phones(cells[2])))
    for n, want in SEATS.items():
        if len(districts.get(n, [])) != want:
            raise ValueError("District %s: the page names %d, the county elects %d"
                             % (n, len(districts.get(n, [])), want))
    extra = set(districts) - set(SEATS)
    if extra:
        raise ValueError("the page names districts the county does not have: %s" % sorted(extra))
    return {"districts": districts, "atLarge": []}
