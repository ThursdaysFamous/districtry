#!/usr/bin/env python3
"""Ping IndexNow so participating search engines recrawl within minutes.

IndexNow (https://www.indexnow.org/) lets a site tell search engines a URL
changed instead of waiting for organic discovery. It notifies Bing, Yandex,
Seznam, and Naver from a single submission — it does NOT feed Google, which
still relies on Search Console + its own crawl.

Ownership is proven by hosting the key as a plain-text file at the site root:

    https://districtry.com/6ce8d9c81c2e4b0b914e34fd134ed36e.txt

The key is a PUBLIC ownership token, not a secret — publishing it is the whole
point of the protocol, so it lives in the repo and deploys with the site.

Usage (run only AFTER a deploy where the key file is already live):

    python3 scripts/indexnow_submit.py --since <commit>      # the pages that changed
    python3 scripts/indexnow_submit.py --all                 # every page in sitemap.xml
    python3 scripts/indexnow_submit.py https://districtry.com/ https://districtry.com/other
    python3 scripts/indexnow_submit.py --since <commit> --dry-run   # list, send nothing

With no argument it submits the homepage, which is all the deploy ever sent
until 2026-11-03. Bing Webmaster Tools then reported "Some important pages
weren't submitted via IndexNow", severity High, naming five pages. The two
fleet-wide edits of 31 October and 1 November had changed every one of the
1,545 pages in the sitemap, and the deploys after them submitted one address
each, the homepage. So the deploy now passes
--since with the commit the last notified deploy published, and this script
submits:

  * every page whose file changed between that commit and this one, and that
    is in either commit's sitemap.xml (so a deleted page is submitted too,
    which is how IndexNow tells an engine to drop it);
  * every page that entered or left the sitemap between the two, which is how
    a dark instance going live is submitted although its files did not change.

THE SITEMAP DECIDES WHAT COUNTS AS A PAGE, never a pattern over the tree:
build_sitemap.py already leaves out redirect shells, noindex pages, dark
instances and the coverage map's frame, and submitting any of those would ask
an engine to index a page the site itself says not to. A data file is not a
page and is not submitted. --all is for a one-time catch-up and for the first
time the key goes live; it is never what a deploy sends by default, because
IndexNow asks for changed addresses and resending 1,500 unchanged ones on
every deploy is the pattern it says not to send.

Exits non-zero if IndexNow rejects the submission.

NOT GATED ON robots.txt, BECAUSE NOTHING IS BEING READ. This SUBMITS
districtry's own addresses to an ingestion endpoint that exists to receive
them, authenticated by a key published on districtry's own domain -- the
direction is outbound, and the thing being handed over is a list of our own
urls. robots.txt tells a crawler which of a site's pages it may READ; there is
no page here to read and no content of api.indexnow.org's that this wants.

THE TEST IS WHOSE CONTENT AND WHICH DIRECTION, never which host. An
unauthenticated read of a page on that host would be gated in full, and so
would following any url this endpoint returned.
"""
import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

# ==== TEMPLATE:BEGIN indexnow-host ====
KEY = "6ce8d9c81c2e4b0b914e34fd134ed36e"
HOST = "districtry.com"
# ==== TEMPLATE:END indexnow-host ====
ENDPOINT = "https://api.indexnow.org/indexnow"  # shared endpoint: fans out to all IndexNow engines
SITE = "https://%s/" % HOST
SITEMAP = "sitemap.xml"
BATCH = 10000  # the protocol's ceiling on urlList in one POST
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def sitemap_urls(text):
    """Every <loc> in a sitemap's text, as a set. An empty text is an empty set."""
    if not text:
        return set()
    root = ET.fromstring(text)
    return {el.text.strip() for el in root.iter(SITEMAP_NS + "loc") if el.text}


def path_url(path):
    """The address a published .html file serves at, or None for anything else.
    `index.html` serves at its directory, which is how the sitemap writes it."""
    if not path.endswith(".html"):
        return None
    if path == "index.html":
        return SITE
    if path.endswith("/index.html"):
        return SITE + path[:-len("index.html")]
    return SITE + path


def git(*args):
    return subprocess.run(["git"] + list(args), check=True,
                          capture_output=True, text=True).stdout


def sitemap_at(commit):
    """sitemap.xml as committed at `commit`, or "" if it had none."""
    try:
        return git("show", "%s:%s" % (commit, SITEMAP))
    except subprocess.CalledProcessError:
        return ""


def changed_urls(base, head="HEAD"):
    """The pages a search engine should recrawl after `base` was replaced by
    `head`: see the module docstring for the two rules."""
    old = sitemap_urls(sitemap_at(base))
    new = sitemap_urls(sitemap_at(head))
    paths = git("diff", "--name-only", "--no-renames", base, head).split("\n")
    touched = {u for u in (path_url(p.strip()) for p in paths if p.strip()) if u}
    return (touched & (old | new)) | (old ^ new)


def submit(urls):
    for i in range(0, len(urls), BATCH):
        chunk = urls[i:i + BATCH]
        payload = {
            "host": HOST,
            "key": KEY,
            "keyLocation": "https://%s/%s.txt" % (HOST, KEY),
            "urlList": chunk,
        }
        req = urllib.request.Request(
            ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                # IndexNow returns 200 (accepted) or 202 (accepted, pending validation).
                print("IndexNow %s %s — submitted %d URL(s)" % (resp.status, resp.reason, len(chunk)))
        except urllib.error.HTTPError as e:
            # 403 = key not found/valid at keyLocation; 422 = URL/host mismatch; 429 = too many.
            print("IndexNow rejected the submission: %s %s\n%s" % (e.code, e.reason, e.read().decode("utf-8", "replace")), file=sys.stderr)
            sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("urls", nargs="*", help="addresses to submit as given")
    ap.add_argument("--since", metavar="COMMIT",
                    help="submit the pages that changed since this commit")
    ap.add_argument("--all", action="store_true",
                    help="submit every page in sitemap.xml")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the list and send nothing")
    args = ap.parse_args()
    if sum(bool(x) for x in (args.urls, args.since, args.all)) > 1:
        ap.error("give addresses, --since or --all, not more than one")

    if args.all:
        with open(SITEMAP, encoding="utf-8") as f:
            urls = sitemap_urls(f.read())
        why = "every page in %s" % SITEMAP
    elif args.since:
        urls = changed_urls(args.since)
        why = "pages changed since %s" % args.since[:12]
    else:
        urls = set(args.urls or [SITE])
        why = "as given"

    foreign = sorted(u for u in urls if not u.startswith(SITE))
    if foreign:
        # IndexNow answers 422 for the whole batch if one address is on another host.
        sys.exit("not on %s, refusing to submit: %s" % (HOST, ", ".join(foreign)))
    urls = sorted(urls)
    print("%d URL(s), %s:" % (len(urls), why))
    for u in urls:
        print("  " + u)
    if not urls:
        print("Nothing a search engine indexes changed; nothing submitted.")
        return
    if args.dry_run:
        print("Dry run; nothing submitted.")
        return
    submit(urls)


if __name__ == "__main__":
    main()
