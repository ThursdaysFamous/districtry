#!/usr/bin/env python3
"""Read every Kentucky county's elected officials from the Department for Local Government.

WHERE THE NAMES COME FROM. The Department for Local Government (DLG) keeps a
county directory at kydlgweb.ky.gov/Counties/. Each county has one page,
16_CountyView.cfm?County=<Name>, carrying the county's website, its form of
fiscal court ("Government Type": Magistrate or Commissioner, blank for
Jefferson and Fayette), the courthouse address and telephone, and a table of
officials: first name, last name, title, telephone and e-mail. The table mixes
the elected officers (judge/executive, magistrates or commissioners, attorney,
clerk, sheriff, jailer, coroner, surveyor, PVA) with staff (treasurer,
bookkeeper). This scraper keeps EVERY row exactly as published;
`build_ky_county_officials.py` decides which titles are which.

HOW THE COUNTY LIST IS READ. The directory's home page carries a search form
whose County_Name list names all 120 counties, and a search for one county
answers with a link to exactly the page above, so the page URL is built from
the list rather than searched for 120 times. Measured 2026-10-11: the search
for Adair returns one link, 16_CountyView.cfm?County=Adair.

POLICY. robots.txt at kydlgweb.ky.gov was read with this scraper's own client
on 2026-10-11: one `User-agent: *` group whose rules name editing and login
pages at the site root. No rule matches /Counties/16_CountyHome.cfm or
/Counties/16_CountyView.cfm, and the file states no Crawl-delay. The scraper
still waits PAUSE seconds between requests.

THE TABLE IS PRINTED TWICE, and the second copy sits inside an HTML comment on
some pages. Only the first table whose header reads FIRST NAME is read, which is
the full one with the EMAIL column.

Output: ky/data/source/ky-county-officials-scrape.json

    python3 ky/scripts/ky_county_officials_scraper.py            # live read
    python3 ky/scripts/ky_county_officials_scraper.py --selftest # offline
"""

import argparse
import html
import json
import os
import re
import sys
import time
from datetime import date
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
TAG_ROOT = os.path.dirname(HERE)
OUT = os.path.join(TAG_ROOT, "data", "source", "ky-county-officials-scrape.json")

BASE = "https://kydlgweb.ky.gov/Counties/"
HOME = BASE + "16_CountyHome.cfm"
VIEW = BASE + "16_CountyView.cfm?County="

PAUSE = 0.5
# Kentucky has 120 counties and the list names every one; a read with fewer is
# a broken read.
MIN_COUNTIES = 120
# Measured 2026-10-11 on the first full read: 1,519 rows. A read finding far
# fewer has lost pages, not officials.
MIN_ROWS = 1300


def text_of(cell):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", cell))).strip()


def parse_counties(home_html):
    sel = re.search(r'<select name="County_Name".*?</select>', home_html, re.S | re.I)
    if not sel:
        raise SystemExit("FAIL: the directory home page has no County_Name list")
    return [v for v in re.findall(r'<option value="([^"]+)"', sel.group(0)) if v]


HEADER_FIELDS = {
    "Website:": "website", "Government Type:": "govType", "Address:": "address",
    "City:": "mailCity", "Zip:": "zip", "Phone:": "phone",
    "Population:": "population",
}


def parse_county(view_html):
    """One county page -> {website, govType, address, ..., officials: [...]}."""
    view_html = re.sub(r"<!--.*?-->", "", view_html, flags=re.S)
    out = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", view_html, re.S | re.I):
        cells = [text_of(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S | re.I)]
        if len(cells) >= 2 and cells[0] in HEADER_FIELDS and HEADER_FIELDS[cells[0]] not in out:
            out[HEADER_FIELDS[cells[0]]] = cells[1]
    officials = []
    for table in re.findall(r"<table[^>]*>(.*?)</table>", view_html, re.S | re.I):
        if "FIRST NAME" not in table:
            continue
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S | re.I):
            raw = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S | re.I)
            cells = [text_of(c) for c in raw]
            if not cells or cells[0] == "FIRST NAME":
                continue
            rec = {"first": cells[0], "last": cells[1] if len(cells) > 1 else "",
                   "title": cells[2] if len(cells) > 2 else ""}
            if len(cells) > 3 and cells[3]:
                rec["phone"] = cells[3]
            if len(cells) > 4:
                m = re.search(r'mailto:([^"]+)"', raw[4])
                if m:
                    rec["email"] = html.unescape(m.group(1)).strip()
            officials.append(rec)
        break
    out["officials"] = officials
    return out


def scrape():
    sys.path.insert(0, os.path.join(TAG_ROOT, "..", "scripts"))
    import requests
    import scraper_common as sc

    headers = dict(sc.UA_HEADERS_ROSTER_BOT)
    headers["Referer"] = HOME
    session = requests.Session()
    sc.require_robots_once(HOME, sc.UA_ROSTER_BOT, headers=headers)
    home = session.get(HOME, headers=headers, timeout=60)
    home.raise_for_status()
    counties = parse_counties(home.text)
    if len(counties) < MIN_COUNTIES:
        raise SystemExit("FAIL: %d counties in the search list, floor %d"
                         % (len(counties), MIN_COUNTIES))

    out, rows = {}, 0
    for n, county in enumerate(counties, 1):
        time.sleep(PAUSE)
        url = VIEW + quote(county)
        r = session.get(url, headers=headers, timeout=60)
        r.raise_for_status()
        rec = parse_county(r.text)
        if not rec["officials"]:
            raise SystemExit("FAIL: %s County's page lists no officials (%s)" % (county, url))
        rec["sourceUrl"] = url
        out[county] = rec
        rows += len(rec["officials"])
        if n % 40 == 0:
            print("  read %d of %d counties" % (n, len(counties)), file=sys.stderr)
    if rows < MIN_ROWS:
        raise SystemExit("FAIL: %d official rows, floor %d" % (rows, MIN_ROWS))
    return {
        "source": {
            "publisher": "Kentucky Department for Local Government",
            "url": HOME,
            "read": date.today().isoformat(),
        },
        "counties": out,
    }


SELFTEST_VIEW = """
<table width="100%"><tr><td>Website:</td><td class="BlueLetter">http://www.myadaircounty.com/</td></tr>
<tr><td>Government Type:</td><td class="BlueLetter">Magistrate</td></tr>
<tr><td>Address:</td><td>424 Public Square, Suite #1</td></tr>
<tr><td>City:</td><td>Columbia</td></tr><tr><td>Zip:</td><td>42728</td></tr>
<tr><td>Phone:</td><td>(270) 384-4703</td></tr></table>
<table><tr><td>FIRST NAME</td><td>LAST NAME</td><td>TITLE</td><td>PHONE</td><div><td>EMAIL</td></div></tr>
<tr bgcolor="#E6E6E6"><td>Larry</td><td>Bryant</td><td>County Judge Executive</td><td>(270) 384-4703</td>
<td><a href="mailto:cje@adaircountyky.com">cje@adaircountyky.com</a></td></tr>
<tr><td></td><td></td><td>County Treasurer</td><td>(606) 432-6236</td><td></td></tr></table>
<!-- <table><tr><td>FIRST NAME</td><td>LAST NAME</td><td>TITLE</td><td>PHONE</td></tr>
<tr><td>Wrong</td><td>Table</td><td>County Magistrate</td><td></td></tr></table> -->
"""


def selftest():
    rec = parse_county(SELFTEST_VIEW)
    assert rec["govType"] == "Magistrate" and rec["mailCity"] == "Columbia", rec
    assert rec["website"] == "http://www.myadaircounty.com/", rec
    assert len(rec["officials"]) == 2, rec["officials"]
    m = rec["officials"][0]
    assert (m["first"], m["last"], m["title"]) == ("Larry", "Bryant", "County Judge Executive"), m
    assert m["email"] == "cje@adaircountyky.com" and m["phone"] == "(270) 384-4703", m
    assert rec["officials"][1]["first"] == "" and "email" not in rec["officials"][1]
    # A commented-out table before the real one must not be read either.
    assert parse_county("<!-- <table><tr><td>FIRST NAME</td></tr><tr><td>X</td><td>Y</td>"
                        "<td>Z</td></tr></table> -->")["officials"] == []
    assert parse_counties('<select name="County_Name"><option value="">Any'
                          '<option value="Adair">Adair</select>') == ["Adair"]
    print("ky_county_officials_scraper selftest: ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    doc = scrape()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    print("wrote %s: %d counties" % (args.out, len(doc["counties"])))


if __name__ == "__main__":
    main()
