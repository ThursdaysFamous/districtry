#!/usr/bin/env python3
"""Chicago's Special Service Area SERVICE PROVIDER list.

An SSA has no elected officeholder: City Council creates it by ordinance and
the Mayor appoints its commission. What a reader actually wants is the
SERVICE PROVIDER AGENCY — the local non-profit the city contracts with to run
the corridor, and the number they would call about a dirty sidewalk. The
boundary dataset (Socrata cmr6-dn8c) names nobody, so the `ssa` card had
nothing but a link until this.

The Department of Planning and Development publishes the list as one
hand-maintained HTML page. It is not a table and not a feed: each SSA is a
bolded heading followed by <br>-separated lines. That shape is the whole
difficulty, and every trap below was MEASURED on the 2026-09-12 page rather
than guessed at.

  1. A PHANTOM BLOCK. "SSA #40 - Expired 12/31/2016, Replaced by" is followed
     by a SEPARATE bolded "SSA #71 Roseland" — the replacement's name is
     bolded inside the notice, so a splitter keyed on <strong> invents a block
     for SSA #71 carrying no provider at all. SSA #71 is a real boundary SSA,
     so that phantom does not fail loudly: it silently gives a live SSA an
     empty provider. A block with no organisation line is dropped, and
     EXPECTED_EMPTY pins the ones that legitimately parse empty so a new one
     is an error rather than a silent loss.
  2. EXPIRED NOTICES. Three headings say "Expired" (#40, #41, #64) and name
     their replacement. #64 carries a FULL provider block — it is the retired
     SSA's old agency — so "has an organisation" is not enough to keep a block.
  3. THE NAME WRAPS. "SSA #42 71st St./" ends mid-name and "Stony Island"
     is the next line, so the first line is part of the NAME, not the
     organisation.
  4. THE ORGANISATION WRAPS. SSA #80's agency is "Greater Englewood Community"
     + "Development Corporation" across two lines.
  5. LINES MERGE, three different ways: city+phone on one line (#19),
     street+city (#33), phone+fax+website (#51).
  6. THE WEBSITE TEXT IS NOT THE URL. SSA #4's link text is
     "www.info@95thstreetba.org" — an e-mail with www. glued on — while its
     href is the real site. The href is what ships.
  7. Three SSAs list no website at all (#20, #44, #52-2021) and one lists two
     (#27). Two write the host with no www. (#55, #60).
  8. One block says "Audit:" where every other says "Audits:" (#63), so a
     stop-word of "audits" lets a run of PDF years leak into the address.

ROBOTS AND USER AGENT, measured 2026-09-12 and re-measured 2026-09-13.
WHAT robots.txt ANSWERS DEPENDS ON WHO ASKS, so both readings are recorded
rather than the convenient one: to Chrome/126 with its client hints
www.chicago.gov has NO robots.txt at all (HTTP 404), so no group binds and
nothing is disallowed; to the districtry token Akamai refuses robots.txt ITSELF
(HTTP 403), which RFC 9309 and CLAUDE.md both file with 404 as allow — so the
answer is the same and the reason is not. An earlier version of this paragraph
gave only the 404, which was true of the client this scraper sends and read as
a fact about the host.

IT IS ALSO READ AT RUN TIME, AS THE CLIENT THAT FETCHES. CLAUDE.md's rule is
that robots.txt is read before the first fetch of a host, and it is read as the
fetching client — so fetch() puts every request through a RobotsGate built on
the same Chrome/126 User-Agent and client-hint headers the page fetch sends, and
stops with a robots-refused verdict if the answer ever becomes a disallow. A
measurement in this docstring is not a substitute for asking: the page is
hand-maintained and the host is Akamai-fronted, so the policy can change between
weekly runs.
The site is Akamai-fronted and refuses the districtry token by client
fingerprint: UA_ROSTER_BOT gets HTTP 403 (AkamaiGHost "Access Denied") on the
requests stack AND on the stdlib client, while Chrome/126 with its client
hints is served the full 271,764-byte page on both. That is the documented
browser-string case in CLAUDE.md, so this sends UA_CHROME_WIN_126; the host's
four rungs are recorded in user-agent-measurements.json.

Writes intermediate JSON; scripts/build_chicago_ssa_providers.py turns it
into il/data/app/chicago-ssa-providers.json.
"""
import argparse
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_common import UA_CHROME_WIN_126, UA_HINTS_CHROME_126  # noqa: E402
from robots_policy import RobotsGate  # noqa: E402  (one reader, fleet-wide)

import requests  # noqa: E402

# ONE LITERAL, NOT TWO ADJACENT ONES, and that is load-bearing rather than
# style. It takes TWO properties of scripts/probe_user_agents.py together, and
# measuring it took three runs:
#   (1) its inventory reads URL literals out of the tree, so a URL split across
#       adjacent string literals contributes its FIRST fragment alone — here
#       the bare directory `/city/en/depts/dcd/supp_info/` on this host; and
#
#   AND A COMMENT IS NOT EXEMPT, which this comment proved on itself. Written
#   with the scheme and host spelled out inside backticks, the line above became
#   an inventory CANDIDATE: probe_user_agents.py scans URL text, not code, so it
#   picked up the quoted address WITH ITS CLOSING BACKTICK and reported
#   www.chicago.gov as all-refused on a 404 for a path that does not exist. The
#   path is written without the scheme for that reason — a prose example of a
#   URL should not be spellable as one.
#   (2) choose_url() then ranks candidates by SHORTEST path (after preferring
#       https and a non-root path), so that fragment outranks the page the
#       scraper actually reads.
# That directory answers HTTP 403 from Apache to EVERY client, so the probe
# recorded www.chicago.gov as `all-refused` on all four rungs — contradicting
# this file's own measurement, which a direct fetch confirms: chrome+hints gets
# HTTP 200 and 271,764 bytes while the districtry token gets 403 from
# AkamaiGHost. Joining both URLs here makes the probe test a real page and
# report `token-refused`, which is what the host does. The first half of this is
# the blind spot validate_card_links.py already handles, by naming concatenated
# literals instead of probing them.
# UNDER il/, where the other Illinois intermediates live, and ANCHORED TO THIS
# FILE rather than the working directory — build_chicago_ssa_providers.py
# anchors its own OUT and DEFAULT_RAW the same way, so the pair agrees from
# any directory. The repo root has no data/source/ at all; only
# data/search-performance.json sits at the root.
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "..", "il", "data", "source",
                           "chicago-ssa-providers.raw.json")
SOURCE_URL = "https://www.chicago.gov/city/en/depts/dcd/supp_info/special_service_areasandproviderlist.html"
# The program page that links it, and what the `ssa` card links. Recorded here
# because the list's own URL is not discoverable from the department landing
# page — it is reached through Business Assistance.
PROGRAM_URL = "https://www.chicago.gov/city/en/depts/dcd/supp_info/special_service_areassaprogram.html"

# Blocks that parse to no organisation and are EXPECTED to. Today this is the
# single phantom from trap 1. A new empty block means the page changed shape.
EXPECTED_EMPTY = {"71"}

# Everything after one of these words belongs to the document archive, not the
# provider. "Audit" is singular on exactly one block (trap 8).
STOP_WORDS = re.compile(r"(?i)^(audits?|agreements?|map|budgets?|annual|sp[ae])\b")
PHONE_RE = re.compile(r"(?i)\bphone:?\s*([0-9][0-9.\-() ]{7,})")
# A house number followed by a compass direction — see the org/street note
# in parse_block(). Deliberately not "starts with a digit".
STREET_RE = re.compile(r"^\d+\s+[NSEW]\b")
# A line that is ONLY a hostname. Two blocks write the site with no www.
# and no scheme (#55 "mgcba.org", #60 "northrivercommission.org"); a
# www.-or-scheme test misses both and they land in the street address.
# Address lines always contain a space, so "no whitespace" is the test.
HOSTLINE_RE = re.compile(r"^(?:https?://)?(?:www\.)?[A-Za-z0-9.\-]+\.[A-Za-z]{2,}/?$")
FAX_RE = re.compile(r"(?i)\bfax:?\s*[0-9][0-9.\-() ]{7,}")
ZIP_RE = re.compile(r"\b(?:Chicago|CHICAGO)\s*,?\s*(?:IL|Illinois)\s*,?\s*(\d{5})\b")
REF_RE = re.compile(r"\s*SSA\s*#\s*0*(\d+)\s*(?:-\s*(\d{4}))?(.*)", re.S)


_ROBOTS = None


def robots_gate():
    """One RobotsGate for this run, built on the CLIENT THIS SCRAPER SENDS.

    The hints go on the SESSION rather than into per-request headers, because
    robots_policy.fetch_verdict() sets only User-Agent and Accept itself and
    merges whatever the session carries — so the robots.txt request goes out as
    the same Chrome/126 client as the page request. Reading it as some other
    client is the mistake this avoids: measured 2026-09-13, this host answers
    robots.txt 404 to Chrome and 403 to the districtry token.
    """
    global _ROBOTS
    if _ROBOTS is None:
        session = requests.Session()
        session.headers.update(UA_HINTS_CHROME_126)
        _ROBOTS = RobotsGate(session, UA_CHROME_WIN_126)
    return _ROBOTS


def fetch(url, timeout=45):
    # BEFORE THE FIRST FETCH OF THE HOST, and cached per host for the run by the
    # gate itself. A refusal is its own verdict and is never worked around.
    allowed, why = robots_gate().allows(url)
    if not allowed:
        sys.exit("chicago-ssa-providers: robots-refused — %s (%s)" % (why, url))
    headers = {"User-Agent": UA_CHROME_WIN_126}
    headers.update(UA_HINTS_CHROME_126)
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def _text(fragment):
    """HTML fragment -> collapsed plain text."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", fragment))).strip()


def split_blocks(page):
    """(heading, body-html) per bolded SSA heading, inside the list table."""
    table = re.search(r"(?is)<table.*?</table>", page)
    if not table:
        raise SystemExit("chicago-ssa-providers: the provider page has no table — "
                         "the page's shape changed; re-read it before trusting this parser")
    parts = re.split(r"(?is)<strong>\s*(SSA\s*#[^<]*?)\s*</strong>", table.group(0))
    return [(parts[i], parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


def parse_block(heading, body):
    """One provider record, or None when the block carries no provider."""
    m = REF_RE.match(html.unescape(heading))
    if not m:
        return None
    ref = m.group(1) + ("-" + m.group(2) if m.group(2) else "")
    name = re.sub(r"\s+", " ", m.group(3) or "").strip(" -–—")

    # trap 2 — an expired SSA's block describes a retired arrangement
    if re.search(r"(?i)expired", heading):
        return {"ref": ref, "number": m.group(1), "expired": True, "name": name}

    # the site url comes from the ANCHOR, never its text (trap 6)
    site = None
    for href, label in re.findall(r'(?is)<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', body):
        if STOP_WORDS.match(_text(label)):
            break
        if href.startswith(("http://", "https://")) and "chicago.gov" not in href:
            site = href
            break

    lines = []
    for seg in re.split(r"(?i)<br\s*/?>", body):
        txt = _text(seg)
        if STOP_WORDS.match(txt):
            break
        if txt:
            lines.append(txt)

    # trap 3 — the heading wrapped mid-name, so line 1 finishes the name
    if name.endswith("/") and lines:
        name = (name + lines.pop(0)).strip()

    phone = addr_street = addr_zip = None
    org_parts, street_parts = [], []
    for line in lines:
        mz = ZIP_RE.search(line)
        mp = PHONE_RE.search(line)
        if mp and not phone:
            phone = re.sub(r"[^0-9]", "", mp.group(1))
            phone = "%s.%s.%s" % (phone[0:3], phone[3:6], phone[6:10]) if len(phone) == 10 else None
        if mz:
            addr_zip = mz.group(1)
            # trap 5 — street and city can share a line (#33)
            before = ZIP_RE.split(line)[0].strip(" ,")
            before = FAX_RE.sub("", PHONE_RE.sub("", before)).strip(" ,")
            if before and not org_parts:
                org_parts.append(before)
            elif before:
                street_parts.append(before)
            continue
        rest = FAX_RE.sub("", PHONE_RE.sub("", line)).strip(" ,")
        if HOSTLINE_RE.match(rest) or re.match(r"(?i)^(www\.|https?://)", rest):
            continue
        if not rest:
            continue
        # Anything before the first STREET line is the organisation, however
        # many lines it wraps over (trap 4). "Starts with a digit" is NOT the
        # street test and the first draft's guard caught it: two agencies are
        # named for the street they sit on — "95th Street/Beverly Hills
        # Business Association" (#4) and "51st Street Business Association"
        # (#52-2021) — and both parsed as addresses, leaving those SSAs with
        # no provider. A Chicago house number is always followed by a compass
        # direction and an organisation name never is, which separates all 50.
        if STREET_RE.match(rest) or street_parts:
            street_parts.append(rest)
        else:
            org_parts.append(rest)

    org = " ".join(org_parts).strip()
    addr_street = " ".join(street_parts).strip() or None
    if addr_street and re.search(r"(?i)\b[a-z0-9\-]+\.(?:org|com|net|gov|info)\b", addr_street):
        raise SystemExit("chicago-ssa-providers: SSA #%s's address carries a hostname "
                         "(%r) — a website line is being read as part of the street "
                         "address" % (ref, addr_street))
    if not org:
        return {"ref": ref, "number": m.group(1), "empty": True, "name": name}
    return {
        "ref": ref, "number": m.group(1), "name": name, "provider": org,
        "address": ("%s, Chicago, IL %s" % (addr_street, addr_zip)
                    if addr_street and addr_zip else None),
        "phone": phone, "url": site,
    }


def scrape():
    page = fetch(SOURCE_URL)
    records, expired, empty = {}, [], []
    for heading, body in split_blocks(page):
        rec = parse_block(heading, body)
        if rec is None:
            continue
        if rec.get("expired"):
            expired.append(rec["ref"])
            continue
        if rec.get("empty"):
            empty.append(rec["number"])
            continue
        if rec["ref"] in records:
            raise SystemExit("chicago-ssa-providers: SSA #%s appears twice — the page's "
                             "numbering is no longer unique, so the join key is unsafe"
                             % rec["ref"])
        records[rec["ref"]] = rec

    unexpected = sorted(set(empty) - EXPECTED_EMPTY)
    if unexpected:
        raise SystemExit("chicago-ssa-providers: %d block(s) carry a heading and no "
                         "provider (%s) and are not the recorded phantom. The page's "
                         "shape changed; read it before trusting this parse."
                         % (len(unexpected), ", ".join("#" + u for u in unexpected)))
    print("chicago-ssa-providers: %d provider(s); skipped %d expired (%s) and %d phantom (%s)"
          % (len(records), len(expired), ", ".join("#" + e for e in expired),
             len(empty), ", ".join("#" + e for e in empty)))
    return {"source_url": SOURCE_URL, "program_url": PROGRAM_URL,
            "expired": sorted(expired), "phantom": sorted(empty),
            "providers": records}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()
    payload = scrape()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    print("wrote %s" % args.out)


if __name__ == "__main__":
    main()
