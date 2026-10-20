#!/usr/bin/env python3
"""
The address box on every question page — generated, never hand-kept.

WHAT A QUESTION PAGE IS. Each instance carries a handful of pages that answer
one question in prose — il/ward.html, wi/county-board.html, ny/council-district
.html and eight more. Every one of them ended with the same hand-off: a .cta
link that opens the map with the right layers on, and a note telling the reader
to search their address once they get there. The reader has already got their
address in mind on the question page; asking them to carry it through a
navigation is a step this does not need.

ONE BUTTON DOES BOTH (Adam, 2026-10-20: "I'd rather one button that can do
both. Search if an address is provided or open the map if not"). With an
address typed, the button opens the map and searches it; with the box left
empty, it opens the map with the same layers on and nothing searched. Until
that day the box sat above the .cta link it shortens, under an "Or open the
map" line, so a reader with JavaScript saw two buttons with the same words on
them, and an empty box answered "Type an address or ZIP first" instead of
opening the map. The .cta link and its note are now the NO-JAVASCRIPT path
only: the shell's stylesheet hides both once this form is shown (a sibling
rule in engine/shared/styles-subpage.txt, so nothing flashes), and a reader
whose browser runs no script still gets the link.

WHAT IT DOES NOT DO IS GEOCODE. The form builds `./#q=<address>` and hands the
typed text to the app, which runs the search it already runs, bounded to the
instance it already serves. Two things follow from that, and both are the
reason for it:

  * NO NEW RECIPIENT. Nothing on a question page contacts a third party. The
    privacy page measures each app's own index.html for the hosts it reaches,
    and a question page that called a geocoder itself would be a transmission
    that page names nowhere.
  * THE HASH, NOT THE QUERY STRING. GoatCounter's count.js sends
    location.search with every hit, so a `?q=` would put a reader's typed
    street address into the analytics record — on a site whose stated standard
    is that a selected point is rounded to two decimals before anything is
    sent. A hash never leaves the browser.

NOTHING HERE IS HAND-KEPT, which is the whole point of generating eleven copies
of one form rather than writing eleven. Every per-page fact is read off the
page itself or off metros.json:

  map link        the page's own .cta href after its `#`: its `layers=` and,
                  where the page names one, its `frame=` area
  button label    the .cta link's text, minus its trailing arrow
  place name      metros.json landing_name for the instance the page sits in

so a page that changes which layers it opens changes its form by regenerating,
and a page that stops carrying a .cta is reported rather than silently left
with a form pointing at layers it no longer names. The form opens exactly what
that link opens, with the typed address added in front.

THE FORM IS HIDDEN UNTIL ITS SCRIPT UNHIDES IT. A reader with no JavaScript
cannot submit it — the navigation is the script — so they get the .cta link
below it instead of an input that does nothing.

WHERE THE MAP OPENS is the app's business, not this form's: a link naming
layers and no point opens on the area those layers cover (ENGINE permalink,
LAYER_FRAMES from the worksheet's `frames`), so Chicago's school board page
opens on Chicago and a statewide layer's page on the state, whichever way the
reader leaves this page. A page about one area whose layers also answer
outside it names the area in its own link instead (`&frame=chicago` on
Chicago's ward page, whose ward layer draws suburban wards too), and this
fails on an area the page's app does not declare, because the app would
ignore it without a word and open the link as if it named no area.

    python3 scripts/build_question_forms.py           # write the regions
    python3 scripts/build_question_forms.py --check   # drift gate for CI
"""

import argparse
import html
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The dark-instance definition lives in ONE place: that gate reads
# deploy-pages.yml's own EXCLUDES, which is what actually decides whether a
# folder is published.
import validate_instance_registration
METROS = os.path.join(REPO_ROOT, "metros.json")

REGION = "question-lookup"
BEGIN = "<!-- ==== GENERATED:BEGIN %s ==== -->" % REGION
END = "<!-- ==== GENERATED:END %s ==== -->" % REGION

# The pages that are NOT question pages. Every other *.html in an instance
# folder is one if — and only if — it carries a .cta link, which is the real
# test; this list only keeps the report honest about what was skipped.
NOT_QUESTIONS = {"index.html", "faq.html", "sources.html", "history.html",
                 "privacy.html"}

CTA_RE = re.compile(
    r'<a class="cta" href="\./#(layers=[^"]+)">(.*?)</a>', re.S)
# What a .cta's hash may say: the layers, then optionally the area the map
# opens on. Nothing else, and only characters that need no escaping inside the
# script's string.
MAP_RE = re.compile(r"^layers=[a-z0-9,-]+(?:&frame=([a-z0-9-]+))?$")


def fail(msg):
    print("build-question-forms: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def instances():
    """Top-level directories that are an instance: index.html + data/app/.

    The TREE is canonical. Reading a table here would let this agree with
    itself about an instance nobody registered, which is the failure
    validate_instance_registration.py exists to catch one level up.

    A DARK INSTANCE IS SKIPPED, AND IS NOT THE UNREGISTERED CASE. A new state
    is built over several PRs behind one blanket `<tag>/**` line in
    deploy-pages.yml's EXCLUDES, and is deliberately absent from metros.json
    for exactly as long — validate_instance_registration.py holds those two
    together in both directions, so its answer is imported here rather than
    re-derived. The form this file writes names the instance's PLACE, read off
    metros.json, so a dark instance has no name to print; it also has no
    question page to carry a form, which is why skipping it costs nothing.
    """
    from validate_instance_registration import dark_instances
    dark = dark_instances()
    out = []
    for name in sorted(os.listdir(REPO_ROOT)):
        d = os.path.join(REPO_ROOT, name)
        if not os.path.isdir(d) or name.startswith("."):
            continue
        if name in dark:
            continue
        if os.path.isfile(os.path.join(d, "index.html")) and \
           os.path.isdir(os.path.join(d, "data", "app")):
            out.append(name)
    if len(out) < 2:
        fail("found %d instance(s) in %s — the discovery rule is broken"
             % (len(out), REPO_ROOT))
    return out


def instance_areas(tag):
    """The area names the instance's worksheet declares under `frames`."""
    rel = "metro-worksheet.json" if tag == "il" else os.path.join(tag, "metro-worksheet.json")
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as f:
        return set((json.load(f).get("frames") or {}).keys())


def landing_names():
    with open(METROS, encoding="utf-8") as f:
        doc = json.load(f)
    return {m["tag"]: m["landing_name"] for m in doc["metros"]}


def question_pages(tag):
    """(path, map link, label) for each page in <tag>/ that carries a .cta."""
    found = []
    d = os.path.join(REPO_ROOT, tag)
    for name in sorted(os.listdir(d)):
        if not name.endswith(".html") or name in NOT_QUESTIONS:
            continue
        path = os.path.join(d, name)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        m = CTA_RE.search(text)
        if not m:
            # A page carrying the region but no .cta is an orphan: its form
            # would point at layers nothing on the page still names.
            if BEGIN in text:
                fail("%s/%s carries a %s region and no .cta link — remove the "
                     "region or restore the link" % (tag, name, REGION))
            continue
        label = re.sub(r"\s+", " ", m.group(2)).strip()
        label = label.rstrip("→").strip()   # the trailing arrow
        link = html.unescape(m.group(1))
        shape = MAP_RE.match(link)
        if not shape:
            fail("%s/%s's map link says #%s; it may name its layers and an "
                 "area to open on (layers=…&frame=…) and nothing else"
                 % (tag, name, link))
        if shape.group(1) and shape.group(1) not in instance_areas(tag):
            fail("%s/%s's map link names the area %r, which %s's worksheet "
                 "does not declare under frames (%s) — the app would ignore "
                 "it and open the link as if it named no area"
                 % (tag, name, shape.group(1), tag,
                    ", ".join(sorted(instance_areas(tag))) or "none"))
        found.append((path, link, label))
    return found


def render(link, label, place):
    """The region's contents — everything BETWEEN the two markers."""
    body = '''<!-- GENERATED by scripts/build_question_forms.py — do not hand-edit.
     The map link and the button label are read from this page's own .cta
     link below; the place name comes from metros.json. Edit those, then rerun. -->
<form class="lookup" id="lookup" hidden>
  <div class="lookup-card">
    <label class="lookup-label" for="lookup-q">Your address or ZIP</label>
    <div class="lookup-row">
      <input class="lookup-input" id="lookup-q" name="q" type="search"
             autocomplete="street-address" enterkeyhint="go" autocapitalize="words"
             aria-describedby="lookup-hint"
             placeholder="Address or ZIP in %(place_attr)s">
      <button class="lookup-go" type="submit">%(label)s</button>
    </div>
    <p class="lookup-hint" id="lookup-hint">Or leave it blank to open the map and pick your location there.</p>
    <p class="lookup-status" id="lookup-status" role="status"></p>
  </div>
</form>
<script>
(function () {
  "use strict";
  // ONE button: with an address typed it opens the map and searches it, with
  // the box empty it opens the map the page's own link below opens. The
  // address goes to the app as a HASH, never a query string, which count.js
  // would send to the analytics host. The app geocodes; this does not.
  var MAP = "%(link)s";
  var form = document.getElementById("lookup");
  var input = document.getElementById("lookup-q");
  var status = document.getElementById("lookup-status");
  // The form sits ABOVE this script on purpose: it runs inline, at parse
  // time, so anything below it is not in the document yet. A first draft put
  // a line after this script that the guard below waited for, and the early
  // return left the form hidden on every page, which looked exactly like a
  // reader with JavaScript off.
  if (!form || !input || !status) return;
  // Shown only here, because only a reader whose browser runs this can submit
  // it. Showing it also hides the .cta link and its note below (a sibling
  // rule in the shell's stylesheet): that link is the same trip for a reader
  // with no script, and two buttons with the same words were one too many.
  form.hidden = false;
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var q = input.value.trim();
    status.textContent = "Opening the map\\u2026";
    window.location.href = q
      ? "./#q=" + encodeURIComponent(q) + "&" + MAP
      : "./#" + MAP;
  });
})();
</script>''' % {
        "place_attr": html.escape(place, quote=True),
        "label": html.escape(label),
        "link": link,
    }
    # A literal </script> anywhere inside the inline script ENDS the element,
    # whatever it is nested in — an HTML parser does not read JavaScript, so a
    # comment is no shelter. The first draft of the comment above explained the
    # ordering bug by naming the tag, which closed the script at that line and
    # left the rest of it as page text: no error a static read would show, and
    # a form that stays hidden on every page exactly as if the reader had
    # JavaScript off. One closing tag, at the end, and nowhere else.
    close = "</" + "script>"
    if body.count(close) != 1 or not body.rstrip().endswith(close):
        fail("the rendered form carries %d closing script tag(s) and must carry "
             "exactly one, at the end" % body.count(close))
    return body


def apply(path, body, check, rel):
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    if BEGIN in text:
        i = text.index(BEGIN) + len(BEGIN)
        j = text.index(END)
        current = text[i:j].strip("\n")
        if current == body:
            return ("current", None)
        if check:
            return ("drift", (current, body))
        new = text[:i] + "\n" + body + "\n" + text[j:]
    else:
        if check:
            return ("missing", None)
        # First insertion: immediately before the .cta link this form is the
        # short path to. The block is written FLUSH rather than at the cta's
        # indentation, because the region's contents are compared verbatim on
        # every --check and an indent applied at insertion and not at render
        # makes the very first check report drift against itself.
        m = CTA_RE.search(text)
        line_start = text.rfind("\n", 0, m.start()) + 1
        block = BEGIN + "\n" + body + "\n" + END + "\n"
        new = text[:line_start] + block + text[line_start:]
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(new)
    return ("written", None)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="drift gate: fail rather than write")
    args = ap.parse_args()

    names = landing_names()
    pages = 0
    drifted = []
    missing = []
    dark = validate_instance_registration.dark_instances() & set(instances())
    for tag in instances():
        if tag in dark:
            # A DARK INSTANCE HAS NO metros.json ENTRY YET, and that is correct
            # rather than drift: a new state is built over several PRs behind a
            # blanket `<tag>/**` exclude in deploy-pages.yml, and metros.json is
            # the switch that publishes it. This gate used to fail on that,
            # which Indiana hit on arrival in 2026-09 as the first dark instance
            # since this file was written — it took the whole fleet's question
            # forms red for a folder nobody is served.
            #
            # THE PLACE NAME IS NOT SUBSTITUTED FROM THE WORKSHEET INSTEAD, and
            # that was the tempting fix: `metro_name` and `landing_name` are
            # different keys that legitimately differ (Illinois is "Chicago" and
            # "Illinois"), so a form built from one and later regenerated from
            # the other drifts AT GO-LIVE, which is the worst moment for it. So
            # the pages are skipped and COUNTED, loudly, and the go-live change
            # regenerates them with every other generated surface.
            #
            # The definition comes from validate_instance_registration's own
            # reader of deploy-pages.yml — never a second list here.
            skipped = len(question_pages(tag))
            print("build-question-forms: %s dark (excluded from the deploy, so "
                  "absent from metros.json) — %d question page(s) skipped; the "
                  "go-live change must regenerate them" % (tag, skipped))
            continue
        if tag not in names:
            fail("instance %r is not in metros.json — the two must agree "
                 "before a question page there can name its place" % tag)
        for path, link, label in question_pages(tag):
            rel = os.path.relpath(path, REPO_ROOT)
            body = render(link, label, names[tag])
            state, detail = apply(path, body, args.check, rel)
            pages += 1
            if state == "drift":
                drifted.append((rel, detail))
            elif state == "missing":
                missing.append(rel)
            elif state == "written":
                print("build-question-forms: %s — region written" % rel)
    if not pages:
        fail("found no question page at all — the .cta discovery rule is broken")
    if args.check:
        for rel in missing:
            print("build-question-forms: %s has no %s region" % (rel, REGION),
                  file=sys.stderr)
        for rel, (cur, new) in drifted:
            print("build-question-forms: DRIFT in %s" % rel, file=sys.stderr)
            import difflib
            for dl in difflib.unified_diff(cur.splitlines(), new.splitlines(),
                                           fromfile="committed",
                                           tofile="regenerated", lineterm="", n=1):
                print("  " + dl, file=sys.stderr)
        if missing or drifted:
            fail("%d question page(s) out of date — run "
                 "python3 scripts/build_question_forms.py"
                 % (len(missing) + len(drifted)))
        print("build-question-forms: OK — %d question page(s) carry the address "
              "box their own .cta describes" % pages)
    else:
        print("build-question-forms: OK — %d question page(s)" % pages)


if __name__ == "__main__":
    main()
