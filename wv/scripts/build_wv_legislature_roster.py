#!/usr/bin/env python3
"""
Build the West Virginia Senate and House of Delegates rosters (district ->
current officeholders) as same-origin app-data files, from the Legislature's
own member lists, so the wv-senate and wv-house cards join a small roster
instead of reaching a third-party host at click time.

index.html's wv-senate and wv-house layers fetch data/app/wv-senate-members.json
and wv-house-members.json lazily on first click and join them to the pre-built
district maps by district number. A weekly GitHub Action
(.github/workflows/update-wv-legislature-roster.yml) reruns this script and
opens a pull request when a roster changes, so officeholder data gets a human
look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-10-29. The Legislature publishes one
roster page per chamber, www.wvlegislature.gov/Senate1/roster.cfm and
www.wvlegislature.gov/House/roster.cfm. Each prints one table row per member:
the name, linked to the member's own page, the party, the district, the
Capitol office's room and building, its telephone and the member's e-mail
address. That day the Senate's held 34 rows, two for each of its 17 districts,
and the House's 100 rows, one for each of its 100 districts. Every address on
both pages was the Capitol's own (1900 Kanawha Blvd. E., Charleston), and the
script stops if a row prints any other, rather than ship an address that could
be a home.

WHAT IS READ, AND WHAT IS NEVER READ. The Senate's district column also prints
each senator's home county, and a further column the counties the district
touches; neither is read. Nothing else on either page names where a member
lives.

THE SENATE ELECTS TWO MEMBERS FROM EACH DISTRICT (W. Va. Const. art. VI, sec. 4),
each for a four-year term, one of the two every two years. So the Senate file is
not the one-member shape the fleet's chamber card reads: each district carries
a `members` list of the two, and `seats` 2, and the app's own Senate layer draws
both. A district with fewer than two senators on the page gets an `asOf` date
and a card saying how many are listed; nothing says a seat is vacant unless the
page does.

THE E-MAIL ADDRESS ships as printed, under the fleet's rule since 2026-10-17
("E-mails too"): an address a government source prints in one official's own
entry is that official's. An address printed for two or more members would be
an office's and ships on no member's row. The Capitol telephone rides the
Capitol office block, since it is the office's line: on 2026-10-29 three
House numbers were printed beside two delegates each.

ROBOTS. The host's robots.txt is read before the first fetch, with the
User-Agent the fetches send. Read 2026-10-29: www.wvlegislature.gov disallows
21 directories and none this script reads, and states no Crawl-delay. The two
pages are fetched one second apart.

Honesty: names are never guessed. A district the page names nobody for gets a
dated record naming nobody; a row this script cannot read stops the build.

Usage:
    python3 wv/scripts/build_wv_legislature_roster.py [output_dir]
    python3 wv/scripts/build_wv_legislature_roster.py --save DIR [output_dir]
    python3 wv/scripts/build_wv_legislature_roster.py --offline DIR [output_dir]

--save writes both pages into DIR (senate-roster.html, house-roster.html);
--offline reads them back instead of fetching.
"""

import datetime
import html as html_module
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

USER_AGENT = "districtry/1.0 (+https://districtry.com/wv/)"
HEADERS = {"User-Agent": USER_AGENT}
PACE_SECONDS = 1.0
ATTEMPTS = 3
RETRY_SECONDS = 5.0

BASE = "https://www.wvlegislature.gov"
CAPITOL_STREET = "1900 Kanawha Blvd. E."
CAPITOL_CITY = "Charleston, WV 25305"

# `seats` is the number of districts; `per_district` how many members each
# elects. Floors catch a truncated page or a layout change while tolerating real
# vacancies: every seat in both chambers was named on 2026-10-29.
CHAMBERS = {
    "S": {"out": "wv-senate-members.json", "label": "Senate", "seats": 17,
          "per_district": 2, "expected": 30, "page": BASE + "/Senate1/roster.cfm",
          "save": "senate-roster.html", "body": "The West Virginia Senate"},
    "H": {"out": "wv-house-members.json", "label": "House", "seats": 100,
          "per_district": 1, "expected": 90, "page": BASE + "/House/roster.cfm",
          "save": "house-roster.html", "body": "The West Virginia House of Delegates"},
}
# A field every named member carried on 2026-10-29. One going missing is the
# Brown County shape: the row count holds and the contact goes.
MIN_FIELD_SHARE = 0.9

PARTY_NAMES = {"Republican": "Republican", "Democrat": "Democratic",
               "Democratic": "Democratic", "Independent": "Independent",
               "Libertarian": "Libertarian", "Mountain": "Mountain"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\(\d{3}\) \d{3}-\d{4}$")
ROW_RE = re.compile(r'<tr valign="top">(.*?)</tr>', re.S | re.I)
TD_RE = re.compile(r'<td class="tdborder">(.*?)</td>', re.S | re.I)
LINK_RE = re.compile(r'href="(lawmaker\.cfm\?member=[^"]+)"[^>]*style="vertical-align:top">([^<]+)</a>', re.I)
MAIL_RE = re.compile(r'href="mailto:\s*([^"]+)"', re.I)


def fetch(url):
    require_robots_once(url, USER_AGENT, headers=HEADERS, label="wv-legislature-roster")
    last = None
    for attempt in range(ATTEMPTS):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            time.sleep(PACE_SECONDS)
            return body
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(RETRY_SECONDS * (attempt + 1))
    raise RuntimeError("could not read %s: %s" % (url, last))


def _text(fragment):
    """A cell's text with tags turned into line breaks, entities decoded."""
    s = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html_module.unescape(s)
    return [" ".join(line.split()) for line in s.split("\n") if line.strip()]


def _member_url(href, page):
    path = urllib.parse.urljoin(page, href)
    parts = urllib.parse.urlsplit(path)
    query = urllib.parse.quote(urllib.parse.unquote(parts.query), safe="=&")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))


def parse(page_html, chamber):
    """Every row of one chamber's roster page as (district, member record)."""
    cfg = CHAMBERS[chamber]
    rows = ROW_RE.findall(page_html)
    out = []
    for row in rows:
        tds = TD_RE.findall(row)
        link = LINK_RE.search(tds[0]) if tds else None
        if len(tds) != 6 or not link:
            raise RuntimeError("%s: a row does not read as six cells with a "
                               "member link: %r" % (cfg["label"], row[:200]))
        name = " ".join(html_module.unescape(link.group(2)).split())
        party_raw = " ".join(_text(tds[1]))
        if party_raw not in PARTY_NAMES:
            raise RuntimeError("%s: %s's party reads %r, which this script does "
                               "not know" % (cfg["label"], name, party_raw))
        if chamber == "S":
            district_cell, address_cell, contact_cells = tds[2], tds[4], [tds[5]]
        else:
            district_cell, address_cell, contact_cells = tds[2], tds[3], [tds[4], tds[5]]
        # the Senate's district cell is "03<br>Wood": the second line is the
        # senator's home county, which is not read
        district_text = _text(district_cell)
        if not district_text or not re.match(r"^\d{1,3}$", district_text[0]):
            raise RuntimeError("%s: %s's district reads %r" % (cfg["label"], name, district_text))
        district = int(district_text[0])
        if not 1 <= district <= cfg["seats"]:
            raise RuntimeError("%s: %s's district %d is not one of 1-%d"
                               % (cfg["label"], name, district, cfg["seats"]))
        address = _text(address_cell)
        if len(address) != 3 or address[1] != CAPITOL_STREET or address[2] != CAPITOL_CITY:
            raise RuntimeError("%s: %s's address is not the Capitol's (%r); stopping "
                               "rather than ship an address that could be a home"
                               % (cfg["label"], name, address))
        email = phone = None
        for cell in contact_cells:
            mail = MAIL_RE.search(cell)
            if mail:
                email = mail.group(1).strip()
            for line in _text(cell):
                if PHONE_RE.match(line):
                    phone = line
        if email and not EMAIL_RE.match(email):
            raise RuntimeError("%s: %s's e-mail address reads %r" % (cfg["label"], name, email))
        office = [address[0], address[1], address[2]]
        if phone:
            office.append("Phone: " + phone)
        rec = {"name": name, "party": PARTY_NAMES[party_raw],
               "url": _member_url(link.group(1), cfg["page"]),
               "capitolOffice": office}
        if email:
            rec["email"] = email
        out.append((district, rec))
    return out


def build(chamber, page_html, today):
    cfg = CHAMBERS[chamber]
    rows = parse(page_html, chamber)
    if len(rows) < cfg["expected"]:
        raise RuntimeError("%s: only %d members read, below the floor of %d"
                           % (cfg["label"], len(rows), cfg["expected"]))
    # an e-mail address printed for two members is an office's
    by_mail = {}
    for _, rec in rows:
        if rec.get("email"):
            by_mail.setdefault(rec["email"].lower(), []).append(rec)
    for recs in by_mail.values():
        if len(recs) > 1:
            for rec in recs:
                rec.pop("email", None)
    by_district = {}
    for district, rec in rows:
        by_district.setdefault(district, []).append(rec)
    roster = {}
    per = cfg["per_district"]
    for d in range(1, cfg["seats"] + 1):
        members = by_district.get(d, [])
        if len(members) > per:
            raise RuntimeError("%s district %d lists %d members, more than the %d it elects"
                               % (cfg["label"], d, len(members), per))
        members.sort(key=lambda r: r["name"].split()[-1])
        if per == 1:
            roster[str(d)] = members[0] if members else {"asOf": today, "sourceUrl": cfg["page"]}
        else:
            rec = {"seats": per, "members": members}
            if len(members) < per:
                rec["asOf"] = today
                rec["sourceUrl"] = cfg["page"]
            roster[str(d)] = rec
    named = [rec for _, rec in rows]
    for field in ("email", "capitolOffice", "url"):
        share = sum(1 for r in named if r.get(field)) / float(len(named))
        if share < MIN_FIELD_SHARE:
            raise RuntimeError("%s: only %.0f%% of members carry %s" % (cfg["label"], 100 * share, field))
    return roster, len(rows)


def main(argv):
    save_dir = offline_dir = None
    args = list(argv)
    if "--save" in args:
        i = args.index("--save")
        save_dir = args[i + 1]
        del args[i:i + 2]
    if "--offline" in args:
        i = args.index("--offline")
        offline_dir = args[i + 1]
        del args[i:i + 2]
    out_dir = args[0] if args else DEFAULT_OUT_DIR
    today = datetime.date.today().isoformat()
    for chamber, cfg in CHAMBERS.items():
        if offline_dir:
            with open(os.path.join(offline_dir, cfg["save"]), encoding="utf-8") as f:
                page = f.read()
        else:
            page = fetch(cfg["page"])
            if save_dir:
                os.makedirs(save_dir, exist_ok=True)
                with open(os.path.join(save_dir, cfg["save"]), "w", encoding="utf-8") as f:
                    f.write(page)
        roster, count = build(chamber, page, today)
        path = os.path.join(out_dir, cfg["out"])
        with open(path, "w", encoding="utf-8") as f:
            json.dump(roster, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("Wrote %s (%d members across %d districts)" % (path, count, cfg["seats"]))


if __name__ == "__main__":
    main(sys.argv[1:])
