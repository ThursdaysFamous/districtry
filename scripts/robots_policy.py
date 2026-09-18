#!/usr/bin/env python3
"""
One reading of robots.txt for the whole fleet.

WHY THIS EXISTS. On 2026-09-12 the fleet had four robots.txt readers
(ia/scripts/robots_gate.py, wi/scripts/validate_robots.py, robots_allows() in
scripts/dupage_municipal_officials_scraper.py, robots_still_disallows() in
scripts/validate_card_links.py) and the one that decides fetches for the most
scrapers, Iowa's, used Python's urllib.robotparser. That parser gets three
things wrong that this project had already been burned by once, by hand, on
wyomingmi.gov (docs/DATA_LAYER_GUIDEBOOK.md, the wyomingmi record):

  1. It keeps only the FIRST `User-agent: *` group and drops every later one.
     Measured: two `*` groups, the second `Disallow: /Portals/`, and
     can_fetch("/Portals/0/map.pdf") returns True. That is exactly the shape
     Cloudflare produces when it inserts its managed block (a Content-Signal
     line and `Allow: /`) above a site's own rules, so it is common, not odd.
  2. Within a group the FIRST matching rule wins, where RFC 9309 says the
     LONGEST match wins. So `Allow: /` listed above `Disallow: /Portals/`
     allows /Portals/ even in a single group.
  3. It matches a group's token against the part of our User-Agent before the
     first "/". Two of this fleet's own tokens begin "Mozilla/5.0 (compatible;
     ...)", so a site publishing a group that names them could never bind them.

This module implements RFC 9309 as written: every group whose token names the
client is merged into one; a client named by a specific group is governed by
those groups and not by `*`; a client named by no specific group is governed
by the merged `*` groups; the most specific (longest) matching rule decides,
and a tie goes to Allow. `*` and `$` in paths are honoured. Two extensions
that are not in the RFC but are on real government sites are read from the
binding groups and exposed rather than ignored: Crawl-delay (the largest
value across binding groups) and Content-Signal (Cloudflare's; the values
are merged with `no` overriding `yes`). Neither changes the allow/disallow
answer; what a caller does with them is policy, and the policy is written in
CLAUDE.md's honesty rules, not here.

WHAT A STATUS MEANS, per RFC 9309 §2.3.1, with one deliberate departure and
one reading the caller chooses:
  200 with a body         the file is read
  200 empty, 404, other 4xx
                          no policy is published: allow all (§2.3.1.3)
  401, 403                status `refused`, and by default ALLOW, as the RFC
                          says (it files these with 404). The fleet had two
                          readings of this on 2026-09-12 — the Iowa gate
                          allowed, scripts/dupage_municipal_officials_scraper.py
                          fetched nothing ("a site that will not show its
                          policy has not published one this client can read")
                          — and the first draft of this module took DuPage's
                          side for the whole fleet. Measured the same hour, that
                          would have called EVERY ArcGIS Online FeatureServer
                          disallowed: services1/2/3/8/9.arcgis.com answer 403
                          to /robots.txt from Azure Front Door while serving
                          their layers to every client, and carto.nationalmap.gov
                          and data.openstates.org do the same. An API host with
                          no readable robots.txt is not refusing its API. So the
                          RFC reading is the default and the status stays
                          VISIBLE: a caller reading a municipal WEBSITE, where a
                          403 on robots.txt is a WAF refusing the client, passes
                          refused_is_refusal=True and fetches nothing, which is
                          what DuPage does. Whether that stricter reading should
                          be every website scraper's is an open policy question;
                          this module makes it a one-argument choice rather
                          than four different accidents.
  202                     an HTTP 202 is never a document; it is what captcha
                          fronts return, so it is read as an access control
                          and the host is not fetched (the fleet's standing
                          rule; the RFC does not contemplate it)
  5xx, network failure    the file is unreachable: disallow all (§2.3.1.4)
Redirects are followed and the final URL is reported, because a county's
robots.txt is sometimes its CMS vendor's (Revize serves cherokeecounty.iowa.gov's
from cms7files.revize.com) and the reader should be able to see that.

STDLIB-ONLY AT MODULE SCOPE, like scripts/scraper_common.py and for the same
reason: scripts/validate_workflow_deps.py walks import closures against each
workflow's pip line, and scrapers whose workflows install nothing import this.
A `requests` session may be passed in; without one the fetch uses urllib.

READING A Crawl-delay AND ENACTING ONE ARE DIFFERENT JOBS, and this module
does both: RobotsPolicy.crawl_delay says what a host asked for, and HostPacer
holds a caller to it. The pacer is here rather than in a scraper because the
second caller needed it — it was written for ia/scripts/ia_county_chair_scraper.py
and ia/scripts/validate_sources.py owes the same debt to two other hosts, so
it is shared machinery now instead of a copy. What it is NOT is a global
sleep: see its own docstring for why a pool of workers across many hosts
needs a queue per host.

Self-test: `python3 scripts/robots_policy.py --selftest` parses the three
saved robots.txt files under scripts/fixtures/robots/, asserts the readings
this project has already established by hand for each, and proves the pacer's
rules with threads and no network.
"""
import re
import sys
import threading
import time
import urllib.parse
from contextlib import contextmanager

CONTENT_SIGNAL_KEYS = ("search", "ai-input", "ai-train", "use")


class Group(object):
    """One User-agent group as written, before merging."""

    def __init__(self, first_line):
        self.agents = []          # lowercased tokens, "*" kept as "*"
        self.rules = []           # (allow: bool, pattern: str, line: int)
        self.crawl_delay = None   # float seconds
        self.content_signal = {}  # {"search": "yes", ...}
        self.first_line = first_line

    def names(self, user_agent):
        """True if any agent line binds `user_agent` by name (never for `*`)."""
        ua = user_agent.lower()
        return any(a != "*" and a in ua for a in self.agents)

    def is_catch_all(self):
        return "*" in self.agents


class RobotsPolicy(object):
    """A parsed robots.txt. Ask it about one client at a time."""

    def __init__(self, text):
        self.groups = []
        self.sitemaps = []
        self._parse(text)

    # --- parsing -----------------------------------------------------------
    def _parse(self, text):
        group = None
        in_agent_run = False
        for lineno, raw in enumerate(text.splitlines(), 1):
            line = raw.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if key == "user-agent":
                if not in_agent_run:
                    group = Group(lineno)
                    self.groups.append(group)
                    in_agent_run = True
                group.agents.append(value.lower() if value != "*" else "*")
                continue
            in_agent_run = False
            if key == "sitemap":
                self.sitemaps.append(value)
                continue
            if group is None:
                continue  # rules before any User-agent line have no group (RFC 9309 §2.2.1)
            if key in ("allow", "disallow"):
                if value:  # an empty Disallow: (or Allow:) is a no-op
                    group.rules.append((key == "allow", value, lineno))
            elif key == "crawl-delay":
                try:
                    group.crawl_delay = float(value)
                except ValueError:
                    pass
            elif key == "content-signal":
                for item in value.split(","):
                    k, _, v = item.strip().partition("=")
                    if k.strip():
                        group.content_signal[k.strip().lower()] = v.strip().lower()

    # --- which groups bind a client -----------------------------------------
    def binding_groups(self, user_agent):
        """The merged set of groups that govern `user_agent` (RFC 9309 §2.2.1).

        Groups naming the client take precedence over `*`; if none names it,
        every `*` group applies. The result is a LIST because the caller may
        want to print where a rule came from; the rules are evaluated as one.
        """
        named = [g for g in self.groups if g.names(user_agent)]
        if named:
            return named
        return [g for g in self.groups if g.is_catch_all()]

    # --- the answer ------------------------------------------------------------
    def decide(self, user_agent, url_or_path):
        """(allowed: bool, why: str). Longest matching rule wins; ties allow."""
        path = _canonical_path(url_or_path)
        groups = self.binding_groups(user_agent)
        if not groups:
            return True, "no group binds this client"
        best = None  # (pattern_len, allow, pattern, line)
        for g in groups:
            for allow, pattern, line in g.rules:
                if _pattern_matches(pattern, path):
                    cand = (len(pattern), allow, pattern, line)
                    if best is None or cand[0] > best[0] or (cand[0] == best[0] and allow and not best[1]):
                        best = cand
        if best is None:
            return True, "no rule in %d binding group(s) matches %s" % (len(groups), path)
        _, allow, pattern, line = best
        return allow, "%s: %s (line %d) is the longest match for %s" % (
            "Allow" if allow else "Disallow", pattern, line, path)

    def allows(self, user_agent, url_or_path):
        return self.decide(user_agent, url_or_path)[0]

    def crawl_delay(self, user_agent):
        """The largest Crawl-delay any binding group states, in seconds, or None."""
        delays = [g.crawl_delay for g in self.binding_groups(user_agent) if g.crawl_delay is not None]
        return max(delays) if delays else None

    def content_signal(self, user_agent):
        """Merged Content-Signal of the binding groups; `no` beats `yes`. {} if none."""
        merged = {}
        for g in self.binding_groups(user_agent):
            for k, v in g.content_signal.items():
                if merged.get(k) == "no":
                    continue
                merged[k] = v
        return merged

    def catch_all_group_count(self):
        return sum(1 for g in self.groups if g.is_catch_all())


def _canonical_path(url_or_path):
    """Path + query of a URL (or a bare path), percent-encoding normalised the
    way urllib.robotparser does it: decode, then re-encode with '/' kept."""
    parts = urllib.parse.urlparse(url_or_path)
    path = parts.path if parts.scheme or parts.netloc else url_or_path.split("?", 1)[0]
    if parts.scheme or parts.netloc:
        if parts.query:
            path = path + "?" + parts.query
    else:
        path = url_or_path
    path = urllib.parse.quote(urllib.parse.unquote(path), safe="/?=&:@!$'(),;+%*")
    return path or "/"


def _pattern_matches(pattern, path):
    """RFC 9309 §2.2.3: `*` matches any run of octets, a trailing `$` anchors."""
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    pieces = [re.escape(urllib.parse.quote(urllib.parse.unquote(p), safe="/?=&:@!$'(),;+%"))
              for p in body.split("*")]
    regex = "^" + ".*".join(pieces) + ("$" if anchored else "")
    return re.match(regex, path) is not None


def resolve_template(url):
    """A `%s`-templated URL as the path shape actually requested.

    Some scraper constants are FORMAT TEMPLATES, not addresses — the archive
    ladder's `https://web.archive.org/save/%s` and friends, and Pierce's
    directory pair, templated on the year. Matching a template against
    robots.txt verbatim asks the wrong question twice: `%s` stands where a real
    path segment goes, and `%%20` is a doubled percent that means a literal
    `%20` on the wire. Pierce's real path is
    `/revize/piercewi/Agendas%20and%20Minutes/...`, so a host rule naming that
    directory would not have matched the string the Wisconsin audit was holding.

    The substitution is exactly what `%` formatting does, in the same order:
    the placeholder first, then the doubled percent. A path segment is
    stand-in text of the right SHAPE, which is all a prefix rule can see; a
    report marks these rows so nobody reads a checked template as a checked
    address. (Written for wi/scripts/validate_robots.py; shared here since
    2026-09-12 because the user-agent probe needs the same shape.)
    """
    return url.replace("%s", "PLACEHOLDER").replace("%%", "%")


# --- fetching ----------------------------------------------------------------

class Verdict(object):
    """What one host's robots.txt says about one client, plus how it was obtained."""

    def __init__(self, status, why, policy=None, final_url=None, http_status=None):
        self.status = status          # served | absent | challenge | unreachable
        self.why = why
        self.policy = policy
        self.final_url = final_url
        self.http_status = http_status

    def allows(self, user_agent, url, refused_is_refusal=False):
        """(allowed, why). `refused_is_refusal` is the caller's reading of a
        401/403 on robots.txt itself — see the module docstring's table."""
        if self.status == "absent":
            return True, self.why
        if self.status == "refused":
            return (not refused_is_refusal), self.why
        if self.status in ("challenge", "unreachable"):
            return False, self.why
        # Served: the `why` keeps the "robots.txt served (N bytes)" prefix the
        # Iowa callers have string-matched since 2026-09-06 to tell a refusal
        # by rule ("robots-refused") from a policy that could not be read
        # ("robots-unknown"), then names the rule that decided.
        ok, rule = self.policy.decide(user_agent, url)
        return ok, "%s: %s" % (self.why, rule)

    def crawl_delay(self, user_agent):
        return self.policy.crawl_delay(user_agent) if self.policy else None

    def content_signal(self, user_agent):
        return self.policy.content_signal(user_agent) if self.policy else {}


def classify(http_status, body, final_url=None, error=None):
    """Turn a robots.txt response into a Verdict. Pure, so it is testable."""
    if error is not None:
        return Verdict("unreachable", "robots.txt unreachable: %s" % error, final_url=final_url)
    if http_status == 200 and body is not None and body.strip():
        return Verdict("served", "robots.txt served (%d bytes)" % len(body),
                       policy=RobotsPolicy(body), final_url=final_url, http_status=200)
    if http_status == 200:
        return Verdict("absent", "robots.txt served empty (allow all)", policy=RobotsPolicy(""),
                       final_url=final_url, http_status=200)
    if http_status == 202:
        return Verdict("challenge", "robots.txt answered HTTP 202 (an access control, not a document)",
                       final_url=final_url, http_status=202)
    if http_status in (401, 403):
        return Verdict("refused", "robots.txt refused to this client (HTTP %d) — no readable policy" % http_status,
                       final_url=final_url, http_status=http_status)
    if 400 <= http_status < 500:
        return Verdict("absent", "no robots.txt (HTTP %d, allow all)" % http_status,
                       policy=RobotsPolicy(""), final_url=final_url, http_status=http_status)
    return Verdict("unreachable", "robots.txt unreachable (HTTP %d, disallow all)" % http_status,
                   final_url=final_url, http_status=http_status)


def fetch_verdict(robots_url, user_agent, timeout=30, session=None, headers=None):
    """GET one robots.txt and classify it. `session` may be a requests.Session;
    without one the stdlib client is used so this module stays stdlib-only.

    READ THE POLICY WITH THE CLIENT THAT WILL CRAWL. `headers`, when given, is
    the full header set the caller's own fetches send; User-Agent is forced to
    `user_agent` so the group that binds still matches what is passed in. A
    caller that sends seven headers and reads robots.txt with two is measuring
    a different client from the one it crawls with, and several county CMSs
    answer the two differently: measured 2026-09-13, all five hosts in
    wi_county_board_scraper.ROBOTS_REFUSED_PENDING returned 403 to the
    User-Agent + Accept pair and 200 to the crawl's own headers. The asymmetry
    runs one way only -- reading with a STRONGER client than the crawl would be
    defeating a control, so no caller may pass headers its fetches do not send.

    Optional and additive: existing callers keep the two-header behaviour.
    """
    headers = dict(headers or {}, **{"User-Agent": user_agent}) if headers \
        else {"User-Agent": user_agent, "Accept": "text/plain,*/*"}
    try:
        if session is not None:
            r = session.get(robots_url, headers=headers, timeout=timeout, allow_redirects=True)
            return classify(r.status_code, r.text, final_url=r.url)
        import urllib.request
        import urllib.error
        req = urllib.request.Request(robots_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", "replace")
                return classify(resp.status, body, final_url=resp.geturl())
        except urllib.error.HTTPError as e:
            return classify(e.code, "", final_url=e.geturl())
    except Exception as exc:  # network, TLS, DNS
        return classify(None, None, error="%s: %s" % (type(exc).__name__, exc))


class RobotsGate(object):
    """One robots.txt fetch per host, cached for the run, thread-safe.

    The API ia/scripts/robots_gate.py has carried since 2026-09-06, so its four
    callers change one import and nothing else:
        gate = RobotsGate(session, USER_AGENT)
        ok, why = gate.allows(url)
    plus two readings the old gate could not give:
        gate.crawl_delay(url)      seconds the binding group asks for, or None
        gate.content_signal(url)   the binding group's Content-Signal, or {}
    The lock is held across the fetch so a host is requested once however
    many workers ask at the same moment.
    """

    def __init__(self, session, user_agent, timeout=30, headers=None):
        self._session = session
        self._ua = user_agent
        self._timeout = timeout
        # The caller's OWN header set, forwarded to fetch_verdict so the policy
        # is read with the client that will crawl -- see its docstring for the
        # five county hosts that answer a two-header read and a full one
        # differently. Optional and additive: a caller that passes nothing
        # keeps the two-header behaviour every existing caller has.
        self._headers = headers
        self._cache = {}
        self._lock = threading.Lock()

    def verdict(self, url):
        parts = urllib.parse.urlparse(url)
        root = "%s://%s/robots.txt" % (parts.scheme, parts.netloc)
        if root in self._cache:
            return self._cache[root]
        with self._lock:
            if root not in self._cache:
                self._cache[root] = fetch_verdict(root, self._ua, self._timeout,
                                                  self._session, self._headers)
            return self._cache[root]

    def allows(self, url):
        """(True, why) if this client may fetch `url`, else (False, why)."""
        return self.verdict(url).allows(self._ua, url)

    def crawl_delay(self, url):
        return self.verdict(url).crawl_delay(self._ua)

    def content_signal(self, url):
        return self.verdict(url).content_signal(self._ua)



class HostPacer(object):
    """Hold every host that states a Crawl-delay to one request at a time.

    WHY THIS IS NOT A GLOBAL SLEEP. ia/scripts/ia_judicial_district_scraper.py
    honours a Crawl-delay by sleeping between fetches, which is right for it:
    one host, one thread. The board-chair scrape runs six workers across 98
    different county hosts, so a global sleep would pace 97 hosts that asked
    for nothing in order to pace the one that did. A host that states a delay
    gets a queue of its own; every other host keeps the pool's full
    parallelism. A single-threaded caller gets the same guarantee for free,
    which is why ia/scripts/validate_sources.py can use the identical object
    to put 30 seconds between its two www.iowacourts.gov probes.

    MEASURED 2026-09-12 FROM A CLAUDE CODE SANDBOX, and the numbers are the
    point. 237 scheduled scripts NAME 430 distinct hosts in code; reading
    every one of their robots.txt files, 25 STATE A Crawl-delay THAT BINDS
    THIS PROJECT, and 24 of those scripts name at least one. NOT ONE host
    states a different delay for a different token: the same value comes back
    for `districtry/1.0`, `districtry-wisconsin/1.0`, the roster bot's string
    and a Chrome/126 string alike, which is `User-agent: *` binding all of
    them exactly as CLAUDE.md says. THE VANTAGE IS NAMED BECAUSE REACHABILITY
    MOVES WITH IT: review's sandbox and this one disagree about which county
    sites answer at all (the address-dependence this repo records for Clayton
    and Polk). The delays do not — they are in a file every vantage can read.

    THE SURFACE, stated so it can be re-derived: every string constant of
    every script a scheduled workflow runs, module and function docstrings
    excluded (a URL a file EXPLAINS is not a URL a file REQUESTS — one Iowa
    builder names iowacourts.gov four times in prose and fetches a different
    host), plus the hosts the board-chair scrape reads out of
    ia-county-board-directory.json. Four strings that parse as a netloc are
    not hosts and are excluded: a `maps.*` template and the three XML/JSON-LD
    NAMESPACE URIs (schema.org, schemas.openxmlformats.org, www.opengis.net),
    which are identifiers and are never fetched.

    NAMING IS NOT FETCHING, which is the correction that produced these
    numbers. A first cut skipped any script whose source did not mention
    requests, urlopen, urllib.request, httpx or playwright, meaning to skip
    pure builders — and it dropped 135 of 290 scheduled scripts, including
    scrapers that fetch through a shared helper, a bound `session.get`, or a
    curl subprocess. With no filter, three more scripts name a delay-stating
    host and ALL THREE ONLY CITE IT: ia/scripts/build_dsm_wards.py carries
    data.dsm.city (60 s) as TERMS_URL and writes it into the file it builds,
    curling services.arcgis.com instead; scripts/build_montgomery_board_roster.py
    and wi/scripts/build_wi_circuit_court_roster.py make no network call at
    all. A BUILDER CITES ITS SOURCE URL IN THE FILE IT WRITES, so a
    host-naming surface bounds who MIGHT fetch and settles nothing on its own.

    THREE DELAY-STATING HOSTS SIT OUTSIDE THAT SURFACE, each for a stated
    reason: www.cityofdodgeville.com and www.cityofwestby.org appear only
    inside a COMMENT block in wi/scripts/wi_alderperson_scraper.py, which ast
    drops by construction; and www.kossuthcounty.iowa.gov is REACHED BY
    REDIRECT rather than named -- the directory holds the bare spelling and
    the server 301s. It was measured at all only because the pacer's
    self-test fixtures used to sit in the chair scraper and named it as a
    literal; those moved here with the test, so no surface names it now. An earlier draft of this
    docstring said "419 hosts, 27 delays", which paired one surface's
    denominator with another's numerator — the 27 came from a first pass that
    regexed raw file text and therefore caught the two commented-out URLs.
    ON CLAUDE.md's OWN FIGURE: it records a 2026-09-12 sweep of "386 hosts
    the scheduled scrapers read" finding 26 delays. No file records that
    surface, so the two were NOT reconciled and neither is claimed here to be
    the wrong count.

    TWO DECISIONS THAT LOOK LIKE DETAILS AND ARE NOT:

    A LEADING `www.` IS FOLDED AWAY, because the pacer's key has to be the
    SERVER and a netloc is not one. `kossuthcounty.iowa.gov` and
    `www.kossuthcounty.iowa.gov` are one machine: measured, the bare name 301s
    to the www one and both return the same 243,691-byte body from the same
    Cloudflare server, and both robots.txt reads state 10 s. Keying on the
    netloc would let one machine hold two queues and half the delay it asked
    for, while reading correctly in the log.

    WHAT THE CHAIR SCRAPE ACTUALLY DOES, corrected 2026-09-12 after review
    read the code: it does NOT try both spellings. `pages_for()` builds every
    URL with urljoin from the directory's own base -- the bare spelling, for
    Kossuth -- and DROPS any candidate whose netloc differs from that base, so
    a www link on the page is skipped as off-site. The www host is reached
    only because `get()` passes allow_redirects=True and the server 301s,
    INSIDE the held block, on a hold keyed to the bare name. So for this
    caller the fold currently changes nothing, and the live run proves it by
    printing one key: `Crawl-delay honoured: kossuthcounty.iowa.gov 10 s`.
    THE FOLD IS A GUARD, NOT LOAD-BEARING TODAY: measured across the 98
    directory hosts, 50 carry a `www.` and NOT ONE host appears in both
    spellings, and validate_sources.py reaches www.iowacourts.gov and
    www.issda.org under one spelling each. It earns its place the day two
    routes name one server differently, which costs nothing to prevent and is
    invisible once it happens.

    ROBOTS.TXT ITSELF IS NOT PACED. The delay is stated INSIDE robots.txt, so
    the first fetch of it cannot be governed by a number it has not read yet,
    and RobotsGate fetches each host's file once and caches it. Every other
    request to a delay-stating site is paced.
    """

    def __init__(self, gate):
        self._gate = gate
        self._table_lock = threading.Lock()
        self._sites = {}        # site -> [lock, last_request_monotonic]
        self.honoured = {}      # site -> delay, for the printed report

    @staticmethod
    def site_of(url):
        host = (urllib.parse.urlparse(url).netloc or "").lower()
        return host[4:] if host.startswith("www.") else host

    @contextmanager
    def hold(self, url):
        delay = None
        try:
            delay = self._gate.crawl_delay(url) if self._gate else None
        except Exception:
            delay = None        # a pacer must never be why a fetch fails
        if not delay:
            yield
            return
        site = self.site_of(url)
        with self._table_lock:
            entry = self._sites.setdefault(site, [threading.Lock(), 0.0])
            self.honoured[site] = delay
        with entry[0]:
            wait = entry[1] + delay - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            try:
                yield
            finally:
                entry[1] = time.monotonic()

    def report(self, prefix="  "):
        """The lines a caller prints so an honoured delay is not silent.

        A delay that is honoured without saying so cannot be told from one
        that is ignored, which is the whole reason the chair scrape prints it.
        """
        if self.honoured:
            return ["%sCrawl-delay honoured: %s %g s" % (prefix, site, delay)
                    for site, delay in sorted(self.honoured.items())]
        return ["%sCrawl-delay honoured: no host this run stated one" % prefix]

# --- self-test on the saved fixtures ------------------------------------------

def _selftest():
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    fixtures = os.path.join(here, "fixtures", "robots")
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)

    def load(name):
        with open(os.path.join(fixtures, name), encoding="utf-8") as f:
            return RobotsPolicy(f.read())

    ua = "districtry/1.0 (+https://districtry.com/)"

    # wyomingmi.gov: two `*` groups 47 lines apart; the second's `Disallow:
    # /Portals/` (9 octets) beats the first's `Allow: /` (1 octet). The reading
    # docs/DATA_LAYER_GUIDEBOOK.md established by hand on 2026-09-09.
    w = load("www.wyomingmi.gov.txt")
    check(w.catch_all_group_count() == 2, "wyomingmi: expected two `*` groups")
    ok, why = w.decide(ua, "/Portals/0/Documents/Precincts/2022 Precinct Map_1.pdf")
    check(not ok, "wyomingmi: /Portals/ must be disallowed to `*` (%s)" % why)
    check("/Portals/" in why and "Disallow" in why, "wyomingmi: why must name the rule (%s)" % why)
    check(w.allows(ua, "/government/city-clerk/"), "wyomingmi: an ordinary page must be allowed")
    check(w.content_signal(ua) == {"search": "yes", "ai-train": "no", "use": "reference"},
          "wyomingmi: Content-Signal must be read from the binding `*` group (%r)" % w.content_signal(ua))
    check(w.allows("ClaudeBot/1.0", "/anything") is False,
          "wyomingmi: a group naming ClaudeBot binds ClaudeBot and disallows it")
    # ...and a ClaudeBot group does not bind a districtry token:
    check(w.allows(ua, "/anything"), "wyomingmi: the ClaudeBot group must not bind districtry")

    # iowacourts.gov: a Cloudflare `*` block, then a second `*` group carrying
    # `Crawl-delay: 30` and an empty `Disallow:`. Everything is allowed and the
    # delay binds.
    i = load("www.iowacourts.gov.txt")
    check(i.catch_all_group_count() == 2, "iowacourts: expected two `*` groups")
    check(i.allows(ua, "/iowa-courts/district-court/judicial-district-2/judges-and-magistrates/"),
          "iowacourts: the judges page must be allowed")
    check(i.crawl_delay(ua) == 30.0, "iowacourts: Crawl-delay 30 must bind `*` (%r)" % i.crawl_delay(ua))
    check(i.content_signal(ua).get("ai-train") == "no", "iowacourts: ai-train=no must be read")

    # sheboyganwi.gov: the Cloudflare `*` block, then a second `*` group with
    # 26 Disallows (admin, search, map pages), then Siteimprove-only crawl
    # delays. The Common-Council page the WI scraper reads is allowed; /admin
    # is not; the crawl delay does not bind `*`.
    s = load("www.sheboyganwi.gov.txt")
    check(s.catch_all_group_count() == 2, "sheboygan: expected two `*` groups")
    check(s.allows(ua, "/395/Common-Council"), "sheboygan: /395/Common-Council must be allowed")
    check(not s.allows(ua, "/admin/users"), "sheboygan: /admin must be disallowed")
    check(not s.allows(ua, "/Search.aspx?q=x"), "sheboygan: /Search.aspx must be disallowed")
    check(s.crawl_delay(ua) is None, "sheboygan: Crawl-delay binds Siteimprove only (%r)" % s.crawl_delay(ua))
    check(s.crawl_delay("Siteimprovebot/2.0") == 20.0, "sheboygan: Siteimprovebot must see Crawl-delay 20")

    # Semantics that need no fixture: longest match, tie -> allow, wildcards,
    # `$`, a specific group overriding `*`, and the `Mozilla/5.0 (compatible;
    # ...)` token shape being bindable by name.
    p = RobotsPolicy("User-agent: *\nDisallow: /a\nAllow: /a/b\nDisallow: /a/b/c$\nDisallow: /*.pdf$\n")
    check(not p.allows(ua, "/a/x"), "longest match: /a disallows /a/x")
    check(p.allows(ua, "/a/b/x"), "longest match: /a/b allows /a/b/x over /a")
    check(not p.allows(ua, "/a/b/c"), "$ anchors: /a/b/c$ disallows exactly /a/b/c")
    check(p.allows(ua, "/a/b/cd"), "$ anchors: /a/b/c$ does not match /a/b/cd")
    check(not p.allows(ua, "/docs/map.pdf"), "wildcard: /*.pdf$ disallows a pdf")
    check(p.allows(ua, "/docs/map.pdf?x=1"), "$ anchors the whole path+query: a query after .pdf escapes /*.pdf$")
    t = RobotsPolicy("User-agent: *\nAllow: /x\nDisallow: /x\n")
    check(t.allows(ua, "/x/y"), "tie between equal-length Allow and Disallow goes to Allow")
    # Two shapes wi/scripts/validate_robots.py learned the hard way before its
    # parser was retired into this one (2026-09-12). cms5.revize.com's `*`
    # group is `Allow: /*.pdf$` (+ .DOC/.DOCX/.PPT/.PPTX) then `Disallow: /`:
    # documents yes, everything else no — a startswith matcher read it as a
    # flat refusal. And Clark County's carries `Disallow: *?lightbox=`, which
    # only a match against path AND query can see.
    rv = RobotsPolicy("User-agent: *\nAllow: /*.pdf$\nAllow: /*.docx$\nDisallow: /\n")
    check(rv.allows(ua, "/revize/x/Agendas%20and%20Minutes/2026.pdf"), "revize: a .pdf is allowed by /*.pdf$")
    check(not rv.allows(ua, "/revize/x/board.html"), "revize: everything else is disallowed")
    check(not rv.allows(ua, "/revize/x/2026.pdf?t=123"), "revize: a cache-busted .pdf?t= is NOT reached by /*.pdf$")
    cl = RobotsPolicy("User-agent: *\nDisallow: *?lightbox=\n")
    check(not cl.allows(ua, "/gallery?lightbox=3"), "clark: *?lightbox= matches path+query")
    check(cl.allows(ua, "/gallery"), "clark: the bare path is allowed")
    q = RobotsPolicy("User-agent: districtry\nAllow: /\nUser-agent: *\nDisallow: /\n")
    check(q.allows(ua, "/anything"), "a group naming districtry governs it; `*` does not apply")
    check(not q.allows("SomethingElse/1.0", "/anything"), "an unnamed client falls to `*`")
    compact = "Mozilla/5.0 (compatible; districtry-roster/1.0)"
    r = RobotsPolicy("User-agent: districtry-roster\nDisallow: /\n")
    check(not r.allows(compact, "/"), "a token inside a Mozilla-prefixed UA is bound by a group naming it")
    e = RobotsPolicy("Disallow: /\nUser-agent: *\nAllow: /\n")
    check(e.allows(ua, "/"), "rules before the first User-agent line belong to no group")
    m = RobotsPolicy("User-agent: a\nUser-agent: b\nDisallow: /\n")
    check(not m.allows("b/1.0", "/"), "consecutive User-agent lines share one group")

    # classify(): the status table in the docstring.
    check(classify(404, "").status == "absent", "404 -> absent")
    check(classify(403, "").status == "refused", "403 -> status refused, visible to the caller")
    check(classify(401, "").status == "refused", "401 -> refused")
    check(classify(410, "").status == "absent", "410 -> absent (any other 4xx is no policy)")
    check(classify(403, "").allows(ua, "https://h/")[0] is True,
          "refused -> allowed by default (RFC 9309 §2.3.1.3; ArcGIS Online 403s its robots.txt)")
    check(classify(403, "").allows(ua, "https://h/", refused_is_refusal=True)[0] is False,
          "refused -> not fetched when the caller reads a website's 403 as a refusal")
    check(classify(202, "").status == "challenge", "202 -> challenge")
    check(classify(500, "").status == "unreachable", "500 -> unreachable")
    check(classify(None, None, error="timeout").status == "unreachable", "network error -> unreachable")
    check(classify(200, "   ").status == "absent", "200 with an empty body -> allow all")
    v = classify(200, "User-agent: *\nDisallow: /private\n")
    ok, why = v.allows(ua, "https://h/private/x")
    check(ok is False and why.startswith("robots.txt served (") and "/private" in why,
          "served -> decided by the policy, why keeps the served prefix and names the rule (%s)" % why)
    check(v.allows(ua, "https://h/public")[0], "served -> allowed path allowed")
    check(classify(202, "").allows(ua, "https://h/")[0] is False, "challenge -> not fetched")
    check(classify(503, "").allows(ua, "https://h/")[0] is False, "unreachable -> not fetched")

    # --- HostPacer: the three claims, proven with threads and no network ----
    # Small delays so this stays under a second; the arithmetic is the same at
    # Kossuth's ten and iowacourts.gov's thirty.
    from concurrent.futures import ThreadPoolExecutor

    class _FakeGate(object):
        """A gate whose Crawl-delay answers come from a table, not a network."""

        def __init__(self, table):
            self._table = table

        def crawl_delay(self, url):
            return self._table.get(HostPacer.site_of(url))

    # (1) a leading www. folds, so one server is one queue
    check(HostPacer.site_of("https://www.kossuthcounty.iowa.gov/a")
          == HostPacer.site_of("https://kossuthcounty.iowa.gov/b")
          == "kossuthcounty.iowa.gov",
          "pacer: www.host and host are not one pacing key")

    DELAY = 0.20
    pacer = HostPacer(_FakeGate({"paced.example": DELAY}))
    stamps = {"paced": [], "free": []}
    stamp_lock = threading.Lock()

    def hit(bucket, url):
        with pacer.hold(url):
            with stamp_lock:
                stamps[bucket].append(time.monotonic())
            time.sleep(0.01)

    # (2) a delay-stating site is serialised and spaced, across BOTH spellings
    urls = ["https://paced.example/1", "https://www.paced.example/2",
            "https://paced.example/3", "https://www.paced.example/4"]
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(lambda u: hit("paced", u), urls))
    paced_elapsed = time.monotonic() - t0
    gaps = [b - a for a, b in zip(sorted(stamps["paced"]), sorted(stamps["paced"])[1:])]
    check(all(g >= DELAY * 0.9 for g in gaps),
          "pacer: a stated delay did not space that site's requests (gaps %s)"
          % ["%.2f" % g for g in gaps])
    check(paced_elapsed >= DELAY * 3 * 0.9,
          "pacer: four paced requests took %.2f s, under three delays" % paced_elapsed)

    # (3) a site that states nothing keeps the pool's parallelism
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(lambda u: hit("free", u),
                    ["https://free.example/%d" % i for i in range(6)]))
    free_elapsed = time.monotonic() - t0
    check(free_elapsed < DELAY,
          "pacer: an unpaced site was slowed (%.2f s)" % free_elapsed)
    check(list(pacer.honoured) == ["paced.example"],
          "pacer: reported the wrong set of honoured sites (%s)" % pacer.honoured)

    # THIS PROJECT'S OWN robots.txt, read by this same reader. Everything above
    # measures how districtry reads other people's files; districtry publishes
    # one too, and on 2026-09-13 it started carrying the Content-Signal line —
    # search=yes, ai-input=yes, ai-train=no, use=reference — which is the same
    # reading it already applied to Sheboygan's. A line this reader cannot
    # parse is a reservation of rights that says nothing, and nothing else in
    # the repo looks at this file: validate_card_links.py scans *.html, and
    # build_sitemap.py does not list robots.txt. So the assertions are here.
    own = os.path.join(os.path.dirname(here), "robots.txt")
    if not os.path.exists(own):
        check(False, "districtry's own robots.txt is not in the tree at %s" % own)
    else:
        with open(own, encoding="utf-8") as f:
            mine = RobotsPolicy(f.read())
        want = {"search": "yes", "ai-input": "yes", "ai-train": "no",
                "use": "reference"}
        check(mine.catch_all_group_count() == 1,
              "own robots.txt: expected exactly one `*` group, found %d — a second "
              "one would change what the signal says to whoever the first does "
              "not name" % mine.catch_all_group_count())
        # Each agent separately, because the bug this guards is a group that
        # names one client and silently drops the signal for the rest.
        for who in (ua, "Googlebot", "Bingbot", "ClaudeBot", "GPTBot", "CCBot",
                    "Google-Extended", "anthropic-ai", "meta-externalagent"):
            check(mine.content_signal(who) == want,
                  "own robots.txt: %s must read the full signal, got %r"
                  % (who, mine.content_signal(who)))
            check(mine.allows(who, "/il/county-board/lasalle.html"),
                  "own robots.txt: %s must be allowed to fetch a county board "
                  "page — no crawler is disallowed by name here, and a page "
                  "published to be found cannot be withheld from the clients "
                  "that find it" % who)
        check(mine.allows(ua, "/llms.txt"),
              "own robots.txt: /llms.txt must be fetchable — it is the guide "
              "this file points at")

    if failures:
        for f in failures:
            print("robots_policy --selftest: FAIL — " + f, file=sys.stderr)
        sys.exit(1)
    print("robots_policy --selftest: OK — 3 fixtures + this site's own "
          "robots.txt + the pacer, %d assertions" % _count_checks())


def _count_checks():
    # The number of check() calls above; kept as a literal so the OK line
    # cannot claim a count the code does not make. 48 on the three saved
    # robots.txt files, 5 on the pacer, and 20 on this site's own robots.txt
    # (one structural, nine agents x two, plus /llms.txt). COUNTED BY RUNNING
    # IT rather than by reading the source: the file-missing check() is a call
    # in the source that the normal path never executes, and a first draft of
    # this literal said 74 for exactly that reason.
    return 73


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print("usage: robots_policy.py --selftest", file=sys.stderr)
        sys.exit(2)
