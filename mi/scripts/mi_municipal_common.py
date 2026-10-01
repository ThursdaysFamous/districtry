#!/usr/bin/env python3
"""Shared helpers for the Michigan city and township board scrapers.

The unit tables and their parsers live in three sibling modules, one per batch
of units, so that each batch can be written and fixed without touching the
others:

    mi_municipal_parsers_cities_a.py   the larger cities
    mi_municipal_parsers_cities_b.py   the rest of the cities
    mi_municipal_parsers_townships.py  the townships

Each exports `UNITS`, a list of dicts:

    {
      "geoid": "2684000",            # Census place (7) or subdivision (10) id
      "name": "Warren",              # how the unit names itself, no "city"
      "kind": "city",                # "city" or "township"
      "body": "City Council",        # the body's own name for itself
      "url": "https://...",          # the page the roster is read from
      "also": ["https://..."],       # optional further pages, same host rules
      "seats": 7,                    # the members the page publishes, counted
      "parse": fn,                   # fn(html, also_htmls) -> Roster
    }

`seats` is a MEASUREMENT of the page made when the parser was written, never a
statutory figure, and the scraper refuses any run that returns another number.
A member leaving and not being replaced moves it; the page saying so is the
case `vacant` exists for.

A parser returns a dict:

    {
      "members": [ {"name", "role", "seat"?, "phone"?, "email"?}, ... ],
      "vacant":  [ "Ward 2" , ... ]          # optional: seats the page says are empty
      "office":  {"phone"?, "email"?}        # optional: the body's own shared line
    }

`role` is the office the page prints ("Mayor", "Council Member", "Trustee").
`seat` is where the page says the member was elected from ("Ward 2",
"District 3", "At Large"), and is left out when the page does not say: never
infer a ward from position on the page.

A parser RAISES ValueError when the page no longer has the shape it was written
for. Returning fewer people is worse than raising, because the count gate would
then read as "the council shrank".
"""

import html as _html
import re

# The fleet's own roster token (scripts/scraper_common.py's UA_ROSTER_BOT),
# copied rather than imported for the reason mi_commissioner_scraper.py gives:
# instance scripts resolve imports inside their own tree.
UA_ROSTER_BOT = "districtry.com roster bot (civic data; contact via site)"

ZERO_WIDTH = re.compile("[​‌‍⁠﻿]")


def strip_comments(h):
    """Remove HTML comments, scripts and styles. A commented-out predecessor
    is the Ionia trap (mi_commissioner_scraper.py)."""
    h = re.sub(r"<!--.*?-->", " ", h or "", flags=re.S)
    h = re.sub(r"<script\b.*?</script>", " ", h, flags=re.S | re.I)
    return re.sub(r"<style\b.*?</style>", " ", h, flags=re.S | re.I)


def txt(s):
    """Visible text of an HTML fragment: tags out, entities decoded, zero-width
    characters removed (Ann Arbor prints one inside a member's name) and runs
    of whitespace collapsed (several CivicPlus sites print double spaces)."""
    s = re.sub(r"<br\s*/?>", " ", s or "", flags=re.I)
    s = _html.unescape(re.sub(r"<[^>]+>", " ", s))
    s = ZERO_WIDTH.sub("", s).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def cf_decode(hexstr):
    """Decode a Cloudflare-obfuscated address (data-cfemail, or the hex after
    /cdn-cgi/l/email-protection#): the first byte is the XOR key."""
    try:
        key = int(hexstr[:2], 16)
        out = "".join(chr(int(hexstr[i:i + 2], 16) ^ key)
                      for i in range(2, len(hexstr), 2))
    except (ValueError, IndexError):
        return None
    return out if "@" in out else None


def emails_in(fragment):
    """Every address in an HTML fragment, in order, de-duplicated: mailto
    hrefs, both Cloudflare spellings, and plain text. Lower-cased."""
    found = []
    for m in re.finditer(r'mailto:([^"\'?>\s]+)', fragment or "", re.I):
        found.append(_html.unescape(m.group(1)))
    for m in re.finditer(r'data-cfemail="([0-9a-fA-F]+)"', fragment or ""):
        found.append(cf_decode(m.group(1)))
    for m in re.finditer(r'email-protection#([0-9a-fA-F]+)', fragment or ""):
        found.append(cf_decode(m.group(1)))
    for m in re.finditer(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                         txt(fragment)):
        found.append(m.group(0))
    out = []
    for e in found:
        if not e:
            continue
        e = e.strip().strip(".").lower()
        if e not in out:
            out.append(e)
    return out


def phone(raw):
    """A US number as ###-###-####, keeping an extension as ` ext. N`; None
    when the digits are not a phone number."""
    raw = raw or ""
    ext = None
    m = re.search(r"(?:ext\.?|extension|x)\s*(\d{1,6})\s*$", raw, re.I)
    if m:
        ext = m.group(1)
        raw = raw[:m.start()]
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None
    out = "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])
    return out + (" ext. " + ext if ext else "")


PHONE_RE = re.compile(r"\(?\b\d{3}\)?[\s.\-]*\d{3}[\s.\-]\d{4}(?:\s*(?:ext\.?|x)\s*\d{1,6})?",
                      re.I)


def phones_in(fragment):
    """Every phone number in a fragment's visible text and tel: hrefs, in
    order, normalised, de-duplicated."""
    out = []
    for m in re.finditer(r'tel:([^"\'>]+)', fragment or "", re.I):
        p = phone(_html.unescape(m.group(1)))
        if p and p not in out:
            out.append(p)
    for m in PHONE_RE.finditer(txt(fragment)):
        p = phone(m.group(0))
        if p and p not in out:
            out.append(p)
    return out


def member(name, role, seat=None, phone_=None, email=None):
    """One member record with absent fields left out."""
    rec = {"name": txt(name), "role": txt(role)}
    if seat:
        rec["seat"] = txt(seat)
    if phone_:
        rec["phone"] = phone_
    if email:
        rec["email"] = email.lower()
    return rec


NAME_OK = re.compile(r"^[A-Z][A-Za-z.'’\- ]+(?:,? (?:Jr|Sr|II|III|IV)\.?)?$")


def check_roster(unit, roster):
    """The gates every unit passes before its roster is kept. Raises
    ValueError naming the first thing wrong."""
    if not isinstance(roster, dict) or not isinstance(roster.get("members"), list):
        raise ValueError("parser returned %r, not a roster dict" % type(roster).__name__)
    members = roster["members"]
    vacant = roster.get("vacant") or []
    total = len(members) + len(vacant)
    if total != unit["seats"]:
        raise ValueError("%d members + %d vacant seats where the page published %d"
                         % (len(members), len(vacant), unit["seats"]))
    seen = set()
    for m in members:
        name = m.get("name") or ""
        if not NAME_OK.match(name) or len(name.split()) < 2 or len(name) > 60:
            raise ValueError("%r does not read as a person's name" % name)
        key = re.sub(r"[^a-z]", "", name.lower())
        if key in seen:
            raise ValueError("%r appears twice" % name)
        seen.add(key)
        if not m.get("role"):
            raise ValueError("%r has no role" % name)
        for e in [m.get("email")] if m.get("email") else []:
            if not re.match(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$", e):
                raise ValueError("%r carries a malformed address %r" % (name, e))
    return roster
