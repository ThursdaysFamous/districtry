#!/usr/bin/env python3
"""Whose e-mail address is this? The checks Wisconsin's officeholder rosters share.

Since 2026-10-17 a Wisconsin roster ships the e-mail address a government page
prints beside an official whatever its domain — a Gmail, internet-provider or
business address as well as the government's own — on Adam's choice that day
("E-mails too"). Until then several readers kept an address only when it was
on the government's own domain, and that domain test was also doing three other
jobs without saying so: it kept out a value that is not one address, an
office's address printed for several officials, and an address that belongs to
the official on the next row. Those three are asked here, by name, so that
dropping the domain test drops nothing else. The county board, alderperson and
at-large board builders all call this file, so one roster cannot answer one of
these questions differently from another.

  EMAIL_SHAPE       one address: one "@", no space anywhere, a dot and two
                    letters after it.
  settle_shared()   an address printed for two or more seats of one place
                    ships on the one seat whose holder's surname its local part
                    carries, when exactly one does, and on no seat otherwise.
                    Ashland County printed one supervisor's address for his
                    own district and for another on 2026-10-17; this keeps it
                    on his district and off the other.
  names_another()   an address whose local part names another official of the
                    same place (that person's surname joined to their initial
                    or first name, or standing as a word of its own) and does
                    not carry the holder's own surname belongs to that other
                    official, and does not ship on this row.
  settle_place()    all three for one place's records, in place: the
                    alderperson and at-large board builders call it, and the
                    county board builder calls the two above per county.

WHAT "CARRIES THE SURNAME" MEANS, because a loose reading hands an office's
address to whoever has a short surname. A surname of five or more letters is
carried when it appears anywhere in the local part's letters ("jlivingston",
"livingston.j"). A shorter one is carried only as a whole word of the local
part or a word made of it and the holder's initial or first name ("hall.j",
"jhall", "johnhall"), so "cityhall" does not carry Hall and "coerward" does not
carry Ward. A hyphenated surname is carried by either half or by both together.

Every message these checks lead to names the place and the seat and never the
address: a personal address is a person's contact detail, and a build log is
not where it is published. The callers write their own messages for that
reason; nothing here prints.

Usage:
    python3 wi/scripts/wi_email_rules.py --selftest
"""

import re
import sys
import unicodedata

EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}
LONG = 5      # a surname this long is matched anywhere in the local part
NICKNAME = re.compile(r'"([^"]+)"|\(([^)]+)\)|“([^”]+)”')


def _fold(text):
    text = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def _local(address):
    """The local part's letters as one string, and its words."""
    local = _fold(str(address or "").split("@", 1)[0])
    words = [w for w in re.split(r"[^a-z]+", local) if w]
    return "".join(words), words


def name_parts(name):
    """(first names, surnames) of a printed name, folded to plain letters.

    A nickname in quotes or brackets ('Jeff "Potsie" Weber', 'Ernst (Ernie)
    Franzen') counts as a first name, because a person's own address is often
    built from the name they go by. Suffixes and one-letter initials are
    dropped. The surname is the last word; a hyphenated one gives each half
    and the two together.
    """
    text = str(name or "")
    nicks = [w for found in NICKNAME.findall(text) for part in found
             for w in re.split(r"[^a-z]+", _fold(part)) if len(w) > 1]
    text = NICKNAME.sub(" ", text).replace(",", " ")
    words = [re.sub(r"[^a-z-]", "", _fold(w)).strip("-") for w in text.split()]
    words = [w for w in words
             if w and w not in SUFFIXES and len(w.replace("-", "")) > 1]
    if not words:
        return [], []
    last = words[-1]
    surnames = [p for p in last.split("-") if len(p) > 1]
    if "-" in last:
        surnames.append(last.replace("-", ""))
    firsts = ([words[0].replace("-", "")] if len(words) > 1 else []) + nicks
    return firsts, surnames


def _forms(surname, firsts):
    """The words a local part may use for one person: the surname alone, or
    joined to their initial or first name on either side."""
    forms = {surname}
    for first in firsts:
        forms |= {first[0] + surname, surname + first[0],
                  first + surname, surname + first}
    return forms


def carries_surname(address, name):
    """Does the address's local part carry this person's surname?"""
    letters, words = _local(address)
    firsts, surnames = name_parts(name)
    for surname in surnames:
        if len(surname) >= LONG and surname in letters:
            return True
        if set(words) & _forms(surname, firsts):
            return True
    return False


def names_another(address, name, others):
    """True when the address names one of OTHERS and not the holder NAME.

    OTHERS are the other officials of the same place. An address carrying the
    holder's own surname is the holder's. Otherwise it names another official
    when it joins that person's surname to their initial or first name
    ("jsmith", "john.smith", "smithj"), or holds their surname as a word of its
    own — unless that word is also one of the holder's first names, because
    "rose.k" is Rose Kowalski's whoever else sits on the board. An official
    who shares the holder's surname is skipped, because carrying that surname
    is consistent with the address being the holder's own.
    """
    if not address or carries_surname(address, name):
        return False
    letters, words = _local(address)
    own_firsts, own = name_parts(name)
    for other in others:
        firsts, theirs = name_parts(other)
        if not theirs or set(theirs) & set(own):
            continue
        for surname in theirs:
            if surname in words and surname not in own_firsts:
                return True
            if len(surname) >= 3 and any(
                    form in letters for form in _forms(surname, firsts) - {surname}):
                return True
    return False


def settle_shared(rows):
    """{address: (keeper or None, [keys])} for every address on two or more keys.

    ROWS is an iterable of (key, holder's name, address) for ONE place.
    Addresses are compared without case. The keeper is the one key whose
    holder's surname the local part carries, when exactly one does; every other
    key sharing that address loses it.
    """
    groups = {}
    for key, name, address in rows:
        if address:
            groups.setdefault(str(address).strip().lower(), []).append((key, name))
    out = {}
    for address, held in groups.items():
        if len(held) < 2:
            continue
        carriers = [key for key, name in held if carries_surname(address, name)]
        out[address] = (carriers[0] if len(carriers) == 1 else None,
                        [key for key, _ in held])
    return out


def settle_place(seats):
    """Every rule above, applied to ONE place's records in place.

    SEATS is a list of (seat label, record), the record being the dict that
    ships, with "name" and perhaps "email"; the label is what a message calls
    the seat ("district 03", "member 2"). Returns (refusals, notes). REFUSALS
    name each seat whose `email` is not one address, and when there are any
    nothing is changed, because a reader that hands over a fragment of a page
    is broken and the build should stop. Otherwise an address printed for two
    or more seats stays only on the seat settle_shared() picks, an address that
    names another official of the place is taken off, and NOTES says which
    seats lost an address and why — by label, never by the address.
    """
    refusals = ["%s: the e-mail field is not one address" % label
                for label, record in seats
                if record.get("email") is not None
                and not EMAIL_SHAPE.match(str(record["email"]))]
    if refusals:
        return refusals, []
    notes = []
    rows = [(i, record.get("name"), record.get("email"))
            for i, (_label, record) in enumerate(seats)]
    for _address, (keeper, keys) in sorted(settle_shared(rows).items()):
        labels = ", ".join(seats[i][0] for i in keys)
        for i in keys:
            if i != keeper:
                seats[i][1].pop("email", None)
        if keeper is None:
            notes.append("one address is printed for %s and names none of "
                         "their holders, or more than one — it ships for none "
                         "of them" % labels)
        else:
            notes.append("one address is printed for %s and names the holder "
                         "of %s — it ships there only" % (labels, seats[keeper][0]))
    names = [record.get("name") for _label, record in seats]
    for i, (label, record) in enumerate(seats):
        address = record.get("email")
        if address and names_another(address, record.get("name"),
                                     names[:i] + names[i + 1:]):
            record.pop("email")
            notes.append("%s: the address names another official of the same "
                         "place and not this one — not shipped" % label)
    return refusals, notes


def _selftest():
    """Every rule above on made-up names and reserved example domains."""
    bad = []

    def same(label, got, want):
        if got != want:
            bad.append("%s: got %r, want %r" % (label, got, want))

    for value in ("pat.doe@example.net", "Pat.Doe+board@co.example.wi.us"):
        same("one address " + value, bool(EMAIL_SHAPE.match(value)), True)
    for value in ("pat doe@example.net", "pat@example", "pat@example.net lee@example.net",
                  "pat@example.net,lee@example.net", "pat.doe", ""):
        same("not one address %r" % value, bool(EMAIL_SHAPE.match(value)), False)

    same("parts", name_parts('Jeff "Potsie" Weber'), (["jeff", "potsie"], ["weber"]))
    same("parts, brackets and suffix", name_parts("Ernst (Ernie) Franzen, Jr."),
         (["ernst", "ernie"], ["franzen"]))
    same("parts, hyphen", name_parts("Gina Cefalu-Paulick"),
         (["gina"], ["cefalu", "paulick", "cefalupaulick"]))
    same("parts, apostrophe and initials", name_parts("Q.A. O'Brien, II"),
         (["qa"], ["obrien"]))

    same("long surname anywhere", carries_surname("jlivingston@example.net", "Jim Livingston"), True)
    same("surname then initial", carries_surname("livingston.j@example.net", "Jim Livingston"), True)
    same("short surname, initial", carries_surname("jhall2@example.net", "Joe Hall"), True)
    same("short surname, word", carries_surname("hall.joe@example.net", "Joe Hall"), True)
    same("short surname inside a word", carries_surname("cityhall@example.net", "Joe Hall"), False)
    same("ward is not coerward", carries_surname("coerward1@example.net", "Tom Ward"), False)
    same("hyphen half", carries_surname("gcefalu@example.net", "Gina Cefalu-Paulick"), True)
    same("a seat mailbox carries nobody", carries_surname("district7@example.net", "Pat Doe"), False)

    roster = [("13", "Jim Livingston", "jim.livingston@example.net"),
              ("15", "Kay Jolma", "Jim.Livingston@example.net"),
              ("16", "Lee Roe", "lee.roe@example.net")]
    same("by row: the named supervisor keeps it", settle_shared(roster),
         {"jim.livingston@example.net": ("13", ["13", "15"])})
    office = [("1", "Pat Doe", "office@example.net"), ("2", "Kay Roe", "office@example.net")]
    same("an office's address: nobody", settle_shared(office),
         {"office@example.net": (None, ["1", "2"])})
    pair = [("1", "Ann Smith", "smiths@example.net"), ("2", "Bob Smith", "smiths@example.net")]
    same("two holders it could name: nobody", settle_shared(pair),
         {"smiths@example.net": (None, ["1", "2"])})
    same("nothing shared", settle_shared([("1", "Pat Doe", "a@example.net"),
                                          ("2", "Kay Roe", "b@example.net")]), {})

    council = ["John Smith", "John Ward", "Tom Rose", "Rosemary Kowalski"]
    same("names another, first.last", names_another(
        "john.smith@example.net", "John Ward", council), True)
    same("names another, initial", names_another(
        "jsmith@example.net", "John Ward", council), True)
    same("names another, surname alone", names_another(
        "smith@example.net", "John Ward", council), True)
    same("own address", names_another("jward@example.net", "John Ward", council), False)
    same("own first name", names_another(
        "rosemary.k@example.net", "Rosemary Kowalski", council), False)
    same("own first name that is another's surname", names_another(
        "rose.k@example.net", "Rose Kowalski", council), False)
    same("another's whole name beside an own first name", names_another(
        "john.smith@example.net", "John Ward", council), True)
    same("a word that holds a surname", names_another(
        "packersfan@example.net", "John Ward", council + ["Ed Packer"]), False)
    same("a seat mailbox", names_another("coerward1@example.net", "Tom Rose", council), False)
    same("a shared surname is not another person", names_another(
        "smith@example.net", "Ann Smith", ["Bob Smith"]), False)
    same("no address", names_another(None, "John Ward", council), False)

    def place(records):
        seats = [("seat %d" % n, dict(r)) for n, r in enumerate(records, 1)]
        refusals, notes = settle_place(seats)
        if any("@" in line for line in refusals + notes):
            bad.append("settle_place: a message carries an address")
        return [r.get("email") for _label, r in seats], len(refusals), len(notes)

    same("place: a personal address on its own row ships", place(
        [{"name": "Pat Doe", "email": "patdoe1960@example.com"},
         {"name": "Kay Roe", "email": "kroe@city.example.gov"}]),
        (["patdoe1960@example.com", "kroe@city.example.gov"], 0, 0))
    same("place: a shared address ships for the one it names", place(
        [{"name": "Jim Livingston", "email": "jim.livingston@example.net"},
         {"name": "Kay Jolma", "email": "Jim.Livingston@example.net"}]),
        (["jim.livingston@example.net", None], 0, 1))
    same("place: an office's address ships for nobody", place(
        [{"name": "Pat Doe", "email": "council@example.net"},
         {"name": "Kay Roe", "email": "council@example.net"}]),
        ([None, None], 0, 1))
    same("place: an address naming another official is left off", place(
        [{"name": "John Ward", "email": "jsmith@example.net"},
         {"name": "John Smith", "email": "john.smith@example.net"}]),
        ([None, "john.smith@example.net"], 0, 1))
    same("place: a value that is not one address is refused and nothing moves",
         place([{"name": "Pat Doe", "email": "pat doe@example.net"},
                {"name": "Kay Roe", "email": "council@example.net"},
                {"name": "Lee Poe", "email": "council@example.net"}]),
         (["pat doe@example.net", "council@example.net", "council@example.net"], 1, 0))

    if bad:
        for line in bad:
            print("wi_email_rules selftest: FAIL %s" % line, file=sys.stderr)
        sys.exit(1)
    print("wi_email_rules selftest: OK (one address, a shared address by row, "
          "an address naming another official, one place's records)")


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        _selftest()
    else:
        print(__doc__.strip())
