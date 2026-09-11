#!/usr/bin/env python3
"""
Build data/app/wi-circuit-judges.json from the wicourts scrape — stage 2 of
the pair (wi_circuit_judges_scraper.py is stage 1).

The join: the judges table's bench (authoritative) enriched per judge with the
contact page's branch number and direct phone, matched by normalized name.
Wisconsin's contact page prints judges ALL-CAPS ("WOOD, HON. DANIEL G. Br 1")
where the judges table prints display case, so matching is by
case-and-punctuation-folded surname + first token. A judge the contact page
lacks ships name-only rather than dropping. Fields degrade individually: no
e-mail exists anywhere on wicourts (measured), so none is invented.

THE CASE EXAMPLE THIS DOCSTRING USED TO GIVE WAS NEVER REAL. It cited
"McDougal -> Mcdougal" as a name whose all-caps rendering title-cases
differently and therefore ships name-only. fold() lowercases, so both spellings
produce the identical key and Richland's judge has always joined and has always
carried her phone; she lacks only a BRANCH, because her county runs one court
and the page prints no "Br" for it. 24 of the 25 branch-less judges are that
same case — a fact about the source, not a failed join.

TWO FALLBACK RUNGS BELOW THE EXACT KEY (added 2026-09-10), because the state's
own two pages write nine of 261 judges' names differently and each was shipping
with no branch and no phone while both sat on the contact page:

  * SPACING — `De Vries, Hon. Martin J.` on the bench table against
    `DEVRIES, HON. MARTIN J. Br 2` on the contact page. Same letters, same
    order, one space. Keyed on the whole name with separators removed.
  * GIVEN NAME — eight judges whose surname matches exactly and whose given
    name does not: `W. Andrew Voigt`/`William Andrew Voigt`,
    `Joe Veenstra`/`Joseph Veenstra`, `Gwen Connolly`/`Gwendolyn G. Connolly`,
    `T. Christopher Dee`/`Thomas Christopher Dee`,
    `Jonathan D. Watts`/`J.D. Watts`, `Dianne Schlipper`/`Diane L. Schlipper`,
    `R. Michael Waterman`/`Richard Michael Waterman`,
    `Zach Wittchow`/`Zachary Wittchow`. Keyed on surname + first INITIAL.

Both rungs require the match to be UNIQUE ON BOTH SIDES — one contact row is
not enough, because two judges of one bench sharing a key would each claim it.
Every fallback join is PRINTED on every run: each one is this builder deciding
that two differently-written names are one judge, and a reader can say no. The
NAME always comes from the bench table; a fallback attaches branch and phone
and never changes a spelling.

A SURNAME THAT DIFFERS BY A LETTER IS NOT BRIDGED, AND ONE JUDGE PAYS FOR IT.
Walworth's Br 1 is `Scholz, Hon. Estee` on the bench table and
`SCHOLTZ, HON. ESTEE Br 1` on the contact page — one `t` apart. She ships
name-only, and her Br 1 line, (262) 741-7023, is deliberately NOT attached:
the surname is the identity anchor, and picking a spelling would be this
project guessing which of two state pages is right about a sitting judge's
name. Recorded in wi/WATCH.md for a human to settle with the county.

Keyed by CIRCUIT KEY — the same keys build_wi_circuit_courts.py stamps on the
geometry (66 county slugs + buffalo-pepin, florence-forest,
menominee-shawano), so the card's join cannot disagree with the map.

Floors (refuses to write otherwise): exactly 69 circuit keys; >= 240 judges;
every circuit carries at least one judge and at least one courthouse address.
"""

import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "wi_circuit_judges_raw.json")
OUT = os.path.join(REPO_ROOT, "data", "app", "wi-circuit-judges.json")

EXPECT_CIRCUITS = 69
MIN_JUDGES = 240

# The two fallback rungs below the exact key exist to bridge a HANDFUL of rows
# the state's own two pages write differently (9 of 261 when they were added,
# 2026-09-10). They are not a general-purpose matcher, and if they ever start
# carrying a large share of the bench the exact key has broken and this run
# must say so rather than paper over it. A ceiling, never a floor: raising it
# to get a run green is the thing it is here to prevent.
MAX_FALLBACK_JOINS = 20

# THE CLERK LINK IS THE STATE'S, AND THE STATE'S CAN GO STALE. `clerkUrl` is
# whatever wicourts.gov's judges table links for that county, which is right
# nearly everywhere and is not maintained against the counties' own moves.
# Dodge County moved to www.co.dodge.wi.gov in 2026 and wicourts still links
# the pre-move path, which the new site answers with a SOFT 404 — HTTP 200 at
# /404-page-not-found, so neither this builder nor validate_card_links.py sees
# anything wrong while the card sends a reader to a "Page Not Found".
#
# An override is pinned per circuit rather than the file being hand-edited,
# because the weekly refresh would put the dead path straight back. Each entry
# names the replacement page the COUNTY publishes, and `--audit-overrides`
# prints any whose upstream has caught up so the entry can be dropped.
# A VALUE OF None MEANS "wicourts' link is dead and no replacement could be
# VERIFIED from here" — the card then ships NO link rather than a broken one,
# the same posture scripts/undeliverable.py takes with an address that cannot
# receive mail. A reader who clicks a dead link gets no error they can act on,
# and a card that links nothing at least does not send them somewhere wrong.
# Never guess a replacement: every URL below was fetched and read.
CLERK_URL_OVERRIDES = {
    # wicourts links /departments/departments-a-d/clerk-of-courts (soft 404);
    # the county's Courts page links this one. Checked 2026-08-29.
    "dodge": "https://www.co.dodge.wi.gov/courts-clerk",
    # THE COUNTY CHANGED DOMAIN. wicourts still links www.co.chippewa.wi.us,
    # which 301s to www.chippewacountywi.gov WITHOUT KEEPING THE PATH, so the
    # redirect lands on that site's own 404 and every status check passes. The
    # live page is on the county's Government index. Checked 2026-09-10.
    "chippewa": "https://www.chippewacountywi.gov/187/Clerk-of-Courts",
    # wicourts links /departments/clerk_of_courts/index.php, a hard 404. The
    # county's own homepage links this one. Checked 2026-09-10.
    "jefferson": "https://www.jeffersoncountywi.gov/courts___legal_services/clerk_of_courts/index.php",
    # NO VERIFIED REPLACEMENT — vernoncounty.org does not resolve, and it is
    # the county's DNS rather than this network: both Google and Cloudflare
    # public resolvers answer SERVFAIL for the apex AND www. SERVFAIL is a
    # broken delegation, not NXDOMAIN, so the domain still exists and may come
    # back; when it does, this entry is dropped rather than replaced.
    # Checked 2026-09-10.
    "vernon": None,
    # NO VERIFIED REPLACEMENT, AND DELIBERATELY NOT CHASED. co.ashland.wi.us
    # resolves NOERROR with no A record at all — the name exists and hosts no
    # site. The county's real site, ashlandcountywi.gov, does resolve, but it
    # publishes `User-agent: * / Disallow: /`, which this project honours: the
    # county board roster it already carries was read once and is carried as a
    # dated document for exactly that reason. So no path there is fetched to
    # verify, and none is guessed. Checked 2026-09-10.
    "ashland": None,
}


def fold(name):
    return "".join(ch for ch in name.lower() if ch.isalpha() or ch == " ").split()


def match_key(name):
    parts = fold(name)
    if not parts:
        return None
    return (parts[-1], parts[0])  # (surname-ish, first token)


def solid_key(name):
    """The whole name with every separator removed, so a surname the two pages
    space differently still keys the same. Dodge's judge is `De Vries, Hon.
    Martin J.` on the bench table and `DEVRIES, HON. MARTIN J. Br 2` on the
    contact page — the same letters in the same order, and nothing here
    changes one."""
    parts = fold(name)
    return "".join(parts) or None


def initial_key(name):
    """(surname-ish, first INITIAL) — the rung that bridges a given name the
    two pages write differently at the same length as each other's."""
    parts = fold(name)
    if not parts or not parts[0]:
        return None
    return (parts[-1], parts[0][0])


def main():
    raw_path = sys.argv[sys.argv.index("--in") + 1] if "--in" in sys.argv else RAW
    with open(raw_path) as f:
        raw = json.load(f)

    circuits = raw["circuits"]
    # The two pages spell county names differently ("Fond du Lac" in the
    # judges table, "Fond Du Lac" in the contact page's anchors), so the
    # contact lookup folds case and punctuation rather than trusting either
    # page's styling.
    def county_fold(name):
        return "".join(ch for ch in name.lower() if ch.isalnum())
    contact = {county_fold(k): v for k, v in raw["contact"].items()}
    unknown = sorted(set(CLERK_URL_OVERRIDES) - set(circuits))
    if unknown:
        raise SystemExit("clerk URL override names no such circuit: %s" % ", ".join(unknown))
    if len(circuits) != EXPECT_CIRCUITS:
        raise SystemExit("scrape carries %d circuits, expected %d" % (len(circuits), EXPECT_CIRCUITS))

    out = {}
    total = 0
    fallbacks = []
    for key, c in circuits.items():
        # branch/phone lookup across the circuit's counties (a merged
        # circuit's judge can sit in either county's courthouse block)
        enrich = {}
        by_solid = {}
        by_initial = {}
        courthouses = []
        for county in c["counties"]:
            block = contact.get(county_fold(county)) or {}
            for row in block.get("branch_rows", []):
                mk = match_key(row["name"])
                if mk and mk not in enrich:
                    enrich[mk] = row
                sk = solid_key(row["name"])
                if sk:
                    by_solid.setdefault(sk, []).append(row)
                ik = initial_key(row["name"])
                if ik:
                    by_initial.setdefault(ik, []).append(row)
            for addr in block.get("addresses", []):
                # first line is the judicial-district label; keep the location
                lines = [ln for ln in addr if not ln.lower().endswith("judicial district")]
                if lines and {"county": county, "lines": lines} not in courthouses:
                    courthouses.append({"county": county, "lines": lines})
        # A fallback must be unique on BOTH sides. One matching contact row is
        # not enough: two judges of one bench sharing a key would each claim it.
        bench_solid, bench_initial = {}, {}
        for j in c["judges"]:
            sk, ik = solid_key(j["name"]), initial_key(j["name"])
            if sk:
                bench_solid[sk] = bench_solid.get(sk, 0) + 1
            if ik:
                bench_initial[ik] = bench_initial.get(ik, 0) + 1

        judges = []
        for j in c["judges"]:
            mk = match_key(j["name"])
            row = enrich.get(mk) if mk else None
            if row is None:
                sk = solid_key(j["name"])
                cand = by_solid.get(sk, []) if sk else []
                if len(cand) == 1 and bench_solid.get(sk) == 1:
                    row = cand[0]
                    fallbacks.append((key, j["name"], row["name"], "spacing"))
            if row is None:
                ik = initial_key(j["name"])
                cand = by_initial.get(ik, []) if ik else []
                if len(cand) == 1 and bench_initial.get(ik) == 1:
                    row = cand[0]
                    fallbacks.append((key, j["name"], row["name"], "given name"))
            entry = {"name": j["name"]}
            if j.get("role"):
                entry["role"] = j["role"]
            if row:
                if row.get("branch"):
                    entry["branch"] = row["branch"]
                if row.get("phone"):
                    entry["phone"] = row["phone"]
                if row.get("role") and "role" not in entry:
                    entry["role"] = row["role"]
            judges.append(entry)
        if not judges:
            raise SystemExit("circuit %s parsed with no judges" % key)
        if not courthouses:
            raise SystemExit("circuit %s parsed with no courthouse address" % key)
        # A branch sort where branches exist keeps Milwaukee's 47 legible.
        judges.sort(key=lambda e: (int(e["branch"]) if e.get("branch", "").isdigit() else 999,
                                    e["name"].split()[-1]))
        total += len(judges)
        entry = {
            "counties": [n + " County" for n in c["counties"]],
            "judges": judges,
            "courthouses": courthouses[:4],
        }
        if key in CLERK_URL_OVERRIDES:
            override = CLERK_URL_OVERRIDES[key]
            if override:
                entry["sourceUrl"] = override
            # else: known dead with no verified replacement — no link ships,
            # and the elif below must not restore wicourts' own dead one.
        elif c.get("clerkUrl"):
            entry["sourceUrl"] = c["clerkUrl"]
        out[key] = entry

    if total < MIN_JUDGES:
        raise SystemExit("only %d judges across the bench (floor %d)" % (total, MIN_JUDGES))

    if len(fallbacks) > MAX_FALLBACK_JOINS:
        raise SystemExit(
            "%d judges joined their contact row by a fallback key (ceiling %d). "
            "That many means the exact surname+first-token key stopped matching "
            "— re-read both wicourts pages and fix the primary key rather than "
            "raising this number." % (len(fallbacks), MAX_FALLBACK_JOINS))

    with open(OUT, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, sort_keys=True)
    enriched = sum(1 for c in out.values() for j in c["judges"] if "phone" in j)
    print("wrote %s — %d circuits, %d judges (%d with a direct phone), %.0f KB"
          % (OUT, len(out), total, enriched, os.path.getsize(OUT) / 1024.0))
    # Every fallback join is PRINTED, because each one is this builder deciding
    # that two differently-written names are one judge. A reader of the weekly
    # run sees exactly which, and can say no.
    for ckey, bench_name, contact_name, why in sorted(fallbacks):
        print("  joined on %-10s %s = %s (%s)" % (why, bench_name, contact_name, ckey))
    for key, url in sorted(CLERK_URL_OVERRIDES.items()):
        upstream = circuits.get(key, {}).get("clerkUrl")
        if url is None:
            # A withheld link is the entry most likely to rot quietly: nothing
            # about it changes when the county's site comes back, so it says on
            # every run that this circuit ships no link and why to re-test.
            print("  override %s -> NO LINK (wicourts links %s, measured dead; "
                  "re-test that host and drop this entry when it answers)"
                  % (key, upstream))
        elif upstream == url:
            print("  override %s is now redundant — wicourts links %s; drop it"
                  % (key, url))
        else:
            print("  override %s -> %s (wicourts still links %s)" % (key, url, upstream))


if __name__ == "__main__":
    main()
