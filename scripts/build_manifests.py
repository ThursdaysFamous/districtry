#!/usr/bin/env python3
"""Emit the ONE web app manifest, and hold the pages that link it and the launcher to it.

WHY THERE IS ONE. Until 2026-10-13 each instance shipped its own
`<tag>/manifest.webmanifest` with scope `./` and no `id`, so installing
districtry from Illinois and then from Wisconsin put two apps on a phone, both
labelled "districtry", and an installed Illinois app ended at the state line:
the sibling hand-off navigates to `/wi/`, which was outside its scope, so
Android opened Wisconsin in a browser tab and the reader had left the app.
districtry is one app that answers in many places, so it installs as one:
`/manifest.webmanifest` at the root, `id` and `scope` `/`, so every page on the
site is inside it and crossing a state line keeps the reader in the same
window.

WHERE IT OPENS. `start_url` is `/app/`, a launcher that reads which state the
reader used last and opens it (`app/index.html`). The key it reads is written
by the engine block `engine/index.html/install-app.txt` on every app's boot, so
the two are one claim read in two places, and `--check` holds them to each
other: a key renamed on one side would leave every installed copy opening the
front page with nothing failing. The launcher has a service worker of its own
(`app/sw.js`, scope `/app/`) so an installed app still opens with no
connection; it caches the launcher page and nothing else, and it deletes only
its own caches, never an instance's.

SHARING A PLACE INTO THE APP (from 2026-10-14). `share_target` puts the
installed districtry in Android's Share menu, so a place open in Google Maps
can be shared straight to it. It sends what was shared to the launcher as
`/app/?title=…&text=…&url=…` (GET, because GitHub Pages answers no POST), and
the launcher hands it on to a state's map in the HASH, as `#q=`, where the map
runs the search a pasted link gets. A GET puts what was shared in the query
string, so three things keep it there and nowhere else: the launcher takes it
out of its own address before it leaves (the next page is sent that address as
its referrer, and the visit counter reports a referrer); the launcher's worker
answers a share from its copy and refreshes that copy by asking for `/app/`
alone, never the request it was handed; and the apps register that worker
when districtry is installed from them and whenever the installed app runs,
so a share is answered on the phone from the start. Safari supports no share
target, so an iPhone never shows districtry in its Share menu.

THE SHARE TARGET'S ADDRESS IS WRITTEN IN FULL, BECAUSE THE GOOGLE PLAY APP
COPIES IT AS WRITTEN (2026-10-16). PWABuilder builds the Play app from this
manifest and puts `share_target` into it unchanged. Bubblewrap resolves a
relative address only on a path PWABuilder does not take, and nothing after it
resolves one either, while Chrome hands a share to the app only once it has
checked that the address belongs to the site the app is linked to, which an
address with no scheme and host cannot. So the first Play build, made while
`action` read `/app/`, dropped every share and opened its start page: a place
shared from Google Maps on Adam's Pixel opened the Illinois map without the
place. That was read in PWABuilder's, Bubblewrap's, android-browser-helper's
and Chromium's code the same day. A browser resolves the full address exactly
as it resolved the short one, so the website's own install is unchanged, and
the host comes from `CNAME`, the file that says where the site is served.

THE GOOGLE PLAY APP (from 2026-10-16). The Play app is a Trusted Web Activity
that opens this site, built with PWABuilder. Android shows it full screen, with
no address bar, only when `/.well-known/assetlinks.json` names its package and
the certificates Play signs it with, so this script writes that file too, from
`PLAY_PACKAGE` and `PLAY_SIGNING_KEYS`. A new app is enrolled in Play's
quantum-ready hybrid signing, which signs with THREE keys: a classical one that
Android 16 and earlier check, and a classical and a post-quantum one that
Android 17 and later check instead. Play Console's ready-made "Digital Asset
Links JSON" names only the first, so by Google's account of which key Android
17 checks, a file pasted from it leaves the address bar on every Android 17
phone with nothing failing (read from the help page, not yet seen on a
phone). The Play-app block (`engine/shared/play-app.txt`) recognises the app
by the same package name, and `--check` holds the two to each other.

WHY THE ROOT SERVICE WORKER IS NOT USED. `/sw.js` is the kill switch that
retires the pre-R2.3 root registration. It must stay exactly that, and a
manifest needs no worker at its own scope to be installable, so the launcher's
worker lives at `/app/` and the root keeps none.

WHAT IS STILL PER INSTANCE. The `INSTANCES` table, because each instance's
worksheet must agree on the name and theme colour one app can only have once,
and each instance's app page must link the root manifest (installs start
there). `scripts/validate_instance_registration.py` holds this table to the
tree. iOS takes its home-screen icon from each page's own
`apple-touch-icon`, never from a manifest, which is why those stay per
instance (generated into each app's head-theme region).

WHAT `--check` ASSERTS, beyond byte-equality of the manifest:
  * every worksheet agrees on `brand.product_name` and `brand.theme_color`;
  * the three icons the manifest names are byte-identical to the brand's own
    files under districtry/icons/ and are PNGs of the size declared;
  * no instance ships a manifest of its own (a second app identity);
  * every page that declares a manifest declares this one, once, and every
    app page and the front door declare it;
  * the launcher reads the key the engine writes, registers its own worker at
    its own scope, is kept out of search, and names no other host;
  * the share target's address is the launcher's full https address on the
    host `CNAME` names, because the Google Play app copies it as written;
  * the launcher reads every parameter the share target sends, takes the share
    out of its own address, hands it on as `#q=`, and leaves the mark the
    engine counts a share by under the key the engine reads;
  * the launcher's worker names no cache outside its own prefix and never
    fetches the request it was handed, and the engine block registers that
    worker at the same script and scope the launcher does;
  * `.well-known/assetlinks.json` is byte-identical to what `PLAY_SIGNING_KEYS`
    produces, every fingerprint in it is well formed and listed once, and the
    Play-app block recognises the app by the package name it names.

Usage:
    python3 scripts/build_manifests.py            # write
    python3 scripts/build_manifests.py --check    # drift gate; exit 1 on diff
"""

import argparse
import difflib
import glob
import json
import os
import re
import sys
import urllib.parse

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (instance dir, worksheet path relative to repo root). IL's worksheet is the
# repo-root one — the same asymmetry generate_metro_files.py carries.
INSTANCES = [
    ("il", "metro-worksheet.json"),
    ("ny", "ny/metro-worksheet.json"),
    ("ca", "ca/metro-worksheet.json"),
    ("wi", "wi/metro-worksheet.json"),
    ("ia", "ia/metro-worksheet.json"),
    ("mi", "mi/metro-worksheet.json"),
    ("mn", "mn/metro-worksheet.json"),
    ("in", "in/metro-worksheet.json"),
    ("nc", "nc/metro-worksheet.json"),
    ("ky", "ky/metro-worksheet.json"),
    ("ok", "ok/metro-worksheet.json"),
    ("sc", "sc/metro-worksheet.json"),
    ("tn", "tn/metro-worksheet.json"),
    ("ar", "ar/metro-worksheet.json"),
    ("ms", "ms/metro-worksheet.json"),
    ("la", "la/metro-worksheet.json"),
]

MANIFEST = "manifest.webmanifest"
MANIFEST_HREF = "/" + MANIFEST
START_URL = "/app/"
CNAME = "CNAME"
HOST_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$")
LAUNCHER = os.path.join("app", "index.html")
LAUNCHER_SW = os.path.join("app", "sw.js")
LAUNCHER_CACHE_PREFIX = "districtry-app-launch-v"
ENGINE_BLOCK = os.path.join("engine", "index.html", "install-app.txt")
PLAY_APP_BLOCK = os.path.join("engine", "shared", "play-app.txt")

# The Google Play app. Its package name is permanent once published.
PLAY_PACKAGE = "com.districtry.app"
ASSET_LINKS = os.path.join(".well-known", "assetlinks.json")

# The certificates Play signs the app with, as the SHA-256 of each certificate
# file Play Console's "Download certificate" buttons give (measured 2026-10-16
# on the four files Adam downloaded; the first matches the fingerprint Play
# Console prints). Play's help page says to register all three keys of hybrid
# signing (support.google.com/googleplay/android-developer/answer/9842756, read
# 2026-10-16). The UPLOAD key is left out on purpose: Play re-signs every copy a
# phone installs from it, so the upload key signs nothing a reader runs, and
# listing it would let a copy signed on a computer rather than by Google claim
# districtry.com as well. Play prompts for a key upgrade about every two years;
# an upgraded key's fingerprints go in here before the upgraded build ships.
PLAY_SIGNING_KEYS = [
    ("92:B8:E3:B4:11:73:79:D6:74:62:57:A0:2A:A9:9E:02:A6:9A:DA:18:BE:3D:F5:A7:20:EB:98:0A:77:C0:AF:F9",
     "classical RSA key, checked by Android 16 and earlier (deployment_cert.der)"),
    ("66:31:30:BC:4E:61:F1:9E:FE:01:D6:EB:E5:8B:D8:5C:AA:B1:40:4B:17:6A:65:98:F2:4D:50:49:45:16:4E:F5",
     "hybrid signing's classical RSA key, checked by Android 17 and later (hybrid_classical_cert.der)"),
    ("1E:27:21:C7:0D:96:84:57:66:99:60:31:DB:43:0F:9B:AA:91:AF:E3:08:92:A9:F0:FB:B6:A1:58:6E:75:88:AA",
     "hybrid signing's post-quantum ML-DSA-65 key, Android 17 and later (hybrid_pqc_cert.der)"),
]
FINGERPRINT_RE = re.compile(r"^(?:[0-9A-F]{2}:){31}[0-9A-F]{2}$")

# What Android's Share menu sends the launcher. Android puts a shared link in
# `text` and usually leaves `url` empty, so the launcher reads all three.
SHARE_PARAMS = ("title", "text", "url")
LAUNCHER_SW_REGISTER_RE = re.compile(
    r'serviceWorker\.register\(\s*"/app/sw\.js"\s*,\s*\{\s*scope:\s*"/app/"')

# The splash background. Not the theme colour: the brand icons sit on a light
# field, and a violet splash behind a light-field icon reads as a mistake on a
# phone. This is the app's own paper tone.
BACKGROUND = "#F4F7F9"

# Root icon -> the brand file it is a copy of, and the size the manifest
# declares for it. favicon-192.png is the front door's own 192px icon and was
# already a byte-identical copy of the brand's; the two 512s are new at the
# root with this manifest.
ICONS = [
    ("favicon-192.png", "districtry/icons/districtry-192.png", 192, "any"),
    ("icon-512.png", "districtry/icons/districtry-512.png", 512, "any"),
    ("icon-maskable-512.png", "districtry/icons/districtry-maskable-512.png", 512, "maskable"),
]

MANIFEST_LINK_RE = re.compile(r'<link\b[^>]*\brel=["\']manifest["\'][^>]*>', re.I)
HREF_RE = re.compile(r'\bhref=["\']([^"\']*)["\']', re.I)


def fail(msg):
    print("build-manifests: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def rel(path):
    return os.path.relpath(path, REPO)


def read(path, what):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError as e:
        fail("cannot read %s (%s): %s" % (what, rel(path), e))


def brand_identity():
    """The name and theme colour every instance must agree on. One app has one
    of each; an instance that changed its own would change every installed
    copy's colour the day it was regenerated, so disagreement fails rather than
    picking a winner."""
    names, colours = {}, {}
    for inst, wpath in INSTANCES:
        w = json.loads(read(os.path.join(REPO, wpath), "the %s worksheet" % inst))
        brand = w.get("brand") or {}
        if not brand.get("product_name") or not brand.get("theme_color"):
            fail("%s: worksheet has no brand.product_name or brand.theme_color — "
                 "the manifest cannot be generated without them" % wpath)
        names.setdefault(brand["product_name"], []).append(inst)
        colours.setdefault(brand["theme_color"], []).append(inst)
    if len(names) != 1 or len(colours) != 1:
        fail("the instances disagree about the app's name or theme colour "
             "(names %s, colours %s). districtry installs as ONE app, which has "
             "one of each." % (names, colours))
    return next(iter(names)), next(iter(colours))


def site_origin():
    """The site's own address, from the host CNAME tells GitHub Pages to serve
    it at, so the share target names the host the manifest is served from."""
    host = read(os.path.join(REPO, CNAME), "CNAME").strip()
    if not HOST_RE.match(host):
        fail("%s holds %r, which is not a lower-case host name, so the share "
             "target's full address cannot be written" % (CNAME, host))
    return "https://" + host


def check_share_target(doc, site):
    """Hold the share target's address to the launcher's full address.

    The Google Play app takes `share_target` from this manifest exactly as
    written, and Chrome delivers a share to that app only after checking that
    the address belongs to the site the app is linked to. An address with no
    scheme and host belongs to no site, so a short one makes the app drop every
    share and open its start page. A browser resolves either form to the same
    place, so nothing on the website would show the difference."""
    action = doc["share_target"]["action"]
    parts = urllib.parse.urlsplit(action)
    want = ("https", urllib.parse.urlsplit(site).netloc, START_URL, "", "")
    if (parts.scheme, parts.netloc, parts.path, parts.query, parts.fragment) != want:
        fail("share_target.action is %r. It must be the launcher's full address, "
             "%s%s: PWABuilder copies it into the Google Play app as written, and "
             "Chrome drops a share whose address does not name the site the app "
             "is linked to, opening the app's start page with the shared place "
             "gone (seen on a Pixel on 2026-10-16)." % (action, site, START_URL))


def png_size(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def build_manifest():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from build_landing_page import DESCRIPTION
    finally:
        sys.path.pop(0)
    name, theme = brand_identity()
    site = site_origin()
    doc = {
        # The app's identity. Explicit so it survives a change of start_url;
        # without it the identity IS the start_url, and moving the launcher
        # would orphan every installed copy.
        "id": "/",
        "name": name,
        "short_name": name,
        "description": DESCRIPTION,
        "lang": "en-US",
        "dir": "ltr",
        "start_url": START_URL,
        "scope": "/",
        "display": "standalone",
        "background_color": BACKGROUND,
        "theme_color": theme,
        "icons": [
            # Without a maskable icon Android crops the square into its
            # adaptive shape and letterboxes it on a white plate. That one
            # carries the safe-zone padding the spec asks for.
            {"src": "/" + icon, "sizes": "%dx%d" % (px, px), "type": "image/png",
             "purpose": purpose}
            for icon, _src, px, purpose in ICONS
        ],
        # districtry in Android's Share menu: what is shared opens the
        # launcher, which hands it to a state's map. The address is written
        # in full because the Google Play app copies it as written (see the
        # docstring).
        "share_target": {
            "action": site + START_URL,
            "method": "GET",
            "params": {p: p for p in SHARE_PARAMS},
        },
    }
    check_share_target(doc, site)
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def build_asset_links():
    """The Digital Asset Links statement that lets the Play app open this site
    full screen. A malformed fingerprint fails nothing on the site and leaves
    the app's address bar showing, so each is checked here."""
    fps = [fp for fp, _role in PLAY_SIGNING_KEYS]
    bad = [fp for fp in fps if not FINGERPRINT_RE.match(fp)]
    if bad:
        fail("PLAY_SIGNING_KEYS holds %s, which %s not a SHA-256 fingerprint "
             "written as 32 upper-case hex pairs joined by colons, the form "
             "Play Console prints" % (", ".join(bad), "is" if len(bad) == 1 else "are"))
    if len(set(fps)) != len(fps):
        fail("PLAY_SIGNING_KEYS lists a fingerprint twice")
    doc = [{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
            "namespace": "android_app",
            "package_name": PLAY_PACKAGE,
            "sha256_cert_fingerprints": fps,
        },
    }]
    return json.dumps(doc, indent=2) + "\n"


def check_play_package():
    """The Play-app block tells the Play app from a browser partly by the
    app's own referrer, android-app://<package>. A package named differently
    there and in the asset links would leave one of them describing an app
    that does not exist, with nothing else failing."""
    play = read(os.path.join(REPO, PLAY_APP_BLOCK), "the Play-app block")
    want = "android-app:\\/\\/" + PLAY_PACKAGE.replace(".", "\\.")
    if want not in play:
        fail("%s does not recognise the referrer android-app://%s, the package "
             "%s names. Change both together." % (PLAY_APP_BLOCK, PLAY_PACKAGE, ASSET_LINKS))


def write_or_check(relpath, want, check, source, why):
    """Write a generated file, or with --check fail if the copy on disk differs."""
    path = os.path.join(REPO, relpath)
    have = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    if check:
        if have != want:
            sys.stdout.writelines(difflib.unified_diff(
                have.splitlines(keepends=True), want.splitlines(keepends=True),
                fromfile="on disk", tofile="from " + source))
            fail("%s drifted from %s. Regenerate rather than hand-editing: %s"
                 % (relpath, source, why))
    elif have != want:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(want)
        print("build-manifests: wrote %s" % relpath)
    else:
        print("build-manifests: %s already current" % relpath)


def icons(check):
    """Copy each root icon from the brand's own file, or check it still is one."""
    drift = []
    for icon, src, px, _purpose in ICONS:
        with open(os.path.join(REPO, src), "rb") as fh:
            want = fh.read()
        size = png_size(want)
        if size != (px, px):
            fail("%s is %s, and the manifest declares %dx%d — the brand file "
                 "changed size, so the declaration must follow it"
                 % (src, "not a PNG" if size is None else "%dx%d" % size, px, px))
        path = os.path.join(REPO, icon)
        have = open(path, "rb").read() if os.path.exists(path) else None
        if have == want:
            continue
        if check:
            drift.append(icon)
        else:
            with open(path, "wb") as fh:
                fh.write(want)
            print("build-manifests: copied %s -> %s" % (src, icon))
    if drift:
        fail("%s no longer match%s the brand's own icon%s under districtry/icons/. "
             "Run scripts/build_manifests.py rather than editing the copies: an "
             "installed app shows these files on the home screen."
             % (", ".join(drift), "es" if len(drift) == 1 else "",
                "" if len(drift) == 1 else "s"))


def pages():
    """Every page the site publishes that could declare a manifest: the root's,
    the launcher's, each instance's and one level of instance subdirectory
    (the per-county pages). Discovered, the way validate_instance_assets.py
    discovers them, so a new instance is covered the day it lands."""
    out = sorted(glob.glob(os.path.join(REPO, "*.html")))
    out += sorted(glob.glob(os.path.join(REPO, "app", "*.html")))
    for inst, _w in INSTANCES:
        out += sorted(glob.glob(os.path.join(REPO, inst, "*.html")))
        out += sorted(glob.glob(os.path.join(REPO, inst, "*", "*.html")))
    return out


def check_pages():
    must = {os.path.join(REPO, "index.html")}
    must |= {os.path.join(REPO, inst, "index.html") for inst, _w in INSTANCES}
    wrong, missing, linking = [], [], 0
    for path in pages():
        text = read(path, "a page")
        links = MANIFEST_LINK_RE.findall(text)
        if not links:
            if path in must:
                missing.append(rel(path))
            continue
        linking += 1
        hrefs = [(HREF_RE.search(l) or [None, None])[1] for l in links]
        if len(links) != 1 or hrefs[0] != MANIFEST_HREF:
            wrong.append("%s (%s)" % (rel(path), ", ".join(str(h) for h in hrefs)))
    if wrong:
        fail("%d page(s) declare a manifest other than %s, or more than one: %s. "
             "There is one districtry app; a page naming another manifest would "
             "install a second one." % (len(wrong), MANIFEST_HREF, "; ".join(wrong)))
    if missing:
        fail("%s declare%s no manifest. Every app page and the front door must "
             "link %s, because that is where a reader installs from."
             % (", ".join(missing), "s" if len(missing) == 1 else "", MANIFEST_HREF))
    for inst, _w in INSTANCES:
        stray = os.path.join(REPO, inst, MANIFEST)
        if os.path.exists(stray):
            fail("%s exists. Instances no longer carry a manifest of their own: "
                 "the one at %s is the app every page installs, and a second file "
                 "is a second app identity waiting for a page to link it."
                 % (rel(stray), MANIFEST_HREF))
    return linking


def check_launcher():
    """The launcher is hand-written; these are the claims it must keep."""
    engine = read(os.path.join(REPO, ENGINE_BLOCK), "the install-app engine block")
    m = re.search(r'\bvar DST_LAST_APP_KEY = "([^"]+)";', engine)
    if not m:
        fail("%s no longer declares DST_LAST_APP_KEY as a string literal, so the "
             "key the launcher must read cannot be established" % ENGINE_BLOCK)
    key = m.group(1)
    page = read(os.path.join(REPO, LAUNCHER), "the app launcher")
    if 'localStorage.getItem("%s")' % key not in page:
        fail("%s does not read localStorage %r, the key %s writes. Every installed "
             "copy would open the front page instead of the reader's state, and "
             "nothing else would fail." % (LAUNCHER, key, ENGINE_BLOCK))
    if not LAUNCHER_SW_REGISTER_RE.search(page):
        fail("%s does not register /app/sw.js at scope /app/ — without it an "
             "installed app cannot open with no connection" % LAUNCHER)
    # The engine registers the same worker when districtry is installed from an
    # app and whenever the installed app runs, so a share is answered from the
    # launcher's copy even before the installed app's first launch.
    if not LAUNCHER_SW_REGISTER_RE.search(engine):
        fail("%s does not register /app/sw.js at scope /app/. Until the launcher's "
             "own first launch, a place shared into the app would reach the host "
             "in the address of the request." % ENGINE_BLOCK)
    share_key = launcher_share_key(engine, page)
    if not re.search(r'<meta name="robots" content="noindex', page):
        fail("%s is not marked noindex. It is a redirect, not a page a search "
             "result should send anyone to." % LAUNCHER)
    if re.search(r'rel=["\']canonical', page):
        fail("%s carries a canonical. build_sitemap.py lists a page on its "
             "canonical, and the launcher is not a destination." % LAUNCHER)
    if re.search(r'''(?:src|href|action)\s*=\s*["'](?:https?:)?//''', page) or \
            re.search(r'''["'](?:https?:)?//[a-z0-9.-]+\.[a-z]{2,}''', page, re.I):
        fail("%s names another host. It runs on every launch of the installed "
             "app, before any page the privacy page measures, so it must reach "
             "nobody but this site." % LAUNCHER)
    if not os.path.exists(os.path.join(REPO, START_URL.strip("/"), "index.html")):
        fail("the manifest's start_url %s has no index.html behind it" % START_URL)
    sw = read(os.path.join(REPO, LAUNCHER_SW), "the launcher's service worker")
    names = set(re.findall(r'"(districtry-[^"]*)"', sw))
    if names != {LAUNCHER_CACHE_PREFIX}:
        fail("%s names %s. It may name only its own cache prefix %r: a worker "
             "that names an instance's cache can delete it."
             % (LAUNCHER_SW, sorted(names), LAUNCHER_CACHE_PREFIX))
    # A share arrives as /app/?text=…, so a worker that refreshed its copy by
    # fetching the request it was handed would send what was shared to the
    # host on every share.
    if re.search(r"\bfetch\(\s*event\.request\b", sw):
        fail("%s fetches the request it was handed. A place shared into the app "
             "arrives in that request's address, so the refresh must ask for the "
             "launcher page alone." % LAUNCHER_SW)
    return key, share_key


def launcher_share_key(engine, page):
    """The launcher's half of a share, and the key the engine counts it by.

    The launcher must read each parameter the manifest's share_target sends,
    take them out of its own address before it leaves (that address is the
    next page's referrer, and the visit counter reports a referrer), hand the
    place on in the hash as `#q=`, and leave the mark the engine block counts a
    share by. It also reads the Google Play app's mark off the class the
    Play-app block sets, so a share opened in that app keeps its tag; a class
    renamed in the block would lose it silently, so the name is checked here."""
    for p in SHARE_PARAMS:
        if 'params.get("%s")' % p not in page:
            fail("%s does not read the share target's %r parameter. Android puts a "
                 "shared link in `text` and sometimes `title` or `url`, so a place "
                 "shared that way would open the app with nothing searched."
                 % (LAUNCHER, p))
    if "history.replaceState(" not in page:
        fail("%s never takes the share out of its own address. That address is "
             "sent to the next page as its referrer, and the visit counter there "
             "reports a referrer." % LAUNCHER)
    if '"#q=" + encodeURIComponent(' not in page:
        fail("%s does not hand the shared place on as #q= in the hash. The hash "
             "never leaves the browser; anything else would." % LAUNCHER)
    m = re.search(r'\bvar DST_SHARE_IN_KEY = "([^"]+)";', engine)
    if not m:
        fail("%s no longer declares DST_SHARE_IN_KEY as a string literal, so the "
             "key the launcher must write cannot be established" % ENGINE_BLOCK)
    share_key = m.group(1)
    if 'sessionStorage.setItem("%s"' % share_key not in page:
        fail("%s does not write sessionStorage %r, the key %s counts a share by. "
             "Shares into the app would go uncounted, and nothing else would fail."
             % (LAUNCHER, share_key, ENGINE_BLOCK))
    play = read(os.path.join(REPO, PLAY_APP_BLOCK), "the Play-app block")
    pm = re.search(r'classList\.add\("([^"]+)"\)', play)
    if not pm or "==== ENGINE:BEGIN play-app ====" not in page or \
            'classList.contains("%s")' % pm.group(1) not in page:
        fail("%s does not carry the Play-app block and read the class it sets "
             "(%s). A place shared into the Google Play app arrives with the app "
             "as the launcher's referrer and no ref=play, so without them the "
             "pages it opens would show the support links Google Play forbids."
             % (LAUNCHER, pm.group(1) if pm else "none found in %s" % PLAY_APP_BLOCK))
    return share_key


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="fail if the manifest, its icons, a page, the launcher "
                         "or the asset links drifted")
    args = ap.parse_args()

    write_or_check(MANIFEST, build_manifest(), args.check, "the brand keys",
                   "a manifest that disagrees with the app is what puts the "
                   "wrong name on someone's home screen.")
    write_or_check(ASSET_LINKS, build_asset_links(), args.check,
                   "PLAY_SIGNING_KEYS",
                   "Android checks this file before it opens the Play app "
                   "without an address bar.")
    check_play_package()

    icons(args.check)
    linking = check_pages()
    key, share_key = check_launcher()
    print("build-manifests: OK — one manifest for %d instances, linked by %d "
          "page(s), sending a share to %s; the launcher reads %r, the key the "
          "apps write, and marks a shared place under %r, the key they count "
          "it by; the asset links name %s with %d Play signing keys"
          % (len(INSTANCES), linking, site_origin() + START_URL, key, share_key,
             PLAY_PACKAGE, len(PLAY_SIGNING_KEYS)))


if __name__ == "__main__":
    main()
