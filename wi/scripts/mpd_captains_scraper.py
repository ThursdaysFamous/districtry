#!/usr/bin/env python3
"""
MPD district captains scraper — the build the 2026-08-27 recon unlocked
(gap `mpd-district-leadership`).

WHY THIS RUNS FROM CI AND NOT FROM A DEVELOPMENT MACHINE: the phase-3
record said city.milwaukee.gov "refuses every automated client this
project can send", and that was true of every client the SANDBOX could
send — the WEC probe (2026-08-27) then measured the refusal
environment-side, and the recon captured the district pages PLAIN, HTTP
200, from a GitHub runner. This scraper therefore follows the
Johnson/Perry shape: the source is real, the vantage is the weekly
workflow's, and a local run in the development sandbox is EXPECTED to
fail its fetches.

THE PAGE STRUCTURE, measured from recon run 33036310501's captures:
each district page at city.milwaukee.gov/police/districts/District-<n>
carries an <h2> "MPD District <n>" followed by an <h3> with the
commanding officer — "Captain Robert S. Thiel" (D1), "Captain Raymond
Bratchett" (D3), and D2's measured trap: the heading renders "Captai n
Erin E. Mejia", markup splitting the word "Captain" itself, so the rank
pattern tolerates whitespace BETWEEN ANY TWO LETTERS of the rank word
and the parse is anchored to headings, never to a substring search of
the page. DISTRICT 4 IS THE SECOND MEASURED SHAPE (capture, run
33039934068): its officer heading is EMPTY (<h3>&nbsp;</h3>) and the
ranked name lives in the large-font paragraph link under the same
"MPD District 4" h2 — so when no h3 matches, the parse falls back to
that h2's own contact block (bounded at its first <hr>), still never
the page at large. The district index (/police/districts) and the city Directory
page (/Directory/police/Police-Districts.htm) are the witnesses: the
index must list all seven districts — it names them in H4 headings
("District One".."District Seven", measured), one level below anything
the district pages use, which cost the first dispatched run a refusal
of a healthy page — and the Directory's tel: links carry ONE phone per
district in the 414-935-72x2 block (measured: 7212..7272), paired by
the "District <n>" H2 each sits under.

HONESTY: a district whose heading parses no ranked name ships as null
(the card keeps its link-only behavior there) — never a guess; the
floor requires at least 6 of 7 named, and a name appearing under two
districts fails the run outright.

Usage:
    python3 wi/scripts/mpd_captains_scraper.py --out /tmp/mpd_captains.json
"""

import os
import argparse
import html as html_mod
import json
import re
import sys
import time
from datetime import datetime, timezone

import requests

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

BASE = "https://city.milwaukee.gov"
INDEX = BASE + "/police/districts"
DIRECTORY = BASE + "/Directory/police/Police-Districts.htm"
DISTRICT_URL = BASE + "/police/districts/District-%d"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}

ORDINALS = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five",
            6: "Six", 7: "Seven"}


def spaced(word):
    """'Captain' -> a pattern tolerating whitespace between any letters —
    District 2's page renders 'Captai n', the measured trap."""
    return r"\s*".join(re.escape(c) for c in word)


# rank first, tolerant; name after. Acting variants ride the same shape
# (the CPD precedent), and Inspector/Lieutenant are accepted so a command
# change doesn't silently drop a district to null.
RANK_RE = re.compile(
    r"^\s*(?P<rank>(?:%s\s+)?(?:%s|%s|%s|%s))\s+(?P<name>[A-Z][^<]{2,60}?)\s*$"
    % (spaced("Acting"), spaced("Captain"), spaced("Inspector"),
       spaced("Commander"), spaced("Lieutenant")),
    re.IGNORECASE)


def fetch(url, tries=3):
    last = None
    for attempt in range(tries):
        try:
            require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                                label="wi-mpd-captains-scraper")
            resp = requests.get(url, headers=HEADERS, timeout=45)
            if resp.status_code == 200:
                return resp.text
            last = "HTTP %d" % resp.status_code
        except requests.RequestException as e:
            last = str(e)[:200]
        time.sleep(1.5 * (attempt + 1))
    raise SystemExit("failed to fetch %s: %s (a fetch failure is EXPECTED "
                     "from the development sandbox — this scraper's vantage "
                     "is the weekly workflow's)" % (url, last))


def headings_of(html, tags=("h1", "h2", "h3")):
    out = []
    for tag in tags:
        for m in re.finditer(r"<%s[^>]*>([\s\S]*?)</%s>" % (tag, tag),
                             html, re.IGNORECASE):
            text = re.sub(r"\s+", " ",
                          html_mod.unescape(re.sub(r"<[^>]+>", " ",
                                                   m.group(1)))).strip()
            if text:
                out.append((tag, text))
    return out


def clean_rank(raw):
    # collapse the intra-word splits the rank pattern tolerated
    # ("Captai n" -> "Captain"; "Acting  Captain" -> "Acting Captain")
    collapsed = re.sub(r"\s+", "", raw)
    if collapsed.lower().startswith("acting"):
        return "Acting " + collapsed[len("acting"):].capitalize()
    return collapsed.capitalize()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    # ---- witness 1: the index must list all seven districts ----
    # the index names them in H4 headings (recon 33036310501's capture:
    # "h4: District One" .. "h4: District Seven") — the first dispatched
    # run read only h1-h3 and refused a healthy page, so h4 is explicit
    index_html = fetch(INDEX)
    index_heads = " ".join(
        t for _, t in headings_of(index_html, tags=("h1", "h2", "h3", "h4")))
    for n, word in ORDINALS.items():
        if not re.search(r"District\s+%s\b" % word, index_heads,
                         re.IGNORECASE):
            raise SystemExit("the district index no longer lists District "
                             "%s — the city reorganized; re-measure" % word)

    # ---- witness 2: the Directory's one-phone-per-district block ----
    dir_html = fetch(DIRECTORY)
    phones = {}
    # each "District N" h2 owns the tel: links that follow it, up to the next
    sections = re.split(r"(?i)(<h2[^>]*>\s*District\s+\d\s*</h2>)", dir_html)
    for i in range(1, len(sections) - 1, 2):
        # the district number is the one in "District <n>" — a bare first-digit
        # search reads the "2" of the "<h2" TAG and keys every phone to
        # district 2 (caught by the fixture test before any CI run shipped it)
        n = int(re.search(r"(?i)District\s+(\d)", sections[i]).group(1))
        m = re.search(r"""href=["']tel:\+?1?[-. ]?([\d\-. ()]{7,})""",
                      sections[i + 1], re.IGNORECASE)
        if m:
            digits = re.sub(r"\D", "", m.group(1))
            if len(digits) == 10:
                phones[n] = "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])
    if len(phones) < 6:
        print("Directory phone witness: only %d district phones parsed — "
              "phones ship where parsed, absence is not a failure"
              % len(phones), file=sys.stderr)

    # ---- the seven district pages ----
    out = {}
    names_seen = {}
    for n in range(1, 8):
        url = DISTRICT_URL % n
        html = fetch(url)
        heads = headings_of(html)
        # anchor: the page must be the district it claims to be
        if not any(re.search(r"District\s+%s\b" % ORDINALS[n], t,
                             re.IGNORECASE) for _, t in heads):
            raise SystemExit("%s does not carry a 'District %s' heading — "
                             "the page moved; re-measure" % (url, ORDINALS[n]))
        rank, name = None, None
        for tag, text in heads:
            if tag != "h3":
                continue
            m = RANK_RE.match(text)
            if m:
                rank = clean_rank(m.group("rank"))
                name = re.sub(r"\s+", " ", m.group("name")).strip()
                break
        if not name:
            # District 4's measured shape (capture, run 33039934068): the
            # officer heading exists and is EMPTY (<h3>&nbsp;</h3>), and the
            # ranked name sits in the large-font paragraph link under the
            # same "MPD District <n>" h2 — so this fallback scans ONLY the
            # contact block that h2 opens (up to its first <hr>), paragraph
            # by paragraph, never the whole page. "Captain's Office" cannot
            # match: the rank pattern requires whitespace then a capitalized
            # name after the rank word.
            block = re.search(r"(?i)<h2[^>]*>\s*MPD\s+District\s+%d\s*</h2>"
                              r"([\s\S]*?)<hr" % n, html)
            if block:
                for pm in re.finditer(r"<(?:p|a)[^>]*>([\s\S]*?)</(?:p|a)>",
                                      block.group(1), re.IGNORECASE):
                    text = re.sub(r"\s+", " ",
                                  html_mod.unescape(re.sub(r"<[^>]+>", " ",
                                                           pm.group(1)))).strip()
                    m = RANK_RE.match(text)
                    if m:
                        rank = clean_rank(m.group("rank"))
                        name = re.sub(r"\s+", " ", m.group("name")).strip()
                        break
        if name:
            if name in names_seen:
                raise SystemExit("%r appears under districts %d and %d — a "
                                 "template leak, not two commands; refuse"
                                 % (name, names_seen[name], n))
            names_seen[name] = n
        rec = {"district": str(n),
               "sourceUrl": url}
        if name:
            rec["rank"] = rank
            rec["name"] = name
        if n in phones:
            rec["phone"] = phones[n]
        out[str(n)] = rec
        print("District %d: %s" % (n, ("%s %s" % (rank, name)) if name
                                   else "NO RANKED NAME on the page — ships "
                                        "null, card keeps its link"),
              file=sys.stderr)

    named = sum(1 for r in out.values() if r.get("name"))
    if named < 6:
        raise SystemExit("only %d of 7 districts parsed a commanding "
                         "officer — the page structure moved; re-measure "
                         "before shipping" % named)

    doc = {"scrapedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "districts": out}
    with open(args.out, "w") as f:
        json.dump(doc, f, indent=1)
        f.write("\n")
    print("wrote %s — %d/7 named, %d phones" % (args.out, named, len(phones)),
          file=sys.stderr)


if __name__ == "__main__":
    main()
