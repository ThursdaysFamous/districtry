#!/usr/bin/env python3
"""Vermont's elected county judges: each county's probate judge and its two
assistant judges, from the Vermont Judiciary's own court location pages.

    python3 vt/scripts/build_vt_county_judges.py --fetch   # read the 28 pages, write the excerpt
    python3 vt/scripts/build_vt_county_judges.py           # build data/app/vt-county-judges.json
    python3 vt/scripts/build_vt_county_judges.py --check   # the file matches the excerpt
    python3 vt/scripts/build_vt_county_judges.py --selftest

Each county elects a probate judge and two assistant judges for four-year
terms beginning on the first of February after the election (the Legislative
Directory and State Manual's selections of the statutes). The Judiciary keeps
one page per county division:

  * /court-locations/<county>-probate-division lists, under "Court Staff", the
    division's "Superior Judge". That is the county's probate judge: the
    Secretary of State's Legislative Directory and State Manual (2025-2026,
    read 2026-11-28) lists the same judge as "Superior Judge ... (Probate)" in
    twelve counties (in Caledonia and Washington also as "Probate Judge"),
    and in Grand Isle and Rutland as the one Superior Judge whose line names
    no other division, the unit's others being marked Civil, Criminal or
    Family.
    The unit's "Presiding Judge" is a Superior Court judge the Governor
    appoints, and is not kept.
  * /court-locations/<county>-civil-division lists "Assistant Judge:" with
    both of the county's assistant judges, comma-separated.

The fetch stops unless every one of the 14 counties gives exactly one probate
judge and exactly two assistant judges. robots.txt is read first and requests
are paced two seconds apart (build_state_courts.Reader).
"""
import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import build_state_courts as bsc  # noqa: E402

LABEL = "build-vt-county-judges"
BASE = "https://www.vermontjudiciary.org/court-locations/%s-%s-division"
COUNTIES = ("Addison", "Bennington", "Caledonia", "Chittenden", "Essex", "Franklin",
            "Grand Isle", "Lamoille", "Orange", "Orleans", "Rutland", "Washington",
            "Windham", "Windsor")
SOURCE = os.path.join(ROOT, "vt", "data", "source", "vt-county-judges.txt")
OUT = os.path.join(ROOT, "vt", "data", "app", "vt-county-judges.json")
COUNTIES_FILE = os.path.join(ROOT, "vt", "data", "app", "state-counties.json")
NAME = re.compile(r"^[A-Z][A-Za-z.'-]*(?: [A-Z][A-Za-z.'-]*){1,4}$")


def fail(msg):
    sys.stderr.write("%s: FAIL — %s\n" % (LABEL, msg))
    sys.exit(1)


def slug(county):
    return county.lower().replace(" ", "-")


def staff_field(lines, label):
    """The value printed under `label` inside the page's "Court Staff" block."""
    if "Court Staff" not in lines:
        return None
    block = lines[lines.index("Court Staff") + 1:]
    for i, ln in enumerate(block[:-1]):
        if ln == label + ":":
            return block[i + 1]
        if ln == "Mission Statement":
            break
    return None


def person(text, where):
    name = re.sub(r"^(?:The )?Honorable\s+", "", text.strip())
    if not NAME.match(name):
        fail("%s: %r does not read as one person's name" % (where, text))
    return name


def read_county(probate_lines, civil_lines, county):
    judge = staff_field(probate_lines, "Superior Judge")
    if not judge:
        fail("%s: the probate division page names no Superior Judge" % county)
    if "," in judge or "&" in judge:
        fail("%s: the probate division page names more than one judge: %r" % (county, judge))
    assistants = staff_field(civil_lines, "Assistant Judge") or staff_field(civil_lines, "Assistant Judges")
    if not assistants:
        fail("%s: the civil division page names no assistant judge" % county)
    names = [person(x, county + " assistant judge") for x in re.split(r",\s*|\s+&\s+|\s+and\s+", assistants)
             if x.strip()]
    if len(names) != 2:
        fail("%s: the civil division page names %d assistant judges, not 2: %r" % (county, len(names), assistants))
    return person(judge, county + " probate judge"), names


def fetch():
    reader = bsc.Reader()
    rows = []
    for county in COUNTIES:
        probate = reader.get(BASE % (slug(county), "probate"))
        civil = reader.get(BASE % (slug(county), "civil"))
        judge, assistants = read_county(probate, civil, county)
        rows.append("probate | %s | %s" % (county, judge))
        rows.extend("assistant | %s | %s" % (county, a) for a in assistants)
    today = datetime.date.today().isoformat()
    head = ["# Vermont's elected county judges, read %s from the Vermont Judiciary's court location pages" % today,
            "# by vt/scripts/build_vt_county_judges.py --fetch. Never hand-edit; re-run the fetch.",
            "# probate | <county> | <name>   (the probate division page's Superior Judge)",
            "# assistant | <county> | <name> (the civil division page's Assistant Judge line, two per county)",
            "read | %s" % today]
    with open(SOURCE, "w") as f:
        f.write("\n".join(head + rows) + "\n")
    print("%s: wrote %s (%d lines)" % (LABEL, os.path.relpath(SOURCE, ROOT), len(rows)))


def parse(text):
    read, counties = None, {}
    for ln in text.splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        parts = [p.strip() for p in ln.split("|")]
        if parts[0] == "read" and len(parts) == 2 and re.match(r"^\d{4}-\d{2}-\d{2}$", parts[1]):
            read = parts[1]
        elif parts[0] in ("probate", "assistant") and len(parts) == 3 and parts[1] in COUNTIES:
            rec = counties.setdefault(parts[1], {"probate": [], "assistant": []})
            rec[parts[0]].append(person(parts[2], parts[1]))
        else:
            fail("unreadable excerpt line: %r" % ln)
    if not read:
        fail("the excerpt has no read date")
    if sorted(counties) != sorted(COUNTIES):
        fail("the excerpt covers %d of Vermont's 14 counties" % len(counties))
    for c, rec in counties.items():
        if len(rec["probate"]) != 1 or len(rec["assistant"]) != 2:
            fail("%s: %d probate and %d assistant judges, not 1 and 2" % (c, len(rec["probate"]), len(rec["assistant"])))
    return read, counties


def build_doc(text, geoids):
    read, counties = parse(text)
    out = {}
    for county in COUNTIES:
        geoid = geoids.get(county + " County")
        if not geoid:
            fail("%s County is not in state-counties.json" % county)
        rec = counties[county]
        out[geoid] = {"county": county, "probate": rec["probate"][0], "assistant": rec["assistant"], "read": read}
    return out


def county_geoids():
    with open(COUNTIES_FILE) as f:
        fc = json.load(f)
    out = {}
    for feat in fc["features"]:
        p = feat.get("properties") or {}
        name = p.get("NAME") or p.get("name")
        geoid = p.get("GEOID") or p.get("geoid")
        if name and geoid:
            out[str(name)] = str(geoid)
    return out


def dumps(doc):
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def selftest():
    probate = ["Court Staff", "Presiding Judge:", "Honorable Robert Katims", "Superior Judge:",
               "Honorable Gregory Glennon", "Court Operations Manager:", "Naomi Henderson", "Mission Statement"]
    civil = ["Court Staff", "Presiding Judge:", "Honorable Alison Arms", "Superior Judge:", "Honorable John Valente",
             "Assistant Judge:", "Honorable Nicole Wilkerson, Honorable Patricia Ross", "Clerk of Court:", "X Y"]
    assert read_county(probate, civil, "Test") == ("Gregory Glennon", ["Nicole Wilkerson", "Patricia Ross"])
    assert staff_field(["Superior Judge:", "A B"], "Superior Judge") is None  # outside Court Staff
    assert staff_field(["Court Staff", "Mission Statement", "Superior Judge:", "A B"], "Superior Judge") is None
    text = "read | 2026-11-28\n" + "".join(
        "probate | %s | Ann Bee\nassistant | %s | Cy Dee\nassistant | %s | Ed Eff\n" % (c, c, c) for c in COUNTIES)
    doc = build_doc(text, {c + " County": str(50001 + 2 * i) for i, c in enumerate(COUNTIES)})
    assert doc["50001"] == {"county": "Addison", "probate": "Ann Bee", "assistant": ["Cy Dee", "Ed Eff"],
                            "read": "2026-11-28"}
    print("%s: selftest OK" % LABEL)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.fetch:
        return fetch()
    with open(SOURCE) as f:
        doc = build_doc(f.read(), county_geoids())
    text = dumps(doc)
    if args.check:
        if not os.path.exists(OUT) or open(OUT).read() != text:
            fail("%s is not what the excerpt builds; run the builder" % os.path.relpath(OUT, ROOT))
        print("%s: OK — 14 counties, read %s" % (LABEL, doc[min(doc)]["read"]))
        return
    with open(OUT, "w") as f:
        f.write(text)
    print("%s: wrote %s — 14 counties, read %s" % (LABEL, os.path.relpath(OUT, ROOT), doc[min(doc)]["read"]))


if __name__ == "__main__":
    main()
