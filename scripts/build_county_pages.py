#!/usr/bin/env python3
"""
One crawlable page per Illinois county board, naming every member.

WHY THIS EXISTS. Measured 2026-09-13: across all 51 authored HTML pages on
this site, NOT ONE OFFICEHOLDER NAME appears. The rosters are real — 799 seats
across 54 districted counties, 104 commissioners across 20 at-large ones, every
seat named, most with an e-mail and a phone — and every one of them reaches a
reader only after JavaScript fetches a JSON file and renders a card. A crawler
sees a map and a toggle list. So the site that knows who represents 903 seats
publishes that fact nowhere a search engine can read it, and someone typing
"who is on the LaSalle County board" is answered by everyone except the
project built to answer it.

WHY A PAGE PER COUNTY AND NOT PER DISTRICT. The obvious reading is one page per
seat, which is 903 of them. Two reasons not to: the queries people actually
type are county-level far more often than district-level, and a page whose
whole content is one name and a phone number is the shape search engines treat
as thin. A county page carries every name in the county — the same crawlable
text at a fraction of the page count, with an anchor per district so a link to
one seat still lands on it. Per-district pages remain possible later; this
decides nothing against them.

WHAT IS ON A PAGE, AND WHAT IS NOT. Everything comes from the shipped roster
the app itself reads, so the page and the card cannot disagree — that is the
point of generating it rather than writing it. A field the roster does not
carry is absent from the page rather than blank: no "email: —", no invented
office. A district the roster leaves empty says so in the app's own words
rather than being skipped, because a board of eighteen showing seventeen seats
reads as complete and is not. Nothing here is guessed, and nothing is
reformatted beyond escaping.

TWO ROSTER SHAPES, both handled:

  * DISTRICTED (54 counties): il/data/app/<slug>-county-board-members.json,
    keyed by district, each `{members: [...], sourceUrl}`. Surveyed key by key
    on introduction rather than assumed, because three shapes share that file
    name. Eleven files carry a per-county EXTRA beside the district keys (an
    office address, a clerk phone, a meeting time, a results URL) — a flat
    record with no `members` and no `name`, skipped, counted on every run.
    Five carry a `chair` key: a flat record that DOES name a person, the board
    chair, who gets a section of their own; skipping it as "not a district"
    would have dropped five real officeholders, which is what the survey was
    for. One file, Winnebago's, is flat for every one of its twenty districts
    and names nobody at all — see NAMES_NOBODY.
  * AT LARGE (20 counties): il/data/app/il-county-commissioners.json, keyed by
    the county in caps, carrying `members`, `structure` and `verified`. These
    pages say outright that the county elects countywide and has no districts,
    which is a fact worth publishing on its own: it is the answer to "what
    district am I in" for a fifth of the counties this app serves.

THE COUNTY NAME AND SLUG ARE NOT A NEW TABLE. Both come from
build_county_status.py's ALL_COUNTIES and slug_of(), which the county-status
page and the coverage ring already use. Measured on introduction: all 54
roster filenames and all 20 at-large keys resolve against that list exactly,
with nothing left over on either side. A roster file this script cannot place
is a failure, not a skip.

  python3 scripts/build_county_pages.py            # (re)generate in place
  python3 scripts/build_county_pages.py --check    # the CI drift gate
"""

import glob
import json
import os
import re
import sys
import urllib.parse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_landing_page import (  # noqa: E402
    FAVICON, FONTFACE, TOKENS, parse_token_block, read, token_css,
)
from build_privacy_page import (  # noqa: E402
    DARK_EXTRA, DARK_TOKENS, LIGHT_TOKENS, esc, fail,
)
from build_history_page import shared_footer_byline  # noqa: E402
from build_county_status import ALL_COUNTIES, slug_of  # noqa: E402

# A county whose shipped roster names NOBODY. A page for it would be a page
# about a county board with no officeholder on it, which is the opposite of
# why these pages exist — and it would fail this work's own test that a
# generated URL names someone. Recorded with what the roster does carry, and
# re-audited: the moment the roster starts naming people the entry is stale
# and the build fails, which is the property ACCEPTED_DROPS had to be given
# after the fact.
NAMES_NOBODY = {
    "Winnebago": dict(
        date="2026-09-13",
        reason="all 20 district keys are flat records carrying an e-mail, a "
               "phone and the county's source URL, and no name field anywhere "
               "in the file. The county publishes per-district contact details "
               "rather than a member list; wincoil.gov's board page is the "
               "roster and nothing here parses names out of it yet.",
    ),
}

INST = "il"
CONCEPT = "county-board"
OUT_DIR = os.path.join(REPO_ROOT, INST, CONCEPT)
APP_DATA = os.path.join(REPO_ROOT, INST, "data", "app")
APP_URL = "https://districtry.com/il/"
APP_NAME = "districtry Illinois"
COMMISSIONERS = os.path.join(APP_DATA, "il-county-commissioners.json")
# The topic page carries the index of these pages, in a region this builder
# owns. Without it the 73 pages are orphans: nothing on the site links them, so
# a crawler reaching the sitemap finds pages with no path in, which is the
# weakest possible position for exactly the pages this work exists to rank.
# generate_metro_files.py leaves a region it has no target for alone (checked),
# so two builders owning regions in one file is the pattern sources.html
# already uses rather than a new one.
INDEX_PAGE = os.path.join(REPO_ROOT, INST, "county-board.html")
INDEX_REGION = "county-index"

NAME_BY_SLUG = {slug_of(n): n for n, _ in ALL_COUNTIES}
NAME_BY_UPPER = {n.upper(): n for n, _ in ALL_COUNTIES}


def district_sort_key(key):
    """Districts are '1'..'30' in most counties and letters ('A'..'N') in Clay.
    Sort numerics numerically and letters after them, so a page reads 1, 2, 10
    rather than 1, 10, 2."""
    return (0, int(key), "") if key.isdigit() else (1, 0, key)


def load_districted():
    """-> ({county name: {...}}, problems, {county name that names nobody})"""
    out, problems, nameless = {}, [], set()
    for path in sorted(glob.glob(os.path.join(APP_DATA, "*-county-board-members.json"))):
        slug = os.path.basename(path).replace("-county-board-members.json", "")
        name = NAME_BY_SLUG.get(slug)
        if name is None:
            problems.append(
                "%s names county slug %r, which build_county_status.ALL_COUNTIES "
                "does not carry — the two lists have diverged"
                % (os.path.relpath(path, REPO_ROOT), slug))
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        districts, skipped, source, chair = [], [], None, None
        for key in sorted(data, key=district_sort_key):
            entry = data[key]
            if not isinstance(entry, dict):
                skipped.append(key)
                continue
            source = source or entry.get("sourceUrl")
            if isinstance(entry.get("members"), list):
                districts.append((key, entry["members"]))
            elif (entry.get("name") or "").strip():
                # A flat record that names someone: the board chair in all five
                # files that carry one. Not a district, and not an extra either.
                chair = dict(entry)
                chair.setdefault("role", "Chair")
            else:
                skipped.append(key)          # a per-county extra, not a district
        named = sum(1 for _, ms in districts
                    for m in ms if (m.get("name") or "").strip())
        named += 1 if chair else 0
        if not named:
            # No page: it would name nobody. Must be recorded, not silent.
            if name not in NAMES_NOBODY:
                problems.append(
                    "%s names nobody — %d key(s), no name field on any of them. "
                    "Either the roster regressed, or this county belongs in "
                    "NAMES_NOBODY with a reason"
                    % (os.path.relpath(path, REPO_ROOT), len(data)))
            nameless.add(name)
            continue
        out[name] = {"districts": districts, "sourceUrl": source, "chair": chair,
                     "skipped": skipped, "slug": slug}
    return out, problems, nameless


def load_at_large():
    with open(COMMISSIONERS, encoding="utf-8") as f:
        data = json.load(f)
    out, problems = {}, []
    for key, entry in sorted(data.items()):
        name = NAME_BY_UPPER.get(key)
        if name is None:
            problems.append(
                "il-county-commissioners.json names %r, which "
                "build_county_status.ALL_COUNTIES does not carry" % key)
            continue
        out[name] = {"members": entry.get("members", []),
                     "structure": entry.get("structure"),
                     "verified": entry.get("verified"),
                     "sourceUrl": entry.get("sourceUrl"),
                     "sourceDocument": entry.get("sourceDocument"),
                     "seats": entry.get("seats"),
                     "slug": slug_of(name)}
    return out, problems


def member_html(m):
    """One member. Every field is optional and an absent one is absent from the
    markup — a roster that does not publish a phone must not render an empty
    row that reads as one."""
    name = (m.get("name") or "").strip()
    if not name:
        return None
    bits = ['<span class="m-name">%s</span>' % esc(name)]
    role = (m.get("role") or "").strip()
    if role:
        bits.append('<span class="m-role">%s</span>' % esc(role))
    contact = []
    email = (m.get("email") or "").strip()
    if email:
        contact.append('<a href="mailto:%s">%s</a>' % (esc(email), esc(email)))
    phone = (m.get("phone") or "").strip()
    if phone:
        contact.append('<a href="tel:%s">%s</a>'
                       % (esc(re.sub(r"[^0-9+]", "", phone)), esc(phone)))
    url = (m.get("url") or "").strip()
    if url.startswith("http"):
        contact.append('<a href="%s" rel="noopener" target="_blank">Official profile</a>'
                       % esc(url))
    if contact:
        bits.append('<span class="m-contact">%s</span>' % " · ".join(contact))
    return '<li class="member">%s</li>' % "".join(bits)


def districted_body(name, rec):
    seats = sum(len(ms) for _, ms in rec["districts"])
    named = sum(1 for _, ms in rec["districts"] for m in ms if (m.get("name") or "").strip())
    chair_named = 1 if rec.get("chair") else 0
    n_dist = len(rec["districts"])
    out = []
    out.append(
        '<p class="lede">The %s County Board is elected by district. This page '
        'lists %s %s and the %s who %s them, exactly as the county publishes '
        'them — it is the same roster the map\'s county board card reads.</p>'
        % (esc(name), n_dist, "district" if n_dist == 1 else "districts",
           "member" if named == 1 else "%d members" % named,
           "holds" if named == 1 else "hold"))
    out.append('<a class="cta" href="../#layers=county-board,county">'
               'Find your %s County district on the map →</a>' % esc(name))
    out.append('<p class="cta-note">Opens the map with the county and county board '
               'layers on. Search your address or ZIP, or tap your location.</p>')
    chair = rec.get("chair")
    if chair:
        row = member_html(chair)
        if row:
            out.append('<section class="district" id="chair">')
            out.append('<h2>Board chair</h2>')
            out.append('<ul class="members">%s</ul>' % row)
            out.append('</section>')
    for label, members in rec["districts"]:
        anchor = "district-%s" % re.sub(r"[^A-Za-z0-9]+", "-", label).lower()
        out.append('<section class="district" id="%s">' % esc(anchor))
        out.append('<h2>District %s</h2>' % esc(label))
        rows = [h for h in (member_html(m) for m in members) if h]
        if rows:
            out.append('<ul class="members">%s</ul>' % "".join(rows))
        else:
            # The app's own wording for a seat its source does not name. A
            # district dropped from the page would read as a board of n-1.
            out.append('<p class="unlisted">Not listed in the county\'s '
                       'directory.</p>')
        out.append('</section>')
    if seats != named:
        out.append('<p class="unlisted">%d of %d seats are not named by the '
                   'county\'s own source.</p>' % (seats - named, seats))
    return "\n".join(out), n_dist, named + chair_named


def at_large_body(name, rec):
    members = rec["members"]
    named = sum(1 for m in members if (m.get("name") or "").strip())
    out = []
    out.append(
        '<p class="lede">%s County elects its board <b>at large</b> — every '
        'member is chosen countywide, so there are no board districts to be in. '
        'These %s represent the whole county.</p>'
        % (esc(name), "is the one member who represents" if named == 1
           else "%d members" % named))
    if rec.get("structure"):
        out.append('<p class="structure">%s</p>' % esc(rec["structure"]))
    rows = [h for h in (member_html(m) for m in members) if h]
    out.append('<section class="district" id="members">')
    out.append('<h2>Members</h2>')
    out.append('<ul class="members">%s</ul>' % "".join(rows) if rows else
               '<p class="unlisted">Not listed in the county\'s directory.</p>')
    out.append('</section>')
    if rec.get("seats") and rec["seats"] > named:
        out.append('<p class="unlisted">%d of %d seats are not named by the '
                   'county\'s own source.</p>' % (rec["seats"] - named, rec["seats"]))
    out.append('<a class="cta" href="../#layers=county">'
               'See %s County on the map →</a>' % esc(name))
    out.append('<p class="cta-note">Opens the map with the county layer on. An '
               'at-large board has no district geometry, so the members above '
               'are the answer for anywhere in the county.</p>')
    return "\n".join(out), 0, named


def source_note(rec, at_large):
    """Where the names came from, in the page's own words. A page that names
    people without saying who published them is the thing this project refuses
    everywhere else."""
    bits = []
    if at_large:
        if rec.get("sourceDocument"):
            bits.append("Source: %s." % esc(rec["sourceDocument"]))
        elif rec.get("sourceUrl"):
            bits.append('Source: <a href="%s" rel="noopener" target="_blank">the '
                        "county's own published roster</a>." % esc(rec["sourceUrl"]))
        if rec.get("verified"):
            bits.append("Verified %s." % esc(rec["verified"]))
    elif rec.get("sourceUrl"):
        bits.append('Source: <a href="%s" rel="noopener" target="_blank">the '
                    "county's own published roster</a>, re-read on a schedule "
                    "and landed as a reviewed pull request." % esc(rec["sourceUrl"]))
    if not bits:
        return ""
    return '<p class="source-note">%s</p>' % " ".join(bits)


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>%(title)s</title>
<meta name="description" content="%(desc)s" />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="%(canonical)s" />
<link rel="icon" href="%(favicon)s" type="image/svg+xml" />
<meta property="og:type" content="article" />
<meta property="og:site_name" content="%(app_name)s" />
<meta property="og:title" content="%(title)s" />
<meta property="og:description" content="%(desc)s" />
<meta property="og:url" content="%(canonical)s" />
<meta property="og:image" content="%(og_image)s" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:locale" content="en_US" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="%(title)s" />
<meta name="twitter:description" content="%(desc)s" />
<meta name="twitter:image" content="%(og_image)s" />
<!-- GENERATED by scripts/build_county_pages.py from the shipped roster this
     county's own card reads. Do NOT hand-edit: `--check` fails the build, and
     a hand edit here would make the page and the card disagree about a real
     person. Fix the roster, or the scraper that writes it. -->
<script>
(function () {
  try {
    var stored = localStorage.getItem("districtry-theme");
    if (stored === "dark" || stored === "light") {
      document.documentElement.setAttribute("data-theme", stored);
    }
  } catch (e) { /* blocked storage — prefers-color-scheme decides */ }
})();
</script>
<style>
%(fontface)s

:root {
  color-scheme: light dark;
%(light)s
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
%(dark)s
  }
}
:root[data-theme="dark"] {
%(dark)s
}

* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font: 400 16px/1.6 var(--font-body);
  -webkit-text-size-adjust: 100%%;
}
a { color: var(--brand-700); }
:focus-visible { outline: 3px solid var(--brand-600); outline-offset: 2px; }

/* Focus-only, and the pair validate_contrast.py measures as (paper, ink):
   16.08:1 light and 15.36:1 dark. */
.skip-link {
  position: absolute; left: -9999px; top: 0;
  background: var(--ink); color: var(--paper);
  padding: 10px 16px; z-index: 10; border-radius: 0 0 6px 0;
}
.skip-link:focus { left: 0; }

main { max-width: 760px; margin: 0 auto; padding: 40px 20px 64px; }
.kicker {
  font: 600 13px/1 var(--font-body); letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--muted); margin: 0 0 10px;
}
.kicker a { color: inherit; text-decoration: none; }
h1 {
  font: var(--font-heading-weight, 700) clamp(26px, 5vw, 34px)/1.15 var(--font-heading);
  margin: 0 0 6px; text-transform: uppercase; letter-spacing: 0.01em;
}
.title-sub { color: var(--ink-3); margin: 0 0 18px; font-size: 15px; }
.lede { color: var(--ink-2); margin: 0 0 16px; }
.structure {
  font-size: 14px; color: var(--muted); border-left: 3px solid var(--brand-border);
  padding: 2px 0 2px 12px; margin: 0 0 16px;
}
.cta {
  display: inline-block; margin: 6px 0 4px; padding: 11px 18px;
  background: var(--brand-700); color: var(--paper);
  border-radius: var(--radius-btn); font-weight: 600; text-decoration: none;
}
.cta:hover { background: var(--brand-600); }
.cta-note { font-size: 13px; color: var(--muted); margin: 6px 0 26px; }

.district { margin: 0 0 6px; padding: 14px 0 2px; border-top: 1px solid var(--border); }
.district h2 {
  font: var(--font-heading-weight, 700) 19px/1.2 var(--font-heading);
  margin: 0 0 8px; text-transform: uppercase; letter-spacing: 0.02em;
}
.members { list-style: none; margin: 0; padding: 0; }
.member { margin: 0 0 12px; }
.m-name { display: block; font-weight: 650; }
.m-role { display: block; font-size: 13px; color: var(--muted); }
/* line-height 28px, the WCAG 2.5.8 spacing floor the landing and history
   footers were fixed to on 2026-09-13: these are 13.5px links that wrap. */
.m-contact { display: block; font-size: 13.5px; line-height: 28px; }
.unlisted { color: var(--muted); font-size: 14px; margin: 0 0 12px; }
.source-note {
  margin: 22px 0 0; padding: 12px 14px; font-size: 13.5px; color: var(--ink-3);
  background: var(--surface-2); border-radius: var(--radius-card);
}
.disclaimer { font-size: 13px; color: var(--muted); margin: 14px 0 0; }
.foot {
  margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--border);
  font-size: 14px; line-height: 28px; color: var(--muted);
}
.foot a { margin-right: 14px; }
</style>
<script type="application/ld+json">
%(jsonld)s
</script>
</head>
<body>
<a href="#page-main" class="skip-link">Skip to content</a>
<main id="page-main">
<p class="kicker">%(mark)s<a href="../">districtry / illinois</a></p>
<h1>%(h1)s</h1>
<p class="title-sub">%(standfirst)s</p>
%(body)s
%(source)s
<p class="disclaimer">districtry is an independent, unofficial civic reference.
It never guesses at who holds a seat: every name above is published by the
county itself, and where a county publishes none this page says so rather than
filling the gap.</p>
<p class="foot">
<a href="../county-board.html">All Illinois county boards</a>
<a href="../">Back to the map</a>
<a href="../sources.html">Sources &amp; data layers</a>
<a href="../faq.html">Common questions</a>
<a href="../../privacy.html">Privacy</a>
<a href="https://overberg.co/why/" target="_blank" rel="noopener">Why this exists</a>
</p>
%(byline)s
</main>
</body>
</html>
"""


def mark_svg():
    """The same inline mark the history pages carry, read from the one file."""
    svg = read(FAVICON, "the brand mark").strip()
    svg = svg.replace("<svg ", '<svg class="districtry-mark" width="18" height="18" '
                               'aria-hidden="true" style="vertical-align:-3px;'
                               'margin-right:6px" ', 1)
    return svg


def build_page(name, rec, at_large, shell):
    slug = rec["slug"]
    canonical = "%s%s/%s.html" % (APP_URL, CONCEPT, slug)
    body, n_dist, named = (at_large_body(name, rec) if at_large
                           else districted_body(name, rec))[:3]
    title = "%s County Board members — %s" % (name, APP_NAME)
    if at_large:
        desc = ("Who sits on the %s County Board: %d members elected at "
                "large across the whole county, with contact details, from the "
                "county's own published roster." % (name, named))
    else:
        # `named` counts the chair, who is NOT one of the district members in
        # any of the five counties that publish one (checked: no chair's name
        # appears in that county's own district list). So the description says
        # the district figure and names the chair separately rather than
        # printing a total the page never shows.
        chair = 1 if rec.get("chair") else 0
        # 155 characters is the gate's ceiling (scripts/validate_serp_lengths.py)
        # and the longest county name plus the longest suffix ran to 160, so
        # the contact clause goes rather than the counts, which are what make
        # one of these 73 descriptions different from the next.
        desc = ("Who represents you on the %s County Board — %d members across "
                "%d districts%s, from the county's own published roster."
                % (name, named - chair, n_dist,
                   " plus the elected chair" if chair else ""))
    standfirst = ("Every member of the %s County Board, from the county's own "
                  "published roster." % name)

    graph = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": canonical,
        "url": canonical,
        "name": title,
        "description": desc,
        "inLanguage": "en-US",
        "about": {"@type": "GovernmentOrganization",
                  "name": "%s County Board" % name,
                  "areaServed": {"@type": "AdministrativeArea",
                                 "name": "%s County, Illinois" % name}},
        "author": {
            "@type": "Person",
            "@id": "https://districtry.com/#author",
            "name": "Adam Overberg",
            "url": "https://overberg.co",
            "email": "hello@overberg.co",
        },
        "isPartOf": {"@id": APP_URL + "#website"},
        "breadcrumb": {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": APP_NAME,
                 "item": APP_URL},
                {"@type": "ListItem", "position": 2,
                 "name": "County boards", "item": APP_URL + "county-board.html"},
                {"@type": "ListItem", "position": 3,
                 "name": "%s County" % name},
            ],
        },
    }
    jsonld = json.dumps(graph, indent=2, ensure_ascii=False).replace("</", "<\\/")

    return PAGE % dict(
        shell,
        title=esc(title), desc=esc(desc), canonical=esc(canonical),
        h1=esc("%s County Board" % name), standfirst=esc(standfirst),
        body=body, source=source_note(rec, at_large), jsonld=jsonld,
        og_image=esc(APP_URL + "og-image.png"), app_name=esc(APP_NAME),
    )


def render_index(rows):
    """rows: [(county name, slug, at_large, seats)] — the index the topic page
    carries. Alphabetical, one flat list: a reader looking for their county
    scans a name, and a crawler gets 73 internal links from a page that already
    ranks for the concept."""
    out = ['    <p class="matrix-lede">Every Illinois county whose board roster this '
           'project has: <b>%d counties</b>, <b>%d people</b>, each name published by '
           'the county itself. %d elect their boards at large, with no districts.</p>'
           % (len(rows), sum(r[3] for r in rows), sum(1 for r in rows if r[2])),
           '    <ul class="county-index">']
    for name, slug, at_large, seats in rows:
        out.append('      <li><a href="county-board/%s.html">%s County</a> '
                   '<span class="county-index-n">%d %s%s</span></li>'
                   % (esc(slug), esc(name), seats,
                      "member" if seats == 1 else "members",
                      ", at large" if at_large else ""))
    out.append("    </ul>")
    return "\n".join(out)


def write_index(rows, check):
    """Splice render_index() into the topic page's GENERATED region."""
    with open(INDEX_PAGE, encoding="utf-8", newline="") as f:
        text = f.read()
    begin = "<!-- ==== GENERATED:BEGIN %s ==== -->" % INDEX_REGION
    end = "<!-- ==== GENERATED:END %s ==== -->" % INDEX_REGION
    if begin not in text or end not in text:
        fail("%s carries no GENERATED region %r — the index has nowhere to go"
             % (os.path.relpath(INDEX_PAGE, REPO_ROOT), INDEX_REGION))
    head, rest = text.split(begin, 1)
    _, tail = rest.split(end, 1)
    new = head + begin + "\n" + render_index(rows) + "\n    " + end + tail
    if new == text:
        return False
    if not check:
        with open(INDEX_PAGE, "w", encoding="utf-8", newline="") as f:
            f.write(new)
    return True


def roster_names(rec, at_large):
    """Every person the roster names for this county, chair included."""
    names = []
    if at_large:
        names += [m.get("name") for m in rec["members"]]
    else:
        names += [m.get("name") for _, ms in rec["districts"] for m in ms]
        if rec.get("chair"):
            names.append(rec["chair"].get("name"))
    return [n.strip() for n in names if (n or "").strip()]


def verify_page(name, rec, at_large, html):
    """The check this work exists to pass: the page NAMES THE PEOPLE.

    Byte-equality against a regenerate already proves the page matches the
    template. It cannot prove the template puts the roster on the page — a
    generator that emitted a beautiful, correct, empty page would pass it every
    time. So this reads the shipped HTML back and asserts, per county, that
    every name in the roster appears in it and that at least one does.

    Names are compared HTML-ESCAPED, because that is what is on the page:
    O'Brien ships as O&#x27;Brien, and comparing the raw name would report a
    real, present officeholder as missing.
    """
    problems = []
    names = roster_names(rec, at_large)
    if not names:
        return ["%s: the page names nobody" % name]
    missing = [n for n in names if esc(n) not in html]
    if missing:
        problems.append(
            "%s: %d roster name(s) do not appear on the page it generated — %s"
            % (name, len(missing), ", ".join(missing[:4])))
    # Every district heading, too: a district dropped from the page reads to a
    # reader as a board one seat smaller than it is.
    if not at_large:
        for label, _ in rec["districts"]:
            if ("<h2>District %s</h2>" % esc(label)) not in html:
                problems.append("%s: district %s has no section on its page"
                                % (name, label))
    return problems


WORKFLOW_DIR = os.path.join(REPO_ROOT, ".github", "workflows")
ROSTER_RE = re.compile(r"[a-z-]+-county-board-members\.json|il-county-commissioners\.json")


def check_workflows():
    """Every weekly job that rewrites a roster these pages read must regenerate
    them in the same run.

    56 workflows rewrite one, and a job that refreshes a roster without
    regenerating opens a bot PR carrying last week's names on a page and this
    week's in the JSON — and fails --check on a PR nobody wrote by hand, which
    is the worst place to discover a convention. The history page has needed
    exactly this rule since it shipped and enforces it nowhere; three workflows
    carry it because someone remembered.

    A workflow that WRITES no file is not asked to regenerate: the Mason
    watcher reads its source and opens nothing, so requiring a build step of it
    would be requiring a no-op.
    """
    problems = []
    for path in sorted(glob.glob(os.path.join(WORKFLOW_DIR, "*.yml"))):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if not ROSTER_RE.search(text):
            continue
        if "git add " not in text:
            continue                      # a watcher: reads, commits nothing
        if "scripts/build_county_pages.py" in text:
            continue
        problems.append(
            "%s rewrites a county board roster and never runs "
            "scripts/build_county_pages.py — its bot PR would ship a page "
            "naming the members it just replaced"
            % os.path.relpath(path, REPO_ROOT))
    return problems


def main():
    check = "--check" in sys.argv[1:]
    districted, problems, nameless = load_districted()
    problems += check_workflows()
    at_large, more = load_at_large()
    problems += more
    overlap = sorted(set(districted) & set(at_large))
    if overlap:
        problems.append(
            "%s carry BOTH a districted roster and an at-large record — one "
            "county cannot elect its board both ways, and a page would have to "
            "pick" % ", ".join(overlap))
    for county, rec in sorted(NAMES_NOBODY.items()):
        if county not in nameless:
            problems.append(
                "NAMES_NOBODY records %s (%s) and its roster now names someone, "
                "or has left the tree — drop the entry and let the page generate: %s"
                % (county, rec["date"], rec["reason"]))
    if problems:
        for p in problems:
            print("build-county-pages: FAIL — %s" % p, file=sys.stderr)
        raise SystemExit(1)
    for county, rec in sorted(NAMES_NOBODY.items()):
        print("  ~ no page for %s: its roster names nobody (recorded %s) — %s"
              % (county, rec["date"], rec["reason"]))

    tokens_css = read(TOKENS, "the design tokens")
    favicon = read(FAVICON, "the brand mark").strip()
    if not favicon.startswith("<svg"):
        fail("favicon.svg does not start with <svg — is it still an SVG?")
    # The font CSS is written for a page at the instance ROOT — `url(fonts/…)`
    # — and these pages sit one level deeper under il/county-board/, where that
    # resolves to il/county-board/fonts/ and 404s. Every face, silently, on all
    # 73 pages: the app would render in system fonts and nothing would say so.
    # That is the defect Michigan's go-live found the hard way (mi/fonts/ did
    # not exist while 18 @font-face rules named it); here
    # scripts/validate_instance_assets.py named all 584 references before the
    # pages shipped, which is the gate doing exactly what it was written for.
    fontface = read(FONTFACE, "the self-hosted font CSS").rstrip("\n")
    depth_fixed = fontface.replace("url(fonts/", "url(../fonts/")
    if depth_fixed == fontface and "url(" in fontface:
        fail("the font CSS no longer writes url(fonts/…), so the ../ hop these "
             "pages need was not applied — check %s"
             % os.path.relpath(FONTFACE, REPO_ROOT))
    shell = {
        "fontface": depth_fixed,
        "light": token_css(LIGHT_TOKENS, parse_token_block(tokens_css, ":root", TOKENS),
                           ":root"),
        "dark": token_css(DARK_TOKENS,
                          parse_token_block(tokens_css, '[data-theme="dark"]', TOKENS),
                          '[data-theme="dark"]', DARK_EXTRA, indent="    "),
        "favicon": "data:image/svg+xml," + urllib.parse.quote(favicon, safe=""),
        "mark": mark_svg(),
        "byline": shared_footer_byline(),
    }

    pages, stale, people, skipped, wrong = {}, [], 0, 0, []
    for name, rec in sorted(districted.items()):
        pages[rec["slug"]] = build_page(name, rec, False, shell)
        wrong += verify_page(name, rec, False, pages[rec["slug"]])
        # District members plus the elected chair where the county has one —
        # the same total the index prints, because two adjacent numbers five
        # apart read as one of them being wrong.
        people += sum(len(ms) for _, ms in rec["districts"])
        people += 1 if rec.get("chair") else 0
        skipped += len(rec["skipped"])
    for name, rec in sorted(at_large.items()):
        pages[rec["slug"]] = build_page(name, rec, True, shell)
        wrong += verify_page(name, rec, True, pages[rec["slug"]])
        people += len(rec["members"])

    if wrong:
        for w in wrong:
            print("build-county-pages: FAIL — %s" % w, file=sys.stderr)
        raise SystemExit(1)

    os.makedirs(OUT_DIR, exist_ok=True)
    existing = {os.path.basename(p)[:-len(".html")]
                for p in glob.glob(os.path.join(OUT_DIR, "*.html"))}
    orphans = sorted(existing - set(pages))
    for slug, html in sorted(pages.items()):
        out = os.path.join(OUT_DIR, slug + ".html")
        current = ""
        if os.path.exists(out):
            with open(out, encoding="utf-8") as f:
                current = f.read()
        if check:
            if current != html:
                stale.append(os.path.relpath(out, REPO_ROOT))
        elif current != html:
            with open(out, "w", encoding="utf-8") as f:
                f.write(html)

    if check and (stale or orphans):
        if stale:
            print("build-county-pages: FAIL — %d page(s) stale, starting with %s. "
                  "Run `python3 scripts/build_county_pages.py`."
                  % (len(stale), ", ".join(stale[:4])), file=sys.stderr)
        for o in orphans:
            print("build-county-pages: FAIL — %s/%s.html has no roster behind it "
                  "any more; delete it" % (CONCEPT, o), file=sys.stderr)
        raise SystemExit(1)
    if orphans and not check:
        for o in orphans:
            os.remove(os.path.join(OUT_DIR, o + ".html"))

    rows = []
    for name, rec in sorted(districted.items()):
        rows.append((name, rec["slug"], False,
                     sum(len(ms) for _, ms in rec["districts"])
                     + (1 if rec.get("chair") else 0)))
    for name, rec in sorted(at_large.items()):
        rows.append((name, rec["slug"], True, len(rec["members"])))
    rows.sort()
    index_moved = write_index(rows, check)
    if check and index_moved:
        print("build-county-pages: FAIL — %s's %r region is stale. Run `python3 "
              "scripts/build_county_pages.py`."
              % (os.path.relpath(INDEX_PAGE, REPO_ROOT), INDEX_REGION),
              file=sys.stderr)
        raise SystemExit(1)

    print("build-county-pages: OK — %d page(s) %s (%d districted, %d at large), "
          "%d people named and each one verified onto its page, "
          "%d non-district key(s) skipped%s"
          % (len(pages), "current" if check else "written", len(districted),
             len(at_large), people, skipped,
             "; removed %d orphan(s)" % len(orphans) if orphans and not check else ""))


if __name__ == "__main__":
    main()
