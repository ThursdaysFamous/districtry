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

SIX BODIES SINCE 2026-10-15. Caledonia, Oshkosh and Janesville are described
below and in their own functions; Mount Pleasant, Menomonee Falls and Fond du Lac
joined that day, each with its gate in its own docstring. TWO OF THE SIX DO NOT
SAY THEY ARE ELECTED AT LARGE — Menomonee Falls says its trustees are elected
"by numbered seat", Fond du Lac does not say — so they carry `atLarge: false`
and a `howElected` sentence repeating what the city says, and the card prints
that sentence instead of "elected at large".

OSHKOSH READS FROM HERE NOW. On 2026-10-15 the city's council page had moved to
www.oshkoshwi.gov, whose robots.txt (621 bytes) answered this file's own token
from a Claude Code sandbox with the default TLS context and permits both pages
read, and both pages answered. The history below is kept as it was written.

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
# THE CITY'S CURRENT HOST, NOT THE ONE THE ELECTIONS COMMISSION LISTS.
# www.ci.oshkosh.wi.us/CityCouncil/ now redirects here, and urllib follows a
# redirect without asking the new host's robots.txt, so the page is fetched at
# its own address and the policy read is the one that governs it (2026-10-15:
# 621 bytes, no rule matching either path).
OSHKOSH_COUNCIL = "https://www.oshkoshwi.gov/CityCouncil/"
OSHKOSH_FORM = "https://www.oshkoshwi.gov/CityCouncil/FormOfGovernment.aspx"
# The tranche of 2026-10-15: three more governing bodies of 25,000 or more
# whose map draws no district. All three hosts served this file's own token,
# robots.txt first, on that day; Mount Pleasant and Menomonee Falls serve the
# 816-byte CivicPlus default policy, which is never to be cited as either
# village's own choice.
MOUNT_PLEASANT_BOARD = "https://www.mtpleasantwi.gov/319/Village-Board"
MENOMONEE_FALLS_BOARD = ("https://www.menomoneefalls.gov/1410"
                         "/Village-Board-Members")
FOND_DU_LAC_ABOUT = "https://www.fdl.wi.gov/city-council/"
FOND_DU_LAC_CONTACT = "https://www.fdl.wi.gov/city-council/contact-us/"
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


# Janesville's Cell Phone cell must hold exactly one telephone number, and any
# number the contact page prints is found with the second pattern.
JANESVILLE_ONE_NUMBER = re.compile(r"^\(?\d{3}\)?[\s.-]*\d{3}[\s.-]\d{4}$")
JANESVILLE_NUMBER = re.compile(r"\(?\b\d{3}\)?[\s.-]*\d{3}[\s.-]\d{4}\b")


def _digits(text):
    """The digits that identify a telephone line, a leading 1 dropped."""
    d = re.sub(r"\D", "", text or "")
    return d[1:] if len(d) == 11 and d.startswith("1") else d


def _tel_links_agree(cell_html):
    """False when a tel: link in the cell dials a different number than the
    number its own text shows. A link showing no number is not compared."""
    for href, shown in re.findall(
            r'(?is)<a\b[^>]*\bhref\s*=\s*["\']?tel:([^"\'>\s]*)[^>]*>(.*?)</a>',
            cell_html or ""):
        text = clean(re.sub(r"(?is)<[^>]+>", " ", shown))
        if re.search(r"\d", text) and _digits(href) != _digits(text):
            return False
    return True


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
    """The Common Council, one `councilMember` block per official: an h3
    reading "Mayor NAME", "Deputy Mayor NAME" or "Council Member NAME", a phone
    line that may be blank, an e-mail and a term.

    THE AT-LARGE GATE IS THE CITY'S OWN SENTENCE on its Form of Government
    page: "Oshkosh elects six council members and a mayor on a non-partisan
    basis, at large". The council page itself never says at large.

    THE BLOCK IS THE UNIT. An earlier version split the page on headings and
    took the first phone number in the text that followed, so a member whose
    phone line is blank (Jacob Amos, measured 2026-10-15) was handed the city's
    main number from further down the page. Reading inside each block leaves a
    blank line blank.
    """
    form = clean(re.sub(r"<[^>]+>", " ", fetch(OSHKOSH_FORM)))
    if not re.search(r"(?i)elects six council members and a mayor\b[^.]*"
                     r"\bat large\b", form):
        raise RuntimeError("Oshkosh's Form of Government page no longer says "
                           "the council is elected at large — the at-large "
                           "claim has lost its source")
    page = fetch(OSHKOSH_COUNCIL)
    members = []
    for block in re.split(r'<div class="councilMember\b', page)[1:]:
        h3 = re.search(r"(?s)<h3>(.*?)</h3>", block)
        if not h3:
            continue
        m = re.fullmatch(r"(Mayor|Deputy Mayor|Council Member)\s+(.+)",
                         clean(re.sub(r"<[^>]+>", " ", h3.group(1))))
        if not m:
            raise RuntimeError("Oshkosh: a council block is headed %r, which "
                               "names no role this reader knows"
                               % clean(h3.group(1)))
        row = {"name": m.group(2), "role": m.group(1)}
        mail = re.search(r'mailto:([A-Za-z0-9._%+-]+@oshkoshwi\.gov)', block)
        if mail:
            row["email"] = mail.group(1)
        body = clean(re.sub(r"<[^>]+>", " ", block[h3.end():]))
        phone = re.search(r"\((\d{3})\)\s*(\d{3})-(\d{4})", body)
        if phone:
            row["phone"] = "(%s) %s-%s" % phone.groups()
        term = re.search(r"Term:\s*(\d{4})", body)
        if term:
            row["term"] = term.group(1)
        members.append(row)
    if len(members) != 7:
        raise RuntimeError("Oshkosh: %d council blocks against the six members "
                           "and mayor its Form of Government page states"
                           % len(members))
    return {"geoid": "5560500", "name": "Oshkosh", "county": "Winnebago",
            "atLarge": True, "board": members, "sourceUrl": OSHKOSH_COUNCIL}


def scrape_mount_pleasant():
    """The Village Board: an h3 per member reading "NAME<br>Village President"
    or "NAME<br>Trustee Seat No. N", then a paragraph with a mailto, a phone
    and "Term Expires: Month YYYY".

    THE AT-LARGE GATE IS THE VILLAGE'S OWN SENTENCE: "These elected officials
    serve at large." The seat numbers are seats, not districts, and the card
    says so.
    """
    page = fetch(MOUNT_PLEASANT_BOARD)
    if "These elected officials serve at large" not in clean(page):
        raise RuntimeError("Mount Pleasant's board page no longer says its "
                           "officials serve at large — the at-large claim has "
                           "lost its source")
    # A heading may not span another heading's close: the page carries an
    # empty `<h3><br></h3>` before a script, and a lazy match across it read a
    # script line into the next member's name.
    members = []
    for m in re.finditer(r'(?s)<h3 class="subhead2"[^>]*>((?:(?!</h3>).)*)'
                         r'</h3>\s*<p[^>]*>(.*?)</p>', page):
        lines = [clean(re.sub(r"<[^>]+>", " ", x))
                 for x in re.split(r"(?i)<br\s*/?>", m.group(1))]
        lines = [x for x in lines if x]
        if len(lines) < 2 or not re.fullmatch(
                r"Village President|Trustee Seat No\. \d", lines[1]):
            continue
        row = {"name": lines[0], "role": lines[1]}
        mail = re.search(r'mailto:([^"?]+@mtpleasantwi\.gov)', m.group(2))
        if mail:
            row["email"] = mail.group(1)
        text = clean(re.sub(r"<[^>]+>", " ", m.group(2)))
        phone = re.search(r"\(\d{3}\)\s*\d{3}-\d{4}", text)
        if phone:
            row["phone"] = phone.group(0)
        term = re.search(r"Term Expires:\s*([A-Z][a-z]+ \d{4})", text)
        if term:
            row["term"] = term.group(1)
        members.append(row)
    if len(members) != 7:
        raise RuntimeError("Mount Pleasant: %d members read against the six "
                           "trustees and one president its page states"
                           % len(members))
    return {"geoid": "5554875", "name": "Mount Pleasant", "county": "Racine",
            "atLarge": True, "board": members,
            "sourceUrl": MOUNT_PLEASANT_BOARD}


def scrape_menomonee_falls():
    """The Village Board: one `member-card` per person, a `member-name` with a
    `seat-badge` ("Seat N") on each trustee, a `member-role`, and a term.

    THE PAGE DOES NOT SAY THE TRUSTEES ARE ELECTED AT LARGE, so this roster
    does not claim it. Its words are "Elected at-large" for the president and
    "6 elected seats · Nonpartisan · Elected by numbered seat" for the
    trustees, and no trustee is given a district. Both sentences are gates,
    and the card prints what the page says rather than "elected at large".

    NO CONTACT SHIPS: the one phone shown is the village's own main number on
    every card, and each e-mail is a form link.
    """
    page = fetch(MENOMONEE_FALLS_BOARD)
    flat = clean(re.sub(r"<[^>]+>", " ", page))
    if "Elected by numbered seat" not in flat or "Elected at-large" not in flat:
        raise RuntimeError("Menomonee Falls no longer says how its board is "
                           "elected in the words this roster repeats")
    members = []
    for card in re.split(r'<div class="member-card\b', page)[1:]:
        # The seat badge sits INSIDE the name span, so it is read and removed
        # before the name is.
        name = re.search(r'(?s)<span class="member-name">(.*?)</span>\s*'
                         r'<span class="member-role">(.*?)</span>', card)
        if not name:
            continue
        badge = re.search(r'(?s)<span class="seat-badge">(.*?)</span>',
                          name.group(1))
        seat = clean(badge.group(1)) if badge else ""
        who = clean(re.sub(r"<[^>]+>", " ", re.sub(
            r'(?s)<span class="seat-badge">.*?</span>', " ", name.group(1))))
        what = clean(re.sub(r"<[^>]+>", " ", name.group(2)))
        if seat and what == "Village Trustee":
            if not re.fullmatch(r"Seat \d", seat):
                raise RuntimeError("Menomonee Falls: %s carries the badge %r"
                                   % (who, seat))
            label = "Trustee, " + seat
        elif not seat and what == "Village President":
            label = what
        else:
            raise RuntimeError("Menomonee Falls: %s has neither a seat nor the "
                               "president's role" % who)
        row = {"name": who, "role": label}
        term = re.search(r'Term Expires</span>\s*<span class="meta-value">'
                         r"([A-Z][a-z]+ \d{4})</span>", card)
        if term:
            row["term"] = term.group(1)
        members.append(row)
    if len(members) != 7:
        raise RuntimeError("Menomonee Falls: %d member cards against six "
                           "trustees and a president" % len(members))
    return {"geoid": "5551000", "name": "Menomonee Falls",
            "county": "Waukesha", "atLarge": False,
            "howElected": "The village says its president is elected at large "
                          "and its six trustees are elected by numbered seat. "
                          "It gives no trustee a district, and the map draws "
                          "none.",
            "board": members, "sourceUrl": MENOMONEE_FALLS_BOARD}


def scrape_fond_du_lac():
    """The City Council's contact page: one person card per member, the name
    in `person-name`, the role in `person-title` ("President", "Council
    Vice-President", "Council Member"), then an e-mail, a phone, "Elected:"
    and "Current Term Ends:".

    THE CITY DOES NOT SAY HOW THE SEATS ARE ELECTED, so this roster does not
    either. Its council page describes "a seven-member City Council elected for
    two-year terms" and gives no member a district; neither that page nor the
    council-organization page says "at large". That sentence is the gate, and
    the card prints it rather than "elected at large".

    THE E-MAIL IS WRITTEN AS HTML ENTITIES, which every browser decodes to the
    address it shows, so decoding it reads the page as a reader sees it. The
    page says members "may be reached ... by contacting their personal
    numbers", and the number on each card is that published contact.
    """
    about = clean(re.sub(r"<[^>]+>", " ", fetch(FOND_DU_LAC_ABOUT)))
    if not re.search(r"(?i)seven-member City Council elected for two-year "
                     r"terms", about):
        raise RuntimeError("Fond du Lac's council page no longer describes a "
                           "seven-member council elected for two-year terms")
    page = fetch(FOND_DU_LAC_CONTACT)
    members = []
    for m in re.finditer(r'(?s)<span class="person-name">(.*?)</span>'
                         r'<span class="person-title">(.*?)</span>(.*?)'
                         r'(?=<span class="person-name">|$)', page):
        row = {"name": clean(re.sub(r"<[^>]+>", " ", m.group(1))),
               "role": clean(re.sub(r"<[^>]+>", " ", m.group(2)))}
        rest = H.unescape(m.group(3))
        mail = re.search(r'mailto:([A-Za-z0-9._%+-]+@fdl\.wi\.gov)', rest)
        if mail:
            row["email"] = mail.group(1)
        text = clean(re.sub(r"<[^>]+>", " ", rest))
        phone = re.search(r"\b\d{3}-\d{3}-\d{4}\b", text)
        if phone:
            row["phone"] = phone.group(0)
        term = re.search(r"Current Terms? Ends:\s*([A-Z][a-z]+ \d{4})", text)
        if term:
            row["term"] = term.group(1)
        members.append(row)
    if len(members) != 7:
        raise RuntimeError("Fond du Lac: %d person cards against the "
                           "seven-member council its page states"
                           % len(members))
    return {"geoid": "5526275", "name": "Fond du Lac", "county": "Fond du Lac",
            "atLarge": False,
            "howElected": "The city describes a seven-member council elected "
                          "for two-year terms and gives no member a district. "
                          "Its pages do not say whether the seats are elected "
                          "at large.",
            "board": members, "sourceUrl": FOND_DU_LAC_CONTACT}


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

    THE CELL-PHONE COLUMN SHIPS SINCE 2026-10-17. The city publishes a City
    Phone and a Cell Phone for each member. Until 2026-10-17 only the City Phone
    was emitted, on the reasoning that the cell number is a personal handset.
    Adam ruled that day, for every state, "if the official government source
    uses personal phone numbers, we publish those", so the cell number is now
    emitted too, labelled "cell" as the column heading says: in `phonesExtra`
    after the city line, or as `phone` for a member the table gives no city
    line. Measured 2026-10-17, five of the seven print one. A cell number that
    is the member's own city line, that the table prints for two or more
    members, or that the page prints outside the table (the city's own lines)
    is not the member's and does not ship; a cell holding anything but one
    telephone number fails the city rather than shipping part of it.

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
    raw_cells = [re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", r) for r in rows]
    raw_cells = [row for row in raw_cells if row]
    cells = [[clean(re.sub(r"(?is)<[^>]+>", " ", c)) for c in row]
             for row in raw_cells]
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

    # How often each number is printed in the table's two phone columns, and
    # the numbers the page prints outside the table (the city's own lines): a
    # cell number found in either is not one member's (see the docstring).
    printed = {}
    for row in cells[1:]:
        if len(row) == len(head):
            for col in ("city phone", "cell phone"):
                key = _digits(row[ix[col]])
                if key:
                    printed[key] = printed.get(key, 0) + 1
    outside = {_digits(n) for n in JANESVILLE_NUMBER.findall(
        clean(re.sub(r"(?is)<[^>]+>", " ", contact.replace(table, " "))))}

    members = []
    for row, raw in zip(cells[1:], raw_cells[1:]):
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
        if phone and not _tel_links_agree(raw[ix["city phone"]]):
            print("  note Janesville: %s's City Phone link dials a different "
                  "number than its text shows — neither ships" % name,
                  file=sys.stderr)
            phone = ""
        if phone:
            member["phone"] = phone
        cell = row[ix["cell phone"]]
        if cell and not JANESVILLE_ONE_NUMBER.match(cell):
            raise RuntimeError("Janesville: %s's Cell Phone cell holds something "
                               "other than one telephone number — re-read the "
                               "table before shipping it" % name)
        key = _digits(cell)
        if cell and not _tel_links_agree(raw[ix["cell phone"]]):
            print("  note Janesville: %s's Cell Phone link dials a different "
                  "number than its text shows — neither ships" % name,
                  file=sys.stderr)
        elif cell and key == _digits(phone):
            pass                       # the city line printed in both columns
        elif cell and (printed.get(key, 0) > 1 or key in outside):
            print("  note Janesville: %s's cell number is printed for another "
                  "member or elsewhere on the page — the city's line, not the "
                  "member's; not shipped" % name, file=sys.stderr)
        elif cell and phone:
            member["phonesExtra"] = ["cell " + cell]
        elif cell:
            member["phone"] = "cell " + cell
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
          ("Janesville", scrape_janesville),
          ("Mount Pleasant", scrape_mount_pleasant),
          ("Menomonee Falls", scrape_menomonee_falls),
          ("Fond du Lac", scrape_fond_du_lac))


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
