#!/usr/bin/env python3
"""
/llms.txt — the short guide to what this site answers and where each answer
came from, for a client reading the site rather than crawling it.

WHY IT IS GENERATED. The llms.txt convention is a hand-written markdown file,
and a hand-written one here would be wrong within a week: it would list the
instances, their layer counts, their topic pages and the number of per-county
board pages, and every one of those moves. This repo's standing finding is that
brand and fleet facts decay into scattered literals the moment they are typed
twice — 98 files carrying `chidistricts`, a redesign built twice because
index.html could not be parameterised — which is why the landing page, the
privacy page, the sources matrix and the county pages are all generated. A
guide that tells a reader what is here has no business being the one file that
lies about it.

So every fact comes from the file that already owns it:

  metros.json              the fleet: each instance's tag, landing_name, blurb
                           and url. A new instance appears here and nowhere
                           else.
  <tag>/metro-worksheet.json
                           that instance's layer count and verified_date.
  sitemap.xml              WHICH PAGES EXIST. Generated itself, and already
                           exactly the set this guide wants: it excludes the
                           six root redirect shells left behind by the R2.3
                           move and il/privacy.html (each canonicalises
                           elsewhere), and coverage-map.html, which carries no
                           canonical at all because it is the landing page's
                           iframe body rather than a destination. A skip list
                           here would have had to name all eight and would rot;
                           the depth test (a URL two segments deep or less is a
                           guide page, deeper is one of the per-county pages an
                           index links) is the same one
                           page_consistency_test.mjs samples by.
  each page's own <title>  so a renamed page renames itself here.
  robots.txt               the Content-Signal, PARSED by scripts/robots_policy.py
                           rather than restated, so the terms section cannot
                           say something the published signal does not.
  build_county_pages       the per-county board pages, counted per instance off
                           its own output directory.

WHAT IT IS NOT. Not a sitemap: sitemap.xml lists all 201 URLs and this lists
the handful a reader needs to find the rest. Not a data dump: the boundaries
and rosters are in each instance's data/app/ and the page that cites them is
what gets linked, because a name without its source is the thing this project
refuses everywhere else.

  python3 scripts/build_llms_txt.py            # (re)generate in place
  python3 scripts/build_llms_txt.py --check    # the CI drift gate
"""

import glob
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from robots_policy import RobotsPolicy  # noqa: E402

OUT = os.path.join(REPO_ROOT, "llms.txt")
SITE = "https://districtry.com"

# The order root pages appear in, ahead of the instances. A root page not
# named here still ships, after these — the list is a preference, not a gate,
# because a new root page must not go missing for want of an edit here.
ROOT_ORDER = ("privacy.html", "sponsorship.html", "traffic.html")

# The one sentence the generator owns, because no file in the tree holds it.
SUMMARY = ("Click a point, or type an address, and see every civic district "
           "that covers it — and who holds those seats. Six instances across "
           "Illinois, Wisconsin, Iowa, Michigan, New York City and San "
           "Francisco. Every boundary and every name comes from a published "
           "source and is cited to it.")


def fail(msg):
    print("build-llms-txt: FAIL — %s" % msg, file=sys.stderr)
    raise SystemExit(1)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def instances():
    """The fleet, from metros.json, checked against the tree.

    metros.json is the fleet's single source and the tree is what actually
    ships, so a mismatch either way is a failure rather than a silent skip:
    an entry with no folder would publish a link to nothing, and a folder with
    no entry is exactly the unregistered-instance case
    validate_instance_registration.py exists for."""
    listed = json.loads(read(os.path.join(REPO_ROOT, "metros.json")))["metros"]
    on_disk = {d for d in os.listdir(REPO_ROOT)
               if os.path.isdir(os.path.join(REPO_ROOT, d, "data", "app"))
               and os.path.exists(os.path.join(REPO_ROOT, d, "index.html"))}
    tags = {m["tag"] for m in listed}
    if tags != on_disk:
        fail("metros.json lists %s and the tree carries %s — "
             "scripts/validate_instance_registration.py names what to edit"
             % (sorted(tags), sorted(on_disk)))
    return listed


def worksheet(tag):
    path = os.path.join(REPO_ROOT, "metro-worksheet.json" if tag == "il"
                        else os.path.join(tag, "metro-worksheet.json"))
    if not os.path.exists(path):
        fail("%s has no worksheet at %s" % (tag, os.path.relpath(path, REPO_ROOT)))
    return json.loads(read(path))


def title_of(rel):
    """A page's own <title>, minus the ` — districtry <place>` tail the brand
    skin appends. Read rather than restated, so renaming a page's title renames
    its line here; only the first 8 KB is scanned, which is where every one of
    these pages puts it."""
    path = os.path.join(REPO_ROOT, rel)
    if not os.path.exists(path):
        fail("sitemap.xml lists /%s and the tree does not carry it — run "
             "`python3 scripts/build_sitemap.py`" % rel)
    m = re.search(r"<title>(.*?)</title>", read(path)[:8192], re.S)
    if not m:
        fail("%s carries no <title> in its first 8 KB" % rel)
    t = re.sub(r"\s+", " ", m.group(1)).strip()
    for esc, ch in (("&amp;", "&"), ("&#x27;", "'"), ("&quot;", '"'),
                    ("&lt;", "<"), ("&gt;", ">")):
        t = t.replace(esc, ch)
    t = re.split(r"\s+—\s+districtry\b", t)[0].strip()
    if not t:
        fail("%s's title is nothing but the brand tail" % rel)
    return t


def sitemap_paths():
    """Every page the sitemap lists, grouped by where it belongs in this guide.

    THE SITEMAP IS THE PAGE SET, not a glob of the tree, and that is what lets
    this file carry no skip list. Eight authored pages exist that a reader
    should never be sent to — the six root redirect shells the R2.3 move left
    behind, il/privacy.html, and coverage-map.html — and the sitemap already
    omits all eight, because build_sitemap.py includes a page on its canonical
    and those either name another path or carry none.

    Returns (root, by_tag, deep_count_by_tag). A URL two segments deep or less
    is a guide page; deeper is one of the per-county board pages, which are
    counted rather than listed — there are 164 of them and the index page each
    instance already publishes is the thing to link."""
    text = read(os.path.join(REPO_ROOT, "sitemap.xml"))
    locs = re.findall(r"<loc>([^<]+)</loc>", text)
    if not locs:
        fail("sitemap.xml lists no <loc> — nothing to guide a reader to")
    root, by_tag, deep = [], {}, {}
    for url in locs:
        if not url.startswith(SITE + "/"):
            fail("sitemap.xml carries %s, which is not on %s" % (url, SITE))
        rel = url[len(SITE) + 1:]
        parts = [p for p in rel.split("/") if p]
        if len(parts) > 2:
            deep[parts[0]] = deep.get(parts[0], 0) + 1
            continue
        if rel in ("", "index.html"):
            continue                      # the front door, named on its own
        if rel.endswith("/"):
            # An instance's app — `/ca/` is one segment like `/privacy.html` is,
            # so the trailing slash is the only thing separating them. Each app
            # is named from its metros.json entry instead.
            continue
        if len(parts) == 1:
            root.append(rel)
        else:
            by_tag.setdefault(parts[0], []).append(rel)
    for tag in by_tag:
        by_tag[tag].sort(key=lambda r: (r.endswith("history.html"),
                                        r.endswith("faq.html"), r))
    root.sort(key=lambda r: (ROOT_ORDER.index(r) if r in ROOT_ORDER
                             else len(ROOT_ORDER), r))
    return root, by_tag, deep


def county_index(tag, deep_count):
    """Which of this instance's pages is the index for its per-county pages.

    Matched by DIRECTORY rather than by name: <tag>/<concept>/ holds the pages
    and <tag>/<concept>.html is their index, which is how build_county_pages.py
    writes them. Nothing here needs to know that Illinois calls the concept
    county-board and Iowa county-supervisor."""
    if not deep_count:
        return None
    dirs = [d for d in sorted(os.listdir(os.path.join(REPO_ROOT, tag)))
            if os.path.isdir(os.path.join(REPO_ROOT, tag, d))
            and glob.glob(os.path.join(REPO_ROOT, tag, d, "*.html"))
            and os.path.exists(os.path.join(REPO_ROOT, tag, d + ".html"))]
    if len(dirs) != 1:
        fail("%s has %d directory(ies) of generated pages (%s) and the sitemap "
             "lists %d of them — this generator names one index per instance"
             % (tag, len(dirs), ", ".join(dirs) or "none", deep_count))
    return "%s/%s.html" % (tag, dirs[0])


def signal():
    """The published Content-Signal, parsed from robots.txt by the one reader.

    PARSED AND NOT RESTATED. The terms section below tells a reader what the
    site asks for, and a hand-typed copy of it could disagree with the file a
    client actually fetches — which is the one disagreement that matters here,
    because the file is the reservation and the prose is only a courtesy."""
    pol = RobotsPolicy(read(os.path.join(REPO_ROOT, "robots.txt")))
    sig = pol.content_signal("*")
    if not sig:
        fail("robots.txt publishes no Content-Signal that scripts/robots_policy.py "
             "can read from its `*` group — the terms section would be a claim "
             "about a line that says nothing")
    return sig


def render():
    fleet = instances()
    sig = signal()
    root, by_tag, deep = sitemap_paths()
    lines = ["# districtry", "", "> " + SUMMARY, ""]

    lines.append("Free, no account, no tracking of individuals. The map runs in "
                 "the browser; what each page sends to whom is listed at "
                 "%s/privacy.html." % SITE)
    lines.append("")

    lines.append("## The whole site")
    lines.append("")
    lines.append("- [districtry](%s/): the front door. Type an address and it "
                 "opens whichever instance covers it, with the point already "
                 "selected; a point nobody covers is told so rather than routed "
                 "somewhere wrong." % SITE)
    for rel in root:
        lines.append("- [%s](%s/%s)" % (title_of(rel), SITE, rel))
    lines.append("")

    verified = sorted({worksheet(m["tag"]).get("verified_date")
                       for m in fleet} - {None})

    for m in fleet:
        tag, ws = m["tag"], worksheet(m["tag"])
        index = county_index(tag, deep.get(tag, 0))
        lines.append("## %s" % m["landing_name"])
        lines.append("")
        lines.append(m["blurb"])
        lines.append("")
        lines.append("- [%s district lookup](%s): %d layers, %s."
                     % (m["landing_name"], m["url"], len(ws["layers"]),
                        m["scope"]))
        for rel in by_tag.get(tag, []):
            if rel == index:
                lines.append("- [%s](%s/%s): links a page per county, %d of "
                             "them, each naming every member with whatever "
                             "contact details that county publishes."
                             % (title_of(rel), SITE, rel, deep[tag]))
            else:
                lines.append("- [%s](%s/%s)" % (title_of(rel), SITE, rel))
        lines.append("")

    lines.append("## Where the answers come from")
    lines.append("")
    lines.append("Each instance's sources page carries one row per layer: what "
                 "it answers, the publisher its boundary comes from, where the "
                 "names on its card come from, and the ground it answers on. "
                 "That page is generated from the same list that registers the "
                 "layers, so a layer cannot ship without a row.")
    lines.append("")
    lines.append("Officeholder names are never guessed. Where no verifiable "
                 "roster exists, a card links the official body instead of "
                 "inventing a name, and what the project does not know is "
                 "recorded rather than left blank — each instance ships a "
                 "machine-readable list of its own gaps at "
                 "`<instance>/data/app/coverage-gaps.json`.")
    lines.append("")
    if len(verified) == 1:
        lines.append("Sources last reverified %s." % verified[0])
    elif verified:
        lines.append("Sources last reverified between %s and %s, per instance."
                     % (verified[0], verified[-1]))
        lines.append("")
    lines.append("")
    lines.append("This is a civic reference tool and it disclaims legal "
                 "precision. Confirm a district assignment with the "
                 "government office that draws it before relying on it for "
                 "anything official.")
    lines.append("")

    lines.append("## Terms")
    lines.append("")
    lines.append("`%s/robots.txt` publishes a Content-Signal, and these are the "
                 "values in it: %s."
                 % (SITE, ", ".join("%s=%s" % kv for kv in sorted(sig.items()))))
    lines.append("")
    lines.append("In plain words: indexing and search are welcome, and so is "
                 "grounding an answer in these pages, on the terms the signal "
                 "names — by reference, with a link back to the page that names "
                 "the person, so a reader can check the government source "
                 "behind it. Training is reserved. No crawler is disallowed by "
                 "name: a site that wants its answers found does not gain "
                 "anything by refusing the clients that find them.")
    lines.append("")
    lines.append("The boundaries and rosters are public records from the "
                 "publishers each sources page names; this project's own work "
                 "is the collection, the citation and the code.")
    lines.append("")
    lines.append("Corrections: corrections@overberg.co. Source: "
                 "https://github.com/ThursdaysFamous/districtry")
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).rstrip("\n") + "\n"

    # EVERY LINK TO THIS SITE MUST BE A PAGE THE SITEMAP LISTS. The generator
    # derives them from the sitemap, so this cannot fail by accident — which is
    # the point: it fails when somebody adds a hand-typed link to the prose, the
    # one way a file whose whole job is pointing a crawler somewhere could point
    # it at a 404. Outbound links (the repository) are not this check's subject;
    # validate_card_links.py probes them monthly, which is why llms.txt is in
    # its authored surface.
    listed = {u for u in re.findall(r"<loc>([^<]+)</loc>",
                                    read(os.path.join(REPO_ROOT, "sitemap.xml")))}
    for url in sorted(set(re.findall(r"\(%s([^)]*)\)" % re.escape(SITE), text))):
        if SITE + url not in listed:
            fail("llms.txt would link %s%s, which sitemap.xml does not list — a "
                 "guide for crawlers cannot point at a page that is not there"
                 % (SITE, url))
    return text


def main():
    check = "--check" in sys.argv[1:]
    text = render()
    current = read(OUT) if os.path.exists(OUT) else ""
    if check:
        if current != text:
            fail("llms.txt is stale. Run `python3 scripts/build_llms_txt.py`.")
    elif current != text:
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(text)
    root, by_tag, deep = sitemap_paths()
    print("build-llms-txt: OK — %s, %d line(s): %d instance(s), %d root page(s), "
          "%d instance page(s), %d per-county page(s) counted not listed; "
          "signal %s"
          % ("current" if check else "written", text.count("\n"),
             len(instances()), len(root), sum(len(v) for v in by_tag.values()),
             sum(deep.values()),
             ",".join("%s=%s" % kv for kv in sorted(signal().items()))))


if __name__ == "__main__":
    main()
