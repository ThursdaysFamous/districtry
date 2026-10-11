"""Shared parsing helpers for the Tennessee commission parsers (stdlib only).

Every county module in this package imports from here and nothing else, so a
parser can be read, tested and changed without the network: it is handed the
pages tn_commissioner_scraper.py fetched and returns what they say."""
import html as _html
import re

ORDINAL_WORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
                 "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
                 "eleventh": 11, "twelfth": 12, "thirteenth": 13,
                 "fourteenth": 14, "fifteenth": 15, "sixteenth": 16,
                 "seventeenth": 17, "eighteenth": 18, "nineteenth": 19,
                 "twentieth": 20}
WORD_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
                "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
                "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15}


def strip_comments(h):
    """Remove HTML comments: a commented-out phone is one the county took down."""
    return re.sub(r"<!--.*?-->", "", h, flags=re.S)


def txt(fragment):
    """Visible text of an HTML fragment, whitespace collapsed."""
    s = re.sub(r"<(script|style)\b.*?</\1>", " ", fragment, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", _html.unescape(s)).strip()


def lines(page):
    """The page's visible text as a list of non-empty lines (block tags break)."""
    s = re.sub(r"<(script|style|noscript)\b.*?</\1>", "\n", page, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>|</?(p|div|li|tr|td|th|h[1-6]|section|article|ul|ol|table|header|footer|span|a|strong|b)\b[^>]*>",
               "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = _html.unescape(s)
    return [re.sub(r"\s+", " ", l).strip() for l in s.split("\n") if l.strip()]


def cf_decode(hexstr):
    """Decode a Cloudflare-obfuscated e-mail (data-cfemail / #hex)."""
    key = int(hexstr[:2], 16)
    return "".join(chr(int(hexstr[i:i + 2], 16) ^ key) for i in range(2, len(hexstr), 2))


def mailtos(fragment):
    """Every e-mail address in a fragment: mailto: links and Cloudflare-
    obfuscated ones, decoded. Order preserved, duplicates dropped."""
    out = []
    for m in re.finditer(r'mailto:\s*(?:%20)*([^"\'?>\s]+)', fragment, re.I):
        out.append(_html.unescape(m.group(1)).strip())
    for m in re.finditer(r'(?:data-cfemail="|/cdn-cgi/l/email-protection#)([0-9a-fA-F]{6,})', fragment):
        out.append(cf_decode(m.group(1)))
    seen, res = set(), []
    for e in out:
        if e.lower() not in seen:
            seen.add(e.lower())
            res.append(e)
    return res


def county_email(addresses, domains):
    """The first address on one of the county's own domains, else None.
    A personal gmail/bellsouth/business address is never returned."""
    for a in addresses:
        dom = a.rsplit("@", 1)[-1].lower() if "@" in a else ""
        if any(dom == d or dom.endswith("." + d) for d in domains):
            return a
    return None


def district_number(label):
    """1 from 'District 1', '1st District', 'First District', 'District One',
    'District I'? (no roman). None when the label carries no district."""
    m = re.search(r"\bDistrict\s*(?:#|No\.?)?\s*(\d{1,2})\b", label, re.I) \
        or re.search(r"\b(\d{1,2})(?:st|nd|rd|th)\s+(?:Commission\s+)?District\b", label, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(%s)\s+(?:Commission\s+)?District\b" % "|".join(ORDINAL_WORDS), label, re.I)
    if m:
        return ORDINAL_WORDS[m.group(1).lower()]
    m = re.search(r"\bDistrict\s+(%s)\b" % "|".join(WORD_NUMBERS), label, re.I)
    if m:
        return WORD_NUMBERS[m.group(1).lower()]
    return None


ROLE = re.compile(r"\b(Chair(?:man|woman|person)?(?:\s+Pro[- ]Tem(?:pore)?)?|"
                  r"Vice[- ]Chair(?:man|woman|person)?|Pro[- ]Tem(?:pore)?|"
                  r"Parliamentarian)\b", re.I)


def member(name, seat=None, role=None, email=None, phone=None, profileUrl=None):
    name = re.sub(r"\s+", " ", (name or "")).strip(" ,-–—")
    if not name:
        raise ValueError("empty name")
    out = {"name": name}
    for k, v in (("seat", seat), ("role", role), ("email", email),
                 ("phone", phone), ("profileUrl", profileUrl)):
        if v:
            out[k] = v
    return out


def vacant(seat=None):
    out = {"vacant": True}
    if seat:
        out["seat"] = seat
    return out
