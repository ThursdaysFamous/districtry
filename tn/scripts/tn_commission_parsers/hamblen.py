"""Hamblen County elects one commissioner from each of 14 districts (the page:
"fourteen positions, which are elected by the citizens of Hamblen County to
represent each of the fourteen County Commission Districts").

The commission page (WordPress/Avada) lists every member as one
"fusion-person" block under the heading "County Commissioners": a
<span class="person-name"> name, a <span class="person-title"> reading
"District N Commissioner" (", Chair" after it for the chair), a mailto link,
and a text line "Email: ... Phone: ...". The district is read from the
member's own title, never from order, and every block's title must be in
that exact form.

E-mail: every member's address is the district's own county mailbox,
districtN@co.hamblen.tn.us, on the county's e-mail domain (the county's
Election Commission page gives its own and its absentee-ballot addresses on
the same domain). It is
recorded only when the mailto link and the printed "Email:" line agree and
the mailbox number is the district the block's own title names, so a
mailbox copied into the wrong block raises instead of shipping. The mailto
links are written with HTML character references and are decoded.

PRIVACY: every block also prints a per-member phone (tel: link and "Phone:"
line). Nothing on the page says they are county lines. They are recorded as
printed, under Adam's ruling of 2026-10-17 that a number a government
publishes beside an official ships whosever line it is; a block whose tel:
link dials something other than its "Phone:" line keeps that member's number
off the record. The County Mayor's office number the page gives as the
commission's point of contact (423-586-1931) and its fax are OFFICE_LINES and
never land on a member. The page prints no member address.

Role: "Chair" is recorded where the title prints it (Stan Harville,
District 10). The county's committee list effective September 2026 also
names Tim Horner Vice-Chairman, but the page does not, so it is not
recorded.

Currency: NO RESULTS of the 6 August 2026 election were found on any
government host. The Election Commission's page on hamblencountytn.gov
(read 2026-10-11) links only November 2026 material; the county site's
WordPress search, media listing and sitemaps (wp-sitemap.xml, its post,
page and download-category sitemaps, read 2026-10-11) carry no 2026 results
post or file, and the download categories "Election Commission" and "2026
Sample Ballots" list nothing publicly; and the Secretary of State's results
page (sos.tn.gov/elections/results) answered HTTP 403 to this project's
client and was not read.

The district pairing is confirmed by the county's GIS office instead. The
county's "GIS Coordinator" page (hamblencountytn.gov/gis-coordinator/) links
"Elected Officials", the Morristown-Hamblen GIS (owner MHGIS) web app
"Morristown-Hamblen Elected Representatives" on ArcGIS Online, whose map
reads the feature layer ElectionGeography_public/FeatureServer/2
(services.arcgis.com/xhDV83hFoiDFnMbw). Queried 2026-10-11 for
electedoffice = 'County Commissioner', it returns one record per district
1..14, "Hamblen County District N" with repname1 "Commissioner <Name>", and
names the same fourteen people in the same districts as this page (Leo
Shalhoup without "E." and "Jr"). The layer's data were last edited
2026-09-30; the records for Districts 1, 3, 6, 7, 8, 9, 11, 12 and 14 carry
that edit date, and those for Districts 2, 4, 5, 10 and 13 were last edited
in 2022 or 2023, i.e. members who sat before and sit again. That layer is
a county record dated after 1 September 2026 naming members by district;
it is hosted on Esri's ArcGIS Online, not on hamblencountytn.gov, and it
was read only as evidence (the parser reads this page).

Seating, all on hamblencountytn.gov: the commission page itself (article
modified 2026-09-29, Stan Harville shown as Chair; the agenda of the 3
September 2026 special-called meeting put the election of a chairman before
the new body, and the 24 September 2026 packet opens "Call to Order -
Chairman Stan Harville"); "Committee Membership - Effective September 2026"
(?ddownload=10704), which names the same fourteen people and "Chairman:
Stan Harville"; the 24 September 2026 commission packet (?ddownload=10716),
whose 14 September 2026 Future Growth committee minutes list all fourteen
present; and the 13 October 2026 committee packet (?ddownload=10777,
created 2026-10-09), whose committee rosters name the same people. None of
those documents names a district. What this does NOT establish: no
election results were compared, so that these fourteen are the August 2026
winners rests on the GIS edit of 30 September 2026 and the post-September
seating, not on the count."""
import re
from ._common import txt, mailtos, county_email, member, read_phones

COUNTY = "Hamblen"; FIPS = "063"
DOMAINS = ("hamblencountytn.gov", "co.hamblen.tn.us")
URLS = ["https://hamblencountytn.gov/county-commission/"]
SEATS = {str(i): 1 for i in range(1, 15)}
AT_LARGE = 0
# The County Mayor's office phone and fax, the commission's point of contact.
OFFICE_LINES = ("423-586-1931", "423-585-4699")

BLOCK = re.compile(r'<div class="fusion-person person\b')
NAME_RE = re.compile(r'<span class="person-name">(.*?)</span>', re.S)
TITLE_RE = re.compile(r'<span class="person-title">(.*?)</span>', re.S)
CONTENT_RE = re.compile(r'<div class="person-content[^"]*">(.*?)</div>', re.S)
TITLE_FORM = re.compile(r"^District (\d{1,2}) Commissioner(?:,\s*(Chair|Vice Chair))?$")
PRINTED = re.compile(r"Email:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+)")


def parse(pages):
    page = pages[URLS[0]]
    start = page.find("<h2>County Commissioners</h2>")
    if start < 0:
        raise ValueError("no 'County Commissioners' heading")
    blocks = BLOCK.split(page[start:])[1:]
    if not blocks or BLOCK.search(page[:start]):
        raise ValueError("member blocks missing, or one sits above the heading")
    districts = {}
    for b in blocks:
        nm, ti, co = NAME_RE.search(b), TITLE_RE.search(b), CONTENT_RE.search(b)
        if not nm or not ti or not co:
            raise ValueError("a member block without a name, title or contact line")
        name, title = txt(nm.group(1)), txt(ti.group(1))
        m = TITLE_FORM.match(title)
        if not m:
            raise ValueError("%r: title %r is not 'District N Commissioner'" % (name, title))
        d, role = m.group(1), m.group(2)
        if d in districts:
            raise ValueError("District %s appears twice" % d)
        linked = mailtos(b)
        printed = PRINTED.findall(txt(co.group(1)))
        if len(linked) != 1 or printed != linked:
            raise ValueError("%r: mailto %s and printed e-mail %s disagree" % (name, linked, printed))
        email = county_email(linked, DOMAINS)
        if email and email.lower() != "district%s@co.hamblen.tn.us" % d:
            raise ValueError("%r (District %s) carries %r, not that district's mailbox"
                             % (name, d, email))
        districts[d] = [member(name, role=role, email=email, phones=read_phones(b[:co.end()]))]
    return {"districts": districts, "atLarge": []}
