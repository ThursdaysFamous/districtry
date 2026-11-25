#!/usr/bin/env python3
"""Battle Creek's nine city commissioners, from the city's own commission page.

THIS SOURCE WAS RECORDED AS BLOCKED AND WAS NOT. The first pass at Battle Creek
guessed a page id — /165/City-Commission — got HTTP 403 from it, and wrote "the
city's commission page answers 403 to this client" into four places. The real
page is /380/City-Commission and answers 200 with 160 KB. A 403 from a path you
invented is a fact about your guess, not about the city; the site's robots.txt
permits general crawling and its home page answers 200, both of which should
have made the 403 suspicious rather than conclusive.

THE COMMISSION IS NINE, NOT FIVE, AND THE FIRST DRAFT OF THIS FILE SHIPPED FIVE.
Reading only the cards that name a ward gave a `seats` of 5, which would have
had the card imply that a ward commissioner is the whole of a reader's city
representation. The city states the arithmetic in its own prose on the same
page: "made up of nine elected officials… Five ward commissioners representing
geographic districts… Three at-large commissioners serving the entire city…
The Mayor, elected citywide." So the PROSE and the CARD LIST are two witnesses
to one fact, and this refuses to write unless they agree — nine stated, nine
published, five of them wards.

THE MEMBER CARDS LEFT THE COMMISSION PAGE IN NOVEMBER 2026. Measured
2026-11-25: /380/City-Commission still carries the composition prose but no
member h-cards (the run of that week failed with 0 cards), and its "Meet Your
Commissioners" page (/1080) is photo links only. The same nine people, titles,
phones and shared contact form are on the city's staff directory department
"Mayor & City Commission" (PEOPLE below), which is where /1080's photos and
the old cards' profile links both lead. So the prose is read from PAGE and the
people from PEOPLE: two pages, one city, the same two witnesses.

EACH MEMBER IS ONE DIRECTORY ROW, WHICH IS WHY THIS IS SAFE TO PARSE. Every
person is one `<li class="list-group-item ...">` carrying its own profile link
(`employee?eid=N`) and name, a title ("Commissioner, Ward N" / "Mayor,
At-Large"), a `tel:` link and a contact link. The parser keys off that block
and never off document order — the directory lists the at-large seats and
wards interleaved (the old cards rendered wards 5, 2, 1, 3, 4). A flat read
that paired each name with the nearest preceding ward label would misplace
members. That is the Franklin County grid trap this project already has on
record, and the fix is the same: read each member's own block.

NO PER-MEMBER E-MAIL EXISTS AND NONE IS INVENTED. Each row's contact link
is the city's SHARED contact form — the identical href on all nine, with
only the visible label differing ("Contact form" on eight, "Email" on one). An
address common to every member belongs to the body, so it is hoisted like Grand
Rapids's switchboard; a member row never carries it. If the city ever publishes
distinct addresses the hrefs stop matching, the hoist is dropped and each row
carries its own — a page improvement must not fail the build.

WHAT THIS DELIBERATELY IGNORES: the COMMISSIONER field on the city's ward GIS
layer. Four of its five records were last edited in March 2023 and nothing in
the layer says whether a name is current. This page is what the city maintains
as people; the geometry is what it maintains as lines. Geometry from whatever
proves the lines, people from whatever the city maintains as people.
"""

import argparse
import html as htmllib
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED -- validate_workflow_deps)

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache", "mi_battle_creek_commission.json")

SITE = "https://www.battlecreekmi.gov"
PAGE = SITE + "/380/City-Commission"                       # the composition prose
PEOPLE = SITE + "/m/directory/department?did=31"          # the members
# shortcut: robots.txt states `Crawl-delay: 10` for `*` (read 2026-11-25); if the
# city raises it, raise this.
CRAWL_DELAY = 10
UA = "districtry/1.0 (civic data; +https://districtry.com)"

EXPECT_WARDS = ("1", "2", "3", "4", "5")
EXPECT_SEATS = 9

# One directory row. Non-greedy to the closing </li>, so rows cannot merge.
CARD_RE = re.compile(r'<li class="list-group-item[^"]*">(.*?)</li>', re.S)
NAME_RE = re.compile(r'<a href="([^"]*employee\?eid=\d+)"[^>]*>\s*(.*?)\s*</a>', re.S)
JOB_RE = re.compile(r'class="d-sm-block d-none">\s*(.*?)\s*</div>', re.S)
TEL_RE = re.compile(r'href="tel:([0-9+()\-. ]+),?"')
MAIL_RE = re.compile(r'<a href="((?:/formcenter/|mailto:)[^"]+)"')
WARD_RE = re.compile(r"\bWard\s*([1-9])\b", re.I)

# The city's own composition sentence, the second witness to `seats`.
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
         "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
STATED_TOTAL_RE = re.compile(r"made up of (\w+) elected officials", re.I)
STATED_WARD_RE = re.compile(r"(\w+) ward commissioners", re.I)
STATED_AL_RE = re.compile(r"(\w+) at-large commissioners", re.I)

# City Hall, printed on this page beside the meeting schedule.
OFFICE_LINES = ["10 N. Division St.", "Battle Creek, MI 49014"]
OFFICE_PHONE_RE = re.compile(r"Phone:\s*(269-966-3311)")


def fail(msg):
    print("battle-creek-commission-scraper: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def get(url):
    out = subprocess.run(["curl", "-sSL", "--fail", "--max-time", "120", "-A", UA, url],
                         check=True, capture_output=True)
    return out.stdout.decode("utf-8", "replace")


def text(s):
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def _phone(digits):
    d = re.sub(r"\D", "", digits)
    if len(d) == 11 and d.startswith("1"):
        d = d[1:]
    return "%s-%s-%s" % (d[:3], d[3:6], d[6:]) if len(d) == 10 else digits


def _abs(href):
    if not href:
        return None
    return SITE + href if href.startswith("/") else href


def parse(page):
    members = []
    for block in CARD_RE.findall(page):
        job = text(JOB_RE.search(block).group(1)) if JOB_RE.search(block) else ""
        if not job:
            continue                      # a row with no title slot is not a seat
        link = NAME_RE.search(block)
        name = text(link.group(2)) if link else ""
        if not name:
            fail("a directory row carries the title %r but no named profile link — "
                 "the page's markup has changed" % job)
        tel, mail = TEL_RE.search(block), MAIL_RE.search(block)
        ward = WARD_RE.search(job)
        members.append({
            "name": name,
            "role": job,
            "ward": ward.group(1) if ward else None,
            "phone": _phone(tel.group(1)) if tel else None,
            "profileUrl": _abs(htmllib.unescape(link.group(1))),
            "contactUrl": _abs(htmllib.unescape(mail.group(1))) if mail else None,
        })
    return members


def stated_composition(page):
    """The city's own arithmetic, read from its prose — the second witness."""
    flat = text(page)

    def word(rx, what):
        m = rx.search(flat)
        if not m:
            fail("the page no longer states %s in its own prose; that sentence is the "
                 "second witness to the seat count and this will not write without it"
                 % what)
        n = WORDS.get(m.group(1).lower())
        if n is None:
            fail("the page states %s as %r, which is not a number word this reads"
                 % (what, m.group(1)))
        return n

    return {"total": word(STATED_TOTAL_RE, "its total membership"),
            "wards": word(STATED_WARD_RE, "how many commissioners come from wards"),
            "atLarge": word(STATED_AL_RE, "how many commissioners are at-large")}


def main():
    argparse.ArgumentParser(description=__doc__,
                            formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    pages = {}
    for url in (PAGE, PEOPLE):
        require_robots_once(url, UA, label="mi-battle-creek-commission")
        if pages:
            time.sleep(CRAWL_DELAY)
        print("Fetching %s…" % url, file=sys.stderr)
        try:
            pages[url] = get(url)
        except Exception as exc:                              # noqa: BLE001
            fail("could not read %s: %s. NOTE: a 403 on some OTHER page id says "
                 "nothing about this one — the first pass at this city recorded "
                 "exactly that mistake." % (url, exc))
    if "list-group-item" not in pages[PEOPLE]:
        fail("%s no longer carries one directory row per person — the parser keys "
             "off that block, and guessing at document order is what the "
             "interleaved ward order punishes" % PEOPLE)

    members = parse(pages[PEOPLE])
    stated = stated_composition(pages[PAGE])

    # WITNESS 1 (the prose) against WITNESS 2 (the published cards).
    if stated["total"] != EXPECT_SEATS:
        fail("the city now states a %d-member commission where this expects %d — a "
             "charter change is a human's call, not a constant to edit past"
             % (stated["total"], EXPECT_SEATS))
    if stated["wards"] + stated["atLarge"] + 1 != stated["total"]:
        fail("the city's own sentence does not add up: %d ward + %d at-large + the "
             "mayor is not %d" % (stated["wards"], stated["atLarge"], stated["total"]))
    if len(members) != stated["total"]:
        fail("the page's prose states %d elected officials and it publishes %d cards"
             % (stated["total"], len(members)))

    ward_members = [m for m in members if m["ward"]]
    citywide = [m for m in members if not m["ward"]]
    if len(ward_members) != stated["wards"]:
        fail("%d cards name a ward, but the city states %d ward commissioners"
             % (len(ward_members), stated["wards"]))
    if len(citywide) != stated["atLarge"] + 1:
        fail("%d cards name no ward, but the city states %d at-large commissioners "
             "plus the mayor" % (len(citywide), stated["atLarge"]))
    if sum(1 for m in citywide if re.search(r"\bmayor\b", m["role"], re.I)
           and not re.search(r"\bvice\b", m["role"], re.I)) != 1:
        fail("the citywide seats do not name exactly one mayor: %s"
             % [m["role"] for m in citywide])

    wards = tuple(sorted(m["ward"] for m in ward_members))
    if wards != EXPECT_WARDS:
        fail("parsed wards %s, expected %s" % (list(wards), list(EXPECT_WARDS)))
    if len({m["name"] for m in members}) != len(members):
        fail("one person appears on two cards")
    withphone = [m for m in members if m["phone"]]
    if len(withphone) < len(members) - 1:
        fail("only %d of %d commissioners carry a phone number; the page published "
             "one for every seat when this was written" % (len(withphone), len(members)))

    # THE CONTACT LINK IS THE BODY'S WHILE IT IS IDENTICAL ON EVERY SEAT. If the
    # city ever publishes distinct addresses, keep them per member rather than
    # failing — a source improving must not break the build.
    contacts = {m["contactUrl"] for m in members if m["contactUrl"]}
    shared = contacts.pop() if len(contacts) == 1 and len(
        [m for m in members if m["contactUrl"]]) == len(members) else None
    if shared:
        for m in members:
            m.pop("contactUrl", None)

    office = {"label": "City Hall", "lines": list(OFFICE_LINES)}
    ph = OFFICE_PHONE_RE.search(text(pages[PAGE]))
    if ph:
        office["phone"] = ph.group(1)
    if any(m.get("phone") == office.get("phone") for m in members):
        fail("a commissioner's direct line is the city switchboard — that number "
             "belongs to the body and is hoisted, never repeated per member")

    for m in sorted(members, key=lambda x: (x["ward"] or "z", x["name"])):
        print("    %-18s %-24s %s" % ("Ward " + m["ward"] if m["ward"] else "Citywide",
                                      m["name"], m["phone"] or "(no phone)"),
              file=sys.stderr)

    payload = {"sourceUrl": PEOPLE, "seats": stated["total"], "members": members,
               "office": office}
    if shared:
        payload["contactUrl"] = shared
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    print("Wrote %s — %d of %d seats named (%d wards, %d citywide)"
          % (CACHE, len(members), stated["total"], len(ward_members), len(citywide)),
          file=sys.stderr)


if __name__ == "__main__":
    main()
