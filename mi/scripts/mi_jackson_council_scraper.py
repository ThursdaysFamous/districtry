#!/usr/bin/env python3
"""Jackson's Mayor and six ward councilmembers, from the city's own pages.

TWO WITNESSES FOR EVERY NAME. The council page (/289) lists the Mayor and one
"City Councilmember <name> (Ward N)" line per ward. Each ward then has a page of
its own (/498, /499, /500, /504, /511, /512), and each of those carries a
"Contact Us" block naming the member, their seat, a phone number and an e-mail
link. This reads both and refuses to write unless every ward page names the
same person the council page puts in that ward, so a ward page left behind
after an election fails the run rather than shipping a former member.

THE WARD PAGE IDS ARE NOT SEQUENTIAL. They are the city's own, read from its
navigation on 2026-09-29, and they are checked against the council page's own
links on every run, so a page the city moves fails here rather than 404ing on
a card.

A DECOY E-MAIL LINK SITS ON THE WARD 3 PAGE. Its contact block carries two
mailto links: an EMPTY one addressed to a former Ward 3 member, and the member's
own, labelled "EMAIL". A reader cannot see or click the empty one, and taking
the first mailto in the block would ship the wrong person's address. So only a
link with visible content (text or an image) counts, and a block with more than
one such link fails the run.

WHAT IS NOT KEPT. Two ward pages print a street address beside the member's
name. Nothing on the page says whether it is an office or a home, so no
per-member address ships; City Hall's address, which the page prints as the
city's, is kept for the body.

THE NAME IS A HEADING BUT NOT ALWAYS THE SAME ONE: Ward 4 sets it as an h2 where
the other pages use an h3, beside an h3 that holds only the photograph.

THE HOST RESETS CONNECTIONS NOW AND THEN (measured 2026-09-29 from this
project's sandbox: two resets in eight requests), so every fetch retries.
"""

import argparse
import html as htmllib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
CACHE = os.path.join(HERE, ".cache", "mi_jackson_council.json")

SITE = "https://www.cityofjackson.org"
INDEX = SITE + "/289/Mayor-City-Council-City-Manager"
MAYOR_PAGE = SITE + "/291/Mayors-Office"
WARD_PAGES = {
    "1": SITE + "/498/Ward-1",
    "2": SITE + "/499/Ward-2",
    "3": SITE + "/500/Ward-3",
    "4": SITE + "/504/Ward-4",
    "5": SITE + "/511/Ward-5",
    "6": SITE + "/512/Ward-6",
}
USER_AGENT = "districtry/1.0 (+https://districtry.com/mi/)"

EXPECT_WARDS = ("1", "2", "3", "4", "5", "6")

WIDGET_RE = re.compile(r'<li class="InfoAdvanced widgetItem[^"]*">(.*?)</li>', re.S)
# The name is a heading, and not always the same one: Ward 4 sets it as an h2
# where the others use h3, beside an h3 holding only the photograph.
HEAD_RE = re.compile(r"<h([2-4])[^>]*>(.*?)</h\1>", re.S)
P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.S)
MAILTO_RE = re.compile(r'<a\b[^>]*href="mailto:([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)
PHONE_RE = re.compile(r"^\(?(\d{3})\)?[\s.-]*(\d{3})[\s.-]*(\d{4})$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
INDEX_MAYOR_RE = re.compile(r"^Mayor\s+(.+)$")
INDEX_MEMBER_RE = re.compile(r"^City Councilmember\s+(.+?)\s*\((Ward\s+([1-9])[^)]*)\)$")


def fail(msg):
    print("jackson-council-scraper: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def get(url):
    out = subprocess.run(["curl", "-sSL", "--fail", "--max-time", "120",
                          "--retry", "4", "--retry-all-errors", "--retry-delay", "3",
                          "-A", USER_AGENT, url],
                         check=True, capture_output=True)
    return out.stdout.decode("utf-8", "replace")


def text(s):
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def phone(s):
    m = PHONE_RE.match(s.strip())
    return "%s-%s-%s" % m.groups() if m else None


def content_lines(page):
    """The text of the page's own content column, one line per element."""
    i = page.find('id="moduleContent"')
    if i < 0:
        fail("the page carries no moduleContent column — the site's template changed")
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", page[i:], flags=re.S)
    lines = htmllib.unescape(re.sub(r"<[^>]+>", "\n", body)).split("\n")
    return [re.sub(r"\s+", " ", l).strip() for l in lines if l.strip()]


def read_index(page):
    """Witness 1: the council page's list of who holds each seat."""
    mayor, wards = None, {}
    for line in content_lines(page):
        if line == "Meetings":
            break                          # the list ends where the page moves on
        m = INDEX_MAYOR_RE.match(line)
        if m and mayor is None:
            mayor = m.group(1)
            continue
        m = INDEX_MEMBER_RE.match(line)
        if m:
            if m.group(3) in wards:
                fail("the council page names two members for Ward %s" % m.group(3))
            wards[m.group(3)] = {"name": m.group(1), "seatText": m.group(2)}
    if not mayor:
        fail("the council page no longer names a Mayor in its list")
    if tuple(sorted(wards)) != EXPECT_WARDS:
        fail("the council page lists wards %s, expected %s — a ward added or removed "
             "is a charter change and a human's call" % (sorted(wards), list(EXPECT_WARDS)))
    for w, url in WARD_PAGES.items():
        path = url[len(SITE):]
        if ('href="%s"' % path) not in page:
            fail("the council page no longer links %s for Ward %s — the city moved the "
                 "page, and the card links it" % (path, w))
    return mayor, wards


def contact_block(page, role_rx, where):
    """The one Contact Us block on a page whose seat line matches `role_rx`."""
    found = []
    for block in WIDGET_RE.findall(page):
        paras = [text(p) for p in P_RE.findall(block)]
        if any(re.search(role_rx, p) for p in paras):
            found.append((block, paras))
    if len(found) != 1:
        fail("%s carries %d contact blocks for this seat, expected exactly one"
             % (where, len(found)))
    block, paras = found[0]
    names = [text(h) for _lvl, h in HEAD_RE.findall(block) if text(h)]
    if len(names) != 1:
        fail("%s's contact block names %d people (%s), expected one"
             % (where, len(names), names))
    role = next(p for p in paras if re.search(role_rx, p))
    phones = [phone(p) for p in paras if phone(p)]
    if len(phones) > 1:
        fail("%s's contact block prints %d phone numbers" % (where, len(phones)))
    # ONLY A LINK A READER CAN SEE COUNTS. The Ward 3 block carries an empty
    # mailto to a former member beside the member's own labelled one.
    visible = [(addr.strip(), inner) for addr, inner in MAILTO_RE.findall(block)
               if text(inner) or re.search(r"<img\b", inner, re.I)]
    if len(visible) > 1:
        fail("%s's contact block carries %d visible e-mail links: %s"
             % (where, len(visible), [a for a, _ in visible]))
    email = None
    if visible:
        email = visible[0][0]
        if not EMAIL_RE.match(email):
            fail("%s links an e-mail address this does not recognise: %r" % (where, email))
    return {"name": names[0], "seat": role, "phone": phones[0] if phones else None,
            "email": email}


def read_office(page):
    """City Hall's address and switchboard, from the page's own Contact Us list.

    The list is one widget item PER LINE ("City Hall", the street, the city, the
    phone), so it is read as the three items that follow the "City Hall" one.
    """
    items = [text(b) for b in WIDGET_RE.findall(page)]
    try:
        i = items.index("City Hall")
    except ValueError:
        fail("no City Hall item in the council page's Contact Us list")
    street, city, ph = (items[i + 1:i + 4] + ["", "", ""])[:3]
    phm = re.match(r"Phone:\s*(\d{3}-\d{3}-\d{4})$", ph)
    if not re.match(r"^\d+ .+", street) or not re.match(r"^Jackson, Michigan \d{5}$", city) \
            or not phm:
        fail("the City Hall lines no longer read as a street, a city and a phone: %r"
             % [street, city, ph])
    return {"label": "City Hall", "lines": [street, city], "phone": phm.group(1)}


def same(a, b):
    return re.sub(r"\s+", " ", a).strip().lower() == re.sub(r"\s+", " ", b).strip().lower()


def main():
    argparse.ArgumentParser(description=__doc__,
                            formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
    from scraper_common import require_robots_allowed
    print("  robots: %s" % require_robots_allowed(INDEX, USER_AGENT,
                                                  label="jackson-council-scraper"),
          file=sys.stderr)

    try:
        index = get(INDEX)
    except Exception as exc:                                  # noqa: BLE001
        fail("could not read %s: %s" % (INDEX, exc))
    mayor_name, listed = read_index(index)
    office = read_office(index)

    members = []
    for w in EXPECT_WARDS:
        url = WARD_PAGES[w]
        try:
            page = get(url)
        except Exception as exc:                              # noqa: BLE001
            fail("could not read %s: %s" % (url, exc))
        rec = contact_block(page, r"\bCouncilmember,\s*Ward\s*%s\b" % w, "the Ward %s page" % w)
        # WITNESS 2 against WITNESS 1.
        if not same(rec["name"], listed[w]["name"]):
            fail("the Ward %s page names %r and the council page names %r — one of the "
                 "city's two pages is out of date, and this will not guess which"
                 % (w, rec["name"], listed[w]["name"]))
        rec.update(ward=w, profileUrl=url)
        members.append(rec)

    try:
        mpage = get(MAYOR_PAGE)
    except Exception as exc:                                  # noqa: BLE001
        fail("could not read %s: %s" % (MAYOR_PAGE, exc))
    mayor = contact_block(mpage, r"^Mayor of Jackson$", "the Mayor's page")
    if not same(mayor["name"], mayor_name):
        fail("the Mayor's page names %r and the council page names %r"
             % (mayor["name"], mayor_name))
    mayor.update(ward=None, seat="Mayor", profileUrl=MAYOR_PAGE)
    members.append(mayor)

    if len({m["name"] for m in members}) != len(members):
        fail("one person appears in two seats")
    for m in members:
        if m["phone"] and m["phone"] == office["phone"]:
            fail("%s's direct line is the City Hall switchboard, which belongs to the "
                 "body" % m["name"])
    withphone = sum(1 for m in members if m["phone"])
    if withphone < len(members) - 1:
        fail("only %d of %d members carry a phone number; every page printed one "
             "when this was written" % (withphone, len(members)))

    for m in members:
        print("    %-9s %-20s %-13s %s" % ("Ward " + m["ward"] if m["ward"] else "Citywide",
                                          m["name"], m["phone"] or "(no phone)",
                                          m["email"] or "(no e-mail)"), file=sys.stderr)

    payload = {"sourceUrl": INDEX, "seats": len(members), "members": members,
               "office": office}
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    print("Wrote %s — %d seats, %d wards and the Mayor"
          % (CACHE, len(members), len(members) - 1), file=sys.stderr)


if __name__ == "__main__":
    main()
