#!/usr/bin/env python3
"""
robots.txt rules: the `*` group, and whether it permits a path.

ONE COPY, because both halves of this file are a record of getting it wrong.
These four functions lived in wi/scripts/validate_robots.py, which was their
only consumer until 2026-09-12, when two more appeared: the fleet's user-agent
probe (scripts/probe_user_agents.py) and a SCRAPER that has to ask before it
fetches (scripts/logan_municipal_officials_scraper.py, whose yearbook sits under
a Disallow). A second copy is how permitted()'s docstring — which records that
literal startswith() matching cannot match a rule containing `*` or `$` at all,
and turned cms5.revize.com's "documents yes, everything else no" into a flat
refusal — drifts away from the code it describes.

THE `*` GROUP IS THE ONE THAT APPLIES to this project. Its clients are none of
the named agents, and a group naming an AI vendor's crawler (ClaudeBot, GPTBot,
CCBot, anthropic-ai, Claude-Web) covers that vendor's own crawling rather than
these scripts — reading one as binding cost real data, and is recorded in
CLAUDE.md's robots section. Reading a NARROWER group to get a friendlier answer
would be picking the rule that suits, which is the opposite error.

Nothing here fetches. A caller reads robots.txt with the client that will do the
crawling — sending a weaker client than the crawl is the one asymmetry a
compliance check must not have — and hands the text to star_disallows().
"""

import re


def star_disallows(text):
    """The `User-agent: *` group's Disallow lines, or None if it has no group.

    Consecutive `User-agent:` lines share one group, which is why the agents
    are collected and the Disallow lines applied to all of them — a file that
    reads `User-agent: A` / `User-agent: *` / `Disallow: /` disallows `*`.
    """
    groups, current, pending = {}, [], True
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = (p.strip() for p in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if not pending:
                current, pending = [], True
            current.append(value.lower())
            groups.setdefault(value.lower(), [])
        elif key in ("disallow", "allow") and current:
            pending = False
            for agent in current:
                groups.setdefault(agent, []).append((key, value))
    return groups.get("*")


def _rule_re(value):
    """One robots.txt path pattern as a regex anchored at the path start.

    `*` matches any run of characters and a TRAILING `$` anchors the end of the
    path — RFC 9309 section 2.2.3, and what every major crawler implements.
    Everything else is a literal, so the regex is built from escaped chunks
    rather than by escaping the whole string and unescaping the metacharacters.
    """
    anchored = value.endswith("$")
    body = value[:-1] if anchored else value
    pattern = ".*".join(re.escape(part) for part in body.split("*"))
    return re.compile("^" + pattern + ("$" if anchored else ""))


def permitted(path, rules):
    """robots.txt longest-match: the most specific rule wins, Allow ties win.

    THE WILDCARDS ARE NOT DECORATION, and leaving them out got a real host
    wrong in the direction that matters. This did literal `startswith`
    matching, which cannot match a pattern containing `*` or `$` AT ALL — so
    every wildcard rule silently evaluated as "does not apply". On
    cms5.revize.com, whose `*` group reads

        Allow: /*.pdf$   (and .DOC/.DOCX/.PPT/.PPTX)
        Disallow: /

    that turned an unmistakable policy — documents yes, everything else no —
    into a flat refusal, because only the bare `Disallow: /` could match. The
    same blindness runs the other way and is worse: a wildcard DISALLOW that
    genuinely covers a path this repo fetches would have been ignored, and the
    gate would have reported the crawl permitted. Clark's own file carries
    `Disallow: *?lightbox=`, which this had been discarding; it happens not to
    cover anything fetched here, which is luck rather than a check.

    Specificity is the length of the rule as WRITTEN, which is what makes
    `/*.pdf$` (7) beat `/` (1) rather than the other way round.
    """
    best_len, best_kind = -1, "allow"
    for kind, value in rules:
        if not value:
            continue                    # `Disallow:` with no value permits all
        if not _rule_re(value).match(path):
            continue
        if len(value) > best_len:
            best_len, best_kind = len(value), kind
        elif len(value) == best_len and kind == "allow":
            best_kind = "allow"
    return best_kind == "allow"


def resolve_template(url):
    """A `%s`-templated URL as the path shape actually requested.

    Six of the swept constants are FORMAT TEMPLATES, not addresses — the
    archive ladder's four (`https://web.archive.org/save/%s` and friends) and
    Pierce's directory pair, which is templated on the year. Matching a
    template against robots.txt verbatim asks the wrong question twice: `%s`
    stands where a real path segment goes, and `%%20` is a doubled percent
    that means a literal `%20` on the wire. Pierce's real path is
    `/revize/piercewi/Agendas%20and%20Minutes/...`, so a host rule naming that
    directory would not have matched the string this script was holding.

    The substitution is exactly what `%` formatting does, in the same order:
    the placeholder first, then the doubled percent. A path segment is
    stand-in text of the right SHAPE, which is all a prefix rule can see; the
    report marks these rows so nobody reads a checked template as a checked
    address.
    """
    return url.replace("%s", "PLACEHOLDER").replace("%%", "%")
