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

This script makes the bucket hold exactly what the deploy is about to publish
in those folders. It reads the ASSEMBLED tree (deploy-pages.yml's _site), not
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
  * An object under one of the two folders with no file in the tree is
    deleted, so a retired archive stops being served as it would on Pages.
    More than MAX_DELETE_SHARE of them at once is refused unless
    --allow-mass-delete is given, because that is what a tree assembled
    wrong looks like.
  * Anything else in the bucket is left alone.
  * After the writes the bucket is listed again and every file must be there
    with its MD5, or the run fails.

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
    python3 scripts/sync_r2_files.py --selftest
"""
import argparse
import base64
import concurrent.futures
import datetime
import hashlib
import hmac
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BUCKET = "districtry-files"
REGION = "auto"
SERVICE = "s3"
# The two folders, under any instance tag. A key outside them is never
# uploaded, compared or deleted.
MANAGED_RE = re.compile(r"^[a-z]{2}/data/app/(tiles|population)/.+")
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

def local_files(tree):
    """{key: md5 hex} for every file under <tag>/data/app/{tiles,population}/
    in the assembled tree."""
    out = {}
    for tag in sorted(os.listdir(tree)):
        for folder in ("tiles", "population"):
            top = os.path.join(tree, tag, "data", "app", folder)
            if not os.path.isdir(top):
                continue
            for dirpath, _, names in os.walk(top):
                for n in names:
                    full = os.path.join(dirpath, n)
                    key = os.path.relpath(full, tree).replace(os.sep, "/")
                    if not MANAGED_RE.match(key):
                        continue
                    with open(full, "rb") as f:
                        out[key] = hashlib.md5(f.read()).hexdigest()
    return out


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
             "wi/data/app/population/index.json": "3"}
    remote = {"il/data/app/tiles/a.pmtiles": "1", "il/data/app/tiles/b.pmtiles": "9",
              "il/data/app/tiles/old.pmtiles": "4", "notes/readme.txt": "5",
              "il/data/app/other.json": "6"}
    up, de, same = plan(local, remote)
    assert up == ["il/data/app/tiles/b.pmtiles", "wi/data/app/population/index.json"], up
    assert de == ["il/data/app/tiles/old.pmtiles"], de  # never notes/ or a file outside the folders
    assert same == ["il/data/app/tiles/a.pmtiles"], same
    assert not MANAGED_RE.match("ga2/data/app/tiles/x") and not MANAGED_RE.match("il/data/app/tilesx")
    big = {"il/data/app/tiles/%d.pmtiles" % i: "x" for i in range(100)}
    assert delete_refusal(sorted(big)[:21], big, False)  # 21 of 100: refused
    assert delete_refusal(sorted(big)[:21], big, True) is None
    assert delete_refusal(sorted(big)[:5], big, False) is None  # a handful is ordinary
    assert verify(local, {**remote, "wi/data/app/population/index.json": "3"}) == ["il/data/app/tiles/b.pmtiles"]

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        for rel, data in (("il/data/app/tiles/a.pmtiles", b"A"), ("il/data/app/population/17031.json", b"P"),
                          ("il/data/app/roster.json", b"R"), ("il/index.html", b"H"),
                          ("fonts/x.woff2", b"F")):
            os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
            with open(os.path.join(d, rel), "wb") as f:
                f.write(data)
        got = local_files(d)
        assert got == {"il/data/app/tiles/a.pmtiles": hashlib.md5(b"A").hexdigest(),
                       "il/data/app/population/17031.json": hashlib.md5(b"P").hexdigest()}, got
        # A whole run against a loopback stand-in for the bucket: what is
        # uploaded, what is left alone, what is deleted, and that every request
        # was signed for the host it was sent to.
        e2e = run_against_stand_in(d)
        urls = check_files_url(got)
    read = run_probe_against_stand_in()
    print("sync_r2_files: selftest OK — 3 AWS signing examples, the planner, the delete guard, "
          "the tree walk, %s, %s and %s" % (e2e, urls, read))


FILES_BLOCK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine", "shared", "files-origin.txt")


def check_files_url(keys):
    """The page's filesUrl (engine/shared/files-origin.txt, the block every app
    and service worker carries), run in Node, must ask the files host for each
    file at the very key this script uploads it under, and must leave a page
    anywhere but the live host, and every other file, on its own site."""
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
    cases = []
    for k in sorted(keys):
        tag, rel = k.split("/", 1)
        cases.append(["live", "https://districtry.com/%s/" % tag, rel, "https://files.example/" + k])
        cases.append(["local", "http://localhost:8000/%s/" % tag, rel, "http://localhost:8000/" + k])
    cases.append(["live", "https://districtry.com/il/", "data/app/roster.json", "https://districtry.com/il/data/app/roster.json"])
    cases.append(["live", "https://districtry.com/il/", "../fleet-outlines.json", "https://districtry.com/fleet-outlines.json"])
    def run(src):
        prog = ("var cases = %s; var out = [];\n"
                "cases.forEach(function (c) {\n"
                "  var u = new URL(c[1]);\n"
                "  var location = { origin: u.origin, hostname: u.hostname };\n"
                "  out.push(eval(%s + '\\nfilesUrl(' + JSON.stringify(c[2]) + ', ' + JSON.stringify(c[1]) + ')'));\n"
                "});\nprocess.stdout.write(JSON.stringify(out));" % (json.dumps(cases), json.dumps(src)))
        res = subprocess.run([node, "-e", prog], capture_output=True, text=True, timeout=60)
        assert res.returncode == 0, res.stderr
        return json.loads(res.stdout)
    for c, got in zip(cases, run(stand_in)):
        assert got == c[3], (c, got)
    shipped = re.search(r"var FILES_ORIGIN = ([^;]*);", block).group(1)
    if shipped == "null":   # the way back: every file from the page's own site
        for c, got in zip(cases, run(block)):
            assert got == c[1].rstrip("/").rsplit("/", 1)[0] + "/" + c[3].split("/", 3)[3], (c, got)
    else:
        # The shipped origin is the files subdomain of the published site and
        # nothing else, so a typo in it cannot send every map somewhere else.
        origin = json.loads(shipped)
        assert origin == "https://files." + cname, "FILES_ORIGIN %r is not https://files.%s" % (origin, cname)
        for c, got in zip(cases, run(block)):
            assert got == c[3].replace("https://files.example", origin, 1), (c, got)
    return "filesUrl run in Node asking for every file at its upload key"


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
    """[(key, kind)] — each live app's smallest tile archive and its population
    index, wherever the tree has them."""
    out = []
    for tag in sorted(live_tags):
        tiles = os.path.join(tree, tag, "data", "app", "tiles")
        if os.path.isdir(tiles):
            names = sorted((os.path.getsize(os.path.join(tiles, n)), n)
                           for n in os.listdir(tiles) if n.endswith(".pmtiles"))
            if names:
                out.append(("%s/data/app/tiles/%s" % (tag, names[0][1]), "tiles"))
        if os.path.isfile(os.path.join(tree, tag, "data", "app", "population", "index.json")):
            out.append(("%s/data/app/population/index.json" % tag, "population"))
    return out


def probe(files_origin, page_origin, tree, live_tags):
    """(problems, checked): every way the files host fails a map, for a sample."""
    problems, checked = [], 0
    sample = probe_sample(tree, live_tags)
    if not sample:
        return ["the tree at %s holds no tile archive or population index for a live app" % tree], 0
    allowed = (page_origin, "*")

    def get(url, headers):
        try:
            return _http("GET", url, headers)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            problems.append("%s could not be reached: %s" % (url, e))
            return None

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
        if kind == "population":
            got = get(url, {"Origin": page_origin})
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
            got = get(url, {"Origin": page_origin, "Range": "bytes=%d-%d" % (a, b)})
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
                          ("zz/data/app/tiles/dark.pmtiles", b"dark")):
            os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
            with open(os.path.join(d, rel), "wb") as f:
                f.write(data)
        assert probe_sample(d, {"il"}) == [("il/data/app/tiles/small.pmtiles", "tiles"),
                                           ("il/data/app/population/index.json", "population")]
        Handler.root = d
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        host = "http://127.0.0.1:%d" % server.server_port
        try:
            problems, checked = probe(host, origin, d, {"il"})
            assert not problems and checked == 4, (problems, checked)
            mode["fault"] = "drop-once"
            problems, checked = probe(host, origin, d, {"il"})
            assert mode.get("dropped") and not problems and checked == 4, (problems, checked)
            for fault, words in (("no-cors", "preflight"), ("no-expose", "expose Content-Range"),
                                 ("whole", "not 206"), ("stale", "other bytes"),
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
            "connection, and five ways wrong")


def run_against_stand_in(tree):
    import http.server
    import io
    import contextlib
    import threading

    store = {"il/data/app/tiles/gone.pmtiles": b"old", "notes/keep.txt": b"mine",
             "il/data/app/population/17031.json": b"P"}   # already current
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
        assert "il/data/app/tiles/gone.pmtiles" not in store
        assert store["notes/keep.txt"] == b"mine"                  # outside the folders: untouched
        assert seen.count("PUT") == 1, seen                        # 17031.json was already current
        assert seen.count("DELETE") == 1, seen
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
    a = ap.parse_args()
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


def run_probe(tree):
    origin = shipped_origin()
    if not origin:
        print("sync_r2_files: FILES_ORIGIN is null, so no map reads the files host; nothing to read")
        return 0
    repo = os.path.join(os.path.dirname(FILES_BLOCK), "..", "..")
    cname = open(os.path.join(repo, "CNAME")).read().strip()
    problems, checked = probe(origin, "https://" + cname, tree, live_tags_of(repo))
    for p in problems:
        print("::error::sync_r2_files: " + p)
    if problems:
        return 1
    print("sync_r2_files: OK — %s answered all %d read(s) as a map on https://%s needs" % (origin, checked, cname))
    return 0


def sync(r2, tree, dry_run=False, allow_mass_delete=False):
    local = local_files(tree)
    if not local:
        print("::error::sync_r2_files: %s holds no file under <tag>/data/app/tiles or population" % tree)
        return 1
    remote = r2.list_objects()
    uploads, deletes, unchanged = plan(local, remote)
    total = sum(os.path.getsize(os.path.join(tree, k)) for k in uploads)
    print("sync_r2_files: %d file(s) in the tree, %d unchanged in the bucket, %d to upload (%.1f MB), %d to delete"
          % (len(local), len(unchanged), len(uploads), total / 1e6, len(deletes)))
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
