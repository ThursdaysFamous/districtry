#!/usr/bin/env python3
"""Copy the published site's large files to the Cloudflare R2 bucket.

The vector-tile archives (<tag>/data/app/tiles/) and the Census block
populations (<tag>/data/app/population/) were 320 MB of a 747 MB published
site on 2026-11-10, and GitHub Pages stops publishing a site past 1 GB. On that
day Adam chose to keep the pages on GitHub and serve these two folders from an
R2 bucket at files.districtry.com, at the same paths. R2 answers the byte
ranges a tile archive is read by; Cloudflare's page hosting answers a range
with the whole file (Cloudflare's own documentation, and measured that day),
which is why the pages themselves did not move.

THE BOUNDARY FILES ARE COPIED TOO, SINCE 2026-11-16 (Adam's "Start" of that day
on moving the map files off GitHub). Measured that day with all fifty states
live, the site without the two folders was 664.6 MB, and 463.5 MB of that was
902 boundary files: the whole-file geometry each app's service worker lists as
GEOMETRY_URLS and serves cache-first. They are read out of each app's sw.js IN
THE TREE, the list the worker itself goes by, so a file is on the files host
exactly when the worker treats its bytes as fixed until the cache name moves.
Rosters and election results are not copied: they change weekly or daily, the
pages that print them are rebuilt in the same change, and GitHub Pages
publishes a page and its roster together, which two hosts cannot. The copies
came first, in a change of their own. THE MAPS READ THEM HERE SINCE THE CHANGE
AFTER IT: on the live site a page asks the files host for each file in its
BOUNDARY_FILES list and its worker for each in GEOMETRY_URLS (filesUrl in
engine/shared/files-origin.txt; both lists are generated from one worksheet
key, and --selftest holds every app's two to each other). GitHub Pages published
the boundary files as well for a week, so a tab opened before the switch kept
working. --leave-out stops that (the third change): after the copy it removes
from the assembled tree both folders and every boundary file except those a
page at the site's root names (the front page's and coverage map's outlines,
which are not apps and read this site), so GitHub Pages publishes none of the
rest. Reading the boundary files from this site again now means publishing
them here again as well as sending filesUrl back to this site for them, in one
change. FILES_ORIGIN null on its own would also send the tile archives and
populations back here, which would take the site past GitHub Pages' 1 GB.

This script makes the bucket hold exactly what the deploy is about to publish
of those files. It reads the ASSEMBLED tree (deploy-pages.yml's _site), not
the checkout, because the assemble step is what leaves the dark instances and
the build inputs out, and a file the deploy would not publish must not be put
on a public host either.

  * A file is uploaded when the bucket has no object at its path or the
    object's ETag is not the file's MD5. Every upload is one PUT, so an ETag is
    always the MD5 of the bytes (R2 gives a multipart object another kind).
    Comparing hashes rather than dates is the point: a fresh checkout dates
    every file to the minute it ran, so a date test would upload all of them
    on every publish, about 1,900 writes 14 times a day, past R2's free
    million a month.
  * A MANAGED object with no file in the tree is deleted, so a retired archive
    or boundary file stops being served as it would on Pages. Managed means
    under one of the two folders, or a .json directly inside an app's
    data/app/: a boundary file that leaves its worker's list (retired, or
    reclassified as a roster) is therefore deleted too, and a roster is never
    there to begin with. More than MAX_DELETE_SHARE of them at once is refused
    unless --allow-mass-delete is given, because that is what a tree assembled
    wrong looks like.
  * Anything else in the bucket is left alone.
  * After the writes the bucket is listed again and every file must be there
    with its MD5, or the run fails.
  * An app whose sw.js is missing, or carries no GEOMETRY_URLS list this
    script can read, or lists a boundary file the tree does not hold, fails
    the run before anything is changed. Reading "no list" as "no boundary
    files" would delete every one of that app's copies.

--probe then asks the question the copy cannot: what a reader's browser gets
from files.districtry.com, which is the bucket's custom domain and its CORS
rule, two Cloudflare settings outside the bucket. It reads a sample the way a
map on the site does (a preflight, byte ranges with the site's Origin, a
population file) and compares the bytes with the tree. It needs no credentials.

It is stdlib only (the deploy installs nothing), so it signs its own requests
with AWS Signature Version 4, which R2 takes with region "auto". --selftest
holds the signer to AWS's published examples and the planner to fixtures, with
no network.

It reads no robots.txt, and validate_robots_adoption.py records it as exempt:
robots.txt says which of a site's pages a crawler may read, and this reads
nobody's pages. It lists and writes this project's own bucket through the
storage API, with the key issued to this project for exactly that, and the
only bytes it moves are this site's own files, mostly outbound; --probe reads
back a few of those same files from this project's own files host.

Credentials come from the environment: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID and
R2_SECRET_ACCESS_KEY (repository secrets). With any of them missing the run
says so and does nothing, unless --require is given.

    python3 scripts/sync_r2_files.py --tree _site            # sync
    python3 scripts/sync_r2_files.py --tree _site --dry-run  # list, change nothing
    python3 scripts/sync_r2_files.py --tree _site --probe    # read the files host as a map does
    python3 scripts/sync_r2_files.py --tree _site --leave-out  # remove what the files host serves from the tree
    python3 scripts/sync_r2_files.py --selftest
"""
import argparse
import base64
import concurrent.futures
import datetime
import gzip
import hashlib
import hmac
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BUCKET = "districtry-files"
REGION = "auto"
SERVICE = "s3"
# What this script owns in the bucket, under any instance tag: the two folders,
# and a .json directly inside an app's data/app/ (where the boundary files
# are). A key outside that is never uploaded, compared or deleted.
MANAGED_RE = re.compile(r"^[a-z]{2}/data/app/(?:(?:tiles|population)/.+|[^/]+\.json)$")
FOLDER_RE = re.compile(r"^[a-z]{2}/data/app/(tiles|population)/.+")
TAG_RE = re.compile(r"^[a-z]{2}$")
# The worker's cache-first list, as generate_metro_files.py writes it into each
# app's sw.js: one "./data/app/<file>" per line. Read from the tree, never from
# a worksheet, for the reason the tree is read at all.
GEOMETRY_LIST_RE = re.compile(r"^const GEOMETRY_URLS = \[\n(.*?)^\];", re.S | re.M)
GEOMETRY_ENTRY_RE = re.compile(r'^\s*"\./data/app/([^"/]+\.json)",?\s*$')
CONTENT_TYPES = {".pmtiles": "application/octet-stream", ".json": "application/json"}
# GitHub Pages serves every file with max-age=600; the files keep that, since
# an archive keeps its address when it is rebuilt.
CACHE_CONTROL = "public, max-age=600"
MAX_DELETE_SHARE = 0.10
UPLOAD_WORKERS = 8
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


# ---------- signing (AWS Signature Version 4) ----------

def _uri_encode(s, keep_slash):
    return urllib.parse.quote(s, safe="-_.~" + ("/" if keep_slash else ""))


def sign_headers(method, host, path, query, headers, payload_sha256,
                 access_key, secret_key, amz_date, region=REGION, service=SERVICE):
    """Return a copy of `headers` with x-amz-date, x-amz-content-sha256 and
    Authorization added. `path` is the unencoded object path ("/bucket/key"),
    `query` a list of (name, value) pairs."""
    h = dict(headers)
    h["host"] = host
    h["x-amz-date"] = amz_date
    h["x-amz-content-sha256"] = payload_sha256
    lower = {k.lower(): " ".join(str(v).split()) for k, v in h.items()}
    names = sorted(lower)
    canonical = "\n".join([
        method,
        _uri_encode(path, True),
        "&".join("%s=%s" % (_uri_encode(k, False), _uri_encode(v, False))
                 for k, v in sorted(query)),
        "".join("%s:%s\n" % (n, lower[n]) for n in names),
        ";".join(names),
        payload_sha256,
    ])
    date = amz_date[:8]
    scope = "%s/%s/%s/aws4_request" % (date, region, service)
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope,
                         hashlib.sha256(canonical.encode()).hexdigest()])
    key = ("AWS4" + secret_key).encode()
    for part in (date, region, service, "aws4_request"):
        key = hmac.new(key, part.encode(), hashlib.sha256).digest()
    sig = hmac.new(key, to_sign.encode(), hashlib.sha256).hexdigest()
    h["Authorization"] = ("AWS4-HMAC-SHA256 Credential=%s/%s, SignedHeaders=%s, Signature=%s"
                          % (access_key, scope, ";".join(names), sig))
    del h["host"]  # urllib sets it from the URL
    return h, sig


class R2:
    def __init__(self, account_id, access_key, secret_key, bucket=BUCKET, endpoint=None):
        # `endpoint` is for the selftest's loopback stand-in; R2's own is the
        # account's host.
        self.endpoint = endpoint or "https://%s.r2.cloudflarestorage.com" % account_id
        self.host = urllib.parse.urlsplit(self.endpoint).netloc
        self.access_key, self.secret_key, self.bucket = access_key, secret_key, bucket

    def request(self, method, key="", query=(), body=b"", headers=None, attempts=4):
        path = "/" + self.bucket + ("/" + key if key else "")
        url = self.endpoint + _uri_encode(path, True)
        if query:
            url += "?" + "&".join("%s=%s" % (_uri_encode(k, False), _uri_encode(v, False))
                                  for k, v in query)
        for attempt in range(attempts):
            amz_date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            signed, _ = sign_headers(method, self.host, path, list(query), headers or {},
                                     hashlib.sha256(body).hexdigest(), self.access_key,
                                     self.secret_key, amz_date)
            req = urllib.request.Request(url, data=body if method in ("PUT", "POST") else None,
                                         method=method, headers=signed)
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    return resp.status, resp.read(), dict(resp.headers)
            except urllib.error.HTTPError as e:
                detail = e.read()[:500].decode("utf-8", "replace")
                # 4xx other than throttling is the request's fault: retrying
                # cannot help and would hide a refused key behind four tries.
                if e.code < 500 and e.code != 429:
                    raise RuntimeError("%s %s answered %d: %s" % (method, key or "/", e.code, detail))
                last = "%d: %s" % (e.code, detail)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last = str(e)
            time.sleep(2 ** (attempt + 1))
        raise RuntimeError("%s %s failed after %d tries: %s" % (method, key or "/", attempts, last))

    def list_objects(self):
        """{key: etag-without-quotes} for every object in the bucket."""
        out, token = {}, None
        ns = "{http://s3.amazonaws.com/doc/2006-03-01/}"
        while True:
            query = [("list-type", "2"), ("max-keys", "1000")]
            if token:
                query.append(("continuation-token", token))
            _, body, _ = self.request("GET", query=query)
            root = ET.fromstring(body)
            for c in root.iter(ns + "Contents"):
                out[c.find(ns + "Key").text] = (c.find(ns + "ETag").text or "").strip('"')
            truncated = (root.findtext(ns + "IsTruncated") or "false") == "true"
            token = root.findtext(ns + "NextContinuationToken")
            if not truncated or not token:
                return out

    def put(self, key, body):
        ext = os.path.splitext(key)[1]
        self.request("PUT", key, body=body, headers={
            "Content-Type": CONTENT_TYPES.get(ext, "application/octet-stream"),
            "Cache-Control": CACHE_CONTROL,
            "Content-MD5": base64.b64encode(hashlib.md5(body).digest()).decode(),
        })

    def delete(self, key):
        self.request("DELETE", key)


# ---------- planning ----------

class TreeError(Exception):
    """The assembled tree cannot be read for what it publishes."""


def boundary_files(tree, tag):
    """The names of the boundary files app `tag` reads whole: its worker's
    GEOMETRY_URLS, read from <tree>/<tag>/sw.js. Raises TreeError when the
    list cannot be read or names a file the tree does not hold, because
    answering "none" for an app that has some would delete its copies."""
    sw = os.path.join(tree, tag, "sw.js")
    if not os.path.isfile(sw):
        raise TreeError("%s/data/app is published and %s/sw.js is not, so its boundary files cannot be listed" % (tag, tag))
    with open(sw, encoding="utf-8") as f:
        lists = GEOMETRY_LIST_RE.findall(f.read())
    if len(lists) != 1:
        raise TreeError("%s/sw.js carries %d GEOMETRY_URLS lists this script can read, not 1" % (tag, len(lists)))
    names = []
    for line in lists[0].splitlines():
        if not line.strip() or line.strip().startswith("//"):
            continue
        m = GEOMETRY_ENTRY_RE.match(line)
        if not m:
            raise TreeError("%s/sw.js GEOMETRY_URLS has a line this script cannot read: %r" % (tag, line.strip()[:120]))
        names.append(m.group(1))
    if len(set(names)) != len(names):
        raise TreeError("%s/sw.js GEOMETRY_URLS names a file twice" % tag)
    missing = [n for n in names if not os.path.isfile(os.path.join(tree, tag, "data", "app", n))]
    if missing:
        raise TreeError("%s/sw.js lists %d boundary file(s) the tree does not hold: %s"
                        % (tag, len(missing), ", ".join(missing[:5])))
    return names


def local_files(tree):
    """{key: md5 hex} for every file the bucket serves: everything under
    <tag>/data/app/{tiles,population}/ in the assembled tree, and each app's
    boundary files (boundary_files)."""
    out = {}

    def take(full):
        key = os.path.relpath(full, tree).replace(os.sep, "/")
        if not MANAGED_RE.match(key):
            return
        with open(full, "rb") as f:
            out[key] = hashlib.md5(f.read()).hexdigest()

    for tag in sorted(os.listdir(tree)):
        if not TAG_RE.match(tag) or not os.path.isdir(os.path.join(tree, tag, "data", "app")):
            continue
        for folder in ("tiles", "population"):
            top = os.path.join(tree, tag, "data", "app", folder)
            if not os.path.isdir(top):
                continue
            for dirpath, _, names in os.walk(top):
                for n in names:
                    take(os.path.join(dirpath, n))
        for n in boundary_files(tree, tag):
            take(os.path.join(tree, tag, "data", "app", n))
    return out


def kind_of(key):
    m = FOLDER_RE.match(key)
    return m.group(1) if m else "boundary"


def by_kind(keys):
    """"282 tiles, 3192 population, 902 boundary" for a list of keys."""
    counts = {}
    for k in keys:
        counts[kind_of(k)] = counts.get(kind_of(k), 0) + 1
    return ", ".join("%d %s" % (counts[k], k) for k in ("tiles", "population", "boundary") if k in counts) or "none"


def plan(local, remote):
    """(uploads, deletes, unchanged) as sorted key lists. Only managed keys
    of `remote` are considered."""
    managed = {k: v for k, v in remote.items() if MANAGED_RE.match(k)}
    uploads = sorted(k for k, md5 in local.items() if managed.get(k) != md5)
    deletes = sorted(k for k in managed if k not in local)
    unchanged = sorted(k for k, md5 in local.items() if managed.get(k) == md5)
    return uploads, deletes, unchanged


def delete_refusal(deletes, remote, allow):
    managed = sum(1 for k in remote if MANAGED_RE.match(k))
    if allow or not deletes or managed == 0:
        return None
    if len(deletes) > 20 and len(deletes) > MAX_DELETE_SHARE * managed:
        return ("would delete %d of the bucket's %d managed objects (more than %d%%); "
                "a tree assembled wrong looks like this, so nothing was changed. "
                "Re-run with --allow-mass-delete if the deletions are meant"
                % (len(deletes), managed, int(MAX_DELETE_SHARE * 100)))
    return None


def verify(local, remote):
    """Keys the bucket is missing or holds with other bytes."""
    return sorted(k for k, md5 in local.items() if remote.get(k) != md5)


# ---------- leaving the files out of what GitHub Pages publishes ----------

ROOT_PAGE_FILE_RE = re.compile(r"\b([a-z]{2}/data/app/[A-Za-z0-9_.-]+\.json)\b")


def root_page_files(tree):
    """Instance data files a page at the site's root names: every
    <tag>/data/app/<name>.json in an .html file directly inside `tree`. Those
    pages (the front page's outlines and example rosters, the coverage map's
    outlines) are not apps, carry no filesUrl, and read this site."""
    out = set()
    for n in sorted(os.listdir(tree)):
        full = os.path.join(tree, n)
        if n.endswith(".html") and os.path.isfile(full):
            with open(full, encoding="utf-8") as f:
                out.update(ROOT_PAGE_FILE_RE.findall(f.read()))
    return out


def leave_to_files_host(tree):
    """Remove from the assembled tree everything the files host serves (both
    folders and every boundary file) except the boundary files a root page
    reads. Returns (files removed, bytes removed, kept keys). Raises TreeError
    when a file a root page names is missing afterwards or a removed file is
    still there; run it after the copy, which reads the same tree."""
    named = root_page_files(tree)
    served = local_files(tree)
    kept = sorted(k for k in served if kind_of(k) == "boundary" and k in named)
    gone = [k for k in served if k not in kept]
    size = 0
    for k in gone:
        full = os.path.join(tree, k)
        size += os.path.getsize(full)
        os.remove(full)
    for tag in os.listdir(tree):
        for folder in ("tiles", "population"):
            top = os.path.join(tree, tag, "data", "app", folder)
            if TAG_RE.match(tag) and os.path.isdir(top):
                shutil.rmtree(top)
    missing = sorted(k for k in named if not os.path.isfile(os.path.join(tree, k)))
    if missing:
        raise TreeError("a root page names %d file(s) the published tree no longer holds: %s"
                        % (len(missing), ", ".join(missing[:5])))
    left = [k for k in gone if os.path.exists(os.path.join(tree, k))]
    if left:
        raise TreeError("%d file(s) the files host serves are still in the published tree" % len(left))
    return len(gone), size, kept


# ---------- selftest ----------

def selftest():
    # AWS's worked examples for Signature Version 4 on S3 ("Signature
    # Calculations for the Authorization Header: Transferring Payload in a
    # Single Chunk"), with its example keys and region us-east-1.
    ak, sk = "AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    host = "examplebucket.s3.amazonaws.com"
    _, sig = sign_headers("GET", host, "/test.txt", [], {"Range": "bytes=0-9"},
                          EMPTY_SHA256, ak, sk, "20130524T000000Z", "us-east-1", "s3")
    assert sig == "f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41", sig
    _, sig = sign_headers("GET", host, "/", [("max-keys", "2"), ("prefix", "J")], {},
                          EMPTY_SHA256, ak, sk, "20130524T000000Z", "us-east-1", "s3")
    assert sig == "34b48302e7b5fa45bde8084f4b7868a86f0a534bc59db6670ed5711ef69dc6f7", sig
    body = b"Welcome to Amazon S3."
    _, sig = sign_headers("PUT", host, "/test$file.text", [],
                          {"Date": "Fri, 24 May 2013 00:00:00 GMT",
                           "x-amz-storage-class": "REDUCED_REDUNDANCY"},
                          hashlib.sha256(body).hexdigest(), ak, sk, "20130524T000000Z",
                          "us-east-1", "s3")
    assert sig == "98ad721746da40c64f1a55b78f14c238d841ea1380cd77a1b5971af0ece108bd", sig

    local = {"il/data/app/tiles/a.pmtiles": "1", "il/data/app/tiles/b.pmtiles": "2",
             "wi/data/app/population/index.json": "3", "il/data/app/wards.json": "7",
             "il/data/app/outline.json": "8"}
    remote = {"il/data/app/tiles/a.pmtiles": "1", "il/data/app/tiles/b.pmtiles": "9",
              "il/data/app/tiles/old.pmtiles": "4", "notes/readme.txt": "5",
              "il/data/app/retired.json": "6", "il/data/app/outline.json": "8",
              "il/data/app/election-results/ward-1.json": "10", "il/index.html": "11"}
    up, de, same = plan(local, remote)
    assert up == ["il/data/app/tiles/b.pmtiles", "il/data/app/wards.json",
                  "wi/data/app/population/index.json"], up
    # A boundary file no worker lists any more goes, like a retired archive;
    # never notes/, a page, or a file in a folder this script does not own.
    assert de == ["il/data/app/retired.json", "il/data/app/tiles/old.pmtiles"], de
    assert same == ["il/data/app/outline.json", "il/data/app/tiles/a.pmtiles"], same
    assert not MANAGED_RE.match("ga2/data/app/tiles/x") and not MANAGED_RE.match("il/data/app/tilesx")
    for owned in ("il/data/app/wards.json", "il/data/app/tiles/a.pmtiles", "wi/data/app/population/55/001.json"):
        assert MANAGED_RE.match(owned), owned
    for not_owned in ("il/data/app/election-results/ward-1.json", "il/data/app/README.md", "il/data/wards.json",
                      "il/index.html", "fleet-outlines.json", "app/data/app/x.json2", "ill/data/app/x.json"):
        assert not MANAGED_RE.match(not_owned), not_owned
    assert by_kind(local) == "2 tiles, 1 population, 2 boundary", by_kind(local)
    big = {"il/data/app/tiles/%d.pmtiles" % i: "x" for i in range(100)}
    assert delete_refusal(sorted(big)[:21], big, False)  # 21 of 100: refused
    assert delete_refusal(sorted(big)[:21], big, True) is None
    assert delete_refusal(sorted(big)[:5], big, False) is None  # a handful is ordinary
    assert verify(local, {**remote, "wi/data/app/population/index.json": "3"}) == [
        "il/data/app/tiles/b.pmtiles", "il/data/app/wards.json"]

    import contextlib
    import io
    import tempfile
    sw = ('const CACHE_NAME = "x-v1";\n\nconst GEOMETRY_URLS = [\n%s];\n\n'
          'const ROSTER_URLS = [\n  "./data/app/roster.json",\n];\n')
    with tempfile.TemporaryDirectory() as d:
        for rel, data in (("il/data/app/tiles/a.pmtiles", b"A"), ("il/data/app/population/17031.json", b"P"),
                          ("il/data/app/roster.json", b"R"), ("il/index.html", b"H"),
                          ("il/data/app/wards.json", b"W"), ("il/data/app/outline.json", b"O"),
                          ("il/data/app/unlisted.json", b"U"),
                          ("il/data/app/election-results/ward-1.json", b"E"),
                          ("il/sw.js", (sw % '  "./data/app/wards.json",\n  "./data/app/outline.json",\n').encode()),
                          ("app/sw.js", b"// the launcher's worker: no list, and no data/app beside it"),
                          ("fonts/x.woff2", b"F")):
            os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
            with open(os.path.join(d, rel), "wb") as f:
                f.write(data)
        assert boundary_files(d, "il") == ["wards.json", "outline.json"]
        got = local_files(d)
        # The two folders and the files the worker lists; never a roster, an
        # election result, a page, or a data file no list names.
        assert got == {"il/data/app/tiles/a.pmtiles": hashlib.md5(b"A").hexdigest(),
                       "il/data/app/population/17031.json": hashlib.md5(b"P").hexdigest(),
                       "il/data/app/wards.json": hashlib.md5(b"W").hexdigest(),
                       "il/data/app/outline.json": hashlib.md5(b"O").hexdigest()}, got
        # A whole run against a loopback stand-in for the bucket: what is
        # uploaded, what is left alone, what is deleted, and that every request
        # was signed for the host it was sent to.
        e2e = run_against_stand_in(d)
        urls = check_files_url(got)
        # Leaving the files out of what GitHub publishes: both folders and every
        # boundary file go, bar one a root page names; a roster, a page and a
        # data file no list names stay. A root page naming a file the tree
        # lacks afterwards stops the deploy.
        with open(os.path.join(d, "index.html"), "w") as f:
            f.write('<script>var o = "il/data/app/outline.json", r = "il/data/app/roster.json";</script>')
        t = os.path.join(d, "..", os.path.basename(d) + "-leave-out")
        shutil.copytree(d, t)
        try:
            count, size, kept = leave_to_files_host(t)
            assert (count, size, kept) == (3, 3, ["il/data/app/outline.json"]), (count, size, kept)
            assert not os.path.exists(os.path.join(t, "il", "data", "app", "tiles"))
            assert not os.path.exists(os.path.join(t, "il", "data", "app", "population"))
            for stays in ("il/data/app/outline.json", "il/data/app/roster.json", "il/data/app/unlisted.json",
                          "il/data/app/election-results/ward-1.json", "il/index.html", "il/sw.js", "index.html"):
                assert os.path.isfile(os.path.join(t, stays)), stays
            assert not os.path.exists(os.path.join(t, "il", "data", "app", "wards.json"))
            shutil.rmtree(t)
            shutil.copytree(d, t)
            with open(os.path.join(t, "coverage-map.html"), "w") as f:
                f.write('fetch("il/data/app/nothere.json")')
            try:
                leave_to_files_host(t)
            except TreeError as e:
                assert "il/data/app/nothere.json" in str(e), str(e)
            else:
                raise AssertionError("a root page naming a file the tree lacks was let through")
        finally:
            shutil.rmtree(t, ignore_errors=True)
            os.remove(os.path.join(d, "index.html"))
        # A tree whose list cannot be read stops the run before the bucket is
        # asked anything: each of these would otherwise read as "this app has no
        # boundary files" and delete its copies.
        refused = 0
        for name, text, words in (
                ("no list", "const ROSTER_URLS = [];\n", "0 GEOMETRY_URLS lists"),
                ("another shape", 'const GEOMETRY_URLS = ["./data/app/wards.json"];\n', "0 GEOMETRY_URLS lists"),
                ("a line it cannot read", sw % '  "./data/app/wards.json",\n  "data/app/outline.json",\n', "cannot read"),
                ("a folder", sw % '  "./data/app/tiles/a.pmtiles",\n', "cannot read"),
                ("a file twice", sw % '  "./data/app/wards.json",\n  "./data/app/wards.json",\n', "twice"),
                ("a file the tree lacks", sw % '  "./data/app/wards.json",\n  "./data/app/gone.json",\n', "does not hold: gone.json")):
            with open(os.path.join(d, "il", "sw.js"), "w") as f:
                f.write(text)
            try:
                local_files(d)
            except TreeError as e:
                assert words in str(e), (name, str(e))
                refused += 1
            else:
                raise AssertionError("a worker with %s was read as a list" % name)
            with contextlib.redirect_stdout(io.StringIO()) as said:
                assert sync(None, d) == 1, name  # ...and the run fails without touching the bucket
            assert "nothing was changed" in said.getvalue(), said.getvalue()
        os.remove(os.path.join(d, "il", "sw.js"))
        try:
            local_files(d)
        except TreeError as e:
            assert "sw.js is not" in str(e), str(e)
            refused += 1
        else:
            raise AssertionError("an app with no worker was read as having no boundary files")
        # An empty list is a list: an app can have no boundary file of its own.
        with open(os.path.join(d, "il", "sw.js"), "w") as f:
            f.write("const GEOMETRY_URLS = [\n];\n")
        assert boundary_files(d, "il") == []
    read = run_probe_against_stand_in()
    print("sync_r2_files: selftest OK — 3 AWS signing examples, the planner, the delete guard, "
          "the tree walk, leaving the files out, %d unreadable workers refused, %s, %s and %s" % (refused, e2e, urls, read))


FILES_BLOCK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine", "shared", "files-origin.txt")


def check_files_url(keys):
    """The page's filesUrl (engine/shared/files-origin.txt, the block every app
    and service worker carries), run in Node, must ask the files host for each
    file at the very key this script uploads it under, and must leave a page
    anywhere but the live host, and every other file, on its own site.

    A boundary file is found by NAME, in the list its app carries: the page's
    BOUNDARY_FILES (bare names) and the worker's GEOMETRY_URLS (./data/app/
    paths), both generated from one worksheet key. Each case is therefore run
    twice, once as the page and once as the worker, and the two must agree."""
    import json
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        raise AssertionError("node is needed to run the files-origin block")
    block = open(FILES_BLOCK).read()
    assert len(re.findall(r"var FILES_ORIGIN = [^;]*;", block)) == 1, "FILES_ORIGIN must be one var line"
    # The live host the block switches on is the one the site is published at.
    cname = open(os.path.join(os.path.dirname(FILES_BLOCK), "..", "..", "CNAME")).read().strip()
    site = re.search(r'var FILES_SITE_HOST = "([^"]*)";', block)
    assert site and site.group(1) == cname, "FILES_SITE_HOST %r is not CNAME's %r" % (site and site.group(1), cname)
    stand_in = re.sub(r"var FILES_ORIGIN = [^;]*;", 'var FILES_ORIGIN = "https://files.example";', block)
    # Each app's boundary files by name: every key that is not under one of
    # the two folders is one (the caller passes exactly what the copy uploads).
    names = {}
    for k in sorted(keys):
        if not FOLDER_RE.match(k):
            tag, rel = k.split("/", 1)
            assert rel.startswith("data/app/") and "/" not in rel[len("data/app/"):], k
            names.setdefault(tag, []).append(rel[len("data/app/"):])
    assert names, "the fixture holds no boundary file, so the boundary case would test nothing"
    cases = []
    for k in sorted(keys):
        tag, rel = k.split("/", 1)
        # SINCE THE SWITCH (2026-11-16) every key the copy uploads is read
        # from the files host on the live site: the two folders by their
        # path, a boundary file by its name in the app's own list.
        cases.append(["live", "https://districtry.com/%s/" % tag, rel, "https://files.example/" + k])
        cases.append(["local", "http://localhost:8000/%s/" % tag, rel, "http://localhost:8000/" + k])
    some_tag = sorted(names)[0]
    some = names[some_tag][0]
    site = "https://districtry.com/%s/" % some_tag
    # What must STAY on the site, on the live host: a roster; a root file; a
    # file with a boundary file's name in a folder below data/app (an election
    # results part); and another app's file of the same name, which is not in
    # THIS app's list and which this app's worker would not keep.
    cases.append(["live", site, "data/app/roster.json", site + "data/app/roster.json"])
    cases.append(["live", site, "../fleet-outlines.json", "https://districtry.com/fleet-outlines.json"])
    cases.append(["live", site, "data/app/election-results/" + some, site + "data/app/election-results/" + some])
    cases.append(["live", site, "../zz/data/app/" + some, "https://districtry.com/zz/data/app/" + some])
    # ...and a boundary file asked for with a query string keeps it.
    cases.append(["live", site, "data/app/%s?v=2" % some, "https://files.example/%s/data/app/%s?v=2" % (some_tag, some)])

    def run(src, worker):
        # The page stands at <site>/<tag>/ with a hash a permalink would carry;
        # the worker at <site>/<tag>/sw.js. Each carries its own list.
        prog = ("var cases = %s, names = %s, worker = %s; var out = [];\n"
                "cases.forEach(function (c) {\n"
                "  var here = new URL(worker ? 'sw.js' : '#p=41.9,-87.6&l=wd', c[1]);\n"
                "  var location = { origin: here.origin, hostname: here.hostname, href: here.href };\n"
                "  var mine = names[here.pathname.split('/')[1]] || [];\n"
                "  var lists = worker\n"
                "    ? 'var GEOMETRY_URLS = ' + JSON.stringify(mine.map(function (n) { return './data/app/' + n; })) + ';\\n'\n"
                "    : 'var BOUNDARY_FILES = ' + JSON.stringify(mine) + ';\\n';\n"
                "  out.push(eval(lists + %s + '\\nfilesUrl(' + JSON.stringify(c[2]) + ', ' + JSON.stringify(c[1]) + ')'));\n"
                "});\nprocess.stdout.write(JSON.stringify(out));"
                % (json.dumps(cases), json.dumps(names), json.dumps(worker), json.dumps(src)))
        res = subprocess.run([node, "-e", prog], capture_output=True, text=True, timeout=60)
        assert res.returncode == 0, res.stderr
        return json.loads(res.stdout)

    def both(src):
        page, worker = run(src, False), run(src, True)
        assert page == worker, [(c, a, b) for c, a, b in zip(cases, page, worker) if a != b][:3]
        return page

    for c, got in zip(cases, both(stand_in)):
        assert got == c[3], (c, got)
    # A page with NO list (a block spliced into a page the generator gave
    # none) sends nothing to the files host by name, and still sends the two
    # folders there: a missing list must not throw, or no file would load.
    prog = ("var location = { origin: 'https://districtry.com', hostname: 'districtry.com', href: 'https://districtry.com/il/' };\n"
            "process.stdout.write(JSON.stringify(eval(%s + '\\n[filesUrl(\"data/app/x.json\", location.href), "
            "filesUrl(\"data/app/tiles/a.pmtiles\", location.href)]')));" % json.dumps(stand_in))
    res = subprocess.run([node, "-e", prog], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    assert json.loads(res.stdout) == ["https://districtry.com/il/data/app/x.json",
                                      "https://files.example/il/data/app/tiles/a.pmtiles"], res.stdout
    shipped = re.search(r"var FILES_ORIGIN = ([^;]*);", block).group(1)
    if shipped == "null":   # the way back: every file from the page's own site
        for c, got in zip(cases, both(block)):
            assert got == c[1].rstrip("/").rsplit("/", 1)[0] + "/" + c[3].split("/", 3)[3], (c, got)
    else:
        # The shipped origin is the files subdomain of the published site and
        # nothing else, so a typo in it cannot send every map somewhere else.
        origin = json.loads(shipped)
        assert origin == "https://files." + cname, "FILES_ORIGIN %r is not https://files.%s" % (origin, cname)
        for c, got in zip(cases, both(block)):
            assert got == c[3].replace("https://files.example", origin, 1), (c, got)
    lists = check_page_lists()
    return ("filesUrl run in Node, as the page and as the worker, asking for every tile, population "
            "and boundary file at its upload key and for nothing else, and %s" % lists)


PAGE_LIST_RE = re.compile(r"^  var BOUNDARY_FILES = \[(.*?)\];$", re.M | re.S)


def check_page_lists():
    """In the checkout, every app's page must carry the same boundary file
    names as its worker. The copy uploads the WORKER's list; the page asks the
    files host for the files in ITS list. A name only the page had would be
    asked of the files host and not be there, on the live site alone, where no
    test on localhost reads it. generate_metro_files.py writes both from one
    worksheet key and its --check holds each to the worksheet; this holds the
    two files to each other, as shipped."""
    import json
    root = os.path.join(os.path.dirname(FILES_BLOCK), "..", "..")
    apps = 0
    for tag in sorted(os.listdir(root)):
        page = os.path.join(root, tag, "index.html")
        if not (os.path.isfile(page) and os.path.isdir(os.path.join(root, tag, "data", "app"))):
            continue
        with open(page, encoding="utf-8") as f:
            found = PAGE_LIST_RE.findall(f.read())
        assert len(found) == 1, "%s/index.html carries %d BOUNDARY_FILES lists, not one" % (tag, len(found))
        mine = json.loads("[" + found[0] + "]")
        theirs = boundary_files(root, tag)
        assert sorted(mine) == sorted(theirs), (
            "%s: the page's BOUNDARY_FILES and sw.js's GEOMETRY_URLS differ: %s"
            % (tag, sorted(set(mine) ^ set(theirs))[:5]))
        apps += 1
    assert apps >= 2, "found %d app(s) in the checkout" % apps
    return "%d apps' pages listing the boundary files their workers list" % apps


def shipped_origin():
    """FILES_ORIGIN as the block ships it, or None."""
    import json
    m = re.search(r"var FILES_ORIGIN = ([^;]*);", open(FILES_BLOCK).read())
    return json.loads(m.group(1)) if m else None


# ---------- reading the files host the way a map does ----------
#
# The copy above proves the BUCKET holds each file; it says nothing about what a
# reader's browser gets from files.districtry.com, which is a separate Cloudflare
# setting (the bucket's custom domain) with a separate rule (its CORS policy).
# A map on districtry.com reads a tile archive across origins, a byte range at a
# time, so three things must hold or every tiled layer draws nothing:
#   * the preflight a browser may send for a Range request is answered for the
#     site's origin, with Range allowed;
#   * a Range request answers 206 with exactly those bytes, an
#     Access-Control-Allow-Origin the site matches, and Content-Range exposed,
#     because the service worker reads Content-Range to store the piece (engine
#     sw-handlers, cachedRange) and a header CORS does not expose reads as empty;
#   * a population file answers 200 with its bytes and the same origin header.
# probe() checks those for a small sample: each live app's smallest archive (its
# first and last bytes) and its population index. It reads only this project's
# own files on this project's own host.
#
# SINCE THE MAPS READ THEIR BOUNDARY FILES THERE TOO (2026-11-16), the sample
# also holds each live app's smallest boundary file, read whole with the
# site's Origin as a page reads it, and ONE boundary file read the way a
# browser asks for it, with Accept-Encoding: gzip. GitHub Pages sent these
# files compressed, and they are the bulk of what a map downloads, so a files
# host that stopped compressing them would make every map several times slower
# to load with nothing else to show for it. That one is the LARGEST boundary
# file across the live apps, because that is the file whose compression
# matters most and the one a size limit on the host's compression would drop
# first. Measured on the day the copies first existed (2026-11-16): Kentucky's
# precincts, 10,197,299 bytes published, arrived as 2,493,584 with gzip, so
# the read costs about 2.5 MB a run.

# This project's own token. Without one urllib sends "Python-urllib/3.x",
# which Cloudflare's default Browser Integrity Check can refuse outright.
PROBE_UA = "districtry-files-check/1.0 (+https://districtry.com/)"


def _http(method, url, headers, timeout=30, attempts=3):
    """(status, headers, body). An HTTP answer of any status is returned as it
    came; a connection that fails (measured on the first runs: one reset in 55
    requests) is tried again after 2 and 4 seconds before the failure is
    raised, so one dropped connection does not turn a publish run red."""
    req = urllib.request.Request(url, method=method, headers=dict(headers, **{"User-Agent": PROBE_UA}))
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            if attempt == attempts - 1:
                raise
            time.sleep(2 * (attempt + 1))


def _why(h, body):
    """What answered a refused request, so a red run says whether it was the
    bucket (an XML error naming a code) or Cloudflare in front of it (an HTML
    block page, a cf-mitigated header)."""
    text = re.sub(r"<[^>]+>", " ", (body or b"")[:600].decode("utf-8", "replace"))
    text = re.sub(r"\s+", " ", text).strip()[:160]
    parts = ["server: %s" % h.get("server", "?")]
    for k in ("cf-mitigated", "content-type"):
        if h.get(k):
            parts.append("%s: %s" % (k, h[k]))
    if text:
        parts.append("body: %s" % text)
    return " [" + "; ".join(parts) + "]"


def _listed(value, name):
    items = [v.strip().lower() for v in (value or "").split(",")]
    return name in items or "*" in items


def probe_sample(tree, live_tags):
    """[(key, kind)] — each live app's smallest tile archive, its population
    index and its smallest boundary file, wherever the tree has them, and the
    largest boundary file of all, to be read compressed. Raises TreeError for an app whose
    boundary files cannot be listed."""
    out = []
    largest = None
    for tag in sorted(live_tags):
        if os.path.isdir(os.path.join(tree, tag, "data", "app")):
            sized = sorted((os.path.getsize(os.path.join(tree, tag, "data", "app", n)), n)
                           for n in boundary_files(tree, tag))
            if sized:
                out.append(("%s/data/app/%s" % (tag, sized[0][1]), "boundary"))
            if sized and (largest is None or sized[-1][0] > largest[0]):
                largest = (sized[-1][0], "%s/data/app/%s" % (tag, sized[-1][1]))
        tiles = os.path.join(tree, tag, "data", "app", "tiles")
        if os.path.isdir(tiles):
            names = sorted((os.path.getsize(os.path.join(tiles, n)), n)
                           for n in os.listdir(tiles) if n.endswith(".pmtiles"))
            if names:
                out.append(("%s/data/app/tiles/%s" % (tag, names[0][1]), "tiles"))
        if os.path.isfile(os.path.join(tree, tag, "data", "app", "population", "index.json")):
            out.append(("%s/data/app/population/index.json" % tag, "population"))
    if largest:
        out.append((largest[1], "compressed"))
    return out


def probe(files_origin, page_origin, tree, live_tags, timings=None):
    """(problems, checked): every way the files host fails a map, for a sample.
    Each GET is appended to `timings`, when given, as (kind, key, ms, bytes,
    cache status, Cloudflare location)."""
    problems, checked = [], 0
    try:
        sample = probe_sample(tree, live_tags)
    except TreeError as e:
        return [str(e)], 0
    if not sample:
        return ["the tree at %s holds no tile archive or population index for a live app" % tree], 0
    allowed = (page_origin, "*")

    def get(url, headers, kind):
        t0 = time.monotonic()
        try:
            got = _http("GET", url, headers)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            problems.append("%s could not be reached: %s" % (url, e))
            return None
        if timings is not None:
            h = got[1]
            timings.append((kind, url[len(files_origin) + 1:], (time.monotonic() - t0) * 1000, len(got[2]),
                            h.get("cf-cache-status") or "-", (h.get("cf-ray") or "").rpartition("-")[2] or "-"))
        return got

    first_tile = next((k for k, kind in sample if kind == "tiles"), None)
    if first_tile:
        url = files_origin + "/" + first_tile
        try:
            st, h, pbody = _http("OPTIONS", url, {"Origin": page_origin,
                                               "Access-Control-Request-Method": "GET",
                                               "Access-Control-Request-Headers": "range"})
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            st, h = None, {}
            problems.append("%s could not be reached: %s" % (url, e))
        if st is not None:
            checked += 1
            if not 200 <= st < 300:
                problems.append("the preflight for %s answered %s, not 2xx (is the CORS rule on the bucket?)%s"
                                % (first_tile, st, _why(h, pbody)))
            elif h.get("access-control-allow-origin") not in allowed:
                problems.append("the preflight for %s does not allow origin %s (Access-Control-Allow-Origin: %r)"
                                % (first_tile, page_origin, h.get("access-control-allow-origin")))
            elif not _listed(h.get("access-control-allow-headers"), "range"):
                problems.append("the preflight for %s does not allow the Range header (Access-Control-Allow-Headers: %r)"
                                % (first_tile, h.get("access-control-allow-headers")))

    for key, kind in sample:
        with open(os.path.join(tree, key), "rb") as f:
            data = f.read()
        url = files_origin + "/" + key
        if kind == "compressed":
            got = get(url, {"Origin": page_origin, "Accept-Encoding": "gzip"}, kind)
            if not got:
                continue
            checked += 1
            st, h, body = got
            if st != 200:
                problems.append("%s answered %s, not 200%s" % (key, st, _why(h, body)))
            elif h.get("content-encoding") != "gzip":
                problems.append("%s (%d bytes) was not sent compressed to a reader that asked for gzip "
                                "(Content-Encoding: %r), so every map downloads its boundary files at full size"
                                % (key, len(data), h.get("content-encoding")))
            else:
                try:
                    plain = gzip.decompress(body)
                except (OSError, EOFError) as e:
                    plain = None
                    problems.append("%s answered gzip that does not open: %s" % (key, e))
                if plain is not None and plain != data:
                    problems.append("%s answered %d bytes, compressed, that differ from the %d published"
                                    % (key, len(plain), len(data)))
            continue
        if kind in ("population", "boundary"):
            got = get(url, {"Origin": page_origin}, kind)
            if not got:
                continue
            checked += 1
            st, h, body = got
            if st != 200:
                problems.append("%s answered %s, not 200%s" % (key, st, _why(h, body)))
            elif h.get("access-control-allow-origin") not in allowed:
                problems.append("%s carries no Access-Control-Allow-Origin for %s (%r)"
                                % (key, page_origin, h.get("access-control-allow-origin")))
            elif body != data:
                problems.append("%s answered %d bytes that differ from the %d published" % (key, len(body), len(data)))
            continue
        size = len(data)
        for a, b in ((0, min(126, size - 1)), (max(0, size - 64), size - 1)):
            got = get(url, {"Origin": page_origin, "Range": "bytes=%d-%d" % (a, b)}, kind)
            if not got:
                break
            checked += 1
            st, h, body = got
            where = "%s bytes %d-%d" % (key, a, b)
            if st != 206:
                problems.append("%s answered %s, not 206%s%s" % (
                    where, st, " (a host that ignores Range sends the whole file)" if st == 200 else "",
                    "" if st == 200 else _why(h, body)))
            elif h.get("access-control-allow-origin") not in allowed:
                problems.append("%s carries no Access-Control-Allow-Origin for %s (%r)"
                                % (where, page_origin, h.get("access-control-allow-origin")))
            elif not _listed(h.get("access-control-expose-headers"), "content-range"):
                problems.append("%s does not expose Content-Range (Access-Control-Expose-Headers: %r), so the "
                                "service worker cannot store the piece" % (where, h.get("access-control-expose-headers")))
            elif h.get("content-range") != "bytes %d-%d/%d" % (a, b, size):
                problems.append("%s answered Content-Range %r; the published file is %d bytes"
                                % (where, h.get("content-range"), size))
            elif body != data[a:b + 1]:
                problems.append("%s answered other bytes than the published file" % where)
    return problems, checked


def live_tags_of(repo_root):
    import json
    with open(os.path.join(repo_root, "metros.json")) as f:
        return {m["tag"] for m in json.load(f)["metros"]}


def run_probe_against_stand_in():
    """probe() against a loopback host serving a fixture tree, once answering as
    R2 does with the rule in place and once for each way it can be wrong."""
    import http.server
    import tempfile
    import threading

    mode = {"fault": None}
    origin = "https://districtry.example"

    class Handler(http.server.BaseHTTPRequestHandler):
        root = None

        def log_message(self, *a):
            pass

        def _cors(self):
            if mode["fault"] != "no-cors" and self.headers.get("Origin") == origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                if mode["fault"] != "no-expose":
                    self.send_header("Access-Control-Expose-Headers", "Content-Range, Content-Length, ETag")

        def do_OPTIONS(self):
            assert self.headers.get("User-Agent") == PROBE_UA, self.headers.get("User-Agent")
            self.send_response(204 if mode["fault"] != "no-cors" else 403)
            if mode["fault"] != "no-cors":
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Methods", "GET, HEAD")
                self.send_header("Access-Control-Allow-Headers", "range")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):
            if mode["fault"] == "drop-once" and not mode.get("dropped"):
                mode["dropped"] = True
                self.close_connection = True
                self.connection.shutdown(2)   # no answer at all: the client sees the connection go
                return
            path = os.path.join(self.root, urllib.parse.unquote(self.path.lstrip("/")))
            if not os.path.isfile(path):
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            data = open(path, "rb").read()
            if mode["fault"] == "blocked":
                body = b"<html><title>Attention Required</title><body>error code: 1010</body></html>"
                self.send_response(403)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if mode["fault"] == "stale":
                data = b"x" + data[1:]
            if "gzip" in self.headers.get("Accept-Encoding", "") and mode["fault"] != "identity":
                body = gzip.compress(data)
                self.send_response(200)
                self._cors()
                self.send_header("Content-Encoding", "gzip")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            m = re.match(r"bytes=(\d+)-(\d+)$", self.headers.get("Range", ""))
            if m and mode["fault"] != "whole":
                a, b = int(m.group(1)), min(int(m.group(2)), len(data) - 1)
                self.send_response(206)
                self.send_header("Content-Range", "bytes %d-%d/%d" % (a, b, len(data)))
                body = data[a:b + 1]
            else:
                self.send_response(200)
                body = data
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    with tempfile.TemporaryDirectory() as d:
        for rel, data in (("il/data/app/tiles/big.pmtiles", bytes(range(256)) * 40),
                          ("il/data/app/tiles/small.pmtiles", bytes(range(200))),
                          ("il/data/app/population/index.json", b'{"17031": 5275541}'),
                          ("il/data/app/wards.json", b'{"type":"FeatureCollection","features":[]}' + b" " * 400),
                          ("il/data/app/outline.json", b'{"type":"FeatureCollection"}'),
                          ("il/data/app/roster.json", b'{"1": "A roster is never sampled"}'),
                          ("il/sw.js", b'const GEOMETRY_URLS = [\n  "./data/app/wards.json",\n  "./data/app/outline.json",\n];\n'),
                          ("zz/data/app/tiles/dark.pmtiles", b"dark")):
            os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
            with open(os.path.join(d, rel), "wb") as f:
                f.write(data)
        assert probe_sample(d, {"il"}) == [("il/data/app/outline.json", "boundary"),
                                           ("il/data/app/tiles/small.pmtiles", "tiles"),
                                           ("il/data/app/population/index.json", "population"),
                                           ("il/data/app/wards.json", "compressed")], probe_sample(d, {"il"})
        Handler.root = d
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        host = "http://127.0.0.1:%d" % server.server_port
        try:
            timings = []
            problems, checked = probe(host, origin, d, {"il"}, timings)
            assert not problems and checked == 6, (problems, checked)
            # Every GET is timed (the preflight is not), and each kind gets a line.
            assert sorted(t[0] for t in timings) == ["boundary", "compressed", "population", "tiles", "tiles"], timings
            lines = read_times(timings)
            assert len(lines) == 4 and lines[0].startswith("read times, boundary: 1 read(s)"), lines
            mode["fault"] = "drop-once"
            problems, checked = probe(host, origin, d, {"il"})
            assert mode.get("dropped") and not problems and checked == 6, (problems, checked)
            for fault, words in (("no-cors", "preflight"), ("no-expose", "expose Content-Range"),
                                 ("whole", "not 206"), ("stale", "other bytes"),
                                 ("stale", "outline.json answered"), ("stale", "compressed, that differ"),
                                 ("identity", "was not sent compressed"),
                                 ("blocked", "body: Attention Required error code: 1010")):
                mode["fault"] = fault
                problems, _ = probe(host, origin, d, {"il"})
                assert any(words in p for p in problems), (fault, problems)
            mode["fault"] = None
            problems, _ = probe(host, "https://elsewhere.example", d, {"il"})
            assert any("Access-Control-Allow-Origin" in p for p in problems), problems
        finally:
            server.shutdown()
    return ("a read of the files host against a loopback stand-in, right, through one dropped "
            "connection, and six ways wrong")


def run_against_stand_in(tree):
    import http.server
    import io
    import contextlib
    import threading

    store = {"il/data/app/tiles/gone.pmtiles": b"old", "notes/keep.txt": b"mine",
             "il/data/app/population/17031.json": b"P",   # already current
             "il/data/app/outline.json": b"O",            # a boundary file, already current
             "il/data/app/retired.json": b"old",          # one no worker lists any more
             "il/data/app/election-results/ward-1.json": b"not this script's"}
    seen = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _key(self):
            path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
            assert path.startswith("/" + BUCKET), path
            return path[len(BUCKET) + 2:]

        def _check_auth(self):
            auth = self.headers.get("Authorization", "")
            assert auth.startswith("AWS4-HMAC-SHA256 Credential=AK/") and "/auto/s3/aws4_request" in auth, auth
            assert "host" in auth.split("SignedHeaders=")[1].split(",")[0].split(";"), auth
            seen.append(self.command)

        def do_GET(self):
            self._check_auth()
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            assert q.get("list-type") == ["2"], q
            keys = sorted(store)
            start = int(q.get("continuation-token", ["0"])[0])
            page = keys[start:start + 2]                   # two a page, to exercise paging
            more = start + 2 < len(keys)
            xml = ['<?xml version="1.0" encoding="UTF-8"?>',
                   '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">',
                   "<IsTruncated>%s</IsTruncated>" % ("true" if more else "false")]
            if more:
                xml.append("<NextContinuationToken>%d</NextContinuationToken>" % (start + 2))
            for k in page:
                xml.append('<Contents><Key>%s</Key><ETag>"%s"</ETag></Contents>'
                           % (k, hashlib.md5(store[k]).hexdigest()))
            xml.append("</ListBucketResult>")
            body = "".join(xml).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_PUT(self):
            self._check_auth()
            body = self.rfile.read(int(self.headers["Content-Length"]))
            assert self.headers["Content-MD5"] == base64.b64encode(hashlib.md5(body).digest()).decode()
            assert self.headers["Cache-Control"] == CACHE_CONTROL
            assert self.headers["x-amz-content-sha256"] == hashlib.sha256(body).hexdigest()
            store[self._key()] = body
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_DELETE(self):
            self._check_auth()
            store.pop(self._key(), None)
            self.send_response(204)
            self.end_headers()

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        r2 = R2("acct", "AK", "SK", endpoint="http://127.0.0.1:%d" % server.server_port)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            assert sync(r2, tree) == 0, out.getvalue()
        assert store["il/data/app/tiles/a.pmtiles"] == b"A"
        assert store["il/data/app/wards.json"] == b"W"             # a listed boundary file: copied
        assert "il/data/app/tiles/gone.pmtiles" not in store
        assert "il/data/app/retired.json" not in store
        assert "il/data/app/roster.json" not in store and "il/data/app/unlisted.json" not in store
        assert store["notes/keep.txt"] == b"mine"                  # outside what this script owns: untouched
        assert store["il/data/app/election-results/ward-1.json"] == b"not this script's"
        assert seen.count("PUT") == 2, seen                        # 17031.json and outline.json were current
        assert seen.count("DELETE") == 2, seen
        seen.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            assert sync(r2, tree) == 0
        assert "PUT" not in seen and "DELETE" not in seen, seen    # a second run changes nothing
    finally:
        server.shutdown()
    return "a whole run against a loopback stand-in for the bucket"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tree", default="_site", help="the assembled site directory")
    ap.add_argument("--dry-run", action="store_true", help="list what would change and change nothing")
    ap.add_argument("--require", action="store_true", help="fail when the credentials are not set")
    ap.add_argument("--allow-mass-delete", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--probe", action="store_true",
                    help="read a sample from the files host the way a map on the site does, "
                         "and compare it with --tree; needs no credentials")
    ap.add_argument("--leave-out", action="store_true",
                    help="remove from --tree what the files host serves, bar the boundary files a "
                         "root page reads, so GitHub Pages does not publish it; run after the copy")
    a = ap.parse_args()
    if a.leave_out:
        return run_leave_out(a.tree)
    if a.selftest:
        selftest()
        return 0
    if a.probe:
        return run_probe(a.tree)

    env = [os.environ.get(n, "").strip() for n in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")]
    if not all(env):
        msg = "sync_r2_files: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID or R2_SECRET_ACCESS_KEY is not set"
        if a.require:
            print("::error::" + msg)
            return 1
        print(msg + "; nothing copied")
        return 0
    if not os.path.isdir(a.tree):
        print("::error::sync_r2_files: no tree at %s" % a.tree)
        return 1

    return sync(R2(*env), a.tree, a.dry_run, a.allow_mass_delete)


def run_leave_out(tree):
    def mb(n):
        return "%.1f MB" % (n / 1e6)
    try:
        before = sum(os.path.getsize(os.path.join(d, n)) for d, _, ns in os.walk(tree) for n in ns)
        count, size, kept = leave_to_files_host(tree)
    except (TreeError, OSError) as e:
        print("::error::sync_r2_files: " + str(e))
        return 1
    print("sync_r2_files: left %d file(s), %s, to the files host; the published tree went from %s to %s"
          % (count, mb(size), mb(before), mb(before - size)))
    print("sync_r2_files: kept %d boundary file(s) a root page reads: %s"
          % (len(kept), ", ".join(kept)))
    return 0


def read_times(timings):
    """Lines saying how long the files host took to answer each kind of read
    from wherever this ran; the deploy runs it on GitHub's runners in the
    United States. Each read opens its own connection, so a time includes the
    connection setup a browser pays once per host."""
    out = []
    for kind in ("boundary", "compressed", "population", "tiles"):
        rows = sorted((r for r in timings if r[0] == kind), key=lambda r: r[2])
        if not rows:
            continue
        caches, places = {}, sorted({r[5] for r in rows})
        for r in rows:
            caches[r[4]] = caches.get(r[4], 0) + 1
        out.append("read times, %s: %d read(s) on new connections, median %.0f ms, slowest %.0f ms (%s, %d bytes); "
                   "cache %s; served from %s"
                   % (kind, len(rows), rows[len(rows) // 2][2], rows[-1][2], rows[-1][1], rows[-1][3],
                      ", ".join("%s %d" % kv for kv in sorted(caches.items())), ", ".join(places)))
    return out


def run_probe(tree):
    origin = shipped_origin()
    if not origin:
        print("sync_r2_files: FILES_ORIGIN is null, so no map reads the files host; nothing to read")
        return 0
    repo = os.path.join(os.path.dirname(FILES_BLOCK), "..", "..")
    cname = open(os.path.join(repo, "CNAME")).read().strip()
    timings = []
    problems, checked = probe(origin, "https://" + cname, tree, live_tags_of(repo), timings)
    for line in read_times(timings):
        print("sync_r2_files: " + line)
    for p in problems:
        print("::error::sync_r2_files: " + p)
    if problems:
        return 1
    print("sync_r2_files: OK — %s answered all %d read(s) as a map on https://%s needs" % (origin, checked, cname))
    return 0


def sync(r2, tree, dry_run=False, allow_mass_delete=False):
    try:
        local = local_files(tree)
    except TreeError as e:
        print("::error::sync_r2_files: %s; nothing was changed" % e)
        return 1
    if not local:
        print("::error::sync_r2_files: %s holds no tile archive, population file or boundary file" % tree)
        return 1
    remote = r2.list_objects()
    uploads, deletes, unchanged = plan(local, remote)
    total = sum(os.path.getsize(os.path.join(tree, k)) for k in uploads)
    held = sum(os.path.getsize(os.path.join(tree, k)) for k in local)
    print("sync_r2_files: %d file(s) in the tree (%s; %.1f MB), %d unchanged in the bucket, "
          "%d to upload (%s; %.1f MB), %d to delete (%s)"
          % (len(local), by_kind(local), held / 1e6, len(unchanged), len(uploads), by_kind(uploads),
             total / 1e6, len(deletes), by_kind(deletes)))
    for k in uploads:
        print("  upload " + k)
    for k in deletes:
        print("  delete " + k)
    refusal = delete_refusal(deletes, remote, allow_mass_delete)
    if refusal:
        print("::error::sync_r2_files: " + refusal)
        return 1
    if dry_run:
        print("sync_r2_files: dry run, nothing changed")
        return 0

    def upload(k):
        with open(os.path.join(tree, k), "rb") as f:
            r2.put(k, f.read())
    # Eight at a time: the first copy is about 1,900 files, and one at a time
    # spends most of its minutes waiting on each request's round trip.
    with concurrent.futures.ThreadPoolExecutor(max_workers=UPLOAD_WORKERS) as pool:
        list(pool.map(upload, uploads))
    for k in deletes:
        r2.delete(k)

    after = r2.list_objects()
    wrong = verify(local, after)
    if wrong:
        print("::error::sync_r2_files: after the copy the bucket is missing or differs on %d file(s): %s"
              % (len(wrong), ", ".join(wrong[:10])))
        return 1
    left = [k for k in deletes if k in after]
    if left:
        print("::error::sync_r2_files: %d deleted object(s) are still listed: %s" % (len(left), ", ".join(left[:10])))
        return 1
    print("sync_r2_files: OK — the bucket holds all %d file(s) with matching MD5s" % len(local))
    return 0


if __name__ == "__main__":
    sys.exit(main())
