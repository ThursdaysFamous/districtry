#!/usr/bin/env python3
"""
Scrape Peoria County's board roster into raw records.

Stage 1 of the two-stage pipeline (scripts/build_peoria_board_roster.py is
stage 2). Peoria is the first county whose roster SPINE is a GIS layer rather
than a page: the county's own `ElectoralDistricts` service publishes a
"County Commissioners" layer carrying, for each of the 18 single-member
districts, the member's name, party and the URL of that member's own page on
the county site. That layer is a stable, machine-readable enumeration — no
markup parsing decides who is on the board — and each member page then
supplies the phone and e-mail the layer does not carry.

So the district assignment and the name come from the county's GIS, the
contact from the county's own member page, and the pair is cross-checked
against the County Board Members index page (a THIRD county surface): a name
the index does not carry is reported, because two county surfaces disagreeing
is exactly the drift this pipeline exists to catch. That cross-check is carried
in the output as an `index` block and floored by the builder — before
2026-09-11 it was a line on stderr, which is how a run that lost three of the
eighteen members from the index shipped anyway.

Peoria elects a Chairperson and a Vice-Chairperson from among the 18 — both
hold their own district seat as well — and the index page is the only surface
that marks them, so the role is read from there and attached to that member's
district row (never invented: a role appears only if the index states it).

FETCH POSTURE: open. Plain ArcGIS REST JSON + server-rendered CivicPlus HTML.

Usage:
    python3 peoria_county_board_scraper.py [output.json]   # default: stdout
"""

import html as html_mod
import json
import re
import sys

import requests

from arcgis_error import raise_for_arcgis_error
from scraper_common import UA_ROSTER_COMPACT  # noqa: E402  (shared machinery — do not fork)

ROSTER_LAYER = ("https://services.arcgis.com/iPiPjILCMYxPZWTc/arcgis/rest/"
                "services/ElectoralDistricts/FeatureServer/3/query")
INDEX_URL = "https://www.peoriacounty.gov/755/County-Board-Members"
UA = {"User-Agent": UA_ROSTER_COMPACT}

MAILTO_RE = re.compile(
    r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
# the member pages label their numbers ("Phone:", "Work phone:", "Cell
# phone:") — take the first labelled number, which is the office line.
PHONE_RE = re.compile(
    r"(?:Work\s+)?[Pp]hone:\s*(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})")
ROLE_RE = re.compile(r"\b(Chairperson|Vice\s+Chairperson)\b")


def clean(s):
    return re.sub(r"\s+", " ", html_mod.unescape(s or "")).strip()


def strip_tags(s):
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    return html_mod.unescape(re.sub(r"(?s)<[^>]+>", "\n", s))


def normalize_phone(raw):
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) != 10:
        return None
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])


def name_key(name):
    """Compare names across county surfaces without tripping on middle
    initials or punctuation ("James C. Dillon" vs "James Dillon")."""
    parts = [p for p in re.split(r"[^A-Za-z]+", (name or "").lower()) if len(p) > 1]
    return (parts[0], parts[-1]) if len(parts) >= 2 else tuple(parts)


def same_person(a, b):
    """Two name keys naming one person. The surfaces differ on diminutives —
    the GIS says "Robert Reneau" and "Matthew Windish" where the index page
    says "Rob" and "Matt" — so the surname must match exactly and the given
    names must agree as far as the shorter one runs. Deliberately strict on
    the surname: this cross-check exists to catch a member appearing on one
    county surface and not the other, and a loose match would hide that."""
    if not a or not b or a[-1] != b[-1]:
        return False
    return a[0].startswith(b[0]) or b[0].startswith(a[0])


def fetch_roster_layer(session):
    r = session.get(ROSTER_LAYER, headers=UA, timeout=60, params={
        "where": "1=1", "returnGeometry": "false", "f": "json",
        "outFields": "DISTRICTID,REPNAME1,PARTY1,DISTRICTURL1",
    })
    r.raise_for_status()
    # HTTP 200 with an `error` member would otherwise read as an empty roster
    # and trip the "zero rows parsed (service change?)" guard below, which
    # names the wrong cause for what is often a rate limit that clears.
    payload = raise_for_arcgis_error(r.json(), "Peoria's roster layer")
    rows = []
    for feat in payload.get("features", []):
        a = feat.get("attributes", {})
        district = clean(str(a.get("DISTRICTID") or ""))
        name = clean(a.get("REPNAME1"))
        if not district or not name:
            continue
        party = clean(a.get("PARTY1"))
        rows.append({
            "district": district,
            "name": name,
            # the layer spells one member's party "Democrat" and the rest
            # "Democratic" — normalize the adjective, don't invent one
            "party": "Democratic" if party == "Democrat" else (party or None),
            "url": clean(a.get("DISTRICTURL1")) or None,
        })
    return rows


# THE INDEX'S MEMBER HEADINGS ARE NOT ONE SHAPE, and reading them as one lost
# both of the board's roles. Measured 2026-09-11 on a 110,624-byte fetch:
# FIFTEEN of the eighteen members sit under `h3.subhead2` (21 such blocks, six
# of them empty) and THREE — Dillon, Williams and Coates — under `h2.subhead1`,
# with BOTH role words inside that h2 group. This function matched the h3 shape
# alone, so it returned fifteen members and no roles at all, and the week's
# roster shipped with the Chairperson and Vice-Chairperson gone.
#
# The three h2 entries carry WYSIWYG artifacts — inline `style="box-sizing:
# inherit; …"` on their anchors, and an empty `<a class="subhead1 subhead2">`
# sibling — which reads as someone editing those three entries in the CMS and
# the heading level moving as a side effect. THAT CAN MOVE BACK, so both shapes
# are accepted rather than one swapped for the other.
#
# Two details the pattern depends on. The class is matched as a WORD inside the
# attribute rather than as the whole of it, because the same editing pass
# produced `class="  subhead1"` with a doubled space on at least one fetch.
# And the heading LEVEL is captured and back-referenced, so the anchor that
# carries `class="subhead1 subhead2"` inside an h2 cannot itself be read as a
# member heading.
INDEX_HEADING_RE = re.compile(
    r'(?is)<h([23])\b[^>]*class="[^"]*\bsubhead[12]\b[^"]*"[^>]*>(.*?)</h\1>')

# THE PAGE REFLOWED ON 2026-09-25 AND THE HEADINGS WENT AWAY ENTIRELY, which
# froze this roster: `subhead` occurs ZERO times on the served page now, so the
# pattern above matched nothing, the index named 0 of 18 members and the
# builder refused to write. The refusal was correct and nothing a reader sees
# moved; what broke is only the block selector.
#
# Measured the same day with this scraper's own client, robots.txt read first
# through robots_policy and allowed: HTTP 200, 109,010 bytes, every member name
# in the served HTML. So not a block, not a fetch failure, not client-rendered.
# The page is CivicPlus and each member is now a paragraph in a `fr-view`
# editor block:
#
#     <div class="fr-view">
#       <p><a href="…/615/James-C-Dillon"><strong>James C. Dillon,
#          Chairperson<br>District 5</strong></a></p><p><img …></p>
#     </div>
#
# EIGHTEEN fr-view blocks, EIGHTEEN anchor-bearing paragraphs, all 18 members
# and both roles, districts 1-18 complete.
#
# `aria-level` IS NOT THE LEADERSHIP MARKER, and it looks like one. Exactly one
# paragraph on the page carries `aria-level="2"` — Williams, the Vice
# Chairperson — and Dillon, the Chairperson, carries none, so anchoring on that
# attribute finds ONE member of eighteen. It is a WYSIWYG artifact of whoever
# last edited that entry, the same class of noise the inline `style=` and the
# empty `<a class="subhead1 subhead2">` were under the old shape.
#
# THE ANCHOR IS REQUIRED, and that is what keeps prose out. The name pattern
# downstream ends in `|$`, so it matches any run of letters and spaces — a
# paragraph reading "Board meetings are held monthly" would parse as a member
# named exactly that and enter `listed`, which is the set the builder's floor
# counts. A link to the member's own page is the page's own statement that the
# paragraph names a member, so it is what the selector asks for.
#
# BOTH SHAPES ARE READ, not one swapped for the other: the heading shape was
# itself a CMS artifact that moved once already, so it can move back.
INDEX_EDITOR_BLOCK_RE = re.compile(r'(?is)<div class="fr-view">(.*?)</div>')
INDEX_EDITOR_ENTRY_RE = re.compile(r"(?is)<p\b[^>]*>(.*?)</p>")
INDEX_ENTRY_ANCHOR_RE = re.compile(r"(?i)<a\s[^>]*href=")


def index_blocks(text):
    """Every HTML fragment on the index that may name one member.

    Returns raw fragments, flattened and matched by the caller: a fragment that
    is not a member simply fails the name pattern, which is how the six empty
    `subhead` blocks were already tolerated.
    """
    blocks = [block for _level, block in INDEX_HEADING_RE.findall(text)]
    for editor in INDEX_EDITOR_BLOCK_RE.findall(text):
        for para in INDEX_EDITOR_ENTRY_RE.findall(editor):
            if INDEX_ENTRY_ANCHOR_RE.search(para):
                blocks.append(para)
    return blocks


def fetch_index_roles(session):
    """Index page -> {name_key: role}, plus the set of names it lists. Roles
    are only ever read from here; a member the index does not mark gets none.

    A leadership heading puts the name and the role in DIFFERENT anchors either
    side of a `<br>`, so the whole heading is flattened before matching —
    strip_tags + clean turn `James C. Dillon,&nbsp;</a><br><a …>Chairperson<br>
    District 5` into `James C. Dillon, Chairperson District 5`."""
    r = session.get(INDEX_URL, headers=UA, timeout=60)
    r.raise_for_status()
    roles, listed = {}, set()
    for block in index_blocks(r.text):
        text = clean(strip_tags(block))
        m = re.match(r"([A-Za-z][A-Za-z.'\-\s]+?),?\s*(?:Chairperson|Vice\s+Chairperson|District\s+\d+|$)", text)
        if not m:
            continue
        key = name_key(m.group(1))
        if not key:
            continue
        listed.add(key)
        role = ROLE_RE.search(text)
        if role:
            roles[key] = re.sub(r"\s+", "-", role.group(1))
    return roles, listed


def fetch_member_contact(session, url):
    try:
        r = session.get(url, headers=UA, timeout=60)
        r.raise_for_status()
    except requests.RequestException:
        return None, None
    email = MAILTO_RE.search(r.text)
    phone = PHONE_RE.search(strip_tags(r.text))
    return (email.group(1).lower() if email else None,
            normalize_phone(phone.group(1)) if phone else None)


def main():
    session = requests.Session()
    rows = fetch_roster_layer(session)
    # `index_read` is NOT `bool(listed)`, and the difference is the whole point
    # of the guard downstream: an index that was fetched and parsed to nothing
    # is a parser break, while an index that could not be fetched is a network
    # outage the roster should survive. Only the first is a refusal.
    index_read = True
    try:
        roles, listed = fetch_index_roles(session)
    except requests.RequestException as exc:
        print("peoria-board-scraper: WARN — index page unreadable (%s); "
              "no roles will be tagged" % exc, file=sys.stderr)
        roles, listed = {}, set()
        index_read = False

    records = []
    missing = []
    for row in rows:
        key = name_key(row["name"])
        email = phone = None
        if row["url"]:
            email, phone = fetch_member_contact(session, row["url"])
        if index_read and not any(same_person(key, k) for k in listed):
            missing.append(row["name"])
            print("peoria-board-scraper: WARN — %s (district %s) is on the GIS "
                  "roster but not the County Board Members index"
                  % (row["name"], row["district"]), file=sys.stderr)
        records.append({
            "district": row["district"],
            "name": row["name"],
            "party": row["party"],
            "role": next((r for k, r in roles.items() if same_person(key, k)), None),
            "phone": phone,
            "email": email,
            "url": row["url"],
        })

    if not records:
        print("peoria-board-scraper: FAIL — zero rows parsed (service change?)",
              file=sys.stderr)
        sys.exit(1)

    # The cross-check ships as DATA rather than as a line on stderr. It printed
    # the three missing names on 2026-09-11 and nothing read them; the builder
    # floors `matched` so the next narrowing stops the run instead.
    out = json.dumps({
        "source": INDEX_URL,
        "index": {
            "read": index_read,
            "rosterCount": len(rows),
            "matched": (len(rows) - len(missing)) if index_read else 0,
            "missing": missing,
        },
        "records": records,
    }, indent=2, ensure_ascii=False)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(out)
        print("peoria-board-scraper: %d records -> %s" % (len(records), sys.argv[1]))
    else:
        print(out)


# --------------------------------------------------------------- selftest ---

# One fixture per shape this index has been MEASURED in, because the shape has
# now changed under us twice and each time the roster froze for a week with the
# page serving every name. This is the Edgar shape a second time: the page was
# fine and the parser was not.
EDITOR_SHAPE = """
<div class="widget editor pageStyles narrow"><div class="fr-view">
  <p><a href="https://www.peoriacounty.gov/615/James-C-Dillon"><strong>James C.
     Dillon, Chairperson<br>District 5</strong></a></p><p><img src="/x"></p>
</div></div>
<div class="widget editor pageStyles narrow"><div class="fr-view">
  <p aria-level="2"><a href="https://www.peoriacounty.gov/565/Sharon-K-Williams"><strong>Sharon
     K. Williams, Vice Chairperson<br>District 1</strong></a></p><p><img src="/y"></p>
</div></div>
<div class="widget editor pageStyles narrow"><div class="fr-view">
  <p><a href="https://www.peoriacounty.gov/635/Brian-Elsasser"><strong>Brian
     Elsasser<br>District 14</strong></a></p><p><img src="/z"></p>
</div></div>
"""

# The shape the page served until 2026-09-25, with the artifacts that were
# measured on it: the doubled space in the class, the inline style, and the
# empty anchor carrying BOTH class names inside the h2.
HEADING_SHAPE = """
<h2 class="  subhead1"><a style="box-sizing: inherit;"
   href="/615/James-C-Dillon">James C. Dillon,&nbsp;</a><br><a
   href="/615/James-C-Dillon">Chairperson<br>District 5</a>
   <a class="subhead1 subhead2"></a></h2>
<h3 class="subhead2"><a href="/635/Brian-Elsasser">Brian Elsasser<br>District 14</a></h3>
<h3 class="subhead2"></h3>
"""

# Prose inside an editor block, which the name pattern's trailing `|$` matches
# as a member named exactly that. The anchor requirement is the only thing
# keeping it out of `listed`, and `listed` is what the builder's floor counts.
PROSE_SHAPE = """
<div class="fr-view">
  <p>Board meetings are held monthly</p>
  <p>County Board Members</p>
</div>
"""


def read_blocks(text):
    """(names, roles) the index parser would take from this markup."""
    names, roles = [], {}
    for block in index_blocks(text):
        flat = clean(strip_tags(block))
        m = re.match(r"([A-Za-z][A-Za-z.'\-\s]+?),?\s*"
                     r"(?:Chairperson|Vice\s+Chairperson|District\s+\d+|$)", flat)
        if not m:
            continue
        key = name_key(m.group(1))
        if not key:
            continue
        names.append(key)
        role = ROLE_RE.search(flat)
        if role:
            roles[key] = re.sub(r"\s+", "-", role.group(1))
    return names, roles


def selftest():
    problems = checks = 0

    def want(label, got, expected):
        nonlocal problems, checks
        checks += 1
        if got != expected:
            problems += 1
            print("  FAIL %-34s expected %r\n%s got      %r"
                  % (label, expected, " " * 41, got))

    names, roles = read_blocks(EDITOR_SHAPE)
    # `name_key` returns a (first, last) tuple, not a slug — the keys below are
    # what it actually produces, checked rather than guessed at.
    want("editor shape names", names,
         [("james", "dillon"), ("sharon", "williams"), ("brian", "elsasser")])
    want("editor shape roles", roles,
         {("james", "dillon"): "Chairperson",
          ("sharon", "williams"): "Vice-Chairperson"})

    names, roles = read_blocks(HEADING_SHAPE)
    want("heading shape names", names, [("james", "dillon"), ("brian", "elsasser")])
    want("heading shape roles", roles, {("james", "dillon"): "Chairperson"})

    # Both at once: a page mid-reflow must not double-count or lose either.
    names, _roles = read_blocks(HEADING_SHAPE + EDITOR_SHAPE)
    want("both shapes on one page", sorted(set(names)),
         [("brian", "elsasser"), ("james", "dillon"), ("sharon", "williams")])

    names, roles = read_blocks(PROSE_SHAPE)
    want("prose names nobody", names, [])

    # The failure this fix is for: the live page with no `subhead` anywhere.
    want("heading shape alone finds nobody in the editor markup",
         [b for _l, b in INDEX_HEADING_RE.findall(EDITOR_SHAPE)], [])

    print("peoria-board-scraper selftest: %s — %d check(s)%s"
          % ("FAIL" if problems else "OK", checks,
             ", %d problem(s)" % problems if problems else ""))
    return 1 if problems else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    main()
