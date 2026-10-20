#!/usr/bin/env python3
"""Write il/data/app/il-library-trustees.json from the scraper's output.

The pair to il_library_trustees_scraper.py, which reads a board of trustees off
each library's own website for the cards no Annual Financial Report answers for.
This half does the refusing: a run that lost coverage leaves the shipped file
alone rather than replacing it with a thinner one.

TWO SOURCES MUST NEVER BOTH CLAIM ONE LIBRARY, and this is the guard. A
district-governed library's filing is the better source — it is a document the
library signed and filed with the State — so a library that starts filing leaves
the scraper's pool on the next run by itself; if one ever appears in both, that
is a pool defect and the build refuses rather than letting a card show two
boards or the app pick one silently. il/index.html stamps this file only where
the filing named no board, and validate_index.py fails on an overlap, so the
rule is enforced on both sides of the hand-off.

A KEY THAT NO CARD CAN REACH FAILS, the sibling builder's rule for the same
reason: the boundary layer's own spelling of a library's name is the join key, so
a library renamed upstream leaves a record here that nothing renders and no gate
would otherwise notice.

EVERY RECORD CARRIES THE PAGE IT WAS READ FROM AND THE DAY IT WAS READ. A
website is not a filing: it has no fiscal year, it can be months stale, and the
only honest thing a card can say is which page said this and when we looked. A
record without both is refused.

A FETCH THAT FAILED IS NOT A LIBRARY THAT STOPPED PUBLISHING, which is Adam's
ruling of 2026-09-19 — "Preserve data we have already fetched" — and here it is
load-bearing rather than a nicety. 176 small library hosts read over an hour is
a lot of chances to time out: Carbondale Public Library answered in one sweep
and timed out in the next, an hour apart, with nothing changed at either end.
A run that simply wrote what it got would drop that library's nine trustees off
the card and the retention gate would see a real loss. So a library the scrape
could not READ keeps its last-good record and its own older read stamp, and the
carried-forward count prints every run.

THE SPLIT IS BY WHAT THE VERDICT MEANS, not by whether the run succeeded. A
transport failure or a host that now refuses us carries forward: neither says
anything about what the page says, and a refusal tells us not to READ a host
rather than to unpublish what it already served. A page that LOADED and no
longer lists a board does not: that is the library having changed its site, the
real event check_roster_retention.py exists to notice, and carrying it forward
would publish trustees the library has taken down.

A TRUSTEE'S OWN TELEPHONE NUMBER AND E-MAIL ADDRESS SHIP ON THAT TRUSTEE, since
2026-10-17, where the library's own page prints them in that trustee's own
entry. That is the fleet's rule from that day: a number or an address a
government publisher prints beside one official ships on that official,
whosever line or mailbox it is. The scraper reports where the page printed each
value; whose it is is decided here, where the library's other publishers can
be seen too. A value ships on nobody where:

  * the page prints it beside two or more trustees, or another library's board
    here or one of the seven rosters built from Annual Financial Reports
    (comptroller_afr.AFR_ROSTERS) gives it beside somebody else. Gilman-
    Danforth and Groff print the library's telephone and one mailbox under
    every trustee, and those 32 values ship on nobody. Those rosters do not
    read this file in turn, so where one of them gives an address to a
    different person, it is taken off here and theirs stands;
  * the page also prints or links it outside the trustees' entries, as the
    board's mailbox above the list or the library's telephone in the footer;
  * it is the library's own line in the library systems' shared directory, or
    the office's or an administrator's in the library's own filing;
  * the part before the @ is made only of words naming an office or the
    library ("board", "trustee3", "info", the library's own name or initials),
    or names the library and not the trustee, or names another trustee and not
    this one;
  * the page links it to a different address or number than it prints. Morris
    prints two trustees' addresses one way and links them another, so which
    one is theirs is not settled and neither ships;
  * undeliverable.py lists it.

One address per trustee: where an entry prints more than one, one on the
library's own domain or a government domain is kept, else one carrying the
trustee's name, first in page order, and two one character apart ship as
neither. Every number left after those tests ships, as `phone` and then
`phonesExtra` in page order, with the label word the page printed, and two one
digit apart ship as neither.
A value not shaped like one number or one address (scraper_common's
person_phone_problem and person_email_problem) refuses the write, naming the
library and the trustee and never the value, and nothing this file prints names
a value either.

MEASURED ON THE LIVE READ OF 2026-10-17: five libraries print 55 values in
their trustees' entries. 21 addresses ship, on seven trustees at Centralia,
nine at Mascoutah and five at Morris, every one carrying the trustee's
surname; no telephone ships, because no library printed a trustee's own.
MIN_WITH_EMAIL floors the addresses at about two thirds of that.

Usage:
    python3 build_il_library_trustees.py <scraper-output.json> [--check]
    python3 build_il_library_trustees.py --selftest
"""

import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_common import (  # noqa: E402
    substantive_changes, emit_changes_output, person_email_problem,
    person_phone_problem)
from il_library_district_officials_scraper import (  # noqa: E402
    shipped_cards, statewide_library_counties)
from il_library_trustees_scraper import (  # noqa: E402
    MIN_MEMBERS, MAX_MEMBERS, host_of)
from comptroller_afr import (  # noqa: E402  (shared — do not fork)
    GOVERNMENT_DOMAIN, _flat, firm_address, library_directory_lines,
    line_digits, local_letters, mail_digest, mail_elsewhere, one_digit_apart,
    one_typo_apart, person_tokens, unit_tokens)
from undeliverable import UNDELIVERABLE  # noqa: E402  (the fleet's one list)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(REPO_ROOT, "il", "data", "app")
OUT_PATH = os.path.join(APP_DIR, "il-library-trustees.json")
FILINGS = os.path.join(APP_DIR, "il-library-district-officials.json")

SOURCE = "Each library's own website"

# MEASURED 2026-09-25 on the first full run: 53 libraries, 388 trustees, 233 of
# them with a role. Each floor sits about 17% under its value, because a library
# redesigning its site is a real event that must not freeze the other fifty-odd.
#
# TWO PASSES OVER THE SAME POOL AN HOUR APART AGREED ON 51 OF THEM, which is
# what makes these floors settable at all: the first read 54 and the second 53,
# three libraries lost to a transport failure and two gained that had failed one
# before. A floor set from a single pass would be a floor set from that pass's
# weather.
MIN_LIBRARIES = 44
MIN_TRUSTEES = 320
MIN_CARDS = 44
# A board page that names a role for nobody is a shape worth flooring on its
# own: the roles come from a different part of the page than the names, and a
# parse regression can lose every role while keeping every name.
MIN_WITH_ROLE = 180

# A verdict that says nothing about what the page says. The record is carried
# forward with its own older read stamp; see the docstring.
CARRY_FORWARD = ("site-unreachable", "board-page-unreachable",
                 "robots-unreadable", "robots-refused")

# Trustees carrying an e-mail address of their own. MEASURED on the live read of
# 2026-10-17 at 21 (see the docstring); the floor sits at about two thirds of
# it, so a run that stops reading the addresses fails rather than shipping none.
# There is no telephone floor, because no library printed a trustee's own.
MIN_WITH_EMAIL = 14

# Words a mailbox is named for when it belongs to an office and not a person.
# Compared on the letters before the @, longest first, together with the
# library's own name words: "trustee3" and "gdlibraryboard" are the library's.
OFFICE_WORDS = ("administration", "administrator", "information", "circulation",
                "secretary", "treasurer", "president", "reference", "librarian",
                "director", "trustees", "trustee", "library", "contact", "office",
                "admin", "board", "staff", "clerk", "chair", "vice", "info",
                "mail", "help", "desk", "ask", "lib", "the", "us")

# Why a value ships on nobody, as the build prints it: counted per library and
# reason, never with the value.
SHARED = "printed beside two or more people"
ON_PAGE = "printed or linked outside the trustees' entries too"
OFFICE_LINE = "the library's own line, or an administrator's in its filing"
OFFICE_MAIL = "the library's own address, or an administrator's in its filing"
MAILBOX = "an office's or the library's mailbox, by its name"
ANOTHER = "named for another trustee"
LINKED = "linked to a different value than the page prints"
DEAD = "listed in undeliverable.py"
TYPO = "two values for one trustee one character apart"
NOT_NAMED = "one of several for one trustee, and not the one kept"
FIRM = "an accountant's or a bank's address, naming nobody"


def fail(msg):
    sys.exit("build-il-library-trustees: FAIL — " + msg)


# ------------------------------------------------- a trustee's own contact ---

def office_mailbox(address, library):
    """Is the part of `address` before the @ made only of words naming an
    office or this library -- OFFICE_WORDS, the library's own name words or its
    initials? Whatever the trustee is called: "board@" is an office's mailbox
    beside a trustee whose surname is Board."""
    letters = local_letters(address)
    for word in sorted(set(OFFICE_WORDS) | unit_tokens(library), key=len,
                       reverse=True):
        letters = letters.replace(word, "")
    if not letters:
        return True
    initials = "".join(w[0] for w in re.findall(r"[a-z]+", library.lower()))
    rest = iter(initials)
    return 2 <= len(letters) and all(ch in rest for ch in letters)


def names_library_only(address, library, name):
    """Does the part before the @ carry a word of the library's own name and
    no piece of the trustee's (comptroller_afr's names_unit_only)?"""
    local = local_letters(address)
    return (any(t in local for t in unit_tokens(library))
            and not any(t in local for t in person_tokens(name)))


def names_another(address, name, board):
    """Does the part before the @ carry a piece of another trustee's name and
    no piece that is this trustee's alone? Two trustees sharing a surname
    decide nothing between them (comptroller_afr's names_another_filer)."""
    local = local_letters(address)
    mine = person_tokens(name)
    theirs = set()
    for other in board:
        if _flat(other) != _flat(name):
            theirs |= person_tokens(other)
    return (any(t in local for t in theirs - mine)
            and not any(t in local for t in mine - theirs))


def official(address, hosts):
    """Is `address` on the library's own domain or a government domain?"""
    domain = address.rsplit("@", 1)[-1].lower()
    return bool(GOVERNMENT_DOMAIN.search(domain) or any(
        domain == host or domain.endswith("." + host) for host in hosts if host))


def link_targets(links, scheme):
    """The values of the `scheme` links among `links`, one per address."""
    out = []
    for link in links or []:
        if link.lower().startswith(scheme):
            out.extend(part.strip() for part in re.split(r"[,;]", link[len(scheme):])
                       if part.strip())
    return out


def printed_values(member):
    """[(kind, value as printed, its links)] for one scraped trustee: each
    value once, an address compared without case and a number by its line,
    with the links of every printing of it."""
    out, seen = [], {}
    for found in member.get("contacts") or []:
        kind = found.get("kind")
        value = (found.get("value") or "").strip()
        if not value:
            continue
        key = (kind, value.casefold() if kind == "email" else line_digits(value))
        if key not in seen:
            seen[key] = len(out)
            out.append((kind, value, []))
        out[seen[key]][2].extend(found.get("links") or [])
    return out


def trustee_boards(reads, carried, context):
    """(boards, notes, problems) under the rules in the module docstring.

    `reads` is {library: the scraper's record} for every library this run read,
    and `carried` {library: the shipped entry} for every library it carries
    forward, whose values were decided on an earlier run and are tested again
    here only against the rest of the roster. `context` holds "directory"
    ({library: its telephone in the shared directory}), "filings" ({library:
    its record in il-library-district-officials.json}), "elsewhere"
    (comptroller_afr.mail_elsewhere's answer) and "undeliverable" (addresses).

    `boards` is {library: [trustee record]}, each record the name, the role
    where there is one, and the values that ship. `notes` counts what did not
    ship by (library, kind, reason) and `problems` names each value not shaped
    like one number or one address by library and trustee; neither carries a
    value.
    """
    notes, problems = collections.Counter(), []

    # EVERY VALUE PRINTED BESIDE EACH NAME, before any other test: whether a
    # value is printed for two people is a fact about the pages, not about
    # what survives the other tests.
    mail_holders, line_holders = {}, {}
    for library, record in reads.items():
        for member in record.get("board") or []:
            name = _flat(member.get("name"))
            for kind, value, _links in printed_values(member):
                if kind == "email":
                    mail_holders.setdefault(value.casefold(), set()).add(
                        mail_digest(name))
                else:
                    line_holders.setdefault(line_digits(value), set()).add(name)
    for library, entry in carried.items():
        for member in entry.get("board") or []:
            name = _flat(member.get("name"))
            if member.get("email"):
                mail_holders.setdefault(member["email"].casefold(), set()).add(
                    mail_digest(name))
            for number in [member.get("phone")] + list(member.get("phonesExtra") or []):
                if number:
                    line_holders.setdefault(line_digits(number), set()).add(name)

    def mail_shared(address):
        key = address.casefold()
        return len(mail_holders.get(key, set())
                   | context["elsewhere"].get(mail_digest(key), set())) > 1

    def line_shared(number):
        return len(line_holders.get(line_digits(number), set())) > 1

    def shape(library, position, name, member):
        for field in ("phone", "phonesExtra", "email"):
            values = member.get(field)
            for value in values if isinstance(values, list) else [values]:
                if value is None:
                    continue
                problem = (person_email_problem(value) if field == "email"
                           else person_phone_problem(value))
                if problem:
                    problems.append("%s, trustee %d (%s): the %s %s"
                                    % (library, position, name,
                                       "e-mail address" if field == "email"
                                       else "telephone number", problem))

    boards = {}
    for library, record in reads.items():
        page = record.get("pageContacts") or {}
        page_mail = {v.casefold() for v in page.get("email") or []}
        page_lines = {line_digits(v) for v in page.get("phone") or []}
        filing = context["filings"].get(library) or {}
        heads = [h for h in filing.get("heads") or [] if isinstance(h, dict)]
        office = filing.get("office") or {}
        office_mail = {v.casefold() for v in
                       [office.get("email")] + [h.get("email") for h in heads] if v}
        office_lines = {line_digits(v) for v in
                        [context["directory"].get(library), office.get("phone")]
                        + [h.get("phone") for h in heads]
                        + [p for h in heads for p in h.get("phonesExtra") or []] if v}
        hosts = {host_of(record.get("website") or ""),
                 host_of(record.get("boardUrl") or "")}
        members = [m for m in record.get("board") or [] if m.get("name")]
        names = [m["name"] for m in members]
        board = []
        for position, member in enumerate(members, 1):
            name = member["name"]
            out = {"name": name}
            if member.get("role"):
                out["role"] = member["role"]
            mails, lines = [], []
            for kind, value, links in printed_values(member):
                if kind == "email":
                    key = value.casefold()
                    if any(t.casefold() != key for t in link_targets(links, "mailto:")):
                        why = LINKED
                    elif key in context["undeliverable"]:
                        why = DEAD
                    elif mail_shared(value):
                        why = SHARED
                    elif key in page_mail:
                        why = ON_PAGE
                    elif key in office_mail:
                        why = OFFICE_MAIL
                    elif office_mailbox(value, library) \
                            or names_library_only(value, library, name):
                        why = MAILBOX
                    elif names_another(value, name, names):
                        why = ANOTHER
                    else:
                        mails.append(value)
                        continue
                    notes[(library, "e-mail address", why)] += 1
                elif kind == "phone":
                    digits = line_digits(value)
                    if any(line_digits(t) != digits
                           for t in link_targets(links, "tel:")):
                        why = LINKED
                    elif line_shared(value):
                        why = SHARED
                    elif digits in page_lines:
                        why = ON_PAGE
                    elif digits in office_lines:
                        why = OFFICE_LINE
                    else:
                        lines.append(value)
                        continue
                    notes[(library, "telephone number", why)] += 1
                else:
                    problems.append("%s, trustee %d (%s): a value of a kind this "
                                    "builder does not know" % (library, position, name))
            # Two numbers for one trustee one digit apart, or two addresses one
            # character apart: the page disagrees with itself, and one of each
            # pair would reach a stranger.
            clash = {i for i, a in enumerate(lines) for j, b in enumerate(lines)
                     if i != j and one_digit_apart(line_digits(a), line_digits(b))}
            if clash:
                notes[(library, "telephone number", TYPO)] += len(clash)
            lines = [v for i, v in enumerate(lines) if i not in clash]
            clash = {i for i, a in enumerate(mails) for j, b in enumerate(mails)
                     if i != j and one_typo_apart(a.casefold(), b.casefold())}
            if clash:
                notes[(library, "e-mail address", TYPO)] += len(clash)
            several = len(mails) > 1
            mails = [v for i, v in enumerate(mails) if i not in clash]
            mine = person_tokens(name)
            named = [v for v in mails if any(t in local_letters(v) for t in mine)]
            chosen = ([v for v in mails if official(v, hosts)] or named
                      or ([] if several else
                          [v for v in mails if not firm_address(v)]))
            if mails and not chosen:
                notes[(library, "e-mail address",
                       NOT_NAMED if several else FIRM)] += len(mails)
            elif len(mails) > 1:
                notes[(library, "e-mail address", NOT_NAMED)] += len(mails) - 1
            if lines:
                out["phone"] = lines[0]
            if len(lines) > 1:
                out["phonesExtra"] = lines[1:]
            if chosen:
                out["email"] = chosen[0]
            shape(library, position, name, out)
            board.append(out)
        boards[library] = board

    # A carried-forward record keeps what an earlier run decided, except that a
    # value the rest of the roster now also gives somebody else is nobody's.
    for library, entry in carried.items():
        board = []
        for position, member in enumerate(entry.get("board") or [], 1):
            out = {k: v for k, v in member.items()
                   if k not in ("phone", "phonesExtra", "email")}
            if member.get("email"):
                if mail_shared(member["email"]):
                    notes[(library, "e-mail address", SHARED)] += 1
                else:
                    out["email"] = member["email"]
            numbers = [n for n in [member.get("phone")]
                       + list(member.get("phonesExtra") or []) if n]
            kept = [n for n in numbers if not line_shared(n)]
            if len(kept) < len(numbers):
                notes[(library, "telephone number", SHARED)] += len(numbers) - len(kept)
            if kept:
                out["phone"] = kept[0]
            if len(kept) > 1:
                out["phonesExtra"] = kept[1:]
            shape(library, position, out.get("name"), out)
            board.append(out)
        boards[library] = board
    return boards, notes, problems


# --------------------------------------------------------------- selftest ---

def selftest():
    """trustee_boards over made-up libraries, one trustee per rule. Every name,
    number and address here is made up. Prints one line and returns the number
    of problems."""
    checks = problems = 0
    lib = "Orchard Public Library"
    context = {
        "directory": {lib: "(217) 555-0100"},
        "filings": {lib: {
            "office": {"email": "office@example.com", "phone": "217-555-0108"},
            "heads": [{"name": "Zed Omega", "role": "Director",
                       "email": "zomega@example.com", "phone": "217-555-0107"}]}},
        "elsewhere": {mail_digest("gus.eta@example.org"):
                      {mail_digest(_flat("Someone Else"))}},
        "undeliverable": {"hal.theta@example.invalid"},
    }

    def person(name, *values, **extra):
        out = {"name": name, "contacts": [
            dict(kind=v[0], value=v[1], **({"links": v[2]} if len(v) > 2 else {}))
            for v in values]}
        out.update(extra)
        return out

    reads = {
        lib: {
            "website": "https://www.orchardlibrary.example.com/",
            "boardUrl": "https://www.orchardlibrary.example.com/board",
            "pageContacts": {"email": ["board@orchardlibrary.example.com",
                                       "printed.twice@example.com"],
                             "phone": ["217-555-0109"]},
            "board": [
                # Every number, in page order with its label, and the address.
                person("Ann Alpha", ("phone", "cell 217-555-0101"),
                       ("phone", "home (217) 555-0123"),
                       ("email", "Ann.Alpha@example.com",
                        ["mailto:ann.alpha@example.com"]), role="President"),
                # An address naming nobody, printed beside one trustee.
                person("Bea Beta", ("email", "bookworm42@example.net")),
                # The directory's line; an address the page prints elsewhere.
                person("Cal Gamma", ("phone", "217.555.0100"),
                       ("email", "printed.twice@example.com")),
                # An office's mailbox, beside a trustee called Board; a number
                # the page prints outside the entries.
                person("Dee Board", ("email", "board1@example.com"),
                       ("phone", "217-555-0109")),
                # Printed one way and linked another.
                person("Eve Epsilon", ("email", "eepsilon@example.com",
                                       ["mailto:eepsilom@example.com"])),
                # Named for another trustee.
                person("Fay Zeta", ("email", "annalpha.home@example.com")),
                # Another roster gives it to somebody else; the administrator's
                # number in the library's filing.
                person("Gus Eta", ("email", "gus.eta@example.org"),
                       ("phone", "217-555-0107")),
                # Undeliverable; the library's own address in its filing.
                person("Hal Theta", ("email", "hal.theta@example.invalid"),
                       ("email", "office@example.com")),
                # A number linked to another.
                person("Ida Iota", ("phone", "217-555-0111", ["tel:+12175550112"])),
                # Two addresses: the one on the library's own domain is kept,
                # over one carrying his name.
                person("Jo Kappa", ("email", "jo.kappa@example.net"),
                       ("email", "jk@orchardlibrary.example.com")),
                # An address naming the library and not her.
                person("Lia Psi", ("email", "orchardfriends@example.com")),
            ]},
        # One telephone and one address under every trustee.
        "Beta Library": {"board": [
            person(n, ("phone", "217-555-0121"), ("email", "trustees.beta@example.com"))
            for n in ("Kit Lambda", "Lu Mu", "Max Nu")]},
        "Gamma Library": {"board": [
            # Two addresses one character apart, two numbers one digit apart.
            person("Ned Xi", ("email", "ned.xi@example.com"),
                   ("email", "ned.xii@example.com"), ("phone", "217-555-0131"),
                   ("phone", "217-555-0132")),
            # Two addresses, one carrying his name.
            person("Ona Omicron", ("email", "readinglover@example.net"),
                   ("email", "oomicron@example.net")),
            # An accountant's address naming nobody.
            person("Pat Pi", ("email", "books@smithcpas.example.com")),
            # Printed beside a trustee of another library too.
            person("Quin Rho", ("email", "shared.family@example.net")),
            # Two addresses, neither carrying his name: neither ships.
            person("Rex Koppa", ("email", "gardenfan@example.net"),
                   ("email", "rainyday7@example.org"))]},
        "Delta Library": {"board": [
            person("Ray Sigma", ("email", "shared.family@example.net")),
            # A carried-forward trustee below carries both of these.
            person("Uma Phi", ("email", "family.upsilon@example.net"),
                   ("phone", "217-555-0142"))]},
    }
    carried = {"Epsilon Library": {"readOn": "2026-10-01", "board": [
        {"name": "Sue Tau", "email": "stau@example.com", "phone": "cell 217-555-0141"},
        {"name": "Tom Upsilon", "email": "family.upsilon@example.net",
         "phone": "217-555-0142"}]}}
    expect = {
        lib: {"Ann Alpha": {"role": "President", "phone": "cell 217-555-0101",
                            "phonesExtra": ["home (217) 555-0123"],
                            "email": "Ann.Alpha@example.com"},
              "Bea Beta": {"email": "bookworm42@example.net"},
              "Cal Gamma": {}, "Dee Board": {}, "Eve Epsilon": {}, "Fay Zeta": {},
              "Gus Eta": {}, "Hal Theta": {}, "Ida Iota": {},
              "Jo Kappa": {"email": "jk@orchardlibrary.example.com"}, "Lia Psi": {}},
        "Beta Library": {"Kit Lambda": {}, "Lu Mu": {}, "Max Nu": {}},
        "Gamma Library": {"Ned Xi": {}, "Ona Omicron": {"email": "oomicron@example.net"},
                          "Pat Pi": {}, "Quin Rho": {}, "Rex Koppa": {}},
        "Delta Library": {"Ray Sigma": {}, "Uma Phi": {}},
        "Epsilon Library": {"Sue Tau": {"email": "stau@example.com",
                                        "phone": "cell 217-555-0141"},
                            "Tom Upsilon": {}},
    }
    mail, line = "e-mail address", "telephone number"
    expect_notes = collections.Counter({
        (lib, mail, ON_PAGE): 1, (lib, line, OFFICE_LINE): 2, (lib, mail, MAILBOX): 2,
        (lib, line, ON_PAGE): 1, (lib, mail, LINKED): 1, (lib, mail, ANOTHER): 1,
        (lib, mail, SHARED): 1, (lib, mail, DEAD): 1, (lib, mail, OFFICE_MAIL): 1,
        (lib, line, LINKED): 1, (lib, mail, NOT_NAMED): 1,
        ("Beta Library", line, SHARED): 3, ("Beta Library", mail, SHARED): 3,
        ("Gamma Library", mail, TYPO): 2, ("Gamma Library", line, TYPO): 2,
        ("Gamma Library", mail, NOT_NAMED): 3, ("Gamma Library", mail, FIRM): 1,
        ("Gamma Library", mail, SHARED): 1, ("Delta Library", mail, SHARED): 2,
        ("Delta Library", line, SHARED): 1, ("Epsilon Library", mail, SHARED): 1,
        ("Epsilon Library", line, SHARED): 1})

    boards, notes, found = trustee_boards(reads, carried, context)
    got = {library: {m["name"]: {k: v for k, v in m.items() if k != "name"}
                     for m in board} for library, board in boards.items()}
    checks += 1
    if got != expect:
        problems += 1
        for library in sorted(set(got) | set(expect)):
            if got.get(library) != expect.get(library):
                print("  FAIL %s\n       expected %s\n       got      %s"
                      % (library, expect.get(library), got.get(library)))
    checks += 1
    if notes != expect_notes:
        problems += 1
        print("  FAIL the reasons counted\n       expected %s\n       got      %s"
              % (sorted(expect_notes.items()), sorted(notes.items())))
    checks += 1
    if found:
        problems += 1
        print("  FAIL well-shaped values were refused: %s" % found)

    # A value not shaped like one number or one address refuses the write,
    # naming the library and the trustee and never the value.
    _boards, _notes, found = trustee_boards(
        {"Zeta Library": {"board": [person(
            "Vic Chi", ("phone", "217-555-0151 217-555-0153"),
            ("email", "vic chi@example.com"), ("fax", "217-555-0152"))]}},
        {}, dict(context, filings={}, directory={}))
    checks += 1
    if len(found) != 3 or not all(p.startswith("Zeta Library, trustee 1 (Vic Chi)")
                                  for p in found):
        problems += 1
        print("  FAIL a misshapen value was not refused by library and trustee: %s"
              % found)
    checks += 1
    if any("555" in p or "@" in p for p in found):
        problems += 1
        print("  FAIL a refusal printed the value it refused")
    # The mailbox test on its own, both ways.
    for address, library, want in (
            ("trustee3@example.com", lib, True), ("gdlibrary@example.com",
                                                  "Gilman-Danforth District Library", True),
            ("orchardboard@example.com", lib, True), ("info@example.com", lib, True),
            ("drussell@example.com", lib, False), ("hal.theta@example.com", lib, False),
            ("gus@example.com", lib, False)):
        checks += 1
        if office_mailbox(address, library) != want:
            problems += 1
            print("  FAIL office_mailbox(%r) is not %s" % (address, want))
    print("build-il-library-trustees selftest: %s — %d check(s)%s"
          % ("FAIL" if problems else "OK", checks,
             ", %d problem(s)" % problems if problems else ""))
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("scraped", nargs="?",
                        help="il_library_trustees_scraper.py --out")
    parser.add_argument("--check", action="store_true",
                        help="compare against the shipped file instead of writing")
    parser.add_argument("--selftest", action="store_true",
                        help="offline: run the contact rules against their "
                             "fixtures and stop")
    args = parser.parse_args()

    # THE CONTACT RULES' FIXTURES RUN BEFORE EVERY BUILD AND EVERY --check, so
    # the weekly refresh cannot write a roster with a rule broken.
    if selftest():
        fail("the contact rules failed their own fixtures")
    if args.selftest:
        return
    if not args.scraped:
        parser.error("the scraper's output is required, except with --selftest")

    with open(args.scraped, encoding="utf-8") as handle:
        payload = json.load(handle)
    scraped = payload.get("libraries")
    if not isinstance(scraped, dict) or not scraped:
        fail("the scraper's output has no libraries object")
    read_on = (payload.get("generated") or "")[:10]
    if len(read_on) != 10:
        fail("the scraper's output has no usable `generated` stamp")

    shipped = {}
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as handle:
            shipped = json.load(handle).get("libraries") or {}

    libraries, reads, carried, carried_lines = {}, {}, {}, []
    for name, record in scraped.items():
        verdict = record.get("verdict")
        if verdict == "read":
            entry = {"board": [], "readOn": read_on}
            if record.get("boardUrl"):
                entry["boardUrl"] = record["boardUrl"]
            if record.get("heading"):
                entry["heading"] = record["heading"]
            libraries[name] = entry
            reads[name] = record
            continue
        if verdict in CARRY_FORWARD and name in shipped:
            libraries[name] = shipped[name]
            carried[name] = shipped[name]
            carried_lines.append("%s (%s, last read %s)"
                                 % (name, verdict, shipped[name].get("readOn", "?")))
    for line in sorted(carried_lines):
        print("  carried forward: %s" % line)
    # A library in the shipped file that this run READ a page for and found no
    # board on is DROPPED, and saying which ones is the whole point of printing
    # it: that is the real event, not a flaky fetch.
    dropped = sorted(set(shipped) - set(libraries))
    for name in dropped:
        print("  dropped: %s — this run read its page and found no board (%s)"
              % (name, (scraped.get(name) or {}).get("verdict", "not in the pool")))

    _kinds, where = shipped_cards(statewide_library_counties())
    cards = sum(len(where.get(name) or []) for name in libraries)
    orphans = sorted(name for name in libraries if not where.get(name))

    with open(FILINGS, encoding="utf-8") as handle:
        filings = json.load(handle)["libraries"]
    both = sorted(name for name in libraries
                  if (filings.get(name) or {}).get("board"))

    # EACH TRUSTEE IS WRITTEN FIELD BY FIELD, never copied from the scrape, so
    # what the scraper reports about where a value sat (`contacts`) ships
    # nowhere. The library's other publishers are read as shipped: the shared
    # directory's telephone, its filing's office and administrators, and the
    # addresses the Annual Financial Report rosters give their officers.
    try:
        directory, _by_code = library_directory_lines(APP_DIR)
    except (OSError, ValueError) as exc:
        fail("cannot read the library directory's telephones: %s" % exc)
    context = {"directory": directory, "filings": filings,
               "elsewhere": mail_elsewhere(APP_DIR, os.path.basename(OUT_PATH)),
               "undeliverable": set(UNDELIVERABLE)}
    boards, notes, contact_problems = trustee_boards(reads, carried, context)
    for name, board in boards.items():
        libraries[name] = dict(libraries[name], board=board)
    for (library, kind, why), count in sorted(notes.items()):
        print("  not shipped: %s — %d %s(s), %s" % (library, count, kind, why))

    trustees = sum(len(v["board"]) for v in libraries.values())
    with_role = sum(1 for v in libraries.values()
                    for m in v["board"] if m.get("role"))
    with_email = sum(1 for v in libraries.values()
                     for m in v["board"] if m.get("email"))
    with_phone = sum(1 for v in libraries.values()
                     for m in v["board"] if m.get("phone"))
    short = sorted(n for n, v in libraries.items() if len(v["board"]) < MIN_MEMBERS)
    long_ = sorted(n for n, v in libraries.items() if len(v["board"]) > MAX_MEMBERS)
    unsourced = sorted(n for n, v in libraries.items() if not v.get("boardUrl"))

    problems = []
    for count, floor, what in ((len(libraries), MIN_LIBRARIES, "librar(ies)"),
                               (trustees, MIN_TRUSTEES, "trustee(s)"),
                               (cards, MIN_CARDS, "card(s) stamped"),
                               (with_role, MIN_WITH_ROLE, "trustee(s) with a role"),
                               (with_email, MIN_WITH_EMAIL,
                                "trustee(s) with their own e-mail address")):
        if count < floor:
            problems.append("%d %s < floor %d" % (count, what, floor))
    problems.extend(contact_problems)
    if orphans:
        problems.append("no card carries: %s" % ", ".join(orphans[:8]))
    if both:
        problems.append("these librar(ies) are in BOTH this file and the "
                        "filings' boards, so a card would carry two: %s"
                        % ", ".join(both[:8]))
    if short:
        problems.append("below the floor of %d trustee(s): %s"
                        % (MIN_MEMBERS, ", ".join(short[:8])))
    if long_:
        problems.append("past the ceiling of %d trustee(s): %s"
                        % (MAX_MEMBERS, ", ".join(long_[:8])))
    if unsourced:
        problems.append("no board page url on: %s" % ", ".join(unsourced[:8]))
    if problems:
        for problem in problems:
            print("  %s" % problem, file=sys.stderr)
        fail("refusing to write a payload that lost coverage or carries a "
             "value not shaped like one telephone number or one address")

    out = {
        "generated": payload.get("generated"),
        "libraries": libraries,
        "source": SOURCE,
    }
    text = json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True) + "\n"

    if args.check:
        if not os.path.exists(OUT_PATH):
            fail("%s is missing" % OUT_PATH)
        with open(OUT_PATH, encoding="utf-8") as handle:
            shipped = json.load(handle)
        # `generated` and every record's `readOn` move on a run that read the
        # same pages and found the same people, so neither is compared.
        def bare(doc):
            libs = {k: {kk: vv for kk, vv in v.items() if kk != "readOn"}
                    for k, v in (doc.get("libraries") or {}).items()}
            rest = {k: v for k, v in doc.items() if k not in ("generated", "libraries")}
            rest["libraries"] = libs
            return rest
        if bare(shipped) != bare(out):
            fail("%s does not match a fresh read of the libraries' own sites"
                 % OUT_PATH)
        print("build-il-library-trustees: OK — shipped file matches (%d "
              "librar(ies) on %d card(s), %d trustee(s), %d with their own "
              "e-mail address, %d with a telephone)"
              % (len(libraries), cards, trustees, with_email, with_phone))
        return

    prior = {}
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as handle:
            prior = json.load(handle)
    moved_lines, moved_summary = substantive_changes(prior, out, "libraries", 1)
    for line in moved_lines:
        print(line)
    print("  %s" % moved_summary)
    emit_changes_output(moved_summary)

    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        handle.write(text)
    fresh = sum(1 for v in libraries.values() if v.get("readOn") == read_on)
    print("build-il-library-trustees: wrote %s — %d librar(ies) on %d card(s), "
          "%d trustee(s), %d with a role, %d with their own e-mail address, %d "
          "with a telephone; %d read this run, %d carried forward, %d dropped, "
          "of a pool of %d"
          % (OUT_PATH, len(libraries), cards, trustees, with_role, with_email,
             with_phone, fresh, len(libraries) - fresh, len(dropped), len(scraped)))


if __name__ == "__main__":
    main()
