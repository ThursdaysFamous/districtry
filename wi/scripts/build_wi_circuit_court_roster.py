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
and the page prints no "Br" for it.

WHAT THE 37 BRANCH-LESS JUDGES ACTUALLY ARE, measured 2026-09-12 (this
docstring said "24 of the 25" and the total was wrong; the 24 was right):
24 have a contact row whose branch is null — Richland's case, a fact about the
source rather than a failed join — and the other 13 have no contact row on the
page at all, so there is nothing to fail to match. Walworth's Scholz is in the
second group because the contact page spells her `SCHOLTZ`, which is the
deliberate non-join recorded below.

THREE FALLBACK RUNGS BELOW THE EXACT KEY, because the state's own two pages
write twelve of 261 judges' names differently and each was shipping with no
branch and no phone while both sat on the contact page:

  * SUFFIX (added 2026-09-12) — a generational suffix takes the surname's slot,
    because fold() makes the LAST token the surname: `Paul Bugenhagen Jr.` on
    the bench table against `Paul Bugenhagen Br 10` on the contact page keys as
    (jr, paul) against (bugenhagen, paul). Three judges shipped with no branch
    and no phone on that alone — Waukesha's Br 10, Jefferson's Br 3 and
    Milwaukee's Br 2. Keyed on the name with any trailing suffix dropped,
    computed for both sides so it works whichever page carries it.
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

All three rungs require the match to be UNIQUE ON BOTH SIDES — one contact row is
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

NOR IS A SUFFIX ALLOWED TO BRIDGE A GIVEN NAME AS WELL. Waukesha's Br 5 is
`Jack A. Melvin` on the contact page and `J. Arthur Melvin III` on the bench
table — two differences at once. Ignore the suffix in the given-name rung too
and both sides key on (melvin, j), and this builder would assert that two
differently-named people are one judge; they may be, and nothing published says
so. The suffix is dropped in its own rung only, and initial_key() says why it
does not drop it. `--selftest` asserts both halves on doctored input.

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
    two pages write differently at the same length as each other's.

    IT DOES NOT STRIP A GENERATIONAL SUFFIX, and that is the guard rather than
    an oversight: stripping here would let a suffix difference and a given-name
    difference compound, which is exactly Waukesha's Br 5 — the bench table's
    `J. Arthur Melvin III` against the contact page's `Jack A. Melvin`. Ignore
    the suffix and both sides key on (melvin, j), and this builder would assert
    that two differently-named people are one judge. They may be; nothing
    published says so.
    """
    parts = fold(name)
    if not parts or not parts[0]:
        return None
    return (parts[-1], parts[0][0])


# Generational suffixes as fold() leaves them (punctuation already gone, so
# `Jr.` and `, Jr.` both arrive as `jr`). Only these five are observed on the
# two wicourts pages; a sixth is added when a run prints a judge who needs it,
# never pre-emptively.
SUFFIXES = ("jr", "sr", "ii", "iii", "iv")


def suffix_key(name):
    """match_key with any trailing generational suffix dropped.

    fold() makes the LAST token the surname slot, so a suffix takes the
    surname's place and the exact key misses: the bench table writes
    `Paul Bugenhagen Jr.` and the contact page `Paul Bugenhagen`, which key as
    (jr, paul) and (bugenhagen, paul). Three judges shipped with no branch and
    no phone on that alone — Waukesha's Br 10, Jefferson's Br 3 and
    Milwaukee's Br 2 — while both pages named them.

    Computed for EVERY name, not only suffixed ones, so the rung works whichever
    side carries the suffix; for an unsuffixed name it equals match_key, which
    can only matter after the exact rung has already missed.
    """
    parts = fold(name)
    while len(parts) > 2 and parts[-1] in SUFFIXES:
        parts = parts[:-1]
    if len(parts) < 2:
        return None
    return (parts[-1], parts[0])


def join_circuit(bench, rows):
    """(entries, fallback joins) for one circuit's judges against its contact rows.

    Extracted from main() so the rules below can be asserted on doctored input
    (`--selftest`) rather than only on whatever the two live pages happen to say
    this week. The order of the rungs is the order of certainty: the exact key,
    then a suffix, then spacing, then a given name.

    EVERY FALLBACK REQUIRES THE MATCH TO BE UNIQUE ON BOTH SIDES. One matching
    contact row is not enough, because two judges of one bench sharing a key
    would each claim it. The NAME always comes from the bench table; a fallback
    attaches branch and phone and never changes a spelling.
    """
    enrich, by_solid, by_initial, by_suffix = {}, {}, {}, {}
    for row in rows:
        mk = match_key(row["name"])
        if mk and mk not in enrich:
            enrich[mk] = row
        sk = solid_key(row["name"])
        if sk:
            by_solid.setdefault(sk, []).append(row)
        ik = initial_key(row["name"])
        if ik:
            by_initial.setdefault(ik, []).append(row)
        xk = suffix_key(row["name"])
        if xk:
            by_suffix.setdefault(xk, []).append(row)

    bench_solid, bench_initial, bench_suffix = {}, {}, {}
    for j in bench:
        sk, ik, xk = solid_key(j["name"]), initial_key(j["name"]), suffix_key(j["name"])
        if sk:
            bench_solid[sk] = bench_solid.get(sk, 0) + 1
        if ik:
            bench_initial[ik] = bench_initial.get(ik, 0) + 1
        if xk:
            bench_suffix[xk] = bench_suffix.get(xk, 0) + 1

    entries, fallbacks = [], []
    for j in bench:
        mk = match_key(j["name"])
        row = enrich.get(mk) if mk else None
        if row is None:
            xk = suffix_key(j["name"])
            cand = by_suffix.get(xk, []) if xk else []
            if len(cand) == 1 and bench_suffix.get(xk) == 1:
                row = cand[0]
                fallbacks.append((j["name"], row["name"], "suffix"))
        if row is None:
            sk = solid_key(j["name"])
            cand = by_solid.get(sk, []) if sk else []
            if len(cand) == 1 and bench_solid.get(sk) == 1:
                row = cand[0]
                fallbacks.append((j["name"], row["name"], "spacing"))
        if row is None:
            ik = initial_key(j["name"])
            cand = by_initial.get(ik, []) if ik else []
            if len(cand) == 1 and bench_initial.get(ik) == 1:
                row = cand[0]
                fallbacks.append((j["name"], row["name"], "given name"))
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
        entries.append(entry)
    return entries, fallbacks


def _selftest():
    """The join rules, on doctored input — offline, stdlib only.

    Every case here is a real pair of spellings from the two wicourts pages, or
    the collision one of them would cause. A rule nothing exercises is a rule
    nobody can change safely, and the suffix rung was added to a builder whose
    join had no test at all.
    """
    def row(name, branch=None, phone=None):
        return {"name": name, "branch": branch, "phone": phone, "role": None}

    def one(bench_names, rows):
        bench = [{"name": n, "role": None} for n in bench_names]
        entries, joins = join_circuit(bench, rows)
        return {e["name"]: e for e in entries}, {b: why for b, _c, why in joins}

    failures = []

    def check(label, cond):
        if not cond:
            failures.append(label)

    # 1. The suffix on the BENCH side, which is the case that shipped three
    #    judges with no branch and no phone: Waukesha Br 10, Jefferson Br 3,
    #    Milwaukee Br 2.
    got, joins = one(["Paul Bugenhagen Jr."],
                     [row("Paul Bugenhagen", "10", "(262) 548-7454")])
    check("bugenhagen joins", got["Paul Bugenhagen Jr."].get("branch") == "10")
    check("bugenhagen phone", got["Paul Bugenhagen Jr."].get("phone") == "(262) 548-7454")
    check("bugenhagen reported", joins.get("Paul Bugenhagen Jr.") == "suffix")
    check("bugenhagen keeps the bench spelling",
          "Paul Bugenhagen Jr." in got and "Paul Bugenhagen" not in got)

    # 2. THE CASE THIS RUNG MUST NOT REACH. Waukesha Br 5 is `Jack A. Melvin`
    #    on the contact page and `J. Arthur Melvin III` on the bench table.
    #    Ignore the suffix AND the given name and both key on (melvin, j);
    #    ignore only the suffix and they do not match, which is the answer.
    got, joins = one(["J. Arthur Melvin III"], [row("Jack A. Melvin", "5", "(262) 548-7543")])
    check("melvin withheld", "branch" not in got["J. Arthur Melvin III"])
    check("melvin unjoined", "J. Arthur Melvin III" not in joins)

    # 3. The suffix on the CONTACT side instead — Iron writes
    #    `Anthony J. Stella, Jr.` where a bench table need not.
    got, joins = one(["Anthony J. Stella"], [row("Anthony J. Stella, Jr.", "1", "(715) 561-3434")])
    check("stella joins from the contact side", got["Anthony J. Stella"].get("branch") == "1")
    check("stella reported", joins.get("Anthony J. Stella") == "suffix")

    # 4. Both sides suffixed is the EXACT key and must not be reported as a
    #    fallback — Iron's real pair, which has always joined.
    got, joins = one(["Anthony J. Stella Jr."], [row("Anthony J. Stella, Jr.", None, "(715) 561-3434")])
    check("stella exact", got["Anthony J. Stella Jr."].get("phone") == "(715) 561-3434")
    check("stella not a fallback", not joins)
    check("no branch invented", "branch" not in got["Anthony J. Stella Jr."])

    # 5. Unique on BOTH sides. Two judges whose names differ only by suffix
    #    would each claim the one contact row, so neither may have it.
    got, joins = one(["Ann Reed Jr.", "Ann Reed Sr."], [row("Ann Reed", "4", "(555) 555-0100")])
    check("colliding suffixes withheld",
          "branch" not in got["Ann Reed Jr."] and "branch" not in got["Ann Reed Sr."])
    check("collision unreported", not joins)

    # 6. A surname a letter apart is still not bridged. Walworth's Br 1 is
    #    `Scholz` on the bench table and `SCHOLTZ` on the contact page.
    got, joins = one(["Estee Scholz"], [row("Estee Scholtz", "1", "(262) 741-7023")])
    check("scholz still withheld", "branch" not in got["Estee Scholz"])

    # 7. The two existing rungs still fire, so this change did not displace them.
    got, joins = one(["Martin J. De Vries"], [row("Martin J. DeVries", "2", "(920) 386-3570")])
    check("spacing rung intact", joins.get("Martin J. De Vries") == "spacing")
    got, joins = one(["Zach Wittchow"], [row("Zachary Wittchow", "6", "(262) 548-7584")])
    check("given-name rung intact", joins.get("Zach Wittchow") == "given name")

    # 8. A judge the contact page does not list at all ships name-only rather
    #    than dropping — Portage's Br 2 is absent from the contact page.
    got, joins = one(["Louis J. Molepske Jr."], [row("Michael D Zell", "1", "(715) 346-1364")])
    check("absent judge still ships", got["Louis J. Molepske Jr."] == {"name": "Louis J. Molepske Jr."})

    if failures:
        raise SystemExit("join selftest FAILED: " + "; ".join(failures))
    print("join selftest: 8 cases, all rules hold")


def main():
    if "--selftest" in sys.argv[1:]:
        _selftest()
        return
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
        rows = []
        courthouses = []
        for county in c["counties"]:
            block = contact.get(county_fold(county)) or {}
            rows.extend(block.get("branch_rows", []))
            for addr in block.get("addresses", []):
                # first line is the judicial-district label; keep the location
                lines = [ln for ln in addr if not ln.lower().endswith("judicial district")]
                if lines and {"county": county, "lines": lines} not in courthouses:
                    courthouses.append({"county": county, "lines": lines})
        judges, joined = join_circuit(c["judges"], rows)
        fallbacks.extend((key, bench_name, contact_name, why)
                         for bench_name, contact_name, why in joined)
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
