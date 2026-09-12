#!/usr/bin/env python3
"""
Cache gate: catch a CACHE-FIRST data file that changed without a cache bump.

WHY THIS EXISTS. Each instance's service worker splits `data/app/*.json` into
two lists by caching policy. ROSTER_URLS are network-first, so a changed roster
reaches a returning visitor immediately — that is deliberate, because a stale
roster names the wrong officeholder. GEOMETRY_URLS are CACHE-FIRST: boundaries
change about once a decade, so serving them from cache is instant and works
offline. The cost of that choice is that a changed geometry file reaches a
returning visitor ONLY when CACHE_NAME changes, because the activate handler
deletes the old cache and the new one refetches.

`sw.js` says so at the top — "Bump CACHE_NAME whenever SHELL_URLS,
GEOMETRY_URLS, or ROSTER_URLS change" — and until this file existed that
sentence was the whole mechanism. It is a comment addressed to whoever
remembers to read it.

WHAT WENT WRONG. On 2026-09-02 Wisconsin added seven counties across five PRs.
Every one of them rewrote `metro-outline.json`, the coverage ring that draws
the scope wash, and it sits in GEOMETRY_URLS. None of the five bumped
CACHE_NAME, which had last moved three weeks earlier. So every returning
visitor kept the old outline: their cards named the new counties' supervisors,
because rosters are network-first, while the map went on grAying those same
counties out as outside coverage. The app contradicted itself, and every gate
in the repo was green — `validate_index.py` checks that each data file appears
in exactly ONE of the two lists, which is a different question entirely.

Fonts joined the cache-first side on 2026-09-12 and are matched differently —
see `_cache_first`. The same rule applies to them: a changed font file reaches a
returning visitor only on a bump.

WHAT IT CHECKS. For each instance, the cache-first files that differ from the
change's base (usually `origin/main`), and whether that instance's CACHE_NAME
differs too. A changed cache-first file with an unchanged cache name fails, and
the message names the files, so the fix is obvious: bump `cache_name` in that
instance's worksheet (`<tag>/metro-worksheet.json`, or the root one for
Illinois) and regenerate.

WHAT IT DELIBERATELY DOES NOT CHECK. Network-first files — they need no bump,
and demanding one for every weekly roster PR would make the bump meaningless
noise that nobody reads. A NEW instance (no `sw.js` at the base) is skipped
rather than failed. And it does not verify the bump is an INCREMENT: any
different name evicts the old cache, which is the property that matters.

THE GAP THIS CANNOT SEE, and it is a real one: a change that ADDS files to
GEOMETRY_URLS without changing any file already there passes here, because the
cache-first list is taken from the BASE's sw.js and a brand-new file has no
stale copy for a returning visitor to hold. That reasoning is sound for the
visitor and it is NOT the whole rule — `sw.js`'s own header says to bump
"whenever SHELL_URLS, GEOMETRY_URLS, or ROSTER_URLS change", which a pure
addition does. Found on the Woodford change (2026-09-05), which added three
geometry files and shipped with the cache name unmoved while this gate stayed
green. Until the comment and the gate are reconciled, TREAT THE COMMENT AS THE
RULE: a change to any of the three lists gets a bump, and this gate catches
only the subset that would actually serve stale bytes.

Usage:
    python3 scripts/check_cache_version.py --base origin/main
"""

import argparse
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_NAME = re.compile(r'const\s+CACHE_NAME\s*=\s*"([^"]+)"')
GEOMETRY = re.compile(r"const\s+GEOMETRY_URLS\s*=\s*\[(.*?)\];", re.S)
SHELL = re.compile(r"const\s+SHELL_URLS\s*=\s*\[(.*?)\];", re.S)
# The font branch is a PREFIX rule in the fetch handler, not a list, so there is
# nothing to parse for names — its presence in the BASE's sw.js is what says a
# returning visitor may be holding a cached font.
FONT_BRANCH = re.compile(r'new URL\("fonts/", self\.registration\.scope\)')


def _git(*args):
    return subprocess.run(("git",) + args, cwd=REPO_ROOT,
                          capture_output=True, text=True)


def _at(ref, path):
    """One file's content at a git ref, or None when it is not there."""
    got = _git("show", "%s:%s" % (ref, path))
    return got.stdout if got.returncode == 0 else None


def _instances():
    """Top-level dirs that ship both an sw.js and a data/app/."""
    out = []
    for name in sorted(os.listdir(REPO_ROOT)):
        if os.path.isfile(os.path.join(REPO_ROOT, name, "sw.js")) and \
           os.path.isdir(os.path.join(REPO_ROOT, name, "data", "app")):
            out.append(name)
    return out


def _worksheet_for(tag):
    """Where THIS instance's worksheet lives, discovered rather than assumed.

    Every instance keeps its worksheet beside its app (`wi/metro-worksheet.json`)
    except Illinois, whose repo-level files stayed at the root when R2.3 moved
    the app down into `il/`. Printing "il/metro-worksheet.json" sent an operator
    to a path that does not exist, in the one message whose whole job is to say
    how to fix the failure. Discovery keeps that right if a worksheet ever
    moves; importing generate_metro_files.INSTANCES for the same map would not,
    because that module exits 1 without jsonschema and not as an ImportError.
    """
    local = os.path.join(tag, "metro-worksheet.json")
    return local if os.path.isfile(os.path.join(REPO_ROOT, local)) \
        else "metro-worksheet.json"


def _cache_first(sw_text, tag):
    """The files this service worker serves cache-first.

    Two kinds, because the worker matches them two ways. GEOMETRY_URLS is a
    literal list of data/app paths. The fonts are a PREFIX branch — the worker
    serves anything under its own fonts/ cache-first without naming a file,
    because a page downloads only the faces it renders glyphs for and listing
    all eighteen would precache about 160 KB nobody uses. So for fonts the
    comparand is every woff2/woff/ttf in the instance's fonts/ directory, and
    only when the BASE's worker already carried that branch: before it did,
    no returning visitor holds a cached font and no bump is owed.
    """
    files = set()
    for pattern in (GEOMETRY, SHELL):
        block = pattern.search(sw_text or "")
        if not block:
            continue
        for line in block.group(1).split("\n"):
            hit = re.search(r'"\./data/app/([^"]+)"', line)
            if hit:
                files.add("%s/data/app/%s" % (tag, hit.group(1)))
    if FONT_BRANCH.search(sw_text or ""):
        fonts = os.path.join(REPO_ROOT, tag, "fonts")
        if os.path.isdir(fonts):
            for name in sorted(os.listdir(fonts)):
                if name.endswith((".woff2", ".woff", ".ttf", ".otf")):
                    files.add("%s/fonts/%s" % (tag, name))
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/main",
                    help="git ref to compare against (default origin/main)")
    args = ap.parse_args()

    if _git("rev-parse", "--verify", args.base).returncode != 0:
        print("check-cache-version: SKIP — %s is not available in this checkout"
              % args.base)
        return 0

    changed = {l.strip() for l in
               _git("diff", "--name-only", args.base, "--").stdout.split("\n")
               if l.strip()}
    problems, checked = [], 0
    for tag in _instances():
        sw_path = "%s/sw.js" % tag
        # THE WORKING TREE IS THE HEAD SIDE, not the last commit. Reading
        # HEAD made this gate fail its own first real use: the bump was made
        # and regenerated but not yet committed, so it compared the base's
        # cache name against the PREVIOUS commit's and reported a change that
        # had already been fixed. In CI the two are the same thing — the
        # checkout IS the commit — which is exactly why a gate can be wrong
        # this way and still look green there. Compare what is on disk.
        with open(os.path.join(REPO_ROOT, sw_path), encoding="utf-8") as fh:
            head_sw = fh.read()
        base_sw = _at(args.base, sw_path)
        if base_sw is None:
            continue                     # a new instance has nothing to go stale
        checked += 1
        # The BASE's list is what a returning visitor already holds.
        stale = sorted(changed & _cache_first(base_sw, tag))
        if not stale:
            continue
        was = CACHE_NAME.search(base_sw)
        now = CACHE_NAME.search(head_sw)
        if was and now and was.group(1) == now.group(1):
            problems.append(
                "  %s: %d cache-first file(s) changed and CACHE_NAME is still "
                "%s, so a returning visitor keeps the old copy:\n%s\n"
                "    Fix: bump \"cache_name\" in %s and run "
                "python3 scripts/generate_metro_files.py"
                % (tag, len(stale), now.group(1),
                   "\n".join("      " + f for f in stale), _worksheet_for(tag)))

    if problems:
        print("check-cache-version: FAIL — a cache-first file changed without a "
              "cache bump\n" + "\n".join(problems), file=sys.stderr)
        return 1
    print("check-cache-version: OK — %d instance(s) checked against %s; every "
          "changed cache-first file carries a cache bump" % (checked, args.base))
    return 0


if __name__ == "__main__":
    sys.exit(main())
