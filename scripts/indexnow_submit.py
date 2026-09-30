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

    python3 scripts/indexnow_submit.py                       # submit the homepage
    python3 scripts/indexnow_submit.py https://districtry.com/ https://districtry.com/other

Good times to run it: the first time the key file goes live (initial indexing),
and after any deploy that changes page content (e.g. a weekly roster refresh).
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
import json
import sys
import urllib.request

# ==== TEMPLATE:BEGIN indexnow-host ====
KEY = "6ce8d9c81c2e4b0b914e34fd134ed36e"
HOST = "districtry.com"
# ==== TEMPLATE:END indexnow-host ====
ENDPOINT = "https://api.indexnow.org/indexnow"  # shared endpoint: fans out to all IndexNow engines

def main():
    urls = sys.argv[1:] or ["https://%s/" % HOST]
    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": "https://%s/%s.txt" % (HOST, KEY),
        "urlList": urls,
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
            print("IndexNow %s %s — submitted %d URL(s):" % (resp.status, resp.reason, len(urls)))
            for u in urls:
                print("  " + u)
    except urllib.error.HTTPError as e:
        # 403 = key not found/valid at keyLocation; 422 = URL/host mismatch; 429 = too many.
        print("IndexNow rejected the submission: %s %s\n%s" % (e.code, e.reason, e.read().decode("utf-8", "replace")), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
