#!/usr/bin/env python3
"""
Court districts and their judges for Kansas, Nebraska, North Dakota, Ohio and
South Dakota, read from each state's own court website.

    python3 scripts/build_state_courts.py --fetch ks   # re-read the court pages into ks/data/source/courts/
    python3 scripts/build_state_courts.py ks           # build the two app files (needs shapely)
    python3 scripts/build_state_courts.py --check      # every state, offline, stdlib only

EVERY DISTRICT HERE IS A SET OF WHOLE COUNTIES, so the county lists are the
boundary and no map is read: the dissolve, the partition gate and the offline
area check are scripts/whole_county_courts.py, shared with the other states.
This file says where each state's county lists and judges come from.

WHAT IS KEPT. `--fetch` reads the court pages (robots.txt first, this
project's own client) and writes ONE plain-text excerpt per state,
`<tag>/data/source/courts/<tag>-courts.txt`: a `district` line per district
with its counties as the court lists them, and a `judge` line per judge with
the title the court prints. Nothing else from the pages is copied: no address,
telephone or fax. The build reads only that excerpt, so a reviewer can read
what changed in a refresh as a text diff.

TWO FILES PER STATE. The districts (`<tag>-judicial-districts.json`) are
geometry, cache-first in the service worker, so they change only when a county
moves between districts. The judges (`<tag>-district-judges.json`) are a
roster keyed by district, network-first, so a new judge reaches a returning
reader at once.

A SEAT THE COURT PRINTS AS VACANT ships as vacant and never as a person named
"Vacant". A heading this file does not know stops the fetch rather than
becoming a judge's name.

No weekly job refreshes these; each state's WATCH.md carries the re-read, and
the card prints the date the pages were read.
"""

import argparse
import datetime
import html
import io
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import whole_county_courts as wcc  # noqa: E402  (FLEET_SHARED)

LABEL = "build-state-courts"

ORDINALS = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh",
            "Eighth", "Ninth", "Tenth", "Eleventh", "Twelfth"]


def ordinal_suffix(n):
    if 10 <= n % 100 <= 20:
        return "%dth" % n
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


# Measured 2026-11-27 on the pages read that day. A count that moves stops the
# build; read the court's page before changing one.
STATES = {
    "co": {
        "name": "Colorado",
        "districts": 23, "counties": 64, "min_judges": 190,
        "unit_word": "judicial district",
        "authority": "The Colorado Judicial Branch's list of trial courts by district (coloradojudicial.gov)",
        "source": "https://www.coloradojudicial.gov/trial-courts-district",
    },
    "id": {
        "name": "Idaho",
        "districts": 7, "counties": 44, "min_judges": 48,
        "unit_word": "judicial district",
        "authority": "Idaho Code sections 1-802 to 1-808 (legislature.idaho.gov)",
        "source": "https://isc.idaho.gov/about-the-courts/judicial-directory",
    },
    "ut": {
        "name": "Utah",
        "districts": 8, "counties": 29, "min_judges": 75,
        "unit_word": "judicial district",
        "authority": "The Utah State Courts' map of judicial districts (utcourts.gov)",
        "source": "https://www.utcourts.gov/en/about/miscellaneous/directory/map-of-judicial-districts.html",
    },
    "wy": {
        "name": "Wyoming",
        "districts": 9, "counties": 23, "min_judges": 26,
        "unit_word": "judicial district",
        "authority": "The Wyoming Judicial Branch's Find a Court list (wyocourts.gov)",
        "source": "https://www.wyocourts.gov/find-a-court/",
    },
    "nm": {
        "name": "New Mexico",
        "districts": 13, "counties": 33, "min_judges": 80,
        "unit_word": "judicial district",
        "authority": "The New Mexico Judicial Branch's Courts by District page (nmcourts.gov)",
        "source": "https://nmcourts.gov/courts-by-district/",
    },
    "or": {
        "name": "Oregon",
        "districts": 27, "counties": 36, "min_judges": 178,
        "unit_word": "judicial district",
        "authority": "ORS 3.012 (oregonlegislature.gov)",
        "source": "https://www.courts.oregon.gov/courts/Pages/judges.aspx",
    },
    "mt": {
        "name": "Montana",
        "districts": 22, "counties": 56, "min_judges": 48,
        "unit_word": "judicial district",
        "authority": "The Montana Judicial Branch's District Courts page (courts.mt.gov)",
        "source": "https://courts.mt.gov/courts/dcourt/",
    },
    "wa": {
        "name": "Washington",
        "districts": 32, "counties": 39, "min_judges": 170,
        "unit_word": "superior court",
        "authority": "The Washington Courts' Judicial Districts Reference List (courts.wa.gov)",
        "source": "https://www.courts.wa.gov/court_dir/?fa=court_dir.judicialdistricts",
    },
    "pa": {
        "name": "Pennsylvania",
        "districts": 60, "counties": 67, "min_judges": 420,
        "unit_word": "judicial district",
        "authority": "The Unified Judicial System of Pennsylvania's Judicial Districts page (pacourts.us)",
        "source": "https://www.pacourts.us/courts/courts-of-common-pleas/judicial-districts",
    },
    "wv": {
        "name": "West Virginia",
        "districts": 30, "counties": 55, "min_judges": 75,
        "unit_word": "judicial circuit",
        "authority": "The West Virginia Judiciary's circuit court map (courtswv.gov)",
        "source": "https://www.courtswv.gov/lower-courts/circuit-courts",
    },
    "ks": {
        "name": "Kansas",
        "districts": 31, "counties": 105, "min_judges": 250,
        "unit_word": "judicial district",
        "authority": "The Kansas Judicial Branch's district court pages (kscourts.gov)",
        "source": "https://www.kscourts.gov/About-the-Courts/District-Courts",
    },
    "ne": {
        "name": "Nebraska",
        "districts": 12, "counties": 93, "min_judges": 50,
        "unit_word": "district court judicial district",
        "authority": "The Nebraska Judicial Branch's district map and directory of district court judges (nebraskajudicial.gov)",
        "source": "https://nebraskajudicial.gov/directories/district-court-judges",
    },
    "nd": {
        "name": "North Dakota",
        "districts": 8, "counties": 53, "min_judges": 45,
        "unit_word": "judicial district",
        "authority": "North Dakota Supreme Court Administrative Rule 6 and the court system's list of district court judges (ndcourts.gov)",
        "source": "https://www.ndcourts.gov/district-court/district-court-judges",
    },
    "oh": {
        "name": "Ohio",
        "districts": 12, "counties": 88, "min_judges": 60,
        "unit_word": "appellate district",
        "authority": "The Supreme Court of Ohio's page on the courts of appeals (supremecourt.ohio.gov)",
        "source": "https://www.supremecourt.ohio.gov/courts/judicial-system/ohio-court-of-appeals/",
    },
    "sd": {
        "name": "South Dakota",
        "districts": 7, "counties": 66, "min_judges": 35,
        "unit_word": "judicial circuit",
        "authority": "The South Dakota Unified Judicial System's circuit pages (ujs.sd.gov)",
        "source": "https://ujs.sd.gov/court-finder/",
    },
}


def source_path(tag):
    return os.path.join(ROOT, tag, "data", "source", "courts", "%s-courts.txt" % tag)


# ---------------------------------------------------------------- reading pages

def page_lines(body):
    """The visible text of a page, one trimmed line per text node."""
    body = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", body)
    body = re.sub(r"<[^>]+>", "\n", body)
    body = html.unescape(body).replace("​", "").replace("\xa0", " ")
    return [re.sub(r"\s+", " ", ln).strip() for ln in body.split("\n")
            if ln.strip()]


class Reader(object):
    """GETs with robots.txt read first per host, paced two seconds apart."""

    def __init__(self):
        import scraper_common as sc
        self.sc = sc
        self.headers = sc.UA_HEADERS_ROSTER_BOT
        self.last = 0.0

    def html(self, url):
        self.sc.require_robots_once(url, self.headers["User-Agent"],
                                    headers=self.headers, label=LABEL)
        wait = 2.0 - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait)
        resp = self.sc.fetch(url, self.headers, timeout=60)
        self.last = time.time()
        return resp.text

    def get(self, url):
        return page_lines(self.html(url))


NOT_A_NAME = re.compile(r"\b(Judges?|Division|Clerk|Administrator|Officer|"
                        r"Courthouse|District Court|Magistrates?)\b", re.I)


def name_problem(name):
    if not name or NOT_A_NAME.search(name) or not re.search(r"[a-z]", name) \
            or len(name.split()) < 2 or len(name) > 60 or re.search("[\u00c2\u00c3]", name):
        return "%r does not read as a judge's name" % name
    return None


def person(name, label):
    name = re.sub(r"\s+", " ", name).strip().rstrip(",")
    problem = name_problem(name)
    if problem:
        wcc.fail(label, problem + "; read the page before teaching this file "
                 "a new heading")
    return name


def fetch_ks(reader):
    roles = {"Chief Judge": "Chief Judge",
             "District Court Judge": "District Judge",
             "District Court Judges": "District Judge",
             "District Judge": "District Judge",
             "District Magistrate Judge": "District Magistrate Judge",
             "District Magistrate Judges": "District Magistrate Judge",
             "Juvenile Division": "Judge, Juvenile Division",
             "Pro Tem Division": "Judge, Pro Tem Division"}
    stop = ("District Court Administrator", "Chief Clerk", "Chief Court Services",
            "Court Administrator")
    out, counties = [], None
    for n in range(1, 32):
        url = ("https://www.kscourts.gov/About-the-Courts/District-Courts/"
               "Districts/%s-Judicial-District" % ordinal_suffix(n))
        lines = reader.get(url)
        if counties is None:
            # The district map every district page carries: "1", "st",
            # "Judicial District", "Atchison, Leavenworth", a long list
            # sometimes wrapped onto a second line after a trailing comma.
            counties = {}
            i = lines.index("Kansas District Map") + 1
            while i < len(lines) and len(counties) < 31:
                if re.match(r"^\d+$", lines[i]) and lines[i + 2] == "Judicial District":
                    text, j = lines[i + 3], i + 4
                    while text.endswith(","):
                        text, j = text + " " + lines[j], j + 1
                    counties[int(lines[i])] = [c.strip() for c in text.split(",")]
                    i = j
                else:
                    i += 1
            for d in sorted(counties):
                out.append("district | %d | %s" % (d, ", ".join(counties[d])))
        start = next(i for i, ln in enumerate(lines) if ln in roles)
        role = None
        for ln in lines[start:]:
            if ln.startswith(stop):
                break
            if ln in roles:
                role = roles[ln]
                continue
            m = re.match(r"^(.*?)(?:,| -) ([A-Z][A-Za-z. ]+?) County$", ln)
            name, county = (m.group(1), m.group(2)) if m else (ln, "")
            if name.strip().lower() == "vacant":
                out.append("vacant | %d | %s | | %s" % (n, role, county))
            else:
                out.append("judge | %d | %s | %s | %s"
                           % (n, role, person(name, "ks %d" % n), county))
    return out


def fetch_ne(reader):
    words = ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
             "Nine", "Ten", "Eleven", "Twelve"]
    out = []
    for n in range(1, 13):
        lines = reader.get("https://nebraskajudicial.gov/directories/district-map/"
                           "district-%d" % n)
        pat = re.compile(r"^District (?:Court )?%s (?:and Probation Dis[a-z]+ \w+ )?"
                         r"(?:is|are) comprised of (?:the following counties: )?(.+?)"
                         r"(?: [Cc]ount(?:y|ies))?\.$" % words[n - 1])
        hits = [pat.match(ln) for ln in lines]
        hits = [h for h in hits if h]
        if len(hits) != 1:
            wcc.fail(LABEL, "ne district %d: %d county sentences" % (n, len(hits)))
        names = re.split(r",\s*(?:and\s+)?|\s+and\s+", hits[0].group(1))
        out.append("district | %d | %s" % (n, ", ".join(c.strip() for c in names if c.strip())))
    lines = reader.get("https://nebraskajudicial.gov/directories/district-court-judges")
    unit = None
    for i, ln in enumerate(lines):
        m = re.match(r"^District: (\d+)$", ln)
        if m:
            unit = int(m.group(1))
        elif ln.startswith("Hon. ") and unit:
            county = lines[i + 2] if lines[i + 1] == "County:" else ""
            out.append("judge | %d | District Judge | %s | %s"
                       % (unit, person(ln[5:], "ne %d" % unit), county))
    return out


ND_DISTRICTS = ["Northwest", "North Central", "Northeast", "Northeast Central",
                "East Central", "Southeast", "South Central", "Southwest"]


def fetch_nd(reader):
    out = []
    lines = reader.get("https://www.ndcourts.gov/legal-resources/rules/ndsupctadminr/6")
    for i, ln in enumerate(lines):
        m = re.match(r"^(.+) Judicial District$", ln)
        if m and m.group(1) in ND_DISTRICTS and i + 1 < len(lines):
            c = re.match(r"^consists of the counties of (.+)\.$", lines[i + 1])
            if c:
                names = re.split(r",\s*(?:and\s+)?|\s+and\s+", c.group(1))
                out.append("district | %s | %s" % (m.group(1), ", ".join(
                    n.strip() for n in names if n.strip())))
    lines = reader.get("https://www.ndcourts.gov/district-court/district-court-judges")
    start = lines.index("District Court Judges", lines.index("District Court Judges") + 1)
    unit = None
    for ln in lines[start + 1:]:
        if ln == "Judicial Referees":
            break
        m = re.match(r"^(.+) District$", ln)
        if m and m.group(1) in ND_DISTRICTS:
            unit = m.group(1)
            continue
        if unit is None:
            continue
        role = "District Judge"
        if ln.endswith(" - Presiding Judge"):
            ln, role = ln[:-len(" - Presiding Judge")], "Presiding Judge"
        out.append("judge | %s | %s | %s | " % (unit, role, person(ln, "nd " + unit)))
    return out


def fetch_oh(reader):
    lines = reader.get(STATES["oh"]["source"])
    out, judges = [], []
    for i, ln in enumerate(lines):
        m = re.match(r"^(\w+) District Court of Appeals$", ln)
        if not m or m.group(1) not in ORDINALS or lines[i + 1] != "County:":
            continue
        n = ORDINALS.index(m.group(1)) + 1
        out.append("district | %d | %s" % (n, ", ".join(
            c.strip() for c in lines[i + 2].split(","))))
        j = lines.index("Appellate Judges:", i) + 1
        while lines[j] != "Online Resources":
            judges.append("judge | %d | Judge | %s | " % (n, person(lines[j], "oh %d" % n)))
            j += 1
    return out + judges


def fetch_sd(reader):
    out, judges = [], []
    roles = {"Presiding Circuit Judge": "Presiding Judge",
             "Circuit Judge": "Circuit Judge"}
    fabric = set(wcc.county_geometry("sd", LABEL))
    for n, word in enumerate(ORDINALS[:7], 1):
        w = word.lower()
        base = "https://ujs.sd.gov/court-finder/%s-judicial-circuit/" % w
        lines = reader.get(base)
        i = lines.index("%s Judicial Circuit Counties" % word) + 1
        names = []
        while re.sub(r" County$", "", lines[i]) in fabric:
            names.append(re.sub(r" County$", "", lines[i]))
            i += 1
        out.append("district | %d | %s" % (n, ", ".join(names)))
        # The Sixth Circuit's contacts page has its own address.
        kind = "court-contacts" if word == "Sixth" else "circuit-contacts"
        lines = reader.get(base + "%s-%s-judicial-circuit/" % (kind, w))
        for k, ln in enumerate(lines[:-1]):
            if ln.startswith("Judge ") and lines[k + 1] in roles:
                judges.append("judge | %d | %s | %s | " % (
                    n, roles[lines[k + 1]], person(ln[6:], "sd %d" % n)))
    return out + judges


CO_BASE = "https://www.coloradojudicial.gov"
# A judges page is a set of accordion sections, each a heading over contact
# cards; a card carries a name, usually a title, and its district. THE SECTION
# DECIDES WHO IS KEPT, because some cards print no title (Pitkin's Elise Myer
# sits under "District Court Judge" with none). The voters retain district
# judges, and Denver's juvenile and probate judges, by district; county court
# judges, magistrates and staff are not kept. A heading naming a judge that
# this file does not know stops the fetch.
CO_KEEP = re.compile(r"District Court (?:Chief )?Judges?\b|"
                     r"Juvenile Court (?:Presiding )?Judges?\b|^Presiding Judge$")
CO_SKIP = re.compile(r"^County Court Judges?\b|^Magistrates?\b|Court Magistrates?\b")
CO_DENVER = {"Denver District Court": "denver-district/denver-district-court-judges-and-staff",
             "Denver Juvenile Court": "denver-juvenile/denver-juvenile-judges-and-staff",
             "Denver Probate Court": "denver-probate/denver-probate-judges-and-staff"}


def co_text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def co_sections(page):
    """[(heading, [(name, title or None, [districts])])] of one judges page."""
    out = []
    for item in re.split(r"<details\b", page)[1:]:
        head = re.search(r"<summary\b[^>]*>(.*?)</summary>", item, re.S)
        if not head:
            continue
        cards = []
        for card in re.findall(r"<article\b[^>]*node--type-contact[^>]*>(.*?)</article>",
                               item, re.S):
            name = re.search(r"field--name-title[^>]*>(.*?)</span>", card, re.S)
            title = re.search(r"field--name-field-contact-title[^>]*>(.*?)</div>", card, re.S)
            unit = re.search(r"field--name-field-district[^>]*>(.*?)</div>\s*</div>", card, re.S)
            cards.append((co_text(name.group(1)) if name else None,
                          co_text(title.group(1)) if title else None,
                          [co_text(x) for x in re.findall(r'field__item"[^>]*>([^<]*)',
                                                          unit.group(1))] if unit else []))
        out.append((co_text(head.group(1)), cards))
    return out


def co_role(title, heading, page):
    said = title if title and title != "Judge" else heading
    if "Chief" in said or "Chief" in heading:
        return "Chief Judge"
    if "Juvenile" in said:
        return "Presiding Judge, Juvenile Court" if "Presiding" in said else "Juvenile Court Judge"
    if "Presiding" in said and "probate" in page:
        return "Presiding Judge, Probate Court"
    if "District" in said:
        return "District Judge"
    wcc.fail(LABEL, "co: %s: no role reads from %r under %r" % (page, title, heading))


def co_key(name):
    """One judge printed two ways on one page ("Anne K. Norrdin", "Anne Norrdin")."""
    words = re.sub(r'"[^"]*"|\b[A-Z]\.', " ", name).lower().split()
    return (words[0], words[-1])


def fetch_co(reader):
    lines = reader.get(CO_BASE + "/trial-courts-district")
    i = lines.index("Trial Courts by District", lines.index("Trial Courts By District")) + 1
    counties, pages, unit = {}, {}, None
    for ln in lines[i:]:
        if ln == "Colorado Judicial Branch":
            break
        if ln == "Image":  # the map's placeholder text, before the first district
            continue
        m = re.match(r"^(\d+)(?:st|nd|rd|th) Judicial District$", ln)
        if m:
            unit = int(m.group(1))
            counties[unit] = []
        elif ln in CO_DENVER:
            if "Denver" not in counties[unit]:
                counties[unit].append("Denver")
            pages.setdefault(unit, []).append(CO_DENVER[ln])
        elif ln == "Denver County Court":
            continue  # the mayor appoints its judges; not a district court
        elif ln.endswith(" County") and unit:
            name = ln[:-len(" County")]
            counties[unit].append(name)
            pages.setdefault(unit, []).append(name.lower().replace(" ", "-") + "-county")
        else:
            wcc.fail(LABEL, "co: %r on the district list is not a district, "
                     "county or Denver court" % ln)
    out = ["district | %d | %s" % (d, ", ".join(counties[d])) for d in sorted(counties)]
    want = "%s Judicial District"
    for d in sorted(pages):
        seen = {}
        for page in pages[d]:
            if "/" not in page:
                # A county's judges page is linked from its court's page, and
                # its address does not always follow the county's name.
                links = sorted(set(re.findall(
                    r'href="(?:%s)?/courts/trial-courts/(%s/[a-z-]*judges-and-staff)[?"]'
                    % (re.escape(CO_BASE), page), reader.html(
                        CO_BASE + "/courts/trial-courts/" + page))))
                if len(links) != 1:
                    wcc.fail(LABEL, "co: %s links %d judges pages" % (page, len(links)))
                page = links[0]
            for heading, cards in co_sections(reader.html(CO_BASE + "/courts/trial-courts/" + page)):
                if not CO_KEEP.search(heading):
                    if "Judge" in heading and not CO_SKIP.search(heading):
                        wcc.fail(LABEL, "co: %s has a section this file does not "
                                 "know: %r" % (page, heading))
                    continue
                for name, title, units in cards:
                    if want % ordinal_suffix(d) not in units:
                        wcc.fail(LABEL, "co: %s lists %s under %s, not district %d"
                                 % (page, name, units, d))
                    name = person(re.sub(r"^Judge ", "", name or ""), "co %d" % d)
                    key, role = co_key(name), co_role(title, heading, page)
                    if key in seen:  # the longer name, and a chief stays chief
                        name = max(name, seen[key][0], key=len)
                        role = "Chief Judge" if "Chief Judge" in (role, seen[key][1]) \
                            else seen[key][1]
                    seen[key] = (name, role)
        for name, role in seen.values():
            out.append("judge | %d | %s | %s | " % (d, role, name))
    return out


ID_WORDS = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh"]


def fetch_id(reader):
    """Counties and seat counts from Idaho Code 1-802 to 1-808; the judges from
    the Supreme Court's judicial directory, whose page fills its list from
    data it carries inline (Nuxt's payload), read here the way the page reads
    it. The directory's district judges must fill exactly the seats the
    statute sets; a difference stops the fetch for a person to read."""
    out, seats = [], {}
    for n, word in enumerate(ID_WORDS, 1):
        lines = reader.get("https://legislature.idaho.gov/statutesrules/idstat/"
                           "title1/t1ch8/sect1-80%d/" % (n + 1))
        c = [re.match(r"^\(1\) The %s judicial district shall consist of the "
                      r"counties of (.+)\.$" % word, ln) for ln in lines]
        k = [re.match(r"^\(2\) The %s judicial district shall have .+ \((\d+)\) "
                      r"district judges\.$" % word, ln) for ln in lines]
        c, k = [x for x in c if x], [x for x in k if x]
        if len(c) != 1 or len(k) != 1:
            wcc.fail(LABEL, "id district %d: %d county and %d seat sentences"
                     % (n, len(c), len(k)))
        names = re.split(r",\s*(?:and\s+)?|\s+and\s+", c[0].group(1))
        out.append("district | %d | %s" % (n, ", ".join(x.strip() for x in names if x.strip())))
        seats[n] = int(k[0].group(1))
    page = reader.html("https://isc.idaho.gov/about-the-courts/judicial-directory")
    m = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
    if not m:
        wcc.fail(LABEL, "id: the judicial directory carries no inline data")
    data = json.loads(m.group(1))

    def val(i):
        v = data[i]
        return data[v["value"]] if isinstance(v, dict) and "value" in v else v
    roles = {"District Judge": "District Judge",
             "Administrative District Judge": "Administrative District Judge"}
    found = {}
    for rec in data:
        if not (isinstance(rec, dict) and {"name", "function", "districts"} <= set(rec)):
            continue
        role = roles.get(val(rec["function"]))
        if not role:
            continue
        d = re.match(r"^(\w+) JUDICIAL DISTRICT$", val(rec["districts"]))
        if not d or d.group(1).lower() not in ID_WORDS:
            wcc.fail(LABEL, "id: %r is in no district this file knows" % val(rec["name"]))
        n = ID_WORDS.index(d.group(1).lower()) + 1
        name = val(rec["name"]).strip()
        found.setdefault(n, []).append(
            "vacant | %d | %s | | " % (n, role) if name.lower() == "vacant" else
            "judge | %d | %s | %s | " % (n, role, person(name, "id %d" % n)))
    for n in sorted(seats):
        if len(found.get(n, [])) != seats[n]:
            wcc.fail(LABEL, "id district %d: the directory lists %d district judge seats, "
                     "the statute sets %d" % (n, len(found.get(n, [])), seats[n]))
        out.extend(found[n])
    return out


UT_BASE = "https://www.utcourts.gov/en"
# A name the court prints in capitals with a part no rule re-cases correctly,
# spelled as a government page spells it (read 2026-11-27).
UT_SPELLED = {
    # senate.utah.gov/tag/public-comment-on-6th-district-appointee-robert-van-dyke/
    "ROBERT VAN DYKE": "Robert Van Dyke",
}
UT_AMBIGUOUS = re.compile(r"\b(?:MC|MAC|VAN|VON|DE|DI|DU|DA|DEL|LA|LE|ST)\b|\bMC[A-Z]|'")
UT_ROLES = (("ASSOCIATE PRESIDING JUDGE ", "Associate Presiding Judge"),
            ("PRESIDING JUDGE ", "Presiding Judge"), ("JUDGE ", "District Judge"))


def ut_case(caps):
    """The display form of a name the court prints in capitals, or a stop."""
    if caps in UT_SPELLED:
        return UT_SPELLED[caps]
    if UT_AMBIGUOUS.search(caps):
        wcc.fail(LABEL, "ut: %r is printed in capitals with a part no rule re-cases; "
                 "add it to UT_SPELLED with the page that spells it" % caps)
    out = []
    for word in caps.split():
        bare = word.strip("(),")
        if re.match(r"^(?:[A-Z]\.)+$", bare) or bare in ("II", "III", "IV"):
            out.append(word)
        elif bare in ("JR.", "SR."):
            out.append(word.replace(bare, bare.capitalize()))
        else:
            out.append(word.replace(bare, "-".join(x.capitalize() for x in bare.split("-"))))
    return " ".join(out)


def fetch_ut(reader):
    """Counties from the courts' map of judicial districts; judges from the
    district court judges' page, which prints every name in capitals (court
    commissioners are listed there too and are not kept)."""
    lines = reader.get(UT_BASE + "/about/miscellaneous/directory/map-of-judicial-districts.html")
    i = lines.index("List of Counties Within Districts")
    counties, unit = {}, None
    for ln in lines[i:]:
        if ln == "Back to Top":
            break
        m = re.match(r"^(\d)(?:st|nd|rd|th) Judicial District$", ln)
        if m:
            unit = int(m.group(1))
            counties[unit] = []
            continue
        c = re.match(r"^([A-Z][A-Za-z ]+) County$", ln)
        if c and unit:
            counties[unit].append(c.group(1))
    out = ["district | %d | %s" % (d, ", ".join(counties[d])) for d in sorted(counties)]
    lines = reader.get(UT_BASE + "/courts/other-court-info/judges-bios/district-courts.html")
    word, seen = None, set()
    for k, ln in enumerate(lines[:-1]):
        m = re.match(r"^(\w+) District Court Judges$", ln)
        if m:
            word = m.group(1)
            continue
        if ln == "Back to Top":
            word = None
        if not word or lines[k + 1] != "%s District Court Judge" % word or ln in seen:
            continue
        seen.add(ln)
        if ln.startswith("COMMISSIONER "):
            continue
        role = next((r for pre, r in UT_ROLES if ln.startswith(pre)), None)
        if not role:
            wcc.fail(LABEL, "ut: %r begins with no title this file knows" % ln)
        caps = ln[len(next(pre for pre, r in UT_ROLES if ln.startswith(pre))):]
        n = ORDINALS.index(word) + 1
        out.append("judge | %d | %s | %s | " % (n, role, person(ut_case(caps), "ut %d" % n)))
    return out


WY_BASE = "https://www.wyocourts.gov"


def fetch_wy(reader):
    """Counties from the Judicial Branch's Find a Court list ("District Court,
    2nd Judicial District, Albany County"); judges from each county's district
    court page, whose Judges section names the judges who sit there as
    "Honorable <name>". A district's judges are the ones its counties' pages
    name, each once."""
    page = reader.html(WY_BASE + "/find-a-court/")
    counties, links = {}, {}
    for ln in page_lines(page):
        m = re.match(r"^District Court, (\d)(?:st|nd|rd|th) Judicial District, (.+) County$", ln)
        if m and m.group(2) not in counties.setdefault(int(m.group(1)), []):
            counties[int(m.group(1))].append(m.group(2))
    for href in sorted(set(re.findall(
            r'href="(%s/court/district-court-(\d)(?:st|nd|rd|th)-judicial-district-[a-z-]+-county/)"'
            % re.escape(WY_BASE), page))):
        links.setdefault(int(href[1]), []).append(href[0])
    out = ["district | %d | %s" % (d, ", ".join(counties[d])) for d in sorted(counties)]
    for d in sorted(counties):
        if len(links.get(d, [])) != len(counties[d]):
            wcc.fail(LABEL, "wy district %d: %d counties, %d court pages"
                     % (d, len(counties[d]), len(links.get(d, []))))
        seen = []
        for url in links[d]:
            lines = reader.get(url)
            i = lines.index("Judges") + 1
            while i < len(lines) and lines[i].startswith("Honorable "):
                name = person(lines[i][len("Honorable "):], "wy %d" % d)
                if name not in seen:
                    seen.append(name)
                i += 1
                while i < len(lines) and not lines[i].startswith("Honorable ") \
                        and lines[i] != "Courtroom Technology":
                    i += 1
        for name in seen:
            out.append("judge | %d | District Judge | %s | " % (d, name))
    # The district courts page states the statewide count; the pages must agree.
    said = [re.search(r"There are (\d+) district judges in the state", ln)
            for ln in reader.get(WY_BASE + "/district-courts/")]
    said = [int(m.group(1)) for m in said if m]
    named = sum(1 for ln in out if ln.startswith("judge "))
    if said != [named]:
        wcc.fail(LABEL, "wy: the court pages name %d district judges, the district "
                 "courts page says %s" % (named, said))
    return out


NM_WORDS = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh",
            "Eighth", "Ninth", "Tenth", "Eleventh", "Twelfth", "Thirteenth"]
NM_SPELLING = {"DeBaca": "De Baca", "Dona Ana": "Doña Ana"}
NM_TERMS = "https://nmcourts.gov/resources/judicial-terms-and-retention-schedule/"


def fetch_nm(reader):
    """Counties from the Judicial Branch's Courts by District page ("First
    Judicial District" / "For Los Alamos, Rio Arriba County and Santa Fe
    County"); judges from the District Court Staggered Terms list the Judicial
    Performance Evaluation Commission keeps (a PDF linked from the Judicial
    Terms and Retention Schedule page, renamed with each update), one row per
    division: "Chief Judge Bryan Biedscheid 6 2020 2024 12/31/30", or "Vacant".
    Each district's divisions must run from 1 with none skipped."""
    lines = reader.get("https://nmcourts.gov/courts-by-district/")
    counties = {}
    for k, ln in enumerate(lines[:-1]):
        m = re.match(r"^(\w+) Judicial District$", ln)
        if not m or m.group(1) not in NM_WORDS:
            continue
        c = re.match(r"^(?:For|Serving) (.+)$", lines[k + 1])
        if not c:
            wcc.fail(LABEL, "nm: %r is not followed by its counties" % ln)
        names = [re.sub(r" County$", "", x.strip()) for x in
                 re.split(r",\s*(?:and\s+)?|\s+and\s+", c.group(1)) if x.strip()]
        counties[NM_WORDS.index(m.group(1)) + 1] = [NM_SPELLING.get(x, x) for x in names]
    if sorted(counties) != list(range(1, 14)):
        wcc.fail(LABEL, "nm: the Courts by District page lists districts %s" % sorted(counties))
    out = ["district | %d | %s" % (d, ", ".join(counties[d])) for d in sorted(counties)]
    pdfs = sorted(set(re.findall(r'href="(https://nmcourts\.gov/wp-content/uploads/[^"]*'
                                 r'District-Court-Staggered-Terms[^"]*\.pdf)"',
                                 reader.html(NM_TERMS))))
    if len(pdfs) != 1:
        wcc.fail(LABEL, "nm: %d district court terms lists linked from %s" % (len(pdfs), NM_TERMS))
    reader.sc.require_robots_once(pdfs[0], reader.headers["User-Agent"],
                                  headers=reader.headers, label=LABEL)
    body = reader.sc.fetch(pdfs[0], reader.headers, timeout=60).content
    if not body.startswith(b"%PDF"):
        # nmcourts.gov answered this client with a challenge page at times on
        # 2026-11-27; that is an access control, never worked around.
        wcc.fail(LABEL, "nm: %s answered with %r, not a PDF; stopping" % (pdfs[0], body[:40]))
    import pypdf
    out += nm_terms_rows("\n".join(
        pg.extract_text() for pg in pypdf.PdfReader(io.BytesIO(body)).pages))
    return out


def nm_terms_rows(text):
    d, divisions, out = None, {}, []
    for ln in text.splitlines():
        ln = ln.strip()
        head = re.match(r"^(\d+)(?:st|nd|rd|th) District Court Division", ln)
        if head:
            d = int(head.group(1))
            divisions[d] = []
            continue
        row = re.match(r"^(Chief Judge |Judge )?(.+?) (\d+)(?: \d{4})?(?: \d{4}| Appointed\*)? "
                       r"\d\d/\d\d/\d\d(?: \*New seat)?$", ln)
        if not row or d is None:
            continue
        divisions[d].append(int(row.group(3)))
        if row.group(2) == "Vacant":
            out.append("vacant | %d | District Judge | | " % d)
        else:
            role = "Chief Judge" if row.group(1) == "Chief Judge " else "District Judge"
            out.append("judge | %d | %s | %s | " % (d, role, person(row.group(2), "nm %d" % d)))
    if sorted(divisions) != list(range(1, 14)):
        wcc.fail(LABEL, "nm: the terms list has districts %s" % sorted(divisions))
    for d, divs in sorted(divisions.items()):
        if divs != list(range(1, len(divs) + 1)):
            wcc.fail(LABEL, "nm district %d: the terms list's divisions read %s; a row "
                     "is printed a new way" % (d, divs))
    return out

MT_BASE = "https://courts.mt.gov"
# Where a page's district judges end (a standing master can sit among them).
MT_STOP = re.compile(r"^(?:District Court Calendar|Clerk of District Court|District Court Clerk "
                     r"and Location|Court Administrator|Limited Courts of Jurisdiction)$")


def fetch_mt(reader):
    """Counties from the District Courts page's county menu, which sends each
    county to its district's Court Locator page; judges from each of those
    pages, which name the district judges "Hon. <name>" (one page in
    capitals) above the standing masters and clerks. A judge printed twice
    (the Eighth also lists them for its calendar) is kept once. The District
    Courts page states the number of district judges; the pages must agree."""
    page = reader.html(MT_BASE + "/courts/dcourt/")
    counties = {}
    for n, name in re.findall(r'<option value="\.\./\.\./CourtLocator/(\d+)(?:st|nd|rd|th)'
                              r'JudicialDistrict">([^<]+) County</option>', page):
        counties.setdefault(int(n), []).append(html.unescape(name))
    out = ["district | %d | %s" % (d, ", ".join(counties[d])) for d in sorted(counties)]
    for d in sorted(counties):
        lines = reader.get("%s/CourtLocator/%sJudicialDistrict" % (MT_BASE, ordinal_suffix(d)))
        seen = {}
        for ln in lines[lines.index("%s Judicial District" % ordinal_suffix(d)) + 1:]:
            if MT_STOP.match(ln):
                break
            m = re.match(r"^Hon\. (.+?)(?: - Dept \d+)?$", ln, re.I)
            if m:
                name = m.group(1) if re.search(r"[a-z]", m.group(1)) else ut_case(m.group(1))
                key = co_key(name)
                if len(name) > len(seen.get(key, "")):
                    seen[key] = name
        if not seen:
            wcc.fail(LABEL, "mt district %d: no judge on its Court Locator page" % d)
        for name in seen.values():
            out.append("judge | %d | District Judge | %s | " % (d, person(name, "mt %d" % d)))
    said = [int(m.group(1)) for m in re.finditer(r"served by (\d+) District Court Judges",
                                                  " ".join(page_lines(page)))]
    named = sum(1 for ln in out if ln.startswith("judge "))
    if said != [named]:
        wcc.fail(LABEL, "mt: the Court Locator pages name %d district judges, the District "
                 "Courts page says %s" % (named, said))
    return out

WA_DIR = "https://www.courts.wa.gov/court_dir/"
WA_RCW = ("https://lawfilesext.leg.wa.gov/Law/RCW/RCW%20%20%202%20%20TITLE/"
          "RCW%20%20%202%20.%2008%20%20CHAPTER/RCW%20%20%202%20.%2008%20.{}.htm")
WA_WORDS = {w: i + 1 for i, w in enumerate(
    "one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen twenty".split())}
WA_WORDS.update({"twenty-four": 24, "fifty-eight": 58})
WA_JUDGE = re.compile(r"^(.+?), (Presiding Judge|Assistant Presiding Judge|Chief Judge|Judge)"
                      r"(?:, Department \w+)?$")


def wa_counties(text):
    """ "Ferry,Pend Oreille,Stevens Counties" -> ["Ferry", "Pend Oreille", "Stevens"]"""
    text = re.sub(r" Count(?:y|ies)$", "", text)
    return [x.strip() for x in re.split(r",\s*(?:and\s+)?|\s+and\s+", text) if x.strip()]


def fetch_wa(reader):
    """Courts from the Court Directory's Judicial Districts Reference List
    (each line one superior court: a county, or counties sharing one court);
    judges from each county's directory page, whose Superior Court section
    (with King's Kent courthouse and juvenile court beneath it) names each
    judge "<name>, Judge" above the District Court. Counties that share a
    court must list the same judges. The number of judges each court may have
    is set by RCW 2.08.061 to 2.08.065, and the directory may list fewer (a
    seat open or not yet funded) but never more."""
    lines = reader.get(WA_DIR + "?fa=court_dir.judicialdistricts")
    i = lines.index("Judicial Districts Reference List") + 1
    courts = {}
    for ln in lines[i:]:
        if not re.search(r"Count(?:y|ies)$", ln):
            break
        names = wa_counties(ln)
        key = (names[0] + " County" if len(names) == 1 else
               ", ".join(names[:-1]) + " and " + names[-1] + " Counties")
        courts[key] = names
    out = ["district | %s | %s" % (k, ", ".join(v)) for k, v in courts.items()]
    seats = {}
    for sec in ("061", "062", "063", "064", "065"):
        text = " ".join(reader.get(WA_RCW.format(sec)))
        text = text[:text.index("[")]
        for who, n in re.findall(r"in the (?:county|counties) of ([A-Z][A-Za-z ,]+?)(?: jointly)?,? "
                                 r"(?:no more than )?([\w-]+) judges? of the superior court", text):
            seats[frozenset(wa_counties(who))] = int(n) if n.isdigit() else WA_WORDS[n]
    page = reader.html(WA_DIR + "?fa=court_dir.county")
    org = {html.unescape(re.sub("<[^>]+>", "", name)).strip(): href for href, name in re.findall(
        r'<a[^>]+href="(/court_dir/orgs/\d+\.html)"[^>]*>(.*?)</a>', page, re.S)}
    for key, names in courts.items():
        if frozenset(names) not in seats:
            wcc.fail(LABEL, "wa: RCW 2.08.061 to .065 set no number of judges for %s" % key)
        lists = []
        for county in names:
            if county not in org:
                wcc.fail(LABEL, "wa: the directory links no page for %s County" % county)
            ln = reader.get("https://www.courts.wa.gov" + org[county])
            a = ln.index("Superior Court")
            b = next(k for k in range(a, len(ln)) if ln[k] in ("District Court", "Municipal Courts"))
            lists.append([m.groups() for m in map(WA_JUDGE.match, ln[a:b])
                          if m and m.group(1) != "Vacant"])
        if len({frozenset(co_key(n) for n, _ in judges) for judges in lists}) != 1:
            wcc.fail(LABEL, "wa: the counties of %s list different judges" % key)
        judges = list({co_key(n): (n, t) for n, t in lists[0]}.values())
        if not judges or len(judges) > seats[frozenset(names)]:
            wcc.fail(LABEL, "wa: %s lists %d judges; RCW sets %d" % (key, len(judges), seats[frozenset(names)]))
        for name, title in judges:
            role = "Superior Court Judge" if title == "Judge" else title
            out.append("judge | %s | %s | %s | " % (key, role, person(name, "wa %s" % key)))
    if len(seats) != len(courts):
        wcc.fail(LABEL, "wa: RCW sets judges for %d courts, the reference list has %d" % (len(seats), len(courts)))
    return out

PA_BASE = "https://www.pacourts.us"
PA_911 = ("https://www.palegis.us/statutes/consolidated/view-statute?txtType=PDF&ttl=42"
          "&div=00.&chpt=009.&sctn=011.&subsctn=000.")
_PA_ONES = "first second third fourth fifth sixth seventh eighth ninth".split()
_PA_TENS = {"tenth": 10, "twentieth": 20, "thirtieth": 30, "fortieth": 40, "fiftieth": 50, "sixtieth": 60}
PA_ORDINAL = dict(_PA_TENS, **{w: i + 1 for i, w in enumerate(_PA_ONES)})
PA_ORDINAL.update({w: 11 + i for i, w in enumerate(
    "eleventh twelfth thirteenth fourteenth fifteenth sixteenth seventeenth eighteenth nineteenth".split())})
for _tens, _n in (("twenty", 20), ("thirty", 30), ("forty", 40), ("fifty", 50)):
    PA_ORDINAL.update({"%s-%s" % (_tens, w): _n + i + 1 for i, w in enumerate(_PA_ONES)})


# Judges the Common Pleas feed lists who sit on another court, checked by hand
# against that court's own page; the fetch fails when one leaves the feed.
PA_OTHER_COURT = {
    # https://www.courts.phila.gov/directory/pj, read 2026-11-27: "President
    # Judge, T. Francis Shields ... Court: Municipal Court".
    "T. Francis Shields": "Philadelphia Municipal Court",
}


def fetch_pa(reader):
    """Counties from the Unified Judicial System's Judicial Districts page
    (its numerical table: district, county, county number); the number of
    judges each district's court of common pleas has from 42 Pa.C.S. section
    911, read as the General Assembly's PDF; judges from the feed the Common
    Pleas Judges page fills its table from (/api/judgeView, judge type 1,
    fifteen at a time, as the page asks). A judge is placed by the county the
    feed gives, since one record carries no district number. Senior judges
    (retired judges the Supreme Court lets keep serving) hold no seat and are
    not kept. The feed lists sitting judges, so a district may show fewer than
    the statute's number, never more."""
    lines = reader.get(PA_BASE + "/courts/courts-of-common-pleas/judicial-districts")
    i = lines.index("County No.", lines.index("Judicial Districts in numerical order")) + 1
    counties, district_of = {}, {}
    while re.match(r"^\d\d$", lines[i]) and re.match(r"^\d+$", lines[i + 2]):
        d, county = int(lines[i]), lines[i + 1]
        counties.setdefault(d, []).append(county)
        district_of[county] = d
        i += 3
    out = ["district | %d | %s" % (d, ", ".join(counties[d])) for d in sorted(counties)]
    reader.sc.require_robots_once(PA_911, reader.headers["User-Agent"],
                                  headers=reader.headers, label=LABEL)
    body = reader.sc.fetch(PA_911, reader.headers, timeout=60).content
    if not body.startswith(b"%PDF"):
        wcc.fail(LABEL, "pa: %s answered with %r, not a PDF" % (PA_911, body[:40]))
    import pypdf
    text = "\n".join(pg.extract_text() for pg in pypdf.PdfReader(io.BytesIO(body)).pages)
    text = text[text.index("§ 911. Courts of common pleas."):text.index("(a.1)")]
    seats = {PA_ORDINAL[w.lower()]: int(n) for n, w in
             re.findall(r"^(\d+)([A-Z][a-z]+(?:-[a-z]+)?)$", text, re.M)}
    if sorted(seats) != sorted(counties):
        wcc.fail(LABEL, "pa: section 911 sets judges for %d districts, the courts list %d"
                 % (len(seats), len(counties)))
    judges, vacant, other, skip = {}, [], set(), 0
    while True:
        page = json.loads(reader.html(PA_BASE + "/api/judgeView?searchText=&judgeType=1"
                                      "&searchType=1&take=15&skip=%d&hasMore=true" % skip))
        for rec in (x["judge"] for x in page["judges"]):
            if rec.get("title") == "Senior Judge":
                continue
            if rec["countyName"] not in district_of:
                wcc.fail(LABEL, "pa: a judge in %r, a county the district table lacks" % rec["countyName"])
            d = district_of[rec["countyName"]]
            if rec.get("judicialDistrict") and int(rec["judicialDistrict"]) != d:
                wcc.fail(LABEL, "pa: %r is in district %s by the feed, %d by county"
                         % (rec["fullName"], rec["judicialDistrict"], d))
            title = rec.get("title") or ""
            role = ("President Judge" if title == "President Judge" else
                    "Administrative Judge" if title.startswith("Administrative Judge") else "Judge")
            name = re.sub(r"^Honorable ", "", re.sub(r"\s+", " ", rec["fullName"]).strip())
            if name.startswith("(Vacant)"):
                # The feed prints an open seat as "(Vacant) <last holder>", with
                # that holder's title; the open seat itself is a judge's seat.
                vacant.append((d, "Judge"))
                continue
            name = re.sub(r",? Esq\.$", "", name)
            if name in PA_OTHER_COURT:
                other.add(name)
                continue
            key = (d,) + co_key(name)
            if key not in judges or role != "Judge":
                judges[key] = (d, role, name)
        if not page["judges"] or not page["nextLinkParams"]["hasMore"]:
            break
        skip = page["nextLinkParams"]["skip"]
    report = ["%s is no longer in the feed; remove him or her from PA_OTHER_COURT" % n
              for n in sorted(set(PA_OTHER_COURT) - other)]
    for d in sorted(counties):
        mine = [j for j in judges.values() if j[0] == d]
        open_ = [v for v in vacant if v[0] == d]
        if not mine or len(mine) > seats[d]:
            report.append("district %d: %d judges, section 911 sets %d" % (d, len(mine), seats[d]))
        if len(mine) + len(open_) > seats[d]:
            # Seen 2026-11-27 in Chester (15 of 15 named) and Columbia-Montour
            # (3 of 3): an open-seat record left beside a full bench. Section
            # 911 is the number of seats, so no seat beyond it is shown open.
            print("build-state-courts: pa district %d: %d judges fill the %d seats section 911 "
                  "sets; %d open-seat record(s) not shown" % (d, len(mine), seats[d],
                                                              len(mine) + len(open_) - seats[d]))
            open_ = open_[:seats[d] - len(mine)]
        for _, role, name in sorted(mine, key=lambda j: (j[1] == "Judge", j[2])):
            out.append("judge | %d | %s | %s | " % (d, role, person(name, "pa %d" % d)))
        for _, role in open_:
            out.append("vacant | %d | %s | | " % (d, role))
    if report:
        wcc.fail(LABEL, "pa: " + "; ".join(report))
    return out


WV_BASE = "https://www.courtswv.gov"


def fetch_wv(reader):
    """Circuits, their counties and their judges from the Court Circuit Map
    PDF the Circuit Courts page links ("WEST VIRGINIA CIRCUIT COURT CIRCUITS",
    each circuit as "<n>th Judicial Circuit", its counties in parentheses, then
    its judges one per line). The PDF's file name carries the month it was
    posted, so it is found from the page each time. The page states the
    statewide number of circuit judges, and the PDF must name that many."""
    page = reader.html(WV_BASE + "/lower-courts/circuit-courts")
    hrefs = re.findall(r'href="([^"]+\.pdf)"[^>]*>[^<]*Circuit Court Map', page)
    if len(hrefs) != 1:
        wcc.fail(LABEL, "wv: the Circuit Courts page links %d circuit court map PDFs" % len(hrefs))
    url = hrefs[0] if hrefs[0].startswith("https://") else WV_BASE + hrefs[0]
    reader.sc.require_robots_once(url, reader.headers["User-Agent"],
                                  headers=reader.headers, label=LABEL)
    body = reader.sc.fetch(url, reader.headers, timeout=60).content
    if not body.startswith(b"%PDF"):
        wcc.fail(LABEL, "wv: %s answered with %r, not a PDF" % (url, body[:40]))
    import pypdf
    text = "\n".join(pg.extract_text() for pg in pypdf.PdfReader(io.BytesIO(body)).pages)
    out = wv_rows(text[text.index("WEST VIRGINIA CIRCUIT COURT CIRCUITS"):])
    said = [int(m.group(1)) for m in re.finditer(
        r"divided into \d+ circuits with (\d+) circuit judges", " ".join(page_lines(page)))]
    named = sum(1 for ln in out if ln.startswith("judge "))
    if said != [named]:
        wcc.fail(LABEL, "wv: the map names %d circuit judges, the Circuit Courts page says %s"
                 % (named, said))
    return out


def wv_rows(text):
    """Excerpt lines from the map PDF's list of circuits."""
    out, d, counties, judges = [], None, None, {}
    for ln in (x.strip() for x in text.splitlines()):
        m = re.match(r"^(.*?)(\d+)(?:st|nd|rd|th) Judicial Circuit$", ln)
        if m:
            if m.group(1):  # a judge's name and the next heading on one line
                judges[d].append(m.group(1).strip())
            d, counties = int(m.group(2)), ""
            judges[d] = []
            continue
        if d is None or not ln:
            continue
        if counties is not None and (counties or ln.startswith("(")):
            counties += " " + ln
            if ln.endswith(")"):
                out.append("district | %d | %s" % (d, re.sub(r"\s+", " ", counties.strip(" ()"))))
                counties = None
            continue
        judges[d].append(ln)
    if sorted(judges) != list(range(1, len(judges) + 1)):
        wcc.fail(LABEL, "wv: the map's circuits are not numbered 1 to %d" % len(judges))
    for n in sorted(judges):
        if not judges[n]:
            wcc.fail(LABEL, "wv circuit %d: the map names no judge" % n)
        for name in judges[n]:
            out.append("judge | %d | Circuit Judge | %s | " % (n, person(name, "wv %d" % n)))
    return out


OR_WORDS = ("first second third fourth fifth sixth seventh eighth ninth tenth eleventh "
            "twelfth thirteenth fourteenth fifteenth sixteenth seventeenth eighteenth "
            "nineteenth twentieth twenty-first twenty-second twenty-third twenty-fourth "
            "twenty-fifth twenty-sixth twenty-seventh").split()
OR_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
              "seven": 7, "eight": 8, "nine": 9}


def fetch_or(reader):
    """Counties and seats from ORS 3.012; judges from the Judicial Department's
    judges list, which its Judges page fills from a SharePoint list, read here
    through the same list's REST address the page's table reads. A judge who
    sits in two counties is listed once per county and kept once. The list's
    circuit judges must fill exactly the seats the statute sets."""
    text = " ".join(reader.get("https://www.oregonlegislature.gov/bills_laws/ors/ors003.html"))
    i = text.index("3.012 Judicial districts. (1)")
    rows = re.findall(r"\(\w+\) The ([a-z-]+) judicial district consists of (?:the counties "
                      r"of )?(.+?) and has (\w+) judges?\.", text[i:i + 8000])
    out, seats = [], {}
    for word, names, n in rows:
        d = OR_WORDS.index(word) + 1
        names = [re.sub(r" County$", "", x.strip()) for x in
                 re.split(r",\s*(?:and\s+)?|\s+and\s+", names) if x.strip()]
        out.append("district | %d | %s" % (d, ", ".join(names)))
        seats[d] = int(n) if n.isdigit() else OR_NUMBERS[n]
    resp = reader.sc.fetch(
        "https://www.courts.oregon.gov/courts/_api/web/GetList('/courts/Lists/Judges')/items?$top=1000",
        dict(reader.headers, Accept="application/json;odata=nometadata"), timeout=60)
    roles = {"Circuit Court Judge": "Circuit Judge",
             "Circuit Court Presiding Judge": "Presiding Judge",
             "Circuit Court Acting Presiding Judge": "Acting Presiding Judge"}
    found = {}
    for rec in resp.json()["value"]:
        if rec.get("Category") != "Circuit Court":
            continue
        role = roles.get(rec.get("Job_x0020_Title"))
        if not role:
            wcc.fail(LABEL, "or: a circuit court title this file does not know: %r"
                     % rec.get("Job_x0020_Title"))
        d = int(rec["Judicial_x0020_District"])
        if (rec.get("Title") or "").strip() == "Vacant":
            # one record per vacant position, so the position is the key
            key, line = ("vacant", rec.get("Position")), "vacant | %d | %s | | " % (d, role)
        else:
            # the name as the page's table shows it
            name = person(html.unescape(re.sub(r"<[^>]+>", " ", rec.get("FullName") or "")),
                          "or %d" % d)
            key, line = name, "judge | %d | %s | %s | " % (d, role, name)
        if key not in [k for k, x in found.get(d, [])]:
            found.setdefault(d, []).append((key, line))
    for d in sorted(seats):
        if len(found.get(d, [])) != seats[d]:
            wcc.fail(LABEL, "or district %d: the judges list holds %d circuit judge seats, "
                     "ORS 3.012 sets %d" % (d, len(found.get(d, [])), seats[d]))
        out.extend(line for key, line in found[d])
    return out


FETCHERS = {"co": fetch_co, "id": fetch_id, "ut": fetch_ut, "wy": fetch_wy, "nm": fetch_nm, "mt": fetch_mt, "wa": fetch_wa, "pa": fetch_pa, "wv": fetch_wv,
            "or": fetch_or, "ks": fetch_ks, "ne": fetch_ne, "nd": fetch_nd, "oh": fetch_oh,
            "sd": fetch_sd}

SOURCES_READ = {
    "wv": "https://www.courtswv.gov/lower-courts/circuit-courts and the circuit court map PDF it links (circuits, counties and judges; the page's statewide count of circuit judges)",
    "pa": "https://www.pacourts.us/courts/courts-of-common-pleas/judicial-districts (counties), 42 Pa.C.S. section 911 on palegis.us (each court's number of judges) and https://www.pacourts.us/api/judgeView?judgeType=1, the feed the Common Pleas Judges page reads (judges; senior judges are not kept)",
    "wa": "https://www.courts.wa.gov/court_dir/?fa=court_dir.judicialdistricts (the superior courts and their counties), each county's Court Directory page (superior court judges; commissioners are not kept) and RCW 2.08.061 to 2.08.065 on lawfilesext.leg.wa.gov (the number of judges each court may have)",
    "mt": "https://courts.mt.gov/courts/dcourt/ (counties, from its county menu, and the statewide number of district judges) and each district's Court Locator page, https://courts.mt.gov/CourtLocator/<n>JudicialDistrict (district judges; standing masters and limited-jurisdiction judges are not kept)",
    "co": "https://www.coloradojudicial.gov/trial-courts-district (counties) and the Judges and Staff page of every county's court and of Denver's district, juvenile and probate courts (district judges; county court judges and magistrates are not kept)",
    "id": "https://legislature.idaho.gov/statutesrules/idstat/title1/t1ch8/sect1-802/ to sect1-808/ (Idaho Code, counties and seats of each district) and https://isc.idaho.gov/about-the-courts/judicial-directory (district judges, from the data the page carries inline; magistrate judges are not kept)",
    "ut": "https://www.utcourts.gov/en/about/miscellaneous/directory/map-of-judicial-districts.html (counties) and https://www.utcourts.gov/en/courts/other-court-info/judges-bios/district-courts.html (district judges, printed in capitals and re-cased; court commissioners are not kept)",
    "wy": "https://www.wyocourts.gov/find-a-court/ (counties) and each county's district court page under https://www.wyocourts.gov/court/ (the judges who sit there)",
    "nm": "https://nmcourts.gov/courts-by-district/ (counties) and the District Court Staggered Terms list linked from https://nmcourts.gov/resources/judicial-terms-and-retention-schedule/ (district judges and vacant divisions, from the Judicial Performance Evaluation Commission's PDF)",
    "or": "https://www.oregonlegislature.gov/bills_laws/ors/ors003.html (ORS 3.012, counties and seats of each district) and the Judicial Department's judges list, https://www.courts.oregon.gov/courts/Pages/judges.aspx, read through the SharePoint list address its table reads (circuit judges)",
    "ks": "the 31 district pages under https://www.kscourts.gov/About-the-Courts/District-Courts/Districts/ (each lists its judges and carries the statewide district map's county lists)",
    "ne": "https://nebraskajudicial.gov/directories/district-map/district-1 to district-12 (counties; the district court's, which differ from the county court's for Otoe and Fillmore) and https://nebraskajudicial.gov/directories/district-court-judges (judges, with the county of each judge's home court)",
    "nd": "https://www.ndcourts.gov/legal-resources/rules/ndsupctadminr/6 (Administrative Rule 6, counties) and https://www.ndcourts.gov/district-court/district-court-judges (judges)",
    "oh": "https://www.supremecourt.ohio.gov/courts/judicial-system/ohio-court-of-appeals/ (counties and judges of all twelve districts)",
    "sd": "https://ujs.sd.gov/court-finder/<circuit>-judicial-circuit/ (counties) and each circuit's contacts page (circuit judges; magistrate judges are not kept)",
}


def write_source(tag, lines):
    path = source_path(tag)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    head = [
        "# %s court districts and judges, kept by scripts/build_state_courts.py --fetch %s"
        % (STATES[tag]["name"], tag),
        "# read: %s" % datetime.date.today().isoformat(),
        "# from: %s" % SOURCES_READ[tag],
        "# district | <district> | <counties, as the court lists them>",
        "# judge | <district> | <title> | <name> | <county the court prints beside the judge, if any>",
        "# vacant | <district> | <title> | | <county>",
    ]
    with open(path, "w") as fh:
        fh.write("\n".join(head + lines) + "\n")
    print("%s: wrote %s (%d lines)" % (LABEL, os.path.relpath(path, ROOT), len(lines)))


# ---------------------------------------------------------------- the build

def unit_key(tag, raw):
    return raw if tag in ("nd", "wa") else int(raw)


def read_source(tag):
    cfg = STATES[tag]
    read, districts, seats = None, {}, {}
    with open(source_path(tag)) as fh:
        for ln in fh:
            ln = ln.rstrip("\n")
            if ln.startswith("# read: "):
                read = ln[len("# read: "):]
            if not ln.strip() or ln.startswith("#"):
                continue
            parts = [p.strip() for p in ln.split("|")]
            kind, unit = parts[0], unit_key(tag, parts[1])
            if kind == "district" and len(parts) == 3:
                if unit in districts:
                    wcc.fail(LABEL, "%s lists district %s twice" % (tag, unit))
                districts[unit] = [c.strip() for c in parts[2].split(",")]
            elif kind in ("judge", "vacant") and len(parts) == 5:
                seat = {"role": parts[2]}
                if kind == "judge":
                    seat["name"] = parts[3]
                else:
                    seat["vacant"] = True
                if parts[4]:
                    seat["county"] = parts[4]
                seats.setdefault(unit, []).append(seat)
            else:
                wcc.fail(LABEL, "%s: unreadable line %r" % (tag, ln))
    if not read or not re.match(r"^\d{4}-\d{2}-\d{2}$", read):
        wcc.fail(LABEL, "%s: the excerpt says no read date" % tag)
    if len(districts) != cfg["districts"]:
        wcc.fail(LABEL, "%s: %d districts, measured %d" % (tag, len(districts), cfg["districts"]))
    if set(seats) - set(districts):
        wcc.fail(LABEL, "%s: judges in districts %s that list no counties"
                 % (tag, sorted(set(seats) - set(districts), key=str)))
    named = sum(1 for v in seats.values() for s in v if "name" in s)
    if named < cfg["min_judges"]:
        wcc.fail(LABEL, "%s: %d judges named, measured at least %d"
                 % (tag, named, cfg["min_judges"]))
    for unit, rows in seats.items():
        for s in rows:
            if s.get("county") and s["county"] not in districts[unit]:
                wcc.fail(LABEL, "%s district %s: %s is beside a county outside "
                         "the district (%s)" % (tag, unit, s.get("name", "a vacancy"),
                                                s["county"]))
    return read, districts, seats


def tiling(tag, districts):
    cfg = STATES[tag]
    rows = [(u, sorted(districts[u]), {}) for u in districts]
    n = sum(len(v) for v in districts.values())
    if n != cfg["counties"]:
        wcc.fail(LABEL, "%s: the districts list %d counties, %s has %d"
                 % (tag, n, cfg["name"], cfg["counties"]))
    return wcc.Tiling("%s-judicial-districts.json" % tag, cfg["unit_word"], rows,
                      cfg["districts"], cfg["authority"])


def roster(read, districts, seats):
    return {str(u): {"read": read, "judges": seats.get(u, [])} for u in districts}


def roster_path(tag):
    return os.path.join(wcc.app_dir(tag), "%s-district-judges.json" % tag)


def build(tag):
    read, districts, seats = read_source(tag)
    wcc.build(tag, LABEL, [tiling(tag, districts)])
    with open(roster_path(tag), "w") as fh:
        json.dump(roster(read, districts, seats), fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("%s: wrote %s-district-judges.json (%d seats, read %s)"
          % (LABEL, tag, sum(len(v) for v in seats.values()), read))


def check(tag):
    read, districts, seats = read_source(tag)
    wcc.check(tag, LABEL, [tiling(tag, districts)])
    with open(roster_path(tag)) as fh:
        shipped = json.load(fh)
    if shipped != roster(read, districts, seats):
        wcc.fail(LABEL, "%s-district-judges.json is not what %s says; re-run "
                 "this builder" % (tag, os.path.relpath(source_path(tag), ROOT)))
    print("%s: %s OK — %d districts, %d seats, read %s"
          % (LABEL, tag, len(districts), sum(len(v) for v in seats.values()), read))


def selftest():
    assert ordinal_suffix(1) == "1st" and ordinal_suffix(12) == "12th" \
        and ordinal_suffix(22) == "22nd" and ordinal_suffix(13) == "13th"
    assert page_lines("<p>A&amp;B</p><script>x</script><b> C\xa0 D </b>") == ["A&B", "C D"]
    for bad in ("Chief Clerk", "Vacant", "JOHN", "Pro Tem Division"):
        assert name_problem(bad), "%r passed as a name" % bad
    assert person("Chas Neff, Jr.", "selftest") == "Chas Neff, Jr."
    assert name_problem("Jos\u00c3\u00a9 Ruiz"), "UTF-8 read as Latin-1 passed as a name"
    assert ut_case("TONY F. GRAF, JR.") == "Tony F. Graf, Jr."
    assert ut_case("RYAN P.C. STACK") == "Ryan P.C. Stack"
    assert ut_case("JENNIFER A. MABEY (BROWN)") == "Jennifer A. Mabey (Brown)"
    assert ut_case("ELIZABETH A. HRUBY-MILLS") == "Elizabeth A. Hruby-Mills"
    assert co_key("Anne K. Norrdin") == co_key("Anne Norrdin")
    assert nm_terms_rows("\n".join(
        ["%dth District Court Division Partisan Election Retained Term Expires" % n
         + ("\nJudge A Bee 1 2020 12/31/28" if n != 3 else
            "\nChief Judge Floripa \u201cFlora\u201d Gallegos 1 2022 2024 12/31/30"
            "\nVacant 2 2026 12/31/28\nTodd A. Coberly 3 2028 Appointed* 12/31/28 *New seat"
            "\nJudge LaDonna Giron 4 Appointed* 12/31/28")
         for n in range(1, 14)]))[2:6] == [
        "judge | 3 | Chief Judge | Floripa \u201cFlora\u201d Gallegos | ",
        "vacant | 3 | District Judge | | ",
        "judge | 3 | District Judge | Todd A. Coberly | ",
        "judge | 3 | District Judge | LaDonna Giron | "]
    assert wv_rows("\n".join([
        "WEST VIRGINIA CIRCUIT COURT CIRCUITS", "1st Judicial Circuit", "(Brooke, Hancock, Ohio)",
        "Joseph Barki", "", "2nd Judicial Circuit", "(Doddridge, Pleasants,", "Ritchie, Wirt)",
        "Richard Lindsay, II", "Kristina Raynes 3rd Judicial Circuit", "(Putnam)", "Amy Mann"])) == [
        "district | 1 | Brooke, Hancock, Ohio", "district | 2 | Doddridge, Pleasants, Ritchie, Wirt",
        "district | 3 | Putnam",
        "judge | 1 | Circuit Judge | Joseph Barki | ",
        "judge | 2 | Circuit Judge | Richard Lindsay, II | ",
        "judge | 2 | Circuit Judge | Kristina Raynes | ",
        "judge | 3 | Circuit Judge | Amy Mann | "]
    print("%s: selftest OK" % LABEL)


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("states", nargs="*", help="ks ne nd oh sd (default: all)")
    ap.add_argument("--fetch", action="store_true", help="re-read the court pages")
    ap.add_argument("--check", action="store_true", help="verify, write nothing")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    tags = args.states or sorted(STATES)
    for tag in tags:
        if tag not in STATES:
            wcc.fail(LABEL, "no state %r here" % tag)
        if args.fetch:
            write_source(tag, FETCHERS[tag](Reader()))
        elif args.check:
            check(tag)
        else:
            build(tag)


if __name__ == "__main__":
    main()
