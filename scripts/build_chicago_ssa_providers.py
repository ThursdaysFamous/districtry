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
boundary SSA, so the fold is safe in both directions; the builder re-checks
both on every run.

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
DEFAULT_RAW = os.path.join(HERE, "..", "data", "source", "chicago-ssa-providers.raw.json")
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
    """Report the join against the shipped SSA boundary ids, when they are local.

    The boundaries are fetched live from Socrata at runtime, so there is no
    same-origin file to compare against — this runs only when a caller passes
    a saved copy. It never gates: the point is to print which SSAs the card
    will say nothing about, so an unexpected jump is visible in the run log.
    """
    with open(path, encoding="utf-8") as fh:
        feats = json.load(fh).get("features") or []
    refs = {}
    for f in feats:
        m = re.match(r"\s*SSA\s*#\s*0*(\d+)", str((f.get("properties") or {}).get("ref_no", "")))
        if m:
            refs[m.group(1)] = (f["properties"].get("ref_no"), f["properties"].get("name"))
    miss = sorted((n for n in refs if n not in out), key=int)
    orphan = sorted((n for n in out if n not in refs), key=int)
    print("  join: %d of %d boundary SSAs have a provider" % (len(refs) - len(miss), len(refs)))
    for n in miss:
        print("    no provider: %-14s %s" % refs[n])
    for n in orphan:
        print("    provider with no boundary SSA: #%s (%s)" % (n, out[n]["ref"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", default=DEFAULT_RAW)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--scrape", action="store_true",
                    help="run the scraper first instead of reading a saved --raw")
    ap.add_argument("--boundaries", help="a saved copy of the Socrata SSA GeoJSON, to "
                                         "report the join (never gates)")
    args = ap.parse_args()

    if args.scrape:
        subprocess.check_call([sys.executable,
                               os.path.join(HERE, "chicago_ssa_provider_scraper.py"),
                               "--out", args.raw])
    with open(args.raw, encoding="utf-8") as fh:
        raw = json.load(fh)

    out = build(raw)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    print("chicago-ssa-providers: wrote %d provider(s) to %s" % (len(out), args.out))
    if args.boundaries:
        check_against_boundaries(out, args.boundaries)


if __name__ == "__main__":
    main()
