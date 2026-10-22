#!/usr/bin/env python3
"""
Build la/data/app/la-conservation-districts.json: which of Louisiana's 44 soil
and water conservation districts cover each parish, and each district's
offices, from the Department of Agriculture and Forestry's map and list of
district contacts.

    python3 la/scripts/build_la_conservation_districts.py                # fetch, check, write
    python3 la/scripts/build_la_conservation_districts.py --save DIR     # the same, keeping what was read in DIR
    python3 la/scripts/build_la_conservation_districts.py --offline DIR  # build from a copy kept with --save
    python3 la/scripts/build_la_conservation_districts.py --check        # offline, standard library only

The Parish card reads the file and lists each district covering the parish,
with its offices. Building needs pdfplumber (scripts/requirements.txt pins
it); --check, which CI runs, does not.

WHAT A DISTRICT IS, from the Louisiana Revised Statutes, read on legis.la.gov
on 2026-10-21 as amended by Acts 2026, No. 180. A district is a governmental
subdivision of the state (R.S. 3:1208). The state Soil and Water Conservation
Commission forms one on the petition of any 25 owners of land in the area,
after a hearing and a referendum, and defines its boundaries, which need not
be contiguous (R.S. 3:1205 A, B). Five supervisors govern it (R.S. 3:1207 A).
Three are elected, one each year, with terms that begin on July 1 (R.S. 3:1207
C), from candidates nominated by petitions that at least 25 qualified voters
in the district sign, in an election the Secretary of State holds (R.S. 3:1206
A); where no more candidates are nominated than there are places, the
Commission may declare them elected without an election (R.S. 3:1206 B). The
Commission appoints the other two (R.S. 3:1205 F). Every supervisor is a
landowner or farm operator and a qualified voter of the state and serves
three years, and the Commission fills a vacancy for the rest of the term
(R.S. 3:1207 A, B). The card says this in LA_CONSERVATION_CHOSEN in
la/index.html, and --check holds that sentence to CHOSEN below.

THE SOURCE. The Department's page on the districts (PAGE_URL) links one PDF
twice: as "Louisiana's 44 Soil & Water Conservation Districts" in its
opening paragraph and as "Find your district and contact" at its foot. The
two links are two assets of the Department's content service with the same
bytes on 2026-10-21; the first is described as "Last updated April 2021", so
this reads the second, ASSET_ID, whose title is "SWCD Map and Contacts". Page
1 is the map: a vector drawing of the 44 districts, each filled in a colour of
its own with its number inside, the parish lines over them in grey, and a
legend listing each district's number, the Department's area it is in (I to
V) and its name. Its credit line says when it was last edited ("edit
10/19/2026" on the copy read 2026-10-21). Page 2 is the list of contacts:
each district's offices, with each office's town, telephone number and
extension.

WHAT IS READ, AND WHAT NEVER IS. From the legend, each district's number and
name; from page 2, each office's town, telephone and extension; from the
credit line, the edit date. Nothing else. The PDF's own metadata names a
member of the Department's staff as its author, and the credit line names
the person who drew the map in 2008; neither is read or carried. Neither
page carries an e-mail address, and --check fails if one appears in the
file. No supervisor is named anywhere in the PDF, and the Secretary of
State's list of elected officials names none either: read on 2026-10-21, its
offices for special districts ("Special District or Tax Ward", "Other Local
Office") listed no one, and its local boards ("Local Board or Commission
Member") only the Greater Lafourche Port Commission. So the card names no
supervisor and says why (LA_CONSERVATION_BOARD), and gap
la-conservation-district-supervisors records it. The operator asked the
Department for a list on 2026-10-21 (docs/ASK_DRAFTS.md, Ask
la-ldaf-swcd-supervisors).

WHICH DISTRICTS COVER EACH PARISH is PARISHES below. It was measured from the
map's drawing objects by la/scripts/measure_la_conservation_parishes.py,
which says how, and copied here by hand. The map can change without this
file noticing, so MAP_FINGERPRINT is a hash of what that measurement read
(every filled path's colour and points, and every district number's place)
and the build stops when the map's no longer matches: then re-run the
measurement, look at what it reports, and update PARISHES and the
fingerprint together. Page 2 can change on its own, and a rebuild then
carries the new offices. Seven parishes are covered by two districts, and
the card lists both, because the map's line between them is not drawn here.
In Jefferson the second is Grand Isle and the land near it, which the map
puts in the Lafourche-Terrebonne district (PARISH_NOTES says so on the card).

THE NAMES. A district's name on the card is its legend name, which ends
"SWCD", with "Soil and Water Conservation District" spelled out. The legend
and page 2 spell some names differently ("Bogue Chitto-Pearl River" and
"Bogue-Chitto/Pearl River", "De Soto" and "Desoto", "La Salle" and
"LaSalle"), so the two are joined on their letters alone, and every district
must have an office and every office a district. District 22 is the Gulf
Coast district, which is its name; no sentence of this project's own names
the gulf. Three town names on page 2 are misspelt, and TOWN_FIXES gives
what the card shows; an entry stops the build once page 2 stops printing it.
"Bossier" and "Deridder" are printed as page 2 gives them.

THE TERMS. The PDF and the page state no licence, and the Department's site
says "All rights reserved". What this file carries is facts about public
offices (which district covers a parish, an office's town and telephone),
which copyright does not cover, credited to the Department on the card.

ROBOTS. robots.txt is read for each host before its first fetch, as the
client that fetches it, and again for any host a redirect leads to: on
2026-10-21 www.ldaf.la.gov's has one group, for every agent, disallowing
/.build-info only, and assets.ctfassets.net answers 404 (no policy, so every
path is allowed).

THE DATE on the card is the map's edit date and the day the PDF was read.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
ROOT = os.path.dirname(INSTANCE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from scraper_common import require_robots_once  # noqa: E402

LABEL = "build-la-conservation-districts"
PAGE_URL = "https://www.ldaf.la.gov/land/conservation/soil-and-water-conservation-districts"
ASSET_ID = "2YUB8fOA5nT12FMFHRBX22"
ASSET_URL = re.compile(r"https://assets\.ctfassets\.net/[A-Za-z0-9]+/" + ASSET_ID +
                       r"/[0-9a-f]+/[A-Za-z0-9_.-]+\.pdf")
USER_AGENT = "districtry/1.0 (+https://districtry.com/la/)"
OUT = os.path.join(INSTANCE, "data", "app", "la-conservation-districts.json")
RECORD = os.path.join(INSTANCE, "data", "source", "la-conservation-districts.source.json")
COUNTIES = os.path.join(INSTANCE, "data", "app", "state-counties.json")
APP_FILE = os.path.join(INSTANCE, "index.html")

DISTRICTS = 44
SUFFIX = " Soil and Water Conservation District"
ROMAN = ("I", "II", "III", "IV", "V")
PHONE = re.compile(r"^\d{3}-\d{3}-\d{4}$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# What measure_la_conservation_parishes.py read on the map of 2026-10-19
# (read 2026-10-21): map_fingerprint() below, and the number of items in it.
MAP_FINGERPRINT = "0b5b447bf573a7214007ee2addd0fdba2636e22d74591f93863db80aa29b20e9"
MAP_ITEMS = 101

# The districts covering each parish, by the legend's numbers, as
# measure_la_conservation_parishes.py found them on that map. Where a parish
# has two, the first covers more of it.
PARISHES = {
    "22001": ["20"],          # Acadia
    "22003": ["37"],          # Allen
    "22005": ["23", "24"],    # Ascension
    "22007": ["24"],          # Assumption
    "22009": ["17"],          # Avoyelles
    "22011": ["9"],           # Beauregard
    "22013": ["6"],           # Bienville
    "22015": ["43"],          # Bossier
    "22017": ["5"],           # Caddo
    "22019": ["22"],          # Calcasieu
    "22021": ["8", "14"],     # Caldwell
    "22023": ["22"],          # Cameron
    "22025": ["34"],          # Catahoula
    "22027": ["2"],           # Claiborne
    "22029": ["16"],          # Concordia
    "22031": ["39"],          # De Soto
    "22033": ["33"],          # East Baton Rouge
    "22035": ["15"],          # East Carroll
    "22037": ["1"],           # East Feliciana
    "22039": ["30"],          # Evangeline
    "22041": ["13"],          # Franklin
    "22043": ["10"],          # Grant
    "22045": ["21"],          # Iberia
    "22047": ["24", "23"],    # Iberville
    "22049": ["8"],           # Jackson
    "22051": ["26", "19"],    # Jefferson
    "22053": ["44"],          # Jefferson Davis
    "22055": ["28"],          # Lafayette
    "22057": ["19"],          # Lafourche
    "22059": ["35"],          # LaSalle
    "22061": ["2"],           # Lincoln
    "22063": ["33"],          # Livingston
    "22065": ["36"],          # Madison
    "22067": ["11"],          # Morehouse
    "22069": ["38"],          # Natchitoches
    "22071": ["26"],          # Orleans
    "22073": ["2", "14"],     # Ouachita
    "22075": ["42"],          # Plaquemines
    "22077": ["25"],          # Pointe Coupee
    "22079": ["12"],          # Rapides
    "22081": ["40"],          # Red River
    "22083": ["14", "13"],    # Richland
    "22085": ["4"],           # Sabine
    "22087": ["26"],          # St. Bernard
    "22089": ["26"],          # St. Charles
    "22091": ["32"],          # St. Helena
    "22093": ["24", "23"],    # St. James
    "22095": ["26"],          # St. John the Baptist
    "22097": ["29"],          # St. Landry
    "22099": ["27"],          # St. Martin
    "22101": ["18"],          # St. Mary
    "22103": ["7"],           # St. Tammany
    "22105": ["32"],          # Tangipahoa
    "22107": ["16"],          # Tensas
    "22109": ["19"],          # Terrebonne
    "22111": ["2"],           # Union
    "22113": ["41"],          # Vermilion
    "22115": ["9"],           # Vernon
    "22117": ["7"],           # Washington
    "22119": ["3"],           # Webster
    "22121": ["25"],          # West Baton Rouge
    "22123": ["31"],          # West Carroll
    "22125": ["1"],           # West Feliciana
    "22127": ["8"],           # Winn
}

# A sentence the card adds for a parish, only where two districts cover it.
PARISH_NOTES = {
    "22051": "On the Department's map, Grand Isle is part of the Lafourche-Terrebonne district.",
}

# The town as page 2 prints it -> (what the card shows, why). Read 2026-10-21.
TOWN_FIXES = {
    "Boute": ("Boutte", "the Crescent district's office; Boutte is in St. Charles Parish"),
    "Belle Chase": ("Belle Chasse", "the Plaquemines district's office, in Plaquemines Parish"),
    "St. Joesph": ("St. Joseph", "the Tensas-Concordia district's second office, in Tensas Parish"),
}

# The two sentences the card states as fact, which la/index.html carries as
# LA_CONSERVATION_CHOSEN and LA_CONSERVATION_BOARD and --check holds to these.
CHOSEN = ("Five supervisors, each a landowner or farm operator, serve three-year "
          "terms. Three are elected, one each year, with terms that begin on July 1: "
          "a candidate is nominated by a petition signed by at least 25 qualified "
          "voters in the district, and the Secretary of State holds the election. "
          "Where no more candidates are nominated than there are seats to fill, the "
          "state Soil and Water Conservation Commission may declare them elected "
          "without an election. The Commission appoints the other two, and fills any "
          "vacancy for the rest of the term.")
BOARD = ("Not named here. The Department of Agriculture and Forestry's list gives "
         "each district's offices but names none of its five supervisors, and the "
         "Secretary of State's list of elected officials names none either, so this "
         "app names no one rather than guessing.")


def fail(msg):
    print("%s: FAIL: %s" % (LABEL, msg))
    raise SystemExit(1)


# ---------- fetching ----------

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url, accept):
    """The body at url, reading each host's robots.txt before its first fetch
    and following a redirect only after reading the new host's."""
    headers = {"User-Agent": USER_AGENT, "Accept": accept, "Accept-Encoding": "identity"}
    opener = urllib.request.build_opener(_NoRedirect)
    for _hop in range(6):
        verdict = require_robots_once(url, USER_AGENT, headers=headers, label=LABEL)
        print("robots %s: %s" % (urllib.parse.urlsplit(url).netloc, verdict))
        try:
            with opener.open(urllib.request.Request(url, headers=headers), timeout=120) as resp:
                if resp.status != 200:
                    fail("%s answered HTTP %d" % (url, resp.status))
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                url = urllib.parse.urljoin(url, e.headers["Location"])
                continue
            fail("%s answered HTTP %d" % (url, e.code))
    fail("more than five redirects from %s" % url)


def asset_url(page):
    found = sorted(set(ASSET_URL.findall(page)))
    if len(found) != 1:
        fail("the Department's page links %d copies of asset %s (%s); read it again"
             % (len(found), ASSET_ID, ", ".join(found) or "none"))
    return found[0]


# ---------- reading the PDF ----------

def map_fingerprint(page):
    """(hash, items) of what the parish measurement reads on the map page:
    every filled path's colour and points, and every one- or two-digit number
    printed on the map itself (the legend sits right of x 1280)."""
    items = []
    for c in page.curves:
        if not c.get("fill"):
            continue
        col = c.get("non_stroking_color")
        pts = [(round(x, 2), round(y, 2)) for x, y in c["pts"]]
        items.append(json.dumps([col, pts], separators=(",", ":")))
    for w in page.extract_words(use_text_flow=False):
        if re.fullmatch(r"\d{1,2}", w["text"]) and w["x0"] < 1280:
            items.append(json.dumps(["n", w["text"], round(w["x0"], 1), round(w["top"], 1)]))
    items.sort()
    return hashlib.sha256("\n".join(items).encode()).hexdigest(), len(items)


def legend(page):
    """{number: name} from the map's legend: one row per district, reading
    number, area (I to V), name, and "SWCD"."""
    words = page.extract_words(use_text_flow=False)
    rows = {}
    for s in sorted((w for w in words if w["text"] == "SWCD" and w["x0"] >= 1280),
                    key=lambda w: w["top"]):
        line = sorted((w for w in words if abs(w["top"] - s["top"]) < 1.0
                       and w["x0"] >= 1280 and w["x1"] <= s["x1"] + 0.5),
                      key=lambda w: w["x0"])
        texts = [w["text"] for w in line]
        if (len(texts) < 4 or not texts[0].isdigit() or texts[1] not in ROMAN
                or texts[-1] != "SWCD"):
            fail("a legend row is not number, area, name, SWCD: %r" % texts)
        name = re.sub(r"\s+([.,])", r"\1", " ".join(texts[2:-1]))
        if texts[0] in rows:
            fail("the legend lists district %s twice" % texts[0])
        rows[texts[0]] = name
    if sorted(rows, key=int) != [str(n) for n in range(1, DISTRICTS + 1)]:
        fail("the legend lists districts %s, not 1 to %d" % (sorted(rows, key=int), DISTRICTS))
    return rows


def edit_date(page):
    found = re.findall(r"\bedit (\d{2})/(\d{2})/(\d{4})\b", page.extract_text() or "")
    if len(found) != 1:
        fail("the map's credit line gives %d edit dates, not one" % len(found))
    month, day, year = found[0]
    return datetime.date(int(year), int(month), int(day)).isoformat()


def offices(page):
    """[(district as printed, town as printed, telephone, extension or None)]
    from page 2's table; a row with no district is another office of the one
    above it."""
    words = page.extract_words(use_text_flow=False)
    head = {w["text"]: w for w in words if w["top"] < 70}
    for k in ("District", "City", "Phone"):
        if k not in head:
            fail("page 2 has no %r column heading" % k)
    city_x, phone_x = head["City"]["x0"], head["Phone"]["x0"]
    lines = {}
    for w in words:
        if w["top"] > head["District"]["bottom"]:
            lines.setdefault(round(w["top"]), []).append(w)
    out, district = [], None
    for top in sorted(lines):
        ws = sorted(lines[top], key=lambda w: w["x0"])
        name = " ".join(w["text"] for w in ws if w["x1"] < city_x - 15)
        town = " ".join(w["text"] for w in ws if w["x1"] >= city_x - 15 and w["x0"] < phone_x - 3)
        tel = [w["text"] for w in ws if w["x0"] >= phone_x - 3]
        if not tel or not PHONE.match(tel[0]) or not town:
            fail("a row of page 2 is not district, town, telephone: %r" % [w["text"] for w in ws])
        ext = "".join(tel[1:])
        m = re.fullmatch(r"x(\d+)", ext) if ext else None
        if ext and not m:
            fail("an extension on page 2 reads %r" % ext)
        district = name or district
        if district is None:
            fail("page 2's first row names no district")
        out.append((district, town, tel[0], m.group(1) if m else None))
    return out


def letters(name):
    return re.sub(r"[^a-z]", "", name.lower())


def read_pdf(path):
    import pdfplumber  # build only; --check needs nothing outside the standard library

    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) != 2:
            fail("the PDF has %d pages, not the map and the list of contacts" % len(pdf.pages))
        fingerprint = map_fingerprint(pdf.pages[0])
        if fingerprint != (MAP_FINGERPRINT, MAP_ITEMS):
            fail("the map has changed (fingerprint %s, %d items; PARISHES was measured on %s, "
                 "%d items). Re-run la/scripts/measure_la_conservation_parishes.py on this "
                 "PDF, read what it reports, and update PARISHES, PARISH_NOTES and "
                 "MAP_FINGERPRINT together" % (fingerprint[0], fingerprint[1],
                                               MAP_FINGERPRINT, MAP_ITEMS))
        names = legend(pdf.pages[0])
        edited = edit_date(pdf.pages[0])
        rows = offices(pdf.pages[1])
    return names, edited, rows


def join(names, rows):
    """{number: {number, name, offices}} with every district given at least
    one office and every office a district."""
    by_letters = {}
    for n, name in names.items():
        if letters(name) in by_letters:
            fail("two legend names read alike: %r" % name)
        by_letters[letters(name)] = n
    districts = {n: {"number": n, "name": name + SUFFIX, "offices": []}
                 for n, name in names.items()}
    used = set()
    for printed, town, phone, ext in rows:
        n = by_letters.get(letters(printed))
        if n is None:
            fail("page 2's district %r matches no district in the legend" % printed)
        if town in TOWN_FIXES:
            used.add(town)
            town = TOWN_FIXES[town][0]
        office = {"town": town, "phone": phone}
        if ext:
            office["ext"] = ext
        districts[n]["offices"].append(office)
    stale = sorted(set(TOWN_FIXES) - used)
    if stale:
        fail("TOWN_FIXES names %s, which page 2 no longer prints; read it again" % stale)
    bare = sorted((n for n, d in districts.items() if not d["offices"]), key=int)
    if bare:
        fail("page 2 lists no office for district(s) %s" % ", ".join(bare))
    return districts


def assemble(districts, edited, read):
    out = {}
    for geoid, nums in sorted(PARISHES.items()):
        rec = {"districts": [districts[n] for n in nums], "mapEdited": edited,
               "pageUrl": PAGE_URL, "read": read}
        if geoid in PARISH_NOTES:
            rec["note"] = PARISH_NOTES[geoid]
        out[geoid] = rec
    return out


# ---------- the offline check ----------

def _stated(app, name):
    m = re.search(r"var %s = ((?:\"(?:[^\"\\]|\\.)*\"\s*\+\s*)*\"(?:[^\"\\]|\\.)*\")\s*;" % name, app)
    if m is None:
        return None
    return "".join(json.loads(s) for s in re.findall(r"\"(?:[^\"\\]|\\.)*\"", m.group(1)))


def check(data, record):
    problems = []
    with open(COUNTIES, encoding="utf-8") as fh:
        parishes = {str(f["properties"]["GEOID"]) for f in json.load(fh)["features"]}
    if set(PARISHES) != parishes:
        problems.append("PARISHES names %d parishes and state-counties.json %d"
                        % (len(PARISHES), len(parishes)))
    if set(data) != set(PARISHES):
        problems.append("the file's parishes differ from PARISHES: %s"
                        % sorted(set(data) ^ set(PARISHES)))
    seen = {}
    edited = {rec.get("mapEdited") for rec in data.values()}
    read = {rec.get("read") for rec in data.values()}
    for geoid, rec in sorted(data.items()):
        extra = set(rec) - {"districts", "mapEdited", "pageUrl", "read", "note"}
        if extra:
            problems.append("%s carries %s" % (geoid, sorted(extra)))
        if rec.get("pageUrl") != PAGE_URL:
            problems.append("%s cites %r, not the Department's page" % (geoid, rec.get("pageUrl")))
        nums = [d.get("number") for d in rec.get("districts") or []]
        if nums != PARISHES.get(geoid):
            problems.append("%s lists districts %s and PARISHES %s" % (geoid, nums, PARISHES.get(geoid)))
        if rec.get("note") != PARISH_NOTES.get(geoid):
            problems.append("%s's note is %r, and PARISH_NOTES gives %r"
                            % (geoid, rec.get("note"), PARISH_NOTES.get(geoid)))
        for d in rec.get("districts") or []:
            n = d.get("number")
            if set(d) != {"number", "name", "offices"}:
                problems.append("district %s in %s carries %s" % (n, geoid, sorted(d)))
            if not str(d.get("name", "")).endswith(SUFFIX):
                problems.append("district %s is named %r" % (n, d.get("name")))
            if not d.get("offices"):
                problems.append("district %s has no office" % n)
            for o in d.get("offices") or []:
                if set(o) - {"town", "phone", "ext"} or not o.get("town"):
                    problems.append("district %s has an office %r" % (n, o))
                if not PHONE.match(str(o.get("phone", ""))):
                    problems.append("district %s's telephone %r is not one number" % (n, o.get("phone")))
                if "ext" in o and not re.fullmatch(r"\d+", str(o["ext"])):
                    problems.append("district %s's extension %r is not digits" % (n, o["ext"]))
                if o.get("town") in TOWN_FIXES:
                    problems.append("district %s's office is in %r, which TOWN_FIXES corrects"
                                    % (n, o["town"]))
            if n in seen and seen[n] != d:
                problems.append("district %s differs between parishes" % n)
            seen[n] = d
    if sorted(seen, key=int) != [str(n) for n in range(1, DISTRICTS + 1)]:
        problems.append("the file lists districts %s, not 1 to %d" % (sorted(seen, key=int), DISTRICTS))
    for geoid in PARISH_NOTES:
        if len(PARISHES.get(geoid, [])) < 2:
            problems.append("PARISH_NOTES has a note for %s, which one district covers" % geoid)
    if len(edited) != 1 or not all(ISO_DATE.match(str(x)) for x in edited):
        problems.append("the file gives map edit dates %s" % sorted(map(str, edited)))
    if len(read) != 1 or not all(ISO_DATE.match(str(x)) for x in read):
        problems.append("the file gives read dates %s" % sorted(map(str, read)))
    if "@" in json.dumps(data):
        problems.append("the file carries an @, and nothing here should be an e-mail address")
    want = {"pageUrl": PAGE_URL, "mapFingerprint": MAP_FINGERPRINT, "mapItems": MAP_ITEMS,
            "mapEdited": next(iter(edited)) if len(edited) == 1 else None,
            "read": next(iter(read)) if len(read) == 1 else None,
            "districts": DISTRICTS, "offices": sum(len(d["offices"]) for d in seen.values())}
    for k, v in want.items():
        if record.get(k) != v:
            problems.append("%s gives %s %r, and the file %r"
                            % (os.path.relpath(RECORD, ROOT), k, record.get(k), v))
    if not ASSET_URL.fullmatch(str(record.get("sourceUrl", ""))):
        problems.append("the record's sourceUrl %r is not the Department's asset" % record.get("sourceUrl"))
    if not re.fullmatch(r"[0-9a-f]{64}", str(record.get("sha256", ""))):
        problems.append("the record's sha256 is %r" % record.get("sha256"))
    with open(APP_FILE, encoding="utf-8") as fh:
        app = fh.read()
    for name, sentence in (("LA_CONSERVATION_CHOSEN", CHOSEN), ("LA_CONSERVATION_BOARD", BOARD)):
        got = _stated(app, name)
        if got != sentence:
            problems.append("la/index.html: %s reads %r, and this builder states %r"
                            % (name, got, sentence))
    return problems


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="offline: hold the shipped file to PARISHES, its record and the card")
    mode.add_argument("--offline", metavar="DIR", help="build from a copy kept with --save")
    ap.add_argument("--save", metavar="DIR", help="keep the page and the PDF read in DIR")
    args = ap.parse_args()

    if args.check:
        with open(OUT, encoding="utf-8") as fh:
            data = json.load(fh)
        with open(RECORD, encoding="utf-8") as fh:
            record = json.load(fh)
        problems = check(data, record)
        if problems:
            for p in problems:
                print("%s: FAIL: %s" % (LABEL, p))
            raise SystemExit(1)
        split = sum(1 for v in PARISHES.values() if len(v) > 1)
        print("%s --check: OK — %d districts over %d parishes (%d with two), the map of %s "
              "read %s, and the card's two sentences as stated here"
              % (LABEL, DISTRICTS, len(data), split, record["mapEdited"], record["read"]))
        return

    if args.offline:
        with open(os.path.join(args.offline, "read.json"), encoding="utf-8") as fh:
            meta = json.load(fh)
        with open(os.path.join(args.offline, "page.html"), encoding="utf-8", errors="replace") as fh:
            page = fh.read()
        pdf_path = os.path.join(args.offline, "map.pdf")
        read = meta["read"]
        url = asset_url(page)
        if url != meta["sourceUrl"]:
            fail("read.json names %s and the saved page links %s" % (meta["sourceUrl"], url))
        with open(pdf_path, "rb") as fh:
            body = fh.read()
    else:
        read = datetime.date.today().isoformat()
        page = fetch(PAGE_URL, "text/html").decode("utf-8", errors="replace")
        url = asset_url(page)
        body = fetch(url, "application/pdf")
        if args.save:
            os.makedirs(args.save, exist_ok=True)
            with open(os.path.join(args.save, "page.html"), "w", encoding="utf-8") as fh:
                fh.write(page)
            with open(os.path.join(args.save, "map.pdf"), "wb") as fh:
                fh.write(body)
            write_json(os.path.join(args.save, "read.json"), {"read": read, "sourceUrl": url})
        pdf_path = None
    if not body.startswith(b"%PDF"):
        fail("%s is not a PDF" % url)
    if pdf_path is None:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
            fh.write(body)
            pdf_path = fh.name
    try:
        names, edited, rows = read_pdf(pdf_path)
    finally:
        if not args.offline:
            os.unlink(pdf_path)
    districts = join(names, rows)
    data = assemble(districts, edited, read)
    record = {"pageUrl": PAGE_URL, "sourceUrl": url, "sha256": hashlib.sha256(body).hexdigest(),
              "bytes": len(body), "mapFingerprint": MAP_FINGERPRINT, "mapItems": MAP_ITEMS,
              "mapEdited": edited, "read": read, "districts": DISTRICTS, "offices": len(rows)}
    problems = [p for p in check(data, record) if not p.startswith("la/index.html")]
    if problems:
        for p in problems:
            print("%s: FAIL: %s" % (LABEL, p))
        raise SystemExit(1)
    write_json(OUT, data)
    write_json(RECORD, record)
    print("wrote %s: %d parishes, %d districts, %d offices (map edited %s, read %s)"
          % (os.path.relpath(OUT, ROOT), len(data), DISTRICTS, len(rows), edited, read))


if __name__ == "__main__":
    main()
