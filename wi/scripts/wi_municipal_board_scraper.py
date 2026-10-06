#!/usr/bin/env python3
"""
Scrape the governing bodies of the Wisconsin municipalities that elect their
WHOLE board AT LARGE, so there is no district to draw and no district to key a
row on. Stage 1 of the pair; build_wi_municipal_boards.py writes
data/app/wi-municipal-boards.json.

WHY THIS FILE EXISTS BESIDE `wi_alderperson_scraper.py` RATHER THAN INSIDE IT.
That file's output is keyed by DISTRICT, which is what its own card draws and
what its builder's floors count. A city whose council is elected citywide has no
district, and putting its members under seat numbers would tell a reader they
were elected in a way they were not — the honesty rule this project applies to
every card. So the two rosters are separate files with separate shapes, and the
City-or-Village card reads whichever one answers for the place under the point.

WHAT SHAPE THESE ROWS TAKE, AND WHY IT IS BORROWED RATHER THAN INVENTED. The
fleet rule is to check how a live app already handles a shape before building a
new one. Illinois's `municipal-officials.json` already carries exactly this: a
`board` list of {name, role} with no district, keyed by the place's 7-digit
GEOID, rendered on a municipal card. Iowa already shows at-large members under
their own heading. So this file emits Illinois's shape, Wisconsin's City-or-
Village card gains a third roster beside the mayor's and the clerk's (both
already joined on that same GEOID), and no new layer, toggle or engine block is
involved.

THE TWO CITIES, each with its route and its measured trap:

  Caledonia (25,470, GEOID 5511950) — the Village Board, through the village's
                    own `/api/public/mwjsPeople` feed, whose query token the
                    board page itself carries, so the token is READ FROM THE
                    PAGE on every run and never pinned here: a pinned token is a
                    credential this project would be guessing at the lifetime of.
                    THE NAMES ARE NOT IN THE PAGE'S OWN HTML, which is why a
                    first triage scored this village as naming nobody.
                    FOUR TRAPS, all measured 2026-10-01.
                    (1) THE SEAT NUMBERS ARE NOT DISTRICTS. The feed labels its
                    members `Trustee 1` through `Trustee 6` — one of them
                    `Trustee #2`, inconsistently — which reads exactly like a
                    district number, and the village's own board page states in
                    its own words that "The Trustees and President represent the
                    entire Village". So they are SEATS, the role ships verbatim
                    and nothing is keyed on the number.
                    (2) A PERSON'S ROLE IS PER COMMITTEE AND MOST OF THEM ARE
                    NOT THE BOARD'S. Each record's `cats` list carries one entry
                    per body the person sits on — `Chair`, `Member`, `Trustee
                    Liaison`, `Trustee/Board Liaison (back-up)` — so reading any
                    of them makes a trustee the Chair of the board. The board's
                    own category id comes from the feed's `categories` list,
                    which names it `Village Board`, and ONLY the entry under
                    that id is read. The builder fails if a person carries none.
                    (3) THE PHONE NUMBER IS IN TWO DIFFERENT FIELDS. Five of the
                    seven carry it in `personWork` and two in `personPhone`,
                    both bare ten-digit strings; either is taken and neither is
                    preferred over a non-empty other.
                    (4) THE ADDRESSES ARE MEMBERS' HOMES — residences in
                    Racine, Franksville and Caledonia, one of them outside the
                    village — and NONE OF THEM SHIPS, the rule this project
                    already applied to Wabash County's clerk's e-mail. No
                    address field is emitted at all, so there is nothing to
                    filter later.
                    One name also arrives with a double space (`Nancy  Pierce`)
                    and is whitespace-normalised.

  Oshkosh (66,816, GEOID 5560500) — the Common Council at `/CityCouncil/`. The
                    page states the shape in its own words: "seven elected
                    officials in the Common Council including the mayor, the
                    deputy mayor, and five council members", every one with an
                    `@oshkoshwi.gov` address and six with a direct line.
                    THIS CITY'S ROBOTS READ IS THE GATE AND IT IS NOT FORCED.
                    From a Claude Code sandbox both Python stacks fail the
                    handshake with `UNEXPECTED_EOF_WHILE_READING` where `curl`
                    completes it. An earlier record read that as evidence about
                    Oshkosh's own certificate chain; it is not, because this
                    sandbox's egress gateway intercepts and re-signs every
                    outbound connection, so the chain inspected was the
                    gateway's (`wi/WATCH.md`, both rows). The app thread could
                    not reproduce the failure at all. So NOTHING here lowers a
                    security level, passes a bundle or reads the policy with a
                    client it does not crawl with: `require_robots_once` is
                    asked exactly as it is for every other host, and if the
                    policy cannot be read the seam refuses and this one city is
                    recorded as that run's failure while Caledonia ships. On a
                    GitHub runner — the vantage the weekly job actually crawls
                    from, and the one `scripts/probe_robots_verdicts.py` exists
                    to measure — the read FAILED THERE TOO, measured
                    2026-10-01: three reads fifteen seconds apart, every one
                    `Connection reset by peer`. So the policy cannot be read
                    from either vantage with the client that crawls, and under
                    RFC 9309 2.3.1.4 an unreadable robots.txt disallows — which
                    is why this city does not ship.
                    THE TWO SYMPTOMS ARE NOT THE SAME AND ARE NOT CLAIMED TO BE.
                    The sandbox fails during the TLS handshake and the runner
                    fails with a reset at the socket; both sit below HTTP and
                    both read as unreachable, and what they have in common is
                    not established. A LOWERED SECURITY LEVEL IS NOT THE ANSWER:
                    it would be an operator's decision rather than a per-site
                    setting, and it cannot touch a connection reset in any case.
                    The server is not simply down — `curl` completes a request to
                    it — so the difference between the clients is real and
                    unexplained, and asking the city is the honest next step
                    rather than tuning a client until one gets through.
                    A PROVISIONAL READING IS RECORDED AND NOT RELIED ON: read
                    from here through a lowered-security context on 2026-10-01,
                    its robots.txt is 331 bytes disallowing fourteen paths
                    (Laserfiche, WebTrac, test directories) and permitting
                    `/CityCouncil/`. That read used a client this project does
                    not crawl with, so it is written down as what one
                    lowered-security read returned and never as the verdict.
                    THE RUNNER DID NOT CONFIRM IT; see above.

BOTH HOSTS SERVE THE DISTRICTRY TOKEN and that is why this file sends one. The
sibling alderperson scraper sends a pinned Chrome string because 17 of the 35
hosts it reaches refuse the token and the User-Agent is set once for all of
them; this file reaches two hosts and neither needs it. Caledonia was measured
with the token on 2026-10-01 (HTTP 200, 152,215 bytes, byte-identical to the
browser-string read) and publishes no robots.txt at all (HTTP 404, allow all).
Oshkosh's token read is the runner's to take.
"""

import io
import json
import html as H
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "scripts"))
from scraper_common import (UA_CHROME_WIN_126, UA_HINTS_CHROME_126,  # noqa: E402
                            UA_ROSTER_BOT, require_robots_once)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(SCRIPT_DIR, ".cache")
DEFAULT_OUT = os.path.join(CACHE_DIR, "wi_municipal_boards_raw.json")

UA = {"User-Agent": UA_ROSTER_BOT}

CALEDONIA_BOARD = "https://www.caledonia-wi.gov/board"
CALEDONIA_FEED_HOST = "https://www.caledonia-wi.gov/"
OSHKOSH_COUNCIL = "https://www.ci.oshkosh.wi.us/CityCouncil/"
JANESVILLE_CONTACT = ("https://www.janesvillewi.gov/government/city-council"
                      "/contact-the-city-council")
JANESVILLE_MEMBERS = ("https://www.janesvillewi.gov/government/city-council"
                      "/city-councilmembers")

# JANESVILLE'S EDGE REFUSES THE TOKEN AND IT REFUSES IT ON ROBOTS.TXT FIRST,
# which is what licenses a browser string here and is measured rather than
# assumed (2026-10-01, this file's own stdlib client, the rung it crawls on):
#   www.janesvillewi.gov/robots.txt  token  HTTP 403
#   www.janesvillewi.gov/robots.txt  below  HTTP 200, 6641 bytes
# The token was asked FIRST and refused, so nothing here escalates past a host
# that was serving us — the rule this project states in both directions.
# THE POLICY IS NOT JANESVILLE'S OWN CHOICE AND MUST NEVER BE CITED AS ONE.
# Those 6,641 bytes are BYTE-IDENTICAL to www.kendallcountyil.gov's, md5
# 16e66653dfbe3d2bee5636483dea61df, re-fetched side by side the same minute:
# 226 Disallow rules aimed at one CMS platform's own admin and asset paths. It
# is published at the city's own host so it binds fully, and it permits the two
# pages below. www.joliet.gov, which CLAUDE.md records serving the same bytes,
# answered 404 to the same client on 2026-10-01 — no policy, allow all — so
# that record was right when written and one of its three hosts has moved.
UA_AKAMAI = dict(UA, **{
    "User-Agent": UA_CHROME_WIN_126,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Connection": "close",
})
UA_AKAMAI.update({k: v for k, v in UA_HINTS_CHROME_126.items()
                  if k.lower().startswith("sec-ch-ua")})


def fetch(url, tries=3, timeout=60, headers=None):
    """Read the host's robots.txt before the first fetch of it, then fetch.

    The seam is asked with the SAME header set this function then crawls with,
    because which client crawls decides which robots group binds — so `headers`
    governs both calls or neither, and a caller cannot read a policy as one
    client and fetch as another. That is a consistency rule and not a licence to
    reach for the richer client: the default is this project's own token, and
    `UA_AKAMAI` is passed by the one city whose edge was measured refusing the
    token on robots.txt itself. A refusal or an unreadable policy raises, and
    `attempt()` turns that into ONE city's recorded failure rather than the
    run's: a robots verdict is always a fact about one host and never a pinned
    reading that has stopped being true, which is the line the sibling scraper
    already draws between the two.
    """
    headers = headers or UA
    try:
        require_robots_once(url, headers["User-Agent"], headers=headers,
                            label="wi_municipal_board_scraper")
    except SystemExit:
        raise RuntimeError(
            "robots.txt declined for %s — see the FAIL line above for the "
            "verdict; nothing was fetched from it"
            % (urllib.parse.urlsplit(url).hostname or url))
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as exc:          # noqa: BLE001 — retried, then reported
            last = exc
    raise RuntimeError("%s: %s" % (url, last))


def clean(text):
    return re.sub(r"\s+", " ", H.unescape(text or "")).strip()


def scrape_caledonia():
    page = fetch(CALEDONIA_BOARD)

    # THE VILLAGE'S OWN WORDS ARE A GATE. If this sentence ever leaves the page,
    # the at-large claim this roster makes has lost its source and the build must
    # stop rather than keep asserting it.
    if "represent the entire Village" not in page:
        raise RuntimeError("Caledonia's board page no longer states that the "
                           "trustees and president represent the entire village "
                           "— the at-large claim has lost its source")

    # The feed's query token rides the page. Two spellings appear; the one
    # carrying `tn=` is the tenant-qualified call the page itself makes.
    refs = [u for u in re.findall(r'api/public/mwjsPeople\?[^"\'<\s]+', page)
            if "tn=" in u]
    if not refs:
        raise RuntimeError("Caledonia's board page no longer carries the "
                           "people-feed URL this scraper reads it from")
    body = fetch(urllib.parse.urljoin(CALEDONIA_FEED_HOST, H.unescape(refs[0])))

    # The response is `var mwjsMemberData={...};` followed by further
    # assignments, so it is not a JSON document and `json.loads` fails on it.
    data, _ = json.JSONDecoder().raw_decode(body[body.index("{"):])

    board_ids = [c.get("catId") for c in data.get("categories", [])
                 if clean(c.get("name")).lower() == "village board"]
    if len(board_ids) != 1:
        raise RuntimeError("Caledonia's feed names %d categories called "
                           "'Village Board'; the role column cannot be read "
                           "without exactly one" % len(board_ids))
    board_id = board_ids[0]

    members = []
    for person in data.get("people", []):
        roles = [clean(c.get("ItemText")) for c in person.get("cats", [])
                 if c.get("eItemId") == board_id or c.get("catId") == board_id]
        roles = [r for r in roles if r]
        if not roles:
            # Every one of the seven carries a Village Board role; a record
            # without one is a shape change, not a member to guess a role for.
            raise RuntimeError("Caledonia: %r carries no Village Board role"
                               % clean(person.get("personName")))
        name = clean(person.get("personName"))
        phone = clean(person.get("personWork")) or clean(person.get("personPhone"))
        row = {"name": name, "role": roles[0]}
        email = clean(person.get("personEmail"))
        if email:
            row["email"] = email
        if re.fullmatch(r"\d{10}", phone or ""):
            row["phone"] = "(%s) %s-%s" % (phone[:3], phone[3:6], phone[6:])
        elif phone:
            row["phone"] = phone
        members.append(row)

    # NO ADDRESS SHIPS. The feed's `addresses` are members' HOME addresses,
    # measured 2026-10-01 — residences in Racine, Franksville and Caledonia.
    return {"geoid": "5511950", "name": "Caledonia", "county": "Racine",
            "atLarge": True, "board": members, "sourceUrl": CALEDONIA_BOARD}


def scrape_oshkosh():
    page = fetch(OSHKOSH_COUNCIL)

    # THE CITY'S OWN WORDS ARE THE AT-LARGE GATE, as at Caledonia.
    flat = clean(page)
    if "deputy mayor" not in flat.lower():
        raise RuntimeError("Oshkosh's council page no longer describes the "
                           "council's composition — the at-large claim has lost "
                           "its source")

    members = []
    seen = set()
    # Each official is a block carrying a name, a role line and a mailto. The
    # mailto is the anchor because it is the one field every one of the seven
    # has, and the role line sits immediately above it.
    for block in re.split(r"(?i)<(?:h[2-5]|div class=\"[^\"]*council)", page):
        mail = re.search(r'mailto:([A-Za-z0-9._%+-]+@oshkoshwi\.gov)', block)
        if not mail:
            continue
        email = mail.group(1)
        if email.lower() in seen:
            continue
        text = clean(re.sub(r"<[^>]+>", " ", block))
        role = re.search(r"(?i)\b(Mayor|Deputy Mayor|Council Member)\b", text)
        name = re.search(r"(?i)\b(Mayor|Deputy Mayor|Council Member)\b\s*"
                         r"([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){1,3})",
                         text)
        if not (role and name):
            continue
        seen.add(email.lower())
        row = {"name": clean(name.group(2)), "role": clean(role.group(1)),
               "email": email}
        phone = re.search(r"\(?(\d{3})\)?[ .-](\d{3})[ .-](\d{4})", text)
        if phone:
            row["phone"] = "(%s) %s-%s" % phone.groups()
        members.append(row)

    return {"geoid": "5560500", "name": "Oshkosh", "county": "Winnebago",
            "atLarge": True, "board": members, "sourceUrl": OSHKOSH_COUNCIL}


def scrape_janesville():
    """Janesville's seven, from the city's own contact table.

    TWO PAGES, AND THE SECOND ONE IS A WITNESS RATHER THAN A SOURCE. The contact
    table carries everything a card needs — name, role, city phone, e-mail and
    term — and the councilmembers page carries the biographies and the same seven
    names. Both are read and the names must agree, because a table is the easiest
    surface on a city site to leave a departed member in.

    THE AT-LARGE GATE IS THE CITY'S OWN SENTENCE, as at Caledonia and Oshkosh,
    and both pages state it: "Councilmembers are elected at large, thus
    representing residents in the whole city" on the contact page, and "seven
    members who are elected on a nonpartisan basis and represent the city as a
    whole" on the members page. Either leaving the site is a shape change.

    THE TRAP IS AN EMPTY LINK CARRYING THE PREVIOUS MEMBER'S ADDRESS, and it is
    the reason this reads cell TEXT and never an href. Measured 2026-10-01, two of
    the seven e-mail cells hold TWO anchors: an empty one — no link text,
    `tabindex="-1"` — whose href is the person who used to hold that seat, then
    the real one. Michael Cass's cell links `marshickd@ci.janesville.wi.us` and
    Shane Seeman's links `wolfet@ci.janesville.wi.us`, neither of whom is on this
    council. **A reader taking the first mailto in the cell ships the wrong
    person's address for two of seven members, and it looks completely right** —
    the Manitowoc `title=` trap one step worse, because there the stale name was
    in an attribute nobody renders and here it is the link's own destination.
    Reading the text the city prints avoids it, and avoids a second trap for
    free: Cassandra Pope's and Richard Neeno's anchors have no `mailto:` scheme
    at all (`href="popec@janesvillewi.gov"`), so a scheme-anchored pattern misses
    two more.

    THE CELL POSITIONS ARE NOT RELIABLE EITHER and are not used as a fallback.
    Two of the seven have no cell-phone number, and some term cells carry
    `colspan="2"`, so a column index drifts; the HEADER ROW names the columns and
    is what this maps on, failing if the five headings ever change.

    THE CELL-PHONE COLUMN IS READ AND NOT SHIPPED. The city publishes a City
    Phone and a Cell Phone for each member, and only the first is emitted: a
    direct city line is the number a resident is meant to use, while the other is
    a personal handset, published on five of seven records so a column built from
    it would be partly blank anyway. Nothing filters it later because nothing
    emits it.

    NO ADDRESS SHIPS. The page gives one mailing address for the whole council
    (City Hall, PO Box 5005) and no member's own, so there is none to exclude.
    """
    contact = fetch(JANESVILLE_CONTACT, headers=UA_AKAMAI)
    if "elected at large" not in clean(contact).lower():
        raise RuntimeError("Janesville's contact page no longer says the "
                           "council is elected at large — the at-large claim "
                           "has lost its source")

    table = None
    for block in re.findall(r"(?is)<table[^>]*>.*?</table>", contact):
        if re.search(r"(?i)>\s*City Phone\s*<", block):
            table = block
            break
    if table is None:
        raise RuntimeError("Janesville's contact page has no table with a City "
                           "Phone column; the roster cannot be read by heading")

    rows = re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", table)
    cells = [[clean(re.sub(r"(?is)<[^>]+>", " ", c))
              for c in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", r)]
             for r in rows]
    cells = [row for row in cells if row]
    if not cells:
        raise RuntimeError("Janesville's contact table has no rows")

    # THE HEADING ROW IS THE AUTHORITY for which column is which, never a
    # position: two members have no cell number and some term cells span two
    # columns, so an index taken from the first data row drifts.
    head = [h.lower() for h in cells[0]]
    want = ["name", "city phone", "cell phone", "email address", "term(s)"]
    if head != want:
        raise RuntimeError("Janesville's contact table heads its columns %r, "
                           "not %r — the mapping is by heading and cannot be "
                           "guessed" % (cells[0], want))
    ix = {k: i for i, k in enumerate(head)}

    members = []
    for row in cells[1:]:
        if len(row) != len(head):
            raise RuntimeError("Janesville: a council row has %d cells against "
                               "%d headings; %r" % (len(row), len(head), row))
        who = row[ix["name"]]
        if not who:
            continue
        # The name cell is "<name>" or "<name>, <role>" — the city's own two
        # officers are the only rows carrying a role, and the rest are plain
        # councilmembers, which is what the page calls them in its own prose.
        name, _, role = (p.strip() for p in who.partition(","))
        member = {"name": name, "role": role or "Councilmember"}
        email = row[ix["email address"]]
        if email:
            member["email"] = email
        phone = row[ix["city phone"]]
        if phone:
            member["phone"] = phone
        term = row[ix["term(s)"]]
        if term:
            member["term"] = term
        members.append(member)

    # THE SECOND PAGE IS THE WITNESS. It must name the same seven people, and a
    # table that has kept a departed member or dropped a new one fails here
    # rather than shipping.
    bios = clean(re.sub(r"(?is)<(script|style|nav)[^>]*>.*?</\1>", " ",
                        fetch(JANESVILLE_MEMBERS, headers=UA_AKAMAI)))
    if "represent the city as a whole" not in bios.lower():
        raise RuntimeError("Janesville's councilmembers page no longer says the "
                           "council represents the city as a whole")
    missing = [m["name"] for m in members if m["name"] not in bios]
    if missing:
        raise RuntimeError("Janesville: %s in the contact table but not on the "
                           "councilmembers page" % ", ".join(missing))

    return {"geoid": "5537825", "name": "Janesville", "county": "Rock",
            "atLarge": True, "board": members,
            "sourceUrl": JANESVILLE_CONTACT}


CITIES = (("Caledonia", scrape_caledonia), ("Oshkosh", scrape_oshkosh),
          ("Janesville", scrape_janesville))


def attempt(label, fn, got, failures):
    """One city's bad day costs that city and nothing else.

    `Exception` is caught and a GATE is not: every gate above raises and gates
    are `RuntimeError`, which IS caught here — deliberately, because each gate
    names one city's source and a changed source in one village says nothing
    about the other. The builder carries a missing city's last-good rows forward
    and names the reason, so a gate is visible in the weekly pull request rather
    than silent. A `SystemExit` from anywhere else is NOT caught and still ends
    the run.
    """
    try:
        got[label] = fn()
        print("%s: %d member(s)" % (label, len(got[label]["board"])))
    except Exception as exc:              # noqa: BLE001 — recorded, per city
        failures[label] = str(exc)
        print("%s: FAILED — %s" % (label, exc), file=sys.stderr)


def main(argv):
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT
    only = argv[argv.index("--city") + 1].lower() if "--city" in argv else None

    got, failures = {}, {}
    for label, fn in CITIES:
        if only and label.lower() != only:
            continue
        attempt(label, fn, got, failures)

    if not got:
        print("No city resolved; nothing written.", file=sys.stderr)
        return 1

    dirname = os.path.dirname(out_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8") as f:
        json.dump({"cities": got, "failures": failures}, f, indent=2,
                  sort_keys=True, ensure_ascii=False)
    print("wrote %s — %d city/cities, %d failure(s)"
          % (os.path.relpath(out_path), len(got), len(failures)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
