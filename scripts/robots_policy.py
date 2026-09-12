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

WHAT A STATUS MEANS, per RFC 9309 §2.3.1, with one deliberate departure:
  200 with a body         the file is read
  4xx                     no policy is published: allow all (§2.3.1.3)
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

Self-test: `python3 scripts/robots_policy.py --selftest` parses the three
saved robots.txt files under scripts/fixtures/robots/ and asserts the readings
this project has already established by hand for each.
"""
import re
import sys
import threading
import urllib.parse

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


# --- fetching ----------------------------------------------------------------

class Verdict(object):
    """What one host's robots.txt says about one client, plus how it was obtained."""

    def __init__(self, status, why, policy=None, final_url=None, http_status=None):
        self.status = status          # served | absent | challenge | unreachable
        self.why = why
        self.policy = policy
        self.final_url = final_url
        self.http_status = http_status

    def allows(self, user_agent, url):
        if self.status == "absent":
            return True, self.why
        if self.status in ("challenge", "unreachable"):
            return False, self.why
        return self.policy.decide(user_agent, url)

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
    if 400 <= http_status < 500:
        return Verdict("absent", "no robots.txt (HTTP %d, allow all)" % http_status,
                       policy=RobotsPolicy(""), final_url=final_url, http_status=http_status)
    return Verdict("unreachable", "robots.txt unreachable (HTTP %d, disallow all)" % http_status,
                   final_url=final_url, http_status=http_status)


def fetch_verdict(robots_url, user_agent, timeout=30, session=None):
    """GET one robots.txt and classify it. `session` may be a requests.Session;
    without one the stdlib client is used so this module stays stdlib-only."""
    headers = {"User-Agent": user_agent, "Accept": "text/plain,*/*"}
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

    def __init__(self, session, user_agent, timeout=30):
        self._session = session
        self._ua = user_agent
        self._timeout = timeout
        self._cache = {}
        self._lock = threading.Lock()

    def verdict(self, url):
        parts = urllib.parse.urlparse(url)
        root = "%s://%s/robots.txt" % (parts.scheme, parts.netloc)
        if root in self._cache:
            return self._cache[root]
        with self._lock:
            if root not in self._cache:
                self._cache[root] = fetch_verdict(root, self._ua, self._timeout, self._session)
            return self._cache[root]

    def allows(self, url):
        """(True, why) if this client may fetch `url`, else (False, why)."""
        return self.verdict(url).allows(self._ua, url)

    def crawl_delay(self, url):
        return self.verdict(url).crawl_delay(self._ua)

    def content_signal(self, url):
        return self.verdict(url).content_signal(self._ua)


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
    check(classify(403, "").status == "absent", "403 -> absent (RFC 9309 §2.3.1.3)")
    check(classify(202, "").status == "challenge", "202 -> challenge")
    check(classify(500, "").status == "unreachable", "500 -> unreachable")
    check(classify(None, None, error="timeout").status == "unreachable", "network error -> unreachable")
    check(classify(200, "   ").status == "absent", "200 with an empty body -> allow all")
    v = classify(200, "User-agent: *\nDisallow: /private\n")
    check(v.allows(ua, "https://h/private/x") == (False, v.allows(ua, "https://h/private/x")[1]), "served -> decided by the policy")
    check(v.allows(ua, "https://h/public")[0], "served -> allowed path allowed")
    check(classify(202, "").allows(ua, "https://h/")[0] is False, "challenge -> not fetched")
    check(classify(503, "").allows(ua, "https://h/")[0] is False, "unreachable -> not fetched")

    if failures:
        for f in failures:
            print("robots_policy --selftest: FAIL — " + f, file=sys.stderr)
        sys.exit(1)
    print("robots_policy --selftest: OK — 3 fixtures, %d assertions" % _count_checks())


def _count_checks():
    # The number of check() calls above; kept as a literal so the OK line
    # cannot claim a count the code does not make.
    return 39


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print("usage: robots_policy.py --selftest", file=sys.stderr)
        sys.exit(2)
