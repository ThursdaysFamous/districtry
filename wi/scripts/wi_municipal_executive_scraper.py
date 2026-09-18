#!/usr/bin/env python3
"""
Scrape Milwaukee County's 21-row municipal-executive layer and WITNESS every
name against the municipality's own page. Stage 1 of the pair;
build_wi_municipal_executives.py writes data/app/wi-municipal-executives.json.

WHY A WITNESS AND NOT A COPY. Milwaukee County GIS & Land Information
publishes `Milwaukee_County_Municipal_Executives`, which is the only source in
Wisconsin this project has found that names mayors and village presidents as
data. It is also STALE BY CONSTRUCTION for the purpose: its own
`dataLastEditDate` is 2024-07-30, and Wisconsin elects mayors and village
presidents every April of EVEN years (Wis. Stat. 8.11), so the April 2026
election fell between that edit and this build. Copying the layer's names
would publish a pre-election roster with a current-looking date on it.

So the layer supplies the SKELETON — which municipalities exist, their place
code, the office's own title, and the contact and link fields — and each
municipality's OWN page decides whether a NAME ships. That is the Coles County
rule (geometry from the service, people from the page) applied to a roster,
and the layer helpfully carries the page: every row has an `Exec_Url`.

WHAT WITNESSING MEANS HERE, stated exactly, because a loose test is worse than
none. The row's surname must appear on the fetched page AND within 220
characters of the word "mayor" or "president". Surname alone is not enough: a
village board page lists trustees too, and a former mayor is often named in
the same site's history. Measured 2026-09-03 across all 19 municipalities:

  WITNESSED (9)   Brown Deer, Fox Point, Franklin, Glendale, Greendale,
                  Greenfield, Shorewood, St. Francis, Whitefish Bay
  CONTRADICTED (2) Cudahy and West Milwaukee — the page fetches in full and
                  the layer's surname is not on it. That is the April 2026
                  election showing up, and it is exactly what the witness is
                  for.
  UNFETCHABLE (8) Bayside, Hales Corners, South Milwaukee and West Allis
                  return 404 FOR THE LAYER'S OWN LINK, which is corroborating
                  evidence of its age rather than a fetch problem at this end;
                  Milwaukee, Oak Creek, River Hills and Wauwatosa refuse this
                  client with 403. A refusal is an access control and is not
                  defeated here.

RE-MEASURED 2026-09-18, AND THE SPLIT HAS MOVED. The 2026-09-03 reading above
stands as what was true that day and is not edited; today the same nineteen
pages answer 9 witnessed, 2 contradicted (Cudahy and West Milwaukee, both still
reading in full) and 8 unfetchable — but as FIVE dead links and THREE refusals,
not four and four. OAK CREEK MOVED FROM 403 TO 404: its site stopped refusing
this client and now says the layer's page is not there, which is a different
fact about the county's link rather than about the city's door. Nothing here
carries a name for any of the eight, so the change costs nothing today; it is
recorded because a count in a docstring that nobody re-measures is how a
verdict table goes quietly wrong. Every one of the nineteen hosts ALLOWS the
path under its own robots.txt, read through scripts/robots_policy.py the same
day — three publish none, two answer 403 on robots.txt itself (the allow
default RFC 9309 gives a file it cannot read), and the remaining fourteen serve
a file that permits it.

A FAILED FETCH IS THREE ANSWERS, NOT ONE (2026-09-18). Those eight were pooled
under one `unreachable` status, and the builder now carries a previously
witnessed name across a fetch failure — so the three have to be told apart
before one of them licenses a carry. `refused` is the 403s, `missing` is the
404s, and `unreachable` is a server that did not answer at all, which is the
only one the builder may carry. The block above the `fetch` function carries
the reasoning; each verdict also gets its own withheld sentence, because "could
not be read" was standing in for all three on the card too.

TWENTY-ONE ROWS ARE NINETEEN MUNICIPALITIES. The City of Milwaukee appears
THREE times (Muni_Code 53000), one row per polygon part. Keying on rows rather
than on Muni_Code ships the same mayor three times and makes every count in
this file wrong by two; the dedupe is by code and the builder gates the
resulting count at 19.

Usage:
    python3 wi/scripts/wi_municipal_executive_scraper.py [--out PATH]
"""

import html
import json
import os
import re
import ssl
import sys
import time
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(SCRIPT_DIR, ".cache")
DEFAULT_OUT = os.path.join(CACHE_DIR, "wi_municipal_executives_raw.json")

# Full browser headers, not a bare UA: three of the four 403s in the first
# measurement were unchanged by richer headers, which is what makes them a
# refusal by the site rather than a thin-client rejection worth working around.
HDRS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Connection": "close",
}

LAYER = ("https://services2.arcgis.com/s1wgJQKbKJihhhaT/arcgis/rest/services/"
         "Milwaukee_County_Municipal_Executives/FeatureServer/42")
# The layer id is 42, not 0 — the FeatureServer publishes exactly one layer and
# numbers it 42. Guessing /0 returns "Invalid URL", which reads like a dead
# service rather than a wrong path.
LAYER_QUERY = LAYER + "/query?where=1%3D1&outFields=*&returnGeometry=false&f=json"

# One sentence per verdict, because "could not be read" was doing the work of
# three different answers on the card as well as in the carry rule.
WITHHELD_WHY = {
    "refused": "the municipality's own site refuses this client, so no name is "
               "witnessed",
    "missing": "the county layer's link to the municipality's page is dead, so "
               "no name is witnessed",
    "unreachable": "the municipality's own page could not be read from here, so "
                   "no name is witnessed",
}

EXPECT_MUNIS = 19          # Milwaukee County's incorporated municipalities
WITNESS_WINDOW = 220       # characters either side of the surname
OFFICE_WORDS = re.compile(r"(?i)\b(mayor|president)\b")


def fail(msg):
    print("wi-municipal-executive-scraper: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


# WHY A FAILED FETCH IS THREE VERDICTS AND NOT ONE. The builder carries a
# previously witnessed name forward across a fetch failure, and the Iowa chair
# rule that governs every carry in this fleet says CARRY ONLY WHERE WE COULD NOT
# ASK. Until 2026-09-18 every failure here read `unreachable`, which pooled a
# site refusing this client, a link that is simply gone, and a network that did
# not answer — three different facts with three different answers:
#
#   refused      401, 403 or a 429 that survived its backoff. An access control.
#                A carried copy would be the site's data kept alive against its
#                refusal, which is the one thing a carry must never do.
#   missing      404 or 410. THE SITE ANSWERED: there is no such page. That is a
#                real change in what the municipality publishes, and the four
#                dead `Exec_Url` values are how the layer's 2024 vintage shows.
#   unreachable  everything else — a timeout, a reset, DNS, a 5xx. The server
#                did not answer the question, so nothing was learnt this run and
#                last week's witness is still the best available statement.
#
# Only `unreachable` is carryable. The two definitive refusals are also not
# retried: a 403 and a 404 do not become a page on the second ask, and three
# rounds of them is noise on somebody's access log.
DEFINITIVE = frozenset([401, 403, 404, 410])
REFUSED_CODES = frozenset([401, 403, 429])
MISSING_CODES = frozenset([404, 410])


def classify(exc):
    """`refused`, `missing` or `unreachable` for the exception that ended a fetch."""
    code = getattr(exc, "code", None)
    if code in REFUSED_CODES:
        return "refused"
    if code in MISSING_CODES:
        return "missing"
    return "unreachable"


def fetch(url, tries=3, timeout=45):
    """(text, None, "read") or (None, reason, verdict). Never raises for a
    per-municipality miss: a page we cannot read is a WITHHELD name, which is a
    result, not a crash. The verdict is what decides whether the builder may
    carry last week's name — see the comment above."""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HDRS)
            with urllib.request.urlopen(req, timeout=timeout,
                                        context=ssl.create_default_context()) as r:
                return r.read().decode("utf-8", "replace"), None, "read"
        except Exception as e:                   # noqa: BLE001 - reported per row
            last = e
            if getattr(e, "code", None) in DEFINITIVE:
                break
            if i + 1 < tries:
                time.sleep(2 * (i + 1))
    return None, "%s: %s" % (type(last).__name__, str(last)[:90]), classify(last)


def page_text(page):
    page = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
    page = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h[1-6]|tr|td)>", "\n", page)
    return re.sub(r"[ \t]+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))


def surname_of(name):
    """The last alphabetic token. 'Michael J. Neitzke' -> 'Neitzke'; a trailing
    suffix is kept out of the way because the layer carries none today and a
    bare 'Jr' would witness against half a village's site."""
    parts = [p for p in re.split(r"\s+", (name or "").strip()) if re.search(r"[A-Za-z]{2}", p)]
    return parts[-1].strip(",.") if parts else ""


def witness(text, name):
    """(witnessed, why). Surname near an office word, or a stated reason."""
    sur = surname_of(name)
    if not sur:
        return False, "the layer names no executive for this municipality"
    hits = list(re.finditer(r"(?i)\b%s\b" % re.escape(sur), text))
    if not hits:
        return False, ("the municipality's own page does not name %s — the layer's "
                       "name predates the April 2026 election" % sur)
    for m in hits:
        window = text[max(0, m.start() - WITNESS_WINDOW): m.start() + WITNESS_WINDOW]
        if OFFICE_WORDS.search(window):
            return True, None
    return False, ("the municipality's own page names %s but not beside the words "
                   "mayor or president, so it does not witness the office" % sur)


def main():
    argv = sys.argv[1:]
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT

    body, err, _ = fetch(LAYER_QUERY)
    if body is None:
        fail("the county's municipal-executive layer did not answer (%s)" % err)
    try:
        rows = json.loads(body)["features"]
    except (ValueError, KeyError) as e:
        fail("the layer's answer did not parse as features (%s)" % e)
    if not rows:
        fail("the layer returned zero rows")

    # 21 rows -> 19 municipalities; see the module docstring.
    by_code = {}
    for f in rows:
        a = f.get("attributes") or {}
        code = (a.get("Muni_Code") or "").strip()
        if not code:
            continue
        by_code.setdefault(code, []).append(a)
    if len(by_code) != EXPECT_MUNIS:
        fail("the layer deduped to %d municipalities, expected %d — Milwaukee "
             "County's municipal fabric changed, or Muni_Code stopped being the "
             "key" % (len(by_code), EXPECT_MUNIS))
    print("  layer: %d rows -> %d municipalities" % (len(rows), len(by_code)),
          file=sys.stderr)

    out = {}
    for code, group in sorted(by_code.items(), key=lambda kv: kv[1][0].get("Muni_Name") or ""):
        a = group[0]
        muni = (a.get("Muni_Name") or "").strip()
        name = (a.get("Exec_Name") or "").strip()
        office = (a.get("Exec_Descrip") or "").strip()
        url = (a.get("Exec_Url") or "").strip()
        # The layer writes e-mail as a mailto: href with a ?subject= tail.
        raw_mail = (a.get("Email_Addr") or "").strip()
        mail = re.sub(r"(?i)^mailto:", "", raw_mail).split("?")[0].strip() or None
        phone = (a.get("Phone_Nbr") or "").strip() or None

        rec = {
            "municipality": muni,
            "muniType": (a.get("MuniType") or "").strip() or None,
            "office": office or None,
            "layerName": name or None,
            "pageUrl": url or None,
            "layerEmail": mail,
            "layerPhone": phone,
            "rowsInLayer": len(group),
        }
        if not url:
            rec.update(witnessed=False, pageStatus="no-url",
                       withheldWhy="the layer publishes no page for this municipality")
            out[code] = rec
            print("  %-18s %-22s NO URL" % (muni, name), file=sys.stderr)
            continue
        page, err, verdict = fetch(url)
        if page is None:
            rec.update(witnessed=False, pageStatus=verdict, fetchError=err,
                       withheldWhy=WITHHELD_WHY[verdict])
            out[code] = rec
            print("  %-18s %-22s %-11s %s"
                  % (muni, name, verdict.upper(), err[:44]), file=sys.stderr)
            continue
        ok, why = witness(page_text(page), name)
        rec.update(witnessed=ok, pageStatus="read", pageBytes=len(page))
        if not ok:
            rec["withheldWhy"] = why
        out[code] = rec
        print("  %-18s %-22s %s" % (muni, name, "WITNESSED" if ok else "withheld"),
              file=sys.stderr)

    n_ok = sum(1 for r in out.values() if r["witnessed"])
    payload = {
        "source": LAYER,
        "sourceName": "Milwaukee County GIS & Land Information",
        "municipalities": out,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    print("wi-municipal-executive-scraper: OK — %d municipalities, %d name(s) "
          "witnessed on the municipality's own page, %d withheld -> %s"
          % (len(out), n_ok, len(out) - n_ok, out_path), file=sys.stderr)


if __name__ == "__main__":
    main()
