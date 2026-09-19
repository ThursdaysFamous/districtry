#!/usr/bin/env python3
"""
A Wikidata item for districtry, drafted and NOT created.

WHY A DRAFT AND NOT AN EDIT. The search audit's last phase-3 item asks for a
Wikidata item, because an item is what a knowledge panel and several AI search
systems read when they want to know what a site is. Creating one is an
outward-facing edit to somebody else's public database under a declared conflict
of interest, and it cannot be undone by this project once other editors have
built on it. So this script writes the item out for a person to review and
enter, and edits nothing. Nothing here is sent or saved anywhere.

EVERY ID IS VERIFIED RATHER THAN REMEMBERED, and that is not a formality: the
first draft of this table had Q193424 for "web application", which is the item
for WEB SERVICE. Each id below was fetched from wikidata.org on the date in
VERIFIED and carries the English label the site returned. `--verify` re-fetches
and fails on a label that has moved; it is not in CI, because a network check
belongs on the monthly job with the other ones.

WHICH WIKIDATA URLS THIS PROJECT MAY READ was measured with the fleet's own
robots reader rather than assumed. `/w/api.php` is DISALLOWED and so is
`query.wikidata.org/sparql`, so neither the search API nor SPARQL is available
here; `/wiki/Special:EntityData/*.json` is explicitly ALLOWED, which is the
endpoint Wikidata publishes for exactly this, and is the only one used.

THE ITEM CARRIES NO COUNT. "93 counties" and "40 layers" are true today and
nobody will re-edit a Wikidata item when they move — the same reasoning that
keeps a seat count out of every generated page here. The jurisdictions come from
metros.json, so a new state joins this draft by being registered.

    python3 scripts/build_wikidata_draft.py           # write docs/WIKIDATA.md
    python3 scripts/build_wikidata_draft.py --check   # drift gate for CI
    python3 scripts/build_wikidata_draft.py --verify  # re-fetch every id (network)
"""

import argparse
import difflib
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METROS = os.path.join(REPO_ROOT, "metros.json")
OUT = os.path.join(REPO_ROOT, "docs", "WIKIDATA.md")
ENTITY_DATA = "https://www.wikidata.org/wiki/Special:EntityData/%s.json"
UA = "districtry/1.0 (+https://districtry.com/)"

VERIFIED = "2026-09-16"

# id -> the English label wikidata.org returned on VERIFIED.
IDS = {
    "P31": "instance of",
    "P856": "official website",
    "P1324": "source code repository URL",
    "P17": "country",
    "P275": "copyright license",
    "P407": "language of work or name",
    "P1001": "applies to jurisdiction",
    "P571": "inception",
    "Q35127": "website",
    "Q189210": "web application",
    "Q30": "United States",
    "Q1860": "English",
    "Q13785927": "Apache Software License 2.0",
    "Q1224853": "Open Database License",
    "Q1204": "Illinois",
    "Q1537": "Wisconsin",
    "Q1546": "Iowa",
    "Q1166": "Michigan",
    "Q1384": "New York",
    "Q62": "San Francisco",
}

# metros.json tag -> the jurisdiction item that instance answers for. STATED,
# because nothing in a tag or a landing name yields a Q-number, and a wrong one
# is a statement about a different place.
#
# NOTHING HERE CATCHES A WRONG ID, which is why each is derived rather than
# recalled. render() checks only that every metros.json tag HAS an entry, and
# --verify only re-fetches each id's label and fails when the label has MOVED —
# so a wrong-but-correctly-labelled id passes both. Reproduced 2026-09-19 by
# setting "ny" to Illinois's own Q1204: the page rendered "Q1204 (Illinois) |
# the /ny/ instance" and --check went green.
#
# ny moved from Q60 (New York City) to Q1384 at the 2026-09-19 go-live, when
# the instance began answering for the whole state. Q1384 was NOT searched for:
# it is the value of Q60's own P131 (located in the administrative territorial
# entity), so it was derived from the id already here. Confirmed the state and
# not the metro area by three properties — P31 = Q35657 ("U.S. state", the same
# class Q1204, Q1537, Q1546 and Q1166 instantiate), P300 = "US-NY", P131 = Q30
# (United States). Its English label is the bare string "New York"; writing
# "New York State" would fail --verify character for character.
JURISDICTION = {
    "il": "Q1204", "wi": "Q1537", "ia": "Q1546", "mi": "Q1166",
    "ny": "Q1384", "ca": "Q62",
}


def fail(msg):
    print("build-wikidata-draft: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def verify():
    """Re-fetch every id's label. Network, robots-checked, not in CI."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import time
    import urllib.request
    from robots_policy import RobotsGate

    gate = RobotsGate(session=None, user_agent=UA)
    moved = []
    for key, label in sorted(IDS.items()):
        url = ENTITY_DATA % key
        allowed, why = gate.allows(url)
        if not allowed:
            fail("robots.txt disallows %s — %s" % (url, why))
        request = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.load(response)
        got = data["entities"][key]["labels"].get("en", {}).get("value")
        if got != label:
            moved.append("%s: recorded %r, wikidata.org says %r"
                         % (key, label, got))
        time.sleep(0.4)
    if moved:
        fail("%d id(s) no longer carry the recorded label:\n  - %s"
             % (len(moved), "\n  - ".join(moved)))
    print("build-wikidata-draft: OK — all %d id(s) still carry the label "
          "recorded on %s" % (len(IDS), VERIFIED))


def q(key):
    return "%s (%s)" % (key, IDS[key])


def render():
    metros = load(METROS)["metros"]
    missing = [m["tag"] for m in metros if m["tag"] not in JURISDICTION]
    if missing:
        fail("metros.json carries %s with no jurisdiction item here — a new "
             "instance needs its Q-number added and verified"
             % ", ".join(missing))
    jurisdictions = "\n".join(
        "| %s | %s | %s |" % (q("P1001"), q(JURISDICTION[m["tag"]]),
                              "the `/%s/` instance" % m["tag"])
        for m in metros)

    return """# A Wikidata item for districtry — drafted, not created

<!-- ==== GENERATED FILE — DO NOT HAND-EDIT ==== -->
<!-- Emitted by scripts/build_wikidata_draft.py.
     Regenerate:  python3 scripts/build_wikidata_draft.py
     Drift gate:  python3 scripts/build_wikidata_draft.py --check
     Re-verify:   python3 scripts/build_wikidata_draft.py --verify  (network) -->

**Nothing here has been entered on wikidata.org.** Creating the item is an edit
to a public database that other people will build on, made under a declared
conflict of interest, and it goes when a person decides it goes — the rule
`docs/ASK_DRAFTS.md` and `docs/PRESS_LIST.md` already set for everything
outbound.

## Read this before creating it

**The conflict of interest is real and must be declared.** Wikidata asks an
editor with a connection to a subject to say so. Anyone creating this item
should be editing from an account whose user page states the connection, and
should expect — and welcome — other editors changing it.

**Notability is the open question, and this project cannot settle it.**
Wikidata's notability policy admits an item that "refers to an instance of a
clearly identifiable conceptual or material entity ... that can be described
using serious and publicly available references." As of %(verified)s the
references available are the site itself and its source repository, both
first-party. The press list records 17 newsrooms contacted and one reply
expressing interest; no third-party piece has published. An item created on
first-party references alone can be nominated for deletion, and that is a
foreseeable outcome rather than a surprise. **The cheap course is to wait for
one published third-party article and create the item citing it.** The other
course — create it now and accept the risk — is a legitimate choice and is the
operator's, not this file's.

**Do not create an item for the person.** A biography item about a living
private individual carries obligations this project is not set up to meet, and
the audit asked for an item about the project.

## The item

| Field | Value |
|---|---|
| Label (en) | districtry |
| Description (en) | web application for finding the civic districts that cover a United States address, and who represents them |
| Also known as (en) | districtry.com; Chicago District Explorer (the project's name before 2026-08-24) |

### Statements

| Property | Value | Note |
|---|---|---|
| %(p31)s | %(website)s | |
| %(p31)s | %(webapp)s | A second value, not a replacement: it is a website and it is an application served through one. |
| %(p856)s | https://districtry.com | |
| %(p1324)s | https://github.com/ThursdaysFamous/districtry | |
| %(p17)s | %(us)s | |
| %(p407)s | %(english)s | |
| %(p275)s | %(apache)s | The CODE licence, from this repository's own `LICENSE`. |
| %(p275)s | %(odbl)s | The DATA licence, from `LICENSE-DATA.md`, which covers the compiled databases and explicitly not the public records underneath them. Enter both or neither — one alone states half of what this project publishes. |
%(jurisdictions)s

### What is deliberately absent

**No count of anything.** Not counties, not layers, not officeholders. Every one
of those is true on the day it is typed and nobody will come back to a Wikidata
item when it moves — the same reason no generated page here states a seat count.
The jurisdictions above come from `metros.json`, so a new state reaches this
draft by being registered rather than by being remembered.

**%(p571)s.** The date the project began is not readable from this repository:
its git history here is shallow and the public changelog's earliest entry is a
snapshot rather than a start. The operator knows it; this file will not guess
it. Add it when creating the item, sourced to something public.

**Developer, operator and author.** Each of those properties takes an ITEM, and
the only candidate is a person — see the rule above. Leave them empty.

## Every id above, verified

Fetched from `Special:EntityData` on **%(verified)s**, with the English label
wikidata.org returned. `--verify` re-fetches and fails on a label that has moved.
This matters: the first draft of this table used Q193424 for "web application",
which is the item for **web service**.

**Nothing re-runs `--verify` on a schedule, and that is deliberate rather than an
oversight.** This file exists for one human action; a monthly job re-checking
twenty labels would be machinery guarding a document nobody is reading in the
months between. Run it immediately before creating the item.

**Which Wikidata URLs this project may read was measured, not assumed.** Its own
robots reader (`scripts/robots_policy.py`) says `/w/api.php` is disallowed and so
is `query.wikidata.org/sparql`, so neither the search API nor SPARQL is available
here. `/wiki/Special:EntityData/*.json` is explicitly allowed, and is the only
endpoint used.

| Id | Label on %(verified)s |
|---|---|
%(ids)s
""" % dict(
        verified=VERIFIED,
        p31=q("P31"), p856=q("P856"), p1324=q("P1324"), p17=q("P17"),
        p407=q("P407"), p275=q("P275"), p571=q("P571"),
        website=q("Q35127"), webapp=q("Q189210"), us=q("Q30"),
        english=q("Q1860"), apache=q("Q13785927"), odbl=q("Q1224853"),
        jurisdictions=jurisdictions,
        ids="\n".join("| `%s` | %s |" % (k, IDS[k]) for k in sorted(IDS)),
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="drift gate: fail rather than write")
    ap.add_argument("--verify", action="store_true",
                    help="re-fetch every id's label from wikidata.org (network)")
    args = ap.parse_args()

    if args.verify:
        return verify()

    page = render()
    try:
        with open(OUT, encoding="utf-8") as f:
            current = f.read()
    except OSError:
        current = None
    if current == page:
        print("build-wikidata-draft: OK — docs/WIKIDATA.md current (%d id(s) "
              "verified %s)" % (len(IDS), VERIFIED))
        return
    if args.check:
        for line in difflib.unified_diff((current or "").splitlines(),
                                         page.splitlines(),
                                         fromfile="committed",
                                         tofile="regenerated", lineterm="", n=1):
            print("  " + line, file=sys.stderr)
        fail("docs/WIKIDATA.md is out of date — run "
             "python3 scripts/build_wikidata_draft.py")
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write(page)
    print("build-wikidata-draft: OK — wrote docs/WIKIDATA.md, %d statement "
          "id(s) verified %s" % (len(IDS), VERIFIED))


if __name__ == "__main__":
    main()
