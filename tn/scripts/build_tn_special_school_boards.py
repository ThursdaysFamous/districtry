#!/usr/bin/env python3
"""
Build tn/data/app/tn-special-school-boards.json: the board of education of
each of Tennessee's fourteen special school districts, written down from each
district's own page and proved against it on every build.

    python3 tn/scripts/build_tn_special_school_boards.py            # read every page, prove every name, write
    python3 tn/scripts/build_tn_special_school_boards.py --check    # offline
    python3 tn/scripts/build_tn_special_school_boards.py --watch    # is every name still on its page?

WHY THESE FOURTEEN. A special school district is a school system the General
Assembly created by a private act, with a board of education its own voters
elect, so it is the kind of special district whose board the done standard's
level 12 asks a card to name (docs/DONE_STANDARD.md; Adam, 2026-10-21, "Only
ones with elected reps"). The other elected kinds were ruled out by Adam on
2026-10-26: a utility district's commissioners are elected by its customers,
"Not voters". The Census draws all fourteen, eleven in its unified layer and
three (Franklin, Lebanon and Paris) in its elementary layer, and this app
draws both layers. Thirteen carry "Special" in the Census's name; Gibson
County's is "Gibson County School District", and the district calls itself
Gibson County Special School District. The build asks TIGERweb for every
Tennessee school district and refuses to write unless every district whose
name says "Special", and Gibson County's, is in the seats file under the
Census's own name and layer, so a fifteenth that appears is not missed.

WHERE THE NAMES COME FROM. Each district's own page, because no state office
publishes the members of Tennessee's school boards (gap
tn-school-board-members). The pages were read on 2026-10-26 with this
project's own client, robots.txt read first at every hop, and three hosts the
districts also use were not read because their robots.txt refuses this
client (hrbschools.org, mckenziessd.org and rhms.net); each district's page
here is on the host the district now uses. What a page prints and what it
leaves out:
  * Gibson County's lists one member per district with the year each term
    ends, Lebanon's one member per zone under the heading "2026 - 2027", and
    West Carroll's two per precinct. The card shows the district, zone or
    precinct as the page gives it. None of these is drawn: no office
    publishes the lines.
  * Richard City's heads its list "2025-2026", which the card says.
  * South Carroll's lists three members and Trenton's five. Neither says how
    many seats the board has, and the card says only that these are the
    members the page lists.
  * Gibson County's and South Carroll's print members' home addresses. None
    is carried, here or anywhere.

CONTACTS follow scripts/city_councils.py's rules (Adam, 2026-10-17): an
e-mail address or a number the page prints beside one member ships on that
member, and one printed for the board ships on nobody. Where Gibson County's
page prints two addresses for a member, the one on the district's domain
ships.

The proof, the record and the contact checks are scripts/city_councils.py's,
which this file calls rather than copying. What this file adds is the list
of districts and the shape of a seat: a member's office on the board
("Chairman") or "Member", and the district, zone or precinct the page lists
them under, if any.
"""

import json
import os
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import city_councils as cc  # noqa: E402

UA = "districtry/1.0 (+https://districtry.com/tn/)"
UNIFIED, ELEMENTARY = "school-district-unified", "school-district-elementary"
TIGER_LAYERS = {UNIFIED: 0, ELEMENTARY: 2}
TIGER_QUERY = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/School/"
               "MapServer/%d/query?where=STATE%%3D%%2747%%27&outFields=GEOID%%2CNAME"
               "&returnGeometry=false&f=json")
# Gibson County's Census name does not say "Special"; the district's own name does.
NOT_NAMED_SPECIAL = {"4701400"}

# Members per district, as each district's own page lists them on 2026-10-26.
# A page that adds or drops a member moves these: read the page, then change
# the number deliberately.
SEATS = {
    "4702970": 7,  # Milan
    "4701400": 7,  # Gibson County, one per district
    "4703900": 3,  # South Carroll, as many as its page lists
    "4704100": 5,  # Trenton
    "4703300": 5,  # Oneida
    "4701260": 6,  # Franklin (elementary)
    "4702370": 5,  # Lebanon (elementary), one per zone
    "4703360": 7,  # Paris (elementary)
    "4702010": 6,  # Huntingdon
    "4702790": 7,  # McKenzie
    "4704490": 6,  # West Carroll, two per precinct
    "4701890": 7,  # Hollow Rock-Bruceton
    "4703540": 4,  # Richard City
    "4701390": 6,  # Bradford
}

SPEC = cc.Spec(
    tag="tn",
    label="build_tn_special_school_boards",
    user_agent=UA,
    seats_file="tn-special-school-board-seats.json",
    out_file="tn-special-school-boards.json",
    seats=SEATS,
    # 25 members' e-mail addresses and 10 members' numbers were written down
    # on 2026-10-26; these floors are about two thirds of each.
    min_emails=17,
    min_phones=7,
)

DISTRICT_KEYS = {"name", "census", "layer", "body", "how", "note", "ownName", "sources",
                 "seats", "officeLines", "officeMailboxes"}
SEAT_KEYS = {"seat", "name", "as", "from", "area", "email", "phone", "phonesExtra"}


def load():
    with open(SPEC.seats_path, encoding="utf-8") as fh:
        return json.load(fh).get("districts") or {}


def check_districts(districts):
    problems = []
    if set(districts) != set(SEATS):
        problems.append("the seats file names %s and the builder states seat counts for %s"
                        % (", ".join(sorted(districts)), ", ".join(sorted(SEATS))))
    for geoid, d in sorted(districts.items()):
        where = "%s (%s)" % (d.get("name"), geoid)
        odd = set(d) - DISTRICT_KEYS
        if odd:
            problems.append("%s carries keys this builder does not read: %s"
                            % (where, ", ".join(sorted(odd))))
        for key in ("name", "census", "body", "how"):
            if not isinstance(d.get(key), str) or not d[key].strip():
                problems.append("%s has no %s" % (where, key))
        if d.get("name") != d.get("census"):
            problems.append("%s: name and census differ; the card titles a district by the "
                            "Census's name, which the map prints" % where)
        if d.get("layer") not in TIGER_LAYERS:
            problems.append("%s: layer %r is not a school district layer this builder reads"
                            % (where, d.get("layer")))
        sources = d.get("sources") or {}
        if len(sources) != 1:
            problems.append("%s cites %d pages and a district cites its board page alone"
                            % (where, len(sources)))
        for key, url in sources.items():
            if not (isinstance(url, str) and url.startswith("https://")):
                problems.append("%s: page %s is not an https address" % (where, key))
        seats = d.get("seats") or []
        if len(seats) != SEATS.get(geoid):
            problems.append("%s has %d members in the seats file and the builder states %s"
                            % (where, len(seats), SEATS.get(geoid)))
        names = set()
        for s in seats:
            odd = set(s) - SEAT_KEYS
            if odd:
                problems.append("%s: a seat carries keys this builder does not read: %s"
                                % (where, ", ".join(sorted(odd))))
            for key in ("seat", "name", "from"):
                if not isinstance(s.get(key), str) or not s[key].strip():
                    problems.append("%s: a seat has no %s" % (where, key))
            if "area" in s and (not isinstance(s["area"], str) or not s["area"].strip()):
                problems.append("%s: %s's area is set and empty" % (where, s.get("name")))
            if s.get("from") not in sources:
                problems.append("%s: %s cites page %r, which the district does not list"
                                % (where, s.get("name"), s.get("from")))
            if s.get("name") in names:
                problems.append("%s names %s twice" % (where, s.get("name")))
            names.add(s.get("name"))
    return problems


def check_census(districts):
    """Every Tennessee school district the Census names as special, and
    Gibson County's, is in the seats file under the Census's own name and
    layer. Read at build time only: TIGERweb is not reachable offline."""
    problems = []
    found = {}
    for layer, number in sorted(TIGER_LAYERS.items()):
        _final, body = cc.get(SPEC, TIGER_QUERY % number, {"User-Agent": UA})
        doc = json.loads(body.decode("utf-8"))
        if "error" in doc or not doc.get("features"):
            raise SystemExit("%s: FATAL: TIGERweb answered %s for the %s layer"
                             % (SPEC.label, json.dumps(doc.get("error"))[:200], layer))
        for f in doc["features"]:
            a = f.get("attributes") or {}
            if "Special" in str(a.get("NAME")) or a.get("GEOID") in NOT_NAMED_SPECIAL:
                found[a["GEOID"]] = (a["NAME"], layer)
    for geoid in sorted(set(found) - set(districts)):
        problems.append("the Census draws %s (%s) and the seats file does not name its board"
                        % (found[geoid][0], geoid))
    for geoid in sorted(set(districts) - set(found)):
        problems.append("the seats file names %s, which the Census does not draw as a special "
                        "school district" % geoid)
    for geoid in sorted(set(found) & set(districts)):
        name, layer = found[geoid]
        d = districts[geoid]
        if (d.get("census"), d.get("layer")) != (name, layer):
            problems.append("%s: the Census names it %r in its %s layer, and the seats file "
                            "says %r in %s" % (geoid, name, layer, d.get("census"), d.get("layer")))
    return problems


def app_doc(districts, pages):
    out = {}
    for geoid, d in sorted(districts.items()):
        url = d["sources"]["board"]
        entry = {"name": d["name"], "layer": d["layer"], "body": d["body"], "how": d["how"],
                 "page": url, "read": pages[url]["read"], "seats": []}
        for key in ("note", "ownName"):
            if d.get(key):
                entry[key] = d[key]
        for s in d["seats"]:
            seat = {"name": s["name"],
                    "role": "Board member" if s["seat"] == "Member" else s["seat"]}
            for key in ("area", "email", "phone", "phonesExtra"):
                if key in s:
                    seat[key] = s[key]
            entry["seats"].append(seat)
        out[geoid] = entry
    return out


def report(problems, mode):
    for p in problems:
        print("%s %s: FAIL: %s" % (SPEC.label, mode, p))
    if problems:
        raise SystemExit(1)


def run_check():
    districts = load()
    report(cc.contacts_selftest() + check_districts(districts)
           + cc.check_contacts(SPEC, districts), "--check")
    pages = cc.load_record(SPEC)
    report(cc.check_record(SPEC, districts, pages), "--check")
    with open(SPEC.out_path, encoding="utf-8") as fh:
        shipped = fh.read()
    if shipped != cc.dumps(app_doc(districts, pages)):
        report(["%s is not what the seats file and the record produce; run the build rather "
                "than editing it by hand" % os.path.relpath(SPEC.out_path, REPO_ROOT)], "--check")
    seats = sum(len(d["seats"]) for d in districts.values())
    print("%s --check: OK — %d special school districts, %d members, every name and contact "
          "found on the page it cites (%s; pages read %s to %s)"
          % (SPEC.label, len(districts), seats, cc.contacts_said(districts),
             min(e["read"] for e in pages.values()), max(e["read"] for e in pages.values())))


def run_watch():
    districts = load()
    report(check_districts(districts) + cc.check_contacts(SPEC, districts), "--watch")
    prior = cc.load_record(SPEC)
    pages, problems, _carried = cc.read_all(SPEC, districts, prior)
    if problems:
        for kind, url, msg in problems:
            print("%s --watch: %s: %s" % (SPEC.label, cc.WATCH_WORDS[kind], msg))
        print("%s --watch: re-read the pages above and update the seats file; a name that has "
              "gone from its page usually means the seat changed hands" % SPEC.label)
        raise SystemExit(1)
    print("%s --watch: every name and contact is still on the page it cites (%d pages read)"
          % (SPEC.label, len(pages)))


def run_build():
    districts = load()
    report(check_districts(districts) + cc.check_contacts(SPEC, districts), "build")
    report(check_census(districts), "build")
    prior = cc.load_record(SPEC)
    pages, problems, carried = cc.read_all(SPEC, districts, prior)
    hard = [msg for kind, url, msg in problems if kind in ("missing", "contact", "refused")]
    hard += ["%s could not be read and has never been read: %s" % (url, msg)
             for kind, url, msg in problems if kind == "unread" and url not in carried]
    report(hard, "build")
    for url in carried:
        print("%s: NOT READ %s; keeping what it said on %s, the last time it was read"
              % (SPEC.label, url, pages[url]["read"]))
    report(cc.check_record(SPEC, districts, pages), "build")
    with open(SPEC.record_path, "w", encoding="utf-8") as fh:
        fh.write(cc.dumps(cc.record_doc(pages)))
    with open(SPEC.out_path, "w", encoding="utf-8") as fh:
        fh.write(cc.dumps(app_doc(districts, pages)))
    print("wrote %s: %d special school districts, %d members (%s)"
          % (os.path.relpath(SPEC.out_path, REPO_ROOT), len(districts),
             sum(len(d["seats"]) for d in districts.values()), cc.contacts_said(districts)))


if __name__ == "__main__":
    if "--check" in sys.argv[1:]:
        run_check()
    elif "--watch" in sys.argv[1:]:
        run_watch()
    else:
        run_build()
