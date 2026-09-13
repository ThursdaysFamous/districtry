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

Measured 2026-09-12: 49 of the boundary file's 58 SSAs get a provider. The
nine that do not are Greek Town (16), Six Corners (28-2014), 95th/Ashland
(69), Roseland (71), Village:Austin (72), Chinatown (73), Oak Street (75),
North Michigan Avenue (76-2024) and West Garfield Park (77) — the city's list
simply has no entry for them, so those cards say so rather than guessing.
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# BOTH PATHS ANCHOR TO HERE, and both live under il/. DEFAULT_RAW pointed at
# the repo root's data/source/ until 2026-09-13 — a directory that does not
# exist and that the scraper never wrote to — so the builder with no --raw
# read nothing, and --scrape would have created a stray root directory beside
# the instance the app actually serves from. The weekly workflow passes --raw
# explicitly, which is why the mismatch never failed a run.
DEFAULT_RAW = os.path.join(HERE, "..", "il", "data", "source",
                           "chicago-ssa-providers.raw.json")
OUT = os.path.join(HERE, "..", "il", "data", "app", "chicago-ssa-providers.json")

# 49 parse today. The floor allows a handful of blocks to lapse between city
# edits without a false alarm, and refuses a run that lost a third of them.
MIN_PROVIDERS = 40
# Every shipped record carries all four; a run that drops one has parsed badly.
REQUIRED = ("provider", "address", "phone")


def bare(ref):
    """'17-2025' -> '17'. See the join-key note in the module docstring."""
    return str(ref).split("-")[0]


def build(raw):
    providers = raw.get("providers") or {}
    if len(providers) < MIN_PROVIDERS:
        raise SystemExit("chicago-ssa-providers: only %d provider(s) parsed, floor is %d "
                         "— refusing to overwrite a good file with a bad scrape"
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

    WHAT DOES NOT GATE, and must not: boundary areas with NO provider. Nine of
    the 58 are in that state because the city's list omits them, which is the
    open half of the gap record rather than an error. They are printed so a jump
    is visible in the run log.
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


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", default=DEFAULT_RAW)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--scrape", action="store_true",
                    help="run the scraper first instead of reading a saved --raw")
    ap.add_argument("--boundaries", required=True,
                    help="the Socrata SSA GeoJSON (cmr6-dn8c). REQUIRED, because a\n"
                         "comparand you can omit is a gate you can skip: this used to\n"
                         "be optional and the weekly workflow never passed it, so the\n"
                         "join was unchecked on every real run. The workflow fetches it\n"
                         "and fails the run if that fetch fails, which is what a weekly\n"
                         "job failing loudly is for.")
    args = ap.parse_args()

    if args.scrape:
        subprocess.check_call([sys.executable,
                               os.path.join(HERE, "chicago_ssa_provider_scraper.py"),
                               "--out", args.raw])
    with open(args.raw, encoding="utf-8") as fh:
        raw = json.load(fh)

    out = build(raw)
    # BEFORE THE WRITE. It ran after it until 2026-09-13, which is why an orphan
    # provider could be reported and shipped in the same run.
    check_against_boundaries(out, args.boundaries)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    print("chicago-ssa-providers: wrote %d provider(s) to %s" % (len(out), args.out))


if __name__ == "__main__":
    main()
