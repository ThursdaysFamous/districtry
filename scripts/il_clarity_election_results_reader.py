#!/usr/bin/env python3
"""
Read the Clarity Elections precinct reports saved in il/data/source/
election-results/2026-11-03/clarity/ and write them as one raw read for
build_il_county_election_results.py, in the shape the Platinum and Kane
scrapers write.

IT READS NO NETWORK. Clarity turns this project's scheduled jobs away (see
il_clarity_election_results_download.py, the hand-run download, and the
README beside the files), so the reports are downloaded by hand and committed,
and this reads the committed copies. The daily refresh folds the same raw read
in every day, so these counties stay on the map at the numbers of the last
hand download, and each county's card prints the time of its own report.

WHICH REPORTS. The counties whose precinct lines the Illinois map draws:

    DuPage, Lake, McHenry, Winnebago (outside Rockford), McLean (outside
    Bloomington), the City of Bloomington, Sangamon, Macoupin

Madison County's report is saved too and is not read: on 2026-11-09 the
county's precinct layer, which the map and this build both read, answered
every request with an ArcGIS Web Adaptor error page, so its precincts could
not be matched or drawn.

THE ROWS ARE CHECKED, NOT TRUSTED: each choice's precinct votes, summed over
the report's vote types, must equal the choice's total; the precinct ballots
must add up to the report's own total; and a precinct row that is not a place
on the map is allowed only where OUTSIDE names it, and its votes are kept as
votes counted outside any precinct.

Usage:
    python3 scripts/il_clarity_election_results_reader.py -o il/data/source/election-results-clarity-raw.json
    python3 scripts/il_clarity_election_results_reader.py --check -o il/data/source/election-results-clarity-raw.json
"""

import argparse
import datetime
import hashlib
import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

from scraper_common import make_fail

fail = make_fail("il-clarity-election-results-reader")

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "..", "il", "data", "source", "election-results", "2026-11-03", "clarity")
BASE = "https://results.enr.clarityelections.com/"

# tag -> (record.json key, the county's name, the office, the area it counts)
COUNTIES = [
    ("dupage", "DuPage", "DuPage", "DuPage County Clerk", "DuPage County"),
    ("lake", "Lake", "Lake", "Lake County Clerk", "Lake County"),
    ("mchenry", "McHenry", "McHenry", "McHenry County Clerk", "McHenry County"),
    ("winnebago", "Winnebago", "Winnebago", "Winnebago County Clerk", "Winnebago County outside Rockford"),
    ("mclean", "McLean", "McLean", "McLean County Clerk", "McLean County outside Bloomington"),
    ("bloomington", "Bloomington", "McLean", "Bloomington Election Commission", "the City of Bloomington"),
    ("sangamon", "Sangamon", "Sangamon", "Sangamon County Clerk", "Sangamon County"),
    ("macoupin", "Macoupin", "Macoupin", "Macoupin County Clerk", "Macoupin County"),
]
# Report rows that are no place on the map. DuPage reports the ballots of
# voters who may vote only for federal offices (Illinois residents living
# abroad, 10 ILCS 5/20) as five units by congressional district,
# "FEDERAL - F03" and so on; their votes are counted outside any precinct.
OUTSIDE = {"dupage": re.compile(r"^FEDERAL - F\d+$")}


# Each office's circuit, for a retention title that names the judge and not
# the court (705 ILCS 35/1: DuPage is the 18th Circuit, Lake the 19th,
# McHenry the 22nd, Winnebago the 17th, McLean the 11th, Sangamon and
# Macoupin the 7th).
CIRCUIT = {"dupage": 18, "lake": 19, "mchenry": 22, "winnebago": 17, "mclean": 11, "bloomington": 11,
           "sangamon": 7, "macoupin": 7}
# Judges a title names by surname alone (Sangamon's "CIRCUIT COURT JUDGE
# RETENTION - REIF"), written in full as the other offices' ballots in this
# file print them, so one judge is one race across the county line.
JUDGE_NAMES = {
    "KNECHT": "James A. Knecht", "REIF": "Christopher E. Reif", "MADONIA": "John M. Madonia",
    "GIGANTI": "Adam Giganti", "GRISCHOW": "Raylene Grischow", "NOLL": "Gail L. Noll",
    "LORTON": "Allison Lorton", "SCHMIDT": "Zachary A. Schmidt", "FITTON": "Matthew J. Fitton",
    "CHAMBERS": "Jason Chambers", "WRIGHT": "Jonathan C. Wright",
}
APPELLATE = {"KNECHT": 4}  # James A. Knecht sits on the 4th District Appellate Court
_ORD_WORDS = ["ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN", "ELEVEN",
              "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN", "SEVENTEEN", "EIGHTEEN", "NINETEEN"]
_TENS_WORDS = ["TWENTY", "THIRTY"]


def cardinal(text):
    """'TWENTY-NINE' 29, 'ELEVEN' 11 (Sangamon's board districts), or None."""
    up = text.upper()
    m = re.search(r"\b(%s)(?:[- ](%s))?\b" % ("|".join(_TENS_WORDS), "|".join(_ORD_WORDS[:9])), up)
    if m:
        return 20 + 10 * _TENS_WORDS.index(m.group(1)) + (_ORD_WORDS.index(m.group(2)) + 1 if m.group(2) else 0)
    m = re.search(r"\b(%s)\b" % "|".join(sorted(_ORD_WORDS, key=len, reverse=True)), up)
    return _ORD_WORDS.index(m.group(1)) + 1 if m else None


def number_in(text):
    """A district number however the title writes it: 'D16', '13TH',
    'DISTRICT 5', or spelled out ('SEVENTY-SEVENTH', 'TWENTY-NINE')."""
    from build_il_county_election_results import spelled_ordinal
    up = text.upper()
    m = re.search(r"\bD(\d+)\b", up) or re.search(r"\b(\d+)(?:ST|ND|RD|TH)\b", up) or \
        re.search(r"\bDISTRICT (\d+)\b", up)
    if m:
        return int(m.group(1))
    n = spelled_ordinal(re.sub(r"(TH|ST|ND|RD)(?=REPRESENTATIVE)", r"\1 ", up))
    return n if n is not None else cardinal(up)


def ordinal(n):
    return "%d%s" % (n, "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


REGION_COUNTIES = {
    # the counties a Regional Superintendent's region holds, where the title
    # names one county or none (the region is the office's own)
    ("dupage", "DUPAGE"): "DuPage County", ("dupage", "KANE"): "Kane County",
    ("lake", ""): "Lake County", ("mchenry", "MCHENRY"): "McHenry County",
    ("mchenry", "BOONE/WINNEBAGO"): "Boone and Winnebago Counties", ("mchenry", "KANE"): "Kane County",
    ("mchenry", "LAKE"): "Lake County", ("bloomington", ""): "DeWitt, Livingston, Logan and McLean Counties",
}


def canonical(tag, title, choices):
    """A Clarity title in the wording build_il_county_election_results.py's
    classify() reads (the Platinum clerks'), as (title, district)."""
    t = re.sub(r"\s+", " ", title).strip()
    up = t.upper()
    yes_no = sorted(c.upper() for c in choices) == ["NO", "YES"]
    if yes_no:
        if re.search(r"\bRETENTION\b|\bRETAIN\b", up):
            return retention(tag, t, up), ""
        return t, ""
    if re.search(r"\bSENATOR\b", up) and re.search(r"\bU\.? ?S\b|UNITED STATES", up):
        return "FOR UNITED STATES SENATOR", "FEDERAL"
    if re.search(r"\bGOV", up):
        return "FOR GOVERNOR AND LIEUTENANT GOVERNOR", "STATE OF ILLINOIS"
    if re.search(r"\bATT(ORNEY|\.)? ?GEN", up):
        return "FOR ATTORNEY GENERAL", "STATE OF ILLINOIS"
    if re.search(r"\bSEC(RETARY|\.)? OF STATE\b", up):
        return "FOR SECRETARY OF STATE", "STATE OF ILLINOIS"
    if re.fullmatch(r"(FOR )?(STATE )?COMPTROLLER", up):
        return "FOR COMPTROLLER", "STATE OF ILLINOIS"
    if re.fullmatch(r"(FOR )?(STATE )?TREASURER", up):
        return "FOR TREASURER", "STATE OF ILLINOIS"
    if "CONGRESS" in up:
        return "FOR REPRESENTATIVE IN CONGRESS", "%s CONGRESSIONAL DIST" % ordinal(number_in(up)).upper()
    if re.search(r"\bSTATE SENAT", up):
        return "FOR STATE SENATOR", "%s LEGISLATIVE DIST" % ordinal(number_in(up)).upper()
    if re.search(r"GENERAL ASSEMBLY|\bG\.A\.|STATE REPRESENTATIVE", up):
        return "FOR REPRESENTATIVE IN THE GENERAL ASSEMBLY", "%s REPRESENTATIVE DIST" % ordinal(number_in(up)).upper()
    if re.search(r"REG(IONAL|\.) SUP|ESR SUPERINTENDENT", up):
        par = re.search(r"\(([^)]+)\)", t) or re.search(r" - (.+)$", t)
        if par:
            names = re.sub(r"(?i)\bcount(y|ies)\b", "", par.group(1))
            parts = [x.strip() for x in re.split(r",|&|-|\band\b", names, flags=re.I) if x.strip()]
            region = (", ".join(parts[:-1]) + " and " + parts[-1] + " Counties") if len(parts) > 1 else parts[0] + " County"
        else:
            lead = re.sub(r"(?i)^(FOR )?|(COUNTY )?REG(IONAL|\.) SUP.*$|SUPERINTENDENT.*$", "", t).strip()
            lead = re.sub(r"(?i)\bCOUNTY\b", "", re.sub(r"(?i)OF SCHOOLS", "", lead)).strip()
            tail = re.search(r"(?i)OF SCHOOLS (.+?)( COUNTY)?$", t)
            word = norm_upper(tail.group(1) if tail else lead)
            region = REGION_COUNTIES.get((tag, word))
            if not region:
                raise ValueError("%s: no region for %r" % (tag, title))
        return "FOR REGIONAL SUPERINTENDENT OF SCHOOLS (%s)" % region, ""
    if re.search(r"FOREST PRESERVE", up):
        return t, "FOREST PRESERVE"
    if re.search(r"CHAIR(PERSON|MAN)? OF THE COUNTY BOARD", up):
        return "FOR CHAIRPERSON OF THE COUNTY BOARD", "COUNTY"
    if re.search(r"\bCOUNTY BOARD\b|MEMBER OF THE COUNTY BOARD", up):
        n = number_in(re.sub(r"\d+[- ]?(YR|YEAR)", "", up))
        if n is None:
            raise ValueError("%s: no district in %r" % (tag, title))
        term = ""
        if re.search(r"UN-?EXPIRED", up):
            m = re.search(r"(\d)[- ]?(YR|YEAR)", up)
            term = " (UNEXPIRED %s-YEAR TERM)" % m.group(1)
        elif re.search(r"\b2[- ]?(YR|YEAR)", up):
            term = " (2-YEAR TERM)"
        return "FOR COUNTY BOARD MEMBER DISTRICT %d%s" % (n, term), "COUNTY BOARD DIST %d" % n
    for office in ("CLERK AND RECORDER", "CLERK", "TREASURER", "SHERIFF"):
        if re.search(r"\b%s\b" % office, up) and ("COUNTY" in up or re.fullmatch(r"(FOR )?" + office, up)):
            return "FOR COUNTY " + office, "COUNTY"
    if re.search(r"\bJUDGE\b|\bCIR(C|CUIT)?\.? ?(CT|COURT)\b", up):
        return vacancy(tag, t, up), ""
    return t, ""


def norm_upper(text):
    return re.sub(r"\s+", " ", text.upper().replace("DUPAGE", "DUPAGE")).strip()


def vacancy(tag, t, up):
    circuit = re.search(r"\b(\d+)(?:ST|ND|RD|TH)\b", up)
    from build_il_county_election_results import spelled_ordinal
    n = spelled_ordinal(up.split(" - ")[0]) if not re.search(r"\d+(ST|ND|RD|TH)\s*(CIR|JUD)", up) else int(circuit.group(1))
    m = re.search(r"(?i)vacancy of (?:the )?(?:hon(?:orable|\.)?\s*)?([^)]+)\)", t)
    who = m.group(1).strip() if m else None
    if not who:
        m = re.search(r"(?i)(?:SUB ?CIRCUIT|CT|COURT)\s*-?\s*([A-Z'][A-Za-z' .]+?)(?: VACANCY)?$", t)
        who = m.group(1).strip().title() if m else None
    if not n or not who:
        raise ValueError("%s: cannot read the court or the vacancy in %r" % (tag, t))
    if "APPELLATE" in up:
        return "FOR JUDGE OF THE APPELLATE COURT %s JUDICIAL DISTRICT (To fill the vacancy of the Hon. %s)" % (
            ordinal(n).upper(), who)
    return "FOR JUDGE OF THE CIRCUIT COURT %s JUDICIAL CIRCUIT (To fill the vacancy of the Hon. %s)" % (
        ordinal(n).upper(), who)


def retention(tag, t, up):
    """A retention question as 'Shall Judge <name> be retained in office as
    Judge of the <court>?', the form classify() reads the judge and court from."""
    m = (re.search(r"(?i)^Retention of (.+?) as Judge", t) or
         re.search(r"(?i)^Retention - Judicial Court (.+)$", t) or
         re.search(r"(?i)^JUDGE FOR RETENTION - (.+)$", t) or
         re.search(r"(?i)RETENTION.* - (?!.*\bCOURT$)([A-Z'][A-Za-z' .]+)$", t) or
         re.search(r"(?i)^RETAIN (.+)$", t) or
         re.search(r"(?i)^RETENTION ([^-]+?)(?: - .*)?$", t))
    if not m:
        return None
    name = m.group(1).strip()
    surname = re.sub(r"[^A-Z']", "", name.split()[-1].upper())
    if surname in JUDGE_NAMES and len(name.split()) == 1:
        name = JUDGE_NAMES[surname]
    if name == name.upper():
        name = " ".join(w if re.fullmatch(r"[A-Z]\.", w) else w.capitalize() for w in name.split())
    if surname in APPELLATE:
        court = "the Appellate Court, %s District" % ordinal(APPELLATE[surname])
    else:
        court = "the Circuit Court, %s Judicial Circuit" % ordinal(CIRCUIT[tag])
    return "Shall Judge %s be retained in office as Judge of %s?" % (name, court)


def utc(stamp):
    """Clarity's '11/6/2026 2:21:49 PM CST' as an ISO time in UTC."""
    m = re.fullmatch(r"(\d+)/(\d+)/(\d{4}) (\d+):(\d+):(\d+) (AM|PM) (CST|CDT)", stamp.strip())
    if not m:
        fail("cannot read the report time %r" % stamp)
    mo, d, y, h, mi, s, ap, zone = m.groups()
    h = int(h) % 12 + (12 if ap == "PM" else 0)
    local = datetime.datetime(int(y), int(mo), int(d), h, int(mi), int(s))
    return (local + datetime.timedelta(hours=6 if zone == "CST" else 5)).strftime("%Y-%m-%dT%H:%M:%SZ")


def choice_text(text):
    t = re.sub(r"\s+", " ", text).strip()
    # "NO CANDIDATE/CANDIDATO" (DuPage's bilingual ballot): an empty position
    if re.match(r"(?i)^no candidate\b", t):
        return "No Candidate"
    return t


def read_county(tag, key, name, publisher, area, record):
    rec = record.get(key)
    if not rec:
        fail("%s: record.json has no %s entry" % (tag, key))
    stem = {"Bloomington": "bloomington"}.get(key, key.lower())
    path = os.path.join(DIR, stem + "-detailxml.zip")
    body = open(path, "rb").read()
    if hashlib.sha256(body).hexdigest() != rec["sha256"]:
        fail("%s: %s is not the file record.json says was downloaded" % (tag, os.path.basename(path)))
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        root = ET.parse(io.BytesIO(z.read("detail.xml"))).getroot()
    stamp = root.findtext("Timestamp") or ""
    if stamp != rec["timestamp"]:
        fail("%s: the report says %r and record.json %r" % (tag, stamp, rec["timestamp"]))
    outside = OUTSIDE.get(tag)
    vt = root.find("VoterTurnout")
    turnout, off = {}, []
    for p in vt.find("Precincts"):
        pname = p.get("name")
        if outside and outside.match(pname):
            off.append(pname)
            continue
        turnout[pname] = [int(p.get("totalVoters")), int(p.get("ballotsCast"))]
    every = sum(int(p.get("ballotsCast")) for p in vt.find("Precincts"))
    if every != int(vt.get("ballotsCast")):
        fail("%s: precinct ballots add to %d, the report says %s" % (tag, every, vt.get("ballotsCast")))
    contests = []
    for c in root.findall("Contest"):
        choices, columns = [], []
        for ch in c.findall("Choice"):
            choices.append(choice_text(ch.get("text")))
            by = {}
            for vtype in ch.findall("VoteType"):
                for p in vtype.findall("Precinct"):
                    by[p.get("name")] = by.get(p.get("name"), 0) + int(p.get("votes"))
            if sum(by.values()) != int(ch.get("totalVotes")):
                fail("%s, %s, %s: precinct votes add to %d, the report says %s"
                     % (tag, c.get("text"), ch.get("text"), sum(by.values()), ch.get("totalVotes")))
            columns.append(by)
        names = set()
        for by in columns:
            names.update(by)
        precincts, out = {}, [0] * len(choices)
        for pname in sorted(names):
            vals = [by.get(pname, 0) for by in columns]
            if pname in turnout:
                precincts[pname] = vals
            elif pname in off:
                out = [a + b for a, b in zip(out, vals)]
            else:
                fail("%s, %s: precinct %r has votes and no turnout row" % (tag, c.get("text"), pname))
        clerk = re.sub(r"\s+", " ", c.get("text")).strip()
        try:
            title, district = canonical(tag, clerk, choices)
        except ValueError as e:
            fail(str(e))
        race = {"name": title, "district": district, "clerkTitle": clerk,
                "voteFor": int(c.get("voteFor") or 1) or 1, "choices": choices, "precincts": precincts}
        if title is None:
            # Winnebago prints three retention questions as "JUDGE OF THE
            # CIRCUIT COURT RETENTION" and names none of the judges: each is
            # its own question, named by its place on the county's ballot
            n = sum(1 for r in contests if r.get("clerkTitle") == clerk) + 1
            race["name"] = ("Retention of a judge of the Circuit Court, %s Judicial Circuit (number %d on %s "
                            "County's ballot, which does not name the judge)" % (ordinal(CIRCUIT[tag]), n, name))
            race["fixed"] = {"group": "questions", "beyond": True}
        if any(out):
            race["outside"] = out
        contests.append(race)
    site = rec["url"].split("/" + rec["version"] + "/")[0] + "/"
    return {
        "county": tag, "name": name, "source": site, "publisher": publisher, "areaName": area,
        "read": utc(stamp), "ballots": sum(v[1] for v in turnout.values()),
        "outsideBallots": every - sum(v[1] for v in turnout.values()),
        "turnout": turnout, "contests": contests,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--check", action="store_true",
                    help="write nothing; fail unless --out already holds exactly this read")
    args = ap.parse_args()
    record = json.load(open(os.path.join(DIR, "record.json")))
    counties = [read_county(*c, record=record) for c in COUNTIES]
    doc = {"read": max(c["read"] for c in counties), "host": BASE, "counties": counties}
    text = json.dumps(doc, separators=(",", ":")) + "\n"
    if args.check:
        if not os.path.exists(args.out) or open(args.out).read() != text:
            fail("%s is not what the saved reports read as; run without --check and commit it" % args.out)
        print("il-clarity-election-results-reader: OK — %s matches the %d saved reports"
              % (os.path.basename(args.out), len(counties)))
        return
    with open(args.out, "w") as fh:
        fh.write(text)
    for c in counties:
        print("%s: %d precincts, %d contests, %d ballots, report of %s"
              % (c["name"] if c["county"] != "bloomington" else "Bloomington", len(c["turnout"]),
                 len(c["contests"]), c["ballots"], c["read"]), file=sys.stderr)


if __name__ == "__main__":
    main()
