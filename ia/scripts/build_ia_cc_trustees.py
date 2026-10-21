#!/usr/bin/env python3
"""
Build ia/data/app/ia-cc-trustees.json: the trustee elected from each director
district of Iowa's community colleges, keyed by the same `ddkey`
("<merged area>-<district>") the CC Director District layer draws.

Input is ia_cc_trustee_scraper.py's output (ia/scripts/.cache/ia_cc_trustees.json).

WHAT IS HELD, PER COLLEGE
--------------------------
A college's seats ship only if the page named EXACTLY the districts its board
has: 1..N, where N is the highest district its own plan draws in
`ia-cc-director-districts.json`. Des Moines Area's plan omits District 2 while
its board page names a District 2 trustee, which is why the set is 1..N rather
than the drawn set: a trustee with no drawn district still ships, keyed by the
seat, and simply has no polygon to answer at. A page naming one district too
few or too many is a page that changed shape, and that college is NOT written
from it.

A COLLEGE THAT FAILS KEEPS ITS LAST-GOOD SEATS (Adam's ruling of 2026-09-19:
a failed read stops the fetch and never unpublishes what we already have). It
carries its own `asOf`, the date its page was last actually read, so a card
never prints a read date for a page that was not read this week. A college
with no last-good record and no good read is left out and printed.

Every name is checked to look like a name (no digits, no "@"), every e-mail
like an e-mail, and no field may read as a street address: Hawkeye's page
prints each trustee's home address beside their name and none of it ships.

Northeast Iowa names its trustees by school district and not by number, so it
ships as a list under `undistricted` and the card says why it names no one for
a district.

Usage:
    python3 ia/scripts/build_ia_cc_trustees.py
    python3 ia/scripts/build_ia_cc_trustees.py --check
"""

import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.join(HERE, "..")
RAW = os.path.join(HERE, ".cache", "ia_cc_trustees.json")
OUT = os.path.join(IA, "data", "app", "ia-cc-trustees.json")
DISTRICTS = os.path.join(IA, "data", "app", "ia-cc-director-districts.json")
COLLEGES = os.path.join(IA, "data", "app", "ia-community-colleges.json")

UNDISTRICTED = {"1"}        # Northeast Iowa: trustees listed by school district
MIN_COLLEGES = 14           # every districted college, or nothing is written
STREET = re.compile(
    r"\b\d{1,6}\s+\w+(?:\s+\w+){0,3}\s+(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Ln|"
    r"Lane|Ct|Court|Blvd|Way|Pl|Place|Cir|Circle|Hwy|Highway|Trl|Ter)\b\.?", re.I)
NAME_OK = re.compile(r"^[A-Za-z][A-Za-z .'’-]+$")
EMAIL_OK = re.compile(r"^[\w.+'-]+@[\w-]+(?:\.[\w-]+)+$")
PHONE_OK = re.compile(r"^\(?\d{3}\)?[ .-]\d{3}-\d{4}$")


def fail(msg):
    print("build-ia-cc-trustees: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def board_sizes():
    """merged area -> highest director district its plan draws."""
    sizes = {}
    for f in json.load(open(DISTRICTS))["features"]:
        p = f["properties"]
        area = str(p["collegedistrict"])
        sizes[area] = max(sizes.get(area, 0), int(p["district"]))
    return sizes


def college_names():
    """merged area -> the college name the community-college layer ships."""
    names = {}
    for f in json.load(open(DISTRICTS))["features"]:
        p = f["properties"]
        names[str(p["collegedistrict"])] = p["name"]
    return names


def record_problems(r):
    out = []
    if r.get("vacant"):
        return [] if set(r) == {"vacant"} else ["a vacant seat carries other fields"]
    name = r.get("name", "")
    if not NAME_OK.match(name):
        out.append("name %r does not read as a name" % name)
    if "email" in r and not EMAIL_OK.match(r["email"]):
        out.append("e-mail %r does not read as an address" % r["email"])
    if "phone" in r and not PHONE_OK.match(r["phone"]):
        out.append("telephone %r does not read as one number" % r["phone"])
    if "termEnds" in r and not re.fullmatch(r"20\d\d", r["termEnds"]):
        out.append("term end %r is not a year" % r["termEnds"])
    for k, v in r.items():
        if isinstance(v, str) and STREET.search(v):
            out.append("field %s reads as a street address" % k)
    allowed = {"name", "role", "email", "phone", "termEnds", "profileUrl"}
    extra = set(r) - allowed
    if extra:
        out.append("unexpected field(s) %s" % sorted(extra))
    return out


def check_college(area, c, size):
    """Problems with one scraped college; empty means it may ship."""
    if area in UNDISTRICTED:
        people = c.get("undistricted") or []
        probs = [p for r in people for p in record_problems(r)]
        if len(people) != size:
            probs.append("names %d trustees for a %d-seat board" % (len(people), size))
        return probs
    seats = c.get("seats") or {}
    want = {str(n) for n in range(1, size + 1)}
    probs = []
    if set(seats) != want:
        probs.append("names districts %s, wanted 1..%d" % (sorted(seats, key=int), size))
    for d, r in seats.items():
        probs += ["district %s: %s" % (d, p) for p in record_problems(r)]
    named = [r["name"] for r in seats.values() if "name" in r]
    if len(set(named)) != len(named):
        probs.append("one name holds two seats")
    return probs


def build(raw, previous, today):
    sizes = board_sizes()
    names = college_names()
    colleges, seats = {}, {}
    carried, dropped = [], []
    prev_colleges = (previous or {}).get("colleges", {})
    for area in sorted(sizes, key=int):
        got = raw.get("colleges", {}).get(area)
        probs = check_college(area, got, sizes[area]) if got else ["page not read"]
        if probs:
            if area in prev_colleges:
                colleges[area] = prev_colleges[area]
                carried.append((area, probs))
            else:
                dropped.append((area, probs))
            continue
        entry = {"college": names[area], "sourceUrl": got["sourceUrl"], "asOf": today}
        if area in UNDISTRICTED:
            entry["undistricted"] = got["undistricted"]
        else:
            entry["seats"] = {d: got["seats"][d] for d in sorted(got["seats"], key=int)}
        # A college whose page says exactly what it said last time keeps the
        # date it was first read that way: a date that moved every week would
        # open a bot PR every week for no change, and an older date understates
        # a read rather than claiming one that did not happen.
        old = prev_colleges.get(area)
        if old and {k: v for k, v in entry.items() if k != "asOf"} == \
                {k: v for k, v in old.items() if k != "asOf"}:
            entry["asOf"] = old["asOf"]
        colleges[area] = entry
    for area, c in colleges.items():
        for d, r in (c.get("seats") or {}).items():
            seats["%s-%s" % (area, d)] = r
    return {"colleges": colleges, "seats": dict(sorted(seats.items(), key=lambda kv: [int(x) for x in kv[0].split("-")]))}, carried, dropped


def check_shipped():
    d = json.load(open(OUT))
    sizes = board_sizes()
    probs = []
    for area, c in d["colleges"].items():
        probs += ["area %s: %s" % (area, p) for p in check_college(area, c, sizes[area])]
        for k in ("college", "sourceUrl", "asOf"):
            if k not in c:
                probs.append("area %s carries no %s" % (area, k))
        for dn, r in (c.get("seats") or {}).items():
            if d["seats"].get("%s-%s" % (area, dn)) != r:
                probs.append("seat %s-%s disagrees with its college's list" % (area, dn))
    keys = {"%s-%s" % (a, dn) for a, c in d["colleges"].items() for dn in (c.get("seats") or {})}
    if set(d["seats"]) != keys:
        probs.append("the seats index and the colleges' lists differ")
    districted = [a for a in d["colleges"] if a not in UNDISTRICTED]
    if len(districted) < MIN_COLLEGES:
        probs.append("%d districted colleges, floor %d" % (len(districted), MIN_COLLEGES))
    if probs:
        fail("; ".join(probs))
    named = sum(1 for r in d["seats"].values() if "name" in r)
    print("build-ia-cc-trustees: OK — %d colleges, %d seats, %d named" % (
        len(d["colleges"]), len(d["seats"]), named))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        check_shipped()
        return
    raw = json.load(open(RAW))
    previous = json.load(open(OUT)) if os.path.exists(OUT) else None
    today = datetime.date.today().isoformat()
    out, carried, dropped = build(raw, previous, today)
    for area, probs in carried:
        print("build-ia-cc-trustees: area %s KEPT FROM LAST GOOD READ (%s): %s" % (
            area, out["colleges"][area].get("asOf"), "; ".join(probs)), file=sys.stderr)
    for area, probs in dropped:
        print("build-ia-cc-trustees: area %s LEFT OUT, no last-good record: %s" % (
            area, "; ".join(probs)), file=sys.stderr)
    districted = [x for x in out["colleges"] if x not in UNDISTRICTED]
    if len(districted) < MIN_COLLEGES:
        fail("%d districted colleges, floor %d; nothing written" % (len(districted), MIN_COLLEGES))
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    named = sum(1 for r in out["seats"].values() if "name" in r)
    print("build-ia-cc-trustees: wrote %s — %d colleges, %d seats, %d named, %d vacant" % (
        os.path.relpath(OUT), len(out["colleges"]), len(out["seats"]), named,
        sum(1 for r in out["seats"].values() if r.get("vacant"))))


if __name__ == "__main__":
    main()
