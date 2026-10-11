#!/usr/bin/env python3
"""
Build ky/data/app/ky-county-officials.json: every Kentucky county's governing body and elected officers.

WHAT IT READS. ky/data/source/ky-county-officials-scrape.json, written by
ky_county_officials_scraper.py from the Department for Local Government's county
directory, one page per county. For Jefferson and Fayette it also reads
ky/data/app/ky-city-officials.json, because those two counties have no fiscal
court: Louisville Metro (KRS 67C) and the Lexington-Fayette Urban County
Government (KRS 67A) are merged city-county governments, the directory lists
their councils under the CITY, and the city builder already joins them. One
source, read once, for one body.

THE GOVERNING BODY. In 118 counties it is the fiscal court, which KRS 67.040
makes the county judge/executive plus either the magistrates (elected from
magisterial districts, KRS 67.045) or three commissioners (KRS 67.050). The
directory prints the form in a "Government Type" field in only 44 counties, so
the form is read from the TITLES the directory gives the members, and the two
must agree wherever the field is filled in.

WHAT IT DOES NOT CLAIM. The directory names each magistrate and commissioner
and never says which district one holds, so no record here carries a district
and the card says so. Measured 2026-10-11: 120 counties, 520 magistrates and 42
commissioners named, one magistrate row in Bracken with no name.

THE ELECTED OFFICERS. KRS elects a county attorney, clerk, sheriff, jailer,
coroner, surveyor and property valuation administrator beside the court. The
directory lists all of them but the surveyor; it lists appointed staff too
(treasurer, finance officer, bookkeeper), which are left out. A title this
builder does not classify FAILS the build rather than being guessed into either
list.

    python3 ky/scripts/build_ky_county_officials.py            # write
    python3 ky/scripts/build_ky_county_officials.py --check    # CI drift gate
    python3 ky/scripts/build_ky_county_officials.py --selftest # offline
"""

import argparse
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)

SCRAPE = os.path.join(INSTANCE, "data", "source", "ky-county-officials-scrape.json")
CITIES = os.path.join(INSTANCE, "data", "app", "ky-city-officials.json")
COUNTIES = os.path.join(INSTANCE, "data", "app", "state-counties.json")
OUT = os.path.join(INSTANCE, "data", "app", "ky-county-officials.json")

JUDGE = "County Judge Executive"
BOARD = {"County Magistrate": ("magistrate", "Magistrate"),
         "County Commissioner": ("commissioner", "Commissioner")}
OFFICERS = {
    "County Attorney": "County Attorney",
    "County Clerk": "County Clerk",
    "County Sheriff": "Sheriff",
    "County Jailer": "Jailer",
    "County Coroner": "Coroner",
    "County PVA": "Property Valuation Administrator",
}
# The order the card and the pages print the officers in.
OFFICER_ORDER = list(OFFICERS.values())
STAFF = {
    "County Treasurer", "Finance Officer", "Bookkeeper", "Office Manager",
    "Deputy Judge/Executive", "Fiscal Court Clerk", "Chief Deputy",
    "Deputy Jailer", "Administrative Assistant", "Clerical, Treasurer's Office",
    "Secretary", "Bookkeeper, Sheriff's Dept.", "Clinton County Finance Officer",
    "Clerk/Bookkeeper", "Budget Clerk", "Chief Financial Officer",
    "Public Administrative Specialist", "Public Administration Specialist",
    "Asst. Treasurer - Payroll Clerk", "Deputy Judge/Executive-Finance Officer",
    "Bookkeeper in Training", "Payroll Clerk", "City Clerk/Treasurer", "Clerk",
    "Office Assistant", "Bookkeeper/Tax Deputy/Personnel",
    "Deputy Sheriff/Bookkeeper",
}
# The directory's own "Government Type" spellings, where it fills one in.
GOV_TYPE = {"Magistrate": "magistrate", "Commissioner": "commissioner",
            "Commissioners": "commissioner"}

# The two merged governments, keyed by county, joined to the Census place the
# city roster already carries them under.
MERGED = {
    "Jefferson": {"place": "2148006", "form": "metro",
                  "body": "Louisville Metro Council",
                  "law": "KRS 67C"},
    "Fayette": {"place": "2146027", "form": "urban-county",
                "body": "Lexington-Fayette Urban County Council",
                "law": "KRS 67A"},
}

# A county whose form a second publisher contradicts. Printed on the card and
# the county's page, and FAILS once the directory stops showing the shape the
# note describes, so it cannot go on describing a disagreement that is over.
FORM_NOTES = {
    "Pike": ("commissioner",
             "The state directory lists three commissioners, while Pike County's "
             "certified 2026 primary ran five numbered magistrate races. This app "
             "has not settled which form the next term takes."),
}

# A directory row whose name is plainly a typing slip, corrected only where a
# second witness names the person. FAILS once the row no longer reads this way,
# so a fix cannot outlive the typo it corrects.
#   Christian: the judge/executive's first name is printed "2". The same row's
#   e-mail is jgilliam@christiancountyky.gov, and the county's own page
#   (christiancountyky.gov/county-judge-executive, read 2026-10-11) says "Jerry
#   Gilliam was elected Christian County's Judge/Executive".
NAME_FIXES = {("Christian", "2", "Gilliam"): "Jerry"}

# Floors, measured 2026-10-11 on the first full read: 120 counties, 680 named
# fiscal court members (118 judge/executives, 520 magistrates, 42
# commissioners), not counting the two merged councils.
MIN_COUNTIES = 120
MIN_MEMBERS = 650


def full_name(o):
    return re.sub(r"\s+", " ", ("%s %s" % (o.get("first", ""), o.get("last", ""))).strip())


def apply_fixes(county, officials, used, fixes):
    for o in officials:
        key = (county, o.get("first", ""), o.get("last", ""))
        if key in fixes:
            o["first"] = fixes[key]
            used.add(key)


def person(o, role_key, role):
    rec = {"name": full_name(o), role_key: role}
    if o.get("phone"):
        rec["phone"] = o["phone"]
    if o.get("email"):
        rec["email"] = o["email"]
    return rec


def build(scrape, cities, counties, fixes=None):
    fixes = NAME_FIXES if fixes is None else fixes
    read = scrape["source"]["read"]
    geoid_of = {f["properties"]["BASENAME"]: f["properties"]["GEOID"] for f in counties}
    out, unknown, used_notes, used_fixes = {}, set(), set(), set()
    for county, c in sorted(scrape["counties"].items()):
        apply_fixes(county, c.get("officials", []), used_fixes, fixes)
        if county not in geoid_of:
            raise SystemExit("FAIL: the directory names %r, which state-counties.json "
                             "does not carry" % county)
        judges, members, officers, forms, unnamed = [], [], [], set(), 0
        for o in c.get("officials", []):
            title = o.get("title", "")
            named = bool(full_name(o))
            if title == JUDGE:
                if named:
                    judges.append(person(o, "role", "County Judge/Executive"))
            elif title in BOARD:
                form, role = BOARD[title]
                forms.add(form)
                if named:
                    members.append(person(o, "role", role))
                else:
                    unnamed += 1
            elif title in OFFICERS:
                if named:
                    officers.append(person(o, "office", OFFICERS[title]))
            elif title not in STAFF and named:
                unknown.add(title)
        officers.sort(key=lambda p: OFFICER_ORDER.index(p["office"]))
        geoid = geoid_of[county]
        rec = {"county": county, "sourceUrl": c["sourceUrl"], "read": read}
        if c.get("website", "").startswith("http"):
            rec["website"] = c["website"]
        office = {}
        if c.get("address"):
            tail = ", ".join(x for x in (c.get("mailCity"),
                                         "KY " + c["zip"] if c.get("zip") else None) if x)
            office["address"] = c["address"] + (", " + tail if tail else "")
        if c.get("phone"):
            office["phone"] = c["phone"]
        if office:
            rec["office"] = office
        if county in MERGED:
            m = MERGED[county]
            if forms:
                raise SystemExit("FAIL: the directory now lists a fiscal court for "
                                 "%s County; MERGED says it has none" % county)
            city = cities.get(m["place"])
            if not city:
                raise SystemExit("FAIL: ky-city-officials.json has no %s (%s)"
                                 % (m["body"], m["place"]))
            seats = city["seats"]
            mayors = [s for s in seats if s["title"] == "Mayor"]
            council = [s for s in seats if s["title"] != "Mayor"]
            if len(mayors) != 1 or not council:
                raise SystemExit("FAIL: %s's city record has %d mayors and %d "
                                 "council members" % (county, len(mayors), len(council)))
            rec.update(form=m["form"], body=m["body"], law=m["law"],
                       bodySourceUrl=city["sourceUrl"], bodyRead=city["read"])
            rec["executive"] = dict({k: v for k, v in mayors[0].items() if k != "title"},
                                    role="Mayor")
            rec["members"] = [dict({k: v for k, v in s.items() if k != "title"},
                                   role="Council member") for s in council]
            if city.get("unnamedSeats"):
                rec["unnamedSeats"] = city["unnamedSeats"]
            # The judge/executive office survives in both merged counties with
            # few duties; it is an elected county office, not a seat on the council.
            officers = judges + officers
            for p in judges:
                p["office"] = p.pop("role")
        else:
            if len(forms) != 1:
                raise SystemExit("FAIL: %s County lists %s; a fiscal court has one form"
                                 % (county, sorted(forms) or "no magistrates or commissioners"))
            form = forms.pop()
            said = GOV_TYPE.get(c.get("govType") or "")
            if c.get("govType") and said is None:
                raise SystemExit("FAIL: %s County's Government Type %r is not one "
                                 "this builder reads" % (county, c["govType"]))
            if said and said != form:
                raise SystemExit("FAIL: %s County's Government Type says %s and its "
                                 "members are titled %s" % (county, said, form))
            if len(judges) != 1:
                raise SystemExit("FAIL: %s County lists %d judge/executives"
                                 % (county, len(judges)))
            rec.update(form=form, body="Fiscal Court",
                       members=judges + members)
            if unnamed:
                rec["unnamedSeats"] = unnamed
        if county in FORM_NOTES:
            want, note = FORM_NOTES[county]
            if rec["form"] != want:
                raise SystemExit("FAIL: FORM_NOTES describes %s County as listed "
                                 "%s and the directory now says %s; re-read it"
                                 % (county, want, rec["form"]))
            rec["formNote"] = note
            used_notes.add(county)
        rec["officers"] = officers
        out[geoid] = rec
    if unknown:
        raise SystemExit("FAIL: the directory prints title(s) this builder does not "
                         "classify: %s. Add each to OFFICERS or STAFF." % sorted(unknown))
    stale = set(fixes) - used_fixes
    if stale:
        raise SystemExit("FAIL: NAME_FIXES entries match nothing the directory "
                         "prints now, so the typo is gone: %s" % sorted(stale))
    stale = set(FORM_NOTES) - used_notes
    if stale:
        raise SystemExit("FAIL: FORM_NOTES names counties the directory no longer "
                         "carries: %s" % sorted(stale))
    return out


def gate(out):
    members = sum(len(r["members"]) for r in out.values()
                  if r["body"] == "Fiscal Court")
    if len(out) < MIN_COUNTIES or members < MIN_MEMBERS:
        raise SystemExit("FAIL: %d counties and %d fiscal court members, floors %d and %d"
                         % (len(out), members, MIN_COUNTIES, MIN_MEMBERS))
    return len(out), members


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def render(out):
    return json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def selftest():
    counties = [{"properties": {"BASENAME": b, "GEOID": g}} for b, g in
                (("Adair", "21001"), ("Jefferson", "21111"), ("Pike", "21195"))]
    scrape = {"source": {"read": "2026-10-11"}, "counties": {
        "Adair": {"govType": "Magistrate", "address": "424 Public Square",
                  "mailCity": "Columbia", "zip": "42728", "phone": "(270) 384-4703",
                  "website": "http://www.myadaircounty.com/", "sourceUrl": "u1",
                  "officials": [
                      {"first": "Sammy", "last": "Baker", "title": "County Magistrate",
                       "phone": "(270) 378-1536"},
                      {"first": "Larry", "last": "Bryant", "title": "County Judge Executive"},
                      {"first": "", "last": "", "title": "County Magistrate"},
                      {"first": "Jamie", "last": "Richard", "title": "County Sheriff"},
                      {"first": "Jennifer", "last": "Corbin", "title": "County Attorney"},
                      {"first": "Melinda", "last": "Quinn", "title": "County Treasurer"}]},
        "Jefferson": {"govType": "", "sourceUrl": "u2", "officials": [
            {"first": "Queenie", "last": "Averette", "title": "County Judge Executive"},
            {"first": "John", "last": "Aubrey", "title": "County Sheriff"}]},
        "Pike": {"govType": "Commissioner", "sourceUrl": "u3", "officials": [
            {"first": "Ray", "last": "Jones II", "title": "County Judge Executive"},
            {"first": "Jim", "last": "Abshire", "title": "County Commissioner"}]}}}
    cities = {"2148006": {"sourceUrl": "c", "read": "2026-10-09", "seats": [
        {"name": "Craig Greenberg", "title": "Mayor"},
        {"name": "Brent Ackerson", "title": "City Council", "phone": "1"}]}}
    out = build(scrape, cities, counties, fixes={})
    a = out["21001"]
    assert a["body"] == "Fiscal Court" and a["form"] == "magistrate", a
    assert [m["role"] for m in a["members"]] == ["County Judge/Executive", "Magistrate"], a
    assert a["unnamedSeats"] == 1 and a["office"]["address"] == "424 Public Square, Columbia, KY 42728"
    assert [o["office"] for o in a["officers"]] == ["County Attorney", "Sheriff"], a["officers"]
    j = out["21111"]
    assert j["body"] == "Louisville Metro Council" and j["executive"]["name"] == "Craig Greenberg"
    assert j["members"] == [{"name": "Brent Ackerson", "phone": "1", "role": "Council member"}]
    assert j["officers"][0] == {"name": "Queenie Averette", "office": "County Judge/Executive"}
    assert out["21195"]["formNote"].startswith("The state directory lists three")
    # A title nobody classified fails rather than being guessed.
    scrape["counties"]["Adair"]["officials"].append(
        {"first": "Ann", "last": "Lee", "title": "County Surveyor General"})
    try:
        build(scrape, cities, counties, fixes={})
    except SystemExit as e:
        assert "County Surveyor General" in str(e), e
    else:
        raise AssertionError("an unknown title passed")
    print("build_ky_county_officials selftest: ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    out = build(load(SCRAPE), load(CITIES), load(COUNTIES)["features"])
    n, members = gate(out)
    text = render(out)
    if args.check:
        with open(OUT, encoding="utf-8") as fh:
            if fh.read() != text:
                raise SystemExit("FAIL: %s is not what the scrape builds; run "
                                 "python3 ky/scripts/build_ky_county_officials.py"
                                 % os.path.relpath(OUT, REPO))
        print("build-ky-county-officials: OK — %d counties, %d fiscal court members"
              % (n, members))
        return
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("build-ky-county-officials: wrote %s — %d counties, %d fiscal court members"
          % (os.path.relpath(OUT, REPO), n, members))


if __name__ == "__main__":
    main()
