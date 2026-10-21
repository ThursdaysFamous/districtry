#!/usr/bin/env python3
"""Generate the root redirect shells, the short addresses, and the branded 404.

All three answer for an address that no ordinary page of this site lives at,
which is why they share a script. A shell is for the eight paths this origin
USED to serve and can name the page they became; a short address is a path
printed or posted where it cannot be taken back, which either forwards to
another site or shows a small page of its own; the 404 is for every other miss,
and can only offer the way back in.

WHY THESE FILES EXIST. Before R2.3 the Illinois app served from this origin's
ROOT, so /school-board.html and its siblings were real, indexed pages. They are
now under /il/. A request arriving at the old path 404s, which is search equity
landing on nothing — Search Console records several of these URLs with real
impressions. GitHub Pages cannot issue a 301, so each old path gets the
strongest available substitute: an instant meta refresh (Google treats it as a
redirect), a canonical naming the real page so the signal consolidates there,
and a JS replace so the browser leaves no history entry. Deliberately NOT
noindex, which would block the consolidation the file exists to perform.

WHY IT IS NOW GENERATED. Six of these were written by hand and two were simply
missing: /ward.html and /precinct.html both 404'd on 2026-09-15, found by the
SEO audit, which named a "stub generator" that did not exist. Eight
near-identical 40-line files is how the seventh gets written wrong and the
ninth never gets written at all.

THE WORDING COMES FROM THE TARGET PAGE'S OWN <title>, so a retitled page cannot
leave its shell describing something else. Each shell says its phrase TWICE, in
the tab title and in the one sentence of body copy, and two of the hand-written
six deliberately differ between the two: /faq.html titles itself "Common
questions about Chicago districts" and then says "The FAQ now lives at", which
is a descriptive title for a search result and a natural phrase in a sentence.
Collapsing those to one string is the first thing this generator got wrong, so
an override carries both. The other six derive exactly, which is how the
derivation was checked.

Put a real 301 in front of the origin and every one of these can be deleted.

A SHORT ADDRESS IS THE OTHER DIRECTION (added 2026-10-18): a path on this
origin that was never a page, printed or posted where it cannot be taken back.
districtry.com/android is the QR code on the in-person sign-up sheet for the
Google Play closed test. A code printed with somebody else's address goes stale
the day that address changes; printed with ours it keeps working, because the
address stays put and SHORT_LINKS below says what it shows today. An entry
takes one of two forms: a FORWARD to another site (`target`), or a small PAGE
of its own (`body`). /android was a forward to the testers' Google Group for
its first hours and became a page that afternoon, when Adam asked for the code
to open the testing steps instead. Both forms are noindex with no canonical,
since neither is a page to find by searching. A page carries the counter every
page here carries; a forward carries none, because validate_analytics.py skips
every page with a meta refresh and a page that leaves at once would mostly
count nothing. Nothing passes the query or the fragment on. A short address
cannot take a name a page already uses, and the script fails on a root page
that says this script generated it when no entry here still does, so a retired
address cannot go on answering unchecked.

THE 404 IS DELIBERATELY SELF-CONTAINED: no webfont, no external stylesheet, no
script. It is the page a reader reaches when something is already wrong, and
every extra request is another thing that can fail underneath it. It carries
noindex, which also keeps it out of sitemap.xml — build_sitemap.py excludes any
page that is noindex or a meta refresh, so nothing has to name it in a skip
list. Its instance list comes from metros.json, so a seventh state appears in
it the day that state ships.

GitHub Pages serves /404.html for any unmatched path on the whole site, with a
real HTTP 404, so this one file covers every instance as well as the root.

Usage:
    python3 scripts/build_redirect_stubs.py            # write them
    python3 scripts/build_redirect_stubs.py --check    # CI drift gate
"""

import argparse
import glob
import html
import json
import os
import re
import sys
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_privacy_page import shared_goatcounter  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Every root path this origin served before R2.3 that still has a page under
# /il/. The value is None to derive both strings from the target page's
# <title>, or an explicit (tab title, body phrase) pair where the hand-written
# shell said something better than the derivation would.
STUBS = {
    "county-board.html": None,
    "faq.html": ("Common questions about Chicago districts", "The FAQ"),
    "history.html": ("History", "The project history"),
    "police-district.html": None,
    "school-board.html": None,
    "sources.html": None,
    # Added 2026-09-15: both 404'd, while six siblings had shells.
    "ward.html": None,
    "precinct.html": None,
}

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Moved — %(title)s</title>
<!-- REDIRECT SHELL, GENERATED by scripts/build_redirect_stubs.py. Do not edit;
     change the script. This path was an indexed page on chidistricts.com, and then on
     districtry.com's own root, before the app moved under /il/ (R2.3) and the domain moved
     to districtry.com (R5). A request arriving here is at a path that no longer holds a
     page, and 404s. That is search equity landing on nothing: GSC records this URL with
     real impressions.

     WHAT REACHES THIS FILE CHANGED ON 2026-09-11 and the old reason is recorded because it
     is the one a reader will assume. The Squarespace forward off chidistricts.com used to
     arrive here with the path intact; it now rewrites to /il/<path> itself, so
     chidistricts.com/sources.html goes straight to districtry.com/il/sources.html in one
     hop and never touches this file. What still lands here is a request to
     districtry.com/<path> directly — old links, bookmarks and index entries from the weeks
     this origin served the app at its own root. Measured, not assumed, and now
     monthly: scripts/check_legacy_redirects.py asserts every legacy path still
     forwards in one hop over HTTPS to its /il/ equivalent.

     GitHub Pages cannot issue a 301, so this is the strongest available substitute: an
     instant meta refresh (Google treats it as a redirect), a canonical naming the real page
     so the signal consolidates there, and a JS replace so the browser leaves no history
     entry. Deliberately NOT noindex — that would block the consolidation this exists to do.

     Put a real 301 in front of the origin (a CDN/proxy layer) and these can be deleted. -->
<meta http-equiv="refresh" content="0; url=/il/%(path)s" />
<link rel="canonical" href="https://districtry.com/il/%(path)s" />
<script>location.replace("/il/%(path)s" + location.search + location.hash);</script>
<style>
  body { margin: 0; padding: 48px 20px; background: #f4f7f9; color: #14181c;
         font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  main { max-width: 34rem; margin: 0 auto; }
  a { color: #5730ab; font-weight: 600; }
</style>
</head>
<body>
<main>
  <h1>This page moved</h1>
  <p>%(phrase)s now lives at
    <a href="/il/%(path)s">districtry.com/il/%(path)s</a>.</p>
  <p>You should be redirected automatically. If not, follow the link above.</p>
</main>
</body>
</html>
"""


# Short addresses: the published name (one root .html, served by GitHub Pages
# at the name without the .html) and what it shows. A FORWARD names its
# `target` on another site, with the words a reader sees for the moment before
# it leaves, or for good if their browser blocks the forward. A PAGE carries
# its own `body`, a list of blocks: ("p", text), ("note", text) for a quieter
# line, ("h2", heading), ("list", [text, ...]) and ("steps", [(text, button),
# ...]), where a button is (label, address) or None. Text takes **bold** and
# [words](address) and nothing else, and an address is https://, mailto: or a
# path on this site. Both forms take the `title` and `description` a chat app
# shows when the address is shared.
#
# /android, 2026-10-18: the in-person sign-up sheet's QR code. For its first
# hours it forwarded to the testers' Google Group; Adam then asked for the code
# to open the testing steps, with the group's link and the app's Play listing,
# so it is a page. The group is linked at its /about page and never the bare
# group address, which gives a signed-out visitor a permission error. When the
# app is published, turn the entry back into a forward to PLAY_LISTING and
# regenerate; every printed code follows.
TESTERS_GROUP = "https://groups.google.com/g/districtry-testers/about"
# The closed test's opt-in page. Google's help (answer 9845334, read
# 2026-10-18) says each tester opts in there after joining the group, and that
# Play Console shows the link only once the test is published; it does not
# print the address. This was the form third-party guides give for the
# console's shareable link, and it was an inference until the same day, when
# Adam, asked to compare it with the link Play Console's Testers tab shows,
# confirmed it and pasted the same address.
PLAY_TEST = "https://play.google.com/apps/testing/com.districtry.app"
# The app's listing. It answered 404 to a visitor who was not signed in,
# measured 2026-10-18 while the app was in its closed test, which is why the
# monthly link check records it in NOT_YET_PUBLIC rather than calling it dead.
PLAY_LISTING = "https://play.google.com/store/apps/details?id=com.districtry.app"

SHORT_LINKS = {
    "android.html": dict(
        title="Help test districtry on Android",
        description="How to join the test of districtry’s Android app: join "
                    "the testers’ group, become a tester on Google Play, then "
                    "install the app.",
        body=[
            ("p", "districtry’s Android app is being tested on Google Play "
                  "before it goes public. Google needs at least 12 people to "
                  "use it from Google Play for 14 days in a row first. Joining "
                  "takes about five minutes."),
            ("h2", "Join the test"),
            ("steps", [
                ("**Check your Play Store account.** On your Android phone, "
                 "open the Play Store and tap your picture in the top right "
                 "corner. Use that Google account for every step below, in "
                 "your browser too.", None),
                ("**Join the testers’ group.** On the group’s page, tap **Join "
                 "group**. If it asks how you want email, choose **Each "
                 "email**, so news about the test reaches you.",
                 ("Open the testers’ group", TESTERS_GROUP)),
                ("**Become a tester.** On Google Play’s test page, tap "
                 "**Become a tester**. It works only after you have joined "
                 "the group.",
                 ("Open Google Play’s test page", PLAY_TEST)),
                ("**Install the app.** Tap **Install**. Google Play shows "
                 "districtry only to testers, so this works after step 3.",
                 ("Open districtry on Google Play", PLAY_LISTING)),
                ("**Remove any copy from the website.** If you added "
                 "districtry to your home screen from the website, press and "
                 "hold its icon, then tap **Uninstall**. Otherwise links and "
                 "shares can open the wrong copy.", None),
            ]),
            ("note", "If Google Play says it can’t find the app, wait an hour "
                     "and open the link again. If the test page has no "
                     "**Become a tester** button, check that your browser is "
                     "signed in to the account you joined the group with. If "
                     "it is, the test may not have opened yet, and the group "
                     "sends an email when it does."),
            ("h2", "For the next 14 days"),
            ("list", [
                "Stay in the group and in the test for 14 days in a row. If "
                "you leave either one and join again, your 14 days start over.",
                "Open the app a few times a week. Look up places you know, "
                "like your home, your work or a relative’s house, and check "
                "what the cards say against your voter registration card or "
                "a sample ballot.",
                "Share a place to districtry from Google Maps: tap **Share**, "
                "then pick districtry.",
            ]),
            ("h2", "Report a problem"),
            ("p", "Scroll to the bottom of the app’s panel and tap **Report a "
                  "bug or leave a comment**. It attaches the map view you’re "
                  "looking at, so pick a spot you’re happy to share. You can "
                  "also email [hello@overberg.co](mailto:hello@overberg.co)."),
            ("note", "Only Android phones can join this test. On an iPhone or "
                     "a computer, districtry works in the browser at "
                     "[districtry.com](/)."),
        ]),
}

MARKER = "GENERATED by scripts/build_redirect_stubs.py"

SHORT_LINK_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>%(title)s</title>
<meta name="description" content="%(description)s" />
<meta name="robots" content="noindex" />
<!-- SHORT ADDRESS, GENERATED by scripts/build_redirect_stubs.py. Do not edit;
     change its entry in SHORT_LINKS there and regenerate. districtry.com/%(name)s
     is printed or posted where it cannot be taken back, so the address stays put
     and that entry says where it forwards today. noindex with no canonical,
     because nothing on this origin is the destination, and no counter, because
     the page leaves at once. -->
<meta http-equiv="refresh" content="0; url=%(target)s" />
<script>location.replace(%(target_js)s);</script>
<meta property="og:type" content="website" />
<meta property="og:site_name" content="districtry" />
<meta property="og:title" content="%(title)s" />
<meta property="og:description" content="%(description)s" />
<meta property="og:url" content="https://districtry.com/%(name)s" />
<meta property="og:image" content="https://districtry.com/og-image.png" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:image:alt" content="districtry — every district that covers a point, and who represents it." />
<meta name="twitter:card" content="summary_large_image" />
<link rel="icon" href="/favicon.svg" type="image/svg+xml" />
<link rel="icon" href="/favicon.ico" sizes="32x32" />
<style>
  :root {
    color-scheme: light dark;
    --ground: #f4f7f9; --ink: #14181c; --muted: #4a5560; --accent: #5730ab;
  }
  @media (prefers-color-scheme: dark) {
    :root { --ground: #121119; --ink: #eeebf6; --muted: #a39db6; --accent: #a98bff; }
  }
  body { margin: 0; padding: 48px 20px; background: var(--ground); color: var(--ink);
         font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  main { max-width: 34rem; margin: 0 auto; }
  h1 { font-size: 1.75rem; line-height: 1.2; margin: 0 0 0.5rem; }
  p { margin: 0 0 1rem; color: var(--muted); }
  a { color: var(--accent); font-weight: 600; }
  /* The one thing a reader can do here, so a target well past WCAG 2.5.8's
     24px: it is alone in its paragraph, which leaves the Inline exception
     nothing to be inline within. */
  .go a { display: inline-block; padding: 0.6rem 1rem; border: 2px solid var(--accent);
          border-radius: 6px; text-decoration: none; }
</style>
</head>
<body>
<main>
  <h1>%(title)s</h1>
  <p>%(lead)s</p>
  <p>%(note)s</p>
  <p class="go"><a href="%(target)s">%(link)s</a></p>
  <p>You should be taken there automatically. If not, follow the link above.</p>
</main>
</body>
</html>
"""

# The page form. Self-contained like the 404, with no webfont and no
# stylesheet to fetch, because it is opened from a phone's camera in a
# corridor or a meeting room and every extra request is a wait there.
SHORT_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>%(title)s</title>
<meta name="description" content="%(description)s" />
<meta name="robots" content="noindex" />
<!-- SHORT ADDRESS, GENERATED by scripts/build_redirect_stubs.py. Do not edit;
     change its entry in SHORT_LINKS there and regenerate. districtry.com/%(name)s
     is printed or posted where it cannot be taken back, so the address stays put
     and that entry says what it shows today. noindex with no canonical, because
     it is for the people holding that address rather than for search, and it
     carries the counter every page here carries. -->
%(goatcounter)s
<meta property="og:type" content="website" />
<meta property="og:site_name" content="districtry" />
<meta property="og:title" content="%(title)s" />
<meta property="og:description" content="%(description)s" />
<meta property="og:url" content="https://districtry.com/%(name)s" />
<meta property="og:image" content="https://districtry.com/og-image.png" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:image:alt" content="districtry — every district that covers a point, and who represents it." />
<meta name="twitter:card" content="summary_large_image" />
<link rel="icon" href="/favicon.svg" type="image/svg+xml" />
<link rel="icon" href="/favicon.ico" sizes="32x32" />
<style>
  :root {
    color-scheme: light dark;
    --ground: #f4f7f9; --ink: #14181c; --muted: #4a5560; --accent: #5730ab;
  }
  @media (prefers-color-scheme: dark) {
    :root { --ground: #121119; --ink: #eeebf6; --muted: #a39db6; --accent: #a98bff; }
  }
  body { margin: 0; padding: 32px 16px 48px; background: var(--ground); color: var(--ink);
         font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  main { max-width: 34rem; margin: 0 auto; }
  h1 { font-size: 1.75rem; line-height: 1.2; margin: 0 0 0.75rem; }
  h2 { font-size: 1.25rem; line-height: 1.3; margin: 2rem 0 0.75rem; }
  p, ul { margin: 0 0 1rem; }
  ul { padding-left: 1.25rem; }
  li { margin: 0 0 0.5rem; }
  .note { color: var(--muted); }
  a { color: var(--accent); font-weight: 600; }
  ol.steps { margin: 0 0 1rem; padding-left: 1.75rem; }
  ol.steps > li { margin: 0 0 1.25rem; padding-left: 0.25rem; }
  ol.steps > li::marker { color: var(--accent); font-weight: 700; }
  ol.steps p { margin: 0 0 0.6rem; }
  /* A step's button is the one thing to tap in it, so a target well past
     WCAG 2.5.8's 24px: it is alone in its paragraph, which leaves the Inline
     exception nothing to be inline within. A link inside a sentence keeps the
     exception. */
  .go a { display: inline-block; padding: 0.6rem 1rem; border: 2px solid var(--accent);
          border-radius: 6px; text-decoration: none; }
</style>
</head>
<body>
<main>
  <h1>%(title)s</h1>
%(body)s</main>
</body>
</html>
"""

# [words](address) in a page's text. Square brackets and parentheses are the
# whole syntax, so neither may appear inside one.
PAGE_LINK = re.compile(r"\[([^\[\]]+)\]\(([^()\s]+)\)")


NOT_FOUND = "404.html"

NOT_FOUND_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Page not found — districtry</title>
<meta name="robots" content="noindex, follow" />
<!-- GENERATED by scripts/build_redirect_stubs.py. Do not edit; change the script.
     GitHub Pages serves this file for any unmatched path across the whole site,
     with a real HTTP 404. Before it existed that was GitHub's own default page,
     which names this project nowhere and offers a reader no way back.

     No webfont, no external stylesheet, no script: this is the page somebody
     reaches when something is already wrong, and each extra request is one more
     thing that can fail underneath it. noindex keeps it out of sitemap.xml by
     construction, since build_sitemap.py excludes every noindex page. -->
<link rel="icon" href="/favicon.svg" type="image/svg+xml" />
<link rel="icon" href="/favicon.ico" sizes="32x32" />
<style>
  :root {
    color-scheme: light dark;
    --paper: #ffffff; --ground: #f4f7f9; --ink: #14181c; --muted: #4a5560;
    --accent: #5730ab; --rule: #dde3e8;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --paper: #1c1a25; --ground: #121119; --ink: #eeebf6; --muted: #a39db6;
      --accent: #a98bff; --rule: #2f2b3c;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 48px 20px; background: var(--ground); color: var(--ink);
         font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  main { max-width: 34rem; margin: 0 auto; }
  h1 { font-size: 1.75rem; line-height: 1.2; margin: 0 0 0.5rem; }
  p { margin: 0 0 1rem; color: var(--muted); }
  a { color: var(--accent); font-weight: 600; }
  ul { list-style: none; margin: 1.5rem 0 0; padding: 0;
       border-top: 1px solid var(--rule); }
  li { border-bottom: 1px solid var(--rule); }
  li a { display: block; padding: 0.85rem 0.25rem; text-decoration: none; }
  li a:hover, li a:focus-visible { background: var(--paper); }
  li span { display: block; font-weight: 400; color: var(--muted); font-size: 0.95rem; }
  /* 24px minimum target, WCAG 2.5.8. The Inline exception does not cover this
     one: it is the only thing in its paragraph, so there is no surrounding
     text for it to be inline WITHIN — the same three-part test
     scripts/page_consistency_test.mjs applies. Measured 17px before this. */
  .home { margin-top: 1.5rem; }
  .home a { display: inline-block; padding: 0.3rem 0; min-height: 24px; }
</style>
</head>
<body>
<main>
  <h1>Page not found</h1>
  <p>There is no page at this address. It may have moved, or the link may be wrong.</p>
  <p>districtry answers one question: which civic districts cover a point, and who
    represents you there. Pick where you are:</p>
  <ul>
%(instances)s  </ul>
  <p class="home"><a href="/">All of districtry</a></p>
</main>
</body>
</html>
"""


def fail(msg):
    sys.exit("build-redirect-stubs: FAIL — %s" % msg)


def render_not_found():
    """The 404, with its instance list read from metros.json."""
    with open(os.path.join(ROOT, "metros.json"), encoding="utf-8") as f:
        fleet = json.load(f)["metros"]
    if len(fleet) < 2:
        fail("metros.json lists %d instance(s); the 404 offers a choice and "
             "needs the real fleet." % len(fleet))
    rows = ""
    for m in fleet:
        for key in ("url", "landing_name", "scope"):
            if not m.get(key):
                fail("metros.json entry %r has no %s" % (m.get("tag"), key))
        # `scope` is the short descriptor the manifest already owns — "all 72
        # counties", "5 boroughs" — which is what a reader needs to tell
        # whether this is their place. The first draft truncated `blurb` at its
        # first full stop instead, and three of six ended mid-abbreviation on
        # "the Assembly, Senate and U". A sentence splitter that does not know
        # about "U.S." is not a sentence splitter.
        rows += ('    <li><a href="%s">%s<span>%s</span></a></li>\n'
                 % (html.escape(m["url"]), html.escape(m["landing_name"]),
                    html.escape(m["scope"])))
    return NOT_FOUND_TEMPLATE % {"instances": rows}


def phrases_for(path, override):
    """(tab title, body phrase) for one shell, from the target's own <title>."""
    if override:
        return override
    target = os.path.join(ROOT, "il", path)
    if not os.path.exists(target):
        fail("%s has no target at il/%s — remove it from STUBS or build the "
             "page." % (path, path))
    with open(target, encoding="utf-8") as f:
        head = f.read(8192)
    m = re.search(r"<title>([^<]*)</title>", head)
    if not m:
        fail("il/%s has no <title> in its first 8KB" % path)
    # Titles read "<question> — districtry Illinois"; the shell wants the
    # question. An em dash is the separator the whole fleet uses.
    phrase = html.unescape(m.group(1)).split(" — ")[0].strip()
    # A title may carry a second clause for search — il/ward.html is "Who is my
    # alderman? Chicago wards" — and only the question belongs in a sentence
    # reading "<phrase> now lives at". Cutting at the first question mark
    # reproduces all six hand-written shells and fixes the seventh.
    if "?" in phrase:
        phrase = phrase.split("?")[0].strip() + "?"
    return phrase, phrase


def render(path, override):
    title, phrase = phrases_for(path, override)
    return TEMPLATE % {"path": path, "title": title, "phrase": phrase}


def page_href(name, href):
    """An address a short page may link, escaped for an attribute: https://,
    mailto: or a path on this site, with nothing that needs quoting."""
    if not re.fullmatch(r"(https://|mailto:|/)[^\s\"'<>\\*()\[\]]*", href):
        fail("short address %s links %r; an address there is https://, mailto: "
             "or a path on this site, with nothing that needs quoting"
             % (name, href))
    if (href.startswith("https://")
            and urlsplit(href).hostname in ("districtry.com", "www.districtry.com")):
        fail("short address %s links %s in full; a page on this site is "
             "written as its path" % (name, href))
    return html.escape(href)


def page_text(name, text):
    """Escaped text with **bold** and [words](address), and nothing else."""
    parts, pos = [], 0
    for m in PAGE_LINK.finditer(text):
        parts.append(html.escape(text[pos:m.start()]))
        parts.append('<a href="%s">%s</a>' % (page_href(name, m.group(2)),
                                              html.escape(m.group(1))))
        pos = m.end()
    parts.append(html.escape(text[pos:]))
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", "".join(parts))
    # Whatever is left over is markup the two rules above did not read, and it
    # would reach the reader as stray asterisks or brackets.
    if re.search(r"[*\[\]]", out):
        fail("short address %s has text it cannot read as **bold** or "
             "[words](address): %r" % (name, text))
    return out


def page_block(name, block):
    """One block of a short page's body; see the comment above SHORT_LINKS."""
    kind, args = block[0], block[1:]
    if kind == "h2" and len(args) == 1:
        return "  <h2>%s</h2>\n" % html.escape(args[0])
    if kind in ("p", "note") and len(args) == 1:
        return "  <p%s>%s</p>\n" % (' class="note"' if kind == "note" else "",
                                    page_text(name, args[0]))
    if kind == "list" and len(args) == 1 and args[0]:
        return "  <ul>\n%s  </ul>\n" % "".join(
            "    <li>%s</li>\n" % page_text(name, item) for item in args[0])
    if kind == "steps" and len(args) == 1 and args[0]:
        items = ""
        for text, button in args[0]:
            items += "    <li>\n      <p>%s</p>\n" % page_text(name, text)
            if button:
                label, href = button
                items += ('      <p class="go"><a href="%s">%s</a></p>\n'
                          % (page_href(name, href), html.escape(label)))
            items += "    </li>\n"
        return '  <ol class="steps">\n%s  </ol>\n' % items
    fail("short address %s has a block it cannot render: %r" % (name, block))


def render_short_page(name, entry):
    """A short address that shows a page of its own."""
    for key in ("title", "description", "body"):
        if not entry.get(key):
            fail("short address %s has no %s" % (name, key))
    extra = sorted(set(entry) - {"title", "description", "body"})
    if extra:
        fail("short address %s is a page and carries %s, which only a forward "
             "reads" % (name, ", ".join(extra)))
    return SHORT_PAGE_TEMPLATE % {
        "name": name[:-len(".html")],
        "title": html.escape(entry["title"]),
        "description": html.escape(entry["description"]),
        "goatcounter": shared_goatcounter(),
        "body": "".join(page_block(name, b) for b in entry["body"]),
    }


def render_short_link(name, entry):
    """One short address: a forward off this origin, with the words a reader
    sees for the moment before it leaves, or a page of its own."""
    if name in STUBS or name == NOT_FOUND:
        fail("%s is both a short address and %s" % (
            name, "a redirect shell" if name in STUBS else "the 404"))
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.html", name):
        fail("short address %r must be one lowercase name at the root ending "
             "in .html, which GitHub Pages serves without the .html" % name)
    if ("target" in entry) == ("body" in entry):
        fail("short address %s needs exactly one of `target` (a forward) and "
             "`body` (a page)" % name)
    if "body" in entry:
        return render_short_page(name, entry)
    for key in ("target", "title", "description", "lead", "link", "note"):
        if not entry.get(key):
            fail("short address %s has no %s" % (name, key))
    target = entry["target"]
    if not target.startswith("https://") or re.search(r"[\s\"'<>\\]", target):
        fail("short address %s forwards to %r; a target is one https address "
             "with nothing that needs quoting" % (name, target))
    if urlsplit(target).hostname in ("districtry.com", "www.districtry.com"):
        fail("short address %s forwards to %s, on this origin. A path that "
             "moved to another page here is a shell, in STUBS." % (name, target))
    esc = {k: html.escape(entry[k]) for k in
           ("target", "title", "description", "lead", "link", "note")}
    return SHORT_LINK_TEMPLATE % dict(esc, name=name[:-len(".html")],
                                      target_js=json.dumps(target))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    targets = [(path, render(path, override))
               for path, override in sorted(STUBS.items())]
    targets += [(name, render_short_link(name, entry))
                for name, entry in sorted(SHORT_LINKS.items())]
    targets.append((NOT_FOUND, render_not_found()))

    # A root page that says this script made it, when nothing here makes it
    # any more: a retired short address would go on forwarding readers with
    # nothing checking where.
    owned = {path for path, _ in targets}
    orphans = []
    for page in sorted(glob.glob(os.path.join(ROOT, "*.html"))):
        if os.path.basename(page) in owned:
            continue
        with open(page, encoding="utf-8") as f:
            if MARKER in f.read():
                orphans.append(os.path.basename(page))
    if orphans:
        fail("%s say%s %s and no entry here makes %s any more. Delete the "
             "file, or restore its entry."
             % (", ".join(orphans), "s" if len(orphans) == 1 else "", MARKER,
                "it" if len(orphans) == 1 else "them"))

    current = {}
    for path, _want in targets:
        dest = os.path.join(ROOT, path)
        have = open(dest, encoding="utf-8").read() if os.path.exists(dest) else None
        # Asked of every target before anything is written, so a bad entry
        # cannot leave the files before it rewritten and the rest not.
        if have is not None and MARKER not in have:
            fail("%s is a page this script did not generate, and an entry here "
                 "would replace it. Give the entry another name." % path)
        current[path] = have

    stale, wrote = [], []
    for path, want in targets:
        dest = os.path.join(ROOT, path)
        have = current[path]
        if have == want:
            continue
        if args.check:
            stale.append(path + (" (missing)" if have is None else ""))
            continue
        with open(dest, "w", encoding="utf-8") as f:
            f.write(want)
        wrote.append(path)

    if args.check:
        if stale:
            fail("%d file(s) out of date: %s. Run "
                 "`python3 scripts/build_redirect_stubs.py`."
                 % (len(stale), ", ".join(stale)))
        print("build-redirect-stubs: OK — %d shell(s), %d short address(es) "
              "and the 404 current" % (len(STUBS), len(SHORT_LINKS)))
        return
    print("build-redirect-stubs: %d shell(s), %d short address(es) and the "
          "404, %d written%s"
          % (len(STUBS), len(SHORT_LINKS), len(wrote),
             (": " + ", ".join(wrote)) if wrote else ""))


if __name__ == "__main__":
    main()
