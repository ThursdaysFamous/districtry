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

WHICH DISTRICT A MEMBER HOLDS. The directory names each magistrate and
commissioner and never says which district one holds. The State Board of
Elections' 2022 recap sheets do (ky_fiscal_court_results_scraper.py writes
them to ky/data/source/ky-fiscal-court-2022-results.json), so a member gains a
`district` when exactly one 2022 contest for the county's own office was won by
a candidate with the member's surname (and, where two winners share a surname,
the member's first name). Nothing else is inferred: a member who took the seat
after that election, a sheet that was not served, or a name spelled two ways
leaves the member without a district, and the card still lists them. The
same name match gives each Louisville Metro and Lexington-Fayette council
member the district their government's own council map names them for
(ky-county-districts.source.json); Lexington's at-large members stay without
one. The fiscal court match holds 346 of 562 members (2026-10-11): 245 of 252 where the sheet carries
text, 101 of 300 where it is a scan, most of the rest being scans whose
hand-tallied grids text recognition cannot read. Measured 2026-10-11: 120
counties, 520 magistrates and 42 commissioners named, one
magistrate row in Bracken with no name.

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
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)

SCRAPE = os.path.join(INSTANCE, "data", "source", "ky-county-officials-scrape.json")
CITIES = os.path.join(INSTANCE, "data", "app", "ky-city-officials.json")
COUNTIES = os.path.join(INSTANCE, "data", "app", "state-counties.json")
OUT = os.path.join(INSTANCE, "data", "app", "ky-county-officials.json")
RESULTS = os.path.join(INSTANCE, "data", "source", "ky-fiscal-court-2022-results.json")
# Which council district each Louisville and Lexington member holds, as the two
# governments' own council maps name them (build_ky_county_districts.py).
SEATS = os.path.join(INSTANCE, "data", "source", "ky-county-districts.source.json")

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
                  "law": "KRS 67C",
                  "mapPublisher": "LOJIC (Louisville/Jefferson County Information Consortium)"},
    "Fayette": {"place": "2146027", "form": "urban-county",
                "body": "Lexington-Fayette Urban County Council",
                "law": "KRS 67A",
                "mapPublisher": "Lexington-Fayette Urban County Government"},
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
# Measured 2026-10-11: 346 of 562 magistrates and commissioners matched, 245
# of 252 in the 51 counties whose sheets carry text and 101 of 300 in the 67
# read from scans. A rebuild matching far fewer has lost the results file.
MIN_DISTRICTED = 330


# Name parts that say nothing about who someone is.
SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}
# The contest heading each fiscal court form is elected under.
CONTEST = {"magistrate": "MAGISTRATE", "commissioner": "COUNTY COMMISSIONER"}


def name_tokens(name):
    """Lower-case ASCII words of a name, quoted nicknames and suffixes dropped."""
    name = re.sub(r'["“”][^"“”]*["“”]', " ", name)
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return [t for t in re.sub(r"[^a-z]", " ", name.lower()).split() if t not in SUFFIXES]


# A nickname whose first letter is not its given name's, so "Bobby Cummins"
# (directory) and "Robert N. CUMMINS" (ballot) can be read as one person.
NICK_INITIAL = {"bobby": "r", "bob": "r", "rob": "r", "dick": "r", "bill": "w",
                "peggy": "m", "ted": "e", "ned": "e", "hank": "h", "jack": "j"}


def initials(name):
    """Every initial a person's given names could be written with, quoted
    nicknames included."""
    quoted = " ".join(re.findall(r'["“”]([^"“”]*)["“”]', name))
    toks = name_tokens(name)[:-1] + name_tokens(quoted)
    return {t[0] for t in toks} | {NICK_INITIAL[t] for t in toks if t in NICK_INITIAL}


def district_sort(d):
    return (0, int(d), "") if d.isdigit() else (1, 0, d)


def attach_districts(rec, sheet, want=None):
    """Give each member the district whose 2022 winner bears their name.

    A member matches only when the surname is the winner's, and one of the
    member's given-name initials is one of the winner's (so "Sara COMBS" never
    gives Dennis Combs a district), in exactly one contest for the county's own office, narrowed by
    first name when two winners share a surname, and no other member has
    already taken that district."""
    want = want or CONTEST[rec["form"]]
    winners = {}
    for key, contest in (sheet or {}).get("contests", {}).items():
        office, _, district = key.partition("|")
        if office == want:
            winners[district] = (name_tokens(contest["winner"]), initials(contest["winner"]))
    taken = set()
    for m in rec["members"]:
        if m["role"] == "County Judge/Executive":
            continue
        mine = name_tokens(m["name"])
        if not mine:
            continue
        given = initials(m["name"])
        hits = [d for d, (w, wi) in winners.items()
                if w and w[-1] == mine[-1] and given & wi]
        if len(hits) > 1:
            hits = [d for d in hits if winners[d][0][0] == mine[0]]
        if len(hits) == 1 and hits[0] not in taken:
            taken.add(hits[0])
            m["district"] = hits[0]
    if taken:
        judge = [m for m in rec["members"] if m["role"] == "County Judge/Executive"]
        rest = [m for m in rec["members"] if m["role"] != "County Judge/Executive"]
        rest.sort(key=lambda m: (0,) + district_sort(m["district"]) if "district" in m
                  else (1, 0, 0, ""))
        rec["members"] = judge + rest
        rec["districtsFrom"] = {"url": sheet["url"], "election": sheet["election"],
                                "method": sheet["method"]}


def attach_council(rec, seats, source):
    """Give each council member the district their government's council map
    names them for, by the attach_districts name rule. A name on the map
    carries no credentials ("Shayla Lynch, J.D." is Lynch)."""
    winners = {d: re.sub(r",.*$", "", n) for d, n in (seats or {}).items()}
    sheet = {"contests": {"COUNCIL|%s" % d: {"winner": n} for d, n in winners.items()}}
    probe = {"members": rec["members"]}
    attach_districts(probe, dict(sheet, url=source["url"], election=None, method="map"),
                     want="COUNCIL")
    rec["members"] = probe["members"]
    if "districtsFrom" in probe:
        rec["districtsFrom"] = {"url": source["url"], "publisher": source["publisher"],
                                "method": "map"}


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


def build(scrape, cities, counties, fixes=None, results=None, council_seats=None):
    fixes = NAME_FIXES if fixes is None else fixes
    council_seats = council_seats or {}
    results = results or {}
    election = (results.get("source") or {}).get("election")
    sheets = {k.lower(): dict(v, election=election)
              for k, v in (results.get("counties") or {}).items()}

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
            if geoid in (council_seats.get("councilSeats") or {}):
                attach_council(rec, council_seats["councilSeats"][geoid],
                               {"url": council_seats["councils"][geoid],
                                "publisher": m["mapPublisher"]})
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
            attach_districts(rec, sheets.get(county.lower()))
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
    districted = sum(1 for r in out.values() for m in r["members"] if "district" in m)
    if len(out) < MIN_COUNTIES or members < MIN_MEMBERS or districted < MIN_DISTRICTED:
        raise SystemExit("FAIL: %d counties, %d fiscal court members and %d with a "
                         "district, floors %d, %d and %d"
                         % (len(out), members, districted, MIN_COUNTIES, MIN_MEMBERS,
                            MIN_DISTRICTED))
    return len(out), members, districted


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
    results = {"source": {"election": "2022-11-08"}, "counties": {"ADAIR": {
        "url": "r1", "method": "text", "contests": {
            "MAGISTRATE|3": {"winner": "Sammy L. BAKER"},
            "COUNTY COMMISSIONER|1": {"winner": "Ann LEE"}}}}}
    seats = {"councils": {"21111": "map"},
             "councilSeats": {"21111": {"7": "BRENT T. ACKERSON", "2": "SHAYLA LYNCH, J.D."}}}
    out = build(scrape, cities, counties, fixes={}, results=results, council_seats=seats)
    assert out["21111"]["members"][0]["district"] == "7", out["21111"]
    assert out["21111"]["districtsFrom"]["url"] == "map"
    del out["21111"]["members"][0]["district"]
    a = out["21001"]
    assert a["members"][1]["district"] == "3" and a["districtsFrom"]["url"] == "r1", a
    # A shared surname with no shared initial is two people, not one.
    rec = {"form": "magistrate", "members": [{"name": "Dennis Combs", "role": "Magistrate"}]}
    attach_districts(rec, {"contests": {"MAGISTRATE|2": {"winner": "Sara COMBS"}}})
    assert "district" not in rec["members"][0] and "districtsFrom" not in rec, rec
    rec = {"form": "magistrate", "members": [{"name": "Bobby Cummins", "role": "Magistrate"}]}
    attach_districts(rec, {"url": "r", "election": "e", "method": "ocr",
                           "contests": {"MAGISTRATE|1": {"winner": "Robert N. CUMMINS"}}})
    assert rec["members"][0]["district"] == "1", rec
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
    out = build(load(SCRAPE), load(CITIES), load(COUNTIES)["features"],
                results=load(RESULTS), council_seats=load(SEATS))
    n, members, districted = gate(out)
    text = render(out)
    if args.check:
        with open(OUT, encoding="utf-8") as fh:
            if fh.read() != text:
                raise SystemExit("FAIL: %s is not what the scrape builds; run "
                                 "python3 ky/scripts/build_ky_county_officials.py"
                                 % os.path.relpath(OUT, REPO))
        print("build-ky-county-officials: OK — %d counties, %d fiscal court members, "
              "%d with a district" % (n, members, districted))
        return
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("build-ky-county-officials: wrote %s — %d counties, %d fiscal court members, "
          "%d with a district" % (os.path.relpath(OUT, REPO), n, members, districted))


if __name__ == "__main__":
    main()
