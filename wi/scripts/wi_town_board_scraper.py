#!/usr/bin/env python3
"""Read every Wisconsin county's published list of town boards.

One module per county under `town_boards/` (see that package's docstring for
the contract). This runner imports each, runs it with failure isolation — one
county's dead link or changed layout is that county's failure and never the
run's — and writes what each returned to the cache, after
`town_boards.normalize`: rows that are not a board member are dropped, and a
telephone number that is an office's line rather than the officer's own (one
printed more than once anywhere in what the module read, or one a page links
as tel: to a different number than it shows) is taken off every officer who
carries it. The rest of each officer's numbers are kept, with the county's
labels (Adam, 2026-10-17: "if the official government source uses personal
phone numbers, we publish those"). Matching town names to the map and deciding
what ships is `build_wi_town_boards.py`'s job.

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
        clean_towns, dropped, taken = town_boards.normalize(
            got.get("towns") or {}, ctx)
        rec.update(ok=True, towns=clean_towns, edition=got.get("edition"),
                   droppedRows=dropped, numbersTakenOff=taken)
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
            people = [p for ps in towns.values() for p in ps]
            print("%-14s ok   %3d towns, %3d with a chair, %3d people, "
                  "%3d with a number (%d with a second), %d rows dropped, "
                  "%d office numbers taken off"
                  % (slug, len(towns), chairs, len(people),
                     sum(1 for p in people if p.get("phone")),
                     sum(1 for p in people if p.get("phonesExtra")),
                     rec["droppedRows"], rec["numbersTakenOff"]))
            if args.show:
                # names and roles only: --print is for checking a parser's
                # reading of names, and a run log is no place for numbers
                for town, ps in sorted(towns.items()):
                    print("    %s: %s" % (town, "; ".join(
                        "%s %s%s" % (p["role"], p["name"],
                                     " [%d numbers]" % len(town_boards.phones_of(p))
                                     if p.get("phone") else "")
                        for p in ps)))
        else:
            print("%-14s FAIL %s" % (slug, rec["error"]))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")


if __name__ == "__main__":
    main()
