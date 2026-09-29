#!/usr/bin/env python3
"""What every tile mirror needs, in one copy.

A "mirror" here is a script that fetches a set some app draws live from
another organisation's server, builds a vector-tile archive from it through
scripts/build_vector_tiles.py's own build and gate, commits the archive and
records what it fetched (docs/OPTIMIZATION_PLAYBOOK.md §10, phase 6).
scripts/mirror_tiger_tiles.py does that for the Census TIGERweb and ZIP
layers; scripts/mirror_portal_tiles.py does it for the three city open-data
portals. What they fetch and how they prove the app still reads it differ
completely; everything below is the same in both.

THE CACHE BUMP IS WHY THIS FILE EXISTS. A replaced archive reaches a
returning visitor only through a new CACHE_NAME, and two mirrors each moving
that name their own way is exactly the two-writers-of-one-fact shape this
repository keeps paying for. There is one bump_cache.
"""

import hashlib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def key(tag, layer):
    return "%s:%s" % (tag, layer)


def archive_path(tag, layer):
    return os.path.join(REPO_ROOT, tag, "data", "app", "tiles", layer + ".pmtiles")


def registered_tiles(html):
    """Every layer id this app registers with a `tiles:` archive."""
    return set(re.findall(r'\btiles:\s*"data/app/tiles/([^"/]+)\.pmtiles"', html))


def worksheet_path(tag):
    # Illinois's worksheet is the repo-root one, the others sit in their folder
    return os.path.join(REPO_ROOT, "metro-worksheet.json") if tag == "il" \
        else os.path.join(REPO_ROOT, tag, "metro-worksheet.json")


def bump_cache(tags, fail):
    """A REPLACED archive reaches a returning visitor only through a new
    CACHE_NAME: the service worker serves every byte range under data/app/tiles/
    from its cache without asking again (engine sw-handlers), and
    scripts/check_cache_version.py fails a change that modifies an archive
    without one. So each app whose archive a run replaced gets its worksheet's
    cache_name moved on by one and its generated files rewritten. An archive
    that is NEW needs nothing — no visitor holds it.

    `fail` is the caller's own failure function, so the message names the
    mirror the operator ran rather than this module."""
    for tag in sorted(tags):
        path = worksheet_path(tag)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        found = re.findall(r'"cache_name":\s*"([^"]*?)(\d+)"', text)
        if len(found) != 1:
            fail("%s: expected one cache_name ending in a number, found %d" % (path, len(found)))
        stem, n = found[0]
        new = "%s%d" % (stem, int(n) + 1)
        text = re.sub(r'("cache_name":\s*")[^"]*(")', lambda m: m.group(1) + new + m.group(2), text, count=1)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("  cache  %-36s %s%s -> %s" % (tag, stem, n, new), flush=True)
    if tags:
        got = subprocess.run([sys.executable, os.path.join(HERE, "generate_metro_files.py")],
                             cwd=REPO_ROOT, capture_output=True, text=True)
        if got.returncode != 0:
            fail("generate_metro_files.py failed after the cache bump: %s" % (got.stderr or got.stdout)[-600:])


# The record each mirror writes. A gate that asks "which archives have no
# shipped file to be held to?" must read EVERY one of them: reading a single
# record was right while one mirror existed and silently answers "this archive
# is unaccounted for" the day a second lands (scripts/build_vector_tiles.py
# --committed and scripts/probe_tile_cards.mjs both asked it that way).
RECORDS = ("tiger-mirror.json", "portal-mirror.json")


def mirrored_layers():
    """{(tag, layer): record} for every archive any mirror recorded."""
    import json
    out = {}
    for name in RECORDS:
        path = os.path.join(REPO_ROOT, name)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as fh:
            for k, rec in (json.load(fh).get("layers") or {}).items():
                tag, _, layer = k.partition(":")
                out[(tag, layer)] = rec
    return out
