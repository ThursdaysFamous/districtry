"""Knox County Commission: 11 members, nine elected from single-member
districts 1-9 and two countywide ("At Large Seat 10" and "At Large Seat 11").
The commission's own WordPress site lists every member as one
<article class="... lsvr_person ...">: the name is the post title, and the
subtitle carries, in one <p>, any commission office ("Chair", "Vice-Chair"),
the seat ("6th District Commissioner" / "At Large Seat 10 Commissioner") and
the term ("2nd Term: 2024-2028"). Each article also carries a WordPress
category (lsvr_person_cat-district-commissioner or -at-large-commissioner),
which must agree with the subtitle, so neither is read from page order.

Terms are staggered: the August 2026 county general election filled Districts
3 and 7 and At-Large Seats 10 and 11 (terms 2026-2030); the other seven were
filled in 2024 (terms 2024-2028). Checked 2026-10-11 against the Knox County
Election Commission's official cumulative results for 6 August 2026
(knoxcounty.org/election/archive/2026-08-06/cumulative.pdf): the four winners
(Huckaby D3, Beeler D7, Cofer Seat 10, Holt Seat 11) are the four this page
lists with 2026-2030 terms.

Phones: the number in a member's "Phone" contact item is recorded as printed
(ten of the eleven print one), under Adam's ruling of 2026-10-17 that a
number a government publishes beside an official ships whosever line it is.
They are individual numbers (865-320-..., 865-203-...), with no label saying
they are office lines, and some are printed beside what is a residential
street address or a personal P.O. box. Only the "Phone" item is read; the
"Address" item is never read. The commission office's phone and fax are
OFFICE_LINES and never land on a member. E-mails are kept only on
knoxcounty.org."""
import re
from ._common import txt, mailtos, county_email, member, district_number, read_phones, Withheld

COUNTY = "Knox"; FIPS = "093"
DOMAINS = ("knoxcounty.org", "knoxcountytn.gov")
URLS = ["https://commission.knoxcountytn.gov/people/"]
SEATS = {str(i): 1 for i in range(1, 10)}
AT_LARGE = 2
# The commission office's phone and fax.
OFFICE_LINES = ("865-215-2534", "865-215-2038")

ROLE_LINE = re.compile(r"^(Chair(?:man|woman|person)?|Vice[- ]Chair(?:man|woman|person)?|"
                       r"Chair(?:man)? Pro[- ]Tem(?:pore)?)$", re.I)
TERM_LINE = re.compile(r"^\d+(?:st|nd|rd|th) Term:\s*\d{4}\s*[-–]\s*\d{4}$", re.I)
DISTRICT_LINE = re.compile(r"^(\d{1,2})(?:st|nd|rd|th) District Commissioner$", re.I)
AT_LARGE_LINE = re.compile(r"^At[- ]Large Seat (\d{1,2}) Commissioner$", re.I)
PROFILE = re.compile(r'href="(https://commission\.knoxcountytn\.gov/people/[a-z0-9-]+/)"')
PHONE_ITEM = re.compile(r'<li class="post__contact-item post__contact-item--phone"[^>]*>(.*?)</li>', re.S)


def _phones(b):
    """The numbers in the article's "Phone" contact items, in order."""
    out = []
    for item in PHONE_ITEM.findall(b):
        got = read_phones(item, strict=True)
        if isinstance(got, Withheld):
            return got
        out += got
    return out


def parse(pages):
    page = pages[URLS[0]]
    blocks = re.split(r"<article\b", page)[1:]
    districts, at_large = {}, []
    for b in blocks:
        head = b[:400]
        if "lsvr_person " not in head and "lsvr_person\"" not in head:
            continue
        if "lsvr_person_cat-commissioner" not in head:
            continue                      # a person on the site who is not a commissioner
        b = b.split("</article>", 1)[0]
        nm = re.search(r'<h2 class="post__title">(.*?)</h2>', b, re.S)
        sub = re.search(r'<p class="post__subtitle">(.*?)</p>', b, re.S)
        if not nm or not sub:
            raise ValueError("a commissioner article without a title or subtitle")
        name = txt(nm.group(1))
        parts = [txt(x) for x in re.split(r"<br\s*/?>", sub.group(1), flags=re.I)]
        parts = [x for x in parts if x]
        role, dist, seat = None, None, None
        for x in parts:
            if ROLE_LINE.match(x):
                if role:
                    raise ValueError("%r: two commission offices %r and %r" % (name, role, x))
                role = x
            elif TERM_LINE.match(x):
                pass
            elif DISTRICT_LINE.match(x):
                dist = DISTRICT_LINE.match(x).group(1)
                if district_number(x) != int(dist):
                    raise ValueError("%r: district label %r read two ways" % (name, x))
            elif AT_LARGE_LINE.match(x):
                seat = AT_LARGE_LINE.match(x).group(1)
            else:
                raise ValueError("%r: unrecognised subtitle line %r" % (name, x))
        if (dist is None) == (seat is None):
            raise ValueError("%r: subtitle %r names neither or both of a district and an at-large seat"
                             % (name, parts))
        cat_district = "lsvr_person_cat-district-commissioner" in head
        cat_at_large = "lsvr_person_cat-at-large-commissioner" in head
        if (dist is not None and not cat_district) or (seat is not None and not cat_at_large):
            raise ValueError("%r: subtitle %r disagrees with the article's category" % (name, parts))
        prof = PROFILE.search(b)
        email = county_email(mailtos(b), DOMAINS)
        rec = member(name, seat=("Seat " + seat) if seat else None, role=role, email=email,
                     profileUrl=prof.group(1) if prof else None, phones=_phones(b))
        if dist is not None:
            districts.setdefault(dist, []).append(rec)
        else:
            if seat not in ("10", "11"):
                raise ValueError("%r: at-large seat %s is not Seat 10 or 11" % (name, seat))
            at_large.append(rec)
    return {"districts": districts, "atLarge": at_large}
