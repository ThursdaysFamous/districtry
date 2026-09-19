#!/usr/bin/env python3
"""Say what a Detroit council roster refresh actually moved, for the PR that
carries it.

WHY THIS EXISTS
----------------
`update-mi-detroit-council-roster.yml` opened every PR under one title and one
paragraph of body, identical every week, ending "this changes data about real
officeholders. Please review the diff before merging."

Measured 2026-09-19 over every commit that has ever touched
mi/data/app/mi-detroit-council-members.json: three commits, of which the first
is the original build (#746) and the other two are this workflow's refreshes
(#831 and #979). BOTH REFRESHES MOVED `archivedAt` AND NOTHING ELSE. So the
sentence asking a human to review a change to officeholder data has been false
on two of the two refreshes it has ever described, and a reviewer who reads it
and opens the diff finds one line of Wayback timestamp.

That is not a wording problem. A body that cries officeholder every week is how
a reviewer learns to skim the one week it matters.

WHY DETROIT AND NOT THE OTHER FIVE
-----------------------------------
`archivedAt` is a 14-digit Wayback capture timestamp, and it moves whenever the
Internet Archive recaptures the city's council page — which is unrelated to
whether anybody's seat changed. Detroit is the ONLY Michigan roster carrying
such a field, checked 2026-09-19 across all six the instance refreshes weekly
(Grand Rapids, Battle Creek, the county commissioners, congress and both state
chambers carry no fetch stamp at all), because it is the only one with an
Archive fallback: detroitmi.gov usually answers this client with a Cloudflare
managed challenge, which this project never defeats.

That challenge is INTERMITTENT, which this file's own subject proved and four
places in this repo denied. `archivedAt` records WHICH RUNG ANSWERED — null
when detroitmi.gov served directly, a timestamp when the Archive did — and
across the roster's three commits it reads 20260831152830 (2026-09-05,
archive), null (2026-09-09, the direct rung) and 20260912152333 (2026-09-16,
archive). So the stamp moving is not always a recapture, and `rung_change()`
below is what tells the two apart. Nobody saw the 2026-09-09 success for ten
days, because the PR body was the static paragraph this script replaces.

The stamp cannot simply be dropped to make the noise go away. The card prints
which day's copy it used, so it is reader-facing, and the scraper's 45-day
ceiling is enforced against it.

THE GUARD THAT MATTERS
-----------------------
A summary that says "no officeholder changed" is a claim a reviewer acts on by
not reading the diff, so it must never be made about a document this script has
not fully accounted for. The classification below is therefore NOT a list of
fields to look at: `flatten()` reduces both documents to every leaf path, the
two are diffed whole, and every changed path must fall into a known class. Any
path that does not is named in the body under its own heading, and the verdict
stops claiming "only".

So a field added to the roster tomorrow shows up as an unclassified change and
is reported, rather than passing silently under a summary that says nothing
moved but the stamp.

THE TITLE CARRIES THE VERDICT
------------------------------
A bot PR is read from a list before it is opened, so the one line that decides
whether somebody opens it is the title, not the body.

USAGE
------
    python3 mi/scripts/summarize_detroit_roster_change.py --new <path> [--old <path>]
    python3 mi/scripts/summarize_detroit_roster_change.py --new <path> --title
    python3 mi/scripts/summarize_detroit_roster_change.py --selftest

`--old` is the copy on main, which the workflow hands over as
`git show HEAD:mi/data/app/mi-detroit-council-members.json`. Omitting it, or
naming a file that does not exist, is read as "this roster is new".

Stdlib only, no network: the workflow that runs it installs no dependencies,
and scripts/validate_workflow_deps.py holds it to that.
"""
import argparse
import json
import os
import sys

ROSTER = "mi/data/app/mi-detroit-council-members.json"

# Every leaf path a known field can produce, as a (matcher, class) pair. The
# classes are what the body groups by; UNCLASSIFIED is not in this table on
# purpose — it is whatever is left, and being left over is the signal.
PERSON = "person"
STAMP = "stamp"
LINK = "link"
SEAT = "seat"
OFFICE = "office"
SOURCE = "source"


def classify(path):
    """Which class of change a leaf path belongs to, or None if unknown.

    Paths look like /districts/5/name, /citywide/0/profileUrl, /archivedAt,
    /office/lines/1. None means this script does not know what the field is,
    which the caller must report rather than skip.
    """
    parts = path.strip("/").split("/")
    if parts == ["archivedAt"]:
        return STAMP
    if parts == ["sourceUrl"]:
        return SOURCE
    if parts and parts[0] == "office":
        return OFFICE
    if len(parts) == 3 and parts[0] in ("districts", "citywide"):
        return {"name": PERSON, "profileUrl": LINK, "seat": SEAT}.get(parts[2])
    return None


def flatten(doc, prefix=""):
    """Every leaf of a JSON document as (path, value).

    The whole point is that nothing is skipped: a field nobody anticipated
    still produces a path, so the diff below sees it.
    """
    if isinstance(doc, dict):
        for key in sorted(doc):
            for pair in flatten(doc[key], prefix + "/" + str(key)):
                yield pair
    elif isinstance(doc, list):
        for index, item in enumerate(doc):
            for pair in flatten(item, prefix + "/" + str(index)):
                yield pair
    else:
        yield prefix, doc


def changed_paths(old, new):
    """Paths whose value differs, was added, or was removed."""
    a, b = dict(flatten(old)), dict(flatten(new))
    out = []
    for path in sorted(set(a) | set(b)):
        if a.get(path, _MISSING) != b.get(path, _MISSING):
            out.append((path, a.get(path, _MISSING), b.get(path, _MISSING)))
    return out


class _Missing(object):
    def __repr__(self):
        return "<absent>"


_MISSING = _Missing()


def seats(doc):
    """seat label -> name, for the table a reader actually wants.

    Keyed by SEAT rather than by list index: `citywide` is a list, and two
    at-large members swapping places in it is not two people changing. A
    district is keyed by its number because that is what the card shows.
    """
    out = {}
    for number in sorted((doc.get("districts") or {}), key=lambda k: int(k)):
        record = doc["districts"][number] or {}
        out["District %s" % number] = record.get("name")
    for record in (doc.get("citywide") or []):
        record = record or {}
        label = record.get("seat") or "At large"
        out[label] = record.get("name")
    return out


def stamp(value):
    """20260912152333 -> 2026-09-12 15:23:33 UTC. None stays None.

    `archivedAt` is null when the scraper's LIVE rung worked and a Wayback
    timestamp when it had to fall back to the Internet Archive, so None is a
    fact about which rung answered and must never be rendered as the string
    "None" — which is what the first draft did, on the one historical refresh
    it was tested against.
    """
    if value is None:
        return None
    text = str(value)
    if len(text) == 14 and text.isdigit():
        return "%s-%s-%s %s:%s:%s UTC" % (text[0:4], text[4:6], text[6:8],
                                          text[8:10], text[10:12], text[12:14])
    return text


def rung_change(facts):
    """Which rung answered, before and after, when the stamp moved.

    Measured on the real history: PR #979 shows `archivedAt` going from null to
    a timestamp, which is NOT the Archive recapturing a page — it is
    detroitmi.gov having answered the previous run and refused this one. The
    reverse matters more: a timestamp going to null means the city is answering
    this client directly again, which mi/WATCH.md names as the cue to retire
    the archive rung and its EXPECTED_UNREACHABLE entry in
    scripts/validate_card_links.py.
    """
    if STAMP not in facts["by_class"]:
        return None
    was, now = facts["stamp_from"], facts["stamp_to"]
    if was is None and now is not None:
        return "fell-back"
    if was is not None and now is None:
        return "recovered"
    if was is not None and now is not None:
        return "recaptured"
    return None


def summarize(old, new):
    """The facts the title and the body are both built from.

    `unclassified` being non-empty is what stops any caller saying "only".
    """
    diffs = changed_paths(old, new) if old is not None else []
    by_class = {}
    unclassified = []
    for path, was, now in diffs:
        kind = classify(path)
        if kind is None:
            unclassified.append((path, was, now))
        else:
            by_class.setdefault(kind, []).append((path, was, now))

    before, after = (seats(old) if old is not None else {}), seats(new)
    moved = [(label, before.get(label, _MISSING), after[label])
             for label in after if before.get(label, _MISSING) != after[label]]
    gone = [label for label in before if label not in after]
    return {
        "new_roster": old is None,
        "seat_changes": sorted(moved),
        "seats_gone": sorted(gone),
        "by_class": by_class,
        "unclassified": unclassified,
        "stamp_from": stamp(old.get("archivedAt")) if old else None,
        "stamp_to": stamp(new.get("archivedAt")) if new.get("archivedAt") else None,
        "seat_count": len(after),
    }


def title(facts):
    if facts["new_roster"]:
        return "Add the Detroit council roster"
    people = len(facts["seat_changes"]) + len(facts["seats_gone"])
    if people == 1 and not facts["seats_gone"]:
        return ("Update Detroit council roster — %s changed"
                % facts["seat_changes"][0][0])
    if people:
        return "Update Detroit council roster — %d seats changed" % people
    if facts["unclassified"]:
        return "Update Detroit council roster — fields this summary cannot name"
    others = [k for k in facts["by_class"] if k != STAMP]
    if others:
        return "Update Detroit council roster — no officeholder changed"
    rung = rung_change(facts)
    # A rung change outranks the stamp in the title, because one of the two
    # directions is something a human is meant to act on.
    if rung == "recovered":
        return ("Update Detroit council roster — detroitmi.gov answered "
                "directly again; the archive rung may be retirable")
    if rung == "fell-back":
        return ("Update Detroit council roster — read through the Archive "
                "this week, no officeholder changed")
    if rung == "recaptured":
        return ("Update Detroit council roster — snapshot stamp only, "
                "no officeholder changed")
    return "Update Detroit council roster — no change"


# The part of the body that is true every week: where the roster comes from and
# what it deliberately does not carry. It sits BELOW the per-run summary,
# because the run is what a reviewer came to read.
STANDING = """### Where this comes from

Detroit's nine City Council members — seven by district, two at large (2012
charter Art. 4 §4-101). The at-large pair ships beside the district member so
the card does not answer seven ninths of the question and look complete doing
it.

**The city's own council page, read directly when detroitmi.gov answers and
through the Internet Archive when it does not.** The city's Cloudflare
challenge is intermittent, so the scraper tries the direct rung first every
run and the archive rung is the fallback; `archivedAt` records which one
answered, and the card prints which day's copy it used. A snapshot older than
45 days is refused rather than served, so this cannot go stale quietly — the
run fails loudly instead. The challenge itself is never defeated.

No phone or e-mail is carried, because the city publishes none on either
surface (gap `detroit-council-contact`).

Generated by `mi/scripts/mi_detroit_council_scraper.py` into
`mi/scripts/build_mi_detroit_council_roster.py`. This summary is written by
`mi/scripts/summarize_detroit_roster_change.py`, which accounts for every
changed field in the file and names any it cannot classify rather than
reporting a quiet week it did not verify."""


def body(facts):
    out = []
    if facts["new_roster"]:
        out.append("**New roster**: %d seats, none of them previously "
                   "published here." % facts["seat_count"])
        out.append("")
        out.append("Please review every name before merging.")
        out.append("")
        out.append(STANDING)
        return "\n".join(out)

    people = facts["seat_changes"]
    gone = facts["seats_gone"]
    if people or gone:
        out.append("**%d seat%s changed. Please review the names before "
                   "merging.**" % (len(people) + len(gone),
                                   "" if len(people) + len(gone) == 1 else "s"))
        out.append("")
        out.append("| Seat | On `main` | In this PR |")
        out.append("|---|---|---|")
        for label, was, now in people:
            out.append("| %s | %s | %s |"
                       % (label, "*not listed*" if was is _MISSING else was,
                          now if now else "*not listed*"))
        for label in gone:
            out.append("| %s | listed | *no longer present* |" % label)
    elif facts["unclassified"]:
        out.append("**No officeholder changed**, and this summary cannot "
                   "account for every field that did — see below.")
    elif [k for k in facts["by_class"] if k != STAMP]:
        out.append("**No officeholder changed.** All %d seats name the same "
                   "people as the copy on `main`; what moved is listed below."
                   % facts["seat_count"])
    elif STAMP in facts["by_class"]:
        out.append("**No officeholder changed.** All %d seats name the same "
                   "people as the copy on `main`; the only field that moved is "
                   "the one recording where this copy was read."
                   % facts["seat_count"])
    else:
        out.append("**Nothing changed.** The rebuilt roster is identical to "
                   "the copy on `main`.")

    rung = rung_change(facts)
    if rung:
        out.append("")
    if rung == "recaptured":
        out.append("The Internet Archive captured a newer copy of the same "
                   "page: %s → %s." % (facts["stamp_from"], facts["stamp_to"]))
    elif rung == "fell-back":
        out.append("**The rung changed.** The previous run read detroitmi.gov "
                   "directly (`archivedAt` was null); this one could not, and "
                   "fell back to the Internet Archive snapshot of %s. The "
                   "city's Cloudflare challenge is INTERMITTENT rather than "
                   "permanent — measured across this file's own history, the "
                   "direct rung served on 2026-09-09 and not on 2026-09-05 or "
                   "2026-09-16 — so this direction is ordinary and the other "
                   "one is the one to act on." % facts["stamp_to"])
    elif rung == "recovered":
        out.append("**The rung changed, and this one is worth acting on.** "
                   "detroitmi.gov answered this client DIRECTLY this run, "
                   "where the previous one needed the Internet Archive "
                   "(snapshot %s). `mi/WATCH.md` names that as the cue to "
                   "retire the archive hop and its `EXPECTED_UNREACHABLE` "
                   "entry in `scripts/validate_card_links.py`. Confirm it is "
                   "not a one-week fluke before retiring anything."
                   % facts["stamp_from"])

    for kind, heading in ((LINK, "Profile links"), (SEAT, "Seat labels"),
                          (OFFICE, "Council office"), (SOURCE, "Source URL")):
        rows = facts["by_class"].get(kind)
        if not rows:
            continue
        out.append("")
        out.append("**%s**" % heading)
        out.append("")
        for path, was, now in rows:
            out.append("- `%s`: %r → %r" % (path, was, now))

    if facts["unclassified"]:
        out.append("")
        out.append("**Fields this summary does not recognise**")
        out.append("")
        out.append("These changed and are not in any class the summariser "
                   "knows, so read them yourself rather than trusting the "
                   "line above:")
        out.append("")
        for path, was, now in facts["unclassified"]:
            out.append("- `%s`: %r → %r" % (path, was, now))

    out.append("")
    out.append(STANDING)
    return "\n".join(out)


def load(path):
    if not path or not os.path.exists(path) or os.path.getsize(path) == 0:
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


# --------------------------------------------------------------------- tests

BASE = {
    "archivedAt": "20260912152333",
    "sourceUrl": "https://example.invalid/government/city-council",
    "office": {"lines": ["2 Woodward Ave. Suite 1340", "Detroit, MI 48226"],
               "phone": "(313) 224-3443"},
    "districts": {str(n): {"name": "Member %d" % n,
                           "profileUrl": "https://example.invalid/d%d" % n,
                           "seat": "City Council District %d" % n}
                  for n in range(1, 8)},
    "citywide": [{"name": "At Large One",
                  "profileUrl": "https://example.invalid/al1",
                  "seat": "City Council President Pro Tem, At Large"},
                 {"name": "At Large Two",
                  "profileUrl": "https://example.invalid/al2",
                  "seat": "City Council At Large"}],
}


def _copy(**changes):
    doc = json.loads(json.dumps(BASE))
    for path, value in changes.items():
        cursor, parts = doc, path.split(".")
        for part in parts[:-1]:
            cursor = cursor[int(part)] if isinstance(cursor, list) else cursor[part]
        last = parts[-1]
        if isinstance(cursor, list):
            cursor[int(last)] = value
        else:
            cursor[last] = value
    return doc


def selftest():
    failures = []
    ran = []

    def check(ok, label):
        print("  %-4s %s" % ("ok" if ok else "FAIL", label))
        ran.append(label)
        if not ok:
            failures.append(label)

    # 1. The Archive recaptured the same page: stamp moved, nobody did.
    f = summarize(BASE, _copy(archivedAt="20260919041102"))
    check("snapshot stamp only" in title(f), "recapture: the title says so")
    check("No officeholder changed" in body(f), "recapture: the body says so")
    check("2026-09-12 15:23:33 UTC → 2026-09-19 04:11:02 UTC" in body(f),
          "recapture: both capture times are printed, human-readable")
    check(not f["seat_changes"] and not f["unclassified"],
          "recapture: no seat change and nothing unaccounted for")

    # 1b. THE CASE THE REAL HISTORY PRODUCED (PR #979): null -> a timestamp,
    #     which is the live rung failing and the Archive taking over, NOT a
    #     recapture. The first draft called it a recapture and printed the
    #     string "None" as the previous snapshot.
    f = summarize(_copy(archivedAt=None), _copy(archivedAt="20260912152333"))
    check("Archive this week" in title(f),
          "fell back: the title names the rung, not a recapture")
    check("None" not in body(f),
          "fell back: a null previous stamp never renders as the word None")
    check("fell back to the Internet Archive snapshot of "
          "2026-09-12 15:23:33 UTC" in body(f),
          "fell back: the body says which rung answered and when")

    # 1c. The reverse, which mi/WATCH.md says to act on.
    f = summarize(_copy(archivedAt="20260912152333"), _copy(archivedAt=None))
    check("answered directly again" in title(f),
          "recovered: the title leads with the actionable half")
    check("EXPECTED_UNREACHABLE" in body(f)
          and "one-week fluke" in body(f),
          "recovered: the body names the follow-up and warns against haste")

    # 2. One district member changed — the case the old body always claimed.
    f = summarize(BASE, _copy(**{"districts.5.name": "Someone Else"}))
    check(title(f).endswith("District 5 changed"),
          "one seat: the title names the district")
    check("| District 5 | Member 5 | Someone Else |" in body(f),
          "one seat: the table gives both names")
    check("Please review the names before merging" in body(f),
          "one seat: the body asks for the review")

    # 3. An at-large member changed — keyed by seat, not by list position.
    f = summarize(BASE, _copy(**{"citywide.1.name": "New At Large"}))
    check("City Council At Large" in body(f),
          "at large: the seat label identifies the change")
    check(len(f["seat_changes"]) == 1, "at large: exactly one seat moved")

    # 4. Reordering the at-large list is NOT two people changing.
    swapped = json.loads(json.dumps(BASE))
    swapped["citywide"] = [swapped["citywide"][1], swapped["citywide"][0]]
    f = summarize(BASE, swapped)
    check(not f["seat_changes"],
          "at large: swapping the two rows changes nobody")

    # 5. A link moved and nobody did: no false officeholder claim, and the
    #    stamp-only sentence must not be used either.
    f = summarize(BASE, _copy(**{"districts.2.profileUrl":
                                 "https://example.invalid/new-2"}))
    check("no officeholder changed" in title(f)
          and "snapshot stamp only" not in title(f),
          "link only: honest title, and not the stamp sentence")
    check("Profile links" in body(f), "link only: the change is named")

    # 6. A field the summariser does not know must be reported, and must stop
    #    the verdict claiming "only".
    f = summarize(BASE, _copy(termEnds="2029-01-01"))
    check(f["unclassified"], "unknown field: reported as unclassified")
    check("cannot name" in title(f), "unknown field: the title refuses to claim")
    check("does not recognise" in body(f) and "termEnds" in body(f),
          "unknown field: named in the body for a human to read")

    # 7. A new roster, with nothing to compare against.
    f = summarize(None, BASE)
    check(title(f) == "Add the Detroit council roster", "new roster: title")
    check("9 seats" in body(f), "new roster: counts what it is publishing")

    # 8. No change at all.
    f = summarize(BASE, json.loads(json.dumps(BASE)))
    check(title(f).endswith("no change"), "identical: says nothing changed")

    # 9. The standing explanation rides every body.
    check(all(STANDING in body(summarize(BASE, doc))
              for doc in (_copy(archivedAt="20260919041102"),
                          _copy(**{"districts.5.name": "X"}))),
          "every body carries where the roster comes from")

    # 10. The shipped roster's real shape produces no unclassified paths —
    #     i.e. this script is not already out of date with the builder.
    shipped = load(os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), ROSTER))
    if shipped is None:
        check(False, "the shipped roster is readable")
    else:
        unknown = [p for p, _ in flatten(shipped) if classify(p) is None]
        check(not unknown,
              "the shipped roster's fields are all classified (%s)"
              % (", ".join(unknown) or "none unknown"))

    # The count is the number of checks that actually RAN, not a literal: a
    # selftest whose summary line cannot move is one that keeps reporting OK
    # after somebody deletes half of it.
    if failures:
        print("summarize-detroit-roster-change: FAIL — %d of %d checks"
              % (len(failures), len(ran)))
        for label in failures:
            print("  - " + label)
        return 1
    if len(ran) < 15:
        print("summarize-detroit-roster-change: FAIL — only %d checks ran; "
              "this selftest is supposed to cover the stamp-only, seat, "
              "at-large, link, unknown-field, new-roster and identical cases"
              % len(ran))
        return 1
    print("summarize-detroit-roster-change: OK — %d checks, including that "
          "the shipped roster carries no field this summariser cannot name"
          % len(ran))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--old", help="the roster as it stands on main")
    ap.add_argument("--new", help="the rebuilt roster")
    ap.add_argument("--title", action="store_true",
                    help="print the PR title instead of the body")
    ap.add_argument("--selftest", action="store_true",
                    help="run the checks and exit")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.new:
        ap.error("--new is required")

    new = load(args.new)
    if new is None:
        raise SystemExit("summarize-detroit-roster-change: %s is missing or "
                         "empty" % args.new)
    facts = summarize(load(args.old), new)
    sys.stdout.write((title(facts) if args.title else body(facts)) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
