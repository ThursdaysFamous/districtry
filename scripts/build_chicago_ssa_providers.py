#!/usr/bin/env python3
"""Write il/data/app/chicago-ssa-providers.json from the scraped provider list.

The `ssa` card's people row. An SSA elects nobody, so what the card can
honestly name is the SERVICE PROVIDER AGENCY the city contracts with to run
the corridor — the organisation a reader would call about it — with its office
address, telephone and site.

THE JOIN KEY IS THE BARE SSA NUMBER, and that is a measurement rather than a
convenience. Both publishers tag an SSA with the year its current term was
established, and they disagree about where the year goes: the boundary
dataset calls one SSA #17-2025 "CentLakeview/Wrigleyville" where the provider
page calls it SSA #17 "Central Lakeview/Wrigleyville", and it calls another
SSA #29 "West Town-2014" where the page calls it SSA #29-2014 "West Town" —
the same year, moved between the reference and the name, in opposite
directions. Joining on the full reference loses both. Measured 2026-09-12 no
bare number is claimed by two providers and every provider maps to a live
boundary SSA, so the fold is safe.

"THE BUILDER RE-CHECKS BOTH ON EVERY RUN" WAS FALSE UNTIL 2026-09-13, and it is
recorded rather than quietly fixed because the sentence appeared in four places
and read as a gate in all four. Only the duplicate-provider direction ever
gated. check_against_boundaries() said in its own docstring that it never gates,
ran only when a caller passed --boundaries, ran AFTER the write, and the weekly
workflow never passed it at all — so a doctored orphan provider #999 wrote 50
records and exited 0. Now --boundaries is REQUIRED, the check runs before the
write, and all three senses of the claim refuse it: duplicate providers,
duplicate boundary areas, and a provider with no area. Verified by running each
one; every refusal exits 1 and writes nothing.

--check re-reads the shipped file against a build from the sources read just
now and exits non-zero on any difference, writing nothing. It is in no
workflow and the comment above main() says why.

ALL 58 OF THE BOUNDARY FILE'S SSAs GET A PROVIDER as of 2026-09-13, and the
nine that did not were never the city's omission. This file said on 2026-09-12
that "the city's list simply has no entry" for Greek Town (16), Six Corners
(28-2014), 95th/Ashland (69), Roseland (71), Village:Austin (72), Chinatown
(73), Oak Street (75), North Michigan Avenue (76-2024) and West Garfield Park
(77). The city's list has an entry for every one of them. Their headings close
the bold run with a <br /> inside it, which the scraper's heading pattern could
not cross, so those nine blocks were absorbed into the block above and never
parsed — and an absent block reads exactly like an absent provider. The cards,
the gap record, the worksheet note and this docstring all then stated it as a
fact about the city. scripts/chicago_ssa_provider_scraper.py carries it as trap
9 and GATES it: a bolded heading that does not become a block is now a failed
run. #73 needed a second fix, trap 10 — its street number carries a letter.

THE LESSON FOR THE NEXT GAP RECORD: a parser that loses a block cannot tell
you it lost one, so "the source does not publish X" is only ever as good as the
proof that the source was fully read. A count guard is not that proof — 49
records passed every floor here for a day.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from scraper_common import flatten_records  # noqa: E402  (shared machinery — do not fork)

# BOTH PATHS ANCHOR TO HERE, and both live under il/. DEFAULT_RAW pointed at
# the repo root's data/source/ until 2026-09-13 — a directory that does not
# exist and that the scraper never wrote to — so a build with no --raw died on
# a FileNotFoundError, and --scrape would have created a stray root directory
# beside the instance the app actually serves from. The weekly workflow passes
# --raw explicitly, which is why the mismatch never failed a run. That absence
# is now a named refusal rather than a traceback, since a --check is the case
# most likely to be run by hand with nothing saved.
#
# normpath so a refusal or a log line names il/data/app/... rather than
# scripts/../il/..., which is the form a reader can paste back.
DEFAULT_RAW = os.path.normpath(os.path.join(HERE, "..", "il", "data", "source",
                                            "chicago-ssa-providers.raw.json"))
OUT = os.path.normpath(os.path.join(HERE, "..", "il", "data", "app",
                                    "chicago-ssa-providers.json"))

# 58 parse today, one per active SSA. The floor allows a handful of blocks to
# lapse between city edits without a false alarm, and refuses a run that lost a
# third of them. IT IS DELIBERATELY NOT RAISED TO 58: what a floor can catch is
# a scrape that collapsed, and 49 of 58 sailed through this one for a day, so
# raising it would buy a narrower version of a guard that already failed. The
# check that actually holds the count is the heading gate in the scraper, plus
# check_against_boundaries() printing every area with no provider.
MIN_PROVIDERS = 40
# Every shipped record carries all four; a run that drops one has parsed badly.
REQUIRED = ("provider", "address", "phone")


def bare(ref):
    """'17-2025' -> '17'. See the join-key note in the module docstring."""
    return str(ref).split("-")[0]


def build(raw):
    providers = raw.get("providers") or {}
    if len(providers) < MIN_PROVIDERS:
        raise SystemExit("chicago-ssa-providers: only %d provider(s) parsed, floor "
                         "is %d — refusing to build from a scrape this thin, in "
                         "either mode: writing it would replace a good file with "
                         "a bad one, and checking against it would call a good "
                         "file drifted"
                         % (len(providers), MIN_PROVIDERS))

    out, seen = {}, {}
    for ref, rec in sorted(providers.items(), key=lambda kv: int(bare(kv[0]))):
        key = bare(ref)
        if key in seen:
            raise SystemExit("chicago-ssa-providers: SSA #%s and #%s both fold to %s — "
                             "the bare number is no longer a unique join key"
                             % (seen[key], ref, key))
        seen[key] = ref
        missing = [f for f in REQUIRED if not rec.get(f)]
        if missing:
            raise SystemExit("chicago-ssa-providers: SSA #%s is missing %s — the "
                             "provider page's block shape changed"
                             % (ref, ", ".join(missing)))
        row = {"provider": rec["provider"], "address": rec["address"],
               "phone": rec["phone"], "ref": ref}
        if rec.get("url"):
            row["url"] = rec["url"]
        out[key] = row
    return out


def check_against_boundaries(out, path):
    """GATE the bare-number join against the city's own boundary dataset.

    WHAT "ONE-TO-ONE IN BOTH DIRECTIONS" MEANS, because this file, the loader
    comment, the worksheet note and validate_index.py all used to claim it while
    only a third of it was checked. The claim is about the FOLD to the bare
    number being injective on each side, and about every provider landing on a
    real area. Three things, and all three now refuse the write:

      (i)  no two PROVIDERS fold to one bare number — checked in build(), the
           only part that ever gated;
      (ii) no two BOUNDARY features fold to one bare number either, which
           nothing checked: SSA#29 'West Town-2014' and a hypothetical SSA#29
           would both key to 29 and the second would silently win the join;
      (iii) no provider bare number is absent from the boundary dataset. This
           is the direction a doctored orphan #999 walked straight through:
           before this change it printed a line and wrote 50 records with exit
           0, because the report ran AFTER the write and never gated.

    WHAT DOES NOT GATE, and must not: boundary areas with NO provider. NONE are
    in that state today — the nine that were are trap 9 in the scraper, a
    parser defect the city's page never had — but the city can add an area
    before it lets a contract, and a build that refused to write until every
    new SSA had an agency would withhold every correct answer over one the
    city has not awarded yet. They are printed instead, so the run log names
    each one and a jump is visible.
    """
    with open(path, encoding="utf-8") as fh:
        feats = json.load(fh).get("features") or []
    refs, dupes = {}, {}
    for f in feats:
        ref = str((f.get("properties") or {}).get("ref_no", ""))
        m = re.match(r"\s*SSA\s*#\s*0*(\d+)", ref)
        if not m:
            continue
        key = m.group(1)
        if key in refs:
            dupes.setdefault(key, [refs[key][0]]).append(f["properties"].get("ref_no"))
        refs[key] = (f["properties"].get("ref_no"), f["properties"].get("name"))

    if not refs:
        raise SystemExit("chicago-ssa-providers: the boundary dataset %s carries "
                         "no SSA ref_no this can read — refusing to write against "
                         "a comparand that parsed to nothing" % path)
    # (ii) the boundary side of the fold
    if dupes:
        raise SystemExit("chicago-ssa-providers: two boundary areas fold to one "
                         "bare SSA number, so the join key is no longer unique on "
                         "the city's own side: %s"
                         % "; ".join("#%s <- %s" % (k, ", ".join(map(str, v)))
                                     for k, v in sorted(dupes.items(),
                                                        key=lambda kv: int(kv[0]))))
    # (iii) every provider must land on a real area
    orphan = sorted((n for n in out if n not in refs), key=int)
    if orphan:
        raise SystemExit("chicago-ssa-providers: %d provider(s) name an SSA number "
                         "the city's boundary dataset does not carry, so the card "
                         "would never show them: %s"
                         % (len(orphan),
                            "; ".join("#%s (%s)" % (n, out[n]["ref"])
                                      for n in orphan)))

    miss = sorted((n for n in refs if n not in out), key=int)
    print("  join: %d of %d boundary SSAs have a provider (gated: no duplicate "
          "bare number on either side, no provider without an area)"
          % (len(refs) - len(miss), len(refs)))
    for n in miss:
        print("    no provider: %-14s %s" % refs[n])


def sort_key(number):
    """Order SSA keys numerically, and survive one that is not a number.

    Every key this builder writes is bare digits, so int() would do — but the
    whole point of --check is to read a file that may have been hand-edited,
    and a ValueError traceback out of the sort is a worse answer than the
    report the caller came for.
    """
    return (0, int(number), "") if str(number).isdigit() else (1, 0, str(number))


def read_shipped(path):
    """The shipped roster as {bare number: record}, or a refusal.

    flatten_records at depth 1 is the shape gate: it refuses a top level that
    is not a dict of dicts, which is exactly what a hand-edit breaks first.
    """
    if not os.path.exists(path):
        raise SystemExit("chicago-ssa-providers: %s is missing, so there is "
                         "nothing to check — run without --check to build it"
                         % path)
    with open(path, encoding="utf-8") as fh:
        shipped = json.load(fh)
    try:
        return flatten_records(shipped, 1)
    except ValueError as exc:
        raise SystemExit("chicago-ssa-providers: %s is not a flat {SSA number: "
                         "record} map — %s" % (path, exc))


def drift_lines(shipped, fresh):
    """Every difference between the shipped roster and a fresh build.

    Empty means the two agree exactly. Values are printed with %r so an
    added or lost trailing space — the shape of edit a phone or address
    reformat makes — is visible rather than rendering as an identical string.
    """
    lines = []
    for key in sorted(set(shipped) - set(fresh), key=sort_key):
        lines.append("  ONLY IN THE SHIPPED FILE  #%s (%s)"
                     % (key, shipped[key].get("provider") or "?"))
    for key in sorted(set(fresh) - set(shipped), key=sort_key):
        lines.append("  ONLY IN A FRESH BUILD     #%s (%s)"
                     % (key, fresh[key].get("provider") or "?"))
    for key in sorted(set(shipped) & set(fresh), key=sort_key):
        was, now = shipped[key], fresh[key]
        for field in sorted(set(was) | set(now)):
            if was.get(field) != now.get(field):
                lines.append("  CHANGED #%s %s: %r -> %r"
                             % (key, field, was.get(field), now.get(field)))
    return lines


# WHERE --check BELONGS, AND WHY IT IS IN NO WORKFLOW TODAY.
#
# Every other generator here has a --check that runs in smoke-test.yml: it
# rebuilds from files already in the tree and fails a PR that hand-edited a
# generated file. This one cannot be that, for two reasons and the second is
# the one that matters.
#
#   It needs two live fetches — the city's provider page and the Socrata
#   boundary dataset. A merge gate that reaches the internet fails every
#   unrelated PR in the repo on the afternoon chicago.gov is slow.
#
#   And even with both hosts up it goes red on a DATA EVENT. The shipped file
#   stops matching a fresh build the moment the city edits a provider's
#   telephone, which is not a defect in anything and is exactly what the weekly
#   workflow already turns into a reviewable PR. A gate that fires for reasons
#   unrelated to the diff in front of it is one people learn to ignore.
#
# Nor is it a new step in update-chicago-ssa-providers.yml, where it would be
# redundant: that workflow rebuilds the file and `git diff`s it, which asks the
# same question and then does something useful with the answer.
#
# So it is a tool rather than a gate — what to run when you want to know
# whether the shipped file is still current without mutating the tree, and the
# first thing to reach for if the weekly workflow has been failing. The
# invocation is:
#
#   python3 scripts/build_chicago_ssa_providers.py --check \
#     --boundaries <the cmr6-dn8c GeoJSON, as the workflow curls it>
#
# WHAT WOULD MAKE IT A MERGE GATE is committing a raw scraper payload and a
# boundary snapshot beside the roster, after which `--check --raw <snapshot>
# --boundaries <snapshot>` is offline and answers a different, narrower
# question: did the BUILDER change without the shipped file being rebuilt?
# That is worth having and is deliberately not in this change — it needs a
# rule for when the snapshots are refreshed, or they rot into a gate that
# passes against a city page nobody has read in a year.

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", default=None,
                    help="a saved scraper payload. A build reads %s; a --check "
                         "with no --raw scrapes fresh into a temporary file "
                         "instead, because a check writes nothing."
                         % os.path.relpath(DEFAULT_RAW, os.path.dirname(HERE)))
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--scrape", action="store_true",
                    help="run the scraper first instead of reading a saved --raw")
    ap.add_argument("--check", action="store_true",
                    help="compare the shipped --out against a build from the "
                         "sources read just now and exit non-zero on any "
                         "difference, writing nothing. NOT a merge gate: it "
                         "needs two live fetches and it goes red on a data "
                         "event (the city editing a provider's telephone) as "
                         "readily as on a defect. See the note above main().")
    ap.add_argument("--boundaries", required=True,
                    help="the Socrata SSA GeoJSON (cmr6-dn8c). REQUIRED, because a\n"
                         "comparand you can omit is a gate you can skip: this used to\n"
                         "be optional and the weekly workflow never passed it, so the\n"
                         "join was unchecked on every real run. The workflow fetches it\n"
                         "and fails the run if that fetch fails, which is what a weekly\n"
                         "job failing loudly is for.")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        if args.check and not args.raw:
            raw_path, scrape = os.path.join(tmp, "raw.json"), True
        else:
            raw_path, scrape = args.raw or DEFAULT_RAW, args.scrape
        if scrape:
            subprocess.check_call([sys.executable,
                                   os.path.join(HERE, "chicago_ssa_provider_scraper.py"),
                                   "--out", raw_path])
        if not os.path.exists(raw_path):
            raise SystemExit("chicago-ssa-providers: no scraper payload at %s — "
                             "pass --scrape to fetch one, or --raw to name a "
                             "saved one" % raw_path)
        with open(raw_path, encoding="utf-8") as fh:
            raw = json.load(fh)

        out = build(raw)
        # BEFORE THE WRITE. It ran after it until 2026-09-13, which is why an
        # orphan provider could be reported and shipped in the same run. A
        # --check runs it too, so the check is never weaker than the build.
        check_against_boundaries(out, args.boundaries)

        if args.check:
            # SAY WHICH PAYLOAD WAS COMPARED. "the sources read just now" is
            # true of the default --check and false of --check --raw <saved>,
            # and a check that overstates its own freshness is the one kind of
            # wrong answer this mode exists to avoid.
            note = ("the provider page read just now" if scrape
                    else "the saved payload %s" % raw_path)
            lines = drift_lines(read_shipped(args.out), out)
            if lines:
                print("\n".join(lines))
                raise SystemExit(
                    "chicago-ssa-providers: %d difference(s) between %s and a "
                    "build from %s. Usually this is the city editing its "
                    "provider page, which the weekly workflow turns into a PR; "
                    "re-run without --check to write it."
                    % (len(lines), args.out, note))
            print("chicago-ssa-providers: OK — %d provider(s); the shipped file "
                  "is exactly what %s and %s build"
                  % (len(out), note, args.boundaries))
            return

        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, sort_keys=True, ensure_ascii=False)
            fh.write("\n")
        print("chicago-ssa-providers: wrote %d provider(s) to %s"
              % (len(out), args.out))


if __name__ == "__main__":
    main()
