#!/usr/bin/env python3
"""Read every Kentucky city's officials from the Department for Local Government.

WHERE THE NAMES COME FROM. The Department for Local Government (DLG) keeps a
municipal directory at kydlgweb.ky.gov/Cities/. Its search answers one county at
a time with the cities in it, and each city's page (16_CityView.cfm?City_ID=N)
carries the city hall's address and telephone, the plan of government
("Gov. Type"), and a table of officials: first name, last name, title, telephone
and e-mail. The table mixes the elected body (Mayor, City Council, City
Commission) with staff (clerk, chief of police, treasurer). This scraper keeps
EVERY row exactly as published; `build_ky_city_officials.py` decides which
titles are the governing body.

HOW IT WAS FOUND TO WORK (2026-10-09). The coverage-gap record measured on
2026-10-01 that the directory "answers one city at a time rather than
publishing a list". That is true and it is not a reason the list cannot be
read: the county search returns every city in a county, so 120 searches and
one page per city cover the state. Two things about the search were measured
before writing this:
  - the form must be posted with every field it carries (City_Name, County,
    AreaDevDist, Gov_Type, Appalachia, Delta_Region, button) — a post carrying
    only County answers HTTP 500;
  - a search with every field set to "Any" answers HTTP 404, so the state is
    read county by county rather than in one search.

POLICY. robots.txt at kydlgweb.ky.gov was read with this scraper's own client
on 2026-10-09: one `User-agent: *` group whose rules name editing and login
pages at the site root (/cityContactAdd.cfm, /login.cfm, ...). No rule matches
/Cities/16_CityHome.cfm, /Cities/16_CityList.cfm or /Cities/16_CityView.cfm,
and the file states no Crawl-delay. The scraper still waits PAUSE seconds
between requests, because it makes about 535 of them.

Output: ky/data/source/ky-city-officials-scrape.json

    python3 ky/scripts/ky_city_officials_scraper.py            # live read
    python3 ky/scripts/ky_city_officials_scraper.py --selftest # offline
"""

import argparse
import html
import json
import os
import re
import sys
import time
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
TAG_ROOT = os.path.dirname(HERE)
OUT = os.path.join(TAG_ROOT, "data", "source", "ky-city-officials-scrape.json")

BASE = "https://kydlgweb.ky.gov/Cities/"
HOME = BASE + "16_CityHome.cfm"
LIST = BASE + "16_CityList.cfm"
VIEW = BASE + "16_CityView.cfm?City_ID="

PAUSE = 0.5
# Every field the search form carries; a post missing any of them answers 500.
FORM = {"City_Name": "", "County": "", "AreaDevDist": "", "Gov_Type": "",
        "Appalachia": "", "Delta_Region": "", "button": "SEARCH"}

# Floors, measured 2026-10-09 on the first full read: 120 counties, and the
# Census counts 415 incorporated places in Kentucky. A read finding far fewer
# is a broken read, not a state that lost its cities.
MIN_COUNTIES = 120
MIN_CITIES = 400


def text_of(cell):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", cell))).strip()


def parse_counties(home_html):
    sel = re.search(r'<select name="County".*?</select>', home_html, re.S | re.I)
    if not sel:
        raise SystemExit("FAIL: the directory home page has no County list")
    return [v for v in re.findall(r'<option value="([^"]+)"', sel.group(0)) if v]


def parse_city_ids(list_html):
    seen = []
    for cid in re.findall(r"16_CityView\.cfm\?City_ID=(\d+)", list_html):
        if cid not in seen:
            seen.append(cid)
    return seen


HEADER_FIELDS = {
    "City Name:": "name", "Address:": "address", "City:": "mailCity",
    "Zip:": "zip", "Phone:": "phone", "Gov. Type:": "govType",
    "Population:": "population", "County:": "county", "e-Mail:": "email",
}


def parse_city(view_html):
    """One city page -> {name, address, ..., officials: [...]}.

    The page carries the officials table twice: once with an EMAIL column for a
    wide screen and once without it for a narrow one. The first table whose
    header reads FIRST NAME is the full one, and it is the only one read."""
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
        raise SystemExit("FAIL: %d counties in the search list, floor %d" % (len(counties), MIN_COUNTIES))

    cities = {}
    for county in counties:
        form = dict(FORM, County=county)
        time.sleep(PAUSE)
        r = session.post(LIST, headers=headers, data=form, timeout=60)
        r.raise_for_status()
        for cid in parse_city_ids(r.text):
            cities.setdefault(cid, county)
    if len(cities) < MIN_CITIES:
        raise SystemExit("FAIL: %d cities found, floor %d" % (len(cities), MIN_CITIES))

    out = {}
    for n, (cid, county) in enumerate(sorted(cities.items(), key=lambda kv: int(kv[0])), 1):
        time.sleep(PAUSE)
        r = session.get(VIEW + cid, headers=headers, timeout=60)
        r.raise_for_status()
        rec = parse_city(r.text)
        rec["searchCounty"] = county
        rec["sourceUrl"] = VIEW + cid
        out[cid] = rec
        if n % 50 == 0:
            print("  read %d of %d cities" % (n, len(cities)), file=sys.stderr)
    return {
        "source": {
            "publisher": "Kentucky Department for Local Government",
            "url": HOME,
            "read": date.today().isoformat(),
            "counties": len(counties),
        },
        "cities": out,
    }


SELFTEST_VIEW = """
<table width="100%"><tr><td>City Name:</td><td>Bowling Green</td></tr>
<tr><td>Address:</td><td>1001 College Street</td></tr>
<tr><td>Phone:</td><td>(270) 393-3632</td></tr></table>
<table><tr><td>Gov. Type:</td><td>City Manager</td></tr>
<tr><td>County:</td><td>Warren</td></tr></table>
<table><tr><td>FIRST NAME</td><td>LAST NAME</td><td>TITLE</td><td>PHONE</td><div><td>EMAIL</td></div></tr>
<tr bgcolor="#E6E6E6"><td>Todd</td><td>Alcott</td><td>Mayor</td><td>(270) 393-3640</td>
<td><a href="mailto:todd.alcott@bgky.org">todd.alcott@bgky.org</a></td></tr>
<tr><td>Ashley</td><td>Jackson</td><td>City Clerk</td><td></td><td></td></tr></table>
<table><tr><td>FIRST NAME</td><td>LAST NAME</td><td>TITLE</td><td>PHONE</td></tr>
<tr><td>Wrong</td><td>Table</td><td>Mayor</td><td></td></tr></table>
"""


def selftest():
    rec = parse_city(SELFTEST_VIEW)
    assert rec["name"] == "Bowling Green", rec
    assert rec["govType"] == "City Manager" and rec["county"] == "Warren", rec
    assert len(rec["officials"]) == 2, rec["officials"]
    m = rec["officials"][0]
    assert (m["first"], m["last"], m["title"]) == ("Todd", "Alcott", "Mayor"), m
    assert m["email"] == "todd.alcott@bgky.org" and m["phone"] == "(270) 393-3640", m
    assert "phone" not in rec["officials"][1] and "email" not in rec["officials"][1]
    assert parse_city_ids('16_CityView.cfm?City_ID=36 x 16_CityView.cfm?City_ID=36 '
                          '16_CityView.cfm?City_ID=7') == ["36", "7"]
    assert parse_counties('<select name="County"><option value="">Any'
                          '<option value="Adair">Adair</select>') == ["Adair"]
    print("ky_city_officials_scraper selftest: ok")


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
    print("wrote %s: %d cities" % (args.out, len(doc["cities"])))


if __name__ == "__main__":
    main()
