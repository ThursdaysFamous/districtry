#!/usr/bin/env python3
"""
Build tn/data/app/tn-trial-judges.json: the circuit, chancery, criminal and
probate judges of each of Tennessee's 32 judicial districts, keyed by district.

    python3 tn/scripts/build_tn_trial_judges.py          # writes
    python3 tn/scripts/build_tn_trial_judges.py --check  # offline: the shipped file must equal a rebuild

It reads two snapshots in tn/data/source/courts/, both read ONCE on 2026-11-25
in the operator's own Chrome (see their headers): the state courts' judge
directory, and the courts' own appointment and vacancy notices. Nothing here
fetches. tncourts.gov answers this project's reader with a managed challenge,
so there is no weekly job; the re-check is in tn/WATCH.md.

THE DIRECTORY IS NOT CURRENT, so it is not shipped as read. Against the courts'
own notices it still lists seven people who do not hold a district seat: four
judges who retired, the prior holders of the two seats the courts have declared
vacant, and a senior judge. Each correction below cites its notice, the notice
must name the person, and each must match exactly one directory row, so a
corrected directory stops the build instead of being corrected twice. Two empty
duplicate pages are dropped too.

THE NOTICES TAKE PEOPLE OUT AND NEVER PUT ANYONE IN. Three judges appointed in
2025 are not in the directory, and Nashville's own trial courts' page, read the
same day, shows why for two of them: neither is on it, and the people the state
directory names instead are. Appointees stand at the next August election, so an
appointment notice says who sat, not who sits. The 20th District's judges must
equal that page (CONTROL), which the build checks.

WHICH DISTRICT. A row's district is every district its counties lie in, read
against the county list tn-judicial-districts.json is drawn from; where the
directory also prints a district it must be one of them. So the chancellor
whose counties span the 4th and 5th is named in both, and the 32nd's judges,
whose district the directory leaves blank, are placed by their counties.
"""

import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import build_tn_judicial_districts as bj  # noqa: E402  (the selector reader)

LABEL = "build-tn-trial-judges"
READ = "2026-11-25"
DIRECTORY = "tncourts-trial-judges-%s.tsv" % READ
NOTICES = "tncourts-notices-%s.tsv" % READ
OUT = os.path.join(os.path.dirname(_HERE), "data", "app", "tn-trial-judges.json")
SITE = "https://www.tncourts.gov"
PAGE = SITE + "/courts/circuit-criminal-chancery-courts/judges"
ROWS = 174  # the directory's four trial-court types on 2026-11-25
OFFICES = {"Chancellor", "Circuit Court Judge", "Criminal Court Judge",
           "Probate Court Judge"}

# Directory rows left out: (name, the judge's page, reason, notice).
DROPS = [
    ("Jeremy D. Ball", "/courts/circuit-criminal-chancery-courts/judges/jeremy-d-ball",
     "a second, empty page for the judge the directory lists in full at jeremy-d-ball-0", None),
    ("Adrienne Ogle", "/courts/circuit-criminal-chancery-courts/judges/adrienne-ogle",
     "a second, empty page for Adrienne Waters Ogle, listed in full", None),
    ("Michael Spitzer", "/courts/circuit-criminal-chancery-courts/judges/michael-e-spitzer",
     "retired; William Lane was appointed to his seat on 15 August 2025",
     "/press/2025/08/18/governor-lee-announces-judicial-district-appointments"),
    ("Paula L. Skahan", "/courts/judges/paula-l-skahan",
     "retired; Raymond Lepone was appointed to her seat",
     "/news/2025/08/29/governor-lee-announces-30th-judicial-district-appointments"),
    ("Cheryl A. Blackburn", "/courts/circuit-criminal-chancery-courts/judges/cheryl-blackburn",
     "retired; Jim Todd was appointed to her seat",
     "/news/2025/09/19/governor-lee-announces-20th-judicial-district-appointment"),
    ("Phillip Robinson", "/courts/circuit-criminal-chancery-courts/judges/phillip-robinson",
     "retired; Bethany Glandorf was appointed to his seat",
     "/news/2025/11/20/governor-lee-announces-20th-judicial-district-circuit-court-appointment"),
    ("G. Scott Green", "/courts/circuit-criminal-chancery-courts/judges/g-scott-green",
     "the prior incumbent of the 6th District criminal court seat the courts declared vacant",
     "/press/2026/11/10/commission-accepting-applications-6th-judicial-district-criminal-court-judge"),
    ("John Harvey Cameron Jr.", "/courts/judges/john-cam-cameron",
     "the prior incumbent of the 12th District circuit court seat the courts declared vacant",
     "/press/2026/10/02/commission-issues-new-notice-vacancy-12th-judicial-district"),
    ("D. Kelly Thomas Jr.", "/courts/court-criminal-appeals/judges/d-kelly-thomas-jr-retired-2022",
     "appointed a senior judge, who sits where the Chief Justice designates, not a judge the "
     "district elects; his directory page is dated 2023, the year of that appointment",
     "/press/2023/08/30/supreme-court-appoints-retired-judge-kelly-thomas-senior-judge"),
]
# The office as the appointment notice gives it, where the directory's is narrower.
OFFICE_FROM_NOTICE = {
    "William K. Lane III": ("Circuit and Chancery Court Judge",
                            "/press/2025/08/18/governor-lee-announces-judicial-district-appointments"),
}
# The control: Nashville's trial courts' own list, read the same day with this
# project's reader (tn/data/source/courts/, see its header).
CONTROL = ("20", "nashville-trial-courts-judges-%s.txt" % READ)
# Seats the courts declared vacant and had not filled when read.
VACANCIES = [
    (6, "Criminal Court Judge",
     "One criminal court seat is vacant: the courts invited applicants on 10 November 2026 "
     "and set the hearing for 11 December 2026. The governor appoints from the nominees.",
     "/press/2026/11/10/commission-accepting-applications-6th-judicial-district-criminal-court-judge"),
    (12, "Circuit Court Judge",
     "One circuit court seat is vacant: the courts sent three nominees to the governor on "
     "22 October 2026, and no appointment had been announced by 25 November 2026.",
     "/press/2026/10/22/commission-sends-three-nominees-governor-12th-judicial-district-circuit-court"),
]


def fail(msg):
    sys.exit("%s: %s" % (LABEL, msg))


def lines(name):
    return [ln.rstrip("\n") for ln in open(os.path.join(bj.SOURCE, name))
            if ln.strip() and not ln.startswith("#")]


def surname(name):
    return re.sub(r",?\s+(Jr\.|Sr\.|II|III|IV)$", "", name.strip()).split()[-1]


def check_control(out):
    district, name = CONTROL
    want = {}
    for ln in lines(name):
        office, people = ln.split("\t")
        want[office] = sorted(surname(p) for p in people.split("; "))
    have = {}
    for j in out[district]["judges"]:
        have.setdefault(j["office"], []).append(surname(j["name"]))
    have = {k: sorted(v) for k, v in have.items()}
    if have != want:
        fail("district %s: the corrected directory gives %s and %s gives %s"
             % (district, have, name, want))


def build():
    notices = {}
    for ln in lines(NOTICES):
        date, url, text = ln.split("\t")
        notices[url[len(SITE):]] = (date, text)

    def cite(path, *names):
        if path not in notices:
            fail("no notice %s in %s" % (path, NOTICES))
        for n in names:
            if surname(n) not in notices[path][1]:
                fail("the notice %s does not name %s" % (path, n))
        return SITE + path

    by_district, _urls = bj.read_selector()
    county_district = {c: d for d, cs in by_district.items() for c in cs}

    rows = [ln.split("\t") for ln in lines(DIRECTORY)]
    if len(rows) != ROWS:
        fail("%s has %d rows, expected %d" % (DIRECTORY, len(rows), ROWS))
    drops = {(n, p): (why, note) for n, p, why, note in DROPS}
    used = set()
    out = {str(d): {"read": READ, "page": PAGE, "judges": [], "vacancies": []}
           for d in sorted(by_district)}
    for name, path, office, counties, district in rows:
        if office not in OFFICES:
            fail("%s: office %r" % (name, office))
        if (name, path) in drops:
            why, note = drops[(name, path)]
            if note:
                cite(note, name)
            used.add((name, path))
            continue
        names = [c.strip() for c in counties.split(",") if c.strip()]
        unknown = [c for c in names if c not in county_district]
        if unknown:
            fail("%s: counties %s are in no district" % (name, unknown))
        ds = sorted({county_district[c] for c in names})
        if district:
            if ds and int(district) not in ds:
                fail("%s: the directory says district %s, the counties %s say %s"
                     % (name, district, names, ds))
            ds = ds or [int(district)]
        if not ds:
            fail("%s: no county and no district" % name)
        rec = {"name": name, "office": office, "url": SITE + path}
        if name in OFFICE_FROM_NOTICE:
            rec["office"] = OFFICE_FROM_NOTICE[name][0]
            rec["officeSource"] = cite(OFFICE_FROM_NOTICE[name][1], name)
        for d in ds:
            out[str(d)]["judges"].append(dict(rec))
    missing = set(drops) - used
    if missing:
        fail("corrections that match no directory row: %s" % sorted(missing))
    for d, office, text, note in VACANCIES:
        out[str(d)]["vacancies"].append({"office": office, "note": text, "url": cite(note)})
    check_control(out)
    for d, entry in out.items():
        if not entry["judges"]:
            fail("district %s names no judge" % d)
        entry["judges"].sort(key=lambda j: (j["office"], surname(j["name"]), j["name"]))
    return out


def render():
    out = build()
    return out, json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def run_check():
    """The --check, also run by build_tn_judicial_districts.py --check, which CI runs."""
    out, text = render()
    if not os.path.exists(OUT) or open(OUT).read() != text:
        fail("%s differs from a rebuild; run without --check" % OUT)
    print("%s: OK (%d judge listings in %d districts)"
          % (LABEL, sum(len(e["judges"]) for e in out.values()), len(out)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--check", action="store_true", help="compare, write nothing")
    if ap.parse_args().check:
        run_check()
        return
    out, text = render()
    with open(OUT, "w") as fh:
        fh.write(text)
    print("%s: wrote %d judge listings in %d districts"
          % (LABEL, sum(len(e["judges"]) for e in out.values()), len(out)))


if __name__ == "__main__":
    main()
