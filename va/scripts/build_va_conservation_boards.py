#!/usr/bin/env python3
"""
Build va/data/app/va-conservation-boards.json: which of Virginia's 47 soil and
water conservation districts covers each county and city, and the directors
its voters elected, for the County or City card.

    python3 va/scripts/build_va_conservation_boards.py                # read, compose, write
    python3 va/scripts/build_va_conservation_boards.py --source F     # compose from a kept fetch
    python3 va/scripts/build_va_conservation_boards.py --check        # offline

WHY THESE BOARDS. A soil and water conservation district is a political
subdivision of the Commonwealth (Code of Virginia section 10.1-538), and most
of its board is elected. Each district is made of whole counties and cities,
so the County or City card names it without a drawn layer, as Kentucky's and
the Carolinas' cards do; the plan for Virginia (Adam's answers of 22 October
2026, "all three as recommended") puts it there.

TWO SOURCES, BOTH THE STATE'S OWN.
  * Which localities each district covers: the Department of Conservation and
    Recreation's list of the 47 districts (LIST_URL). The builder refuses to
    write unless it finds 47 districts, every county and city it names is one
    of the state's 133 (state-counties.json) or is recorded in LIST_STALE, and
    no locality sits in two. The list's telephone numbers are not read.
  * Who the voters elected: the Department of Elections' results of every
    "Soil and Water Conservation Director" contest since FIRST_YEAR, read
    through the same reader as the local officials builder
    (build_va_local_officials.fetch). Directors are elected at the November
    general election every fourth year from 2003 (section 10.1-530 B), so the
    contests fall in 2015, 2019 and 2023; each names its district and its
    county or city ("Thomas Jefferson (Albemarle County)"), or the district
    alone where the district is one county ("Halifax"). The district a result
    names must be the district the list puts that locality in, or the build
    fails.

HOW MANY ARE ELECTED (section 10.1-515): three from a district that is one
county or city, and two from each county or city of a district that has more
than one; the Virginia Soil and Water Conservation Board appoints two more,
one of them the local extension agent (section 10.1-529). A vacancy in any
seat is filled by the Board's appointment for the rest of the term (section
10.1-530 C), and no list read here names an appointee, so the card names the
elected directors only and says so. A result whose winners are fewer than the
seats the law gives (seven localities in 2023, where the results list one
seat) ships as `listed` below `seats`, and the card says the other seat is
not named.

WHICH ELECTION. A locality's names are the winners of its latest November
election whose term has begun: terms begin on 1 January after the election
(section 10.1-530 B). Winners of a later election ship as `pending` until
then. A result the builder cannot read for a winner (a tie at the last seat)
ships as `unsettled` and names no one.

NOTHING HERE IS A CONTACT. The file carries names, election dates and contest
numbers; the build and --check refuse any value with an "@" or a telephone
number's shape, the shared conservation boards module's test.

`--check` is offline: the file is written as the build writes it, it names
all 133 counties and cities, each district's localities agree with the
entries that point to it, no locality has more names than seats, the record
holds the list's and the results' hashes, and the County or City card in
va/index.html still says what CARD_CLAIMS says it must.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "scripts"))

import va_localities as vl  # noqa: E402
import build_va_local_officials as lo  # noqa: E402

LABEL = "build_va_conservation_boards"
LIST_URL = "https://www.dcr.virginia.gov/soil-and-water/swcdlist"
OFFICE = "553"          # the results' "Soil and Water Conservation Director"
DISTRICTS = 47          # the list's own count, read 2026-10-30
OUT = os.path.join(vl.DATA, "va-conservation-boards.json")
RECORD = os.path.join(vl.INSTANCE, "data", "source", "va-conservation-boards.record.json")
INDEX_HTML = os.path.join(vl.INSTANCE, "index.html")
CONTACT_RE = re.compile(r"@|\(?\b\d{3}\)?[ .-]\d{3}[.-]\d{4}\b")

# Entries in the list that are not a county or city today, each with why.
LIST_STALE = {
    "Bedford (City)": "Bedford became a town in Bedford County on 1 July 2013, so "
                      "it is in the Peaks of Otter district through the county",
}
# Localities the results name that are not a county or city today.
RESULTS_FORMER = {"Bedford City"}

# Sentences the County or City card must keep, so it cannot come to say
# something about how these boards are chosen that this builder does not.
CARD_CLAIMS = (
    "two directors are elected by the voters of each county and city in the district",
    "three directors are elected by the voters of the district",
    "two more are appointed by the Virginia Soil and Water Conservation Board",
    "A seat that falls vacant is filled by the Board's appointment",
)


def fail(msg):
    raise SystemExit("%s: FATAL: %s" % (LABEL, msg))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dumps(doc):
    return json.dumps(doc, indent=1, ensure_ascii=False) + "\n"


def name_key(name):
    """Compare locality names without case, spacing or "&" against "and"."""
    return re.sub(r"[^a-z]", "", name.replace("&", " and ").casefold())


def load_localities():
    """{GEOID: the Census's NAME ("Albemarle County", "Richmond city")}."""
    with open(vl.COUNTIES, encoding="utf-8") as fh:
        feats = json.load(fh)["features"]
    return {f["properties"]["GEOID"]: f["properties"]["NAME"] for f in feats}


# ---------- the Department of Conservation and Recreation's list ----------
def fetch_list(today):
    import requests  # noqa: PLC0415
    from scraper_common import require_robots_once  # noqa: PLC0415

    require_robots_once(LIST_URL, lo.USER_AGENT, label=LABEL)
    r = requests.get(LIST_URL, headers={"User-Agent": lo.USER_AGENT}, timeout=60,
                     allow_redirects=False)
    if r.status_code != 200:
        fail("the list at %s answered HTTP %d" % (LIST_URL, r.status_code))
    return {"read": today.isoformat(), "url": LIST_URL, "html": r.text}


def parse_list(page, localities):
    """{district name: [GEOID, ...]} from the list's table, whose rows are a
    number, the district's name (with its cities in brackets and its office
    telephone, neither read) and its localities separated by semicolons."""
    import html as htmllib  # noqa: PLC0415

    by_key = {name_key(n): g for g, n in localities.items()}
    out, seen = {}, {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        cells = [" ".join(htmllib.unescape(re.sub(r"<[^>]+>", " ", c)).split())
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if len(cells) < 3 or not re.fullmatch(r"\d\d", cells[0]):
            continue
        name = re.split(r"\s*[:;(|]|\s+\(?\d{3}\)", cells[1])[0].strip()
        if not name or re.search(r"\d", name):
            fail("a row of the list has no district name: %r" % cells[1])
        if name in out:
            fail("the list names the %s district twice" % name)
        geoids = []
        for part in cells[2].split(";"):
            part = part.strip()
            if not part:
                continue
            if part in LIST_STALE:
                continue
            m = re.fullmatch(r"(.+?) \(City\)", part)
            full = (m.group(1) + " city") if m else (part + " County")
            g = by_key.get(name_key(full))
            if not g:
                fail("the list puts %r in the %s district, and it is not one of the state's "
                     "counties and cities" % (part, name))
            if g in seen:
                fail("the list puts %s in both the %s and the %s district"
                     % (localities[g], seen[g], name))
            seen[g] = name
            geoids.append(g)
        if not geoids:
            fail("the list's %s district covers no county or city" % name)
        out[name] = sorted(geoids)
    if len(out) != DISTRICTS:
        fail("the list gave %d districts and the builder states %d" % (len(out), DISTRICTS))
    return out


# ---------- the election results ----------
def took_office(date):
    """Terms begin on 1 January after the November election (10.1-530 B)."""
    return datetime.date(date.year + 1, 1, 1)


def read_results(source, districts, localities):
    """{GEOID: [contest, ...]}: every director contest, matched to its locality
    and checked against the district the list puts that locality in."""
    by_key = {name_key(n): g for g, n in localities.items()}
    district_of = {g: d for d, gs in districts.items() for g in gs}
    single = {d.casefold(): gs[0] for d, gs in districts.items() if len(gs) == 1}
    out = {}
    for c in source["contests"].values():
        if (c.get("office") or {}).get("id") != OFFICE:
            continue
        if "primary" in (c.get("eventTypeDisplayName") or "").lower():
            continue
        div = " ".join(((c.get("division") or {}).get("name") or "").split())
        m = re.fullmatch(r"(.+?) \((.+)\)", div)
        if m:
            dist, loc = m.group(1), m.group(2)
            if loc in RESULTS_FORMER:
                continue
            g = by_key.get(name_key(re.sub(r" City$", " city", loc)))
            if not g:
                fail("contest %s names %r, which is not one of the state's counties and cities"
                     % (c["id"], loc))
        else:
            dist, g = div, single.get(div.casefold())
            if not g:
                fail("contest %s names the %r district alone, which is not a district of one "
                     "county or city on the list" % (c["id"], div))
        if g not in district_of:
            fail("contest %s elects directors from %s, which the list puts in no district"
                 % (c["id"], localities[g]))
        if dist.casefold() != district_of[g].casefold():
            fail("contest %s names the %r district for %s, and the list says %s"
                 % (c["id"], dist, localities[g], district_of[g]))
        names, how = lo.winners(c)
        out.setdefault(g, []).append({
            "contest": c["id"], "date": datetime.date.fromisoformat(c["event"]["startDate"][:10]),
            "special": bool(c.get("isSpecial")), "seats": c.get("nSeats") or 1,
            "winners": names, "how": how,
        })
    return out


def compose(source, listing, today):
    localities = load_localities()
    districts = parse_list(listing["html"], localities)
    results = read_results(source, districts, localities)
    district_of = {g: d for d, gs in districts.items() for g in gs}
    out = {"asOf": today.isoformat(), "listRead": listing["read"], "districts": {},
           "localities": {}}
    for d, gs in sorted(districts.items()):
        out["districts"][d] = {"localities": gs, "elected": 3 if len(gs) == 1 else 2}
    for g in sorted(localities):
        name = localities[g]
        if g not in district_of:
            out["localities"][g] = {"name": name, "district": None}
            continue
        d = district_of[g]
        seats = out["districts"][d]["elected"]
        entry = {"name": name, "district": d, "seats": seats}
        contests = [c for c in results.get(g, []) if not c["special"]]
        if not contests:
            fail("the results hold no director election for %s, in the %s district" % (name, d))
        started = [c for c in contests if took_office(c["date"]) <= today]
        later = [c for c in contests if took_office(c["date"]) > today]
        if not started:
            fail("no director election for %s has a term that has begun" % name)
        last = max(c["date"] for c in started)
        base = [c for c in started if c["date"] == last]
        if len(base) != 1:
            fail("%s has %d director contests on %s; the builder reads one"
                 % (name, len(base), last))
        base = base[0]
        if base["seats"] > seats:
            fail("%s's director election of %s elects %d and the law gives it %d"
                 % (name, last, base["seats"], seats))
        if not base["winners"]:
            entry["unsettled"] = "the result of the election of %s does not say who won (%s)" % (
                lo.vaReadDate(last) if hasattr(lo, "vaReadDate") else last.isoformat(), base["how"])
            entry["members"] = []
        else:
            entry["members"] = [{"name": n, "elected": last.isoformat(), "contest": base["contest"]}
                                for n in base["winners"]]
        if base["seats"] < seats:
            entry["listed"] = base["seats"]
        if later:
            nxt = max(c["date"] for c in later)
            for c in later:
                if c["date"] == nxt and c["winners"]:
                    entry.setdefault("pending", []).extend(
                        {"name": n, "elected": nxt.isoformat(), "contest": c["contest"]}
                        for n in c["winners"])
        out["localities"][g] = entry
    problems = check_doc(out, localities)
    if problems:
        for p in problems:
            print("%s: FAIL: %s" % (LABEL, p), file=sys.stderr)
        raise SystemExit(1)
    return out


# ---------- checks shared by the build and --check ----------
def strings_in(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from strings_in(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings_in(v)


def check_doc(doc, localities):
    problems = []
    locs = doc.get("localities") or {}
    dists = doc.get("districts") or {}
    if set(locs) != set(localities):
        problems.append("the file's counties and cities are not the state's 133: missing %s, "
                        "extra %s" % (sorted(set(localities) - set(locs))[:5],
                                      sorted(set(locs) - set(localities))[:5]))
    if len(dists) != DISTRICTS:
        problems.append("the file has %d districts and the builder states %d"
                        % (len(dists), DISTRICTS))
    for d, info in dists.items():
        gs = info.get("localities") or []
        want = 3 if len(gs) == 1 else 2
        if info.get("elected") != want:
            problems.append("the %s district elects %r and the law gives %d"
                            % (d, info.get("elected"), want))
        for g in gs:
            if (locs.get(g) or {}).get("district") != d:
                problems.append("the %s district lists %s, whose entry names %r"
                                % (d, g, (locs.get(g) or {}).get("district")))
    for g, e in locs.items():
        d = e.get("district")
        if d is None:
            if set(e) != {"name", "district"}:
                problems.append("%s is in no district and carries %s" % (g, sorted(e)))
            continue
        if d not in dists or g not in dists[d].get("localities", []):
            problems.append("%s names the %r district, which does not list it" % (g, d))
            continue
        if e.get("seats") != dists[d]["elected"]:
            problems.append("%s carries %r seats and its district elects %d"
                            % (g, e.get("seats"), dists[d]["elected"]))
        members = e.get("members")
        if not isinstance(members, list):
            problems.append("%s has no members list" % g)
            continue
        if len(members) > e["seats"]:
            problems.append("%s names %d directors for %d seats" % (g, len(members), e["seats"]))
        if "listed" in e and not (isinstance(e["listed"], int) and 0 < e["listed"] < e["seats"]):
            problems.append("%s: listed must be fewer than the seats: %r" % (g, e["listed"]))
        if not members and "unsettled" not in e:
            problems.append("%s names no director and says nothing about why" % g)
        for m in members + (e.get("pending") or []):
            if set(m) - {"name", "elected", "contest"}:
                problems.append("%s: a director carries %s" % (g, sorted(m)))
            n = m.get("name")
            if n is not None and (not isinstance(n, str) or n != lo.spelled(n) or not n
                                  or n.strip().lower() in lo.NOT_CANDIDATES):
                problems.append("%s: %r is not a name as the build writes one" % (g, n))
            if not re.fullmatch(r"\d{4}-11-\d{2}", str(m.get("elected") or "")):
                problems.append("%s: %r was not elected at a November election" % (g, m))
            if not re.fullmatch(r"\d+", str(m.get("contest") or "")):
                problems.append("%s: %r cites no contest" % (g, m))
    for value in strings_in(doc):
        if CONTACT_RE.search(value):
            problems.append("%r looks like a contact detail, which this file never carries" % value)
    return problems


def check():
    localities = load_localities()
    problems = []
    for path in (OUT, RECORD):
        if not os.path.exists(path):
            fail("%s does not exist; run the build" % os.path.relpath(path))
    with open(OUT, encoding="utf-8") as fh:
        raw = fh.read()
    doc = json.loads(raw)
    if raw != dumps(doc):
        problems.append("%s is not written the way the build writes it" % os.path.relpath(OUT))
    with open(RECORD, encoding="utf-8") as fh:
        record = json.load(fh)
    if record.get("shipped_sha256") != sha(raw.encode("utf-8")):
        problems.append("%s is not the file the record says the build wrote; run the build"
                        % os.path.relpath(OUT))
    if record.get("list", {}).get("read") != doc.get("listRead"):
        problems.append("the file says the list was read %s and the record says %s"
                        % (doc.get("listRead"), record.get("list", {}).get("read")))
    problems += check_doc(doc, localities)
    with open(INDEX_HTML, encoding="utf-8") as fh:
        page = fh.read()
    if "data/app/va-conservation-boards.json" not in page:
        problems.append("va/index.html does not read va-conservation-boards.json")
    for claim in CARD_CLAIMS:
        if claim not in page:
            problems.append("the County or City card no longer says %r, which this builder "
                            "says it must" % claim)
    if problems:
        for p in problems[:40]:
            print("%s --check: FAIL: %s" % (LABEL, p), file=sys.stderr)
        raise SystemExit(1)
    locs = doc["localities"]
    inside = [e for e in locs.values() if e["district"]]
    named = sum(len(e["members"]) for e in inside)
    seats = sum(e["seats"] for e in inside)
    print("%s --check: OK — %d districts covering %d counties and cities (%d in none), "
          "%d of %d elected seats named, list read %s, composed as of %s"
          % (LABEL, len(doc["districts"]), len(inside), len(locs) - len(inside), named, seats,
             doc["listRead"], doc["asOf"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--source", help="compose from a kept fetch of the results")
    ap.add_argument("--save-source")
    ap.add_argument("--list-source", help="compose from a kept read of the list")
    ap.add_argument("--today", help="compose as of this date (YYYY-MM-DD)")
    args = ap.parse_args()
    if args.check:
        check()
        return
    today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()
    if args.list_source:
        with open(args.list_source, encoding="utf-8") as fh:
            listing = json.load(fh)
    else:
        listing = fetch_list(today)
    if args.source:
        with open(args.source, encoding="utf-8") as fh:
            source = json.load(fh)
    else:
        source = lo.fetch(today, offices=[OFFICE], label=LABEL)
        if args.save_source:
            with open(args.save_source, "w", encoding="utf-8") as fh:
                json.dump(source, fh)
    doc = compose(source, listing, today)
    # A week whose names and districts are unchanged keeps the file and its
    # record as they are, so the weekly job opens no pull request for a date.
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as fh:
            old = json.load(fh)
        if dict(old, asOf=None, listRead=None) == dict(doc, asOf=None, listRead=None):
            print("unchanged since %s; %s left as it is" % (old.get("asOf"), os.path.relpath(OUT)),
                  file=sys.stderr)
            return
    raw = dumps(doc).encode("utf-8")
    with open(OUT, "wb") as fh:
        fh.write(raw)
    contests = {k: v for k, v in source["contests"].items()
                if (v.get("office") or {}).get("id") == OFFICE}
    record = {
        "list": {"url": listing["url"], "read": listing["read"],
                 "sha256": sha(listing["html"].encode("utf-8")), "bytes": len(listing["html"])},
        "results": {"api": lo.API, "office": OFFICE, "fetched": source.get("fetched"),
                    "contests": len(contests),
                    "sha256": sha(json.dumps(contests, sort_keys=True).encode("utf-8"))},
        "asOf": doc["asOf"],
        "shipped_sha256": sha(raw),
    }
    os.makedirs(os.path.dirname(RECORD), exist_ok=True)
    with open(RECORD, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("wrote %s (%d bytes)" % (os.path.relpath(OUT), len(raw)), file=sys.stderr)


if __name__ == "__main__":
    main()
