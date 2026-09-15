#!/usr/bin/env python3
"""
The deterministic half of a roster PR review, printed as a verdict block.

Run in a worktree that has the PR's head with origin/main merged in. It finds
every data/app JSON file that differs from the base ref and, for each one,
compares the two versions the way docs/MANAGER.md says a roster is compared:

  * both sides flattened to SCALAR LEAVES and diffed as multisets, because a
    line diff cannot tell a reorder from a substitution (#824: 217 identical
    leaf values) and a top-level comparison reports a renamed key one level
    down as a difference (#875);
  * per-field coverage counts on both sides, the retention gate's question
    asked per file;
  * names added, removed, and MOVED between fields, because a name swap reads
    as a field loss to a coverage count (#829);
  * "values only in base", which must be empty for the clean shape;
  * PERMUTATION within a field where the totals are unmoved, the signature of
    thirteen judges each carrying a colleague's phone (#837);
  * an honorific in a file that otherwise carries none;
  * an apartment, unit or suite marker in an office address, because a home
    address never ships;
  * a unit code claimed by two cards in one county;
  * whether the only moved value is a `generated` stamp, said on one line,
    because nine Illinois files carry one and open a PR every week on it.

It exits 1 on any finding, 0 on a clean or stamp-only diff, 2 on a usage
error. What it deliberately does not do is judge: driving a new guard branch
with doctored input, tracing whether a fetch policy can fail open, checking
what a PR says it did NOT do, and checking a drafted ask against the card are
the manager's, and docs/MANAGER.md lists them.

Usage:
    python3 scripts/review_roster_pr.py [PR-NUMBER] [--base origin/main]
    python3 scripts/review_roster_pr.py --selftest

PR-NUMBER is a label for the header line only. The shell this runs in has no
GitHub access, so the script never fetches a PR; the caller makes the worktree.
Stdlib only.
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Keys whose value is a person's (or, for a provider roster, an organisation's)
# identity. A value under one of these that appears on both sides under a
# different key path is a name MOVED, not a name lost.
NAME_KEYS = {
    "name", "displayname", "display_name", "fullname", "full_name", "member",
    "chair", "official", "officeholder", "supervisor", "commissioner",
    "alderman", "alderperson", "mayor", "clerk", "judge", "provider", "agency",
    "president", "trustee",
}
# Keys whose value is an office location. A residential marker here is the
# home-address rule being broken.
ADDRESS_KEY_RE = re.compile(r"(address|office|street)", re.I)
RESIDENTIAL_RE = re.compile(r"\b(apt\.?|apartment|unit)\s*#?\s*\w|\bsuite\b|\bste\.?\s*\w", re.I)
HONORIFIC_RE = re.compile(r"^(Mr|Mrs|Ms|Miss|Dr|Hon|Rev|Sen|Rep)\.?\s+", re.I)
# Keys that identify a seat inside a county. Two records in one county
# claiming the same one is two cards for one seat.
UNIT_KEYS = ("district", "unit", "seat", "ward")
COUNTY_KEYS = ("county", "countyName", "county_name", "countyFips", "county_fips")
STAMP_KEY = "generated"


def leaves(obj, path=""):
    """Yield (path, scalar) for every scalar under obj; lists index by [n]."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            for item in leaves(v, path + "/" + str(k)):
                yield item
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            for item in leaves(v, path + "[" + str(i) + "]"):
                yield item
    else:
        yield path, obj


def field_of(path):
    """The last key segment of a leaf path, list indices stripped."""
    seg = path.rsplit("/", 1)[-1]
    return re.sub(r"\[\d+\]$", "", seg)


def record_of(path):
    """The path of the record a leaf sits in: everything but its last key."""
    return path.rsplit("/", 1)[0]


def coverage(leafmap):
    """field -> number of leaves carrying a non-empty value."""
    out = collections.Counter()
    for p, v in leafmap.items():
        if v not in (None, "", [], {}):
            out[field_of(p)] += 1
    return out


def records(obj, path="", county=None):
    """Yield (path, dict, county) for every dict that carries at least one
    scalar. `county` is inherited from the nearest ancestor that names one,
    because a district record sits inside its county's block and rarely
    repeats the county on itself."""
    if isinstance(obj, dict):
        here = next((obj[k] for k in COUNTY_KEYS if k in obj and obj[k] not in (None, "")), county)
        if any(not isinstance(v, (dict, list)) for v in obj.values()):
            yield path, obj, here
        for k, v in obj.items():
            for item in records(v, path + "/" + str(k), here):
                yield item
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            for item in records(v, path + "[" + str(i) + "]", county):
                yield item


def identity_of(rec, path):
    """What a record is keyed by for the permutation test: its name when it
    carries one, else its path. A reorder moves paths and keeps names, so a
    name-keyed comparison sees a reorder as nothing and a phone handed to a
    colleague as a change."""
    for k, v in rec.items():
        if k.lower() in NAME_KEYS and isinstance(v, str) and v:
            return "name:" + v
    return "path:" + path


def is_roster(obj, path):
    """False for the data/app files that are not rosters and would only
    produce noise here: geometry, and the generated gap panel."""
    base = os.path.basename(path)
    if base == "coverage-gaps.json" or "outline" in base:
        return False
    if isinstance(obj, dict) and obj.get("type") == "FeatureCollection":
        return False
    return True


def review_pair(label, base, head):
    """Compare two parsed JSON documents. Returns (findings, notes).

    findings: list of strings, each a defect signature that fails the review.
    notes: list of strings worth printing that do not fail it.
    """
    findings, notes = [], []
    lb = dict(leaves(base))
    lh = dict(leaves(head))

    # ---- stamp-only: the AFR-route shape, said on one line and nothing else
    changed = {p for p in set(lb) | set(lh) if lb.get(p, _MISSING) != lh.get(p, _MISSING)}
    if changed and all(field_of(p) == STAMP_KEY for p in changed):
        notes.append("%s: stamp-only — the only moved value is `%s` (%r -> %r); "
                     "no record, name or field changed"
                     % (label, STAMP_KEY, lb.get("/" + STAMP_KEY), lh.get("/" + STAMP_KEY)))
        return findings, notes
    if not changed:
        notes.append("%s: identical" % label)
        return findings, notes

    # ---- leaf multisets
    mb = collections.Counter(_hashable(v) for v in lb.values())
    mh = collections.Counter(_hashable(v) for v in lh.values())
    only_base = mb - mh
    only_head = mh - mb
    notes.append("%s: leaves base %d, head %d; values only in base %d, only in head %d; "
                 "paths changed %d" % (label, len(lb), len(lh), sum(only_base.values()),
                                       sum(only_head.values()), len(changed)))
    if only_base:
        sample = ", ".join(repr(v) for v, _ in only_base.most_common(6))
        findings.append("%s: %d value(s) present in base and absent from head: %s%s"
                        % (label, sum(only_base.values()), sample,
                           " …" if len(only_base) > 6 else ""))
    if not only_base and not only_head and changed:
        notes.append("%s: every value survives; %d path(s) changed — a rename or a reorder, "
                     "not a loss" % (label, len(changed)))

    # ---- per-field coverage
    cb, ch = coverage(lb), coverage(lh)
    for f in sorted(set(cb) | set(ch)):
        b, h = cb.get(f, 0), ch.get(f, 0)
        if b and not h:
            findings.append("%s: field `%s` vanished — on %d record(s) in base, none in head" % (label, f, b))
        elif b and h < b and (b - h) >= 3 and h * 2 <= b:
            findings.append("%s: field `%s` lost most of its records — %d -> %d" % (label, f, b, h))
        elif b != h:
            notes.append("%s: field `%s` coverage %d -> %d" % (label, f, b, h))

    # ---- names: added, removed, moved between fields
    nb = {p: v for p, v in lb.items() if field_of(p).lower() in NAME_KEYS and isinstance(v, str)}
    nh = {p: v for p, v in lh.items() if field_of(p).lower() in NAME_KEYS and isinstance(v, str)}
    vb, vh = collections.Counter(nb.values()), collections.Counter(nh.values())
    removed, added = vb - vh, vh - vb
    fields_by_name_b = collections.defaultdict(set)
    fields_by_name_h = collections.defaultdict(set)
    for p, v in nb.items():
        fields_by_name_b[v].add(field_of(p))
    for p, v in nh.items():
        fields_by_name_h[v].add(field_of(p))
    moved = sorted(v for v in vb if v in vh and fields_by_name_b[v] != fields_by_name_h[v])
    if removed:
        findings.append("%s: %d name(s) removed: %s" % (label, sum(removed.values()),
                                                       ", ".join(sorted(removed))))
    if added:
        notes.append("%s: %d name(s) added: %s" % (label, sum(added.values()),
                                                  ", ".join(sorted(added))))
    if moved:
        findings.append("%s: %d name(s) moved between fields: %s" % (label, len(moved), ", ".join(
            "%s (%s -> %s)" % (v, "/".join(sorted(fields_by_name_b[v])),
                               "/".join(sorted(fields_by_name_h[v]))) for v in moved)))
    if not removed and not added and not moved:
        notes.append("%s: zero name changes" % label)

    # ---- permutation within a field, totals unmoved. Records are keyed by
    # their name rather than their path, so a reorder is not a permutation.
    by_field_b = collections.defaultdict(dict)
    by_field_h = collections.defaultdict(dict)
    for p, rec, _ in records(base):
        ident = identity_of(rec, p)
        for k, v in rec.items():
            if not isinstance(v, (dict, list)) and k.lower() not in NAME_KEYS:
                by_field_b[k][ident] = v
    for p, rec, _ in records(head):
        ident = identity_of(rec, p)
        for k, v in rec.items():
            if not isinstance(v, (dict, list)) and k.lower() not in NAME_KEYS:
                by_field_h[k][ident] = v
    for f in sorted(set(by_field_b) & set(by_field_h)):
        fb, fh = by_field_b[f], by_field_h[f]
        if collections.Counter(map(_hashable, fb.values())) != collections.Counter(map(_hashable, fh.values())):
            continue  # totals moved; a real change, reported elsewhere
        shared = [i for i in fb if i in fh and fb[i] != fh[i]]
        distinct = len(set(map(_hashable, fb.values())))
        if len(shared) >= 2 and distinct > 1:
            findings.append("%s: field `%s` permuted — the same %d value(s) reassigned across %d "
                            "record(s) with every total unmoved (e.g. %s: %r -> %r)"
                            % (label, f, distinct, len(shared), shared[0], fb[shared[0]], fh[shared[0]]))

    # ---- honorific in a file that otherwise has none
    hon_h = [(p, v) for p, v in nh.items() if HONORIFIC_RE.match(v.strip())]
    hon_b = [(p, v) for p, v in nb.items() if HONORIFIC_RE.match(v.strip())]
    if hon_h and len(hon_h) <= max(2, len(nh) // 20):
        new = [x for x in hon_h if x[1] not in {v for _, v in hon_b}]
        if new:
            findings.append("%s: honorific in a file that otherwise carries none: %s"
                            % (label, ", ".join("%s=%r" % x for x in new[:4])))

    # ---- residential marker in an office address, on values new in head
    res = []
    for p, v in lh.items():
        if isinstance(v, str) and ADDRESS_KEY_RE.search(field_of(p)) and RESIDENTIAL_RE.search(v):
            if lb.get(p) != v:
                res.append((p, v))
    if res:
        findings.append("%s: apartment/unit/suite marker in %d office address(es) new in head: %s"
                        % (label, len(res), "; ".join("%s=%r" % x for x in res[:4])))

    # ---- unit code claimed twice in one county
    dup_h = _duplicate_units(head)
    dup_b = _duplicate_units(base)
    new_dups = sorted(set(dup_h) - set(dup_b))
    if new_dups:
        findings.append("%s: unit code claimed by two cards in one county: %s"
                        % (label, ", ".join("%s/%s" % d for d in new_dups[:6])))
    return findings, notes


def _duplicate_units(obj):
    seen = collections.Counter()
    for _, rec, county in records(obj):
        unit = next((rec[k] for k in UNIT_KEYS if k in rec and rec[k] not in (None, "")), None)
        if county is None or unit is None:
            continue
        seen[(str(county), str(unit))] += 1
    return [k for k, n in seen.items() if n > 1]


_MISSING = object()


def _hashable(v):
    return json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v


# ---------------------------------------------------------------- git side

def changed_data_files(base):
    out = subprocess.check_output(["git", "diff", "--name-only", base, "--"],
                                  cwd=REPO_ROOT, text=True)
    return sorted(p for p in out.split() if "/data/app/" in p and p.endswith(".json"))


def read_base(base, path):
    try:
        raw = subprocess.check_output(["git", "show", "%s:%s" % (base, path)],
                                      cwd=REPO_ROOT, text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return None
    return json.loads(raw)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pr", nargs="?", help="PR number, used only to label the report")
    ap.add_argument("--base", default="origin/main", help="ref to compare the worktree against")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    files = changed_data_files(args.base)
    head_label = "PR #%s" % args.pr if args.pr else "working tree"
    print("review_roster_pr: %s against %s — %d data/app file(s) differ" % (head_label, args.base, len(files)))
    if not files:
        print("  nothing to review")
        return 0
    all_findings = []
    for path in files:
        base = read_base(args.base, path)
        try:
            with open(os.path.join(REPO_ROOT, path), encoding="utf-8") as fh:
                head = json.load(fh)
        except FileNotFoundError:
            print("  %s: DELETED in head" % path)
            all_findings.append("%s deleted" % path)
            continue
        if base is None:
            n = sum(1 for _ in leaves(head))
            print("  %s: NEW file, %d leaves — nothing to compare; review the builder's floors" % (path, n))
            continue
        if not is_roster(head, path):
            print("  note  %s: not a roster (geometry or the gap panel) — changed, not compared here" % path)
            continue
        findings, notes = review_pair(path, base, head)
        for line in notes:
            print("  note  " + line)
        for line in findings:
            print("  FIND  " + line)
        all_findings.extend(findings)
    if all_findings:
        print("review_roster_pr: %d finding(s) — read each before merging" % len(all_findings))
        return 1
    print("review_roster_pr: OK — no defect signature in %d file(s)" % len(files))
    return 0


# ---------------------------------------------------------------- selftest

def selftest():
    """Every check witnessed failing on a doctored input, and the clean shapes
    witnessed passing. A check that has never failed has not been tested."""
    roster = {
        "generated": "2026-09-13T22:00:00Z",
        "17001": {"county": "Adams", "members": [
            {"district": "1", "name": "Ann Aldridge", "phone": "217-555-0101"},
            {"district": "2", "name": "Bob Baxter", "phone": "217-555-0102"},
            {"district": "3", "name": "Cara Cole", "phone": "217-555-0103"}]},
        "17003": {"county": "Alexander", "members": [
            {"district": "1", "name": "Dan Dodd", "phone": "618-555-0201"},
            {"district": "2", "name": "Eve Evans", "phone": "618-555-0202"}]},
    }
    cases = []

    def case(name, mutate, expect_fail, must_mention=None):
        head = json.loads(json.dumps(roster))
        mutate(head)
        findings, notes = review_pair("t", roster, head)
        ok = bool(findings) == expect_fail
        text = " ".join(findings + notes)
        if ok and must_mention:
            ok = must_mention in text
        cases.append((name, ok, findings, notes))

    case("stamp-only passes and is said on one line",
         lambda h: h.__setitem__("generated", "2026-09-20T22:00:00Z"), False, "stamp-only")
    case("identical passes", lambda h: None, False, "identical")
    case("a reorder within a list passes with every value surviving",
         lambda h: h["17001"]["members"].reverse(), False, "every value survives")
    case("a renamed key one level down passes as a rename, not a loss",
         lambda h: h["17001"].__setitem__("board", h["17001"].pop("members")), False, "rename or a reorder")
    case("a name added passes and is named",
         lambda h: h["17003"]["members"].append({"district": "3", "name": "Fay Frost", "phone": "618-555-0203"}),
         False, "Fay Frost")
    case("a value only in base fails",
         lambda h: h["17001"]["members"][1].__setitem__("phone", "217-555-9999"), True, "only in base")
    case("a name removed fails",
         lambda h: h["17001"]["members"].pop(2), True, "Cara Cole")
    case("a name moved to another field fails",
         lambda h: (h["17001"]["members"][0].__setitem__("chair", h["17001"]["members"][0].pop("name"))),
         True, "moved between fields")
    case("phones permuted with totals unmoved fails",
         lambda h: (h["17001"]["members"][0].__setitem__("phone", "217-555-0102"),
                    h["17001"]["members"][1].__setitem__("phone", "217-555-0101")),
         True, "permuted")
    case("a field vanishing fails",
         lambda h: [m.pop("phone") for c in ("17001", "17003") for m in h[c]["members"]], True, "vanished")
    case("an honorific in a file with none fails",
         lambda h: h["17003"]["members"][0].__setitem__("name", "Mr. Dan Dodd"), True, "honorific")
    case("a suite marker in a new office address fails",
         lambda h: h["17001"]["members"][0].__setitem__("officeAddress", "12 Main St, Apt 4B, Quincy"),
         True, "apartment/unit/suite")
    case("a unit code claimed twice in one county fails",
         lambda h: h["17001"]["members"].append({"district": "2", "name": "Gus Gale", "phone": "217-555-0104"}),
         True, "claimed by two cards")

    failed = [c for c in cases if not c[1]]
    for name, ok, findings, notes in cases:
        print("  %s  %s" % ("ok  " if ok else "FAIL", name))
        if not ok:
            for line in findings:
                print("        finding: " + line)
            for line in notes:
                print("        note: " + line)
    print("review_roster_pr selftest: %d case(s), %d failure(s)" % (len(cases), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
