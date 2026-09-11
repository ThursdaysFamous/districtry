#!/usr/bin/env python3
"""Hold every authored page's <title> and meta description to what Google shows.

WHY THIS EXISTS SEPARATELY FROM THE WORKSHEET GATE. generate_metro_files.py
already refuses a worksheet whose brand.head.title or brand.head.description
overruns, and that gate has held since 2026-09-09 — measured on 2026-09-11, not
one of the six instance index.html pages is over. It cannot see anything else.
The six apps are 6 of 46 authored pages here; the other forty are the sub-pages,
the topic pages, the root pages and the redirect shells, and NOTHING measured
them. On that date 9 titles and 23 descriptions were over, the worst a 252-
character description on traffic.html and an 85-character double-question title
on ny/community-board.html.

THE SURFACE IS DISCOVERED, NEVER LISTED. Every *.html at the repo root and in
each instance folder, which is the rule validate_card_links.py and
validate_instance_registration.py already discover by — a hand-kept list is how
Iowa shipped three pages outside the link gate for a month.

THE LIMITS ARE A STATED PROXY AND NOT A MEASUREMENT. Google truncates a SERP
entry by PIXEL WIDTH, which depends on the glyphs: an em dash and an "l" are one
character each and nothing like the same width. Character count is the cheap
stand-in every SEO tool uses, and it is what the worksheet gate already uses, so
the two agree rather than contradicting each other on the same page. Both are
imported from generate_metro_files so there is one definition of each number.

CHARACTERS, NOT BYTES. A review of the 2026-09-09 rewrite reported every string
exactly 2 over, because it had counted UTF-8 bytes and every one of those titles
carries one em dash — 1 character, 3 bytes. len() on a str is the right measure.

Entities are unescaped before measuring: a description carrying &amp; shows the
reader one character, not five.
"""

import html
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# One definition of each limit, shared with the worksheet gate.
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
try:
    from generate_metro_files import SERP_LIMITS
except Exception:  # jsonschema absent, and this gate is stdlib-only on purpose
    SERP_LIMITS = {"title": 60, "description": 155}

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
DESC_RE = re.compile(r'<meta\s+name="description"\s+content="(.*?)"', re.S)

# A redirect shell is a page whose whole job is to leave. It carries a title so
# a reader who lands on it mid-hop sees something, and it is deliberately NOT in
# the sitemap. Its title still has to fit, because Google indexed these paths
# while they served the app -- /school-board.html carried 744 impressions on the
# old domain -- so they are measured exactly like any other page.


def fail(msg):
    print("validate-serp-lengths: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def authored_pages():
    """Root *.html plus each instance folder's *.html. An instance is a
    top-level directory carrying an index.html and a data/app/ — the same test
    validate_card_links.py uses, so the two gates cover the same tree."""
    out = []
    for name in sorted(os.listdir(REPO_ROOT)):
        p = os.path.join(REPO_ROOT, name)
        if os.path.isfile(p) and name.endswith(".html"):
            out.append(name)
    for name in sorted(os.listdir(REPO_ROOT)):
        d = os.path.join(REPO_ROOT, name)
        if not os.path.isdir(d) or name.startswith("."):
            continue
        if not (os.path.isfile(os.path.join(d, "index.html"))
                and os.path.isdir(os.path.join(d, "data", "app"))):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith(".html"):
                out.append("%s/%s" % (name, f))
    return out


def measure(path):
    with open(os.path.join(REPO_ROOT, path), encoding="utf-8") as fh:
        s = fh.read()
    t = TITLE_RE.search(s)
    d = DESC_RE.search(s)
    return (html.unescape(t.group(1).strip()) if t else None,
            html.unescape(d.group(1).strip()) if d else None)


def main():
    pages = authored_pages()
    if len(pages) < 10:
        fail("found only %d authored page(s) — discovery is broken, not the "
             "tree" % len(pages))

    over = []
    missing = []
    for page in pages:
        title, desc = measure(page)
        if title is None:
            missing.append("%s has no <title>" % page)
        elif len(title) > SERP_LIMITS["title"]:
            over.append((page, "title", len(title), SERP_LIMITS["title"], title))
        if desc is not None and len(desc) > SERP_LIMITS["description"]:
            over.append((page, "description", len(desc),
                         SERP_LIMITS["description"], desc))

    if missing:
        fail("\n    ".join(missing))

    if over:
        lines = []
        for page, key, n, limit, value in sorted(over, key=lambda r: -r[2]):
            lines.append("%s: %s is %d characters against a %d limit — the last "
                         "%d would be cut from the search result.\n      %r"
                         % (page, key, n, limit, n - limit, value))
        fail("%d overrun(s). Shorten them; do not raise the limit. Trim the "
             "FRONT: the tail is where the differentiator lives.\n    %s"
             % (len(over), "\n    ".join(lines)))

    print("validate-serp-lengths: OK — %d authored page(s), every title within "
          "%d characters and every description within %d"
          % (len(pages), SERP_LIMITS["title"], SERP_LIMITS["description"]))


if __name__ == "__main__":
    main()
