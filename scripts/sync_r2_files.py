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

It is stdlib only (the deploy installs nothing), so it signs its own requests
with AWS Signature Version 4, which R2 takes with region "auto". --selftest
holds the signer to AWS's published examples and the planner to fixtures, with
no network.

It reads no robots.txt, and validate_robots_adoption.py records it as exempt:
robots.txt says which of a site's pages a crawler may read, and this reads
nobody's pages. It lists and writes this project's own bucket through the
storage API, with the key issued to this project for exactly that, and the
only bytes it moves are this site's own files, mostly outbound.

Credentials come from the environment: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID and
R2_SECRET_ACCESS_KEY (repository secrets). With any of them missing the run
says so and does nothing, unless --require is given.

    python3 scripts/sync_r2_files.py --tree _site            # sync
    python3 scripts/sync_r2_files.py --tree _site --dry-run  # list, change nothing
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
    print("sync_r2_files: selftest OK — 3 AWS signing examples, the planner, the delete guard, "
          "the tree walk, %s and %s" % (e2e, urls))


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
    if shipped == "null":   # as shipped before the move: every file from the page's own site
        for c, got in zip(cases, run(block)):
            assert got == c[1].rstrip("/").rsplit("/", 1)[0] + "/" + c[3].split("/", 3)[3], (c, got)
    return "filesUrl run in Node asking for every file at its upload key"


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
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return 0

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
