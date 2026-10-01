#!/usr/bin/env python3
"""
Scrape Racine Unified's Board of Education page — the nine districted seats,
the people in them, and the one seat the district itself declares vacant.

Pairs with build_rusd_school_board_districts.py, which builds the geometry
from RUSD's own ward composition. Geometry from what proves the lines, people
from what the district maintains as people.

THE PAGE IS AN APPTEGY/THRILLSHARE CMS and its content is not in the served
markup as elements — it is a JSON blob of HTML fragments inside a script. So
the read is: pull the fragments, pair each "Election District N" heading with
the fragment that follows it, and parse that fragment.

EACH SEAT STATES ITS OWN NUMBER AND THAT IS THE POINT. A fragment carries
"<strong>District N Schools</strong>" inside it, independently of the heading
above it. Pairing by ORDER alone is the Forest trap in a different vendor's
markup — one fragment inserted or removed and every seat below it is filed
under its neighbour's district, with nine real RUSD board members on the card
and up to eight of them in the wrong place. So the heading's number and the
fragment's own number are required to AGREE, and the scrape fails loudly when
they do not rather than shipping a plausible shift.

THE VACANCY IS TESTED ON BOTH SURFACES, the Florence rule. District 2 is
empty as of 2026-08-20 and the page says so twice: the seat's fragment opens
with an empty paragraph where the others carry a name, and a separate
"Notice of Vacancy: Election District 2" heading appears above. A seat with no
name and no notice, or a notice over a seat that has started naming somebody,
both fail — otherwise a parse that merely lost a name publishes a vacancy.

NAMES CARRY HONORIFICS AND ROLES IN ONE CELL: "Mrs. Sarah Walker Cleaveland,
Board Treasurer". The role is what follows the comma; the name is everything
before it, honorific included, exactly as RUSD prints it. THE E-MAIL IS NOT A
WITNESS FOR THE NAME — District 5's Ally Docksey files as allyson.docksey@ —
so no surname-agreement gate applies here.
"""

import json
import os
import re
import sys
import time
import urllib.request
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(SCRIPT_DIR, ".cache", "rusd_school_board_raw.json")

PAGE = "https://www.rusd.org/o/rusd/page/board-of-education"
UA = {"User-Agent": "districtry-wisconsin/1.0 (+https://districtry.com/wi/)"}

EXPECT_SEATS = [str(n) for n in range(1, 10)]
MIN_NAMED = 8          # RUSD declares one vacancy; a second is news, not routine
MIN_PHONES = 8
MIN_EMAILS = 8


def fetch(url, tries=4, timeout=90):
    last = None
    for i in range(tries):
        try:
            require_robots_once(url, UA["User-Agent"],
                                headers=UA, label="wi-rusd-school-board-scraper")
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as exc:                        # noqa: BLE001
            last = exc
            if i + 1 < tries:
                time.sleep(2 * (i + 1))
    raise SystemExit("fetch failed after %d tries: %s\n  %s" % (tries, url, last))


def unescape(s):
    return (s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'")
             .replace("&rsquo;", "’").replace("&lt;", "<").replace("&gt;", ">")
             .replace("&quot;", '"'))


def text_of(html):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html))).strip()


def main():
    argv = sys.argv[1:]
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT

    page = fetch(PAGE)
    blob = page.replace('\\"', '"').replace("\\\\", "\\")
    frags = re.findall(r'"html":"(.*?)"\}', blob)
    if len(frags) < 10:
        raise SystemExit("only %d content fragments on the board page — the CMS "
                         "payload has reshaped" % len(frags))

    # Headings that open a seat, and the vacancy notices, in page order.
    seats, notices = [], set()
    for i, f in enumerate(frags):
        t = text_of(f)
        m = re.fullmatch(r"Election District ([1-9])", t)
        if m:
            seats.append((m.group(1), i))
            continue
        m = re.search(r"Notice of Vacancy:\s*Election District ([1-9])", t)
        if m:
            notices.add(m.group(1))

    if [d for d, _ in seats] != EXPECT_SEATS:
        raise SystemExit("board page opens seats %s, expected %s"
                         % ([d for d, _ in seats], EXPECT_SEATS))

    members = {}
    for district, idx in seats:
        body = frags[idx + 1] if idx + 1 < len(frags) else ""
        # The seat's OWN statement of its number, independent of the heading.
        own = re.search(r"<strong>\s*District\s*([1-9])\s*Schools", body)
        if not own:
            raise SystemExit("the fragment under 'Election District %s' carries no "
                             "'District N Schools' label — cannot confirm which seat "
                             "it is, and order alone is not enough" % district)
        if own.group(1) != district:
            raise SystemExit(
                "heading says Election District %s, the fragment under it says "
                "District %s Schools — the fragments have shifted and pairing by "
                "order would file every seat below this one under its neighbour"
                % (district, own.group(1)))

        paras = re.findall(r"<p[^>]*>(.*?)</p>", body, re.S)
        head = text_of(paras[0]) if paras else ""
        rec = {}
        if head:
            strong = re.search(r"<strong>(.*?)</strong>", paras[0], re.S)
            label = text_of(strong.group(1)) if strong else head
            name, _, role = label.partition(",")
            rec["name"] = name.strip()
            if role.strip():
                rec["role"] = role.strip()
            phone = re.search(r"\(\d{3}\)\s*\d{3}-\d{4}", head)
            if phone:
                rec["phone"] = phone.group(0)
            email = re.search(r"[\w.+-]+@rusd\.org", head)
            if email:
                rec["email"] = email.group(0)
        term = re.search(r"Term ends ([A-Z][a-z]+ \d{4})", text_of(body))
        if term:
            rec["termExpires"] = term.group(1)
        members[district] = rec

    # The vacancy, on both surfaces.
    nameless = {d for d, r in members.items() if not r.get("name")}
    if nameless != notices:
        raise SystemExit(
            "seats with no name %s do not match the page's vacancy notices %s — a "
            "seat that lost its name to a parse is not a vacancy, and a notice over "
            "a seat that has started naming somebody is out of date"
            % (sorted(nameless), sorted(notices) or "none"))
    for d in nameless:
        members[d]["vacant"] = True

    named = [d for d, r in members.items() if r.get("name")]
    if len(named) < MIN_NAMED:
        raise SystemExit("only %d of 9 seats named (floor %d) — %s carry no name"
                         % (len(named), MIN_NAMED,
                            sorted(set(EXPECT_SEATS) - set(named))))
    phones = sum(1 for r in members.values() if r.get("phone"))
    emails = sum(1 for r in members.values() if r.get("email"))
    if phones < MIN_PHONES or emails < MIN_EMAILS:
        raise SystemExit("contact thinned: %d phones, %d e-mails (floors %d/%d)"
                         % (phones, emails, MIN_PHONES, MIN_EMAILS))

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump({"members": members, "sourceUrl": PAGE,
                   "vacancies": sorted(nameless)}, fh, indent=1, sort_keys=True)
    print("scraped %d seats (%d named, %d vacant by the district's own notice), "
          "%d phones, %d e-mails -> %s"
          % (len(members), len(named), len(nameless), phones, emails, out_path),
          file=sys.stderr)


if __name__ == "__main__":
    main()
