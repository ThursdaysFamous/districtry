#!/usr/bin/env python3
"""
Scrape the boards of trustees of Iowa's 15 community colleges, one trustee per
director district, from each college's own board page.

THE ROUTE, AND WHY IT IS FIFTEEN PAGES
---------------------------------------
Iowa Code 260C.11 elects one trustee from each director district of a merged
area, and the state keeps no list of them: the Department of Education does
not publish one and the Iowa Association of Community College Trustees names
no trustee by district. Each college publishes its own board, and measured
2026-10-21 all fifteen do, on pages that answer HTTP 200 to this project's own
token (`UA_HEADERS_ROSTER_BOT`) after a robots.txt read that permits them. They
are laid out fifteen ways, so each has a parser of its own below, and each
parser is held to the districts the college's own plan draws
(`ia-cc-director-districts.json`) by the builder.

FOURTEEN NAME THE DISTRICT AND ONE DOES NOT
--------------------------------------------
Northeast Iowa (merged area 1) lists each trustee with the SCHOOL DISTRICTS
they represent and no director-district number. Four of its nine trustees list
Dubuque Community, so a school district does not identify a seat, and this file
does not guess one. NICC is read for the record and shipped with no district,
which the card states.

NO HOME ADDRESSES, EVER
------------------------
Hawkeye (merged area 7) prints each trustee's street address, which is where
they live, and the names of their spouses. This file reads the NAME, the ROLE,
the TERM, an E-MAIL from a `mailto:` link inside the trustee's own entry and a
TELEPHONE printed in that entry, and never an address line, not even to drop it
later: a value that is parsed is a value that can leak into an output. A
telephone or e-mail printed in one official's own entry ships under the fleet
rule of 2026-10-17 (CLAUDE.md), whosever line it is.

ONE COLLEGE HIDES ITS ADDRESSES FROM MACHINES, AND THAT IS RESPECTED
---------------------------------------------------------------------
Eastern Iowa (merged area 9) writes each address as `adermody9FREEEICC`,
which a script on the page turns back into an address. That is a page asking
not to be harvested, so no e-mail is read from it.

COMMENTED-OUT MARKUP IS NOT PUBLISHED
--------------------------------------
Iowa Central's page carries a trustee's former address inside an HTML comment
(`bmwessels@... -->`). A reader sees nothing there, so every comment is removed
before anything is read.

Usage:
    python3 ia/scripts/ia_cc_trustee_scraper.py            # -> ia/scripts/.cache/
    python3 ia/scripts/ia_cc_trustee_scraper.py --save-cache DIR   # keep the pages
    python3 ia/scripts/ia_cc_trustee_scraper.py --from-cache DIR   # re-parse them
    python3 ia/scripts/ia_cc_trustee_scraper.py --selftest
"""

import argparse
import html
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(HERE, ".cache", "ia_cc_trustees.json")
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from scraper_common import (  # noqa: E402
    UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, require_robots_once)

# merged-area number (the shipped `collegedistrict`) -> board page
PAGES = {
    1: "https://www.nicc.edu/about/administration/board-of-trustees/",
    2: "https://www.niacc.edu/about/governing-board/",
    3: "https://iowalakes.edu/contact_category/board-of-trustees/",
    4: "https://nwicc.edu/about/board-of-trustees/",
    5: "https://www.iowacentral.edu/about/trustees.asp",
    6: "https://www.iavalley.edu/district/about-iowa-valley/board-of-directors.html",
    7: "https://www.hawkeyecollege.edu/about/leadership/board-of-trustees",
    9: "https://eicc.edu/about/board-trustees/default.aspx",
    10: "https://www.kirkwood.edu/about-us/trustees/index",
    11: "https://www.dmacc.edu/about/leadership.html",
    12: "https://www.witcc.edu/about/board/",
    13: "https://www.iwcc.edu/about/administration/board-of-trustees/",
    14: "https://www.swcciowa.edu/about/general-college-information/board-of-directors",
    15: "https://www.indianhills.edu/about/boardoftrustees.php",
    16: "https://www.scciowa.edu/meet/about/leadership/board-of-trustees/index.aspx",
}

# Iowa Lakes lists its board as links to one profile page per trustee; each
# profile names the district. Read from the board page itself, never listed here.
IOWA_LAKES_PROFILE = re.compile(r'href="(https://iowalakes\.edu/directory/[a-z0-9-]+/)"')

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7,
         "VIII": 8, "IX": 9}
DNUM = r"(\d{1,2}|IX|IV|V?I{0,3})"
EMAIL = re.compile(r"[\w.+'-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"\(?\b\d{3}\)?[ .-]\d{3}-\d{4}\b")
ROLE_WORDS = r"(?:Board )?(?:President|Vice President|Chair|Vice Chair|Chairperson|Vice Chairperson)"


def dnum(token):
    token = token.strip().upper()
    if token.isdigit():
        return int(token)
    return ROMAN.get(token)


def _mailto(m):
    """A mailto link as its text then its address, or the address once when the
    text IS the address (NWICC's links are the trustee's name, Hawkeye's read
    "Email Barbara McGregor", DMACC's are the address itself)."""
    addr = html.unescape(m.group(1)).strip()
    text = html.unescape(re.sub(r"<[^>]*>", " ", m.group(2))).strip()
    if text.lower() == addr.lower():
        return "\n%s\n" % addr
    return "\n%s\n%s\n" % (text, addr)


def page_lines(raw):
    """The page's visible text, one line per block, with each mailto: address
    written into the text where its link stood (Hawkeye's links read "Email
    Barbara McGregor" and the address is only in the href)."""
    b = re.sub(r"(?s)<!--.*?-->", " ", raw)
    b = re.sub(r"(?is)<(script|style|noscript|svg|head)\b.*?</\1>", " ", b)
    b = re.sub(r'(?is)<a\b[^>]*href="mailto:([^"?]+)[^"]*"[^>]*>(.*?)</a>',
               _mailto, b)
    b = re.sub(r"(?i)<br\s*/?>|</(?:p|div|li|h\d|tr|td|th|dt|dd|section|article)>", "\n", b)
    b = re.sub(r"(?i)(<(?:p|div|li|h\d|tr|dt|dd)\b)", "\n\\1", b)
    t = html.unescape(re.sub(r"<[^>]*>", " ", b))
    out = []
    for line in t.split("\n"):
        line = re.sub(r"[ \t\xa0​]+", " ", line).strip()
        if line:
            out.append(line)
    return out


def clean_name(s):
    s = re.sub(r"^(Mr|Mrs|Ms|Miss|Dr)\.?\s+", lambda m: "Dr. " if m.group(1) == "Dr" else "", s.strip())
    return re.sub(r"\s+", " ", s).strip(" ,")


def split_role(s):
    """'Kevin Halterman (President)' / 'Linnea Fletcher, President' -> name, role."""
    m = re.match(r"^(.*?)\s*\((%s)\)\s*$" % ROLE_WORDS, s)
    if not m:
        m = re.match(r"^(.*?)\s*,\s*(%s)\s*$" % ROLE_WORDS, s)
    if m:
        return clean_name(m.group(1)), m.group(2).replace("Board ", "")
    return clean_name(s), None


def rec(name, role=None, email=None, phone=None, term=None):
    r = {"name": name}
    if role:
        r["role"] = role
    if email:
        r["email"] = email
    if phone:
        r["phone"] = phone
    if term:
        r["termEnds"] = term
    return r


# ---- per-college parsers: lines -> {district number: record} ----------------

def p_niacc(lines):
    out = {}
    for i, line in enumerate(lines):
        m = re.match(r"^District %s:" % DNUM, line)
        if not m:
            continue
        # entry above: name, [role], occupation, town, Term: yyyy-yyyy
        j = i - 1
        term = None
        while j >= 0 and not lines[j].startswith("Term:"):
            j -= 1
        tm = re.match(r"Term:\s*\d{4}\s*-\s*(\d{4})", lines[j])
        term = tm.group(1) if tm else None
        k = j - 1
        block = []
        while k >= 0 and not re.match(r"^(District %s:|Includes|District Map)" % DNUM, lines[k]):
            block.insert(0, lines[k])
            k -= 1
        role = None
        for b in block[1:]:
            rm = re.match(r"^Board (Vice President|President)$", b)
            if rm:
                role = rm.group(1)
        out[dnum(m.group(1))] = rec(clean_name(block[0]), role, term=term)
    return out


def p_iowa_lakes_profile(lines):
    for line in lines:
        m = re.match(r"^(Trustee|President|Vice President|Secretary|Treasurer) District (\d)\s*$", line)
        if m:
            return int(m.group(2)), (None if m.group(1) == "Trustee" else m.group(1))
    return None, None


def p_nwicc(lines):
    out = {}
    for i, line in enumerate(lines):
        m = re.match(r"^District %s$" % DNUM, line)
        if m and i + 1 < len(lines):
            name, role = split_role(lines[i + 1])
            email = lines[i + 2] if i + 2 < len(lines) and EMAIL.fullmatch(lines[i + 2]) else None
            out[dnum(m.group(1))] = rec(name, role, email)
    return out


def p_iowa_central(lines):
    out = {}
    for i, line in enumerate(lines):
        m = re.match(r"^District (\d)$", line)
        if not m:
            continue
        name_i = i - 1
        role = None
        if re.match(r"^(Vice President|President)$", lines[name_i]):
            role = lines[name_i]
            name_i -= 1
        email = None
        for nxt in lines[i + 1:i + 3]:
            if re.match(r"^District \d$", nxt) or re.match(r"^(Mr|Mrs|Ms|Dr)\.? ", nxt):
                break
            em = EMAIL.search(nxt)
            if em:
                email = em.group(0)
        out[int(m.group(1))] = rec(clean_name(lines[name_i]), role, email)
    return out


def p_iowa_valley(lines):
    out = {}
    for i, line in enumerate(lines):
        m = re.match(r"^Director District %s\b(?:\s*[—-]\s*Board (Vice President|President))?" % DNUM, line)
        if m and i > 0:
            out[dnum(m.group(1))] = rec(clean_name(lines[i - 1]), m.group(2))
    return out


def p_hawkeye(lines):
    out = {}
    starts = [i for i, l in enumerate(lines) if re.match(r"^District %s: " % DNUM, l)]
    for n, i in enumerate(starts):
        m = re.match(r"^District %s: (.+)$" % DNUM, lines[i])
        end = starts[n + 1] if n + 1 < len(starts) else i + 12
        block = lines[i + 1:end]
        email = phone = term = None
        for b in block:
            if b.startswith("Student Representative"):
                break
            if PHONE.fullmatch(b):
                phone = b
            em = EMAIL.fullmatch(b)
            if em:
                email = em.group(0)
            tm = re.match(r"^Term Expires: \w+ (\d{4})$", b)
            if tm:
                term = tm.group(1)
        out[dnum(m.group(1))] = rec(clean_name(m.group(2)), email=email, phone=phone, term=term)
    return out


def p_eicc(lines):
    out = {}
    for i, line in enumerate(lines):
        m = re.match(r"^District %s$" % DNUM, line)
        if not m:
            continue
        # name, [obfuscated address], (town), District N, [Term Expires yyyy]
        j = i - 1
        if lines[j].startswith("("):
            j -= 1
        if "FREEEICC" in lines[j]:
            j -= 1
        term = None
        if i + 1 < len(lines):
            tm = re.match(r"^Term Expires (\d{4})$", lines[i + 1])
            term = tm.group(1) if tm else None
        name = clean_name(lines[j])
        out[dnum(m.group(1))] = {"vacant": True} if name == "Vacant" else rec(name, term=term)
    return out


def p_kirkwood(lines):
    out = {}
    for i, line in enumerate(lines):
        m = re.match(r"^District (\d)$", line)
        if m and i >= 2 and lines[i - 1].startswith("Elected:"):
            name, role = split_role(lines[i - 2])
            out[int(m.group(1))] = rec(name, role)
    return out


def p_dmacc(lines):
    out = {}
    for i, line in enumerate(lines):
        m = re.match(r"^District (\d) :", line)
        if not m:
            continue
        j = i - 1
        term = None
        tm = re.match(r"^Expires:? (\d{4})$", lines[j])
        if tm:
            term = tm.group(1)
            j -= 1
        email = None
        if EMAIL.fullmatch(lines[j]):
            email = lines[j]
            j -= 1
        name, role = split_role(lines[j])
        out[int(m.group(1))] = rec(name, role, email, term=term)
    return out


def p_witcc(lines):
    out = {}
    for i, line in enumerate(lines):
        m = re.match(r"^District %s$" % DNUM, line)
        if m and i + 1 < len(lines):
            name, role = split_role(lines[i + 1])
            email = lines[i + 2] if i + 2 < len(lines) and EMAIL.fullmatch(lines[i + 2]) else None
            out[dnum(m.group(1))] = rec(name, role, email)
    return out


def p_iwcc(lines):
    out = {}
    for i, line in enumerate(lines):
        m = re.match(r"^District %s$" % DNUM, line)
        if not m or i + 1 >= len(lines):
            continue
        role = None
        nxt = lines[i + 2] if i + 2 < len(lines) else ""
        rm = re.match(r"^(Board President|Vice President|President)\b", nxt)
        if rm:
            role = rm.group(1).replace("Board ", "")
        term = None
        for b in lines[i + 2:i + 7]:
            tm = re.search(r"Term Ends\s*[–-]\s*(\d{3})\s*(\d)", b)
            if tm:
                term = tm.group(1) + tm.group(2)
                break
        out[dnum(m.group(1))] = rec(clean_name(lines[i + 1]), role, term=term)
    return out


def p_swcc(lines):
    out = {}
    for i, line in enumerate(lines):
        m = re.match(r"^District (\d)$", line)
        if not m:
            continue
        # name, [role], town, District N
        name_i = i - 2
        role = None
        if re.match(r"^(Vice President|President)$", lines[name_i]):
            role = lines[name_i]
            name_i -= 1
        out[int(m.group(1))] = rec(clean_name(lines[name_i]), role)
    return out


def p_indian_hills(lines):
    out = {}
    for line in lines:
        m = re.match(r"^(.+?)\s*,\s*(?:(Vice President|President)\s*,\s*)?[A-Z][a-z]+\s*\(District #(\d)\)$", line)
        if m:
            out[int(m.group(3))] = rec(clean_name(m.group(1)), m.group(2))
    return out


def p_southeastern(lines):
    out = {}
    for i, line in enumerate(lines):
        m = re.match(r"^(?:Board (Vice Chairperson|Chairperson)|Member)\s*-\s*Director District (\d)$", line)
        if not m:
            continue
        email = lines[i + 1] if i + 1 < len(lines) and EMAIL.fullmatch(lines[i + 1]) else None
        out[int(m.group(2))] = rec(clean_name(lines[i - 1]), m.group(1), email)
    return out


def p_nicc(lines):
    """No district numbers: a list of trustees, read for the record only."""
    out = []
    for i, line in enumerate(lines):
        if line.startswith("School District") and i >= 2:
            j = i - 1
            email = None
            if EMAIL.fullmatch(lines[j]):
                email = lines[j]
                j -= 1
            j -= 1  # the town line
            name, role = split_role(re.sub(r"\s+,", ",", lines[j]))
            out.append(rec(name, role, email))
    return out


PARSERS = {2: p_niacc, 4: p_nwicc, 5: p_iowa_central, 6: p_iowa_valley,
           7: p_hawkeye, 9: p_eicc, 10: p_kirkwood, 11: p_dmacc, 12: p_witcc,
           13: p_iwcc, 14: p_swcc, 15: p_indian_hills, 16: p_southeastern}


def fetch(url):
    require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT,
                        label="ia-cc-trustees")
    req = urllib.request.Request(url, headers=UA_HEADERS_ROSTER_BOT)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def scrape(get):
    colleges = {}
    for area, url in sorted(PAGES.items()):
        raw = get(url)
        lines = page_lines(raw)
        if area == 1:
            colleges[str(area)] = {"sourceUrl": url, "undistricted": p_nicc(lines)}
            continue
        if area == 3:
            seats = {}
            for prof in sorted(set(IOWA_LAKES_PROFILE.findall(raw))):
                plines = page_lines(get(prof))
                d, role = p_iowa_lakes_profile(plines)
                name = plines[plines.index("Iowa Lakes Community College") - 1] \
                    if "Iowa Lakes Community College" in plines else None
                if d and name:
                    r = rec(clean_name(name), role)
                    r["profileUrl"] = prof
                    seats[d] = r
            colleges[str(area)] = {"sourceUrl": url, "seats": seats}
            continue
        colleges[str(area)] = {"sourceUrl": url, "seats": PARSERS[area](lines)}
        if area == 9:
            # never an e-mail from a page that obfuscates its addresses
            for r in colleges[str(area)]["seats"].values():
                r.pop("email", None)
    for c in colleges.values():
        if "seats" in c:
            c["seats"] = {str(k): v for k, v in sorted(c["seats"].items())}
    return colleges


def cache_getter(directory):
    """Read pages saved earlier by --save-cache, keyed by the url's own text."""
    def get(url):
        with open(os.path.join(directory, re.sub(r"[^A-Za-z0-9]+", "_", url) + ".html")) as f:
            return f.read()
    return get


def selftest():
    sample = ('<div>District I: Barbara A. McGregor<br>2920 280th St.<br>Charles City, IA 50616'
              '<br>641-435-2454 <br><a href="mailto:x@example.com">Email Barbara</a><br>'
              'Spouse: David<br>Term Expires: November 2027</div>'
              '<div>District II: Jay Nardini<br>5414 Blue Bonnet Drive<br>Term Expires: November 2029</div>')
    got = p_hawkeye(page_lines(sample))
    assert got[1] == {"name": "Barbara A. McGregor", "email": "x@example.com",
                      "phone": "641-435-2454", "termEnds": "2027"}, got
    assert "2920" not in json.dumps(got) and "Blue Bonnet" not in json.dumps(got), got
    assert page_lines("<p>a<!-- hidden@x.com --></p>") == ["a"]
    assert split_role("Kevin Halterman (President)") == ("Kevin Halterman", "President")
    assert split_role("Linnea Fletcher, President") == ("Linnea Fletcher", "President")
    assert clean_name("Mrs. Kati Lemberg") == "Kati Lemberg"
    assert clean_name("Dr. John Marshall") == "Dr. John Marshall"
    assert p_indian_hills(["Katie Nichols, Vice President, Keosauqua (District #9)",
                           "Beth Danowsky , Sigourney (District #1)"]) == {
        9: {"name": "Katie Nichols", "role": "Vice President"}, 1: {"name": "Beth Danowsky"}}
    assert p_eicc(["Vacant", "(Davenport)", "District I", "Jo Smith", "jsmith9FREEEICC",
                   "(Clinton)", "District V", "Term Expires 2027"]) == {
        1: {"vacant": True}, 5: {"name": "Jo Smith", "termEnds": "2027"}}
    print("ia-cc-trustee-scraper: selftest OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_PATH)
    ap.add_argument("--from-cache")
    ap.add_argument("--save-cache")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    get = cache_getter(a.from_cache) if a.from_cache else fetch
    if a.save_cache:
        inner = get

        def get(url):  # noqa: F811
            body = inner(url)
            os.makedirs(a.save_cache, exist_ok=True)
            with open(os.path.join(a.save_cache, re.sub(r"[^A-Za-z0-9]+", "_", url) + ".html"), "w") as f:
                f.write(body)
            return body
    colleges = scrape(get)
    for area, c in sorted(colleges.items(), key=lambda kv: int(kv[0])):
        print("ia-cc-trustees: area %s: %s" % (area, (
            "%d seats" % len(c["seats"])) if "seats" in c else "%d undistricted" % len(c["undistricted"])),
            file=sys.stderr)
    text = json.dumps({"colleges": colleges}, indent=1, ensure_ascii=False)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as f:
        f.write(text + "\n")
    print("ia-cc-trustees: wrote %s" % a.out, file=sys.stderr)


if __name__ == "__main__":
    main()
