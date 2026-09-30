#!/usr/bin/env python3
"""
Build data/app/borough-officials.json (Borough President + District Attorney
+ County Clerk) from the operator-maintained scripts/borough_officials_source.json
(METRO_EXPANSION_PLAYBOOK §9, §11.3), plus — for the County Clerk row only —
the NYC Green Book scraped by greenbook_clerk_scraper.py.

The BP and DA rows are elected offices with no clean machine-readable roster,
and they change only every 4 years, so they stay an operator step: edit the
source JSON with hand-verified names + official URLs, then run this.

THE CLERK ROW HAS TWO PUBLISHERS AND THE RULE BETWEEN THEM IS NARROW.
NYC County Clerks are APPOINTED by the Appellate Division, so there is no
certified election return behind them. The courts' own site named two of five
and has been behind a Cloudflare managed challenge since 2026-09-26, so three
boroughs named nobody. Adam ruled on 2026-09-29 that the Green Book — the City
of New York's own staff directory — may fill those absences.

    FILL AN ABSENCE. NEVER OVERWRITE A NAME.

That is the whole rule, and it is STRUCTURAL rather than a list of boroughs: a
clerk whose operator entry carries a name is left exactly as it is, whatever
the directory says. The case it exists for is the Bronx, where the two
publishers disagree (the card says Hon. Ischia Bravo, the directory says Luis
Diaz) and nothing this project can read settles which is current — both routes
that could are shut. A disagreement is PRINTED on every run and acted on by
nobody; it is the operator's to rule on, not this builder's.

WHY A DISAGREEMENT PRINTS RATHER THAN FAILS. Brooklyn is the one control
available on the directory — the only borough where both publishers name
somebody — and it passes. Failing the build if it ever stopped passing would
turn a borough's clerk changing office into a red weekly job, when what
actually happened is that one of two sources caught up first. Printing keeps it
visible to a reader of the run without deciding anything. The comparison is on
the PERSON and not the string, because the operator file writes "Hon. Nancy T.
Sunshine" where the directory writes "Nancy Sunshine" and a literal comparison
would report a disagreement every week that does not exist.

A FILLED NAME IS STAMPED `nameSource`, so the card can say which publisher
named this person and a reader can see that two feed one row. A name the
operator verified carries no stamp, which is what "the courts' page, checked by
hand" has always meant here.

IF THE SCRAPE DID NOT RUN, NOTHING IS UNPUBLISHED. A missing cache file does
not empty the three clerk names out of the shipped roster: the previous
output's Green Book names are carried forward and a NOT RE-READ line naming the
file and its age prints instead (CLAUDE.md, Adam's ruling of 2026-09-19 — a
refusal or an outage stops the FETCH and never deletes what we already have).

Only entries with a non-null name are emitted for BP and DA (a null name -> the
card links to the NYC Green Book and names no one). Officeholder data is never
guessed.

Output shape: { "<Borough>": { "bp": {"name","url"}, "da": {"name","url"},
"clerk": {"name"?,"nameSource"?,"url","address"?,"phone"?} } }. Clerk entries
are emitted even without a name (the office/link rows are verifiable on their
own).

Usage:
    python3 ny/scripts/build_borough_officials.py
"""

import json
import os
import re
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(os.path.dirname(__file__), "borough_officials_source.json")
CACHE = os.path.join(os.path.dirname(__file__), ".cache", "greenbook_clerks.json")
OUT = os.path.join(REPO, "data", "app", "borough-officials.json")
BOROUGHS = ["Manhattan", "Bronx", "Brooklyn", "Queens", "Staten Island"]

GREENBOOK = "greenbook"
GREENBOOK_LABEL = "NYC Green Book"

# Honorifics and middle initials the operator file carries and the directory
# does not. Stripped only for the COMPARISON — never from a shipped name.
_HONORIFIC = re.compile(r"^(hon\.?|honorable|mr\.?|ms\.?|mrs\.?|dr\.?)\s+", re.I)
_INITIAL = re.compile(r"\b[A-Za-z]\.\s*")


def clean(entry, allow_nameless=False):
    if not entry:
        return None
    name = (entry.get("name") or "").strip()
    if not name and not allow_nameless:
        return None
    out = {}
    if name:
        out["name"] = name
    for field in ("url", "address", "phone"):
        value = (entry.get(field) or "").strip()
        if value:
            out[field] = value
    return out or None


def same_person(a, b):
    """Do two spellings name the same person?

    Deliberately loose on FORM and strict on CONTENT: honorifics and middle
    initials come off, case and punctuation are flattened, and what is left
    must match exactly. "Hon. Nancy T. Sunshine" and "Nancy Sunshine" are the
    same person; "Hon. Ischia Bravo" and "Luis Diaz" are not, and no amount of
    normalising makes them agree.
    """
    def key(name):
        name = _HONORIFIC.sub("", (name or "").strip())
        name = _INITIAL.sub("", name)
        name = re.sub(r"[^a-z ]", "", name.lower())
        return " ".join(name.split())
    return key(a) == key(b)


def load_greenbook():
    """(clerks, note) — the scrape, or the last-good names carried forward."""
    if os.path.exists(CACHE):
        data = json.load(open(CACHE))
        clerks = data.get("clerks") or {}
        return ({b: (v.get("name") or "").strip() for b, v in clerks.items()
                 if (v.get("name") or "").strip()},
                "read %s (scraped %s)" % (os.path.basename(CACHE),
                                          data.get("scraped_at") or "unknown"))

    # No scrape this run. Carry forward whatever the shipped roster already
    # credits to the Green Book, and say so rather than silently dropping it.
    if not os.path.exists(OUT):
        return {}, "no scrape and no previous output — no clerk name is filled"
    previous = json.load(open(OUT))
    carried = {}
    for boro, row in previous.items():
        clerk = row.get("clerk") or {}
        if clerk.get("nameSource") == GREENBOOK and clerk.get("name"):
            carried[boro] = clerk["name"]
    age = (time.time() - os.path.getmtime(OUT)) / 86400.0
    return carried, ("NOT RE-READ — %s is absent, so %d Green Book name(s) are "
                     "carried forward from data/app/borough-officials.json "
                     "(%.1f days old)" % (os.path.basename(CACHE), len(carried), age))


def main():
    src = json.load(open(SRC)).get("boroughs", {})
    greenbook, note = load_greenbook()
    print("build_borough_officials: %s" % note, file=sys.stderr)

    roster = {}
    filled = 0
    from_greenbook = []
    disagreements = []
    for boro in BOROUGHS:
        row = src.get(boro, {})
        entry = {}
        for role in ("bp", "da", "clerk"):
            # elected BP/DA rows require a name; the appointed clerk's office
            # row is verifiable without one (see the source's _verified note).
            person = clean(row.get(role), allow_nameless=(role == "clerk"))
            if role == "clerk" and person is not None:
                directory = greenbook.get(boro)
                if person.get("name") and directory:
                    # BOTH publishers name somebody. The operator file wins,
                    # always — this is the branch that must never write.
                    if not same_person(person["name"], directory):
                        disagreements.append(
                            "%s: card names %s, %s names %s — LEFT AS IS (the "
                            "operator's to rule on)"
                            % (boro, person["name"], GREENBOOK_LABEL, directory))
                elif directory and not person.get("name"):
                    person["name"] = directory
                    person["nameSource"] = GREENBOOK
                    from_greenbook.append("%s: %s" % (boro, directory))
            if person:
                # Key order is the reading order — a name before the address
                # it sits at — and a filled name is added last, so it is
                # re-ordered here rather than left where the fill put it.
                entry[role] = {k: person[k] for k in
                               ("name", "nameSource", "url", "address", "phone")
                               if k in person}
                filled += 1
        if entry:
            roster[boro] = entry

    with open(OUT, "w") as f:
        json.dump(roster, f, indent=0, ensure_ascii=False)

    for line in from_greenbook:
        print("build_borough_officials: filled from %s — %s"
              % (GREENBOOK_LABEL, line), file=sys.stderr)
    for line in disagreements:
        print("build_borough_officials: PUBLISHERS DISAGREE — %s" % line,
              file=sys.stderr)
    if filled == 0:
        print("wrote data/app/borough-officials.json: EMPTY — no names filled in the source yet "
              "(operator step §11.3; cards link to the NYC Green Book until then).", file=sys.stderr)
    else:
        named = sum(1 for row in roster.values() for rec in row.values() if rec.get("name"))
        print("wrote data/app/borough-officials.json: %d of 15 offices filled, "
              "%d named (%d of them from the %s)"
              % (filled, named, len(from_greenbook), GREENBOOK_LABEL), file=sys.stderr)


if __name__ == "__main__":
    main()
