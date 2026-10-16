#!/usr/bin/env python3
"""Read every Wisconsin county's published list of town boards.

One module per county under `town_boards/` (see that package's docstring for
the contract). This runner imports each, runs it with failure isolation — one
county's dead link or changed layout is that county's failure and never the
run's — and writes what each returned, untouched, to the cache. Matching town
names to the map and deciding what ships is `build_wi_town_boards.py`'s job.

    python3 wi/scripts/wi_town_board_scraper.py              # every county
    python3 wi/scripts/wi_town_board_scraper.py --county clark,door
    python3 wi/scripts/wi_town_board_scraper.py --county clark --print

`--print` shows what a module returned, town by town, for checking a parser
against its document by eye.
"""

import argparse
import datetime
import importlib
import json
import os
import pkgutil
import sys
import traceback

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import town_boards  # noqa: E402

CACHE_DIR = os.path.join(SCRIPT_DIR, ".cache")
DEFAULT_OUT = os.path.join(CACHE_DIR, "wi_town_boards_raw.json")


def modules():
    for info in sorted(pkgutil.iter_modules(town_boards.__path__),
                       key=lambda m: m.name):
        if info.name.startswith("_"):
            continue
        yield info.name


def run_one(slug):
    mod = importlib.import_module("town_boards." + slug)
    ctx = town_boards.Ctx(getattr(mod, "CLIENT", "token"))
    rec = {
        "county": mod.COUNTY_NAME,
        "fips": mod.COUNTY_FIPS,
        "sourceUrl": mod.SOURCES[0],
        "client": getattr(mod, "CLIENT", "token"),
        "readOn": datetime.date.today().isoformat(),
    }
    try:
        got = mod.scrape(ctx)
        towns = got.get("towns") or {}
        clean_towns = {}
        dropped = 0
        for town, people in towns.items():
            keep = []
            for p in people:
                if not p.get("role") or not town_boards.looks_like_person(p.get("name")):
                    dropped += 1
                    continue
                keep.append(town_boards.person(p["name"], p["role"]))
            if keep:
                clean_towns[town_boards.clean(town)] = keep
        rec.update(ok=True, towns=clean_towns, edition=got.get("edition"),
                   droppedRows=dropped)
    except Exception as exc:  # noqa: BLE001 — one county's failure, recorded
        rec.update(ok=False, error="%s: %s" % (type(exc).__name__, exc))
        traceback.print_exc()
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--county", help="comma-separated module names")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--print", action="store_true", dest="show")
    args = ap.parse_args()

    wanted = list(modules())
    if args.county:
        pick = [c.strip() for c in args.county.split(",") if c.strip()]
        unknown = sorted(set(pick) - set(wanted))
        if unknown:
            sys.exit("no module named %s under town_boards/" % ", ".join(unknown))
        wanted = pick

    # merge into an existing cache so a one-county run does not erase the rest
    out = {}
    if os.path.exists(args.out):
        with open(args.out) as fh:
            out = json.load(fh)
    for slug in wanted:
        rec = run_one(slug)
        out[slug] = rec
        if rec["ok"]:
            towns = rec["towns"]
            chairs = sum(1 for ps in towns.values()
                         if any(p["role"] == "Chairperson" for p in ps))
            print("%-14s ok   %3d towns, %3d with a chair, %3d people, %d rows dropped"
                  % (slug, len(towns), chairs, sum(len(v) for v in towns.values()),
                     rec["droppedRows"]))
            if args.show:
                for town, ps in sorted(towns.items()):
                    print("    %s: %s" % (town, "; ".join(
                        "%s %s" % (p["role"], p["name"]) for p in ps)))
        else:
            print("%-14s FAIL %s" % (slug, rec["error"]))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")


if __name__ == "__main__":
    main()
