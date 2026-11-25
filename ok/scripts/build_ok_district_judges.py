#!/usr/bin/env python3
"""
Build ok/data/app/ok-district-judges.json: who holds each of Oklahoma's 75
district judge offices, and, where it is someone else, who takes the office
for the term that starts in January 2027.

    python3 ok/scripts/build_ok_district_judges.py          # writes
    python3 ok/scripts/build_ok_district_judges.py --check  # offline, writes nothing

Offline and stdlib only: everything it reads is a dated excerpt in
ok/data/source/courts/ (see its README). build_ok_judicial_districts.py
--check, which CI runs, runs this --check too.

WHO HOLDS EACH OFFICE NOW is the State Election Board's roster (published
March 2025), with the Governor's appointments since then laid over it from the
Judicial Nominating Commission's list. The roster lags: it still names Aletia
Haynes Timmons, who retired on 3 March 2025. The newest district judge
appointment it shows is Jason A. Reese's of 16 December 2024, so every
district judge appointment on the Commission's list after that date must be in
APPOINTMENTS, or the build stops.

WHO TAKES OFFICE IN JANUARY 2027 is the Election Board's April 2026 list of
candidates and its official 2026 results. An office with one candidate was on
no ballot; an office with several is decided by the latest result that gives a
candidate more than half the votes. The build stops on an office with several
candidates and no such result, unless NO_VOTE records why.

THE COURTS' OWN DIRECTORY IS NOT THE SOURCE. oscn.net's robots.txt asks every
automated reader to stay out. One county page (Adair, District 15) was read by
hand in the operator's Chrome on 2026-11-25 before the site put up a "verify
you are human" page, and the build requires District 15 to name the same four
people that page does.

No officeholder's home town is read or written: every source prints one, and
the excerpts leave it out.
"""

import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import build_ok_judicial_districts as districts  # noqa: E402

LABEL = "build-ok-district-judges"
SOURCE = districts.SOURCE
OUT = os.path.join(os.path.dirname(_HERE), "data", "app", "ok-district-judges.json")
READ = "2026-11-25"
ROSTER = "ok-roster-2024-district-judges.txt"
CANDIDATES = "ok-candidates-2026-district-judges.txt"
RESULTS = "ok-results-2026-district-judges.txt"
JNC = "ok-jnc-appointments-district-judges.txt"
OSCN = "oscn-adair-district-judges-2026-11-25.txt"
ROSTER_SHOWS_UP_TO = "2024-12-16"  # Jason A. Reese, District 9 Office 1, is on the roster

# The Commission's position wording -> (district, office). Each was matched to
# the Governor's own notice or the Commission's vacancy page, which name the
# district and office: Green replaced Timmons (vacancy page, okjnc.com/952),
# Getchell replaced Golden in Creek County, Brooks replaced Morris in Carter
# County (Governor's notice of 2025-10-16, "20th Judicial District, Office 1").
APPOINTMENTS = {
    "District Judge, Oklahoma Co., Ofc. 1": (7, 1),
    "District Judge, Creek Co., Ofc. 1": (24, 1),
    "District Judge, Carter Co., Ofc. 1": (20, 1),
}

# Two candidates filed, and the official results list no vote for the office
# in June or November 2026, and the Election Board lists no withdrawal. The
# office's holder is named; who holds it after January 2027 is not.
NO_VOTE = {(7, 10)}

# One person printed two ways in two documents, where the name test below
# cannot tell. (name now, name as filed in April 2026)
SAME_PERSON = {
    ("Bill LaFortune", "WILLIAM DAVID LaFORTUNE, SR."),  # Bill for William; the incumbent
    ("Michael Hogan", "MIKE HOGAN"),  # Mike for Michael; the incumbent
    # The same first and middle names and the same home town in both documents.
    ("Emily Maxwell Herron", "EMILY MAXWELL"),
}

SUFFIXES = {"jr", "sr", "ii", "iii"}


def fail(msg):
    sys.exit("%s: %s" % (LABEL, msg))


def rows(name, width):
    with open(os.path.join(SOURCE, name)) as fh:
        out = [[c.strip() for c in ln.split("|")]
               for ln in fh if ln.strip() and not ln.startswith("#")]
    for r in out:
        if len(r) != width:
            fail("%s: expected %d fields in %r" % (name, width, r))
    return out


def office_key(text, name):
    m = re.match(r"^District (\d+), Office (\d+)$", text)
    if not m:
        fail("%s: unreadable office %r" % (name, text))
    return int(m.group(1)), int(m.group(2))


def tokens(name):
    words = re.sub(r"[^a-z ]", "", name.lower().replace("-", " ")).split()
    return [w for w in words if w not in SUFFIXES]


def same_person(now, filed):
    """Same surname and at least one given name in common, or SAME_PERSON."""
    if (now, filed) in SAME_PERSON:
        return True
    a, b = tokens(now), tokens(filed)
    if not a or not b or a[-1] != b[-1]:
        return False
    return bool({w for w in a[:-1] if len(w) > 1} & {w for w in b[:-1] if len(w) > 1})


def display(filed):
    # shortcut: title-case of an all-caps name; a name printed with lower case
    # (McAFFREY) stops the build, and would need its spelling written down
    if any(c.islower() for c in filed):
        fail("%r is not all capitals; write its spelling down before showing it" % filed)
    return filed.title()


def build():
    offices = {(d, o) for d, lst in districts.read_offices().items() for o, _c in lst}

    holder = {}
    for office, name in rows(ROSTER, 2):
        k = office_key(office, ROSTER)
        if k in holder:
            fail("%s lists %s twice" % (ROSTER, office))
        holder[k] = {"name": name}
    if set(holder) != offices:
        fail("%s names offices %s that the offices excerpt does not, and misses %s"
             % (ROSTER, sorted(set(holder) - offices), sorted(offices - set(holder))))

    used = set()
    for date, position, name in rows(JNC, 3):
        if not position.startswith("District Judge,") or date <= ROSTER_SHOWS_UP_TO:
            continue
        if position not in APPOINTMENTS:
            fail("the Commission lists %s appointed %s on %s, after the roster; add it "
                 "to APPOINTMENTS with its district and office" % (name, position, date))
        k = APPOINTMENTS[position]
        if same_person(holder[k]["name"], name.upper()):
            fail("%s is already the roster's name for District %d, Office %d" % ((name,) + k))
        holder[k] = {"name": name, "appointed": date}
        used.add(position)
    if used != set(APPOINTMENTS):
        fail("APPOINTMENTS names %s, which the Commission's list does not show after %s"
             % (sorted(set(APPOINTMENTS) - used), ROSTER_SHOWS_UP_TO))

    filed = {}
    for office, _number, name in rows(CANDIDATES, 3):
        filed.setdefault(office_key(office, CANDIDATES), []).append(name)
    if set(filed) != offices:
        fail("%s covers %s, not every office" % (CANDIDATES, sorted(set(filed) ^ offices)))

    results = {}
    for date, office, _prec, name, votes, pct in rows(RESULTS, 6):
        k = office_key(office, RESULTS)
        if name not in filed.get(k, []):
            fail("%s: %s is not a candidate for %s in April 2026" % (RESULTS, name, office))
        results.setdefault(k, {}).setdefault(date, []).append((name, int(votes), float(pct)))

    for k in sorted(offices):
        names = filed[k]
        if len(names) == 1:
            if k in results:
                fail("District %d, Office %d had one candidate and yet a result" % k)
            winner, how = names[0], "only-candidate"
        elif k in NO_VOTE:
            if k in results:
                fail("District %d, Office %d is in NO_VOTE and has a result" % k)
            holder[k]["noVote"] = True
            continue
        else:
            latest = results.get(k, {})
            if not latest:
                fail("District %d, Office %d had %d candidates and no result"
                     % (k + (len(names),)))
            race = latest[max(latest)]
            top = [n for n, _v, p in race if p > 50]
            if len(top) != 1:
                fail("District %d, Office %d: no candidate has more than half the votes "
                     "on %s" % (k + (max(latest),)))
            winner, how = top[0], "elected"
        if not same_person(holder[k]["name"], winner):
            holder[k]["next"] = {"name": display(winner), "how": how}

    adair = sorted(n.split(",")[0].lower() for d, n in rows(OSCN, 2) if d == "District 15")
    ours = sorted(tokens(holder[(15, o)]["name"])[-1] for o in range(1, 5))
    if adair != ours:
        fail("the court's Adair page names %s for District 15, and this build %s"
             % (adair, ours))

    out = {}
    for d, o in sorted(offices):
        rec = {"office": o}
        rec.update(holder[(d, o)])
        out.setdefault(str(d), {"read": READ, "offices": []})["offices"].append(rec)
    return out


def dump(data):
    return json.dumps(data, indent=1, ensure_ascii=False) + "\n"


def run_check():
    want = dump(build())
    with open(OUT) as fh:
        if fh.read() != want:
            fail("%s is not what the sources build; run "
                 "ok/scripts/build_ok_district_judges.py" % os.path.relpath(OUT))
    print("%s: OK" % LABEL)


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--check", action="store_true", help="compare, write nothing")
    if ap.parse_args().check:
        run_check()
        return
    data = build()
    with open(OUT, "w") as fh:
        fh.write(dump(data))
    n = sum(len(v["offices"]) for v in data.values())
    nxt = sum(1 for v in data.values() for r in v["offices"] if "next" in r)
    print("%s: %d offices in %d districts, %d changing hands in January 2027"
          % (LABEL, n, len(data), nxt))


if __name__ == "__main__":
    main()
