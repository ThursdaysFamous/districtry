#!/usr/bin/env python3
"""
The city rosters, in the served bytes — generated into the question pages.

WHY. scripts/build_county_pages.py put 2,650 county officeholders where a
crawler can read them, and it left the CITY seats where they were: behind a
JSON fetch and a rendered card. Measured 2026-09-15, New York City's 51 Council
Members and San Francisco's 11 Supervisors appeared in no served byte of this
site. Both rosters are already shipped as data/app files and already reviewed
before they ship; nothing was missing except a table.

WHERE. Each city's own question page — ny/council-district.html,
ca/supervisor-district.html — rather than a page per seat. That is the decision
build_county_pages.py already made and states: a page whose whole content is one
name is the shape search engines treat as thin, and the question people type is
about the body far more often than about one seat. Each row carries schema.org
Person markup, so a reader asking a machine "who represents District 6" gets a
name it can attribute.

THE TABLE IS A DATED SNAPSHOT AND SAYS SO. The instance's own verified_date is
printed above it. The map card beside it reads the same roster file, so the two
cannot disagree — but a static table is a claim about a day, and a claim about
a day that does not name the day is the thing this project does not ship.

WHAT IS NOT HERE. Chicago's 50 alderpeople. That roster is not a shipped file:
il/index.html fetches Socrata htai-wnw4 live on every toggle, so there is
nothing for this to read. NOT_YET records it rather than leaving it to be
noticed, and --check FAILS on an entry whose roster has since appeared.

    python3 scripts/build_officeholder_tables.py           # write the regions
    python3 scripts/build_officeholder_tables.py --check   # drift gate for CI
"""

import argparse
import difflib
import html
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REGION = "officeholder-table"
BEGIN = "<!-- ==== GENERATED:BEGIN %s ==== -->" % REGION
END = "<!-- ==== GENERATED:END %s ==== -->" % REGION

# Where the table goes, and the words that page uses for its own seats. The
# roster-to-page join has no mechanical source — nothing in council-members.json
# says which page it belongs on — so it is stated, the way build_county_pages.py
# states one entry per state. Everything else is read: the names and offices
# from the roster, the date from the instance's worksheet, the district count
# from the roster itself.
TABLES = [
    dict(tag="ny", page="council-district.html",
         roster="council-members.json", worksheet="ny/metro-worksheet.json",
         seat="District", holder="Council Member",
         body="the New York City Council",
         heading="Who represents each Council district"),
    dict(tag="ca", page="supervisor-district.html",
         roster="sf-supervisor-members.json", worksheet="ca/metro-worksheet.json",
         seat="District", holder="Supervisor",
         body="the San Francisco Board of Supervisors",
         heading="Who represents each supervisor district"),
]

# A seat this cannot table yet, with the reason and the date, in the shape
# ACCEPTED_DROPS and EXPECTED_UNREACHABLE already use: re-audited every run, so
# an entry that stops being true FAILS rather than going quiet.
NOT_YET = [
    dict(tag="il", page="ward.html", roster="ward-members.json",
         date="2026-09-15",
         reason="Chicago's 50 alderpeople are not a shipped roster: il/index.html "
                "fetches Socrata htai-wnw4 live on first toggle of the ward layer, "
                "so there is no data/app file to read. The dataset does carry all "
                "50 with a name, ward office address, phone, e-mail and website, "
                "so the work is a roster pipeline (scraper, builder, count guard, "
                "weekly workflow opening a PR) plus the decision of whether the "
                "card keeps reading Socrata live beside a shipped snapshot"),
]

# The region goes immediately before this section, on every page that has one.
ANCHOR = "  <section>\n    <h2>Related lookups</h2>"


def fail(msg):
    print("build-officeholder-tables: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def load(path):
    with open(os.path.join(REPO_ROOT, path), encoding="utf-8") as f:
        return json.load(f)


def district_key(k):
    """Sort 1, 2, 10 rather than 1, 10, 2 — and never crash on a lettered one."""
    return (0, int(k), "") if k.isdigit() else (1, 0, k)


def render(entry):
    roster = load(os.path.join(entry["tag"], "data", "app", entry["roster"]))
    worksheet = load(entry["worksheet"])
    verified = worksheet.get("verified_date")
    if not verified:
        fail("%s has no verified_date and the table is dated with it"
             % entry["worksheet"])

    keys = sorted(roster, key=district_key)
    named = [k for k in keys if isinstance(roster[k], dict) and roster[k].get("name")]
    if not named:
        fail("%s/data/app/%s names nobody — refusing to write an empty table"
             % (entry["tag"], entry["roster"]))
    has_office = any(roster[k].get("office") for k in named)

    rows = []
    for k in keys:
        rec = roster[k] if isinstance(roster[k], dict) else {}
        name = rec.get("name")
        seat = "%s %s" % (entry["seat"], k)
        if not name:
            # A seat the roster does not name is printed as one. Leaving it out
            # would make the table claim a smaller body than the city elects.
            cells = ['<td>%s</td>' % html.escape(seat),
                     '<td class="who">Not listed</td>']
            if has_office:
                cells.append("<td></td>")
            rows.append("      <tr>%s</tr>" % "".join(cells))
            continue
        # The <meta> sits INSIDE a cell, not between <tr> and <td>. An HTML
        # parser foster-parents any non-table content out of a <tr>, which
        # moves it before the whole table and detaches it from the itemscope
        # it was meant to describe — valid-looking markup that says nothing.
        cells = ['<td>%s</td>' % html.escape(seat),
                 '<td class="who"><meta itemprop="jobTitle" content="%s, %s">'
                 '<span itemprop="name">%s</span></td>'
                 % (html.escape(entry["holder"], quote=True),
                    html.escape(seat, quote=True), html.escape(name))]
        if has_office:
            office = rec.get("office") or ""
            cells.append('<td itemprop="address">%s</td>' % html.escape(office))
        rows.append(
            '      <tr itemscope itemtype="https://schema.org/Person">%s</tr>'
            % "".join(cells))

    head = ["<th>%s</th>" % html.escape(entry["seat"]),
            "<th>%s</th>" % html.escape(entry["holder"])]
    if has_office:
        head.append("<th>District office</th>")

    return """  <section>
    <h2>%(heading)s</h2>
    <p>All %(n)d seats on %(body)s, as this site had them on <strong>%(verified)s</strong>.
      The map above reads the same roster, so a card and this table cannot disagree — but a
      table is a claim about a day, and this one names its day. Where the roster does not name
      a seat it says so rather than guessing. <a href="sources.html">Where these names come
      from</a>.</p>
    <div class="flow-table-wrap">
    <table class="flow">
      <thead><tr>%(head)s</tr></thead>
      <tbody>
%(rows)s
      </tbody>
    </table>
    </div>
  </section>

""" % {
        "heading": html.escape(entry["heading"]),
        "n": len(keys),
        "body": html.escape(entry["body"]),
        "verified": html.escape(verified),
        "head": "".join(head),
        "rows": "\n".join(rows),
    }


def apply(entry, body, check):
    rel = os.path.join(entry["tag"], entry["page"])
    path = os.path.join(REPO_ROOT, rel)
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    if BEGIN in text:
        i = text.index(BEGIN) + len(BEGIN)
        j = text.index(END)
        current = text[i:j].strip("\n")
        if current == body.rstrip("\n"):
            return ("current", rel, None)
        if check:
            return ("drift", rel, (current, body.rstrip("\n")))
        new = text[:i] + "\n" + body.rstrip("\n") + "\n" + text[j:]
    else:
        if check:
            return ("missing", rel, None)
        if ANCHOR not in text:
            fail("%s has no 'Related lookups' section to sit above" % rel)
        new = text.replace(ANCHOR, BEGIN + "\n" + body.rstrip("\n") + "\n" + END + "\n" + ANCHOR, 1)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(new)
    return ("written", rel, None)


def verify_shipped(entry):
    """Read the page BACK and find every name the roster carries.

    Byte-equality proves the region matches what render() produces today, and
    would pass a correct, empty template every time — the property
    build_county_pages.py had to be given after the fact. This asks the other
    question: is the person in the file a reader downloads. Escaped, because
    O'Brien ships as O&#x27;Brien.
    """
    rel = os.path.join(entry["tag"], entry["page"])
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as f:
        shipped = f.read()
    roster = load(os.path.join(entry["tag"], "data", "app", entry["roster"]))
    missing = [k for k, rec in sorted(roster.items(), key=lambda kv: district_key(kv[0]))
               if isinstance(rec, dict) and rec.get("name")
               and html.escape(rec["name"]) not in shipped]
    if missing:
        fail("%s does not name %d of its own roster's members (%s) — the table "
             "is present and does not carry them"
             % (rel, len(missing), ", ".join(missing[:5])))
    return sum(1 for rec in roster.values()
               if isinstance(rec, dict) and rec.get("name"))


WORKFLOWS = os.path.join(REPO_ROOT, ".github", "workflows")


def check_workflows():
    """A workflow that rewrites a tabled roster must regenerate the table.

    This is the rule build_county_pages.py already enforces for the 170
    per-county pages. Without it the failure lands on the bot's own PR: the
    weekly job rewrites the roster, the page still names last week's members,
    and --check goes red on a PR nobody wrote. Catching it here instead names
    the workflow and the two lines it is missing, before that ever happens.
    """
    for entry in TABLES:
        roster = "%s/data/app/%s" % (entry["tag"], entry["roster"])
        page = "%s/%s" % (entry["tag"], entry["page"])
        for name in sorted(os.listdir(WORKFLOWS)):
            if not name.endswith((".yml", ".yaml")):
                continue
            path = os.path.join(WORKFLOWS, name)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            if ("git add" not in text) or (roster not in text):
                continue
            if "build_officeholder_tables.py" not in text:
                fail(".github/workflows/%s rewrites %s and never regenerates %s "
                     "— add a step running python3 "
                     "scripts/build_officeholder_tables.py and `git add %s`"
                     % (name, roster, page, page))
            if page not in text:
                fail(".github/workflows/%s regenerates the table and never "
                     "commits it — add `git add %s`" % (name, page))
            print("build-officeholder-tables: %s regenerates %s" % (name, page))


def audit_not_yet():
    """An entry that has stopped being true is a hole in the record."""
    for e in NOT_YET:
        roster = os.path.join(REPO_ROOT, e["tag"], "data", "app", e["roster"])
        if os.path.exists(roster):
            fail("NOT_YET records %s/%s as having no shipped roster (%s), and "
                 "%s/data/app/%s now exists — add it to TABLES and drop the entry"
                 % (e["tag"], e["page"], e["date"], e["tag"], e["roster"]))
        page = os.path.join(REPO_ROOT, e["tag"], e["page"])
        if not os.path.exists(page):
            fail("NOT_YET records %s/%s and that page is gone — drop the entry"
                 % (e["tag"], e["page"]))
        print("build-officeholder-tables: ~ %s/%s has no table (%s): %s"
              % (e["tag"], e["page"], e["date"], e["reason"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="drift gate: fail rather than write")
    args = ap.parse_args()

    drifted, missing, seats = [], [], 0
    for entry in TABLES:
        body = render(entry)
        state, rel, detail = apply(entry, body, args.check)
        seats += body.count("itemtype=")
        if state == "drift":
            drifted.append((rel, detail))
        elif state == "missing":
            missing.append(rel)
        elif state == "written":
            print("build-officeholder-tables: %s — table written" % rel)
        if state != "drift" and state != "missing":
            verify_shipped(entry)
    audit_not_yet()
    check_workflows()

    if args.check:
        for rel in missing:
            print("build-officeholder-tables: %s has no %s region" % (rel, REGION),
                  file=sys.stderr)
        for rel, (cur, new) in drifted:
            print("build-officeholder-tables: DRIFT in %s" % rel, file=sys.stderr)
            for dl in difflib.unified_diff(cur.splitlines(), new.splitlines(),
                                           fromfile="committed",
                                           tofile="regenerated", lineterm="", n=1):
                print("  " + dl, file=sys.stderr)
        if missing or drifted:
            fail("%d table(s) out of date — run "
                 "python3 scripts/build_officeholder_tables.py"
                 % (len(missing) + len(drifted)))
        print("build-officeholder-tables: OK — %d table(s), %d officeholder(s) in "
              "the served bytes, %d seat(s) recorded as not tabled yet"
              % (len(TABLES), seats, len(NOT_YET)))
    else:
        print("build-officeholder-tables: OK — %d table(s), %d officeholder(s)"
              % (len(TABLES), seats))


if __name__ == "__main__":
    main()
