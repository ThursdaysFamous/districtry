#!/usr/bin/env python3
"""
Every page's JSON-LD: parses, resolves, and counts what it says it counts.

WHY. The site went from 8 structured-data nodes describing people to 3,000-odd
in one change (2026-09-16): 183 county boards and 20 rostered question pages now
publish `member` -> `OrganizationRole` -> `Person`, an `ItemList` of seats, and
a `DataCatalog` per sources page. All of it is generated, and each generator's
own `--check` proves its page matches what that generator produces today — which
is a different question from whether the graph is coherent. A dangling `@id`, a
list whose `numberOfItems` disagrees with its own elements, or a block that no
longer parses would pass every one of those gates.

WHAT IT CHECKS, and each one is a way the graph can be wrong while every page
still looks right:

  * every ld+json block PARSES. A block a consumer cannot read says nothing, and
    nothing else here reads them — `page_consistency_test.mjs` boots a browser,
    where an unparseable block is silently ignored.
  * every `@id` is absolute and under this site. A relative or foreign id names
    somebody else's entity.
  * no `@id` is DEFINED twice on one page with different content. Two nodes
    claiming one identity is the one error a consumer resolves by picking one.
  * every `{"@id": ...}` REFERENCE resolves to a node defined on the same page,
    except the three site-wide nodes each page legitimately points at.
  * `ItemList.numberOfItems` equals the number of elements, and the positions
    run 1..n with no gaps. This is the count a reader of the graph trusts, and
    it is exactly the claim the page's own prose makes in words.
  * every `Person` carries a non-empty `name`. A Person node with no name is
    the shape a roster gap takes if it is ever rendered rather than skipped.

WHAT IT DOES NOT CHECK is whether schema.org would approve of a type choice —
that is a reading, not a measurement, and the generators record their reasoning
where they make one.

    python3 scripts/validate_structured_data.py
    python3 scripts/validate_structured_data.py --report   # per-page counts
"""

import argparse
import collections
import glob
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://districtry.com"
BLOCK = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)

# Nodes the whole site shares. Each is DEFINED on an index page — the fleet
# root's or an instance's — and REFERENCED from every sub-page under it, which is
# what @id is for; a reference to one of these from a page that does not define
# it is correct rather than dangling. The bare `#website` is the fleet root's,
# which the four root sub-pages point at; the two-letter form is an instance's.
SITE_WIDE = re.compile(r"^%s/(#author|#publisher|#website|[a-z]{2}/#website)$"
                       % re.escape(SITE))


def fail(msg):
    print("validate-structured-data: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def pages():
    """Every authored page in the tree. DISCOVERED, never listed — the rule
    validate_card_links.py and build_sitemap.py already discover by, so a new
    instance or a new per-county page is covered the day it ships. engine/ holds
    a DIRECTORY named index.html (the per-fence store compose_app.py splices
    from), which the glob cannot tell from a file."""
    out = []
    for pattern in ("*.html", "*/*.html", "*/*/*.html"):
        for path in sorted(glob.glob(os.path.join(REPO_ROOT, pattern))):
            rel = os.path.relpath(path, REPO_ROOT)
            # The noindexed rebrand preview under districtry/ is not a page.
            if rel.split(os.sep)[0] == "districtry" or not os.path.isfile(path):
                continue
            out.append(rel)
    return out


def walk(node, visit):
    if isinstance(node, dict):
        visit(node)
        for value in node.values():
            walk(value, visit)
    elif isinstance(node, list):
        for value in node:
            walk(value, visit)


def check_page(rel, problems, counts):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as f:
        text = f.read()
    blocks = BLOCK.findall(text)
    if not blocks:
        return
    defined, referenced = {}, set()

    def visit(node):
        node_id = node.get("@id")
        if isinstance(node_id, str):
            if not node_id.startswith(SITE):
                problems.append("%s: @id %r is not under %s" % (rel, node_id, SITE))
            # A node that carries ONLY an @id is a reference; one that carries
            # anything else is a definition. That is the whole distinction, and
            # it is the one JSON-LD itself draws.
            if len(node) == 1:
                referenced.add(node_id)
            else:
                body = json.dumps(node, sort_keys=True)
                if node_id in defined and defined[node_id] != body:
                    problems.append("%s: @id %r is defined twice with different "
                                    "content" % (rel, node_id))
                defined[node_id] = body
        if node.get("@type") == "Person" and not (node.get("name") or "").strip():
            problems.append("%s: a Person node carries no name" % rel)
        if node.get("@type") == "ItemList":
            elements = node.get("itemListElement") or []
            stated = node.get("numberOfItems")
            if stated is not None and stated != len(elements):
                problems.append("%s: ItemList %s says numberOfItems %s and "
                                "carries %d" % (rel, node.get("@id", "(no @id)"),
                                                stated, len(elements)))
            want = list(range(1, len(elements) + 1))
            got = [e.get("position") for e in elements if isinstance(e, dict)]
            if got != want:
                problems.append("%s: ItemList %s positions are not 1..%d"
                                % (rel, node.get("@id", "(no @id)"), len(elements)))
            counts["lists"] += 1
        if node.get("@type") in ("GovernmentOrganization", "Organization"):
            counts["orgs"] += 1
        if node.get("@type") == "Person":
            counts["people"] += 1
        if node.get("@type") == "Dataset":
            counts["datasets"] += 1

    for block in blocks:
        try:
            data = json.loads(block.replace("<\\/", "</"))
        except ValueError as exc:
            problems.append("%s: an ld+json block does not parse — %s" % (rel, exc))
            continue
        counts["blocks"] += 1
        walk(data, visit)

    for node_id in sorted(referenced - set(defined)):
        if SITE_WIDE.match(node_id):
            continue
        problems.append("%s: @id %r is referenced and defined nowhere on the "
                        "page" % (rel, node_id))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true",
                    help="print the node counts this found, per type")
    args = ap.parse_args()

    problems = []
    counts = collections.Counter()
    seen = 0
    for rel in pages():
        before = counts["blocks"]
        check_page(rel, problems, counts)
        if counts["blocks"] > before:
            seen += 1

    if not seen:
        fail("no page in the tree carries an ld+json block — this gate reads "
             "them from the tree, so finding none means the discovery is broken "
             "rather than that the site has none")

    if args.report:
        for key in sorted(counts):
            print("  %-10s %d" % (key, counts[key]))

    if problems:
        for line in problems[:40]:
            print("validate-structured-data: " + line, file=sys.stderr)
        fail("%d problem(s) across %d page(s)" % (len(problems), seen))

    print("validate-structured-data: OK — %d block(s) on %d page(s) parse; "
          "%d organisation(s), %d person node(s), %d list(s) whose counts and "
          "positions hold, %d dataset(s); every @id absolute, unique on its "
          "page, and resolving" % (counts["blocks"], seen, counts["orgs"],
                                   counts["people"], counts["lists"],
                                   counts["datasets"]))


if __name__ == "__main__":
    main()
