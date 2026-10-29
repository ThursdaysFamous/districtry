"""Shared parsing helpers for the Tennessee commission parsers (stdlib only).

Every county module in this package imports from here and nothing else, so a
parser can be read, tested and changed without the network: it is handed the
pages tn_commissioner_scraper.py fetched and returns what they say."""
import html as _html
import re
from urllib.parse import unquote

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
        out.append(cf_decode(m.group(1)).strip())
    seen, res = set(), []
    for e in out:
        if e.lower() not in seen:
            seen.add(e.lower())
            res.append(e)
    return res


# ——— e-mail addresses ———
#
# Adam chose on 2026-10-17, for every state, that a personal e-mail address a
# government page prints beside an official is shown ("E-mails too"). So an
# address a county's own page prints in a member's own block ships on that
# member, whatever its domain: a county mailbox, a gmail or a business address
# alike. Until that day an address shipped only on the county's own domains.
# What stays out is a question of whose address it is, never of privacy:
#
#   - an address printed for two or more members, which is the office's, and
#     one that carries another member's surname and not this member's, a block
#     welded to its neighbour's (settle_emails);
#   - an address whose link and printed text disagree, or a county mailbox
#     that names somebody else, where a parser can see either (each module
#     says which checks it makes);
#   - a county mailbox named for an office rather than a person (info@,
#     mayor@, commission@ and the rest of OFFICE_MAILBOXES; a business's
#     info@ printed as a member's own is that member's), and an address whose
#     domain runs the county's own into more letters
#     ("...@maurycounty-tn.govgmail.com"), a typing slip no mail reaches
#     (member_email);
#   - anything that is not one address (EMAIL_SHAPE), and an address the
#     fleet's undeliverable list withholds (the builder).

EMAIL_SHAPE = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
OFFICE_MAILBOXES = {"info", "webmaster", "contact", "admin", "office", "mayor",
                    "countymayor", "commission", "commissioners", "countycommission",
                    "countycommissioners", "clerk", "countyclerk", "publicrecords",
                    "help", "support", "noreply"}


def on_domains(address, domains):
    """True when an address is on one of the county's own domains."""
    dom = address.rsplit("@", 1)[-1].lower() if "@" in address else ""
    return any(dom == d or dom.endswith("." + d) for d in domains)


def misprinted(address, domains):
    """True when an address's domain runs one of the county's domains into more
    letters ("maurycounty-tn.govgmail.com"): a typing slip, never a mailbox."""
    dom = address.rsplit("@", 1)[-1].lower() if "@" in address else ""
    return not on_domains(address, domains) and any(dom.startswith(d) for d in domains)


def office_mailbox(address):
    """True when an address is named for an office (info@, mayor@), not a person."""
    return re.sub(r"[^a-z]", "", address.split("@", 1)[0].lower()) in OFFICE_MAILBOXES


def county_email(addresses, domains):
    """The first address on one of the county's own domains, else None."""
    for a in addresses:
        if on_domains(a, domains):
            return a
    return None


def member_email(addresses, domains):
    """The address to record from those one member's own block prints, in the
    page's order: the county's, where the block prints one, because a record
    carries one address and the county's mailbox is the office's own channel;
    otherwise the first address the block prints, whatever its domain. A
    county office's mailbox is never a member's and is passed over. None when the
    block prints none; a Withheld reason (read_emails) passes through for
    member() to turn into a note, and one is given when the only address
    printed is a misprinted county address."""
    if isinstance(addresses, Withheld):
        return addresses
    good = [a.strip() for a in addresses if a and EMAIL_SHAPE.fullmatch(a.strip())]
    good = [a for a in good if not (office_mailbox(a) and on_domains(a, domains))]
    slips = [a for a in good if misprinted(a, domains)]
    good = [a for a in good if not misprinted(a, domains)]
    pick = county_email(good, domains) or (good[0] if good else None)
    if pick is None and slips:
        return Withheld("the only address printed runs the county's domain into another")
    return pick


def other_email(fragment, domains):
    """For a county that keeps a county address only when it names the
    member: the address on another domain that the member's own block prints,
    for when the block prints no county one (member_email chooses), None when
    it prints none, or a Withheld reason (read_emails)."""
    got = read_emails(fragment)
    if isinstance(got, Withheld):
        return got
    return member_email([a for a in got if not on_domains(a, domains)], domains)


MAILTO_A = re.compile(r'<a\b([^>]*)>(.*?)</a>', re.S | re.I)
MAILTO_HREF = re.compile(r'\bhref\s*=\s*["\']\s*mailto:([^"\'?]*)', re.I)
CF_HIDDEN = re.compile(r'(?:data-cfemail="|/cdn-cgi/l/email-protection#)([0-9a-fA-F]{6,})')


def address_of(raw):
    """One address as a link or a text gives it: percent and entity escapes
    undone, a doubled "mailto:" prefix ("mailto:mailto%20x@...") dropped, and
    spaces and zero-width characters gone."""
    s = unquote(_html.unescape(raw or ""))
    s = re.sub(r"^\s*(?:mailto(?::|\s)+)+", "", s, flags=re.I)
    return re.sub(r"[\s\u200b\u200c\u200d\u2060\ufeff]+", "", s).strip(".,;:")


def read_emails(fragment):
    """The e-mail addresses one member's block prints, in the page's order:
    each mailto link's, each Cloudflare-hidden one decoded, and each written in
    its text, the same address twice (case-blind) once. A link whose own text
    is an address other than the one it opens answers Withheld, because the
    page does not say which of the two is the member's."""
    body = re.sub(r"<(script|style)\b.*?</\1>", " ", fragment, flags=re.S | re.I)
    found = []
    for m in MAILTO_A.finditer(body):
        href = MAILTO_HREF.search(m.group(1))
        if not href:
            continue
        opens = address_of(href.group(1))
        shown = [address_of(a) for a in EMAIL_SHAPE.findall(txt(m.group(2)))]
        if opens and any(a.lower() != opens.lower() for a in shown):
            return Withheld("a link prints one e-mail address and opens another")
        found.append((m.start(), opens))
    for m in CF_HIDDEN.finditer(body):
        found.append((m.start(), cf_decode(m.group(1))))
    for m in re.finditer(r"(?:^|>)([^<]+)", body):
        for a in EMAIL_SHAPE.finditer(_html.unescape(m.group(1))):
            found.append((m.start(1) + a.start(), address_of(a.group(0))))
    seen, out = set(), []
    for _, a in sorted(found, key=lambda x: x[0]):
        if a and EMAIL_SHAPE.fullmatch(a) and a.lower() not in seen:
            seen.add(a.lower())
            out.append(a)
    return out


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


# ——— telephone numbers ———
#
# Adam's ruling of 2026-10-17, for every state: "if the official government
# source uses personal phone numbers, we publish those." So a number a county's
# own page prints beside a member ships on that member's record, whosever line
# it is, with the page's own label kept in front of it ("cell 931-555-0100";
# a one-letter "C:" or "(c)" is written out as the word). The first number is
# `phone`, any further ones `phonesExtra`, in the page's order. What stays out:
#
#   - a number labelled as a fax, and every number of that person printed both
#     as a fax and as something else (one line cannot be both);
#   - every number of a member whose tel: link dials something other than the
#     number printed beside it, because the page then says two different
#     things and nothing here can tell which one is meant;
#   - a number printed for two or more members, or that is one of the module's
#     OFFICE_LINES (the county's, the commission's or the mayor's own line):
#     it belongs to the office, not the person (settle_phones);
#   - anything that is not a telephone number. No parser reads an address, a
#     town or a ZIP code, and a number is never given an area code the page
#     does not print: a mobile can be issued anywhere, and a guessed prefix
#     reaches a stranger.

# A number as a page prints it: an optional area code, written "(931) ",
# "(931)-", "931-", "931.", "931/" or "931) " (a page that dropped the opening
# parenthesis), then the exchange and the line, and an optional extension; or
# an area code in parentheses with the exchange and the line parted by a space
# alone ("(931) 555 0100", the shape of Montgomery County's District 6 number
# on 2026-10-17).
# The lookbehind keeps a run of digits inside a longer number, a ZIP+4 or a
# word from being read as a number of its own.
NUMBER = re.compile(
    r"(?<![\w(.\-])"
    r"(?:(?:\(\d{3}\)\s*[-.]?\s*|\d{3}\)\s*|\d{3}\s*[-./]\s*)?"
    r"\d{3}\s*[-.]\s*\d{4}"
    r"|\(\d{3}\)\s*\d{3}\s\d{4})"
    r"(?:\s*(?:ext\.?|x)\s*\d{1,6})?"
    r"(?![\w\-])", re.I)
# The page's own words for a line, and how each is written here; "Phone",
# "Tel" and the like name no kind of line, so they add nothing.
LABEL_WORDS = {"cell": "cell", "cellular": "cell", "mobile": "mobile",
               "home": "home", "work": "work", "business": "business",
               "office": "office", "personal": "personal", "residence": "residence",
               "fax": "fax"}
LABEL_LETTERS = {"c": "cell", "h": "home", "w": "work", "b": "business", "o": "office",
                 "f": "fax"}
NOT_LABELS = ("phone number", "telephone", "phone", "tel", "ph", "number")
_WORD = r"(?:%s)(?:\s+phone)?" % "|".join(sorted(LABEL_WORDS, key=len, reverse=True))
_NOISE = r"(?:%s)" % "|".join(NOT_LABELS)
# One token of the text around the numbers: a label word (with "phone" after
# it, as in "Cell Phone"), a one-letter label in parentheses or before a
# colon, a word that names no kind of line, or a separator.
_TOKEN = re.compile(
    r"(?P<word>\(\s*%s\s*\)|\b%s\b)(?P<wcolon>\s*:)?"
    r"|(?P<letter>\(\s*[CHWBOF]\s*\)|\b[CHWBOF]\s*(?=:))(?P<lcolon>\s*:)?"
    r"|(?P<noise>\b%s\b\s*:?)"
    r"|(?P<sep>[\s|/,;:•·&#–—-]+|\bor\b|\band\b)" % (_WORD, _WORD, _NOISE), re.I)


class Withheld(str):
    """Why a member's printed numbers are not kept; never a number itself."""


def _phone_text(fragment):
    """The visible text of a fragment, one line per block element, with the
    inline tags removed outright so "(423)-<a ...>555-0100</a>" reads as one
    number. A line break in the HTML source is not one on the page, so the
    source's own whitespace is collapsed first ("(731) 555-0100" and "Cell" on
    two source lines are one line on the page). Zero-width characters, which
    some pages put after a number, go."""
    s = re.sub(r"<(script|style|noscript)\b.*?</\1>", " ", fragment, flags=re.S | re.I)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"<br\b[^>]*>|</?(p|div|li|tr|td|th|h[1-6]|ul|ol|table|section|article)\b[^>]*>",
               "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = _html.unescape(s).replace("​", "").replace("﻿", "").replace("\xa0", " ")
    return [re.sub(r"\s+", " ", l).strip() for l in s.split("\n") if l.strip()]


def phone_digits(value):
    """The dialled digits of a number as printed (its extension and a leading
    country code 1 dropped), used only to compare two numbers."""
    value = re.split(r"(?i)\s*(?:ext\.?|x)\s*\d", value)[0]
    d = re.sub(r"\D", "", value)
    return d[1:] if len(d) == 11 and d.startswith("1") else d


def same_number(a, b):
    """Two printed numbers are one line when their digits agree, or when one
    is printed without its area code and its seven digits end the other."""
    da, db = phone_digits(a), phone_digits(b)
    if da == db:
        return True
    short, long_ = sorted((da, db), key=len)
    return len(short) == 7 and len(long_) == 10 and long_.endswith(short)


TEL_LINK = re.compile(r'<a\b[^>]*\bhref\s*=\s*["\']tel:([^"\']*)["\'][^>]*>(.*?)</a>', re.S | re.I)


def tel_disagrees(fragment):
    """True when a tel: link in the fragment dials a number other than the
    one printed: its own text when that text is a number (or the last seven
    digits of one, with the area code printed just outside the link), and
    otherwise the numbers printed beside it, as for a link around an icon."""
    printed = [m.group(0) for l in _phone_text(fragment) for m in NUMBER.finditer(l)]
    for m in TEL_LINK.finditer(fragment):
        dialled = phone_digits(unquote(_html.unescape(m.group(1))))
        if not dialled:
            continue
        own = re.sub(r"\D", "", " ".join(_phone_text(m.group(2))))
        if len(own) >= 7:
            if not same_number(dialled, own):
                return True
        elif printed and not any(same_number(dialled, p) for p in printed):
            return True
    return False


# A run of seven or more digits with the separators a number is printed with:
# in a phone field, one that is not a whole number is a number misprinted.
DIGIT_RUN = re.compile(r"\(?\d[\d()\s.\-]*\d")


def _label_of(tok):
    if tok.group("word"):
        w = re.sub(r"[()\s]+|phone$", " ", tok.group("word").lower()).split()[0]
        return LABEL_WORDS[w]
    return LABEL_LETTERS[re.sub(r"[()\s]", "", tok.group("letter")).lower()]


def read_phones(fragment, strict=False):
    """Every telephone number a member's fragment prints, in the page's order,
    each as printed with the page's own label written in front of it.

    A label BEFORE a number ("Cell: 931-...", "Home 901-...", "(C) 423-...")
    or AFTER one ("(731) 555-0100 (Cell)", "(615) 555-0100 - Cell") is that
    number's; a label followed by a colon always opens the number after it.
    A fax is never kept, nor any number the fragment also labels a fax. When a
    tel: link disagrees with the printed number, the answer is a Withheld
    reason instead of numbers.

    strict: the fragment is a phone field and nothing else, so text that is
    neither a number, a label nor a separator raises ValueError (without
    quoting it, since it may be an address), as does a label with no number;
    a run of digits that is not a whole number ("(865) 555-01005") is a
    misprint, and that member's numbers are Withheld rather than guessed at."""
    if tel_disagrees(fragment):
        return Withheld("its tel: link dials a number other than the one printed")
    if strict:
        for line in _phone_text(fragment):
            rest = NUMBER.sub(" ", line)
            if any(len(re.sub(r"\D", "", r)) >= 7 for r in DIGIT_RUN.findall(rest)):
                return Withheld("the page prints it in a form that is not a whole "
                                "telephone number")
    found = []                                  # [label or None, number as printed]
    for line in _phone_text(fragment):
        pos, pending, last = 0, None, None      # pending: a label waiting for a number
        spans = list(NUMBER.finditer(line))
        for m in spans + [None]:
            gap = line[pos:m.start() if m else len(line)]
            i = 0
            while i < len(gap):
                t = _TOKEN.match(gap, i)
                if not t or t.end() == i:
                    if strict:
                        raise ValueError("a phone field holds text that is neither a "
                                         "number nor a label")
                    pending = last = None       # unknown text breaks a label's pairing
                    i += 1
                    continue
                i = t.end()
                if not (t.group("word") or t.group("letter")):
                    continue
                label = _label_of(t)
                if t.group("wcolon") or t.group("lcolon") or last is None or last[0]:
                    pending = label             # "Cell: 931-...": opens the next number
                else:
                    last[0], last = label, None  # "931-... (Cell)": closes the one before
            if m is None:
                break
            entry = [pending, m.group(0).strip()]
            found.append(entry)
            pending, last, pos = None, entry, m.end()
        if pending is not None and strict:
            raise ValueError("a phone label with no number after it")
    faxes = [n for label, n in found if label == "fax"]
    out, seen = [], []
    for label, number in found:
        if label == "fax" or any(same_number(number, f) for f in faxes):
            continue
        if any(same_number(number, s) for s in seen):
            continue
        seen.append(number)
        out.append("%s %s" % (label, number) if label else number)
    return out


def page_field(fragment):
    """read_phones(fragment, strict=True) for a phone field on a member's own
    page (a module's member_pages): text there that is neither a number nor a
    label leaves that one member without a number, with a note, instead of
    refusing the county, because the names come from the roster page and the
    member's page adds only the number."""
    try:
        return read_phones(fragment, strict=True)
    except ValueError as exc:
        return Withheld(str(exc))


def same_person(shown, name):
    """True when every word of a name a member's own page shows is a word of
    the name the roster gives ("Harrison Wexler" for "Harrison Wexler, Sr",
    "Jeremy H.G. Hayes" for "Jeremy H.G.Hayes"), letters only, any case."""
    words = lambda s: re.findall(r"[a-z]+", (s or "").lower())
    have = set(words(name))
    return bool(words(shown)) and all(w in have for w in words(shown))


def settle_phones(parsed, office_lines=()):
    """After a parse: leave out every number printed for two or more members
    or equal to one of the county's OFFICE_LINES, and turn each record's
    Withheld marker into a note. -> notes, one per member affected, naming the
    member and district and never a number."""
    rows = [("District %s" % d, r) for d in sorted(parsed.get("districts") or {}, key=int)
            for r in parsed["districts"][d]]
    rows += [("countywide", r) for r in parsed.get("atLarge") or []]
    notes = []
    for where, r in rows:
        why = r.pop("_withheld", None)
        if why:
            notes.append("%s, %s: no number kept - %s" % (where, r.get("name"), why))

    def numbers(r):
        return [x for x in [r.get("phone")] + list(r.get("phonesExtra") or []) if x]

    held = {id(r): numbers(r) for _, r in rows}
    for where, r in rows:
        keep = []
        for p in held[id(r)]:
            if any(same_number(p, o) for o in office_lines):
                notes.append("%s, %s: a number that is an office's own line is left out"
                             % (where, r.get("name")))
                continue
            others = sum(1 for _, o in rows if o is not r
                         and any(same_number(p, q) for q in held[id(o)]))
            if others:
                notes.append("%s, %s: a number the page also prints for %d other "
                             "member(s) is left out" % (where, r.get("name"), others))
                continue
            keep.append(p)
        r.pop("phone", None)
        r.pop("phonesExtra", None)
        if keep:
            r["phone"] = keep[0]
        if keep[1:]:
            r["phonesExtra"] = keep[1:]
    return notes


NAME_SUFFIXES = ("jr", "sr", "ii", "iii", "iv")


def surname_parts(name):
    """The letters of a member's surname, and of each half of a hyphenated
    one, three letters or more: "Mary Smith-Jones" -> {"smithjones", "smith",
    "jones"}. A suffix (Jr, Sr, III) is not the surname."""
    words = re.findall(r"[A-Za-z][A-Za-z'.-]*", name or "")
    while len(words) > 1 and words[-1].lower().strip(".") in NAME_SUFFIXES:
        words.pop()
    last = words[-1].lower() if words else ""
    parts = {re.sub(r"[^a-z]", "", p) for p in [last] + last.split("-")}
    return {p for p in parts if len(p) > 2}


def settle_emails(parsed):
    """After a parse: leave out every e-mail address printed for two or more
    members, which is the office's, and one whose local part carries another
    member's surname (four letters or more) and not this member's, which is a
    block welded to its neighbour's; and turn a parser's reason for reading no
    address (member() keeps it as _email_withheld) into a note. -> notes naming
    the member and district, never an address."""
    rows = [("District %s" % d, r) for d in sorted(parsed.get("districts") or {}, key=int)
            for r in parsed["districts"][d]]
    rows += [("countywide", r) for r in parsed.get("atLarge") or []]
    notes = []
    for where, r in rows:
        why = r.pop("_email_withheld", None)
        if why:
            notes.append("%s, %s: no e-mail address is kept: %s" % (where, r.get("name"), why))
    rows = [(w, r) for w, r in rows if r.get("name")]
    held = {id(r): (r.get("email") or "").strip().lower() for _, r in rows}
    for where, r in rows:
        mail = held[id(r)]
        if not mail:
            continue
        local = re.sub(r"[^a-z]", "", mail.split("@", 1)[0])
        others = sum(1 for _, o in rows if o is not r and held[id(o)] == mail)
        if others:
            notes.append("%s, %s: an e-mail address the page also prints for %d other "
                         "member(s) is left out" % (where, r.get("name"), others))
            r.pop("email", None)
            continue
        if any(p in local for p in surname_parts(r.get("name"))):
            continue
        if any(len(p) > 3 and p in local for _, o in rows if o is not r
               for p in surname_parts(o.get("name"))):
            notes.append("%s, %s: an e-mail address carrying another member's name is "
                         "left out" % (where, r.get("name")))
            r.pop("email", None)
    return notes


def member(name, seat=None, role=None, email=None, phone=None, profileUrl=None,
           phones=None):
    """One seat's record. `phones` is what read_phones returned: a list of
    numbers (the first becomes `phone`, the rest `phonesExtra`) or a Withheld
    reason, which settle_phones turns into a note; neither a reason nor the
    numbers behind it ever ships. `email` is one address or a Withheld reason
    (member_email), which settle_emails turns into a note the same way."""
    name = re.sub(r"\s+", " ", (name or "")).strip(" ,-–—")
    if not name:
        raise ValueError("empty name")
    out = {"name": name}
    if isinstance(phones, Withheld):
        out["_withheld"] = str(phones)
        phones = None
    if isinstance(email, Withheld):
        out["_email_withheld"] = str(email)
        email = None
    numbers = ([phone] if phone else []) + list(phones or [])
    for k, v in (("seat", seat), ("role", role), ("email", email),
                 ("phone", numbers[0] if numbers else None), ("profileUrl", profileUrl)):
        if v:
            out[k] = v
    if numbers[1:]:
        out["phonesExtra"] = numbers[1:]
    return out


def add_phones(record, phones):
    """A record member() already built, given what read_phones returned for
    it (numbers, or a Withheld reason); every other field passes through as
    it was. Used by the counties whose numbers sit on each member's own page
    (member_pages), which is read after the roster page has named them."""
    email = record.get("email")
    if record.get("_email_withheld"):
        email = Withheld(record["_email_withheld"])
    if record.get("_withheld") or isinstance(phones, Withheld):
        held = Withheld(record.get("_withheld") or phones)
        return member(record["name"], seat=record.get("seat"), role=record.get("role"),
                      email=email, profileUrl=record.get("profileUrl"), phones=held)
    numbers = ([record["phone"]] if record.get("phone") else []) + \
        list(record.get("phonesExtra") or []) + list(phones or [])
    return member(record["name"], seat=record.get("seat"), role=record.get("role"),
                  email=email, profileUrl=record.get("profileUrl"), phones=numbers)


def vacant(seat=None):
    out = {"vacant": True}
    if seat:
        out["seat"] = seat
    return out
